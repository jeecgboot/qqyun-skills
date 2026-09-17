# 已有图改配置（mutate 唯一 CLI 家）

> **已点名改一项配置：读文首命令表 → 下一工具=执行。** 禁止 memory / grep 脚本 / `--help` / 手写 py / `comp_ops --set` / 二次 save。  
> 建盘、加图、按钮、查询面板 → `create.md`，不要用本文件。

会话已有 TID/APP/PAGE 直接填。缺 TID 才 `tenants`；本轮点名应用名才 `apps`（见 `SKILL.md` §3）。未给 `--page-name` 且应用内仅一张盘 → 命令自动选用，不必先 `menus`。

```bash
SKILL_REFS="$HOME/.claude/skills/jeecg-lowcode-dashboard/references"
QQY="py $SKILL_REFS/scripts/qqy_ops.py"
COMP="py $SKILL_REFS/scripts/comp_ops.py"
LINKAGE="py $SKILL_REFS/scripts/linkage_ops.py"
LINK="py $SKILL_REFS/scripts/link_ops.py"
# 隐含：PYTHONIOENCODING=utf-8 PYTHONPATH="$SKILL_REFS:$SKILL_REFS/scripts"
# 公共前缀：$QQY <cmd> API TOKEN --tenant-id TID --app-name APP --page-name PAGE
```

`--name` 匹配 `componentName` **或** `option.title.text`。打印的 `REBOUND=` 等是 componentName（可附 `title=`），≠ 绑错，勿再 list。

## 命令表（先扫这里）

| 口语 | 命令 | 停 |
|------|------|-----|
| 改色 / 金色 / 多色 / 柱体渐变 | `set-chart-color --color` / `--colors` / `--gradient` | `COLORED=` |
| 点大小 / 圆角 / 柱宽 / 无专用旗标的样式 | `set-chart-color --style "用户原句"`（可与 `--color` 同条；禁 query_page / 手写 py。**JHeatMap 热力三项除外 → 下行**） | `SIZE_SET=` `COLORED=` |
| 热力地图(JHeatMap) 点大小 / 点模糊大小 / 最大透明度 | `comp_ops edit`：`--set commonOption.heat.pointSize=20` `--set commonOption.heat.blurSize=25` `--set commonOption.heat.maxOpacity=10`（**禁 `set-chart-color --style`**：点大小被解析成 symbolSize 死键、模糊/透明度词跳过——2026-09-09 实测） | `共编辑 N 个组件` |
| 折线类型：曲线 / 折线 / 面积 | `set-chart-color --line-type`（可与 `--color` 同条；口语原样） | `LINE_TYPE=` |
| 词云形状 | `set-chart-color --shape`（口语原样） | `SHAPE_SET=` |
| 饼图(JPie) 设为环形 / 标签位置（中心等） | `comp_ops edit --name … --set option.isRadius=true --set option.pieLabelPosition=center`（**JPie 自带键，禁 switch-type 换 JRing**；内外径键 option.innerRadius/outRadius） | `共编辑 N 个组件` |
| 数值标签 / 百分比标签 | `set-chart-color --label-show` / `--percent-label`（可与 `--colors` 同条） | `LABEL_SET=` |
| 前 N 项 / 按字段排序 | `set-chart-sort --top-n --field --order` | `TOP_N=` / `SORTED=` |
| 图内筛选（≠ 查询面板） | `set-chart-filter` | `FILTERED=` |
| 计算值公式 / 普通数值改成求和计算值 | `set-chart-calc --formula 求和`（可 `--title`） | `CALC_SET=` |
| 环比 / 同比 / 与上月相比 / 升红降绿 | `set-chart-compare --compare --trend` | `COMPARE=` |
| 换维 / 值 / 范围 / 换表 / 双轴 | `rebind-chart` | `REBOUND=` |
| 换类型（柱↔折，维值不变） | `switch-type` | `SWITCHED=` |
| 改图标题 | `rename-chart --title` | `RENAMED=` |
| 图标题样式（颜色 / 加粗 / 字号 / 上下左右边距） | `comp_ops edit`：`--set option.title.textStyle.color=#FFD700` `--set option.title.textStyle.fontWeight=bold` `--set option.title.textStyle.fontSize=20` `--set option.title.top=10` `--set option.title.left=15`（**`set-chart-color --style` 词表不解析标题词**，走「标题样式」节） | `共编辑 N 个组件` |
| 数值单位（后缀/小数位/数量级） | `comp_ops edit --set compStyleConfig.showUnit.unit=元 --set …numberLevel=4 --set …decimal=2 --set …position=suffix`（勿写 option 层，见「数值单位设置」节） | `共编辑 N 个组件` |
| 仪表盘页改名 | `rename-page` | `RENAMED=` |
| 钻取（点柱过滤自己） | `add-drill` | `DRILLED=` |
| 每 N 分钟刷新 | `set-chart-refresh --minutes` | `REFRESH_SET=` |
| 打开总计 / 全部字段 / 汇总平均 | `set-chart-summary --field all --total-type 平均` | `SUMMARY_SET=` |
| 透视前 N 行列 / 开关合计 | `set-pivot --row-n --col-n --line-total 关 --column-total 关` | `PIVOT_SET=` |
| 计算值改回普通字段 | `set-chart-calc --clear --val` 字段原词 | `CALC_SET=` |
| 删盘 | `delete-page` | `DELETED=` |
| 删盘上某个组件（排行榜/图/文本，非整盘） | `comp_ops delete`（qqy_ops 无此命令） | 见下方「删组件」节 |
| 工作表右侧统计改范围 | `set-form-chart --query-range` | `FORM_CHART_SET=` |
| 表单统计图转公共/转个人 | `move-form-chart --type private --to public --title 原词`（同名全改；未中 → CAND 行取真实标题重跑） | `MOVED=` |
| 页移组（未归组页） | `group-menu --group` | — |

