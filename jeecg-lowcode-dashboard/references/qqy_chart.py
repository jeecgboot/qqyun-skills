# -*- coding: utf-8 -*-
"""QQY dataType=4 统计图表 config 构建器。qqy_ops.py 使用，禁止业务侧手写 config。"""
import copy
import json
import os

SKIP_WIDGET_TYPES = {'file-upload', 'imgupload', 'photo', 'location'}
NUM_WIDGET_TYPES = {'money', 'integer', 'number', 'rate', 'slider', 'formula', 'summary', 'calcVal'}
DATE_WIDGET_TYPES = {'date', 'datetime', 'time'}

# nameFields 日期归组（FieldConfig.vue）；filterField 系统日期 customDateType 固定 '3'
DATE_GROUP = {
    '1': '年(YYYY)',
    '6': '年月(YYYY年M月)',
    '2': '月(YYYY-MM)',
    '7': '月(M月)',
    '3': '日(YYYY-MM-DD)',
    '4': '时(YYYY-MM-DD hh)',
    '5': '分(YYYY-MM-DD hh:mm)',
}
# 计算值 $model-N$ 聚合码（JTagInput.vue formulaType）
CALC_AGG = {'1': '求和', '2': '最大值', '3': '最小值', '4': '平均值', '5': '计算'}
# 查询范围（ChartSetModal / useOnlineDataBiz rangeOptions，共 16）
QUERY_RANGE = (
    'all', 'last7days', 'last30days',
    'today', 'yesterday', 'tomorrow',
    'week', 'preWeek', 'nextWeek',
    'month', 'preMonth', 'nextMonth',
    'year', 'preYear', 'nextYear',
    'custom',
)

QQY_CHARTS = {
    'JBar', 'JStackBar', 'JMultipleBar', 'JNegativeBar',
    'JHorizontalBar', 'JRankingList', 'JTotalProgress',
    'JLine', 'JArea', 'JMultipleLine', 'DoubleLineBar',
    'JWordCloud', 'JPie', 'JRing', 'JRose',
    'JFunnel', 'JPyramidFunnel', 'JRadar', 'JCircleRadar',
    'JColorGauge', 'JGauge', 'JAntvGauge', 'JNumber',
    'JScatter', 'JBubble', 'JPivotTable',
    'JAreaMap', 'JBubbleMap', 'JHeatMap', 'JBarMap',
}

# 口语 → 组件。skill 禁止再维护对照表；新说法加这里。
COMP_ALIAS = {
    '柱状图': 'JBar', '基础柱形图': 'JBar', '柱形图': 'JBar', '柱': 'JBar',
    '折线图': 'JLine', '折线': 'JLine',
    '面积图': 'JLine',
    '饼图': 'JPie', '饼': 'JPie',
    '环形图': 'JRing', '环图': 'JRing', '环形': 'JRing',
    '玫瑰图': 'JRose',
    '词云': 'JWordCloud', '词云图': 'JWordCloud', '字符云': 'JWordCloud',
    '透视表': 'JPivotTable', '透视': 'JPivotTable',
    '双轴图': 'DoubleLineBar', '双轴': 'DoubleLineBar',
    '多折线': 'JMultipleLine', '多折线图': 'JMultipleLine',
    '数字卡': 'JNumber', '数字': 'JNumber', '指标卡': 'JNumber',
    '排行榜': 'JRankingList', '横向排行榜': 'JRankingList', '排行': 'JRankingList',
    '条形图': 'JHorizontalBar', '基础条形图': 'JHorizontalBar', '横向条形': 'JHorizontalBar',
    '区域地图': 'JAreaMap', '中国区域地图': 'JAreaMap',
    '气泡地图': 'JBubbleMap', '中国气泡地图': 'JBubbleMap',
    '热力地图': 'JHeatMap',
    '柱状地图': 'JBarMap', '柱形地图': 'JBarMap', '立体柱地图': 'JBarMap',
    '雷达图': 'JRadar', '雷达': 'JRadar', '普通雷达图': 'JRadar',
    '圆形雷达图': 'JCircleRadar', '圆形雷达': 'JCircleRadar', '圈雷达': 'JCircleRadar',
    '堆叠柱': 'JStackBar', '堆叠柱状图': 'JStackBar', '堆叠柱形图': 'JStackBar',
    '对比柱形图': 'JMultipleBar', '对比柱': 'JMultipleBar', '多柱': 'JMultipleBar',
    '分组柱': 'JMultipleBar', '多系列柱': 'JMultipleBar',
    '正负条形图': 'JNegativeBar', '正负柱': 'JNegativeBar', '正负条': 'JNegativeBar',
    '散点图': 'JScatter', '散点': 'JScatter', '普通散点图': 'JScatter',
    '散点地图': 'JBubbleMap',
    '气泡图': 'JBubble', '气泡': 'JBubble',
    '漏斗图': 'JFunnel', '普通漏斗图': 'JFunnel', '漏斗': 'JFunnel',
    '金字塔漏斗图': 'JPyramidFunnel', '金字塔漏斗': 'JPyramidFunnel', '金字塔': 'JPyramidFunnel',
    '南丁格尔玫瑰图': 'JRose', '南丁格尔': 'JRose', '玫瑰': 'JRose',
    '饼状环形图': 'JRing',
    '基础折线图': 'JLine', '对比折线图': 'JMultipleLine',
    '多色仪表盘': 'JColorGauge', '色阶仪表盘': 'JColorGauge', '色阶仪表': 'JColorGauge',
    '基础仪表盘': 'JGauge', '仪表盘': 'JGauge', '仪表': 'JGauge',
    '渐变仪表盘': 'JAntvGauge', '渐变仪表': 'JAntvGauge',
    '数字卡片': 'JNumber',
    '统计进度图': 'JTotalProgress', '总进度图': 'JTotalProgress', '总进度': 'JTotalProgress',
    '热力图': 'JHeatMap', '中国热力地图': 'JHeatMap',
}
# 长词在前，避免「柱状地图」先命中「柱」、「圆形雷达」先命中「雷达」
COMP_HINTS = (
    (('横向条', '条形'), 'JHorizontalBar'),
    (('排行',), 'JRankingList'),
    (('字符云', '词云'), 'JWordCloud'),
    (('透视',), 'JPivotTable'),
    (('双轴',), 'DoubleLineBar'),
    (('多折', '对比折'), 'JMultipleLine'),
    (('数字卡', '指标卡', '数字卡片'), 'JNumber'),
    (('区域地',), 'JAreaMap'),
    (('气泡地', '散点地'), 'JBubbleMap'),
    (('热力',), 'JHeatMap'),
    (('立体柱', '柱状地', '柱形地'), 'JBarMap'),
    (('圆形雷', '圈雷'), 'JCircleRadar'),
    (('散点',), 'JScatter'),
    (('气泡图', '气泡'), 'JBubble'),
    (('雷达',), 'JRadar'),
    (('金字塔',), 'JPyramidFunnel'),
    (('漏斗',), 'JFunnel'),
    (('渐变仪',), 'JAntvGauge'),
    (('多色仪', '色阶'), 'JColorGauge'),
    (('统计进度', '总进度'), 'JTotalProgress'),
    (('仪表',), 'JGauge'),
    (('对比柱', '多系列柱', '分组柱', '多柱'), 'JMultipleBar'),
    (('正负',), 'JNegativeBar'),
    (('堆叠',), 'JStackBar'),
    (('南丁格尔',), 'JRose'),
    (('环形', '环图'), 'JRing'),
    (('玫瑰',), 'JRose'),
    (('饼',), 'JPie'),
    (('折线',), 'JLine'),
    (('面积图',), 'JLine'),
    (('柱状', '柱形', '基础柱'), 'JBar'),
)


