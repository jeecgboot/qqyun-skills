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

## 路线：声明式 `flows.py` 优先，但**覆盖不到就必须补齐或手建**

**新建应用的流程优先走 `build_flows.py` + `flow_dsl` 声明式生成**（见 `create-flow.md`）。
节点类型超出 `flow_dsl` 覆盖范围时，按 `miniflow-node-types.md` 手写 `node_config`。

> ⛔ **2026-09-17 事故：这条「一律走批量」曾是错的，代价是 63 条流程全部不可用。**
> `build_flows.py` + `flow_dsl` 的**实际覆盖范围比它声称的窄**。实测（52 表进销存应用）：
> 凡「主表触发 → 取关联多条明细 → 逐行调子流程」这类流程，**引擎一个契约都没发出去**，
> 而 save/deploy 全绿。对照已知正确产物，缺的是：
>
> | 节点 | 正确形态（手建/golden） | build_flows 实际发出 |
> |---|---|---|
> | 取明细 | `selectType=3`（从单条记录获取关联记录）+ `linkFormTableField`=父表 link 的 model + `formTableId=form_start_<父表code>` + `limitNum` **留空** + `getDataType=1` | `selectType=1`、`limitNum=0`、`getDataType=2`、`linkFormTableField` 空 |
> | 新增单据 | `attr.formModel` **全字段映射** | `formModel` **空**（面板全空） |
> | 调子流程 | `attr.subFormTableObject`（数据对象=上游 getMore 节点）+ 传参 `record id` + **并行** 执行 | 数据对象空、逐条执行 |
> | 子流程自身 | `数据源`(上下文表) + 「被以下工作流触发」登记（`customProcessId` 回写） | 无（页面白屏，URL 上 `subFormTableObject=null`） |
> | 子流程尾部 | 建完明细后还有「**更新记录**」节点 | 建完明细即结束 |
> | `get_one` 取值 | 筛选值取「获取节点数据」/「本流程参数」 | 取「工作表事件回显」 |
>
> **动手前的三条硬规矩：**
> 1. 批量生成这类流程前，**先取一个已知正确的同类流程 `processJson` 当基准**
>    （机制：`/act/process/extActProcess/queryById`），逐节点对齐 `attr` 全键；
>    不要凭 `flow_dsl` 助手的名字假设它会发对。
> 2. **不要用「未覆盖清单」当免责**——检查的是「发出去的 `attr` 对不对」，
>    不是「助手有没有抛错」。
> 3. 生成后**必须回读 `processJson` 与基准逐节点 diff**，差异非空即视为失败；
>    `OK:done 建 N / 失败 0` **不等于**配置正确。

### `flow_dsl` 的助手清单（2026-09-16 扩容后）

| 助手 | 干什么 |
|---|---|
| `flow(名称, table=, on=新增/修改/新增\|修改/删除, cond=[(字段,规则,值)], watch=[字段名])` | 主流程；`cond`=触发条件，`watch`=监控字段 |
| `subflow(名称, context=明细表, params=[变量名])` | 子流程；`params` 声明它要收的流程变量 |
| `get_one(表, cond=[字段名] 或 [(字段,规则,值)], empty=继续/新增/中止/分支)` | 取单条 |
| `get_more(表, cond=, sort=, limit=)` | 取多条 |
| `update(表, {字段: 值})` / `add(表, {字段: 值})` | 改 / 新建 |
| `approve(名称, users=/roles=)` / `appr(名称, who=发起人/部门/部门负责人)` | **审批**节点；`appr` = 按表达式取审批人 |
| `fill(名称, users=/roles=/who=)` | **填写**节点（办理人看/改表单） |
| `gateway(名称, branches=[{name, cond, nodes}])` | 排他分支 |
| `data_branch(found=[...], missing=[...])` | **数据判断分支**，紧跟 `get_one(empty="分支")` |
| `compute(名称, "$甲$ - $乙$", {"甲": ref(..), "乙": ref(..)})` + `result(名称)` | **流程内运算** |
| `call_sub(子流程名, pass_={参数名: ref(..)})` | 调子流程并传参 |
| `delay(分钟)` / `note(标题, users=, kind=system/email/dingding/weixinqy)` | 延时 / 通知 |
| `ref(字段, node=节点名)` / `var(变量名)` / `inc()` / `dec()` / `lit()` | 值 |

**审批节点 vs 填写节点（选错就白建）**

| | `approve()` / `appr()` → `approver` | `fill()` → `edit` |
|---|---|---|
| 办理人看到 | 只有审批按钮 | **完整表单**，可看可改 |
| 能挂字段权限 | 能 | 能（都是走那个独立 API） |
| 什么时候用 | 纯审批：同意 / 不同意 | 「边看单子边处理」、要在节点里改字段 |

业务语言说「审批」时，先确认要不要看/改表单——**要，就用 `fill()`**。

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

## 输出预算自查

| 项 | 上限 |
|---|---|
| 单次响应输出 | ≤ 32000 token |
| 一批脚本行数 | ≤ 500 行 |
| 单次工具调用打印 | ≤ 50 行 |

超了就再拆批。
