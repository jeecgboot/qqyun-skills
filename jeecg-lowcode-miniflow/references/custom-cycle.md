# 自定义周期（timeCycle=custom）定时触发完全解 —— 月/日/周/时 四轴 + 可抄模板（2026-09-10 定稿/巩固）

**命中特征**：timerEvent 周期**不在 7 个预置实名内**（每分钟/每小时/每天/每月1号/每周三/周一到周五/每年12月31日）——如 每周一/每月15号/每年上半年每周五/奇数月+每10天/固定月×月末 → **0 轮判定 runner 不可用**（gotchas #66，禁止 --help/grep/读 runner 求证），直抄本文件「〇、模板」脚本轮。**本文件 = 自定义周期唯一权威**（模板/四轴字段/例句映射/验算契约/防坑全文在此，SKILL.md 只留路由指针）；trigger-types.md timerEvent 节仅保留参数总表/示例 JSON/陷阱增量，不再全文重复本文件内容。

**唯一生效路径**：`build_process_json` 后 **save 前手工并入 `pj['attr']`** 四轴字段 → generateExecTime 验算（含 dayValue=5 的组合除外）→ `times` 回填 → save+deploy → 回读断言（timeCycle==custom + 各轴字段 + beginDateStr）。壳命名=「定时触发流程-<周期实名复合名>」；用户给了名则用用户的。

## 〇、完整可抄模板（改 ①–⑨ 常量后 1 次 py 跑完）

含执行节点 → 在 config.`nodes` 里填，骨架**按动作选**：①扫描批改（get_more→data_update 批量改/新增）= 照抄 `timer_job_runner.py` `cmd_scan` 的 get_more/data_update 变异段（E2 契约：`du.attr.formTableSourceTaskId/formTableSourceGetDataType/formTableId` 指源 getMore、ftl 的 getMore 条目 `isSubStart=True`，复用 `insert_fns`/`relabel_levels`）；②有/无记录分支通知 = 照抄 `cmd_check`（get_one + emptyAction=3 + databranch + msg，gotchas #66）；③多条记录逐行发消息必须 callActivity 子流程（gotchas #57）。复用函数直接 `import timer_job_runner as tjr`；**禁止整文件 Read runner**——`grep -n "^def cmd_"` 定行号后 offset/limit 只读命中节（gotchas #71）。验算步骤已内联在脚本里，禁止拆成两轮 py。实测全链产物（本组合+执行节点合一，2026-09-09 二次实证）：`订单超时自动处理-奇数月每10天` flow=`2097615109882576898`——function(-24H)→get_more→data_update，条件 支付状态=eq:未付款 + 下单时间=le_fn:-24H、更新 支付状态=已超时，一次 py save+deploy+回读全通过。

