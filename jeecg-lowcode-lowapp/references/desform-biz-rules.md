# 业务规则（bizRuleConfig）参考文档

业务规则存储在 `config.bizRuleConfig` 中，是一个规则数组。规则在**前端填报时实时计算**，当条件满足时执行指定动作（显示/隐藏/必填/锁定等）。

---

## 执行时序与冲突处理（源码验证）

> 源码：`src/mixins/generate/BizRulesMixins.js`

**执行顺序：按数组顺序依次执行**，规则内部分为 4 类依次处理：`normalConfig`（显示/隐藏/编辑/只读）→ `requiredConfig`（必填）→ `checkConfig`（MESSAGE 提示）→ `lockConfig`（锁定记录）。

**冲突规则：后执行者覆盖**。若规则 A（索引 0）对字段 X 执行 SHOW，规则 B（索引 1）对同一字段 X 执行 HIDE，最终结果是 HIDE（后者赢）。因此规则顺序有业务含义，配置时需注意。

---

## 子表字段支持（源码验证）

**条件（rules）**：支持引用子表字段，格式为 `subTableModel.fieldModel`（含 `.`）。代码检测到 `model.includes('.')` 时，取 `.` 前半段作为主字段 model，仅监听该主字段的顶层变化，**不做深层子表行级联动**。因此子表字段可作为触发条件，但触发粒度是整个子表变化，而非某一行的变化。

**动作（actions）**：子表字段 model 也可作为 SHOW/HIDE/REQUIRED 等动作的目标，行为与普通字段一致。

---

## formula 字段支持的操作符（源码验证）

公式字段支持的 rule 操作符取决于其 `options.type`：

| formula 的 `options.type` | 支持的操作符 |
|---|---|
| `"number"` | `EQ` `NE` `GT` `GE` `LT` `LE` |
| `"date"` | `DATE_LT` `DATE_LE` `DATE_GT` `DATE_GE` |
| 其他类型 | ❌ 不支持作为条件字段 |

---

## ⚠️ 与 desform-filter-rules.md 的关键区别

业务规则的 `rule` 字段与数据过滤条件（`desform-filter-rules.md`）**是完全不同的两套体系，不可混用**：

| 对比项 | 业务规则（本文档） | 数据过滤条件 |
|---|---|---|
| 命名格式 | **全大写**，如 `EQ` `IN_ONE_OF` | **全小写**，如 `eq` `in` |
| 执行位置 | 前端实时计算（填报时） | 后端数据库查询 |
| `IN` 的含义 | 字符串**包含**（substring） | ❌ 不存在此写法 |
| 列表匹配 | `IS_ONE_OF` / `IN_ONE_OF` | `in` / `not_in` |
| 开头/结尾匹配 | `BEFORE` / `AFTER` | `right_like` / `left_like` |
| 独有规则 | `VALUE_CHANGE` `IN_ALL_OF` `DATE_*` | `range` `like` `linkage` |

**常见混淆错误**：用 `"in"` 代替 `"IS_ONE_OF"` → 规则永远不生效，且不报错。

---

## bizRuleConfig 数组结构

```json
[
  {
    "name": "规则1",
    "enabled": true,
    "matchType": "AND",
    "rules": [ /* 条件数组 */ ],
    "actions": [ /* 动作数组 */ ]
  }
]
```

### matchType（条件关系）

| 值 | 含义 |
|---|---|
| `"AND"` | 且——所有条件全部满足 |
| `"OR"` | 或——满足任意一个条件 |

---

## 条件项（rules 数组元素）

