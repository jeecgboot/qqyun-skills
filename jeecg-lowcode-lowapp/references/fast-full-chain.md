# 全链路新建（应用 + 工作表 + 关联 + 简流 + 盘 + 灌数）

**只读两页**：本页 + **`engine-contract.md`**（引擎硬约束一页纸——那十几条**不报错、
只静默写坏**，写规格前必须先读完）。读完第一条 tool call 必须是执行脚本。

**禁止：** 并行 Read `jeecg-lowcode-lowapp` / `miniflow` / `dashboard` 的 SKILL.md 全文；`memory_search`；`miniflow-node-types.md`；`example/入库审批*.md`；`widget-options`；`json-config`；`desform-lowapp.md` 全文；`--help` 再确认。

> **动真机前先过 `scripts/precheck.py`**（纯静态、不联网、可反复跑）：
> `python scripts/precheck.py --spec app_spec.json --flows flows.py --expect "表单=52,字典=22,看板=25"`
> 拦的是**本来要真机才暴露**的错：公式占位符、带出字段名、看板透视空 `val`、
> 查询面板跨表、流程 `ref/cond` 引了本行没有的字段、**网关单出口带条件**、
> **标题只靠关联带出**。
> 2026-09-16 建 52 表应用实测：不过这一关，每一类错都要付一次 3~9 分钟的重跑。
>
> ⚠️ **`--flows` 必须带**（2026-09-17 实测事故）：漏传时**流程段整段不跑**，
> 却照样打印「✓ 可以动真机了」—— 那一轮 63 条流程带着 19 个静态就能查出的错上了真机，
> 代价是一轮 19 条失败 + 两轮 234s 全量重发。现在**漏传会被直接拦下**（目录里有
> 带 `FLOWS =` 的 `.py` 就报错），确实没有流程时用 `--no-flows` 显式跳过。
> 另外：有提示时收尾语变成「✓ 预检通过（有 N 条提示，逐条确认过再动真机）」——
> **提示里躺着的正是「接口全绿但内容错」那类**（19 张表的标题就是这么漏掉的），别不看。

**预算（2026-09-16 实测，走 `build_app.py`）：**

| 规模 | 墙钟 | 瓶颈 |
|---|---|---|
| 4 表全流程 | **20 秒** | — |
| 52 表 6 段 | **约 6 分钟** | 建壳数分钟；补丁已不再是瓶颈 |
| 单段 | 流程 52 条 **51 秒**；看板 25 张 **22 秒** | 都很快，别怕批量 |

> **补丁段的瓶颈已修**（2026-09-16）：原先 52 张表**串行**读设计 ≈ **4 分 31 秒**，
> 而每次跑补丁都要付一遍。真凶不是并发度，是 `query_form()` 里
> `get_form_id` 逐表走的慢路径（每表 2~3 次 HTTP）。
> 现在 `prewarm_form_ids()` 用 `/online/lowApp/miniflow/tenantAppFormList` **一次**拿全
> 「编码→ID」，再加 4 并发读 —— **4 分 31 秒 → 5.2 秒**。
> 注意：各轮之间**本来就不重读**（设计读进内存后各轮在内存里重算），优化点只在第一遍读。

**超标 = 在逐条手工拼、或又在读文档**，不是接口慢（读 5ms / 写 330ms）。
手工逐条时 63 条流程要 55 分钟、25 张盘要 42 分钟 —— 差的是**轮数**，不是速度。
另一类超标是**返工**：规格里一个静态错误 → 一次真机重跑。所以 `precheck.py` 是必需品。

（本页与 dashboard skill / multiform-template 同规则处**同步维护**：改 add-filter 约束等规则时两处同改，本页=全链路自包含优先。）

## ⓪ 先看规模：≥10 张表就走编排器，别手工串

`build_app.py` 一条命令跑完六段，每段回读计数、有缺口非零退出：

```bash
python "<lowapp>/scripts/build_app.py" --api-base URL --token TOKEN \
  --tenant-name "租户名" --app-name "应用名" --create-app --spec app_spec.json --rows 2
```

