---
name: jeecg-lowcode-miniflow
description: JeecgBoot 简流（MiniFlow）设计器 AI 自动创建器。Use when user asks to create/design a mini flow (简流), or says "创建简流", "生成简流", "新建简流", "简流设计器", "工作表触发流程", "低代码简流", "敲敲云简流", "miniflow", "miniDesFlow", "MiniFlow". Triggers when user describes a lightweight approval flow tied to a desform table (工作表事件触发 / 工作表联动流程), or needs to create workflow through the MiniFlow designer API. Also triggers when user wants to add approval flow to an existing desform form without BPMN. 改已有简流时只读本文件「修改已有简流」；新建只读 create-flow.md；**定时触发（壳/扫描/公告）按正文路由直跑 runner，自定义周期 → references/custom-cycle.md**。禁止打开 miniflow_creator.py / node-types / gotchas / example；查+建/改+save+deploy 同一脚本一次跑，禁止先探查再做、禁止跑通后再开"惯例核对"轮；凭证只用本轮消息或本会话已有值，禁止全盘搜、禁止翻其他 skill。
---

# JeecgBoot 简流设计器

将自然语言转为简流 JSON，经 API 创建或修改。脚本：`<skill_base_dir>\scripts\miniflow_creator.py`。

## 读文档路由（先看这张表，再决定读不读后面）

接口本身一般 **3–10 秒**。超过 1 分钟几乎都是多余阅读，不是后端慢。**按用户这句选一行，只读该行，读完立刻执行。** 文末参考列表不是开场必读。

> ⛔ **2026-09-17 事故：速度优先压过契约，导致批量建的 63 条流程全部不可用。**
> 本 skill 曾用「禁止打开 node-types / gotchas / example」「跑通后别再开核对轮」压耗时。
> 后果：`build_flows.py` + `flow_dsl` 建出来的流程，**引擎认的键一条都没发出去**
> （明细取关联记录、`callActivity` 数据对象/并行/传 record id、`data_add` 全字段、
> 子流程登记），而 save/deploy 全绿、计数全对。
>
> **因此：生成流程前必须读 `references/node-contract.md`（节点必填键一览）。**
> 它与「提速」冲突时**一律以它为准**。写完不算完 —— **必须回读 `processJson` 逐节点核对**，
> `OK:done` / `全部启用` **不是**验收。
> 建完**必须跑** `scripts/check_node_contract.py --api-base … --token … --tenant-id … --app-id …`：
> 它逐节点回读 `processJson` 对照 `references/node-contract.md`，违例非 0 即退出码 1。
> 2026-09-17 实测：它在我这里报 36 条违例，而同一次 `build_flows` 报的是「建 63 / 失败 0」。

