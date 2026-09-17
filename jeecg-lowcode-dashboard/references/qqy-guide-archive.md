# 敲敲云（QQY）仪表盘详细参考 — 全文归档

> 旧全量指南（默认勿读）：仅未点名交互细节（轮播/iframe/时钟四步、按钮 operationType）时打开；组件清单已迁出（见下节）。已点名 → 现行 `../SKILL.md` §4 / `create.md` / `mutate.md`。  
> 权威：`../SKILL.md` §4 + `../create.md` / `../mutate.md`。未点名且卡住时，才按索引打开本节。  
> 「强制四步/六步」仅未点名；与 skill 冲突时以 SKILL 为准。  
> 查应用/表单/加图/按钮：用 `qqy_ops.py`，禁止为单次需求手写脚本。

### 组件清单（已迁出）

> 统计图 30 可用码 / UI 7 清单 / 禁用清单 / 口语↔码 → **`component-words.md`**（唯一词表，与 `qqy_chart.py` 同源）。原清单表 2026-09-09 删除防漂移，勿在本归档重建。

**🚨 QQY 非统计图表组件 config 规范（验证来源：data.ts + JCarousel.vue 源码）**

> 以下配置为实际可用结构，**禁止使用 dataType:4 + nameFields 等统计图表写法**（非统计组件不走 getTotalData 接口，用 dataType:4 会导致白屏/TypeError）。

**通用 card 结构（所有组件通用）：**

> **🚨 card.title 必须为 `''`（空字符串），禁止设置为组件名称（如"实时日期"/"嵌入URL"）**。QQY 非统计图表组件的标题由 `option.body` 或 `chartData` 内容展示，卡片头设置了 title 会产生双重标题。

```python
CARD = {
    'title': '',       # 🚨 必须空字符串，所有非统计图表组件均如此，无例外
    'extra': '',
    'rightHref': '',   # 🚨 必须是空字符串，禁止改为对象或含 headColor/textStyle
    'size': 'default',
}
```

**JText（文本）：**
```python
{
    'dataType': 1,
    'url': '',
    'timeOut': 0,
    'linkageConfig': [],
    'turnConfig': {'url': ''},   # 🚨 必填，缺少时读 turnConfig.url 报 TypeError
    'chartData': '文本内容',      # 🚨 纯字符串，禁止用 {'value': '...'} dict 格式
    'background': '#FFFFFF', 'borderColor': '#E8E8E8',
    'size': {'width': w*75, 'height': h*11},
    'option': {
        'horseLamp': False, 'speed': 1000,
        'card': {**CARD},
        'body': {
            'text': '文本内容', 'color': '#464646', 'fontWeight': 'bold',
            'marginLeft': 0, 'marginTop': 20, 'letterSpacing': 0,
            'fontSize': 22, 'textAlign': 'center',
        },
    },
}
```

**JCurrentTime（实时日期）：** 完整 config → `templates-ui.md`（`showWeek:'show'|'hide'`；`card.title=''`）。

**JFilterQuery（查询条件）：**

> **🚨 QQY 查询条件完整配置流程（6步）** 已点名应用+看板+联动图表+条件字段（如「名称包含」）→ **禁止走本节**：Write specs + `qqy_ops.py add-filter --specs-file`（按标题匹配图表、表单自动取自联动图表 config、comp/add+saveCompToPage 一次进程，见 ../create.md「按钮 / 查询面板」）。跨两张工作表的图（如产品表非地图 + 省份表地图）必须**两次** add-filter，禁止手写合并一个 JFilterQuery。**本节仅当用户没点名图表/条件、无法唯一匹配时**先询问：
>
> 1. **关联图表**：调用 `comp_ops.py list` 列出当前仪表盘中**统计类型**图表（排除 noViewChart），询问联动控制哪几个图表
> 2. **添加条件**：询问添加几个查询条件
> 3. **条件显示名**：询问每个条件的显示名称（如"名称"、"日期"）
> 4. **筛选字段**：调用 `GET /desform/api/fields/{tableName}` 查询表单字段（过滤 SKIP_TYPES），展示给用户，询问每个条件关联哪个字段（`fieldList[i]` 对应 `relationChartList[i]`）
> 5. **查询方式**：根据字段 type 展示可用选项，询问用户选择
> 6. **执行**：收集完以上信息后，一次性写入完整 config（conditionFields + filter + relationChartList + chartData + linkageConfig）
>
> **字段类型 → 查询方式对应关系（来自 FilterSetModal.vue）：**
> - `input/textarea` 类型：等于(1) / 包含(2，LIKE，默认) / 开头是(5) / 结尾是(6)
> - `date/time/number/money/int/double/BigDecimal/integer/slider/rate`：等于(1) / 晚于-大于(3) / 早于-小于(4) / 在范围内(2，默认)
> - 其他类型（select/radio等）：等于(1)