规格格式（表名+字段名+关系，**只写业务语言**）见 `app-spec.md`。字段类型由 `spec_infer`
推断、关联/汇总/字典由 `patch_fields` 建、流程由 `build_flows` 建——都不用手写。
`--from 阶段名` 续跑，`--only 阶段名` 单跑。

**手写各段只在表数很少、或要做编排器覆盖不到的定制时。**下面 ①–⑦ 是各段的做法。

用户点名了顺序就跟点名。默认：①应用 ②分组+工作表 ③双向关联 **④灌数** ⑤简流 save+deploy
⑥按钮绑简流 ⑦仪表盘。

> ⚠️ **④灌数 必须排在 ⑤简流 之前。** 原先默认「最后灌数」，`add_data` 会触发该表的
> tableEvent 主流程，而主流程普遍带「取多条 → 逐行调子流程」——灌 N 行 = **N 轮级联写**。
> 2026-09-15 实测照旧顺序跑：**1 小时 4 分，后端崩一次**；2026-09-16 复现：52 条流程建好后
> 再灌数，**6 分钟没跑完，后端直接失联**（同一天干净顺序只要 3.7 分钟）。
> 流程还没建时先灌：无级联。这条以前只写在注释里、靠人记得，现在 `build_app.py`
> 的灌数段会**主动拦住**（应用里已有流程就报错退出，见 `stage_data`）。

凭证：本轮消息或本会话已有的 api-base / token；租户按**名**匹配（`--tenant-name`），禁止用默认 `X-Tenant-Id:2` 冒充点名租户。Windows：中文只进 UTF-8 JSON / `.py`，禁止 `python -c` 内联中文。

---

## ① 应用（零预读）

```bash
python "<lowapp>/scripts/lowapp_creator.py" --api-base URL --token TOKEN \
  --tenant-name "租户名" --config create_app.json
# create_app.json: {"action":"create","appName":"应用名"}
```

⚠️ **规格给了应用的图标/主题色/封面就一定要传，不要省**——不传走脚本默认值 `iconType=ant-design:schedule-outlined`、`iconBackColor=rgb(0, 188, 212)`、`appCoverImg=coverImage002`，**撞对两项也是巧合**，封面基本必错（2026-09-16 用户实测：「图标/颜色/封面 这个是不是没有对上」→ 只有封面错，前两项恰好等于默认值）：

```json
{"action":"create","appName":"应用名",
 "iconType":"ant-design:schedule-outlined", "iconBackColor":"rgb(0, 188, 212)",
 "appCoverImg":"coverImage009"}
```
改已有应用（`action:edit` **必须带 `id` 或 `fromName`**，只给 appName 会报「JSON 必须提供 id 或 fromName」）：`{"action":"edit","id":"<app_id>","appName":"...","iconType":"...","iconBackColor":"...","appCoverImg":"..."}`；`action:list` 回读三项核对。

打印的 `tenant_id` / `app_id` 后面全用，禁止再 list。

## ② 分组 + 工作表（同一对话轮，可先分组后表）

分组：`init_lowapp` 后 `create_worksheet_group(group_name=…)`（函数在 `desform_lowapp_utils`，不要打开 `desform-lowapp.md`）。

工作表：Write `job.json` → `create_linked_worksheets.py`（字段写法见 `fast-create.md`，**不要**打开 json-config）。公式修正 / link-field 关联带出 / 流水号规则 / 隐藏键的补丁契约全在 `fast-create.md`「建后补丁契约速查」一张表，随取随用。

- `forms[].code` 必须全局唯一：自带短后缀（如日期），禁止探 `get_form_id`。
- `forms[].fields` + `titleIndex` 直接写；radio `options` 数组、`required`/`defaultValue` 可写。
- 多表互指关联：**先不写 `link`**，表建完走 ③。单条一对一才用 `link`。
- 表建完 `get_menus` + `move_worksheet_to_group(menu_id, group_id)`。

## ③ 双向关联（`add_link_record.py`）

job **必须** `tenantName` + `appName`（`target` 同样要 `appName`+`worksheet`）。**不要只写 `tenantId`/`appId`** → 脚本报 `缺少应用`。

不同表可并行；**同一张表**的多个关联必须串行。

