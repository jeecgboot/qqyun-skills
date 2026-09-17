# -*- coding: utf-8 -*-
"""零真机预检 —— 动真机之前，把能静态查出来的错全查掉。

    python precheck.py --spec app_spec.json [--flows flows.py]

**为什么要它**：2026-09-16 建 52 表应用实测 42 分钟，其中约 15 分钟是**真机才暴露的错**
触发的重跑——公式占位符引用了本表没有的字段、看板透视 `val` 传了空数组、
查询面板的 charts 跨了两张表。这些都是**纯静态信息**，本可以在这里挡下来。

预检通过 ≠ 一定对（真机还有接口与权限问题），但**预检不过 = 一定错**，
且不用付一次几分钟的建表/建盘/建流程。

## 2026-09-17 补的四类（各对应一次真机返工，都是纯静态信息）

1. **元组 cond 不再崩**：`flow_dsl` 的 `(字段, 规则, 值)` 里值可能是 `ref()/var()` 的
   dict，老代码 `if c not in ctxf` 直接 `TypeError: unhashable type: 'dict'`
   —— **整段流程校验跑不完**（不是报错几条，是根本没输出）。
2. **`ref(node=...)` 按那个节点的表校验**：老代码一律按上下文表查，
   跨表 `ref("采购入库单编号", node="获取采购入库")` 全被误报（52 表应用刷 30+ 条假错）。
3. **`get_more(..., from_="start")` 必须有同名关联控件**：引擎靠「本表 → 目标表」的
   关联控件建数据对象，缺了它紧跟的 `call_sub` 会报「请先 get_more」级联失败。
   注意 `from_` 要写 **目标表名**，不是关联控件的显示名。
4. **看板的图名不能互为子串**：`add-filter` 的匹配是双向子串，
   一个查询面板的图名命中多张图 → 整盘 FAIL（图已建好、只差筛选栏）。

## 2026-09-17 再补一类：`多选` 写在没绑字典的字段上

5. **`多选` 是开关不是声明**。它只在「字段绑了 `字典`」的分支里生效（决定那个字典字段
   走 checkbox 还是 select）；字段**不在 `字典` 里**时它一个字都不起作用，直接落到
   `infer()` → `input`。表现是**静默**的：不报错、不警告、应用照建，前端多一个空文本框。
   要「不绑字典的静态选项」只能写 `静态多选` / `静态单选`。
   52 表应用实测踩到（`产品权限`：销售/采购/赠送），只能建完再打补丁改控件类型。

设计原则：**读文件，不联网**。所以它能在动真机之前跑，也就能跑很多次。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

#: patch_fields 的重入轮数（带出字段可能由另一条关联建出来）
ROUNDS = 3

errs, warns = [], []
BY_NAME = {}          # 表名 → 表单定义
EFF = {}              # 表名 → 自身字段 ∪ 关联带出的字段（收敛后）
SUBS = set()          # 已定义的子流程名（call_sub 解析用）
SPEC = {}             # 整份规格（get_more(from_="start") 要查 links）
NODES = {}            # 流程名 → {节点名: 节点该表}（ref(node=...) 解析用）


def err(m):
    errs.append(m)


def warn(m):
    warns.append(m)


# ---------------- 规格 ----------------

def load_spec(path):
    with io.open(path, encoding='utf-8') as fh:
        return json.load(fh)


def build_eff(spec):
    """算出每张表「最终会有哪些字段」——自身字段 + 关联带出的他表字段。

    带出字段可能**本身是另一条关联建出来的**（明细表的标题来自它关联的上游表），
    patch_fields 靠最多 ROUNDS 轮重入收敛。这里照它的语义模拟：
    收敛不了的就是真缺口。
    """
    links = spec.get('links') or []
    eff = {n: set(f.get('字段') or []) for n, f in BY_NAME.items()}
    # 收敛结果要写回全局，后面的看板 / 流程检查都依赖它
    EFF.clear()
    EFF.update(eff)
    link_by = {}
    for lk in links:
        t, fld, tgt = lk.get('表'), lk.get('字段'), lk.get('目标')
        if t not in BY_NAME:
            err('links：表「%s」不存在' % t)
            continue
        if tgt not in BY_NAME:
            err('links：%s.%s 的目标表「%s」不存在' % (t, fld, tgt))
            continue
        if fld not in (BY_NAME[t].get('字段') or []):
            err('links：%s 的字段「%s」不在该表自己的字段列表里' % (t, fld))
        if (t, fld) in link_by:
            err('links：%s.%s 重复声明' % (t, fld))
        link_by[(t, fld)] = tgt

    pending = [lk for lk in links
               if lk.get('表') in BY_NAME and lk.get('目标') in BY_NAME]
    for _ in range(ROUNDS):
        still = []
        for lk in pending:
            t, tgt = lk['表'], lk['目标']
            if all(c in eff[tgt] for c in (lk.get('带出') or [])):
                eff[t].update(lk.get('带出') or [])
            else:
                still.append(lk)
        if len(still) == len(pending):
            break
        pending = still
    for lk in pending:
        bad = [c for c in (lk.get('带出') or []) if c not in eff[lk['目标']]]
        err('links：%s.%s → %s 带出 %s，%d 轮内落不下（目标表没有）'
            % (lk['表'], lk['字段'], lk['目标'], '、'.join(bad), ROUNDS))

    for sm in (spec.get('summaries') or []):
        t, fld = sm.get('表'), sm.get('字段')
        lkf, col = sm.get('关联字段'), sm.get('汇总列')
        if t not in BY_NAME:
            err('summaries：表「%s」不存在' % t)
            continue
        if fld not in eff[t]:
            err('summaries：%s 的字段「%s」不在其字段列表里' % (t, fld))
        tgt = link_by.get((t, lkf))
        if not tgt:
            err('summaries：%s 没有关联记录「%s」' % (t, lkf))
        elif col not in eff[tgt]:
            err('summaries：%s.%s ← %s 没有列「%s」' % (t, fld, tgt, col))
    EFF.clear()
    EFF.update(eff)
    return link_by


def check_forms(spec):
    dicts = spec.get('字典') or {}
    for f in (spec.get('forms') or []):
        name = f.get('名称')
        if not name:
            err('有表单没写「名称」')
            continue
        flds = f.get('字段') or []
        if not flds:
            err('表「%s」字段列表为空' % name)
        for k in list((f.get('字典') or {}).values()):
            if k not in dicts:
                err('表「%s」绑了不存在的字典「%s」' % (name, k))
        for fld in (f.get('字典') or {}):
            if fld not in flds:
                err('表「%s」字典字段「%s」不在字段列表里' % (name, fld))
        for fld in list((f.get('编号') or {})) + list((f.get('公式') or {})):
            if fld not in flds:
                err('表「%s」编号/公式字段「%s」不在字段列表里' % (name, fld))
        # 静态选项（不绑应用字典的多选/单选，如 产品权限：销售/采购/赠送）。
        # 规格里不声明时 `spec_infer.infer` 只会给出 input，前端就是个空文本框。
        for key in ('静态多选', '静态单选'):
            for fld, opts in (f.get(key) or {}).items():
                if fld not in flds:
                    err('表「%s」%s 的「%s」不在字段列表里' % (name, key, fld))
                if not opts:
                    err('表「%s」%s 的「%s」选项为空' % (name, key, fld))
                if fld in (f.get('字典') or {}):
                    err('表「%s」的「%s」同时出现在 %s 和 字典 里——绑字典的用 `多选`，'
                        '不绑字典的才用 `%s`' % (name, fld, key, key))
        # ⚠️ `多选` 是**开关**不是**声明**：它只在 `elif f in dicts` 那条分支里生效
        # （决定绑字典的字段走 checkbox 还是 select）。字段**不在 `字典` 里**时它一个
        # 字都不起作用，直接落到 `infer()` → `input`——前端是个空文本框，不报错、
        # 不警告、预检也照样通过。2026-09-17 建 52 表应用实测踩到（产品权限静默变文本框）。
        # 想表达「不绑字典的静态选项」只能写 `静态多选` / `静态单选`。
        for fld in (f.get('多选') or []):
            if fld not in flds:
                err('表「%s」多选 的「%s」不在字段列表里' % (name, fld))
            if fld not in (f.get('字典') or {}):
                err('表「%s」的「%s」写在 `多选` 里但没绑字典——`多选` 只是「字典字段走 '
                    'checkbox 还是 select」的开关，不绑字典时它完全不生效，会静默落成'
                    '文本框。要静态选项请写成 `静态多选`：{"%s": ["选项1", "选项2"]}'
                    % (name, fld, fld))


def check_layouts(spec):
    """分节布局里的字段名必须真的在这张表上——名字写错要等第④段才炸，太晚。"""
    layouts = spec.get('layouts') or {}
    for name, secs in layouts.items():
        f = BY_NAME.get(name)
        if not f:
            err('layouts 里的表「%s」不存在' % name)
            continue
        # 表上的控件 = 建壳字段 + 补丁阶段建的（关联记录的「带出」、汇总）
        have = set(f.get('字段') or [])
        for l in (spec.get('links') or []):
            if l.get('表') == name:
                have |= set(l.get('带出') or [])
        have |= {s.get('字段') for s in (spec.get('summaries') or []) if s.get('表') == name}
        placed = []
        for s in secs:
            if not (s.get('字段') or s.get('标题')):
                err('layouts「%s」里有一个空分节（既没标题也没字段）' % name)
            for fld in (s.get('字段') or []):
                if fld not in have:
                    err('layouts「%s」的字段「%s」不在该表字段里' % (name, fld))
                placed.append(fld)
        dup = sorted({x for x in placed if placed.count(x) > 1})
        if dup:
            err('layouts「%s」里这些字段被放了多次：%s' % (name, '、'.join(dup)))
        miss = [x for x in (f.get('字段') or []) if x not in placed]
        if miss:
            warn('layouts「%s」没点名 %d 个字段（会按原顺序排在最后）：%s'
                 % (name, len(miss), '、'.join(miss[:8])))


def check_formulas(spec):
    for f in (spec.get('forms') or []):
        name = f.get('名称')
        for k, expr in (f.get('公式') or {}).items():
            for ph in re.findall(r'\$([^$]+)\$', expr or ''):
                if ph not in EFF.get(name, set()):
                    err('表「%s」公式「%s」引用了本表没有的字段「%s」' % (name, k, ph))


def check_titles(spec):
    # 靠「关联带出」建出来的字段（补丁阶段才存在）——建壳阶段解析不到。
    link_out = {}
    for l in (spec.get('links') or []):
        link_out.setdefault(l.get('表'), set()).update(l.get('带出') or [])
    for f in (spec.get('forms') or []):
        name, title = f.get('名称'), f.get('标题')
        if not title:
            warn('表「%s」没写标题字段' % name)
        elif title not in EFF.get(name, set()):
            err('表「%s」标题「%s」既不是自身字段，也不是关联带出的字段' % (name, title))
        elif title in link_out.get(name, set()):
            # 2026-09-17 实测：52 表里 19 张明细表的标题就是这么错的——规格写「产品名称」，
            # 该字段由 links 带出（补丁阶段才建），建壳时不存在，带出/汇总/公式分支都跳过它，
            # 构建器**静默回退**成字段列表里下一个能用的控件（例：标题变成「已出库-退货数量」）。
            # 接口全绿、列表标题列却是空的，只有逐表回读 config.titleField 才看得出。
            warn('表「%s」标题「%s」是靠关联带出建的：建壳阶段解析不到，构建器会静默回退成别的字段。'
                 '建完必须回读 config.titleField，不符就把 design["config"]["titleField"] '
                 '改成该控件的 model 再 save_design_from_file' % (name, title))


# ---------------- 看板 ----------------

def check_pages(spec):
    code_of = {}
    for f in (spec.get('forms') or []):
        code_of[f.get('名称')] = (f.get('code') or '').strip() or f.get('名称')
    for p in (spec.get('pages') or []):
        pname = p.get('name')
        if not pname:
            err('有看板没写 name')
            continue
        charts = p.get('charts') or {}
        all_titles = set()
        for form, specs in charts.items():
            table = form if form in BY_NAME else None
            if not table:
                for nm, cd in code_of.items():
                    if form == cd:
                        table = nm
                        break
            if not table:
                err('看板「%s」引用了不存在的表「%s」' % (pname, form))
                continue
            flds = set(EFF.get(table, set())) | {'record_count', 'create_time'}
            for s in specs:
                title = s.get('title') or s.get('componentName') or '?'
                all_titles.add(title)
                dims = s.get('dim')
                dims = [dims] if isinstance(dims, str) else (dims or [])
                vals = s.get('val')
                vals = [vals] if isinstance(vals, str) else (vals or [])
                # ⚠️ 透视表空 val 会让 add-charts 直接失败（实测 25 张盘里 13 张栽在这）
                if s.get('comp') == 'JPivotTable' and not any(vals):
                    err('看板「%s」图「%s」是透视表但 val 为空 —— 清单式透视请给 record_count'
                        % (pname, title))
                for d in ([s.get('grp')] if s.get('grp') else []) + dims + vals:
                    if d and d not in flds:
                        err('看板「%s」图「%s」的字段「%s」不在 %s 里'
                            % (pname, title, d, table))
        # ⚠️ add-filter 的 charts 必须同一张表；跨表要每表一次
        # ⚠️ 且**图名之间不能互为子串**：`qqy_ops.cmd_add_filter` 的 `_chart_hit` 是
        #    `kw == a or kw in a or a in kw`，命中多条就报「同名多张，请用 componentName
        #    精确定位」并让**整张盘 FAIL**（图已建好、只差筛选栏，重跑还得先 --recreate）。
        #    2026-09-17 实测栽了 4 张：对账数量/对账数量2、客户/客户标签分析、堆叠柱形图/堆叠柱形图2。
        all_titles = []
        for form, specs in charts.items():
            for s in specs:
                t = s.get('title') or s.get('componentName')
                if t:
                    all_titles.append(t)

        def _hits(kw):
            return [t for t in all_titles if kw == t or kw in t or t in kw]

        for flt in (p.get('filters') or []):
            names = flt.get('charts') or []
            if not names:
                err('看板「%s」的查询面板没写 charts' % pname)
                continue
            tables = set()
            for n in names:
                for form, specs in charts.items():
                    if any((s.get('title') or s.get('componentName')) == n for s in specs):
                        tables.add(form)
                        break
                else:
                    warn('看板「%s」查询面板引用的图「%s」不在本页 charts 里' % (pname, n))
                hit = _hits(n)
                if len(hit) > 1:
                    err('看板「%s」查询面板的图名「%s」会命中多张图 %s —— add-filter 会直接失败；'
                        '把同页标题改成互不为子串（如「应收对账数量」/「应付对账数量」）'
                        % (pname, n, hit))
            if len(tables) > 1:
                err('看板「%s」的查询面板跨了多张表 %s —— add-filter 必须同表，请每表一条'
                    % (pname, sorted(tables)))


# ---------------- 流程 ----------------

def load_flows(path):
    """执行 flows.py 拿 FLOWS。flow_dsl 是纯数据构造、不联网，所以可以安全 exec。"""
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    mf = os.path.normpath(os.path.join(here, '..', '..',
                                       'jeecg-lowcode-miniflow', 'scripts'))
    if mf not in sys.path:
        sys.path.insert(0, mf)
    m = importlib.util.spec_from_file_location('user_flows', path)
    mod = importlib.util.module_from_spec(m)
    m.loader.exec_module(mod)
    return getattr(mod, 'FLOWS', None) or []


def _node_tables(nodes):
    out = []
    for n in nodes or []:
        if n.get('table'):
            out.append(n['table'])
        for b in (n.get('branches') or []):
            out += _node_tables(b.get('nodes') or [])
    return out


def check_flows(flows, spec):
    if not flows:
        return
    subs = [f for f in flows if f.get('kind') == 'sub']
    SUBS.clear()
    SUBS.update(f['name'] for f in subs)
    names = [f.get('name') for f in flows]
    dup = {n for n in names if names.count(n) > 1}
    if dup:
        err('流程名重复：%s' % '、'.join(sorted(dup)))

    NODES.clear()
    for f in flows:
        name = f.get('name')
        ctx = f.get('table') or f.get('context')
        if ctx not in BY_NAME:
            err('流程「%s」的表「%s」不存在' % (name, ctx))
            continue
        ctxf = EFF.get(ctx, set())
        NODES[name] = _node_map(f.get('nodes'), ctx)
        for t in _node_tables(f.get('nodes')):
            if t not in BY_NAME:
                err('流程「%s」引用了不存在的表「%s」' % (name, t))
        for node in (f.get('nodes') or []):
            _check_node(name, ctx, ctxf, node)


def _node_map(nodes, ctx, out=None):
    """流程内「节点名 → 该节点产出的表」——`ref(字段, node=X)` 要按 X 的表校验。"""
    out = {} if out is None else out
    for n in nodes or []:
        if not isinstance(n, dict):
            continue
        if n.get('name') and n.get('type') != 'subprocess':
            out[n['name']] = n.get('table') or ctx
        for b in (n.get('branches') or []):
            _node_map(b.get('nodes'), ctx, out)
        _node_map(n.get('found'), ctx, out)
        _node_map(n.get('missing'), ctx, out)
    return out


def _check_node(fname, ctx, ctxf, node, depth=0):
    if depth > 4:
        return
    t = node.get('type')
    if t == 'get_one' or t == 'get_more':
        tb = node.get('table')
        for c in (node.get('cond') or []):
            # ⚠️ 两种写法都要收（2026-09-17 修）：
            #   · 字符串       → 同名匹配：字段要在**上下文表**和**目标表**都有
            #   · (字段,规则,值) → 显式：字段名是**目标表**的，值可能是 ref()/var() 的 dict
            # 老版本直接 `if c not in ctxf`，元组里带 dict 会
            # `TypeError: unhashable type: 'dict'`，**整段流程校验跑不完**。
            fld = c if isinstance(c, str) else (c[0] if isinstance(c, (list, tuple)) and c else None)
            if fld is None:
                err('流程「%s」cond 形态无法识别：%r' % (fname, c))
                continue
            if isinstance(c, str) and fld not in ctxf:
                err('流程「%s」cond「%s」：上下文表 %s 没有该字段（两侧同名才取得到值）'
                    % (fname, fld, ctx))
            if tb in BY_NAME and fld not in EFF.get(tb, set()):
                err('流程「%s」cond「%s」：目标表 %s 没有该字段' % (fname, fld, tb))
        # 「取本单的关联明细」= `get_more(..., from_="start")`，引擎要拿**本表指向目标表的
        # 那条关联控件**（selectType=3 + linkFormTableField）。本表没有这条关联时，
        # 设计器里「选择数据对象」空白、紧跟的 call_sub 直接报「子流程尚未构建」级联失败。
        # 2026-09-17 实测：4 条主流程栽在这里（写的是**关联控件的显示名**而非**目标表名**，
        # 例如「采购退货.退货产品明细」的目标表其实叫「采购退货产品明细」）。
        if t == 'get_more' and str(node.get('from') or '') in ('start', '工作表事件触发'):
            if tb in BY_NAME and not any(
                    l.get('表') == ctx and l.get('目标') == tb for l in (SPEC.get('links') or [])):
                err('流程「%s」get_more("%s", from_="start")：本表 %s 没有指向「%s」的关联记录'
                    '（from_="start" 要写**目标表名**，不是关联控件的显示名）'
                    % (fname, tb, ctx, tb))
    elif t in ('data_update', 'data_add'):
        tb = node.get('table')
        if tb not in BY_NAME:
            return
        for k in (node.get('mapping') or {}):
            if k not in EFF.get(tb, set()):
                err('流程「%s」写 %s.%s：目标表没有该字段' % (fname, tb, k))
    elif t == 'subprocess':
        if node.get('sub') not in SUBS:
            err('流程「%s」call_sub 调了未定义的子流程「%s」' % (fname, node.get('sub')))
    elif t == 'exclusive':
        brs = node.get('branches') or []
        # 排他网关至少要 2 个出口，且必须留一支不带条件做默认支。
        # 2026-09-17 实测：只写「如果 X 就走这一支」而漏掉「其他情况」那支时，
        # save_flow 全绿、deploy 才报「检测到排他网关, 仅有一个出口却配置了条件！」——
        # 4 条审批链整条发布不出来，得再跑一轮 build_flows（全量重发 234s）。
        if len(brs) < 2:
            err('流程「%s」网关「%s」只有 %d 个出口：排他网关至少 2 支，'
                '且其中一支不带条件（默认支 / 「其他情况进入此流程」）'
                % (fname, node.get('name'), len(brs)))
        elif not any(not (b.get('cond') or []) for b in brs):
            err('流程「%s」网关「%s」的 %d 个出口全带条件：必须留一支不带条件的默认支'
                % (fname, node.get('name'), len(brs)))
        for b in brs:
            for (fld, _rule, _val) in (b.get('cond') or []):
                if fld not in ctxf:
                    err('流程「%s」网关条件字段「%s」不在上下文表 %s 里' % (fname, fld, ctx))
            for n in (b.get('nodes') or []):
                _check_node(fname, ctx, ctxf, n, depth + 1)


def _walk_ref_nodes(node, out):
    """收集 `($ref, $node)` 对——**带 node 的 ref 取的是那个节点产出的记录**。"""
    if isinstance(node, dict):
        if '$ref' in node:
            out.append((node['$ref'], node.get('$node') or 'start'))
        for v in node.values():
            _walk_ref_nodes(v, out)
    elif isinstance(node, list):
        for v in node:
            _walk_ref_nodes(v, out)


def check_flow_refs(flows):
    """`ref()` 分两种来源校验（2026-09-17 修）：

    · `node=start`（缺省）→ 取**上下文行**的字段，必须在本表（含带出）里；
    · `node=<取单/新增节点名>` → 取**那个节点产出的记录**的字段，要按**那个节点的表**查。

    老版本一律按上下文表查，跨表 `ref(字段, node="获取采购入库")` 全部误报——
    实测一个 52 表应用会刷 30+ 条假错误，等于把流程段的校验废掉。
    """
    for f in flows:
        name = f.get('name')
        ctx = f.get('table') or f.get('context')
        if ctx not in BY_NAME:
            continue
        ctxf = EFF.get(ctx, set())
        by_node = NODES.get(name) or {}
        refs = []
        _walk_ref_nodes(f.get('nodes') or [], refs)
        for r, nd in refs:
            if nd in ('start', '子流程', '工作表事件触发'):
                if r not in ctxf:
                    err('流程「%s」ref("%s")：上下文表 %s 没有该字段（子流程只能读本行）'
                        % (name, r, ctx))
                continue
            tb = by_node.get(nd)
            if tb is None:
                err('流程「%s」ref("%s", node=%r)：流程里没有这个节点名'
                    % (name, r, nd))
            elif r not in EFF.get(tb, set()):
                err('流程「%s」ref("%s", node=%r → %s)：该表没有这个字段'
                    % (name, r, nd, tb))


# ---------------- 数量 ----------------

def check_counts(spec, expect):
    # 分组同时来自表单和看板（「经营看板」这类组只有看板、没有表单）
    got = {
        '分组': len({x.get('分组') for x in (spec.get('forms') or []) if x.get('分组')}
                  | {x.get('group') for x in (spec.get('pages') or []) if x.get('group')}),
        '表单': len(spec.get('forms') or []),
        '字典': len(spec.get('字典') or {}),
        '看板': len(spec.get('pages') or []),
    }
    for k, v in got.items():
        print('  %s：%d%s' % (k, v, ('（期望 %d）' % expect[k]) if expect.get(k) else ''))
    for k, want in (expect or {}).items():
        if want and got.get(k) != want:
            err('%s 数 %d ≠ 期望 %d' % (k, got.get(k), want))


def main():
    ap = argparse.ArgumentParser(description='零真机预检：规格 + 流程静态校验，不联网')
    ap.add_argument('--spec', required=True)
    ap.add_argument('--flows', default='', help='flows.py（可选）')
    ap.add_argument('--no-flows', action='store_true',
                    help='显式声明本应用没有流程（跳过「漏传 --flows」的拦截）')
    ap.add_argument('--expect', default='',
                    help='数量期望，如 "汇总=7,表单=52,字典=22,看板=25"')
    a = ap.parse_args()

    spec = load_spec(a.spec)
    global BY_NAME
    SPEC.clear()
    SPEC.update(spec)
    for f in (spec.get('forms') or []):
        if f.get('名称') in BY_NAME:
            err('表名重复：%s' % f['名称'])
        BY_NAME[f.get('名称')] = f
    EFF.update({n: set(f.get('字段') or []) for n, f in BY_NAME.items()})

    expect = {}
    for kv in (a.expect or '').split(','):
        if '=' in kv:
            k, v = kv.split('=', 1)
            expect[k.strip()] = int(v)

    print('—— 数量 ——')
    check_counts(spec, expect)

    print('—— 工作表 / 关联 / 汇总 ——')
    build_eff(spec)
    check_forms(spec)
    check_formulas(spec)
    check_titles(spec)
    check_layouts(spec)

    print('—— 看板 ——')
    check_pages(spec)

    if a.flows:
        print('—— 流程 ——')
        flows = load_flows(a.flows)
        print('  流程：%d（子 %d / 主 %d）'
              % (len(flows), len([x for x in flows if x.get('kind') == 'sub']),
                 len([x for x in flows if x.get('kind') == 'main'])))
        check_flows(flows, spec)
        check_flow_refs(flows)
    elif not a.no_flows:
        # ⚠️ 2026-09-17 实测事故：漏传 --flows 时流程段**整段不跑**，
        # 却照样打印「✓ 预检通过 —— 可以动真机了」。那一轮 63 条流程带着 19 个静态
        # 就能查出来的错上了真机，代价是一轮 19 条失败 + 两轮 234s 全量重发。
        # 「绿灯」必须覆盖用户手上真实存在的流程，否则就是假绿灯。
        cand = []
        if spec.get('flows'):
            cand.append('spec 里的 flows 数组')
        d = os.path.dirname(os.path.abspath(a.spec))
        try:
            for fn in sorted(os.listdir(d)):
                if not fn.endswith('.py'):
                    continue
                try:
                    txt = io.open(os.path.join(d, fn), encoding='utf-8').read()
                except Exception:
                    continue
                if re.search(r'^\s*FLOWS\s*=', txt, re.M):
                    cand.append(fn)
        except OSError:
            pass
        if cand:
            err('漏传 --flows，流程段整段没校验（发现 %s）。'
                '流程的错只会在真机上暴露 —— 用 --flows <flows.py> 重跑；'
                '确实没有流程就加 --no-flows 显式跳过' % '、'.join(cand))

    print()
    if warns:
        print('⚠ 提示 %d 条：' % len(warns))
        for w in warns[:20]:
            print('  -', w)
        if len(warns) > 20:
            print('  … 还有 %d 条' % (len(warns) - 20))
    if errs:
        print('✗ 预检不通过 %d 条：' % len(errs))
        for e in errs[:60]:
            print('  -', e)
        if len(errs) > 60:
            print('  … 还有 %d 条' % (len(errs) - 60))
        raise SystemExit(1)
    # 「通过了」这句话只在没有任何提示时才敢说满 —— 提示里躺着的是「接口全绿但内容错」那类，
    # 用户看到 ✓ 就不会再往下看提示（2026-09-17 实测：19 张表的标题就是这么漏掉的）。
    print('✓ 预检通过 —— 可以动真机了' if not warns
          else '✓ 预检通过（有 %d 条提示，逐条确认过再动真机）' % len(warns))


if __name__ == '__main__':
    if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')       # Windows 中文输出
    main()
