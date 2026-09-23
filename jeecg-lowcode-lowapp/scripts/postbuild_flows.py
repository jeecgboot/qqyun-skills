# -*- coding: utf-8 -*-
"""建后简流：按钮触发 / 工作表事件触发的流程，用中文名声明，脚本负责取值形态、save 前自愈、
幂等建流、节点字段权限。逻辑来自 2026-09-21 CRM 应用 22 条流程真机跑通的脚本（契约闸门违例 0）。
build_flows.py + flow_dsl 只出工作表事件流；**按钮触发、填写节点、字段权限、取关联明细逐行新增**走这里。

  python postbuild_flows.py --api-base URL --token T --tenant-id N --app-id A \
         --config flows_config.py [--work DIR] [--dry-run] [--replace 流程名,流程名]

前置：postbuild_probe.py 已跑过（子表转换/改名之后必须重跑，否则字段快照是旧的）。
配置文件是一段 Python，往 FLOWS / PERMS 里追加，写法见 references/postbuild-kit.md。

已固化的坑（不用再记）：
- 节点 id 前缀：审批/填写 Activity、排他/数据分支 Gateway、延时 TimerEventDefinition_；用 nid()/gid() 取号
- 按钮流根 attr.formTableId 必须为 None；data_update 的 updateFields 必须注入 attr；
  get_one 的 formTableId=form_<本节点id>_<表code>；取关联明细是 selectType=3 且不写 limitNum；
  逐行新增要 attr 与 formTableList 同时带 addDataType=2
- 审批后写回状态：approver → data_update **直连**。不要接「意见分支」——本环境 save 直接报
  mxGraph getAbsolutePoints() NPE（2026-09-21 试过三种 id 写法均失败）；驳回由审批节点自带按钮处理
- 「= 当前日期/时间」用 sysdate()/systime()，不要插 +0D 运算节点（契约闸门判违例）
- 字典字段写落库值：用 dv('字典名','文案')
"""
import sys, os, json, re, time, argparse, tempfile, hashlib, base64, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', '..', 'jeecg-lowcode-miniflow', 'scripts')))
from miniflow_creator import build_process_json, save_flow, deploy_flow
from desform_lowapp_utils import init_lowapp

ap = argparse.ArgumentParser()
ap.add_argument('--api-base', required=True)
ap.add_argument('--token', required=True)
ap.add_argument('--tenant-id', required=True)
ap.add_argument('--app-id', required=True)
ap.add_argument('--config', required=True)
ap.add_argument('--work', default=None)
ap.add_argument('--dry-run', action='store_true')
ap.add_argument('--replace', default='', help='逗号分隔的流程名：先删后建（之后重跑 postbuild_appconfig 重绑按钮）')
A = ap.parse_args()
API, TOKEN, TID, AID = A.api_base, A.token, str(A.tenant_id), A.app_id
WORK = A.work or os.path.join(tempfile.gettempdir(), 'jeecg-desform', AID)
for _f in ('probe.json', 'dicts.json'):
    if not os.path.exists(os.path.join(WORK, _f)):
        sys.exit('缺少 %s —— 先跑 postbuild_probe.py' % os.path.join(WORK, _f))
PROBE = json.load(open(os.path.join(WORK, 'probe.json'), encoding='utf-8'))
DICTS = json.load(open(os.path.join(WORK, 'dicts.json'), encoding='utf-8'))
CODE = {t: v['code'] for t, v in PROBE.items()}
TITLE = {t: v['titleField'] for t, v in PROBE.items()}
init_lowapp(API, TOKEN, tenant_id=int(TID) if TID.isdigit() else TID, app_id=AID)

_FLD = {}
for _t, _v in PROBE.items():
    _m = {}
    for _w in _v['widgets']:
        if _w['type'] == 'divider' or _w['name'] in _m:
            continue
        _m[_w['name']] = _w
    _FLD[_t] = _m


def w(t, n):
    if t not in _FLD:
        raise KeyError('应用里没有工作表「%s」' % t)
    x = _FLD[t].get(n)
    if x is None:
        raise KeyError('%s.%s 不存在（改过名/转过子表就重跑 postbuild_probe.py）' % (t, n))
    return x