**noViewChart 排除列表（不应出现在联动图表候选中）：**
```python
noViewChart = [
    'JFilterQuery','JText','JCustomButton','JCarousel','JDragEditor',
    'JIframe','JCurrentTime','JImg','JCalendar','JMultiViewCalendar',
    'JWaitMatter','JDynamicInfo','JQuickNav','JProjectCard','JRadioButton',
    'JTabs','JGrid','JCustomEchart','online','design'
]
```

**JFilterQuery 完整 config 结构（来自 FilterSetModal.vue resetComp/addFilter + 实操验证）：**
```python
import uuid, json

# 各条件的 fieldList 顺序必须与 relationChartList 顺序一一对应
# ⚠️ 目标图表无需任何修改，联动完全由 JFilterQuery 的 linkageConfig 驱动

# Step 1: 构建单个 conditionField 对象（conditionFields/filter.conditionFields 共用）
def make_condition_field(field_name, field_txt, field_type, widget_type, query_mode='2'):
    # query_mode: '1'=等于 '2'=包含(LIKE) '3'=晚于/大于 '4'=早于/小于 '5'=开头是 '6'=结尾是
    rule_map = {'1': 'EQ', '2': 'LIKE', '3': 'GT', '4': 'LT', '5': 'LLIKE', '6': 'RLIKE'}
    return {
        'fieldName': field_name, 'fieldTxt': field_txt,
        'fieldType': field_type, 'widgetType': widget_type,
        'rule': rule_map.get(query_mode, 'LIKE'),
        'condition': query_mode,
        'val': '', 'fieldValue': '',
        'options': [], 'fieldShow': True, 'customDateType': ''
    }

# Step 2: 构建表单字段 options（过滤不支持类型 + 去除 dataType:null）
SKIP_TYPES = {'file-upload', 'imgupload', 'sub-table-design', 'link-field',
              'auto-number', 'barcode', 'editor', 'capital-money', 'text-compose',
              'formula', 'markdown', 'location', 'summary', 'daterange', 'datetimerange'}
resp = bi_utils._request('GET', f'/desform/api/fields/{form_code}')
raw_fields = (resp.get('result') or {}).get('fields', [])
form_fields = [f for f in raw_fields if f.get('type') not in SKIP_TYPES]
for f in form_fields:                           # 去除 API 返回的 dataType:null（参考JSON无此字段）
    f.get('options', {}).pop('dataType', None)

system_fields = [                               # publicFields（前端 getFormField 自动追加，API需手动补充）
    {'name': '创建人',   'model': 'create_by',   'type': 'select-user', 'options': {}},
    {'name': '修改人',   'model': 'update_by',   'type': 'select-user', 'options': {}},
    {'name': '修改时间', 'model': 'update_time', 'type': 'date',        'options': {}},
    {'name': '创建时间', 'model': 'create_time', 'type': 'date',        'options': {}},
    {'name': '流程状态', 'model': 'bpm_status',  'type': 'select',      'options': {'dictCode': 'bpm_status', 'remote': 'dict'}},
]
all_options = form_fields + system_fields

# Step 3: 构建完整 filter_config
condition_fields = [
    make_condition_field('input_xxx', '订单名称', 'string', 'input', '2'),
    make_condition_field('money_xxx', '金额',     'number', 'money', '1'),
]

chart_data_list = [
    {
        'id': 'query_' + str(uuid.uuid4()),
        'label': '订单名称',    # 条件显示名（用户指定）
        'type': 'input',        # 字段控件类型（影响前端渲染）
        'fieldList': [          # 顺序对应 relationChartList 顺序，同表同字段则写两次
            'input_xxx',        # 图表0（基础柱形图）对应字段 model
            'input_xxx',        # 图表1（基础饼图）对应字段 model
        ],
        'queryMode': '2',       # '1'=等于 '2'=包含(LIKE) '3'=晚于 '4'=早于 '5'=开头是 '6'=结尾是
        'defVal': None, 'beginValue': None, 'endValue': None,
    },
    {
        'id': 'query_' + str(uuid.uuid4()),
        'label': '金额', 'type': 'money',
        'fieldList': ['money_xxx', 'money_xxx'],
        'queryMode': '1',
        'defVal': None, 'beginValue': None, 'endValue': None,
    },
]

filter_config = {
    'dataType': 1,
    'timeOut': 0,
    'isEnableFilterBtn': True,           # ✅ 必须，缺失则无查询按钮
    'isQueryAfterShowData': False,       # ✅ 必须，缺失则查询行为异常
    'conditionFields': condition_fields, # ✅ 必须，缺失则筛选条件不显示
    'filter': {                          # ✅ 必须，缺失则筛选面板报错
        'conditionMode': 'and',
        'conditionFields': condition_fields,  # 与顶层 conditionFields 相同
        'queryField': 'input_xxx',            # 主查询字段名（第一个条件字段）
        'customTime': [],
        'queryRange': 'all',
    },
    'relationChartList': [               # 关联的统计图表列表
        {
            'code': 'ding_dan_biao_gui5',   # tableName（工作表编码，来自图表config.tableName）
            'options': all_options,          # 表单字段 + 系统字段（见上方构建步骤）
            'checked': 1,
            'label': '基础柱形图',           # 图表显示名（componentName）
            'type': 'design',               # 来自图表 config.formType（'design'/'online'）
            'key': '1776425135452',         # 对应图表的 comp.i 值
        },
        {
            'code': 'ding_dan_biao_gui5',
            'options': all_options,         # 同一工作表可复用同一份 options
            'checked': 1,
            'label': '基础饼图',
            'type': 'design',
            'key': '17874487-...',
        },
    ],
    'chartData': json.dumps(chart_data_list, ensure_ascii=False),  # ✅ 必须是 JSON 字符串，不是 list
    'linkageConfig': [                   # ✅ 必须，缺失则查询不触发图表刷新
        {
            'linkageId': '1776425135452',   # 目标图表 comp.i
            'linkageConfig': [{'src': 'input_xxx', 'tgt': 'input_xxx'}],  # src=查询字段model，tgt=图表接收字段
        },
        {
            'linkageId': '17874487-...',
            'linkageConfig': [{'src': 'input_xxx', 'tgt': 'input_xxx'}],
        },
    ],
    'size': {'width': 1800, 'height': 110},  # height=h*11（h=10时为110）
    'background': '#FFFFFF',
    'borderColor': '#E8E8E8',
    'chart': {'subclass': 'JFilterQuery', 'category': 'Common'},
    'option': {
        'title': {'show': True, 'text': '查询条件', 'textStyle': {'color': '#464646', 'fontSize': 14}},
        'card': {'rightHref': '', 'size': 'default', 'extra': '', 'title': ''},
    },
}
```

