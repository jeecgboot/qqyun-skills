# 建盘 / 加图 / 按钮过滤 / 复合盘

> 已有图改色/标签/排序/环比/换绑等 → **`mutate.md`**，不要用本文件。  
> 规则权威：本页。可复制 specs JSON → `gold-specs.md`（字面量须按当轮点名替换）。

```bash
SKILL_REFS="$HOME/.claude/skills/jeecg-lowcode-dashboard/references"
QQY="py $SKILL_REFS/scripts/qqy_ops.py"
# PYTHONIOENCODING=utf-8 PYTHONPATH="$SKILL_REFS:$SKILL_REFS/scripts"
# Windows JSON：--specs-file + py -c json.dump / Write（UTF-8 无 BOM）
```

`ADDED=` / `SIZE_SET=` / `PAGE_ID=` / `SHARE_URL=` / `AGG_SAVED=` / `FILTER_EDITED=` 打印完 → 删临时 JSON → 停。

## 空白盘

```bash
$QQY create-page API TOKEN --tenant-id TID --app-id APP_ID --name "看板名" --group "分组"
# 租户可按名（--tenant-name）；⚠️ 应用不解析名称——必 --app-id（本命令是唯一例外，其余写命令 --app-name 即可）
```

未指定 `--group` → 第一个已有分组。业务单表/复合盘优先 `create-dashboard`（免 pageId）。

## 单表新建盘

金额类图**省略 `calc`**（显式须真实 `$model-N$`，禁占位 `$money_xxx$`）。按日 `--date-group 按日`。

```bash
$QQY create-dashboard API TOKEN \
  --tenant-name "…" --app-name APP --form-name FORM \
  --name "看板名" --specs-file SPECS.json
```

## 已有盘加图（非 JTotalProgress）

**单图（≤30s）：** `add-charts --form-name FORM --oral "用户这张图的原句"`。点名 dim/val/按日/本周叠 `--dim/--val/--date-group` **或写结构句进 `--oral`**（维度=/数值=、透视 行=列=值=、双轴 左轴…右轴…——解析与自动标题规则见 `SKILL.md` 铁律 #1）；点名标题叠 `--title`。没有圆角/配色等旗标时原句进 `--oral` 立刻跑。`dim=None` 叠旗标短跑。禁为单图读本文 / Write specs。`ORAL_APPLIED=` / `ADDED=` 即停。

**多图才 Write specs（≤60s；四地图 ≤30s）：** ① 点名维值跳过 `fields` ② Write specs（已有盘勿 `y:0`，省略 y 则装箱；`queryRange`/`dateGroup`/`comp` 口语或码，脚本归一；colors / percentLabel / scatterLabelShow / legendShow / dataFilterNum / sorts / barWidth / borderRadius / labelShow / 环比三元组 / showLineTotal 首轮写全；保持默认浅蓝=勿写 colors）③ `add-charts --app-name --page-name --form-name` → `ADDED=` 删临时 JSON 停。  
禁止：开场 `memory_search`、grep 组件名/`dataFilterNum`/`barWidth`/`scatterLabelShow`/`legend`、为确认 `comp`/option/柱顶标签/图例读 `charts-special`/脚本/`gold-specs`、事后 `set-chart-color`/`set-chart-sort`/`query_page` patch 补本轮已点名项。仅缺 JSON 骨架才读 `gold-specs.md`。specs 一次写成功再跑（优先 Write；禁 `py -c` 漏 argv 空跑）。「不是最新」立刻原命令重跑，禁读 `save_page`。

**`comp` 口语直接进 `--comp`/specs**（脚本按唯一词表 `qqy_chart.py COMP_ALIAS` 归一；口语↔码速查 → `component-words.md`。禁止在本文查 J 代码、禁 grep 脚本）。雷达 dim 必填 + `--legend-show`；地图半行 + `--scatter-label`。勿手写 option 骨架。仅 JColorGauge / 环比细节 / JT / **白屏或不显示** → `charts-special.md`。