def norm_comp_type(raw):
    """口语图类型 → QQY comp。未知返回原串（调用方 COMP_UNKNOWN）。"""
    s = str(raw or '').strip()
    if not s:
        return ''
    if s in QQY_CHARTS:
        return s
    hit = COMP_ALIAS.get(s)
    if hit:
        return hit
    if not s.endswith('图'):
        hit = COMP_ALIAS.get(s + '图')
        if hit:
            return hit
    for keys, val in COMP_HINTS:
        for k in keys:
            if k in s:
                return val
    return s

GROUP_TYPES = {
    'JStackBar', 'JMultipleBar', 'JNegativeBar',
    'JMultipleLine', 'DoubleLineBar', 'JTotalProgress',
    'JBubble', 'JPivotTable',
    'JRadar', 'JCircleRadar',  # 指南 isGroup=T；空 nameFields 不渲染（dim 仍必填）
}
EMPTY_DIM_TYPES = {'JNumber', 'JGauge', 'JColorGauge', 'JAntvGauge'}
HORIZONTAL_TYPES = {'JHorizontalBar', 'JRankingList', 'JTotalProgress'}
MAP_TYPES = {'JBarMap', 'JAreaMap', 'JBubbleMap', 'JHeatMap'}
PIVOT_OR_MAP = {'JPivotTable'} | MAP_TYPES

CATEGORY_MAP = {
    'JBar': 'Bar', 'JStackBar': 'Bar', 'JMultipleBar': 'Bar', 'JNegativeBar': 'Bar',
    'JHorizontalBar': 'HorizontalBar', 'JRankingList': 'HorizontalBar',
    'JTotalProgress': 'HorizontalBar',
    'JLine': 'Line', 'JArea': 'Line', 'JMultipleLine': 'Line', 'DoubleLineBar': 'Line',
    'JWordCloud': 'WordCloud',
    'JPie': 'Pie', 'JRing': 'Pie', 'JRose': 'Pie',
    'JFunnel': 'Funnel', 'JPyramidFunnel': 'Funnel',
    'JRadar': 'Radar', 'JCircleRadar': 'Radar',
    'JColorGauge': 'Gauge', 'JGauge': 'Gauge', 'JAntvGauge': 'Gauge',
    'JNumber': 'Number',
    'JScatter': 'Scatter', 'JBubble': 'Scatter',
    'JPivotTable': 'Table',
    'JAreaMap': 'Map', 'JBubbleMap': 'Map', 'JHeatMap': 'Map', 'JBarMap': 'Map',
}

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
    'headerFreeze': True, 'unilineShow': True, 'izPage': False,
    'columnFreeze': True, 'lineFreeze': True, 'showProgressText': True,
    'progress': {'show': True, 'name': '进度'},
    'target': {'show': True, 'name': '目标'},
}
DEFAULT_ANALYSIS = {
    'isRawData': True, 'showMode': 1, 'showData': 1, 'showFields': [],
    'isCompare': False, 'compareType': '', 'compareValue': None,
    'trendType': '1', 'izTimeOut': False, 'timeOut': 0,
}

