# 简流节点类型详细参考手册

本文档详细说明简流（MiniFlow）所有节点类型的配置参数，供 AI 生成 processJson 时参考。

---

## 一、审批节点（approver）

流程中涉及审批时使用，支持或签/会签、多种审批人来源、超时提醒、加签转审等。

### 1.1 完整配置结构

```python
{
    "type": "approver",
    "name": "经理审批",

    # ── 审批人组（必填）────────────────────────────────────
    # ⚠️ 简流不支持数字型 approverType（如 "1"直接上级/"2"部门负责人/"3"部门审批人 等），
    # 也没有"层级"(levelMode)概念。只使用下方字符串型值，levelMode 固定填 1 即可（无实际效果）。
    "approverGroups": [
        {
            # 审批人来源类型（只能使用以下字符串值）
            "approverType": "candidateUser",   # 指定用户（**单数**；表单字段类才用复数 candidateUsers）
            # ⚠️ 下面 approverIds 写**裸账号**（["admin"]），**不带 `user.` 前缀**——
            #    前缀是消息节点 toUserIds 的写法；带前缀时 save/deploy 全绿、实例照起，
            #    但**任务谁都收不到**（2026-09-16 实测，见 gotchas #90）
            # "approverType": "candidateDepts", # 指定部门
            # "approverType": "candidateGroups",# 指定角色
            # "approverType": "candidatePosts", # 指定岗位
            # 表单人员/部门字段：approverType="candidateUsers"（复数）+ assigneeType="assigneeByVariable"
            #   部门字段必须再加 isNeedTranslateToUserIds: true，否则部门不展开成用户 → 成员全收不到
            # ⚠️ 会签节点（approvalMode=3~7）不支持 myself/发起人自选/上一节点审批人，
            #    如需类似效果请改用 assigneeByExp（指定公式）

            # 赋值方式
            "assigneeType": "assigneeByName",  # 直接指定
            # "assigneeType": "assigneeByExp",   # 表达式
            # "assigneeType": "assigneeByVariable", # 表单字段

            # 按 approverType 填对应字段：
            "approverIds":   ["admin"],         # candidateUser/candidateUsers 时用，填用户 username
            "approverNames": ["管理员"],
            "deptIds":       [],                # candidateDepts 时用，填部门数据库 ID
            "deptNames":     [],
            "roleIds":       [],                # candidateGroups 时用，⚠️ 填角色 Code（如 "general_manager"），不是数据库 ID
            "roleNames":     [],                # ⚠️ 必须与 roleIds 一一对应填写，留空 [] 会导致审批人面板为空
            "postIds":       [],                # candidatePosts 时用，填职务数据库 ID
            "postNames":     [],
            "expressionsIds":   [],             # assigneeByExp 时用，如 ["${applyUserId}"]
            "expressionsNames": [],             # 对应显示名，如 ["获取发起人"]

            "levelMode": 1,                     # 固定填 1，简流无层级概念
            "approverId": "",
            "approverName": "",
            "variableTitle": [],   # ⚠️ assigneeByVariable（办理人=表单字段）时**必须写 [字段中文名]**，
                                   #    如 ["记录创建人"]/["部门负责人"]——**留空 = 设计器「指定填写对象」
                                   #    渲染成空的「+ 添加人员」**（卡片 content 写对了也没用，2026-09-16 实测返工）。
                                   #    取值即 variableContent[0].fieldLabel。
            # variableContent: assigneeByVariable 时使用，结构为数组：
            # [{"formTableCode":"xxx","formTableId":"form_start_xxx",
            #   "nodeId":"start","nodeType":"table",        # table=start节点, search=get_one节点
            #   "fieldName":"select_user_xxx","fieldType":"select-user",
            #   "fieldLabel":"直接上级"}]
            # select-depart 字段还需额外加："isNeedTranslateToUserIds": true
            "variableContent": "",   # assigneeByVariable 时改为数组，其余情况保持 ""
            "formTableType": ""      # "table"=start节点, "search"=get_one节点，其余情况 ""
        }
    ],

    # ── 审批方式（attr）────────────────────────────────────
    "attr": {
        # approvalMethod: 审批方式
        #   1 = 或签 或 会签（统一为 1，通过 approvalMode 区分具体类型）
        # ⚠️ 注意：会签节点 approvalMethod 也是 1，不是 2
        "approvalMethod": 1,

        # isSequential: 会签执行顺序（approvalMode=3~7 时有效）
        #   False = 并行会签：所有审批人同时收到任务，谁先处理均可
        #   True  = 串行会签：按顺序逐个审批，前一人完成后下一人才能审批
        "isSequential": False,

        # ratio: 按比例投票时的通过比例（0~1），approvalMode=6 时有效
        # 例：ratio=0.6 表示 60% 的审批人通过即可
        "ratio": 0.5,

        # assigneeIsEmpty: 审批人为空时
        #   0 = 不自动跳过（默认）
        #   1 = 自动跳过该节点
        "assigneeIsEmpty": 0,

        # skipApproval: 审批人与发起人为同一人时
        #   0 = 由发起人对自己审批（默认）
        #   1 = 自动跳过该节点
        #   2 = 转交给部门负责人审批
        #       （当前审批人必须有所属部门且部门设置了负责人）
        "skipApproval": 0,

        # ── 高级功能开关 ──────────────────────────────────
        "allowAddSign":          True,   # 允许加签（前加签/后加签）
        #   前加签：加签人审批后，原审批人再审批
        #   后加签：原审批人审批后，加签人再审批
        "allowCountersignAddUser": False, # 允许会签时动态加入审批人
        "transferStatus":        True,   # 允许转审（将任务转给其他人处理）
        "rejectStatus":          True,   # 允许驳回（可选择驳回到已审批的任意节点）
        "ccStatus":              True,   # 允许抄送（处理时可手动选择抄送人）
        "msgStatus":             False,  # 开启消息通知（任务到达时发系统/钉钉/企微/邮件）
        "selnextUserStatus":     True,   # 允许处理时选择下一步处理人
        "formEditStatus":        False,  # 审批时是否可编辑表单字段
        "hasResultBranch":       False,  # 是否启用意见分支（opinion）

        # ── 超时提醒配置（可选）──────────────────────────
        "nodeTimeout": None,             # ⚠️ 关键字段！超时小时数（数字，如 2 = 2小时，最小 0.5）
        "timeType": "timeDate",          # 超时类型（固定值）
        "timeDate": None,                # 与 nodeTimeout 保持相同值
        # 两个字段必须同时设置，缺 nodeTimeout 则超时不生效

        # ── 会签多人审批内部参数（固定，无需修改）─────────
        # collection：系统自动根据 approverGroups 生成，无需手动填写
        #   指定用户      → flowUtil.stringToList(assigneeUserIdList)
        #   按部门        → minFlowUtils.getDepartUsersLoop(deptId, execution)
        #   按角色        → minFlowUtils.getRoleUsers(roleCode)
        #   按职位        → minFlowUtils.getPositionUsers(positionId)
        "collection": "${flowUtil.stringToList(assigneeUserIdList)}",
        "elementVariable": "assigneeUserId",
        "loopCardinality": None,
        # completionCondition: 会签完成条件表达式
        # 生产实际值示例: "${nrOfCompletedInstances/nrOfInstances==1}" (全员通过)
        # completionCondition：approvalMode=7（自定义）时填自定义表达式；其他 approvalMode 由系统自动生成：
        #   approvalMode=3（全员通过）→ ${nrOfCompletedInstances/nrOfInstances==1}
        #   approvalMode=4（一人通过）→ ${nrOfCompletedInstances/nrOfInstances>0}
        #   approvalMode=5（半数通过）→ ${nrOfCompletedInstances/nrOfInstances>=0.5}
        #   approvalMode=6（按比例）  → ${nrOfCompletedInstances/nrOfInstances>=ratio}
        #   approvalMode=7（自定义）  → 填写自定义 Flowable EL 表达式
        "completionCondition": None,     # approvalMode=7 时填自定义完成条件表达式

        # ── 会签节点顺序标识 ──────────────────────────────────
        # level: 会签节点在流程中的序号（字符串），从 "1" 开始递增
        # 多个会签节点依次为 "1"、"2"、"3" ...
        # 单审批节点无需设置，仅 approvalMode=3~7 时有意义
        "level": "1",
    },

    # ── 字段权限（可选）──
    # "privileges": [
    #     {"field": "fieldId", "readable": True, "editable": False}
    # ],
    "privileges": [],
    "configure": {},
    "taskListenerData": [],
    "listenerData": [],
}
```

> ⚠️ **落库位置（2026-09-10 实证）：** 本节列在节点**顶层**的 `approvalMode` / `attr` 外的展示顺序键只是 DSL 写法；save 后**决策类键一律存储于 `attr` 内**——`attr.approvalMethod`、`attr.isSequential`、`attr.completionCondition`、`attr.level`、`attr.ratio`、`attr.expressionValue`。**回读断言查 `attr.*`；查节点顶层会得到 None 并误判"配置丢失"**（gotchas #81）。`approverGroups` 例外：**两处都写同值**——`attr.approverGroups`（界面面板处）+ 节点顶层同名副本；仅写一处会让另一处滞留旧值（2026-09-15 实证）。

### 1.2 常用场景示例

**或签（默认，任一人通过）：**
```python
{"type": "approver", "name": "经理审批", "approverGroups": [
    {"approverType": "candidateUser", "assigneeType": "assigneeByName",
     "approverIds": ["userId"], "approverNames": ["张三"]}
]}
```

**并行会签（所有人必须通过）：**
```python
{"type": "approver", "name": "多人会签", "approvalMode": 3, "attr": {
    "approvalMethod": 1, "isSequential": False,
    "completionCondition": "${nrOfCompletedInstances/nrOfInstances==1}"
}, "approverGroups": [
    {"approverType": "candidateUsers", "assigneeType": "assigneeByName",
     "approverIds": ["user1", "user2"], "approverNames": ["张三", "李四"]}
]}
```

**串行会签（按顺序逐个审批，所有人通过）：**
```python
{"type": "approver", "name": "串行会签", "approvalMode": 3, "attr": {
    "approvalMethod": 1, "isSequential": True,
    "completionCondition": "${nrOfCompletedInstances/nrOfInstances==1}"
}, ...}
```

**会签-一人通过（串行，任一人通过即完成）：**
```python
{"type": "approver", "name": "会签(通过只需一人)", "approvalMode": 4, "attr": {
    "approvalMethod": 1, "isSequential": True,
    "completionCondition": "${nrOfCompletedInstances/nrOfInstances>0}"
}, "approverGroups": [
    {"approverType": "candidateDepts", "assigneeType": "assigneeByName",
     "deptIds": ["deptId"], "deptNames": ["采购部"]}
]}
```

**会签-半数通过（并行，50% 以上通过即完成）：**
```python
{"type": "approver", "name": "会签(半数通过)", "approvalMode": 5, "attr": {
    "approvalMethod": 1, "isSequential": False,
    "completionCondition": "${nrOfCompletedInstances/nrOfInstances>=0.5}"
}, "approverGroups": [
    {"approverType": "candidateGroups", "assigneeType": "assigneeByName",
     "roleIds": ["admin"], "roleNames": ["管理员"]}
]}
```

**按比例投票（60% 通过即可）：**
```python
{"type": "approver", "name": "会签(按比例投票)", "approvalMode": 6, "attr": {
    "approvalMethod": 1, "isSequential": False, "ratio": 0.6,
    "completionCondition": "${nrOfCompletedInstances/nrOfInstances>=0.6}"
}, "approverGroups": [
    {"approverType": "candidatePosts", "assigneeType": "assigneeByName",
     "postIds": ["positionId"], "postNames": ["部门经理"]}
]}
```

**会签-自定义（completionCondition 表达式）：**
```python
{"type": "approver", "name": "会签(自定义)", "approvalMode": 7, "attr": {
    "approvalMethod": 1, "isSequential": False,
    "completionCondition": "${nrOfCompletedInstances/nrOfInstances>=0.8}"
}, "approverGroups": [
    {"approverType": "candidateUsers", "assigneeType": "assigneeByName",
     "approverIds": ["user1", "user2", "user3"], "approverNames": ["张三", "李四", "王五"]}
]}
```

**发起人自己审批时自动跳过：**
```python
{"type": "approver", "name": "上级审批", "attr": {"skipApproval": 1}, ...}
```

**指定角色审批：**
```python
# ✅ roleIds 填角色 roleCode 字符串，不是数据库雪花 ID（已通过实际示例验证）
{"approverType": "candidateGroups", "assigneeType": "assigneeByName",
 "roleIds": ["dept_manager"],       # roleCode，如 "general_manager" / "dept_manager"
 "roleNames": ["部门经理"]}
```

**多角色会签（同一 group 内放多个角色）：**
```python
# 多个角色必须放在同一个 approverGroup，分开成两个 group 会变成独立串行任务
{"approverType": "candidateGroups", "assigneeType": "assigneeByName",
 "roleIds": ["general_manager", "purchase_director"],   # roleCode 数组
 "roleNames": ["总经理", "采购总监"]}
```

**表达式（assigneeByExp）：**

`approverType` 固定用 `"candidateUsers"`（复数），`expressionsIds` 填内置表达式：

| 表达式 | 含义 |
|--------|------|
| `${applyUserId}` | 发起人本人 |
| `${flowNodeExpression.getApplyDepartLeaders(execution)}` | 发起人部门负责人 |
| `${flowNodeExpression.getDepartLeaders(applyUserId)}` | 发起人所属所有部门负责人 |
| `${flowNodeExpression.getLevel1DepartLeaders(applyUserId)}` | 上一级部门负责人 |
| `${flowNodeExpression.getLevel2DepartLeaders(applyUserId)}` | 上二级部门负责人 |
| `${flowNodeExpression.getLevel3DepartLeaders(applyUserId)}` | 上三级部门负责人 |
| `${flowNodeExpression.getFormDepartLeaders(execution,'<字段key>')}` | 表单部门字段对应的负责人 |
| `${oaFlowExpression.getUserSuperPositionLevel1(applyUserId)}` | 上一级岗位人员 |
| `${oaFlowExpression.getUserSuperPositionLevel2(applyUserId)}` | 上二级岗位人员 |
| `${oaFlowExpression.getUserSuperPositionLevel3(applyUserId)}` | 上三级岗位人员 |

```python
{"approverType": "candidateUsers", "assigneeType": "assigneeByExp",
 "expressionsIds": ["${flowNodeExpression.getApplyDepartLeaders(execution)}"],
 "expressionsNames": ["发起人部门负责人"]}

# 发起人本人（兜底写法）
{"approverType": "candidateUser", "assigneeType": "assigneeByExp",
 "expressionsIds": ["${applyUserId}"], "expressionsNames": ["获取发起人"]}
```

**表单人员字段（assigneeByVariable）：**
```python
# 引用 start 节点（工作表事件触发）的 select-user 字段
{"approverType": "candidateUsers", "assigneeType": "assigneeByVariable",
 "variableContent": [
     {"formTableCode": "qing_jia_shen_qing_4mwz",
      "formTableId": "form_start_qing_jia_shen_qing_4mwz",
      "nodeId": "start", "nodeType": "table",
      "fieldName": "select_user_xxx", "fieldType": "select-user",
      "fieldLabel": "直接上级"}
 ],
 "variableTitle": ["直接上级"], "formTableType": "table"}

# 引用 data_get_one 节点的查询结果字段（nodeType="search"）
{"approverType": "candidateUsers", "assigneeType": "assigneeByVariable",
 "variableContent": [
     {"formTableCode": "ke_hu_shen_qing_co38",
      "formTableId": "form_task969210390657540096_ke_hu_shen_qing_co38",
      "nodeId": "task969210390657540096", "nodeType": "search",
      "fieldName": "create_by", "fieldType": "select-user",
      "fieldLabel": "记录创建人"}
 ],
 "variableTitle": ["记录创建人"], "formTableType": "search"}

# 引用 select-depart 部门字段时，必须加 isNeedTranslateToUserIds:true
{"approverType": "candidateUsers", "assigneeType": "assigneeByVariable",
 "variableContent": [
     {"formTableCode": "ke_hu_shen_qing_co38",
      "formTableId": "form_start_ke_hu_shen_qing_co38",
      "nodeId": "start", "nodeType": "table",
      "fieldName": "select_depart_xxx", "fieldType": "select-depart",
      "fieldLabel": "所属部门", "isNeedTranslateToUserIds": True}
 ],
 "variableTitle": ["所属部门"], "formTableType": "table"}
```

### 1.3 审批方式速查表

> ⚠️ 会签节点 `approvalMethod` 统一为 `1`，通过节点级 **`approvalMode`** 字段（在 `attr` 外）区分会签类型。

| approvalMode（节点级） | approvalMethod（attr内） | isSequential | completionCondition | 含义 |
|:---:|:---:|:---:|---|------|
| 不填（默认） | 1 | - | - | **或签**：任一人通过即可 |
| 3 | 1 | False | `==1` | **并行会签-全员通过**：所有人同时收到任务，全部通过才继续 |
| 3 | 1 | True | `==1` | **串行会签-全员通过**：按顺序逐个审批，全部通过才继续 |
| 4 | 1 | True | `>0` | **会签-一人通过**：任一人通过即可，一人驳回即全部驳回 |
| 5 | 1 | False | `>=0.5` | **会签-半数通过**：一半以上人通过即可 |
| 6 | 1 | False | `>=ratio` | **会签-比例投票**：按 `ratio` 比例通过（如 0.6=60%） |
| 7 | 1 | False | 自定义填写 | **会签-自定义**：用 `completionCondition` 表达式控制 |

### 1.4 「高级设置」逐项对照（设计器面板 ↔ 落库键）

审批节点与填写节点共用这一组开关，**都在 `attr` 里**。面板上默认打勾的别手贱关掉，
默认打叉的别乱开——它们直接改变办理人页面上有哪些按钮。

