"""
QQY全组件仪表盘生成脚本（预置脚本，勿修改）
适用于敲敲云（QQY）低代码应用仪表盘，一次生成 30 个统计图表 + 7 个 UI 组件。

用法:
  PYTHONIOENCODING=utf-8 py gen_qqy_all_comps.py \\
    <API_BASE> <TOKEN> \\
    --page-id PAGE_ID \\
    --app-id APP_ID \\
    --tenant-id TENANT_ID \\
    --form-code FORM_CODE \\
    [--form-name 表单名称] \\
    [--form-type design|online]

示例:
  PYTHONIOENCODING=utf-8 py gen_qqy_all_comps.py \\
    <api_base> <token> \\
    --page-id 1204574932509007872 \\
    --app-id 1962454153628905473 \\
    --tenant-id 2 \\
    --form-code jeecg_1111_vjav \\
    --form-name 测试表单

踩坑记录（2026-04-16 首次生成时遇到的问题）：
  1. GBK编码：读取JSON文件必须加 encoding='utf-8'，否则中文字段报 UnicodeDecodeError
  2. Windows无 python3：必须用 py 命令，并加 PYTHONIOENCODING=utf-8 前缀
  3. compStyleConfig + analysis：QQY dataType=4 组件必填，缺少则前端 TypeError 白屏（useChartBiz.ts）
  4. filter.conditionFields：必须存在且为空数组，否则设置弹窗报错
  5. seriesType：必须是数组格式 [{"series":"1","type":"bar"},...] 而非字符串 'bar'
     ⚠️ 但只有 JPivotTable + 4个地图 需要填充非空数组，其余统计图表均为 []（空数组）
  6. 仪表盘类 nameFields=[]：JGauge/JColorGauge/JAntvGauge 只有 valueFields，nameFields 必须为空数组
  7. 散点图 nameFields 必须是数值字段：JScatter/JBubble 的 nameFields 用数值字段（非字符串）
  8. 地图组件需要 commonOption + geo（旧版ECharts格式）+ visualMap（含seriesIndex）
     ⚠️ commonOption 仅地图类型需要，其余统计图表不应包含 commonOption
  9. 各地图 visualMap/commonOption/geo 完全不同（来自参考数据，不可统一处理）：
     JAreaMap : seriesIndex=[0] show=false roam=false  标准commonOption
     JBubbleMap: seriesIndex=[1] show=false roam=false  标准commonOption
     JHeatMap : seriesIndex=[1] show=TRUE  roam=true   commonOption含heat{blurSize:20,pointSize:15}
     JBarMap  : seriesIndex=[0] show=false roam=true   geo含aspectScale:0.96/areaColor:#37805B
     ⚠️ JHeatMap show 必须为 True，否则报 "Heatmap must use with visualMap"
  10. JPivotTable 需要顶层 pivotTable 配置字段，且 isGroup=True
  11. QQY 保存页面 body 必须传 lowAppId，否则应用归属丢失
  12. option.card 必须含 headColor:"#FFFFFF"；title.text 必须设为组件显示名称
  13. option 坐标轴颜色：仪表盘白底禁用大屏暗色 #EEF1FA，不加 axisLabel.color 覆盖
  14. JWordCloud/JTotalProgress/JNumber/JRadar/JCircleRadar/JColorGauge/JAntvGauge 无坐标轴，option 只需 title+card
  15. DoubleLineBar 需要双 yAxis 数组格式，series=[{type:'bar'},{type:'line'}]
  16. filterField 必须包含 5 个系统字段（create_by/update_by/update_time/create_time/bpm_status）
  17. assistYFields/assistTypeFields：只有 JPivotTable + 4个地图 需要填充，其余统计图表均为 []
  18. compStyleConfig.showField 必须是 ''（空字符串），columnFreeze 必须为 False
  19. JHorizontalBar/JRankingList/JTotalProgress 的 category 必须是 'HorizontalBar' 非 'Bar'
"""
import json, time, argparse, copy
import bi_utils

# ── 命令行参数 ────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description='QQY全组件仪表盘生成器')
parser.add_argument('api_base',    help='API地址')
parser.add_argument('token',       help='Token')
parser.add_argument('--page-id',   required=True,  help='已有仪表盘页面ID')
parser.add_argument('--app-id',    required=True,  help='低代码应用ID（QQY appId）')
parser.add_argument('--tenant-id', required=True,  help='租户ID（QQY tenantId）')
parser.add_argument('--form-code', required=True,  help='设计器/Online表单编码')
parser.add_argument('--form-name', default='测试表单', help='表单显示名称')
parser.add_argument('--form-type', default='design', choices=['design', 'online'],
                    help='表单类型（design=设计器表单，online=Online表单）')
args = parser.parse_args()

t0        = time.time()
API_BASE  = args.api_base.rstrip('/')
TOKEN     = args.token
PAGE_ID   = args.page_id
APP_ID    = args.app_id
TENANT_ID = str(args.tenant_id)
FORM_CODE = args.form_code
FORM_NAME = args.form_name
FORM_TYPE = args.form_type

# ── QQY 模式初始化（必须设置 extra_headers）───────────────────────────────────
bi_utils.init_api(API_BASE, TOKEN, extra_headers={
    'X-Low-App-ID': APP_ID,
    'X-Tenant-Id':  TENANT_ID,
})

# ── 查询页面，缓存已有组件（禁止覆盖已有组件）────────────────────────────────
raw    = bi_utils._request('GET', '/drag/page/queryById', params={'id': PAGE_ID})
p_info = raw.get('result') or {}
tmpl   = p_info.get('template') or []
if isinstance(tmpl, str):
    try:    tmpl = json.loads(tmpl)
    except: tmpl = []