CREATE_TIME_SYS = {
    'fieldName': 'create_time', 'fieldTxt': '创建时间', 'options': {},
    'fieldType': 'date', 'widgetType': 'date', 'customDateType': '3', 'fieldShow': True,
}
SYSTEM_FILTER_FIELDS = [
    {'fieldName': 'create_by', 'fieldTxt': '创建人', 'options': {},
     'fieldType': 'select-user', 'widgetType': 'select-user', 'customDateType': '3', 'fieldShow': True},
    {'fieldName': 'update_by', 'fieldTxt': '修改人', 'options': {},
     'fieldType': 'select-user', 'widgetType': 'select-user', 'customDateType': '3', 'fieldShow': True},
    {'fieldName': 'update_time', 'fieldTxt': '修改时间', 'options': {},
     'fieldType': 'date', 'widgetType': 'date', 'customDateType': '3', 'fieldShow': True},
    copy.deepcopy(CREATE_TIME_SYS),
    {'fieldName': 'bpm_status', 'fieldTxt': '流程状态',
     'options': {'dictCode': 'bpm_status', 'remote': 'dict'},
     'fieldType': 'select', 'widgetType': 'select', 'customDateType': '3', 'fieldShow': True},
]

RECORD_COUNT = {
    'fieldName': 'record_count', 'fieldTxt': '记录数量',
    'fieldType': 'count', 'widgetType': 'text',
    'fieldShow': True, 'groupField': '', 'options': [], 'customDateType': '',
}

_SERIES_TYPE_ARRAY = [
    {'series': '1', 'type': 'bar'},
    {'series': '2', 'type': 'bar'},
    {'series': '', 'type': 'bar'},
]


def parse_design_fields(raw_fields):
    """设计器表单 fields[] -> 统一字段对象列表。跳过 file-upload 等。"""
    all_fields = []
    for f in raw_fields or []:
        ftype = f.get('type', '')
        if ftype in SKIP_WIDGET_TYPES:
            continue
        opts = f.get('options') or {}
        if opts.get('type') in ('dates', 'daterange', 'datetimerange'):
            continue
        if not f.get('fieldShow', True):
            continue
        if ftype in NUM_WIDGET_TYPES:
            field_type = 'number'
        elif ftype in DATE_WIDGET_TYPES:
            field_type = 'date'
        else:
            field_type = 'string'
        all_fields.append({
            'fieldName': f.get('model', ''),
            'fieldTxt': f.get('name', ''),
            'fieldType': field_type,
            'widgetType': ftype,
            'fieldShow': True,
            'options': opts if isinstance(opts, dict) else {},
            'customDateType': '',
        })
    return all_fields


def parse_aggregation_fields(raw_fields):
    """聚合表 getFields 结果（数组，计算字段 {title,type,value}）。"""
    all_fields = []
    for f in raw_fields or []:
        ftype = (f.get('type') or f.get('widgetType') or 'string').lower()
        if ftype in SKIP_WIDGET_TYPES:
            continue
        field_type = 'number' if ftype in NUM_WIDGET_TYPES or ftype == 'number' else 'string'
        all_fields.append({
            'fieldName': f.get('value') or f.get('fieldName') or f.get('model') or '',
            'fieldTxt': f.get('title') or f.get('fieldTxt') or f.get('name') or '',
            'fieldType': field_type,
            'widgetType': ftype,
            'fieldShow': True,
            'options': f.get('options') or {},
            'customDateType': '',
        })
    return all_fields


def as_value_field(field):
    obj = copy.deepcopy(field)
    obj['groupField'] = obj.get('groupField', '')
    obj.setdefault('fieldShow', True)
    obj.setdefault('options', [])
    obj.setdefault('customDateType', '')
    return obj


def make_calc_field(formula, field_txt, calc_id=None):
    """计算值对象，同一份写入 calcFields 与 valueFields（widgetType=calcVal）。"""
    import uuid
    return {
        'fieldName': formula,
        'fieldTxt': field_txt,
        'calcId': calc_id or str(uuid.uuid4()),
        'fieldType': 'number',
        'widgetType': 'calcVal',
    }


def is_date_dim_field(field):
    """只有日期控件 / 系统创建·修改时间才能写 customDateType。checkbox/select 等禁止按日归组。"""
    if not field:
        return False
    wt = (field.get('widgetType') or '').lower()
    ft = (field.get('fieldType') or '').lower()
    name = field.get('fieldName') or ''
    return (
        wt in DATE_WIDGET_TYPES
        or (ft == 'date' and wt not in ('checkbox', 'select', 'radio', 'input', 'textarea'))
        or name in ('create_time', 'update_time')
    )


