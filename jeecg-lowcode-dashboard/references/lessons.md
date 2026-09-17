# 敲敲云仪表盘历史教训（短指针）

> 教训索引（已放开）：常规路径卡住 / 对证历史经验时对照本文件；不改行为，只记录「哪类坑 → 看哪个文件」。现行权威：`SKILL.md` 铁律 + §4；症状 → `pitfalls-core.md`。  
> 长叙事已压缩；细节以 SKILL / charts-special / templates-ui 为准。

## 索引

| 主题 | 节 |
|------|-----|
| 通读/开场 memory / 结果对仍久 | §1–2/§7–8/§23–25/§34–35/§37–39/§41–42/§44/§46/§49–50/§56–60 |
| 跨表查询 | §40–41；`gold-product-province-filter.md` |
| 改标题 / tab标题 | §43；mutate.md |
| 柱改折 / 折改柱 / switch-type / 基础柱形图 | §44/§59；mutate.md `switch-type --to JBar|JLine` |
| 钻取 / 点柱过滤自己 | §46；SKILL 高频表 `add-drill` |
| 改计算值公式 / 平均×求和 | §47；mutate.md `set-chart-calc` |
| 改柱/线色 / 金色 / 柱体渐变 | §48；mutate.md `set-chart-color --gradient` |
| 前 N 项 / 按字段降序 | §58；mutate.md `set-chart-sort` |
| 折线类型改成曲线/面积 / 改红+曲线 / 改黄+面积 | §56；mutate.md `set-chart-color --line-type` |
| 已有饼改色+数值标签 / 百分比标签 | §57；mutate.md `set-chart-color --colors … --label-show` |
| 换数据源 / 跨应用换表 | §49；mutate.md `rebind-chart --form-app-name` |
| 双轴改右轴 / assistY | §50；mutate.md `rebind-chart --assist-y/--assist-type` |
| 租户+应用误走积木/系统门户 | §51；铁律 #0 |
| 口语标题≠componentName / 误判找不到 | §52；mutate.md `--name` 命中 |
| 自行发挥多表门户墙钟虚高 | §53；§4/create.md「复合盘」 |
| 全场景墙钟虚高（点名仍探查/多轮往返） | §54；铁律 #6 |
| 聚合关联类型不匹配 / 行表头非关联字段 | §55；`aggregation.md` |
| 聚合工厂建后连接配置不显示 / 缺行 id 手修 | `aggregation.md`「工厂存储结构」；已修入 qqy_ops.py save-agg（自动 row_n+children） |
| 聚合图 dim 落 LINK_DIM 不渲染 / 新图颜色 oral 不收 | `aggregation.md`「绑图」；SKILL §4 聚合行 |
| JColorGauge / 雷达 / 环比 | §27–30；`charts-special` §0 |
| 私自加字段 | §33 |
| 地图族 | §31–35 |
| 按钮高度 / 样式 | §9–10/§36 |
| 表单统计 / 统计复制到盘 | §12–17b/§64；form-stats.md「复制到仪表盘」 |
| 单表新建金标 / calc / y | §20–22；`gold-specs.md` |
| 单表单按钮门户复合盘 / 并排漏 x/y | §61；`examples/gold-singleform-button-portal.md`；create.md「布局」⚠️ |
| 查询面板顶置 / 密排盘组件级联位移 | `mutate.md`「顶置 / 插入级联」；`comp_ops move` |
| 金标同类盘加查询面板仍预读 4 轮（memory/grep/预查 list） | `gold-product-province-filter.md`「增量场景」；pitfalls-core 墙钟 |
| comp_ops 改图缺 pageId（menus+edit 拆两轮往返） | §67；SKILL §3「租户/应用」 |

## §1–22（建盘 / 加图 / 表单统计 / 按钮过滤）

| 节 | 现象 | 见 |
|----|------|-----|
| 1 | 单表新建拆多轮 shell、通读多 skill | create.md；一条 `create-dashboard` |
| 2 | 计算值图仍 grep/改脚本 | create.md / charts-special `calc`；勿探查 |
| 3 | 透视+双轴仍改脚本 | `assistY`/`assistType`；一条 `add-charts` |
| 4 | 跨应用加图头未切 | `--form-app-name` |
| 5 | 销售额绑成单价 | 省略 calc 自动售价×销量 |
| 6–8 | JTotalProgress 卡死 / 仍挖源码 | 禁 `add-charts`；charts-special §1 |
| 9 | 加按钮通读 guide | create.md「按钮 / 查询面板」 `add-buttons` |
| 10 | 图形样式错 / h=10 裁字 | `btnType=graphical`；h≥19 |
| 11 | 折线+过滤拆多轮 | `add-charts`→`add-filter` |
| 12–16 | 表单统计拆多轮 / 中文坏 | create.md「工作表右侧统计」 单命令；禁管道 heredoc |
| 17/17b | 转公共仍读他 skill/`form-stats` | 只读 create.md「工作表右侧统计」 |
| 18 | 页改名拆多轮 | `rename-page` |
| 19 | 全组件行宽未自检 | 行合计=24 |
| 20–22 | KPI 宽/日归组/calc 占位符 | `w:8`；`dateGroup:"3"`；禁 `$money_xxx$` |

