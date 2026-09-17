> **【强制规则】本文档供 AI 理解填值规则功能的配置方式。当用户询问该功能的使用方式时，只需回答用户实际操作时关心的问题（如：在哪里填规则码、填完后怎么触发、完全只读怎么设置），不要解释 JSON 结构或代码层面的实现细节。**
>
> **【强制规则】填值规则必须由用户在 JeecgBoot 系统管理后台预先定义，其 `规则Code` 是不可预测的。在为控件配置填值规则时，如果用户没有提供规则 Code，必须停下来询问用户提供，绝对不能猜测或编造规则 Code。**
>
> **【强制规则】禁止通过猜测的方式调用任何 API 自行查询规则 Code。如果用户说"不要找我确认/直接生成"，也必须让用户主动提供规则 Code，或明确告知用户"填值规则部分需要您提供规则 Code"后跳过该部分。**

# 填值规则（fillRuleCode）

⛔ **敲敲云属性面板不展示填值规则**（WidgetConfig `v-if="!isLowApp"`）。本 skill 不要给工作表配置 `fillRuleCode`。编号请用 `auto-number`。

填值规则沿用 JeecgBoot 平台的编码生成规则机制，支持根据表单字段值动态计算填入结果。常见场景：公文发文字号、合同编号、单据号等按特定规则自动生成的字段。

## 前提：在系统后台定义规则

填值规则必须**提前在系统管理后台**中定义，路径：**系统管理 → 填值规则**。

每条规则有唯一的**规则 Code**（如 `contract_no_rule`），这个 Code 在配置控件时使用。**AI 无法预知用户系统中已有哪些规则，必须由用户提供。**

## JSON 配置

`fillRuleCode` 对 `input`（单行文本）和 `textarea`（多行文本）控件有效：

```json
{"name": "合同编号", "type": "input", "fillRuleCode": "contract_no_rule"}
```

如果不希望用户修改自动生成的值，配合 `readonly: true` 使用（完全只读）：

```json
{"name": "发文字号", "type": "input", "fillRuleCode": "doc_ref_rule", "readonly": true}
```

## Python 代码

```python
INPUT('合同编号', fill_rule_code='contract_no_rule')
INPUT('发文字号', fill_rule_code='doc_ref_rule', readonly=True)
```

## 触发时机

| 场景 | 是否触发 |
|------|---------|
| 新增模式，首次进入表单 | ✅ 自动执行一次，将表单当前数据传递给后台计算 |
| 编辑/查看模式，进入页面 | ❌ 不自动触发 |
| 表单字段值发生变化后（需 JS 增强） | ✅ 手动调用 `api.executeAllFillRule()` 触发 |

## 动态触发：字段变化时重新计算

如果填值规则的计算依赖于其他表单字段，当依赖字段变化后，需要通过 JS 增强重新触发。在 JSON 配置的 `expand.js` 中写入：

```javascript
api.watch({
    // 替换为需要监听的字段 model（如 input_1774607211242_327900）
    input_xxxxxxxxx_xxxxxx() {
        api.executeAllFillRule()
    }
})
```

JSON 配置完整示例（包含 JS 增强）：

```json
{
  "formName": "合同申请单",
  "formCode": "contract_apply",
  "fields": [
    {"name": "合同类型", "type": "select", "required": true, "options": ["采购合同", "销售合同"]},
    {"name": "合同编号", "type": "input", "fillRuleCode": "contract_no_rule", "readonly": true}
  ],
  "expand": {
    "js": "api.watch({ 'select_合同类型的model': function() { api.executeAllFillRule() } })"
  }
}
```

> **注意：** JS 增强中引用字段 model 时，必须使用控件实际的 model 值（如 `select_1774607211242_327900`），而非字段中文名。在表单创建成功后，可通过 `get_form_fields(code)` 查询各字段的 model。

## 注意事项

1. **`input` 和 `textarea` 控件支持 `fillRuleCode`**，`number`、`money` 等其他控件不支持。
2. **规则 Code 必须由用户提供**，不可猜测。
3. `readonly: true` 设置后，用户无法手动修改字段值，仅由填值规则写入。
4. 填值规则的具体计算逻辑在 JeecgBoot 后台管理界面配置，表单设计器侧只负责指定使用哪条规则。