**关键注意事项：**
- `conditionFields`（顶层）和 `filter.conditionFields` 必须同时存在且内容相同，缺一不可
- `chartData` 为数组（实操 UI 保存即 list）。条目含 `queryMode`（`'1'`等于 `'2'`包含）、`fieldList`、`defVal`
- UI 最小形态可以没有顶层 `conditionFields` / `filter` / `linkageConfig`；要联动图表仍需 `linkageConfig`
- `linkageConfig` 驱动查询联动，**目标图表无需任何修改**（禁止在目标图表上添加 drillData）
- `linkageConfig[].linkageConfig[].src` = JFilterQuery 传出的字段 model；`tgt` = 目标图表接收的字段 model
- `relationChartList[].options` 必须包含表单字段 + publicFields（系统字段），前端筛选面板从此列表渲染可选字段
- `options` 中需过滤不支持类型（见 SKIP_TYPES），且去除 API 返回的 `dataType: null`（与参考JSON保持一致）
- 同一工作表的多个图表，`options` 可复用同一份字段列表
- `chartData[].fieldList[i]` 对应 `relationChartList[i]` 的选中字段 model；同表同字段则写相同值两次
- 获取表单字段：`GET /desform/api/fields/{tableName}`，字段在 `result.fields`
- **业务加查询条件联动禁止手写本节 config**：走 `qqy_ops.py add-filter`（禁止 Write `_tmp_*.py`、禁止手工 `comp/add`+`saveCompToPage`、禁止 `save_page`；`ADDED=` 即成功）。本节 config 模板只用于排障/特殊场景

**获取关联图表候选列表的方法（来自源码 handleChartList）：**
```python
# 来自 FilterSetModal.vue handleChartList
label = (cfg.get('option') or {}).get('title', {}).get('text', '') \
     or (cfg.get('option') or {}).get('card', {}).get('title', '') \
     or comp.get('componentName', '')
key   = comp['i']
code  = cfg.get('tableName', '')
type_ = cfg.get('type', '')   # 'design' or 'aggregation'
```

**JCustomButton（按钮）：**

> **🚨 chartData 存储规则（2026-09-01 前端保存实操）**：
> - `chartData` 为 **数组**（template 整体 dumps）。含 worksheet 对象时也是数组，禁止再 `json.dumps(chartData)` 双重编码
> - `worksheet` 为对象（label/value/key，op2 另含 type/desformId）
> - op1 `defVal` 为控件对象列表：`{name,model,type,value,checked:1,key,options,rules}`

