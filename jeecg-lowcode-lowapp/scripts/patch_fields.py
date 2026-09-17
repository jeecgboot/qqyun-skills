# -*- coding: utf-8 -*-
"""补丁阶段 —— 把建壳阶段建不出来的字段一次性补齐。

    python patch_fields.py --api-base URL --token TOKEN --tenant-id N --app-id A \
        --spec app_spec.json [--only 表1,表2] [--dry-run]

## 为什么必须有这一阶段

`create_linked_worksheets.py` 只能建「不依赖别的控件」的字段。下面这些**必须建壳后回读**
才能建，因为它们的参数是**运行时才生成的**（model / key）：

| 补什么 | 卡在哪 |
|---|---|
| 跨表关联记录 | `titleField` 要目标表的标题字段 model —— 建表前不知道 |
| 他表字段 | `linkRecordKey` 要本表关联控件的 key —— 建壳后才有 |
| 汇总 | `linkTable` 要关联控件的 key（多条关联时**不带前缀**） |
| 字典绑定 | 应用级字典要 `dictCodeAppId` + 项快照，creator 不写这些 |
| 自动编号规则 | `options.numberRules` |
| 公式 | `expression` 里是 `$model$`，不是中文名 |

## 与「上一版 apply_spec.py」的关键区别（别重蹈覆辙）

上一版用「依赖驱动、10 轮收敛」解决跨表依赖，复杂度失控，且把应用搞挂过。
这里**不需要多轮**：建壳阶段已经把**全部**表建好了，所有 model/key 在补丁开始时就全部可得。
所以每张表就是 **读一次 → 补完该表全部后置字段 → 写一次**，一次到位。

## 输出纪律

只打 `OK:` / `FAIL:` 摘要行，不 dump 设计 JSON。
未落地的字段逐条给原因（含近似候选），全量落盘 `patch_gaps.json`；有缺口则 `exit 5`。
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import desform_utils as DU                                    # noqa: E402
from desform_lowapp_utils import init_lowapp                  # noqa: E402
from spec_infer import near_names, resolve                    # noqa: E402

if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 全局 socket 超时。desform_utils.api_request 调 _urlopen(req) 时**不传 timeout**，
# 而 urllib 不传 timeout = **无限等** —— 服务端卡住时客户端会永远挂着不放
# （实测记录：4 并发 × 13 波 × 180s ≈ 39 分钟真跑满过）。
# 不改共享的 desform_utils（爆炸半径太大），这里设进程级默认超时，覆盖它内部所有请求。
SOCKET_TIMEOUT = 60
socket.setdefaulttimeout(SOCKET_TIMEOUT)

SUMMARY_TYPES = {
    '求和': 'inner-sum', '合计': 'inner-sum',
    '平均': 'inner-average',
    '最大': 'inner-max', '最小': 'inner-min',
    '计数': 'inner-record-count', '记录数': 'inner-record-count',
}
SHOW_MODE = {'单条': 'single', '多条': 'many', 'single': 'single', 'many': 'many'}
SHOW_TYPE = {'卡片': 'card', '下拉': 'select', '表格': 'table',
             'card': 'card', 'select': 'select', 'table': 'table'}
LAYOUT_TYPES = {'card', 'divider', 'text', 'tabs', 'grid'}


def log(*a):
    print(*a, flush=True)


# ---------------- 控件树遍历 ----------------

def iter_widgets(nodes):
    """扁平遍历控件树（含 card / 子表 columns），只吐 dict。"""
    for n in nodes or []:
        if not isinstance(n, dict):
            continue
        yield n
        sub = n.get('list')
        if isinstance(sub, list):
            for s in sub:
                if isinstance(s, dict):
                    yield from iter_widgets(s.get('list') if s.get('list') else [s])
        for c in (n.get('columns') or []):
            if isinstance(c, dict):
                yield from iter_widgets(c.get('list') if c.get('list') else [c])


def find_widget(design, name):
    for w in iter_widgets(design.get('list')):
        if w.get('name') == name:
            return w
    return None


def card_template(design):
    for it in design.get('list') or []:
        if isinstance(it, dict) and it.get('type') == 'card' and it.get('isAutoGrid'):
            return it
    return None


def append_widget(design, widget, seq):
    """把工厂返回值挂到 design['list']。
    LINK_RECORD/LINK_FIELD 自带 card 包裹（wrap=True），**不要再套一层**——套了后端静默丢弃。"""
    import copy
    tpl = card_template(design)
    if isinstance(widget, dict) and widget.get('type') == 'card' and isinstance(widget.get('list'), list):
        c = widget
    else:
        c = copy.deepcopy(tpl) if tpl else {'options': {}, 'isContainer': True,
                                            'type': 'card', 'isAutoGrid': True}
        c['list'] = [widget]
    base = int(time.time() * 1000) % 1000000
    c['model'] = 'card_%d_%d' % (base, seq)
    c['key'] = '%d_%d' % (base, seq)
    design.setdefault('list', []).append(c)


def preserve_dicts(design):
    """整单保存前把已绑字典控件的 remote 复位为 'dict'，否则绑定态被冲回静态。"""
    for w in iter_widgets(design.get('list')):
        o = w.get('options')
        if isinstance(o, dict) and o.get('isDictItem') and o.get('dictCode'):
            o['remote'] = 'dict'


# ---------------- 引擎 ----------------

class Engine(object):
    def __init__(self, spec, api, token, tenant, app, dry_run=False):
        self.spec = spec
        self.api, self.token = api.rstrip('/'), token
        self.tenant, self.app = str(tenant), str(app)
        self.dry_run = dry_run
        self.designs = {}        # 表名 -> design dict
        self.codes = {}          # 表名 -> code
        self.reg = {}            # 表名 -> {字段名: {"model","key","type"}}
        self.dicts = {}          # 字典名 -> {"dictCode","items"}
        self.gaps = []           # 本轮补丁未落地项（每轮重算）
        self.load_gaps = []      # 载入阶段的问题（不可重试，不随轮次清空）
        self.tmpdir = os.path.join(tempfile.gettempdir(), 'jeecg-desform')
        os.makedirs(self.tmpdir, exist_ok=True)

    # ---------- 载入 ----------

    def form_items(self):
        return [f for f in (self.spec.get('forms') or []) if f.get('名称')]

    def resolve_codes(self):
        """表名 → desformCode。spec 里不必写 code（那是建壳阶段的事）；
        这里从应用菜单回查，让规格只承载业务信息。"""
        from desform_lowapp_utils import get_menus
        try:
            ml = (get_menus(self.app) or {}).get('menuList') or []
        except Exception as e:                                    # noqa: BLE001
            self._load_gap('-', '-', '读应用菜单失败: %s' % str(e)[:100])
            return
        by_name = {m.get('menuName'): m.get('desformCode')
                   for m in ml if m.get('type') == 'form' and m.get('desformCode')}
        for f in self.form_items():
            if not f.get('code'):
                f['code'] = by_name.get(f['名称'])

    #: 读设计的并发度。读不占事务、也不会像并发写那样把连接池占干，
    #: 所以与 mock_data_fill 的取字段同口径给 4；**写仍然串行**。
    READ_WORKERS = 4

    def prewarm_form_ids(self):
        """一次调用拿全「表单编码 → 表单 ID」，省掉每张表各一次的 queryByCode + 存在性校验。

        `query_form()` 内部是 get_form_id(1~2 次 HTTP) + queryById(1 次)。
        而 `/online/lowApp/miniflow/tenantAppFormList` **一次**就返回本租户全部应用的
        `{code, id, name}`——52 张表等于白省 104 次 HTTP。
        失败不影响正确性（回退到原来的逐步解析），只影响速度。
        """
        try:
            r = DU.api_request(
                '/online/lowApp/miniflow/tenantAppFormList?tenantId=%s' % self.tenant,
                method='GET')
            apps = (r.get('result') or {}).get('apps') or []
        except Exception:                                         # noqa: BLE001
            return 0
        n = 0
        for ap in apps:
            for f in ap.get('desforms') or []:
                if f.get('code') and f.get('id'):
                    DU._cache_put(f['code'], f['id'], 0)   # uc 由 queryById 那步刷新
                    n += 1
        if n:
            log('OK:prewarm 预热 %d 个表单 ID（省掉 %d 次 HTTP）' % (n, 2 * n))
        return n

    def load_designs(self):
        self.resolve_codes()
        self.prewarm_form_ids()
        items = []
        for f in self.form_items():
            name, code = f['名称'], f.get('code')
            if not code:
                self._load_gap(name, '-', '应用里找不到这张表（建壳阶段没建成？）')
                continue
            items.append((name, code))

        # ⚠️ 这里是补丁阶段的**真瓶颈**：52 张表串行读设计 ≈ **4 分 31 秒**
        # （2026-09-16 实测，且每次跑补丁都要付一遍）。并发读把它压到 ~1/4。
        # 注意：轮次之间**本来就不重读**（设计读进 self.designs 后各轮在内存里重算），
        # 所以优化点在这第一遍读，不在轮次。
        from concurrent.futures import ThreadPoolExecutor

        def _read(item):
            name, code = item
            try:
                return name, code, DU.query_form(code), None
            except Exception as e:                                # noqa: BLE001
                return name, code, None, e

        with ThreadPoolExecutor(max_workers=self.READ_WORKERS) as ex:
            results = list(ex.map(_read, items))

        for name, code, row, exc in results:            # map 保序：登记顺序与规格一致
            if exc is not None:
                self._load_gap(name, '-', '读设计失败: %s' % str(exc)[:80])
                continue
            if not row:
                self._load_gap(name, '-', '表不存在（建壳阶段没建成？）')
                continue
            design = json.loads(row['desformDesignJson'])
            self.designs[name] = design
            self.codes[name] = code
            self.reg[name] = {w['name']: {'model': w.get('model'), 'key': w.get('key'),
                                          'type': w.get('type')}
                              for w in iter_widgets(design.get('list')) if w.get('name')}
        log('OK:read 读到 %d 张表的设计' % len(self.designs))
        if not self.designs:
            log('FAIL:read 一张表都没读到 —— 检查 app-id 是否正确、建壳阶段是否跑过')
            raise SystemExit(5)

    def load_dicts(self):
        r = DU.api_request('/sys/dict/getDictListByLowAppId', method='GET')
        recs = r.get('result') or []
        if isinstance(recs, dict):
            recs = recs.get('records') or []
        for x in recs:
            nm = x.get('dictName')
            if not nm:
                continue
            items = [{'value': i.get('itemValue', i.get('value')),
                      'label': i.get('itemText', i.get('label')),
                      'itemColor': i.get('itemColor') or ''}
                     for i in (x.get('dictItemsList') or x.get('items') or [])]
            self.dicts[nm] = {'dictCode': x.get('dictCode'), 'items': items}
        log('OK:dicts 回查到 %d 个应用字典' % len(self.dicts))

    # ---------- 表内字段解析 ----------

    def link_key(self, table, field):
        """本表某个关联记录控件的 key（汇总的 linkTable 要它）。"""
        info = (self.reg.get(table) or {}).get(field)
        return info.get('key') if info else None

    def src_info(self, target, field):
        """目标表某个字段的 {model,key,type}。

        走 `spec_infer.resolve`：精确 → 去空白后精确 → 唯一近似候选。
        宽松是必要的——规格里的「带出」写的是**显示名**，常和目标表真实字段名对不上。
        """
        reg = self.reg.get(target) or {}
        hit = resolve(list(reg), field)
        return reg.get(hit) if hit else None

    # ---------- 各类型补齐 ----------

    def _gap(self, table, field, reason):
        self.gaps.append({'table': table, 'field': field, 'reason': reason})

    def _load_gap(self, table, field, reason):
        """载入阶段的问题。**必须单独存**：run() 每轮会 `self.gaps = []` 重算，
        把载入问题混在里面会被第一轮直接清掉——实测踩到：app-id 传错时
        「读到 0 张表」却报「补丁全部落地，无缺口」，退出码还是 0。"""
        self.load_gaps.append({'table': table, 'field': field, 'reason': reason})

    def _register(self, fname, widget):
        for x in iter_widgets([widget]):
            if x.get('name'):
                self.reg.setdefault(fname, {})[x['name']] = {
                    'model': x.get('model'), 'key': x.get('key'), 'type': x.get('type')}

    def do_links(self, fname, design, seq):
        """关联记录 + 它带出的他表字段。

        ⚠️ 两件事**各自独立幂等**，不能因为「关联记录已存在」就 `continue` 掉带出字段：
        带出字段可能上一轮因源字段没就位而失败，这一轮还要重试（否则永远补不上）。
        """
        done = 0
        for lk in self.spec.get('links') or []:
            if lk.get('表') != fname:
                continue
            fld, tgt = lk.get('字段'), lk.get('目标')
            tgt_code = self.codes.get(tgt)
            if not tgt_code:
                self._gap(fname, fld, '目标表「%s」不在 spec 或未建成' % tgt)
                continue

            # ① 关联记录本身
            w = find_widget(design, fld)
            if w is not None:
                key = w.get('key') or ((self.reg.get(fname) or {}).get(fld) or {}).get('key')
            else:
                # 目标表的标题字段可能**本身就是一个他表字段**（明细表的标题是
                # 从它关联的上游表带出来的），此时它要等那张表的关联先建好。
                # 所以本函数必须可重入——run() 会跑有限几轮。
                title_model = ((self.reg.get(tgt) or {})
                               .get(self.spec['_title_of'].get(tgt) or '', {}).get('model'))
                if not title_model:
                    self._gap(fname, fld, '目标表「%s」的标题字段「%s」还没就位'
                              % (tgt, self.spec['_title_of'].get(tgt)))
                    continue
                show = [i['model'] for i in
                        (self.src_info(tgt, s) for s in (lk.get('带出') or [])) if i]
                res = DU.LINK_RECORD(fld, tgt_code, title_model, show_fields=show or None,
                                     show_mode=SHOW_MODE.get(lk.get('条数') or '单条', 'single'),
                                     show_type=SHOW_TYPE.get(lk.get('显示') or '卡片', 'card'))
                append_widget(design, res[0], seq); seq += 1
                self._register(fname, res[0])
                key = res[1]
                done += 1

            # ② 带出字段（与 ① 独立判定）
            if not key:
                continue
            for sf in (lk.get('带出') or []):
                if find_widget(design, sf):
                    continue
                info = self.src_info(tgt, sf)
                if not info:
                    cands = near_names(list(self.reg.get(tgt) or {}), sf)
                    self._gap(fname, '%s → 带出「%s」' % (fld, sf),
                              '目标表「%s」没有字段「%s」' % (tgt, sf) +
                              ('（是否想写：%s）' % '、'.join(cands) if cands else ''))
                    continue
                r2 = DU.LINK_FIELD(sf, key, info['model'],
                                   field_type=info.get('type') or 'input')
                append_widget(design, r2[0], seq); seq += 1
                self._register(fname, r2[0])
                done += 1
        return done

    def do_summaries(self, fname, design, seq):
        done = 0
        for sm in self.spec.get('summaries') or []:
            if sm.get('表') != fname:
                continue
            fld, lkf, col = sm.get('字段'), sm.get('关联字段'), sm.get('汇总列')
            if find_widget(design, fld):
                continue
            key = self.link_key(fname, lkf)
            if not key:
                self.gaps.append({'table': fname, 'field': fld,
                                  'reason': '本表没有关联记录「%s」（summary 的关联字段写错了？）' % lkf})
                continue
            # 汇总列在**关联目标表**里；目标表名 = links 里这条关联的目标
            tgt = next((l.get('目标') for l in (self.spec.get('links') or [])
                        if l.get('表') == fname and l.get('字段') == lkf), None)
            info = self.src_info(tgt, col) if tgt else None
            if not info:
                cands = near_names(list(self.reg.get(tgt) or {}), col) if tgt else []
                self.gaps.append({'table': fname, 'field': fld,
                                  'reason': '关联表「%s」没有列「%s」' % (tgt, col) +
                                            ('（是否想写：%s）' % '、'.join(cands) if cands else '')})
                continue
            # ⚠️ 对 link-record 汇总时 linkTable 传**控件 key（不带前缀）**，传 model 面板会读不到
            w = DU.SUMMARY(fld, key, info['model'],
                           summary_type=SUMMARY_TYPES.get(sm.get('方式') or '求和', 'inner-sum'))[0]
            append_widget(design, w, seq); seq += 1
            for x in iter_widgets([w]):
                if x.get('name'):
                    self.reg[fname][x['name']] = {'model': x.get('model'),
                                                  'key': x.get('key'), 'type': x.get('type')}
            done += 1
        return done

    def do_forms(self, fname, design):
        """字典绑定 / 自动编号规则 / 公式 —— 都作用于已存在的控件。"""
        done = 0
        f = next((x for x in self.form_items() if x['名称'] == fname), {})
        # 字典
        for fld, dname in (f.get('字典') or {}).items():
            w = find_widget(design, fld)
            if not w:
                self.gaps.append({'table': fname, 'field': fld,
                                  'reason': '字典绑定：控件不存在（没进 字段 列表？）'})
                continue
            dm = self.dicts.get(dname)
            if not dm:
                self.gaps.append({'table': fname, 'field': fld,
                                  'reason': '应用字典「%s」不存在' % dname})
                continue
            want = {'remote': 'dict', 'dictCode': dm['dictCode'], 'dictCodeAppId': self.app,
                    'isDictItem': True, 'showLabel': True, 'useColor': True,
                    'props': {'label': 'label', 'value': 'value'}, 'options': dm['items']}
            o = w.setdefault('options', {})
            # `remote` 不参与比较：服务端**回读时一律把它归一化成 false**，
            # 拿它判等会导致每次重跑都判定「没绑好」而重复写（实测踩到）。
            # 真正的绑定标志是 dictCode + isDictItem + 选项快照。
            if all(o.get(k) == v for k, v in want.items() if k != 'remote'):
                continue
            o.update(want)
            done += 1
        # 自动编号
        for fld, rule in (f.get('编号') or {}).items():
            w = find_widget(design, fld)
            if not w:
                self.gaps.append({'table': fname, 'field': fld, 'reason': '自动编号：控件不存在'})
                continue
            prefix, digits, with_date = (list(rule) + [None, None, None])[:3]
            rules = []
            if prefix:
                rules.append({'type': 'text', 'text': prefix, 'value': prefix})
            if with_date:
                rules.append({'type': 'create_date', 'dateFormat': 'yyyyMMdd',
                              'formatCustom': 'yyyyMMdd', 'format': 'yyyyMMdd'})
            rules.append({'type': 'number', 'mode': 2, 'start': 1, 'reset': 1,
                          'length': digits or 4, 'continue': True})
            o = w.setdefault('options', {})
            if o.get('numberRules') == rules:                  # 已设好 → 不重复写
                continue
            o['numberRules'] = rules
            done += 1
        # 公式
        for fld, expr in (f.get('公式') or {}).items():
            w = find_widget(design, fld)
            if not w:
                self.gaps.append({'table': fname, 'field': fld, 'reason': '公式：控件不存在'})
                continue
            built = self.build_expr(fname, expr)
            if not built:
                self.gaps.append({'table': fname, 'field': fld,
                                  'reason': '公式占位符对不上本表字段'})
                continue
            o = w.setdefault('options', {})
            if o.get('expression') == built and o.get('mode') == 'CUSTOM':
                continue                                        # 已设好 → 不重复写
            o.update({'type': 'number', 'mode': 'CUSTOM', 'expression': built,
                      'decimal': 2, 'thousand': True, 'emptyAsZero': True})
            done += 1
        return done

    def build_expr(self, table, expr):
        """把 `$字段中文名$` 换成 `$model$`。

        ⚠️ 按 `$` 分段处理，**不要**逐字符扫描：逐字符扫描会在复制原表达式的 `$` 之后
        又补一次 `$model$`，产出 `$$model$$`（双美元）。平台把它当空引用，公式**静默算不出**——
        接口照样 success。2026-09-16 实测踩到。
        """
        reg = self.reg.get(table) or {}
        names = sorted(reg, key=len, reverse=True)
        parts = expr.split('$')
        out = []
        for idx, part in enumerate(parts):
            if idx % 2 == 0:                    # 偶数段 = 字面量（运算符、括号、数字）
                out.append(part)
                continue
            if part in reg:                     # 奇数段 = 占位字段名
                out.append('$%s$' % reg[part]['model'])
                continue
            # 占位名写得不完整时按最长前缀切，剩下的原样接回去
            hit = next((n for n in names if part.startswith(n)), None)
            if not hit:
                return None
            out.append('$%s$%s' % (reg[hit]['model'], part[len(hit):]))
        return ''.join(out)

    # ---------- 主流程 ----------

    MAX_ROUNDS = 3      # 有界重试：见 do_links 里「目标表标题本身是他表字段」的说明

    def run(self, only=None):
        self.spec['_title_of'] = {f['名称']: f.get('标题') for f in self.form_items()}
        self.load_designs()
        self.load_dicts()
        only = set(only or [])
        touched = set()
        for rnd in range(1, self.MAX_ROUNDS + 1):
            self.gaps = []                       # 每轮重算：上一轮补齐的缺口应消失
            changed = 0
            for f in self.form_items():
                fname = f['名称']
                if only and fname not in only:
                    continue
                design = self.designs.get(fname)
                if design is None:
                    continue
                seq = 1
                n1 = self.do_links(fname, design, seq)
                n2 = self.do_summaries(fname, design, seq + n1)
                n3 = self.do_forms(fname, design)
                n = n1 + n2 + n3
                if not n:
                    continue
                if self.dry_run:
                    log('OK:dry %s 待补 %d 个（关联%d 汇总%d 其它%d）' % (fname, n, n1, n2, n3))
                    continue
                preserve_dicts(design)
                path = os.path.join(self.tmpdir, 'patch_%s.json' % self.codes[fname])
                try:
                    with open(path, 'w', encoding='utf-8') as fh:
                        json.dump(design, fh, ensure_ascii=False)
                    # 走官方保存通道：它会补 linkData 的 sqParam、取最新 updateCount、并刷缓存
                    DU.save_design_from_file(self.codes[fname], path)
                    changed += 1
                    touched.add(fname)
                    log('OK:patch %s 补 %d 个' % (fname, n))
                except Exception as e:                            # noqa: BLE001
                    self._gap(fname, '-', '保存失败: %s' % str(e)[:90])
                    log('FAIL:patch %s %s' % (fname, str(e)[:90]))
                finally:
                    if os.path.exists(path):
                        os.remove(path)
            if not changed:
                break
            if rnd > 1:
                log('OK:round%d 又补齐 %d 张表' % (rnd, changed))
        log('OK:done 共改动 %d 张表' % len(touched))
        return self.report()

    def report(self):
        self.gaps = self.load_gaps + self.gaps
        if not self.gaps:
            log('OK:delivery 补丁全部落地，无缺口')
            return 0
        reasons = {}
        for g in self.gaps:
            reasons.setdefault(g['reason'], []).append('%s.%s' % (g['table'], g['field']))
        log('FAIL:delivery 有 %d 处未落地 —— 按原因分组：' % len(self.gaps))
        for why, items in sorted(reasons.items(), key=lambda kv: -len(kv[1])):
            log('   [%d] %s' % (len(items), why))
            for it in items[:6]:
                log('        - %s' % it)
            if len(items) > 6:
                log('        …同类另 %d 个' % (len(items) - 6))
        path = os.path.join(self.tmpdir, 'patch_gaps.json')
        try:
            with open(path, 'w', encoding='utf-8') as fh:
                json.dump(self.gaps, fh, ensure_ascii=False, indent=1)
            log('  完整清单已落盘：%s' % path)
        except Exception as e:                                    # noqa: BLE001
            log('  (清单落盘失败: %s)' % str(e)[:80])
        return 5


def main():
    ap = argparse.ArgumentParser(description='补丁阶段：补齐建壳阶段建不出来的字段')
    ap.add_argument('--api-base', required=True)
    ap.add_argument('--token', required=True)
    ap.add_argument('--tenant-id', required=True)
    ap.add_argument('--app-id', required=True)
    ap.add_argument('--spec', required=True)
    ap.add_argument('--only', default='', help='只处理这些表（逗号分隔）')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    with open(a.spec, encoding='utf-8') as fh:
        spec = json.load(fh)

    init_lowapp(a.api_base, a.token, tenant_id=int(a.tenant_id), app_id=a.app_id)
    DU.init_api(a.api_base.rstrip('/'), a.token)

    eng = Engine(spec, a.api_base, a.token, a.tenant_id, a.app_id, dry_run=a.dry_run)
    only = [x.strip() for x in a.only.split(',') if x.strip()]
    raise SystemExit(eng.run(only or None))


if __name__ == '__main__':
    main()