## §23–36（墙钟类 + 结构类，跨表查询/复合盘为主）

| 节 | 现象 | 见 |
|----|------|-----|
| 23 | 空白盘前探查 30s+ | 铁律；有 ID 直接建 |
| 24 | 多折线先问+配色二次补丁 | 首轮 `colors`；禁 ask |
| 25 | 换普通图当新能力+百分比 patch | 新建换 `comp`；`percentLabel` 首轮 |
| 26 | 复合盘问技能域 + ConvertTo-Json | create.md「复合盘」；`py -c json.dump` |
| 27 | JColorGauge 白屏 + 错租户 | `charts-special` §0；`tenants --name` |
| 28 | 雷达空 dim 不渲染 | `charts-special` §0 |
| 29 | 环比无「与上月相比」 | `charts-special` §0：`compareValue:0`；h≥30 |
| 30 | 红升绿降写成 `"1"` | `trendType:"2"` |
| 29b | 气泡图已点名仍探查 | `JBubble` dim/val/grp |
| 31 | 建表未归组 + 加图 y:0 | lowapp 默认第一组；禁 y:0 |
| 32 | 气泡地图不显示 / options 漏表 | 勿预置 series；menus 兜底 |
| 33 | 无「城市」却私自加字段 | 铁律 #4；先问近义 |
| 34 | 已点名热力仍读 guide | create.md / charts-special JHeatMap+colors |
| 35 | 柱状地图事后 patch 标签 | 首轮 `scatterLabelShow` |
| 36 | 图形按钮多行裁字 | h≈20×可视行数 |

## §37–64（短指针）