```bash
# 单图：原句进 --oral（推荐）
$QQY add-charts API TOKEN --tenant-id TID --app-name APP --form-name FORM \
  --oral "用户这张图的原句"
# 多图才 --specs-file
$QQY add-charts API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --form-name FORM --specs-file SPECS.json
# 跨应用：--form-app-name … --form-name …
# 聚合表：--form-name 写聚合名即可（自动 form_type=aggregation）
```

| 项 | 规则 |
|----|------|
| 新建换类型 | 只改 specs `comp`/title/dim/val → `add-charts`。已有图改类型/维绑 → `mutate.md` |
| 多折线 | `JMultipleLine` + `grp`；`colors` 定色板前 N 色；`dataFilterNum` 截 X 轴不是系列数 |
| 改色路径（新建） | JBar/JHorizontalBar 实心柱=`series[0].itemStyle.color`；柱体渐变=`showLinearGradient`+`customColor` **每色一条**；JLine/JArea=itemStyle+customColor 同步；饼/多系列=`customColor`。未写 `colors` 时 option 已带手工默认（JBar/JHorizontalBar/JLine `#64b5f6`）；保持默认浅蓝=勿写 `colors` |
| 前 N / 排序（新建） | `dataFilterNum:N` + `sorts:{"name":"数值中文名","type":"desc"}`；脚本把 name 解析成 field model |
| **标题 / 口径（新建）——需求必须点名，别只给"统计哪张表 记录数"** | 需求只写「数字指标卡，统计【考勤打卡】，统计项：记录数量」时，标题是空的、口径默认全量，做出来用户一看就是「标题没匹配上」。**每张卡/图都要问清三件**：① **标题** ② **时间范围**（今天/本月/全年…）③ **筛选条件**（如 打卡状态=迟到）。落库键位**按组件类型分三种，不是两种**：<br>· JNumber 标题 = `config.option.card.title`（**不是** `option.title`，写错就是空标题）<br>· **JPivotTable 标题也 = `config.option.card.title`**——透视表**没有 ECharts 标题区**，`option.title.text` 落的是平台占位「表格」，真标题只能走卡头；只写 `title.text` ＝ 表头一片空白。**2026-09-16 二次返工实测**（`card.title` 补上即恢复显示）<br>· 其它图（饼/柱/折…）标题 = `config.option.title.text`，且 `card.title` **必须留 `''`**（写非空 → 双标题，见下方硬禁令）<br>· 口径 = `config.filter`：`{conditionMode, conditionFields:[{condition:"1", fieldName:<字段model>, fieldTxt:<中文名>, fieldValue:<值>}], queryField:<时间字段model|create_time>, queryRange:"today/month/year", customTime:[]}`<br>⚠️ 同一盘里 `queryRange` **逐卡不同是正常的**（参照盘「今日应到人数」用 `year`，其余今日卡用 `today`，图表用 `month`），不要统一成一个值。2026-09-16 实测：整盘 6 张 KPI 标题全被用户退回重做。**验收**＝**按组件类型分支回读**（JNumber/JPivotTable 断言 `option.card.title` 非空；饼/柱/折断言 `option.title.text` 非空），**再打开盘逐卡看是否真的渲染出来**＋数字是否符合口径。⚠️ **「键非空」≠「渲染出来」**——接口 success 和我自己的断言通过都不算验收（2026-09-16 连续两轮用「键非空」冒充验收被用户截图退回）。拿不准某类型的渲染键时，先找**同租户被打开过的盘**（`visitsNum>0`）逐键对照，别只信本文档。**本表的键位只留在 skill 里**：写需求/规格文档时只写业务口径（标题＋时间范围＋筛选条件），把 `config.option.card.title` 这类实现细节写进规格会被用户退回（2026-09-16「这个不应该是放到仪表盘的skill中吗」） |
| 其它样式 | 无专用旗标一律进 `--oral`/`--style`（点大小/圆角/柱宽/配色/形状/标签）；禁 grep option |
| 布局 | 同行同 y；半行 `w:12`，柱/折/饼 h=30–32；整行 `w:24`；3 KPI 各 `w:8`（4 个各 `w:6`）；底部=省略 y（⚠️ 省略 x/y = 顺序竖排，不自动左右并排——**并排/同行必须显式 x/y**，2026-09-08 实测踩坑）；地图半行 `w:12 h:35`（勿 `w:24`）；透视整行 h=30–36。全组件行表 → `charts-special.md` §5 |
| 地图 | `--comp` 接用户原词（柱状地图/区域地图/…）；点名柱顶标签 → `--scatter-label`（禁读专题、禁事后 patch） |
| 空维 | 仅数字卡 / 色阶仪表 / 总进度可 `dim:[]` |
| **透视 val** | **不能为空数组**。「清单式」透视（只列字段、不统计）写 `val:[]` 会让 `add-charts` **直接失败** → 给 `record_count`，`dim` 放要列的字段。2026-09-16 实测：一批 25 张盘里 **13 张**栽在这一条 |
| `--date-group` | 口语按日/每天/按月；码=1年/6年月/2月/7月简/3日/4时/5分，口语与码等价。**仅日期维生效**；明细表无日期字段 → 按日回退 `create_time`+3 |
| `--query-range` | 口语全部/本月/本周/上月…与码（all/month/week/preMonth…，共 16 码）等价，脚本归一。**未说默认**：仪表盘图=`all`；表单统计 add-form-chart=`month`（要全部显式写） |
| 关联记录作 dim | specs 写中文名（如「关联物料」）；脚本展开 `localField`+`fieldName=titleField`+`sourceCode`。只写 `link_record_*` → 空数据 |
| 表单名 | 易子串冲突 → 精确名或 `--form-code`。点名多表但 dim/val 只在一张 → 绑有维值的那张，禁 `--form-name A,B` |
| 过滤联动透视 | 透视 `option.title` 固定「表格」；`charts` 可用 componentName 或「表格」 |
| `move` 后 size | 须像素 `width=w*75` `height=h*11` |

