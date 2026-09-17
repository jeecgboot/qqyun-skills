# 查询工作表（linkage 类型默认值）

## 一、概述

查询工作表是控件默认值的高级配置，通过 `advancedSetting.defaultValue.type = "linkage"` 启用。根据条件自动从其他工作表查询数据，将结果回填到当前字段。

### 与 link-record + link-field 的区别

| 特性 | link-record + link-field | 查询工作表（linkage） |
|------|------------------------|-------------------|
| 交互方式 | 用户手动选择 | 自动根据条件查询 |
| 触发时机 | 用户操作 | 表单加载 + 依赖字段变化 |
| 绑定位置 | 独立控件 | 任意控件的默认值配置 |
| 存储方式 | 存储关联记录 ID | 存储查询结果值 |

## 二、配置格式

```json
{
  "advancedSetting": {
    "defaultValue": {
      "type": "linkage",
      "value": { "appId": "…", "desformCode": "…", "operation": "FIRST", "rules": [], "linkages": [], "…": "…" }
    }
  }
}
```

> ⚠️ **`value` 直接存配置对象本身（JSON 对象），禁止存成字符串（含 URL 编码串 / JSON 序列化串）**——2026-09-16 核对部署产物：①运行时 `lib/jm-form-bundle/JmForm.umd.js` 的 `decodeLINKAGETConfig` 是恒等函数、调用点直接取 `config.rules / config.linkages / config.desformCode / config.appId`；②设计器 `lib/jm-form/JmForm.umd.js` 弹窗提交即 `advancedSetting.defaultValue.value = encodeLINKAGETConfig(配置对象)`，该 encode 同样是恒等函数（模块 532）。存字符串时保存与回读全绿，但**运行时静默不取数、设计器「查询工作表设置」面板显示为空**（表现为「默认值没配」）。与 `fast-link-record-linkage.md` 的「字符对象」配方并存时以本节为准（字符对象是更早部署版本的产物）。

### 配置对象（直接作为 `value`，不编码）

```json
{
  "appId": "",                // 目标工作表所属应用 ID——必填真实值，勿留空（见下 ⚠️）
  "desformCode": "",         // 目标工作表 code（必填）
  "matchType": "AND",        // "AND" / "OR"
  "operation": "FIRST",      // 聚合操作
  "rules": [],               // 查询条件（至少一条）
  "linkages": [],            // 字段映射（COUNT 时可空）
  "sorts": [],               // 排序（CUSTOM_SORT 时需要）
  "isMultiple": false,
  "maxRecordCount": 200
}
```

> ⚠️ **`appId` 必须填目标工作表所属应用的真实 ID，禁止留空 `""`**（2026-09-08 实测：日期控件默认值=查询工作表，`appId` 留空整单保存后，设计器「查询工作表设置」面板**应用/工作表两处空白**——条件与字段映射仍可读）。面板先按 `appId` 回填「应用」下拉、再按该应用过滤「工作表」下拉；同应用目标直接写当前应用 ID。上文配置对象与示例中的 `""` / 缺省写法只是「编码前」示意，UI 保存必然写入所选应用。

## 三、operation 聚合操作

| 值 | UI 文案 | 说明 | 需要 linkages |
|----|------|------|:---:|
| `FIRST` | 最新的 | 最新一条（按 `create_time desc`） | 是 |
| `LAST` | 最老的 | 最老一条（按 `create_time asc`） | 是 |
| `CUSTOM_SORT` | 自定义 | 按自定义排序取第一条；排序行默认 `create_time desc` | 是 |
| `IGNORE` | 不获取 | 匹配多条时不取任何数据（返回空） | 是 |
| `COUNT` | 数量 | 统计符合条件的数量，不需要字段映射 | 否 |
| `MAX` | 最大值 | 取最大值，适用于**数字或日期**字段 | 是 |
| `MIN` | 最小值 | 取最小值，适用于**数字或日期**字段 | 是 |
| `AVG` | 平均值 | 取平均值，**仅数字**字段 | 是 |
| `SUM` | 求和 | 求和，**仅数字**字段 | 是 |

> 补充口径（2026-09-07 源码核对）：
> - **COUNT/MAX/MIN/AVG/SUM 只在非关联记录场景提供**（默认值、函数计算 LINKAGET、子表等）；关联记录「默认值=查询工作表」时下拉只有 FIRST/LAST/CUSTOM_SORT/IGNORE。
> - 聚合类要聚合哪个源字段，由字段映射行的 `linkModel` 决定（如 求和 需映射行 linkModel=源表金额字段）；COUNT 不用映射。
> - MAX/MIN 取的是对应映射字段值的最大/最小（数字按数值、日期按时间比较）。

