# 定时触发壳（8 实名）契约参考 —— runner 兜底（2026-09-09 实测）

**角色**：日常建壳由 `scripts/timer_job_runner.py shell` 一条命令完成（SKILL.md 路由直跑，防呆+回读+耗时内嵌，**禁止为它手抄本文件脚本**）。本文件只在 **runner 异常 / 需要理解壳的 API 契约 / 手工改造壳结构** 时使用。

**适用周期**：仅 7 个预置实名 = 每分钟/每小时/每天/每月1号/每周三/周一到周五/每年12月31日。**「自定义」不在其中**（无组合字段的 timeCycle=custom 会 hourType1 每小时跑）→ 自定义周期（每周一/每月15号/每年上半年每周五…）走 `custom-cycle.md`，壳流程一律不带执行节点（空壳可 save+deploy）。

**名称规范** = 「定时触发流程-<周期实名>」（应用内既有：每月1号/每周三/周一到周五/每年12月31日…；用户给了名则用用户的）。改 ①–⑧ 常量后 1 次 py 跑完，防呆自查内嵌，禁止任何探查轮。

```python
# -*- coding: utf-8 -*-
import sys, time, json, requests
sys.path.insert(0, r'<skill_base_dir>\scripts')
from miniflow_creator import query_flow, build_process_json, save_flow, deploy_flow

API, TOKEN = '<api_base>', '<token>'          # ①-② 凭证：按 SKILL「凭证」节取（memory 凭证文件 / 本轮消息）
TENANT, APP = '<租户id>', '<lowAppId>'        # ③-④ 目标租户与所属应用
NAME = '定时触发流程-每周三'                   # ⑤ 名称规范=「定时触发流程-<周期实名>」；用户给了名则用用户的
BEGIN = '<开始执行时间 YYYY-MM-DD HH:mm>'      # ⑥ 字符串形态（时间戳丢分钟位）
END = None                                    # ⑦ 结束执行时间；用户没给 → None（调度窗口=只按开始时间排）
CYCLE = '每周三'                              # ⑧ 周期实名（仅 7 预置选 1，见上；自定义 → custom-cycle.md）
MAP = {'每分钟':'1','每小时':'2','每天':'3','每月1号':'4','每周三':'5','周一到周五':'6','每年12月31日':'7'}

# 防呆即探查替代：应用下同名流程存在即中止（0.1s，仅名称不带 processJson）
hd = {'X-Access-Token': TOKEN, 'X-Tenant-Id': str(TENANT), 'X-Low-App-ID': str(APP)}
lst = requests.get(f'{API}/act/process/extActProcess/list', headers=hd,
                   params={'pageNo': 1, 'pageSize': 100}, timeout=30).json()
names = [x.get('processName') for x in ((lst.get('result') or {}).get('records') or [])]
assert NAME not in names, f'同名流程已存在: {NAME}'

ts = int(time.time() * 1000)
config = {
    'processName': NAME, 'processKey': f'process{ts}', 'processType': 'oa',
    'lowAppId': APP, 'tenantId': TENANT, 'startType': 'timerEvent',
    'beginDateStr': BEGIN, 'timeCycleName': CYCLE,
    'startTaskId': f'task{ts}000', 'nodes': [],
}
if END:                                # 没给结束时间就不传
    config['endDateStr'] = END
pj = build_process_json(config)               # 自动映射 attr.timeCycle（每周三→"5"）

res = save_flow(API, TOKEN, config, pj)
assert res.get('success'), res
flow_id = res['result']['id']
print('deploy:', json.dumps(deploy_flow(API, TOKEN, flow_id), ensure_ascii=False)[:200])
back = query_flow(API, TOKEN, flow_id=flow_id)
ra = back.get('processJson')
ra = ra if isinstance(ra, dict) else json.loads(ra)
a = ra['attr']
assert a.get('timeCycle') == MAP[CYCLE] and a.get('beginDateStr') == BEGIN \
    and (END is None or a.get('endDateStr') == END), a
print(f'完成: id={flow_id} name={NAME} startType={back.get("startType")} updateCount={back.get("updateCount")} '
      f'cycle={CYCLE}({a["timeCycle"]}) 窗口 {BEGIN} ~ {END}')
```

**汇报**：命中时刻由模型心算并在回复中列出（按 BEGIN~END 窗口 + 周期逐次推演），**不要为此开脚本**。壳流程等用户后续补执行节点（补节点走 SKILL.md「修改已有简流」）。