def as_dim_field(field, date_group='', *, expand_link_record=True):
    """维度字段。

    关联记录（link-record）作柱/折/饼等维度时（2026-09-04 对照手工盘）：
    - fieldName 必须改为目标表标题字段 options.titleField（展示名）
    - localField = 本表关联字段 model
    - sourceCode = options.sourceCode（顶层也要）
    - options 保留完整关联控件 dict
    缺 titleField/sourceCode 时不改写（避免静默坏配置）。
    JPivotTable 行/列同样必须展开（2026-09-04 用户手工修透视对照：不展开则不渲染）。
    """
    obj = copy.deepcopy(field)
    obj.setdefault('fieldShow', True)
    opts = obj.get('options')
    if opts is None:
        obj['options'] = []
    elif not isinstance(opts, (dict, list)):
        obj['options'] = []

    wt = (obj.get('widgetType') or '').lower()
    if expand_link_record and wt == 'link-record':
        opts = obj.get('options') if isinstance(obj.get('options'), dict) else {}
        title_field = (opts.get('titleField') or '').strip()
        source_code = (opts.get('sourceCode') or '').strip()
        local = (obj.get('fieldName') or '').strip()
        if title_field and source_code and local:
            obj['localField'] = local
            obj['fieldName'] = title_field
            obj['sourceCode'] = source_code
            obj['options'] = copy.deepcopy(opts)
            obj['widgetType'] = 'link-record'
            if not obj.get('fieldType'):
                obj['fieldType'] = 'string'

    if date_group and is_date_dim_field(obj):
        # 关联记录维度禁止套日期归组
        if (obj.get('widgetType') or '').lower() == 'link-record' or obj.get('localField'):
            obj['customDateType'] = ''
        else:
            obj['customDateType'] = str(date_group)
            if not obj.get('fieldType') or obj['fieldType'] == 'string':
                obj['fieldType'] = 'date'
            if not obj.get('widgetType') or obj['widgetType'] in ('input', 'text'):
                obj['widgetType'] = 'date'
    else:
        obj['customDateType'] = ''
    return obj


# 用户口径 ↔ 表单显示名。specs 写「销售额/产品名称」时也能命中「售价/名称」。
ALIAS_AMOUNT = frozenset({
    '销售额', '销售金额', '金额', '售价', '单价', '价格', '收入', '营收',
    '总价', '费用', 'amount', 'price', 'money', 'sales',
})
ALIAS_QTY = frozenset({
    '销量', '销售量', '数量', '库存', '件数', '台数', 'qty', 'quantity',
})
ALIAS_NAME = frozenset({
    '名称', '产品名称', '商品名称', '品名', '标题', '姓名',
    '客户', '客户名称', '订单号', '编号', 'name', 'title',
})
_ALIAS_GROUPS = (ALIAS_AMOUNT, ALIAS_QTY, ALIAS_NAME)


def resolve_field(token, all_fields, allow_record_count=True, allow_create_time=True):
    """token 可以是 fieldName / fieldTxt / 用户口径别名 / record_count / create_time。"""
    if token is None or token == '' or token == []:
        return None
    if isinstance(token, (list, tuple)):
        return None if not token else resolve_field(token[0], all_fields,
                                                    allow_record_count, allow_create_time)
    key = str(token).strip()
    aliases_count = {'record_count', '记录数', '记录数量', 'count'}
    aliases_time = {'create_time', '创建时间'}
    if allow_record_count and key.lower() in {a.lower() for a in aliases_count}:
        return copy.deepcopy(RECORD_COUNT)
    if allow_create_time and key in aliases_time:
        return copy.deepcopy(CREATE_TIME_SYS)
    for f in all_fields:
        if f.get('fieldName') == key or f.get('fieldTxt') == key:
            return copy.deepcopy(f)
    contains = []
    for f in all_fields:
        txt = str(f.get('fieldTxt') or '')
        if txt and (key in txt or txt in key):
            contains.append(f)
    if contains:
        contains.sort(key=lambda f: len(str(f.get('fieldTxt') or '')))
        return copy.deepcopy(contains[0])
    group = next((g for g in _ALIAS_GROUPS if key in g), None)
    if group:
        hits = [f for f in all_fields if str(f.get('fieldTxt') or '') in group]
        if not hits:
            hits = [f for f in all_fields
                    if any(a in str(f.get('fieldTxt') or '')
                           or str(f.get('fieldTxt') or '') in a
                           for a in group)]
        if hits:
            if group is ALIAS_AMOUNT:
                money = [f for f in hits if f.get('widgetType') == 'money']
                if money:
                    return copy.deepcopy(money[0])
            return copy.deepcopy(hits[0])
    return None