def M(t, n):
    return w(t, n)['model']


def _assignee_family(t, n):
    """办理人字段的底层控件族：他表字段沿 showField 链解到最底层。
    引擎 MinFlowUtils:1094-1096 只认 fieldType 字面量 select-user / select-depart，
    写 link-field 两边都不进 → 部门 id 被当账号派发，无人收到待办（2026-09-22 项目管理实测）。"""
    x = w(t, n)
    ty = x['type']
    hops = 0
    while ty == 'link-field' and hops < 4:
        ft = x.get('fieldType')
        if ft and ft != 'link-field':
            ty = ft
            break
        nxt = None
        for tb, fs in _FLD.items():
            for cand in fs.values():
                if cand.get('model') == x.get('showField'):
                    nxt = cand
                    break
            if nxt:
                break
        if not nxt:
            break
        x, ty, hops = nxt, nxt['type'], hops + 1
    if ty not in ('select-user', 'select-depart'):
        sys.exit('FAIL: 办理人字段 %s.%s 解到的控件族是 %r，引擎只接受 select-user / select-depart'
                 '（他表字段请指向成员/部门控件）' % (t, n, ty))
    return ty


def T(t, n):
    """控件族：他表字段取其 fieldType，日期取档位"""
    x = w(t, n)
    if x['type'] == 'link-field':
        return x.get('fieldType') or 'input'
    if x['type'] == 'date':
        return x.get('dtype') or 'date'
    return x['type']


def dv(dict_name, label):
    items = DICTS.get(dict_name)
    if not items or label not in items:
        raise KeyError('字典「%s」里没有选项「%s」' % (dict_name, label))
    return items[label]


# ── 取号 ──
_TS, _SEQ = int(time.time() * 1000), [0]


def _next():
    _SEQ[0] += 1
    return '%d%03d' % (_TS, _SEQ[0])


def nid():
    return 'task' + _next()


def gid():
    return 'Gateway' + _next()


# ── 取值形态 ──
_START = '工作表事件触发'


def start(t, n):
    """当前触发记录的某字段"""
    return {'variableValue': M(t, n), 'formTableCode': CODE[t], 'variableName': n,
            'fieldType': T(t, n), 'formNodeType': 'table', 'formNodeId': 'start', 'formNodeName': _START}


def start_id(t):
    """当前触发记录的记录 id"""
    return {'variableValue': '_id', 'formTableCode': CODE[t], 'variableName': '记录id',
            'fieldType': 'input', 'formNodeType': 'table', 'formNodeId': 'start', 'formNodeName': _START}


def search(node, t, n):
    """前面 get_one 节点查到的那条记录的字段；node = get_one() 的返回值"""
    return {'variableValue': M(t, n), 'formTableCode': CODE[t], 'variableName': n,
            'fieldType': T(t, n), 'formNodeType': 'search', 'formNodeId': node['id'], 'formNodeName': node['name']}


def more(node, t, n):
    """前面 get_more_link 节点取到的明细行字段（逐行新增时用）"""
    return {'variableValue': M(t, n), 'formTableCode': CODE[t], 'variableName': n,
            'fieldType': T(t, n), 'formNodeType': 'getMore', 'formNodeId': node['id'], 'formNodeName': node['name']}


def more_id(node, t):
    return {'variableValue': '_id', 'formTableCode': CODE[t], 'variableName': '记录id',
            'fieldType': 'input', 'formNodeType': 'getMore', 'formNodeId': node['id'], 'formNodeName': node['name']}


def added(node, t):
    """前面 add 节点刚新增的那条记录的 id（写进关联记录字段）"""
    return {'variableValue': '_id', 'formTableCode': CODE[t], 'variableName': '记录id',
            'fieldType': 'link-record', 'formNodeType': 'plus', 'formNodeId': node['id'], 'formNodeName': node['name']}


def sysdate():
    return {'formNodeType': 'system', 'variableValue': 'nowDate', 'variableName': '当前日期'}


def systime():
    return {'formNodeType': 'system', 'variableValue': 'nowTime', 'variableName': '当前时间'}


