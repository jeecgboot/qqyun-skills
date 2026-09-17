"""
JeecgBoot 简流（MiniFlow）创建工具脚本

将简化的 JSON 配置转换为简流 processJson，并通过 API 创建简流。

用法（命令行）:
  python miniflow_creator.py --api-base <URL> --token <TOKEN> --config <config.json>
  python miniflow_creator.py --api-base <URL> --token <TOKEN> --config <config.json> --id <flow_id>

或在 Claude Code Python 块中直接 import 使用：
  from miniflow_creator import build_process_json, save_flow

节点类型:
  审批/填写:
  - approver        审批节点
  - edit            表单编辑节点（由发起人或指定人填写表单）

  数据操作:
  - data_update     更新记录（修改工作表字段值）
  - data_add        添加记录（向工作表新增一条记录）
  - data_delete     删除记录（删除工作表中的记录）
  - upvariable      更新流程参数（设置/更新流程内的变量，供分支条件引用）

  数据查询:
  - get_one         获取单条记录（从工作表/多条节点/关联字段查询一条）
  - get_more        获取多条记录（批量查询，可供批量操作或子流程使用）
  - get_one_sysinfo 获取单个系统人员/部门/角色（从用户组件/组织架构获取）
  - get_more_sysinfo获取多个系统人员/部门/角色（批量，配合子流程逐条处理）

  分支/流程控制:
  - exclusive       排他网关（条件分支，互斥，只走一个分支）
  - parallel        并行分支（所有分支同时执行，全部完成后继续）
  - inclusive       包含分支（满足条件的分支都执行）
  - opinion         意见分支（审批人手动点按钮选择分支，须跟在approver后）
  - data_branch     数据判断分支（有数据/无数据，须跟在emptyAction=3的get_one后）
  - time            延迟节点（等待指定时长或到达指定时间点）
  - notice          通知节点（发送消息给指定人员，支持系统/钉钉/企微/邮件）
  - operation       运算节点（数值运算/统计条数/函数计算）
  - subprocess      子流程节点（真实 type=callActivity，引用已有流程或批量处理多条记录）
  - service         服务任务节点（调用后端 Java 类或 Spring 委托表达式）
  - script          脚本节点（执行 JavaScript / Groovy 脚本）
"""

import urllib.request
import urllib.parse
import json
import sys
import time
import argparse
import hashlib

# 修复 Windows 控制台中文乱码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


# ====== ID 生成工具 ======

_id_counter = 0


def gen_id(prefix=''):
    """生成类雪花ID的节点ID"""
    global _id_counter
    _id_counter += 1
    ts = int(time.time() * 1000)
    uid = ts * 10000 + _id_counter
    return f'{prefix}{uid}'


# ====== 默认配置常量 ======

DEFAULT_APPROVER_ATTR = {
    "approvalEnabled": True,
    "approvalMethod": 1,   # 统一为 1，会签类型由节点级 approvalMode 区分
    "sameMode": 1,         # 保留字段，由系统内部使用，无需手动修改
    "assigneeIsEmpty": 0,
    "skipApproval": 0,
    "ratio": 0.5,
    "loopCardinality": None,
    "isSequential": False,
    "collection": "${flowUtil.stringToList(assigneeUserIdList)}",
    "elementVariable": "assigneeUserId",
    "completionCondition": None,
    "timeDate": None,
    "timeType": "timeDate",
    "allowAddSign": True,
    "allowCountersignAddUser": False,
    "formEditStatus": False,
    "transferStatus": True,
    "rejectStatus": True,
    "ccStatus": True,
    "msgStatus": False,
    "selnextUserStatus": True,
    "hasResultBranch": False,
}

# approvalMode → completionCondition 自动映射
# approvalMode=3: 所有人通过(并行/串行)  approvalMode=4: 一人通过  approvalMode=5: 半数通过
# approvalMode=6: 按比例投票             approvalMode=7: 自定义(由调用方填 completionCondition)
_APPROVAL_MODE_CONDITIONS = {
    3: "${nrOfCompletedInstances/nrOfInstances==1}",
    4: "${nrOfCompletedInstances/nrOfInstances>0}",
    5: "${nrOfCompletedInstances/nrOfInstances>=0.5}",
}

DEFAULT_EDIT_ATTR = {
    "approvalEnabled": False,
    "approvalMethod": 1,
    "sameMode": 1,
    "assigneeIsEmpty": 0,
    "skipApproval": 0,
    "ratio": 0.5,
    "loopCardinality": None,
    "isSequential": False,
    "collection": "${flowUtil.stringToList(assigneeUserIdList)}",
    "elementVariable": "assigneeUserId",
    "completionCondition": None,
    "timeDate": None,
    "timeType": "timeDate",
    "allowAddSign": False,
    "allowCountersignAddUser": False,
    "formEditStatus": False,
    "transferStatus": True,
    "rejectStatus": True,
    "ccStatus": True,
    "msgStatus": False,
    "selnextUserStatus": True,
}

DEFAULT_EXECUTE_LISTENERS = [
    {
        "id": "402880e54803a496014805e5d9190012",
        "eventType": "end",
        "listenerType": "javaClass",
        "listenerName": "平台通用流程结束监听",
        "value": "org.jeecg.modules.extbpm.listener.execution.ProcessEndListener",
        "allowDel": False
    },
    {
        "id": "506880e54803a496014805e5d9190012",
        "eventType": "end",
        "listenerType": "javaClass",
        "listenerName": "流程结束删除redis数据",
        "value": "org.jeecg.modules.minides.listener.ProcessEndRemoveRedisListener",
        "allowDel": False
    }
]

DEFAULT_TASK_LISTENER_DATA = [
    {
        "eventType": "create",
        "listenerType": "class",
        "listenerName": "发起人节点跳过监听",
        "value": "org.jeecg.modules.extbpm.listener.task.TaskCreatedAutoSubmitListener"
    }
]

DEFAULT_EVENT_LISTENERS = [
    {
        "listenerType": "javaClass",
        "listenerName": "任务创建全局监听",
        "value": "org.jeecg.modules.listener.tasktip.TaskCreateGlobalListener",
        "allowDel": False
    }
]

# 定时触发：timeCycleName → ISO 8601 Duration
_TIMER_CYCLE_ISO_MAP = {
    "每分钟":    "PT1M",
    "每小时":    "PT1H",   # 2026-09-10 订正：小时必须带 T（P1H 设计器解析失败）
    "每天":      "P1D",
    "每周":      "P7D",
    "每周一":    "P7D",
    "每周二":    "P7D",
    "每周三":    "P7D",
    "每周四":    "P7D",
    "每周五":    "P7D",
    "周一到周五": "P7D",
    "每月":      "P1M",
    "每月1号":   "P1M",
    "每年":      "P1Y",
}

# 定时触发：timeCycleName → 前端 attr.timeCycle 数字字符串编码
# ⚠️ 必须是字符串，整数编码前端下拉无法匹配，会显示原始数字。
_TIMER_CYCLE_CODE_MAP = {
    "每分钟":    "1",
    "每小时":    "2",
    "每天":      "3",
    "每月1号":   "4",
    "每周三":    "5",
    "周一到周五": "6",
    "每年12月31日": "7",
    "自定义":    "custom",
}


# ====== 节点构建函数 ======

def build_approver_group(group_config):
    """构建审批人组对象"""
    group_id = group_config.get("id", gen_id("group"))
    approver_type = group_config.get("approverType", "candidateUser")
    role_ids = group_config.get("roleIds", [])
    # candidateGroups 时 roleIds 必须填角色 Code（如 "dept_manager"），不是数据库 ID
    if approver_type == "candidateGroups" and role_ids:
        for rid in role_ids:
            if isinstance(rid, str) and rid.isdigit() and len(rid) > 10:
                raise ValueError(
                    f"roleIds 中检测到数据库 ID「{rid}」。\n"
                    f"candidateGroups 时 roleIds 必须填角色 Code（如 \"dept_manager\"），不是数据库 ID。\n"
                    f"请通过 /sys/role/list 查询角色 roleCode 后重新填写。"
                )
    # 填写人=表单字段：variableTitle 是设计器「指定填写对象」的显示来源，缺则面板为空。
    # 调用方通常只写 variableContent，这里从 fieldLabel 自动派生，别让每个建流脚本各记一遍。
    assignee_type = group_config.get("assigneeType", "assigneeByName")
    var_title = group_config.get("variableTitle", [])
    var_content = group_config.get("variableContent", "")
    if assignee_type == "assigneeByVariable" and not var_title and isinstance(var_content, list) and var_content:
        _label = (var_content[0] or {}).get("fieldLabel") if isinstance(var_content[0], dict) else None
        if _label:
            var_title = [_label]

    return {
        "id": group_id,
        "approverType": approver_type,
        "assigneeType": assignee_type,
        "levelMode": group_config.get("levelMode", 1),
        "approverIds": group_config.get("approverIds", []),
        "approverId": group_config.get("approverId", ""),
        "approverNames": group_config.get("approverNames", []),
        "approverName": group_config.get("approverName", ""),
        "deptIds": group_config.get("deptIds", []),
        "deptNames": group_config.get("deptNames", []),
        "roleIds": role_ids,
        "roleNames": group_config.get("roleNames", []),
        "postIds": group_config.get("postIds", []),
        "postNames": group_config.get("postNames", []),
        "expressionsIds": group_config.get("expressionsIds", []),
        "expressionsNames": group_config.get("expressionsNames", []),
        "variableTitle": var_title,
        "variableContent": var_content,
        "formTableType": group_config.get("formTableType", ""),
    }


def _get_approver_content(groups):
    """从 approverGroups 中提取显示文本（= 画布卡片「填写人：X」里的 X）

    variableTitle（填写人=表单字段）也要计入：否则卡片文案为空、设计器显示灰色
    「设置这个节点」未配置占位（2026-09-16 实测）。
    """
    names = []
    for g in groups:
        names.extend(g.get("variableTitle") or [])
        names.extend(g.get("approverNames", []))
        names.extend(g.get("deptNames", []))
        names.extend(g.get("roleNames", []))
        names.extend(g.get("postNames", []))
        names.extend(g.get("expressionsNames", []))
    return "、".join(names) if names else ""


def build_approver_node(node_config, form_config, level, parent_id=None):
    """构建审批节点"""
    node_id = node_config.get("id", gen_id("task"))
    approval_mode = node_config.get("approvalMode", 1)

    attr = dict(DEFAULT_APPROVER_ATTR)
    attr["level"] = str(level)
    # 从 form_config 注入表单绑定字段（字段权限生效的必要条件）
    form_table_code = form_config.get("formTableCode", "")
    attr["formTableCode"] = form_table_code
    attr["formTableName"] = form_config.get("formTableName", "")
    attr["formTableId"] = form_config.get("formTableId", f"form_start_{form_table_code}")
    attr["formTableSourceTaskId"] = "start"
    attr["formTableSourceNodeType"] = "table"
    attr.update(node_config.get("attr", {}))

    # 根据 approvalMode 自动补全 completionCondition 和 isSequential
    if approval_mode in (3, 4, 5, 6, 7):
        # approvalMode=4（一人通过）默认串行
        if approval_mode == 4 and "isSequential" not in node_config.get("attr", {}):
            attr["isSequential"] = True
        # approvalMode=6 按比例：用 ratio 动态生成
        if approval_mode == 6 and attr.get("completionCondition") is None:
            ratio = attr.get("ratio", 0.5)
            attr["completionCondition"] = f"${{nrOfCompletedInstances/nrOfInstances>={ratio}}}"
        # approvalMode=3/4/5 用固定映射；approvalMode=7 保持 None（由调用方填）
        elif approval_mode in _APPROVAL_MODE_CONDITIONS and attr.get("completionCondition") is None:
            attr["completionCondition"] = _APPROVAL_MODE_CONDITIONS[approval_mode]

    groups = [build_approver_group(g) for g in node_config.get("approverGroups", [])]
    # approverGroups 两处都写同值：attr 为界面面板处，节点顶层为副本（2026-09-15 实证）
    attr["approverGroups"] = groups
    content = _get_approver_content(groups)

    node = {
        "id": node_id,
        "name": node_config.get("name", "审批"),
        "type": "approver",
        "status": -1,
        "attr": attr,
        "taskListenerData": node_config.get("taskListenerData", []),
        "listenerData": node_config.get("listenerData", []),
        "approverGroups": groups,
        "approverType": "candidateGroups",
        "assigneeType": "assigneeByName",
        "approvalMode": approval_mode,
        "privileges": node_config.get("privileges", []),
        "configure": node_config.get("configure", {}),
        "childNode": None,
        "addable": True,
        "deletable": False,
        "error": False,
        "errorContent": "",
        "content": content,
        "pid": parent_id or "",
    }
    return node


def build_edit_node(node_config, form_config, level, parent_id=None):
    """构建表单编辑节点（edit）"""
    node_id = node_config.get("id", gen_id("task"))
    form_table_id = form_config.get("formTableId", f"form_start_{form_config.get('formTableCode', '')}")
    form_table_code = form_config.get("formTableCode", "")
    form_table_name = form_config.get("formTableName", "")
    source_task_id = node_config.get("formTableSourceTaskId", "start")

    attr = dict(DEFAULT_EDIT_ATTR)
    attr["formTableId"] = form_table_id
    attr["level"] = str(level)
    attr["formTableName"] = form_table_name
    attr["formTableCode"] = form_table_code
    attr["formTableSourceNodeType"] = "table"
    attr["formTableSourceTaskId"] = source_task_id
    attr.update(node_config.get("attr", {}))

    # 默认：表单节点由发起人操作
    default_groups = [
        {
            "approverType": "candidateUser",
            "assigneeType": "assigneeByExp",
            "expressionsIds": ["${applyUserId}"],
            "expressionsNames": ["获取发起人"],
        }
    ]
    groups = [build_approver_group(g) for g in node_config.get("approverGroups", default_groups)]
    # approverGroups 两处都写同值：attr 为界面面板处，节点顶层为副本（2026-09-15 实证）
    attr["approverGroups"] = groups
    content = _get_approver_content(groups)

    node = {
        "id": node_id,
        "name": node_config.get("name", "表单"),
        "type": "edit",
        "status": -1,
        "attr": attr,
        "taskListenerData": node_config.get("taskListenerData", []),
        "listenerData": node_config.get("listenerData", []),
        "approverGroups": groups,
        "approverType": "candidateGroups",
        "assigneeType": "assigneeByName",
        "approvalMode": 1,
        "privileges": node_config.get("privileges", []),
        "configure": node_config.get("configure", {}),
        "childNode": None,
        "addable": True,
        "deletable": False,
        "error": False,
        "errorContent": "",
        "content": content,
        "pid": parent_id or "start",
    }
    return node


def fix_edit_contents(process_json):
    """自愈：把 edit/approver 节点卡片文案里误写成「表达式原文」的 content 改回语义名。

    节点顶层 `content` = 设计器画布卡片里「填写人：xxx」那行，**界面自己拼前缀，落库只放显示名**：
    绑定表单字段 → 字段中文名；表达式/内置解析 → `expressionsNames`（如 `${applyUserId}` → 「获取发起人」）。
    把 `assigneeByExp(${applyUserId})` 原样写进 content，卡片会把这段代码直接显示出来
    （2026-09-16 用户实测指着卡片纠正「这里应该是 获取发起人」）。

    save 前调用：`fixes = fix_edit_contents(pj)`，有修正再 save+deploy。
    返回 [(节点id, 旧值, 新值)]，无修正返回 []；幂等（已正确的 content 不含 `$`/`assigneeBy`，不动）。
    """
    fixes = []

    def walk(node):
        if isinstance(node, list):
            for x in node:
                walk(x)
            return
        if not isinstance(node, dict):
            return
        if node.get("type") in ("edit", "approver"):
            cur = str(node.get("content") or "")
            if "$" in cur or "assigneeBy" in cur:
                name = _get_approver_content(node.get("approverGroups") or [])
                if name:
                    node["content"] = name
                    fixes.append((node.get("id"), cur, name))
        for v in node.values():
            walk(v)

    walk(process_json)
    return fixes


