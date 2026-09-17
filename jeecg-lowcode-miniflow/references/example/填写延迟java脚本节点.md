# 简流设计器填写/延迟/脚本/服务节点示例

> **文档结构说明（双结构）：**
> - **一、精简示例（AI 速读版）** — 使用 `miniflow_creator.py` 的 config 简化格式，带中文注释，AI 直接照抄即可运行
> - **二、完整 JSON 附录（来自生产数据）** — 真实 processJson 全量结构，供排障、精确复刻、人工核对
>
> 日常创建流程读第一部分；遇到前端渲染异常或需要核对细节时读第二部分。

---

## 一、精简示例（AI 速读版）

本文档覆盖四种节点：填写节点（edit）、延迟节点（time）、脚本节点（script）、服务节点（service）。

### 1. 填写节点（edit → 真实类型 edit）

**① 触发后指定人填写，带字段权限：**

```python
{
    "type": "edit",
    "name": "触发表单填写",
    "approverGroups": [                       # 不写 approverGroups 时默认=发起人
        {
            "approverType": "candidateUser",
            "assigneeType": "assigneeByName",
            "approverIds": ["admin"],         # 指定填写人
            "approverNames": ["admin"],
        }
    ],
    "privileges": [                           # 字段权限：逐字段控制可写/必填/可见
        {
            "ruleName": "客户编码",                        # 字段显示名
            "ruleCode": "input_1776136714724_557407",      # 字段 model
            "processNodeCode": "task968405252451770368",   # ⚠️ 必须等于本节点 ID，写错权限不生效
            "formBizCode": "cw_customer_profile",          # 表单编码
            "desformComKey": "1776136714724_650203",       # 设计器组件 key
            "writable": True,        # 可写
            "required": True,        # 必填
            "enabled": True,         # 启用（false=整行置灰不可填）
            "displayable": True,     # 显示（false=隐藏）
            "original": False,
            "del": False,
        },
        # 其余字段条目结构相同；不需要控制的字段直接省略
    ],
}
```

**② 获取单条数据后填写查询到的记录（search 绑定）：**

```python
# 前置：get_one 节点（⚠️ 自定义 ID，edit 节点要引用）
{
    "type": "get_one",
    "id": "task968405436317474816",          # 时间戳格式 task{ts}001，禁止 UUID
    "name": "获取单条数据",
    "getType": 1,
    "formTableCode": "cw_account_subject",
    "formTableName": "会计科目表",
    "emptyAction": 1,
},
# 后续：填写查询结果
{
    "type": "edit",
    "name": "获取数据填写",
    "approverGroups": [
        {"approverType": "candidateUser", "assigneeType": "assigneeByExp",
         "expressionsIds": ["${applyUserId}"], "expressionsNames": ["获取发起人"]}
    ],
    # ⚠️ edit 默认绑定触发表（table），改绑查询结果必须用 attr 显式覆盖
    "attr": {
        "formTableSourceTaskId": "task968405436317474816",   # get_one 节点 ID
        "formTableSourceNodeType": "search",                 # search=填写查询结果
        "formTableId": "form_task968405436317474816_cw_account_subject",  # 格式 form_{节点ID}_{表code}
        "formTableCode": "cw_account_subject",
        "formTableName": "会计科目表",
        "nodeTimeout": 2,                   # 填写超时（生产数据值）
    },
    "privileges": [
        # 结构同 ①，processNodeCode 改为本节点 ID
    ],
}
```

### 2. 延迟节点（time → 真实类型 timer_event）

```python
# ① 延迟指定时长（timeType=timeDuration）
#    ⚠️ timeCycle 是「执行时间」单选组的**模式 token**，只认 4 个预设 + "custom"：
#       PT1M=1分钟后 / P1H=1小时后 / P1D=1天后 / P1M=一个月后
{ "type": "time", "name": "延迟1小时", "attr": {"timeCycle": "P1H", "timeDate": None} },

# ② 预设外的时长（30分钟/1周/2小时30分…）→ 必须 custom + 时长串放 timeDate
{ "type": "time", "name": "延时30分钟",
  "attr": {"timeType": "timeDuration", "timeCycle": "custom", "timeDate": "PT30M"} },
{ "type": "time", "name": "延时1周",
  "attr": {"timeType": "timeDuration", "timeCycle": "custom", "timeDate": "P7D"} },

# ③ 到指定时间点继续（timeType=timeDate）
{
    "type": "time",
    "name": "指定时间",
    "attr": {
        "timeType": "timeDate",               # timeDate=指定时刻
        "timeDate": "2026-04-14T19:00:00",
    },
},
```

