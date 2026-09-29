# -*- coding: utf-8 -*-
"""建后核验（只读）：抓「存了值但设计器面板解析不到」这一类——save/回读/precheck/契约检查全绿、
运行时往往也正常，只有打开面板才看得见的缺陷。零应用知识，任何应用通用。

  python postbuild_verify.py --api-base URL --token T --tenant-id N --app-id A [--work DIR]
         [--self-test]   注入已知缺陷，证明本校验器抓得住（只改内存，不落库）
         [--no-buttons]  跳过按钮检查（每张表一次 CLI 调用，表多时省时间）

检查项：
  引用完整性  汇总 linkTable(→本表关联控件 key)/field、他表字段 linkRecordKey(key)/showField/saveType、
              关联记录 titleField/showFields/twoWayModel 互指/记录范围/批量添加绑定字段、
              默认值 $key.model$ 与 linkage/LINKAGET、选项数据源 linkDataConfig、编号 field 段、公式占位符
  子表不变式  isSubTable 控件 model==sub_table_design_<key>、showType=table、回指字段 single+card
  简流        本应用流程是否全部启用
  按钮        processId 必须属于本应用流程；关联记录条件值必须是记录 id；字典字段条件值不能是文案
"""
import sys, os, json, re, argparse, tempfile, subprocess, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from desform_lowapp_utils import init_lowapp, get_menus, check_menu_order
from desform_utils import query_form

ap = argparse.ArgumentParser()
ap.add_argument('--api-base', required=True)
ap.add_argument('--token', required=True)
ap.add_argument('--tenant-id', required=True)
ap.add_argument('--app-id', required=True)
ap.add_argument('--work', default=None)
ap.add_argument('--self-test', action='store_true')
ap.add_argument('--no-buttons', action='store_true')
A = ap.parse_args()
AID = A.app_id
from skill_temp_path import app_workdir  # noqa: E402
WORK = A.work or app_workdir(AID)   # 该应用的工作目录
os.makedirs(WORK, exist_ok=True)
TID = int(A.tenant_id) if str(A.tenant_id).isdigit() else A.tenant_id
init_lowapp(A.api_base, A.token, tenant_id=TID, app_id=AID)

NOT_FIELD = ('divider', 'tabs', 'card', 'grid', 'text')


def walk(n, out=None):
    out = [] if out is None else out
    if isinstance(n, dict):
        if n.get('type') and n.get('key') and n.get('type') not in ('card', 'grid'):
            out.append(n)
        for k in ('list', 'columns', 'panes'):
            v = n.get(k)
            if isinstance(v, list):
                for it in v:
                    walk(it, out)
    elif isinstance(n, list):
        for it in n:
            walk(it, out)
    return out


CODE = {}


def _menus(nodes):
    for n in nodes or []:
        if n.get('type') == 'form' and n.get('desformCode'):
            CODE[n.get('menuName')] = n.get('desformCode')
        _menus(n.get('children'))


_m = get_menus(AID) or {}
_menus(_m.get('menuList') or _m.get('result') or [])

W = {t: walk(json.loads(query_form(c)['desformDesignJson']).get('list') or []) for t, c in CODE.items()}
CODE2T = {v: k for k, v in CODE.items()}
BAD, INFO, INJECTED = [], [], []

