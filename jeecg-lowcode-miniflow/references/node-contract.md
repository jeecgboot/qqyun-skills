# 节点契约（生成流程前必读 · 从线上已跑通的流程实测提取）

> **这页回答一个问题：引擎到底认哪些键。**
> 助手函数「建出来了」≠ 引擎「读得懂」。save/deploy 全绿、回读计数也对，
> 但键没发出去 → 面板空白、运行时一行都不写。
>
> **用法**：写 `node_config` / 改 `build_flows` 之前，按本页核对目标节点的**必填键**。
> 校验方式只有一个 —— 生成后回读 `processJson`，与本页逐键对照。

约定：`attr.*` = 落在节点 `attr` 里的键；`(node)` = 落在节点**顶层**的键（别写进 attr）。

> ⚠️ **校验边界（2026-09-20 实测补充）**：本页覆盖 `data_get_more` / `callActivity` /
> `data_add` / `data_get_one` / `data_update` / 分支网关 / `edit`·`approver` **七类节点的键契约**。
> 消息节点的正文占位符绑定**不在本页**，那套契约在 `miniflow-node-types.md` 八
> （8.1b 与该节末两段）。
>
> 另注：`{{字段名}}` **不是**自动解析的模板语法（区别于明道云等"写字段名就带出"的设计器），
> 不配映射就是一段纯文本。
>
> **`check_node_contract.py` 的覆盖范围比本页宽**（2026-09-20 扩过一轮）：除本页的键契约外，
> 还查 ① `formTableId` / `funText` 能否解析到本流程真实存在的节点与表、② 画布 `content` 是不是
> 原始 id / hex / 字段名本身、③ `formTableList` 与节点双向对得上、④ 消息占位符有没有在
> `jsonContext` 里绑定、⑤ 同名重复副本。**验收就以它为准**；它自带 `--self-test`（不联网），
> 拿合成样例证明这几类缺陷都抓得出来 —— 校验器本身也会退化，改完它先跑自测。

---

## 1. 取多条明细：`data_get_more` 的「从单条记录获取关联记录」

父单据触发 → 取其关联明细（子表）时用这一种；**不是**「从工作表获取多条」。

| 键 | 值 | 说明 |
|---|---|---|
| `selectType` | `3` | 3=从单条记录获取关联记录 |
| `getDataType` | `1` | |
| `noDataType` | `1` | |
| `formType` | `2` | |
| `formTableCode` / `formTableName` | 主表 | 上下文表 |
| `formTableId` | `form_start_<主表code>` | |
| `linkFormTableField` | **父表 link-record 控件的 model** | 指向明细的关联控件 |
| `linkFormTableCode` / `linkFormTableName` | 明细表 | |
| `linkFormTableType` | `1` | |
| `formTableSourceTaskId` | `start` | |
| `formTableSourceNodeType` | `table` | |
| `expressionType` | `delegateExpression` | |
| `expressionValue` | `${getMoreRecordDelegate}` | 漏了 → deploy 报 `flowable-servicetask-missing-implementation` |
| `sortType` | `desc` / `asc` | |

⚠️ **`limitNum` 不写**（留空）。写了数字 = 只取 N 条，逐行子流程会漏行。

## 2. 逐行调子流程：`callActivity`

| 位置 | 键 | 值 |
|---|---|---|
| attr | `isMulti` | `true`（逐行） |
| attr | `customProcessId` | 子流程的 **DB id** |
| attr | `subFormTableObject` | **选择数据对象**，见下 |
| attr | `formTableId` | `form_<上游 getMore 节点id>_<明细表code>` |
| attr | `calledElement` / `processId` / `processName` | 子流程标识 |
| attr | **`formTableSourceTaskId`** | **上游 `get_more` 节点的 id**（逐行场景必填，见下 ⚠️） |
| attr | `collection` / `elementVariable` / `loopCardinality` / `isSequential` / `completionCondition` / `variableList` | 循环相关；**逐行处理明细时不要写 `collection`/`elementVariable`**（那是审批人列表场景的写法） |

> ⚠️ **`attr.formTableSourceTaskId` 空串 = 多实例子流程永远不结束（2026-09-21 实测事故）**：
> 值必须是**上游那个 `get_more` 节点的 id**（与 `subFormTableObject.nodeId` 同值）。
> 手拼/自愈节点时最容易漏掉它——`build_process_node` 产出的该键就是**空串**。
> 后果：子流程拿不到行源，token 停在 callActivity 上，**父记录 `bpmStatus` 永久停在 2（处理中）
> → 列表里被锁、没有编辑按钮；子流程一条也不建**。而 `save` / `deploy` /
> `check_node_contract` **全部通过**（只查结构，不跑实例）。
> 判据只有一条：真机造一条会走该分支的记录，看 `bpmStatus` 是否到 3。
| **(node)** | `inVariableModels` | **传参**（向子流程传初始值） |
| **(node)** | `outVariableModels` | |
| **(node)** | `listenerData` | |

`subFormTableObject` 形状（键名固定）：

```json
{"formTableId": "form_<getMore节点id>_<明细表code>",
 "nodeId": "<getMore节点id>", "nodeName": "<getMore节点名>",
 "nodeType": "getMore",
 "formTableCode": "<明细表code>", "formTableName": "<明细表名>",
 "formTableMainCode": "<主表code>", "formTableType": 1,
 "selectType": 3, "getDataType": 1}
```

**多条数据执行方式**：UI 里的「并行 / 逐条执行」——默认应按**并行**（`isSequential=false`）。

**传参首选「[文本] id = 添加节点 -- record id」**（线上 29 条子流程里 9 条这么传，
主流程侧 8 处 `field:"id"` 的取值形态**无一例外**都是它）：

```jsonc
{"field": "id",
 "val": {"variableValue": "_id", "formTableCode": "<data_add 目标表 code>",
         "variableName": "记录id", "formNodeType": "plus",
         "formNodeId": "<data_add 节点 id>", "formNodeName": "添加记录"}}
```

⚠️ 它**不是** `ref()` 的形状（`variableValue` 是字面 `_id` 而不是字段 model、
`formNodeType` 是 `plus`）。用 `ref()` 套 → 子流程里那个字段永远是空的，
链路跑起来「像什么都没发生」。
`flow_dsl.record_id()` 产出就是这个形状；**它只能指向前面 `add()` 建的新增节点**。

**子流程侧这几处登记是 `build_flows` 第 ③ 趟的客户端写入 —— 后端不会替你做，不要等它**：