def fix_variable_titles(process_json):
    """自愈：填写人=表单字段（assigneeByVariable）的节点补 `variableTitle`。

    设计器「指定填写对象」面板读的是审批人组里的 `variableTitle`；只写 `variableContent`
    时画布卡片仍显示「填写人: X」（取自节点 content），但右侧面板的填写对象是**空的**，
    用户会以为流程没配好（2026-09-16 用户实测：「员工考勤确认 没有值」，已自愈重发）。

    契约（gotchas #1848）：`approverType='candidateUsers'` + `assigneeType='assigneeByVariable'`
    + `variableContent=[{formTableCode, formTableId:'form_start_<code>', nodeId:'start',
      nodeType:'table', fieldName:<人员字段 model>, fieldType:'select-user', fieldLabel:<中文名>}]`
    **+ `variableTitle:[<中文名>]`** + `formTableType:'table'`。

    `build_process_json` 已在返回前自动调用（幂等：仅当 variableTitle 为空且能从
    variableContent[0].fieldLabel 推出名字时才写）；改已有流程可直接调用本函数后 save+deploy。
    返回 [(节点名, 字段中文名)]，无改动返回 []。
    """
    fixes = []

    def walk(node):
        if isinstance(node, list):
            for x in node:
                walk(x)
            return
        if not isinstance(node, dict):
            return
        if node.get("type") in ("edit", "approver"):
            # approverGroups 两处都写同值：attr 为界面面板处、节点顶层为副本，两处都要补
            for holder in (node, node.get("attr") or {}):
                for g in (holder.get("approverGroups") or []):
                    if not isinstance(g, dict) or g.get("assigneeType") != "assigneeByVariable":
                        continue
                    vc = g.get("variableContent") or []
                    if not isinstance(vc, list) or not vc or not isinstance(vc[0], dict):
                        continue
                    label = vc[0].get("fieldLabel") or ""
                    if label and g.get("variableTitle") != [label]:
                        g["variableTitle"] = [label]
                        fixes.append((node.get("name"), label))
        for v in node.values():
            walk(v)

    walk(process_json)
    return fixes


def build_data_update_node(node_config, form_config, level, parent_id=None):
    """构建数据更新节点（data_update）"""
    node_id = node_config.get("id", gen_id("task"))
    form_table_code = node_config.get("formTableCode", form_config.get("formTableCode", ""))
    form_table_name = node_config.get("formTableName", form_config.get("formTableName", ""))
    source_task_id = node_config.get("formTableSourceTaskId", "start")
    form_table_id = node_config.get("formTableId", f"form_{source_task_id}_{form_table_code}")

    update_fields = []
    for uf in node_config.get("updateFields", []):
        field_id = uf.get("id", gen_id())
        val = uf.get("val", "")
        # val 直接使用：固定值时为字符串，引用变量时为对象（由调用方传入正确格式）
        # ⚠️ 不要把字符串包装成 {"funText": val, "funContext": {}}，前端无法识别该格式
        update_fields.append({
            "id": field_id,
            "optType": uf.get("optType", "1"),
            "fieldValue": uf.get("fieldValue", ""),
            "field": uf["field"],
            "val": val,
            "fieldType": uf.get("fieldType", ""),
            "type": uf.get("type", uf.get("fieldType", "")),
        })

    attr = {
        "formType": 2,
        "updateFields": update_fields,
        "formTableSourceTaskId": node_config.get("formTableSourceTaskId", "start"),
        # ⚠️ 不能硬编码 "table"：线上 44 条 data_update 的来源类型是
        # search(35，来自「取单条数据」) / plus(9，来自「新增记录」)，
        # 写 "table" = 更新目标行指错，运行时更新到别的行或更新不到。
        "formTableSourceNodeType": node_config.get("formTableSourceNodeType", "table"),
        "formTableCode": form_table_code,
        "formTableName": form_table_name,
        "expressionType": "delegateExpression",
        "expressionValue": "${updateRecordDelegate}",
        "level": str(level),
        "formTableId": form_table_id,
    }
    attr.update(node_config.get("attr", {}))

    node = {
        "id": node_id,
        "name": node_config.get("name", "更新记录"),
        "type": "data_update",
        "status": -1,
        "attr": attr,
        "configure": {},
        "childNode": None,
        "addable": True,
        "deletable": False,
        "error": False,
        "content": f'工作表 "{form_table_name}"',
        "pid": parent_id or "",
        "errorContent": "",
    }
    return node


def build_exclusive_gateway(node_config, form_config, level, parent_id=None):
    """构建排他网关（条件分支）"""
    gateway_id = node_config.get("id", gen_id("Gateway"))

    condition_nodes = []
    for branch in node_config.get("conditionNodes", []):
        branch_id = branch.get("id", gen_id("flow"))
        is_default = branch.get("isDefault", False)
        priority = branch.get("priorityLevel", 1)
        branch_type = 2 if is_default else branch.get("branchType", 1)

        # 支持简化的 conditions 列表 或 完整的 conditionGroup
        condition_group = []
        if branch.get("conditionGroup"):
            for cg in branch["conditionGroup"]:
                query_items = [
                    {
                        "rule": qi.get("rule", ""),
                        "ruleName": qi.get("ruleName", ""),
                        "valueType": qi.get("valueType", "1"),
                        "val": qi.get("val"),
                        "name": qi.get("name", None),
                        "field": qi.get("field", ""),
                        "columnName": qi.get("columnName", ""),
                        "type": qi.get("type", ""),
                        "valType": qi.get("valType", qi.get("type", "")),
                    }
                    for qi in cg.get("queryItems", [])
                ]
                condition_group.append({
                    "id": gen_id(),
                    "matchType": cg.get("matchType", ""),
                    "queryItems": query_items,
                })
        elif branch.get("conditions") and not is_default:
            query_items = [
                {
                    "rule": qi.get("rule", ""),
                    "ruleName": qi.get("ruleName", ""),
                    "valueType": qi.get("valueType", "1"),
                    "val": qi.get("val"),
                    "name": qi.get("name", None),
                    "field": qi.get("field", ""),
                    "columnName": qi.get("columnName", ""),
                    "type": qi.get("type", ""),
                    "valType": qi.get("valType", qi.get("type", "")),
                }
                for qi in branch["conditions"]
            ]
            condition_group.append({
                "id": gen_id(),
                "matchType": "",
                "queryItems": query_items,
            })

        branch_attr = {
            "branchType": branch_type,
            "priorityLevel": priority,
            "conditionGroup": condition_group,
            "showPriorityLevel": True,
            "level": str(level),
        }
        if not is_default:
            branch_attr["branchForm"] = {
                "formTableCode": form_config.get("formTableCode", ""),
                "formNodeId": "start",
                "formNodeType": "table",
            }
            branch_attr["formTableCode"] = form_config.get("formTableCode", "")

        # 构建分支的子节点链
        child_node = build_node_chain(branch.get("nodes", []), form_config, level + 1, parent_id=branch_id)

        # 生成条件展示文本
        if not is_default and condition_group:
            items = condition_group[0].get("queryItems", [])
            content_parts = [
                f'[{it.get("columnName", it.get("field", ""))} {it.get("ruleName", "")} {it.get("val", "")}]'
                for it in items
            ]
            content = " ".join(content_parts)
        else:
            content = branch.get("name", "其他情况") + "进入此流程"

        condition_node = {
            "id": branch_id,
            "pid": gateway_id,
            "name": branch.get("name", "分支"),
            "isDefault": is_default,
            "type": 3,
            "status": -1,
            "error": False,
            "childNode": child_node,
            "addable": True,
            "deletable": False,
            "attr": branch_attr,
            "content": content,
            "errorContent": "" if not is_default else None,
        }
        condition_nodes.append(condition_node)

    node = {
        "id": gateway_id,
        "name": node_config.get("name", "路由"),
        "type": "exclusive",
        "status": -1,
        "childNode": None,
        "addable": True,
        "conditionNodes": condition_nodes,
        "attr": {"level": str(level)},
        "pid": parent_id or "",
    }
    return node


def build_parallel_gateway(node_config, form_config, level, parent_id=None):
    """构建并行分支（所有分支同时执行，全部完成后才继续）

    注意：
    - conditionNode type 为 10（非 3），branchType 为 2
    - 并行网关的 childNode 必须是 polymerize 聚合节点
    - polymerize 节点的 pid 指向并行网关 ID
    """
    gateway_id = node_config.get("id", gen_id("Gateway"))
    polymerize_id = gen_id("Gateway")

    condition_nodes = []
    for i, branch in enumerate(node_config.get("conditionNodes", [])):
        branch_id = branch.get("id", gen_id("flow"))

        branch_attr = {
            "branchType": 2,
            "conditionGroup": [],
            "level": str(level),
        }

        child_node = build_node_chain(branch.get("nodes", []), form_config, level + 1, parent_id=branch_id)

        condition_node = {
            "id": branch_id,
            "pid": gateway_id,
            "name": branch.get("name", f"并行{i+1}"),
            "type": 10,
            "status": -1,
            "error": False,
            "childNode": child_node,
            "addable": True,
            "deletable": False,
            "attr": branch_attr,
            "content": "任意(其他)",
            "errorContent": None,
        }
        condition_nodes.append(condition_node)

    # 聚合节点（polymerize）作为并行网关的 childNode
    polymerize_node = {
        "id": polymerize_id,
        "pid": gateway_id,
        "name": "聚合",
        "type": "polymerize",
        "status": -1,
        "childNode": None,
        "addable": True,
        "deletable": False,
        "attr": {"level": str(level)},
    }

    node = {
        "id": gateway_id,
        "name": node_config.get("name", "并行审批"),
        "type": "parallel",
        "status": -1,
        "childNode": polymerize_node,
        "addable": True,
        "conditionNodes": condition_nodes,
        "attr": {"level": str(level)},
        "pid": parent_id or "",
    }
    return node


def build_inclusive_gateway(node_config, form_config, level, parent_id=None):
    """构建包含分支（满足条件的分支都执行，可走多个分支）"""
    gateway_id = node_config.get("id", gen_id("Gateway"))

    condition_nodes = []
    for branch in node_config.get("conditionNodes", []):
        branch_id = branch.get("id", gen_id("flow"))
        is_default = branch.get("isDefault", False)
        priority = branch.get("priorityLevel", 1)
        branch_type = 2 if is_default else branch.get("branchType", 1)

        condition_group = []
        if branch.get("conditionGroup"):
            for cg in branch["conditionGroup"]:
                query_items = [
                    {
                        "rule": qi.get("rule", ""),
                        "ruleName": qi.get("ruleName", ""),
                        "valueType": qi.get("valueType", "1"),
                        "val": qi.get("val"),
                        "name": qi.get("name", None),
                        "field": qi.get("field", ""),
                        "columnName": qi.get("columnName", ""),
                        "type": qi.get("type", ""),
                        "valType": qi.get("valType", qi.get("type", "")),
                    }
                    for qi in cg.get("queryItems", [])
                ]
                condition_group.append({
                    "id": gen_id(),
                    "matchType": cg.get("matchType", ""),
                    "queryItems": query_items,
                })
        elif branch.get("conditions") and not is_default:
            query_items = [
                {
                    "rule": qi.get("rule", ""),
                    "ruleName": qi.get("ruleName", ""),
                    "valueType": qi.get("valueType", "1"),
                    "val": qi.get("val"),
                    "name": qi.get("name", None),
                    "field": qi.get("field", ""),
                    "columnName": qi.get("columnName", ""),
                    "type": qi.get("type", ""),
                    "valType": qi.get("valType", qi.get("type", "")),
                }
                for qi in branch["conditions"]
            ]
            condition_group.append({
                "id": gen_id(),
                "matchType": "",
                "queryItems": query_items,
            })

        branch_attr = {
            "branchType": branch_type,
            "priorityLevel": priority,
            "conditionGroup": condition_group,
            "showPriorityLevel": True,
            "level": str(level),
        }
        if not is_default:
            branch_attr["branchForm"] = {
                "formTableCode": form_config.get("formTableCode", ""),
                "formNodeId": "start",
                "formNodeType": "table",
            }
            branch_attr["formTableCode"] = form_config.get("formTableCode", "")

        child_node = build_node_chain(branch.get("nodes", []), form_config, level + 1, parent_id=branch_id)

        if not is_default and condition_group:
            items = condition_group[0].get("queryItems", [])
            content_parts = [
                f'[{it.get("columnName", it.get("field", ""))} {it.get("ruleName", "")} {it.get("val", "")}]'
                for it in items
            ]
            content = " ".join(content_parts)
        else:
            content = branch.get("name", "其他情况") + "进入此流程"

        condition_node = {
            "id": branch_id,
            "pid": gateway_id,
            "name": branch.get("name", "分支"),
            "isDefault": is_default,
            "type": 3,
            "status": -1,
            "error": False,
            "childNode": child_node,
            "addable": True,
            "deletable": False,
            "attr": branch_attr,
            "content": content,
            "errorContent": "" if not is_default else None,
        }
        condition_nodes.append(condition_node)

    inclusive_end_id = gen_id("Gateway")
    inclusive_end_node = {
        "id": inclusive_end_id,
        "pid": gateway_id,
        "name": "聚合",
        "type": "inclusive_end",
        "status": -1,
        "childNode": None,
        "addable": True,
        "deletable": False,
        "error": False,
        "attr": {"level": str(level)},
    }

    node = {
        "id": gateway_id,
        "name": node_config.get("name", "包含路由"),
        "type": "inclusive",
        "status": -1,
        "childNode": inclusive_end_node,
        "addable": True,
        "conditionNodes": condition_nodes,
        "attr": {"level": str(level)},
        "pid": parent_id or "",
    }
    return node


# 延迟节点（timer_event）：「执行时间」单选组的 4 个 UI 预设 token。
# ⚠️ 设计器只认这 4 个字面值 + "custom"；预设外的时长（30分钟/1周/2小时30分…）
#    必须走 timeCycle="custom" + timeDate=<ISO 8601 Duration>，否则弹窗「执行时间」显示未选中。
# ⚠️「1小时后」的预设 token 是 P1H（**不是** ISO 的 PT1H）——PT1H 只用于"自定义"输入框。
_TIMER_DURATION_PRESETS = {
    "PT1M": "PT1M", "1分钟后": "PT1M", "1分钟": "PT1M",
    "P1H": "P1H", "PT1H": "P1H", "1小时后": "P1H", "1小时": "P1H",
    "P1D": "P1D", "1天后": "P1D", "1天": "P1D",
    "P1M": "P1M", "一个月后": "P1M", "1个月": "P1M",
}


