# 简流触发类型详细参考

各触发类型的完整参数说明和真实 processJson 示例。

## 触发方式总表

| startType | 中文名 | createStartNode | 关键专属参数 | 详见 |
|---|---|---|---|---|
| `manual` | 手动发起 | `false` | 无 | 本文 manual 节 |
| `tableEvent` | 工作表事件触发 | `false` | formTableCode/titleField/startEventType/startCondition | 本文 tableEvent 节 |
| `buttonEvent` | 自定义按钮触发 | `false` | 同 tableEvent + inputParams；需另建 Desform 按钮 | 本文 buttonEvent 节 |
| `timerEvent` | 定时触发 | `false` | beginDateStr/timeCycleName/endDateStr | 本文 timerEvent 节 |
| `dateFieldEvent` | 按日期字段触发 | `false` | triggerField/executeType/plusDate/cycleType | 本文 dateFieldEvent 节 |
| `userEvent` | 人员事件触发 | `false` | selectType（1入职/2离职）；formTableList 固定结构 | 本文 userEvent 节 |
| `subEvent` | 子流程（被 callActivity 调用） | `false` | subFormTableObject 必填 | 本文 subEvent 节 + `create-flow.md` 三层规则 |

> ⚠️ **`createStartNode`（是否启用「发起人节点」）本 skill 一律默认 `false`**：builder 默认即 false，**不要手动补 `true`**。仅当用户**明确点名**要「发起人节点／发起人填写／启用发起人节点」时，才在 config 传 `"createStartNode": True`（builder 读该 config 键）。旧文档「`add` only → true」「manual → true」是平台**历史样本的观察值、不是必须值**——线上实测同为 add 触发的流程 true/false 都存在且都正常跑（2026-09-11 用户裁定默认关闭）。

> ⚠️ 后端 `StartTypeEnums` 还含 `signal` / `message`，属**老版设计器遗留**（新版前端抽屉已不提供，仅老数据兼容）——不要在新建流程时使用。触发配置存 `start 节点 attr.startType`；老数据才有顶层 `startType`。
> 触发执行的信号规则（后端 BpmnCreator）：tableEvent 信号名 `{formTableCode}:{表单关联id}:{startEventType}`；buttonEvent `button_signal:{流程id}`；userEvent `user_signal:add|leave:{processKey}`；subEvent 靠全局 `MiniSubProcessStartListener` 继承主流程变量。

## 目录

