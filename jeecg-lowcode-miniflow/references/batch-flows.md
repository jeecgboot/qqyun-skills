# 批量建流程（一次要建 >5 条）

## 铁律：大 JSON 只走文件，不进模型输出

2026-09-15 实测：63 条流程（源 processJson 合计约 2.8MB）时，agent 试图把等价配置一次性拼进模型输出 →
**单次响应超过 32000 输出 token 上限，agent 直接崩，57 分钟 0 产出。**

对照证据：同一轮里 25 个看板（44 次工具调用）顺利完成 —— 差别在 dashboard 走 **CLI + `--specs-file`**，大 JSON 落盘、不进模型输出。

**所以：**
- 每条流程一个 `--config` JSON 文件（`json.dump(..., ensure_ascii=False)`，**无 BOM**）
- 脚本一律 Write 成 `.py` 文件再执行；**禁止 `python -c "…大段代码…"`**
- 只 print 汇总行：`OK <流程名>` / `FAIL <流程名> <一句话原因>`
- **禁止 print** 返回体、`processJson`、节点树、设计 JSON
- 回读用程序断言，不要把回读结果打印出来人工比对

## 分批

- **每批 5~8 条**，一批一个脚本、一次 py 调用
- 每批结束只报一行：`第 N 批：成功 x / 失败 y`
- 60+ 条 → 拆 8~12 批

## 顺序（错了两边都建不起来）

1. **先全部子流程**：`save_flow` → `register_subprocess_id` → 补 `customProcessId=<DBid>` → `deploy_flow` → 校验 `/act/process/list` 出现 `key=process<DBid>`
2. **再建主流程**：`callActivity.attr.customProcessId` 指向**新建的**子流程 id

父流程必须在子流程 deploy 且注册完成之后才能建，否则 callActivity 找不到定义。

> ✅ **2026-09-20 起这条顺序由 `build_flows.py` 硬性执行**（阶段①.5 闸门）：
> 子流程全部建完 → 拉一次 `/act/process/list` → 逐条断言 `processKey` 已在引擎注册，
> **有缺就直接 `sys.exit(1)`，父流程一条都不建**。要带病继续得显式加 `--force`。
>
> 为什么做成闸门而不是提示：子流程没注册时，**父流程照样建得成功**（save/deploy 全绿），
> 错要等运行时调到子流程才抛 `FlowableObjectNotFoundException`。
> 2026-09-17 实测 22 条踩坑、2026-09-20 又靠流程外脚本补跑一次 ——
> 「事后补救」这条路已经证伪两次了。

## 路线：声明式 `flows.py` 优先，但**覆盖不到就必须补齐或手建**

**新建应用的流程优先走 `build_flows.py` + `flow_dsl` 声明式生成**（见 `create-flow.md`）。
节点类型超出 `flow_dsl` 覆盖范围时，按 `miniflow-node-types.md` 手写 `node_config`。

