# 两种子表风格详解

## 别名对照

- **设计子表**（sub-table-design）= **内部子表**（数据内嵌于主表）
- **工作表子表**（link-record + isSubTable=true）= **外部子表**（数据存储在独立工作表）

> 当用户提及"内部子表"、"嵌入子表"、"内嵌子表"时 → 设计子表
> 当用户提及"外部子表"、"独立子表"、"工作表子表"、"关联子表"时 → 工作表子表

## 完整对比

| 维度 | 内部子表（sub-table-design） | 外部子表（link-record + isSubTable） |
|------|---------------------------|-----------------------------------|
| 数据存储 | 嵌入主表 JSON 字段中 | 独立工作表，独立数据空间 |
| 数据库表 | 与主表共享同一条记录 | 独立的 design_form + design_form_data |
| 控件支持 | 28 种（受限于 subTableCheckType） | 不受限，等同于普通表单 |
| 编辑模式 | 行内编辑(1) / 弹出编辑(2) | 同 link-record 展示模式 |
| 数据量限制 | 建议 < 200 行（受主表 JSON 大小限制） | 无限制 |
| 独立访问 | 不可独立访问 | 可独立作为工作表访问 |
| 权限控制 | 跟随主表权限 | 可独立配置权限 |
| 查询性能 | 查主表即得（一次查询） | 需关联查询 |
| 可转换性 | 可转为外部子表 | 不可逆转回内部子表 |

## 一、内部子表（sub-table-design）

### 核心配置

```json
{
  "type": "sub-table-design",
  "isContainer": true,
  "columns": [
    { "span": 12, "list": [/* 子表内控件 */] },
    { "span": 12, "list": [/* 子表内控件 */] }
  ],
  "options": {
    "columnNumber": 2,
    "operationMode": 1,
    "subTableName": "",
    "defaultRows": 0,
    "showCheckbox": true,
    "showNumber": true,
    "showRowButton": false,
    "allowAdd": true,
    "autoHeight": true,
    "isWordStyle": false,
    "isWordInnerGrid": false
  }
}
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `columnNumber` | 布局列数（需与 columns 长度一致） |
| `operationMode` | 1=行内编辑 2=弹出编辑 |
| `subTableName` | 子表名（Online 绑定时使用） |
| `defaultRows` | 默认预填行数 |
| `showCheckbox` | 显示选择框 |
| `showNumber` | 显示序号 |
| `allowAdd` | 允许新增行 |
| `isWordStyle` | Word 表格风格 |

### 数据存储格式

```json
{
  "main_field": "value",
  "sub_table_design_xxx": [
    { "_id": "row_001", "field_a": "val1", "field_b": 100 },
    { "_id": "row_002", "field_a": "val2", "field_b": 200 }
  ]
}
```

`_id` 由后端自动生成，用于行标识。

### 支持的控件（源码 subTableSupportTypes）

input, textarea, number, integer, money, date, time, radio, checkbox, select, switch, slider, rate, color, phone, email, imgupload, file-upload, area-linkage, select-user, select-depart, select-depart-post, org-role, formula, link-record, link-field, **capital-money, text-compose**（LHZP-1984）

子表清单里有 **联动 `category-linkage`**，以及源码里的 `table-dict` / `select-tree`，但敲敲云 skill **不允许使用**，禁止生成。

全新创建时**不支持**的 type（布局/高级控件）见 `desform-json-config.md`「全新创建的设计子表不支持的 type」。

### Python 用法

```python
sub = make_sub_table('订单明细', [
    SUB_INPUT('产品名称', sub_key, required=True),
    SUB_NUMBER('数量', sub_key),
    SUB_MONEY('单价', sub_key),
    SUB_FORMULA('小计', sub_key, mode='PRODUCT', expression='$数量model$*$单价model$'),
])