## 总进度图 JTotalProgress

**禁止 `add-charts`**（编辑卡死）。`comp/add`+`saveCompToPage`。`nameFields:[]`；`valueFields`=进度值；`option` 仅 `{series:[进度条,轨道条],targetValue}`；`chart`=`{subclass:'JTotalProgress',category:'HorizontalBar'}`。未说本月 → `queryRange=all`。细节 → `charts-special.md` §1。

## 按钮 / 查询面板

- `add-buttons`；布局口语写进 specs（图形/圆角/均分/每行N），脚本解析；`place=top|bottom`
- 已点名：缺打开页 pageId / 业务流程 flowId 才各查一次 → 一条 `add-buttons`。`op` 别名：`创建记录`/`打开列表视图`/`打开页面`+pageId/`打开链接`+url/`调用业务流程`+flowId。外部打开 → `openMode:"2"`。`customPage`/`bizFlow` 须 `{label,value,key}`
- **组合 op 按钮组**（上述 op 混排 ≥2 类，如 5 连按钮组）→ 直抄 `examples/gold-5ops-button-group.md` 换 pageId/flowId/表单名即跑，免拼字段（2026-09-08 实测 1.4s）
- **图形多行高度：** `graphical` 单行 h≥19（默认 20）；总 h≈`20×ceil(n/rowNum)`
- **每行几个（`rowNum`）没点名时默认 4**（不足 4 个按钮按实际个数）。2026-09-17 前的默认是
  「按钮总数」→ 全挤一行；模版首页是 5 钮 / `rowNum=4`（第 5 个换行）——用户报的
  「默认应该一行四个」就是这条。
- **配色没点名时按按钮位置轮换调色板**（`#ED4B82` `#9c27b0` `#64b5f6` `#83c683` `#ff8a66` `#ff9800`），
  不再整组用 op 的同一个默认色。2026-09-17 事故：一组 5 个「打开列表视图」全落成同一个
  `#ED4B82`，用户报「按钮的颜色和图表都一样」。想固定某色 → specs 里给该按钮写 `"color"`。