```python
import json

# 简单按钮（无绑定，chartData 用列表）
btn_list_simple = [
    {
        'btnId': str(int(time.time()*1000)),
        'title': '示例按钮',
        'icon': 'ant-design:plus-outlined',
        'color': '#1890FF',
        'operationType': '1',   # '1'=创建记录 '2'=打开视图 '3'=自定义页面 '4'=链接 '6'=业务流程
        'worksheet': '', 'view': '', 'defVal': [], 'customPage': '',
        'href': {'url': '', 'isParam': False, 'params': []},   # 🚨 href 必须是对象
        'openMode': '2',
        'bizFlow': '',
        'click': {'type': '1', 'message': {'title': '你确认执行此操作吗？', 'okText': '确认', 'cancelText': '取消'}},
    }
]

# 绑定表单视图的按钮（operationType='2'；chartData 仍是数组，勿双重 dumps）
btn_list_bound = [
    {
        'btnId': str(int(time.time()*1000)),
        'title': '按钮标题',   # 例：某张工作表的名称
        'icon': 'ant-design:calendar-twotone',
        'color': '#ED4B82',
        'operationType': '2',   # 打开视图
        'worksheet': {          # 🚨 完整对象（含 desformId），禁止简单字符串
            'label': '表单名称', 'value': 'form_code', 'key': 'form_code',
            'type': 'form', 'desformId': 'desform_id_here',
        },
        'view': 'view_id_here', # 视图ID（GET /desform/api/list/view?desformCode=xxx 获取）
        'defVal': [],  # op1 创建记录：[{'field':'字段model','value':'默认值'}, ...]
        'customPage': '',
        'href': {'url': '', 'isParam': False, 'params': []},
        'openMode': '2',
        'bizFlow': '',
        'appInfo': {'type': 'current'},   # 🚨 绑定按钮必须含此字段
        'desformId': 'desform_id_here',   # 与 worksheet.desformId 一致
        'click': {'type': '1', 'message': {'title': '你确认执行此操作吗？', 'okText': '确认', 'cancelText': '取消'}},
    }
]

config = {
    'dataType': 1,
    'url': '',
    'timeOut': 0,
    'chartData': btn_list_simple,          # 简单按钮用列表
    # 'chartData': btn_list_bound,  # 含绑定也是数组，不要 dumps
    # 🚨 rowNum 默认与按钮数量相同（如5个按钮填5），确保一行横向显示；btnDirection 对 btnType=button 无效
    'option': {'title': '', 'btnType': 'button', 'btnStyle': 'solid', 'btnWidth': 'custom', 'btnDirection': 'column', 'rowNum': len(btn_list)},
    'background': '#FFFFFF', 'borderColor': '#E8E8E8',
    'size': {'width': w*75, 'height': h*11},
}
```

**JDragEditor（富文本）：**
```python
{
    'dataType': 1,
    'timeOut': 0,
    'chartData': '<p>富文本内容</p>',   # 🚨 HTML 字符串，禁止用 dict 或 json.dumps
    'background': '#FFFFFF', 'borderColor': '#E8E8E8',
    'size': {'width': w*75, 'height': h*11},
}
```

**JCarousel（轮播图）：**

> 已点名 → `../create.md`「文本 / 轮播 / iframe / 时钟」+ `../templates-ui.md`（勿在本归档排障）。  
> **未点名**才走下方四步。

> **🚨 QQY 模式强制交互流程（禁止直接添加静态图片）**：
>
> **Step 1** — 查询应用工作表列表并展示给用户选择：
> ```python
> bi_utils._request('GET', '/desform/api/list/options', params={'appId': APP_ID})
> # 展示：[1] 表单名 (code: xxx)，等待用户选择
> ```
>
> **Step 2** — 并行查询选定工作表的字段 + 视图：
> ```python
> # 字段（取 imgupload/photo/image 类型，跳过 file-upload）
> bi_utils._request('GET', f'/desform/api/fields/{FORM_CODE}', params={'subTable': True})
> # 视图
> bi_utils._request('GET', '/desform/api/list/view', params={'desformCode': FORM_CODE})
> ```
> 展示图片类字段列表和视图列表（无视图则填 `''`）。
>
> **Step 3** — 询问用户三项：
> - 使用哪个图片字段（`imgupload`/`photo`/`image` 类型，`file-upload` 附件不可用）
> - 使用哪个视图（无视图选 `''`）
> - 显示模式：全部显示（`showMode:'all'`）还是每条记录显示首张（`showMode:'single'`）
>
> **Step 4** — 拿到用户确认后写入绑定 config（见下方方式1）
>
> **唯一例外**：用户明确说"用静态图片"或"示例图片"时才可跳过 Step 1-3，直接用方式2。

