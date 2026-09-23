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
    '平均': 'inner-average', '平均值': 'inner-average', '均值': 'inner-average',
    '最大': 'inner-max', '最大值': 'inner-max', '最小': 'inner-min', '最小值': 'inner-min',
    '计数': 'inner-record-count', '记录数': 'inner-record-count', '记录数量': 'inner-record-count',
    '条数': 'inner-record-count', '总数': 'inner-record-count', '数量': 'inner-record-count',
    # ⚠️ 「记录数量」与「已填计数」是两个不同的汇总方式，别混：
    #   inner-record-count     = 记录数量（统计子表**总行数**，不引用任何数据列）
    #   inner-completed-count  = 已填计数（统计**已填写的行数**）
    # 且 inner-record-count 是**特殊结构**：`field` 要填类型字符串 "inner-record-count"、
    # `summary` 留空 —— 按普通结构写成 field=<某列>/summary=inner-record-count 时，
    # 设计器认不出这个组合，会把原始码 `inner-record-count` 直接显示在「统计方式」里
    # （2026-09-20 用户实测发现）。desform_creator 里有该特殊结构的自动解析。
    '已填计数': 'inner-completed-count', '未填计数': 'inner-incompletely-count',
}
SHOW_MODE = {'单条': 'single', '多条': 'many', 'single': 'single', 'many': 'many'}
SHOW_TYPE = {'卡片': 'card', '下拉': 'select', '表格': 'table',
             'card': 'card', 'select': 'select', 'table': 'table'}
LAYOUT_TYPES = {'card', 'divider', 'text', 'tabs', 'grid'}


def log(*a):
    print(*a, flush=True)


def link_modes(link):
    """关联记录控件的 (showMode, showType)。

    ⚠️ **`条数="单条"` 只有「卡片 / 下拉」两档，没有「表格」。** 写 `显示:"表格"` 是非法组合：
    落库 `showType:'table'`，前端就真按表格渲染（2026-09-20 用户实测：8 个单条关联
    全被渲染成表格，需求原文写的是「单条」、作者照抄了「显示=表格」）。
    非法组合**夹成卡片**（单条没点名「下拉」时的默认档），并打一行 WARN ——
    静默夹掉只是换了个地方再静默一次，日志是这条防线唯一的可见出口。

    ⚠️ **别拿「线上某个应用长这样」当合法性依据**（2026-09-21 踩到）。曾回读线上一个
    进销存模版，看到 8 个 `showMode=single / showType=table` 就判定「这是既有形态、
    夹取是错的」并**把校验撤销了** —— **因果搞反了**：那 8 个正是同一类错误污染出来的
    **坏数据**，设计器产不出、也修不回来（用户在设计器里根本找不到「表格」这一项）。
    线上应用**不是标准**，它自己就可能不对；与设计器能力冲突时**以设计器为准**。
    """
    mode = SHOW_MODE.get(link.get('条数') or '单条', 'single')
    stype = SHOW_TYPE.get(link.get('显示') or '卡片', 'card')
    if mode == 'single' and stype not in ('card', 'select'):
        log('WARN:单条关联 %s.%s 的显示方式「%s」非法（单条只有卡片/下拉）→ 按卡片建'
            % (link.get('表'), link.get('字段'), link.get('显示')))
        stype = 'card'
    return mode, stype


# ---------------- 控件树遍历 ----------------

def iter_widgets(nodes):
    """（薄封装）控件树遍历**统一走 `design_utils.iter_widgets`**。

    原先本文件自带一份实现，`regroup_layout` 和临时脚本又各有一份 —— 三份对
    「card 的子控件放在 `list` 还是 `columns`」的假设不一致。2026-09-20 实测：
    只走 `columns` 的那份在一张 47 表的应用上**一个控件都找不到**，且不报错
    （只是静默返回空）。收敛成一份，改解析只改 `design_utils`。

    参数沿用历史形态：收 **list**（`design['list']` 或 `[widget]`），也兼容 dict。
    """
    from design_utils import iter_widgets as _iw
    for x in _iw(nodes):
        yield x

