# -*- coding: utf-8 -*-
"""
汇总/筛选条件规则可用性映射（QueryRuleMap 复刻）。

依据前端源码（2026-09-03 实测对照）：

用途：写 summary / 业务规则 / 条件组里的 rule 码之前，先按字段（type + options）
查本模块允许的规则码。rule 码 = QueryRuleMap 的键，UI 下拉选项顺序 = RULE_ORDER。

注意：
- 不存在 "LIKE"；文本“以 xx 开头” = BEFORE，值不带 %；
- 日期区间 = DATE_GE / DATE_LE（早于/晚于带等于）；
- 无值规则（EMPTY/NOT_EMPTY/VALUE_CHANGE）value 传 []；
- rule 匹配在设置筛选面板（SettingFilterDialog）场景，isSuperQuery=False。
"""

# 源码 numberFieldTypes
NUMBER_TYPES = ('number', 'integer', 'money', 'slider', 'rate', 'summary')
# 源码 chooseFieldTypes
CHOOSE_TYPES = ('checkbox', 'radio', 'select')
# 源码 filterUpload（保存的是图片/文件数据，不做文本比较）
UPLOAD_TYPES = ('imgupload', 'file-upload', 'hand-sign')
# 源码 ctypes.oa.signHolidaySelect
OA_SIGN_HOLIDAY_SELECT = 'oa-sign-holiday-select'
# 源码 filterString 排除名单（除数字/选择/上传外的非文本类）
STRING_EXCLUDE = (
    'date', 'select-user', 'select-depart', 'select-depart-post', 'org-role',
    'area-linkage', 'formula', 'switch', 'link-record', OA_SIGN_HOLIDAY_SELECT,
)
# 源码 DATE_LT.filter：date 控件允许日期比较的 options.type 粒度
DATE_GRANULARITIES = ('date', 'datetime', 'year', 'month', 'quarter', 'week')

RULE_ORDER = (
    'EQ', 'NE', 'GT', 'GE', 'LT', 'LE', 'IN', 'NOT_IN', 'IS_ONE_OF',
    'NOT_IS_ONE_OF', 'IN_ONE_OF', 'NOT_IN_ONE_OF', 'IN_ALL_OF',
    'DATE_LT', 'DATE_LE', 'DATE_GT', 'DATE_GE',
    'BEFORE', 'NOT_BEFORE', 'AFTER', 'NOT_AFTER',
    'EMPTY', 'NOT_EMPTY', 'VALUE_CHANGE',
)

RULE_LABELS = {
    'EQ': '等于', 'NE': '不等于', 'GT': '大于', 'GE': '大于等于',
    'LT': '小于', 'LE': '小于等于', 'IN': '包含', 'NOT_IN': '不包含',
    'IS_ONE_OF': '是其中一个', 'NOT_IS_ONE_OF': '不是其中一个',
    'IN_ONE_OF': '包含其中一个', 'NOT_IN_ONE_OF': '不包含任何一个',
    'IN_ALL_OF': '同时包含', 'DATE_LT': '早于', 'DATE_LE': '早于等于',
    'DATE_GT': '晚于', 'DATE_GE': '晚于等于', 'BEFORE': '开头是',
    'NOT_BEFORE': '开头不是', 'AFTER': '结尾是', 'NOT_AFTER': '结尾不是',
    'EMPTY': '为空', 'NOT_EMPTY': '不为空', 'VALUE_CHANGE': '值发生变化',
}