bi_utils._page_components[PAGE_ID] = list(tmpl)
bi_utils._page_info[PAGE_ID] = {
    'name':  p_info.get('name', 'QQY全组件仪表盘'),
    'style': p_info.get('style', 'default'),
    'theme': p_info.get('theme', 'default'),
}
existing_count = len(tmpl)

# 新组件追加在已有组件下方
if tmpl:
    START_ROW = max(c.get('y', 0) + c.get('h', 5) for c in tmpl) + 1
else:
    START_ROW = 0
print(f'[页面] {p_info.get("name","?")} (ID: {PAGE_ID}), 已有组件: {existing_count}个, 从y={START_ROW}开始')

# ── 查询表单字段，自动分类 DIM/VAL/GRP/VAL2 ─────────────────────────────────
SKIP_WIDGET_TYPES = {'file-upload', 'imgupload', 'photo'}
NUM_WIDGET_TYPES  = {'money', 'integer', 'number', 'rate', 'slider', 'formula', 'summary'}

if FORM_TYPE == 'design':
    resp = bi_utils._request('GET', f'/desform/api/fields/{FORM_CODE}',
                             params={'subTable': True})
    raw_fields = (resp.get('result') or {}).get('fields', [])
    all_fields = []
    for f in raw_fields:
        ftype = f.get('type', '')
        if ftype in SKIP_WIDGET_TYPES: continue
        opts = f.get('options') or {}
        if opts.get('type') in ('dates', 'daterange', 'datetimerange'): continue
        if not f.get('fieldShow', True): continue
        field_type = 'number' if ftype in NUM_WIDGET_TYPES else 'string'
        all_fields.append({
            'fieldName':      f.get('model', ''),
            'fieldTxt':       f.get('name', ''),
            'fieldType':      field_type,
            'widgetType':     ftype,
            'fieldShow':      True,
            'options':        opts,
            'customDateType': '',
        })
else:
    # Online 表单
    resp    = bi_utils._request('GET', '/online/cgform/head/list', params={'pageSize': 100})
    records = (resp.get('result') or {}).get('records', [])
    head    = next((r for r in records if r.get('tableName') == FORM_CODE), None)
    if not head:
        print(f'[错误] 未找到Online表单: {FORM_CODE}'); sys.exit(1)
    resp2      = bi_utils._request('GET', '/online/cgform/field/listByHeadId',
                                   params={'headId': head['id']})
    raw_fields = resp2.get('result', [])
    all_fields = []
    for f in raw_fields:
        if f.get('dbIsKey') != 0 or f.get('dbIsPersist') == 0: continue
        ftype      = f.get('dbType', 'String')
        field_type = 'number' if ftype in ('int', 'double') else 'string'
        all_fields.append({
            'fieldName':      f.get('dbFieldName', ''),
            'fieldTxt':       f.get('dbFieldTxt', ''),
            'fieldType':      field_type,
            'widgetType':     f.get('fieldShowType', 'text'),
            'fieldShow':      True,
            'options':        [],
            'customDateType': '',
        })

str_fields = [f for f in all_fields if f['fieldType'] == 'string']
num_fields  = [f for f in all_fields if f['fieldType'] == 'number']
if not str_fields and all_fields: str_fields = all_fields[:1]
if not num_fields  and all_fields: num_fields  = all_fields[-1:]

_PH_STR = {'fieldName': 'dim_field', 'fieldTxt': '维度', 'fieldType': 'string',
            'widgetType': 'input', 'fieldShow': True, 'options': [], 'customDateType': ''}
_PH_NUM = {'fieldName': 'val_field', 'fieldTxt': '数值', 'fieldType': 'number',
            'widgetType': 'number', 'fieldShow': True, 'options': [], 'customDateType': '', 'groupField': ''}

DIM  = str_fields[0]  if str_fields else _PH_STR
# 分组字段优先选 select/radio 类型（避免选到 textarea 导致分组无意义）
_select_fields = [f for f in str_fields if f.get('widgetType') in ('select', 'radio', 'checkbox')]
_non_textarea   = [f for f in str_fields if f.get('widgetType') not in ('textarea', 'editor')]
GRP  = (_select_fields[0] if _select_fields else
        _non_textarea[-1] if _non_textarea else
        str_fields[-1])  if str_fields else _PH_STR
VAL  = {**num_fields[0], 'groupField': ''}  if num_fields else _PH_NUM
VAL2 = {**num_fields[1], 'groupField': ''}  if len(num_fields) > 1 else copy.deepcopy(VAL)

print(f'[字段] 维度={DIM["fieldTxt"]}  数值={VAL["fieldTxt"]}  分组={GRP["fieldTxt"]}')