def build_time_node(node_config, form_config, level, parent_id=None):
    """构建延迟节点（等待固定时长 / 到达指定时间点后继续）

    ⚠️ attr.timeCycle 是**模式选择器**，不是时长值：
      · 命中 UI 四预设（1分钟后/1小时后/1天后/一个月后）→ timeCycle=<预设 token>、timeDate=None
      · 其余任意时长（PT30M / PT2H30M / P7D / P14D / P3DT4H30M …）→ timeCycle="custom"
        + timeDate="<ISO 8601 Duration>"。写进 timeCycle 会 save/deploy 成功但设计器显示未设置。
      · 指定时间点（timeType="timeDate"）→ timeCycle=None、timeDate="YYYY-MM-DDTHH:mm:ss"

    时长可写在 node_config["duration"]，或 attr.timeCycle / attr.timeDate（兼容旧写法）：
        build_time_node({"id": "...", "name": "延时30分钟", "duration": "PT30M"}, ...)
        build_time_node({"id": "...", "name": "延时", "attr": {"timeType": "timeDate",
                                                              "timeDate": "2026-04-14T19:00:00"}}, ...)
    """
    node_id = node_config.get("id", gen_id("TimerEventDefinition_"))
    src = dict(node_config.get("attr") or {})
    for k in ("timeType", "timeCycle", "timeDate"):   # 顶层同名字段优先（兼容旧调用）
        if node_config.get(k) is not None:
            src[k] = node_config[k]

    time_type = src.get("timeType") or "timeDuration"
    _tc, _td = src.get("timeCycle"), src.get("timeDate")
    # timeCycle 已是 "custom" 时，真正的时长在 timeDate 里
    # duration 允许写顶层，也允许写 attr（两种调用方都见过；只认顶层时，
    # attr.duration=5 会被静默忽略、落回 PT1M）
    _raw = str(_td if _tc == "custom" else (
        node_config.get("duration") or src.get("duration") or _tc or _td or "PT1M")).strip()

    if time_type == "timeDate":
        attr = {"timeType": "timeDate", "timeCycle": None, "timeDate": _raw, "level": str(level)}
    else:
        _preset = _TIMER_DURATION_PRESETS.get(_raw)
        attr = {"timeType": "timeDuration", "timeCycle": _preset or "custom",
                "timeDate": None if _preset else _raw, "level": str(level)}

    node = {
        "id": node_id,
        "name": node_config.get("name", "延迟"),
        "type": "timer_event",
        "status": -1,
        "attr": attr,
        "configure": {},
        "childNode": None,
        "addable": True,
        "deletable": False,
        "error": False,
        "errorContent": "",
        "content": attr.get("timeDate") or attr.get("timeCycle") or "",
        "pid": parent_id or "",
    }
    return node


def build_notice_node(node_config, form_config, level, parent_id=None):
    """
    构建通知节点（向指定人员发送消息提醒）。

    noticeType 枚举（对应真实节点 type）：
      "system"    → type="message_system"   系统消息
      "email"     → type="message_email"    邮件通知
      "dingding"  → type="message_ding"     钉钉消息
      "weixinqy"  → type="message"          企业微信消息

    接收人配置（在 attr 或节点顶层）：
      toUserIds      固定用户/角色/部门 ID 列表，格式：["user.xxx", "role.xxx", "dept.xxx"]
      toUserNames    对应的显示名称列表
      toUserExpression  动态表达式，如 "${applyUserId}"（发起人）

    email 额外支持：
      copyToUserIds    抄送人 ID 列表
      copyToUserName   抄送人名称列表
      copyUserExpression  抄送人动态表达式
    """
    node_id = node_config.get("id", gen_id("task"))
    user_attr = node_config.get("attr", {})

    # noticeType → (node type, attr.type)
    notice_type = user_attr.get("noticeType", node_config.get("noticeType", "system"))
    _TYPE_MAP = {
        "system":   ("message_system", "system"),
        "email":    ("message_email",  "email"),
        "dingding": ("message_ding",   "dingtalk"),
        "weixinqy": ("message",        "wechat_enterprise"),
    }
    node_type, attr_type = _TYPE_MAP.get(notice_type, ("message_system", "system"))

    # 接收人：优先使用 toUserIds；未提供时若配了 approverGroups，从 expression 中提取
    to_user_ids   = user_attr.get("toUserIds",   node_config.get("toUserIds",   []))
    to_user_names = user_attr.get("toUserNames", node_config.get("toUserNames", []))
    to_user_expr  = user_attr.get("toUserExpression", node_config.get("toUserExpression", ""))

    # toUserExpression 无效（消息静默丢失），不再设默认值

    title   = user_attr.get("noticeTitle",   user_attr.get("title",   node_config.get("name", "消息通知")))
    content = user_attr.get("noticeContent", user_attr.get("templateContext", ""))

    attr = {
        "type": attr_type,
        "title": title,
        "description": user_attr.get("description", ""),
        "expressionType": "delegateExpression",
        "expressionValue": "${messageDelegate}",
        "templateContext": content,
        "toUserIds": to_user_ids,
        "toUserNames": to_user_names,
        "toUsers": [],
        "toUserExpression": to_user_expr,
        "level": str(level),
        "jsonContext": user_attr.get("jsonContext", {}),
    }

    if notice_type == "system":
        attr["receiveType"] = user_attr.get("receiveType", "user")

    if notice_type == "email":
        attr["sendType"] = user_attr.get("sendType", 1)
        attr["copyToUserIds"]  = user_attr.get("copyToUserIds", [])
        attr["copyToUserName"] = user_attr.get("copyToUserName", [])
        attr["copyUserExpression"] = user_attr.get("copyUserExpression", "")

    # 生成 content 摘要
    if to_user_names:
        content_str = "知会人:" + ",".join(to_user_names)
    elif to_user_expr:
        content_str = f"知会人:{to_user_expr}"
    else:
        content_str = "发送通知"

    node = {
        "id": node_id,
        "name": node_config.get("name", "发送通知"),
        "type": node_type,
        "status": -1,
        "attr": attr,
        # toUserIds 必须同时放在节点顶层，放在 attr 内无效
        "toUserIds":   to_user_ids,
        "toUserNames": to_user_names,
        "toUsers":     [],
        "privileges": [],
        "configure": {},
        "childNode": None,
        "addable": True,
        "deletable": False,
        "error": False,
        "errorContent": "",
        "content": content_str,
        "pid": parent_id or "",
    }

    return node


def build_data_delete_node(node_config, form_config, level, parent_id=None):
    """
    构建删除记录节点（data_delete）。

    删除对象可以是触发表单、新增记录节点、获取单条/多条记录节点对应的记录。
    通过 formTableSourceTaskId 指定要删除哪个节点的数据。
    """
    node_id = node_config.get("id", gen_id("task"))
    form_table_code = node_config.get("formTableCode", form_config.get("formTableCode", ""))
    form_table_name = node_config.get("formTableName", form_config.get("formTableName", ""))
    source_task_id = node_config.get("formTableSourceTaskId", "start")
    form_table_id = node_config.get("formTableId", f"form_{source_task_id}_{form_table_code}")

    attr = {
        "formType": 2,
        "formTableSourceTaskId": source_task_id,
        "formTableSourceNodeType": "table",
        "formTableCode": form_table_code,
        "formTableName": form_table_name,
        "expressionType": "delegateExpression",
        "expressionValue": "${deleteRecordDelegate}",
        "level": str(level),
        "formTableId": form_table_id,
    }
    attr.update(node_config.get("attr", {}))

    node = {
        "id": node_id,
        "name": node_config.get("name", "删除记录"),
        "type": "data_delete",
        "status": -1,
        "attr": attr,
        "configure": {},
        "childNode": None,
        "addable": True,
        "deletable": False,
        "error": False,
        "content": f'工作表 "{form_table_name}"',
        "pid": parent_id or "",
        "errorContent": "",
    }
    return node


def build_upvariable_node(node_config, form_config, level, parent_id=None):
    """
    构建更新流程参数节点（upvariable → 实际类型 data_update_variable）。

    用于在流程中更新预先定义的流程参数（如计数器、状态标记），
    后续节点（尤其是分支条件）可引用这些参数。

    updateVariable 示例（正确格式）：
      [{
          "field": "material_name_var",   # 流程参数变量名
          "compType": "input",
          "valueType": 2,                 # 2=取表单字段值
          "val": {
              "variableValue": "input_xxx",      # 表单字段 ID
              "formTableCode": "my_form_code",
              "variableName": "物料名称",
              "formNodeType": "table",
              "formNodeId": "start",
              "formNodeName": "工作表事件触发"
          }
      }]

    date 类型示例（固定日期赋值）：
      [{
          "type": "date",
          "field": "birthdate",
          "compType": "date",
          "val": "2026-04-14T09:07:44.076Z"   # ISO 字符串，无 valueType
      }]

    注意：type 省略时默认为 "variable"；date 类型的 val 为字符串，不含 valueType。
    """
    node_id = node_config.get("id", gen_id("task"))

    # 兼容 updateVariable（新格式）和 variableFields（旧格式）
    raw_items = node_config.get("updateVariable", node_config.get("variableFields", []))
    update_variable = []
    for item in raw_items:
        item_type = item.get("type", "variable")
        # date 类型：固定日期赋值，val 为 ISO 字符串；variable 类型：从表单取值，val 为对象
        entry = {
            "id": item.get("id", gen_id()),
            "type": item_type,
            "val": item.get("val", {} if item_type != "date" else ""),
            "compType": item.get("compType", item.get("fieldType", "input")),
            "field": item["field"],
        }
        if item_type != "date":
            entry["valueType"] = item.get("valueType", 2)
        update_variable.append(entry)

    attr = {
        "selectType": 1,
        "formType": 2,
        "formTableId": None,
        "formTableCode": None,
        "formTableName": "",
        "expressionType": "delegateExpression",
        "expressionValue": "${updateVariableDelegate}",
        "updateVariable": update_variable,
        "level": str(level),
    }
    attr.update({k: v for k, v in node_config.get("attr", {}).items()
                 if k not in ("updateVariable", "selectType", "formType",
                               "expressionValue", "formTableId", "formTableCode", "formTableName")})

    node = {
        "id": node_id,
        "name": node_config.get("name", "更新流程参数"),
        "type": "data_update_variable",
        "status": -1,
        "attr": attr,
        "configure": {},
        "childNode": None,
        "addable": True,
        "deletable": False,
        "error": False,
        "content": f"更新了 {len(update_variable)} 个参数",
        "pid": parent_id or "",
        "errorContent": "",
    }
    return node


def _build_query_conditions(conditions):
    """将简化条件列表转为 conditionGroup 结构"""
    if not conditions:
        return []
    query_items = [
        {
            "rule": c.get("rule", ""),
            "ruleName": c.get("ruleName", ""),
            "valueType": c.get("valueType", "1"),
            "val": c.get("val"),
            "name": c.get("name", None),
            "field": c.get("field", ""),
            "columnName": c.get("columnName", ""),
            "type": c.get("type", ""),
            "valType": c.get("valType", c.get("type", "")),
        }
        for c in conditions
    ]
    return [{"id": gen_id(), "matchType": "", "queryItems": query_items}]


def build_get_one_node(node_config, form_config, level, parent_id=None):
    """
    构建获取单条记录节点（get_one → 前端类型 data_get_one）。

    getType / selectType:
      1 = 从工作表直接查询（需 formTableCode/formTableName/conditions）
      2 = 从多条数据节点中取单条（需 sourceTaskId）
      3 = 从关联字段取单条（需 sourceTaskId + relationField）

    emptyAction / noDataType（未查到数据时，2026-09-15 设计器源码实证）:
      1 = 继续执行（之后节点使用本节点对象或数据时跳过执行）
      2 = 在工作表中新增记录后继续执行（仅 selectType=1 可选）
      3 = 中止流程，或继续执行查找结果分支（配 data_branch）
      未显式选择时默认 0
    """
    node_id = node_config.get("id", gen_id("task"))
    # 支持 getType（脚本简化名）和 selectType（后端名）
    get_type = node_config.get("selectType", node_config.get("getType", 1))
    form_table_code = node_config.get("formTableCode", form_config.get("formTableCode", ""))
    form_table_name = node_config.get("formTableName", form_config.get("formTableName", ""))
    source_task_id = node_config.get("sourceTaskId", node_config.get("formTableSourceTaskId", ""))

    # formTableId：
    #   selectType=1 → form_{nodeId}_{formTableCode}
    #   selectType=2/3 → form_{sourceTaskId}_{formTableCode}（指向源节点）
    if node_config.get("formTableId"):
        form_table_id = node_config["formTableId"]
    elif get_type == 1:
        form_table_id = f"form_{node_id}_{form_table_code}"
    else:
        form_table_id = f"form_{source_task_id}_{form_table_code}" if source_task_id else f"form_{node_id}_{form_table_code}"

    # formTableSourceNodeType：
    #   selectType=2 → "getMore"（源是 data_get_more 节点）
    #   selectType=3 → "table"（源是 start/工作表）或 "search"（源是其他 get_one 节点）
    _default_source_node_type = None
    if get_type == 2:
        _default_source_node_type = "getMore"
    elif get_type == 3:
        _default_source_node_type = "table" if source_task_id == "start" else "search"

    # 支持 conditions（简化）或 searchFieldGroup（后端原始）
    search_field_group = node_config.get(
        "searchFieldGroup",
        _build_query_conditions(node_config.get("conditions", []))
    )

    attr = {
        "selectType": get_type,            # 前端使用 selectType，不再是 getType
        "formType": 2,
        "formModel": {},
        "formTableCode": form_table_code,
        "formTableName": form_table_name,
        "formTableId": form_table_id,
        "formTableSourceTaskId": source_task_id,
        "formTableSourceGetDataType": node_config.get("formTableSourceGetDataType", None),
        "linkFormTableField": node_config.get("relationField", node_config.get("linkFormTableField", None)),
        "userFormTableField": node_config.get("userFormTableField", None),
        "deptFormTableField": node_config.get("deptFormTableField", None),
        "roleFormTableField": node_config.get("roleFormTableField", None),
        "expressionType": "delegateExpression",
        "expressionValue": "${getOneRecordDelegate}",
        "searchContent": [],
        "searchFieldGroup": search_field_group,  # 前端使用 searchFieldGroup，不再是 conditionGroup
        "sortField": node_config.get("orderField", node_config.get("sortField", "")),
        "ignoreSortRule": node_config.get("ignoreSortRule", False),
        "sortType": node_config.get("orderType", node_config.get("sortType", "asc")),
        "noDataType": node_config.get("emptyAction", node_config.get("noDataType", 0)),  # 前端使用 noDataType
        "level": str(level),
    }
    if _default_source_node_type and "formTableSourceNodeType" not in node_config.get("attr", {}):
        attr["formTableSourceNodeType"] = _default_source_node_type
    attr.update({k: v for k, v in node_config.get("attr", {}).items()
                 if k not in attr})

    node = {
        "id": node_id,
        "name": node_config.get("name", "获取单条记录"),
        "type": "data_get_one",            # 修复：前端类型为 data_get_one，不是 get_one
        "status": -1,
        "attr": attr,
        "configure": {},
        "childNode": None,
        "addable": True,
        "deletable": False,
        "error": False,
        "content": f'工作表 "{form_table_name}"',
        "pid": parent_id or "",
        "errorContent": "",
    }
    return node