⚠️ **本文件此前写「父流程 deploy 后回填」，是错的 —— 文档与源码脱节已久，2026-09-23 同步订正。**

**这不是新发现。** `build_flows.py` 第 ③ 趟（`sub_links` 循环）自 **2026-09-17** 起就在注释里
写明了「**后端不会替你做**，设计器是自己算好一起提交的」，并附跨两个应用 29 条子流程的实测：
靠 API 存完后 `formTableList[0].isSubStart` 与 `subFlowSourceInfo` **一条都没回填上**。
**只是契约文档当时没跟着改**，于是长期停在错误说法上（本条结论的成熟度按 09-17 那份源码算，
不是按 09-23 这次调试算）。
**父流程 `callActivity` 发得再对，不动手写就永远是空。**

误信这一句的代价（销售管理定时流程实测）：拿「父流程发歪了」去解释一切，逐个换自变量试 ——
子流程重存、父 `subFlowList`、`subFormTableObject.isSubStart`、`collection`/`elementVariable`、
触发类型（表事件 vs 定时）、取数节点锚定，**6 个假设轮轮证伪**。它们确实都不成立，
因为自变量根本不在这几处。

回填要写四处，①②③ 的 `subFormTableObject` 必须**同源一致**：

| 处 | 位置 | 要点 |
|---|---|---|
| ① | 父流程 `callActivity` 节点 `attr.subFormTableObject` | `nodeId` = 父流程那条 `get_more` 节点 id |
| ② | 子流程 `attr.subFormTableObject` + `attr.formTableId` | **漏了 → 引擎拿不到「本次处理的是哪张表」，子流程里 `ref()` 取空、`var()` 正常**，记账类子流程每次都走 missing 分支、新建的行只有 `var` 写进去的那几个字段（2026-09-22 进销存 R3 实测，**四道闸门全绿**） |
| ③ | 子流程 `formTableList[0]` | `isSubStart:true` + `nodeType:"search"` + `nodeTypeMain:"getMore"`，`nodeId`/`formTableId` 指向父流程那条 `get_more` 节点 —— 子流程页的「数据源」 |
| ④ | 子流程 `subFlowSourceInfo` | 追加 `{mainProcessName, nodeName, mainProcessId}` ——「被以下工作流触发」 |

⚠️ **登记名是别名 `"子流程"`（`build_flows.SUB_ROW_NAME`），不是父流程那个节点的名字。**
金标「增加/减少库存子流程」里父节点叫「从单条记录获取关联记录」，子流程登记的照样是「子流程」；
填成父节点名时设计器下拉会显示得像表名。

⚠️ **乐观锁：父流程 save 会连带顶掉子流程的 `updateCount`**（服务端在父流程存盘时会写一笔
子流程的 `subFlowSourceInfo`，哪怕写出来是 `[]`）。所以**「先存父、再存子」时必须重读子流程
`updateCount`**；拿旧的去存 → `save` 返回 `success:false` —— 只打 `success` 不打 `message`
就会白丢一轮。

> **证据强度：本条仅一例观测**（2026-09-23 销售管理定时流程），**机制未跨流程验证**。
> 机制上的推断是「任何带 `subFlowList` 的父流程存盘，都会重算子流程的 `subFlowSourceInfo`」，
> 但没在第二个案例上验过。**照「存之前重读 `updateCount`」办不会错**，无论机制是否普遍成立。

子流程「本行字段」引用还要一并定形（`build_flows._fix_sub_ownrow_refs`）：
`formNodeId` = 父流程 `get_more` 节点 id、`formNodeName` = `"子流程"`、`formNodeType` = `"search"`；
`data_update` 指向本行的 `formTableSourceTaskId:"start"` / `formTableSourceNodeType:"table"`
也要改成 节点 id + `"search"`。
⚠️ **取数节点位于网关分支里时不要改**（`_in_branch`）：这种拓扑下 search 形态运行时取空。

**验收**：回读子流程，确认 `subFlowSourceInfo` 非空**且** `formTableList[0].isSubStart == true`。
好消息是**这个能验** —— 回填是静态落库，不依赖起执行器，比「造一条记录看 `bpmStatus`」门槛低得多。
（本项目实测：63 条流程里只有 1 条回填上了。）

> **子流程页白屏 / 「被以下工作流触发」为空** = 同一件事：
> 这四处登记有没写全的 + 父流程 `customProcessId` 没指对。
> 见 `gotchas.md` #47 的发布配方。

## 3. 新增记录：`data_add` 必须写全 `formModel`

| 键 | 值 |
|---|---|
| `formModel` | **目标表每个要写的字段 → 取值**（不写 = 面板全空、运行时建空记录） |
| `addDataType` / `formType` / `noDataType` | |
| `formTableCode` / `formTableName` / `formTableId` | 目标表 |
| `formTableSourceNodeType` / `formTableSourceTaskId` | 取值来源节点 |
| `expressionType` / `expressionValue` | |

⚠️ **按行批量新增，`pj.formTableList` 里那条登记也必须跟着写**（2026-09-20 实测，对照可用参考应用发现）：
批量节点的 `attr.addDataType=2` + `attr.formTableSourceGetDataType=1` 只改节点本身不够 ——
`formTableList[]` 中同一 `nodeId` 的条目要**同时**带 `addDataType: 2` 与 `formTableSourceGetDataType: 1`。
登记写成 `addDataType: 1` 时节点面板/回读全绿、`attr` 也对，但引擎按「单条新增」处理，
**逐行循环不发生**（症状：按钮点了没有明细、父表也看不到子行）。`check_node_contract.py` 目前不校验这条，需人工比。

`formModel` 的取值形态（两种，别混）：

```jsonc
// ① 引用上游明细行的字段（跨子表引用）—— funText + funContext
"input_1701429216564_793751": {
  "funText": "{{<hash>.link_field_1697783086235_444204}}",
  "funContext": {"<hash>": "<URL 编码的 {field, formTableCode, ...}>"}
}
// ② 流程变量（如传进来的 record id）—— ⚠️ 仅子流程/被传参的流程可用，见下方警告
"link_record_1701311092220_846556": {
  "variableName": "id", "formNodeType": "variable", "variableValue": "id"
}
```

