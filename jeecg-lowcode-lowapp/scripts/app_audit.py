# -*- coding: utf-8 -*-
"""真机回读核验 —— `precheck.py` 的联网姊妹件。

    python app_audit.py --api-base URL --token TOK --tenant-id N --app-id A \
        --spec app_spec.json [--flows flows.py] \
        [--expect "表单=47,字典=32,看板=16"] [--form 表名]

**输入只有 `app_spec.json` + `flows.py`，零应用知识** —— 所有断言都由规格反推，
所以任何应用/任何提示词通用。`--form X` 只查一张表 = **单表小样**，
补丁脚本改完先跑它，别整批跑完才发现解析写错。

## 与 precheck 的分工

| | precheck.py | 本脚本 |
|---|---|---|
| 联网 | 否 | 是 |
| 时机 | 动真机**前** | 每段跑完 / 交付前 |
| 抓什么 | 规格自洽（占位符、带出字段名、看板透视空 val） | **「接口全绿但配置没落地」** |

后者是这套流水线最贵的一类错：`save`/`deploy`/回读计数全绿，只有人打开设计器才看得出来。
本脚本把它们变成可断言的：

  · 控件类型 / 档位（`type` + `dictCode`/`numberRules`/`expression`/`format`）
  · 关联记录的 条数·显示 / 双向互指 / 带出是否**存储**
  · 汇总的 linkTable 与汇总列
  · 标题字段（构建器对「靠关联带出的标题」会**静默回退**成别的字段）
  · **流程要用到的键在明细行上是否物理存在且存储**（engine-contract 第五节，
    从 `flows.py` 的 `ref()` / 同名字段 `cond` **推导**，不照抄任何表）
  · 看板：盘标题是否被追加到数组末尾（渲染到盘底）、每排宽和、图表引用的字段是否真实存在

退出码：0=无违例（可能有提示）；1=有违例。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from design_utils import (find_widget, form_codes, init_pages,  # noqa: E402
                          is_saved_field, iter_widgets, menu_index,
                          page_key, page_template, widget_index)
from spec_infer import explicit                                    # noqa: E402

BAD, WARN = [], []


def err(m):
    BAD.append(m)
    print('  x %s' % m)


def warn(m):
    WARN.append(m)
    print('  ! %s' % m)


def ok(m):
    print('  . %s' % m)


# ---------------------------------------------------------------- 规格侧小工具

def load_spec(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def load_flows(path):
    if not path:
        return []
    import importlib.util
    mf = os.path.normpath(os.path.join(_HERE, '..', '..',
                                       'jeecg-lowcode-miniflow', 'scripts'))
    if mf not in sys.path:
        sys.path.insert(0, mf)
    m = importlib.util.spec_from_file_location('_audit_flows', path)
    mod = importlib.util.module_from_spec(m)
    try:
        m.loader.exec_module(mod)
    except NameError as ex:
        # 建后套件的简流配置（button_flow/appr/upd 那套）与 flow_dsl 的 flows.py 同名，传错必 NameError
        # （2026-09-22 项目管理 R2）。套件配置请改名 pb_flows.py，`--flows` 只收 flow_dsl 那份
        raise SystemExit('FAIL: --flows 要的是 flow_dsl 写的 flows.py（定义 FLOWS = [...]），'
                         '%s 看起来是建后套件的 pb_flows.py：%s' % (path, ex))
    return getattr(mod, 'FLOWS', None) or []


def deep_walk(obj):
    """深度遍历任意嵌套结构（dict / list / **tuple**）。

    ⚠️ 必须收 tuple：`cond` 写的是 `(字段, 规则, 值)` 元组，元素里还可能是
    `ref(...)`。只认 dict/list 会让**元组里的引用整个丢掉**
    （2026-09-21 实测：`cond=[("产品编码","等于",ref("产品编码"))]` 的 ref 漏掉，
    推导出的键从 212 掉到 204 —— 检查静默变松，正好漏掉流程真正要读的键）。
    """
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            yield cur
            stack.extend(cur.values())
        elif isinstance(cur, (list, tuple)):
            stack.extend(cur)


def patch_fields_of(spec, table):
    """该表里**补丁阶段才建**的字段名（关联/带出/汇总）——与 `build_app.split_fields` 同口径。

    这些字段建壳时不存在，所以「控件类型」那一档要跳过它们（另有专门校验）。
    """
    out = set()
    for l in spec.get('links') or []:
        if l.get('表') != table:
            continue
        out.add(l.get('字段'))
        out.update(l.get('带出') or [])
        out.update((l.get('带出映射') or {}).keys())
    for s in spec.get('summaries') or []:
        if s.get('表') == table:
            out.add(s.get('字段'))
    for f in spec.get('forms') or []:
        if f.get('名称') == table:
            out.update((f.get('中转字段') or {}).keys())
    return out


# ---------------------------------------------------------------- 各段校验


def apply_rename(spec, struct_path, carry_namespace='local'):
    """按 struct 配置的 RENAME={表:{旧名:新名}} 把规格里的字段名换成真机现名。
    审计只吃规格，而**建后 RENAME** 会让规格名与真机名分家 ——
    2026-09-22 CRM 实测 60 条、销售管理 5 条全是这一类假阳性。

    ⚠️ 2026-09-24：RENAME 的**由来**（「规格里斜杠 = 与，写不了 `X/元`」）已被证伪 ——
    代码从来没有按 `/` 拆字段名的地方，规格直接写 `X/元` 就是最终名（见 `app-spec.md`
    「四条硬规矩」第 1 条）。所以新规格**不该再有 RENAME**，这个参数只为读得懂存量配置。

    `carry_namespace` 决定 `links[].带出` 按**谁**的映射改名 —— 两个检查器理解相反：
      · `'local'`（默认）：按**本表**改。把带出当成「本表要建的那些他表字段控件名」，
        与 `app_audit` 的校验口径一致（它核的是本表控件存在）—— 改不得，会把它从 0 条
        变成一堆假违例。
      · `'target'`：按**目标表**改。把带出当成「要从目标表带出哪些字段」——这是真机语义
        （`报价单.选择客户.showFields` 存的是**客户表**的 model），也是 `precheck` 的校验口径
        （`c not in eff[目标]`）。
    带出在 RENAME 前两套名字重合，改名后分家，所以一个值满足不了两边 —— 只能按调用方给。"""
    ns = {}
    try:
        exec(compile(open(struct_path, encoding='utf-8').read(), struct_path, 'exec'), ns)
    except Exception as e:                      # noqa: BLE001
        print('  ! --struct 读取失败，跳过 RENAME：%s' % e)
        return spec
    ren = ns.get('RENAME') or {}
    to_lf = ns.get('TO_LINKFIELD') or {}
    del_mv = ns.get('DELETE_THEN_MOVE') or {}
    link_data = ns.get('LINKDATA') or []
    if not (ren or to_lf or del_mv or link_data):
        return spec
    spec = json.loads(json.dumps(spec, ensure_ascii=False))
    forms = {f.get('名称'): f for f in spec.get('forms') or []}
    # LINKDATA：(表, 字段, 目标表, 目标字段) —— 建后把该字段改成 select + remote=linkData
    # （下拉选项来自工作表）。规格里通常写「单行文本」，审计不读它就必报「声明 input → 实际 select」
    # （2026-09-22 CRM R3 两条假违例）。
    # ⚠️ 这里**只能把该字段从「类型」里摘掉**（摘掉 = 审计跳过这一档），不能改写成「下拉」之类的名字：
    # `spec_infer.TYPE_CN` 里没有映射到 select 的中文名，`explicit()` 认不出就抛 ValueError，
    # 整个审计直接退出（2026-09-22 CRM R4 实测，是上一版这条改动的回归）。
    for row in link_data:
        if not row or len(row) < 2:
            continue
        f = forms.get(row[0])
        if f and isinstance(f.get('类型'), dict):
            f['类型'].pop(row[1], None)
    # TO_LINKFIELD：(本表字段, 经由关联控件, 源表, 源表字段) → 该字段真机上已是他表字段，
    # 挂到对应关联的「带出映射」里：控件类型那一档跳过它、关联那一档核它存在且存储
    for t, rows in to_lf.items():
        for row in rows:
            fld, via, _src, src_f = row[:4]
            lk = next((l for l in (spec.get('links') or []) if l.get('表') == t and l.get('字段') == via), None)
            if lk is None:
                continue
            lk.setdefault('带出映射', {})[fld] = src_f
            if len(row) > 4 and row[4] == 'view':       # 第 5 项 'view' = 仅显示，审计不要求存储（销售-速测19 #2）
                lk.setdefault('仅显示', []).append(fld)
            if fld in (lk.get('带出') or []):
                lk['带出'].remove(fld)
    # DELETE_THEN_MOVE：(要删控件名, 要删类型, 搬入原位的控件名, 其类型) → 被删的名字从规格里拿掉
    for t, rows in del_mv.items():
        f = forms.get(t)
        if not f:
            continue
        gone = {r[0] for r in rows}
        f['字段'] = [x for x in (f.get('字段') or []) if x not in gone]
        f['必填'] = [x for x in (f.get('必填') or []) if x not in gone]
        for k in ('字典', '编号', '公式', '类型', '选项', '静态多选', '静态单选', '静态下拉', '日期粒度', '中转字段'):
            if isinstance(f.get(k), dict):
                f[k] = {kk: v for kk, v in f[k].items() if kk not in gone}
    if not ren:
        return spec

    def rn(t, name):
        return (ren.get(t) or {}).get(name, name)

    def rn_expr(expr, m):
        """把公式表达式里的 $占位符$ 按本表映射改名。m 为空/非字符串时原样返回。"""
        if not isinstance(expr, str) or not m:
            return expr
        return re.sub(r'\$([^$]+)\$',
                      lambda mo: '$%s$' % m.get(mo.group(1), mo.group(1)), expr)

    for f in spec.get('forms') or []:
        t = f.get('名称')
        if t not in ren:
            continue
        f['字段'] = [rn(t, x) for x in (f.get('字段') or [])]
        f['必填'] = [rn(t, x) for x in (f.get('必填') or [])]
        for k in ('字典', '编号', '公式', '类型', '选项', '静态多选', '静态单选', '静态下拉', '日期粒度', '中转字段'):
            if isinstance(f.get(k), dict):
                f[k] = {rn(t, kk): v for kk, v in f[k].items()}
        # ⚠️ 公式的**表达式正文**里还有 $占位符$，上面那行只改了字典的键。
        # 不补这一步，「成本单价」→「成本单价/元」之后公式仍写 `$成本单价$`，
        # 静态检查就会报「引用了本表没有的字段」——2026-09-24 实测 48 条假违例。
        if isinstance(f.get('公式'), dict):
            f['公式'] = {rn(t, kk): rn_expr(v, ren.get(t) or {})
                         for kk, v in f['公式'].items()}
        if f.get('标题'):
            f['标题'] = rn(t, f['标题'])
    for lk in spec.get('links') or []:
        t, tgt = lk.get('表'), lk.get('目标')
        if t in ren:
            lk['字段'] = rn(t, lk.get('字段'))
            lk['带出'] = [rn(t, x) for x in (lk.get('带出') or [])]     # 带出控件在本表的名字
            lk['仅显示'] = [rn(t, x) for x in (lk.get('仅显示') or [])]
            if isinstance(lk.get('带出映射'), dict):
                lk['带出映射'] = {rn(t, k): v for k, v in lk['带出映射'].items()}
        if tgt in ren:
            lk['显示字段'] = [rn(tgt, x) for x in (lk.get('显示字段') or [])]
            if carry_namespace == 'target':
                lk['带出'] = [rn(tgt, x) for x in (lk.get('带出') or [])]  # 要从目标表带出哪些字段
            if isinstance(lk.get('带出映射'), dict):
                lk['带出映射'] = {k: rn(tgt, v) for k, v in lk['带出映射'].items()}
    for sm in spec.get('summaries') or []:
        t = sm.get('表')
        if t in ren:
            sm['字段'] = rn(t, sm.get('字段'))
            sm['关联字段'] = rn(t, sm.get('关联字段'))
        tgt = next((l.get('目标') for l in (spec.get('links') or [])
                    if l.get('表') == t and l.get('字段') == sm.get('关联字段')), None)
        if tgt in ren:
            sm['汇总列'] = rn(tgt, sm.get('汇总列'))
    for t, secs in (spec.get('layouts') or {}).items():
        if t in ren:
            for sec in secs:
                sec['字段'] = [rn(t, x) for x in (sec.get('字段') or [])]
    return spec


def check_scale(spec, flows, expect, idx):
    print('\n[规模]')
    n_form = len(spec.get('forms') or [])
    n_dict = len(spec.get('字典') or {})
    n_page = len(spec.get('pages') or [])
    if len(idx['forms']) != n_form:
        err('工作表 %d / 规格 %d' % (len(idx['forms']), n_form))
    else:
        ok('工作表 %d' % n_form)
    if n_page == 0 and idx['pages']:
        ok('看板 %d（规格未声明 pages，跳过条数比对）' % len(idx['pages']))
    elif len(idx['pages']) != n_page:
        err('看板 %d / 规格 %d' % (len(idx['pages']), n_page))
    else:
        ok('看板 %d' % n_page)
    for k, want in (expect or {}).items():
        got = {'分组': len(idx['groups']), '表单': len(idx['forms']),
               '看板': len(idx['pages']), '字典': n_dict}.get(k)
        if got is None:
            continue
        (ok if got == want else err)('%s %d / 期望 %d' % (k, got, want))
    return n_dict


def check_dicts(spec, n_dict, api_base, token, app_id):
    print('\n[应用字典]')
    from desform_utils import api_request
    r = api_request('/sys/dict/getDictListByLowAppId?lowAppId=%s' % app_id, method='GET')
    items = r.get('result') or []
    if isinstance(items, dict):
        items = items.get('records') or items.get('list') or []
    (ok if len(items) == n_dict else err)('字典 %d / 规格 %d' % (len(items), n_dict))


def check_flows_scale(flows, api_base, token, app_id, tenant_id):
    print('\n[简流]')
    from desform_utils import api_request
    r = api_request('/act/process/extActProcess/listProcess',
                    params={'lowAppId': app_id, 'pageNo': 1, 'pageSize': 1000},
                    method='GET')
    recs = ((r.get('result') or {}).get('records')) or []
    alive = [x for x in recs if str(x.get('openStatus')) == '1'
             and str(x.get('processStatus')) == '1']
    if not flows:
        ok('流程 %d 条（未给 --flows，跳过条数比对）' % len(alive))
        return
    # 建后套件的按钮流/审批流（postbuild_flows）与手建流程不在 flows.py 里：多出来是常态，
    # 少了才是问题（2026-09-22 三个应用各报一条「N / M」全是这一类假阳性）
    if len(alive) < len(flows):
        err('流程启用 %d / flows.py %d（有流程没启用或没建成）' % (len(alive), len(flows)))
    elif len(alive) > len(flows):
        ok('流程启用 %d（flows.py %d，另 %d 条来自建后套件/手建）' % (len(alive), len(flows), len(alive) - len(flows)))
    else:
        ok('流程 %d 条全部启用' % len(alive))


def check_form(spec, form, design, ws, code_ctx):
    """单张表的控件级校验。design = 已解析的设计；ws = widget_index。"""
    t = form['名称']
    patch = patch_fields_of(spec, t)
    must = set(form.get('必填') or [])
    dg = form.get('字典') or {}
    sm = form.get('静态多选') or {}
    so = form.get('静态单选') or {}
    ss = form.get('静态下拉') or {}
    nums = form.get('编号') or {}
    forms_ = form.get('公式') or {}
    types = form.get('类型') or {}
    dates = form.get('日期粒度') or {}

    for fld in form.get('字段') or []:
        if fld in patch:
            continue                      # 关联/带出/汇总另有校验
        w = ws.get(fld)
        if not w:
            err('%s.%s 控件缺失' % (t, fld))
            continue
        got = w.get('type')
        opt = w.get('options') or {}

        if fld in dg:
            # 字典可以绑在 select / radio / checkbox 上（`多选` 那档落 checkbox，
            # 事后手工改成 radio 也是合法的），所以只断言**绑定确实在**。
            if not opt.get('dictCode'):
                err('%s.%s 绑了字典但 dictCode 为空（字典没落地）' % (t, fld))
            elif got not in ('select', 'radio', 'checkbox'):
                err('%s.%s 字典字段的控件类型是 %s' % (t, fld, got))
        elif fld in sm and got != 'checkbox':
            err('%s.%s 静态多选 → 实际 %s' % (t, fld, got))
        elif fld in so and got != 'radio':
            err('%s.%s 静态单选 → 实际 %s' % (t, fld, got))
        elif fld in ss and got != 'select':
            err('%s.%s 静态下拉 → 实际 %s' % (t, fld, got))
        elif fld in nums:
            if got != 'auto-number':
                err('%s.%s 编号 → 实际 %s' % (t, fld, got))
            elif not opt.get('numberRules'):
                err('%s.%s 自动编号规则为空' % (t, fld))
        elif fld in forms_:
            if got != 'formula':
                err('%s.%s 公式 → 实际 %s' % (t, fld, got))
            else:
                expr = opt.get('expression') or ''
                is_date = opt.get('type') == 'date' or opt.get('dateBegin') or opt.get('dateEnd')
                if not expr and not is_date:
                    err('%s.%s 公式表达式为空' % (t, fld))
                elif is_date and not (opt.get('dateBegin') or opt.get('dateAddExp')):
                    err('%s.%s 日期公式没有 dateBegin / dateAddExp' % (t, fld))
                # 占位符必须已经翻成 model：残留 `$中文$` 说明 build_expr 没跑
                import re
                left = [x for x in re.findall(r'\$([^$]+)\$', expr) if re.search(r'[一-鿿]', x)]
                if left:
                    err('%s.%s 公式里残留中文占位符 %s' % (t, fld, '、'.join(left[:3])))
        elif fld in types:
            want = explicit(types[fld])
            if got != want and {got, want} != {'money', 'number'} \
                    and {got, want} != {'input', 'textarea'}:
                err('%s.%s 声明 %s → 实际 %s' % (t, fld, want, got))
        elif fld in must:
            if not opt.get('required'):
                err('%s.%s 是必填但 required 未落' % (t, fld))

        # 日期档位：只管**本表叶子**字段（他表字段的格式在源表上）
        if fld in dates and got != 'link-field':
            want = {'date': 'yyyy-MM-dd', 'datetime': 'yyyy-MM-dd HH:mm:ss'}.get(dates[fld])
            if want and opt.get('format') != want:
                warn('%s.%s 日期档位 %s / 期望 %s' % (t, fld, opt.get('format'), want))

    # 标题字段：构建器解析不了「靠关联带出的标题」会**静默回退**成别的字段
    title = form.get('标题')
    if title and 'code' in code_ctx:
        cur = ((design.get('config') or {}).get('titleField'))
        w = ws.get(title)
        if not w:
            err('%s 标题「%s」控件不存在' % (t, title))
        elif cur != w.get('model'):
            err('%s titleField 指向 %s，规格要「%s」' % (t, cur, title))


def check_links(spec, forms_by_name, design_of, code_of, only=None):
    print('\n[关联记录]')
    n_ok = 0
    for l in spec.get('links') or []:
        t = l.get('表')
        fld = l.get('字段')
        if only and t != only:
            continue
        if t not in code_of:
            err('links：表「%s」不在应用里' % t)
            continue
        d = design_of(t)
        w = find_widget(d, fld, 'link-record')
        if not w:
            err('%s.%s 关联控件不存在' % (t, fld))
            continue
        o = w.get('options') or {}
        # 条数 / 显示
        num = {'单条': 'single', '多条': 'many'}.get(l.get('条数'))
        disp = {'卡片': 'card', '下拉': 'select', '表格': 'table'}.get(l.get('显示'))
        # ⚠️ 无例外：`条数=单条` 只有卡片/下拉，**没有**「表格」档（2026-09-21 踩到）。
        # 曾给 `single+table` 开过 warn 后门、理由是「需求点名 + 收尾脚本改回」——
        # **那个理由本身是错的**：设计器的「显示方式」下拉里没有这一项，落库即坏数据，
        # 用户改不回来。真机出现 single+table = 违例，一律 err。
        if num and o.get('showMode') != num:
            err('%s.%s showMode=%s / 规格 %s' % (t, fld, o.get('showMode'), num))
        if disp and o.get('showType') != disp:
            err('%s.%s showType=%s / 规格 %s' % (t, fld, o.get('showType'), disp))
        if num == 'single' and o.get('showType') == 'table':
            err('%s.%s 是「单条 + 表格」—— 单条没有表格档位，设计器里改不回来' % (t, fld))
        # 双向：两侧互指（只改一侧 = 「半转」）
        if l.get('双向'):
            tw = l['双向']
            back = None
            tgt = l.get('目标')
            for l2 in spec.get('links') or []:
                if l2.get('表') == tgt and l2.get('目标') == t:
                    if tw is True or l2.get('字段') == tw:
                        back = l2
                        break
            if not back:
                err('%s.%s 声明双向但找不到回指控件' % (t, fld))
            else:
                bw = find_widget(design_of(tgt), back.get('字段'), 'link-record')
                if not bw:
                    err('%s.%s 回指控件不存在' % (tgt, back.get('字段')))
                elif o.get('twoWayModel') != bw.get('model') \
                        or (bw.get('options') or {}).get('twoWayModel') != w.get('model'):
                    err('%s.%s ↔ %s.%s 双向未互指（%s / %s）'
                        % (t, fld, tgt, back.get('字段'),
                           o.get('twoWayModel'), (bw.get('options') or {}).get('twoWayModel')))
        # 带出：本表要有他表字段控件，且**存储**（view 的话流程取到空值）
        expect_carry = list(l.get('带出') or []) + list((l.get('带出映射') or {}).keys())
        view_only = set(l.get('仅显示') or [])          # 需求明写「仅显示」的：不要求存储（流程用到时下面的键推导仍会拦）
        for c in expect_carry:
            cw = find_widget(d, c)
            if not cw:
                err('%s.%s 带出「%s」控件不存在' % (t, fld, c))
            elif c not in view_only and not is_saved_field(cw):
                err('%s.%s 带出「%s」是只显示（saveType=%s），流程取不到值'
                    % (t, fld, c, (cw.get('options') or {}).get('saveType')))
        # 显示字段：只展示、不建控件，但名字必须真在目标表上
        for c in (l.get('显示字段') or []):
            if c not in widget_index(design_of(l.get('目标'))):
                err('%s.%s 显示字段「%s」不在目标表 %s 上' % (t, fld, c, l.get('目标')))
        n_ok += 1
    ok('关联 %d 条已回读' % n_ok)


def check_summaries(spec, design_of, code_of, only=None):
    print('\n[汇总]')
    n = 0
    for s in spec.get('summaries') or []:
        t, fld, lkf, col = s.get('表'), s.get('字段'), s.get('关联字段'), s.get('汇总列')
        if only and t != only:
            continue
        if t not in code_of:
            continue
        d = design_of(t)
        w = find_widget(d, fld)
        if not w:
            err('%s.%s 汇总控件不存在' % (t, fld))
            continue
        if w.get('type') != 'summary':
            warn('%s.%s 是 %s（总汇控件应为 summary）' % (t, fld, w.get('type')))
        lw = find_widget(d, lkf, 'link-record')
        o = w.get('options') or {}
        if lw:
            lt = o.get('linkTable')
            if lt not in (lw.get('key'), lw.get('model'),
                          'sub_table_design_%s' % lw.get('key')):
                err('%s.%s 的 linkTable=%s 没指向关联「%s」' % (t, fld, lt, lkf))
        tgt = next((x.get('目标') for x in (spec.get('links') or [])
                    if x.get('表') == t and x.get('字段') == lkf), None)
        # 「计数」汇总不需要汇总列（数记录条数，precheck 也接受不写）——以前按 None 去找列，
        # 每个计数汇总都误报一条（2026-09-24 任务-一句话5 报 4 条）
        if tgt and col and col not in widget_index(design_of(tgt)):
            err('%s.%s 的汇总列「%s」不在 %s 上' % (t, fld, col, tgt))
        n += 1
    ok('汇总 %d 条已回读' % n)


def check_flow_fields(flows, code_of, design_of, only=None):
    """**engine-contract 第五节**：被流程逐行处理的明细表必须**物理携带**它要用的键。

    清单是**推出来的**，不照抄任何表：子流程里
      · `get_one/get_more` 的**字符串** cond（同名匹配）→ 该字段要在上下文表上
      · 任何 `ref(...)` → 同上（子流程的 ref 只解析本行）
    再追加一条：这些字段若是有他表字段，必须 `saveType='save'`（`view` 取到空值）。
    """
    print('\n[流程要用到的键（推导）]')
    need = {}
    for f in flows:
        if only and (f.get('table') or f.get('context')) != only:
            continue
        ctx = f.get('table') or f.get('context')
        if not ctx:
            continue
        for cur in deep_walk(f.get('nodes') or []):
            for c in (cur.get('cond') or []):
                if isinstance(c, str):            # 同名匹配：字段要在上下文表上
                    need.setdefault(ctx, set()).add(c)
            r = cur.get('$ref')
            # ⚠️ 只收 `$node == start` 的引用（= 上下文本行）。
            # `ref("X", node="某节点")` 取的是**那个节点结果表**的字段，
            # 拿它当上下文表的字段会**假报缺失**
            # （2026-09-21 实测：一条「转单」流程的报价单被误报缺「销售订单编号」，
            #   其实那是 ref(..., node="查新销售订单") —— 字段长在新建的那张单上）。
            if r and cur.get('$node') in (None, 'start'):
                need.setdefault(ctx, set()).add(r)
    n_bad = 0
    for ctx, flds in need.items():
        if ctx not in code_of:
            err('流程上下文表「%s」不在应用里' % ctx)
            continue
        ws = widget_index(design_of(ctx))
        for fld in sorted(flds):
            w = ws.get(fld)
            if not w:
                err('%s 缺流程要读的字段「%s」（一行都不会写）' % (ctx, fld))
                n_bad += 1
            elif not is_saved_field(w):
                err('%s.%s 是只显示（saveType=%s），流程取到空值'
                    % (ctx, fld, (w.get('options') or {}).get('saveType')))
                n_bad += 1
    if not n_bad:
        ok('推导出的 %d 个键全部存在且存储' % sum(len(v) for v in need.values()))


def check_relay(spec, design_of, code_of, only=None):
    """**中转字段**（隐藏取值信封）：存在、隐藏、默认值指向对的字段。

    ⚠️ 这一档坏起来全是**静默**的：字段在、能存值，但默认值是空的 →
    子流程建出来的台账行永远没有那个关联记录。save/回读计数一律看不出来。

    规格形态：`forms[i]["中转字段"] = {"<本表字段名>": ("<父表名>", "<父表字段名>")}`
    """
    print('\n[中转字段]')
    n = n_bad = 0
    for f in spec.get('forms') or []:
        t = f.get('名称')
        relay = f.get('中转字段') or {}
        if not relay or (only and t != only) or t not in code_of:
            continue
        try:
            design = design_of(t)
        except Exception:                    # noqa: BLE001
            continue
        for name, pair in relay.items():
            n += 1
            w = find_widget(design, name)
            if not w:
                err('%s.%s 中转字段缺失（补丁阶段没建出来）' % (t, name))
                n_bad += 1
                continue
            if not (w.get('options') or {}).get('hidden'):
                err('%s.%s 中转字段没设隐藏（用户会在表单上看到这个机制字段）' % (t, name))
                n_bad += 1
            parent, pfield = (list(pair) + [None, None])[:2] if isinstance(pair, list) else (None, None)
            pcode = code_of.get(parent)
            host = None
            for x in iter_widgets(design):
                xo = x.get('options')
                if (x.get('type') == 'link-record' and isinstance(xo, dict)
                        and xo.get('sourceCode') == pcode):
                    host = x
                    break
            if not host:
                err('%s.%s 找不到指向「%s」的关联控件，默认值无法解析' % (t, name, parent))
                n_bad += 1
                continue
            got = ((w.get('advancedSetting') or {}).get('defaultValue') or {}).get('value') or ''
            if '$' not in got:
                err('%s.%s 中转字段没有默认值表达式（建出来的明细行会带着空值）' % (t, name))
                n_bad += 1
            elif not got.startswith('$%s.' % host.get('key')):
                err('%s.%s 默认值 %r 没指向「%s」那个关联控件（key=%s）—— 父单据一换就取错行'
                    % (t, name, got, parent, host.get('key')))
                n_bad += 1
    if not n_bad:
        ok('%d 个中转字段都存在、隐藏、默认值指向对' % n)


def option_values(design):
    """设计 → {字段名: {显示名 或 存储值: 存储值}}（只收**有固定选项**的控件）。

    值的**真身**只有设计里的 `options[].value` 一处；`label` 是页面显示名。
    两个方向都塞进同一个 map：写显示名能翻过去、写存储值也算命中（幂等）。
    """
    out = {}
    for w in iter_widgets(design):
        n = w.get('name')
        opts = ((w.get('options') or {}).get('options')) or []
        m = {}
        for it in opts:
            if isinstance(it, dict) and it.get('value') is not None:
                m[str(it['value'])] = it['value']
                if it.get('label') is not None:
                    m[str(it['label'])] = it['value']
        if n and m:
            out[n] = m
    return out


def _one_value(model2field, model, v):
    """一个**字面量**取值是否合法 → 错误描述 / None。变量对象（dict）不判。"""
    if model not in model2field or isinstance(v, (dict, type(None))):
        return None
    t, field, m = model2field[model]
    vals = set(str(x) for x in m.values())
    for x in (v if isinstance(v, list) else [v]):
        if isinstance(x, dict):
            continue
        if str(x) in vals:
            continue
        if str(x) in m:                      # 正好是某个显示名 → 就是这一类错
            return ('%s.%s 写的是**显示名** %r，表单真实存储的是 %r'
                    % (t, field, x, m[str(x)]))
        return ('%s.%s 的值 %r 不是合法存储值（可选：%s）'
                % (t, field, x, "、".join(sorted(vals))[:120]))
    return None


def check_flow_values(code_of, design_of, api_base, token, app_id, only=None):
    """流程里写的**字面量**必须是表单真实存储值，不是页面显示名。

    ⚠️ 2026-09-21 用户实测报障：触发条件写「入库确认 等于 是」，而表单存的是字典值
    `"0"`。落库的 `SuperQueryItem.val="是"`，引擎拿它去 Mongo 里比 `"0"` → **恒不匹配**，
    日志是「匹配不到数据，不满足触发条件！」，**流程静默不触发**。写字段同理：
    把「是」当值写进 `updateFields` / `formModel`，页面上看着是空的。

    这一档 `save`/`deploy`/契约检查**全绿** —— 只有把真机 `processJson` 翻出来、
    拿表单的 options 逐个对照才看得见。所以放在这里，作为交付闸门的一部分。
    条件项、更新字段、新增记录的 formModel 三处都查。
    """
    print('\n[流程里的取值（真机回读）]')
    from desform_utils import api_request
    r = api_request('/act/process/extActProcess/listProcess',
                    params={'lowAppId': app_id, 'pageNo': 1, 'pageSize': 1000},
                    method='GET')
    recs = ((r.get('result') or {}).get('records')) or []
    model2field = {}                     # 字段 model → (表名, 字段名, 显示名→值)
    for t in list(code_of or {}):
        if only and t != only:
            continue
        try:
            d = design_of(t)
        except Exception:                # noqa: BLE001
            continue
        for fname, m in option_values(d).items():
            w = find_widget(d, fname)
            if w and w.get('model'):
                model2field[w['model']] = (t, fname, m)
    n_val = n_bad = 0
    for rec in recs:
        try:
            spj = json.loads(rec.get('processJson') or '{}')
        except ValueError:
            continue
        for node in deep_walk(spj):
            hit = []
            for q in (node.get('queryItems') or []):        # 触发条件 / 网关分支 / 取数
                # 「为空 / 不为空」这两个比较符本来就不带值（val 恒 ""），
                # 拿空串去比选项表必然「不是合法存储值」→ 每条这类条件都是一条假违例
                # （2026-09-22 销售 R4 实测）。同理空值本身也没什么可校验的。
                if str(q.get('rule') or '') in ('empty', 'not_empty') or q.get('val') in ('', None):
                    continue
                hit.append((q.get('field'), q.get('val'), '条件'))
            for u in (node.get('updateFields') or []):      # 更新记录
                hit.append((u.get('field'), u.get('val'), '更新'))
            fm = node.get('formModel')                      # 新增记录
            if isinstance(fm, dict):
                hit += [(k, v, '新增') for k, v in fm.items()]
            # 调子流程传参：字面量若等于某个字典/选项字段的**显示文案**而不是存储值，多半是漏翻
            # （2026-09-22 进销存实测「账向」经 var() 落成文案，本段以前不查、546 处全绿）
            for u in ((node.get('attr') or {}).get('variableList') or []):
                v = u.get('val')
                if isinstance(v, str) and v:
                    for _t, _f, _m in model2field.values():
                        if v in _m and str(_m[v]) != v:
                            err('流程「%s」的传参 %s=%r 像是「%s.%s」的显示文案（存储值 %r），请翻成存储值'
                                % (rec.get('processName'), u.get('field'), v, _t, _f, _m[v]))
                            n_bad += 1
                            break
            for model, v, where in hit:
                n_val += 1
                why = _one_value(model2field, model, v)
                if why:
                    err('流程「%s」的%s %s' % (rec.get('processName'), where, why))
                    n_bad += 1
    if not n_bad:
        ok('%d 条流程 / %d 处字面量取值全部是表单真实存储值' % (len(recs), n_val))


def check_pages(spec, idx, only=None):
    print('\n[看板]')
    code_of = {f['名称']: f.get('code') for f in spec.get('forms') or []}
    for p in spec.get('pages') or []:
        name = p.get('name')
        if only and name != only:
            continue
        pid = idx['pages'].get(name)
        if not pid:
            err('看板「%s」不在菜单里' % name)
            continue
        tmpl, _ = page_template(pid)
        if not tmpl:
            err('看板「%s」组件数 0' % name)
            continue
        want_text = any((u.get('comp') or 'JText') == 'JText' for u in (p.get('ui') or []))
        if want_text and tmpl[0].get('component') != 'JText':
            err('看板「%s」盘标题不在数组下标 0（会渲染到盘底）' % name)
        expect = []
        for grp in (p.get('charts') or {}).values():
            expect.extend(grp)
        charts = [c for c in tmpl
                  if c.get('component') not in ('JText', 'JFilterQuery', 'JCustomButton')]
        if len(charts) != len(expect):
            err('看板「%s」图表数 %d / 规格 %d' % (name, len(charts), len(expect)))
        cover = {}                                   # 每一行 y 被哪些组件覆盖（宽度累加）
        for c in tmpl:
            y0, h = int(c.get('y') or 0), max(int(c.get('h') or 1), 1)
            for yy in range(y0, y0 + h):
                cover[yy] = cover.get(yy, 0) + int(c.get('w') or 0)
        bad_rows = sorted(y for y, s in cover.items() if s > 24)
        gaps = sorted(y for y, s in cover.items() if s < 24)
        if bad_rows:
            err('看板「%s」y=%s 行组件重叠（宽和 %s > 24）' % (name, bad_rows[0], cover[bad_rows[0]]))
        if gaps:
            warn('看板「%s」y=%s 起 %d 行右侧留白（宽和 %s < 24）' % (name, gaps[0], len(gaps), cover[gaps[0]]))
        # 图表引用的字段必须真在对应表上（改了字段名最容易漏）
        for form, specs in (p.get('charts') or {}).items():
            code = code_of.get(form)
            if not code:
                continue
            ws = set(widget_index(design_of(form))) | {
                'record_count', 'create_time', 'update_time', 'create_by', 'update_by',
                'bpm_status', '创建时间', '修改时间', '创建人', '修改人', '流程状态'}
            for s in specs:
                for k in ('dim', 'val', 'grp'):
                    v = s.get(k)
                    vs = [v] if isinstance(v, str) else (v or [])
                    for x in vs:
                        if isinstance(x, dict):
                            x = x.get('field')
                        if x and x not in ws:
                            err('看板「%s」图「%s」的 %s「%s」不在 %s 上'
                                % (name, s.get('title'), k, x, form))
        ok('看板「%s」回读完成' % name)


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser(description='真机回读核验（规格驱动，任何应用通用）')
    ap.add_argument('--api-base', required=True)
    ap.add_argument('--token', required=True)
    ap.add_argument('--tenant-id', required=True)
    ap.add_argument('--app-id', required=True)
    ap.add_argument('--spec', required=True, help='app_spec.json（app_audit 只吃这一份）')
    ap.add_argument('--flows', default='', help='flows.py；给了才校验流程条数与字段可见性')
    ap.add_argument('--no-flows', action='store_true',
                    help='与 precheck 同口径：显式声明没有流程（等同不给 --flows；以前这里报参数错，CRM-速测18）')
    ap.add_argument('--expect', default='', help='如 "表单=47,字典=32,看板=16"')
    ap.add_argument('--form', default='', help='只查这一张表（单表小样）')
    ap.add_argument('--struct', default='', help='建后套件的 struct 配置（读其 RENAME，把规格旧名换成真机现名再比对）')
    ap.add_argument('--pages-only', action='store_true')
    a = ap.parse_args()

    spec = load_spec(a.spec)
    if a.struct:
        spec = apply_rename(spec, a.struct)
    flows = load_flows(a.flows)
    expect = {}
    for kv in (a.expect or '').split(','):
        if '=' in kv:
            k, v = kv.split('=', 1)
            if v.strip().isdigit():
                expect[k.strip()] = int(v.strip())

    from desform_utils import init_api, query_form
    from desform_lowapp_utils import init_lowapp
    init_api(a.api_base, a.token)
    init_lowapp(a.api_base, a.token, tenant_id=a.tenant_id, app_id=a.app_id)
    # 看板侧是**另一套连接**（bi_utils 有自己的 api base / token），不 init 会拼出
    # `/drag/page/queryById?...` 这种没有 host 的 URL，报 unknown url type
    init_pages(a.api_base, a.token)

    code_of, code_to_name = form_codes(a.api_base, a.token, a.tenant_id, a.app_id)
    for f in spec.get('forms') or []:
        if f.get('名称') not in code_of:
            err('规格里的表「%s」在应用里找不到（建壳没建成？）' % f.get('名称'))
    # 规格表名 → code 用规格里的 code 兜底（build_app 会写进 spec）
    for f in spec.get('forms') or []:
        if f.get('code') and f.get('名称') not in code_of:
            code_of[f['名称']] = f['code']

    idx = menu_index(a.app_id)
    print('租户=%s 应用=%s  /  表单 %d · 看板 %d · 分组 %d'
          % (a.tenant_id, a.app_id, len(idx['forms']), len(idx['pages']),
             len(idx['groups'])))

    _cache = {}

    def design_of(table):
        if table not in _cache:
            code = code_of.get(table)
            if not code:
                raise SystemExit('FAIL:表「%s」没有 code，无法回读' % table)
            _cache[table] = json.loads(query_form(code)['desformDesignJson'])
        return _cache[table]

    check_scale(spec, flows, expect, idx)
    check_dicts(spec, len(spec.get('字典') or {}), a.api_base, a.token, a.app_id)
    if flows:
        check_flows_scale(flows, a.api_base, a.token, a.app_id, a.tenant_id)

    if not a.pages_only:
        print('\n[控件类型 / 档位 / 标题]')
        n = 0
        for f in spec.get('forms') or []:
            if a.form and f.get('名称') != a.form:
                continue
            if f.get('名称') not in code_of:
                continue
            d = design_of(f['名称'])
            check_form(spec, f, d, widget_index(d), code_of)
            n += 1
        ok('%d 张表控件级回读完成' % n)

        check_relay(spec, design_of, code_of, only=a.form or None)
        check_links(spec, None, design_of, code_of, only=a.form)
        check_summaries(spec, design_of, code_of, only=a.form)
        if flows:
            check_flow_fields(flows, code_of, design_of, only=a.form)
            check_flow_values(code_of, design_of, a.api_base, a.token, a.app_id,
                              only=a.form or None)

    check_pages(spec, idx, only=None if not (a.form or a.pages_only) else None)

    print('\n==== 违例 %d 条 / 提示 %d 条 ====' % (len(BAD), len(WARN)))
    for m in BAD:
        print('  x %s' % m)
    return 1 if BAD else 0


if __name__ == '__main__':
    sys.exit(main())
