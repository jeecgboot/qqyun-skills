# -*- coding: utf-8 -*-
"""按业务分节重排**已有工作表**的布局：divider 段标题 + card（每卡 ≤N 个字段），
同时把「标题是他表带出字段」的表的 `config.titleField` 一并修正。

    python scripts/regroup_layout.py --api-base URL --token TOK \
        --tenant-id N --app-id A --config <layout.json> [--spec app_spec.json] [--form 表名] [--dry-run]

`layout.json`：

    {
      "采购退货": [
        {"标题": "采购订单信息", "字段": ["选择采购订单", "采购订单名称", "采购订单编码"]},
        {"标题": "退货信息",     "字段": ["退货申请日期", "退货原因", "退货产品总数"]},
        {"标题": "退货产品明细", "字段": ["退货产品明细"]}
      ]
    }

## 为什么要有这个脚本（2026-09-17 实测）

批量建表时「建壳」只把 ≤50 个字段两两配对，**补丁阶段追加的字段各自单独成卡**，
且全程没有任何 divider。结果线上进销存模版是

    divider「采购订单信息」 → card[3 字段] …（366 张卡里 240 张是 3 字段）

而批量建出来的表是 **20 张 card 平铺、零 divider、每卡 1 字段**——「表单布局和模版不一样」
说的就是这件事。`desform_creator.py` 现在认 `sections` 了，但它只管**新建**；
已经建好的表要用本脚本补。

字段名匹配的是控件的 `name`（= 标签名）。名单不必穷尽：没点名的字段按原顺序收在最后。
分节里写了表上没有的字段名 → **直接报错并列出可用的名字**，不静默少放。

## 2026-09-17 提速：串行读设计 → 预热 + 4 并发

原实现逐表 `query_form(code)`（内部是 `get_form_id` 1~2 次 HTTP + `queryById` 1 次），
**串行**跑 52 张表 —— 这正是 `patch_fields.py` 早就量过的 **4 分 31 秒**那条慢路径，
只是因为两个脚本各写各的，补丁修了、布局没跟上。
现在：`tenantAppFormList`（本来就要调，用来拿 code）顺手预热「code→id」，
再 4 并发读设计 —— 与 `patch_fields.load_designs` 同口径。**写仍然串行**（服务端本来
就把并发写序列化了，加并发只换争抢开销）。

## 顺带修 titleField（--spec）

`build_app` 的 `titleIndex` 只在**建壳字段**里找标题，而明细表的标题（`产品名称`）是
补丁阶段从上游关联**带出来**的 → 找不到就静默回退到 0 号字段，接口零报错。
反正这里已经把 design 读进内存了，给 `--spec` 就顺手改回 `config.titleField`，
省掉一轮 52 张表的「读→核对→再读→改」。**只改 config，不动控件**——
避开 engine-contract #13（换控件类型会换 model，标题字段和上游关联会全部悬空）。
"""
import argparse
import json
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import desform_lowapp_utils as LU              # noqa: E402
from desform_utils import (init_api, query_form, save_design_from_file,   # noqa: E402
                           apply_group_layout, GROUP_WIDE_TYPES)

#: 读设计的并发度。读不占事务、不会像并发写那样把连接池占干（见 patch_fields 同名单例）。
READ_WORKERS = 4


def log(*a):
    print(*a, flush=True)


def inner_of(w):
    if w.get('type') == 'card' and len(w.get('list') or []) == 1:
        return w['list'][0]
    return w


def widgets_of(design):
    """顶层 list → [(widget, key, model)]，与创建器产出的形状对齐。"""
    out = []
    for w in (design.get('list') or []):
        out.append((w, w.get('key', ''), w.get('model', '')))
    return out


def iter_widgets(items):
    for it in (items or []):
        if not isinstance(it, dict):
            continue
        yield it
        for x in iter_widgets(it.get('list')):
            yield x
        for c in (it.get('columns') or []):
            if isinstance(c, dict):
                for x in iter_widgets(c.get('list')):
                    yield x


def prewarm(api_base, token, tenant_id, app_id):
    """一次调用拿全「表单编码 → 表单 ID」+ 表名 → code，省掉逐表的 get_form_id。

    返回 (code_of{表名: code}, n_prewarm)。这个接口本来就要调（拿 code），
    顺手把 id 塞进 `query_form` 的缓存，等于白省 2×N 次 HTTP。
    """
    import urllib.request
    url = ('%s/online/lowApp/miniflow/tenantAppFormList?tenantId=%s'
           % (api_base.rstrip('/'), tenant_id))
    req = urllib.request.Request(url)
    req.add_header('X-Access-Token', token)
    req.add_header('X-Tenant-Id', str(tenant_id))
    req.add_header('X-Low-App-ID', str(app_id))
    with urllib.request.urlopen(req, timeout=120) as resp:
        r = (json.loads(resp.read().decode('utf-8')).get('result') or {})
    me = next((x for x in (r.get('apps') or []) if str(x.get('id')) == str(app_id)), None)
    if not me:
        raise SystemExit('FAIL: 租户里找不到 app=%s' % app_id)
    code_of, n = {}, 0
    for f in (me.get('desforms') or []):
        if f.get('name'):
            code_of[f['name']] = f.get('code')
        if f.get('code') and f.get('id'):
            import desform_utils as DU
            DU._cache_put(f['code'], f['id'], 0)   # uc 由 queryById 那步刷新
            n += 1
    log('OK:prewarm 预热 %d 个表单 ID（省掉 %d 次 HTTP）' % (n, 2 * n))
    return code_of