def resolve_field_with_fallback(token, all_fields, role='val',
                                allow_record_count=True, allow_create_time=True):
    """精确/包含/别名失败则按角色回退。返回 (field, note_or_None)。role=dim/val/grp。"""
    hit = resolve_field(token, all_fields, allow_record_count, allow_create_time)
    if hit is not None:
        return hit, None
    rec_dim, rec_val, rec_grp, _date_fields = recommend_fields(all_fields)
    key = '' if token is None or token == [] else str(token).strip()
    if role == 'dim':
        fb = rec_dim or (copy.deepcopy(CREATE_TIME_SYS) if allow_create_time else None)
        if fb is None:
            return None, 'dim=%s 无法回退' % key
        return copy.deepcopy(fb), 'dim=%s 回退到 %s(%s)' % (
            key, fb.get('fieldName'), fb.get('fieldTxt'))
    if role == 'grp':
        fb = rec_grp or rec_dim
        if fb is None:
            return None, 'grp=%s 无法回退' % key
        return copy.deepcopy(fb), 'grp=%s 回退到 %s(%s)' % (
            key, fb.get('fieldName'), fb.get('fieldTxt'))
    money = [f for f in all_fields if f.get('widgetType') == 'money']
    nums = [f for f in all_fields if f.get('fieldType') == 'number']
    qty = [f for f in nums if f.get('widgetType') != 'money']
    if key in ALIAS_AMOUNT or any(a in key for a in ('额', '价', '金')):
        fb = money[0] if money else (nums[0] if nums else copy.deepcopy(RECORD_COUNT))
    elif key in ALIAS_QTY or any(a in key for a in ('量',)):
        fb = qty[0] if qty else (nums[0] if nums else copy.deepcopy(RECORD_COUNT))
    else:
        fb = rec_val
    return copy.deepcopy(fb), 'val=%s 回退到 %s(%s)' % (
        key, fb.get('fieldName'), fb.get('fieldTxt'))


def recommend_fields(all_fields):
    """推荐 dim/val/grp，给 fields 命令展示。"""
    str_fields = [f for f in all_fields if f['fieldType'] == 'string']
    num_fields = [f for f in all_fields if f['fieldType'] == 'number']
    date_fields = [f for f in all_fields if f['fieldType'] == 'date']
    dim = str_fields[0] if str_fields else (date_fields[0] if date_fields else None)
    val = num_fields[0] if num_fields else copy.deepcopy(RECORD_COUNT)
    select_fields = [f for f in str_fields if f.get('widgetType') in ('select', 'radio', 'checkbox')]
    non_textarea = [f for f in str_fields if f.get('widgetType') not in ('textarea', 'editor')]
    grp = (select_fields[0] if select_fields else
           (non_textarea[-1] if len(non_textarea) > 1 else
            (str_fields[-1] if str_fields else dim)))
    return dim, val, grp, date_fields


def _card(name=''):
    return {'title': '', 'size': 'default', 'headColor': '#FFFFFF',
            'textStyle': {'color': '#464646', 'fontSize': 16, 'fontWeight': 'bold'}}


# 运行时靠 series[0].itemStyle.color 上色（无 customColor 时）。缺省必须写 #64b5f6，
# 否则 ECharts 走默认第一色 #5470c6，和手工拖入的 qqyMenuData 不一致。
SOLID_ITEMSTYLE_TYPES = {
    'JBar', 'JHorizontalBar', 'JRankingList', 'JLine', 'JArea', 'JScatter', 'JGauge',
}
DEFAULT_SERIES_COLOR = '#64b5f6'

# 多系列/扇区：运行时 getCustomColor(customColor)；空则用 colorPanel.classic（与手工一致）
CUSTOM_COLOR_TYPES = {
    'JPie', 'JRing', 'JRose', 'JFunnel', 'JPyramidFunnel',
    'JMultipleLine', 'JMultipleBar', 'JStackBar', 'JNegativeBar',
    'DoubleLineBar', 'JBubble', 'JRadar', 'JCircleRadar', 'JWordCloud',
}

# 标题渲染键走「卡片头」option.card.title 的组件（没有 ECharts 标题区）；
# 其余组件标题走 option.title.text。判据与后果见 _sanitize_menu_option 内注释。
CARD_TITLE_TYPES = {'JNumber', 'JPivotTable'}

_DEFAULT_CONFIGS = None


def _default_configs():
    """qqyMenuData 抽出来的默认 option（scripts/default_configs.json）。"""
    global _DEFAULT_CONFIGS
    if _DEFAULT_CONFIGS is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'scripts', 'default_configs.json')
        with open(path, encoding='utf-8') as f:
            _DEFAULT_CONFIGS = json.load(f)
    return _DEFAULT_CONFIGS