脚本不写 twoWay。两边字段都成功后，**同一脚本** `get_form_fields` 一次 + 两边 `update_widget(..., {"options":{"twoWayModel": 对方 model}}, key=本方 key)`。不要停下来告知「v1 不支持」。

⚠️ **`showFields`（显示字段）要主动给**：不传即落 `[]`，关联卡片/明细表里只显示标题一列，用户会当成「字段没勾上」（2026-09-16 实测反馈「显示字段 提示词里面没有，导致没有勾选」）。需求没写就按业务取 2~6 个关键列，或直接问一句。写法与判据 → `fast-add-link-record.md` 的 `showFields` 行。

## ④ 简流（只 import `miniflow_creator`，禁止打开 node-types / 入库审批示例）

同一 `.py`：`fetch_app_forms` + `fetch_form_fields` 解析中文名 → `build_process_json` → save → deploy。全程 py ≤2 次。

> ⚠️ **建 `edit`（填写）节点必须写 `content`**（= 填写人**显示名**，如 `'直接上级'`），否则设计器卡片显示灰色的「**设置这个节点**」未配置占位，用户会以为流程没建好。界面自己拼「填写人：」前缀，落库只放显示名；手建的节点设计器会自动写这个字段，脚本建的不会（2026-09-15 实测，用户指出「手动的就没有」）。
> **显示名 ≠ 表达式原文**：填写人是表单字段就写字段中文名；填写人是表达式/内置解析（`assigneeByExp`+`${applyUserId}` 等）要写**语义名**（`'获取发起人'`，即同节点 `approverGroups[0].expressionsNames[0]`）；角色/岗位/部门写对应名称。把 `assigneeByExp(${applyUserId})` 原样塞进 content，画布卡片会把这段代码直接显示出来（2026-09-16 用户指着卡片纠正「这里应该是 获取发起人」，已自愈重发）。收尾回读断言 content 非空且**不含 `$`、不含 `assigneeBy`**。

同轮要建 **≥3 条流程：直接跑 `../../jeecg-lowcode-miniflow/scripts/build_flows.py`**，
不要在对话里逐条拼 `processJson`。它吃一个声明式 `flows.py`（用 `flow_dsl` 写，
字段/表名一律中文，引擎自己换 code/model）：

```python
from flow_dsl import *
FLOWS = [
    flow("巡检计划-审批", "巡检计划", on="新增", nodes=[
        approve(name="主管审批", users=["admin"], mode=1),
    ]),
]
```
```bash
python "<miniflow>/scripts/build_flows.py" --api-base URL --token TOKEN \
  --tenant-id N --app-id A --spec flows.py
```

> ⚠️ **重跑失败项必须带 `--only`**（2026-09-17 实测）：`--update` 是**无条件全量重存+重发布**，
> 63 条流程实测 **234s**，而且**什么都不改也一样跑满**。只改了几条却整批重发 =
> 每次返工白烧 4 分钟。重跑时把 `FAIL:` 行里的流程名抄进 `--only`，被点名主流程
> 引用到的子流程会**自动带上**：
> ```bash
> python ".../build_flows.py" ... --spec flows.py --update --only "调拨-其他出库单,销售换货"
> # → OK:only 只处理 2 条（点名 1 + 依赖子流程 1）…… 8.6s   （对比全量 234s）
> ```
> 流程名写错会当场 `SystemExit` 列出，不会静默少建。

> ⚠️ 这里**曾经是一条死链**：老版本写「先读 `create-flow.md`『批量建流程』节」——
> 那份文档讲的是单条流程怎么拼 `processJson`，**从来没有指向批量引擎**。
> 结果是几十条流程那轮跑了 **55 分钟 0 产出**（逐条拼、撞 32000 输出上限）。
> `build_flows.py` 现在一次 50+ 条实测 **51 秒**。别再逐条拼。

骨架抄 `create-flow.md`：

| 需求 | 组合 |
|------|------|
| 有则更新 / 无则新增 | **D** |
| 按钮改当前行 | **E**（buttonEvent 的 `attr.formTableId=None`；save 前自愈 `updateFields`） |
| 审批通过后按关联多条逐行改库存 | **F**（主流程 opinion + 子流程 D；getType=3 外科重写内嵌在 F，勿开 node-types） |

