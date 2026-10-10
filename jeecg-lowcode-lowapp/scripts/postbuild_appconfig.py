# -*- coding: utf-8 -*-
"""建后应用配置：自定义按钮（含绑简流）、列表视图、导航隐藏、功能开关。声明式、幂等、可反复跑。
逻辑来自 2026-09-21 CRM 应用真机跑通的脚本。简流要先建好（postbuild_flows.py），按钮按**流程名**绑定。

  python postbuild_appconfig.py --api-base URL --token T --tenant-id N --app-id A \
         --config appconfig.py [--work DIR] [--dry-run] [--only buttons,views,menus,switches]

配置文件是一段 Python，定义 BUTTONS / VIEWS / HIDE_MENUS / MENU_ORDER / SWITCH_ALL_ON，写法见 references/postbuild-kit.md。

已固化的坑（不用再记）：
- 按钮 CLI 的 update 参数是**顶层字段**（不是 changes:{}）；list 返回 result.buttons
- 建按钮时平台会自动生成一条**占位流程**并写进 processId（纯表单按钮也会）→ 本脚本建完立刻
  换绑到真实流程 / 清空，回读确认后删掉占位流程；不会留孤儿
- 关联记录字段的条件值必须是**记录 id**（用 record_id(表, 标题值) 取），字典字段用 dv() 取落库值
- 数据过滤的条件必须包在筛选组里（根层裸条件界面不显示、落库会被吞）
- CLI 的 stdout/stderr 混排，取第一个带 success 键的 JSON 对象
"""
import sys, os, json, re, argparse, tempfile, subprocess, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from desform_lowapp_utils import init_lowapp, get_menus, get_switch_settings, save_switch_settings
from desform_data_utils import list_data, add_data

ap = argparse.ArgumentParser()
ap.add_argument('--api-base', required=True)
ap.add_argument('--token', required=True)
ap.add_argument('--tenant-id', required=True)
ap.add_argument('--app-id', required=True)
ap.add_argument('--config', required=True)
ap.add_argument('--work', default=None)
ap.add_argument('--dry-run', action='store_true')
ap.add_argument('--only', default='buttons,views,menus,switches')
A = ap.parse_args()
API, TOKEN, TID, AID = A.api_base, A.token, str(A.tenant_id), A.app_id
from skill_temp_path import app_workdir  # noqa: E402
WORK = A.work or app_workdir(AID, create=False)   # 该应用的工作目录（probe 建的；读不到就报缺 probe.json）
for _f in ('probe.json', 'dicts.json'):
    if not os.path.exists(os.path.join(WORK, _f)):
        sys.exit('缺少 %s —— 先跑 postbuild_probe.py' % os.path.join(WORK, _f))
PROBE = json.load(open(os.path.join(WORK, 'probe.json'), encoding='utf-8'))
DICTS = json.load(open(os.path.join(WORK, 'dicts.json'), encoding='utf-8'))
CODE = {t: v['code'] for t, v in PROBE.items()}
ONLY = {x.strip() for x in A.only.split(',') if x.strip()}
init_lowapp(API, TOKEN, tenant_id=int(TID) if TID.isdigit() else TID, app_id=AID)

BTN_CLI = os.path.join(HERE, 'list_view', 'desform_custom_button.py')
VIEW_CLI = os.path.join(HERE, 'list_view', 'desform_list_view.py')
SWITCH_CODES = ['SHOW_CREATE_BTN', 'IMPORT_DATA', 'VIEW_EXPORT', 'BATCH_ACTION', 'BATCH_EDIT',
                'BATCH_EXPORT', 'BATCH_REMOVE', 'BATCH_CUSTOM_BUTTON', 'RECORD_SHARE',
                'RECORD_COMMENT', 'RECORD_SYS_PRINT', 'FILES_DOWNLOAD', 'RECORD_LOGS']
_dec = json.JSONDecoder()
LOG, FAIL, PLAN = [], [], []