| 用户在说 | 只读 | 禁止读 |
|---------|------|--------|
| 同轮要**批量新建多条流程**（≥3 条） | **先读 `references/node-contract.md`**（每种节点的必填键；不读 = 必有静默错配）；再读 `create-flow.md`「**批量建流程**」节：探查一次共享 JSON + 自愈硬清单 + 代理拆分 + `miniflow_helpers`（FunBuilder/publish_subflow/check_app_flows）。⚠️ **填写（edit）节点卡片文案 `content` 必须写「填写人显示名」**：绑定字段写字段中文名（`'直接上级'`/`'姓名'`），**表达式填写人写语义名**（`${applyUserId}` → `'获取发起人'`，即 `approverGroups[0].expressionsNames[0]`）——**禁止把 `assigneeByExp(${applyUserId})` 这类表达式原文写进 content**，画布卡片会原样显示这段代码（2026-09-16 用户实测指着卡片纠正）；收尾断言 content 非空且不含 `$`/`assigneeBy` | 每条流程各读一遍 create-flow.md；各代理重复 fetch 字段；子流程手工走 5 步发布配方 |
| **「<某应用>下新建 XX 流程」**——"应用" = 敲敲云/QQY 低代码应用（如「流程应用」「应用1」「应用2」） | 本文件路由表后续行 + `create-flow.md`。**判定只看「应用」二字**：句中出现「应用 / 工作表 / 敲敲云 / QQY / lowAppId」任一 → 必是本 skill | ⛔ **jeecg-bpmn / BPMN**——BPMN 是系统级引擎、**无"应用"归属**。⚠️ **四个反陷阱（实测会踩）：① 应用名本身可能就叫「流程应用」，其中的「流程」二字属于应用名、不是 BPMN 信号；②「获取单条数据」「获取多条数据」「或签」「审批人列表（多选人员）」全是简流原生节点/概念，不是 BPMN 专有——出现这些词反而更该走简流；③ 不得以"我先把 bpmn 载进来再读凭证 memory"为借口**——选 skill 前先 Read 凭证 memory（含各应用 lowAppId 与已建简流）再决定（2026-09-10 误加载 bpmn、用户纠正；gotchas #79）；④ **「包含分支 / 包容分支 / 排他分支 / 互斥分支 / 并行分支」全是设计器节点名**——「包含分支审批」要读成「包含分支 + 审批节点」，**不能读成动词「包含」+「分支」**（2026-09-10「全控件表单」误建成 exclusive、用户纠正后改 inclusive 返工）；分支类需求建流前必须让用户在 **互斥 / 包含 / 并行** 三选一，**禁止默认按互斥建**（消歧段见 `create-flow.md`）；⑤ **「表单内每个组件一条分支」类需求，条件规则必须按控件族分流**——范围查询只属日期/时间/数值，文本与公式**无「在范围内」**、文件类仅 为空/不为空（写不匹配的 rule 服务端不校验：save/deploy/回读全绿但设计器下拉无该项，见 gotchas #85、node-types 二十节） |
| 同一句还要**建应用 / 工作表 / 仪表盘** | 只读 `jeecg-lowcode-lowapp/references/fast-full-chain.md` | 本文件全文；node-types；`example/`（含入库审批）；dashboard SKILL |
| 在**已有流程**加 / 改 / 删某个节点 | 本文件「凭证」+「修改已有简流」（get_more 精简 config 已内嵌）。**点名的节点类型精简 config 没有**（如 api / aiOrchestration / message_*）→ 走下方默认段例外：grep node-types 标题后只读命中节 | `miniflow_creator.py`；gotchas；`example/`；trigger-types；`create-flow.md`；其他 skill |
| **工作表新增→单审批→改记录字段→结束**（最高频 OA 型：「新增记录触发」「审批通过后把状态改成已通过」「审批人直接指定用户/角色/部门」） | `create-flow.md`「**组合 J**」——含完整可抄 config + 落库位置 + 自愈，**单轮 1 次 py 即终态**（2026-09-10 实证）；解析/断言自伤预防见 gotchas #81。**脚本节点测算 + 排他分支变体 → 同文件「组合 J 变体」（流程变量四处同名·变量名用中文，gotchas #83）** | 入库审批示例全文、node-types 审批/更新节、`example/`、gotchas 全文 |
| 改**工作表事件触发筛选 / 触发条件**（startCondition 规则、值、触发字段、条件组） | 本文件「凭证」+「修改已有简流」+「startCondition 规则码（改触发条件必读）」段（下方内嵌） | 凭记忆写规则码；**把「在范围内」拆成两条 ge+le AND**（有独立 `range` 规则，2026-09-07 用户截图纠正，见 gotchas #50）；**日期类字段 val 写日期字符串**（必须毫秒时间戳 int，见下方规则码段/gotchas #52） |
| **删除整条流程**（按名称删） | 本文件「凭证」+「删除整条流程」（DELETE /act/process/extActProcess/delete?id=，代码已内嵌、2026-09-03 实测） | `miniflow_creator.py`；node-types；`example/`；create-flow.md；gotchas 全文（异常再 grep） |
| 查/列**应用下**流程、诊断「流程列表慢」 | api-reference.md「前置查询接口·查询应用下流程列表」：`extActProcess/list` + `X-Low-App-ID` 头，0.1s 只含该应用 | **用 `/act/process/list` 当应用列表/当慢的证据**——它是引擎定义列表，无应用过滤，457 条实测 3–5s/154KB（2026-09-09 实测） |
| **新建「定时触发流程」壳**（只说开始/结束/循环周期，**没说触发后要做什么**） | **直接跑 `scripts/timer_job_runner.py shell …`（argv 化，实测 3-5s）**；runner 异常兜底抄 `references/timer-shell-contract.md`；**周期 ∉ 7 预置（自定义组合）→ 抄 `references/custom-cycle.md`（完整模板内附）** | create-flow.md 全文；trigger-types；gotchas；example/；node-types |
| **新建定时壳**、周期=**固定月份×每月最后一天**（「每年上半年/每月最后一天」「1~6月最后一天」等） | 抄 `references/custom-cycle.md`：`dayValue=5`(每月最后一天)+`monthType=2`+`monthValues` **字符串数组** = 1 条流程即终态（2026-09-10 实测）。⛔ 口语「上半月」可能指**上半年**——语义先让用户一句话/截图确认再建；**禁止**当「1~15号每天+月末」拆两条、**禁止**探测 L 列表写法（dayValues 只收 1-31）、**禁止** generateExecTime 验算本组合（月末算例=每月30号，预览缺陷） | trigger-types 全文；gotchas；example/；node-types |
| 新建**「按日期字段触发」壳**（dateFieldEvent：给工作表+日期字段+时刻如"下午三点"，没说触发后要做什么）；**或带触发条件**（「…等于今天且医生等于管理员」等记录级过滤） | **直接跑 `scripts/timer_job_runner.py datefield --tenant <租户id> --app <id或名称> --table <工作表名> --field <日期字段中文名> --at 15:00 [--conds "医生=eq:管理员,状态=eq:待确认"]`**（argv 化；`--execute` 1当天/2前/3后、`--cycle-type` 1不重复/2每年/3每月/4每周、`--plus/--plus-unit` 分钟/小时/天；防呆+双回读内嵌，2026-09-09 建流实证）。**--conds 为全规则 DSL**（2026-09-10 扩展，序列化铁律内嵌：行独立雪花 id、组 matchType 大写）：eq/ne/gt/ge/lt/le/like(全模糊)/left_like/right_like/range(在范围内)/in/not_in/empty/not_empty；字段族=文本/数值/金额/日期/时间/下拉/单选/多选/人员/部门/岗位/组织角色/省市区/开关/他表字段/关联记录/系统字段(创建人·创建时间·修改人·修改时间)；**日期字段条件行 runner 直接支持**——`预约日期=eq:今天` 自动落 variable 形态(valueType:3+三键系统变量对象，2026-09-09 UI 手工补行实证)，字面量日期(如 2026-09-09)自动转毫秒 int；到期调度 triggerField+executeType 与日期行并存；属于/在范围 多值用竖线分隔——均**禁止探查轮**（2026-09-09 用户手工修复实证，细节见 trigger-types.md dateFieldEvent 节末）。⚠️ **--conds 白名单外 6 类控件**（`rate` 评分 / `color` 颜色 / `slider` 滑块 / `phone` 手机号 / `email` 邮箱 / **`select-depart-post` 部门+岗位联动**）仅支持 为空/不为空，且 runner **逐字段报错、一次只报一个**——**命中即两段式**（① runner 建支持行 ② 一条脚本回读 startCondition 追加 + 重排 + save/deploy + 回读），**禁止喂给 runner 反复试跑**；**颜色控件不支持筛选**，勿为其建条件行（2026-09-10 用户定论）。⛔ 时刻默认 15:00、存量同名壳默认「新建保留旧壳」——**均禁止提问/禁止为此探查**（用户实证选择） | create-flow.md 全文；trigger-types；gotchas；example/；node-types |
| 报错 / 前端空白 / 保存 500 | `gotchas.md` 用 grep 搜报错原文或现象，只读命中项 | 从头读 gotchas |
| 子流程 / callActivity / subEvent | `gotchas.md` 搜 subEvent/callActivity，只读命中项（**新建/发布 subEvent 先看 #47 API 自动发布配方**，三层 subEvent 见 #31；**手工拼子流程节点必须带渲染键**——start 根与每个手拼节点都要 `addable/deletable/content/error/errorContent`，否则设计器无＋（#39 2026-09-04 修正段 + create-flow.md subEvent 段））；`example/主子流程配置示例.md` **精简示例**第一节 | 入库审批全文、node-types 全文 |
| 同款业务改造：**主流程审批节点后插 get_more + 并行子流程、subEvent 子流程按明细行改台账**（资产领用/归还/调拨/报废/维修等 主表+明细+台账 三表结构） | **直接复用 `example/资产领用发放改造示例.md`**（完整跑通脚本：探查+建子流程+发布校验+主流程修改+回读校验 **1 次 py 跑完**，只改 ①–⑤ 常量；2026-09-07 实测）。⚠️ 需求点名「从关联字段获取单条」时模板 get_one 是 selectType=1 查询写法、不满足——先读 gotchas #53 把点名节点外科改成 selectType=3 再跑 | 其他 example 全文、node-types、gotchas 全文（异常再 grep） |
| 同款业务：**定时扫描 → 批量更新/新增/通知**（订单超时、预约就诊提醒、库存补货等 timerEvent 场景，全新建） | **零文档零探查直接跑 `scripts/timer_job_runner.py`（4 子命令全实测 3-5s：shell 壳 / announce 一次性全员公告 / scan 扫描+批改(update)+批量逐条新增(add)+逐行站内(to-field)+邮件(mail-to) / check 有/无记录分支动作）**——用法见下方「定时触发统一运行器」。改已有主流程才读 `example/定时批量处理逐行通知示例.md` 改 ①–⑤ 常量。铁律：多记录发消息必须 callActivity 子流程逐行（gotchas #57）；data_update 批量挂 getMore 契约且 formTableId 指向源 getMore（组合 E2）；同表两字段比较=gotchas #63 形态；定时/按日期触发**不得**含 start 空表条目（否则 UI 变量选择器出现「定时触发 工作表:""」——builder 已修 2026-09-14，存量清理见 gotchas #85）。**周期 ∉ 7 预置（每周一/每周四/每月15号…）→ runner 覆盖不了，抄 `references/custom-cycle.md`（模板+四轴语义+验算）** | 其他 example 全文、node-types、gotchas 全文（异常再 grep） |

### 定时触发统一运行器（全新建首选：单命令直跑，禁止写脚本轮）

