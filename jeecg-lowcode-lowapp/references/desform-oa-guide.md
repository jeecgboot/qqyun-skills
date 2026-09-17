# OA 审批应用一键生成（表单 + 流程 + 授权）

当用户说"创建审批单"、"创建报销单"、"做一个OA表单带流程"、"面试申请"、"请假申请"等，使用本指南一次性完成 **表单设计 → 流程创建 → 流程发布 → 表单关联 → 角色授权**。

---

## OA 交互流程

### OA Step 0: 解析用户需求

从用户描述中提取：

| 信息 | 默认值 | 示例 |
|------|--------|------|
| 应用名称 | 用户指定 | "费用报销单" |
| 表单编码 | 英文命名，`oa_` 前缀 | `oa_expense_reimbursement` |
| 表单字段 | 从描述中解析 | 申请人、金额、附件等 |
| 流程节点 | 从描述中解析 | 提交→部门审批→财务审核→结束 |
| 审批人 | 从描述中解析 | 角色/指定人/表达式 |

### OA Step 1: 展示应用摘要并确认

**必须展示以下内容，等待用户确认后再执行：**

```
## OA 应用摘要

- 应用名称：费用报销单
- 表单编码：oa_expense_reimbursement
- 目标环境：http://localhost:8080/jeecgboot

### 表单字段

| 序号 | 字段名称 | 控件类型 | 必填 | 说明 |
|------|---------|---------|------|------|
| 1 | 申请人 | select-user | 是 | 标题字段 |
| 2 | 报销金额 | money | 是 | |
| ... | ... | ... | ... | ... |

### 流程节点

| 序号 | 节点名称 | 类型 | 审批人 |
|------|---------|------|--------|
| 1 | 开始 | startEvent | - |
| 2 | 提交申请 | userTask (草稿) | ${applyUserId} |
| ... | ... | ... | ... |

### 连线

开始 → 提交 → 审批 → 结束

确认以上信息正确？(y/n)
```

### OA Step 2: 一键执行创建

用户确认后，使用 `scripts/desform_oa.py` 脚本一次性完成全部操作。

**使用步骤：**
1. 根据用户需求生成 JSON 配置文件（Write 到工作目录的临时 `.json` 文件）
2. 用 Bash 执行脚本：
```bash
python "<skill目录>/scripts/desform_oa.py" \
    --api-base <后端地址> \
    --token <TOKEN> \
    --config <config.json>
```
3. 删除临时 JSON 配置文件

**脚本自动完成：**
1. 创建设计器表单（调用 desform_creator）
2. 创建 BPMN 流程（调用 bpmn_creator）
3. 发布流程
4. 关联表单到流程
5. 设置草稿节点表单可编辑 + 表单地址
6. 查询已有授权 → 追加新表单ID → 保存授权给管理员角色

---

## OA JSON 配置格式

```json
{
  "appName": "费用报销单",
  "form": {
    "formName": "费用报销单",
    "formCode": "oa_expense_reimbursement",
    "layout": "word",
    "titleIndex": 2,
    "fields": [
      {"name": "报销单号", "type": "auto-number", "prefix": "BXBX"},
      {"name": "---", "type": "divider", "text": "基本信息"},
      {"name": "申请人", "type": "select-user", "required": true},
      {"name": "所在部门", "type": "select-depart", "required": true},
      {"name": "申请日期", "type": "date", "required": true},
      {"name": "报销类别", "type": "select", "required": true, "options": ["差旅费", "交通费", "办公用品"]},
      {"name": "---", "type": "divider", "text": "费用明细"},
      {"name": "报销金额", "type": "money", "required": true, "unit": "元"},
      {"name": "费用说明", "type": "textarea"},
      {"name": "发票/凭证", "type": "imgupload", "required": true},
      {"name": "附件", "type": "file-upload"},
      {"name": "---", "type": "divider", "text": "审批信息"},
      {"name": "部门负责人意见", "type": "oa-approval-comments"},
      {"name": "财务审核意见", "type": "oa-approval-comments"}
    ]
  },
  "process": {
    "processName": "费用报销审批流程",
    "processKey": "oa_expense_reimbursement_process",
    "typeId": "oa",
    "nodes": [
      {"id": "start", "type": "startEvent", "name": "开始"},
      {"id": "task_draft", "type": "userTask", "name": "提交报销申请", "draft": true,
       "assignee": {"type": "expression", "value": "applyUserId"}},
      {"id": "task_dept", "type": "userTask", "name": "部门负责人审批",
       "assignee": {"type": "role", "value": "manager"}},
      {"id": "task_finance", "type": "userTask", "name": "财务审核",
       "assignee": {"type": "role", "value": "finance"}},
      {"id": "end", "type": "endEvent", "name": "结束"}
    ],
    "flows": [
      {"id": "flow_1", "source": "start", "target": "task_draft"},
      {"id": "flow_2", "source": "task_draft", "target": "task_dept"},
      {"id": "flow_approve", "source": "task_dept", "target": "task_finance", "name": "通过"},
      {"id": "flow_reject", "source": "task_dept", "target": "end", "name": "拒绝"},
      {"id": "flow_end", "source": "task_finance", "target": "end"}
    ]
  },
  "auth": {
    "roleId": "f6817f48af4fb3af11b9e8bf182f618b",
    "authMode": "role"
  }
}
```