| 节 | 现象 | 见 |
|----|------|-----|
| 37 | 轮播通读 SKILL | create.md「文本 / 轮播」节；`templates-ui` |
| 38 | iframe 问技能域 | create.md「文本」节；`option.body.url` |
| 39 | 时钟通读 | create.md「文本」节；角标可 y:0 |
| 40 | 跨表手合并失败 | 两次 `add-filter`；`gold-product-province-filter` |
| 41 | 跨表结果对仍久 | 铁律；禁 list 挖 title |
| 42 | 加按钮仍开场 memory | create.md「按钮 / 查询面板」 |
| 43 | 改标题 +「tab标题」 | mutate.md：`card.title=''` |
| 44 | 柱改折仍久 | mutate.md `switch-type` |
| 45 | 图加筛选误走 `add-filter` + 探查过久 | mutate.md `set-chart-filter` |
| 46 | 加钻取 → memory+grep+失败 CLI（接口秒级、整轮~1m） | mutate.md `add-drill`；`charts-special` §4 |
| 47 | 改计算值 → 手写临时脚本 + 再查 tenants | mutate.md `set-chart-calc` |
| 48 | 改柱色 → 通读+PS `--set` JSON 炸 + 手写 py -c；柱体渐变把第二色塞进 `color1` → 面板只一色、无渐变 | mutate.md `set-chart-color --gradient --colors A,B`（每色一条） |
| 49 | 跨应用换表 → 手写 py -c（接口~0.5s、整轮~1m） | mutate.md `rebind-chart --form-app-name` |
| 50 | 双轴改右轴 → memory+通读+手写 py -c（用户追问为何久） | mutate.md `rebind-chart --assist-y/--assist-type` |
| 51 | 租户+应用下「门户/自定义仪表盘」误走 `jeecg-portal`/`jimubi-dashboard` | 铁律 #0；§4 首行；description 硬路由 |
| 52 | 「产品信息」柱图 → list 无同名 / `REBOUND=本周记录数` 被当成绑错；用户追问为何久+为何找不到 | mutate.md：`--name` 可匹配 `option.title.text`；`REBOUND=` 打 componentName；接口~1.5s，久=探查 |
| 53 | 自行发挥多表门户 → 开场 memory + forms 参数失败空等 + `--help`；接口~20s 整轮 2–3m | §4 自行发挥；create.md「复合盘」；墙钟 ≤1m |
| 54 | 点名多表复合盘仍 memory + 全表 fields + 多轮拆查 | pitfalls-core 墙钟段；`pitfalls-core` |
| 55 | 聚合「关联仓库↔仓库名称」类型不匹配；行表头写未参与关联的「关联物料」；改双向回指则 `$lookup` 空 | `aggregation.md`：多表等值连接；按关联记录名称分组用单表 |
| 56 | 已有折线改红+曲线 / 改黄+面积 → 开场 memory + grep `lineType`/`面积` 确认别名 + 只报 shell 当整轮（接口秒级、用户追问为何久） | mutate.md：`--color`+`--line-type 曲线|面积`；禁 `switch-type JSmoothLine/JArea`；pitfalls-core 墙钟段J |
| 57 | 已有饼「三色+数值标签」→ 开场 memory + 通读 SKILL + grep `percentLabel` + 写一次性脚本二次 save（接口~7s、用户追问为何久） | mutate.md：`--colors`+`--label-show` 同条；禁手写 py / 二次 save；pitfalls-core 墙钟段H/J |
| 58 | 已有图「只显示前 8 项，按库存数量降序」→ grep `dataFilterNum`/`sorts` + 手写一次性脚本（接口 2.4s、整轮~1m；用户追问为何久） | mutate.md `set-chart-sort --top-n --field --order`；禁手写 py / `comp_ops --set`；pitfalls-core 墙钟段J |
| 59 | 已有图改「基础柱形图」→ 开场 memory + grep switch-type + 误跑 `qqy_ops pages`（无此子命令）再 `menus` 才 `switch-type`（接口~2.7s、用户追问为何久） | mutate.md `switch-type --to JBar`；缺 pageId=`menus`（无 pages）；pitfalls-core 墙钟段J |
| 60 | 已有盘加图：口语图类型 `COMP_UNKNOWN` 后 grep 别名；PS 裸 `#`/`$` 当元字符；样式无现成旗标 → `query_page`+手写 py（接口秒级、整轮数分钟） | 别名只在脚本；`--oral`/`--style` 收口无旗标样式；元字符一律引号；`*_UNKNOWN=` 只改该旗标重跑；`ADDED=` 禁 dump 页 |
| 61 | 复合盘并排组件省略 x/y → 4 组件全 x=0 单列竖排（自动排=顺序追加、不左右填空），发现后删盘重建整轮返工（接口~10s、整轮数分钟；用户追问为何久） | SKILL.md layout 骨架注释「省略 x/y=顺序排、不并排；并排必须显式 x/y」；create.md「布局」行 ⚠️；金标 `gold-singleform-button-portal.md`（坐标全表 + 字面量） |
| 62 | 聚合表加图 `--dim 仓库名称`（源表单字段）→ 回退落 `LINK_DIM`、维度渲染不出字段；oral「浅紫」未应用（`ORAL_APPLIED` 只 comp/dim/val）、`itemStyle.color` 空 → 用户手修 | `aggregation.md`「绑图」：dim=聚合输出本地列原词（`fieldName==localField` + `titleField` 显示）；新图配色 → 加图后 `set-chart-color`（浅紫 `#673bb7`） |
| 63 | 聚合表柱图 `set-chart-sort`（按公式列降序+前5）→ 落盘 `sorts.name=库存合计69c48` 型 calcId 键 → **整图白屏**，设计器手工保存（name 清空）才恢复；色与前 N 本身写对了 | `set-chart-sort` 已对聚合表 value 列自动留空 name 只写 type/前 N（2026-09-08 脚本修复）；detail 见 `aggregation.md`「绑图」排序段 |
| 64 | 表单统计饼图复制到盘：raw 链首轮对响应假设错（`result` 当 dict 实为 list / 找 `pageCompId` 实为 `result.id` / `code=200` 当失败退出）→ 已落库坏项后多轮返工+清理（接口秒级、整轮分钟级，用户追问为何久）；公共区 2 张同配置 JPie 曾按旧规则询问用户 | form-stats.md「复制到仪表盘」：`result` 即 list、成功码=200、新 ID 在 `result.id`；保存后**数 template 项数**并清 `pageCompId=None` 坏项；回读校验禁截断输出。**同型多图默认取首张禁询问**（2026-09-08 用户铁令，旧规则作废） |
| 65 | 表单图（非聚合）val=自动金额公式（`$money…$*$number…$`），`set-chart-sort` 未点名排序字段 → 回落 valueFields[0]=公式串 → 落盘 `sorts.name=公式串` → **整图白屏**；设计器手工保存把 name 清空（剩 `{name:"",type:"desc"}`、dataFilterNum 保留）即恢复。手存后 config 残留 oral 误塞的 typeFields（「只列前2名」→ 支付方式 radio）无碍渲染（isGroup=false）（1009/902 本月订单看板·销售额排行榜，2026-09-08 实测，与 §63 聚合 calcId 键同签名） | 已修入 qqy_ops.py set-chart-sort：value 侧排序键以 `$` 开头 → 同聚合规则自动留空 name，只写 type/前 N（sorts.name 只认真实列键，另见 mutate.md「前 N 项 / 排序」⚠️） |
| 66 | 删 902/本月订单看板 JRankingList「销售额排行榜」：mutate.md 通读无删组件命令 → grep scripts + 逐段读 comp_ops/bi_utils（3 文件 5 段）→ comp_ops 直跑不带租户头 result 空 → 凭证旧 pageId 又空 → `menus` 现取新 ID → wrapper 两踩 MSYS 路径坑（真接口×4 秒级、整轮 ~20 工具调用，用户追问为何久） | 删组件 = `comp_ops delete --name`（qqy_ops 无）；先 `comp_ops list` 拿真实 componentName（口语「排行榜」≠「销售额排行榜」）；非租户2 页面预置租户头 + pageId 用 `menus` 现取；wrapper 先 `cygpath -m`（mutate.md「删组件」已全量沉淀）；文档没答案 → 1 次跑 usage，禁源码考古 |
| 67 | 点名改已有图（1008 新疆兵团/应用1/AI看板903「销售额构成」饼图设环形+标签中心，2026-09-09）：全新会话无 PAGE_ID 缓存 → menus 现取 id 与 `comp_ops edit` 拆两轮 Bash（真接口 3+2 次共 ~5s、整轮 ~1min 用户追问为何久；以往 30s 系同轮/历史会话已有 PAGE_ID 直跑 1 轮） | `comp_ops` 只收 PAGE_ID、不解析盘名：缺 id = `menus`（`drag` 行 menuUrl 列）现取与 edit **同壳串行一条 Bash**——`PAGE_ID=$(py …/qqy_ops.py menus API TOKEN --tenant-name 租户 --app-name 应用 2>/dev/null \| awk -F'\t' '$2=="drag" && $3=="盘名" {print $5; exit}')` 再 `comp_ops edit "$PAGE_ID" …`；`共编辑 N 个组件` 即停（实测同壳提取一次命中 1255392767526969344；SKILL §3 已并句） |
| 68 | 仪表盘收尾三处「键写对了但没用」：① `sorts` 我按列表 `[{field,order}]` 写 → 落盘变成 **Python repr 字符串**塞进 `sorts.name`，排序静默不生效；② 「近一年」当成 `queryRange` 选项写（还写成 `preYear`＝去年）→ 时间范围里根本没有「近一年」这项，只能 `queryRange:"custom"` + `customTime:[起,止]`；③ 按钮组回读读 `config.buttons` 恒空（真键是 `config.chartData`）→ 自检误报「0 个按钮」（2026-09-17 MEGA-项目管理） | `sorts` 是**单键字典** `{name:<图上真列 model>, type:"asc"/"desc"}`（写列表会被字符串化）；回读断言要 `isinstance(sorts, dict) and sorts.name`；口径一律按 `filter.queryField/queryRange/customTime` 三元组回读；JCustomButton 的按钮数组在 **`config.chartData`**，每项含 `title/openMode/icon/color/worksheet.desformId/operationType`。已并入 MEGA 自检脚本 `audit_dash.py` |
| 69 | 两个「原应用里有、敲敲云没有」的块怎么落：① 透视表的「计算列（剩余预算＝总预算−已发生成本）」——透视表的列只能来自**工作表字段**，图表侧造不出列；② 量规的「目标值＝总预算（求和）」——量规面板只有「进度 / 目标」两个显示名，没有显式的目标字段槽（2026-09-17 MEGA） | ① 在**工作表里加一个公式控件**（＝那两个字段相减），再当普通列勾进透视表 `nameFields`；② 进度/目标＝`valueFields[0]/[1]` 两槽 ＋ `compStyleConfig.progress.show`、`compStyleConfig.target.show` 都打开——**此条未做渲染验证**（无前端账号，只核到配置层），交付时要标明。别拿别的租户的量规当样本：那些都是大屏 `dataType=1` 写死的 `chartData`，没有 valueFields |
