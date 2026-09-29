# -*- coding: utf-8 -*-
"""端到端冒烟测试：造单 → 触发流程 → 回读断言 → 按记录 id 清理（零残留）。

为什么要有它：`save` / `deploy` / `check_node_contract` / `app_audit` **全是结构检查** ——
「流程跑起来账对不对」它们一条都看不见。2026-09-21 进销存实测：结构闸门全绿的应用里藏着
「第一笔入库丢账」「公式值累加把库存冲成 0」「同事件两条流程只跑一条」…… 全靠造单回读才暴露。
凡是带**台账 / 记账 / 回写**类流程的应用，交付前必须跑一遍本脚本。

    python smoke_flows.py --api-base URL --token T --tenant-id N --app-id A --config smoke.py [--flows flows.py]
                          [--only 用例名,用例名] [--keep] [--include-approval] [--allow-skip]

配置（smoke.py，只写中文名；字典/选项字段写**显示文案**，脚本换成落库值）：

    MARK = 'SMK'                                   # 测试数据标记：出现在某个文本字段里，清理兜底靠它
    BASE = {                                       # 基础数据：别名 → (表, {字段: 值})
        'wh': ('仓库信息', {'仓库名称': 'SMK仓'}),
        'p1': ('产品信息', {'产品名称': 'SMK产品', '成本单价/元': 10}),
    }
    CASES = [{
        'name': '其他入库单-确认',
        'doc': ('其他入库单', {'入库类型': '期初入库', '入库仓库': '@wh', '仓库编码': '@wh.仓库编码',
                              '入库确认': '否', '库存已记账': '否'}),
        'rows': [('其他入库产品明细', '其他入库单', '其他入库产品明细',      # (明细表, 明细回指父单的字段, 父单上的明细字段)
                  {'产品信息': '@p1', '产品编码': '@p1.产品编码', '本次入库数量': 10})],
        'trigger': 'update',                        # update=建好后改 confirm 字段触发；add=带着明细一次新增触发
        'confirm': {'入库确认': '是'},
        'wait': 20,
        'expect': [('库存实时统计', {'仓库编码': '@wh.仓库编码', '产品编码': '@p1.产品编码'},
                    {'其他入库数量': 10, '当前库存数量': 10})],   # 期望里写 {'#': 1} = 断言命中行数
        # 'alias': 'rk1',                          # 可选：给本单据起别名，后面的用例用 '@rk1' 引用
    }]

取值写法：`'@别名'` = 那条记录（关联记录字段自动包成 `[id]`）；`'@别名.字段'` = 那条记录的字段值；
`'@doc'` / `'@doc.字段'` = 本用例的单据；`'$now'` = 当前毫秒时间戳。
expect 的期望值另可写 `'$today'`（日期是今天，毫秒/字符串都认）、`'$notempty'`（有值即可）、`'$empty'`（为空）。
用例按顺序跑、共享 BASE 与前面用例建的数据
（所以「先入库 10 再出库 3 期望库存 7」可以直接写成两个用例）。

审批流：用例写 `'approval': {'node': '部门经理审批', 'approve_all': True}` —— 断言落点 + 任务在当前用户待办，
可选逐个办结后再跑 expect 验回写；收尾先 `/act/processInstance/clear` 清本次实例、再删记录。
没写 approval 的「新增即进审批」表上的用例默认跳过（`--include-approval` 强跑），**有跳过时退出码 3**（`--allow-skip` 放行）。
按钮流：`'trigger': 'button:作废'`；'approval' 加 `'path': [...]` 断言办结经过的节点；expect 定位可写 `'@doc'`。完整配置说明见
`references/smoke-flows.md`。
"""
import argparse
import importlib.util
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from desform_lowapp_utils import init_lowapp, get_menus          # noqa: E402
from desform_utils import query_form                             # noqa: E402
from desform_data_utils import add_data, list_data, edit_data, delete_data   # noqa: E402


def log(m):
    print(m, flush=True)


class App(object):
    def __init__(self, app_id):
        self.forms = {}       # 表名 → code
        self.meta = {}        # 表名 → {字段名: {model,type,labels:{文案:值}}}
        for m in (get_menus(app_id).get('menuList') or []):
            if m.get('type') == 'form' and m.get('desformCode'):
                self.forms[m.get('menuName')] = m['desformCode']

    def fields(self, table):
        if table not in self.meta:
            if table not in self.forms:
                raise SystemExit('FAIL: 应用里没有工作表「%s」' % table)
            design = json.loads(query_form(self.forms[table])['desformDesignJson'])
            out = {}
            for w in _walk(design):
                name = w.get('name')
                if not name or w.get('type') in ('divider', 'card', 'tabs', 'grid') or name in out:
                    continue
                wo = w.get('options') or {}
                opts = wo.get('options')
                labels = {}
                if isinstance(opts, list):
                    for o in opts:
                        if isinstance(o, dict) and o.get('value') is not None:
                            labels[str(o.get('label') if o.get('label') is not None else o['value'])] = o['value']
                out[name] = {'model': w['model'], 'type': w['type'], 'labels': labels,
                             'showField': wo.get('showField'), 'multiple': bool(wo.get('multiple'))}
            self.meta[table] = out
        return self.meta[table]

    def source_labels(self, showField):
        """他表字段（link-field）带出的字典值：本控件没有 options，要顺 showField 找源控件。
        不翻的话写进去的是文案、库里存的是序号串，断言恒假（2026-09-22 进销存 R2 对账明细「账向」）。"""
        if not showField:
            return {}
        if getattr(self, '_by_model', None) is None:
            self._by_model = {}
            for t in list(self.forms):
                try:
                    for meta in self.fields(t).values():
                        if meta.get('labels'):
                            self._by_model.setdefault(meta['model'], meta['labels'])
                except SystemExit:
                    continue
        return self._by_model.get(showField) or {}

    def model(self, table, name):
        f = self.fields(table).get(name)
        if not f:
            raise SystemExit('FAIL: 表「%s」没有字段「%s」' % (table, name))
        return f

    def rows(self, table):
        out, page = [], 1
        while True:
            r = list_data(self.forms[table], page=page, size=200)
            recs = r.get('records') or []
            out += recs
            if len(out) >= (r.get('total') or 0) or not recs:
                return out
            page += 1

    def row(self, table, rid):
        for r in self.rows(table):
            if r['id'] == rid:
                return r['desformData']
        return None


def _walk(n):
    if isinstance(n, dict):
        if n.get('type') and n.get('model'):
            yield n
        for v in n.values():
            for x in _walk(v):
                yield x
    elif isinstance(n, list):
        for i in n:
            for x in _walk(i):
                yield x


