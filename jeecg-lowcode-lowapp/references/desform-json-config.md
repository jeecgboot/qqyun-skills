# desform_creator.py JSON 配置格式

通用脚本 `scripts/desform_creator.py` 支持通过 JSON 配置文件创建表单，避免每次编写大量 Python 代码。

## JSON 顶层结构

```json
{
  "formName": "表单中文名称",
  "formCode": "module_form_code",
  "layout": "word",
  "titleIndex": 0,
  "fields": [
    {"name": "字段名", "type": "控件类型", ...控件参数}
  ],
  "menuParent": "父菜单名称",
  "menuIcon": "ant-design:appstore-outlined",
  "expand": {
    "js": "// JS 增强代码",
    "css": "/* CSS 增强代码 */",
    "url": {
      "js": "",
      "css": "/desform/expand/css/custom.css"
    }
  }
}
```

| JSON 字段 | 必填 | 默认值 | 说明 |
|-----------|------|--------|------|
| `formName` | 是 | - | 表单中文名称 |
| `formCode` | 是 | - | 表单编码（英文，模块名前缀） |
| `layout` | 否 | `"auto"` | 布局模式：`auto`/`half`/`full`/`word`（详见 `desform-layout.md`） |
| `titleIndex` | 否 | `0` | 标题字段在 fields 中的索引 |
| `fields` | 是 | - | 字段定义数组 |
| `menuParent` | 否 | - | 生成菜单 SQL 的父菜单名称 |
| `menuIcon` | 否 | `ant-design:appstore-outlined` | 父菜单图标 |
| `expand` | 否 | - | JS/CSS 增强配置（见下方说明） |

## 字段定义（fields 数组）

每个字段只需 `name` + `type`，其余参数可选：

```json
{"name": "工程名称", "type": "input", "required": true}
{"name": "工程类别", "type": "radio", "options": ["土建", "安装", "装饰"]}
{"name": "验收日期", "type": "date"}
{"name": "所属季度", "type": "date", "dateType": "quarter"}
{"name": "金额", "type": "money", "unit": "万元"}
{"name": "自动编号", "type": "auto-number", "prefix": "GCYS"}
{"name": "条码", "type": "barcode"}
{"name": "定位", "type": "location"}
{"name": "所在地区", "type": "area-linkage"}
{"name": "省份", "type": "area-linkage", "areaLevel": 1}
{"name": "签字", "type": "hand-sign", "required": true}
{"name": "---", "type": "divider", "text": "分隔标题"}
{"name": "性别", "type": "radio", "dictCode": "sex",
 "options": [{"value": "1", "label": "男"}, {"value": "2", "label": "女"}]}
```

## 主表支持的 type

**所有主表控件（除 divider/text/buttons/tabs 布局控件外）均支持以下两个通用参数：**

**`remoteAPI`** — 远程取值接口地址（URL 支持 `{{上下文变量}}` 和 `${字段model}` 动态传参）：
```json
{"name": "真实姓名", "type": "input", "remoteAPI": "/desform/api/getName?userId={{sysUserCode}}"}
```
> 详见 `desform-remote-api.md`

**`defaultExpr`** — 默认值表达式，支持上下文变量 `{{varName}}` 和字段引用 `$fieldModel$`，仅新增时生效：
```json
{"name": "操作人", "type": "input", "defaultExpr": "{{sysUserName}}"}
{"name": "记录时间", "type": "input", "defaultExpr": "{{sysDate}} {{sysTime}}"}
```
> 详见 `desform-context-vars.md` — 完整变量列表、混合语法、注意事项。

> **各 type 的完整参数（含 `disabled`/`hidden`/`placeholder` 等所有字段）见权威文档 `desform-widget-options.md`**，按 SKILL.md 中的 `WIDGET_OPTIONS_INDEX` 索引定位对应控件片段直接阅读，不要凭记忆填写参数。

