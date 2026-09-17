#!/usr/bin/env python3
"""把全新创建的设计子表转为独立工作表。

POST /desform/subToWorksheet。body 键名来自前端 Network 实测，禁止改键、禁止探测。

  python sub_to_worksheet.py --api-base <URL> --token <TOKEN> \\
      --tenant-id <TID> --app-id <APP> --parent-code order_info --sub-name 订单明细表

Windows 中文名用 UTF-8 --config（不要 PowerShell --json / python -c）：
  {"parentCode":"order_info","subName":"订单明细表"}
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from desform_lowapp_utils import init_lowapp
from desform_utils import (
    LINK_RECORD,
    api_request,
    delete_form,
    get_form_id,
    query_form,
    save_auth_from_design,
    save_design_from_file,
)


def load_config(path: str) -> dict:
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def parse_design(raw):
    if isinstance(raw, dict):
        return raw
    return json.loads(raw)


def find_widget(node, *, name=None, wtype=None):
    if isinstance(node, dict):
        if node.get('type') and (name is None or node.get('name') == name) \
                and (wtype is None or node.get('type') == wtype) \
                and ('model' in node or 'key' in node):
            return node
        for v in node.values():
            r = find_widget(v, name=name, wtype=wtype)
            if r:
                return r
    elif isinstance(node, list):
        for i in node:
            r = find_widget(i, name=name, wtype=wtype)
            if r:
                return r
    return None


def find_sub_table(design, sub_name):
    found = find_widget(design, name=sub_name, wtype='sub-table-design')
    if found:
        return found
    if sub_name:
        return None
    return find_widget(design, wtype='sub-table-design')


def already_converted(design, sub_name):
    w = find_widget(design, name=sub_name, wtype='link-record')
    if w and w.get('isSubTable'):
        return w
    return None


def _replace_node(node, pred, new_w):
    if isinstance(node, list):
        for i, item in enumerate(node):
            if isinstance(item, dict) and pred(item):
                node[i] = new_w
                return True
            if _replace_node(item, pred, new_w):
                return True
    elif isinstance(node, dict):
        for v in node.values():
            if _replace_node(v, pred, new_w):
                return True
    return False


def patch_parent_to_link_record(parent_code, sub_name, body, column_fields):
    """后端 subToWorksheet 只建新表+迁数据，主表设计仍是 sub-table-design。
    前端才会把控件换成 link-record + isSubTable。脚本必须补这一步。"""
    parent = query_form(parent_code)
    design = parse_design(parent['desformDesignJson'])
    if already_converted(design, sub_name):
        return
    show_fields = []
    title = ''
    for w in column_fields:
        if w.get('type') in ('link-record', 'divider', 'text', 'buttons'):
            continue
        m = w.get('model')
        if m:
            show_fields.append(m)
            if not title:
                title = m
    widget, _k, _m = LINK_RECORD(
        sub_name, body['originSubCode'], title,
        show_fields=show_fields,
        show_mode='many',
        show_type='table',
        wrap=False,
    )
    old_key = body['parentModel'][len('link_record_'):]
    widget['isSubTable'] = True
    widget['model'] = body['parentModel']
    widget['key'] = old_key
    widget['options']['twoWayModel'] = body['subModel']
    widget['options']['sourceCode'] = body['originSubCode']
    widget['advancedSetting']['defaultValue']['customConfig'] = True
    ok = _replace_node(
        design,
        lambda it: it.get('type') == 'sub-table-design' and it.get('name') == sub_name,
        widget,
    )
    if not ok:
        raise RuntimeError(f'主表未替换设计子表: {sub_name}')
    hw = list((design.get('config') or {}).get('hasWidgets') or [])
    hw = [x for x in hw if x != 'sub-table-design']
    if 'link-record' not in hw:
        hw.append('link-record')
    design.setdefault('config', {})['hasWidgets'] = hw
    path = os.path.join(os.path.join(__import__('tempfile').gettempdir(), 'jeecg-desform'),
                        f'{parent_code}_after_convert.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(design, f, ensure_ascii=False, indent=2)
    save_design_from_file(parent_code, path)
    save_auth_from_design(parent_code)


def clone_columns(sub) -> list:
    out = []
    for col in sub.get('columns') or []:
        for w in col.get('list') or []:
            nw = copy.deepcopy(w)
            nw['isSubItem'] = False
            nw.pop('subOptions', None)
            out.append(nw)
    return out


def build_new_config(parent_cfg: dict, fields: list) -> dict:
    title = None
    types = []
    for w in fields:
        t = w.get('type')
        if t and t not in types:
            types.append(t)
        if title is None and t not in (None, 'link-record', 'divider', 'text', 'buttons'):
            title = w.get('model')
    cfg = copy.deepcopy(parent_cfg) if parent_cfg else {}
    cfg['formStyle'] = cfg.get('formStyle') or 'normal'
    cfg['titleField'] = title or (fields[0].get('model') if fields else '')
    cfg['hasWidgets'] = types
    cfg['designMobileView'] = False
    cfg['disabledAutoGrid'] = False
    return cfg


def build_body(parent_form: dict, sub: dict) -> dict:
    parent_code = parent_form['desformCode']
    parent_name = parent_form.get('desformName') or parent_code
    parent_design = parse_design(parent_form['desformDesignJson'])
    parent_title = (parent_design.get('config') or {}).get('titleField') or ''
    origin = sub['model']
    parent_model = f"link_record_{sub['key']}"

    fields = clone_columns(sub)
    rev, _k, sub_model = LINK_RECORD(
        parent_name, parent_code, parent_title,
        show_mode='single', show_type='card', is_self=True, wrap=False,
    )
    rev['options']['twoWayModel'] = parent_model
    rev['advancedSetting']['defaultValue']['customConfig'] = True
    rev['advancedSetting']['defaultValue']['valueSplit'] = ''
    fields.append(rev)

    new_design = {
        'list': fields,
        'config': build_new_config(parent_design.get('config') or {}, fields),
    }
    return {
        'subModel': sub_model,
        'parentCode': parent_code,
        'parentModel': parent_model,
        'originSubCode': origin,
        'designForm': {
            'desformName': sub.get('name') or '未命名',
            'desformCode': origin,
            'desformDesignJson': json.dumps(new_design, ensure_ascii=False, separators=(',', ':')),
        },
    }


def ok_already(parent_code, sub_name, extra=None):
    result = {'parentCode': parent_code, 'name': sub_name}
    if extra:
        result.update(extra)
    print(json.dumps({
        'success': True, 'action': 'subToWorksheet',
        'message': '已经是工作表子表',
        'result': result,
    }, ensure_ascii=False, indent=2))


def main() -> None:
    p = argparse.ArgumentParser(description='设计子表转为独立工作表')
    p.add_argument('--api-base', required=True)
    p.add_argument('--token', required=True)
    p.add_argument('--tenant-id', required=True)
    p.add_argument('--app-id', default=None)
    p.add_argument('--parent-code', default=None, help='主表 desformCode')
    p.add_argument('--sub-name', default=None, help='子表显示名，如 订单明细表')
    p.add_argument('--config', default=None, help='UTF-8 JSON：parentCode / subName / appId')
    args = p.parse_args()

    cfg = load_config(args.config) if args.config else {}
    parent_code = args.parent_code or cfg.get('parentCode') or cfg.get('parent-code')
    sub_name = args.sub_name or cfg.get('subName') or cfg.get('sub-name')
    app_id = args.app_id or cfg.get('appId') or cfg.get('app-id')
    if not parent_code or not sub_name:
        print(json.dumps({'success': False, 'message': '需要 parentCode 和 subName'}, ensure_ascii=False))
        sys.exit(1)

    init_lowapp(args.api_base, args.token, tenant_id=args.tenant_id, app_id=app_id)
    parent = query_form(parent_code)
    if not parent:
        print(json.dumps({'success': False, 'message': f'主表不存在: {parent_code}'}, ensure_ascii=False))
        sys.exit(1)
    design = parse_design(parent['desformDesignJson'])

    already = already_converted(design, sub_name)
    if already:
        ok_already(parent_code, sub_name, {
            'originSubCode': (already.get('options') or {}).get('sourceCode'),
        })
        return

    sub = find_sub_table(design, sub_name)
    if not sub:
        print(json.dumps({'success': False, 'message': f'未找到子表: {sub_name}'}, ensure_ascii=False))
        sys.exit(1)

    body = build_body(parent, sub)
    exist_id, _ = get_form_id(body['originSubCode'])
    if exist_id:
        # 半成品：新表编码=原子表 model，已占码但主表仍是 sub-table-design
        delete_form(body['originSubCode'], exist_id)

    r = api_request('/desform/subToWorksheet', data=body, method='POST')
    if not r.get('success') and '已存在' in str(r.get('message') or ''):
        parent2 = query_form(parent_code)
        design2 = parse_design(parent2['desformDesignJson']) if parent2 else {}
        already = already_converted(design2, sub_name)
        if already:
            ok_already(parent_code, sub_name, {
                'originSubCode': (already.get('options') or {}).get('sourceCode'),
            })
            return

    if r.get('success'):
        patch_parent_to_link_record(parent_code, sub_name, body, clone_columns(sub))

    out = {
        'success': bool(r.get('success')),
        'action': 'subToWorksheet',
        'message': r.get('message'),
        'result': {
            'parentCode': body['parentCode'],
            'parentModel': body['parentModel'],
            'subModel': body['subModel'],
            'originSubCode': body['originSubCode'],
            'desformName': body['designForm']['desformName'],
        },
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if not r.get('success'):
        sys.exit(1)


if __name__ == '__main__':
    main()
