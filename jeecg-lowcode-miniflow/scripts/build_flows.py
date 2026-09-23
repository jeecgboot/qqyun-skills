# -*- coding: utf-8 -*-
"""批量建流程 —— 从一个声明式 flows.py 建完全部流程（规格驱动，从零生成，不需要任何既有应用作参考）。

    python build_flows.py --api-base URL --token TOKEN --tenant-id N --app-id A \
        --spec /path/flows.py [--only 流程名] [--dry-run]

`flows.py` 只写业务规格（`from flow_dsl import *` + `FLOWS = [...]`），**不写引擎代码**。
字段/表名一律中文，引擎自己换 code / model——见 `flow_dsl.py` 顶部。

## 为什么要有这个脚本（2026-09-15 实测）

63 条流程那一轮跑了 **55 分钟且 0 产出**，两个原因：
1. **逐条一轮的散打做法**：63 条 × ~44KB 节点配置写进模型输出 → 撞 32000 输出上限直接崩。
2. 全链路路径（`fast-full-chain.md`）当时**不指向 `batch-flows.md`**，agent 55 分钟后才偶然翻到。

本脚本把「机制」全部固化，agent 只剩「把规格翻译成 DSL」这一件不可避免的事：
  · 中文名 → code/model 解析（一次拉全，落盘复用）
  · **先子流程后主流程**：子流程 save → deploy → 注册 → 补 customProcessId → 再 deploy → 校验
  · 主流程的 `call_sub` 自动绑到**新建的**子流程 id
  · 幂等：同名已存在则跳过（可断点续跑）
  · 大 JSON 只在脚本内流转，**不进模型输出**；只打 `OK:` / `FAIL:`

2026-09-16 补齐 5 处「静默建错」（详见 `references/batch-flows.md`）：
  · 触发事件类型发的是数字键 `tableEventType` → 改成引擎真的读的字符串 `startEventType`
  · 触发条件 `startCondition` 从未下传 → 现在由 `flow(cond=[...])` 生成
  · `databranch` / `function` 两种节点没有分发 → 现在 `data_branch()` / `compute()`
  · `ref(node=...)` 一律把 formNodeId 写成 "start" → 现在指向真实节点 id
  · 子流程的流程变量三处都没传 → 现在 `subflow(params=)` / `call_sub(pass_=)` / `var()`

序列化依据：从 63 条实际在跑的流程 processJson 实测提取（见 flow_dsl.py 文末）。
"""
import argparse
import importlib.util
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import miniflow_creator as MC  # noqa: E402
from flow_dsl import OPT_SET, OPT_INC, OPT_DEC, APPLY_EXPR  # noqa: E402

# 表单设计的遍历只有一处实现（lowapp 的 engine-contract §12-b）：
# 这里要读 `options.options[].label/value`，必须用同一个 design_utils.iter_widgets，
# 不能就地再写一份 —— card 的子控件在 `list`、columns 是另一种历史形态，
# 抄错一处就静默读空（表现是「一个字段的选项都查不到」→ 值校验整段失效）。
try:
    from design_utils import iter_widgets  # noqa: E402
except ImportError:                       # 两个 skill 的 scripts 不在同一个 sys.path
    _LOWAPP_SCRIPTS = os.path.expanduser("~/.claude/skills/jeecg-lowcode-lowapp/scripts")
    if _LOWAPP_SCRIPTS not in sys.path:
        sys.path.insert(0, _LOWAPP_SCRIPTS)
    from design_utils import iter_widgets  # noqa: E402


def log(*a):
    print(*a, flush=True)


RULE = {"等于": "eq", "不等于": "ne", "大于": "gt", "大于等于": "ge",
        "小于": "lt", "小于等于": "le", "包含": "like",
        "属于": "in", "是其中一个": "in",
        # 引擎支持 not_in（trigger-types.md「全规则 DSL 已覆盖 eq/ne 之外规则：
        # gt/ge/lt/le/like/…/in/not_in/empty/not_empty」）。此前表里没有它，
        # 需求写「不是任何一个」时无处可写。
        "不属于": "not_in", "不是其中一个": "not_in", "不是任何一个": "not_in",
        "为空": "empty", "不为空": "not_empty"}


#: 条件条目的**控件族**（`type`/`valType`）由 `Resolver.family()` 给 ——
#  他表字段要沿 `showField` **递归解到最底层控件**，不是照抄自己的 `link-field`、
#  也不是一律写 `input`。历史与全案见 gotchas #104。
#  另：他表字段只有 **saveType='save'（存储数据）** 才能作条件，`view`（仅显示）不可（gotchas #86）。

#: 日期族条件值支持的字符串格式 → 本地时区零点毫秒
_DATE_FMTS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d")


def _date_ms(s):
    """日期字符串 → **本地时区毫秒时间戳 int**。

    日期类字段的条件值必须是毫秒时间戳：写日期字符串能 save/deploy，
    但**运行时恒不成立**（字段存储=毫秒，数字 vs 字符串比较必 false），
    设计器值框还会显示错日期（create-flow.md 日期类字段条件值 / gotchas #52）。
    """
    for fmt in _DATE_FMTS:
        try:
            return int(time.mktime(time.strptime(s.strip(), fmt)) * 1000)
        except ValueError:
            continue
    raise SystemExit(
        "FAIL: 日期族条件值 %r 认不出。请写毫秒时间戳 int（推荐）或 'YYYY-MM-DD'/'YYYY-MM-DD HH:MM[:SS]'；"
        "写别的字符串能 save/deploy 但条件恒不成立" % (s,))


def _cond_val(v):
    """queryItem.val：数字字面量写成字符串（gotchas #12；引擎 BigDecimal 两种都吃，设计器只按字符串回显）。"""
    if isinstance(v, bool) or isinstance(v, dict):
        return v
    if isinstance(v, (int, float)):
        return str(v)
    return v


def cond_value(family, v, rv):
    """条件值 → `(val, name)`，按控件族给形态。

    · `select-depart`：`val` 必须是**部门 id 数组**、`name` 是**名称数组**（两处都要写；
      写名称/None 设计器不识别、引擎按 id 比对 → 条件永不成立）。
      规格里写的是部门**名称**，翻成 id 是这里的职责（create-flow.md 部门段，2026-09-09 用户 UI 实测）。
    · `date`：`val` 要**毫秒时间戳 int**；日期字符串在这里转（见 `_date_ms`）。
    · `select-user`：`val`=**username 标量** + `name`=**显示名标量**，两处都要
      （create-flow.md:598，2026-09-09 用户 UI 实测「写 userId 或 id 数组设计器『未选中』」）。
      规格里写成 `(username, 显示名)` 二元组；**只给 username 会静默漏 name**，
      故这里拒绝裸字符串、要求显式给显示名。
    · 其余族：原样返回，`name` 留 None（`select` 多选就用名称，2026-09-20 实测渲染正常）。
    """
    if isinstance(v, dict):                       # 变量引用 / 运算结果：原样
        return v, None
    if family == "select-depart":
        # 写入侧 `field_value` 已把部门名翻成 id（2026-09-22 A2），条件侧同一值会再进这里：
        # 已是 id 的直接用、反查名称填 name；否则按名翻 id。不判就是「找不到部门「<id>」」（销售管理 R2 实测）
        items = [v] if isinstance(v, str) else [x for x in (v or [])]
        ids, names = [], []
        for x in items:
            if isinstance(x, str) and x.isdigit():
                ids.append(x); names.append(rv.dept_name(x))
            else:
                ids.append(rv.dept_id(x)); names.append(x)
        return ids, names
    if family == "date":
        return (v, None) if isinstance(v, int) and not isinstance(v, bool) else (_date_ms(v), None)
    if family == "select-user":
        if isinstance(v, (list, tuple)) and len(v) == 2:
            return v[0], v[1]
        raise SystemExit(
            "FAIL: select-user（人员）字段的条件值要写成 `(username, 显示名)` 二元组（如 "
            "('admin', '管理员')）—— `val` 收 username、`name` 收显示名，**两处都要**；"
            "只给 username 会让 `name` 为空，设计器不识别（create-flow.md:598）。收到：%r" % (v,))
    return v, None


def rule_code(rule_cn):
    """中文规则名 → 引擎 code。**认不出就报错，绝不回落。**

    ⚠️ 各处原先写的是 `RULE.get(rule_cn, "eq")`：规则名不在表里（例如「不属于」）
    会**静默变成「等于」**——条件正好写反，而 save/deploy/回读全绿，
    只有真跑（甚至跑完都看不出）才发现。宁可响亮失败。
    """
    if rule_cn not in RULE:
        raise KeyError("分支规则「%s」不在 RULE 表里（写了会静默退化成「等于」，条件就是反的）。"
                       "可用：%s" % (rule_cn, "、".join(sorted(RULE))))
    return RULE[rule_cn]


#: 非 tableEvent 触发要**原样透传到 config 顶层**的专属键（build_process_json 从顶层读）
TRIGGER_EXTRA = ("beginDateStr", "endDateStr", "timeCycleName", "timeCycle", "dayValue",
                 "hourType", "hourValues", "dayValues", "triggerField",
                 "plusDate", "plusDateUnit", "executionTime", "selectType")


def trigger_extras(start_type, spec):
    """每种 startType 的专属触发参数。**别照 tableEvent 抄——形状不一样。**

    依据 `references/trigger-types.md`「触发方式总表」各节。两个实测坑：
      · buttonEvent 的 `formTableId` **必须是 null**（`form_start_<code>` 是 tableEvent 的形状）；
        `startEventType` 也不是 "click"，按钮信号走 `button_signal:{流程id}`，示例写 "add|update"。
      · timerEvent 必须给 `timeCycleName`；置空会让 `attr.timeCycle` 变成 "custom"、周期不按预期执行。
    """
    if start_type == "buttonEvent":
        return {"startEventType": spec.get("startEventType") or "add|update",
                "formTableId": None,
                "inputParams": spec.get("inputParams") or []}
    if start_type == "timerEvent":
        out = {k: spec[k] for k in TRIGGER_EXTRA if spec.get(k) is not None}
        if not out.get("timeCycleName"):
            raise ValueError(
                "timerEvent「%s」缺 timeCycleName（如 '每天'/'每小时'）——置空会让 "
                "attr.timeCycle 变成 custom、触发无法按预期周期执行（trigger-types.md）。"
                % spec.get("name"))
        return out
    if start_type in ("manual", "userEvent"):
        return {k: spec[k] for k in TRIGGER_EXTRA if spec.get(k) is not None}
    return {}
# 触发事件类型。引擎读的是 **attr.startEventType**，值是字符串——
# 2026-09-16 之前这里发的是数字键 `tableEventType`，creator 那边读的是
# `startEventType`（取不到就落回默认 "add|update"）→ **63 条流程的触发事件
# 全部静默变成「新增|修改」**，这是「生成的流程触发时机全都不对」的根因。
EVENT = {"新增": "add", "修改": "update", "新增|修改": "add|update", "删除": "delete"}

# 引擎里「变量对象」的 formNodeType 是节点类型的另一种叫法，不是节点 type 本身
NODE_FORM_TYPE = {"get_one": "search", "get_more": "getMore",
                  "data_add": "plus", "operation": "function"}