def _sanitize_menu_option(opt, chart_type, name=''):
    """把菜单默认 option 改成 QQY dataType=4 可落盘形态。"""
    if not isinstance(opt, dict):
        opt = {}
    # JBarMap 菜单 JSON 误写成 'series '（尾空格），克隆时纠正
    if 'series ' in opt:
        if 'series' not in opt:
            opt['series'] = opt['series ']
        opt.pop('series ', None)
    # 气泡/热力预置 series 会占 series[0] 导致不渲染
    if chart_type in ('JBubbleMap', 'JHeatMap'):
        opt.pop('series', None)
    # 区域/柱状地图：菜单默认可能缺 series 或空数组，需预置 type=map
    if chart_type in ('JAreaMap', 'JBarMap'):
        series = opt.get('series')
        if not isinstance(series, list) or not series:
            opt['series'] = [{'type': 'map', 'map': 'china', 'geoIndex': 0, 'data': []}]
    card = opt.get('card')
    if not isinstance(card, dict):
        card = _card()
        opt['card'] = card
    # 标题渲染键按组件类型分三种（2026-09-16 二次返工实测）：
    #   · JNumber / JPivotTable —— 没有 ECharts 标题区，标题只走卡片头 option.card.title；
    #     透视表 opt.title.text 还会被占位成「表格」，只写 title.text ＝ 表头一片空白
    #   · 其余饼/柱/折等 —— 标题走 ECharts opt.title.text，card.title 写非空会「双标题」
    card['title'] = (name or '') if chart_type in CARD_TITLE_TYPES else ''
    if chart_type == 'JPivotTable':
        opt['title'] = {'show': True, 'text': '表格'}
    else:
        title = opt.get('title')
        if not isinstance(title, dict):
            title = {'show': True, 'textStyle': {'fontWeight': 'normal'}}
            opt['title'] = title
        title['show'] = True
        title['text'] = name or title.get('text') or ''
        ts = title.get('textStyle')
        if not isinstance(ts, dict):
            ts = {}
            title['textStyle'] = ts
        ts.setdefault('fontWeight', 'normal')
    if chart_type == 'JColorGauge':
        series = opt.get('series')
        if not isinstance(series, list) or not series or not isinstance(series[0], dict):
            series = [{}]
            opt['series'] = series
        s0 = series[0]
        s0['type'] = 'gauge'
        s0.setdefault('min', 0)
        s0.setdefault('max', 100)
        s0.setdefault('data', [])
        s0.setdefault('detail', {'formatter': '{value}%', 'fontSize': 25})
        axis = s0.setdefault('axisLine', {})
        if not isinstance(axis, dict):
            axis = {}
            s0['axisLine'] = axis
        ls = axis.setdefault('lineStyle', {})
        if not isinstance(ls, dict):
            ls = {}
            axis['lineStyle'] = ls
        ls.setdefault('width', 10)
        ls.setdefault('color', [[0.33, '#52C41A'], [0.66, '#FAAD14'], [1, '#FF4D4F']])
    if chart_type in SOLID_ITEMSTYLE_TYPES:
        series = opt.get('series')
        if isinstance(series, list) and series and isinstance(series[0], dict):
            ist = series[0].get('itemStyle')
            if not isinstance(ist, dict):
                ist = {}
                series[0]['itemStyle'] = ist
            if not ist.get('color'):
                ist['color'] = DEFAULT_SERIES_COLOR
            if chart_type in ('JBar', 'JHorizontalBar', 'JRankingList'):
                ist.setdefault('borderRadius', 0)
                series[0].setdefault(
                    'barWidth', 40 if chart_type == 'JBar' else 20)
                ist.setdefault('showLinearGradient', False)
    return opt


