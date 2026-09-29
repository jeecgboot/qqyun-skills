# -*- coding: utf-8 -*-
"""建后结构补丁（build_app 之后跑）：规格语言表达不了的档位，用一份声明式配置一次补齐。
逻辑来自 2026-09-21 CRM 24 表应用真机跑通的补丁脚本，参数化后收编；不改任何现有脚本。

  python postbuild_struct.py --api-base URL --token T --tenant-id N --app-id A \
         --config postbuild_config.py [--work DIR] [--dry-run]

前置：先跑 postbuild_probe.py（本脚本从 {work}/probe.json 取「表名→编码」）。
配置文件是一段 Python，只需定义用到的变量（全部可省略），写法见 references/postbuild-kit.md：

  DELETE_THEN_MOVE / TO_LINKFIELD / SUBTABLES / FILTERS / CREATE_MODE / LINK_TITLE /
  NUMBER_RULES / FIELD_NUMBER_RULES / LINKDATA / OPT_FLAGS / WIDTH / RENAME

约定：
- 配置里一律写字段中文名，脚本解析 key/model；同名时优先取非分隔符控件，
  要点名分隔符写 '名称#divider'。
- RENAME 最后执行，所以其它项都用**改名前**的名字。
- 子表转换只动 isSubTable / model / 两侧 twoWayModel，**不碰汇总 linkTable**（它存控件 key）。
- 只保存真正有变化的表；--dry-run 只报告不保存。重复执行幂等。
"""
import sys, os, json, argparse, tempfile, copy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from desform_lowapp_utils import init_lowapp
from desform_utils import query_form, save_design_from_file, save_auth_from_design

ap = argparse.ArgumentParser()
ap.add_argument('--api-base', required=True)
ap.add_argument('--token', required=True)
ap.add_argument('--tenant-id', required=True)
ap.add_argument('--app-id', required=True)
ap.add_argument('--config', required=True)
ap.add_argument('--work', default=None)
ap.add_argument('--dry-run', action='store_true')
A = ap.parse_args()
AID = A.app_id
from skill_temp_path import app_workdir  # noqa: E402
WORK = A.work or app_workdir(AID, create=False)   # 该应用的工作目录（probe 建的；读不到就报缺 probe.json）
_pp = os.path.join(WORK, 'probe.json')
if not os.path.exists(_pp):
    sys.exit('缺少 %s —— 先跑 postbuild_probe.py' % _pp)
PROBE = json.load(open(_pp, encoding='utf-8'))
CODE = {t: v['code'] for t, v in PROBE.items()}
CODE2T = {v: k for k, v in CODE.items()}

# ── 配置：全部可省略 ──
DELETE_THEN_MOVE = {}    # {表: [(要删控件名, 要删类型, 搬入原位的控件名, 其类型)]}
TO_LINKFIELD = {}        # {表: [(本表字段, 本表关联控件, 源表, 源表字段[, 'view'])]}  建错类型 → 他表字段（保留 key/model）
                         # 第 5 项写 'view' = 仅显示（需求明写「仅显示」时；默认存储数据，流程要用就别写 view）
SUBTABLES = []           # [(主表, 主表子表控件, 明细表, 明细回指字段)]
FILTERS = []             # [(本表, 本表关联控件, 目标表, 目标表字段, 本表比较字段)]  记录范围：目标字段 等于 本表字段
CREATE_MODE = []         # [(主表, 子表控件, 明细表, 明细里用于批量选择的关联字段)]
LINK_TITLE = {}          # {表: {关联控件: 目标表里作标题的字段}}
NUMBER_RULES = {}        # {表: {编号字段: [numberRules 段...]}}
FIELD_NUMBER_RULES = []  # [(表, 编号字段, 前缀, 引用的本表字段, 连接符, 流水位数)] → 前缀{字段}连接符+N位流水
LINKDATA = []            # [(表, 字段, 目标表, 目标字段)]  下拉选项来自工作表
OPT_FLAGS = {}           # {表: {字段: {required/hidden/hiddenOnAdd/disabled/readonly: bool}}}
WIDTH = {}               # {表: {字段: autoWidth 百分比}}
RENAME = {}              # {表: {旧名: 新名}}
exec(compile(open(A.config, encoding='utf-8').read(), A.config, 'exec'), globals())

