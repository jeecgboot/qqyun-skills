"""
JeecgBoot 表单设计器通用创建脚本
=================================
通过 JSON 配置文件创建/更新表单设计器，避免每次编写大量 Python 代码。

用法:
  python desform_creator.py --api-base <URL> --token <TOKEN> --config <config.json>
  python desform_creator.py --api-base <URL> --token <TOKEN> --config <config.json> --force
  python desform_creator.py --api-base <URL> --token <TOKEN> --tenant-id 2 --app-id <APP_ID> --config <config.json>

参数:
  --api-base    JeecgBoot 后端地址
  --token       X-Access-Token
  --config      JSON 配置文件路径
  --force       强制覆盖已存在的表单（默认检测到已存在时退出）
  --tenant-id   lowApp 模式：组织（租户）ID（整数）
  --app-id      lowApp 模式：应用 ID（字符串）；与 --tenant-id 配合使用

JSON 配置格式:
{
  "formName": "工程竣工验收申请表",
  "formCode": "eng_completion_acceptance",
  "layout": "word",            // auto|half|full|word，默认 auto
  "titleIndex": 0,             // 标题字段索引，默认 0（第一个非分隔符字段）
  "fields": [
    {"name": "自动编号", "type": "auto-number", "prefix": "GCYS"},
    {"name": "条码", "type": "barcode"},
    {"name": "工程名称", "type": "input", "required": true},
    {"name": "工程类别", "type": "radio", "options": ["土建", "安装"]},
    {"name": "开工时间", "type": "date"},
    {"name": "工程量清单", "type": "textarea"},
    {"name": "图片上传", "type": "imgupload"},
    {"name": "定位", "type": "location"},
    {"name": "签字", "type": "hand-sign"},
    {"name": "---", "type": "divider", "text": "第二部分"},
    {"name": "金额", "type": "money", "unit": "万元"},
    {"name": "状态", "type": "select", "options": ["启用", "禁用"]},
    {"name": "性别", "type": "radio", "dictCode": "sex",
     "options": [{"value": "1", "label": "男"}, {"value": "2", "label": "女"}]}
  ],
  "menuParent": "工程管理",     // 可选，生成菜单 SQL 的父菜单名称
  "menuIcon": "ant-design:tool-outlined",  // 可选，父菜单图标
  "expand": {                  // 可选，JS/CSS 增强
    "js": "api.watch({...})",
    "css": ".el-form-item__label { font-weight: bold; }",
    "url": {
      "js": "",
      "css": "/desform/expand/css/custom.css"
    }
  }
}

支持的 type 值:
  基础: input, textarea, number, integer, money, date, time, switch, slider, rate, color
  选择: radio, select, checkbox（支持 options + dictCode）
  系统: select-user, select-depart, org-role, phone, email, area-linkage
  文件: file-upload, imgupload, hand-sign
  高级: auto-number, formula, barcode, location, link-record, link-field
  容器: sub-table-design（设计子表，内嵌 fields 数组）
  布局: divider, editor, markdown

子表配置选项:
  columnNumber: 1/2/3/4，布局列数（默认 2）
  operationMode: 1=行内编辑，2=弹出编辑（默认 1）
  isWordStyle: true/false，Word 文档风格（默认 false）
  isWordInnerGrid: true/false，内嵌栅格（默认 false）
  defaultRows: 默认预填行数（默认 0）
  allowAdd / showCheckbox / showNumber / autoHeight: 操作控制（默认 true）
  defaultValType: none/custom；defaultValue: 默认行数组（默认 none / []）
  required / hidden / hiddenOnAdd / fieldNote: 校验与显示

子表示例:
    {"name": "明细清单", "type": "sub-table-design",
     "columnNumber": 2, "operationMode": 1, "fields": [
      {"name": "物品名称", "type": "input", "required": true},
      {"name": "负责人", "type": "select-user"},
      {"name": "数量", "type": "integer"},
      {"name": "单价", "type": "money"},
      {"name": "是否验收", "type": "switch"}
    ]}
  子表内支持的 type:
    基础: input, textarea, integer, number, money, date, time
    选择: select, radio, checkbox
    系统: select-user, select-depart, select-depart-post, phone, email, area-linkage, capital-money, text-compose
    ⛔ 不允许使用: table-dict, select-tree, category-linkage（联动）
    开关: switch, slider, rate, color
    文件: imgupload, file-upload
    关联: link-record, link-field, formula, product
"""

import argparse
import json
import sys
import os

# 注意：Windows 中文乱码修复已在 desform_utils.py 模块加载时自动处理

# 自动定位 desform_utils.py
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SKILL_DIR = os.path.dirname(_SCRIPT_DIR)
for _path in [os.getcwd(), _SCRIPT_DIR]:
    if os.path.exists(os.path.join(_path, 'desform_utils.py')):
        sys.path.insert(0, _path)
        break

from desform_utils import *
from desform_utils import (_apply_half_layout, _apply_word_layout, _is_half_suitable,
                           apply_group_layout)
from desform_utils import LOWAPP_DISABLED_WIDGET_TYPES