```python
# 方式1：绑定表单图片字段（QQY 模式默认方式，必须走 Step 1-3 交互）
carousel_config_bound = {
    'dataType': 1,               # 🚨 dataType=1，禁止用 dataType=4
    'url': '', 'timeOut': 0,
    'linkageConfig': [],
    'dataMapping': [{'filed': '路径', 'mapping': ''}],
    # 🚨 QQY 绑定字段（JCarousel.vue queryDesDatList 函数读取）
    'worksheet': {'label': '表单名', 'value': 'desform_code_xxx', 'key': 'desform_code_xxx'},
    'field': 'imgupload_xxx_xxx',                 # 🚨 imgupload/photo/image 类型字段 model，file-upload 不可用
    'view': 'view_id_or_empty_string',            # 视图ID，无视图时填 ''
    'showMode': 'all',           # 'all'=每条记录所有图片  'single'=每条记录取第一张
    'maxCount': 15,              # 前端默认 15
    'appInfo': {'label': '应用名', 'value': APP_ID},  # 可跨应用，value=他应用 ID
    'chartData': [               # 绑定后仍可保留默认静态图，运行时走 worksheet+field
        {'src': 'https://jeecgos.oss-cn-beijing.aliyuncs.com/files/site/drag/0.png'},
        {'src': 'https://jeecgos.oss-cn-beijing.aliyuncs.com/files/site/drag/1.png'},
        {'src': 'https://jeecgos.oss-cn-beijing.aliyuncs.com/files/site/drag/2.png'},
    ],
    'option': {'autoplay': True, 'dots': True, 'dotPosition': 'bottom', 'easing': 'linear'},
    'background': '#FFFFFF', 'borderColor': '#E8E8E8',
    'size': {'width': w*75, 'height': h*11},
}

# 方式2：静态图片（仅当用户明确要求"静态/示例图片"时使用）
carousel_config_static = {
    'dataType': 1,
    'url': '', 'timeOut': 0,
    'linkageConfig': [],
    'dataMapping': [{'filed': '路径', 'mapping': ''}],
    'chartData': [
        {'src': 'https://img.alicdn.com/imgextra/i1/O1CN01YpZoEn1mS8PaFLZg7_!!6000000004952-2-tps-1920-1080.png'},
    ],
    'option': {'autoplay': True, 'dots': True, 'dotPosition': 'bottom', 'easing': ''},
    'background': '#FFFFFF', 'borderColor': '#E8E8E8',
    'size': {'width': w*75, 'height': h*11},
}
```

**JIframe / JCurrentTime：** 已点名 → `../templates-ui.md` + `../create.md`「文本 / 轮播 / iframe / 时钟」。  
要点：`option.body.url`（禁 `option.url`）；`showWeek` 须 `'show'/'hide'` 字符串；`card.title=''`。

### dataType=4 / 统计图 / 全组件（已迁出）

> **已点名加图 / 改绑 / 全组件 → 禁止读本节。**  
> - 业务路径：../SKILL.md §4 + qqy_ops.py add-charts / 
ebind-chart / …  
> - 透视/双轴/地图/JT 结构：charts-special.md  
> - specs 示例：gold-specs.md  
> - 全组件批量：gen_qqy_all_comps.py（见 charts-special §5）  
> 本归档**不再**收录 dataType=4 完整 config、手写 save_page 建图脚本、30 组件 series 对照表（易与铁律冲突）。


### 按钮（JCustomButton）操作类型配置

QQY 仪表盘中自定义按钮通过 `operationType` 绑定业务操作，5 种类型均来自 `ButtonSetModal.vue`。

**证据**：`packages/dragEngine/modal/chartset/ButtonSetModal.vue` 第 388-410 行定义 `operationTypeOption`；第 590-617 行定义按钮完整结构。

#### 添加按钮：用户已点名则一条命令；没点名才四步询问

> **已点名（强制快路径，禁止走下面四步）：** 用户已给出应用 + 已有仪表盘名 + 按钮名称 + 操作（创建记录到某表 / 打开某表列表视图 / 打开某页 / 打开某链接 / 调用某流程）→ 禁止询问、禁止通读本节、禁止 Write `_tmp_*.py`。立刻 Write `--specs-file` + `qqy_ops.py add-buttons`（见 skill「已有仪表盘加按钮」）。无自定义视图时 `view=''`（全部记录）。`saveCompToPage` 的 `template` 必须是 JSON 字符串。
>
> **未点名：** 才走下面四步。严禁创建空绑定的占位按钮。

---

**第一步：询问按钮数量和名称**

> 用户说"添加按钮"时，必须先问：

```
请问需要添加几个按钮？每个按钮叫什么名字？
（可参考默认推荐：创建记录 / 打开视图 / 跳转页面 / 打开链接 / 调用业务流程）
```

---

**第二步：询问每个按钮触发的操作类型**

> 列出5种操作类型，让用户为每个按钮逐一选择：

| operationType | 操作 | 需要对接 |
|--------------|------|---------|
| `'1'` | 创建记录 | 选择**工作表（表单）** |
| `'2'` | 打开视图 | 选择**工作表（表单）** → 再选**视图** |
| `'3'` | 打开自定义页面 | 选择**应用内仪表盘页面** |
| `'4'` | 打开链接 | 用户输入**网页地址（URL）** |
| `'6'` | 调用业务流程 | 选择**业务流程** |

---

**第三步：并行查询所有候选资源并展示给用户选择**

> 根据用户选择的操作类型，查询对应的候选列表。**三个接口并行调用，一次性展示。**

