# 图表专题（按需）

> 仅当 **总进度 / JColorGauge / 环比细节 / 钻取卡住 / 雷达·地图·透视·双轴白屏或不显示** 时读取。  
> 普通柱/折/饼/环/玫瑰/词云/排行/数字（无环比）以及**已点名雷达/四地图/透视/双轴加图** → `add-charts --comp` 旗标（`create.md`；雷达 dim 必填 + `--legend-show`；四地图 ≤30s），**禁止先读本文件**（口语↔J 码/别名确认 → `component-words.md`，禁读本文件与脚本）。  
> 改已有图 CLI → `mutate.md`；建盘/加图 → `create.md`。未点名交互细节 → `qqy-guide-archive.md`。

---

## 0. 雷达 / JColorGauge / JNumber 环比（结构权威）

| 组件 | 规则 |
|------|------|
| **雷达** JRadar/JCircleRadar | 业务加图走 `create.md` 4 步，**勿先读本节**。`dim`=对比对象**必填**（`nameFields:[]` 不渲染）；指标进 `val`（可数组）。「维度轴放销量/售价」= **`val`**。图例=`legendShow:true`。第三指标未点名且表有单价/售价 → 默认「单价」 |
| **JColorGauge** | `dim:[]`；须 1 条 `type:gauge` + `axisLine` 分段；`colors` 写 axisLine，**禁**扩 `type:line` / 只写 `{title,card}`（白屏）。JAntvGauge 可用 `{title,card}`。改色 → `mutate.md` `set-chart-color` |
| **JNumber 环比** | **已有图** → `set-chart-compare`（`mutate.md`），禁手写 py。新建首轮：`queryRange:month`+`isCompare`+`compareType:preMonth`+**`compareValue:0`**+`trendType`（`1`绿升红降/`2`红升绿降；点名升红必须 `2`）+`unit`/`numberLevel`；同步 `analysis.*` 与 `option.isCompare`/`trendType`；**h≥30**。示例 → `gold-specs.md` |

---

## 1. JTotalProgress（总进度图）

**禁止 `add-charts`**（builder 结构 → 设计器编辑卡死）。走 `comp/add` + `saveCompToPage`，1 次进程 1 轮（≤30s）。要点速查已在 `create.md`「总进度图 JTotalProgress」；组装 28 键卡住才读本节下表。

| 步骤 | 动作 |
|------|------|
| 1 | 进程内解析：租户 + `--app-name` + `--page-name` + 表单字段 |
| 2 | 组装 **UI 规范 28 键**扁平 config（见下） |
| 3 | `POST /drag/page/comp/add`（config=JSON 字符串）→ `pageCompId` |
| 4 | `POST /drag/page/saveCompToPage`（`template` **必须** `json.dumps` 字符串；项只含 x/y/w/h/i/component/componentName/pageCompId，**无 config**） |
| 5 | 打印 `ADDED=1` / `SHARE_URL`；默认半行 `w:12 h:32` 追加底部；未说「本月」→ `queryRange=all` |

同应用已有可用 JTotalProgress：深拷贝扁平 config，只改 `option.targetValue` / `filter.queryRange` / 必要时字段，再写入。

**28 键（实测）：**  
`analysis,appId,appType,assistTypeFields,assistYFields,authFieldShowResult,calcFields,chart,compStyleConfig,dataNum,dataType,drillData,filter,filterField,formId,formName,formType,jsConfig,nameFields,option,size,sorts,tableName,timeOut,turnConfig,type,typeFields,valueFields`

| 要点 | 值 |
|------|-----|
| `nameFields` | `[]`（禁止塞维度） |
| `valueFields` | 销量等进度值字段 |
| `option` | **仅** `{series:[进度条,轨道条], targetValue:{'<valueField model>':目标值}}` |
| 进度条 | `barWidth:19 color:#151B87 zlevel:1` + label |
| 轨道条 | `#eeeeee barGap:'-100%' type:bar` |
| `chart` | `{subclass:'JTotalProgress', category:'HorizontalBar'}`（无 isGroup） |
| `size` | `{height:300}` |
| `compStyleConfig` | 含 progress / target / showProgressText |
| 禁止顶层 | seriesType / chartData / dataFilterNum / background / borderColor / actionConfig |
| 禁止 option | title / card |
| 禁止 analysis | compareType |

用户目标值 N → `targetValue[销量model]=N`。禁止为求证再 Read 源码 / 试 `getTotalData`。

---

## 2. 透视表 / 双轴

| 组件 | 关键点 |
|------|--------|
| **JPivotTable** | 行=`nameFields`，列=`typeFields`，值=`valueFields`；`isGroup:true`；顶层必有 `pivotTable`（缺则「暂无数据」）；`showColumnTotal/showLineTotal` 实操为 `true`；`controlList`/`unitList` 对**每个**数值字段一条（`key`=fieldName）；`option` 只需 `{title:{show:true,text:'表格'},card:{…}}`（**option.title 固定「表格」**，用户可见名在 `componentName`）；`analysis.compareType:''`；**关联记录行/列与柱/饼相同必须展开**：`localField`+`fieldName=titleField`+顶层 `sourceCode`（旧「不展开」结论作废，2026-09-04 对照手工修盘） |
| **DoubleLineBar** | `isGroup:true`，`chart.category:'Line'`；左轴分组=`typeFields`，右轴数值=`assistYFields`，右轴分组=`assistTypeFields`；`yAxis:[{"type":"value"},{"type":"value"}]`；`seriesType=[{series:系列名,type:'bar'},…]`（数组，禁止字符串） |
| 跨应用 | `add-charts --form-app-name`；config `appId`=表单应用；查字段前切 `X-Low-App-ID` |