⚠️ **形态② 是「流程变量」引用，只在子流程等被传参的流程里成立**（变量由调用方
`call_sub(..., pass_={'id': record_id()})` 传入，源码见 `flow_dsl.var()`）。
**主流程（buttonEvent / tableEvent）没有名为 `id` 的流程参数**——把「当前触发记录的记录id」
写成这个形态会落库为 `{formNodeType:'variable'}`，设计器显示「本流程参数 -- id」、运行时取空
（2026-09-20 ds0920 实测：建流时按本条把 `ref('id')` 批量改成 `var('id')`，5 条主流程 6 处落库为空值行，
逐个人工重写才恢复）。**当前触发记录的记录id** 用
`{variableValue:'_id', variableName:'记录id', formNodeType:'table', formNodeId:'start', formNodeName:'<触发表节点名>'}`；
**前面 `add()` 刚新增的那条**用 `formNodeType:'plus'` + 该 add 节点 id（即 §2 的传参形态）。

> `flow_dsl` 里用 **`lit({...})`** 原样写这两种形态（见 `batch-flows.md` 助手清单）——
> 它跳过解析直接落库，2026-09-22 库存先进先出应用实测与设计器产物逐字节一致。
> ⚠️ 但 `lit()` 只解决**写值**；**不能**拿它给 `get_one` / `cond` 提供「当前记录的 `_id`」当**查询条件**
> （`_id` 不在 `flow_dsl` 的字段表里，见 `batch-flows.md`「未覆盖清单」）。

⚠️ **凡带 `formNodeType` 的取值条目必须同时带 `formTableCode`**（引用来源表：`table`/`start` → 流程起始表 code、
`getMore` → 该节点 `linkFormTableCode`、`plus` → 该 add 节点目标表 code）；`variableValue:'_id'` 的还要带
`fieldType` = **目标字段**真实类型（关联记录 `link-record`、文本 `input`）。
缺了服务端不校验（save/deploy 全绿），但引擎**静默丢弃该字段**：该字段非必填 → 只是字段空、子表回指也空；
必填 → **整条记录不落库**（症状：按钮点了父表 0 行、子表却建了行）。2026-09-20 实测（ds0921「创建报价单」父表 0 行、
子表 8 行回指全空）；flow_dsl 生成的 `formModel` 引用条目曾全部缺这两个键 —— 批量建过的流程要按本条逐条扫。

## 4. 取单条：`data_get_one`

attr 必带 `searchFieldGroup`（筛选条件落在这里，**不在**顶层 `conditions`）、
`formTableSourceGetDataType`、`formTableSourceNodeType`、`formTableSourceTaskId`、
`sortField` / `sortType`、`selectType`、`formModel`；
选人/部门/角色字段另带 `userFormTableField` / `deptFormTableField` / `roleFormTableField`。

**筛选条件的取值来源**：用「获取单条节点数据 / 本流程参数」，
**不要**用「工作表事件回显」——后者在子流程里取不到父单据的值。

### 子流程**首节点**按记录定位：`selectType=3`「从关联字段获取单条」+ 四处对齐 `isSubStart`（2026-09-24 实测）

线上跑通的形态（与参考流 `测试01-子流程1` 逐键一致）：

```python
a['selectType'] = 3
a['formTableSourceNodeType'] = 'search'
a['formTableSourceTaskId'] = '<该子流程 formTableList 里 isSubStart 那条的 nodeId>'
a['formTableId'] = f"form_{a['formTableSourceTaskId']}_{a['formTableCode']}"
a['formTableSourceGetDataType'] = 1
a['linkFormTableField'] = '<记录上那个关联字段的 model>'    # 源表
```

⚠️ `formTableSourceTaskId` 长的像 `task…`、看着就是**父流程的节点 id** —— 它其实是该子流程
**自己的数据对象 id**，值必须等于 `isSubStart.nodeId`。写成父流程里真实存在、但**没登记**的
另一个节点 id（或与 `start.attr.subFormTableObject` 不一致）→ 首节点取到 `dataId=null`，
日志 `未获取到数据，dataId = null` / `Id must not be null!`，**save / deploy 全绿**。
同一子流程被多处 `callActivity` 调用时最容易踩（症状像「条件写错了」，其实是登记对不上，
与 gotchas #45 的 XML 缺 listener 是两回事）。

## 5. 更新：`data_update`

`attr.updateFields` = 完整条目数组（`field` / `val` / `fieldType` / `type` / `optType`）。
`optType`：`"1"` 设值 / `"2"` 增加 / `"3"` 减少。
`attr.formTableSourceNodeType` 指向取值来源（`search` / `getMore` / `table`）。

## 6. 分支：`databranch` / `exclusive` / `inclusive`

节点**顶层** `conditionNodes`；`attr` 只有 `level`（`exclusive` 另有 `hasResultBranch`）。
分支 content 由引擎生成，不要手写。

### 6.0 分支条件的两类「写错也不报错」

**（a）判据是「运算节点结果」时，`branchForm` 必须落在分支 `attr`，不是条件项里**
（2026-09-21 实测）：

```python
branch['attr']['branchForm'] = {'formTableCode': 'function-<funType>',   # 统计条数=function-record
                                'formNodeId': <运算节点 id>,
                                'formNodeType': 'function'}
branch['attr']['formTableCode'] = 'function-<funType>'   # 与 branchForm 同值
# 条件项只写：{'rule':'eq','field':'result','val':0,'type':'number', ...}
```

把 `branchForm` 塞进 queryItem 里**不报错、也不生效** → `field:"result"` 按触发行取值、
恒不命中 → **该分支永远不执行，每次都落到默认支**。有默认支所以**不会卡**
（`bpmStatus` 照样是 3），**只有数据不对**——比卡住更难发现。

**（b）`link-record` / 子表 的「为空 / 不为空」规则码是 `empty` / `not_empty`，不是 `null` / `notNull`**
（2026-09-21 实测）：

```json
{"rule": "not_empty", "ruleName": "不为空", "valueType": "1",
 "val": [], "name": [], "field": "<link_record_ 或 sub_table_design_ model>",
 "type": "link-record", "valType": "link-record"}
```

`val` / `name` 都是**空数组**（不是 `""` / `null`）。
写成 `notNull` 的后果比 (a) 重：该条件每次求值都出错 →
**`inclusive` 网关的 token 永远到不了 `inclusive_end`** → 实例永久卡住
（`bpmStatus=2`），**且与哪条分支命中无关**。
`miniflow-node-types.md` §4.2 的规则表列的是**通用规则集**，按控件族取码时以本段为准。

