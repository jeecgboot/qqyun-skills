# -*- coding: utf-8 -*-
"""
JeecgBoot 大屏/仪表盘设计器 Python 工具库
用于通过 API 自动创建和管理大屏、仪表盘页面及其组件。

使用方式：
    from bi_utils import *
    init_api('<api_base>', '<token>')
    page_id = create_page('销售大屏', style='bigScreen')
    add_number(page_id, '销售额', x=50, y=50, w=400, h=200, value=128560)
    add_chart(page_id, 'JBar', '月度销售', x=50, y=280, w=860, h=380,
              categories=['1月','2月','3月'], series=[{'name':'销售额','data':[820,932,901]}])
    save_page(page_id)
"""

import json
import urllib.request
import urllib.parse
import time
import random
import uuid

# ============================================================
# 全局配置
# ============================================================
API_BASE = ''
TOKEN = ''
EXTRA_HEADERS = {}   # QQY模式额外头：{'X-Low-App-ID': appId, 'X-Tenant-Id': tenantId}

# 内存中缓存页面组件数据，save_page 时一次性提交
_page_components = {}  # {page_id: [component_dict, ...]}
_page_info = {}        # {page_id: {name, style, theme, ...}}


# ============================================================
# 大屏 vs 仪表盘 模式预设（颜色、样式完全不同）
# ============================================================
# 大屏（bigScreen）- 深色背景，亮色文字
_BIGSCREEN = {
    'bg': '#FFFFFF00',
    'border_color': '#FFFFFF00',
    'title_color': '#ffffff',
    'axis_color': '#ffffff',
    'grid_color': 'rgba(255,255,255,0.1)',
    'body_color': '#ffffff',
    'suffix_color': '#ffffff',
    'legend_color': '#ffffff',
    'tooltip_color': '#ffffff',
    'card': {'title': '', 'extra': '', 'rightHref': '', 'size': 'small'},
    'number_font_size': 32,
    # 表格
    'table_header_bg': 'rgba(0,0,0,0.3)',
    'table_header_color': '#ffffff',
    'table_body_bg': 'rgba(0,0,0,0.1)',
    'table_body_color': '#ffffff',
    'table_body_font_size': 14,
    'table_header_font_size': 14,
    # 滚动表格
    'scroll_odd_color': '#0a2732',
    'scroll_even_color': '#003b51',
    'scroll_header_bg': '#0a73ff',
    'scroll_header_color': '#ffffff',
    'scroll_body_color': '#ffffff',
    'scroll_border_color': 'rgba(255,255,255,0.1)',
    # 排行榜
    'ranking_color': '#1370fb',
    'ranking_text_color': '#fff',
}

# 仪表盘（default）- 亮色背景，深色文字，带卡片头
_DASHBOARD = {
    'bg': '#FFFFFF',
    'border_color': '#E8E8E8',
    'title_color': '#464646',
    'axis_color': '#909198',
    'grid_color': '#F3F3F3',
    'body_color': '#464646',
    'suffix_color': '#909198',
    'legend_color': '#464646',
    'tooltip_color': '#464646',
    'card': {
        'title': '',  # 由各函数填充
        'extra': '', 'rightHref': '',
        'size': 'default',
        'headColor': '#FFFFFF',
        'textStyle': {'color': '#464646', 'fontSize': 16, 'fontWeight': 'bold'},
    },
    'number_font_size': 32,
    # 表格
    'table_header_bg': '#FAFAFA',
    'table_header_color': '#464646',
    'table_body_bg': '#FFFFFF',
    'table_body_color': '#666666',
    'table_body_font_size': 13,
    'table_header_font_size': 14,
    # 滚动表格
    'scroll_odd_color': '#FFFFFF',
    'scroll_even_color': '#FAFAFA',
    'scroll_header_bg': '#F0F0F0',
    'scroll_header_color': '#464646',
    'scroll_body_color': '#666666',
    'scroll_border_color': '#E8E8E8',
    # 排行榜
    'ranking_color': '#1890FF',
    'ranking_text_color': '#464646',
}


def _get_mode(page_id):
    """获取页面模式预设（大屏 or 仪表盘）"""
    info = _page_info.get(page_id, {})
    style = info.get('style', 'bigScreen')
    if style == 'default':
        return _DASHBOARD
    return _BIGSCREEN


def _make_card(mode, title):
    """根据模式创建 card 配置。
    大屏模式：card.title 保持为空（标题由 ECharts option.title 显示，避免重复）
    仪表盘模式：card.title 设置标题（卡片头显示）
    """
    card = dict(mode['card'])
    if 'textStyle' in mode['card']:
        card['textStyle'] = dict(mode['card']['textStyle'])
    # 大屏不用 card 标题头，仪表盘用
    if mode is _DASHBOARD:
        card['title'] = title
    else:
        card['title'] = ''
    return card


def init_api(api_base, token, extra_headers=None):
    """初始化 API 地址和 Token（QQY模式可传 extra_headers={'X-Low-App-ID':appId,'X-Tenant-Id':tenantId}）"""
    global API_BASE, TOKEN, EXTRA_HEADERS
    API_BASE = api_base.rstrip('/')
    TOKEN = token
    if extra_headers:
        EXTRA_HEADERS = extra_headers
    print(f'[bi_utils] API: {API_BASE}')


# ============================================================
# HTTP 工具
# ============================================================
def _request(method, path, data=None, params=None):
    """发送 HTTP 请求"""
    url = f'{API_BASE}{path}'
    if params:
        url += '?' + urllib.parse.urlencode(params)

    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
        'X-Access-Token': TOKEN,
    }
    if EXTRA_HEADERS:
        headers.update(EXTRA_HEADERS)

    body = None
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        # QQY 首次请求常见冷启动，30s 不够
        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else ''
        print(f'[bi_utils] HTTP {e.code}: {error_body}')
        raise
    except Exception as e:
        print(f'[bi_utils] Request error: {e}')
        raise


def _gen_key():
    """生成唯一 key"""
    return f'{int(time.time() * 1000)}_{random.randint(100000, 999999)}'


def _gen_uuid():
    """生成 32 位无横线 UUID"""
    return uuid.uuid4().hex


