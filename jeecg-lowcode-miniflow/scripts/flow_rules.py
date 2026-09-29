# -*- coding: utf-8 -*-
"""流程声明（flow_dsl 的 FLOWS）上的「引擎行为规则」—— 构建前的一道预处理。

为什么有这个模块（2026-09-21 进销存 47 表 / 56 流程真机端到端实测）：
下面六条引擎行为**全部是静默的** —— save / deploy / 节点契约检查全绿，流程也照跑，
只有造单据、点确认、回读数据才看得出账错了。那一轮为此在真机上试错约 30 分钟。
把它们固化成「自动改写 / 构建期报错」，声明怎么写都不会再踩。

| # | 引擎行为（实测）                                   | 本模块的处理                          |
|---|--------------------------------------------------|---------------------------------------|
| 1 | 数据分支网关名必须是引擎硬编码的「数据分支」，否则取不到数据时**终止实例**（曾被误判为「无数据支不执行」） | 强制校正名字；绕行改写改为可选 `rewrite_databranch` |
| 2 | 流程 `add()` 建的行**不吃表单默认值**，空值上 `inc`/`dec` **静默不生效**，且实测还会连累**同节点其余字段一起不写**（2026-09-22 进销存 R2/R5） | 被累加过的列在 `add()` 里自动补 0；**接口建的行 `DEFAULTS()` 也不落**，造数脚本要自己写 0 |
| 3 | number/integer 目标的增/减走 `Integer.parseInt`，带小数的值（公式落库 20.0、运算结果）归 0 | **构建器已改走 BigDecimal 路径**（updateFields.**fieldType**=money，引擎读的是这个键），本模块不再默认插运算节点；`expand_formula=True` 可选 |
| 4 | 运算节点从「取单条」结果取数曾观测不准（**源码未证实**） | 告警 |
| 5 | 判据取自输入行上复制来的 link-field/summary **快照**时读的是旧值（比较符本身对称、支持小数：ConditionItemComparator:94-185） | 告警：改用取多条/取单条的实时结果 |
| 6 | 同表同事件多条主流程**都会触发但未必都生效**：`cond` 判的是**当前行**而非触发快照，前一条改了字段后，后一条的条件就不再成立（2026-09-22 进销存 R5 定论）| 告警：合并成一条多分支流程，或改显式链式 |
| 7 | **子流程内的排他网关实测恒走默认支**（2026-09-22 进销存两例：`盘亏数量>0`、`result()>=0`） | 告警：**已知风险，不是改结构的许可**。照需求原文建 + 在交付里标注，由用户决定。要改成 `get_one + data_branch`（会把「获取多条」塌成「获取单条」）或挪到父流程，**必须先问用户**。教训见 batch-flows.md「禁止语义等价替换」条 |

用法（build_flows / precheck 都走这两个入口）：

    flows, rep = flow_rules.apply_static(flows, rewrite=True)          # 不需要字段类型
    flows, rep2 = flow_rules.apply_typed(flows, ftype, fexpr, rewrite=True)
    #   ftype(表, 字段) -> 控件类型 | None
    #   fexpr(表, 字段) -> 公式表达式（占位符是 `$字段中文名$`）| None

`rep` = {"errors": [...], "warnings": [...], "notes": [...]}。notes 是「我替你改了什么」，必须打印给人看。
本模块**纯数据变换、不联网**，所以 precheck 也能用它做零真机检查。
"""
import copy
import re

START = "start"
DATA_BRANCH_NAME = "数据分支"      # 引擎 MiniDesConstant.DATA_BRANCH_NAME，BaseDataDelegate:1088 精确比较