> ⛔ **2026-09-17 事故：这条「一律走批量」曾是错的，代价是 63 条流程全部不可用。**
> `build_flows.py` + `flow_dsl` 的**实际覆盖范围比它声称的窄**。实测（52 表进销存应用）：
> 凡「主表触发 → 取关联多条明细 → 逐行调子流程」这类流程，**引擎一个契约都没发出去**，
> 而 save/deploy 全绿。对照节点契约（`node-contract.md` §7/§9），缺的是：
>
> | 节点 | 正确形态（见 `node-contract.md` §7/§9） | build_flows 实际发出 |
> |---|---|---|
> | 取明细 | `selectType=3`（从单条记录获取关联记录）+ `linkFormTableField`=父表 link 的 model + `formTableId=form_start_<父表code>` + `limitNum` **留空** + `getDataType=1` | `selectType=1`、`limitNum=0`、`getDataType=2`、`linkFormTableField` 空 |
> | 新增单据 | `attr.formModel` **全字段映射** | `formModel` **空**（面板全空） |
> | 调子流程 | `attr.subFormTableObject`（数据对象=上游 getMore 节点）+ 传参 `record id` + **并行** 执行 | 数据对象空、逐条执行 |
> | 子流程自身 | `数据源`(上下文表) + 「被以下工作流触发」登记（`customProcessId` 回写） | 无（页面白屏，URL 上 `subFormTableObject=null`） |
> | 子流程尾部 | 建完明细后还有「**更新记录**」节点 | 建完明细即结束 |
> | `get_one` 取值 | 筛选值取「获取节点数据」/「本流程参数」 | 取「工作表事件回显」 |
>
> **2026-09-20 复测（52 表进销存，同一批流程）又抓出六个偏移 —— 说明这类「助手名看着对、发出去是另一回事」
> 是系统性的，不是一次性事故。完整清单 + 修法见 `node-contract.md` §9。**
>
> | 项 | 正确形态 | 实际发出 | 面板症状 |
> |---|---|---|---|
> | 子流程内取值来源 | `formNodeType:'search'` + `formNodeId`=数据源节点 id | `'getMore'` | 气泡显示「获取多条节点数据」 |
> | `data_get_one.formTableId` | `form_<本节点id>_<表code>` | `form_start_<表code>` | 更新对象选错 |
> | `data_update` 来源 | 指向前置 `data_get_one` + `'search'` | `'start'`/`'table'` | 同上 |
> | `updateFields[]` | 含 `id`/`fieldValue`/`valType`/`valueType` | 缺键 | 更新值显示 `[object Object]` |
> | 审批流 | `approver → data_update` 直连 | 套排他网关两支 | 更新被包在条件里 |
> | 审批人 | `appr(who="发起人")` | 写死 `users=["admin"]` | 人事不符 |
>
> **因此「按 `node-contract.md` §9 逐节点核对」不是可选项，是这条流水线的必经步骤。**
>
> **动手前的三条硬规矩：**
> 1. 批量生成这类流程前，**先把 `node-contract.md` §7/§9 的正确形状写进生成器**；
>    不要凭 `flow_dsl` 助手的名字假设它会发对。
>    ⛔ 不要走「找一份别人配好的同类流程来仿」这条路 —— **线上不存在现成的对照组**，
>    正确形状只在契约页里，照着写。
> 2. **不要用「未覆盖清单」当免责**——检查的是「发出去的 `attr` 对不对」，
>    不是「助手有没有抛错」。
> 3. 生成后**必须回读 `processJson`，逐节点对照 `node-contract.md` §9.1 的清单**，
>    对不上即视为失败；`OK:done 建 N / 失败 0` **不等于**配置正确。

### `flow_dsl` 的助手清单（2026-09-16 扩容后）

| 助手 | 干什么 |
|---|---|
| `flow(名称, table=, on=新增/修改/新增\|修改/删除, cond=[(字段,规则,值)], watch=[字段名])` | 主流程；`cond`=触发条件，`watch`=监控字段 |
| `subflow(名称, context=明细表, params=[变量名])` | 子流程；`params` 声明它要收的流程变量 |
| `get_one(表, cond=[字段名] 或 [(字段,规则,值)], empty=继续/新增/中止/分支)` | 取单条 |
| `get_more(表, cond=, sort=, limit=, from_=, name=)` | 取多条。⛔ **`from_` 只认字面量 `"start"`**（=「取本单的关联明细」，发 `selectType=3`）；写字段中文名 / 字段 model 都**不认**，会静默降级成 `getType=1`。**要喂给 `call_sub` 的取多条必须写 `from_="start"`** —— 否则数据对象为空、逐行子流程一行都取不到 |
| `update(表, {字段: 值})` / `add(表, {字段: 值})` | 改 / 新建 |
| `approve(名称, users=/roles=)` / `appr(名称, who=发起人/部门/部门负责人)` | **审批**节点；`appr` = 按表达式取审批人 |
| `fill(名称, users=/roles=/who=)` | **填写**节点（办理人看/改表单） |
| `gateway(名称, branches=[{name, cond, nodes}])` | 排他分支（**不含条件的那条会自动成兜底支**）。**要「相容分支 / 包含分支 / 包容分支」= inclusive**：照常 `gateway(...)`，再加一行 `g['type'] = 'inclusive'`，然后照常喂 `build_flows`（Resolver 会正常解析条件，产出 `inclusive` + `inclusive_end`）。⚠️ **别自己去调 `build_process_json` 拼**——它只是构建器、不解析中文名与中文规则；且它读的键是 `conditionNodes` 而 `gateway()` 产出的是 `branches`，写错会静默产出**空网关**（现在会直接报错拦住） |
| `data_branch(found=[...], missing=[...])` | **数据判断分支**，紧跟 `get_one(empty="分支")`。网关名由引擎硬编码为「数据分支」，DSL 已强制，传别的名会被覆盖（2026-09-21 源码定论，见 node-contract 8.3） |
| `upsert(表, cond, found=[...], missing=[...])` | **按条件定位一行：查到走 found / 没查到走 missing**（台账、库存、余额类回写的标准写法；默认展开成原生 `get_one(empty=分支)+data_branch`） |
| `compute(名称, "$甲$ - $乙$", {"甲": ref(..), "乙": ref(..)})` + `result(名称)` | **流程内运算**（四则/函数 → `funType: fun`） |
| `compute_record(名称, source=get_more节点名)` + `result(名称)` | **统计条数**（`funType: record`，数上游 get_more 取回几条） |
| `call_sub(子流程名, pass_={参数名: ref(..)})` | 调子流程并传参 |
| `delay(分钟)` / `note(标题, users=, kind=system/email/dingding/weixinqy)` | 延时 / 通知 |
| `ref(字段, node=节点名)` / `var(变量名)` / `inc()` / `dec()` / `lit()` | 值 |
| **`record_id(node=add节点名)`** | **上游 `add()` 刚建的那条记录的 id**（`variableValue:"_id"` + `formNodeType:"plus"` 形态，见 `node-contract.md` §2）。用在 `call_sub(..., pass_={"id": record_id(node="添加记录")})`；子流程里 `add(明细表, {"父单关联字段": var("id"), …})` 就能把新建明细行**挂到刚建的父单上**。⚠️ 2026-09-21 前本表漏列它，作者拿 `ref("id"/"_id", node=…)` 硬套 → 字段校验拒绝，「业务单→建凭证单→建明细行」这档整整白探了一轮 |

