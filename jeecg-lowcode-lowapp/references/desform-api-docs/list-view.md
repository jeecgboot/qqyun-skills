# 列表视图 API

基础路径：`/desform/view`

列表视图控制的是数据记录在列表页的展示方式，与表单视图（控制填报界面布局）完全独立。
创建表单时系统会自动生成一个默认表格视图，无需手动调用创建接口。

---

## 查询

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/queryByCodeLite` | `code` | 查询表单下所有列表视图（精简，仅返回 id/name/type/seq） |
| GET | `/queryById` | `id` | 按视图 ID 查询完整配置 |

> ⚠️ 云版 SaaS（app.qiaoqiaoyun.com，2026-09-10 实测）：`/desform/view/queryByCodeLite` 与 `/desform/view/queryById` 均 **404 不存在**；
> 该环境改用 `GET /desform/view/queryByCode?code=<form_code>`（或 `/desform/view/list?code=`，返回 `result.viewList`）——
> 一次直接返回**完整**视图数组（含 columnList/conditions/queryList/orders/buttonList/systemColumnList/showColumn 等全部配置），无需再查详情；view id 为 Mongo 风格 24 位十六进制串。

### `/queryByCodeLite` 返回示例

```json
{
  "success": true,
  "result": [
    {"id": "2039367322597408771", "name": "默认表格", "type": "base", "seq": 0},
    {"id": "2039961002911772674", "name": "项目看板", "type": "card",  "seq": 1}
  ]
}
```

---

## 创建

```
POST /desform/view/addView
Content-Type: application/json
```

**返回值说明：** 新建视图 ID 同时出现在 `result` 和 `message` 字段中。

```json
{"success": true, "message": "2039669254511738881", "result": "2039669254511738881"}
```

### 创建表格视图（type=base）

```json
{
  "type": "base",
  "code": "<form_code>",
  "name": "视图名称（可选）"
}
```

### 创建看板视图（type=card）

```json
{
  "type": "card",
  "code": "<form_code>",
  "groupField": "select_xxx",
  "filterGroupType": "all",
  "titleField": "input_xxx_key",
  "name": "视图名称（可选）"
}
```

> `groupField` 仅支持：单选(radio)、下拉(select)、开关(switch)、人员(select-user/create_by/update_by)、表字典(table-dict)、关联记录单条(link-record)。必须非多选（`multi`/`multiple` 不为 true）。`bpm_status` 可分组；部门 `select-depart` / `sys_org_code`、他表字段仅显示（`link-field` + `saveType=view`）不行。

> `titleField` 传字段的 **key**（不是 model），支持的控件类型：input、textarea、money、integer、number、phone、email、link-record

### 创建日历视图（type=calendar）

```json
{
  "type": "calendar",
  "code": "<form_code>",
  "titleField": "input_xxx",
  "calendarColumnList": [
    {
      "beginDateField": "date_start",
      "endDateField": "date_end",
      "tag": "计划",
      "seq": 0,
      "type": "date"
    }
  ],
  "name": "视图名称（可选）"
}
```

> `endDateField` 可选，不填则显示为单个日期点。`type` 为 `"date"` 或 `"datetime"`，必须与字段控件类型一致。

> 日历 / 甘特图的 `titleField` 传字段 **model**；看板 `titleField` 传字段 **key**。

### 创建甘特图视图（type=gantt）

```json
{
  "type": "gantt",
  "code": "<form_code>",
  "titleField": "input_xxx",
  "ganttFields": {
    "beginDateField": "date_start",
    "endDateField": "date_end",
    "dateType": "date",
    "defaultView": "day"
  },
  "name": "视图名称（可选）"
}
```

---

## 更新

```
PUT /desform/view/updateViewConfig
Content-Type: application/json
```

通用更新接口，`id` 为必填，其余字段按需传入。

```json
{"id": "2039961002911772674", "name": "新名称"}
```

### 表格视图（base）可更新的字段

**基础设置（bgsz）：**

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `lineHeight` | string | `"middle"` | 行高：`"small"` / `"middle"` / `"large"` |
| `autoRefresh` | int | `0` | 自动刷新秒数，0=关闭。下拉只有 0/30/60/120/180/240/300；其它正整数定时器仍会跑，下拉对不上。详见 `desform-list-view.md` 甘特图「自动刷新」 |
| `hasSummary` | bool | `false` | 数据统计开关 |
| `autoSubmitBpm` | bool | `false` | 新增数据后自动提交关联流程 |
| `showColumn` | string | `"default"` | 列显示模式：`"default"` / `"diy"` |
| `fixedColumnNum` | int | `0` | 冻结前 N 列，0=不冻结 |
| `columnList` | array | `[]` | 自定义列配置 `[{field, show, seq}]` |
| `showColumnList` | array | `[]` | 可见性覆盖 `[{field, show}]`，优先级高于 `columnList`，不影响系统字段 |
| `systemColumnList` | array | `[]` | 系统字段显隐 `[{field, show, seq}]`，仅在 `showColumn="default"` 时生效 |

> **`showColumn` 模式差异：**
> - `"default"`：显示前 50 个字段，`textarea`/`editor`/`markdown` 强制排除，系统字段通过 `systemColumnList` 控制
> - `"diy"`：无数量上限，`textarea`/`editor`/`markdown` 默认排除但可在 `columnList` 中显式开启，系统字段通过 `columnList` 控制（`systemColumnList` 此时无效）

**排序（px）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `orders` | array | `[{field, type}]`，`field` 为字段 **model**，`type` 为 `"asc"` / `"desc"`。不要用 `order`。清空传 `[]` |

**快速筛选（kssx）：**

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `queryList` | array | `[]` | `[{field, name, type, queryType, seq}]` |
| `queryButton` | bool | `true` | 是否显示查询按钮 |
| `waitQuery` | bool | `false` | 是否等待点击查询后再加载数据 |

**筛选列表（sxlb）：**

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `leftFilterField` | string | — | 左侧筛选字段 model |
| `leftFilterData` | string | `"all"` | 数据范围：`"all"` / `"part"` / `"exist"` |
| `leftFilterOrder` | string | `"desc"` | 筛选项排序：`"asc"` / `"desc"` |
| `leftFilterCondition` | string | — | 附加过滤条件 |
| `addFormDefaultStatus` | bool | `true` | 新增时是否默认带入当前筛选值 |

**自定义动作**（`zdyan`）：自定义按钮通过独立 API 管理，详见 `references/desform-custom-button.md`。

---

### 看板视图（card）可更新的字段

**看板设置：**

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `groupField` | string | `"create_by"` | 分组字段 model。类型白名单：radio/select/switch/select-user/create_by/update_by/table-dict/link-record（单条）/`bpm_status`。必须非多选；不含 select-depart、link-field 仅显示 |
| `filterGroupType` | string | `"all"` | 显示项：`"all"`=全部，`"part"`=显示指定的项 |
| `filterGroupCondition` | string | `""` | `filterGroupType="part"` 时生效，逗号分隔的分组值；人员字段存储 username |

**卡片外观：**

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `titleField` | string | 表单标题字段 | 卡片标题字段的 **key**（非 model），支持：input/textarea/money/integer/number/phone/email/link-record |
| `showLabel` | bool | `false` | 是否在卡片上显示字段名称标签 |
| `cardColumnList` | array | `[]` | 卡片显示字段 `[{field: key, show: bool, seq: int}]`，`field` 为字段 **key**。显示全部/全部隐藏：已有列表只改 `show` 整表回写；`[]` 不是隐藏全部。不进列表：button/buttons/grid/card/tabs/text/divider/barcode；子表只记子表自身 |
| `coverField` | string | `""` | 封面图字段的 **key**（必须是 `imgupload` 控件），传 `"none"` 表示不显示封面 |
| `coverView` | bool | `true` | 是否允许点击封面查看大图 |

**排序、数据过滤、自定义动作：与表格视图一致。**

> **特别注意：** 看板视图的 `titleField`、`coverField`、`cardColumnList` 中的 `field`，均使用字段的 **key** 而非 model。

---

### 日历视图（calendar）可更新的字段

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `calendarColumnList` | array | — | 日期组，整表替换。结构同创建：`[{beginDateField, endDateField?, tag, seq, type}]`。`beginDateField`/`endDateField` 为字段 **model**；不传 `endDateField` 表示单日 |
| `titleField` | string | 表单标题字段 | 日历事件显示的标题字段 model |
| `calendarDefault` | string | `"dayGridMonth"` | 默认视图：`"dayGridMonth"`（月）/ `"timeGridWeek"`（周）/ `"timeGridDay"`（日） |
| `firstDay` | string | `"0"` | 每周第一天：`"0"`=周日，`"1"`=周一，以此类推 |
| `weekStatus` | bool | `false` | `true`=只显示工作日 |
| `weekDayList` | array | `["0","6"]` | 休息日列表（字符串数组），`weekStatus=true` 时生效 |
| `lunarStatus` | bool | `false` | 是否显示农历 |
| `hourStatus` | bool | `false` | 是否使用24小时制 |

**排序、数据过滤、自定义动作：与表格视图一致。**

**示例 - 完整更新看板配置：**

```json
{
  "id": "2042087764412162050",
  "groupField": "select_xxx",
  "filterGroupType": "part",
  "filterGroupCondition": "一年级,二年级",
  "titleField": "1775221412356_467704",
  "showLabel": false,
  "cardColumnList": [
    {"field": "1775221412356_467704", "show": true,  "seq": 0},
    {"field": "1775221412363_750337", "show": true,  "seq": 1},
    {"field": "1775221412369_947960", "show": false, "seq": 2}
  ],
  "coverField": "1775704940295_808184",
  "coverView": true
}
```

---

## 删除

```
GET /desform/view/removeView?id={view_id}
```

---

## 排序

### 简单排序（移动到某视图之后）

```
POST /desform/view/sortView?id={view_id}&after={target_id_or_first}
```

> `after=first` 则移到最前面。

### 完全重排序

```
POST /desform/view/resetOrder
Content-Type: application/json
```

```json
{
  "list": [
    {"id": "2039367322597408771", "seq": 1},
    {"id": "2039961002911772674", "seq": 2},
    {"id": "2039669254511738881", "seq": 3}
  ]
}
```

> 必须传入表单下**所有**视图的完整顺序，建议先调用 `queryByCodeLite` 获取列表再重排。