> **回执即停点（2026-09-08 教训）：** `ADDED=` / `COLORED=` / `REBOUND=` 等打印即成功。**禁止** dump 页 JSON / query_page 复盘配置、**禁止**翻历史会话 jsonl 考古「上次怎么配的」（同需求 → 本 skill 文档 / 记忆索引）。用户没报白屏/不显示/配色不对就不查组件配置。

## 改色 / 渐变 / 折线类型 / 标签

按组件分流：JBar 实心柱写 `itemStyle.color`；JLine 同步 customColor；饼/多系列只写 customColor；地图/JColorGauge 同命令。

口语「折线类型」=`--line-type` → 落盘 `smooth`/`line`/`area`（曲线另 `smooth=true`）。**禁止** `switch-type JSmoothLine/JArea`。

口语「显示数值标签」=`--label-show`（饼 `{b}\n{c}`）；「百分比标签」=`--percent-label`（饼 `{b}\n{d}%`）。可与 `--colors` 同条。无 `--name` 则同类型全改。

**JPie 数值文字颜色 ≠ 色板颜色**（2026-09-08 AI看板903 实测）：`--color/--colors` 对饼/多系列只写 `customColor`（大写 hex，如 `#1890FF`）——用户要「数值颜色蓝色」时改到的是扇区色板，**文字颜色不动**。数值文字的 颜色/字号/字重 直写 series label 键：

```bash
$COMP edit API TOKEN PAGE_ID --name 销售额构成 \
  --set "option.series[0].label.color=#1890ff" \
  --set "option.series[0].label.fontSize=15" \
  --set "option.series[0].label.fontWeight=lighter"
```

设计器 UI 写出的 label 色值是小写 hex（`#1890ff`，与脚本大写的 customColor 可区分来源）；「字体大小15/细体/字号」等词 `set-chart-color --style` 词表全跳过（`NOTE=未知颜色`，无有效样式直接 usage 退出），字号/字重只能 edit 写键。