**⚠️ 照需求原文建，禁止「语义等价」的链路替换（2026-09-20 销售管理实测事故）。**
需求写「获取多条 → 运算统计条数 → 互斥分支（结果 = 0 / 其他）」，作者觉得「取单条 → 数据分支」是同一语义、
流程里做不了算术，就换了。两处都错：① 条数统计本来就做得了（`compute_record`）；
② 那条替代链路在真机上**把流程实例直接中止**（`get_one` 的 `noDataType=3` 在没有后续数据分支时
结束流程），新增节点一次没跑，而 save/deploy/契约检查全绿。
**需求里出现的节点名（获取多条 / 统计条数 / 互斥分支…）就是节点类型，照抄。**

**分支条件可以直接用运算节点结果当判据**：`gateway(branches=[{"name": "没有", "cond": [(result("统计条数"), "等于", 0)], "nodes": [add(...)]}])`
—— 主语写成 `result("节点名")` 而不是字段名。builder 会自动落成 `field="result"` +
`branchForm={formTableCode: "function-{funType}", formNodeId: <运算节点id>, formNodeType: "function"}`
（形态见 `miniflow-node-types.md`「四」4.4.1 / gotchas #59）。**别写成字段名**——引擎会按触发行快照取值，
条件恒判失败、永远走兜底支，而接口全绿。

**审批节点 vs 填写节点（选错就白建）**

| | `approve()` / `appr()` → `approver` | `fill()` → `edit` |
|---|---|---|
| 办理人看到 | 只有审批按钮 | **完整表单**，可看可改 |
| 能挂字段权限 | 能 | 能（都是走那个独立 API） |
| 什么时候用 | 纯审批：同意 / 不同意 | 「边看单子边处理」、要在节点里改字段 |

业务语言说「审批」时，先确认要不要看/改表单——**要，就用 `fill()`**。

### 构建前的「引擎行为规则」（`flow_rules.py`，`build_flows` / `precheck` 自动执行）

2026-09-21 先按真机黑盒试错写了六条，当晚对照源码逐条核实后修正（表与源码行号见 `scripts/flow_rules.py` 文首）：

| 规则 | 现状 |
|---|---|
| 1 数据分支网关名 | **强制「数据分支」**（真因，原「无数据支不执行」是误判）；`--rewrite-databranch` 可选绕行形态 |
| 2 流程建的行不吃默认值 | 被累加的列自动补 0（旧值为空时引擎 NPE） |
| 3 累加带小数的值归 0 | **构建器**对 number/integer 目标写 `fieldType=money` 走 BigDecimal；对 formula/summary/link-field 目标累加直接报错 |
| 4 运算节点取「取单条」结果 | 源码未证实 → 只告警 |
| 5 网关比较符 | 比较符对称、不再限制；判据是输入行 link-field/summary 快照时告警 |
| 6 同表同事件多流程 | 源码与对照实验都证明各触发一次 → 只告警提示合并 |
| 办理人=表单字段 | `fieldType` 必须解到 `select-user`/`select-depart`（引擎只认这两个字面量，他表字段要沿链解到底），解不出报错 |