#：运算节点 compute() 的输入，只有这几种控件类型实测取数可靠
COMPUTE_OK_TYPES = {"number", "integer", "formula", "slider", "rate"}
#：直接 inc/dec 实测可靠的来源类型（money、number 都跑通过；公式会把原值冲成 0）
INC_UNSAFE_TYPES = set()          # 构建器已走 BigDecimal 路径；expand_formula=True 时临时置 {"formula"}
INC_UNKNOWN_TYPES = {"summary", "link-field"}
#：网关判据白名单
SNAPSHOT_TYPES = {"link-field", "summary"}    # 输入行上的复制值/汇总值：判据读到的可能是旧快照


def _report():
    return {"errors": [], "warnings": [], "notes": []}


def _is_result(v):
    return isinstance(v, dict) and "$result" in v


def _is_ref(v):
    return isinstance(v, dict) and "$ref" in v


def _result(name, decimals=2):
    return {"$result": name, "$decimals": decimals}


def _ref(field, node=START):
    return {"$ref": field, "$node": node}


def _children(node):
    """节点下挂的子节点列表们（就地可改）。"""
    out = []
    for b in node.get("branches") or []:
        if isinstance(b.get("nodes"), list):
            out.append(b["nodes"])
    for k in ("found", "missing"):
        if isinstance(node.get(k), list):
            out.append(node[k])
    if isinstance(node.get("default"), list):
        out.append(node["default"])
    return out


def walk_lists(nodes):
    """深度优先产出每一个「节点列表」（含嵌套在分支里的）。"""
    yield nodes
    for n in nodes:
        if isinstance(n, dict):
            for sub in _children(n):
                for x in walk_lists(sub):
                    yield x


def walk_nodes(nodes):
    for lst in walk_lists(nodes):
        for n in lst:
            if isinstance(n, dict):
                yield n


def _names(flow):
    return {n.get("name") for n in walk_nodes(flow.get("nodes") or []) if n.get("name")}


def _uniq(base, used):
    name, i = base, 2
    while name in used:
        name, i = "%s%d" % (base, i), i + 1
    used.add(name)
    return name


def _tuple_cond(cond):
    """get_one 的「同名匹配」字符串写法 → 显式三元组（get_more 复用同一组条件时要用）。"""
    out = []
    for c in cond or []:
        out.append((c, "等于", _ref(c)) if isinstance(c, str) else tuple(c))
    return out


# ───────────────────────── 静态规则（不需要字段类型） ─────────────────────────

def _expand_upsert(flow, rep, rewrite_databranch=False):
    """`upsert()` → 默认展开成引擎原生 `get_one(empty="分支") → data_branch(「数据分支」)`；
    `rewrite_databranch=True` 才展开成绕行形态（取多条→统计条数→判 0）。"""
    used = _names(flow)
    for lst in walk_lists(flow.get("nodes") or []):
        i = 0
        while i < len(lst):
            n = lst[i]
            if isinstance(n, dict) and n.get("type") == "upsert":
                base = n.get("name") or ("查%s" % n["table"])
                if rewrite_databranch:
                    lst[i:i + 1] = _upsert_nodes(n["table"], n.get("cond"), n.get("found") or [],
                                                 n.get("missing") or [], base, used)
                    i += 3
                else:
                    lst[i:i + 1] = [
                        {"type": "get_one", "table": n["table"], "cond": n.get("cond") or [], "empty": "分支",
                         "name": base, "fields": None},
                        {"type": "data_branch", "name": DATA_BRANCH_NAME,
                         "found": list(n.get("found") or []), "missing": list(n.get("missing") or [])}]
                    i += 2
            else:
                i += 1


def _upsert_nodes(table, cond, found, missing, base, used):
    """绕行形态：取多条(同条件) → 统计条数 → 互斥分支（=0 走 missing；否则 取单条 + found）。"""
    cond = _tuple_cond(cond)
    gm = _uniq("%s(列表)" % base, used)
    cr = _uniq("统计%s条数" % base, used)
    go = _uniq(base, used) if base in used else base
    used.add(go)
    gw = _uniq("%s是否存在" % base, used)
    return [
        {"type": "get_more", "table": table, "cond": cond, "sort": None, "limit": 0, "from": None, "name": gm},
        {"type": "operation", "name": cr, "fun_type": "record", "source": gm, "decimals": 0},
        {"type": "exclusive", "name": gw, "default": None, "branches": [
            {"name": "没查到", "cond": [(_result(cr, 0), "等于", 0)], "nodes": list(missing)},
            {"name": "其他情况", "nodes": [
                {"type": "get_one", "table": table, "cond": cond, "empty": "继续", "name": go, "fields": None}
            ] + list(found)}]},
    ]