| 设计器面板上的项 | 落库键 | 默认 / 取值 | 含义 |
|---|---|---|---|
| 允许转审 | `transferStatus` | true | 办理人可把任务转给别人 |
| 允许驳回 | `rejectStatus` | true | 可驳回到前面任意已办节点 |
| 允许抄送 | `ccStatus` | true | 处理时可手动选抄送人 |
| 处理时选择下一步处理人 | `selnextUserStatus` | true | 办理人自选下一节点的人 |
| 允许加签 | `allowAddSign` | 审批 true / **填写 false** | 前加签（加签人先办、原办理人再办）/ 后加签（反过来） |
| 会签时允许加人 | `allowCountersignAddUser` | false | 会签进行中还能拉人进来 |
| 消息通知 | `msgStatus` | false | 任务到达时发系统/钉钉/企微/邮件 |
| 表单可编辑 | `formEditStatus` | false | ⚠️ 与字段权限是两回事，见下 |
| 审批人为空时 | `assigneeIsEmpty` | 0 | `0`=不自动跳过（默认）/ `1`=自动跳过该节点 |
| 审批人=发起人时 | `skipApproval` | 0 | `0`=由发起人自己审 / `1`=自动跳过 / `2`=转交部门负责人（该办理人须有部门且部门有负责人） |
| 超时提醒 | `nodeTimeout` + `timeDate` | null | 超时**小时数**（数字，最小 0.5，如 48=48 小时）。**两个字段必须同值且同时设，缺 `nodeTimeout` 整块不生效**；常配 `timeType:"timeDate"` |
| 意见分支开关 | 审批节点 `hasResultBranch` / 填写节点 `approvalEnabled` | false | 只有为 true，该节点后才能挂 `opinion`(suggest)；否则设计器里按钮灰置 |
| 审批方式 | `approvalMethod` | 固定 `1` | 会签类型由**节点级** `approvalMode` 区分，见 1.3 |

> ⚠️ **`formEditStatus` 与字段权限是两回事**：前者是「这张表单在这个节点**整体**能不能改」，
> 后者（走 `/act/process/extActProcessNodePermission/saveOrUpdateBatch`）才是
> 「**具体哪个字段**能改 / 只读 / 隐藏」。要「只放开个别字段」必须**两个都配**。

---

## 二、填写节点（edit）

让指定人员填写/编辑表单字段，可控制每个字段的可见/可编辑权限。

### 2.1 完整配置

```python
{
    "type": "edit",
    "name": "填写详情",

    # 表单数据来源节点（通常是 "start"）
    "formTableSourceTaskId": "start",

    # 填写人（与审批节点 approverGroups 结构相同）
    "approverGroups": [
        {
            "approverType": "candidateUser",
            "assigneeType": "assigneeByExp",
            "expressionsIds": ["${applyUserId}"],
            "expressionsNames": ["获取发起人"]
        }
        # —— 填写人 = 表单字段（如「直接上级」「姓名」）时必须用下面这组，
        #    且 **variableTitle 不能省**：设计器「指定填写对象」面板读的就是它，
        #    只写 variableContent 时面板显示为空（用户会以为流程没配好）。
        #    build_approver_group 已能从 variableContent[0].fieldLabel 自动派生
        #    variableTitle，调用方只写 variableContent 即可；卡片文案 content 由
        #    _get_approver_content 一并取用，无需手写。
        # {
        #     "approverType": "candidateUsers",            # 注意是复数 candidateUsers
        #     "assigneeType": "assigneeByVariable",
        #     "variableContent": [{
        #         "formTableCode": "<本表 code>",
        #         "formTableId": "form_start_<本表 code>",
        #         "nodeId": "start", "nodeType": "table",
        #         "fieldName": "<人员字段 model，如 select_user_xxx>",
        #         "fieldType": "select-user",              # 部门字段写 select-depart
        #         "fieldLabel": "直接上级",                 # = variableTitle 的值
        #         # select-depart 另需："isNeedTranslateToUserIds": true
        #     }],
        #     "variableTitle": ["直接上级"],
        #     "formTableType": "table"
        # }
    ],

    # ⚠️ 字段权限**不在 processJson 里** —— 节点内 `privileges` 写什么都**不影响权限**，
    #    只当它是设计器面板的回显残留。**唯一有效途径 = 独立 API**：
    #      POST /act/process/extActProcessNodePermission/saveOrUpdateBatch
    #      （每字段两条 ruleType=1显示 + ruleType=2编辑；ruleCode=字段 model；status 用字符串；
    #        必填 = 两条都 required:true。见 api-reference.md / field-perm-rule.md / gotchas #字段权限）
    #    为什么这么肯定（2026-09-16 受控实验）：同一节点只写节点内 privileges（生产全键、
    #      desformComKey 非空）→ save/deploy 全绿 → 回读 processJson 里 privileges 在，
    #      但 GET .../extActProcessNodePermission/list 该节点 **0 条**；再用 API 写两条 → 立刻 2 条。
    #      即两条通道完全独立，节点内那份进不了权限表。另有用户实测：只写它时审批表单里字段仍全部可编辑。
    #    下面注释里的 {field, readable, editable} 是**无效简写**，仅示意语义，勿照抄。
    # 字段权限（**无效占位**，真正的权限走上面的 API）
    "privileges": [],

    "attr": {
        "approvalEnabled": False,  # 开启后该审批节点才能挂「意见分支」（suggest）；不开则意见分支按钮灰置
        "transferStatus": True,   # 允许转审
        "rejectStatus":   True,   # 允许驳回
        "ccStatus":       True,   # 允许抄送
        "selnextUserStatus": True,
        "allowAddSign":   False,
        "msgStatus":      False,
        "nodeTimeout":    None,           # ⚠️ 超时小时数（数字），缺此字段超时不生效
        "timeDate":       None,           # 与 nodeTimeout 保持相同值
        "timeType":       "timeDate",
        "formEditStatus": False,
    }
}
```

### 2.2 场景示例

**发起人填写表单：**
```python
{"type": "edit", "name": "表单"}
# 默认 approverGroups 为发起人
```

**指定用户填写，部分字段只读：**
```python
{
    "type": "edit", "name": "业务员填写",
    "approverGroups": [
        {"approverType": "candidateUser", "assigneeType": "assigneeByName",
         "approverIds": ["userId"], "approverNames": ["李四"]}
    ],
    "privileges": [
        {"field": "contract_amount", "readable": True, "editable": False}  # 金额只读
    ]
}
```

---

## 三、更新记录节点（data_update）

自动将工作表中的指定字段更新为新值，支持固定值、变量引用、数值增减等。

### 3.1 完整配置（processJson 真实结构）

```python
{
    "type": "data_update",
    "name": "更新采购申请",
    "attr": {
        "formType": 2,
        "formTableId": "form_start_{formTableCode}",        # 来源是start节点时
        # 来源是get_one节点时：form_{get_one节点ID}_{formTableCode}
        "formTableCode": "cai_gou_shen_qing_swdd",
        "formTableName": "采购申请",
        "formTableSourceTaskId": "start",                   # 要更新的数据来源节点ID
        "formTableSourceNodeType": "table",                 # start="table"，get_one="search"
        "expressionType": "delegateExpression",
        "expressionValue": "${updateRecordDelegate}",
        "level": "1",
        "updateFields": [
            # 类型1：固定值（val 直接是字符串/数值）
            {
                "id": "968425733284339712",
                "optType": "1",                # 操作类型（见下表）
                "field": "select_xxx",         # 目标字段ID
                "val": "成交客户",              # 直接字符串
                "fieldType": "select",
                "type": "select",
                "fieldValue": ""
            },
            # 类型2：引用变量（val 是对象，需加 valueType=3 + valType="variable"）
            {
                "id": "968425362914713600",
                "optType": "1",
                "valueType": 3,               # 引用变量时必须为 3
                "field": "date_xxx",
                "val": {
                    "formNodeType": "system",  # 变量来源类型
                    "variableValue": "nowDate",
                    "variableName": "当前日期"
                },
                "fieldType": "date",
                "type": "date",
                "options": {"format": "yyyy-MM-dd"},
                "valType": "variable",         # 引用变量时必须为 "variable"
                "fieldValue": ""
            }
        ]
    }
}

> ⚠️ **updateFields 条目引用变量必带三键（2026-09-09 实测）：** 只要 `val` 是**对象**（变量引用，formNodeType ∈ table / search / getMore / function / system），**条目顶层**就必须带 `valueType: 3` + `valType: "variable"`（类型 2 注释已写"引用变量时必须为 3"，但手拼条目极易漏）。**缺键时 save/deploy 全绿、服务端 JSON 看似正常，设计器却把该条目当固定值解析——日期字段的值框显示成一个具体时间而非变量引用**。date 字段条目另带 `options: {"format": "yyyy-MM-dd"}`。
> 引用**运算节点结果**（formNodeType=function，=UI 值源选「运算结果」的同款存储）的完整条目形态：

```python
{
    "id": "<18位时间戳id>",
    "optType": "1",
    "valueType": 3,                        # ⚠️ 必带：3=引用变量
    "field": "date_xxx",                   # 目标字段 model
    "val": {
        "formNodeType": "function",        # function=引用运算节点结果
        "variableValue": "result",
        "formTableCode": "function-date",  # function-{funType}：date/number/fun/date-diff/record
        "variableName": "结果",
        "fieldType": "date",
        "formNodeId": "task<运算节点ID>",
        "formNodeName": "<运算节点名>",
        "operationMode": "cache",
        "decimals": 2
    },
    "fieldType": "date",
    "type": "date",
    "valType": "variable",                 # ⚠️ 必带
    "options": {"format": "yyyy-MM-dd"},   # date 字段必带
    "fieldValue": ""
}
```

> ⚠️ **function 运算节点的 formTableList 登记要按链序插入**（紧随 start 表条目 `nodeId=start, nodeType=table` 之后），**不要一律 append 到列表尾部**——登记顺序即设计器解析下游节点可引用数据源的顺序，append 到下游 data_add / getMore 等条目之后，引用该 function 结果的节点在 UI 里会解析不到源（2026-09-09 实测同场景整改；get_more 登记的插序规范见 SKILL.md get_more 段）。
```

**optType 操作类型：**

| optType | 说明 | 适用字段类型 |
|---------|------|------------|
| `"1"` | 设为固定值（默认） | 所有类型 |
| `"2"` | 增加/追加（数值字段+值，数组字段追加元素） | number/money/多选 |
| `"3"` | 减少/移除（数值字段-值，数组字段删除元素） | number/money/多选 |

**数据来源（formTableSourceTaskId 指向谁）决定 formTableSourceNodeType——写错会静默不写库（2026-09-04 实证）：**
- 源=`start`（更新当前触发记录）→ `"table"`（例：按钮点当前行改状态）
- 源=get_one/单条查询 → `"search"`（单条；wms 库存增减链）
- 源=**getMore**（selectType=3 关联多条 / selectType=4 批量取数）→ `"getMore"` **且必须带 `formTableSourceGetDataType=1`**——写成 `"search"` 引擎不批量迭代，流程跑完但一行不改
- `formTableId` = `form_{源节点id}_{目标表code}`

**变量 val 引用其他表单字段时（formNodeType="table"/"search"/"getMore"）：**
```python
"val": {
    "formNodeType": "table",         # 来源节点类型
    "formNodeId": "start",
    "formNodeName": "工作表事件触发",
    "formTableCode": "source_form",
    "variableValue": "input_xxx",    # 来源字段ID
    "variableName": "字段显示名"
}
```

### 3.2 常用场景（脚本简化格式）

```python
# 更新状态字段（固定值）
{"type": "data_update", "name": "标记已审批",
 "updateFields": [{"field": "status_field", "val": "已审批", "fieldType": "select"}]}

# 数值增加
{"type": "data_update", "name": "库存增加",
 "updateFields": [{"field": "stock", "val": 1, "fieldType": "number", "optType": "2"}]}

# 数值减少
{"type": "data_update", "name": "库存减少",
 "updateFields": [{"field": "stock", "val": 1, "fieldType": "number", "optType": "3"}]}
```

---

## 四、排他网关（exclusive）— 互斥分支

满足条件走对应分支，只走一个分支（第一个满足条件的分支），必须有且只有一个默认分支（isDefault=True）。

### 4.1 完整配置

```python
{
    "type": "exclusive",
    "name": "路由",
    "conditionNodes": [
        {
            "name": "金额小于1万",
            "isDefault": False,
            "priorityLevel": 1,         # 优先级，数字越小越先判断
            "branchType": 1,            # 1=条件分支，2=默认分支
            "conditions": [             # 简化写法，单组条件
                {
                    "rule": "lt",           # 条件规则
                    "ruleName": "小于",
                    "field": "money_xxx",   # 字段ID
                    "columnName": "合同金额", # 字段名（展示用）
                    "val": 10000,
                    "type": "money",        # 字段类型
                    "valueType": "1",       # 1=固定值
                    "valType": "money"      # 值类型
                }
            ],
            "nodes": [...]               # 该分支下的子节点
        },
        {
            "name": "金额1万~10万",
            "isDefault": False,
            "priorityLevel": 2,
            "conditions": [
                {"rule": "ge", "ruleName": "大于等于", "field": "money_xxx",
                 "columnName": "合同金额", "val": 10000, "type": "money"},
                {"rule": "lt", "ruleName": "小于", "field": "money_xxx",
                 "columnName": "合同金额", "val": 100000, "type": "money"}
                # 多个条件默认 AND 关系
            ],
            "nodes": [...]
        },
        {
            "name": "其他情况",           # 必须有一个默认分支
            "isDefault": True,
            "priorityLevel": 3,
            "nodes": [...]
        }
    ]
}
```

### 4.2 条件规则（rule）完整列表

| rule | 含义 | rule | 含义 |
|------|------|------|------|
| `eq` | 等于 | `ne` | 不等于 |
| `lt` | 小于 | `le` | 小于等于 |
| `gt` | 大于 | `ge` | 大于等于 |
| `like` | 包含 | `notLike` | 不包含 |
| `null` | 为空 | `notNull` | 不为空 |
| `in` | 是其中一个 | `not_in` | 不是任何一个 |
| `between` | 介于两值之间 | | |

> ⚠️ **分支下条件值形态勘误（2026-09-10 用户 UI 实测纠正；「分支下」= 互斥/包含网关 conditionNodes 的条件行，与触发条件 startCondition 是两套场景，勿互套）**：
>
> 1. **规则码**：`in`→「是其中一个」、`not_in`→「不是任何一个」、`ne`→「不等于」。**旧表 `notIn`/「不属于」为错码**——写 notIn 能 save/deploy 但设计器选项不对、用户一眼识破（ruleName 仅展示，运行时只看 rule 码）。
> 2. **选项类控件 val 形态（分支下）**：radio（单选）→ `val`=数组（如 `["1"]`）、**无 `value` 键**、`name`=**[]** 空数组、`valType`=""、行带雪花 id；checkbox（多选框）→ `val`=逗号串字符串 + `value`=数组、`valType`=""；select（下拉）→ `val`+`value` 均数组、`valType`=`select`。
> 3. **日期/日期时间字段（分支下）**：`type`/`valType` 写字段控件类型 **`date`**（**禁止写 `datetime`**——设计器值框显示异常，2026-09-10 用户两次纠正）；`val` 写**毫秒时间戳 int**（2026-09 → `1788192000000`；年月=当月 1 号 0 点；日期时间=秒级毫秒）。**写日期字符串也错**（能 save/deploy 但设计器显示不对）。
> 4. UI 原生样本（分支下，2026-09-10 用户界面保存后 queryById 实测）：
>    - checkbox：`{"rule":"not_in","ruleName":"不是任何一个","valueType":"1","val":"1","name":null,"field":"checkbox_xxx","columnName":"多选框","type":"checkbox","valType":"","value":["1"]}`
>    - radio：`{"id":"1789008108043203","rule":"not_in","ruleName":"不是任何一个","valueType":"1","val":["1"],"name":[],"field":"radio_xxx","columnName":"单选按钮","type":"radio","valType":""}`
>    - date：`{"rule":"ne","ruleName":"不等于","valueType":"1","val":1789040031000,"name":null,"field":"date_xxx","columnName":"日期时间","type":"date","valType":"date"}`
> 5. **触发条件 startCondition 的同款规则**（2026-09-10 用户 UI 实测，流程「单选按钮触发新增编辑流程」）：radio not_in = `val`=数组 + `name`=**null**（**不是 []**）+ `valType`=""——`name` 用 null 还是 [] 按场景区分（#34 同源），分支下=[]、触发条件下=null。

### 4.3 条件字段类型（type）

| type | 说明 |
|------|------|
| `text` | 文本 |
| `textarea` | 多行文本 |
| `number` | 数值 |
| `money` | 金额 |
| `select` | 下拉选择 |
| `date` | 日期 |
| `datetime` | 日期时间 |
| `user` | 人员组件 |
| `dept` | 部门组件 |

### 4.4 使用流程变量作为条件

```python
# 使用流程参数（upvariable 节点设置的变量）
"conditionGroup": [
    {
        "queryItems": [
            {
                "rule": "gt", "ruleName": "大于",
                "field": "contract_count",     # 流程参数名
                "columnName": "合同数量",
                "val": 0, "type": "number",
                "valueType": "1",
                # 工作表选 "流程参数"
            }
        ]
    }
]
```

### 4.4.1 使用运算节点结果作为条件（2026-09-09 实测，用户 UI 确认）

排他/包含分支的字段源可直接选**运算节点**（条件 = 运算结果与常量比较），**无需先经 upvariable 中转流程参数**（中转旧路径见「十一」，仅流程参数类业务仍需）。

```python
{
    "type": "exclusive",
    "name": "时长路由",
    "conditionNodes": [
        {
            "name": "时长大于10天",            # 条件分支
            "isDefault": False,
            "priorityLevel": 1,
            "branchType": 1,
            "conditionGroup": [{
                "queryItems": [{
                    "rule": "gt", "ruleName": "大于",
                    "valueType": "1",
                    "val": 10,                 # 与结果比较的常量
                    "name": None,
                    "field": "result",         # ⚠️ 恒为 "result"（运算节点输出列）
                    "columnName": "结果",
                    "type": "number",          # 按结果类型（date-diff 天数=number）
                    "valType": "number"
                }]
            }],
            "branchForm": {                    # ⚠️ 字段源 = 运算节点
                "formTableCode": "function-date-diff",   # function-{funType}
                "formNodeId": "<运算节点ID>",
                "formNodeType": "function"
            },
            "formTableCode": "function-date-diff",       # 与 branchForm.formTableCode 一致
            "nodes": [{"type": "approver", "name": "总监审批",
                       "approverGroups": [{"approverType": "candidateUser", "assigneeType": "assigneeByName",
                                           "approverIds": ["<username>"], "approverNames": ["<显示名>"]}]}],
        },
        {
            "name": "时长小于等于10天",        # 补集兜底：>N 与 ≤N 互为补集时不用再写反向条件
            "isDefault": True,
            "branchType": 2,
            "conditionGroup": [],
            "nodes": [{"type": "approver", "name": "部长审批",
                       "approverGroups": [{"approverType": "candidateUser", "assigneeType": "assigneeByName",
                                           "approverIds": ["<username>"], "approverNames": ["<显示名>"]}]}],
        },
    ],
}
```

