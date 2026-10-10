# -*- coding: utf-8 -*-
"""流程外科：flow_dsl / postbuild_flows 都表达不了的几档，建完后按节点名改 processJson → saveFlow → deploy。

用法:
  python flow_surgery.py --api-base URL --token T --tenant-id N --app-id A --config ops.py [--dry-run]

ops.py 里写 OPS = [...]，每项一个 dict（流程按 processName 找；同名多条时写 'flow': '名称@表code' 或临时唯一名）：
  {'op': 'to_button', 'flow': 名}                      表事件 → 按钮触发（gotchas #97 的键集，2026-09-28 与同应用
                                                        postbuild_flows 建的按钮流逐键对照过）
  {'op': 'link_get_one', 'flow': 名, 'node': 取单条节点名, 'link': 关联字段中文名, 'src': 'start'|'<节点名>'}
                                                        「从关联字段获取单条」（selectType=3，node-contract §4）：
                                                        src=start → 取触发行/子流程输入行的关联字段；
                                                        src=节点名 → 取前面某个取单条节点那条记录的关联字段
  {'op': 'sequential', 'flow': 名}                      调子流程改「逐条执行」（isSequential=true）
  {'op': 'rename', 'flow': 临时名, 'to': 正式名}        最后一步：临时唯一名改回需求原名（同名流程分属多表时用）
  {'op': 'var_cond', 'flow': 名, 'gateway': 网关名, 'branch': 分支名, 'field': 条件字段中文名,
   'rule': 'lt'|'le'|'gt'|'ge'|'eq'|'ne', 'var_table': 表, 'var_field': 字段中文名, 'var_node': 'start'|节点名}
                                                        网关条件「字段 与 另一个表单字段 比较」（线上写法：valueType=2 + 变量；分支显示为「字段 规则 表名.字段」）。
                                                        取值对象形态**排他/相容网关均实测可用**（2026-09-28 相容 18/18；2026-10-09 生产管理排他网关全链复验）。
                                                        ⚠️「排他网关恒假」是旧结论，真因是**值落成了常量**（valueType:"1"；数值族字段的常量部署时还不加引号 → 运行时崩）。
  {'op': 'set_branch', 'flow': 名, 'branch': 分支名, 'src': 'start'|'<取单条节点名>',
   'items': [(字段中文名, 规则中文名, 值)], 'match': 'AND'|'OR', 可选: 'gateway': 网关名 / 'branch_id': 分支行id}
                                                        整条重写某分支的条件。⚠️ 键名：条目列表是 **items**（不是 branches）、
                                                        来源是 **src**（不是 node）、主语(LHS)写**字段中文名**（不写元组）。
                                                        值可为字面量 / None(配「为空/不为空」) / ('var','start'|节点名,'字段名')。
                                                        同一流程内分支名重复时（多个网关上都有「全部合格」）必须加 **gateway** 联定位（或 branch_id）。
每项都幂等；dry-run 只打印计划。
"""
import sys, os, json, argparse, copy, re
sys.stdout.reconfigure(encoding='utf-8')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import requests                                              # noqa: E402
from miniflow_creator import save_flow, deploy_flow, fetch_form_fields, fetch_app_forms  # noqa: E402

ap = argparse.ArgumentParser()
for k in ('--api-base', '--token', '--tenant-id', '--app-id', '--config'):
    ap.add_argument(k, required=True)
ap.add_argument('--dry-run', action='store_true')
A = ap.parse_args()
API, T, TID, AID = A.api_base.rstrip('/'), A.token, str(A.tenant_id), str(A.app_id)
H = {'X-Access-Token': T, 'X-Tenant-Id': TID, 'X-Low-App-ID': AID}
G = {}
exec(open(A.config, encoding='utf-8').read(), G)
OPS = G['OPS']


def get(path, **p):
    return requests.get(API + path, headers=H, params=p, timeout=60).json()


recs = [x for x in (get('/act/process/extActProcess/list', pageSize=1000, lowAppId=AID).get('result') or {}).get('records', [])
        if str(x.get('lowAppId')) == AID]
FULL = {}