TID = int(A.tenant_id) if str(A.tenant_id).isdigit() else A.tenant_id
init_lowapp(A.api_base, A.token, tenant_id=TID, app_id=AID)

DESIGNS, ORIG, NOTES, MISS = {}, {}, [], []


def design(t):
    if t not in CODE:
        raise KeyError('应用里没有工作表「%s」（probe.json 过期就重跑 postbuild_probe.py）' % t)
    if t not in DESIGNS:
        DESIGNS[t] = json.loads(query_form(CODE[t])['desformDesignJson'])
        ORIG[t] = copy.deepcopy(DESIGNS[t])
    return DESIGNS[t]


def walk(node, out=None, parent=None, idx=None):
    out = [] if out is None else out
    if isinstance(node, dict):
        if node.get('type') and node.get('key') and node.get('type') not in ('card', 'grid'):
            out.append((node, parent, idx))
        for k in ('list', 'columns', 'panes'):
            v = node.get(k)
            if isinstance(v, list):
                for i, it in enumerate(v):
                    walk(it, out, v, i)
    elif isinstance(node, list):
        for i, it in enumerate(node):
            walk(it, out, node, i)
    return out


def widgets(t):
    return walk(design(t).get('list') or [])


def find_slot(t, name, wtype=None):
    """按中文名找控件。'名称#类型' 或 wtype 点名类型；否则同名时优先非分隔符。"""
    if wtype is None and '#' in name:
        name, wtype = name.rsplit('#', 1)
    hit = None
    for w, p, i in widgets(t):
        if w.get('name') != name:
            continue
        if wtype is not None:
            if w.get('type') == wtype:
                return w, p, i
            continue
        if w.get('type') != 'divider':
            return w, p, i
        hit = hit or (w, p, i)
    return hit or (None, None, None)


def find(t, name, wtype=None):
    return find_slot(t, name, wtype)[0]


def model_of(t, name, wtype=None):
    w = find(t, name, wtype)
    return w['model'] if w else None


def note(t, msg):
    NOTES.append('  %s: %s' % (t, msg))


def miss(msg):
    MISS.append(msg)


# ── 1. 删多余控件 + 搬位 ──
for t, jobs in DELETE_THEN_MOVE.items():
    for dead, dtype, live, ltype in jobs:
        dw, dp, di = find_slot(t, dead, dtype)
        lw, lp, li = find_slot(t, live, ltype)
        if dw is None or lw is None:
            continue                       # 已处理过，幂等跳过
        lp.pop(li)
        _w, dp2, di2 = find_slot(t, dead, dtype)
        dp2[di2] = lw
        note(t, '删空壳「%s」，「%s」搬入原位' % (dead, live))

# ── 2. 建错类型 → 他表字段（保留 key/model，整体替换 options）──
for t, jobs in TO_LINKFIELD.items():
    for job in jobs:
        fname, lrname, src_t, src_f = job[:4]
        save_type = 'view' if len(job) > 4 and job[4] == 'view' else 'save'
        w, lr, sw = find(t, fname), find(t, lrname, 'link-record'), find(src_t, src_f)
        if w is None or lr is None or sw is None:
            miss('%s 他表字段 %s（关联=%s 源=%s.%s）' % (t, fname, lrname, src_t, src_f)); continue
        if w.get('type') == 'link-field':
            continue
        so, old = sw.get('options') or {}, w.get('options') or {}
        w['type'], w['className'], w['icon'] = 'link-field', 'form-link-field', 'icon-field'
        w['options'] = {
            'linkRecordKey': lr['key'], 'showField': sw['model'], 'saveType': save_type,
            'fieldType': sw['type'],
            'fieldOptions': {k: so[k] for k in ('type', 'format', 'precision', 'unitText',
                                                'options', 'dictCode') if k in so},
            'hidden': old.get('hidden', False), 'hiddenOnAdd': old.get('hiddenOnAdd', False),
            'fieldNote': old.get('fieldNote', ''), 'autoWidth': old.get('autoWidth', 50)}
        w.pop('rules', None)
        note(t, '「%s」改为他表字段 ← %s.%s' % (fname, src_t, src_f))

