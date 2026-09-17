# -*- coding: utf-8 -*-
"""
JeecgBoot 表单设计器（desform）- 积木报表集成工具脚本

一键创建积木报表并关联到 desform 表单的打印功能（单条记录卡片式 / Word 风格打印布局）。

用法:
  python desform_jimureport.py --api-base <URL> --token <TOKEN> --config <config.json>

config.json 格式:
  {
    "action": "create_report",
    "desformCode": "oa_car_use",      // desform 表单编码（必填）
    "reportName": "用车申请打印",       // 可选，缺省 = "{表单名}打印"
    "formStyle": "auto",              // 可选 auto(默认,自动读表单formStyle) / normal / word
    "fields": [                       // 可选，不提供则自动从表单字段读取
      {"fieldName": "input_xxx", "fieldText": "申请人"}
    ]
  }

  {
    "action": "delete_report",
    "reportId": "xxx",
    "desformCode": "oa_car_use"       // 可选，提供则同时清除表单 allowJmReport 关联
  }

与 onlform 集成的关键差异（已实测确认 @2026-05-21）:
  - 数据 API:  /desform/api/data/{desformCode}/queryById?id=${id}&token=${token}  （无 mock 参数）
  - 字段引用:  ${dbCode.model}  单值绑定（不是 onlform 的 #{dbCode.field} 列表绑定）
  - fieldName: 控件 model（数据 API 返回 JSON 的 key 永远等于控件 model）
  - fieldText: 控件 title（中文名）
  - 预览 URL:  {{sysBasePath}}/jmreport/view/{reportId}  （desform 专用变量）
  - 回写表单:  designConfig.config.allowJmReport=true + jmReportURL=预览URL
"""

import os
import sys
import json
import ssl
import time
import hashlib
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from desform_utils import (  # noqa: E402
    init_api, query_form, update_design_config, get_api_base, _urlopen,
)

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

# 积木报表接口基础地址（可能与 desform 的 api-base 不同，见 main / --jmreport-base）
_JM_BASE = None

# 积木报表接口签名密钥（与 onlform 集成脚本一致）
SIGNATURE_SECRET = 'dd05f1c54d63749eda95f9fa6d49v442a'
SIGNED_ENDPOINTS = [
    '/jmreport/queryFieldBySql', '/jmreport/executeSelectApi',
    '/jmreport/loadTableData', '/jmreport/testConnection',
    '/jmreport/download/image', '/jmreport/dictCodeSearch',
    '/jmreport/getDataSourceByPage', '/jmreport/getDataSourceById',
]

# desform 报表类型 ID（积木报表内部 type，沿用系统默认值）
JM_REPORT_TYPE = '984272091947253760'

# 长文本控件类型：值独占整行
LONG_TEXT_TYPES = {'textarea', 'rich-editor', 'editor', 'html', 'json-editor'}


# ====== 积木报表 HTTP（自包含，含签名 + 双 token header） ======

def _compute_sign(params_dict):
    str_params = {}
    for k, v in params_dict.items():
        if v is None:
            continue
        if isinstance(v, bool):
            str_params[k] = str(v).lower()
        elif isinstance(v, (int, float)):
            str_params[k] = str(v)
        elif isinstance(v, (dict, list)):
            str_params[k] = json.dumps(v, ensure_ascii=False, separators=(',', ':'))
        else:
            str_params[k] = str(v)
    sorted_params = dict(sorted(str_params.items()))
    params_json = json.dumps(sorted_params, ensure_ascii=False, separators=(',', ':'))
    return hashlib.md5((params_json + SIGNATURE_SECRET).encode('utf-8')).hexdigest().upper()


