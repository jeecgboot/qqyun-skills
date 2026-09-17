# 节点契约（生成流程前必读 · 从线上已跑通的流程实测提取）

> **这页回答一个问题：引擎到底认哪些键。**
> 助手函数「建出来了」≠ 引擎「读得懂」。save/deploy 全绿、回读计数也对，
> 但键没发出去 → 面板空白、运行时一行都不写。
>
> **用法**：写 `node_config` / 改 `build_flows` 之前，按本页核对目标节点的**必填键**。
> 校验方式只有一个 —— 生成后回读 `processJson`，与本页逐键对照。

约定：`attr.*` = 落在节点 `attr` 里的键；`(node)` = 落在节点**顶层**的键（别写进 attr）。

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
| attr | `collection` / `elementVariable` / `loopCardinality` / `isSequential` / `completionCondition` / `variableList` | 循环相关 |
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

**子流程侧的两个键是父流程 deploy 后回填的，不要手写**：
- 子流程 `formTableList[0]`（`isSubStart:true` + `nodeType:"search"` + `nodeTypeMain:"getMore"`，
  `nodeId`/`formTableId` 指向**父流程那条 getMore 节点**）—— 这就是子流程页的「数据源」。
- 子流程 `subFlowSourceInfo` ——「被以下工作流触发」的列表。

父流程的 `callActivity` 契约发对了，这两个才回填得上；父流程发歪 → 子流程页白屏、
触发列表为空。**验收时必须回读子流程确认它们非空**（本项目实测：63 条流程里只有 1 条回填上了）。

> **子流程页白屏 / 「被以下工作流触发」为空** = 同一件事：
> 子流程自己的 `subFormTableObject` 上下文 + 父流程回写的 `customProcessId` 都没登记。
> 见 `gotchas.md` #47 的发布配方。

## 3. 新增记录：`data_add` 必须写全 `formModel`

| 键 | 值 |
|---|---|
| `formModel` | **目标表每个要写的字段 → 取值**（不写 = 面板全空、运行时建空记录） |
| `addDataType` / `formType` / `noDataType` | |
| `formTableCode` / `formTableName` / `formTableId` | 目标表 |
| `formTableSourceNodeType` / `formTableSourceTaskId` | 取值来源节点 |
| `expressionType` / `expressionValue` | |

`formModel` 的取值形态（两种，别混）：

```jsonc
// ① 引用上游明细行的字段（跨子表引用）—— funText + funContext
"input_1701429216564_793751": {
  "funText": "{{<hash>.link_field_1697783086235_444204}}",
  "funContext": {"<hash>": "<URL 编码的 {field, formTableCode, ...}>"}
}
// ② 流程变量（如传进来的 record id）
"link_record_1701311092220_846556": {
  "variableName": "id", "formNodeType": "variable", "variableValue": "id"
}
```

## 4. 取单条：`data_get_one`

attr 必带 `searchFieldGroup`（筛选条件落在这里，**不在**顶层 `conditions`）、
`formTableSourceGetDataType`、`formTableSourceNodeType`、`formTableSourceTaskId`、
`sortField` / `sortType`、`selectType`、`formModel`；
选人/部门/角色字段另带 `userFormTableField` / `deptFormTableField` / `roleFormTableField`。

**筛选条件的取值来源**：用「获取单条节点数据 / 本流程参数」，
**不要**用「工作表事件回显」——后者在子流程里取不到父单据的值。

## 5. 更新：`data_update`

`attr.updateFields` = 完整条目数组（`field` / `val` / `fieldType` / `type` / `optType`）。
`optType`：`"1"` 设值 / `"2"` 增加 / `"3"` 减少。
`attr.formTableSourceNodeType` 指向取值来源（`search` / `getMore` / `table`）。

## 6. 分支：`databranch` / `exclusive`

节点**顶层** `conditionNodes`；`attr` 只有 `level`（`exclusive` 另有 `hasResultBranch`）。
分支 content 由引擎生成，不要手写。

## 7. 审批 / 填写：`edit`（`approver`）

节点顶层：`approverGroups` / `approverType` / `assigneeType` / `privileges` / `listenerData`。
attr（30+ 键，常用）：`approvalEnabled`、`formEditStatus`、`ccStatus`、`rejectStatus`、
`transferStatus`、`allowAddSign`、`skipApproval`、`selnextUserStatus`、`msgStatus`、
`sameMode`、`assigneeIsEmpty`、`timeType`/`timeDate`、`isSequential`、`ratio`、`level`。
**`content`（办理人显示名）非空**且不含 `$` / `assigneeBy`。
**字段权限不在 processJson 里**，走 `/act/process/extActProcessNodePermission/saveOrUpdateBatch`。

---

## 自检（生成后必跑）

对每条新建流程：`queryById` → 解析 `processJson` → 按本页逐节点核对必填键，
**差异非空即失败**。`OK:done 建 N / 失败 0`、`全部启用` 都**不能**代替这一步。