# ── 公共默认值 ─────────────────────────────────────────────────────────────────
# ⚠️ compStyleConfig + analysis：QQY dataType=4 必填，缺少则前端 TypeError 白屏（useChartBiz.ts）
DEFAULT_COMP_STYLE_CONFIG = {
    'summary': {
        'showY': True, 'showTotal': False, 'showField': '',
        'totalType': 'sum', 'showName': '总计',
    },
    'showUnit': {'numberLevel': '', 'position': 'suffix', 'unit': ''},
    'assist': {
        'summary': {'showY': True, 'showField': '', 'totalType': 'sum', 'showName': '总计'},
        'showUnit': {'numberLevel': '', 'position': 'suffix', 'unit': ''},
    },
    # ⚠️ columnFreeze=False（参考数据）；headerFreeze/unilineShow/lineFreeze=True
    'headerFreeze': True, 'unilineShow': True, 'izPage': False,
    'columnFreeze': False, 'lineFreeze': True, 'showProgressText': True,
    'progress': {'show': True, 'name': '进度'},
    'target':   {'show': True, 'name': '目标'},
}
DEFAULT_ANALYSIS = {
    'isRawData': True, 'showMode': 1, 'showData': 1, 'showFields': [],
    'isCompare': False, 'compareType': '', 'trendType': '1',
    'izTimeOut': False, 'timeOut': 0,
}
# CARD：UI 组件 option 外层 card（含 extra/rightHref）
CARD = {'title': '', 'extra': '', 'rightHref': '', 'size': 'default'}

# 系统字段（create_time 也用于 assistTypeFields）
_CREATE_TIME_SYS = {
    'fieldName': 'create_time', 'fieldTxt': '创建时间', 'options': {},
    'fieldType': 'date', 'widgetType': 'date', 'customDateType': '3', 'fieldShow': True,
}
_SYSTEM_FILTER_FIELDS = [
    {'fieldName': 'create_by',  'fieldTxt': '创建人',  'options': {},
     'fieldType': 'select-user', 'widgetType': 'select-user', 'customDateType': '3', 'fieldShow': True},
    {'fieldName': 'update_by',  'fieldTxt': '修改人',  'options': {},
     'fieldType': 'select-user', 'widgetType': 'select-user', 'customDateType': '3', 'fieldShow': True},
    {'fieldName': 'update_time','fieldTxt': '修改时间', 'options': {},
     'fieldType': 'date', 'widgetType': 'date', 'customDateType': '3', 'fieldShow': True},
    {'fieldName': 'create_time','fieldTxt': '创建时间', 'options': {},
     'fieldType': 'date', 'widgetType': 'date', 'customDateType': '3', 'fieldShow': True},
    {'fieldName': 'bpm_status', 'fieldTxt': '流程状态',
     'options': {'dictCode': 'bpm_status', 'remote': 'dict'},
     'fieldType': 'select', 'widgetType': 'select', 'customDateType': '3', 'fieldShow': True},
]

# filterField：系统字段在前，表单字段在后（供联动过滤使用）
FILTER_FIELD = _SYSTEM_FILTER_FIELDS + [
    {k: f[k] for k in ('fieldName', 'fieldTxt', 'fieldType', 'widgetType',
                        'fieldShow', 'options', 'customDateType')}
    for f in all_fields
]

# ── 各图表类型默认 ECharts option ──────────────────────────────────────────────
# ⚠️ 参考标准：以实测可用的参考JSON为准，非文档猜测
# ⚠️ option.card 必须含 headColor:"#FFFFFF"；title.text 必须设为组件显示名称
# ⚠️ 仪表盘白底主题：不加 axisLabel.color 等颜色覆盖（禁用大屏暗色 #EEF1FA 等）
_MAP_TYPES = {'JBarMap', 'JAreaMap', 'JBubbleMap', 'JHeatMap'}