命中"定时触发"任何全新建需求 → 优先 `scripts/timer_job_runner.py`，**零文档零探查零写脚本，一条命令即终态**（凭证内置读 memory；防呆同名中止；双回读断言+耗时内嵌；收件人按姓名/角色自动解析）。条件 DSL：`<字段>=eq:<值>`（radio/select 写文案）、`<字段>=le_fn:-24H`（D/H 偏移，today/tomorrow 别名）、`A=le_field:B`（同表两字段比较）。`--cycle` 仅 7 预置实名：每分钟/每小时/每天/每月1号/每周三/周一到周五/每年12月31日——**自定义周期 runner 不支持 → `references/custom-cycle.md`**。旧 `timer_notify_runner.py`（单形态）保留作 fallback。

```bash
# 壳：只给调度（开始/可选结束/周期）、无动作 → 空壳
py -3 scripts/timer_job_runner.py shell --tenant <租户id> --app <lowAppId> --begin "<开始执行时间>" [--end "<结束执行时间>"] --cycle <7预置周期名> [--name <流程名>]
# 一次性全员/指定人公告：--once=执行当天23:59截断 → 仅一次
py -3 scripts/timer_job_runner.py announce --tenant <租户id> --app <lowAppId> --begin "<执行时间>" --once --title <标题> --body <正文> [--users <姓名1,姓名2>]
# 扫描→批改→逐行站内/邮件（超时改状态提醒、库存补货等）：--to-field=逐行站内发该字段对应人；--mail-to 按姓名/角色
py -3 scripts/timer_job_runner.py scan --tenant <租户id> --app <lowAppId> --scan <工作表> --conds "<状态字段>=eq:<新文案>,<日期字段>=le_fn:-24H" --update <状态字段>=<新文案> --to-field <联系人字段> --title <标题> --body <正文> --begin "<开始执行时间>"
# scan 同式换 --add <目标表>:<源字段>=<目标字段>,<状态字段>=固定:<值>,<日期字段>=now --mail-to <收件人> → 批量逐条新增+邮件
# 检查有/无记录→分支通知：--if-data=<有数据支动作> / --if-empty=<无数据支动作>（如 msg:user:<姓名>）
py -3 scripts/timer_job_runner.py check --tenant <租户id> --app <lowAppId> --scan <工作表> --conds "<日期字段>=ge_fn:+1D" --if-empty "msg:user:<姓名>" --title <标题> --body <正文> --cycle <7预置周期名>
# 按日期字段触发：监控工作表日期字段，每条记录到期时刻各触发一次；--execute 1当天/2前/3后；--cycle-type 1不重复/2每年/3每月/4每周；"下午三点"=--at 15:00（默认即 15:00）
#   --conds=触发条件(全字段族全规则 DSL，2026-09-10)：<字段中文名>=<规则>:<值>,逗号=且；规则 eq/ne/gt/ge/lt/le/
#     like(全模糊)/left_like/right_like/range(在范围内)/in(属于)/not_in/empty/not_empty；属于/在范围 多值用 | 分隔；
#     日期字段值=宏(今天/昨天/明天/本周/上周/最近7天/本月/上月/下月)或字面量(2026-09-09→毫秒)；人员/部门/岗位/
#     组织角色/省市区按名或编码解析；系统字段(创建人/创建时间/修改人/修改时间)可点名；附件文件类仅 为空/不为空
py -3 scripts/timer_job_runner.py datefield --tenant <租户id> --app <id或名称> --table <工作表名> --field <日期字段中文名> --at 15:00 [--execute 2 --plus 1 --plus-unit 天 --cycle-type 1] [--name <流程名>] [--conds "预约日期=eq:今天,状态=eq:待确认,医生=eq:管理员,描述=like:复诊,附件=not_empty:,数字=ge:10,金额=gt:100,多选框组=in:选项A|选项B"]
```

覆盖：壳 / 一次性公告 / 扫描（批改/逐条新增/逐行站内/邮件）/ 有·无记录分支 / 按日期字段触发壳（datefield）。**未覆盖**：多条"汇总成一条动态明细"、**自定义周期（非 7 预置）→ `references/custom-cycle.md`**（0 轮判定 runner 不可用，gotchas #66）；多条记录逐行发消息必须 callActivity 子流程（gotchas #57）。datefield 的周期轴是 cycleType（不重复/每年/每月/每周，与 scan 的 7 预置 timeCycle 不同轴，勿互套）。

**CLI 补遗（argv 契约即 argparse 默认，勿读源码求证——gotchas #73）：** `--tenant` 只收**数字 id**（int() 强转，传名称即崩；租户名→id 全集见凭证 memory 文件）；`--app` 可传 id 或名称；`--begin` 可省 → 按 `--at`（默认 07:00）自动取**下一个**该时刻（当天已过→明天），「每天 7 点跑」只传 `--cycle 每天` 即可；`scan` 不传 `--title/--body` 用默认「提醒 / 请及时处理。」；参数错了 SystemExit 会自述字段名与候选值，改参重跑 ≤1 次。

默认不要打开 `miniflow-node-types.md`。仅当 create-flow / 本文件精简 config 不够时，才 `grep -n "^## "` 列出标题、或 `grep -n "^## .*（<类型>）"` 精确命中后，用 `Read offset=<标题行号> limit=<节行数>` **只读命中节**；标题括号是「别名 / processJson 类型」双标签（如 `time / timer_event`、`subprocess / callActivity`、`data_branch / databranch`），按 config 别名或内部类型哪个词搜都能命中。禁止不带 offset/limit 的整文件 Read；若 Read 返回了全文，只用目标节并立刻执行，不要接着打开 example/gotchas。

### 执行加速（强制）

1. **查流程必须带租户：** `query_flow` 已注入 `X-Tenant-Id`。用户给的是流程**名称**时 `query_flow(api, token, process_name="订单申请")`（换成目标环境真实流程名），不要先翻本地 json 找 processKey。⚠️ **`process_name` 模式不按应用过滤**（会命中别的应用的同名流程）——改/删前先按第 14 条确认 id 属于本应用，见 gotchas #87。
2. **改已有流程禁止重建：** 服务器拉最新 `processJson` → 只用 `build_*_node` 生成新节点 → 改 `childNode`/`pid`/`formTableList` → `save_flow` + `deploy_flow`。禁止 `build_process_json` 重铺整条链，禁止动用户没点名的节点。
3. **字段 model：** 用内置 `fetch_form_fields(api, token, form_code, tenant_id)`（封装 fields 接口，按中文名返回 `{model, type, options}`；link-record 返回 `{sourceCode, titleField}`，select/radio 返回可选值列表），应用/工作表用 `fetch_app_forms(...)`（两级结构一次给全）。**禁止手写死 model / formTableCode**——脚本内按语义自动解析即可（表单重建后 model 会变）。
4. **一次脚本跑完：** 只 `import` `miniflow_creator`，禁止 Read / grep / list 该文件。禁止先写探查脚本再写创建/修改脚本。写在同一个临时 `.py`，一次 `py -3` 执行。
   - 改已有：`query_flow` → 改 `childNode`/`pid`/`formTableList` → `save_flow` → `deploy_flow`。节点找不到就让该脚本失败退出，不要再开一轮「先打印树」。
   - 新建：getUserInfo + tenantAppFormList + fields → `build_process_json` → `save_flow` → `deploy_flow`。`startTaskId` 用 `task{ts}000`，与任何节点 ID 都不同（相同则 save 500 Duplicate key）。
