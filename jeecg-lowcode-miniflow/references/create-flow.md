# 新建整条简流

仅当用户要**新建**流程时读本文。改已有流程只看 `SKILL.md`「修改已有简流」，不要打开本文件。

脚本：`<skill_base_dir>\scripts\miniflow_creator.py`  
Windows 用 `py -3` 跑脚本。含中文节点名时写成临时 `.py` 再执行，不要 `python -c`。

---

## 前置参数

| 参数 | 说明 | 示例 |
|------|------|------|
| API 地址 | JeecgBoot 后端 | `http://localhost:8080/jeecgboot` |
| X-Access-Token | JWT | 本轮消息或本会话已有值 |
| X-Tenant-Id | 租户 ID | 未知时 `save_flow` 会从 getUserInfo 补 |
| lowAppId | 所属低代码应用 ID | 必须有 |
| 流程名称 | 简流名称 | `订单申请` |
| startType | 触发方式 | 见下表 |

凭证规则见 `SKILL.md`「凭证」，不要全盘搜、不要翻其他 skill。

**startType：**

| 值 | 说明 | 额外参数 |
|----|------|---------|
| `tableEvent` | 工作表新增/更新/删除时触发 | formTableCode/Name/Id/titleField/startEventType |
| `manual` | 用户主动发起 | 无 |
| `buttonEvent` | 工作表自定义按钮触发 | 同 tableEvent，另需创建 Desform 按钮 |
| `timerEvent` | 定时触发 | beginDateStr/timeCycleName/endDateStr |
| `dateFieldEvent` | 日期字段到期 | triggerField/executeType/plusDate |
| `userEvent` | 人员入职/离职 | formTableList 固定结构 |
| `subEvent` | 被 callActivity 调用的子流程 | `subFormTableObject` 必填 |

触发参数细节 → `trigger-types.md` 对应节，不要读全文。

**tableEvent / buttonEvent 额外：**

| 参数 | 说明 |
|------|------|
| formTableCode | Desform 表单编码 |
| formTableName | 表单名称 |
| formTableId | ⚠️ 仅 **tableEvent** 传 `form_start_{formTableCode}`；**buttonEvent 不传**（builder 会按 config 原样写入 attr，而 UI 原生 buttonEvent 的 attr.formTableId 实测必须为 null；传了必多一次修正轮） |
| titleField | 标题字段 model |
| startEventType | `add` / `update` / `add\|update` / `delete` |

`createStartNode`（是否启用「发起人节点」）：**默认 `False`，不要写 `True`**（builder 默认即 False）。仅当用户**明确点名**要「发起人节点 / 发起人填写 / 启用发起人节点」时，才在 config 里传 `"createStartNode": True`。⚠️ 旧文档「`add` 触发必须 true」已于 2026-09-11 作废（线上同为本 skill 建的 add 触发流程，true/false 都存在且都正常跑）。  
`conditionFields` 必须是字段 model **字符串数组**，不能是对象数组。

**subEvent 三层（2026-09-03 傍晚 4建 实证更正，必须以本段为准）：**

1. `config.startType = "subEvent"`（API 层）
2. processJson **根节点** `startType` 也必须是 `"subEvent"`（⚠️ 早期版本要求 manual 的结论已过时：根层 manual 会让引擎生成的 XML 缺 MiniSubProcessStartListener 注入 → 运行时父行变量全空、条件变 `_id:""`、子流程空跑，且 UI 发布会**按根层现值**原样保存，手动改不回来；4建 全链路验证 = 三层全 subEvent）
3. `attr.startType` 同样为 `"subEvent"`；`attr.subFormTableObject` 必填（主流程 `data_get_more` 节点引用，含 `isSubStart:true`）

> **⚠️ subEvent 发布必读（5建 19:03 实证更正，免 UI 点击）：** 三层 JSON 就位且记录 processKey=`process<DBid>` 后，发布唯一缺的是**记录 customProcessId 字段**——API deploy 每次都注册，但 key 按 `'process'+customProcessId` 拼接，该字段空则注册出坏 key（`process`/`processnull`）导致 callActivity 查不到。**补一次设计器式保存再 PUT 即可全 API 自动注册：** `POST /act/designer/miniDesFlow/api/saveFlow`（Content-Type=x-www-form-urlencoded 表单，参数含 updateCount/processJson/processName/processKey=process<DBid>/processType=oa/id/**customProcessId=<DBid>**/lowAppId/startType=subEvent，tenantId 走 X-Tenant-Id 头）→ `PUT /act/process/extActProcess/deployProcess {"id":<DBid>}`（无需 X-Sign 等签名头）→ 校验 `/act/process/list` 出现 key=`process<DBid>` version≥1。历史结论"必须 UI 保存并发布 / #33a 带头 PUT"为当时表象，机理见 `gotchas.md` #47。三层 subEvent（#31）与 XML 监听器注入（#45）是与本条独立的另一维，仍须满足。

踩坑细节 → `gotchas.md` 搜 subEvent / callActivity。

> **⚠️ 手工拼子流程 JSON 的渲染键清单（2026-09-04 实证，防"无＋加节点标识"）：** subEvent 子流程常需手工构造 JSON（builder 对普通流程会自动补齐渲染键，手搭不会）。**start 根节点与每一个手拼节点**（data_add/data_get_*/callActivity 等）都必须带五个渲染键，否则设计器无"＋"、无法删除：
> ```python
> # start 根节点（控制首节点上方的＋）：
> start_node.update({'addable': True, 'deletable': False, 'content': '发起流程',
>                    'error': False, 'errorContent': '', 'status': -1})
> # 普通节点（data_add 单条/链中节点）：
> node.update({'addable': True, 'deletable': False,
>              'content': '工作表 "目标表单名"', 'error': False, 'errorContent': ''})
> ```
> 仅「批量新增(addDataType=2)且确定不再挂后续」的终点才省略 addable；单条 data_add 终点也保留 `addable=True`。详见 gotchas #39（2026-09-04 修正段）。

---

## 节点类型速查

`config.nodes` 用脚本别名。写成 processJson 内部类型会抛 ValueError。

| config.nodes 类型 | processJson 类型 | 说明 |
|---|---|---|
| `approver` | `approver` | 审批 |
| `edit` | `edit` | 表单编辑 |
| `exclusive` | `exclusive` | 排他网关 |
| `data_update` | `data_update` | 更新记录 |
| `parallel` | `parallel` | 并行分支 |
| `inclusive` | `inclusive` | 包含分支 |
| `time` | `timer_event` | 延迟（config 必须用 `time`） |
| `notice` | `message_*` | 通知，用 `noticeType` 区分 |
| `data_add` | `data_add` | 添加记录 |
| `data_delete` | `data_delete` | 删除记录 |
| `upvariable` | `data_update_variable` | 更新流程参数 |
| `get_one` | `data_get_one` | 获取单条 |
| `get_more` | `data_get_more` | 获取多条 |
| `get_one_sysinfo` | `data_get_udr_one` | 获取单个人员/部门/角色 |
| `get_more_sysinfo` | `data_get_udr_more` | 获取多个人员/部门/角色 |
| `opinion` | `suggest` | 意见分支 |
| `data_branch` | `databranch` | 数据判断（config 必须用 `data_branch`） |
| `operation` | `function` | 运算（config 必须用 `operation`） |
| `subprocess` | `callActivity` | 子流程 |
| `service` | `service` | 服务任务 |
| `script` | `script` | 脚本 |

> ⚠️ **exclusive 两个建流级大坑（2026-09-11 实测返工，必读）：**
> 1. **自定义表达式条件有运行时作用域**：`${字段model} 运算符 值` 只在 **tableEvent 触发且引用起始行字段**时可用（起始行字段会注入为 EL 变量）。**buttonEvent 按钮触发、get_one 检索结果字段不注入 EL 变量**——运行时网关报 `Unknown property used in expression: ${xxx}`、流程卡死，而 save/deploy 全绿。这两种场景的分支条件必须用**字段条件组**（branchType 1 + conditionGroup + branchForm 指向 start/检索节点；检索字段比较用 queryItems 的 val=变量对象 valueType 3 + valType variable，见 node-types 4.4.1/4.5、trigger-types val 变量形态）。用户点名「自定义表达式」且触发是 buttonEvent 时也要说明此限制。
> 2. **网关后的合并链（exclusive 的 childNode）builder 静默丢弃**：config 里把「分支后汇合的节点」（如 分支后审批、最终改状态）写在 exclusive 的 `childNode` 上，`build_process_json` **不保留**——save/deploy/回读全绿，但节点根本没落库，流程跑完分支就断。正确姿势：新建时不依赖网关 childNode，建后按 SKILL.md「修改已有简流」把合并链挂到落库 JSON 的 `exclusive.childNode`（新节点 pid=网关 id；approver/data_update 完整结构照抄同应用已有流程 query_flow 取模板，updateFields 完整写进 attr；「新建回查」必查网关 childNode 是否 null）。

扩展节点需手动构建 JSON：`approve_result`、`api`、`aiOrchestration`、`message_*`。其中 **`api`（HTTP 调用）与 `aiOrchestration`（调用 AI 编排流程）的完整 attr 契约与构造示例见 `miniflow-node-types.md` 二十六 / 二十七节**；`approve_result` / `message_*` 见对应示例文件。禁用类型（抄送 `copy` 等）见二十七节之后的「二十八、不可用 / 占位节点类型」。

