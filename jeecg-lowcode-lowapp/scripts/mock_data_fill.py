# -*- coding: utf-8 -*-
"""按应用规格灌测试数据 —— 让建完的应用打开就有内容。

    python mock_data_fill.py --api-base URL --token TOKEN --tenant-id N --app-id A \
        --spec app_spec.json [--rows 5] [--only 表1,表2]

## 两遍灌（顺序不能反）

    ① 先灌所有表的**标量字段**（文本/金额/数字/日期/选项），每表 N 行
    ② 再灌**关联记录**：单条→随机挑一条目标表记录；多条→先建 K 条子记录，再回填 id 数组

汇总字段的值来自子记录，所以必须先有 ② 才有数；反过来则汇总恒为 0。

## 三条硬约束（都是踩过的坑）

1. **键一律用 model**（`get_form_fields` 拿）。写中文名会**静默入库**——
   `list_data` 看得见值、界面**整列显示空**。
2. **日期写毫秒时间戳** + `<model>_dictText`；选项字段写**选项文案**。
3. **关联记录写 id 数组** + `model_dictTextPrint`。

## 灌数必须排在建流程之前

`add_data` 会触发该表的 tableEvent 主流程，而主流程普遍带「取多条 → 逐行调子流程」——
灌 N 行 = N 轮级联写。实测照旧顺序跑，灌数 **1h4m** 且后端崩过一次。
调用方（`build_app.py`）已把本阶段排在流程之前；单独跑时也请遵守。
"""
from __future__ import annotations

import argparse
import json
import os
import random
import socket
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import desform_utils as DU                                          # noqa: E402
import desform_data_utils as DD                                     # noqa: E402
from desform_lowapp_utils import init_lowapp, get_menus             # noqa: E402

if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

socket.setdefaulttimeout(60)

# ⚠️ **写数据串行跑**（WORKERS = 1）。这不只是更保险，实测还更快：
#
#   | 方式                | 每次写入 | 依据                        |
#   |---------------------|---------|-----------------------------|
#   | 串行 25 次           | 0.044s  | 0.09 + 23×0.04 + 0.05 / 25  |
#   | 4 并发 × 12 轮 (48) | 0.065s  | 3.1s / 48                   |
#
# 服务端把并发写全序列化了 —— 加并发换不来吞吐，只换来争用开销。而连接池只有 **20**
# （oracle176 profile），52 张表里 23 张有自动编号（生成编号在同一事务里锁序列表）、
# 50 个汇总字段（事务内跨表聚合），事务持连接的时长被这些子工作拉长。
# 实测 8 并发把池子占干的后果：每个新事务抛 `CannotCreateTransactionException:
# Could not open JDBC Connection for transaction` → 请求积压 → **后端进程直接倒下**
# （探测从 HTTP 200 变成 `WinError 10061 目标计算机积极拒绝`）。
#
# 想改回并发：把 WORKERS 调大即可，但先看上面的数字 —— 串行是**又快又稳**那一侧。
WORKERS = 1

# 池子打满时抛的错，属于**可等的瞬时**故障，退避重试；其余异常照旧即刻上报。
# 不区分的话，「一次抖动」和「后端真挂了」看起来一模一样，只能靠人肉盯着。
TRANSIENT = ('Could not open JDBC Connection', 'CannotCreateTransaction',
             'Connection is not available', 'Unable to acquire JDBC Connection',
             '连接池', 'timed out')
RETRIES = 4          # 首试 + 3 次退避；退避总时长 1.5+2.25+3.375 ≈ 7s
BACKOFF = 1.5

# 取字段是**纯读**，和写数据的风险不同，所以单独给并发 —— 但也别拉满整个池子。
# 实测：52 张表串行取字段要 **约 4.3 分钟**（`get_form_fields` 单次 4~5.6s，服务端每次
# 重算设计 JSON），8 并发降到 118s。取 4 是折中：既拿回大部分收益，又只占 20 池的两成，
# 给应用自身的请求留足余量。
FIELD_WORKERS = 4