def _get_default_chart_option(chart_type, name=''):
    """根据图表类型返回 ECharts option。以参考JSON为权威标准。"""
    # option 内部使用的 card（含 headColor，无 extra/rightHref）
    CARD_OPT = {'title': '', 'size': 'default', 'headColor': '#FFFFFF'}
    TITLE = {'show': True, 'text': name}

    # ── 地图（每种地图配置完全不同，按类型分别处理）────────────────────────────
    # ⚠️ JHeatMap: show=True 必须，否则报 "Heatmap must use with visualMap"
    # ⚠️ JBarMap: geo 含 aspectScale:0.96 / areaColor:'#37805B' / roam:true
    # ⚠️ JHeatMap/JBarMap/JBubbleMap: roam=true；JAreaMap: roam=false（对照手工气泡图）
    if chart_type in _MAP_TYPES:
        roam = chart_type in ('JHeatMap', 'JBarMap', 'JBubbleMap')
        # geo：JBarMap 特有 aspectScale 和 areaColor
        if chart_type == 'JBarMap':
            geo = {
                'top': 30, 'aspectScale': 0.96, 'zoom': 1, 'roam': True,
                'label': {'emphasis': {'color': '#fff', 'show': False}},
                'itemStyle': {
                    'normal': {'shadowOffsetX': 0, 'shadowOffsetY': 0, 'borderColor': '#a9a9a9',
                               'areaColor': '#37805B', 'shadowBlur': 0, 'borderWidth': 1,
                               'shadowColor': '#80d9f8'},
                    'emphasis': {'areaColor': '#fff59c'}},
            }
        else:
            geo = {
                'top': 30, 'zoom': 1, 'roam': roam,
                'label': {'emphasis': {'color': '#fff', 'show': False}},
                'itemStyle': {
                    'normal': {'shadowOffsetX': 0, 'borderColor': '#a9a9a9',
                               'shadowOffsetY': 0, 'areaColor': '',
                               'shadowBlur': 0, 'borderWidth': 1, 'shadowColor': '#80d9f8'},
                    'emphasis': {'areaColor': '#fff59c', 'borderWidth': 0}},
            }
        area = {
            'markerColor': '#df2425' if chart_type == 'JHeatMap' else '#DDE330',
            'shadowBlur': 10, 'markerCount': 5, 'markerOpacity': 1,
            'name': ['中国'], 'scatterLabelShow': False,
            'shadowColor': '#DDE330', 'value': ['china'], 'markerType': 'effectScatter',
        }
        # visualMap 按类型分别配置
        if chart_type == 'JBarMap':
            vm = {'max': 200, 'show': False, 'seriesIndex': [0]}
        elif chart_type == 'JHeatMap':
            vm = {'min': 0, 'top': 'bottom', 'max': 200, 'left': '5%',
                  'calculable': True, 'show': True, 'type': 'continuous', 'seriesIndex': [1]}
        elif chart_type == 'JBubbleMap':
            vm = {'min': 0, 'top': 'bottom', 'max': 200, 'left': '5%',
                  'calculable': True, 'show': False, 'type': 'continuous', 'seriesIndex': [1]}
        else:  # JAreaMap
            vm = {'min': 0, 'top': 'bottom', 'max': 200, 'left': '5%',
                  'calculable': True, 'show': False, 'type': 'continuous', 'seriesIndex': [0]}
        opt = {
            'drillDown': False, 'area': area, 'geo': geo,
            'grid': {'bottom': 115, 'show': False}, 'legend': {'data': []},
            'title': {'left': 10, 'show': True, 'text': name,
                      'textStyle': {'fontWeight': 'normal'}},
            'graphic': [],
            'card': {'rightHref': '', 'size': 'default', 'extra': '', 'title': '',
                     'headColor': '#FFFFFF'},
            'visualMap': vm,
        }
        # Bubble/Heat：勿预置 series（含空数组也可能干扰）；Area/Bar 可写 map series
        if chart_type in ('JAreaMap', 'JBarMap'):
            opt['series'] = [{'type': 'map', 'map': 'china', 'geoIndex': 0, 'data': []}]
        return opt

    # ── 无坐标轴类型（只需 title + card）──────────────────────────────────────
    # ⚠️ JWordCloud/JTotalProgress/JNumber/JRadar/JCircleRadar/JAntvGauge 均如此
    # JColorGauge 不可只写 title+card，否则白屏（须完整 gauge + axisLine 分段色）
    if chart_type in ('JWordCloud', 'JTotalProgress', 'JNumber',
                      'JRadar', 'JCircleRadar', 'JAntvGauge'):
        return {'title': TITLE, 'card': copy.deepcopy(CARD_OPT)}

    # ── 透视表（title text 固定为"表格"）─────────────────────────────────────
    if chart_type == 'JPivotTable':
        return {'title': {'show': True, 'text': '表格'}, 'card': copy.deepcopy(CARD_OPT)}

    # ── JColorGauge 多色仪表盘（必须 axisLine 分段色 + type:gauge）──────────────
    if chart_type == 'JColorGauge':
        return {
            'series': [{
                'axisLabel': {'show': True, 'fontSize': 12},
                'pointer': {'width': 8},
                'axisLine': {
                    'lineStyle': {
                        'width': 10,
                        'color': [[0.33, '#52C41A'], [0.66, '#FAAD14'], [1, '#FF4D4F']],
                    }
                },
                'anchor': {'itemStyle': {'color': '#FAC858'}},
                'splitLine': {'length': 12, 'lineStyle': {'color': '#eee', 'width': 4}},
                'axisTick': {'show': True, 'lineStyle': {'color': '#eee'}},
                'title': {'fontSize': 14},
                'detail': {'formatter': '{value}%', 'fontSize': 25},
                'min': 0, 'max': 100, 'data': [], 'type': 'gauge',
            }],
            'tooltip': {'formatter': '{a} <br/>{b} : {c}%'},
            'title': TITLE, 'card': copy.deepcopy(CARD_OPT),
        }

    # ── JGauge 基础仪表盘 ─────────────────────────────────────────────────────
    if chart_type == 'JGauge':
        return {
            'series': [{'min': 0, 'data': [], 'max': 100,
                        'axisTick': {'lineStyle': {'color': '#eee'}, 'show': True},
                        'detail': {'formatter': '{value}'},
                        'type': 'gauge'}],
            'title': TITLE, 'card': copy.deepcopy(CARD_OPT),
        }

    # ── 饼图系列 ──────────────────────────────────────────────────────────────
    if chart_type == 'JPie':
        return {
            'series': [{'data': [], 'type': 'pie'}],
            'title': TITLE, 'card': copy.deepcopy(CARD_OPT),
        }
    if chart_type == 'JRing':
        return {
            'series': [{'data': [], 'avoidLabelOverlap': False,
                        'label': {'show': False}, 'labelLine': {'show': False},
                        'type': 'pie', 'radius': ['40%', '70%']}],
            'title': TITLE, 'card': copy.deepcopy(CARD_OPT),
        }
    if chart_type == 'JRose':
        return {
            'series': [{'data': [], 'roseType': 'area', 'type': 'pie'}],
            'title': TITLE, 'card': copy.deepcopy(CARD_OPT),
        }

    # ── 漏斗图 ────────────────────────────────────────────────────────────────
    if chart_type in ('JFunnel', 'JPyramidFunnel'):
        sort = 'descending' if chart_type == 'JFunnel' else 'ascending'
        return {
            'series': [{'data': [], 'left': '10%', 'gap': 2,
                        'name': 'Funnel', 'sort': sort, 'type': 'funnel'}],
            'title': TITLE, 'card': copy.deepcopy(CARD_OPT),
        }

    # ── 横向条形图（JHorizontalBar + JRankingList：y轴为category，x轴为value）──
    if chart_type in ('JHorizontalBar', 'JRankingList'):
        return {
            'yAxis': {'data': [], 'type': 'category'},
            'xAxis': {'type': 'value'},
            'series': [{'type': 'bar'}],
            'grid': {'containLabel': True},
            'title': TITLE, 'card': copy.deepcopy(CARD_OPT),
        }

    # ── 双轴图（yAxis 为数组，series 含 bar + line）──────────────────────────
    if chart_type == 'DoubleLineBar':
        return {
            'yAxis': [{'type': 'value'}, {'type': 'value'}],
            'xAxis': {'type': 'category'},
            'series': [{'type': 'bar'}, {'type': 'line'}],
            'grid': {'containLabel': True},
            'title': TITLE, 'card': copy.deepcopy(CARD_OPT),
        }

    # ── 散点/气泡图（x/y 轴均为 value）─────────────────────────────────────
    if chart_type in ('JScatter', 'JBubble'):
        return {
            'yAxis': {'type': 'value'},
            'xAxis': {'type': 'value'},
            'series': [{'type': 'scatter'}],
            'grid': {'containLabel': True},
            'title': TITLE, 'card': copy.deepcopy(CARD_OPT),
        }

    # ── 基础柱形图（单系列，xAxis 含 data:[]）────────────────────────────────
    if chart_type == 'JBar':
        return {
            'yAxis': {'type': 'value'},
            'xAxis': {'data': [], 'type': 'category'},
            'series': [{'type': 'bar'}],
            'grid': {'containLabel': True},
            'title': TITLE, 'card': copy.deepcopy(CARD_OPT),
        }

    # ── 分组柱形图（isGroup=True，xAxis 无 data:[]）──────────────────────────
    if chart_type in ('JStackBar', 'JMultipleBar', 'JNegativeBar'):
        return {
            'yAxis': {'type': 'value'},
            'xAxis': {'type': 'category'},
            'series': [{'type': 'bar'}],
            'grid': {'containLabel': True},
            'title': TITLE, 'card': copy.deepcopy(CARD_OPT),
        }

    # ── 基础折线图/面积图（单系列，xAxis 含 data:[]）─────────────────────────
    if chart_type in ('JLine', 'JArea'):
        return {
            'yAxis': {'type': 'value'},
            'xAxis': {'data': [], 'type': 'category'},
            'series': [{'type': 'line'}],
            'grid': {'containLabel': True},
            'title': TITLE, 'card': copy.deepcopy(CARD_OPT),
        }

    # ── 对比折线图（isGroup=True，xAxis 无 data:[]）──────────────────────────
    if chart_type == 'JMultipleLine':
        return {
            'yAxis': {'type': 'value'},
            'xAxis': {'type': 'category'},
            'series': [{'type': 'line'}],
            'grid': {'containLabel': True},
            'title': TITLE, 'card': copy.deepcopy(CARD_OPT),
        }

    # ── 兜底（不应到达此处，返回最小结构）────────────────────────────────────
    return {'title': TITLE, 'card': copy.deepcopy(CARD_OPT)}


