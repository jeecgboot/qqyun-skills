# 字典数据源配置

对于 radio/select/checkbox 控件，数据源有两种方式。

## 方式一：静态选项（默认）

**⚠️ `showLabel` 与 label 字段的关系（易错点）：**

只有当 `showLabel: true` 时，options 数组中的 `label` 字段才会被渲染到页面上，否则前端只显示 `value`。

| 场景 | 正确写法 |
|------|---------|
| value 与显示文本相同（直接用文字作为 value） | 字符串列表，`showLabel: false`（默认） |
| value 与显示文本不同（如 value="1"，显示"一年级"） | dict 列表含 `label`，必须同时设 `showLabel: true` |

```json
// ✅ value 即显示文本（如枚举中文选项）— showLabel 可为 false
"options": {
  "remote": false,
  "showLabel": false,
  "options": [
    { "value": "待审核", "itemColor": "#2196F3" },
    { "value": "已通过", "itemColor": "#08C9C9" }
  ]
}

// ✅ value 与 label 不同（如数字编码 + 中文描述）— 必须 showLabel: true
"options": {
  "remote": false,
  "showLabel": true,
  "options": [
    { "value": "1", "label": "一年级", "itemColor": "#2196F3" },
    { "value": "2", "label": "二年级", "itemColor": "#08C9C9" }
  ]
}
```

> **脚本自动处理**：通过 `desform_creator.py` 的 JSON 配置或 `RADIO`/`SELECT`/`CHECKBOX` 函数传入 `{value, label}` 格式时，脚本会自动检测并设置 `showLabel: true`，无需手动干预。手动构造 desformDesignJson 时需自行保证一致。

## 方式二：系统字典

当用户描述中提到「字典」、「数据字典」或使用了 JeecgBoot 常见字典编码（如 sex、priority、valid_status 等），使用字典配置：

```json
"options": {
  "remote": "dict",
  "dictCode": "sex",
  "showLabel": true,
  "options": [],
  "remoteOptions": [],
  "props": { "value": "value", "label": "label" }
}
```

同时在**控件顶层**（与 options 同级）添加 `dictOptions`：
```json
"dictOptions": [
  { "value": "1", "label": "男" },
  { "value": "2", "label": "女" }
]
```

## 常用 JeecgBoot 系统字典编码

| 字典编码 | 说明 | 典型值 |
|---------|------|--------|
| `sex` | 性别 | 1=男, 2=女 |
| `priority` | 优先级 | L=低, M=中, H=高 |
| `valid_status` | 有效状态 | 0=无效, 1=有效 |
| `msg_category` | 消息类型 | 1=通知, 2=系统 |
| `send_status` | 发送状态 | 0=未发送, 1=已发送 |
| `yn` | 是否 | Y=是, N=否 |

> **提示：** 当用户指定的字典编码不确定是否存在时，可通过 API `GET /sys/dict/getDictItems/{dictCode}` 查询确认。如果用户只说了"用字典"但未指定编码，需要询问具体的字典编码。

## desform_utils.py 快捷函数使用字典的正确写法

> **踩坑警告：** `RADIO`/`SELECT`/`CHECKBOX` 的 `options` 是**必填位置参数**，使用字典时也不能省略。
> 当指定 `dict_code` 时，`options` 参数必须传**字典项列表**（`[{value, label}]` 格式），不要传字符串列表。
> **不存在** `dict_options` 关键字参数，不要传它（会报 `unexpected keyword argument` 错误）。

```python
# 正确 ✅ — options 传字典项列表 + dict_code
RADIO('性别', [{'value': '1', 'label': '男'}, {'value': '2', 'label': '女'}], dict_code='sex')
SELECT('状态', [{'value': '0', 'label': '无效'}, {'value': '1', 'label': '有效'}], dict_code='valid_status')

# 错误 ❌ — 缺少 options 位置参数
RADIO('性别', dict_code='sex')

# 错误 ❌ — 不存在 dict_options 参数
RADIO('性别', ['男', '女'], dict_code='sex', dict_options=[...])

# 不用字典时，options 传字符串列表即可
SELECT('职称', options=['教授', '副教授', '讲师', '助教'])
```

## 底层 `make_widget` 函数中字典的实现原理（仅供参考）

```python
# desform_utils.py 内部处理逻辑：
if dict_code:
    opts["remote"] = "dict"
    opts["dictCode"] = dict_code
    opts["showLabel"] = True
    opts["options"] = []
    extra["dictOptions"] = options if isinstance(options[0], dict) else []
```
