# 组件词表（按需 · 唯一词表）

> **唯一词表**：与 `scripts/qqy_chart.py` 同源（`COMP_ALIAS`=口语→码、`QQY_CHARTS`=可用 30 码、UI 清单=lowAppMenu）。**新说法/新组件改脚本，禁止在本文件抄全表、禁止在文档再维护第二份对照表**（抄会漂移）。
> **何时查**：`COMP_UNKNOWN=` / 口语不在词表 / 表单统计 J 码确认。查完立刻回执行，禁 grep 脚本、禁为别名读 `charts-special.md`/`create.md` 对码。
> 下表是**常用子集**仅供扫读，全量以脚本为准。

## 统计图 30 可用码（QQY_CHARTS）

| 分类 | compType |
|------|----------|
| 柱形图（4） | JBar、JStackBar、JMultipleBar、JNegativeBar |
| 条形图（3） | JHorizontalBar、JRankingList、JTotalProgress |
| 折线图（4） | JLine、JArea、JMultipleLine、DoubleLineBar |
| 饼状图（3） | JPie、JRing、JRose |
| 漏斗图（2） | JFunnel、JPyramidFunnel |
| 雷达图（2） | JRadar、JCircleRadar |
| 仪表盘（3） | JColorGauge、JGauge、JAntvGauge |
| 数值（1） | JNumber |
| 散点图（2） | JScatter、JBubble |
| 表格（1） | JPivotTable |
| 文本（1） | JWordCloud |
| 地图（4） | JAreaMap、JBubbleMap、JHeatMap、JBarMap |

## 常用口语 → 码（子集；全量见脚本 COMP_ALIAS）

柱状/柱形/基础柱形=JBar ｜ 折线/基础折线=JLine ｜ 多折线/对比折线=JMultipleLine ｜ 面积=JLine（面积外观走 `--line-type 面积`）｜ **饼图=JPie** ｜ 环形/环图=JRing ｜ 玫瑰/南丁格尔=JRose ｜ 词云=JWordCloud ｜ 排行/排行榜=JRankingList ｜ 数字卡/指标卡/数字=JNumber ｜ 透视表/透视=JPivotTable ｜ 双轴=DoubleLineBar ｜ 条形/横向条形=JHorizontalBar ｜ 堆叠柱=JStackBar ｜ 对比柱/多柱/分组柱=JMultipleBar ｜ 正负条=JNegativeBar ｜ 散点=JScatter ｜ 气泡=JBubble ｜ 漏斗=JFunnel ｜ 金字塔漏斗=JPyramidFunnel ｜ 雷达=JRadar ｜ 圆形雷达=JCircleRadar ｜ 色阶仪表=JColorGauge ｜ 仪表盘=JGauge ｜ 区域地图=JAreaMap ｜ 气泡地图=JBubbleMap ｜ 热力地图=JHeatMap ｜ 柱状/柱形/立体柱地图=JBarMap

> ⚠️ 上述口语别名（环形=JRing 等）是**新建加图选型**用；**改已有饼图**「设为环形 / 标签位置」= JPie 内自带 option 开关（`option.isRadius` / `option.pieLabelPosition`），禁按别名 `switch-type` 换 JRing（2026-09-08 实测教训，改法见 `mutate.md`）。

## ⚠️ 表单统计差异（add-form-chart / 工作表右侧统计）

- `--comp` **只收 J 码**（JPie/JBar/JLine/…），**不走上面口语表**——传中文（饼图）必报「组件不在 QQY 清单」。
- 默认：comp=JBar、dim=create_time、val=record_count、query-range=month、date-group=3 → 「本月按日柱状」；要个人计数饼图显式给 `--comp JPie --dim 选项字段 --val record_count --query-range all`。
- 选项类 dim（多选/单选/复选）计数可 JPie；date-group 对非日期 dim 自动忽略，勿按日期口径预期。

## UI / 功能组件（7，仅限 QQY；dataType=1，禁 add-charts）

JCustomButton 按钮 ｜ JText 文本 ｜ JFilterQuery 查询条件 ｜ JCarousel 轮播图（须绑表单图片字段） ｜ JDragEditor 富文本 ｜ JIframe 嵌入URL ｜ JCurrentTime 实时日期

## 禁用清单（chartConfig / lowAppMenu 中不存在，勿添加）

统计类：JDynamicBar、JMixLineBar、JCapsuleChart、JPercentBar、JBackgroundBar、JStepLine、JSmoothLine、JRotatePie、JQuadrant、JCustomProgress、JProgress、JLiquid、JPictorialBar、JPictorial、JRingProgress、JActiveRing、JRadialBar、JRectangle、JBar3d、JBarGroup3d、JFlyLineMap、JTotalBarMap、JTotalFlyLineMap、JCommonTable、JList、JGrowCard、JSimpleCard、JProjectCard
UI 类：JWaitMatter、JDynamicInfo、JQuickNav、JRadioButton、JTabs、JGrid、JImg、JCalendar、JMultiViewCalendar、JArchitecture、JVrHourse

> 记法：饼族 = JPie(饼)/JRing(环)/JRose(玫瑰)；柱族带 前缀（J*Bar）记 形状词；地图族统一 J*Map。
