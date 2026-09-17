# 表单数据树（自关联树）

## 概念说明

表单数据树是一种**数据层级结构**，与"树控件"（select-tree）完全不同：

| 对比项 | select-tree（树控件） | 表单数据树（自关联） |
|--------|----------------------|---------------------|
| 本质 | 输入控件，从预定义树形分类中选值 | 表单记录之间的父子关系 |
| 数据来源 | 固定的分类字典或数据库表 | 表单自身的记录 |
| 树的节点 | 字典/分类条目 | 表单的每一条记录 |
| 典型场景 | 选省市区、选行业分类 | 组织层级、任务分解、部门结构 |

**表单数据树的核心思想**：表单的每条记录都可以通过一个"关联记录"字段，指向同一表单中的另一条记录作为其父节点，从而形成任意深度的树状层级。

### 典型使用场景

- **组织架构**：部门表中，每个部门通过"上级部门"字段关联同表中另一个部门
- **任务分解**：任务表中，子任务通过"父任务"字段指向主任务
- **分类目录**：分类表中，子分类指向父分类（无限级）
- **区域层级**：地区表中，县/市/省之间互相关联

---

## 配置方法

### 核心原理

在表单中添加一个 `link-record`（关联记录）控件：
- `options.sourceCode` 设置为**本表单自身的 `desformCode`**
- 控件顶层设置 `isSelf: true`（与 `type`/`key`/`model` 同级，不在 `options` 内）

### 一步到位：直接写入 JSON 配置（推荐）

`desform_creator.py` 支持将 `titleField` 写为**字段中文名**，创建时自动解析为实际 model——无需分阶段，一条命令完成：

```json
{
  "formName": "部门管理",
  "formCode": "org_department",
  "fields": [
    {"type": "input", "name": "部门名称", "required": true},
    {"type": "input", "name": "部门编号"},
    {"type": "textarea", "name": "备注"},
    {
      "type": "link-record",
      "name": "上级部门",
      "sourceCode": "org_department",
      "titleField": "部门名称",
      "showMode": "single",
      "showType": "card",
      "isSelf": true
    }
  ]
}
```

脚本会在构建所有字段后自动将 `"部门名称"` 解析为实际 model（如 `input_xxx`），并在控件顶层写入 `isSelf: true`。

### 完整 widget 结构（实测验证，仅供参考）

```json
{
    "type": "link-record",
    "name": "上级部门",
    "className": "form-link-record",
    "icon": "icon-link",
    "hideTitle": false,
    "key": "1775738525987_231329",
    "model": "link_record_1775738525987_231329",
    "modelType": "main",
    "isSelf": true,
    "isSubItem": false,
    "rules": [],
    "remoteAPI": { "url": "", "executed": false },
    "advancedSetting": {
        "defaultValue": {
            "type": "compose",
            "value": "",
            "format": "string",
            "allowFunc": true,
            "valueSplit": "",
            "customConfig": true
        }
    },
    "options": {
        "sourceCode": "my_form_code",
        "showMode": "single",
        "showType": "card",
        "titleField": "input_1775737429491_692500",
        "showFields": [],
        "allowView": true,
        "allowEdit": true,
        "allowAdd": true,
        "allowSelect": true,
        "buttonText": "添加记录",
        "twoWayModel": "",
        "dataSelectAuth": "all",
        "filters": [{ "matchType": "AND", "rules": [] }],
        "search": { "enabled": false, "field": "", "rule": "like", "afterShow": false, "fields": [] },
        "createMode": { "add": true, "select": false, "params": { "selectLinkModel": "" } },
        "width": "100%",
        "defaultValue": "",
        "defaultValType": "none",
        "required": false,
        "disabled": false,
        "hidden": false,
        "hiddenOnAdd": false,
        "fieldNote": "",
        "autoWidth": 33.333
    }
}
```

**与普通 link-record 的差异：**

| 属性 | 普通 link-record | 自关联树 |
|------|-----------------|---------|
| `isSelf`（顶层） | 不存在 / false | **`true`** |
| `options.sourceCode` | 其他表单的 code | **本表单自身的 code** |
| `advancedSetting.valueSplit` | `","` | **`""`**（空串） |
| `advancedSetting.customConfig` | `true` | `true`（相同） |

> `isSelf` 必须是控件的**顶层属性**，放在 `options` 内部无效。

---

## 两阶段创建法（仅当无法使用 desform_creator.py 时）

> 通常不需要此方法，优先使用上方的一步到位 JSON 配置。仅在需要直接调用 Python API 的场景下使用。

**阶段一**：先创建表单主体，不包含自关联字段

```json
{
  "name": "部门管理",
  "code": "org_department",
  "fields": [
    { "type": "input", "name": "部门名称", "required": true },
    { "type": "input", "name": "部门编号" },
    { "type": "textarea", "name": "备注" }
  ]
}
```

**阶段二**：查询创建后的字段 model，再追加自关联字段

```python
from desform_utils import init_api, get_form_fields, add_widget, LINK_RECORD

init_api('<api_base>', '<token>')

# 1. 获取标题字段 model
title_field, fields_map = get_form_fields('org_department')
dept_name_model = fields_map['部门名称']['model']

# 2. 构造自关联控件（is_self=True 自动处理顶层 isSelf 和 valueSplit）
widget, key, model = LINK_RECORD(
    '上级部门',
    source_code='org_department',   # 关联自身
    title_field=dept_name_model,
    show_mode='single',
    show_type='card',
    is_self=True,                   # 标记为自关联树
    wrap=False                      # 不需要 card 包裹，直接追加
)

add_widget('org_department', widget)
print("自关联字段添加成功")
```

---

## 关键配置说明

### `showType` 的选择

自关联树 `showType` 默认推荐 `"card"`（系统对自关联有特殊的树形展示支持）：

| showType | 说明 |
|----------|------|
| `card`（卡片） | 展示父记录的卡片，点击可展开子树，推荐 |
| `select`（下拉） | 从下拉列表选父记录，数据量大时可配合搜索 |
| `table`（表格） | showMode 为 single 时不推荐 |

### `showMode` 的选择

- 大多数树场景：`showMode: "single"`（一条记录只有一个父节点）
- 多父节点场景（DAG 结构）：`showMode: "many"`

### 防止循环引用

系统不会自动阻止循环引用（A 是 B 的父，B 又是 A 的父）。如需防止：
- 添加 JS 增强校验（见 `references/desform-js-enhance.md`）
- 在自定义接收 URL 中校验（见 `references/desform-custom-receive-url.md`）

---

## 自关联树数据新增（实测验证）

新增子记录时，link-record 字段值必须是 **Python list**，`add_data` 内部的 `json.dumps` 会将其序列化为 JSON 数组 `["parentId"]`，与前端行为一致：

```python
from desform_data_utils import add_data

# ✅ 正确：传 Python list
add_data('org_department', {
    'input_xxx':       '财务部',
    'link_record_xxx': ['2042226506569424897'],  # 父节点 ID，用 list 包裹
})

# ❌ 错误：json.dumps([id]) 会二次序列化，服务端存入错误格式
# ❌ 错误：裸字符串 ID，服务端 fastjson 报错（记录仍入库但格式错误）
```

---

## 与 desform-cross-form-binding 的区别

| 场景 | 推荐文档 |
|------|---------|
| 同一表单内记录互相引用（本文档） | `desform-self-tree.md` |
| 两个不同表单互相关联 | `desform-cross-form-binding.md` |
| 一个表单关联另一个表单（单向） | `desform-link-record.md` |
