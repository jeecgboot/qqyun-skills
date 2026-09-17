# 条件过滤 rule 速查表

> **强制阅读规则：凡构建列表数据过滤、高级查询、自定义按钮 `conditionsGroup` 等包含小写 `rule` 的条件对象，必须先查阅本文档，确认 rule 值合法。**
>
> **不包括**关联记录控件的 `options.filters`（设计器「设置筛选条件」）：那套用大写 `EQ`/`IN`/`DATE_LT`，见 `desform-link-record.md`。
>
> 本表对齐前端 `useFilterField.ts` 的 `getConditionOptions()` / `getDefaultRule()`。写错的 rule 会导致条件编辑器 `TypeError: Cannot read properties of undefined (reading 'indexOf')`，保存时不报错，用户打开编辑界面才爆。

---

## ⚠️ 核心警告

**`rule` 必须使用字符串 code，不能使用运算符符号。**

| 错误写法 | 正确写法 |
|---------|---------|
| `"rule": "="` | `"rule": "eq"` |
| `"rule": "!="` | `"rule": "ne"` |
| `"rule": ">"` | `"rule": "gt"` |
| `"rule": ">="` | `"rule": "ge"` |
| `"rule": "<"` | `"rule": "lt"` |
| `"rule": "<="` | `"rule": "le"` |
| `"rule": "null"` | `"rule": "empty"` |
| `"rule": "not null"` | `"rule": "not_empty"` |
| `"rule": "not in"` | `"rule": "not_in"` |

---

## rule 完整速查表（按字段类型）

未在下表点名的控件（含 `phone` / `email`）走**文本类**。新增条件时 `rule` 必须填「默认」列，不要一律写 `eq`。

| 字段类型 | 可用 rule | 默认 |
|---------|------------|------|
| 文本类<br>`input` / `textarea` / `phone` / `email` / `auto-number` | `like` `eq` `ne` `like_with_and` `right_like` `left_like` `empty` `not_empty` | `like` |
| 数值/时间类<br>`number` / `integer` / `money` / `rate` / `slider` / `formula` / `summary` / `date` / `datetime` / `datetime_s` / `datetime_sf` / `time` / `year` / `month` / `quarter` / `week` / `x_oa_timeout_date` | `eq` `ne` `gt` `ge` `lt` `le` `range` `empty` `not_empty` | `eq` |
| 单选/省市区<br>`radio` / `area-linkage` | `eq` `ne` `in` `not_in` `empty` `not_empty` | `eq` |
| 联动<br>`category-linkage` | `eq` `ne` `empty` `not_empty` | `eq` |
| 多选/下拉<br>`checkbox` / `select` | `eq` `ne` `in` `not_in` `empty` `not_empty` | `eq` |
| 人员/部门/岗位/下拉树/表字典/组织角色<br>`select-user` / `select-depart` / `select-depart-post` / `table-dict` / `select-tree` / `org-role` | `eq` `ne` `in` `not_in` `empty` `not_empty` | `eq` |
| 开关<br>`switch` | `eq` `ne` `empty` `not_empty` | `eq` |
| 关联记录<br>`link-record` | `eq` `ne` `in` `not_in` `empty` `not_empty` | `eq` |
| 仅判空<br>`sub-table-design` / `map` / `location` / `imgupload` / `file-upload` / `hand-sign` / `color` / `editor` / `markdown` | `empty` `not_empty` | `empty` |
| 系统字段 `create_time` / `update_time` | 同数值/时间类（`type`=`datetime`，`timestamp`=`true`） | `eq` |
| 系统字段 `create_by` / `update_by` | 同人员类（`type`=`select-user`） | `eq` |
| 系统字段 `bpm_status` | 同多选/下拉类（`type`=`select`） | `eq` |
| 系统字段 `sys_org_code` | 同部门类（`type`=`select-depart`） | `eq` |

**不要用的 rule：**

