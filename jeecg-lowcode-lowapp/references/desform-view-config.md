# 表单视图创建完整指南

## 表单视图类型

- **主表单视图**（desformType=1）：默认创建的表单
- **子表单视图**（desformType=2）：基于主表单视图创建的表单视图变体，通过 `parentId/parentCode` 关联

> 优先使用 `scripts/desform_view_creator.py` 通用脚本创建表单视图，支持复制主表单视图或自定义字段两种模式。

## 命令行参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--api-base` | 是 | JeecgBoot 后端地址 |
| `--token` | 是 | X-Access-Token |
| `--parent-code` | 是 | 主表单编码（desformType=1 的表单） |
| `--view-name` | 是 | 表单视图名称 |
| `--view-code` | 是 | 表单视图编码 |
| `--mobile` | 否 | 设为移动端表单视图 |
| `--config` | 否 | 自定义字段 JSON 配置文件 |
| `--force` | 否 | 强制覆盖已存在的表单视图 |

## 两种创建模式

### 模式一：复制主表单视图（不传 --config）

直接复制主表单视图的 desformDesignJson 创建子表单视图。最简方式，无需准备 JSON 文件。

```bash
# PC 表单视图（原样复制主表单视图设计）
python desform_view_creator.py --api-base <URL> --token <TOKEN> \
    --parent-code proj_task_management \
    --view-name "项目任务-简洁视图" --view-code proj_task_simple

# 移动端表单视图（复制 + 自动应用移动端优化）
python desform_view_creator.py --api-base <URL> --token <TOKEN> \
    --parent-code proj_task_management \
    --view-name "项目任务-移动端" --view-code proj_task_mobile --mobile
```

### 模式二：自定义字段（传 --config）

使用独立的 JSON 配置文件定义表单视图字段，格式与 `desform_creator.py` 的配置相同（见 `desform-json-config.md`），但 **formName/formCode 不写在 JSON 中**，而是由命令行的 `--view-name` / `--view-code` 传入。

```bash
python desform_view_creator.py --api-base <URL> --token <TOKEN> \
    --parent-code proj_task_management \
    --view-name "项目任务-移动端" --view-code proj_task_mobile \
    --config mobile_view.json --mobile
```

## 自定义表单视图 JSON 配置格式

```json
{
  "layout": "full",
  "titleIndex": 0,
  "fields": [
    {"name": "字段名", "type": "控件类型", ...控件参数}
  ],
  "expand": {
    "js": "// 可选 JS 增强",
    "css": "/* 可选 CSS 增强 */"
  }
}
```

| JSON 字段 | 必填 | 默认值 | 说明 |
|-----------|------|--------|------|
| `layout` | 否 | `"full"` | 布局模式：`auto`/`half`/`full`/`word`（移动端推荐 `full`） |
| `titleIndex` | 否 | `0` | 标题字段在 fields 中的索引 |
| `fields` | 是 | - | 字段定义数组（格式与 desform_creator.py 完全一致） |
| `expand` | 否 | - | JS/CSS 增强配置 |

> **注意：** `formName` 和 `formCode` **不在** JSON 配置中，由命令行参数传入。

### fields 格式

与 `desform_creator.py` 完全一致，支持所有控件类型和参数。详见 `desform-json-config.md`。

---

## `--mobile` 自动优化规则

当使用 `--mobile` 参数时，脚本会自动对设计 JSON 应用以下优化（无论是复制主表单视图还是自定义配置）：

| 优化项 | 规则 | 说明 |
|--------|------|------|
| `config.designMobileView` | → `true` | 标记为移动端表单视图 |
| 所有控件 `autoWidth` | → `100` | 单列全宽显示 |
| `radio`/`checkbox` | 添加 `mobileOptions: {inline: true, matrixWidth: 80}` | 选项横向排列 |
| `date`/`time` | 添加 `mobileOptions: {editable: false}` | 禁止手动输入，仅弹窗选择 |
| `sub-table-design` | `operationMode` → `2` | 子表切换为弹出编辑（移动端行内编辑体验差） |

> **注意：** 如果控件已有 `mobileOptions`，脚本不会覆盖（用户手动配置优先）。

---

## 移动端表单视图设计规范

当设计移动端表单视图时（`izMobileView=1` 或 `config.designMobileView=true`），AI 应遵循：

1. **单列布局**：所有控件 autoWidth 设为 100，不使用半行布局
2. **简化字段**：精简核心信息，次要字段设 `hiddenOnAdd: true`
3. **避免复杂容器**：不用 Grid 多列、Tabs，改用 Divider 分区
4. **输入友好**：date/time 设 `mobileOptions: {editable: false}`；radio/checkbox 设 `mobileOptions: {inline: true}`
5. **子表优化**：使用 `operationMode: 2`（弹出编辑）
6. **layout 选择**：移动端表单视图使用 `layout='full'`