普通图 `assistYFields`/`assistTypeFields` 默认 `[]`。新建 specs → `create.md` / `gold-specs.md`。已有双轴改轴 → `mutate.md` `rebind-chart`。

---

## 3. option / seriesType / 地图（最小必查）

### 通用 option

| 规则 | 说明 |
|------|------|
| 笛卡尔图必须有 series 类型 | `option.series:[{type:'bar'/'line'/'scatter'}]` + xAxis/yAxis/grid，否则 `Unknown series undefined` |
| `isGroup:true` 禁止 `option:{}` | 至少 `series:[]` + grid + tooltip |
| `isGroup` 禁止 `xAxis/yAxis.data:[]` | 只写 `type` 或省略轴，否则分类轴永不填充 |
| 禁止大屏暗色 | 勿写 `axisLabel.color`/`textStyle.color` `#EEF1FA` |
| `seriesType` 必须是数组 | 默认 `[]`；禁止 `'bar'` 字符串（`.map is not a function`） |
| `option.card` | 含 `headColor:'#FFFFFF'`；`title.text`=显示名 |
| HorizontalBar 系 | `JHorizontalBar`/`JRankingList`/`JTotalProgress` 的 `chart.category`=`'HorizontalBar'` |
| JWordCloud | option 仅 `{title,card}` |
| JRankingList | 完整横向条：`yAxis:{data:[],type:'category'}` + `xAxis:{type:'value'}` + `series:[{type:'bar'}]` |
| JGauge | 完整 gauge series（min/max/detail/type:gauge） |
| JColorGauge / 改柱色 | 结构 → 本节 §0；mutate → `mutate.md` `set-chart-color` |
| JAntvGauge | 可用 `{title,card}`（AntV 自渲染） |
| `summary.showField` | `'all'`=全部；`''`=未选；字段名=指定 |
| `totalType` | `'sum'/'max'/'min'/'average'`（禁止 `'avg'`） |
| freeze 四项 | `headerFreeze/unilineShow/lineFreeze/columnFreeze` 全 `True` |
| `commonOption` | **仅** 4 地图需要；其余统计图禁止 |

### 地图（JAreaMap / JBubbleMap / JHeatMap / JBarMap）

点名 dim/val 的业务加图 → `create.md` 4 步（≤30s）。本节只服务于白屏/不显示。

| 规则 | 说明 |
|------|------|
| option 不能 `{}` | 必须含 `geo` + `area` + `visualMap`；**Area/Bar** 可含 map `series`；**Bubble/Heat 禁止预置仅 `type:map` 的 series**（会占 series[0]，气泡/热力不显示；对照手工图：无 `series` 键，前端用 `area.markerType` 拼 effectScatter/heatmap + map） |
| `area` 四图都要 | `markerType` 等；缺 → series type undefined |
| geo 用旧版 ECharts | `itemStyle.normal/emphasis` 嵌套，禁止新版扁平 `areaColor` |
| `commonOption` | Area/Bubble：`barSize:10` + areaColor/inRange…；Heat 加 `heat:{blurSize:20,pointSize:15,maxOpacity:1}`；BarMap `barSize:12` |
| 地图「开启钻取/下钻」开关 | 落盘 **`commonOption.breadcrumb`** = `{drillDown:true, textColor:"#42a5f6"}`（breadcrumb=下钻路径导航，textColor=路径文字色）；**`option.drillDown` 前端不读，写了不生效**（2026-09-08 AI903 JBubbleMap 实测：API 写 option.drillDown=true 页面无变化，UI 手工开启后对比落盘在此） |
| visualMap.seriesIndex | Area=`[0]` show:False；Bubble=`[1]` show:False；**Heat=`[1]` show:True**；Bar=`[0]` show:False |
| JHeatMap 四强制 | ① show:True ② seriesIndex:[1] ③ geo.roam:True ④ heat blurSize:20/pointSize:15 |
| 地图 `colors` | specs 首轮写入 → `visualMap.inRange.color` + `commonOption.inRange.color`（`qqy_ops._apply_spec_colors` 已分流）；红黄热力例 `["#FFEB3B","#FF9800","#F44336"]`；**禁止**对地图扩 `type:line` series、禁止事后 patch |
| JBubbleMap | **默认半行 `w:12 h:35`**（与 §5 行表一致）；`geo.roam:true`；**勿写 `option.series`**；size 可仅 `{height:385}` |
| JHeatMap | 同 Bubble：**勿写 series**；半行 `w:12 h:35`；业务加图只改 `comp`/`dim`/`val`/`colors`，勿先读 archive |
| JBarMap geo | `aspectScale:0.96` + `areaColor:'#37805B'` + `roam:True` |
| **柱顶/数字标签** | specs 首轮 **`scatterLabelShow:true`**（→ `option.area.scatterLabelShow`）；别名 `mapLabel`/`topLabel`/`barLabel`/`labelShow`。业务加图**禁止**为开标签再读本节或事后 `query_page` patch |
| valueFields | 用表单真实数值字段；无数值才兜底 `record_count` |
| **comp 别名（业务侧已够，勿为确认再探查）** | 柱状/柱形/立体柱=`JBarMap`；区域/色块=`JAreaMap`；气泡=`JBubbleMap`；热力=`JHeatMap` |

