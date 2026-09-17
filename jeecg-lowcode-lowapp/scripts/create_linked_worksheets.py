#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在已有低代码应用下并行建工作表，并可选一对一关联记录。

给 AI：不要手写建表+LINK_RECORD。用户给了租户/应用/表名后，Write utf-8 config，
一条命令跑本脚本。Windows 中文必须走 --config 文件，不要 PowerShell --json。

  python create_linked_worksheets.py --api-base <URL> --token <TOKEN> --config job.json
  python create_linked_worksheets.py --api-base <URL> --token <TOKEN> --config -
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from desform_lowapp_utils import init_lowapp, get_apps, get_worksheet_groups, create_app, create_worksheet_group  # noqa: E402
from desform_utils import LINK_RECORD, add_widget, api_request, update_widget  # noqa: E402
from lowapp_creator import list_current_tenants  # noqa: E402

if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

CREATOR = os.path.join(_SCRIPT_DIR, 'desform_creator.py')

DEFAULT_FIELDS = [
    {'name': '编号', 'type': 'auto-number', 'prefix': 'NO'},
    {'name': '名称', 'type': 'input', 'required': True},
    {'name': '金额', 'type': 'money'},
    {'name': '日期', 'type': 'date'},
    {'name': '状态', 'type': 'radio', 'options': ['草稿', '生效', '关闭']},
]


def match_one(items, raw, name_key, strip_suffixes, label):
    raw = (raw or '').strip()
    if not raw:
        raise SystemExit(f'缺少{label}名称')
    exact = [x for x in items if str(x.get(name_key) or '').strip() == raw]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        names = ', '.join(str(x.get(name_key)) for x in exact)
        raise SystemExit(f'{label}「{raw}」匹配到多条: {names}')
    stripped = raw
    for s in strip_suffixes:
        if stripped.endswith(s) and len(stripped) > len(s):
            stripped = stripped[: -len(s)]
            break
    if stripped != raw:
        exact2 = [x for x in items if str(x.get(name_key) or '').strip() == stripped]
        if len(exact2) == 1:
            return exact2[0]
        if len(exact2) > 1:
            names = ', '.join(str(x.get(name_key)) for x in exact2)
            raise SystemExit(f'{label}「{stripped}」匹配到多条: {names}')
    listing = ', '.join(f"{x.get('id')}={x.get(name_key)}" for x in items) or '(空)'
    raise SystemExit(f'未找到{label}: {raw}；现有: {listing}')


def make_code(name):
    h = hashlib.md5(name.encode('utf-8')).hexdigest()[:10]
    return f'ws_{h}'


def default_fields(_form_name):
    return json.loads(json.dumps(DEFAULT_FIELDS, ensure_ascii=False))


def extract_fields(design):
    title = (design.get('config') or {}).get('titleField')
    fields = {}

    def walk(items):
        for item in items or []:
            t = item.get('type')
            if t == 'card':
                walk(item.get('list'))
            elif t == 'grid':
                for col in item.get('columns') or item.get('cols') or []:
                    walk(col.get('list'))
            elif t == 'tabs':
                for pane in item.get('panes') or item.get('list') or []:
                    walk(pane.get('list'))
            elif t in ('divider', 'text', 'buttons'):
                continue
            else:
                name = item.get('name') or ''
                if name and name not in fields:
                    fields[name] = {
                        'model': item.get('model'),
                        'key': item.get('key'),
                        'type': t,
                    }

    walk(design.get('list'))
    return title, fields


def query_design(code):
    r = api_request(f'/desform/queryByCode?desformCode={code}', method='GET')
    if not r.get('success') or not r.get('result'):
        raise RuntimeError(f'queryByCode 失败 {code}: {r}')
    design = json.loads(r['result']['desformDesignJson'])
    return r['result'], extract_fields(design)


def create_one(cfg, api_base, token, tenant_id, app_id):
    p = subprocess.run(
        [
            sys.executable, CREATOR,
            '--api-base', api_base,
            '--token', token,
            '--tenant-id', str(tenant_id),
            '--app-id', str(app_id),
            '--config', '-',
        ],
        input=json.dumps(cfg, ensure_ascii=False).encode('utf-8'),
        capture_output=True,
        timeout=180,
    )
    text = ((p.stdout or b'') + b'\n' + (p.stderr or b'')).decode('utf-8', errors='replace')
    print(text)
    blocked = '[阻止]' in text
    if p.returncode != 0 and not blocked:
        raise RuntimeError(f'创建 {cfg["formCode"]} 失败 (exit={p.returncode})')
    m = re.search(r'标题字段:\s*(\S+)', text)
    return {
        'code': cfg['formCode'],
        'blocked': blocked,
        'title': m.group(1) if m else None,
    }