```bash
$QQY set-chart-color API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --comp 柱状图 --color 金色
# 多色 --colors 口语色名；渐变 --gradient --colors A,B
# ⚠️ 地图(JAreaMap)深浅色阶：匹配用 --comp 类型码 + --match-dim <dim内部id>（给标题/名字会 CHART_NOT_FOUND）
#   色词禁带「XX金额…大小」等尾巴（整段被当颜色字吞 → NOTE=未知颜色、色不落盘）；一律显式 hex：
#   --comp JAreaMap --match-dim radio_xxx --colors "#9ecae1,#08306b" --gradient（2026-09-08 实测落盘 MAP_INRANGE）

$QQY set-chart-color API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --comp 折线图 --color 黄色 --line-type 面积

$QQY set-chart-color API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --name CHART --colors 紫,绿,黄 --label-show
$QQY set-chart-color API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --comp 词云 --shape 用户原词
$QQY set-chart-color API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --name CHART --style "用户样式原句"
```

柱体渐变落盘：`itemStyle.showLinearGradient=true` + `customColor:[{color,color1}×N]` **每色一条**（禁一条 `{color:A,color1:B}`）。新建图 specs 写 `showLinearGradient:true` + `colors:[A,B]`（`create.md`）。

实心柱 `--color` ≠ 柱体渐变 `--gradient --colors A,B`。

**地图渐变色阶（JAreaMap 色块深浅，实测 2026-09-08）：** 描色散写不解析，用原句进 `--oral`：

```bash
$QQY set-chart-color API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --name 各省销售额分布 --oral "地图颜色按销售额大小用渐变色阶由浅到深表示，数值越高颜色越深"
```

回执 `ORAL_APPLIED=val,colors,showLinearGradient` + `COLORED=` 即成功；落盘 `commonOption.inRange.color` 色带（如 `[#04387b,#467bc0]`），**配置无字面 `showLinearGradient` 键属正常**；`visualMap.max:200` 为建图骨架默认，前端按数据驱动，**勿 patch**；`NOTE=未知颜色…已跳过` 属预期，非失败。

**地图视觉映射（开关 / 数值区间；2026-09-09 AI903 JBubbleMap 实测沉淀）：** `--oral` 只解析**区域配色**（口语色词自动映射 hex：红黄蓝绿 → `#FF4D4F,#FFD700,#1890FF,#52C41A`，落盘 MAP_INRANGE=`commonOption.inRange.color`，回执 `ORAL_APPLIED=colors`）；「开启视觉映射 / 最小值0 / 最大值10000」**不进 oral 词表**。开关+区间键 = 标准 echarts，全在 `option.visualMap.{show,min,max}`（勿写 commonOption 层；「骨架 max:200 前端按数据驱动勿 patch」指默认值无需改——用户点名固定区间时以点名为准，直写即生效）：

```bash
$COMP edit API TOKEN PAGE_ID --name 中国省份销售额气泡地图 \
  --set option.visualMap.show=true --set option.visualMap.min=0 \
  --set option.visualMap.max=10000
# 非租户2 QQY 页：menus 一次取 PAGE_ID + 预置 X-Tenant-Id/X-Low-App-ID runpy（模板见「删组件」节）
```

**饼图「设为环形 / 标签位置」（2026-09-08 实测沉淀）：** QQY 饼图(JPie) 设计器自带键，`set-chart-color --style` 词表不解析 → 走 `comp_ops edit`（非租户2 页先预置租户头，见「删组件」节模板）：

```bash
$COMP edit API TOKEN PAGE_ID --name 销售额构成 \
  --set option.isRadius=true --set option.pieLabelPosition=center
# option.isRadius=true = 环形（option.innerRadius/outRadius=60/100 控内外径，沿用画布值即可）
# option.pieLabelPosition=center = 标签位置中心（饼图专键；勿 patch series[].label.position 原始键）
# ⚠️ 教训：勿 JPie→JRing 换型！用户要「设为环形」= JPie 内开开关，换型=改组件种类（图例/模板都变），
#   且 UI 再保存会以饼图模板整体覆盖 option，换型痕迹全丢还白改一轮
```