def build_get_more_node(node_config, form_config, level, parent_id=None):
    """
    构建获取多条记录节点（get_more → 前端类型 data_get_more）。

    getType / selectType:
      1 = 从工作表直接查询多条（需 formTableCode/formTableName/conditions）
      3 = 从单条记录的关联字段取多条（需 sourceTaskId + relationField）
          → formTableSourceNodeType 自动推断：sourceTaskId=="start" 时="table"，否则="search"
      4 = 从新增节点（data_add plus节点）取刚新增的记录（需 sourceTaskId）
          → formTableSourceNodeType 自动设为 "plus"

    fetchMode / getDataType:
      "cache" / 1   = 执行到此节点时缓存数据（默认，推荐）
      "realtime" / 2 = 每次其他节点使用时实时查询
    """
    node_id = node_config.get("id", gen_id("task"))
    # 支持 getType（脚本简化名）和 selectType（后端名）
    get_type = node_config.get("selectType", node_config.get("getType", 1))
    form_table_code = node_config.get("formTableCode", form_config.get("formTableCode", ""))
    form_table_name = node_config.get("formTableName", form_config.get("formTableName", ""))
    _source_task_id = node_config.get("sourceTaskId", node_config.get("formTableSourceTaskId", ""))

    # formTableId：
    #   selectType=1 → null（不生成，由 formTableList 管理）
    #   selectType=3/4 → form_{sourceTaskId}_{formTableCode}（指向源节点）
    #   其他 → form_{nodeId}_{formTableCode}
    if node_config.get("formTableId") is not None:
        form_table_id = node_config["formTableId"]
    elif get_type == 1:
        form_table_id = None
    elif get_type in (3, 4) and _source_task_id:
        form_table_id = f"form_{_source_task_id}_{form_table_code}"
    else:
        form_table_id = f"form_{node_id}_{form_table_code}" if form_table_code else None

    # 支持 conditions（简化）或 searchFieldGroup（后端原始）
    search_field_group = node_config.get(
        "searchFieldGroup",
        _build_query_conditions(node_config.get("conditions", []))
    )

    # fetchMode → getDataType 映射
    fetch_mode = node_config.get("fetchMode", "cache")
    get_data_type = node_config.get("getDataType", 1 if fetch_mode == "cache" else 2)

    # formTableSourceNodeType 自动推断（可被 attr 覆盖）
    _default_source_node_type = None
    if get_type == 3:
        _default_source_node_type = "table" if _source_task_id == "start" else "search"
    elif get_type == 4:
        _default_source_node_type = "plus"

    attr = {
        "selectType": get_type,            # 前端使用 selectType
        "formType": 2,
        "formTableCode": form_table_code,
        "formTableName": form_table_name,
        "formTableId": form_table_id,
        "formTableSourceTaskId": _source_task_id,
        "linkFormTableField": node_config.get("relationField", node_config.get("linkFormTableField", None)),
        "expressionType": "delegateExpression",
        "expressionValue": "${getMoreRecordDelegate}",
        "searchContent": "",
        "searchFieldGroup": search_field_group,  # 前端使用 searchFieldGroup
        "sortField": node_config.get("orderField", node_config.get("sortField", "")),
        "ignoreSortRule": node_config.get("ignoreSortRule", False),
        "sortType": node_config.get("orderType", node_config.get("sortType", "asc")),
        "noDataType": node_config.get("emptyAction", node_config.get("noDataType", 1)),
        "getDataType": get_data_type,      # 1=缓存 2=实时
        "level": str(level),
    }
    # ⚠️ selectType=3「从单条记录获取关联记录」**不发 limitNum**（线上模版实测该键不存在）；
    # 发了数字 = 只取前 N 条，逐行子流程会静默漏行。
    if get_type != 3:
        attr["limitNum"] = node_config.get("limitCount", node_config.get("limitNum", 0))
    if _default_source_node_type:
        attr["formTableSourceNodeType"] = _default_source_node_type
    attr.update({k: v for k, v in node_config.get("attr", {}).items()
                 if k not in attr})
    if not attr.get("sortField"):
        attr.pop("sortField", None)        # 空排序键线上模版不落

    node = {
        "id": node_id,
        "name": node_config.get("name", "获取多条记录"),
        "type": "data_get_more",           # 修复：前端类型为 data_get_more，不是 get_more
        "status": -1,
        "attr": attr,
        "configure": {},
        "childNode": None,
        "addable": True,
        "deletable": False,
        "error": False,
        # selectType=3 的卡片写的是**明细表**名（线上模版：关联表 "退货产品明细"）
        "content": (f'关联表 "{attr.get("linkFormTableName") or form_table_name}"'
                    if get_type == 3 else f'工作表 "{form_table_name}"'),
        "pid": parent_id or "",
        "errorContent": "",
    }
    return node


def build_get_one_sysinfo_node(node_config, form_config, level, parent_id=None):
    """
    构建获取单个系统人员/部门/角色节点（get_one_sysinfo）。

    getType（selectType 映射）:
      "user_field"  → selectType=1  从工作表用户组件字段获取
      "dept_field"  → selectType=2  从工作表部门组件字段获取
      "role_field"  → selectType=3  从工作表角色组件字段获取
      "org_user"    → selectType=4  从组织架构查询用户
      "org_dept"    → selectType=5  从组织架构查询部门
      "org_role"    → selectType=6  从组织架构查询角色

    noDataType: 1=继续执行 / 2=在工作表中新增记录后继续 / 3=中止或进查找结果分支（默认 0）
    conditions:  筛选条件列表（对应 searchFieldGroup/userFormTableField 等）
    """
    node_id = node_config.get("id", gen_id("task"))
    get_type = node_config.get("getType", "org_user")
    no_data_type = node_config.get("noDataType", node_config.get("emptyAction", 0))
    search_conditions = _build_query_conditions(node_config.get("conditions", []))
    form_code = form_config.get("formTableCode", "")
    source_task_id = node_config.get("sourceTaskId", "start")

    # getType → selectType 映射
    SELECT_TYPE_MAP = {
        "user_field": 1, "dept_field": 2, "role_field": 3,
        "org_user": 4,   "org_dept": 5,   "org_role": 6,
    }
    # selectType → 系统表/字段属性名
    SYS_TABLE_MAP = {
        1: ("sys_user",   "userFormTableField"),
        2: ("sys_depart", "deptFormTableField"),
        3: ("sys_role",   "roleFormTableField"),
        4: ("sys_user",   None),
        5: ("sys_depart", None),
        6: ("sys_role",   None),
    }
    select_type = SELECT_TYPE_MAP.get(get_type, 4)
    sys_table, field_attr_name = SYS_TABLE_MAP[select_type]

    _SYS_TABLE_NAMES = {"sys_user": "用户表", "sys_depart": "部门表", "sys_role": "角色表"}
    node_name = node_config.get("name", "获取人员信息")

    if select_type <= 3:
        # 从工作表字段获取
        field_ids = node_config.get("fieldIds", node_config.get("sourceField", node_config.get("conditions", [])))
        field_list = field_ids if isinstance(field_ids, list) else [field_ids] if field_ids else []
        attr = {
            "selectType": select_type,
            "tenantId": "2",
            "formTableCode": form_code,
            "formTableId": f"form_{source_task_id}_{form_code}",
            "formTableSourceNodeType": "table",
            "formTableSourceTaskId": source_task_id,
            field_attr_name: field_list,
            "noDataType": no_data_type,
            "expressionType": "delegateExpression",
            "expressionValue": "${getUserDeptRoleOneDelegate}",
            "level": str(level),
        }
        form_table_list = [{
            "formTableId": f"form_{node_id}_{sys_table}",
            "nodeId": node_id,
            "nodeName": node_name,
            "nodeType": "getUserDeptRole",
            "formTableCode": sys_table,
            "formTableName": form_config.get("formTableName", ""),
            "formTableMainCode": form_code,
            "selectType": select_type,
            "level": str(level),
        }]
    else:
        # 从组织架构查询
        attr = {
            "selectType": select_type,
            "tenantId": "2",
            "formTableCode": sys_table,
            "formTableId": f"form_{node_id}_{sys_table}",
            "formTableSourceNodeType": "",
            "formTableSourceTaskId": "",
            "formTableSourceGetDataType": None,
            "searchFieldGroup": search_conditions,
            "noDataType": no_data_type,
            "expressionType": "delegateExpression",
            "expressionValue": "${getUserDeptRoleOneDelegate}",
            "level": str(level),
        }
        form_table_list = [{
            "formTableId": f"form_{node_id}_{sys_table}",
            "nodeId": node_id,
            "nodeName": node_name,
            "nodeType": "getUserDeptRole",
            "formTableCode": sys_table,
            "formTableName": _SYS_TABLE_NAMES.get(sys_table, sys_table),
            "formTableMainCode": sys_table,
            "selectType": select_type,
            "formTableSourceGetDataType": None,
            "level": str(level),
        }]

    attr.update({k: v for k, v in node_config.get("attr", {}).items() if k not in attr})

    node = {
        "id": node_id,
        "name": node_config.get("name", "获取人员信息"),
        "type": "data_get_udr_one",
        "status": -1,
        "attr": attr,
        "formTableList": form_table_list,
        "configure": {},
        "childNode": None,
        "addable": True,
        "deletable": False,
        "error": False,
        "content": get_type,
        "pid": parent_id or "",
        "errorContent": "",
    }
    return node


def build_get_more_sysinfo_node(node_config, form_config, level, parent_id=None):
    """
    构建获取多个系统人员/部门/角色节点（get_more_sysinfo）。

    getType（selectType 映射）:
      "user_field"  → selectType=1  从工作表用户组件字段获取多条
      "dept_field"  → selectType=2  从工作表部门组件字段获取多条
      "role_field"  → selectType=3  从工作表角色组件字段获取多条
      "org_user"    → selectType=4  从组织架构查询用户列表
      "org_dept"    → selectType=5  从组织架构查询部门列表
      "org_role"    → selectType=6  从组织架构查询角色列表

    noDataType: 1=继续执行 / 2=在工作表中新增记录后继续 / 3=中止或进查找结果分支（默认 0）
    conditions:  筛选条件列表（searchFieldGroup / xxxFormTableField）
    """
    node_id = node_config.get("id", gen_id("task"))
    get_type = node_config.get("getType", "org_user")
    no_data_type = node_config.get("noDataType", 1)
    search_conditions = _build_query_conditions(node_config.get("conditions", []))
    form_code = form_config.get("formTableCode", "")
    source_task_id = node_config.get("sourceTaskId", "start")

    SELECT_TYPE_MAP = {
        "user_field": 1, "dept_field": 2, "role_field": 3,
        "org_user": 4,   "org_dept": 5,   "org_role": 6,
    }
    SYS_TABLE_MAP = {
        1: ("sys_user",   "userFormTableField"),
        2: ("sys_depart", "deptFormTableField"),
        3: ("sys_role",   "roleFormTableField"),
        4: ("sys_user",   None),
        5: ("sys_depart", None),
        6: ("sys_role",   None),
    }
    _SYS_TABLE_NAMES = {"sys_user": "用户表", "sys_depart": "部门表", "sys_role": "角色表"}
    select_type = SELECT_TYPE_MAP.get(get_type, 4)
    sys_table, field_attr_name = SYS_TABLE_MAP[select_type]
    node_name = node_config.get("name", "获取多个人员信息")

    if select_type <= 3:
        # 从工作表字段获取多条
        field_ids = node_config.get("fieldIds", node_config.get("sourceField", node_config.get("conditions", [])))
        field_list = field_ids if isinstance(field_ids, list) else [field_ids] if field_ids else []
        attr = {
            "selectType": select_type,
            "tenantId": "2",
            "formTableCode": form_code,
            "formTableId": f"form_{source_task_id}_{form_code}",
            "formTableSourceTaskId": source_task_id,
            "formTableSourceNodeType": "table",
            field_attr_name: field_list,
            "searchFieldGroup": [],
            "ignoreSortRule": False,
            "sortType": "desc",
            "noDataType": no_data_type,
            "expressionType": "delegateExpression",
            "expressionValue": "${getUserDeptRoleMoreDelegate}",
            "level": str(level),
        }
        form_table_list = [{
            "formTableId": f"form_{node_id}_{sys_table}",
            "nodeId": node_id,
            "nodeName": node_name,
            "nodeType": "getMoreUserDeptRole",
            "formTableCode": sys_table,
            "formTableName": form_config.get("formTableName", ""),
            "formTableMainCode": form_code,
            "selectType": select_type,
            "level": str(level),
        }]
    else:
        # 从组织架构查询（selectType=4/5/6）
        attr = {
            "selectType": select_type,
            "tenantId": "2",
            "formTableId": sys_table,
            "formTableCode": sys_table,
            "formTableSourceTaskId": "",
            "formTableSourceGetDataType": None,
            "searchFieldGroup": search_conditions,
            "userFormTableField": [],
            "ignoreSortRule": False,
            "sortType": "desc",
            "noDataType": no_data_type,
            "expressionType": "delegateExpression",
            "expressionValue": "${getUserDeptRoleMoreDelegate}",
            "level": str(level),
        }
        form_table_list = [{
            "formTableId": f"form_{node_id}_",
            "nodeId": node_id,
            "nodeName": node_name,
            "nodeType": "getMoreUserDeptRole",
            "formTableCode": "",
            "formTableName": _SYS_TABLE_NAMES.get(sys_table, sys_table),
            "formTableMainCode": sys_table,
            "selectType": select_type,
            "formTableSourceGetDataType": None,
            "level": str(level),
        }]

    attr.update({k: v for k, v in node_config.get("attr", {}).items() if k not in attr})

    node = {
        "id": node_id,
        "name": node_config.get("name", "获取多个人员信息"),
        "type": "data_get_udr_more",
        "status": -1,
        "attr": attr,
        "formTableList": form_table_list,
        "configure": {},
        "childNode": None,
        "addable": True,
        "deletable": False,
        "error": False,
        "content": get_type,
        "pid": parent_id or "",
        "errorContent": "",
    }
    return node


def build_data_add_node(node_config, form_config, level, parent_id=None):
    """
    构建添加记录节点（data_add）。

    参数（node_config 顶层或 attr 内均可）：
      formTableCode   目标工作表 code
      formTableName   目标工作表名称
      formTableId     目标表 formTableId（默认 form_{nodeId}_{code}）
      addDataType     1=单条新增（默认），2=基于 get_more 逐条新增
      formModel       字典，key=目标字段ID，value=字段值配置对象
                      （详见 references/gotchas.md #22 与 miniflow-node-types.md data_add 节）
      formTableSourceTaskId   来源节点 ID（addDataType=2 时填 get_more 节点ID）
      formTableSourceNodeType 来源节点类型（addDataType=2 时填 "getMore"）
      formTableSourceCode     来源节点的 formTableCode（addDataType=2 时填）
      formTableSourceGetDataType  1=从Redis缓存 2=从数据库（addDataType=2 时填）
      formTableSourceId       来源节点的 formTableId（addDataType=2 时填）
    """
    node_id = node_config.get("id", gen_id("task"))
    user_attr = node_config.get("attr", {})

    target_code = node_config.get("formTableCode", user_attr.get("formTableCode", form_config.get("formTableCode", "")))
    target_name = node_config.get("formTableName", user_attr.get("formTableName", form_config.get("formTableName", "")))
    target_id = node_config.get("formTableId", user_attr.get("formTableId", f"form_{node_id}_{target_code}"))
    add_data_type = node_config.get("addDataType", user_attr.get("addDataType", 1))

    # formModel：key=目标字段ID，value=字段值配置对象（由调用方直接提供）
    form_model = node_config.get("formModel", user_attr.get("formModel", {}))

    attr = {
        "addDataType": add_data_type,
        "noDataType": 1,
        "formType": 2,
        "formModel": form_model,
        "formTableId": target_id,
        "formTableCode": target_code,
        "formTableName": target_name,
        "formTableSourceTaskId": node_config.get("formTableSourceTaskId", user_attr.get("formTableSourceTaskId", "")),
        "formTableSourceNodeType": node_config.get("formTableSourceNodeType", user_attr.get("formTableSourceNodeType", "")),
        "expressionType": "delegateExpression",
        "expressionValue": "${addRecordDelegate}",
        "level": str(level),
    }
    # addDataType=2 的额外字段
    if add_data_type == 2:
        for k in ("formTableSourceCode", "formTableSourceGetDataType", "formTableSourceId"):
            v = node_config.get(k, user_attr.get(k))
            if v is not None:
                attr[k] = v
    # 其余 attr 透传（排除已处理的字段避免重复）
    _handled = {"addDataType", "noDataType", "formType", "formModel", "formTableId",
                "formTableCode", "formTableName", "formTableSourceTaskId", "formTableSourceNodeType",
                "expressionType", "expressionValue", "level",
                "formTableSourceCode", "formTableSourceGetDataType", "formTableSourceId"}
    for k, v in user_attr.items():
        if k not in _handled:
            attr[k] = v

    node = {
        "id": node_id,
        "name": node_config.get("name", "添加记录"),
        "type": "data_add",
        "status": -1,
        "attr": attr,
        "configure": {},
        "childNode": None,
        "addable": True,
        "deletable": False,
        "error": False,
        "content": f'工作表 "{target_name}"',
        "pid": parent_id or "",
        "errorContent": "",
    }
    return node


