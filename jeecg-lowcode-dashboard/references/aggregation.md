# 聚合表 / 聚合工厂（卡住再读）

> 权威最短路径在 `create.md`「聚合表 / 工厂」。本页只补结构。代码里没有「集合表」一词，口语集合表 = **聚合表**。

## 两种产物

| kind | `relationForms.formType` | 数据来源 | 关联 |
|------|--------------------------|----------|------|
| `single` | `single` | 1 张工作表 | — |
| `multi`（聚合表） | `multi` | ≥1 张工作表 | left / inner / all |
| `factory`（聚合工厂） | `aggregation` | **只能选已有聚合表**（下拉会滤掉工厂） | left / all（无 inner） |

仪表盘 `FormSelectModal` 第二 Tab 同时列出二者，前缀 `[聚合]` / `[聚合工厂]`。绑图一律 `config.type='aggregation'`，`formType` 仍为 `'design'`，`formId=tableName=聚合id`。

## save-agg specs

```json
{
  "name": "库存聚合",
  "kind": "multi",
  "join": "left",
  "forms": ["入库单", "出库单"],
  "links": [{"left": "关联仓库", "right": "关联仓库"}],
  "headers": ["关联仓库"],
  "calcs": [{"name": "净入库", "expr": "入库数量-出库数量"}],
  "filters": [{"form": "入库单", "field": "审批状态", "op": "等于", "value": "已通过"}]
}
```

- 同名则 `edit`，`{"new": true}` 强制新建。
- 工厂/多表连接行必须带行 id——前端按 id 渲染连接配置，无 id 时设计器打开工厂显示「无连接配置」需手修重连。已修入脚本：multi/factory 每行自动补 `row_n`、工厂源字段自动补 `children: []`（2026-09-08 实测教训，勿再手补）。
- 工厂（formType=aggregation）存储结构（对照 UI 保存版）：`relationForms = {formList:[{label, value=<源聚合id>, fieldOptions:[{title,value,type,options,children:[]}…]}…], fieldList:[{<左聚合id>:<左字段value>, "id":"row_n", <右聚合id>:<右字段value>}…], formType:"aggregation", relationMode:"left|all"}`；`headerFields=[{name:"左标题-右标题", value:"<左value>-<右value>"}]`（行表头=配对字段链）；`calculateFields` 同聚合表。
- `expr` 写中文字段名即可，脚本编译为 `$入库数量@model@formCode@common$`。
- 公式落库后图表字段名 = 去特殊字符名 + calcId 前 5 位（如 `总额fc37c`）。行表头 `fieldName` = 多表 value 链的第一段。
- 未传 `links` 时按**同名标题**自动配对。
- 聚合图 **不显示查询范围**，`add-charts` 会把非 `all` 改成 `all`。

## 改已有聚合（公式 / 过滤，最短路径，2026-09-08 实测沉淀）

`save-agg` 同名 = **全量重建 PUT**：specs 里缺的 forms/links/headers/filters 会被清空覆盖，specs 须给全。**公式 id 保留规则**：specs 每条 calcs 带 `"id"` 则原样保留，不带则生成新 uuid——而图表公式列字段名 = 去特殊字符名 + calcId 前 5 位（如 `库存件数1a9b0`），**已绑公式列的图按字段名定位，uuid 重建即断链**。故改公式（改名/新增/删）最少 2 轮、零读代码：

1. **1 条 Bash 查询**：`GET /drag/onlDragTableRelation/list` 按 `aggregationName`（注意：字段叫 aggregationName 不是 name）命中，摘要打印 `id / aggregationName / calculateFields / headerFields / filterCondition`（原公式 id+name+formulas、现有过滤全在此；连带拿 formCode 值供 specs 用）。**必带 `PYTHONIOENCODING=utf-8`**（漏了中文名输出乱码 → 整条重查一遍）；`relationForms / headerFields / calculateFields / filterCondition` 落库均为 JSON **字符串**，须 parse 后再摘要
2. **Write specs**：`{name, kind, forms, headers, filters}` 按查得结构原样给全；`calcs` 只放结果公式：
   - 改名 → `{"id":"<原公式id>", "name":"新名", "expr":"字段中文名"}`（expr 写中文名即编译回原 formulas；原 expr 可从 formulas 的 `$名@id@code@common$` 反推「名」段 + 运算符）
   - 新增 → `{"name":"新公式名", "expr":"库存数量/1000"}`（无 id，脚本生成新 uuid）
3. **1 条 `qqy_ops.py save-agg <API> <TOKEN> --tenant-id/--tenant-name --app-name/--app-id --name <聚合名> --specs-file <JSON>`**（specs 可带 `"id":"<聚合id>"` 精确定位编辑；**save-agg 不收 `--form-name`**——那是聚合加图 add-charts 的旗标，误传 = usage 报错），`AGG_SAVED=` + `AGG_ACTION=edit` 即停

**加/改过滤（2026-09-08 实测）**：同名保存 = 过滤同样全量重建，specs 加 `"filters"` 数组即落库（需与步骤 1 查得的保留条件合并）：
```json
"filters": [
  {"form": "实时库存", "field": "库存数量", "op": "大于", "value": 10},
  {"form": "实时库存", "field": "关联物料", "op": "包含", "value": "水泥"}
]
```
中文 `op`（等于/大于/包含…）由脚本编译；落库 `filterCondition` 条 = `{form:{label,value,fieldOptions 全量}, title/name/field/type/options, rule:"eq"/"like"…英文码, val:"值"}`。⚠️ link-record 类字段按标题文本过滤（如 关联物料 包含 水泥）命中与否取决于查询后端是否翻译，交付后建议 1 次数据预览确认。
**选项核对免探查（2026-09-08 实测）**：save-agg 落库后回查 1 次 `list`，`filterCondition` 内嵌所选字段完整 `options`（radio/select 选项原文全在）——核过滤值与选项文本一条查询即完成。勿为核选项先查 fields / 预览 / 翻 lowapp 脚本找工作表字段接口（全是零产出探查）。