---

## OA 表单字段类型

支持所有 desform 标准控件类型，额外增加 OA 专用类型：

| type | 说明 |
|------|------|
| `oa-approval-comments` | 审批意见组件（grid 6:18布局，禁用状态，由流程节点控制启用） |

> **审批意见组件规则：** 当字段名包含"意见"、"签字"、"审批"等关键词（如"部门负责人意见"、"财务审核签字"），**必须**使用 `oa-approval-comments` 类型，**不要**使用 `hand-sign` 或 `textarea`。

---

## OA 审批人（assignee）类型

| type 值 | value 含义 | 示例 |
|---------|-----------|------|
| `assignee` | 固定用户名 | `"admin"` |
| `expression` | 表达式变量名 | `"applyUserId"` |
| `candidateUsers` | 多候选人 | `"admin,jeecg"` |
| `role` | 角色编码 | `"manager"` |
| `dept` | 部门ID | `"6d35e179..."` |
| `approvalRole` | 审批角色编码 | `"finance_approver"` |

---

## OA 流程分支规则

> **重要：** 生成流程 JSON 配置时，必须根据表单字段决定分支方式：
> - **表单有 `result` 等可用于条件判断的字段** → 使用 `exclusiveGateway` + `conditions` 条件分支
> - **表单没有 `result` 字段** → 使用**手工分支**（从 userTask 直接引出多条无条件的 sequenceFlow）
>
> **手工分支使用前提：** 仅在通过/拒绝后还需要经过不同的后续处理节点时才使用。如果审批后只有结束节点，不需要手工分支，直接连到结束即可。

---

## 常见 OA 应用模板

#### 费用报销单
- 字段：报销单号、申请人、部门、日期、报销类别、金额、说明、发票、附件、部门负责人意见(审批意见)、财务审核意见(审批意见)
- 流程：提交 → 部门审批 →(手工分支: 通过/拒绝)→ 财务审核 → 结束

#### 请假申请单
- 字段：申请人、部门、日期、请假类型、开始/结束日期、天数、说明、附件、部门负责人意见(审批意见)
- 流程：提交 → 部门审批 → 结束（审批后只有结束节点，不需要手工分支）

#### 采购申请单
- 字段：申请人、部门、日期、采购物品、数量、预算金额、供应商、说明、附件、部门负责人意见(审批意见)、总经理意见(审批意见)
- 流程：提交 → 部门审批 →(手工分支: 通过/拒绝)→ 总经理审批 → 结束

#### 出差申请单（含 callActivity 子流程）
- 字段：申请人、部门、出差地点、开始/结束日期、天数、事由、预算、附件、部门负责人意见(审批意见)、总监审批意见(审批意见)
- 主流程：提交 → 部门审批 →(手工分支: 同意/不同意)→ 总监审批 → 借款子流程(callActivity) → 结束
- **注意：** 需先用 `jeecg-bpmn` 的 `bpmn_creator.py` 创建子流程，再创建主流程