子流程：三层 `startType=subEvent`；save 后 `register_subprocess_id`；再按 create-flow **#47** 补 `customProcessId=<DBid>` 保存并 deploy；`/act/process/list` 有 key=`process<DBid>` 才建父流程。

审批人：username/realname **精确**匹配点名 → 角色用 **roleName** 精确匹配 → 否则 `candidateUser` + `admin` + 该用户 `realname`。禁止把 `roleCode=admin`（超管角色）当成「管理员」。

> ⚠️ **审批组四种形态写错都是静默故障**（save/deploy 全绿、实例照起，**只是任务没人收到**，2026-09-16 用户实测报障）：① 指定成员 = `candidateUser`（单数）+ `approverIds:[**裸账号**]`（**不带 `user.` 前缀**，那是消息节点 `toUserIds` 的写法）；② 发起人 = `candidateUser` + `assigneeByExp`；③ 办理人=表单**用户**字段 = `candidateUsers`（**复数**）+ `assigneeByVariable`；④ 办理人=表单**部门**字段 = 同上 **再加 `variableContent[].isNeedTranslateToUserIds: true`**（缺它部门不展开成用户 → 部门成员全收不到）。
> 验收判据只有一条：`/act/task/myTodo` 里任务是否出现在**该办理人**的待办（`/act/task/list` 的 `taskAssigneeId` 对表单字段类不回填，不能当判据）。最稳 = **正反例对照**：同一部门字段选「该用户所属部门」应出现、选「其不在的部门」应不出现，一次排除"兜底给发起人/管理员"的假阳性。详见 miniflow `gotchas #90`。

## ⑤ 自定义按钮

`desform_custom_button.py --config`：`clickThen=confirm` + `flowStatus=true` + `conditionsGroup`（字段中文名）。先有真实简流 `flow_id`，再 `action=update` 把 `processId` 换成它。不要等 y/n。

## ⑥ 仪表盘（敲敲云盘，禁止积木/大屏/门户）

`PYTHONIOENCODING=utf-8` + `PYTHONPATH=<dashboard/references>:<.../scripts>`。

同壳串行：`create-page --group 点名分组 --name 看板名` → 按表 `add-charts --form-code --specs-file` → `add-buttons` → 跨表则**每表一次** `add-filter --specs-file`（**禁止**给 add-filter 传 `--form-code` / `--form-name`）。

- 关联维写中文名；按日 `dateGroup:"3"`；本月 `queryRange:"month"`；饼 `percentLabel:true`。
- 透视 `charts` 匹配「表格」或 componentName。
- 4 个 KPI 同行各 `w:6`；半行图 `w:12 h:32`。
- specs 用 Write / `json.dump` 无 BOM；成功立刻删临时 JSON。

## ④ 灌数（**排在简流之前**；并发 + 后台，勿逐条串行干等）

**用 `scripts/mock_data_fill.py`**，它是**规格驱动**的，不是「改顶部 FIELDS 即跑」的模板：

```bash
python "<lowapp>/scripts/mock_data_fill.py" --api-base URL --token TOKEN \
  --tenant-id N --app-id A --spec app_spec.json --rows 3
```

两遍灌，顺序不能反：① 先灌所有表的**标量**（文本/金额/数字/日期/选项），
② 再灌**关联记录**（单条→随机挑一条目标表记录；多条→挑 K 条回填 id 数组）。
汇总字段的值来自子记录，所以必须先有 ② 才有数。

**执行默认：写数据串行跑**（`WORKERS = 1`）。2026-09-16 实测推翻了原先「并发 8~16」的写法：

| 方式 | 每次写入 | 依据 |
|---|---|---|
| **串行** | **0.044s** | 25 次：0.09 + 23×0.04 + 0.05 |
| 4 并发 | 0.065s | 48 次 / 3.1s |

服务端把并发写全序列化了 —— **加并发换不来吞吐，只换来争用开销**，而连接池只有 20。
8 并发实测把池子占干 → `CannotCreateTransactionException: Could not open JDBC Connection
for transaction` → 请求积压 → **后端进程直接倒下**。串行在这台环境下是又快又稳那一侧。