def build_opinion_gateway(node_config, form_config, level, parent_id=None):
    """
    构建意见分支（suggest/opinion）。

    审批人处理任务时手动选择走哪个分支，分支名称 = 审批界面的按钮名称。
    必须紧跟在审批节点（approver）之后使用。

    conditionNodes 示例：
      [{"name": "同意", "nodes": [...]}, {"name": "不同意", "nodes": [...]}]

    注意：
    - gateway ID 使用 suggest_{ts} 前缀
    - conditionNode ID 使用 btn{ts} 前缀（非 flow{ts}）
    - conditionNode type 为 8（非 3）
    - conditionNode 无子节点时不含 childNode 键
    """
    gateway_id = node_config.get("id", gen_id("suggest_"))

    condition_nodes = []
    for i, branch in enumerate(node_config.get("conditionNodes", [])):
        branch_id = branch.get("id", gen_id("btn"))
        child_node = build_node_chain(branch.get("nodes", []), form_config, level + 1, parent_id=branch_id)
        cn = {
            "id": branch_id,
            "pid": gateway_id,
            "name": branch.get("name", f"分支{i+1}"),
            "type": 8,
            "attr": {"priorityLevel": branch.get("priorityLevel", 2)},
            "status": -1,
            "addable": True,
            "deletable": False,
            "error": False,
        }
        # 只有存在子节点时才添加 childNode 键
        if child_node is not None:
            cn["childNode"] = child_node
        condition_nodes.append(cn)

    return {
        "id": gateway_id,
        "name": node_config.get("name", "意见分支"),
        "type": "suggest",
        "status": -1,
        "childNode": None,
        "addable": True,
        "error": False,
        "conditionNodes": condition_nodes,
        "attr": {"level": str(level)},
        "pid": parent_id or "",
    }


def build_data_branch_gateway(node_config, form_config, level, parent_id=None):
    """
    构建数据判断分支（data_branch）。

    基于 get_one 节点的查询结果自动分流：有数据走第一个分支，无数据走第二个分支。
    必须紧跟在 get_one 节点（emptyAction=3）之后使用。

    conditionNodes 应包含两个分支：
      [{"name": "有数据", "nodes": [...]}, {"name": "无数据", "nodes": [...]}]
    """
    gateway_id = node_config.get("id", gen_id("Gateway"))

    condition_nodes = []
    branch_names = ["有数据", "无数据"]
    for i, branch in enumerate(node_config.get("conditionNodes", [])):
        branch_id = branch.get("id", gen_id("flow"))
        child_node = build_node_chain(branch.get("nodes", []), form_config, level + 1, parent_id=branch_id)
        branch_name = branch.get("name", branch_names[i] if i < 2 else f"分支{i+1}")
        condition_nodes.append({
            "id": branch_id,
            "pid": gateway_id,
            "name": branch_name,
            "isDefault": False,
            "type": 3,
            "status": -1,
            "error": False,
            "childNode": child_node,
            "addable": True,
            "deletable": False,
            "attr": {
                "branchType": 2,
                "priorityLevel": i + 1,
                "conditionGroup": [],
                "showPriorityLevel": True,
                "level": str(level),
            },
            "content": "${flow_has_data==1}" if i == 0 else "${flow_has_data==0}",
            "errorContent": None,
        })

    return {
        "id": gateway_id,
        "name": node_config.get("name", "数据判断"),
        "type": "databranch",
        "status": -1,
        "childNode": None,
        "addable": True,
        "conditionNodes": condition_nodes,
        "attr": {"level": str(level)},
        "pid": parent_id or "",
    }


def build_operation_node(node_config, form_config, level, parent_id=None):
    """
    构建运算节点（operation/function → 实际类型 function）。

    funType 枚举：
      "number"    数值四则运算（默认）
      "fun"       函数计算（CONCAT/IF/SUM 等）
      "date"      日期加减时间，需提供 attr.dateFieldVal + attr.dateFunctionFormat
      "date-diff" 日期时长计算，需提供 attr.dateFieldVal + attr.dateFieldEndVal + attr.dateFunctionFormat
      "record"    统计 get_more 节点数据条数（funContext 结构不同，见方式三）

    方式一：formula 自动解析（推荐，适用于 number/fun，字段 ID 格式 type_timestamp_random）
      {
          "type": "operation",
          "name": "计算库存价值",
          "formula": "money_1776167663168_481661 * number_1776167663174_127741",
          "sourceTaskId": "start",   # 字段所在数据来源节点 ID
          "fieldNames": {"money_1776167663168_481661": "金额",   # 可选：{字段model: 中文名}
                         "number_1776167663174_127741": "数量"}  # 提供后 fieldText/content 自动中文
      }

    方式二：显式指定 funFields + funText（适用于复杂公式）
      {
          "type": "operation",
          "name": "计算",
          "funText": "{{0}}*{{1}}+100",   # {{0}} {{1}} 引用 funFields 中对应字段
          "funFields": [
              {"field": "money_xxx", "formTableCode": "my_form", "fieldText": "金额",
               "formNodeId": "start", "formNodeName": "工作表事件触发", "tableText": "表单"},
              {"field": "number_yyy", "formTableCode": "my_form", "fieldText": "数量", ...}
          ]
      }

    方式三：record 类型（统计 get_more 节点条数）
      {
          "type": "operation",
          "funType": "record",
          "name": "统计数据条数",
          "sourceTaskId": "task_get_more节点ID",
          "formTableCode": "表单code",
          "formTableName": "表单名",
          "getDataType": 1,    # get_more 节点的 getDataType（默认1）
      }
      # 脚本自动构建 funContext 和 funText，并将 operationMode 设为 "everyTime"

    ⚠️ funContext 条目 hash 必须用前端规则：md5(规范8键条目JSON的 UTF-8 原文, 紧凑序列化)。
      用其他规则（如 md5(字段ID)、ensure_ascii=True 转义）算出的 key，前端展示公式时按自己的
      规则重算匹配不上 → 编辑器回退显示 {{hash.字段}} 占位符原文（2026-09-08 实测）。
    """
    import re as _re
    node_id = node_config.get("id", gen_id("task"))
    formula = node_config.get("formula", node_config.get("functionExpr", ""))
    fun_fields = node_config.get("funFields", [])

    # funType 可省略：formula 以函数名 XXX( 开头自动判 fun（CONCAT/IF/SUM…），否则默认 number
    fun_type = node_config.get("funType", "") or (
        "fun" if _re.match(r"^\s*[A-Z_][A-Z0-9_]*\(", formula) else "number")

    def _hash_field_entry(entry):
        """前端规则：md5(紧凑 UTF-8 原文 JSON)。返回 (hash, URL编码值)"""
        raw = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
        # value 编码必须 UI 原生风格（仅转义 " { } 与非 ASCII，: , 原样，gotchas #54 末段实证）：
        # python 默认 safe="" 会把 : , 转成 %3A %2C → 前端重算匹配不上 → 公式框回退 {{hash.字段}} 原文
        return hashlib.md5(raw.encode("utf-8")).hexdigest(), urllib.parse.quote(raw, safe=":,.-_/?")

    if fun_fields:
        # 方式二：显式 funFields + funText 模板（{{0}} {{1}} ...）
        fun_context = {}
        fun_text = node_config.get("funText", formula)
        node_content = fun_text          # 卡片上显示中文算式，别让设计器露出 {{hash.字段}}
        for i, f in enumerate(fun_fields):
            fid = f["field"]
            entry = {
                "field": fid,
                "formTableCode": f.get("formTableCode", form_config.get("formTableCode", "")),
                "formNodeId": f.get("formNodeId", "start"),
                "formNodeType": "table",
                "variableValue": fid,
                "formNodeName": f.get("formNodeName", "工作表事件触发"),
                "tableText": f.get("tableText", form_config.get("formTableName", "")),
                "fieldText": f.get("fieldText", ""),
            }
            h, enc = _hash_field_entry(entry)
            fun_context[h] = enc
            fun_text = fun_text.replace(f"{{{{{i}}}}}", f"{{{{{h}.{fid}}}}}")
            node_content = node_content.replace(f"{{{{{i}}}}}", f.get("fieldText") or fid)
    elif fun_type == "record":
        # 方式三：统计 get_more 节点数据条数（funContext 是普通 dict，不是 hash → URL编码）
        source_task_id = node_config.get("sourceTaskId", "")
        ftc = node_config.get("formTableCode", form_config.get("formTableCode", ""))
        ftn = node_config.get("formTableName", form_config.get("formTableName", ""))
        ftid = node_config.get("formTableId", f"form_{source_task_id}_{ftc}" if source_task_id else "")
        get_data_type = node_config.get("getDataType", 1)
        fun_context = {
            "nodeId": source_task_id,
            "formTableCode": ftc,
            "getDataType": get_data_type,
            "formTableId": ftid,
            "formTableName": ftn,
        }
        fun_text = node_config.get("funText", ftid)
        node_content = None
    elif formula:
        # 方式一：从 formula 中自动提取字段 ID（格式：类型_时间戳_随机数）
        field_ids = list(dict.fromkeys(
            _re.findall(r'\b([a-z][a-z_]+_\d{10,}_\d+)\b', formula)
        ))
        fun_context = {}
        fun_text = formula
        source_task_id = node_config.get("sourceTaskId", "start")
        fc = form_config.get("formTableCode", "")
        fn = form_config.get("formTableName", "")
        field_names = node_config.get("fieldNames") or {}
        content_cn = formula  # 中文显示公式
        for fid in field_ids:
            entry = {
                "field": fid,
                "formTableCode": fc,
                "formNodeId": source_task_id,
                "formNodeType": "table",
                "variableValue": fid,
                "formNodeName": "工作表事件触发",
                "tableText": fn,
                "fieldText": field_names.get(fid, ""),
            }
            h, enc = _hash_field_entry(entry)
            fun_context[h] = enc
            fun_text = fun_text.replace(fid, f"{{{{{h}.{fid}}}}}")
            cn = field_names.get(fid)
            if cn:
                content_cn = content_cn.replace(fid, cn)
        # 字段中文名齐全时 content 用中文公式，否则退回原文（占位符形态）
        if field_names and all(fid in field_names for fid in field_ids):
            node_content = content_cn
        else:
            node_content = None
    else:
        # date / date-diff / fun 等类型：funContext 为空或由用户在 node_config 中直接提供
        fun_context = node_config.get("funContext", {})
        fun_text = node_config.get("funText", "")
        node_content = None

    # record 类型默认 operationMode=everyTime，其余默认 cache
    default_op_mode = "everyTime" if fun_type == "record" else "cache"

    attr = {
        "funType": fun_type,
        "funContext": fun_context,
        "funText": fun_text,
        "expressionType": "delegateExpression",
        "expressionValue": "${functionDelegate}",
        "level": str(level),
        "operationMode": node_config.get("operationMode", default_op_mode),
        "decimals": node_config.get("decimals", 2),
    }
    attr.update({k: v for k, v in node_config.get("attr", {}).items()
                 if k not in ("funType", "funContext", "funText", "expressionValue")})

    if node_content is None:
        node_content = (fun_text[:40] + "...") if len(fun_text) > 40 else fun_text

    return {
        "id": node_id,
        "name": node_config.get("name", "运算"),
        "type": "function",
        "status": -1,
        "attr": attr,
        "configure": {},
        "childNode": None,
        "addable": True,
        "deletable": False,
        "error": False,
        "content": node_config.get("content", node_content),
        "pid": parent_id or "",
        "errorContent": "",
    }


# 子流程 processKey → 真实数据库 ID 的注册表
# 在创建子流程后调用 register_subprocess_id(processKey, dbId) 登记，
# build_subprocess_node 会自动从注册表中查找，避免 processId 为空导致点击时空白。
_subprocess_id_registry: dict = {}


def register_subprocess_id(process_key: str, db_id: str) -> None:
    """登记子流程 processKey → 数据库 ID 的映射。

    在调用 save_flow 获得子流程 DB ID 后立即调用此函数，
    之后 build_subprocess_node 会自动使用正确的 DB ID。

    示例:
        result = save_flow(api, token, config, pj)
        sub_db_id = result['result']['id']
        register_subprocess_id(f'process{ts}SUB1', sub_db_id)
    """
    _subprocess_id_registry[process_key] = str(db_id)


def _is_valid_db_id(value: str) -> bool:
    """判断字符串是否是合法的雪花算法 DB ID（纯数字，长度 ≥ 15）。"""
    return bool(value) and value.isdigit() and len(value) >= 15


def build_subprocess_node(node_config, form_config, level, parent_id=None):
    """
    构建子流程节点（callActivity）。

    真实 type 为 "callActivity"，ID 前缀用 "Activity"。
    子流程的完整工作流分两步：
      ① 先用 save_flow+deploy_flow 创建独立子流程（startType="subEvent"）并发布；
      ② 再在父流程中添加本节点引用子流程。

    参数：
      customProcessId  子流程数字ID（存储在DB中的 id，非 processKey）
                       ★ 必须是纯数字的雪花 ID（如 2046511427177975811），
                         不能是 processKey 后缀（如 1776761321203SUB1）。
                         推荐在 save_flow 之后调用 register_subprocess_id() 自动注入。
      processName      子流程名称（显示用）
      sourceTaskId     上游 get_more 节点 ID（批量处理时必填）
      isMulti          是否多实例（批量处理时为 True，默认 True）
      isSequential     True=逐条串行，False=并行（默认 False）
      subFormTableObject   来源数据对象（从 get_more 节点的 formTableList 条目复制，
                           需加 isSubStart: True）
      inVariableModels 父→子变量传递列表（默认包含 applyUserId/dataId/handleDataId 等）
      outVariableModels 子→父变量回传列表（默认空）
      approvalEnabled  是否启用审批（默认 True）
    """
    node_id = node_config.get("id", gen_id("Activity"))
    user_attr = node_config.get("attr", {})

    # customProcessId = 子流程数据库 ID（DB id，非 processKey）
    custom_process_id = node_config.get("customProcessId", user_attr.get("customProcessId", ""))
    # processKey = 子流程 processKey（用于 calledElement），可单独传 calledElement 覆盖
    process_key = node_config.get("processKey", user_attr.get("processKey", ""))
    process_name = node_config.get("processName", user_attr.get("processName", node_config.get("name", "子流程")))

    # ── 自动查注册表，解决 processId 为空 / 误传 processKey 后缀导致点击子流程空白 ──
    # 计算 calledElement 候选值（用于注册表查找）
    _called_candidate = node_config.get("calledElement", user_attr.get("calledElement", ""))
    if not _called_candidate and process_key:
        _called_candidate = process_key if process_key.startswith("process") else f"process{process_key}"
    # 1. 若 customProcessId 非法（非纯数字雪花 ID），尝试从注册表查找
    if not _is_valid_db_id(custom_process_id):
        registered = _subprocess_id_registry.get(_called_candidate, "")
        if registered:
            print(f"[subprocess] 自动注入 processId: {_called_candidate} → {registered}")
            custom_process_id = registered
        else:
            # 非法值且注册表中无记录 → 抛出明确错误，防止无声创建空白子流程
            bad_val = repr(custom_process_id)
            hint = (
                f"\n  解决方法：在创建子流程后立即调用\n"
                f"  register_subprocess_id('{_called_candidate}', result['result']['id'])\n"
                f"  其中 result 是 save_flow 的返回值。"
            )
            raise ValueError(
                f"[subprocess] customProcessId={bad_val} 不是有效的数据库 ID（需为纯数字雪花 ID，如 2046511427177975811）。"
                f"{hint}"
            )
    source_task_id = node_config.get("sourceTaskId", user_attr.get("formTableSourceTaskId", ""))
    is_multi = node_config.get("isMulti", user_attr.get("isMulti", True))
    is_sequential = node_config.get("isSequential", user_attr.get("isSequential", False))
    sub_form_table_obj = node_config.get("subFormTableObject", user_attr.get("subFormTableObject", None))

    # calledElement 优先用显式传入的 calledElement，其次用 processKey，兜底用 customProcessId 拼接（向后兼容）
    explicit_called = node_config.get("calledElement", user_attr.get("calledElement", ""))
    if explicit_called:
        called_element = explicit_called
    elif process_key:
        called_element = process_key if process_key.startswith("process") else f"process{process_key}"
    else:
        called_element = f"process{custom_process_id}" if custom_process_id else ""
    # formTableId 来自 subFormTableObject
    sub_form_table_id = sub_form_table_obj.get("formTableId", "") if sub_form_table_obj else ""

    attr = {
        "approvalEnabled": node_config.get("approvalEnabled", user_attr.get("approvalEnabled", True)),
        "calledElement": called_element,
        "formTableName": node_config.get("formTableName", user_attr.get("formTableName", None)),
        "formTableSourceTaskId": source_task_id,
        "formTableCode": node_config.get("formTableCode", user_attr.get("formTableCode", None)),
        "processName": process_name,
        # ⚠️ processId 线上 25 条全是空串（实测分布：21 空串 / 4 null，无一例外）。
        # 早先这里写 DB id —— 引擎认的是 customProcessId，写这里只会和模版对不上。
        "processId": "",
        "customProcessId": custom_process_id,
        "loopCardinality": None,
        "ratio": 0.5,
        "isSequential": is_sequential,
        "isMulti": is_multi,
        "subFormTableObject": sub_form_table_obj,
        "collection": "${flowUtil.stringToList(assigneeUserIdList)}",
        "elementVariable": "assigneeUserId",
        "completionCondition": None,
        # 父→子的传参：**必须在这里传**。早先这里恒为 []，且透传时被 _handled 挡掉，
        # 于是子流程里所有「流程变量」永远是空的——子流程照跑、一行都不写。
        "variableList": node_config.get("variableList")
                        or user_attr.get("variableList") or [],
        "level": str(level),
        "formTableId": sub_form_table_id,
    }
    # 透传其余 attr
    _handled = set(attr.keys())
    for k, v in user_attr.items():
        if k not in _handled:
            attr[k] = v

    default_in_vars = [
        {"source": "applyUserId", "target": "applyUserId"},
        {"source": "dataId", "target": "dataId"},
        {"source": "JG_LOCAL_PROCESS_ID", "target": "JG_SUB_MAIN_PROCESS_ID"},
        {"source": "handleDataId", "target": "handleDataId"},
    ]

    return {
        "id": node_id,
        "name": node_config.get("name", "子流程"),
        "type": "callActivity",
        "status": -1,
        "attr": attr,
        "approvalMode": 1,
        "listenerData": [
            {
                "id": "502880e54853a496014805e5d9190012",
                "eventType": "start",
                "listenerType": "javaClass",
                "listenerName": "子流程流程变量",
                "value": "org.jeecg.modules.extbpm.process.adapter.delegate.MiniCallActivityListener",
                "allowDel": False,
            }
        ],
        "inVariableModels": node_config.get("inVariableModels", default_in_vars),
        "outVariableModels": node_config.get("outVariableModels", []),
        "configure": {},
        "childNode": None,
        "addable": True,
        "deletable": False,
        "error": False,
        "content": f"执行流程:{process_name}",
        "pid": parent_id or "",
        "errorContent": "",
    }