class Proc(object):
    """审批流运行时验收（2026-09-24 一句话建应用：三个应用都只能手写脚本才验得了审批）。

    · 单据 ↔ 实例：`myApplyProcessList` 没有单据 id（`bpmBizTitle` 有时是「表名【标题】」、有时为空），
      所以按「触发前后实例 id 做差」+ 本应用流程 key（`processDefinitionId` 冒号前）对应。
      列表按发起时间倒序，取头几页就够；用例串行跑，差出来的就是本用例触发的。
    · 清理：先 `GET /act/processInstance/clear`（界面「清空流程」），不行再 `processComplete` 逐个办结。
      删记录**不会**结束实例 —— 顺序反了会在办理人待办里留下打开是空白表单的孤儿任务。
    """

    def __init__(self, app_id):
        from desform_utils import api_request
        self.req = api_request
        r = api_request('/act/process/extActProcess/list',
                        params={'pageNo': 1, 'pageSize': 500, 'lowAppId': app_id}, method='GET')
        recs = ((r or {}).get('result') or {}).get('records') or []
        self.keys = {x.get('processKey'): x.get('processName') for x in recs
                     if str(x.get('lowAppId')) == str(app_id) and x.get('processKey')}
        self.seen = set(i['processInstanceId'] for i in self.mine())
        self.created = []           # 本次运行触发的实例 id（清理用）
        self.checked = set()        # 已被某个 approval 断言认领的实例
        self.path = {}              # 实例 id → approve_all 办结经过的节点名（按顺序）

    def key(self, inst):
        return (inst.get('processDefinitionId') or '').split(':')[0]

    def mine(self, pages=3):
        out = []
        for pg in range(1, pages + 1):
            r = self.req('/act/task/myApplyProcessList',
                         params={'pageNo': pg, 'pageSize': 100}, method='GET')
            recs = ((r or {}).get('result') or {}).get('records') or []
            out += [x for x in recs if self.key(x) in self.keys]
            if len(recs) < 100:
                break
        return out

    def new(self):
        """自上次调用以来本应用新起的实例（记进 created，收尾清理）。"""
        fresh = [i for i in self.mine() if i['processInstanceId'] not in self.seen]
        for i in fresh:
            self.seen.add(i['processInstanceId'])
            self.created.append(i['processInstanceId'])
        return fresh

    def todo(self, pid):
        r = self.req('/act/task/myTodo', params={'pageNo': 1, 'pageSize': 500}, method='GET')
        return [x for x in (((r or {}).get('result') or {}).get('records') or [])
                if x.get('processInstanceId') == pid]

    def open_tasks(self, pid):
        r = self.req('/act/task/processHistoryList', params={'processInstanceId': pid}, method='GET')
        recs = ((r or {}).get('result') or {}).get('records') or []
        return [x for x in recs if x.get('id') != 'start' and not x.get('endTime')]

    def approve_all(self, pid, rounds=6, reject=()):
        """把实例上的审批任务逐个按「通过」办结，直到实例结束（用来验审批通过后的回写）。
        reject：这些节点按「不同意」办结（审批结果分支走否决支，flow_dsl.approve_result）——
        办结时带 `approve_result_val=N`（后端 ExtActTaskCcServiceImpl 按它写 approve_result_<节点>）。

        返回 (是否结束, 说明)；办结经过的节点名按顺序记在 `self.path[pid]`（approval 的 'path' 断言用）。"""
        path = self.path.setdefault(pid, [])
        for _ in range(rounds):
            ts = self.open_tasks(pid)
            if not ts:
                # 没有待办 ≠ 结束：延时/定时这类非人工节点也没有任务（本机无执行器时会一直停着，engine-contract #18）。
                # 以实例的 endTime 为准（2026-09-24 CRM-速测16：卡在延时节点仍打印 ended）
                inst = next((i for i in self.mine(pages=1) if i.get('processInstanceId') == pid), None)
                if inst is not None and not inst.get('endTime'):
                    return False, '没有待办任务、但实例未结束（停在延时/定时等非人工节点？经过：%s）' % (' → '.join(path) or '无')
                return True, 'ended（经过：%s）' % (' → '.join(path) or '无')
            t = ts[0]
            info = self.req('/act/task/getProcessTaskTransInfo', params={'taskId': t['id']}, method='GET')
            trans = (((info or {}).get('result') or {}).get('transitionList') or [{}])
            r = self.req('/act/task/processComplete', data={
                'taskId': t['id'], 'nextnode': trans[0].get('nextnode'),
                'processModel': 1, 'reason': 'smoke_flows 自动审批',
                'approve_result_val': 'N' if t.get('name') in reject else 'Y'}, method='POST')
            if not (r or {}).get('success'):
                return False, '办结「%s」失败：%s' % (t.get('name'), (r or {}).get('message'))
            path.append(t.get('name'))
            time.sleep(2)
        return False, '办结 %d 轮后实例仍未结束' % rounds

    def clear(self, pid):
        why = ''
        try:
            r = self.req('/act/processInstance/clear', params={'processInstanceId': pid}, method='GET')
            if (r or {}).get('success'):
                return 'cleared'
            why = (r or {}).get('message')
        except Exception as ex:                  # noqa: BLE001
            why = str(ex)[:80]
        ok, msg = self.approve_all(pid)          # 退路：逐个办结
        return 'completed' if ok else 'FAIL(clear: %s; complete: %s)' % (why, msg)


ORG_ARRAY_TYPES = ('select-user', 'select-depart', 'select-depart-post', 'org-role')
_DATE_RE = __import__('re').compile(r'^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}(:\d{2})?)?$')