多个 time 节点可串联。节点 ID 前缀为 `TimerEventDefinition_`（脚本自动生成，与 task 前缀区分）。

### 3. 脚本节点（script）与服务节点（service）

```python
{
    "type": "script",
    "name": "脚本节点",
    "attr": {
        "scriptFormat": "javascript",         # 或 "groovy"
        "scriptContent": "var sum = 2 + 9;\nexecution.setVariable(\"myVar\", sum);",
        # 多行脚本用 \n 分隔；execution.setVariable 设置流程变量供后续节点引用
    },
},
{
    "type": "service",
    "name": "服务节点",
    "attr": {
        "expressionType": "class",            # class=Java 类全路径；delegateExpression=Spring 委托表达式
        "expressionValue": "org.jeecg.modules.testListenerExpression.TestService",
        # 可选："resultVariable": "输出变量名", "description": "描述"
    },
},
```

### 4. 生产数据提炼的关键知识点

1. **privileges 的 processNodeCode 必须等于所在节点 ID**——字段权限按节点绑定，复制节点时忘改 processNodeCode 会导致权限不生效（真实踩坑点）。
2. **edit 节点默认绑定触发表**：formTableId=form_start_xxx、formTableSourceNodeType=table；填写查询结果时必须通过 attr 覆盖三件套（formTableSourceTaskId=get_one 节点 ID、formTableSourceNodeType=search、formTableId=form_{节点ID}_{表code}）。
3. **get_one 要用自定义 ID** 才能被后续 edit / data_update 引用；ID 必须是时间戳格式（task{ts}001），禁止 UUID，否则 mxGraph 渲染失败。
4. **time 节点 timeType 枚举**：timeDate=指定时刻（配 timeDate ISO 字符串）、timeDuration=延迟时长。**⚠️ `attr.timeCycle` 是模式选择器不是时长值**——只认 `PT1M`/`P1H`/`P1D`/`P1M`（四个 UI 预设）与 `"custom"`；预设外的时长一律 `timeCycle="custom"` + 时长串写 `attr.timeDate`（如 `PT30M`/`P7D`）。直接把 ISO 串写进 timeCycle 会 save/deploy 全绿但设计器「执行时间」整排未选中（2026-09-10 用户实测）。生产数据第三个延时节点顶层有冗余的 `"timeDate": ""` 空串字段，真实生效的是 attr.timeDate。
5. **脚本/服务节点 content 为 "已设置"**（生产数据固定值）；scriptContent 在 JSON 中换行是字面 `\n`、双引号需转义 `\"`；生产数据中 script 节点带 `privileges: []` 与 `description: null` 冗余字段。

---

## 二、完整 JSON 附录（来自生产数据）

> 以下为真实流程保存后的完整 processJson，供精确复刻与排障参考。日常使用以上方精简示例即可。

### 填写节点示例（完整 processJson）

