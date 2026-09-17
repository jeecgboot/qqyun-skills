# 关联记录（link-record）与他表字段（link-field）完整参考

## 一、link-record 完整 options

```json
{
  "sourceCode": "",              // 源表单 desformCode（必填）
  "showMode": "single",          // "single" 单条 / "many" 多条
  "showType": "card",            // "card" 卡片 / "select" 下拉 / "table" 表格
  "titleField": "",              // 源表标题字段 model（必填）
  "showFields": [],              // 额外展示的字段 model 列表
  "allowView": true,             // 允许查看
  "allowEdit": true,             // 允许编辑
  "allowAdd": true,              // 允许新增并关联
  "allowSelect": true,           // 允许从已有记录选择（关它才去掉「+ 关联已有数据」）
  "hiddenOnAdd": false,          // 「新增时隐藏」：新建记录时整块不渲染，看已有记录时照常显示
  "buttonText": "添加记录",
  "twoWayModel": "",             // 双向关联：源表中反向 link-record 的 model
  "dataSelectAuth": "all",       // "all" 全部 / "read" 仅有读权限的
  "filters": [{ "matchType": "AND", "rules": [] }],  // 筛选条件，始终只用 [0]
  "search": { "enabled": false, "field": "", "rule": "like", "afterShow": false, "fields": [] },
  "createMode": {},              // 新增模式
  "width": "100%",
  "defaultValue": "",
  "defaultValType": "none",       // none 无 / first 第一条数据。查询工作表走 advancedSetting.defaultValue.type=linkage，此时此项用 none
  "required": false,
  "disabled": false,
  "hidden": false
}
```

**className**: `form-link-record`，**icon**: `icon-link`

## 二、showType 三种模式

> **组合约束（2026-09-09 UI 核对）：卡片、下拉单选/多选均可；表格仅多选。** 反组合（单选+表格）面板不提供，勿配。

| 特性 | card（卡片） | select（下拉） | table（表格） |
|------|-------------|--------------|-----------|
| 显示样式 | 卡片网格 | 下拉框 | 表格行列 |
| 适用 showMode | single / many | single / many | **仅 many** |
| 内置搜索 | 否 | 是 | 否 |
| 子表内可用 | 是 | 是 | 否 |
| 需要 card 包裹 | single 时是 | 否 | 否（独占整行） |
| 适用场景 | 字段多详细展示 | 数据量大空间有限 | 一对多行数据 |

## 二-a、外部子表模式（「子表作为单独工作表」/「已有工作表作为子表」）（2026-09-04 实测，样例：工作表 主.子）

用户说「子表作为单独工作表」「一对多子表、子表单独建」「已有工作表作为子表」时，主表明细区**不是普通 many 关联**，而是 link-record + `isSubTable`（表格式明细区）。主表侧控件落库形态：

```json
{
  "type": "link-record", "name": "子", "className": "form-link-record", "icon": "icon-link",
  "isSubTable": true,                                  // ⚠️ 顶层标记，必写
  "key": "1788486935939_597293",
  "model": "sub_table_design_1788486935939_597293",    // ⚠️ model 前缀 sub_table_design_，后缀 = key
  "options": {
    "sourceCode": "<子表code>", "showMode": "many", "showType": "table",
    "titleField": "<子表标题字段model>", "showFields": ["<子表展示列models>"],
    "twoWayModel": "<子表回指字段model>", "dataSelectAuth": "all", "...": ""
  }
}
```

子表（独立工作表）侧回指主表字段：普通 link-record，`showMode:"single"` + `showType:"card"`，`options.twoWayModel` 指向主表侧明细控件 model（互指）。

**从创建脚本产出的普通 many 关联转换：**
1. 主表侧明细控件：`model` 改 `sub_table_design_<原key>`、顶层加 `isSubTable:true`、`options.showType="table"`
2. 子表回指字段对齐 `single`+`card`，`options.twoWayModel` = 主表侧新 model
3. 主表对该明细列求和的汇总字段 `options.linkTable` 同步为新 model；**用户在界面手工重绑汇总后 linkTable 落库为明细控件 key（无前缀）**——两种写法都存在，以界面最后一次保存为准
4. model 改名后 `save_auth_from_design(主表code)` 重刷字段权限（auth 按 model 存）