def _get_chart_common_option(chart_type):
    """地图类型专用 commonOption。
    ⚠️ 只有地图类型需要 commonOption，其余统计图表不应包含此字段。
    JHeatMap 的 heat 字段：blurSize:20 pointSize:15（来自参考数据）
    """
    if chart_type == 'JHeatMap':
        return {
            'heat': {'blurSize': 20, 'pointSize': 15, 'maxOpacity': 1},
            'barSize': 10, 'gradientColor': False,
            'breadcrumb': {'drillDown': False, 'textColor': '#000000'},
            'areaColor': {'color1': '#f7f7f7', 'color2': '#fcc02e'},
            'barColor': '#fff176', 'barColor2': '#fcc02e',
            'inRange': {'color': ['#04387b', '#467bc0']},
        }
    if chart_type == 'JBarMap':
        return {
            'barSize': 12, 'gradientColor': False,
            'breadcrumb': {'drillDown': False, 'textColor': '#000000'},
            'areaColor': {'color1': '#f7f7f7', 'color2': '#fcc02e'},
            'barColor': '#fff176', 'barColor2': '#fcc02e',
            'inRange': {'color': ['#04387b', '#467bc0']},
        }
    # JAreaMap / JBubbleMap
    return {
        'barSize': 10, 'gradientColor': False,
        'breadcrumb': {'drillDown': False, 'textColor': '#000000'},
        'areaColor': {'color1': '#f7f7f7', 'color2': '#fcc02e'},
        'barColor': '#fff176', 'barColor2': '#fcc02e',
        'inRange': {'color': ['#04387b', '#467bc0']},
    }


# ── mk_cfg：构建 dataType=4 统计图表 config ──────────────────────────────────
# ⚠️ seriesType/assistYFields/assistTypeFields：
#    只有 JPivotTable + 4个地图 填充非空值，其余统计图表均为 []（空数组）
# ⚠️ commonOption：只有地图类型需要，其余统计图表不加此字段
_SERIES_TYPE_ARRAY = [
    {'series': '1', 'type': 'bar'},
    {'series': '2', 'type': 'bar'},
    {'series': '',  'type': 'bar'},
]
_PIVOT_OR_MAP_TYPES = {'JPivotTable', 'JAreaMap', 'JBubbleMap', 'JHeatMap', 'JBarMap'}


