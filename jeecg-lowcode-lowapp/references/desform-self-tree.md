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
>
> ⚠️ **2026-09-17 实测追问：自关联控件漏写 `isSelf`/`valueSplit` 会被设计器当成通用「树控件」**。
> 全租户扫描：平台自己建的自关联控件（7 个样例）**无一例外**都带 `isSelf: true` + `valueSplit: ''`；
> 用工厂建、只写 `sourceCode=本表 code` 的控件（本项目 任务/费用科目/WBS任务模板 各 2 个）
> 在设计器里显示为「关联记录 - 树控件」，用户报「应该是关联记录 自己关联自己」。补上两键即恢复。

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

自关联树 `showType` **必须**用 `"card"`（系统对自关联有特殊的树形展示支持）。
⛔ **显示方式只有 卡片 / 下拉 / 表格 三档，没有独立的「树」**——树形是卡片模式自带的
（父记录以卡片呈现、点开展开子树）。2026-09-17 用户问「是不是只有卡片？能支持树」时实测核对：
租户里平台/其他应用自建的 8 个自关联控件，**7 个 card**（人事管理·部门表 上级部门、教育管理·课程分类表 上级分类、
关联记录·商品表 上级商品、供应商管理·采购批次 父/子、销售记录·订单明细 订单信息），仅 1 个 select（员工信息表 直属上级）。
👉 自关联的一对控件（父侧 single + 子侧 many）**两侧都写 card**，不要按普通关联的习惯给父侧配下拉、子侧配表格，

| showType | 说明 |
|----------|------|
| `card`（卡片） | 展示父记录的卡片，点击可展开子树，推荐 |
| `select`（下拉） | 从下拉列表选父记录，数据量大时可配合搜索 |
| `table`（表格） | showMode 为 single 时不推荐 |

### ⛔ 别无意中建两个自关联控件（父子字段取「最后一个」；简流要写值时是**唯一例外**，见 3）

2026-09-17 实测（前端源码 `useFilterField` + 后端接口双验证）：

- **表格视图的树是自动开的**：表里有 `link-record` + `isSelf` 时，前端 `BaseList` 会给列表请求带上
  `parentField`（父子字段 model）+ `parentId`，行上带 `__HAS_CHILD`，展开时按 `parentId` 拉子级
  （`BasicTable` 的 `isTreeTable`，平台菜单/流程实例列表也在用）。后端 `POST/GET /desform/data/list`
  实测：`parentField` + 空 `parentId` 只返回**根记录**、`parentId=<父id>` 只返回**子记录**，
  `__HAS_CHILD` 在 `desformDataJson` 里。
- **父子字段取的是「设计里遍历到的最后一个自关联控件」**：`useFilterField` 里
  `(t.type==='link-record' && t.isSelf && (l.is=true, l.field=t.model), …)`——**无条件覆盖**。
  遍历顺序（`Fe()`）= 数组顺序，容器（`isContainer` 的 grid 的 `columns` / `card` 的 `list` /
  `tabs` 的 `panes`）先递归子级、再算自己。
- ⇒ **一张表里建「父(单条) + 子(多条)」两个自关联，且多条侧排在后面时，会被选成父子字段 → 树是反的**
  （实测：拿多条侧当 `parentField`，返回的根记录是叶子）。

**正确做法（三选一）：**
1. **只建单条侧这一个自关联**（平台建的部门表/商品表/课程分类表都这样）——最简单、最稳，推荐；
2. 非要建一对，就把**单条侧放在最后**（平台建的供应商管理·采购批次：`子` 在前、`父` 在后）。
   ⚠️ 顺序 = 设计 JSON 的数组顺序 = 表单上的显示顺序，改了顺序表单排版也跟着变。