# 造数据的词表（纯演示，让看板上有可读的内容）
WORDS = ['华东', '华南', '华北', '西南', '东北', '中部']
BRANDS = ['华为', '思科', '锐捷', '新华三', '中兴', 'TP-LINK']
CNAMES = ['北京宏远', '上海联创', '广州天翼', '深圳恒通', '杭州云栖', '成都锦江']


def log(*a):
    print(*a, flush=True)


def _pick(name, i, seq):
    """按字段名挑一个像样的示例值。"""
    if '名称' in name or '姓名' in name:
        if '客户' in name:
            return CNAMES[i % len(CNAMES)]
        if '供应商' in name:
            return CNAMES[(i + 2) % len(CNAMES)] + '供应链'
        if '仓库' in name:
            return '仓库%d号' % (i + 1)
        if '产品' in name:
            return '%s-产品%d' % (BRANDS[i % len(BRANDS)], seq)
        return '%s%d' % (name[:4], i + 1)
    if '品牌' in name:
        return BRANDS[i % len(BRANDS)]
    if '规格' in name:
        return '%dU机架式' % (1 + i % 4)
    if '单位' in name:
        return ['台', '套', '件', '个'][i % 4]
    if '职位' in name:
        return ['经理', '主管', '专员'][i % 3]
    if '抬头' in name:
        return CNAMES[i % len(CNAMES)] + '有限公司'
    if '账号' in name or '账户' in name:
        return '6222%012d' % random.randint(0, 10 ** 12)
    return '%s%d' % (name[:6], i + 1)


def sample_value(field_name, ftype, dict_items, i, seq):
    """按控件类型造一个值。返回 (值, 是否需要 _dictText)。"""
    n = field_name or ''
    if ftype in ('select', 'radio', 'checkbox') and dict_items:
        vals = [d.get('label') or d.get('value') for d in dict_items]
        if ftype == 'checkbox':
            return [vals[i % len(vals)]], True
        return vals[i % len(vals)], True
    if ftype in ('money', 'number', 'integer', 'rate', 'slider'):
        v = round(random.uniform(10, 5000), 2)
        return (int(v) if ftype in ('integer', 'rate') else v), False
    if ftype in ('date', 'summary-date'):
        return int((time.time() - i * 86400) * 1000), False
    if ftype == 'phone':
        return '138%08d' % random.randint(0, 10 ** 8), False
    if ftype == 'email':
        return 'demo%d@example.com' % i, False
    if ftype == 'area-linkage':
        return ['北京市', '北京市', '朝阳区'], False
    if ftype in ('select-user', 'select-depart', 'select-depart-post', 'org-role'):
        return None, False                       # 需要真实组织 id，演示数据留空
    if ftype in ('imgupload', 'file-upload'):
        return None, False
    if ftype in ('auto-number', 'formula', 'summary', 'link-record', 'link-field',
                 'card', 'divider', 'text', 'tabs', 'grid', 'sub-table-design'):
        return None, False                       # 系统生成 / 关联 / 装饰，不手工写
    return _pick(n, i, seq), False