class Runner(object):
    def __init__(self, app, mark):
        self.app, self.mark = app, mark
        self.alias = {}       # 别名 → (表, id)
        self.made = {}        # 表 → [id]
        self.res = []
        self.failed_cases = []
        self.proc = None      # Proc：有 approval 用例（或 --include-approval）时才建
        self.pre = None       # 运行前各表已有记录 id（snapshot()）；清理只删运行中新出现的

    def snapshot(self):
        """记下运行前各表已有的记录。以前 expect 按条件命中的记录一律进清理名单 —— 库里已有的业务/保留数据
        碰巧满足条件就被物理删除（2026-09-24 任务-一句话6：保留的 8 条处理记录被删）。"""
        self.pre = {t: {r['id'] for r in self.app.rows(t)} for t in self.app.forms}

    # ---- 取值 ----
    def value(self, table, field, v):
        f = self.app.model(table, field)
        if isinstance(v, str) and v == '$now':
            return int(time.time() * 1000)
        # 多条关联一次挂多条：['@a', '@b'] 或 '@a,@b'（以前报「别名还没建」，考勤-速测19）
        if f['type'] == 'link-record':
            parts = v if isinstance(v, list) else (
                [x.strip() for x in v.split(',')] if isinstance(v, str) and ',' in v else None)
            if parts and all(isinstance(x, str) and x.startswith('@') and '.' not in x for x in parts):
                out = []
                for x in parts:
                    if x[1:] not in self.alias:
                        raise SystemExit('FAIL: 取值 %s：别名「%s」还没建' % (x, x[1:]))
                    out.append(self.alias[x[1:]][1])
                return out
        if isinstance(v, str) and v.startswith('@'):
            ref, _, sub = v[1:].partition('.')
            if ref not in self.alias:
                raise SystemExit('FAIL: 取值 %s：别名「%s」还没建（BASE 里没有，也不是 doc）' % (v, ref))
            tb, rid = self.alias[ref]
            if not sub:
                return [rid] if f['type'] == 'link-record' else rid
            if sub in ('id', '_id', '记录id'):
                # 把记录 id 写进文本字段（「线索池id」这类回查键；以前报「没有字段 id」并中止整轮，CRM-速测19）
                return [rid] if f['type'] == 'link-record' else rid
            return (self.app.row(tb, rid) or {}).get(self.app.model(tb, sub)['model'])
        if f['type'] == 'checkbox' or (f['type'] == 'select' and f.get('multiple')):
            # 多选：字符串数组（只选一项也是数组，desform-data-utils.md「控件落库格式」3）；
            # 以前写成裸串（2026-09-24 任务-一句话6 标签字段）
            parts = v if isinstance(v, list) else [x.strip() for x in str(v).split(',') if x.strip()]
            return [f['labels'].get(x, x) if isinstance(x, str) else x for x in parts]
        if isinstance(v, str) and f['labels'] and v in f['labels']:
            return f['labels'][v]                      # 字典 / 选项：文案 → 落库值
        if isinstance(v, str) and f['type'] == 'link-field' and not f['labels']:
            lb = self.app.source_labels(f.get('showField'))
            if v in lb:
                return lb[v]                           # 他表字段带出的字典值：顺 showField 翻
        if isinstance(v, str) and f['type'] == 'date' and _DATE_RE.match(v.strip()):
            # 日期控件存毫秒：'2026-10-31' / '2026-10-31 09:30' 按**本机本地时间**折成毫秒（与页面一致；
            # 以前原样写字符串，同列混格式，2026-09-24 任务-一句话8）
            fmt = {10: '%Y-%m-%d', 16: '%Y-%m-%d %H:%M', 19: '%Y-%m-%d %H:%M:%S'}[len(v.strip())]
            return int(time.mktime(time.strptime(v.strip(), fmt)) * 1000)
        if isinstance(v, str) and f['type'] in ORG_ARRAY_TYPES:
            # 选人/选部门/岗位/角色**单选也存数组**（desform-data-utils.md「控件落库格式」第 1 节）；
            # 以前原样写裸串，保留数据在页面上显示不出人（2026-09-24 任务管理返工 fix_userfmt）
            return [x.strip() for x in v.split(',') if x.strip()]
        return v

    def payload(self, table, kv):
        return {self.app.model(table, k)['model']: self.value(table, k, v) for k, v in kv.items()}

    def new(self, table, kv, alias=None):
        body = self.payload(table, kv)
        rid = add_data(self.app.forms[table], body)['id']
        self.made.setdefault(table, []).append(rid)
        if alias:
            self.alias[alias] = (table, rid)
        self.note_overrides(table, rid, kv, body)
        return rid

    def note_overrides(self, table, rid, kv, body):
        """回读刚新增的记录：传入值被改掉的打 NOTE（不判失败）。

        服务端「取关联字段」默认值会覆盖 API 传入值（engine-contract #17），新增触发的流程也可能改写字段；
        以前不回读 → 冒烟全绿、保留数据静默写错（2026-09-24 担保-一句话5：担保费率传 1.8 落成 2.0）。"""
        row = self.app.row(table, rid) or {}
        for k in kv:
            f = self.app.model(table, k)
            # 他表字段也要比：传入值被服务端按关联记录改写时，依赖它的审批/断言会莫名失败（2026-09-24 销售-速测16 G）
            # 自动编号也比：传了值会被改写（CRM-速测16）
            got, want = row.get(f['model']), body.get(f['model'])
            if want in (None, '') or _same(got, want):
                continue
            if f['type'] in ('formula', 'summary', 'summary-date'):
                # 公式/汇总服务端会按明细重算、覆盖传入值（传 1000 落库 300，进销存-速测18 S6）：别传，按重算后的口径写期望
                log('  NOTE: %s.%s 是%s，传入 %r 被服务端重算成 %r —— 别给它传值，期望按重算结果写'
                    % (table, k, '公式' if f['type'] == 'formula' else '汇总', want, got))
            else:
                log('  NOTE: %s.%s 传入 %r，落库 %r —— 被默认值/流程改写？造保留数据时要核对'
                    % (table, k, want, got))
        # 没传的选人/选部门/岗位：服务端按「当前登录人/部门」默认值补的是**裸字符串**（平台后端
        # DesignFormDataServiceBaseImpl.getDefaultComposeVal 对 #D:CURRENT# 直接 return 字符串），同列与数组混存
        # （2026-09-24 担保-一句话6 / 任务-一句话7）。页面新增走前端默认值不受影响；这里只提示，造保留数据时显式传这些字段
        for name, f in self.app.fields(table).items():
            if name in kv or f['type'] not in ORG_ARRAY_TYPES:
                continue
            got = row.get(f['model'])
            if isinstance(got, str) and got:
                log('  NOTE: %s.%s 没传值，服务端默认值落成字符串 %r（应为数组）—— 造保留数据时显式传它'
                    % (table, name, got))

    # ---- 用例 ----
    def run_case(self, c):
        log('── %s' % c['name'])
        if self.proc:
            self.proc.new()                            # 吸收本用例之前起的实例，下面差出来的只属于本用例
            self.case_base = set(self.proc.created)    # 基线：之前用例留下的（含未办结的）实例不算本用例
        dt, dkv = c['doc']
        trigger = c.get('trigger') or 'update'
        button = None
        if isinstance(trigger, dict) and trigger.get('button'):
            button = trigger['button']
        elif isinstance(trigger, str) and trigger.startswith('button:'):
            button = trigger.split(':', 1)[1].strip()
        if button:                                     # 按钮流：先建单（有 confirm 照改），再点按钮
            trigger = 'update'
        if trigger == 'delete' and isinstance(dkv, str):
            raise SystemExit("FAIL: 用例「%s」trigger='delete' 要先新建再删，doc 不能写别名 %s" % (c['name'], dkv))
        if trigger == 'add' and isinstance(dkv, str):
            raise SystemExit("FAIL: 用例「%s」trigger='add' 要新建单据，doc 不能写别名 %s" % (c['name'], dkv))
        if trigger == 'add':                           # 明细先建，单据**带着明细**一次新增（触发那一刻明细就得在）
            link = {}
            for (rt, _back, parent_field, rkv) in c.get('rows') or []:
                link.setdefault(parent_field, []).append(self.new(rt, rkv))
            body = self.payload(dt, dkv)
            for pf, ids in link.items():
                body[self.app.model(dt, pf)['model']] = ids
            did = add_data(self.app.forms[dt], body)['id']
            self.made.setdefault(dt, []).append(did)
            self.alias['doc'] = (dt, did)
            self.note_overrides(dt, did, dkv, body)
        elif isinstance(dkv, str) and dkv.startswith('@'):
            # 复用前面用例建的单据（'doc': ('Bug', '@bug1')）：同一条记录连续点多个按钮走完生命周期
            # （以前每个用例都新建单据，「确认→解决→关闭→激活」只能自写脚本，2026-09-24 萌萌 Bug 版）
            ref = dkv[1:]
            if ref not in self.alias or self.alias[ref][0] != dt:
                raise SystemExit("FAIL: 用例「%s」的 doc %s：别名没建过或不是表「%s」的记录" % (c['name'], dkv, dt))
            did = self.alias[ref][1]
            self.alias['doc'] = (dt, did)
            if c.get('confirm'):
                full = dict(self.app.row(dt, did) or {})
                full.update(self.payload(dt, c['confirm']))
                edit_data(self.app.forms[dt], did, full)
        else:
            did = self.new(dt, dkv, alias='doc')
            link = {}
            for (rt, back, parent_field, rkv) in c.get('rows') or []:
                rid = self.new(rt, dict(rkv, **{back: '@doc'}))
                link.setdefault(parent_field, []).append(rid)
            full = dict(self.app.row(dt, did) or {})   # edit 是全量覆盖：取整行再改
            for pf, ids in link.items():
                full[self.app.model(dt, pf)['model']] = ids
            full.update(self.payload(dt, c.get('confirm') or {}))
            edit_data(self.app.forms[dt], did, full)
            if trigger == 'delete':
                # 删除触发：建好（明细也挂上）后删掉本单，再按 expect 验删除流程的回写（销售-速测19：删除流程只能手写脚本测）
                if self.proc:
                    self.proc.new()
                    self.case_base = set(self.proc.created)
                delete_data(self.app.forms[dt], did)
                if did in self.made.get(dt, []):
                    self.made[dt].remove(did)
                log('  [OK] 已删除本单 %s（触发删除流程）' % did)
        if c.get('alias'):                             # 让后面的用例能用 '@别名' 引用这张单据
            self.alias[c['alias']] = (dt, did)
        if button:
            if self.proc:
                self.proc.new()                        # 建单触发的实例先吸收掉，按钮起的实例单独认
                self.case_base = set(self.proc.created)   # 并入基线：审批断言只认按钮起的实例（review #5）
            if not self.click(dt, did, button, c.get('button_params')):
                self.res.append(False)
                self.failed_cases.append(c['name'])
                return
        if c.get('approval'):
            self.check_approval(c)
        self.wait_expect(c)

    def click(self, table, did, label, params=None):
        """点自定义按钮：按钮名 → `/desform/button/list` 里同表同名按钮（`label`）的 processId →
        `POST /act/designer/miniDesFlow/api/buttonStartProcess`，五个参数都走 **query**
        （放 body 报 `Required request parameter 'processId'`，miniflow gotchas #109）。
        ⚠️ 按钮的显示条件（conditionList）接口不校验 —— 冒烟点得动 ≠ 界面上看得见，显示条件另看。"""
        from desform_utils import api_request
        code = self.app.forms[table]
        r = api_request('/desform/button/list', params={'designFormCode': code}, method='GET') or {}
        res = r.get('result')
        btns = (res.get('records') if isinstance(res, dict) else res) or []
        hit = [b for b in btns if b.get('label') == label]
        if not hit or not hit[0].get('processId'):
            log('  [FAIL] 按钮「%s」：表「%s」上没有这个按钮（或没绑流程）；现有：%s'
                % (label, table, '、'.join(str(b.get('label')) for b in btns) or '无'))
            return False
        if getattr(self, '_me', None) is None:
            u = api_request('/sys/user/getUserInfo', method='GET') or {}
            self._me = (((u.get('result') or {}).get('userInfo') or {}).get('username')) or 'admin'
        q = {'processId': hit[0]['processId'], 'dataId': did, 'formKey': code,
             'applyUserId': self._me,
             'inputParams': json.dumps([{'field': k, 'value': v} for k, v in (params or {}).items()],
                                       ensure_ascii=False)}
        r = api_request('/act/designer/miniDesFlow/api/buttonStartProcess', params=q, method='POST') or {}
        ok = bool(r.get('success'))
        log('  [%s] 点按钮「%s」→ %s' % ('OK' if ok else 'FAIL', label, (r.get('message') or '')[:120]))
        return ok

    def check_approval(self, c):
        """'approval': {'node': '部门经理审批'} 或 {'nodes': [...]}；可选 'flow'（流程名，多条流程同时起时收窄）、
        'todo': False（不查当前用户待办）、'approve_all': True（断言后逐个办结审批，再跑 expect 验通过后的回写）、
        'reject': ['节点名']（这些节点点「不同意」，验审批结果分支的否决支）、'wait'（秒，默认 20）。"""
        ap = c['approval']
        want = [ap['node']] if ap.get('node') else list(ap.get('nodes') or [])
        if not want and ap.get('path'):
            # 只写了 path：落点 = 路径第一个节点。以前 want 为空 → 期望落点「」必败且不逐级办结，
            # 依赖这单的后续用例级联失败（2026-09-24 申报-一句话5 首跑 6 败）
            want = [ap['path'][0]]
        if not want:
            raise SystemExit("FAIL: 用例「%s」的 approval 缺 'node'/'nodes'/'path'，断言不了落点" % c['name'])
        deadline = time.time() + float(ap.get('wait') or 20)
        hit, got = None, []
        while True:
            self.proc.new()
            got = []
            for i in self.proc.mine(pages=1):
                pid = i['processInstanceId']
                if (pid not in self.proc.created or pid in self.proc.checked
                        or pid in getattr(self, 'case_base', ())):
                    continue
                fname = self.proc.keys.get(self.proc.key(i))
                if ap.get('flow') and fname != ap['flow']:
                    continue
                got.append((fname, i.get('currentTaskName')))
                if i.get('currentTaskName') in want and hit is None:
                    hit = i
            if hit is not None or time.time() >= deadline:
                break
            time.sleep(3)
        ok = hit is not None
        msg = '审批落点：期望停在「%s」；本用例新起实例（流程, 当前节点）=%s' % ('/'.join(want), got or '无')
        if ok and ap.get('todo', True):
            td = [t.get('taskName') for t in self.proc.todo(hit['processInstanceId'])]
            ok = hit.get('currentTaskName') in td
            msg += '；当前用户待办=%s' % (td or '无（任务没派到当前 token 用户 —— 查审批人配置）')
        self.res.append(ok)
        log('  [%s] %s' % ('PASS' if ok else 'FAIL', msg))
        if not ok:
            self.failed_cases.append(c['name'])
            return
        self.proc.checked.add(hit['processInstanceId'])
        if ap.get('approve_all') or ap.get('path') or ap.get('reject'):    # path / reject 都要逐个办结才生效
            pid = hit['processInstanceId']
            done, why = self.proc.approve_all(pid, reject=set(ap.get('reject') or ()))
            self.res.append(done)
            log('  [%s] 审批逐个办结 → %s' % ('PASS' if done else 'FAIL', why))
            if not done:
                self.failed_cases.append(c['name'])
            elif ap.get('path'):
                got = self.proc.path.get(pid) or []
                ok = got == list(ap['path'])
                self.res.append(ok)
                log('  [%s] 审批路径：期望 %s；实际 %s' % ('PASS' if ok else 'FAIL',
                                                        ' → '.join(ap['path']), ' → '.join(got) or '无'))
                if not ok:
                    self.failed_cases.append(c['name'])

    def wait_expect(self, c):
        deadline = time.time() + float(c.get('wait') or 20)
        last = []
        while True:
            last = [self.check_one(e) for e in c.get('expect') or []]
            if all(ok for ok, _ in last) or time.time() >= deadline:
                break
            time.sleep(3)
        for ok, msg in last:
            self.res.append(ok)
            log('  [%s] %s' % ('PASS' if ok else 'FAIL', msg))
        # 记下失败用例名，收尾时打出 --only 复跑命令（见 main() 末尾）
        if not all(ok for ok, _ in last):
            self.failed_cases.append(c['name'])

    def locate_ids(self, where):
        """`'@doc'` / `'@别名'` = 那条记录本身；`'@别名.关联字段'` = 那条记录的关联记录指向的记录。
        没有文本标题的表（代偿申请、放款登记…）不用再挑一个文本列放 MARK 来定位。"""
        ref, _, sub = where[1:].partition('.')
        if ref not in self.alias:
            raise SystemExit('FAIL: 定位 %s：别名「%s」还没建' % (where, ref))
        tb, rid = self.alias[ref]
        if not sub:
            return {rid}
        v = (self.app.row(tb, rid) or {}).get(self.app.model(tb, sub)['model'])
        if isinstance(v, str):
            v = [x for x in v.split(',') if x]
        return set(v or [])

    def check_one(self, e):
        table, where, want = e[0], e[1], e[2]
        if isinstance(where, str):
            if not where.startswith('@'):
                raise SystemExit("FAIL: expect 定位写成字符串时只能是 '@别名' / '@别名.关联字段'：%r" % where)
            ids = self.locate_ids(where)
            hits = [r for r in self.app.rows(table) if r['id'] in ids]
        else:
            wv = {self.app.model(table, k)['model']: self.value(table, k, v) for k, v in where.items()}
            hits = [r for r in self.app.rows(table)
                    if all(_same(r['desformData'].get(m), v) for m, v in wv.items())]
        for r in hits:                                 # 流程派生出来的记录也要清理（运行前就有的不算）
            if self.pre is not None and r['id'] in self.pre.get(table, ()):
                continue
            if r['id'] not in self.made.setdefault(table, []):
                self.made[table].append(r['id'])
        if '#' in want:                                # {'#': 1} = 断言命中行数
            n = want['#']
            if len(hits) != n:
                return False, '%s %s 行数：实际=%d 期望=%d' % (table, where, len(hits), n)
        if not hits:
            return (not [k for k in want if k != '#']), '%s %s：没有命中的记录' % (table, where)
        d, bad = hits[0]['desformData'], []
        for k, v in want.items():
            if k == '#':
                continue
            got = d.get(self.app.model(table, k)['model'])
            if isinstance(v, str) and v in _SPECIAL:
                if not _SPECIAL[v](got):
                    bad.append('%s 实际=%s 期望=%s' % (k, got, v))
                continue
            exp = self.value(table, k, v)
            if isinstance(v, str) and v.startswith('@') and exp in _EMPTY:
                # 引用解析出来是空：两边都空也「相等」，断言等于没做（2026-09-24 考勤-速测18 S11）
                bad.append('%s 期望值 %s 解析为空（被引用的记录上该字段没值）—— 断言无意义，'
                           '换一个有值的引用，或明确写 \'$empty\'' % (k, v))
                continue
            if not _same(got, exp):
                bad.append('%s 实际=%s 期望=%s' % (k, got, exp))
        return (not bad), '%s %s → %s' % (table, where, '；'.join(bad) if bad else
                                          '、'.join('%s=%s' % (k, v) for k, v in want.items()))

    # ---- 清理 ----
    def _marked(self, r):
        """记录是不是测试造的：只看真实文本列。`*_dictText` / `*_dictTextPrint` 是关联记录回指带来的
        标题文案，按它删会把被测试数据回指的**业务/预置记录**一起删掉（2026-09-22 CRM「销售阶段·进行中」被误删）"""
        return any(isinstance(v, str) and self.mark in v for k, v in (r.get('desformData') or {}).items()
                   if not k.endswith('_dictText') and not k.endswith('_dictTextPrint'))

    def cleanup(self):
        if not self.proc:
            log('OK:cleanup 本次没有跟踪流程实例（没有 approval 用例，也没加 --include-approval）')
        if self.proc:                                  # 先清实例，再删记录（顺序反了会留孤儿待办）
            self.proc.new()
            res = [(pid, self.proc.clear(pid)) for pid in dict.fromkeys(self.proc.created)]
            bad = [(p, r) for p, r in res if r.startswith('FAIL')]
            log('%s:cleanup 本次触发的流程实例 %d 个 → 清掉 %d 个%s' % (
                'OK' if not bad else 'WARN', len(res), len(res) - len(bad),
                ('；失败：' + '、'.join('%s %s' % x for x in bad[:5])) if bad else ''))
        n = 0
        # 「我」= 本次冒烟自己建过记录的账号（流程派生记录的创建人也是发起人本人）；
        # 运行中新出现、但不是「我」建的（同时有人在这个应用里录数据）一律不删（review #4）
        me = {_token_user()} - {None}
        for table in self.app.forms:                   # 兜底：带标记的派生记录 + 运行中新出现的记录
            for r in self.app.rows(table):
                fresh = (self.pre is not None and r['id'] not in self.pre.get(table, ())
                         and r.get('createBy') in me)
                if fresh and r['id'] not in self.made.setdefault(table, []):
                    # 流程派生、文本写死带不上标记的（以前每次残留、只报 WARN，2026-09-24 任务-一句话6）
                    self.made[table].append(r['id'])
                    log('  cleanup: 本次运行新出现 %s/%s（流程派生）' % (table, r['id']))
                    continue
                if self._marked(r) and not (self.pre is not None and r['id'] in self.pre.get(table, ())):
                    # 运行前就有的带标记记录（上次 --keep 保留的演示数据）也不碰（CRM-速测16：删了上轮保留的 8 条）
                    if r['id'] not in self.made.setdefault(table, []):
                        self.made[table].append(r['id'])
                        log('  cleanup: 兜底命中 %s/%s（文本列含「%s」）' % (table, r['id'], self.mark))
        # ⚠️ `/act/processInstance/clear` 会**连同业务记录一起删掉**（2026-09-24 实测），所以审批单
        # 到这里常常已经不在了：delete_data 不抛异常、只回 success=false —— 按回执计数，别把失败算成删除。
        gone = 0
        live = {t: {r['id'] for r in self.app.rows(t)} for t in self.made}
        for table, ids in self.made.items():
            for rid in dict.fromkeys(ids):
                if rid not in live.get(table, ()):
                    gone += 1
                    continue
                try:
                    r = delete_data(self.app.forms[table], rid, hard=True) or {}
                    if r.get('success'):
                        n += 1
                    else:
                        log('  WARN: 删除失败 %s %s %s' % (table, rid, (r.get('message') or '')[:80]))
                except Exception as ex:                # noqa: BLE001
                    log('  WARN: 删除失败 %s %s %s' % (table, rid, str(ex)[:80]))
        if gone:
            log('  cleanup: %d 条记录已随流程实例清理一并删除' % gone)
        left, nonempty, kept = [], [], 0
        for table in self.app.forms:
            rows = self.app.rows(table)
            pre = self.pre.get(table, set()) if self.pre is not None else set()
            new_rows = [r for r in rows if r['id'] not in pre]      # 运行前已有的（保留的演示数据）不算残留
            kept += len(rows) - len(new_rows)
            if new_rows:
                nonempty.append('%s=%d' % (table, len(new_rows)))
            for r in new_rows:
                if self._marked(r):
                    left.append('%s/%s' % (table, r['id']))
        log('OK:cleanup 删除 %d 条；带标记「%s」的残留 %d 条%s' % (n, self.mark, len(left),
                                                         ('：' + '、'.join(left[:8])) if left else ''))
        # ⚠️「带标记残留 0 条」**不等于**「没留垃圾」：只有系统字段的**空行**没有任何文本列，
        # 标记兜底扫不到。2026-09-23 进销存实测：`get_one empty=` 错位一格让子流程每跑一次就
        # 新建一条空行，冒烟一路报「残留 0 条」，实际攒了 16 条。
        # 所以收尾**再报一遍全表行数** —— 空应用上跑完应当全是 0，非 0 就得挨张看。
        if nonempty:
            log('WARN:cleanup 本次运行新增的行没清干净（请逐张核对是否测试残留）：%s'
                % '、'.join(nonempty))
        else:
            log('OK:cleanup 本次运行 0 行残留%s' % ('（运行前已有 %d 行，未动）' % kept if kept else ''))
        return not left


