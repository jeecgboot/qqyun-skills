#!/usr/bin/env python3
"""列表视图：视图专有 action——看板 / 日历 / 甘特 三类设置集中于此。

对齐前端源码（均为某视图类型专有）：
- 看板 add_board / config_board：multi/config/Kanbanshezhi.vue
- 日历 add_calendar / config_calendar：multi/config/Rilishezhi.vue
- 甘特 add_gantt / update_gantt：views/gantt/components/GanttViewConfig.vue
  （含 GanttViewFieldSelect / GanttShowFieldConfig）

由 desform_list_view.py 内部调用，不要单独当 CLI。
"""
import os
import sys

_SELF = os.path.dirname(os.path.abspath(__file__))
for _p in (_SELF, os.path.dirname(_SELF)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from desform_utils import (
    add_list_view_board, add_list_view_calendar, add_list_view_gantt,
    config_calendar_columns, get_form_fields, query_list_views,
    query_list_view_by_id, update_list_view,
)
from desform_list_view import (
    dump, pick, resolve_code, resolve_views, maybe_model, maybe_key,
    _BOARD_GROUP_TYPES, _TITLE_FIELD_TYPES, _BOARD_COVER_TYPES,
    _CALENDAR_DATE_TYPES, _SKIP_LAYOUT_TYPES,
)


def run(action: str, cfg: dict, app_id: str) -> None:

    if action == 'add_board':
        code = resolve_code(cfg, app_id)
        group = pick(cfg, 'groupField', 'group_field')
        title = pick(cfg, 'titleField', 'title_field')
        view_id = add_list_view_board(
            code,
            group_field=maybe_model(code, group) if group else None,
            title_field=maybe_key(code, title) if title else None,
            name=pick(cfg, 'name', 'viewName'),
        )
        dump(True, action, result={'viewId': view_id, 'code': code})
        return

    if action == 'config_board':
        code = resolve_code(cfg, app_id) if pick(cfg, 'code', 'desformCode', 'worksheet', 'worksheetName', 'menuName') else None
        if not code:
            if not pick(cfg, 'viewId'):
                raise ValueError('config_board 必须提供 code/worksheet 或 viewId')
            code = query_list_view_by_id(str(cfg['viewId'])).get('desform_code')
            if not code:
                raise ValueError('config_board 无法从 viewId 解析 code，请传 worksheet/code')
        views = query_list_views(code)
        if pick(cfg, 'viewId', 'viewName', 'name'):
            hit, _ = resolve_views(cfg, code)
        else:
            hit = [v for v in views if v.get('type') == 'card']
        if not hit:
            raise ValueError('未找到看板视图（type=card），请传 viewId 或 viewName')
        group_field = pick(cfg, 'groupField', 'group_field')
        filter_type = pick(cfg, 'filterGroupType', 'filter_group_type')
        condition = pick(cfg, 'filterGroupCondition', 'filter_group_condition')
        title_field = pick(cfg, 'titleField', 'title_field')
        show_label = pick(cfg, 'showLabel', 'show_label')
        cover_field = pick(cfg, 'coverField', 'cover_field')
        cover_view = pick(cfg, 'coverView', 'cover_view')
        card_all_show = pick(cfg, 'cardShowAll', 'card_show_all')
        card_all_hide = pick(cfg, 'cardHideAll', 'card_hide_all')
        card_only_names = pick(cfg, 'cardFieldNames', 'card_field_names')
        card_hide_names = pick(cfg, 'cardHideFieldNames', 'card_hide_field_names')
        if filter_type is not None and filter_type not in ('all', 'part'):
            raise ValueError('filterGroupType 只有 all/part（看板不支持 exist）: %s' % filter_type)
        if isinstance(card_only_names, str):
            card_only_names = [card_only_names]
        if isinstance(card_hide_names, str):
            card_hide_names = [card_hide_names]
        _, fields_map = get_form_fields(code)

        def info_of(token):
            if token in fields_map:
                return fields_map[token]
            for f in fields_map.values():
                if token in (f.get('model'), f.get('key')):
                    return f
            return None

        def check_type(token, allowed, label):
            info = info_of(token)
            if not info:
                raise ValueError('未找到字段: %s' % token)
            if info.get('type') not in allowed:
                raise ValueError('字段「%s」类型 %s 不支持作为%s，仅限: %s' % (
                    token, info.get('type'), label, '/'.join(allowed)))
            return info

        def build_card_list(v):
            cur = query_list_view_by_id(v['id'])
            ordered = []
            seen = set()
            cur_list = sorted((dict(c) for c in (cur.get('cardColumnList') or [])),
                              key=lambda c: c.get('seq') if isinstance(c.get('seq'), int) else 99)
            for c in cur_list:
                f = c.get('field')
                if f and f not in seen:
                    ordered.append(f)
                    seen.add(f)
            for name, info in fields_map.items():
                key = info.get('key')
                if key and key not in seen and info.get('type') not in _SKIP_LAYOUT_TYPES and not info.get('parent'):
                    ordered.append(key)
                    seen.add(key)
            hide = set(card_hide_names or [])
            only = set()
            if card_all_show is True:
                pass
            elif card_only_names is not None:
                only = set()
                for n in card_only_names:
                    info = info_of(n)
                    if not info or not info.get('key'):
                        raise ValueError('未找到字段: %s' % n)
                    only.add(info['key'])
            want = {}
            for f in ordered:
                want[f] = True
            if card_all_hide is True:
                for f in want:
                    want[f] = False
            elif only:
                for f in want:
                    if f not in only:
                        want[f] = False
            elif hide:
                hk = set()
                for n in hide:
                    info = info_of(n)
                    if not info or not info.get('key'):
                        raise ValueError('未找到字段: %s' % n)
                    hk.add(info['key'])
                for f in want:
                    if f in hk:
                        want[f] = False
            return [{'field': f, 'show': want[f], 'seq': i} for i, f in enumerate(ordered)]

        updated = []
        for v in hit:
            if v.get('type') != 'card':
                raise ValueError('视图「%s」(id=%s) 不是看板视图' % (v.get('name'), v.get('id')))
            kwargs = {}
            if group_field is not None:
                check_type(group_field, _BOARD_GROUP_TYPES, '分组字段')
                kwargs['groupField'] = maybe_model(code, group_field, fields_map)
                if condition is None:
                    kwargs['filterGroupCondition'] = ''
            if filter_type is not None:
                kwargs['filterGroupType'] = filter_type
            if condition is not None:
                kwargs['filterGroupCondition'] = (','.join(str(c) for c in condition)
                                                  if isinstance(condition, (list, tuple)) else condition)
            if title_field is not None:
                if title_field != '':
                    check_type(title_field, _TITLE_FIELD_TYPES, '标题字段')
                kwargs['titleField'] = maybe_key(code, title_field) if title_field else ''
            if show_label is not None:
                kwargs['showLabel'] = bool(show_label)
            if cover_field is not None:
                if cover_field not in ('none', ''):
                    check_type(cover_field, _BOARD_COVER_TYPES, '封面字段')
                    kwargs['coverField'] = maybe_key(code, cover_field)
                else:
                    kwargs['coverField'] = '' if cover_field == '' else 'none'
            if cover_view is not None:
                kwargs['coverView'] = bool(cover_view)
            if any(x is not None for x in (card_all_show, card_all_hide, card_only_names, card_hide_names)):
                kwargs['cardColumnList'] = build_card_list(v)
            if not kwargs:
                raise ValueError('config_board 至少传一个要改的设置（groupField/filterGroupType/.../cardShowAll 等）')
            updated.append({'viewId': v['id'], 'name': v.get('name'), 'payload': kwargs,
                            'api': update_list_view(v['id'], **kwargs)})
        dump(True, action, result={'code': code, 'updated': updated})
        return


    if action == 'add_calendar':
        code = resolve_code(cfg, app_id)
        cols = pick(cfg, 'dateColumns', 'date_columns')
        if not cols:
            raise ValueError('add_calendar 必须提供 dateColumns')
        norm = []
        for col in cols:
            item = {
                'begin_field': maybe_model(code, pick(col, 'begin_field', 'beginField')),
                'tag': pick(col, 'tag'),
                'field_type': pick(col, 'field_type', 'fieldType', 'type') or 'date',
            }
            end = pick(col, 'end_field', 'endField')
            if end:
                item['end_field'] = maybe_model(code, end)
            norm.append(item)
        title = pick(cfg, 'titleField', 'title_field')
        view_id = add_list_view_calendar(
            code, norm,
            title_field=maybe_model(code, title) if title else None,
            name=pick(cfg, 'name', 'viewName'),
        )
        dump(True, action, result={'viewId': view_id, 'code': code})
        return

    if action == 'config_calendar':
        code = resolve_code(cfg, app_id) if pick(cfg, 'code', 'desformCode', 'worksheet', 'worksheetName', 'menuName') else None
        if not code:
            if not pick(cfg, 'viewId'):
                raise ValueError('config_calendar 必须提供 code/worksheet 或 viewId')
            code = query_list_view_by_id(str(cfg['viewId'])).get('desform_code')
            if not code:
                raise ValueError('config_calendar 无法从 viewId 解析 code，请传 worksheet/code')
        views = query_list_views(code)
        if pick(cfg, 'viewId', 'viewName', 'name'):
            hit, _ = resolve_views(cfg, code)
        else:
            hit = [v for v in views if v.get('type') == 'calendar']
        if not hit:
            raise ValueError('未找到日历视图（type=calendar），请传 viewId 或 viewName')
        cols = pick(cfg, 'dateColumns', 'date_columns', 'calendarColumnList', 'calendar_column_list')
        calendar_default = pick(cfg, 'calendarDefault', 'calendar_default')
        first_day = pick(cfg, 'firstDay', 'first_day')
        week_status = pick(cfg, 'weekStatus', 'week_status')
        week_day_list = pick(cfg, 'weekDayList', 'week_day_list')
        lunar_status = pick(cfg, 'lunarStatus', 'lunar_status')
        hour_status = pick(cfg, 'hourStatus', 'hour_status')
        title_field = pick(cfg, 'titleField', 'title_field')
        if calendar_default is not None and calendar_default not in ('dayGridMonth', 'timeGridWeek', 'timeGridDay'):
            raise ValueError('calendarDefault 只能 dayGridMonth/timeGridWeek/timeGridDay: %s' % calendar_default)
        if first_day is not None:
            first_day = str(first_day)
            if first_day not in ('0', '1', '2', '3', '4', '5', '6'):
                raise ValueError('firstDay 只能是 0-6（0=周日）: %s' % first_day)
        if week_day_list is not None:
            week_day_list = [str(d) for d in week_day_list]
            bad = [d for d in week_day_list if d not in ('0', '1', '2', '3', '4', '5', '6')]
            if bad:
                raise ValueError('weekDayList 只能是 0-6: %s' % bad)
        _, fields_map = get_form_fields(code)

        def c_info_of(token):
            if token in fields_map:
                return fields_map[token]
            for f in fields_map.values():
                if token in (f.get('model'), f.get('key')):
                    return f
            return None

        def c_check_type(token, allowed, label):
            info = c_info_of(token)
            if not info:
                raise ValueError('未找到字段: %s' % token)
            if info.get('type') not in allowed:
                raise ValueError('字段「%s」类型 %s 不支持作为%s，仅限: %s' % (
                    token, info.get('type'), label, '/'.join(allowed)))
            return info

        norm = None
        if cols is not None:
            norm = []
            for col in cols:
                item = {
                    'begin_field': maybe_model(code, pick(col, 'begin_field', 'beginField')),
                    'tag': pick(col, 'tag'),
                    'field_type': pick(col, 'field_type', 'fieldType', 'type') or 'date',
                }
                if not item['begin_field']:
                    raise ValueError('dateColumns 每项必须提供 begin_field: %s' % col)
                c_check_type(item['begin_field'], _CALENDAR_DATE_TYPES, '日历日期字段')
                end = pick(col, 'end_field', 'endField')
                if end:
                    item['end_field'] = maybe_model(code, end)
                    c_check_type(item['end_field'], _CALENDAR_DATE_TYPES, '日历结束日期字段')
                norm.append(item)
        updated = []
        for v in hit:
            if v.get('type') != 'calendar':
                raise ValueError('视图「%s」(id=%s) 不是日历视图' % (v.get('name'), v.get('id')))
            kwargs = {}
            if calendar_default is not None:
                kwargs['calendarDefault'] = calendar_default
            if first_day is not None:
                kwargs['firstDay'] = first_day
            if week_status is not None:
                kwargs['weekStatus'] = bool(week_status)
                if week_day_list is None:
                    # 对齐 UI：开启只显示工作日默认隐藏周六日，关闭则清空
                    kwargs['weekDayList'] = ['0', '6'] if week_status else []
            if week_day_list is not None:
                kwargs['weekDayList'] = week_day_list
            if lunar_status is not None:
                kwargs['lunarStatus'] = bool(lunar_status)
            if hour_status is not None:
                kwargs['hourStatus'] = bool(hour_status)
            if title_field is not None:
                if title_field != '':
                    c_check_type(title_field, _TITLE_FIELD_TYPES, '标题字段')
                # 日历 titleField 存 model（与看板存 key 不同，实测 2026-09）
                kwargs['titleField'] = maybe_model(code, title_field, fields_map) if title_field else ''
            if kwargs:
                update_list_view(v['id'], **kwargs)
            if norm is not None:
                config_calendar_columns(v['id'], norm)
            if not kwargs and norm is None:
                raise ValueError('config_calendar 至少传一个要改的设置（dateColumns/calendarDefault/firstDay/.../titleField）')
            updated.append({'viewId': v['id'], 'name': v.get('name'),
                            'payload': dict(kwargs, calendarColumnList=norm) if norm is not None else kwargs})
        dump(True, action, result={'code': code, 'updated': updated})
        return


    if action == 'add_gantt':
        code = resolve_code(cfg, app_id)
        start = pick(cfg, 'startField', 'start_field', 'beginDateField')
        end = pick(cfg, 'endField', 'end_field', 'endDateField')
        if not start or not end:
            raise ValueError('add_gantt 必须提供 startField 和 endField')
        title = pick(cfg, 'titleField', 'title_field')
        view_id = add_list_view_gantt(
            code,
            start_field=maybe_model(code, start),
            end_field=maybe_model(code, end),
            field_type=pick(cfg, 'fieldType', 'field_type') or 'date',
            default_view=pick(cfg, 'defaultView', 'default_view') or 'day',
            title_field=maybe_model(code, title) if title else None,
            name=pick(cfg, 'name', 'viewName'),
        )
        dump(True, action, result={'viewId': view_id, 'code': code})
        return

    if action == 'update_gantt':
        code = resolve_code(cfg, app_id) if pick(cfg, 'code', 'desformCode', 'worksheet', 'worksheetName', 'menuName') else None
        if pick(cfg, 'viewId'):
            view_id = str(cfg['viewId'])
        else:
            if not code:
                raise ValueError('update_gantt 必须提供 viewId 或 worksheet+viewName')
            views = query_list_views(code)
            hit = [v for v in views if v.get('type') == 'gantt'] if not pick(cfg, 'viewName', 'name') \
                else [v for v in resolve_views(cfg, code)[0]]
            if not hit:
                raise ValueError('未找到甘特图视图（type=gantt），请传 viewId 或 viewName')
            view_id = hit[0]['id']
        start_raw = pick(cfg, 'startField', 'start_field', 'beginDateField', 'begin_date_field')
        end_raw = pick(cfg, 'endField', 'end_field', 'endDateField', 'end_date_field')
        has_start = 'startField' in cfg or 'start_field' in cfg or 'beginDateField' in cfg or 'begin_date_field' in cfg
        has_end = 'endField' in cfg or 'end_field' in cfg or 'endDateField' in cfg or 'end_date_field' in cfg
        view = query_list_view_by_id(view_id)
        if not code:
            code = view.get('desform_code') or None
        cur_gf = dict(view.get('ganttFields') or {})
        if has_start or has_end:
            if not code:
                raise ValueError('改日期字段需要提供 code/worksheet（解析字段类型）')
            _, fields_map = get_form_fields(code)

            def gf_field_type(model):
                info = next((f for f in fields_map.values() if model in (f.get('model'), f.get('key'))), None)
                if not info:
                    raise ValueError('未找到字段: %s' % model)
                if info.get('type') not in ('date', 'datetime'):
                    raise ValueError('甘特图日期字段仅支持 date/datetime（year/month 不支持），「%s」类型为 %s' % (
                        info.get('model'), info.get('type')))
                return info

            begin = maybe_model(code, start_raw, fields_map) if has_start else (cur_gf.get('beginDateField') or '')
            end = maybe_model(code, end_raw, fields_map) if has_end else (cur_gf.get('endDateField') or '')
            if not start_raw:
                begin = ''
            if not end_raw:
                end = ''
            types = {}
            if begin:
                types['beginDateField'] = gf_field_type(begin).get('type')
            if end:
                types['endDateField'] = gf_field_type(end).get('type')
            if begin and end and types['beginDateField'] != types['endDateField']:
                raise ValueError('开始/结束日期字段类型须一致（date 或 datetime），当前: %s/%s' % (
                    types['beginDateField'], types['endDateField']))
            cur_gf['beginDateField'] = begin
            cur_gf['endDateField'] = end
            cur_gf['dateType'] = next(iter(types.values()), '') if types else ''
        if 'showUnscheduled' in cfg or 'show_unscheduled' in cfg:
            cur_gf['showUnscheduled'] = bool(pick(cfg, 'showUnscheduled', 'show_unscheduled'))
        if 'defaultView' in cfg or 'default_view' in cfg:
            dv = pick(cfg, 'defaultView', 'default_view')
            if dv not in ('day', 'week', 'month', 'quarter', 'year'):
                raise ValueError('defaultView 只能 day/week/month/quarter/year: %s' % dv)
            cur_gf['defaultView'] = dv
        if 'colorFields' in cfg or 'color_fields' in cfg:
            cur_gf['colorFields'] = pick(cfg, 'colorFields', 'color_fields')
        extra = {}
        if 'autoRefresh' in cfg or 'auto_refresh' in cfg:
            ar = pick(cfg, 'autoRefresh', 'auto_refresh')
            try:
                ar = int(ar)
            except (TypeError, ValueError):
                raise ValueError('autoRefresh 必须是整数秒: %s' % ar)
            if ar not in (0, 30, 60, 120, 180, 240, 300):
                raise ValueError('autoRefresh 只能 0/30/60/120/180/240/300: %s' % ar)
            extra['autoRefresh'] = ar
        # 甘特显示字段（GanttShowFieldConfig）：{key, field: model, show, seq}，新字段默认隐藏
        g_all = pick(cfg, 'ganttShowAll', 'gantt_show_all')
        g_hide = pick(cfg, 'ganttHideAll', 'gantt_hide_all')
        g_only = pick(cfg, 'ganttFieldNames', 'gantt_field_names')
        g_hide_names = pick(cfg, 'ganttHideFieldNames', 'gantt_hide_field_names')
        if isinstance(g_only, str):
            g_only = [g_only]
        if isinstance(g_hide_names, str):
            g_hide_names = [g_hide_names]
        if any(x is not None for x in (g_all, g_hide, g_only, g_hide_names)):
            if not code:
                raise ValueError('改显示字段需要提供 code/worksheet')
            _, fields_map = get_form_fields(code)
            cur_list = sorted((dict(c) for c in (view.get('showColumnList') or [])),
                              key=lambda c: c.get('seq') if isinstance(c.get('seq'), int) else 99)
            ordered = []
            seen = set()
            for c in cur_list:
                f = c.get('field')
                if f and f not in seen:
                    ordered.append(f)
                    seen.add(f)
            for info in fields_map.values():
                m = info.get('model')
                if m and m not in seen and info.get('type') not in _SKIP_LAYOUT_TYPES and not info.get('parent'):
                    ordered.append(m)
                    seen.add(m)

            def g_info_of(token):
                if token in fields_map:
                    return fields_map[token]
                for f in fields_map.values():
                    if token in (f.get('model'), f.get('key')):
                        return f
                raise ValueError('未找到字段: %s' % token)

            want = {f: True for f in ordered}
            if g_hide is True:
                for f in want:
                    want[f] = False
            elif g_only is not None:
                keys = {g_info_of(n)['model'] for n in g_only}
                for f in want:
                    if f not in keys:
                        want[f] = False
            elif g_hide_names is not None:
                keys = {g_info_of(n)['model'] for n in g_hide_names}
                for f in want:
                    if f in keys:
                        want[f] = False
            if g_all is True:
                for f in want:
                    want[f] = True
            extra['showColumnList'] = [{
                'key': next((i.get('key') for i in fields_map.values() if i.get('model') == f), ''),
                'field': f, 'show': want[f], 'seq': i,
            } for i, f in enumerate(ordered)]
        elif pick(cfg, 'showColumnList', 'show_column_list') is not None:
            extra['showColumnList'] = pick(cfg, 'showColumnList', 'show_column_list')
        r = update_list_view(view_id, ganttFields=cur_gf, **extra)
        dump(True, action, result={'viewId': view_id, 'ganttFields': cur_gf, 'extra': extra, 'api': r})
        return


    raise ValueError('视图模块未知 action: ' + action)