- 文本类**没有** `in` / `not_in` / `gt` / `ge` / `lt` / `le` / `range`，也**没有 `not_like`（不存在「不包含」操作符）**
- `category-linkage` **没有** `in` / `not_in`（按完整路径匹配）
- `link-record` 的 `linkage`（查询工作表）**不要**写进高级查询 / 数据过滤；前端只在右侧筛选、非多选、非 SQL 适配时才出现该选项
- 字段列表排除（`dontShowTypes`）：`link-field`（**仅 saveType=view 排除**）、`daterange`、`datetimerange`、`capital-money`、`ocr`。**link-field saveType=save 会出现在字段列表**，按 `options.fieldType` 走对应类型规则（fieldType=input → 文本类操作符）
- 类型与操作符一一对应：`time`/`year`/`month`/`quarter`/`week`/`date`/`datetime*`/数值类 → 数值操作符集（含 `range`）；`map`/`location`/`color`/`editor`/`hand-sign`/`markdown`/`imgupload`/`file-upload` → 仅 `empty`/`not_empty`；文本类默认集含 `like_with_and`（包含任意）
- ⚠️ 2026-09-09 源码核对（`useComponentCondition.getConditionOptions` + `type.definition.dontShowTypes`）：保存超界面合法的条件项不会报错，但**非法 rule 在界面编辑该条件时无法回显**（下拉无对应项），勿存 `not_like` 之类规则

敲敲云禁止**生成** `category-linkage` / `table-dict` / `select-tree`，但已有字段做筛选仍按上表。

`barcode` / `text-compose` 等未点名控件按文本类（实测 2026-09-10 条件可建、查询不报错）；但 `barcode` 无独立存储列（值由 `options.sourceModel` 指向的编号列生成展示），其文本类条件恒不匹配（`empty` 恒真）——建条件可用，结果为空属预期。

---

## rule 含义与 val 格式

| `rule` 值 | 中文含义 | `val` |
|-----------|---------|-------|
| `eq` | 等于 | 单值 |
| `ne` | 不等于 | 单值 |
| `like` | 包含（全模糊） | 字符串 |
| `right_like` | 以…开始 | 字符串 |
| `left_like` | 以…结尾 | 字符串 |
| `like_with_and` | 包含任意（多个关键词命中任一） | 逗号分隔字符串 |
| `in` | 是其中一个 | 多值：**逗号分隔字符串**（2026-09-10 实测：数组形态编辑器不回显，禁数组） |
| `not_in` | 不是其中一个 | 同上 |
| `gt` / `ge` / `lt` / `le` | 大于 / 大于等于 / 小于 / 小于等于 | 单值 |
| `range` | 在范围内 | **逗号分隔字符串** `"min,max"`，不要传数组 |
| `empty` | 为空 | `""`（前端隐藏值输入） |
| `not_empty` | 不为空 | `""` |
| `linkage` | 查询工作表 | 仅右侧筛选的 `link-record`，高级查询/数据过滤不要用 |

日期字段：**筛选条件值（高级查询、数据过滤）不用毫秒时间戳**——`val` 一律按控件 `format` 传**字符串**：日 `YYYY-MM-DD`、日期时间 `YYYY-MM-DD HH:mm:ss`、月 `YYYY-MM`、季/周转具体日期（季→季度首日如 `2026-07-01`、周→当周周一如 `2026-09-07`；直写 `"2026-Q3"`/`"2026-37周"` 界面不回显，2026-09-11 实测）；系统字段 `create_time`/`update_time` 用全格式 `YYYY-MM-DD HH:mm:ss`（只给日期补 `00:00:00`）；`range` 同样用逗号拼接字符串（如 `"2026-09-09 10:00:00,2026-09-09 11:00:00"`）。⚠️ 2026-09-10 实测+用户确认：高级查询编辑器保存/回显即字符串，存毫秒时间戳会"值不对"。**数据过滤（`/desform/view/updateViewConfig`）同口径**——条件体如 `{"id":"<viewId>","conditionType":"and","conditions":[{"field":"date_...","rule":"eq","val":"2026-09-10","type":"date","name":"日期A"}]}`，日期值为格式化字符串（2026-09-10 用户实测体）。注：直连 `/desform/data/list` 时字符串值实测匹配不到、毫秒时间戳可匹配（前端应用条件时应另有转换，验证以界面为准）。

`in` / `not_in` 时人员、部门、岗位按多选处理。`link-record` 多条时条件项带 `multiple: true`（与控件 `multi` 一致），等于/不等于按完整集合筛选。⚠️ 2026-09-11 实测：按钮 `conditionsGroup` 提交 `multiple` 会被服务端规范化丢弃（CLI 与直连 `/desform/button/update` 均如此，回读固定为 `{field,rule,type,val,valText}`）；link-record 控件的多条标记实际键为 `options.showMode`（`single`/`many`），非 `multi`。

