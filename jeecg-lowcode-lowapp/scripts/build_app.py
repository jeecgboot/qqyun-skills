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
              ★ 必须在补丁**之后**：补丁是「一个字段一张卡」地追加，
                字段没齐就排 = 白排（2026-09-17 实测的布局事故）
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

from spec_infer import infer                                   # noqa: E402

if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# ⚠️ 「布局」必须夹在「补丁」和「灌数」之间：补丁阶段是**一个字段一张卡**地追加，
# 只有等字段全齐了才能按业务分节重排（divider + card）。顺序错了 = 白排。
STAGES = ['字典', '建壳', '补丁', '布局', '灌数', '流程', '看板']
SHELL_CHUNK = 12            # 建壳每批表数（并发 = 表数，别超连接池）
WORK = os.path.join(tempfile.gettempdir(), 'jeecg-buildapp')
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
    sums = {s.get('字段') for s in (spec.get('summaries') or []) if s.get('表') == name}
    dicts = form.get('字典') or {}
    multisel = set(form.get('多选') or [])
    # 静态选项：**不绑应用字典**的多选/单选（如 产品权限：销售/采购/赠送）。
    # 不写这两个键时它只会落到 `infer()` → `input`，前端是个空文本框；而 `多选`
    # 只在「绑了字典」的分支里生效（它是「字典字段走 checkbox 还是 select」的开关）。
    # 2026-09-17 建 52 表应用实测踩到：产品权限静默变成文本框，只能事后补丁改控件。
    static_multi = form.get('静态多选') or {}
    static_one = form.get('静态单选') or {}
    nums = form.get('编号') or {}
    formulas = form.get('公式') or {}

    shell, patch = [], []
    for f in form.get('字段') or []:
        if f in links or f in carried or f in sums:
            patch.append(f)
        elif f in dicts:
            shell.append({'name': f, 'type': 'checkbox' if f in multisel else 'select'})
        elif f in static_multi:
            shell.append({'name': f, 'type': 'checkbox', 'options': static_multi[f]})
        elif f in static_one:
            shell.append({'name': f, 'type': 'radio', 'options': static_one[f]})
        elif f in nums:
            shell.append({'name': f, 'type': 'auto-number'})
        elif f in formulas:
            shell.append({'name': f, 'type': 'formula'})
        else:
            shell.append({'name': f, 'type': infer(f)})
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
    return 0 if got >= len(forms) else 5


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


def stage_layout(spec, a, work):
    """按业务分节重排所有表的布局（divider 段标题 + card 每卡 ≤3 字段）。

    规格里没有 `layouts` 就跳过——不硬造分组，免得把顺序排乱。
    """
    layouts = spec.get('layouts')
    if not layouts:
        log('[4/7 布局] 规格里没有 layouts，跳过（表单保持默认排布）')
        return 0
    lp = os.path.join(work, 'layout.json')
    with open(lp, 'w', encoding='utf-8') as fh:
        json.dump(layouts, fh, ensure_ascii=False)
    rg = os.path.join(_HERE, 'regroup_layout.py')
    # ⚠️ **必须传 `--spec`**：`regroup_layout.fix_title()` 靠它拿「表名 → 规格里的标题」
    # 才能把 `config.titleField` 指回规格点名的那个控件。不传时 `titles = {}`，
    # `fix_title(design, None)` 直接返回，**一句话不说地 52 张表全不修**。
    # 2026-09-17 实测代价：新应用建完「标题不符 19/52」，只能事后写 dbg.py + fixtitle.py
    # 补一轮 —— 而这轮补丁的代码路径（iter_widgets + model 回填）早已在本文件里存在。
    rc = run_script(rg, ['--api-base', a.api_base, '--token', a.token,
                         '--tenant-id', a.tenant_id, '--app-id', a.app_id,
                         '--config', lp, '--spec', a.spec], '布局')
    log('[4/7 布局] %s' % ('完成' if rc == 0 else '有缺口（见上面逐表输出）'))
    return rc


def stage_data(spec, a, work):
    # `--rows 0` = 明确不要测试数据 → 整段跳过。
    # 不跳的话它仍会全量读 52 张表做「抽样回读」，纯浪费一轮（2026-09-16 实测）。
    # 交付要求是「不需要灌入测试数据」时，本段不应产生任何读。
    if not a.rows:
        log('[5/7 灌数] --rows 0：不灌测试数据，整段跳过')
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
    return rc


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
    ap.add_argument('--tenant-id', help='已知就直接给，省一次解析')
    ap.add_argument('--app-id', help='已知就直接给')
    ap.add_argument('--spec', required=True)
    ap.add_argument('--flows', default='',
                    help='flows.py（flow_dsl 写的 63 条流程）。不给则看 spec 里的 flows 数组')
    ap.add_argument('--create-app', action='store_true', help='应用不存在则自动创建')
    ap.add_argument('--rows', type=int, default=3, help='每表灌几行')
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
    os.makedirs(WORK, exist_ok=True)

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
    a.tenant_id, a.app_id = resolve_tenant_app(cfg, a.api_base.rstrip('/'), a.token)
    a.api_base = a.api_base.rstrip('/')
    log('租户=%s 应用=%s' % (a.tenant_id, a.app_id))

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
        rc = fn[s](spec, a, WORK) or rc
        dt = time.time() - t_s
        spent.append((s, dt))
        log('[%s] %.1fs' % (s, dt))
        if rc:
            log('FAIL: 阶段「%s」未通过，停在这里。修好后用 --from %s 续跑。' % (s, s))
            log('累计：%s' % ' / '.join('%s %.1fs' % (n, d) for n, d in spent))
            return rc
    log('OK:全部完成 %.1fs  —— %s'
        % (time.time() - t0, ' / '.join('%s %.1fs' % (n, d) for n, d in spent)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
