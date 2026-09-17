#!/usr/bin/env python3
"""列表视图：自定义显示列。由 desform_list_view.py 调用，不要单独当 CLI。"""
from __future__ import annotations

import os
import sys

_SELF = os.path.dirname(os.path.abspath(__file__))
for _p in (_SELF, os.path.dirname(_SELF)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from desform_utils import get_form_fields, query_list_view_by_id

_SKIP_COL_TYPES = {
    'button', 'buttons', 'grid', 'card', 'tabs', 'text', 'divider', 'barcode',
}
# 自定义列「全部显示」写死的系统字段，顺序与前端 systemFieldDataList 一致
# （前端 columnUtils.ts：seq 100-105，修改时间/修改人 = update_time/update_by）
_DIY_SHOW_ALL_SYSTEM_FIELDS = (
    'create_time',    # 创建时间
    'create_by',      # 创建人
    'update_time',    # 修改时间
    'update_by',      # 修改人
    'sys_org_code',   # 所属部门
    'bpm_status',     # 流程状态
)
# 大字段类型（前端 columnUtils.ts largeFieldTypes，QQYUN-8909）：
# showColumn=default 时强制排除、不可显示；diy 时默认排除但 column_list 显式 show=True 可显示。
_LARGE_FIELD_TYPES = {'textarea', 'markdown', 'editor'}
_SYS_FIELD_ALIAS = {
    '创建时间': 'create_time', '创建人': 'create_by',
    '修改时间': 'update_time', '更新时间': 'update_time',
    '修改人': 'update_by', '更新人': 'update_by',
    '所属部门': 'sys_org_code', '流程状态': 'bpm_status',
}
_TYPE_ALIASES = {
    '单选框组': 'radio', '单选': 'radio', 'radio': 'radio',
    '多选框组': 'checkbox', '多选': 'checkbox', 'checkbox': 'checkbox',
    '金额': 'money', 'money': 'money',
    '整数': 'integer', 'integer': 'integer',
}

def build_diy_column_visibility(code: str, view_id: str, visible: bool):
    """自定义列全部显示/隐藏。列表必须保留：业务字段 + 6 个写死系统字段。清空 [] 不是隐藏全部。

    语义（对齐前端 columnUtils.ts，2026-09）：diy 模式下 columnList 是全量快照，
    未列入 columnList 的新增字段默认隐藏（与后台一致）；故此处总是全量重建。
    """
    view = query_list_view_by_id(view_id)
    cols = [dict(c) for c in (view.get('columnList') or [])]
    _, fields = get_form_fields(code)
    biz = []
    for info in fields.values():
        if info.get('type') in _SKIP_COL_TYPES or info.get('parent'):
            continue
        key = info.get('key')
        if key:
            biz.append(key)
    if cols:
        for i, c in enumerate(cols):
            c['show'] = visible
            if c.get('seq') is None:
                c['seq'] = i
        existing = {c.get('field') for c in cols}
        seq = max((c.get('seq') or 0) for c in cols) + 1
        for key in biz:
            if key not in existing:
                cols.append({'field': key, 'show': visible, 'seq': seq})
                seq += 1
    else:
        cols = [{'field': key, 'show': visible, 'seq': i} for i, key in enumerate(biz)]
    existing = {c.get('field') for c in cols}
    seq = (max((c.get('seq') or 0) for c in cols) + 1) if cols else 0
    for key in _DIY_SHOW_ALL_SYSTEM_FIELDS:
        if key in existing:
            for c in cols:
                if c.get('field') == key:
                    c['show'] = visible
        else:
            cols.append({'field': key, 'show': visible, 'seq': seq})
            seq += 1
    scl = [dict(c) for c in (view.get('showColumnList') or [])]
    sys_set = set(_DIY_SHOW_ALL_SYSTEM_FIELDS)
    if scl:
        for c in scl:
            c['show'] = visible
        have = {c.get('field') for c in scl}
        for key in biz:
            if key not in have:
                scl.append({'field': key, 'show': visible})
    else:
        scl = [{'field': c['field'], 'show': visible} for c in cols
               if c.get('field') not in sys_set]
    return cols, scl


def normalize_widget_types(raw) -> set:
    out = set()
    for item in raw or []:
        key = str(item).strip()
        if not key:
            continue
        out.add(_TYPE_ALIASES.get(key, key))
    return out


def resolve_field_names(code, names):
    """字段中文名 → key。没说组件时走这里，禁止当控件 type。"""
    _, fields = get_form_fields(code)
    key_index = {info.get('key'): name for name, info in fields.items() if info.get('key')}
    want_keys = set()
    resolved = []
    missing = []
    for raw in names or []:
        name = str(raw).strip()
        if not name:
            continue
        if name in fields:
            info = fields[name]
            want_keys.add(info['key'])
            resolved.append({'name': name, 'field': info['key'], 'type': info.get('type')})
        elif name in _SYS_FIELD_ALIAS:
            want_keys.add(_SYS_FIELD_ALIAS[name])
            resolved.append({'name': name, 'field': _SYS_FIELD_ALIAS[name], 'type': 'system'})
        elif name in _DIY_SHOW_ALL_SYSTEM_FIELDS:
            want_keys.add(name)
            resolved.append({'name': name, 'field': name, 'type': 'system'})
        elif name in key_index:
            want_keys.add(name)
            resolved.append({'name': key_index[name], 'field': name,
                             'type': fields[key_index[name]].get('type')})
        else:
            missing.append(name)
    if missing:
        raise ValueError('未找到字段: %s；当前字段: %s' % (missing, list(fields.keys())))
    return want_keys, resolved


def load_column_list(code, view_id):
    """保留已有 show；没有 columnList 才按全部字段建一份。"""
    view = query_list_view_by_id(view_id)
    cols = [dict(c) for c in (view.get('columnList') or [])]
    if not cols:
        cols, _ = build_diy_column_visibility(code, view_id, True)
    return cols, view


def write_show_column_list(cols):
    sys_set = set(_DIY_SHOW_ALL_SYSTEM_FIELDS)
    return [{'field': c['field'], 'show': c['show']} for c in cols
            if c.get('field') not in sys_set]


def apply_column_name_filter(code: str, view_id: str, names):
    """只显示指定字段中文名；其余 show=false，列表保留。"""
    cols, _scl = build_diy_column_visibility(code, view_id, True)
    want_keys, shown = resolve_field_names(code, names)
    for c in cols:
        c['show'] = c.get('field') in want_keys
    return cols, write_show_column_list(cols), shown


def patch_column_show_by_names(code: str, view_id: str, names, visible: bool):
    """按字段名改显隐，其它列不动。

    ⚠️ diy 模式语义（前端同）：columnList 是全量快照，未列出的字段（含以后新增）
    默认隐藏。本函数 load_column_list 会先补全全量快照，保证「其它列不动」只是
    show 不变，不是可省略不写。
    """
    cols, _view = load_column_list(code, view_id)
    want_keys, resolved = resolve_field_names(code, names)
    by_field = {c.get('field'): c for c in cols}
    seq = (max((c.get('seq') or 0) for c in cols) + 1) if cols else 0
    for key in want_keys:
        if key in by_field:
            by_field[key]['show'] = visible
        else:
            cols.append({'field': key, 'show': visible, 'seq': seq})
            seq += 1
    return cols, write_show_column_list(cols), resolved


def patch_column_show_by_types(code: str, view_id: str, types: set, visible: bool):
    """仅用户明确说组件/控件类型时使用。其它列不动。"""
    cols, _view = load_column_list(code, view_id)
    _, fields = get_form_fields(code)
    key_to_type = {}
    match_keys = set()
    resolved = []
    for name, info in fields.items():
        t = info.get('type')
        if info.get('key'):
            key_to_type[info['key']] = t
        if t in types and info.get('key'):
            match_keys.add(info['key'])
            resolved.append({'name': name, 'field': info['key'], 'type': t})
    by_field = {c.get('field'): c for c in cols}
    seq = (max((c.get('seq') or 0) for c in cols) + 1) if cols else 0
    for key in match_keys:
        if key in by_field:
            by_field[key]['show'] = visible
        else:
            cols.append({'field': key, 'show': visible, 'seq': seq})
            seq += 1
    return cols, write_show_column_list(cols), resolved


def apply_column_type_filter(code: str, view_id: str, types: set):
    """只显示指定控件类型；其余业务字段和 6 个系统字段 show=false，列表保留。"""
    cols, scl = build_diy_column_visibility(code, view_id, True)
    _, fields = get_form_fields(code)
    key_to_type = {}
    for info in fields.values():
        t = info.get('type')
        if info.get('key'):
            key_to_type[info['key']] = t
        if info.get('model'):
            key_to_type[info['model']] = t
    shown = []
    for c in cols:
        t = key_to_type.get(c.get('field'))
        c['show'] = t in types
        if c['show']:
            shown.append({'field': c.get('field'), 'type': t})
    sys_set = set(_DIY_SHOW_ALL_SYSTEM_FIELDS)
    scl = [{'field': c['field'], 'show': c['show']} for c in cols
           if c.get('field') not in sys_set]
    return cols, scl, shown