| type | 说明 |
|------|------|
| `input` | 单行文本 |
| `textarea` | 多行文本 |
| `number` | 数字 |
| `integer` | 整数 |
| `money` | 金额 |
| `date` | 日期（`dateType`：`year`/`month`/`quarter`/`week`/`date`/`datetime`/`datetime_sf`/`datetime_s`。敲敲云不用 daterange） |
| `time` | 时间 |
| `switch` | 开关 |
| `slider` | 滑块 |
| `rate` | 评分 |
| `color` | 颜色 |
| `radio` | 单选（`options` 必填） |
| `select` | 下拉（`options` 必填） |
| `checkbox` | 多选（`options` 必填） |
| `select-user` | 选人 |
| `select-depart` | 选部门 |
| `select-depart-post` | 选岗位 |
| `org-role` | 组织角色 |
| `phone` | 手机 |
| `email` | 邮箱 |
| `area-linkage` | 省市级联（`areaLevel`：`1`=省 / `2`=省市 / `3`=省市区，默认 `3`） |
| `category-linkage` | ⛔ 敲敲云 skill 屏蔽，禁止新建 |
| `table-dict` | ⛔ 敲敲云禁用 |
| `select-tree` | ⛔ 敲敲云禁用 |
| `file-upload` | 文件上传 |
| `imgupload` | 图片上传 |
| `hand-sign` | 手写签名 |
| `auto-number` | 自动编号 |
| `barcode` | 条码/二维码 |
| `capital-money` | 大写金额（关联 money/formula/summary 字段） |
| `text-compose` | 文本组合（$model$ 引用字段） |
| `location` | 定位 |
| `map` | 地图（百度地图） |
| `ocr` | 文本识别 |
| `formula` | 公式 |
| `divider` | 分隔符（`name` 会被忽略，用 `text`） |
| `editor` | 富文本 |
| `markdown` | Markdown |
| `text` | 静态文本（不存储数据） |
| `buttons` | 按钮（不存储数据） |
| `tabs` | 标签页容器（见下方 tabs 说明） |
| `link-record` | 关联记录。建表时若用户说了记录范围/筛选条件或查询设置，把 `filters` / `search` / `dataSelectAuth` 写在该字段上（场景表见 `desform-link-record.md`「调用场景」），不要事后当列表筛选去配 |
| `link-field` | 他表字段 |
| `summary` | 汇总（数值类聚合：sum/avg/max/min/count 等） |
| `summary-date` | 汇总日期（语法糖，内部映射到 `SUMMARY_DATE()`，最终生成 `type:"date"`+`isSummary:true` 的控件，并非独立控件类型。参数: linkTable/field/summaryType/dateType/format/filter） |
| `sub-table-design` | 设计子表（`fields` 必填，见下方子表说明） |

---

## 重要注意事项（AI 生成必读）

### 1. capital-money 关联金额控件

`capital-money`（大写金额）可关联 `money`、`formula`、`summary` 三种类型的控件。关联优先级：

1. **`moneyField`（推荐）**：传入目标字段的中文名，脚本自动解析为对应控件的 key。适用于大写金额与目标字段不相邻的场景。
2. **`moneyWidgetKey`**：直接传入控件 key（适用于已知 key 的场景）。
3. **自动查找（兜底）**：如果两者都未指定，脚本向前查找最近的 `money`/`formula`/`summary` 控件。

```json
{"name": "预算总额", "type": "money", "required": true, "unit": "万元"},
{"name": "总金额", "type": "formula", "mode": "CUSTOM",
 "expression": "$预算总额$*1.13", "decimal": 2, "unit": "元"},
{"name": "其他字段", "type": "input"},
{"name": "大写金额", "type": "capital-money", "moneyField": "总金额"}
```

### 2. formula 表达式使用字段中文名引用（自动解析）

公式控件的 `expression`、`dateBegin`、`dateEnd` 等表达式中的 `$model$` 引用必须是实际控件的 model。但 JSON 配置中无法预知 model（因为包含时间戳），因此 **`desform_creator.py` 支持使用字段中文名作为占位符，自动解析为实际 model**。

```json
{"name": "预算总额", "type": "money"},
{"name": "已拨付金额", "type": "money"},
{"name": "剩余预算", "type": "formula", "mode": "CUSTOM",
 "expression": "$预算总额$-$已拨付金额$", "decimal": 2}
```