5. **新建回合预算（强制）：** 全程 `py` 执行 ≤2 次。用户没给 formTableCode / 字段 model / 表结构不熟悉时，走 create-flow.md「**自适应一步流**」：`fetch_app_forms` + `fetch_form_fields` 在**同一个脚本内**定位表单、按语义解析 model，直接 `build_process_json` → `save_flow` → `deploy_flow`，不要"先打印 → 人看 → 再写创建脚本"的中间回合。确需先看输出才能定节点时：至多 1 次探查 + 1 次创建，且探查**一次打印给全**——应用两级列表全量打印、字段打印 `{中文名: model/type/可选值}`；禁止用摘要/裁剪函数把结构藏起来（否则必再来一轮，多花数十秒）。
6. **模板常量即目标环境禁止探查轮（强制）：** 路由表 `example/` 验证模板的 ①–⑤ 常量（TENANT/APP/表 code/字段 model）与用户描述环境**一字不差**时，改常量直接 1 次 `py` 跑完——模板自带防呆（应用/表在位 assert + 同名主流程中止打印），再为"防呆自查"跑探查轮纯属多轮返工，耗时主因不是后端慢而是探查轮串行（2026-09-09 教训，gotchas #58/#59/#61）。
7. **用户已确认 = 事实，禁止考古求证序列化（强制，2026-09-09 用户判定严重问题）：** 用户确认过的能力/格式直接按文档既有形态构造。**禁止**为"求证 UI 落库序列化"扫存量流程、**禁止**下载/反编译设计器前端 bundle（服务器 `/jeecg-boot/joa/miniDesFlow/`，本地无源码）——20+ 分钟零收益（gotchas #62）。结构/序列化正确性唯一校验 = save+deploy 后回读（一轮秒级）；引擎取数效果靠首跑验证，不对再修一轮。**时间盒：任何探查 2 次无果即停**，转"按最可能形态构造 + 回读"。同表两字段比较（A ≤ 本行 B）条件形态见 gotchas #63。
8. **简单流程默认值直接建，提问 ≤1 次（强制）：** 定时扫描→落表→通知/邮件类简单业务，常规默认（空轮不通知、通知一轮一次、收件人按语义/真实姓名推断）直接做，不连环提问（gotchas #64；同日两次超时均因提问+考古，用户反馈"不会有询问"）。
9. **模板/脚本跑通即终态，禁止"惯例核对/确认性"轮（强制，2026-09-09 超时主因）：** 路由命中模板、或一次 py 已 save+deploy 成功 → **直接收工汇报**，禁止再开第二轮 py"求心安"——核对同类流程命名惯例、结构对照、看别人有没有节点、改名对齐等。可推断的惯例（如定时壳命名=「定时触发流程-<周期>」）已由模板/本文件预置，不许事后探查。回读只允许内联在同一个脚本尾部（见模板）。
10. **依赖无关的文档并行读（强制）：** 凭证文件 / 路由命中文件 / trigger-types 命中节 / gotchas 命中项——命中与否由**用户原话**判定、彼此不依赖，**同一轮并行 Read**，禁止串行读完一个再决定读下一个（每串 1 轮 ≈ 多 8-15s）。
11. **路由标"直接跑 xxx_runner.py"的需求禁止写脚本轮（强制，2026-09-09）：** 此类需求 = 单条 Bash `py -3` 命令（凭证由 runner 内置读取，argv 传参，防呆+双回读内嵌，实测 5.8s），**禁止**复制模板/example 到临时 .py 改常量再跑（那是 runner 未覆盖场景的 fallback）、**禁止**读 example/gotchas 正文、**禁止**跑后再开确认轮——输出即终态。可重复的需求类（定时扫描→逐行通知、按日期扫当天等）优先沉淀成 runner 而非改 ①–⑤ 常量。
12. **凭证/记忆「已建」记录 = 已删候选，先核实再提问（强制，2026-09-10 复发）：** reference/记忆里的「XX 已建/在录」是旧 session 快照，流随时可能被删（实测 09-09 建的公告流次日 queryById 三应用全 500）。建新前若记忆有同调度同收件人存量 → 只许 1 条 `extActProcess/list`(0.1s) 核实或在建流脚本头部内联；核实出真冲突才把处理方式与内容/命名等未知**并入同一次 AskUserQuestion 一次问透**，禁止因快照发起第二轮提问或独立探查轮（gotchas #65）。
13. **防呆断言禁止用记忆快照值/猜键名（强制，2026-09-10 首跑失败实证）：** 脚本内 id（lowAppId/formTableId/DB id/键名）一律以**运行时 API 返回为唯一事实源**，防呆只断言「存在/按中文名定位成功」——拿记忆快照值做 `==` 断言且键名靠猜必崩（如 `fetch_app_forms` 返回 app=`{id, name, forms}`，**lowAppId 键名就是 `id`**、无 `lowAppId` 键；写 `app.get('lowAppId')==<记忆值>` 会让应用/表/字段全定位成功后仍多出整一轮 edit+重跑，gotchas #76）。
14. **建流前先列应用现有流程，判定建/改（强制，2026-09-10 建改误判实证）：** 用户说「XX 应用中……流程」未明说新建还是修改时，先 `GET /act/process/extActProcess/list`（带 X-Low-App-ID 头，0.1s）看该应用下现有流程——**已有同名/同业务流程一律按「修改已有简流」走，禁止直接新建**（实测：把「修改互斥分支流程条件」误判为新建，多建一条流程再删，用户纠正「是修改 而不是 新增」）。
15. **独立只读接口并发 + 会话值复用（强制，2026-09-10 用户连续两次追问「怎么这么慢」）：** 慢的主因 = 同一脚本里 7~14 个互不依赖的只读接口逐个串行（每个 1-5s 累加）+ 同会话重复拉已解析过的 app/form/字段/部门/角色/用户/字典。改法：① 互不依赖的 GET 用 `ThreadPoolExecutor` 一批并行（部门树/角色列表/用户列表/raw fields/字典主表同批，依赖 raw 的字典条目第二批）；② 本会话已成功解析的 lowAppId/formTableCode/titleField/字段 model/部门 id/角色 roleCode/用户映射/字典 itemValue **直接复用，禁止同会话重复拉取**（「运行时 API 为唯一事实源」约束的是**断言对象**，不是取数本身）：

```python
from concurrent.futures import ThreadPoolExecutor   # 独立只读接口一批并行，禁止逐个串行
with ThreadPoolExecutor(max_workers=8) as ex:
    f1 = ex.submit(requests.get, API + '/sys/sysDepart/queryTreeList', headers=HT, timeout=30)
    f2 = ex.submit(requests.get, API + '/sys/role/list', headers=HT, params={'pageSize': 200}, timeout=30)
    f3 = ex.submit(requests.get, API + '/sys/user/list', headers=HT, params={'pageNo': 1, 'pageSize': 200}, timeout=30)
    f4 = ex.submit(requests.get, API + '/desform/api/fields/' + form_code, headers=HT, params={'group': 'true'}, timeout=30)
    dep, role, user, raw = f1.result().json(), f2.result().json(), f3.result().json(), f4.result().json()
```

16. **同名工作表跨应用：定位目标表必须先按流程 lowAppId 限定应用（强制，2026-09-10 实测返工一轮）：** `fetch_app_forms` 返回**租户全量**应用，而**同名工作表常同时存在于多个应用**（实测一个租户下 4 个应用各有「仓库档案」、2 个应用各有「采购申请单」）——跨应用按中文名直接匹配会多命中、断言失败。正确顺序：先 `query_flow` 拿 `rec['lowAppId']` → 在 `fetch_app_forms` 结果里取 `str(app['id']) == str(rec['lowAppId'])` 的应用 → **只在该应用 `forms` 内**按中文名匹配；断言写「应用内唯一定位成功」，不要写成「租户内唯一」（后者在本环境必失败）。给已有流程加 添加记录/更新记录/获取记录 类节点时尤其容易踩。