3. **简流要往这张表的自关联字段写值时，必须再压一个隐藏占位自关联在最前面**（2026-09-21 实测）。
   - 后端 `handleTreeTableParentField` 取的是设计里**第一个** isSelf
     （`DesignFormDataServiceBaseImpl:2805` `.filter(isSelf).findFirst()`），而**简流写关联字段下发的是裸字符串**
     （新增/更新节点都是；`variableValue:"_id"` 与指向关联控件都一样），平台那步 `getJSONArray()` 直接崩：
     `操作失败：offset 1, character 2, line 1, column 1, fastjson-version 2.0.58 <记录id>`。
   - **这个错抛在 `save(...)` 之后**（mongo 不在 Spring 事务里），后果三条：
     ① 新增节点每次执行都崩 → Flowable **重试 3 次** → **一次建出 3 条重复子记录**；
     ② 库里**原样存裸串**（不归一）→ 该记录之后**编辑、删除都撞同一个错**（连删都删不掉）；
     ③ 崩在写 `__HAS_CHILD` 之前 → **父行永远没有展开箭头**。
   - 占位控件永远不被写值 → 后端读到空 → 直接 return，不再崩；**列表视图取的是最后一个**（见上）→ 树仍取真字段。
   - 占位控件照抄真自关联的 options，改这几项：`hidden:true`、`hiddenOnAdd:true`、`disabled:true`、
     `allowAdd/allowSelect/allowEdit/allowView:false`、`required:false`、`defaultValue:''`，并用**新的 model/key**。
   - **代价**：平台不再自动给父行写 `__HAS_CHILD` → 改由流程的「更新记录」节点自己写；
     该节点来源是多条时**必须带 `formTableSourceGetDataType:1`**，否则引擎**静默不写库**（保存/发布全绿、箭头不出来）。
   - **判定**（不用跑流程）：挑一条自关联字段有值的记录做一次**无操作** `desform/data/edit`
     （读出原文再原样写回）——有裸串时必失败，修好后必成功。

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

> **注意：简流（miniflow 的「新增/更新记录」节点）做不到上面这一点** —— 它固定下发裸串，
> 所以那种表要压占位自关联（本页第 3 条），不是靠改流程取值写法能解决的。
```

---

## 与 desform-cross-form-binding 的区别

| 场景 | 推荐文档 |
|------|---------|
| 同一表单内记录互相引用（本文档） | `desform-self-tree.md` |
| 两个不同表单互相关联 | `desform-cross-form-binding.md` |
| 一个表单关联另一个表单（单向） | `desform-link-record.md` |

---

## 实测补充（2026-09-21 项目管理三版报障）：`options.isSelf` / `options.valueSplit` 不是可选项

平台/二版自己建的自关联控件，**三处**都带：

| 位置 | 键 | 二版四个自关联控件 | 三版漏写后 |
|---|---|---|---|
| 控件顶层 | `isSelf: true` | 有 | 有（构建器 `is_self=True` 写的） |
| 控件 `options` | `isSelf: true` ＋ `valueSplit: ""` | 有 | **缺** |
| `advancedSetting.defaultValue` | `valueSplit: ""` | 有 | 视写法而定 |

**症状**：设计里 `options.hidden: true` 的「上级任务占位」**在列表里露成一列**（表头就是控件名），
用户当场报障；自关联的父级回写 / 树展开逻辑也认不到这个控件。
**修法**：对照二版把 `options.isSelf` / `options.valueSplit` 补齐 → 整表回存 → 回读断言三处都命中。
**教训**：建表时一次写全三处；事后补要整表回存，还有被设计器改回去的风险。

---

## 实测补充（2026-09-24 项目管理）：`__HAS_CHILD` 控件的 `model` 必须是**字面量**

**现象**：自关联的父子两侧、顺序（占位在前）、`isSelf` 三处全齐，子记录也挂上了父级；
但**任务列表展不开**——树模式下根查询只返回根记录，父行没有展开箭头，子行永远拉不出来。

**根因**：展开箭头靠父行数据里的**字面键 `__HAS_CHILD`**（前端固定读这个键，不是控件 model）。
而简流「更新记录」节点写库，是**按目标控件的 `model` 当字段名**写的。建表时这个控件若被自动命名成
`input_<key>`（工厂默认命名），流程就把 `'true'` 写进 `input_1790…`，前端读 `__HAS_CHILD` 读到空 → 没箭头。

**30 秒自检**：拿一条**真有子级**的父行看库里的键——
`{"__HAS_CHILD": "true"}` ✓ ／ `{"input_1790…": "true"}` ✗（名字对不上，前端看不见）。

**修法**：
1. `query_form` → 把该控件 `model` 改成字面量 `'__HAS_CHILD'`（`key` 保持自动命名即可；
   平台样表就是 key 自动、model 字面量）→ `save_design_from_file` → `save_auth_from_design`；
2. 流程里 `updateFields[].field` 由旧 model 改成 `'__HAS_CHILD'`，重存重发布。

**教训（比这一条本身更重要）**：排查「流程明明执行了却不生效」时，先对齐
**控件 model == 写库的键 == 前端读的键**，再怀疑「节点没执行」——
只看自己以为的那个键，会得出完全反向的结论（本次为此绕了几小时）。