class Filler(object):
    def __init__(self, spec, api, token, tenant, app, rows):
        self.spec = spec
        self.api, self.token = api.rstrip('/'), token
        self.tenant, self.app = str(tenant), str(app)
        self.rows = rows
        self.codes = {}          # 表名 -> code
        self.fields = {}         # 表名 -> {字段名: {model,key,type}}
        self.dicts = {}          # 字典名 -> [项]
        self.ids = {}            # 表名 -> [记录id]
        self._snap = {}          # code -> {id: desformData}，供 merge_edit 用
        self._dict_idx = {}      # (表名, 字段名) -> 字典项
        self.fail = 0
        self.skipped = 0         # 到点未写的行数
        self._deadline = None
        self._lock = threading.Lock()

    def resolve(self):
        ml = (get_menus(self.app) or {}).get('menuList') or []
        by = {m.get('menuName'): m.get('desformCode')
              for m in ml if m.get('type') == 'form' and m.get('desformCode')}
        for f in self.spec.get('forms') or []:
            nm = f.get('名称')
            self.codes[nm] = f.get('code') or by.get(nm)
        # ⚠️ **必须并发取字段。** 实测 `get_form_fields` 单次要 **4~5.6 秒**
        # （`get_menus` 只要 0.34s，所以不是网络慢，是服务端每次重算设计 JSON）。
        # 52 张表串行 = **约 4.3 分钟，一行数据都还没写** —— 之前所有「灌数卡住了」
        # 的观感都是这么来的，卡的根本不是写。
        # 这里是纯读，不像写那样占事务池，所以并发取是安全的；但 `get_form_fields`
        # 内部走 `DU` 的全局 `_ACCESS_TOKEN`/`_API_BASE`（只读，线程安全），
        # 各调用之间无共享可写状态。
        names = [(nm, c) for nm, c in self.codes.items() if c]
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=FIELD_WORKERS) as ex:
            futs = {ex.submit(DU.get_form_fields, c): nm for nm, c in names}
            for fu in as_completed(futs):
                nm = futs[fu]
                try:
                    _, flds = fu.result()
                    self.fields[nm] = flds
                except Exception as e:                            # noqa: BLE001
                    log('FAIL:fields %s %s' % (nm, str(e)[:70]))
        log('OK:fields %d 张表并发取字段 %.1fs' % (len(self.fields), time.time() - t0))
        r = DU.api_request('/sys/dict/getDictListByLowAppId', method='GET')
        recs = r.get('result') or []
        if isinstance(recs, dict):
            recs = recs.get('records') or []
        for x in recs:
            self.dicts[x.get('dictName')] = x.get('dictItemsList') or x.get('items') or []
        self._build_index()
        log('OK:resolve 表%d 字段字典%d' % (len(self.fields), len(self.dicts)))

    def _dict_of(self, table, field):
        """字段 → 字典项。**建索引查，不要每次线性扫 spec 的 52 张表**。

        原先写成 `next(x for x in spec['forms'] if x['名称'] == table)`，而它被放在
        「每行 × 每字段」的内层循环里 —— 1115 字段 × 52 表 × 行数的比较。不是主要瓶颈，
        但纯属白烧，且随表数平方增长。
        """
        return self._dict_idx.get((table, field))

    def _build_index(self):
        self._dict_idx = {}
        for f in self.spec.get('forms') or []:
            for fld, dn in (f.get('字典') or {}).items():
                self._dict_idx[(f['名称'], fld)] = self.dicts.get(dn)

    def _payload(self, table, i, seq):
        payload = {}
        for fname, info in (self.fields.get(table) or {}).items():
            if '.' in fname:                    # 子表列，单独处理
                continue
            val, _ = sample_value(fname, info.get('type'),
                                  self._dict_of(table, fname), i, seq)
            if val is None:
                continue
            payload[info['model']] = val
            if info.get('type') in ('select', 'radio', 'checkbox'):
                payload[info['model'] + '_dictText'] = val
        return payload

    def _add_with_retry(self, code, payload, table):
        """池子打满时退避重试；退避耗尽或非瞬时错误则抛出。"""
        for attempt in range(RETRIES):
            try:
                return DD.add_data(code, payload)
            except Exception as e:                                    # noqa: BLE001
                msg = str(e)
                last = attempt == RETRIES - 1
                if last or not any(t in msg for t in TRANSIENT):
                    raise
                time.sleep(BACKOFF ** attempt)          # 1.5 / 2.25 / 3.375s
        return None

    def write_row(self, table, i, seq):
        """写**一行** —— 并行度就以这个为单位（见 main 里的说明）。"""
        if self._deadline and time.time() > self._deadline:
            self.skipped += 1        # 到点就短路，已发出的那批写完就收工
            return 0
        code = self.codes.get(table)
        if not code:
            return 0
        try:
            r = self._add_with_retry(code, self._payload(table, i, seq), table)
        except Exception as e:                                        # noqa: BLE001
            with self._lock:
                self.fail += 1
                if self.fail <= 3:
                    log('FAIL:add %s %s' % (table, str(e)[:70]))
            return 0
        rid = (r or {}).get('id')
        if rid:
            # list.append 在 GIL 下是原子的；只有 fail 计数需要锁
            self.ids.setdefault(table, []).append(str(rid))
        return 1

    def fill_scalars(self, table):
        """串行灌一张表（`fill_links` 现造目标表数据时用）。"""
        if not self.codes.get(table) or not self.fields.get(table):
            return 0
        return sum(self.write_row(table, i, i) for i in range(self.rows))

    def _rows_snapshot(self, code):
        """id -> desformData。**edit_data 是全量覆盖**，必须先取回来再合并。"""
        snap = {}
        try:
            d = DD.list_data(code, 1, 500)
        except Exception:                                             # noqa: BLE001
            return snap
        for r in (d.get('records') or []):
            snap[str(r.get('id'))] = r.get('desformData') or {}
        return snap

    def _merge_edit(self, code, rid, patch):
        """把 patch 合并进该记录现有 desformData 再提交。

        ⚠️ `desform_data_utils.edit_data` 是**全量覆盖**：只传关联字段会把该行其它字段**全部清空**
        （实测踩到：某表的「类型/时间」等旁路字段在回填关联后整列消失）。
        """
        cur = self._snap.get(code, {}).get(str(rid))
        if cur is None:
            snap = self._rows_snapshot(code)
            self._snap.setdefault(code, {}).update(snap)
            cur = snap.get(str(rid), {})
        merged = dict(cur)
        merged.update(patch)
        DD.edit_data(code, rid, merged)

    def fill_links(self):
        """② 关联记录：单条→随机挑；多条→挑 K 条目标表记录，回填 id 数组。"""
        done = 0
        for lk in self.spec.get('links') or []:
            table, fld, tgt = lk.get('表'), lk.get('字段'), lk.get('目标')
            code, reg = self.codes.get(table), self.fields.get(table)
            if not code or not reg or fld not in reg:
                continue
            info = reg[fld]
            if info.get('type') != 'link-record':
                continue
            pool = self.ids.get(tgt) or []
            if not pool:                      # 目标表没数据就现造几条
                # ⚠️ 必须包 try：这里是在遍历 links 的过程里**顺带**补灌目标表，
                # 一张表出问题不该把整轮关联回填打断——实测就是这里没包，
                # 一个 `sample_value` 的返回契约错误让「灌数」整段 exit=1。
                try:
                    self.fill_scalars(tgt)
                except Exception as e:                            # noqa: BLE001
                    self.fail += 1
                    log('FAIL:link-scalars %s %s' % (tgt, str(e)[:70]))
                pool = self.ids.get(tgt) or []
            if not pool:
                continue
            many = str(lk.get('条数') or '单条') in ('多条', 'many')
            for rid in self.ids.get(table) or []:
                pick = pool[:2] if many else [random.choice(pool)]
                try:
                    self._merge_edit(code, rid, {info['model']: pick})
                    done += 1
                except Exception as e:                                # noqa: BLE001
                    self.fail += 1
                    if self.fail <= 3:
                        log('FAIL:link %s.%s %s' % (table, fld, str(e)[:60]))
        return done

    # 不手工灌、也不该由本脚本校验的类型（系统生成 / 关联 / 装饰 / 需真实组织 id）
    SKIP_VERIFY = ('link-record', 'link-field', 'summary', 'formula', 'auto-number',
                   'select-user', 'select-depart', 'select-depart-post', 'org-role',
                   'imgupload', 'file-upload', 'sub-table-design')

    def verify(self):
        """按 model 键抽样回读 —— 只数行数查不出「整列显示空」。

        ⚠️ 值在 `record['desformData']` 里，**不在记录顶层**。
        直接 `record.get(model)` 会全取到 None，把好数据误判成「整行皆空」（实测踩到）。
        """
        bad = 0
        for table, code in self.codes.items():
            reg = self.fields.get(table) or {}
            try:
                d = DD.list_data(code, 1, 2)
            except Exception:                                         # noqa: BLE001
                continue
            recs = d.get('records') or []
            want = [i['model'] for f, i in reg.items()
                    if '.' not in f and i.get('type') not in self.SKIP_VERIFY]
            if not recs:
                log('FAIL:verify %s 无数据' % table)
                bad += 1
                continue
            data = recs[0].get('desformData') or {}
            got = [m for m in want if data.get(m) not in (None, '', [])]
            if want and not got:
                log('FAIL:verify %s 整行皆空（键写错了？）' % table)
                bad += 1
        return bad