## 前 N 项 / 排序

`dataFilterNum` 截 X 轴不是系列数。`sorts.name` 落图上已绑 `fieldName`（中文名从图维值解析，禁 `fields`）。未点名方向默认 `desc`。≠ `set-chart-filter`。

> **⚠️ `sorts.name` 只认图上真实列键**（已绑 fieldName / 聚合输出列）。自动金额公式值（`$money…$*$number…$`，表单图无 calc 自拼）和聚合 calcId 后缀键（`库存合计69c48` 型）写进 name → 前端不认 → **整图白屏**，设计器手工保存（清空 name，剩 `{name:"",type:"desc"}`）才恢复。脚本已对这两类自动留空 name、只写 type/前 N（2026-09-08 修复；实例 lessons §63/§65）。

```bash
$QQY set-chart-sort API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --name CHART --top-n N --field 数值字段 --order desc
# 也可 --sort 字段降序；只截条数可只 --top-n
```

## 图内筛选

≠ 查询面板 `add-filter` / `edit-filter`（那些在 `create.md`）。数值筛选**无** `val`/`rule`。

`condition`：`1`= `2`≠ `3`> `4`< `5`≥ `6`≤ `7`空 `8`非空 `9`范围内 `10`不在范围。

```bash
$QQY set-chart-filter API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --name CHART --field FIELD --op 大于 --value 100
# 口语「数字」且表无该字段 → 回落到图 valueFields；--clear
```

## 计算值

≠ rebind。聚合码：`1`求和 `2`最大 `3`最小 `4`平均 `5`计算。须同步 `calcFields`+`valueFields`。  
点名图即使还没有计算值：把当前数值字段升级为 `$model-1$`（求和）。禁止 dump 页 JSON / 手写 py。同句改标题加 `--title`（一条、一次 save）。

```bash
$QQY set-chart-calc API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --name CHART --formula 求和 --title 新标题
$QQY set-chart-calc API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --comp 柱状图 --formula 求和×求和
$QQY set-chart-calc API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --name CHART --clear --val 字段原词
```

## 刷新 / 总计 / 透视限制

```bash
$QQY set-chart-refresh API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --name CHART --minutes 每5分钟
$QQY set-chart-summary API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --name CHART --field all --total-type 平均
$QQY set-pivot API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --name CHART --row-n N --col-n M --line-total 关 --column-total 关
$QQY delete-page API TOKEN --tenant-id TID --app-name APP --page-name PAGE

**JPivotTable 通用 UI 键位（2026-09-08 AI看板903 实测；set-pivot 只覆盖 row/col-n 与 showLineTotal/showColumnTotal，其余走 `comp_ops edit`，非租户2 预置头模板见「删组件」节）：**

- 单行显示=`compStyleConfig.unilineShow`；是否分页=`compStyleConfig.izPage`；表头冻结=`compStyleConfig.headerFreeze`（均在 compStyleConfig 层，非 option）
- 列汇总（右侧合计列）：`pivotTable.columnSummary.controlList[i].show`（逐值指标开关）+ `showName`（列标题提示词，如「鸳」）+ `totalType`（sum 求和）+ `pivotTable.showColumnTotal=true` 同步
- ⚠️ 列汇总「位置」= `pivotTable.columnSummary.location` **只认数字枚举码 `"2"`=右侧**——写字符串 `"right"` 前端不认，提示词不显示（2026-09-08 手工对照实测）
- 行汇总（底部总计行）= `pivotTable.lineSummary.controlList[i].show`（location `"bottom"`），UI 手工保存会把同组 `controlList[].show` 一并打开、并补全 `unitList[]` 为 {unit,numberLevel,position,decimal,key}——API 单点改后勿假定其他键没被 UI 联动
- 前 N 行/列截断 = `pivotTable.showLineCount/showColumnCount`
$QQY set-form-chart API TOKEN --tenant-id TID --app-name APP --form-name FORM \
  --type private --title TITLE --query-range 全部
```