> **⚠️ 分支类型消歧（2026-09-10「全控件表单」误建返工）：** 用户口中的「**包含分支 / 包容分支**」= `inclusive`（**不是**动词「包含」+「分支」；「包含分支审批」要读成「包含分支 + 审批节点」）、「**互斥 / 排他分支**」= `exclusive`、「**并行分支**」= `parallel`——出现这些词一律**先按节点名解释**。用户只说「分支」而没点名类型时，建流前用 `AskUserQuestion` 让用户在 **互斥 / 包含 / 并行** 三选一，**禁止默认按互斥建**（提问预算 ≤1 次时，这一次优先给"分支类型"，不要花在粒度/审批人等可推断项上）。`inclusive` 三条硬约束：① 条件必须 `conditionGroup` 格式，且条件节点同级要带 `branchForm`+`formTableCode`（gotchas #12）；② **不得用 `isDefault` 兜底分支**，每条分支都要有明确条件；③ 聚合节点 `inclusive_end` 由 `build_process_json` 自动生成，**禁止手工插入**（gotchas #13）。④ **「表单内每个组件一条分支」类需求，条件规则必须按控件族分流**：范围查询只属**日期 / 时间 / 数值**族；文本 `input`/`textarea` 与公式 `formula` **无「在范围内」**（用等于/不等于/模糊/空值类），文件 `file-upload` **仅 为空 / 不为空**——整表统一铺一种规则会写出该控件下拉里不存在的项：**服务端不校验**，save/deploy/回读全绿，只有人打开设计器才看到（下拉无该项、值框渲染异常）。规则表见 `miniflow-node-types.md` 二十节，踩坑记录见 gotchas #85。结构细节只读 `miniflow-node-types.md` 六节。

> **⚠️ 流程里含 get_one / get_more 时：save 前必做三条自愈**——补 `attr.formTableId`（builder 落 null）、删 `attr.limitNum`（写 0 会被设计器显示成「限制数量 1」）、`formTableList` 兜底按 `nodeId` 单键判重。三条的写法与实证见 `SKILL.md`「修改已有简流」get_more 段末（不要为此另开探查轮）。

> **⚠️ 二次 save / 修复重发必带 lowAppId（实测静默清空事故）：** 对已存在的流程再次 save（修复节点、改分支、重发等）时，后端用请求里的 `lowAppId` **原样覆盖**数据库字段——config 是重新拼的、lowAppId 留了空/占位即被清成空串：**流程不删、引擎照跑、save/deploy/回读全绿，只在应用简流列表里消失**（按 `extActProcess/list?lowAppId=` 查不到）。重发前必须 `query_flow` 从记录回取 `rec['lowAppId']` 填进 config（同「修改已有简流」铁律），**禁止**沿用首轮记忆的 id 之外再留空；批建多流程收尾时按 `lowAppId` 过滤列一次流程核对条数（期望=主流程+子流程总数），缺的逐条 queryById 查 `lowAppId` 是否为空并补 save（urlencoded 带 lowAppId）+ 重发。

节点字段优先用本文「常用节点组合」。组合不够时才 `grep -n "^## .*（<类型>）"` 定位 `miniflow-node-types.md` 后只读该节（标题括号是「别名 / processJson 类型」双标签，例如 `（get_one / data_get_one）`，两种词都能命中）；用 grep 输出的标题行号做 `Read offset/limit` 切片，禁止整文件 Read。若 Read 返回了全文，只用目标节并立刻执行。

---

## 执行步骤

### 1. 解析需求

流程名称、触发方式、关联表单、节点列表。缺必填则问用户。

### 2. processKey 与节点 ID

```python
import time
ts = int(time.time() * 1000)
process_key = f"process{ts}"
start_task_id = f"task{ts}000"   # 仅给 startTaskId，禁止给任何节点
# 节点：task{ts}001、Gateway{ts}002、flow{ts}003 … 禁止 gen_id()
```

`startTaskId` 必须与所有节点 ID 都不同。写成第一个 childNode 的 ID → save 500 `Duplicate key`。

### 3. 前置查询 + 创建 + 发布（同一脚本一次跑完）

需要 userId / deptId / roleId / formTableCode / titleField / 字段 model 时，全部写进同一个 `.py`，不要分多次、不要开 Agent、不要先探查再创建。

```python
# 1) GET /sys/user/getUserInfo → result.userInfo.loginTenantId
# 2) GET /online/lowApp/miniflow/tenantAppFormList?tenantId=  （应用+工作表+titleField）
# 3) 仅当需要字段 model：GET /desform/api/fields/<formCode>?group=true
#    中文名在 fields[].name，result 是 dict 不是 list
# 1)-3) 可换用 miniflow_creator 内置 fetch_app_forms / fetch_form_fields 一行拿到紧凑结构
#    （见「结构未知：自适应一步流」，推荐，省解析代码且输出小）
# 4) 需要角色时：GET /sys/role/list?pageSize=100
# 然后立刻 build_process_json → save_flow → deploy_flow
```

完整 API → `api-reference.md`。

```python
import sys, time
sys.path.insert(0, r'<skill_base_dir>\scripts')
from miniflow_creator import build_process_json, save_flow, deploy_flow

ts = int(time.time() * 1000)
config = {
    "processName": "流程名称",
    "processKey": f"process{ts}",
    "processType": "oa",
    "lowAppId": "<lowAppId>",
    "tenantId": "<loginTenantId>",
    "startType": "tableEvent",
    "formTableCode": "<code>",
    "formTableName": "<name>",
    "formTableId": "form_start_<code>",
    "titleField": "<fieldModel>",
    "startEventType": "add",
    "startTaskId": f"task{ts}000",
    "nodes": [
        # 抄本文「常用节点组合」，不要为此打开 node-types
    ]
}

process_json = build_process_json(config)  # 只接受单个 dict
# createStartNode 不补：默认 False=不启用发起人节点；用户点名要发起人节点时才在 config 里传 "createStartNode": True
result = save_flow(api_base, token, config, process_json)
if result.get('success'):
    flow_id = result['result']['id']
    deploy_flow(api_base, token, flow_id)
```

`save_flow` 读 `config["processName"]` / `config["processKey"]`，不要写成 `name`/`key`。
`save_flow` 之后立刻 `deploy_flow`。调试阶段可先只 save。

### 4. 输出

流程 ID、名称、Key、操作类型（新建）、updateCount、发布状态。

---

## 结构未知：自适应一步流（新建的第一选择）

用户只给了**应用名 + 业务描述**（最常见），没给 formTableCode / titleField / 字段 model 时，
**不要**分多轮探查——"先打印结构 → 人看 → 再写创建脚本"每多一轮中间回合就多几十秒。
把发现写进同一个脚本：按应用名定位表单、按中文名/type 自动解析 model，一次 `py -3` 跑完。
（新建任务全程 py 执行 ≤2 次，理想 1 次。）

```python
import sys, time
sys.path.insert(0, r'<skill_base_dir>\scripts')
from miniflow_creator import (fetch_app_forms, fetch_form_fields,
                              build_process_json, save_flow, deploy_flow)

# ① 应用两级结构一次拿全（apps[].forms[] 含 code/name/titleField）；tenant_id 可留空自动解析
#    ⚠️ app 自身键：id=lowAppId（响应 {id,name,forms}，无 lowAppId/appId 键）；防呆只断言「存在」，
#    禁止拿记忆快照里的 id 做相等断言——运行时返回才是唯一事实源（gotchas #76）
apps = fetch_app_forms(api_base, token, tenant_id)
order_f = next(f for a in apps if a['name'] == '目标应用'
                 for f in a['forms'] if f['name'] == '订单管理')   # 触发表单（应用名/表单名换成目标环境实际名称）
cust_f  = next(f for a in apps if a['name'] == '目标应用'
                 for f in a['forms'] if f['name'] == '客户管理')   # 目标表单

# ② 字段按中文名取 model：返回 {中文名: {'model','type','options'}}
#    link-record 的 options = {'sourceCode','titleField'}；select/radio 的 options = [可选值]
fo = fetch_form_fields(api_base, token, order_f['code'], tenant_id)
fc = fetch_form_fields(api_base, token, cust_f['code'],  tenant_id)
# 按语义定位，禁止手写死 model（表单重建后 model 会变）：
link_cust = next(m for m in fo.values()
                 if m['type'] == 'link-record'
                 and m['options'].get('sourceCode') == cust_f['code'])   # 触发表→目标表 的关联字段
status    = next(m for m in fc.values()
                 if m['type'] == 'radio' and '成交客户' in (m['options'] or []))  # 状态字段
name_field = fc['客户名称']               # 中文名直取
# titleField 用 ① 的 form['titleField']，不要拿字段名猜

# ③ 节点骨架抄「常用节点组合」（本需求=组合 D），model / formTableCode / titleField 全部用上面解析值，
#    同一脚本内直接 build → save → deploy，不在脚本之间看输出
ts = int(time.time() * 1000)
config = {
    # ...结构同「执行步骤 3」示例；此处 formTableCode=order_f['code']、titleField=order_f['titleField']、
    #    nodes 里的字段 model = link_cust['model'] / name_field['model'] / status['model'] 等解析值
}
process_json = build_process_json(config)
# 不要补 createStartNode：默认 False=不启用发起人节点（用户点名要发起人节点时才在 config 传 True）
result = save_flow(api_base, token, config, process_json)
if result.get('success'):
    deploy_flow(api_base, token, result['result']['id'])
```

规则：

- 探查打印只是脚本内的 debug 回声，**一次给全**：应用两级列表、字段 `{中文名: model/type/可选值}`。
  禁止用摘要/裁剪函数把结构藏起来——藏了必然再开一轮探查。
- 确需人看输出才能定节点时：至多 1 次探查 + 1 次创建，探查后的下一个脚本必须完成创建。
- `fetch_app_forms` / `fetch_form_fields` 是 `miniflow_creator.py` 内置只读函数，失败时打印
  `[warn]` 并返回空结构，不会中断一步流脚本。

---

## 批量建流程（一次建多条时的提速约定）

同轮要建 ≥3 条流程时，按本节执行；否则按上文普通流程走。