# ── 自检：每类缺陷各注入一处 ──
if A.self_test:
    def _first(pred):
        for t, ws in W.items():
            for w in ws:
                if pred(t, w):
                    return t, w
        return None, None

    lk = {t: {w['key'] for w in ws if w['type'] == 'link-record'} for t, ws in W.items()}
    t, w = _first(lambda t, w: w['type'] == 'summary' and (w.get('options') or {}).get('linkTable') in lk[t])
    if w:
        w['options']['linkTable'] = 'sub_table_design_' + w['options']['linkTable']; INJECTED.append((t, w['name']))
    t, w = _first(lambda t, w: w['type'] == 'link-field')
    if w:
        w['options']['showField'] = 'bogus_model'; INJECTED.append((t, w['name']))
    t, w = _first(lambda t, w: w['type'] == 'link-record' and (w.get('options') or {}).get('showFields'))
    if w:
        w['options']['showFields'] = ['bogus_show']; INJECTED.append((t, w['name']))
    t, w = _first(lambda t, w: '$' in str(((w.get('advancedSetting') or {}).get('defaultValue') or {}).get('value'))
                  and ((w.get('advancedSetting') or {}).get('defaultValue') or {}).get('type') == 'compose')
    if w:
        w['advancedSetting']['defaultValue']['value'] = '$badkey.badmodel$'; INJECTED.append((t, w['name']))
    t, w = _first(lambda t, w: ((w.get('advancedSetting') or {}).get('defaultValue') or {}).get('type') == 'linkage'
                  and isinstance(w['advancedSetting']['defaultValue'].get('value'), dict)
                  and w['advancedSetting']['defaultValue']['value'].get('rules'))
    if w:
        w['advancedSetting']['defaultValue']['value']['rules'][0]['model'] = 'bogus_rule'; INJECTED.append((t, w['name']))
    t, w = _first(lambda t, w: w.get('isSubTable') is True)
    if w:
        w['model'] = 'link_record_bogus'; INJECTED.append((t, w['name']))
    _forms = [m for m in (_m.get('menuList') or []) if m.get('type') == 'form']
    if len(_forms) > 1:                                  # 菜单排序号重复（并行建表的典型产物）
        _forms[1]['orderNum'] = _forms[0].get('orderNum')
        _forms[1]['parentId'] = _forms[0].get('parentId'); INJECTED.append(('菜单', '分组内'))

MODELS = {t: {w['model'] for w in ws} for t, ws in W.items()}
LINKKEYS = {t: {w['key']: w for w in ws if w['type'] == 'link-record'} for t, ws in W.items()}
BYMODEL = {t: {w['model']: w for w in ws} for t, ws in W.items()}


def bad(t, w, msg):
    BAD.append('%s.%s (%s)  %s' % (t, w.get('name'), w.get('type'), msg))


def tgt_of(t, key):
    lw = LINKKEYS[t].get(key)
    return CODE2T.get((lw.get('options') or {}).get('sourceCode')) if lw else None


def chk_refs(t, w, text, where):
    for tok in re.findall(r'\$([^$]+)\$', text or ''):
        if tok.startswith('_CONTEXT_VAR_'):
            continue
        if '.' in tok:
            k, m = tok.split('.', 1)
            if k not in LINKKEYS[t]:
                bad(t, w, '%s 引用的 %s 不是本表关联记录控件 key（点分前半要用 key 不是 model）' % (where, k)); continue
            tt = tgt_of(t, k)
            if tt and m not in MODELS[tt]:
                bad(t, w, '%s 引用 %s 在目标表「%s」不存在' % (where, m, tt))
        elif tok not in MODELS[t]:
            bad(t, w, '%s 引用的 %s 不是本表字段 model' % (where, tok))


def chk_linkage(t, w, cfg, where):
    if not isinstance(cfg, dict):
        bad(t, w, '%s 配置不是对象（存成字符串时面板显示为空、运行时不取数）' % where); return
    tt = CODE2T.get(cfg.get('desformCode'))
    if not tt:
        bad(t, w, '%s desformCode=%s 不在本应用' % (where, cfg.get('desformCode'))); return
    if cfg.get('appId') in (None, ''):
        bad(t, w, '%s appId 为空（面板「应用/工作表」下拉会空白）' % where)
    for r in (cfg.get('rules') or []):
        if r.get('model') not in MODELS[tt]:
            bad(t, w, '%s 条件字段 %s 在目标表「%s」不存在' % (where, r.get('model'), tt))
        if r.get('valueType') == 'field':
            for v in (r.get('value') or []):
                if v and not str(v).startswith('_CONTEXT_VAR_') and v not in MODELS[t]:
                    bad(t, w, '%s 条件取值 %s 不是本表字段' % (where, v))
        if not r.get('sqParam'):
            bad(t, w, '%s 条件缺 sqParam（API 直写不会自动补，新增页不回填）' % where)
    for l in (cfg.get('linkages') or []):
        if l.get('model') not in MODELS[t]:
            bad(t, w, '%s 映射目标 %s 不是本表字段' % (where, l.get('model')))
        if l.get('linkModel') not in MODELS[tt]:
            bad(t, w, '%s 映射来源 %s 在目标表「%s」不存在' % (where, l.get('linkModel'), tt))