脚本会将 `$预算总额$` 自动替换为 `$money_1774607470511_377187$` 等实际 model。

**日期公式同理：**
```json
{"name": "计划开始日期", "type": "date"},
{"name": "计划结束日期", "type": "date"},
{"name": "项目工期", "type": "formula", "mode": "DATEIF",
 "dateBegin": "$计划开始日期$", "dateEnd": "$计划结束日期$",
 "dateFormatMethod": 2, "datePrintUnit": "d"}
```

> **注意：** 引用的字段必须在 fields 数组中定义且在 formula 之前出现。如果字段名未找到匹配，占位符将保持原样不替换。

### 3. Word 布局下分隔符自动适配

在 Word 风格布局（`layout: "word"`）下，`divider` 分隔符会自动包裹在一个 `span=24`、`isWordStyle=true` 的 grid 容器中，以确保与 Word 风格的表格边框视觉一致。无需手动配置，JSON 中按普通分隔符写法即可：

```json
{"name": "---", "type": "divider", "text": "分区标题"}
```

---

## tabs（标签页容器）

```json
{
  "type": "tabs",
  "name": "Tabs",
  "tabLabels": ["基本信息", "详细信息", "附件"],
  "tabType": "border-card",
  "position": "top"
}
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `tabLabels` | 标签页名称数组 | `["Tab1", "Tab2"]` |
| `tabType` | 标签样式：`border-card` / `card` / `''` | `border-card` |
| `position` | 标签位置：`top` / `bottom` / `left` / `right` | `top` |

> 注意：tabs 内的子控件需要在创建后通过 Python 脚本手动添加到 `panes[i]['list']` 中，JSON 配置暂不支持嵌套子控件定义。

---

## 子表 `sub-table-design` 说明

子表通过嵌套 `fields` 数组定义子控件，无需手动处理 `parent_key`，脚本自动完成。

### 子表配置选项

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `columnNumber` | 1/2/3/4 | 2 | 布局列数（单列/双列/三列/四列） |
| `operationMode` | 1/2 | 1 | 操作方式：1=行内编辑，2=弹出编辑 |
| `isWordStyle` | bool | false | Word 文档风格（黑色边框表格样式，仅预览和使用时生效） |
| `isWordInnerGrid` | bool | false | 内嵌栅格模式（配合 isWordStyle 解决内部边框显示问题） |
| `defaultRows` | int | 0 | 默认预填行数（0=不预填） |

### columnNumber 与 columns 数组的对应关系（重要）

`columnNumber` 控制子表设计区域的布局列数，JSON 中的 `columns` 数组长度**必须**与 `columnNumber` 一致，
每列的 `span = 24 / columnNumber`。如果不匹配（如 `columnNumber=2` 但 `columns` 只有 1 个元素），
设计器会显示异常（空白列或控件挤压）。

| columnNumber | columns 数组 | 每列 span |
|---|---|---|
| 1 | `[{span:24, list:[...]}]` | 24 |
| 2 | `[{span:12, list:[...]}, {span:12, list:[...]}]` | 12 |
| 3 | `[{span:8, list:[...]}, {span:8, list:[...]}, {span:8, list:[...]}]` | 8 |
| 4 | `[{span:6, list:[...]}, ...(共4个)]` | 6 |

`make_sub_table()` 和 `desform_creator.py` 已自动处理：根据 `columnNumber` 生成对应数量的列，并将子控件**顺序填充**到各列（先填满第1列，再填第2列……），确保表格视图的列顺序与字段定义顺序一致。当字段较多时，可将 `columnNumber` 设为 3 或 4 以获得更紧凑的设计视图布局。

### 子表内支持的 type

> **注意：** 子表内只支持以下 type，不要凭空捏造不存在的类型。数字用 `number`，整数用 `integer`，多行文本用 `textarea`。标 ⛔ 的类型（含联动 `category-linkage`）**不允许使用**。

> **各 type 的完整参数见 `desform-widget-options.md`**（同主表，按 WIDGET_OPTIONS_INDEX 定位）。子表内控件用 `col_width` 控制列宽，不用 `autoWidth`。

| type | 说明 |
|------|------|
| `input` | 单行文本 |
| `textarea` | 多行文本 |
| `integer` | 整数 |
| `number` | 数字 |
| `money` | 金额 |
| `date` | 日期 |
| `time` | 时间 |
| `select` | 下拉选择（`options` 必填） |
| `radio` | 单选（`options` 必填） |
| `checkbox` | 多选（`options` 必填） |
| `capital-money` | 大写金额（LHZP-1984 子表可用） |
| `text-compose` | 文本组合（LHZP-1984 子表可用） |
| `select-user` | 选人 |
| `select-depart` | 选部门 |
| `select-depart-post` | 选岗位 |
| `phone` | 手机 |
| `email` | 邮箱 |
| `area-linkage` | 省市级联（`areaLevel`：`1`=省 / `2`=省市 / `3`=省市区，默认 `3`） |
| `category-linkage` | 联动。⛔ **不允许使用**（skill 禁止生成） |
| `table-dict` | ⛔ 不允许使用 |
| `select-tree` | ⛔ 不允许使用 |
| `org-role` | 组织角色 |
| `switch` | 开关（默认 Y/N） |
| `slider` | 滑块 |
| `rate` | 评分 |
| `color` | 颜色 |
| `imgupload` | 图片上传（子表内缩略图自动缩小为 50x50） |
| `file-upload` | 文件上传 |
| `link-record` | 关联记录（子表内强制为下拉模式） |
| `link-field` | 他表字段（子表内强制为保存模式） |
| `formula` | 公式 |
| `product` | 乘积公式（`field_models` 必填） |

### 全新创建的设计子表不支持的 type

全新创建 `sub-table-design` 时，**不要**往子表 `fields` 里放下面这些 type（主表可以用）。脚本遇到会报 `子表内不支持的控件类型`。

| 类别 | 不支持的 type |
|------|----------------|
| 布局 | `card`、`grid`、`tabs`、`divider`、`text`、`buttons`、嵌套 `sub-table-design` |
| 高级 | `auto-number`、`barcode`、`capital-money`、`text-compose`、`location`、`map`、`ocr`、`editor`、`markdown`、`hand-sign`、`summary`、`summary-date` |

子表内也**不允许任何布局组件**。可用控件以本节「子表内支持的 type」为准。

### 子表内特殊约束（源码强制行为）

- `imgupload` 在子表内缩略图自动缩小为 50x50（主表默认 100x100）
- `link-record` 在子表内强制为下拉模式（`showType = 'select'`），不支持卡片/表格模式
- `link-field` 在子表内强制为保存模式（`saveType = 'save'`），不支持 view 模式
- 所有子表内控件自动设置 `isSubItem: true` 和 `subOptions.parentKey`
- 子表内控件不使用 `autoWidth`，使用 `col_width` 控制列宽（默认 200px）
- ⛔ 子表 **不允许使用** `category-linkage`（联动）、`table-dict`、`select-tree`

---

## 完整示例

### 主表示例（工程竣工验收申请表）

```json
{
  "formName": "工程竣工验收申请表",
  "formCode": "eng_completion_acceptance",
  "layout": "word",
  "fields": [
    {"name": "自动编号", "type": "auto-number", "prefix": "GCYS"},
    {"name": "工程名称", "type": "input", "required": true},
    {"name": "工程类别", "type": "radio", "options": ["土建工程", "安装工程", "装饰工程", "市政工程"]},
    {"name": "负责人", "type": "select-user", "required": true},
    {"name": "所属部门", "type": "select-depart"},
    {"name": "开工时间", "type": "date"},
    {"name": "完工时间", "type": "date"},
    {"name": "工程量清单", "type": "textarea"},
    {"name": "现场图片", "type": "imgupload"},
    {"name": "---", "type": "divider", "text": "验收审查"},
    {"name": "验收结论", "type": "radio", "options": ["合格", "不合格", "整改后复验"]},
    {"name": "负责人签字", "type": "hand-sign"}
  ],
  "menuParent": "工程验收管理"
}
```

### 子表示例（采购订单）

```json
{
  "formName": "采购订单",
  "formCode": "purchase_order",
  "titleIndex": 0,
  "fields": [
    {"name": "订单编号", "type": "auto-number", "prefix": "PO"},
    {"name": "供应商", "type": "input", "required": true},
    {"name": "采购员", "type": "select-user", "required": true},
    {"name": "订单日期", "type": "date", "required": true},
    {"name": "商品明细", "type": "sub-table-design",
     "columnNumber": 2, "operationMode": 1, "fields": [
      {"name": "商品名称", "type": "input", "required": true},
      {"name": "规格", "type": "input"},
      {"name": "类别", "type": "radio", "options": ["原材料", "半成品", "成品"]},
      {"name": "数量", "type": "integer", "col_width": "100px"},
      {"name": "单价", "type": "money", "col_width": "120px"},
      {"name": "金额", "type": "money", "col_width": "120px"},
      {"name": "是否含税", "type": "switch"},
      {"name": "交货日期", "type": "date"},
      {"name": "备注", "type": "textarea", "col_width": "250px"}
    ]},
    {"name": "备注", "type": "textarea"}
  ]
}
```

### 弹出编辑 + Word 风格子表示例

```json
{"name": "检验明细", "type": "sub-table-design",
 "operationMode": 2, "isWordStyle": true, "fields": [
  {"name": "检验项目", "type": "input", "required": true},
  {"name": "检验人", "type": "select-user"},
  {"name": "检验结果", "type": "radio", "options": ["合格", "不合格", "待检"]},
  {"name": "检验日期", "type": "date"},
  {"name": "照片", "type": "imgupload"},
  {"name": "附件", "type": "file-upload"}
]}
```

---

## JS/CSS 增强配置（expand）

通过 `expand` 字段可在 JSON 配置中直接设置 JS/CSS 增强，无需编写自定义 Python 脚本。

```json
{
  "formName": "请假申请",
  "formCode": "oa_leave",
  "fields": [...],
  "expand": {
    "js": "if (data.isAddAction) { api.hide('approve_status') }",
    "css": ".el-form-item__label { font-weight: bold; color: #333; }",
    "url": {
      "js": "",
      "css": "/desform/expand/css/custom-theme.css"
    }
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `expand.js` | string | 内联 JS 增强代码（可用 api/data/moment 等上下文） |
| `expand.css` | string | 内联 CSS 增强代码 |
| `expand.url.js` | string | 外部 JS 文件 URL |
| `expand.url.css` | string | 外部 CSS 文件 URL |

- `expand` 中的四个字段均为可选，只需填写需要的部分
- JS/CSS 增强的详细用法见 `desform-js-enhance.md` 和 `desform-css-enhance.md`

---

## 调用示例

> ⛔ **方式选择（必须遵守）：字段数 ≤50 → stdin 管道；字段数 >50 → 临时文件。禁止在字段数 ≤50 时使用临时文件。**

```bash
# ✅ 默认方式（字段数 ≤50）：stdin 管道，无需临时文件
echo '<json_config>' | python "<skill目录>/scripts/desform_creator.py" \
    --api-base <api_base> \
    --token <token> \
    --config -

# 如需覆盖已存在的表单（加 --force）
echo '<json_config>' | python "<skill目录>/scripts/desform_creator.py" \
    --api-base <api_base> \
    --token <token> \
    --config - --force
```

```bash
# ⚠️ 仅当字段数 >50 时才使用临时文件方式
# 1. Write 工具生成 JSON 配置文件
# 2. 执行脚本
python "<skill目录>/scripts/desform_creator.py" \
    --api-base <api_base> \
    --token <token> \
    --config eng_acceptance.json

# 如需覆盖已存在的表单
python "<skill目录>/scripts/desform_creator.py" \
    --api-base <api_base> \
    --token <token> \
    --config eng_acceptance.json \
    --force

# 3. 删除临时 JSON 文件
```