```json
{
    "id": "start",
    "startTaskId": "task968405157874409472",
    "name": "工作表事件触发",
    "type": "start",
    "createStartNode": false,
    "initiator": "applyUserId",
    "status": -1,
    "error": false,
    "startNodeContent": null,
    "childNode": {
        "id": "task968405252451770368",
        "name": "触发表单填写",
        "type": "edit",
        "status": -1,
        "attr": {
            "approvalEnabled": false,
            "approvalMethod": 1,
            "sameMode": 1,
            "assigneeIsEmpty": 0,
            "skipApproval": 0,
            "ratio": 0.5,
            "loopCardinality": null,
            "isSequential": false,
            "collection": "${flowUtil.stringToList(assigneeUserIdList)}",
            "elementVariable": "assigneeUserId",
            "completionCondition": null,
            "timeDate": null,
            "timeType": "timeDate",
            "allowAddSign": false,
            "allowCountersignAddUser": false,
            "formEditStatus": false,
            "transferStatus": true,
            "rejectStatus": true,
            "ccStatus": true,
            "msgStatus": false,
            "selnextUserStatus": true,
            "formTableId": "form_start_cw_customer_profile",
            "level": "1",
            "formTableName": "客户档案",
            "formTableCode": "cw_customer_profile",
            "formTableSourceNodeType": "table",
            "formTableSourceTaskId": "start"
        },
        "taskListenerData": [],
        "listenerData": [],
        "approverGroups": [
            {
                "id": "group968405252451770369",
                "approverType": "candidateUser",
                "assigneeType": "assigneeByName",
                "levelMode": 1,
                "approverIds": [
                    "admin"
                ],
                "approverId": "",
                "approverNames": [
                    "admin"
                ],
                "approverName": "",
                "deptIds": [],
                "deptNames": [],
                "postIds": [],
                "postNames": [],
                "roleIds": [],
                "roleNames": [],
                "expressionsIds": [],
                "expressionsNames": []
            }
        ],
        "approverType": "candidateGroups",
        "assigneeType": "assigneeByName",
        "approvalMode": 1,
        "privileges": [
            {
                "ruleName": "客户编码",
                "ruleCode": "input_1776136714724_557407",
                "processId": "",
                "processNodeCode": "task968405252451770368",
                "formBizCode": "cw_customer_profile",
                "desformComKey": "1776136714724_650203",
                "writable": true,
                "required": true,
                "original": false,
                "del": false,
                "enabled": true,
                "displayable": true
            },
            {
                "ruleName": "客户名称",
                "ruleCode": "input_1776136714732_375811",
                "processId": "",
                "processNodeCode": "task968405252451770368",
                "formBizCode": "cw_customer_profile",
                "desformComKey": "1776136714732_256777",
                "writable": true,
                "required": false,
                "original": false,
                "del": false,
                "enabled": true,
                "displayable": true
            },
            {
                "ruleName": "客户类型",
                "ruleCode": "select_1776136714739_705427",
                "processId": "",
                "processNodeCode": "task968405252451770368",
                "formBizCode": "cw_customer_profile",
                "desformComKey": "1776136714739_967439",
                "writable": false,
                "required": false,
                "original": false,
                "del": false,
                "enabled": true,
                "displayable": true
            },
            {
                "ruleName": "联系人",
                "ruleCode": "input_1776136714746_969452",
                "processId": "",
                "processNodeCode": "task968405252451770368",
                "formBizCode": "cw_customer_profile",
                "desformComKey": "1776136714746_160399",
                "writable": false,
                "required": false,
                "original": false,
                "del": false,
                "enabled": true,
                "displayable": false
            },
            {
                "ruleName": "联系电话",
                "ruleCode": "input_1776136714752_331927",
                "processId": "",
                "processNodeCode": "task968405252451770368",
                "formBizCode": "cw_customer_profile",
                "desformComKey": "1776136714752_611525",
                "writable": false,
                "required": false,
                "original": false,
                "del": false,
                "enabled": false,
                "displayable": false
            },
            {
                "ruleName": "电子邮箱",
                "ruleCode": "input_1776136714759_464654",
                "processId": "",
                "processNodeCode": "task968405252451770368",
                "formBizCode": "cw_customer_profile",
                "desformComKey": "1776136714759_793619",
                "writable": false,
                "required": false,
                "original": false,
                "del": false,
                "enabled": false,
                "displayable": false
            },
            {
                "ruleName": "所在地区",
                "ruleCode": "input_1776136714766_715796",
                "processId": "",
                "processNodeCode": "task968405252451770368",
                "formBizCode": "cw_customer_profile",
                "desformComKey": "1776136714766_464456",
                "writable": true,
                "required": false,
                "original": false,
                "del": false,
                "enabled": true,
                "displayable": true
            },
            {
                "ruleName": "开户银行",
                "ruleCode": "input_1776136714773_226199",
                "processId": "",
                "processNodeCode": "task968405252451770368",
                "formBizCode": "cw_customer_profile",
                "desformComKey": "1776136714773_941268",
                "writable": true,
                "required": false,
                "original": false,
                "del": false,
                "enabled": true,
                "displayable": true
            },
            {
                "ruleName": "银行账号",
                "ruleCode": "input_1776136714779_370995",
                "processId": "",
                "processNodeCode": "task968405252451770368",
                "formBizCode": "cw_customer_profile",
                "desformComKey": "1776136714779_237621",
                "writable": true,
                "required": false,
                "original": false,
                "del": false,
                "enabled": true,
                "displayable": true
            },
            {
                "ruleName": "信用等级",
                "ruleCode": "select_1776136714786_913430",
                "processId": "",
                "processNodeCode": "task968405252451770368",
                "formBizCode": "cw_customer_profile",
                "desformComKey": "1776136714786_126405",
                "writable": true,
                "required": false,
                "original": false,
                "del": false,
                "enabled": true,
                "displayable": true
            },
            {
                "ruleName": "备注",
                "ruleCode": "textarea_1776136714792_725725",
                "processId": "",
                "processNodeCode": "task968405252451770368",
                "formBizCode": "cw_customer_profile",
                "desformComKey": "1776136714792_781385",
                "writable": true,
                "required": false,
                "original": false,
                "del": false,
                "enabled": true,
                "displayable": true
            }
        ],
        "configure": {},
        "childNode": {
            "id": "task968405436317474816",
            "name": "获取单条数据",
            "type": "data_get_one",
            "status": -1,
            "attr": {
                "selectType": 1,
                "formType": 2,
                "formModel": {},
                "formTableId": "form_task968405436317474816_cw_account_subject",
                "formTableCode": "cw_account_subject",
                "formTableName": "会计科目表",
                "formTableSourceTaskId": "",
                "formTableSourceGetDataType": null,
                "linkFormTableField": null,
                "userFormTableField": null,
                "deptFormTableField": null,
                "roleFormTableField": null,
                "expressionType": "delegateExpression",
                "expressionValue": "${getOneRecordDelegate}",
                "searchContent": [],
                "searchFieldGroup": [],
                "sortField": "create_time",
                "ignoreSortRule": false,
                "sortType": "desc",
                "noDataType": 1,
                "level": "2"
            },
            "configure": {},
            "childNode": {
                "id": "task968405526662782976",
                "name": "获取数据填写",
                "type": "edit",
                "status": -1,
                "attr": {
                    "approvalEnabled": false,
                    "approvalMethod": 1,
                    "sameMode": 1,
                    "assigneeIsEmpty": 0,
                    "skipApproval": 0,
                    "ratio": 0.5,
                    "loopCardinality": null,
                    "isSequential": false,
                    "collection": "${flowUtil.stringToList(assigneeUserIdList)}",
                    "elementVariable": "assigneeUserId",
                    "completionCondition": null,
                    "timeDate": null,
                    "timeType": "timeDate",
                    "allowAddSign": false,
                    "allowCountersignAddUser": false,
                    "formEditStatus": false,
                    "transferStatus": true,
                    "rejectStatus": true,
                    "ccStatus": true,
                    "msgStatus": false,
                    "selnextUserStatus": false,
                    "formTableId": "form_task968405436317474816_cw_account_subject",
                    "level": "3",
                    "formTableName": "会计科目表",
                    "formTableCode": "cw_account_subject",
                    "formTableSourceNodeType": "search",
                    "formTableSourceTaskId": "task968405436317474816",
                    "nodeTimeout": 2
                },
                "taskListenerData": [],
                "listenerData": [],
                "approverGroups": [
                    {
                        "id": "group968405526662782977",
                        "approverType": "candidateUser",
                        "assigneeType": "assigneeByExp",
                        "levelMode": 1,
                        "approverIds": [],
                        "approverId": "",
                        "approverNames": [],
                        "approverName": "",
                        "deptIds": [],
                        "deptNames": [],
                        "postIds": [],
                        "postNames": [],
                        "roleIds": [],
                        "roleNames": [],
                        "expressionsIds": [
                            "${applyUserId}"
                        ],
                        "expressionsNames": [
                            "获取发起人"
                        ]
                    }
                ],
                "approverType": "candidateGroups",
                "assigneeType": "assigneeByName",
                "approvalMode": 1,
                "privileges": [
                    {
                        "ruleName": "科目编码",
                        "ruleCode": "input_1776136707707_791404",
                        "processId": "",
                        "processNodeCode": "task968405526662782976",
                        "formBizCode": "cw_account_subject",
                        "desformComKey": "1776136707707_659176",
                        "writable": true,
                        "required": true,
                        "original": false,
                        "del": false,
                        "enabled": true,
                        "displayable": true
                    },
                    {
                        "ruleName": "科目名称",
                        "ruleCode": "input_1776136707714_412360",
                        "processId": "",
                        "processNodeCode": "task968405526662782976",
                        "formBizCode": "cw_account_subject",
                        "desformComKey": "1776136707714_796889",
                        "writable": true,
                        "required": false,
                        "original": false,
                        "del": false,
                        "enabled": true,
                        "displayable": true
                    },
                    {
                        "ruleName": "科目类型",
                        "ruleCode": "select_1776136707721_165878",
                        "processId": "",
                        "processNodeCode": "task968405526662782976",
                        "formBizCode": "cw_account_subject",
                        "desformComKey": "1776136707721_635490",
                        "writable": false,
                        "required": false,
                        "original": false,
                        "del": false,
                        "enabled": true,
                        "displayable": true
                    },
                    {
                        "ruleName": "余额方向",
                        "ruleCode": "select_1776136707727_840927",
                        "processId": "",
                        "processNodeCode": "task968405526662782976",
                        "formBizCode": "cw_account_subject",
                        "desformComKey": "1776136707727_275302",
                        "writable": false,
                        "required": false,
                        "original": false,
                        "del": false,
                        "enabled": true,
                        "displayable": false
                    },
                    {
                        "ruleName": "上级科目",
                        "ruleCode": "input_1776136707734_991397",
                        "processId": "",
                        "processNodeCode": "task968405526662782976",
                        "formBizCode": "cw_account_subject",
                        "desformComKey": "1776136707734_816719",
                        "writable": false,
                        "required": false,
                        "original": false,
                        "del": false,
                        "enabled": true,
                        "displayable": false
                    },
                    {
                        "ruleName": "是否末级",
                        "ruleCode": "radio_1776136707741_312968",
                        "processId": "",
                        "processNodeCode": "task968405526662782976",
                        "formBizCode": "cw_account_subject",
                        "desformComKey": "1776136707741_362282",
                        "writable": false,
                        "required": false,
                        "original": false,
                        "del": false,
                        "enabled": false,
                        "displayable": false
                    },
                    {
                        "ruleName": "币种",
                        "ruleCode": "select_1776136707747_624507",
                        "processId": "",
                        "processNodeCode": "task968405526662782976",
                        "formBizCode": "cw_account_subject",
                        "desformComKey": "1776136707747_445587",
                        "writable": false,
                        "required": false,
                        "original": false,
                        "del": false,
                        "enabled": false,
                        "displayable": false
                    },
                    {
                        "ruleName": "备注",
                        "ruleCode": "textarea_1776136707754_532619",
                        "processId": "",
                        "processNodeCode": "task968405526662782976",
                        "formBizCode": "cw_account_subject",
                        "desformComKey": "1776136707754_986691",
                        "writable": false,
                        "required": false,
                        "original": false,
                        "del": false,
                        "enabled": false,
                        "displayable": false
                    }
                ],
                "configure": {},
                "childNode": null,
                "addable": true,
                "deletable": false,
                "error": false,
                "errorContent": "",
                "content": "获取发起人",
                "pid": "task968405436317474816"
            },
            "addable": true,
            "deletable": false,
            "error": false,
            "content": "工作表 \"会计科目表\"",
            "pid": "task968405252451770368",
            "errorContent": ""
        },
        "addable": true,
        "deletable": false,
        "error": false,
        "errorContent": "",
        "content": "admin",
        "pid": "start"
    },
    "addable": true,
    "startType": "manual",
    "timeType": "timeDate",
    "timeDate": null,
    "timeCycle": "PT1H",
    "entTime": null,
    "messageEventName": null,
    "formTableList": [
        {
            "formTableId": "form_start_cw_customer_profile",
            "nodeId": "start",
            "nodeName": "工作表事件触发",
            "nodeType": "table",
            "formTableCode": "cw_customer_profile",
            "formTableName": "客户档案",
            "formTableMainCode": "cw_customer_profile",
            "selectType": 1,
            "level": 0
        },
        {
            "formTableId": "variable",
            "nodeId": "processVariable",
            "formTableCode": "_variable_",
            "nodeName": "流程参数",
            "formTableName": "流程参数",
            "nodeType": "variable"
        },
        {
            "formTableId": "form_task968405436317474816_cw_account_subject",
            "nodeId": "task968405436317474816",
            "nodeName": "获取单条数据",
            "nodeType": "search",
            "formTableCode": "cw_account_subject",
            "formTableName": "会计科目表",
            "formTableMainCode": "cw_account_subject",
            "selectType": 1,
            "formTableSourceGetDataType": null,
            "level": "2"
        }
    ],
    "listenerData": [],
    "attr": {
        "formType": 2,
        "startType": "tableEvent",
        "formTableId": "form_start_cw_customer_profile",
        "formTableCode": "cw_customer_profile",
        "formTableSourceId": null,
        "formTableName": "客户档案",
        "subFormTableObject": null,
        "titleField": "input_1776136714724_557407",
        "endDate": null,
        "beginDateStr": null,
        "endDateStr": null,
        "timeCycleName": null,
        "startEventType": "add|update",
        "startCondition": [],
        "conditionFields": [],
        "triggerField": null,
        "plusDate": null,
        "hourValues": [],
        "plusDateUnit": 3,
        "executionTime": null,
        "dayValues": [],
        "dayValue": 1,
        "hourType": 1,
        "signalEventName": null,
        "inputParams": [],
        "selectType": 1
    },
    "variableList": [],
    "hasVariableList": true,
    "hasInputParams": false,
    "executeListeners": [
        {
            "id": "402880e54803a496014805e5d9190012",
            "eventType": "end",
            "listenerType": "javaClass",
            "listenerName": "平台通用流程结束监听",
            "value": "org.jeecg.modules.extbpm.listener.execution.ProcessEndListener",
            "allowDel": false
        },
        {
            "id": "506880e54803a496014805e5d9190012",
            "eventType": "end",
            "listenerType": "javaClass",
            "listenerName": "流程结束删除redis数据",
            "value": "org.jeecg.modules.minides.listener.ProcessEndRemoveRedisListener",
            "allowDel": false
        }
    ],
    "taskListenerData": [
        {
            "eventType": "create",
            "listenerType": "class",
            "listenerName": "发起人节点跳过监听",
            "value": "org.jeecg.modules.extbpm.listener.task.TaskCreatedAutoSubmitListener"
        }
    ],
    "eventListeners": [
        {
            "listenerType": "javaClass",
            "listenerName": "任务创建全局监听",
            "value": "org.jeecg.modules.listener.tasktip.TaskCreateGlobalListener",
            "allowDel": false
        }
    ],
    "content": "工作表 \"客户档案\"",
    "errorContent": ""
}
```