# ============================================================
# type → 工厂函数 映射
# ============================================================
_TYPE_MAP = {
    # 基础
    'input': INPUT,
    'textarea': TEXTAREA,
    'number': NUMBER,
    'integer': INTEGER,
    'money': MONEY,
    'date': DATE,
    'time': TIME,
    'switch': SWITCH,
    'slider': SLIDER,
    'rate': RATE,
    'color': COLOR,
    # 选择
    'radio': RADIO,
    'select': SELECT,
    'checkbox': CHECKBOX,
    # 系统
    'select-user': USER,
    'select-depart': DEPART,
    'select-depart-post': DEPART_POST,
    'phone': PHONE,
    'email': EMAIL,
    'area-linkage': AREA,
    'category-linkage': CATEGORY_LINKAGE,
    'org-role': ORG_ROLE,
    # 文件
    'file-upload': FILE,
    'imgupload': IMGUPLOAD,
    'hand-sign': HANDSIGN,
    # 高级
    'auto-number': AUTONUMBER,
    'formula': FORMULA,
    'barcode': BARCODE,
    'location': LOCATION,
    'table-dict': TABLE_DICT,
    'select-tree': SELECT_TREE,
    'link-record': LINK_RECORD,
    'link-field': LINK_FIELD,
    'capital-money': CAPITAL_MONEY,
    'text-compose': TEXT_COMPOSE,
    'ocr': OCR,
    'map': MAP,
    'summary': SUMMARY,
    'summary-date': SUMMARY_DATE,
    'editor': EDITOR,
    'markdown': MARKDOWN,
    # OA
    'oa-approval-comments': OA_APPROVAL_COMMENTS,
    # 布局容器
    'tabs': TABS,
    'grid': GRID,
    'card': CARD,
    # 静态
    'divider': DIVIDER,
    'text': TEXT,
    'buttons': BUTTONS,
}

# 子表内控件 type → 工厂函数 映射
_SUB_TYPE_MAP = {
    # 基础
    'input': SUB_INPUT,
    'textarea': SUB_TEXTAREA,
    'integer': SUB_INTEGER,
    'number': SUB_NUMBER,
    'money': SUB_MONEY,
    'date': SUB_DATE,
    'time': SUB_TIME,
    # 选择
    'select': SUB_SELECT,
    'radio': SUB_RADIO,
    'checkbox': SUB_CHECKBOX,
    'table-dict': SUB_TABLE_DICT,
    'select-tree': SUB_SELECT_TREE,
    # 系统
    'select-user': SUB_USER,
    'select-depart': SUB_DEPART,
    'select-depart-post': SUB_DEPART_POST,
    'org-role': SUB_ORG_ROLE,
    'phone': SUB_PHONE,
    'email': SUB_EMAIL,
    'area-linkage': SUB_AREA,
    # 开关/评分
    'switch': SUB_SWITCH,
    'slider': SUB_SLIDER,
    'rate': SUB_RATE,
    'color': SUB_COLOR,
    # 文件
    'imgupload': SUB_IMGUPLOAD,
    'file-upload': SUB_FILE,
    # 关联/公式
    'link-record': SUB_LINK_RECORD,
    'link-field': SUB_LINK_FIELD,
    'formula': SUB_FORMULA,
    'product': SUB_PRODUCT,
    'capital-money': SUB_CAPITAL_MONEY,
    'text-compose': SUB_TEXT_COMPOSE,
}

# 子表内控件的参数名映射
_SUB_PARAM_MAP = {
    'required': 'required',
    'col_width': 'col_width',
    'unit': 'unit',
    # sub-select / sub-radio / sub-checkbox
    'options': 'options',
    'dictCode': 'dict_code',
    # sub-select-user / sub-select-depart
    'multiple': 'multiple',
    # sub-switch
    'active': 'active',
    'inactive': 'inactive',
    # sub-table-dict
    'dictTable': 'dict_table',
    'dictCodeCol': 'dict_code_col',
    'dictTextCol': 'dict_text_col',
    'style': 'style',
    'queryScope': 'query_scope',
    'filterable': 'filterable',
    'clearable': 'clearable',
    'disabled': 'disabled',
    # 以下 options-only 参数不走工厂函数，由 _apply_options_keys 后置写入
    # 'useColor': 'useColor',
    # 'fieldNote': 'fieldNote',
    # 'inline': 'inline',
    # 'showLabel': 'showLabel',
    # 'hidden': 'hidden',
    # 'hiddenOnAdd': 'hiddenOnAdd',
    # sub-select-tree
    'categoryCode': 'category_code',
    'dataFrom': 'data_from',
    'tableConf': 'table_conf',
    # sub-link-record
    'sourceCode': 'source_code',
    'titleField': 'title_field',
    'showFields': 'show_fields',
    'showMode': 'show_mode',
    # sub-link-field
    'linkRecordKey': 'link_record_key',
    'showField': 'show_field',
    'fieldType': 'field_type',
    'fieldOptions': 'field_options',
    # sub-formula
    'mode': 'mode',
    'expression': 'expression',
    # sub-formula - date modes
    'dateBegin': 'date_begin',
    'dateEnd': 'date_end',
    'dateFormatMethod': 'date_format_method',
    'datePrintUnit': 'date_print_unit',
    'dateAddExp': 'date_add_exp',
    'datePrintFormat': 'date_print_format',
    # sub-product
    'field_models': 'field_models',
    # sub-area-linkage
    'areaLevel': 'level',
}

# 需要 options 参数的控件类型（options 作为第二个位置参数）
_OPTION_TYPES = {'radio', 'select', 'checkbox'}