```python
# 工作表（operationType 1/2）
forms = bi_utils._request('GET', '/desform/api/list/options', params={'appId': APP_ID})
# 展示: label=表单名称, value=formCode

# 应用内仪表盘页面（operationType 3）——必须按 lowAppId 精确过滤！
pages_resp = bi_utils._request('GET', '/drag/page/list', params={'lowAppId': APP_ID, 'pageNo':1, 'pageSize':100})
pages = [p for p in pages_resp.get('result',{}).get('records',[]) if p.get('lowAppId') == APP_ID]
# 展示: name=页面名称, id=pageId

# 业务流程（operationType 6）——必须用此专用接口，禁止用 /act/process/list
# 只返回「自定义按钮 / 按钮触发」类型流程；空列表 = 应用内还没有该类型流程，去流程里新建后再选
flows = bi_utils._request('GET', '/act/process/extActProcess/listBtProcess',
    params={'processName': '', 'processKey': '', 'lowAppId': APP_ID})
# 展示: processName=流程名称, id=流程ID
```

> **⚠️ 查询接口规范（已踩坑验证）：**
> - 表单：`/desform/api/list/options?appId=APP_ID`（返回应用下设计器表单）
> - 仪表盘页面：`/drag/page/list?lowAppId=APP_ID`，**结果必须二次过滤** `p.get('lowAppId') == APP_ID`（接口返回混入全局页面）
> - 业务流程：`/act/process/extActProcess/listBtProcess?lowAppId=APP_ID`（**专用接口**，`/act/process/list` 返回全局所有流程，禁止使用）

---

**第四步：根据用户选择生成按钮组件**

查到 desformId 后构建 worksheet 对象，然后一次性写入所有按钮：

```python
# 查 desformId（operationType 1/2 必须）
r = bi_utils._request('GET', f'/desform/api/fields/{FORM_CODE}', params={'subTable': True})
desform_id = (r.get('result') or {}).get('id')

# 查视图（operationType 2）
views = bi_utils._request('GET', '/desform/api/list/view', params={'desformCode': FORM_CODE})
# result=None 或 [] → view 填 ''（全部）
```

> **🚨 customPage 必须是对象，不能是字符串 pageId！**
> `'customPage': {'label': '页面名称', 'value': 'pageId', 'key': 'pageId'}`
>
> **🚨 bizFlow 必须是对象，不能是字符串 ID！**
> `'bizFlow': {'label': processName, 'value': id, 'key': id}`

---

**默认按钮样式（强制，除非用户明确指定）：**

```python
'option': {
    'btnType':  'button',   # 按钮样式（非图形）
    'btnStyle': 'solid',    # 方块（非圆形/虚线）
    'btnWidth': 'divide',   # 等分宽度（非自适应）
    'rowNum': len(btn_list),# 每行几个；建议=按钮数，实操可以小于按钮总数
}
```

---

| operationType | 操作 | 必须询问 | customPage/worksheet 类型 |
|--------------|------|---------|--------------------------|
| `'1'` | 创建记录 | 选择**工作表**；可选配置字段默认值 | worksheet=对象，customPage='' |
| `'2'` | 打开视图 | 选择**工作表** → 再选**视图** | worksheet=对象，customPage='' |
| `'3'` | 打开自定义页面 | 选择应用下的**仪表盘页面** → 询问**打开方式**（当前/新页面） | **customPage=对象** `{label,value,key}`，worksheet='' |
| `'4'` | 打开链接 | 用户输入**网页地址** → 询问**打开方式**；可选是否传参 | worksheet=''，customPage='' |
| `'6'` | 调用业务流程 | 立即执行 or **二次确认** → 选择**业务流程**；有传参时配置参数 | worksheet=''，customPage='' |

> 非QQY模式（普通仪表盘）只支持 `'4'` 打开链接。

#### 收集绑定信息的标准流程（强制）

> 用户确认每个按钮的操作类型后，必须先查询候选列表展示给用户选择，再创建按钮。

**worksheet 对象完整结构（operationType 1/2 必须用对象，不能是空字符串）：**
```python
'worksheet': {
    'label': '订单表',                  # 表单显示名
    'value': 'ding_dan_biao_gui5',      # formCode（同 key）
    'key':   'ding_dan_biao_gui5',
    'type':  'form',
    'desformId': '2044729857917284354', # 通过 /desform/api/fields/{code} 取 result.id
},
'desformId': '2044729857917284354',     # 顶层也要填，与 worksheet.desformId 一致
'appInfo': {'type': 'current'},         # 当前应用必填
```

**🚨 chartData 存储规则：**
- 一律用 Python 列表（含 worksheet 对象时也是）。禁止 `json.dumps(btn_list)` 双重编码

> 非QQY模式（普通仪表盘）只支持 `'4'` 打开链接。

#### option 样式结构

```python
'option': {
    'title': '',              # 按钮组标题
    'btnType': 'button',      # 产品「样式」：'button'=按钮 | 'graphical'=图形（用户说「样式图形」时用 graphical！）
    'btnStyle': 'solid',      # 产品「形状」：'solid'=矩形 | 'circle'=圆形 | 'dashed'=虚线
    'btnWidth': 'divide',     # 产品「宽度」：'divide'=等分 | 'custom'=自适应
    'btnDirection': 'column', # 产品「方向」（仅图形）：'column'=上下 | 'row'=左右
    'rowNum': len(btn_list),  # 每行几个；建议=按钮数以便一行排开，不是强制相等
}
```