def _jm_request(token, path, data=None, method='POST'):
    """调用积木报表接口（带 X-Access-Token + token 双 header，必要时签名）。
    使用 _JM_BASE（积木报表服务地址，可能与 desform 的 api-base 不同）。"""
    import urllib.request
    base = (_JM_BASE or get_api_base()).rstrip('/')
    url = f'{base}{path}'
    if method == 'GET':
        sep = '&' if '?' in url else '?'
        url += f'{sep}_t={int(time.time() * 1000)}'
    headers = {
        'X-Access-Token': token,
        'token': token,
        'Content-Type': 'application/json; charset=UTF-8',
    }
    if any(path.rstrip('/').endswith(ep.rstrip('/')) for ep in SIGNED_ENDPOINTS):
        headers['X-TIMESTAMP'] = str(int(time.time() * 1000))
        headers['X-Sign'] = _compute_sign(data if data else {})
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
    else:
        req = urllib.request.Request(url, headers=headers, method=method)
    resp = _urlopen(req, timeout=30, context=_ssl_ctx)
    return json.loads(resp.read().decode('utf-8'))


# ====== 字段 & 表单风格读取 ======

# 非数据控件：仅布局/装饰，不参与打印
NON_DATA_TYPES = {'card', 'grid', 'tabs', 'divider', 'alert', 'text', 'html',
                  'button', 'sub-table-design'}

# 子表/关联表单打印开关（config 可覆盖）
DEFAULT_INCLUDE_SUB = True


def _extract_fields(items, out):
    """递归提取主表数据控件，返回 [{fieldName(model), fieldText(title), type}]，
    跳过布局容器(card/grid/tabs)和子表(sub-table-design)。"""
    for item in items:
        t = item.get('type')
        if t == 'card' and 'list' in item:
            _extract_fields(item['list'], out)
        elif t in ('grid', 'tabs') and 'columns' in item:
            for col in item['columns']:
                _extract_fields(col.get('list', []), out)
        elif t == 'sub-table-design':
            continue  # 子表不进入主表字段（单独生成数据集）
        elif 'model' in item and t not in NON_DATA_TYPES:
            out.append({
                'fieldName': item['model'],
                'fieldText': item.get('name') or item.get('options', {}).get('label') or item['model'],
                'type': t,
            })


def _extract_sub_tables(items, out):
    """递归提取子表（sub-table-design），返回 [{name, model, fields:[{fieldName, fieldText, type}]}]"""
    for item in items:
        t = item.get('type')
        if t == 'card' and 'list' in item:
            _extract_sub_tables(item['list'], out)
        elif t in ('grid', 'tabs') and 'columns' in item:
            for col in item['columns']:
                _extract_sub_tables(col.get('list', []), out)
        elif t == 'sub-table-design':
            sub_fields = []
            for col in (item.get('columns') or []):
                for sw in (col.get('list') or []):
                    if sw.get('model'):
                        sub_fields.append({
                            'fieldName': sw['model'],
                            'fieldText': sw.get('name') or sw.get('options', {}).get('label') or sw['model'],
                            'type': sw.get('type', ''),
                        })
            out.append({
                'name': item.get('name', '明细清单'),
                'model': item.get('model', ''),
                'fields': sub_fields,
            })


def _extract_link_records(items, out):
    """递归提取关联记录（link-record），返回 [{name, model, sourceCode, showMode}]"""
    for item in items:
        t = item.get('type')
        if t == 'card' and 'list' in item:
            _extract_link_records(item['list'], out)
        elif t in ('grid', 'tabs') and 'columns' in item:
            for col in item['columns']:
                _extract_link_records(col.get('list', []), out)
        elif t == 'link-record':
            opts = item.get('options') or {}
            src = opts.get('sourceCode', '')
            if src:
                out.append({
                    'name': item.get('name', '关联记录'),
                    'model': item.get('model', ''),
                    'sourceCode': src,
                    'showMode': opts.get('showMode', 'many'),
                })