```python
# -*- coding: utf-8 -*-
import sys, time, json, requests
sys.path.insert(0, r'<skill_base_dir>\scripts')
import timer_job_runner as tjr          # 复用 back() 回读（先看 cmd_check 调用点再传参，gotchas #66）
from miniflow_creator import save_flow, deploy_flow, build_process_json

API, TOKEN = '<api_base>', '<token>'          # ①-② 凭证：按 SKILL「凭证」节取
TENANT, APP = '<租户id>', '<lowAppId>'        # ③-④ 目标租户与所属应用
NAME = '<流程名，壳=定时触发流程-<周期实名>>'    # ⑤
BEGIN = '<最近一次目标时刻，如 2026-09-10 09:00>' # ⑥ 字符串形态；分钟位=触发分钟
WEEK = ['MON']                                # ⑦ 按周触发填这里（MON..SUN）；改按日/月组合见第一节字段表
HOUR = [9]                                    # ⑧ 固定整点（多点并列数组元素）
MONTHS, MONTH_TYPE = [], 1                    # ⑨ 月筛选：默认每月(type1)；指定月=type2 + MONTHS=['1'..'12'] **字符串数组**
h = {'X-Access-Token': TOKEN, 'X-Tenant-Id': str(TENANT), 'X-Low-App-ID': str(APP)}
lst = requests.get(f'{API}/act/process/extActProcess/list', headers=h,
                   params={'pageNo': 1, 'pageSize': 100}, timeout=30).json()
names = [x.get('processName') for x in ((lst.get('result') or {}).get('records') or [])]
assert NAME not in names, f'同名流程已存在: {NAME}'

ts = int(time.time() * 1000)
cfg = {'processName': NAME, 'processKey': f'process{ts}', 'processType': 'oa',
       'lowAppId': APP, 'tenantId': str(TENANT), 'startType': 'timerEvent',
       'beginDateStr': BEGIN, 'timeCycleName': '自定义', 'startTaskId': f'task{ts}000',
       'nodes': []}                          # ← 执行节点填这里（扫描/通知抄 cmd_check 骨架）
pj = build_process_json(cfg)
ra = pj['attr']
ra.update({'beginDateStr': BEGIN, 'timeCycleName': '自定义', 'timeCycle': 'custom',
           'hourType': 3, 'hourValues': HOUR, 'hourValueMin': 0, 'hourValueMax': 23,
           'dayOrWeekType': 2, 'dayValue': 1, 'dayValues': [], 'weekValue': WEEK,
           'monthType': MONTH_TYPE, 'monthValues': MONTHS})
#   组合形态按第一节四轴表改：按日 dayOrWeekType1+固定号 dayValue3+dayValues / 每N天 dayValue4+Min起点/Max步长 /
#   月末 dayValue5 / 周几 dayOrWeekType2+weekValue / 指定月 monthType2+monthValues(字符串数组)
ra.setdefault('conditionFields', []); ra.setdefault('startCondition', [])
ra.setdefault('endDateStr', None); ra['times'] = []

# —— generateExecTime 验算（契约见第三节；⛔ 含 dayValue=5 月末的组合跳过本段，直接 save）——
form = {'beginDateStr': BEGIN, 'timeCycleName': '自定义', 'timeCycle': 'custom',
        'hourType': '3', 'hourValueMin': '0', 'hourValueMax': '23',
        'dayOrWeekType': '2', 'dayValue': '1', 'monthType': str(MONTH_TYPE)}
for v in HOUR: form.setdefault('hourValues', []).append(str(v))
for v in WEEK: form.setdefault('weekValue', []).append(v)
for v in MONTHS: form.setdefault('monthValues', []).append(v)
g = requests.post(f'{API}/act/designer/miniDesFlow/api/generateExecTime',
                  headers={'X-Access-Token': TOKEN, 'X-Tenant-Id': str(TENANT), 'X-Low-App-ID': str(APP)},
                  data=form, timeout=30).json()
obj = g.get('obj')
assert isinstance(obj, list) and len(obj) >= 7, json.dumps(g, ensure_ascii=False)[:300]
#   心算期望（首跑跨年！见第三节）后自行断言 obj 前 N 次，如 obj[:N] == ['YYYY-MM-DD HH:mm:ss', ...]
ra['times'] = obj

mcfg = {k: cfg[k] for k in ('processName', 'processKey', 'processType', 'lowAppId', 'tenantId', 'startType')}
res = save_flow(API, TOKEN, mcfg, pj)
assert res.get('success'), res
fid = res['result']['id']
d = deploy_flow(API, TOKEN, fid)
assert isinstance(d, dict) and d.get('success'), d
rp = tjr.back(API, TOKEN, fid)                # 高危回读：custom 组合字段
pjc = rp.get('processJson') or rp
pjc = pjc if isinstance(pjc, dict) else json.loads(pjc)
a = pjc.get('attr') or {}
assert a.get('timeCycle') == 'custom' and a.get('weekValue') == WEEK \
    and a.get('hourValues') == HOUR and a.get('monthValues') == MONTHS \
    and a.get('beginDateStr') == BEGIN, a
print(f'✅ {NAME}({fid}) | {BEGIN} 起 周{WEEK} 时{HOUR} 月{MONTHS if MONTH_TYPE == 2 else "每月"}')
```

## 一、attr 四轴字段速查

**月轴（月份筛选）**：`monthType=1` 每月都触发（`monthValues=[]`）；`monthType=2` 指定月——⛔ **`monthValues` 必须字符串数组** `["1".."12"]`（整数数组能 save、引擎也命中，但设计器面板形态错——2026-09 用户 UI 纠正）。口语映射：上半年=`["1","2","3","4","5","6"]`、下半年=`["7","8","9","10","11","12"]`、奇数月=`["1","3","5","7","9","11"]`、偶数月=`["2","4","6","8","10","12"]`、季度末月=`["3","6","9","12"]`；指定月可任意并列。