### 延时节点示例（完整 processJson）

```json
{
    "id": "start",
    "startTaskId": "task968452415907078144",
    "name": "工作表事件触发",
    "type": "start",
    "createStartNode": false,
    "initiator": "applyUserId",
    "status": -1,
    "error": false,
    "startNodeContent": null,
    "childNode": {
        "id": "TimerEventDefinition_968452522509508608",
        "name": "指定时间",
        "type": "timer_event",
        "status": -1,
        "childNode": {
            "id": "TimerEventDefinition_968452877490233344",
            "name": "延迟1分钟",
            "type": "timer_event",
            "status": -1,
            "childNode": {
                "id": "TimerEventDefinition_968453021795262464",
                "name": "延时",
                "type": "timer_event",
                "status": -1,
                "childNode": null,
                "addable": true,
                "deletable": false,
                "error": false,
                "attr": {
                    "timeDate": "2026-04-15T12:13:14",   // ⚠️ custom 模式下，timeDate 存的是用户填的值（此处=具体时间）
                    "timeCycle": "custom",               // ← 「执行时间」选中「自定义」选项
                    "timeType": "timeDuration",
                    "level": "3"
                },
                "pid": "TimerEventDefinition_968452877490233344",
                "timeDate": ""
            },
            "addable": true,
            "deletable": false,
            "error": false,
            "attr": {
                "timeDate": null,
                "timeCycle": "PT1M",                     // ← 命中预设「1分钟后」，时长值直接放 timeCycle
                "timeType": "timeDuration",
                "level": "2"
            },
            "pid": "TimerEventDefinition_968452522509508608"
        },
        "addable": true,
        "deletable": false,
        "error": false,
        "attr": {
            "timeDate": "2026-04-14T19:00:00",
            "timeCycle": null,
            "timeType": "timeDate",
            "level": "1"
        },
        "pid": "start"
    },
    "addable": true,
    "startType": "manual",
    "timeType": "timeDate",
    "timeDate": null,
    "timeCycle": "PT1H",
    "entTime": null,
    "messageEventName": null,
    "formTableList": [
        {
            "formTableId": "form_start_ke_hu_shen_qing_co38",
            "nodeId": "start",
            "nodeName": "工作表事件触发",
            "nodeType": "table",
            "formTableCode": "ke_hu_shen_qing_co38",
            "formTableName": "客户信息",
            "formTableMainCode": "ke_hu_shen_qing_co38",
            "selectType": 1,
            "level": 0
        },
        {
            "formTableId": "variable",
            "nodeId": "processVariable",
            "formTableCode": "_variable_",
            "nodeName": "流程参数",
            "formTableName": "流程参数",
            "nodeType": "variable"
        }
    ],
    "listenerData": [],
    "attr": {
        "formType": 2,
        "startType": "tableEvent",
        "formTableId": "form_start_ke_hu_shen_qing_co38",
        "formTableCode": "ke_hu_shen_qing_co38",
        "formTableSourceId": null,
        "formTableName": "客户信息",
        "subFormTableObject": null,
        "titleField": "input_1775629274119_420857",
        "endDate": null,
        "beginDateStr": null,
        "endDateStr": null,
        "timeCycleName": null,
        "startEventType": "add|update",
        "startCondition": [],
        "conditionFields": [],
        "triggerField": null,
        "plusDate": null,
        "hourValues": [],
        "plusDateUnit": 3,
        "executionTime": null,
        "dayValues": [],
        "dayValue": 1,
        "hourType": 1,
        "signalEventName": null,
        "inputParams": [],
        "selectType": 1
    },
    "variableList": [],
    "hasVariableList": true,
    "hasInputParams": false,
    "executeListeners": [
        {
            "id": "402880e54803a496014805e5d9190012",
            "eventType": "end",
            "listenerType": "javaClass",
            "listenerName": "平台通用流程结束监听",
            "value": "org.jeecg.modules.extbpm.listener.execution.ProcessEndListener",
            "allowDel": false
        },
        {
            "id": "506880e54803a496014805e5d9190012",
            "eventType": "end",
            "listenerType": "javaClass",
            "listenerName": "流程结束删除redis数据",
            "value": "org.jeecg.modules.minides.listener.ProcessEndRemoveRedisListener",
            "allowDel": false
        }
    ],
    "taskListenerData": [
        {
            "eventType": "create",
            "listenerType": "class",
            "listenerName": "发起人节点跳过监听",
            "value": "org.jeecg.modules.extbpm.listener.task.TaskCreatedAutoSubmitListener"
        }
    ],
    "eventListeners": [
        {
            "listenerType": "javaClass",
            "listenerName": "任务创建全局监听",
            "value": "org.jeecg.modules.listener.tasktip.TaskCreateGlobalListener",
            "allowDel": false
        }
    ],
    "content": "工作表 \"客户信息\"",
    "errorContent": ""
}
```

