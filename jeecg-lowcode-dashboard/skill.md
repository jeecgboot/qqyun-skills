---
name: jeecg-lowcode-dashboard
description: >-
  Use when working with 敲敲云/QQY in-app dashboards (lowAppId, dataType=4): charts,
  filters, buttons, rebind/drill/calc/color/label/topN/sort/compare/环比/同比, dual-axis, maps,
  carousel/iframe/clock/text/richtext, 聚合表/聚合工厂, or 租户+应用下的看板/门户/自定义仪表盘.
  硬路由：点名租户+应用的仪表盘/看板/门户/自定义仪表盘 → 本 skill；禁止 jimubi-dashboard /
  jimubi-bigscreen / jeecg-portal。NOT for 无应用归属的积木盘/大屏/EOA 门户.
  同一句还要建应用/工作表/简流 → 不要读本文件，只读 jeecg-lowcode-lowapp/references/fast-full-chain.md.
  **建 ≥5 张盘 → 跑 references/scripts/build_dashboards.py**（声明式 dashboards.json、单进程、非破坏、可断点续跑）；禁止手搓编排器、禁止 subprocess 逐操作起进程、禁止 delete-then-create。
---

# 敲敲云（QQY）仪表盘

应用内盘（DragEngineQqyun，24 列，dataType=4，必须 `lowAppId`）。  
无应用归属 → `jimubi-dashboard` / `jimubi-bigscreen` / `jeecg-portal`。

## 铁律

0. **租户+应用 = 本 skill。** 含租户（名/ID）+ 应用（名/ID），且建/改「仪表盘 / 看板 / 门户 / 自定义仪表盘」→ 只走这里。禁止再问敲敲云还是积木。
1. **§4 命中 → 下一工具=执行（壳命令，不是 Read）。** 凭证：**首条 Bash 前 Read 一次** memory 凭证文件（`reference_jeecgboot_credentials.md`，MEMORY.md 同目录）取 API Base / X-Access-Token，会话内复用。**凭证禁写入 skill 文件/仓库**（2026-09-08 铁律）。禁止开场 `memory_search`/`memory_get` 扫全量、grep 脚本/`--help`/option 键、读 `create.md`/`charts-special`/`gold-specs`。通用「提到过往工作就搜记忆」对本 skill **无效**：点名租户/应用/表后读完本文件立刻跑命令，memory 不是准备。
   **没有对应旗标 ≠ 读全文。** 加图：`--form-name` + `--oral "用户这张图的原句"`。**点名 dim/val/按日/本周可叠 `--dim/--val/--date-group`，也可只写 `--oral`**——解析器已认 维度=…/数值=…、透视 行=…列=…值=…、双轴 左轴…右轴…按…（值=数字/条数 归记录数）；括号里的字段名不会当 dim；缺 dim/val 会**一次性合并报错**，不再挤牙膏多轮。**点名标题仍必须叠 `--title`**（`--oral` 不解析「标题：」，漏叠自动标题=真实统计描述（2026-09-08 规则：dim=名称类→各{表单名词}{数值词}统计，如 名称×销售额计算值/产品表 → 各产品销售额统计；dim=其他→各{dim}{数值词}统计；无 dim→{数值词}统计；本月/本周/近N天等时间词前缀。**禁组件名 JBar/JLine 当标题**，脚本打印 `NOTE=…缺省标题=统计描述`））。圆角/配色/形状/柱宽/点大小等一律进 `--oral`，禁止翻文档或 Write specs。脚本打印 `ORAL_APPLIED=`；`dim=None` 叠旗标短跑，仍禁止 Read。查询面板：Write `FILTER.json` + `add-filter --specs-file`（禁 `--form-name/--oral/--form-code`）。