# 参数名映射：JSON key → 函数参数名
_PARAM_MAP = {
    'required': 'required',
    'width': 'width',
    'prefix': 'prefix',
    'dateFormat': 'date_format',
    'unit': 'unit',
    'placeholder': 'placeholder',
    'multiple': 'multiple',
    'dictCode': 'dict_code',
    'unique': 'unique',
    'precision': 'precision',
    'allowHalf': 'allow_half',
    'fmt': 'fmt',
    'codeType': 'code_type',
    # formula
    'mode': 'mode',
    'expression': 'expression',
    'decimal': 'decimal',
    # formula - date modes
    'dateBegin': 'date_begin',
    'dateEnd': 'date_end',
    'dateFormatMethod': 'date_format_method',
    'datePrintUnit': 'date_print_unit',
    'dateAddExp': 'date_add_exp',
    'datePrintFormat': 'date_print_format',
    # link-record
    'sourceCode': 'source_code',
    'titleField': 'title_field',
    'showFields': 'show_fields',
    'showMode': 'show_mode',
    'showType': 'showType',
    'isSelf': 'is_self',
    # link-field
    'linkRecordKey': 'link_record_key',
    'showField': 'show_field',
    'fieldType': 'field_type',
    'fieldOptions': 'field_options',
    # table-dict
    'dictTable': 'dict_table',
    'dictCodeCol': 'dict_code_col',
    'dictTextCol': 'dict_text_col',
    'style': 'style',
    'queryScope': 'query_scope',
    'filterable': 'filterable',
    'clearable': 'clearable',
    'disabled': 'disabled',
    # 以下 options-only 参数不走工厂函数，由 _apply_options_keys 后置写入
    # 'useColor': 'useColor',
    # 'fieldNote': 'fieldNote',
    # 'inline': 'inline',
    # 'showLabel': 'showLabel',
    # 'hidden': 'hidden',
    # 'hiddenOnAdd': 'hiddenOnAdd',
    # date / summary-date
    'format': 'fmt',
    'dateType': 'date_type',
    # select-tree
    'categoryCode': 'category_code',
    'dataFrom': 'data_from',
    'tableConf': 'table_conf',
    # barcode
    'sourceModel': 'source_model',
    'maxWidth': 'max_width',
    # capital-money
    'moneyWidgetKey': 'money_widget_key',
    'moneyField': 'money_field',
    # summary
    'subTableModel': 'sub_table_model',
    'fieldModel': 'field_model',
    'summaryType': 'summary_type',
    'linkTable': 'sub_table_model',
    'field': 'field_model',
    'filter': 'filter',
    # text-compose
    # (expression 已在 formula 区映射)
    # remoteAPI 远程取值
    'remoteAPI': 'remote_api',
    # 默认值表达式（compose 类型，支持 {{上下文变量}} 和 $字段引用$）
    'defaultExpr': 'default_expr',
    # 填值规则编码（仅 input 控件支持）
    'fillRuleCode': 'fill_rule_code',
    # 完全只读（配合填值规则使用，防止用户修改生成值）
    'readonly': 'readonly',
    # location
    'defaultCurrent': 'default_current',
    'showMap': 'show_map',
    # map
    'height': 'height',
    'zoom': 'zoom',
    'lng': 'lng',
    'lat': 'lat',
    # ocr
    'ocrType': 'ocr_type',
    'fieldMapping': 'field_mapping',
    # text
    'text': 'text',
    'fontSize': 'font_size',
    'fontColor': 'font_color',
    'align': 'align',
    'bold': 'bold',
    # buttons
    'btnType': 'btn_type',
    'icon': 'icon',
    'clickCode': 'click_code',
    # tabs
    'tabLabels': 'tab_labels',
    'tabType': 'tab_type',
    'position': 'position',
    # switch
    'active': 'active',
    'inactive': 'inactive',
    # slider
    'minVal': 'min_val',
    'maxVal': 'max_val',
    'showInput': 'show_input',
    # imgupload
    'length': 'length',
    # area-linkage：源码 options.areaLevel（1=省，2=省市，3=省市区，默认 3）
    'areaLevel': 'level',
    # input 扫码 【LHZP-1945】
    'allowScan': 'allow_scan',
    'scanEditable': 'scan_editable',
    # category-linkage 【LHZP-229】
    'table': 'table',
    'txt': 'txt',
    'storeKey': 'store_key',
    'idField': 'id_field',
    'pidField': 'pid_field',
    'condition': 'condition',
    'level': 'level',
}

# ---- 白名单：纯 options 属性的 JSON 配置键 ----
# 这些键的最终归宿是 widget.options，但没有任何工厂函数接受它们作为参数，
# 因此从 _PARAM_MAP 中移除，在 widget 构建后通过 _apply_options_keys 写入。
_OPTIONS_KEYS = {
    'fieldNote', 'hidden', 'hiddenOnAdd', 'inline', 'showLabel', 'useColor',
    'disabled', 'placeholder', 'unique', 'readonly', 'precision', 'allowHalf',
    'filterable', 'clearable',
}

# 全新创建子表（sub-table-design）面板项，写入子表 options，不进列控件
_SUB_TABLE_OPTIONS_KEYS = {
    'allowAdd', 'showCheckbox', 'showNumber', 'autoHeight', 'showRowButton',
    'defaultValType', 'defaultValue',
    'required', 'hidden', 'hiddenOnAdd', 'fieldNote',
}