def _token_user():
    """当前 token 的登录账号（JWT payload 的 username）；解不出返回 None（则不删任何「运行中新出现」的记录）。"""
    import base64
    try:
        import desform_utils as DU
        part = (DU._TOKEN or '').split('.')[1]
        part += '=' * (-len(part) % 4)
        return json.loads(base64.urlsafe_b64decode(part).decode('utf-8')).get('username')
    except Exception:                                  # noqa: BLE001
        return None


def _is_today(v):
    """日期值是不是今天：毫秒时间戳（数字或数字串）按本机时区折日；字符串看前 10 位。"""
    today = time.strftime('%Y-%m-%d')
    if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit() and len(v) >= 12):
        return time.strftime('%Y-%m-%d', time.localtime(int(v) / 1000)) == today
    return isinstance(v, str) and v[:10] == today


_EMPTY = (None, '', [], {})
#: expect 里的特殊期望值 → 判定函数（按钮/流程写入「当前日期」时写不出具体值，
#: 以前只能另写脚本回读，2026-09-24 任务管理/担保-一句话10）
_SPECIAL = {'$today': _is_today,
            '$notempty': lambda v: v not in _EMPTY, '$not_empty': lambda v: v not in _EMPTY,
            '$empty': lambda v: v in _EMPTY}