# ============================================================
# 页面管理 API
# ============================================================
def create_page(name, style='bigScreen', theme=None, background_image=None,
                type_id='0', design_type=100, protection_code='', low_app_id=None):
    """
    创建大屏或仪表盘页面。

    Args:
        name: 页面名称
        style: 'bigScreen'=大屏, 'default'=仪表盘
        theme: 主题，默认大屏=dark，仪表盘=default
        background_image: 背景图路径，大屏默认 '/img/bg/bg4.png'
        type_id: 分类 ID，默认 '0'
        design_type: 设计类型 100=PC, 30=手机, 80=平板
        protection_code: 保护密码
        low_app_id: QQY 低代码应用 ID。不传时回退 EXTRA_HEADERS['X-Low-App-ID']。
                    QQY 创建必须写入 body.lowAppId，禁止传 isLowApp。
    Returns:
        page_id: 页面 ID
    """
    if theme is None:
        theme = 'dark' if style == 'bigScreen' else 'default'
    if background_image is None and style == 'bigScreen':
        background_image = '/img/bg/bg4.png'
    if not low_app_id:
        low_app_id = EXTRA_HEADERS.get('X-Low-App-ID') or ''

    payload = {
        'name': name,
        'type': type_id,
        'protectionCode': protection_code,
        'theme': theme,
        'style': style,
        'backgroundImage': background_image or '',
        'designType': design_type,
    }
    if low_app_id:
        payload['lowAppId'] = low_app_id

    result = _request('POST', '/drag/page/add', data=payload)

    if not result.get('success'):
        raise Exception(f"创建页面失败: {result.get('message', json.dumps(result, ensure_ascii=False))}")

    page_data = result.get('result', {})
    page_id = page_data.get('id')
    if not page_id:
        raise Exception(f"创建页面成功但未返回 ID: {json.dumps(result, ensure_ascii=False)}")

    # 缓存页面信息
    _page_components[page_id] = []
    _page_info[page_id] = {
        'name': name,
        'style': style,
        'theme': theme,
        'backgroundImage': background_image or '',
        'designType': design_type,
        'updateCount': page_data.get('updateCount', 1),
        'path': page_data.get('path', ''),
        'lowAppId': low_app_id or page_data.get('lowAppId') or '',
    }

    print(f'[bi_utils] 页面创建成功: {name} (ID: {page_id})')
    return page_id


def query_page(page_id):
    """查询页面详情（含组件配置）"""
    result = _request('GET', '/drag/page/queryById', params={'id': page_id})
    if not result.get('success'):
        raise Exception(f"查询页面失败: {result.get('message')}")
    # result 键存在但值为 None 时 .get(k, {}) 仍返回 None（过期 pageId/错租户常见）
    page = result.get('result') or {}
    if not isinstance(page, dict) or not page:
        raise Exception(
            '查询页面失败: result 为空（pageId=%s 可能过期/错租户/错应用；改用 --page-name 或 tenants+apps+menus）'
            % page_id)

    # 更新缓存（保留所有关键字段，避免 save_page 时丢失）
    if page_id not in _page_info:
        _page_info[page_id] = {}
    info = _page_info[page_id]
    info['updateCount'] = page.get('updateCount', 1)
    info['name'] = page.get('name', '')
    # 仅当服务器返回了非空值时才更新，避免覆盖 create_page 设置的值
    for field in ('backgroundImage', 'style', 'theme', 'designType', 'lowAppId'):
        server_val = page.get(field)
        if server_val is not None:
            info[field] = server_val
        elif field not in info:
            info[field] = EXTRA_HEADERS.get('X-Low-App-ID', '') if field == 'lowAppId' else ''
    # 缓存 desJson（页面宽高等配置），save_page 时回传避免丢失
    info['desJson'] = page.get('desJson', '') or ''

    # 解析 template
    template = page.get('template')
    if template and isinstance(template, str):
        try:
            page['template'] = json.loads(template)
        except:
            pass

    return page


def list_pages(style=None, page_no=1, page_size=50):
    """列表查询页面"""
    params = {'pageNo': page_no, 'pageSize': page_size}
    if style:
        params['style'] = style
    result = _request('GET', '/drag/page/list', params=params)
    if not result.get('success'):
        raise Exception(f"查询列表失败: {result.get('message')}")
    return result.get('result', {})


def save_page(page_id):
    """
    保存页面设计（将所有缓存的组件一次性提交）。

    通过 POST /drag/page/edit 提交，后端会：
    1. 删除所有旧的 OnlDragPageComp 记录
    2. 从 template 中提取 config 创建新的 comp 记录
    3. 更新 template（移除 config，注入 pageCompId）

    优化说明（2026-04-08）：
    - 不再在 save_page 内部调用 query_page，消除额外 API 往返和 updateCount 竞争
    - 用 `page_id in _page_components` 区分"主动设置（含空列表）"vs"未设置"，
      修复删除全部组件后 save_page 用旧模板覆盖的 bug
    - 传 desJson 避免页面宽高配置丢失
    """
    info = _page_info.get(page_id)

    # 若没有缓存的页面元数据（updateCount/name/style 等），先查询一次
    if info is None:
        try:
            query_page(page_id)
            info = _page_info.get(page_id, {})
        except Exception as e:
            print(f'[bi_utils] 查询页面警告: {e}，使用空元数据')
            info = {}

    # 取组件列表：
    #   - page_id 在 _page_components 中（含 [] 空列表）→ 使用缓存值（含有意清空的情形）
    #   - page_id 不在 _page_components 中 → 从服务端拉取，保留现有组件
    if page_id in _page_components:
        components = _page_components[page_id]
    else:
        try:
            page = query_page(page_id)
            info = _page_info.get(page_id, {})
            existing = page.get('template', [])
            components = existing if isinstance(existing, list) else []
        except Exception as e:
            print(f'[bi_utils] 查询页面警告: {e}，使用空组件列表')
            components = []

    # 构建 template JSON
    template = json.dumps(components, ensure_ascii=False)

    payload = {
        'id': page_id,
        'name': info.get('name', ''),
        'template': template,
        'updateCount': info.get('updateCount', 1),
        'style': info.get('style', 'bigScreen'),
        'theme': info.get('theme', 'dark'),
        'backgroundImage': info.get('backgroundImage', ''),
        'designType': info.get('designType', 100),
        'desJson': info.get('desJson', '') or '',
    }
    # QQY 保存必须回传 lowAppId，否则应用归属丢失
    low_app_id = info.get('lowAppId') or EXTRA_HEADERS.get('X-Low-App-ID') or ''
    if low_app_id:
        payload['lowAppId'] = low_app_id

    result = _request('POST', '/drag/page/edit', data=payload)

    if not result.get('success'):
        raise Exception(f"保存页面失败: {result.get('message')}")

    # 更新 updateCount（下次保存时使用最新值，无需重新 query）
    new_count = result.get('result', {})
    if isinstance(new_count, dict):
        info['updateCount'] = new_count.get('updateCount', info.get('updateCount', 1) + 1)
    else:
        info['updateCount'] = info.get('updateCount', 1) + 1

    print(f'[bi_utils] 页面保存成功: {info.get("name", page_id)} ({len(components)} 个组件)')
    return True