2. **已点名零探查：** 点名名称直接进写命令 `--tenant-name/--app-name/--page-name/--form-name`（命令内部解析；2026-09-08 起 `--tenant-name` 为 add_auth **全命令**通用，与 `--tenant-id` 二选一，如 `add-charts --tenant-name 北京国炬…`）。禁止为填 ID 先单独 `tenants`/`apps`。点名对得上历史会话 ≠ 开场搜记忆；memory 旧 APP_ID/PAGE_ID/组件配置一律丢弃。**点名 ID 与记忆归属冲突禁反向确认**——如旧记录「仓储系统管理在 TID=1008」而用户本轮说 2：同名应用可共存多租户（2026-09-08 实测：仓储系统管理 = 租户2 北京国炬 APP 2095840106451202050 与 租户1008 新疆兵团 APP 2095784150765826050 各一套），按本轮点名直接跑，`APP_NOT_FOUND`/报错才查才问。**字段口语 = 点名**：`--dim` 直用用户原词——哪怕长得像控件类型名（「多选框组/多选框/下拉框」可能就是字段显示名本身），禁止因「像类型描述」先查 `fields`；报字段不存在才停问。缺打开页 pageId / 业务流程 flowId 才各查一次（pageId 见 §3 `menus`）。
3. **交付即停：** `ADDED=` / `RENAMED=` / `SWITCHED=` / `REBOUND=` / `FILTERED=` / `FILTER_EDITED=` / `CALC_SET=` / `COLORED=` / `LINE_TYPE=` / `LABEL_SET=` / `SHAPE_SET=` / `SIZE_SET=` / `TOP_N=` / `SORTED=` / `COMPARE=` / `DRILLED=` / `REFRESH_SET=` / `SUMMARY_SET=` / `PIVOT_SET=` / `DELETED=` / `FORM_CHART_SET=` / `MOVED=` / `AGG_SAVED=` / `PAGE_ID=` / `SHARE_URL=` 打印完就停（`ROLLBACK_PAGE=`/`ORAL_APPLIED=`/`CAND`/`NOTE=` = 反馈非停 token）。禁止事后 list / `query_page` / 手写 py。未要求不 clip。
4. **点名 dim/val 不存在 → 停问** 近义或是否授权加字段。禁止私自 `add_widget`。
5. **已有图改配置 → 下方高频表原样跑；表外命令 / 字段约束 → `mutate.md`（唯一权威，与脚本同步维护）。** 禁止 grep 脚本 / 手写 py / `comp_ops --set`。表中没有的改法：用户原句附到最接近命令（`--oral`/`--style`）。组件口语/码不确定 → 查 `component-words.md`（禁 grep 脚本）。
6. **最小耗时 / 最短路径（2026-09-08 用户铁令）。** 点名任务免探查、加载即执行。路径已知直用 `$SKILL_REFS`；找不到目录用 `ls ~/.claude/skills`，**禁止 Glob `**` / 大范围 ripgrep 开场搜索**（Windows 下每次各超时 20s，纯浪费）。禁止逐层翻 references——按需表只读**命中**的那一份，一份 SKILL.md 后即执行。一次运行当探查：命令自带 CAND/NOT_FOUND 输出就是信息源——「1 猜 + 1 CAND 重跑」（秒级×2）优于多次只读预探查。

整轮墙钟 = 接口 + 探查往返。开场 memory 计入探查（常见 30–40s），不是准备。接口秒级而整轮分钟级 = 路径违规。

**建 ≥5 张盘 → `references/scripts/build_dashboards.py`**（读声明式 `dashboards.json`，一条命令建完；单进程 + 非破坏 + 断点续跑）。手搓编排器、每操作 `subprocess` 起进程、delete-then-create **三条都禁止**——2026-09-15 实测手搓方案：25 张盘跑 42 分钟，还因 `menus` 抓错列（名称后是 parentId，**drag 的 pageId 在 menuUrl 列**）删盘从未生效，攒出 58 个重复盘。

**判断标准以「轮数」为主：单点 mutate 1 轮、已有盘加图 1 轮、图+查询 2 轮串行、复合盘 1 轮、多表单主链 1 条 Bash；秒数为参考（单点 mutate ≤15–30s、单图旗标加图 ≤30s、复合盘一条 ≤60s、多表单全链 ≤2–3m）**——慢先数轮数；轮数超标查本节禁止项，轮数达标仍久才 `pitfalls-core` 墙钟段。已解析 TID/APP/PAGE 直接用。点名维值跳过 `fields`。互不依赖只读同壳；同页写入串行（失败改参立刻重跑，中间禁 Read/grep）。**口语枚举（本月/按日/包含/柱状图…）进 layout/specs/旗标，脚本归一；禁止为对码读文档或删盘重写 JSON。** 加图（含雷达/四地图/透视/双轴）禁先读 `charts-special`/`gold-specs`（读它确认别名 = 探查；仅白屏/不显示才读）。**单图禁止 Write specs-file**，用 `--oral "原句"` + 点名旗标。勿事后再 mutate。改计算值+标题 = 一条 `set-chart-calc`；改回字段 `--clear --val`。禁止 dump 页 JSON / 手写 py。「不是最新」立刻原命令重跑。追问为何久 → `pitfalls-core` 墙钟段即答，禁再 memory/grep。