def get_chart_option(chart_type, name=''):
    """优先克隆 qqyMenuData/default_configs 的完整 option（含柱色/网格/tooltip），
    再按组件补必填键。禁止再手搓只有 {type:bar} 的空骨架。"""
    raw = _default_configs().get(chart_type)
    if isinstance(raw, dict) and isinstance(raw.get('option'), dict):
        opt = copy.deepcopy(raw['option'])
        return _sanitize_menu_option(opt, chart_type, name)
    title = {'show': True, 'text': name}
    card = _card()
    if chart_type in MAP_TYPES:
        # JBubbleMap/JHeatMap：前端按 area.markerType 动态拼 effectScatter/heatmap + map；
        # 预置仅 type=map 的 series 会占 series[0]，气泡/热力不渲染（对照手工 JBubbleMap：无 series 键）。
        # JAreaMap/JBarMap：可预置 map series（visualMap.seriesIndex=[0]）。
        roam = chart_type in ('JHeatMap', 'JBarMap', 'JBubbleMap')
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
                    'normal': {'shadowOffsetX': 0, 'shadowOffsetY': 0, 'areaColor': '',
                               'shadowBlur': 0, 'borderWidth': 1, 'shadowColor': '#80d9f8'},
                    'emphasis': {'areaColor': '#fff59c', 'borderWidth': 0}},
            }
            if chart_type == 'JAreaMap':
                geo['itemStyle']['normal']['borderColor'] = '#a9a9a9'
        area = {
            'markerColor': '#df2425' if chart_type == 'JHeatMap' else '#DDE330',
            'shadowBlur': 10, 'markerCount': 5, 'markerOpacity': 1,
            'name': ['中国'], 'scatterLabelShow': False,
            'shadowColor': '#DDE330', 'value': ['china'], 'markerType': 'effectScatter',
        }
        if chart_type == 'JBarMap':
            vm = {'max': 200, 'show': False, 'seriesIndex': [0]}
        elif chart_type == 'JHeatMap':
            vm = {'min': 0, 'top': 'bottom', 'max': 200, 'left': '5%',
                  'calculable': True, 'show': True, 'type': 'continuous', 'seriesIndex': [1]}
        elif chart_type == 'JBubbleMap':
            vm = {'min': 0, 'top': 'bottom', 'max': 200, 'left': '5%',
                  'calculable': True, 'show': False, 'type': 'continuous', 'seriesIndex': [1]}
        else:
            vm = {'min': 0, 'top': 'bottom', 'max': 200, 'left': '5%',
                  'calculable': True, 'show': False, 'type': 'continuous', 'seriesIndex': [0]}
        opt = {
            'drillDown': False, 'area': area, 'geo': geo,
            'grid': {'bottom': 115, 'show': False}, 'legend': {'data': []},
            'title': {'left': 10, 'show': True, 'text': name, 'textStyle': {'fontWeight': 'normal'}},
            'graphic': [], 'card': card, 'visualMap': vm,
        }
        if chart_type in ('JAreaMap', 'JBarMap'):
            opt['series'] = [{'type': 'map', 'map': 'china', 'geoIndex': 0, 'data': []}]
        # JBubbleMap / JHeatMap：不写 series，交给前端按 area.markerType 组装
        return opt
    if chart_type in ('JWordCloud', 'JTotalProgress', 'JNumber',
                      'JRadar', 'JCircleRadar', 'JAntvGauge'):
        return {'title': title, 'card': card}
    if chart_type == 'JPivotTable':
        return {'title': {'show': True, 'text': '表格'}, 'card': card}
    # JColorGauge 必须带 axisLine 分段色 series；仅 title+card 或不写 type:gauge 会白屏不渲染
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
            'title': title, 'card': card,
        }
    if chart_type == 'JGauge':
        return {
            'series': [{'min': 0, 'data': [], 'max': 100,
                        'axisTick': {'lineStyle': {'color': '#eee'}, 'show': True},
                        'detail': {'formatter': '{value}'}, 'type': 'gauge'}],
            'title': title, 'card': card,
        }
    if chart_type == 'JPie':
        return {'series': [{'data': [], 'type': 'pie'}], 'title': title, 'card': card}
    if chart_type == 'JRing':
        return {'series': [{'data': [], 'avoidLabelOverlap': False,
                            'label': {'show': False}, 'labelLine': {'show': False},
                            'type': 'pie', 'radius': ['40%', '70%']}],
                'title': title, 'card': card}
    if chart_type == 'JRose':
        return {'series': [{'data': [], 'roseType': 'area', 'type': 'pie'}],
                'title': title, 'card': card}
    if chart_type in ('JFunnel', 'JPyramidFunnel'):
        sort = 'descending' if chart_type == 'JFunnel' else 'ascending'
        return {'series': [{'data': [], 'left': '10%', 'gap': 2,
                            'name': 'Funnel', 'sort': sort, 'type': 'funnel'}],
                'title': title, 'card': card}
    if chart_type in HORIZONTAL_TYPES and chart_type != 'JTotalProgress':
        return {
            'yAxis': {'data': [], 'type': 'category'},
            'xAxis': {'type': 'value'},
            'series': [{'type': 'bar', 'barWidth': 20,
                        'itemStyle': {'color': DEFAULT_SERIES_COLOR, 'borderRadius': 0}}],
            'grid': {'containLabel': True, 'top': 70, 'bottom': 60, 'left': 50, 'right': 30},
            'tooltip': {'trigger': 'axis'}, 'legend': {'show': True},
            'title': title, 'card': card,
        }
    if chart_type == 'DoubleLineBar':
        return {
            'yAxis': [{'type': 'value'}, {'type': 'value'}],
            'xAxis': {'type': 'category'},
            'series': [{'type': 'bar'}, {'type': 'line'}],
            'grid': {'containLabel': True, 'top': 70, 'bottom': 60, 'left': 50, 'right': 30},
            'tooltip': {'trigger': 'axis'}, 'legend': {'show': True},
            'title': title, 'card': card,
        }
    if chart_type in ('JScatter', 'JBubble'):
        return {
            'yAxis': {'type': 'value'}, 'xAxis': {'type': 'value'},
            'series': [{'type': 'scatter',
                        'itemStyle': {'color': DEFAULT_SERIES_COLOR}, 'symbolSize': 10}],
            'grid': {'containLabel': True, 'top': 70, 'bottom': 60, 'left': 50, 'right': 30},
            'tooltip': {'trigger': 'axis'}, 'legend': {'show': True},
            'title': title, 'card': card,
        }
    if chart_type == 'JBar':
        return {
            'yAxis': {'type': 'value'},
            'xAxis': {'data': [], 'type': 'category'},
            'series': [{'type': 'bar', 'barWidth': 40,
                        'itemStyle': {'color': DEFAULT_SERIES_COLOR, 'borderRadius': 0,
                                      'showLinearGradient': False},
                        'label': {'position': 'top'}}],
            'grid': {'containLabel': True, 'top': 90, 'bottom': 115, 'show': False},
            'tooltip': {'trigger': 'axis'}, 'legend': {'show': True},
            'title': title, 'card': card,
        }
    if chart_type in ('JStackBar', 'JMultipleBar', 'JNegativeBar'):
        return {
            'yAxis': {'type': 'value'},
            'xAxis': {'type': 'category'},
            'series': [{'type': 'bar'}],
            'grid': {'containLabel': True, 'top': 70, 'bottom': 60, 'left': 50, 'right': 30},
            'tooltip': {'trigger': 'axis'}, 'legend': {'show': True},
            'title': title, 'card': card,
        }
    if chart_type in ('JLine', 'JArea'):
        series = [{'type': 'line', 'itemStyle': {'color': DEFAULT_SERIES_COLOR},
                   'label': {'position': 'top'}}]
        if chart_type == 'JArea':
            series = [{'type': 'line', 'areaStyle': {},
                       'itemStyle': {'color': DEFAULT_SERIES_COLOR},
                       'label': {'position': 'top'}}]
        return {
            'yAxis': {'type': 'value'},
            'xAxis': {'data': [], 'type': 'category'},
            'series': series,
            'grid': {'containLabel': True, 'top': 90, 'bottom': 115, 'show': False},
            'tooltip': {'trigger': 'axis'}, 'legend': {'show': True},
            'title': title, 'card': card,
        }
    if chart_type == 'JMultipleLine':
        return {
            'yAxis': {'type': 'value'},
            'xAxis': {'type': 'category'},
            'series': [{'type': 'line'}],
            'grid': {'containLabel': True, 'top': 70, 'bottom': 60, 'left': 50, 'right': 30},
            'tooltip': {'trigger': 'axis'}, 'legend': {'show': True},
            'title': title, 'card': card,
        }
    return {'title': title, 'card': card}