> `rowNum` = **每行显示几个**，不必等于按钮总数（实操 5 个按钮 `rowNum=4`）。`btnWidth`：`divide` 等分 / `custom` 自适应都合法。`btnType='button'` 时 `btnDirection` 无效。

**🚨 按钮样式实测渲染规则（2026-09-02，`Button.vue` + `ButtonSetModal.vue` 源码确认）：**
- 样式（btnType）radio 中文文案：`按钮` / `图形`。默认 button = 整块色条按钮（宽 `100%` 或 auto + 白字图标左/文字右），用户说「样式图形」而写默认值 = 样式错。
- 形状（btnStyle）radio 无文字，只有 3 个形状图标：方形（solid）/ 椭圆（circle）/ 虚线环（dashed）。**图形样式下**：solid → iconWrap `border-radius:12px` 圆角方块卡；circle → `50%` 正圆；dashed → 灰底、图标用按钮自定义色。按钮样式下 circle → 整条 18px 胶囊圆角。
- 图形（graphical）样式渲染：column 方向 = iconWrap 72×72 上 + name 下；row 方向 = 48×48 左 + name 右。**graphical 强制按 `100/rowNum%` 均分宽度**（btnWidth 不生效）。
- **🚨 图形样式行高**：`.btn-area` `min-height:200px`，h=10（110px）会把按钮名裁掉。图形样式 h 必须 ≥19（209px，建议 20，`config.size.height = h*11`）；普通按钮样式 h=10 即可。
- 中文词 → 枚举映射（add-buttons specs 已支持）：图形/graphical/icon→graphical；按钮/标准→button；矩形/方块/圆角→solid（圆角=圆角方形卡，**不是 circle**）；圆形/椭圆→circle；虚线→dashed；上下/纵向→column；左右/横向→row。

#### chartData 每个按钮完整结构

> 🚨 字段名是 `chartData`，不是 `btnList`！