def models_of(fields, names):
    out = []
    for n in names:
        info = fields.get(n)
        if info and info.get('model'):
            out.append(info['model'])
    return out


def extra_show_fields(fields, title_model):
    preferred = ['名称', '金额', '状态', '日期']
    out = models_of(fields, preferred)
    if out:
        return out
    for info in fields.values():
        if info.get('model') and info.get('model') != title_model and info.get('type') != 'link-record':
            out.append(info['model'])
        if len(out) >= 3:
            break
    return out


def resolve_tenant_app(cfg, api_base, token):
    tid = cfg.get('tenantId') or cfg.get('tenant_id')
    app_id = cfg.get('appId') or cfg.get('app_id')
    tenant_name = cfg.get('tenantName') or cfg.get('tenant_name') or ''
    app_name = cfg.get('appName') or cfg.get('app_name') or ''

    if tid in (None, ''):
        tenants = list_current_tenants(api_base, token)
        tenant = match_one(tenants, tenant_name, 'name', ('租户', '组织'), '租户')
        tid = tenant['id']
        print(f'租户: {tenant.get("name")} id={tid}')
    else:
        print(f'租户 id={tid}')

    init_lowapp(api_base, token, tenant_id=tid)
    if app_id in (None, ''):
        apps = (get_apps(tenant_id=tid).get('apps') or [])
        try:
            app = match_one(apps, app_name, 'appName', ('应用',), '应用')
        except SystemExit:
            # 2026-09-15：应用不存在时不再直接退出——job.json 带 "createApp": true 则自动创建，
            # 否则给出可操作提示（避免先跑一轮失败、再手动补建应用的往返）。
            if not cfg.get('createApp'):
                listing = ', '.join(f"{x.get('id')}={x.get('appName')}" for x in apps) or '(空)'
                raise SystemExit(
                    f'应用「{app_name}」不存在。两种做法：① job.json 加 "createApp": true 自动创建；'
                    f'② 先运行 scripts/lowapp_creator.py --json "{{\\"action\\":\\"create\\",\\"appName\\":\\"{app_name}\\"}}" 创建后再跑。'
                    f'现有应用: {listing}')
            app_id = create_app(tenant_id=tid, app_name=app_name)
            print(f'[createApp] 应用不存在，已自动创建: {app_name} id={app_id}')
            init_lowapp(api_base, token, tenant_id=tid, app_id=app_id)
            return tid, app_id
        app_id = app['id']
        print(f'应用: {app.get("appName")} id={app_id}')
    else:
        print(f'应用 id={app_id}')
    init_lowapp(api_base, token, tenant_id=tid, app_id=app_id)
    return tid, app_id


# fields.type 合法码（2026-09-15 实测；写错 creator 报「未知的控件类型」，
# 并行批建时一张错即整批失败重跑，故在此 fail-fast 预检）。完整说明见
# references/fast-create.md「fields.type 合法码速查」。
KNOWN_FIELD_TYPES = {
    'input', 'textarea', 'number', 'integer', 'money', 'phone', 'email',
    'radio', 'checkbox', 'select', 'date', 'time', 'switch', 'rate', 'slider',
    'imgupload', 'file-upload', 'divider', 'editor', 'text',
    'area-linkage', 'location', 'capital-money', 'text-compose',
    'auto-number', 'select-user', 'select-depart', 'select-depart-post',
    'org-role', 'sub-table-design', 'formula', 'link-record', 'link-field',
}