# ── 3. 子表转换：只动 isSubTable / model / 两侧 twoWayModel；不碰汇总 linkTable ──
OLD_MODELS = {}
for master, mf, det_t, det_f in SUBTABLES:
    mw, dw = find(master, mf, 'link-record'), find(det_t, det_f, 'link-record')
    if mw is None or dw is None:
        miss('子表 %s.%s ↔ %s.%s' % (master, mf, det_t, det_f)); continue
    old_model, new_model = mw['model'], 'sub_table_design_' + mw['key']
    mw['isSubTable'] = True
    mw['model'] = new_model
    mo = mw.setdefault('options', {})
    mo['showMode'], mo['showType'], mo['twoWayModel'] = 'many', 'table', dw['model']
    do = dw.setdefault('options', {})
    do['showMode'], do['showType'], do['twoWayModel'] = 'single', 'card', new_model
    if old_model != new_model:
        OLD_MODELS[old_model] = (master, mf)
        note(master, '子表转换「%s」→ %s' % (mf, new_model))

# ── 4. 记录范围 ──
def sq_type(w):
    o = w.get('options') or {}
    if w['type'] == 'link-field':
        return o.get('fieldType') or 'input'
    if w['type'] == 'date':
        return o.get('type') or 'date'
    return w['type']


for t, lrname, tgt_t, tgt_f, self_f in FILTERS:
    lr, sw, lw = find(t, lrname, 'link-record'), find(tgt_t, tgt_f), find(t, self_f)
    if not (lr and sw and lw):
        miss('记录范围 %s.%s（%s.%s = 本表 %s）' % (t, lrname, tgt_t, tgt_f, self_f)); continue
    lr.setdefault('options', {})['dataSelectAuth'] = 'all'
    lr['options']['filters'] = [{'matchType': 'AND', 'rules': [{
        'model': sw['model'], 'rule': 'EQ', 'valueType': 'field',
        'value': [lw['model']], 'sqParam': {'type': sq_type(sw), 'rule': 'eq'}}]}]

# ── 5. 手动添加 + 批量添加 ──
for master, mf, det_t, det_f in CREATE_MODE:
    mw, dm = find(master, mf, 'link-record'), model_of(det_t, det_f, 'link-record')
    if not (mw and dm):
        miss('批量添加 %s.%s（绑定 %s.%s）' % (master, mf, det_t, det_f)); continue
    mw.setdefault('options', {})['createMode'] = {
        'add': True, 'select': True, 'params': {'selectLinkModel': dm}}

# ── 6. 关联控件标题字段 ──
for t, m in LINK_TITLE.items():
    for lrname, tgt_field in m.items():
        lr = find(t, lrname, 'link-record')
        if lr is None:
            miss('标题字段 %s.%s' % (t, lrname)); continue
        tgt_t = CODE2T.get((lr.get('options') or {}).get('sourceCode'))
        fm = model_of(tgt_t, tgt_field) if tgt_t else None
        if not fm:
            miss('标题字段 %s.%s → %s.%s' % (t, lrname, tgt_t, tgt_field)); continue
        lr['options']['titleField'] = fm

# ── 7. 编号规则 ──
for t, m in NUMBER_RULES.items():
    for fname, rules in m.items():
        w = find(t, fname, 'auto-number')
        if w is None:
            miss('编号 %s.%s' % (t, fname)); continue
        w.setdefault('options', {})['numberRules'] = json.loads(json.dumps(rules))