## 环比 / 同比

已有 **JNumber**。口语「打开与上月相比、升红降绿」。禁 grep `isCompare`、禁手写 py、禁 `comp_ops --set`。  
开对比时 `queryRange` 不能 `all`（上月→`month`）；`h<30` 自动抬到 30。结构权威 `charts-special` §0。

```bash
$QQY set-chart-compare API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --name CHART --compare 上月 --trend 升红降绿
# --compare 上月/环比/preMonth / 上年/同比/preYear
# --trend 升红降绿=2 / 升绿降红=1
```

## 换维 / 值 / 表 / 双轴

类型不变。未点名的轴/维值保留；换表时清空旧 conditionFields；未点名范围默认 `all`。跨应用须同时 dim+val。点名 dim/val 不存在 → 铁律停问。双轴结构卡住 → `charts-special.md` §2。

```bash
$QQY rebind-chart API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --name CHART --dim DIM --val VAL --query-range all
# 标题未知：--match-dim … --comp JBar
# 跨应用：--form-app-name … --form-name … --dim … --val …
# 双轴右轴：--comp DoubleLineBar --assist-y … --assist-type …
```

## 换类型

dim/val/范围不变。非 add-charts、非删旧重建。同族笛卡尔优先；跨到地图/数字卡/总进度勿硬切。QQY `dataType=4` 须深拷贝后只翻类型标记。

`--to` 接用户原词（折线图/柱状图）。禁 `JSmoothLine`/`JArea`（面积用 `--line-type`）。缺 PAGE_ID → §3 `menus` 一次（勿 `qqy_ops pages`）。

```bash
$COMP switch-type API TOKEN PAGE_ID --name CHART --to 折线图
```

保留：`nameFields`/`valueFields`/`filter.queryRange`/表单绑定/坐标/标题。

## 改图标题 / 页改名

`rename-chart` 一次写齐：`componentName`=新标题；`option.title`=`{show:true,text:新标题}`；`option.card.title`=**`''`**（非空 → 双标题 /「tab标题」）。禁 `comp_ops edit --set option.title.text`。

**同名歧义：** `--name` 匹配 componentName **或** `option.title.text`；新建漏叠 `--title` 时默认标题=自动统计描述（2026-09-08 起非组件名；结构相同的图会撞同名题） → `CHART_AMBIGUOUS count=N`。此时 `--match-dim` 与 `--name` **同给会被忽略**；去掉 `--name`、只给 `--match-dim`（用 add-charts 打印的 dim 内部 id，非中文名）即唯一命中。

页改名（侧栏菜单同步；禁只用 `page_ops.py rename`）：

```bash
$QQY rename-chart API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --name OLD --title NEW
$QQY rename-page API TOKEN --tenant-id TID --app-name APP --page-name OLD --name NEW
```

## 图标题样式（2026-09-08 实测沉淀）

QQY 图标题样式键 = `option.title.textStyle.{color,fontWeight,fontSize}` + `option.title.top/left`（px）。盘上设计师先例：`title.textStyle={fontWeight:"normal"}`、`title.left=10`。`--name` 匹配 componentName（=标题文字），直跑即改：

```bash
$COMP edit API TOKEN PAGE_ID --name 销售额构成 \
  --set "option.title.textStyle.color=#FFD700" \
  --set "option.title.textStyle.fontWeight=bold" \
  --set "option.title.textStyle.fontSize=20" \
  --set "option.title.top=10" --set "option.title.left=15"
```

**禁止**为此 dump 页 JSON / 查组件结构 / grep 脚本——`set-chart-color --style` 报「必须提供」即表外，直接走本命令。非租户2 QQY 页：menus 一次取 PAGE_ID + 预置 X-Tenant-Id/X-Low-App-ID runpy（模板见「删组件」节）。