def normalize_forms(cfg, groups=None):
    """归一表单配置，并决定每张表的归属分组（2026-09-08 规则）。

    应用有工作表分组时默认归第一个（groups 已按 orderNum 升序）；job 可写
    forms[].group=分组中文名 显式指定；应用无分组（groups 空）才不设置。
    """
    forms = cfg.get('forms') or []
    if not forms:
        raise SystemExit('config.forms 不能为空')
    groups = groups or []
    out = []
    for f in forms:
        if isinstance(f, str):
            f = {'name': f}
        name = (f.get('name') or f.get('formName') or '').strip()
        if not name:
            raise SystemExit(f'表单缺 name: {f}')
        code = (f.get('code') or f.get('formCode') or '').strip() or make_code(name)
        fields = f.get('fields') or default_fields(name)

        bad = [fd for fd in fields
               if isinstance(fd, dict) and fd.get('type')
               and fd['type'] not in KNOWN_FIELD_TYPES]
        if bad:
            hint = '; '.join(f"{fd.get('name')}:{fd.get('type')}" for fd in bad)
            raise SystemExit(
                f'表单「{name}」含未知控件类型: {hint}\n'
                '常见纠错: 日期时间=date+dateType:"datetime" / 附件=file-upload / '
                '流水号=auto-number；完整合法码表见 references/fast-create.md')

        group_id = None
        want = (f.get('group') or f.get('groupName') or '').strip()
        if want:
            hit = [g for g in groups if str(g.get('menuName') or '').strip() == want]
            if not hit:
                names = ', '.join(str(g.get('menuName')) for g in groups) or '(应用内无分组)'
                raise SystemExit(f'分组「{want}」不存在；现有分组: {names}')
            if len(hit) > 1:
                raise SystemExit(f'分组「{want}」匹配到多条: '
                                 + ', '.join(g.get('id') for g in hit))
            group_id = hit[0]['id']
        elif groups:
            group_id = groups[0]['id']
        if group_id:
            print(f'  归组: {name} -> 分组 id={group_id}')

        out.append({
            'formName': name,
            'formCode': code,
            'layout': f.get('layout') or 'auto',
            # 业务分节：给了就按 divider + card 排（压过 auto/half）。
            # 没有它时建出来的是「一长串单字段卡、零 divider」，与线上模版形态不同——
            # 详见 desform_utils.apply_group_layout 的说明。
            'sections': f.get('sections'),
            'titleIndex': f.get('titleIndex', 0),
            'fields': fields,
            'appMenuGroupId': group_id,
        })
    return out


def add_one_to_one(from_form, to_form, link, from_meta, to_meta):
    from_code, from_title, from_fields = from_meta
    to_code, to_title, to_fields = to_meta
    from_field = (link.get('fromField') or to_form['formName']).strip()
    to_field = (link.get('toField') or ('所属' + from_form['formName'])).strip()
    show_mode = link.get('showMode') or 'single'
    show_type = link.get('showType') or 'card'

    jobs = []
    keys = {}

    if from_fields.get(from_field, {}).get('type') != 'link-record':
        ws, k, m = LINK_RECORD(
            from_field, to_code, to_title,
            show_fields=extra_show_fields(to_fields, to_title),
            show_mode=show_mode, show_type=show_type,
        )
        jobs.append((from_code, ws, f'{from_form["formName"]} 添加关联记录失败'))
        keys['from'] = (k, m)
    else:
        info = from_fields[from_field]
        keys['from'] = (info['key'], info['model'])
        print(f'{from_form["formName"]} 已有关联记录「{from_field}」，跳过 add_widget')

    if to_fields.get(to_field, {}).get('type') != 'link-record':
        ws, k, m = LINK_RECORD(
            to_field, from_code, from_title,
            show_fields=extra_show_fields(from_fields, from_title),
            show_mode=show_mode, show_type=show_type,
        )
        jobs.append((to_code, ws, f'{to_form["formName"]} 添加反向关联失败'))
        keys['to'] = (k, m)
    else:
        info = to_fields[to_field]
        keys['to'] = (info['key'], info['model'])
        print(f'{to_form["formName"]} 已有关联记录「{to_field}」，跳过 add_widget')

    def do_add(code, ws, err):
        r = add_widget(code, ws)
        if not r or not r.get('success'):
            raise RuntimeError(f'{err}: {r}')
        return r

    if jobs:
        with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
            futs = [ex.submit(do_add, *job) for job in jobs]
            for f in as_completed(futs):
                f.result()

    k_from, m_from = keys['from']
    k_to, m_to = keys['to']

    def upd(code, key, two_way):
        r = update_widget(code, {'options': {'twoWayModel': two_way}}, key=key)
        if not r or not r.get('success'):
            raise RuntimeError(f'{code} twoWayModel 失败: {r}')
        return r

    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = [
            ex.submit(upd, from_code, k_from, m_to),
            ex.submit(upd, to_code, k_to, m_from),
        ]
        for f in as_completed(futs):
            f.result()
    print(f'twoWay: {from_form["formName"]}.{from_field}={m_from} <-> {to_form["formName"]}.{to_field}={m_to}')