**日/周轴（`dayOrWeekType` 二选一）**：
- 按日 `dayOrWeekType=1`：
  - `dayValue=1` 每天；`dayValue=2` 范围（语义未见实测，勿臆造用法）
  - `dayValue=3` 固定号：`dayValues=["15"]`（每月15号）；**真固定号多值列表合法**（每月1、3、5号 = `dayValues=["1","3","5"]`）——⛔ **落库必须字符串数组（UI 保存形态；整数数组能 save、generateExecTime 预览也算得出，但设计器绑定错/显示未选中，2026-09-10 用户 UI 手工修复「每年上半年每月1、3、5号」后回读比对实证，与 monthValues 同律）**；数值只收 1-31（32→空结果、99→被忽略，**无真·L/月末写法**，gotchas #68）；**整数形态已落库可 API 外科改写修复**（queryById→仅改 attr.dayValues 为字符串数组→save+deploy，2026-09-10 实测，不必等用户 UI 手工）；⛔ **按日组合回读断言必须比对 dayValues 项**——模板断言只断 weekValue，照抄会漏断整数形态（2026-09-10 实测漏断）
  - `dayValue=4` 增量型：`dayValueMin=起点` + `dayValueMax=步长` + `dayValues=[]`（"从1号起每隔10天"=Min1/Max10）——⛔ 写成 `dayValue3+dayValues=[1,11,21]` 固定列表 = 用户判定错误
  - `dayValue=5` 每月最后一天（月末），不填 dayValues
- 按星期 `dayOrWeekType=2`：`weekValue=['MON'..'SUN']` + `dayValue=1` + `dayValues=[]`；多周几并列（周一到周五=`['MON','TUE','WED','THU','FRI']`）

**时轴**：`hourType=3` 固定整点 `hourValues=[9]`（多点并列数组元素即可；hourType=3 伴随的 `hourValueMin=0/Max=23` 保留默认勿臆造）；`hourType=2`=**小时范围触发**：`hourValueMin=起点`~`hourValueMax=终点` 每小时一次、`hourValues=[]`（「每天2点到5点」=min2/max5，2026-09-10 空壳实测首例，见 §二）；⛔ `hourType=1` = **每小时都触发**（UI 自定义面板小时下拉默认值——只改日/月没显式设小时就回读 hourType1 每小时跑，大坑）。

**分钟位**：一律取 `beginDateStr` 的分钟（hourValues=[0] 时 begin 写 `"…00:30"` → 00:30；写 09:00 丢分钟成 00:00）。

## 二、需求例句 → attr 映射（已验证行为准）

| 用户原话 | monthType+monthValues | 日/周字段 | hour | 验算/首跑 | 实测产物 |
|---------|----------------------|----------|------|-----------|---------|
| 每周一 09:00 | 1+[] | dayOrWeekType2+weekValue=["MON"] | hourType3+[9] | 常规 | 上周订单周报提醒 `2097588261299617794`（含执行节点） |
| 每年上半年最后一天 09:00 | 2+["1".."6"] | dayOrWeekType1+dayValue=5 | hourType3+[9]（hour 取开始时间的小时） | ⛔ 禁验算（dayValue5 预览缺陷） | 定时触发流程-每年上半年最后一天 `2097598817473593346` |
| 奇数月、从1号起每10天 23:00 | 2+["1","3","5","7","9","11"] | dayOrWeekType1+dayValue4+dayValueMin=1+dayValueMax=10+dayValues=[] | hourType3+[23] | obj=09-11/09-21/11-01/11-11/11-21…全23:00 | 订单超时自动处理-奇数月每10天 `2097615109882576898`（2026-09-09 重建，含执行节点全链；旧 `2097595322318127105` 用户 UI 定稿版已删） |
| **每年上半年(1-6月)每周五 09:00** | 2+["1".."6"] | dayOrWeekType2+weekValue=["FRI"] | hourType3+[9] | **obj=2027-01-01 起每周五 09:00（跨年，见三）** | 定时触发流程-每年上半年每周五 `2097599236161601539`（2026-09-10 实测，指定月×周几首例） |
| **每年上半年(1-6月) 每月1、3、5号 09:00** | 2+["1".."6"] | dayOrWeekType1+dayValue3+**dayValues=["1","3","5"]**（⛔ 字符串数组，整数=绑定错） | hourType3+[9] | obj=2027-01-01/01-03/01-05/02-01…（跨年） | 定时触发流程-每年上半年每月1、3、5号 `2097615073585070082`（用户 UI 修复定稿） |
| 每年上半年(1-6月)每月1号 09:00 | 2+["1".."6"] | dayOrWeekType1+dayValue3+dayValues=["1"]（⛔ 字符串数组同律） | hourType3+[9] | obj=2027-01-01/02-01/…/06-01 09:00（跨年，见三） | 定时触发流程-每年上半年每月1号 `2097615164240756738`（2026-09-10 实测；初建整数[1] 已 API 外科改写修复，见 §一） |
| 每月15号（固定号） | 1+[] | dayOrWeekType1+dayValue3+dayValues=["15"] | hourType3+[…] | dayValue3 可验算 | — |
| **每天 2 点到 5 点（小时范围，每小时一次）** | 1+[] | dayOrWeekType1+dayValue1（每天）+dayValues=[] | **hourType=2 范围**+hourValueMin=2+hourValueMax=5（hourValues=[]） | obj=09-11 02:00/03:00/04:00/05:00 + 09-12 02:00…（begin 09:00 当天窗口已过→首跑次日） | 定时触发流程-每天2点到5点 `2097619790906195970`（2026-09-10 空壳实测，hourType=2 范围首例） |
| 周一到周五（8 实名"6"同义） | 1+[] | dayOrWeekType2+weekValue=[MON,TUE,WED,THU,FRI] | hourType3+[…] | 常规 | — |