- **页首要有分区标题**：模版首页在按钮/统计块之间插 `JText`（`w=24 h≈10`）做分节，
  只用图堆出来的盘会「没有层次」。走 `add-ui --comp 文本 --style 大标题,整行`。
- **仅当用户要查询面板**才 `add-filter`；`charts` 须同一 `tableName`；`mode`「包含」=`2`；默认 `place=above`；`saveCompToPage.template` 须 JSON **字符串**。CLI **不接受** `--form-code` / `--form-name` / `--oral`（表单从 charts 推断）。骨架：`{title,place:"above",charts:["折线"],conditions:[{field:"名称",mode:"包含"}]}`
- **已有盘同时加图+查询** → `add-charts`（叠 dim/val）出 `ADDED=` 后立刻 `add-filter --specs-file`，中间禁 Read/grep；≠ `create-dashboard --layout-file`
- **已有面板改匹配/默认值** → `edit-filter`（≠ add-filter、≠ 图筛选）

```bash
$QQY add-buttons API TOKEN --tenant-id TID --app-name APP --page-name PAGE --specs-file BUTTONS.json
$QQY add-filter API TOKEN --tenant-id TID --app-name APP --page-name PAGE --specs-file FILTER.json
$QQY edit-filter API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --field FIELD --mode 等于 --value VAL
# 多面板 --name；清空 --clear-value
```

| 改什么 | 必须同步写 |
|--------|------------|
| 匹配方式 | `conditionFields.condition`+`rule`（`1/EQ`·`2/LIKE`·`5/LLIKE`·`6/RLIKE`）+ `chartData[].queryMode` |
| 默认值 | `chartData[].defVal` + `conditionFields.val`/`fieldValue` |

**跨表** → **每表一次**同表 `add-filter`（串行）；透视匹配 **「表格」**；select「包含」常落成 EQ → 强制 `LIKE`/`condition=2`/`queryMode=2`。同结构盘字面量（产品名+省份名那张）→ `examples/gold-product-province-filter.md`。

> ⚠️ **一条 `filters[]` 里的 `charts` 必须全在同一张表**。想让一页里两张表的图都受筛选 →
> 写**两条** `filters`（每条一张表）。写成一条跨表 → `add-filter` 失败、整张盘记 `FAIL`。
> 2026-09-16 实测踩过。

## 批量建盘失败后怎么办（`build_dashboards.py`）

**它是非破坏的：盘已存在就跳过**（这是为了可断点续跑）。带来的坑是——
**加图失败的盘已经建出来了，重跑会 `OK:skip` 跳过，永远修不好。**

- 失败明细打在 `FAIL:<盘名>` 的**下一行缩进行**里（`charts/<表>: …` 或 `filter: …`）。
  别只看 `OK:done 建 N / 跳过 M / 失败 K` 的汇总行 —— 那行不会告诉你为什么。
- 修好规格后必须 `--recreate <盘名,盘名>` 先删后建，单跑那几张盘。
- 常见三类原因：**透视 `val` 为空** / **`filters` 跨表** / **字段中文名在该表不存在**。

## 文本 / 富文本 / 轮播 / iframe / 时钟

已点名 → `add-ui`（禁手写 config、禁读 `templates-ui`，仅卡住才读）。禁止 `add-charts`。

```bash
$QQY add-ui API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --comp 文本 --text "标题原文" --style 大标题,加粗,居中,整行
$QQY add-ui … --comp 富文本 --html "<p>…</p>" --w 24
$QQY add-ui … --comp 轮播 --form-name FORM --max-count 3
$QQY add-ui … --comp iframe --url URL --w 24
$QQY add-ui … --comp 时钟 --week show
```

| 组件 | 必记 |
|------|------|
| **JCarousel** | raw fields 取 `imgupload`/`photo`/`image`；`maxCount`/`autoplay` 首轮写；已有盘底部 y；半行默认 |
| **JIframe** | 展示 URL=`option.body.url`；`card.title:''`；中间=`max_bottom//2` 并下移下方 |
| **JCurrentTime** | `showWeek:'show'`（字符串）；`format`+`hourlySystem:'24'`；右上角 `x:16 y:0 w:8 h:10`（角标允许 y:0） |