# 所有已知的 JSON 配置键（白名单校验用，避免误报警告）
_KNOWN_JSON_KEYS = {'name', 'type', 'options', 'text', 'fields',
                    'columnNumber', 'operationMode', 'isWordStyle', 'isWordInnerGrid', 'defaultRows',
                    'category'}
_KNOWN_JSON_KEYS |= set(_PARAM_MAP.keys()) | _OPTIONS_KEYS | _SUB_TABLE_OPTIONS_KEYS
_SUB_KNOWN_JSON_KEYS = {'name', 'type'} | set(_SUB_PARAM_MAP.keys()) | _OPTIONS_KEYS


def _apply_options_keys(widget, field_def):
    """将 field_def 白名单内的 options 属性写入 widget.options。
    widget 可能是 (card, key, model) tuple 或纯 dict。
    """
    w = widget[0] if isinstance(widget, tuple) else widget
    # card 容器：提取内层控件
    if w.get('type') == 'card' and w.get('list') and len(w['list']) == 1:
        w = w['list'][0]
    opts = w.setdefault('options', {})
    for key in _OPTIONS_KEYS:
        if key in field_def:
            opts[key] = field_def[key]


def _build_sub_widget(field_def, parent_key):
    """根据 JSON 字段定义构建子表内控件 tuple"""
    ftype = field_def['type']
    name = field_def['name']

    if ftype in LOWAPP_DISABLED_WIDGET_TYPES:
        raise ValueError(
            f'敲敲云子表不允许使用控件 "{name}" 的类型 {ftype}。'
            f'已禁用：table-dict、select-tree、category-linkage（联动）、cascader、全部 OA 字段。'
        )

    factory = _SUB_TYPE_MAP.get(ftype)
    if not factory:
        raise ValueError(f'子表内不支持的控件类型: {ftype}（支持: {", ".join(_SUB_TYPE_MAP.keys())}）')

    kwargs = {}
    for json_key, param_name in _SUB_PARAM_MAP.items():
        if json_key in field_def:
            kwargs[param_name] = field_def[json_key]

    # 警告未知参数
    for k in field_def:
        if k not in _SUB_KNOWN_JSON_KEYS:
            print(f'  ⚠ [警告] 子表字段 "{name}" 的配置项 "{k}" 脚本无法识别，如需配置请使用 --preprocess 预处理方式设置')

    # sub-select / sub-radio / sub-checkbox 需要 options 作为位置参数
    if ftype in ('select', 'radio', 'checkbox'):
        options = kwargs.pop('options', [])
        return factory(name, parent_key, options, **kwargs)

    # sub-table-dict 需要 dict_table, dict_code_col, dict_text_col
    if ftype == 'table-dict':
        dict_table = kwargs.pop('dict_table', '')
        dict_code_col = kwargs.pop('dict_code_col', '')
        dict_text_col = kwargs.pop('dict_text_col', '')
        return factory(name, parent_key, dict_table, dict_code_col, dict_text_col, **kwargs)

    # sub-link-record 需要 source_code, title_field 作为位置参数
    if ftype == 'link-record':
        source_code = kwargs.pop('source_code')
        title_field = kwargs.pop('title_field')
        return factory(name, parent_key, source_code, title_field, **kwargs)

    # sub-link-field 需要 link_record_key, show_field 作为位置参数
    if ftype == 'link-field':
        link_record_key = kwargs.pop('link_record_key')
        show_field = kwargs.pop('show_field')
        return factory(name, parent_key, link_record_key, show_field, **kwargs)

    # sub-product 需要 field_models 作为位置参数
    if ftype == 'product':
        field_models = kwargs.pop('field_models')
        return factory(name, parent_key, field_models, **kwargs)

    return factory(name, parent_key, **kwargs)