def resolve_form(code):
    """读取表单：返回 dict
    {form_name, form_style, form_id, fields, sub_tables, link_records}

    - fields:       主表数据字段 [{fieldName(model), fieldText(title), type}]
    - sub_tables:   子表（sub-table-design）列表 [{name, model, fields}]
    - link_records: 关联记录（link-record）列表 [{name, model, sourceCode}]
    """
    form_data = query_form(code)
    if not form_data:
        print(f'错误: 表单 {code} 不存在')
        sys.exit(1)
    form_name = form_data.get('desformName', code)
    form_id = form_data.get('id', '')
    raw = form_data.get('desformDesignJson', '{}')
    design = json.loads(raw) if isinstance(raw, str) else (raw or {})
    form_style = design.get('config', {}).get('formStyle', 'normal')

    fields = []
    sub_tables = []
    link_records = []
    _extract_fields(design.get('list', []), fields)
    _extract_sub_tables(design.get('list', []), sub_tables)
    _extract_link_records(design.get('list', []), link_records)
    return {
        'form_name': form_name, 'form_style': form_style, 'form_id': form_id,
        'fields': fields, 'sub_tables': sub_tables, 'link_records': link_records,
    }


def _resolve_other_form_fields(code):
    """读取其他 desform 表单（关联记录目标）的字段列表"""
    try:
        info = resolve_form(code)
        return info['fields']
    except SystemExit:
        return []


# ====== 报表模板构建 ======

def build_styles():
    """构建样式数组（与积木报表设计器一致的格式，索引含义见下）。"""
    border = {"bottom": ["thin", "#d8d8d8"], "top": ["thin", "#d8d8d8"],
              "left": ["thin", "#d8d8d8"], "right": ["thin", "#d8d8d8"]}
    return [
        {"border": border},                                                          # 0 边框
        {"border": border, "align": "center"},                                       # 1 边框+居中
        {"border": border, "align": "center", "valign": "middle"},                   # 2 边框+居中+垂直居中
        {"border": border, "align": "right", "valign": "middle",
         "bgcolor": "#F5F5F5", "font": {"bold": True}},                              # 3 标签(灰底+右对齐+加粗)
        {"border": border, "align": "center", "valign": "middle",
         "bgcolor": "#01b0f1", "color": "#ffffff"},                                  # 4 表头蓝底白字
        {"border": border, "align": "center", "valign": "middle",
         "font": {"bold": True, "size": 16}, "bgcolor": "#E6F2FF", "color": "#0066CC"},  # 5 标题(淡蓝底深蓝字)
        {"border": border, "align": "left", "valign": "middle"},                     # 6 值(左对齐)
        {"border": border, "align": "center", "valign": "middle",
         "font": {"bold": True, "size": 16}},                                        # 7 Word 标题(无底色)
        {"border": border, "align": "center", "valign": "middle",
         "bgcolor": "#F2F2F2", "font": {"bold": True}},                              # 8 Word 标签(浅灰底居中加粗)
    ]


def _bind(db_code, field_name):
    """desform 单值绑定：${dbCode.model}"""
    return f"${{{db_code}.{field_name}}}"


def build_card_layout(report_name, db_code, fields, title_style, label_style, value_style):
    """卡片式布局（标签-值对，每行2组共4列）。返回 (rows, merges)。"""
    rows = {}
    merges = []
    rows["1"] = {"cells": {"0": {"text": report_name, "style": title_style,
                                 "merge": [0, 3], "height": 45}}, "height": 45}
    merges.append("A2:D2")

    normal_fields = [f for f in fields if f.get('type') not in LONG_TEXT_TYPES]
    long_fields = [f for f in fields if f.get('type') in LONG_TEXT_TYPES]

    row_idx = 2
    for i in range(0, len(normal_fields), 2):
        f1 = normal_fields[i]
        cells = {
            "0": {"text": f1['fieldText'], "style": label_style},
            "1": {"text": _bind(db_code, f1['fieldName']), "style": value_style},
        }
        if i + 1 < len(normal_fields):
            f2 = normal_fields[i + 1]
            cells["2"] = {"text": f2['fieldText'], "style": label_style}
            cells["3"] = {"text": _bind(db_code, f2['fieldName']), "style": value_style}
        else:
            cells["2"] = {"text": "", "style": label_style}
            cells["3"] = {"text": "", "style": value_style}
        rows[str(row_idx)] = {"cells": cells, "height": 32}
        row_idx += 1

    for f in long_fields:
        rows[str(row_idx)] = {"cells": {
            "0": {"text": f['fieldText'], "style": label_style},
            "1": {"text": _bind(db_code, f['fieldName']), "style": value_style, "merge": [0, 2]},
        }, "height": 50}
        merges.append(f"B{row_idx + 1}:D{row_idx + 1}")
        row_idx += 1

    rows["len"] = 200
    return rows, merges