def delete_page(page_id, physical=False):
    """
    删除页面。

    Args:
        page_id: 页面 ID
        physical: True=物理删除（彻底），False=逻辑删除（回收站）
    """
    if physical:
        result = _request('DELETE', '/drag/page/physicalDelete', params={'id': page_id})
    else:
        result = _request('DELETE', '/drag/page/delete', params={'id': page_id})

    if not result.get('success'):
        raise Exception(f"删除页面失败: {result.get('message')}")

    # 清理缓存
    _page_components.pop(page_id, None)
    _page_info.pop(page_id, None)

    print(f'[bi_utils] 页面删除成功: {page_id} ({"物理删除" if physical else "逻辑删除"})')
    return True


def recover_page(page_id):
    """恢复回收站中的页面"""
    result = _request('POST', '/drag/page/recoveryDelete', data={'id': page_id})
    if not result.get('success'):
        raise Exception(f"恢复页面失败: {result.get('message')}")
    print(f'[bi_utils] 页面恢复成功: {page_id}')
    return True


def copy_page(page_id):
    """复制页面"""
    result = _request('GET', '/drag/page/copyPage', params={'id': page_id})
    if not result.get('success'):
        raise Exception(f"复制页面失败: {result.get('message')}")
    new_page = result.get('result', {})
    new_id = new_page.get('id')
    print(f'[bi_utils] 页面复制成功: {page_id} → {new_id}')
    return new_id


# ============================================================
# 组件添加函数
# ============================================================
def add_component(page_id, component, title, x, y, w, h, config=None):
    """
    添加通用组件到页面。

    Args:
        page_id: 页面 ID
        component: 组件类型，如 'JBar', 'JNumber', 'JTable'
        title: 组件标题
        x, y: 位置（大屏=像素，仪表盘=栅格）
        w, h: 尺寸（大屏=像素，仪表盘=栅格）
        config: 组件配置 dict（可选，会与默认配置合并）
    Returns:
        component dict（已加入缓存）
    """
    if page_id not in _page_components:
        _page_components[page_id] = []

    key = _gen_key()

    # 栅格单位转换为像素（仪表盘模式）
    info = _page_info.get(page_id, {})
    style = info.get('style', 'bigScreen')
    if style == 'default':
        px_w = w * 75
        px_h = h * 11
    else:
        px_w = w
        px_h = h

    # 基础配置
    default_config = {
        'dataType': 1,
        'timeOut': 0,
        'size': {'width': px_w, 'height': px_h},
        'chart': {
            'subclass': component,
            'category': _get_category(component),
        },
        'option': {},
        'chartData': [],
        'linkageConfig': [],
        'turnConfig': {'url': '', 'type': '_blank'},
        'linkType': 'url',
    }

    # 合并用户配置
    if config:
        _deep_merge(default_config, config)

    comp = {
        'component': component,
        'componentName': title,
        'visible': True,
        'i': key,
        'x': x,
        'y': y,
        'w': w,
        'h': h,
        'pcX': x,
        'pcY': y,
        'pcW': w,
        'orderNum': len(_page_components[page_id]),
        'config': json.dumps(default_config, ensure_ascii=False),
    }

    _page_components[page_id].insert(0, comp)
    return comp


def add_number(page_id, title, x, y, w, h, value=0, prefix='', suffix='',
               font_size=None, color=None, bg_color=None):
    """
    添加数字指标组件（JNumber）。
    自动根据页面模式（大屏/仪表盘）应用不同默认样式。

    Args:
        value: 显示的数值
        prefix: 前缀（如 '¥'）
        suffix: 后缀（如 '元', '%'）
        font_size: 字体大小（默认根据模式自动设置）
        color: 字体颜色（默认根据模式自动设置）
    """
    mode = _get_mode(page_id)
    if font_size is None:
        font_size = mode['number_font_size']
    if color is None:
        color = mode['body_color']

    config = {
        'dataType': 1,
        'chartData': json.dumps({'value': value}, ensure_ascii=False),
        'background': mode['bg'],
        'borderColor': mode['border_color'],
        'option': {
            'title': {'text': title, 'show': True,
                      'textStyle': {'color': mode['title_color'], 'fontSize': 14}},
            'body': {
                'text': '',
                'color': color,
                'fontSize': font_size,
                'fontWeight': 'bold',
                'marginLeft': 0,
                'marginTop': 0,
            },
            'card': _make_card(mode, title),
            'prefix': prefix,
            'prefixColor': mode['suffix_color'],
            'prefixFontSize': 14,
            'suffix': suffix,
            'suffixColor': mode['suffix_color'],
            'suffixFontSize': 14,
            'isCompare': False,
            'trendType': '1',
        },
        'analysis': {
            'isCompare': False,
            'compareType': '',
            'trendType': '1',
        },
    }
    return add_component(page_id, 'JNumber', title, x, y, w, h, config)