> ⚠️ 要点：① `queryItems[].field` 固定 `"result"`、`columnName` 写「结果」，比较常量写 `val`（valueType=1）；② funType → formTableCode：date→`function-date`、date-diff→`function-date-diff`、number→`function-number`、fun→`function-fun`、record→`function-record`；③ 运算节点须在流程 `formTableList` 按链序登记（同 #58 function 登记规则），否则设计器字段源解析不到；④ 补集分支第二条直接用默认分支（isDefault=true/branchType=2/conditionGroup=[]）。全链路已实测（save/deploy/回读/设计器显示/用户确认），详见 gotchas #59。

**变体：运算结果 vs 运算结果（双运算节点互比，2026-09-09 用户 UI 确认）** —— 比较值不是常量而是另一个运算节点的结果时（如「时长结果 ≥ 统计条数结果」）：

```python
# branchForm 不变（指向被比较的运算节点，field 仍为 "result"），只换 queryItems：
{"rule": "ge", "ruleName": "大于等于",
 "valueType": 3,                        # ⚠️ 3=val 是变量引用对象
 "val": {"formNodeType": "function",    # 比较值来源 = 另一运算节点
         "variableValue": "result",
         "formTableCode": "function-record",   # 另一运算的 function-{funType}
         "variableName": "结果",
         "formNodeId": "<另一运算节点ID>",
         "formNodeName": "<另一运算节点名>",
         "operationMode": "everyTime",  # record 型固定 everyTime；其余 cache
         "decimals": 2},
 "name": None,
 "field": "result", "columnName": "结果",
 "type": "number",
 "valType": "variable"}                 # ⚠️ val 为变量时 valType='variable'（常量时为 'number'）
```

> 双运算互比的额外前提：两个运算节点都在 `formTableList` 按链序登记；「统计条数」类运算（funType=record）还要满足 funContext.nodeId=上游 get_more 节点 id、getDataType 与 get_more 一致、operationMode=everyTime（见「十八」18.2）。补集分支仍用默认分支兜底。

### 4.5 真实 processJson conditionNodes 关键字段（实测 JSON 实证）

```json
{
    "id": "flow968440236302573569",
    "pid": "Gateway968440236302573568",
    "name": "成交客户",
    "isDefault": false,
    "type": 3,
    "attr": {
        "branchType": 1,
        "priorityLevel": 1,
        "conditionGroup": [
            {
                "id": "968440474182524928",
                "matchType": "",
                "queryItems": [
                    {
                        "rule": "eq", "ruleName": "等于",
                        "valueType": "1",
                        "val": "成交客户",
                        "name": null,
                        "field": "select_1775649166520_177631",
                        "columnName": "客户状态",
                        "type": "select",
                        "valType": "select"
                    }
                ]
            }
        ],
        "showPriorityLevel": true,
        "level": "1",
        "branchForm": {
            "formTableCode": "ke_hu_shen_qing_co38",
            "formNodeId": "start",
            "formNodeType": "table"
        },
        "formTableCode": "ke_hu_shen_qing_co38"
    }
}
```

> 关键规律：`queryItems[].name` 固定为 `null`（标签在 `columnName`）；默认分支 `isDefault: true`，`branchType: 2`，`conditionGroup: []`；`branchForm` 和 `formTableCode` 必须在每个条件分支的 `attr` 中携带。

> ⚠️ **`branchForm.formNodeId` 必须指向「产出该值的那个节点」，不能一律填 `start`（2026-09-16 实测返工）。** `start` = 从**触发那一刻的起始行快照**取值；**流程中途由 edit/approver 节点填的字段，起始行快照不会随之刷新**，网关评估时永远拿到空值 → 条件静默判失败、走默认分支（save/deploy 全绿，只有后台日志 `【条件评估】… 实际值:<> … 结果:<✗失败>` 才暴露）。上面 4.5 示例填 `start` 是因为它判的 `客户状态` **新增时就有值**。生产里的指向规律：
>
> | 被判字段的来源 | `formNodeId` / `formNodeType` |
> |---|---|
> | 新增时就有（起始行） | `start` / `table` |
> | get_one 检索结果 | 该 `data_get_one` 节点 / `search` |
> | 运算节点结果 | 该 function 节点 / `function` |
> | **edit/approver 节点中途填的** | 该填写节点 id / **`table`**（✅ 2026-09-16 实测通过：分支正确读到审批节点填入的值、按预期走对应分支。`formTableCode` 填该表 code） |

---

## 五、并行分支（parallel）

所有分支同时执行，全部完成后才进入下一节点。无需配置条件。

> **位置约束：** 并行/包容分支不能再加进并行行（conditionNode，type=10）内部——设计器面板在此处灰置；网关嵌套网关的通用禁令见 gotchas #36。

```python
{
    "type": "parallel",
    "name": "并行审批",
    "conditionNodes": [
        {
            "name": "总监审批",
            "isDefault": False,
            "nodes": [
                {"type": "approver", "name": "总监审批", "approverGroups": [...]}
            ]
        },
        {
            "name": "总经理审批",
            "isDefault": False,
            "nodes": [
                {"type": "approver", "name": "总经理审批", "approverGroups": [...]}
            ]
        }
    ]
}
```

> **适用场景：** 多个部门/角色需要同时审批，全部通过后流程才继续。

**真实 processJson 关键字段：**
- 网关 ID 前缀：`Gateway`
- 聚合节点：`childNode = {"type": "polymerize", "id": gateway_id + "1", ...}`（ID 为网关 ID + `"1"`）
- `conditionNodes[].type`：`10`（不是 3）
- `conditionNodes[].attr.branchType`：`2` 或 `3`，`conditionGroup: []`，无条件
- 意见分支（suggest）的 `conditionNodes[].type`：`8`，`id` 前缀为 `btn`，`attr: {"priorityLevel": 2}`

---

## 六、包含分支（inclusive）

所有满足条件的分支都执行（与排他网关的区别：互斥只走一个，包含可走多个）。

> **位置约束：** 同并行分支——不能加进并行行（type=10）内部。

```python
{
    "type": "inclusive",
    "name": "包含路由",
    "conditionNodes": [
        {
            "name": "销售总监审批",
            "isDefault": False,
            "priorityLevel": 1,
            "conditions": [
                {"rule": "eq", "ruleName": "等于",
                 "field": "status_field", "columnName": "合同状态",
                 "val": "执行中", "type": "select"}
            ],
            "nodes": [{"type": "approver", "name": "销售总监审批", ...}]
        },
        {
            "name": "总经理审批",
            "isDefault": False,
            "priorityLevel": 2,
            "conditions": [
                {"rule": "gt", "ruleName": "大于",
                 "field": "money_field", "columnName": "合同金额",
                 "val": 100000, "type": "money"}
            ],
            "nodes": [{"type": "approver", "name": "总经理审批", ...}]
        }
    ]
}
```

> **场景示例：** 合同状态为"执行中"且金额大于10万时，销售总监和总经理都需要审批；只满足其中一个条件时只走对应分支。

**真实 processJson 关键字段：**
- 聚合节点 `type: "inclusive_end"`（不是 `polymerize`），ID = 网关 ID + `"1"`
- `conditionNodes[].type`：`10`（多数）或 `3`，均合法
- `conditionNodes[].attr.branchType`：`1`（条件分支）
- `conditionNodes[].attr.branchForm`：`{"formTableCode": "...", "formNodeId": "start", "formNodeType": "table"}` — 必须携带
- `conditionNodes[].attr.formTableCode`：与 `branchForm.formTableCode` 相同 — 必须携带
- `queryItems[].name`：固定 `null`；`queryItems[].val`：`in` 规则为**数组**（不是字符串）

> ⚠️ **规则下拉按控件族白名单给**（范围查询只属日期/时间/数值；文本与公式无「在范围内」、文件类仅 为空/不为空）——「表单内每个组件一条分支」批量铺规则前必读 **二十节「规则下拉白名单按控件族给」**；写不匹配的 rule 服务端不校验（save/deploy/回读全绿但设计器渲染异常），见 gotchas #85。

### 6.2 `in` 规则（值属于列表）

当字段值需要匹配多个候选值之一时，使用 `in` 规则，`val` 为数组：

```python
{
    "name": "经理审批",
    "isDefault": False,
    "priorityLevel": 1,
    "conditions": [
        {
            "rule": "in", "ruleName": "属于",
            "field": "customer_type_field", "columnName": "客户类型",
            "val": ["成交客户", "非成交客户"], "type": "select"
        }
    ],
    "nodes": [{"type": "approver", "name": "经理审批", ...}]
}
```

### 6.3 多组 OR 条件（conditionGroup）

当一个分支需要 `(A 且 B) 或 (C 且 D)` 这类复合逻辑时，使用 `conditionGroup`：
- **多个组之间是 OR 关系**
- **同一组内多个 queryItems 是 AND 关系**（`matchType: ""` 表示 AND）

```python
{
    "name": "高价值客户审批",
    "isDefault": False,
    "priorityLevel": 3,
    "conditionGroup": [
        {
            # 组1：企业客户 AND 金额 ≥ 100万
            "matchType": "",
            "queryItems": [
                {"rule": "eq", "ruleName": "等于",
                 "field": "customer_type_field", "columnName": "客户类型",
                 "val": "企业客户", "type": "select"},
                {"rule": "ge", "ruleName": "大于等于",
                 "field": "money_field", "columnName": "合同金额",
                 "val": 1000000, "type": "money"}
            ]
        },
        {
            # 组2：个人客户 AND 金额 > 10万
            "matchType": "",
            "queryItems": [
                {"rule": "eq", "ruleName": "等于",
                 "field": "customer_type_field", "columnName": "客户类型",
                 "val": "个人客户", "type": "select"},
                {"rule": "gt", "ruleName": "大于",
                 "field": "money_field", "columnName": "合同金额",
                 "val": 100000, "type": "money"}
            ]
        }
    ],
    "nodes": [{"type": "approver", "name": "高价值客户审批", ...}]
}
```

> **等价逻辑：** `(企业客户 && 金额 ≥ 100万) || (个人客户 && 金额 > 10万)`

---

## 七、延迟节点（time / timer_event）

上一节点完成后，先暂停流程，按配置等待后再继续执行后续节点。支持两种定时类型（「指定时间触发」/「指定一个时间段之后执行」）。

> **节点 ID 必须以 `TimerEventDefinition_` 为前缀**，如 `TimerEventDefinition_968452522509508608`。

> ⚠️ **`attr.timeCycle` 是「执行时间」单选组的模式选择器，不是时长值。** 见 §7.1 的预设 token 表——把任意 ISO 串直接塞进 `timeCycle` 会 save/deploy 全绿但设计器里「执行时间」整排未选中、抽屉空白（2026-09-10 用户实测）。

> ⚠️ **勿与 `start` 根节点顶层的 `timeCycle` 混淆**：生产数据的 `start` 根节点顶层恒有一组冗余字段 `{timeType, timeDate, timeCycle, entTime, messageEventName}`（典型值 `timeCycle="PT1H"`、`timeType="timeDate"`、`timeDate=null`）——**它与延迟语义无关、不参与任何等待计算**；全库约 38 处 `PT1H` 全部出自这里（各 example 的完整 processJson 中的同名片段同理）。改动/复制流程时原样保留即可，**不要**据此认为延迟节点的 `timeCycle` 该写 `PT1H`。

**节点顶层键契约（2026-09-10 全库 4 个延时节点实测完全一致）：**

```python
['addable', 'attr', 'childNode', 'deletable', 'error', 'errorContent',
 'id', 'name', 'pid', 'status', 'timeDate', 'type']
```

手工拼 dict 时 `addable=True` / `deletable=False` / `error=False` / `errorContent=''` **不可省**（否则流程图无「＋加节点」图标）；顶层 `timeDate` 是冗余键（UI 原生节点落 `""` 空串，**真实生效值只在 `attr.timeDate`**）；`content` 非必需（`build_time_node` 会自动补）。

### 7.1 等待固定时长（timeType = timeDuration）

等待固定时长后继续，适合"审批通过后 N 天执行"场景。

设计器「执行时间」是单选组，**只认下面 5 个 token**；比对不上就一个都不选中：

| UI 选项 | `attr.timeCycle` | `attr.timeDate` |
|---|---|---|
| 1分钟后 | `PT1M` | `None` |
| 1小时后 | **`P1H`** ⚠️非标准 ISO，但这是预设 token | `None` |
| 1天后 | `P1D` | `None` |
| 一个月后 | `P1M` | `None` |
| **自定义** | **`custom`** | **ISO 8601 Duration 串** |

**预设外的任意时长（30分钟/1周/2小时30分…）UI 上只能走「自定义」**，落库 = `custom` + 时长串放 `timeDate`：

```python
# ✅ 命中预设
{"type": "timer_event", "name": "延迟1小时",
 "attr": {"timeType": "timeDuration", "timeCycle": "P1H", "timeDate": None}}

# ✅ 预设外时长 —— 必须 custom，时长串写进 timeDate
{"type": "timer_event", "name": "延时30分钟",
 "attr": {"timeType": "timeDuration", "timeCycle": "custom", "timeDate": "PT30M"}}
{"type": "timer_event", "name": "延时1周",
 "attr": {"timeType": "timeDuration", "timeCycle": "custom", "timeDate": "P7D"}}

# ❌ 错误：预设外的值塞进模式位 → 设计器「执行时间」整排未选中
{"attr": {"timeType": "timeDuration", "timeCycle": "PT30M", "timeDate": None}}
```

**`timeDate` 里的时长串 = 标准 ISO 8601 Duration** `P[n]Y[n]M[n]DT[n]H[n]M[n]S`（官方文档 <https://help.qiaoqiaoyun.com/flow/node/time.html>）：

| 值 | 含义 | 备注 |
|----|------|------|
| `PT30S` / `PT1M` / `PT30M` | 30秒 / 1分钟 / 30分钟 | ⚠️ 时/分/秒必须在 `T` 之后（`P1M` 是"月"） |
| `PT1H` / `PT2H30M` / `PT8H` | 1小时 / 2小时30分 / 8小时 | ⚠️ 小时必须带 `T` |
| `P1D` / `P7D` / `P14D` | 1天 / 7天(1周) / 14天(2周) | ⚠️ **无 `W` 位**，1周写 `P7D` 不是 `P1W` |
| `P1M` / `P3M` / `P1Y` | 1个月 / 3个月 / 1年 | `T` 之前的 `M`=月 |
| `P1DT8H` / `P1Y6M3DT4H30M` | 组合写法 | |

⚠️ 注意 `P1H`（预设 token）与 `PT1H`（标准 ISO）**不是同一个东西**：想选「1小时后」用 `P1H`；标准写法 `PT1H` 只在「自定义」输入框（`timeDate`）里用。

⚠️ 任何形态错误都**能 save/deploy 成功但设计器显示未选中**，删/改节点后必须按「token 白名单 / custom+ISO 串」的**形态**回读 `attr.timeCycle` 与 `attr.timeDate`（只比对"写进去的值还在不在"是自证循环，查不出错）。

### 7.2 到达指定时间点（timeType = timeDate）

到达某个具体时间点后继续，适合"在某日期执行"场景。

```python
{
    "type": "timer_event",
    "name": "指定时间",
    "attr": {
        "timeType": "timeDate",        # ✅ 正确值（非 "date"）
        "timeDate": "2026-04-14T19:00:00",   # ISO 8601 日期时间字符串（非时长串）
        "timeCycle": None,
    }
}
```

### 7.3 两种定时类型对照

`timeCycle` 固定填 `"custom"`，具体值写入 `timeDate`——**值有两种语义**：绝对时间点，或（下拉无对应档位时的）相对时长 ISO 串。

```python
{
    "type": "timer_event",
    "name": "延时",
    "attr": {
        "timeType": "timeDuration",
        "timeCycle": "custom",                 # ← 固定值 "custom"
        "timeDate": "2026-04-15T12:13:14",     # ① 绝对时间点
        # "timeDate": "PT3M",                  # ② 相对时长：下拉无「3分钟后」档位时用这个（2026-09-10 用户口述规则，API 侧已验、UI 原生样本待确认）
    }
}
```

> ⚠️ **相对时长档位（如"3分钟后"）落库形态**：`timeCycle` 仍写 `"custom"`，把 `PT3M` 写进 **`timeDate`**。**不是** `timeCycle:"PT3M"`（非枚举 → 前端显示为空），**也不是**"当前时刻+3分钟"的具体时间点（那是死值，非每次运行相对等待）。只剩 `timeType/timeCycle/timeDate` 三键，勿自造辅助键。详见 gotchas #30 custom 契约段。
>
> **custom 值必须是标准 ISO 8601 时长**：`P[n]Y[n]M[n]DT[n]H[n]M[n]S`，时分秒务必带 `T`——`PT30M`(30分钟)/`PT1H`(1小时)/`PT2H30M`/`P3D`(3天)/`P1DT8H`/`P1Y6M`；常见错误：`P30M`→`PT30M`、`P1H`→`PT1H`、`PT1H30`→`PT1H30M`、`PT`→`PT1M`、`P`→`P1D`。⚠️ `M` 在 `T` 前是"月"、`T` 后是"分钟"；下拉枚举 token 与自定义值不是一套，勿混（详见 gotchas #30）。

**三种模式对照：**

| 模式 | timeType | 关键字段 |
|------|----------|---------|
| 固定时长 | `timeDuration` | `timeCycle = "P1H"/"P1D"/"P1M"`，`timeDate = None` |
| 指定时间点 | `timeDate` | `timeDate = "2026-04-14T19:00:00"`，`timeCycle = None` |
| 自定义 | `timeDuration` | `timeCycle = "custom"`，`timeDate = "2026-04-15T12:13:14"`（时间点）或 `"PT3M"`（相对时长） |

---

## 八、通知节点（notice → message_*）

> ⚠️ **真实节点 type 不是 `"notice"`**，系统实际使用 `message_system`、`message_email`、`message_ding`、`message`。
> 脚本（miniflow_creator.py）中用 `type: "notice"` + `attr.noticeType` 描述，内部自动映射。

向指定人员自动发送消息，支持 4 种渠道：

| 脚本 noticeType | 真实节点 type | 说明 |
|---|---|---|
| `"system"` | `message_system` | 系统消息（站内信） |
| `"email"` | `message_email` | 邮件 |
| `"dingding"` | `message_ding` | 钉钉 |
| `"weixinqy"` | `message` | 企业微信 |

接收人通过 `toUserIds`/`toUserExpression` 指定（**不是** `approverGroups`）：
- 指定用户：`"user.{username}"`
- 指定角色：`"role.{roleCode}"`
- 指定部门：`"dept.{deptId}"`
- 发起人表达式：`toUserExpression: "${applyUserId}"`