for t, ws in W.items():
    for w in ws:
        o, ty = (w.get('options') or {}), w['type']

        if ty == 'summary':
            lt, src = o.get('linkTable'), None
            if lt in LINKKEYS[t]:
                src = tgt_of(t, lt)
            elif lt and str(lt).startswith('sub_table_design_') and lt[len('sub_table_design_'):] in LINKKEYS[t]:
                bad(t, w, 'linkTable 存了 %s；源是关联记录（含工作表子表）时应存控件 key，面板才解析得到' % lt)
                src = tgt_of(t, lt[len('sub_table_design_'):])
            elif lt in BYMODEL[t] and BYMODEL[t][lt]['type'] == 'sub-table-design':
                src = None                              # 设计子表：存 model 是对的
            elif lt in BYMODEL[t] and BYMODEL[t][lt]['type'] == 'link-record':
                bad(t, w, 'linkTable 存了关联记录的 model，应存控件 key')
            else:
                bad(t, w, 'linkTable=%s 解析不到本表的关联记录/子表控件' % lt)
            f = o.get('field')
            if f and f != 'inner-record-count' and src and f not in MODELS[src]:
                bad(t, w, '汇总列 %s 在明细表「%s」不存在' % (f, src))

        elif ty == 'link-field':
            lrk = o.get('linkRecordKey')
            if lrk not in LINKKEYS[t]:
                bad(t, w, 'linkRecordKey=%s 不是本表关联记录控件 key' % lrk)
            else:
                tt = tgt_of(t, lrk)
                if tt and o.get('showField') not in MODELS[tt]:
                    bad(t, w, 'showField=%s 在目标表「%s」不存在' % (o.get('showField'), tt))
            if o.get('saveType') != 'save':
                INFO.append('%s.%s 他表字段 saveType=%s（仅显示、值不落库；需求写「存储数据」时是缺陷）'
                            % (t, w.get('name'), o.get('saveType')))

        elif ty == 'link-record':
            tt = CODE2T.get(o.get('sourceCode'))
            if not tt:
                bad(t, w, 'sourceCode=%s 不在本应用' % o.get('sourceCode'))
            else:
                if o.get('titleField') and o['titleField'] not in MODELS[tt]:
                    bad(t, w, 'titleField=%s 在目标表「%s」不存在' % (o['titleField'], tt))
                for sf in (o.get('showFields') or []):
                    if not isinstance(sf, str):
                        bad(t, w, 'showFields 元素必须是裸 model 字符串，现为 %s' % type(sf).__name__)
                    elif sf not in MODELS[tt]:
                        bad(t, w, 'showFields 含 %s，目标表「%s」无此字段' % (sf, tt))
                    elif BYMODEL[tt][sf]['type'] in NOT_FIELD:
                        bad(t, w, 'showFields 混进了非数据控件「%s」' % BYMODEL[tt][sf].get('name'))
                twm = o.get('twoWayModel')
                if twm:
                    if twm not in MODELS[tt]:
                        bad(t, w, 'twoWayModel=%s 在目标表「%s」不存在' % (twm, tt))
                    elif (BYMODEL[tt][twm].get('options') or {}).get('twoWayModel') != w['model']:
                        bad(t, w, '双向未互指：对面「%s」指向 %s' % (
                            BYMODEL[tt][twm].get('name'), (BYMODEL[tt][twm].get('options') or {}).get('twoWayModel')))
                for grp in (o.get('filters') or []):
                    for r in (grp.get('rules') or []):
                        if r.get('model') not in MODELS[tt]:
                            bad(t, w, '记录范围条件字段 %s 在目标表「%s」不存在' % (r.get('model'), tt))
                        if r.get('valueType') == 'field':
                            for v in (r.get('value') or []):
                                if v not in MODELS[t]:
                                    bad(t, w, '记录范围取值 %s 不是本表字段' % v)
                cm = o.get('createMode') or {}
                slm = (cm.get('params') or {}).get('selectLinkModel')
                if cm.get('select') and (not slm or slm not in MODELS[tt]):
                    bad(t, w, '批量添加绑定字段 %s 在明细表「%s」不存在' % (slm, tt))
                if w.get('isSubTable') is True:
                    if w['model'] != 'sub_table_design_' + w['key']:
                        bad(t, w, '工作表子表 model 应为 sub_table_design_<key>，现为 %s' % w['model'])
                    if o.get('showType') != 'table':
                        bad(t, w, '工作表子表 showType 应为 table')
                    if not twm:
                        bad(t, w, '工作表子表缺 twoWayModel（添加记录弹窗带不出父记录）')
                    elif twm in MODELS[tt]:
                        bo = BYMODEL[tt][twm].get('options') or {}
                        if bo.get('showMode') != 'single' or bo.get('showType') != 'card':
                            bad(t, w, '明细回指字段「%s」应为 单条+卡片' % BYMODEL[tt][twm].get('name'))

        if ty == 'auto-number':
            for seg in (o.get('numberRules') or []):
                if seg.get('type') == 'field' and seg.get('value') not in MODELS[t]:
                    bad(t, w, '编号 field 段 %s 不是本表字段' % seg.get('value'))
        if ty == 'formula':
            chk_refs(t, w, o.get('expression') or '', '公式')
        if o.get('remote') == 'linkData':
            if ty != 'select':
                bad(t, w, '选项来自工作表但控件不是 select（界面是文本框）')
            chk_linkage(t, w, o.get('linkDataConfig'), '选项数据源')

        dv = (w.get('advancedSetting') or {}).get('defaultValue') or {}
        v = dv.get('value')
        if dv.get('type') in ('compose', 'function') and isinstance(v, str) and v and not v.startswith('#'):
            body = v
            for cfgtxt in re.findall(r'LINKAGET\((\{.*?\})\s+,\s+\[', v, re.S):
                try:
                    chk_linkage(t, w, json.loads(cfgtxt), '函数内 LINKAGET')
                except Exception:
                    bad(t, w, '函数内 LINKAGET 配置解析失败')
                body = body.replace(cfgtxt, '')
            chk_refs(t, w, body, '默认值(%s)' % dv['type'])
        elif dv.get('type') == 'linkage':
            chk_linkage(t, w, v, '默认值(查询工作表)')


