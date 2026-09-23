# -*- coding: utf-8 -*-
"""端到端冒烟测试：造单 → 触发流程 → 回读断言 → 按记录 id 清理（零残留）。

为什么要有它：`save` / `deploy` / `check_node_contract` / `app_audit` **全是结构检查** ——
「流程跑起来账对不对」它们一条都看不见。2026-09-21 进销存实测：结构闸门全绿的应用里藏着
「第一笔入库丢账」「公式值累加把库存冲成 0」「同事件两条流程只跑一条」…… 全靠造单回读才暴露。
凡是带**台账 / 记账 / 回写**类流程的应用，交付前必须跑一遍本脚本。

    python smoke_flows.py --api-base URL --token T --tenant-id N --app-id A --config smoke.py [--flows flows.py]
                          [--only 用例名,用例名] [--keep] [--include-approval]

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
`'@doc'` / `'@doc.字段'` = 本用例的单据；`'$now'` = 当前毫秒时间戳。用例按顺序跑、共享 BASE 与前面用例建的数据
（所以「先入库 10 再出库 3 期望库存 7」可以直接写成两个用例）。

⚠️ **默认跳过「新增即进审批」的表**：平台没有「完成审批任务」的 API，跑了会在办理人待办里留下悬空任务。
传了 `--flows` 才能识别；确实要跑加 `--include-approval`，并自行处理留下的待办。
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
                             'showField': wo.get('showField')}
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


class Runner(object):
    def __init__(self, app, mark):
        self.app, self.mark = app, mark
        self.alias = {}       # 别名 → (表, id)
        self.made = {}        # 表 → [id]
        self.res = []
        self.failed_cases = []

    # ---- 取值 ----
    def value(self, table, field, v):
        f = self.app.model(table, field)
        if isinstance(v, str) and v == '$now':
            return int(time.time() * 1000)
        if isinstance(v, str) and v.startswith('@'):
            ref, _, sub = v[1:].partition('.')
            if ref not in self.alias:
                raise SystemExit('FAIL: 取值 %s：别名「%s」还没建（BASE 里没有，也不是 doc）' % (v, ref))
            tb, rid = self.alias[ref]
            if not sub:
                return [rid] if f['type'] == 'link-record' else rid
            return (self.app.row(tb, rid) or {}).get(self.app.model(tb, sub)['model'])
        if isinstance(v, str) and f['labels'] and v in f['labels']:
            return f['labels'][v]                      # 字典 / 选项：文案 → 落库值
        if isinstance(v, str) and f['type'] == 'link-field' and not f['labels']:
            lb = self.app.source_labels(f.get('showField'))
            if v in lb:
                return lb[v]                           # 他表字段带出的字典值：顺 showField 翻
        return v

    def payload(self, table, kv):
        return {self.app.model(table, k)['model']: self.value(table, k, v) for k, v in kv.items()}

    def new(self, table, kv, alias=None):
        rid = add_data(self.app.forms[table], self.payload(table, kv))['id']
        self.made.setdefault(table, []).append(rid)
        if alias:
            self.alias[alias] = (table, rid)
        return rid

    # ---- 用例 ----
    def run_case(self, c):
        log('── %s' % c['name'])
        dt, dkv = c['doc']
        trigger = c.get('trigger') or 'update'
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
        if c.get('alias'):                             # 让后面的用例能用 '@别名' 引用这张单据
            self.alias[c['alias']] = (dt, did)
        self.wait_expect(c)

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

    def check_one(self, e):
        table, where, want = e[0], e[1], e[2]
        wv = {self.app.model(table, k)['model']: self.value(table, k, v) for k, v in where.items()}
        hits = [r for r in self.app.rows(table)
                if all(_same(r['desformData'].get(m), v) for m, v in wv.items())]
        for r in hits:                                 # 流程派生出来的记录也要清理
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
            got, exp = d.get(self.app.model(table, k)['model']), self.value(table, k, v)
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
        n = 0
        for table in self.app.forms:                   # 兜底：带标记的派生记录
            for r in self.app.rows(table):
                if self._marked(r):
                    if r['id'] not in self.made.setdefault(table, []):
                        self.made[table].append(r['id'])
                        log('  cleanup: 兜底命中 %s/%s（文本列含「%s」）' % (table, r['id'], self.mark))
        for table, ids in self.made.items():
            for rid in dict.fromkeys(ids):
                try:
                    delete_data(self.app.forms[table], rid, hard=True)
                    n += 1
                except Exception as ex:                # noqa: BLE001
                    log('  WARN: 删除失败 %s %s %s' % (table, rid, str(ex)[:80]))
        left = []
        for table in self.app.forms:
            for r in self.app.rows(table):
                if self._marked(r):
                    left.append('%s/%s' % (table, r['id']))
        log('OK:cleanup 删除 %d 条；带标记「%s」的残留 %d 条%s' % (n, self.mark, len(left),
                                                         ('：' + '、'.join(left[:8])) if left else ''))
        return not left


def _same(got, exp):
    if got == exp:
        return True
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
        if 'add' not in str(pj.get('startEventType') or attr.get('startEventType') or ''):
            continue
        t = code2name.get(pj.get('formTableCode') or attr.get('formTableCode'))
        if not t:
            continue
        # 触发条件 startCondition（组里有 queryItems）→ 默认态数据不触发，不拦
        cond = attr.get('startCondition') or pj.get('startCondition') or []
        if any((g or {}).get('queryItems') for g in cond if isinstance(g, dict)):
            continue
        stack, has = list(pj.get('nodes') or []), False
        while stack and not has:
            n = stack.pop()
            if not isinstance(n, dict):
                continue
            if n.get('type') in ('approver', 'edit'):
                has = True
            for k in ('nodes', 'children', 'branches', 'childNode'):
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
            if o.startswith('@') and o[1:] in by_alias:
                out.add(by_alias[o[1:]])
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


def main():
    ap = argparse.ArgumentParser(description='端到端冒烟测试：造单→触发流程→回读断言→清理')
    for k in ('--api-base', '--token', '--tenant-id', '--app-id', '--config'):
        ap.add_argument(k, required=True)
    ap.add_argument('--flows', default='', help='flows.py：用来识别「新增即进审批」的表（默认跳过这些用例）')
    ap.add_argument('--only', default='', help='只跑这些用例（逗号分隔）')
    ap.add_argument('--keep', action='store_true', help='不清理测试数据（排查用）')
    ap.add_argument('--include-approval', action='store_true', help='连「新增即进审批」的表也跑（会留下悬空待办）')
    a = ap.parse_args()

    init_lowapp(a.api_base.rstrip('/'), a.token, tenant_id=str(a.tenant_id), app_id=str(a.app_id))
    cfg = {}
    with open(a.config, encoding='utf-8') as fh:
        exec(compile(fh.read(), a.config, 'exec'), cfg)
    mark = cfg.get('MARK') or 'SMK'
    app = Runner(App(str(a.app_id)), mark)
    skip_tables = set() if a.include_approval else (approval_tables(a.flows) | approval_tables_live(app.app, a.app_id))
    only = {s.strip() for s in a.only.split(',') if s.strip()}
    if only:
        only = _with_alias_deps(only, cfg.get('CASES') or [])
    skipped = 0
    try:
        for alias, (table, kv) in (cfg.get('BASE') or {}).items():
            if table in skip_tables:
                raise SystemExit('FAIL: BASE 里的表「%s」新增即进审批，不能当基础数据' % table)
            app.new(table, kv, alias=alias)
        for c in cfg.get('CASES') or []:
            if only and c['name'] not in only:
                continue
            tables = [c['doc'][0]] + [r[0] for r in c.get('rows') or []]
            hit = [t for t in tables if t in skip_tables]
            if hit:
                skipped += 1
                log('── %s\n  [SKIP] 表「%s」新增即进审批（平台没有完成审批任务的 API，跑了会留悬空待办）；'
                    '要跑加 --include-approval' % (c['name'], '、'.join(hit)))
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
    sys.exit(0 if (bad == 0 and clean) else 2)


if __name__ == '__main__':
    main()