## 运行

```bash
SKILL_REFS="$HOME/.claude/skills/jeecg-lowcode-dashboard/references"
# 凭证来源与加载协议 → 铁律 #1（Read 一次 memory 凭证文件，会话内复用）
QQY_API="<API Base>"; QQY_TOKEN="<X-Access-Token>";
PYTHONIOENCODING=utf-8 PYTHONPATH="$SKILL_REFS:$SKILL_REFS/scripts" py "$SKILL_REFS/scripts/qqy_ops.py" "$QQY_API" "$QQY_TOKEN" ...
# 点名场景 = 1 条 Bash 直跑（凭证已载入，见铁律 #1）：
QQY_API="<API Base>"; QQY_TOKEN="<X-Access-Token>"; PYTHONIOENCODING=utf-8 PYTHONPATH="$SKILL_REFS:$SKILL_REFS/scripts" \
  py "$SKILL_REFS/scripts/qqy_ops.py" add-form-chart "$QQY_API" "$QQY_TOKEN" \
  --tenant-name 租户名 --app-name 应用名 --form-name 表单名 \
  --type private --title 标题 --comp JPie --dim 字段原词 --val record_count --query-range all
```

单图：`--form-name` + `--oral "原句"`（结构句 / `ORAL_APPLIED` / 叠旗标规则见铁律 #1）。跨应用数据表（「应用2的产品表」）同条叠 `--form-app-name 应用原词`，禁停问。**禁止**为单图 Write specs、禁止因「没有旗标」读 create.md。查询面板才 Write `FILTER.json`；多图/复合盘才 `--specs-file`/`--layout-file`。禁止 `Set-Content UTF8`、`ConvertTo-Json`、`--specs` 内联。  
头：`X-Access-Token` + `X-Tenant-Id` + `X-Low-App-ID`=**应用 ID**（≠ pageId）。401 才重登。成功后删临时 specs。  
**PowerShell：** 参数值含 `# $ `` 一律双引号（`#` 是注释、`$` 是变量；裸 `#RRGGBB` → `--colors` 缺参）。

## 租户 / 应用（§3）

| 用户给了什么 | 做法 |
|--------------|------|
| 本轮数字 tenant-id / app-id | 直接用 |
| 只给租户名 / 应用名 | 写命令加 `--tenant-name` / `--app-name`（`--tenant-id`/`--tenant-name` 二选一——add_auth 全命令支持按名解析，2026-09-08；0 条自动去「租户/公司」后缀）。禁止为填 ID 先单独 `tenants`/`apps`。memory 旧 ID 丢弃。禁止用默认 `tenant=2` 冒充 |
| 无 ID 无名称 | 停下问，禁止猜 `1`/`2`/`1000` |
| 写命令报 `APP_NOT_FOUND` / `TENANT_NOT_UNIQUE` | 才单独 `tenants`/`apps` 一次 |

**例外：`create-page` 只收 `--tenant-id`/`--tenant-name` + `--app-id`**（不解析应用名；见 create.md「空白盘」段）。

点名看板优先 `--page-name`（QQY，mutate 命令自己解析，不必先 `menus`）。未给看板名且应用内仅一张盘 → 命令自动选用。多盘才 `menus` 一次。`switch-type` / `add-drill` / `comp_ops edit` 要 PAGE_ID：缺则 `menus` 一次（`drag` 行 menuUrl；**禁止** `qqy_ops pages`）——**取 id 与改图同壳串行一条 Bash**（awk 抓 menuUrl 列喂给 PAGE_ID，禁拆两轮模型往返；2026-09-09 AI903 实测）。侧栏找不到刚建的盘 → 按应用名重解析，禁止在旧 ID 上改分组。

## 已有图改配置（高频；先看这里）

会话已有 TID/APP/PAGE 时 **下一工具就是对应命令**。完整 CLI / 字段约束 → **`mutate.md`**（表中命令已够则不必读）。