def build_service_node(node_config, form_config, level, parent_id=None):
    """
    构建服务任务节点（service → Java 类调用）。

    参数:
      expressionType   "class"（默认）或 "delegateExpression"
      expressionValue  Java 类全路径（如 "org.jeecg.modules.testListenerExpression.TestService"）
                       或 Spring 表达式（如 "${myServiceDelegate}"）
      resultVariable   输出变量名（可选）
      description      节点描述（可选）

    示例:
      {
          "type": "service",
          "name": "服务节点",
          "attr": {
              "expressionType": "class",
              "expressionValue": "org.jeecg.modules.testListenerExpression.TestService",
              "description": "执行业务逻辑"
          }
      }
    """
    node_id = node_config.get("id", gen_id("task"))
    user_attr = node_config.get("attr", {})

    expression_type = user_attr.get("expressionType",
                                    node_config.get("expressionType", "class"))
    expression_value = user_attr.get("expressionValue",
                                     node_config.get("expressionValue", ""))
    result_variable = user_attr.get("resultVariable",
                                    node_config.get("resultVariable", ""))
    description = user_attr.get("description",
                                node_config.get("description", ""))

    attr = {
        "expressionType": expression_type,
        "expressionValue": expression_value,
        "level": str(level),
    }
    if result_variable:
        attr["resultVariable"] = result_variable
    if description:
        attr["description"] = description
    attr.update({k: v for k, v in user_attr.items() if k not in attr})

    return {
        "id": node_id,
        "name": node_config.get("name", "服务节点"),
        "type": "service",
        "status": -1,
        "attr": attr,
        "configure": {},
        "childNode": None,
        "addable": True,
        "deletable": False,
        "error": False,
        "content": expression_value,
        "pid": parent_id or "",
        "errorContent": "",
    }


def build_script_node(node_config, form_config, level, parent_id=None):
    """
    构建脚本节点（script → JavaScript / Groovy）。

    参数:
      scriptFormat    脚本语言："javascript"（默认）或 "groovy"
      scriptContent   脚本内容（支持多行）
                      可通过 execution.setVariable("varName", value) 设置流程变量
      autoStoreVariables  是否自动存储变量（默认 False）
      description     节点描述（可选）

    示例:
      {
          "type": "script",
          "name": "脚本节点",
          "attr": {
              "scriptFormat": "javascript",
              "scriptContent": "var sum = 2 + 9;\\nexecution.setVariable('myVar', sum);",
              "description": "计算并设置变量"
          }
      }
    """
    node_id = node_config.get("id", gen_id("task"))
    user_attr = node_config.get("attr", {})

    script_format = user_attr.get("scriptFormat",
                                  node_config.get("scriptFormat", "javascript"))
    script_content = user_attr.get("scriptContent",
                                   node_config.get("scriptContent", ""))
    auto_store = user_attr.get("autoStoreVariables",
                               node_config.get("autoStoreVariables", False))
    description = user_attr.get("description",
                                node_config.get("description", ""))

    attr = {
        "scriptFormat": script_format,
        "scriptContent": script_content,
        "autoStoreVariables": auto_store,
        "level": str(level),
    }
    if description:
        attr["description"] = description
    attr.update({k: v for k, v in user_attr.items() if k not in attr})

    # content 显示脚本前 40 字符
    content_preview = script_content[:40] + "..." if len(script_content) > 40 else script_content

    return {
        "id": node_id,
        "name": node_config.get("name", "脚本节点"),
        "type": "script",
        "status": -1,
        "attr": attr,
        "configure": {},
        "childNode": None,
        "addable": True,
        "deletable": False,
        "error": False,
        "content": content_preview,
        "pid": parent_id or "",
        "errorContent": "",
    }


def build_node(node_config, form_config, level, parent_id=None):
    """根据 type 构建对应节点"""
    node_type = node_config.get("type", "approver")
    if node_type == "approver":
        return build_approver_node(node_config, form_config, level, parent_id)
    elif node_type == "edit":
        return build_edit_node(node_config, form_config, level, parent_id)
    elif node_type == "data_update":
        return build_data_update_node(node_config, form_config, level, parent_id)
    elif node_type == "exclusive":
        return build_exclusive_gateway(node_config, form_config, level, parent_id)
    elif node_type == "parallel":
        return build_parallel_gateway(node_config, form_config, level, parent_id)
    elif node_type == "inclusive":
        return build_inclusive_gateway(node_config, form_config, level, parent_id)
    elif node_type == "time":
        return build_time_node(node_config, form_config, level, parent_id)
    elif node_type == "notice":
        return build_notice_node(node_config, form_config, level, parent_id)
    elif node_type == "data_add":
        return build_data_add_node(node_config, form_config, level, parent_id)
    elif node_type == "data_delete":
        return build_data_delete_node(node_config, form_config, level, parent_id)
    elif node_type == "upvariable":
        return build_upvariable_node(node_config, form_config, level, parent_id)
    elif node_type == "get_one":
        return build_get_one_node(node_config, form_config, level, parent_id)
    elif node_type == "get_more":
        return build_get_more_node(node_config, form_config, level, parent_id)
    elif node_type == "get_one_sysinfo":
        return build_get_one_sysinfo_node(node_config, form_config, level, parent_id)
    elif node_type == "get_more_sysinfo":
        return build_get_more_sysinfo_node(node_config, form_config, level, parent_id)
    elif node_type in ("opinion", "suggest"):
        return build_opinion_gateway(node_config, form_config, level, parent_id)
    elif node_type == "data_branch":
        return build_data_branch_gateway(node_config, form_config, level, parent_id)
    elif node_type == "operation":
        return build_operation_node(node_config, form_config, level, parent_id)
    elif node_type in ("subprocess", "callActivity"):
        return build_subprocess_node(node_config, form_config, level, parent_id)
    elif node_type == "service":
        return build_service_node(node_config, form_config, level, parent_id)
    elif node_type == "script":
        return build_script_node(node_config, form_config, level, parent_id)
    else:
        raise ValueError(
            f"不支持的节点类型: {node_type}，支持: "
            f"approver / edit / "
            f"data_update / data_add / data_delete / upvariable / "
            f"get_one / get_more / get_one_sysinfo / get_more_sysinfo / "
            f"exclusive / parallel / inclusive / opinion / data_branch / "
            f"operation / subprocess / time / notice / "
            f"service / script"
        )


def _get_convergence_child(node):
    """返回节点的聚合子节点（polymerize 或 inclusive_end），若不存在返回 None"""
    if not isinstance(node, dict):
        return None
    child = node.get("childNode")
    if child and child.get("type") in ("polymerize", "inclusive_end"):
        return child
    return None


def _level_of(node, node_id):
    """在已建好的节点树里按 id 找某个节点的 attr.level。"""
    if not isinstance(node, dict) or not node_id:
        return None
    if node.get("id") == node_id:
        return (node.get("attr") or {}).get("level")
    for cn in (node.get("conditionNodes") or []):
        got = _level_of(cn.get("childNode"), node_id)
        if got:
            return got
    return _level_of(node.get("childNode"), node_id)


def build_node_chain(nodes, form_config, start_level=1, parent_id=None):
    """将节点列表构建为链式结构（通过 childNode 连接）"""
    if not nodes:
        return None

    root = None
    current = None

    for i, node_config in enumerate(nodes):
        node_type = node_config.get("type", "")

        # data_branch 必须紧跟在 emptyAction=3 的 get_one 节点之后
        if node_type == "data_branch":
            if i == 0:
                raise ValueError(
                    "data_branch 必须紧跟在 get_one 节点之后，不能作为第一个节点"
                )
            prev = nodes[i - 1]
            if prev.get("type") != "get_one":
                raise ValueError(
                    f"data_branch 前置节点必须是 get_one，当前前置节点类型为: {prev.get('type')}"
                )
            if prev.get("emptyAction", prev.get("noDataType", 0)) != 3:
                raise ValueError(
                    "data_branch 前置 get_one 的 emptyAction 必须设为 3（中止流程，或继续执行查找结果分支；2=新增记录后继续，勿混用）"
                )

        level = start_level + i
        # pid 跟踪：若前一个节点有聚合子节点（polymerize/inclusive_end），pid 指向聚合节点
        if i == 0:
            pid = parent_id
        else:
            conv = _get_convergence_child(current)
            pid = conv["id"] if conv else (current.get("id") if current else None)
        node = build_node(node_config, form_config, level, pid)

        if root is None:
            root = node
            current = node
        else:
            # 若前一个节点有聚合子节点，将新节点接在聚合子节点之后
            conv = _get_convergence_child(current)
            if conv is not None:
                conv["childNode"] = node
            else:
                current["childNode"] = node
            current = node

    return root