def build_widget(field_def):
    """根据 JSON 字段定义构建控件 tuple（或子表容器 dict）"""
    ftype = field_def['type']
    name = field_def['name']

    if ftype in LOWAPP_DISABLED_WIDGET_TYPES:
        raise ValueError(
            f'敲敲云设计器不支持控件 "{name}" 的类型 {ftype}。'
            f'已禁用：table-dict、select-tree、cascader、category-linkage、全部 OA 字段。'
            f'多级选项请用 radio/select。'
        )

    # 子表特殊处理
    if ftype == 'sub-table-design':
        sub_fields = field_def.get('fields', [])
        column_number = field_def.get('columnNumber', 2)
        # 先用临时 key 构建子控件（需要 parent_key）
        # 创建空子表仅为获取 key
        tmp_table, parent_key = make_sub_table(name, [], column_number=1)
        sub_widgets = []
        for sf in sub_fields:
            w, k, m = _build_sub_widget(sf, parent_key)
            _apply_options_keys(w, sf)
            sub_widgets.append(w)
        # 用真正的参数创建子表（sub_widgets 会被均匀分配到各列）
        sub_table, _ = make_sub_table(
            name, sub_widgets,
            column_number=column_number,
            operation_mode=field_def.get('operationMode', 1),
            is_word_style=field_def.get('isWordStyle', False),
            is_word_inner_grid=field_def.get('isWordInnerGrid', False),
            default_rows=field_def.get('defaultRows', 0),
        )
        # 修正 key/model：使用第一次生成的 key（子控件的 parentKey 指向它）
        sub_table['key'] = parent_key
        sub_table['model'] = tmp_table['model']
        opts = sub_table.setdefault('options', {})
        for key in _SUB_TABLE_OPTIONS_KEYS:
            if key in field_def:
                opts[key] = field_def[key]
        return sub_table

    factory = _TYPE_MAP.get(ftype)
    if not factory:
        raise ValueError(f'未知的控件类型: {ftype}')

    # 构建关键字参数
    kwargs = {}
    for json_key, param_name in _PARAM_MAP.items():
        if json_key in field_def:
            kwargs[param_name] = field_def[json_key]

    # 警告未知参数
    for k in field_def:
        if k not in _KNOWN_JSON_KEYS:
            print(f'  ⚠ [警告] 字段 "{name}" 的配置项 "{k}" 脚本无法识别，如需配置请使用 --preprocess 预处理方式设置')

    # divider 特殊处理：text 参数
    if ftype == 'divider':
        text = field_def.get('text', name)
        return factory(text)

    # text 静态文本：无 name 参数，用 text 参数
    if ftype == 'text':
        return factory(**kwargs)

    # buttons 按钮：无 name 参数
    if ftype == 'buttons':
        return factory(**kwargs)

    # tabs 容器：无 name 参数
    if ftype == 'tabs':
        return factory(**kwargs)

    # map 地图：name + kwargs
    if ftype == 'map':
        return factory(name, **kwargs)

    # summary 汇总控件：需要 sub_table_model + field_model 作为位置参数
    if ftype == 'summary':
        sub_table_model = kwargs.pop('sub_table_model', '')
        field_model = kwargs.pop('field_model', '')
        return factory(name, sub_table_model, field_model, **kwargs)

    # summary-date 汇总日期：同 summary，位置参数 + date_type/fmt 等可选
    if ftype == 'summary-date':
        sub_table_model = kwargs.pop('sub_table_model', '')
        field_model = kwargs.pop('field_model', '')
        return factory(name, sub_table_model, field_model, **kwargs)

    # 需要 options 的控件
    if ftype in _OPTION_TYPES:
        options = field_def.get('options', [])
        return factory(name, options, **kwargs)

    # auto-number 特殊处理
    if ftype == 'auto-number':
        return factory(name, **kwargs)

    # table-dict：需要 dict_table 等位置参数，style 和 query_scope 通过 **kwargs 传递
    if ftype == 'table-dict':
        dict_table = kwargs.pop('dict_table', '')
        dict_code_col = kwargs.pop('dict_code_col', '')
        dict_text_col = kwargs.pop('dict_text_col', '')
        return factory(name, dict_table, dict_code_col, dict_text_col, **kwargs)

    # select-tree：需要 category_code
    if ftype == 'select-tree':
        category_code = kwargs.pop('category_code', '')
        return factory(name, category_code, **kwargs)

    # category-linkage：表名/字段映射；也接受嵌套 category 对象
    if ftype == 'category-linkage':
        cat = field_def.get('category') or {}
        return factory(
            name,
            table=kwargs.pop('table', None) or cat.get('table', ''),
            txt=kwargs.pop('txt', None) or cat.get('txt', ''),
            store_key=kwargs.pop('store_key', None) or cat.get('key', ''),
            id_field=kwargs.pop('id_field', None) or cat.get('idField', ''),
            pid_field=kwargs.pop('pid_field', None) or cat.get('pidField', ''),
            condition=kwargs.pop('condition', None) or cat.get('condition', ''),
            level=kwargs.pop('level', None) or cat.get('level', 3),
            **kwargs,
        )

    # 其余控件：name + kwargs
    return factory(name, **kwargs)


def _extract_widget_info(item):
    """从 widget tuple 或 dict 中提取 (inner_widget, key, model, type)"""
    if isinstance(item, tuple):
        w, key, model = item[0], item[1], item[2]
    else:
        w = item
        key, model = w.get('key', ''), w.get('model', '')
    # card 容器：提取内部控件
    inner = w
    if w.get('type') == 'card' and w.get('list') and len(w['list']) == 1:
        inner = w['list'][0]
    return inner, key, model, inner.get('type', '')


def _find_sub_field_widget(widgets, sub_table_name, field_name):
    """在 widgets 中查找子表内的字段 widget。

    Args:
        widgets: create_form 的 widgets 列表
        sub_table_name: 子表中文名
        field_name: 子表内字段中文名

    Returns:
        找到的字段 widget dict，未找到返回 None
    """
    for item in widgets:
        inner, key, model, wtype = _extract_widget_info(item)
        if wtype == 'sub-table-design' and inner.get('name') == sub_table_name:
            for col in inner.get('columns', []):
                for sw in col.get('list', []):
                    if sw.get('name') == field_name:
                        return sw
    return None