**1. 结构探查一次做完全员共享。** 主会话先跑一个探查脚本：`fetch_app_forms` + 涉及各表 `fetch_form_fields`，把 `{表code: {字段中文名: {model,type,options}}}` dump 成 JSON 放 `{tmpdir}/jeecg-desform/`（如 `probe_<应用名>.json`）。各流程脚本直接读文件取 model，**禁止**每条流程重复 fetch；跨进程（子代理）无法复用会话缓存，共享文件是唯一的复用通道。

**2. 代理拆分：一代理 ≤2 条流程；预估 >15 节点的流程独占一个代理。** 简单流程（按钮改当前行、单 get_one+data_update、删除触发记录）模板内嵌 prompt，代理零文档阅读；只有大流代理才允许 grep node-types。

**3. save 前自愈硬清单（首轮 build 后逐项过，禁止踩坑后才补）：**
   - buttonEvent：`pj['attr']['formTableId']=None`
   - data_update：完整 `updateFields` 注入 `attr`（只增键不整块替换，attr 里已有 expressionType/expressionValue）；⚠️ **val 为空串 `''` 的条目首次 create 会被服务端静默丢弃**（save success、回读才暴露），「清空字段」类条目须 create 后带 flow_id 二次 save 再 deploy 才持久化（实测）
   - get_one/get_more：补 `attr.formTableId=f'form_{节点id}_{表code}'`、删 `limitNum`；get_more 批量更新还须 `formTableSourceGetDataType=1` 且 formTableId 指向**源** getMore
   - 分支条件：buttonEvent/get_one 结果字段**不进自定义 EL**，用字段条件组（branchType 1 + branchForm 指向 start/search 节点）
   - 运算节点：builder 会把无 formula 的运算登记成 function-number，手拼 fun 节点用 `FunBuilder`（见下）保证 function-fun 登记正确
   - **edit（填写）节点：填写人=表单字段时 `variableTitle` 必须写字段中文名**（面板「指定填写对象」的唯一显示来源；只写 `variableContent` → 画布卡片正常但面板为空，2026-09-16 用户实测「员工考勤确认 没有值」）。`build_approver_group` 已自动从 `variableContent[0].fieldLabel` 派生、`_get_approver_content` 也已纳入，**正常走 builder 无需手写**；只有手改已有流程 JSON 时要显式补 `variableTitle`
   - **edit（填写）节点 + approver（审批）节点都要写 `content`（办理人显示名）**——⚠️ **两类节点同病**：`content` 为空时画布卡片都渲染成灰色「设置这个节点」，用户会当成「人员没了」。**审批节点别以为 builder 会自动填**：`assigneeByName`（点名到人）会，**`assigneeByVariable`（办理人=表单字段）不会**（2026-09-16 实测：4 个审批节点全空，而 edit 的同类节点因先修过而正常）。（界面自己拼「填写人：」前缀，落库不写前缀、不写节点名）。取值口径：绑定表单字段 → 字段中文名（`'直接上级'`/`'部门主管审批人'`/`'姓名'`）；表达式/内置解析（`assigneeByExp` 等）→ **语义名**（`${applyUserId}` → `'获取发起人'`）；角色/岗位/部门 → 对应名称。⚠️ **禁止把表达式原文写进 content**（写成 `'assigneeByExp(${applyUserId})'` 时画布卡片原样显示这串代码，2026-09-16 用户实测指着卡片纠正「这里应该是 获取发起人」；正确值就在同节点 `approverGroups[0].expressionsNames[0]`，自愈直接取它）。整单自愈：`query_flow` → 改 `childNode.content` → `save_flow(flow_id=, update_count=)` → `deploy_flow`
     > ⚠️ **2026-09-16 30 表批建补充：builder 清空 `content` 不止「写成表达式原文」一种情形。** 办理人 = **表单字段**（`assigneeByVariable`）时，config 里写好的 `content` 会被 `build_process_json` **直接丢成空串**（同批里 `assigneeByExp` 的 content 却保留，所以只查一两节点看不出规律）；save/deploy 全绿、check_app_flows 也过，只有回读 processJson 才看到卡片是灰的「设置这个节点」。
     > **自愈位置：`build_process_json` 之后、`save_flow` 之前**（改 config 无效，builder 会再清一次）。做法：walk pj 取所有 **`type in ('edit','approver')`** 节点（⚠️ 只取 `'edit'` 会漏掉审批节点——2026-09-16 就是这么漏的），`content` 为空 / 含 `$` / 含 `assigneeBy` 时按办理人来源回填，取第一个命中的：`approverNames[0]` → `expressionsNames[0]` → `variableContent[0].fieldLabel`（表单字段，即中文名）→ `roleNames[0]`/`deptNames[0]`/`postNames[0]`。收尾断言：**这两类节点全部** `content` 非空且**不含 `$`、不含 `assigneeBy`**。批建时这条断言要跑在**每条**流程上，不能只抽查。
     > **与 content 同批要自愈的第二个键：`variableTitle`。** 凡 `assigneeByVariable`（办理人=表单字段）的组，**必须写 `variableTitle: [字段中文名]`**（= `variableContent[0].fieldLabel`）；留空则**配置面板**的「指定填写对象」显示成空的「+ 添加人员」，而画布卡片 content 是正常的——两个键坏在不同界面，只修一个会以为已经好了（2026-09-16 实测：12 个「办理人=表单字段」节点**全部** variableTitle 为空——其中 8 个是 edit、4 个是 approver；注意别与「13 个 edit 节点」的字段权限数混淆，两个口径不同）。回读断言：walk 所有 `approverGroups`（顶层 + `attr` 两份），`assigneeType=='assigneeByVariable'` 的组 `variableTitle` 非空。
   - 收尾回读：逐节点打印 `name / type / content / assigneeType`，重点断言 content 非空且**不含 `$`、不含 `assigneeBy`**（防止表达式原文漏进卡片文案）；save 前可一行自愈 `fixes = miniflow_creator.fix_edit_contents(pj)`（把误写成表达式原文的 content 换回语义名，幂等，返回待修清单，非空才 save+deploy）
   - **edit 节点字段权限不在 processJson 里**：`privileges` 对简流无效，必须建完流程后调 `POST /act/process/extActProcessNodePermission/saveOrUpdateBatch`（每字段 ruleType=1显示+2编辑两条；默认是「显示+可编辑」，所以「其余只读」要把**该节点用到的每个字段都写行**）。批量建流程时这是**独立收尾步骤**，save/deploy 全绿不代表权限已设（2026-09-16 实测：13 个 edit 节点全漏）。契约与档位表见 `field-perm-rule.md`。
   - 重发/改已有流程：`lowAppId` 必须从 `query_flow` 记录回取（见 SKILL.md「修改已有简流」）

**4. 助手函数（`scripts/miniflow_helpers.py`，契约取自线上已发布流程实测）：**

```python
from miniflow_helpers import FunBuilder, du_var_function, publish_subflow, check_app_flows

# function(fun) 节点：text 拼接/IF 计算，不用再手搓 8 键 funContext + md5 + URL 编码
fb = FunBuilder()
p1 = fb.add_ref(field=m_名称, form_table_code=src_code, node_id=get_one_id,
                node_type='search', node_name='获取XX记录', table_text='XX表', field_text='名称')
expr = f"CONCAT({p1},'-',{p1})"
fn_node = fb.build(node_id=f'task{ts}010', name='拼接品名', expr=expr, level='2')
# data_update 引用其结果：
uf_val = du_var_function(fn_node['id'], fn_node['name'], field_type='input')

# subEvent 子流程发布：5 步配方（register→urlencoded saveFlow 补 customProcessId→PUT deploy→校验 key）一次调用
r = publish_subflow(api_base, token, low_app_id, 子flow_id, tenant_id)
assert r['ok'], r['messages']

# 批建收尾：按应用核对流程条数（防 lowAppId 静默丢失， missing 非空逐条 queryById 补）
chk = check_app_flows(api_base, token, low_app_id, tenant_id, expected_names=[...全部流程名...])
assert not chk['missing'], chk['missing']
```

**5. 收尾必查**：`check_app_flows` 的 missing 为空；子流程 `/act/process/list` 的 `key`（注意引擎列表键名是 `key` 不是 `processKey`）= `process<DBid>`。

---

## 常用节点组合

### A. opinion → 同意发通知 / 拒绝结束

`toUserIds` 必须在节点**顶层**（不在 attr 内）。

```python
{"type": "opinion", "name": "意见分支", "conditionNodes": [
    {
        "name": "同意",
        "nodes": [{
            "type": "notice",
            "name": "审批通知",
            "attr": {"noticeType": "system", "noticeTitle": "已通过"},
            "toUserIds": ["user.admin"],
            "toUserNames": ["admin"],
        }]
    },
    {"name": "拒绝", "nodes": []}
]}
```

**⚠️ 落库位置：`approverGroups` 两处都写同值——`attr.approverGroups`（界面面板处）+ 节点顶层 `approverGroups`（副本）；仅写一处会让另一处滞留旧值（2026-09-15 实证）。`isSequential`、`completionCondition`、`level`、`ratio`、`approvalMethod` 等一律落 **attr 内**，回读断言查 `attr.*`（节点顶层读必为 None）（2026-09-10 实证，gotchas #81）。**

### B. 并行会签（全员通过）

```python
{"type": "approver", "name": "会签", "approvalMode": 3,
 "attr": {"isSequential": False, "completionCondition": "${nrOfCompletedInstances/nrOfInstances==1}"},
 "approverGroups": [{"approverType": "candidateUsers", "assigneeType": "assigneeByName",
                     "approverIds": ["user01", "user02", "user03"],
                     "approverNames": ["user01", "user02", "user03"],
                     "levelMode": 1, "approverId": "", "approverName": "",
                     "deptIds": [], "roleIds": [], "postIds": [], "expressionsIds": []}]}
```