## 二-b、filters vs search：建表时调用场景（先看这张表）

`options.filters`（设置筛选条件）和 `options.search`（查询设置）都是 **link-record 控件上的设计器配置**，在**建工作表 / 加关联记录字段时一并写入**。不是列表页功能，不是用户选记录时才去调的 API。用户没提就保持默认，不要主动加。

| 用户在建表（或改这个关联记录字段）时说 | 写入 | 禁止当成 |
|----------------------------------------|------|----------|
| 「只能选状态=启用的」「记录范围」「设置筛选条件」「仅能选有查看权限的」 | `dataSelectAuth` + `filters`（本节三） | `search`；列表数据过滤；高级查询 superQuery |
| 「选记录时按名称搜」「查询设置」「查询之后再显示」「让用户自己按状态筛」 | `search`（本节四） | `filters.rules`（那是写死的范围，不是给用户填的筛选项） |
| 上面两类都说了 | **同一个** link-record 上两份都写 | 拆成两次接口、拆成两个控件 |
| 「列表筛选」「视图数据过滤」「高级查询」 | **不是这两项** | 走 `desform-list-view.md` / `desform-super-query.md` |
| 工作表子表里的关联记录（`isSubTable`） | 可以写 `filters`；**没有**查询设置面板 | 不要写 `search` |

**何时写：** 创建 JSON 的 `link-record` 字段带上，或 `LINK_RECORD(..., filters=..., search=...)`。已有表才用 `update_widget`。源表字段 `model` 必须来自源表，禁止猜。

> ⚠ 2026-09-03 实测修复：`LINK_RECORD` 的 `filters=`/`search=`/`data_select_auth=` 此前经 `**kw` 传给 make_widget，被白名单当未知参数**静默丢弃**（只打警告），导致关联记录带筛选必须二次 `update_widget` 补。现已改为显式命名参数直接写进 options，示例可用。给已有表新增关联记录字段建议直接走 `scripts/add_link_record.py`（见 `fast-add-link-record.md`）。

## 三、filters 筛选条件（关联记录「设置筛选条件」）

> **调用场景见上一节。** 建表时写进该关联记录的 `options.filters`。对齐 `FilterConfig.vue` + `QueryRuleMap`（`isSuperQuery=true`）。**不是**列表数据过滤 / 高级查询（那些用小写 `eq`/`like`）。

选择记录时两层限制：

| 配置 | 值 | 含义 |
|------|----|------|
| `dataSelectAuth` | `all`（默认） | 可选择所有记录，请求不带 appId |
| `dataSelectAuth` | `read` | 仅可选择有查看权限的记录，请求带源表 `lowAppId` |
| `filters[0].rules` | 空 | 未开启筛选（UI 显示「设置筛选条件」勾选框） |
| `filters[0].rules` | 非空 | 需同时满足这些条件（或按 `matchType` 取或） |

**默认 / 清空**都是 `[{matchType:"AND",rules:[]}]`。运行时**只读 `filters[0]`**，不要写多组。

### 3.1 设计 JSON 结构