17. **自愈禁止整块写 attr；决策键只在 attr 内读（强制，2026-09-10 年度预算流程两次自伤）：** `n['attr'] = {...}` 整块赋值会覆盖 builder 生成的 `expressionType:'delegateExpression'`/`expressionValue:'${updateRecordDelegate}'` → deploy 报 **`flowable-servicetask-missing-implementation`**（正解：只 `a['updateFields']=...` 增补键，勿整体替换）；排他分支条件自愈必须读 **`br['attr']['conditionGroup']`**（builder 放 attr 内，读顶层得 None → 写出空条件、分支恒走默认支），并补 `qi['id']`（builder 不生成行 id，缺则设计器无法编辑该行）。全量见 gotchas #82。审批人点名实体在本租户查不到时（如「财务总监」只有「财务主管」）→ 一次性并发拉 positions+roles+users+角色成员，连同其他未知项**一次 AskUserQuestion 问透**，禁止串行求证。

18. **本环境无任务完成/实例查询 API（强制，2026-09-10 swagger 728 路径确认）：** `/act/task/complete`、`/act/task/approve`、`/act/process/extActProcessInstance/*` 全 404；`/act/task/list` 忽略 `processInstanceId` 过滤参数（需客户端筛）。**审批后落库（updateFields 写变量）只能 UI 验收**，禁止为此连开探测轮；分支路由核验读 `/act/task/myApplyProcessList` 的 `currentTaskName`（★ 中文任务名最直观）。

### 凭证（强制）

按顺序取，取到即停：

1. 本轮用户消息里的 api-base / token / 租户
2. 本会话已经成功用过的同一组
3. 都没有：问用户一次

禁止 grep 用户家目录、禁止读其他 jeecg skill、禁止翻历史脚本找 token。  
Windows 执行用 `py -3`，不要假设 `python` 在 PATH。含中文时写成临时 `.py` 再跑，含中文 print 输出加 `PYTHONIOENCODING=utf-8`（否则 GBK 乱码，gotchas #60）。

凭证 memory 文件除 API/TOKEN 还含**租户全集（名→id，如 1008=新疆兵团）与各租户 QQY 应用 lowAppId、表单 code 快照**——runner `--tenant` 只收数字 id，故首条 Bash 前 Read 本文件可一次性消掉 API/TOKEN/租户/应用四个未知（2026-09-10 实测），禁止再开「租户名→id 解析」轮。

---

## 修改已有简流

```python
import sys, time
sys.path.insert(0, r'<skill_base_dir>\scripts')
from miniflow_creator import query_flow, save_flow, deploy_flow, build_get_more_node

rec = query_flow(api_base, token, process_name="订单申请")   # 换成目标环境里要改的真实流程名
pj = rec['processJson']
flow_id, update_count = rec['id'], rec['updateCount']

# 只 build 用户点名的新节点，接到目标节点的父.childNode，并补 formTableList
# ...

config = {
    'processName': rec['processName'],
    'processKey': rec['processKey'],
    'processType': 'oa',
    'lowAppId': rec['lowAppId'],    # 必须从 rec 取，禁止空字符串——传空会静默覆盖库字段：流程从应用简流列表消失，save/deploy/回读全绿不报错
    'startType': rec['startType'],
    'tenantId': rec.get('tenantId') or '',
}
result = save_flow(api_base, token, config, pj, flow_id=flow_id, update_count=update_count)
if result.get('success'):
    deploy_flow(api_base, token, flow_id)
```

`lowAppId` 必须从 `rec['lowAppId']` 取。每次必须 `query_flow()` 拉最新，禁止用本地缓存的 processJson。

**插在某节点之前：**

```python
def find_parent_of_named(node, parent, target_name):
    if node is None:
        return None, None
    if node.get('name') == target_name:
        return parent, node
    found_p, found_n = find_parent_of_named(node.get('childNode'), node, target_name)
    if found_n is not None:
        return found_p, found_n
    for branch in node.get('conditionNodes') or []:
        found_p, found_n = find_parent_of_named(branch.get('childNode'), branch, target_name)
        if found_n is not None:
            return found_p, found_n
    return None, None

parent, target = find_parent_of_named(pj, None, "查询客户是否存在")
new_node['childNode'] = target
new_node['pid'] = parent.get('id') or 'start'
target['pid'] = new_node['id']
parent['childNode'] = new_node
```

**删某个节点**（接到下游，并清 `formTableList`）：

```python
parent, target = find_parent_of_named(pj, None, "获取多条记录")
nxt = target.get('childNode')
parent['childNode'] = nxt
if nxt:
    nxt['pid'] = parent.get('id') or 'start'
pj['formTableList'] = [e for e in (pj.get('formTableList') or []) if e.get('nodeId') != target['id']]
```

节点 ID：`ts = int(time.time() * 1000)` 后 `f'task{ts}001'`，禁止 `gen_id()`。

**⚠️ 给网关分支加节点：挂 `br['childNode']`，不要写 `br['nodes']`（2026-09-11 实测，用户「分支里看不到消息」返工）：** 分支子节点在库里存的是 **`childNode` 链**（同应用【互斥分支2】三个分支均为 `childNode.type=message_system`、无 `nodes` 键）；写成 `br['nodes']=[节点]` 时 save/deploy 全绿、回读自己的写法也能读到，但**设计器分支显示为空**（用户看不到）。正确写法：`br.pop('nodes', None); msg['pid']=br['id']; br['childNode']=msg`。

**⚠️ 节点 id 必须是合法 XML NCName（字母开头）——数字开头 save 成功但 deploy 500（2026-09-11 实测）：** `f"{流程DBid}{i}001"` 这类纯数字 id 会让发布报 `cvc-datatype-valid.1.2.1: '<id>' 不是 'NCName' 的有效值`（save 200、deploy 500，流程停在旧版本）。统一用 `task{ts}{i}001` 形态。