`candidateGroups` 时 `roleIds` 填 roleCode，且必须同时填 `roleNames`。

### C. timerEvent 每天 + get_more + 钉钉

必须设 `timeCycleName`（不能 null），否则 `attr.timeCycle="custom"`。

```python
config = {
    "processName": "每日提醒",
    "processKey": f"process{ts}",
    "processType": "oa",
    "lowAppId": "<lowAppId>",
    "startType": "timerEvent",
    "beginDateStr": "2026-05-01 08:00",
    "timeCycleName": "每天",
    "nodes": [
        {
            "type": "get_more",
            "name": "查询今日数据",
            "getType": 1,
            "formTableCode": "<表单编码>",
            "formTableName": "<表单名>",
            "conditions": [
                {"rule": "eq", "field": "status", "val": "待处理", "type": "string"}
            ],
            "fetchMode": "cache", "limitCount": 0,
        },
        {
            "type": "notice",
            "name": "发钉钉通知",
            "attr": {"noticeType": "dingding", "noticeTitle": "每日提醒", "noticeContent": "..."},
            "toUserIds": ["user.<username>"],
            "toUserNames": ["<username>"],
        }
    ]
}
```

get_more 字段说明见 `SKILL.md`「修改已有简流」内嵌 config（不要为此打开 `example/获取多条数据.md`）。

### D. 工作表新增：判断关联记录是否存在 → 有则更新 / 无则新增

触发表单用 link-record 选目标表记录时，get_one 条件必须匹配目标表 `_id`（存的是主键，不是名称）。`emptyAction=3` 后紧跟 `data_branch`。更新查到的记录时 `formTableSourceNodeType` 必须是 `"search"`。

> `data_branch` 两分支的 content（`${flow_has_data==1}` / `${flow_has_data==0}`）与 attr 由 `build_process_json` 自动生成，**第一支=有数据（查到）、第二支=无数据**，config 里只写分支名和 nodes，不要手写 content / branchType，也不要为此打开 node-types 求证。节点结构未知时（只知应用名/表单名）先读「结构未知：自适应一步流」。

```python
ts = int(time.time() * 1000)
get_one_id = f"task{ts}001"
config = {
    "processName": "订单管理新增简流",
    "processKey": f"process{ts}",
    "processType": "oa",
    "lowAppId": "<lowAppId>",
    "tenantId": "<loginTenantId>",
    "startType": "tableEvent",
    "formTableCode": "order_mgmt",
    "formTableName": "订单管理",
    "formTableId": "form_start_order_mgmt",
    "titleField": "<订单标题字段 model>",
    "startEventType": "add",
    "startTaskId": f"task{ts}000",
    "nodes": [
        {
            "type": "get_one", "id": get_one_id, "name": "查询客户是否存在",
            "getType": 1, "formTableCode": "customer_mgmt", "formTableName": "客户管理",
            "emptyAction": 3,
            "conditions": [{
                "rule": "eq", "ruleName": "等于", "valueType": 2,
                "val": {
                    "variableValue": "<订单.客户 link-record model>",
                    "formTableCode": "order_mgmt", "variableName": "客户",
                    "formNodeType": "table", "formNodeId": "start",
                    "formNodeName": "工作表事件触发",
                },
                "name": "记录id", "field": "_id", "columnName": "记录id",
                "type": "input", "valType": "variable",
            }],
        },
        {
            "type": "data_branch", "id": f"Gateway{ts}002", "name": "判断客户是否存在",
            "conditionNodes": [
                {"id": f"flow{ts}003", "name": "客户已存在", "nodes": [{
                    "type": "data_update", "id": f"task{ts}004",
                    "name": "将客户状态改为成交客户",
                    "formTableCode": "customer_mgmt", "formTableName": "客户管理",
                    "formTableSourceTaskId": get_one_id,
                    "attr": {"formTableSourceNodeType": "search"},
                    "updateFields": [{
                        "field": "<客户状态字段 model>", "val": "成交客户",
                        "fieldType": "radio", "type": "radio",
                    }],
                }]},
                {"id": f"flow{ts}005", "name": "客户不存在", "nodes": [{
                    "type": "data_add", "id": f"task{ts}006", "name": "创建客户",
                    "formTableCode": "customer_mgmt", "formTableName": "客户管理",
                    "formModel": {
                        "<客户名称字段 model>": {
                            "variableValue": "<订单.客户名称字段 model>",
                            "formTableCode": "order_mgmt", "variableName": "客户名称",
                            "fieldType": "input", "formNodeType": "table",
                            "formNodeId": "start", "formNodeName": "工作表事件触发",
                        },
                        "<客户状态字段 model>": "成交客户",   # ⚠️ radio/select 固定值=纯字符串选项文案（已验证）；funText 对象写法不会写入状态
                    },
                }]},
            ],
        },
    ],
}
```

subprocess 的 `customProcessId` 必须是数据库 ID：save 子流程后立刻 `register_subprocess_id`。见 `gotchas.md` callActivity。

### E. buttonEvent → data_update 更新当前行固定值（2026-09-04 实证）

最典型场景：表视图按钮「更新订单状态」→ 点击把当前行 select 字段置「已通过」。按钮本体 API（button/save flowStatus=true → button/update 换绑 flow_id）见 `api-reference.md`「Desform 自定义按钮 API」，本节只讲**流程侧 data_update**。

**坑（实证）**：updateFields 若写进 data_update 节点的 `attr` 交给 `build_process_json`，会被 builder 覆盖成 `null`，字段彻底丢失——save+deploy 后查 JSON 才发现。config 顶层写（同 D 组合写法）在既有流程可用，但 builder 内部行为不可依赖。**统一以「save 前自愈注入」为准**：

```python
ts = int(time.time() * 1000)
def walk_du(n, acc=None):
    acc = [] if acc is None else acc
    if not n: return acc
    if n.get('type') == 'data_update': acc.append(n)
    for ch in [n.get('childNode')] + list(n.get('conditionNodes') or []):
        walk_du(ch, acc)
    return acc

# ① config 顶层键描述节点（同 D：formTableCode/Name 必须给全；无成品可参照，按下方契约直接构造）
config = {**buttonEvent_start_keys,   # startType='buttonEvent', formTableCode/Name/titleField…
    'nodes': [{'type': 'data_update', 'id': f'task{ts}001', 'name': '更新订单状态',
               'formTableCode': dd.code, 'formTableName': dd.name,
               'formTableSourceTaskId': 'start',
               'attr': {'formTableSourceNodeType': 'table'},
               'updateFields': [{'field': status_model, 'val': '已通过',
                                 'fieldType': 'select', 'type': 'select'}]}]}
pj = build_process_json(config)
pj['attr']['formTableId'] = None   # ⚠️ buttonEvent：config 顶层不要带 formTableId（builder 原样写入 attr），此处必须置 null 与 UI 原生 buttonEvent 一致

# ③ 自愈：save 前把完整 updateFields 条目注入（字段 model/val 一律用脚本解析值，勿照抄参照）
for du in walk_du(pj):
    du['attr']['updateFields'] = [{
        'id': str(ts) + '9', 'optType': '1', 'fieldValue': '',
        'field': status_model, 'val': '已通过',       # radio/select 固定值=纯字符串文案（已验证）
        'fieldType': 'select', 'type': 'select',       # 按目标字段真实 type 填
    }]
    du['attr']['level'] = '1'                          # 紧跟 start 归一化
assert all((n.get('attr') or {}).get('updateFields') for n in walk_du(pj)), 'updateFields 注入失败，中止'
# → save_flow → deploy_flow → 按钮 API（顺序不能反：先有真实 flow_id 再 button/update 换绑）
```

**E2：data_update 更新 getMore 取到的多条记录（09-04 实证）**——链条 `start(buttonEvent) → getMore(selectType=3 关联多条) → data_update`：getMore 节点 attr 按「十三」⚠️ 存储契约写；**下游 data_update 的 attr 必须 `formTableSourceTaskId=<getMore节点id>` + `formTableSourceNodeType="getMore"` + `formTableSourceGetDataType=1`**（写成 `"search"`=get_one 的写法 → 引擎静默不批量写库，流程跑完数据不动）。⚠️ **`attr.formTableId` 必须 = 源 getMore 节点的 formTableId（`form_{getMore节点id}_{表code}`），不能填自身 id `form_{本节点id}_{code}`**（2026-09-09 用户手工修复实证：填自身 id 时 save/deploy 全 success、回读节点也一致，但节点配置不正确、UI/引擎按错误记录集取数；自愈与回读断言应加 `formTableId == form_{getMore节点id}_{code}`）。updateFields 固定值 val 直接给数值/文案，optType "1"。


### F. 审批通过后按关联多条逐行「有则更新 / 无则新增」（2026-09-04 仓储实测）

**禁止**打开 `example/入库审批修改库存示例.md`（数千行）和 `miniflow-node-types.md`。本组合 = 主流程 A/opinion + 子流程 D + 下面 3 段契约。同一 `.py` 跑完：先子后主。

**① 主流程** `tableEvent` + `startEventType=add`：`approver` → `opinion`（同意 / 拒绝）。同意支：`get_more`（`getType:3` 取主表关联多条）→ `subprocess`（`isMulti:true`，`customProcessId`=子流程 DB id）→ `data_update` 当前行状态=已通过。拒绝支：只 `data_update` 状态=已拒绝。buttonEvent 取消同类：无审批，`attr.formTableId=None`，扣减用 optType `"3"`。