### 条件值形态实测（2026-09-10，对照 UI 已保存样本）

选项/主数据类条件值 **单值=纯字符串、多值=逗号串，禁数组（编辑器不回显）**：

| 类型 | 值（示例） |
|------|-----------|
| `select-user`（含 `create_by`/`update_by`） | username 串，多值逗号串（`"lzy,qianduan03"`） |
| `select-depart`(-post) / `org-role` / `area-linkage` | 部门id / roleCode / 末级区划码 串（`"110101,310101"`） |
| `link-record` | 记录 id 串；多条项带 `multiple:true` |
| `radio` / 单选 `select` | 选项 value 串（`"在职"`） |
| `checkbox` / 多选 `select` | 选项 value 逗号串（`"0,1"`） |
| `switch` / 数值 / 文本 / `empty` | `"Y"`/`"N"`；数字（`range` 用 `"3,4"`）；串（`like_with_and` 用逗号串）；`""` |

- ⚠️ **「当前用户」写 `"#{sys_user_code}"`**（2026-09-15 实测）：`select-user` 条件表达"等于当前登录人"用此形态，不要写「当前用户」等中文字面值。其他系统上下文值（当前部门等）同理。
- 日期/时间类用格式化字符串（见上「日期字段」段）、`range` 逗号串；**与数据落库格式不同**（数据侧人员/部门/关联存数组+`_dictText`），勿混淆。
- 系统字段：`field`=`create_by`/`update_by`（`type`=`select-user`）、`create_time`/`update_time`（`type`=`datetime`+`"timestamp":true`）；含系统字段整包直连 `PUT /desform/view/updateViewConfig`（体 `{"id","conditionType":"and","conditions":[{"matchType":"and","queryItems":[…],"showPop":false}]}`；CLI 不解析系统列）。核验：`GET /desform/superQuery/list?code=` 读 UI 已保存条目。

**条件值取值来源（形态见上表）：** 用户 `/sys/user/selectUserList`（username）、部门 `/sys/sysDepart/queryTreeList`（id）、角色 `/sys/role/list`（roleCode）、字典项取 `itemValue`、关联记录用 `list_data` 按标题匹配取 id、地区用国标末级区划码。`bpm_status` 用编码：1=待提交、2=处理中、3=已完成、4=已作废、5=已挂起、`rejectProcess`=退回中（口语「进行中」=「处理中」）。`sys_org_code` 数据存 orgCode（如 `A22A03`），非部门 id。按钮条件项 = `{field,rule,type,val,valText}`，时间项不带 `timestamp`。未收录形态以环境实测为准，勿按显示文案硬猜。

---

## 条件项完整字段说明

以下字段说明同时适用于：
- 自定义按钮的 `conditionsGroup[].queryItems[]`
- 视图数据过滤的条件项
- 筛选条件（高级查询）的 `queryItems[]`
- 其他任何使用 `FilterItem` 结构的地方

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `field` | ✅ | string | 字段 model（如 `select_1775xxx`）或系统字段名（如 `create_time`） |
| `rule` | ✅ | string | 比较规则，必须是本文档中该类型的合法 code |
| `val` | ✅ | string \| number \| array | 比较值；见上表。`empty`/`not_empty` 传 `""` |
| `type` | ✅ | string | 字段控件类型（如 `input`、`select`、`number`、`date`） |
| `name` | — | string | 字段中文名（界面展示用，可省略） |
| `valText` | — | string | 值的展示文本；**传 `""` 而非 `null`**，否则部分 UI 渲染异常 |
| `timestamp` | — | boolean | 日期字段是否以时间戳形式传值 |
| `multiple` | — | boolean | `link-record` 多条时传 `true` |
| `showPop` | — | boolean | 仅分组上使用，固定 `false` |

### conditionsGroup 分组字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `matchType` | ✅ | 组内条件关系：`'and'` / `'or'` |
| `queryItems` | ✅ | 条件项数组（见上表） |
| `showPop` | — | 固定传 `false`（UI 状态字段，后端忽略但前端依赖） |