改写/校正会打印 `NOTE:flow_rules …`（**要看**）；`--no-rewrite` 关改写、`--strict` 告警升级、`--lenient` 降级。
这些规则只是静态改写与告警，**不构成验收**：流程建对没建对，结构上由 `check_node_contract.py` 判，
运行起来账对不对**只有端到端冒烟看得见**——而冒烟**默认不跑**（用户明确要求才跑，见
`lowapp/references/fast-full-chain.md` ⑧-b）。所以默认交付口径是「结构闸门全绿、未做运行验证」，
别把前者说成后者。

### 批量 DSL 还**没**覆盖的（要手写 node_config，见 `miniflow-node-types.md`）

> 口径：`flow_dsl` 只覆盖「业务模板里反复出现」的那几种；下面这些要么很罕用，
> 要么参数太多（如审批人的 6 种取人方式），做成助手反而更容易写错。

| 缺口 | creator 支持？ | 说明 |
|---|---|---|
| **节点字段权限 `privileges`** | ❌ 节点内那份**无效** | 必须走 `/act/process/extActProcessNodePermission/saveOrUpdateBatch`，见 `field-perm-rule.md` 与 `api-reference.md` |
| **节点高级设置**（转办/加签/抄送/驳回/自选下一步/超时/表单可编辑） | ✅ 走 `attr` 手写 | 无 DSL 助手；逐项对照表见 `miniflow-node-types.md` **1.4** |
| 意见分支 `opinion` | ✅ `build_opinion_gateway` | 审批人点按钮选分支（同意/不同意） |
| 审批结果分支 `approve_result` | ❌ 只能手建 | 见 `miniflow-node-types.md` 十七-B |
| 并行 `parallel` / 包含 `inclusive` | ✅ `build_parallel_gateway` / `build_inclusive_gateway` | 并行需 `polymerize` 聚合节点 |
| 删除 `data_delete` / 更新流程参数 `upvariable` / 取人员部门 `get_*_sysinfo` / 服务 `service` / 脚本 `script` | ✅ 各有 `build_*` | 业务模板里很少见 |
| 触发类型 `manual` / `buttonEvent` / `timerEvent` / `dateFieldEvent` / `userEvent` | ✅ `build_process_json` | `build_flows.flow()` 只出 `tableEvent`；定时/按日期走 `timer_job_runner.py`，按钮触发要手写 config |

判定：需求的节点落在上表 → **停下来按 `miniflow-node-types.md` 手写 node_config**，
别指望 `flow_dsl` 兜住，也别为它扩 DSL（除非确认要在多条流程里复用）。
**唯一例外是字段权限**：它不是节点，是流程建完后的独立收尾步骤，见 `field-perm-rule.md`。

### 四个会「静默建错」的地方（2026-09-16 修掉，别退回去）

1. **触发事件类型**：引擎读 `attr.startEventType`，值是**字符串**（`add`/`update`/
   `add|update`/`delete`）。曾经发的是数字键 `tableEventType` → 取不到就落回默认
   `add|update`，**63 条流程的触发时机全部变成「新增|修改」**。
2. **触发条件 `startCondition`**：曾经压根没往 creator 传 → 记录级过滤条件全丢，
   流程变成「只要动这张表就跑」。DSL 里写 `flow(..., cond=[("字段","等于","值")])`。
3. **子流程的流程变量**：分三处，缺一处就静默失效（子流程照跑、一个字都不写）——
   · 子流程 config 根级 `variableList` 声明参数名，`hasVariableList=False`
     （主流程相反：`variableList=[]`、`hasVariableList=True`）；
   · 父流程 callActivity 的 `attr.variableList` 按名字传值；
   · 子流程节点里用 `var("参数名")` 引用。
   早先 `build_subprocess_node` 把 `attr.variableList` 硬写成 `[]`，且透传被 `_handled`
   挡掉，**任何传参都到不了子流程**。