**（c）子流程里带条件的分支：`branchForm` 必须写 `search` + 该子流程 `isSubStart` 登记的那条 `nodeId`**
（2026-09-24 实测）：

```python
br['attr']['branchForm'] = {'formTableCode': '<明细表 code>',
                            'formNodeId': '<formTableList 里 isSubStart 那条的 nodeId>',
                            'formNodeType': 'search'}
br['attr']['formTableCode'] = '<同上>'
```

子流程没有可判的「触发起始行」。写成 `{'formNodeId':'start','formNodeType':'table'}` 时
**save / deploy 照样成功**，但部署出的 BPMN 里条件退化成裸字段（无来源前缀）：

```
正确: ${ branchExpressUtils.eq2('tbb95413.search.task790080497913007.input_x', …) }
退化: ${ branchExpressUtils.eq2('input_x', …) }        ← 恒不成立
```

后果按网关有没有默认支分成两种，**都静默**：无默认支 → 实例报
`No outgoing sequence flow of the exclusive gateway '<id>' could be selected`、整单回滚；
有默认支 → 走默认支，看着「跑完了」，实际一条业务支都没执行。
判据看运行日志：正常分支必打 `【条件评估】字段:<带前缀> | 操作符:<…> | 实际值:<…> | 结果:<✓通过>`，
退化分支只有 `-等于:<裸字段>,<值>`，**没有随后的【条件评估】行**。

同族的几处必须指向**同一条** `isSubStart` 登记：分支的 `branchForm.formNodeId`、
子流程 `start.attr.subFormTableObject`、`start.attr.formTableId` —— 不一致时报 `Id must not be null!`；
`isSubStart` 只留 1 条（重复登记会让首节点取到 `dataId=null`）。
子流程**首节点**取数的对齐口径见 §4 末。

### ⚠️ `inclusive`（包含分支）**必须保证任何情况下至少有一条分支命中**，否则实例永久卡死

（2026-09-20 实测事故，用户报「新建一条记录后没有编辑按钮、流程状态是处理中、我的发起里也没有流程」）

`inclusive` 的语义是「所有**满足条件**的分支都走」——**一条都不满足时 token 停在网关上**，
既不走分支也不进聚合，实例永远不结束。后果全是静默的：

- 触发记录 `bpm_status` 停在 **2(处理中)** → 该记录在列表里**被锁、没有编辑按钮**；
- `/act/task/list` 总数 0（没有待办任务，看不出"卡"）；
- **不出现在「我的发起」**（`tableEvent` 流程默认 `createStartNode=False`，本来就不进我的发起，
  所以这一条**不是**故障证据，容易被误判成"流程压根没触发"）。

**实测对照（同一条流程、只差一个字段）：**

| 触发记录的字段 | 结果 |
|---|---|
| `重要程度 = 一星`（某条分支命中） | 分支执行、`bpmStatus=3 已完成` |
| `重要程度 = 空`（一条都不命中） | 值写不进去、**`bpmStatus=2 处理中` 永久卡住** |

**根因写法**：把「枚举值是否在某个集合里」直接写成 `eq/  in` 分支，而**没覆盖字段为空的情况**。
字段是**非必填**时，新建记录的默认状态就是空 —— 也就是**最常见的那条路径必卡**。

**修法**：给每个 `inclusive` 补一条**兜底分支**（无动作、`nodes: []`），条件用该控件族**合法规则集**内
的「为空」：

```python
{'name': '重要程度为空', 'priorityLevel': 6,
 'conditions': [{'rule': 'empty', 'ruleName': '为空', 'valueType': '1',
                 'val': '', 'name': None, 'field': <该字段 model>,
                 'columnName': '重要程度', 'type': 'input', 'valType': 'input'}],
 'nodes': []}          # 兜底分支不需要动作，只要"命中"即可让实例走下去
```

⚠️ **兜底条件的规则必须按控件族选**，不能顺手写 `not_in`——**文本类（input/textarea）没有 `not_in`**，
只有 `eq/ne/模糊/为空/不为空`；数值/金额类才有 `gt/ge/lt/le/range/为空`；选项类（radio/select/checkbox）
才有 `in/not_in`。写了不存在的规则**服务端不校验**：save/deploy/回读全绿，只有人打开设计器才看到
下拉里没这一项（同 gotchas #85）。
`inclusive` **不得用 `isDefault` 兜底分支**（见 `create-flow.md`），所以「兜底」要靠一条**显式的
`为空` 条件分支**，不是默认分支。

**排查与解锁**：
- 判定：`list_data` 看该记录的 `bpmStatus`（2=卡住、3=已完成）；`edit_data` 会触发 `add|update`，
  所以**把卡住的记录重新编辑一次**（新实例这次能命中兜底分支）即可解锁，`bpmStatus` 会变 3。
- ⚠️ 解锁时改记录**别用「只传一个字段」的 `edit_data`** —— 它是**全量覆盖**，只传的字段会
  把该行其余字段清空（`fast-full-chain.md` 已写，2026-09-20 又踩了一次：解锁时只传「客户简称」，
  把用户的记录清成了只剩一个字段）。要**整行回填**：先 `list_data` 取全量 `desformData`，
  改目标字段，再整体写回。

## 7. 审批 / 填写：`edit`（`approver`）

节点顶层：`approverGroups` / `approverType` / `assigneeType` / `privileges` / `listenerData`。
attr（30+ 键，常用）：`approvalEnabled`、`formEditStatus`、`ccStatus`、`rejectStatus`、
`transferStatus`、`allowAddSign`、`skipApproval`、`selnextUserStatus`、`msgStatus`、
`sameMode`、`assigneeIsEmpty`、`timeType`/`timeDate`、`isSequential`、`ratio`、`level`。
**`content`（办理人显示名）非空**且不含 `$` / `assigneeBy`。
**字段权限不在 processJson 里**，走 `/act/process/extActProcessNodePermission/saveOrUpdateBatch`。

**审批后要写回状态时，`data_update` 直接串在审批节点后面，不要再套排他网关。**

正确形态（2026-09-20 实测：进销存应用里 `采购申请-审批` 等 8 条审批流**全部**是这个形状）：

```
start → approver（审批）→ data_update（写回单据状态）
```

- **驳回由审批节点自带的驳回按钮处理，流程直接结束**，不需要、也不应该有「驳回写回」那条分支。
  给它配网关两支会让「审批通过」也变成一条条件边，用户看到的是「更新节点被包在条件判断里」。
