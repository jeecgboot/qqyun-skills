"""
JeecgBoot 表单设计器（desform）通用工具库
==========================================
提供 API 调用、控件工厂、表单组装、菜单SQL生成等共通功能。

使用示例:
    from desform_utils import *
    init_api('<api_base>', '<token>')
    form_id, uc = find_or_create_form('Customer Info', 'customer_info')
    widgets = [
        INPUT('客户名称', required=True),
        PHONE('电话'),
        SELECT('类型', options=['企业', '个人']),
    ]
    save_design(form_id, 'customer_info', widgets, title_index=0, update_count=uc)
"""

import urllib.request
import urllib.parse
import json
import time
import random
import ssl
import uuid
import sys

# Windows 控制台中文乱码修复：强制 UTF-8 输出
if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# ============================================================
# 全局配置
# ============================================================
_API_BASE = ''
_TOKEN = ''
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

# lowApp 模式上下文（由 desform_lowapp_utils.init_lowapp 注入）
_TENANT_ID = '1'      # X-Tenant-Id，默认 '1'（普通模式）
_LOW_APP_ID = None    # x-low-app-id，None 表示普通模式

# 固定角色ID（用于授权SQL）
ROLE_ID = 'f6817f48af4fb3af11b9e8bf182f618b'

# 表单缓存: {code: {'id': str, 'uc': int}}
_FORM_CACHE = {}


def clear_cache():
    """清空 Python 内存缓存"""
    global _FORM_CACHE
    _FORM_CACHE = {}


def init_api(api_base, token):
    """初始化 API 地址和 Token"""
    global _API_BASE, _TOKEN
    _API_BASE = api_base.rstrip('/')
    _TOKEN = token


# ============================================================
# API 请求
# ============================================================
def get_headers():
    """返回当前请求头字典（供外部直接使用 requests 库时调用）"""
    h = {
        'X-Access-Token': _TOKEN,
        'X-Sign': '00000000000000000000000000000000',
        'X-Tenant-Id': _TENANT_ID,
        'X-Timestamp': str(int(time.time() * 1000)),
        'Content-Type': 'application/json; charset=UTF-8',
    }
    if _LOW_APP_ID:
        h['x-low-app-id'] = _LOW_APP_ID
    return h


def get_api_base():
    """返回当前 API 基础地址"""
    return _API_BASE


def _is_loopback_host(hostname):
    if not hostname:
        return False
    host = hostname.lower().strip('[]')
    return host in ('127.0.0.1', 'localhost', '::1') or host.endswith('.localhost')


def _urlopen(req, timeout=None, context=None):
    """urlopen；loopback 强制直连，避免 http_proxy/Clash 把 127.0.0.1 打成 502。"""
    ctx = _SSL_CTX if context is None else context
    host = urllib.parse.urlparse(req.full_url).hostname
    if _is_loopback_host(host):
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPHandler(),
            urllib.request.HTTPSHandler(context=ctx),
        )
        return opener.open(req, timeout=timeout)
    kwargs = {'context': ctx}
    if timeout is not None:
        kwargs['timeout'] = timeout
    return urllib.request.urlopen(req, **kwargs)


def api_request(path, data=None, method='POST', params=None):
    """发送 API 请求，返回 JSON 响应。
    params: dict，用于 GET 请求的 URL 查询参数（如 {'code': 'student_form'}）
    """
    url = f'{_API_BASE}{path}'
    if params:
        url = f'{url}?{urllib.parse.urlencode(params)}'
    headers = get_headers()
    if data is not None:
        json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(url, data=json_data, headers=headers, method=method)
    else:
        req = urllib.request.Request(url, headers=headers, method=method)
    resp = _urlopen(req)
    return json.loads(resp.read().decode('utf-8'))


# ============================================================
# 字典查询
# ============================================================
def query_dict(dict_code):
    """查询字典项列表，返回 [{value, text, label, ...}, ...]

    用法: query_dict('sex') → [{'value': '1', 'text': '男'}, {'value': '2', 'text': '女'}]
    """
    r = api_request(f'/sys/dict/getDictItems/{dict_code}', method='GET')
    if r.get('success') and r.get('result'):
        return r['result']
    return []


def search_dict(keyword):
    """通过关键词模糊搜索字典编码，返回匹配的字典列表 [{id, dictCode, dictName, ...}, ...]

    用法: search_dict('性别') → [{'dictCode': 'sex', 'dictName': '性别', ...}]
          search_dict('sex')  → [{'dictCode': 'sex', 'dictName': '性别', ...}]
    """
    r = api_request(f'/sys/dict/list?pageNo=1&pageSize=200&dictName={keyword}', method='GET')
    results = []
    if r.get('success') and r.get('result'):
        records = r['result'].get('records', [])
        results.extend(records)
    # 也按 dictCode 搜索
    r2 = api_request(f'/sys/dict/list?pageNo=1&pageSize=200&dictCode={keyword}', method='GET')
    if r2.get('success') and r2.get('result'):
        seen_ids = {rec['id'] for rec in results}
        for rec in r2['result'].get('records', []):
            if rec['id'] not in seen_ids:
                results.append(rec)
    return results


# ============================================================
# 编码唯一性检查
# ============================================================
def check_code_available(code):
    """检查表单编码是否可用（数据库级唯一性校验）

    调用 GET /sys/duplicate/check 接口检查 design_form 表中 desform_code 是否已存在。

    Args:
        code: 表单编码

    Returns:
        True 表示可用，False 表示已存在
    """
    r = api_request(
        f'/sys/duplicate/check?tableName=design_form&fieldName=desform_code&fieldVal={code}',
        method='GET'
    )
    return r.get('success', False)


# ============================================================
# 表单缓存 & 查找
# ============================================================
def _cache_put(code, form_id, uc=0):
    """写入缓存"""
    _FORM_CACHE[code] = {'id': form_id, 'uc': uc}


def _cache_get(code):
    """读取缓存，返回 (id, uc) 或 (None, None)"""
    c = _FORM_CACHE.get(code)
    if c:
        return c['id'], c['uc']
    return None, None


def _cache_remove(code):
    """清除缓存"""
    _FORM_CACHE.pop(code, None)


def _find_by_list(code):
    """通过 list API 全量搜索 + 精确匹配 desformCode 查找表单（按创建时间倒序，取最新的）"""
    page = 1
    while page <= 10:
        r = api_request(f'/desform/list?pageNo={page}&pageSize=100&column=createTime&order=desc', method='GET')
        if not r.get('success') or not r.get('result'):
            break
        records = r['result'].get('records', [])
        if not records:
            break
        for rec in records:
            if rec.get('desformCode') == code:
                fid, uc = rec['id'], rec.get('updateCount', 0)
                _cache_put(code, fid, uc)
                return fid, uc
        total = r['result'].get('total', 0)
        if page * 100 >= total:
            break
        page += 1
    return None, None


def _verify_form_exists(form_id):
    """验证表单 ID 是否真实存在（通过 list API 验证，不走缓存）"""
    try:
        # list API 不走 Redis 缓存，结果可靠
        page = 1
        while page <= 5:
            r = api_request(f'/desform/list?pageNo={page}&pageSize=100&column=createTime&order=desc', method='GET')
            if not r.get('success') or not r.get('result'):
                return False
            for rec in r['result'].get('records', []):
                if rec.get('id') == form_id:
                    return True
            total = r['result'].get('total', 0)
            if page * 100 >= total:
                break
            page += 1
        return False
    except Exception:
        return False


def get_form_id(code):
    """通过表单编码获取表单 ID（带缓存），返回 (form_id, update_count) 或 (None, None)

    查找顺序: 缓存 → queryByCode(带验证) → list 全量搜索
    """
    # 1. 缓存（已验证过的）
    fid, uc = _cache_get(code)
    if fid:
        return fid, uc

    # 2. queryByCode（需要验证，该接口有服务端缓存可能返回已删除的幽灵记录）
    try:
        r = api_request(f'/desform/queryByCode?desformCode={code}', method='GET')
        if r.get('success') and r.get('result') and r['result'].get('id'):
            fid = r['result']['id']
            uc = r['result'].get('updateCount', 0)
            # 验证 ID 是否真实存在
            if _verify_form_exists(fid):
                _cache_put(code, fid, uc)
                return fid, uc
            # 幽灵记录，跳过
    except Exception:
        pass

    # 3. list 全量搜索（list 结果比较可靠）
    return _find_by_list(code)


def find_or_create_form(name, code, app_menu_group_id=None):
    """查找或创建表单，返回 (form_id, update_count, code)

    策略：先 add → 成功则查找 ID；add 失败(code已存在)则查找已有表单。
    结果自动缓存。

    Args:
        app_menu_group_id: lowApp 模式下的工作表分组ID（可选）
    """
    # 1. 尝试创建
    try:
        body = {'desformName': name, 'desformCode': code}
        if app_menu_group_id is not None:
            body['appMenuGroupId'] = app_menu_group_id
        add_r = api_request('/desform/add', body)
        if add_r.get('success'):
            # add 成功，优先从返回值获取 ID
            if add_r.get('result') and add_r['result'].get('id'):
                fid = add_r['result']['id']
                _cache_put(code, fid, 0)
                return fid, 0, code
            # 旧版后端不返回 ID，通过 list 搜索
            for wait in [2, 2, 3]:
                time.sleep(wait)
                fid, uc = _find_by_list(code)
                if fid:
                    _cache_put(code, fid, uc)
                    return fid, uc, code
    except Exception:
        pass

    # 3. add 失败(code已存在)，查找已有表单直接使用
    fid, uc = get_form_id(code)
    if fid:
        return fid, uc, code

    raise RuntimeError(f'无法查找或创建表单: {code}')


def get_form_fields(form_code):
    """查询已有表单的字段信息，返回 (titleField_model, {name: {model, key, type}})

    字段中文名在整张表里不唯一（设计子表列常与主表同名）。同名直接覆盖会让
    `fields['数字']` 指向子表列 model，主表写入/改字段全部写错。

    规则：
    - 主表字段：key = 中文名（`fields['数字']`）
    - 子表列：key = `{子表名}.{列名}`（`fields['设计子表.数字']`），并带 `parent`
    - 仍冲突时：追加 `#{model}`，绝不覆盖已有项
    """
    # 优先使用缓存获取 ID
    fid, _ = get_form_id(form_code)
    q = None
    if fid:
        q = api_request(f'/desform/queryById?id={fid}', method='GET')
    if not q or not q.get('success') or not q.get('result') or not q['result'].get('desformDesignJson'):
        # fallback: queryByCode
        q = api_request(f'/desform/queryByCode?desformCode={form_code}', method='GET')
        if not q.get('success') or not q.get('result') or not q['result'].get('desformDesignJson'):
            raise RuntimeError(f'表单 {form_code} 未找到或无设计数据')
    design = json.loads(q['result']['desformDesignJson'])
    title_field = design['config']['titleField']
    fields = {}

    def _put(name, info, parent_name=None):
        model = info.get('model') or ''
        key = f'{parent_name}.{name}' if parent_name else name
        if not key:
            key = model
        if key in fields:
            key = f'{key}#{model}'
        if parent_name:
            info = dict(info)
            info['parent'] = parent_name
        fields[key] = info

    def extract(items, parent_name=None):
        for item in items or []:
            t = item.get('type')
            name = item.get('name') or ''
            if t == 'card':
                extract(item.get('list', []), parent_name)
            elif t == 'grid':
                for col in item.get('columns') or item.get('cols') or []:
                    extract(col.get('list', []), parent_name)
            elif t == 'tabs':
                for pane in item.get('panes') or item.get('list') or []:
                    extract(pane.get('list', []), parent_name)
            elif t == 'sub-table-design':
                if item.get('model'):
                    _put(name, {
                        'model': item['model'],
                        'key': item.get('key'),
                        'type': t,
                    }, parent_name)
                for col in item.get('columns', []):
                    extract(col.get('list', []), parent_name=name)
            elif item.get('model') and t not in ('card',):
                _put(name, {
                    'model': item['model'],
                    'key': item.get('key'),
                    'type': t,
                }, parent_name)

    extract(design.get('list', []))
    return title_field, fields


def _model_to_key(design, model):
    """从 desformDesignJson 的 list 中，根据 model 找到对应控件的 key。"""
    def search(items):
        for item in items:
            if item.get('model') == model:
                return item.get('key', '')
            if item.get('type') == 'card' and 'list' in item:
                r = search(item['list'])
                if r:
                    return r
        return ''
    return search(design.get('list', []))


def _get_title_model(code):
    """获取表单标题字段的 model（日历、甘特图视图使用）。

    直接返回 config.titleField 中存储的 model 字符串。
    若 config.titleField 为空则抛出 ValueError。
    """
    form_data = query_form(code)
    if not form_data:
        raise ValueError(f'表单 {code} 不存在，无法获取 titleField')
    design_str = form_data.get('desformDesignJson', '{}')
    design = json.loads(design_str) if isinstance(design_str, str) else design_str
    title_model = design.get('config', {}).get('titleField', '')
    if not title_model:
        raise ValueError(f'表单 {code} 未设置 titleField，请手动传入 title_field 参数')
    return title_model


def _get_title_key(code):
    """获取表单标题字段的 key（看板视图专用，其他视图用 _get_title_model）。

    从 config.titleField（存储的是 model）解析出对应控件的 key。
    若 config.titleField 为空则抛出 ValueError。
    """
    form_data = query_form(code)
    if not form_data:
        raise ValueError(f'表单 {code} 不存在，无法获取 titleField')
    design_str = form_data.get('desformDesignJson', '{}')
    design = json.loads(design_str) if isinstance(design_str, str) else design_str
    title_model = design.get('config', {}).get('titleField', '')
    if not title_model:
        raise ValueError(f'表单 {code} 未设置 titleField，请手动传入 title_field 参数')
    key = _model_to_key(design, title_model)
    return key if key else title_model  # 找不到 key 时降级返回 model


# ============================================================
# ID 生成
# ============================================================
def _gen_key():
    ts = int(time.time() * 1000)
    rnd = random.randint(100000, 999999)
    return f"{ts}_{rnd}"


def _gen_model(widget_type):
    ts = int(time.time() * 1000)
    rnd = random.randint(100000, 999999)
    safe = widget_type.replace('-', '_')
    return f"{safe}_{ts}_{rnd}"


def _sleep():
    time.sleep(0.003)


# ============================================================
# 控件核心工厂
# ============================================================
def _adv(fmt='string', custom=False, split=''):
    return {
        "defaultValue": {
            "type": "compose", "value": "", "format": fmt,
            "allowFunc": True, "valueSplit": split, "customConfig": custom
        }
    }

# ---- make_widget 的 options 级合法参数白名单 ----
_VALID_OPTIONS_KWARGS = {
    'fieldNote', 'hidden', 'hiddenOnAdd', 'disabled', 'placeholder',
    'unique', 'readonly', 'inline', 'showLabel', 'useColor',
    'filterable', 'clearable', 'precision', 'allowHalf',
    'allowScan', 'scanEditable',
}

# 敲敲云（lowApp）设计器左侧面板不展示的控件（Container.vue QQYUN-3641 / OA 整组）
# 本 skill 禁止新建这些类型；读已有表单时工厂仍保留。
LOWAPP_DISABLED_WIDGET_TYPES = frozenset({
    'table-dict', 'select-tree', 'cascader', 'category-linkage',
    'oa-approval-comments', 'x_oa_timeout_date', 'x_oa_official_doc_no',
    'oa-sign-holiday-select', 'oa-leave-date-select', 'oa-sign-patch-select',
})

# 前端 componentsConfig.js（2026-09-03 对照）中带 advancedSetting 的控件白名单。
# UI 拖拽只按组件定义生成该块；此前对所有类型统一注入，导致 editor/markdown/upload/
# 地图/定位/公式/条码/文本/org-role 等与 UI 结构不一致（UI 保存重建 options、默认值双源冲突）。
# link-field 刻意不加：其默认值由他表字段联动单独管理（源码虽有该块，行为需另验证）。
_WITH_ADV_SETTING = frozenset({
    'input', 'textarea', 'number', 'integer', 'money',
    'radio', 'checkbox', 'date', 'select', 'switch', 'slider',
    'phone', 'email',
    'select-user', 'select-depart', 'select-depart-post',
    'link-record',
})

# 日期显示类型 → designType / 默认 format（源码 WidgetConfigMixins.onDateTypeChange）
# 敲敲云不提供 daterange / dates / datetimerange（仅普通设计器兼容老数据）
_DATE_TYPE_META = {
    'year':        {'designType': 'date',     'format': 'yyyy'},
    'month':       {'designType': 'date',     'format': 'yyyy-MM'},
    'quarter':     {'designType': 'date',     'format': 'yyyy-[Q]Q', 'format_locked': True, 'timestamp': True},
    'week':        {'designType': 'date',     'format': 'yyyy-WW周', 'format_locked': True},
    'date':        {'designType': 'date',     'format': 'yyyy-MM-dd'},
    'datetime_s':  {'designType': 'datetime', 'format': 'yyyy-MM-dd HH'},
    'datetime_sf': {'designType': 'datetime', 'format': 'yyyy-MM-dd HH:mm'},
    'datetime':    {'designType': 'datetime', 'format': 'yyyy-MM-dd HH:mm:ss'},
}

def make_widget(widget_type, name, class_name, icon, options,
                required=False, is_sub=False, parent_key=None, extra=None,
                mobile_options=None, model=None, remote_api=None, default_expr=None,
                **kwargs):
    """创建控件（通用工厂），返回 (widget_dict, key, model)

    Args:
        model: 可选，预分配的 model（用于 table-dict popup 等需要提前知晓自身 model 的场景）
        mobile_options: 移动端覆盖配置（widget 顶层属性），移动端渲染时 merge 到 options。
            例如 radio/checkbox: {"inline": True, "matrixWidth": 120}
            例如 date/time: {"editable": False}
        remote_api: 可选，远程取值接口地址。支持绝对地址（http(s)://...）或相对地址（/开头）。
            URL 中可使用 {{上下文变量}} 和 ${表单字段model} 动态传参。
            例如: '/desform/api/getName?userId={{sysUserCode}}&name=${input_xxx}'
        default_expr: 可选，默认值表达式（compose 类型）。支持上下文变量 {{varName}} 和字段引用 $fieldModel$。
            例如: '{{sysUserCode}}'、'{{sysDate}} {{sysTime}}'、'前缀-$input_xxx$'
            对 text 组件无效（text 组件通过 options.text 设置内容）。
    """
    key = _gen_key()
    model = model or _gen_model(widget_type)
    _sleep()

    # 合并透传的 options 级参数（白名单校验，防 AI 杜撰参数静默写入）
    if kwargs:
        unknown = set(kwargs) - _VALID_OPTIONS_KWARGS
        if unknown:
            print(f'  ⚠ [警告] make_widget("{name}") 收到非白名单参数: {sorted(unknown)}，已忽略')
        for k, v in kwargs.items():
            if k in _VALID_OPTIONS_KWARGS:
                options[k] = v

    fmt = "number" if widget_type in ("number", "integer", "money", "slider") else "string"
    custom = widget_type in ("radio", "checkbox", "select", "link-record", "sub-table-design")
    # select-user/depart/depart-post 需要 valueSplit=',' 但 customConfig=False
    needs_split = custom or widget_type in ("select-user", "select-depart", "select-depart-post")
    split = "," if needs_split else ""

    w = {
        "type": widget_type, "name": name,
        "className": class_name, "icon": icon,
        "hideTitle": False, "options": options,
        "remoteAPI": {"url": remote_api or "", "executed": False},
        "key": key, "model": model, "modelType": "main",
        "rules": [{"required": True, "message": "${title}必须填写"}] if required else [],
        "isSubItem": is_sub
    }

    if mobile_options:
        w["mobileOptions"] = mobile_options

    if widget_type in _WITH_ADV_SETTING:
        w["advancedSetting"] = _adv(fmt, custom, split)
        if default_expr is not None:
            w["advancedSetting"]["defaultValue"]["value"] = default_expr
    elif default_expr is not None:
        print(f'  ⚠ [警告] make_widget("{name}") 类型 {widget_type} 在 UI 定义中无 advancedSetting，default_expr 已忽略')

    if is_sub and parent_key:
        w["subOptions"] = {"width": "200px", "parentKey": parent_key}

    if extra:
        w.update(extra)

    return w, key, model