class Resolver(object):
    """中文名 → code / model 的解析层。一次拉全，之后只查内存。"""

    def __init__(self, api, token, tenant, app):
        self.api, self.token = api, token
        self.tenant, self.app = str(tenant), str(app)
        self.forms = {}          # 表名 → code
        self.fields = {}         # (表名, 字段名) → {"model","type"}

    def load(self, tables):
        all_apps = MC.fetch_app_forms(self.api, self.token, self.tenant)
        me = None
        for a in (all_apps or []):
            if str(a.get("id")) == self.app:
                me = a
                break
        if not me:
            raise SystemExit("FAIL: 在租户里找不到 app=%s" % self.app)
        for f in (me.get("forms") or []):
            self.forms[f.get("name")] = f.get("code")
        missing = [t for t in tables if t not in self.forms]
        if missing:
            raise SystemExit("FAIL: 应用里没有这些工作表: %s" % "、".join(missing))
        n = 0
        for t in tables:
            # fetch_form_fields 返回单个 dict {中文名: {model,type,options}}
            ip = MC.fetch_form_fields(self.api, self.token, self.forms[t], self.tenant)
            for name, v in (ip or {}).items():
                # options 必须留：link-record 的 options 里有 sourceCode/titleField，
                # 「取本单关联明细」要靠它反查主表上那个关联控件的 model
                self.fields[(t, name)] = {"model": v["model"], "type": v["type"],
                                          "options": v.get("options")}
                n += 1
        log("OK:resolve %d 张表 / %d 个字段" % (len(tables), n))

    def link_to(self, master, detail):
        """主表上指向 detail 表的 link-record 控件 → (model, 字段中文名)。

        「取本单关联明细」必须带 linkFormTableField = 这个 model，否则引擎按
        「从工作表获取多条」处理（selectType=1），逐行子流程一行都取不到。
        """
        dcode = self.forms.get(detail)
        if not dcode:
            return None, None
        for (t, name), fi in self.fields.items():
            if t != master or fi.get("type") != "link-record":
                continue
            op = fi.get("options") or {}
            if isinstance(op, dict) and op.get("sourceCode") == dcode:
                return fi["model"], name
        return None, None

    def code(self, table):
        if table not in self.forms:
            raise KeyError("工作表不存在: %s" % table)
        return self.forms[table]

    def has(self, table, field):
        return (table, field) in self.fields

    def f(self, table, field):
        k = (table, field)
        if k not in self.fields:
            raise KeyError("%s 里没有字段 %s" % (table, field))
        return self.fields[k]

    def dept_id(self, name):
        """部门名 → 部门 id。

        select-depart 的条件值 `val` 要写**部门 id 数组**（`name` 才写名称数组）——
        写名称能 save/deploy 但引擎按 id 比对，**条件永不成立**、流程静默不触发
        （create-flow.md「部门选择控件（select-depart）的触发条件编码」2026-09-09 用户 UI 实测）。

        ⚠️ 两条都是坑：
        · 必须带 `X-Tenant-Id`，不带时返回各组织根、取值源不同（gotchas #61）；
        · 部门树是**嵌套**的（运维服务中心挂在「销售部」下），要递归展平，只取首层会漏。
        """
        self._load_depts()
        if name not in self._depts:
            raise SystemExit(
                "FAIL: 租户 %s 下找不到部门「%s」—— select-depart 的条件值必须是本租户**存在的**"
                "部门名（写错/跨租户都只会静默不匹配，不报错）。现有：%s"
                % (self.tenant, name, "、".join(sorted(self._depts))))
        return self._depts[name]

    def _load_depts(self):
        if getattr(self, "_depts", None) is not None:
            return
        try:
            r = MC.api_request(self.api, self.token, "/sys/sysDepart/queryTreeList",
                               method="GET", extra_headers={"X-Tenant-Id": self.tenant})
        except RuntimeError as e:
            raise SystemExit("FAIL: 取部门树失败（select-depart 条件值要部门 id）：%s" % e)
        res = r.get("result")
        if isinstance(res, dict):
            res = res.get("list")
        self._depts = {}

        def flat(ns):
            for x in (ns or []):
                if x.get("departName"):
                    self._depts[x["departName"]] = x.get("id")
                flat(x.get("children"))
        flat(res)

    def dept_name(self, did):
        """部门 id → 部门名（条件项的 `name` 要名称数组）。"""
        self._load_depts()
        for n, i in self._depts.items():
            if str(i) == str(did):
                return n
        raise SystemExit("FAIL: 租户 %s 下没有 id 为 %s 的部门（select-depart 值请写本租户部门名）" % (self.tenant, did))

    # ---- 显示名 → 表单真实存储值 ----

    def opt_labels(self, table):
        """表名 → {字段名: {显示名或值: 存储值}}（惰性，一张表只拉一次设计）。

        真值只有一处来源：表单设计里每个选项的 `value`（`label` 才是页面上显示的字）。
        `fetch_form_fields` 给的 `options` 是**裸值数组**（["0","1"]），标签在这一层
        已经被剥掉了 —— 所以过去只能拿到值、拿不到名，写规格的人就顺手写了显示名。
        要拿 label→value 对照，只有回读 `/desform/queryByCode` 的设计 JSON 一条路。
        """
        cache = getattr(self, "_labels", None)
        if cache is None:
            cache = self._labels = {}
        if table in cache:
            return cache[table]
        out = {}
        code = self.forms.get(table)
        dj = None
        if code:
            try:
                r = MC.api_request(self.api, self.token,
                                   "/desform/queryByCode?desformCode=%s" % code,
                                   method="GET")
                dj = ((r or {}).get("result") or {}).get("desformDesignJson")
            except Exception:                                        # noqa: BLE001
                dj = None
        if dj:
            design = json.loads(dj) if isinstance(dj, str) else dj
            for w in iter_widgets(design):
                name = w.get("name")
                opts = ((w.get("options") or {}).get("options")) or []
                m = {}
                for it in opts:
                    if not isinstance(it, dict) or it.get("value") is None:
                        continue
                    m[str(it["value"])] = it["value"]      # 值本身也收：写值幂等
                    if it.get("label") is not None:
                        m[str(it["label"])] = it["value"]
                if name and m:
                    out[name] = m
        elif self.fields:                     # 恒有字段时说明「本该有设计却没拉到」
            log("WARN:%s 的设计 JSON 没拉到（code=%r）—— 该表只能按「裸值」校验，"
                "显示名→存储值的翻译这轮不生效" % (table, code))
        cache[table] = out
        return out

    def formula_expr(self, table, field):
        """公式字段的表达式，占位符换成**字段中文名**（`$到货数量$-$不合格数量$`）；不是公式/读不到 → None。

        给 flow_rules 规则 3 用：公式值不能直接累加、运算节点直读公式字段也取不准，
        只能把公式**展开成底层数字字段**在流程里重算 —— 所以要拿到表达式本身。
        """
        cache = getattr(self, "_fexpr", None)
        if cache is None:
            cache = self._fexpr = {}
        if table not in cache:
            out, code = {}, self.forms.get(table)
            try:
                r = MC.api_request(self.api, self.token,
                                   "/desform/queryByCode?desformCode=%s" % code, method="GET")
                dj = ((r or {}).get("result") or {}).get("desformDesignJson")
                design = json.loads(dj) if isinstance(dj, str) else (dj or {})
            except Exception:                                        # noqa: BLE001
                design = {}
            ws = list(iter_widgets(design))
            by_model = {w.get("model"): w.get("name") for w in ws if w.get("model")}
            for w in ws:
                o = w.get("options") or {}
                if w.get("type") == "formula" and o.get("mode") == "CUSTOM" and o.get("expression"):
                    ex = o["expression"]
                    for m, nm in by_model.items():
                        ex = ex.replace("$%s$" % m, "$%s$" % nm)
                    out[w.get("name")] = ex
            cache[table] = out
        return cache[table].get(field)

    def field_value(self, table, field, v):
        """把规格里写的**显示名**翻成表单**真实存储值**。

        ⚠️ 2026-09-21 用户实测报障：`cond=[("入库确认", "等于", "是")]` 里写的
        「是」是**页面上显示的字**，而表单存的是字典值 `"0"`。落库的
        `SuperQueryItem.val="是"`，引擎拿它去 Mongo 里比 `"0"` → **恒不匹配**，
        日志是「匹配不到数据，不满足触发条件！」，流程静默不触发。
        写字段（update/add）同理：把「是」当值写进去，页面上看着是空的。
        全应用的下拉/字典/单选字段都吃这一刀，不是某一两条流程的事。

        认不出就**报错**：静默放过 = 把「永不成立的流程」再建一遍。
        """
        if isinstance(v, dict):           # 变量对象（ref/var/result…）：不是字面量，原样
            return v
        # 「这个字段有没有固定选项」以 fetch_form_fields 的 options 为准：
        # 它是**裸值数组**，拿得到、但**没有标签** —— 正好当「该字段是否枚举型」的判据。
        # 只按设计 JSON 判会把「设计没拉到」误当成「字段是自由文本」，静默放过。
        declared = (self.fields.get((table, field)) or {}).get("options")
        # ⚠️ 只有**列表**形态的 options 才是「固定选项」。他表字段（link-field）的 options 是个
        # **dict**（{fieldType, saveType, showField}）—— 当成选项数组迭代会把这三个键名当成
        # 合法值，于是「销售部门 属于 运维服务中心」这类条件直接报「不是这个字段的合法选项，
        # 可选：fieldType、saveType、showField」，任何对他表字段写字面量的条件都建不出来
        # （2026-09-21 销售管理实测）。非列表一律视为「没有固定选项」，交给 cond_value 按族编码
        # （select-depart 就是在那里把部门名翻成部门 id 的）。
        if not isinstance(declared, (list, tuple)):
            declared = []
        m = dict(self.opt_labels(table).get(field) or {})
        for x in (declared or []):
            m.setdefault(str(x), x)
        if not m:
            # 部门控件没有「选项」，但写入值必须是部门 id（数组）——写部门名会落成文本，
            # 下游按部门比较的流程恒不命中（2026-09-22 销售管理实测）。条件侧 cond_value 早就翻了。
            try:
                fam = self.family(table, field)
            except SystemExit:
                fam = None
            if fam == "select-depart":
                def _dep(x):
                    return x if (not isinstance(x, str) or x.isdigit()) else self.dept_id(x)
                if isinstance(v, str) and v:
                    return [_dep(v)]
                if isinstance(v, list):
                    return [_dep(x) for x in v]
            return v                      # 真的没有固定选项（文本/数字/日期…）：原样
        if isinstance(v, list):           # 多选：逐项翻
            return [self.field_value(table, field, x) for x in v]
        if not isinstance(v, str):
            return v
        if v in m:
            return m[v]
        pairs = sorted(set((k, val) for k, val in m.items() if k != str(val)))
        raise SystemExit(
            "FAIL: %s.%s 的值 %r 不是这个字段的合法选项。\n"
            "  这里必须写**表单真实存储的值**，不是页面上的显示名。可选：%s"
            % (table, field, v,
               "、".join("%s→%r" % kv for kv in pairs[:24])
               or "、".join(sorted(m)[:24])))

    def _index(self):
        """`字段 model → (表名, 字段名, field)` 全局索引（惰性，只拉一次）。

        链式他表字段要沿 `showField` 解到**最底层**控件，而 `showField` 指向的那张表
        未必在本流程 spec 里 —— 所以索引拉的是**应用里全部工作表**，不是 `load()` 那几张。
        """
        if getattr(self, "_idx", None) is None:
            self._idx = {}
            for tname, tcode in self.forms.items():
                try:
                    fm = MC.fetch_form_fields(self.api, self.token, tcode, self.tenant) or {}
                except Exception:
                    continue
                for fn, meta in fm.items():
                    if meta.get("model"):
                        self._idx[meta["model"]] = (tname, fn, meta)
        return self._idx

    def family(self, table, field, _seen=None):
        """条件条目的**控件族** —— 他表字段要递归解到最底层控件。

        ⚠️ 三层套娃都得处理（2026-09-20 本应用实测）：
        · 一指文本   `目标客户.单位名称`  fieldType=`input`          → `input`
        · 一指部门   `机会目录.销售部门`  fieldType=`select-depart`  → `select-depart`
        · **链式**    `回款记录.销售部门` → `销售合同.销售部门` → `机会目录.销售部门`
                     中间层 fieldType **就是字符串 `'link-field'`**，照抄它正好落回
                     「设计器不认这个族」的坑 → 必须继续沿 `showField` 往下解。

        解不到最底层就**报错**，禁止回落（回落=猜，猜 `input` 就是再踩一遍 gotchas #104）。
        """
        return self._family(self.f(table, field), table, field, _seen)

    def _family(self, tf, table, field, _seen=None):
        """`family()` 的递归体。**沿着 meta 走，不再回头查 `self.f()`。**

        为什么必须分成两层：链路下一跳的表是顺着 `_index()`（全应用 model 索引）找到的，
        **不一定在 `load()` 加载过的集合里** —— `load()` 只加载 spec 里点名的表，
        而「他表字段的来源表」是解析过程中才发现的。
        2026-09-20 实测：`销售产品明细.产品编码` 是链式他表字段，来源表 `产品销售价格表`
        没被加载 → 递归里 `self.f("产品销售价格表", "产品编码")` 直接 KeyError
        「产品销售价格表 里没有字段 产品编码」，整条子流程建不出来。
        """
        if tf.get("type") != "link-field":
            return tf.get("type")
        op = tf.get("options") or {}
        ft = op.get("fieldType") if isinstance(op, dict) else None
        seen = _seen if _seen is not None else set()
        m = tf.get("model")
        if m in seen:
            raise SystemExit("FAIL: 他表字段链成环（%s.%s），无法判定条件族" % (table, field))
        seen.add(m)
        if ft == "link-field":
            nxt = self._index().get(op.get("showField"))
            if not nxt:
                raise SystemExit(
                    "FAIL: %s.%s 是链式他表字段，但 showField=%r 在应用里找不到对应字段，"
                    "无法解到最底层控件族（禁止猜）" % (table, field, op.get("showField")))
            return self._family(nxt[2], nxt[0], nxt[1], seen)
        if not ft:
            raise SystemExit(
                "FAIL: %s.%s 是他表字段但解析不出 `options.fieldType`，无法判定条件族。"
                "**禁止猜**（猜成 input 会让设计器给错运算符列表、条件静默不匹配）——"
                "先查 /desform/api/fields/<code> 的 options 有没有 fieldType" % (table, field))
        return ft