- 审批节点的 `approverGroups[0]` 决定谁来办：**默认 = 流程发起人**，用
  `assigneeType="assigneeByExp"` + `expressionsIds:["${applyUserId}"]` +
  `expressionsNames:["获取发起人"]` + `approverType:"candidateUser"`，
  且节点 `content` 写 `'获取发起人'`。DSL 用 `appr(name, who="发起人")`，**不要写死 `users=["admin"]`**。
- `data_update` 的 `formTableSourceTaskId`/`formTableSourceNodeType` 仍是 `start`/`table`
  （它改的是触发记录本身），`formTableId` 为 `form_start_<触发表code>`。

> ⚠️ 本条曾写作「通过/驳回各写回什么，都要在节点后接 `data_update` 分支」——**那个描述是错的，已删除**。
> 按它建出来的流程，审批通过路径被包进条件分支。

### 7-b 办理人必须能解析到人（2026-09-24，`check_node_contract` 已机械化）

下面四种形态 save/deploy/审计**全绿**，运行时要么实例起不来、要么任务谁都收不到。闸门逐条判违例：

| 形态 | 后果 | 正确写法 |
|---|---|---|
| `approverIds:["user.admin"]` | 任务派给不存在的 `user.admin` | **裸账号** `["admin"]`（`user.` 只用于消息节点 `toUserIds`） |
| `roleIds:["部门经理"]`（角色名） | 引擎按 roleCode 归集待办 → 无人 | `roleIds:["dept_manager"]` + `roleNames:["部门经理"]`；`build_flows` 已按 `/sys/role/list` 自动把名/码解析好 |
| `${applyUserDeptLeaderId}` / `${applyUserDeptId}` | 本机 Flowable 抛 Unknown property，实例起不来，前置节点写的「审批中」已落库 → 单据卡死 | `candidateUsers` + `${flowNodeExpression.getDepartLeaders(applyUserId)}`（表达式白名单见 `miniflow-node-types.md`「表达式」表） |
| 顶层 `approverGroups` 与 `attr.approverGroups` 不一致 | BPMN 取**顶层**；外科补丁只改 attr 等于没改 | 两份同改 |

另判：审批组里的账号在本租户不存在 → 违例。

> 说明（2026-09-24 第 2 轮三个应用回读）：审批**节点顶层**的 `approverType` / `assigneeType` 两个键固定回读为 `candidateGroups` / `assigneeByName`，与审批组内部（部门负责人类是 `candidateUsers` + `assigneeByExp`）不一致——**运行时只看 `approverGroups`，顶层这两个键可以忽略**，12 个审批落点全部进待办。核对办理人形态请看 `approverGroups[]`（顶层与 `attr` 两份），别按节点顶层键误报。

**真机验证结果（临时应用「审批人验证-临时」，admin 发起）**：`roles=["部门经理"]` / `users=["admin"]` /
`appr(who="部门负责人")` 三种都起实例、进 admin 待办。`appr(who="上级部门负责人")`
（`getLevel1DepartLeaders`）**实例能起、但任务无办理人**——admin 的上级部门（北京国炬软件信息）没设负责人，
表达式解析为空人。**「上级部门负责人」不能当默认审批人**；要用就先确认发起人上级部门配了负责人，
否则改用租户里真实存在的角色（roleCode）。闸门看不见这一类（取决于运行时组织架构）。

---

## 8. 进销存真机反馈归总的五条（2026-09-20 实测）

**8.1 写字典 / 选项字段一律用「落库 value」，不是界面 label。**
触发条件比较、`updateFields` 赋值，只要目标是**绑了字典或静态选项**的字段，就必须写落库值。
写 label → ① 条件永不成立（**流程压根不触发**）；② 值写进去了但下拉里没这一项，**记录打开回显为空**。
→ 字典项的 `value` 与 `label` 通常是两个不同的值：建完字典先 `getDictListByLowAppId` **回读**每项 value，流程里引用回读到的 value。

**8.2 改库存的定位键 = `仓库编码` + `产品编码` 两个文本字段，且是 AND。**
匹配库存表一行 = **仓库编码 = 本行仓库编码 且 产品编码 = 本行产品编码**，两个都要匹配（不是或）。
→ **凡是流程要用到的表，都必须自带这两个字段**，且是「存储数据」（`saveType='save'`）——
产品编码从本行「选择产品」关联记录带出，仓库编码从所属单据带出。
→ 与之配套：库存表自己的 `仓库编码`/`产品编码` 也必须是**他表字段且 save**，否则没得比。

**8.3 改库存前先判「有没有这条记录」，再分两条路走。**
`get_one(库存表, cond=[仓库编码, 产品编码], empty="分支")` →
`data_branch(found=[update 累加/扣减], missing=[add 新建])`。
**新建那步必须把定位键（两个编码）连同名称一起写进去**（否则下次还是定位不到、无限新建）。
禁止用「未查到就自动新增」的隐式兜底替代这条显式分支；
也禁止只写 `get_one → update` 两节点了事（查不到时整条记账静默不执行）。

> ### ⚠️ `empty=` → `noDataType` 的落库口径（**以设计器为准**：继续=1 / 新增=2 / 中止=3）
>
> 权威出处 `miniflow_creator.build_get_one_node` 文首（2026-09-15 设计器源码实证）：
>
> | `noDataType` | 语义 |
> |---|---|
> | `1` | 继续执行（之后用到本节点对象的节点跳过） |
> | `2` | **在工作表中新增记录后继续执行**（仅 `selectType=1` 可选） |
> | `3` | 中止流程，或继续执行查找结果分支（配 `data_branch`） |
> | `0` | 未显式选择（默认） |
>
> ⛔ **`build_flows.py` 的 `get_one` 分支早先写的是 `{继续:0, 新增:1, 中止:2, 分支:3}` —— 整体错位一格。**
> 后果：`empty="中止"` 落成 `noDataType=2` =「**未查到就在工作表里新增一条空记录**后继续」。
> 2026-09-23 进销存实测：销售/采购的「数量回写」子流程每跑一次就往 `销售产品明细` /
> `采购订单产品明细` 各扔一条**空行**，8 轮冒烟攒了 16 条，而 `save` / `deploy` /
> `check_node_contract` / `app_audit` **全绿** —— 只有去数表里的行才发现。
> **已修**（映射改为 `继续=1 / 新增=2 / 中止=3 / 分支=3`）。
> `empty="分支"` 与「中止」同为 3，所以走 `data_branch` 的那条链一直是**对的**，
> 这也解释了为什么这个错位能藏这么久。
>
> **自查**：建完回读节点 `attr.noDataType`，与上表对一遍。