def build_process_json(config):
    """
    根据简化配置构建完整的 processJson。

    config 必填字段:
      processName      流程名称
      processKey       流程Key（如 process1775632585486）
      lowAppId         低代码应用ID
      startType        触发方式（见下）
      nodes            节点列表

    startType 枚举:
      "tableEvent"   工作表事件触发（新增/更新/删除记录）
      "buttonEvent"  按钮触发（Desform 自定义按钮）
      "manual"       手动发起
      "timerEvent"   定时触发 / 按日期字段触发
      "userEvent"    人员事件触发（入职/离职）

    tableEvent / buttonEvent 额外必填:
      formTableCode    表单编码
      formTableName    表单名称
      formTableId      表单ID（格式: form_start_<formTableCode>）
      titleField       标题字段ID
      startEventType   触发事件类型（默认 "add|update"）

    通用可选字段:
      createStartNode  是否启用「发起人节点」（默认 False=不启用）。
                       仅当用户明确要求发起人节点/发起人填写时才传 True；
                       不要因为「新增触发」就自动置 True（旧规则已作废）。

    timerEvent 额外字段（在 config 顶层或 config["attr"] 中）:
      beginDateStr     开始执行时间（首次触发时间，如 "2024-05-01 08:30:00"）
      endDateStr       结束执行时间（可选）
      timeCycleName    循环周期名称（"每天"/"每小时"/"每分钟"/"自定义" 等）
      dayValue         每月第几天（月循环）
      hourType         小时触发类型（1=固定值 2=范围）
      hourValues       固定执行小时列表（如 [8, 18]）
      dayValues        固定执行日期列表（范围触发，如 [10, 11, 12]）
      triggerField     日期字段触发时的字段ID（设置此值 = 按日期字段触发）
      plusDate         日期偏移量（正=之后 负=之前）
      plusDateUnit     偏移单位（1=分钟 2=小时 3=天）
      executionTime    日期型字段执行时刻（如 "09:00"）
      startCondition   筛选条件列表

    userEvent 额外字段:
      userEventType    事件类型（1=入职 2=离职）
      startCondition   筛选条件列表
    """
    start_type = config.get("startType", "manual")
    form_table_code = config.get("formTableCode", "")
    form_table_name = config.get("formTableName", "")
    form_table_id = config.get("formTableId", f"form_start_{form_table_code}")
    title_field = config.get("titleField", "")
    start_event_type = config.get("startEventType", "add|update")

    form_config = {
        "formTableCode": form_table_code,
        "formTableName": form_table_name,
        "formTableId": form_table_id,
    }

    start_task_id = config.get("startTaskId", gen_id("task"))

    # 构建节点链
    child_node = build_node_chain(config.get("nodes", []), form_config, start_level=1, parent_id="start")

    # 回填 subFormTableObject.level = **数据对象那个节点自己的 level**。
    # 线上 25 条 callActivity 的 subFormTableObject 都带 level（等于它引用的 getMore 节点的
    # attr.level），而 level 是 build_node_chain 按位置算的 —— 建 callActivity 时还不知道，
    # 只能在整条链建完之后回来补。（2026-09-17：漏了它，设计器「选择数据对象」一栏对不上。）
    def _backfill_sub_obj_level(node):
        if node is None:
            return
        if node.get("type") == "callActivity":
            a = node.get("attr") or {}
            obj = a.get("subFormTableObject")
            if isinstance(obj, dict) and not obj.get("level"):
                src = a.get("formTableSourceTaskId")
                lv = _level_of(child_node, src)
                if lv:
                    obj["level"] = lv
        for cn in (node.get("conditionNodes") or []):
            _backfill_sub_obj_level(cn.get("childNode"))
        _backfill_sub_obj_level(node.get("childNode"))

    _backfill_sub_obj_level(child_node)

    # 从已构建的节点链中收集额外的表引用（data_add / data_get_one / data_get_more / function 等）
    def _collect_extra_tables(node, result):
        if node is None:
            return
        ntype = node.get("type", "")
        attr = node.get("attr", {})
        nid = node.get("id", "")
        nname = node.get("name", "")

        if ntype == "data_add":
            ftc = attr.get("formTableCode", "")
            add_type = attr.get("addDataType", 1)
            entry = {
                "formTableId": attr.get("formTableId", f"form_{nid}_{ftc}"),
                "nodeId": nid,
                "nodeName": nname,
                "nodeType": "plus",
                "formTableCode": ftc,
                "formTableName": attr.get("formTableName", ""),
                "formTableMainCode": ftc,
                "addDataType": add_type,
                "level": attr.get("level", "1"),
            }
            if add_type == 2:
                entry["formTableSourceGetDataType"] = attr.get("formTableSourceGetDataType", 1)
            result.append(entry)

        elif ntype in ("data_get_one",):
            select_type = attr.get("selectType", 1)
            ftc = attr.get("formTableCode", "")
            if select_type == 3:
                # 从关联字段获取单条：formTableCode 用子表，formTableMainCode 用主表
                link_code = attr.get("linkFormTableCode", "")
                link_name = attr.get("linkFormTableName", "")
                result.append({
                    "formTableId": f"form_{nid}_{link_code}",
                    "nodeId": nid,
                    "nodeName": nname,
                    "nodeType": "search",
                    "formTableCode": link_code,
                    "formTableName": link_name,
                    "formTableMainCode": ftc,
                    "formTableType": attr.get("linkFormTableType", 1),
                    "selectType": select_type,
                    "level": attr.get("level", "1"),
                })
            else:
                entry = {
                    "formTableId": attr.get("formTableId", f"form_{nid}_{ftc}"),
                    "nodeId": nid,
                    "nodeName": nname,
                    "nodeType": "search",
                    "formTableCode": ftc,
                    "formTableName": attr.get("formTableName", ""),
                    "formTableMainCode": ftc,
                    "selectType": select_type,
                    "level": attr.get("level", "1"),
                }
                # selectType=2（从多条节点取单条）需要 formTableSourceGetDataType
                if select_type == 2:
                    entry["formTableSourceGetDataType"] = attr.get("formTableSourceGetDataType", 1)
                else:
                    entry["formTableSourceGetDataType"] = None
                result.append(entry)

        elif ntype in ("data_get_more",):
            select_type = attr.get("selectType", 1)
            if select_type == 3:
                # 从关联字段获取多条：formTableCode 用子表，formTableMainCode 用主表
                # linkFormTableMainCode 可覆盖（链接表的父表与源表不同时使用）
                link_code = attr.get("linkFormTableCode", "")
                link_name = attr.get("linkFormTableName", "")
                main_code = attr.get("linkFormTableMainCode", attr.get("formTableCode", ""))
                result.append({
                    "formTableId": f"form_{nid}_{link_code}",
                    "nodeId": nid,
                    "nodeName": nname,
                    "nodeType": "getMore",
                    "formTableCode": link_code,
                    "formTableName": link_name,
                    "formTableMainCode": main_code,
                    "formTableType": attr.get("linkFormTableType", 1),
                    "selectType": select_type,
                    "getDataType": attr.get("getDataType", 1),
                    "level": attr.get("level", "1"),
                })
            else:
                # selectType 1/2/4：formTableId 始终用 form_{nodeId}_{formTableCode}
                ftc = attr.get("formTableCode", "")
                result.append({
                    "formTableId": f"form_{nid}_{ftc}",
                    "nodeId": nid,
                    "nodeName": nname,
                    "nodeType": "getMore",
                    "formTableCode": ftc,
                    "formTableName": attr.get("formTableName", ""),
                    "formTableMainCode": ftc,
                    "selectType": select_type,
                    "getDataType": attr.get("getDataType", 1),
                    "level": attr.get("level", "1"),
                })

        elif ntype == "function":
            fun_type = attr.get("funType", "number")
            func_code = f"function-{fun_type}"
            result.append({
                "formTableId": f"form_{nid}_{func_code}",
                "nodeId": nid,
                "nodeName": nname,
                "nodeType": "function",
                "formTableCode": func_code,
                "formTableName": nname,
                "operationMode": attr.get("operationMode", "cache"),
                "decimals": attr.get("decimals", 2),
                "level": attr.get("level", "1"),
            })

        elif ntype in ("data_get_udr_one", "data_get_udr_more"):
            # 节点上的 formTableList 已包含完整的 getUserDeptRole 条目，直接收集
            result.extend(node.get("formTableList", []))

        for cn in node.get("conditionNodes", []):
            _collect_extra_tables(cn.get("childNode"), result)
        _collect_extra_tables(node.get("childNode"), result)

    _extra_tables = []
    _collect_extra_tables(child_node, _extra_tables)

    # start 节点名称
    _start_node_name_map = {
        "tableEvent": "工作表事件触发",
        "buttonEvent": "按钮触发",
        "timerEvent": "定时触发",
        "dateFieldEvent": "按日期字段触发",
        "userEvent": "人员事件触发",
        "subEvent": "子流程触发",
        "manual": "发起人",
    }
    start_node_name = _start_node_name_map.get(start_type, "发起人")

    # 发起人节点开关：默认 False（不启用）。仅用户明确要求「发起人节点/发起人填写」时才传 True。
    # 旧版由 create-flow.md 手动 patch 成 True（add 触发），2026-09-11 用户裁定默认关闭。
    _csn = config.get("createStartNode", False)
    _create_start_node = _csn is True or str(_csn).strip().lower() in ("true", "1", "yes")

    # subEvent：从 config 中取 subFormTableObject（callActivity 的 getMore 节点引用）
    _sub_form_obj = config.get("subFormTableObject") or {}
    if start_type == "subEvent" and _sub_form_obj:
        # subEvent 的 formTableCode/Name/Id 从 subFormTableObject 中取
        form_table_code = _sub_form_obj.get("formTableCode", form_table_code)
        form_table_name = _sub_form_obj.get("formTableName", form_table_name)
        form_table_id   = _sub_form_obj.get("formTableId",   form_table_id)

    # formTableList
    _table_node_types = ("tableEvent", "buttonEvent", "timerEvent", "dateFieldEvent")
    if start_type == "userEvent":
        # 人员触发：固定 sys_user 表，nodeType 为 "userEvent"
        form_table_list = [
            {
                "formTableId": "form_start_sys_user",
                "nodeId": "start",
                "nodeName": start_node_name,
                "nodeType": "userEvent",
                "formTableCode": "sys_user",
                "formTableName": start_node_name,
            }
        ]
    elif start_type == "subEvent":
        # 子流程触发：formTableList 首条为 subFormTableObject（带 isSubStart:true）
        form_table_list = [_sub_form_obj] if _sub_form_obj else []
        form_table_list.append({
            "formTableId": "variable",
            "nodeId": "processVariable",
            "formTableCode": "_variable_",
            "nodeName": "流程参数",
            "formTableName": "流程参数",
            "nodeType": "variable",
        })
    else:
        # start 条目仅在存在真实工作表时登记：定时/按日期字段/手动等无工作表触发若登记空表条目，
        # 设计器「变量选择器」会出现可选中但无字段的「定时触发 工作表:""」（2026-09-14 用户 UI 验收纠正）
        form_table_list = []
        if form_table_code:
            form_table_list.append({
                "formTableId": form_table_id,
                "nodeId": "start",
                "nodeName": start_node_name,
                "nodeType": "table",
                "formTableCode": form_table_code,
                "formTableName": form_table_name,
                "formTableMainCode": form_table_code,
                "selectType": 1,
                "level": 0,
            })
        form_table_list.append({
            "formTableId": "variable",
            "nodeId": "processVariable",
            "formTableCode": "_variable_",
            "nodeName": "流程参数",
            "formTableName": "流程参数",
            "nodeType": "variable",
        })
    form_table_list.extend(_extra_tables)

    # 从 config 或 config["attr"] 中取触发方式专属字段
    _extra = config.get("attr", {})

    # start 节点 attr
    _has_table = start_type in _table_node_types
    start_attr = {
        "formType": 2,
        "startType": start_type,
        "formTableId": form_table_id if _has_table else None,
        "formTableCode": form_table_code if (_has_table or start_type == "subEvent") else None,
        "formTableSourceId": None,
        "formTableName": form_table_name if (_has_table or start_type == "subEvent") else None,
        "subFormTableObject": _sub_form_obj if start_type == "subEvent" else None,
        "titleField": title_field,
        "endDate": None,
        # timerEvent 字段
        "beginDateStr": config.get("beginDateStr", _extra.get("beginDateStr", None)),
        "endDateStr": config.get("endDateStr", _extra.get("endDateStr", None)),
        "timeCycleName": config.get("timeCycleName", _extra.get("timeCycleName", None)),
        "dayValue": config.get("dayValue", _extra.get("dayValue", 1)),
        "hourType": config.get("hourType", _extra.get("hourType", 1)),
        "hourValues": config.get("hourValues", _extra.get("hourValues", [])),
        "dayValues": config.get("dayValues", _extra.get("dayValues", [])),
        # datefield 触发字段
        "triggerField": config.get("triggerField", _extra.get("triggerField", None)),
        "triggerFieldType": config.get("triggerFieldType", _extra.get("triggerFieldType", None)),
        "executeType": config.get("executeType", _extra.get("executeType", None)),
        "cycleType": config.get("cycleType", _extra.get("cycleType", None)),  # 0=不重复/1=每年/2=每月/3=每周
        "linkFormTableName": config.get("linkFormTableName", _extra.get("linkFormTableName", None)),
        "plusDate": config.get("plusDate", _extra.get("plusDate", None)),
        "plusDateUnit": config.get("plusDateUnit", _extra.get("plusDateUnit", 3)),
        "executionTime": config.get("executionTime", _extra.get("executionTime", None)),
        # userEvent 字段
        "userEventType": config.get("userEventType", _extra.get("userEventType", None)),
        # tableEvent 字段
        "startEventType": start_event_type if start_type in ("tableEvent", "buttonEvent") else None,
        # 通用
        "startCondition": config.get("startCondition", _extra.get("startCondition", [])),
        # 监控字段（update 触发时后端先比对新旧值，只有被监控字段变了才继续校验 startCondition）。
        # 空数组 = 任何一次修改都算；写错/漏写不会报错，只是流程会「多跑」。
        "conditionFields": config.get("conditionFields", _extra.get("conditionFields", [])) or [],
        "signalEventName": None,
        "inputParams": config.get("inputParams", []),
        "selectType": 1,
    }

    # timerEvent：计算 timeCycle（ISO 8601 或自定义 Quartz Cron）
    _time_cycle_name = config.get("timeCycleName", _extra.get("timeCycleName", ""))
    _cron_expr = config.get("cronExpr", _extra.get("cronExpr", ""))   # 自定义 Quartz Cron（timeCycleName="自定义"时填）
    if start_type == "timerEvent":
        if _time_cycle_name == "自定义" and _cron_expr:
            _top_time_cycle = _cron_expr    # Quartz Cron 格式，如 "0 0 8 * * ?"
        else:
            _iso = _TIMER_CYCLE_ISO_MAP.get(_time_cycle_name, "P1D")
            _begin = config.get("beginDateStr", _extra.get("beginDateStr", ""))
            # 格式化为 ISO 8601 datetime（去掉秒）
            _begin_iso = _begin.replace(" ", "T")[:16] if _begin else ""
            _top_time_cycle = f"R/{_begin_iso}/{_iso}" if _begin_iso else _iso

        # attr.timeCycle：字符串数字编码（"3"=每天）
        # ⚠️ 必须是字符串，整数编码前端下拉无法匹配，会显示原始数字
        _begin_str = config.get("beginDateStr", _extra.get("beginDateStr", ""))
        _end_str = config.get("endDateStr", _extra.get("endDateStr", ""))
        start_attr["timeCycle"] = _TIMER_CYCLE_CODE_MAP.get(_time_cycle_name, "custom")
        start_attr["beginDate"] = _begin_str          # 与 beginDateStr 相同，前端需要
        # endDate：ISO 格式（YYYY-MM-DDTHH:mm），前端结束时间框读此字段
        start_attr["endDate"] = _end_str.replace(" ", "T")[:16] if _end_str else None
        # endDateStr 统一保持原格式（服务端读此字段）
        if _end_str:
            start_attr["endDateStr"] = _end_str
        start_attr["timeCycleName"] = _time_cycle_name or None
        # 额外 UI 展示字段（参考已发布定时流程结构）
        start_attr.setdefault("hourValueMin", 0)
        start_attr.setdefault("hourValueMax", 23)
        start_attr.setdefault("dayValueMin", 1)
        start_attr.setdefault("dayValueMax", None)
        start_attr.setdefault("monthValueMin", 1)
        start_attr.setdefault("monthValueMax", None)
        start_attr.setdefault("monthValues", [])
        start_attr.setdefault("dayOrWeekType", 1)
        start_attr.setdefault("weekValue", [])
        start_attr.setdefault("monthType", 1)
        start_attr.setdefault("times", [])
    else:
        _top_time_cycle = "PT1H"

    _end_time = config.get("endDateStr", _extra.get("endDateStr", None))
    if _end_time:
        _end_time = _end_time.replace(" ", "T")[:16]   # 格式化为 ISO 8601，如 "2026-04-09T17:03"

    # 节点内容描述
    if start_type in ("tableEvent", "buttonEvent"):
        _content = f'工作表 "{form_table_name}"'
    elif start_type == "timerEvent":
        _content = _time_cycle_name or "定时触发"
    elif start_type == "userEvent":
        _evt = {1: "入职", 2: "离职"}.get(config.get("userEventType", _extra.get("userEventType", 1)), "入职")
        _content = f"人员{_evt}时触发"
    else:
        _content = ""

    process_json = {
        "id": "start",
        "startTaskId": start_task_id,
        "name": start_node_name,
        "type": "start",
        "createStartNode": _create_start_node,
        "initiator": "applyUserId",
        "status": -1,
        "error": False,
        "startNodeContent": None,
        "childNode": child_node,
        "addable": True,
        # subEvent 子流程：根节点存 "manual"，真实类型在 attr.startType 中
        "startType": "manual" if start_type == "subEvent" else start_type,
        "timeType": "timeDate",
        "timeDate": None,
        "timeCycle": _top_time_cycle,
        "entTime": _end_time,
        "messageEventName": None,
        "formTableList": form_table_list,
        "listenerData": [],
        "attr": start_attr,
        # 子流程用它声明「我要收哪些流程变量」（父流程的 callActivity 按名字传进来）；
        # 主流程没有变量，恒为空且 hasVariableList=True。
        "variableList": config.get("variableList", _extra.get("variableList", [])) or [],
        "hasVariableList": config.get("hasVariableList", start_type != "subEvent"),
        "hasInputParams": False,
        "executeListeners": DEFAULT_EXECUTE_LISTENERS,
        "taskListenerData": DEFAULT_TASK_LISTENER_DATA,
        "eventListeners": DEFAULT_EVENT_LISTENERS,
        "content": _content,
        "errorContent": "",
    }

    # 自动兜底：填写人=表单字段的节点补 variableTitle（面板「指定填写对象」读它，缺则显示为空）
    fix_variable_titles(process_json)

    return process_json


# ====== API 调用 ======

def api_request(api_base, token, path, form_data=None, method='POST', extra_headers=None):
    """发送表单格式 HTTP 请求（application/x-www-form-urlencoded）"""
    url = f'{api_base}{path}'
    headers = {'X-Access-Token': token}
    if extra_headers:
        headers.update(extra_headers)

    if form_data is not None:
        encoded = urllib.parse.urlencode(form_data, quote_via=urllib.parse.quote).encode('utf-8')
        headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
        req = urllib.request.Request(url, data=encoded, headers=headers, method=method)
    else:
        req = urllib.request.Request(url, headers=headers, method=method)

    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        raise RuntimeError(f'HTTP {e.code}: {body}')