def load(name):
    if '@' in name:                                   # 名称@工作表名 或 名称@表code：同名流程分属多表时用
        n, tb = name.split('@', 1)
        cand = [x for x in recs if x['processName'] == n]
        cand = [x for x in cand if tb in (json.loads(full(x['id'])['processJson'])['formTableList'][0].get('formTableCode'),
                                         json.loads(full(x['id'])['processJson'])['formTableList'][0].get('formTableName'))]
    else:
        cand = [x for x in recs if x['processName'] == name]
    if len(cand) != 1:
        raise SystemExit('流程「%s」匹配 %d 条（同名多表请用 名@表code 或临时唯一名）' % (name, len(cand)))
    r = full(cand[0]['id'])
    r['_pj'] = json.loads(r['processJson'])
    return r


def full(fid):
    if fid not in FULL:
        FULL[fid] = get('/act/process/extActProcess/queryById', id=fid)['result']
    return FULL[fid]


def walk(n):
    if isinstance(n, dict) and n.get('type'):
        yield n
        if n.get('childNode'):
            yield from walk(n['childNode'])
        for c in n.get('conditionNodes') or []:
            yield from walk(c)


def node(pj, name):
    ns = [x for x in walk(pj) if x.get('name') == name]
    if len(ns) != 1:
        raise SystemExit('节点「%s」匹配 %d 个' % (name, len(ns)))
    return ns[0]


FIELDS = {}
_TNAME = {}


def tname_of(code):
    if not _TNAME:
        for ap_ in fetch_app_forms(API, T, TID):
            if str(ap_.get('id')) == AID:
                _TNAME.update({f_['code']: f_['name'] for f_ in ap_.get('forms') or []})
    return _TNAME.get(code)


def fields(code):
    if code not in FIELDS:
        FIELDS[code] = fetch_form_fields(API, T, code, TID)
    return FIELDS[code]


def replace_all(o, fn):
    if isinstance(o, dict):
        fn(o)
        for v in o.values():
            replace_all(v, fn)
    elif isinstance(o, list):
        for v in o:
            replace_all(v, fn)