组合规则：**月轴 × (日轴|周轴) × 时轴**自由笛卡尔，一天一条流程；⛔ 同一组合能一条表达（含 固定月×月末）时**禁止拆两条**。

命名：壳=「定时触发流程-<周期实名复合名>」（应用内已有：每月1号/每周三/周一到周五/每月1、3、5号/每年上半年最后一天/每年上半年每周五/每年上半年每月1号；用户给了名则用用户的）。

## 三、generateExecTime 验算（custom 落库前契约，2026-09-10 两轮试错定稿）

`POST /act/designer/miniDesFlow/api/generateExecTime`；headers 带 X-Access-Token+X-Tenant-Id（可加 X-Low-App-ID）。form 传参 **Spring 绑定形态**：Integer[]/String[] 字段=**重复参数**（`hourValues=9`、`dayValues=1&dayValues=11`、`weekValue=FRI`、`monthValues=1&monthValues=2`）——⛔ 传 JSON 串报 500「Failed to convert…Integer[]」；标量（beginDateStr/hourType/dayValue/dayValueMin/Max/monthType…）字符串传；dict/复杂对象勿传。

- 成功响应**顶层 `obj`** = 未来 7 次 `"yyyy-MM-dd HH:mm:ss"`（不是 result.times）
- 用法：**心算期望 → 断言 obj 前 N 次一致 → `ra['times']=obj` 回填 → save+deploy → 回读断言**（timeCycle==custom、各轴字段、beginDateStr）
- **跨年心算（2026-09-10 实测新增）**：begin 落在不满足月筛选的时段时，首跑推到次年——「2026-09-10 09:00 起、每年1-6月每周五」首跑 = **2027-01-01 09:00**（2027-01-01 恰逢周五），后续每周五至 6 月底、次年 1 月再续。心算期望从「≥begin 的下一个命中时刻」逐次推，**别只盯当年**；月轴严格跳过非目标月
- ⛔ **例外=含 `dayValue=5`（每月最后一天）的组合跳过验算**：预览算例把月末算成每月30号、2月不显示，个别月组（如 [1,2]）直接 500 `Index: 2, Size: 2`——预览缺陷；此类校验=save+deploy+回读断言（gotchas #68），勿因预览报错/时间怪而拆条或改需求

## 四、口语歧义与防坑（2026-09-10 教训固化，gotchas #66-68）

1. **歧义先确认再建**：上半月≠上半年、每月最后一天≠固定号、每隔N天≠固定列表、工作日≠周一到周五（周六补班等）。语义不确定 → 建前同一次提问请用户一句话/UI 截图确认，**禁止先探测引擎表达力**（语义错时探测全白耗）。
2. **用户反驳方案（"不用拆/一条就行"）= 语义读错强信号** → 回需求词重读并确认，不是辩引擎能力。
3. `beginDateStr` 必须**字符串**形态（时间戳丢分钟位），分钟位即触发分钟。
4. UI 小时默认 hourType1=每小时 → 有目标小时必须显式 `hourType3+hourValues`。
5. monthType=2 严格跳过非目标月 → 心算命中时刻要**跨年**（见三）。
6. 组合正确性唯一校验 = generateExecTime（可用组合）+ save+deploy + 回读；禁止考古扫存量流程/反编译前端（SKILL.md 执行加速 #7/#62）。