**互斥分支条件修改的匹配坑（2026-09-10 实测）：** 设计器里排他网关分支名常是配置条件时自动生成的「字段+规则+值」（如 `单行文本等于测试`），与用户口述的「单行文本分支」不同名——按 `name` 找不到时按 `attr.conditionGroup[0].queryItems[0].columnName`（字段中文名）匹配；改条件时条件行缺 `id` 要补独立 id（行结构铁律，见下方 startCondition 规则码段）。**自定义表达式条件（分支条件类型=自定义）另成一套形态，勿与字段条件组互套（2026-09-10 用户 UI 实证）：** 表达式存分支节点 `content` 键（`${字段model 运算符 值}`）、`attr.branchType` 恒为 2、`conditionGroup` 恒为 `[]`、attr 无 branchForm，区分条件/默认分支只靠 `isDefault`；语法：**字符串值加单引号、数值不加**，运算符 `== != >= <= > <`，逻辑 `&&`（并且）/`||`（或者）。⚠️ **日期类字段（date，options.timestamp=true）的值写毫秒时间戳数字、不加引号**（如 2026-09-11 00:00 本地=`1789056000000`；写带引号的日期串能 save/deploy 但运行时恒不成立——字段存储=毫秒，数字 vs 字符串比较必 false，2026-09-10 用户实测确认「日期组件需要时间戳」）；**时间字段（time）仍是 `"HH:mm:ss"` 字符串、加引号**（用户 2026-09-10 确认「时间组件不是」毫秒）。完整落库 JSON 见 node-types 二十节、自愈模板见 create-flow 组合 J。
> ⚠️ **自定义表达式运行时作用域（2026-09-11 实测，buttonEvent 全流程返工）：** 只在 tableEvent 触发且引用起始行字段时可用；**buttonEvent 按钮触发、get_one 检索结果字段不注入 EL 变量**，运行时网关报 `Unknown property used in expression: ${xxx}`、流程卡死。这两种场景改字段条件组：分支 attr 写 `branchType:1` + `conditionGroup`（queryItems 行带 id；检索字段间比较 val=变量对象 `{formNodeType:"search", formNodeId:<get_one节点id>, ...}` + `valueType:3` + `valType:"variable"`）+ `branchForm` 指向 start/检索节点 + attr 内 `formTableCode`；默认分支 `branchType:2` + `conditionGroup:[]`。改完 save+deploy（新发起实例才生效，旧实例需用户终止）。
> ⚠️ **网关后合并链静默丢失（2026-09-11 实测）：** `build_process_json` **不保留 config 里 exclusive 的 `childNode`**——分支后的汇合节点（审批/最终改状态）根本没落库，save/deploy/回读全绿、流程跑完分支就断。新建回查必须看网关 `childNode` 是否为 null；丢失则按本节流程挂回：合并链新节点 `pid`=网关 id，approver/data_update 完整结构照抄同应用已有流程（query_flow 取模板，updateFields 完整写进 attr，source=start 时 `formTableSourceTaskId:"start"`/`formTableSourceNodeType:"table"`/`formTableId:"form_start_<code>"`），补 formTableList search 条目后 save+deploy。

### startCondition 规则码（改触发条件必读）

改 startCondition 前先查本段，**禁止凭记忆声称某规则不存在**（2026-09-07 教训：把「在范围内」错判为无此规则、拆成两条 AND，用户截图纠正，见 gotchas #50）。全枚举同 `trigger-types.md`「rule 全枚举」。

| rule | 文案 | 备注 |
|------|------|------|
| `eq` / `ne` | 等于 / 不等于 | |
| `gt` / `ge` / `lt` / `le` | 大于 / 大于等于 / 小于 / 小于等于 | |
| `in` / `not_in` | 是其中一个（或 属于）/ 不是任何一个（ruleName 纯展示，2026-09-10 用户 UI 样本） | 多值。⚠️ **val/value 形态随字段类型而变（实测见 gotchas #51）：checkbox → `val`=逗号字符串 + `value` 数组；select → `val`=数组 + `value` 数组；radio → `val`=数组、无 `value` 键**；**switch（开关）→ `val`=activeValue 字符串（见 gotchas #53）**。写错形态能 save/deploy 但 UI 显示错误 |
| `like` / `left_like` / `right_like` | **全模糊 / 左模糊 / 右模糊** | ⚠️ 设计器 UI 选项文案就是 全模糊/左模糊/右模糊（2026-09-08 用户截图实测：rule=right_like 保存后设计器下拉显示「右模糊」；example 里 like 的 ruleName=全模糊）。旧文档「包含/开头是/结尾是」是错的，按 rule 码选选项、ruleName 写同名文案（左模糊→ruleName=左模糊） |
| `empty` / `not_empty` | 为空 / 不为空 | `val` 和 `valType` 都写 **null**（**禁止空字符串**——日期/时间字段写 `""` 会在设计器值框显示 Invalid date，2026-09-08 用户实测；旧文档「空字符串」写法已过时） |
| **`range`** | **在范围内** | **用 `beginVal`/`endVal` 代替 `val`**（数字/日期字段可用，rule 白名单不匹配时 UI 不显示该选项）。**不要拆成两条 ge+le AND** |

单条条件形态：`{"rule": ..., "ruleName": ..., "valueType": "1", "val": ...（range 用 beginVal/endVal）, "name": None, "field": <model>, "columnName": <中文名>, "type": <字段类型>, "valType": <字段类型>}`。
**startCondition 在 processJson 里的位置**：根级 `pj['startCondition']`（根级没有再查 `pj['attr']['startCondition']`），结构 = 条件组列表 `[{id, matchType, queryItems:[单条条件...]}]`——改值只动组内 `queryItems` 条目与组 `matchType`，组 `id` 等其余键沿用既有值。⚠️ **UI 新版（2026-09-09 用户手工修复样本）行结构铁律：queryItems 每行必须带独立 `id`**——缺 id 的行设计器无法编辑/删除，且整组失去「添加条件」「且/或」能力（用户实测症状）；**dateFieldEvent（按日期字段触发）的触发条件同样落在 attr.startCondition**；到期调度由 triggerField+executeType 承载，**与日期条件行并存**——用户点名「<日期字段>=今天」时**要写该行**，形态=variable（`valueType:3` + `val`={formNodeType:'system', variableValue:'Today', variableName:'今天'} + `type`=date + `valType:'variable'`、行带 UI 式雪花 id；日期串/毫秒 int/裸 Today 字符串仍全错），完整样本见 trigger-types.md dateFieldEvent 节末（2026-09-09 用户 UI 手工补行实证，旧「日期字段勿写条件行」结论作废）。
**⚠️ 组织/人员类字段条件值形态各异（2026-09-09 用户 UI 保存样本实测，勿互套、勿凭输入框样式猜）：select-user → `val`=**username 标量** + `name`=**显示名标量**（如 `"val":"admin", "name":"管理员"`；写 userId 或 id 数组都会 UI「未选中」）；select-depart → `val`=[部门id] **数组** + `name`=[部门名] **数组**；org-role → `val`=roleCode 标量、`name`=null。**
**⚠️ 日期类字段的 val 必须写毫秒时间戳数字**（写日期字符串能 save/deploy，但条件恒不成立、或被引擎/UI 解析歪导致意外命中且选择器显示错日期——2026-09-08 两次实测，见 gotchas #52）：options.timestamp=true 的 date 字段（年月/年季度/年周/年月日/日期时间）→ 本地时区毫秒 int（年月→当月 1 号 0 点、年月日→当日 0 点；日期时间 eq 秒级相等）；只有 time 字段（无 timestamp）写 `"HH:mm:ss"` 字符串。判定看 raw `GET /desform/api/fields/<code>` 该控件 `options.timestamp`（注意 raw 里 `name`=中文名、`model`=编码），勿凭 fetch_form_fields 的 type 猜。
组内多条件 `matchType`：**UI 原生大写 `"AND"`/`"OR"`**（2026-09-09 用户手工修复样本=大写 OR；此前小写 and 实测导致设计器行间连接符错乱/「仍显示或」——小写形态已证伪）。单行时组 `matchType` 写 `''` 即可。⚠️ 用户没提 且/或 就只写单条条件，禁止自行加多条件组（跨租户值渲染为空行，2026-09-09 用户纠正）。改监控字段：`pj['attr']['conditionFields'] = [<model>]`。**改触发条件值按高危回读**：save+deploy 后 `query_flow` 核对 queryItem 的 rule/val 与行 id（org 控件 roleCode/编码写错静默失效，不报错）。