4. **延时节点的时长**：`delay(N)` 曾经恒等于「1 分钟后」——因为 `duration` 写成了
   `attr.duration`（裸分钟数），而 `build_time_node` 只在**顶层**找 `duration` 且要
   ISO 8601 时长串。现在 `delay(N)` 会转成 `PT{N}M`（整小时/整天走 `P1H`/`P1D` 预置，
   设计器认得）。

5. **条件值 / 写入值写的是显示名**（2026-09-21 用户实测报障，见 `gotchas.md` #105）：
   `cond=[("入库确认","等于","是")]` 里的「是」是**页面显示名**，表单存的字典值是 `"0"` ——
   引擎拿 `"是"` 去 Mongo 里比 `"0"`，**恒不匹配、流程静默不触发**；写字段同理（写进去是空的）。
   **三处都要翻**：主流程 `cond`、**网关分支 cond**（⚠️ 它另起炉灶拼 queryItem，
   不走 `_cond_items`，最容易漏）、写入（`updateFields` / `formModel`）。
   已由 `Resolver.field_value()` 收编，认不出的值**直接报错**。
   提示词里的「是/否/已通过」是**业务语义**，落库前一律要问「这个字段真实存的是什么」。

### 2026-09-22 四应用并行实测后收进构建器的三件事（gotchas #118–#120）

- `call_sub(pass_={参数: 字面量})`：字面量按**子流程里该参数写入的目标字段**翻存储值（字典/选项字段写文案 = 落文案）。前提是子流程先于主流程建（本来就是这个顺序）。
- 写入 `select-depart` 目标：部门名自动翻成 `[部门id]`；已经是 id 的原样。
- 条件可写二元组 `("到货日期", "为空")` / `("…", "不为空")`，不必补 `None`。

### 引擎侧的对应叫法（写 `ref(node=...)` 时要用）

| 节点 type | 变量对象里的 `formNodeType` |
|---|---|
| 流程上下文行（start） | `table`（`formNodeId` 写 `"start"`、`formNodeName` 写「工作表事件触发」） |
| `data_get_one` | `search` |
| `data_get_more` | `getMore` |
| `data_add` | `plus` |
| `function`（运算） | `function`（`variableName:"结果"`、`variableValue:"result"`、`formTableCode:"function-fun"`） |

`formNodeId` 必须是**真正产出这个字段的那个节点的 id**。写死 `"start"` 时字段名对、
来源指错 → 运行时读的是上下文行，值永远不对。

### 自检

改过 `Builder` / `flow_dsl` 后至少跑
`python -m py_compile build_flows.py flow_dsl.py miniflow_creator.py`；
真机验证用**一次性测试流程**（建完立刻 `DELETE /act/process/extActProcess/delete?id=`），
别在正式应用里留垃圾流程。

## 幂等与失败处理

- 同名流程已存在 → 先 `GET` 查清单命中就跳过或带 `--id` 改，不要盲建
- 单条失败**只记录不中断**，整批跑完再统一重试失败项
- `save` 报 Duplicate key → `startTaskId` 不要等于任何节点 id
- `deploy` 成功但 callActivity 找不到定义 → 子流程补 `customProcessId` 再 deploy

## 改 / 重建单条流程的收尾（必做三件）

重建会换 `processId`，**引用方不会自动跟**。2026-09-21 实测：用 `--only <流程名>` 重建 2 条后，
旧记录没删掉、按钮还指着旧 id，应用里多出重名孤儿流，而每一轮验收闸门都显示「全绿」。

1. **删除步骤必带 `pageSize`** —— `extActProcess/list` 不传只回 10 条，目标不在前 10 条就静默不删
2. **按钮重绑** —— 凡 `processId` == 旧 id 的自定义按钮，`update` 成新 id（`update` 必带 `code`）
3. **回读三件事** —— 应用内流程总数（按记录的 `lowAppId` 过滤，租户下别的应用会同名）；
   每个按钮 `processId` 在清单里；不在产出清单里的孤儿流清掉

⚠️ **不要用「某字段为空/长度阈值」判断哪条是空壳流程**。`extActProcess/list` 返回的是
**精简记录**，`processJson` 根本不在记录里 —— 按长度判会把真流程全判成空壳删光（实测一次删掉 22 条）。
删除白名单只有一个正确来源：**本次产出的 id 集合**。

## 输出预算自查

| 项 | 上限 |
|---|---|
| 单次响应输出 | ≤ 32000 token |
| 一批脚本行数 | ≤ 500 行 |
| 单次工具调用打印 | ≤ 50 行 |

超了就再拆批。