for t, fname, prefix, ref_f, sep, width in FIELD_NUMBER_RULES:
    w, rm = find(t, fname, 'auto-number'), model_of(t, ref_f)
    if not (w and rm):
        miss('编号 %s.%s（引用 %s）' % (t, fname, ref_f)); continue
    w.setdefault('options', {})['numberRules'] = [
        {'type': 'text', 'text': prefix, 'value': prefix},
        {'type': 'field', 'model': rm, 'value': rm},   # 服务端认 model（widget-options auto-number 节）；只写 value 时引用段恒空（CRM-速测20：SJ--003）
        {'type': 'text', 'text': sep, 'value': sep},
        {'type': 'number', 'mode': 2, 'start': 1, 'reset': 0, 'length': width, 'continue': False}]

# ── 8. 下拉选项来自工作表（控件必须是 select，键集抄本应用一个真实静态下拉）──
def _select_tpl():
    for t in CODE:
        for w, _p, _i in widgets(t):
            o = w.get('options') or {}
            if w.get('type') == 'select' and not o.get('dictCode') and not o.get('remote'):
                return {k: v for k, v in o.items()
                        if k not in ('dictCode', 'dictCodeAppId', 'isDictItem', 'remoteOptions',
                                     'remoteFunc', 'options', 'defaultValue', 'hidden',
                                     'hiddenOnAdd', 'autoWidth', 'fieldNote', 'linkDataConfig')}
    return {}


_tpl = None
for t, fname, tgt_t, tgt_f in LINKDATA:
    w, lm = find(t, fname), model_of(tgt_t, tgt_f)
    if w is None or not lm:
        miss('下拉来自工作表 %s.%s ← %s.%s' % (t, fname, tgt_t, tgt_f)); continue
    old = w.get('options') or {}
    cur = old.get('linkDataConfig') or {}
    if (w.get('type') == 'select' and old.get('remote') == 'linkData'
            and cur.get('desformCode') == CODE[tgt_t]
            and ((cur.get('linkages') or [{}])[0]).get('linkModel') == lm):
        continue                           # 已是目标态
    if _tpl is None:
        _tpl = _select_tpl()
    o = dict(_tpl)
    o.update({'remote': 'linkData', 'options': [], 'showLabel': True, 'multiple': False,
              'filterable': False, 'clearable': True,
              'linkDataConfig': {'desformCode': CODE[tgt_t], 'appId': AID, 'matchType': 'AND',
                                 'rules': [], 'sortType': 'OPT_ASC',
                                 'linkages': [{'model': w['model'], 'linkModel': lm,
                                               'linkName': tgt_f}]},
              'hidden': old.get('hidden', False), 'hiddenOnAdd': old.get('hiddenOnAdd', False),
              'fieldNote': old.get('fieldNote', ''), 'autoWidth': old.get('autoWidth', 50)})
    w['type'], w['className'], w['icon'], w['options'] = 'select', 'form-select', 'icon-select', o
    w.pop('advancedSetting', None)
    note(t, '「%s」改为下拉，选项来自 %s.%s' % (fname, tgt_t, tgt_f))

# ── 9. 属性开关 / 宽度 ──
for t, m in OPT_FLAGS.items():
    for fname, kv in m.items():
        w = find(t, fname)
        if w is None:
            miss('属性 %s.%s' % (t, fname)); continue
        o = w.setdefault('options', {})
        o.update(kv)
        if kv.get('required'):
            w['rules'] = [{'required': True, 'message': '${title}必须填写'}]

for t, m in WIDTH.items():
    for fname, wd in m.items():
        w = find(t, fname)
        if w is None:
            miss('宽度 %s.%s' % (t, fname)); continue
        w.setdefault('options', {})['autoWidth'] = wd