def add_chart(page_id, chart_type, title, x, y, w, h,
              categories=None, series=None, pie_data=None):
    """
    添加图表组件。

    支持的 chart_type: JBar, JLine, JSmoothLine, JHorizontalBar, JStackBar,
    JMixLineBar, DoubleLineBar, JPie, JRing, JRose, JFunnel, JRadar, JScatter,
    JGauge, JLiquid, JProgress, JWordCloud, JAreaMap, JFlyLineMap, 等等。

    Args:
        chart_type: 组件类型
        categories: X轴类目数据 ['一月','二月',...]（轴类图表用）
        series: 系列数据 [{'name':'系列1','data':[1,2,3]}]（轴类图表用）
        pie_data: 饼图数据 [{'name':'A','value':10}]（饼/环/玫瑰图用）
    """
    # 确定图表 ECharts 类型
    echart_type_map = {
        'JBar': 'bar', 'JHorizontalBar': 'bar', 'JBackgroundBar': 'bar',
        'JMultipleBar': 'bar', 'JNegativeBar': 'bar', 'JStackBar': 'bar',
        'JLine': 'line', 'JSmoothLine': 'line', 'JStepLine': 'line',
        'JMultipleLine': 'line',
        'JMixLineBar': 'bar',  # 混合类型
        'JPie': 'pie', 'JRing': 'pie', 'JRose': 'pie',
        'JFunnel': 'funnel',
        'JRadar': 'radar',
        'JScatter': 'scatter', 'JBubble': 'scatter',
        'JGauge': 'gauge',
    }
    echart_type = echart_type_map.get(chart_type, 'bar')

    # 构建 chartData
    chart_data = []
    if pie_data:
        chart_data = pie_data
    elif categories and series:
        if len(series) == 1:
            # 单系列：简单 name/value
            for i, cat in enumerate(categories):
                chart_data.append({
                    'name': cat,
                    'value': series[0]['data'][i] if i < len(series[0]['data']) else 0,
                })
        else:
            # 多系列：需要 type 字段区分
            for s in series:
                for i, cat in enumerate(categories):
                    chart_data.append({
                        'name': cat,
                        'value': s['data'][i] if i < len(s['data']) else 0,
                        'type': s.get('name', ''),
                    })

    mode = _get_mode(page_id)

    # 构建 ECharts option（根据模式应用不同颜色）
    option = {
        'title': {'text': title, 'show': True,
                  'textStyle': {'color': mode['title_color'], 'fontSize': 16},
                  'subtextStyle': {'color': mode['axis_color']}},
        'tooltip': {'show': True, 'textStyle': {'color': mode['tooltip_color']}},
        'legend': {'show': len(series or []) > 1 or bool(pie_data),
                   'textStyle': {'color': mode['legend_color'], 'fontSize': 12}},
        'grid': {'left': 60, 'right': 30, 'top': 70, 'bottom': 40, 'show': False},
        'card': _make_card(mode, title),
    }

    if pie_data:
        # 饼图系列
        radius = '55%'
        if chart_type == 'JRing':
            radius = ['40%', '55%']
        elif chart_type == 'JRose':
            radius = ['20%', '55%']

        option['tooltip']['trigger'] = 'item'
        if chart_type in ('JPie', 'JRing', 'JRose'):
            option['legend']['orient'] = 'vertical'
        option['series'] = [{
            'name': title,
            'type': 'pie',
            'radius': radius,
            'data': pie_data,
            'emphasis': {'itemStyle': {'shadowBlur': 10, 'shadowOffsetX': 0,
                                       'shadowColor': 'rgba(0,0,0,0.5)'}},
        }]
    elif categories and series:
        # 轴类图表
        option['xAxis'] = {
            'type': 'category',
            'show': True,
            'data': categories,
            'axisLabel': {'color': mode['axis_color']},
            'axisLine': {'lineStyle': {'color': mode['grid_color']}},
        }
        option['yAxis'] = {
            'type': 'value',
            'show': True,
            'axisLabel': {'color': mode['axis_color']},
            'splitLine': {'lineStyle': {'color': mode['grid_color']}},
        }

        if chart_type == 'JHorizontalBar':
            option['xAxis'], option['yAxis'] = option['yAxis'], option['xAxis']
            option['yAxis']['data'] = categories
            option['yAxis']['type'] = 'category'
            option['xAxis'] = {
                'type': 'value', 'show': True,
                'axisLabel': {'color': mode['axis_color']},
                'axisLine': {'lineStyle': {'color': mode['grid_color']}},
                'splitLine': {'lineStyle': {'color': mode['grid_color']}},
            }

        option['series'] = []
        for s in series:
            series_item = {
                'name': s.get('name', ''),
                'type': echart_type,
                'data': s.get('data', []),
            }
            if chart_type == 'JSmoothLine':
                series_item['smooth'] = True
            if chart_type == 'JStepLine':
                series_item['step'] = 'middle'
            if chart_type == 'JStackBar':
                series_item['stack'] = 'total'
            option['series'].append(series_item)

    # 仪表盘模式：card.title 留空，仅用 option.title 显示标题（避免重复）
    option['card'] = _make_card(mode, '')

    config = {
        'dataType': 1,
        'chartData': json.dumps(chart_data, ensure_ascii=False),
        'background': mode['bg'],
        'borderColor': mode['border_color'],
        'option': option,
    }

    return add_component(page_id, chart_type, title, x, y, w, h, config)


def add_table(page_id, title, x, y, w, h, columns=None, data=None):
    """
    添加数据表格组件（JTable）。

    Args:
        columns: 列名列表 ['姓名', '年龄', '地址']
        data: 数据行列表 [{'姓名':'张三','年龄':'28','地址':'北京'}]
    """
    columns = columns or []
    data = data or []

    chart_data = []
    for col in columns:
        field_name = col.lower().replace(' ', '_')
        chart_data.append({
            'fieldTxt': col,
            'fieldName': field_name,
            'type': 'field',
            'isShow': 'Y',
            'isTotal': 'N',
        })

    mode = _get_mode(page_id)

    config = {
        'dataType': 1,
        'chartData': json.dumps(chart_data, ensure_ascii=False),
        'background': mode['bg'],
        'borderColor': mode['border_color'],
        'option': {
            'title': {'text': title, 'show': True,
                      'textStyle': {'color': mode['title_color'], 'fontSize': 16}},
            'bordered': True,
            'size': 'small',
            'headerBgColor': mode['table_header_bg'],
            'headerColor': mode['table_header_color'],
            'headerFontSize': mode['table_header_font_size'],
            'bodyBgColor': mode['table_body_bg'],
            'bodyColor': mode['table_body_color'],
            'bodyFontSize': mode['table_body_font_size'],
            'card': _make_card(mode, title),
            'data': data,
        },
    }

    return add_component(page_id, 'JTable', title, x, y, w, h, config)


