> **【强制规则】本文档供 AI 理解远程API取值功能的完整配置规则。当用户询问该功能的使用方式时，只需回答用户实际操作时关心的问题（如：填什么地址、怎么传参、返回值有什么注意事项），不要解释 JSON 结构、remoteAPI 字段如何设置、或其他只有 AI 代码生成时才需要关心的内容。**

# 远程API取值（remoteAPI）

控件通过调用远程接口获取默认值。接口返回什么，控件就填什么。当动态参数中引用的表单字段值发生变化时，接口会自动重新调用（300ms 防抖）。

## JSON 配置位置

存储在控件的顶层 `remoteAPI` 字段中：

```json
{
  "remoteAPI": {
    "url": "填写接口地址，支持动态参数",
    "executed": false
  }
}
```

- `url`：接口地址，支持绝对地址（`http(s)://...`）或相对地址（`/` 开头，相对于 JeecgBoot 后端，会自动携带 Token）
- `executed`：是否已执行过（运行时状态，配置时填 `false` 即可）

## 动态参数语法

URL 中支持两种占位符，可混合使用：

| 语法 | 含义 | 示例 |
|------|------|------|
| `{{变量名}}` | 上下文变量（系统级，见下节） | `{{sysUserCode}}` |
| `${字段model}` | 表单字段值（当前表单的控件 model） | `${input_xxx_yyy}` |

**特殊表单变量：**
- `${_id}` — 当前数据的 ID（仅编辑模式下有值）
- `${fieldModel_dictText}` — 字段的翻译值（数据字典、日期等字段默认传原始值，加 `_dictText` 后缀可传翻译后的显示值）

**完整示例：**
```
/desform/api/getName?id=${_id}&name=${input_name_xxx}&sex=${select_sex_xxx}&op={{sysUserCode}}_{{sysUserName}}
```

## 上下文变量（`{{变量名}}`）

完整变量列表见 `desform-context-vars.md`（权威来源）。

上下文变量不依赖表单字段，值在页面加载时就确定，不会随表单操作变化。

## 接口返回值规则

1. **接口返回什么值，控件就直接填什么值**——不做额外处理。
2. **返回字符串时，必须用英文双引号包裹**，否则 JS 解析会出错（尤其是纯数字字符串）：
   ```java
   // 错误：return "1749321205115531266";   // JS 会截断大数
   // 正确：
   return "\"1749321205115531266\"";
   ```
3. 返回 JSON 对象/数组时，控件需能接收对象类型（如 select-user、sub-table 等）。
4. 使用绝对地址（`http://...`）时需自行处理跨域。

## 触发时机

| 场景 | 是否触发 |
|------|---------|
| 新增模式，页面首次加载 | ✅ 触发 |
| 编辑/查看模式，页面首次加载 | ❌ 不触发 |
| URL 中的 `${表单字段}` 对应字段值发生变化 | ✅ 触发（编辑/新增均生效） |
| URL 中只有 `{{上下文变量}}`，无表单字段引用 | 仅新增时触发一次 |

## Python 配置方式

在 `desform_creator.py` 的 JSON 配置中，通过字段的 `remoteAPI` 属性设置：

```json
{
  "name": "真实姓名",
  "type": "input",
  "remoteAPI": "/desform/api/getName?userId={{sysUserCode}}"
}
```

在 `desform_utils.py` 的控件工厂函数中，通过 `remote_api` 参数传入：

```python
INPUT('真实姓名', remote_api='/desform/api/getName?userId={{sysUserCode}}')
MONEY('合同金额', required=True, remote_api='/api/getAmount?id=${_id}')
SELECT('状态', ['启用', '禁用'], remote_api='https://api.example.com/getStatus?op={{sysUserCode}}')
```

所有主表控件工厂函数均支持 `remote_api` 关键字参数（通过 `make_widget` 统一处理），子表控件不支持。

## 测试用接口地址

| 适用控件 | 接口地址 |
|---------|---------|
| 文本框（input） | `http://api.jeecg.com/mock/36/getRealName` |
| 富文本（editor） | `http://api.jeecg.com/mock/36/getRichTextDetails` |