def _fix_data_branch(flow, rep, rewrite_databranch=False):
    """规则 1：数据分支网关名必须是「数据分支」（引擎精确比较，否则取不到数据时终止实例）。
    `rewrite_databranch=True` 时改写成绕行形态（取多条→统计条数→判 0）。"""
    fname = flow.get("name")
    used = _names(flow)
    for lst in walk_lists(flow.get("nodes") or []):
        i = 0
        while i < len(lst):
            n = lst[i]
            if not (isinstance(n, dict) and n.get("type") == "data_branch"):
                i += 1
                continue
            if n.get("name") != DATA_BRANCH_NAME:
                rep["notes"].append("流程「%s」：数据分支网关名「%s」→ 已校正为「%s」（引擎按此名放行，"
                                    "否则取不到数据时直接终止实例）" % (fname, n.get("name"), DATA_BRANCH_NAME))
                n["name"] = DATA_BRANCH_NAME
            prev = lst[i - 1] if i > 0 and isinstance(lst[i - 1], dict) else {}
            # 「取多条」后接数据分支也是**合法**形态，别拦。
            # 依据：数据分支是靠取数基类 `BaseDataDelegate.noDataExecute()` 触发的，
            # 「取多条」走同一条无数据路径；提示词给项目管理子流程的节点顺序就是
            # 「① 取本条任务(get_one) → ② 取父任务(get_more) → ③ 数据分支」，
            # 且该分支要判的是 **② 取到没取到父任务**（判 ① 会失去意义 —— ① 的闸门
            # 已经写在它的四条条件里了）。2026-09-22 项目管理 R6 实测该顺序可用。
            if not ((prev.get("type") == "get_one" and prev.get("empty") == "分支")
                    or prev.get("type") == "get_more"):
                rep["errors"].append(
                    "流程「%s」：数据分支前面必须紧跟 get_one(..., empty=\"分支\") 或 get_more" % fname)
                i += 1
                continue
            if rewrite_databranch and (n.get("missing") or []):
                used.discard(prev.get("name"))
                lst[i - 1:i + 1] = _upsert_nodes(prev["table"], prev.get("cond"), n.get("found") or [],
                                                 n.get("missing") or [], prev.get("name") or ("查%s" % prev["table"]), used)
                rep["notes"].append("流程「%s」：「%s」+ 数据分支 → 按 --rewrite-databranch 改写为 取多条→统计条数→判 0"
                                    % (fname, prev.get("name")))
                i += 2
            i += 1


def _inc_columns(flows):
    """全应用里被 inc()/dec() 过的列：{表: {字段, ...}}。"""
    out = {}
    for f in flows:
        for n in walk_nodes(f.get("nodes") or []):
            if n.get("type") != "data_update":
                continue
            for k, v in (n.get("mapping") or {}).items():
                if isinstance(v, dict) and ("$inc" in v or "$dec" in v):
                    out.setdefault(n.get("table"), set()).add(k)
    return out


def inc_columns(flows):
    """被 `inc`/`dec` 累加过的列：`{表: {列…}}`。precheck 用它提示「没有初值的累加列」。"""
    return _inc_columns(flows)