def get_common_option(chart_type):
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
    return {
        'barSize': 10, 'gradientColor': False,
        'breadcrumb': {'drillDown': False, 'textColor': '#000000'},
        'areaColor': {'color1': '#f7f7f7', 'color2': '#fcc02e'},
        'barColor': '#fff176', 'barColor2': '#fcc02e',
        'inRange': {'color': ['#04387b', '#467bc0']},
    }


def make_pivot_table(value_fields):
    keys = [f['fieldName'] for f in value_fields] or ['record_count']
    return {
        'columnSummary': {
            'controlList': [{'showName': '', 'show': True, 'totalType': 'sum',
                             'position': '2', 'key': k} for k in keys],
            'name': '列汇总', 'location': 'right',
        },
        'lineSummary': {
            'controlList': [{'showName': '', 'show': True, 'totalType': 'sum',
                             'key': k} for k in keys],
            'name': '行汇总', 'location': 'bottom',
        },
        'unitList': [{'showName': '', 'unit': '', 'key': k} for k in keys],
        'showLineCount': 0, 'showColumnCount': 0,
        'showColumnTotal': True, 'showLineTotal': True,
    }


def mk_cfg(app_id, form_code, form_name, form_type, chart_type, title,
           name_fields, value_fields, type_fields=None, w=12, h=28,
           query_range='all', query_field='create_time', custom_time=None):
    """构建 QQY dataType=4 完整 config。"""
    if chart_type not in QQY_CHARTS:
        raise ValueError('QQY 不支持组件: %s' % chart_type)
    is_group = chart_type in GROUP_TYPES
    category = CATEGORY_MAP.get(chart_type, 'Bar')
    _is_pivot_or_map = chart_type in PIVOT_OR_MAP
    cfg = {
        'dataType': 4,
        'formType': 'design',
        'formId': form_code,
        'formName': form_name,
        'tableName': form_code,
        'type': form_type,
        'appId': app_id,
        'appType': 'current',
        'nameFields': list(name_fields),
        'valueFields': [as_value_field(v) for v in value_fields],
        'typeFields': list(type_fields or []),
        'assistYFields': [as_value_field(v) for v in value_fields] if _is_pivot_or_map else [],
        'assistTypeFields': [copy.deepcopy(CREATE_TIME_SYS)] if _is_pivot_or_map else [],
        'calcFields': [],
        'dataNum': '',
        'dataFilterNum': '',
        'sorts': {'name': '', 'type': ''},
        'filter': {
            'queryField': query_field or 'create_time',
            'queryRange': query_range or 'all',
            'conditionFields': [],
            'customTime': list(custom_time or []),
            'conditionMode': 'and',
        },
        'chart': {'category': category, 'subclass': chart_type, 'isGroup': is_group},
        'compStyleConfig': copy.deepcopy(DEFAULT_COMP_STYLE_CONFIG),
        'analysis': copy.deepcopy(DEFAULT_ANALYSIS),
        'option': get_chart_option(chart_type, title),
        'actionConfig': {'operateType': 'modal', 'modalName': '', 'url': ''},
        'turnConfig': {'url': ''},
        'jsConfig': '',
        'drillData': [],
        'authFieldShowResult': [],
        'timeOut': 0,
        'chartData': '[]',
        'background': '#FFFFFF',
        'borderColor': '#E8E8E8',
        'size': {'width': w * 75, 'height': h * 11},
        'seriesType': copy.deepcopy(_SERIES_TYPE_ARRAY) if _is_pivot_or_map else [],
    }
    if chart_type in MAP_TYPES:
        cfg['commonOption'] = get_common_option(chart_type)
    if chart_type == 'JPivotTable':
        cfg['pivotTable'] = make_pivot_table(value_fields)
    return cfg


def menu_size(chart_type, default_w=12, default_h=30):
    raw = _default_configs().get(chart_type) or {}
    try:
        w = int(raw.get('w') or default_w)
    except (TypeError, ValueError):
        w = default_w
    try:
        h = int(raw.get('h') or default_h)
    except (TypeError, ValueError):
        h = default_h
    return w, h


def make_component(comp_type, title, x, y, w, h, cfg, order_num=0, key=None):
    return {
        'component': comp_type,
        'componentName': title,
        'visible': True,
        'i': key,
        'x': x, 'y': y, 'w': w, 'h': h,
        'pcX': x, 'pcY': y, 'pcW': w,
        'orderNum': order_num,
        'config': cfg,
    }