> **最佳实践**：移动端表单视图优先使用 `--mobile` 复制主表单视图并自动优化，而非手动构建全部控件。`--mobile` 已自动覆盖上述规范中的第 1/4/5 条。

---

## Python API 方式（备用）

当通用脚本无法满足需求时，可直接使用 Python API：

```python
create_view(parent_code, view_name, view_code, design_json=None, is_mobile=False)
```

- `design_json=None` 时自动复制主表单视图的设计 JSON
- `is_mobile=True` 时设为移动端表单视图（同一主表单视图下只能有一个）

---

## 完整示例

### 示例一：为主表单创建 PC + 移动端两个表单视图

```bash
# 假设已有主表单 proj_task_management

# 步骤 1：创建 PC 表单视图（复制主表单视图设计）
python desform_view_creator.py --api-base <api_base> \
    --token <TOKEN> \
    --parent-code proj_task_management \
    --view-name "项目任务管理-简洁视图" --view-code proj_task_mgmt_simple

# 步骤 2：创建移动端表单视图（复制主表单视图 + 移动端优化）
python desform_view_creator.py --api-base <api_base> \
    --token <TOKEN> \
    --parent-code proj_task_management \
    --view-name "项目任务管理-移动端" --view-code proj_task_mgmt_mobile --mobile
```

### 示例二：使用自定义字段配置创建移动端精简表单视图

**mobile_view.json:**
```json
{
  "layout": "full",
  "titleIndex": 1,
  "fields": [
    {"name": "---", "type": "divider", "text": "基本信息"},
    {"name": "任务编号", "type": "auto-number", "prefix": "TASK"},
    {"name": "任务名称", "type": "input", "required": true},
    {"name": "任务类型", "type": "select", "options": ["需求开发", "缺陷修复", "技术优化"], "required": true},
    {"name": "优先级", "type": "radio", "options": [{"value": "P0", "label": "紧急"}, {"value": "P1", "label": "高"}, {"value": "P2", "label": "中"}]},
    {"name": "当前状态", "type": "select", "options": ["待分配", "进行中", "已完成"], "required": true},
    {"name": "---", "type": "divider", "text": "人员"},
    {"name": "负责人", "type": "select-user", "required": true},
    {"name": "所属部门", "type": "select-depart", "required": true},
    {"name": "---", "type": "divider", "text": "时间"},
    {"name": "计划开始日期", "type": "date", "required": true},
    {"name": "计划结束日期", "type": "date", "required": true},
    {"name": "完成进度", "type": "slider"},
    {"name": "---", "type": "divider", "text": "附件"},
    {"name": "任务描述", "type": "textarea"},
    {"name": "相关附件", "type": "file-upload"},
    {"name": "负责人签字", "type": "hand-sign", "required": true}
  ]
}
```

```bash
python desform_view_creator.py --api-base <api_base> \
    --token <TOKEN> \
    --parent-code proj_task_management \
    --view-name "项目任务管理-移动端" --view-code proj_task_mgmt_mobile \
    --config mobile_view.json --mobile
```

---

## 实战踩坑汇总

### 1. create_view 的 design_json 参数格式

`create_view()` 的 `design_json` 接受 **JSON 字符串** 或 **dict**（包含 `{"list": [...], "config": {...}}` 完整结构）。

**常见错误：** 直接传入 Python 工厂函数返回的 tuple 列表（如 `[INPUT('姓名'), DATE('日期')]`），这些是 `(widget_dict, key, model)` 三元组，不是设计 JSON。

**正确做法：** 使用 `build_design_json()` 组装，或使用 `desform_view_creator.py` 脚本自动处理。

### 2. SUB_* 工厂函数需要 parent_key

`SUB_INPUT`、`SUB_SELECT` 等子表内控件工厂函数的第二个位置参数是 `parent_key`（子表的 key），不能脱离 `make_sub_table` 上下文单独使用。

**在 JSON 配置中不受此限制**——`desform_view_creator.py` 和 `desform_creator.py` 内部自动处理 `parent_key`。

### 3. 移动端表单视图推荐"复制 + 优化"模式

手动构建移动端表单视图的全部控件容易遗漏 `parent_key`、`config` 结构等细节。推荐做法：

1. 先创建主表单
2. 使用 `--mobile` 复制主表单视图并自动优化
3. 如需精简字段，使用 `--config` 自定义字段列表 + `--mobile` 自动优化

### 4. 同一主表单视图下只能有一个移动端表单视图

JeecgBoot 限制每个主表单最多一个 `izMobileView=1` 的子表单视图。创建第二个移动端表单视图前需先删除旧的，或使用 `--force` 覆盖。

### 5. 表单视图编码查询

`query_form(code)` 默认按编码查询，但可能查不到子表单视图（取决于后端实现）。如需查询子表单视图详情，使用 `get_form_id(view_code)` 获取 ID。