# ── 节点 ──
def upd(name, t, fields, src=None):
    """更新记录。src=None 更新触发记录；src=get_one 节点 则更新查到的那条。fields: [(字段名, 值)]"""
    nid_ = nid()
    ufs = []
    for i, (fn, val) in enumerate(fields):
        e = {'id': '%s_%d' % (nid_, i), 'optType': '1', 'fieldValue': '', 'field': M(t, fn),
             'val': val, 'fieldType': T(t, fn), 'type': T(t, fn)}
        if isinstance(val, dict):
            e['valueType'], e['valType'] = 3, 'variable'
            if w(t, fn)['type'] == 'date':
                e['options'] = {'format': 'yyyy-MM-dd HH:mm:ss' if T(t, fn).startswith('datetime') else 'yyyy-MM-dd'}
        ufs.append(e)
    s = (src['id'], 'search') if src else ('start', 'table')
    return {'type': 'data_update', 'id': nid_, 'name': name, 'formTableCode': CODE[t], 'formTableName': t,
            'formTableSourceTaskId': s[0], 'attr': {'formTableSourceNodeType': s[1]},
            'updateFields': ufs, '_uf': ufs, '_src': s, '_tbl': t}


def add(name, t, mapping, batch_from=None):
    """新增记录。mapping: {目标字段名: 值}；batch_from=get_more_link 节点 则按行批量新增"""
    fm = {M(t, fn): val for fn, val in mapping.items()}
    n = {'type': 'data_add', 'id': nid(), 'name': name, 'formTableCode': CODE[t], 'formTableName': t,
         'formModel': fm, '_fm': fm, '_tbl': t}
    if batch_from:
        n['_batch'] = batch_from['id']
    return n


def get_one(name, t, conds, empty=3):
    """取单条。empty: 3=后面接 branch() 分支；1=未找到继续执行"""
    return {'type': 'get_one', 'id': nid(), 'name': name, 'getType': 1, 'formTableCode': CODE[t],
            'formTableName': t, 'emptyAction': empty, 'conditions': conds, '_tbl': t}


def cond(t, field, val):
    """get_one 的条件：目标表字段 等于 某取值。field='_id' 表示按记录 id 匹配"""
    is_id = field == '_id'
    return {'rule': 'eq', 'ruleName': '等于', 'valueType': 2, 'val': val, 'name': field,
            'field': '_id' if is_id else M(t, field), 'columnName': '记录id' if is_id else field,
            'type': 'input' if is_id else T(t, field), 'valType': 'variable'}


def get_more_link(name, src_t, link_field, det_t):
    """从触发记录的关联字段取全部明细行（selectType=3）"""
    return {'type': 'get_more', 'id': nid(), 'name': name, 'formTableCode': CODE[src_t],
            'formTableName': src_t, '_gm3': {'src_t': src_t, 'link_field': link_field, 'det_t': det_t}}


DATA_BRANCH_NAME = '数据分支'      # 引擎 MiniDesConstant.DATA_BRANCH_NAME（BaseDataDelegate:1088 精确比较）


def branch(name, found, missing):
    """数据分支，紧跟 get_one(empty=3)。⚠️ 网关不能嵌在另一个网关的分支里。

    ⚠️ **网关名被强制成「数据分支」**，`name` 只当注释用：引擎 `BaseDataDelegate.noDataExecute()`
    拿网关名和硬编码常量精确比较，名字不对时**取不到数据就直接终止实例**（gotchas #113），
    而 save/deploy/verify 全绿。本函数此前原样透传 `name`，文档与 crm 示例又恰好教了
    自定义名字（「判断线索池是否存在」），照抄必中（2026-09-22 CRM R3 实测发现）。"""
    g = gid()
    if name and name != DATA_BRANCH_NAME:
        print('NOTE:data_branch 网关名「%s」→ 强制为「%s」（引擎按名字判定，见 gotchas #113）'
              % (name, DATA_BRANCH_NAME))
    return {'type': 'data_branch', 'id': g, 'name': DATA_BRANCH_NAME, 'conditionNodes': [
        {'id': g + 'a', 'name': '有数据', 'nodes': found}, {'id': g + 'b', 'name': '无数据', 'nodes': missing}]}