## 四、rules 查询条件

```json
{
  "model": "target_field_model",
  "rule": "EQ",
  "valueType": "field",
  "value": ["current_field_model"],
  "sqParam": { "type": "input", "rule": "eq" }
}
```

- `rule`：**QueryRuleMap 大写 key**（`EQ`/`IN`/`DATE_LT`…），禁止小写、禁止 `range`/`isNull` 等旧写法。中文与可用类型见下
- `valueType`：`fixed` = 固定值；`field` = 引用本表字段值（本表字段 model 数组，运行时取 `[0]`，值为空整条规则跳过）；`system` = 系统变量（仅前端高级查询模式提供，查询工作表设置普通模式没有）
- `value`：**始终数组**。fixed 存比较值；field 存 `[本表字段model]`；**「本表字段值」的候选列表含「上下文变量」分组 5 项**（2026-09-09 源码核对，09-09 UI 实测存储形态）：当前登录人账号、当前登录人名称、当前登录人的部门编号、当前系统日期、当前系统时间——选中后 `value[0]` 存 **`_CONTEXT_VAR_sysUserCode` / `_CONTEXT_VAR_sysUserName` / `_CONTEXT_VAR_sysOrgCode` / `_CONTEXT_VAR_sysDate` / `_CONTEXT_VAR_sysTime`**（**不带 `$` 包裹**；API 直写曾误带 `$...$`，新增页不回填，2026-09-09 UI 对比实测），运行时按上下文变量取值（`select-user`/`select-depart` 源字段存储 id 而变量是账号/部门编号时可能永不相等，属存储形态差异，不回填脏值属预期）。⚠️ **反向注意**：`advancedSetting.defaultValue.value`（默认值 / 表达式）里的同名变量**必须带 `$`**（`$_CONTEXT_VAR_sysDate$`）——两个键要求相反，别互套（见 `fast-create.md`「建后补丁契约速查」）
- `sqParam`：保存时自动生成——`type` = 源字段控件类型（如 input/select/money），`rule` = 小写运行时规则（`eq/ne/gt/ge/lt/le/like/not_like/right_like/left_like/in/not_in/empty/not_empty`），**UI 面板保存才自动生成，API 整单写设计 JSON 不会补，必须手写**（2026-09-08 实测：同表手工 UI 配置的字段带 `sqParam` 新增页正常回填；API 直写缺 `sqParam` 的 linkage 配置，新增页不回填——补齐 `{"type": 源字段控件类型, "rule": 小写规则}` 后一致）
- 无值规则 `EMPTY` / `NOT_EMPTY`：`value: []`，仍算一条有效条件

**中文 ↔ 大写 key 快速映射：** 等于`EQ` 不等于`NE` 大于/大于等于/小于/小于等于`GT/GE/LT/LE`（数值类） 包含/不包含`IN/NOT_IN`、开头是`BEFORE`、结尾是`AFTER`（文本类） 早于/早于等于/晚于/晚于等于`DATE_LT/LE/GT/GE`（日期类） 是其中一个`IS_ONE_OF`（单选类） 包含其中一个`IN_ONE_OF`（多选类） 为空/不为空`EMPTY/NOT_EMPTY`。

**按源字段类型的完整可用规则表与禁止项**（同时包含/开头不是/结尾不是/值发生变化在高级查询里不可用）与 `desform-link-record.md` §3.2 是同一套，不重复展开，直接按该表取用。

## 五、linkages 字段映射

```json
{
  "model": "current_field_model",
  "linkModel": "target_field_model",
  "linkName": "显示名"
}
```

一次查询可映射多个字段，查询到数据后批量回填。

## 六、sorts 排序

```json
{ "column": "field_model", "order": "desc" }
```

仅 CUSTOM_SORT 时生效，支持多字段排序。

## 七、执行时机

1. **表单加载时**：发现 `type="linkage"` 立即执行查询
2. **依赖字段变化时**：自动 watch rules 中 valueType="field" 引用的字段
3. **防抖**：500ms 防抖 + queryId 去重

## 八、后端 API

```
POST /desform/data/aDefVal/linkaget
```

请求体（2026-09-07 源码核对）：
```json
{
  "key": "控件key",
  "appId": "应用ID",
  "desformCode": "target_code",
  "operation": "FIRST",
  "superQueryString": "URL编码的高级查询JSON（encodeURIComponent）",
  "linkages": [{"model": "...", "linkModel": "..."}],
  "sorts": [{"column": "...", "order": "desc"}],
  "designSubMode": false,
  "multiple": false,
  "maxRecordCount": 200
}
```