## 工作表右侧统计

```bash
# 完整金样例（个人统计加饼图，按选项字段计数，范围全部）
$QQY add-form-chart API TOKEN --tenant-id TID --app-name APP --form-name FORM \
  --type private --title "按多选框组统计" --comp JPie --dim 多选框组 --val record_count --query-range all
# 省略时默认：comp=JBar、dim=create_time、date-group=3、val=record_count、query-range=month（本月按日柱状）
# ⚠️ 表单统计 --comp 只收 J 码（JPie/JBar/JLine/…）；中文口语（如「饼图」）必被拒 → component-words.md
# ⚠️ 选项类 dim（多选/单选/复选）勿按日期口径预期（date-group 自动忽略）
$QQY delete-form-chart API TOKEN --tenant-id TID --app-name APP --form-name FORM --type private --title "…"
$QQY move-form-chart API TOKEN --tenant-id TID --app-name APP --form-name FORM --type private --to public --title "…"
$QQY copy-form-chart API TOKEN --tenant-id TID --app-name APP --form-name FORM --type public --title "…"
```

标题未命中用 `CAND title=` 立刻重跑。仅复制到仪表盘或需自定义 dim 时才读 `form-stats.md`。

表单统计图 → 仪表盘：扁平化 + `comp/add`+`saveCompToPage`（`form-stats.md`）。

## 复合盘（图 + 按钮/过滤）

**何时用：** 新建盘同时含图 + 按钮/过滤，且按钮夹在两段图之间、或过滤要联动后加的图。  
**何时不用：** 只有图 → 单表新建/加图；只往已有盘加按钮/过滤/图+查询 → 本节「按钮 / 查询面板」（`add-charts` 后立刻 `add-filter`）。

**单表复合（≤60s）：一条 `create-dashboard --tenant-name --app-name --form-name --layout-file`。** 禁止拆成 create-page → add-charts → add-buttons → add-filter 四轮。禁止为对码先读本文：`queryRange`/`dateGroup`/`comp` **口语或码均可**（脚本归一；如 `本月`/`按日`/`折线图`）。失败脚本回滚半成品页，原命令重跑，禁手删再改 JSON。

**点名单表单复合盘零预读零预查（2026-09-08 教训沉淀）：** 凭证 Read → Write layout（照本段骨架换字面量）→ 1 条直跑 ≤60s。禁读金标 `examples/` / memory 应用结构 / 词表；禁预跑 menus/forms/fields——`create-dashboard` 自带表单字段回显 + CAND 行 + 失败自动回滚，字段名直接用用户原词，报错按 CAND 秒级重跑，勿预查。教训实例：同点名单表单盘曾 4 轮预探查（create.md+金标+memory+2 次发现查询）而执行步本身仅 4.3s，预查全浪费。

```json
{
  "charts": [{"comp":"JNumber","title":"KPI","x":0,"y":0,"w":12,"h":17,"dim":[],"val":"record_count"}],
  "buttons": {"rowNum":2,"btnType":"graphical","btnWidth":"divide","place":"bottom",
    "buttons":[{"title":"BTN","op":"创建记录","form":"FORM"}]},
  "afterCharts": [{"comp":"JLine","title":"T","w":24,"h":32,"dim":"create_time","val":"record_count","dateGroup":"3","queryRange":"week"}],
  "filter": {"title":"查询条件","place":"above","charts":["T"],"conditions":[{"field":"FIELD","mode":"包含"}]}
}
```

字面量（表名/按钮文案/标题/字段）**必须按当轮点名替换**。

```bash
$QQY create-dashboard API TOKEN --tenant-name "…" --app-name APP --form-name FORM \
  --name "盘名" --group "分组" --layout-file layout.json
```

自行发挥门户：`--auto --form-name 主表`（KPI×3+柱+折+饼+透视），禁再读本段发明第二套。

**多表**（勿一次 `create-dashboard` 塞多表，易 `FORM_NEED_CHOICE`）：