def _zero_fill(flows, rep, rewrite):
    """规则 2：流程建的行不吃表单默认值 → 被累加过的列在 add() 里补 0。

    ⚠️ 只管**流程自己建的行**。API（造数脚本 / 冒烟）建的行同样不吃默认值，
    那些列要在建后套件的 `DEFAULTS()` 里给初值 0，否则第一次累加被静默吞掉
    （2026-09-22 进销存 R2：11 个被累加列补初值后才对账）。"""
    cols = _inc_columns(flows)
    for f in flows:
        for n in walk_nodes(f.get("nodes") or []):
            if n.get("type") != "data_add" or not n.get("mapping"):
                continue
            miss = sorted(c for c in cols.get(n.get("table"), ()) if c not in n["mapping"])
            if not miss:
                continue
            if rewrite:
                for c in miss:
                    n["mapping"][c] = 0
                rep["notes"].append("流程「%s」节点「%s」：新建 %s 时自动补 0 → %s（这些列会被别的流程累加，"
                                    "空值上做「增加」不生效）" % (f.get("name"), n.get("name"), n.get("table"),
                                                         "、".join(miss)))
            else:
                rep["warnings"].append("流程「%s」节点「%s」：新建 %s 没写 %s，它们会被累加 —— 空值上「增加」不生效，"
                                       "请显式写 0" % (f.get("name"), n.get("name"), n.get("table"), "、".join(miss)))


def _check_gateways(flows, rep, strict):
    """规则 5（修正版）：比较符本身对称且支持小数（ConditionItemComparator.le/lt/ge/gt 均 BigDecimal），
    不再限制运算符；只对「字段 vs ref(字段)」这种未证实的写法告警。判据**来源**的检查在 apply_typed 里。"""
    bucket = rep["errors"] if strict else rep["warnings"]
    for f in flows:
        for n in walk_nodes(f.get("nodes") or []):
            if n.get("type") != "exclusive":
                continue
            if f.get("kind") == "sub":
                # 2026-09-22 进销存 R2 实测：子流程内的排他网关**两例都恒走默认支**
                # （`盘亏数量>0`、`result()>=0`），源码未定论但代价是整条链静默不记账。
                # ⛔ 本条**不是改结构的授权**：2026-09-22 销售管理实测，作者把下面这句
                #    「改用 get_one + data_branch()」当成施工指令照做，连带把需求原文点名的
                #    `get_more`(获取多条) 换成 `get_one`、`compute_record`(统计条数) 整个删掉，
                #    并用「与需求同语义」背书 —— 而 data_branch 判的是「有没有数据」不是「有几条」。
                #    照原文建、标已知风险；要改结构必须先问用户。
                bucket.append("流程「%s」是子流程，里面的排他网关「%s」实测恒走默认支（2026-09-22 两例）。"
                              "⚠️ 这是【已知风险】，不是【必须改结构】—— 需求原文写的是"
                              "「获取多条 / 运算统计条数 / 互斥分支」这类节点时，**照原文建**，"
                              "在交付说明里标成已知风险交给用户决定。"
                              "⛔ 不许把本告警当成改结构的许可证：data_branch() 判的是「有没有数据」"
                              "而不是「有几条」，选它必然连带把 get_more 换成 get_one、"
                              "把判据从「计数==0」换成「是否存在」—— 那是语义降级"
                              "（需求里的「多条」量词会消失），不是等价替换。"
                              "确实要改成 get_one(cond 带比较, empty=\"分支\") + data_branch()、"
                              "或把判断挪到父流程，**必须先跟用户确认**。"
                              "（详见 batch-flows.md「禁止语义等价替换」条）"
                              % (f.get("name"), n.get("name")))
            for b in n.get("branches") or []:
                for c in b.get("cond") or []:
                    subj, val = c[0], (c[2] if len(c) > 2 else None)
                    where = "流程「%s」网关「%s」分支「%s」" % (f.get("name"), n.get("name"), b.get("name"))
                    if _is_result(subj) and isinstance(val, dict):
                        bucket.append("%s：运算结果建议只和固定数值比（和 ref()/var() 比的写法未验证）" % where)
                    elif not _is_result(subj) and _is_ref(val):
                        bucket.append("%s：「字段 vs ref(字段)」比较未经真机验证（此前一次不命中已确认是快照旧值所致）；"
                                      "稳妥写法：compute() 算差额后判 result()" % where)


