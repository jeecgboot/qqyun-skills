# -*- coding: utf-8 -*-
"""一条命令建完一个低代码应用 —— 7 段流水线编排器。

    python build_app.py --api-base URL --token TOKEN --tenant-name 租户名 \
        --app-name 应用名 --spec app_spec.json [--flows flows.py] \
        [--from 补丁] [--only 建壳,补丁] [--dry-run]

流程两个入口都收：`--flows flows.py`（flow_dsl DSL，文档各处推荐的那种）
或 spec 里的 `flows` 数组。2026-09-17 之前**只认后者**，于是「按文档写完 flows.py、
跑 build_app 却打『规格里没有流程，跳过』、应用建出来 0 流程」——
那句日志是误导性的，不是「没有流程」，是「这个入口读不到你的流程」。

## 7 段（顺序不能改）

    ① 字典    应用级字典（**必须最先**：补丁阶段要拿 dictCode 去绑）
    ② 建壳    52 张表的标量字段，分片 ≤12 表/批 —— 避免打满后端 20 连接池
    ③ 补丁    跨表关联 / 他表 / 汇总 / 字典绑定 / 自动编号 / 公式（每表一次读改写）
    ④ 布局    按业务分节重排（divider 段标题 + card 每卡 ≤3 字段）
              → 再把规格 `容器` 点名的字段 MOVE 进 Tabs（Tabs 固定落表单末尾）
              ★ 必须在补丁**之后**：补丁是「一个字段一张卡」地追加，
                字段没齐就排 = 白排（2026-09-17 实测的布局事故）
              ★ 两小步的**内部顺序也不能反**：先分节、后装容器。反过来的话
                容器字段不在任何分节里，会被分节重新分卡**摊平出来**
    ⑤ 灌数    测试数据（★ **必须排在流程之前**，见下）
    ⑥ 流程    简流，先子后主
    ⑦ 看板    应用内看板

每段结束回读计数并打一行 `[N/7 阶段] 期望 X / 实际 Y`；有缺口即非零退出。

## 为什么灌数必须排在流程之前

`add_data` 会触发该表的 tableEvent 主流程，而主流程普遍带「取多条 → 逐行调子流程」——
灌 N 行 = **N 轮级联写**。实测按「先流程后灌数」跑，灌数 **1h4m** 且后端崩过一次。
流程还没建时先灌：不产生级联，也没有「忘记灌完恢复流程」的风险。

## 为什么建壳要分片

`create_linked_worksheets.py` 建表用的是 `max_workers=len(forms)`——**并发无上限**，
52 张表就是 52 个并发子进程直冲后端，而 Druid 连接池只有 20。分片是编排层的职责，
不去改既有脚本的行为。重跑幂等（已存在的表打 `[阻止]` 被跳过），可断点续跑。

规格格式见 `references/app-spec.md`。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from spec_infer import infer, explicit, normalize_containers, default_precision    # noqa: E402

if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# ⚠️ 「布局」必须夹在「补丁」和「灌数」之间：补丁阶段是**一个字段一张卡**地追加，
# 只有等字段全齐了才能按业务分节重排（divider + card）。顺序错了 = 白排。
STAGES = ['字典', '建壳', '补丁', '布局', '灌数', '流程', '看板']
SHELL_CHUNK = 12            # 建壳每批表数（并发 = 表数，别超连接池）
from skill_temp_path import app_workdir, bind_workspace, find_workspace, workspace_of   # noqa: E402  中间产物落 <工作目录>/build/
DATA_BUDGET = 300           # 灌数总预算（秒）。超了就当尽力而为收工，不拦交付（--data-budget 可改）


def log(*a):
    print(*a, flush=True)


def run_script(script, argv, label):
    """跑一个兄弟脚本（一次一段，不是每操作一次）。"""
    p = subprocess.run([sys.executable, script] + [str(x) for x in argv],
                       capture_output=True, timeout=3600)
    text = ((p.stdout or b'') + b'\n' + (p.stderr or b'')).decode('utf-8', errors='replace')
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith(('OK:', 'FAIL:', '[N/', '[')):
            log('   %s' % s)
    if p.returncode != 0:
        log('FAIL:%s exit=%s' % (label, p.returncode))
    return p.returncode


# ---------------- 规格 → 各引擎的输入 ----------------

def split_fields(form, spec):
    """把 spec 的 `字段` 拆成「建壳要建的」和「补丁阶段建的」。

    建壳：叶子字段（类型推断）+ 字典字段（只给 name+type，绑定留到补丁）+ 自动编号
    补丁：关联记录 / 他表 / 汇总 / 公式（都要运行时 model/key）
    """
    name = form['名称']
    links = {l.get('字段'): l for l in (spec.get('links') or []) if l.get('表') == name}
    carried = {c for l in (spec.get('links') or []) if l.get('表') == name
               for c in (l.get('带出') or [])}
    # 「带出映射」：**本表控件名 ≠ 目标表字段名** 的他表字段。`带出` 只能建出与目标表
    # 同名的控件，于是「销售换货」要从「仓库信息」带出两个仓库的名称/编码时，
    # 一组要叫「换货入库仓库名称/编码」、另一组要叫「换货出库仓库名称/编码」，
    # 同名会互相顶掉 —— 规格此前表达不了，只能建完手改。写法：
    #   {"带出映射": {"换货入库仓库名称": "仓库名称", "换货入库仓库编码": "仓库编码"}}
    carried |= {c for l in (spec.get('links') or []) if l.get('表') == name
                for c in (l.get('带出映射') or {})}
    sums = {s.get('字段') for s in (spec.get('summaries') or []) if s.get('表') == name}
    # 「中转字段」：隐藏的取值信封，**必须留给补丁阶段建** —— 它的默认值是
    # `$<父关联控件 key>.<父表字段 model>$`，那两个 id 建壳时还不存在。
    # 漏进建壳清单会**静默**建出一个不带默认值的空 input，补丁阶段再 `if find_widget: continue`
    # 直接跳过 —— 表现是「字段在、但是空的」，流程照样取不到值（2026-09-21 加）。
    relay = set((form.get('中转字段') or {}).keys())
    dicts = form.get('字典') or {}
    multisel = set(form.get('多选') or [])
    # 静态选项：**不绑应用字典**的多选/单选（如 产品权限：销售/采购/赠送）。
    # 不写这两个键时它只会落到 `infer()` → `input`，前端是个空文本框；而 `多选`
    # 只在「绑了字典」的分支里生效（它是「字典字段走 checkbox 还是 select」的开关）。
    # 2026-09-17 建 52 表应用实测踩到：产品权限静默变成文本框，只能事后补丁改控件。
    static_multi = form.get('静态多选') or {}
    static_one = form.get('静态单选') or {}
    # 「下拉单选」：静态写死的 select。规格原先**表达不了这一档** —— `静态单选` 固定落
    # radio、`字典` 那档又要求选项来自应用字典，于是需求写「下拉单选」时作者只能写
    # `静态单选`，建出来是一排横排单选钮。2026-09-20 实测：16 表应用里 25 个「下拉单选」
    # 字段（跨 10 张表）全部中招，precheck 不报（它只认字段名、不看控件偏好）。
    static_sel = form.get('静态下拉') or {}
    nums = form.get('编号') or {}
    formulas = form.get('公式') or {}
    # 「日期粒度」：日期控件的档位（year/month/quarter/week/date/datetime_s/datetime_sf/datetime）。
    # 2026-09-20 加：此前**整条链路都不透传** —— 创建器 job 认 `dateType`
    # （desform_creator 把 `dateType` 映射到工厂的 `date_type`），但 build_app 从不写它，
    # 于是所有日期字段一律落成 `options.type='date'`（年月日）。需求写「**年份**」的
    # （机会年份）会显示年月日；写「**日期时间**」的（外出时间/回来时间）也只剩年月日。
    # 两类都是用户一眼能看出、接口却全绿的偏差。
    dates = form.get('日期粒度') or {}
    # 「显式类型」：`infer()` 是猜名字，猜错时规格此前**没有补救的口子**，只能建完表
    # 再单独改控件。这里给一个 {字段名: 中文类型名} 的映射，**优先于 infer**。
    # 只覆盖叶子类型；下拉/关联/汇总/公式各有自己的声明键。
    explicit_types = form.get('类型') or {}

    # ⚠️ `必填` / `选项` 以前**在规格里根本表达不了**，于是在这里被丢掉：
    # `required` 在 spec→建壳 的整条链路上**没有任何消费者**，`f('客户名称','input',
    # required=True)` 是纯装饰；控件级选项（附件个数上限那类）同理，连写的地址都没有。
    # 表现是**静默**的：应用照建，只是字段不是必填、附件没有上限，接口零报错。
    # 2026-09-18 实测：全应用 10 个 `required=True` 字段全是空操作。
    # 建壳器那边一直是支持的（`_PARAM_MAP` 里有 required/multiple），缺的只是把值传下去。
    must = set(form.get('必填') or [])
    extras = form.get('选项') or {}

    shell, patch = [], []
    for f in form.get('字段') or []:
        if f in links or f in carried or f in sums or f in relay:
            patch.append(f)
            continue
        if f in dicts:
            d = {'name': f, 'type': 'checkbox' if f in multisel else 'select'}
        elif f in static_multi:
            d = {'name': f, 'type': 'checkbox', 'options': static_multi[f]}
        elif f in static_sel:
            d = {'name': f, 'type': 'select', 'options': static_sel[f]}
        elif f in static_one:
            d = {'name': f, 'type': 'radio', 'options': static_one[f]}
        elif f in dates:
            # type 固定 date，具体档位交给 dateType（创建器翻译 → 工厂 date_type → options.type）
            d = {'name': f, 'type': 'date', 'dateType': dates[f]}
        elif f in nums:
            d = {'name': f, 'type': 'auto-number'}
        elif f in formulas:
            d = {'name': f, 'type': 'formula'}
        elif f in explicit_types:
            # 显式类型优先于 infer()：名字猜错了就在这里纠正（如「技术协议」是附件上传）
            d = {'name': f, 'type': explicit(explicit_types[f])}
        else:
            d = {'name': f, 'type': infer(f)}
        if f in must:
            d['required'] = True
        d.update(extras.get(f) or {})       # 控件级选项（precheck 按白名单校验过）
        # 费率/比例/百分比的 number 默认 2 位小数（工厂默认 0 → 1.5% 填不进，见 spec_infer.default_precision）
        prec = default_precision(f, d.get('type'), d)
        if prec is not None:
            d['precision'] = prec
        shell.append(d)
    return shell, patch


def make_job(spec, tenant_id, app_id):
    forms = []
    for f in spec.get('forms') or []:
        shell, _ = split_fields(f, spec)
        if not shell:
            continue
        names = [x['name'] for x in shell]
        title = f.get('标题')
        forms.append({
            'name': f['名称'],
            'code': f['code'],
            'group': f.get('分组'),
            'titleIndex': names.index(title) if title in names else 0,
            'fields': shell,
        })
    return {'tenantId': str(tenant_id), 'appId': str(app_id), 'forms': forms}


def _pv(v):
    """渲染一个值为 flow_dsl 表达式。

    ⚠️ 不能直接 `json.dumps` 整个流程：`flow_dsl` 的 `flow()/approve()/ref()` 是**函数调用**，
    产出的是带标记的 Python 结构；把原始 JSON 塞进去，引擎会报「未知节点类型」
    （2026-09-16 实测：'未知节点类型: approve'）。
    """
    if isinstance(v, dict):
        if '$ref' in v:
            return 'ref(%r, node=%r)' % (v['$ref'], v.get('$node') or 'start')
        if '$lit' in v:
            return 'lit(%r)' % (v['$lit'],)
        return '{%s}' % ', '.join('%r: %s' % (k, _pv(x)) for k, x in v.items())
    if isinstance(v, list):
        return '[%s]' % ', '.join(_pv(x) for x in v)
    return repr(v)


def _pn(node):
    """渲染一个流程节点：`{"fn":"approve","args":{...}}` → `approve(name='审批', ...)`。"""
    fn = node.get('fn')
    if not fn:
        raise SystemExit('流程节点缺 fn：%r' % (node,))
    args = node.get('args') or {}
    return '%s(%s)' % (fn, ', '.join('%s=%s' % (k, _pv(v)) for k, v in args.items()))


def make_flows_py(spec):
    lines = ['# -*- coding: utf-8 -*-  (build_app.py 自动生成)',
             'from flow_dsl import *', '', 'FLOWS = [']
    for f in spec.get('flows') or []:
        kind = f.get('kind') or 'main'
        ctor = 'subflow' if kind in ('sub', 'subflow') else 'flow'
        kw = {k: v for k, v in f.items() if k not in ('nodes', 'kind')}
        argstr = ', '.join('%s=%s' % (k, _pv(v)) for k, v in kw.items())
        nodes = ', '.join(_pn(n) for n in (f.get('nodes') or []))
        lines.append('    %s(%s, nodes=[%s]),' % (ctor, argstr, nodes))
    lines.append(']')
    return '\n'.join(lines) + '\n'


def make_dashboards(spec):
    """看板规格里的表名 → 表单 code。

    `build_dashboards.py` 的 docstring 明说：`charts` 的键**优先写 code**，
    按中文名走 `--form-name` 在「desform.lowAppId 与应用 ID 不一致」的环境会退化成
    菜单兜底、漏表（它自述的实测：52 表应用里 `--form-name 客户` 直接解析失败）。
    规格作者只该写业务语言（表的中文名），翻译成 code 是编排器的活——
    否则每份规格都要求人肉记住 52 个 `t<hash>NN`，那正是这套流水线要消灭的负担。
    """
    code_of = {}
    for f in spec.get('forms') or []:
        if f.get('名称'):
            code_of[f['名称']] = (f.get('code') or '').strip() or f['名称']
    pages = []
    for p in spec.get('pages') or []:
        q = dict(p)
        q['charts'] = {code_of.get(k, k): v
                       for k, v in (p.get('charts') or {}).items()}
        pages.append(q)
    return {'pages': pages}


# ---------------- 各段 ----------------

def stage_dicts(spec, a, work):
    items = spec.get('字典') or {}
    if not items:
        log('[1/7 字典] 规格里没有字典，跳过')
        return 0
    dicts_py = os.path.join(_HERE, 'lowapp_dict.py')
    ok = 0
    for name, opts in items.items():
        cfg = {'dictName': name,
               'dictItemsList': [{'itemText': o if isinstance(o, str) else o.get('itemText')}
                                 for o in opts]}
        p = os.path.join(work, 'dict.json')
        with open(p, 'w', encoding='utf-8') as fh:
            json.dump(cfg, fh, ensure_ascii=False)
        r = subprocess.run([sys.executable, dicts_py, '--api-base', a.api_base,
                            '--token', a.token, '--tenant-id', str(a.tenant_id),
                            '--app-id', str(a.app_id), '--action', 'add', '--config', p],
                           capture_output=True, timeout=300)
        txt = ((r.stdout or b'') + (r.stderr or b'')).decode('utf-8', errors='replace')
        # 已存在时后端报错，视为通过（幂等）
        ok += 1 if (r.returncode == 0 or '已存在' in txt or 'exist' in txt.lower()) else 0
    log('[1/7 字典] 期望 %d / 就位 %d' % (len(items), ok))
    return 0 if ok == len(items) else 5


def stage_shell(spec, a, work):
    job = make_job(spec, a.tenant_id, a.app_id)
    forms = job['forms']
    clw = os.path.join(_HERE, 'create_linked_worksheets.py')
    rc = 0
    for i in range(0, len(forms), SHELL_CHUNK):
        chunk = forms[i:i + SHELL_CHUNK]
        p = os.path.join(work, 'job_%02d.json' % (i // SHELL_CHUNK))
        with open(p, 'w', encoding='utf-8') as fh:
            json.dump({'tenantId': job['tenantId'], 'appId': job['appId'],
                       'forms': chunk}, fh, ensure_ascii=False)
        log('   批次 %d-%d / %d' % (i + 1, i + len(chunk), len(forms)))
        rc |= run_script(clw, ['--api-base', a.api_base, '--token', a.token,
                               '--config', p], '建壳')
    got = count_forms(a)
    log('[2/7 建壳] 期望 %d / 实际 %d' % (len(forms), got))
    if got < len(forms):
        return 5
    return rc_menu_order(spec, a, '建壳')


def menu_order_of(spec):
    """规格 → [(分组, [菜单名...])]。

    给了 `菜单顺序` 用它；没给就按 `forms` 的书写顺序（分组按首次出现）。
    `forms` 的书写顺序**不影响建表**（关联/汇总都在补丁段才建），所以两种写法等价 ——
    `菜单顺序` 只在「想按依赖顺序写 forms、又要另一个菜单顺序」时才需要。
    """
    mo = spec.get('菜单顺序')
    if mo:
        pairs = mo.items() if isinstance(mo, dict) else [(x.get('分组'), x.get('工作表') or []) for x in mo]
        return [(g or None, list(ns)) for g, ns in pairs]
    order = {}
    for f in spec.get('forms') or []:
        order.setdefault(f.get('分组') or None, []).append(f['名称'])
    return list(order.items())


def rc_menu_order(spec, a, stage):
    """建表是并行的，菜单排序号天然错乱且会重复 —— 每次建完都强制按规格重排并回读。

    2026-09-21 实测事故：24 表 6 分组应用，分组与组内顺序全乱，而建壳/补丁/闸门全绿
    （当时没有任何一环核对顺序，只核对了「表在不在对的分组里」）。
    """
    from desform_lowapp_utils import init_lowapp, apply_menu_order
    init_lowapp(a.api_base, a.token, a.tenant_id, a.app_id)
    # 建壳时看板还没建：点名了看板名不算错，等看板段建完再排一次
    r = apply_menu_order(menu_order_of(spec), a.app_id, missing='skip' if stage == '建壳' else 'error')
    for c in r['changed']:
        log('   OK:menu-order %s' % c)
    for p in r['problems']:
        log('   FAIL:menu-order %s' % p)
    log('[%s] 菜单顺序 %s' % (stage, '回读不符 %d 处' % len(r['problems']) if r['problems'] else '已按规格排好（回读一致）'))
    return 5 if r['problems'] else 0


def stage_patch(spec, a, work):
    pf = os.path.join(_HERE, 'patch_fields.py')
    sp = os.path.join(work, 'spec_for_patch.json')
    with open(sp, 'w', encoding='utf-8') as fh:
        json.dump(spec, fh, ensure_ascii=False)
    rc = run_script(pf, ['--api-base', a.api_base, '--token', a.token,
                         '--tenant-id', a.tenant_id, '--app-id', a.app_id,
                         '--spec', sp], '补丁')
    log('[3/7 补丁] %s' % ('完成' if rc == 0 else '有缺口（见上面原因分组）'))
    return rc


def stage_containers(spec, a, work):
    """第④段后半：把规格 `容器` 点名的控件搬进 Tabs 容器。

    ⚠️ **必须紧跟在分节之后**。分节会把字段重新分卡，容器再从中把点名的控件摘走；
    顺序反过来（先装容器、再分节）时，容器字段不在任何分节里，会落进 `rest` 被
    **重新分卡摊平出来** —— 容器还在，里面的控件没了。

    这一步以前根本不存在：规格语言里没有「容器」，需求写「XX 用多 tab」时只能把控件
    平铺建出来、事后再手工搬，且**交付时没有任何东西会告诉你 tab 没建**。
    """
    todos = []
    for f in (spec.get('forms') or []):
        cons, errs = normalize_containers(f)
        for e in errs:
            log('FAIL:[4/7 布局] %s' % e)
        if errs:
            return 5
        if cons:
            todos.append((f.get('名称'), f.get('code'), cons))
    if not todos:
        return 0

    from desform_utils import (init_api, query_form,
                               save_design_from_file, group_into_tabs)
    init_api(a.api_base, a.token)
    made = 0
    for name, code, cons in todos:
        try:
            design = json.loads(query_form(code)['desformDesignJson'])
        except Exception as e:                                    # noqa: BLE001
            log('FAIL:[4/7 布局] 取不到表「%s」的设计：%s' % (name, str(e)[:90]))
            return 5
        try:
            rep = group_into_tabs(design, cons)
        except KeyError as e:
            log('FAIL:[4/7 布局] 表「%s」%s' % (name, e))
            return 5
        if rep['skipped']:
            log('OK: %s 容器已存在，跳过：%s' % (name, '、'.join(rep['skipped'])))
        if not rep['made']:
            continue
        p = os.path.join(work, 'tabs_%s.json' % code)
        with open(p, 'w', encoding='utf-8') as fh:
            json.dump(design, fh, ensure_ascii=False)
        try:
            save_design_from_file(code, p)
        except Exception as e:                                    # noqa: BLE001
            log('FAIL:[4/7 布局] 表「%s」容器保存失败：%s' % (name, str(e)[:90]))
            return 5
        made += 1
        for cname, flds in rep['moved'].items():
            log('OK: %s 容器「%s」装入 %d 个控件：%s'
                % (name, cname, len(flds), '、'.join(flds)))
    log('[4/7 布局] 容器：%d 张表新建 / %d 张已有' % (made, len(todos) - made))
    return 0


def stage_layout(spec, a, work):
    """按业务分节重排所有表的布局（divider 段标题 + card 每卡 ≤3 字段），
    再把规格 `容器` 点名的字段装进 Tabs。

    规格里没有 `layouts` 就跳过分节（不硬造分组，免得把顺序排乱）—— 但**容器照装**：
    两者是独立的规格键，只写 `容器` 不写 `layouts` 是合法的。
    """
    layouts = spec.get('layouts')
    rg = os.path.join(_HERE, 'regroup_layout.py')
    if not layouts:
        log('[4/7 布局] 规格里没有 layouts，跳过分节（表单保持默认排布）')
        # 标题照样要修：建壳时标题若是关联记录/他表字段/汇总（补丁阶段才建出来），titleField
        # 先落在第一个普通字段上，以前只有分节脚本顺手改回 —— 没写 layouts 就整批不修
        # （2026-09-24 进销存-速测18：25 张表标题错，交付检查不报）
        rc = run_script(rg, ['--api-base', a.api_base, '--token', a.token,
                             '--tenant-id', a.tenant_id, '--app-id', a.app_id,
                             '--titles-only', '--spec', a.spec], '标题')
        return rc | stage_containers(spec, a, work)
    # 分节名单里可以写**容器名**（夹在字段中间的选项卡，app-spec「layouts」节）：容器在分节之后才建，
    # 第一遍先把容器名摘掉排好分节，装完容器再按完整名单排一遍，选项卡就落到声明位置
    # （以前 precheck 拦容器名、容器一律落在末尾，只能建完另跑 regroup_layout 挪，CRM-速测18/19）
    cnames = {}
    for f in (spec.get('forms') or []):
        cs = {c.get('名称') for c in (f.get('容器') or []) if isinstance(c, dict) and c.get('名称')}
        if cs:
            cnames[f.get('名称')] = cs
    first = {t: [dict(s, 字段=[x for x in (s.get('字段') or []) if x not in cnames.get(t, ())])
                 for s in secs] for t, secs in layouts.items()}
    need_second = any(x in cnames.get(t, ()) for t, secs in layouts.items()
                      for s in secs for x in (s.get('字段') or []))
    lp = os.path.join(work, 'layout.json')
    with open(lp, 'w', encoding='utf-8') as fh:
        json.dump(first, fh, ensure_ascii=False)
    # ⚠️ **必须传 `--spec`**：`regroup_layout.fix_title()` 靠它拿「表名 → 规格里的标题」
    # 才能把 `config.titleField` 指回规格点名的那个控件。不传时 `titles = {}`，
    # `fix_title(design, None)` 直接返回，**一句话不说地 52 张表全不修**。
    # 2026-09-17 实测代价：新应用建完「标题不符 19/52」，只能事后写 dbg.py + fixtitle.py
    # 补一轮 —— 而这轮补丁的代码路径（iter_widgets + model 回填）早已在本文件里存在。
    rc = run_script(rg, ['--api-base', a.api_base, '--token', a.token,
                         '--tenant-id', a.tenant_id, '--app-id', a.app_id,
                         '--config', lp, '--spec', a.spec], '布局')
    log('[4/7 布局] %s' % ('完成' if rc == 0 else '有缺口（见上面逐表输出）'))
    # 容器**必须紧跟分节**：分节重新分卡 → 容器再从中摘走点名的控件（见 stage_containers）
    rc |= stage_containers(spec, a, work)
    if need_second:
        lp2 = os.path.join(work, 'layout_with_tabs.json')
        with open(lp2, 'w', encoding='utf-8') as fh:
            json.dump({t: secs for t, secs in layouts.items() if t in cnames}, fh, ensure_ascii=False)
        rc2 = run_script(rg, ['--api-base', a.api_base, '--token', a.token,
                              '--tenant-id', a.tenant_id, '--app-id', a.app_id,
                              '--config', lp2, '--spec', a.spec], '布局(选项卡归位)')
        log('[4/7 布局] 选项卡按分节名单归位：%s' % ('完成' if rc2 == 0 else '有缺口'))
        rc |= rc2
    return rc


def stage_data(spec, a, work):
    # `--rows` 默认 **0**（= 不灌数）。**只有用户在提示词里明确要求**
    # （「灌测试数据」「造示例数据」「填几条演示数据」…）才传 `--rows N`。
    # 理由：灌数是最贵的一段（要触发级联写、要抽样回读 52 张表），
    #       而多数交付并不需要库里有数据 —— 看板/报表打开时实时查库，空盘也正确。
    # 不跳的话它仍会全量读 52 张表做「抽样回读」，纯浪费一轮（2026-09-16 实测）。
    if not a.rows:
        log('[5/7 灌数] 未要求灌数（--rows 0，默认）：整段跳过')
        return 0

    # ⚠️ 硬闸门：**流程已存在时不许灌数**。
    # `add_data` 会触发该表的 tableEvent 主流程，而主流程普遍带「取多条 → 逐行调子流程」，
    # 灌 N 行 = N 轮级联写。2026-09-16 实测：应用在 10:41 建好 52 条流程后，
    # 10:57 再单独跑 `--only 灌数`，**六分钟没跑完，后端直接失联**（同一天早些时候
    # 干净顺序跑只要 3.7 分钟）。这条不变量以前只写在注释里，靠人记得 —— 而 `--only`
    # 让人可以随手乱序执行。所以在这里拦住，而不是等踩了再解释。
    n_flow = 0
    try:
        n_flow = count_flows(a)
    except Exception:                                             # noqa: BLE001
        pass
    if n_flow:
        log('[5/7 灌数] 跳过 —— 应用里已有 %d 条流程，现在灌数会触发级联写（实测能把后端点挂）。' % n_flow)
        log('      演示数据**不影响交付**：结构已经好了。要补数据就在建流程之前重跑本段。')
        return 0

    mf = os.path.join(_HERE, 'mock_data_fill.py')
    sp = os.path.join(work, 'spec_for_patch.json')
    # ⚠️ **灌数不阻塞交付**：它的产物只是「打开时有内容」，而应用结构（分组/表单/关联/
    # 汇总/字典/流程/看板）在它之前已经建完了。所以无论成功、超预算、还是报错，
    # 这一段都返回 0 让流水线继续 —— 曾经因为它失败把整轮 52 表的结果全丢掉重来。
    # 但**绝不静默**：下面的日志必须写清楚到底灌没灌上，别让人以为数据是齐的。
    rc = run_script(mf, ['--api-base', a.api_base, '--token', a.token,
                         '--tenant-id', a.tenant_id, '--app-id', a.app_id,
                         '--spec', sp, '--rows', a.rows,
                         '--budget', str(DATA_BUDGET)], '灌数')
    if rc == 0:
        log('[5/7 灌数] 完成（或按预算收工）')
    else:
        log('[5/7 灌数] 未完成（exit=%s）—— **跳过，继续建流程/看板**。' % rc)
        log('      应用结构不受影响；只是打开时部分表单/看板可能没有内容。')
        log('      要补数据：建流程之前 `--only 灌数`，或加大 --data-budget。')
    return 0


def _count_flows_in(path):
    """数一个 flows.py 里有多少条（`FLOWS` 是纯数据构造，exec 不联网）。"""
    try:
        import importlib.util
        mf = os.path.normpath(os.path.join(
            _HERE, '..', '..', 'jeecg-lowcode-miniflow', 'scripts'))
        if mf not in sys.path:
            sys.path.insert(0, mf)
        m = importlib.util.spec_from_file_location('_probe_flows', path)
        mod = importlib.util.module_from_spec(m)
        m.loader.exec_module(mod)
        return len(getattr(mod, 'FLOWS', None) or [])
    except Exception:                                             # noqa: BLE001
        return 0


def stage_flows(spec, a, work):
    """建流程。两种喂法都收：

      · `--flows <flows.py>`     —— 文档推荐的批量路径（`flow_dsl` DSL，63 条实测 51 秒）
      · spec 里的 `flows` 数组   —— 编排器自己拼成 flows.py 再喂给同一个引擎

    ⚠️ 2026-09-17 之前**只认后者**，而 `fast-full-chain.md` / `app-spec.md` 一路推荐前者
      —— 结果是「按文档写完 flows.py，跑 build_app 却打一句『规格里没有流程，跳过』、
      应用建出来 52 表 0 流程」，还得再手工补一次 `build_flows`。
      那句日志是**误导性的**：不是「没有流程」，是「这个入口读不到你的流程」。
    """
    if a.flows:
        fp, expect = a.flows, _count_flows_in(a.flows)
    elif spec.get('flows'):
        fp = os.path.join(work, 'flows.py')
        with open(fp, 'w', encoding='utf-8') as fh:
            fh.write(make_flows_py(spec))
        expect = len(spec['flows'])
    else:
        log('[5/7 流程] 规格里没有流程（也没给 --flows），跳过')
        return 0

    bf = os.path.normpath(os.path.join(
        _HERE, '..', '..', 'jeecg-lowcode-miniflow', 'scripts', 'build_flows.py'))
    if not os.path.exists(bf):
        log('FAIL:[5/7 流程] 找不到 build_flows.py: %s' % bf)
        return 5
    rc = run_script(bf, ['--api-base', a.api_base, '--token', a.token,
                         '--tenant-id', a.tenant_id, '--app-id', a.app_id,
                         '--spec', fp], '流程')
    alive = count_flows(a)
    log('[5/7 流程] 源文件 %d 条 / 已启用 %d' % (expect, alive))
    return rc


def stage_pages(spec, a, work):
    pages = (spec.get('pages') or [])
    if not pages:
        log('[6/7 看板] 规格里没有看板，跳过')
        return 0
    bd = os.path.normpath(os.path.join(
        _HERE, '..', '..', 'jeecg-lowcode-dashboard', 'references', 'scripts',
        'build_dashboards.py'))
    if not os.path.exists(bd):
        log('FAIL:[6/7 看板] 找不到 build_dashboards.py: %s' % bd)
        return 5
    dp = os.path.join(work, 'dashboards.json')
    with open(dp, 'w', encoding='utf-8') as fh:
        json.dump(make_dashboards(spec), fh, ensure_ascii=False)
    # 传 --app-id / --tenant-id：应用名会重名（比如旧版改名后同名残留、或大小写差异），
    # 让下游再按名字解析一次纯属自找麻烦——这里已经解析出 id 了，直接给 id。
    rc = run_script(bd, ['--api-base', a.api_base, '--token', a.token,
                         '--tenant-id', a.tenant_id, '--app-id', a.app_id,
                         '--tenant-name', a.tenant_name, '--app-name', a.app_name,
                         '--spec', dp], '看板')
    got = count_pages(a)
    log('[6/7 看板] 期望 %d / 实际 %d' % (len(pages), got))
    return rc or rc_menu_order(spec, a, '看板')          # 新建的看板也是菜单，建完再排一次


# ---------------- 回读计数 ----------------

def _counts(a):
    from desform_lowapp_utils import get_menus
    from desform_utils import init_api, api_request
    init_api(a.api_base, a.token)
    ml = (get_menus(a.app_id) or {}).get('menuList') or []
    forms = [m for m in ml if m.get('type') == 'form']
    drags = [m for m in ml if m.get('type') == 'drag']
    r = api_request('/act/process/extActProcess/listProcess',
                    params={'lowAppId': a.app_id, 'pageNo': 1, 'pageSize': 500}, method='GET')
    fl = ((r.get('result') or {}).get('records')) or []
    alive = [x for x in fl if str(x.get('openStatus')) == '1'
             and str(x.get('processStatus')) == '1']
    return len(forms), len(drags), len(alive)


def count_forms(a):
    try:
        return _counts(a)[0]
    except Exception:                                             # noqa: BLE001
        return -1


def count_flows(a):
    try:
        return _counts(a)[2]
    except Exception:                                             # noqa: BLE001
        return -1


def count_pages(a):
    try:
        return _counts(a)[1]
    except Exception:                                             # noqa: BLE001
        return -1


def main():
    global DATA_BUDGET
    ap = argparse.ArgumentParser(description='一条命令建完一个低代码应用')
    ap.add_argument('--api-base', required=True)
    ap.add_argument('--token', required=True)
    ap.add_argument('--tenant-name', required=True)
    ap.add_argument('--app-name', required=True)
    ap.add_argument('--tenant-id', help='已知就直接给，省一次解析（--tenant-name 仍必填）')
    ap.add_argument('--app-id', help='已知就直接给')
    ap.add_argument('--spec', required=True)
    ap.add_argument('--flows', default='',
                    help='flows.py（flow_dsl 写的 63 条流程）。不给则看 spec 里的 flows 数组')
    ap.add_argument('--create-app', action='store_true',
                    help='新建应用；租户里已有同名应用则报错退出（续跑已有应用改传 --app-id）')
    # ⚠️ 默认 0 = **不灌数**。只有用户提示词明确要求灌数才传 N。
    # 别为了「让看板有东西看」擅自灌 —— 那是用户没要求的数据污染。
    ap.add_argument('--rows', type=int, default=0,
                    help='每表灌几行；**默认 0 = 不灌数**。仅当用户在提示词里明确要求'
                         '（灌测试数据/示例数据/演示数据）时才传 N')
    ap.add_argument('--data-budget', type=int, default=DATA_BUDGET,
                    help='灌数总预算秒数（默认 %d）。超了按尽力而为收工，不阻塞交付；'
                         '0 = 不限时。' % DATA_BUDGET)
    ap.add_argument('--only', default='', help='只跑这些段（逗号分隔）')
    ap.add_argument('--from', dest='from_', default='', help='从这一段开始跑')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    DATA_BUDGET = a.data_budget

    # 规格路径**先绝对化**：`a.spec` 会被透传给子脚本（布局段的 `--spec`）。
    # 现在 `run_script` 不传 cwd、子进程继承本进程 cwd，相对路径侥幸能解析；
    # 但那是实现细节，不该指望。绝对化一次，后面随便怎么调都安全。
    a.spec = os.path.abspath(a.spec)

    with open(a.spec, encoding='utf-8') as fh:
        spec = json.load(fh)

    # 解析租户 / 应用（应用不存在且 --create-app 时自动建）
    sys.path.insert(0, _HERE)
    from create_linked_worksheets import resolve_tenant_app
    cfg = {'tenantName': a.tenant_name, 'appName': a.app_name}
    if a.tenant_id:
        cfg['tenantId'] = a.tenant_id
    if a.app_id:
        cfg['appId'] = a.app_id
    if a.create_app:
        cfg['createApp'] = True
        # --create-app = 必须是新应用。早先遇同名应用会静默复用，2026-09-23 首跑因此把补丁
        # 打进了租户里已存在的另一个同名测试应用（41 张表被改）。续跑已有应用请传 --app-id。
        cfg['newApp'] = not a.app_id
    if a.dry_run and cfg.pop('createApp', None):
        # --dry-run 不许建应用（2026-09-23 实测：先 resolve 再判 dry-run，预演时就真把应用建出来了）
        try:
            a.tenant_id, a.app_id = resolve_tenant_app(cfg, a.api_base.rstrip('/'), a.token)
        except SystemExit as e:
            if '不存在' not in str(e):
                raise
            a.tenant_id, a.app_id = a.tenant_id or '?', 'dryrun'
            log('DRY: 应用「%s」不存在，正式运行时 --create-app 才会创建（预演不建）' % a.app_name)
    else:
        a.tenant_id, a.app_id = resolve_tenant_app(cfg, a.api_base.rstrip('/'), a.token)
    a.api_base = a.api_base.rstrip('/')
    log('租户=%s 应用=%s' % (a.tenant_id, a.app_id))
    if not a.dry_run:
        # spec 放在工作目录（skill_temp_path.py --new）里时，把 app_id 绑进它的 app.json，
        # 之后任何脚本拿 app_id 都能找回同一个目录
        ws = bind_workspace(a.spec, a.app_id, a.app_name, a.tenant_id)
        if ws:
            log('工作目录=%s' % ws)
        else:
            # spec 不在工作目录里（如续跑时拿了一份外面的 spec）：产物仍按 app_id 找回原工作目录
            ws = find_workspace(a.app_id)
            log('工作目录=%s' % (ws + '（spec 不在其中，按 app_id 找回）' if ws
                                else '（没有工作目录，产物落 jeecg-lowcode/%s/）' % a.app_id))
    if a.app_id == 'dryrun':
        # 预演且应用还没建：'dryrun' 只是占位，别当 app_id 在根目录下开 dryrun/（2026-09-24 实测）
        ws = workspace_of(a.spec)
        work = os.path.join(ws, 'build') if ws else app_workdir(None, 'build')
        os.makedirs(work, exist_ok=True)
    else:
        work = app_workdir(a.app_id, 'build')   # <工作目录>/build/：并行多个应用的 tabs_/job_ 互不覆盖

    # 给每张表定 code。**必须是纯 ASCII**：code 会出现在 /desform/api/fields/<code>
    # 这类**路径**（不是 query）里，而 `bi_utils._request` 只 urlencode params、不编码路径，
    # 中文 code 会直接 `UnicodeEncodeError: 'ascii' codec can't encode ...`
    # —— 2026-09-16 实测：看板阶段因此整段失败，页面建出来却是 0 组件。
    import hashlib
    h = hashlib.md5(('%s|%s' % (a.app_name, a.app_id)).encode('utf-8')).hexdigest()[:5]
    for i, f in enumerate(spec.get('forms') or []):
        code = (f.get('code') or '').strip()
        if not code:
            f['code'] = 't%s%02d' % (h, i + 1)
        elif not code.isascii():
            raise SystemExit('表「%s」的 code「%s」含非 ASCII 字符。code 会进 URL 路径，'
                             '必须纯 ASCII（字母/数字/下划线）。请改 spec 里的 code。'
                             % (f.get('名称'), code))

    stages = STAGES
    if a.only:
        stages = [s for s in STAGES if s in {x.strip() for x in a.only.split(',')}]
    elif a.from_:
        if a.from_ not in STAGES:
            raise SystemExit('--from 只能是：%s' % '、'.join(STAGES))
        stages = STAGES[STAGES.index(a.from_):]

    if a.dry_run:
        job = make_job(spec, a.tenant_id, a.app_id)
        n_flow = _count_flows_in(a.flows) if a.flows else len(spec.get('flows') or [])
        log('DRY: 建壳 %d 表 / 补丁 %d 关联 %d 汇总 / 流程 %d%s / 看板 %d'
            % (len(job['forms']), len(spec.get('links') or []),
               len(spec.get('summaries') or []), n_flow,
               '（来自 %s）' % os.path.basename(a.flows) if a.flows else '',
               len(spec.get('pages') or [])))
        for g, ns in menu_order_of(spec):
            log('   菜单 %s：%s' % (g or '（未分组）', '、'.join(ns)))
        for f in job['forms'][:2]:
            log('   例 %s titleIndex=%s 建壳字段=%d 类型=%s'
                % (f['name'], f['titleIndex'], len(f['fields']),
                   ','.join(x['type'] for x in f['fields'][:8])))
        return 0

    t0 = time.time()
    rc = 0
    fn = {'字典': stage_dicts, '建壳': stage_shell, '补丁': stage_patch,
          '布局': stage_layout, '灌数': stage_data, '流程': stage_flows,
          '看板': stage_pages}
    # 分段计时：**只打总耗时等于没打**。2026-09-17 复盘一轮 52 表应用，事后想回答
    # 「1 小时里哪段慢」时，日志里除了看板自报的 76.5s 以外一个字都没有 ——
    # 只能拿文件 mtime 反推，推不出建壳/补丁各占多少。每段尾随一行，成本为零。
    spent = []
    for s in stages:
        log('── %s ──' % s)
        t_s = time.time()
        rc = fn[s](spec, a, work) or rc
        dt = time.time() - t_s
        spent.append((s, dt))
        log('[%s] %.1fs' % (s, dt))
        if rc:
            log('FAIL: 阶段「%s」未通过，停在这里。修好后用 --from %s 续跑。' % (s, s))
            log('累计：%s' % ' / '.join('%s %.1fs' % (n, d) for n, d in spent))
            return rc
    log('OK:全部完成 %.1fs  —— %s'
        % (time.time() - t0, ' / '.join('%s %.1fs' % (n, d) for n, d in spent)))
    # 规格表达不了的档位（子表/记录范围/默认值/按钮流/按钮/视图/导航/开关）别现场手写补丁脚本
    log('NEXT: 还有规格写不下的需求 → references/postbuild-kit.md，写配置后一条命令：')
    log('      python scripts/postbuild_run.py --api-base … --token … --tenant-id %s --app-id %s --dir <配置目录>'
        % (a.tenant_id, a.app_id))
    return 0


if __name__ == '__main__':
    sys.exit(main())