def main():
    parser = argparse.ArgumentParser(description='低代码应用：并行建工作表 + 一对一关联记录')
    parser.add_argument('--api-base', required=True)
    parser.add_argument('--token', required=True)
    parser.add_argument('--config', required=True, help='UTF-8 JSON 路径，或 "-" 读 stdin')
    args = parser.parse_args()

    if args.config == '-':
        cfg = json.load(sys.stdin)
    else:
        with open(args.config, 'r', encoding='utf-8') as f:
            cfg = json.load(f)

    api_base = args.api_base.rstrip('/')
    token = args.token
    tid, app_id = resolve_tenant_app(cfg, api_base, token)
    groups = (get_worksheet_groups(app_id).get('groups') or [])
    # 自动创建 job 声明但不存在的分组（2026-09-15 修复：原行为 SystemExit 导致
    # 「空应用 + forms[].group」必现整批失败、只剩空应用）
    declared = []
    for f in (cfg.get('forms') or []):
        if isinstance(f, dict):
            g = (f.get('group') or f.get('groupName') or '').strip()
            if g and g not in declared:
                declared.append(g)
    existing = {str(g.get('menuName') or '').strip() for g in groups}
    created_groups = [g for g in declared if g not in existing]
    for g in created_groups:
        print(f'分组「{g}」不存在，自动创建')
        gid = create_worksheet_group(app_id=app_id, group_name=g)
        if gid:
            # 不等 get_worksheet_groups 刷新（首个分组有迁移副作用、列表接口有延迟），
            # 直接把新分组补进本地列表
            groups.append({'id': str(gid), 'menuName': g})
        else:
            # 返回值拿不到 id（首个分组迁移路径）：重试拉列表按名匹配
            import time
            for _ in range(5):
                time.sleep(2)
                groups = (get_worksheet_groups(app_id).get('groups') or [])
                hit = [x for x in groups if str(x.get('menuName') or '').strip() == g]
                if hit:
                    break
            if not hit:
                raise SystemExit(
                    f'分组「{g}」已创建但拿不到 id（列表接口延迟）；请重跑，'
                    '已创建的表会被 [阻止] 跳过、不会重复')
            print(f'  分组「{g}」id={hit[0]["id"]}（重试拉取成功）')
    if groups:
        print(f'应用内工作表分组 {len(groups)} 个: '
              + ', '.join(f'{g["id"]}={g.get("menuName")}' for g in groups))
    forms = normalize_forms(cfg, groups)

    created = {}
    with ThreadPoolExecutor(max_workers=max(1, len(forms))) as ex:
        futs = {
            ex.submit(create_one, fc, api_base, token, tid, app_id): fc['formCode']
            for fc in forms
        }
        for fut in as_completed(futs):
            created[futs[fut]] = fut.result()

    metas = {}
    by_name = {}
    for fc in forms:
        row, (title, fields) = query_design(fc['formCode'])
        title = title or created[fc['formCode']].get('title')
        metas[fc['formCode']] = (fc['formCode'], title, fields)
        by_name[fc['formName']] = fc
        print(f'{fc["formName"]} id={row.get("id")} code={fc["formCode"]} title={title} fields={list(fields)}')

    link = cfg.get('link')
    if link:
        from_name = (link.get('from') or forms[0]['formName']).strip()
        to_name = (link.get('to') or (forms[1]['formName'] if len(forms) > 1 else '')).strip()
        if from_name not in by_name or to_name not in by_name:
            raise SystemExit(f'link.from/to 必须是 forms 里的 name: {from_name!r} / {to_name!r}')
        ff, tf = by_name[from_name], by_name[to_name]
        add_one_to_one(ff, tf, link, metas[ff['formCode']], metas[tf['formCode']])

    print('DONE')


if __name__ == '__main__':
    main()