**② 子流程** `startType=subEvent`（三层，见上文）节点抄组合 D：`get_one` 目标表（按仓+料两个 `eq`，`emptyAction=3`）→ `data_branch` 有=`data_update` `optType:"2"`（加）/ 无=`data_add`。跨流程引用明细字段：`formNodeType:"search"` + `formNodeId`=父 get_more id。

**③ get_more selectType=3 外科重写**（build 后、save 前；节点 id/childNode 不动）：

```python
a = node['attr']
a.update({
    'selectType': 3, 'formType': 2,
    'formTableCode': src_code, 'formTableName': src_name,          # 源表（主表）
    'formTableId': f'form_start_{src_code}',
    'linkFormTableField': link_model,                              # 源表 many link 的 model
    'linkFormTableCode': tgt_code, 'linkFormTableName': tgt_name,  # 目标表（明细）
    'linkFormTableType': 1,
    'formTableSourceTaskId': 'start', 'formTableSourceNodeType': 'table',
    'getDataType': 1, 'noDataType': 1,
    'expressionType': 'delegateExpression',
    'expressionValue': '${getMoreRecordDelegate}',
})
for k in ('getType', 'sourceTaskId', 'relationField'):
    node.pop(k, None)
```

`formTableList` 该条：`formTableCode/Name`=目标表、`formTableMainCode`=源表、`selectType=3`、`isSubStart:true`。漏 delegate → deploy 报 `flowable-servicetask-missing-implementation`。

**④ 子流程发布：** save → `register_subprocess_id` → 再 POST saveFlow（urlencoded）带 `id`+`customProcessId=<DBid>`+`processKey=process<DBid>`+`startType=subEvent` → deploy → `/act/process/list` 出现 key=`process<DBid>`。机理见上文 subEvent #47，不要打开 gotchas 全文。

**⑤ 审批人兜底：** username/realname 精确匹配点名 → 角色按 **roleName** 精确匹配 → 否则 `candidateUser` `admin` + 该用户 `realname`。禁止把 `roleCode=admin`（超管角色）当成「管理员」。
> ⚠️ **approverIds 写裸账号**（`["admin"]`），**不能带 `user.` 前缀**（前缀是消息节点 `toUserIds` 的写法）；办理人=**表单字段**时 `approverType` 用**复数 `candidateUsers`** + `assigneeByVariable`，且 **select-depart 字段必须加 `isNeedTranslateToUserIds: true`**。四种形态写错都**不报错、只是任务谁都收不到** → 见 gotchas #90（含 `/act/task/myTodo` 正反例验收法）。

**⑥ 按钮：** 先有真实 `flow_id`，再 `desform_custom_button.py` create（`flowStatus:true`）+ update 换绑 `processId`。`updateFields` 仍按组合 E 自愈注入。

### F. tableEvent → 系统消息给记录创建人（两节点快路径，2026-09-07 全链路实测）

触发条件（字段=固定值）+ 消息变量收件人，一条脚本跑完；字段 model 用 `fetch_form_fields` 解析，禁止写死。

```python
import json, time
ts = int(time.time() * 1000)
var_entry = "var." + json.dumps({
    "formTableCode": "<触发表code>", "formTableId": "form_start_<触发表code>",
    "nodeId": "start", "nodeType": "table",
    "field": "create_by", "fieldType": "select-user",   # 记录创建人（系统字段）
}, ensure_ascii=False)

config = {
    "processName": "<流程名>",
    "processKey": f"process{ts}", "processType": "oa",
    "lowAppId": "<应用ID>", "tenantId": "<租户ID>",
    "startType": "tableEvent",
    "formTableCode": "<触发表code>", "formTableName": "<触发表名>",
    "formTableId": "form_start_<触发表code>", "titleField": "<标题字段model>",
    "startEventType": "add|update",                        # add / update / add|update / delete
    "startCondition": [{                                   # 触发条件：字段=固定值
        "id": str(ts), "matchType": "",
        "queryItems": [{"rule": "eq", "ruleName": "等于", "valueType": "1",
                        "val": "测试", "name": None,
                        "field": "<条件字段model>", "columnName": "<条件字段中文名>",
                        "type": "input", "valType": "input"}],
    }],
    "startTaskId": f"task{ts}000",
    "nodes": [{
        "type": "notice", "name": "发送系统消息",
        "attr": {"noticeType": "system", "noticeTitle": "<消息标题>",
                 "noticeContent": "<消息内容>"},
        "toUserIds": [var_entry], "toUserNames": ["记录创建人"],   # 变量收件人格式见 gotchas #49
    }],
}
pj = build_process_json(config)
pj["attr"]["conditionFields"] = ["<条件字段model>"]   # ⚠️ builder 不落监控字段，必须 save 前自愈
# createStartNode 不补：默认 False=不启用发起人节点（用户点名时才在 config 传 True）
result = save_flow(api_base, token, config, pj)
if result.get('success'):
    deploy_flow(api_base, token, result['result']['id'])
```

要点：

- **触发字段/触发条件**：`conditionFields` = 监控字段 model 数组（update 事件时后端先比对新旧值）；`startCondition` = 条件组（queryItems 的 `valueType:"1"` 固定值、`rule` 用 `eq` 等代码、`type`/`valType` 按字段真实 type）。两者都配时，只有监控字段变了且条件满足才触发。注意 startCondition 的 `name` 写 `null`（#34 互斥分支条件里写 `[]`，是不同场景，勿混用）。
- **⚠️ 日期类字段的条件值（2026-09-08 实测，gotchas #52）**：条件字段是日期（年月/年季度/年周/年月日/日期时间）时，`val` 必须写**本地时区毫秒时间戳 int**（例：2026-09-08 10:30:00 → `1788834600000`），写日期字符串能 save/deploy 但条件恒不成立或意外命中、UI 选择器显示错日期；只有「时间」字段写 `"HH:mm:ss"` 字符串。判定口径：raw `/desform/api/fields/<code>` 该控件 `options.timestamp=true`（raw 里 `name`=中文名、`model`=编码），勿凭 fetch_form_fields 的 type 猜。
- **⚠️ 条件字段是日期类时 val 写毫秒时间戳数字**（写日期字符串能 save/deploy 但永不触发，见 gotchas #52）：先按本地时区换算（年月→当月 1 号 0 点、年月日→当日 0 点），`"val": 1788192000000` 这种 int；日期时间 eq 秒级相等易踩坑，优先 range。只有 time 字段写 `"HH:mm:ss"` 字符串。
- **收件人=记录创建人**：`"var."+JSON` 字符串（键：formTableCode/formTableId/nodeId/nodeType/field/fieldType），`toUserNames` 写显示名；attr 内与节点顶层都要写。其他人员字段同理换 `field`；❌ 别用 approver 的 variableContent 对象形态（会群发错误收件人），❌ 别用 toUserExpression。
- **开关(switch)字段的条件值**：= raw 控件 `options.activeValue` 字符串（「是/开」；`fetch_form_fields` 对 switch 不返回 options），queryItem `type`/`valType` 写 `switch`（gotchas #53，2026-09-08 实测）。
- **⚠️ 设计子表（内部子表）作触发字段（2026-09-09 实测，用户截图纠正）**：`fields` 接口**不返回** sub-table-design 容器——表单里有「内部子表」但 `fetch_form_fields`/raw fields 都看不到（只有外部子表 link-record 在顶层）。子表 model 要从**表单设计 JSON** 取：lowapp skill `query_form(code)['desformDesignJson']`（json.loads 后递归找 `type=='sub-table-design'` 的节点，model 前缀 `sub_table_design_`，`name`=中文名；也可从同表 summary 控件的 `options.linkTable` 间接看到）。startCondition 编码：`field`=子表 model、`columnName`=子表中文名、`type`=`sub-table-design`；空类规则 `empty`/`not_empty` 时 `val`/`valType` 写 **null**（与本应用用户/开关流程的 not_empty 样本同构）。`conditionFields` 同样写子表 model（update 触发时子表旧值走 redis 比对）。已实测建流程 save/deploy/回读通过。
- **省市级联动(area-linkage)字段的条件值**：`val`=末级行政编码字符串（海淀区→`"110108"`）+ `allVal`=各级编码数组（`["110000","110100","110108"]`，北京市/市辖区/海淀区）；写名称路径字符串能 save/deploy 但设计器显示「未选中」、运行时也不匹配（gotchas #57，2026-09-09 实测）。
- **⚠️ 部门选择控件（select-depart）的触发条件编码（2026-09-09 实测）**：`val` 写**部门 id 数组** `["<deptId>"]`、`name` 写**名称数组** `["研发部"]`——两处都要写；写字符串/None 设计器不识别、条件不匹配。部门 id 从 `GET /sys/sysDepart/queryTreeList` 该节点的 `id` 字段取（snowflake 或 UUID 视环境而定，以接口返回值为准）；行数据里该字段存储形态也是 id 数组 + `_dictText` 名称。同族控件 select-user（用户）的编码是 `val`=**username 标量** + `name`=**显示名标量**（如 `"val":"admin","name":"管理员"`；写 userId 或 id 数组设计器「未选中」，2026-09-09 用户 UI 实测纠正）——三者形态不同，勿互相套用。
- **⚠️ 组织角色控件（org-role）的触发条件编码（2026-09-09 实测，用户 UI 纠正）**：`val` 写**角色 roleCode 字符串**（不是 roleName 中文名、也不是 roleId！），`name` 写 `null`，`type`/`valType` 写 `org-role`。写中文名能 save/deploy 但条件不匹配。`fetch_form_fields` 对 org-role **不返回 options**，roleCode 必须用 `GET /sys/role/list?pageSize=200` 按 roleName 找——取该记录 `roleCode` 字段的短随机码（6~12 位字母数字），**不是 `id` 字段的 snowflake 长串**。**⚠️ 该接口不按租户过滤（实测 21 条里混有 tenantId=0/None/其他租户），必须先按 `tenantId == 当前租户` 过滤再按 roleName 找**；写别租户的同名角色 roleCode 能 save/deploy，但设计器值框显示空、条件无效——**角色控件是租户隔离的**（设计器选择器只显示本租户角色；用户/部门本环境 tenantId 全 null、不隔离，2026-09-09 实测）。**筛选条件多条时不要自行加 且/或 组**——用户没说就是单条，实测组级 matchType 写 `and` UI 仍显示「或」且跨租户值渲染为空行（2026-09-09 用户纠正）。UI 原生样本（rule=eq，field/columnName 换成目标环境实际值）：
  ```json
  {"rule": "eq", "ruleName": "等于", "valueType": "1",
   "val": "<roleCode>", "name": null,
   "field": "<org-role 字段 model>", "columnName": "<字段中文名>",
   "type": "org-role", "valType": "org-role"}
  ```