# ── 10. 改名（最后做；model/key 不变，引用不受影响）──
for t, m in RENAME.items():
    for old, new in m.items():
        w = find(t, old)
        if w is None:
            if find(t, new) is None:
                miss('改名 %s.%s → %s' % (t, old, new))
            continue
        w['name'] = new

# ── 保存：只存真正变了的表 ──
def _dump(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False)


def changed_widgets(t):
    a = {w['key']: (_dump(w), w.get('name')) for w, _p, _i in walk(ORIG[t].get('list') or [])}
    b = {w['key']: (_dump(w), w.get('name')) for w, _p, _i in walk(DESIGNS[t].get('list') or [])}
    names = [b[k][1] for k in b if k not in a or a[k][0] != b[k][0]]
    names += ['-%s' % a[k][1] for k in a if k not in b]
    return names


CHANGED = [t for t in DESIGNS if _dump(ORIG[t]) != _dump(DESIGNS[t])]
for t in sorted(CHANGED):
    print('%s %s：%s' % ('PLAN' if A.dry_run else 'SAVE', t, '、'.join(changed_widgets(t)) or '(结构位置变化)'))
    if A.dry_run:
        continue
    d = DESIGNS[t]
    for w, _p, _i in walk(d.get('list') or []):      # 字典控件回存前置回 dict，否则绑定态被冲成静态
        o = w.setdefault('options', {})
        if o.get('dictCode') and o.get('isDictItem'):
            o['remote'] = 'dict'
    p = os.path.join(WORK, 'struct_%s.json' % CODE[t])
    json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
    save_design_from_file(CODE[t], p)
    save_auth_from_design(CODE[t])

# 旧子表 model 不得在已加载的设计里残留（跨表 showFields / filters 引用）
blob = _dump({t: DESIGNS[t] for t in DESIGNS})
dangling = [m for m in OLD_MODELS if m in blob]

# 已建流程若引用了旧子表 model，转换后条件/取数悬空且 save/deploy/契约/app_audit 全绿，只有冒烟抓得到
# （2026-09-22 销售管理 R2 实测：build_app --flows 先建了流程、SUBTABLES 后转子表）。这里扫全部 processJson。
FLOW_DANGLING = []
if OLD_MODELS:
    try:
        from desform_utils import api_request
        _r = api_request('/act/process/extActProcess/listProcess',
                         params={'lowAppId': AID, 'pageNo': 1, 'pageSize': 1000}, method='GET')
        for _rec in (((_r or {}).get('result') or {}).get('records') or []):
            _pj = _rec.get('processJson') or ''
            _pj = _pj if isinstance(_pj, str) else json.dumps(_pj, ensure_ascii=False)
            _hit = [m for m in OLD_MODELS if m in _pj]
            if _hit:
                FLOW_DANGLING.append((_rec.get('processName'), _hit))
    except Exception as _e:                      # noqa: BLE001
        NOTES.append('! 流程悬空扫描失败（不影响结构补丁）：%s' % str(_e)[:120])

for n in NOTES:
    print(n)
for m in MISS:
    print('MISS:' + m)
for _n, _hit in FLOW_DANGLING:
    print('TODO: 流程「%s」引用了%s换名的子表控件 %s → 转换后必须 `build_flows.py --update --only "%s"` 重建'
          % (_n, '将被' if A.dry_run else '已', '、'.join(_hit), _n))
print('%s:struct 变更 %d 张表 / 未解析 %d 项 / 旧子表model残留 %d / 流程悬空 %d'
      % ('DRY' if A.dry_run else 'OK', len(CHANGED), len(MISS), len(dangling), len(FLOW_DANGLING)))
if OLD_MODELS and not A.dry_run:
    print('TODO: 子表 model 已换名 → 重跑 postbuild_probe.py，再建简流/按钮（旧字段快照作废）')
if MISS or dangling or (FLOW_DANGLING and not A.dry_run):
    sys.exit(2)