def find_widget(design, name):
    hit = None
    for w in iter_widgets(design.get('list')):
        if w.get('name') == name:
            if w.get('type') != 'divider':          # 同名分隔符排后（2026-09-22 三个应用都撞到）
                return w
            hit = hit or w
    return hit


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

    def _required_of(self, fname):
        f = next((x for x in self.form_items() if x['名称'] == fname), None) or {}
        return set(f.get('必填') or [])

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
                # 关联记录的「显示字段」：显式 `显示字段` 优先，没写时沿用 `带出`
                # （历史上是同一条声明 —— `带出` 既建他表字段、又充当展示列）。
                # **只展示、不带出**的列必须显式写 `显示字段`，否则规格表达不了。
                # 2026-09-20 实测：Tabs 里的关联记录要展示 5~6 列但一个带出字段都没有，
                # 只能手写补丁；而手写时把形状写成 [{"field":…,"show":true}] 是**静默失效**的
                # （引擎只认 ["<model>", …] 裸字符串数组，回落到只显示标题一列）。
                show_names = lk.get('显示字段') or (lk.get('带出') or [])
                show = [i['model'] for i in
                        (self.src_info(tgt, s) for s in show_names) if i]
                _mode, _stype = link_modes(lk)
                # 目标表 == 本表 → 自关联树：必须 is_self=True（engine-contract C6：
                # 顶层 isSelf + options 的 isSelf/valueSplit + advancedSetting 的 valueSplit
                # 三处都要写全；缺 options 那两个键时隐藏控件会在列表里露成一列、
                # 且父级回写/树展开认不到它）。
                res = DU.LINK_RECORD(fld, tgt_code, title_model, show_fields=show or None,
                                     show_mode=_mode, show_type=_stype,
                                     is_self=(tgt == fname))
                if fld in self._required_of(fname):          # 规格「必填」点名了关联记录
                    for _w in iter_widgets([res[0]]):
                        if _w.get('type') == 'link-record':
                            _w.setdefault('options', {})['required'] = True
                            _w['rules'] = [{'required': True, 'message': '${title}必须填写'}]
                append_widget(design, res[0], seq); seq += 1
                self._register(fname, res[0])
                key = res[1]
                done += 1

            # ② 带出字段（与 ① 独立判定）
            #   `带出`     = 建出的控件**与目标表字段同名**；
            #   `带出映射` = 本表控件名 ≠ 目标表字段名（如两个仓库都带「仓库名称/仓库编码」，
            #                要分别落成「换货入库仓库名称/编码」与「换货出库仓库名称/编码」）。
            #   saveType 一律 `'save'`（存储数据）：需求写「带出/存储数据」的字段是流程的定位键，
            #   `'view'`（仅显示）既不落库、也不能作流程条件 —— 引擎侧会静默取到空值。
            if not key:
                continue
            wanted = [(sf, sf) for sf in (lk.get('带出') or [])]
            wanted += [(local, src) for local, src in (lk.get('带出映射') or {}).items()]
            for local_name, src_name in wanted:
                if find_widget(design, local_name):
                    continue
                info = self.src_info(tgt, src_name)
                if not info:
                    cands = near_names(list(self.reg.get(tgt) or {}), src_name)
                    self._gap(fname, '%s → 带出「%s」' % (fld, local_name),
                              '目标表「%s」没有字段「%s」' % (tgt, src_name) +
                              ('（是否想写：%s）' % '、'.join(cands) if cands else ''))
                    continue
                r2 = DU.LINK_FIELD(local_name, key, info['model'],
                                   field_type=info.get('type') or 'input',
                                   save_type='save')
                append_widget(design, r2[0], seq); seq += 1
                self._register(fname, r2[0])
                done += 1
        return done

    def do_relay(self, form, design, seq):
        """隐藏**中转字段**：默认值 = 「本表指向父单据的关联控件」上的某个字段。

        规格形态：写在**表（form）**上，`"中转字段": {"<本表字段名>": ("<父表名>", "<父表字段名>")}`

        ⚠️ **为什么需要它**（2026-09-21 用户手工跑通后回抄）：
        记账子流程要把 `库存实时统计.仓库信息`（一个 **link-record**）写对，
        可它手里只有**明细行**。明细行上原本只有「入库仓库编码/入库仓库名称」这类
        **link-field** —— 那是纯文本，只有一个值、**不带指回仓库记录的指针**，
        拿它写不进 link-record 字段（写进去页面上是空的）。
        解法：明细表上挂一个隐藏字段，默认值走设计器的「其他工作表」取值
        （落库是 compose 的 `$<父关联控件 key>.<父表字段 model>$`），
        于是**每一行明细都物理带着**一个真的仓库关联记录，子流程 `ref()` 就能取到。

        实测要点（别退回去）：
        · 控件类型是 **`input`**（不是 link-record）—— 它只是个**搬运值的信封**，
          存的是记录的 id；流程能把它写进 link-record 字段，是因为**目标字段**是
          link-record，两边存的都是记录 id。
        · `$key.model$` 里**前半是本表那条关联控件的 key（不是 model）**，别写串。
        · 必须 `hidden=True`：机制字段，不该出现在表单上让人填。
        · 默认值**只在新增那一刻算**。父单据的对应字段为空时，这行明细的中转字段就是空的，
          下游建出来的行仍然没有记录 —— 所以**父单据必须先把那个字段写上**。
        """
        done = 0
        fname = form['名称']
        for name, pair in (form.get('中转字段') or {}).items():
            if not (isinstance(pair, (list, tuple)) and len(pair) == 2):
                self._gap(fname, name, '中转字段的值要写成 ("父表名", "父表字段名")')
                continue
            parent, pfield = pair
            if find_widget(design, name):
                continue                       # 幂等：已存在就跳过
            pcode = self.codes.get(parent)
            if not pcode:
                self._gap(fname, name, '父表「%s」不在 spec 或未建成' % parent)
                continue
            # ① 本表上指向父单据的那个关联控件（按 sourceCode 认，不按名字猜）
            host = None
            for w in iter_widgets(design.get('list')):
                o = w.get('options')
                if (w.get('type') == 'link-record' and isinstance(o, dict)
                        and o.get('sourceCode') == pcode):
                    host = w
                    break
            if not host:
                self._gap(fname, name,
                          '本表没有指向「%s」的关联记录控件，中转字段无处挂' % parent)
                continue
            info = self.src_info(parent, pfield)
            if not info:
                cands = near_names(list(self.reg.get(parent) or {}), pfield)
                self._gap(fname, name, '父表「%s」没有字段「%s」' % (parent, pfield) +
                          ('（是否想写：%s）' % '、'.join(cands) if cands else ''))
                continue
            expr = "$%s.%s$" % (host.get('key'), info['model'])
            res = DU.INPUT(name, hidden=True, default_expr=expr)
            append_widget(design, res[0], seq); seq += 1
            self._register(fname, res[0])
            log('  · %s.%s ← %s.%s（隐藏中转，默认值 %s）'
                % (fname, name, parent, pfield, expr))
            done += 1
        return done

    def _save_one(self, fname, tag):
        """整单保存 + 一次瞬态重试（后端偶发 500 / 连接瞬断，重跑就好 —— 2026-09-22 进销存 R3）。"""
        preserve_dicts(self.designs[fname])
        path = os.path.join(self.tmpdir, '%s_%s.json' % (tag, self.codes[fname]))
        try:
            with open(path, 'w', encoding='utf-8') as fh:
                json.dump(self.designs[fname], fh, ensure_ascii=False)
            for attempt in (1, 2):
                try:
                    DU.save_design_from_file(self.codes[fname], path)
                    return None
                except Exception as e:                     # noqa: BLE001
                    if attempt == 2:
                        return str(e)[:90]
                    log('WARN:%s %s 保存失败，2 秒后重试一次：%s' % (tag, fname, str(e)[:70]))
                    time.sleep(2)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def do_two_way(self):
        """`links` 里声明了 `双向` 的关联记录，两侧互填 `options.twoWayModel`。

        契约（`desform-link-record.md` §六）：A 的 link-record 设 `sourceCode=B_code`，
        B 的设 `sourceCode=A_code`，**双方 `twoWayModel` 互指对方的 model**（指 model，
        不是 key），选择关联时自动在两边建立关系。

        `双向` 取值：
          `true`       → 目标表里**恰好一个** link-record 指回本表，自动用它；
                         0 个或 ≥2 个都是歧义 → 记缺口，**不猜**（如销售合同有
                         「客户目录 / 合同相对方1/2/3」四个控件都指回客户目录）。
          `"<控件名>"` → 指名目标表里回指本表的那个控件。

        ⚠️ 必须在**主循环之后**单独跑：两侧控件可能由不同表的补丁建出来，主循环按表
        顺序处理时对端可能还不存在。
        ⚠️ 2026-09-20 补：此前 `patch_fields` 里 `twoWayModel` **一处都没有**，规格也
        表达不了「双向」——需求被静默降级，接口全绿而应用里 `twoWayModel` 全空。
        """
        tw = [lk for lk in (self.spec.get('links') or []) if lk.get('双向')]
        if not tw:
            return 0
        dirty, n = set(), 0
        for lk in tw:
            table, fld, tgt = lk.get('表'), lk.get('字段'), lk.get('目标')
            d_local, d_peer = self.designs.get(table), self.designs.get(tgt)
            if not self.codes.get(tgt) or d_local is None or d_peer is None:
                self._gap(table, fld, '双向：目标表「%s」尚未就位' % tgt)
                continue
            local = find_widget(d_local, fld)
            if local is None:
                self._gap(table, fld, '双向：本表关联记录控件还没建出来')
                continue

            peers = [w for w in iter_widgets(d_peer.get('list'))
                     if w.get('type') == 'link-record'
                     and (w.get('options') or {}).get('sourceCode') == self.codes.get(table)]
            want = lk.get('双向')
            if isinstance(want, str) and want.strip():
                peers = [w for w in peers if w.get('name') == want.strip()]
                if not peers:
                    self._gap(table, fld, '双向：目标表「%s」里没有名为「%s」的回指控件'
                              % (tgt, want))
                    continue
            if len(peers) != 1:
                self._gap(table, fld,
                          '双向：目标表「%s」指回本表的 link-record 有 %d 个（%s）—— '
                          '`双向` 写成要指定的那个控件名'
                          % (tgt, len(peers),
                             '、'.join(sorted(w.get('name') or '?' for w in peers)) or '无'))
                continue
            peer = peers[0]

            lo = local.setdefault('options', {})
            po = peer.setdefault('options', {})
            lm, pm = local.get('model'), peer.get('model')
            if lo.get('twoWayModel') == pm and po.get('twoWayModel') == lm:
                continue                                   # 已互指，幂等
            lo['twoWayModel'] = pm
            po['twoWayModel'] = lm
            dirty.update((table, tgt))
            n += 1
            log('OK:two-way %s.%s <-> %s.%s' % (table, fld, tgt, peer.get('name')))

        if self.dry_run:
            return n
        for fname in sorted(dirty):
            err = self._save_one(fname, 'twoway')
            if err:
                self._gap(fname, '-', '双向关联保存失败: %s' % err)
                log('FAIL:two-way %s %s' % (fname, err))
        return n

    def retry_two_way(self):
        """第二趟双向收敛：首趟若报「尚未就位 / 还没建出来」，把相关表的设计**从真机重读**再试一次。

        这些控件是本次补丁刚建出来的，首趟判失败后原样重跑一趟就全好
        （2026-09-22 项目管理 R3：7 对全中、首趟 exit 5），不该让人白返工一轮。"""
        stale = [g for g in self.gaps
                 if '双向：' in g.get('reason', '') and ('尚未就位' in g['reason'] or '还没建出来' in g['reason'])]
        if not stale:
            return 0
        tables = sorted({g['table'] for g in stale} |
                        {lk.get('目标') for lk in (self.spec.get('links') or []) if lk.get('双向')})
        for t in tables:
            code = self.codes.get(t)
            if not code:
                continue
            try:
                self.designs[t] = json.loads(DU.query_form(code)['desformDesignJson'])
            except Exception as e:                         # noqa: BLE001
                log('WARN:two-way 重读 %s 失败：%s' % (t, str(e)[:70]))
        self.gaps = [g for g in self.gaps if g not in stale]
        log('OK:two-way 首趟 %d 对未就位 → 重读 %d 张表后再收敛一轮' % (len(stale), len(tables)))
        return self.do_two_way()

    def do_summaries(self, fname, design, seq):
        done = 0
        for sm in self.spec.get('summaries') or []:
            if sm.get('表') != fname:
                continue
            fld, lkf, col = sm.get('字段'), sm.get('关联字段'), sm.get('汇总列')
            if find_widget(design, fld):
                continue
            # 「方式」写了却不认识 → 以前静默回落 inner-sum（2026-09-22 销售管理「最大值」实测：两行 0.06 求出 0.12）
            if sm.get('方式') and sm['方式'] not in SUMMARY_TYPES:
                self._gap(fname, fld, '汇总方式「%s」不认识，可用：%s' % (sm['方式'], '、'.join(sorted(SUMMARY_TYPES))))
                continue
            key = self.link_key(fname, lkf)
            if not key:
                self.gaps.append({'table': fname, 'field': fld,
                                  'reason': '本表没有关联记录「%s」（summary 的关联字段写错了？）' % lkf})
                continue
            stype = SUMMARY_TYPES.get(sm.get('方式') or '求和', 'inner-sum')
            if stype == 'inner-record-count':
                # 特殊结构：field 填类型字符串、summary 留空（desform-widget-options 汇总节）。
                # 按普通结构写 field=<列>/summary=inner-record-count 设计器认不出、不计数（2026-09-22 项目管理 R2）
                w = DU.SUMMARY(fld, key, 'inner-record-count', summary_type='')[0]
                append_widget(design, w, seq); seq += 1
                for x in iter_widgets([w]):
                    if x.get('name'):
                        self.reg[fname][x['name']] = {'model': x.get('model'),
                                                      'key': x.get('key'), 'type': x.get('type')}
                done += 1
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
            # 带条件的汇总：规格 `条件` → options.filter。
            # 「源字段」写的是**目标表**上的字段名。落库形状三件套缺一不可：
            # rule 大写 / sqParam.rule 小写 / value 恒为数组 —— 漏了 sqParam 平台会
            # **静默忽略整条条件**（保存、回读都正常，症状是"不该算的记录也被算进来"）。
            sflt = None
            conds = sm.get('条件') or []
            if conds:
                rules, bad = [], None
                for c in conds:
                    ci = self.src_info(tgt, c.get('源字段')) if tgt else None
                    if not ci:
                        bad = c.get('源字段')
                        break
                    rules.append({
                        'model': ci['model'],
                        'rule': c.get('rule') or 'EQ',
                        'valueType': 'fixed',
                        'value': list(c.get('value') or []),
                        'valueText': c.get('valueText') or '',
                        'sqParam': {'type': c.get('type') or 'select',
                                    'rule': c.get('sqRule') or 'eq'},
                    })
                if bad:
                    self._gap(fname, fld, '汇总条件里的源字段「%s」在「%s」里没有' % (bad, tgt))
                    continue
                sflt = {'enabled': True, 'matchType': 'AND', 'rules': rules}
            # ⚠️ 对 link-record 汇总时 linkTable 传**控件 key（不带前缀）**，传 model 面板会读不到
            w = DU.SUMMARY(fld, key, info['model'], summary_type=stype, filter=sflt)[0]
            append_widget(design, w, seq); seq += 1
            for x in iter_widgets([w]):
                if x.get('name'):
                    self.reg[fname][x['name']] = {'model': x.get('model'),
                                                  'key': x.get('key'), 'type': x.get('type')}
            done += 1
        return done

    def do_opt_flags(self, fname, design, seq):
        """规格 `选项` 统一施加 —— **所有控件类型**都要吃这一档。

        `build_app.split_fields` 只把 `选项` 传给**建壳字段**（标量）；走补丁建出来的
        link-record / link-field / summary **一个都拿不到**。表现是静默的：字段在、
        类型对、save/回读全绿，只是「新增时隐藏 / 禁用 / 不可选」全没生效
        （2026-09-22 项目管理 R6 实测 20 处，含 6 个 hiddenOnAdd、2 个 disabled、
        2 个 hidden 的自关联控件）。

        幂等：只写与本表规格不一致的键。
        """
        f = next((x for x in self.form_items() if x['名称'] == fname), {})
        extras = f.get('选项') or {}
        n = 0
        for name, kv in extras.items():
            hit = False
            for w in iter_widgets(design.get('list')):
                if w.get('name') != name or w.get('type') in LAYOUT_TYPES:
                    continue
                hit = True
                o = w.setdefault('options', {})
                for k, v in kv.items():
                    if o.get(k) != v:
                        o[k] = v
                        n += 1
            if not hit:
                self._gap(fname, name, '构造选项：控件不存在')
        return n

    def do_forms(self, fname, design, seq=900):
        """字典绑定 / 自动编号规则 / 公式。字典/编号作用于已存在控件；
        公式**控件不存在时会新建**（对已建应用补一个公式字段，2026-09-22 进销存 R2）。"""
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
            built = self.build_expr(fname, expr)
            if not built:
                self.gaps.append({'table': fname, 'field': fld,
                                  'reason': '公式占位符对不上本表字段'})
                continue
            w = find_widget(design, fld)
            if not w:
                # 建壳阶段跳过了已存在的表 → 规格里**新增**的公式字段原先无处落地，只能手写脚本
                # （2026-09-22 进销存 R2「[2] 公式：控件不存在」+ exit 5）。这里直接建出来。
                nw = DU.FORMULA(fld, mode='CUSTOM', expression=built)[0]
                append_widget(design, nw, seq); seq += 1
                for x in iter_widgets([nw]):
                    if x.get('name'):
                        self.reg[fname][x['name']] = {'model': x.get('model'),
                                                      'key': x.get('key'), 'type': x.get('type')}
                done += 1
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
                n3 = self.do_relay(f, design, seq + n1 + n2)
                n4 = self.do_forms(fname, design, seq + n1 + n2 + n3)
                n5 = self.do_opt_flags(fname, design, seq + n1 + n2 + n3 + n4)
                n = n1 + n2 + n3 + n4 + n5
                if not n:
                    continue
                if self.dry_run:
                    log('OK:dry %s 待补 %d 个（关联%d 汇总%d 中转%d 其它%d）'
                        % (fname, n, n1, n2, n3, n4))
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
        # 双向关联放在主循环之后：两侧控件可能由不同表的补丁创建，且它跨表改两份设计
        n_tw = self.do_two_way()
        n_tw += self.retry_two_way()
        if n_tw:
            log('OK:two-way 双向关联互指 %d 组' % n_tw)
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