def build_report_template(report_name, db_code, fields, form_style):
    """按 form_style 选择布局，返回 (rows, cols, merges)。"""
    if form_style == 'word':
        # Word 风格：无底色标题(7) + 浅灰标签(8) + 左对齐值(6)
        rows, merges = build_card_layout(report_name, db_code, fields,
                                         title_style=7, label_style=8, value_style=6)
    else:
        # normal 风格：蓝底标题(5) + 灰底标签(3) + 左对齐值(6)
        rows, merges = build_card_layout(report_name, db_code, fields,
                                         title_style=5, label_style=3, value_style=6)
    cols = {"0": {"width": 110}, "1": {"width": 180},
            "2": {"width": 110}, "3": {"width": 180}, "len": 100}
    return rows, cols, merges


def _col_letter(idx):
    """列索引(0起) → Excel 列字母：0→A, 1→B, 25→Z, 26→AA"""
    s = ''
    idx += 1
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        s = chr(65 + rem) + s
    return s


def _list_bind(ds_code, field_name):
    """子表列表绑定：#{dsCode.model}（自动循环展开，无需 loopBlockList）"""
    return f"#{{{ds_code}.{field_name}}}"


def build_subtable_template(report_name, db_code, fields, form_style, sub_ds):
    """主子表布局：主表卡片区 + 每个子表/关联一个三段式区块。
    参考实测方案（2026-08-05，用户手动报表 + AI 复刻验证）：
    - 主表：标题行(merge A1:D1) + 字段行(标签 style2 + 值 style3)，每行 2 组共 4 列
    - 子表区块：标题行(style5, merge 全列) + 表头行(style4 蓝底) + 数据行(style0, #{dsCode.model} 列表绑定)
    - 区块间空一行；行号直接使用（参考报表行号 0/23/27/31 与 merges A1/A23/A27/A31 一致）
    """
    if form_style == 'word':
        title_style, label_style, value_style = 7, 8, 6
    else:
        title_style, label_style, value_style = 5, 3, 6

    rows = {}
    merges = []

    # 主表标题行（行 0，merge A1:D1）
    rows["0"] = {"cells": {"1": {"merge": [0, 3], "style": title_style, "text": report_name}}, "height": 57}
    merges.append("A1:D1")

    # 主表字段：每行 2 组（标签 + 值），从行 1 开始
    row_idx = 1
    for i in range(0, len(fields), 2):
        f1 = fields[i]
        cells = {
            "1": {"style": label_style, "text": f1['fieldText'] + ":"},
            "2": {"style": value_style, "text": _bind(db_code, f1['fieldName'])},
        }
        if i + 1 < len(fields):
            f2 = fields[i + 1]
            cells["3"] = {"style": label_style, "text": f2['fieldText'] + ":"}
            cells["4"] = {"style": value_style, "text": _bind(db_code, f2['fieldName'])}
        rows[str(row_idx)] = {"cells": cells, "height": 40}
        row_idx += 1

    # 子表区块
    for ds in sub_ds:
        ds_code = ds['ds_code']
        ds_fields = ds['fields']
        n = len(ds_fields)
        start = row_idx + 1  # 空一行再开始

        # 标题行（merge 全列）
        rows[str(start)] = {"cells": {"1": {"merge": [0, n - 1], "style": title_style,
                                            "text": ds['name']}}, "height": 57}
        col_last = _col_letter(n - 1)
        merges.append(f"A{start + 1}:{col_last}{start + 1}")

        # 表头行
        head_cells = {}
        for j, f in enumerate(ds_fields):
            head_cells[str(j + 1)] = {"style": 4, "text": f['fieldText']}
        rows[str(start + 1)] = {"cells": head_cells, "height": 40}

        # 数据行（列表绑定）
        data_cells = {}
        for j, f in enumerate(ds_fields):
            data_cells[str(j + 1)] = {"style": 0, "text": _list_bind(ds_code, f['fieldName'])}
        rows[str(start + 2)] = {"cells": data_cells, "height": 40}

        row_idx = start + 2

    rows["len"] = 200
    cols = {"0": {"width": 40}, "1": {"width": 120}, "2": {"width": 120},
            "3": {"width": 120}, "4": {"width": 120}, "len": 100}
    return rows, cols, merges