def when(t, field, val, name, nodes):
    """排他分支的一支：触发记录字段 等于 固定值"""
    return {'name': name, 'isDefault': False, 'branchType': 1, 'nodes': nodes, 'conditions': [{
        'rule': 'eq', 'ruleName': '等于', 'field': M(t, field), 'columnName': field, 'val': val,
        'type': T(t, field), 'valueType': '1', 'valType': T(t, field)}]}


def otherwise(name, nodes=None):
    return {'name': name, 'isDefault': True, 'branchType': 2, 'nodes': nodes or []}


def exclusive(name, branches):
    """排他分支：when(...)×N + otherwise(...) 恰好一支"""
    for i, b in enumerate(branches):
        b['priorityLevel'] = i + 1
    return {'type': 'exclusive', 'id': gid(), 'name': name, 'conditionNodes': branches}


def _grp(t=None, field=None):
    g = {'approverIds': [], 'approverNames': [], 'deptIds': [], 'deptNames': [], 'roleIds': [],
         'roleNames': [], 'postIds': [], 'postNames': [], 'levelMode': 1, 'approverId': '', 'approverName': ''}
    if field:                                   # 办理人 = 表单成员/部门字段
        x = w(t, field)
        fam = _assignee_family(t, field)        # 引擎只认 select-user / select-depart 两个字面量（MinFlowUtils:1094）
        vc = [{'formTableCode': CODE[t], 'formTableId': 'form_start_%s' % CODE[t], 'nodeId': 'start',
               'nodeType': 'table', 'fieldName': x['model'], 'fieldType': fam, 'fieldLabel': field}]
        if fam == 'select-depart':
            vc[0]['isNeedTranslateToUserIds'] = True
        g.update({'approverType': 'candidateUsers', 'assigneeType': 'assigneeByVariable',
                  'expressionsIds': [], 'expressionsNames': [], 'variableTitle': [field],
                  'variableContent': vc, 'formTableType': 'table'})
    else:                                       # 办理人 = 获取发起人
        g.update({'approverType': 'candidateUser', 'assigneeType': 'assigneeByExp',
                  'expressionsIds': ['${applyUserId}'], 'expressionsNames': ['获取发起人'],
                  'variableTitle': [], 'variableContent': '', 'formTableType': ''})
    return g


def appr(name, t=None, field=None):
    """审批节点（或签）。默认审批人=获取发起人；给 t+field 则取表单成员字段"""
    g = [_grp(t, field)]
    c = field or '获取发起人'
    return {'type': 'approver', 'id': 'Activity' + _next(), 'name': name, 'approvalMode': 1,
            'approverGroups': g, 'content': c,
            'attr': {'approvalMethod': 1, 'approverGroups': g, 'level': '1'}, '_content': c}


def fill(name, t=None, field=None):
    """填写节点（办理人能看/改表单）。字段可编辑/必填/隐藏在 PERMS 里配"""
    g = [_grp(t, field)]
    c = field or '获取发起人'
    return {'type': 'edit', 'id': 'Activity' + _next(), 'name': name, 'approverGroups': g, 'content': c,
            'attr': {'approverGroups': g, 'level': '1', 'formEditStatus': True}, '_content': c}


def delete_cur(name, t):
    return {'type': 'data_delete', 'id': nid(), 'name': name, 'formTableCode': CODE[t], 'formTableName': t,
            'formTableSourceTaskId': 'start',
            'attr': {'formTableSourceNodeType': 'table', 'formTableId': 'form_start_%s' % CODE[t]}}


def delay(name, minutes):
    return {'type': 'time', 'id': 'TimerEventDefinition_' + _next(), 'name': name, 'duration': 'PT%dM' % minutes}