def add_scroll_table(page_id, title, x, y, w, h, columns=None, data=None):
    """
    添加自动滚动表格组件（JScrollTable）。

    Args:
        columns: 列名列表
        data: 数据行列表（二维数组格式）
    """
    columns = columns or []
    data = data or []

    # JScrollTable expects chartData as array of objects
    # columns maps to option.fieldMapping
    field_mapping = []
    for col in columns:
        field_name = col.lower().replace(' ', '_')
        field_mapping.append({'name': col, 'key': field_name, 'width': 0})

    # Convert data rows: if data is list of lists, convert to list of dicts
    chart_data = []
    if data and isinstance(data[0], (list, tuple)):
        for row in data:
            item = {}
            for j, col in enumerate(columns):
                field_name = col.lower().replace(' ', '_')
                item[field_name] = row[j] if j < len(row) else ''
            chart_data.append(item)
    elif data and isinstance(data[0], dict):
        chart_data = data
    else:
        chart_data = data or []

    mode = _get_mode(page_id)

    config = {
        'dataType': 1,
        'chartData': json.dumps(chart_data, ensure_ascii=False),
        'background': mode['bg'],
        'borderColor': mode['border_color'],
        'option': {
            'title': {'text': title, 'show': True,
                      'textStyle': {'color': mode['title_color'], 'fontSize': 16}},
            'ranking': False,
            'textPosition': 'center',
            'lineHeight': 50,
            'fontSize': 20,
            'bodyFontSize': 18,
            'scrollTime': 50,
            'scroll': True,
            'showBorder': True,
            'borderWidth': 1,
            'borderColor': mode['scroll_border_color'],
            'borderStyle': 'solid',
            'showHead': True,
            'bodyFontColor': mode['scroll_body_color'],
            'oddColor': mode['scroll_odd_color'],
            'evenColor': mode['scroll_even_color'],
            'headerBgColor': mode['scroll_header_bg'],
            'headerFontColor': mode['scroll_header_color'],
            'fieldMapping': field_mapping,
            'card': _make_card(mode, title),
        },
    }

    return add_component(page_id, 'JScrollTable', title, x, y, w, h, config)


def add_ranking(page_id, title, x, y, w, h, data=None):
    """
    添加排行榜组件（JScrollRankingBoard）。

    Args:
        data: 排行数据 [{'name':'项目A','value':100}, ...]
    """
    data = data or []

    mode = _get_mode(page_id)

    config = {
        'dataType': 1,
        'chartData': json.dumps(data, ensure_ascii=False),
        'background': mode['bg'],
        'borderColor': mode['border_color'],
        'option': {
            'title': {'text': title, 'show': True,
                      'textStyle': {'color': mode['title_color'], 'fontSize': 16}},
            'waitTime': 2000,
            'rowNum': 5,
            'carousel': 'single',
            'sort': True,
            'fontSize': 13,
            'color': mode['ranking_color'],
            'textColor': mode['ranking_text_color'],
            'card': _make_card(mode, title),
        },
    }

    return add_component(page_id, 'JScrollRankingBoard', title, x, y, w, h, config)


def add_text(page_id, title, x, y, w, h, content='', font_size=16, color=None,
             font_weight='normal', text_align='left', letter_spacing=0):
    """
    添加文本组件（JText）。
    使用与真实模板一致的 option.body 结构 + chartData: {"value": "..."} 格式。

    Args:
        content: 文本内容
        font_size: 字体大小
        color: 字体颜色（默认根据模式自动设置）
        font_weight: 字体粗细 'normal'/'bold'
        text_align: 对齐方式 'left'/'center'/'right'
        letter_spacing: 字间距（大屏标题建议 5-8）
    """
    mode = _get_mode(page_id)
    if color is None:
        color = mode['title_color']

    text_value = content or title
    config = {
        'dataType': 1,
        'chartData': {'value': text_value},
        'option': {
            'body': {
                'color': color,
                'fontSize': font_size,
                'fontWeight': font_weight,
                'letterSpacing': letter_spacing,
                'text': '',
                'marginTop': 0,
                'marginLeft': 0,
            },
            'textAlign': text_align,
            'card': {'title': '', 'extra': '', 'rightHref': '', 'size': 'default'},
            'openUrl': '',
            'isLink': False,
            'openType': '_blank',
        },
    }

    return add_component(page_id, 'JText', title, x, y, w, h, config)


def add_image(page_id, title, x, y, w, h, src=''):
    """
    添加图片组件（JImg）。

    Args:
        src: 图片 URL
    """
    config = {
        'dataType': 1,
        'chartData': src,
        'option': {
            'objectFit': 'cover',
        },
    }

    return add_component(page_id, 'JImg', title, x, y, w, h, config)


def add_gauge(page_id, title, x, y, w, h, value=0, max_val=100,
              unit='%', color='#00BAFF'):
    """
    添加仪表盘组件（JGauge）。

    Args:
        value: 当前值
        max_val: 最大值
        unit: 单位
        color: 指针颜色
    """
    mode = _get_mode(page_id)
    tail_color = '#333' if mode is _BIGSCREEN else '#E8E8E8'

    config = {
        'dataType': 1,
        'chartData': json.dumps([{'name': title, 'value': value}], ensure_ascii=False),
        'background': mode['bg'],
        'borderColor': mode['border_color'],
        'option': {
            'title': {'text': title, 'show': True,
                      'textStyle': {'color': mode['title_color'], 'fontSize': 16}},
            'card': _make_card(mode, title),
            'series': [{
                'type': 'gauge',
                'max': max_val,
                'detail': {'formatter': f'{{value}}{unit}'},
                'data': [{'value': value, 'name': title}],
                'axisLine': {
                    'lineStyle': {
                        'color': [[value / max_val, color], [1, tail_color]],
                    }
                },
            }],
        },
    }

    return add_component(page_id, 'JGauge', title, x, y, w, h, config)