```json
{
  "dataSelectAuth": "all",
  "filters": [{
    "matchType": "AND",
    "rules": [
      {
        "model": "radio_源表状态model",
        "rule": "EQ",
        "valueType": "fixed",
        "value": ["1"],
        "valueText": "启用",
        "sqParam": { "type": "radio", "rule": "eq" }
      },
      {
        "model": "select_user_负责人model",
        "rule": "EQ",
        "valueType": "field",
        "value": ["select_user_本表填报人model"],
        "sqParam": { "type": "select-user", "rule": "eq" }
      }
    ]
  }]
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `matchType` | ✅ | **大写** `AND`（且）/ `OR`（或）。请求时才会 `toLowerCase()` |
| `rules[].model` | ✅ | **源表**字段 model，或系统字段 `create_by` / `create_time` / `update_by` / `update_time` |
| `rules[].rule` | ✅ | **QueryRuleMap 大写 key**（`EQ`/`IN`/`DATE_LT`…），禁止小写 `eq`/`like`，禁止 `range`/`isNull`/`notIn` |
| `rules[].valueType` | ✅ | `fixed`=固定值；`field`=引用**本表**非容器字段 model。**不是** `"value"` |
| `rules[].value` | ✅ | **始终数组**。`fixed` 存比较值；`field` 存 `[本表字段model]`（运行时只用 `[0]`） |
| `rules[].valueText` | — | 展示翻译（选人/字典/关联记录等会写入） |
| `rules[].sqParam.type` | ✅ | 运行时 superQuery 的 `type`，见 3.4 |
| `rules[].sqParam.rule` | ✅ | 运行时 superQuery 的小写 `rule`，见 3.2。无映射的规则不要写进 filters |

无值规则 `EMPTY` / `NOT_EMPTY`：`value` 传 `[]`，仍保留该条。其余规则若 `value` 为空，前端确定时会丢掉。

`field` 取值：本表非容器控件。条件字段本身是 `link-record` 时，只能引用 **sourceCode 相同**的其他关联记录。运行时用当前表单 `models[value[0]]` 替换；该 model 空则整条规则跳过。

选人/部门/岗位的固定值控件会开「当前登录人」快捷项（`allowCurrLogin`），仍是 `valueType:"fixed"`，不要写 `valueType:"system"`（关联记录弹窗不提供该选项）。

**固定值编辑器按源字段类型出控件（2026-09-09 源码核对）：** 单选/多选/下拉固定值=下拉多选（多值连选）；日期/时间/开关/省市区/组织角色/嵌套关联记录=各自选择器（日期区间类折叠为单值）；**人员/部门/岗位条件的固定值编辑器支持直接选「当前登录人/部门/岗位」**（allowCurrLogin，如 select-user 固定值=当前登录人），落库值以 UI 保存后 JSON 为准。筛选条件**值类型只有 固定值/本表字段值**（无独立"系统变量"类型，当前登录人走固定值编辑器内快捷项）。

### 3.2 rule → 运行时 superQuery（必须写 sqParam）

| 设计器 rule（存 JSON） | 中文 | `sqParam.rule` | 何时可用 |
|------------------------|------|----------------|----------|
| `EQ` / `NE` | 等于 / 不等于 | `eq` / `ne` | 除上传、签名、`isSubTable` 关联记录外 |
| `GT` `GE` `LT` `LE` | 大于 / ≥ / 小于 / ≤ | `gt` `ge` `lt` `le` | 数值类：`number`/`integer`/`money`/`slider`/`rate`/`summary`/`formula`(数字) |
| `IN` / `NOT_IN` | 包含 / 不包含 | `like` / `not_like` | **文本类**（不是「是其中一个」） |
| `BEFORE` / `AFTER` | 开头是 / 结尾是 | `right_like` / `left_like` | 文本类 |
| `IS_ONE_OF` / `NOT_IS_ONE_OF` | 是其中一个 / 不是其中一个 | `in` / `not_in` | `radio`；人员/部门/岗位/组织角色 **单选**；关联记录 `showMode=single`；已有 `select-tree`/`table-dict` 单选 |
| `IN_ONE_OF` / `NOT_IN_ONE_OF` | 包含其中一个 / 不包含任何一个 | `in` / `not_in` | `checkbox`/`select`；人员等 **多选**；关联记录 `showMode=many`；已有树/表字典多选 |
| `DATE_LT` `DATE_LE` `DATE_GT` `DATE_GE` | 早于 / 早于等于 / 晚于 / 晚于等于 | `lt` `le` `gt` `ge` | `date` 且 `options.type` ∈ `date`/`datetime`/`year`/`month`/`quarter`/`week`；或 `formula` 且 `options.type=date` |
| `EMPTY` / `NOT_EMPTY` | 为空 / 不为空 | `empty` / `not_empty` | 除 `switch` 外 |

**禁止写入**（`isSuperQuery` 下无 `superQueryType`，弹窗不出现）：`IN_ALL_OF`（同时包含）、`NOT_BEFORE`（开头不是）、`NOT_AFTER`（结尾不是）、`VALUE_CHANGE`（值发生变化）。

**按字段类型的可用 rule（默认都是 `EQ`，上传类默认 `EMPTY`）：**

| 源表字段类型 | 可用 rule |
|--------------|-----------|
| 文本类：`input`/`textarea`/`phone`/`email`/`auto-number`/`time` 及未点名控件 | `EQ` `NE` `IN` `NOT_IN` `BEFORE` `AFTER` `EMPTY` `NOT_EMPTY` |
| 数值类 | `EQ` `NE` `GT` `GE` `LT` `LE` `EMPTY` `NOT_EMPTY` |
| 日期 `type∈date/datetime/year/month/quarter/week` | `EQ` `NE` `DATE_LT` `DATE_LE` `DATE_GT` `DATE_GE` `EMPTY` `NOT_EMPTY` |
| 日期 `datetime_s` / `datetime_sf` | 仅 `EQ` `NE` `EMPTY` `NOT_EMPTY`（无早于/晚于） |
| `radio` | `EQ` `NE` `IS_ONE_OF` `NOT_IS_ONE_OF` `EMPTY` `NOT_EMPTY` |
| `checkbox` / `select` | `EQ` `NE` `IN_ONE_OF` `NOT_IN_ONE_OF` `EMPTY` `NOT_EMPTY` |
| `select-user` / `select-depart` / `select-depart-post` / `org-role` | `EQ` `NE` + 单选 `IS_ONE_OF*` / 多选 `IN_ONE_OF*` + `EMPTY` `NOT_EMPTY` |
| `area-linkage` | `EQ` `NE` `EMPTY` `NOT_EMPTY` |
| `switch` | `EQ` `NE`（**无**为空/不为空） |
| `link-record`（非 `isSubTable`） | `EQ` `NE` + single→`IS_ONE_OF*` / many→`IN_ONE_OF*` + `EMPTY` `NOT_EMPTY` |
| `link-record` 且 `isSubTable`，或 `sub-table-design` | 仅 `EMPTY` `NOT_EMPTY` |
| `imgupload` / `file-upload` / `hand-sign` | 仅 `EMPTY` `NOT_EMPTY` |
| `link-field` | 仅 `saveType=save` 才出现在字段列表，按 `fieldType` 走对应行 |
| 系统字段 `create_by`/`update_by` | 同人员单选 |
| 系统字段 `create_time`/`update_time` | 同日期 `datetime` |

弹窗字段列表还会拼上系统四字段。**不出现**：`barcode`、`capital-money`、`saveType=view` 的他表字段。

`value` 多值：`IN`/`NOT_IN`/`IS_ONE_OF`/`NOT_IS_ONE_OF`/`IN_ONE_OF`/`NOT_IN_ONE_OF`、以及 `checkbox`、`select.multiple`。运行时 `fixed` 用 `value.join(',')`。

日期固定值可为时间戳或相对区间 key（展示用）：`TODAY` `YESTERDAY` `TOMORROW` `THIS_WEEK` `LAST_WEEK` `NEXT_WEEK` `LAST_7_DAYS` `THIS_MONTH` `LAST_MONTH` `NEXT_MONTH`。不要自造别的 key。

**月/季/周粒度固定值 = 周期起始时间戳**：`options.type` ∈ `month`/`quarter`/`week` 的 `EQ`/`NE` 固定值须写周期起始毫秒时间戳（UI 落库口径），写格式化字符串（`"2026-Q3"`）面板不显示条件值（2026-09-09 实测）。通用值规则见 `desform-widget-options.md`「date」。

### 3.3 与列表过滤的对照（禁止混用）

| | 关联记录 `options.filters` | 列表数据过滤 / 高级查询 |
|--|---------------------------|------------------------|
| `rule` | 大写 `EQ` `IN` `DATE_LT` | 小写 `eq` `like` `lt` |
| 文本「包含」 | `IN` → sqParam `like` | 直接 `like` |
| 「是其中一个」 | `IS_ONE_OF` / `IN_ONE_OF` → `in` | 直接 `in` |
| 日期比较 | `DATE_LT` 不是 `LT`，也没有 `range` | `lt` / `range` |
| 空值 | `EMPTY` / `NOT_EMPTY` | `empty` / `not_empty` |
| 值字段 | `value` 数组 + `valueType` | `val` |
| 匹配 | `matchType` 大写 `AND`/`OR` | 小写 `and`/`or` |

### 3.4 `sqParam.type`（getSuperQueryType）

按条件字段（源表 widget）计算，缺字段时为 `"text"`：

| 源控件 | `sqParam.type` |
|--------|----------------|
| 普通控件 | `widget.type` |
| `date` | `options.type`（`date`/`datetime`/`year`/`month`/`quarter`/`week`/`datetime_s`/`datetime_sf`） |
| `formula` 数字 | `number` |
| `formula` 日期且 `mode=DATEADD` | `date` |
| `formula` 日期其他 mode | `input` |
| `link-field` | `options.fieldType` |
| 系统创建/修改时间 | `datetime` |
| 系统创建/修改人 | `select-user` |

缺 `sqParam` 时运行时会 `item.rule.toLowerCase()`：`EQ`→`eq` 碰巧对，但 `IN`→`in`（应为 `like`）、`DATE_LT`→`date_lt`（应为 `lt`）、`BEFORE`→`before`（应为 `right_like`），条件会错。

### 3.5 写入方式（建表时写进控件）

```python
# 建表 / 新加关联记录：跟 LINK_RECORD 一次提交
ws, k, m = LINK_RECORD('客户', source_code, title_model,
    dataSelectAuth='read',
    filters=[{
        "matchType": "AND",
        "rules": [{
            "model": status_model,
            "rule": "EQ",
            "valueType": "fixed",
            "value": ["1"],
            "sqParam": {"type": "radio", "rule": "eq"},
        }],
    }])