**控件族条件值形态（值 ≠ 中文名，2026-09-09 补 org-role / area-linkage 实测）**：select-user → `val`=username 标量 + `name`=显示名标量、`type`/`valType`=`select-user`（勿写 userId/id 数组，见上方 2026-09-09 用户实测）；select-depart → `val`=部门 id 数组 + `name`=名称数组、`type`/`valType`=`select-depart`；**org-role（组织角色）→ `val`=角色 roleCode 字符串、`name:null`、`type`/`valType`=`org-role`（连字符写法，与字段 model 前缀 `org_role_` 不同，勿照抄 model）**——写 roleName 中文名或 roleId 都能 save/deploy 但不匹配（org-role 写中文名 2026-09-09 实测踩坑，用户 UI 纠正）；roleCode 用 `GET /sys/role/list?pageSize=200` 按 roleName 找，**⚠️ 该接口跨租户返回，必须按 `tenantId == 当前租户` 过滤**（角色控件租户隔离，写别租户同名角色 UI 值框显示空）。org-role UI 原生样本：`{"rule":"eq","ruleName":"等于","valueType":"1","val":"<roleCode>","name":null,"field":"<org-role字段model>","columnName":"<字段中文名>","type":"org-role","valType":"org-role"}`（更多细节见 create-flow.md 组合 F）。**area-linkage（省市级联动）→ `val`=末级行政编码字符串 + `allVal`=各级编码数组**（如 海淀区：`"val":"110108","allVal":["110000","110100","110108"]`）——写名称路径字符串（"北京市/市辖区/海淀区"）能 save/deploy 但设计器显示「未选中」、运行时也不匹配（2026-09-09 实测，gotchas #57）。**link-field（他表字段控件）→ `type`/`valType` 写 `input`**（UI 原生编码，⚠️ 勿照抄字段 type 写 `link-field`——能 save/deploy 但运行时条件不匹配、流程不触发，2026-09-09 用户实测纠正）；**`val` 写设计器选择器里显示的选项文本**（⚠️ 勿按口述词写：实测用户口述「家居」、实际选项为「家具」，照抄口述词条件永不成立）。`fetch_form_fields` 对 org-role 不返回 options，必须查角色列表。**空类规则（empty/not_empty）UI 原生编码（2026-09-10 两次用户 UI 重存实证）：选择类控件（select-user/radio/select-depart/org-role）→ `val`=[] 空数组 + `name`=[] + `valType`=""；文本类（input）→ `val`="" + `name`=null + `valType`=""**——写 null/null/null 能 save/deploy 但设计器显示不对（用户两次纠正）；⛔ 日期/时间类字段空规则仍写 null（写 "" 会 Invalid date，gotchas #34/#52）。

### get_more 精简 config（改已有流程用这个，不要打开 node-types / example）

`getType` / `selectType`：`1`=从工作表查多条；`3`=从单条记录的关联字段取多条；`4`=从 data_add 取刚新增的记录。  
`fetchMode`：`"cache"` → `getDataType=1`（执行到此节点时缓存）；`"realtime"` → `getDataType=2`（每次使用实时获取）。  
`limitCount` / `limitNum`：最多条数，`0`=不限制。  
`sortField` + `sortType`：`"asc"` / `"desc"`。

```python
ts = int(time.time() * 1000)
node_id = f'task{ts}001'
form_config = {
    'formTableCode': (pj.get('attr') or {}).get('formTableCode', ''),
    'formTableName': (pj.get('attr') or {}).get('formTableName', ''),
}
# 单价/数量等字段 model 来自 GET /desform/api/fields/<formCode>?group=true 的 fields[].name
new_node = build_get_more_node({
    'id': node_id,
    'name': '获取多条记录',
    'getType': 1,
    'formTableCode': '<目标工作表 code>',
    'formTableName': '<表单名>',
    'conditions': [{
        'rule': 'ge', 'ruleName': '大于等于', 'valueType': '1',
        'val': 30, 'name': None,
        'field': '<单价字段 model>', 'columnName': '单价',
        'type': 'money', 'valType': 'money',
    }],
    'sortField': '<数量字段 model>',
    'sortType': 'desc',
    'fetchMode': 'realtime',
    'limitCount': 15,
    'emptyAction': 1,
}, form_config, level=1, parent_id=parent.get('id') or 'start')
new_node['attr']['searchContent'] = '[单价 大于等于 30]'
```

`getType=3`（从单条记录的关联字段取多条，落库为 `attr.selectType=3`）时 config DSL 写 `getType:3`/`sourceTaskId`/`relationField`；但 ⚠️ **builder 平移产物会让设计器 UI「节点对象/关联字段」错乱**——save 前必须按 `miniflow-node-types.md`「十三」的 ⚠️ **selectType=3 存储契约**外科重写该节点 attr（formTableCode/Name/Id=源表、linkFormTableCode/Name/Type=目标表、linkFormTableField=源表 link model、顶层零杂键）。  
`getType=4` 时再加 `sourceTaskId`（上游 data_add 节点 ID）。

**补 formTableList**（selectType=1/4；`getDataType` 与节点 attr 一致）：

```python
entry = {
    'formTableId': f'form_{node_id}_{form_code}',
    'nodeId': node_id,
    'nodeName': '获取多条记录',
    'nodeType': 'getMore',
    'formTableCode': form_code,
    'formTableName': form_name,
    'formTableMainCode': form_code,
    'selectType': 1,
    'getDataType': 2,
    'level': '1',
}
ftl = pj.setdefault('formTableList', [])
# 插到目标节点那条之前；已有同 nodeId 则覆盖
```

**⚠️ get_one / get_more 节点的 save 前自愈三条（2026-09-11 实证：`build_process_json` 产物与 UI 原生不一致——`save`/`deploy`/回读全绿，只有人打开设计器才看得出来）**

1. **`attr.formTableId` builder 会落成 `null`**（键在、值是 None，`setdefault` 补不进去，回读才暴露）→ 用**直接赋值**：`a['formTableId'] = f'form_{节点id}_{表code}'`，同时补齐 `formTableCode/formTableName/getDataType/selectType`。get_more 的 `getDataType` 要与下游统计节点（`funType=record`）一致（都写 1）。
2. **删掉 `limitNum` = 真「不限制」**：builder 按 `limitCount` 默认写 `attr.limitNum = 0`，但设计器「限制数量」输入框把 `0` **显示成 `1`**（用户会以为被限成一条）；UI 原生节点**根本不写这个键**。自愈 `a.pop('limitNum', None)`（连带 builder 多写的空 `sortField` 一起删）；**确实要限条数才写 `a['limitNum'] = <n>`**。回读断言写「无 limitNum 键」，别断言 `== 0`。
3. **`formTableList` 别乱兜底**：builder 已替查询节点登记条目（nodeType 是 `search`，**不是** `getOne`）。确需兜底时判重只能按 **`nodeId` 单键**——按 `(nodeId, nodeType)` 判重会把已有条目误判成缺失，再追加一条 `nodeType:"getOne"` 的**重复条目**（save/deploy 依旧全绿，靠回读逐条打印才看得出来）。