## 图例样式（2026-09-09 AI903 实测沉淀）

QQY 图例（option.legend）权威键 = **`t`/`r`/`b`/`l` 数字百分比**（5=5%，无 `%` 字符串）+ `orient`（vertical 竖排/horizontal 横向）+ `textStyle.fontSize`。⚠️ **echarts 标准 `top`/`left`（字符串 `"5%"`）前端不读 = 死键**——2026-09-09 AI903 实测：`--set option.legend.top=5%` 落盘保存成功但页面边距无变化；用户手工 UI 保存后真实值落 `t:5`/`r:5`，`top`/`left` 残留未被 UI 清除（UI 保存只重写自己认识的键，死键遗留无害但证前端不消费）。同批写入的 `textStyle.fontSize=15`/`orient=vertical` 生效 = 与 echarts 共用键，故「部分生效部分失效」= 键位差异，非保存失败。UI 面板无 b/l 字面先例（JScatter 等 legend 仅 `{show}`，JPie 手工后仅 `{t,r}`），按需直写 t/r/b/l 即可：

```bash
$COMP edit API TOKEN PAGE_ID --name 销售额构成 \
  --set "option.legend.t=5" --set "option.legend.l=5" \
  --set "option.legend.textStyle.fontSize=15" \
  --set "option.legend.orient=vertical"
# 非租户2 QQY 页：menus 一次取 PAGE_ID + 预置 X-Tenant-Id/X-Low-App-ID runpy（模板见「删组件」节）
```

## 数值单位设置（后缀文本 / 小数位 / 数量级）（2026-09-08 实测沉淀）

QQY 图组件「数值单位」权威键位 = `config.compStyleConfig.showUnit`（设计器单位面板落盘点），结构 `{unit, numberLevel, position, decimal}`：

- `unit` 字符串后缀文本（元/个…）；`position`=`suffix`/`prefix`（后/前缀）
- `numberLevel` **字符串码**（实测 `"4"`=万；金标 JNumber「万元」同配 4）；`decimal` 数字=小数位
- ⚠️ **勿写 option 层** `option.unit/numberLevel/decimal`（2026-09-08 AI903 实测：`comp_ops edit --set option.unit=元` 成功落盘 `config.option.unit`，但前端单位渲染不读 option 层 → 页面无变化；用户手工 UI 保存后正确值落在 `compStyleConfig.showUnit`，option 层残留键无害）。辅助轴为空时 `assist.showUnit` 默认三键 `{unit:"",numberLevel:"",position:"suffix"}`（无 decimal，与主 showUnit 四键可区分）

```bash
$COMP edit API TOKEN PAGE_ID --name 销售额构成 \
  --set compStyleConfig.showUnit.unit=元 \
  --set compStyleConfig.showUnit.numberLevel=4 \
  --set compStyleConfig.showUnit.decimal=2 \
  --set compStyleConfig.showUnit.position=suffix
# comp_ops edit --set 路径 = config 内相对路径（打印 config.option.unit = config[option][unit]），直写 compStyleConfig.showUnit.* 即权威位置
# 非租户2 QQY 页：menus 一次取 PAGE_ID + 预置 X-Tenant-Id/X-Low-App-ID runpy（模板见「删组件」节）
```

## 仪表盘刻度样式（JGauge / JColorGauge；2026-09-08 AI903 实测沉淀）

JColorGauge「销量当前百分比」实测：键位=标准 echarts gauge，全在 **`option.series[0]` 扁平键**（勿猜 axisLine.ticks / 顶层自定义键）。口语「仪表盘」的组件类型先 `comp_ops list` 分清 JGauge / JColorGauge / JAntvGauge——**JAntvGauge（AntV 自渲染）无这些键，勿改**；前两者同构。`set-chart-color --style` 词表不解析 gauge 词 → **直走 `comp_ops edit`**，禁为键位读 default_configs.json / grep 脚本（词表行骨架已默认 `axisTick.show:true` `splitLine:{length:12,width:4}` `detail.fontSize:25` `axisLabel.fontSize:12`，实测色 #eee）。