create_form('采购订单', 'purchase_order', [
    INPUT('订单号', required=True),
    DATE('下单日期'),
    sub,
])
```

> ⚠️ **2026-09-14 实测大坑（人事OA 30 表整单补丁踩毁 1 表）：上面示例只在 `create_form` 路径下安全（布局引擎会解包）。手工把 `make_sub_table` 结果插入**已有表单**的 `design['list']` 再走 `save_design_from_file` 时，必须自己做两层解包，否则整表报废：**
> 1. `make_sub_table(...)` 返回 `(container, key, model)` 三元组，插入 design 前取 `[0]`；
> 2. **`container['columns'][].list` 里每个子控件还是 `SUB_*` 的 `(widget, key, model)` 三元组未解包**——必须二次解包 `w = w[0]`。漏了这一步 `json.dump` 会把 tuple 序列化成 JSON 数组，落库后子表列是数组不是控件对象；
> 3. **保存接口不校验结构，照样返回"保存成功"；下次 `queryByCode/queryById` 遍历时对数组条目调 `getString("type")` 抛 NPE（`...because "item" is null`），整张表查不出来**。insert 前本地校验：design['list'] 每项必须是 dict；sub-table-design 的 columns[].list 每项必须是 dict。
>
> **整表已损坏的修复**（query 全挂、`save_design_from_file` 因先 query 而拒存）：直接 `PUT /desform/edit`，body `{"id":"<formId>","desformDesignJson":"<修正后JSON>","updateCount":<当前值>,"autoNumberDesignConfig":{"update":{},"current":{}},"refTableDefaultValDbSync":{"changes":{},"removeKeys":[]}}`；`updateCount` 和 formId 从 `/desform/list` 记录取（queryById 已不可用）。修完立即回查 `queryByCode` 验证。

## 二、外部子表（link-record + isSubTable）

### 核心配置

```json
{
  "type": "link-record",
  "isSubTable": true,
  "options": {
    "sourceCode": "子工作表编码",
    "showMode": "many",
    "showType": "table",
    "titleField": "子表标题字段model",
    "showFields": ["field1", "field2"],
    "allowView": true,
    "allowEdit": true,
    "allowAdd": true,
    "allowSelect": true,
    "twoWayModel": "子表中反向 link-record 的 model"
  }
}
```

### 数据存储格式

主表：
```json
{ "link_record_xxx": ["sub_001", "sub_002"] }
```

子工作表（独立存储）：
```json
{ "_id": "sub_001", "field_a": "val1", "link_record_yyy": ["main_001"] }
```

### 创建方式

1. 在添加子表弹窗中选择"将已有工作表作为子表"
2. 从内部子表转换（右键 → "转为工作表"）

### Python 用法

```python
# 先创建子工作表
create_form('订单明细', 'order_detail', [
    INPUT('产品名称', required=True),
    NUMBER('数量'),
    MONEY('单价'),
])

# 主表中通过 link-record 关联
create_form('采购订单', 'purchase_order', [
    INPUT('订单号', required=True),
    LINK_RECORD('订单明细', source_code='order_detail',
                title_field='input_xxx', show_mode='many', show_type='table'),
])
```

## 三、内部子表转外部子表（subToWorksheet）

**触发**：内部子表右键 → "将子表转为工作表"

**转换流程**：
1. 提取内部子表所有控件，组装为新工作表设计 JSON
2. 自动为新工作表添加反向 link-record（双向关联）
3. 后端遍历主表数据，将子表数据迁移到新工作表
4. 建立双向关联（主表→子表ID列表，子表→主表ID）
5. 删除主表中原来的子表字段数据
6. `PUT /desform/edit`：主表该字段从 `sub-table-design` 换成 `link-record`（`isSubTable=true`）。`POST /subToWorksheet` **不会**改主表设计，缺这一步设计器仍显示内嵌子表

**不可逆**：转换后无法恢复为内部子表。

实际请求体、编码冲突处理、一键脚本见 `desform-new-sub-table.md`「转换工作表」。禁止猜 `id`/`widgetKey` 探测。

## 四、选型建议

| 场景 | 推荐 | 原因 |
|------|------|------|
| 数据行数 < 50，字段简单 | 内部子表 | 一次查询，高效 |
| 数据行数 > 100 | 外部子表 | 避免主表 JSON 过大 |
| 子表需要独立管理/查询 | 外部子表 | 支持独立访问 |
| 子表需要独立权限 | 外部子表 | 可独立配置 |
| 快速开发简单明细 | 内部子表 | 配置简单 |
| 与 Online 一对多对接 | 内部子表 | generateByCgform 自动映射 |