def _check_same_event(flows, rep):
    """规则 6：同表 + 同触发时机 + 同监控字段 的主流程 ≥2 条。

    引擎会**逐条触发**（信号名每流程唯一，BpmnCreator:366），但每条的 `cond` 是对
    **求值那一刻的当前行**判的、不是触发快照 —— 前一条改了行上的字段后，后一条的条件
    往往就不成立了，表现成「只跑了一条」（2026-09-22 进销存 R5 定论，与早前观测在此和解）。
    """
    seen = {}
    for f in flows:
        if f.get("kind") != "main":
            continue
        key = (f.get("table"), f.get("on"), tuple(sorted(f.get("watch") or [])))
        seen.setdefault(key, []).append(f.get("name"))
    for (tb, on, watch), names in seen.items():
        if len(names) > 1:
            rep["warnings"].append("表「%s」上有 %d 条主流程同为「%s」触发、监控字段相同（%s）：%s —— "
                                   "引擎会逐条触发，但每条的 cond 判的是**当前行**而非触发快照："
                                   "前一条改了字段后，后一条条件往往不再成立、静默不执行"
                                   "（2026-09-22 进销存 R5 定论）。合并成一条多分支流程，或改成显式链式"
                                 % (tb, len(names), on, "、".join(watch) or "无", "、".join(names)))


def _normalize_conds(flows):
    """("字段", "为空") 二元组 → ("字段", "为空", None)。写法本身合法，不该让构建器抛 unpack 错。"""
    def fix(lst):
        out = []
        for c in lst or []:
            if isinstance(c, (list, tuple)) and len(c) == 2:
                out.append((c[0], c[1], None))
            else:
                out.append(c)
        return out
    for f in flows:
        if f.get("cond"):
            f["cond"] = fix(f["cond"])
        for n in walk_nodes(f.get("nodes") or []):
            if n.get("cond") and n.get("type") in ("get_one", "get_more", "upsert"):
                n["cond"] = fix(n["cond"])
            for b in n.get("branches") or []:
                if b.get("cond"):
                    b["cond"] = fix(b["cond"])


def apply_static(flows, rewrite=True, strict=False, rewrite_databranch=False):
    flows = copy.deepcopy(flows)
    rep = _report()
    _normalize_conds(flows)
    for f in flows:
        _expand_upsert(f, rep, rewrite_databranch)
        _fix_data_branch(f, rep, rewrite_databranch)
    _zero_fill(flows, rep, rewrite)
    _check_gateways(flows, rep, strict)
    _check_same_event(flows, rep)
    return flows, rep


# ───────────────────────── 类型规则（需要 ftype(表, 字段)） ─────────────────────────

def _node_tables(flow):
    ctx = flow.get("table") or flow.get("context")
    out = {START: ctx}
    for n in walk_nodes(flow.get("nodes") or []):
        if n.get("name") and n.get("type") in ("get_one", "get_more", "data_add"):
            out[n["name"]] = n.get("table") or ctx
    return out


_ARITH = re.compile(r"^[\s0-9.+\-*/()]*$")
NUM_TYPES = {"number", "integer", "slider", "rate"}