| 口语 | 键（路径前缀 `option.series[0].`） |
|------|------|
| 关闭刻度线 | `axisTick.show=false` |
| 指标字号（中央数值） | `detail.fontSize=N` |
| 刻度长度 | `axisTick.length=N` |
| 刻度字号（刻度数字） | `axisLabel.fontSize=N` |
| 刻度颜色 | `axisTick.lineStyle.color=#hex`（小写） |
| 分割线长度 | `splitLine.length=N` |
| 分割线颜色 | `splitLine.lineStyle.color=#hex`（小写） |

```bash
$COMP edit API TOKEN PAGE_ID --name 销量当前百分比 \
  --set option.series[0].axisTick.show=false \
  --set option.series[0].detail.fontSize=25 \
  --set option.series[0].axisTick.length=25 \
  --set option.series[0].axisLabel.fontSize=15 \
  --set option.series[0].splitLine.length=15 \
  --set option.series[0].axisTick.lineStyle.color=#ffd700 \
  --set option.series[0].splitLine.lineStyle.color=#ff0000
# 非租户2 QQY 页：menus 一次取 PAGE_ID + 预置 X-Tenant-Id/X-Low-App-ID runpy（模板见「删组件」节）
```

## 热力地图热力配置（JHeatMap；2026-09-09 AI903 实测沉淀）

「各省销售额热力分布」实测：热力点「点大小/点模糊大小/最大透明度」权威键 = **`config.commonOption.heat.{pointSize, blurSize, maxOpacity}`**（勿写 `option.series[0].symbolSize`）。**禁走 `set-chart-color --style`**——词表把「点大小」解析成通用 symbolSize 写死键（回执仅 `ORAL_APPLIED=symbolSize` 即此坑特征），「点模糊大小/最大透明度」不在词表直接跳过 → 三项残缺。判型 JHeatMap 可 `comp_ops list` 看 component 列。热力三项 → 直走 `comp_ops edit`（非租户2 页预置 X-Tenant-Id/X-Low-App-ID runpy 模板见「删组件」节）：

```bash
$COMP edit API TOKEN PAGE_ID --name 各省销售额热力分布 \
  --set commonOption.heat.pointSize=20 \
  --set commonOption.heat.blurSize=25 \
  --set commonOption.heat.maxOpacity=10
# 键位与建图骨架默认（blurSize:20/pointSize:15/maxOpacity:1）→ charts-special §3 地图节；
# maxOpacity 用户给值直写不换算（骨架 1=默认，用户报 10 就写 10，canvas 超 1 自钳位=拉满）
```

## 钻取

维名中文即可；省略 mapping 则用图上第一维。卡住 → `charts-special.md` §4。≠ 联动 `add-linkage`。

```bash
$QQY add-drill API TOKEN --tenant-id TID --app-name APP --page-name PAGE --name CHART
# 指定维：--mapping 名称  或 --dim 名称
```

## 联动（组件间，linkage_ops.py）

| | 联动 `add-linkage` | 钻取 `add-drill`（上） |
|--|------|------|
| 刷新 | **其他**组件 | **自身** |
| 参数 | `--source` + `--target` | `--name` |
| mapping | `src=tgt`，多组逗号分隔 | QQY：`name=<nameFields[0].fieldName>` |

```bash
$LINKAGE show API TOKEN PAGE_ID
$LINKAGE add-linkage API TOKEN PAGE_ID --source "源图" --target "目标图" --mapping "value=age"
$LINKAGE remove-linkage API TOKEN PAGE_ID --source "源图" --target "目标图"
# 禁止 --source/--target 混给 add-drill；mapping 用 `=` 不用 `:`
```

## 图表外链 / 自定义 JS（link_ops.py）