DIRTY = {}
LOG = []
for op in OPS:
    r = DIRTY.get(op['flow']) or load(op['flow'])
    pj = r['_pj']
    k = op['op']
    if k == 'to_button':
        if pj.get('startType') == 'buttonEvent':
            LOG.append('SAME to_button %s' % op['flow']); continue
        pj['startType'] = 'buttonEvent'; pj['name'] = '按钮触发'
        a = pj.setdefault('attr', {})
        a['startType'] = 'buttonEvent'; a['formTableId'] = None; a['startEventType'] = 'add'; a['startCondition'] = []
        for x in pj.get('formTableList') or []:
            if x.get('nodeId') == 'start':
                x['nodeName'] = '按钮触发'

        def _fix(o):
            if o.get('formNodeId') == 'start' and o.get('formNodeName') == '工作表事件触发':
                o['formNodeName'] = '按钮触发'
        replace_all(pj, _fix)
        r['startType'] = 'buttonEvent'
        LOG.append('to_button %s' % op['flow'])
    elif k == 'link_get_one':
        n = node(pj, op['node'])
        a = n.setdefault('attr', {})
        if a.get('selectType') == 3 and a.get('linkFormTableCode'):     # 已改过（幂等重跑）：目标表在 link* 上
            tgt_code, tgt_name = a['linkFormTableCode'], a.get('linkFormTableName')
        else:
            tgt_code = a.get('formTableCode') or n.get('formTableCode')
            tgt_name = a.get('formTableName') or n.get('formTableName')
        if op.get('src', 'start') == 'start':
            st = next(x for x in pj['formTableList'] if x.get('nodeId') == 'start' or x.get('isSubStart'))
            sid, stype = st['nodeId'], ('search' if st.get('isSubStart') else 'table')
            if pj.get('startType') == 'subEvent':
                sid, stype = st['nodeId'], 'search'
            scode, sname = st['formTableCode'], st['formTableName']
        else:
            sn = node(pj, op['src'])
            sa = sn.get('attr') or {}
            sid, stype = sn['id'], 'search'
            scode, sname = sa.get('linkFormTableCode') or sa.get('formTableCode'), sa.get('linkFormTableName') or sa.get('formTableName')
        f = fields(scode).get(op['link'])
        if not f:
            raise SystemExit('「%s」里没有关联字段「%s」' % (sname, op['link']))
        want = {'selectType': 3, 'formType': 2, 'formTableCode': scode, 'formTableName': sname,
                'formTableSourceTaskId': sid, 'formTableSourceNodeType': stype, 'formTableSourceGetDataType': 1,
                'formTableId': 'form_%s_%s' % (sid, scode), 'linkFormTableField': f['model'],
                'linkFormTableCode': tgt_code, 'linkFormTableName': tgt_name, 'linkFormTableType': 1,
                'expressionType': 'delegateExpression', 'expressionValue': '${getOneRecordDelegate}',
                'noDataType': 1, 'searchFieldGroup': [], 'searchContent': []}
        if all(a.get(x) == v for x, v in want.items()):
            LOG.append('SAME link_get_one %s/%s' % (op['flow'], op['node'])); continue
        a.update(want)
        n['content'] = '关联表 "%s"' % tgt_name
        for x in pj.get('formTableList') or []:
            if x.get('nodeId') == n['id']:
                x.update({'formTableId': 'form_%s_%s' % (n['id'], tgt_code), 'nodeType': 'search', 'formTableCode': tgt_code,
                          'formTableName': tgt_name, 'formTableMainCode': scode, 'formTableType': 1, 'selectType': 3})
        LOG.append('link_get_one %s/%s ← %s.%s' % (op['flow'], op['node'], sname, op['link']))
    elif k == 'sequential':
        hit = 0
        for n in walk(pj):
            if n['type'] == 'callActivity':
                a = n.setdefault('attr', {})
                if a.get('isSequential') is not True:
                    a['isSequential'] = True; hit += 1
        LOG.append('sequential %s (%d)' % (op['flow'], hit))
    elif k == 'var_cond':
        g = node(pj, op['gateway'])
        br = next(c for c in g['conditionNodes'] if c.get('name') == op['branch'])
        items = [q for grp in (br.get('attr') or {}).get('conditionGroup') or [] for q in grp.get('queryItems') or []]
        q = next(q for q in items if q.get('columnName') == op['field'] and q.get('rule') == op['rule'])
        vt_code = next(x['formTableCode'] for x in pj['formTableList']
                       if (op.get('var_node', 'start') == 'start' and x.get('nodeId') == 'start')
                       or x.get('nodeName') == op.get('var_node'))
        vf = fields(vt_code)[op['var_field']]
        vn = 'start' if op.get('var_node', 'start') == 'start' else node(pj, op['var_node'])['id']
        q.update({'valueType': 2, 'valType': 'variable',
                  'val': {'variableValue': vf['model'], 'formTableCode': vt_code, 'variableName': op['var_field'],
                          'formNodeType': 'table' if vn == 'start' else 'search', 'formNodeId': vn,
                          'formNodeName': pj.get('name') if vn == 'start' else op['var_node']}})
        LOG.append('var_cond %s/%s/%s %s %s' % (op['flow'], op['branch'], op['field'], op['rule'], op['var_field']))
    elif k == 'set_branch':
        # 整条重写分支条件：{'flow','branch','src':'start'|取单条节点名,'items':[(字段,规则,值)], 'match':'AND'}
        # 值：字面量 / None(配「为空」「不为空」) / ('var', 'start'|节点名, 字段名) = 与另一个字段比较（线上写法）
        RULE = {'等于': 'eq', '不等于': 'ne', '大于': 'gt', '大于等于': 'ge', '小于': 'lt', '小于等于': 'le',
                '为空': 'empty', '不为空': 'not_empty'}
        br = [x for x in walk(pj) if x.get('name') == op['branch'] and (x.get('attr') or {}).get('conditionGroup') is not None]
        if op.get('gateway'):                                        # 分支名跨网关重复时联定位（2026-10-09）
            gid = node(pj, op['gateway'])['id']
            br = [x for x in br if x.get('pid') == gid]
        if op.get('branch_id'):
            br = [x for x in br if x.get('id') == op['branch_id']]
        if len(br) != 1:
            raise SystemExit('分支「%s」匹配 %d 个（跨网关同名分支请加 "gateway": "<网关名>" 或 "branch_id"）'
                             % (op['branch'], len(br)))
        br = br[0]

        def _src(nm):
            if nm == 'start':
                st = next(x for x in pj['formTableList'] if x.get('nodeId') == 'start')
                return 'start', 'table', st['formTableCode'], pj.get('name') or '按钮触发'
            sn = node(pj, nm)
            sa = sn.get('attr') or {}
            return sn['id'], 'search', sa.get('linkFormTableCode') or sa.get('formTableCode'), nm
        sid, stype, scode, _sn = _src(op.get('src', 'start'))
        items, texts = [], []
        for fn, rule, val in op['items']:
            f = fields(scode)[fn]
            r2 = RULE[rule]
            q = {'rule': r2, 'ruleName': rule, 'name': fn, 'field': f['model'], 'columnName': fn, 'type': f['type']}   # gotchas #12：name 填字段名
            if isinstance(val, tuple) and val and val[0] == 'var':
                vid, vtype, vcode, vname = _src(val[1])
                vf = fields(vcode)[val[2]]
                q.update({'valueType': 2, 'valType': 'variable',
                          'val': {'variableValue': vf['model'], 'formTableCode': vcode, 'variableName': val[2],
                                  'formNodeType': vtype, 'formNodeId': vid, 'formNodeName': vname}})
                # 显示文字写明比较的表和字段（平台默认只显示「对象」两字，看不出比的是谁）
                texts.append('%s %s %s.%s' % (fn, rule, tname_of(vcode) or vname, val[2]))
            elif r2 in ('empty', 'not_empty'):
                q.update({'valueType': '1', 'val': '', 'valType': ''})
                texts.append('%s %s' % (fn, rule))
            else:
                q.update({'valueType': '1', 'val': str(val), 'valType': f['type']})   # gotchas #12：字面量写字符串
                texts.append('%s %s %s' % (fn, rule, val))
            items.append(q)
        a = br.setdefault('attr', {})
        grp = (a.get('conditionGroup') or [{}])[0]
        a['conditionGroup'] = [{'id': grp.get('id') or br['id'] + '1', 'matchType': (op.get('match', 'AND') if len(items) > 1 else ''),
                                'queryItems': items}]
        a['branchForm'] = {'formTableCode': scode, 'formNodeId': sid, 'formNodeType': stype}
        a['formTableCode'] = scode
        br['content'] = '[%s]' % ' 且 '.join(texts)
        LOG.append('set_branch %s/%s %s' % (op['flow'], op['branch'], br['content']))
    elif k == 'insert_delete':
        # 在 after 节点后插入「删除记录」，删 source（取多条）节点取到的那批记录
        if any(x['type'] == 'data_delete' and x.get('name') == op.get('name', '删除记录') for x in walk(pj)):
            LOG.append('SAME insert_delete %s' % op['flow']); continue
        af, src = node(pj, op['after']), node(pj, op['source'])
        sa = src.get('attr') or {}
        code, tname = sa.get('linkFormTableCode') or sa.get('formTableCode'), sa.get('linkFormTableName') or sa.get('formTableName')
        nid = 'task%s9' % src['id'][4:]
        dn = {'id': nid, 'name': op.get('name', '删除记录'), 'type': 'data_delete', 'status': -1,
              'attr': {'formType': 2, 'formModel': {}, 'formTableId': 'form_%s_%s' % (src['id'], code),
                       'formTableCode': code, 'formTableName': tname, 'formTableSourceTaskId': src['id'],
                       'expressionType': 'delegateExpression', 'expressionValue': '${deleteRecordDelegate}',
                       'level': (af.get('attr') or {}).get('level', '1'), 'formTableSourceNodeType': 'getMore',
                       'formTableSourceGetDataType': sa.get('getDataType', 1)},
              'configure': {}, 'addable': True, 'deletable': False, 'error': False,
              'content': '工作表 "%s"' % tname, 'pid': af['id'], 'errorContent': ''}
        child = af.get('childNode')
        if child:
            child['pid'] = nid
            dn['childNode'] = child
        af['childNode'] = dn
        LOG.append('insert_delete %s 删除「%s」取到的 %s' % (op['flow'], op['source'], tname))
    elif k == 'get_more_from':
        # 取多条改为「从取单条节点那条记录的关联字段取」（selectType=3，来源 search），并同步依赖它的 callActivity 数据对象。
        # ⚠️ callActivity 的同步口径（2026-10-09 生产管理实测补）：只匹配「subFormTableObject.nodeId 已经等于本节点」是不够的 ——
        # 生产管理「新增生产物料清单」里 callActivity 被 builder 接在流程里**第一个** from_="start" 的取多条上（取物料清单），
        # 而那段的行随后被 insert_delete 删掉；被转换的却是**紧随其后**的取多条（取BOM清单）→ 旧口径条件不成立、**静默跳过**，
        # 逐行子流程 0 行输入、流程 st=3 跑完却一条明细都不生成（五道闸门全绿）。现在三种命中：① nodeId 已指向本节点；
        # ② 本节点的 childNode 就是该 callActivity（紧随其后）；③ op 里显式写 "sync_sub": "<callActivity 节点名>"。
        # 三种都没命中且流程里确有 callActivity 时打 WARN（列出现有输入行），不再静默。
        n, sn = node(pj, op['node']), node(pj, op['src'])
        sa = sn.get('attr') or {}
        scode, sname = sa.get('linkFormTableCode') or sa.get('formTableCode'), sa.get('linkFormTableName') or sa.get('formTableName')
        f = fields(scode).get(op['link'])
        if not f:
            raise SystemExit('「%s」里没有关联字段「%s」' % (sname, op['link']))
        tcode = f['options'].get('sourceCode') if isinstance(f.get('options'), dict) else None
        tname = tname_of(tcode) or op.get('target_name')
        a = n.setdefault('attr', {})
        a.update({'selectType': 3, 'formType': 2, 'formTableId': 'form_%s_%s' % (sn['id'], scode), 'formTableCode': scode,
                  'formTableName': sname, 'formTableSourceTaskId': sn['id'], 'formTableSourceNodeType': 'search',
                  'linkFormTableField': f['model'], 'linkFormTableCode': tcode, 'linkFormTableName': tname,
                  'linkFormTableType': 1, 'expressionType': 'delegateExpression',
                  'expressionValue': '${getMoreRecordDelegate}', 'searchFieldGroup': [], 'noDataType': 1})
        for x in pj.get('formTableList') or []:
            if x.get('nodeId') == n['id']:
                x.update({'formTableId': 'form_%s_%s' % (n['id'], tcode), 'formTableCode': tcode, 'formTableName': tname,
                          'formTableMainCode': scode, 'selectType': 3, 'nodeType': 'getMore'})
                obj = dict(x)
        synced_ca = []
        for c in walk(pj):
            ca = c.get('attr') or {}
            if c['type'] != 'callActivity':
                continue
            cur_src = (ca.get('subFormTableObject') or {}).get('nodeId')
            adjacent = (n.get('childNode') or {}).get('id') == c['id']          # callActivity 紧随本节点
            named = bool(op.get('sync_sub')) and c.get('name') == op['sync_sub']  # 显式点名
            if cur_src != n['id'] and not adjacent and not named:
                continue
            if cur_src != n['id']:
                LOG.append('  callActivity「%s」输入行 %s → %s（%s）'
                           % (c.get('name'), (ca.get('subFormTableObject') or {}).get('nodeName'),
                              n.get('name'), '紧随本节点' if adjacent else '显式点名'))
            # 四个键必须一起改齐：formTableSourceTaskId / formTableId / subFormTableObject.{nodeId,nodeName,formTableId,...}
            # ⚠️ 只改 5 个表码键（旧写法）在「本来已经指对」时可跑，但本节点接管另一个 callActivity 时
            # nodeId/nodeName/formTableSourceTaskId 不跟着改 → 三键互相矛盾、check_node_contract 直接判不合格（2026-10-09 实测）。
            so = dict(ca.get('subFormTableObject') or {})
            so.update({k2: obj[k2] for k2 in ('formTableId', 'formTableCode', 'formTableName',
                                              'formTableMainCode', 'selectType', 'getDataType', 'level')
                       if obj.get(k2) is not None})
            so.update({'nodeId': n['id'], 'nodeName': n.get('name'), 'nodeType': 'getMore',
                       'isSubStart': True, 'formTableType': so.get('formTableType', 1)})
            ca['subFormTableObject'] = so
            ca['formTableId'] = obj['formTableId']
            ca['formTableSourceTaskId'] = n['id']
            # 被调子流程的输入行（isSubStart 条目 + attr.subFormTableObject）同步成新表 ——
            # postbuild_subfix 只查登记在不在、不比表码，这里不改子流程就一直指着旧表（2026-09-28 实测）
            sid_ = str(ca.get('customProcessId') or '')
            if sid_:
                sr = next((v for v in DIRTY.values() if str(v['id']) == sid_), None) or dict(full(sid_))
                sr.setdefault('_pj', json.loads(sr['processJson']))
                spj = sr['_pj']
                for e in spj.get('formTableList') or []:
                    if e.get('isSubStart'):
                        e.update({'formTableCode': tcode, 'formTableName': tname, 'formTableMainCode': scode,
                                  'formTableId': 'form_%s_%s' % (n['id'], tcode)})
                        spj.setdefault('attr', {})['subFormTableObject'] = dict(e)
                        spj['attr'].update({'formTableId': e['formTableId'], 'formTableCode': tcode, 'formTableName': tname})
                DIRTY[sr['processName']] = sr
                LOG.append('  子流程「%s」输入行同步为 %s' % (sr['processName'], tname))
            synced_ca.append(c.get('name'))
        if not synced_ca:
            cas = [c for c in walk(pj) if c.get('type') == 'callActivity']
            if cas:
                LOG.append('WARN get_more_from %s/%s 未同步任何 callActivity —— 流程里有 %d 个，当前输入行：%s。'
                           '确认该「取多条」是不是子流程的数据源：是 → 补 "sync_sub":"<callActivity节点名>" 再跑一次；'
                           '不是 → 忽略本告警'
                           % (op['flow'], op['node'], len(cas),
                              '；'.join('%s ← %s' % (c.get('name'), ((c.get('attr') or {}).get('subFormTableObject') or {}).get('nodeName') or '未登记') for c in cas)))
        n['content'] = '关联表 "%s"' % tname
        LOG.append('get_more_from %s/%s ← %s.%s' % (op['flow'], op['node'], sname, op['link']))
    elif k == 'get_one_var':
        # 取单条按「记录id 等于 流程参数」查（子流程收父流程传进来的记录 id）
        n = node(pj, op['node'])
        a = n.setdefault('attr', {})
        a['selectType'] = 1
        a['searchFieldGroup'] = [{'matchType': '', 'id': n['id'] + '1', 'queryItems': [
            {'val': {'variableName': op['var'], 'formNodeType': 'variable', 'variableValue': op['var']},
             'field': '_id', 'valType': 'variable', 'valueType': 4, 'name': '记录id', 'rule': 'eq', 'ruleName': '等于',
             'type': 'input', 'columnName': '记录id'}]}]
        LOG.append('get_one_var %s/%s 记录id = 参数 %s' % (op['flow'], op['node'], op['var']))
    elif k == 'get_one_cond':
        # 取单条改为「从工作表按条件取」（selectType=1）：cond=[(目标表字段, '等于', ('row'|'start', 本行字段))]
        n = node(pj, op['node'])
        a = n.setdefault('attr', {})
        tcode = a.get('linkFormTableCode') if a.get('selectType') == 3 and a.get('linkFormTableCode') else a.get('formTableCode')
        tname = tname_of(tcode) or a.get('linkFormTableName') or a.get('formTableName')
        st = next(x for x in pj['formTableList'] if x.get('isSubStart') or x.get('nodeId') == 'start')
        items = []
        for tf, rule, (_w, rf) in op['cond']:
            rfm = fields(st['formTableCode'])[rf]
            # ⚠️「记录id」是特例：`_id` 不是控件、不在 fields() 里（**按名字解析**这条路一律取不到它），
            #    但**落库形态**平台是认的 —— gotchas #45『查询入库单』就是 `_id` 配 link-record 变量、
            #    线上照跑。没有本特例时「从工作表获取单条，取<某条关联>的那条」这档根本表达不出来，
            #    只能手写 JSON —— 而手写正是 2026-10-08 销售管理把这一档误做成 selectType=3
            #    （「从关联字段获取」）的来源。条目形态与上面 get_one_var 的 `_id` 条目一致。
            if tf in ('记录id', '_id'):
                tfm, tty, tfname = '_id', 'input', '记录id'
            else:
                tfm, tty, tfname = fields(tcode)[tf]['model'], fields(tcode)[tf]['type'], tf
            items.append({'val': {'formNodeId': st['nodeId'], 'formNodeName': st.get('nodeName') or '子流程',
                                  'variableName': rf, 'formNodeType': 'search' if st.get('isSubStart') else 'table',
                                  'variableValue': rfm['model'], 'formTableCode': st['formTableCode']},
                          'field': tfm, 'valType': 'variable', 'valueType': 2, 'name': tfname,
                          'rule': {'等于': 'eq'}[rule], 'ruleName': rule, 'type': tty, 'columnName': tfname})
        for x2 in ('linkFormTableField', 'linkFormTableCode', 'linkFormTableName', 'linkFormTableType', 'formTableSourceGetDataType'):
            a.pop(x2, None)
        a.update({'selectType': 1, 'formTableCode': tcode, 'formTableName': tname, 'formTableSourceTaskId': '',
                  'formTableId': 'form_%s_%s' % (n['id'], tcode), 'searchFieldGroup': [{'matchType': '', 'id': n['id'] + '1', 'queryItems': items}],
                  'expressionType': 'delegateExpression', 'expressionValue': '${getOneRecordDelegate}', 'noDataType': 1})
        n['content'] = '工作表 "%s"' % tname
        for x in pj.get('formTableList') or []:
            if x.get('nodeId') == n['id']:
                x.update({'formTableCode': tcode, 'formTableName': tname, 'formTableMainCode': tcode, 'selectType': 1,
                          'formTableId': 'form_%s_%s' % (n['id'], tcode), 'nodeType': 'search'})
        LOG.append('get_one_cond %s/%s %s' % (op['flow'], op['node'], op['cond']))
    elif k == 'swap':
        # 交换相邻两个节点（a 在前、b 紧跟其后）→ b 在前
        a_, b_ = node(pj, op['a']), node(pj, op['b'])
        if a_.get('childNode') is not b_:
            if b_.get('childNode') is a_:
                LOG.append('SAME swap %s' % op['flow']); continue
            raise SystemExit('swap：「%s」后面不是「%s」' % (op['a'], op['b']))
        parent = next(x for x in walk(pj) if x.get('childNode') is a_) if pj.get('childNode') is not a_ else pj
        rest = b_.get('childNode')
        parent['childNode'] = b_; b_['pid'] = parent['id']
        b_['childNode'] = a_; a_['pid'] = b_['id']
        if rest:
            a_['childNode'] = rest; rest['pid'] = a_['id']
        else:
            a_.pop('childNode', None)
        LOG.append('swap %s：「%s」移到「%s」前' % (op['flow'], op['b'], op['a']))
    elif k == 'set_fun':
        # 更新节点的某字段写成「函数表达式」取值（文本拼接，如 {{原材料.所属产品名称}}、{{本行.产品名称}}）
        # op: {'flow','node': 更新节点名, 'field': 目标字段中文名, 'expr': '{表.字段@来源}、{表.字段@来源}'}，来源=取单条节点名 / row（子流程本行）/ start
        import hashlib, urllib.parse
        un = node(pj, op['node'])
        ua = un.setdefault('attr', {})
        tcode = ua.get('formTableCode')
        tf = fields(tcode)[op['field']]
        ctx, text = {}, op['expr']
        for tok in re.findall(r'\{(.+?)\}', op['expr']):
            tb, rest = tok.split('.', 1)
            fn, src = rest.split('@', 1)
            if src in ('row', 'start'):
                st = next(x for x in pj['formTableList'] if x.get('isSubStart') or x.get('nodeId') == 'start')
                nid, nname, ntype, ncode = st['nodeId'], (pj.get('name') or st.get('nodeName')) if src == 'start' else '子流程', \
                    ('search' if st.get('isSubStart') else 'table'), st['formTableCode']
            else:
                sn = node(pj, src)
                sa = sn.get('attr') or {}
                nid, nname, ntype, ncode = sn['id'], src, 'search', sa.get('linkFormTableCode') or sa.get('formTableCode')
            fm = fields(ncode)[fn]['model']
            ref = {'field': fm, 'formTableCode': ncode, 'formNodeId': nid, 'formNodeType': ntype, 'variableValue': fm,
                   'formNodeName': nname, 'tableText': tb, 'fieldText': fn}
            h = hashlib.md5(json.dumps(ref, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
            ctx[h] = urllib.parse.quote(json.dumps(ref, ensure_ascii=False, separators=(',', ':')), safe=':,')
            text = text.replace('{%s}' % tok, '{{%s.%s}}' % (h, fm), 1)
        if un['type'] == 'data_add':            # 新增记录：写在 formModel[model]
            ua.setdefault('formModel', {})[tf['model']] = {'funText': text, 'funContext': ctx}
            LOG.append('set_fun %s/%s.%s = %s' % (op['flow'], op['node'], op['field'], op['expr']))
            DIRTY[op['flow']] = r
            continue
        ufs = ua.setdefault('updateFields', [])
        ent = next((u for u in ufs if u.get('field') == tf['model']), None)
        if ent is None:
            ent = {'optType': '1', 'field': tf['model'], 'id': '%s_%d' % (un['id'], len(ufs)), 'type': tf['type'],
                   'fieldValue': '', 'fieldType': tf['type']}
            ufs.append(ent)
        for x2 in ('valueType', 'valType'):
            ent.pop(x2, None)
        ent['val'] = {'funText': text, 'funContext': ctx}
        LOG.append('set_fun %s/%s.%s = %s' % (op['flow'], op['node'], op['field'], op['expr']))
    elif k == 'rename':
        if r['processName'] == op['to']:
            LOG.append('SAME rename %s' % op['to']); continue
        r['processName'] = op['to']
        LOG.append('rename %s → %s' % (op['flow'], op['to']))
    else:
        raise SystemExit('未知 op %s' % k)
    DIRTY[op['flow']] = r

for x in LOG:
    print(x)
if A.dry_run:
    print('DRY: 待保存 %d 条' % len(DIRTY)); sys.exit(0)
fail = 0
for name, r in DIRTY.items():
    cfg = {'processName': r['processName'], 'processKey': r['processKey'], 'processType': r.get('processType') or 'oa',
           'lowAppId': AID, 'tenantId': TID, 'startType': r['startType'],
           'customProcessId': str(r['id']) if r['startType'] == 'subEvent' else (r.get('customProcessId') or ''),
           'triggerOtherProcess': r.get('triggerOtherProcess') or '0'}
    if r['startType'] == 'subEvent':
        cfg['processKey'] = 'process%s' % r['id']            # gotchas #47：子流程定义 key = process<DBid>
    # 保存父流程时后端会顺带改子流程记录（updateCount 变），版本号必须保存前现取
    uc = get('/act/process/extActProcess/queryById', id=r['id'])['result'].get('updateCount')
    s = save_flow(API, T, cfg, r['_pj'], flow_id=r['id'], update_count=uc)
    if not s.get('success'):
        print('FAIL save %s %s' % (name, s.get('message'))); fail += 1; continue
    d = deploy_flow(API, T, r['id'], tenant_id=TID, low_app_id=AID)
    print('%s %s' % ('OK' if (d or {}).get('success') else 'FAIL deploy', name)); fail += 0 if (d or {}).get('success') else 1
print('%s:surgery 保存 %d 条 / 失败 %d' % ('OK' if not fail else 'FAIL', len(DIRTY), fail))
sys.exit(2 if fail else 0)
