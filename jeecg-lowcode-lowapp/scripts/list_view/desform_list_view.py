#!/usr/bin/env python3
"""JeecgBoot 列表视图通用脚本。

查 / 改 / 建表格、看板、日历、甘特图。禁止为这些操作现写临时 .py。

视图专有配置（对齐前端 multi/config/*.vue，action 与视图类型对应，见各分支注释）：
- 仅表格视图：config_table（列/统计/行高）、config_quick_filter（快速筛选 Kuaisushaixuan）、
  config_left_filter（筛选列表 Shaixuanliebiao）
- 看板：add_board、config_board（看板设置 Kanbanshezhi）
- 日历：add_calendar、config_calendar（日历设置 Rilishezhi）
- 甘特：add_gantt、update_gantt（甘特设置）
- 通用（任意视图类型）：config_sort（默认排序）、config_data_filter（数据过滤）、config_system_columns

用法:
  python desform_list_view.py --api-base <URL> --token <TOKEN> --tenant-id <TID> --app-id <APP> --json '{"action":"config_table","code":"xx","viewId":"yy","hasSummary":false}'
  python desform_list_view.py --api-base <URL> --token <TOKEN> --tenant-name <租户> --config <utf8.json>
"""
from __future__ import annotations

import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdin.reconfigure(encoding='utf-8')
except Exception:
    pass

import os
import sys