def available_rules(wtype, options=None, is_sub_table=False):
    """按字段 type + options 返回该字段可用的 rule 码（保序）。

    options 需含 rule 判定要用的键：type（date 粒度）、multiple、showMode、
    isSubTable（link-record 顶层）等，缺失按 False/缺省处理。
    """
    options = options or {}
    wt = (wtype or '').replace('__summary__', '')  # 汇总日期注册前缀剔除
    is_sub = wt == 'sub-table-design' or (wt == 'link-record' and (is_sub_table or options.get('isSubTable')))
    upload = wt in UPLOAD_TYPES
    numeric = wt in NUMBER_TYPES or (wt == 'formula' and options.get('type') == 'number')
    choose = wt in CHOOSE_TYPES or wt == OA_SIGN_HOLIDAY_SELECT
    is_string = (
        not numeric and not choose and wt not in STRING_EXCLUDE
        and not is_sub and not upload
    )
    multiple = bool(options.get('multiple'))
    show_mode = options.get('showMode', 'single')

    out = []
    for code in RULE_ORDER:
        if code in ('EQ', 'NE'):
            ok = not is_sub and not upload
        elif code in ('GT', 'GE', 'LT', 'LE'):
            ok = numeric
        elif code in ('IN', 'NOT_IN'):
            ok = is_string
        elif code in ('IS_ONE_OF', 'NOT_IS_ONE_OF'):
            # 源码：radio 与请假类型恒可用；checkbox/select 走 IN_ONE_OF 族，不给 IS_ONE_OF
            ok = wt in ('radio', OA_SIGN_HOLIDAY_SELECT) \
                or (wt in ('select-user', 'select-depart', 'select-depart-post', 'org-role') and not multiple) \
                or (wt in ('select-tree', 'table-dict') and not multiple) \
                or (wt == 'link-record' and not is_sub and show_mode == 'single')
        elif code in ('IN_ONE_OF', 'NOT_IN_ONE_OF'):
            ok = (wt in ('checkbox', 'select')) \
                or (wt in ('select-user', 'select-depart', 'select-depart-post', 'org-role') and multiple) \
                or (wt in ('select-tree', 'table-dict') and multiple) \
                or (wt == 'link-record' and not is_sub and show_mode == 'many')
        elif code == 'IN_ALL_OF':
            ok = (wt in ('checkbox', 'select')) \
                or (wt in ('select-user', 'select-depart', 'select-depart-post', 'org-role') and multiple) \
                or (wt in ('select-tree', 'table-dict') and multiple) \
                or (wt == 'link-record' and not is_sub and show_mode == 'many')
        elif code in ('DATE_LT', 'DATE_LE', 'DATE_GT', 'DATE_GE'):
            if wt == 'formula':
                ok = options.get('type') == 'date'
            else:
                ok = wt == 'date' and options.get('type') in DATE_GRANULARITIES
        elif code in ('BEFORE', 'NOT_BEFORE', 'AFTER', 'NOT_AFTER'):
            ok = is_string
        elif code in ('EMPTY', 'NOT_EMPTY'):
            ok = wt != 'switch'
        else:  # VALUE_CHANGE
            ok = True
        if ok:
            out.append(code)
    return out


def normalize_rule(rules, wtype, options=None, is_sub_table=False):
    """把传入的 rule 码过滤到该字段允许集合内（不合法返回提示）。"""
    allowed = set(available_rules(wtype, options, is_sub_table))
    bad = [r for r in rules if r not in allowed]
    if bad:
        return [], '规则不适用于该字段: %s（可用: %s）' % (
            ', '.join(map(str, bad)),
            ', '.join('%s(%s)' % (r, RULE_LABELS[r]) for r in allowed),
        )
    return rules, None


if __name__ == '__main__':
    import sys, json
    args = sys.argv[1:]
    if args and args[0] in ('--demo', 'demo'):
        cases = [
            ('input', {}),
            ('money', {}),
            ('date', {'type': 'date'}),
            ('date', {'type': 'month'}),
            ('select-user', {'multiple': True}),
            ('switch', {}),
            ('textarea', {}),
        ]
        for t, o in cases:
            print('%-14s %-30s -> %s' % (t, json.dumps(o, ensure_ascii=False), available_rules(t, o)))
    else:
        t = args[0] if args else 'input'
        o = json.loads(args[1]) if len(args) > 1 else {}
        print('\n'.join('%s(%s)' % (r, RULE_LABELS[r]) for r in available_rules(t, o)))