- **⚠️ builder 落库键映射（回读/修复要查落库键，不是 DSL 键，2026-09-08 实测）**：`build_process_json` 把 notice 的 DSL 键翻译成存储键——`noticeType`→`attr.type`、`noticeTitle`→`attr.title`、`noticeContent`→`attr.templateContext`（attr 内还落 `toUserIds`/`toUserNames`）。回读校验消息内容查 `attr.templateContext` 而非 `noticeContent`（查 DSL 键会误判「内容丢失」多花一轮修复）；修复消息节点内容/标题时直接改 `attr.title`/`attr.templateContext` 落库键。
- **⚠️ link-field（他表字段控件）触发条件编码（2026-09-09 用户实测纠正）**：`type`/`valType` 写 **`input`**（UI 原生，勿照抄字段 type 写 `link-field`——能 save/deploy 但运行时条件不匹配、流程不触发）；`val` 写**设计器选择器里显示的选项文本**（勿按口述词写：实测口述「家居」、实际选项为「家具」，照抄口述词条件永不成立）。触发字段/监控字段 `conditionFields` 仍写该字段 model。
- **实测验证**：add_data 一条满足条件的记录 → `GET /sys/annountCement/listByUser`（带 X-Tenant-Id 头）出现消息且只有正确收件人收到；不满足条件的记录不触发。

### G. 消息模板引用运算节点结果（写正文变量前必读 gotchas #55）

新建含「运算 → 通知/消息引用计算结果」的流程时，notice 节点正文引用运算结果**禁止**按运算公式的 funContext 形态写 `jsonContext`（那是公式上下文 8 键，消息侧不认）：

- **正确契约见 gotchas #55**：正文键 `attr.templateContext`；`jsonContext` 值为 base64(6 键紧凑 JSON)，键序 `field:"result"` / `formTableCode:"function-{funType}"` / `nodeId:<运算节点id>` / `nodeType:"function"` / `operationMode:"cache"` / `decimals:2`；hash 键 = md5(该紧凑 JSON)；占位符后缀统一写中文「结果」（`{{md5.结果}}`，一个运算节点一条）。
- 消息引用**表字段**（非运算结果）是另一套 4 键 JSON（`example/消息节点.md` 知识点 3），别混。
- ⚠️ 按 8 键函数上下文形态写能 save+deploy、消息也照发，但**取值全空**，须消息发出去才暴露——自愈/修正只写 `templateContext` + `jsonContext`，勿写 `noticeContent`（服务端双存、改了不生效）。
- 收件人=记录创建人等变量收件人写法同本组合 F。

### H. timerEvent 定时扫描 → getMore 批量更新 + **子流程逐行**系统消息（2026-09-09「订单超时自动处理」两版实证）

定时触发每天跑，扫描工作表中满足条件的多条记录 → 批量改状态 → 逐条给记录上 select-user 字段（客户）发系统消息。

> ⚠️ **多记录发消息禁止直连主流程（用户 2026-09-09 指正）：** message 节点直接跟在 getMore 后**不逐行执行**（主流程只处理单记录，运行时不会对每行发）。正确结构 = **主链到 data_update 为止，后面挂 callActivity 子流程逐行**：
> 主链 `function(-1D) → data_get_more(双条件) → data_update(getMore 批量) → callActivity(subEvent 子流程, isMulti:true)`
> 子流程（subEvent 三层）内只放 `message_system`，收件人 var 引用父 getMore 行：`nodeType='search'`（子流程内行上下文=search 形态，nodeTypeMain=getMore）+ `formTableId=form_{父getMore节点id}_{表code}` + `nodeId=父getMore节点id`。
> 本组合下方代码=修复后实证版（双回读+引擎 key 核验通过）。子流程整条手工 JSON/发布配方（补 customProcessId → PUT deploy → 校验 key=process<DBid>）抄「主子流程配置示例.md」§4/§5 + gotchas #47；callActivity attr/subFormTableObject/listenerData/inVariableModels 生产形态见该文件附录。**完整一键模板（改 ①–⑤ 常量即跑，含全新建/改已有两种）→ `example/定时批量处理逐行通知示例.md`，优先直抄模板；本组合代码为内联简版。**

```python
import sys, time, json
sys.path.insert(0, r'<skill_base_dir>\scripts')
from miniflow_creator import fetch_app_forms, fetch_form_fields, build_process_json, save_flow, deploy_flow

ts = int(time.time() * 1000)
op_id, gm_id, du_id = f'task{ts}001', f'task{ts}002', f'task{ts}003'
F_DATE, F_RADIO, F_CUST = '<日期字段model>', '<radio字段model>', '<select-user字段model>'   # fetch_form_fields 按中文名解析，勿写死

var_val = {'variableValue': 'result', 'formTableCode': 'function-date', 'variableName': '结果',
           'fieldType': 'date', 'formNodeType': 'function', 'formNodeId': op_id,     # ⚠️ fieldType=字段真实类型
           'formNodeName': '计算截止时间', 'operationMode': 'cache', 'decimals': 2}
var_entry = 'var.' + json.dumps({'formTableCode': '<表code>', 'formTableId': f'form_{gm_id}_<表code>',
                                 'nodeId': gm_id, 'nodeType': 'search',            # ⚠️ nodeType='search'：子流程内引用父 getMore 行
                                 'field': F_CUST, 'fieldType': 'select-user'}, ensure_ascii=False)

config = {
    'processName': '订单超时自动处理', 'processKey': f'process{ts}', 'processType': 'oa',
    'lowAppId': '<lowAppId>', 'tenantId': '<tenantId>',
    'startType': 'timerEvent', 'beginDateStr': '2026-09-10 09:00',   # ⚠️ 字符串形态，时间戳会丢分钟位
    'endDateStr': '2026-12-31 18:00', 'timeCycleName': '每天',        # ⚠️ 8 个 UI 实名之一（每天→timeCycle "3"）
    'startTaskId': f'task{ts}000',
    'nodes': [
        {'type': 'get_more', 'id': gm_id, 'name': '查询超时记录', 'getType': 1,
         'formTableCode': '<表code>', 'formTableName': '<表名>',
         'conditions': [
             {'rule': 'eq', 'ruleName': '等于', 'valueType': '1', 'val': '未付款',      # radio 固定值=纯字符串选项文案
              'name': None, 'field': F_RADIO, 'columnName': '支付状态', 'type': 'radio', 'valType': 'radio'},
             {'rule': 'le', 'ruleName': '小于等于', 'valueType': 3, 'val': var_val,   # 日期 le 函数结果：valueType=3 + valType=variable
              'name': None, 'field': F_DATE, 'columnName': '下单时间', 'type': 'date', 'valType': 'variable'},
         ],
         'fetchMode': 'cache', 'limitCount': 0},
        {'type': 'data_update', 'id': du_id, 'name': '批量标记已超时',
         'formTableCode': '<表code>', 'formTableName': '<表名>',
         'formTableSourceTaskId': gm_id, 'attr': {'formTableSourceNodeType': 'getMore'}},
        # ⚠️ 主链到此为止——多记录发消息不能直连（下方自愈挂 callActivity 子流程逐行）
    ],
}
pj = build_process_json(config)

# ① function(-1D) 手插链头（builder 不支持 date 运算，生产形态=gotchas #41）+ 登记 formTableList
op = {'id': op_id, 'name': '计算截止时间', 'type': 'function', 'status': -1, 'configure': {},
      'attr': {'funType': 'date', 'funContext': {}, 'funText': '-1D',
               'expressionType': 'delegateExpression', 'expressionValue': '${functionDelegate}',
               'dateFieldVal': {'formNodeType': 'system', 'variableValue': 'nowDate', 'variableName': '当前日期'},
               'dateFunctionFormat': {'argument': 'date', 'result': 'date', 'end': '2', 'out': 'd'},   # datetime 字段时 argument/result='datetime'
               'operationMode': 'cache', 'decimals': 2},
      'addable': True, 'deletable': False, 'error': False, 'errorContent': '', 'content': '当前日期  -1D'}
op['childNode'] = pj.get('childNode'); op['pid'] = 'start'
if pj.get('childNode'): pj['childNode']['pid'] = op_id
pj['childNode'] = op
pj.setdefault('formTableList', []).insert(0, {'formTableId': f'form_{op_id}_function-date', 'nodeId': op_id,
    'nodeName': '计算截止时间', 'nodeType': 'function', 'formTableCode': 'function-date',
    'formTableName': '计算截止时间', 'operationMode': 'cache', 'decimals': 2})

# ② save 前自愈（walk 按 id 取节点后改 attr；链线性所以 level 按 1..N 归位）：
#    getMore：attr.searchFieldGroup[0].queryItems = 上面两个条件（多条件落库键是 searchFieldGroup，不在顶层 conditions）
#              attr.formTableId = f'form_{gm_id}_<表code>'；getDataType=1/noDataType=1/selectType=1/formType=2 补齐
#    data_update：attr.formTableSourceGetDataType=1；attr.updateFields=[{'id':str(ts)+'9','optType':'1','fieldValue':'',
#                  'field':F_RADIO,'val':'已超时','fieldType':'radio','type':'radio'}]（组合 E ③ 形态）
#              ⚠️ attr.formTableId = f'form_{gm_id}_<表code>'（= 源 getMore 的 formTableId，填自身 id 是配置错：save/deploy/回读全绿）
#    callActivity 挂到 data_update 之后（手工 JSON）：attr 全键 + subFormTableObject=父 gm 的 formTableList 条目+isSubStart:true
#              + listenerData(MiniCallActivityListener) + inVariableModels 4 条（applyUserId/dataId/JG_LOCAL_PROCESS_ID→JG_SUB_MAIN_PROCESS_ID/handleDataId）
#              → 生产形态抄「主子流程配置示例.md」附录；父 gm 的 formTableList 条目补 isSubStart:true
# ③ 顺序（先子后主）：建 subEvent 子流程（三层 startType，root/attr.formTableList[0] 均为 search 形态；
#    子流程内唯一节点 message_system：attr receiveType='user'/title/templateContext/toUserIds=var_entry + 节点顶层双写）
#    → 发布配方 gotchas #47：回查 updateCount → POST saveFlow 补 customProcessId/processKey=process<DBid> → PUT deployProcess
#    → 校验 /act/process/list 出现 key=process<DBid> → 再 save_flow+deploy 主流程
#    回读断言：主链 == ['function','data_get_more','data_update','callActivity']、callActivity.customProcessId==子DBid 且 isMulti、
#    ⚠️ du.attr.formTableId == f'form_{gm_id}_<表code>'、子流程三层 subEvent 且消息收件人 var 含 nodeType='search' 条目
```