# ====== 核心流程 ======

def create_report(token, config):
    code = config['desformCode']
    db_code = config.get('dataCode', 'formmain')
    user_style = config.get('formStyle', 'auto')
    include_sub = config.get('includeSubTables', DEFAULT_INCLUDE_SUB)

    print('[准备] 读取表单字段与风格 ...')
    info = resolve_form(code)
    form_name, form_style = info['form_name'], info['form_style']
    form_id = info['form_id']
    if user_style != 'auto':
        form_style = user_style
    report_name = config.get('reportName', f'{form_name}打印')

    fields = info['fields']
    sub_tables = info['sub_tables']
    link_records = info['link_records']
    if config.get('fields'):
        fields = [{'fieldName': f['fieldName'], 'fieldText': f.get('fieldText', f['fieldName']),
                   'type': f.get('type', '')} for f in config['fields']]
    if not fields:
        print('错误: 表单无可打印字段，请在配置中手动提供 fields')
        sys.exit(1)
    print(f'  表单: {form_name}  风格: {form_style}  主表字段: {len(fields)}'
          f'  子表: {len(sub_tables)}  关联: {len(link_records)}')

    # ===== Step 1: 创建空报表 =====
    print('\n[Step 1/5] 创建空报表 ...')
    r = _jm_request(token, '/jmreport/save', {
        "id": "", "code": "", "name": report_name, "type": JM_REPORT_TYPE, "template": 0})
    if not r.get('success'):
        print(f'  失败: {r.get("message")}'); sys.exit(1)
    res = r.get('result')
    report_id = res.get('id') if isinstance(res, dict) else str(res)
    if not report_id:
        print('  失败: 未返回 reportId'); sys.exit(1)
    print(f'  reportId={report_id}')

    # ===== Step 2: 保存 API 数据源（主表 + 子表 + 关联，desform API v2） =====
    print('\n[Step 2/5] 保存 API 数据源 ...')
    data_base = f"{{{{ domainURL }}}}/desform/api/v2/data/{form_id}"

    def _save_ds(db_code, db_name, api_url, ds_fields, params):
        field_list = [{
            "fieldName": f['fieldName'], "fieldText": f['fieldText'],
            "widgetType": "String", "orderNum": i, "tableIndex": i + 1,
            "extJson": "", "dictCode": "",
        } for i, f in enumerate(ds_fields)]
        save_db = {
            "izSharedSource": 0, "jimuReportId": report_id,
            "dbCode": db_code, "dbChName": db_name,
            "dbType": "1", "dbSource": "", "jsonData": "", "apiConvert": "",
            "jimuSharedSourceId": None, "apiUrl": api_url, "apiMethod": "0",
            "isList": "1", "isPage": "0", "dbDynSql": "",
            "fieldList": field_list, "paramList": params,
        }
        r = _jm_request(token, '/jmreport/saveDb', save_db)
        if not r.get('success'):
            print(f'  失败 [{db_code}]: {r.get("message")}')
            print(f'  API: {api_url}')
            sys.exit(1)
        print(f'  {db_code} ({len(ds_fields)} 字段) -> success=True')

    id_params = [
        {"paramName": "id", "orderNum": 1, "tableIndex": 1, "id": "",
         "paramValue": "", "extJson": "", "dictCode": "", "_index": 0, "_rowKey": 30},
    ]
    token_params = id_params + [
        {"paramName": "token", "orderNum": 2, "tableIndex": 2, "id": "",
         "paramValue": "", "extJson": "", "dictCode": "", "_index": 1, "_rowKey": 31},
    ]

    # 主表
    _save_ds(db_code, report_name,
             f'{data_base}/queryById?id=${{id}}&token=${{token}}',
             fields, token_params)

    # 子表 + 关联（使用 API v2 独立数据集，列表绑定 #{} 自动循环）
    sub_ds = []  # [{ds_code, name, fields}]
    if include_sub:
        for st in sub_tables:
            if not st.get('model'):
                continue
            ds_code = f"gen_{st['model'].split('_')[-1]}sub"
            sub_ds.append({'ds_code': ds_code, 'name': st['name'], 'fields': st['fields']})
            _save_ds(ds_code, st['name'],
                     f'{data_base}/{st["model"]}/queryById?id=${{id}}',
                     st['fields'], id_params)
        seen_src = set()
        for lr in link_records:
            # 单条记录关联（showMode=single）作为主表字段，不生成子表（规则 @2026-08-05）
            if lr.get('showMode') == 'single':
                continue
            src = lr.get('sourceCode', '')
            if not src or src in seen_src:
                continue
            seen_src.add(src)
            lr_fields = _resolve_other_form_fields(src)
            if not lr_fields:
                print(f'  [警告] 关联表单 {src} 无字段，跳过')
                continue
            ds_code = src.replace('demo_', '') + 'sub'
            sub_ds.append({'ds_code': ds_code, 'name': lr['name'], 'fields': lr_fields})
            _save_ds(ds_code, lr['name'],
                     f'{data_base}/{src}/queryById?id=${{id}}',
                     lr_fields, id_params)

    # ===== Step 3: 构造模板 =====
    print('\n[Step 3/5] 构造报表模板 ...')
    styles = build_styles()
    if sub_ds:
        rows, cols, merges = build_subtable_template(report_name, db_code, fields, form_style, sub_ds)
    else:
        rows, cols, merges = build_report_template(report_name, db_code, fields, form_style)
    print(f'  {len([k for k in rows if k != "len"])} 行, {len(merges)} 个合并')

    # ===== Step 4: 保存完整设计 =====
    print('\n[Step 4/5] 保存完整报表设计 ...')
    designer_obj = {
        "id": report_id, "name": report_name, "type": JM_REPORT_TYPE,
        "template": 0, "delFlag": 0, "submitForm": 0, "reportName": report_name,
    }
    save_data = {
        "designerObj": json.dumps(designer_obj, ensure_ascii=False),
        "name": "sheet1", "freeze": "A1", "freezeLineColor": "rgb(185, 185, 185)",
        "rows": rows, "cols": cols, "styles": styles, "merges": merges,
        "validations": [], "autofilter": {}, "dbexps": [], "dicts": [],
        "loopBlockList": [], "zonedEditionList": [],
        "fixedPrintHeadRows": [], "fixedPrintTailRows": [],
        "rpbar": {"show": True, "pageSize": "", "btnList": []},
        "hiddenCells": [],
        "hidden": {"rows": [], "cols": [], "conditions": {"rows": {}, "cols": {}}},
        "recordSubTableOrCollection": {"group": [], "record": [], "range": []},
        "displayConfig": {},
        "printConfig": {"paper": "A4", "width": 210, "height": 297, "definition": 1,
                        "isBackend": False, "marginX": 10, "marginY": 10,
                        "layout": "portrait", "printCallBackUrl": ""},
        "querySetting": {"izOpenQueryBar": False, "izDefaultQuery": True},
        "queryFormSetting": {"useQueryForm": False, "dbKey": "", "idField": ""},
        "area": {"sri": 0, "sci": 0, "eri": 0, "eci": 0, "width": 100, "height": 25},
        "submitHandlers": [], "chartList": [],
        "background": False, "dataRectWidth": 580,
        "excel_config_id": report_id, "pyGroupEngine": False,
        "isViewContentHorizontalCenter": False, "fillFormStyle": "default",
        "sheetId": "default", "sheetName": "默认Sheet", "sheetOrder": "0",
    }
    r = _jm_request(token, '/jmreport/save', save_data)
    if not r.get('success'):
        print(f'  失败: {r.get("message")}'); sys.exit(1)
    print('  success=True')

    # ===== Step 5: 回写表单 allowJmReport / jmReportURL =====
    print('\n[Step 5/5] 关联到 desform 表单打印 ...')
    report_url = "{{sysBasePath}}/jmreport/view/" + report_id
    update_design_config(code, {"allowJmReport": True, "jmReportURL": report_url})
    print(f'  allowJmReport=True, jmReportURL={report_url}')

    base = (_JM_BASE or get_api_base()).rstrip('/')
    print('\n' + '=' * 56)
    print('全部完成!')
    print('=' * 56)
    print(f'  报表名称  : {report_name}')
    print(f'  reportId  : {report_id}')
    print(f'  数据集编码: {db_code}')
    print(f'  字段数量  : {len(fields)}  风格: {form_style}')
    print(f'  关联表单  : {code}')
    print(f'  设计器    : {base}/jmreport/index/{report_id}')
    print(f'  预览      : {base}/jmreport/view/{report_id}?id=<数据ID>&token=<token>')
    print('=' * 56)
    print('提示: 打印入口在 desform 表单详情页右上角打印图标。')