```json
{
  "model": "input_1774607211242_327900",
  "rule": "EQ",
  "valueType": "fixed",
  "value": ["待审核"],
  "valueText": "待审核"
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `model` | ✅ | 字段的 model（从 `get_form_fields` 获取） |
| `rule` | ✅ | 条件操作符，见下表，**全大写** |
| `valueType` | ✅ | 值类型：`"fixed"` \| `"field"` \| `"system"` |
| `value` | ✅ | 值数组（无值规则传 `[]`；`MESSAGE` 动作传字符串） |
| `valueText` | — | 值的展示文本（可省略，不影响逻辑） |

### valueType 三种类型

| valueType | 含义 | value 格式 |
|---|---|---|
| `"fixed"` | 固定值 | `["值1", "值2"]`（多值时满足任意一个） |
| `"field"` | 字段值（与另一个字段的值比较） | `["other_field_model"]` |
| `"system"` | 系统变量 | `["sysUserCode"]`（见下方系统变量表） |

> ⚠️ **`valueType="field"` 的 `value` 必须写「裸 model」，不能带 `$...$` 包裹**（2026-09-17 实测）：
> 正确 `{"valueType":"field","value":["summary_1789629720122_806986"],"valueText":"$summary_1789629720122_806986$"}`，
> 写成 `"value":["$summary_...$"]` 时**设计器解析不了，条件处直接显示「字段已删除」**（用户截图报障）。
> 注意与 `expression`（公式）相反——公式里必须 `$model$`，业务规则 `value` 里必须裸 model，`valueText` 才是 `$model$`。

**系统变量可选值**（`valueType="system"` 时 `value[0]` 的合法值）：

| 变量 | 含义 |
|---|---|
| `sysUserCode` | 当前登录人编码（username） |
| `sysUserId` | 当前登录人 ID |
| `sysUserName` | 当前登录人名称 |
| `sysOrgId` | 当前登录人的部门 ID |
| `sysOrgCode` | 当前登录人的部门编码 |
| `sysRoleCode` | 当前登录人的角色编码 |
| `sysDate` | 当前日期（yyyy-MM-dd） |
| `sysTime` | 当前日期时分秒 |

---

## 条件操作符（rule）完整表

### 通用规则（适用于大多数字段，除 switch）

| rule | 中文 | 是否需要 value |
|---|---|---|
| `EMPTY` | 为空 | ❌（传 `[]`） |
| `NOT_EMPTY` | 不为空 | ❌（传 `[]`） |
| `VALUE_CHANGE` | 值发生变化 | ❌（传 `[]`） |

> **注意**：`switch` 控件**不支持** `EMPTY` / `NOT_EMPTY`（与 filter-rules 的 `switch` 行为不同）。

### 字符串类字段（input / textarea / auto-number / phone / email 等）

| rule | 中文 | 说明 |
|---|---|---|
| `EQ` | 等于 | |
| `NE` | 不等于 | |
| `IN` | 包含（substring） | ⚠️ 此处是"字符串包含"，不是列表匹配 |
| `NOT_IN` | 不包含 | 同上 |
| `BEFORE` | 开头是 | 等价于 filter 的 `right_like` |
| `NOT_BEFORE` | 开头不是 | |
| `AFTER` | 结尾是 | 等价于 filter 的 `left_like` |
| `NOT_AFTER` | 结尾不是 | |

### 数值类字段（number / integer / money / rate / slider / formula[number] / summary）

| rule | 中文 |
|---|---|
| `EQ` | 等于 |
| `NE` | 不等于 |
| `GT` | 大于 |
| `GE` | 大于等于 |
| `LT` | 小于 |
| `LE` | 小于等于 |

### 日期类字段（date / formula[date]）

| rule | 中文 | 说明 |
|---|---|---|
| `DATE_LT` | 早于 | 不含等于 |
| `DATE_LE` | 早于等于 | |
| `DATE_GT` | 晚于 | 不含等于 |
| `DATE_GE` | 晚于等于 | |

### 单选类字段（radio / 单选 select-user / 单选 select-depart / 单选 org-role / 单选 link-record）

| rule | 中文 | 说明 |
|---|---|---|
| `IS_ONE_OF` | 是其中一个 | value 可传多个值，满足其一即触发 |
| `NOT_IS_ONE_OF` | 不是其中一个 | |

> `select-user`/`select-depart`/`org-role` 的单选/多选由 `options.multiple` 决定。
> `link-record` 的单选/多选由 `options.showMode` 决定（`"single"` = 单选，`"many"` = 多选）。

### 多选类字段（checkbox / 多选 select / 多选 select-user / 多选 select-depart / 多选 link-record）

| rule | 中文 | 说明 |
|---|---|---|
| `IN_ONE_OF` | 包含其中一个 | 字段值与 value 有交集即触发 |
| `NOT_IN_ONE_OF` | 不包含任何一个 | 没有交集才触发 |
| `IN_ALL_OF` | 同时包含 | 字段值包含 value 中所有项才触发 |

### switch 字段

| rule | 中文 |
|---|---|
| `EQ` | 等于（传开关的 active/inactive 值，如 `"Y"` / `"N"`） |
| `NE` | 不等于 |

---

## 动作项（actions 数组元素）

```json
{
  "type": "SHOW",
  "value": ["input_xxx", "select_yyy"]
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `type` | ✅ | 动作类型，见下表 |
| `value` | ✅ | 目标字段 model 数组；`MESSAGE` 类型传字符串；`LOCK` 传 `[]` |

### 动作类型（type）完整表

| type | 中文 | value 格式 | 说明 |
|---|---|---|---|
| `SHOW` | 显示 | `[model, ...]` | 可含普通字段、容器（grid/tabs）、静态组件（divider/text/buttons） |
| `HIDE` | 隐藏 | `[model, ...]` | 同上 |
| `EDIT` | 可编辑 | `[model, ...]` | 仅普通字段 |
| `READONLY` | 只读 | `[model, ...]` | 仅普通字段 |
| `REQUIRED` | 必填 | `[model, ...]` | 仅普通字段 |
| `SHOW_TAB_PANE` | 显示 Tab 页 | `["tabModel.paneName", ...]` | 格式：tabs 的 model + "." + pane 的 name |
| `HIDE_TAB_PANE` | 隐藏 Tab 页 | `["tabModel.paneName", ...]` | 同上 |
| `MESSAGE` | 提示错误 | `"错误提示文字"` | **value 是字符串，不是数组** |
| `LOCK` | 锁定记录 | `[]` | 禁止编辑整条记录 |
| `CLEAN_VALUE` | 清空值 | `[model, ...]` | 将指定字段的值清空为 null |

> **SHOW/HIDE 的特殊性**：这两个动作的 value 可以包含容器组件（grid/tabs）和静态无值组件（divider/text/buttons），其他动作只能选择有值的普通字段。

> **反向动作**：系统会自动处理反向逻辑——当条件不满足时，`SHOW` 的反向是 `HIDE`，`EDIT` 的反向是 `READONLY`，`REQUIRED` 无反向（条件不满足时恢复为非必填）。
>
> **⚠️ 反向逻辑的本质是"回到字段原始状态"，而非"主动切换到相反状态"**。因此配置业务规则前，必须确认目标字段的原始属性与预期默认状态一致，否则规则不生效：
> - 用 `SHOW` 控制显示 → 字段 `options.hidden` 必须为 `true`（默认隐藏），否则条件不满足时字段依然可见
> - 用 `HIDE` 控制隐藏 → 字段 `options.hidden` 必须为 `false`（默认可见），否则条件不满足时字段依然隐藏
> - 用 `EDIT` 控制可编辑 → 字段原始应为 `readonly: true` 或 `disabled: true`
> - 用 `READONLY` 控制只读 → 字段原始应为 `readonly: false`
>
> **操作步骤**：配置业务规则前，先用 `query_form` 查询目标字段的当前原始属性，必要时先用 `update_widget(..., key=字段key)` 修正原始属性，再写入规则。

---

## 完整示例

### 示例 1：当状态为"审核中"时，隐藏"提交按钮"并显示只读提示

```json
{
  "name": "审核状态锁定",
  "enabled": true,
  "matchType": "AND",
  "rules": [
    {
      "model": "radio_1774607211242_100001",
      "rule": "IS_ONE_OF",
      "valueType": "fixed",
      "value": ["auditing"]
    }
  ],
  "actions": [
    {
      "type": "HIDE",
      "value": ["buttons_1774607211242_200001"]
    },
    {
      "type": "MESSAGE",
      "value": "当前记录正在审核中，无法修改"
    }
  ]
}
```

### 示例 2：当金额 > 10000 时，报销说明必填

```json
{
  "name": "大额报销必填",
  "enabled": true,
  "matchType": "AND",
  "rules": [
    {
      "model": "money_1774607211242_100002",
      "rule": "GT",
      "valueType": "fixed",
      "value": ["10000"]
    }
  ],
  "actions": [
    {
      "type": "REQUIRED",
      "value": ["textarea_1774607211242_200002"]
    }
  ]
}
```

---

## Python 操作

业务规则保存在 `config.bizRuleConfig` 中，使用 `update_design_config` 快捷函数更新：

```python
from desform_utils import init_api, update_design_config

init_api('<api_base>', '<token>')

# 新增一条规则
rules = [
    {
        "name": "状态锁定",
        "enabled": True,
        "matchType": "AND",
        "rules": [
            {
                "model": "radio_xxx",
                "rule": "IS_ONE_OF",
                "valueType": "fixed",
                "value": ["done"]
            }
        ],
        "actions": [
            {"type": "LOCK", "value": []}
        ]
    }
]
update_design_config('my_form_code', {"bizRuleConfig": rules})
```

> **注意**：`bizRuleConfig` 是数组，`update_design_config` 对数组采用**整体替换**策略。
> 如需追加规则，必须先查询现有规则再追加，不能只传新规则。

```python
from desform_utils import init_api, query_form, update_design_config
import json

init_api('<api_base>', '<token>')

# 查询现有规则
form_data = query_form('my_form_code')
design_json = json.loads(form_data['desformDesignJson'])
existing_rules = design_json['config'].get('bizRuleConfig', [])

# 追加新规则
new_rule = { ... }
existing_rules.append(new_rule)

update_design_config('my_form_code', {"bizRuleConfig": existing_rules})
```