禁读 create.md / qqy_ops.py（铁律禁 grep 脚本）；本文件也只在卡住时读。实测 3 轮 ≈35s–1min 完成（对照：预读文档+读脚本 600 行曾耗 10 轮）。

## 关联字段 / 行表头（对照前端 DBFormTable + 后端 `$lookup`）

前端校验（`DBFormTable.vue`）：同一行左右 `type` 须相同；数值族（money/integer/number/rate/slider/formula/summary）可互配；任一侧是 `link-field`（他表字段）则放行。`link-record` ≠ `input`。UI 红字「[文本]xxx字段类型不匹配」。

后端多表连接（`MongodbUtil.getAggregationTableQuery`）：**只按 `fieldList[0]` 做 `$lookup(from, localField, foreignField)`**，即主表该字段的**存值** = 从表该字段的**存值**。后续 `fieldList` 行只是对已 lookup 数组再 `$filter`，不是第二条独立关联。

| 用户点名 | 正确写法 |
|----------|----------|
| 两表都有同名同类型且存同一值的字段（如入库单/出库单都有「关联仓库」） | `kind:multi`，`links: [{left:"关联仓库", right:"关联仓库"}]` |
| 要按本表关联记录的名称分组（如库存的仓库名、物料名） | **单表** `kind:single`，行表头直接选「关联仓库」「关联物料」。后端 `linkRecordFieldTranslate` 会用 `titleField` + `sourceCode` 对 `_id` lookup 成名称 |
| 「关联记录」对档案标题文本（库存.关联仓库 ↔ 仓库.仓库名称） | **禁止。** 类型不同；值也不同（存的是对表 `_id`，不是名称） |
| 改成对表反向关联记录（库存.关联仓库 ↔ 仓库.实时库存） | **禁止。** 类型能过，但值对不上（仓 id ≠ 库存 id），`$lookup` 结果空 |

**行表头（多表）：** `getHeaderList` 只从 `fieldList` 拼 `左标题-右标题`。`headers` 写关联字段名即可。未参与 `links` 的字段不能当行表头。单表 `fieldList`=该表全部字段，行表头可选任意字段。

`save-agg`：类型不兼容 → `LINK_TYPE_MISMATCH`（不改写成双向回指）；多表非关联行表头 → `HEADER_NOT_IN_LINKS`。

## 绑图

```bash
py qqy_ops.py add-charts … --form-name "库存聚合" --specs-file SPECS.json
```

不必 `--form-type aggregation`。`forms` 列表 `relationForms` 是 JSON **字符串**，须 parse 后再看 `formType`。

### 聚合图维度 = 聚合输出本地列（2026-09-08 实测教训）

- **dim 只绑聚合输出本地列**：行表头/分组列原词（如「关联仓库-实时库存」）+ 公式数值字段名（`库存合计c793b` 型）。点名维度若**只存在于关联记录源表单**（如对「关联仓库」传源表里的「仓库名称」）→ 脚本回退写 `LINK_DIM {localField: link列, fieldName: 源表字段id, sourceCode}`；但聚合结果行的 key 只有本地列（link_record 列 / 公式列），**没有源表 input id** → 前端匹配不到数据列，维度设置渲染不出字段。
- 正确形态（对照用户手修）：`nameFields` 绑本地列本身 `fieldName==localField`，显示文本走 link 列元数据 `options.titleField`（=源表标题字段 id，如仓库名称）——由聚合表字段元数据自带，勿人为拼 sourceCode 链。
- 新图非默认色：`add-charts` 的 `--oral` 颜色词未落库（实测 `ORAL_APPLIED` 只 comp/dim/val，`itemStyle.color` 空）→ 加图后补 `set-chart-color`（浅紫 `#673bb7` = 用户手修值）。
- **排序坑（2026-09-08 实测）**：`set-chart-sort` 按数值列（公式/输出列，fieldName=`库存合计69c48` 型 = 中文名+calcId 前 5 位）排序时，**不要把该 fieldName 写进 `sorts.name`**——前端数据面板/渲染不认 calcId 后缀键，落盘后整图白屏，设计器手工保存会清空 name（保留 type/前 N）才恢复。`set-chart-sort` 已内置回退：聚合表（`config.type=aggregation`）value 侧排序自动留空 name、仅保留 type 与前 N 并打 `NOTE=`；精确排序列需在设计器数据面板手选。按维度列（nameFields 本地列）排序行为未验证。

## 接口

| 用途 | 方法 |
|------|------|
| 列表 | `GET /drag/onlDragTableRelation/list` |
| 图表字段 | `GET /drag/onlDragTableRelation/getFields/{id}` |
| 工厂选源字段 | `GET /drag/onlDragTableRelation/getAggregationFields/{id}` |
| 预览 | `POST /drag/onlDragTableRelation/queryTableData` |
| 保存 | `POST …/add` · `PUT …/edit` |

校验 `validateInfo` 前端开关恒假，不必写。
