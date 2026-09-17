# 核心踩坑（按需·症状→指针）

> 默认不读。白屏 / 不渲染 / 编辑卡死 / 接口报错 / **墙钟过长** 时打开。  
> CLI 不在本表：改图 → `mutate.md`；建盘/加组件 → `create.md`。  
> `lessons.md` 教训索引，卡住/对证历史经验时对照。

## 墙钟过长

接口秒级而整轮分钟级 = 探查/往返，不是接口慢。禁止再用 memory/grep 来「分析为什么久」。开场 `memory_search`（「对得上历史会话 / 找 pageId」）就是探查，点名后禁止；通用 memory 指令对本 skill 无效。

| 症状 | 立刻做 |
|------|--------|
| 已点名改一项配置仍数分钟 | `mutate.md` 文首命令表原样跑；成功关键字即停 |
| 已有图改柱/折仍久 / 误跑 `qqy_ops pages` | `switch-type --to JBar|JLine`；缺 pageId 用 `menus`（无 pages） |
| 点名仍全表 `fields` / 每批加图各开一轮 | 点名维值跳过 fields；多表 add-charts 同壳串行 |
| 凭证从哪来 | 首条 Bash 前 Read 一次 memory 凭证文件（reference_jeecgboot_credentials.md）；401/换环境 → 问用户更新该文件；凭证禁写 skill/仓库 |
| 字段口语像控件类型（「多选框组」）先 `fields` | 口语=点名，`--dim` 直用原词；报字段不存在才停问 |
| `query_page` 空 / 旧 pageId / forms 参数错干等 | `SKILL.md` §3；立刻改参短跑 |
| `unrecognized arguments: --form-code/--form-name/--oral` | add-filter 只用 `--specs-file FILTER.json`；禁 grep / 禁再读全文 |
| 开场读完 lowapp+miniflow+本 SKILL 才建盘 | 全链路只读 `fast-full-chain.md` |
| 多表 `FORM_NEED_CHOICE` | `create.md` 复合盘：按表分批 add-charts |
| 已有图「前 N / 排序」仍 grep `dataFilterNum` | `mutate.md` `set-chart-sort` |
| 已有盘加图仍 grep 组件名 / 读 `charts-special` / Write 单图 specs / 开场 memory | `--oral "原句"` **且点名 dim/val 叠旗标**（≤30s）；禁 `memory_search`/`memory_get`（含与读 SKILL 并行）；仅白屏才 `charts-special` |
| `specs[0] 无法解析 dim=None` | 立刻叠 `--dim/--val` 短跑；禁 Read / 禁再只靠 `--oral` |
| add-charts 报「必须提供 --specs-file 或 --comp 或 --oral」而 oral 明明给了 | oral 缺组件口语词（只写「按…给…排名」→ 解析成 grp 分支、无 comp）→ 组件词（排行榜/柱状图…）放回 oral 或叠 `--comp J码` 重跑；禁 Read（2026-09-08 实测：补「排行榜」即过） |
| `*_UNKNOWN=` 后 grep 脚本确认别名/J 代码 | 只改该旗标近义重跑，禁 Read；别名只在脚本 |
| 参数含 `# $ `` 未加引号 / argparse 缺参 | PowerShell 元字符一律双引号 |
| `ADDED=` 后 dump 页 / 手写 py 补样式 | 首轮 `--oral`/`--style` 写全；漏了用最接近 mutate 命令加 `--style` 一条 |
| 点名多表绑错表 / `--form-name A,B` | `--form-name` 写有点名维值的那张 |
| 没有旗标（圆角/配色/形状/柱宽/点大小）就读 create.md / grep option | `--oral "用户原句"` 立刻跑；禁 Read；看 `ORAL_APPLIED=` |
| 复合盘拆成 4 轮 create-page/add-charts/add-buttons/add-filter | `create-dashboard --layout-file` 一条 ≤60s |
| 口语进 specs/layout 被拒后删盘对码重跑 | 脚本归一（本月/按日/柱状图…）；原命令重跑。禁读文档对码 |
| 为拿 TID/APP 先 `tenants`/`apps` 再写 | 写命令直接 `--tenant-name --app-name`；0 条脚本内去「租户/公司」后缀 |
| 建盘中途失败留下空页再手删重建 | 脚本 `ROLLBACK_PAGE=`；不要再开一轮 delete-page |
| 已有盘图+查询仍猜 `add-filter --oral` / 读 create.md / 失败后再写 JSON | `add-charts` 出 `ADDED=` 后立刻 Write `FILTER.json` + `add-filter --specs-file`；已有盘 ≠ layout-file |
| 文本/轮播/富文本仍读 `templates-ui` / 手写 config | `add-ui --comp` 用户原词 `--style 大标题,加粗,居中,整行` |
| 已有图刷新/总计/透视限制仍 grep timeOut/summary | `set-chart-refresh --minutes` 口语 / `set-chart-summary` / `set-pivot` |
| 自行发挥门户先 forms+fields 再发明布局 | `create-dashboard --auto` |
| 折线「面积」去 `switch-type JArea` | `--line-type` 接用户原词 |
| 已有饼改色+数值标签仍 grep `percentLabel` / 手写二次 save | `mutate.md` `--colors`+`--label-show` 同条 |
| 已有数字卡「与上月相比 / 升红降绿」仍 grep `isCompare` | `mutate.md` `set-chart-compare` |
| 已有图改计算值/标题仍 dump 页 JSON / 手写 py | `set-chart-calc --formula 求和`（无 calc 也升级）；同句改标题加 `--title`；只改标题 `rename-chart` |
| 跨表查询仍手合并一个 JFilterQuery | `create.md`：每表一次 `add-filter` |
| 删组件：mutate.md 无答案 → grep 脚本 / 逐段读 comp_ops+bi_utils 源码（单点删除 20+ 轮） | 删组件 = `comp_ops delete`（qqy_ops 无）；`mutate.md`「删组件」；文档没答案 → 1 次 `py comp_ops.py`（空参）看 usage，禁源码考古 |
| 金标同类盘加查询面板仍预读 memory / grep create.md+mutate.md / 预跑 list 查图名 | 凭证 Read → 抄 `examples/gold-product-province-filter.md` 字面量 → Write FILTER.json → `add-filter`：自带逐图 `CHART_MATCH=` 校验，错名/他表当场报错+CAND，图名无需预查（2026-09-08 实测：多 4 轮 +1~2min） |
| `add-filter` 后要顶置/位移组件，不知命令或坐标 | `comp_ops move --x --y`（`mutate.md`「顶置 / 插入级联」）；坐标 `comp_ops list` 一次现取现算净位移，禁抄其他盘 y 字面量 |
| comp_ops 改图（环形/标签/字号/移动等）全新会话缺 pageId：menus 取 id 与 edit 拆两轮 Bash（接口秒级、整轮 ~1min，用户追问为何久） | 同壳串行一条 Bash：`PAGE_ID=$(… qqy_ops.py menus API TOKEN --tenant-name 租户 --app-name 应用 2>/dev/null \| awk -F'\t' '$2=="drag" && $3=="盘名" {print $5; exit}')` 再 `comp_ops edit "$PAGE_ID" --name …`，`共编辑 N 个组件` 即停（2026-09-09 AI903 实测同壳提取一次命中） |

## 渲染 / 配置

| 症状 | 指针 |
|------|------|
| skill 柱/线比手工深（#5470c6） | 未写 `itemStyle.color=#64b5f6`；JBar 实心柱只认 itemStyle |
| 柱体渐变开了但列表只有一色 | `mutate.md`：`--gradient --colors A,B`（每色一条 customColor） |
| 聚合表加图 FORM_NOT_FOUND | `--form-name` 写聚合名；卡住 → `aggregation.md` |
| 聚合「字段类型不匹配」/ 行表头选不了 / 数据空 | `aggregation.md` |
| 图表白屏 TypeError | `compStyleConfig`+`analysis`+`filter`；dataType=4 |
| set-chart-sort 后整图白屏 | `sorts.name` 落了内部键：聚合 calcId 后缀键 / 表单自动金额公式串（`$…$*$…$`）→ 前端不认 → 设计器手工保存（name 清空）即恢复；脚本已自动留空 name 只写 type+前 N（2026-09-08 修复）；实例 lessons §63/§65，规则 mutate.md「前 N 项 / 排序」⚠️ |
| 总进度图点组件卡死 | 勿 `add-charts`；`charts-special` §1 |
| JColorGauge 白屏 | `charts-special` §0：gauge + axisLine |
| 只有轴无柱/线 | `option.series` 缺 type |
| 标题重复 / 「tab标题」 | `mutate.md`：`card.title=''` |
| JNumber 无「与上月相比」/ 箭头色反 | 已有图 → `mutate.md` `set-chart-compare`；新建 → `charts-special` §0 |
| 雷达不渲染 | `charts-special` §0：`dim` 必填 |
| 气泡/热力不显示 | 勿预置 map series；半行 w:12；`charts-special` §地图 |
| 关联记录作维空数据 | `create.md`：`as_dim_field` 展开 |
| 查询条件不能跨表单 | 每表一次 `add-filter`（`create.md`） |
| 要图筛选却多了 JFilterQuery | 误用 `add-filter` → `set-chart-filter` |
| `CHART_NOT_FOUND` 透视 | 匹配「表格」 |
| forms/options 找不到侧栏表 | menus 兜底 |
| 刚建的盘侧栏没有 / 写盘成功但用户找不到 | §3：写命令用本轮 `--app-name`；禁盲信 memory appId |
| **一批盘全挤在第一个分组里**（如 25 个盘全进「经营看板」） | `create-page` 未传 `--group`——缺省=**应用已有第一个分组**，静默落组、不报错。建时每盘必带 `--group <点名分组>`；已建好的改归组用 `group-menu --page-id <id> --group <组名>`（一次一盘，脚本内循环） |
| **删盘删不掉 / 盘越建越多**（25 个目标建成 58 个） | 从 `menus` 文本里正则抓 pageId 抓错了列：列序是 `id/type/menuName/parentId/menuUrl`，**名称后那一列是 parentId（分组 id）**。对 drag 菜单 **`menuUrl` 才是 pageId**。判定：`delete-page` 传了分组 id → 静默不生效 → 每次重跑净增一批。正解用 `build_dashboards.py`，它在 `index_menus()` 里取 `menuUrl` 列 |
| **建一批盘（≥5）** | 跑 `scripts/build_dashboards.py`（声明式 `dashboards.json`、单进程、非破坏、可断点续跑）。**禁止手搓编排器 + 禁止 `subprocess` 逐操作起进程 + 禁止 delete-then-create**——2026-09-15 实测手搓方案 25 张盘跑 42 分钟且攒出 58 个重复盘 |
| 图形按钮第二行字被裁 | graphical h≈20×行数（`create.md`） |
| 私自加字段被批 | 铁律：点名 dim/val 不存在先问 |
| `--specs 必须是非空 JSON 数组` | `--specs-file` + `py -c json.dump` |
| Token 401 | 重登后重跑 |
| 中文乱码 | `PYTHONIOENCODING=utf-8` + `py` |
| `py -c` 内嵌路径 FileNotFoundError / ModuleNotFoundError（跑 wrapper 时） | MSYS `/c/...` 在 `py -c` 源码内不被转换、PYTHONPATH 分隔用 `;`：先 `cygpath -m` 再拼（mutate.md「删组件」有整条） |