def main():
    ap = argparse.ArgumentParser(description='按应用规格灌测试数据')
    ap.add_argument('--api-base', required=True)
    ap.add_argument('--token', required=True)
    ap.add_argument('--tenant-id', required=True)
    ap.add_argument('--app-id', required=True)
    ap.add_argument('--spec', required=True)
    ap.add_argument('--rows', type=int, default=3, help='每表灌几行（默认 3）')
    ap.add_argument('--only', default='', help='只灌这些表（逗号分隔）')
    ap.add_argument('--budget', type=int, default=300,
                    help='总预算秒数（默认 300）。到点就停手并**以 0 退出**：'
                         '演示数据没灌完不算失败，应用结构已经好了。')
    a = ap.parse_args()

    with open(a.spec, encoding='utf-8') as fh:
        spec = json.load(fh)
    init_lowapp(a.api_base, a.token, tenant_id=int(a.tenant_id), app_id=a.app_id)
    DU.init_api(a.api_base.rstrip('/'), a.token)

    only = [x.strip() for x in a.only.split(',') if x.strip()]
    if only:
        keep = set(only)
        for lk in (spec.get('links') or []):          # 关联目标表一并带上，否则关联灌不上
            if lk.get('表') in keep:
                keep.add(lk.get('目标'))
        spec['forms'] = [f for f in spec.get('forms') or [] if f.get('名称') in keep]

    fl = Filler(spec, a.api_base, a.token, a.tenant_id, a.app_id, a.rows)
    t0 = time.time()
    # 预算从**进 main 就开始算**，不是从写第一行开始 —— 取字段那段实测就要 2 分钟，
    # 只掐写的话预算形同虚设。
    fl._deadline = t0 + a.budget if a.budget else None
    fl.resolve()

    tables = [f['名称'] for f in spec.get('forms') or [] if fl.codes.get(f['名称'])]

    # ⚠️ 并行单位是**行**，不是**表**。原先按表提交（52 个任务、每个 2 行），
    # 大表小表混在一起，最后一批只剩最大的表在跑、其余 worker 全空转 ——
    # 实测 92 行要 223.6s。改成按行铺平后，池子全程饱和，尾部只有 1 行。
    # 单条写实测 0.56s、8 并发 0.20s（服务端有争用，加速比 2.8x），
    # 所以 104 行的理论下界 ≈21s，而不是被尾部长拖成 3 分钟。
    jobs = [(t, i, i) for t in tables for i in range(fl.rows)]
    total = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(fl.write_row, t, i, s): t for t, i, s in jobs}
        for fu in as_completed(futs):
            try:
                total += fu.result() or 0
            except Exception as e:                                    # noqa: BLE001
                log('FAIL:fill %s %s' % (futs[fu], str(e)[:70]))
    log('OK:scalars 共写入 %d 行 / %d 张表 %.1fs' % (total, len(tables), time.time() - t0))

    # 到点了就不再回填关联/回读校验 —— 那两个也要几分钟，且它们只在"数据齐全"时才有意义。
    # 半灌的应用照样能打开、看板照样出图，缺的只是部分行的内容。
    if fl.skipped:
        log('OK:budget 到点收工：跳过 %d 行（预算 %ds，实耗 %.0fs）'
            % (fl.skipped, a.budget, time.time() - t0))
        log('           演示数据不齐**不影响交付** —— 分组/表单/关联/汇总/字典/流程/看板都已就位。')
        log('           想要全量数据可稍后单独重跑：--only 灌数（或加大 --budget）。')
        raise SystemExit(0)

    linked = fl.fill_links()
    log('OK:links 回填 %d 处关联' % linked)

    bad = fl.verify()
    log('OK:verify 抽样回读完成，异常表 %d 张；失败计数 %d' % (bad, fl.fail))
    if bad or fl.fail:
        log('注意：灌数有异常，但**它不阻塞交付** —— 应用结构已建成，可正常打开使用。')
    raise SystemExit(0)


if __name__ == '__main__':
    main()