**追加修改要点（实测 2026-09）：**
- 已存在 get_more / get_one 的**多条件**不在节点顶层 `conditions`：实存 `attr.searchFieldGroup=[{id, matchType, queryItems:[...]}]`（queryItems 元素 = 上面单条件 dict）。追加「或」条件：向同组 `queryItems` append 新条件并把组级 `matchType` 置**大写 `"OR"`**（UI 原生口径：原生样本 AND 组即写 `"AND"`；设计器显示已核验，2026-09-11。旧文档的小写 `"or"` 写法已作废）；同时同步 `attr.searchContent` 展示文案——多条之间用**「 或 」**连接（AND 组对应「 且 」，原生卡片样式如 `[字段 大于 x] 且 [字段 小于等于 y]`）。
- 手动 dict 插入节点（不经 `build_*_node`）必须补渲染键 `addable=True / deletable=False / content='工作表 "XX"' / error=False / errorContent=''`，否则流程图无「＋加节点」图标；**不能有后续的节点不要加 addable**（分支网关主干、approve_result 上游等，见 gotchas #39 / #18）。
- **往网关前插运算/取数节点时 level 必须小于网关与分支的 level**（上游用 `"0.1"/"0.2"/…`，网关与各 `conditionNode` 同值如 `"1"`，分支内子节点更大如 `"2"`，`formTableList` 条目 level 与节点逐条一致）——否则分支条件的来源树（选择结果值）**只列出部分运算节点**，用户看到「函数计算/统计结果选不到」；条件本身没错，重排 level 后 save+deploy 即可（gotchas #84）。
- data_add 日期字段要「当前日期+N天」：在公共上游插 `funType='date'` 运算节点（funText `+10D`）+ formModel `formNodeType='function'` 引用（gotchas #41 完整代码）。
- data_update 的 updateFields 条目只要 `val` 是**对象**（变量引用，含运算节点 result）：条目顶层**必须带 `valueType: 3` + `valType: 'variable'`**（date 字段另加 `options.format`）——缺键 save/deploy 全绿、服务端 JSON 看着也对，但设计器把该值当**固定值**显示（日期字段表现为一个具体时间而非变量）；引用 function 结果需同时补 function-date 的 formTableList 登记且**按链序插 start 表条目之后，勿 append 尾部**（gotchas #58，2026-09-09 实测）。
- 排他/包含网关条件分支可直接引用**运算节点结果**判断（无需 upvariable 中转流程参数）：`field="result"` + `branchForm={formTableCode:'function-{funType}', formNodeId:运算节点id, formNodeType:'function'}`，补集分支用默认分支兜底（gotchas #59，node-types「四」4.4.1 完整代码）。
- 选项来自**字典/工作表**的 radio/select：写**字典 itemValue / 源表记录 _id**，字段内联 options 是占位副本，别照抄文案（gotchas #40，含免 Sign 取值接口）。

save 之后必须 `deploy_flow`。输出：流程 ID、名称、Key、操作类型（修改）、updateCount、发布状态。

**回读校验策略（用户 2026-09-08 确认，仅高危改动回读）：**
- 回读 = save+deploy 后 `query_flow(api, token, flow_id=<流程id>)`（⚠️ `flow_id` 必须**关键字**传参——第 3 位置参数是 process_key，位置传 id 查不到流程，见 gotchas #54 回读段内补注）拉服务端最新 processJson，逐节点打印 type/name + 关键 attr（分支 Y/N、hasResultBranch、updateFields[].field、approverNames/Ids 等）核对；不符即 raise 失败退出，不"成功汇报"。回读段**内联主脚本尾部同一轮 py**，禁止单独再开一轮（回读轮合并写法见 `example/资产领用发放改造示例.md` #337）。改用 queryById 兜底时 `processJson` 是字符串，先 `json.loads` 再 walk（gotchas #54）。⚠️ 建流脚本**单命令执行、禁止 `||` 兜底重跑**——py 正常但脚本断言失败时兜底会重跑整脚本、把流程建两遍（2026-09-09 双建实证）
- **高危（必回读）**：新增/移动节点、改 childNode/pid/conditionNodes（approve_result、手动 dict）、写字段 model 节点（data_update.updateFields、data_add、get_one/get_more 条件、selectType=3/4）、formTableList、子流程/发布——服务端对这类存在"保存 200 但静默落错"
- **低危（save+deploy 成功即收工，不回读）**：已有节点只改值——换审批人组 approverIds/approverNames、改节点名、非结构 attr（开关/提醒等）
- 判定基准：是否动到**结构 / 跨节点引用 / 字段 model**；每次脚本输出须注明本次改动属哪类、是否开了回读

---

## 删除整条流程

```python
import sys, requests
sys.path.insert(0, r'<skill_base_dir>\scripts')
from miniflow_creator import query_flow

API, TOKEN = '<api_base>', '<token>'
rec = query_flow(API, TOKEN, process_name="订单申请")   # 按名称取最新一条（换成目标环境真实流程名）
assert rec, f'未找到流程（名称可能不对）: {rec}'
headers = {'X-Access-Token': TOKEN,
           'X-Tenant-Id': str(rec['tenantId']),
           'X-Low-App-ID': str(rec['lowAppId'])}
r = requests.delete(f"{API}/act/process/extActProcess/delete",
                    params={'id': rec['id']}, headers=headers, timeout=30)
print('删除响应:', r.json())   # 成功: {"code":200,"success":true,"message":"删除成功!"}
assert query_flow(API, TOKEN, process_name="订单申请") is None, '删除后复查仍存在'
```

实测要点（gotchas #42，2026-09-03 全链路跑通）：
- 接口 `DELETE /act/process/extActProcess/delete?id=<流程记录 DBid>`：**方法必须 DELETE**（GET 报「不支持」）；id 是 `query_flow` 返回的 `rec['id']`，**不是 processKey**。
- 头带 `X-Access-Token` + `X-Tenant-Id` + `X-Low-App-ID`（值全部从 rec 取，禁止写死）。
- `query_flow` 同名多条只返回**最新一条**；删除后复查返回 None 即成功。
- 删除前确认无引用：自定义按钮 processId、被 callActivity 引用的子流程（有引用先解绑/删父流程）；已停用/未发布流程可直接删，建议先停用再删。
- 要删旧的那条但按名只能查到最新 → 用「改名挪移法」停用兜底（gotchas #42 末节）。

---

## 新建流程

读 `references/create-flow.md`，不要在本文件继续找创建步骤。

---

## References

不是开场必读。先按文首路由选文件，再用 grep 定位后读片段。

| 文件 | 何时读取 |
|------|---------|
| `references/create-flow.md` | **新建**整条流程 |
| `references/trigger-types.md` | 新建且 startType 不是 tableEvent/manual，需要完整触发参数 |
| `references/timer-shell-contract.md` | 定时壳（7 预置实名）API 契约 / runner 异常兜底脚本（日常建壳走 runner，禁止手抄本文件） |
| `references/custom-cycle.md` | **自定义周期**（timeCycle=custom，∉7 预置）定时流程唯一权威：完整可抄模板 + 月/日/周/时四轴字段 + 需求例句→attr 映射（含已验证 flow）+ generateExecTime 验算契约（跨年心算/月末例外）+ 口语歧义防坑 |
| `references/miniflow-node-types.md` | 精简 config 不够时：grep `^## ` 定节后，用 grep 行号 `Read offset/limit` 只读该节 |
| `references/api-reference.md` | 需要 API 路径 / buttonEvent 按钮 |
| `references/gotchas.md` | 报错或前端异常，grep 现象后只读命中项 |
| `references/field-perm-rule.md` | 配置节点字段权限 |
| `references/example/` | 精简 config 不够、需要对生产结构时，只读对应文件「精简示例」 |