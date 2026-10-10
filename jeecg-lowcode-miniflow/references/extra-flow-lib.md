# 手拼简流构建器（extra_flow_lib）—— 两个批量构建器不覆盖的档

`build_flows.py`（DSL 批量）与 lowapp `postbuild_flows.py` 都做不了的形态，用
`scripts/extra_flow_lib.py` 手拼。本库形态取自 **2026-10-08 实测**（24 表应用 25 条流，
其中 7 条手拼；check_node_contract 违例 0，关键节点与真机 `processJson` 逐键保真比对通过）。

## 覆盖档位

| 档 | 用什么 |
|---|---|
| 关联取值取单条 | `get_one(..., select_type=3, src=..., link_field=..., link_table=...)` |
| 有/无数据分流 | `databranch(gw_id, prev_id, yes_child, no_child)` |
| 取多条 → 统计条数 → 占位符消息 | `get_more` + `record_fn` + `placeholder_ctx` + `msg_node` |
| 调子流程 | `publish_subflow`（#47 配方）+ `ca_node` + `pj['subFlowList']` |
| 定时（每天）| `timer_custom(pj, begin, hour=7)`（自定义周期；7 预置周期用 runner 即可） |
| 按日期字段触发 | cfg 直填 `triggerField/executeType/plusDate/...` + `df_cond_group/df_item` 写 startCondition |
| 自动新增（引用本记录字段）| `add_node` + `start_ref` + `sys_ms()` |
| 删除记录（挂 getMore 源）| `del_node` |

## 用法

```python
import sys; sys.path.insert(0, '<miniflow skill>/scripts')
from miniflow_creator import build_process_json, save_flow, deploy_flow
from extra_flow_lib import *

L = init(API, TOKEN, TID, AID,
         code_map={'工单': 'tb_gd', '客户': 'tb_cust', ...},
         fields_map={t: fetch_form_fields(API, TOKEN, code, TID) for t, code in code_map.items()})
# 节点 id 惯例 f'task{TS}xxx' / f'Gateway{TS}xxx'；TS 由 init 返回

n1 = get_one(f'task{TS}031', '查询记录', '工单', [c_fixed(FM('工单','状态'),'状态','radio','待处理')],
             3, 'start', '0.500')
gw = databranch(f'Gateway{TS}034', n1['id'], yes_child=None, no_child=None)
# 分支内首节点 pid 必须改成分支行 id：
yes['pid'] = gw['conditionNodes'][0]['id']
n1['childNode'] = gw

cfg = {'processName': '每日提醒', 'processKey': f'process{TS}903', 'processType': 'oa',
       'lowAppId': AID, 'tenantId': TID, 'startType': 'timerEvent',
       'beginDateStr': '2026-10-09 07:00', 'endDateStr': '2030-12-31 23:59',
       'timeCycleName': '每天', 'startTaskId': f'task{TS}030', 'nodes': []}
pj = build_process_json(cfg)
timer_custom(pj, '2026-10-09 07:00', hour=7)          # 自定义周期才需要；7 预置周期省略
pj['childNode'] = n1
pj.setdefault('formTableList', []).extend([ftl_get_one(...), ftl_get_more(...), ftl_fn(...)])
save_deploy(cfg, pj, '每日提醒')
readback('每日提醒', expect_types=['data_get_one', 'databranch', 'data_get_more', ...])
```

配方细节（消息占位符 / callActivity 传参 / 子流程骨架 / dateFieldEvent cfg / 数据分支两支皆空 / 两跳关联取值）
均已固化在库函数里（msg_node + placeholder_ctx / ca_node / publish_subflow / df_cond_group / databranch / get_one select_type=3）。
换应用只改 `init()` 的常量与 code_map/fields_map（字段 model 现取禁照抄）；2026-10-08 七配方真机实测通过（24 表应用 25 条流）。

## 契约红线（改脚本前先看，违了 save/deploy 也不会拦）

1. **日期控件值写 `sys_ms()`**（`variableValue:'millisecond'`）——`nowDate` 会落成字符串混格式。
2. **分支内首节点 `pid` = 分支行 id**（不是网关 id）；`databranch` 名必须恰为「数据分支」，
   两支 content 是 `${flow_has_data==1}` / `${flow_has_data==0}`，`attr.branchType=2`。
3. **callActivity**：`customProcessId`=子流程 DB id、`isMulti`、`subFormTableObject`（**与子流程
   start 那份同一对象**，`formTableId` 非空）、`formTableSourceTaskId`=上游 getMore 节点 id、
   listenerData=MiniCallActivityListener、inVariableModels 四对——`ca_node` 已全带。
   ⚠️ `collection` 保留 `${flowUtil.stringToList(assigneeUserIdList)}` 残值、别动。
4. **子流程四登记**：父 callActivity 数据对象 ↔ 子流程 `start.attr.subFormTableObject` ↔
   子流程 `formTableList[0]`（`isSubStart:true`、`nodeTypeMain:'getMore'`、
   **`nodeName`=父流程调用节点名**）↔ 父流程 `pj['subFlowList']`。`publish_subflow` 负责发布
   （saveFlow→补 customProcessId→deploy→校验 `process<DBid>` 注册）；传参经
   `start.variableList` 声明 + 父 `ca.attr.variableList` 填 `rec7(...,'input')`。
5. **`query_flow` 按名查必须带 `low_app_id`**（本库 `readback` 已带），否则跨应用扫不到/命中错。
6. function 节点 **`content`（画布文案）不要等于 `funText`**（契约检查提示项）；
   `record_fn` 的 `funContext.formTableId` 必须指 getMore 节点（`form_<gm_id>_<code>`）。
7. 节点建了就要登记 `formTableList`（变量选择器的输入行）；`ftl_*` 系列已对好 nodeType。
8. 收尾必须跑 lowapp 的 `check_node_contract.py`（违例非 0 即失败）+ 本库 `readback()`；
   `save/deploy` 全绿**不是**验收。
