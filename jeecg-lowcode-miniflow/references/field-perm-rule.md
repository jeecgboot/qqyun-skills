---
name: 简流节点字段权限正确格式
description: saveOrUpdateBatch 接口字段权限的 ruleCode 和记录数规范
type: feedback
---

**ruleCode 必须用字段 model 值，每字段必须提交两条记录（ruleType=1+2）。必填通过记录的 `required` 布尔字段控制，禁止用 ruleType=3。**

**Why:** ruleCode 用 desformComKey 会导致权限不生效；只传 ruleType=1 没有 ruleType=2 也不生效；ruleType=3 不存在，必填靠的是每条记录自身的 `required: true`。另外 `processJson` 的 `privileges` 数组对简流字段权限无效，必须用此独立 API。**`desformComKey` 留空同样静默失效**——取值的坑：要用 `desform_utils.get_form_fields(code)` 返回的 `key`，**不要用 `miniflow_creator.fetch_form_fields`**（同名函数，后者只返回 `{model,type,options}`、**没有 key**，用它取值拿到 None 写进 `or ''` 就是空串，save 照常 200）。

**How to apply:** 调用 `/act/process/extActProcessNodePermission/saveOrUpdateBatch` 时：

| 字段 | 正确值 | 错误值 |
|------|--------|--------|
| `ruleCode` | 字段 `model` 值（如 `auto_number_1776337156811_785567`） | desformComKey（如 `1776337156811_723650`） |
| `desformComKey` | 控件 `key`（如 `1776337156811_723650`），**必须非空** | 留空——整条权限静默不生效（运行时匹配不到控件，审批表单里**全部字段仍可编辑**，2026-09-16 实测返工） |
| 记录条数 | 每字段 2 条（ruleType=1 + ruleType=2） | 只发 1 条 ruleType=1 |
| `status` | 字符串 `"0"` / `"1"` | 数字 0 / 1 |
| 必填 | 两条记录都加 `"required": true` | 额外发一条 ruleType=3 |
| 改已有权限 | **先 GET list 取该记录 `id`，回传时带 `id`**（不带 id 的同内容重发 = 静默无操作：返回 `批量保存成功` 但值不变；2026-09-15 实测） | 无 id 直接重发期望更新 |

**三种权限场景完整示例：**

```json
[
  // ── 必填字段（入库单号）──
  {
    "ruleCode": "auto_number_1776337156811_785567",
    "ruleName": "入库单号",
    "desformComKey": "1776337156811_723650",
    "formBizCode": "wh_inbound",
    "formType": "2",
    "processId": "xxx",
    "processNodeCode": "taskXxx",
    "ruleType": "1",
    "status": "1",       // 显示
    "required": true     // ← 必填在这里
  },
  {
    "ruleCode": "auto_number_1776337156811_785567",
    "ruleName": "入库单号",
    "desformComKey": "1776337156811_723650",
    "formBizCode": "wh_inbound",
    "formType": "2",
    "processId": "xxx",
    "processNodeCode": "taskXxx",
    "ruleType": "2",
    "status": "0",       // 可编辑
    "required": true     // ← 两条都要设 true
  },
  // ── 仅可见字段（入库日期）──
  {
    ...
    "ruleType": "1", "status": "1", "required": false
  },
  {
    ...
    "ruleType": "2", "status": "1", "required": false   // status="1" 只读
  },
  // ── 隐藏字段（入库类型）──
  {
    ...
    "ruleType": "1", "status": "0", "required": false   // 隐藏
  },
  {
    ...
    "ruleType": "2", "status": "1", "required": false   // 只读
  }
]
```

**status 含义：**
- `ruleType=1`（显示权限）：`"1"`=显示，`"0"`=隐藏
- `ruleType=2`（编辑权限）：`"0"`=可编辑，`"1"`=只读/禁用
- **`required`**：布尔字段，`true`=必填；必填时 ruleType=1 和 ruleType=2 两条记录都要设为 `true`

**重名控件消歧（2026-09-16 实测）：** 字段与分隔符/文本等展示控件同名时，按名字配权限会配到错误的一个（典型：配到分隔符上，真正的字段仍是只读）。**判据：看组件类型，分隔符/文本肯定不是目标**；真数据控件的 `ruleName` 带 `#<model>` 后缀（如 `退货审批状态#select_1789531255295_198274`）。