### 脚本节点、服务节点示例（完整 processJson）

```json
{
    "id": "start",
    "startTaskId": "task969184373427576832",
    "name": "工作表事件触发",
    "type": "start",
    "createStartNode": false,
    "initiator": "applyUserId",
    "status": -1,
    "error": false,
    "startNodeContent": null,
    "childNode": {
        "id": "task969187462633136128",
        "name": "脚本节点",
        "type": "script",
        "status": -1,
        "attr": {
            "scriptFormat": "javascript",
            "scriptContent": "var sum = 2 + 9;\nexecution.setVariable(\"myVar\", sum);",
            "description": null,
            "level": "0.500"
        },
        "privileges": [],
        "configure": {},
        "childNode": {
            "id": "task969187433759547392",
            "name": "服务节点",
            "type": "service",
            "status": -1,
            "attr": {
                "resultVariable": null,
                "description": null,
                "expressionType": "class",
                "expressionValue": "org.jeecg.modules.testListenerExpression.TestService",
                "level": "1"
            },
            "childNode": null,
            "pid": "task969187462633136128",
            "error": false,
            "content": "已设置",
            "errorContent": ""
        },
        "addable": true,
        "deletable": false,
        "error": false,
        "content": "已设置",
        "pid": "start",
        "errorContent": ""
    },
    "addable": true,
    "startType": "manual",
    "timeType": "timeDate",
    "timeDate": null,
    "timeCycle": "PT1H",
    "entTime": null,
    "messageEventName": null,
    "formTableList": [
        {
            "formTableId": "form_start_ke_hu_shen_qing_co38",
            "nodeId": "start",
            "nodeName": "工作表事件触发",
            "nodeType": "table",
            "formTableCode": "ke_hu_shen_qing_co38",
            "formTableName": "客户信息",
            "formTableMainCode": "ke_hu_shen_qing_co38",
            "selectType": 1,
            "level": 0
        },
        {
            "formTableId": "variable",
            "nodeId": "processVariable",
            "formTableCode": "_variable_",
            "nodeName": "流程参数",
            "formTableName": "流程参数",
            "nodeType": "variable"
        }
    ],
    "listenerData": [],
    "attr": {
        "formType": 2,
        "startType": "tableEvent",
        "formTableId": "form_start_ke_hu_shen_qing_co38",
        "formTableCode": "ke_hu_shen_qing_co38",
        "formTableSourceId": null,
        "formTableName": "客户信息",
        "subFormTableObject": null,
        "titleField": "input_1775629274119_420857",
        "endDate": null,
        "beginDateStr": null,
        "endDateStr": null,
        "timeCycleName": null,
        "startEventType": "update",
        "startCondition": [],
        "conditionFields": [],
        "triggerField": null,
        "plusDate": null,
        "hourValues": [],
        "plusDateUnit": 3,
        "executionTime": null,
        "dayValues": [],
        "dayValue": 1,
        "hourType": 1,
        "signalEventName": null,
        "inputParams": [],
        "selectType": 1
    },
    "variableList": [],
    "hasVariableList": true,
    "hasInputParams": false,
    "executeListeners": [
        {
            "id": "402880e54803a496014805e5d9190012",
            "eventType": "end",
            "listenerType": "javaClass",
            "listenerName": "平台通用流程结束监听",
            "value": "org.jeecg.modules.extbpm.listener.execution.ProcessEndListener",
            "allowDel": false
        },
        {
            "id": "506880e54803a496014805e5d9190012",
            "eventType": "end",
            "listenerType": "javaClass",
            "listenerName": "流程结束删除redis数据",
            "value": "org.jeecg.modules.minides.listener.ProcessEndRemoveRedisListener",
            "allowDel": false
        }
    ],
    "taskListenerData": [
        {
            "eventType": "create",
            "listenerType": "class",
            "listenerName": "发起人节点跳过监听",
            "value": "org.jeecg.modules.extbpm.listener.task.TaskCreatedAutoSubmitListener"
        }
    ],
    "eventListeners": [
        {
            "listenerType": "javaClass",
            "listenerName": "任务创建全局监听",
            "value": "org.jeecg.modules.listener.tasktip.TaskCreateGlobalListener",
            "allowDel": false
        }
    ],
    "content": "工作表 \"客户信息\"",
    "errorContent": "",
    "privileges": []
}
```
