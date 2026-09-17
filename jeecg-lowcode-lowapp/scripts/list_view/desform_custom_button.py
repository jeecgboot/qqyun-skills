#!/usr/bin/env python3
"""自定义按钮 CLI（表格 / 看板 / 日历 / 甘特 四种视图同一套按钮体系）。

对齐前端 multi/BaseConfigDrawer.vue 等四个视图抽屉 + config/Zidingyianniu.vue +
ZdyanDrawer.vue：按钮挂在"设计器"层（/desform/button/*），视图只保存绑定关系
（视图 zdyan.buttonList = 按钮 id 列表）；全局按钮 allView=true 自动出现在所有视图。

四个视图是否一样？
- 按钮面板/规则/接口四个视图完全相同（同一组件同参数），脚本无需按视图类型分支；
- 唯一差别不在视图类型：SQL 自适应（isSQLAdapt）数据源下 UI 隐藏"自定义动作"与"排序"。
- 删除按钮时 UI 分两种：仅从当前视图移除(remove) vs 彻底删除(delete，连触发的工作流)。

由 desform_list_view.py 体系内部调用入口使用；本脚本可独立 CLI 运行。
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

_SELF = os.path.dirname(os.path.abspath(__file__))
for _p in (_SELF, os.path.dirname(_SELF)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from lowapp_creator import load_config, resolve_tenant_id
from desform_lowapp_utils import init_lowapp
from desform_utils import get_form_fields
from desform_button_utils import (
    add_button_to_view, check_button_label, create_button, delete_button,
    get_button, list_buttons, remove_button_from_view, reorder_buttons, update_button,
)
from desform_list_view import _SKIP_KEYS, dump, pick, resolve_app_id, resolve_code

# 规则常量（对齐 references/desform-custom-button.md）
BUTTON_DEFAULTS = {
    'showStatus': 'always',
    'clickThen': 'execute',
    'flowStatus': True,
    'color': 'rgb(33, 150, 243)',
}
COLOR_PRESETS = (
    'rgb(33, 150, 243)', 'rgb(156, 39, 176)', 'rgb(63, 81, 181)',
    'rgb(233, 30, 99)', 'rgb(255, 152, 0)', 'rgb(76, 175, 80)',
    'rgb(0, 188, 212)',
)
# 真实 update 场景是"整条记录回传、字段不一定全"（对齐 UI /desform/button/update）：
# 记录元数据键不作为变更字段（显式 null 可用来清字段）
_UPDATE_META = ('designFormCode', 'createBy', 'createTime', 'updateBy', 'updateTime',
                'seq', 'allView')
_CLICK_THEN = ('execute', 'confirm', 'form')
_SHOW_STATUS = ('always', 'condition')
# 条件 rule 合法全集（对齐 useFilterField switchRuleHandle + desform-filter-rules.md）
_COND_RULES = ('like', 'eq', 'right_like', 'left_like', 'ne', 'gt', 'ge', 'lt', 'le',
               'in', 'not_in', 'like_with_and', 'range', 'empty', 'not_empty', 'elemMatch')
# 每类组件可用条件（对齐前端 useFilterField.ts getConditionOptions，按钮条件编辑器同源）
_TEXT_RULES = ('like', 'eq', 'ne', 'like_with_and', 'right_like', 'left_like', 'empty', 'not_empty')
_NUM_DATE_RULES = ('eq', 'ne', 'gt', 'ge', 'lt', 'le', 'empty', 'not_empty', 'range')
_CHOICE_RULES = ('eq', 'ne', 'in', 'not_in', 'empty', 'not_empty')
_SWITCH_RULES = ('eq', 'ne', 'empty', 'not_empty')
_EMPTY_ONLY_TYPES = ('map', 'location', 'sub-table-design', 'color', 'hand-sign', 'editor',
                     'markdown', 'imgupload', 'file-upload')
_NUM_DATE_TYPES = ('time', 'year', 'month', 'quarter', 'week', 'date', 'datetime',
                   'datetime_s', 'datetime_sf', 'integer', 'number', 'money', 'rate',
                   'slider', 'formula', 'summary', 'x_oa_timeout_date')
_CHOICE_TYPES = ('radio', 'select', 'checkbox', 'area-linkage', 'select-depart',
                 'select-depart-post', 'select-user', 'table-dict', 'select-tree',
                 'org-role', 'link-record')


def _rule_set_for(ftype: str):
    if ftype in _NUM_DATE_TYPES:
        return _NUM_DATE_RULES
    if ftype in _CHOICE_TYPES:
        return _CHOICE_RULES
    if ftype == 'switch':
        return _SWITCH_RULES
    if ftype == 'category-linkage':
        return _SWITCH_RULES
    if ftype in _EMPTY_ONLY_TYPES:
        return ('empty', 'not_empty')
    return _TEXT_RULES  # 文本类及未知类型默认
CONFIRM_TEXT_DEFAULTS = {'tip': '你确认对记录执行此操作吗？', 'ok': '确认', 'cancel': '取消'}


def _to_model(code: str, token, fields_map):
    if token in fields_map:
        return fields_map[token]['model']
    for f in fields_map.values():
        if token in (f.get('model'), f.get('key')):
            return f.get('model')
    return token


def _normalise_condition_items(items, code, fields_map, where):
    if not isinstance(items, list):
        raise ValueError('%s 必须是数组' % where)
    out = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('%s 每项必须是对象' % where)
        it = dict(item)
        field = it.get('field')
        if field is not None:
            it['field'] = _to_model(code, field, fields_map)
        # 对齐 UI 实际保存 payload：条件项带控件 type、valText 空串
        info = next((f for f in fields_map.values() if f.get('model') == it.get('field')), None)
        if info:
            it.setdefault('type', info.get('type'))
        rule = it.get('rule')
        if rule is not None and rule not in _COND_RULES:
            raise ValueError('%s 的 rule 只能为 %s（不能用 = 等符号）: %s'
                             % (where, '/'.join(_COND_RULES), rule))
        # 按字段组件类型限制可用规则（对齐 useFilterField.getConditionOptions）：
        # 文本 like/eq/ne/…；数值/日期 eq/ne/gt/ge/lt/le/range；选项 eq/ne/in/not_in；
        # 开关 eq/ne；富文本/附件/子表等仅 empty/not_empty
        ftype = it.get('type')
        if rule is not None and ftype:
            allowed = _rule_set_for(ftype)
            if rule not in allowed:
                raise ValueError('%s 字段类型 %s 的 rule 只能是 %s（不能用 = 等符号）: %s'
                                 % (where, ftype, '/'.join(allowed), rule))
        it.setdefault('valText', '')
        out.append(it)
    return out


def _normalise_conditions(cfg: dict, code: str):
    """启用按钮=满足筛选条件时的条件结构：
    支持"单条条件" conditions 与"筛选组" conditionsGroup（对齐 UI ButtonConditions，
    可同时存在多个组、每组 matchType+queryItems；条件为空 UI 会退回 always，这里直接报错）。
    """
    flat = cfg.get('conditions')
    groups = pick(cfg, 'conditionsGroup', 'conditions_group')
    ctype = pick(cfg, 'conditionType', 'condition_type', default='and')
    if ctype not in ('and', 'or'):
        raise ValueError('conditionType（组间关系）只能 and/or: %s' % ctype)
    if not flat and not groups:
        raise ValueError('showStatus=condition 必须提供 conditions（单条条件）或 conditionsGroup（筛选组）')
    _, fields_map = get_form_fields(code)
    flat = _normalise_condition_items(flat, code, fields_map, 'conditions') if flat else None
    if groups is not None:
        if not isinstance(groups, list):
            raise ValueError('conditionsGroup 必须是数组')
        ng = []
        for g in groups:
            if not isinstance(g, dict):
                raise ValueError('conditionsGroup 每项必须是对象（筛选组）')
            gg = dict(g)
            if 'matchType' not in gg:
                gg['matchType'] = 'and'
            if gg['matchType'] not in ('and', 'or'):
                raise ValueError('组内 matchType 只能 and/or: %s' % gg['matchType'])
            if 'queryItems' not in gg:
                raise ValueError('筛选组必须含 queryItems 数组: %s' % g)
            gg['queryItems'] = _normalise_condition_items(gg['queryItems'], code, fields_map, 'queryItems')
            # 对齐 UI 实际保存 payload：组级 showPop 固定 false（UI 状态字段）
            gg.setdefault('showPop', False)
            ng.append(gg)
        groups = ng
    return flat, groups, ctype


_FORM_TABLE = ('current', 'link-record')
_FORM_TYPE = ('update', 'create')
_ATTR_VALUES = ('readonly', '', 'required')


_DESIGN_CACHE = {}


def _design_json(code: str):
    """表单（工作表）设计 JSON，进程内按 code 缓存"""
    if code not in _DESIGN_CACHE:
        from desform_utils import query_form
        _DESIGN_CACHE[code] = json.loads(query_form(code)['desformDesignJson'])
    return _DESIGN_CACHE[code]


def _find_link_in(design, key):
    """在设计 JSON 中按 key/model 定位 link-record 控件，返回 widget dict"""
    def walk(n):
        if isinstance(n, dict):
            if n.get('type') == 'link-record' and (n.get('key') == key or n.get('model') == key):
                return n
            for x in n.values():
                r = walk(x)
                if r:
                    return r
        elif isinstance(n, list):
            for x in n:
                r = walk(x)
                if r:
                    return r
        return None

    return walk(design)


def _link_record_widget(code: str, key):
    return _find_link_in(_design_json(code), key)


def _normalise_form_config(cfg: dict, code: str, *, strict: bool = False):
    """点击后=填写指定内容（form）的 buttonFormConfig 规则——逐条对齐 ButtonFormConfig.vue：

    1) 填写对象 formTable：
       - current（当前记录）
       - link-record（关联记录·单条）：先选"关联字段" linkRecordField——UI 第一个下拉
         selectOptions1 从**当前表**字段中过滤 type=link-record 且 multi=false
         （multi = options.showMode==='many'，multi=false 即单条）；linkRecordTable =
         该字段的 options.sourceCode（UI 下拉项 table=code=sourceCode）
    2) 填写内容 formType：
       - update（填写指定字段）：updateFieldList 非空。字段作用域：formTable=current 取
         当前表字段；formTable=link-record 取**关联目标表**（linkRecordTable）字段
         （UI FormFieldSelect 在 link-record 模式用 dynamicColumnList = linkRecordField
         指向表的设计字段）
       - create（新建关联记录）：必选"关联字段" createFormField——UI 第二个下拉
         selectOptions2 只过滤 type=link-record（单条/多条都行），作用域同上：
         formTable=current 取当前表关联记录字段、formTable=link-record 取关联目标表的
         关联记录字段；createFormCode = 该字段自身的 sourceCode（UI onChangeCreateFormField
         取下拉项 table=code=sourceCode），脚本可查目标表设计本地推断
    3) updateFieldList 每项（UI FormFieldSelect 选中字段即存
       {key, attr, defaultVal:'', type, field:model, model, name}）：
       - attr ∈ readonly（只读）/ ''（填写）/ required（必填），新增时 UI 按字段是否必填
         给 required/''；defaultVal 默认 ''，数组默认值以逗号拼串存储

    strict=True（create 新建按钮）：交叉依赖齐全性强制校验；
    strict=False（update 部分字段回传，对齐 /desform/button/update 场景）：只校验/规范化
    用户本次给出的字段，缺失的依赖（linkRecordField/linkRecordTable）交给后端保留原值，
    目标表不可读时字段 key/model 原样透传。
    """
    fc = cfg.get('buttonFormConfig')
    if fc is None:
        return None
    if not isinstance(fc, dict):
        raise ValueError('buttonFormConfig 必须是对象')
    fc = dict(fc)
    form_table = fc.get('formTable') or 'current'
    form_type = fc.get('formType') or 'update'
    if form_table not in _FORM_TABLE:
        raise ValueError('formTable 只能 current/link-record: %s' % form_table)
    if form_type not in _FORM_TYPE:
        raise ValueError('formType 只能 update/create: %s' % form_type)
    _, cur_fields = get_form_fields(code)
    fc['formTable'] = form_table
    fc['formType'] = form_type

    def match_any(fmap, token):
        if token in fmap:
            return fmap[token]['key']
        for f in fmap.values():
            if token in (f.get('model'), f.get('key')):
                return f.get('key')
        return None

    def find_info(fmap, key):
        return next((f for f in fmap.values() if f.get('key') == key), None)

    def check_link(fmap, design, where, token, *, single_only=False):
        """字段须在某表内且为 link-record 控件；linkRecordField 走 single_only（单条）"""
        key = match_any(fmap, token)
        if key is None:
            raise ValueError('%s 未找到字段: %s' % (where, token))
        info = find_info(fmap, key)
        if info.get('type') != 'link-record':
            raise ValueError('%s 必须是关联记录字段（link-record），「%s」类型为 %s'
                             % (where, token, info.get('type')))
        w = _find_link_in(design, key)
        if single_only and w and (w.get('options') or {}).get('showMode') == 'many':
            raise ValueError('%s 需为单条（单选）关联记录，「%s」是多选形态' % (where, token))
        return key, w

    def source_of(w, where):
        src = (w or {}).get('options') and (w['options'].get('sourceCode'))
        if not src:
            raise ValueError('无法推断 %s（关联记录控件未指向工作表），请显式提供' % where)
        return src

    # —— 填写对象：link-record 单条校验 + 目标表推断 ——
    lr_table = fc.get('linkRecordTable')
    if fc.get('linkRecordField'):
        lk, w = check_link(cur_fields, _design_json(code), 'linkRecordField',
                           fc['linkRecordField'], single_only=True)
        fc['linkRecordField'] = lk
        inferred = source_of(w, 'linkRecordTable（关联目标工作表）')
        if lr_table and lr_table != inferred:
            raise ValueError('linkRecordTable(%s) 与 linkRecordField 指向的表(%s) 不一致'
                             % (lr_table, inferred))
        fc['linkRecordTable'] = lr_table = inferred
    elif strict and form_table == 'link-record':
        raise ValueError('formTable=link-record 时必须提供 linkRecordField'
                         '（当前表内的单条关联记录字段）')

    # 字段作用域表上下文：link-record 模式由 linkRecordTable 决定
    tctx = None
    if form_table == 'link-record' and lr_table:
        try:
            _, tmap = get_form_fields(lr_table)
            tctx = (tmap, _design_json(lr_table))
        except Exception as e:
            if strict:
                raise ValueError('读取关联目标工作表失败（%s）: %s' % (lr_table, e))
            tctx = None  # 宽松模式目标表不可读：相关字段原样透传

    if form_type == 'create':
        cf = fc.get('createFormField')
        if strict and not cf:
            raise ValueError('formType=create 时必须提供 createFormField（新建哪条关联记录）')
        if cf:
            # createFormField 只要求是关联记录字段（单条/多条均可），作用域随 formTable
            if tctx:
                fmap, design = tctx
                ck, w = check_link(fmap, design, 'createFormField', cf)
            elif match_any(cur_fields, cf):
                ck, w = check_link(cur_fields, _design_json(code), 'createFormField', cf)
            elif strict:
                raise ValueError('无法校验 createFormField（目标表不可读且非当前表字段）: %s' % cf)
            else:
                ck, w = cf, None  # 宽松模式目标表未知：原样透传
            fc['createFormField'] = ck
            if w is not None and not fc.get('createFormCode'):
                fc['createFormCode'] = source_of(w, 'createFormCode（新建记录的表单编码）')
    elif form_type == 'update':
        ul = fc.get('updateFieldList')
        if strict and (not isinstance(ul, list) or not ul):
            raise ValueError('formType=update 时必须提供 updateFieldList（非空数组）')
        if not isinstance(ul, list) or not ul:
            return fc  # 宽松模式未携带列表：不动
        fmap = tctx[0] if tctx else (cur_fields if form_table == 'current' else None)
        if strict and fmap is None:
            raise ValueError('formTable=link-record 时必须提供 linkRecordField'
                             '（当前表内的单条关联记录字段）')
        title_of = ({info.get('key'): name for name, info in fmap.items() if info.get('key')}
                    if fmap is not None else {})
        norm = []
        for it in ul:
            if not isinstance(it, dict) or not it.get('key'):
                raise ValueError('updateFieldList 每项必须含 key（字段中文名/model/key）')
            i2 = dict(it)
            attr = i2.get('attr', '')
            if attr not in _ATTR_VALUES:
                raise ValueError("attr 只能是 readonly/''(填写)/required: %s" % attr)
            dv = i2.get('defaultVal', '')
            if isinstance(dv, (list, tuple)):
                dv = ','.join(str(x) for x in dv)  # 多选默认值 UI 以逗号拼串存储
            i2['defaultVal'] = dv
            key = match_any(fmap, i2['key']) if fmap is not None else None
            if key is None and strict:
                raise ValueError('updateFieldList 未找到字段: %s' % i2['key'])
            if key is None:
                norm.append(i2)  # 目标表未知：原样透传
                continue
            i2['key'] = key
            info = find_info(fmap, key)
            if info:
                i2.setdefault('type', info.get('type'))
                i2.setdefault('field', info.get('model'))
                i2.setdefault('model', info.get('model'))
                i2.setdefault('name', title_of.get(key, ''))
            norm.append(i2)
        fc['updateFieldList'] = norm
    return fc


def run(action: str, cfg: dict, app_id: str) -> None:
    code = resolve_code(cfg, app_id)
    view_id = pick(cfg, 'viewId')
    button_id = pick(cfg, 'buttonId', 'id')

    if action == 'list':
        buttons = list_buttons(form_code=code, view_id=view_id)
        dump(True, action, result={'code': code, 'viewId': view_id, 'count': len(buttons),
                                   'buttons': buttons})
        return

    if action == 'get':
        if not button_id:
            raise ValueError('get 必须提供 id/buttonId')
        dump(True, action, result=get_button(button_id))
        return

    if action == 'create':
        label = pick(cfg, 'label')
        if not label:
            raise ValueError('create 必须提供 label（按钮名称）')
        if not check_button_label(code, label):
            raise ValueError('按钮名称已存在: %s' % label)
        click_then = pick(cfg, 'clickThen', default=BUTTON_DEFAULTS['clickThen'])
        if click_then not in _CLICK_THEN:
            raise ValueError('clickThen 只能 %s: %s' % ('/'.join(_CLICK_THEN), click_then))
        show_status = pick(cfg, 'showStatus', default=BUTTON_DEFAULTS['showStatus'])
        if show_status not in _SHOW_STATUS:
            raise ValueError('showStatus 只能 %s: %s' % ('/'.join(_SHOW_STATUS), show_status))
        color = pick(cfg, 'color', default=BUTTON_DEFAULTS['color'])
        if color not in COLOR_PRESETS:
            raise ValueError('color 只能从预设色选: %s' % '；'.join(COLOR_PRESETS))
        icon = pick(cfg, 'icon')
        if icon and ':' not in icon:
            raise ValueError('icon 必须 Iconify 格式 {图标集}:{图标名}，如 ant-design:edit-outlined')
        cond_flat = cond_groups = cond_type = None
        if show_status == 'condition':
            cond_flat, cond_groups, cond_type = _normalise_conditions(cfg, code)
        form_config = None
        if click_then == 'form' and 'buttonFormConfig' in cfg:
            form_config = _normalise_form_config(cfg, code, strict=True)
        if 'flowStatus' in cfg:
            flow_status = bool(cfg['flowStatus'])
        else:
            flow_status = click_then in ('execute', 'confirm')
        if click_then in ('execute', 'confirm') and not flow_status:
            raise ValueError('execute/confirm 必须执行工作流（flowStatus 强制 true）')
        button = dict(BUTTON_DEFAULTS)
        button.update({k: v for k, v in cfg.items() if k not in _SKIP_KEYS
                       and k not in ('global', 'checkOnly', 'buttonId', 'id', 'flowStatus',
                                     'conditions', 'conditionsGroup', 'conditions_group',
                                     'conditionType', 'condition_type', 'confirmText')})
        button['showStatus'] = show_status
        button['clickThen'] = click_then
        button['flowStatus'] = flow_status
        if color is not None:
            button['color'] = color
        if show_status == 'condition':
            button['conditionType'] = cond_type
            if cond_flat:
                button['conditionList'] = cond_flat
            button['conditionsGroup'] = cond_groups
        if form_config is not None:
            button['buttonFormConfig'] = form_config
        if click_then == 'confirm':
            # 对齐 UI ButtonConfirmText：未配置时保存默认文案
            ct = pick(cfg, 'confirmText') or {}
            button['confirmText'] = dict(CONFIRM_TEXT_DEFAULTS, **ct)
        result = create_button(form_code=code, button=button, view_id=view_id if not pick(cfg, 'global') else None)
        out = dict(result or {})
        if flow_status:
            out['note'] = ('flowStatus=True 已自动创建空流程（processId=%s）；流程节点请用 '
                           'jeecg-lowcode-miniflow 技能配置' % out.get('processId'))
        dump(True, action, result={'code': code, 'viewId': view_id, 'button': out})
        return

    if action == 'update':
        if not button_id:
            raise ValueError('update 必须提供 id/buttonId')
        label = pick(cfg, 'label')
        if label and not check_button_label(code, label, button_id=button_id):
            raise ValueError('按钮名称已存在: %s' % label)
        changes = {k: v for k, v in cfg.items() if k not in _SKIP_KEYS and k not in _UPDATE_META
                   and k not in ('buttonId', 'id', 'global', 'checkOnly',
                                 'conditions', 'conditionsGroup', 'conditions_group',
                                 'conditionType', 'condition_type', 'confirmText')}
        if not changes and not any(k in cfg for k in ('conditions', 'conditionsGroup', 'conditions_group')):
            raise ValueError('update 必须提供要改的字段（label/icon/color/showStatus/clickThen/'
                             'conditions/conditionsGroup/processId 等）')
        if 'buttonFormConfig' in changes:
            form_config = _normalise_form_config({**cfg, 'buttonFormConfig': changes['buttonFormConfig']}, code)
            if form_config is not None:
                changes['buttonFormConfig'] = form_config
            elif 'buttonFormConfig' in changes:
                del changes['buttonFormConfig']
        if 'clickThen' in changes and changes['clickThen'] not in _CLICK_THEN:
            raise ValueError('clickThen 只能 %s' % '/'.join(_CLICK_THEN))
        if 'showStatus' in changes and changes['showStatus'] not in _SHOW_STATUS:
            raise ValueError('showStatus 只能 %s' % '/'.join(_SHOW_STATUS))
        if 'color' in changes and changes['color'] not in COLOR_PRESETS:
            raise ValueError('color 只能从预设色选: %s' % '；'.join(COLOR_PRESETS))
        # 字段不一定全的整条回传场景：显式 null 允许用于清字段，这里放行（不做必填校验）
        if 'clickThen' in changes and changes['clickThen'] == 'confirm':
            # 运行时 useCustomButton 会解构 confirmText（tip/ok/cancel），缺了按钮直接渲染崩溃，
            # 故切到 confirm 时保证默认文案存在
            if 'confirmText' not in changes and not cfg.get('confirmText'):
                changes['confirmText'] = dict(CONFIRM_TEXT_DEFAULTS)
        elif 'clickThen' in changes:
            # 从 confirm 切到其它动作：清理 confirmText（对齐 UI 保存逻辑）
            if 'confirmText' not in changes and not cfg.get('confirmText'):
                changes['confirmText'] = None
        if 'showStatus' in changes and changes['showStatus'] == 'always':
            # 从 condition 切到 always：清空条件（conditionType 显式 null）
            if not any(k in cfg for k in ('conditions', 'conditionsGroup', 'conditions_group', 'conditionType', 'condition_type')):
                changes['conditionList'] = []
                changes['conditionsGroup'] = []
                changes['conditionType'] = None
        cond_flat = cond_groups = cond_type = None
        has_cond_cfg = any(k in cfg for k in ('conditions', 'conditionsGroup', 'conditions_group',
                                              'conditionType', 'condition_type'))
        new_status = changes.get('showStatus')
        if new_status == 'condition':
            cond_flat, cond_groups, cond_type = _normalise_conditions(cfg, code)
        elif new_status == 'always' and has_cond_cfg:
            cond_flat, cond_groups = [], []
        elif new_status is None and has_cond_cfg:
            # 只改条件不动 showStatus：要求当前就是 condition，直接整组替换
            cond_flat, cond_groups, cond_type = _normalise_conditions(cfg, code)
        if cond_type is not None:
            changes['conditionType'] = cond_type
        if cond_flat is not None:
            changes['conditionList'] = cond_flat
        if cond_groups is not None:
            changes['conditionsGroup'] = cond_groups
        if 'confirmText' in cfg:
            ct = cfg['confirmText'] or {}
            changes['confirmText'] = dict(CONFIRM_TEXT_DEFAULTS, **ct)
        if not changes:
            raise ValueError('update 没有可写入的变更')
        result = update_button(button_id=button_id, form_code=code, changes=changes, view_id=view_id)
        dump(True, action, result={'id': button_id, 'viewId': view_id, 'changed': changes, 'api': result})
        return

    if action == 'delete':
        if not button_id:
            raise ValueError('delete 必须提供 id/buttonId')
        # 彻底删除按钮（连带触发的工作流），对齐 UI 删除弹窗的「彻底删除」选项
        ok = delete_button(button_id=button_id, form_code=code)
        dump(True, action, result={'deleted': button_id, 'api': ok})
        return

    if action == 'remove':
        # 仅从当前视图移除绑定，按钮本身保留（对齐 UI「仅从当前视图移除」）
        if not button_id or not view_id:
            raise ValueError('remove 必须提供 id/buttonId 和 viewId')
        ok = remove_button_from_view(button_id=button_id, view_id=view_id)
        dump(True, action, result={'viewId': view_id, 'removed': button_id, 'api': ok})
        return

    if action == 'bind':
        # 把已有按钮加入当前视图（对齐 UI「添加已有按钮」）
        if not button_id or not view_id:
            raise ValueError('bind 必须提供 id/buttonId 和 viewId')
        ok = add_button_to_view(button_id=button_id, view_id=view_id)
        dump(True, action, result={'viewId': view_id, 'bound': button_id, 'api': ok})
        return

    if action == 'reorder':
        ids = pick(cfg, 'ids', 'buttonIds')
        if not ids:
            raise ValueError('reorder 必须提供 ids（按钮 id 有序列表）')
        if isinstance(ids, str):
            ids = [i.strip() for i in ids.split(',') if i.strip()]
        ok = reorder_buttons(ids)
        dump(True, action, result={'ids': ids, 'api': ok})
        return

    raise ValueError('不支持的 action: %s（list/get/create/update/delete/remove/bind/reorder）' % action)


def main() -> None:
    parser = argparse.ArgumentParser(description='JeecgBoot 自定义按钮管理（四类视图通用）')
    parser.add_argument('--api-base', required=True)
    parser.add_argument('--token', required=True)
    parser.add_argument('--tenant-id', default=None)
    parser.add_argument('--tenant-name', default=None)
    parser.add_argument('--app-id', default=None)
    parser.add_argument('--app-name', default=None)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument('--json', help='业务 JSON 字符串')
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
        tenant_id = args.tenant_id or resolve_tenant_id(None, tenant_name, args.api_base, args.token)
        init_lowapp(args.api_base, args.token, tenant_id=tenant_id)
        app_id = pick(cfg, 'appId') or args.app_id
        if not app_id:
            if args.app_name or pick(cfg, 'appName'):
                app_id = resolve_app_id(cfg, tenant_id, cli_app_name=args.app_name)
            else:
                raise ValueError('自定义按钮操作必须提供 --app-id/appId 或 --app-name/appName（按钮挂在设计器层）')
        init_lowapp(args.api_base, args.token, tenant_id=tenant_id, app_id=app_id)
        run(action, cfg, app_id)
    except Exception as e:
        dump(False, action, message=str(e))


if __name__ == '__main__':
    main()