### 8.1 系统消息 / 钉钉 / 企业微信

```python
{
    "type": "notice",
    "name": "系统消息",
    "attr": {
        "noticeType": "system",            # system / dingding / weixinqy
        "noticeTitle": "审批通知",
        "noticeContent": "您的申请已通过审批，请查看。",
    },
    # 接收人（默认发起人）：
    "toUserExpression": "${applyUserId}",  # 或用固定 ID：
    # "toUserIds": ["user.admin", "role.admin"],
    # "toUserNames": ["admin", "管理员"],
}
```

### 8.1b 变量收件人（如「记录创建人」）——2026-09-07 前端源码+全链路实测

固定收件人之外，`toUserIds` 条目可以是**变量**：字符串 `"var." + JSON.stringify({formTableCode, formTableId, nodeId, nodeType, field, fieldType})`（对照前端 MessageUserSelect 组件落库格式）。并行 `toUserNames` 写显示名；attr 内与节点顶层两处都要写。

```python
import json
# 记录创建人 = start 节点系统字段 create_by（fieldType select-user）
var_entry = "var." + json.dumps({
    "formTableCode": "ws_76fa890969", "formTableId": "form_start_ws_76fa890969",
    "nodeId": "start", "nodeType": "table",
    "field": "create_by", "fieldType": "select-user",
}, ensure_ascii=False)

{
    "type": "notice", "name": "发送系统消息",
    "attr": {
        "noticeType": "system", "noticeTitle": "触发通知",
        "noticeContent": "新增了一条数据",
        "toUserIds": [var_entry], "toUserNames": ["记录创建人"],
    },
    "toUserIds": [var_entry], "toUserNames": ["记录创建人"],   # 节点顶层同写
}
```

- `field` 是字段 model；其他人员字段同理换 `field`/`fieldType`。固定收件人（`user.`/`role.`/`dept.`）与 `var.` 条目可混排。
- ❌ **不要**用 approver 的 `variableTitle`/`variableContent` 对象形态——实测消息群发给 8 个错误收件人、正确收件人收不到（gotchas #49）。
- 两节点完整配方（触发条件+监控字段+验证方式）见 create-flow.md 组合 F。

**查询类节点结果作收件人（2026-09-09 API 直写 + UI 手配保存逐键比对实证）**：同款 6 键 var 条目，`nodeType` 按上游节点的 formTableList `nodeType` 填，`nodeId` = 上游节点 id，条目要引用该节点输出（注意通知节点必须挂在上游之后）：

- 获取单条记录（data_get_one）结果里的 select-user 字段：
  `{"formTableCode": <表code>, "formTableId": "form_{get_one节点id}_{表code}", "nodeId": <get_one节点id>, "nodeType": "search", "field": <该记录上的用户字段model>, "fieldType": "select-user"}`
  （formTableId/formTableCode 与 get_one 节点 formTableList 条目一致，与「十四」get_one→nodeType=search 的取数口径同源）
- 获取单个用户（data_get_udr_one，从用户字段/组织架构取到的人）→ 收件人=取到的用户本身：
  `{"formTableCode": "sys_user", "formTableId": "form_{udr节点id}_sys_user", "nodeId": <udr节点id>, "nodeType": "getUserDeptRole", "field": "username", "fieldType": "select-user"}`
  （字段=sys_user 记录的用户名列；UI 手配保存回读与 API 直写逐键一致，属已实证形态。角色/部门取数按同表结构类推 `sys_role`/`sys_depart`，未单独实测）
- 收件人显示名 `toUserNames`（attr 层）UI 重存时会**重写为引用目标显示名**（工作表用户字段→该字段中文名；sys_user.username→「用户标识」），顶层 toUserNames **保留旧值不强制同步**（两处可不一致，属 UI 正常行为）；UI 重存还会把 `attr.title` 同步为节点名、补 `toUsers:[]`/`toUserExpression:""`/`jsonContext:{}`、节点 content 前缀「通知人:」。这些展示层差异不影响 API 直写形态的可用性。

**引用上游「添加记录」节点新增的值作消息正文（2026-09-10 API 直写 + 回读实证）**：消息节点位于 data_add 之后时，正文引用该新增记录的字段值，走与表字段同一套 4 键占位符契约，只是 `nodeId`=data_add 节点 id、`nodeType="plus"`：

```python
ref = {'field': <目标表字段model>, 'formTableCode': <data_add 的目标表 code>,
       'nodeId': <data_add 节点id>, 'nodeType': 'plus'}
h = hashlib.md5(json.dumps(ref, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
a['templateContext'] += '\n仓库名称：{{%s.仓库名称}}' % h          # 后缀=字段中文名
a.setdefault('jsonContext', {}).update({h: base64.b64encode(json.dumps(ref, ensure_ascii=False, separators=(',', ':')).encode()).decode()})
```
（`md5` 对**紧凑无空格** JSON 串计算；正文追加时用「/n + 标签：占位符」，append 不覆盖原正文；同一引用可同时写进多个消息节点，jsonContext 按 hash 合并。）

**引用上游「获取单条记录」节点结果字段作消息正文（2026-09-11 实证）**：查询类节点的结果字段作**收件人**已实证（见上「查询类节点结果作收件人」段）；作**正文**引用走同表字段同一套 4 键契约，只换 `nodeId`=上游查询节点 id、`nodeType="search"`——至此 4 键的 `nodeType` 三态齐备：start=`table`、data_add=`plus`、查询节点=`search`。

```python
ref = {'field': <被查表字段model>, 'formTableCode': <被查表 code>,
       'nodeId': <get_one 节点 id>, 'nodeType': 'search'}
cs = json.dumps(ref, ensure_ascii=False, separators=(',', ':'))
h  = hashlib.md5(cs.encode('utf-8')).hexdigest()
a['templateContext'] += '\n标签：{{%s.%s}}' % (h, <字段中文名>)      # 后缀=该字段中文名，同表字段段
a.setdefault('jsonContext', {})[h] = base64.b64encode(cs.encode('utf-8')).decode()
```

- `formTableCode` = **被查询表**的 code（不是流程触发表）；口径与 get_one 节点 formTableList 条目的 `form_{节点id}_{表code}` 同源，与「十四」get_one→`nodeType=search` 取数口径一致。
- 消息节点必须挂在查询节点**之后**；正文追加用「\n + 标签：占位符」，不覆盖原正文；jsonContext 按 hash 合并，可与其他引用源（表字段 4 键 / 运算结果 6 键）**共存于同一消息节点**（同一 `jsonContext` 字典里混合存放即可，键数互不影响）。
- ⛔ **获取多条记录（get_more）的结果字段不支持作消息正文引用**（2026-09-11 用户明确）：多条结果只用于批量更新 / 批量新增 / 传子流程逐条处理，或经「运算-统计条数」（`funType=record`，见「十八」18.2）拿到数量后再引用——**不要给 get_more 写正文占位符**；要引用其中的记录字段时改用 get_one 取单条。

### 8.2 邮件通知（支持抄送）

```python
{
    "type": "notice",
    "name": "邮件通知",
    "attr": {
        "noticeType": "email",
        "noticeTitle": "机会目录已作废",    # 邮件主题（必填）
        "noticeContent": "机会目录已于今日作废，请知悉。",
    },
    "toUserIds": ["user.userId1"],         # 收件人
    "toUserNames": ["客户经理"],
    "copyToUserIds": ["user.userId2"],     # 抄送人（可选）
    "copyToUserName": ["部门经理"],
}
```

---

## 九、添加记录节点（data_add）

自动向指定工作表新增一条记录，也可配合"获取多条记录"节点批量新增。

> ⚠️ **processJson 使用 `attr.formModel`（dict，key=目标字段ID，value=字段值配置对象）**，脚本直接接收 `formModel` 字典（无需转换，直接透传）。

**场景一：新增单条记录（addDataType=1）：**
```python
{
    "type": "data_add",
    "name": "添加一条记录",
    "attr": {
        "addDataType": 1,                              # 1=单条新增
        "noDataType": 1,
        "formType": 2,
        "formTableId": "form_{节点ID}_{formTableCode}",
        "formTableCode": "ding_dan_shen_qing_c5dg",
        "formTableName": "订单申请",
        "formTableSourceTaskId": "",                   # 单条新增时为空
        "formTableSourceNodeType": "",                 # 单条新增时为空
        "expressionType": "delegateExpression",
        "expressionValue": "${addRecordDelegate}",
        "level": "1",
        "formModel": {
            # key=目标字段ID，value=字段值配置（5种类型，见下方）
            "input_xxx": {"variableValue": "input_yyy", "formTableCode": "src_form",
                          "variableName": "来源字段名", "fieldType": "input",
                          "formNodeType": "table", "formNodeId": "start", "formNodeName": "触发节点"},
            "date_xxx": {"formNodeType": "system", "variableValue": "nowDate", "variableName": "当前日期"},
            "money_xxx": {"variableValue": "result", "formTableCode": "function-number",
                          "variableName": "结果", "fieldType": "money",
                          "formNodeType": "function", "formNodeId": "task_fn_id",
                          "formNodeName": "数值运算", "operationMode": "cache", "decimals": 2},
        }
    }
}
```

**场景二：基于 get_more 批量逐条新增（addDataType=2）：**
```python
{
    "type": "data_add",
    "attr": {
        "addDataType": 2,                              # 2=批量逐条新增
        "formTableSourceTaskId": "task_get_more节点ID",
        "formTableSourceNodeType": "getMore",
        "formTableSourceCode": "src_sub_form_code",    # getMore 的源表编码
        "formTableSourceGetDataType": 1,
        "formTableSourceId": "form_{getMore节点ID}_{src_form_code}",
        # ... 其他同场景一
    }
}
```

**formModel 值的 formNodeType 枚举：**

| formNodeType | 说明 |
|---|---|
| `table` | 来自 start 节点（工作表事件触发） |
| `search` | 来自 data_get_one 查询结果 |
| `getMore` | 来自 data_get_more 多条数据（逐条引用） |
| `function` | 来自运算节点，`variableValue="result"` |
| `plus` | 来自上游 data_add 节点的新增主键（`variableValue="_id"`） |
| `system` | 系统变量（如 `"nowDate"` 当前日期） |

**formModel 值类型（5 种，value 形态：）**

| 类型 | 写法 | 示例 |
|---|---|---|
| ① 固定值 | 目标字段 model 直接对应**纯字符串/数值**（radio/select 填选项文案） | `"radio_xxx": "成交客户"` |
| ② 引用表字段 | formNodeType=`table`/`search`/`getMore` 的变量对象（见上方场景一） | `{"variableValue": "input_yyy", ..., "formNodeId": "start"}` |
| ③ 系统变量 | formNodeType=`system` | `{"formNodeType": "system", "variableValue": "nowDate", "variableName": "当前日期"}` |
| ④ 运算结果 | formNodeType=`function`，`variableValue="result"` | `{"variableValue": "result", ..., "formNodeType": "function", "operationMode": "cache"}` |
| ⑤ 上游新增主键 | formNodeType=`plus`，`variableValue="_id"` | 配合 getType=4 的 data_add/get_more 引用 |

> ⚠️ **固定值不要写成 `{"funText": "成交客户", "fieldType": "radio"}`**：funText+funContext 形态是**变量拼接**（`{{占位符}}` 内嵌）的写法，radio/select 状态字段按此写不会写入值。实测：data_add 中 radio 固定值写纯字符串文案即生效（详见 gotchas §38）。

> **formTableList 中该节点的 nodeType 为 `"plus"`**（不是 `"data_add"`），`addDataType` 也会记录在其中。

---

## 十、删除记录节点（data_delete）

自动删除工作表中的某条记录，删除对象可以是触发表单记录、get_one 查回的单条记录、get_more 返回的多条记录。

```python
# 场景1：删除触发表单自身记录（formTableSourceNodeType="table"）
{
    "type": "data_delete",
    "name": "删除记录",
    "attr": {
        "formType": 2,
        "formModel": {},                               # 固定空对象
        "formTableId": "form_start_{formTableCode}",  # 来源节点的 formTableId
        "formTableCode": "ke_hu_shen_qing_co38",
        "formTableName": "客户信息",
        "formTableSourceTaskId": "start",
        "formTableSourceNodeType": "table",            # start节点用 "table"
        "expressionType": "delegateExpression",
        "expressionValue": "${deleteRecordDelegate}",
        "level": "1"
    }
}

# 场景2：删除 get_one 查回的单条记录（formTableSourceNodeType="search"）
{
    "type": "data_delete",
    "attr": {
        "formTableId": "form_{get_one节点ID}_{formTableCode}",
        "formTableSourceTaskId": "task_get_one节点ID",
        "formTableSourceNodeType": "search",           # get_one 用 "search"
        "expressionValue": "${deleteRecordDelegate}",
    }
}

# 场景3：删除 get_more 返回的所有多条记录（formTableSourceNodeType="getMore"）
{
    "type": "data_delete",
    "attr": {
        "formTableId": "form_{get_more节点ID}_{formTableCode}",
        "formTableSourceTaskId": "task_get_more节点ID",
        "formTableSourceNodeType": "getMore",          # get_more 用 "getMore"
        "formTableSourceGetDataType": 1,               # getMore 时必须有此字段
        "expressionValue": "${deleteRecordDelegate}",
    }
}
```

---

## 十一、更新流程参数节点（upvariable / data_update_variable）

在流程中定义并更新一个临时参数，后续节点（尤其是分支条件）可引用该参数值。

**场景示例：** 统计销售合同数量后，将数量存入流程参数 `contract_count`，再用分支节点判断是否大于 0。

### 11.1 第一步：在触发节点定义流程参数

在 `start` 节点的 `attr.inputParams` 中声明参数：

```python
# processJson 中 start 节点 attr 里添加
"inputParams": [
    {
        "field": "contract_count",    # 参数标识（变量名）
        "columnName": "合同数量",      # 显示名称
        "fieldType": "number",        # text / number / date
        "val": 0                      # 初始值
    }
]
```

> ⚠️ **`columnName` 必须写，且变量名建议直接用中文并与它同值**（用户 2026-09-10 定论）：只写 `field` 时设计器「本流程参数」列表**退回显示英文标识**（`[数字] totalSubsidy`）——参数其实在、绑定也对，但使用者会以为没生成。`start.attr.inputParams` 与根 `variableList` 两处声明同理；脚本节点 `execution.setVariable('总补贴金额', …)` 写中文变量名可直接运行（Groovy 支持中文标识符）。四处同名完整模板见 create-flow.md「组合 J 变体」+ gotchas #83。

### 11.2 第二步：配置更新流程参数节点

`updateVariable` 数组中每项支持两种赋值方式：

**方式一：从表单字段取值（type: "variable"，默认）**

```python
{
    "type": "upvariable",
    "name": "更新客户名称",
    "updateVariable": [
        {
            "field": "name",              # 流程参数字段名
            "compType": "input",          # 参数类型：input / number / date
            # type 省略时默认 "variable"
            "valueType": 2,               # 2 = 从表单字段取值
            "val": {
                "variableValue": "input_1775629274119_420857",  # 来源表单字段 ID
                "formTableCode": "ke_hu_shen_qing_co38",        # 来源表单 code
                "variableName": "客户名称",
                "formNodeType": "table",
                "formNodeId": "start",
                "formNodeName": "工作表事件触发"
            }
        }
    ]
}
```

**方式二：固定日期赋值（type: "date"）**

```python
{
    "type": "upvariable",
    "name": "设置生日",
    "updateVariable": [
        {
            "type": "date",               # 固定日期，val 为 ISO 字符串，无 valueType
            "field": "birthdate",
            "compType": "date",
            "val": "2026-04-14T09:07:44.076Z"
        }
    ]
}
```

> 旧格式 `variableFields` 仍兼容，但推荐使用 `updateVariable`。

### 11.3 第三步：在分支节点中引用流程参数

在 `exclusive`/`inclusive` 的条件中，将工作表选为 `"流程参数"`，字段选 `contract_count`：

```python
{
    "type": "exclusive",
    "name": "判断合同数量",
    "conditionNodes": [
        {
            "name": "有合同",
            "isDefault": False,
            "priorityLevel": 1,
            "conditions": [
                {
                    "rule": "gt", "ruleName": "大于",
                    "field": "contract_count",     # 流程参数名
                    "columnName": "合同数量",
                    "val": 0, "type": "number",
                    "valueType": "1",
                    # formTableCode 选 "_variable_"（流程参数表）
                }
            ],
            "nodes": [...]
        },
        {"name": "无合同", "isDefault": True, "nodes": [...]}
    ]
}
```

> ⚠️ **条件行 `field` = 流程参数名，`columnName` 写中文显示名**（便于设计器核对）；`branchForm` 与 `formTableCode` 均填 `_variable_`、`formNodeId='processVariable'`、`formNodeType='variable'`。**脚本节点 `setVariable` 写入的变量同此形态**——脚本节点**没有** function-* 虚拟表，勿套 4.4.1 的 function 形态（gotchas #59）。实测模板见 create-flow.md「组合 J 变体」+ gotchas #83。

---

## 十二、获取单条记录节点（get_one / data_get_one）

从工作表查询一条数据，供后续节点使用（更新/删除/字段赋值）。

**获取方式：**
- `1` — 从工作表直接查询单条（可配筛选条件和排序）
- `2` — 从多条数据节点中取单条
- `3` — 从关联字段（关联记录/子表）取单条

**场景示例：** 《销售合同》新增时，从《机会目录》获取关联记录，将机会状态改为"已签订"。

```python
{
    "type": "get_one",              # builder 配置层写 get_one；落库/设计器真实 type 为 data_get_one（脚本自动转换）
    "name": "获取机会记录",

    # 获取方式（1=从工作表, 2=从多条数据节点, 3=从关联字段）
    "getType": 1,

    # getType=1 时：目标工作表
    "formTableCode": "ji_hui_mu_lu",
    "formTableName": "机会目录",

    # 筛选条件（可选）
    "conditions": [
        {
            "rule": "eq", "ruleName": "等于",
            "field": "customer_id", "columnName": "客户ID",
            "val": "触发表单的客户ID字段",
            "type": "text"
        }
    ],

    # 排序（可选，省略则随机取一条）
    "orderField": "create_time",
    "orderType": "desc",           # asc / desc

    # 未查到数据时的处理方式（界面项名「未获取到数据时」；本键为 builder 配置层入参，
    # 落库写 attr.noDataType——设计器前端只认该键；2026-09-15 设计器源码实证）
    # 1 = 继续执行（之后节点使用本节点对象或数据时跳过执行）
    # 2 = 在工作表中新增记录后继续执行（仅 selectType=1 可选，选中后需在面板配置新增记录表单）
    # 3 = 中止流程，或继续执行查找结果分支
    # 未显式选择时该属性默认存 0
    "emptyAction": 1,
}
```