要点：

- **触发参数**：timerEvent 抽屉完整字段（hourType/dayValue 等）由 builder 按 timeCycleName 自动映射，config 只需 beginDateStr/endDateStr/timeCycleName；调度修改只动 processJson.attr 三字段后 save+deploy（body 勿动）。发布后引擎注册 key=processKey，`/act/process/list` 可核验。
- **状态字段语义映射**：目标选项不存在时用已有近似选项（如无「待支付」→「未付款」）并在交付说明中写明，不私自造选项。选项来自字典/工作表时 val 写 itemValue（gotchas #40）。
- **逐行发消息必须走子流程（用户 2026-09-09 定论）**：主流程 message 节点不逐行；子流程内 var 条目 `nodeType='search'`（子流程行上下文，nodeTypeMain=getMore）、`formTableId=form_{父getMore节点id}_{表code}`、`nodeId=父getMore节点id`（start 上下文才是 `'table'`/`form_start_`；主流程直连 getMore 的 `'getMore'` 形态只可在设计器选到人、运行不逐行）。正文要引用记录字段时另见组合 G/gotchas #55（jsonContext 需 md5+base64）。
- **数据批量更新**：必须 `formTableSourceNodeType='getMore'` + `formTableSourceTaskId=<getMore节点id>` + `formTableSourceGetDataType=1`（组合 E2）；写成 `'search'` 引擎静默不批量写库。

### I. timerEvent「仅执行一次」+ 全员系统公告站内消息（2026-09-09 实测交付）

用户说"XX 时间执行**这一次即可，不用重复**：向**全员**发一条**系统公告/站内消息**"时直抄本组合——无工作表参与，start 后直接 message_system。

- **仅一次 = 调度窗口截断**：引擎按 `[beginDateStr, endDateStr]` 窗口排程（`begin + n×周期 ≤ end` 才触发）。`beginDateStr`=执行时刻、`endDateStr`=当天 `23:59`、周期「每天」→ 窗口内只命中一次；**无独立"仅一次"周期**（dateFieldEvent 的 `cycleType=1` 是另一套 startType，勿套，见 trigger-types.md）。
- **全员 = 枚举租户全部用户**：全平台流程扫描 **0 个 "all 类型收件人" 实证**——不存在"全员"接收类型。收件 = `GET /sys/user/list`（**`X-Tenant-Id`=目标租户**，不是默认登录租户）全量 `username/realname` → `user.{username}` 逐人；后续租户加人需人工补收件人。
- **存储契约**：message_system `attr{type:"system", title, templateContext, receiveType:"user", toUserIds, toUserNames}`；**节点顶层 toUserIds/toUserNames 双写**（builder 落库键：noticeTitle→attr.title、noticeContent→attr.templateContext）。builder 产物若缺 `attr.receiveType` → save 前自愈补 `"user"`（同应用既有消息流程实测必有此键）。
- **拿真实契约 / 查流程 JSON**：`GET /act/process/extActProcess/queryById?id=`（带 `X-Low-App-ID` 头）——`extActProcess/list` 响应**不带** processJson（2026-09-09 实测）。⚠️ 禁止翻本地 jeecg 前后端源码找 UI 契约——简流模块不在本地源码树（多轮 grep 全空实测）。
- 验证：发布成功只代表调度已注册；投递要等 fire 时间，事后 `GET /sys/annountCement/listByUser`（X-Tenant-Id）逐用户核对。

```python
# ① 目标租户用户（X-Tenant-Id 用目标租户）
uj = requests.get(f'{API}/sys/user/list',
    headers={'X-Access-Token': TOKEN, 'X-Tenant-Id': '<租户id>'},
    params={'pageNo': 1, 'pageSize': 100}).json()
users = uj['result']['records']          # [{username, realname, ...}]

# ② 组装（beginDateStr 必须字符串形态）
ts = int(time.time() * 1000)
config = {
    'processName': '<名称，如：系统维护公告定时发送>',
    'processKey': f'process{ts}', 'processType': 'oa',
    'lowAppId': '<lowAppId>', 'tenantId': '<租户id>',
    'startType': 'timerEvent',
    'beginDateStr': '<执行时刻 YYYY-MM-DD HH:mm>',   # = 执行时刻（字符串形态）
    'endDateStr': '<执行日 23:59>',                  # 当天截止 => 仅执行一次
    'timeCycleName': '每天',
    'startTaskId': f'task{ts}000',
    'nodes': [{
        'type': 'notice', 'id': f'task{ts}001', 'name': '发送系统公告',
        'attr': {'noticeType': 'system', 'noticeTitle': '<标题>',
                 'noticeContent': '<正文>'},
        'toUserIds': ['user.' + u['username'] for u in users],
        'toUserNames': [u['realname'] or u['username'] for u in users],
    }],
}
pj = build_process_json(config)

# ③ save 前自愈：attr 缺 receiveType 补 'user'（对照真实 message_system 样本）
def collect(n, acc):
    if not n:
        return acc
    acc.append(n)
    for b in [n.get('childNode')] + list(n.get('conditionNodes') or []):
        collect(b, acc)
    return acc
for n in collect(pj.get('childNode'), []):
    if n.get('type') == 'message_system':
        n['attr'].setdefault('receiveType', 'user')

result = save_flow(API, TOKEN, config, pj)
if result.get('success'):
    deploy_flow(API, TOKEN, result['result']['id'])
```

**回读断言**（高危：新建+发布必回读）：root `startType=timerEvent`；`attr.{beginDateStr=<执行时刻>, endDateStr=<执行日 23:59>, timeCycle='3'}`；msg `attr.{type='system', title, templateContext, receiveType='user'}`；顶层与 attr 的 `toUserIds` 数量 == `len(users)`。

> ⚠️ 内容含"将于 XX 时升级"而发送时刻恰为 XX 时这类口径矛盾，先向用户确认（提前提醒应早于事件时刻），不擅自改用户给的时间。
- ⚠️ **消息/引用类节点一律按本条 + gotchas #55 自拼，禁止为单节点探查全应用流程并整节点复制库内成品流**——早期 AI 成品可能按 4 键 jsonContext / 后缀=节点名的旧契约落库（见 gotchas #55 末节），照抄会扩散「消息取值全空」bug；契约明确时省掉整轮探查。

### J. 互斥分支-自定义表达式条件（2026-09-10 用户 UI 创建实证）

用户说「互斥分支 + 分支条件使用自定义 + 自定义流转条件为 XX」时，**不是**字段条件组（branchType=1 + conditionGroup），而是**自定义表达式**：表达式存分支节点 `content` 键、`attr.branchType` 恒为 2、`conditionGroup` 恒为 `[]`、attr 无 branchForm，区分条件/默认分支只靠 `isDefault`（2026-09-10 误建实证：按字段条件组建一条被用户纠正）。builder 的 exclusive 只支持字段条件形态 → **save 前自愈**重写每个分支：

```python
# save 前自愈（条件分支示例；默认分支同式：content='其他情况进入此流程'、priorityLevel=2）
for br in ex['conditionNodes']:
    br['attr'] = {'branchType': 2, 'priorityLevel': 1 if not br.get('isDefault') else 2,
                  'conditionGroup': [], 'showPriorityLevel': True, 'level': '1'}
    if br.get('isDefault'):
        br['content'] = '其他情况进入此流程'
    else:
        br['content'] = "${<字段model> == '测试'}"   # 表达式按下方语法拼
```

**表达式语法（用户 2026-09-10 确认）：** 字段用 model 引用、整体包 `${...}`；**字符串值加单引号**（`'张三'`）、**数值不加**（`100`）；**⚠️ 日期类字段（date，options.timestamp=true）的值=毫秒时间戳数字、不加引号**（如 `${date_xxx < 1789056000000}`=2026-09-11 00:00 本地；写带引号日期串能 save/deploy 但运行时恒不触发，2026-09-10 用户实测确认「日期组件需要时间戳」）；**时间字段（time）仍写 `"HH:mm:ss"` 字符串、加引号**（「时间组件不是」毫秒）；运算符 `== != >= <= > <`；逻辑 并且 `&&`、或者 `||`（如 `${input_xxx == '测试' && number_xxx > 10}`）。完整落库 JSON 见 node-types 第二十节「自定义表达式条件」。