def msg(name, content, to=(), to_names=(), body=()):
    """系统消息节点（message_system）。

    ⚠️ 收件人/正文都可以是**表单字段**（不是固定人/固定文本），此时必须传变量引用，
    两种形态不同、不能混用（miniflow-node-types.md §8.1b）：
      收件人 = 6 键 `var.` 条目（formTableCode/formTableId/nodeId/nodeType/field/fieldType）
      正文   = 4 键 ref → md5 → base64 存进 `attr.jsonContext`，正文里写 `{{<md5>.<中文名>}}`

    to   : 收件人列表。元素传 `start(t, 人员字段)` 或 `search(get_one节点, t, 人员字段)` 的返回值
           （=该记录上的人员字段），或固定 id 字符串 `'user.xx'`/`'role.xx'`/`'dept.xx'`。
    to_names: 显示名，与 to 一一对应；传变量引用时可省（自动取字段中文名）。
    body : 正文引用的字段，传 `start(...)`/`search(...)` 的返回值；
           content 里用**该字段中文名**作占位符 `{机会名称}`，本函数负责换成哈希形态。

    位置约束：消息节点必须挂在被引用节点**之后**（收件人引用的 get_one 必须在同一链上游）。
    """
    ids, names, jc = [], [], {}
    for i, x in enumerate(to):
        if isinstance(x, dict):                                   # 变量引用 → 6 键 var. 条目
            _nid = x['formNodeId']
            ids.append('var.' + json.dumps({
                'formTableCode': x['formTableCode'],
                'formTableId': ('form_start_%s' % x['formTableCode']) if _nid == 'start'
                               else 'form_%s_%s' % (_nid, x['formTableCode']),
                'nodeId': _nid, 'nodeType': x['formNodeType'],
                'field': x['variableValue'], 'fieldType': x['fieldType'],
            }, ensure_ascii=False))
            names.append(to_names[i] if i < len(to_names) else x.get('variableName', ''))
        else:                                                     # 固定收件人
            ids.append(x)
            names.append(to_names[i] if i < len(to_names) else x)
    # ⚠️ 校验必须在替换**前**对原文做：替换后的 `{{<md5>.中文名}}` 本身也会被 `\{[^{}]+\}` 匹配到
    missing = [x for x in re.findall(r'\{([^{}]+)\}', content) if x not in {r['variableName'] for r in body}]
    if missing:                                                   # 字段名写错 / 忘了进 body
        raise KeyError('msg(%r)：正文里 %s 没有对应的 body 引用 —— 占位符必须用**字段中文名**，'
                       '且该字段要出现在 body 里。' % (name, missing))
    for r in body:
        ref = {'field': r['variableValue'], 'formTableCode': r['formTableCode'],
               'nodeId': r['formNodeId'], 'nodeType': r['formNodeType']}
        cs = json.dumps(ref, ensure_ascii=False, separators=(',', ':'))
        h = hashlib.md5(cs.encode('utf-8')).hexdigest()
        content = content.replace('{%s}' % r['variableName'], '{{%s.%s}}' % (h, r['variableName']))
        jc[h] = base64.b64encode(cs.encode('utf-8')).decode()
    return {'type': 'notice', 'id': nid(), 'name': name, 'attr': {
        'noticeType': 'system', 'noticeContent': content,
        'toUserIds': ids, 'toUserNames': names, 'jsonContext': jc}}


def trig(t, field, val):
    """工作表事件的触发条件：字段 等于 固定值（字典字段传 dv() 的结果）"""
    return [{'rule': 'eq', 'ruleName': '等于', 'valueType': '1', 'val': val, 'name': None,
             'field': M(t, field), 'columnName': field, 'type': T(t, field), 'valType': T(t, field)}]


FLOWS, PERMS = [], []


def button_flow(name, table, nodes):
    FLOWS.append({'name': name, 'start': 'buttonEvent', 'table': table, 'nodes': nodes})


def table_flow(name, table, nodes, event='add', cond=None, watch=None):
    """event: add / update / add|update / delete；watch: 监控字段名列表（update 时防重复触发）"""
    FLOWS.append({'name': name, 'start': 'tableEvent', 'table': table, 'event': event, 'nodes': nodes,
                  'cond': cond, 'watch': [M(table, f) for f in (watch or [])]})


def perm(flow, node, table, editable=(), required=(), hidden=()):
    """节点字段权限：没点名的字段一律只读可见"""
    PERMS.append((flow, node, table, list(editable), list(required), list(hidden)))


exec(compile(open(A.config, encoding='utf-8').read(), A.config, 'exec'), globals())


# ── 构建 + save 前自愈 ──
def walk_nodes(n, acc=None):
    acc = [] if acc is None else acc
    if not isinstance(n, dict):
        return acc
    if n.get('type'):
        acc.append(n)
    for ch in [n.get('childNode')] + list(n.get('conditionNodes') or []):
        walk_nodes(ch, acc)
    return acc