```python
# ===== 各 operationType 完整结构对照（以正确前端数据为准）=====

# operationType='1' 创建记录
btn_create = {
    'btnId': 'btn' + str(int(time.time()*1000)),
    'title': '创建记录',
    'icon': 'ant-design:plus-outlined',
    'color': '#2196f3',
    'operationType': '1',
    'worksheet': {                        # 必须是对象
        'label': '订单表', 'value': 'form_code', 'key': 'form_code',
        'type': 'form', 'desformId': 'desform_id_here',
    },
    'view': '',
    'defVal': [],                         # op1：[{name,model,type,value,checked:1,key,options,rules}]
    'customPage': '',
    'href': {'url': '', 'isParam': False, 'params': []},
    'openMode': '2', 'bizFlow': '',
    'click': {'type': '1', 'message': {'title': '你确认执行此操作吗？', 'okText': '确认', 'cancelText': '取消'}},
    'appInfo': {'type': 'current'},       # 必须是 {'type': 'current'}，不能是 None
    'desformId': 'desform_id_here',       # 与 worksheet.desformId 一致
}

# operationType='2' 打开视图
btn_view = {
    **btn_create,
    'operationType': '2',
    'worksheet': {'label': '测试表单', 'value': 'form_code', 'key': 'form_code', 'type': 'form', 'desformId': 'desform_id_here'},
    'view': 'view_id_or_empty',           # 无独立视图时填 ''（全部）
}

# operationType='3' 打开自定义页面 🚨 customPage 必须是对象，不是字符串！
btn_page = {
    'btnId': 'btn' + str(int(time.time()*1000)),
    'title': '打开自定义页面',
    'icon': 'ant-design:layout-outlined',
    'color': '#9c27b0',
    'operationType': '3',
    'worksheet': '', 'view': '', 'defVal': [],
    'customPage': {                        # 🚨 对象！不能是 pageId 字符串
        'label': 'AI生成仪表盘',
        'value': '1204574932509007872',
        'key':   '1204574932509007872',
    },
    'href': {'url': '', 'isParam': False, 'params': []},
    'openMode': '2', 'bizFlow': '',
    'click': {'type': '1', 'message': {'title': '你确认执行此操作吗？', 'okText': '确认', 'cancelText': '取消'}},
    'appInfo': {'type': 'current'},       # 必须是 {'type': 'current'}，不能是 None
    # ❌ 不要加 desformId、bizParams（op3 没有这两个字段）
}

# operationType='4' 打开链接
btn_link = {
    'btnId': 'btn' + str(int(time.time()*1000)),
    'title': '打开链接',
    'icon': 'ant-design:link-outlined',
    'color': '#ff9800',
    'operationType': '4',
    'worksheet': '', 'view': '', 'defVal': [], 'customPage': '',
    'href': {'url': 'https://www.baidu.com', 'isParam': False, 'params': []},
    'openMode': '2', 'bizFlow': '',
    'click': {'type': '1', 'message': {'title': '你确认执行此操作吗？', 'okText': '确认', 'cancelText': '取消'}},
    'appInfo': None,
}

# operationType='6' 调用业务流程
# 🚨 Step 1: 先查询业务流程列表
# flows = bi_utils._request('GET', '/act/process/extActProcess/listBtProcess',
#     params={'processName': '', 'processKey': '', 'lowAppId': APP_ID})
# 取 result 列表中用户选择的流程：id → bizFlow.value, processName → bizFlow.label
btn_flow = {
    'btnId': 'btn' + str(int(time.time()*1000)),
    'title': '调用业务流程',
    'icon': 'ant-design:apartment-outlined',
    'color': '#4caf50',
    'operationType': '6',
    'worksheet': '', 'view': '', 'defVal': [], 'customPage': '',
    'href': {'url': '', 'isParam': False, 'params': []},
    'openMode': '2',
    # 🚨 bizFlow 必须是对象，不能是字符串ID！
    'bizFlow': {'label': '流程名称', 'value': '流程ID', 'key': '流程ID'},
    'bizParams': [],                       # 传参配置（仅 op6 有此字段）
    'click': {'type': '1', 'message': {'title': '你确认执行此操作吗？', 'okText': '确认', 'cancelText': '取消'}},
    # 🚨 op6 的 appInfo 必须是 {'type': 'current'}，不能是 None
    'appInfo': {'type': 'current'},
    # ❌ 不要加 desformId（op6 无此字段）
}

# ===== 各字段适用范围速查 =====
# worksheet(对象)   → op1/op2 必填；op3/4/6 填 ''
# desformId(顶层)   → op1/op2 必填；op3/4/6 不要加
# view              → op2 必填；其余填 ''
# customPage(对象)  → op3 必填；其余填 ''  🚨 对象不是字符串！
# href.url          → op4 必填；其余填 ''
# bizFlow(对象)     → op6 必填 {'label':名称,'value':ID,'key':ID}；其余填 ''  🚨 对象不是字符串！
# bizParams(列表)   → 仅 op6 有；其余不要加
# appInfo           → op1/op2/op3/op6 填 {'type':'current'}；仅 op4 填 None

config = {
    'dataType': 1,                   # 🚨 按钮组件固定用 dataType=1，禁止用 4
    'timeOut': 0,
    'chartData': [btn],              # 数组，含绑定也不要 dumps
    'option': {'title': '', 'btnType': 'button', 'btnStyle': 'solid', 'btnWidth': 'custom', 'btnDirection': 'column', 'rowNum': len(btn_list)},
    'compStyleConfig': {},           # QQY必须包含
    'analysis': {},                  # QQY必须包含
    'background': '#FFFFFF', 'borderColor': '#E8E8E8',
    'size': {'width': w*75, 'height': h*11},
}
```

#### defVal（创建记录默认值）

实操结构（整段控件，不是 `{field,value}`）：

```python
'defVal': [
    {
        'name': '名称', 'model': 'input_xxx', 'type': 'input',
        'value': '测试', 'checked': 1, 'key': '1788246488841_314777',
        'options': {}, 'rules': [{'message': '${title}必须填写', 'required': True}],
    },
    {
        'name': '数字', 'model': 'number_xxx', 'type': 'number',
        'value': 11, 'checked': 1, 'key': '...', 'options': {}, 'rules': [],
    },
]
```

#### defVal（创建记录默认值）不支持的字段类型

以下字段类型**不能**设置默认值：`dates` / `daterange` / `datetimerange` / `sub-table-design` / `link-field` / `color` / `auto-number` / `barcode` / `imgupload` / `fileupload` / `file-upload` / `editor` / `capital-money` / `text-compose` / `formula` / `phone` / `email` / `markdown` / `location` / `summary`

#### 其他限制

- 至少保留 1 个按钮（删除时需检查 `chartData.length > 1`）
- 调用业务流程二次确认弹窗可自定义提示文字/确认文字/取消文字

**通过 comp_ops.py 设置按钮 config：**
```bash
# 先查询按钮组件的 i 值
py comp_ops.py list $API_BASE $TOKEN $PAGE_ID

# 用 edit 命令写入按钮配置（chartData 为 JSON 数组文本）
py comp_ops.py edit $API_BASE $TOKEN $PAGE_ID --name "自定义按钮" \
  --set 'chartData=[{"btnId":"btn_001","title":"新增","icon":"ant-design:plus-outlined","color":"#2196f3","operationType":"1","worksheet":"","view":"","defVal":[],"customPage":"","href":{"url":"","isParam":false,"params":[]},"openMode":"2","bizFlow":"","bizParams":[],"click":{"type":"1","message":{"title":"你确认执行此操作吗？","okText":"确认","cancelText":"取消"}}}]'
```