def mk_cfg(category, subclass, is_group,
           name_fields, value_fields, type_fields=None,
           option=None, name='', pivot_table=None):
    """
    构建 QQY 统计图表配置（dataType=4）。
    ⚠️ name 参数用于 option.title.text，必须传入组件显示名称。
    ⚠️ series_type / common_option 已移除：由内部逻辑自动处理。
    """
    _is_pivot_or_map = subclass in _PIVOT_OR_MAP_TYPES
    _type_fields = list(type_fields) if type_fields else []
    cfg = {
        'dataType':  4,
        'formType':  FORM_TYPE,
        'formId':    FORM_CODE,
        'formName':  FORM_NAME,
        'tableName': FORM_CODE,
        'type':      FORM_TYPE,
        'appId':     APP_ID,
        'appType':   'current',
        'nameFields':       list(name_fields),
        'valueFields':      list(value_fields),
        'typeFields':       _type_fields,
        # ⚠️ 只有 JPivotTable + 地图 填充 assistYFields/assistTypeFields，其余为 []
        'assistYFields':    list(value_fields) if _is_pivot_or_map else [],
        'assistTypeFields': [copy.deepcopy(_CREATE_TIME_SYS)] if _is_pivot_or_map else [],
        'calcFields':       [],
        'dataNum':    '',
        'sorts':  {'name': '', 'type': ''},
        'filter': {'queryField': 'create_time', 'queryRange': 'all',
                   'conditionFields': [], 'customTime': [], 'conditionMode': 'and'},
        'chart':  {'category': category, 'subclass': subclass, 'isGroup': is_group},
        'compStyleConfig': copy.deepcopy(DEFAULT_COMP_STYLE_CONFIG),
        'analysis':        copy.deepcopy(DEFAULT_ANALYSIS),
        'filterField':     copy.deepcopy(FILTER_FIELD),
        # ⚠️ option 必须是完整配置，title.text 来自 name 参数
        'option':          option if option is not None else _get_default_chart_option(subclass, name),
        'actionConfig':    {'operateType': 'modal', 'modalName': '', 'url': ''},
        'turnConfig': {'url': ''},
        'jsConfig':   '',
        'drillData':  [],
        'authFieldShowResult': [],
        'timeOut':    0,
        'background':  '#FFFFFF',
        'borderColor': '#E8E8E8',
        # ⚠️ 只有 JPivotTable + 地图 填充 seriesType，其余为 []
        'seriesType': copy.deepcopy(_SERIES_TYPE_ARRAY) if _is_pivot_or_map else [],
    }
    # ⚠️ commonOption 只给地图类型，其余统计图表不加此字段
    if subclass in _MAP_TYPES:
        cfg['commonOption'] = _get_chart_common_option(subclass)
    # ⚠️ pivotTable：透视表必须包含顶层 pivotTable 配置
    if pivot_table:
        cfg['pivotTable'] = pivot_table
    return cfg


# ── 透视表顶层配置（使用所有数值字段）─────────────────────────────────────────
# ⚠️ pivotTable 的 columnSummary/lineSummary/unitList 必须包含所有数值字段的 key
_val_keys = [f['fieldName'] for f in num_fields] if num_fields else [VAL['fieldName']]
PIVOT_TABLE_CFG = {
    'columnSummary': {
        'controlList': [{'showName': '', 'show': True, 'totalType': 'sum',
                         'position': '2', 'key': k} for k in _val_keys],
        'name': '列汇总', 'location': 'right',
    },
    'lineSummary': {
        'controlList': [{'showName': '', 'show': True, 'totalType': 'sum',
                         'key': k} for k in _val_keys],
        'name': '行汇总', 'location': 'bottom',
    },
    'unitList': [{'unit': '', 'numberLevel': '', 'position': 'suffix',
                  'decimal': 0, 'key': k} for k in _val_keys],
    'showLineCount': 0, 'showColumnCount': 0,
    'showColumnTotal': False, 'showLineTotal': False,
}