`get_form_fields` 取字段（纯读，单次 4~5.6s）**另给 4 并发**：52 张表串行要 4.3 分钟，
那才是灌数「看起来卡住」的真正原因。读不占事务，风险与写不同，所以两者不用同一个数。

灌数 Bash 用 `run_in_background: true`，**与绑图/看板并行**——盘只依赖表单结构、不依赖行数据
（页面打开实时查数），灌数不是绑图前置。完成后 TaskOutput 收结果。

**数据量分级**：≤50 条 → 并发 `add_data`；50~1000+ 条 → 1 次整批 `POST /desform/data/importXls/{desformCode}`；直连 SQL 仅纯演示且用户授权才用。

`get_form_fields` → `add_data`。关联记录：id **数组** + `model_dictTextPrint`。radio/select 固定值=选项文案。date 按 timestamp 写毫秒 + `_dictText`。

**键一律用 model（`fields[中文名]['model']`）**：写中文字段名会**静默入库**——`list_data` 看得见值、界面**整列显示空**（2026-09-11 仁和医院「科室信息」10 条全空实踩，详见 `desform-data-utils.md` 开头 ⚠️）。灌完**按 model 键抽样回读**，只数行数查不出来。

**`add_data` 会触发 tableEvent 主流程 —— 这不是「属预期」就完事了，它是级联写的入口。**
流程建好后每写一行都可能拖动几十次下游写。所以灌数**必须在流程之前**（见文首 ⚠️）。
若应用里已经有流程，`build_app.py` 会拦住；手工单独跑时自己确认清楚。

改状态：**不要** `batch_update`（常报「参数缺失」）→ `list_data` 取 `desformData` 再
`edit_data` 整单合并。**`edit_data` 是全量覆盖**，只传要改的字段会把该行其余字段清空。

---

## ⑧ 交付闸门（每段回读计数，缺口必须报出来）

收尾前逐项回读，**不要只看脚本自己报的「成功」**：

| 项 | 怎么读 | 判定 |
|---|---|---|
| 分组 / 表单 / 看板 | `get_menus(app_id).menuList` 按 `type` 分组计数 | 与规格一致 |
| 字典 | `/sys/dict/getDictListByLowAppId` | 22 条 |
| 流程 | `/act/process/extActProcess/listProcess`，按 `openStatus`+`processStatus` 均为 1 过滤 | 全部启用 |
| **流程节点契约** | **跑 `jeecg-lowcode-miniflow/scripts/check_node_contract.py`** | **违例 0 条** |
| **表单布局** | 每张表回读 design，数 `divider` 与 `card` 子字段数 | 有分节、每卡 ≤3 字段 |
| 数据 | `list_data(code,1,2)`，值在 **`record['desformData']`** 里 | 非空 |

⚠️ **「流程全部启用」这一行不能单独用**。2026-09-17 实测：63 条流程全绿、全部启用，
但节点键一条都没发对（`data_add` 发的 `addFields` 引擎不认、`get_more` 没发 `selectType=3`、
`callActivity` 缺数据对象），应用整体不可用。
**计数对得上 ≠ 配置发对了**，必须再跑一次节点契约校验。

`build_app.py` 每段都会打 `[N/7 阶段] 期望 X / 实际 Y`，有缺口立即非零退出。
**静默通过是最坏的结果** —— 曾经有一次 app-id 写错、一张表都没读到，却报「补丁全部落地，
无缺口」并以 0 退出（`patch_fields.py` 的 `load_gaps` / `SystemExit(5)` 就是为堵这个）。

---

## 失败立刻改参短跑（不要再读文档）

| 现象 | 立刻做 |
|------|--------|
| `缺少应用` | job 补 `tenantName`+`appName`，去掉仅 ID 写法 |
| `unrecognized arguments: --form-code` | add-filter 删 `--form-code`/`--form-name` |
| `batch_update` 参数缺失 | 改 `edit_data` |
| save 500 Duplicate key | `startTaskId` 不要等于任何节点 id |
| deploy 成功但 callActivity 找不到定义 | 子流程补 `customProcessId` 再 deploy（组合 F / #47） |
| 编码已存在 / `[阻止]` | 换带日期后缀的 code，不要探 8 次 `get_form_id` |