def add_liquid(page_id, title, x, y, w, h, value=50, color='#00BAFF'):
    """
    添加水球图组件（JLiquid）。

    Args:
        value: 0~100 的百分比值（如 97.3 表示 97.3%）
        color: 颜色
    """
    mode = _get_mode(page_id)

    config = {
        'dataType': 1,
        'chartData': json.dumps([{'value': value}], ensure_ascii=False),
        'background': mode['bg'],
        'borderColor': mode['border_color'],
        'option': {
            'title': {'text': title, 'show': True,
                      'textStyle': {'color': mode['title_color'], 'fontSize': 16}},
            'liquidType': 'circle',
            'color': color,
            'borderWidth': 2,
            'distance': 1,
            'borderColor': color,
            'strokeOpacity': 0,
            'count': 4,
            'length': 128,
            'textColor': mode['title_color'],
            'textFontSize': 30,
            'card': _make_card(mode, title),
        },
    }

    return add_component(page_id, 'JLiquid', title, x, y, w, h, config)


def add_countdown(page_id, title, x, y, w, h, value=0, font_size=48, color='#00BAFF'):
    """
    添加数字翻牌器组件（JCountTo）。

    Args:
        value: 目标数值
        font_size: 字体大小
        color: 字体颜色
    """
    mode = _get_mode(page_id)
    if color == '#00BAFF' and mode is _DASHBOARD:
        color = mode['body_color']

    config = {
        'dataType': 1,
        'chartData': str(value),
        'background': mode['bg'],
        'borderColor': mode['border_color'],
        'option': {
            'title': {'text': title, 'show': True,
                      'textStyle': {'color': mode['title_color'], 'fontSize': 16}},
            'endVal': value,
            'fontSize': font_size,
            'color': color,
            'duration': 2000,
            'card': _make_card(mode, title),
        },
    }

    return add_component(page_id, 'JCountTo', title, x, y, w, h, config)


def add_border(page_id, x, y, w, h, border_type=1, color='#00BAFF'):
    """
    添加装饰边框组件（JDragBorder）。

    Args:
        border_type: 边框样式 1~13
        color: 边框颜色
    """
    config = {
        'dataType': 1,
        'option': {
            'borderType': border_type,
            'color': [color],
        },
    }

    return add_component(page_id, 'JDragBorder', f'边框{border_type}', x, y, w, h, config)


def add_decoration(page_id, x, y, w, h, deco_type=1, color='#00BAFF'):
    """
    添加装饰条组件（JDragDecoration）。

    Args:
        deco_type: 装饰样式 1~12
        color: 颜色
    """
    config = {
        'dataType': 1,
        'option': {
            'decorationType': deco_type,
            'color': [color],
        },
    }

    return add_component(page_id, 'JDragDecoration', f'装饰{deco_type}', x, y, w, h, config)


def add_current_time(page_id, x, y, w=280, h=33, fmt='YYYY-MM-DD hh:mm:ss',
                     show_week='show', hourly_system='12',
                     color=None, font_weight='normal', letter_spacing=0):
    """
    添加实时时钟组件（JCurrentTime）。

    Args:
        fmt: 时间格式，如 'YYYY-MM-DD hh:mm:ss'
        show_week: 是否显示星期 'show'/'hide'
        hourly_system: 时制 '12'/'24'
        color: 字体颜色（默认根据模式自动设置）
        font_weight: 字体粗细 'normal'/'bold'
        letter_spacing: 字间距
    """
    mode = _get_mode(page_id)
    if color is None:
        color = mode['title_color']

    config = {
        'dataType': 1,
        'background': mode['bg'],
        'borderColor': mode['border_color'],
        'chartData': '',
        'option': {
            'showWeek': show_week,
            'hourlySystem': hourly_system,
            'format': fmt,
            'card': {'title': '', 'extra': '', 'rightHref': '', 'size': 'default'},
            'body': {
                'text': '', 'color': color, 'fontWeight': font_weight,
                'marginLeft': 0, 'marginTop': 0, 'letterSpacing': letter_spacing,
            },
        },
    }

    return add_component(page_id, 'JCurrentTime', '实时时钟', x, y, w, h, config)


def add_word_cloud(page_id, title, x, y, w, h, data=None,
                   font_family='SimSun', color='#FFE472',
                   min_size=8, max_size=32, shape='circle'):
    """
    添加词云图组件（JWordCloud）。

    Args:
        data: 词云数据 [{'name':'词语','value':9}, ...]，默认使用内置示例数据
        font_family: 字体
        color: 文字颜色
        min_size: 最小字号
        max_size: 最大字号
        shape: 词云形状 'circle'/'cardioid'/'diamond'/'triangle'/'star' 等
    """
    mode = _get_mode(page_id)
    if data is None:
        data = [
            {'value': 9, 'name': 'AntV'}, {'value': 8, 'name': 'F2'},
            {'value': 8, 'name': 'G2'}, {'value': 8, 'name': 'G6'},
            {'value': 8, 'name': 'DataSet'}, {'value': 8, 'name': '墨者学院'},
            {'value': 6, 'name': 'Analysis'}, {'value': 6, 'name': 'Data Mining'},
            {'value': 6, 'name': 'Data Vis'}, {'value': 6, 'name': 'Design'},
            {'value': 6, 'name': 'Grammar'}, {'value': 6, 'name': 'Graphics'},
            {'value': 6, 'name': 'Graph'}, {'value': 6, 'name': 'Hierarchy'},
            {'value': 6, 'name': 'Labeling'}, {'value': 6, 'name': 'Layout'},
            {'value': 6, 'name': 'Quantitative'}, {'value': 6, 'name': 'Relation'},
            {'value': 6, 'name': 'Statistics'}, {'value': 6, 'name': '可视化'},
            {'value': 6, 'name': '数据'}, {'value': 6, 'name': '数据可视化'},
        ]

    config = {
        'dataType': 1,
        'background': mode['bg'],
        'borderColor': mode['border_color'],
        'chartData': json.dumps(data, ensure_ascii=False),
        'option': {
            'fontFamily': font_family,
            'color': color,
            'minSize': min_size,
            'maxSize': max_size,
            'padding': 8,
            'customColor': [],
            'series': [{'shape': shape}],
            'card': {'title': '', 'extra': '', 'rightHref': '', 'size': 'default'},
            'title': {
                'text': title, 'textAlign': 'left', 'show': True,
                'textStyle': {'color': mode['title_color'], 'fontWeight': 'normal'},
            },
        },
    }

    return add_component(page_id, 'JWordCloud', title, x, y, w, h, config)