def transform(design, sections, per_card):
    """就地重排 layout；返回 (divider 数, card 数, 顶层项数)。"""
    widgets = widgets_of(design)
    have = [inner_of(w).get('name') for (w, _, _) in widgets]
    try:
        top, _ = apply_group_layout(widgets, sections, per_card=per_card)
    except KeyError as e:
        raise SystemExit('FAIL: %s' % e)
    design['list'] = top
    return (sum(1 for w in top if w.get('type') == 'divider'),
            sum(1 for w in top if w.get('type') == 'card'), len(top))


def fix_title(design, title):
    """把 `config.titleField` 指回规格点名的那张控件（只改 config）。"""
    if not title:
        return None
    cfg = design.setdefault('config', {})
    tgt = next((x for x in iter_widgets(design.get('list')) if x.get('name') == title), None)
    if not tgt or not tgt.get('model'):
        return 'WARN: 找不到控件「%s」' % title
    if cfg.get('titleField') == tgt['model']:
        return None
    cfg['titleField'] = tgt['model']
    return 'title'


def save_one(code, design, dry_run):
    p = os.path.join(tempfile.gettempdir(), 'jeecg-desform', 'layout_%s.json' % code)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(design, f, ensure_ascii=False)
    if not dry_run:
        save_design_from_file(code, p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--api-base', required=True)
    ap.add_argument('--token', required=True)
    ap.add_argument('--tenant-id', required=True)
    ap.add_argument('--app-id', required=True)
    ap.add_argument('--config', required=True)
    ap.add_argument('--spec', default='', help='app_spec.json（给了就顺手修 titleField）')
    ap.add_argument('--form', default=None, help='只处理这一张表（默认全部）')
    ap.add_argument('--per-card', type=int, default=3)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    with open(a.config, 'r', encoding='utf-8') as f:
        layout = json.load(f)

    titles = {}
    if a.spec:
        with open(a.spec, 'r', encoding='utf-8') as f:
            spec = json.load(f)
        titles = {x['名称']: x.get('标题') for x in (spec.get('forms') or []) if x.get('名称')}

    LU.init_lowapp(a.api_base, a.token, tenant_id=a.tenant_id, app_id=a.app_id)
    init_api(a.api_base, a.token)
    code_of = prewarm(a.api_base, a.token, a.tenant_id, a.app_id)

    todo = [a.form] if a.form else list(layout.keys())
    items = []
    bad = []
    for name in todo:
        if name not in layout:
            continue
        code = code_of.get(name)
        if not code:
            bad.append('工作表不存在: %s' % name)
            continue
        items.append((name, code))

    # ★ 并发读（原实现是逐表串行 query_form ≈ 4 分 31 秒/52 张）
    def _read(item):
        name, code = item
        try:
            return name, code, query_form(code), None
        except Exception as e:                                    # noqa: BLE001
            return name, code, None, e

    with ThreadPoolExecutor(max_workers=READ_WORKERS) as ex:
        results = list(ex.map(_read, items))

    # ★ 串行改写 + 保存（写要保持串行）
    done = 0
    for name, code, fd, exc in results:
        if exc is not None or not fd:
            bad.append('取不到工作表 %s（%s）' % (name, str(exc)[:80]))
            continue
        design = json.loads(fd['desformDesignJson'])
        have = [inner_of(w).get('name') for (w, _, _) in widgets_of(design)]
        try:
            nd, nc, ntop = transform(design, layout[name], a.per_card)
        except SystemExit as e:
            bad.append('%s —— %s；表里现有控件名: %s'
                       % (name, e, '、'.join(x for x in have if x)))
            continue
        note = fix_title(design, titles.get(name))
        try:
            save_one(code, design, a.dry_run)
        except Exception as e:                                    # noqa: BLE001
            bad.append('%s 保存失败: %s' % (name, str(e)[:90]))
            continue
        done += 1
        extra = ''
        if note == 'title':
            extra = '  +titleField→%s' % titles.get(name)
        elif note:
            extra = '  ' + note
            # `fix_title` 返回 WARN = 规格点名的标题控件在本表上找不到 → `config.titleField`
            # **没被改**。这以前只挂在 OK 行尾部，不进 `bad`、不影响退出码，整轮照样
            # 报「✓ 全部完成」—— 正是本文件要消灭的那类静默半坏。标题是交付项，
            # 设不上就得算失败并出现在末尾的失败清单里。
            bad.append('%s 标题未设置：%s' % (name, note))
        log('OK: %s → divider %d / card %d / 顶层 %d 项%s'
            % (code, nd, nc, ntop, extra))

    log('OK:done 处理 %d 张表%s' % (done, '（dry-run，未保存）' if a.dry_run else ''))
    if bad:
        log('\n✗ %d 项失败:' % len(bad))
        for b in bad:
            log('   ' + b)
        return 1
    log('✓ 全部完成')
    return 0


if __name__ == '__main__':
    sys.exit(main())