# ── 导航菜单：排序号重复/为空、分组 parentId 混用 NULL 与空串 → 显示顺序不确定 ──
# （「顺序对不对」要有期望才能判，那一档由 build_app / postbuild_appconfig 的 MENU_ORDER 写完回读；
#   这里只查「顺序是否确定」，不依赖任何配置，所以对任何应用都能跑）
_MENU_BAD = check_menu_order(_m.get('menuList') or _m.get('result') or [])
if A.self_test:
    _MENU_BAD = [b.replace('菜单.', '菜单.分组内 ', 1) if '重复' in b else b for b in _MENU_BAD]
BAD.extend(_MENU_BAD)


# ── 简流 / 按钮 ──
def _req(path):
    r = urllib.request.Request(A.api_base + path, headers={
        'X-Access-Token': A.token, 'X-Tenant-Id': str(A.tenant_id)})
    with urllib.request.urlopen(r, timeout=120) as f:
        return json.loads(f.read().decode('utf-8'))


FLOW_IDS = set()
try:
    recs = [x for x in (((_req('/act/process/extActProcess/listProcess?pageSize=500') or {}).get('result') or {})
                        .get('records') or []) if x.get('lowAppId') == AID]
    FLOW_IDS = {x.get('id') for x in recs}
    off = [x.get('processName') for x in recs
           if not (str(x.get('openStatus')) == '1' and str(x.get('processStatus')) == '1')]
    INFO.append('简流 %d 条，未启用 %d 条' % (len(recs), len(off)))
    for n in off:
        BAD.append('简流「%s」未启用/未发布' % n)
except Exception as e:
    INFO.append('简流清单读取失败：%s' % str(e)[:80])

