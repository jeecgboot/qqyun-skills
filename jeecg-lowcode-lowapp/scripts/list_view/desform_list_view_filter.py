#!/usr/bin/env python3
"""列表视图：数据过滤。由 desform_list_view.py 调用，不要单独当 CLI。

控件类型可用 rule 写在本文件，对齐 references/desform-filter-rules.md。
"""
from __future__ import annotations

import os
import sys

_SELF = os.path.dirname(os.path.abspath(__file__))
for _p in (_SELF, os.path.dirname(_SELF)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import json
import re
from datetime import datetime, timedelta, timezone

from desform_utils import get_form_fields, query_form

_RULE_ALIAS = {
    '包含': 'like', '等于': 'eq', '不等于': 'ne', '不是': 'ne',
    '大于': 'gt', '大于等于': 'ge', '小于': 'lt', '小于等于': 'le',
    '在范围内': 'range', '是其中一个': 'in', '不是其中一个': 'not_in',
    '包含任意': 'like_with_and', '为空': 'empty', '不为空': 'not_empty',
}
# 对齐 references/desform-filter-rules.md：类型 → (可用 rule, 默认 rule)
_TEXT_TYPES = {'input', 'textarea', 'phone', 'email', 'auto-number'}
_NUM_DATE_TYPES = {
    'number', 'integer', 'money', 'rate', 'slider', 'formula', 'summary',
    'date', 'datetime', 'datetime_s', 'datetime_sf', 'time',
    'year', 'month', 'quarter', 'week', 'x_oa_timeout_date',
}
_RADIO_TYPES = {'radio', 'area-linkage'}
_CHOICE_TYPES = {'checkbox', 'select'}
_PICKER_TYPES = {
    'select-user', 'select-depart', 'select-depart-post',
    'table-dict', 'select-tree', 'org-role',
}
_EMPTY_ONLY_TYPES = {
    'sub-table-design', 'map', 'location', 'imgupload', 'file-upload',
    'hand-sign', 'color', 'editor', 'markdown',
}
_RULES_TEXT = (['like', 'eq', 'ne', 'like_with_and', 'right_like', 'left_like',
                'empty', 'not_empty'], 'like')
_RULES_NUM = (['eq', 'ne', 'gt', 'ge', 'lt', 'le', 'range', 'empty', 'not_empty'], 'eq')
_RULES_CHOICE = (['eq', 'ne', 'in', 'not_in', 'empty', 'not_empty'], 'eq')
_RULES_SWITCH = (['eq', 'ne', 'empty', 'not_empty'], 'eq')
_RULES_EMPTY = (['empty', 'not_empty'], 'empty')


def rules_for_widget_type(ftype: str):
    if ftype in _TEXT_TYPES or not ftype:
        return _RULES_TEXT
    if ftype in _NUM_DATE_TYPES:
        return _RULES_NUM
    if ftype in _RADIO_TYPES or ftype in _CHOICE_TYPES or ftype in _PICKER_TYPES:
        return _RULES_CHOICE
    if ftype == 'switch':
        return _RULES_SWITCH
    if ftype == 'link-record':
        return _RULES_CHOICE
    if ftype == 'category-linkage':
        return (['eq', 'ne', 'empty', 'not_empty'], 'eq')
    if ftype in _EMPTY_ONLY_TYPES:
        return _RULES_EMPTY
    return _RULES_TEXT


def normalize_filter_rule(ftype: str, rule, val):
    allowed, default = rules_for_widget_type(ftype)
    if not rule:
        if isinstance(val, list) and len(val) > 1:
            if 'in' in allowed:
                return 'in'
            if 'like_with_and' in allowed:
                return 'like_with_and'
        if isinstance(val, str) and ',' in val and 'range' in allowed:
            return 'range'
        return default
    if rule not in allowed:
        if rule == 'in' and 'like_with_and' in allowed:
            return 'like_with_and'
        if rule == 'like' and ftype in _RADIO_TYPES | _CHOICE_TYPES and 'eq' in allowed:
            return 'eq'
        if rule == 'range' and ftype in _TEXT_TYPES:
            raise ValueError('文本字段不支持 range，请用 like / like_with_and')
        raise ValueError(
            '字段类型 %s 不支持 rule=%s，可用: %s' % (ftype, rule, ','.join(allowed)))
    return rule


_CST = timezone(timedelta(hours=8))


def collect_filter_meta(code: str):
    """一次取字段 + 设计 JSON，供数据过滤把中文名/选项文案收成 model 和落库值。"""
    _, fields = get_form_fields(code)
    form = query_form(code)
    design = json.loads(form.get('desformDesignJson') or '{}')
    by_name, by_model, by_key = {}, {}, {}

    def walk(node):
        if isinstance(node, dict):
            if node.get('type') and (node.get('model') or node.get('key')):
                opt = node.get('options') or {}
                raw_opts = opt.get('options') or opt.get('columns') or []
                label_map = {}
                for o in raw_opts:
                    if not isinstance(o, dict):
                        continue
                    val = o.get('value')
                    lab = o.get('label') if o.get('label') not in (None, '') else o.get('value')
                    if val is not None:
                        label_map[str(lab)] = val
                        label_map[str(val)] = val
                meta = {
                    'model': node.get('model'),
                    'key': node.get('key'),
                    'type': node.get('type'),
                    'name': node.get('name'),
                    'timestamp': bool(opt.get('timestamp')),
                    'activeValue': opt.get('activeValue'),
                    'inactiveValue': opt.get('inactiveValue'),
                    'label_map': label_map,
                }
                if meta['model']:
                    by_model[meta['model']] = meta
                if meta['key']:
                    by_key[str(meta['key'])] = meta
                if meta['name']:
                    by_name[meta['name']] = meta
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for i in node:
                walk(i)

    walk(design)
    for name, info in fields.items():
        if name in by_name:
            continue
        by_name[name] = {
            'model': info.get('model'), 'key': info.get('key'),
            'type': info.get('type'), 'name': name,
            'timestamp': False, 'activeValue': None, 'inactiveValue': None,
            'label_map': {},
        }
    return by_name, by_model, by_key


def lookup_filter_meta(token, by_name, by_model, by_key):
    if token in (None, ''):
        return None
    s = str(token)
    return by_name.get(s) or by_model.get(s) or by_key.get(s)


def month_range_timestamps(year: int, month: int):
    start = datetime(year, month, 1, tzinfo=_CST)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=_CST)
    else:
        end = datetime(year, month + 1, 1, tzinfo=_CST)
    end = end - timedelta(milliseconds=1)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def coerce_date_val(val, meta: dict):
    if val in (None, ''):
        return val, None
    s = str(val).strip()
    m = re.match(r'^(\d{4})[-年/](\d{1,2})月?$', s)
    if m:
        ts1, ts2 = month_range_timestamps(int(m.group(1)), int(m.group(2)))
        y, mo = int(m.group(1)), int(m.group(2))
        if meta.get('timestamp'):
            return '%s,%s' % (ts1, ts2), True
        last = 31
        for d in (31, 30, 29, 28):
            try:
                datetime(y, mo, d)
                last = d
                break
            except ValueError:
                continue
        return '%s-%02d-01,%s-%02d-%02d' % (y, mo, y, mo, last), None
    if meta.get('timestamp') and re.match(r'^\d{4}-\d{2}-\d{2}', s):
        parts = [p.strip() for p in s.split(',') if p.strip()]
        out = []
        for i, p in enumerate(parts):
            dt = datetime.strptime(p[:10], '%Y-%m-%d').replace(tzinfo=_CST)
            if i == len(parts) - 1 and len(parts) > 1:
                dt = dt.replace(hour=23, minute=59, second=59, microsecond=999000)
            out.append(str(int(dt.timestamp() * 1000)))
        return ','.join(out), True
    return val, (True if meta.get('timestamp') else None)


