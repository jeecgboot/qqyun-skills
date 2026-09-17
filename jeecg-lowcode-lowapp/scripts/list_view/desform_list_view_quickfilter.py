#!/usr/bin/env python3
"""列表视图：快速筛选 queryList 解析。由 desform_list_view.py 调用，不要单独当 CLI。

字段中文名 -> {field, type, queryType, seq}。type/queryType 默认值以 UI 实测
payload（/desform/view/updateViewConfig 的 queryList，2026-09-02）为准，并对照前端
Kuaisushaixuan.vue / ts/useFilterField.ts 的 getDefaultRule 补全。
"""
from __future__ import annotations

import os
import sys

import os
import sys

_SELF = os.path.dirname(os.path.abspath(__file__))
for _p in (_SELF, os.path.dirname(_SELF)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from desform_utils import get_form_fields

# 控件类型 -> (type, queryType)。
# 实测规律：文本类 like；单选/数值/日期/选择类 eq；展示/富文本/附件/子表类 empty。
# eq：radio/switch/time/date/datetime/datetime_s/datetime_sf/integer/number/money/checkbox/
#     select/select-depart/select-depart-post/select-user/org-role/table-dict/select-tree/
#     link-record/area-linkage/category-linkage/rate/slider/formula/summary/year/month/
#     quarter/week/x_oa_timeout_date
# empty：map/location/sub-table-design/color/hand-sign/editor/markdown/imgupload/file-upload
# 其余（input/textarea/phone/email/auto-number/text-compose 等）默认 like。
# formula 列 UI 保存时转 number（日期模式转 date/input）；date 控件配了 dateType 时列类型为
# year/month/quarter/week。dontShowTypes=['link-field','daterange','datetimerange',
# 'capital-money','ocr'] 为 UI 禁止加入快速筛选的类型。
_QUICK_FILTER_DEFAULTS = {
    'input': ('input', 'like'),
    'textarea': ('textarea', 'like'),
    'phone': ('phone', 'like'),
    'email': ('email', 'like'),
    'auto-number': ('auto-number', 'like'),
    'text-compose': ('text-compose', 'like'),
    'money': ('money', 'eq'),
    'number': ('number', 'eq'),
    'integer': ('integer', 'eq'),
    'radio': ('radio', 'eq'),
    'select': ('select', 'eq'),
    'checkbox': ('checkbox', 'eq'),
    'switch': ('switch', 'eq'),
    'rate': ('rate', 'eq'),
    'slider': ('slider', 'eq'),
    'date': ('date', 'eq'),
    'year': ('year', 'eq'),
    'month': ('month', 'eq'),
    'quarter': ('quarter', 'eq'),
    'week': ('week', 'eq'),
    'time': ('time', 'eq'),
    'datetime': ('datetime', 'eq'),
    'datetime_s': ('datetime_s', 'eq'),
    'datetime_sf': ('datetime_sf', 'eq'),
    'x_oa_timeout_date': ('x_oa_timeout_date', 'eq'),
    'table-dict': ('table-dict', 'eq'),
    'select-tree': ('select-tree', 'eq'),
    'category-linkage': ('category-linkage', 'eq'),
    'map': ('map', 'empty'),
    'location': ('location', 'empty'),
    'color': ('color', 'empty'),
    'editor': ('editor', 'empty'),
    'markdown': ('markdown', 'empty'),
    'file-upload': ('file-upload', 'empty'),
    'imgupload': ('imgupload', 'empty'),
    'hand-sign': ('hand-sign', 'empty'),
    'sub-table-design': ('sub-table-design', 'empty'),
    'select-user': ('select-user', 'eq'),
    'select-depart': ('select-depart', 'eq'),
    'select-depart-post': ('select-depart-post', 'eq'),
    'org-role': ('org-role', 'eq'),
    'area-linkage': ('area-linkage', 'eq'),
    'link-record': ('link-record', 'eq'),
    'summary': ('summary', 'eq'),
    'formula': ('number', 'eq'),
}

# 系统列快速筛选：中文名 -> (model, type, queryType)。
# type 与 type.definition.ts systemFields 定义一致（修改时间/修改人 = update_time/update_by）。
_SYS_QUICK_FILTER = {
    '创建人': ('create_by', 'select-user', 'eq'),
    '更新人': ('update_by', 'select-user', 'eq'),
    '修改人': ('update_by', 'select-user', 'eq'),
    '创建时间': ('create_time', 'datetime', 'eq'),
    '更新时间': ('update_time', 'datetime', 'eq'),
    '修改时间': ('update_time', 'datetime', 'eq'),
    '所属部门': ('sys_org_code', 'select-depart', 'eq'),
    '流程状态': ('bpm_status', 'select', 'eq'),
}

_SYS_FIELD_NAMES = {name: triple[0] for name, triple in _SYS_QUICK_FILTER.items()}


def build_query_list(code: str, names) -> list:
    """字段中文名列表 -> 快速筛选 queryList。

    字段名找不到或控件类型未收录时抛错（列出可用字段/提示显式 queryList），不静默透传。
    """
    _, fields_map = get_form_fields(code)
    qlist = []
    for i, n in enumerate(names):
        info = fields_map.get(n)
        if not info:
            for v in fields_map.values():
                if n in (v.get('model'), v.get('key')):
                    info = v
                    break
        if info:
            default = _QUICK_FILTER_DEFAULTS.get(info.get('type'))
            if default:
                qlist.append({'field': info['model'], 'type': default[0], 'queryType': default[1], 'seq': i})
                continue
        if n in _SYS_QUICK_FILTER:
            model, ftype, qt = _SYS_QUICK_FILTER[n]
            qlist.append({'field': model, 'type': ftype, 'queryType': qt, 'seq': i})
            continue
        if n in _SYS_FIELD_NAMES:
            raise ValueError('系统字段「%s」暂无内置快速筛选方式，请用 queryList 显式传 type/queryType' % n)
        raise ValueError('未找到字段: %s；现有: %s' % (n, '、'.join(fields_map)))
    return qlist
