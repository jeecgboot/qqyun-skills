# 关联 Online 表单（cgform）

## 一、概述

表单设计器（Desform）可绑定 Online 表单（cgform），实现：
- 基于 Online 字段自动生成 Desform 控件
- 数据双向同步（Desform ↔ Online）
- 支持一对一子表和一对多子表

绑定字段：`DesignForm.cgformCode` 存储 Online 表单的 tableName，`config.onlineForm` 存储于设计 JSON 中。

## 二、字段类型映射

| Online 类型 | Desform 控件 | 说明 |
|---|---|---|
| text | input | 文本 |
| password | input (showPassword) | 密码 |
| textarea | textarea | 多行 |
| radio | radio | 单选 |
| checkbox | checkbox | 多选 |
| list | select | 下拉单选 |
| list_multi | select (multiple) | 下拉多选 |
| date | date | 日期 |
| datetime | date (含时分秒) | 日期时间 |
| time | time | 时间 |
| popup / popup_dict / sel_search | table-dict | 弹窗选择 |
| umeditor | editor | 富文本 |
| sel_depart | select-depart | 部门 |
| sel_user | select-user | 用户 |
| image | imgupload | 图片 |
| file | file-upload | 文件 |
| pca | area-linkage | 省市级联 |
| switch | switch | 开关 |
| markdown | markdown | Markdown |
| cat_tree / sel_tree | select-tree | 树选择 |

不支持的类型或子表不支持的类型降级为 `input`。

**自动忽略的字段**：id, create_by, create_time, update_by, update_time, sys_org_code, has_child

## 三、一对一子表（relationType=1）

**Desform 表现**：
- 使用 Card 容器包装子表字段
- model 格式：`{子表名}#{字段名}`（如 `sub_user#username`）
- modelType：`sub_one2one`

**数据存储**：
```json
// Desform 内部
{ "sub_user#username": "张三", "sub_user#phone": "138xxx" }

// 同步到 Online 时转换
{ "sub-table-one2one_sub_user": [{"username": "张三", "phone": "138xxx"}] }
```

## 四、一对多子表（relationType=0）

**Desform 表现**：
- 使用 `sub-table-design` 组件
- model 格式：`sub_table_design_{子表名}`
- 子表内每个字段标记 `isSubItem: true`

**数据存储**：
```json
// Desform 内部
{ "sub_table_design_order_detail": [
    {"_id": "row1", "item": "A", "qty": 10},
    {"_id": "row2", "item": "B", "qty": 20}
]}

// 同步到 Online 时，去掉前缀
{ "order_detail": [{"item": "A", "qty": 10}, {"item": "B", "qty": 20}] }
```

## 五、数据同步机制

### 保存（Desform → Online）

1. 提取 desformDataJson 数据
2. 一对一：`sub_user#username` → `sub-table-one2one_sub_user[0].username`
3. 一对多：遍历数组，转换多选/文件/日期格式
4. 调用 Online API：新增 `cgformPostCrazyForm` / 修改 `cgformPutCrazyForm`
5. 保存 `onlineFormDataId`

### 加载（Online → Desform）

1. 通过 `onlineFormDataId` 调用 Online API
2. 返回 `main`、`one2one`、`one2many` 三部分
3. 一对一数据展平为 `{子表名}#{字段名}`
4. 一对多数据映射到 `sub-table-design` 的 model
5. 合并为单一 JSON

### 数据格式转换

| Desform 类型 | 保存到 Online 的转换 |
|---|---|
| checkbox / select(多选) | JSON 数组 → 逗号分隔字符串 |
| imgupload / file-upload | 对象数组 → URL 逗号分隔 |
| date (timestamp) | 时间戳 → 日期字符串 |
| select-user / select-depart | 数组 → 逗号分隔 |

## 六、关键实体字段

| 字段 | 位置 | 说明 |
|------|------|------|
| `cgformCode` | DesignForm | 绑定的 Online 表单 tableName |
| `onlineFormCode` | DesignFormData | Online 表单编码 |
| `onlineFormDataId` | DesignFormData | Online 数据记录 ID |
| `config.onlineForm` | 设计 JSON | Online 绑定标记 |