def coerce_option_val(val, meta: dict, orig_text_holder: list):
    if val in (None, ''):
        return val
    label_map = meta.get('label_map') or {}
    t = meta.get('type')
    if t == 'switch':
        on_v = meta.get('activeValue')
        off_v = meta.get('inactiveValue')
        mapping = {
            '开': on_v, '关': off_v, '是': on_v, '否': off_v,
            'true': on_v, 'false': off_v, 'Y': on_v, 'N': off_v,
            '1': on_v, '0': off_v,
        }
        if isinstance(val, str) and val in mapping and mapping[val] is not None:
            orig_text_holder.append(val)
            return mapping[val]
        return val
    if t in ('radio', 'select', 'checkbox', 'table-dict', 'select-tree'):
        if isinstance(val, list):
            mapped, texts = [], []
            for x in val:
                sx = str(x)
                if sx in label_map:
                    mapped.append(label_map[sx])
                    texts.append(sx)
                else:
                    mapped.append(x)
                    texts.append(sx)
            orig_text_holder.append(','.join(texts))
            return mapped
        sx = str(val)
        if sx in label_map:
            orig_text_holder.append(sx)
            return label_map[sx]
    return val


def resolve_one_filter_item(item: dict, by_name, by_model, by_key) -> dict:
    out = dict(item)
    token = out.get('name') or out.get('field')
    meta = lookup_filter_meta(token, by_name, by_model, by_key)
    if not meta and out.get('field'):
        meta = lookup_filter_meta(out.get('field'), by_name, by_model, by_key)
    if not meta:
        raise ValueError('数据过滤未找到字段: %s' % token)
    out['field'] = meta['model'] or meta['key']
    out['type'] = meta['type']
    out['name'] = meta.get('name') or out.get('name') or token
    rule = out.get('rule')
    if isinstance(rule, str) and rule in _RULE_ALIAS:
        rule = _RULE_ALIAS[rule]
    out['rule'] = normalize_filter_rule(meta.get('type'), rule, out.get('val'))
    texts = []
    if 'val' in out:
        out['val'] = coerce_option_val(out['val'], meta, texts)
        if out.get('rule') == 'range' or meta.get('type') in (
                'date', 'datetime', 'datetime_s', 'datetime_sf', 'month', 'year'):
            new_val, ts = coerce_date_val(out['val'], meta)
            out['val'] = new_val
            if ts:
                out['timestamp'] = True
    if 'valText' not in out:
        out['valText'] = texts[0] if texts else ''
    return out


def resolve_filter_conditions(code: str, conditions):
    if not conditions:
        return conditions
    by_name, by_model, by_key = collect_filter_meta(code)

    def resolve_node(node):
        if not isinstance(node, dict):
            return node
        kids = node.get('items')
        kid_key = 'items'
        if kids is None:
            kids = node.get('queryItems')
            kid_key = 'queryItems'
        if kids is not None:
            n = dict(node)
            n[kid_key] = [resolve_node(x) for x in kids]
            return n
        return resolve_one_filter_item(node, by_name, by_model, by_key)

    return [resolve_node(c) for c in conditions]