def _iso_duration(minutes):
    """分钟数 → ISO 8601 时长。整小时/整天走预置（设计器认得），其余走自定义。"""
    if minutes and minutes % 1440 == 0:
        return "P%dD" % (minutes // 1440)
    if minutes and minutes % 60 == 0:
        return "PT%dH" % (minutes // 60)
    return "PT%dM" % minutes


class Builder(object):
    def __init__(self, rv):
        self.rv = rv
        self.task_seq = 0
        self.sub_ids = {}         # 子流程名 → {"db_id","process_key","process_name"}
        self.built = {}           # 节点名 → {"id","type"}（引用别的节点结果时要用它的 id）
        self.var_targets = {}     # (子流程名, 参数名) → (表, 字段)：call_sub 传字面量时按目标字段翻存储值
        self._cur_name = ""
        self._ctx = ""            # 当前流程的上下文表（同名匹配的条件取值就用它）
        # 最近一个「取本单关联明细」节点 / 「新增记录」节点——call_sub 的
        # 数据对象与「传 record id」要指回它们（见 _node 的 subprocess 分支）
        self._last_get_more = None
        self._last_add = None

    def nid(self):
        self.task_seq += 1
        return "task%d%03d" % (int(time.time() * 1000), self.task_seq)

    # ---- 条件 ----
    def _cond_items(self, cond, table):
        """DSL 条件 → 引擎 queryItems。

        两种写法都收：
          · "字段名"           → 同名匹配：拿**上下文行**同名字段的值去比
          · (字段, 规则, 值)   → 显式：规则用中文，值可以是裸值 / ref() / var()
        """
        items = []
        for c in (cond or []):
            if isinstance(c, str):
                fname, rule_cn, val = c, "等于", None
                if not self.rv.has(table, fname):
                    # 目标表没这个字段 → 说明写错了，早点报，别等到运行时静默不匹配
                    raise KeyError("%s 里没有字段 %s（条件写的是目标表的字段名）"
                                   % (table, fname))
                val = {"$ref": fname, "$node": "start"}
            elif len(c) == 2:                    # ("字段", "为空") 这类不带值的写法
                fname, rule_cn, val = c[0], c[1], None
            else:
                fname, rule_cn, val = c
            tf = self.rv.f(table, fname)
            v = self.value(val, self._ctx, table)
            # 字面量要先翻成**表单真实存储值**（写的是「是」、库里存的是 "0" —— 见
            # Resolver.field_value）。变量对象（ref/var）不走这里：那是运行期取值。
            # 「为空 / 不为空」不带值：拿空串去比选项表必然「不是合法选项」而报错
            # （2026-09-22 销售 R3：「客户类型 为空」这一支根本写不出来）
            if rule_cn not in ("为空", "不为空"):
                v = self.rv.field_value(table, fname, v)
            fam = self.rv.family(table, fname)
            v, nm = cond_value(fam, v, self.rv)
            items.append({
                "rule": rule_code(rule_cn), "ruleName": rule_cn,
                "valueType": 2 if isinstance(v, dict) else "1",
                "val": _cond_val(v), "name": nm if nm is not None else fname,
                "field": tf["model"], "columnName": fname,
                "type": fam,
                "valType": "variable" if isinstance(v, dict) else fam,
            })
        return items

    def trigger(self, spec):
        """主流程的**触发条件**。空列表 = 无条件（任何一次增删改都跑）。"""
        if not spec.get("cond"):
            return []
        self._ctx = spec["table"]
        return [{"id": MC.gen_id(), "matchType": "AND",
                 "queryItems": self._cond_items(spec["cond"], spec["table"])}]

    def watch_fields(self, spec):
        """主流程的**监控字段** → model 数组。空 = 任何一次修改都算。"""
        names = spec.get("watch") or []
        if not names:
            return []
        if "修改" not in str(spec.get("on", "")):
            raise KeyError("flow(%r)：写了 watch 但 on=%r —— 监控字段只在「修改」触发时起作用"
                           % (spec["name"], spec.get("on")))
        return [self.rv.f(spec["table"], n)["model"] for n in names]

    # ---- 值 ----
    def value(self, v, ctx_table, table=None):
        """把 DSL 值解析成落库形态：固定值 或 变量对象。"""
        if isinstance(v, dict) and "$var" in v:
            # 流程变量（子流程收到的参数）：名字就是 subflow(params=[...]) 里那一个
            n = v["$var"]
            return {"variableValue": n, "variableName": n, "formNodeType": "variable"}
        if isinstance(v, dict) and "$record_id" in v:
            # 「传 record id」= 上游「新增记录」节点建出来的那条记录的 id。
            # 落库形态与普通字段引用不同（variableName="记录id" / variableValue="_id" /
            # formNodeType="plus"），是线上模版实测的原样，别套用 ref() 的形状。
            nm = v["$record_id"] or (self._last_add or {}).get("name")
            b = self.built.get(nm) if nm else None
            add = self._last_add
            if not add or (nm and add["name"] != nm):
                raise KeyError("record_id(%r)：只能指向前面 add() 建的「新增记录」节点"
                               % nm)
            return {"variableValue": "_id", "formTableCode": add["code"],
                    "variableName": "记录id", "formNodeType": "plus",
                    "formNodeId": (b or {}).get("id") or add["id"],
                    "formNodeName": add["name"]}
        if isinstance(v, dict) and "$result" in v:
            # 运算节点的结果。formTableCode 必须是 **function-{funType}**（不是恒定的
            # function-fun）、record 型 operationMode 必须是 everyTime —— 写错设计器
            # 字段源解析不到（node-types「四」4.4.1 要点② / 「十八」18.2）。
            b = self.built.get(v["$result"])
            if not b or b["type"] != "operation":
                raise KeyError("result(%r)：找不到这个运算节点（只能引用前面 compute() 建的）"
                               % v["$result"])
            ft = b.get("fun_type") or "fun"
            return {"formNodeId": b["id"], "formNodeName": v["$result"],
                    "operationMode": "everyTime" if ft == "record" else "cache",
                    "variableName": "结果",
                    "formNodeType": "function", "variableValue": "result",
                    "decimals": v.get("$decimals", 2),
                    "formTableCode": "function-%s" % ft}
        if isinstance(v, dict) and "$ref" in v:
            node = v["$node"]
            if node in ("start", "子流程", "工作表事件触发"):
                # ⚠️ 子流程里「输入行」的合法名是 **"子流程"**，不是「工作表事件触发」
                # （那个节点在子流程里根本不存在 → 幽灵引用，设计器下拉选不到）。
                # 依据：金标样例 example/入库审批修改库存示例.md 全篇 `formNodeName:"子流程"`；
                # check_node_contract 也显式 `if is_sub: names.add("子流程")`
                # （注释原文「输入行在子流程内的合法别名」）。
                # 注意别写成「子流程触发」——那是 start 节点在**画布上的显示名**
                # （miniflow_creator._start_node_name_map），不是值引用该用的名字。
                start_name = ("子流程" if getattr(self, "_is_sub", False)
                              else "工作表事件触发")
                src_table, ftype, fid, fname = (ctx_table, "table", "start",
                                                start_name)
            else:
                b = self.built.get(node)
                if not b:
                    raise KeyError("ref(%r, node=%r)：这个节点还没建（只能引用前面的节点）"
                                   % (v["$ref"], node))
                # formNodeId 必须指向**真正产出这个字段的节点**；早先这里一律写 "start"，
                # 字段名对了、来源指错了——运行时读的是上下文行，值永远不对。
                src_table = b.get("table") or ctx_table
                ftype = NODE_FORM_TYPE.get(b["type"], "search")
                fid, fname = b["id"], node
            fi = self.rv.f(src_table, v["$ref"])
            # fieldType 不能少：线上模版里引用型取值固定 7 键
            # （fieldType/formNodeId/formNodeName/formNodeType/formTableCode/variableName/variableValue）
            return {"variableValue": fi["model"], "formTableCode": self.rv.code(src_table),
                    "variableName": v["$ref"], "formNodeType": ftype,
                    "formNodeId": fid, "formNodeName": fname,
                    "fieldType": fi["type"]}
        if isinstance(v, dict) and ("$inc" in v or "$dec" in v):
            # flow_dsl.inc()/dec() 的标记：脱壳解析，optType 在 node() 里按字段补
            return self.value(v["$inc"] if "$inc" in v else v["$dec"], ctx_table, table)
        if isinstance(v, dict) and "$lit" in v:
            return v["$lit"]
        if isinstance(v, dict) and "$calc" in v:
            raise NotImplementedError(
                "flow_dsl.calc() 已废弃：算术请用 compute()（流程内运算）或工作表公式字段。")
        return v

    # ---- 办理人分组（审批节点与填写节点共用）----
    def groups(self, spec, dflt="admin"):
        """DSL 的 users/roles/exp → 引擎 approverGroups。

        `exp` 是**表达式取人**：`${applyUserId}` → 「获取发起人」这类语义名。
        `dflt` 决定「谁都没点名」时的兜底：审批节点兜底 admin，填写节点兜底发起人。
        """
        groups = []
        # 办理人 = 表单字段（`spec["form_field"] = (表, 字段)`，元组或 dict 都收）。
        # 落库形态是四种里的第 ③/④ 种：`candidateUsers`（**复数**）+
        # `assigneeByVariable`。⚠️ variableContent 必须是**原生七键**
        # （`fieldName` 才是字段 model，另带 formTableCode/formTableId/nodeId/nodeType 四个上下文键），
        # 键名写错时 save/deploy 全绿、设计器也看不出，但任务解析不到办理人 → 谁都不进待办
        # （2026-09-20 实测：`field`+`type` 形态的 3 条实例全部无人可办）。
        # ⚠️ 部门/岗位类字段必须另带 `isNeedTranslateToUserIds`，
        # 缺它部门**不展开成用户** → 任务谁都收不到（见 fast-full-chain「审批组四种形态」/ gotchas #90）。
        ff = spec.get("form_field")
        if ff:
            if isinstance(ff, dict):
                tbl, fld, is_dept = ff.get("table"), ff.get("field"), ff.get("dept", True)
            else:
                tbl, fld = ff[0], ff[1]
                is_dept = ff[2] if len(ff) > 2 else True
            tf = self.rv.f(tbl, fld)
            code = self.rv.code(tbl)
            # 引擎 MinFlowUtils:1094-1096 只认 fieldType 字面量 select-user / select-depart：
            # 他表字段落 `link-field` 两边都不进 → 部门 id 被当账号派发，**无人收到待办**（静默）。
            # 所以这里必须沿他表字段链解到最底层控件族（Resolver.family），解不出就报错。
            fam = self.rv.family(tbl, fld)
            if fam not in ("select-user", "select-depart"):
                raise SystemExit("FAIL: 办理人字段 %s.%s 解到的控件族是 %r，引擎只接受 select-user / select-depart"
                                 "（他表字段请指向成员/部门控件）" % (tbl, fld, fam))
            var_content = {"formTableCode": code, "formTableId": "form_start_%s" % code,
                           "nodeId": "start", "nodeType": "table",
                           "fieldName": tf["model"], "fieldType": fam,
                           "fieldLabel": fld}
            if is_dept:
                var_content["isNeedTranslateToUserIds"] = True
            groups.append({
                "approverType": "candidateUsers", "assigneeType": "assigneeByVariable",
                "approverIds": [], "approverNames": [],
                "approverId": "", "approverName": "",
                "deptIds": [], "deptNames": [], "roleIds": [], "roleNames": [],
                "postIds": [], "postNames": [],
                "expressionsIds": [], "expressionsNames": [],
                "variableTitle": [fld],
                "variableContent": [var_content],
                "formTableType": "table", "levelMode": 1,
            })
        who = spec.get("who")
        if who:
            # 名称与表达式 id 必须**成对**（见 flow_dsl.APPLY_EXPR）：
            # 只改 expressionsNames 不改 id，卡片上写的和实际取的人会对不上。
            if who not in APPLY_EXPR:
                raise KeyError("办理人只支持 %s，收到 %r"
                               % ("/".join(APPLY_EXPR), who))
            eid, ename = APPLY_EXPR[who]
            groups.append({"approverType": "candidateUser", "assigneeType": "assigneeByExp",
                           "approverIds": [], "approverNames": [], "deptIds": [],
                           "roleIds": [], "postIds": [],
                           "expressionsIds": [eid],
                           "expressionsNames": [ename], "levelMode": 1,
                           "approverId": "", "approverName": "", "variableTitle": [],
                           "variableContent": "", "formTableType": ""})
        if spec.get("users"):
            groups.append({"approverType": "candidateUser", "assigneeType": "assigneeByName",
                           "approverIds": ["user.%s" % u for u in spec["users"]],
                           "approverNames": list(spec["users"]), "levelMode": 1,
                           "approverId": "", "approverName": "", "deptIds": [], "roleIds": [],
                           "postIds": [], "expressionsIds": []})
        if spec.get("roles"):
            groups.append({"approverType": "candidateGroups", "assigneeType": "assigneeByName",
                           "roleIds": list(spec["roles"]), "roleNames": list(spec["roles"]),
                           "levelMode": 1, "approverId": "", "approverName": "",
                           "approverIds": [], "deptIds": [], "postIds": [], "expressionsIds": []})
        if not groups:
            if dflt == "apply":
                eid, ename = APPLY_EXPR["发起人"]
                return [{"approverType": "candidateUser", "assigneeType": "assigneeByExp",
                         "approverIds": [], "approverNames": [], "deptIds": [], "roleIds": [],
                         "postIds": [], "expressionsIds": [eid],
                         "expressionsNames": [ename], "levelMode": 1,
                         "approverId": "", "approverName": "", "variableTitle": [],
                         "variableContent": "", "formTableType": ""}]
            groups.append({"approverType": "candidateUser", "assigneeType": "assigneeByName",
                           "approverIds": ["user.admin"], "approverNames": ["admin"],
                           "levelMode": 1, "approverId": "", "approverName": "",
                           "deptIds": [], "roleIds": [], "postIds": [], "expressionsIds": []})
        return groups

    # ---- 更新对象自动绑定 ----
    def _auto_source(self, table):
        """`update()` 没写 source 时，绑到**前面最近的、取同一张表的 get_one**。

        设计器里「更新记录」的「更新对象」= 上游「取单条数据」的结果，不是触发行。
        DSL 早先一律落 "start"（= 触发行），于是最典型的
        `get_one(表) → update(表, {...})` 被配成「更新触发流程的那一行」：
        面板上「更新对象」显示错、运行时更新不到刚查到的那行（2026-09-20 用户报障）。

        找不到同表 get_one 时返回 "start"：审批流写回单据状态就是这种
        （start → approver → update(触发表) 前面没有 get_one），语义正确。
        """
        for nm, reg in reversed(list(self.built.items())):
            if reg["type"] == "get_one" and reg.get("table") == table:
                return nm
        return "start"

    # ---- 单个节点 ----
    def node(self, spec, ctx_table):
        """建一个节点，并登记「节点名 → id」，好让后面的节点能用 `ref(node=...)` 指它。"""
        self._ctx = ctx_table
        if "id" not in spec:
            spec = dict(spec, id=self.nid())     # 自己发 id，creator 侧会沿用
        n = self._node(spec, ctx_table)
        if isinstance(n, dict):
            # 自己发出去的 id 回填进节点，creator 侧会原样沿用——
            # 这样 `ref(node=...)` / `result(...)` 拿到的 id 与最终落库的一致
            n.setdefault("id", spec["id"])
            if n.get("name"):
                reg = {"id": n["id"], "type": n["type"],
                       "table": spec.get("table") or ctx_table}
                # 运算节点要记住 funType：下游引用它的结果时，formTableCode 得写
                # function-{funType}、record 型的 operationMode 还得是 everyTime
                # （node-types「四」4.4.1 / 18.2）。丢了这两样设计器解析不到字段源。
                if n["type"] == "operation":
                    reg["fun_type"] = n.get("funType") or "fun"
                # 同理记下 get_more 的 getDataType：下游「统计条数」必须与它一致，
                # 否则读错存储、运行时 ClassCastException（2026-09-20 实测）
                if n["type"] == "get_more":
                    reg["get_data_type"] = (
                        1 if (spec.get("fetch_mode") or "cache") == "cache" else 2)
                # 「取本单关联明细」要额外记住主表/明细表 code：后面 call_sub 的
                # 数据对象是按这四个值拼的（via=节点名时用得上）
                if (n["type"] == "get_more" and self._last_get_more
                        and self._last_get_more["name"] == n["name"]):
                    reg["main_code"] = self._last_get_more["main"]
                    reg["detail_code"] = self._last_get_more["code"]
                    reg["detail_table"] = self._last_get_more["table"]
                self.built[n["name"]] = reg
        return n

    def _node(self, spec, ctx_table):
        t = spec["type"]

        if t == "get_one":
            tb = spec["table"]
            conds = self._cond_items(spec.get("cond"), tb)
            return {"type": "get_one", "name": spec["name"], "getType": 1,
                    "formTableCode": self.rv.code(tb), "formTableName": tb,
                    # 显式写死 formTableId = form_<本节点 id>_<表 code>（node-contract §9）。
                    # 不写时靠 creator 的 selectType=1 默认分支推导：值一样，但推导过程
                    # 不可见，上游默认一变就静默漂走。
                    "formTableId": "form_%s_%s" % (spec["id"], self.rv.code(tb)),
                    "conditions": conds,
                    # 3 = 中止流程，或继续执行查找结果分支（配 data_branch）
                    "emptyAction": {"继续": 0, "新增": 1, "中止": 2,
                                    "分支": 3}.get(spec.get("empty"), 0)}

        if t == "get_more":
            tb = spec["table"]
            # —— 取「本单的关联明细」：selectType=3「从单条记录获取关联记录」——
            # 引擎认的是 selectType=3 + linkFormTableField(=主表 link 控件的 model)
            # + formTableId=form_start_<主表code> + limitNum 留空。
            # 只发 getType=1「从工作表获取多条」时：面板显示错、逐行子流程一行都取不到
            # （2026-09-17 实测：批量建的 63 条流程全栽在这里）。
            if str(spec.get("from") or "") in ("start", "工作表事件触发"):
                lmodel, lname = self.rv.link_to(ctx_table, tb)
                # ⚠️ 静默故障防线（2026-09-22 销售管理实测）：from_='start' 但主表上找不到
                # 指向该明细表的关联控件时，旧行为是**静默降级**成 getType=1「从工作表获取多条」——
                # selectType 停在 1、linkFormTableField 为空、_last_get_more 不登记，
                # 于是下游 call_sub「选择数据对象」空白、逐行子流程一行都取不到，
                # 而 save/deploy 全绿（同上文 2026-09-17 那 63 条的坑）。这里直接报错。
                if not lmodel:
                    raise KeyError(
                        "get_more(%r, from_='start')：主表 %r 上没有解析到指向明细表 %r 的关联记录控件 —— "
                        "「从单条记录获取关联记录」取不到数据对象。\n"
                        "  查两处：① 主表 %r 上确实存在一条关联到 %r 的关联记录字段（子表/关联工作表都算）；"
                        "② get_more 的第一个参数写的是那张明细表。"
                        % (spec["name"], ctx_table, tb, ctx_table, tb))
                self._last_get_more = {"id": spec["id"], "code": self.rv.code(tb),
                                       "name": spec["name"],
                                       "main": self.rv.code(ctx_table),
                                       "table": tb}
                return {"type": "get_more", "name": spec["name"],
                        "selectType": 3, "sourceTaskId": "start",
                        "formTableCode": self.rv.code(ctx_table),
                        "formTableName": ctx_table,
                        "relationField": lmodel,
                        "limitCount": None,          # 关联明细不设条数上限
                        "conditions": [],
                        "attr": {"linkFormTableCode": self.rv.code(tb),
                                 "linkFormTableName": tb, "linkFormTableType": 1,
                                 "getDataType": 1, "noDataType": 1,
                                 "formTableSourceNodeType": "table"}}
            conds = self._cond_items(spec.get("cond"), tb)
            # ⚠️ `fetchMode` → `getDataType`（miniflow_creator:1302：cache=1 / realtime=2）。
            # 这里早先写死了 `"realtime"`（=2），而「运算-统计条数」节点读的是 **cache(1)**
            # 那份存储 —— 2026-09-20 实测事故：子流程的 统计条数 节点直接抛
            # `ClassCastException: Cannot cast java.util.ArrayList to java.lang.String`
            # （FunctionDelegate.getRecordSize 按 String 读，拿到的却是 realtime 存的 List），
            # 子流程死在这一步，后面的分支/新增/更新**全部没执行**，而 save/deploy/契约检查
            # 一切全绿。默认跟库默认（":1301 fetch_mode 默认 cache"）一致用 cache；
            # 确需实时查询时在规格里写 `fetch_mode="realtime"`。
            d = {"type": "get_more", "name": spec["name"], "getType": 1,
                 "formTableCode": self.rv.code(tb), "formTableName": tb,
                 "conditions": conds,
                 "fetchMode": spec.get("fetch_mode") or "cache",
                 "limitCount": spec.get("limit") or 0}
            if spec.get("sort"):
                sf = self.rv.f(tb, spec["sort"])
                d["sortField"], d["sortType"] = sf["model"], "desc"
            return d

        if t == "data_update":
            tb = spec["table"]
            # 更新目标行由谁产出：formTableSourceTaskId 指向那个节点的 id，
            # formTableId 跟着写成 form_<来源节点id>_<表code>，formTableSourceNodeType
            # 取 search/plus（线上 44 条实测：search 35 / plus 9，没有一例是 "table"）。
            # source 不传（= DSL update() 的默认）时自动绑到前面最近的、取同一张表的
            # get_one。早先写成 `spec.get("source") or "start"`，把「没写」和「明写 start」
            # 并成一种 → get_one(表) → update(表) 全落成「更新触发行」。
            src = spec.get("source")
            if src is None:
                src = self._auto_source(tb)
            if src in ("start", "工作表事件触发"):
                src_id, src_type = "start", "table"
            else:
                b = self.built.get(src)
                if not b:
                    raise KeyError("update(%r, source=%r)：这个节点还没建"
                                   % (spec["name"], src))
                src_id = b["id"]
                src_type = NODE_FORM_TYPE.get(b["type"], "search")
            ufs = []
            for fname, v in (spec["mapping"] or {}).items():
                tf = self.rv.f(tb, fname)
                if isinstance(v, dict) and "$var" in v:
                    self.var_targets[(self._cur_name, v["$var"])] = (tb, fname)
                # optType 逐字段：inc()→"2" 增加 / dec()→"3" 减少 / 其余→"1" 设值。
                # 没有它，「库存自动累加维护」只能写成覆盖，语义是错的。
                opt = OPT_SET
                if isinstance(v, dict) and "$inc" in v:
                    opt = OPT_INC
                elif isinstance(v, dict) and "$dec" in v:
                    opt = OPT_DEC
                val = self.rv.field_value(tb, fname, self.value(v, ctx_table))
                # 变量对象还要带全两样，否则设计器解析不完整（二者都只在真跑/前端才暴露）：
                #   ① function 型（运算结果）要 `fieldType` = **写入字段的类型**；
                #   ② 写**日期字段**要 `options.format`（值取该字段自己的 format）。
                # check_node_contract 对这两条分别判「运算结果引用不完整」「写日期字段缺
                # options.format」；金标样例见 example/分支示例.md。
                if isinstance(val, dict):
                    if val.get("formNodeType") == "function":
                        val.setdefault("fieldType", tf["type"])
                # ⚠️ 引擎 UpdateRecordDelegate.getUpdateValue：number/integer 走 Integer.parseInt(toString())，
                # 任何带小数点的值（公式落库的 20.0、运算结果 7.0、甚至旧值本身）都解析成 0 → 「累加把原值冲成 0」；
                # money 走 BigDecimal 安全。所以 optType 增/减 且目标是 number/integer 时，条目 type 写 money
                # 借 BigDecimal 路径。⚠️ 引擎读的是条目的 **fieldType**（UpdateRecordDelegate:161
                # `String type = jsonObject.getString("fieldType")`），不是 `type` —— 2026-09-21 第一版只改了
                # `type`，真机回归「查到→累加公式值」仍得 0，改到 fieldType 后通过。两键同写。
                # formula/summary/link-field 目标在该方法里哪个分支都不进、返回 null → 字段被清空，直接拦下。
                if opt in ("2", "3") and tf["type"] in ("formula", "summary", "link-field", "text-compose"):
                    raise SystemExit("FAIL: update(%r) 对「%s」做增加/减少 —— 它是 %s 字段，引擎会把它清空"
                                     "（getUpdateValue 返回 null）。累加只能落在 数字/整数/金额 字段上"
                                     % (spec["table"], fname, tf["type"]))
                _eng_type = "money" if (opt in ("2", "3") and tf["type"] in ("number", "integer")) else tf["type"]
                uf_item = {"field": tf["model"], "val": val, "fieldType": _eng_type,
                           "type": _eng_type, "optType": opt,
                           "valueType": 3 if isinstance(val, dict) else None,
                           "valType": "variable" if isinstance(val, dict) else None}
                if isinstance(val, dict) and "date" in str(tf["type"]):
                    uf_item["options"] = {
                        "format": (tf.get("options") or {}).get("format") or "yyyy-MM-dd"}
                ufs.append(uf_item)
            d = {"type": "data_update", "name": spec["name"],
                 "formTableCode": self.rv.code(tb), "formTableName": tb,
                 "formTableSourceTaskId": src_id,
                 "formTableSourceNodeType": src_type,
                 "formTableId": "form_%s_%s" % (src_id, self.rv.code(tb)),
                 "updateFields": ufs}
            # ⚠️ 用 get_more 的结果**批量更新**时，还必须带 formTableSourceGetDataType
            # （= 源 get_more 的 getDataType），漏了引擎**静默不写库**（create-flow.md
            # 「数据批量更新」组合 E2 / node-types「三」数据来源速查：『否则批量更新静默
            # 无效』）。2026-09-20 实测：子流程「更新客户联系人」接口全绿、一个字段没改。
            # ⚠️ 必须放进 **attr**：`build_data_update_node` 的 attr 是「固定键 +
            # node_config['attr'] 透传」，写在节点顶层的键会被**直接丢掉**（静默）。
            if src_type == "getMore":
                d.setdefault("attr", {})["formTableSourceGetDataType"] = \
                    b.get("get_data_type", 1)
            return d

        if t == "data_add":
            tb = spec["table"]
            # 必须是 formModel（{目标字段 model: 取值}），不是 addFields——
            # 发 addFields 时 creator 侧取不到，落库 formModel 为空：
            # 设计器「新增记录」面板全空、运行时建出空记录（2026-09-17 实测）。
            form_model = {}
            for fname, v in (spec.get("mapping") or {}).items():
                tf = self.rv.f(tb, fname)
                if isinstance(v, dict) and "$var" in v:
                    self.var_targets[(self._cur_name, v["$var"])] = (tb, fname)
                form_model[tf["model"]] = self.rv.field_value(
                    tb, fname, self.value(v, ctx_table))
            # 登记：后面 call_sub 的「传 record id」要指向它
            self._last_add = {"id": spec["id"], "name": spec["name"],
                              "code": self.rv.code(tb)}
            # ⚠️ 建出来的是**单条新增**（addDataType=1，来源＝本节点自己）。若事后要把它
            # 改成**批量逐条新增**（`addDataType=2`，get_more 几条建几条），`attr` 里必须
            # **同时**补上这 5 个 source 键，一个都不能少：
            #   formTableSourceTaskId       = 上游 get_more 节点 ID
            #   formTableSourceNodeType     = "getMore"
            #   formTableSourceCode         = 上游 get_more 的**源表**编码
            #   formTableSourceId           = form_{上游get_more节点ID}_{源表编码}
            #   formTableSourceGetDataType  = 1        ← 最容易漏的就是它
            # **漏任何一个都是静默失效**：save/deploy 全 success、节点回读也在，引擎就是不写库，
            # 目标表 0 行；下游若接多实例子流程，还会连带炸在
            # `Cannot resolve identifier '<getMore节点id>_assigneeDataIdList'`
            # —— getMore 只在 `if (isNotEmpty(records))` 里发布那个变量，取到 0 行就不发布，
            # **报错点在最后一环、根因在第一环**（2026-09-22 实机踩到）。
            # 参照实现：`miniflow_creator.py` 的 `build_data_add_node`（addDataType=2 时
            # 这 5 个键一起落）和 `postbuild_flows.py` 的 `_batch` 分支
            # （从上游 get_more 节点的 formTableCode 推出 Code / Id）。
            return {"type": "data_add", "name": spec["name"],
                    "formTableCode": self.rv.code(tb), "formTableName": tb,
                    # 线上 28 条 data_add 的这两个键**都是空串**（来源是「本节点自己」，
                    # 不是触发行）；写成 "start"/"table" 会让面板的来源标注错
                    "formTableSourceTaskId": "", "formTableSourceNodeType": "",
                    "formModel": form_model, "addDataType": 1, "formType": 2, "noDataType": 1,
                    "expressionType": "delegateExpression",
                    "expressionValue": "${addRecordDelegate}"}

        if t == "approver":
            groups = []
            if spec.get("_exp"):        # flow_dsl.appr()：审批人 = 发起人
                # expressionsNames 是设计器卡片上的「填写人」显示名，别塞表达式原文
                groups.append({"approverType": "candidateUser", "assigneeType": "assigneeByExp",
                               "approverIds": [], "approverNames": [], "deptIds": [],
                               "roleIds": [], "postIds": [],
                               "expressionsIds": ["${applyUserId}"],
                               "expressionsNames": [spec["_exp"]], "levelMode": 1,
                               "approverId": "", "approverName": "", "variableTitle": [],
                               "variableContent": "", "formTableType": ""})
            if spec.get("users"):
                # ⚠️ approverIds 写**裸账号**，不能带 `user.` 前缀——`user.xxx` 是**消息节点
                # toUserIds** 的写法；写成前缀时 save/deploy 全绿、新增记录也起实例，
                # 但**任务谁都收不到**（2026-09-16 用户实测报障「指定成员的任务没人收到」，
                # 线上参照应用的 2 条指定成员组落库均为裸账号）。
                groups.append({"approverType": "candidateUser", "assigneeType": "assigneeByName",
                               "approverIds": [u for u in spec["users"]],
                               "approverNames": list(spec["users"]), "levelMode": 1,
                               "approverId": "", "approverName": "", "deptIds": [], "roleIds": [],
                               "postIds": [], "expressionsIds": []})
            if spec.get("roles"):
                # ⚠️ candidateGroups 的 roleIds 按文档必须填**角色 Code**（如 "admin"），
                # 而 DSL 这里收的是角色名——名字≠Code 时同样静默解析不到人。未实测，用到请先核。
                groups.append({"approverType": "candidateGroups", "assigneeType": "assigneeByName",
                               "roleIds": list(spec["roles"]), "roleNames": list(spec["roles"]),
                               "levelMode": 1, "approverId": "", "approverName": "",
                               "approverIds": [], "deptIds": [], "postIds": [], "expressionsIds": []})
            if not groups:      # 没点名审批人 → 兜底 admin
                groups.append({"approverType": "candidateUser", "assigneeType": "assigneeByName",
                               "approverIds": ["admin"], "approverNames": ["admin"],
                               "levelMode": 1, "approverId": "", "approverName": "",
                               "deptIds": [], "roleIds": [], "postIds": [], "expressionsIds": []})
            return {"type": "approver", "name": spec["name"],
                    "approvalMode": 3 if spec.get("mode") == 3 else 1,
                    "approverGroups": self.groups(spec, dflt="admin")}

        if t == "edit":
            # 填写节点：办理人打开表单边看边改。与 approver 的区别见 flow_dsl.fill()。
            return {"type": "edit", "name": spec["name"],
                    "approverGroups": self.groups(spec, dflt="apply")}

        # 三种网关的分支结构同构（conditionNodes 里每条带 conditions / isDefault），
        # 差别只在语义：exclusive=只走第一条命中、inclusive=命中的**都走**、
        # parallel=**无条件全走**。中文对照：互斥/排他分支=exclusive、
        # 相容分支=包含分支=inclusive、并行分支=parallel（create-flow.md 分支类型消歧）。
        if t in ("exclusive", "inclusive", "parallel"):
            branches = spec.get("branches") or []
            # ⚠️ **硬闸 1**：parallel 分支带条件 = 条件会被整组丢掉。
            # `build_parallel_gateway` 把 branchType 硬编码成 2、conditionGroup 恒空。
            # 2026-09-20 实测事故：把需求里的「相容分支」误当 parallel 建，
            # 5 个分支的条件全部消失、变成无条件全跑（设「一般项目」和「重点项目」
            # 同时执行，结果看谁后写），而 save/deploy/回读/契约检查**全绿**。
            if t == "parallel":
                bad = [ (b.get("name") or "分支%d" % (i + 1))
                        for i, b in enumerate(branches) if b.get("cond") ]
                if bad:
                    raise ValueError(
                        "parallel 网关「%s」的分支（%s）带了条件——并行分支**不支持条件**，"
                        "发下去会被整组丢掉、变成无条件全跑。要「满足条件的分支都走」"
                        "请改用 inclusive（即明道云的「相容分支」/「包含分支」）。"
                        % (spec["name"], "、".join(bad)))
            brs = []
            for i, b in enumerate(branches):
                items = []
                branch_form = None
                for (fname, rule_cn, val) in (b.get("cond") or []):
                    # 判据可以是**运算节点的结果**：主语写成 `result("统计条数")`。
                    # 此时 field 固定 "result"、字段源换成该运算节点
                    # （branchForm=function-{funType}）——否则分支按触发行快照取值，
                    # 恒判失败、永远走兜底支（node-types「四」4.4.1 / gotchas #59）。
                    if isinstance(fname, dict) and "$result" in fname:
                        rb = self.built.get(fname["$result"])
                        if not rb or rb["type"] != "operation":
                            raise KeyError(
                                "网关「%s」分支「%s」：判据 result(%r) 找不到对应运算节点"
                                % (spec["name"], b.get("name"), fname["$result"]))
                        fcode = "function-%s" % (rb.get("fun_type") or "fun")
                        items.append({"rule": rule_code(rule_cn),
                                      "ruleName": rule_cn, "valueType": "1",
                                      "val": val, "name": None,
                                      "field": "result", "columnName": "结果",
                                      "type": "number", "valType": "number"})
                        branch_form = {"formTableCode": fcode,
                                       "formNodeId": rb["id"],
                                       "formNodeType": "function"}
                        continue
                    if isinstance(val, dict) and ("$ref" in val or "$var" in val):
                        # 排他网关的分支条件**只支持「字段 vs 字面量」**：值写 ref()/var() 时
                        # 引擎仍按 valueType:"1" 当字面量比，条件恒假，而且实测父流程会卡在
                        # bpm=2 不结束（2026-09-22 进销存 R2「收款单-核销」）。
                        raise ValueError(
                            "网关「%s」分支「%s」的条件 %s 右侧写了 ref()/var() —— 分支不支持"
                            "「字段对字段」比较（会恒判失败且父流程卡死）。改法二选一："
                            "① compute() 算出差值再用 result() 当主语；"
                            "② get_one(目标表, cond=[(字段, 规则, 值)], empty=\"分支\") + data_branch()"
                            "（引擎原生，实测可靠）"
                            % (spec["name"], b.get("name"), fname))
                    tf = self.rv.f(ctx_table, fname)
                    _ct = self.rv.family(ctx_table, fname)
                    # 字面量先翻成**表单真实存储值**（写「冻结释放入库」、库里存 "9"）。
                    # ⚠️ 这里原先直接 `cond_value(_ct, val)` —— 分支条件是**另起炉灶**拼的，
                    # 没走 `_cond_items`，所以主触发条件修好了、**分支条件还是显示名**
                    # （2026-09-21 实测：其他入库单-确认 的分支恒落默认支）。
                    _raw = val if rule_cn in ("为空", "不为空") else self.rv.field_value(ctx_table, fname, val)
                    _v, _nm = cond_value(_ct, _raw, self.rv)
                    items.append({"rule": rule_code(rule_cn),
                                  "ruleName": rule_cn, "valueType": "1",
                                  "val": _cond_val(_v), "name": _nm if _nm is not None else fname,
                                  "field": tf["model"], "columnName": fname,
                                  "type": _ct, "valType": _ct})
                e = {"name": b.get("name") or ("分支%d" % (i + 1)),
                     "nodes": [self.node(x, ctx_table) for x in (b.get("nodes") or [])]}
                if items:
                    e["conditions"] = items
                else:
                    e["isDefault"] = True
                if branch_form:
                    e["branchForm"] = branch_form
                brs.append(e)
            # ⚠️ **硬闸 2**：inclusive **不得用 isDefault 兜底分支**，每条分支都要有明确条件
            # （create-flow.md「inclusive 三条硬约束 ②」/ gotchas #12）。要兜底就写
            # 「为空」这类**显式条件**的分支。exclusive 不受此限——它的默认分支是正常用法。
            if t == "inclusive":
                bad = [e["name"] for e in brs if e.get("isDefault")]
                if bad:
                    raise ValueError(
                        "inclusive 网关「%s」的分支（%s）没有条件 → 会被建成 isDefault 兜底分支，"
                        "而 inclusive **不得用 isDefault 兜底**（create-flow.md 硬约束②/ gotchas #12）。"
                        "请给每条分支写明确条件，要兜底就用「为空」这类显式条件。"
                        % (spec["name"], "、".join(bad)))
            return {"type": t, "name": spec["name"], "conditionNodes": brs}

        if t == "data_branch":
            # 数据判断分支：必须紧跟在 get_one(empty="分支") 之后（creator 会校验）
            def branch(nm, nodes):
                return {"name": nm, "nodes": [self.node(x, ctx_table) for x in nodes]}
            return {"type": "data_branch", "name": "数据分支",      # 引擎硬编码，见 flow_dsl.DATA_BRANCH_NAME
                    "conditionNodes": [branch("有数据", spec.get("found") or []),
                                       branch("无数据", spec.get("missing") or [])]}

        if t == "operation":
            # 「统计条数」= funType=record，数的是上游 get_more 取回了几条。
            # 三要素（example/运算节点示例.md §4）：sourceTaskId=上游 get_more 节点 id、
            # formTableCode/formTableName 与它一致、getDataType 与它一致（本 builder 的
            # get_more 恒为 1）；operationMode 固定 everyTime（实时统计），不是 cache。
            if (spec.get("fun_type") or "") == "record":
                src = spec.get("source")
                b = self.built.get(src)
                if not b or b["type"] != "get_more":
                    raise KeyError(
                        "compute_record(%r, source=%r)：source 必须是前面 get_more() 建的节点"
                        % (spec.get("name"), src))
                tb = b.get("table") or ctx_table
                return {"type": "operation", "name": spec["name"],
                        "funType": "record", "sourceTaskId": b["id"],
                        "formTableCode": self.rv.code(tb), "formTableName": tb,
                        # ⚠️ 必须与上游 get_more 的 getDataType **一致**（「record 统计
                        # 三要素」之一）。两边不一致时运行时读错存储 —— 2026-09-20 实测：
                        # 统计节点写 1、get_more 实为 2 → ClassCastException。故这里
                        # 从登记的 get_data_type 取，不再写死。
                        "getDataType": b.get("get_data_type", 1),
                        "decimals": spec.get("decimals", 0)}

            # 运算节点：expr 里的 $名字$ 换成 funText 的 {{i}}，并备好每个字段的出处。
            # 用 creator 的「方式二」（显式 funFields），因为方式一假定所有字段都来自
            # 上下文表——而实际算式里的字段多半来自上面某个「取单条数据」节点。
            expr, fun_fields = spec.get("expr") or "", []
            for label, ref_v in (spec.get("fields") or {}).items():
                if ("$%s$" % label) not in expr:
                    raise KeyError("compute(%r)：算式里找不到占位符 $%s$"
                                   % (spec["name"], label))
                if not (isinstance(ref_v, dict) and "$ref" in ref_v):
                    raise KeyError("compute(%r)：$%s$ 必须是 ref(...)，不能是固定值"
                                   % (spec["name"], label))
                val = self.value(ref_v, ctx_table)
                src_node = ref_v["$node"]
                src_table = (ctx_table if src_node in ("start", "子流程", "工作表事件触发")
                             else (self.built.get(src_node) or {}).get("table"))
                fi = self.rv.f(src_table, ref_v["$ref"])
                fun_fields.append({
                    "field": fi["model"], "formTableCode": val["formTableCode"],
                    "fieldText": ref_v["$ref"], "formNodeId": val["formNodeId"],
                    "formNodeName": val["formNodeName"], "tableText": src_table or "",
                })
                expr = expr.replace("$%s$" % label, "{{%d}}" % (len(fun_fields) - 1))
            if "{{" not in expr:
                raise KeyError("compute(%r)：算式里一个 $占位符$ 都没有" % spec["name"])
            return {"type": "operation", "name": spec["name"],
                    "funText": expr, "funFields": fun_fields,
                    "funType": "fun", "decimals": spec.get("decimals", 2)}

        if t == "subprocess":
            sub = self.sub_ids.get(spec["sub"])
            if not sub:
                raise KeyError("子流程尚未构建: %s（顺序必须是先子后主）" % spec["sub"])
            multi = bool(spec.get("multi", True))

            # —— 逐行调子流程（callActivity）的**全套契约**，形状照线上模版实测 ——
            # 少任何一项都不是「建歪一点」，而是：设计器里「选择数据对象」空白、
            # 子流程页白屏、「被以下工作流触发」为空、运行时一行都不进子流程。
            gm = self._last_get_more
            via = spec.get("via")
            if via:
                b = self.built.get(via)
                if not b or b["type"] != "get_more":
                    raise KeyError("call_sub(%r, via=%r)：via 必须是前面 get_more() 建的节点"
                                   % (spec["name"], via))
                gm = {"id": b["id"], "name": via,
                      "code": b.get("detail_code"), "main": b.get("main_code"),
                      "table": b.get("detail_table")}
            if multi and not gm:
                raise KeyError(
                    "call_sub(%r)：逐行调子流程前面必须有 get_more(..., from_=\"start\")"
                    "（取本单关联明细）——没有数据对象时子流程会绑不上、整条链断掉"
                    % spec["name"])
            if multi and not (gm.get("code") and gm.get("main")):
                # ⚠️ 这条报错原来只说「数据对象缺明细表/主表 code」——那是**下游症状**，
                # 真正的上游原因几乎总是前面那条 get_more 的 from_ 没写 "start"
                # （2026-09-22 实测：按名字猜成"关联字段名/字段 model"，连错两次，
                #  并且被误导去查"分支拓扑""子表 model"各一轮）。这里把原因写在最前面。
                raise KeyError(
                    "call_sub(%r)：数据对象不完整（明细表/主表 code 为空）。\n"
                    "  ➜ 最可能的原因：前面那条 get_more 的 from_ 不是 \"start\"。\n"
                    "     正确写法：get_more(%r, from_=\"start\")   # 字面量 'start'，\n"
                    "     不是字段中文名、也不是字段 model —— 它的含义是「取本单的关联明细」。\n"
                    "  ➜ 次可能：from_ 写了 \"start\" 但主表上没有指向该明细表的关联控件（那一条会单独报错）。\n"
                    "  当前数据对象：%r"
                    % (spec["name"], gm.get("table") or "<明细表>", gm))

            attr = {"approvalEnabled": True,
                    "calledElement": "process%s" % sub["db_id"],
                    "formTableName": None, "formTableCode": None,
                    "processName": sub["process_name"], "processId": "",
                    "customProcessId": str(sub["db_id"]),
                    "loopCardinality": None, "ratio": 0.5,
                    "isSequential": False, "isMulti": multi,
                    "collection": "${flowUtil.stringToList(assigneeUserIdList)}",
                    "elementVariable": "assigneeUserId",
                    "completionCondition": None}

            var_list = []
            for pname, pv in (spec.get("pass") or {}).items():
                # 字面量经 var() 写进字典/选项字段时，落库要的是存储值不是显示文案
                # （2026-09-22 进销存实测「账向」落成文案；engine-contract 5-b 漏了「传参」这一处）。
                # 子流程先建，所以这里已知道该参数写进了哪张表哪个字段。
                tgt = self.var_targets.get((spec["sub"], pname))
                if tgt and not isinstance(pv, dict):
                    pv = self.rv.field_value(tgt[0], tgt[1], pv)
                val = self.value(pv, ctx_table)
                var_list.append({
                    "id": MC.gen_id(), "optType": "1",
                    "valueType": 2 if isinstance(val, dict) else "1",
                    "fieldValue": "",
                    "field": pname, "val": val,
                    "fieldType": "input", "type": "input",
                    "valType": "variable" if isinstance(val, dict) else None,
                })
            if var_list:
                attr["variableList"] = var_list

            if multi:
                attr["formTableSourceTaskId"] = gm["id"]
                attr["formTableId"] = "form_%s_%s" % (gm["id"], gm["code"])
                attr["subFormTableObject"] = {
                    "formTableId": attr["formTableId"],
                    "nodeId": gm["id"], "nodeName": gm["name"], "nodeType": "getMore",
                    "formTableCode": gm["code"], "formTableName": gm.get("table") or "",
                    "formTableMainCode": gm["main"], "formTableType": 1,
                    "isSubStart": True, "selectType": 3, "getDataType": 1,
                }

            return {"type": "subprocess", "name": spec["name"],
                    "approvalMode": 1,
                    # 子流程流程变量靠这个监听器注入；漏了 → 子流程里 var() 全是空
                    "listenerData": [{
                        "id": "502880e54853a496014805e5d9190012",
                        "eventType": "start", "listenerType": "javaClass",
                        "listenerName": "子流程流程变量",
                        "value": ("org.jeecg.modules.extbpm.process.adapter.delegate."
                                  "MiniCallActivityListener"),
                        "allowDel": False}],
                    # 这 4 条是引擎固定回传的上下文，缺了子流程取不到父单据
                    "inVariableModels": [
                        {"source": "applyUserId", "target": "applyUserId"},
                        {"source": "dataId", "target": "dataId"},
                        {"source": "JG_LOCAL_PROCESS_ID",
                         "target": "JG_SUB_MAIN_PROCESS_ID"},
                        {"source": "handleDataId", "target": "handleDataId"},
                    ],
                    "outVariableModels": [],
                    "attr": attr}

        if t == "time":
            # duration 必须是 ISO 8601 时长串。早先写的是裸分钟数（`attr.duration: 5`），
            # build_time_node 又只在**顶层**找 duration → 一律落回 "PT1M"：
            # `delay(30)` 建出来是「1 分钟后」，save/deploy 全绿。
            return {"type": "time", "name": spec["name"],
                    "duration": _iso_duration(int(spec.get("minutes") or 1))}

        if t == "notice":
            users = list(spec.get("users") or [])
            # 收件人允许写 "role.xxx" / "dept.xxx"；裸姓名补 "user." 前缀
            ids = [u if "." in u else "user.%s" % u for u in users]
            return {"type": "notice", "name": spec["name"],
                    "noticeType": spec.get("kind") or "system",
                    "attr": {"noticeTitle": spec.get("title") or "通知",
                             "noticeContent": spec.get("content") or ""},
                    "toUserIds": ids, "toUserNames": users}

        raise KeyError("未知节点类型: %s" % t)

    def build(self, spec):
        """spec → (config, nodes) 供 build_process_json 用。"""
        ctx = spec.get("table") or spec.get("context")
        self._cur_name = spec.get("name") or ""
        # 每条流程重新开始登记：节点名只在**本流程内**唯一，跨流程复用会指错节点
        self.built = {}
        self._last_get_more = None
        self._last_add = None
        # 供 value() 决定「本行」引用的起始节点显示名（子流程里不是「工作表事件触发」）
        self._is_sub = spec.get("kind") != "main"
        nodes = [self.node(x, ctx) for x in (spec.get("nodes") or [])]
        if spec["kind"] == "main":
            # ⚠️ 别写死 "tableEvent"：按钮/定时/手动触发的 attr 形状与它**不同**，
            # 照抄会静默建出「工作表事件触发」的流程（触发时机全错）。
            start_type = spec.get("startType") or "tableEvent"
            config = {
                "processName": spec["name"],
                "lowAppId": self.rv.app,
                "processType": "oa",
                "startType": start_type,
                # flow(..., trigger_other=True) → 本流程写出的记录也触发目标表的流程
                # （引擎内部写入默认绕过 tableEvent；随 config 发才能在 --update 重存后保住）
                "triggerOtherProcess": "1" if spec.get("trigger_other") else "0",
                "formTableCode": self.rv.code(spec["table"]),
                "formTableName": spec["table"],
                # 引擎读 attr.startEventType（字符串）；写数字键会被静默忽略
                "startEventType": EVENT.get(spec.get("on", "新增"), "add"),
                "startCondition": self.trigger(spec),
                # 监控字段：update 时后端先比对新旧值，只有这些字段变了才继续校验条件
                "conditionFields": self.watch_fields(spec),
                "nodes": nodes,
            }
            config.update(trigger_extras(start_type, spec))
        else:
            config = {
                "processName": spec["name"],
                "lowAppId": self.rv.app,
                "processType": "oa",
                "startType": "subEvent",
                "formTableCode": self.rv.code(spec["context"]),
                "formTableName": spec["context"],
                # 声明本子流程要收哪些流程变量；不声明 = 调用方传了也收不到
                "variableList": [{"field": p, "id": MC.gen_id(), "type": "input",
                                  "options": {"format": "yyyy-MM-dd"}}
                                 for p in (spec.get("params") or [])],
                "hasVariableList": False,     # 子流程恒 False（实测 29/29 条如此）
                "nodes": nodes,
            }
        # ⚠️ 必须返回**二元组**：两处调用点都写的是 `config, nodes = b.build(f)`
        # （本函数 docstring 也一直写着 "→ (config, nodes)"）。2026-09-16 实测：
        # 只 `return config` 时，把 8 个键的 dict 解包成 2 个变量 →
        # `ValueError: too many values to unpack (expected 2)`，
        # 主流程与子流程**一条都建不出来**——这就是 `flow_dsl.py` 里
        # 「save → deploy 实盘路径尚未验证过」那条备注背后的真实原因。
        return config, nodes


# ---------------- 主流程 ----------------

def load_spec(path):
    m = importlib.util.spec_from_file_location("user_flows", path)
    mod = importlib.util.module_from_spec(m)
    try:
        m.loader.exec_module(mod)
    except NameError as ex:
        # 建后套件的简流配置（button_flow/appr/upd）传进来只会报裸 NameError（2026-09-22 项目管理 R2）
        raise SystemExit("FAIL: --spec 要的是 flow_dsl 写的 flows.py（定义 FLOWS = [...]），"
                         "%s 看起来是建后套件的 pb_flows.py（它走 postbuild_flows.py --config）：%s" % (path, ex))
    flows = getattr(mod, "FLOWS", None)
    if not flows:
        raise SystemExit("FAIL: spec 里没有 FLOWS")
    return flows


def tables_of(flows):
    out = []
    for f in flows:
        for t in ([f.get("table"), f.get("context")] + _node_tables(f.get("nodes") or [])):
            if t and t not in out:
                out.append(t)
    return out


def _in_branch(nodes, node_id):
    """`node_id` 是不是**嵌在网关分支里**（不在主链路上）。

    主链路上的取多条 → 子流程可以按 `search + 该节点 id` 取值（进销存 29 条子流程实测正常）；
    分支里的取多条 → 子实例读不到，必须保持 `table/start`（销售 R3 实测，14 处 ref 全空）。"""
    if not node_id:
        return False

    def scan(ns, inside):
        for n in (ns if isinstance(ns, list) else [ns]):
            if not isinstance(n, dict):
                continue
            if inside and str(n.get("id")) == str(node_id):
                return True
            for b in (n.get("branches") or []):
                if scan(b.get("nodes"), True):
                    return True
            for b in (n.get("conditionNodes") or []):
                if scan(b.get("nodes") or b.get("childNode"), True):
                    return True
            for k in ("found", "missing", "childNode"):
                if n.get(k) and scan(n[k], inside):
                    return True
        return False

    return scan(nodes, False)


def _walk_nodes(nodes):
    """把节点树（含分支里的）拍平成一个列表。"""
    out = []
    if not isinstance(nodes, list):
        nodes = [nodes]
    for n in nodes:
        if not isinstance(n, dict):
            continue
        out.append(n)
        for b in (n.get("branches") or []):
            out += _walk_nodes(b.get("nodes"))
        # ⚠️ **已构建**的网关节点用 `conditionNodes`（spec 里才叫 `branches`）。
        # 不漏它，网关分支里的 `call_sub` 在「subFlowList / 子流程回填」那一趟彻底隐身——
        # 子流程建了、没登记、没补 customProcessId，真机上报
        # `Process definition process<subId> was not found`（2026-09-20 本应用实测：
        # 顶层 call_sub 的「生成机会编号报销」回填成功，藏在包含分支里的
        # 「添加修改客户联系人」漏掉，主流程一跑就炸）。
        for c in (n.get("conditionNodes") or []):
            out.append(c)
            out += _walk_nodes(c.get("nodes"))
        for k in ("found", "missing"):
            out += _walk_nodes(n.get(k) or [])
        out += _walk_nodes(n.get("nodes") or [])
    return out


def _node_tables(nodes):
    out = []
    if not isinstance(nodes, list):
        return out
    for n in nodes:
        if not isinstance(n, dict):
            continue
        if n.get("table"):
            out.append(n["table"])
        for b in (n.get("branches") or []):
            out += _node_tables(b.get("nodes") or [])
        # data_branch 的两条支路（键名是 found/missing，别和 get_one 的 empty= 撞）
        out += _node_tables(n.get("found") or [])
        out += _node_tables(n.get("missing") or [])
    return out


def deployed_keys(api, token, tenant, app):
    """引擎里**已部署**的流程定义 key 集合（`/act/process/list`）。

    子流程只有在这里出现 `key=process<DBid>` 才算真的可被调用：API 存完、
    `deploy` 返回成功，都**不代表**引擎里有这个定义。缺它时父流程的 callActivity
    一执行就抛 `FlowableObjectNotFoundException`，而 save/deploy 全绿
    （2026-09-17 实测 22 条子流程踩坑；2026-09-20 又靠流程外的脚本补跑一次）。
    """
    import requests
    out = set()
    try:
        r = requests.get(api + "/act/process/list",
                         params={"pageNo": 1, "pageSize": 500},
                         headers={"X-Access-Token": token, "X-Tenant-Id": str(tenant),
                                  "X-Low-App-ID": str(app)}, timeout=60)
        res = (r.json() or {}).get("result")
        rows = (res.get("records") if isinstance(res, dict) else res) or []
        for x in rows:
            k = x.get("key") or x.get("processKey")
            if k:
                out.add(str(k))
    except Exception:                                             # noqa: BLE001
        pass
    return out


# 说明：子流程「本行字段」引用的定形**只有一个实现** —— 见下面的
# `_fix_sub_ownrow_refs()`（formNodeName 写别名 "子流程"）。这里曾短暂存在过另一个
# 版本（把 formNodeName 写成父流程 get_more 节点的名字），已删除：两份实现形态不同，
# 留着必然有人调错。要改就改 `_fix_sub_ownrow_refs()`。

def existing_names(api, token, tenant, app):
    """该应用下已有的流程名集合（带 X-Low-App-ID 头，0.1s 只含本应用）。"""
    import requests
    try:
        r = requests.get(api + "/act/process/extActProcess/list",
                         params={"lowAppId": app, "pageSize": 500, "pageNo": 1},
                         headers={"X-Access-Token": token, "X-Tenant-Id": str(tenant),
                                  "X-Low-App-ID": str(app)}, timeout=60)
        res = (r.json() or {}).get("result") or {}
        rows = (res.get("records") if isinstance(res, dict) else res) or []
        return {x.get("processName") for x in rows}
    except Exception:                                             # noqa: BLE001
        return set()


def _own_flow(rec, app_id, tenant_id=None):
    """按名字查回来的记录是否**真的属于本应用**。

    `listProcess` 不过滤租户，同名流程可能来自别的租户/应用 → 不能当成「本应用已存在」。
    记录里 `lowAppId` 为空时（后端偶发漏写）退回看 `tenantId`：还是本租户就认，
    保住「lowAppId 被写空、记录还在」那条兜底路径的原意。
    """
    if not rec:
        return None
    if str(rec.get("lowAppId") or "") == str(app_id):
        return rec
    if not rec.get("lowAppId") and tenant_id is not None \
            and str(rec.get("tenantId") or "") == str(tenant_id):
        return rec
    return None


SUB_ROW_NAME = "子流程"     # 子流程内「输入行」的合法别名（= formNodeName 该写的值）


def _fix_sub_ownrow_refs(spj, node_id, log_=None):
    """子流程「本行字段」引用定形 —— 必须在父流程发布**之后**跑（见 main 的 pass ③）。

    落库三键的实测形态（2026-09-20 全库扫 17/17 条手搭子流程一致）：
        formNodeId   = 父流程那个 get_more 节点的 id（= formTableList isSubStart 的 nodeId）
        formNodeName = "子流程"
        formNodeType = "search"

    `Builder.value()` 对「本行」写的是 `table` + `formNodeId:"start"` —— 那是**主流程触发行**
    的写法，子流程画布上根本没有 start 这个节点。运行时按上下文行取值，所以**跑得对**，
    但设计器解析不到来源 → 字段值面板「设置的数据」与手动下拉显示不一致（用户报障形态）。
    本函数只改引用**三键**，不动 variableValue/variableName/formTableCode（那些本来就是对的）。

    顺带把 `data_update` 指向「本行」的来源也定形：sub 流程里 source=start 的更新
    写的是 `formTableSourceTaskId:"start"` + `formTableSourceNodeType:"table"`，
    实测形态应为 输入行 nodeId + `"search"`（金标 自动报价2 的「更新报价明细」）。
    返回 (改写引用数, 改写更新节点数)。
    """
    n_ref = n_upd = 0

    def walk(o):
        nonlocal n_ref, n_upd
        if isinstance(o, dict):
            if o.get("variableValue") and o.get("formNodeId") in (node_id, "start"):
                if (o.get("formNodeType") != "search"
                        or o.get("formNodeName") != SUB_ROW_NAME
                        or o.get("formNodeId") != node_id):
                    o["formNodeType"] = "search"
                    o["formNodeName"] = SUB_ROW_NAME
                    o["formNodeId"] = node_id
                    n_ref += 1
            if (o.get("type") == "data_update"
                    and o.get("formTableSourceTaskId") == "start"):
                o["formTableSourceTaskId"] = node_id
                o["formTableSourceNodeType"] = "search"
                code = o.get("formTableCode")
                if code:
                    o["formTableId"] = "form_%s_%s" % (node_id, code)
                n_upd += 1
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(spj)
    if log_ and (n_ref or n_upd):
        log("OK:subrow 引用 %d 处 + 更新节点 %d 个 → search/%s/%s"
            % (n_ref, n_upd, SUB_ROW_NAME, node_id))
    return n_ref, n_upd


def main():
    ap = argparse.ArgumentParser(description="批量建流程：规格驱动、单进程、幂等")
    ap.add_argument("--api-base", required=True)
    ap.add_argument("--token", required=True)
    ap.add_argument("--tenant-id", required=True)
    ap.add_argument("--app-id", required=True)
    ap.add_argument("--spec", required=True, help="flows.py")
    ap.add_argument("--only", default="",
                    help="只处理这些流程名（逗号分隔）。**重跑失败项时一定要加**："
                         "不加时 --update 会把全部流程重存重发（63 条实测 234s），"
                         "加了只碰这几条。被选中主流程引用到的子流程会自动带上"
                         "（子流程必须先建，否则只会撞「子流程尚未构建」白跑一轮）。")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--update", action="store_true",
                    help="同名流程**重存+重发布**（保留原 processKey），而不是跳过。"
                         "改了 flows.py 想生效必须加这个——默认同名会静默跳过。")
    ap.add_argument("--force", action="store_true",
                    help="跳过「子流程 processKey 必须已在引擎注册」这道硬屏障。"
                         "**默认不开**：带病建父流程 = 整批 callActivity 指向不存在的定义，"
                         "只能返工。只在明知引擎侧另有补救手段时用。")
    ap.add_argument("--no-rewrite", action="store_true",
                    help="关闭 flow_rules 的自动改写（data_branch→upsert 形态、add() 补 0、公式累加前插运算节点），"
                         "改为报错/告警。默认开启改写：这三处引擎行为都是静默写坏账，见 flow_rules.py 文首。")
    ap.add_argument("--rewrite-databranch", action="store_true",
                    help="把 get_one(empty=分支)+data_branch 改写成「取多条→统计条数→判 0」的绕行形态。"
                         "默认不改写：真因是网关名（已强制「数据分支」），绕行只在引擎确有缺陷时用。")
    ap.add_argument("--strict", action="store_true", help="flow_rules 的告警（未验证的网关判据等）升级为报错")
    ap.add_argument("--lenient", action="store_true",
                    help="flow_rules 的「运算节点取数来源」报错降级为告警（确认目标引擎已修复时才用）")
    a = ap.parse_args()

    flows = load_spec(a.spec)
    # 引擎行为规则（静态部分）：必须在 --only 过滤**之前**对全部流程跑 ——
    # 「哪些列会被累加」「同表同事件有几条主流程」都是全应用口径。
    import flow_rules as FR
    flows, rep = FR.apply_static(flows, rewrite=not a.no_rewrite, strict=a.strict,
                                 rewrite_databranch=a.rewrite_databranch)
    if not FR.print_report(rep, log):
        raise SystemExit("FAIL: flow_rules 静态规则不通过 %d 条（见上）" % len(rep["errors"]))
    only = {s.strip() for s in a.only.split(",") if s.strip()}
    if only:
        known = {f["name"] for f in flows}
        miss = sorted(only - known)
        if miss:
            raise SystemExit("--only 里有 flows.py 中不存在的流程名：%s" % "、".join(miss))
        # 被选中主流程引用到的子流程自动带上：callActivity 是按 key 引用子流程的，
        # 子流程没先建/没先发布 → 「子流程尚未构建」整条主流程建不出来。
        sub_names = {f["name"] for f in flows if f["kind"] == "sub"}
        picked = set(only)
        changed = True
        while changed:
            changed = False
            for f in flows:
                if f["name"] not in picked:
                    continue
                for n in _walk_nodes(f.get("nodes") or []):
                    s = n.get("sub")
                    if s in sub_names and s not in picked:
                        picked.add(s)
                        changed = True
        flows = [f for f in flows if f["name"] in picked]
        log("OK:only 只处理 %d 条（点名 %d + 依赖子流程 %d）"
            % (len(flows), len(only), len(picked) - len(only)))
    rv = Resolver(a.api_base, a.token, a.tenant_id, a.app_id)
    rv.load(tables_of(flows))
    # 引擎行为规则（类型部分）：要真机字段类型，所以放在 Resolver 之后
    flows, rep = FR.apply_typed(
        flows, lambda t, f: (rv.fields.get((t, f)) or {}).get("type"), rv.formula_expr,
        rewrite=not a.no_rewrite, lenient=a.lenient)
    if not FR.print_report(rep, log):
        raise SystemExit("FAIL: flow_rules 类型规则不通过 %d 条（见上；确认引擎已修复可加 --lenient）"
                         % len(rep["errors"]))

    have = existing_names(a.api_base, a.token, a.tenant_id, a.app_id)
    # listProcess 是按 lowAppId 过滤的 —— 记录还在、但 lowAppId 被写空时它就不出现在列表里。
    # 那种情况下**不能当新建**（会建出重名副本、且原条目的 callActivity 绑定全断）。
    # 所以：列表里没有的，再按名字查一次；查得到就走更新。
    #
    # ⚠️ **必须带 low_app_id**（2026-09-17 修）：`listProcess` **不按 X-Tenant-Id 过滤**，
    # 不带 lowAppId 时会逐页扫到**别的租户的同名流程**并当命中返回。
    # 实测（租户 1013 新建「进销存」，1009~1012 早先建过同名应用）：63 条里 61 条被判
    # 「已存在」→ 全 `OK:skip` → 本应用 0 条流程；这轮按名字轮询还白烧了 20 分钟。
    # 带上 lowAppId 后服务端直接过滤（1 页返回），既准又快。
    orphan = [f["name"] for f in flows if f["name"] not in have
              and _own_flow(MC.query_flow(a.api_base, a.token, process_name=f["name"],
                                          tenant_id=a.tenant_id, low_app_id=a.app_id),
                            a.app_id, a.tenant_id)]
    if orphan:
        log("OK:plan 这几条不在列表里、但按名字查得到（lowAppId 可能被写空），按更新处理：%s"
            % "、".join(orphan))
        have |= set(orphan)
    subs = [f for f in flows if f["kind"] == "sub"]
    mains = [f for f in flows if f["kind"] == "main"]
    log("OK:plan 子流程 %d / 主流程 %d（已存在 %d 条同名）" % (len(subs), len(mains), len(have)))

    if a.dry_run:
        for f in subs + mains:
            log("OK:plan [%s] %s ← %s" % (f["kind"], f["name"], f.get("table") or f.get("context")))
        return

    b = Builder(rv)
    t0 = time.time()
    ok = skip = fail = 0
    sub_links = []      # 主流程 callActivity → 子流程的引用，供第 ③ 趟回填

    # ① 子流程：save → deploy → 注册 → 补 customProcessId → 再 deploy → 校验
    for f in subs:
        name = f["name"]
        rec = None
        if name in have:
            # 带 low_app_id：不带时 listProcess 会跨租户命中同名流程（见 query_flow 注释）
            rec = _own_flow(MC.query_flow(a.api_base, a.token, process_name=name,
                                          tenant_id=a.tenant_id, low_app_id=a.app_id),
                            a.app_id, a.tenant_id)
            if rec and not a.update:
                b.sub_ids[name] = {"db_id": str(rec["id"]), "process_key": rec.get("processKey"),
                                   "process_name": name}
                log("OK:skip 子 %s" % name)
                skip += 1
                continue
        try:
            config, nodes = b.build(f)
            # --update 必须**保留原 processKey**：主流程的 call_sub 是按 key 引用子流程的
            config["processKey"] = (rec.get("processKey") if rec
                                    else "process%d" % (int(time.time() * 1000) % 10 ** 12))
            config["startTaskId"] = "start%s" % (int(time.time() * 1000) % 10 ** 9)
            pj = MC.build_process_json(dict(config, nodes=nodes))
            if rec:                                   # 重存：按 id + updateCount 覆盖
                fid = str(rec["id"])
                MC.save_flow(a.api_base, a.token, config, pj, flow_id=fid,
                             update_count=rec.get("updateCount"))
            else:
                r = MC.save_flow(a.api_base, a.token, config, pj)
                fid = (r.get("result") or {}).get("id") or r.get("id")
            # ⚠️ **Flowable 定义 key = `'process' + 记录的 customProcessId 字段`**，
            # 与记录里的 processKey **无关**（gotchas #47：抓 UI「保存并发布」HAR 逐项对比
            # + 一次性子流程控制实验实测）。而 `save_flow` 是从 **config** 取
            # `customProcessId` 当**表单字段**发的（`miniflow_creator` 第 ~3055 行），
            # 不是从 processJson.attr 读。以前这里只写 `pj["attr"]["customProcessId"]`、
            # 没写 config → **记录列恒空** → 注册出坏 key（`process` / `processnull`）→
            # 父流程 callActivity 按 `process<DBid>` 永远查不到，真机抛
            # `FlowableObjectNotFoundException`（2026-09-20 本应用实测：子流程建出来了、
            # 主流程一跑就炸，而 save/deploy 全报成功）。
            # 修法即 #47 配方：processKey=process<DBid> + customProcessId=<DBid> 重存再 deploy。
            config["customProcessId"] = str(fid)
            config["processKey"] = "process%s" % fid
            MC.register_subprocess_id(config["processKey"], str(fid))
            pj.setdefault("attr", {})["customProcessId"] = str(fid)
            pj["attr"]["processKey"] = config["processKey"]
            rec = MC.query_flow(a.api_base, a.token, flow_id=fid,
                                tenant_id=a.tenant_id)
            if rec:
                MC.save_flow(a.api_base, a.token, config, pj, flow_id=fid,
                             update_count=rec.get("updateCount"))
            MC.deploy_flow(a.api_base, a.token, fid, tenant_id=a.tenant_id, low_app_id=a.app_id)
            b.sub_ids[name] = {"db_id": str(fid), "process_key": config["processKey"],
                               "process_name": name}
            log("OK:sub %s id=%s" % (name, fid))
            ok += 1
        except Exception as e:                                    # noqa: BLE001
            log("FAIL:sub %s %s" % (name, str(e)[:170]))
            fail += 1

    # ①.5 硬屏障：子流程的 processKey 必须在**引擎里**有已部署定义，才允许建父流程。
    #
    # 为什么是闸门而不是提示：父流程的 callActivity 是按 `customProcessId` + 引擎里的
    # processKey 解析子流程的。子流程没注册上去时，主流程**照样建得成功**（save/deploy
    # 全绿），错要等到运行时调子流程那一刻才抛 FlowableObjectNotFoundException。
    # 2026-09-17 实测 22 条子流程踩坑、2026-09-20 又靠流程外脚本补跑一次 ——
    # 「事后补救」这条路已经证明走不通，所以这里直接拦住。
    if b.sub_ids:
        keys = deployed_keys(a.api_base, a.token, a.tenant_id, a.app_id)
        missing = [(nm, v["process_key"]) for nm, v in b.sub_ids.items()
                   if v["process_key"] not in keys]
        if missing and not a.force:
            for nm, pk in missing:
                log("FAIL:barrier 子流程 %s 的 processKey=%s 在引擎里没有已部署定义"
                    % (nm, pk))
            log("FAIL:barrier %d/%d 条子流程未注册，已拦住父流程不建。修法："
                "子流程须带 customProcessId=<DBid> + processKey=process<DBid> 重存再 "
                "deployProcess（gotchas #47）。确认要带病继续再加 --force。"
                % (len(missing), len(b.sub_ids)))
            sys.exit(1)
        if missing:
            log("WARN:barrier --force 放行 %d 条未注册子流程：%s"
                % (len(missing), "、".join(nm for nm, _ in missing)))
        else:
            log("OK:barrier 子流程 %d 条 processKey 全部已在引擎注册" % len(b.sub_ids))

    # ② 主流程：call_sub 已能解析到新子流程 id
    for f in mains:
        name = f["name"]
        rec = None
        if name in have:
            # 带 low_app_id：不带时 listProcess 会跨租户命中同名流程（见 query_flow 注释）
            rec = _own_flow(MC.query_flow(a.api_base, a.token, process_name=name,
                                          tenant_id=a.tenant_id, low_app_id=a.app_id),
                            a.app_id, a.tenant_id)
            if rec and not a.update:
                log("OK:skip 主 %s" % name)
                skip += 1
                continue
        try:
            config, nodes = b.build(f)
            config["processKey"] = (rec.get("processKey") if rec
                                    else "process%d" % (int(time.time() * 1000) % 10 ** 12))
            config["startTaskId"] = "start%s" % (int(time.time() * 1000) % 10 ** 9)
            pj = MC.build_process_json(dict(config, nodes=nodes))
            if rec:                                   # --update：重存，保留原 processKey
                fid = str(rec["id"])
                MC.save_flow(a.api_base, a.token, config, pj, flow_id=fid,
                             update_count=rec.get("updateCount"))
            else:
                r = MC.save_flow(a.api_base, a.token, config, pj)
                fid = (r.get("result") or {}).get("id") or r.get("id")
            # 主流程侧：subFlowList = 每个 callActivity 一条（前端算的值，后端不推导）。
            # 缺它 → 子流程页「被以下工作流触发」为空。字段名与线上模版一致：
            # {subProcessId, subNodeName, status:1}
            sfl, seen = [], set()
            for n in _walk_nodes(nodes):
                if n.get("type") != "subprocess":
                    continue
                a2 = n.get("attr") or {}
                pid = a2.get("customProcessId")
                key = (pid, n.get("name"))
                if key in seen:
                    continue
                seen.add(key)
                sfl.append({"subProcessId": pid, "subNodeName": n.get("name"), "status": 1})
                obj = a2.get("subFormTableObject")
                if isinstance(obj, dict) and pid:
                    sub_links.append({"sub_id": pid, "sub_name": a2.get("processName"),
                                      "node_name": n.get("name"), "obj": dict(obj),
                                      "main_id": str(fid), "main_name": name,
                                      # 取数节点在网关分支里时，它的结果存在**分支执行**的 redis key 下，
                                      # 子实例读不到 → 子流程所有 ref() 取空（2026-09-22 销售 R3 后端日志实证）
                                      "nested": _in_branch(nodes, obj.get("nodeId"))})
            if sfl:
                pj["subFlowList"] = sfl
                # 二次保存必带 updateCount：新建的那条要先查一次当前值（乐观锁）
                again = MC.query_flow(a.api_base, a.token, flow_id=fid,
                                      tenant_id=a.tenant_id) or {}
                MC.save_flow(a.api_base, a.token, config, pj, flow_id=fid,
                             update_count=again.get("updateCount"))
            MC.deploy_flow(a.api_base, a.token, fid, tenant_id=a.tenant_id, low_app_id=a.app_id)
            log("OK:%s %s id=%s" % ("upd" if rec else "main", name, fid))
            ok += 1
        except Exception as e:                                    # noqa: BLE001
            log("FAIL:main %s %s" % (name, str(e)[:170]))
            fail += 1

    # ③ 子流程登记回填 —— **后端不会替你做**，设计器是自己算好一起提交的
    #    （2026-09-17 实测：两个应用、29 条子流程，靠 API 存完之后
    #     `formTableList[0].isSubStart` 与 `subFlowSourceInfo` 一条都没回填上，
    #     于是子流程页「数据源」空白、「被以下工作流触发」为空、点进去白屏）。
    #    主流程侧：`subFlowList` = 每个 callActivity 一条，前端算的。
    #    子流程侧：`formTableList[0]`（数据源）+ `subFlowSourceInfo`（谁调我）。
    if a.update or True:
        log("OK:backfill 子流程登记回填 %d 条引用" % len(sub_links))
        for lk in sub_links:
            try:
                srec = MC.query_flow(a.api_base, a.token, flow_id=lk["sub_id"],
                                     tenant_id=a.tenant_id)
                if not srec:
                    log("FAIL:backfill 子流程 %s 查不到" % lk["sub_name"])
                    continue
                spj = srec.get("processJson")
                spj = json.loads(spj) if isinstance(spj, str) else (spj or {})
                obj = dict(lk["obj"])
                obj["nodeTypeMain"] = "getMore"
                obj["nodeType"] = "search"          # 子流程侧是 search（主流程侧是 getMore）
                # ⚠️ 登记名是「子流程」这个**别名**，不是父流程那个 get_more 节点的名字：
                # 金标 增加/减少库存子流程 里父节点叫「从单条记录获取关联记录」，
                # 子流程登记的照样是「子流程」。填成父节点名时设计器下拉会显示成像表名。
                obj["nodeName"] = SUB_ROW_NAME
                ftl = spj.get("formTableList") or []
                if ftl and ftl[0].get("isSubStart"):
                    ftl[0] = obj
                else:
                    spj["formTableList"] = [obj] + [e for e in ftl if not e.get("isSubStart")]
                # ⚠️ `subFormTableObject` 必须**三处一致**：父流程 callActivity 节点、子流程 `start.attr`、
                # 子流程 `formTableList[0]`（金标 `example/主子流程配置示例.md` 第 2/6 条）。
                # 回填趟此前只写了第三处，`start.attr` 留着空壳 `{nodeTypeMain: null}` + `formTableId: null`，
                # 引擎拿不到「本次处理的是哪张表」→ 子流程里 `ref()` 取空、`var()` 正常，记账类子流程每次都走
                # missing 分支、新建的行只有 var 写进去的那几个字段（2026-09-22 进销存 R3 实测，四道闸门全绿）。
                sattr = spj.setdefault("attr", {})
                sattr["subFormTableObject"] = dict(obj)
                sattr["formTableId"] = obj.get("formTableId")
                sattr.setdefault("formTableCode", obj.get("formTableCode"))
                sattr.setdefault("formTableName", obj.get("formTableName"))
                src = [x for x in (spj.get("subFlowSourceInfo") or [])
                       if x.get("mainProcessId") != lk["main_id"]]
                src.append({"mainProcessName": lk["main_name"],
                            "nodeName": lk["node_name"],
                            "mainProcessId": lk["main_id"]})
                spj["subFlowSourceInfo"] = src
                # 子流程「本行字段」引用定形（改用 obj["nodeId"] = 父流程那个 get_more 节点）。
                # ⚠️ 只在取数节点位于**主链路**时才改：分支里的取数，子实例读不到（见 _in_branch）
                if lk.get("nested"):
                    log("OK:backfill 子流程 %s 的取数节点在网关分支里 → 取值来源保持 table/start"
                        "（search 形态在这种拓扑下运行时取空）" % lk["sub_name"])
                else:
                    _fix_sub_ownrow_refs(spj, obj.get("nodeId"), log)
                # ⚠️ 第一个参数必须是**建流程时的 config**（processName/processKey/startType…），
                # 不能拿 processJson 顶替 —— 那里面没有这些键，save 会把 processName/
                # processKey 写成空串，流程记录当场被写坏。
                # 2026-09-17 实测：26 条回填把 25 条子流程写成空名，列表里直接查不到了。
                cfg = dict(srec)
                MC.save_flow(a.api_base, a.token, cfg, spj, flow_id=str(lk["sub_id"]),
                             update_count=srec.get("updateCount"))
                MC.deploy_flow(a.api_base, a.token, lk["sub_id"],
                               tenant_id=a.tenant_id, low_app_id=a.app_id)
                # 改写细节由 _fix_sub_ownrow_refs 自己打（OK:subrow …），此处只报回填本身
                log("OK:backfill %s ← %s / %s"
                    % (lk["sub_name"], lk["main_name"], lk["node_name"]))
                ok += 1
            except Exception as e:                                # noqa: BLE001
                log("FAIL:backfill %s %s" % (lk["sub_name"], str(e)[:150]))
                fail += 1

    log("OK:done %s %d / 跳过 %d / 失败 %d，%.1fs"
        % ("更新" if a.update else "建", ok, skip, fail, time.time() - t0))
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