- [manual — 手动发起](#manual)
- [tableEvent — 工作表事件触发](#tableevent)
- [timerEvent — 定时触发](#timerevent)
- [dateFieldEvent — 日期字段触发](#datefieldevent)
- [buttonEvent — 自定义按钮触发](#buttonevent)
- [userEvent — 人员事件触发](#userevent)
- [subEvent — 子流程触发](#subevent)
- [startCondition — 触发过滤条件](#startcondition)

---

## manual

用户主动发起，无额外参数。流程发起走按钮/页面入口，不需要信号。若流程需要「发起人」节点（后端自动生成：id=startTaskId、type=approver、`${applyUserId}` 表达式），在 config 传 `"createStartNode": True`；**默认不启用**（见上方总表注）。

```json
{
    "startType": "manual",
    "startCondition": [], "conditionFields": []
}
```

---

## tableEvent

工作表新增/更新/删除记录时触发。

**额外参数：**

| 参数 | 说明 | 示例 |
|------|------|------|
| formTableCode | Desform 表单编码 | `ke_hu_shen_qing_co38` |
| formTableName | 表单名称 | `客户信息` |
| formTableId | 表单 ID | `form_start_ke_hu_shen_qing_co38` |
| titleField | 标题字段 model | `input_1775629274119_420857` |
| startEventType | 触发事件 | `add\|update`、`add`、`update`、`delete` |
| startCondition | 触发过滤条件（可选） | 见下方 |
| conditionFields | 监控字段（update 时填） | `["input_xxx"]` |

> `createStartNode`（顶层字段）：**默认 `false`**；仅用户点名要发起人节点时才传 `true`（旧「`"add"` only → `true`」已作废，见上方总表注）
> `formTableId` 格式固定：`form_start_{formTableCode}`，可自动推导。
> **conditionFields 触发时机**：`startEventType` 含 update 时，后端先比对监控字段**新旧值**，只有被监控字段发生变化才继续走 startCondition 校验（子表旧值走 redis 临时缓存）——不要把无需监控的字段塞进 conditionFields，否则记录任何无关字段变动都可能触发。
> **流程参数联动**：tableEvent 配了流程参数（variableList）时，保存前须向根 `formTableList` 追加条目 `{"formTableId":"variable","nodeId":"processVariable","formTableCode":"_variable_","nodeType":"variable"}`；流程参数条目结构 `{id, type:"input"|"number"|"date", options:{format:"yyyy-MM-dd"}, field}`。

**① tableEvent - 新增或更新（createStartNode 默认 false）：**

```json
{
    "startType": "tableEvent",
    "formTableId": "form_start_ke_hu_shen_qing_co38",
    "formTableCode": "ke_hu_shen_qing_co38",
    "formTableName": "客户信息",
    "titleField": "input_1775629274119_420857",
    "startEventType": "add|update",
    "startCondition": [
        {
            "id": "969586911868002304",
            "matchType": "",
            "queryItems": [{
                "rule": "eq", "ruleName": "等于",
                "valueType": "1", "val": "个人客户", "name": null,
                "field": "select_1775648798126_168238",
                "columnName": "客户类型", "type": "select", "valType": "select"
            }]
        }
    ],
    "conditionFields": ["input_1775629274119_420857"]
}
```

**② tableEvent - 仅新增（createStartNode 默认 false，要发起人节点才传 true）：**

```json
{
    "startType": "tableEvent",
    "formTableCode": "ke_hu_shen_qing_co38",
    "startEventType": "add",
    "conditionFields": []
}
```

---

## timerEvent

按固定周期执行。⚠️ **架构分工**：timeCycle `"1"`~`"7"` 预置周期 + 参数表/示例 JSON = 本节；**自定义周期（timeCycle=custom：四轴组合字段/完整可抄模板/需求例句→attr 映射/generateExecTime 验算契约/口语歧义防坑）权威 = `references/custom-cycle.md`**，本文件不全文重复。

**额外参数：**

| 参数 | 说明 | 示例 |
|------|------|------|
| beginDateStr | 首次执行时间 | `2024-05-01 08:30:00` |
| endDateStr | 结束执行时间（用户明确要求时才填） | `2025-12-31 23:59:59` |
| timeCycleName | 循环周期名称（**主要配置项**） | `"每天"`、`"每小时"`、`"自定义"` |
| timeCycle | 脚本根据 timeCycleName 自动映射，一般无需手动设置 | `"3"` = 每天 |

**timeCycle 预置值映射：**

| timeCycle 值 | 含义 | ISO/Cron 格式 |
|---|---|---|
| `"1"` | 每分钟 | `PT1M` |
| `"2"` | 每小时 | `PT1H` |
| `"3"` | 每天 | `P1D` |
| `"4"` | 每月1号 | Cron: `0 0 1 1 * ?` |
| `"5"` | 每周三 | Cron: `0 0 1 ? * WED` |
| `"6"` | 周一到周五 | Cron: `0 0 1 ? * MON-FRI` |
| `"7"` | 每年12月31日 | Cron: `0 0 1 31 12 ?` |
| `"custom"` | 自定义 Cron | 需配合 hourType/dayOrWeekType/monthType |

> UI「循环周期」下拉实名 = 上表「含义」列（每分钟→1、…、每年12月31日→7、自定义→custom）。config 里写 timeCycleName，脚本映射 timeCycle。

> ⚠️ 设置 `timeCycleName`（如 `"每天"`），脚本自动映射为 `timeCycle: "3"` 和 `attr.timeCycle: "3"`。**不要把 `timeCycleName` 设为 null**，否则 `attr.timeCycle` 会变成 `"custom"`，触发无法按预期周期执行。
> ⚠️ 用户说"到XX结束"时必须在 config 中加 `endDateStr`，不能只靠 cron 表达式。

> **「仅执行一次」需求**（用户说"执行这一次即可 / 不用重复"）：timerEvent **没有**「不重复」周期实名——UI 循环周期只有 8 项（每分钟/每小时/每天/每月1号/每周三/周一到周五/每年12月31日/自定义；`dateFieldEvent` 的 `cycleType=1`=不重复 是另一套 startType 的字段，勿跨 startType 套用）。用**调度窗口截断**：`beginDateStr`=执行时刻 + `endDateStr`=当天 `23:59` + 预置周期（推荐「每天」）→ 窗口 `[begin, end]` 内只命中一次（2026-09-09 实测交付；完整配方+全员消息见 create-flow.md 组合 I）。

**自定义 Cron 配置项（timeCycle="custom"）：**

cron 五位格式 `0 {分} {时} {天} {月} {星期}`，各段取值：

| 参数 | 选项（UI 实名） | 值字段 → cron 片段 |
|------|------|------|
| `hourType` | `1`每小时都触发 / `2`按范围触发 / `3`按固定值触发 / `4`按一定增量触发 | 1→`*`；2→`hourValueMin`-`hourValueMax`（0-23）；3→`hourValues[]`逗号拼接；4→`hourValueMin`/`hourValueMax`（**min=起点，max=步长增量**，cron 写 `min/max`） |
| `dayOrWeekType` | `1`按日 / `2`按周（单选） | 决定走 dayValue 还是 weekValue |
| `dayValue`（dayOrWeekType=1） | `1`每天都触发 / `2`按范围触发 / `3`按固定值触发 / `4`按一定增量触发 / `5`每月最后一天触发 | 1→`*`；2→`dayValueMin`-`dayValueMax`；3→`dayValues[]`逗号拼接；4→`dayValueMin`(起点)/`dayValueMax`(步长) 增量（"从1号起每10天"=Min1+Max10+`dayValues=[]`，2026-09-10 用户 UI 定稿）；5→月末（后端特殊处理） |
| `weekValue`（dayOrWeekType=2） | 复选：一~日 | `["MON","TUE","WED","THU","FRI","SAT","SUN"]` 多选数组 → 星期位 |
| `monthType` | `1`每月都触发 / `2`按固定值触发 | 1→`*`；2→`monthValues[]`（1-12）逗号拼接；**⚠️ monthValues 必须字符串数组** `["1","3","5",...]`（写整数能 save/引擎命中但 UI 面板形态错，2026-09 用户 UI 纠正；指定月组合形态/例句 → `references/custom-cycle.md`） |
| 分钟位 | — | 取 `beginDateStr` 按 `yyyy-MM-dd HH:mm` 解析出的**分钟数**（非整点才写入） |

**UI 必填校验（API 构造同样要满足，否则节点 error：** `dayValue=2` 必须有 `dayValueMin/Max`；`dayValue=3` 必须有非空 `dayValues`；`monthType=2` 必须有非空 `monthValues`。

**beginDateStr / endDate / times 的形态（API 构造注意）：**

- UI 绑定的是 `attr.beginDate`/`attr.endDate`（日期对象）；`beginDateStr` 为空时 onSave 兜底写 `beginDate.valueOf()`（**毫秒时间戳数字**）。
- 但后端 `getCustomCron` 用 `yyyy-MM-dd HH:mm` **字符串**解析 beginDateStr 取分钟位——时间戳形态会解析失败、分钟位丢成 `0`。**API 直接构造时 beginDateStr 一律写字符串** `"2026-05-01 08:30"`（本文件示例均为字符串形态，正确）。
- `attr.times` = generateExecTime 返回的未来执行时间列表。custom 调度**落库前必须调接口验算并回填**；预置周期可留 `[]`。
- **generateExecTime 验算（custom 落库前必须；契约全文/验算步骤/跨年心算 → `references/custom-cycle.md` 第三节）：** `POST /act/designer/miniDesFlow/api/generateExecTime`（headers 带 X-Access-Token+X-Tenant-Id），form **Spring 绑定**——数组字段=重复参数（⛔ JSON 串报 500「Failed to convert…Integer[]」）、标量字符串传、dict/复杂对象勿传；成功响应**顶层 `obj`**=未来 7 次列表，回填 `ra['times']=obj` 后 save+deploy。⛔ 含 dayValue=5(每月最后一天) 组合**跳过验算**（预览缺陷：月末算成每月30号/2月不显示/[1,2] 组 500），校验=save+deploy+回读断言。

> ⚠️ **固定月×月末 = 单条 custom 原生组合**（2026-09-10 实测「每年上半年最后一天」建流成功）：`monthType=2`+`monthValues` **字符串数组**（「上半年」=`["1","2","3","4","5","6"]`）+ `dayValue=5`(每月最后一天) 一条即达。口语「上半月」可能指上半年，先与用户确认再建，勿拆两条（dayValues 只收 1-31；完整语义/例句/防坑 → `references/custom-cycle.md`）。

**timerEvent 抽屉完整字段总览（对应 UI）：** 节点名称 / 开始执行时间（beginDate→beginDateStr）/ 结束执行时间（endDate→endDateStr，可不填）/ 循环周期（timeCycle 8 选 1）/ 自定义时：小时配置（hourType+值字段）+ 日/周配置（dayOrWeekType→dayValue 或 weekValue）+ 月配置（monthType→monthValues）。

**③ timerEvent - 每天执行（timeCycle:"3"）：**

```json
{
    "startType": "timerEvent",
    "formTableId": null, "formTableCode": "", "formTableName": "",
    "titleField": null,
    "startEventType": "add|update",
    "startCondition": [], "conditionFields": [],
    "beginDateStr": "2026-04-08 08:00",
    "endDateStr": "2026-04-09 16:48",
    "timeCycleName": "每天",
    "timeCycle": "3",
    "hourType": 1, "dayValue": 1,
    "hourValues": [], "dayValues": [],
    "hourValueMin": 0, "hourValueMax": 23,
    "dayValueMin": 1, "dayValueMax": null,
    "monthValueMin": 1, "monthValueMax": null,
    "monthValues": [], "dayOrWeekType": 1,
    "weekValue": [], "monthType": 1,
    "times": []
}
```

**④ timerEvent - 自定义定时（timeCycle:"custom"，hourType:2=范围）：**

```json
{
    "startType": "timerEvent",
    "timeCycle": "custom",
    "hourType": 2,
    "hourValueMin": 0, "hourValueMax": 10,
    "dayOrWeekType": 1, "dayValue": 1,
    "times": ["2026-04-08 08:00:00", "2026-04-08 09:00:00", "2026-04-08 10:00:00"]
}
```

**timerEvent 完整 builder config 直填示例（新建流程直接抄，`build_process_json` 可消费）：**

```python
ts = int(time.time() * 1000)
config = {
    "processName": "每日待处理提醒",
    "processKey": f"process{ts}",
    "processType": "oa",
    "lowAppId": "<lowAppId>",
    "tenantId": "<loginTenantId>",
    "startType": "timerEvent",
    "beginDateStr": "2026-05-01 08:00",     # 必须字符串（见上方形态说明），时间戳会丢分钟位
    "endDateStr": "2026-12-31 23:59",        # 可选，用户明说结束才填
    "timeCycleName": "每天",                  # ⚠️ 只能用 8 个 UI 实名之一
    "startTaskId": f"task{ts}000",
    "nodes": [
        # get_more 查询 + notice 通知，骨架见 create-flow.md 组合 C
    ],
}
process_json = build_process_json(config)   # 脚本自动映射 attr.timeCycle="3"
result = save_flow(api_base, token, config, process_json)
if result.get('success'):
    deploy_flow(api_base, token, result['result']['id'])
```

> ⚠️ **timeCycleName 简写陷阱**：脚本 `_TIMER_CYCLE_CODE_MAP` 只认 8 个 UI 实名（每分钟/每小时/每天/每月1号/每周三/周一到周五/每年12月31日/自定义）；写简写 `"每月"`/`"每年"`/`"每周"` 不在 CODE_MAP 里，`attr.timeCycle` 会 fallback 成 `"custom"` → 按 cron 逻辑执行而非预期周期。
> **自定义周期唯一生效路径 = attr 组合字段**（hourType/dayValue/weekValue/monthType…），save 前手动并入 `process_json['attr']`（字段见上方「自定义 Cron 配置项」表）。⚠️ config 顶层 `cronExpr` 直写**不生效**：脚本只把它写到顶层 timeCycle，而新版简流后端只读 `attr.timeCycle`（custom 时用组合字段拼 cron），顶层 cron 仅老版双层结构（startType=manual+顶层 timerEvent）才被消费。组合字段表达力有限：**分钟位只能取 beginDateStr 的分钟数**（无法表达 `*/15` 分钟循环），此类需求改用预置周期或拆多条流程。

---

## dateFieldEvent

监控工作表中某个日期字段，到期时触发。

> 一键建壳/带触发条件壳：直接跑 `scripts/timer_job_runner.py datefield --tenant … --app … --table <工作表名> --field <日期字段中文名> --at <HH:MM> [--conds "医生=eq:管理员,状态=eq:待确认"]`（见 SKILL.md 路由/用法，argv 化实测 2026-09-09，带 --conds 的序列化铁律 2026-09-09 用户纠正实证）；本节为手工建流/参数细调的完整契约。

**额外参数：**

| 参数 | 说明 | 示例 |
|------|------|------|
| formTableCode | 监控的工作表编码 | `he_tong_biao` |
| formTableId | 工作表真实 DB id（⚠️ 必须用 `desform/api/fields/{code}` 返回的 `result.id`，禁止用 `form_start_xxx` 格式，否则 UI 显示工作表名称错误） | `（取本环境真实 id，禁止照抄历史值）` |
| formTableName | 工作表名称 | `合同表` |
| triggerField | 触发的日期字段 ID（model） | `date_1234567890` |
| triggerFieldType | 字段类型（4 种） | `year` / `month` / `date` / `datetime` |
| executeType | 执行时机 | `1`=到期当天、`2`=到期前、`3`=到期后 |
| plusDate | 偏移量（executeType=2/3 时），**字符串类型** | `"1"` |
| plusDateUnit | 偏移单位 | `1`=分钟、`2`=小时、`3`=天 |
| executionTime | 每天执行时刻 | `09:00` |
| cycleType | 重复类型 | `1`=不重复、`2`=每年、`3`=每月、`4`=每周 |
| linkFormTableName | 触发字段的显示名称 | `"订单日期"` |

> ⚠️ `plusDate` 必须是**字符串**（`"1"`），不是数字（`1`）。
> ⚠️ **cycleType 枚举**：**`1`=不重复 / `2`=每年 / `3`=每月 / `4`=每周**，每周重复必须用 `4`（不是 `"week"` 或其他）。

**⑤ dateFieldEvent - 到期前1天触发（attr 示例）：**

```json
{
    "startType": "dateFieldEvent",
    "formTableId": "1234567890123456789",
    "formTableCode": "ding_dan_shen_qing_c5dg",
    "formTableName": "订单申请",
    "titleField": null,
    "triggerField": "date_1775640531752_255416",
    "triggerFieldType": "date",
    "plusDate": "1",
    "plusDateUnit": 3,
    "executionTime": "01:00",
    "executeType": 2,
    "cycleType": 1,
    "linkFormTableName": "订单日期",
    "searchFieldGroup": [],
    "startCondition": [],
    "conditionFields": []
}
```

> 脚本已于 2026-04-17 修复对 `dateFieldEvent` 的支持，直接在 config 中传入以上字段即可，无需手动 patch processJson。

**dateFieldEvent 触发条件（记录级过滤，2026-09-09 用户手工修复样本实证；日常用 runner `--conds` 单命令，勿手工拼）：**

结构 = attr.startCondition（单组，非 pj 根级）：
```json
[{"id": "17889493676641", "matchType": "AND", "queryItems": [
    {"id": "1022091181871505408", "rule": "eq", "ruleName": "等于", "val": "admin",
     "name": "管理员", "field": "select_user_..._184896", "columnName": "医生",
     "type": "select-user", "valType": "select-user"}]}]
```
⚠️ 实测铁律（2026-09-09 用户纠正，非推测）：
1. **每行 queryItem 必须带独立 `id`**（数字串）——缺 id 的行设计器无法编辑/删除，且**整组失去「添加条件」「且/或」能力**（用户实测症状）。
2. 组级 `matchType` 大写 `AND`/`OR`（≥2 行时是行间连接符；单行写 `''` 即可，勿写小写）。
3. ⚠️ **日期字段条件行可写，但必须是系统变量「今天」形态**（2026-09-09 用户 UI 手工补行实证；旧版「日期字段禁止写条件行」结论作废——到期调度由 `triggerField`+`executeType=1` 承载，**与日期条件行并存**才是 UI 全貌）：`valueType:3`、`val`=三键系统变量对象、`type`=date、`valType:'variable'`、行带 UI 式雪花 id（无 `name` 键）。UI 补行实测样本（流程「预约表按日期触发-多条件」row12；其余 11 行 API 产物被 UI 保存**原样保留**，id 不重写）：

   ```json
   {"id": "1022104301599891456", "columnName": "预约日期", "field": "date_1788940622445_600374",
    "rule": "eq", "ruleName": "等于", "valueType": 3,
    "val": {"formNodeType": "system", "variableValue": "Today", "variableName": "今天"},
    "type": "date", "valType": "variable"}
   ```

   ⛔ `val` 写日期字符串 / 毫秒 int / `Today` 裸字符串 仍全错（恒不成立或 UI 异常）；变量对象只此三键。语义：条件行做记录级过滤（预约日期==今天），调度仍按 triggerField 到期当天 15:00。runner `--conds` **2026-09-10 起直接支持**（`预约日期=eq:今天` 自动落本形态；全规则 DSL 已覆盖 eq/ne 之外规则：gt/ge/lt/le/like/left_like/right_like/range/in/not_in/empty/not_empty + 全字段族 + 系统字段 + 字面量日期→毫秒），此类需求直接跑 runner `datefield --conds "..."`，不再手工拼。
4. select-user 行形态 = `val`=username + `name`=realname（字符串标量，**无 `valueType` 键**，与 UI 原生行一致）；select/radio 行值直通选项文案（区别于 searchFieldGroup 的 itemValue 口径，勿互套）。

**dateFieldEvent 触发条件控件族支持矩阵（2026-09-10 实测，建流前先按此分类，避免试跑）：**

| 控件（字段 type） | runner `--conds` 值比较 | 条件行形态要点 |
|------|------|------|
| input / textarea | eq/ne/like/left_like/right_like | val=文本 |
| number / integer / money / percent | eq/ne/gt/ge/lt/le | val=数值 |
| date / datetime | eq(宏→变量行)；字面量 → eq/ne/gt/ge/lt/le | 宏「今天」= valueType:3 + 三键系统变量对象；字面量→本地毫秒 int |
| time | eq/ne | val=`"HH:mm:ss"` 字符串 |
| select / radio | eq/ne/in/not_in | val=选项文案（in 时 select 带 `value` 键、radio 不带） |
| checkbox | in/not_in | val=逗号串 + `value`=数组 双形态 |
| switch | eq/ne | val=**activeValue**（字段 raw options 取，本表 Y/N，⛔ 勿写「开」） |
| select-user | eq/ne | val=username + name=realname |
| select-depart / select-position(post) | eq/ne/in/not_in | val=[id] + name=[名] 数组 |
| org-role | eq/ne | val=roleCode、name=null（role/list 按 roleName 反查） |
| area-linkage | eq/ne | val=末级编码 + allVal=编码链——**传「省码\|市码\|区码」，写名称路径无效** |
| link-field | eq/ne/模糊系 | type/valType 写 `input` |
| ⛔ **rate / color / slider / phone / email / select-depart-post** | **不支持（仅 为空/不为空）** | 走追加脚本，形态见下 |

**白名单外 6 类的追加行形态（无 UI 原生样本，按「type=控件类型 + 数值/文本语义」构造，save/deploy/回读通过；语义待首跑）：**
`rate`→val=数值；`slider`→val=数值；`phone`/`email`→val=字符串；`select-depart-post`→**按部门族** val=[岗位id] + name=[岗位名]、type/valType=`select-depart-post`（岗位 id 由 `/sys/position/list` 按名取，⛔ 勿照抄部门族的 `select-position`）；**⛔ color（颜色）控件不支持筛选——不要为其建条件行**（2026-09-10 用户定论）。org-role 追加时若报「租户内查无角色」→ 直接写 roleCode（部分角色记录无 tenantId 字段，runner 的 `tenantId==当前租户` 过滤会漏，如「施工方」=`builder`）。

**两段式建流模板（需求含白名单外控件时）：** ① runner `datefield --conds "<全部支持行>"` 建成（一次过，勿逐字段试）；② 同一脚本 `query_flow(flow_id=<id>)` 回读 → 向组 `queryItems` 追加构造行（行 id 用独立 `f'{ts}{n:03d}'`，与 runner 段不重）→ 按需求原话顺序重排 → `save_flow` + `deploy_flow` → 回读断言（行数 / 中文名顺序 / id 唯一）。实测 24 行 = runner 17 行(9.8s) + 追加 7 行，全链 ~40s。

**dateFieldEvent 完整 builder config 直填示例（合同到期前 1 天提醒，新建流程直接抄）：**

```python
ts = int(time.time() * 1000)
# ① 同脚本内解析字段：GET /desform/api/fields/<formCode>?group=true（或 fetch_form_fields）
#    date_field = 按中文名/类型定位的日期字段 model；db_id = 该接口 result.id（真实 DB id）
config = {
    "processName": "合同到期提醒",
    "processKey": f"process{ts}",
    "processType": "oa",
    "lowAppId": "<lowAppId>",
    "tenantId": "<loginTenantId>",
    "startType": "dateFieldEvent",
    "formTableCode": "he_tong_biao",
    "formTableName": "合同表",
    "formTableId": "<fields接口的 result.id>",   # ⚠️ 真实 DB id，禁止 form_start_ 前缀
    "titleField": "<合同名称字段 model>",
    "triggerField": "<到期日期字段 model>",
    "triggerFieldType": "date",                   # year / month / date / datetime
    "executeType": 2,                             # 1=到期当天 2=之前 3=之后
    "plusDate": "1",                              # ⚠️ 字符串；executeType=1 时可不填
    "plusDateUnit": 3,                            # 1=分钟 2=小时 3=天
    "executionTime": "09:00",                     # 每天执行时刻
    "cycleType": 1,                               # 1=不重复 2=每年 3=每月 4=每周（源码口径）
    "startTaskId": f"task{ts}000",
    "nodes": [
        # 典型组合：get_more（查当天到期记录）+ notice（提醒负责人），骨架见 create-flow.md 组合 C
    ],
}
process_json = build_process_json(config)
result = save_flow(api_base, token, config, process_json)
if result.get('success'):
    deploy_flow(api_base, token, result['result']['id'])
```

> 运行机制：记录 add/update/delete 时后端 `syncRegisterDateFieldTriggerProcessJob` 按「triggerField 值 ± plusDate/plusDateUnit」算目标时间，`cycleType` 2/3/4 生成对应 cron，插入 flowable 定时作业（`act_ru_timer_job`）。即**每条记录一个定时作业**，改字段值会重建作业——不是流程级单一定时。

---

## buttonEvent

工作表自定义按钮触发。attr 结构同 tableEvent，但 `formTableId` 为 `null`（不是 `form_start_xxx`），专属默认 `inputParams: []`（按钮启动时传入的参数，条目 `{name, value}`）。

需要额外通过 Desform 按钮 API 创建并绑定按钮，见 `references/api-reference.md`（Desform 自定义按钮 API 章节）。

> **inputParams 联动**：配了按钮参数时，保存前须向根 `formTableList` 追加 `{"formTableId":"inputParams","nodeId":"inputParams","formTableCode":"_inputParams_","nodeType":"inputParams"}`。按钮运行时入口为 `POST /act/designer/miniDesFlow/api/buttonStartProcess`（processId/dataId/formKey/inputParams/applyUserId），要求流程已发布。

**⑦ buttonEvent - attr 示例：**

```json
{
    "startType": "buttonEvent",
    "formTableId": null,
    "formTableCode": "ke_hu_shen_qing_co38",
    "formTableName": "客户信息",
    "titleField": "input_1775629274119_420857",
    "startEventType": "add|update",
    "startCondition": [], "conditionFields": []
}
```

---

## userEvent

人员入职/离职时触发。`userEventType` 不在 `attr` 内，通过 `formTableList[0].nodeType="userEvent"` 区分。

**selectType**：`attr.selectType`——`1`=当有新人入职时、`2`=当有人员离职时（后端 userStartProcess 按 selectType 匹配信号 `user_signal:add` / `user_signal:leave`）。触发时流程变量 `BPM_FORM_TYPE=3`、`BPM_FORM_KEY=sys_user`、`BPM_DATA_ID=用户id`，startCondition 可对用户字段过滤（走 `getUserEventStartFlag` 判定）。

**formTableList 固定结构：**

```json
[{
    "formTableId": "form_start_sys_user",
    "nodeId": "start",
    "nodeName": "人员事件触发",
    "nodeType": "userEvent",
    "formTableCode": "sys_user",
    "formTableName": "人员事件触发"
}]
```

**⑥ userEvent - attr 示例：**

```json
{
    "startType": "userEvent",
    "formTableId": null, "formTableCode": "", "formTableName": "",
    "startCondition": [], "conditionFields": [],
    "selectType": 1
}
```

---

## subEvent

被主流程 callActivity 调用的子流程。**不是独立触发**——由主流程子流程节点拉起，运行时靠 `MiniSubProcessStartListener` 从主流程继承变量（`BPM_BIZ_TITLE`/`APPLY_USER_ID`/`BPM_DATA_ID`，会签多实例时用 `handleDataId`）。

**专属参数：**

| 参数 | 说明 |
|------|------|
| `subFormTableObject` | **必填**。子流程数据来源声明（JSONObject）：含来源节点类型 `nodeType`（search/getMore/getMoreUserDeptRole，saveFlow 时后端会按 `nodeTypeMain` 记录并把 getMore 强转 search）、来源表 code、`isSubStart:true`；主流程的 `data_get_more` 节点引用它定位数据 |
| `variableList` | 传给子流程的参数（JSONArray），每项生成 CallActivity inParameter（`MI_LOCAL_{field}`→`{field}`） |

```json
{
    "startType": "subEvent",
    "subFormTableObject": {"nodeType": "search", "formTableCode": "ru_ku_dan", "isSubStart": true},
    "startCondition": [], "conditionFields": []
}
```

> ⚠️ **三层规则与发布配方是 subEvent 的完整前置**（config.startType / 根节点 startType / attr.startType 三层全 `subEvent`；发布必须补 `customProcessId`），见 `create-flow.md`「subEvent 三层」段与 `gotchas.md` #31/#45/#47——那两处是权威，本节只列触发参数。

---

## startCondition

触发过滤条件（仅 tableEvent 有效），满足条件才触发流程。

```json
"startCondition": [
    {
        "id": "968429846822821888",
        "matchType": "AND",           // 多条件组须大写 "AND"/"OR"（留空 "" 渲染为「或」，仅单行可用；2026-09-11 实测）
        "queryItems": [
            {
                "rule": "eq",                           // 条件规则
                "ruleName": "等于",
                "field": "select_1775649166520_177631", // 字段 model
                "columnName": "客户状态",               // 字段显示名
                "type": "select",                       // 字段控件类型
                "val": "非成交客户",                    // 条件值
                "valueType": "1",                       // "1"=固定值
                "valType": "select",
                "name": null
            }
        ]
    }
]
```

**rule 全枚举（与设计器「筛选规则」下拉逐项对应）：**

| rule | 说明 | 备注 |
|------|------|------|
| `eq` | 等于 | |
| `ne` | 不等于 | |
| `gt` | 大于 | |
| `ge` | 大于等于 | |
| `lt` | 小于 | |
| `le` | 小于等于 | |
| `in` | 属于 / 是其中一个 | 多值（两种文案并存，纯展示） |
| `not_in` | 不是任何一个 | 多值（2026-09-10 用户 UI 样本：ruleName=不是任何一个；旧文案「不属于」同规则码） |
| `like` | 全模糊 | |
| `left_like` | 左模糊 | |
| `right_like` | 右模糊 | 2026-09-08 用户截图实测：设计器下拉显示「右模糊」，旧文案「结尾是」是错的；ruleName 与选项同名 |
| `empty` | 为空 | `val`/`valType` 写 **null**，禁止空字符串（日期/时间字段写 `""` → 设计器值框显示 Invalid date，2026-09-08 实测） |
| `not_empty` | 不为空 | 同上 |
| `range` | 区间 | 用 `beginVal`/`endVal` 代替 `val` |

> 每个 rule 有适用控件类型白名单（如 `range` 只用于数字/日期），不匹配时 UI 不展示该选项。
> **area-linkage（省市级联动）字段的条件值**：`val`=末级行政编码字符串（海淀区→`"110108"`）+ `allVal`=各级编码数组（`["110000","110100","110108"]`）；写名称路径字符串能 save/deploy 但设计器显示「未选中」（gotchas #57，2026-09-09 实测）。

**val 的变量形态：**

- **系统变量**（val 为精简对象 `{formNodeType:"system", variableValue, variableName}`）：`nowDate`/`nowTime`/`dataSourceId`/`executeId`/`second`/`millisecond`
- **日期范围宏**（后端 `SystemDateRangeEnums`，共 11 个）：`Today`/`Yesterday`/`Tomorrow`/`ThisWeek`/`LastWeek`/`NextWeek`/`Last7Days`/`ThisMonth`/`LastMonth`/`NextMonth`
- 变量引用对象（引用上游节点字段）：`{variableValue, formTableCode, variableName, fieldType, formNodeType, formNodeId, formNodeName}`（formNodeType 枚举：table/subEvent/plus/search/getMore/system/variable/getUserDeptRole/getMoreUserDeptRole/userEvent/function）

**matchType 说明：** 组间恒为「或」（OR）；组内由 matchType 决定——UI 构造存大写 `"AND"`/`"OR"`，后端 `ConditionGroup` 解析小写 `"and"`/`"or"`，两者均可见到，**别手写成混合形态**，跟随本环境 `query_flow` 拉到的既有流程写法。