**JAreaMap 最小 option 骨架：**

```json
{
  "drillDown": false,
  "area": {"name":["中国"],"value":["china"],"markerType":"effectScatter","markerColor":"#DDE330","shadowBlur":10,"markerCount":5,"markerOpacity":1,"scatterLabelShow":false,"shadowColor":"#DDE330"},
  "geo": {"top":30,"zoom":1,"roam":false,"itemStyle":{"normal":{"areaColor":"#f7f7f7","borderColor":"#b0b5c1","borderWidth":0.5},"emphasis":{"areaColor":"#fcc02e"}},"label":{"emphasis":{"show":true,"color":"#000"}}},
  "series": [{"type":"map","map":"china","geoIndex":0,"data":[]}],
  "visualMap": {"min":0,"max":200,"type":"continuous","show":false,"calculable":true,"top":"bottom","left":"5%","seriesIndex":[0]}
}
```

---

## 4. 钻取（补充；CLI → `mutate.md`）

| dataType | mapping target |
|----------|----------------|
| 2（SQL） | FreeMarker 参数名，如 `name=year` |
| 4（QQY） | `name=<nameFields[0].fieldName>`（表单 model，非中文名） |

跨表联动：维度传出的是**显示文本**；目标若绑关联记录（存 id）会失败 → 用他表字段存储模式。  
**无钻取面板：** `JPivotTable` / 四地图 / `JCustomEchart`。

---

## 5. 全组件批量生成（30 统计 + 7 UI）

组件可用/禁清单与口语↔码 → `component-words.md`（与脚本同源）。用户说「全组件 / 所有统计图表」时：

1. 点名表单 → **直接跑** `gen_qqy_all_comps.py`（禁先确认字段；与 SKILL §4「点名全组件」一致）  
2. 脚本内置推荐 dim/val/grp；白屏/失败才回查字段（禁止从头 Write 脚本）  
3. **交付前自检行宽**：每行 w 合计=24，预置坐标有空缺必须一次布局脚本修

```bash
py "$SKILL_REFS/scripts/gen_qqy_all_comps.py" API TOKEN \
  --page-id PAGE_ID --app-id APP_ID --tenant-id TENANT_ID --form-code FORM_CODE \
  [--form-name 名称] [--form-type design|online]
```

推荐字段：dim=首个 string；val=首个 number/money（否则 `record_count`）；grp=第二个 string（否则同 dim）。

脚本内置：仅 `chartConfig(isLowApp=true)` 清单；全部 dataType=4；必含 compStyleConfig/analysis/filter；重生成直接覆盖 template。

### 修复后规范布局（验收锚点）

| 行 y | 组件（类型 → x/w） |
|------|------|
| 0/29/58/87/116/145 | 两两 w=12：JBar+JStackBar、JMultipleBar+JNegativeBar、JHorizontalBar+JRankingList、JTotalProgress+JLine、JArea+JMultipleLine、DoubleLineBar+JWordCloud |
| 174 | JPie(0,12)+JRing(12,12) |
| 203 | JRose(0,12)+JFunnel(12,12) |
| 232 | JPyramidFunnel(0,12)+JRadar(12,12) |
| 261 | JCircleRadar(0,12)+JColorGauge(12,6)+JGauge(18,6) |
| 290 | JAntvGauge(0,6)+JNumber(6,6)+JScatter(12,12) |
| 319 | JPivotTable(0,12)+JAreaMap(12,12) |
| 354 | JBubble(0,12)+JBubbleMap(12,12) |
| 389 | JHeatMap(0,12)+JBarMap(12,12) |
| 424 | JText(0,12)+JCurrentTime(12,12) |
| 441 | JFilterQuery(0,24) |
| 451 | JCustomButton(0,12)+JDragEditor(12,12) |
| 471 | JIframe(0,12)+JCarousel(12,12) |

h 参考（实测区间，同行同 y 对齐即可）：折/柱/饼/环/漏斗/雷达族 28–32（行表间距 29、金标自排 32 均可）、地图 30–35、透视 30–36、仪表盘族 25、JNumber 无对比 17 / **有环比≥30**、文本/按钮 17、编辑器 20、iframe 30、轮播 25、过滤 10。  
修布局：按 `component` 类型改 x/y/w/h + 同步 `config.size`（w×75 / h×11）→ 一次 `save_page`。禁止逐个 `move`。