def _src_nodes(nodes, acc):
    for n in nodes or []:
        if isinstance(n, dict):
            if n.get('id'):
                acc[n['id']] = n
            for b in n.get('conditionNodes') or []:
                _src_nodes(b.get('nodes'), acc)
    return acc


def build(flow):
    t = flow['table']
    ts = int(_next())
    cfg = {'processName': flow['name'], 'processKey': 'process%d' % ts, 'processType': 'oa',
           'lowAppId': AID, 'tenantId': TID, 'startType': flow['start'], 'formTableCode': CODE[t],
           'formTableName': t, 'titleField': TITLE[t], 'startEventType': flow.get('event', 'add'),
           'startTaskId': 'task%d000' % ts, 'nodes': flow['nodes']}
    if flow['start'] == 'tableEvent':
        cfg['formTableId'] = 'form_start_%s' % CODE[t]
    if flow.get('cond'):
        cfg['startCondition'] = [{'id': str(ts), 'matchType': '', 'queryItems': flow['cond']}]
    pj = build_process_json(cfg)
    if flow['start'] == 'buttonEvent':
        pj.setdefault('attr', {})['formTableId'] = None
    if flow.get('watch'):
        pj.setdefault('attr', {})['conditionFields'] = flow['watch']

    origs = _src_nodes(flow['nodes'], {})
    for n in walk_nodes(pj):
        orig, a, ty = origs.get(n.get('id')), n.setdefault('attr', {}), n.get('type')
        if not orig:
            continue
        if ty == 'data_update' and orig.get('_uf'):
            s = orig['_src']
            a['updateFields'] = orig['_uf']
            a.setdefault('level', '1')
            a['formTableSourceNodeType'], a['formTableSourceTaskId'] = s[1], s[0]
            n['formTableSourceTaskId'] = s[0]
            a['formTableId'] = ('form_start_%s' % CODE[orig['_tbl']] if s[0] == 'start'
                                else 'form_%s_%s' % (s[0], CODE[orig['_tbl']]))
        elif ty == 'data_add' and orig.get('_fm') is not None:
            a['formModel'] = orig['_fm']
            if orig.get('_batch'):
                a.update({'addDataType': 2, 'formTableSourceGetDataType': 1,
                          'formTableSourceNodeType': 'getMore', 'formTableSourceTaskId': orig['_batch']})
                # ⚠️ 批量新增的 5 个 source 键**漏一个都是静默失效**：save/deploy 全 success、
                # 节点回读也在，引擎就是不写库、目标表 0 行；下游若接多实例子流程，还会连带炸在
                # `Cannot resolve identifier '<getMore节点id>_assigneeDataIdList'`
                # —— getMore 只在 `if (isNotEmpty(records))` 里发布那个变量（2026-09-22 实机踩到）。
                # 这两个键能从 `_batch` 指的上游 get_more 的 DSL 节点直接推出来
                # （`get_more_link` 的节点上就带 formTableCode）：
                #   formTableSourceCode = 上游 get_more 的 formTableCode（**源表**，不是本节点的新增目标表）
                #   formTableSourceId   = form_{上游 get_more 节点 id}_{源表编码}
                _b = origs.get(orig['_batch']) or {}
                _bcode = _b.get('formTableCode')
                if _bcode:
                    a['formTableSourceCode'] = _bcode
                    a['formTableSourceId'] = 'form_%s_%s' % (orig['_batch'], _bcode)
                for e in (pj.get('formTableList') or []):
                    if e.get('nodeId') == n['id']:
                        e['addDataType'], e['formTableSourceGetDataType'] = 2, 1
        elif ty == 'data_get_one':
            a['formTableId'] = 'form_%s_%s' % (n['id'], CODE[orig['_tbl']])
            a.pop('limitNum', None)
        elif ty == 'data_get_more' and orig.get('_gm3'):
            g = orig['_gm3']
            a.update({'selectType': 3, 'formType': 2, 'getDataType': 1, 'noDataType': 1,
                      'formTableCode': CODE[g['src_t']], 'formTableName': g['src_t'],
                      'formTableId': 'form_start_%s' % CODE[g['src_t']],
                      'linkFormTableField': M(g['src_t'], g['link_field']),
                      'linkFormTableCode': CODE[g['det_t']], 'linkFormTableName': g['det_t'],
                      'linkFormTableType': 1, 'formTableSourceTaskId': 'start',
                      'formTableSourceNodeType': 'table', 'expressionType': 'delegateExpression',
                      'expressionValue': '${getMoreRecordDelegate}', 'sortType': 'desc'})
            a.pop('limitNum', None)
            for k in ('getType', 'sourceTaskId', 'relationField'):
                n.pop(k, None)
            for e in (pj.get('formTableList') or []):
                if e.get('nodeId') == n['id']:
                    e.update({'formTableCode': CODE[g['det_t']], 'formTableName': g['det_t'],
                              'formTableMainCode': CODE[g['src_t']], 'selectType': 3, 'getDataType': 1,
                              'formTableId': 'form_%s_%s' % (n['id'], CODE[g['det_t']])})
        elif ty in ('edit', 'approver') and orig.get('_content'):
            c = n.get('content') or ''
            if (not c) or '$' in c or 'assigneeBy' in c:
                n['content'] = orig['_content']
            for grp in (n.get('approverGroups') or []) + (a.get('approverGroups') or []):
                if grp.get('assigneeType') == 'assigneeByVariable' and not grp.get('variableTitle'):
                    grp['variableTitle'] = orig['approverGroups'][0]['variableTitle']
    for n in walk_nodes(pj):
        if n.get('type') == 'data_update':
            assert (n.get('attr') or {}).get('updateFields'), 'updateFields 未注入：%s' % n.get('name')
        if n.get('type') in ('edit', 'approver'):
            c = n.get('content') or ''
            assert c and '$' not in c and 'assigneeBy' not in c, '办理人显示名为空/是表达式：%s' % n.get('name')
    return cfg, pj