_SELF = os.path.dirname(os.path.abspath(__file__))
for _p in (_SELF, os.path.dirname(_SELF)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from desform_lowapp_utils import init_lowapp, get_apps, get_menus
from desform_utils import (
    add_list_view_table,
    config_table_base,
    config_table_left_filter,
    config_table_quick_filter,
    config_table_sort,
    config_table_system_columns,
    config_view_data_filter,
    delete_list_view,
    get_form_fields,
    query_list_view_by_id,
    query_list_views,
    reset_list_view_order,
    sort_list_view,
    update_list_view,
)
from lowapp_creator import load_config, resolve_tenant_id

_TABLE_TYPES = ('base', 'table')
from desform_list_view_columns import (
    apply_column_name_filter,
    apply_column_type_filter,
    build_diy_column_visibility,
    normalize_widget_types,
    patch_column_show_by_names,
    patch_column_show_by_types,
)
from desform_list_view_filter import resolve_filter_conditions
from desform_list_view_quickfilter import _SYS_QUICK_FILTER, build_query_list
from desform_list_view_quickfilter import build_query_list

_SKIP_KEYS = {
    'action', 'appName', 'appId', 'code', 'desformCode', 'worksheet',
    'worksheetName', 'menuName', 'viewId', 'viewName', 'name', 'id',
    'tenantName', 'fromName',
}


def dump(ok: bool, action: str, result=None, message: str | None = None) -> None:
    out = {'success': ok, 'action': action}
    if result is not None:
        out['result'] = result
    if message:
        out['message'] = message
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    if not ok:
        sys.exit(1)


def pick(cfg: dict, *keys, default=None):
    for k in keys:
        if k in cfg and cfg[k] is not None and cfg[k] != '':
            return cfg[k]
    return default


def resolve_app_id(cfg: dict, tenant_id, cli_app_id=None, cli_app_name=None) -> str:
    if cli_app_id:
        return str(cli_app_id)
    if pick(cfg, 'appId'):
        return str(cfg['appId'])
    name = cli_app_name or pick(cfg, 'appName')
    if not name:
        raise ValueError('必须提供 --app-id 或 appName')
    matched = [a for a in (get_apps(tenant_id=tenant_id).get('apps') or [])
               if a.get('appName') == name]
    if len(matched) == 1:
        return str(matched[0]['id'])
    if not matched:
        raise ValueError(f'未找到应用: {name}')
    raise ValueError(f'找到多个同名应用，请传 appId: {name}')


def resolve_code(cfg: dict, app_id: str) -> str:
    code = pick(cfg, 'code', 'desformCode')
    if code:
        return str(code)
    name = pick(cfg, 'worksheet', 'worksheetName', 'menuName')
    if not name:
        raise ValueError('JSON 必须提供 code 或 worksheet')
    menus = (get_menus(app_id=app_id).get('menuList') or [])
    matched = [m for m in menus if m.get('type') == 'form' and m.get('menuName') == name]
    if len(matched) == 1:
        return str(matched[0].get('desformCode'))
    if not matched:
        names = [m.get('menuName') for m in menus if m.get('type') == 'form']
        raise ValueError(f'未找到工作表: {name}；当前: {names}')
    raise ValueError(f'找到多个同名工作表，请传 code: {name}')


def resolve_views(cfg: dict, code: str, *, table_only=False, require=True):
    view_id = pick(cfg, 'viewId')
    views = query_list_views(code)
    if view_id:
        hit = [v for v in views if str(v.get('id')) == str(view_id)]
        if not hit:
            raise ValueError(f'未找到视图 id={view_id}')
        return hit, views
    view_name = pick(cfg, 'viewName', 'name')
    pool = [v for v in views if v.get('type') in _TABLE_TYPES] if table_only else views
    if view_name:
        hit = [v for v in pool if v.get('name') == view_name]
        if len(hit) == 1:
            return hit, views
        if not hit:
            raise ValueError(f'未找到视图: {view_name}')
        raise ValueError(f'找到多个同名视图，请传 viewId: {view_name}')
    if table_only:
        hit = [v for v in views if v.get('type') in _TABLE_TYPES]
        if hit:
            return hit, views
    if require:
        raise ValueError('必须提供 viewId 或 viewName')
    return [], views


_SYS_FIELD_NAMES = {
    '创建人': 'create_by',
    '更新人': 'update_by', '修改人': 'update_by',
    '创建时间': 'create_time',
    '更新时间': 'update_time', '修改时间': 'update_time',
    '流程状态': 'bpm_status', '所属部门': 'sys_org_code',
}

# 左侧筛选（筛选列表）可选字段类型白名单，与前端 Shaixuanliebiao.vue compTypes 一致
_LEFT_FILTER_TYPES = ('link-record', 'table-dict', 'radio', 'checkbox', 'select', 'select-tree',
                      'select-user', 'select-depart', 'select-depart-post', 'org-role')
# 左侧筛选可用系统字段（对齐前端 useFieldSelect：systemFields 的类型命中 compTypes 才追加）。
# 创建/修改时间(datetime) 不在 compTypes 故不可用；model -> 类型
_SYS_LEFT_FILTER = {v[0]: v[1] for v in _SYS_QUICK_FILTER.values()}
_SYS_LEFT_LABEL = '创建人/修改人/所属部门/流程状态'
# 看板设置白名单（前端 Kanbanshezhi.vue）：分组字段 / 标题字段 / 封面字段
_BOARD_GROUP_TYPES = ('radio', 'select', 'select-user', 'table-dict', 'link-record', 'switch')
# 标题字段白名单：看板/日历共用（Kanbanshezhi.vue 与 Rilishezhi.vue titleFieldTypes 一致）
_TITLE_FIELD_TYPES = ('input', 'textarea', 'money', 'integer', 'number', 'phone', 'email',
                      'link-record', 'select-user')
_BOARD_COVER_TYPES = ('imgupload',)
# 日历日期字段白名单（Rilishezhi.vue CalendarFieldSelect，date 及其 dateType 变体）
_CALENDAR_DATE_TYPES = ('date', 'year', 'month', 'quarter', 'week', 'datetime',
                        'datetime_s', 'datetime_sf', 'x_oa_timeout_date')
_SKIP_LAYOUT_TYPES = ('button', 'buttons', 'grid', 'card', 'tabs', 'text', 'divider', 'barcode')


def maybe_model(code: str, value, fields_map=None):
    if value in (None, ''):
        return value
    sys_fields = {'create_by', 'update_by', 'bpm_status', 'create_time', 'update_time', 'sys_org_code'}
    if value in sys_fields:
        return value
    if fields_map is None:
        _, fields_map = get_form_fields(code)
    if value in fields_map:
        return fields_map[value]['model']
    for info in fields_map.values():
        if value in (info.get('model'), info.get('key')):
            return info.get('model')
    if value in _SYS_FIELD_NAMES:
        return _SYS_FIELD_NAMES[value]
    return value


def maybe_key(code: str, value):
    if value in (None, ''):
        return value
    _, fields = get_form_fields(code)
    if value in fields:
        return fields[value]['key']
    for info in fields.values():
        if value in (info.get('model'), info.get('key')):
            return info.get('key')
    return value


def run(action: str, cfg: dict, app_id: str) -> None:
    if action in ('add_board', 'config_board', 'add_calendar', 'config_calendar',
                  'add_gantt', 'update_gantt'):
        import desform_list_view_special as _m
        return _m.run(action, cfg, app_id)

    if action == 'list':
        code = resolve_code(cfg, app_id)
        views = query_list_views(code)
        dump(True, action, result={'code': code, 'views': views, 'count': len(views)})
        return

    if action == 'get':
        code = resolve_code(cfg, app_id) if pick(cfg, 'code', 'desformCode', 'worksheet', 'worksheetName', 'menuName') else None
        if pick(cfg, 'viewId'):
            view = query_list_view_by_id(str(cfg['viewId']))
        else:
            if not code:
                raise ValueError('get 必须提供 viewId，或 code/worksheet + viewName')
            hit, _ = resolve_views(cfg, code)
            view = query_list_view_by_id(hit[0]['id'])
        dump(True, action, result=view)
        return

    if action == 'delete':
        code = resolve_code(cfg, app_id)
        hit, _ = resolve_views(cfg, code)
        results = [delete_list_view(v['id']) for v in hit]
        dump(True, action, result={'deleted': [v['id'] for v in hit], 'api': results})
        return

    if action == 'sort':
        view_id = pick(cfg, 'viewId')
        after = pick(cfg, 'after')
        if not view_id or after is None:
            raise ValueError('sort 必须提供 viewId 和 after')
        dump(True, action, result=sort_list_view(str(view_id), after))
        return

    if action == 'reset_order':
        ids = pick(cfg, 'viewIds', 'ids')
        if not ids:
            raise ValueError('reset_order 必须提供 viewIds')
        dump(True, action, result=reset_list_view_order(ids))
        return

    if action == 'add_table':
        code = resolve_code(cfg, app_id)
        view_id = add_list_view_table(code, name=pick(cfg, 'name', 'viewName'))
        dump(True, action, result={'viewId': view_id, 'code': code})
        return

    if action in ('config_table', 'set_summary'):
        code = resolve_code(cfg, app_id)
        hit, _ = resolve_views(cfg, code, table_only=True)
        kwargs = {}
        mapping = {
            'lineHeight': 'line_height', 'line_height': 'line_height',
            'autoRefresh': 'auto_refresh', 'auto_refresh': 'auto_refresh',
            'hasSummary': 'has_summary', 'has_summary': 'has_summary',
            'autoSubmitBpm': 'auto_submit_bpm', 'auto_submit_bpm': 'auto_submit_bpm',
            'showColumn': 'show_column', 'show_column': 'show_column',
            'fixedColumnNum': 'fixed_column_num', 'fixed_column_num': 'fixed_column_num',
            'columnList': 'column_list', 'column_list': 'column_list',
            'showColumnList': 'show_column_list', 'show_column_list': 'show_column_list',
        }
        for src, dst in mapping.items():
            if src in cfg and cfg[src] is not None:
                kwargs[dst] = cfg[src]
        if action == 'set_summary' and 'has_summary' not in kwargs:
            enabled = pick(cfg, 'enabled', 'hasSummary', 'has_summary')
            if enabled is None:
                raise ValueError('set_summary 必须提供 hasSummary 或 enabled')
            kwargs['has_summary'] = bool(enabled)
        if 'showAll' in cfg or 'show_all' in cfg:
            col_visible = bool(pick(cfg, 'showAll', 'show_all'))
        elif pick(cfg, 'hideAll', 'hide_all') is True:
            col_visible = False
        else:
            col_visible = None
        show_types = pick(cfg, 'showTypes', 'show_types')
        type_set = normalize_widget_types(show_types) if show_types is not None else None
        field_names = pick(cfg, 'fieldNames', 'fields')
        if isinstance(field_names, str):
            field_names = [field_names]
        hide_names = pick(cfg, 'hideFieldNames', 'hideFields')
        if isinstance(hide_names, str):
            hide_names = [hide_names]
        hide_types_raw = pick(cfg, 'hideTypes', 'hide_types')
        hide_type_set = normalize_widget_types(hide_types_raw) if hide_types_raw is not None else None
        if (not kwargs and col_visible is None and type_set is None
                and field_names is None and hide_names is None and hide_type_set is None):
            raise ValueError(
                'config_table 必须提供要改的字段（如 hasSummary / showAll / fieldNames / hideFieldNames）')
        updated = []
        for v in hit:
            call_kw = dict(kwargs)
            shown = None
            if hide_names is not None:
                cols, scl, shown = patch_column_show_by_names(
                    code, v['id'], hide_names, False)
                call_kw['show_column'] = call_kw.get('show_column') or 'diy'
                call_kw['column_list'] = cols
                call_kw['show_column_list'] = scl
            elif hide_type_set is not None:
                cols, scl, shown = patch_column_show_by_types(
                    code, v['id'], hide_type_set, False)
                call_kw['show_column'] = call_kw.get('show_column') or 'diy'
                call_kw['column_list'] = cols
                call_kw['show_column_list'] = scl
            elif field_names is not None:
                cols, scl, shown = apply_column_name_filter(code, v['id'], field_names)
                call_kw['show_column'] = call_kw.get('show_column') or 'diy'
                call_kw['column_list'] = cols
                call_kw['show_column_list'] = scl
            elif type_set is not None:
                cols, scl, shown = apply_column_type_filter(code, v['id'], type_set)
                call_kw['show_column'] = call_kw.get('show_column') or 'diy'
                call_kw['column_list'] = cols
                call_kw['show_column_list'] = scl
            elif col_visible is not None:
                cols, scl = build_diy_column_visibility(code, v['id'], col_visible)
                call_kw['show_column'] = call_kw.get('show_column') or 'diy'
                call_kw['column_list'] = cols
                call_kw['show_column_list'] = scl
            r = config_table_base(v['id'], **call_kw)
            item = {
                'viewId': v['id'], 'name': v.get('name'), 'type': v.get('type'),
                'columnCount': len(call_kw.get('column_list') or []),
                'api': r,
            }
            if shown is not None:
                item['shown'] = shown
            updated.append(item)
        dump(True, action, result={'code': code, 'updated': updated})
        return

    if action == 'config_system_columns':
        code = resolve_code(cfg, app_id)
        hit, _ = resolve_views(cfg, code, table_only=True)
        fields = pick(cfg, 'showFields', 'show_fields')
        if fields is None:
            raise ValueError('config_system_columns 必须提供 showFields')
        updated = [config_table_system_columns(v['id'], fields) for v in hit]
        dump(True, action, result={'updated': updated})
        return

    if action == 'config_sort':
        code = resolve_code(cfg, app_id)
        named = pick(cfg, 'viewId', 'viewName', 'name')
        hit, _ = resolve_views(cfg, code, table_only=not named)
        orders = pick(cfg, 'orders')
        if orders is None:
            raise ValueError('config_sort 必须提供 orders（可 []）')
        norm = []
        if orders:
            _, fields_map = get_form_fields(code)
            for o in orders:
                item = dict(o)
                f = item.get('field')
                if f is not None:
                    item['field'] = maybe_model(code, f, fields_map)
                if item.get('type') not in ('asc', 'desc'):
                    raise ValueError('orders 每项的 type 只能为 asc/desc: %s' % o)
                norm.append(item)
        updated = [config_table_sort(v['id'], norm) for v in hit]
        dump(True, action, result={'updated': updated, 'orders': norm})
        return

    if action == 'config_quick_filter':
        code = resolve_code(cfg, app_id)
        hit, _ = resolve_views(cfg, code, table_only=True)
        qlist = pick(cfg, 'queryList', 'query_list')
        names = pick(cfg, 'fieldNames', 'fields')
        if qlist is not None and names is not None:
            raise ValueError('queryList 与 fieldNames 只能二选一')
        if qlist is None and names is None:
            raise ValueError('config_quick_filter 必须提供 queryList 或 fieldNames')
        if isinstance(names, str):
            names = [names]
        if qlist is None:
            qlist = build_query_list(code, names)
        updated = [
            config_table_quick_filter(
                v['id'], qlist,
                query_button=bool(pick(cfg, 'queryButton', 'query_button', default=True)),
                wait_query=bool(pick(cfg, 'waitQuery', 'wait_query', default=False)),
            ) for v in hit
        ]
        dump(True, action, result={'updated': updated, 'queryList': qlist})
        return

    if action == 'config_left_filter':
        code = resolve_code(cfg, app_id)
        hit, _ = resolve_views(cfg, code, table_only=True)
        clear = pick(cfg, 'clear') is True
        raw_field = pick(cfg, 'leftFilterField', 'left_filter_field', 'field')
        data = pick(cfg, 'leftFilterData', 'left_filter_data')
        order = pick(cfg, 'leftFilterOrder', 'left_filter_order')
        cond = pick(cfg, 'leftFilterCondition', 'left_filter_condition')
        add_default = pick(cfg, 'addFormDefaultStatus', 'add_form_default_status', 'defaultStatus')
        if not clear:
            if data is not None and data not in ('all', 'exist', 'part'):
                raise ValueError('leftFilterData 只能是 all/exist/part: %s' % data)
            if order is not None and order not in ('asc', 'desc'):
                raise ValueError('leftFilterOrder 只能是 asc/desc: %s' % order)
        _, fields_map = get_form_fields(code)
        updated = []
        for v in hit:
            cur = query_list_view_by_id(v['id'])
            field = '' if clear else maybe_model(code, raw_field, fields_map) if raw_field is not None \
                else (cur.get('leftFilterField') or '')
            if field:
                info = next((i for n, i in fields_map.items()
                             if field in (n, i.get('model'), i.get('key'))), None)
                ftype = info.get('type') if info else _SYS_LEFT_FILTER.get(field)
                shown = next((n for n, i in fields_map.items() if i is info), field)
                if not info and field not in _SYS_LEFT_FILTER:
                    raise ValueError('未找到左侧筛选字段: %s（业务字段或系统字段 %s）' % (field, _SYS_LEFT_LABEL))
                if ftype not in _LEFT_FILTER_TYPES:
                    raise ValueError('字段「%s」类型 %s 不支持左侧筛选，仅限: %s；可用系统字段: %s' % (
                        shown, ftype, '/'.join(_LEFT_FILTER_TYPES), _SYS_LEFT_LABEL))
            cond_val = '' if clear else (cond if cond is not None else (cur.get('leftFilterCondition') or ''))
            if isinstance(cond_val, (list, tuple)):
                cond_val = ','.join(str(c) for c in cond_val)
            updated.append(config_table_left_filter(
                v['id'],
                left_filter_field=field,
                left_filter_data='' if clear else (data if data is not None else (cur.get('leftFilterData') or 'all')),
                left_filter_order='' if clear else (order if order is not None else (cur.get('leftFilterOrder') or 'desc')),
                left_filter_condition=cond_val,
                add_form_default_status=True if clear else bool(
                    add_default if add_default is not None else cur.get('addFormDefaultStatus', False)),
            ))
        dump(True, action, result={'updated': updated, 'clear': clear})
        return

    if action == 'config_data_filter':
        code = resolve_code(cfg, app_id)
        hit, _ = resolve_views(cfg, code)
        cond = pick(cfg, 'conditions')
        if cond is None:
            raise ValueError('config_data_filter 必须提供 conditions（可 []）')
        match = pick(cfg, 'matchType', 'match_type') or 'and'
        resolved = resolve_filter_conditions(code, cond)
        updated = [config_view_data_filter(v['id'], resolved, match_type=match) for v in hit]
        dump(True, action, result={'updated': updated, 'conditions': resolved})
        return

    if action == 'update':
        code = resolve_code(cfg, app_id) if pick(cfg, 'code', 'desformCode', 'worksheet', 'worksheetName') else None
        if pick(cfg, 'viewId'):
            targets = [{'id': str(cfg['viewId'])}]
        else:
            if not code:
                raise ValueError('update 必须提供 viewId 或 worksheet+viewName')
            targets, _ = resolve_views(cfg, code)
        fields = {k: v for k, v in cfg.items() if k not in _SKIP_KEYS}
        if not fields:
            raise ValueError('update 必须提供要改的字段')
        updated = [update_list_view(v['id'], **fields) for v in targets]
        dump(True, action, result={'updated': updated})
        return

    raise ValueError(
        '不支持的 action: %s（list/get/delete/sort/reset_order/add_table/add_board/'
        'add_calendar/add_gantt/config_table/set_summary/config_system_columns/'
        'config_board/config_sort/config_quick_filter/config_left_filter/config_data_filter/'
        'config_calendar/update_gantt/update）' % action
    )


def main() -> None:
    parser = argparse.ArgumentParser(description='JeecgBoot 列表视图管理')
    parser.add_argument('--api-base', required=True)
    parser.add_argument('--token', required=True)
    parser.add_argument('--tenant-id', default=None)
    parser.add_argument('--tenant-name', default=None)
    parser.add_argument('--app-id', default=None)
    parser.add_argument('--app-name', default=None)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument('--json', help='业务 JSON 字符串（推荐，一条命令，不要写临时文件）')
    src.add_argument('--config', help='业务 JSON 路径，或 - 表示 stdin')
    args = parser.parse_args()

    cfg = load_config(args.config, args.json)
    action = (cfg.get('action') or '').strip()
    if not action:
        dump(False, '', message='JSON 必须包含 action')
        return

    tenant_name = args.tenant_name or cfg.get('tenantName')
    if not args.tenant_id and not tenant_name:
        dump(False, action, message='必须提供租户 ID 或租户名称')
        return

    try:
        tenant_id = args.tenant_id or resolve_tenant_id(
            None, tenant_name, args.api_base, args.token)
        init_lowapp(args.api_base, args.token, tenant_id=tenant_id)
        app_id = resolve_app_id(cfg, tenant_id, args.app_id, args.app_name)
        init_lowapp(args.api_base, args.token, tenant_id=tenant_id, app_id=app_id)
        run(action, cfg, app_id)
    except Exception as e:
        dump(False, action, message=str(e))


if __name__ == '__main__':
    main()