def _expand_formula(table, field, ftype, fexpr, depth=0):
    """公式字段 → (只含数字字段占位符的算式, {字段名: 字段名})；展不开返回 (None, 原因)。"""
    if depth > 3:
        return None, "公式嵌套超过 3 层"
    expr = fexpr(table, field) if fexpr else None
    if not expr:
        return None, "读不到它的公式表达式"
    if not _ARITH.match(re.sub(r"\$[^$]+\$", "1", expr)):
        return None, "公式里有函数/非四则运算（%s）" % expr
    fields = {}
    for nm in dict.fromkeys(re.findall(r"\$([^$]+)\$", expr)):
        ty = ftype(table, nm)
        if ty in NUM_TYPES:
            fields[nm] = nm
        elif ty == "formula":
            sub, sub_fields = _expand_formula(table, nm, ftype, fexpr, depth + 1)
            if sub is None:
                return None, "它依赖的公式字段「%s」展不开：%s" % (nm, sub_fields)
            expr = expr.replace("$%s$" % nm, "(%s)" % sub)
            fields.update(sub_fields)
        else:
            return None, "它依赖「%s」（%s 字段），运算节点从这类字段取数不可靠" % (nm, ty or "未知类型")
    return expr, fields


def _fix_inc(flow, ftype, fexpr, rep, rewrite, expand_formula=False):
    """规则 3：inc/dec(ref(公式字段)) → 把公式展开成底层数字字段，前插运算节点重算。

    2026-09-21 两轮真机对照：① 公式值直接累加 → 原值被冲成 0；② 运算节点 `$v$` 直读公式字段再累加 → 加的是 0
    （同一个结果拿去当「>0」判据却是对的，很有迷惑性）；③ 运算节点从**数字字段**重算（到货-不合格）→ 正确。
    """
    fname = flow.get("name")
    tables = _node_tables(flow)
    used = _names(flow)
    made = {}
    for lst in list(walk_lists(flow.get("nodes") or [])):
        for n in lst:
            if not (isinstance(n, dict) and n.get("type") == "data_update"):
                continue
            for k, v in list((n.get("mapping") or {}).items()):
                op = None
                if isinstance(v, dict):
                    op = "$inc" if "$inc" in v else ("$dec" if "$dec" in v else None)
                if not op or not _is_ref(v[op]):
                    continue
                r = v[op]
                node = r.get("$node") or START
                ty = ftype(tables.get(node), r["$ref"])
                where = "流程「%s」节点「%s」：%s 的累加值取自「%s」" % (fname, n.get("name"), k, r["$ref"])
                if ty in INC_UNKNOWN_TYPES:
                    rep["warnings"].append(where + "（%s 字段）—— 这类来源没有真机验证过，建好后务必造一单回读确认" % ty)
                if ty not in (INC_UNSAFE_TYPES | ({"formula"} if expand_formula else set())):
                    continue
                if node != START:
                    rep["errors"].append(where + "（公式字段，且来自节点「%s」的结果）—— 公式值累加会把原值冲成 0，"
                                         "而运算节点只能可靠地读**本行数字字段**。请改成从本行取" % node)
                    continue
                expr, fields = _expand_formula(tables.get(node), r["$ref"], ftype, fexpr)
                if expr is None:
                    rep["errors"].append(where + "（公式字段）—— 公式值直接累加会把原值**冲成 0**，且无法自动展开：%s。"
                                         "请把累加值改成数字字段，或自己 compute() 从数字字段重算" % fields)
                    continue
                if not rewrite:
                    rep["errors"].append(where + "（公式字段）—— 直接累加会把原值**冲成 0**。请 compute(\"%s\") "
                                         "从数字字段重算后 inc(result())，或去掉 --no-rewrite" % expr)
                    continue
                key = (node, r["$ref"])
                if key not in made:
                    cn = _uniq("算%s" % r["$ref"], used)
                    ph = {nm: "f%d" % i for i, nm in enumerate(fields, 1)}
                    ex = expr
                    for nm, p_ in ph.items():
                        ex = ex.replace("$%s$" % nm, "$%s$" % p_)
                    flow["nodes"].insert(len(made), {"type": "operation", "name": cn, "expr": ex, "decimals": 2,
                                                     "fields": {p_: _ref(nm) for nm, p_ in ph.items()}})
                    made[key] = cn
                    rep["notes"].append(where + "（公式 %s）→ 已在流程最前面插入运算节点「%s」从数字字段重算，"
                                        "改为累加运算结果" % (expr, cn))
                n["mapping"][k] = {op: _result(made[key])}