def _same(got, exp):
    if got == exp:
        return True
    if isinstance(got, list) or isinstance(exp, list):
        # 选人/选部门：库里是数组，流程回写的可能是裸串 / 逗号串 —— 按成员集合比
        def _norm(x):
            if isinstance(x, list):
                return set(str(i) for i in x)
            return set(i.strip() for i in str(x or '').split(',') if i.strip())
        return _norm(got) == _norm(exp)
    try:
        return float(got) == float(exp)
    except (TypeError, ValueError):
        return False


def approval_tables_live(app, app_id):
    """真机回读：启用中、新增触发、无触发条件、含审批/填写节点的流程 → 该表「新增即进审批」。
    建后套件 `postbuild_flows` 建的流程不在 flows.py 里，只看 flows.py 会漏（2026-09-22 CRM R2：
    冒烟造的回款单/退货申请触发了填写节点流程，记录删了、2 条待办悬空，脚本却报残留 0）。"""
    out = set()
    try:
        from desform_utils import api_request
        r = api_request('/act/process/extActProcess/listProcess',
                        params={'lowAppId': app_id, 'pageNo': 1, 'pageSize': 1000}, method='GET')
    except Exception as ex:                      # noqa: BLE001
        log('  WARN: 回读真机流程失败，审批表只按 flows.py 判：%s' % str(ex)[:80])
        return out
    code2name = {v: k for k, v in app.forms.items()}
    for rec in (((r or {}).get('result') or {}).get('records') or []):
        if str(rec.get('openStatus')) != '1':
            continue
        try:
            pj = json.loads(rec.get('processJson') or '{}')
        except ValueError:
            continue
        attr = pj.get('attr') or {}
        if pj.get('startType') and pj.get('startType') != 'tableEvent':
            continue                             # 按钮流 / 子流程 / 定时的 attr 里也带 startEventType='add'
        if 'add' not in str(pj.get('startEventType') or attr.get('startEventType') or ''):
            continue
        t = code2name.get(pj.get('formTableCode') or attr.get('formTableCode'))
        if not t:
            continue
        # 触发条件 startCondition（组里有 queryItems）→ 默认态数据不触发，不拦
        cond = attr.get('startCondition') or pj.get('startCondition') or []
        if any((g or {}).get('queryItems') for g in cond if isinstance(g, dict)):
            continue
        # ⚠️ processJson 的节点链挂在**根的 childNode** 上、分支在 conditionNodes 里 —— 以前从
        # `pj['nodes']`（不存在）起步、也不认 conditionNodes，一个节点都走不到，这个函数恒返回空集，
        # 「新增即进审批」的表从没被真机识别过（2026-09-24 担保 R2 复现）。
        stack, has = [pj], False
        while stack and not has:
            n = stack.pop()
            if not isinstance(n, dict):
                continue
            if n.get('type') in ('approver', 'edit'):
                has = True
            for k in ('nodes', 'children', 'branches', 'childNode', 'conditionNodes'):
                v = n.get(k)
                if isinstance(v, list):
                    stack.extend(v)
                elif isinstance(v, dict):
                    stack.append(v)
        if has:
            out.add(t)
    return out