> ⚠️ **运行时作用域限制（2026-09-11 实测，buttonEvent 全流程返工）：自定义表达式只在 tableEvent 触发且引用起始行字段时可用**——起始行字段才会注入为 EL 变量。**buttonEvent 按钮触发与 get_one 检索结果字段不注入 EL 变量**，运行时网关报 `Unknown property used in expression: ${summary_xxx} > 100000`、流程卡死在网关（save/deploy/回读全绿，只有真跑才炸）。这两种场景一律用**字段条件组**（branchType 1 + conditionGroup + branchForm 指向 start/检索节点），检索字段间比较的 queryItems 写法：`valueType:"3"` + `valType:"variable"` + val 变量对象 `{formNodeType:"search", formNodeId:<get_one节点id>, ...}`（见 trigger-types「val 的变量形态」）。已建错流程的修复模板见 SKILL.md「修改已有简流」互斥分支段（query_flow → 重写分支 attr → save+deploy）。

### J. 工作表新增 → 单审批（或签）→ 更新触发记录字段 → 结束【最高频 OA 模板】

「新增记录触发 → 一个审批节点 → 通过后把某字段改成 XX」是最常见需求，**本组合 + 自适应一步流 = 单轮 1 次 py 即终态**（2026-09-10 请假申请审批实证，save→deploy 仅 1.6s）。**禁止**再拆成「B 节拿 approverGroups + node-types 拿审批人来源 + 入库示例拿 data_update」三轮文档拼装。

```python
import sys, time
sys.path.insert(0, r'<skill_base_dir>\scripts')
from miniflow_creator import (fetch_app_forms, fetch_form_fields,
                              build_process_json, save_flow, deploy_flow, query_flow)

apps = fetch_app_forms(API, TOKEN, TENANT)
app  = next(a for a in apps if a['name'] == '<应用名>')          # app 键名是 id（=lowAppId），无 lowAppId 键
tbl  = next(f for f in app['forms'] if f['name'] == '<工作表名>')
fo   = fetch_form_fields(API, TOKEN, tbl['code'], TENANT)
st   = fo['<状态字段中文名>']
assert '已通过' in (st.get('options') or []), f'目标选项不存在: {st.get("options")}'   # 选项必须先核实

ts = int(time.time() * 1000)
ap_id, du_id = f'task{ts}001', f'task{ts}002'
config = {
    'processName': '<流程名>', 'processKey': f'process{ts}', 'processType': 'oa',
    'lowAppId': str(app['id']), 'tenantId': TENANT,
    'startType': 'tableEvent', 'formTableCode': tbl['code'], 'formTableName': tbl['name'],
    'formTableId': f'form_start_{tbl["code"]}', 'titleField': tbl['titleField'],
    'startEventType': 'add', 'startTaskId': f'task{ts}000',
    'nodes': [
        {'type': 'approver', 'id': ap_id, 'name': '<审批节点名>', 'approvalMode': 1,   # 1=或签
         'attr': {'approvalMethod': 1},
         'approverGroups': [{'approverType': 'candidateUser', 'assigneeType': 'assigneeByName',
                             'approverIds': [<username>], 'approverNames': [<显示名>],
                             'deptIds': [], 'deptNames': [], 'roleIds': [], 'roleNames': [],
                             'postIds': [], 'postNames': [], 'expressionsIds': [], 'expressionsNames': [],
                             'levelMode': 1, 'approverId': '', 'approverName': '',
                             'variableTitle': [], 'variableContent': '', 'formTableType': ''}]},
        {'type': 'data_update', 'id': du_id, 'name': '<更新节点名>',
         'formTableCode': tbl['code'], 'formTableName': tbl['name'],
         'formTableSourceTaskId': 'start',
         'attr': {'formTableSourceNodeType': 'table'},
         'updateFields': [{'field': st['model'], 'val': '已通过',
                           'fieldType': st['type'], 'type': st['type']}]},
    ],
}
pj = build_process_json(config)
# createStartNode 保持 builder 默认 False：**不启用发起人节点**（旧版此处写 True，2026-09-11 作废）

# 自愈：data_update 完整 updateFields 注入 attr（组合 E ③；顶层写法会被 builder 置 null）
for n in [pj['childNode'], pj['childNode']['childNode']]:
    if n.get('type') == 'data_update':
        n['attr']['updateFields'] = [{'id': str(ts) + '9', 'optType': '1', 'fieldValue': '',
                                      'field': st['model'], 'val': '已通过',
                                      'fieldType': st['type'], 'type': st['type']}]
result = save_flow(API, TOKEN, config, pj)
assert result.get('success'), result
flow_id = result['result']['id']
deploy_flow(API, TOKEN, flow_id)
# 回读内联同轮（只读 attr.*，见下）
```

- **审批人来源四选一**（`approverType` / 填哪些键）：指定用户 `candidateUser`+`assigneeByName` → `approverIds=[username]`（**username 不是 userId**）+`approverNames=[显示名]`；指定角色 `candidateGroups` → `roleIds=[roleCode]`+`roleNames=[名]`；指定部门 `candidateDepts` → `deptIds`+`deptNames`；指定职务 `candidatePosts` → `postIds`+`postNames`。
- **或签 = `approvalMode=1`**（builder 恒写 1，禁止断言"无该键"）；会签 3~7 见组合 B。
- **⚠️ 落库位置：`approverGroups` 两处都写同值——`attr.approverGroups`（界面面板处）+ 节点顶层副本（仅写一处另一处会滞留旧值，2026-09-15 实证）；`formTableSourceTaskId` / `formTableId` / `level` / `updateFields` / `formTableSourceNodeType` 全在 `attr` 内**。**回读断言必须读 `attr.*`**——查节点顶层得 None，会误判"更新源丢失"再多跑一轮修复（gotchas #81）。
- **触发条件**：只需「新增触发」时不写 `startCondition`；要记录级过滤（如仅某类型）再按组合 F 加，并补 `attr.conditionFields`（builder 不落监控字段）。
- **发起人节点**：默认**不启用**（`createStartNode=False`，builder 默认值，不要补写）；仅用户点名要「发起人节点／发起人填写／启用发起人节点」时才在 config 传 `"createStartNode": True`。
- **防呆内联脚本头部**：`extActProcess/list` 查同名（0.1s），断言不存在才新建——禁止单独一轮核实（#70）。
- **建后首跑验证**：新增一条记录 → 审批人待办出现 → 通过后该记录状态字段变「已通过」。

**组合 J 变体：脚本节点 / 排他分支 / 引用脚本变量（2026-09-10 实测，细节见 gotchas #82）**

链路 `tableEvent add → script → exclusive → approver → data_update` 时，在 J 的基础上补三条：

1. **自愈只增补键，禁止 `n['attr'] = {...}` 整块赋值** —— builder 已在 attr 内生成 `expressionType:'delegateExpression'`/`expressionValue:'${updateRecordDelegate}'`（miniflow_creator.py:392），整块替换会让 data_update 变无实现 serviceTask、**deploy 报 `flowable-servicetask-missing-implementation`**。
2. **分支条件自愈读 `br['attr']['conditionGroup']`，不是 `br.get('conditionGroup')`**（builder 放 attr 内，读顶层得 None → 会写出空条件）；并补 `qi['id']=str(ts)+序号`（builder 不生成行 id，缺则设计器无法编辑该行、整组失去且/或）。
3. **script 节点纯 attr 承载**：`{'scriptFormat':'javascript','scriptContent':'多行JS','autoStoreVariables':False,'description':...}`；跨节点引用 `execution.setVariable` 的变量 → 根级 `variableList` 声明变量名 + formTableList 加 `_variable_` 条目；分支条件 `field=<变量名>` + `branchForm/formTableCode='_variable_'`。

4. **流程参数命名（用户 2026-09-10 定论，见 gotchas #83）**：脚本 `setVariable` 变量名、`variableList[].field`、`variableList[].columnName`、data_update 取值 `variableValue`/`variableName`、分支条件 `field`/`columnName` **四处同名，且变量名直接用中文**（Groovy 支持中文标识符，实测可跑）。**只写 `field` 不写 `columnName` 时设计器「本流程参数」列表退回显示英文标识**（`[数字] totalSubsidy`）——绑定其实是好的，但使用者会以为参数没生成。声明条目形态：`{'id': <雪花id>, 'type': 'number', 'options': {'format': 'yyyy-MM-dd'}, 'field': '总补贴金额', 'columnName': '总补贴金额'}`（`type` 仅 input/number/date；三种类型的生产样本都带 `options.format`）。
5. **脚本节点两处文本必须同写**：`attr.scriptContent` **和节点顶层 `content`**（设计器卡片显示文本）。只改前者时卡片仍显示旧脚本/旧变量名。改名后断言 `json.dumps(pj)` 无旧名残留——实测正是靠该断言发现第二处。
6. **脚本读表字段**：`execution.getVariable('<字段model>')`；**date 字段实测传入 `yyyy-MM-dd HH:mm:ss` 字符串**，直接 `new Date(str)` 抛异常且**被 Groovy 静默吞掉**（变量为空、不报错）→ 做 Date / 毫秒 / 字符串三形态兜底解析（截前 10 位按 `yyyy-MM-dd` parse）。

**排他分支两条支线必须真跑一次**（造 2 条数据，比值各落一个支线）——`/act/task/myApplyProcessList` 读 `currentTaskName` 是最直观核验（★ 本环境无任务完成 API，审批后落库只能 UI 验收，见 #82）。