```

已有控件才 `update_widget(code, {"options": {"dataSelectAuth": "read", "filters": [...]}}, key=k)`。`model` 必须是源表真实 model，禁止猜。

## 四、search 查询设置（关联记录「查询设置」）

> **调用场景见「二-b」。** 建表时写进该关联记录的 `options.search`。对齐 `SearchConfig.vue`。属性面板在 `!isSubTable` 才有；**工作表子表没有查询设置**。
>
> `search.fields` 只决定选记录时用户**能用哪些字段自己筛**，不存条件值。写死的可选范围走 `filters`，不要写进 `search`。

默认 / 取消查询设置，都重置为：

```json
{
  "enabled": false,
  "field": "",
  "rule": "like",
  "afterShow": false,
  "fields": []
}
```

勾选并确定后 `enabled` 必为 `true`。

### 4.1 字段说明

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `enabled` | boolean | `false` | 是否启用查询设置 |
| `field` | string | `""` | **关键词搜索**打在源表哪个字段的 model |
| `rule` | string | `"like"` | 关键词搜索方式：`eq`=精确，`like`=模糊。这里是 **superQuery 小写**，不要写成 `EQ`/`IN` |
| `afterShow` | boolean | `false` | 「在查询之后再显示记录」：打开选择弹窗先不拉数据，用户输入关键字或点筛选后才查 |
| `fields` | string[] | `[]` | 用户侧「筛选」可用的源表字段 model 列表，**顺序即展示顺序** |

```json
{
  "search": {
    "enabled": true,
    "field": "input_客户名称model",
    "rule": "like",
    "afterShow": true,
    "fields": ["radio_状态model", "select_user_负责人model", "create_time"]
  }
}
```

### 4.2 关键词搜索字段 `field`（白名单）

设计器下拉只允许这些源表控件（`simpleAllowWidgets`）：

`input` / `textarea` / `phone` / `email` / `text-compose` / `auto-number`

- 必须是源表真实 model。空字符串时弹窗打开会落到上述列表的第一项。
- 源表一个都没有：不要开查询设置（前端会取 `[0].model` 崩）。
- **不能**用数字、日期、单选、人员、系统字段做 `field`。
- 未启用时（`enabled=false`）：关键字仍可搜，但打在 **`titleField`** 上，规则固定 `like`，`type` 固定 `"text"`。
- 启用后：`field` + `rule`，`type` 仍固定 `"text"`。关键字为空则不加这组条件。

### 4.3 用户筛选字段 `fields`

文案：「用户可通过以下字段筛选数据」。可拖拽排序。

**可加入：** 源表业务字段 + 系统字段 `create_by` / `create_time` / `update_by` / `update_time`。

**不可加入：** `capital-money`；`link-field` 且 `saveType !== "save"`。

`fields` 为空（或未启用）：选择弹窗不出现筛选按钮。非空且 `enabled=true` 才显示。

设计 JSON **只存 model 数组**，不要写 `queryItems`。用户在弹窗里填的值是运行时的，查询时临时拼进 `search.queryItems`。

选择弹窗里各类型的比较方式（`SelectLinkFilterBox`，不用手写）：

| 源字段类型 | 运行时 rule |
|------------|-------------|
| `input` / `textarea` / `text-compose` / `auto-number` | `like` |
| `number` / `integer` / `money` / `slider` / `summary`；数字公式 | `range`（`"min,max"`） |
| `radio` / `select` / `checkbox`；人员/部门/岗位/组织角色 | `in`（多选） |
| `date` 且 type=`date`/`datetime`/`month` | `range` |
| 日期公式 `DATEADD` | 日期 `eq`；时长类 `DATEIF*` → `range` |
| `color` / `hand-sign` / `editor` / `markdown` / `imgupload` / `file-upload` / `barcode` / `ocr` | 用户选 `empty` / `not_empty` |
| `phone` / `email` / `switch` / `time` / 年季周等其余 | 默认 `eq`（未做特殊转换） |

下拉模式（`showType=select`）只有关键字框，**没有**用户筛选按钮；`fields` / `afterShow` 对下拉不生效。`afterShow` 只作用于卡片/表格选择弹窗。

### 4.4 与 `filters` 如何一起查

`queryCardDataList` 三组条件 **AND**：

1. 关键字（有输入才带）：`{field, type:"text", rule: eq\|like, val}`
2. 设计器 `options.filters[0]`（记录范围，大写 `EQ`…，见上一节）
3. 用户筛选 `search.queryItems`（仅 `enabled` 且用户点了筛选）

不要把用户筛选项写进 `filters.rules`，也不要把固定范围写进 `search.fields`。

### 4.5 写入方式（建表时写进控件）

```python
# 建表 / 新加关联记录：跟 LINK_RECORD 一次提交
ws, k, m = LINK_RECORD('客户', source_code, title_model,
    search={
        "enabled": True,
        "field": name_model,   # 仅文本六类
        "rule": "like",
        "afterShow": False,
        "fields": [status_model, owner_model],
    })