# ============================================================
# Card 容器
# ============================================================
def make_card(*widgets):
    """创建 card 容器，包裹 1~4 个控件"""
    key = _gen_key()
    _sleep()
    return {
        "key": key, "type": "card", "isAutoGrid": True,
        "isContainer": True, "list": list(widgets),
        "options": {}, "model": f"card_{key}"
    }


def CARD(*widgets, width='100%', row_num=1):
    """卡片容器控件（不需要外层 card 包裹）

    Card 是 AutoGrid 布局之外的独立容器，可容纳多个子控件。
    普通控件自动包裹在 AutoGrid card 中，但 CARD() 创建的是
    显式的非 AutoGrid 卡片容器。

    Args:
        widgets: 子控件的 (widget_dict, key, model) tuple 或裸 widget dict
        width: 卡片宽度，默认 '100%'
        row_num: 每行控件数，默认 1

    Returns:
        (widget_dict, key, model)

    用法:
        input_w, _, _ = INPUT('姓名', wrap=False)
        phone_w, _, _ = PHONE('手机', wrap=False)
        card_w, card_k, card_m = CARD(input_w, phone_w, row_num=2)
    """
    key = _gen_key()
    _sleep()
    child_list = []
    for item in widgets:
        if isinstance(item, tuple):
            child_list.append(item[0])
        else:
            child_list.append(item)
    w = {
        "type": "card", "name": "卡片",
        "className": "form-card", "icon": "icon-card",
        "hideTitle": False, "hideLabel": True,
        "isContainer": True,
        "list": child_list,
        "options": {
            "width": width, "rowNum": row_num, "hidden": False,
        },
        "key": key, "model": f"card_{key}",
    }
    return w, key, w["model"]


def GRID(columns, gutter=8, justify='start', align='top',
         is_word_style=False):
    """栅格布局控件（不需要 card 包裹）

    Grid 是 12 列栅格系统，用于精确控制列宽和多列布局。

    Args:
        columns: 列定义列表，每项为 dict: {"span": 12, "list": [widget...]}
            或简写为 (span, [widget_list]) tuple
        gutter: 列间距（px），默认 8
        justify: 水平对齐 'start'|'center'|'end'|'space-between'|'space-around'
        align: 垂直对齐 'top'|'middle'|'bottom'
        is_word_style: 是否为 Word 风格栅格

    Returns:
        (widget_dict, key, model)

    用法:
        input_w, _, _ = INPUT('姓名', wrap=False)
        phone_w, _, _ = PHONE('手机', wrap=False)
        grid_w, grid_k, grid_m = GRID([
            {"span": 12, "list": [input_w]},
            {"span": 12, "list": [phone_w]},
        ])
        # 或简写：
        grid_w, grid_k, grid_m = GRID([
            (12, [input_w]),
            (12, [phone_w]),
        ])
    """
    key = _gen_key()
    _sleep()
    cols = []
    for col in columns:
        if isinstance(col, tuple):
            span, col_list = col
            cols.append({
                "span": span,
                "options": {
                    "flex": False,
                    "flexAlignItems": "flex-start",
                    "flexJustifyContent": "start",
                },
                "list": [w[0] if isinstance(w, tuple) else w for w in col_list],
            })
        elif isinstance(col, dict):
            # 确保 list 中的 tuple 被解包
            col_list = col.get("list", [])
            col["list"] = [w[0] if isinstance(w, tuple) else w for w in col_list]
            if "options" not in col:
                col["options"] = {
                    "flex": False,
                    "flexAlignItems": "flex-start",
                    "flexJustifyContent": "start",
                }
            cols.append(col)
    class_name = "form-grid form-grid-word-theme" if is_word_style else "form-grid"
    w = {
        "type": "grid", "name": "栅格布局",
        "className": class_name, "icon": "icon-grid",
        "hideTitle": False, "hideLabel": True,
        "isContainer": True,
        "columns": cols,
        "options": {
            "isWordStyle": is_word_style,
            "gutter": gutter, "justify": justify, "align": align,
            "hidden": False,
        },
        "key": key, "model": f"grid_{key}",
        "rules": [], "modelType": "main",
    }
    return w, key, w["model"]


def SUMMARY(name, sub_table_model, field_model, summary_type='inner-sum',
            width=100, filter=None, *, wrap=True):
    """汇总控件 — 对子表某列进行汇总计算（只能在主表使用，不能在子表内使用）。

    用于替代 FORMULA(mode='SUM') 来汇总子表列数据（FORMULA 的 SUM 模式只能汇总主表字段）。

    Args:
        name: 控件名称，如 '合计金额'
        sub_table_model: 子表的 model，如 'sub_table_design_xxx'
        field_model: 要汇总的子表列 model，如 'formula_xxx'（预估金额列）
        summary_type: 汇总方式，'inner-sum'(求和), 'inner-average'(平均), 'inner-max'(最大), 'inner-min'(最小),
                      'inner-record-count'(记录数), 'inner-completed-count'(已填计数), 'inner-incompletely-count'(未填计数),
                      'inner-date-earliest'(最早日期), 'inner-date-latest'(最晚日期)
        filter: 过滤条件，如 {"enabled": True, "matchType": "AND", "rules": [...]}
        wrap: 是否包裹 AutoGrid card（默认 True）

    用法:
        sub_table, sub_key = make_sub_table('明细', [])
        sub_amount = SUB_PRODUCT('金额', sub_key, [price_model, qty_model])
        # ... 组装子表 ...
        total = SUMMARY('合计金额', sub_table['model'], sub_amount[2])
    """
    key = _gen_key()
    model = _gen_model("summary")
    _sleep()
    default_filter = {"enabled": False, "rules": [], "matchType": "AND"}
    w = {
        "type": "summary", "name": name,
        "className": "form-summary", "icon": "icon-sigma",
        "hideTitle": False,
        "options": {
            "linkTable": sub_table_model,
            "field": field_model,
            "summary": summary_type,
            "filter": filter if filter else default_filter,
            "hidden": False, "hiddenOnAdd": False, "required": False, "fieldNote": "",
            "autoWidth": width,
        },
        "key": key, "model": model, "modelType": "main",
        "rules": [], "isSubItem": False
    }
    if wrap:
        return _card_wrap(w, key, model)
    return w, key, model


def SUMMARY_DATE(name, sub_table_model, field_model, summary_type='inner-date-earliest',
                 date_type='date', fmt='yyyy-MM-dd', filter=None, *, wrap=True):
    """汇总日期控件 — 对子表日期列做最早/最晚聚合（只能在主表使用，不能在子表内使用）。

    这是 type="date" + isSummary=true 的特殊控件，内部通过 __summary__date 前缀注册以区分普通日期选择器。

    Args:
        name: 控件名称
        sub_table_model: 子表的 model，如 'sub_table_design_xxx'
        field_model: 要汇总的子表日期列。支持三种传法：
            - 字符串 model（如 'date_xxx'）
            - widget tuple（如 SUB_DATE 的返回值）
            - widget dict（从子表 columns 中取出的控件对象）
            传 widget 时会自动提取 model，并用其 options.designType 覆盖 date_type 和 fmt
        summary_type: 仅 'inner-date-earliest'(最早) 或 'inner-date-latest'(最晚)
        date_type: 'date' 或 'datetime'。传 widget 时会被自动覆盖为字段的 designType
        fmt: 日期输出格式。传 widget 时会被自动覆盖为字段的 format
        filter: 过滤条件
        wrap: 是否包裹 AutoGrid card（默认 True）

    用法:
        date_field = SUB_DATE('日期字段', parent_key)
        earliest = SUMMARY_DATE('最早日期', sub_table['model'], date_field)
        # date_type 和 fmt 自动从 date_field 的 options 中提取
    """
    # 自动提取：如果传的是 widget tuple/dict，提取 model 并同步 designType/format
    field_widget = None
    if isinstance(field_model, (list, tuple)):
        # widget tuple: (widget_dict, key, model)
        field_widget = field_model[0]
        field_model = field_model[2] if len(field_model) > 2 else field_model[0].get('model', field_model)
    elif isinstance(field_model, dict) and 'options' in field_model:
        field_widget = field_model
        field_model = field_widget.get('model', field_model)

    if field_widget:
        field_opts = field_widget.get('options', {})
        field_dt = field_opts.get('designType', 'date')
        if field_dt in ('date', 'datetime'):
            date_type = field_dt
            fmt = field_opts.get('format', 'yyyy-MM-dd' if field_dt == 'date' else 'yyyy-MM-dd HH:mm:ss')

    if date_type == 'datetime' and fmt == 'yyyy-MM-dd':
        fmt = 'yyyy-MM-dd HH:mm:ss'
    key = _gen_key()
    model = _gen_model("date")
    _sleep()
    default_filter = {"enabled": False, "rules": [], "matchType": "AND"}
    w = {
        "type": "date", "name": name,
        "className": "form-summary-date", "icon": "icon-sigma",
        "isSummary": True,
        "hideTitle": False,
        "options": {
            "linkTable": sub_table_model,
            "field": field_model,
            "summary": summary_type,
            "type": date_type,
            "designType": date_type,
            "format": fmt,
            "timestamp": True,
            "defaultValue": "",
            "filter": filter if filter else default_filter,
            "hidden": False, "hiddenOnAdd": False, "required": False, "fieldNote": "",
        },
        "key": key, "model": model, "modelType": "main",
        "rules": [], "isSubItem": False,
        "advancedSetting": {
            "defaultValue": {
                "type": "compose", "value": "", "format": "string",
                "allowFunc": True, "valueSplit": "", "customConfig": False,
            }
        }
    }
    if wrap:
        return _card_wrap(w, key, model)
    return w, key, model


# ============================================================
# 子表
# ============================================================
def make_sub_table(name, sub_widgets, column_number=2, operation_mode=1,
                   is_word_style=False, is_word_inner_grid=False, default_rows=0):
    """创建子表容器，sub_widgets 为子控件列表，返回 (sub_table_dict, sub_key)

    Args:
        column_number: 布局列数 1/2/3/4，columns 数组长度必须与此一致
        operation_mode: 操作方式 1=行内编辑，2=弹出编辑
        is_word_style: 是否启用 Word 文档风格（黑色边框表格样式）
        is_word_inner_grid: 是否启用内嵌栅格（配合 is_word_style 解决内部边框问题）
        default_rows: 默认预填行数

    注意：columns 数组的长度必须等于 columnNumber，每列的 span = 24 / columnNumber。
    如果不匹配，设计器会显示异常（如空白列或控件挤压）。
    """
    key = _gen_key()
    model = _gen_model("sub-table-design")
    _sleep()
    col_span = 24 // column_number
    columns = []
    for i in range(column_number):
        columns.append({"span": col_span, "list": []})
    # 将 sub_widgets 顺序填充到各列（先填满第1列，再填第2列……）
    # 这样表格视图按列顺序读取时，字段顺序与定义顺序一致
    import math
    per_col = math.ceil(len(sub_widgets) / column_number) if column_number > 0 else len(sub_widgets)
    for idx, w in enumerate(sub_widgets):
        col_idx = idx // per_col if per_col > 0 else 0
        col_idx = min(col_idx, column_number - 1)
        columns[col_idx]["list"].append(w)
    return {
        "type": "sub-table-design", "name": name,
        "className": "form-sub-table", "icon": "icon-table",
        "hideTitle": False, "class": ["data-j-editable-design"],
        "isContainer": True,
        "columns": columns,
        "options": {
            "isWordStyle": is_word_style, "isWordInnerGrid": is_word_inner_grid,
            "gutter": 0,
            "columnNumber": column_number, "operationMode": operation_mode,
            "justify": "start", "align": "top",
            "defaultValue": [], "subTableName": "", "defaultRows": default_rows,
            "showCheckbox": True, "showNumber": True, "showRowButton": False,
            "allowAdd": True, "autoHeight": True, "defaultValType": "none",
            "hidden": False, "hiddenOnAdd": False, "required": False, "fieldNote": ""
        },
        "key": key, "model": model, "modelType": "main",
        "rules": [], "isSubItem": False
    }, key


# ============================================================
# 快捷控件工厂函数（大写命名）
# 默认返回 (autoGridCard, widget_key, widget_model)
# wrap=False 时返回 (widget_dict, widget_key, widget_model)
# is_sub=True 时返回子表控件 (widget_dict, widget_key, widget_model)
# ============================================================

def _card_wrap(w, key, model):
    """包裹控件到 card 并返回 (card, key, model)"""
    return make_card(w), key, model


def _finalize(w, k, m, wrap, is_sub, col_width, sub_extra=None):
    """统一处理控件的包裹逻辑。

    - is_sub=True → 设置子表列宽，返回裸控件
    - wrap=True → 包裹 AutoGrid card
    - wrap=False → 返回裸控件（用于 Grid 列内）
    """
    if is_sub:
        w["subOptions"]["width"] = col_width
        if sub_extra:
            w["subOptions"].update(sub_extra)
        return w, k, m
    if wrap:
        return _card_wrap(w, k, m)
    return w, k, m