def add_color_block(page_id, title, x, y, w, h, blocks=None,
                    line_num=2, font_size=16, color='#fff'):
    """
    添加色块指标卡组件（JColorBlock）。

    Args:
        blocks: 指标数据列表 [{'backgroundColor':'#67C23A','prefix':'标签','value':'12345','suffix':'元'}, ...]
                默认使用内置4个示例色块
        line_num: 每行显示几个色块
        font_size: 数值字号
        color: 文字颜色
    """
    mode = _get_mode(page_id)
    if blocks is None:
        blocks = [
            {'backgroundColor': '#67C23A', 'prefix': '朝阳总销售额', 'value': '12345', 'suffix': '亿'},
            {'backgroundColor': '#409EFF', 'prefix': '昌平总销售额', 'value': '12345', 'suffix': '亿'},
            {'backgroundColor': '#E6A23C', 'prefix': '海淀总销售额', 'value': '12345', 'suffix': '亿'},
            {'backgroundColor': '#F56C6C', 'prefix': '西城总销售额', 'value': '12345', 'suffix': '亿'},
        ]

    config = {
        'dataType': 1,
        'background': mode['bg'],
        'borderColor': mode['border_color'],
        'chartData': json.dumps(blocks, ensure_ascii=False),
        'option': {
            'whole': False, 'width': 50, 'height': 50, 'lineNum': line_num,
            'borderSplitx': 20, 'borderSplity': 20, 'decimals': 0,
            'fontSize': font_size, 'color': color, 'fontWeight': 'normal',
            'textAlign': 'center', 'padding': 5,
            'prefixFontSize': 16, 'prefixColor': color, 'prefixFontWeight': 'normal',
            'prefixSplitx': 0, 'prefixSplity': 0,
            'suffix': '', 'suffixSplitx': 40, 'suffixFontSize': 16,
            'suffixColor': color, 'suffixFontWeight': 'normal', 'prefix': '',
            'card': _make_card(mode, title),
            'body': {'text': '', 'color': color, 'fontWeight': 'bold',
                     'marginLeft': 0, 'marginTop': 0},
        },
    }

    return add_component(page_id, 'JColorBlock', title, x, y, w, h, config)


def add_progress(page_id, title, x, y, w, h, data=None,
                 bar_width=19, color='#FF9D00', bg_color='#9C9CA1',
                 border_radius=10):
    """
    添加进度条组件（JProgress）。

    Args:
        data: 进度数据 [{'name':'满意度','value':50}, ...]
        bar_width: 进度条粗细
        color: 进度条颜色
        bg_color: 背景条颜色
        border_radius: 圆角
    """
    mode = _get_mode(page_id)
    if data is None:
        data = [{'name': '满意度', 'value': 50}]

    label_color = mode['title_color']

    config = {
        'dataType': 1,
        'background': mode['bg'],
        'borderColor': mode['border_color'],
        'chartData': json.dumps(data, ensure_ascii=False),
        'option': {
            'valueXOffset': 0, 'valueYOffset': 0,
            'grid': {'show': False, 'top': 0, 'left': 0, 'right': 55,
                     'bottom': 0, 'containLabel': True},
            'yAxis': {'yUnit': '', 'axisLabel': {'show': True, 'color': label_color}},
            'title': {'text': '', 'textAlign': 'left', 'show': False, 'textStyle': {}},
            'tooltip': {'confine': True, 'trigger': 'axis',
                        'axisPointer': {'type': 'none'}},
            'series': [
                {
                    'barWidth': bar_width, 'realtimeSort': True,
                    'label': {'show': False, 'position': 'left',
                              'formatter': '{c}%', 'color': label_color, 'fontSize': 24},
                    'itemStyle': {'normal': {'barBorderRadius': border_radius}},
                    'color': color, 'zlevel': 1,
                },
                {
                    'type': 'bar', 'barGap': '-100%', 'color': bg_color,
                    'barWidth': bar_width,
                    'label': {
                        'show': True, 'valueAnimation': True, 'position': 'right',
                        'color': label_color, 'fontSize': 18,
                        'formatter': '{c}', 'offset': [0, 0],
                    },
                    'itemStyle': {'normal': {'barBorderRadius': border_radius}},
                },
            ],
            'card': _make_card(mode, title),
        },
    }

    return add_component(page_id, 'JProgress', title, x, y, w, h, config)


def add_total_progress(page_id, title, x, y, w, h, data=None,
                       bar_width=19, color='#151B87', bg_color='#eeeeee',
                       border_radius=10):
    """
    添加总进度条组件（JTotalProgress）。

    Args:
        data: 进度数据 [{'value':50}, ...]
        bar_width: 进度条粗细
        color: 进度条颜色
        bg_color: 背景条颜色
        border_radius: 圆角
    """
    mode = _get_mode(page_id)
    if data is None:
        data = [{'value': 50}]

    label_color = mode['title_color']
    if mode is _BIGSCREEN:
        bg_color = '#333333'

    config = {
        'dataType': 1,
        'background': mode['bg'],
        'borderColor': mode['border_color'],
        'chartData': json.dumps(data, ensure_ascii=False),
        'option': {
            'targetValue': {},
            'series': [
                {
                    'barWidth': bar_width,
                    'label': {
                        'show': True, 'position': 'right', 'offset': [0, -40],
                        'formatter': '{c}{a}', 'color': label_color, 'fontSize': 24,
                    },
                    'itemStyle': {'normal': {'barBorderRadius': border_radius}},
                    'color': color, 'zlevel': 1,
                },
                {
                    'type': 'bar', 'barGap': '-100%', 'color': bg_color,
                    'barWidth': bar_width,
                    'itemStyle': {'normal': {'barBorderRadius': border_radius}},
                },
            ],
            'card': _make_card(mode, title),
        },
    }

    return add_component(page_id, 'JTotalProgress', title, x, y, w, h, config)


# ============================================================
# 编辑已有页面
# ============================================================
def update_page(page_id, new_components=None):
    """
    更新已有页面的组件。

    Args:
        page_id: 页面 ID
        new_components: 新的组件列表（完全替换）
    """
    # 查询当前页面信息
    page = query_page(page_id)

    if new_components is not None:
        _page_components[page_id] = new_components
    elif page_id not in _page_components:
        # 从已有页面加载组件
        template = page.get('template', [])
        if isinstance(template, str):
            try:
                template = json.loads(template)
            except:
                template = []
        _page_components[page_id] = template

    return save_page(page_id)