if not A.no_buttons and not A.self_test:
    dicts_p = os.path.join(WORK, 'dicts.json')
    labels, values = set(), set()
    if os.path.exists(dicts_p):
        for items in json.load(open(dicts_p, encoding='utf-8')).values():
            labels |= set(items.keys()); values |= {str(x) for x in items.values()}
    # ⚠️ 这里是本脚本的**唯一热区**：原来每张表起一个 `desform_custom_button.py`
    # 子进程（47 次解释器冷启动 ≈ 3~5 分钟），而它只是调一次 `/desform/button/list`。
    # 改成**进程内直调** `desform_button_utils.list_buttons`（共用本进程已 init 的连接）；
    # import 失败再回落到原来的子进程路径，行为不变（2026-09-23）。
    dec, nb = json.JSONDecoder(), 0
    try:
        from desform_button_utils import list_buttons as _list_buttons
    except Exception:                                    # noqa: BLE001
        _list_buttons = None
    cli = os.path.join(HERE, 'list_view', 'desform_custom_button.py')

    def _buttons_of(t):
        """返回该表的按钮列表；进程内路径失败时回落子进程 CLI。"""
        if _list_buttons is not None:
            try:
                return _list_buttons(form_code=CODE[t]) or []
            except Exception:                            # noqa: BLE001
                pass
        p = os.path.join(WORK, 'verify_btn.json')
        json.dump({'action': 'list', 'worksheet': t}, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
        r = subprocess.run([sys.executable, cli, '--api-base', A.api_base, '--token', A.token,
                            '--tenant-id', str(A.tenant_id), '--app-id', AID, '--config', p],
                           capture_output=True, text=True, encoding='utf-8')
        out = (r.stdout or '') + '\n' + (r.stderr or '')
        for i, ch in enumerate(out):                     # stdout/stderr 混排，取第一个带 success 的 JSON 对象
            if ch == '{':
                try:
                    obj, _e = dec.raw_decode(out[i:])
                except Exception:
                    continue
                if isinstance(obj, dict) and 'success' in obj:
                    return ((obj.get('result') or {}).get('buttons') or [])
        return []

    _SYS_MODELS = {'bpm_status', 'create_by', 'create_time', 'update_by', 'update_time', 'sys_org_code'}
    for t in CODE:
        for b in _buttons_of(t):
            nb += 1
            pid = b.get('processId')
            if pid and FLOW_IDS and pid not in FLOW_IDS:
                BAD.append('按钮 %s/%s processId=%s 不在本应用流程里（占位流程没换绑？）' % (t, b.get('label'), pid))
            for g in (b.get('conditionsGroup') or []):
                for q in (g.get('queryItems') or []):
                    if q.get('rule') in ('empty', 'not_empty'):
                        continue
                    fw, v = BYMODEL[t].get(q.get('field')), q.get('val')
                    if fw is None and q.get('field') in _SYS_MODELS:
                        continue                 # 系统字段（流程状态 bpm_status 等）：不在设计器控件里，但是合法条件
                    if fw is None:
                        BAD.append('按钮 %s/%s 条件字段 %s 不是本表字段' % (t, b.get('label'), q.get('field')))
                    elif v in (None, ''):
                        BAD.append('按钮 %s/%s 条件「%s」值为空' % (t, b.get('label'), fw.get('name')))
                    elif fw['type'] == 'link-record' and not str(v).replace(',', '').isdigit():
                        BAD.append('按钮 %s/%s 关联记录条件值应是记录 id，现为 %s' % (t, b.get('label'), v))
                    elif (fw.get('options') or {}).get('isDictItem') and str(v) in labels and str(v) not in values:
                        BAD.append('按钮 %s/%s 字典条件值写了文案「%s」，应写落库值' % (t, b.get('label'), v))
    INFO.append('自定义按钮 %d 个' % nb)

print('核验 %d 张表 / %d 个控件' % (len(W), sum(len(x) for x in W.values())))
for i in INFO[:12]:
    print('  · ' + i)
if len(INFO) > 12:
    print('  · ……其余 %d 条提示略' % (len(INFO) - 12))
print('问题 %d 条：' % len(BAD))
for b in BAD:
    print('  x ' + b)
if A.self_test:
    missed = [n for (t, n) in INJECTED if not any(('%s.%s ' % (t, n)) in b for b in BAD)]
    print('自检：注入 %d 处，未被抓到 -> %s' % (len(INJECTED), missed or '无，校验器有效'))
    sys.exit(3 if missed else 0)
sys.exit(2 if BAD else 0)