def _build_name_registry(fields, widgets):
    """构建两级作用域注册表，解决主表/子表字段同名冲突

    Returns:
        (main_registry, sub_registry)
        - main_registry: {字段名 → (key, model, type)}  仅主表字段
        - sub_registry:  {子表名 → {字段名 → (key, model, type)}}

    规则：
        - 向下（主→子）禁止引用
        - 向上（子→主）仅默认值允许，公式/条码等禁止跨界
    """
    main_registry = {}   # 主表字段
    sub_registry = {}    # {子表名称: {子字段名 → (key, model, type)}}

    for fd, widget in zip(fields, widgets):
        inner, key, model, wtype = _extract_widget_info(widget)
        name = fd.get('name', '')

        # 主表字段（排除分隔符；子表容器也需注册，供 summary linkTable 查 model）
        if name and name != '---' and key and model:
            main_registry[name] = (key, model, wtype)

        # 子表内字段：归属到子表名下，不与主表混合
        if wtype == 'sub-table-design' and 'columns' in inner:
            sub_fields = {}
            for col in inner.get('columns', []):
                for sub_w in col.get('list', []):
                    sub_name = sub_w.get('name', '')
                    sub_key = sub_w.get('key', '')
                    sub_model = sub_w.get('model', '')
                    sub_type = sub_w.get('type', '')
                    if sub_name and sub_key and sub_model:
                        sub_fields[sub_name] = (sub_key, sub_model, sub_type)
            sub_registry[name] = sub_fields

    return main_registry, sub_registry


def _resolve_model_ref(expression, scope_registry):
    """解析表达式中的 $placeholder$ 引用，替换为实际的 model

    Args:
        expression: 含 $字段名$ 占位符的表达式
        scope_registry: {字段名 → (key, model, type)}  限定查找范围

    仅在 scope_registry 内查找，找不到则保留原样（可能已是实际 model）。
    """
    import re

    def replacer(match):
        ref = match.group(1)
        if ref in scope_registry:
            return f'${scope_registry[ref][1]}$'
        return match.group(0)

    return re.sub(r'\$([^$]+)\$', replacer, expression)


def _post_process_widgets(fields, widgets):
    """对构建完成的控件列表进行后处理，自动解析跨控件引用

    处理内容：
    1. capital-money: 在主表作用域内查找 money 控件 key
    2. summary: linkTable(子表名匹配) / field(子表内作用域) / filter(子表内作用域)
    3. formula(主表): 表达式仅在 main_registry 中解析
    4. barcode: sourceModel 仅在 main_registry 中解析
    5. text-compose: expression 仅在 main_registry 中解析
    6. link-record: titleField 仅在 main_registry 中解析
    7. 子表 formula: 仅在本子表作用域内解析，不穿透到主表

    作用域规则：
        - 向下（主→子）禁止：主表公式/条码等不能引用子表字段
        - 向上（子→主）仅默认值允许：子表公式不允许引用主表字段
    """
    main_registry, sub_registry = _build_name_registry(fields, widgets)

    for i, (fd, widget) in enumerate(zip(fields, widgets)):
        inner, key, model, wtype = _extract_widget_info(widget)

        # 1. capital-money: 在主表作用域内查找 money 控件 key
        if wtype == 'capital-money':
            opts = inner.get('options', {})
            money_field_name = opts.pop('moneyField', None) or fd.get('moneyField')
            if money_field_name and money_field_name in main_registry:
                resolved_key = main_registry[money_field_name][0]
                opts['moneyWidgetKey'] = resolved_key
                print(f'  [指定关联] 大写金额 "{fd.get("name")}" → moneyField="{money_field_name}" → moneyWidgetKey={resolved_key}')
            elif not opts.get('moneyWidgetKey'):
                # 兜底：查找前面最近的 money/formula/summary 控件（仅主表）
                money_key = None
                for j in range(i - 1, -1, -1):
                    _, prev_key, _, prev_type = _extract_widget_info(widgets[j])
                    if prev_type in ('money', 'formula', 'summary'):
                        money_key = prev_key
                        break
                if money_key:
                    opts['moneyWidgetKey'] = money_key
                    print(f'  [自动关联] 大写金额 "{fd.get("name")}" → moneyWidgetKey={money_key}')
                else:
                    print(f'  [警告] 大写金额 "{fd.get("name")}" 未找到可关联的金额控件')

        # 2. summary / summary-date: linkTable 匹配子表名，field/filter 在本子表作用域内解析
        if wtype == 'summary' or (wtype == 'date' and inner.get('isSummary')):
            opts = inner.get('options', {})
            # linkTable: 子表中文名 → 子表 model（匹配 sub_registry 的 key）
            link_table = opts.get('linkTable', '')
            if link_table and link_table in sub_registry:
                # 子表本身也是一个主表控件，用 main_registry 取其 model
                resolved_model = main_registry.get(link_table, (None, link_table, None))[1]
                opts['linkTable'] = resolved_model
                print(f'  [自动解析] 汇总 "{fd.get("name")}" linkTable: "{link_table}" → {resolved_model}')

                # field/filter: 在对应子表作用域内解析
                sub_scope = sub_registry[link_table]
                # inner-record-count 特殊处理：field 填汇总类型字符串，summary 留空
                summary_type = opts.get('summary', '')
                if summary_type == 'inner-record-count':
                    opts['field'] = 'inner-record-count'
                    opts['summary'] = ''
                    print(f'  [自动解析] 汇总 "{fd.get("name")}" inner-record-count → field="inner-record-count", summary=""')
                else:
                    field_val = opts.get('field', '')
                    if field_val and field_val in sub_scope:
                        resolved_field = sub_scope[field_val][1]
                        opts['field'] = resolved_field
                        print(f'  [自动解析] 汇总 "{fd.get("name")}" field: "{field_val}" → {resolved_field}')
                        # summary-date: 同步 designType 和 format 到被引用的日期字段
                        if wtype == 'date' and inner.get('isSummary'):
                            # 从子表 widget 中查找原字段的 options
                            sub_widget = _find_sub_field_widget(widgets, link_table, field_val)
                            if sub_widget:
                                sub_opts = sub_widget.get('options', {})
                                sub_dt = sub_opts.get('designType', 'date')
                                sub_fmt = sub_opts.get('format', 'yyyy-MM-dd')
                                opts['type'] = sub_dt
                                opts['designType'] = sub_dt
                                opts['format'] = sub_fmt
                                print(f'  [自动匹配] 汇总日期 "{fd.get("name")}" designType/format → {sub_dt}/{sub_fmt}')

                flt = opts.get('filter', {})
                if flt.get('enabled'):
                    for rule in flt.get('rules', []):
                        rule_model = rule.get('model', '')
                        if rule_model and rule_model in sub_scope:
                            rule['model'] = sub_scope[rule_model][1]
                            print(f'  [自动解析] 汇总 "{fd.get("name")}" filter.model: "{rule_model}" → {sub_scope[rule_model][1]}')
                        if rule.get('valueType') == 'field':
                            new_values = []
                            for v in rule.get('value', []):
                                if isinstance(v, str) and v in sub_scope:
                                    new_values.append(sub_scope[v][1])
                                else:
                                    new_values.append(v)
                            rule['value'] = new_values
            elif link_table and link_table in main_registry:
                # 兼容：linkTable 已是 model 的情况
                pass

        # 3. formula(主表): 仅 main_registry，不穿透到子表
        if wtype == 'formula':
            opts = inner.get('options', {})
            for expr_field in ('expression', 'dateBegin', 'dateEnd', 'dateAddExp'):
                val = opts.get(expr_field, '')
                if val and '$' in val:
                    resolved = _resolve_model_ref(val, main_registry)
                    if resolved != val:
                        opts[expr_field] = resolved
                        print(f'  [自动解析] 公式 "{fd.get("name")}" {expr_field}: {val} → {resolved}')

        # 4. barcode: sourceModel 仅 main_registry
        if wtype == 'barcode':
            opts = inner.get('options', {})
            src = opts.get('sourceModel', '')
            if src and '$' in src:
                resolved = _resolve_model_ref(src, main_registry)
                if resolved != src:
                    opts['sourceModel'] = resolved

        # 5. text-compose: expression 仅 main_registry
        if wtype == 'text-compose':
            opts = inner.get('options', {})
            expr = opts.get('expression', '')
            if expr and '$' in expr:
                resolved = _resolve_model_ref(expr, main_registry)
                if resolved != expr:
                    opts['expression'] = resolved
                    print(f'  [自动解析] 文本组合 "{fd.get("name")}" expression: {expr} → {resolved}')

        # 6. link-record: titleField 仅 main_registry（自关联时常用）
        if wtype == 'link-record':
            opts = inner.get('options', {})
            tf = opts.get('titleField', '')
            if tf and tf in main_registry:
                resolved_model = main_registry[tf][1]
                opts['titleField'] = resolved_model
                print(f'  [自动解析] 关联记录 "{fd.get("name")}" titleField: "{tf}" → {resolved_model}')

    # 7. 子表内 formula/product: 仅在本子表作用域内解析，不穿透到主表
    for i, (fd, widget) in enumerate(zip(fields, widgets)):
        inner, _, _, wtype = _extract_widget_info(widget)
        if wtype == 'sub-table-design' and 'columns' in inner:
            sub_name = fd.get('name', '')
            sub_scope = sub_registry.get(sub_name, {})
            for col in inner.get('columns', []):
                for sub_w in col.get('list', []):
                    sub_type = sub_w.get('type', '')
                    if sub_type == 'formula':
                        sub_opts = sub_w.get('options', {})
                        for expr_field in ('expression', 'dateBegin', 'dateEnd', 'dateAddExp'):
                            val = sub_opts.get(expr_field, '')
                            if val and '$' in val:
                                resolved = _resolve_model_ref(val, sub_scope)
                                if resolved != val:
                                    sub_opts[expr_field] = resolved