> ### ✅ 已结案（2026-09-21 源码定论）：「无数据」支不执行 = 网关**名字**不对
>
> **源码**：`BaseDataDelegate.noDataExecute()`（mindesflow-flowable，1074–1099 行）——`noDataType=3` 且取不到数据时，
> 只有下一节点是 Gateway **且 `name.equals(MiniDesConstant.DATA_BRANCH_NAME)`（= `"数据分支"`）** 才 `canStop=false` 继续；
> 否则 `stopProcessInstanceById` 终止实例、把 `BPM_STATUS` 置 3（已完成）并发一条消息。
> 设计器 `smart-flow-design-jeecg/packages/FlowNode/Add/index.vue:1107` 建该节点写死 `name: "数据分支"`，所以手工画的一直是对的；
> 技能 `flow_dsl.data_branch()` / `miniflow_creator.build_data_branch_gateway()` 当时默认名是**「数据判断」**，我们还传过自定义名。
> 这就是「missing 支一个节点都不跑、无报错、`bpm_status=3`」的全部解释。当时排查的 `content`/`emptyAction`/`noDataType` 都不是变量。
>
> **修法（2026-09-21 已落地）**：三处强制 `"数据分支"`（`flow_dsl`、`miniflow_creator`、`build_flows`），`flow_rules` 规则 1 改为校正名字，
> `check_node_contract` 对 `databranch.name != "数据分支"` 判违例。验证应用回归：原生 `data_branch` 首笔建库存行 + 第二笔累加均通过。
> 曾经的绕行形态「取多条→统计条数→判 0」仍可用 `build_flows --rewrite-databranch` 得到，不再默认。

**8.4 子流程里的 `data_add.formModel` / `data_update.updateFields` 每一项必须指向真实源节点。**

```jsonc
"<目标字段 model>": {
  "formNodeId":   "<产出该值的节点的 id>",     // 例如父流程的 data_get_more 节点
  "formNodeName": "<该节点的名字>",            // 例如「取产品需求明细」
  "formNodeType": "getMore",                   // table / search / getMore / plus / function
  "variableName": "<源字段中文名>",
  "variableValue": "<源字段 model>",
  "formTableCode": "<源表 code>",
  "fieldType":    "<源控件类型>"
}
```

引用父流程**刚新建**的记录 → 用「记录 id」传参形态
`{"variableName":"id","formNodeType":"variable","variableValue":"id"}`。
**禁止**写「从多节点数据触发」「工作表事件回显」这类**设计器下拉里根本不存在**的取数方式——
接口不报错，运行时取空值，链路跑成「什么都没发生」。

**8.5 「修改时触发」的流程必须设 `watch`（监控字段）。**
条件写「`库存已记账`=否 且 `XX确认`=是」之外，还要把**监控字段**设为那个 `XX确认` 字段，
保证**只在它变化的那一次**触发。否则用户每改一次单子就重跑一遍 → **重复记账**。

---

## 9. ★ 六个必须写死的形状（以本页为准，不要去别处找参照）

**本节是全篇优先级最高的一条。** 上面的键是「引擎认什么」，本节讲**「怎么保证你发出去的形状对」**。

**2026-09-20 实测事故（52 表进销存应用，`flow_dsl` 全自动生成）：**
`build_flows.py` 报「建 53 / 失败 0」，`save`/`deploy`/计数回读全绿，
**契约层却从头错到尾**——用户打开设计器一眼就看出「筛选条件的值不存在」「明明是单条却显示获取多条」
「更新对象不对」「更新值显示 `[object Object]`」。全部返工。

**规矩：下面这六个形状是本页写死的规格，照写即可。**

⛔ **不要采用「先找一份别人配好的同类流程/应用来仿」这种做法。**
**真实部署里不存在这样一个对照组**——线上没有现成的、可复现的、形态正确的参照流程，
只有用户自己这次要用的应用。把「对齐参照物」写进流程 = 把交付押在一个不存在的输入上。
（那次排查中出现的对照应用是**临时测试产物**，一次性、不可复现，不能当方法论。）
**唯一可复现的验收方式 = 生成后回读 `processJson`，逐节点对照本页 9.1 的清单。**

### 9.1 `flow_dsl` 自动生成的六个偏移（实测，逐条对照修）

| 项 | 正确形态（本页规格） | `flow_dsl` 生成 | 用户可见症状 |
|---|---|---|---|
| 子流程内取值来源 | `formNodeType: 'search'` + `formNodeId` = **父流程那个 get_more 节点 id**（= `formTableList` 中 `isSubStart:true` 那条的 `nodeId`）+ `formNodeName` = 别名 **`"子流程"`** | `table` + `formNodeId:"start"` + 「工作表事件触发」 | 气泡显示「**获取多条节点数据**」、设计器解析不到来源 |

> ⚠️ **这条有一个硬例外（2026-09-22 销售 R3 后端日志实证）**：上面的 `search` 形态只适用于
> **父流程的取多条节点在主链路上**的拓扑。取多条若**嵌在网关分支里**（inclusive/exclusive 的某一支），
> 它的结果存在**分支执行**的 redis key 下，子实例读不到 → 子流程里每个 `ref()` 都取空，
> 而 `save`/`deploy`/`app_audit`/`postbuild_verify` **全绿**，只有端到端冒烟抓得到。
> 那种拓扑下**必须保持 `table` + `formNodeId:"start"`**。
> `build_flows` 的回填趟已按「取数节点是否在分支里」自动区分（`_in_branch`），
> `check_node_contract` 规则 ⑥ 同口径放行；两边不再打架。
> 对照证据：进销存 29 条子流程（取多条在主链路）用 `search` 形态，冒烟 19/19 全过；
> 销售 1 条子流程（取多条在 inclusive 分支内）用 `search` 形态时 14 处 ref 全空，改回 `table/start` 立刻通过。
| `data_get_one.attr.formTableId` | `form_<本节点 id>_<formTableCode>` | `form_start_<formTableCode>` | 面板「选择更新对象」显示错 |
| `data_update.attr.formTableSourceTaskId` | 指向**前置 `data_get_one` 的节点 id**；配合 `formTableSourceNodeType: 'search'` | `'start'` / `'table'` | 更新节点选择的更新对象不对 |
| `data_update.attr.formTableId` | `form_<来源节点 id>_<formTableCode>` | `form_start_<code>` | 同上 |
| `updateFields[]` 条目 | `val` 是对象时必须带条目顶层 **`valueType: 3`** + `valType: 'variable'`；date 字段另带 `options.format`（gotchas #58） | 整个丢掉这两键 → 设计器按固定字面量解析 | 更新值一栏显示 **`[object Object]`** |
| 审批流结构 | `start → approver → data_update` 直连 | 套排他网关两支 | 更新节点被包在条件判断里 |