> ⚠️ **触发表单通过「关联记录」控件选择目标表记录时**（如订单.客户 → 客户表），条件 field 必须用目标表主键 **`_id`**，不能按业务字段（客户名称）匹配——link-record 存的是目标记录主键 id；val 引用触发表单的关联字段值。`emptyAction=3` 可配合紧邻的「数据判断分支（databranch）」做查到/查不到分流（枚举见十二节）。完整示例见 create-flow.md「组合 D」，反例见 gotchas.md §37（真实 processJson 中查询条件序列化在 `attr.searchFieldGroup[].queryItems[]`，不是顶层 conditions）。

**getType=3（从关联字段获取）：**
```python
{
    "type": "get_one",
    "name": "获取关联机会",
    "getType": 3,
    "sourceTaskId": "start",        # 从哪个节点获取关联字段
    "relationField": "opportunity", # 关联字段ID
    "formTableCode": "ji_hui_mu_lu",
    "formTableName": "机会目录",
    "emptyAction": 0,
}
```

---

## 十三、获取多条记录节点（get_more / data_get_more）

从工作表查询多条数据，可用于批量更新、批量新增、传给子流程逐条处理。

**获取方式（getType/selectType）：**
- `1` — 从工作表直接查询多条（`formTableCode` + 筛选条件）
- `3` — 从单条记录获取其关联记录（子表/关联记录字段），`formTableSourceNodeType` 自动推断：source=start→"table"，其他→"search"
- `4` — 从新增节点（data_add）获取刚新增的多条记录，`formTableSourceNodeType` 自动设为 "plus"

**取数策略（`attr.getDataType`，界面项「获取数据并缓存 / 每次使用实时获取」）：** `1`=获取数据并缓存（默认，执行到本节点时取数并缓存）；`2`=每次使用实时获取（下游每次用到时实时查询最新数据）。条数上限 `attr.limitNum`（0=不限；界面显示「限制数量」）。（2026-09-16 设计器源码实证）

**场景示例：** 采购单新增时，获取其《采购明细》子表数据，批量添加到《入库明细》。

```python
# getType=3：从单条记录获取关联记录
{
    "type": "get_more",
    "name": "获取采购明细",
    "getType": 3,                       # ⚠️ 真实值是 3，不是 2

    "sourceTaskId": "start",           # 数据源节点（触发表单/get_one节点ID）
    "relationField": "cai_gou_ming_xi", # 关联字段ID（子表/关联记录字段key）
    "formTableCode": "sub_table_xxx",   # 关联子表/关联表的 formTableCode
    "formTableName": "采购明细",

    # 排序（可选）
    "orderField": "",
    "orderType": "asc",

    # 限制条数（0=不限制）
    "limitCount": 0,

    # 获取策略
    # "cache"     = 执行到此节点时缓存数据（推荐，数据量大时用）
    # "realtime"  = 每次使用时实时查询最新数据
    "fetchMode": "cache",
}

> ⚠️ **selectType=3 存储契约（2026-09-04 实证——上面简写只是 config DSL，落库与设计器 UI 读的都是 attr 形态）**
> `build_process_json` 把简写平移进 attr 后会得到 UI 错乱 JSON：`attr.formTableCode` 成了**目标表**、缺 `linkFormTableCode/Name` → 设计器打开该节点时「节点对象」「关联字段」下拉为空/错位。**规范 attr**：
> - `attr.formTableCode/Name/Id` = **源表**（记录从哪条来；源=start 时 `formTableId=form_start_{源表code}`）
> - `attr.linkFormTableField` = 源表上 many link 的 model
> - `attr.linkFormTableCode/Name/Type(=1)` = **关联目标表**（返回的记录表）
> - `attr.selectType=3` + `formTableSourceTaskId` + `formTableSourceNodeType`（源=start→`"table"`，其它源→`"search"`）+ `getDataType=1` + `level`
> - 全部键只放 attr，**顶层零杂键**（`getType/sourceTaskId/relationField` 仅存在于 config DSL，落库必清）
> - `formTableList` 的 getMore 条目：`formTableCode/Name`=目标表、`formTableMainCode`=源主表、`formTableId=form_{节点id}_{目标表code}`、`formTableType=1`、`selectType=3`
> - ⚠️ **attr 必须带 delegate 键**：`expressionType:"delegateExpression"` + `expressionValue:"${getMoreRecordDelegate}"`（位置同「三」data_update 的 `${updateRecordDelegate}`）——外科重写若整块覆盖 builder 原 attr 而漏了这两键，deploy 报 `flowable-servicetask-missing-implementation`（2026-09-04 重建「更新单价」实测：builder 平移产物本来带 delegate 键，整块替换时被抹掉，补回后发布成功）
> 建流流程：build → 按此契约**外科重写该节点 attr**（节点 id/childNode 不动，delegate 键必须保留/补回）→ save → deploy。
> **下游 data_update 引用此 getMore 时**：`attr.formTableSourceNodeType="getMore"` + `attr.formTableSourceGetDataType=1`（不是 "search"），否则批量更新静默无效；见「三、更新记录节点」数据来源速查。

# getType=4：从 data_add 节点获取刚新增的记录
{
    "type": "get_more",
    "name": "获取刚新增订单明细",
    "getType": 4,                       # ⚠️ 真实值是 4
    "sourceTaskId": "task_data_add节点ID",
    "formTableCode": "sub_table_xxx",
    "formTableName": "订单明细",
}

# getType=1：从工作表直接查询
{
    "type": "get_more",
    "name": "获取待处理订单",
    "getType": 1,
    "formTableCode": "order_table",
    "formTableName": "订单",
    "conditions": [{"rule": "eq", "field": "status", "val": "待处理", "type": "select"}],
    "fetchMode": "cache",
}
```

---

## 十四、获取单个系统人员/部门/角色（get_one_sysinfo / data_get_udr_one）

从工作表的用户/部门/角色组件，或系统组织架构中，获取一条人员/部门/角色数据，供后续节点使用。

**可获取的属性：**
- 人员：用户标识、姓名、电话、邮箱、工号、性别
- 部门：部门ID、部门名称、机构编码
- 角色：角色ID、角色名称、角色编码

**场景示例：** 合同签订后，获取"合同签订人"的手机号，更新到"签订人手机号"字段。

**getType 枚举：**

| getType | selectType | 说明 | 关键参数 |
|---------|-----------|------|---------|
| `user_field` | 1 | 从表单用户字段获取 | `fieldIds`（用户组件字段key） |
| `dept_field` | 2 | 从表单部门字段获取 | `fieldIds`（部门组件字段key） |
| `role_field` | 3 | 从表单角色字段获取 | `fieldIds`（角色组件字段key） |
| `org_user` | 4 | 从组织架构查询用户 | `conditions`（筛选条件） |
| `org_dept` | 5 | 从组织架构查询部门 | `conditions`（筛选条件） |
| `org_role` | 6 | 从组织架构查询角色 | `conditions`（筛选条件） |

```python
# 方式一：从表单用户组件字段获取（getType=user_field/dept_field/role_field）
{
    "type": "get_one_sysinfo",
    "name": "获取签订人信息",
    "getType": "user_field",           # 从用户字段取
    "sourceTaskId": "start",           # 数据源节点ID
    "fieldIds": ["create_by"],         # 工作表中的用户/部门/角色组件字段key（列表）
    # sourceField 也可以接受单个字符串，兼容旧写法
    "conditions": [],
    "emptyAction": 0,                  # 1=继续执行 / 2=新增记录后继续 / 3=中止或进查找结果分支（完整枚举见十二节）
}

# 方式二：从组织架构查询（getType=org_user/org_dept/org_role）
{
    "type": "get_one_sysinfo",
    "name": "从组织查询用户",
    "getType": "org_user",
    "conditions": [                    # 按用户属性筛选，空=取第一条
        {"rule": "eq", "ruleName": "等于", "field": "realname",
         "columnName": "姓名", "val": "张丽", "type": "text"}
    ],
    "emptyAction": 0,
}
```

> ⚠️ **content / tenantId 落库契约（2026-09-09 用户 UI 实测纠正）**：节点**顶层 `content` = 画布卡片底部来源行**，UI 原生必写 `工作表 "<attr.formTableName>"`（selectType 1-3=来源工作表名；4-6=用户表/部门表/角色表）。构建器常落成 getType 码（卡片显示英文）或缺 content（显示「设置此节点」），且 `attr.tenantId` 可能残留生成环境示例值——save 前自愈：`node['content'] = f'工作表 "{attr.formTableName}"'`、`node['attr']['tenantId'] = 当前登录租户`。⚠️ 经 builder 生成的**单数** udr 节点还可能连 `attr.formTableName` 都不落（有 formTableCode 无名），content 公式会退化成 `工作表 ""`——自愈时先补 `attr.formTableName = 来源工作表中文名` 再算 content（2026-09-09 实证；UI 手配保存后三项原样留存）。完整修正见《example/获取单个用户示例.md》「5. ⚠️ content / tenantId 落库修正」。

---

## 十五、获取多个系统人员/部门/角色（get_more_sysinfo / data_get_udr_more）

从组织人员/部门/角色中获取多条数据，通常配合子流程逐条处理。

**场景示例：** 定时每天凌晨1点从系统用户中同步人员信息至《员工档案》（有则更新，无则新增）。

```python
{
    "type": "get_more_sysinfo",
    "name": "获取系统用户列表",

    # 获取来源："org_user"=组织用户, "org_dept"=组织部门, "org_role"=组织角色
    "getType": "org_user",

    # 筛选条件（按人员属性过滤，可选）
    "conditions": [
        {
            "rule": "eq", "ruleName": "等于",
            "field": "status",          # 人员属性字段
            "columnName": "状态",
            "val": "1", "type": "text"
        }
    ],
}
```

> **与子流程结合：** `get_more_sysinfo` 获取多条数据后，添加"子流程"节点选择该节点为数据源，可设置并行/串行对每条人员数据逐条执行子流程。

---

## 十六、意见分支（opinion / suggest）

审批人在处理任务时**手动选择**走哪个分支，分支名称即审批界面的按钮名称。

> **约束：** 必须紧跟在审批节点（approver）之后使用，且上游审批节点 `attr.approvalEnabled` 必须为 `true`（默认 False；不开则设计器「意见分支」按钮灰置，分支不生效）。

**场景示例：** 销售经理审批时，由其手动决定走"总监审批"还是"总经理审批"分支。

```python
{
    "type": "opinion",
    "name": "意见分支",
    "conditionNodes": [
        {
            "name": "总监审批",        # 分支名 = 审批界面按钮名
            "nodes": [
                {"type": "approver", "name": "总监审批", "approverGroups": [...]}
            ]
        },
        {
            "name": "总经理审批",
            "nodes": [
                {"type": "approver", "name": "总经理审批", "approverGroups": [...]}
            ]
        }
    ]
}
```

> **与 exclusive 的区别：** exclusive 根据字段值自动判断；opinion 由审批人手动选择。

**手动构建真实 processJson 模板**（改已有流程插 suggest 时用；新建走 builder 的 `type: "opinion"` 即可）：

```python
ts = int(time.time() * 1000)
suggest_id = f'suggest_{ts}001'      # 网关 id 只能用 suggest_ 前缀，用 Gateway 前缀保存报 mxGraph NPE（gotchas #35）
suggest_node = {
    'id': suggest_id,
    'pid': '<上游审批节点 id>',
    'name': '意见分支',
    'type': 'suggest',               # 真实类型是 suggest（opinion 是 builder 别名）
    'status': -1,
    'childNode': None,               # 分支汇合后的后续节点
    'addable': True,
    'error': False,
    'conditionNodes': [              # 分支 = 按钮节点（type=数字8、id 前缀 btn）
        {'id': f'btn{ts}002', 'pid': suggest_id, 'name': '同意',   # 分支名 = 审批界面按钮名
         'type': 8, 'attr': {'priorityLevel': 1}, 'status': -1,
         'childNode': None,          # 该分支下游节点挂 childNode，不是 nodes[]
         'addable': True, 'deletable': False, 'error': False},     # 不能带 errorContent（gotchas #7）
        {'id': f'btn{ts}003', 'pid': suggest_id, 'name': '拒绝',
         'type': 8, 'attr': {'priorityLevel': 2}, 'status': -1,
         'childNode': None,
         'addable': True, 'deletable': False, 'error': False},
    ],
}
```

> 按钮节点 attr 只需 `priorityLevel`（int，分支序号）；分支可增删（2~N 个），名称即按钮文案。上游审批节点需 `attr.approvalEnabled=true` 且 `addable=false`（防节点间插入）。

---

## 十七、数据判断分支（data_branch / databranch）

基于 `get_one`（获取单条记录）节点的查询结果，自动分流：有数据走一条分支，无数据走另一条分支。

> **约束：** 必须紧跟在 `get_one` 节点之后，`get_one` 的 `emptyAction` 应设为 `3`（中止流程，或继续执行查找结果分支）。
>
> **真实 processJson type：** `"databranch"`（无下划线）。`"data_branch"`（带下划线）会导致部署失败。
>
> **底层机制：** `get_one` 执行后将结果写入流程变量 `flow_has_data`（`1`=有数据，`0`=无数据），两分支 `content` 固定为 `"${flow_has_data==1}"` / `"${flow_has_data==0}"`，`attr.branchType` 均为 `2`。

**手动构建要点**（不经 builder 时）：网关 id 用 `Gateway` 前缀、type `"databranch"`（无下划线）；两分支为普通条件行（`type:3`、`flow` 前缀 id、`pid`=网关 id、`isDefault:false`、`attr.branchType=2`），`content` 必须是 **EL 表达式原文** `"${flow_has_data==1}"` / `"${flow_has_data==0}"`（写成中文文案部署失败，gotchas #27）；分支下游节点挂 `childNode`。

**场景示例：** 查询《机会目录》是否存在对应记录，有则修改机会状态，无则发送通知提醒。

```python
# 先添加 get_one 节点（emptyAction=3 才能触发数据分支）
{"type": "get_one", "name": "查机会记录",
 "formTableCode": "opportunity", "formTableName": "机会目录",
 "emptyAction": 3},

# 紧接着添加数据判断分支
{
    "type": "databranch",
    "name": "数据判断",
    "conditionNodes": [
        {
            "name": "有数据",
            "nodes": [
                # 有数据时执行：更新机会状态
                {"type": "data_update", "name": "更新机会状态",
                 "updateFields": [{"field": "status", "val": "已签订", "fieldType": "select"}]}
            ]
        },
        {
            "name": "无数据",
            "nodes": [
                # 无数据时执行：发通知
                {"type": "notice", "name": "通知签订人", "attr": {
                    "noticeType": "system", "noticeContent": "未找到对应机会记录，请手动处理"
                }}
            ]
        }
    ]
}
```

---

## 十七-B、审批结果分支（approve_result）

根据上游审批节点的审批结果（通过 / 否决）自动分流。

> **约束：**
> - 必须直接跟在审批节点（approver）之后。
> - 上游审批节点的 `attr.hasResultBranch` 必须设为 `true`，且 `addable` 必须为 `false`（禁止在该节点后手动插入新节点）。
> - `conditionNodes` 固定包含两个分支：通过（`resultVal: "Y"`）和否决（`resultVal: "N"`）。
> - 每个分支的 `attr.approveResultBranch` 为 `true`，`attr.branchType` 为 `2`。

**场景示例：** 经理审批后，通过则进入总监审批，否决则发送系统消息通知。

```python
ts = int(time.time() * 1000)
gateway_id = f"Gateway{ts}"

# 上游审批节点必须开启结果分支
approver_node = {
    "type": "approver",
    "name": "经理审批",
    "attr": {
        "hasResultBranch": True,   # 必须为 True
        # ...其他审批字段
    },
    "addable": False,              # 必须为 False，禁止节点间插入
    "approverGroups": [...]
}

# 紧接着添加审批结果分支（必须手动构建，脚本不支持此类型）
approve_result_node = {
    "id": gateway_id,
    "pid": approver_node["id"],    # ⚠️ 必须填上游审批节点的 id，否则服务端报 getPid() null
    "name": "审批结果分支",
    "type": "approve_result",
    "status": -1,
    "addable": True,
    "attr": {"level": "2"},        # level 为字符串
    "childNode": None,             # 两分支汇合后的后续节点（通常为 None）
    "conditionNodes": [
        {
            "id": f"flow{ts}001",
            "pid": gateway_id,     # ⚠️ 必须填 gateway_id，否则服务端报 getId() null
            "name": "通过",
            "isDefault": False,
            "type": 3,
            "status": -1,
            "addable": True,
            "deletable": False,
            "error": False,
            "errorContent": None,
            "content": None,
            "childNode": None,     # 通过分支的子节点（下游节点放这里，而非 nodes[]）
            "attr": {
                "branchType": 2,
                "priorityLevel": 1,
                "conditionGroup": [],
                "showPriorityLevel": True,
                "approveResultBranch": True,
                "resultVal": "Y"   # Y = 通过
            }
        },
        {
            "id": f"flow{ts}002",
            "pid": gateway_id,     # ⚠️ 必须填 gateway_id
            "name": "否决",
            "isDefault": False,
            "type": 3,
            "status": -1,
            "addable": True,
            "deletable": False,
            "error": False,
            "errorContent": None,
            "content": "",
            "childNode": None,     # 否决分支的子节点
            "attr": {
                "branchType": 2,
                "priorityLevel": 2,
                "conditionGroup": [],
                "showPriorityLevel": True,
                "approveResultBranch": True,
                "resultVal": "N"   # N = 否决
            }
        }
    ]
}

# 将 approve_result 插入审批节点之后
approver_node["childNode"] = approve_result_node
```

> **⚠️ 分支内手动子节点(2026-09-04 实测):** 通过/否决分支 `childNode` 里的 data_update/data_add 等**手动 dict** 必须在其 `attr` 内补 `expressionType: "delegateExpression"` + `expressionValue: "${updateRecordDelegate}"`(各类型委托名见 gotchas「手动构建 ServiceTask 必须含委托表达式」表),否则 deploy 报 `flowable-servicetask-missing-implementation`。approve_result 网关本身只需 `attr.level`(生产值 "1.500";上游 approver attr.level="1.000")。