def add_to_existing(page_id, component_func, *args, **kwargs):
    """
    向已有页面追加组件。先加载已有组件，再添加新组件，最后保存。

    用法：
        add_to_existing(page_id, add_number, '新指标', x=500, y=0, w=400, h=200, value=999)
    """
    if page_id not in _page_components or not _page_components[page_id]:
        # 先加载已有组件
        page = query_page(page_id)
        template = page.get('template', [])
        if isinstance(template, str):
            try:
                template = json.loads(template)
            except:
                template = []
        _page_components[page_id] = template

    # 调用组件添加函数
    return component_func(page_id, *args, **kwargs)


# ============================================================
# 菜单 SQL 生成
# ============================================================
ROLE_ID = 'f6817f48af4fb3af11b9e8bf182f618b'


def gen_menu_sql(parent_name, children, icon='ant-design:appstore-outlined', role_id=None):
    """
    生成菜单 SQL + 角色授权 SQL。

    Args:
        parent_name: 父菜单名称
        children: [(名称, page_id, sort_no), ...]
        icon: 父菜单图标
        role_id: 角色 ID，默认使用 ROLE_ID

    Returns:
        SQL 字符串
    """
    rid = role_id or ROLE_ID
    parent_id = _gen_uuid()
    lines = []

    # 父菜单
    lines.append(f"-- 父菜单: {parent_name}")
    lines.append(
        f"INSERT INTO sys_permission(id, parent_id, name, url, component, component_name, "
        f"redirect, menu_type, perms, perms_type, sort_no, always_show, icon, is_route, "
        f"is_leaf, keep_alive, hidden, hide_tab, description, status, del_flag, rule_flag, "
        f"create_by, create_time, update_by, update_time, internal_or_external) "
        f"VALUES ('{parent_id}', NULL, '{parent_name}', '/{parent_id}', "
        f"'layouts/RouteView', NULL, NULL, 0, NULL, '1', 1.00, 0, '{icon}', "
        f"1, 0, 0, 0, 0, NULL, '1', 0, 0, 'admin', now(), NULL, NULL, 0);"
    )
    rp_id = _gen_uuid()
    lines.append(
        f"INSERT INTO sys_role_permission (id, role_id, permission_id, data_rule_ids, "
        f"operate_date, operate_ip) VALUES ('{rp_id}', '{rid}', '{parent_id}', NULL, "
        f"now(), '127.0.0.1');"
    )
    lines.append('')

    # 子菜单
    for name, page_id, sort_no in children:
        menu_id = _gen_uuid()
        lines.append(f"-- 子菜单: {name}")
        lines.append(
            f"INSERT INTO sys_permission(id, parent_id, name, url, component, component_name, "
            f"redirect, menu_type, perms, perms_type, sort_no, always_show, icon, is_route, "
            f"is_leaf, keep_alive, hidden, hide_tab, description, status, del_flag, rule_flag, "
            f"create_by, create_time, update_by, update_time, internal_or_external) "
            f"VALUES ('{menu_id}', '{parent_id}', '{name}', "
            f"'/drag/page/view/{page_id}', "
            f"'super/drag/page/dashboardPreview', 'dashboardPreview', "
            f"NULL, 0, NULL, '1', {sort_no}.00, 0, NULL, 0, 1, 0, 0, 0, NULL, '1', "
            f"0, 0, 'admin', now(), NULL, NULL, 0);"
        )
        rp_id2 = _gen_uuid()
        lines.append(
            f"INSERT INTO sys_role_permission (id, role_id, permission_id, data_rule_ids, "
            f"operate_date, operate_ip) VALUES ('{rp_id2}', '{rid}', '{menu_id}', NULL, "
            f"now(), '127.0.0.1');"
        )
        lines.append('')

    return '\n'.join(lines)


# ============================================================
# 辅助函数
# ============================================================
def _get_category(component):
    """根据组件类型获取分类"""
    category_map = {
        'JBar': 'Bar', 'JHorizontalBar': 'Bar', 'JBackgroundBar': 'Bar',
        'JMultipleBar': 'Bar', 'JNegativeBar': 'Bar', 'JStackBar': 'Bar',
        'JDynamicBar': 'Bar', 'JCapsuleChart': 'Bar',
        'JLine': 'Line', 'JSmoothLine': 'Line', 'JStepLine': 'Line',
        'JMultipleLine': 'Line',
        'JMixLineBar': 'MixLineBar', 'DoubleLineBar': 'DoubleLineBar',
        'JPie': 'Pie', 'JRing': 'Ring', 'JRose': 'Rose',
        'JGauge': 'Gauge', 'JColorGauge': 'Gauge', 'JSemiGauge': 'Gauge',
        'JProgress': 'Progress', 'JCustomProgress': 'Progress',
        'JLiquid': 'Liquid', 'JRadialBar': 'RadialBar',
        'JFunnel': 'Funnel', 'JPyramidFunnel': 'Funnel',
        'JRadar': 'Radar', 'JCircleRadar': 'Radar',
        'JScatter': 'Scatter', 'JBubble': 'Bubble',
        'JWordCloud': 'WordCloud',
        'JAreaMap': 'Map', 'JBubbleMap': 'Map', 'JFlyLineMap': 'Map',
        'JHeatMap': 'Map', 'JBarMap': 'Map',
        'JBar3d': '3D', 'JBarGroup3d': '3D',
        'JNumber': 'Number', 'JCountTo': 'CountTo',
        'JTable': 'Table', 'JScrollTable': 'ScrollTable',
        'JPivotTable': 'PivotTable',
        'JScrollRankingBoard': 'Ranking',
        'JText': 'Text', 'JImg': 'Image',
        'JCarousel': 'Carousel', 'JVideoPlay': 'Video',
        'JCustomButton': 'Button', 'JTabs': 'Tabs',
        'JDragBorder': 'Border', 'JDragDecoration': 'Decoration',
        'JIframe': 'Iframe', 'JCurrentTime': 'Time',
    }
    return category_map.get(component, 'Common')


def _deep_merge(base, override):
    """深度合并字典，override 覆盖 base"""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base