> ⚠️ **`formNodeType` 用数据源条目的 `nodeType`，不是 `nodeTypeMain`。**
> `formTableList[0]` 里 `nodeType: "search"`、`nodeTypeMain: "getMore"` ——
> 前者才是本节点在**本流程上下文**里的形态，用它才解析得到本行字段。

### 9.2 这六条已经修进生成器了 —— 不要再写「事后补丁」

**2026-09-20 已把上面六条逐条修进生成器本身**，不再需要「建完再拉回来改」的那道补丁：

| 偏移 | 修在哪 |
|---|---|
| ① 子流程取值源 `search` + 输入行 nodeId | `build_flows.py::_fix_sub_ownrow_refs()`，在**阶段③回填**里跟登记一起写（输入行的 nodeId 是从父流程调用节点拷来的，建子流程那一刻还不存在，所以只能在这一步改）。它同时把子流程里 `formTableSourceTaskId:"start"` 的 `data_update` 重指到输入行 |
| ② `get_one.formTableId` | `build_flows.py` get_one 分支**显式写死** `form_<本节点id>_<表code>`，不再靠 creator 推导 |
| ③④ `data_update` 的更新对象 | `flow_dsl.update()` 的 `source` 默认改成 `None` = **自动绑到前面最近的、取同一张表的 get_one**；需要更新触发行时显式 `source=START`（审批流就是这种） |
| ⑤ `updateFields` 的 `valType`/`valueType` | `miniflow_creator.build_data_update_node` 不再把它们**丢掉**（这是 `[object Object]` 的直接原因）。⚠️ **`valueType` 是 `3`**（val 是变量对象），与 gotchas #58/#603 一致；**不是 2** —— 条件行 `queryItems` 才是另一套口径，两者别混 |

**验收 = 跑闸门，不是跑补丁**：

```bash
python scripts/check_node_contract.py --api-base … --token … --tenant-id N --app-id A
```

§9.1 六条里，**②⑤ 和 ① 的「子流程内取值源」有闸门断言**：

| §9.1 条目 | 闸门断言 | 位置 |
|---|---|---|
| ① 子流程内取值源 | 子流程内 `formNodeType:'table'` + `formNodeId:'start'` 的取值源**按处数汇总报违例** | `check_extra` ⑥ |
| ② `get_one.formTableId` | 必须等于 `form_<本节点id>_<formTableCode>` | `check_flow` data_get_one 段 |
| ⑤ `updateFields` | `val` 为对象 → `valueType==3` + `valType=='variable'`；`formNodeType=='function'` 另需 `fieldType`/`operationMode`/`decimals`；date 字段需 `options.format` | `check_flow` data_update 段 |

⚠️ **③④（`data_update` 的更新对象指向）目前没有闸门** ——
`flow_dsl.update()` 的 `source` 自动绑定（`_auto_source`）保证发得对，
但**发错时闸门不会红**。要补的话应在 `check_flow` 的 `data_update` 段加：
`formTableSourceNodeType=='search'` 时 `formTableSourceTaskId` 必须解析到本流程里
真实存在的 `data_get_one`，且 `formTableId == form_<该id>_<formTableCode>`。

判据仍旧是 **违例 0 条**。

> ⛔ **不要退回「建完再用脚本改产物」那条路。**
> 它是本轮返工的真正代价来源：补丁脚本在流程外，漏跑一次就是整批流程错，
> 而 `save`/`deploy` 依然全绿。**形状对了要体现在生成器里，不是体现在补丁里。**
> 若某条偏移在新版本又出现，**改生成器 + 在 `check_node_contract.py` 加断言**，
> 两件事一起做；只做其中一件，下一轮一定复发。

```python
# 仅当引擎版本尚未含上述修复时，才照这个补丁思路兜底（步骤与 9.1 一一对应）：
#   ① 子流程：src = next(e for e in formTableList if e.get('isSubStart'))
#      凡 val 里 formNodeId == src['nodeId'] 的，formNodeType 一律置 'search'
#   ② data_get_one：formTableId = f"form_{node['id']}_{attr['formTableCode']}"
#   ③ data_update/data_add：顺序走过节点、记住最近一个 data_get_one 的 id，
#      formTableSourceTaskId 置为该 id、formTableSourceNodeType 置 'search'，
#      formTableId = f"form_{该id}_{formTableCode}"
#   ④ updateFields 里 val 是对象的条目，顶层补 valueType:3 + valType:'variable'
#      （date 字段另加 options:{format:'yyyy-MM-dd'}）；固定值条目不受影响
```

改完（无论走生成器还是补丁）**都要在设计器里打开看一眼节点面板**——
`save`/`deploy` 全绿、`check_node_contract` 全绿，**都不代表面板上显示对**。

### 9.3 连带：控件类型改了，流程里的类型副本要跟着改

把某个字典字段从 `select` 改成 `radio`（或把普通输入框改成他表字段 `link-field`）之后，
**已经建好的流程里存的是旧类型**（`conditions[].type`/`valType`、`updateFields[].type`/`fieldType`），
引擎按旧类型匹配 → 条件永不成立。做法：读线上 design 建 `model → type` 映射，
遍历所有流程回写这三/四个键，再按 #47 重存 + 重发布。
**改控件类型是「字段侧 + 流程侧」两处，只改一处就是静默故障。**

### 9.4 运算节点：`funContext` 条目的 `formNodeType` 必须是**来源节点的类型**

`function` 运算节点的 `funContext` 每个条目是 **8 键**（键序 field / formTableCode / formNodeId /
formNodeType / variableValue / formNodeName / tableText / fieldText，hash 规则见 gotchas #54），
其中 **`formNodeType` = 产出该值的那个节点的类型**，不是笼统的 `table`：

| 值来自 | `formNodeType` |
|---|---|
| 流程上下文行（触发记录） | `table` |
| `data_get_one` | `search` |
| `data_get_more` | `getMore` |
| `data_add` | `plus` |