def api_json_request(api_base, token, path, data=None, method='POST', extra_headers=None):
    """发送 JSON 格式 HTTP 请求（application/json）"""
    url = f'{api_base}{path}'
    headers = {
        'X-Access-Token': token,
        'Content-Type': 'application/json; charset=UTF-8',
    }
    if extra_headers:
        headers.update(extra_headers)

    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
    else:
        req = urllib.request.Request(url, headers=headers, method=method)

    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        raise RuntimeError(f'HTTP {e.code}: {body}')


def deploy_flow(api_base, token, flow_id, tenant_id=None, low_app_id=None):
    """
    发布简流。

    参数:
      api_base     JeecgBoot 后端地址
      token        X-Access-Token
      flow_id      简流 ID（save_flow 返回的 result.id）
      tenant_id    租户 ID；省略时自动从 getUserInfo 解析
      low_app_id   低代码应用 ID；省略时尝试 listProcess 按 id 扫描解析

    返回:
      API 响应字典，成功时 success=True，message="发布成功!"

    实测（2026-09-03，gotchas #33a）:
      deployProcess 必须同时带 X-Tenant-Id + X-Low-App-ID，否则 subEvent 子流程是"假发布"
      （回"发布成功"但 /act/process/list 的 version 不递增，定义缺子流程启动数据注入，
      运行时报 _id:"" 查无数据）；只带租户头不带应用头会 500"未找到对应实体"。
      补全两头后 subEvent 记录直接注册出完整可用定义，无需再走临时改 manual 的两段式。
      主流程(表/按钮触发)无头也能注册，但统一补头更稳。
      注：listProcess/queryById 不带 X-Low-App-ID 时默认落到租户的"当前应用"，
      扫描可能找不到目标流程 → 自动退回无头发布并告警；subEvent 场景请显式传 low_app_id。
    """
    extra = {}
    if tenant_id in (None, ''):
        tenant_id = _resolve_tenant_id(api_base, token, '')
    if tenant_id:
        extra['X-Tenant-Id'] = str(tenant_id)
    if low_app_id in (None, ''):
        # 兜底: listProcess 按 id 扫描取 lowAppId（受"当前应用"限制，非必然命中）
        try:
            headers = {'X-Access-Token': token}
            if extra.get('X-Tenant-Id'):
                headers['X-Tenant-Id'] = extra['X-Tenant-Id']
            for page in range(1, 6):
                params = urllib.parse.urlencode({
                    'processDesginType': 'mini', 'pageNo': page, 'pageSize': 50,
                    'column': 'createTime', 'order': 'desc',
                })
                url = f'{api_base}/act/process/extActProcess/listProcess?{params}'
                req = urllib.request.Request(url, headers=headers)
                resp = urllib.request.urlopen(req)
                data = json.loads(resp.read().decode('utf-8'))
                records = (data.get('result') or {}).get('records') or []
                for rec in records:
                    if str(rec.get('id')) == str(flow_id):
                        if not low_app_id and rec.get('lowAppId'):
                            low_app_id = rec['lowAppId']
                        if not extra.get('X-Tenant-Id') and rec.get('tenantId'):
                            extra['X-Tenant-Id'] = str(rec['tenantId'])
                        break
                if low_app_id:
                    break
                total = (data.get('result') or {}).get('total', 0)
                if page * 50 >= total:
                    break
        except Exception as e:
            print(f'[deploy_flow] 扫描流程记录失败(将不带租户头发布): {e}')
    if low_app_id:
        extra['X-Low-App-ID'] = str(low_app_id)
    # 头必须成对：只带租户头不带应用头会 500；缺任一头则退回无头旧行为（主流程可用，subEvent 假发布）
    if 'X-Tenant-Id' in extra and 'X-Low-App-ID' not in extra:
        print('[deploy_flow] 警告: 仅解析到 X-Tenant-Id 未解析到 X-Low-App-ID，退回无头发布；'
              'subEvent 子流程请显式传 low_app_id(见 gotchas #33a)')
        extra = {}
    if not extra:
        print('[deploy_flow] 警告: 未带 X-Tenant-Id/X-Low-App-ID 发布，subEvent 子流程可能假发布(见 gotchas #33a)')
    return api_json_request(api_base, token, '/act/process/extActProcess/deployProcess',
                            data={'id': flow_id}, method='PUT', extra_headers=extra or None)


def _parse_process_json(rec):
    """将记录中的 processJson 字符串解析为 dict（已是 dict 则原样返回）。"""
    if rec is None:
        return rec
    pj = rec.get('processJson', '')
    if isinstance(pj, str) and pj:
        rec['processJson'] = json.loads(pj)
    return rec


def _resolve_tenant_id(api_base, token, tenant_id=''):
    """优先用传入值；否则从 getUserInfo.loginTenantId 取。listProcess 不带租户会返回 0 条。"""
    if tenant_id not in (None, ''):
        return str(tenant_id)
    try:
        info = api_request(api_base, token, '/sys/user/getUserInfo', method='GET')
        result = info.get('result') or {}
        user_info = result.get('userInfo') or {}
        tid = user_info.get('loginTenantId')
        if tid in (None, ''):
            tid = result.get('loginTenantId', '')
        return str(tid) if tid not in (None, '') else ''
    except Exception:
        return ''


def query_flow(api_base, token, process_key=None, process_name=None, flow_id=None,
               tenant_id=None, low_app_id=None):
    """
    查询已有简流信息。用户给名称/ID/Key 任一即可。

    参数:
      api_base      JeecgBoot 后端地址
      token         X-Access-Token
      process_key   流程 Key（如 process1775648210785），可位置参数
      process_name  流程名称（如 订单新增-客户自动建档），精确匹配
      flow_id       数据库 ID，有则走 queryById（最快）
      tenant_id     租户 ID；省略时自动 getUserInfo
      low_app_id    低代码应用 ID；**按名字查时务必传**，见下

    返回:
      流程记录字典，包含 id、processKey、processName、processJson（已解析为 dict）、
      updateCount、lowAppId、startType 等字段；未找到时返回 None

    实测说明:
      listProcess 必须带 X-Tenant-Id，否则多租户环境返回 0 条。
      分页每次取 50 条，最多翻 50 页。

    ⚠️ **2026-09-17 补 `low_app_id`：按名字查时一定要传，否则会跨租户命中。**
      `listProcess` **不按 X-Tenant-Id 过滤**。同一条敲敲云上多个租户若建过同名应用，
      不传 `lowAppId` 就会逐页扫到**别的租户的同名流程**并当命中返回。
      实测（租户 1013 新建「进销存」，而 1009~1012 早先建过同名应用）：
        · `build_flows` 的 orphan 兜底检测按名字轮询 63 次，每次最多翻 50 页 × 50 条
          —— **白烧 20 分钟**，还把其中 61 条判成「已存在」→ 全 `OK:skip`
          → 本应用最终 **0 条流程**（接口全绿、结果全空）。
      传 `lowAppId` 后服务端直接过滤（1 页返回），既准又快。
    """
    tenant_id = _resolve_tenant_id(api_base, token, tenant_id)
    headers = {'X-Access-Token': token}
    if tenant_id:
        headers['X-Tenant-Id'] = tenant_id

    if flow_id:
        url = f'{api_base}/act/process/extActProcess/queryById?id={urllib.parse.quote(str(flow_id))}'
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read().decode('utf-8'))
        rec = data.get('result')
        return _parse_process_json(rec) if rec else None

    page = 1
    page_size = 50
    while page <= 50:
        query = {
            'processDesginType': 'mini',
            'pageNo': page,
            'pageSize': page_size,
            'column': 'createTime',
            'order': 'desc',
        }
        if low_app_id not in (None, ''):
            query['lowAppId'] = str(low_app_id)
        params = urllib.parse.urlencode(query)
        url = f'{api_base}/act/process/extActProcess/listProcess?{params}'
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read().decode('utf-8'))
        records = data.get('result', {}).get('records', [])
        for rec in records:
            if process_key and rec.get('processKey') == process_key:
                return _parse_process_json(rec)
            if process_name and rec.get('processName') == process_name:
                return _parse_process_json(rec)
        total = data.get('result', {}).get('total', 0)
        if page * page_size >= total:
            break
        page += 1
    return None


def save_flow(api_base, token, config, process_json, flow_id='', update_count=None):
    """
    调用简流保存 API（创建或修改）。

    参数:
      api_base      JeecgBoot 后端地址（如 http://localhost:8080/jeecgboot）
      token         X-Access-Token
      config        简流配置字典
      process_json  build_process_json() 生成的 processJson 字典（或已有流程的 processJson dict）
      flow_id       流程ID：留空=新建，填入已有 ID=修改
      update_count  版本号（修改时必须传入流程当前的 updateCount，否则报"不是最新版本"）
                    新建时留空（默认传 '1'）；修改时从 query_flow() 返回的记录中取

    返回:
      API 响应字典，成功时 result.id 为流程ID，result.updateCount 为累计修改次数

    重要：修改现有流程时，update_count 必须与数据库中当前值一致，否则会报：
      "流程修改失败，不是最新版本，请重新进入设计页面！"
    """
    if update_count is None:
        update_count = '1'
    process_json_str = json.dumps(process_json, ensure_ascii=False)

    form_data = {
        'updateCount': str(update_count),
        'processJson': process_json_str,
        'processName': config.get('processName', ''),
        'processKey': config.get('processKey', ''),
        'processType': config.get('processType', 'oa'),
        'id': flow_id,               # 空=新建，填入=修改
        'customProcessId': config.get('customProcessId', ''),
        'lowAppId': config.get('lowAppId', ''),
        'startType': config.get('startType', 'manual'),
    }

    extra_headers = {'X-Miniflowexclusionfieldmode': 'true'}
    low_app_id = config.get('lowAppId', '')
    if low_app_id:
        extra_headers['X-Low-App-Id'] = low_app_id

    # 自动从 getUserInfo 获取当前登录用户的租户ID，config.tenantId 可覆盖
    tenant_id = _resolve_tenant_id(api_base, token, config.get('tenantId', ''))
    if tenant_id:
        extra_headers['X-Tenant-Id'] = tenant_id

    return api_request(api_base, token, '/act/designer/miniDesFlow/api/saveFlow', form_data,
                       extra_headers=extra_headers)


# ====== 结构探查（只读辅助，一步流脚本用） ======

def fetch_app_forms(api_base, token, tenant_id=''):
    """
    查询当前租户全部低代码应用及其工作表（紧凑两级结构）。

    用法（新建简流第一步，替代手写 GET /online/lowApp/miniflow/tenantAppFormList）:
      apps = fetch_app_forms(api_base, token, tenant_id)
      app  = next(a for a in apps if '销售' in a['name'])
      form = next(f for f in app['forms'] if '订单' in f['name'])  # -> form['code'] / form['titleField']

    返回:
      [{'id', 'name', 'forms': [{'code', 'name', 'id', 'titleField'}, ...]}, ...]
      两级结构一次给全；接口失败时打印警告并返回 []（不中断一步流脚本）
    """
    tid = _resolve_tenant_id(api_base, token, tenant_id)
    path = '/online/lowApp/miniflow/tenantAppFormList'
    if tid:
        path += '?tenantId=' + urllib.parse.quote(tid)
    try:
        resp = api_request(api_base, token, path, method='GET',
                           extra_headers={'X-Tenant-Id': tid} if tid else None)
    except RuntimeError as e:
        print(f'[warn] fetch_app_forms 失败: {e}', file=sys.stderr)
        return []
    out = []
    for app in (resp.get('result') or {}).get('apps') or []:
        forms = [{'code': f.get('code'), 'id': f.get('id'),
                  'name': f.get('name'), 'titleField': f.get('titleField')}
                 for f in app.get('desforms') or []]
        out.append({'id': app.get('id'), 'name': app.get('name'), 'forms': forms})
    return out


def fetch_form_fields(api_base, token, form_code, tenant_id=''):
    """
    查询工作表的字段清单（按中文名索引的紧凑字典），供节点条件/赋值定位 model。

    ⚠️ 中文名在响应的 fields[].name（不是 label）；model 是写进节点配置的稳定 ID，
       formTableCode / 字段 model 都不要手写死，从本函数解析（表单重建后 model 会变）。

    用法:
      fm = fetch_form_fields(api_base, token, 'customer_mgmt', tenant_id)
      fm['客户状态']  # -> {'model': 'radio_...', 'type': 'radio', 'options': ['潜在客户', '意向客户', '成交客户', '流失客户']}
      fm['客户名称']['model']

    返回:
      {'中文名': {'model', 'type', 'options'}, ...}
      options：select/radio/checkbox 为可选值列表；link-record 为 {'sourceCode', 'titleField'}；其余省略。
      接口失败时打印警告并返回 {}（不中断一步流脚本）
    """
    tid = _resolve_tenant_id(api_base, token, tenant_id)
    path = '/desform/api/fields/' + urllib.parse.quote(form_code) + '?group=true'
    try:
        resp = api_request(api_base, token, path, method='GET',
                           extra_headers={'X-Tenant-Id': tid} if tid else None)
    except RuntimeError as e:
        print(f'[warn] fetch_form_fields({form_code}) 失败: {e}', file=sys.stderr)
        return {}
    out = {}
    for f in (resp.get('result') or {}).get('fields') or []:
        name = f.get('name')
        if not name:
            continue
        ftype = f.get('type') or ''
        meta = {'model': f.get('model'), 'type': ftype}
        opts = f.get('options') or {}
        if ftype == 'link-record':
            meta['options'] = {'sourceCode': opts.get('sourceCode'),
                               'titleField': opts.get('titleField')}
        elif ftype in ('select', 'radio', 'checkbox') and opts.get('options'):
            meta['options'] = [o.get('value') for o in opts['options'] if o.get('value') is not None]
        out[name] = meta
    return out


# ====== 命令行入口 ======

def main():
    parser = argparse.ArgumentParser(description='JeecgBoot 简流创建/修改/发布工具')
    parser.add_argument('--api-base', required=True,
                        help='JeecgBoot 后端地址（如 http://localhost:8080/jeecgboot）')
    parser.add_argument('--token', required=True, help='X-Access-Token')
    parser.add_argument('--config', required=True, help='JSON 配置文件路径')
    parser.add_argument('--id', default='', help='流程ID（修改时提供，创建时留空）')
    parser.add_argument('--deploy', action='store_true', help='保存后自动发布流程')
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    is_update = bool(args.id)
    action = '修改' if is_update else '创建'

    print(f'开始{action}简流: {config.get("processName", "")}')
    print(f'  processKey: {config.get("processKey", "")}')
    print(f'  startType: {config.get("startType", "manual")}')
    if config.get("formTableCode"):
        print(f'  关联表单: {config.get("formTableName", "")} ({config.get("formTableCode", "")})')
    if is_update:
        print(f'  流程ID: {args.id}')

    process_json = build_process_json(config)

    result = save_flow(
        args.api_base, args.token, config, process_json,
        flow_id=args.id
    )

    if result.get('success'):
        res_data = result.get('result', {})
        flow_id = res_data.get('id', '')
        update_count = res_data.get('updateCount', '')
        print(f'\n✓ 简流{action}成功!')
        print(f'  流程ID: {flow_id}')
        print(f'  流程名称: {config.get("processName", "")}')
        print(f'  流程Key: {config.get("processKey", "")}')
        print(f'  updateCount: {update_count}')

        # 自动发布
        if args.deploy and flow_id:
            print(f'\n正在发布流程...')
            deploy_result = deploy_flow(args.api_base, args.token, flow_id)
            if deploy_result.get('success'):
                print(f'✓ 流程发布成功!')
            else:
                print(f'✗ 流程发布失败: {deploy_result.get("message", deploy_result)}')
                sys.exit(1)
    else:
        print(f'\n✗ 简流{action}失败: {result.get("message", result)}')
        sys.exit(1)


if __name__ == '__main__':
    main()