def _check_compute(flow, ftype, rep, lenient):
    """规则 4（修正版）：运算节点取「取单条/取多条」结果曾观测不准，**源码未证实** → 只告警。
    公式/金额/汇总字段直接参与运算在源码上是安全的（getNumberResult 用 BigDecimal），不再报。"""
    tables = _node_tables(flow)
    for n in walk_nodes(flow.get("nodes") or []):
        if n.get("type") != "operation" or n.get("fun_type") == "record":
            continue
        for ph, r in (n.get("fields") or {}).items():
            if not _is_ref(r):
                continue
            node = r.get("$node") or START
            if node != START:
                rep["warnings"].append("流程「%s」运算节点「%s」的 $%s$ 取自节点「%s」的结果 —— 2026-09-21 曾观测取值不准"
                                       "（源码未证实），建好后造一单回读确认；判「有没有余额」更稳的写法是 "
                                       "get_more(带条件) + compute_record + result()==0"
                                       % (flow.get("name"), n.get("name"), ph, node))


def _check_judgement_sources(flow, ftype, rep):
    """规则 5（来源）：网关判据若是输入行上的 link-field / summary，读到的是复制/汇总时的快照，
    在同一流程里刚被上游节点改过的量不会反映进来（2026-09-21 核销「小于等于 0 不命中」的真因）。"""
    ctx = flow.get("table") or flow.get("context")
    for n in walk_nodes(flow.get("nodes") or []):
        if n.get("type") != "exclusive":
            continue
        for b in n.get("branches") or []:
            for c in b.get("cond") or []:
                subj = c[0]
                if _is_result(subj) or not isinstance(subj, str):
                    continue
                ty = ftype(ctx, subj)
                if ty in SNAPSHOT_TYPES:
                    rep["warnings"].append("流程「%s」网关「%s」分支「%s」：判据「%s」是本行的 %s 字段（快照值），"
                                           "上游节点刚改过的量不会反映进来。要判实时余额请用 get_more(带条件)+compute_record"
                                           % (flow.get("name"), n.get("name"), b.get("name"), subj, ty))


def apply_typed(flows, ftype, fexpr=None, rewrite=True, lenient=False, expand_formula=False):
    flows = copy.deepcopy(flows)
    rep = _report()
    for f in flows:
        _fix_inc(f, ftype, fexpr, rep, rewrite, expand_formula)
        _check_compute(f, ftype, rep, lenient)
        _check_judgement_sources(f, ftype, rep)
    return flows, rep


def print_report(rep, log=print, title="flow_rules"):
    for m in rep["notes"]:
        log("NOTE:%s %s" % (title, m))
    for m in rep["warnings"]:
        log("WARN:%s %s" % (title, m))
    for m in rep["errors"]:
        log("FAIL:%s %s" % (title, m))
    return not rep["errors"]


# ───────────────────────── 自测（不联网） ─────────────────────────

