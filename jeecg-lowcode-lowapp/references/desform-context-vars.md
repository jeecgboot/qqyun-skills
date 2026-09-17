> **【强制规则】本文档供 AI 理解上下文变量功能的完整配置规则。当用户询问该功能的使用方式时，只需回答用户实际操作时关心的问题（如：有哪些变量可用、在哪里填、能不能拼接），不要解释 JSON 结构、defaultExpr 字段如何工作、或其他只有 AI 代码生成时才需要关心的内容。**

# 上下文变量（默认值表达式）

在表单设计器中，使用 `{{变量名}}` 语法可以将系统级动态值（当前用户、当前时间等）嵌入到控件的默认值或文本内容中。

## 可用的上下文变量

| 变量名 | 含义 | 示例值 |
|--------|------|--------|
| `sysUserCode` | 当前登录用户账号 | `zhangsan` |
| `sysUserName` | 当前登录用户真实姓名 | `张三` |
| `sysOrgCode` | 当前登录用户部门编码 | `A001` |
| `sysDate` | 当前系统日期 | `2019-07-26` |
| `sysTime` | 当前系统时间 | `10:43:42` |
| `sysBasePath` | 当前系统后台根路径 | `http://localhost:8080/jeecg-boot` |

## 支持使用上下文变量的位置

### 1. 控件默认值（所有控件）

所有控件的 `advancedSetting.defaultValue`（compose 类型）的 `value` 字段均支持 `{{varName}}`。

**支持的语法（可混合使用）：**

| 写法 | 说明 |
|------|------|
| `{{sysUserCode}}` | 单个上下文变量 |
| `{{sysDate}} {{sysTime}}` | 多个变量拼接（可加空格或其他字符） |
| `操作人：{{sysUserName}}` | 变量与静态文本混合 |
| `$fieldModel$` | 引用其他字段的值（见 desform-default-value.md） |
| `{{sysDate}}-$input_xxx$` | 上下文变量 + 字段引用混合 |

**JSON 配置示例：**
```json
{"name": "操作人账号", "type": "input", "defaultExpr": "{{sysUserCode}}"}
{"name": "操作人姓名", "type": "input", "defaultExpr": "{{sysUserName}}"}
{"name": "所属部门", "type": "input", "defaultExpr": "{{sysOrgCode}}"}
{"name": "记录时间", "type": "input", "defaultExpr": "{{sysDate}} {{sysTime}}"}
{"name": "备注", "type": "textarea", "defaultExpr": "{{sysDate}} 由 {{sysUserName}} 填写"}
```

**Python 代码示例：**
```python
INPUT('操作人账号', default_expr='{{sysUserCode}}')
INPUT('操作人姓名', default_expr='{{sysUserName}}')
INPUT('记录时间', default_expr='{{sysDate}} {{sysTime}}')
TEXTAREA('备注', default_expr='{{sysDate}} 由 {{sysUserName}} 填写')
```

> **注意：** `defaultExpr` 设置的是 `advancedSetting.defaultValue.value`（compose 类型），仅在新增模式下生效。`select-user`、`select-depart` 等有专属 `defaultLogin` 参数的控件建议使用该参数而非 `defaultExpr`。

### 2. 文本组件（type=text）

文本组件的 `options.text` 内容支持 `{{varName}}`，用于在表单中显示动态说明文字。

**JSON 配置示例：**
```json
{"name": "提示文字", "type": "text", "text": "当前操作人：{{sysUserName}}，操作时间：{{sysDate}} {{sysTime}}"}
```

**Python 代码示例：**
```python
TEXT(text='当前操作人：{{sysUserName}}，操作时间：{{sysDate}} {{sysTime}}')
```

### 3. 远程API取值接口地址（`remoteAPI.url`）

`remoteAPI.url` 中的 `{{varName}}` 语法与上述相同，变量含义也相同。远程 API 的其他配置规则（返回值格式、触发时机、`${字段model}` 传参）见 `desform-remote-api.md`。

## 运行时效果示例

配置：`"当前系统时间 {{sysDate}} {{sysTime}}"`

运行时渲染为：`当前系统时间 2026-04-02 12:05:01`

## 注意事项

1. **大括号格式**：必须是双大括号 `{{ }}` 包裹，单括号无效。
2. **变量名大小写**：严格区分大小写，`sysUserCode` 与 `sysusercode` 是不同的。
3. **生效时机**：默认值仅在新增（add/preview）操作时求值，编辑模式下显示已保存的数据，不重新求值。
4. **文本组件例外**：文本组件（`type=text`）在所有模式（新增/编辑/查看）下都会实时渲染变量值，因为它不存储数据。
5. **子表控件**：子表内的控件不支持通过 `defaultExpr` 设置上下文变量默认值。