| 改什么 | 命令 | 停 |
|--------|------|-----|
| 色 / 渐变 / 折线类型 / 词云形状 / 数值·百分比标签 / 其余样式 | `set-chart-color`（可同条 `--color/--colors/--gradient/--line-type/--shape/--label-show/--percent-label/--style`；无专用旗标的样式整段 `--style`） | `COLORED=` `LINE_TYPE=` `SHAPE_SET=` `LABEL_SET=` `SIZE_SET=` |
| 前 N / 排序 | `set-chart-sort --top-n --field --order`（聚合/自动金额公式`$`开头值列排序自动留空 name——内部键/公式串前端不认，写 name 整图白屏，见 mutate.md「前N/排序」⚠️） | `TOP_N=` `SORTED=` |
| 图内筛选 | `set-chart-filter`（≠ `add-filter`） | `FILTERED=` |
| 计算值（无 calc 也升级；可同条改标题） | `set-chart-calc --formula 求和` [`--title`] | `CALC_SET=` `RENAMED=` |
| 环比 / 同比 / 与上月相比 / 升红降绿 | `set-chart-compare --compare --trend` | `COMPARE=` |
| 维/值/表/双轴 | `rebind-chart` | `REBOUND=` |
| 换类型（柱↔折） | `comp_ops switch-type --to` 接用户原词（折线图/柱状图）；禁 JSmoothLine/JArea | `SWITCHED=` |
| 饼图 设为环形 / 标签位置（中心等） | `comp_ops edit --name 饼图名 --set option.isRadius=true --set option.pieLabelPosition=center`（**JPie 自带键，禁 switch-type 换 JRing**；内外径 option.innerRadius/outRadius） | `共编辑 N 个组件` |
| JPie 数值文字颜色/字号/字重 | `comp_ops edit --name 饼图名 --set option.series[0].label.color=#1890ff --set option.series[0].label.fontSize=15 --set option.series[0].label.fontWeight=lighter`（**数值文字颜色禁走 `set-chart-color --color/--colors`**——饼图分流只写 customColor 扇区色板，改不到文字；`--style` 词表不解析字号/细体，字重 `lighter`=细体） | `共编辑 N 个组件` |
| 图标题 | `rename-chart --name OLD --title NEW`（同名多图 `CHART_AMBIGUOUS` → 去 `--name` 只给 `--match-dim` 维度内部id，禁与 `--name` 同给） | `RENAMED=` |
| 图标题样式（标题颜色/加粗/字号/上下左右边距） | `comp_ops edit --name 标题原词 --set option.title.textStyle.color=#FFD700 --set option.title.textStyle.fontWeight=bold --set option.title.textStyle.fontSize=20 --set option.title.top=10 --set option.title.left=15`（**`set-chart-color --style` 词表不解析标题词**；PAGE_ID+非租户2 预置头 → `mutate.md`「图标题样式」） | `共编辑 N 个组件` |
| 数值单位（后缀文本/小数位/数量级万） | `comp_ops edit --name 图名 --set compStyleConfig.showUnit.unit=元 --set compStyleConfig.showUnit.numberLevel=4 --set compStyleConfig.showUnit.decimal=2 --set compStyleConfig.showUnit.position=suffix`（**权威键位=compStyleConfig.showUnit，option 层同键前端不读**——2026-09-08 AI903 实测；numberLevel 字符串码 "4"=万；position suffix/prefix；非租户2 预置头 → `mutate.md`「数值单位设置」） | `共编辑 N 个组件` |
| 地图 视觉映射：开启 / 最小最大值 / 区域配色 | 区域配色走 `set-chart-color --comp 气泡地图 --oral` 用户原句——**只解析配色**（色词自动转 hex：红黄蓝绿→`#FF4D4F,#FFD700,#1890FF,#52C41A`，落盘 MAP_INRANGE，回执 `ORAL_APPLIED=colors`）；「开启/最小值/最大值」口语不进词表 → `comp_ops edit --set option.visualMap.show=true --set option.visualMap.min=0 --set option.visualMap.max=10000`（键=标准 echarts 全在 option.visualMap；PAGE_ID+非租户2 预置头 → `mutate.md`「地图视觉映射」） | `COLORED=` / `共编辑 N 个组件` |
| 热力地图(JHeatMap) 点大小/点模糊大小/最大透明度 | `comp_ops edit --name 图名 --set commonOption.heat.pointSize=20 --set commonOption.heat.blurSize=25 --set commonOption.heat.maxOpacity=10`（**禁 `set-chart-color --style`**——词表把「点大小」误映射 symbolSize 死键、「点模糊大小/最大透明度」不解析（2026-09-09 AI903 实测仅 `ORAL_APPLIED=symbolSize`）；权威键 `commonOption.heat` 见 charts-special §3；PAGE_ID+非租户2 预置头 → `mutate.md`「热力地图热力配置」） | `共编辑 N 个组件` |
| 仪表盘(JGauge/JColorGauge) 刻度线/刻度长度/刻度字号/分割线/指标字号 | `comp_ops edit --name 图名 --set option.series[0].axisTick.show=false --set option.series[0].axisTick.length=25 --set option.series[0].axisLabel.fontSize=15 --set option.series[0].detail.fontSize=25 --set option.series[0].axisTick.lineStyle.color=#ffd700 --set option.series[0].splitLine.length=15 --set option.series[0].splitLine.lineStyle.color=#ff0000`（键=标准 echarts gauge 全在 series[0]：刻度线=axisTick/刻度数字=axisLabel/指标=detail/分割线=splitLine；`--style` 词表不解析 gauge 词禁走它；**JAntvGauge 无此键勿改**；键位与最短路径 → `mutate.md`「仪表盘刻度样式」） | `共编辑 N 个组件` |
| 页改名 | `rename-page` | `RENAMED=` |
| 钻取 | `add-drill`（维名中文即可，可省略 mapping） | `DRILLED=` |
| 定时刷新 | `set-chart-refresh --minutes` 口语原样 | `REFRESH_SET=` |
| 打开总计 / 全部字段 / 汇总平均 | `set-chart-summary --field all --total-type 平均` | `SUMMARY_SET=` |
| 透视前 N 行/列、关合计 | `set-pivot --row-n 10 --col-n 5 --line-total 关 --column-total 关` | `PIVOT_SET=` |
| 计算值改回字段 | `set-chart-calc --clear --val` 字段原词 | `CALC_SET=` |
| 删盘 | `delete-page --page-name` | `DELETED=` |
| 工作表右侧统计改范围 | `set-form-chart --query-range` 口语原样 | `FORM_CHART_SET=` |
| 右侧统计转公共/转个人（个人统计↔公共） | `move-form-chart --type private --to public --title 原词`（同名全改；未中 → 输出 CAND 行取真实标题立刻重跑，同进程 list+updateType） | `MOVED=` |