```bash
$LINK show API TOKEN PAGE_ID
$LINK set API TOKEN PAGE_ID --name "图表名" --url "https://…?c=\${name}"
$LINK remove API TOKEN PAGE_ID --name "图表名"
$LINK set-js API TOKEN PAGE_ID --name "图表名" --js 'window.open("…");return false;'
$LINK remove-js API TOKEN PAGE_ID --name "图表名"
# URL 占位 ${name}/${value}/${type}；打开方式 --target _blank（默认）/_self
# jsConfig 执行顺序：jsConfig →（return true?）→ 外链 → 联动 → 钻取
```

## 组件几何 / 通用编辑（comp_ops.py；勿动统计绑定）

```bash
$COMP list API TOKEN PAGE_ID
$COMP edit API TOKEN PAGE_ID --name "组件名" --set "option.showValue=true" --set "option.unit=个"
$COMP move API TOKEN PAGE_ID --name "组件名" --x 0 --y 17
# move 改了 --w/--h 后须修回像素 size：width=w*75 height=h*11
$COMP batch-add API TOKEN PAGE_ID --specs-file BATCH.json   # 仅静态/UI（≥2 个一次 save）
$COMP delete API TOKEN PAGE_ID --name "组件名"（或 --type JRankingList / --id，按 componentName 匹配，含 JGroup 组内）
```

**顶置 / 插入级联（2026-09-08 实测）：** 密排盘无空行时（如 AI903：顶部 y0–92 被 按钮组 24x60 + 操作按钮 24x18 + 横幅 24x14 占满，全页 25 组件 0..521 密排）新增 10 单位高面板并顶置 = 插入行以下全组件顺移：双面板顶置 y=0/10 → 面板原占位之上的组件 +20、之下 +10（原位空档吸收 10）；单面板插任意行 → 该行之下全部 +10。坐标 `comp_ops list` 一次现取现算净位移，禁抄他盘 y 字面量；纯 y 位移安全、无需回修像素，批量逐件 move 保存。

改图标题用 `rename-chart`（禁 `comp_ops edit --set option.title.text`）；QQY 统计图添加走 `add-charts` / JT 走 `comp/add`（**禁止 `comp_ops add`**，默认 dataType=1）。

## 删组件 / 非租户2 页预置头 runpy 模板（2026-09-08 实测）

**本标题 = 全文档 grep 锚点**：`图标题样式 / 数值单位 / 仪表盘刻度 / 饼图环形` 等处「模板见『删组件』节」都指本节代码块（曾因本节是「组件几何」尾部无标题段落，`grep ^## 删组件` 不中致跨节指针失效，2026-09-09 修正）。删组件走 `comp_ops delete`（qqy_ops 无此命令），`--name` 按 componentName——口语 ≠ 真实名时先 `comp_ops list` 现取（含 JGroup 组内）。

**QQY 非默认租户页面（TID≠2）必须先预置租户头**：comp_ops 直跑不发 X-Tenant-Id → 非租户2 的页面 result 为空；且 pageId 须先 `qqy_ops menus` 取当前值（`--tenant-id/--tenant-name` + `--app-id/--app-name` 按名解析均可，2026-09-09 实测；凭证旧 pageId 会过期，如 1009/902「本月订单看板」旧 1255059562517110784 → 新 1257220110994251776）。预置头后 runpy 执行（init_api 不带 extra 不清预置值）：

```bash
REFS="$(cygpath -m "$SKILL_REFS")"; COMP="$REFS/scripts/comp_ops.py"
PYTHONIOENCODING=utf-8 PYTHONPATH="$REFS;$REFS/scripts" py -c "
import sys, bi_utils
bi_utils.EXTRA_HEADERS = {'X-Tenant-Id': '1009', 'X-Low-App-ID': '2095077235819794433'}
sys.argv = ['comp_ops', 'delete', API, TOKEN, PAGE_ID, '--name', '销售额排行榜']
import runpy; runpy.run_path(r'$COMP', run_name='__main__')
"
```