## 接口速记

- 组件 ID=`i`；侧栏/匹配键=`componentName`；图内可见标题=`option.title.text`（二者常不一致）；库 ID=`pageCompId`
- `query_page` → `template` 已是 list；空页可能 `None` → `or []`
- 删除组件：用户未明确说删则禁止自行 delete
- `comp_ops` 各命令（含 delete）不带租户头 → 非租户2 的 QQY 页面 `queryById` result 空（bi_utils 空 result 报错常误导成「pageId 过期」）：先 `qqy_ops menus --tenant-id --app-id` 现取 pageId（凭证旧 ID 也会过期），再预置 `bi_utils.EXTRA_HEADERS` 后 runpy 执行（完整 wrapper 见 `mutate.md`「删组件」）

- **`qqy_ops` 的 API/TOKEN 是「子命令之后的位置参数」**，不是 `--api-base` / `--token` 旗标（2026-09-11 实测）：写成 `qqy_ops.py --api-base URL --token T create-page …` → `argument command: invalid choice: '<URL>'`（argparse 把 URL 当成了子命令名）。正确＝`qqy_ops.py create-page <API> <TOKEN> --app-id …`；批量串行用 subprocess 传 `['create-page', API, TOKEN, …]`，**不要**加通用前缀函数。
- **`add-charts --specs-file` 的文件必须是「JSON 数组」**，不是 `{"charts": […]}`——后者是 `create-dashboard --layout-file` 的骨架（2026-09-11 实测）：传对象 → `--specs 必须是非空 JSON 数组`、rc=1；**且后续 `set-chart-filter` / `set-chart-calc` 会全部 `CHART_NOT_FOUND`**（图根本没建上），极易误判成筛选命令本身有问题。
- **`create-page` 输出含 PAGE_ID / MENU_ID / GROUP_ID 三个 19 位 id**（2026-09-11 实测）：解析必须精确抓 `PAGE_ID=(\d+)`；用「最后一个 19 位数字」会拿到 **GROUP_ID**，于是 `comp_ops edit` 报 `query_page` 异常、`add-charts --page-id <组id>` 静默跑偏。另：页面一旦建好（哪怕图表全失败）**不要再跑 `create-page` 重建**，改为复用已知 PAGE_ID，否则留下空壳重复页。