# ── 全组件列表 (comp_type, name, cfg, w, h) ───────────────────────────────────
# 30 个统计图表（dataType=4，绑定设计器/Online表单）+ 7 个 UI 组件（dataType=1）
ALL_COMPS = [
    # ── 柱形图（4个）──────────────────────────────────────────────────────────
    ('JBar',          '基础柱形图',
     mk_cfg('Bar', 'JBar', False, [DIM], [VAL], name='基础柱形图'),                              12, 28),
    ('JStackBar',     '堆叠柱形图',
     mk_cfg('Bar', 'JStackBar', True, [DIM], [VAL], [GRP], name='堆叠柱形图'),                  12, 28),
    ('JMultipleBar',  '对比柱形图',
     mk_cfg('Bar', 'JMultipleBar', True, [DIM], [VAL], [GRP], name='对比柱形图'),               12, 28),
    ('JNegativeBar',  '正负条形图',
     mk_cfg('Bar', 'JNegativeBar', True, [DIM], [VAL], [GRP], name='正负条形图'),               12, 28),

    # ── 条形图（3个）──────────────────────────────────────────────────────────
    ('JHorizontalBar', '基础条形图',
     mk_cfg('HorizontalBar', 'JHorizontalBar', False, [DIM], [VAL], name='基础条形图'),          12, 28),
    ('JRankingList',  '排行榜',
     mk_cfg('HorizontalBar', 'JRankingList', False, [DIM], [VAL], name='排行榜'),               12, 28),
    ('JTotalProgress', '统计进度图',
     mk_cfg('HorizontalBar', 'JTotalProgress', True, [DIM], [VAL], [GRP], name='统计进度图'),   12, 28),

    # ── 折线图（4个）──────────────────────────────────────────────────────────
    ('JLine',         '基础折线图',
     mk_cfg('Line', 'JLine', False, [DIM], [VAL], name='基础折线图'),                            12, 28),
    ('JArea',         '面积图',
     mk_cfg('Line', 'JArea', False, [DIM], [VAL], name='面积图'),                               12, 28),
    ('JMultipleLine', '对比折线图',
     mk_cfg('Line', 'JMultipleLine', True, [DIM], [VAL], [GRP], name='对比折线图'),             12, 28),
    ('DoubleLineBar', '双轴图',
     mk_cfg('Line', 'DoubleLineBar', True, [DIM], [VAL], [GRP], name='双轴图'),                 12, 28),

    # ── 字符云（1个）──────────────────────────────────────────────────────────
    ('JWordCloud',    '字符云',
     mk_cfg('WordCloud', 'JWordCloud', False, [DIM], [VAL], name='字符云'),                     12, 28),

    # ── 饼图（3个）────────────────────────────────────────────────────────────
    ('JPie',          '饼图',
     mk_cfg('Pie', 'JPie', False, [DIM], [VAL], name='饼图'),                                   10, 28),
    ('JRing',         '饼状环形图',
     mk_cfg('Pie', 'JRing', False, [DIM], [VAL], name='饼状环形图'),                            10, 28),
    ('JRose',         '南丁格尔玫瑰图',
     mk_cfg('Pie', 'JRose', False, [DIM], [VAL], name='南丁格尔玫瑰图'),                        10, 28),

    # ── 漏斗图（2个）──────────────────────────────────────────────────────────
    ('JFunnel',       '普通漏斗图',
     mk_cfg('Funnel', 'JFunnel', False, [DIM], [VAL], name='普通漏斗图'),                       10, 28),
    ('JPyramidFunnel', '金字塔漏斗图',
     mk_cfg('Funnel', 'JPyramidFunnel', False, [DIM], [VAL], name='金字塔漏斗图'),              10, 28),

    # ── 雷达图（2个）──────────────────────────────────────────────────────────
    ('JRadar',        '普通雷达图',
     mk_cfg('Radar', 'JRadar', False, [DIM], [VAL], name='普通雷达图'),                         12, 28),
    ('JCircleRadar',  '圆形雷达图',
     mk_cfg('Radar', 'JCircleRadar', False, [DIM], [VAL], name='圆形雷达图'),                   12, 28),

    # ── 仪表盘（3个）：nameFields=[] 只有 valueFields ──────────────────────────
    # ⚠️ 仪表盘类 nameFields 必须为空数组；JColorGauge/JAntvGauge option 只有 title+card
    ('JColorGauge',   '多色仪表盘',
     mk_cfg('Gauge', 'JColorGauge', False, [], [VAL], name='多色仪表盘'),                        6, 25),
    ('JGauge',        '基础仪表盘',
     mk_cfg('Gauge', 'JGauge', False, [], [VAL], name='基础仪表盘'),                             6, 25),
    ('JAntvGauge',    '渐变仪表盘',
     mk_cfg('Gauge', 'JAntvGauge', False, [], [VAL], name='渐变仪表盘'),                         6, 25),

    # ── 数值（1个）────────────────────────────────────────────────────────────
    ('JNumber',       '数字卡片',
     mk_cfg('Number', 'JNumber', False, [DIM], [VAL], name='数字卡片'),                          6, 17),

    # ── 散点图（2个）：⚠️ JScatter nameFields 必须是数值字段（非字符串）─────────
    ('JScatter',      '普通散点图',
     mk_cfg('Scatter', 'JScatter', False, [VAL], [VAL2], name='普通散点图'),                    12, 28),
    ('JBubble',       '气泡图',
     mk_cfg('Scatter', 'JBubble', True, [DIM], [VAL], [GRP], name='气泡图'),                   12, 28),

    # ── 透视表（1个）──────────────────────────────────────────────────────────
    ('JPivotTable',   '透视表',
     mk_cfg('Table', 'JPivotTable', True, [DIM], [VAL],
            name='透视表', pivot_table=PIVOT_TABLE_CFG),                                        14, 30),

    # ── 地图（4个）────────────────────────────────────────────────────────────
    # ⚠️ commonOption/seriesType/assistYFields 由 mk_cfg 根据 _is_pivot_or_map 自动处理
    # ⚠️ visualMap.seriesIndex：JAreaMap/JBarMap=[0]，JBubbleMap/JHeatMap=[1]（内置）
    ('JAreaMap',      '区域地图',
     mk_cfg('Map', 'JAreaMap', False, [DIM], [VAL], name='区域地图'),                           14, 35),
    ('JBubbleMap',    '散点地图',
     mk_cfg('Map', 'JBubbleMap', False, [DIM], [VAL], name='散点地图'),                         14, 35),
    ('JHeatMap',      '热力地图',
     mk_cfg('Map', 'JHeatMap', False, [DIM], [VAL], name='热力地图'),                           14, 35),
    ('JBarMap',       '柱形地图',
     mk_cfg('Map', 'JBarMap', False, [DIM], [VAL], name='柱形地图'),                            14, 35),

    # ── 7个UI组件（dataType=1，静态数据）──────────────────────────────────────
    ('JText',         '文本组件',     {
        'dataType': 1, 'url': '', 'timeOut': 0, 'linkageConfig': [],
        'turnConfig': {'url': ''},
        'chartData': '文本内容示例',
        'background': '#FFFFFF', 'borderColor': '#E8E8E8',
        'option': {
            'horseLamp': False, 'speed': 1000, 'card': copy.deepcopy(CARD),
            'body': {'text': '文本内容示例', 'color': '#464646', 'fontWeight': 'bold',
                     'marginLeft': 0, 'marginTop': 20, 'letterSpacing': 0,
                     'fontSize': 22, 'textAlign': 'center'},
        },
    }, 12, 17),

    ('JCurrentTime',  '实时日期',     {
        'dataType': 1, 'url': '', 'timeOut': 0, 'turnConfig': {'url': ''}, 'chartData': '',
        'background': '#3F7DD4', 'borderColor': '#E8E8E8',
        # ⚠️ showWeek 必须是字符串 'show'/'hide'，禁止用布尔值
        'option': {
            'showWeek': 'show', 'card': copy.deepcopy(CARD),
            'body': {'text': '', 'color': '#FFFFFF', 'fontWeight': 'normal',
                     'marginLeft': 0, 'marginTop': 13},
        },
    }, 12, 17),

    ('JFilterQuery',  '查询条件',     {
        'dataType': 1, 'url': '', 'timeOut': 0,
        'chartData': [],  # ⚠️ 空数组（非 dict）
        'background': '#FFFFFF', 'borderColor': '#E8E8E8',
    }, 24, 10),

    ('JCustomButton', '自定义按钮',   {
        'dataType': 1, 'url': '', 'timeOut': 0,
        'chartData': [{
            'btnId':         str(int(time.time() * 1000)),
            'title':         '示例按钮',
            'icon':          'ant-design:plus-outlined',
            'color':         '#1890FF',
            'operationType': '4',
            'worksheet': '', 'view': '', 'defVal': [], 'customPage': '',
            'href':          {'url': '', 'isParam': False, 'params': []},
            'openMode':      '2',
            'bizFlow':       '',
            'click': {'type': '1', 'message': {
                'title': '你确认执行此操作吗？', 'okText': '确认', 'cancelText': '取消',
            }},
        }],
        'option': {'title': '', 'btnType': 'button', 'btnStyle': 'solid',
                   'btnWidth': 'custom', 'btnDirection': 'column', 'rowNum': 4},
        'background': '#FFFFFF', 'borderColor': '#E8E8E8',
    }, 12, 17),

    ('JDragEditor',   '富文本',       {
        'dataType': 1, 'timeOut': 0,
        'chartData': '<p>富文本内容示例</p>',
        'background': '#FFFFFF', 'borderColor': '#E8E8E8',
    }, 12, 20),

    ('JIframe',       '嵌入URL',      {
        'dataType': 1, 'url': 'https://www.jeecg.com', 'timeOut': 0, 'chartData': '',
        'background': '#FFFFFF', 'borderColor': '#E8E8E8',
        'option': {'card': copy.deepcopy(CARD), 'body': {'url': 'https://www.jeecg.com'}},
    }, 12, 30),

    ('JCarousel',     '轮播图（静态）', {
        'dataType': 1, 'url': '', 'timeOut': 0, 'linkageConfig': [],
        'chartData': '[]',
        'background': '#FFFFFF', 'borderColor': '#E8E8E8',
    }, 12, 25),
]