```

已有控件才 `update_widget`。关闭则写回默认对象（`enabled: false`，`fields: []`）。

## 五、createMode 新增模式

```json
{
  "createMode": {
    "add": true,
    "select": false,
    "params": { "selectLinkModel": "" }
  }
}
```

- `add: true` — 打开源表新增弹窗
- `select: true` — 从其他 link-record 批量选择

## 六、twoWayModel 双向关联

表单 A 的 link-record 设 `sourceCode=B_code`，B 的 link-record 设 `sourceCode=A_code`，双方 `twoWayModel` 互指对方的 model。选择关联时自动在两边建立关系。

⚠️ **改成单向关联时（2026-09-17 实测）**：删掉一端（例：合同里的「项目」控件）后，
另一端（项目里的「项目合同」）的 `options.twoWayModel` **会留在原地指向一个已经不存在的 model**，
接口不会报错、表单也能打开——但它是个悬空引用。做法：删除一端的同一次保存里，
把另一端 `twoWayModel` 等于**被删控件 model** 的那些控件一起清掉（`options.pop('twoWayModel')`），
保存后 `queryById` 回读确认该 model 在设计 JSON 里**一次都不出现**了。

## 七、link-field（他表字段）

```json
{
  "linkRecordKey": "",       // link-record 的 KEY（注意是 key 不是 model！）
  "showField": "",           // 源表字段 model
  "saveType": "view",        // "view" 仅展示 / "save" 保存到当前表单
  "fieldType": "",           // 源字段控件类型
  "fieldOptions": {}         // 源字段 options 子集
}
```

**className**: `form-link-field`，**icon**: `icon-field`

### saveType 区别

- `view`：运行时动态查询展示，数据始终最新
- `save`：选择时保存字段值快照，同时保存 `{model}_dictText` 翻译值

> ⚠️ **被公式引用的他表字段必须 `saveType='save'`**（2026-09-17 实测）：`view` 不落库、没有值，
> 公式编辑器（以及汇总/过滤）里这个字段会显示成「**字段已删除**」——用户截图：应收计划.款项比例 = `$款项金额$/$合同金额$`，
> 第二个 chip 就是「字段已删除」（`合同金额` 是 view 型他表字段）。改成 `save` 后引用正常。
> 工厂 `LINK_FIELD(..., save_type='save')` 会被白名单丢弃 → 终产物恒 `view`，必须整单改 `options.saveType='save'`
> 后重存（本项目在 `patch_links.py::_save_types_for_formula_refs` 里按公式引用统一回填）。

### 关键注意

`linkRecordKey` 必须是 link-record 的 `key`（如 `1774581245281_700049`），不是 `model`（如 `link_record_1774581245281_700049`）。这是最常见的配置错误。

**⚠️ 2026-09-09 实测补正（契约键落库位置 + save_type 白名单丢弃）：**

1. **契约键实际落库在控件 `options` 里**（`options.linkRecordKey/showField/saveType/fieldType/fieldOptions`），不在控件顶层——回读核对必须查 `widget['options']`，查顶层会误判「键全丢」。
2. **`LINK_FIELD(..., save_type='save')` 的 save_type 会被 make_widget 白名单丢弃**（警告「收到非白名单参数: ['save_type']，已忽略」），工厂产物 saveType 恒为 `view`。要「存储数据」必须事后改 `options.saveType='save'` + `options.fieldType`/`fieldOptions`，走**整单设计保存**（`query_form` → 改控件 options → `save_design_from_file`），不要用 `update_widget` 试（浅合并删不掉旧键、且契约键在 options 子层）。
3. 工厂产物形态：`LINK_FIELD(...)` 返回 **list `[card]`**（card.list[0] 才是 link-field 控件 dict），`add_widget` 传 `res[0]`。

## 八、子表内使用

- showType 不能为 `table`（避免嵌套表格）
- 需设置 `isSubItem: true`
- 使用 `SUB_LINK_RECORD` 和 `SUB_LINK_FIELD` 快捷函数

## 九、Python 工具函数

```python
# 主表
LINK_RECORD(name, source_code, title_field,
            show_fields=None, show_mode='single', show_type='card',
            is_self=False, wrap=True,
            filters=None, search=None, data_select_auth='all', **kw)