`--name` 匹配 componentName **或** `option.title.text`。mutate 全量示例 → `mutate.md`；典型如下（add-drill/refresh/summary/pivot/delete-page 等 → mutate.md）：

```bash
QQY_API="<API Base>"; QQY_TOKEN="<X-Access-Token>";
QQY="py $SKILL_REFS/scripts/qqy_ops.py"
COMP="py $SKILL_REFS/scripts/comp_ops.py"
$QQY set-chart-color "$QQY_API" "$QQY_TOKEN" --tenant-id TID --app-name APP --page-name PAGE --comp 柱状图 --color 金色
$QQY add-charts "$QQY_API" "$QQY_TOKEN" --tenant-id TID --app-name APP --form-name FORM --oral "用户这张图的原句" --dim DIM --val VAL
$QQY add-filter "$QQY_API" "$QQY_TOKEN" --tenant-id TID --app-name APP --page-name PAGE --specs-file FILTER.json
$QQY add-ui "$QQY_API" "$QQY_TOKEN" --tenant-id TID --app-name APP --page-name PAGE --comp 文本 --text "标题原文" --style 大标题,加粗,居中,整行
$COMP switch-type "$QQY_API" "$QQY_TOKEN" PAGE_ID --name CHART --to 折线图
# FILTER.json {title:"查询条件",place:"above",charts:["折线"],conditions:[{field:"名称",mode:"包含"}]}
# layout.json 复合盘键位骨架（单表单复合盘唯一需写死的 JSON；值按本轮替换，禁为此读 create.md）：
#   {"charts":[{"comp":"JNumber","title":"KPI","x":0,"y":0,"w":12,"h":17,"dim":[],"val":"record_count"}],
#    "buttons":{"rowNum":2,"btnType":"graphical","btnWidth":"divide","place":"bottom","buttons":[{"title":"BTN","op":"创建记录","form":"FORM"}]},
#    "afterCharts":[{"comp":"JLine","title":"T","w":24,"h":32,"dim":"create_time","val":"record_count","dateGroup":"3","queryRange":"week"}],
#    "filter":{"title":"查询条件","place":"above","charts":["T"],"conditions":[{"field":"FIELD","mode":"包含"}]}}
# 多图 = 同数组加元素；位置 = x/y/w/h。省略 x/y = 从上到下顺序排，【不会】自动左右并排；并排必须显式 x/y（2026-09-08：省略坐标 → 4 组件全 x=0 单列堆叠，删盘重建才补上）
# 数字卡 JNumber 禁叠 "calc":"求和"+数值 val——表含 money 字段（如单价）时引擎自动拼出 $f-2$*$f-4$+$f-1$ 垃圾公式（2026-09-08 实测）；总数卡 val=record_count，合计卡只绑字段、建后 set-chart-calc --formula 求和 升级
# add-filter 禁 --form-name/--oral/--form-code；表单从 charts 推断
```