def cli(script, payload):
    p = os.path.join(WORK, 'appconfig_call.json')
    json.dump(payload, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
    r = subprocess.run([sys.executable, script, '--api-base', API, '--token', TOKEN, '--tenant-id', TID,
                        '--app-id', AID, '--config', p], capture_output=True, text=True, encoding='utf-8')
    out = (r.stdout or '') + '\n' + (r.stderr or '')
    for i, ch in enumerate(out):
        if ch == '{':
            try:
                o, _e = _dec.raw_decode(out[i:])
            except Exception:
                continue
            if isinstance(o, dict) and 'success' in o:
                return o
    return {'success': False, 'message': out[-200:]}


def _req(method, path, body=None):
    hdr = {'X-Access-Token': TOKEN, 'X-Tenant-Id': TID}
    data = None
    if body is not None:
        data, hdr['Content-Type'] = json.dumps(body, ensure_ascii=False).encode('utf-8'), 'application/json'
    r = urllib.request.Request(API + path, data=data, headers=hdr, method=method)
    with urllib.request.urlopen(r, timeout=120) as f:
        return json.loads(f.read().decode('utf-8'))


# ── 配置助手 ──
def dv(dict_name, label):
    items = DICTS.get(dict_name)
    if not items or label not in items:
        raise KeyError('字典「%s」里没有选项「%s」' % (dict_name, label))
    return items[label]


_RID = {}


def record_id(t, title):
    """按标题字段的值取记录 id（关联记录字段的条件值要用它）"""
    if t not in _RID:
        tf = PROBE[t]['titleField']
        _RID[t] = {str((r.get('desformData') or {}).get(tf)): r['id']
                   for r in ((list_data(CODE[t], 1, 500) or {}).get('records') or [])}
    if title not in _RID[t] and A.dry_run:
        # dry-run 不真的预置 SEED，新应用上这条基础数据还不存在 → 返回占位值，别让预演崩
        # （2026-09-24 CRM-速测17 C：新应用 --dry-run 直接 KeyError，只能跳过预演）
        return '__DRYRUN_RID__'
    if title not in _RID[t]:
        raise KeyError('工作表「%s」里没有标题为「%s」的记录 —— 按钮条件/视图过滤引用关联记录时目标表要先有这条基础数据：'
                       '在本配置里写 SEED = {"%s": [{"<标题字段名>": "%s", ...}]}，脚本会在建按钮前预置' % (t, title, t, title))
    return _RID[t][title]


def fill_fields(*specs):
    """点击后当前记录的字段可填写：'字段' 或 ('字段','required'|'readonly'|'') 或 ('字段', attr, 默认值)
    默认值写**落库值**（字典字段用 dv('字典名','文案') 取值）。以前三元组的第三项被静默丢掉，
    「提交」按钮预填「申报状态=已提交」配不出来（2026-09-24 申报-一句话7 K2）。"""
    lst = []
    for s in specs:
        if isinstance(s, str):
            lst.append({'key': s, 'attr': ''})
        else:
            it = {'key': s[0], 'attr': s[1] if len(s) > 1 else ''}
            if len(s) > 2:
                it['defaultVal'] = ','.join(map(str, s[2])) if isinstance(s[2], (list, tuple)) else s[2]
            lst.append(it)
    return {'formTable': 'current', 'formType': 'update', 'updateFieldList': lst}


def new_link(field):
    """点击后当前记录，新建关联记录，关联字段 field"""
    return {'formTable': 'current', 'formType': 'create', 'createFormField': field}


def C(name, rule, val=''):
    """条件项：rule 用代码 eq/ne/in/not_in/empty/not_empty/like…；in 的多值用逗号串"""
    return (name, rule, val)


BUTTONS = []        # [(工作表, 按钮名, 'execute'|'form'|'confirm', [C(...)]或None, fill_fields()/new_link()/None, 简流名或None)]
VIEWS = {}          # {工作表: {summary:bool, cols:[], qf:[], filter:[C()], sort:[{field,type}],
                    #           extra:[{name, filter:[C()], cols:[], qf:[], lineHeight:'middle'}]}}
HIDE_MENUS = []     # 导航里隐藏的工作表
SEED = {}           # {工作表: [{字段名: 值, ...}, ...]} 基础数据预置（销售阶段这类被按钮条件/视图过滤引用的字典表）；按标题字段去重
MENU_ORDER = []     # [(分组名, [工作表/看板名, ...]), ...] 导航的分组顺序与组内顺序；没点名的排在点名项之后
SWITCH_ALL_ON = False
_SRC = compile(open(A.config, encoding='utf-8').read(), A.config, 'exec')
# 配置里 `ST = {k: record_id('销售阶段', k) ...}` 在 exec 那一刻就求值，而预置要用的记录还没建 →
# 全新应用首跑必 KeyError、写了 SEED 也没用（2026-09-22 CRM R2 实测）。所以分两遍：
# 第一遍把 record_id/dv 顶成占位函数只取 SEED，预置完再真正执行配置。
_probe = dict(globals())
_probe['record_id'] = lambda t, title: '__RID__'
_probe['dv'] = lambda d, label: '__DV__'
try:
    exec(_SRC, _probe)
    SEED = _probe.get('SEED') or {}
except Exception as _e:                          # noqa: BLE001
    SEED = {}
    LOG.append('配置预扫描失败（跳过 SEED 预置）：%s' % str(_e)[:100])

# ═════════ 0. 基础数据预置（按钮条件 / 视图过滤引用的关联记录，首跑前必须先有） ═════════
if SEED:
    for _t, _rows in SEED.items():
        if _t not in PROBE:
            FAIL.append('SEED：应用里没有工作表「%s」' % _t); continue
        _tf = PROBE[_t]['titleField']
        _have = {str((r.get('desformData') or {}).get(_tf))
                 for r in ((list_data(CODE[_t], 1, 500) or {}).get('records') or [])}
        _wd = {x['name']: x for x in PROBE[_t]['widgets'] if x.get('type') != 'divider'}
        for _row in _rows:
            _title = next((v for k, v in _row.items() if _wd.get(k, {}).get('model') == _tf), None)
            if _title is not None and str(_title) in _have:
                continue
            _payload, _bad = {}, [k for k in _row if k not in _wd]
            if _bad:
                FAIL.append('SEED：%s 没有字段 %s' % (_t, '、'.join(_bad))); continue
            for k, v in _row.items():
                _payload[_wd[k]['model']] = v
            PLAN.append('预置 %s：%s' % (_t, _title))
            if not A.dry_run:
                add_data(CODE[_t], _payload)
        _RID.pop(_t, None)                      # 让 record_id() 重新拉
    LOG.append('基础数据预置 %d 张表已核对' % len(SEED))

exec(_SRC, globals())                             # 第二遍：真正执行配置（record_id 现在能取到预置的记录）

# ═════════ 1. 按钮 ═════════
# ── 按钮条件的**值**：中文选项名 → 落库 value（2026-10-09 加） ──
# 配置里条件值按需求原文写中文（「质检状态 是其中一个 已提交」）—— 视图那条路
# （`config_data_filter`）本来就会落到 value，**按钮这条路原来原样落库**：
# 于是 `val` 是「已提交」而库里存的是「0」→ 条件恒不成立 → **按钮永远不显示**
# （2026-10-09 生产管理实测：70 个条件项里 37 个是文案；用户报「订单提报为什么不显示」）。
#
# ⚠️ **翻译必须以该字段自己的选项表为准**，不能按「静态下拉 = label」猜：
#   · 绑字典的字段（下拉单选 + 字典「X」）→ value 是字典值（1..n）；
#   · 静态下拉 → value 可能是**序号**（0/1/2…，本项目就是），也可能 label 即 value；
#   · 文本/数字/日期等没有选项表 → 原样保留（人员 `#{sys_user_code}`、关联记录 id 也走这档）。
# 选项表取 PROBE（建后探针快照），命中不到再回落到**实读该表设计**（快照可能是旧的）。
_BAD_VALS, _OPTS_CACHE = [], {}


def _table_options(ws):
    """该工作表 控件名 → [{value,label}] 选项表（一次建成，整表复用）。

    来源顺序：**实读该表设计**（唯一权威，字典字段的选项也内联在这里）→ 失败才退回 PROBE 快照。
    ⚠️ PROBE 里的 `options.options` 常是空的（建后探针只留 name/model/type 等），
    所以**不能**拿它当主来源 —— 2026-10-09 第一版就是栽在这（37 条只修好 14 条）。
    """
    if ws not in _OPTS_CACHE:
        cache = {}

        def _walk(o):
            if isinstance(o, dict):
                if o.get('type') == 'tabs':
                    for p in (o.get('panes') or []):
                        yield from _walk(p.get('list'))
                    return
                yield o
                for v in o.values():
                    yield from _walk(v)
            elif isinstance(o, list):
                for v in o:
                    yield from _walk(v)

        try:
            from desform_utils import query_form
            dj = json.loads(query_form(CODE[ws])['desformDesignJson'])
            for x in _walk(dj.get('list')):
                # ⚠️ 个别控件的 `options` 是**数组**（不是 dict）—— 一律先 isinstance 再取，
                #    否则整个表的设计读取会炸成 'list' object has no attribute 'get'（2026-10-09 实测）
                opt = x.get('options')
                o = (opt.get('options') if isinstance(opt, dict) else None) or []
                if x.get('name') and o:
                    cache[x['name']] = o
        except Exception as _e:                      # noqa: BLE001
            LOG.append('按钮条件值翻译：读 %s 设计失败（%s），退回 PROBE' % (ws, str(_e)[:60]))
        for x in ((PROBE.get(ws) or {}).get('widgets') or []):
            opt = x.get('options')
            o = (opt.get('options') if isinstance(opt, dict) else None) or []
            if x.get('name') and o and x['name'] not in cache:
                cache[x['name']] = o
        _OPTS_CACHE[ws] = cache
    return _OPTS_CACHE[ws]


def _field_options(ws, fname):
    """该字段的 [{value,label}] 选项表；没有就返回 []（文本/数字/日期/人员/关联等本就没有）。"""
    return _table_options(ws).get(fname) or []


def _btn_val(ws, fname, raw):
    """条件值 → 落库 value 串（多值英文逗号）。认不出的原样保留并记进 `_BAD_VALS`。"""
    sv = '' if raw is None else str(raw)
    opts = _field_options(ws, fname)
    if not sv or not opts:
        return sv
    vals = {str(o.get('value')) for o in opts}
    lab2val = {str(o.get('label')): str(o.get('value')) for o in opts}
    if sv in vals:                      # 整串已是 value
        return sv
    if sv in lab2val:                   # 整串就是一个 label（label 里带「、」也不会被拆坏）
        return lab2val[sv]
    out = []
    for t in re.split(r'[，,、]', sv):
        if t == '':
            continue
        if t in vals:
            out.append(t)
        elif t in lab2val:
            out.append(lab2val[t])
        else:
            out.append(t)
            _BAD_VALS.append('%s 的「%s」=%r 里 %r 既不是 value 也不是 label（照原样下发）'
                             % (ws, fname, raw, t))
    return ','.join(out)


def _btn_query_items(ws, conds):
    return [{'field': n, 'rule': r, 'val': _btn_val(ws, n, v)} for n, r, v in conds]



if 'buttons' in ONLY and BUTTONS:
    fl = _req('GET', '/act/process/extActProcess/list?pageSize=500&lowAppId=' + AID)
    # 身份 = 流程名 + 所属表（同名流程分属多张表是合法的，2026-09-28 生产管理：6 组同名按钮流）
    _flows = {}
    for x in ((fl.get('result') or {}).get('records') or []):
        if x.get('lowAppId') != AID:
            continue
        _pj = json.loads(((_req('GET', '/act/process/extActProcess/queryById?id=%s' % x['id']) or {})
                          .get('result') or {}).get('processJson') or '{}')
        _tc = next((y.get('formTableCode') for y in _pj.get('formTableList') or [] if y.get('nodeId') == 'start'), None)
        _flows[(x.get('processName'), _tc)] = x.get('id')
    flows = {n: i for (n, _c), i in _flows.items()}          # 兼容旧口径（按名）

    def _fid(flow, ws):
        return _flows.get((flow, CODE[ws])) or flows.get(flow)
    cur = {}
    for ws in sorted({b[0] for b in BUTTONS}):
        for b in ((cli(BTN_CLI, {'action': 'list', 'code': CODE[ws]}).get('result') or {}).get('buttons') or []):
            cur[(ws, b.get('label'))] = b
    placeholders = set()
    SEQ = {}
    for _bt in BUTTONS:
        ws, label, click, conds, formcfg, flow = _bt[:6]
        # 第 7 项（可选）= 按钮其余属性：confirmText / color / icon / seq …（2026-09-28：对齐线上「二次确认文案 + 图标 + 颜色」）
        extra = dict(_bt[6]) if len(_bt) > 6 and _bt[6] else {}
        if 'seq' in extra:        # 按钮 update 接口不写 seq（回读恒 None）→ 收尾按 seq 统一 reorder
            SEQ.setdefault(ws, []).append((extra.pop('seq'), label))
        if flow and flow not in flows:
            FAIL.append('按钮 %s/%s：简流「%s」不存在（先跑 postbuild_flows.py）' % (ws, label, flow)); continue
        target = _fid(flow, ws) if flow else None
        b = cur.get((ws, label))
        if b is None:
            PLAN.append('建按钮 %s/%s' % (ws, label))
            if A.dry_run:
                continue
            pay = {'action': 'create', 'code': CODE[ws], 'label': label, 'clickThen': click,
                   'showStatus': 'condition' if conds else 'always'}
            if conds:
                pay['conditionsGroup'] = [{'matchType': 'and',
                                           'queryItems': _btn_query_items(ws, conds)}]
            if formcfg:
                pay['buttonFormConfig'] = formcfg
            if flow:
                pay['flowStatus'] = True
            pay.update(extra)
            r = cli(BTN_CLI, pay)
            if not r.get('success'):
                FAIL.append('按钮 %s/%s 创建失败：%s' % (ws, label, str(r.get('message'))[:120])); continue
            b = next((x for x in ((cli(BTN_CLI, {'action': 'list', 'code': CODE[ws]}).get('result') or {})
                                  .get('buttons') or []) if x.get('label') == label), None)
            if b is None:
                FAIL.append('按钮 %s/%s 建后回读不到' % (ws, label)); continue
        else:
            # 已存在的按钮也同步点击方式 / 显示条件 / 扩展属性（以前只在新建时写，改配置重跑不生效）
            want = {'clickThen': click, 'showStatus': 'condition' if conds else 'always', **extra}
            diff = {k: v for k, v in want.items() if b.get(k) != v}
            if conds:   # 条件按中文名写、落库是 model，无法逐字比较 → 有条件就整组重写（幂等）
                diff['conditionsGroup'] = [{'matchType': 'and',
                                            'queryItems': _btn_query_items(ws, conds)}]
                diff['showStatus'] = 'condition'
            if diff:
                PLAN.append('按钮 %s/%s 同步 %s' % (ws, label, '、'.join(sorted(diff))))
                if not A.dry_run:
                    r = cli(BTN_CLI, dict({'action': 'update', 'id': b['id'], 'code': CODE[ws]}, **diff))
                    if not r.get('success'):
                        FAIL.append('按钮 %s/%s 同步失败：%s' % (ws, label, str(r.get('message'))[:120]))
        pid = b.get('processId') or None
        if pid != target:
            PLAN.append('按钮 %s/%s 换绑 %s → %s' % (ws, label, pid, target))
            if A.dry_run:
                continue
            r = cli(BTN_CLI, {'action': 'update', 'id': b['id'], 'code': CODE[ws],
                              'processId': target, 'flowStatus': bool(target)})
            if not r.get('success'):
                FAIL.append('按钮 %s/%s 换绑失败：%s' % (ws, label, str(r.get('message'))[:120])); continue
            if pid and pid not in _flows.values():
                placeholders.add(pid)
    for ws, lst in SEQ.items():      # 排序：reorder 的 ids 顺序即按钮顺序
        now_ = {x.get('label'): x for x in ((cli(BTN_CLI, {'action': 'list', 'code': CODE[ws]}).get('result') or {})
                                            .get('buttons') or [])}
        ids = [now_[l]['id'] for _s, l in sorted(lst, key=lambda z: (z[0] is None, z[0] or 0)) if l in now_]
        cur_order = [x.get('id') for x in sorted(now_.values(), key=lambda x: (x.get('seq') is None, x.get('seq') or 0))]
        if ids and [i for i in cur_order if i in ids] != ids:
            PLAN.append('按钮排序 %s：%s' % (ws, ' → '.join(l for _s, l in sorted(lst, key=lambda z: (z[0] is None, z[0] or 0)))))
            if not A.dry_run:
                r = cli(BTN_CLI, {'action': 'reorder', 'code': CODE[ws], 'ids': ids})
                if not r.get('success'):
                    FAIL.append('按钮排序 %s 失败：%s' % (ws, str(r.get('message'))[:120]))
    if not A.dry_run:
        bad = []
        for ws in sorted({b[0] for b in BUTTONS}):
            now = {x.get('label'): x for x in ((cli(BTN_CLI, {'action': 'list', 'code': CODE[ws]}).get('result') or {})
                                               .get('buttons') or [])}
            for w2, label, _c, _k, _f, flow, *_x in BUTTONS:
                if w2 == ws and (now.get(label) or {}).get('processId') != (_fid(flow, ws) if flow else None):
                    if label in now:
                        bad.append('%s/%s' % (ws, label))
        if bad:
            FAIL.append('按钮换绑回读不符：%s（占位流程未删）' % bad)
        else:
            for pid in placeholders:
                try:
                    _req('DELETE', '/act/process/extActProcess/delete?id=%s' % pid)
                except Exception:
                    pass
            if placeholders:
                LOG.append('删除占位流程 %d 条' % len(placeholders))
    LOG.append('按钮 %d 个已核对' % len(BUTTONS))

# ═════════ 2. 列表视图 ═════════
def _grp(items):
    return [{'match_type': 'and', 'items': [{'name': n, 'rule': r, 'val': v} for n, r, v in items]}]


def _view_cfg(code, vid, summary, cols, qf, flt, sort, line_height, tag, left=None, calendar=None):
    # left = 左侧筛选字段中文名（仅表格视图）；calendar = {'begin': 开始字段, 'end': 结束字段, 'title': 标题字段}
    # （2026-09-28 生产管理：需求有「左侧筛选 订单状态」「日历视图 开始/结束/标题」，此前 VIEWS 写不出来）
    steps = [] if calendar else [({'action': 'config_table', 'code': code, 'viewId': vid, 'hasSummary': bool(summary),
               **({'lineHeight': line_height} if line_height else {})}, '统计开关')]
    if left:
        steps.append(({'action': 'config_left_filter', 'code': code, 'viewId': vid, 'leftFilterField': left,
                       'leftFilterData': 'all'}, '左侧筛选'))
    if calendar:
        # 直连 updateViewConfig：列表视图 CLI 的 config_calendar 不认系统字段（「创建时间」报「未找到字段 create_time」，
        # 2026-09-28 生产管理「自行排产」日历视图实测），系统字段直接写 create_time / update_time
        _t = next(k for k, v in CODE.items() if v == code)
        _wm = {x['name']: x for x in PROBE[_t]['widgets']}
        _sys = {'创建时间': 'create_time', '修改时间': 'update_time'}
        _m = lambda n: _sys.get(n) or (_wm[n]['model'] if n in _wm else None)
        _b, _e = _m(calendar['begin']), _m(calendar.get('end') or '')
        if not _b:
            FAIL.append('视图 %s 日历开始字段「%s」不存在' % (tag, calendar['begin']))
        else:
            _body = {'id': vid, 'calendarColumnList': [{'beginDateField': _b, 'endDateField': _e or '', 'type': 'datetime',
                                                        'tag': '', 'seq': 0}]}
            if calendar.get('title') and calendar['title'] in _wm:
                _body['titleField'] = _wm[calendar['title']]['model']
            _rr = _req('PUT', '/desform/view/updateViewConfig', _body)
            if not _rr.get('success'):
                FAIL.append('视图 %s 日历设置：%s' % (tag, str(_rr.get('message'))[:100]))
    if cols:
        steps.append(({'action': 'config_table', 'code': code, 'viewId': vid, 'fieldNames': cols}, '显示列'))
    if qf:
        steps.append(({'action': 'config_quick_filter', 'code': code, 'viewId': vid, 'fieldNames': qf}, '快速筛选'))
    if flt:
        steps.append(({'action': 'config_data_filter', 'code': code, 'viewId': vid, 'matchType': 'and',
                       'conditions': _grp(flt)}, '数据过滤'))
    if sort:
        steps.append(({'action': 'config_sort', 'code': code, 'viewId': vid, 'orders': sort}, '排序'))
    for pay, what in steps:
        r = cli(VIEW_CLI, pay)
        if not r.get('success'):
            FAIL.append('视图 %s %s：%s' % (tag, what, str(r.get('message'))[:100]))


if 'views' in ONLY:
    if not VIEWS:
        # ⚠️ 以前这里是 `if 'views' in ONLY and VIEWS:` —— 空声明**整段静默跳过、连日志都不打**。
        # 2026-09-30 生产管理 R11 的 18 个视图就是这么丢的：配置里只有个空壳 `VIEWS = {}`
        # 加几行需求原文注释，跑完 4 次日志里翻不到一个「视图」字样，四道闸门又都不看列表视图
        # （precheck 只看**看板**），最后界面上一眼才发现。**空声明必须出声。**
        LOG.append('⚠️ 视图：VIEWS 为空 —— 本次一个视图都没核对。需求里若有「视图：」段落，'
                   '必须在配置文件里逐条声明（表格视图/日历/看板/甘特），见 references/postbuild-kit.md')
    else:
        made = 0
        for t, p in VIEWS.items():
            code = CODE[t]
            vs = {v['name']: v['id'] for v in ((cli(VIEW_CLI, {'action': 'list', 'code': code}).get('result') or {})
                                               .get('views') or [])}
            main = vs.get(p.get('main', '全部')) or (list(vs.values())[0] if len(vs) == 1 else None)
            if not main:
                FAIL.append('视图 %s：找不到默认表格视图' % t); continue
            missing = [e['name'] for e in p.get('extra', []) if e['name'] not in vs]
            for n in missing:
                PLAN.append('建视图 %s/%s' % (t, n))
            if A.dry_run:
                continue
            _view_cfg(code, main, p.get('summary', True), p.get('cols'), p.get('qf'), p.get('filter'),
                      p.get('sort'), p.get('lineHeight'), '%s/全部' % t)
            for e in p.get('extra', []):
                vid = vs.get(e['name'])
                if not vid:
                    rr = _req('POST', '/desform/view/addView', {'type': e.get('type', 'base'), 'code': code, 'name': e['name']})
                    vid = rr.get('result') or rr.get('message')
                    made += 1
                _view_cfg(code, vid, e.get('summary', True), e.get('cols'), e.get('qf'), e.get('filter'),
                          e.get('sort'), e.get('lineHeight'), '%s/%s' % (t, e['name']), e.get('left'), e.get('calendar'))
        LOG.append('视图：%d 张表已%s，新建 %d 个' % (len(VIEWS), '核对' if A.dry_run else '配置', made))

# ═════════ 3. 导航隐藏 ═════════
def _form_menus():
    out = []

    def wk(ns):
        for n in ns or []:
            if n.get('type') == 'form':
                out.append(n)
            wk(n.get('children'))
    m = get_menus(AID) or {}
    wk(m.get('menuList') or m.get('result') or [])
    return out


if 'menus' in ONLY and HIDE_MENUS:
    unknown = [x for x in HIDE_MENUS if x not in CODE]
    if unknown:
        FAIL.append('导航隐藏：没有工作表 %s' % unknown)
    for n in _form_menus():
        want = 1 if n.get('menuName') in HIDE_MENUS else None
        if (n.get('hideFlag') or None) != want:
            PLAN.append('导航%s %s' % ('隐藏' if want else '显示', n.get('menuName')))
            if not A.dry_run:
                _req('PUT', '/online/lowAppMenu/edit', {'id': n['id'], 'hideFlag': want})
    if not A.dry_run:                                   # 该接口对任何输入都回「编辑成功」，必须回读
        after = {n['menuName']: (n.get('hideFlag') or None) for n in _form_menus()}
        wrong = [k for k, v in after.items() if (v == 1) != (k in HIDE_MENUS)]
        if wrong:
            FAIL.append('导航隐藏回读不符：%s' % wrong)
    LOG.append('导航隐藏 %d 张已核对' % len(HIDE_MENUS))

# ═════════ 3-b. 导航顺序（分组顺序 + 组内顺序；写完回读） ═════════
if 'menus' in ONLY and MENU_ORDER:
    from desform_lowapp_utils import apply_menu_order
    # 看板分组/看板在建盘之前不存在：以前整段 exit 2（2026-09-22 项目管理实测）。现在缺的只提示、跳过，
    # 建盘后再跑一次 `--only menus` 即可补齐
    from desform_lowapp_utils import _flat_menus
    _ml = _flat_menus((get_menus(AID) or {}).get('menuList') or [])
    _have = {m.get('menuName') for m in _ml}
    for _g, _ns in MENU_ORDER:
        _miss = ([_g] if _g and _g not in _have else []) + [n for n in _ns if n not in _have]
        if _miss:
            LOG.append('导航顺序：%s 尚不存在（看板建完再跑 --only menus），本次跳过' % '、'.join(_miss))
    _r = apply_menu_order([(g, list(ns)) for g, ns in MENU_ORDER], AID, dry_run=A.dry_run, missing='skip')
    PLAN.extend('导航顺序 ' + c for c in _r['changed'])
    FAIL.extend('导航顺序：' + p for p in _r['problems'])
    LOG.append('导航顺序 %d 个分组已核对' % len(MENU_ORDER))

# ═════════ 4. 功能开关全开 ═════════
if 'switches' in ONLY and SWITCH_ALL_ON:
    n_fix = 0
    for t, code in CODE.items():
        got = {x.get('code'): x.get('enabled') for x in (get_switch_settings(code) or [])}
        off = [c for c in SWITCH_CODES if got.get(c) is not True]
        if not off:
            continue
        PLAN.append('功能开关 %s 补开 %d 项' % (t, len(off)))
        if A.dry_run:
            continue
        save_switch_settings(code, [{'_id': None, 'code': c, 'desformCode': code, 'enabled': True,
                                     'userAuth': 1, 'viewAuth': 1, 'viewIds': [], 'createBy': None,
                                     'createTime': None, 'updateBy': None, 'updateTime': None}
                                    for c in SWITCH_CODES])          # 父子开关要一次全发
        n_fix += 1
    LOG.append('功能开关：%d 张表已核对，补开 %d 张' % (len(CODE), n_fix))

for x in LOG:
    print('· ' + x)
if _BAD_VALS:
    print('⚠ 按钮条件值有 %d 项既不是 value 也不是 label（已原样下发，界面上多半不成立）：'
          % len(_BAD_VALS))
    for m in _BAD_VALS[:10]:
        print('   · ' + m)
for x in PLAN:
    print(('PLAN ' if A.dry_run else 'DONE ') + x)
for x in FAIL:
    print('FAIL:' + x)
print('%s:appconfig 待办/已办 %d 项 / 失败 %d' % ('DRY' if A.dry_run else 'OK', len(PLAN), len(FAIL)))
if FAIL:
    sys.exit(2)
