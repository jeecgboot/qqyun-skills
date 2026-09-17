# 简流已踩坑汇总

> 遇到报错或前端异常时查阅。先 grep 报错原文或现象，只读命中项，不要从头通读。新建/改已有流程的正常路径见 `SKILL.md` 路由表，不要开场就读本文。

## 目录

1. [config.nodes 类型名别名](#1-confignodes-类型名别名)
2. [手动构建 ServiceTask 必须含委托表达式](#2-手动构建-servicetask-必须含委托表达式)
3. [节点 ID 时间戳格式](#3-节点-id-时间戳格式)
4. [startTaskId 必须与节点 ID 不同](#4-starttaskid-必须与节点-id-不同)
5. [意见分支标准用法](#5-意见分支标准用法)
6. [修改已有流程时注入意见分支](#6-修改已有流程时注入意见分支)
7. [suggest conditionNode 不含 errorContent](#7-suggest-conditionnode-不含-errorcontent)
8. [岗位审批人前端显示"设置此节点"](#8-岗位审批人前端显示设置此节点)
9. [手动构建分支网关必须加 addable=True](#9-手动构建分支网关必须加-addabletrue)
10. [并行分支 conditionNode 需要 content 字段](#10-并行分支-conditionnode-需要-content-字段)
11. [Desform 自定义按钮 flowStatus 必须为 true](#11-desform-自定义按钮-flowstatus-必须为-true)
12. [包含分支条件必须用 conditionGroup 格式](#12-包含分支条件必须用-conditiongroup-格式)
13. [包含分支聚合节点由脚本自动生成](#13-包含分支聚合节点由脚本自动生成)
14. [通知节点接收人禁止使用 toUserExpression](#14-通知节点接收人禁止使用-touserexpression)
15. [edit 节点发起人本人配置](#15-edit-节点发起人本人配置)
16. [dateFieldEvent 脚本已修复](#16-datefieldevent-脚本已修复)
17. [子流程节点踩坑汇总](#17-子流程节点踩坑汇总)
18. [审批结果分支上游节点 addable=False](#18-审批结果分支上游节点-addablefalse)
19. [timerEvent timeCycle 必须是字符串数字](#19-timerevent-timecycle-必须是字符串数字)
20. [timerEvent 结束时间必须写入 config](#20-timerevent-结束时间必须写入-config)
21. [包含分支意见分支 form_config 必须含表单字段](#21-包含分支意见分支-form_config-必须含表单字段)
22. [data_add 节点 formModel 格式](#22-data_add-节点-formmodel-格式)
23. [dateFieldEvent cycleType 枚举](#23-datefieldevent-cycletype-枚举)
24. [子表列权限 formBizCode 规则](#24-子表列权限-formbizcode-规则)
25. [inclusive + polymerize 双节点规范](#25-inclusive--polymerize-双节点规范)
26. [修改已有流程时手动拼分支节点 pid=null](#26-修改已有流程时手动拼分支节点-pidnull)
27. [databranch conditionNodes 必须用 EL 表达式](#27-databranch-conditionnodes-必须用-el-表达式)
28. [data_add 日期字段禁止用 EL 表达式覆盖系统当前日期](#28-data_add-日期字段禁止用-el-表达式覆盖系统当前日期)
29. [单实例子流程必须设置 subFormTableObject](#29-单实例子流程必须设置-subformtableobject)
30. [延迟节点：timeCycle 是模式选择器，预设外时长必须走 custom + timeDate](#30-延迟节点timecycle-是模式选择器预设外时长必须走-custom--timedate)
31. [子流程三层 startType 必须全为 subEvent](#31-子流程三层-starttype-必须全为-subevent)
32. [callActivity 关键字段必须在 attr 内部，customProcessId 必须是数据库 ID](#32-callactivity-关键字段必须在-attr-内部customprocessid-必须是数据库-id)
33. [assigneeByRole 必须同时填 roleNames，否则 UI 显示"未配置人员"](#33-assigneebyrole-必须同时填-rolenames否则-ui-显示未配置人员)
34. [互斥分支 select 字段条件必须用 type/valType="select"，审批节点 attr 必须含表单来源](#34-互斥分支-select-字段条件必须用-typevalTypeselect审批节点-attr-必须含表单来源)
35. [opinion 节点 ID 必须用 suggest_ 前缀，禁止用 Gateway 前缀](#35-opinion-节点-id-必须用-suggest_-前缀禁止用-gateway-前缀)
36. [网关节点禁止嵌套在另一个网关的 conditionNodes 内](#36-网关节点禁止嵌套在另一个网关的-conditionnodes-内)
42. [删除简流流程记录：DELETE /act/process/extActProcess/delete?id=；无法删除时用「改名挪移法」停用兜底](#42-删除简流流程记录delete-actprocessextactprocessdeleteid无法删除时用改名挪移法停用兜底)
43. [引擎定义核验口径：主流程 key=记录 processKey，只有 subEvent 子流程才是 process<DBid>](#43-引擎定义核验口径主流程-key记录-processkey只有-subevent-子流程才是-processdbid)
44. [API 写入数据同样触发 tableEvent 简流；date 落库格式判定](#44-api-写入数据同样触发-tableevent-简流date-落库格式判定)
45. [子流程 get_one「查询入库单」按 link-record 变量查 `_id` 反复查不到：XML 缺 MiniSubProcessStartListener 因果链 + 修复（2026-09-03 仓储实测）](#45-子流程-get_one查询入库单按-link-record-变量查-_id-反复查不到xml-缺-minisubprocessstartlistener-因果链--修复2026-09-03-仓储实测)
46. [data_add「添加记录」link-record 字段（仓库）新增行一直为空/被丢弃：JSON formModel 正确仍需 UI 重配节点映射（2026-09-03 仓储实测）](#46-data_add添加记录link-record-字段仓库新增行一直为空被丢弃json-formmodel-正确仍需-ui-重配节点映射2026-09-03-仓储实测)
47. [subEvent 子流程 API 发布"不生效"真根因：deploy 实际注册了但缺 customProcessId 字段→定义 key 拼错（#33/#33a/"必须 UI 发布"结论更正，2026-09-03 实测）](#47-subevent-子流程-api-发布不生效真根因deploy-实际注册了但缺-customprocessid-字段定义-key-拼错3333a必须-ui-发布结论更正2026-09-03-实测)
48. [api/aiOrchestration 手动构造的三个坑 + 禁用类型清单](#48-apiaiorchestration-手动构造的三个坑--禁用类型清单)
51. [字典选项字段触发条件值必须写 itemValue，写中文 label UI 显示"未选中"](#51-字典选项字段checkbox-多选框触发条件值必须写-itemvalue写中文-label-ui-显示未选中)
53. [switch（开关）控件触发条件值 = activeValue 字符串](#53-switch开关控件触发条件值--activevalue-字符串)
54. [queryById 返回的 processJson 是 JSON 字符串，回读前必须 json.loads](#54-querybyid-返回的-processjson-是-json-字符串回读前必须-jsonloads)
61. [组织查询条件值跨租户陷阱：部门树与角色列表必须按当前租户过滤（2026-09-09 实测）](#61-组织查询条件值跨租户陷阱部门树与角色列表必须按当前租户过滤2026-09-09-实测)

> 注：目录 37–41 为文档演进遗留编号，正文含 #40 / #41，不影响使用。

---

## 1. config.nodes 类型名别名

`config.nodes` 中使用脚本别名，写成 processJson 内部类型名会抛 ValueError。

| config 别名（✅） | processJson 类型 | ❌ 错误写法 |
|---|---|---|
| `time` | `timer_event` | `timer_event` |
| `operation` | `function` | `function` |
| `data_branch` | `databranch` | `databranch` |
| `upvariable` | `data_update_variable` | — |
| `subprocess` | `callActivity` | — |

---

## 2. 手动构建 ServiceTask 必须含委托表达式

手动构建任何 ServiceTask 类节点时，`attr` 中必须包含 `expressionType` 和 `expressionValue`，否则 Flowable 部署报 `flowable-servicetask-missing-implementation`。

> 脚本的 `build_*` 函数已内置委托表达式；此规范仅针对绕过脚本直接手动拼接 dict 的情况。

```python
"expressionType": "delegateExpression",
"expressionValue": "${对应Delegate名}"
```

| 节点 type | expressionValue |
|-----------|----------------|
| `data_get_udr_one` | `${getUserDeptRoleOneDelegate}` |
| `data_get_udr_more` | `${getUserDeptRoleMoreDelegate}` |
| `data_update` | `${updateRecordDelegate}` |
| `data_add` | `${addRecordDelegate}` |
| `data_delete` | `${deleteRecordDelegate}` |
| `data_get_one` | `${getOneRecordDelegate}` |
| `data_get_more` | `${getMoreRecordDelegate}` |
| `function` | `${functionDelegate}` |
| `data_update_variable` | `${updateVariableDelegate}` |
| `message_system` / `message_ding` / `message_email` / `message` | `${messageDelegate}` |

---

## 3. 节点 ID 时间戳格式

`gen_id()` 生成的 UUID 类 ID 会导致服务端 mxGraph 渲染解析失败。

```python
ts = int(time.time() * 1000)

# ✅ 正确：时间戳格式，后缀递增区分各节点
edit_id        = f'task{ts}001'
approver_id    = f'task{ts}002'
suggest_id     = f'suggest_{ts}003'
btn_agree_id   = f'flow{ts}004'
btn_reject_id  = f'flow{ts}005'
parallel_id    = f'Gateway{ts}006'
polymerize_id  = f'Gateway{ts}007'
group_id       = f'group{ts}012'

# ❌ 错误
edit_id = gen_id('task')
```

---

## 4. startTaskId 必须与节点 ID 不同

**现象：** `save_flow` 返回 500，`Duplicate key task…`（attempted merging values ChildNode…）。

**根因：** `startTaskId` 与某个节点（通常是第一个 childNode）ID 相同，服务端按 ID 合并节点时冲突。

`startTaskId` 是开始任务的独立 ID，**不是**第一个业务节点的 ID。

```python
ts = int(time.time() * 1000)
config = {
    'startTaskId': f'task{ts}000',   # 只给 startTaskId
    'nodes': [
        {'type': 'get_one', 'id': f'task{ts}001', ...},  # 节点从 001 起
    ],
}

# ❌ 错误：与第一个节点相同 → Duplicate key
config['startTaskId'] = f'task{ts}001'
process_json['startTaskId'] = process_json['childNode']['id']
```

---

## 5. 意见分支标准用法

直接在 `config.nodes` 使用 `"type": "opinion"`，后续节点放入 `conditionNodes[].nodes`：

```python
# ✅ 正确
{"type": "opinion", "name": "意见分支",
 "conditionNodes": [
     {"name": "同意", "nodes": [{"type": "approver", ...}]},
     {"name": "不同意", "nodes": []},
 ]}

# ❌ 错误：手动构建 suggest 注入 → mxGraph 渲染报 getAbsolutePoints() null
suggest_node = {'id': ..., 'type': 'suggest', 'conditionNodes': [...]}
approver_node['childNode'] = suggest_node
```

---

## 6. 修改已有流程时注入意见分支

> ⚠️ 此场景极易连续踩两个坑，必须按以下步骤执行。

| 错误 | 现象 | 原因 |
|------|------|------|
| 手动构建 suggest dict 注入 | `getAbsolutePoints() null`，保存失败 | 缺少 mxGraph 兼容细节 |
| `build_opinion_gateway` 缺 `parent_id` | `getPid() is null`，保存失败 | suggest 节点必须有 pid |

```python
from miniflow_creator import build_opinion_gateway

suggest_node = build_opinion_gateway(
    {
        'name': '意见分支',
        'type': 'opinion',
        'conditionNodes': [
            {'name': '同意', 'nodes': [...]},
            {'name': '不同意', 'nodes': []},
        ]
    },
    form_config,       # 必须包含 formTableCode/formTableName/formTableId
    level=3,
    parent_id='目标审批节点ID'   # ← 必须传！
)

# 注入到目标审批节点的 childNode
find_and_inject(pj, '目标审批节点ID', suggest_node)
```

---

## 7. suggest conditionNode 不含 errorContent

意见分支的按钮节点（type=8）**不能包含 `errorContent` 字段**：

```python
# ✅ 正确（无 errorContent）
{"id": btn_id, "pid": suggest_id, "name": "同意", "type": 8,
 "attr": {"priorityLevel": 2}, "status": -1,
 "childNode": ..., "addable": True, "deletable": False, "error": False}

# ❌ 错误
{..., "error": False, "errorContent": ""}  # errorContent 不能出现在 type=8 节点
```

---

## 8. 岗位审批人前端显示"设置此节点"

使用 `candidatePosts` 指定岗位审批人时，前端节点卡片会显示"设置此节点"而不是岗位名称。

**原因：** `_get_approver_content()` 原本漏掉了 `postNames`，导致 `content` 字段为空。

**已修复（2026-04-17）：** 脚本已补加 `postNames`，直接使用脚本即可。遇到其他类型审批人卡片显示"设置此节点"，检查 `_get_approver_content()` 是否覆盖了该类型的名称字段。

---

## 9. 手动构建分支网关必须加 addable=True

排他/并行/包含网关在**手动构建 processJson** 时，gateway 节点本身必须显式设置 `"addable": True`，否则前端不渲染分支内的 "+" 插入按钮。

```python
# ✅ 正确
exclusive_node = {'id': gateway_id, 'type': 'exclusive', 'addable': True, ...}

# ❌ 错误（前端分支内无 "+" 按钮）
exclusive_node = {'id': gateway_id, 'type': 'exclusive'}  # 无 addable
```

> 脚本 `build_exclusive_gateway`、`build_parallel_gateway`、`build_inclusive_gateway` 已自动处理此字段，只有手动拼 gateway dict 才会踩此坑。

---

## 10. 并行分支 conditionNode 需要 content 字段

```python
# ✅ 正确
{
    "id": branch1_id, "pid": parallel_id, "name": "邮件通知", "type": 10,
    "attr": {"branchType": 2, "conditionGroup": [], "level": "3", "showPriorityLevel": False},
    "childNode": email_node,
    "content": "邮件通知(并行)",  # ← 需要 content 字段
    "errorContent": None,         # ← errorContent 设为 None（不是空字符串）
    "addable": True, "deletable": False, "error": False, "status": -1
}
```

---

## 11. Desform 自定义按钮 flowStatus 必须为 true

`POST /desform/button/save` 必须传 `flowStatus: true`，否则报 `"操作失败，Id must not be null"`。

另外，`confirmText` 必须是 JSON 对象，不能是序列化字符串：

```python
'confirmText': {'tip': '确认？', 'ok': '确定', 'cancel': '取消'}  # ✅
'confirmText': '{"tip":"确认？",...}'                              # ❌
```

---

## 12. 包含分支条件必须用 conditionGroup 格式

禁止在包含分支的 conditionNodes 中使用简写 `conditions` 数组，必须使用完整 `conditionGroup` 格式，且满足：

| 要求 | 错误写法 | 正确写法 |
|------|---------|---------|
| 条件格式 | `"conditions": [{...}]` | `"conditionGroup": [{"id":..., "queryItems":[...]}]` |
| val 类型 | `"val": 10000`（数字） | `"val": "10000"`（字符串） |
| name 字段 | `"name": null` | `"name": "合计金额"`（字段标签） |

conditionNode 还必须同级提供 `branchForm` 和 `formTableCode`。

> ⚠️ 不要把兜底分支（isDefault=true）当作"其他情况"，应为每个分支设明确条件。

---

## 13. 包含分支聚合节点由脚本自动生成

`build_process_json` 会自动在 `inclusive` 的 `childNode` 中生成 `inclusive_end` 聚合节点，**无需也不能手动插入**。

```python
# ✅ 正确：直接 save，不做额外处理
process_json = build_process_json(config)
result = save_flow(api_base, token, config, process_json)

# ❌ 错误：手动再插入聚合节点 → 前端出现两个聚合图标
inclusive_node['childNode'] = {"type": "polymerize", ...}
```

> `inclusive` 的聚合类型是 `inclusive_end`；`parallel` 的聚合类型是 `polymerize`，两者不可混用。

---

## 14. 通知节点接收人禁止使用 toUserExpression

`toUserExpression: "${applyUserId}"` 在通知节点中无效。必须用 `toUserIds` 指定：

```python
# ✅ 正确
{"toUserIds": ["user.admin", "role.dept_manager", "dept.{deptId}"],
 "toUserNames": ["admin", "部门经理", "某部门"]}

# ❌ 错误（消息不会发出）
{"toUserExpression": "${applyUserId}", "toUserIds": []}
```

**toUserIds 格式：** `user.{username}`、`role.{roleCode}`、`dept.{deptId}`

---

## 15. edit 节点发起人本人配置

`approverType: "myself"` 在编辑节点上不稳定，前端可能显示"未设置"。必须改用表达式：

```python
# ✅ 正确
{"type": "edit", "approverType": "candidateUser", "assigneeType": "assigneeByExp",
 "approverGroups": [{
     "approverType": "candidateUser", "assigneeType": "assigneeByExp",
     "expressionsIds": ["${applyUserId}"], "expressionsNames": ["获取发起人"],
 }]}

# ❌ 错误（前端显示"未设置"）
{"approverType": "myself", "assigneeType": "myself", "approverGroups": [{"approverType": "myself"}]}
```

---

## 16. dateFieldEvent 脚本已修复

脚本已于 2026-04-17 修复对 `dateFieldEvent` 的支持（`_start_node_name_map`、`_table_node_types`、`start_attr` 均已更新）。直接在 config 中传入完整参数即可，无需手动 patch processJson。

若创建后前端触发方式仍显示空，手动 patch：

```python
attr['startType'] = 'dateFieldEvent'
attr['formTableCode'] = form_table_code
attr['formTableId'] = f'form_start_{form_table_code}'
attr['triggerField'] = trigger_field_id
attr['triggerFieldType'] = 'date'
attr['executeType'] = 2
attr['plusDate'] = 1
attr['plusDateUnit'] = 3
attr['executionTime'] = '08:00'
```

---

## 17. 子流程节点踩坑汇总

| 坑 | 错误写法 | 正确写法 |
|----|---------|---------|
| 节点类型 | `"type": "subprocess"` | `"type": "callActivity"` |
| 节点 ID 前缀 | `task{ts}001` | `Activity{ts}001` |
| `subFormTableObject` 为空 | `null` → NullPointerException | 必须是有效 JSONObject |
| `processId` 未填 | `""` → 前端🔗打开子流程显示空 | 填子流程 DB ID |
| 子流程 `formTableList` 为空 | `[]` → 设计器无法识别表单上下文 | 填对应表单条目 |
| 子流程 startType（三层） | 任一层为 `"manual"` | 三层全部为 `"subEvent"`，见 #31 |
| 父流程缺 `subFlowList` | 未设置 → 关联不完整 | `process_json['subFlowList'] = [{"subProcessId": ..., "subNodeName": ...}]` |
| `calledElement`/`customProcessId` 位置 | 放在节点顶层 | 必须在 `attr` 内部，见 #32 |
| `attr.customProcessId` 值 | processKey 后缀（如 `"1776xxx001"`） | 子流程数据库实际 ID（如 `"2046445818582962178"`），见 #32 |

---

## 18. 审批结果分支上游节点 addable=False

手动构建 `approve_result` 后，必须将上游审批节点 `addable=False`，否则节点间可插入新节点，导致流程结构错误。

---

## 19. timerEvent timeCycle 必须是字符串数字

`attr.timeCycle` 和 config 级 `timeCycle` 必须是**字符串数字**（如 `"3"`），不是名称（`"每天"`），不是整数（`3`）。

```python
"timeCycle": "3"   # ✅ 每天
"timeCycle": 3     # ❌ 数字，前端无法解析
"timeCycle": "每天" # ❌ 名称，无效
```

同时需设置 `attr.beginDate`（首次执行日期）。

---

## 20. timerEvent 结束时间必须写入 config

用户说"到XX结束"时必须在 config 中加 `endDateStr`：

```python
config['endDateStr'] = '2026-12-31 23:59:59'  # ✅
# 不能只靠 cron 表达式控制时间范围
```

---

## 21. 包含分支意见分支 form_config 必须含表单字段

`build_opinion_gateway` 的 `form_config` 必须包含 `formTableCode`/`formTableName`/`formTableId`，缺失导致内部审批节点表单字段为空：

```python
form_table_code = pj.get('attr', {}).get('formTableCode', '')
form_config = {
    'formTableCode': form_table_code,
    'formTableName': pj.get('attr', {}).get('formTableName', ''),
    'formTableId': pj.get('attr', {}).get('formTableId', f'form_start_{form_table_code}'),
}
```

---

## 22. data_add 节点 formModel 格式

`data_add` 节点 `attr` 使用 `formModel` 字典（key=目标字段 ID），不是 `addFields` 列表：

```python
# ✅ 正确
{"type": "data_add", "attr": {
    "formModel": {
        "input_fieldId1": "固定值",
        "select_fieldId2": "${变量}"
    }
}}

# ❌ 错误（旧格式，脚本已修复）
{"type": "data_add", "attr": {"addFields": [{"field": ..., "val": ...}]}}
```

---

## 23. dateFieldEvent cycleType 枚举

`1`=不重复 / `2`=每年 / `3`=每月 / `4`=每周，每周重复必须用 `4`（不是 `"week"` 或其他）。

---

## 24. 子表列权限 formBizCode 规则

子表列权限的 `formBizCode` 必须用**主表名**，不能用子表名。`ruleCode` 格式为 `子表Key前缀:columnKey`。

---

## 25. inclusive + polymerize 双节点规范

手动构建 inclusive 分支时，必须同时设置：
- `polymerize.pid = inclusive.id`
- 下游节点 `.pid = polymerize.id`

缺少任意一个会导致前端 NPE（空指针）报错。

---

## 26. 修改已有流程时手动拼分支节点 pid=null

**现象：** `save_flow` 返回 500，报错 `Cannot invoke "String.indexOf(String)" because the return value of "ChildNode.getPid()" is null`。

**根因：** 直接手动构建分支类节点（opinion/exclusive/parallel/inclusive）的 dict，忘记设置 `pid` 字段。简流每个节点都必须有 `pid` 指向父节点，否则后端解析时 NPE。

| 节点 | 必须设置的 `pid` |
|------|----------------|
| 分支网关节点本身 | 父节点 ID |
| 每个 conditionNode | 分支网关节点 ID |
| conditionNode 内的子节点 | 所在 conditionNode 的 ID |

**解决：** 修改已有流程时，分支类节点必须通过脚本的 `build_*` 函数生成（如 `build_opinion_gateway`、`build_exclusive_gateway` 等），不可手动拼 dict——`build_*` 函数会自动递归设置所有 `pid`。

```python
# ✅ 正确：用脚本函数，pid 自动处理
opinion_node = build_opinion_gateway(opinion_config, form_config, level=2, parent_id=approver_id)

# ❌ 错误：手动拼 dict，pid 缺失 → 500 getPid() is null
opinion_node = {"type": "suggest", "id": "...", "conditionNodes": [...]}  # 没有 pid
```

---

## 30. 延迟节点：`timeCycle` 是**模式选择器**，预设外时长必须走 `custom` + `timeDate`

**现象：** 设计器打开延迟节点，抽屉里「定时类型=指定一个时间段之后执行」正常，但**「执行时间」整排单选框一个都没选中、下方没有输入框**；用户判定"没设置上"，手工重设后链路才通。**2026-09-10 用户实测（供应商准入会签「延时30分钟」）**。

**根因（2026-09-10 用户手工修复 + 设计器源码双重实证）：** 弹窗「执行时间」是**单选组**，它把 `attr.timeCycle` 的值和 5 个写死的 token 逐一比对来决定选中项——**只有下面 5 个值能命中，其余任何值 → 一个都不选中 → 输入框也不渲染**：

| UI 选项 | `attr.timeCycle` 绑定值 | 备注 |
|---|---|---|
| 1分钟后 | `PT1M` | 分钟必须带 `T`（与「一个月后」`P1M` 区分） |
| 1小时后 | **`P1H`** | ⚠️ **不是** `PT1H`——加 `T` 前端无法识别、整排不选中 |
| 1天后 | `P1D` | |
| 一个月后 | `P1M` | |
| **自定义** | **`custom`** | 值写进 `timeDate`，见下方 custom 契约 |

> ⚠️ **合并留痕（2026-09-10）**：本节一度出现两张重复 token 表，其中一张把「1小时后」写成 `PT1H`（与另一张的 `P1H` 直接矛盾），系两支改动同日各自新增、合并去重不彻底所致。**以本表为唯一准绳**——`timeCycle` 槽只认 `P1H`，`PT1H` 永远不会出现在 `timeCycle` 里。

```python
# ✅ 命中 UI 预设 —— 值直接放 timeCycle，timeDate 为 None
{"timeType": "timeDuration", "timeCycle": "PT1M", "timeDate": None}  # 1分钟后
{"timeType": "timeDuration", "timeCycle": "P1H",  "timeDate": None}  # 1小时后
{"timeType": "timeDuration", "timeCycle": "P1D",  "timeDate": None}  # 1天后
{"timeType": "timeDuration", "timeCycle": "P1M",  "timeDate": None}  # 一个月后

# ✅ 预设外时长 —— 必须 custom + timeDate（UI「自定义」选项）
{"timeType": "timeDuration", "timeCycle": "custom", "timeDate": "PT30M"}   # 30分钟
{"timeType": "timeDuration", "timeCycle": "custom", "timeDate": "PT2H30M"} # 2小时30分
{"timeType": "timeDuration", "timeCycle": "custom", "timeDate": "P7D"}     # 1周
{"timeType": "timeDuration", "timeCycle": "custom", "timeDate": "P14D"}    # 2周

# ✅ 指定时间点（定时类型=指定时间触发）—— timeCycle 为 None
{"timeType": "timeDate", "timeDate": "2026-04-20T23:23:00", "timeCycle": None}

# ✅ 自定义 —— 相对时长（下拉无所需档位时，如「3分钟后」）
{"timeType": "timeDuration", "timeCycle": "custom", "timeDate": "PT3M"}

# ✅ 自定义 —— 绝对时间点
{"timeType": "timeDuration", "timeCycle": "custom", "timeDate": "2026-04-20T23:23:00"}

# ❌ 错误：把时长写进 timeCycle 枚举位（非 5 档枚举值 → 前端显示为空）
{"timeCycle": "PT1H"}   # 想表达"1小时后"应写 timeCycle:"custom" + timeDate:"PT1H"
{"timeCycle": "PT5M"}   # 同上，非枚举值一律显示为空
```

> ⚠️ **custom 档的取值契约（2026-09-10 用户口述规则）：** 下拉只有 5 个档位，需要「3分钟后」这种**非枚举时长**时，选**自定义**，把时长按 **ISO 时长字符串**写进 **`timeDate`**（如 `"PT3M"`）——**不是**把具体时刻算出来写进去（写具体时间点语义就变成"某时刻执行"，且写入时刻+3min 是死值，不是每次运行时相对等 3 分钟）。即：`timeCycle` 仍写 `"custom"`，`PT3M` 是被"自定义"选中的那个值，**不要**写成 `timeCycle:"PT3M"`（非枚举 → 前端显示为空）。节点 attr 只需 `timeType/timeCycle/timeDate`，勿自造 `customValue`/`customUnit` 之类的辅助键。

> **📌 本条证据等级：API 侧已验，UI 原生样本待确认（2026-09-10 复核）。** 全租户 109 条流程中**仅 4 个延时节点，且 4 个全部由 API 写入**——「`custom` + ISO 时长串」目前只有三方自洽（用户口述规则 + API 落库回读 + 脚本 `build_time_node` 实现），**没有任何设计器 UI 原生落库样本**；唯一含「自定义」的原生样本（`example/填写延迟java脚本节点.md` 的延时节点示例）其 `timeCycle:"custom"` 配的是**绝对时间点** `2026-04-15T12:13:14`，原文注释亦为「custom 模式下 timeDate 存的是用户填的值」。故**首次**用此形态建节点后，应请用户在设计器里打开该节点确认「执行时间=自定义」且输入框有值，再据反馈收敛。**对照**：「四预设 token」与「指定时间点」两种形态已有生产落库实证。

**「自定义」输入框里该填什么（ISO 8601 时长，用户提供权威规则 2026-09-10）：** 语法 `P[n]Y[n]M[n]DT[n]H[n]M[n]S`——`P` 开头；`T` 之前 `Y/M/D`=年月日；`T` 之后 `H/M/S`=时分秒；**时分秒必须带 `T`**。

> ⚠️ **本表只管 `timeDate`（选中「自定义」后才出现的输入框），与上一张表的 `timeCycle` 枚举位是两套值、勿互串**——下表「❌ 错误」的含义是**写进 `timeDate` 会错**，并非说它在 `timeCycle` 里对。

| 含义 | ✅ 写进 `timeDate` | ❌ 写进 `timeDate` 的错误写法 |
|---|---|---|
| 30分钟 | `PT30M` | `P30M`（分钟在 T 之后） |
| 1小时 | `PT1H` | `P1H`（`P1H` 是 `timeCycle` 的预设 token，**不是** ISO 时长） |
| 2小时30分 | `PT2H30M` | `PT1H30`（分钟要带 `M`） |
| 1天 | `P1D` | `P`（P 后必须有值） |
| 3天4小时30分 | `P3DT4H30M` | — |
| 1年6个月 | `P1Y6M` | — |

⚠️ **`M` 出现两次**：`T` 之前是"月"（`P2M`=2个月），`T` 之后是"分钟"（`PT2M`=2分钟）。⚠️ 下拉枚举 token（`P1H`/`PT1M`/`P1D`/`P1M`/`custom`）是**另一套**，只用于 `timeCycle` 槽；写进 `timeDate` 的自定义值必须是标准 ISO（下拉的「1小时后」token 是 `P1H`，而自定义里写"1小时后"要写 `PT1H`）——两者勿混。

官方文档：<https://help.qiaoqiaoyun.com/flow/node/time.html>（2.2 速查表讲的正是**「自定义」输入框里该填什么**，别误当成 `timeCycle` 的合法取值表——旧结论就是在这里踩的。）

⚠️ **回读断言必须查 `attr.timeCycle` 与 `attr.timeDate` 两者**：只比对"我写进去的值还在不在"是自证循环（写错了照样能读到写错的值），要按"预设 token 白名单 / custom+ISO 串"这个**形态**去断言。

脚本侧：`build_time_node` 已按本契约重写——传 `duration`（或 `attr.timeDate`）后自动分流：命中四预设 → `timeCycle=<预设>`；否则 → `timeCycle="custom"` + `timeDate=<ISO>`。旧的 `_TIMER_CYCLE_ISO_MAP` / `_TIMER_CYCLE_CODE_MAP` 只管**定时触发流程的调度周期**（startType=timerEvent），与延迟节点无关，勿混用。（函数名为 `build_time_node`——旧文本提到的 `build_timer_event_node` 并不存在，调用会 ImportError。）

---

## 27. databranch conditionNodes 必须用 EL 表达式

脚本 `build_data_branch_gateway` 原先生成的 conditionNodes 结构有误，与运行时期望不符，导致前端显示不正确且分支判断失效。

**错误结构（旧）：**

```python
"isDefault": i > 0,          # 有数据分支 isDefault=False，无数据 isDefault=True
"branchType": 2 if i > 0 else 1,
"showPriorityLevel": False,
"content": branch_name + "进入此流程",  # 纯文本，无法被引擎识别
```

**正确结构：**

```python
"isDefault": False,           # 两个分支均为 False
"branchType": 2,              # 两个分支均为 2
"showPriorityLevel": True,
"content": "${flow_has_data==1}",   # 有数据分支（index 0）
# 或
"content": "${flow_has_data==0}",   # 无数据分支（index 1）
"errorContent": None,
```

> 脚本 `build_data_branch_gateway` 已于 2026-04-20 修复，直接使用脚本即可。

---

## 28. data_add 日期字段禁止用 EL 表达式覆盖系统当前日期

`data_add` 节点 `formModel` 中，日期字段（type=`date`）的默认值**不能**使用 `${now()}`、`${dateAdd(...)}` 等 EL 表达式——这些函数在 data_add 委托的执行上下文中不存在，写入后字段值为空或报错。

若字段在 desform 表单中配置了 `"defaultValueType": 1`（系统当前日期），只需在 `formModel` 中设置为 `""` 或**不包含该字段**，表单自身会自动填入当前日期：

```python
# ✅ 正确：留空，由表单 defaultValueType=1 自动填当前日期
"formModel": {
    "date_xxx": "",   # 或直接不写这个 key
}

# ❌ 错误：EL 表达式在 data_add 上下文中不可用
"formModel": {
    "date_xxx": "${now()}",
    "date_yyy": "${dateAdd(now(), 7, 'day')}",
}
```

---

## 31. 子流程三层 startType 必须全为 subEvent

**现象：** 子流程被调用后执行异常，或前端显示触发方式不正确。

**根因：** 子流程的 `startType` 存在**三个独立层级**，必须全部设置为 `"subEvent"`：

| 层级 | 说明 | 错误值 |
|------|------|--------|
| 数据库记录层 | `save_flow` 的 config 中 `startType` | `"manual"` |
| processJson 顶层 | `process_json['startType']` | `"manual"` |
| processJson.attr 层 | `process_json['attr']['startType']` | 通常已为 `"subEvent"`，但需确认 |

**正确写法：**

```python
# 三层都必须是 subEvent
config = {
    'processName': '批量修改库存',
    'processKey': f'process{ts}S001',
    'processType': 'oa',
    'lowAppId': '<lowAppId>',
    'startType': 'subEvent',          # ← 层级1：数据库记录层
}
process_json = build_process_json(config)
process_json['startType'] = 'subEvent'       # ← 层级2：processJson 顶层
# 层级3：build_process_json 对 subEvent 会自动设置 attr.startType，确认即可
```

**修复已有子流程（三层统一修正）：**

```python
rec = query_flow(api_base, token, process_key)
pj = json.loads(rec['processJson'])
pj['startType'] = 'subEvent'          # 修正顶层
pj['attr']['startType'] = 'subEvent'  # 修正 attr 层（通常已正确）
cfg = {
    'processName': rec['processName'], 'processKey': rec['processKey'],
    'processType': 'oa', 'lowAppId': rec['lowAppId'],
    'startType': 'subEvent',           # 修正数据库记录层
}
save_flow(api_base, token, cfg, pj, flow_id=rec['id'], update_count=rec['updateCount'])
deploy_flow(api_base, token, rec['id'])
```

---

## 32. callActivity 关键字段必须在 attr 内部，customProcessId 必须是数据库 ID

**现象：** 父流程保存成功，但子流程无法被调用；前端"执行流程"节点显示异常。

**根因一：字段位置错误**

`calledElement`、`customProcessId`、`subFormTableObject` 这三个字段**只能存在于 `attr` 内部**，放在节点顶层无效且会造成混乱：

```python
# ✅ 正确：在 attr 内
callactivity_node = {
    "id": "Activity{ts}001",
    "type": "callActivity",
    "attr": {
        "calledElement":    "process1776745678798S001",  # 子流程 processKey
        "customProcessId":  "2046445818582962178",       # 子流程数据库 ID
        "subFormTableObject": {...},
        ...
    }
}

# ❌ 错误：放在节点顶层（无效，且污染结构）
callactivity_node = {
    "id": "Activity{ts}001",
    "type": "callActivity",
    "calledElement": "...",     # ← 顶层无效
    "customProcessId": "...",   # ← 顶层无效
    "attr": {...}
}
```

**根因二：customProcessId 值错误**

`attr.customProcessId` 必须是子流程的**数据库实际 ID**（整数字符串），不是 processKey 的后缀：

```python
# 子流程信息示例：
#   processKey = "process1776745678798S001"
#   数据库 ID  = "2046445818582962178"（从 save_flow 返回值或 extActProcess/list 查询）

# ✅ 正确
"attr": {
    "calledElement":   "process1776745678798S001",   # processKey（完整值）
    "customProcessId": "2046445818582962178",         # 数据库 ID（非 processKey 后缀）
}

# ❌ 错误（processKey 的后缀不是数据库 ID）
"attr": {
    "calledElement":   "process1776745678798S001",
    "customProcessId": "1776745678798S001",    # ← 错误！这是 processKey 后缀
}
```

**同步修正 `subFlowList`：**

父流程顶层的 `subFlowList` 中 `subProcessId` 也必须是数据库 ID：

```python
process_json['subFlowList'] = [
    {'subProcessId': '2046445818582962178', 'subNodeName': '批量修改库存'},
]
```

---

## 33. subEvent 子流程 deploy 后 callActivity 报 Process definition not found（已由 #47 定论取代，2026-09-03 5建 实证）

**现象（保留供检索）：** 子流程 save/deploy 均回"发布成功"、`processDeployTime` 也更新，但主流程审批到 callActivity 抛：

```
FlowableObjectNotFoundException: Process definition process<子流程DBid> was not found
    at ...CallActivityBehavior.getProcessDefinitionByKey(...)
```

**定论（2026-09-03 19:03 抓 UI HAR + 控制实验，本段历史内容与 #33a 全部作废）：** 不是"subEvent 不注册"，而是 **deploy 每次都注册、但定义 key 按 `'process'+记录.customProcessId` 拼接——API 创建从不写该字段 → 注册出坏 key（`process`/`processnull`）** → callActivity 按 `process<DBid>` 查不到。**不要走 manual 两段式、不要先让用户 UI 发布**：按 **#47** 的 API 配方（designer saveFlow 表单补 `customProcessId=<DBid>` → 无签名 PUT deployProcess → `/act/process/list` 验 key=`process<DBid>` version≥1）即全自动注册。

---
---

## 29. 单实例子流程必须设置 subFormTableObject

**现象：** 子流程节点前端显示"选择数据对象没有设置"，子流程启动后无法获取主流程表单数据。

**根因：** `subFormTableObject` 为 `null`，系统无法确定子流程的数据上下文，导致前端配置不完整，运行时 NPE。

**区分两种场景：**

| 场景 | subFormTableObject 来源 |
|------|------------------------|
| 批量子流程（配合 get_more） | 从 get_more 节点的 formTableList 条目复制，加 `isSubStart: True` |
| **单实例子流程（直接调用）** | 指向主流程触发表单的 start 节点数据对象 |

**单实例子流程正确写法（引用触发表单）：**

```python
n["attr"]["subFormTableObject"] = {
    "formTableId":       "form_start_{formTableCode}",  # 触发表单 ID
    "nodeId":            "start",
    "nodeName":          "触发记录",
    "nodeType":          "table",
    "formTableCode":     "{formTableCode}",             # 触发表单编码
    "formTableName":     "{formTableName}",             # 触发表单名称
    "formTableMainCode": "",
    "formTableType":     0,
    "isSubStart":        True,                          # ⚠️ 必须为 True
}
# 同步修正 attr 顶层字段
n["attr"]["formTableId"]   = "form_start_{formTableCode}"
n["attr"]["formTableCode"] = "{formTableCode}"
n["attr"]["formTableName"] = "{formTableName}"
```


## 34. 互斥分支 select 字段条件必须用 type/valType="select"，审批节点 attr 必须含表单来源

**现象：** 互斥分支条件设置后不生效（条件匹配失败），或审批节点无法显示表单字段。

**根因1：** select/radio 类型字段作为条件时，`type` 和 `valType` 写成了 `"string"`，导致条件匹配失败。

**根因2：** 审批节点 attr 缺少表单来源字段（`formTableSourceTaskId`/`formTableSourceNodeType`），导致节点无法关联表单数据。

**正确写法：**

```python
# ✅ select 字段条件
{
    "rule": "eq",
    "ruleName": "等于",         # ← 必须填，不能留空
    "valueType": "1",
    "val": "调拨入库",           # ← 字段的实际选项值
    "name": [],                  # ← 数组，不是 null 或字符串
    "field": "select_1776760516461_391756",
    "columnName": "入库类型",    # ← 字段中文名
    "type": "select",            # ← 必须是 "select"，不是 "string"
    "valType": "select"          # ← 必须是 "select"，不是 "string"
}

# ✅ 审批节点 attr 必须含表单来源
{
    ...,
    "formTableCode": "wms_inbound",
    "formTableName": "入库单",
    "formTableId": "form_start_wms_inbound",
    "formTableSourceTaskId": "start",         # ← 数据来源节点 ID
    "formTableSourceNodeType": "table"        # ← 来源类型
}
```

**错误写法：**
```python
# ❌ type/valType 用 "string" → 条件不匹配
{"type": "string", "valType": "string", "name": null, ...}

# ❌ 审批节点缺少表单来源 → 节点无法关联表单
{"approvalEnabled": true, ...}  # 缺少 formTableSourceTaskId
```

**预防：** 构建条件时，先确认字段类型（`select`/`radio`/`input` 等），type 和 valType 与字段类型保持一致。

**"不为空"条件的正确写法（rule="not_empty"）：**

```python
# ✅ 正确：rule="not_empty"，val 和 valType 都写 null（2026-09-08 实测 save 成功）
#    ⚠️ 禁止空字符串：日期/时间字段写 val="" 会在设计器值框显示 "Invalid date"（用户截图反馈）
{
    "rule": "not_empty",
    "ruleName": "不为空",
    "valueType": "1",
    "val": None,
    "name": [],
    "field": "link_record_xxx",
    "columnName": "关联仓库",
    "type": "link-record",
    "valType": None          # ← null，不是空字符串、也不是字段类型名
}

# ❌ 错误写法
{"rule": "notNull", "valType": "link-record", ...}   # rule 和 valType 均错
{"rule": "not_empty", "val": "", "valType": ""}     # 旧写法：非日期字段能存但已过时；日期/时间字段会显示 Invalid date
```

多条件 AND 逻辑时，`conditionGroup[].matchType` 必须显式设为 `"and"`，留空 `""` 前端默认渲染为"或"：

```python
"conditionGroup": [{
    "id": "...",
    "matchType": "and",   # ← 必须显式写 "and"，空字符串 = OR
    "queryItems": [...]
}]
```

---

## 33. assigneeByRole 必须同时填 roleNames，否则 UI 显示"未配置人员"

**现象：** 按角色审批节点在简流设计器 UI 上显示"未配置人员"，但流程实际保存了 roleIds。

**根因：** `roleNames` 为空数组 `[]` 时，前端仅凭 `roleNames` 渲染显示，即使 `roleIds` 有值也认为"未配置"。

**修复写法：**
```python
{
    "assigneeType": "assigneeByRole",
    "roleIds":   ["2036627369534967809"],
    "roleNames": ["部门经理"],   # ← 必须与 roleIds 一一对应
}
```

**预防：** 构建 `make_role_approver_group` 时，从角色列表查询结果直接填入 roleName，不能留空数组。

---

## 35. opinion 节点 ID 必须用 suggest_ 前缀，禁止用 Gateway 前缀

**现象：** `save_flow` 报 mxGraph 错误 `Cannot invoke "com.mxgraph.view.mxCellState.getAbsolutePoints()" ... null`，流程保存失败。

**根因：** mxGraph 服务端按节点 ID 前缀区分节点类型：`Gateway` 前缀保留给排他/并行/包含/数据判断网关，opinion/suggest 节点若用 `Gateway` 前缀，渲染器会尝试按网关逻辑计算路径点，因结构不符而触发 NPE。

| 节点类型 | 正确 ID 前缀 |
|---------|------------|
| approver / edit 等任务节点 | `Activity` |
| exclusive / parallel / inclusive / databranch | `Gateway` |
| opinion / suggest | `suggest_` ← 唯一正确值 |
| 延迟 timer_event | `TimerEventDefinition_` |

```python
ts = int(time.time() * 1000)

# ✅ 正确
OPINION_ID = f"suggest_{ts}019"

# ❌ 错误（用 Gateway 前缀）→ mxGraph getAbsolutePoints() NPE
OPINION_ID = f"Gateway{ts}019"
```

**定位方法：** 若遇到 getAbsolutePoints() 报错，将流程缩减到最简结构（只保留 approver + opinion），逐步验证节点 ID 前缀，通常是 opinion ID 写成了 `Gateway` 开头。

---

## 36. 网关节点禁止嵌套在另一个网关的 conditionNodes 内

**现象：** `save_flow` 报 mxGraph 错误 `getAbsolutePoints() ... null`，保存失败。

**根因：** mxGraph 渲染不支持网关嵌套结构——将 `parallel`/`exclusive`/`inclusive`/`data_branch` 放入另一个网关的 `conditionNodes[].nodes` 时，渲染器无法计算内层网关的绝对路径点，触发 NPE。

**受影响的网关类型：**
- `parallel`（并行分支）
- `exclusive`（排他分支）
- `inclusive`（包含分支）
- `data_branch`（数据判断分支）
- `opinion`/`suggest`（意见分支）

```python
# ❌ 错误：parallel 嵌套在 data_branch 的 conditionNode.nodes 内
data_branch_node = {
    "type": "data_branch",
    "conditionNodes": [
        {
            "name": "有数据",
            "nodes": [
                parallel_node,   # ← 网关类节点不能放在这里！
                approver_node,
            ]
        }
    ]
}

# ✅ 正确：parallel 移到主流程顶级链，data_branch conditionNode 内只放简单节点
main_nodes = [
    get_more_node,
    data_branch_node,    # conditionNode.nodes 内只放 approver/notice 等简单节点
    parallel_node,       # ← 移到顶级链，排在 data_branch 之后
    ...
]
```

**conditionNodes[].nodes 内只能放的安全节点类型：**
`approver`、`edit`、`notice`、`data_update`、`data_add`、`data_delete`、`service`、`script`、`get_one`、`get_more`、`get_one_sysinfo`、`get_more_sysinfo`、`upvariable`、`operation`、`time`

任何网关类节点必须位于顶级链（childNode 链）上，不得放入其他网关的分支内。

---

## 36. ✅ roleIds 填角色 roleCode，不是数据库雪花 ID（已验证修正）

**现象（旧文档错误）：** 旧版本文档曾说 `roleIds` 要填数据库雪花 ID 并需 patch `roleCode`——这是错的。

**正确结论（通过 `审批节点示例.md` 真实示例验证）：**
- `roleIds` 填角色的 **roleCode** 字符串（如 `"dept_manager"`、`"general_manager"`）
- `roleNames` 填角色名称
- **无需 patch**，`build_process_json` 直接透传，无需额外操作

```python
# ✅ 正确：roleIds 填 roleCode
group = {
    "approverType": "candidateGroups",
    "assigneeType": "assigneeByName",
    "roleIds": ["dept_manager"],       # roleCode，查 /sys/role/list 的 roleCode 字段
    "roleNames": ["部门经理"],
    "approverIds": [], "approverNames": [], "deptIds": [], "postIds": [],
    "expressionsIds": [], "expressionsNames": [],
    "variableTitle": [], "variableContent": "", "formTableType": "",
    "levelMode": 1, "approverId": "", "approverName": ""
}

# ❌ 错误（旧写法）：传数据库雪花 ID → 系统无法识别，审批人为空
group = {"roleIds": ["2039607913830985729"], ...}   # 禁止这样写
```

**多角色会签必须合并为同一 group：**
```python
# ✅ 正确：两个角色放同一 group → 真正的多人会签
{"roleIds": ["general_manager", "purchase_director"],
 "roleNames": ["总经理", "采购总监"]}

# ❌ 错误：两个 group → 变成两个独立审批任务，不是会签
[{"roleIds": ["general_manager"]}, {"roleIds": ["purchase_director"]}]
```

**主管审批推荐用法（动态获取发起人所在部门负责人）：**
```python
{
    "approverType": "candidateUsers",
    "assigneeType": "assigneeByExp",
    "expressionsIds": ["${flowNodeExpression.getDepartLeaders(applyUserId)}"],
    "expressionsNames": ["发起人所属所有部门的负责人(候选用户)"],
    "roleIds": [], "roleNames": [], "approverIds": [], "approverNames": [],
    "deptIds": [], "postIds": [], "expressionsIds": [...], "variableTitle": [],
    "variableContent": "", "formTableType": "", "levelMode": 1
}
```

---

## 37. 关联记录(link-record)查询：get_one 条件必须匹配目标表 `_id`，不能按业务字段

**问题现象**：触发表单通过"关联记录"(link-record)控件选择目标表记录（如订单表单的"客户"字段），流程里 get_one 却按业务字段（如"客户名称"）匹配触发表单的文本输入框 → 关联选中的记录与名称不一致时查不到/误判。

**根因**：link-record 控件存储的是目标记录的**主键 id**，不是业务字段值。按名称匹配语义错误，应按主键关联。

**正确写法**（表事件触发流程中判断记录是否存在）：
```python
{
    "type": "get_one",
    "name": "查询客户是否存在",
    "getType": 1,
    "formTableCode": "customer_mgmt",      # 目标表
    "formTableName": "客户管理",
    "conditions": [{
        "rule": "eq", "ruleName": "等于", "valueType": 2,
        "val": {                           # 取触发表单 link-record 字段的值（=目标记录id）
            "variableValue": "link_record_1788250148332_783985",  # 订单.客户 字段 model
            "formTableCode": "order_mgmt",  # 触发表单 code
            "variableName": "客户",
            "formNodeType": "table",
            "formNodeId": "start",
            "formNodeName": "工作表事件触发",
        },
        "name": "记录id",
        "field": "_id",                    # ⚠️ 目标表主键，不是业务字段
        "columnName": "记录id",
        "type": "input",
        "valType": "variable",
    }],
    "emptyAction": 3,                      # noDataType=3（中止或继续执行查找结果分支），配合 databranch 无数据分支
}
```

**验证案例（实测）**：查询条件用业务字段"客户名称"匹配被关联记录反复查不到，改用目标表主键 `_id` 后通过。引申：凡"判断被关联的记录是否存在"，优先用 `_id` 关联，再用业务字段兜底。
```

---

## 38. data_add 的 radio/select 固定值必须写纯字符串（已验证）；formTableName 误填字段 model 会显示 key

**现象 1：** data_add 的 `formModel` 里给 radio/select 状态字段写 `{"funText": "成交客户", "fieldType": "radio"}` → 设计器打开「创建客户」节点，状态字段未选中/未写入。funText 对象是**变量引用**（如 `{{占位符}}` + funContext）的写法，不是固定值写法。

**正确写法（实测对照 data_add 落库 JSON）：**

```python
formModel = {
    "<客户名称字段 model>": {"variableValue": "input_xxx", "formTableCode": "order_mgmt",
                             "variableName": "客户名称", "fieldType": "input",
                             "formNodeType": "table", "formNodeId": "start",
                             "formNodeName": "工作表事件触发"},   # 变量引用照旧
    "<客户状态字段 model>": "成交客户",          # ✅ radio/select 固定值=纯字符串选项文案
}
```

**现象 2（排查信号）：** 节点卡片/流程图上显示字段 key（如 `工作表 "input_1788249882373_599422"`）而不是表单中文名 → 该节点 `attr.formTableName` 被误填成了**字段 model**（应为表单中文名）。修正时同步处理三处：节点 `attr.formTableName`、节点 `content`（`工作表 "XX"`）、`formTableList[].formTableName`。表单中文名与字段 model 都是短字符串变量时，避免同一变量名先后复用（后赋值覆盖前值），写脚本时用 `FORM_NAME` / `FIELD_MODEL` 之类区分命名。

---

## 39. 手插线性节点必须补 UI 渲染键；终结/分支处**不要**加 addable（实测）

**现象：** 手动 dict 方式插入的 data_add / function 等节点（不经 `build_*_node` 辅助函数）在流程图节点下方**没有「＋加节点」图标**，也无法删除。正常节点自带 `addable / deletable / content / error / errorContent` 五个渲染键。

**补键：**
```python
node.update({'addable': True, 'deletable': False,
             'content': '工作表 "目标表单名"',   # data_add/data_get 类写 "工作表 "XX""；function 运算节点写功能描述
             'error': False, 'errorContent': ''})
```
**⚠️ 不需要后续的位置不要加 addable**：`approve_result` 分支上游审批节点必须 `addable=False`（见 #18）；databranch 分支网关主干 `childNode=null`，加号在各分支内部尾部（见 #9/#10）；批量新增(data_add addDataType=2)作为链条终点时同理不加。

> **2026-09-04 修正（子流程手搭踩坑）：** ①"终点不加 addable"只适用于「批量新增(addDataType=2)且确定不再挂后续节点」的**多行批量终点**；**单条 data_add(addDataType=1)** 作为终点也要 `addable=True`（否则设计器无法在其后继续加节点）。② **手工搭 subEvent 子流程的 start 根节点同样必须带渲染键**（`addable=True`、`content='发起流程'`、`error=False`、`errorContent=''`）——start 的 addable 控制「start 与首个节点之间」的＋（首个节点上方的加号）；builder 生成的主流程 start 自带该键，手搭子流程根很容易漏。③ callActivity / 子流程引用的上游 get_more 等手拼节点一律补全五渲染键。

> **2026-09-10 更正（反面现象：节点卡片上浮出「删除/取消」按钮）：** 触发键是顶层 **`deletable: true`**——API 插入的 edit 节点 `addable:true + deletable:true + content:非空` 仍浮出操作菜单（用户截图投诉）；同一流程的原生节点（`addable:true / deletable:false`）从不浮出，证明诱因是 `deletable`、**与 `content` 是否为空无关**（旧表述"addable/deletable 写成 True 且无 content"作废）。修法：链上节点 `addable:true`（保留＋）**+ `deletable:false`** + 非空 `content`；高危字段回读确认。⚠️ 与 #18「approve_result 上游审批节点 addable=False」是**两个独立维度**（addable 控「＋」、deletable 控操作菜单），别互相套用。详见 node-types 十七-B 注 3。

**验证案例：** 手插 data_add「添加记录」后无图标，补键即恢复；同批手插 function「计算下次跟进时间」一并补齐。纯显示键，不影响引擎执行。

---

## 40. 选项来自字典/工作表的 radio/select：真实存储值=字典 itemValue / 源表记录 id；字段内联 options 是占位副本

**现象：** data_add/update 给选项源为「字典」或「工作表」的字段写内联 options 里的文案（如「选项1」「A类」）→ 表单控件打开时未选中该选项，因为控件实时下拉列表是运行时从字典/源表拉的，与字段配置内联副本不一致。

**判定：** `GET /desform/api/fields/{code}?group=true` 原样返回字段 `options`：`remote:"dict"` → 字典源（`options.dictCode`）；`remote:"linkData"` → 工作表源（`options.linkDataConfig.desformCode` + 展示 titleField）；`remote` 为空才是真静态选项（文案即存储值）。⚠️ 静态选项条目键形不定：生产样本常见**只有 `value`（值即文案）+ `itemColor`、无 `label` 键**（2026-09-11 订单表「状态」实测：`{"itemColor":"#00C345","value":"已完成"}`）——判断「选项是否存在/取值」按 `value`/`label`/`text` 依次取，**禁止假定 `label` 键存在**（假定即整轮脚本重跑）。

**取真实值（免 Sign 校验的接口）：**
```python
# 字典源：先扫主表按 dictCode 拿 id，再取条目（itemValue=真实存储值，itemText=文案）
GET /sys/dict/list?pageNo=1&pageSize=100          # 本地按 dictCode 过滤，取返回 id
GET /sys/dictItem/list?dictId={id}&pageNo=1&pageSize=100
# 工作表源：存储值=源表记录 _id；源表无记录时下拉为空，任何值都对不上（先造源数据或该字段不设值）
GET /desform/data/list?desformCode={code}&pageNo=1&pageSize=N   # 需 X-Tenant-Id
```
> ⚠️ `/sys/dict/loadDict/{code}` 需 Sign 签名不可用；`/desform/api/data/list` 参数对不上恒返回空，行数据查询用 `/desform/data/list`。

**验证案例（实测）：** 选项源为字典的 radio/select 固定值写字典 itemValue（如「任务状态」字典 待办=1/已办=2/取消=3，则写 `'1'`）而非字段内联选项文案「选项1」。

---

## 41. data_add 日期字段设「当前日期+N天」：插 date 运算节点 + formModel function 引用（#28 的正解）

#28 只讲了禁止 EL 表达式的反面。业务要「下次跟进时间=今天+10天」且字段无表单默认值时：

```python
# ① 在目标 data_add 的公共上游插入 operation(function) 节点
op = {'id': f'task{ts}001', 'name': '计算下次跟进时间', 'type': 'function', 'status': -1, 'configure': {},
      'attr': {
          'funType': 'date', 'funContext': {}, 'funText': '+10D',          # +/-数字+单位：+10Y/-3M/+30D/+24H
          'expressionType': 'delegateExpression', 'expressionValue': '${functionDelegate}',
          'dateFieldVal': {'formNodeType': 'system', 'variableValue': 'nowDate', 'variableName': '当前日期'},
          'dateFunctionFormat': {'argument': 'date', 'result': 'date', 'end': '2', 'out': 'd'},
          # ↑ 目标字段是 datetime 时 argument/result 用 'datetime'
          'operationMode': 'cache', 'decimals': 2,
      }}
# formTableList 补登记
ftl.append({'formTableId': f'form_{op_id}_function-date', 'nodeId': op_id, 'nodeName': '计算下次跟进时间',
            'nodeType': 'function', 'formTableCode': 'function-date', 'formTableName': '计算下次跟进时间',
            'operationMode': 'cache', 'decimals': 2})
# ② data_add 的 formModel 日期字段引用运算结果
fm[date_field_model] = {'variableValue': 'result', 'formTableCode': 'function-date',
                        'variableName': '结果', 'fieldType': 'date',
                        'formNodeType': 'function', 'formNodeId': op_id,
                        'formNodeName': '计算下次跟进时间', 'operationMode': 'cache', 'decimals': 2}
```

**要点：** 运算节点只需插一个在公共上游（分支前），function 引用可被多份下游 data_add 副本共用；funType 取 `date` 的运算节点完整生产形态见 `example/运算节点示例.md`「为日期加减时间」。插入后记得按 #39 补 UI 渲染键。

---

## 42. 删除简流流程记录：DELETE /act/process/extActProcess/delete?id=；无法删除时用「改名挪移法」停用兜底（2026-09-03 实测）

**✅ 真实删除接口（2026-09-03 用户提供并实测通过）：**

```
DELETE {api-base}/act/process/extActProcess/delete?id=<流程记录 DBid>
# 头：X-Access-Token + X-Tenant-Id + X-Low-App-ID
# id = 流程记录 DB id（query_flow 返回的 id），不是 processKey
```

- 方法必须 **DELETE**：GET 访问报「不支持 GET 请求方法，支持 DELETE」（实测 8080 与 3100 一致）
- 删除成功直接返回 `success:true`，流程记录消失（实测 query_flow 再查为 None）
- ⚠️ 之前踩的弯路：曾探测 `/online/lowApp/miniflow` 下 delete/del/remove/deleteFlow 等全部 404、误判"无删除 API"——真实接口在 `/act/process/extActProcess/delete`，路由表未覆盖
- ⚠️ 删除前确认无引用：自定义按钮 processId、被 callActivity 引用的子流程（有引用先解绑/删除父流程）；按钮 create 返回的 `processId` 若无独立流程记录会报「未找到对应实体」（正常，非 bug）
- 已停用/未发布的流程可直接删；建议先停用再删，避免误删正在跑的流程

**兜底（无 id 时停用）：** 拿不到 id（如按名只能查到最新一条）时用「改名挪移法」保留记录、不再触发（三步，全程 save 不 deploy）：
1. 最新同名流程先改名成临时名（只改 processName）
2. 按原名查到旧流程 → 三层 startType（config / processJson 顶层 / `attr`）改 `manual` + 改名「(已停用)」再 save
3. 临时名改回原名

**配套行为：** `query_flow(api, token, process_name=...)` 同名多条时返回**最新一条**（实测）。

**验证案例（实测）：** ① 用 DELETE 接口删除按钮占位的空流程 processId →「未找到对应实体」（正常，非 bug）；② 删除重复创建的旧流程记录 → `success:true`，query_flow 复查确认已无记录。

---

## 43. 引擎定义核验口径：主流程 key=记录 processKey，只有 subEvent 子流程才是 process<DBid>（与 #47 配套，2026-09-03 实测）

**现象：** 用（#33 旧文遗留判据） `process<DBid>` 去 `/act/process/list` 核验 **tableEvent / buttonEvent 主流程** → 永远 MISSING，误判部署失败，白重发一轮（重发也不会有 process<DBid>）。

**规则：**
- 主流程（tableEvent / buttonEvent）deploy 成功后，引擎定义 key = 流程记录的 **processKey**（如 `process1788402126749`），**不是** `process<id>`
- 只有 **subEvent 子流程**才是 `process<DBid>`（callActivity 运行时按 `process + attr.customProcessId` 找定义）
- 验证：`GET /act/process/list`（X-Tenant-Id + X-Low-App-ID）分别按「主流程 processKey / 子流程 process<DBid>」匹配，互不套用

---

## 44. API 写入数据同样触发 tableEvent 简流；date 落库格式判定（2026-09-03 实测）

**现象：** `add_data`（`/desform/data/add`）向绑定了「新增触发」简流的工作表插记录，流程立刻起实例、生成审批待办——是**预期行为**，不是 bug。

**用途：** 造测试数据时可插入「待审批」记录让流程自然跑起来，供 UI 审批演示；不想产生待办就别往触发表插数。

**date 落库格式判定：** date 控件存毫秒还是 `"yyyy-MM-dd"` 字符串，看 `GET /desform/api/fields/{code}` 该控件 `options.timestamp`：`true` → 毫秒时间戳 + 写 `_dictText`；否则直接存日期字符串。

---

## 45. 子流程 get_one「查询入库单」按 link-record 变量查 `_id` 反复查不到：XML 缺 MiniSubProcessStartListener 因果链 + 修复（2026-09-03 仓储实测）

**现象（跨两个子流程多次复现）：** subEvent 子流程首个 get_one「查询入库单」条件为 `_id` = 明细行「所属入库单」（link-record 变量引用），运行日志：

```
WARN o.j...a.b:1934 - Id must not be null!
==== 加密查询规则 criteriaList:[{"criteriaObject":{"_id":""},"key":"_id"}]
---【流程数据节点#获取单条记录，节点名称：查询入库单】-------- 未获取到数据，dataId = null
```

→ 子流程空跑直接结束：库存不增/不减；严重时 data_add 只写入 integer 字段、link-record 字段（仓库）整字段被丢。

**根因链（发布途径 → XML 完整性 → 变量注入，缺一环即 `_id:""`）：**

1. 子流程实例**按明细行启动**（主流程 get_more 取 N 条明细 → callActivity 逐条起子流程）；「查询入库单」的 `_id` 值来自**父行 link-record 变量引用**（明细.所属入库单 → 主表记录 id），不是子流程自己能查到的。
2. 该值由子流程 process 级 **start executionListener `MiniSubProcessStartListener`** 注入（把主流程实例 ID + dataId 写进子流程上下文）。XML 缺它 → 所有父行变量解析为空 → `_id:""`。
3. **manual 根层两段式发布（manual→deploy→subEvent，已废弃）注册的定义 XML 残缺**——定义 key `process<DBid>` 存在、callActivity 能启动（日志见 MiniCallActivityListener），数据流却全断，因为 XML 在根层 manual 期间生成、缺 MiniSubProcessStartListener 注入（#31）；同配置换成 UI 发布过的另一条子流程就正常（2026-09-03 交叉验证）。**现行 API 配方（#47：三层 subEvent + designer saveFlow 带 customProcessId）不经过 manual 态，XML 完整，无需 UI 兜底。**

**修复（三步，按序执行）：**

1. **UI 打开子流程 → 检查三层 startType 全为 subEvent → 保存并发布**（只保存无效）。
2. **发布后确认引擎定义已更新**：`GET /act/process/list` 按 key=`process<DBid>` 匹配，看 **version 是否递增**（15:21:02 增加库存 ver 11→12、15:33:09 减少库存 ver 6→9 后运行均生效）。⚠️ updateCount / processDeployTime / 后端 node_deploy INSERT 日志**不能**证明引擎定义已更新——2026-09-03 实测：15:15:52 UI 保存并发布后日志有 node_deploy INSERT（deployment 记录）但 ver 未变、运行仍失效（孤儿快照行：deployment_id 无对应 Flowable 定义，运行时按当前定义的 depId 查不到），重复发布一次后（ver 递增）才生效。该发布未注册现象疑似平台 bug，遇 ver 不增应再发一次并记录反馈。
3. **核对「查询入库单」条件语义**：查询字段 = `记录id`（`_id`）；条件值 = 变量引用**明细行.所属入库单**（variableValue 是明细表 link-record 字段 model 如 `link_record_xxx`，**不是** `_id`）；formTableCode = 入库单主表。

**验证：** 再跑一条数据，日志 criteria 出现真实主单 id（`{"_id":{"$in":["2095..."]}}`）即修复；仍为 `""` 说明发布没生效，回第 1 步。

**关联：** data_add「添加记录」新增行成功但 link-record 字段（仓库）为空/被丢是独立问题（本问题数据流正常，是 data_add 写 link-record 环节丢失），见 **#46**——同样需 UI 重配该节点字段映射 + 发布。

---

## 46. data_add「添加记录」link-record 字段（仓库）新增行一直为空/被丢弃：JSON formModel 正确仍需 UI 重配节点映射（2026-09-03 仓储实测）

**现象（同一节点跨三次运行复现，15:04/15:12/15:18 均失败）：** 增加库存子流程「添加记录」data_add 新增行**成功**，但 link-record 字段（仓库）写入为空/整字段被丢，integer 字段（数量）与另一个 link-record（物料）正常写入：

```
新增行 = {数量: 25, 物料: [WL-007]}   ← 仓库字段缺失
日志: WARN ... Id must not be null!
```

**排查过程（每步都看似"应该好了"但实际未好）：**

1. **查流程 JSON：formModel 三字段齐全且引用正确**——仓库字段 `link_record_1788405208930_270268` 引用「查询入库单」节点的 `所属仓库`（variableValue=`link_record_1788405208847_808482`、formTableCode=入库单主表、fieldType=link-record），与数量/物料的引用写法一致 → **配置层看不出错**。
2. **换新增组合重试仍丢** → 排除目标行已存在与否、物料差异（新增分支 vs 更新分支都试过）。
3. **日志显示 data_update 更新分支正常**（777 单累加成功、仓库匹配正确）→ 说明「查询实时库存」AND 条件与上游 get_one 数据流没问题，问题**只在 data_add 写 link-record**。
4. 反复 API 改 JSON + 反复发布 → 仍丢。

**真正的修复（2026-09-03 用户操作后生效，15:21 ver 12 发布、15:22:23 333-1 新增行带 CKA01）：**

1. **UI 打开该 data_add 节点 → 在节点配置面板里重新选择「仓库」字段的映射来源**（不用 API 直接改 JSON——JSON 看着对，但运行时不认或丢）——**必须用户在 UI 重配，API 侧改 JSON 无效**。
2. UI 保存并发布（见 #45 步骤 2 确认发布生效：`GET /act/process/list` version 递增）。
3. 走一条**仓库+物料组合不存在**的新数据验证：新增行必须带仓库值。

**结论：** data_add 的 link-record 字段值若来自**中间 get_one 节点**（如「查询入库单」查询结果，而非子流程启动明细行），JSON formModel 配置即使正确，运行时也可能不写入——**遇到"新增行成功但 link-record 字段为空"，先让用户在 UI 重配该节点的字段映射并发布，不要在 API/JSON 层反复尝试。** 与 #45 的 `_id:""`（父行变量未注入）不同：本问题 get_one 上游数据流正常（更新分支仓库匹配成功），是 data_add 节点写 link-record 环节丢失。

---

## 47. subEvent 子流程 API 发布"不生效"真根因：deploy 实际注册了但缺 customProcessId 字段→定义 key 拼错（#33/#33a/"必须 UI 发布"结论更正，2026-09-03 实测）

**现象（5建 17:36~19:03 复现与定位）：** 子流程 API 保存 + `deployProcess` 报"发布成功"、记录 `processDeployTime` 也更新，但主流程审批到 callActivity 抛 `Process definition process<DBid> was not found`；按 key=`process<DBid>` 查 `/act/process/list` 查无。

**真根因（抓 UI「保存并发布」HAR 逐项对比 + 一次性子流程控制实验证实，19:03）：**

1. `deployProcess` 对 subEvent 流程**每次都真实注册**，但 Flowable 定义 key 由后端按 `'process' + 记录.customProcessId 字段` 拼接（与记录 processKey 无关）。
2. API 创建/改 key 保存流程时**从不写 customProcessId** → 字段空 → 注册出**坏 key**（实测形态 `process` / `processnull`，def name=记录 processKey）→ callActivity 按 `process<DBid>` 永远查不到 → 表现为"API 发布无效"。
3. 设计器 UI 的 `saveFlow` 表单**每次都带 `customProcessId=流程id`**（同时带 processKey/id/processName/processType/lowAppId/startType），所以 UI 发布一直正常。
4. **与 #33a 的"缺租户/应用请求头"、与 X-Sign/X-TIMESTAMP/X-MiniFlowExclusionFieldMode 均无关**——本次全程无签名、有头照常注册（头是会话标配不是开关；X-Sign 实测为假线索）。

**API 全自动发布配方（免 UI 点击，2026-09-03 19:03 实验验证：一次性 subEvent 流程补 customProcessId 保存后无签名 PUT → `/act/process/list` 出现 key=`process<DBid>` ver1；对已 UI 发布记录裸 API deploy 同样正确 bump v6）：**

```python
# ① 子流程记录就位（三层 subEvent、processKey=process<DBid>）后补一次设计器式保存：
#    POST /act/designer/miniDesFlow/api/saveFlow
#    Content-Type: application/x-www-form-urlencoded（表单，不是 JSON body）
#    参数：updateCount=<记录现值(取 query_flow updateCount)>  processJson=<完整JSON字符串>
#         processName=<流程名>  processKey=process<DBid>  processType=oa
#         id=<DBid>  customProcessId=<DBid>  lowAppId=<应用id>  startType=subEvent
#    tenantId 走 X-Tenant-Id 请求头即可；X-Sign/X-MiniFlowExclusionFieldMode 非必需
# ② PUT /act/process/extActProcess/deployProcess  body {"id": "<DBid>"}（无需签名头）
# ③ 校验：/act/process/list 出现 key='process<DBid>' 且 version>=1
# ③b 存量记录（customProcessId 已写入、三层 subEvent 已就位）的常规修改：save_flow→deploy_flow 一次生效，
#     无需每次执行 ③；③ 仅保留给「新建 subEvent 子流程」与「运行异常怀疑发布未生效」时的排查。
# ③c 个别环境实测 /act/process/list 返回空结果或 read timeout（接口不可用）时，可改验 queryById 的 processXml：
#     取 extActProcess/queryById?id=<DBid> → result.processXml 是 base64 → 解码后 <process id="..."> 即引擎定义 key
#     （主流程=记录 processKey；subEvent=process+DBid），毫秒级，与 ③ 验证同一层证据。
```

**历史条目衔接：** #33（manual 两段式）、#33a（带头 PUT 即注册）与 create-flow.md 早期"必须用户 UI 保存并发布"都是当时平台版本 + 未抓 UI 请求条件下的**局部表象结论**；本条目是接口层完整机理。遇"发布成功但查无 process<DBid>"：先按本条补 `customProcessId` 再 PUT，**不要**先走 manual 两段式、**不要**急着让用户 UI 发布。注意与 #31/#45 的 XML 层问题（三层 subEvent、MiniSubProcessStartListener 注入）相互独立，两者需同时满足；另外勿混淆两个 customProcessId：主流程 callActivity 节点 `attr.customProcessId`（caller 侧指向子流程 DBid）与子流程**记录**的 customProcessId 字段（deploy 时决定 def key）是两回事。

**实验残留物（无碍，可忽略）：** /act/process/list 中 key=`process`(ver 60+) 与 `processnull` 的历史坏 key 行。

## 48. api/aiOrchestration 手动构造的三个坑 + 禁用类型清单

1. **api 节点 `requestBody` 键前端默认构造里没有**（FlowNode/Add/index.vue L633-668，抽屉才补）——手动构造 POST/PUT/PATCH 的 api 节点必须显式写 `'requestBody': ''`（哪怕空串），否则该键缺失。
2. **api/aiOrchestration 不走 expressionType/expressionValue**：后端 TaskNodeCreator 按 type 硬编码委托表达式（`${apiTaskDelegate}` / `${aiOrchestrationTaskDelegate}`），attr 里不要画蛇添足；也不需要 formTableList 联动（五类联动节点之外）。
3. **抄送节点（type=数字 2）后端未实现**：DesignerAdapterUtil 遇 type=copy 直接抛 `抄送功能暂未实现`——前端抽屉完整是假象，保存能过、发布必炸。Event(5)/Divide/Notice(20) 同为占位半成品，全部禁用。
4. **数字型 type 陷阱**：抄送=2、事件=5、通知占位=20、分支行=3、并行行=10、按钮=8 是**数字**，其余是字符串；遍历判断时不能一律按字符串比较。
5. **deployProcess 方法是 PUT 不是 POST**（与 #47 实测一致）。
6. 停用流程优先 `GET /act/process/close/{processKey}`（激活 open/{processKey}），#42 的「改名挪移法」仅在删除受阻时兜底——新端点清单见 api-reference.md「补充端点」。

## 49. 消息节点变量收件人：对象形态群发错误收件人，正确格式是 "var."+JSON（2026-09-07 全链路实测）

**现象：** 通知节点收件人配「记录创建人」时，写成 approver 那套对象形态（`toUserIds` 放 `{variableTitle, variableContent:[{...}], formTableType}`）→ 接口保存/发布全部 success，流程也正常触发，但**消息群发给 8 个错误收件人、真正的创建人收不到**（`/sys/annountCement/listByUser` 查无）。

**真相（前端 MessageUserSelect 组件源码，模块 f1b0）：** 变量收件人在 `attr.toUserIds` 里是**字符串**：

```python
import json
entry = "var." + json.dumps({
    "formTableCode": "<表code>", "formTableId": "form_start_<表code>",
    "nodeId": "start", "nodeType": "table",
    "field": "create_by", "fieldType": "select-user",
}, ensure_ascii=False)
# attr.toUserIds = [entry]，attr.toUserNames = ["记录创建人"]
# 节点顶层 toUserIds/toUserNames 也要写同一份（同静态收件人两处规则）
```

- `field` 是字段 model；系统字段「记录创建人」= `create_by`（fieldType `select-user`）。
- 固定收件人仍是 `user.{username}` / `role.{roleCode}` / `dept.{deptId}` 字符串，与 `var.` 条目可混排。
- ❌ `toUserExpression`（如 `${applyUserId}`）无效（#14 已有）；❌ 对象形态无效且会错误群发。
- 验证：给表新增一条满足条件记录 → `GET /sys/annountCement/listByUser`（带 X-Tenant-Id 头）应出现该消息，且只有正确收件人收到。

**关联坑：tableEvent 的 `conditionFields`（触发字段）build_process_json 不落库**——config 里传了也被写成空数组。save 前必须自愈注入：`pj['attr']['conditionFields'] = [<监控字段model>]`（startCondition 不受影响，正常落库）。两节点快路径完整配方见 create-flow.md 组合 F。

## 50. 触发筛选「在范围内」是独立 rule=range（beginVal/endVal），不要拆成两条 AND（2026-09-07 实测）

**现象：** 改触发条件为「数字 在范围内 0-100」时，AI 先断言"简流触发条件没有 range 规则"，用「数字≥0 且 数字≤100」两条 AND 兜底；用户截图纠正——设计器「筛选规则」下拉里数字字段本来就有「在范围内」选项。

**真相：** startCondition 的 rule 全枚举包含 `range`（trigger-types.md「rule 全枚举」，2026-09-07 本会话实测落库成功，updateCount 正常递增）：

```python
{"rule": "range", "ruleName": "在范围内", "valueType": "1",
 "beginVal": 0, "endVal": 100,            # ← range 用 beginVal/endVal 代替 val
 "name": None,
 "field": "number_xxx", "columnName": "数字",
 "type": "number", "valType": "number"}
```

- `range` 只用于数字/日期字段（每个 rule 有控件类型白名单，不匹配时 UI 不展示该选项）。
- 两条 ge+le AND 语义等价但非 UI 原生形态——用户点名「在范围内」就直接用 range，不要发明替代结构。
- 教训：改触发条件前先查 rule 全枚举（SKILL.md「startCondition 规则码」段已内嵌），**禁止凭记忆声称某规则不存在**。
- 关联：`empty`/`not_empty` 的 `val` 与 `valType` 都写 **null**、禁止空字符串（日期/时间字段写 `""` → 设计器 Invalid date，2026-09-08 实测；见同文件「不为空」条件写法段）；组内多条件 `matchType` 用小写 `"and"`/`"or"`。

## 51. 字典选项字段（checkbox 多选框）触发条件值必须写 itemValue，写中文 label UI 显示"未选中"（2026-09-07 实测）

**现象：** 用户说"触发字段【多选按钮】，条件=是其中一个【咨询/方案】"。字段实为字典选项 checkbox（isDictItem=true，dictCode=FCJcYSivQI），`fetch_form_fields` 返回 options=["1","2","3","4"]。照用户口述把 val 写成 ["咨询","方案"] → 保存发布成功，但用户截图反馈：触发条件里多选框的值**没有选中任何项**。

**真相：** 字段原始配置里选项是 label/value 成对存储：

```json
"options": {
    "isDictItem": true, "dictCode": "FCJcYSivQI",
    "options": [
        {"label": "咨询", "value": "1"},
        {"label": "方案", "value": "2"},
        {"label": "实施", "value": "3"},
        {"label": "运维", "value": "4"}
    ]
}
```

- 触发条件 val 必须写 **itemValue**（"1"/"2"）；写中文 label 不报错、能 save/deploy，但 UI 显示未选中、运行时也不匹配。
- ⚠️ **`in`/`not_in` 多值的 UI 原生存储格式（2026-09-07 用户 UI 保存后 queryById 实测）**：
  ```json
  {"rule": "in", "ruleName": "属于", "valueType": "1",
   "val": "1,3",                 // ← checkbox（多选框）：逗号拼接的字符串！不是数组
   "name": null,
   "field": "checkbox_xxx", "columnName": "多选框",
   "type": "checkbox", "valType": "checkbox",
   "value": ["1", "3"]}          // ← 同时还有一个 value 数组，两处都要写
  ```
  **⚠️ 格式随字段类型而变（同日 select 字段对比实测，用户 UI 保存后 queryById）：select（下拉选择框）字段的 `val` 是数组** `["2","3"]`（不是逗号字符串），`value` 数组照写。API 直改时：checkbox → `val`=逗号字符串 + `value` 数组；select → `val`=数组 + `value` 数组；**radio（单选框）→ `val`=数组、无 `value` 键**（UI 保存数据里只有 val）。写错形态能 save/deploy，但 UI 值选择器显示错误（用户会立刻发现）。留档样本实测：ruleName 文案并存且纯展示（in：「属于」/「是其中一个」；**not_in：「不是任何一个」**，2026-09-10 用户 UI 样本），运行时只看 rule 码；valType 随字段类型（select=`select`、checkbox=`""`、radio=`radio`）。
- wrapper `fetch_form_fields` 返回的 options 列表**本身就是 value 列表**（不是 label 文案）。当 options 与用户口述的中文文案对不上时，**不要用口述文案当条件值**，去 raw 接口查 label/value 映射：`GET /desform/api/fields/<formCode>?group=true` → 该字段节点的 `options.options[]` = `[{label:中文, value:存储值}]`（字典/工作表源才成对；**静态选项常仅 `value`+`itemColor`、无 `label` 键，见 #40**）。
- 修法：queryById/query_flow 拉最新 processJson → 定位 startCondition 里该字段的 queryItem → 按上面格式改 val+value → save_flow + deploy_flow。若流程被用户在 UI 改过名导致按名查不到，直接 `GET /act/process/extActProcess/queryById?id=<DBid>`（带 X-Tenant-Id 头）兜底。
- 关联：#40 是 radio/select 同款问题；本条是 checkbox + 触发条件场景。字典项换 label 不改 value 时流程无需动。

---

## 51. data_update 的 updateFields[].field 必须填字段 model；误填中文名 → 该条更新被引擎静默跳过（2026-09-07 资产归还实测）

**现象：** 子流程 data_update 节点同一条 updateFields 两条：状态置「闲置」（field 误填中文名「资产状态」）+ 保管人置空（field=model `select_user_xxx`）。运行时**保管人清空成功、状态未写**——同节点一个字段生效一个不生效，无任何报错。

**根因：** `fetch_form_fields` 返回 `{中文名: {model, type, options}}`——遍历取值时误把**键（中文名）**当 model 填进 `updateFields[].field`；引擎按 model（`select_xxx`）匹配目标列，中文名解析不到 → 该条目**静默跳过**（大概率仅 WARN 日志），同节点其他 field=model 的条目正常写库。

**铁律：** 凡是要 model 的地方（data_update `field`、get_one/get_more 条件 `variableValue`/`field`、formModel 键），一律取 `v['model']`，禁止 `item[0]` / `item[0][0]`（那是中文名）。自检：回读已保存流程 JSON，updateFields[].field 必须形如 `select_1788512957192_239364` 而非「资产状态」。

**验证修复：** 修正 field 为 model 后重跑数据，目标字段正常写入（联行数据：zc_asset 状态在用→闲置）。

**关联发布坑：** subEvent 子流程**改配置后**发布，只 `save_flow(extActProcess)` + `deploy_flow` **不会重新注册引擎定义**——`GET /act/process/list` 按 key=`process<DBid>` 查 version **不递增**（deployTime 仍旧）、运行时仍走旧 XML（#45 同款现象）。必须按 #47 配方补一次 designer saveFlow（form：id + customProcessId + processJson + 最新 updateCount）再 PUT deploy，version 递增（1→2）才生效。**#47 配方对"创建"和"修改"都适用。**

---

## 52. 日期类字段触发条件值必须写毫秒时间戳数字；只有 time 字段才用字符串（2026-09-08 实测）

**现象：** tableEvent 触发条件「日期（年月）等于 2026-09-08」，API 把 `val` 写成字符串 `"2026-09-08"` → 保存/发布全 success，但**流程永不触发**（条件恒不匹配）。用户在 UI 里用日期选择器重选一遍后正常——JSON 里 val 变成数字 `1788192000000`。用户继续反馈：日期时间条件「好像也不行」，只有时间字段好用。

**真相（14 个 UI 原生测试流程取证 + 字段配置比对）：** startCondition 条件值 `val` 的形态跟随**字段存储形态**（与 #44 落库判定同源，口径看 `GET /desform/api/fields/{code}` 该控件 `options.timestamp`）：

| 字段 | options.timestamp | val 形态 | 实测样本 |
|---|---|---|---|
| 日期（年月/年季度/年周/年月日/日期时间） | `true` | **毫秒时间戳数字（int）**，不是日期字符串 | 年月 eq → `1788192000000`（=2026-09-01 00:00 本地） |
| 时间 | `null` | 字符串 `"HH:mm:ss"` | time eq → `"10:30:00"` ✅ 所以"只有时间好用" |

- 日期（年月）选 2026-09 → 落**当月 1 号 00:00:00 本地时间**毫秒（`1788192000000`）；年月日选 2026-09-08 → 当日 0 点（`1788796800000`）。
- 日期时间 eq 是**秒级毫秒相等**：UI 选择器容易带上"当前秒数"，记录里秒数对不上就不触发——「日期时间也不行」的最可能原因（服务器上该流程 val=`1788834630000`=2026-09-08 10:30:30，记录必须是同一秒）。日期时间条件要么选精确到秒的值，要么改用 `range`（#50）。
- 判断依据看 raw 字段配置的 `options.timestamp`，不要在 `fetch_form_fields` 返回的 type（date/time 一律如此）上猜存储形态。

**修法：** 触发条件涉及日期类字段时，先按本地时区换算毫秒时间戳（当日/当月首日 0 点）写成 **int** 数字再 save_flow + deploy_flow；写字符串能 save/deploy 但条件永不成立。API 新建流程时直接落时间戳数字，避免用户再 UI 手选一遍。

---

## 77. 自定义表达式（分支 content）日期类字段值必须毫秒时间戳；time 字段才是字符串（2026-09-10 实测）

**现象：** 互斥分支-自定义表达式条件「日期 小于 2026-09-11」写成 `${date_xxx < '2026-09-11'}`，save/deploy/回读全绿，但**运行时条件恒不成立**——加满足条件的记录也不触发，admin 站内消息 0 条。用户问「是不是要写成时间戳」。

**真相：** 日期字段（options.timestamp=true）记录数据存的是**毫秒时间戳数字**（#52 同源），表达式引擎拿字段值（数字）与带引号的日期串比较 → 类型不匹配必 false。修法：值写**毫秒时间戳数字、不加引号**——`${date_xxx < 1789056000000}`（1789056000000=2026-09-11 00:00 本地；2026-09-01 00:00 本地=1788192000000，+10 天）。**时间字段（time）不是毫秒**：仍写 `"HH:mm:ss"` 字符串、加引号（用户 2026-09-10 确认「日期组件需要时间戳」「时间组件不是」）。规则已入必读路径：SKILL.md 互斥分支段、create-flow.md 组合 J、node-types 二十节。

---

## 53. 需求点名「从关联字段获取单条」禁止用 selectType=1「_id=link值 条件查询」替代（2026-09-07 资产调拨实测被驳回）

**现象：** 资产调拨主子流程改造（复用《资产领用发放改造示例.md》①–⑤ 常量模板），需求点名子流程「根据资产调拨明细(使用从关联字段获取单条)获取固定资产」。第一版按模板把「获取固定资产」建成 data_get_one `selectType=1`（从工作表查询单条，条件 `记录id = 明细.选择固定资产 link 值`）——语义等价、运行时也能取到目标记录，但用户在设计器看到节点取数方式不是「从关联字段获取单条」，被驳回："未按要求使用"。

**根因：** 模板里 3 个 data_get_one（查主单/查台账）全是 selectType=1「`_id=link值` 条件查询」写法，只换 ①–⑤ 常量就照抄了。把"能取到同一条数据"当成"按点名取数方式实现"——用户点名的是设计器原生能力，必须落库为对应形态，禁止发明语义等价的替代结构（#50 同款教训：点名 range 就用 range）。

**正确形态（data_get_one `selectType=3` 从关联字段获取单条；契约权威样本=《获取单条数据.md》附录完整 JSON）：**
- node `attr.selectType=3`；`content` 改 `关联表 "目标表名"`（不再是 `工作表 "…"`）
- 源记录三键：`attr.formTableCode/Name`=**源表**（link 所在记录的表；子流程按明细行场景=明细表）、`formTableId=form_{上游数据节点id}_{源表code}`、`formTableSourceTaskId`=上游数据节点 id（子流程行数据 = 主流程 get_more 节点 id）
- 关联目标三键：`attr.linkFormTableField`=源记录上的 link 字段 model、`attr.linkFormTableCode/Name/Type(=1)`=**目标表**（返回的记录表，如固定资产台账）
- 无附加筛选：`searchFieldGroup: []`；`noDataType=3`（中止或进查找结果分支）无数据时进 databranch「无数据」分支
- delegate 键保留：`expressionType:"delegateExpression"` + `expressionValue:"${getOneRecordDelegate}"`
- `start.formTableList` 该节点条目同步：`selectType:3`、`formTableCode/Name`=目标表、`formTableMainCode`=源表、`formTableType:1`、`formTableId=form_{本节点id}_{目标表code}`
- `formTableSourceNodeType` 与上游真实节点类型对齐：上游=start→`"table"`、search 类数据节点→`"search"`；上游是 get_more 时参照《获取单条数据.md》附录 selectType=2 样本用 `"getMore"` + `formTableSourceGetDataType=1`

**教训：** 复用《资产领用发放改造示例.md》做归还/调拨/报废/维修改造时，逐节点核对需求对取数方式的措辞——凡点名「从关联字段获取单条」的节点，把模板的 selectType=1 查询写法外科重写为上面的 selectType=3 形态（节点 id/childNode/pid 不动），不能只改 ①–⑤ 常量。改后发布走 #51 结尾的 #47 配方（designer saveFlow 补存 + PUT deploy，引擎 version 递增才生效）。

**验证修复：** 资产调拨发放子流程「获取固定资产」按此重写：源=调拨资产明细、linkFormTableField=`link_record_1788513286482_600387`(明细.选择固定资产) → 固定资产台账；引擎 key=`process<DBid>` version 1→2，回读 attr.selectType=3 通过。

---

## 54. operation 运算节点显示 key/编码串而非字段中文名：主因 funText 占位符/funContext key 不一致；content 卡片文案是次要独立差异（2026-09-08 实测）

**现象：** 新建运算链流程（tableEvent 触发，链 number→date→date-diff→get_more→record→fun，config 精简格式、number/fun 带 fieldNames），save+deploy 后反馈「节点显示的 key 未正确显示名字」：先是运算内容显示 `{{<32hex>.money_…}}*0.13`（raw key），修复轮之后又变成一整段 `{{%7B%22field%22%3A%22money_…%7D….}}*0.13` 的 URL 编码乱码（后者是脚本改坏的，见下）。

**两处独立缺陷（同层症状、不同数据键，别混）：**
1. **funText 占位符/funContext（主因，用户实际所见）** → 下方「根因」「修法」整节。
2. **content 卡片渲染键（次要独立差异）**：builder 对 date/date-diff/record 写的 content 与设计器画布卡片文案不一致（date `+30D` vs 画布 `注册时间  +10Y`、date-diff 空 vs `当前日期 减 注册时间`、record `form_task<节点id>_<表code>` 裸串 vs `统计数据条数：采购申请`；number/fun/get_more 正常）。服务端差异属实，**但可见影响未获用户证实，修 content 不解决占位符症状、反之亦然**——需要对齐卡片文案时按 example/运算节点示例.md 知识点 9 的格式 save 前自愈或 save 后补一轮 content 修正再 deploy（2026-09-08 实测）。

**根因（脚本 bug，禁止再犯）：** `funContext` 是 `{md5key: URL编码value}` 映射。用 `new_fc[ok] != ok` 判断"key 是否变化"**恒为 True**（value 是编码串，永远 ≠ 32hex key），再执行 `ft.replace('{{'+ok+'.', '{{'+new_fc[ok]+'.')` → 占位符前缀整体被替换成 URL 编码的 value → 公式区显示乱码。**铁律：funContext 的 value 只用于解码/展示，绝不参与占位符字符串替换；重写 funText 占位符只能用 32hex key 本身。** 占位符正确格式 = `{{<md5key>.<字段model>}}`（与脚本 builder 产物一致，见下）。

**前端 hash 规则（2026-09-08 逐字节实测 ✅）：** 同字段同上下文的条目 hash key 与脚本 builder 产物**完全相同**。规则 = `md5(解码后 value 的规范 8 键紧凑 JSON, ensure_ascii=False, separators=(',',':'))`（键序 field/formTableCode/formNodeId/formNodeType/variableValue/formNodeName/tableText/fieldText，无 variableName）。

**funContext 值编码风格（存储侧）：** 只转义 `"`→`%22`、`{`/`}`、非 ASCII（中文→%XX），`,` 与 `:` **保持原样**（不是 encodeURIComponent，也不是 python quote 默认——后者会把 `:` `,` 也转义成 %3A/%2C）。两种编码解码结果相同 → 不影响 key；但对齐存储风格可减少前端疑点。python 生成该风格串：`urllib.parse.quote(s, safe=':,.-_/?')`。

**修法（外科）：** query_flow 拉最新 → 定位 number/fun 节点 → funContext 保持 {key: value}、校验 `key == md5(解码canonical)` → funText 用 regex 找出所有非 32hex 前缀占位符（即被误写成 value 串的）还原为 `{{key.field}}`（key 由解码 value 重算，field 取 value 内 field 或 `{{…}}` 内 '.' 后缀）→ 断言全部占位符前缀 ∈ funContext → save_flow(updateCount) + deploy_flow → 回读 regex 断言无残留。

> **⚠️ 编码风格实证（2026-09-08）：** 即使占位符 key 全部符合 `md5(8键canonical)`、funText 格式正确 `{{hex.model}}`，funContext **value 的 URL 编码风格仍会让前端公式框回退显示 `{{hash.model}}` 原文**——python `urllib.parse.quote` 默认把 `:`/`,` 转义成 `%3A`/`%2C`（值形如 `%7B%22field%22%3A%22money_…%2C…`）时前端匹配失败；重编码为存储风格 `urllib.parse.quote(json.dumps(d, ensure_ascii=False, separators=(',',':')), safe=':,.-_/?')`（仅转义 `"` `{` `}` 与非 ASCII，`,` `:` 原样，形如 `%7B%22field%22:%22money_…%22,%22…`）后，硬刷新页面公式框显示中文正常。⚠️ record 类型 funContext 是普通 dict（非 hash→URL 映射），重编码时须跳过；改后回读确认服务端未改写回 python 风格。**【2026-09-08 夜 builder 修复：funContext value 编码已内置该风格 `quote(safe=":,-._/?")`，且 funType 省略时按 formula 是否以函数名 `XXX(` 开头自动识别（CONCAT/IF → fun）——此后新建流程不再触发本节问题；仅存量脏流程按本节外科修复。】**

**关联：** #39 渲染键清单（addable/content 等）；example/运算节点示例.md 知识点 8（fieldNames/编码）与 9（content 卡片文案）；node-types 十八节 ⚠️。

---

## 53. switch（开关）控件触发条件值 = activeValue 字符串（2026-09-08 新建流程实测）

**现象：** 需求「工作表事件触发：触发字段【开关】，条件 开关 等于 是」。字段实为 switch 控件：`fetch_form_fields` 只返回 `{"model": "switch_xxx", "type": "switch"}`（**无 options 键**），raw 字段配置里也没有 label/value 对——按 #51 的「label→value 映射」去找会落空：

```json
{"name": "开关", "model": "switch_1788751648788_345191", "type": "switch",
 "options": {"activeValue": "1", "inactiveValue": "0", "defaultValue": false, ...}}
```

**修法：** 「是/开」= raw 控件 `options.activeValue`（本例 `"1"`；「否/关」= `inactiveValue`）。startCondition queryItem 形态：`{"rule": "eq", "valueType": "1", "val": "1", "name": None, "field": <model>, "columnName": "开关", "type": "switch", "valType": "switch"}`——val 纯字符串、无 `value` 键。已按此新建「开关触发新增编辑流程」（DB 2097254326793056257）save+deploy+回读通过。

**⚠️ 边界（未完全验证）：** 该环境 405 条流程里扫描前 30 条未找到 UI 原生 switch 触发条件样本，val 纯字符串形态系按字段存储值（activeValue）推断；若用户反馈设计器条件值框显示不对（#51 同款「未选中」现象），以 UI 原生保存后的样本为准更正本条。

---

## 54. queryById 返回的 processJson 是 JSON 字符串，回读前必须 json.loads（2026-09-08 实测）

**现象：** save+deploy 后用 `GET /act/process/extActProcess/queryById?id=<DBid>` 回读，`result.processJson` 是 **str**（JSON 字符串）不是 dict——直接递归 walk 找 `startCondition` 找不到，断言误报失败，多开一轮纯验证回合（流程本身早已创建发布成功）。

**修法：** 回读优先按 SKILL.md「回读校验策略」用 `query_flow(api, token, flow_id=<id>)`（wrapper 已解析，`rec['processJson']` 直接是 dict）；用 queryById 兜底（gotchas #51 的兜底路径）时先 `pj = json.loads(rec['processJson']) if isinstance(rec['processJson'], str) else rec['processJson']` 再 walk。

> ⚠️ **query_flow 传参（2026-09-09 补）**：签名 `query_flow(api, token, process_key=None, process_name=None, flow_id=None, tenant_id=None)`——第 3 **位置**参数是 `process_key`，`flow_id` 必须**关键字**传（位置传 id 会被当 processKey 查，真实 key 是 `process<ts>` → 返回 None，误判「流程没建成」多花整轮）。上方 `query_flow(flow_id)` 是简写，勿照抄。

## 55. 消息节点引用函数（function）节点计算结果：内容键是 attr.templateContext，jsonContext 是 6 键 + 模板后缀写「结果」（2026-09-08 实证）

`example/消息节点.md` 知识点 3 只覆盖**表字段**引用（4 键 JSON），补充函数运算结果引用的形态（2026-09-08 实证）：

- **消息正文键 = `attr.templateContext`**（builder 把 config 的 `attr.noticeContent` 映射成它）。⚠️ save 前自愈时若误写 `attr.noticeContent`，服务端会**原样双存两个键**（templateContext 仍是旧值、noticeContent 多出无效键），消息渲染读 templateContext → 表现"改了没生效"。自愈永远写 `templateContext`。
- jsonContext 值 = base64(6 键紧凑 JSON)，键序：`field:"result"`、`formTableCode:"function-{funType}"`（如 function-fun/function-number）、`nodeId:<函数节点 id>`、`nodeType:"function"`、`operationMode:"cache"`、`decimals:2`（比表字段 4 键多 operationMode/decimals 两键）。
- hash 键 = `md5(该 6 键紧凑 JSON)`（与 4 键表字段同款 canonical 规则，见 `消息节点.md` 知识点 3）。
- 模板占位符后缀是**中文标签「结果」**（所有函数类型统一），即 `{{<md5key>.结果}}`——不是 `result`、不是字段 model。逐函数节点多行引用（每个运算节点一个 hash、模板一行一个）Round-trip 稳定，服务端不改写。
- 收件人（处理人）侧仍走 gotchas #49 的 `var.`+JSON（field `create_by`）或 `user.xxx` 前缀，与本条目无耦合。
- **症状锚（同日复现）**：消息照发、正文里占位符被解析成**空值**（如「取当前时间：」后空白），不是原样显示 `{{...}}` 文本 → jsonContext 键形写错（曾按公式 funContext 8 键 formNodeId/variableValue 形态写）或占位符后缀不是「结果」；占位符**原样显示**才是 hash 不在 jsonContext / 未部署生效。按本条目修正后重新触发即出值。

> ⚠️ **覆盖范围：本条只实证了「表字段」与「函数节点结果」两种引用源。** get_one/get_more 查到的记录字段、data_add 新增/更新的字段、流程参数（upvariable）等作为消息模板引用源时，jsonContext 的键数/键序/后缀**均未实证**——不要按本条键数外推（表字段 4 键 → 函数结果 6 键的前车之鉴：外推必错）。需用时不要自行外推构造：停手向用户说明该引用源契约未实证，建议先在 UI 手工配置一次后回读其存储形态，或暂缓该引用。**例外：`get_one` 结果字段作正文引用已实证**（4 键 + `nodeType="search"`，2026-09-11）——⚠️ 仅限 `get_one`，**`get_more`（获取多条记录）的结果字段不支持作正文引用**（只能经「运算-统计条数」取数量后引用），形态与写见 node-types「八、通知节点」该段，**不必**再走「先 UI 手配一次回读」的流程；其余引用源（流程参数 upvariable、data_update 更新值等）仍按本条告警处理。

> ⚠️ **新建时禁止拿库内成品流当模板整节点复制（2026-09-09 教训）：** 本条契约明确，消息节点**直接按上文自拼**即可；禁止为单个消息节点去列全应用流程、再拉成品流全量 JSON 抄结构。库内同形态成品流若是早前 AI 会话按**旧契约**造的（4 键 jsonContext、占位符后缀=节点名、noticeContent 键双存等），照抄会把「消息取值全空」的旧 bug 扩散到新流。**契约只认本条文档**——不要尝试参照/鉴别环境内成品流（其他环境不会预置成品流，文档须自足）。

## 56. fun 节点公式必须写字段 model：写中文名 → builder 正则提取不到、funText 裸中文、节点取不到字段（2026-09-08 实证）

**现象：** 公式里写中文名（如 `CONCAT(名称,'-',描述)`）时 save+deploy 全绿、发布成功，但节点根本没挂字段引用——builder 按 `类型_时间戳_随机数` 正则从公式提取字段 ID 生成 funContext，中文名提取不到 → funText 无占位符、funContext 为空，引擎运行时取不到触发记录字段值。

**坑中坑（假绿）：** 回读断言 `re.findall('{{[0-9a-f]{32}\.', funText)` 得空集时断言"全部占位符∈funContext"恒真通过——占位符为空不算失败。回读必须断言**占位符数 == 公式里引用字段数（>0）**。（2026-09-09 补：无字段引用的函数如 `DATENOW()` **没有**占位符是正常的——funContext={}、funText 裸函数文本；断言口径即上式，0 字段公式允许 0 占位符，勿要求每个 fun 节点必有占位符，否则新建回读误报。）

**正确形态：** 公式里写字段 model（`CONCAT({{hash.model}},'-',{{hash.model}})` 由 builder 从 formula 自动生成），字段 model 同字段同上下文的 hash 与 UI 原生保存逐字节相同（对照 #54 记录值可复核）；修复后 funText 样例即 UI 原生形态 `{{ccad48e0….input_…}}`。fieldNames 只补中文展示名，不是取字段的途径。

## 57. 多记录 getMore 后禁止直连消息节点：引擎不逐行，必须 callActivity 子流程逐行发送（2026-09-09 用户定论+双回读实证）

**现象：** 定时/批量场景链 `get_more(多条) → message_system(收件人=行内 select-user 字段)` 能 save+deploy+回读全绿、设计器也显示「知会人: 客户」，但**运行时消息不逐行**（主流程只处理单记录上下文，多记录发消息"直接配置不支持"——用户原话）。data_update 有 getMore 批量契约（见组合 E2）不在此限，只有消息类节点受限。

**修复（2026-09-09「订单超时自动处理」完整跑通）：** 主链到 data_update 为止，其后再挂 **callActivity 子流程**（`isMulti:true`、`customProcessId`=子流程 DB id、`subFormTableObject`=父 getMore 的 formTableList 条目+`isSubStart:true`、listenerData MiniCallActivityListener + inVariableModels 4 条）；新建 **subEvent 三层子流程**，内部唯一节点 message_system，收件人 var 条目：

```python
"var." + json.dumps({"formTableCode": "<表code>", "formTableId": f"form_{父getMore节点id}_{<表code>}",
                     "nodeId": 父getMore节点id, "nodeType": "search",   # 子流程行上下文形态（nodeTypeMain=getMore）
                     "field": "<select-user model>", "fieldType": "select-user"}, ensure_ascii=False)
```

- 子流程 start 根：顶层/attr 全 subEvent（三层）；attr.formTableList[0]=subFormTableObject search 形态；root 渲染键/监听器常量照「主子流程配置示例.md」附录或例 资产领用发放改造示例.md 常量区。
- 发布子流程走 #47 配方（save → 回查 updateCount → POST designer saveFlow 补 customProcessId/processKey=process<DBid> → PUT deployProcess → /act/process/list 校验 key=process<DBid>）。
- 主流程 gm 的 formTableList 条目要补 `isSubStart:true`；主流程摘除消息节点后 save+deploy。
- 完整流程代码/自愈/回读断言 = create-flow.md **组合 H**（2026-09-09 已按本结论改写）。
- 主流程直连的 var `nodeType='getMore'` 形态在设计器能选到人（显示「知会人:客户」），运行不逐行——与子流程内 `nodeType='search'` 形态的区别是本次实证的关键。

## 57. 省市级联动（area-linkage）触发条件值：val=末级行政编码 + allVal=各级编码数组，写名称路径字符串 UI 显示"未选中"（2026-09-09 实测）

**现象：** 新建简流「省市级联动触发新增编辑流程」（八匹狼/流程对接/高级字段，触发字段=省市级联动，条件=等于 北京市/市辖区/海淀区）。API 按用户口述把 val 写成名称路径字符串 `"北京市/市辖区/海淀区"` → save/deploy 全绿、回读 JSON 也有值，但用户打开设计器：触发条件值**没有选中任何项**。

**真相：** 用户 UI 重选后 query_flow 对比，唯一差异在 queryItem 的值编码（rule/type/valType 等其余键不变）：

```json
// ❌ API 直写（名称路径字符串）：设计器解析不了，显示"未选中"，运行时也不匹配
{"rule": "eq", "ruleName": "等于", "valueType": "1",
 "val": "北京市/市辖区/海淀区", "name": null,
 "field": "area_linkage_xxx", "columnName": "省市级联动",
 "type": "area-linkage", "valType": "area-linkage"}

// ✅ UI 原生存储（用户重选后逐键对比）：
{"rule": "eq", "ruleName": "等于", "valueType": "1",
 "val": "110108",                                // ← 末级行政编码（海淀区）
 "name": null,
 "field": "area_linkage_xxx", "columnName": "省市级联动",
 "type": "area-linkage", "valType": "area-linkage",
 "allVal": ["110000", "110100", "110108"]}       // ← 各级行政编码数组（北京市/市辖区/海淀区）
```

- 触发条件值必须写**末级行政编码**（海淀区=`110108`），且必须带 **`allVal`=各级编码数组**。
- 行政编码 = 国标行政区划码（北京市 110000 / 市辖区 110100 / 海淀区 110108）；无把握时先 UI 选中一次再 query_flow 回读真值（本次即此法）。
- 关联：#51 同款现象（checkbox 写中文 label 显示未选中）；本条是 area-linkage 控件 + 编码数组形态。必读路径已同步：SKILL.md startCondition「控件族条件值形态」段 + create-flow.md 组合 F 要点 + trigger-types.md rule 全枚举注释。

## 58. GET /desform/api/fields/<code> 的字段数组在 result.fields，不在 result 本身：按 result 数组/records 解析会**静默空输出**（2026-09-09 实测）

**现象：** 探查字段写成 `(rr.get('result') or {}).get('records') or rr.get('result')` → result 是 dict 且无 records 键，回退拿到的仍是 dict 不是列表 → 字段打印**整段为空且无报错**，误以为"表没字段/接口不通"，多跑一轮才发现是结构猜错。

**真相：** result 结构 = `{"desformCode":…, "titleField":<主标题 model>, "desformName":…, "id":…, "fields":[…字段数组…]}`。字段元素键：`name`=中文名、`model`=控件编码（脚本侧一律用 model）、`type`、`options`——radio/select 内联选项在 `options.options[]`（`value`=label 文案同值，如 未付款/已超时）；date 控件 `options.timestamp:true` = 存储毫秒时间戳；select-user `options.customReturnField:"username"`。

**修法：** 字段探查一律用内置 `fetch_form_fields()`（已封装、按中文名返回 `{model,type,options}`），禁手写解析；确需 raw 用 `raw['result']['fields']`。同轮教训：任何没实证过形状的接口，先打印原文再写解析（见 #59）。

## 59. 新接口第一轮必须打印 response.text 再写解析；extActProcess/list 元素形态不稳（字符串/空/dict 都可能）（2026-09-09 实测）

**现象：** 探查应用下流程写 `(res.get('result') or {}).get('records')` 后直接 `x.get('id')` → `AttributeError: 'str' object has no attribute 'get'`（records 元素是**字符串 id** 而非 dict）；同一接口稍改参数 records 又返回 `[]` total 0。响应形状随参数/数据变化，凭猜必翻车，而且报错要等下一整轮才知道。

**修法：** 首次碰任何接口先 `print(r.text[:800])` 看真实形状再写解析；列表元素解析前加 `isinstance(x, dict)` 防御（非 dict 打印原文退出，别让 traceback 代替诊断）。已实证过的接口解析写法（#51/#54/SKILL.md 内嵌代码）直接抄，不要每轮重猜。字段接口形状见 #58。

## 60. Windows 控制台跑含中文 print 的脚本：加 PYTHONIOENCODING=utf-8，否则 GBK 乱码（2026-09-09 实测）

**现象：** `py -3 xxx.py` 直接执行，中文输出乱码（`== 应用内流程 ==` 显示成 `== Ӧ�������� ==`），干扰判读、一度误以为输出异常。

**修法：** 运行命令带 `PYTHONIOENCODING=utf-8 py -3 xxx.py`（或脚本内 `sys.stdout.reconfigure(encoding='utf-8')`）。纯显示层问题，不影响流程逻辑。

## 61. 模板常量区与目标环境一字不差时直接改 ①–⑤ 一次跑完，禁止"防呆自查"探查轮（2026-09-09 实测教训）

**现象：** 任务「新疆兵团/应用1 订单超时自动处理」（TENANT 1008 / APP 2095343423447621634 / 表 ws_f4fb69bd1f / 下单时间 date_…821243 / 支付状态 radio_…855357 / 客户 select_user_…464676）与 `example/定时批量处理逐行通知示例.md` ①–⑤ 常量区**完全相同**——模板本就是同款任务验证产物。实际却为"防呆自查"多跑了 4 轮探查（租户→应用→字段→同名流程），其中两轮因 #58/#59 响应结构假设错而返工。总耗时 ≈ 多轮**串行**（每轮=写脚本+运行+逐段分析），不是后端慢（单接口 3–10s）。

**修法：** 模板 ①–⑤ 常量（TENANT/APP/表 code/字段 model/日期/循环）与用户描述环境吻合 → 改常量直接 1 次 `py` 跑完。模板自带防呆：应用/表单在位 assert + 同名主流程存在即中止打印，无需"先看看再建"。回合预算见 SKILL.md「执行加速」#5/#6。

## 62. 用户已确认的能力 = 最终事实：禁止扫存量流程/下载设计器 bundle 考古序列化（2026-09-09 严重教训，用户判定"严重问题"）

**现象：** 任务「新疆兵团/应用1 库存不足自动补货提醒」需要「库存数量 ≤ 本行安全库存（同表两字段）」条件。用户已确认"设计器条件值能选同表字段"后，仍为拿到 UI 落库序列化形态：扫了 13 条存量流程（无样本）→ 下载 6.2MB 设计器前端 bundle（服务器 `/jeecg-boot/joa/miniDesFlow/js/`，23+ chunk）→ grep 压缩 JS 多轮（单行 minified 使 `grep -c` 失真、GBK 乱码、懒加载 chunk 不在 index.html 引用里等连环小坑）。最终序列化仍是按文档既有形态（变量引用对象）构造——考古零收益；结构正确性靠 save 后回读兜底。全程 20+ 分钟，此类简单流程按模板应 1 分钟（同日 #61 同款教训重演，用户已两次投诉耗时）。简流设计器是独立前端（MiniDesFlowModal iframe `/act/designer/miniDesFlow/index`），只以压缩产物存在于服务器，本机任何源码树都没有。

**修法（强制）：**
- 用户确认过的能力/事实 = 最终事实，直接按文档形态构造。禁止为"求证序列化格式"扫存量流程、禁止下载/反编译设计器 bundle。
- 结构/序列化正确性的**唯一校验手段**：save+deploy → queryById 回读核对（一轮秒级）；引擎真实取数效果靠首跑/手动触发，发现不对改一轮即可（save 200 但 UI/引擎不认的形态再多考古也看不出来）。
- **时间盒**：任何探查动作 2 次无果立即停止，转"按最可能形态构造 + 回读"。

## 63. 同表两字段比较（字段A ≤ 本行字段B）查询条件序列化：val=变量对象 + formNodeType search 自引用查询节点（2026-09-09 构造落库，待首跑实证）

**背景：** 定时扫描场景需要"库存数量 ≤ 安全库存"这类本行两字段比较，条件是每行各自的阈值，不是固定值。用户确认设计器条件值可选手表同表字段。**此形态按变量引用对象构造，已回读一致；引擎取数效果待 2026-09-10 08:00 首跑实证**（流程「库存不足自动补货提醒」2097571574512812033，租户 1008/应用1）。若首跑条件恒空或设计器值框显示"对象"，只需改 val 形态再 save+deploy 一轮。

```python
# get_one / get_more 条件（均落 attr.searchFieldGroup=[{id,matchType:"",queryItems:[...]}]，回读核对该键，不是顶层 conditions）
item = {
    "rule": "le", "ruleName": "小于等于", "valueType": "2",
    "val": {   # = 被比较字段（本行 B），formNodeId 指向查询节点自身 id
        "variableValue": "<B 字段 model>", "formTableCode": "<查询表 code>",
        "variableName": "<B 中文名>", "fieldType": "number",
        "formNodeType": "search", "formNodeId": "<查询节点自身 id>", "formNodeName": "<节点名>",
    },
    "name": None, "field": "<A 字段 model>", "columnName": "<A 中文名>",
    "type": "number", "valType": "variable",
}
```

配套结构（2026-09-09 已回读验证可用）：get_one(该条件, `emptyAction=3`) → `data_branch`「有/无」→ 有支内 get_more(同条件) → `data_add` 批量逐条（`addDataType=2` + `formTableSourceTaskId=<getMore节点id>` + `formTableSourceNodeType=getMore` + `formTableSourceGetDataType=1`，formModel 引用行字段用 `formNodeType:"getMore"` 变量对象，radio 固定值写选项文案，日期写 `{formNodeType:"system","variableValue":"nowDate"}`）→ notice（`noticeType:"email"`，收件人 `user.qinfeng` 顶层与 attr 双写）。「空轮不发」= get_one+数据分支实现，无需 getMore 直连 databranch（builder 不支持）。

## 64. 简单业务流程禁止连环提问：常规默认直接建，提问 ≤1 次且只问硬需求（2026-09-09 用户纠正）

**现象：** 同日上午「系统维护公告定时发送」被批"1 分钟该建好"，下午「库存不足自动补货提醒」又连环抛出 4 个 AskUserQuestion（采购员账号/空轮是否发/邮件形式/条件能力），用户明确反馈"不会有询问"。其中"空轮不通知""一轮一封"属可推断常规默认，不该问；"条件值能否选同表字段"也应在探查出字段结构后自己按能力假设构造、交给回读+首跑验证（gotchas #62/#63），而非提问。

**修法（强制）：** 简单业务（定时扫描→落表→通知/邮件）默认：空轮不通知、通知一轮一次、收件人按用户真实姓名/语义推断（如"采购员"→该租户唯一带邮箱的相关用户）直接定；整体提问 ≤1 次，只问真正无法推断的硬需求（如多个候选人语义等价时）。问卷可选项避免诱导式提问。

## 65. 凭证/记忆里「已建 XX 流」= 过期快照候选：先 1 条 list 核实再决策，真冲突才提问且一次问透（2026-09-10 用户再次点名"还是问很多次、还是慢"）

**现象：** 全新建 announce（1008/应用1 全员系统公告「系统登录提醒」，09-10 15:00 仅一次）——凭证文件记 09-09 已建同调度同收件人「系统维护公告定时发送」flow 2097566197045985282。仅凭该快照就向用户发起第二轮「改既有流 vs 另建」冲突提问，随后为验证它连写 3 个探查脚本（query_flow 两参形态试错 / raw list / 跨三应用 queryById）；实测该流**早已被删**（queryById 三应用全 500），提问+探查全白费，单任务拖到 ~3min。真正建流只花 runner 3.1s。

**根因：** reference/记忆是对旧 session 落库状态的快照，流可被随时删除；「已建」≠「现在还在」。既把快照当真冲突发起了第二轮提问（违反 #64 提问 ≤1 次），又违反「命中 runner 直接跑」路由去写探查脚本轮。

**修法（强制）：**
1. 新建前若记忆/凭证有同调度同收件人存量记录 → 只允许 1 条 `extActProcess/list`（0.1s，头带 X-Tenant-Id+X-Low-App-ID）核实是否真在位——核实**内联建流脚本头部**或直接依赖 runner 自带同名防呆（真同名会中止并打印），**禁止**开成独立"探查脚本轮"。
2. 核实出真冲突 → 冲突处理与内容/命名等一切未知**合并进同一次 AskUserQuestion 一次问透**；核实显示已删/不存在 → 冲突问题不存在，按全新建单命令收工。
3. 凭证文件里"契约技巧"性记录（queryById 拿全 JSON 等）不是开探查轮的许可证——被旧记录误导时第一脚仍是单命令 runner。

## 66. 「每周一」等非 8 实名周期 runner 不支持：0 轮判定直接脚本轮 + 手工并入 attr 组合字段（2026-09-10「上周订单周报提醒」实测）

**现象：** 需求=每周一 09:00 扫描近7天订单发管理员。先花 6+ 轮（--help×2、grep、py -c、Read runner 源码）求证 runner 能否表达「每周一」，又花 2 次 py 失败在复用其内部函数签名上，单任务 ~8min（净执行仅 ~25s）。

**根因：** trigger-types.md 明写 timeCycle 只有 8 个 UI 实名（每分钟/每小时/每天/每月1号/每周三/周一到周五/每年12月31日/自定义），runner CYCLE_MAP 同源——**「每周一」不在其中**，引擎侧需 timeCycle="custom"+组合字段表达。文档已写结论却开轮求证，违反「文档已写禁止考古」。

**修法（强制）：**
1. **0 轮判定**：用户周期 ∉ 8 实名（如每周一/每周四）→ runner 直接不可用 → 走 create-flow 脚本轮，不必读 runner/help/源码确认。
2. **自定义周期唯一生效路径 = attr 组合字段**，build 后 save 前手工并入 `pj['attr']`：每周一 09:00 = `timeCycle:'custom' + hourType:3 + hourValues:[9] + dayOrWeekType:2 + weekValue:['MON'] + monthType:1`（秒级不动）；分钟位取 beginDateStr 的分钟（时间戳形态会丢分钟，字符串必须）。
3. 复用 runner 模块内部函数（import timer_job_runner）**先看 cmd_* 调用点**再传参：`get_fields`→原始字段 dict list（name=中文名/model）；`parse_conds(flds, code, name, node_id, node_name, spec_list, ts)` 第 6 参是 **conds 列表**非字符串；返回值 `(items, fns)` 需再 `insert_fns(pj, fns)`；`resolve_users(api, tok, tenant, [姓名])`。结构照抄 cmd_check（505-595 行）骨架即可。
4. 实测产物（1008/应用1「上周订单周报提醒」2097588261299617794）：`function(-7D) → data_get_one(ge_fn:-7D) → databranch 有数据→message_system admin/无数据空`，回读断言 timeCycle==custom && weekValue==['MON'] && hourValues==[9] 通过。

## 67. 探查脚本一轮打全：先 list 取现存参照 id 再 queryById，禁止照抄凭证旧 id（2026-09-10 复发）

**现象：** 建流前探查脚本 v1 直接 queryById 凭证文件记的「订单超时自动处理」2097562932984086529——该流 09-09 建、次日已被删，queryById 返回 None 整轮白费；v2/v3 又分开打表结构/字段/用户，探查共 3 轮。

**修法（强制）：** 一轮探查脚本内按序执行：① `extActProcess/list`（X-Tenant-Id+X-Low-App-ID）列现存流程拿**真实**参照 id（凭证旧 id 一律先 list 核对在位）→ ② `tenantAppFormList` 打全两级表单结构 → ③ `desform/api/fields/<code>` 打全目标表字段（含 options.timestamp）→ ④ `sys/user/list` 打全用户。四件事同一 py 一次打完，禁止按依赖拆轮。

## 68. 定时壳周期口语语义不定 = 先确认再建；用户说「一条流程就行」是语义读错的信号，禁止按错误假设探测引擎（2026-09-10「每年上半年+每个月最后一天」实测教训）

**现象：** 需求=1008/应用1 新建定时壳「每年**上半月**触发，每个月最后一天触发」，begin 2026-09-10 09:00。误把「上半月」读成「每月1~15号每天」→ 断言单条 custom 周期装不下「1-15 每天 + 月末」→ 提拆两条流程被否（用户：一个流程就可以实现）；仍没翻语义，反按错误假设去探测引擎表达力（2 轮 generateExecTime 试 dayValues=[1..15,30]、32、99 等 L 列表写法），第二轮 AskUserQuestion 再被否，最后用户贴 UI 截图澄清：**上半月=上半年(1~6月)**，「固定月×每月最后一天」=自定义面板原生单条组合。真正建流 ~4s；全程慢在错误语义上的探测与追问（当天截图本会话读不了还多走了一轮 vision skill）。

**根因：** ①周期口语（上半月/上半年/每隔N天/工作日…）有歧义时直接按自己的理解定了方案，没先让用户一句话或贴截图确认；②用户对方案说「不需要拆/一条就行」= 语义理解错误的**强信号**——正确动作是回到需求词重读并请用户确认，却继续去证明「引擎做不了我理解的那条」= 答非所问；③本文件组合字段语义、trigger-types 早已写明 monthValues 字符串数组与 dayValue=5=月末，按错误语义查文档自然对不上。

**修法（强制）：**
1. timerEvent 周期语义不确定 → 建前并入同一次提问请用户给准确规则（一句话/UI 截图），**禁止先探测引擎表达力**——语义错时探测全白耗。
2. 用户反驳方案（"不用拆/一个就行"）→ 立即重读需求词找歧义并确认，不是辩引擎能力。
3. **固定月×月末 = 单条 custom 原生组合**（实测「定时触发流程-每年上半年最后一天」2097598817473593346）：attr=hourType3+hourValues=[9]+dayOrWeekType1+dayValue=5(每月最后一天)+monthType2+monthValues=**字符串数组** ["1".."6"]（整数数组引擎能命中但 UI 面板形态错，2026-09-10 用户定稿）；hour 取用户开始时间的小时，分钟位取 beginDateStr。
4. 含 dayValue=5 的组合**禁止 generateExecTime 验算**：预览把月末算成每月30号、2月不显示，个别月组（[1,2]）500 `Index: 2, Size: 2`——预览缺陷；校验=save+deploy+回读断言。dayValue=3 的 dayValues 值域仅 1-31 数值（32→空结果、99→被忽略）且落库**必须字符串数组**（见 #72），列表内无真·L，别再探测。

## 69. low-code act/process 域列表接口成功码=code:0（非 200）：核实/防呆脚本写 `code==200` 守卫会误触发白跑一轮（2026-09-09 实测）

**现象：** 建流前核实轮脚本写 `if j.get('code')!=200: print(r.text); exit`——`extActProcess/list` 成功时返回 `{"code":0,"message":"","result":{records...}}`，守卫误判为失败把正常响应当错误截断打印（records 一条没打印），整轮作废重写重跑（0.1s 操作变两轮往返）。

**根因：** 把常规 `/sys/*`、desform 域接口「成功码=200」的惯性照搬到 low-code `/act/process/*` 端点；该域成功=code:0（与 Jeecg 旧版 Result code=0 同源，列表接口尤为常见）。

**修法（强制）：** ① act/process 域接口判成功只看 `(j.get('result') or {}).get('records')` 存在即可——runner `no_dup` 正是此写法（无任何 code 判断）；② 新域/新接口第一轮仍按 #59 先 `print(r.text[:500])` 再写解析，不确定就先打后解、勿写可能误判的 guard；③ 防呆核实的存量打印（名称+id）放脚本头部直出，不依赖 guard 分支。

## 70. 「建前同名核实」独立成一轮 = 固定多一轮往返：核实必须内联建流脚本头部，与 save+deploy 同一次 py（2026-09-09 实测复发）

**现象：** 本次把核实拆成独立脚本轮先跑（且 #69 守卫错一次、再修再跑），确认无冲突后才另写建流脚本再跑一轮。SKILL 规则 #12/#65 本就允许「核实内联建流脚本头部」，实操仍开成独立轮。

**根因：** 心理上把「核实」当独立任务；实际 list 0.1s + 同名 assert + build/save/deploy/回读无依赖延迟，可同 py 顺序执行——内联后核实的存量打印天然成为建流日志的一部分，还顺带避免核实轮与建流轮之间被其他会话删改造成的竞态。

**修法（强制）：** 建新流且凭证/记忆有同调度存量记录 → 建流脚本头 5 行内 `requests.get(api+'/act/process/extActProcess/list', headers=h, params={'pageNo':1,'pageSize':200})` 打印存量名称+id，同名 assert 中止；无冲突继续 build/save/deploy/回读——**一条 py 命令就是终态**。独立核实轮只保留给「输出需人类看图决策」的场景，且一轮打印给全（#67）。

## 71. 复刻 runner/模板骨架禁止整文件 Read：grep 定行号后 offset/limit 只读 cmd_* 命中节；复用函数直接 import（2026-09-09 实测）

**现象：** 自定义周期建流需抄 `timer_job_runner.py` 的 cmd_scan 骨架，直接整文件 Read 651 行（shell/announce/check/subflow 全部卷入）拖慢该轮；实际只需 cmd_scan 一节 ~145 行 + back/walk 短函数。

**根因：** 此前 #66 已写「结构照抄 cmd_check（505-595 行）」仍未养成 `grep "^def cmd_"` → offset/limit 精读的习惯；函数签名疑问（parse_conds 参数/返回值）其实 import + 看调用点即可解决，无需通读全文。

**修法（强制）：** 复用 runner 内部骨架 → 先 `grep -n "^def cmd_scan|^def cmd_check|^def back|^def parse_conds|^def insert_fns"` 定行号，再 `Read offset/limit` **只读命中节**；骨架函数（parse_conds/insert_fns/relabel_levels/walk/back）直接 `import timer_job_runner as tjr` 复用，签名不确定查 cmd_* 调用点行（首参 a=argparse namespace）。**骨架按动作选**：扫描批改（get_more→data_update/批量新增）=cmd_scan 的 gm/du 变异段（E2 契约）；有/无记录分支通知=cmd_check；逐行发消息=callActivity（#57）。

## 72. timerEvent custom 固定号 dayValues 落库必须字符串数组：整数数组能 save+验算但设计器绑定错（2026-09-10 用户 UI 手工修复后回读比对实证）

**现象：** 建「定时触发流程-每年上半年每月1、3、5号」（1008/应用1）初版按旧文档把 dayValues 写成整数 `[1,3,5]`（dayOrWeekType1+dayValue3+monthType2+monthValues["1".."6"]+hourType3+[9]）——save+deploy 成功、generateExecTime 验算未来7次全对（2027-01-01/01-03/01-05/02-01/02-03/02-05/03-01 09:00），用户测试发现**绑定不对**，UI 手工重勾 1、3、5 修复。回读比对（updateCount 1→3）：修复版 attr 唯一差异 = dayValues 整数 `[1,3,5]` → **字符串数组 `["1","3","5"]`**；monthValues/hourValues/beginDateStr/times 一字未变。

**根因：** dayValues 与 monthValues 同律——设计器「自定义」面板保存形态是**字符串数组**；整数数组引擎预览能算、save/deploy 也过，但设计器面板绑定/勾选显示错。generateExecTime 预览参数走 HTTP form 重复参数（自动字符串化），掩盖了落库类型差异——**验算通过 ≠ UI 绑定对**。

**修法（强制）：**
1. custom 固定号组合（dayValue=3）dayValues 落库写**字符串数组**（`["1","3","5"]`），与 monthValues 同律；值域 1-31（32→空结果、99→被忽略）。旧文档「整数列表」写法作废（#68 末尾已同步修正）。
2. 结构正确性校验=save+deploy+**回读断言比对类型**：`assert a['dayValues']==['1','3','5']`——字符串比对天然区分 int/list，整数版首轮即断言失败。
3. 实测定稿：定时触发流程-每年上半年每月1、3、5号 `2097615073585070082`（dayValue3+dayValues=["1","3","5"]+monthType2+monthValues["1".."6"]+hourType3+[9]，begin 2026-09-10 09:00 无 end → 首跑 2027-01-01 09:00 跨年）。custom-cycle.md §一/§二 已按字符串数组修正。

## 73. 路由标「直接跑 runner」→ 两个 runner 源码=禁止读区（--help/grep/Read 全免）：参数未知直接跑，SystemExit 秒级自述；用户耗时红线≈单任务 1 分钟（2026-09-10 实测：6 轮源码 grep 后才建，9.1s 建流仍判定超时）

**现象：** 「预约就诊提醒-每天」（1008/应用1，scan 路由）实际建流 9.1s 一次过，却先对 timer_job_runner.py / timer_notify_runner.py 花 ~6 轮 --help+grep+Read 求证 cycle 预置、--at 默认、--begin 是否必填、--to-field 类型、--update 是否必带——SKILL.md usage 与 argparse 默认（--cycle 每天/--at 07:00/--title「提醒」/--body「请及时处理。」）早已回答；另存量核实轮因响应键假设错崩 2 轮。用户判定：「为什么耗时这么久，之前 1m 就能完工」。

**根因：** ①把「源码求证参数」当比「跑一次看报错」更稳的路径——实际 runner 防呆 SystemExit 自带字段名与候选值自述（如扫描表不存在打印全表单名），错跑 ≤5s 改参即重试，源码求证无终止判据、每轮 5-15s 纯开销；②路由表与执行加速 #11 只把 example/gotchas/node-types 列禁区，**没把 runner 自身源码列进去**——留了口子（#71 只管「复刻骨架禁整文件 Read」，管不到「分段 grep 求证 argv」）；③凭证文件（唯一凭证源，内含租户全集与各租户应用 lowAppId）未按「首条 Bash 前 Read」先读，拖到源码轮之后。

**修法（强制）：**
1. 「直接跑 runner」路由下，timer_job_runner.py / timer_notify_runner.py 源码 = 与 example/gotchas **同权禁止读**（--help/grep/Read/分段节选全免）；argv 契约 = SKILL.md usage + CLI 补遗段，够用即单命令跑。
2. 参数报错 = 终态信息：SystemExit 自述错哪改哪，改参重跑 ≤1 次，**禁止转源码轮**。
3. 耗时红线：单任务（一条流的建/改）从需求到收工汇报 ≈1 分钟（用户基准）；工具轮 ≥3 即按 #62「按最可能形态构造 + save+deploy 回读」收敛，不自查「是不是还该求证什么」。

## 74. act/process 域列表响应终版形态：result=分页 dict{records,…}（非裸数组）、记录名称键=processName（无 name 键）；新域解析先打 records[0].keys()（2026-09-10 实测，补 #59/#69 落地键）

**现象：** 存量核实轮写 `rows = j.get('result')` 后 `rows[0]` → KeyError:0（result 实为分页 dict）；改 `f.get('name')` → 6 条流程名全 None（名称键是 processName）。核实 0.1s 的活崩成 3 轮（每崩一轮 = 一进一出往返）。

**根因：** #59 只警告「形态不稳/先 print text」、#69 只给 code:0 判定，都没落**具体键**；键名靠猜（name/rows 顶层）两连崩，且两崩都在拿到数据之后——输出作废最亏。

**修法（强制）：** ① 解析样板：`res = j.get('result') or {}; rows = res.get('records') if isinstance(res, dict) else (res or [])`；② 名称键一律 `f.get('processName')`（record 键清单：processName/processKey/processStatus/startType/tenantId/lowAppId/id/…，无 name）；③ 新域第一轮 print(r.text[:300]) 与 print(首条 keys) 同屏先出，键名不再靠猜。

## 75. timer_notify_runner.get_fields 返回字段 dict 列表（键 name=中文名/model/type/options），非 {中文名:…} 索引 dict；select-user 的 options.customReturnField=username 可预判逐行站内可行（2026-09-10 实测）

**现象：** 探查脚本对 get_fields 结果直接 `flds.items()` → AttributeError 'list' object has no attribute 'items'；崩点已在字段数据拿全之后，整轮输出作废重跑。

**根因：** get_fields（timer_notify_runner 的 fields 接口封装）返回**列表**，miniflow_creator 的 fetch_form_fields 返回 {中文名:…} dict——两个同名概念不同型，混用即崩。

**修法（强制）：** ① get_fields 结果遍历用 `for f in flds: f['name']/f['model']/f['type']`；② 打印 options 前 ~120 字符可同轮预判：select-user 有 customReturnField=username（→可作逐行站内收件人）、date 有 options.timestamp=true（→毫秒级条件，可用 eq_fn:today），把「字段形态轮」并进既有轮次，不另开。

## 76. 防呆断言禁止用记忆快照值做相等断言：fetch_app_forms 的 app 返回 {id, name, forms}，lowAppId 键名是 `id`（2026-09-10 新建 dateFieldEvent 首跑失败实证）

**现象：** 租户 1008/应用2 新建 dateFieldEvent 壳，应用名/工作表/字段按中文名全部定位成功，脚本却在防呆行崩：`assert str(app.get('lowAppId')) == '2096920382883459074'` → 无 lowAppId 键 → get 返回 None → assert 必挂。多出一整轮 edit×2 + 脚本重跑（耗时主因不是接口慢，是这轮失败）。

**根因：** 双重自我埋雷——① 键名靠文档/记忆猜：create-flow.md 只写了 `forms[].code/name/titleField`，没写 app 自身键名；实际响应 `app={id: <lowAppId>, name, forms}`，lowAppId 键就是 `id`；② 防呆断言值抄记忆快照（记忆规则自己写着「快照=已删/已变候选」），值与运行时脱钩即白跑。API 数据从头到尾是对的，输出全作废只因断言写得蠢。

**修法（强制）：** ① 取 id 用运行时返回：`low_app_id = str(app['id'])`；键名不明先 `print(app.keys())` 或 any-key 兜底 `next((app[k] for k in ('lowAppId', 'appId', 'id') if app.get(k)), '')`；② 防呆只断言「存在/名称匹配」，禁止与记忆/文档值做 `==` 相等断言；③ 同族连坐（#65/#67/#74）：一切 id（已建流 id、租户表 id、app id、记录名称键）都以运行时为准，记忆/文档只当提示词。2026-09-10 同场景修正后 = 取 `app['id']` 一次 py 跑通（save+deploy+回读断言全过）。

## 58. data_update 引用运算节点结果的条目缺 valueType/valType → 设计器把值显示成具体时间而非变量引用；function 登记须按链序（2026-09-09 实测）

**现象：** 审批流「部门负责人审核」前插 日期加减运算节点（申请日期+50D）+ 更新记录节点把结果写回主表「需求到货日期」。API 直写 save/deploy 全绿、回读 JSON 中 `updateFields[].val` 也是正确的 function 引用（`formNodeType="function"` / `variableValue="result"`），但用户在设计器打开更新节点：目标日期字段的值框显示成**一个具体时间**，不是「运算节点 → 结果」的变量引用。

**真相（用户 UI 对照逐键比对）：** updateFields 条目缺了 `valueType: 3` + `valType: "variable"` 两键——只要 `val` 是对象（变量引用），**条目顶层**必须带这两键（node-types「三」类型 2 注释"引用变量时必须为 3"，手拼条目时极易漏）；date 字段另带 `options: {"format": "yyyy-MM-dd"}`。缺键不报错：服务端照存 dict，设计器却按固定字面量解析显示。完整形态（function 结果引用条目）见 miniflow-node-types.md「三」3.1 新增 ⚠️ 段。

**次要点（同场景一并整改）：** function 运算节点的 formTableList 登记（`nodeType=function`、code=`function-date`）**不能一律 append 列表尾部**——登记顺序=设计器对下游节点可引用数据源的解析顺序，须按链序插到 start 表条目（`nodeId=start, nodeType=table`）之后（get_more 早有"插到目标节点那条之前"规范，见 SKILL.md get_more 段；本次实测 function 同规范，曾因 append 到下游 data_add 条目之后致引用节点解析异常）。

**修法：** query_flow 拉最新 → 定位 data_update 节点 → `updateFields[0]` setdefault `valueType=3 / valType='variable' / options.format` → 把 function-date 登记从尾部摘下插到 start 表条目之后 → save_flow + deploy_flow → 回读断言三键在位、登记 index == start 条目 index+1 → 提示用户刷新设计器核对。

**关联：** #41（data_add formModel 引 function 结果——formModel 条目无 valueType 体系，勿混）；#54/#55（运算节点 UI 显示错乱的 funText/funContext hash 体系，属另一独立问题）。必读路径已同步：SKILL.md「修改已有简流·追加修改要点」+ node-types「三」3.1 ⚠️ 段 + 运算节点示例.md 知识点 5。

## 59. exclusive 分支条件可直接引用运算节点结果：branchForm=function-{funType} + field="result"，无需 upvariable 中转流程参数（2026-09-09 用户 UI 确认）

**场景：** 审批流加「时长>10天走总监审批、≤10天走部长审批」——date-diff 运算节点（申请日期→当前日期时长）后接排他网关分流。

**初版（绕路）：** 照 18.2 老话术「统计结果常配合 upvariable 存入流程参数再用 exclusive 判断」搭了中转：更新流程参数节点（data_update_variable，updateVariable[].val=function 引用）+ 根 `variableList` 声明参数 + 分支条件 `field=参数名`（branchForm=流程参数 `_variable_`）。

**用户指正：** 分支判断**可直接用运算节点结果**，无需流程参数中转。改为直引后 save/deploy/回读全绿，用户设计器核对显示正确、分流实测可用。

**直引形态**（运算结果 与 常量 比较，完整代码见 miniflow-node-types.md「四」4.4.1）：

```python
# 分支 attr（条件分支 branchType=1）
"branchForm": {"formTableCode": "function-date-diff",   # function-{funType}
               "formNodeId": "<运算节点ID>",
               "formNodeType": "function"},
"formTableCode": "function-date-diff",                  # 同 branchForm.formTableCode
# conditionGroup.queryItems[0]
{"rule": "gt", "ruleName": "大于", "valueType": "1", "val": 10,   # 比较常量
 "name": None, "field": "result",                      # ⚠️ 恒为 "result"（运算节点输出列）
 "columnName": "结果", "type": "number", "valType": "number"}
```

- 适用 funType → formTableCode：date→function-date、date-diff→function-date-diff、number→function-number、fun→function-fun、record→function-record；`field` 一律 `result`。
- **前提：** 运算节点 `function-{funType}` 虚拟表已在 formTableList 按链序登记（#58 同款规则），否则设计器分支字段源解析不到。
- **补集分支（>N / ≤N）** 第二条直接用默认分支（isDefault=true / branchType=2 / conditionGroup=[]），不必再写反向条件（互为补集且需求含等号边）。
- **变体：运算结果 vs 运算结果（双运算节点互比，2026-09-09 用户 UI 确认）：** 需求升级为「计算申请时长结果 ≥ 获取多条记录统计条数结果 → 总监审批，否则部长审批」。subject 保持本分支 branchForm 所指运算、field 仍 `result`；**比较值 val 换成另一运算节点的 result 变量引用**：`valueType: 3` + `valType: "variable"` + `val={formNodeType:"function", variableValue:"result", formTableCode:"function-record", formNodeId:<统计节点id>, formNodeName:"统计记录条数", operationMode:"everyTime", decimals:2}`——record 型统计节点 operationMode 固定 everyTime。save/deploy/回读/设计器显示全绿。额外前提同主体四点 + **统计节点（funType=record）自身**要满足：funContext.nodeId=上游 get_more 节点 id、getDataType 与 get_more 一致（18.2），且两个运算节点都在 formTableList 按链序登记。
- **关联：** #41/#58 是 data_add formModel / data_update updateFields 的 val 对象形态，与分支条件的 field='result'+branchForm 形态不同，勿混用；upvariable 中转仍适用于流程参数类业务。必读路径已同步：node-types「四」4.4.1（含双运算互比变体）+ node-types 18.2 注 + SKILL.md「修改已有简流·追加修改要点」。

## 60. fun 公式引用运算节点结果：funContext canonical 是 10 键（表字段 8 键 + operationMode/decimals 夹在 formNodeName 与 tableText 之间），按 8 键算 hash → 公式框回退 {{hash.result}} 原文（2026-09-09 实测，UI 样本逐字节对齐）

**现象：** 函数计算节点 `ABS(取 date-diff 运算结果)` 用 API 构造：先按表字段 **8 键** canonical（field/formTableCode/formNodeId/formNodeType/variableValue/formNodeName/tableText/fieldText）算 key → save/deploy/回读全绿，但设计器公式框显示 `ABS({{fea71e46….result}})` 原文而非中文公式。

**真相：** 公式里引用的若是**运算节点结果**（非表字段），前端 canonical 是 **10 键**：8 键基础上在 `formNodeName` 之后、`tableText` 之前插入 `operationMode`、`decimals`。UI 手配样本（用户在设计器「函数计算」流程手加 ABS 节点，2026-09-09）解码原文：

```json
{"field": "result", "formTableCode": "function-date-diff", "formNodeId": "<date-diff节点id>", "formNodeType": "function", "variableValue": "result", "formNodeName": "<运算节点名>", "operationMode": "cache", "decimals": 2, "tableText": "<运算节点名>", "fieldText": "结果"}
```

funText 占位符后缀是 `.result`（不是中文「结果」）；content 卡片形如 `ABS(时长-结果)`；节点 attr 的 `operationMode`/`decimals` 顶层键与 canonical 内的两键取值一致（date/date-diff/number/fun 来源= cache，**record 来源 = everyTime**——2026-09-09 第二 UI 样本实证，canonical 的 operationMode 跟随来源节点模式，勿恒写 cache）。

**修法：** canonical 按 10 键、键序照上重算 `md5(compact, ensure_ascii=False)` → funContext 值按存储风格编码（`urllib.parse.quote(cs, safe=':,.-_/?')`）→ funText 换新 key → save+deploy → 回读断言 `key == md5(解码后 10 键 canonical)`。

**收尾实证（2026-09-09）：** 用户在设计器打开该 ABS 节点**手动重存一次**后回读，存储与 API 构造产物**逐字节一致**（key/canonical/编码全同）→ 契约已对齐；若此时显示仍为原文，是前端缓存/旧标签页所致（硬刷新/重开设计器），不要再改存储。

> ⚠️ **占位符括号形态铁律（2026-09-09 追加实证）：** funText 占位符必须**连续闭合** `ABS({{<32hex>.result}})`——曾用易错 f-string 折叠模板产出 `ABS({{<32hex>}.result})`（闭合 `}` 插到了 `.result` 之前），前端解析不成占位符 → 公式框恒显示原文；该形态与"hash 不匹配"症状相同但**存储 canonical/key 全对**，且 UI 打开重选字段后会自动改写成正确形态（存字节对比即可识别：`}.result` vs `.result}}`）。回读断言不要只查 funText 含 `{{`，要断言 `re.search(r'\{\{[0-9a-f]{32}\}\}\.', ft)` 无命中（即闭合符在 suffix 之后）。

**关联：** #54（表字段引用 8 键 canonical 与存储编码风格）；#55（消息模板引用函数结果走 templateContext/jsonContext **6 键**）——三套机制勿混：公式 funContext **10 键** / 消息 jsonContext **6 键** / val 对象引用（#41/#58 无 hash）。必读路径已同步：node-types「十八」⚠️ 段。

## 61. 组织查询条件值跨租户陷阱：部门树与角色列表必须按当前租户过滤（2026-09-09 实测）

**现象：** 新建含「从组织架构查询部门 / 角色」节点（get_one_sysinfo，selectType=5/6）的流程，`conditions` 的 `departName`/`roleName` 值直接取接口返回的「第一条」名称 → save/deploy/回读全绿，但用户核对指出该部门/角色**不在当前租户**（运行查询也匹配不到）。

**真相（两条接口各一个坑）：**

1. `/sys/sysDepart/queryTreeList` **不带 X-Tenant-Id 头**时返回**跨组织全量部门树**，首层根节点即各家组织的公司节点（含他组织根）；取「第一条」极易命中他组织的根部门，例如取到另一组织的公司名。
2. `/sys/role/list` 实测**带不带 X-Tenant-Id 头返回结果完全相同**（接口本身不做租户过滤）；角色记录的 `tenantId` 混杂本租户 id、`0`、`1`、`null`、他租户 id 多类——用 `('', '0', 'None')` 宽匹配兜底会命中根租户 / 他租户角色（曾命中他组织角色）。

**修法：**

1. 先 `GET /sys/tenant/list?pageSize=200` 按组织名定位**当前租户 id**（注意与部门树首层组织公司名不是同一张表）。
2. 部门：**带 `X-Tenant-Id=<当前租户id>`** 调 `queryTreeList`，返回的即该租户直属部门列表，取其名称做条件值（无头返回的首层根是各组织根，禁止当取值源）。
3. 角色：带头调用后仍须在结果内按 **`tenantId == 当前租户id` 严格相等**过滤（禁止 `''/0/None` 宽匹配）；同一租户可能只有一条角色记录，该条才是本租户角色。
4. `conditions` 的 val 必须 eq 本租户真实 `departName`/`roleName`——写他组织名称能 save/deploy，但运行按租户上下文查不到（等同 org-role 控件写别租户 roleCode 的静默失效，见 SKILL.md startCondition 规则码段）。
5. 改值属结构内条件改动，save+deploy 后回读核对 queryItem 的 val。

**关联：** `api-reference.md`「查询部门树 / 查询角色列表」两接口段（已同步）；`example/获取单个用户示例.md`「6」段（已同步）；node-types「十四」组织查询示例（ⓓⓔⓕ 条件值为演示用名，勿照抄当条件值）。

## 77. dateFieldEvent 触发条件：「日期字段=今天」条件行可写且必须写 —— variable「Today」形态（2026-09-09 用户 UI 补行实证，推翻「勿写条件行」结论）

**现象：** 建「预约表按日期触发-多条件」dateFieldEvent 壳（预约日期当天 15:00、不重复、11 条 API 条件全「且」）时，按早期结论把「预约日期 等于 今天」**省略**（认为由 triggerField+executeType=1 承载）。用户核对后**在 UI 手工补上该行**并要求对照。

**真相：** 日期条件行不是不能写，而是必须写成**系统变量「今天」**形态——与 triggerField+executeType 调度**并存**才是 UI 全貌。用户补行实测样本（row12，插在条件组末尾；组 id/其余 11 行 API 产物被 UI 保存**原样保留**，含 id `1788952549087x` 未重写）：

```json
{"id": "1022104301599891456", "columnName": "预约日期", "field": "date_1788940622445_600374",
 "rule": "eq", "ruleName": "等于", "valueType": 3,
 "val": {"formNodeType": "system", "variableValue": "Today", "variableName": "今天"},
 "type": "date", "valType": "variable"}
```

要点：`valueType` 是**数字 3**（非字符串 "1"）；`val`=三键系统变量对象（formNodeType:'system' / variableValue:'Today' / variableName:'今天'，与 #41 date 运算节点 dateFieldVal 的 nowDate/当前日期 同族）；`type`=date（字段控件类型）、`valType`='variable'；行无 `name` 键；id 为 UI 雪花串。⛔ `val` 写日期字符串 / 毫秒 int / `Today` 裸字符串 全错（恒不成立或 UI 显示异常）——只有此对象形态有效。

**语义边界：** 条件行=记录级过滤（预约日期==今天），调度=每条记录 triggerField 到期当天 executeType=1 时刻触发，两者并存不冲突。runner `--conds` **2026-09-10 起直接支持本形态**（`预约日期=eq:今天`，全规则 DSL；旧「仅 eq/ne、值含冒号解析错、需手工并入脚本」结论作废）——矩阵见 `trigger-types.md` dateFieldEvent 节，白名单外控件的处理见 #78。

**关联：** #65（快照流可能已删——本会话实测应用2 `extActProcess/list` 已空，旧快照 -管理员/-每月 等均不在）；trigger-types.md dateFieldEvent 节（已同步修正）。

## 78. dateFieldEvent runner `--conds` 白名单外 6 类控件：先按名单预筛走两段式，禁止喂 runner 反复试跑（2026-09-10 实测，24 条件流 + 耗时复盘）

**现象：** 建「预约表按日期触发-24条件」（24 行全且）时，`datefield --conds` **每遇一个不支持类型才报一次错**（`触发条件暂不支持字段类型 <type>(字段「XX」)`），先后被 `rate`(评分)、`select-depart-post`(岗位) 挡住 → **两次整跑报废**（各 ~3s + 决策轮）。

**白名单外 6 类（仅 为空/不为空）：** `rate` / `color` / `slider` / `phone` / `email` / **`select-depart-post`（部门+岗位联动，字段名常叫「岗位」，易误判为已支持的 select-position）**。判定源码=timer_job_runner.py 条件构造段的 fallback SystemExit；**建流前按此名单预筛一次**，不要再喂给 runner 试。

**正解=两段式：** runner 一次建全部支持行（本次 17 行 9.8s 过）→ 同脚本 `query_flow(flow_id=)` 回读 `startCondition` → 追加不支持行（评分 ge 4 / 滑块 le 80 / 手机号 eq / 邮箱 like qq.com / 岗位 [postId]+[名] / 组织角色 roleCode）→ 按用户原话顺序重排 → save+deploy+回读（行 id 用独立 ts 段）。骨架见 trigger-types.md dateFieldEvent 节「两段式建流模板」。

**UI 定论：** **颜色（color）控件不支持筛选**——建了也要删（2026-09-10 用户当场要求删除，终态 23 行）。

**本次慢因复盘（2m9s，同类需求目标 ≤1min）：** ① 白名单知识缺位 → 2 次 runner 失败整跑；② 失败后违反 #73 读了 `--help` + runner 源码 ~250 行（3 轮 grep/读）才拿到清单——**该清单本应预置在 skill 里**（本轮已补入上方矩阵）；③ 探查输出拆成 2 次读取（head/tail，应一轮精简打印）。可省 ≈4-5 轮。**沉淀后同类需求路径 = 1 条 runner + 1 条追加脚本，共 2 次 py。**

**关联：** #73（runner 源码=禁止读区，本次仍犯）；#77（其末段过时结论已就地更正）；trigger-types.md dateFieldEvent 节「控件族支持矩阵」。

---

## 79. 「<应用>下新建 XX 流程」误路由到 jeecg-bpmn：应用=lowApp 是排他信号，「流程/审批」二字不构成 BPMN 依据（2026-09-10 用户纠正 + 子代理基线复现）

**现象：** 用户原话「在新疆兵团租户下**「流程应用」下**新建采购审批流程：审批人由"获取单条数据"节点查出的"审批人列表（多选人员）"字段决定，或签通过」。AI 拿「流程」二字匹配，加载 **jeecg-bpmn** 整份 SKILL.md 走 BPMN 路线；用户纠正：**「已经指明应用下了，就应该走简流」**。

**根因：** 「应用」= 敲敲云/QQY 低代码应用（lowApp），**其下流程一律是简流**；BPMN 是系统级引擎、**没有"应用"归属**。限定语「<应用>下」比业务词「流程/审批」更强。附带证据也被忽略：句中「获取单条数据」「审批人列表（多选人员）字段」都是简流术语（BPMN 无"获取单条数据"节点）。

**基线实证（子代理复现，writing-skills RED→GREEN→REFACTOR）：** 把同一句原话交给未加载任何 skill 的子代理，它**同样选了 jeecg-bpmn**，理由原话：「这是 JeecgBoot「流程应用」下的 **BPMN 审批流程**（含"获取单条数据"节点与或签审批），正是 jeecg-bpmn 的职责范围」——稳定误判，不是偶发。故修的是 skill 路由，不是"下次注意"。

**⚠️ 第二轮复现的升级版rationalization（REFACTOR 依据）：** 补了路由行后再测，子代理**仍选 bpmn**，新理由：①「流程应用」是 **BPMN 模块的系统级分类名**、不是 QQY 低代码应用；②「获取单条数据」「或签」是 **BPMN 概念、简流没有这两样**（**纯属臆造**——`data_get_one` 是简流原生节点，或签=简流 `approvalMethod=1`）。**故路由行必须显式写明这两个反驳**，光写"应用=lowApp"不够：应用名恰叫「流程应用」时，「流程」二字会强烈误导。**判据应是句中的「应用」二字本身，而非应用名叫什么。**

**耗时复盘（13 回合，同类目标 ≤2 次 py；接口实测均 3-10s，慢的不是后端）：**

| 浪费点 | 应做 |
|---|---|
| ① 先加载 bpmn 整份 SKILL.md，被用户纠正才回正轨 | 选 skill 前先 Read 凭证 memory（有各应用 lowAppId 与已建简流）——**顺序反了**是根因 |
| ② 探查脚本与创建脚本拆成 2 次 py（先打印→人看→再建） | 违反「自适应一步流」：字段 model 未知时应在**同一脚本内**解析并直接建流 |
| ③ 读 4 处文档（create-flow 全文 + approver 整节 + get_one 整节 + 2 份 example） | example 那两份 grep 命中一行即够；命中节并行读 |
| ④ 存量流程核实单开第 3 个脚本 | 应内联在建流脚本头部（0.1s） |

**正解路径：** SKILL.md 路由表首行 + 执行加速 #14「第一步固定是读凭证 memory + 状态核实」。

**附：本次建成的两条可复用契约**（node-types §一·1.2 只给了 start 节点引用的写法，**未给"引用 get_one 查询结果字段"的写法**，本次实测补齐）：

- **审批人引用 get_one 结果的字段**（`nodeType:'search'`）：`formTableId` 必须是 `form_<getOne节点id>_<表code>`（**不是** `form_start_...`），`nodeId`=getOne 节点 id、`nodeType:'search'`、`formTableType:'search'`——四个值全对才生效，写错任一 save/deploy 全绿但审批人为空。
- **get_one 查「触发记录自身」**：条件 `field:'_id'` + `valueType:2` + `val={variableValue:'_id', formNodeType:'table', formNodeId:'start', formTableCode:<表code>, variableName:'记录id'}`；落库键是 `attr.searchFieldGroup[0].queryItems`（**不在**顶层 conditions），并置 `attr.formTableId=form_<getOne节点id>_<表code>`。

**关联：** SKILL.md 路由表首行、执行加速 #14；memory `feedback_app_scope_routes_to_miniflow`；同类"先侦察再动手"失败见 #65。

---

## 80. 需求项在契约里定位不到：先验适用性 + 直接问用户，禁止反向工程落库键（2026-09-10「请假销假流程」实测，~30 轮里 ~18 轮浪费于此）

**现象：** 用户需求 7 项，其中「已经审批过该对象的审批人自动通过」在**既定契约文档、`DEFAULT_APPROVER_ATTR` 默认值常量、本租户存量扫描**三处都定位不到落库键，于是开启长链探查，全部无果。

**实际动作序列（每轮单看都"合理"，合起来是灾难）：** grep `已审批/sameMode/skipOne` → 读 **jeecg-bpmn** SKILL + `bpmn_creator.py`（被 `sameMode` 带过 skill 边界）→ 按记忆 id 查存量流（全 500）→ probe builder → probe `DEFAULT_APPROVER_ATTR` → 扫本租户 92 条流程 10 个审批节点（无一条启用过该开关）→ grep api-reference → Glob Java 源码（无）→ 扫 approverGroup 键集 → **才去问用户** → 跨租户扫（`X-Tenant-Id` 不隔离，全租户返回同一批）→ curl 前端根路径（`/jeecg-boot/` 302，非 SPA）→ GitHub API（401）→ WebSearch。

**三个根因（按严重度）：**

1. **先找实现、后验适用性（最大）——** 追到最后一轮才意识到：该流程**只有一个审批节点**，审批人**不可能"已经审批过该对象"**，此开关**恒不触发**。若第 8 轮先验适用性即可判定"不适用"并收工，直接省 ~15 轮。**适用性判断必须优先于实现打捞。**
2. **把「提问 ≤1 次」用错地方 ——** 该规则本意是「定时/通知类简单业务的常规默认值别连环问」，被泛化成"任何情况都别问"。于是明知有未知（**表里根本没有「备注」字段**、开关键未知）却憋着不问——而**用户当场就截图了**。正确答案一直在用户的设计器界面上，服务器端反向工程不可能拿到。**该问不问是最贵的沉默。**
3. **无时间盒 ——** SKILL「任何探查 2 次无果即停」被连做 8 轮无视。

**附带：别让一条线索把你拽过 skill 边界。** `sameMode` 出现在 `jeecg-bpmn` 文档 → 就去读 bpmn SKILL + 源码；而「**sameMode 是系统内部字段**（用户=1/部门=2/角色=1/职务=4，前端按组类型自动改写），**不是**同人跳过开关」这句话**就写在 miniflow 自己的 `references/example/审批节点示例.md:161`**——绕完 bpmn 才读到。违反「应用=lowApp 必走简流」（gotchas #79）。

**正解路径（约 6 轮）：** 状态核查+取字段（2）→ **【此处一次性提问：① 表里无「备注」，用哪个字段？②「已审批过自动通过」我不确定落库方式，且当前单节点结构下不适用，请确认】** → 读审批节点契约 + 建流 + 回读（3）→ 权限回读（1）。提问时 `skipApproval`/`transferStatus`/`rejectStatus`/`nodeTimeout` 契约均已到手，只差那一个待定项，故回复后可一次做完。

**本次沉淀的可复用契约（填补 node-types §一 空白）：**

- **「已经审批过该对象的审批人自动通过」的落库键 = 未知（本次未解，勿猜）。** UI 位置=审批节点配置面板「审批节点设置」区**第二项**；语义=同一审批人在**多个审批节点**重复出现时，后续节点自动通过（[官方文档](https://help.qiaoqiaoyun.com/flow/node/approve.html) 示例：经理→总监→总经理→财务，且经理=总经理）；**简流无此键**——节点契约、`DEFAULT_APPROVER_ATTR`、全租户 10 个审批节点扫描均无；设计器前端不在服务器（`/jeecg-boot/` 302）、源码不在开源 `jeecgboot-vue3`（商业版）。**⚠️ 单审批节点流程恒不触发。** 同区**第一项**「审批人为空时自动跳过」= `assigneeIsEmpty`（**已知，非未知**）。
- **审批节点「关闭驳回/转审 / 超时提醒 / 同人自动通过」四件套**（本次实测 save+deploy+回读全过）：`rejectStatus: False`（关驳回）、`transferStatus: False`（关转审）、`nodeTimeout: 48` + `timeDate: 48` + `timeType: 'timeDate'`（48h 未处理提醒，**两个字段必须同值且同时设，缺 `nodeTimeout` 不生效**）、`skipApproval: 1`（审批人=发起人时自动通过；0=默认自己审、2=转部门负责人）。配 `formEditStatus: True` 使审批时表单可编辑（**须再配字段权限才能只放开个别字段**，否则整表可编辑）。
- **字段权限 = 独立 API，不随建流走**（`processJson.privileges` 对简流无效）：`POST /act/process/extActProcessNodePermission/saveOrUpdateBatch`，每字段 **2 条**（`ruleType=1` 显示 + `ruleType=2` 编辑），`ruleCode`=**字段 model**（非 desformComKey），`status` 为**字符串**：ruleType=1 时 `"1"`显示/`"0"`隐藏，ruleType=2 时 `"0"`可编辑/`"1"`只读。回读用 `GET /act/process/extActProcessNodePermission/list?processNodeCode=<节点id>&processId=<流程id>&pageSize=100`。**"仅 X 可编辑其余只读" = 全部字段都提交两条**，X 的 ruleType=2 写 `"0"`、其余写 `"1"`（本次 7 字段 14 条，回读 14 条全过）。
- **审批人=表单人员字段**（同会议纪要）：`approverType:'candidateUsers'` + `assigneeType:'assigneeByVariable'` + `variableContent=[{formTableCode, formTableId:'form_start_<code>', nodeId:'start', nodeType:'table', fieldName:<select-user model>, fieldType:'select-user', fieldLabel:<中文名>}]` + `variableTitle:[<中文名>]` + `formTableType:'table'`。

**用户指令化要求（2026-09-10）：** 任何操作都以**最短路径、最小耗时**方式解决——先验适用性、契约未知直接问、探查 2 次即停。

**关联：** SKILL.md 执行加速 #13（本规则）、#7（时间盒）、#8（提问规则的适用范围）；memory `feedback_ask_on_unknown_contract`；同族"先侦察再动手"见 #65 / #76 / #79。

---

## 81. builder 落库：节点决策类 DSL 键全在 attr 内 —— 回读断言读节点顶层必为 None（2026-09-10 实证，同一族第 3 次复发）

**现象：** 建「请假申请审批」（`tableEvent add → 或签·指定用户 → data_update 触发记录状态`）时 save/deploy 全 success，回读按 `du.get('formTableSourceTaskId')` 断言得 `None` → 误判"更新节点没绑定触发记录"→ 多跑一轮 verify 才自证清白。**服务端 save→deploy 实测仅 1.585s；4 轮自伤（2 报错 + 1 编辑 + 1 验证）全是解析/断言自造。**

**实证落库位置（data_update）：** 节点顶层只有 `id/name/type/pid/childNode/attr/configure + 5 个渲染键`；**`formTableSourceTaskId` / `formTableId` / `formTableCode` / `formTableName` / `formTableSourceNodeType` / `level` / `updateFields` / `expressionType` / `expressionValue` 全在 `attr` 内**（`attr.formTableSourceTaskId='start'`、`attr.formTableId='form_start_<表code>'`）。approver 同族：`attr.approvalMethod` / `attr.isSequential` / `attr.completionCondition` / `attr.level` / `attr.ratio`；**`approverGroups` 例外但存两处：`attr.approverGroups`（界面面板处）+ 节点顶层同名副本，写时两处写同值——仅写一处会让另一处滞留旧值（2026-09-15 实证：顶层副本滞留在建流时默认的「发起人」）**。

**同族前车（说明这是通则、不是个案）：** `isSequential` 在 attr 内（顶层读必 None）；`approvalMode==1` 判或签。三次全是「**DSL 写法 ≠ 落库位置**」。

**根因：** 同一份契约在库里以两种形态存在——`example/主子流程配置示例.md:169` 等是**写库原始 JSON**（键在 attr 内），`create-flow.md` 组合是 **DSL 写法**（键在顶层，builder 搬运）。**同一次任务里我两条都读过，仍写错断言**；且 grep 时该证据已在眼前（`"formTableSourceTaskId": "start"` 缩进在 attr 块内）却被筛掉。

**How to apply：**
1. **回读断言只读 `attr.*`** —— 先 `print(json.dumps(node['attr'], ensure_ascii=False))` 全量打，再按键断言；判定"配置丢失"前先确认查的是落库层还是 DSL 层。
2. **并列自伤（同一脚本内）：** `fetch_form_fields` 对**无选项控件（date / integer / textarea）整个省略 `options` 键**（不是 `None`）——遍历打印必须 `.get('options')`，`v['options']` 会 KeyError 崩在第 2 个字段、整轮作废。
3. 目标 = **单轮 1 次 py 即终态**（create-flow.md 组合 J 已内联全文，勿再拼装）。

**关联：** create-flow.md 组合 J（本需求模板）；#38 / #40（落库值 ≠ UI 文案）；#58（缺 valueType/valType 的设计器表现）；#70（防呆内联脚本头部）；#54（queryById 的 processJson 是字符串）。

---

## 82. 自愈禁止整块写 `attr` / 从节点顶层读决策键 —— builder 已把决策键生成在 attr 内，覆盖即丢（2026-09-10 年度预算流程实测，两次全是自伤）

**场景：** 建「年度预算审批流程」（1008/流程应用：`tableEvent add → script 脚本节点 → exclusive 排他 → approver → data_update`）。save 成功，**deploy 报 `flowable-servicetask-missing-implementation`**；修完再回读，又发现**排他分支条件为空**。两次都不是 builder 的锅：

1. **deploy 失败根因 —— 自愈整块替换了 attr。** 我在 save 前写 `n['attr'] = {...}`（只列 updateFields/formTableId/level…），把 builder 在 `miniflow_creator.py:392-393` 生成的 `expressionType:'delegateExpression'` + `expressionValue:'${updateRecordDelegate}'` **一起覆盖没了** → 该节点在 XML 里成了无实现的 serviceTask。**正解：自愈只增补键**（`a['updateFields']=...` / `a['expressionType']=...`），**禁止 `n['attr'] = {...}` 整体赋值**。⚠️ `attr.update(node_config.get('attr',{}))`（:397）是**用户 attr 覆盖 builder 默认值**，顶层 config 里写 attr 同样能丢键。
2. **条件被清空根因 —— 从节点顶层读决策键。** 自愈里写 `cg = br.get('conditionGroup')` → None → 给条件分支写了空 `conditionGroup`。**builder 把 `conditionGroup` 放在 `attr` 内**（`miniflow_creator.py:472-478`，分支顶层无此键）→ **必须读 `br['attr']['conditionGroup']`**。#81「DSL 写法 ≠ 落库位置」同族**第 4 次复发**。
3. **builder 生成的 `queryItems` 不带行 `id`** → 该行在设计器里不可编辑/删除、整组失去「且/或」（09-09 用户实测铁律）。本次交付的流程同样中招，**事后补 `qi['id']` 才合规**——自愈时应一并补 `qi['id']=str(ts)+序号`。

**同批沉淀的契约：**

- **script 节点（脚本节点）**：节点 type=`script`，**纯 attr 承载** `{scriptFormat:'javascript', scriptContent:'多行 JS', autoStoreVariables:false, description}`，无 delegate 需求、无需 formTableList 登记；`execution.getVariable('<表单字段model>')` 可读本行字段值、`execution.setVariable('<名>',值)` 写入的变量**与表字段同名即可被下游直接引用**。跨节点引用脚本变量（分支条件/更新记录值）时：根级 `variableList` 声明变量名 + formTableList 加 `_variable_` 条目（builder 默认空数组）；分支条件写 `field=<变量名>` + `branchForm/formTableCode='_variable_'`，updateFields 的 val 写 `{variableValue,formTableCode:'_variable_',formNodeType:'variable',formNodeId:'processVariable',...}` + `valueType:3/valType:'variable'`。
- **本环境无「任务完成 / 实例查询」API**：swagger 728 路径确认（`/act/task/complete`、`/act/task/approve`、`/act/process/extActProcessInstance/*` 全 404；`/act/task/list` 忽略 `processInstanceId` 过滤参数需客户端筛）。**审批后落库（updateFields 写变量）只能 UI 验收**，禁止为此连开探测轮——本次为找该接口多花 ~6 轮。分支路由核验走 `/act/task/myApplyProcessList` 读 `currentTaskName`（★ 中文任务名最直观），不要靠 `/act/task/list` 过滤。

**耗时复盘（用户基准 ≈1 分钟）：** 建流本体 2 次 py（探查+创建）已达标，多花的轮次 = 审批人考古 ~5 轮 + 上述自伤 1 轮 + 找完成接口 ~6 轮。**审批人点名实体在租户里不存在时**（如「财务总监」只有「财务主管」），一次性并发拉 positions+roles+users+角色成员，再连同其他未知项**一次 AskUserQuestion 问透**，禁止串行求证。

**关联：** #81（本族第 3 次）；#80（适用性优先于实现打捞）；#73（耗时红线）；SKILL.md 执行加速 #15。

---

## 83. 流程参数必须有中文显示名，且与脚本变量名保持一致（2026-09-10 用户实测，用户定论口径）

**现象：** 脚本节点 `setVariable('totalSubsidy', …)` + 根 `variableList` 只写 `field` 不写 `columnName` 时，save/deploy/回读全绿，但设计器「更新记录 → 设为 → 本流程参数」列表显示 `[数字] totalSubsidy`，用户核对时问「流程参数中没有呢？」（以为参数根本没生成）。**参数其实在，且绑定正确**——UI 只是显示英文标识。

**根因：** 设计器「本流程参数」列表**优先显示 `columnName`，缺省才退回显示 `field`**。`variableList[].field` 是变量标识（脚本 `setVariable` 的 key），`columnName` 才是 UI 标签。只写 field = UI 全程暴露英文标识。

**修法（用户定论：变量名与显示名保持一致，避免使用者误判）：** 变量名直接用中文，`field` 与 `columnName` 同值 —— 脚本、variableList、取值 val、分支条件**四处同名**，UI 与脚本从头到尾一个词：

```python
"variableList": [{"id": "<雪花id>", "type": "number", "options": {"format": "yyyy-MM-dd"},
                  "field": "总补贴金额", "columnName": "总补贴金额"}]
# 脚本:            execution.setVariable('总补贴金额', 总补贴金额)
# data_update 取值: val={'formNodeType': 'variable', 'formNodeId': 'processVariable',
#                        'formTableCode': '_variable_', 'variableValue': '总补贴金额', 'variableName': '总补贴金额'}
# 排他分支条件:     field='总补贴金额', columnName='总补贴金额', type/valType='number', val=5000
```

Groovy 支持中文标识符（局部变量、`setVariable` 名均可用中文），本环境已实测 save/deploy/回读全绿。

**⚠️ 改名/改脚本必须两处同步：** 脚本节点除 `attr.scriptContent` 外还有**节点顶层 `content`**（卡片显示文本）——只改前者时设计器卡片仍显示旧变量名。改名前先 `json.dumps(processJson)` 全量搜旧名，改后断言无残留（本次实测正是靠该断言发现第二处）。

**关联：** #58（val 对象三键同族，同为「存储正确但 UI 显示错」）；#82（同批并行建流实测）；node-types「十一」「二十四-B」；create-flow.md「组合 J 变体」。
---

## 84. data_update「选择更新对象」写成**前置节点 id** —— save/deploy/回读全绿，但设计器里更新对象错、回填不落库（2026-09-11 仁和医院 8 条简流实测，用户 UI 验收才发现）

**现象：** 8 条 tableEvent 简流（`start → 审批/脚本节点 → data_update 回填本行`）建完 save+deploy 全 success、`extActProcess/list` 8 条齐全、行数复核也过。用户在 UI 打开流程，**「选择更新对象」下拉里选中的是审批/脚本节点**（不是「工作表事件触发」）→ 回填不生效。用户手工修好 1 条、我拿它和其余 7 条对 JSON 才定位：**12 个回填节点全部中招**。

**落库差异（同一字段，两种值）：**

| | `formTableSourceTaskId` | `formTableId` |
|---|---|---|
| ✅ 正确（更新触发记录） | `'start'` | `'form_start_<表code>'` |
| ❌ 错误（本次生成） | `'task1789119920958001'`（**前一节点 id**） | `'form_task1789119920958001_<表code>'` |

**为什么断言漏掉：** 错误形态**自身是自洽的**（`form_<nodeId>_<code>` 恰与 `formTableSourceTaskId=<nodeId>` 配对），所以「formTableId 是否 == form_ + formTableSourceTaskId + _ + code」这类一致性断言**恒真、查不出来**。#81 讲的是「决策键在 `attr` 内」，**没讲值该指向谁**——本条补的正是这个值。

**判据（更新目标决定取值；两种都合法，禁止互套）：**
- 更新**触发记录本身**（tableEvent 场景的绝大多数回填）→ `'start'` + `form_start_<表code>`
- 更新 **getMore / get_one 取到的记录** → `<取数节点id>` + `form_<该节点id>_<表code>`（create-flow.md §E2、组合 F 已载）

**How to apply：**
1. 造回填节点时 `formTableSourceTaskId` / `formTableId` **显式写死 `'start'` / `'form_start_' + code`**，禁止拿「上一节点 id」推导（builder 不会替你纠正，且它默认就是前一节点）。
2. **回读断言必查，save/deploy 绿不算数**：逐条 `queryById` → 遍历全部 `type=='data_update'` → 断言 `attr.formTableId == 'form_start_' + attr.formTableCode`（仅限"更新触发记录"场景）。
3. **改已有流程**：`save_flow(api, token, cfg, pj, flow_id=<id>, update_count=<uc>)` —— **不会**新建重复条（实测改完 7 条后应用内流程数仍为 8）；`cfg` 由 `extActProcess/queryById` 行字段重建（`startTaskId='task'+processKey去掉 process 前缀+'000'`、`titleField` 取 `fetch_app_forms`）。
4. 这是同族**第三次**「save/deploy 全绿 ≠ 配置正确」（#81 断言读错层、create-flow §E2 填自身 id）⇒ **简流验收必须落到 JSON 值级断言**。

**关联：** #81（同族：决策键在 attr 内）；create-flow.md §E2 / 组合 F（getMore 的正确形态）；#54（queryById 的 processJson 是字符串）。

---

## 85. 定时触发流程不得登记 start 空表条目 —— 否则变量选择器出现「定时触发 工作表:""」（2026-09-14 用户 UI 验收纠正；builder 已修）

**现象：** 定时触发流程（timerEvent / dateFieldEvent）建好后，设计器打开任一节点，「变量选择器」多出一项 **「定时触发　工作表:""」**——可被当作参数来源选中，但点开**没有任何字段**。用户定论口径：**定时触发本就没有工作表和参数，不应作为参数源出现**。

**根因：** `miniflow_creator.build_process_json` 的 formTableList 组装，在 `start_type ∉ {userEvent, subEvent}` 的 `else` 分支**无条件**登记一条 start 条目；定时/按日期/手动等触发没有工作表 → `formTableCode/Name` 落成**空串**，形成空表条目：

```json
{ "formTableId": "form_start_", "nodeId": "start", "nodeName": "定时触发",
  "nodeType": "table", "formTableCode": "", "formTableName": "", "formTableMainCode": "", "selectType": 1, "level": 0 }
```

设计器的来源分组是**按 formTableList 逐条渲染**（`nodeName`→分组标题、`formTableName`→「工作表:xx」）——对照同列表里 `流程参数` 条目（formTableName="流程参数"）显示正常。⚠️ root 级与 start 节点内的 `formTableList` 是**同一个 list 对象**，修 root 即修两处。

**How to apply：**
1. **builder 已修（2026-09-14）**：start 条目仅当 `formTableCode` 非空才登记。回归方式（本地、不打接口）：`build_process_json` 分别跑 timerEvent / tableEvent 配置，断言前者 `formTableList` 无 `nodeId=='start'` 条目、后者保留且表单码正确、两者 `processVariable` 条目都在。
2. **存量流程清理**（旧定时流程仍带该条目）：`query_flow` 拉最新 pj → 从 `pj['formTableList']` 删除 `nodeId=='start'`（或 `formTableId=='form_start_'`）条目 → `save_flow` + `deploy_flow` → 回读断言 root 与 start 节点内均无。实测一轮通过（`流程修改成功` / `发布成功!`），主链与工作表引用未动。
3. **只删 formTableList 条目**：勿动 start 节点 attr 的 `formTableId:'form_start_'` 与流程级 attr——那是定时节点自身配置，删条目后 UI 即正常（用户验收确认）。
4. 定位线索：凡 UI 来源选择器出现「**工作表:""**」的空分组，先查 `formTableList` 是否残留无表/空表的 start 条目（`nodeType:'table'` + 空 `formTableCode`）。

**关联：** #84（同族：save/deploy 全绿 ≠ UI 正确，须 UI 验收才发现）；#39（渲染键）；create-flow.md「补 formTableList」段。


---

## 84. 往链上插运算/取数节点后，分支条件的「选择结果值」列不全 —— 节点 level 必须小于网关/分支 level（2026-09-11 用户截图 + UI 原生流程对照实证）

**现象：** 分支条件里要选「运算结果」当比较值，点开来源树（选择结果值）**只列出部分运算节点**（常见是只列出链上第一个，例如只有 `数值运算`，`函数计算`/`统计条数`(fun/record) 根本没出现），用户会问「为什么没有 XX 和 YY 的结果」。但流程 save/deploy/回读全绿，落库的 `val` 引用对象、`formNodeTable`/`formTableList` 登记、`branchForm` 全都正确——**不是存储问题，是设计器按 level 过滤了来源树**。

**根因：** 来源树**按节点 `level` 判断「该来源是否排在此分支之前」**，只列出 level 不大于当前分支的来源（实测分支 level=1 时，level=0 的工作表与 level=1 的运算节点列出，level=2/4 的两个运算节点不列）。用 API 往已有流程的网关前插节点时，若把新节点 level 顺次写成 `1/2/3/4`，而**网关与 conditionNodes 的 level 仍是原值 `1`**，后续节点就"排到分支后面去了"。

**正确 level 约定（与设计器原生一致，对照 UI 原生流程实测）：**

| 位置 | level | 说明 |
|------|-------|------|
| 上游链（插入的运算/取数节点） | `"0.1"` / `"0.2"` / `"0.3"` … 严格递增且 **< 1** | 原生流程上游实测小数值（0.333/0.834/0.855/0.875） |
| 网关 `attr.level` 与各 `conditionNode.attr.level` | 两者**同值**（如 `"1"`） | 原生流程实测网关 0.959 / 分支 0.959 |
| 分支内子节点（审批等） | 比分支大（如 `"2"`） | 原生流程实测 1.000（网关 0.959） |
| `formTableList` 条目 `level` | **逐条与对应节点 level 同值**（字符串） | 原生样本两者一致；start 条目是 int `0` |

**修法：** 改 level 即可，**条件本身（queryItems/branchForm）不用动** —— 重排后 save + deploy（本次实测 updateCount+2、2s 内完成），让用户**刷新设计器页面**（旧标签页缓存 processJson，刷新前仍显示旧的来源树）。

**自查（插完节点立刻做）：** 按链序打印 `节点名 level`，断言「上游链 level < 网关/分支 level < 分支内子节点 level」，并核 `formTableList` 条目 level 与节点一致；不满足就重排后再 save。⚠️ level 相同（上游==分支）时本次实测仍能列出（等值通过），但**不要依赖等值**——原生流程全是严格小于，按严格小于构造。

**顺带结论：** 分支条件的比较值来源里，`fun`/`record` 型运算节点**都是可选的**（原生流程存在「字段源=function-fun + 比较值=function-record」的分支条件），「只有 number 能选」是 level 造成的假象，不要据此改写成别的形态。

**关联：** #59（分支直接引用运算结果：`field="result"` + branchForm=function-{funType}）；#58（function 登记须按链序）；node-types「十八」18.1~18.3、「四」4.4.1；SKILL.md「追加修改要点」。

## 85. 分支条件规则必须落在该控件的「规则下拉白名单」内：写不支持的 rule，save/deploy/回读全绿、设计器下拉里根本没有该项（2026-09-11 用户 UI 逐族实测）

**场景：** 「表单内每个组件一条分支」类需求，整表统一铺同一种规则（本例先统一「等于」，再依次整表改 不等于 / 大于 / 大于等于 / 小于 / 在范围内）。前几步用户没说什么，铺到**在范围内**时暴露：文本组件（`input`）的规则下拉里**没有「在范围内」**——下拉列表只有 等于 / 不等于 / 全模糊 / 左模糊 / 右模糊 / 为空 / 不为空。用户原话：「没有范围查询的字段不需要设置为范围」。

**实测白名单（逐族打开设计器确认）：**

| 控件族 | 规则下拉可选 |
|--------|-------------|
| 文本 `input` / `textarea` | 等于、不等于、全模糊、左模糊、右模糊、为空、不为空（**无** 大于/小于/在范围内） |
| 公式 `formula` | **无「在范围内」**（用户实测；等于可用） |
| 文件 `file-upload` | **仅 为空 / 不为空** |
| 日期 `date` / 时间 `time`（时间选择器**有** 在范围内）/ 数值 `number`·`integer`·`money`·`rate`·`slider` | 比较类 + **在范围内** |

**⚠️ 真正的坑：服务端不校验 rule 与控件族的匹配。** 写 `range` 到文本字段上照样 `save_flow` 成功、`deploy_flow` 成功、`query_flow` 回读 `rule/ruleName/beginVal/endVal` 一字不差——**「回读通过」在这类正确性上完全无效**，只有人打开设计器才看得到（下拉框里没有该项、值框渲染异常）。所以批量铺规则前就按族分流，别指望回读兜底。

**正确做法：** 建/改批量分支时**按控件族分流铺规则**——日期/时间/数值才写 `range`（`beginVal`/`endVal`，日期两端毫秒时间戳 int、时间 `"HH:mm:ss"` 字符串）；文本/公式写 `eq`（或模糊类）；文件类写 `empty`/`not_empty`（`val=[]`+`name=[]`+`valType=""`）。改完仍按高危回读（结构/值形态），但**族匹配与否要靠人看设计器**，脚本不能自证。

**顺带（同一轮暴露的渲染表现）：** 分支卡片**正文**那行 `[字段 规则 值]` 是设计器前端按 `conditionGroup` 的**原始值**现拼的，**不读节点 `content`**——日期类必然显示毫秒（如 `[年 在范围内 1767196800000...]`），而卡片**标题**读的是 `name`（可读文案，如「年在范围内2026-01-01-2026-12-31」）。落库 `content` 即使写成可读文案也不会被正文采用。**属渲染表现、改 JSON 无效**，别为用户提的这个观感返工改条件值（改条件值会动语义）。

**关联：** node-types「二十 · 规则下拉白名单按控件族给」、node-types「六」（包含分支，含指针）；#52/#77（日期毫秒、时间字符串）；#50（触发筛选的 `range` 独立规则）；SKILL.md 路由表分支类需求段。

---

## 86. 他表字段（link-field）只有「存储数据」模式可作流程条件，`saveType:"view"`（仅显示）不可作条件（2026-09-11 用户定论）

**规则：** link-field 控件的 `options.saveType` 决定它能否当条件字段——**仅「存储数据」模式可作条件；「仅显示」模式（`saveType:"view"`）不可用作条件**（查询条件、分支条件同理）。

**判定：** `GET /desform/api/fields/<code>?group=true` 看该控件 `options.saveType`（`"view"` = 仅显示）。

**坑的形状与 #85 同源：** 服务端不校验——给 view 模式的他表字段写条件，`save_flow`/`deploy_flow`/回读**全绿**，只有人打开设计器才看得出不对，引擎运行时也不匹配。所以「批量给所有控件铺条件/分支」时，**先按 `saveType` 把他表字段剔掉**，别事后靠回读兜底。

⚠️ **别拿环境里的样本当反例/先例**：本机（萌萌科技租户）现存 link-field 样本**全部是 `saveType:"view"`**（固定资产管理各明细表、萌销售全控件表单的「客户名称」），未见存储模式样本——"环境里都这样写"不能证明可用。

**要按他表字段的语义检索时：** 改用它的**来源关联记录字段（link-record）**作条件——link-record 存的是目标记录 id（`eq` 单值 / `in` 用 id 数组），那才是可用条件字段；联动显示的 link-field 只是它的只读副本（值=源记录 `showField` 字段值，见 #40）。

**关联：** #85（规则族白名单，同属"服务端不校验、只有人看设计器才发现"族）、#40（link-record / link-field 存储值差异）、node-types「二十」。

## 87. 按流程名改/删前必须先按应用过滤：`query_flow(process_name=…)` 会命中别的应用（2026-09-15 实测）

**`query_flow(process_name=...)` 不按应用过滤** —— 全租户按名匹配、只返回最新一条。多应用有同名流程时（实测同一租户两个应用各有一条「修改计划状态」），会拿到**别的应用**那条，改/删跟着错过去（我就这么误删了一条别的应用的流程）。附带：`DELETE .../extActProcess/delete` 的响应体会返回**被删流程的完整 processJson**，删错时旧应用整份定义直接打进日志。

**改/删流程前先限定应用再取 id：** `GET /act/process/extActProcess/list` + `X-Low-App-ID` 头（0.1s，分页 dict，见 #74）→ 按 `processName` 核对 id 在本应用存在 → 再 `query_flow(flow_id=...)`。查不到就是应用不对，不要退回全租户查。

---

## 88. `/act/process/close/{processKey}` 会**永久拆掉「新增触发」注册** —— open / 重新 deploy / 改配置全都恢复不了，只能**删流程记录重建**（2026-09-16 考勤管理(标准版) 实测，用户连说三轮「还是不行」）

**现象：** 「考勤确认」流程（`startType=tableEvent` + `startEventType=add`，工作表 `kqqr0916`）在某次 `close` 之后**再也不触发**。排查过程全部为「正常」：
- `/act/process/extActProcess/list`：`openStatus=1`、`processStatus=1`、`relationCode=desform_kqqr0916_<流程id>` 齐全
- `deploy_flow` 反复 `success`，`processDeployTime` 一直在更新
- `processJson` 与**同表上另一条能正常触发的流程逐键一致**（root、attr、节点顶层、approverGroups[0]、privileges 全对上）
- 表的 `desform` 记录里没有任何 flow 绑定字段
- 同一份配置在别的表（`bk0916`）上**触发正常**

**根因：** 调过 `GET /act/process/close/{processKey}`（挂起）后，该流程的**工作表事件触发注册被拆掉**，后续 `GET /act/process/open/{processKey}`、重新 `save_flow`、重新 `deploy_flow` 都**不会重建**这个注册 —— 表象上流程「已启用」，实际引擎里没有它的触发条目。

**How to apply：**
1. **别用 `close` 做「临时停用再启用」**。要短期停用就用设计器里的开关；已经 `close` 过又发现不触发 → **直接重建**。
2. 重建步骤（实测有效）：`query_flow` 备份 `processJson` → 备份该流程各 edit 节点的字段权限行（`extActProcessNodePermission/list`）→ `DELETE /act/process/extActProcess/delete?id=<流程id>` → `save_flow(cfg, pj)`（**新 `processKey`/`startTaskId`**）→ `deploy_flow` → 把权限行**去掉 `id`** 后带新 `processId` 重灌。
3. 重建后**必须实测**：`POST /desform/data/add` 灌一条 → `/act/task/myApplyProcessList` 看实例是否出现且 `currentTaskName` 落在预期节点。
4. **权限行重灌的坑：** `saveOrUpdateBatch` 对同 `(processNodeCode, processId, ruleCode, ruleType)` 会报「规则编码已存在，不允许重复添加」——**必须带原 `id` 回提交**；行体只认 `{processId, processNodeCode, ruleCode, ruleName, ruleType(字符串"1"/"2"), status(字符串), desformComKey, formBizCode, formType:"2", required, delFlag}`，多带 `writable/enabled/displayable` 会「批量保存失败」且**不给原因**。请求头要带 `Content-Type: application/json`，否则报 `Content-Type 'application/octet-stream' is not supported`。

**同批学到的两条（都别再走弯路）：**
- **「办理人列空」不能当判据**：`/act/task/list` 的 `taskAssigneeId` 对 `assigneeByVariable`（办理人取自表单人员字段）**不回填** —— 用户自己用设计器建、能正常办理的流程同样是 `''`/`None`；写死用户（`approverIds:["admin"]`）才回填。判「解析成功」看任务是否出现在该用户待办里。
- **一张工作表挂两条「新增触发」流程会冲突**，实测只有一条生效（用户为此主动停用了其中一条）。

**关联：** #84/#85 同族（save/deploy/回读全绿 ≠ 运行时正确）；api-reference.md「挂起 / 激活流程」条需补此警告。

> **补记（`attr.approverGroups` 到底要不要写）：** 用户用设计器现建的流程，`attr` 里**没有** `approverGroups`，「指定填写对象」的 chip 照样正常渲染 —— 说明设计器**读顶层 `approverGroups` 为主、`attr` 那份是给面板做副本**。`create-flow.md` 里「两处都写同值」的 2026-09-15 结论是**针对「改已有流程」**（只改一处会让另一处滞留旧值），不是「新建时必须两处都写」。`build_edit_node` 目前两处都写（无害，保留）；**别因为它比设计器产物多一个键就去「对齐」删除** —— 2026-09-16 我正是拿「设计器产物」当基准批量删/加，来回改了两遍，与真因（close 拆注册）完全无关。

---

## 89. 分支判「流程中途才填的字段」时，`branchForm.formNodeId` 必须指向产出该值的节点；填 `start` 永远取到空（2026-09-16 实测）

**现象：** 互斥分支「简历是否合格 等于 合格」，用户在审批节点选了「合格」并提交，分支却判失败、走了默认分支。后台日志：

```
【条件评估】字段:<select_xxx> | 操作符:<等于> | 实际值:<> | 期望值:<合格> | 结果:<✗失败>
```

**排查（值本身没问题）：** 直接查数据表，该记录的字段值**就是**「合格」——数据存对了，是**分支取值取错了地方**。

**根因：** `branchForm.formNodeId="start"` 表示「从**触发那一刻的起始行快照**取值」。该字段在新增页隐藏、要到审批节点才填，**触发时为空**；审批节点提交虽然更新了记录，但**不会刷新起始行快照**，网关评估时拿到的仍是空。

**规律（翻生产流程实证）：** `branchForm` 指向**把该值产出来的节点**，不是固定 start——
| 被判字段的来源 | formNodeId / formNodeType |
|---|---|
| 新增时就有（如 采购单价） | `start` / `table` |
| get_one 检索结果 | 该 data_get_one 节点 / `search` |
| 运算节点结果 | 该 function 节点 / `function` |
| edit/approver 中途填的 | 该填写节点 id / **`table`**（✅ 2026-09-16 实测通过） |

**How to apply：**
1. 建分支前先问：**被判的字段是「触发时就有」还是「流程中途才填」**。中途才填的一律**不能**填 `start`。
2. 指向填写该字段的 edit/approver 节点 id，`formTableCode` 填该表 code。
3. 症状识别：save/deploy 全绿、设计器里条件显示完全正常，**只有真跑一遍**才在后台日志看到「实际值:<>」——与 #84/#85 同族（全绿 ≠ 运行时正确）。
4. 兜底：在产出节点后加 `upvariable` 把值写进**流程参数**，分支改判流程参数（`branchForm` 填 `_variable_`）。
5. **怎么验（不用问人）**：**必须用新记录验**——改动前建的记录流程已经跑完，看不出分支走了哪条。判据是**流程实例停在哪个节点**：查 `currentTaskName` 是否落在预期下游节点。
   ⚠️ **别拿记录 `bpm_status` 当通用判据**：它只表示流程结没结束（3=已结束 / 2=进行中），**推不出分支对错**。只有当「走错的分支会立刻结束、走对的分支会停下等人」时，才能拿它间接推断（本案例恰是这个形状：错分支发完消息即结束→3，对分支停在「安排面试」→2）；换条流程两条分支可能都是 3，照搬会误判。

**关联：** #84/#85（同族）；miniflow-node-types.md 四节 branchForm 条（已同步）。

---

## 90. 审批组四种形态**写错都是静默无任务**：指定成员带 `user.` 前缀 / 表单部门字段漏 `isNeedTranslateToUserIds` / 单复数混用（2026-09-16 用户报障实测）

**现象（用户原话）：**「面试流程中的需求部门填写人员设置的招聘部门，部门下人员没有收到任务」。
后台表现**全绿**：流程已发布且已启用、新增记录照常起实例、`/act/task/list` 里任务也在 —— **只有 `/act/task/myTodo` 能看出没人收到**。

**根因：同轮踩到两处，都是 `approverGroups` 落库形态写错**（save/deploy 全是 success，零报错）：

| 办理人来源 | 正确形态 | 错法 → 后果 |
|---|---|---|
| 指定成员 | `candidateUser`（**单数**）+ `assigneeByName` + `approverIds: ['admin']`（**裸账号**） | 写成 `['user.admin']`（那是**消息节点** `toUserIds` 的写法）→ 谁都收不到 |
| 表单·部门字段 | `candidateUsers`（**复数**）+ `assigneeByVariable` + `variableContent[].isNeedTranslateToUserIds: true` | 漏 translate 键 → 部门**不展开成用户** → 部门成员全收不到 |
| 表单·用户字段 | `candidateUsers`（复数）+ `assigneeByVariable`（**不带** translate 键） | 单数无生产样本；带 translate 非本形态 |
| 发起人 | `candidateUser`（单数）+ `assigneeByExp` | — |

**判据（唯一）：** `/act/task/myTodo` 里任务是否出现在**该办理人**的待办。
- ❌ `/act/task/list` 的 `taskAssigneeId` 对表单字段/部门类**不回填**，不能拿它判「解析成功」（#88 同批两条之一）。
- ✅ **最稳 = 正反例对照**：一条记录部门选「该用户所属部门」、另一条选「该用户不在的部门」→ 应出现 / 应不出现。一次排除「兜底给发起人/管理员」的假阳性（本环境无「任务完成」API，只能验到这一步，别为此开探测轮）。

**How to apply：**
1. 建流时按上表逐组核对；`build_flows.py` 的 Builder 曾写 `"user.%s"`、`"user.admin"`（2026-09-16 已修为裸账号），批量建流前确认这两处。
2. 收尾**必做运行时验收**，别把 save/deploy 成功当交付：

```python
# ① POST /desform/data/add 造一条记录（字段 key 用 model）→ ② sleep 3~6s（流程异步起）
# ③ GET /act/task/myTodo?pageSize=50 → 断言目标任务出现在该办理人待办里
# ④ 反例：换一个该办理人不在的部门重复 ①~③ → 断言不出现
```

3. 单复数别混：指定成员 / 发起人 = 单数 `candidateUser`，表单字段类 = 复数 `candidateUsers`。

**关联：** #88（重建后必实测、办理人列空不能当判据）、#87（按名改删先按应用过滤）；`example/审批节点示例.md` §一.4、`miniflow-node-types.md` 一节、`create-flow.md` 组合 F ⑤、`fast-full-chain.md` ④ 已同步；`build_flows.py` / `flow_dsl.py` 两处代码已修。