def _extract_field_table(design_json):
    """从设计 JSON 中提取字段参照表，委托给 desform_utils 中的同名函数"""
    return extract_field_table_from_design(design_json)


def _print_field_table(field_rows):
    """格式化打印字段参照表"""
    print(f'\n  {"字段名称":<20} {"key":<35} {"model":<45} {"type"}')
    print(f'  {"-"*20} {"-"*35} {"-"*45} {"-"*15}')
    for row in field_rows:
        print(f'  {row["name"]:<20} {row["key"]:<35} {row["model"]:<45} {row["type"]}')


def main():
    parser = argparse.ArgumentParser(description='JeecgBoot 表单设计器通用创建工具')
    parser.add_argument('--api-base', required=True, help='JeecgBoot 后端地址')
    parser.add_argument('--token', required=True, help='X-Access-Token')
    parser.add_argument('--config', required=True, help='JSON 配置文件路径，传 "-" 则从 stdin 读取')
    parser.add_argument('--force', action='store_true', help='强制覆盖已存在的表单')
    parser.add_argument('--check-only', action='store_true',
                        help='仅检查表单编码是否可用，不创建表单')
    parser.add_argument('--preprocess', action='store_true',
                        help='预处理模式：生成设计JSON到临时文件后退出，供AI手动修改，'
                             '修改完成后调用 save_design_from_file(code, file_path) 保存')
    parser.add_argument('--tenant-id', type=int, default=None,
                        help='lowApp 模式：组织（租户）ID，与 --app-id 配合使用')
    parser.add_argument('--app-id', default=None,
                        help='lowApp 模式：应用 ID，与 --tenant-id 配合使用')
    args = parser.parse_args()

    if args.config == '-':
        import sys as _sys, io as _io
        stdin_stream = _io.TextIOWrapper(_sys.stdin.buffer, encoding='utf-8')
        config = json.load(stdin_stream)
    else:
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)

    form_name = config['formName']
    form_code = config['formCode']
    layout = config.get('layout', 'auto')
    title_index = config.get('titleIndex', 0)
    # lowApp 工作表分组（2026-09-08：有分组时默认归第一个，链脚本注入；直接跑 creator 可手写）
    app_menu_group_id = config.get('appMenuGroupId')

    if args.tenant_id is not None:
        import importlib, desform_lowapp_utils as _lowapp_utils
        _lowapp_utils.init_lowapp(args.api_base, args.token,
                                  tenant_id=args.tenant_id,
                                  app_id=args.app_id)
    else:
        init_api(args.api_base, args.token)

    # --check-only：仅检查编码可用性
    if args.check_only:
        available = check_code_available(form_code)
        print(f"编码 {form_code} {'可用' if available else '已被占用'}")
        sys.exit(0 if available else 1)

    # 防覆盖检查
    existing_id, _ = get_form_id(form_code)
    if existing_id and not args.force:
        print(f'[阻止] 表单 {form_code} 已存在 (ID={existing_id})')
        print(f'如需覆盖，请加 --force 参数')
        sys.exit(1)

    # 构建控件列表
    fields = config.get('fields', [])
    widgets = []
    for fd in fields:
        widget = build_widget(fd)
        _apply_options_keys(widget, fd)
        widgets.append(widget)

    # 后处理：自动解析跨控件引用（capital-money、formula 表达式等）
    _post_process_widgets(fields, widgets)

    # JS/CSS 增强配置
    expand = config.get('expand')

    # config 覆盖项：从 JSON 配置中提取需要覆盖的 config 字段
    config_overrides = {}
    if config.get('customRequestURL'):
        config_overrides['customRequestURL'] = [{"url": config['customRequestURL']}]
    if 'transactional' in config:
        config_overrides['transactional'] = config['transactional']

    # --preprocess：生成设计 JSON 到临时文件后退出，供 AI 手动修改
    if args.preprocess:
        import tempfile
        form_style = 'word' if layout == 'word' else 'normal'

        # 与 create_form 内部相同的布局逻辑
        if layout == 'word':
            top_items, all_models = _apply_word_layout(widgets, form_name=form_name)
        elif config.get('sections'):
            top_items, all_models = apply_group_layout(widgets, config['sections'])
        elif layout == 'half' or (layout == 'auto' and len(widgets) >= 6):
            top_items, all_models = _apply_half_layout(widgets)
        else:
            top_items = []
            all_models = []
            for item in widgets:
                if isinstance(item, tuple):
                    top_items.append(item[0])
                    all_models.append((item[1], item[2]))
                else:
                    top_items.append(item)
                    all_models.append((item.get('key', ''), item.get('model', '')))

        title_model = all_models[title_index][1] if title_index < len(all_models) else all_models[0][1]
        design_json = build_design_json(top_items, title_model, form_style, expand=expand,
                                        config_overrides=config_overrides or None)

        # 创建表单实体（获取 form_id，设计 JSON 稍后由 save_design_from_file 保存）
        form_id, uc, actual_code = find_or_create_form(
            form_name, form_code, app_menu_group_id=app_menu_group_id)

        # 写入临时文件（格式化 JSON）
        tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False,
            encoding='utf-8', prefix=f'desform_{form_code}_'
        )
        json.dump(design_json, tmp, ensure_ascii=False, indent=2)
        tmp.close()

        field_rows = _extract_field_table(design_json)

        print(f'\n{"=" * 60}')
        print(f'[预处理模式] 设计JSON已生成，等待手动修改后保存')
        print(f'{"=" * 60}')
        print(f'  表单ID:   {form_id}')
        print(f'  表单编码: {actual_code}')
        print(f'  JSON文件: {tmp.name}')
        _print_field_table(field_rows)
        print(f'\n修改完成后，调用以下方法保存:')
        print(f'  save_design_from_file("{actual_code}", r"{tmp.name}")')
        sys.exit(0)

    # 创建表单
    form_id, title_model = create_form(form_name, form_code, widgets,
                                        title_index=title_index, layout=layout,
                                        expand=expand,
                                        config_overrides=config_overrides or None,
                                        app_menu_group_id=app_menu_group_id,
                                        sections=config.get('sections'))

    print(f'\n{"=" * 50}')
    print(f'表单创建成功')
    print(f'{"=" * 50}')
    print(f'  表单ID:   {form_id}')
    print(f'  表单名称: {form_name}')
    print(f'  表单编码: {form_code}')
    print(f'  标题字段: {title_model}')
    print(f'  布局风格: {layout}')

    # 生成菜单 SQL
    menu_parent = config.get('menuParent')
    if menu_parent:
        menu_icon = config.get('menuIcon', 'ant-design:appstore-outlined')
        sql = gen_menu_sql(menu_parent, [
            (form_name, form_code, 1),
        ], icon=menu_icon)
        print(f'\n--- 菜单 SQL ---\n{sql}')


if __name__ == '__main__':
    main()