def INPUT(name, required=False, width=100, placeholder='', unique=False,
          fill_rule_code='', readonly=False, allow_scan=False, scan_editable=True,
          *, wrap=True, is_sub=False, parent_key=None, col_width='200px', **kw):
    opts = {
        "width": "100%", "defaultValue": "", "required": required,
        "dataType": None, "pattern": "", "patternMessage": "",
        "placeholder": placeholder, "clearable": False, "readonly": readonly,
        "disabled": False, "fillRuleCode": fill_rule_code, "showPassword": False,
        # 【LHZP-1945】单行文本扫码（APP 端）；与 showPassword 互斥
        "allowScan": allow_scan, "scanEditable": scan_editable,
        "unique": unique, "hidden": False, "hiddenOnAdd": False,
        "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("input", name, "form-input", "icon-input", opts,
                          required=required, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def TEXTAREA(name, required=False, width=100, placeholder='',
             fill_rule_code='', readonly=False,
             *, wrap=True, is_sub=False, parent_key=None, col_width='250px', **kw):
    opts = {
        "width": "100%", "defaultValue": "", "required": required,
        "disabled": False, "pattern": "", "patternMessage": "",
        "placeholder": placeholder, "readonly": readonly, "unique": False,
        "fillRuleCode": fill_rule_code,
        "hidden": False, "hiddenOnAdd": False, "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("textarea", name, "form-textarea", "icon-textarea", opts,
                          required=required, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def NUMBER(name, required=False, width=100, unit='', precision=0, placeholder='',
           *, wrap=True, is_sub=False, parent_key=None, col_width='120px', **kw):
    opts = {
        "width": "", "required": required, "defaultValue": 0,
        "placeholder": placeholder, "precision": precision, "controls": False,
        "min": 0, "minUnlimited": True, "max": 100, "maxUnlimited": True,
        "step": 1, "disabled": False, "controlsPosition": "right",
        "unitText": unit, "unitPosition": "suffix", "showPercent": False,
        "align": "left", "hidden": False, "hiddenOnAdd": False,
        "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("number", name, "form-number", "icon-number", opts,
                          required=required, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def INTEGER(name, required=False, width=100, unit='', placeholder='请输入整数',
            *, wrap=True, is_sub=False, parent_key=None, col_width='120px', **kw):
    opts = {
        "width": "", "placeholder": placeholder, "required": required,
        "min": 0, "minUnlimited": True, "max": 100, "maxUnlimited": True,
        "step": 1, "precision": 0, "controls": not bool(unit), "disabled": False,
        "controlsPosition": "right", "unitText": unit, "unitPosition": "suffix",
        "showPercent": False, "align": "left", "hidden": False,
        "hiddenOnAdd": False, "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("integer", name, "form-integer", "icon-integer", opts,
                          required=required, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def MONEY(name, required=False, width=100, unit='元', placeholder='请输入金额',
          *, wrap=True, is_sub=False, parent_key=None, col_width='150px', **kw):
    opts = {
        "width": "180px", "placeholder": placeholder, "required": required,
        "unitText": unit, "unitPosition": "suffix", "precision": 2,
        "hidden": False, "disabled": False, "hiddenOnAdd": False,
        "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("money", name, "form-money", "icon-money", opts,
                          required=required, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def DATE(name, required=False, width=100, fmt=None, placeholder='',
         date_type='date',
         *, wrap=True, is_sub=False, parent_key=None, col_width='180px', **kw):
    """日期选择器。

    Args:
        date_type: 显示类型（写入 options.type）。敲敲云可选：
            日期组（designType=date）：year / month / quarter / week / date（默认）
            日期时间组（designType=datetime）：datetime_s / datetime_sf / datetime
        fmt: 显示格式。不传则按 date_type 用源码默认；quarter/week 格式锁定不可改。

    敲敲云不提供 daterange / dates / datetimerange。
    """
    meta = _DATE_TYPE_META.get(date_type)
    if meta is None:
        raise ValueError(
            f'DATE date_type="{date_type}" 非法。敲敲云可选: {", ".join(_DATE_TYPE_META)}'
        )
    format_value = meta['format'] if (fmt is None or meta.get('format_locked')) else fmt
    timestamp = meta.get('timestamp', True)
    opts = {
        "defaultValue": "", "defaultValueType": 1,
        "readonly": False, "disabled": False, "editable": True,
        "clearable": True, "placeholder": placeholder, "startPlaceholder": "",
        "endPlaceholder": "", "designType": meta['designType'], "type": date_type,
        "format": format_value, "timestamp": timestamp, "required": required,
        "width": "", "hidden": False, "hiddenOnAdd": False,
        "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("date", name, "form-date", "icon-date", opts,
                          required=required, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def TIME(name, required=False, width=100,
         *, wrap=True, is_sub=False, parent_key=None, col_width='150px', **kw):
    opts = {
        "defaultValue": "", "inputDefVal": False,
        "readonly": False, "disabled": False, "editable": True,
        "clearable": True, "placeholder": "", "startPlaceholder": "",
        "endPlaceholder": "", "isRange": False, "arrowControl": False,
        "format": "HH:mm:ss", "required": required, "width": "",
        "hidden": False, "hiddenOnAdd": False, "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("time", name, "form-time", "icon-time", opts,
                          required=required, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def SWITCH(name, active='Y', inactive='N', width=100,
           *, wrap=True, is_sub=False, parent_key=None, col_width='100px', **kw):
    opts = {
        "defaultValue": False, "disabled": False,
        "activeValue": active, "inactiveValue": inactive,
        "hidden": False, "hiddenOnAdd": False, "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("switch", name, "form-switch", "icon-switch", opts,
                          is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def _make_options_list(options, colors=None, field_name=None):
    """将简单字符串列表或 dict 列表转为 options 数组。

    支持两种输入格式：
    - 字符串列表: ['选项1', '选项2'] → [{"value": "选项1", "itemColor": "#xxx"}, ...]
    - dict 列表: [{'value': '1', 'label': '男'}] → [{"value": "1", "label": "男", "itemColor": "#xxx"}, ...]
      注：label 与 value 不同时，label 会被保留在输出中；调用方应同步将 showLabel 设为 True。

    注意：value 必须是简单字符串，不能是嵌套对象，否则渲染时显示 [object Object]。

    颜色规则：
    - 如果选项已自带合法的 itemColor（在合法 20 色列表中），直接保留
    - 否则从 default_colors 按索引循环分配
    """
    # 合法 20 色（与前端 src/data/colors.js 的 Colors 数组完全一致）
    default_colors = [
        "#2196F3", "#08C9C9", "#00C345", "#FAD714", "#FF9300",
        "#F52222", "#EB2F96", "#7500EA", "#2D46C4", "#484848",
        "#C9E6FC", "#C3F2F2", "#C2F1D2", "#FEF6C6", "#FFE5C2",
        "#FDCACA", "#FACDE6", "#DEC2FA", "#CCD2F1", "#D3D3D3",
    ]
    result = []
    for i, opt in enumerate(options):
            # 如果用户指定了 itemColor，必须在合法列表中，否则报错
        user_color = None
        if isinstance(opt, dict):
            user_color = opt.get('itemColor')
        if user_color:
            if user_color in default_colors:
                c = user_color
            else:
                raise ValueError(
                    f'字段 "{field_name}" 的选项 "{opt.get("value", opt)}" 使用了非法颜色值 "{user_color}"，'
                    f'不在合法 20 色列表中。请从以下颜色中选择：\n'
                    f'  {"  ".join(default_colors)}'
                )
        elif colors and i < len(colors) and colors[i] in default_colors:
            c = colors[i]
        else:
            c = default_colors[i % len(default_colors)]
        # dict 格式时提取 value 字段，避免嵌套对象导致 [object Object]
        if isinstance(opt, dict):
            val = opt.get('value', opt.get('label', str(opt)))
            item = {"value": val, "itemColor": c}
            label = opt.get('label')
            if label is not None and str(label) != str(val):
                item["label"] = label
        else:
            val = opt
            item = {"value": val, "itemColor": c}
        result.append(item)
    return result


def RADIO(name, options, required=False, width=100, dict_code=None,
          *, wrap=True, is_sub=False, parent_key=None, col_width='200px', **kw):
    """单选框组。options: 字符串列表 或 dict_code 指定系统字典"""
    options_list = _make_options_list(options, field_name=name) if options else []
    show_label = kw.pop('showLabel', None)
    if show_label is None:
        show_label = any("label" in o for o in options_list)
    opts = {
        "inline": kw.pop('inline', True), "matrixWidth": 120, "defaultValue": "",
        "showType": kw.pop('showType', 'default'),
        "showLabel": show_label,
        "useColor": kw.pop('useColor', False),
        "colorIteratorIndex": 3,
        "options": options_list,
        "required": required, "width": "", "remote": False,
        "remoteOptions": [], "props": {"value": "value", "label": "label"},
        "remoteFunc": "", "disabled": False,
        "hidden": kw.pop('hidden', False),
        "hiddenOnAdd": kw.pop('hiddenOnAdd', False),
        "fieldNote": kw.pop('fieldNote', ''),
    }
    if not is_sub:
        opts["autoWidth"] = width
    extra = {}
    if dict_code:
        opts["remote"] = "dict"
        opts["dictCode"] = dict_code
        opts["showLabel"] = True
        opts["options"] = []
        extra["dictOptions"] = options if isinstance(options[0], dict) else []
    w, k, m = make_widget("radio", name, "form-radio", "icon-radio-active", opts,
                          required=required, extra=extra, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def CHECKBOX(name, options, required=False, width=100, dict_code=None,
             *, wrap=True, is_sub=False, parent_key=None, col_width='200px', **kw):
    options_list = _make_options_list(options, field_name=name) if options else []
    show_label = kw.pop('showLabel', None)
    if show_label is None:
        show_label = any("label" in o for o in options_list)
    opts = {
        "inline": kw.pop('inline', True), "matrixWidth": 120, "defaultValue": [],
        "showLabel": show_label,
        "showType": kw.pop('showType', 'default'), "useColor": kw.pop('useColor', False),
        "colorIteratorIndex": 3,
        "options": options_list,
        "required": required, "width": "", "remote": False,
        "remoteOptions": [], "props": {"value": "value", "label": "label"},
        "remoteFunc": "", "disabled": False,
        "hidden": kw.pop('hidden', False),
        "hiddenOnAdd": kw.pop('hiddenOnAdd', False),
        "fieldNote": kw.pop('fieldNote', ''),
    }
    if not is_sub:
        opts["autoWidth"] = width
    extra = {}
    if dict_code:
        opts["remote"] = "dict"
        opts["dictCode"] = dict_code
        opts["showLabel"] = True
        opts["options"] = []
        extra["dictOptions"] = options if isinstance(options[0], dict) else []
    w, k, m = make_widget("checkbox", name, "form-checkbox", "icon-checkbox", opts,
                          required=required, extra=extra, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def SELECT(name, options, required=False, width=100, multiple=False, dict_code=None,
           placeholder='',
           *, wrap=True, is_sub=False, parent_key=None, col_width='150px', **kw):
    options_list = _make_options_list(options, field_name=name) if options else []
    show_label = kw.pop('showLabel', None)
    if show_label is None:
        show_label = any("label" in o for o in options_list)
    opts = {
        "defaultValue": "" if not multiple else [],
        "multiple": multiple, "disabled": False, "clearable": True,
        "placeholder": placeholder, "required": required,
        "showLabel": show_label,
        "showType": kw.pop('showType', 'default'), "width": "", "useColor": kw.pop('useColor', False),
        "colorIteratorIndex": 3,
        "options": options_list,
        "remote": False, "filterable": kw.pop('filterable', False),
        "remoteOptions": [], "props": {"value": "value", "label": "label"},
        "remoteFunc": "",
        "hidden": kw.pop('hidden', False),
        "hiddenOnAdd": kw.pop('hiddenOnAdd', False),
        "fieldNote": kw.pop('fieldNote', ''),
    }
    if not is_sub:
        opts["autoWidth"] = width
    extra = {}
    if dict_code:
        opts["remote"] = "dict"
        opts["dictCode"] = dict_code
        opts["showLabel"] = True
        opts["options"] = []
        extra["dictOptions"] = options if isinstance(options[0], dict) else []
    w, k, m = make_widget("select", name, "form-select", "icon-select", opts,
                          required=required, extra=extra, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def PHONE(name, required=False, width=100, placeholder='',
          *, wrap=True, is_sub=False, parent_key=None, col_width='180px', **kw):
    opts = {
        "width": "", "defaultValue": "", "required": required,
        "placeholder": placeholder, "readonly": False, "disabled": False,
        "unique": False, "hidden": False, "showVerifyCode": False,
        "hiddenOnAdd": False, "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("phone", name, "form-input-phone", "icon-mobile-phone", opts,
                          required=required, extra={
        "defaultRules": [
            {"type": "phone", "message": "请输入正确的手机号码"},
            {"type": "validator", "message": "", "trigger": "blur"}
        ]
    }, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def EMAIL(name, required=False, width=100, placeholder='',
          *, wrap=True, is_sub=False, parent_key=None, col_width='200px', **kw):
    opts = {
        "width": "", "defaultValue": "", "required": required,
        "placeholder": placeholder, "readonly": False, "disabled": False,
        "unique": False, "hidden": False, "showVerifyCode": False,
        "hiddenOnAdd": False, "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("email", name, "form-input-email", "icon-email", opts,
                          required=required, extra={
        "defaultRules": [
            {"type": "email", "message": "请输入正确的邮箱地址"},
            {"type": "validator", "message": "", "trigger": "blur"}
        ]
    }, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def USER(name, required=False, width=100, multiple=False, default_login=False, placeholder='',
         *, wrap=True, is_sub=False, parent_key=None, col_width='200px', **kw):
    opts = {
        "keyMaps": [], "defaultValue": "", "defaultLogin": default_login,
        "placeholder": placeholder, "width": "100%", "multiple": multiple,
        "disabled": False, "customReturnField": "username",
        "hidden": False, "dataAuthType": "member",
        "hiddenOnAdd": False, "required": required, "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("select-user", name, "form-select-user", "icon-user-circle", opts,
                          required=required, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def DEPART(name, required=False, width=100, multiple=False, placeholder='',
           *, wrap=True, is_sub=False, parent_key=None, col_width='200px', **kw):
    opts = {
        "keyMaps": [], "defaultValue": "", "defaultLogin": False,
        "placeholder": placeholder, "width": "100%", "multiple": multiple,
        "disabled": False, "customReturnField": "id",
        "hidden": False, "dataAuthType": "member",
        "hiddenOnAdd": False, "required": required, "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("select-depart", name, "form-select-depart", "icon-depart", opts,
                          required=required, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def AREA(name, required=False, width=100, level=3, placeholder='请选择',
         *, wrap=True, is_sub=False, parent_key=None, col_width='250px', **kw):
    """省市级联动（area-linkage）。

    源码默认：type='area-linkage', name='省市级联动', className='form-area-linkage',
    icon='icon-jilianxuanze', hideTitle=False。
    options 源码默认：width='', placeholder='请选择', areaLevel=3, defaultValue='',
    clearable=True, disabled=False, hidden=False。

    Args:
        level: 选择级别，写入 options.areaLevel。1=省，2=省市，3=省市区（默认 3）。
        placeholder: 占位提示，默认「请选择」。

    写入数据时只存最后一级区划代码（1→省码如 110000，2→市码如 110100，3→区码如 110101），
    不要写「省码,市码,区码」。
    """
    opts = {
        "width": "", "placeholder": placeholder, "areaLevel": level,
        "defaultValue": "", "clearable": True, "disabled": False,
        "hidden": False, "hiddenOnAdd": False, "required": required,
        "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("area-linkage", name, "form-area-linkage", "icon-jilianxuanze", opts,
                          required=required, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def CATEGORY_LINKAGE(name, table='', txt='', store_key='', id_field='', pid_field='',
                     condition='', level=3, required=False, width=100, placeholder='请选择',
                     *, wrap=True, is_sub=False, parent_key=None, col_width='250px', **kw):
    """联动（category-linkage）。⛔ 本 skill 禁止新建（敲敲云需屏蔽）。

    源码默认：type='category-linkage', name='联动', className='form-category-linkage',
    icon='icon-liandong', hideTitle=False。
    options.defaultValue 为路径数组 []（emitPath=true），不是最后一级字符串。

    Args:
        table: 数据表名（category.table），必填才能出选项
        txt: 显示字段（category.txt）
        store_key: 存储字段（category.key）
        id_field: ID 字段（category.idField）
        pid_field: 父 ID 字段（category.pidField）
        condition: 根级条件（仅第一层）
        level: 联动层级，1–10，默认 3；移动端最多 3 层

    写入数据传 Python list，如 ['省码', '市码', '区码']。dictText 为 pathLabels 用 / 拼接。
    子表清单含此类型，但 skill 不允许使用（主表、子表均禁止新建）。
    """
    opts = {
        "defaultValue": [], "width": "100%", "placeholder": placeholder,
        "required": required, "disabled": False, "clearable": True,
        "hidden": False, "hiddenOnAdd": False, "fieldNote": "",
        "category": {
            "table": table, "txt": txt, "key": store_key,
            "level": level, "idField": id_field, "pidField": pid_field,
            "condition": condition,
        },
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("category-linkage", name, "form-category-linkage", "icon-liandong", opts,
                          required=required, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def ORG_ROLE(name, required=False, width=100, multiple=False, placeholder='选择组织角色',
             *, wrap=True, is_sub=False, parent_key=None, col_width='200px', **kw):
    """组织角色选择控件"""
    opts = {
        "defaultValue": "", "defaultLogin": False,
        "placeholder": placeholder, "width": "100%", "multiple": multiple,
        "disabled": False,
        "hidden": False, "dataAuthType": "member",
        "hiddenOnAdd": False, "required": required, "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("org-role", name, "form-org-role", "icon-zuzhijuese", opts,
                          required=required, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def DEPART_POST(name, required=False, width=100, multiple=False, placeholder='',
                *, wrap=True, is_sub=False, parent_key=None, col_width='200px', **kw):
    """岗位组件"""
    opts = {
        "keyMaps": [], "defaultValue": "", "defaultLogin": False,
        "placeholder": placeholder, "width": "100%", "multiple": multiple,
        "disabled": False, "customReturnField": "id",
        "hidden": False, "dataAuthType": "member",
        "hiddenOnAdd": False, "required": required, "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("select-depart-post", name, "form-select-depart", "icon-gangwei", opts,
                          required=required, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def TABLE_DICT(name, dict_table='', dict_code_col='', dict_text_col='',
               required=False, width=100, multiple=False, style='select',
               query_scope='cgreport', filterable=True, clearable=True, disabled=False,
               *, wrap=True, is_sub=False, parent_key=None, col_width='200px', **kw):
    """表字典控件。⛔ 敲敲云设计器隐藏（QQYUN-3641），本 skill 禁止新建。

    Args:
        name: 控件名称
        dict_table: 字典表名（Online报表编码或数据库表名）
        dict_code_col: 值字段列名
        dict_text_col: 显示字段列名（popup 模式下会自动设为自身 model）
        style: 展示风格 'select'(下拉) 或 'popup'(弹窗)
        query_scope: 查询模式 'cgreport'(Online报表) 或 'database'(数据库表)
        filterable: 是否可搜索（仅 style=select 有效，默认 True）
        clearable: 是否可清除（默认 True）
        disabled: 是否禁用（默认 False）
    """
    # popup 模式下 dictText 必须为该控件自身的 model，需提前生成
    model_for_dicttext = None
    if style == 'popup':
        model_for_dicttext = _gen_model('table-dict')
        _sleep()

    text_col = model_for_dicttext if style == 'popup' else dict_text_col

    opts = {
        "width": "100%", "defaultValue": "", "placeholder": "点击选择表字典",
        "showIcon": True, "iconName": "icon-popup",
        "disabled": disabled, "multiple": multiple, "clearable": clearable,
        "style": style, "dictTable": dict_table,
        "dictCode": dict_code_col, "dictText": text_col,
        "hidden": False, "required": required, "filterable": filterable,
        "queryScope": query_scope,
        "hiddenOnAdd": False, "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("table-dict", name, "form-dict", "icon-dict", opts,
                          required=required, is_sub=is_sub, parent_key=parent_key, model=model_for_dicttext, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def SELECT_TREE(name, category_code='B02', required=False, width=100, multiple=False, placeholder='',
                disabled=False, data_from='category', table_conf=None,
                *, wrap=True, is_sub=False, parent_key=None, col_width='200px', **kw):
    """下拉树控件。⛔ 敲敲云设计器隐藏（QQYUN-3641），本 skill 禁止新建。

    Args:
        name: 控件名称
        category_code: 分类字典编码（data_from='category' 时使用，默认 'B02'）
        disabled: 是否禁用（默认 False）
        data_from: 数据来源 'category'（分类树，默认）或 'table'（自定义表树）
        table_conf: 自定义表树配置（data_from='table' 时使用），dict，支持字段：
            name(表名), code(值字段), text(显示字段), pidField(父节点字段),
            rootPid(根节点值), leaf(叶子标识字段), converIsLeafVal(bool)
    """
    table_defaults = {
        "name": "", "code": "", "text": "",
        "pidField": "", "rootPid": "", "leaf": "",
        "converIsLeafVal": True,
    }
    if data_from == 'table' and table_conf:
        table_defaults.update(table_conf)

    opts = {
        "defaultValue": "", "placeholder": placeholder, "width": "",
        "disabled": disabled, "multiple": multiple,
        "dataFrom": data_from,
        "conf": {
            "category": {"code": category_code},
            "table": table_defaults,
            "condition": "",
            "conditionOnlyRoot": True,
        },
        "hidden": False, "required": required,
        "hiddenOnAdd": False, "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("select-tree", name, "form-select-tree", "icon-tree", opts,
                          required=required, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def IMGUPLOAD(name, required=False, width=100, length=9,
              *, wrap=True, is_sub=False, parent_key=None, col_width='150px', **kw):
    opts = {
        "defaultValue": [], "size": {"width": 100, "height": 100},
        "width": "", "tokenFunc": "funcGetToken", "token": "",
        "domain": "http://img.h5huodong.com", "disabled": False,
        "length": length, "multiple": True, "hidden": False,
        "hiddenOnAdd": False, "required": required,
        "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("imgupload", name, "form-tupian", "icon-tupian", opts,
                          required=required, is_sub=is_sub, parent_key=parent_key, **kw)
    sub_extra = {"size": {"width": 50, "height": 50}} if is_sub else None
    return _finalize(w, k, m, wrap, is_sub, col_width, sub_extra=sub_extra)


def FILE(name, required=False, width=100,
         *, wrap=True, is_sub=False, parent_key=None, col_width='200px', **kw):
    opts = {
        "defaultValue": [], "token": "", "length": 0,
        "drag": False, "listStyleType": "card", "multiple": False,
        "multipleDown": True, "disabled": False, "buttonText": "点击上传文件",
        "tokenFunc": "funcGetToken", "hidden": False, "hiddenOnAdd": False,
        "required": required, "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("file-upload", name, "form-file-upload", "icon-shangchuan", opts,
                          required=required, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def SLIDER(name, required=False, width=100, min_val=0, max_val=100, show_input=False,
           *, wrap=True, is_sub=False, parent_key=None, col_width='200px', **kw):
    opts = {
        "defaultValue": 0, "disabled": False, "required": required,
        "min": min_val, "max": max_val, "step": 1,
        "showInput": show_input, "showPercent": False, "range": False,
        "width": "", "hidden": False, "hiddenOnAdd": False,
        "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("slider", name, "form-slider", "icon-slider", opts,
                          required=required, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def RATE(name, required=False, width=100, max_val=5, allow_half=False,
         *, wrap=True, is_sub=False, parent_key=None, col_width='150px', **kw):
    opts = {
        "defaultValue": None, "max": max_val, "disabled": False,
        "allowHalf": allow_half, "required": required,
        "hidden": False, "hiddenOnAdd": False,
        "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("rate", name, "form-rate", "icon-rate", opts,
                          required=required, extra={
        "defaultRules": [{"type": "validator", "message": "", "trigger": "change"}]
    }, is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def COLOR(name, width=100,
          *, wrap=True, is_sub=False, parent_key=None, col_width='120px', **kw):
    opts = {
        "defaultValue": "", "disabled": False, "showAlpha": False,
        "required": False, "hidden": False, "hiddenOnAdd": False,
        "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("color", name, "form-color", "icon-color", opts,
                          is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def AUTONUMBER(name, prefix='', width=100, date_format='yyyyMMdd', *, wrap=True, **kw):
    """自动编号控件

    date_format: 创建日期段格式，UI 可选 yyyyMMdd / yyyyMM / MMdd / yyyy（2026-09-03 对照
        ConfigItem.vue；'custom' 需面板自定义格式，本工厂不生成，走 update_widget 手写
        {type:'create_date', format:'custom', formatCustom:'<格式>'}）
    """
    # numberRules 段对象必须带 UI 渲染依赖的辅助键（2026-09-03 对照 ConfigItem.vue 与 UI 样本）：
    # text 段面板绑定 rule.text（顺带 value 同值兼容后端旧字段）；
    # create_date 段面板绑定 rule.format（选中项），formatCustom 仅 format='custom' 时用，
    # dateFormat 为后端兼容键——三键同写与 UI 手工配置样本（自动编号-01）一致。
    # 缺 text/format 时设计器规则面板读不到段内容，表现为「设置没生效」（接口 success）。
    rules = [{"type": "number", "mode": 1, "start": 1, "reset": 0, "length": 4, "continue": False}]
    if prefix:
        rules.insert(0, {"type": "text", "text": prefix, "value": prefix})
        rules.insert(1, {"type": "create_date", "format": date_format,
                         "dateFormat": date_format, "formatCustom": date_format})
    w, k, m = make_widget("auto-number", name, "form-auto-number", "icon-hashtag", {
        "numberRules": rules,
        "generateOnAdd": True,
        "placeholder": "${title}自动生成，不需要填写",
        "hidden": False, "hiddenOnAdd": False, "fieldNote": "", "autoWidth": width
    }, **kw)
    if wrap:
        return _card_wrap(w, k, m)
    return w, k, m


def HANDSIGN(name, required=False, width=100, *, wrap=True, **kw):
    w, k, m = make_widget("hand-sign", name, "form-hand-sign", "icon-signature", {
        "width": "100%", "height": "200px", "disabled": False,
        "hidden": False, "hiddenOnAdd": False, "required": required,
        "fieldNote": "", "autoWidth": width
    }, required=required, **kw)
    if wrap:
        return _card_wrap(w, k, m)
    return w, k, m


def OA_APPROVAL_COMMENTS(name='审批意见', required=False, width=100, *, wrap=True, **kw):
    """OA 审批意见控件。⛔ 敲敲云无 OA 字段分组，本 skill 禁止新建。"""
    w, k, m = make_widget("oa-approval-comments", name, "form-oa-approval-comments", "icon-input", {
        "width": "100%", "required": required, "disabled": False,
        "placeholder": "", "hidden": False,
        "hiddenOnAdd": False, "fieldNote": "", "autoWidth": width
    }, required=required, **kw)
    if wrap:
        return _card_wrap(w, k, m)
    return w, k, m


# ============================================================
# 静态展示 / 高级控件（不存储数据或特殊用途）
# ============================================================

def TEXT(text='这里是一段文本', font_size=16, font_color='#4c4c4c',
         align='left', bold=False, *, wrap=True, **kw):
    """静态文本展示控件（不存储数据）"""
    w, k, m = make_widget("text", "文本", "form-text", "icon-text", {
        "text": text, "width": "100%", "align": align,
        "verticalAlign": "top", "fontSize": font_size, "lineHeight": "",
        "fontColor": font_color, "fontBold": bold,
        "fontItalic": False, "fontUnderline": False, "fontLineThrough": False,
        "hidden": False,
    }, **kw)
    w["hideLabel"] = True
    if wrap:
        return _card_wrap(w, k, m)
    return w, k, m


def BUTTONS(text='按钮', btn_type='default', icon='', click_code="console.log('hello,world!')",
            *, wrap=True, **kw):
    """按钮控件（不存储数据）

    Args:
        text: 按钮文字
        btn_type: 按钮类型 'default'|'primary'|'success'|'warning'|'danger'|'info'
        icon: 图标名称
        click_code: 点击事件 JS 代码
    """
    w, k, m = make_widget("buttons", "按钮", "form-buttons", "icon-btn2", {
        "text": text, "icon": icon, "type": btn_type,
        "btnSize": "default", "plain": False, "round": False,
        "circle": False, "disabled": False, "hidden": False,
    }, **kw)
    w["hideLabel"] = True
    w["event"] = {"click": click_code}
    if wrap:
        return _card_wrap(w, k, m)
    return w, k, m


def BARCODE(name, source_model='', code_type='barcode', max_width=180,
            *, wrap=True, **kw):
    """条码/二维码控件

    Args:
        source_model: 引用字段的 model（条码内容来源）
        code_type: 'barcode'(一维码) 或 'qrcode'(二维码)
    """
    w, k, m = make_widget("barcode", name, "form-barcode", "icon-tiaoma", {
        "maxWidth": max_width, "codeType": code_type,
        "sourceModel": source_model, "hidden": False,
    }, **kw)
    if wrap:
        return _card_wrap(w, k, m)
    return w, k, m


def CAPITAL_MONEY(name, money_widget_key='', money_field='', width=100,
                  *, wrap=True, is_sub=False, parent_key=None, col_width='150px', **kw):
    """大写金额控件 — 关联一个金额/数字字段，自动转换为中文大写。
    【LHZP-1984】子表内可用。

    Args:
        money_widget_key: 关联的金额控件 key（直接指定）
        money_field: 关联的字段中文名（由 _post_process_widgets 解析为 key）
    """
    opts = {
        "moneyWidgetKey": money_widget_key, "hidden": False,
        "hiddenOnAdd": False, "fieldNote": "",
    }
    if money_field:
        opts["moneyField"] = money_field
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("capital-money", name, "form-money", "icon-money", opts,
                          is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def TEXT_COMPOSE(name, expression='', width=100,
                 *, wrap=True, is_sub=False, parent_key=None, col_width='200px', **kw):
    """文本组合控件 — 将多个字段值拼接展示。【LHZP-1984】子表内可用。

    Args:
        expression: 组合表达式，使用 $model$ 引用字段，如 '$input_xxx$-$input_yyy$'
    """
    opts = {
        "expression": expression, "hidden": False,
        "hiddenOnAdd": False, "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("text-compose", name, "form-text-compose", "icon-zuhe", opts,
                          is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def LOCATION(name, required=False, width=100, default_current=False, show_map=False,
             *, wrap=True, **kw):
    """定位控件"""
    w, k, m = make_widget("location", name, "form-location", "icon-location", {
        "width": "100%", "defaultValue": "",
        "defaultCurrent": default_current,
        "showLngLat": False, "showMap": show_map,
        "disabled": False, "hidden": False,
        "hiddenOnAdd": False, "required": required, "fieldNote": "", "autoWidth": width
    }, required=required, **kw)
    if wrap:
        return _card_wrap(w, k, m)
    return w, k, m


def MAP(name, required=False, width='100%', height='300px', zoom=15, lng=116.397467, lat=39.908806, **kw):
    """地图控件（百度地图）"""
    w, k, m = make_widget("map", name, "form-map", "icon-map", {
        "width": width, "height": height, "zoom": zoom,
        "required": required,
        "point": {"lng": lng, "lat": lat},
        "mapSettings": {
            "dragging": True, "scrollWheelZoom": True,
            "doubleClickZoom": True, "keyboard": False,
            "inertialDragging": True, "continuousZoom": True,
            "pinchToZoom": True,
        },
        "mapControls": {
            "navigation": True, "geolocation": True,
            "scale": True, "mapType": True,
            "panorama": False, "overviewMap": False,
        },
        "disabled": False, "hidden": False,
    }, **kw)
    return w, k, m


def OCR(name, ocr_type='normal', field_mapping=None, required=False, width=100,
        *, wrap=True, **kw):
    """文本识别控件（OCR）

    Args:
        ocr_type: 识别类型 'normal'(通用)|'id_card'(身份证)|'vat_invoice'(增值税发票)|'train_ticket'(火车票)
        field_mapping: 识别结果到表单字段的映射 dict
    """
    w, k, m = make_widget("ocr", name, "form-ocr", "icon-ocr-a", {
        "type": ocr_type,
        "fieldMapping": field_mapping or {},
        "hidden": False, "disabled": False, "required": required,
        "hiddenOnAdd": False, "fieldNote": "", "autoWidth": width
    }, required=required, **kw)
    if wrap:
        return _card_wrap(w, k, m)
    return w, k, m


# ============================================================
# 不需要 card 包裹的控件（直接返回控件本身）
# ============================================================

def DIVIDER(text='', **kw):
    """分隔符（不需要 card 包裹），返回 (widget_dict, key, model)"""
    w, k, m = make_widget("divider", text or "分隔符", "form-divider", "icon-divider", {
        "heightNumber": 48, "type": "horizontal", "text": text,
        "position": "center", "hidden": False, "hiddenOnAdd": False,
        "required": False, "fieldNote": ""
    }, **kw)
    w["hideLabel"] = True
    w["formItemMargin"] = True
    return w, k, m


def EDITOR(name, required=False, **kw):
    """富文本编辑器（不需要 card 包裹）"""
    w, k, m = make_widget("editor", name, "form-editor", "icon-fuwenbenkuang", {
        "defaultValue": "", "width": "100%", "disabled": False,
        "hidden": False, "hiddenOnAdd": False, "required": required, "fieldNote": ""
    }, required=required, **kw)
    return w, k, m


def MARKDOWN(name, required=False, **kw):
    """Markdown 编辑器（不需要 card 包裹）"""
    w, k, m = make_widget("markdown", name, "form-markdown", "icon-markdown", {
        "defaultValue": "", "width": "100%", "height": 300,
        "viewerAutoHeight": False, "disabled": False,
        "hidden": False, "hiddenOnAdd": False, "required": required, "fieldNote": ""
    }, required=required, **kw)
    return w, k, m


def TABS(tab_labels=None, tab_type='border-card', position='top'):
    """标签页容器控件（不需要 card 包裹）

    Args:
        tab_labels: 标签页名称列表，默认 ['Tab1', 'Tab2']
        tab_type: 标签样式 'border-card'|'card'|''
        position: 标签位置 'top'|'bottom'|'left'|'right'

    Returns:
        (widget_dict, key, model) — 向 panes[i]['list'] 中添加子控件

    用法:
        tabs_w, tabs_k, tabs_m = TABS(['基本信息', '详细信息'])
        # 向第一个标签页添加控件
        tabs_w['panes'][0]['list'].append(input_widget)
        # 向第二个标签页添加控件
        tabs_w['panes'][1]['list'].append(select_widget)
    """
    if tab_labels is None:
        tab_labels = ['Tab1', 'Tab2']
    key = _gen_key()
    _sleep()
    panes = []
    for label in tab_labels:
        panes.append({
            "name": label, "label": label, "rowNum": 1,
            "hidden": False, "hiddenOnAdd": False, "list": []
        })
    w = {
        "type": "tabs", "name": "Tabs",
        "className": "form-tabs", "icon": "icon-tab",
        "hideTitle": False, "hideLabel": True,
        "isContainer": True,
        "key": key, "model": f"tabs_{key}",
        "panes": panes,
        "options": {
            "width": "100%", "activeName": "",
            "type": tab_type, "position": position,
            "hidden": False,
        },
    }
    return w, key, w["model"]


# ============================================================
# 关联控件
# ============================================================

def LINK_RECORD(name, source_code, title_field, show_fields=None,
                required=False, width=100, show_mode='single', show_type='card',
                *, is_self=False, wrap=True, is_sub=False, parent_key=None, col_width='200px',
                filters=None, search=None, data_select_auth='all', **kw):
    """关联记录控件，返回 (card_or_widget, key, model)

    Args:
        source_code: 源表单 desformCode；自关联时传本表单自身的 desformCode
        title_field: 源表单标题字段 model
        show_fields: 源表单展示字段 model 列表
        show_mode: 'single' 或 'many'
        show_type: 'card', 'select', 'table'
        is_self: 是否为自关联（source_code == 本表单自身），设为 True 时会在控件顶层写入 isSelf=true
        filters: 可选，写进 options.filters 的筛选条件（默认空 AND）。
                 ⚠ 2026-09-03 修复：此前经 **kw 传给 make_widget 会被白名单丢弃（仅警告），
                 改控件类型后 filters 静默丢失；现为显式参数，必须走这里。
        search: 可选，写进 options.search 的查询设置（默认关闭）。
        data_select_auth: 'all' 全部 / 'read' 仅可选有查看权限的记录。
    """
    opts = {
        "sourceCode": source_code, "showMode": show_mode, "showType": show_type,
        "titleField": title_field, "showFields": show_fields or [],
        "allowView": True, "allowEdit": True, "allowAdd": True, "allowSelect": True,
        "buttonText": "添加记录", "twoWayModel": "", "dataSelectAuth": data_select_auth,
        "filters": filters if filters is not None else [{"matchType": "AND", "rules": []}],
        "search": search if search is not None else {"enabled": False, "field": "", "rule": "like", "afterShow": False, "fields": []},
        "createMode": {"add": True, "select": False, "params": {"selectLinkModel": ""}},
        "width": "100%", "defaultValue": "", "defaultValType": "none",
        "required": required, "disabled": False, "hidden": False,
        "hiddenOnAdd": False, "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    # is_self 是控件顶层属性（不在 options 内），通过 extra 注入
    extra = {"isSelf": True} if is_self else None
    # 自关联时 valueSplit 应为空串（make_widget 默认 "," 给 link-record，需覆盖）
    w, k, m = make_widget("link-record", name, "form-link-record", "icon-link", opts,
                          required=required, is_sub=is_sub, parent_key=parent_key,
                          extra=extra, **kw)
    if is_self:
        # valueSplit 在 advancedSetting 内，make_widget 已生成，直接覆盖
        w["advancedSetting"]["defaultValue"]["valueSplit"] = ""
    if is_sub:
        w["subOptions"]["width"] = col_width
        return w, k, m
    # AutoGrid.check: showType='table' bypasses AutoGrid
    if show_type == 'table':
        return w, k, m
    if wrap:
        return _card_wrap(w, k, m)
    return w, k, m


def LINK_FIELD(name, link_record_key, show_field, field_type='input',
               field_options=None, width=100,
               *, wrap=True, is_sub=False, parent_key=None, col_width='150px', **kw):
    """他表字段控件（与 link-record 配对使用）"""
    opts = {
        "linkRecordKey": link_record_key, "showField": show_field,
        "saveType": "view", "fieldType": field_type,
        "fieldOptions": field_options or {},
        "width": "100%", "defaultValue": "", "readonly": False,
        "disabled": False, "hidden": False, "hiddenOnAdd": False,
        "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    w, k, m = make_widget("link-field", name, "form-link-field", "icon-field", opts,
                          is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


def FORMULA(name, mode='CUSTOM', expression='', fields=None,
            width=100, unit='', decimal=2,
            date_begin='', date_end='', date_format_method=1,
            date_print_unit='m', date_add_exp='', date_print_format='YYYY-MM-DD',
            *, wrap=True, is_sub=False, parent_key=None, col_width='150px', **kw):
    """公式控件

    Args:
        mode: 数值模式(必须大写): 'SUM', 'AVERAGE', 'MAX', 'MIN', 'PRODUCT', 'CUSTOM'
              日期模式: 'DATEIF', 'DATEADD', 'NOW_DATEIF', 'PAST_NOW_DATEIF'
        expression: 自定义表达式（mode='CUSTOM' 时使用），字段引用语法: $model$
        fields: SUM/AVERAGE 等预定义模式时的字段 model 列表
        date_begin: 日期模式 — 开始日期字段引用，如 '$date_model$'
        date_end: 日期模式 — 结束日期字段引用，如 '$date_model$'
        date_format_method: 日期模式 — 格式化方式（1=开始00:00结束00:00，2=开始00:00结束24:00）
        date_print_unit: 日期模式 — 输出单位（'Y'年/'M'月/'d'天/'h'小时/'m'分钟）
        date_add_exp: DATEADD 模式 — 加减表达式，如 '+8h+30m', '-2d'
        date_print_format: DATEADD 模式 — 输出格式，如 'YYYY-MM-DD HH:mm:ss'
    """
    mode = mode.upper()
    _DATE_MODES = {'DATEIF', 'DATEADD', 'NOW_DATEIF', 'PAST_NOW_DATEIF'}
    opt_type = 'date' if mode in _DATE_MODES else 'number'
    opts = {
        "type": opt_type, "mode": mode, "expression": expression,
        "decimal": decimal, "thousand": True, "percent": False,
        "unitPosition": "suffix", "unitText": unit, "emptyAsZero": True,
        "dateBegin": date_begin, "dateEnd": date_end,
        "dateFormatMethod": date_format_method,
        "datePrintUnit": date_print_unit, "dateAddExp": date_add_exp,
        "datePrintFormat": date_print_format,
        "hidden": False, "hiddenOnAdd": False, "fieldNote": "",
    }
    if not is_sub:
        opts["autoWidth"] = width
    if fields and mode != 'CUSTOM':
        opts["fields"] = fields
    w, k, m = make_widget("formula", name, "form-formula", "icon-formula", opts,
                          is_sub=is_sub, parent_key=parent_key, **kw)
    return _finalize(w, k, m, wrap, is_sub, col_width)


# ============================================================
# 子表控件别名（向后兼容，推荐直接使用主函数 + is_sub=True）
# ============================================================

def SUB_INPUT(name, parent_key, required=False, col_width='200px', **kw):
    return INPUT(name, required=required, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_INTEGER(name, parent_key, required=False, col_width='120px', unit='', **kw):
    return INTEGER(name, required=required, unit=unit, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_NUMBER(name, parent_key, required=False, col_width='120px', unit='', **kw):
    return NUMBER(name, required=required, unit=unit, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_MONEY(name, parent_key, required=False, col_width='150px', unit='元', **kw):
    return MONEY(name, required=required, unit=unit, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_SELECT(name, parent_key, options, required=False, col_width='150px', **kw):
    return SELECT(name, options, required=required, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_DATE(name, parent_key, required=False, col_width='180px', **kw):
    return DATE(name, required=required, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_TIME(name, parent_key, required=False, col_width='150px', **kw):
    return TIME(name, required=required, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_SWITCH(name, parent_key, active='Y', inactive='N', col_width='100px', **kw):
    return SWITCH(name, active=active, inactive=inactive, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_RADIO(name, parent_key, options, required=False, col_width='200px', dict_code=None, **kw):
    return RADIO(name, options, required=required, dict_code=dict_code, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_CHECKBOX(name, parent_key, options, required=False, col_width='200px', dict_code=None, **kw):
    return CHECKBOX(name, options, required=required, dict_code=dict_code, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_TEXTAREA(name, parent_key, required=False, col_width='250px', **kw):
    return TEXTAREA(name, required=required, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_SLIDER(name, parent_key, col_width='200px', min_val=0, max_val=100, **kw):
    return SLIDER(name, min_val=min_val, max_val=max_val, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_RATE(name, parent_key, col_width='150px', max_val=5, **kw):
    return RATE(name, max_val=max_val, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_COLOR(name, parent_key, col_width='120px', **kw):
    return COLOR(name, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_USER(name, parent_key, required=False, col_width='200px', multiple=False, **kw):
    return USER(name, required=required, multiple=multiple, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_DEPART(name, parent_key, required=False, col_width='200px', multiple=False, **kw):
    return DEPART(name, required=required, multiple=multiple, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_DEPART_POST(name, parent_key, required=False, col_width='200px', **kw):
    return DEPART_POST(name, required=required, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_ORG_ROLE(name, parent_key, required=False, col_width='200px', multiple=False, **kw):
    return ORG_ROLE(name, required=required, multiple=multiple, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_PHONE(name, parent_key, required=False, col_width='180px', **kw):
    return PHONE(name, required=required, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_EMAIL(name, parent_key, required=False, col_width='200px', **kw):
    return EMAIL(name, required=required, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_AREA(name, parent_key, required=False, col_width='250px', **kw):
    return AREA(name, required=required, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_CAPITAL_MONEY(name, parent_key, money_widget_key='', money_field='', col_width='150px', **kw):
    return CAPITAL_MONEY(name, money_widget_key=money_widget_key, money_field=money_field,
                         wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_TEXT_COMPOSE(name, parent_key, expression='', col_width='200px', **kw):
    return TEXT_COMPOSE(name, expression=expression, wrap=False, is_sub=True,
                        parent_key=parent_key, col_width=col_width, **kw)

def SUB_IMGUPLOAD(name, parent_key, required=False, col_width='150px', **kw):
    """子表图片上传。缩略图自动缩小为 50x50（主表默认 100x100）。"""
    return IMGUPLOAD(name, required=required, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_FILE(name, parent_key, required=False, col_width='200px', **kw):
    return FILE(name, required=required, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width, **kw)

def SUB_TABLE_DICT(name, parent_key, dict_table='', dict_code_col='', dict_text_col='',
                   required=False, col_width='200px', multiple=False, style='select',
                   query_scope='cgreport', filterable=True, clearable=True, disabled=False,
                   **kw):
    return TABLE_DICT(name, dict_table=dict_table, dict_code_col=dict_code_col,
                      dict_text_col=dict_text_col, required=required,
                      multiple=multiple, style=style, query_scope=query_scope,
                      filterable=filterable, clearable=clearable, disabled=disabled,
                      wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width,
                      **kw)

def SUB_SELECT_TREE(name, parent_key, category_code='', required=False, col_width='200px',
                    multiple=False, disabled=False, data_from='category', table_conf=None,
                    **kw):
    return SELECT_TREE(name, category_code=category_code, required=required,
                       multiple=multiple, disabled=disabled,
                       data_from=data_from, table_conf=table_conf,
                       wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width,
                       **kw)

def SUB_LINK_RECORD(name, parent_key, source_code, title_field, show_fields=None,
                    required=False, col_width='200px', **kw):
    return LINK_RECORD(name, source_code, title_field, show_fields=show_fields,
                       required=required, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width,
                       **kw)

def SUB_LINK_FIELD(name, parent_key, link_record_key, show_field,
                   field_type='input', field_options=None, col_width='150px', **kw):
    return LINK_FIELD(name, link_record_key, show_field, field_type=field_type,
                      field_options=field_options, wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width,
                      **kw)

def SUB_FORMULA(name, parent_key, mode='CUSTOM', expression='', col_width='150px', unit='',
                fields=None, date_begin='', date_end='', date_format_method=1,
                date_print_unit='m', date_add_exp='', date_print_format='YYYY-MM-DD',
                **kw):
    """子表公式控件（向后兼容别名）。详见 FORMULA() 文档。"""
    return FORMULA(name, mode=mode, expression=expression, unit=unit,
                   fields=fields, date_begin=date_begin, date_end=date_end,
                   date_format_method=date_format_method, date_print_unit=date_print_unit,
                   date_add_exp=date_add_exp, date_print_format=date_print_format,
                   wrap=False, is_sub=True, parent_key=parent_key, col_width=col_width,
                   **kw)


def SUB_PRODUCT(name, parent_key, field_models, col_width='150px', unit='', **kw):
    """子表乘积公式（快捷方式）—— formula 控件 PRODUCT 模式的语法糖。

    等价于 SUB_FORMULA(name, parent_key, mode='PRODUCT', expression='$a$*$b$')，
    自动根据 field_models 列表拼接 PRODUCT 表达式。

    Args:
        name: 控件标签名
        parent_key: 所属子表的 key
        field_models: 参与乘积的字段 model 列表，如 ['money_xxx', 'integer_xxx']
        col_width: 子表列宽（默认 '150px'）
        unit: 单位文本

    用法:
        sub_qty = SUB_INTEGER('数量', sub_key)
        sub_price = SUB_MONEY('单价', sub_key)
        sub_amount = SUB_PRODUCT('金额', sub_key, [sub_price[2], sub_qty[2]])
    """
    expression = ''.join(f'${m}$' for m in field_models)
    return SUB_FORMULA(name, parent_key, mode='PRODUCT', expression=expression,
                       col_width=col_width, unit=unit)




# ============================================================
# 设计 JSON 组装 & 保存
# ============================================================

def _collect_types(items):
    """递归收集所有控件类型"""
    types = set()
    for item in items:
        t = item.get('type')
        if t:
            types.add(t)
        if t == 'card' and 'list' in item:
            types.update(_collect_types(item['list']))
        if t == 'grid' and 'columns' in item:
            for col in item['columns']:
                types.update(_collect_types(col.get('list', [])))
        if t == 'sub-table-design' and 'columns' in item:
            for col in item['columns']:
                types.update(_collect_types(col.get('list', [])))
    return types


def make_word_grid(*rows, cols_per_row=2):
    """创建 Word 风格的栅格行（匹配 JeecgBoot 真实 Word 风格实现）

    真实 Word 风格通过 CSS class `form-grid form-grid-word-theme` +
    表单设计器内置 Word 风格 CSS 实现表格边框效果。

    布局规则（参照加班申请等真实表单）：
    - 两列行：标签 span=6 + 控件 span=6 + 标签 span=4 + 控件 span=8
    - 单列整行：标签 span=6 + 控件 span=18
    - 标签列使用 `text` 控件（居中、16px），flex 垂直居中
    - 控件列的控件 hideTitle=True

    Args:
        rows: 每个 row 是一组 (widget_dict, key, model) tuple 或裸 widget dict
        cols_per_row: 每行放几个控件（1 或 2）

    Returns:
        grid dict
    """
    key = _gen_key()
    _sleep()

    columns = []

    for idx, item in enumerate(rows):
        if isinstance(item, tuple):
            w = item[0]
        else:
            w = item

        # 从 card 中提取内部控件
        inner = w
        if w.get('type') == 'card' and w.get('list') and len(w['list']) == 1:
            inner = w['list'][0]

        widget_name = inner.get('name', '')
        inner['hideTitle'] = True
        inner['hideLabel'] = True

        # 计算 span
        if cols_per_row == 2:
            if idx == 0:
                label_span, field_span = 6, 6
            else:
                label_span, field_span = 4, 8
        else:
            label_span, field_span = 6, 18

        # 标题列（text 控件，居中 16px）
        label_key = _gen_key()
        _sleep()
        label_widget = {
            "type": "text", "name": "文本",
            "className": "form-text", "icon": "icon-text",
            "hideLabel": True, "hideTitle": False,
            "options": {
                "text": widget_name, "width": "100%", "align": "center",
                "fontSize": 16, "fontColor": "#000000",
                "fontBold": False, "fontItalic": False,
                "fontUnderline": False, "fontLineThrough": False,
                "hidden": False, "required": False, "hiddenOnAdd": False,
                "verticalAlign": "top", "fieldNote": ""
            },
            "remoteAPI": {"url": "", "executed": False},
            "key": label_key, "model": f"text_{label_key}",
            "modelType": "main", "rules": [], "isSubItem": False
        }

        # 标签列 options：flex 垂直居中（textarea/hand-sign 等宽控件也居中）
        label_col_opts = {"flex": True, "flexAlignItems": "center", "flexJustifyContent": "start"}

        columns.append({
            "span": label_span,
            "list": [label_widget],
            "options": label_col_opts
        })

        # 控件列
        columns.append({
            "span": field_span,
            "list": [inner],
            "options": {"flex": True, "flexAlignItems": "center", "flexJustifyContent": "start"}
        })

    grid = {
        "type": "grid", "name": "栅格布局",
        "className": "form-grid form-grid-word-theme",
        "icon": "icon-grid",
        "hideLabel": True, "isContainer": True,
        "columns": columns,
        "options": {
            "gutter": 0, "justify": "start", "align": "top",
            "hidden": False, "required": False, "hiddenOnAdd": False,
            "isWordStyle": False, "isWordInnerGrid": False, "fieldNote": ""
        },
        "key": key, "model": f"grid_{key}",
        "rules": [], "hideTitle": False, "modelType": "main"
    }
    return grid


def _make_word_title(title_text):
    """创建 Word 风格表单顶部标题（text 控件，24px 加粗居中）"""
    key = _gen_key()
    _sleep()
    return {
        "type": "text", "name": "文本",
        "className": "form-text", "icon": "icon-text",
        "hideLabel": True, "hideTitle": False,
        "options": {
            "text": title_text, "width": "100%", "align": "center",
            "fontSize": 24, "fontColor": "#000000",
            "fontBold": True, "fontItalic": False,
            "fontUnderline": False, "fontLineThrough": False,
            "hidden": False, "required": False, "hiddenOnAdd": False,
            "verticalAlign": "top", "fieldNote": ""
        },
        "remoteAPI": {"url": "", "executed": False},
        "key": key, "model": f"text_{key}",
        "modelType": "main", "rules": [], "isSubItem": False
    }


def _make_word_divider_grid(item):
    """将分隔符包裹在 Word 风格的 grid 中（单列 span=24, isWordStyle=true）

    Word 布局下分隔符不使用标签+控件的两列格式，而是用一个占满整行的 grid 容器，
    内部放置 divider 控件，grid 设置 isWordStyle=true 以保持边框一致性。
    """
    if isinstance(item, tuple):
        w = item[0]
    else:
        w = item
    key = _gen_key()
    _sleep()
    grid = {
        "type": "grid", "name": "栅格布局",
        "className": "form-grid form-grid-word-theme",
        "icon": "icon-grid",
        "hideLabel": True, "isContainer": True,
        "columns": [{
            "span": 24,
            "list": [w],
            "options": {
                "flex": False,
                "flexAlignItems": "flex-start",
                "flexJustifyContent": "start",
            }
        }],
        "options": {
            "gutter": 0, "justify": "start", "align": "top",
            "hidden": False, "required": False, "hiddenOnAdd": False,
            "isWordStyle": True, "isWordInnerGrid": False, "fieldNote": ""
        },
        "key": key, "model": f"grid_{key}",
        "rules": [], "hideTitle": False, "modelType": "main"
    }
    return grid


def _apply_word_layout(widgets, form_name=''):
    """将 widgets 列表转换为 Word 风格布局（匹配 JeecgBoot 真实实现）

    真实 Word 风格特征：
    - 顶部有独立的 text 标题控件（24px 加粗居中）
    - 每行是 grid 容器，className = 'form-grid form-grid-word-theme'
    - 适合半行的控件两两配对（标签6+值6 | 标签4+值8）
    - textarea/file-upload/hand-sign 等宽控件独占一行（标签6+值18）
    - formStyle 设为 'word'，表单设计器内置 Word 风格 CSS 自动生效

    Args:
        widgets: 控件列表
        form_name: 表单名称（用于生成顶部标题，空则不生成）

    Returns:
        (new_top_items, all_models)
    """
    top_items = []
    all_models = []

    # 添加顶部标题
    if form_name:
        title_widget = _make_word_title(form_name)
        top_items.append(title_widget)

    half_buffer = None

    for item in widgets:
        wtype = _get_widget_type(item)

        if isinstance(item, tuple):
            key, model = item[1], item[2]
        else:
            key, model = item.get('key', ''), item.get('model', '')

        if _is_half_suitable(wtype):
            if half_buffer is None:
                half_buffer = (item, key, model)
            else:
                # 两个控件配对成一行
                grid = make_word_grid(half_buffer[0], item, cols_per_row=2)
                top_items.append(grid)
                all_models.append((half_buffer[1], half_buffer[2]))
                all_models.append((key, model))
                half_buffer = None
        else:
            # 先刷出缓冲区
            if half_buffer is not None:
                grid = make_word_grid(half_buffer[0], cols_per_row=1)
                top_items.append(grid)
                all_models.append((half_buffer[1], half_buffer[2]))
                half_buffer = None

            # 分隔符特殊处理：包裹在单列 span=24 的 grid 中，带 isWordStyle
            if wtype == 'divider':
                divider_grid = _make_word_divider_grid(item)
                top_items.append(divider_grid)
                all_models.append((key, model))
            else:
                # 宽控件独占一行
                grid = make_word_grid(item, cols_per_row=1)
                top_items.append(grid)
                all_models.append((key, model))

    if half_buffer is not None:
        grid = make_word_grid(half_buffer[0], cols_per_row=1)
        top_items.append(grid)
        all_models.append((half_buffer[1], half_buffer[2]))

    return top_items, all_models


def build_design_json(widgets, title_model, form_style='normal', expand=None,
                      config_overrides=None):
    """组装完整的 desformDesignJson

    Args:
        widgets: 顶层控件列表（card 包裹的和不需要 card 的混合）
        title_model: 标题字段的 model
        form_style: 表单风格 'normal' 或 'word'
            - 'normal': 默认风格
            - 'word': Word 风格（表单设计器内置 CSS 自动生效）
        expand: JS/CSS 增强配置 dict，格式: {"js": "...", "css": "...", "url": {"js": "...", "css": "..."}}
        config_overrides: dict，覆盖 config 中任意字段（最终 merge 到 config 上），例如:
            {"customRequestURL": [{"url": "https://..."}], "transactional": False}
    """
    is_word = (form_style == 'word')
    has_widgets = sorted(list(_collect_types(widgets)))

    # Word 风格：关闭自动栅格和顶部标题（内置 CSS 自动生效，无需加载外部 CSS）
    if is_word:
        base_expand = {"js": "", "css": "", "url": {"js": "", "css": ""}}
        show_header = False
        disabled_auto_grid = True
        dialog_top = 60
        dialog_width = 1100
        allow_print = True
    else:
        base_expand = {"js": "", "css": "", "url": {"js": "", "css": ""}}
        show_header = True
        disabled_auto_grid = False
        dialog_top = 20
        dialog_width = 1000
        allow_print = False

    # 合并用户传入的 expand 配置
    if expand:
        if expand.get('js'):
            base_expand['js'] = expand['js']
        if expand.get('css'):
            base_expand['css'] = expand['css']
        if expand.get('url'):
            if expand['url'].get('js'):
                base_expand['url']['js'] = expand['url']['js']
            if expand['url'].get('css'):
                base_expand['url']['css'] = expand['url']['css']
    expand = base_expand

    result = {
        "list": widgets,
        "config": {
            "formStyle": "word" if is_word else "normal",
            "titleField": title_model,
            "showHeaderTitle": show_header,
            "labelWidth": 100,
            "labelPosition": "top",
            "size": "small",
            "dialogOptions": {
                "top": dialog_top, "width": dialog_width,
                "padding": {"top": 25, "right": 25, "bottom": 30, "left": 25}
            },
            "disabledAutoGrid": disabled_auto_grid,
            "designMobileView": False,
            "enableComment": True,
            "hasWidgets": has_widgets,
            "defaultLoadLargeControls": False,
            "expand": expand,
            "transactional": True,
            "customRequestURL": [{"url": ""}],
            "disableMobileCss": True,
            "allowExternalLink": False,
            "externalLinkShowData": is_word,
            "headerImgUrl": "",
            "externalTitle": "",
            "enableNotice": False,
            "noticeMode": "external",
            "noticeType": "system",
            "noticeReceiver": "",
            "allowPrint": allow_print,
            "allowJmReport": False,
            "jmReportURL": "",
            "bizRuleConfig": [],
            "bigDataMode": False
        }
    }
    if config_overrides:
        result["config"].update(config_overrides)
    return result


def save_design(form_id, form_code, widgets, title_model, update_count=1, form_style='normal',
                expand=None, config_overrides=None):
    """保存表单设计到 API

    Args:
        form_id: 表单 ID
        form_code: 表单编码（用于日志）
        widgets: 顶层控件列表
        title_model: 标题字段 model
        update_count: 当前 updateCount（从 find_or_create_form 获取）
        form_style: 表单风格 'normal' 或 'word'
        expand: JS/CSS 增强配置 dict（可选），见 build_design_json
        config_overrides: dict，覆盖 config 中任意字段，例如:
            {"customRequestURL": [{"url": "https://..."}], "transactional": False}

    Returns:
        API 响应 dict
    """
    design_json = build_design_json(widgets, title_model, form_style, expand=expand,
                                    config_overrides=config_overrides)
    design_json = _auto_fill_linkdata_sqparam(design_json)
    payload = {
        'id': form_id,
        'desformDesignJson': json.dumps(design_json, ensure_ascii=False),
        'updateCount': update_count,
        'autoNumberDesignConfig': {'update': {}, 'current': {}},
        'refTableDefaultValDbSync': {'changes': {}, 'removeKeys': []}
    }
    result = api_request('/desform/edit', payload, method='PUT')

    if result.get('success'):
        print(f'  {form_code} 保存成功')
        return result

    msg = result.get('message', '')

    # 自动重试: 未找到对应实体 → ID 可能是旧的幽灵记录，清缓存后重新搜索
    if '未找到对应实体' in msg:
        print(f'  {form_code} ID={form_id} 无效，重新搜索...')
        _cache_remove(form_code)
        new_id, new_uc = _find_by_list(form_code)
        if new_id and new_id != form_id:
            payload['id'] = new_id
            payload['updateCount'] = new_uc
            result = api_request('/desform/edit', payload, method='PUT')
            if result.get('success'):
                print(f'  {form_code} 保存成功 (重试, ID={new_id})')
                return result

    # 自动重试: 版本过时 → updateCount 不匹配，逐个尝试 uc+1, uc+2, ...
    if '版本已过时' in msg or '版本过时' in msg:
        print(f'  {form_code} 版本过时(uc={update_count})，尝试递增...')
        _cache_remove(form_code)
        for try_uc in range(update_count + 1, update_count + 10):
            payload['updateCount'] = try_uc
            result = api_request('/desform/edit', payload, method='PUT')
            if result.get('success'):
                print(f'  {form_code} 保存成功 (uc={try_uc})')
                return result
            retry_msg = result.get('message', '')
            if '版本已过时' not in retry_msg and '版本过时' not in retry_msg:
                break

    raise RuntimeError(f'{form_code} 保存失败: {msg}')


# ============================================================
# 字段权限（auth）
# ============================================================

# 不创建权限的控件类型（容器 + 纯布局/展示元素）
_AUTH_SKIP_TYPES = {'card', 'grid', 'tabs', 'divider', 'text'}


def _recursive_all_widgets(data_list, handler, parent=None):
    """Python 版 recursiveAllWidget（参考 vue-form-making-jeecg/src/util/utils.js:208）

    遍历 design JSON 的 list，对每个控件调用 handler(item, parent)。
    容器控件会先递归其子控件，再对自身调用 handler。
    """
    for item in data_list:
        if item.get('isContainer'):
            if item.get('columns'):
                # grid / sub-table-design 等有 columns 的容器
                for col in item['columns']:
                    _recursive_all_widgets(col.get('list', []), handler, parent=item)
            elif item.get('type') == 'card':
                _recursive_all_widgets(item.get('list', []), handler, parent=item)
            elif item.get('type') == 'tabs':
                for pane in item.get('panes', []):
                    _recursive_all_widgets(pane.get('list', []), handler, parent=item)
        handler(item, parent)


def _build_auth_list(form_code, design_list, form_id=None):
    """从 design JSON 的 list 中提取所有需要权限控制的字段

    Args:
        form_code: 表单编码
        design_list: design JSON 的 list 数组（layout 变换后的最终结构）
        form_id: 表单ID（后端 desform_id 字段必填）

    Returns:
        auth 权限数组，可直接传给 addAuthBatch 接口
    """
    auth_items = []

    def handler(item, parent):
        wtype = item.get('type', '')
        if wtype in _AUTH_SKIP_TYPES or not wtype:
            return
        auth = {
            "desformCode": form_code,
            "desformId": form_id or "",
            "authComKey": item['key'],
            "authTitle": item.get('name', ''),
            "authField": item['model'],
            "subTable": bool(item.get('isSubItem', False)),
            "status": 0
        }
        if item.get('isSubItem') and parent:
            auth["subKey"] = parent['key']
            auth["subTitle"] = parent.get('name', '')
        auth_items.append(auth)

    _recursive_all_widgets(design_list, handler)
    return auth_items


def _collect_auth_keys(design_list):
    """从 design list 中收集所有需要权限的控件 key 集合"""
    keys = set()

    def handler(item, parent):
        wtype = item.get('type', '')
        if wtype not in _AUTH_SKIP_TYPES and wtype:
            keys.add(item['key'])

    _recursive_all_widgets(design_list, handler)
    return keys


def _query_existing_auth_keys(form_code):
    """查询表单已有的权限 key 集合

    Returns:
        set of authComKey
    """
    try:
        r = api_request(f'/desform/auth/query/{form_code}?permissionType=field&onlyEnabled=false', method='GET')
        if r.get('success') and r.get('result'):
            return {item['authComKey'] for item in r['result']}
    except Exception:
        pass
    return set()


def add_auth_batch(form_code, design_list, form_id=None):
    """批量新增字段权限（用于新建表单）

    Args:
        form_code: 表单编码
        design_list: design JSON 的 list 数组
        form_id: 表单ID（后端 desform_id 字段必填）

    Returns:
        API 响应 dict，无字段时返回 None
    """
    auth_list = _build_auth_list(form_code, design_list, form_id=form_id)
    if not auth_list:
        return None
    result = api_request('/desform/auth/addAuthBatch', auth_list, method='POST')
    if result.get('success'):
        print(f'  {form_code} 字段权限已创建 ({len(auth_list)} 个字段)')
    else:
        raise RuntimeError(f'权限创建失败: {result.get("message", "")}')
    return result


def _delete_auth_keys(form_code, keys_to_delete):
    """批量删除权限（按 authComKey）

    Args:
        form_code: 表单编码
        keys_to_delete: 要删除的 authComKey 集合
    """
    if not keys_to_delete:
        return
    keys_str = ','.join(keys_to_delete)
    r = api_request(
        f'/desform/auth/deleteBatchByAuthComKey?desformCode={form_code}&authComKeys={keys_str}',
        method='DELETE'
    )
    if r.get('success'):
        print(f'  {form_code} 已删除 {len(keys_to_delete)} 个旧字段权限')
    else:
        print(f'  [警告] {form_code} 删除旧字段权限失败: {r.get("message", "")}')


def sync_auth(form_code, design_list, form_id=None):
    """同步字段权限（用于更新表单）：新增新字段权限 + 删除已移除字段权限

    Args:
        form_code: 表单编码
        design_list: 新的 design JSON 的 list 数组
        form_id: 表单ID（后端 desform_id 字段必填）
    """
    new_keys = _collect_auth_keys(design_list)
    old_keys = _query_existing_auth_keys(form_code)

    # 需要新增的 key
    added_keys = new_keys - old_keys
    # 需要删除的 key
    removed_keys = old_keys - new_keys

    # 删除已移除的字段权限
    if removed_keys:
        _delete_auth_keys(form_code, removed_keys)

    # 新增新字段权限
    if added_keys:
        auth_list = _build_auth_list(form_code, design_list, form_id=form_id)
        new_auth_list = [a for a in auth_list if a['authComKey'] in added_keys]
        if new_auth_list:
            result = api_request('/desform/auth/addAuthBatch', new_auth_list, method='POST')
            if result.get('success'):
                print(f'  {form_code} 新增 {len(new_auth_list)} 个字段权限')
            else:
                raise RuntimeError(f'新增权限失败: {result.get("message", "")}')

    if not added_keys and not removed_keys:
        print(f'  {form_code} 字段权限无变化')


def save_auth_from_design(form_code):
    """查询已有表单设计并创建字段权限（用于重试）

    Args:
        form_code: 表单编码

    Returns:
        API 响应 dict
    """
    form = query_form(form_code)
    if not form or not form.get('desformDesignJson'):
        raise RuntimeError(f'表单 {form_code} 未找到或无设计数据')
    form_id = form.get('id', '')
    design = json.loads(form['desformDesignJson'])
    return add_auth_batch(form_code, design.get('list', []), form_id=form_id)


# ============================================================
# 菜单 SQL 生成（含授权 SQL）
# ============================================================

def _gen_id():
    """生成 32 位无横线 UUID 作为菜单/授权记录 ID"""
    return uuid.uuid4().hex


def gen_menu_sql(parent_name, children, role_id=None, icon='ant-design:appstore-outlined'):
    """生成菜单 + 授权 SQL

    Args:
        parent_name: 父菜单名称
        children: [(name, desform_code, sort), ...] 或 [(menu_id, name, desform_code, sort), ...] (兼容旧格式)
        role_id: 角色 ID（默认使用全局 ROLE_ID）
        icon: 父菜单图标（默认 'ant-design:appstore-outlined'）

    Returns:
        完整 SQL 字符串
    """
    rid = role_id or ROLE_ID
    lines = []
    parent_id = _gen_id()

    # 父菜单
    lines.append(f"""INSERT INTO sys_permission(id, parent_id, name, url, component, component_name, redirect, menu_type, perms, perms_type, sort_no, always_show, icon, is_route, is_leaf, keep_alive, hidden, hide_tab, description, status, del_flag, rule_flag, create_by, create_time, update_by, update_time, internal_or_external)
VALUES ('{parent_id}', NULL, '{parent_name}', '/{parent_id}', 'layouts/RouteView', NULL, NULL, 0, NULL, '1', 1.00, 0, '{icon}', 1, 0, 0, 0, 0, NULL, '1', 0, 0, 'admin', now(), NULL, NULL, 0);""")

    # 父菜单授权
    lines.append(f"""INSERT INTO sys_role_permission (id, role_id, permission_id, data_rule_ids, operate_date, operate_ip)
VALUES ('{_gen_id()}', '{rid}', '{parent_id}', NULL, now(), '127.0.0.1');""")

    # 子菜单
    for item in children:
        # 兼容旧格式 (menu_id, name, code, sort) 和新格式 (name, code, sort)
        if len(item) == 4:
            _, name, code, sort = item
        else:
            name, code, sort = item
        menu_id = _gen_id()
        lines.append(f"""
INSERT INTO sys_permission(id, parent_id, name, url, component, component_name, redirect, menu_type, perms, perms_type, sort_no, always_show, icon, is_route, is_leaf, keep_alive, hidden, hide_tab, description, status, del_flag, rule_flag, create_by, create_time, update_by, update_time, internal_or_external)
VALUES ('{menu_id}', '{parent_id}', '{name}', '/online/desform/list/{code}', 'super/online/desform/auto/AutoDesformDataList', 'AutoDesformDataList', NULL, 0, NULL, '1', {sort}.00, 0, NULL, 0, 1, 0, 0, 0, NULL, '1', 0, 0, 'admin', now(), NULL, NULL, 0);""")

        lines.append(f"""INSERT INTO sys_role_permission (id, role_id, permission_id, data_rule_ids, operate_date, operate_ip)
VALUES ('{_gen_id()}', '{rid}', '{menu_id}', NULL, now(), '127.0.0.1');""")

    return '\n'.join(lines)


# ============================================================
# 便捷函数：批量创建表单
# ============================================================

def query_form(code):
    """查询表单基本信息，返回 dict 或 None（带缓存）

    返回字段包括: id, desformCode, desformName, updateCount, desformDesignJson 等
    """
    fid, _ = get_form_id(code)
    if fid:
        try:
            r = api_request(f'/desform/queryById?id={fid}', method='GET')
            if r.get('success') and r.get('result'):
                # 更新缓存中的 updateCount
                _cache_put(code, fid, r['result'].get('updateCount', 0))
                return r['result']
        except Exception:
            pass
    return None


# ============================================================
# 设计 JSON 预处理工具（手动修改设计 JSON 再保存）
# ============================================================

def extract_field_table_from_design(design_json):
    """从设计 JSON 中提取字段参照表

    遍历整个 list 结构（包括 card/grid/tabs/sub-table），
    返回每个有效控件的 {name, key, model, type}。

    Args:
        design_json: desformDesignJson dict

    Returns:
        list[dict]  每项包含 name, key, model, type
    """
    rows = []

    def _visit(w, prefix=''):
        wtype = w.get('type', '')
        name = w.get('name', w.get('title', ''))
        key = w.get('key', '')
        model = w.get('model', '')

        # card 容器：透传，不记录自身
        if wtype == 'card':
            for inner in w.get('list', []):
                _visit(inner, prefix)
            return

        # grid 容器：透传
        if wtype == 'grid':
            for col in w.get('cols', []):
                for item in col.get('list', []):
                    _visit(item, prefix)
            return

        # tabs 容器：透传
        if wtype == 'tabs':
            for pane in w.get('list', []):
                for item in pane.get('list', []):
                    _visit(item, prefix)
            return

        # 子表：记录自身，再递归进入列
        if wtype == 'sub-table-design':
            if key and model:
                rows.append({'name': prefix + name, 'key': key, 'model': model, 'type': wtype})
            sub_prefix = f'  [{name}] '
            for col in w.get('columns', []):
                for sub_w in col.get('list', []):
                    _visit(sub_w, sub_prefix)
            return

        # 普通控件
        if key and model:
            rows.append({'name': prefix + name, 'key': key, 'model': model, 'type': wtype})

    for w in design_json.get('list', []):
        _visit(w)

    return rows


def export_design_json(code, output_path=None):
    """查询已有表单的设计 JSON 并导出到文件（预处理功能——用于修改表单场景）

    AI 可在修改后调用 save_design_from_file() 将修改保存到后台。

    Args:
        code: 表单编码
        output_path: 导出路径（可选，不传则自动生成临时文件）

    Returns:
        (file_path, field_rows)
        - file_path:   导出的文件路径
        - field_rows:  字段参照表 list[dict(name, key, model, type)]
    """
    import tempfile

    form_data = query_form(code)
    if not form_data:
        raise ValueError(f'表单 {code} 不存在')

    design_json_str = form_data.get('desformDesignJson', '{}')
    design_json = json.loads(design_json_str) if isinstance(design_json_str, str) else design_json_str

    if not output_path:
        tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False,
            encoding='utf-8', prefix=f'desform_{code}_'
        )
        output_path = tmp.name
        json.dump(design_json, tmp, ensure_ascii=False, indent=2)
        tmp.close()
    else:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(design_json, f, ensure_ascii=False, indent=2)

    field_rows = extract_field_table_from_design(design_json)

    print(f'\n[预处理] 表单 {code} 设计JSON已导出')
    print(f'  文件路径: {output_path}')
    print(f'\n  {"字段名称":<20} {"key":<35} {"model":<45} {"type"}')
    print(f'  {"-"*20} {"-"*35} {"-"*45} {"-"*15}')
    for row in field_rows:
        print(f'  {row["name"]:<20} {row["key"]:<35} {row["model"]:<45} {row["type"]}')
    print(f'\n修改完成后，调用 save_design_from_file("{code}", r"{output_path}") 保存')

    return output_path, field_rows


# linkData rules[].rule → superQueryType 映射
_LINKDATA_RULE_SQ_TYPE = {
    'EQ': 'eq', 'NE': 'ne',
    'IN': 'like', 'NOT_IN': 'not_like',
    'IS_ONE_OF': 'in', 'NOT_IS_ONE_OF': 'not_in',
    'EMPTY': 'empty', 'NOT_EMPTY': 'not_empty',
}


def _flatten_design_list(items):
    """展平设计 JSON 的 list 树（card 容器 → 实际控件）"""
    result = []
    for item in items:
        if item.get('type') == 'card':
            result.extend(_flatten_design_list(item.get('list', [])))
        else:
            result.append(item)
    return result


def _auto_fill_linkdata_sqparam(design_json):
    """自动填充设计 JSON 中所有 linkData 控件的 sqParam。

    遍历每个控件，发现 options.remote == 'linkData' 时：
    1. 调用 /desform/api/fields/{desformCode} 查询目标表字段
    2. 根据 rule 中的 model 匹配目标字段类型（同 getSuperQueryType 逻辑）
    3. 根据 rule code 查 superQueryType
    4. 写入 sqParam: {type: 目标字段类型, rule: superQueryType}
    """
    _fields_cache = {}
    modified = 0

    widgets = _flatten_design_list(design_json.get('list', []))
    for w in widgets:
        opts = w.get('options', {})
        cfg = opts.get('linkDataConfig')
        if not cfg or opts.get('remote') != 'linkData':
            continue
        rules = cfg.get('rules')
        if not rules:
            continue

        desform_code = cfg['desformCode']
        # 缓存目标表字段
        if desform_code not in _fields_cache:
            try:
                r = api_request(f'/desform/api/fields/{desform_code}', method='GET')
                if r.get('success'):
                    _fields_cache[desform_code] = r['result']['fields']
                else:
                    _fields_cache[desform_code] = []
            except Exception:
                _fields_cache[desform_code] = []

        target_fields = _fields_cache[desform_code]
        if not target_fields:
            continue

        for rule in rules:
            model = rule.get('model', '')
            # 匹配目标字段，返回 sqParam.type
            field_type = 'text'
            for f in target_fields:
                if f.get('model') == model or f.get('value') == model:
                    wtype = f.get('type', 'text')
                    # getSuperQueryType 等价逻辑
                    if wtype == 'formula':
                        fopts = f.get('options', {})
                        if fopts.get('type') == 'date':
                            field_type = 'input'
                        else:
                            field_type = 'number'
                    elif wtype == 'link-field':
                        field_type = f.get('options', {}).get('fieldType', 'text')
                    elif wtype == 'date':
                        field_type = f.get('options', {}).get('type', 'date')
                    else:
                        field_type = wtype
                    break

            rule_code = rule.get('rule', '')
            sq_type = _LINKDATA_RULE_SQ_TYPE.get(rule_code, 'eq')
            rule['sqParam'] = {'type': field_type, 'rule': sq_type}
            modified += 1

    if modified > 0:
        print(f'  已自动填充 {modified} 条 linkData sqParam')
    return design_json


def save_design_from_file(code, file_path):
    """从文件读取设计 JSON 并保存到后台（预处理功能的最后一步）

    适用于：
    - desform_creator.py --preprocess 生成临时文件，AI 修改后调用本函数保存
    - export_design_json() 导出后，AI 修改后调用本函数保存

    保存前会自动填充 linkData 控件的 sqParam，无需手工处理。

    Args:
        code:      表单编码
        file_path: 设计 JSON 文件路径

    Returns:
        API 响应 dict
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        design_json = json.load(f)

    # 自动填充 linkData 的 sqParam
    design_json = _auto_fill_linkdata_sqparam(design_json)

    # 获取最新 updateCount（避免版本冲突）
    form_data = query_form(code)
    if not form_data:
        raise ValueError(f'表单 {code} 不存在，无法保存设计JSON')

    fid = form_data['id']
    update_count = form_data.get('updateCount', 0)

    payload = {
        'id': fid,
        'desformDesignJson': json.dumps(design_json, ensure_ascii=False),
        'updateCount': update_count,
        'autoNumberDesignConfig': {'update': {}, 'current': {}},
        'refTableDefaultValDbSync': {'changes': {}, 'removeKeys': []}
    }
    result = api_request('/desform/edit', payload, method='PUT')

    if result.get('success'):
        print(f'  {code} 设计JSON保存成功')
        _cache_put(code, fid, update_count + 1)
        return result

    raise RuntimeError(f'{code} 设计JSON保存失败: {result.get("message", "未知错误")}')


# ============================================================
# designConfig 快捷更新
# ============================================================

def _deep_merge_config(base, updates):
    """递归深度合并 config dict（原地修改 base）

    合并规则：
    - updates 的值是 dict 且 base 中对应值也是 dict：递归合并（只覆盖指定子字段）
    - updates 的值是 list：整体替换（数组不做元素级合并）
    - 其他类型（str/int/bool/None）：直接覆盖
    - base 中不存在的 key：直接写入
    """
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge_config(base[key], value)
        else:
            # list、基本类型、None、以及 base 中不存在的 key 均整体替换
            base[key] = value


def update_design_config(code, config_updates):
    """快捷更新表单的 designConfig

    自动查询表单最新设计 JSON，深度合并 config_updates 后保存。
    适用于修改发布设置、填报通知、打印设置、业务规则等 config 字段，
    无需手动处理 updateCount 或完整的 designJson。

    合并规则（深度合并，非浅覆盖）：
    - dict 值：递归合并，只覆盖指定的子字段，其余子字段保持不变
      例如 {"dialogOptions": {"width": 800}} 只更新 width，不影响 top/padding
    - list 值：整体替换（bizRuleConfig、customRequestURL 等数组必须传完整内容）
    - 其他类型（str/int/bool/None）：直接覆盖

    Args:
        code:           表单编码
        config_updates: dict，要更新的 config 字段。示例：
            # 打印设置
            {"allowPrint": True, "disabledAutoGrid": False}
            # 填报通知
            {"enableNotice": True, "noticeMode": "always",
             "noticeType": "system,email", "noticeReceiver": "admin"}
            # 只更新 dialogOptions 中的 width（其余字段不变）
            {"dialogOptions": {"width": 800}}
            # 业务规则（数组整体替换，需传完整列表）
            {"bizRuleConfig": [...]}
            # 外部链接
            {"allowExternalLink": True, "externalTitle": "我的表单"}

    Returns:
        API 响应 dict

    Raises:
        ValueError:    表单不存在
        RuntimeError:  保存失败
    """
    form_data = query_form(code)
    if not form_data:
        raise ValueError(f'表单 {code} 不存在')

    fid = form_data['id']
    update_count = form_data.get('updateCount', 0)

    # 解析当前设计 JSON（可能是字符串或已解析的 dict）
    raw = form_data.get('desformDesignJson', '{}')
    if isinstance(raw, str):
        design_json = json.loads(raw) if raw.strip() else {}
    else:
        design_json = raw if raw else {}

    # 深度合并到当前 config
    current_config = design_json.get('config', {})
    _deep_merge_config(current_config, config_updates)
    design_json['config'] = current_config

    design_json = _auto_fill_linkdata_sqparam(design_json)
    payload = {
        'id': fid,
        'desformDesignJson': json.dumps(design_json, ensure_ascii=False),
        'updateCount': update_count,
        'autoNumberDesignConfig': {'update': {}, 'current': {}},
        'refTableDefaultValDbSync': {'changes': {}, 'removeKeys': []},
    }
    result = api_request('/desform/edit', payload, method='PUT')

    if result.get('success'):
        _cache_put(code, fid, update_count + 1)
        updated_keys = ', '.join(str(k) for k in config_updates.keys())
        print(f'  [{code}] designConfig 已更新: {updated_keys}')
        return result

    raise RuntimeError(
        f'[{code}] designConfig 更新失败: {result.get("message", "未知错误")}'
    )


def delete_form(code_or_id, form_id=None):
    """删除表单：逻辑删除 → 真实删除

    支持 3 种调用方式：
      delete_form('elder_person')              # 传 code，自动查找 ID
      delete_form('elder_person', '123456')     # 传 code + 已知 ID，跳过搜索
      delete_form(id='123456')                  # 只传 ID

    会自动处理同 code 多条记录的情况（全部删除）。
    删除后自动清除缓存。返回已删除的 ID 列表。
    """
    deleted_ids = []
    code = None

    # 判断传入的是 code 还是 ID
    if form_id:
        # 明确传了 form_id，code_or_id 就是 code
        code = code_or_id
        all_ids = [str(form_id)]
    elif code_or_id and str(code_or_id).isdigit() and len(str(code_or_id)) > 15:
        # 纯数字且长度>15，判定为 ID
        all_ids = [str(code_or_id)]
    else:
        # 传的是 code，需要查找 ID
        code = code_or_id
        all_ids = []

        # 优先从缓存获取
        cached_id, _ = _cache_get(code)
        if cached_id:
            all_ids.append(cached_id)

        # 再通过 queryByIdOrCode 快速查找
        try:
            r = api_request(f'/desform/queryByIdOrCode?desformCode={code}', method='GET')
            if r.get('success') and r.get('result') and r['result'].get('id'):
                qid = r['result']['id']
                if qid not in all_ids:
                    all_ids.append(qid)
        except Exception:
            pass

        # 如果快速查找没结果，再走 list 全量搜索兜底
        if not all_ids:
            page = 1
            while page <= 10:
                r = api_request(f'/desform/list?pageNo={page}&pageSize=100&column=createTime&order=desc', method='GET')
                if not r.get('success') or not r.get('result'):
                    break
                records = r['result'].get('records', [])
                if not records:
                    break
                for rec in records:
                    if rec.get('desformCode') == code:
                        all_ids.append(rec['id'])
                total = r['result'].get('total', 0)
                if page * 100 >= total:
                    break
                page += 1

    if not all_ids:
        print(f'  {code_or_id}: 未找到表单，无需删除')
        return deleted_ids

    for fid in all_ids:
        try:
            # Step 1: 逻辑删除
            r2 = api_request(f'/desform/deleteBatch?ids={fid}', method='DELETE')
            ok2 = r2.get('success', False)
            # Step 2: 真实删除
            r3 = api_request(f'/desform/recycleBin/deleteByIds?ids={fid}', method='DELETE')
            ok3 = r3.get('success', False)
            if ok2 and ok3:
                deleted_ids.append(fid)
                print(f'  {code_or_id}: 已删除 {fid}')
            else:
                print(f'  {code_or_id}: 删除 {fid} 部分失败 (deleteBatch={ok2}, recycleBin={ok3})')
        except Exception as e:
            print(f'  {code_or_id}: 删除 {fid} 异常: {e}')

    # 清除缓存
    if code:
        _cache_remove(code)
    return deleted_ids


def update_form(code, widgets, title_index=0, config_overrides=None):
    """修改已有表单设计：查询 → 重新保存设计 → 返回 (form_id, title_model)

    Args:
        code: 表单编码
        widgets: 新的控件列表（同 create_form 格式）
        title_index: 标题字段在 widgets 中的索引
        config_overrides: dict，覆盖 config 中任意字段，例如:
            {"customRequestURL": [{"url": "https://..."}], "transactional": False}
    """
    # 查询表单（带缓存）
    form_id, uc = get_form_id(code)
    if not form_id:
        raise RuntimeError(f'表单 {code} 不存在，无法更新')

    # 解包 widgets
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

    # 保存设计
    save_design(form_id, code, top_items, title_model, uc,
                config_overrides=config_overrides)
    # 更新缓存（updateCount 会被后端自动递增）
    _cache_put(code, form_id, uc + 1)
    print(f'  {code}: 已更新 (ID={form_id})')

    # 同步字段权限（新增 + 删除）
    try:
        sync_auth(code, top_items, form_id=form_id)
    except Exception as e:
        print(f'  [警告] {code} 字段权限同步失败: {e}')

    return form_id, title_model


def _is_half_suitable(widget_type):
    """判断控件是否适合半行布局（textarea/editor/markdown/file-upload/imgupload/sub-table-design 等宽控件不适合）"""
    wide_types = {'textarea', 'editor', 'markdown', 'file-upload', 'imgupload',
                  'sub-table-design', 'divider', 'map', 'hand-sign', 'grid', 'tabs'}
    return widget_type not in wide_types


def _get_widget_type(item):
    """从 widget tuple 或 dict 中获取控件类型"""
    if isinstance(item, tuple):
        w = item[0]
    else:
        w = item
    # card 容器：检查内部控件
    if w.get('type') == 'card' and w.get('list'):
        return w['list'][0].get('type', '')
    return w.get('type', '')


def _get_inner_widget(item):
    """从 card-wrapped tuple 中提取内部控件 dict"""
    if isinstance(item, tuple):
        w = item[0]
    else:
        w = item
    if w.get('type') == 'card' and w.get('list') and len(w['list']) == 1:
        return w['list'][0]
    return None


def _set_autowidth(widget, width):
    """设置控件的 autoWidth"""
    if 'options' in widget and isinstance(widget['options'], dict):
        widget['options']['autoWidth'] = width


def _apply_half_layout(widgets):
    """将 widgets 列表中适合的控件两两配对为半行布局

    规则：
    - textarea/editor/markdown/file-upload/imgupload/sub-table-design/divider 等保持整行
    - 其余控件两两配对到同一个 card 中，autoWidth 设为 50
    - 奇数个适合半行的控件时，最后一个保持整行

    Args:
        widgets: [(card_dict, key, model), ...] 或 dict 混合列表

    Returns:
        (new_top_items, all_models) — 重组后的顶层控件列表和 model 列表
    """
    top_items = []
    all_models = []
    half_buffer = None  # 缓存一个待配对的半行控件

    for item in widgets:
        wtype = _get_widget_type(item)
        inner = _get_inner_widget(item)

        if inner and _is_half_suitable(wtype):
            # 适合半行布局
            _set_autowidth(inner, 50)
            if isinstance(item, tuple):
                key, model = item[1], item[2]
            else:
                key, model = item.get('key', ''), item.get('model', '')

            if half_buffer is None:
                # 缓存等配对
                half_buffer = (inner, key, model)
            else:
                # 配对成功，合并到一个 card
                paired_card = make_card(half_buffer[0], inner)
                top_items.append(paired_card)
                all_models.append((half_buffer[1], half_buffer[2]))
                all_models.append((key, model))
                half_buffer = None
        else:
            # 不适合半行的控件，先刷出缓冲区
            if half_buffer is not None:
                _set_autowidth(half_buffer[0], 100)  # 恢复整行
                solo_card = make_card(half_buffer[0])
                top_items.append(solo_card)
                all_models.append((half_buffer[1], half_buffer[2]))
                half_buffer = None

            # 原样添加
            if isinstance(item, tuple):
                top_items.append(item[0])
                all_models.append((item[1], item[2]))
            else:
                top_items.append(item)
                all_models.append((item.get('key', ''), item.get('model', '')))

    # 刷出最后的缓冲区
    if half_buffer is not None:
        _set_autowidth(half_buffer[0], 100)
        solo_card = make_card(half_buffer[0])
        top_items.append(solo_card)
        all_models.append((half_buffer[1], half_buffer[2]))

    return top_items, all_models


#: 分节布局里必须独占整行、不能塞进 card 的控件类型
GROUP_WIDE_TYPES = {
    'sub-table-design', 'tabs', 'grid', 'editor', 'markdown', 'map',
    'hand-sign', 'file-upload', 'imgupload', 'textarea', 'divider', 'text',
    'buttons', 'border-card',
}


def _group_flatten(item):
    """把顶层条目拆成 [(字段控件, key, model), ...]。

    创建器给每个字段套了一层 card：建壳阶段是 `make_card(w)`（单元素），
    半行布局阶段是 `make_card(a, b)`（双元素）。**两层都要拆平**——只认单元素 card 的话，
    2 个字段会粘成一坨、名字读成 None（2026-09-17 实测：`[00]`/`[04]` 两张双子卡取不到名）。
    """
    if isinstance(item, tuple):
        w, k, m = item[0], item[1], item[2]
    else:
        w, k, m = item, item.get('key', ''), item.get('model', '')
    if w.get('type') == 'card' and w.get('list'):
        out = []
        for c in w['list']:
            out.append((c, c.get('key', ''), c.get('model', '')))
        return out
    return [(w, k, m)]


def make_group_card(inners):
    """把若干字段控件装进一个 `isAutoGrid` 卡片，并均分列宽（线上模版实测：N 个字段 → autoWidth=100/N）。"""
    n = len(inners) or 1
    aw = round(100.0 / n, 3)
    for w in inners:
        opts = w.setdefault('options', {})
        opts['autoWidth'] = aw
        opts.setdefault('width', '100%')
    key = _gen_key()
    _sleep()
    return {
        'hideTitle': False,
        'options': {'hidden': False, 'hiddenOnAdd': False, 'fieldNote': '',
                    'required': False},
        'isContainer': True,
        'model': f'card_{key}',
        'modelType': 'main',
        'type': 'card',
        'isAutoGrid': True,
        'key': key,
        'list': list(inners),
    }


def apply_group_layout(widgets, sections, per_card=3):
    """按业务分节重排顶层控件 → `divider` 段标题 + `card`（每卡 ≤ per_card 个字段）。

    线上进销存模版实测的形态：顶层不是一长串「一个字段一张卡」，而是

        divider「采购订单信息」 → card[选择采购订单, 采购订单名称, 采购订单编码]
        divider「退货产品明细」 → link-record …（宽控件独占整行）

    2026-09-17 实测差异：批量建出来的表是 **20 张 card 平铺、零 divider、每卡 1 字段**——
    因为「补丁阶段」追加的字段各自单独成卡，而分节信息从头到尾没人发过。

    Args:
        widgets: 顶层控件列表（card 包裹的 tuple 和裸控件混合），即创建器产出的形状
        sections: `[{"标题": "采购订单信息", "字段": ["选择采购订单", ...]}, ...]`
                  「字段」写**控件名**（name/label）。名单不必穷尽——没点名的字段
                  按原顺序收在最后一节「其他信息」里，不会被丢。
        per_card: 一张 card 里最多放几个字段（模版实测众数是 3）

    Returns:
        (top_items, all_models) —— 与 `_apply_half_layout` 同形，可直接喂 build_design_json

    Raises:
        KeyError: 分节里写了表里没有的字段名（**早报**，不要静默少放一个字段）
    """
    flat = []
    for it in widgets:
        flat.extend(_group_flatten(it))              # [(w, key, model), ...]
    taken = set()
    top, models = [], []

    def flush(buf, meta):
        if not buf:
            return
        top.append(make_group_card(buf))
        models.extend(meta)

    def put(w, k, m, buf, meta):
        if w.get('type') in GROUP_WIDE_TYPES:
            flush(buf, meta)
            del buf[:], meta[:]
            top.append(w)
            models.append((k, m))
        else:
            buf.append(w)
            meta.append((k, m))

    for sec in (sections or []):
        title = (sec.get('标题') or '').strip()
        if title:
            dw, _, _ = DIVIDER(title)
            top.append(dw)
        buf, meta = [], []
        for fname in (sec.get('字段') or []):
            hit = None
            for i, (w, k, m) in enumerate(flat):
                if i in taken:
                    continue
                if w.get('name') == fname:
                    hit = i
                    break
            if hit is None:
                raise KeyError('分节「%s」里的字段「%s」在这张工作表里找不到（改名了？还是写错了？）'
                               % (title or '(无标题)', fname))
            taken.add(hit)
            put(flat[hit][0], flat[hit][1], flat[hit][2], buf, meta)
            if len(buf) >= per_card:
                flush(buf, meta)
                del buf[:], meta[:]
        flush(buf, meta)

    rest = [(w, k, m) for i, (w, k, m) in enumerate(flat) if i not in taken]
    if rest:
        buf, meta = [], []
        for w, k, m in rest:
            put(w, k, m, buf, meta)
            if len(buf) >= per_card:
                flush(buf, meta)
                del buf[:], meta[:]
        flush(buf, meta)
    return top, models


def create_form(name, code, widgets, title_index=0, layout='auto', expand=None,
                config_overrides=None, app_menu_group_id=None, sections=None):
    """一站式创建表单：查找/创建 → 保存设计 → 返回 (form_id, title_model)

    Args:
        name: 表单名称
        code: 表单编码
        widgets: 顶层控件列表（card 包裹的 tuple 和裸控件 tuple 混合）
        title_index: 标题字段在 widgets 中的索引
        layout: 布局模式
            - 'auto': 字段数 >= 6 时自动使用半行布局（默认）
            - 'half': 强制半行布局
            - 'full': 强制整行布局（不做半行处理）
            - 'word': Word 风格布局（带边框表格样式）
        expand: JS/CSS 增强配置 dict（可选），格式:
            {"js": "...", "css": "...", "url": {"js": "...", "css": "..."}}
        config_overrides: dict，覆盖 config 中任意字段，例如:
            {"customRequestURL": [{"url": "https://..."}], "transactional": False}
        app_menu_group_id: lowApp 模式下的工作表分组ID（由 desform_lowapp_utils 传入）

    Returns:
        (form_id, title_model)
    """
    form_style = 'word' if layout == 'word' else 'normal'

    if layout == 'word':
        top_items, all_models = _apply_word_layout(widgets, form_name=name)
    elif sections:
        # 有业务分节就走分节（divider + card），压过 'auto'/'half'——
        # 那两个只会在「一个字段一张卡」和「两两配对」之间选，都出不了分节
        top_items, all_models = apply_group_layout(widgets, sections)
    elif layout == 'half' or (layout == 'auto' and len(widgets) >= 6):
        top_items, all_models = _apply_half_layout(widgets)
    else:
        # 原有逻辑：逐个解包
        top_items = []
        all_models = []
        for item in widgets:
            if isinstance(item, tuple):
                top_items.append(item[0])
                all_models.append((item[1], item[2]))
            else:
                top_items.append(item)
                all_models.append((item.get('key', ''), item.get('model', '')))

    # 确定标题字段
    title_model = all_models[title_index][1] if title_index < len(all_models) else all_models[0][1]

    # 查找或创建
    form_id, uc, actual_code = find_or_create_form(name, code, app_menu_group_id=app_menu_group_id)
    print(f'  ID={form_id}, success=True')

    # 保存设计
    save_design(form_id, actual_code, top_items, title_model, uc, form_style, expand=expand,
                config_overrides=config_overrides)
    # 更新缓存
    _cache_put(actual_code, form_id, uc + 1)

    # 自动创建字段权限
    try:
        add_auth_batch(actual_code, top_items, form_id=form_id)
    except Exception as e:
        print(f'  [警告] {actual_code} 字段权限创建失败: {e}')

    return form_id, title_model


# ============================================================
# 表单复制
# ============================================================
def copy_form(source_code, new_code=None):
    """复制表单

    Args:
        source_code: 源表单编码
        new_code: 新表单编码（可选，不传则自动生成）

    Returns:
        新表单信息 dict

    注意:
        后端 LowAppCopyMenu 不支持 newFormName 参数，新表单名称由后端自动生成。
    """
    body = {"originFormCode": source_code}
    if new_code:
        body["newFormCode"] = new_code
    r = api_request('/desform/api/copyDesignForm', data=body, method='PUT')
    if r.get('success'):
        print(f"[copy_form] 复制成功: {source_code} → {new_code or '(自动编码)'}")
        return r.get('result')
    else:
        raise RuntimeError(f"复制失败: {r.get('message', '未知错误')}")


# ============================================================
# 版本管理
# ============================================================
def create_version(code, remarks=''):
    """为表单创建版本快照

    Args:
        code: 表单编码
        remarks: 版本备注
    """
    # desformCode 是 @RequestParam（URL 参数），remarks 在 body 中
    import urllib.parse
    encoded_code = urllib.parse.quote(code, safe='')
    r = api_request(f'/desform/version/create?desformCode={encoded_code}', data={
        "remarks": remarks
    })
    if r.get('success'):
        print(f"[create_version] 版本创建成功: {code}")
    else:
        print(f"[create_version] 版本创建失败: {r.get('message', '')}")
    return r


def list_versions(code, page=1, size=10):
    """列出表单版本历史"""
    r = api_request(f'/desform/version/list?desformCode={code}&pageNo={page}&pageSize={size}', method='GET')
    if r.get('success') and r.get('result'):
        return r['result'].get('records', [])
    return []


# ============================================================
# 视图创建
# ============================================================
def create_view(parent_code, view_name, view_code, design_json=None, is_mobile=False):
    """创建子视图（desformType=2）

    Args:
        parent_code: 主视图编码
        view_name: 视图名称
        view_code: 视图编码
        design_json: 设计JSON字符串（不传则复制主视图）
        is_mobile: 是否设为移动端视图
    """
    # 获取主视图信息
    parent_id, _ = get_form_id(parent_code)
    if not parent_id:
        raise RuntimeError(f"主视图不存在: {parent_code}")

    # 如果没有传 design_json，复制主视图的设计
    if design_json is None:
        parent_form = query_form(parent_code)
        if parent_form and parent_form.get('desformDesignJson'):
            design_json = parent_form['desformDesignJson']
        else:
            raise RuntimeError(f"无法获取主视图设计JSON: {parent_code}")

    # 移动端视图设置
    if is_mobile:
        import json as _json
        dj = _json.loads(design_json) if isinstance(design_json, str) else design_json
        dj['config']['designMobileView'] = True
        design_json = _json.dumps(dj, ensure_ascii=False)

    body = {
        "desformName": view_name,
        "desformCode": view_code,
        "desformType": 2,
        "parentId": parent_id,
        "parentCode": parent_code,
        "izMobileView": 1 if is_mobile else 0,
        "desformDesignJson": design_json if isinstance(design_json, str) else json.dumps(design_json, ensure_ascii=False),
    }
    r = api_request('/desform/add', data=body)
    if r.get('success'):
        print(f"[create_view] 视图创建成功: {view_code} (mobile={is_mobile})")
        return r.get('result')
    else:
        raise RuntimeError(f"视图创建失败: {r.get('message', '未知错误')}")


# ============================================================
# 列表视图（addView）
# ============================================================

def add_list_view_table(code, name=None):
    """为表单创建表格列表视图

    系统在创建表单时会自动生成默认表格视图；只有用户明确要求时才需调用本函数。

    Args:
        code: 表单编码
        name: 视图名称（可选，不传由后台自动生成）

    Returns:
        新建视图 ID（字符串）
    """
    body = {"type": "base", "code": code}
    if name is not None:
        body["name"] = name
    r = api_request('/desform/view/addView', data=body)
    if r.get('success'):
        view_id = r.get('result') or r.get('message')
        print(f'  [add_list_view_table] 表格视图创建成功: {code} (viewId={view_id})')
        return view_id
    raise RuntimeError(f'表格视图创建失败: {r.get("message", "未知错误")}')


def add_list_view_board(code, group_field=None, title_field=None, name=None):
    """为表单创建看板列表视图（也称卡片视图）

    数据按 group_field 的字段值分列展示。分组字段仅支持：
      单选(radio)、下拉(select)、开关(switch)、人员(select-user/create_by/update_by)、
      表字典(table-dict)、关联记录单条(link-record)、系统字段 bpm_status。
      必须非多选；不含部门、他表字段仅显示。

    Args:
        code:         表单编码
        group_field:  分组字段 model（不传默认使用 create_by）
        title_field:  标题字段 model（不传则自动从表单 config.titleField 获取）
        name:         视图名称（可选，不传由后台自动生成）

    Returns:
        新建视图 ID（字符串）
    """
    if group_field is None:
        group_field = 'create_by'

    if title_field is None:
        title_field = _get_title_key(code)

    body = {
        "type": "card",
        "code": code,
        "groupField": group_field,
        "filterGroupType": "all",
        "titleField": title_field,
    }
    if name is not None:
        body["name"] = name
    r = api_request('/desform/view/addView', data=body)
    if r.get('success'):
        view_id = r.get('result') or r.get('message')
        print(f'  [add_list_view_board] 看板视图创建成功: {code} (viewId={view_id}, groupField={group_field})')
        return view_id
    raise RuntimeError(f'看板视图创建失败: {r.get("message", "未知错误")}')


def _build_calendar_column_list(date_columns):
    """把 date_columns（begin_field/end_field/tag/field_type）转成后端 calendarColumnList。"""
    calendar_column_list = []
    for seq, col in enumerate(date_columns):
        entry = {
            "beginDateField": col['begin_field'],
            "tag": col['tag'],
            "seq": seq,
            "type": col['field_type'],
        }
        if col.get('end_field'):
            entry['endDateField'] = col['end_field']
        calendar_column_list.append(entry)
    return calendar_column_list


def add_list_view_calendar(code, date_columns, title_field=None, name=None):
    """为表单创建日历列表视图

    Args:
        code:          表单编码
        date_columns:  日期列配置列表，每项为 dict：
                         begin_field  (str, 必填) 开始日期字段 model
                         end_field    (str, 可选) 结束日期字段 model；不填则仅显示单个日期点
                         tag          (str, 必填) 分组标识，≤5 个字
                         field_type   (str, 必填) 字段类型："date" 或 "datetime"
                       示例（两组）：
                         [
                           {"begin_field": "date_xxx", "end_field": "date_yyy",
                            "tag": "计划", "field_type": "date"},
                           {"begin_field": "create_time", "tag": "创建", "field_type": "datetime"},
                         ]
        title_field:   标题字段 model（不传则自动从表单 config.titleField 获取）
        name:          视图名称（可选，不传由后台自动生成）

    Returns:
        新建视图 ID（字符串）
    """
    if title_field is None:
        title_field = _get_title_model(code)

    calendar_column_list = _build_calendar_column_list(date_columns)

    body = {
        "type": "calendar",
        "code": code,
        "titleField": title_field,
        "calendarColumnList": calendar_column_list,
    }
    if name is not None:
        body["name"] = name
    r = api_request('/desform/view/addView', data=body)
    if r.get('success'):
        view_id = r.get('result') or r.get('message')
        print(f'  [add_list_view_calendar] 日历视图创建成功: {code} (viewId={view_id}, {len(calendar_column_list)} 组日期)')
        return view_id
    raise RuntimeError(f'日历视图创建失败: {r.get("message", "未知错误")}')


def config_calendar_columns(view_id, date_columns):
    """更新已有日历视图的日期组（整表替换 calendarColumnList）

    date_columns 格式与 add_list_view_calendar 完全相同（begin_field/end_field/tag/field_type）。
    不要把 begin_field 直接传给 update_list_view——后端字段名是 beginDateField。

    Args:
        view_id:       日历视图 ID
        date_columns:  完整日期组列表；多组时传入全部组，不是增量补丁

    Returns:
        API 响应 dict
    """
    return update_list_view(
        view_id, calendarColumnList=_build_calendar_column_list(date_columns)
    )


def add_list_view_gantt(code, start_field, end_field, field_type='date',
                        default_view='day', title_field=None, name=None):
    """为表单创建甘特图列表视图

    Args:
        code:          表单编码
        start_field:   开始日期字段 model（必填，不可与 end_field 相同）
        end_field:     结束日期字段 model（必填，不可与 start_field 相同）
        field_type:    日期类型 "date" 或 "datetime"（默认 "date"）
        default_view:  默认视图模式（默认 "day"）
        title_field:   标题字段 model（不传则自动从表单 config.titleField 获取）
        name:          视图名称（可选，不传由后台自动生成）

    Returns:
        新建视图 ID（字符串）
    """
    if start_field == end_field:
        raise ValueError('start_field 和 end_field 不能相同')

    if title_field is None:
        title_field = _get_title_model(code)

    body = {
        "type": "gantt",
        "code": code,
        "titleField": title_field,
        "ganttFields": {
            "beginDateField": start_field,
            "endDateField": end_field,
            "dateType": field_type,
            "defaultView": default_view,
        },
    }
    if name is not None:
        body["name"] = name
    r = api_request('/desform/view/addView', data=body)
    if r.get('success'):
        view_id = r.get('result') or r.get('message')
        print(f'  [add_list_view_gantt] 甘特图视图创建成功: {code} (viewId={view_id})')
        return view_id
    raise RuntimeError(f'甘特图视图创建失败: {r.get("message", "未知错误")}')


def query_list_views(code):
    """查询表单下所有列表视图的精简信息（id、name、type、seq）

    Args:
        code: 表单编码

    Returns:
        list of dict，每项包含 id、name、type、seq
    """
    r = api_request(f'/desform/view/queryByCodeLite?code={code}', method='GET')
    if r.get('success'):
        return r.get('result', [])
    raise RuntimeError(f'查询列表视图失败: {r.get("message", "未知错误")}')


def query_list_view_by_id(view_id):
    """根据视图 ID 查询该视图的完整配置

    Args:
        view_id: 视图 ID

    Returns:
        dict，视图完整配置；视图不存在时抛出 RuntimeError
    """
    r = api_request(f'/desform/view/queryById?id={view_id}', method='GET')
    if r.get('success'):
        return r.get('result')
    raise RuntimeError(f'查询视图失败: {r.get("message", "未知错误")}')


def delete_list_view(view_id):
    """删除列表视图

    Args:
        view_id: 要删除的视图 ID

    Returns:
        API 响应 dict
    """
    r = api_request(f'/desform/view/removeView?id={view_id}', method='GET')
    if r.get('success'):
        print(f'  [delete_list_view] 视图删除成功: viewId={view_id}')
        return r
    raise RuntimeError(f'列表视图删除失败: {r.get("message", "未知错误")}')


def sort_list_view(view_id, after):
    """将指定列表视图移动到某视图之后（简单排序）

    Args:
        view_id: 要移动的视图 ID
        after:   排在哪个视图之后的视图 ID；传 "first" 则移到最前面

    Returns:
        API 响应 dict
    """
    r = api_request(f'/desform/view/sortView?id={view_id}&after={after}', method='POST')
    if r.get('success'):
        print(f'  [sort_list_view] 视图排序成功: viewId={view_id} after={after}')
        return r
    raise RuntimeError(f'列表视图排序失败: {r.get("message", "未知错误")}')


def reset_list_view_order(view_ids):
    """完全重排序：按传入顺序重置所有列表视图的 seq

    需要先用 query_list_views(code) 获取所有视图 ID，
    再按期望顺序传入本函数。

    Args:
        view_ids: 视图 ID 列表，顺序即为最终排列顺序（seq 从 1 开始自动分配）

    Returns:
        API 响应 dict

    示例:
        views = query_list_views('<form_code>')
        ids = [v['id'] for v in views]          # 当前顺序
        ids.insert(0, ids.pop(2))               # 把第3个移到最前
        reset_list_view_order(ids)
    """
    order_list = [{"id": vid, "seq": seq + 1} for seq, vid in enumerate(view_ids)]
    body = {"list": order_list}
    r = api_request('/desform/view/resetOrder', data=body)
    if r.get('success'):
        print(f'  [reset_list_view_order] 视图重排序成功: {len(view_ids)} 个视图')
        return r
    raise RuntimeError(f'列表视图重排序失败: {r.get("message", "未知错误")}')


def config_table_base(view_id, line_height=None, auto_refresh=None, has_summary=None,
                      auto_submit_bpm=None, show_column=None, fixed_column_num=None,
                      column_list=None, show_column_list=None):
    """配置表格视图的基础设置

    Args:
        view_id:          视图 ID
        line_height:      行高，'small'（紧凑）| 'middle'（中等）| 'large'（高），默认 'middle'
        auto_refresh:     自动刷新间隔秒数，0=关闭，最小 3；常用预设：30/60/120/180/240/300
        has_summary:      bool，是否开启数据统计
        auto_submit_bpm:  bool，新增数据后是否自动提交关联流程
        show_column:      显示列模式，'default'（与表单字段一致）| 'diy'（自定义）
        fixed_column_num: int，冻结前 N 列，0=不冻结
        column_list:      自定义列配置，格式：[{"field": "字段key", "show": True/False, "seq": 0}, ...]
                          定义字段顺序和基础可见性。
                          不传时：show_column='diy' 模式下系统默认显示所有非大字段控件（无 50 个上限）；
                          传入时：按列表精确控制每个字段的可见性和顺序。
        show_column_list: 可见性覆盖列表，优先级高于 column_list 中的 show 值
                          格式：[{"field": "字段key", "show": True/False}, ...]
                          当 column_list 和 show_column_list 对同一字段的 show 冲突时，
                          以 show_column_list 的值为准

    Returns:
        API 响应 dict

    示例:
        # 只改行高
        config_table_base(view_id, line_height='small')

        # 切换为自定义列模式，同时指定字段顺序和可见性
        config_table_base(
            view_id,
            show_column='diy',
            column_list=[
                {"field": "input_name", "show": True,  "seq": 0},
                {"field": "select_status", "show": True,  "seq": 1},
                {"field": "date_due",   "show": False, "seq": 2},
            ]
        )

        # 通过 show_column_list 覆盖部分字段的可见性
        config_table_base(
            view_id,
            show_column='diy',
            column_list=[{"field": "input_name", "show": True, "seq": 0}],
            show_column_list=[{"field": "input_name", "show": False}]  # 覆盖，最终不可见
        )
    """
    if auto_refresh is not None and auto_refresh != 0 and auto_refresh < 3:
        raise ValueError('auto_refresh 最小值为 3 秒，传 0 表示关闭')

    params = {}
    if line_height is not None:
        params['lineHeight'] = line_height
    if auto_refresh is not None:
        params['autoRefresh'] = auto_refresh
    if has_summary is not None:
        params['hasSummary'] = has_summary
    if auto_submit_bpm is not None:
        params['autoSubmitBpm'] = auto_submit_bpm
    if show_column is not None:
        params['showColumn'] = show_column
    if fixed_column_num is not None:
        params['fixedColumnNum'] = fixed_column_num
    if column_list is not None:
        params['columnList'] = column_list
    if show_column_list is not None:
        params['showColumnList'] = show_column_list

    return update_list_view(view_id, **params)


# 系统字段固定顺序（与前端 systemFieldDataList 一致）
_SYSTEM_FIELDS_SEQ = {
    'create_time':  100,
    'create_by':    101,
    'update_time':  102,
    'update_by':    103,
    'sys_org_code': 104,
    'bpm_status':   105,
}


def config_table_system_columns(view_id, show_fields):
    """配置表格视图的系统字段显隐（仅适用于 show_column='default' 模式）

    通过 systemColumnList 控制系统字段显隐，该字段仅在 show_column='default' 时生效。
    若当前视图为 show_column='diy' 模式，本函数无效——此时需将系统字段直接写入
    column_list，通过 config_table_base(view_id, column_list=[...]) 来控制显隐。

    showColumnList 不参与系统字段的显示与隐藏控制，无论哪种模式均如此。

    系统字段在 default 模式下的默认可见性：
      bpm_status（流程状态）：默认显示
      create_time / create_by / update_time / update_by / sys_org_code：默认隐藏

    Args:
        view_id:      视图 ID
        show_fields:  要显示的系统字段名列表，从以下 6 个中选：
                        'create_time' （创建时间）
                        'create_by'   （创建人）
                        'update_time' （修改时间）
                        'update_by'   （修改人）
                        'sys_org_code'（所属部门）
                        'bpm_status'  （流程状态）
                      未包含在列表中的字段将被设为隐藏。

    Returns:
        API 响应 dict

    示例:
        # 只显示创建时间和创建人
        config_table_system_columns(view_id, show_fields=['create_time', 'create_by'])

        # 全部隐藏
        config_table_system_columns(view_id, show_fields=[])

        # 全部显示
        config_table_system_columns(view_id, show_fields=list(_SYSTEM_FIELDS_SEQ.keys()))
    """
    show_set = set(show_fields)
    invalid = show_set - set(_SYSTEM_FIELDS_SEQ.keys())
    if invalid:
        raise ValueError(f'不支持的系统字段：{invalid}，可选值：{list(_SYSTEM_FIELDS_SEQ.keys())}')

    system_column_list = [
        {"field": field, "show": field in show_set, "seq": seq}
        for field, seq in _SYSTEM_FIELDS_SEQ.items()
    ]
    return update_list_view(view_id, systemColumnList=system_column_list)


def config_table_sort(view_id, orders):
    """配置视图默认排序（表格/看板/日历/甘特图通用）

    Args:
        view_id: 视图 ID
        orders:  排序规则列表，格式：
                   [{"field": "字段model名", "type": "asc"/"desc"}, ...]
                 升降序键是 type（与界面保存一致），不要用 order。
                 传 [] 清空排序。多条按列表顺序生效。

    Returns:
        API 响应 dict

    示例:
        config_table_sort(view_id, orders=[
            {"field": "date_due",   "type": "asc"},
            {"field": "select_priority", "type": "desc"},
        ])
        config_table_sort(view_id, orders=[])  # 清空
    """
    norm = []
    for item in orders or []:
        direction = item.get('type') or item.get('order') or 'asc'
        norm.append({"field": item.get('field', ''), "type": direction})
    return update_list_view(view_id, orders=norm)


def config_table_quick_filter(view_id, query_list, query_button=True, wait_query=False):
    """配置表格视图的快速筛选栏

    Args:
        view_id:      视图 ID
        query_list:   筛选字段列表，格式：
                        [{"field": "字段model名", "name": "显示名称",
                          "type": "控件类型", "query_type": "查询方式", "seq": 0}, ...]
        query_button: bool，是否显示查询按钮（默认 True）
        wait_query:   bool，是否等待点击查询后才加载数据（默认 False）

    Returns:
        API 响应 dict

    示例:
        config_table_quick_filter(view_id, query_list=[
            {"field": "input_name", "name": "姓名", "type": "input", "query_type": "like", "seq": 0},
            {"field": "select_status", "name": "状态", "type": "select", "query_type": "=", "seq": 1},
        ])
    """
    return update_list_view(view_id, queryList=query_list,
                            queryButton=query_button, waitQuery=wait_query)


def config_table_left_filter(view_id, left_filter_field=None, left_filter_data='all',
                              left_filter_order='desc', left_filter_condition=None,
                              add_form_default_status=True):
    """配置表格视图的筛选列表（左侧分组筛选栏）

    Args:
        view_id:                视图 ID
        left_filter_field:      左侧筛选字段 model（字段 key）
        left_filter_data:       筛选数据范围，'all'（全部）| 'part'（部分）| 'exist'（有数据），默认 'all'
        left_filter_order:      筛选项排序方向，'asc' | 'desc'（默认 'desc'）
        left_filter_condition:  附加过滤条件（字符串，可不传）
        add_form_default_status: bool，新增表单时是否默认选中当前筛选项（默认 True）

    Returns:
        API 响应 dict

    示例:
        config_table_left_filter(
            view_id,
            left_filter_field='select_status',
            left_filter_data='exist',
            left_filter_order='asc',
        )
    """
    params = {
        'leftFilterData': left_filter_data,
        'leftFilterOrder': left_filter_order,
        'addFormDefaultStatus': add_form_default_status,
    }
    if left_filter_field is not None:
        params['leftFilterField'] = left_filter_field
    if left_filter_condition is not None:
        params['leftFilterCondition'] = left_filter_condition

    return update_list_view(view_id, **params)


def config_view_data_filter(view_id, conditions, match_type='and'):
    """配置视图的数据过滤（sjgl）——限制此视图只显示满足条件的记录

    支持所有视图类型（表格、看板、日历、甘特图）。

    Args:
        view_id:     视图 ID
        conditions:  过滤条件，支持两种格式：

          格式一：简单列表（所有条件放在同一个分组内）
            [
                {"field": "select_xxx", "rule": "eq",   "val": "初一", "type": "select", "name": "年级"},
                {"field": "number_xxx", "rule": "gt",   "val": 10,     "type": "number", "name": "年龄"},
            ]

          格式二：分组列表（多个条件分组，每组内部有自己的 match_type）
            [
                {
                    "match_type": "or",
                    "items": [
                        {"field": "input_xxx", "rule": "like", "val": "王", "type": "input", "name": "姓名"},
                        {"field": "input_xxx", "rule": "like", "val": "张", "type": "input", "name": "姓名"},
                    ]
                },
                {
                    "match_type": "and",
                    "items": [
                        {"field": "number_xxx", "rule": "gt", "val": 3,  "type": "number", "name": "年龄"},
                        {"field": "number_xxx", "rule": "lt", "val": 50, "type": "number", "name": "年龄"},
                    ]
                }
            ]

        match_type:  多个分组之间的关系，'and'（且）或 'or'（或），默认 'and'
                     只有 conditions 为分组列表（格式二）且有多个分组时才生效

    每个过滤条件项的字段说明：
        field:  字段的 model（如 select_1775221412376_152628）或系统字段（如 create_time）
        rule:   比较规则，按字段类型有所不同，见下方规则表
        val:    比较值；rule 为 'empty'/'not_empty' 时传 '' 或 None
        type:   字段控件类型（如 input、select、number、date 等）
        name:   字段中文名（可选，用于界面展示）

    规则（rule）速查表：
        文本类（input/textarea/auto-number 等默认）:
            like（包含）、eq（等于）、right_like（以..开始）、left_like（以..结尾）、
            in（在...中）、ne（不等于）、like_with_and（多词匹配）、empty、not_empty

        数值/时间类（number/integer/money/rate/slider/formula/summary/
                     date/datetime/datetime_s/datetime_sf/time/year/month/quarter/week）:
            eq、ne、gt（大于）、ge（大于等于）、lt（小于）、le（小于等于）、
            range（在范围内，val 传列表 [min, max]）、empty、not_empty

        单选/省市区（radio/area-linkage）:
            eq、ne、in、not_in、empty、not_empty

        多选/下拉（checkbox/select）:
            eq、ne、in、not_in、empty、not_empty

        人员/部门/下拉树/表字典/角色（select-user/select-depart/table-dict/select-tree/org-role）:
            eq、ne、in（是其中一个）、not_in（不是其中一个）、empty、not_empty

        开关（switch）:
            eq、ne、empty、not_empty

        关联记录（link-record）:
            eq、ne、in、not_in、empty、not_empty、linkage（查询工作表）

        子表/地图/图片/文件/手写签名等:
            empty、not_empty

        系统字段:
            create_time/update_time → 同数值/时间类规则
            create_by/update_by    → 同人员类规则（in/not_in 等）
            bpm_status             → 同多选/下拉规则

    清除数据过滤：
        config_view_data_filter(view_id, [])

    Returns:
        API 响应 dict

    示例：
        # 只显示年级为"初一"的学生
        config_view_data_filter(view_id, [
            {"field": "select_1775221412376_152628", "rule": "eq", "val": "初一",
             "type": "select", "name": "年级"}
        ])

        # 多分组：（姓王 或 姓张）且 年龄在 10~18 之间
        config_view_data_filter(view_id, [
            {
                "match_type": "or",
                "items": [
                    {"field": "input_xxx", "rule": "like", "val": "王", "type": "input", "name": "姓名"},
                    {"field": "input_xxx", "rule": "like", "val": "张", "type": "input", "name": "姓名"},
                ]
            },
            {
                "match_type": "and",
                "items": [
                    {"field": "number_xxx", "rule": "gt", "val": 10, "type": "number", "name": "年龄"},
                    {"field": "number_xxx", "rule": "lt", "val": 18, "type": "number", "name": "年龄"},
                ]
            }
        ], match_type='and')
    """
    if not conditions:
        # 清除数据过滤
        body = {
            "id": view_id,
            "matchType": "and",
            "conditionType": "and",
            "conditions": []
        }
        r = api_request('/desform/view/updateViewConfig', data=body, method='PUT')
        if r.get('success'):
            print(f'  [config_view_data_filter] 数据过滤已清除: viewId={view_id}')
            return r
        raise RuntimeError(f'数据过滤清除失败: {r.get("message", "未知错误")}')

    # 判断是简单列表还是分组列表
    is_group_format = isinstance(conditions[0], dict) and 'items' in conditions[0]

    if is_group_format:
        # 格式二：分组列表
        api_conditions = []
        for group in conditions:
            group_match = group.get('match_type', 'and')
            items = group.get('items', [])
            api_conditions.append({
                'matchType': group_match,
                'queryItems': [_normalize_filter_item(item) for item in items]
            })
    else:
        # 格式一：简单列表，自动包装为单个分组
        api_conditions = [{
            'matchType': match_type,
            'queryItems': [_normalize_filter_item(item) for item in conditions]
        }]

    body = {
        "id": view_id,
        "matchType": match_type,
        "conditions": api_conditions
    }

    r = api_request('/desform/view/updateViewConfig', data=body, method='PUT')
    if r.get('success'):
        total = sum(len(g['queryItems']) for g in api_conditions)
        print(f'  [config_view_data_filter] 数据过滤配置成功: viewId={view_id}, '
              f'{len(api_conditions)} 个分组, 共 {total} 个条件')
        return r
    raise RuntimeError(f'数据过滤配置失败: {r.get("message", "未知错误")}')


def _normalize_filter_item(item):
    """将用户传入的过滤条件项规范化为 API 所需格式"""
    rule = item.get('rule', 'eq')
    val = item.get('val', '')
    if val is None:
        val = ''
    return {
        'field': item['field'],
        'rule': rule,
        'val': val,
        'type': item.get('type', 'input'),
        'name': item.get('name', ''),
    }


def update_list_view(view_id, **fields):
    """更新列表视图配置

    通用更新接口，可修改视图的任意字段（名称、分组字段、日期字段等）。

    Args:
        view_id: 视图 ID（由 add_list_view_* 返回，或通过查询获得）
        **fields: 要更新的字段，例如：
                    name="新名称"
                    groupField="select_xxx"
                    titleField="input_xxx"

    Returns:
        API 响应 dict

    示例:
        update_list_view('2039961002911772674', name='项目看板')
        update_list_view('2039961002911772674', name='计划视图', groupField='select_xxx')
    """
    body = {"id": view_id, **fields}
    r = api_request('/desform/view/updateViewConfig', data=body, method='PUT')
    if r.get('success'):
        print(f'  [update_list_view] 视图更新成功: viewId={view_id}')
        return r
    raise RuntimeError(f'列表视图更新失败: {r.get("message", "未知错误")}')


# ============================================================
# 字典创建
# ============================================================
def create_dict(dict_code, dict_name, items, description=''):
    """创建新字典及其字典项

    Args:
        dict_code: 字典编码（唯一）
        dict_name: 字典名称
        items: 字典项列表 [{'value': '1', 'label': '事假'}, ...]
        description: 描述

    Returns:
        字典ID
    """
    # 创建字典主表
    r = api_request('/sys/dict/add', data={
        "dictCode": dict_code,
        "dictName": dict_name,
        "description": description,
        "type": 0
    })
    if not r.get('success'):
        raise RuntimeError(f"创建字典失败: {r.get('message', '')}")

    dict_id = r.get('result', {}).get('id') if isinstance(r.get('result'), dict) else r.get('result')
    if not dict_id:
        # 尝试查询刚创建的字典
        search_results = search_dict(dict_code)
        for sr in search_results:
            if sr.get('dictCode') == dict_code:
                dict_id = sr['id']
                break

    if not dict_id:
        raise RuntimeError(f"无法获取字典ID: {dict_code}")

    # 逐条添加字典项
    for i, item in enumerate(items):
        item_text = item.get('label', item.get('text', ''))
        item_value = str(item.get('value', ''))
        api_request('/sys/dictItem/add', data={
            "dictId": dict_id,
            "itemText": item_text,
            "itemValue": item_value,
            "sortOrder": i + 1,
            "status": 1
        })

    print(f"[create_dict] 字典创建成功: {dict_code} ({len(items)} 项)")
    return dict_id


def query_or_create_dict(dict_code, dict_name, items, description=''):
    """查询字典，不存在则创建

    Returns:
        (dict_id, items_list)
    """
    existing = query_dict(dict_code)
    if existing:
        print(f"[query_or_create_dict] 字典已存在: {dict_code}")
        return None, existing

    dict_id = create_dict(dict_code, dict_name, items, description)
    return dict_id, items


# ============================================================
# 字段级操作
# ============================================================
def add_widget(code, widget_or_widgets):
    """向已有表单追加控件

    Args:
        code: 表单编码
        widget_or_widgets: 单个控件 dict 或控件列表（多个时逐个添加）
    """
    widgets = widget_or_widgets if isinstance(widget_or_widgets, list) else [widget_or_widgets]
    last_r = None
    for i, w in enumerate(widgets):
        # 校验：必须是由 DATE()/INPUT() 等函数生成的完整控件结构，裸配置 dict 会被后端静默写入
        if 'key' not in w or 'model' not in w:
            raise ValueError(
                f'[add_widget] 第 {i+1} 个控件缺少 key/model，必须使用 DATE()/INPUT() 等函数生成完整控件结构，'
                '不能直接传裸配置 dict。如需按位置插入，请使用 export_design_json → 手动插入 → save_design_from_file。'
            )
        # 后端 @RequestBody JSONObject 期望单个对象，逐个发送
        r = api_request(f'/desform/api/{code}/addWidget', data=w, method='PUT')
        last_r = r
        if not r.get('success'):
            print(f"[add_widget] 第 {i + 1} 个控件添加失败: {r.get('message', '')}")
            return r
    print(f"[add_widget] 成功添加 {len(widgets)} 个控件到 {code}")
    return last_r


def update_widget(code, changes_dict, *, key=None, model=None):
    """修改指定控件的属性

    Args:
        code: 表单编码
        changes_dict: 要修改的属性字典，如 {"name": "新名称", "options": {"required": True}}
        key: 控件的 key（优先使用，精准定位，从 get_form_fields 返回值取）
        model: 控件的 model（key 不可用时使用）

    注意：key 和 model 必须显式指定其一，优先传 key（更精准，用 model 定位有时会报"组件不存在"）
    """
    if not key and not model:
        raise ValueError("[update_widget] key 和 model 不能都为空，请显式指定其一")
    body = {"action": "update", "widget": changes_dict}
    if key:
        body["key"] = key
    else:
        body["model"] = model
    identifier = key or model
    r = api_request(f'/desform/api/{code}/updateWidget', data=body, method='PUT')
    if r.get('success'):
        print(f"[update_widget] 成功更新控件 {identifier}")
    else:
        print(f"[update_widget] 更新失败: {r.get('message', '')}")
    return r


def delete_widget(code, *, key=None, model=None):
    """删除指定控件

    Args:
        code: 表单编码
        key: 控件的 key（优先使用，精准定位）
        model: 控件的 model（key 不可用时使用）

    注意：key 和 model 必须显式指定其一，优先传 key
    """
    if not key and not model:
        raise ValueError("[delete_widget] key 和 model 不能都为空，请显式指定其一")
    body = {"action": "delete"}
    if key:
        body["key"] = key
    else:
        body["model"] = model
    identifier = key or model
    r = api_request(f'/desform/api/{code}/updateWidget', data=body, method='PUT')
    if r.get('success'):
        print(f"[delete_widget] 成功删除控件 {identifier}")
    else:
        print(f"[delete_widget] 删除失败: {r.get('message', '')}")
    return r