def approval_tables(flows_path):
    """「新增即进审批/填写」的表：造一条就会留下一个没法用 API 完成的待办。"""
    if not flows_path:
        return set()
    mf = os.path.normpath(os.path.join(_HERE, '..', '..', 'jeecg-lowcode-miniflow', 'scripts'))
    if mf not in sys.path:
        sys.path.insert(0, mf)
    spec = importlib.util.spec_from_file_location('user_flows_smoke', flows_path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except NameError as ex:
        raise SystemExit('FAIL: --flows 要的是 flow_dsl 写的 flows.py（定义 FLOWS = [...]），%s 看起来是建后套件的 '
                         'pb_flows.py（button_flow/appr/upd 那套）：%s' % (flows_path, ex))
    if not hasattr(mod, 'FLOWS'):
        raise SystemExit('FAIL: --flows 文件里没有 FLOWS 列表：%s' % flows_path)
    import flow_rules as FR
    out = set()
    for f in getattr(mod, 'FLOWS', None) or []:
        if f.get('kind') == 'main' and '新增' in str(f.get('on') or ''):
            if any(n.get('type') in ('approver', 'edit') for n in FR.walk_nodes(f.get('nodes') or [])):
                if f.get('cond'):
                    # 带触发条件的审批流（如「合同状态=审批中」才进审批）：造默认态的基础数据不会触发，
                    # 整张表拒掉会让 BASE 写不了（2026-09-22 CRM R2 实测）。只提示，由用例自己避开条件值
                    log('  提示：表「%s」的流程「%s」带条件进审批，造数时避开 %s'
                        % (f.get('table'), f.get('name'), f.get('cond')))
                    continue
                out.add(f.get('table'))
    return out


def _with_alias_deps(only, cases):
    """`--only` 选中的用例若引用了别的用例起的 `alias`（'@xxx'），把那些用例也带上（递归）。
    否则报「别名还没建」，只能把基础单据挪进 BASE（2026-09-22 销售管理 R2 实测）。"""
    by_alias = {c['alias']: c['name'] for c in cases if c.get('alias')}

    def refs(o, out):
        if isinstance(o, str):
            # '@别名' 与 '@别名.字段' 都算引用（以前只认前者，'@rk1.仓库编码' 带不上前置用例 —— 2026-09-24 进销存-速测17 #7）
            key = o[1:].split('.', 1)[0] if o.startswith('@') else None
            if key in by_alias:
                out.add(by_alias[key])
        elif isinstance(o, dict):
            for v in o.values():
                refs(v, out)
        elif isinstance(o, (list, tuple)):
            for v in o:
                refs(v, out)
        return out

    need = set(only)
    while True:
        more = set()
        for c in cases:
            if c['name'] in need:
                more |= refs(c, set())
        more -= need
        if not more:
            break
        log('  --only 补上被引用的前置用例：%s' % '、'.join(sorted(more)))
        need |= more
    return need


def validate_config(runner, cfg, only=()):
    """开跑前把整份配置过一遍：表、字段、别名引用。以前配置错一处要等基础数据造完、跑到那个用例才
    SystemExit 中止整轮（CRM-速测19 第 4 个用例写 '@pool3.id'，前面白跑、后面全没跑）。只读，不造数据。"""
    app, errs = runner.app, []
    defined = set((cfg.get('BASE') or {}).keys())

    def chk_field(t, f, where):
        try:
            app.model(t, f)
        except SystemExit as e:
            errs.append('%s：%s' % (where, str(e).replace('FAIL: ', '')))
            return False
        return True

    def chk_val(v, where, local):
        vals = v if isinstance(v, list) else [v]
        for x in vals:
            if not isinstance(x, str):
                continue
            for part in (x.split(',') if ',' in x and x.strip().startswith('@') else [x]):
                part = part.strip()
                if part.startswith('@'):
                    ref = part[1:].split('.', 1)[0]
                    if ref not in local:
                        errs.append('%s：引用 %s，别名「%s」在这之前没有定义（BASE / 前面用例的 alias / doc）'
                                    % (where, part, ref))

    for alias, (t, kv) in (cfg.get('BASE') or {}).items():
        if t not in app.forms:
            errs.append('BASE「%s」：应用里没有工作表「%s」' % (alias, t))
            continue
        for k, v in kv.items():
            if chk_field(t, k, 'BASE「%s」' % alias):
                chk_val(v, 'BASE「%s」.%s' % (alias, k), defined)
    for c in cfg.get('CASES') or []:
        if only and c.get('name') not in only:
            continue
        nm = c.get('name')
        dt, dkv = c['doc']
        if c.get('trigger') == 'delete' and c.get('approval'):
            # 删除后审批实例随记录一起清掉，审批断言必然失败（销售-速测20）
            errs.append('用例「%s」trigger=delete 不能写 approval：删掉单据后实例也没了。'
                        '新增即审批的表上跑删除用例，去掉 approval、运行时加 --include-approval' % nm)
        local = set(defined) | {'doc'}
        if dt not in app.forms:
            errs.append('用例「%s」：应用里没有工作表「%s」' % (nm, dt))
            continue
        if isinstance(dkv, dict):
            for k, v in dkv.items():
                if chk_field(dt, k, '用例「%s」doc' % nm):
                    chk_val(v, '用例「%s」doc.%s' % (nm, k), defined)
        else:
            chk_val(dkv, '用例「%s」doc' % nm, defined)
        for k in (c.get('confirm') or {}):
            chk_field(dt, k, '用例「%s」confirm' % nm)
        for row in c.get('rows') or []:
            rt, back, pf, rkv = row
            if rt not in app.forms:
                errs.append('用例「%s」rows：没有工作表「%s」' % (nm, rt))
                continue
            chk_field(rt, back, '用例「%s」rows' % nm)
            chk_field(dt, pf, '用例「%s」rows' % nm)
            for k, v in rkv.items():
                if chk_field(rt, k, '用例「%s」rows' % nm):
                    chk_val(v, '用例「%s」rows.%s' % (nm, k), local)
        for e in c.get('expect') or []:
            t, where, want = e[0], e[1], e[2]
            if t not in app.forms:
                errs.append('用例「%s」expect：没有工作表「%s」' % (nm, t))
                continue
            if isinstance(where, dict):
                for k, v in where.items():
                    if isinstance(v, str) and v in _SPECIAL:
                        # $today/$empty 只是期望值写法，放进定位条件会按字面比较、静默查到 0 行（担保-一句话12、人事OA-速测20）
                        errs.append('用例「%s」expect 定位.%s 写了 %s —— 特殊值只能写在期望值里，定位条件请写具体值'
                                    % (nm, k, v))
                    elif chk_field(t, k, '用例「%s」expect 定位' % nm):
                        chk_val(v, '用例「%s」expect 定位.%s' % (nm, k), local)
            else:
                chk_val(where, '用例「%s」expect 定位' % nm, local)
            for k, v in want.items():
                if k != '#' and chk_field(t, k, '用例「%s」expect' % nm):
                    chk_val(v, '用例「%s」expect.%s' % (nm, k), local)
        if c.get('alias'):
            defined.add(c['alias'])
    return errs


def main():
    ap = argparse.ArgumentParser(description='端到端冒烟测试：造单→触发流程→回读断言→清理')
    for k in ('--api-base', '--token', '--tenant-id', '--app-id', '--config'):
        ap.add_argument(k, required=True)
    ap.add_argument('--flows', default='', help='flows.py：用来识别「新增即进审批」的表（默认跳过这些用例）')
    ap.add_argument('--only', default='', help='只跑这些用例（逗号分隔）')
    ap.add_argument('--keep', action='store_true', help='不清理测试数据（排查用）')
    ap.add_argument('--include-approval', action='store_true', help='连「新增即进审批」的表也跑（收尾清掉本次触发的流程实例）')
    ap.add_argument('--allow-skip', action='store_true',
                    help='有用例被跳过时仍以 0 退出（默认 3：skip 不等于通过）')
    a = ap.parse_args()

    init_lowapp(a.api_base.rstrip('/'), a.token, tenant_id=str(a.tenant_id), app_id=str(a.app_id))
    cfg = {}
    with open(a.config, encoding='utf-8') as fh:
        exec(compile(fh.read(), a.config, 'exec'), cfg)
    mark = cfg.get('MARK') or 'SMK'
    app = Runner(App(str(a.app_id)), mark)
    skip_tables = set() if a.include_approval else (approval_tables(a.flows) | approval_tables_live(app.app, a.app_id))
    if a.include_approval or any(c.get('approval') for c in cfg.get('CASES') or []):
        app.proc = Proc(str(a.app_id))             # 跟踪本次触发的实例，收尾统一清
    only = {s.strip() for s in a.only.split(',') if s.strip()}
    if only:
        only = _with_alias_deps(only, cfg.get('CASES') or [])
    skipped, skip_list = 0, []
    problems = validate_config(app, cfg, only)
    if problems:
        log('FAIL: 冒烟配置有 %d 处错误（还没造任何数据）：' % len(problems))
        for x in problems:
            log('  - ' + x)
        sys.exit(2)
    app.snapshot()                                 # 运行前已有的记录：清理时一条都不碰
    try:
        for alias, (table, kv) in (cfg.get('BASE') or {}).items():
            if table in skip_tables:
                raise SystemExit('FAIL: BASE 里的表「%s」新增即进审批，不能当基础数据' % table)
            app.new(table, kv, alias=alias)
        for c in cfg.get('CASES') or []:
            if only and c['name'] not in only:
                continue
            # doc 写 '@别名' = 复用已有单据、不新增 → 不会「新增即进审批」，不拿它判跳过（进销存-速测17 #6）
            reuse = isinstance(c['doc'][1], str) and c['doc'][1].startswith('@')
            tables = ([] if reuse else [c['doc'][0]]) + [r[0] for r in c.get('rows') or []]
            hit = [t for t in tables if t in skip_tables]
            if hit and not c.get('approval'):          # 写了 approval 断言的用例就是来测审批的，不跳
                skipped += 1
                skip_list.append((c['name'], '、'.join(hit)))
                log('── %s\n  [SKIP] 表「%s」新增即进审批；要测审批就给用例写 approval 断言'
                    '（收尾自动清本次实例），或加 --include-approval' % (c['name'], '、'.join(hit)))
                continue
            app.run_case(c)
    finally:
        clean = True if a.keep else app.cleanup()
    ok, bad = sum(app.res), len(app.res) - sum(app.res)
    log('RESULT pass=%d fail=%d skip=%d' % (ok, bad, skipped))
    # 复跑提示：每个用例的 wait 是**串行硬等**（5 个用例 ≈ 2 分钟纯等待），
    # 全量复跑一次失败修正要多烧几分钟。2026-09-21 进销存实测：3 轮全量冒烟里
    # 约 5 分钟花在重复等待已经通过的用例上 —— 改完只跑失败的那个即可。
    if app.failed_cases:
        seen, names = set(), []
        for n in app.failed_cases:
            if n not in seen:
                seen.add(n)
                names.append(n)
        log('HINT:改完只复跑失败用例（别再全量跑，每个用例的 wait 是硬等）：')
        log('     --only "%s"' % ','.join(names))
    # 跳过要醒目：`pass=24 fail=0 skip=1` 读起来像全绿，而被跳过的往往正是网关的非审批分支
    # （2026-09-24 项目申报 R2：「不立项」分支因立项结果表新增即进审批被默认跳过）。
    if skip_list:
        log('WARN:有 %d 个用例被跳过 —— 它们**没有被验证**：' % len(skip_list))
        for n, t in skip_list:
            log('     · %s（表「%s」新增即进审批）' % (n, t))
        log('     补跑：--include-approval --only "%s"（收尾自动清本次实例）；'
            '或给用例写 approval 断言；确认可以不验时加 --allow-skip' % ','.join(n for n, _ in skip_list))
    if bad or not clean:
        sys.exit(2)
    sys.exit(3 if (skip_list and not a.allow_skip) else 0)


if __name__ == '__main__':
    main()