1. 各写命令带 `--tenant-name --app-name`（禁止先 tenants/apps 填 ID）
2. 点名维值：跳过 fields
3. `create-page`（建议 `--group`）→ `PAGE_ID`
4. 按 `formCode` 拆 specs → **同壳串行** `add-charts --form-code <表>`
5. 同壳或紧随：`add-buttons` → 跨表则每表一次 `add-filter`（**不要**给 add-filter 传 `--form-code`）

布局通则：KPI 行 `w:8`；半行图 `w:12 h:32`；关联维写中文名。  
**只复用编排不复用字面量。**

同轮先建表再加图：侧栏已有表则直接加图；否则 lowapp `fast-create.md`（勿读全文）→ 灌数 → 加图。  
同一句还要建应用/工作表/简流 → **不要读本 skill**，只读 lowapp `fast-full-chain.md`。

## 聚合表 / 工厂

```bash
$QQY save-agg API TOKEN --tenant-id TID --app-name APP --specs-file AGG.json
# {name, kind:single|multi|factory, join:left|inner|all, forms:[表名],
#  links:[{left,right}], headers:[维], calcs:[{name,expr}], filters:[…]}
$QQY delete-agg API TOKEN --tenant-id TID --app-name APP --name "聚合名"
```

`links` 左右 type 须相同且存值相等；按关联记录名称分组用单表。结构 → `aggregation.md`。

## 布局

24 列；`config.size` = `w×75` / `h×11`。一行 3 KPI → 各 w=8 同 y；柱/折半行 w=12 h≈32。同行 w 合计宜=24。JNumber 无对比 h≈17；有环比/同比 h≥30。

## 硬禁令（结构后果）

| 禁令 | 后果 |
|------|------|
| QQY 统计图用 `comp_ops.py add` / UI 组件用 `add-charts` | 白屏或错路径 |
| JTotalProgress 用 `add-charts` | 编辑卡死 |
| JColorGauge 只写 `{title,card}` 或 `colors` 扩成 `type:line` | 白屏 |
| 并行多个 `add` / 未缓存 template 就 `save_page` | 丢组件 |
| `X-Low-App-ID`=pageId / `tenant=2` 顶替点名租户 | 表单空 / 错租户 |
| 表单统计嵌套 config 原样进仪表盘 | 不渲染 |
| 手搓跨表 `JFilterQuery` | 字段芯片不可用 |
| 改图标题写 `card.title=新名` | 双标题 /「tab标题」 |
| JIframe URL 写 `option.url`；时钟 `showWeek` 用布尔 | 不嵌页 / 白屏 |
| `dateGroup` 英文别名 / calc 占位符 | 归组错 / 字面量 |
| 雷达空 `nameFields`；关联 dim 只写 `link_record_*` | 不渲染 |
| JNumber 环比缺 `compareValue:0` / 开对比 h=17 | 无对比行 / 挤裁 |
| Bubble/Heat 预置仅 `type:map` 的 series；地图 `w:24` | 不显示 |
| 点名 dim/val 不存在却私自 `add_widget` | 越权 / 丢数据 |
| 聚合 `links` 左右不同类型或把关联记录对标题/反向字段 | UI 类型不匹配或 `$lookup` 空 |
| PowerShell `ConvertTo-Json` 写 specs | 1 元数组塌成对象 |
| PowerShell 裸 `# $ `` | `#` 当注释、`$` 当变量；参数缺参或截断。值一律双引号 |
| `add-form-chart --comp` 传中文口语（饼图） | 「组件不在 QQY 清单」→ 表单统计 `--comp` **只收 J 码**（JPie），口语表见 component-words.md |

组件口语↔J 码、可用/禁清单（30 统计图 + 7 UI）→ **`component-words.md`**（唯一词表，与 `qqy_chart.py` COMP_ALIAS/QQY_CHARTS 同源）；清单外（JProgress/JTabs/JGrid 等）禁止添加。

## 输出

`http://{前端:3100}/drag/share/{appId}/{pageId}`。未要求链接 → 默认不 clip。