## §4 场景路由（命中即执行）

| 用户意图 | 立刻做什么 | 卡住再读 |
|----------|------------|----------|
| 同一句还要建应用/工作表/简流 | **禁止读本 SKILL**；只读 lowapp `fast-full-chain.md` | — |
| 已有图改色/标签/样式/类型/维绑/筛选/计算值/排序/环比/钻取/标题/刷新/总计/透视合计 | 上方命令表直接跑（不必先读 `mutate.md`） | 表中没有的改法把原句 `--oral`/`--style` 附到最接近命令；禁因缺旗标读全文 |
| 租户+应用下建门户/自定义仪表盘/看板 | 同新建空白盘/复合盘；`--tenant-name --app-name` 直接写，禁先 tenants/apps | `create.md` |
| 自行发挥门户 | `create-dashboard --auto --form-name 主表 --name 门户名 --group …`（禁先读 create.md、禁发明第二套布局） | `create.md` |
| 新建空白盘 | `create-page --name 盘名 --group 分组`（租户按名/ID 均可，**应用必 `--app-id`**，不解析应用名） | `create.md` |
| 页改名 / 移组 / 删盘 | `rename-page` / `group-menu --group` / `delete-page` | `mutate.md` |
| 移除盘上单个组件（排行榜/某图/文本等，非删整盘） | `comp_ops delete`（`qqy_ops` 无删组件命令）：先 `comp_ops list` 拿真实 componentName（口语「排行榜」≠ 名「销售额排行榜」），再 `delete --name`（`--type`/`--id` 也可，含 JGroup 组内）；非租户2 页面预置租户头 + pageId 用 `menus` 现取 | `mutate.md`「删组件」（2026-09-08 实测沉淀） |
| 单表新建盘 | 多图才 Write specs；**单图用旗标** `--comp/--dim/--val` → `create-dashboard`（金额类省略 calc；按日 `--date-group 按日`） | `create.md` |
| 已有盘加图 | **下一工具=执行**（≤30s）：`add-charts --app-name --form-name FORM --oral "用户这张图的整句"`。**点名 dim/val 叠 `--dim/--val`（及 `--date-group/--query-range`）、点名标题叠 `--title`（`--oral` 不解析「标题：」；漏叠自动标题=统计描述，规则见铁律1）；没有样式旗标才进 `--oral`。禁止 Read / 禁止 Write specs / 禁开场 `memory_search`。** `dim=None` 叠旗标短跑。点名多表 → `--form-name` 写有点名维值的那张。数据表在别的应用（如「应用2的产品表」）→ 同条叠 `--form-app-name 应用原词`，**禁止因表单不在本应用而停问**。数值口语「X计算值」（销售额计算值等）= 金额口径：金额字段省略 `--calc`，引擎自动 售价×销量（lessons.md §5；create.md 金额类省略 calc）——字段缺失 ≠ 询问，仅表上无金额/数量两字段才停问。含 `# $ `` 的值加引号。`COMP_UNKNOWN=` / 口语不在词表 → `component-words.md`（唯一词表）选码或近义词重跑 | **—**；仅白屏才 `charts-special` |
| 已有盘加图+查询条件 | 串行：`add-charts --app-name`（叠 dim/val）→ Write `FILTER.json` → `add-filter --specs-file`。中间禁 Read/grep。**已有盘 ≠ `create-dashboard --layout-file`** | `create.md` 仅 JSON 骨架卡住 |
| 复合盘（图+按钮/过滤） | **Write layout（口语可）+ 一条** `create-dashboard --tenant-name --app-name --form-name --name 盘名 --group 分组 --layout-file`（**`--name`/`--group` 必填**——2026-09-08 实测漏掉 → usage 报错整条白跑）（`{charts,buttons,afterCharts,filter}`；`queryRange`/`dateGroup`/`comp` 口语或码）。**点名单表单复合盘 = 凭证 Read → Write layout → 直跑，中间零预读零预查**（骨架键位 = 上方 mutate 示例 `# layout.json` 行，直接写死换字面量）：禁读 create.md/金标 examples/memory 应用结构、禁预跑 menus/forms/fields——create-dashboard 自带表单字段回显 + CAND + 失败自动回滚。教训（2026-09-08 实测）：同点名单表单盘曾 4 轮预探查（读 create.md+金标+memory+2 次发现查询），执行步本身仅 4.3s | 按钮 op / 过滤 mode 卡住才 `create.md` |
| 多表单(≥2)新建复合盘 | **直接 `multiform-template.md`**：发现捆绑一条 → 并行 Write specs → 主链单壳（create-page + 按 formCode 串行 add-charts + add-buttons + 每表一次 add-filter），墙钟目标 ≤2–3m。禁止拆多轮、禁止整链重放 | JSON 骨架卡住才 `create.md` / `gold-specs.md` |
| 建/改聚合表/工厂；**改聚合公式或过滤**；用聚合加图 | 建/改：`save-agg <API> <TOKEN> --tenant-id/--tenant-name --app-name/--app-id --name 聚合名 --specs-file`（**save-agg 不收 `--form-name`**——那是聚合加图 `add-charts` 的选表旗标；参数错 → usage 输出即参表）。聚合加图 **dim 只认聚合输出本地列/行表头原词**，禁传关联源表单里的字段名——脚本会回退落 LINK_DIM 致维度不渲染（2026-09-08 实测）。**改公式/过滤先 1 条查询拿原 id + filterCondition**：specs 全量给 + calcs 带 `"id"`（不带则生成新 uuid，而图表公式列字段名 = 名+calcId 前 5 位 → 已绑公式列的图断链）；filters 全量替换，中文 op（大于/包含…）脚本编译 rule 码。查+改细则 → aggregation.md「改已有聚合」 | `aggregation.md`「改已有聚合（公式/过滤，最短路径）」「绑图」 |
| 加按钮 / 查询面板 / 改已有面板 | `add-buttons --specs-file` / `add-filter --specs-file` / `edit-filter --field --mode`。`add-filter` 禁 `--form-name/--oral/--form-code`。`调用业务流程` = 绑**已有**流程，只查 flowId（金标 §1 探测），**禁止为绑定整载 jeecg-bpmn skill** | **组合 op 按钮组**（创建记录/列表/页面/链接/业务流程混排 ≥2 类）→ 先抄 `examples/gold-5ops-button-group.md`；其余 `create.md` 仅 JSON 骨架卡住（图形按钮 `btnType=graphical`、h≥19，多行 h≈20×行数） |
| 跨表查询面板 | 每表一次 `add-filter`；透视匹配「表格」 | 同类字面量才 `examples/gold-product-province-filter.md` |
| 文本 / 富文本 / 轮播 / iframe / 时钟 | `add-ui --comp` 接用户原词；大标题/加粗/居中/整行进 `--style`；禁读 `templates-ui` | `templates-ui.md` 仅卡住 |
| 工作表右侧统计 | `add-form-chart --type private --title 标题 --comp JPie --dim 字段 --val record_count --query-range all`（**`--comp` 只收 J 码**：JPie/JBar/JLine…；选项类 dim 勿传 `--date-group`；默认=本月按日柱状；**点名即 1 条 Bash 直跑**——`--dim` 用字段显示名原词，0 探查）；改范围 `set-form-chart`；**转公共/转个人 `move-form-chart`**（`--type` 源 tab、`--to` 目标 tab、`--title` 原词，同名全改） | `form-stats.md`（仅复制到盘/失败） |
| 总进度图 JTotalProgress | `comp/add`+`saveCompToPage`；**禁 add-charts** | `charts-special` §1 |
| 同轮先建表再加图 | 侧栏已有表则直接加图；否则 lowapp `fast-create` → 灌数 → 加图 | `fast-create.md`「禁止」节 |
| 点名 mock/灌数 | **灌数走 lowapp**；本 skill 只绑图 | — |
| 点名全组件/所有统计图 | 点名表单 → **直接** `gen_qqy_all_comps.py`（脚本内置推荐 dim/val，禁先确认字段） | 仅失败 → `charts-special` §5 |
| 未点名表单/字段；点名 dim/val 不存在 | 四步询问 / 铁律 #4 | `form-field-inquiry.md` |
| 白屏/卡死/报错 / 墙钟过长 | — | `pitfalls-core.md` |