def _self_test():
    ty = {("明细", "本次入库数量"): "formula", ("明细", "到货"): "number", ("明细", "优惠"): "money"}
    ftype = lambda t, f: ty.get((t, f))
    inc = lambda v: {"$inc": v}
    flows = [
        {"name": "记账-子", "kind": "sub", "context": "明细", "nodes": [
            {"type": "get_one", "table": "库存", "cond": ["编码"], "empty": "分支", "name": "查库存"},
            {"type": "data_branch", "name": "有没有", "found": [
                {"type": "data_update", "table": "库存", "mapping": {"入库数": inc(_ref("本次入库数量"))},
                 "name": "累加", "source": None}],
             "missing": [{"type": "data_add", "table": "库存", "mapping": {"编码": _ref("编码")}, "name": "建行"}]}]},
        {"name": "A", "kind": "main", "table": "盘点", "on": "修改", "watch": ["确认"], "nodes": []},
        {"name": "B", "kind": "main", "table": "盘点", "on": "修改", "watch": ["确认"], "nodes": [
            {"type": "operation", "name": "算", "expr": "$x$", "fields": {"x": _ref("优惠")}, "decimals": 2},
            {"type": "exclusive", "name": "网关", "branches": [
                {"name": "小", "cond": [(_result("算"), "小于等于", 0)], "nodes": []}, {"name": "其他", "nodes": []}]}]},
    ]
    flows[2]["table"] = "明细"
    f2, r1 = apply_static(flows)
    types = [n["type"] for n in f2[0]["nodes"]]
    assert types == ["get_one", "data_branch"], types                                 # 规则 1：原生形态
    assert f2[0]["nodes"][1]["name"] == DATA_BRANCH_NAME and any("已校正" in x for x in r1["notes"]), r1
    f2b, _ = apply_static(flows, rewrite_databranch=True)
    assert [n["type"] for n in f2b[0]["nodes"]] == ["get_more", "operation", "exclusive"]   # 绕行形态仍可选
    add = [n for n in walk_nodes(f2[0]["nodes"]) if n["type"] == "data_add"][0]
    assert add["mapping"].get("入库数") == 0, add                                      # 规则 2
    assert not any("小于等于" in w for w in r1["warnings"]), r1                        # 规则 5：比较符不再受限
    flows[2]["table"] = "盘点"
    _, r6 = apply_static(flows)
    assert any("当前行" in w for w in r6["warnings"]) and not r6["errors"], r6       # 规则 6：降为告警
    flows[2]["table"] = "明细"
    ty[("明细", "不合格")] = "number"
    f3d, _ = apply_typed(f2, ftype, lambda t, f: {"本次入库数量": "$到货$-$不合格$"}.get(f))
    assert [n["type"] for n in f3d[0]["nodes"]] == ["get_one", "data_branch"]                         # 规则 3：默认不插节点
    f3, r2 = apply_typed(f2, ftype, lambda t, f: {"本次入库数量": "$到货$-$不合格$"}.get(f), expand_formula=True)
    assert [n["type"] for n in f3[0]["nodes"]] == ["operation", "get_one", "data_branch"]              # 规则 3：可选展开
    calc = f3[0]["nodes"][0]
    assert calc["expr"] == "$f1$-$f2$" and calc["fields"]["f1"]["$ref"] == "到货", calc               # 展开到数字字段
    upd_branch = f3[0]["nodes"][2]["found"]
    assert [n["type"] for n in upd_branch] == ["data_update"], upd_branch
    assert "$result" in upd_branch[0]["mapping"]["入库数"]["$inc"]
    _, r2b = apply_typed(f2, ftype, lambda t, f: "$到货$-$优惠$", expand_formula=True)                  # 依赖金额 → 报错
    assert any("无法自动展开" in e for e in r2b["errors"]), r2b
    assert not r2["errors"] and any("小于等于" in w for w in r1["warnings"]) is False   # 规则 4：不再报错
    two = [{"name": "T", "kind": "main", "table": "明细", "on": "新增", "cond": [("到货", "不为空")], "nodes": [
        {"type": "exclusive", "name": "g", "branches": [{"name": "a", "cond": [("到货", "为空")], "nodes": []},
                                                        {"name": "其他", "nodes": []}]}]}]
    f4, _ = apply_static(two)
    assert f4[0]["cond"] == [("到货", "不为空", None)] and f4[0]["nodes"][0]["branches"][0]["cond"] == [("到货", "为空", None)]
    bad = copy.deepcopy(flows); bad[0]["nodes"][0]["empty"] = "继续"
    _, r3 = apply_static(bad)
    assert any("紧跟 get_one" in e for e in r3["errors"]), r3
    print("flow_rules self-test OK")


if __name__ == "__main__":
    _self_test()