- 请求发出前 **500ms 防抖 + queryId 去重**（同控件连续触发只认最后一次请求的响应）
- `multiple: true`（`isMultiple`）时查询多条回填数组型字段，`maxRecordCount` 缺省按 **200**
- 返回数据若是含 `{` 或 `[` 的 JSON 字符串会先解析成对象/数组再回填（数组型/多值结果）

## 九、编码机制

> **2026-09-07 源码核对：** 当前前端保存/回读 linkage 配置时**已不再压缩键名**（旧版曾压缩为 `aid/fCode/mType/oper/lModel/vType` 等短键；短键映射仍被兼容，历史数据可正常读取）。新写配置**直接用完整键对象即可**：
> ```json
> {"appId":"...", "desformCode":"...", "matchType":"AND", "operation":"FIRST",
>  "rules":[...], "linkages":[...], "sorts":[...], "isMultiple":false, "maxRecordCount":200}
> ```
> 若某版本又出现「写入后设计器面板不显示」现象，按 `fast-link-record-linkage.md` 的字符对象配方落地（2026-09-02 起 `update_link_record.py` 已内置字符对象 + 整单保存）。

改已有关联记录不要手写这段：走 `scripts/update_link_record.py`（`references/fast-link-record.md`）。

## 十、示例

### 根据订单号自动填充金额

```json
{
  "desformCode": "order_form",
  "matchType": "AND",
  "operation": "FIRST",
  "rules": [{
    "model": "order_no",
    "rule": "EQ",
    "valueType": "field",
    "value": ["input_order_no_xxx"]
  }],
  "linkages": [{
    "model": "money_amount_xxx",
    "linkModel": "order_amount"
  }],
  "sorts": [{"column": "create_time", "order": "desc"}]
}
```

### 统计符合条件的记录数

```json
{
  "desformCode": "task_form",
  "matchType": "AND",
  "operation": "COUNT",
  "rules": [
    {"model": "assignee", "rule": "EQ", "valueType": "field", "value": ["select_user_xxx"]},
    {"model": "status", "rule": "EQ", "valueType": "fixed", "value": ["进行中"]}
  ],
  "linkages": []
}
```

## 十一、常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 查询不执行 | rules 为空或依赖字段无值 | 确保至少一条有效 rule |
| 返回空值 | IGNORE 模式下匹配到多条 | 改用 FIRST |
| 字段映射无效 | linkModel 错误 | 核实目标表字段 model |
| 编辑模式不触发 | linkage 默认值仅新增时生效 | 编辑时用 JS 增强 |

## 十二、设计器「查询工作表设置」弹窗行为（2026-09-07 源码核对）

适用场景为同一弹窗的不同形态：高级默认值=查询工作表（type=linkage）、关联记录默认值=查询工作表、**函数计算编辑器内的 LINKAGET 配置**、设计子表默认值=查询工作表。
> **注意区分**：radio/checkbox/select「选项数据源=查询工作表」（同名弹窗，产出 `options.linkDataConfig`，含 sortType、无 operation）不是本文档对象，见 `desform-option-datasource.md`。

- **新配置默认**：`matchType=AND`、`operation=FIRST`、rules/linkages/sorts 为空、`isMultiple=false`、`maxRecordCount=200`
- **提交校验**：至少一条有效筛选条件——值为空的规则会被剔除，但「为空/不为空」类无值规则算有效（值类型自动置 `fixed`）；`operation ≠ COUNT` 时至少一条字段映射
- **目标表可选字段** = 工作表字段 + 系统字段 `create_by`/`create_time`/`update_by`/`update_time` + `bpm_status`（流程状态，字典 `bpm_status`），筛选条件/排序/映射都可选它们
- **sqParam**：UI 保存时自动填充（type=目标字段控件类型映射、rule=高级查询规则映射）；**API 直写配置不会自动生成，须手写同规则值**，否则运行时查询失败不回填（见 §四 ⚠️）
- **operation UI 语义**：FIRST=最新一条、LAST=最老一条、CUSTOM_SORT=自定义排序取第一条、IGNORE=不获取、COUNT=数量、MAX/MIN=最大/最小值（数字、日期）、AVG=平均（仅数字）、SUM=求和（仅数字）；**COUNT/MAX/MIN/AVG/SUM 仅在非关联记录场景提供**
- **isMultiple（多值/多条回填）**：operation 锁定 `CUSTOM_SORT`，出现「查询数量」输入（1~500，默认 200）；发出请求时带 `multiple=true`
- **linkName**：含半角括号 `()` 时以百分号编码存储（`%28`/`%29`），显示时解码
- **字段映射行** = 本表目标控件 model → 目标表字段 model（linkName 为显示名）；关联记录默认值场景下空映射自动补「本控件 model → `_id`（记录 ID）」