**易混：** 图内筛选 `set-chart-filter` ≠ 查询面板 `add-filter`。单图 Write specs / 因缺旗标读 create.md / `add-filter` 猜 `--oral` = 路径违规。口语不在旗标表里 = `--oral` 原句，≠ grep（oral 结构句与 `ORAL_APPLIED` 规则见铁律 #1）。

沉淀新能力：只加 **§4 一行 + `create.md` 或 `mutate.md` 一处**。实例字面量进 `examples/`，勿写进通则。历史文档不设禁读（`lessons.md` / `qqy-guide*.md` / `cli-cheatsheet.md` 保留为兼容参考，见下方按需表）。

## 按需加载（默认不读）

| 文件 | 何时读 |
|------|--------|
| `mutate.md` | 已有图改配置且表中命令不够 / 卡住（点名改色/加图 **禁止**读） |
| `create.md` | 仅新建复合盘 layout / FILTER.json 骨架卡住 / 硬禁令。**点名单图 / 已有盘图+查询禁止读** |
| `charts-special.md` | 仅白屏/不显示 / JT / 钻取卡住。加图确认别名 **禁止**读 |
| `gold-specs.md` | 仅缺多图 JSON 骨架。单图禁止读 |
| `aggregation.md` | 聚合表/工厂结构 |
| `templates-ui.md` | 仅 `add-ui` 卡住 |
| `form-stats.md` | 复制到盘 / 右侧统计失败需扁平化 |
| `form-field-inquiry.md` | 未点名表单字段；或点名 dim/val 不存在 |
| `component-words.md` | 组件口语↔J 码 / 可用清单确认（`COMP_UNKNOWN=` / 表单统计 J 码）；禁 grep 脚本 |
| `pitfalls-core.md` | 白屏/卡死/报错/墙钟过长 |
| `examples/gold-product-province-filter.md` | 仅盘结构与该金标同类时 |
| `examples/gold-5ops-button-group.md` | 已有盘加按钮组且 op 混排 ≥2 类时，字面量照抄换 pageId/flowId/表单名即跑（含发现一条 Bash + 直跑命令）；单类按钮读 create.md 即可 |
| `multiform-template.md` | ≥2 表单新建复合盘编排（占位符通用版）；单表单盘 / 金标同类 勿读 |
| `examples/gold-warehouse-5table-dashboard.md` | 仅盘结构与仓储 5 表单金标同类时（字面量照抄改名即跑） |
| `examples/gold-singleform-button-portal.md` | 仅**单表单**「数字卡行+柱/折并排+图形按钮组+afterChart 折线+查询条件联动」盘与该金标同类时（字面量照抄换租户/表单即跑，坐标全表含 x/y） |
| lowapp `fast-create.md` / `fast-full-chain.md` | 同句建表 / 全链路 |
| `lessons.md` | 教训总索引（现象→章节/命令 §4-x）；常规路径卡住或对证历史经验时对照 |
| `qqy-guide.md` | 文档导航（各需求→打开哪份）；定位不到时看 |
| `qqy-guide-archive.md` | 旧全量指南：未点名交互细节（轮播/iframe/时钟、按钮 operationType）；组件清单已迁 component-words |
| `cli-cheatsheet.md` | CLI 命令对照速查（与 mutate/create 同源冗余，卡住对照） |
| `form-field-inquiry-full.md` | 未点名表单/字段询问旧全文（封存；手写 config 段已作废删除） |

脚本：`qqy_ops.py`、`comp_ops.py`、`gen_qqy_all_comps.py`、`linkage_ops.py`、`link_ops.py`、`page_ops.py`（模块 `qqy_chart.py`=唯一词表源、`bi_utils.py`=请求封装，**禁读**；`test_chart_mutate.py` 为开发测试勿交付）。禁止为确认 CLI 打开脚本。