# is_self=True：自关联树模式，自动在顶层写入 isSelf=true 并将 valueSplit 置空
# filters= 写 options.filters（默认空 AND）；search= 写 options.search；
# data_select_auth='all'/'read'（记录范围）。三者 2026-09-03 起为显式参数，
# 不再被 make_widget 白名单丢弃（此前会静默忽略，只打警告）。
LINK_FIELD(name, link_record_key, show_field,
           field_type='input', field_options=None, save_type='view', **kw)

# 子表
SUB_LINK_RECORD(name, parent_key, source_code, title_field,
                show_fields=None, col_width='200px')
SUB_LINK_FIELD(name, parent_key, link_record_key, show_field,
               field_type='input', field_options=None, col_width='150px')
```

## 十、自关联（表单数据树）

当 `sourceCode` 指向表单自身（link-record 关联自己）时，会形成**表单数据树**结构——记录之间通过父子关系形成无限级层级（如组织架构、任务分解、无限级分类）。

> 这是一种特殊配置，需要额外的 `isSelf: true` 顶层属性，且有"先有鸡先有蛋"的创建顺序问题。**遇到此场景必须阅读 `references/desform-self-tree.md`**，其中包含完整配置方法和两阶段创建法。

## 十一、常见踩坑

| 问题 | 原因 | 解决 |
|------|------|------|
| 关联记录不显示 | sourceCode 或 titleField 错误 | 核实源表编码和标题字段 model |
| link-field 始终空白 | linkRecordKey 写的是 model | 改为 link-record 的 key |
| link-field 数据不保存 | saveType 为 view | 改为 save |
| icon 显示异常 | icon 写成 icon-link-record | 改为 icon-link |
| 过滤条件不生效 | `valueType` 写成 `"value"`，或 `rule` 写成小写 `eq`/`like` | `valueType` 用 `fixed`/`field`；`rule` 用大写 `EQ`/`IN`/`DATE_LT`，并写 `sqParam` |
| 过滤条件不生效 | `field` 的 value 不是数组或不是本表 model | `value: ["本表字段model"]`，运行时只用 `[0]` |
| 文本包含查不到 | `filters.rule` 写成了 `like` 或小写 `in` | 文本包含用 `IN`（sqParam `like`）；「是其中一个」才用 `IS_ONE_OF` |
| 查询设置不出现 | 控件是 `isSubTable` | 工作表子表没有查询设置 |
| 关键词搜不到 / 打开弹窗报错 | `search.field` 不是文本六类，或源表没有这类字段 | `field` 只能是 `input`/`textarea`/`phone`/`email`/`text-compose`/`auto-number` |
| 用户筛选按钮没有 | `search.enabled` 为 false，或 `fields` 为空 | 两者都要：`enabled: true` 且 `fields` 非空 |
| 下拉模式筛不了 | `showType=select` 没有用户筛选 UI | 用户筛选只在卡片/表格选择弹窗；下拉只有关键字 |
| `search.rule` 写成 `EQ`/`LIKE` | 查询设置用的是 superQuery 小写 | 只用 `eq` / `like` |
| 把记录范围/查询设置配成列表筛选 | 调错场景 | 这两项是**建表时**写在关联记录控件上的，见「二-b」 |

## 十二、标题字段是「两层」结构（2026-09-04 实测：改一处不联动另一处）

需求写「关联员工表，标题字段为姓名」这类描述时，**「标题字段」同时存在两处**，都要核对：

| 层 | 位置 | 作用 | 怎么改 |
|----|------|------|--------|
| 表级 | 目标表 `desformDesignJson.config.titleField`（存 model） | 该表记录标题；**新加**的关联控件建时默认取它 | 最小 patch：`query_form` 取整行 → 只改 design `config.titleField` → `PUT /desform/edit`（payload 需 id/desformDesignJson/updateCount/autoNumberDesignConfig/refTableDefaultValDbSync 原样回传） |
| 控件级 | 每个已建 link-record 控件的 `options.titleField`（存 model） | 关联弹窗/卡片/下拉**实际显示**哪个字段 | `update_widget(code, {'options': {'titleField': <目标表新标题 model>}}, key=<控件key>)` |

**核心坑：控件级 titleField 在关联创建那一刻固化**（工具取的是当时目标表 config.titleField）。之后把目标表标题从「编号」改成「名称」，所有已建关联**仍显示旧编号**——必须按 sourceCode 分组逐个 update_widget 同步，改表标题不会自动联动。

**修法速查（把「编号标题」改成「名称标题」）：**
1. 先改被引用表的表级标题（`/desform/edit` 最小 patch，见上表）；
2. 列出该应用全部表所有 link-record：查每控件 `options.sourceCode` + `options.titleField`；
3. 对 src=被改表 且 titleField=旧 model 的控件逐个 update_widget 覆盖为**新名称字段 model**（sourceCode 不同但旧 model 相同也要全改，例如多人引员工表的 8 处关联一次全中）。

> 自关联（isSelf）同样受此影响：部门.上级部门 自己引用自己，控件级 titleField 也要从旧编号改成名称。

## 十六、`options.titleField`：关联控件的「标题字段」必须等于目标表的标题字段

关联控件（单条下拉 / 多条表格）里显示的那一列文本，取的是 **`options.titleField` 指向的 model**，
它必须等于**目标表 `designConfig.config.titleField`**（即该表设计器里选的「标题字段」）：

```python
# 以 销售合同.客户 为例：目标表 mj_cust 的 config.titleField = 客户名称的 model
w['options']['titleField'] = query_form('mj_cust')['desformDesignJson']['config']['titleField']
```

⛔ **写错的症状（2026-09-17 MEGA 实测，用户截图）**：下拉选项显示「**未命名**」、列表里那列空白。
save / deploy / 回读 processJson 全部正常，只有人打开表单才看得见。
成因通常是**用了上一轮构建缓存下来的 model**（模型 ts 与线上不一致）——重建成两轮时最容易踩：
关联控件是第一轮建的，目标表第二轮重建后 model 全变了。
**判定**：把每个 link-record 的 `options.titleField` 与目标表现行 `config.titleField` 比一遍，不等就是错的
（MEGA 里 24 张表一共 37 处）；**修**：按目标表现值改写，save 后回读再比一遍。
本项目脚本：`qqy-mega2/fix_title_field.py`。