def _req(method, path, body=None):
    hdr = {'X-Access-Token': TOKEN, 'X-Tenant-Id': TID}
    data = None
    if body is not None:
        data, hdr['Content-Type'] = json.dumps(body, ensure_ascii=False).encode('utf-8'), 'application/json'
    r = urllib.request.Request(API + path, data=data, headers=hdr, method=method)
    with urllib.request.urlopen(r, timeout=120) as f:
        return json.loads(f.read().decode('utf-8'))


def existing_flows():
    r = _req('GET', '/act/process/extActProcess/list?pageSize=500&lowAppId=' + AID)   # 不带 pageSize 只回 10 条
    return {x.get('processName'): x.get('id') for x in ((r.get('result') or {}).get('records') or [])
            if x.get('lowAppId') == AID}


def _sig(pj):
    """结构签名：节点(类型,名称)序列 + 写入内容，节点 id 归一化"""
    norm = lambda s: re.sub(r'(task|Activity|Gateway|flow|suggest_|TimerEventDefinition_|process)\d+\w?', r'\1#', s)
    out = []
    for n in walk_nodes(pj):
        a = n.get('attr') or {}
        out.append([n.get('type'), n.get('name'),
                    norm(json.dumps(a.get('updateFields'), sort_keys=True, ensure_ascii=False)) if a.get('updateFields') else None,
                    norm(json.dumps(a.get('formModel'), sort_keys=True, ensure_ascii=False)) if a.get('formModel') else None])
    return out


names = [f['name'] for f in FLOWS]
dup = {n for n in names if names.count(n) > 1}
if dup:
    sys.exit('流程名重复：%s（同名流程按名查询只返回最新一条，后续换绑会错）' % dup)

ex = existing_flows()
replace = {x.strip() for x in A.replace.split(',') if x.strip()}
unknown = replace - set(names)
if unknown:
    sys.exit('--replace 点名了配置里没有的流程：%s' % unknown)