> **⚠️ 手动子节点综合实测补充(2026-09-04,buttonEvent+approve_result+edit+message 全链跑通):**
> 1. **分支内手动子节点必须带顶层 `pid`=所属分支 id**(如 `flow{ts}001`),网关与分支的 pid 按本模板填,否则保存 500 `getPid() null`。
> 2. **手动 edit(填写)节点 attr 必须补 `isSequential:false`**(顺带 completionCondition:null/approvalMethod:1/sameMode:1),否则保存 500 `ChildAttr.getIsSequential() is null`——报错常被误判成 approver,实际 approver 的 attr 由 builder 全键生成,不用手写。
> 3. **画布浮出「删除/取消」操作菜单 = 子节点顶层 `deletable` 写成 True**。⚠️ **2026-09-10 更正**：旧表述「`addable/deletable` 写成 True **且无 `content`**」两处都不准——实测 API 插入的 edit 节点**带非空 content 仍复现**，且同流程原生节点多为 `addable:true / deletable:false` 从不浮出，故触发键是 **`deletable`**、与 `content` 是否为空无关，`addable` 也不是诱因。链上节点生产值 = `addable:true`（保留「＋」）+ **`deletable:false`** + `content` 概要文案(edit 写**填写人姓名**,对齐 approver 的 content=人名;message_system 写内容文本)。否则设计器一打开就在节点上浮出操作菜单,用户必投诉。

> ⚠️ **2026-09-15 补充：`content` 为空不是「浮出菜单」那个问题，而是会让节点卡片显示「设置此节点」。**
> 实测（考勤应用 6 条流程）：`build_process_json` 建的 edit 节点 `content` 默认是**空串**，设计器画布上该节点卡片渲染成灰色的「**设置此节点**」未配置占位，用户一眼就以为流程没配好（同一张盘上另有一条手工建的同类节点显示正常，用户据此指出「手动的就没有」）。
> 对照：手工在界面建的 edit 节点，设计器**自动写入** `content`=填写人姓名，卡片显示「填写人：直接上级」——即**界面自己拼「填写人：」前缀，落库的 content 只放姓名**。
> **正确做法：建 edit 节点时把 `content` 写成填写人姓名**（如 `'直接上级'`、`'部门主管审批人'`、`'姓名'`）；表达式的填写人写语义名（如 `${applyUserId}` → `'发起人'`）。改已有流程时整单 `query_flow` → 改 `childNode.content` → `save_flow(flow_id=, update_count=)` → `deploy_flow`。
> 4. **人员显示名 vs 身份**:approver/edit 的 group 里 `approverIds` 存 username(admin),`approverNames` 必须存**显示名/真实姓名(管理员)**,UI 与画布按 names 渲染;names 填 username 时界面显示 admin 不翻译。group 键位照生产补全(levelMode/approverId/approverName 空串/dept*/role*/post*/expressions* 空数组)。edit 顶层另加 approverType/assigneeType/approvalMode。
> 5. edit 面板「指定填写表单」恒显示 `form_start_{code}` 原始值(UI 手选同款),非 bug;落库键对即可:attr.formTableId=form_start_{code} + formTableCode + formTableName + formTableSourceTaskId=start + formTableSourceNodeType=table。
> 6. edit 字段权限:**只能**调 `/act/process/extActProcessNodePermission/saveOrUpdateBatch`(每字段 ruleType=1+2 两条,必填 required:true,status 用字符串,实测 200 生效)。节点内 `privileges` **不参与权限**——2026-09-16 受控实验:只写它时 save/deploy 全绿、权限 API 该节点 0 条;用 API 写完立刻 2 条。别再「两套都写」,那只是白写一份。

**真实 processJson 关键字段（实测 JSON 实证）：**

| 字段 | 说明 |
|---|---|
| `type` | `"approve_result"` |
| `id` | `"Gateway"` 前缀 + 时间戳，如 `"Gateway968400087229308928"` |
| `pid` | ⚠️ **必填**：上游审批节点的 `id`，缺失报 `getPid() null` |
| `status` | 固定 `-1` |
| `attr.level` | 字符串，如 `"2"` |
| `addable` | 网关节点本身可为 `true`；上游审批节点必须为 `false` |
| `conditionNodes[].id` | ⚠️ **必填**：`"flow"` 前缀 + 时间戳，缺失报 `getId() null` |
| `conditionNodes[].pid` | ⚠️ **必填**：gateway 节点的 `id` |
| `conditionNodes[].isDefault` | 固定 `false` |
| `conditionNodes[].type` | 固定 `3` |
| `conditionNodes[].status` | 固定 `-1` |
| `conditionNodes[].addable` | 固定 `true` |
| `conditionNodes[].deletable` | 固定 `false` |
| `conditionNodes[].error` | 固定 `false` |
| `conditionNodes[].errorContent` | 固定 `null` |
| `conditionNodes[].content` | 通过分支为 `null`，否决分支为 `""` |
| `conditionNodes[].childNode` | 分支内的子节点（非 `nodes[]`） |
| `conditionNodes[].attr.approveResultBranch` | 固定 `true` |
| `conditionNodes[].attr.resultVal` | `"Y"` = 通过，`"N"` = 否决 |
| `conditionNodes[].attr.branchType` | 固定 `2` |

---

## 十八、运算节点（operation / function）

对数值/多条数据/文本/日期等进行计算，计算结果可供后续节点（更新记录、流程参数、分支条件）引用。

> **底层实现：** 全部 5 种运算类型均使用 `${functionDelegate}` 委托表达式执行。

支持五种运算类型：

| funType（脚本+前端统一用此值） | 说明 |
|---|---|
| `number` | 数值运算（四则运算表达式），用 `formula` 或 `funFields` 配置 |
| `record` | 统计 get_more 节点数据条数，用 `sourceTaskId` 指向 get_more 节点 |
| `fun` | 函数计算（CONCAT/IF/SUM 等），用 `formula` 或 `funFields` 配置 |
| `date` | 日期加减（+10Y/-3M 等），需在 `attr` 中提供 `dateFieldVal`+`dateFunctionFormat` |
| `date-diff` | 时间差，需在 `attr` 中提供 `dateFieldVal`+`dateFieldEndVal`+`dateFunctionFormat` |

> ⚠️ **funContext hash 与中文名（2026-09-08 实测，config 层详见 `example/运算节点示例.md`）：**
> 条目 hash 前端规则 = `md5(规范 8 键条目 JSON 的 UTF-8 原文, 紧凑序列化)`，键序固定
> field/formTableCode/formNodeId/formNodeType/variableValue/formNodeName/tableText/fieldText（**无 variableName**）。
> 建 number/fun 节点时 config 必须带 `fieldNames: {字段model: 中文名}`，否则 `fieldText` 为空 → 设计器显示字段 key；
> 用其他 hash 规则（`md5(字段ID)` / `ensure_ascii=True` 转义）算出的 key，前端展示公式时按己方规则重算匹配不上 → 回退显示 `{{hash.字段}}` 原文。
> ⚠️ **公式引用运算节点结果（非表字段）的条目是 10 键**（2026-09-09 UI 样本逐字节确认）：8 键基础上在 `formNodeName` 与 `tableText` 之间多 `operationMode`/`decimals` 两键——`{"field":"result","formTableCode":"function-{funType}","formNodeId":<运算节点id>,"formNodeType":"function","variableValue":"result","formNodeName":<运算节点名>,"operationMode":<跟随来源节点模式>,"decimals":2,"tableText":<运算节点名>,"fieldText":"结果"}`，funText 占位符后缀 `.result`、content 形如 `ABS(时长-结果)`。⚠️ canonical 内 `operationMode` **跟随来源运算节点的模式**（date/date-diff/number/fun 来源→"cache"，record 来源→"everyTime"——两个 UI 样本分别实证），不是恒 cache。按 8 键算 hash 必不匹配 → 公式框回退 `{{hash.result}}` 原文（gotchas #60）。API 构造与 UI 手配重存产物逐字节一致；仍显示原文时优先排查前端缓存/旧标签页。

### 18.1 数值运算（arithmetic）