def delete_report(token, config):
    report_id = config.get('reportId', '')
    if not report_id:
        print('错误: delete_report 需要 reportId'); sys.exit(1)
    print(f'[Step 1/2] 删除报表 {report_id} ...')
    try:
        r = _jm_request(token, f'/jmreport/delete?id={report_id}', method='DELETE')
        print('  删除成功' if r.get('success') else f'  删除失败: {r.get("message")}')
    except Exception as e:
        print(f'  删除异常: {e}')

    code = config.get('desformCode')
    if code:
        print('[Step 2/2] 清除表单打印关联 ...')
        try:
            update_design_config(code, {"allowJmReport": False, "jmReportURL": ""})
            print('  已清除 allowJmReport / jmReportURL')
        except Exception as e:
            print(f'  清除失败: {e}')
    else:
        print('[Step 2/2] 未提供 desformCode，跳过清除表单关联')
    print('\n报表删除完成!')


def main():
    global _JM_BASE
    p = argparse.ArgumentParser(description='desform - 积木报表集成工具')
    p.add_argument('--api-base', required=True, help='desform 接口地址（如 http://host:3100/jeecgboot）')
    p.add_argument('--jmreport-base', default=None,
                   help='积木报表接口地址（如 http://host:8080/jeecg-boot），缺省时与 --api-base 相同')
    p.add_argument('--token', required=True)
    p.add_argument('--config', required=True)
    args = p.parse_args()

    init_api(args.api_base, args.token)
    _JM_BASE = args.jmreport_base or args.api_base
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    action = config.get('action', 'create_report')
    if action == 'create_report':
        create_report(args.token, config)
    elif action == 'delete_report':
        delete_report(args.token, config)
    else:
        print(f'未知操作类型: {action}'); sys.exit(1)


if __name__ == '__main__':
    main()