res, fail = [], 0
for f in FLOWS:
    try:
        cfg, pj = build(f)
    except Exception as e:
        res.append('FAIL %s 构建失败：%s' % (f['name'], str(e)[:160])); fail += 1; continue
    fid = ex.get(f['name'])
    if A.dry_run:
        if not fid:
            res.append('PLAN %s 新建（%d 个节点）' % (f['name'], len(walk_nodes(pj)) - 1)); continue
        cur = json.loads(((_req('GET', '/act/process/extActProcess/queryById?id=%s' % fid) or {})
                          .get('result') or {}).get('processJson') or '{}')
        same = _sig(cur) == _sig(pj)
        res.append('%s %s' % ('SAME' if same else 'DIFF', f['name']))
        continue
    if fid and f['name'] in replace:
        _req('DELETE', '/act/process/extActProcess/delete?id=%s' % fid)
        fid = None
    if fid:
        res.append('SKIP %s 已存在 %s' % (f['name'], fid)); continue
    r = save_flow(API, TOKEN, cfg, pj)
    if not r.get('success'):
        res.append('FAIL %s %s' % (f['name'], str(r.get('message'))[:160])); fail += 1; continue
    fid = r['result']['id']
    d = deploy_flow(API, TOKEN, fid)
    if not (d or {}).get('success'):
        # 打后端原文：本轮一次「15 条全 deploy 失败」的真因是后端 Xerces 类初始化被毒化，
        # 与配置无关，但日志只写「已保存但发布失败」，只能手写一次 deploy 才看得到（项目管理 R3）
        res.append('FAIL %s 已保存但发布失败 %s —— %s'
                   % (f['name'], fid, str((d or {}).get('message'))[:200])); fail += 1; continue
    ex[f['name']] = fid
    res.append('OK %s %s' % (f['name'], fid))

# ── 节点字段权限：按流程名+节点名回读真实节点 id 再配 ──
if PERMS and not A.dry_run:
    from desform_utils import get_form_fields
    cache, fcache = {}, {}
    for fname, nname, tbl, ed, rq, hd in PERMS:
        fid = ex.get(fname)
        if not fid:
            res.append('FAIL 权限 %s/%s：流程不存在' % (fname, nname)); fail += 1; continue
        if fid not in cache:
            pj = json.loads(((_req('GET', '/act/process/extActProcess/queryById?id=%s' % fid) or {})
                             .get('result') or {}).get('processJson') or '{}')
            cache[fid] = {n.get('name'): n.get('id') for n in walk_nodes(pj)}
        node_id = cache[fid].get(nname)
        if not node_id:
            res.append('FAIL 权限 %s/%s：节点不存在' % (fname, nname)); fail += 1; continue
        if tbl not in fcache:
            fcache[tbl] = get_form_fields(CODE[tbl])[1]      # 要 key：必须用 desform_utils 的，不能用 miniflow 的同名函数
        unknown_f = [x for x in list(ed) + list(rq) + list(hd) if x not in fcache[tbl]]
        if unknown_f:
            res.append('FAIL 权限 %s/%s：字段不存在 %s' % (fname, nname, unknown_f)); fail += 1; continue
        rows = []
        for name, meta in fcache[tbl].items():
            if '.' in name:
                continue
            req, base = name in rq, {'ruleCode': meta['model'], 'ruleName': name, 'desformComKey': meta['key'],
                                     'formBizCode': CODE[tbl], 'formType': '2', 'processId': fid,
                                     'processNodeCode': node_id}
            rows.append(dict(base, ruleType='1', status='0' if name in hd else '1', required=req))
            rows.append(dict(base, ruleType='2', status='0' if (name in ed or req) else '1', required=req))
        r = _req('POST', '/act/process/extActProcessNodePermission/saveOrUpdateBatch', rows)
        if r.get('success'):
            res.append('OK 权限 %s/%s %d 行' % (fname, nname, len(rows)))
        else:
            res.append('FAIL 权限 %s/%s %s' % (fname, nname, str(r.get('message'))[:100])); fail += 1

for x in res:
    print(x)
diff = sum(1 for x in res if x.startswith('DIFF'))
print('%s:flows 共 %d 条 / 失败 %d%s' % ('DRY' if A.dry_run else 'OK', len(FLOWS), fail,
                                       (' / 与现网不一致 %d' % diff) if A.dry_run else ''))
if not A.dry_run:
    print('TODO: 跑 jeecg-lowcode-miniflow/scripts/check_node_contract.py，违例 0 才算交付')
if fail or diff:
    sys.exit(2)