# ── 24列栅格自动布局（行填充算法）────────────────────────────────────────────
TOTAL_COLS = 24
cur_x, cur_y, row_h = 0, START_ROW, 0
placements = []  # [(x, y, w, h), ...]

for _, _, _, w, h in ALL_COMPS:
    if cur_x + w > TOTAL_COLS:
        cur_y += row_h + 1
        cur_x  = 0
        row_h  = 0
    placements.append((cur_x, cur_y, w, h))
    cur_x += w
    row_h  = max(row_h, h)

# ── 添加组件到页面 ────────────────────────────────────────────────────────────
components = bi_utils._page_components[PAGE_ID]
base_ts    = int(time.time() * 1000)
added      = 0

for i, ((comp_type, name, cfg, w, h), (x, y, w2, h2)) in enumerate(
        zip(ALL_COMPS, placements)):
    cfg = copy.deepcopy(cfg)
    # ⚠️ size 字段用像素（width=w×75，height=h×11），不是栅格单位
    cfg['size'] = {'width': w2 * 75, 'height': h2 * 11}

    # chartData 序列化（list/dict → JSON字符串）
    if 'chartData' in cfg and not isinstance(cfg['chartData'], str):
        cfg['chartData'] = json.dumps(cfg['chartData'], ensure_ascii=False)

    comp = {
        'i':             str(base_ts + i * 10),
        'x':             x,
        'y':             y,
        'w':             w2,
        'h':             h2,
        'component':     comp_type,
        'componentName': name,
        'config':        cfg,
    }
    components.append(comp)
    added += 1
    print(f'  [{added:>2}] {name} ({comp_type})  x={x} y={y} w={w2} h={h2}')

# ── 保存页面（⚠️ 必须传 lowAppId，否则应用归属丢失）────────────────────────────
raw2   = bi_utils._request('GET', '/drag/page/queryById', params={'id': PAGE_ID})
p2     = raw2.get('result') or {}
info   = bi_utils._page_info.get(PAGE_ID, {})
payload = {
    'id':          PAGE_ID,
    'name':        info.get('name', 'QQY全组件仪表盘'),
    'template':    json.dumps(components, ensure_ascii=False),
    'updateCount': p2.get('updateCount', 1),
    'style':       info.get('style', 'default'),
    'theme':       info.get('theme', 'default'),
    'lowAppId':    APP_ID,
}
bi_utils._request('POST', '/drag/page/edit', data=payload)

elapsed = time.time() - t0
print(f'\n[保存完成] 共添加 {added} 个组件（已有 {existing_count} 个）')
print(f'页面 ID: {PAGE_ID}')
print(f'耗时: {elapsed:.1f}s')