**2026-09-22 实测事故（库存先进先出，`build_flows` 生成）：** 引用 `get_one` 结果的运算节点，
**每个条目都被写成 `"formNodeType": "table"`** → **运算结果恒为空** →
引用它的 `data_add.formModel` / `data_update.updateFields` **全部写空值**，
现象是「流程跑了，什么都没写」；而 `save` / `deploy` / `check_node_contract.py` **全绿**
（该闸门对 `function` 节点零覆盖，见 gotchas #90）。**属于 §9.1 同族的第七个偏移，且尚未修进生成器。**

**修法（外科 · 先自证再动手）：**

```python
# ① 自证口径：md5(解码后的 value) 必须等于现有 key，不等就是口径不同，中止
canon = urllib.parse.unquote(v)
assert hashlib.md5(canon.encode("utf-8")).hexdigest() == k, (k, "口径不符，中止")
# ② 改 formNodeType —— 按该条目 formNodeId 对应节点的真实类型（get_one→search / get_more→getMore / add→plus）
d = json.loads(canon); d["formNodeType"] = KIND[d["formNodeId"]]
# ③ 重编码 + 重算 key，并替换 funText 里的 {{旧key. 前缀
canon2 = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
new_key = hashlib.md5(canon2.encode("utf-8")).hexdigest()
new_fc[new_key] = urllib.parse.quote(canon2, safe=":,.-_/?")   # 编码风格同 #54
new_ft = new_ft.replace("{{%s." % k, "{{%s." % new_key)
```

⚠️ **改完必须 `save_flow` + `deploy_flow` 重发，再回读 `funContext` 逐条核对** ——
`funText` 占位符前缀、`funContext` 的 key、`md5(解码值)` 三者必须互相自洽。
（同 §9.3：**改控件类型后，流程侧那份类型副本也要跟着改**，两件事一起做。）

### 9.5 取值是**实时的**：`ref()` 读「求值那一刻的当前行」，不是触发时的快照

多节点链里，`ref("本行字段")` 与 `ref("字段", node=<get_one节点>)` 读到的都是
**已被前序节点改过的最新值**（2026-09-22 库存先进先出实测）。

**好处：「实时 min」写法成立**，不必把上一节点的运算结果串起来 ——

```python
# 扣减量 = min(本单剩余未发, 该批次现有库存)；两个 ref 都是当场最新值
compute("扣减量", "IF($剩余未发$ > $批库存$, $批库存$, $剩余未发$)",
        {"剩余未发": ref("剩余未发"), "批库存": ref("库存数量", node=批次节点)})
```

`compute` 的 `fields` **只吃 `ref()`**：写 `result("上一节点")` 会直接报
**「必须是 ref(...)，不能是固定值」**。

**坑（同一枚硬币的反面）：** 想拿「扣减**前**的原值」做减法（`原值 - 已扣`）会**算错**。
要原值只能**在扣减之前**用另一个运算节点先存下来。

⚠️ **跨批次公式尤其容易踩：** 不能写成 `min(A, ΣB) - min(A, ΣB_prev)` ——
引擎读实时当前值，Σ 会被自己前面的扣减污染（实测：该扣 20 却扣了 50）。
**逐批只写本批的 `min`，让链上每个节点各扣各的。**

---

## 自检（生成后必跑）

对每条新建流程：`queryById` → 解析 `processJson` → 按本页逐节点核对必填键，
**差异非空即失败**。`OK:done 建 N / 失败 0`、`全部启用` 都**不能**代替这一步。

> ⚠️ **核对前先确认「没有同名重复副本」（2026-09-20 实测踩坑）**：`query_flow(process_name=...)`
> 同名多条时**只返回最新一条**（见 SKILL.md「删除整条流程」），而按应用遍历的校验器（如
> `check_node_contract.py`）会把**所有**副本都查一遍。两者一旦指向不同副本，
> 症状是：**你改的和回读的都是新的那条（全对），校验器却持续报旧那条的违例** ——
> 极易误判成"校验器读错层/读了引擎侧副本"，然后在错误的假设上空转。
> 判别方法：**报违例的流程名跑一次 `query_flow` 拿 id，再和校验器覆盖的 id 集合比对**；
> 流程条数多于预期（如需求 9 条、应用里有 10 条）就是有副本。
> 成因通常是**建流脚本不幂等**：脚本崩在中途（部门不存在、字段解析失败等）后重跑，
> 第二次又建了一份 —— 建流脚本第一件事必须是查重跳过（见 `batch-flows.md`「幂等与失败处理」）。

> ⚠️ **子流程的 `formTableList` 条目不落在本流程的节点上（2026-09-20 实测）**：
> 子流程的「数据源」那条登记**指向父流程的 getMore 节点** ——
> 子流程侧 `{nodeId: <父流程节点id>, nodeType: "search", level: "1", isSubStart: true}`，
> 父流程侧**同一个节点 id** 另有 `level: "2"` 的一条。子流程的写回节点
> （`updateFields[].val.formNodeId`、`searchFieldGroup` 的条件）也一并指向它。
>
> 所以：**拿「本流程节点 id 全集」去判子流程登记条目是不是悬空，必然误报**。
> 校验器（`check_node_contract.py`）对这一档放行，只保留形态判据
> （`form_<节点id>_<表code>` 的表 code 段不能空）—— 那一条才抓得住真缺陷。
> 同理，`{nodeId: "processVariable", formTableId: "variable", nodeType: "variable"}`
> 是引擎自己登记的「流程参数」伪表，也不对任何节点，须一并豁免。


---

## 「更新记录」里写**日期字段**的口径（2026-09-21 实测）

**只能写系统变量对象**，且带 `options.format`：

```json
{"field": "date_xxx", "optType": "1", "fieldValue": "",
 "val": {"formNodeType": "system", "variableValue": "nowDate", "variableName": "当前日期"},
 "fieldType": "date", "type": "date",
 "valueType": 3, "valType": "variable", "options": {"format": "yyyy-MM-dd"}}
```

⛔ **不要**写 `"val": ""`（哪怕意图是「清空」）：
· 设计器里这一格显示 **invalid date**（用户一眼就能看出不对）；
· 运行期也不写库 —— 提交后字段还是原值。
要真「清空」字段，用设计器的「清空」选项（对应 `optType` 另一个取值），别拿空串凑。

验收：回读 `processJson` 的 `updateFields`，凡 `fieldType` 含 `date` 的，
`val` 必须是对象（系统变量/字段变量），不能是空串或裸字符串。