对数值/金额字段进行四则运算（+/-/*/÷/括号）。

**场景示例：** 计算合同金额的 3% 作为佣金，发送给签订人。

```python
{
    "type": "operation",
    "name": "计算佣金",
    "operationType": "arithmetic",  # 数值运算
    "formula": "合同金额字段ID * 0.03",  # 数学表达式，支持字段引用和常量
    "sourceTaskId": "start",            # 数据来源节点
}
```

### 18.2 统计数据条数（record）

统计 `get_more` 节点获取到的多条记录的数量，结果为整数。

> **约束：** 需通过 `sourceTaskId` 指向流程中某个 `get_more` 节点 ID，可引用任意位置的 `get_more` 节点。

> ⚠️ **funType="record" 的 funContext 与其他类型不同**：是普通 dict（不是 URL 编码的 hash 格式），脚本已自动处理，用户无需关心。`operationMode` 自动设为 `"everyTime"`。

**场景示例：** 统计关联销售合同数量，判断是否大于 0 再决定后续逻辑。

```python
# 第一步：先获取多条记录
{"type": "get_more", "name": "获取多条数据",
 "getType": 1, "formTableCode": "contract", "formTableName": "销售合同"},

# 第二步：统计条数（funType=record）
{
    "type": "operation",
    "funType": "record",               # ⚠️ 用 funType 而非 operationType
    "name": "统计销售合同数量",
    "sourceTaskId": "task_get_more节点ID",
    "formTableCode": "contract",
    "formTableName": "销售合同",
    "getDataType": 1,                  # 与 get_more 节点一致，默认 1
}
```

> 统计结果常配合 `upvariable` 存入流程参数，再用 `exclusive` 分支判断结果是否大于 0。⚠️ 分支条件也可**直接引用运算节点结果**（field=`result` + branchForm=function-{funType}），无需中转流程参数——完整形态见「四」4.4.1 / gotchas #59。

### 18.3 函数计算（function）

通过内置函数（数学/日期/文本/逻辑）对字段值进行处理，生成新的结果值。

**场景示例：** 从机会编号中取最右 4 位，拼接新的编号格式。

```python
{
    "type": "operation",
    "name": "函数计算",
    "operationType": "function",  # 函数计算
    "sourceTaskId": "start",
    # functionExpr 为函数表达式，可嵌套；字段用字段ID引用
    "functionExpr": "CONCAT('OPP-', RIGHT(opportunity_no_field, 4))",
}
```

**内置函数库（依据设计器前端「函数计算」面板目录数据整理，共 35 个）：**

函数面板左侧按页签分组：常用函数 / 数学函数 / 日期函数 / 文本函数 / 逻辑函数 / 高级函数。「常用函数」= IF、SUM、AVERAGE、CONCAT、DATEADD 共 5 个（同时显示在各所属分类页签）；「高级函数」目录为空，页面展开无内容。函数名大写，文本字面量带引号，参数可嵌套函数。

**数学函数（13 个；SUM、AVERAGE 同时显示在「常用函数」页）：**

| 函数 | 语法 | 说明 | 示例 |
|------|------|------|------|
| SUM | `SUM(数值1,数值2…)` | 求和 | `SUM(10,20,30)` → 60 |
| AVERAGE | `AVERAGE(数值1,数值2…)` | 平均值 | `AVERAGE(10,20,30)` → 20 |
| MAX | `MAX(数值1,数值2…)` | 最大值 | `MAX(10,20,30)` → 30 |
| MIN | `MIN(数值1,数值2…)` | 最小值 | `MIN(10,20,30)` → 10 |
| PRODUCT | `PRODUCT(数值1,数值2…)` | 乘积 | `PRODUCT(15,4)` → 60 |
| COUNTA | `COUNTA(数值1,数值2…)` | 参数中非空值的个数 | — |
| ABS | `ABS(数值)` | 绝对值 | `ABS(-7)` → 7 |
| INT | `INT(数值)` | 取整（帮助文案称"返回小于等于原数的最接近整数"，示例 `INT(-3.14159265)` → -3，实际更像截断） | — |
| MOD | `MOD(被除数,除数)` | 相除余数 | `MOD(15,4)` → 3 |
| ROUND | `ROUND(数值,位数)` | 按位数四舍五入 | `ROUND(3.14159265,4)` → 3.1416 |
| ROUNDUP | `ROUNDUP(数值,位数)` | 按绝对值增大方向舍入 | `ROUNDUP(3.14159265,4)` → 3.1416 |
| ROUNDDOWN | `ROUNDDOWN(数值,位数)` | 按绝对值减小方向舍入 | `ROUNDDOWN(3.14159265,4)` → 3.1415 |
| NUMBER | `NUMBER(文本)` | 文本等类型转数值（IF 结果为文本型，常配此函数） | `NUMBER('-1')+5` → 4 |

**日期函数（7 个；DATEADD 同时显示在「常用函数」页）：**

| 函数 | 语法 | 说明 | 示例 |
|------|------|------|------|
| DATEADD | `DATEADD(初始日期,计算式,[输出格式])` | 日期加减时间。计算式如 `+8h`、`+1M-12d`，单位 `Y/M/d/h/m`，也可直接加减一个日期字段；第 3 参可选：**1=日期（默认）、2=日期时间** | `DATEADD('2023-05-11 12:23:00','+8h',2)` → 2023-05-11 20:23:00 |
| DATENOW | `DATENOW()` | 当前时间 | `DATENOW()` → 2023-05-11 12:23 |
| DAY | `DAY(日期时间)` | 天数（1~31） | `DAY('2021-5-1')` → 1 |
| MONTH | `MONTH(日期时间)` | 月份（1~12） | `MONTH('2021-5-1')` → 5 |
| YEAR | `YEAR(日期时间)` | 四位年份 | `YEAR('2021-5-1')` → 2021 |
| DATEIF | `DATEIF(开始,结束,格式化方式,[输出单位])` | 两日期/时间间时长。格式化方式：**1=开始00:00~结束00:00（结束当天不计满）、2=开始00:00~结束24:00（结束当天计满一天）**；输出单位 `Y/M/d/h/m`，默认 `d` | `DATEIF('2021-3-8','2021-3-14',2,'d')` → 7 |
| DATEFORMAT | `DATEFORMAT(日期,格式)` | 时间戳/日期转指定格式。格式 `YYYY/MM/DD/HH/mm/ss` 等（moment 写法） | `DATEFORMAT('2022-12-02','YYYY年MM月DD日')` → 2022年12月02日 |

**文本函数（10 个；CONCAT 同时显示在「常用函数」页）：**

| 函数 | 语法 | 说明 | 示例 |
|------|------|------|------|
| CONCAT | `CONCAT(文本1,文本2…)` | 合并文本 | `CONCAT('我是','中国','人')` → 我是中国人 |
| LEFT | `LEFT(原文本,[字符数])` | 从左提取；字符数缺省时从第一个字符起 | — |
| RIGHT | `RIGHT(原文本,[字符数])` | 从右提取 | `RIGHT('我是中国人',3)` → 中国人 |
| REPLACE2 | `REPLACE2(原文本,开始位置,字符数,替换文本)` | 替换指定位置内容（开始位置 1 起算，含被替换字符） | `REPLACE2('+8613534257715',1,3,'')` → 13534257715 |
| TRIM | `TRIM(文本)` | 删除首尾空格 | `TRIM(' 南京 ')` → 南京 |
| CLEAN | `CLEAN(文本)` | 删除所有空格 | `CLEAN('135 3425 7715')` → 13534257715 |
| FIND | `FIND(原文本,开始字符,结束字符)` | 取开始/结束字符之间的内容；两者可空（空=从头/到尾），官方用它截取时长结果的"天" | `FIND('1天23小时15分钟','','天')` → 1 |
| SPLIT | `SPLIT(原文本,间隔符)` | 按间隔符分割 | `SPLIT('HX045-SZ190-NZ021-LS097','-')` → HX045,SZ190,NZ021,LS097 |
| JOIN2 | `JOIN2(数组,间隔符)` | 按间隔符把数组元素拼成文本（间隔符空则逐字符拼） | `JOIN2(部门字段,'-')` → 产品部-销售部-研发部 |
| STRING | `STRING(数值)` | 数值等类型转文本 | `STRING(-1)+STRING(5)` → '-15' |

**逻辑函数（5 个；IF 同时显示在「常用函数」页）：**

| 函数 | 语法 | 说明 | 示例 |
|------|------|------|------|
| IF | `IF(表达式,成立时输出,不成立时输出)` | 条件判断。⚠️ **输出固定为文本类型**，要当数字用须包 `NUMBER()` | `IF(分数>=60,'及格','不及格')` |
| AND | `AND(表达式1,表达式2…)` | 全部成立才 TRUE | — |
| OR | `OR(表达式1,表达式2…)` | 任一成立即 TRUE | — |
| ISBLANK | `ISBLANK(文本)` | 是否为空 | `ISBLANK(年龄)` → TRUE |
| INCLUDE | `INCLUDE(原文本,检索的字符)` | 是否包含指定字符 | `INCLUDE("北京市朝阳区",'朝阳')` → TRUE |

> ⚠️ **此前的"函数举例"文案里出现过 `LEN`、`UPPER`、`LOWER`、`NOW`、`TODAY`、`DATEDIFF`、`DATE_FORMAT`、`NOT` 等名称，均不在本函数目录中**（面板选不出来），生成公式一律以上表为准。

### 18.4 日期加减（date）

对日期字段加减年/月/日/时/分，生成新的日期值。

- `funContext` 自动为 `{}`（脚本 else 分支处理）
- `funText` 格式：`"+10Y"` / `"-3M"` / `"+30D"` / `"+24H"`（+/-数字+单位）
- `dateFieldVal`：变量引用对象（同 data_add formModel 值格式，见下方）
- `dateFunctionFormat`：`{argument, result, end, out}` 配置对象

```python
{
    "type": "operation",
    "funType": "date",
    "name": "为日期加减时间",
    "funText": "+10Y",                 # 加10年，也可 -3M / +30D / +24H 等
    "attr": {
        "dateFieldVal": {              # 起始日期变量引用
            "variableValue": "date_1776162654792_637160",   # 日期字段 ID
            "formTableCode": "ke_hu_shen_qing_co38",
            "variableName": "注册时间",
            "formNodeType": "table",   # 来源类型：table/search/system 等
            "formNodeId": "start",
            "formNodeName": "工作表事件触发"
        },
        "dateFunctionFormat": {
            "argument": "date",        # 输入类型：date / datetime
            "result": "date",          # 输出类型：date / datetime
            "end": "2",
            "out": "d"                 # 输出单位（d=天，H=时等）
        }
    }
}
```

### 18.5 时间差计算（date-diff）

计算两个日期的差值，返回年/月/日/时/分/秒。

- `funContext` 自动为 `{}`，`funText` 自动为 `""`
- 起始/结束日期均为变量引用对象，可以是表单字段或系统变量（`nowDate`）

```python
{
    "type": "operation",
    "funType": "date-diff",
    "name": "时长",
    "attr": {
        "dateFieldVal": {              # 起始日期变量引用
            "variableValue": "date_start_field",
            "formTableCode": "my_form",
            "variableName": "开始日期",
            "formNodeType": "table",
            "formNodeId": "start",
            "formNodeName": "工作表事件触发"
        },
        "dateFieldEndVal": {           # 结束日期（支持系统变量 nowDate）
            "formNodeType": "system",
            "variableValue": "nowDate",
            "variableName": "当前日期"
        },
        "dateFunctionFormat": {
            "argument": "datetime",    # 输入类型
            "result": "datetime",      # 输出类型
            "end": "2",
            "out": "d"                 # 输出单位（d=天，Y=年，M=月，H=时）
        }
    }
}
```

---

## 十九、子流程（subprocess / callActivity）

主流程执行过程中发起另一个独立流程（子流程），子流程执行完毕后再返回主流程继续。

**两种使用场景：**
1. **流程复用** — 多个入口（新增触发/按钮触发）共享同一套审批流程
2. **批量处理** — 配合 `get_more` 对多条记录逐条/并行执行子流程

```python
{
    "type": "subprocess",          # 或 "callActivity"，脚本统一生成 callActivity 类型
    "name": "发起审批子流程",

    # ── 必填：已有子流程信息 ──────────────────────────────────
    # 注意：customProcessId 是数字型 DB ID（不是 processKey 字符串）
    # 先用 query_flow 或直接从系统中查到子流程的 id，再填此处
    "customProcessId": "968466510463016960",   # 子流程的数字 DB ID
    "processName": "子流程名称",                # 显示名称

    # ── 批量处理（配合 get_more）──────────────────────────────
    "sourceTaskId": "task_get_more_id",        # 上游 get_more 节点 ID
    "isMulti": True,                           # 是否多实例（批量时 True）
    "isSequential": False,                     # False=并行，True=串行逐条

    # ── subFormTableObject：来源数据对象（从 get_more formTableList 条目复制，加 isSubStart:True）
    "subFormTableObject": {
        "formTableId":       "form_task_xxx_sub_table_yyy",  # get_more 节点 formTableId
        "nodeId":            "task_get_more_id",
        "nodeName":          "从单条记录获取关联记录",
        "nodeType":          "getMore",
        "formTableCode":     "sub_table_yyy",   # 子表 code
        "formTableName":     "明细表名",
        "formTableMainCode": "main_table_zzz",  # 主表 code
        "formTableType":     1,
        "isSubStart":        True,              # ⚠️ 必须为 True
        "selectType":        3,
        "getDataType":       1,
        "level":             "0.500",
    },
}
```

**批量处理底层机制：**

配合 `get_more` 时，后端生成 `callActivity` 多实例节点，固定传入子流程的变量：

| source | target | 说明 |
|--------|--------|------|
| `applyUserId` | `applyUserId` | 发起人 |
| `dataId` | `dataId` | 主记录 ID |
| `JG_LOCAL_PROCESS_ID` | `JG_SUB_MAIN_PROCESS_ID` | 父流程实例 ID（子流程通过此变量回溯父流程） |
| `handleDataId` | `handleDataId` | 当前循环记录 ID（每次循环对应 get_more 中的一条记录） |

- **Collection 变量命名规律**：`{sourceTaskId}_assigneeDataIdList`（由 get_more 节点自动填充）
- **监听器**：`MiniCallActivityListener`（系统自动添加，无需手动配置）
- **`subFlowSourceInfo`**：子流程 processJson 顶层字段，记录哪些父流程引用了此子流程（系统自动维护）
- **批量场景关键差异**：`callActivity.attr.formTableCode/formTableName` 为 `null`；`formTableId` 和 `subFormTableObject` 指向 get_more 节点子表；子流程 `formTableList[0].nodeType="search"`, `nodeTypeMain="getMore"`

**流程复用示例：**
```python
# 主流程 1（新增触发）
{"type": "subprocess", "name": "机会审批",
 "customProcessId": "968466510463016960",  # 子流程 DB ID（数字型）
 "processName": "机会审批子流程"}

# 主流程 2（自定义按钮触发）
{"type": "subprocess", "name": "机会审批",
 "customProcessId": "968466510463016960",
 "processName": "机会审批子流程"}
# 两个主流程共用同一个审批子流程
```

**批量数据处理示例：**
```python
# 1. 先获取多条联系人（get_more 节点 ID 假设为 "task_get_contacts"）
{"type": "get_more", "name": "从单条记录获取关联记录", "getType": 3,  # ⚠️ 真实值是 3
 "sourceTaskId": "start", "relationField": "contacts_field",
 "formTableCode": "contacts", "formTableName": "联系人"},

# 2. 对每条联系人并行执行子流程
{"type": "subprocess", "name": "子流程",
 "customProcessId": "968466510463016960",   # 子流程 DB ID（数字型）
 "processName": "联系人审批子流程",
 "sourceTaskId": "task_get_contacts",        # 上面 get_more 节点 ID
 "isMulti": True,
 "isSequential": False,                      # False=并行
 "subFormTableObject": {                     # 从 get_more formTableList 条目复制
     "formTableId": "form_task_get_contacts_contacts",
     "nodeId": "task_get_contacts",
     "nodeName": "从单条记录获取关联记录",
     "nodeType": "getMore",
     "formTableCode": "contacts",
     "formTableMainCode": "main_table_code",
     "formTableType": 1,
     "isSubStart": True,
     "selectType": 2,
     "getDataType": 1,
     "level": "1"
 }
}
```

---

## 十九-B、消息服务任务节点（message_*）

区别于通知节点（notice），消息服务任务是后台自动发送的 ServiceTask，由 `${messageDelegate}` 处理。支持 4 种类型：`message_system`（系统消息）、`message`（企业微信）、`message_ding`（钉钉）、`message_email`（邮件）。

### 完整配置（以 message_system 为例，实测 JSON 实证）

```python
{
    "type": "message_system",
    "name": "系统消息",
    "attr": {
        "type": "system",                          # system / wechat_enterprise / dingtalk / email
        "title": "系统消息",                         # 消息标题
        "description": "",
        "expressionType": "delegateExpression",
        "expressionValue": "${messageDelegate}",    # 固定委托表达式

        # ── 接收人 ──
        "receiveType": "user",                      # user=指定用户
        "toUserIds": ["user.admin", "user.jeecg"],  # 用户ID格式: "user.{username}"
        "toUserNames": ["admin", "JEECG演示"],       # 用户显示名
        "toUsers": [],
        "toUserExpression": "",                     # 可选：表达式指定用户

        # ── 消息模板 ──
        # 用 {{hash.字段标签}} 引用表单字段值
        "templateContext": "有面试的人{{b48c8f0542b119e3ef6ce743d68f3625.面试人姓名}}",

        # jsonContext: hash → base64编码的字段映射JSON
        # base64 解码后: {"field":"input_xxx","formTableCode":"jian_li_qyk9","nodeId":"start","nodeType":"table"}
        "jsonContext": {
            "b48c8f0542b119e3ef6ce743d68f3625": "eyJmaWVsZCI6ImlucHV0X3h4eCIsImZvcm1UYWJsZUNvZGUiOiJqaWFuX2xpX3F5azkiLCJub2RlSWQiOiJzdGFydCIsIm5vZGVUeXBlIjoidGFibGUifQ=="
        },

        "level": "2"
    }
}
```

### 模板语法说明

- 用 `{{hash.字段显示名}}` 引用表单字段值
- `hash` 是 `jsonContext` 的 key（MD5 生成），value 是 base64 编码的 JSON
- 解码后的 JSON 结构：`{"field": "字段ID", "formTableCode": "表单编码", "nodeId": "start", "nodeType": "table"}`
- ⚠️ **裸写 `{{字段中文名}}`（不带 hash）= 占位符不解析**（2026-09-16 实测）：消息照发、save/deploy 全绿，但正文里显示的是占位符原文或空白。**两个键要成对写**——正文 `{{<md5>.<字段中文名>}}` + `attr.jsonContext[<md5>] = base64(紧凑JSON)`；只写正文不注册 jsonContext 同样无效。规格里给出的 `{{应聘者姓名}}` 这类**是业务示意，落库必须补 hash 前缀**。
  ```python
  ref = {'field': M[字段中文名], 'formTableCode': 表code, 'nodeId': 'start', 'nodeType': 'table'}
  cs  = json.dumps(ref, ensure_ascii=False, separators=(',', ':'))   # 紧凑、无空格
  h   = hashlib.md5(cs.encode('utf-8')).hexdigest()
  a['templateContext'] += '标签：{{%s.%s}}' % (h, 字段中文名)          # 后缀=字段中文名
  a.setdefault('jsonContext', {})[h] = base64.b64encode(cs.encode('utf-8')).decode()
  ```
  回读复核：解 `jsonContext` 的 base64 → 用 `field` 反查中文名 → 断言正文里存在 `{{<该hash>.<该中文名>}}`。

### 其他消息类型

```python
# 企业微信消息
{"type": "message", "attr": {"type": "wechat_enterprise", ...}}

# 钉钉消息
{"type": "message_ding", "attr": {"type": "dingtalk", ...}}

# 邮件消息（额外支持 copyToUserIds 抄送）
{"type": "message_email", "attr": {
    "type": "email", "sendType": 1,
    "toUserIds": ["user.xxx"], "copyToUserIds": ["user.xxx"], ...}}
```

---

## 二十、互斥分支条件规则补充

### 自定义表达式条件（2026-09-10 用户 UI 创建实证，旧「customExpression」键说法已作废）

设计器「互斥分支 → 分支条件类型 = 自定义」的落库**不是 conditionGroup**：表达式存在**分支节点的 `content` 键**，`attr.branchType` 恒为 **2**、`conditionGroup` 恒为 **[]**，attr 无 branchForm——与字段条件模式（条件分支 branchType=1 + conditionGroup.queryItems）完全不同；区分「条件分支 / 默认分支」只靠 `isDefault`。

真实落库 JSON（流程 startType=manual，表达式引用 start 表字段 model）：

```json
{
    "id": "Gateway1022357062010707968",
    "name": "路由",
    "type": "exclusive",
    "pid": "start",
    "attr": {"level": "1"},
    "conditionNodes": [
        {
            "id": "flow1022357062010707969",
            "pid": "Gateway1022357062010707968",
            "name": "分支1",
            "isDefault": false,
            "type": 3,
            "content": "${input_1788950148201_455954 == '张三'}",
            "attr": {"branchType": 2, "priorityLevel": 1, "conditionGroup": [],
                     "showPriorityLevel": true, "level": "1"},
            "addable": true, "deletable": false, "error": false, "errorContent": "",
            "childNode": null
        },
        {
            "id": "flow1022357062010707970",
            "pid": "Gateway1022357062010707968",
            "name": "其他情况",
            "isDefault": true,
            "type": 3,
            "content": "其他情况进入此流程",
            "attr": {"branchType": 2, "priorityLevel": 2, "conditionGroup": [],
                     "showPriorityLevel": true, "level": "1"},
            "addable": true, "deletable": false, "error": false, "errorContent": null,
            "childNode": null
        }
    ]
}
```

**表达式语法（用户 2026-09-10 确认）：**

- 字段用**模型名（model）**引用（如 `input_1788950148201_455954`），整体包在 `${...}` 内
- **字符串类型的值必须加单引号**：`${input_xxx == '张三'}`；**时间字段（time）也是字符串**：`${time_xxx == '10:30:00'}`
- **数值类型的值不加单引号**：`${number_xxx >= 100}`
- **⚠️ 日期类字段（date，options.timestamp=true）的值写毫秒时间戳数字、不加引号**：`${date_xxx < 1789056000000}`（=2026-09-11 00:00 本地）——写带引号的日期串（`${date_xxx == '2026-09-10'}`）能 save/deploy 但**运行时恒不成立**：字段存储=毫秒，数字 vs 字符串比较必 false（2026-09-10 用户实测确认「日期组件需要时间戳」，同 gotchas #52 存储形态规律）
- 比较运算符：`==` `!=` `>=` `<=` `>` `<`（单等号 `=` 不支持）
- 逻辑连接：并且 `&&`、或者 `||`（如 `${input_xxx == '测试' && number_xxx > 10}`）
- 分支名由用户自定义（不像字段条件模式自动生成「字段+规则+值」）

⚠️ 两套形态勿互套：字段条件模式见 4.5（条件分支 `branchType:1` + `attr.conditionGroup[].queryItems[]` + `attr.branchForm/formTableCode`）；自定义表达式模式 = `content` + `branchType:2` + `conditionGroup:[]`。

### 多条件 AND / OR 组合

`conditionGroup` 中同一组（同一 `queryItems`）的多个条件默认 **AND** 关系；
多个组之间为 **OR** 关系：

```python
# (金额 > 1万 AND 状态=执行中) OR (金额 > 10万)
"conditionGroup": [
    {
        "matchType": "and",
        "queryItems": [
            {"rule": "gt", "field": "amount", "val": 10000, "type": "money"},
            {"rule": "eq", "field": "status", "val": "执行中", "type": "select"},
        ]
    },
    {
        "matchType": "and",
        "queryItems": [
            {"rule": "gt", "field": "amount", "val": 100000, "type": "money"},
        ]
    }
]
```

### 规则下拉白名单按控件族给（2026-09-11 用户 UI 逐族实测）

分支条件（排他/包含网关的 `queryItems[].rule`，以及条件行「规则」选择器）的**可选规则按控件族给**，写库时服务端**不做校验**——写不匹配的 rule 能 save+deploy 成功、回读也一致，只有人打开设计器才看得到异常（下拉里没有该项、值框渲染异常）。实测口径：

| 控件族 | 规则下拉可选 |
|--------|-------------|
| 文本 `input` / `textarea` | 等于、不等于、全模糊、左模糊、右模糊、为空、不为空（**无** 大于/小于/在范围内） |
| 公式 `formula` | **无「在范围内」**（等于可用） |
| 文件 `file-upload` | **仅 为空 / 不为空** |
| 日期 `date` / 时间 `time` / 数值 `number`·`integer`·`money`·`rate`·`slider` | 比较类（`gt`/`ge`/`lt`/`le`…）+ **`range`（在范围内）** |

要点：

- **他表字段 `link-field` 仅「存储数据」模式可作条件**：`options.saveType=="view"`（仅显示）的字段**不可**用作条件（查询条件/分支条件同），服务端不校验、写了照样 save/deploy；要按该语义检索请改用其来源的**关联记录（link-record）**字段（见 gotchas #86）。条件编码另见上表：link-field 的 `type`/`valType` 写 `input`。
- **范围查询只属于日期 / 时间 / 数值族**；文本与公式走等值/模糊类，文件类走空值类（`val=[]`+`name=[]`+`valType=""`）。
- 「表单内每个组件一条分支」类需求**按族分流铺规则**，不要整表统一一种规则（整表统一 = 必然给某些控件写出下拉里没有的项）。
- 日期 `range` 两端仍必须写**毫秒时间戳 int**（见 4.5 / gotchas #52、#77）；时间 `time` 写 `"HH:mm:ss"` 字符串。
- 分支**卡片正文**那行是设计器前端按 `conditionGroup` 原始值现拼的（不读节点 `content`），日期类必然显示毫秒；卡片**标题**读 `name`（可读）。属渲染表现，改 JSON 无效。

---

## 二十一、常用审批人表达式

| 表达式 | 含义 |
|--------|------|
| `${applyUserId}` | 流程发起人 |
| `${applyUserDeptId}` | 发起人所在部门 |
| `${applyUserDeptLeaderId}` | 发起人部门负责人 |

---

## 二十二、触发方式（startType）

startType 枚举值（来源：ExtActProcess.java）：

| startType | 说明 |
|-----------|------|
| `tableEvent` | 工作表事件触发（新增/更新/删除记录时） |
| `manual` | 手动发起（由用户在页面主动提交） |
| `buttonEvent` | 按钮触发（Desform 表单中自定义按钮触发） |
| `timerEvent` | 定时触发（按固定周期执行） |
| `dateFieldEvent` | 按日期字段触发（工作表日期字段到期时执行，**独立类型，非 timerEvent 变体**） |
| `userEvent` | 人员事件触发（入职/离职时） |
| `subEvent` | 子流程事件（由父流程触发，无需手动配置） |

---

### 22.1 工作表事件触发（tableEvent）

记录新增、更新或删除时自动触发流程。

```python
{
    "startType": "tableEvent",
    "formTableCode": "ding_dan_shen_qing_c5dg",
    "formTableName": "订单申请",
    "formTableId":   "form_start_ding_dan_shen_qing_c5dg",
    "titleField":    "input_xxx",      # 标题字段ID，用于流程实例显示名
    "startEventType": "add|update",   # "add" / "update" / "add|update" / "delete"
}
```

---

**触发条件（startCondition）：** tableEvent / timerEvent 支持配置筛选条件，只有满足条件的记录才会触发流程（存在 processJson 的 `attr.startCondition` 中）。

```python
# 触发条件示例：只有"客户类型=个人客户"的记录才触发
# ⚠️ 注意：startCondition 有 id/matchType/queryItems 包装层
"startCondition": [
    {
        "id": "969586911868002304",   # 条件组ID（时间戳随机数）
        "matchType": "",              # 同组内多条件关系：""=AND，"or"=OR
        "queryItems": [
            {
                "rule": "eq", "ruleName": "等于",
                "valueType": "1",                          # "1"=固定值
                "val": "个人客户",
                "name": None,
                "field": "select_1775648798126_168238",    # 字段ID
                "columnName": "客户类型",
                "type": "select", "valType": "select"
            }
        ]
    }
]
```

> `createStartNode`（是否启用「发起人节点」）顶层字段规则：**默认 `false`（不启用）**，builder 读 config 键 `createStartNode`；仅用户明确点名要发起人节点/发起人填写时才传 `true`。旧「`startEventType="add"` → `true`」规则已作废（2026-09-11）。
> `conditionFields`：更新触发时填字段 ID 字符串数组（监控哪些字段变更触发）；新增/删除时为 `[]`。

---

### 22.2 手动发起（manual）

由用户在页面发起申请，无需关联工作表事件。

```python
{
    "startType": "manual",
    # 不需要 formTableCode / formTableId / startEventType
}
```

---

### 22.3 按钮触发（buttonEvent）

Desform 工作表中配置自定义按钮，点击按钮时触发流程。

```python
{
    "startType": "buttonEvent",
    "formTableCode": "合同表单编码",
    "formTableName": "合同",
    "formTableId":   None,          # ⚠️ buttonEvent 中 attr.formTableId 为 null，不是 "form_start_xxx"
    "titleField":    "title_field_id",
    "startEventType": "add|update",
}
```

> 场景示例：合同审批按钮，点击后触发合同审批流程。

---

### 22.4 定时触发（timerEvent）

在指定时间范围内按循环周期自动触发。

**start_attr 关键字段：**

| 字段 | 说明 | 示例 |
|------|------|------|
| `beginDateStr` | 开始执行时间（首次触发时间） | `"2024-05-01 08:00:00"` |
| `endDateStr` | 结束执行时间（循环截止，可为空） | `"2024-12-31 18:00:00"` |
| `timeCycleName` | 循环周期名称 | `"每天"` / `"每小时"` / `"自定义"` |
| `dayValue` | 每月第几天（月循环用） | `1` |
| `hourType` | 小时触发类型（1=固定值，2=范围） | `1` |
| `hourValues` | 固定执行小时列表 | `[8, 18]` |
| `dayValues` | 固定执行日期列表（范围触发） | `[10, 11, 12]` |

**config 顶层字段（timeCycleName="自定义" 时使用）：**

| 字段 | 说明 | 示例 |
|------|------|------|
| `cronExpr` | 自定义 Quartz Cron 表达式（6 字段） | `"0 0 8 * * ?"` |

**循环周期（timeCycleName）与 ISO 8601 时长对照：**

| timeCycleName | ISO 8601 时长 |
|--------------|--------------|
| `"每分钟"` | PT1M |
| `"每小时"` | PT1H |
| `"每天"` | P1D |
| `"每周"` / `"每周三"` / `"周一到周五"` | P7D |
| `"每月"` / `"每月1号"` | P1M |
| `"每年"` | P1Y |
| `"自定义"` | — Quartz Cron，如 `0 0 0-10 * * ?` |

```python
{
    "startType": "timerEvent",
    "beginDateStr": "2024-05-01 08:30:00",   # 开始执行时间
    "endDateStr": "2024-12-31 18:00:00",      # 结束执行时间（可空）
    "timeCycleName": "每天",                   # 循环周期名称
    "nodes": [...]
}

# 自定义 Cron：
{
    "startType": "timerEvent",
    "beginDateStr": "2024-05-01 08:00:00",
    "endDateStr": "2024-12-31 23:59:00",
    "timeCycleName": "自定义",
    "cronExpr": "0 0 8 10-12 * ?",            # Quartz Cron（6 字段）
    "nodes": [...]
}
```

> **场景示例：** 每天早上 8:30 提醒负责人跟进客户。

---

### 22.5 按日期字段触发（dateFieldEvent）

> ⚠️ **`attr.startType` 是 `"dateFieldEvent"`，不是 `"timerEvent"`！** 这是独立触发类型。

根据工作表中某个日期字段的值，在日期前后触发流程。

**start_attr 关键字段：**

| 字段 | 说明 | 示例 |
|------|------|------|
| `triggerField` | 触发日期字段 ID | `"date_1775640531752_255416"` |
| `triggerFieldType` | 字段类型 | `"date"` / `"datetime"` |
| `formTableCode` | 工作表编码 | `"ding_dan_shen_qing_c5dg"` |
| `executeType` | 执行时机 | `1`=到期当天、`2`=到期前、`3`=到期后 |
| `plusDate` | 偏移量，**字符串类型** | `"1"`（提前/延后1天） |
| `plusDateUnit` | 偏移单位（1=分钟 2=小时 3=天） | `3`（天） |
| `executionTime` | 每天执行时刻 | `"01:00"` |
| `cycleType` | 重复类型 | `0`=不重复、`1`=每年、`2`=每月、`3`=每周 |
| `linkFormTableName` | 触发字段显示名（自动填写） | `"订单日期"` |

```python
{
    "startType": "dateFieldEvent",   # ✅ 独立类型，不是 timerEvent
    "attr": {
        "startType": "dateFieldEvent",
        "formTableCode": "ding_dan_shen_qing_c5dg",
        "formTableName": "订单申请",
        "formTableId": "form_start_ding_dan_shen_qing_c5dg",
        "triggerField": "date_1775640531752_255416",  # 触发字段ID
        "triggerFieldType": "date",                   # date / datetime
        "executeType": 2,           # 1=当天 2=到期前 3=到期后
        "plusDate": "1",            # ⚠️ 字符串，不是整数
        "plusDateUnit": 3,          # 1=分钟 2=小时 3=天
        "executionTime": "01:00",   # 日期类型字段专用（datetime 不需要）
        "cycleType": 1,             # 1=每年（0=不重复/1=每年/2=每月/3=每周）
        "linkFormTableName": "订单日期",
        "searchFieldGroup": [],
        "startCondition": [],       # 可选筛选条件
    }
}
```

> **场景示例：** 订单日期到期前 1 天执行通知流程。

---

### 22.6 人员事件触发（userEvent）

组织内有员工入职或离职时自动触发流程。

**start_attr 关键字段：**

| 字段 | 说明 | 取值 |
|------|------|------|
| `startCondition` | 筛选条件（满足才触发） | `[...]` |

> ⚠️ `userEventType`（入职/离职）**不在 `attr` 内**，真实 processJson 的 `attr` 中没有该字段。`formTableList` 使用固定结构（`nodeType:"userEvent"`）区分人员事件。

```python
{
    "startType": "userEvent",
    "attr": {
        "startType": "userEvent",
        "startCondition": [],      # 可选筛选条件
        "selectType": 1,
    },
    # formTableList 固定结构（不同于 tableEvent）：
    "formTableList": [
        {
            "formTableId": "form_start_sys_user",
            "nodeId": "start",
            "nodeName": "人员事件触发",
            "nodeType": "userEvent",       # 固定值
            "formTableCode": "sys_user",   # 固定值
            "formTableName": "人员事件触发" # 固定值
        }
    ]
}
```

> **场景示例：** 有新员工入职时，自动在《员工档案》表中新增记录。

---

## 二十三、processJson 顶层字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 固定为 `"start"` |
| `startTaskId` | string | 开始任务ID，自动生成 |
| `name` | string | 开始节点名称 |
| `type` | string | 固定为 `"start"` |
| `initiator` | string | 固定为 `"applyUserId"` |
| `childNode` | object | 第一个子节点（链式结构） |
| `formTableList` | array | 关联的工作表列表 |
| `attr` | object | 触发配置（startType/formTableCode 等） |
| `executeListeners` | array | 流程级监听器（固定，不可删） |
| `taskListenerData` | array | 任务监听器（固定，不可删） |
| `eventListeners` | array | 全局事件监听器（固定，不可删） |

---

## 二十四-A、服务任务节点（service）

调用后端 Java 类或 Spring 委托表达式执行自定义业务逻辑。

### 完整配置

```python
{
    "type": "service",
    "name": "服务节点",
    "attr": {
        # 调用方式：
        #   "class"               = 直接调用 Java 类（实现 JavaDelegate 接口）
        #   "delegateExpression"  = 通过 Spring EL 表达式解析 Bean
        "expressionType": "class",
        "expressionValue": "org.jeecg.modules.testListenerExpression.TestService",
        # 或使用委托表达式：
        # "expressionType": "delegateExpression",
        # "expressionValue": "${myServiceDelegate}",

        "resultVariable": "",   # 输出变量名（可选）
        "description": "执行业务逻辑"
    }
}
```

### 常用场景

**调用 Java 类：**
```python
{"type": "service", "name": "服务节点",
 "attr": {"expressionType": "class",
          "expressionValue": "org.jeecg.modules.testListenerExpression.TestService"}}
```

**调用 Spring Bean 委托表达式：**
```python
{"type": "service", "name": "调用服务",
 "attr": {"expressionType": "delegateExpression",
          "expressionValue": "${updateRecordDelegate}"}}
```

---

## 二十四-B、脚本节点（script）

执行 JavaScript 或 Groovy 脚本，可读写流程变量。

### 完整配置

```python
{
    "type": "script",
    "name": "脚本节点",
    "attr": {
        # 脚本语言：javascript（默认）或 groovy
        "scriptFormat": "javascript",

        # 脚本内容（支持多行，用 \n 换行）
        # 通过 execution.setVariable("变量名", 值) 向流程写入变量
        # 通过 execution.getVariable("变量名") 读取流程变量
        "scriptContent": "var sum = 2 + 9;\nexecution.setVariable('myVar', sum);",

        # 是否自动存储脚本内所有顶级变量为流程变量（默认 False，推荐保持 False）
        "autoStoreVariables": False,

        "description": "计算并设置变量"
    }
}
```

> ⚠️ **节点顶层 `content` 与 `attr.scriptContent` 要同写**（`content` 是设计器卡片显示文本；只改 scriptContent 时卡片仍显示旧脚本/旧变量名）。**变量名建议直接用中文**（Groovy 支持中文标识符），并与根 `variableList[].field`/`columnName`、data_update 取值、分支条件四处一致——只写英文 `field` 不写 `columnName` 时设计器「本流程参数」列表显示英文标识（用户 2026-09-10 定论，gotchas #83 + create-flow.md「组合 J 变体」）。读本行表单字段用 `execution.getVariable('<字段model>')`；**date 字段实测传入 `yyyy-MM-dd HH:mm:ss` 字符串**，直接 `new Date(str)` 抛异常且被 Groovy 静默吞掉 → 需做 Date / 毫秒 / 字符串三形态兜底解析。

### 常用场景

**计算并存入流程变量（JavaScript）：**
```python
{"type": "script", "name": "计算金额",
 "attr": {
     "scriptFormat": "javascript",
     "scriptContent": "var total = price * qty;\nexecution.setVariable('totalAmount', total);"
 }}
```

**Groovy 脚本：**
```python
{"type": "script", "name": "数据处理",
 "attr": {
     "scriptFormat": "groovy",
     "scriptContent": "execution.setVariable('flag', true)"
 }}
```

**读取已有变量再运算：**
```python
{"type": "script", "name": "折扣计算",
 "attr": {
     "scriptFormat": "javascript",
     "scriptContent": (
         "var amount = execution.getVariable('totalAmount');\n"
         "var discount = amount * 0.9;\n"
         "execution.setVariable('discountAmount', discount);"
     )
 }}
```

---

## 二十五、必须包含的系统监听器（不可删除）

```python
executeListeners = [
    {
        "id": "402880e54803a496014805e5d9190012",
        "eventType": "end", "listenerType": "javaClass",
        "listenerName": "平台通用流程结束监听",
        "value": "org.jeecg.modules.extbpm.listener.execution.ProcessEndListener",
        "allowDel": False
    },
    {
        "id": "506880e54803a496014805e5d9190012",
        "eventType": "end", "listenerType": "javaClass",
        "listenerName": "流程结束删除redis数据",
        "value": "org.jeecg.modules.minides.listener.ProcessEndRemoveRedisListener",
        "allowDel": False
    }
]

taskListenerData = [
    {
        "eventType": "create", "listenerType": "class",
        "listenerName": "发起人节点跳过监听",
        "value": "org.jeecg.modules.extbpm.listener.task.TaskCreatedAutoSubmitListener"
    }
]

eventListeners = [
    {
        "listenerType": "javaClass",
        "listenerName": "任务创建全局监听",
        "value": "org.jeecg.modules.listener.tasktip.TaskCreateGlobalListener",
        "allowDel": False
    }
]
```

## 二十六、API 节点（api）— 调用 HTTP 接口

生成 ServiceTask，委托表达式 `${apiTaskDelegate}`（后端按 type=api 硬编码，**不需要** attr.expressionType/expressionValue）。**不需要**注册 formTableList（不在五类联动清单内）。

### attr 字段清单

| 字段 | 类型 | 默认 | 说明 |
|---|---|---|---|
| nodeKey | string | `Activity_<uuid>` | 后端活动键 |
| apiUrl | string | `""` | 接口地址；相对路径（不以 http 开头）= 内部接口，自动拼网关域名并补 `X-Access-Token`/`X-TIMESTAMP`/`TENANT-ID`/`X-LOW-APP-ID` 头（用户已配同名 header 不覆盖） |
| httpMethod | string | `"GET"` | GET/POST/PUT/DELETE/PATCH |
| headers | array | `[]` | 条目 `{name, value}` |
| inputParams | array | `[]` | 条目 `{name, value}`；GET/DELETE → URL Query；POST/PUT/PATCH 无 requestBody → 序列化为 JSON Body，有 requestBody → 也作 Query |
| requestBody | string | `""` | 请求体 JSON 文本（仅 POST/PUT/PATCH）；⚠️ 前端默认构造**没有此键**，是抽屉才补的——手动构造必须显式带上 |
| returnResults | array | `[]` | 条目 `{field, variable}`：field=响应取值路径，variable=目标流程变量名 |
| timeout | number | 30000 | 毫秒，范围 1000-300000 |
| retryCount | number | 3 | 0-10；失败重试次数，全部失败写流程变量 `apiError=异常消息` 并抛异常终止 |
| description | string | `""` | 描述 |

### 占位符体系（apiUrl/headers/inputParams/requestBody 内嵌替换）

- `${varName}` → 取流程变量，缺失替换为空串
- `#{x-access-token}` / `#{x-timestamp}` / `#{time}` / `#{date}` / `#{datetime}` → 系统上下文值

### returnResults 的 field 路径规则

- 支持 `result.records[0].name`、`[0].name`、`a.0.b` 等多级下标写法
- field 留空 → 整个响应对象（JSON 字符串形式）
- 响应非 JSON 时：field 为 `response`/`body`/`responseBody` → 原始文本；field 为 `status`/`code`/`responseCode` → HTTP 状态码

### 构造示例

```python
ts = int(time.time() * 1000)
api_node = {
    'id': f'task{ts}001',
    'pid': 'start',
    'name': '调用接口',
    'type': 'api',
    'level': '1',
    'childNode': None,                # 必须显式给，防止旧版本链路断链
    'attr': {
        'nodeKey': f'Activity_{ts}001',
        'apiUrl': '/act/api/hello',   # 官方 demo 接口（@IgnoreAuth），联调首选
        'httpMethod': 'GET',
        'headers': [],
        'inputParams': [{'name': 'type', 'value': 'test'}],
        'requestBody': '',
        'returnResults': [{'field': 'result.summary.avgScore', 'variable': 'avg_score'}],
        'timeout': 30000,
        'retryCount': 3,
        'description': '',
    },
    'addable': True, 'deletable': False,
    'content': 'GET /act/api/hello (1入参，1出参)',   # UI 卡片正文，格式：方法 地址 (N入参，M出参)
    'error': False, 'errorContent': '',
}
```

## 二十七、AI 编排节点（aiOrchestration）— 调用 AI 流程

生成 ServiceTask，委托表达式 `${aiOrchestrationTaskDelegate}`（同样不需要 expressionType/expressionValue、不注册 formTableList）。运行时经 `ISysBaseAPI.runAiragFlow` 同步执行 airag AI 编排流程（`airag_flow` 表），结果按 returnResults 写回流程变量；执行异常时按流程配置 `error_notice_user_ids` 发系统消息并终止实例。

### attr 字段清单

| 字段 | 类型 | 默认 | 说明 |
|---|---|---|---|
| nodeKey | string | `Activity_<uuid>` | 后端活动键 |
| aiProcessId | string | `""` | **必填**；AI 编排流程 id，从 `GET /airag/flow/list?status=enable,release` 选 |
| inputParams | array | `[]` | 条目 `{name, value}`；value 支持 `${变量}` 取流程变量、`#{sysUserId}` 等系统变量；⚠️ 落库**只保留 name/value 两键**（type/nameText/required/fromFlow 是 UI 态） |
| returnResults | array | `[]` | 条目 `{field, variable}`：field=AI 输出字段路径（留空=整个结果；AI 输出模式为 text/card 时 field 恒为 `""`），variable=目标流程变量 |
| endOutputType | string | `"default"` | `text` / `card` / `default` 三种输出模式（回显用） |
| description | string | `""` | 描述 |

出参取值路径同 API 节点（`a.b.c`、`list[0]`、`data.users[0].name`）；复杂值（Map/List）序列化成 JSON 字符串再 setVariable。`returnResults[].field` 的具体路径取决于所选 AI 流程的输出定义（可 `GET /airag/flow/queryFlowConfig?id=` 查，纯 HTTP 调用即可，无需其他 skill）；拿不准时 **field 留空取整个结果**，再由下游节点解析。

### 构造示例

```python
ai_node = {
    'id': f'task{ts}002',
    'pid': 'start',
    'name': 'AI分析',
    'type': 'aiOrchestration',
    'level': '1',
    'childNode': None,
    'attr': {
        'nodeKey': f'Activity_{ts}002',
        'aiProcessId': '<airag流程id>',
        'inputParams': [{'name': 'question', 'value': '${apply_user_name}的问题'}],
        'returnResults': [{'field': 'data.answer', 'variable': 'ai_answer'}],
        'endOutputType': 'default',
        'description': '',
    },
    'addable': True, 'deletable': False,
    'content': 'AI流程: 智能问答 (1入参，1出参)',   # 格式：AI流程: {流程名} ({N}入参，{M}出参)
    'error': False, 'errorContent': '',
}
```

## 二十八、不可用 / 占位节点类型

**禁止在 processJson 中使用以下类型**：

| 类型 | 前端组件 | 状态 |
|---|---|---|
| `copy`（抄送，type=**数字 2**） | FlowDrawer/Copyer 完整 | ❌ **后端直接抛异常** `抄送功能暂未实现，请不要选择抄送`（DesignerAdapterUtil L374-376）——保存能过、发布必炸。需要通知效果改用 `message_*` 通知节点 |
| `5`（数字，事件） | FlowDrawer/Event | ❌ 半成品：抽屉无保存逻辑，配置区全是注释占位 |
| `20`（数字，通知占位） | 无抽屉 | ❌ 占位；真正的通知走 `message_*` 字符串类型节点 |
| Divide | 未注册进渲染映射 | ❌ 纯静态分隔卡片，nodeUtil/文档均无构造 |

**数字型 type 与字符串型混用提醒**：抄送=2、事件=5、通知占位=20、分支行=3、并行行=10、意见分支按钮=8 均为**数字**；其余全部是字符串。遍历判断节点类型时不能一律 `== 'xxx'` 字符串比较。

**service 节点构造瑕疵**：前端默认构造缺 `childNode` 键（Add/index.vue L613-629）——手动构造 service/api/aiOrchestration/script 节点时一律显式写 `childNode: None`，树操作兜底虽存在但旧链路可能断。
