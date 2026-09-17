# -*- coding: utf-8 -*-
"""定时扫描→逐行站内系统消息 简流【一键运行器】2026-09-09（整链双回读实证，模板固化）

需求类：每天早上X点定时 → 查某工作表「日期字段=当天」的记录 → 逐条给该行
select-user 字段(如医生/客户)发站内系统消息提醒。
结构：subEvent子流程(message_system 逐行, toUserIds var search引用主链getMore行)
     → 发布 → 主流程 timerEvent → function(+0D 计算当天) → data_get_more(日期eq当天)
     → callActivity(子流程 isMulti 逐行)。含防呆、save、deploy、双回读、耗时统计。

用法（Windows bash, 单命令）：
  PYTHONIOENCODING=utf-8 py -3 scripts/timer_notify_runner.py \\
      --tenant 1008 --app 2095343423447621634 --form 预约表 \\
      --date 就诊日期 --to 医生 \\
      --title 今日就诊提醒 --body 您今天有预约就诊安排，请提前做好准备并及时接诊。 \\
      --at 07:00 [--main 流程名 --sub 子流程名 --begin "YYYY-MM-DD HH:MM" --cycle 每天]
凭证：自动读 memory reference_jeecgboot_credentials.md（唯一凭证源）；可用 --api/--token 覆盖。
--date/--to 可省：表内唯一 date / select-user 字段时自动选；有多个则报错列出候选。
"""
import argparse, os, re, sys, time, json, datetime, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from miniflow_creator import fetch_app_forms, build_process_json, save_flow, deploy_flow, query_flow

CRED_FILE = r'C:\Users\25067\.claude\projects\C--Users-25067\memory\reference_jeecgboot_credentials.md'
CYCLE_MAP = {'每分钟': '1', '每小时': '2', '每天': '3', '每月1号': '4', '每周三': '5',
             '周一到周五': '6', '每年12月31日': '7', '自定义': 'custom'}

def load_creds():
    txt = open(CRED_FILE, encoding='utf-8').read()
    api = re.search(r'\*\*API Base\*\*：`([^`]+)`', txt).group(1)
    tok = re.search(r'\*\*X-Access-Token\*\*：`([^`]+)`', txt).group(1)
    return api, tok

def get_fields(api, tok, code, tenant):
    raw = requests.get(api + '/desform/api/fields/' + code, params={'group': 'true'},
                       headers={'X-Access-Token': tok, 'X-Tenant-Id': str(tenant)}, timeout=30).json()
    r = raw.get('result') if isinstance(raw, dict) else raw
    if isinstance(r, dict):
        r = r.get('fields') or r.get('list') or []
    return [f for f in (r or []) if isinstance(f, dict)]

def pick(flds, kw, want, role):
    cand = [f for f in flds if f.get('type') in want]
    if kw:
        cand = [f for f in cand if kw in (f.get('name') or '')]
    if not cand:
        raise SystemExit(f'未找到{role}字段(kw={kw}): ' + json.dumps(
            [{'n': f.get('name'), 'm': f.get('model'), 't': f.get('type')} for f in flds], ensure_ascii=False))
    if len(cand) > 1:
        raise SystemExit(f'{role}字段候选多个，请用 --{"date" if role == "日期" else "to"} 指定: ' +
                         json.dumps([f.get('name') for f in cand], ensure_ascii=False))
    return cand[0]

def main():
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument('--tenant', required=True)
    p.add_argument('--app', required=True)
    p.add_argument('--form', required=True, help='表单中文名（含匹配）')
    p.add_argument('--date', default='', help='日期字段中文名；省=表内唯一 date 字段')
    p.add_argument('--to', default='', help='收件人 select-user 字段中文名；省=表内唯一')
    p.add_argument('--title', required=True)
    p.add_argument('--body', required=True)
    p.add_argument('--at', default='07:00', help='每天几点 HH:MM，默认 07:00')
    p.add_argument('--main', default='', help='主流程名；省=表单名+当天提醒')
    p.add_argument('--sub', default='', help='子流程名；省=主流程名+通知子流程')
    p.add_argument('--begin', default='', help="开始 'YYYY-MM-DD HH:MM'；省=下一次 --at 时刻")
    p.add_argument('--end', default='', help="结束 'YYYY-MM-DD HH:MM'；省=不设结束")
    p.add_argument('--cycle', default='每天', choices=list(CYCLE_MAP))
    p.add_argument('--api', default='')
    p.add_argument('--token', default='')
    a = p.parse_args()

    t0 = time.time()
    API, TOKEN = (a.api or load_creds()[0]), (a.token or load_creds()[1])
    TENANT, APP = int(a.tenant), a.app
    h = {'X-Access-Token': TOKEN, 'X-Tenant-Id': str(TENANT), 'X-Low-App-ID': str(APP)}
    app = None
    for x in fetch_app_forms(API, TOKEN, TENANT):
        if str(x.get('id')) == str(APP) or (x.get('name') or '') == APP:
            app = x; break
    assert app, f'应用不存在(可用名字或 id 传 --app): {a.app}'
    appid = str(app['id'])
    forms = app.get('forms') or []
    hits = [f for f in forms if a.form in (f.get('name') or '')]
    if not hits:
        raise SystemExit('未找到表单: ' + json.dumps([f.get('name') for f in forms], ensure_ascii=False))
    CODE, NAME = hits[0]['code'], hits[0]['name']
    flds = get_fields(API, TOKEN, CODE, TENANT)
    fd = pick(flds, a.date, ('date', 'datetime'), '日期')
    fu = pick(flds, a.to, ('select-user',), '收件人')
    F_DATE, DATE_COL = fd['model'], fd['name']
    F_CUST, TO_COL = fu['model'], fu['name']
    FT = 'datetime' if fd['type'] == 'datetime' else 'date'
    MAIN = a.main or (NAME + '当天提醒')
    SUB = a.sub or (MAIN + '通知子流程')
    now = datetime.datetime.now()
    if a.begin:
        BEGIN = a.begin
    else:
        hh, mm = map(int, a.at.split(':'))
        nxt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if nxt <= now:
            nxt += datetime.timedelta(days=1)
        BEGIN = nxt.strftime('%Y-%m-%d %H:%M')
    print(f'发现: 表={NAME}({CODE}) | {DATE_COL}={F_DATE}({fd["type"]}) | {TO_COL}={F_CUST} | '
          f'流程={MAIN} | 开始={BEGIN} {a.cycle}({CYCLE_MAP[a.cycle]}) | 耗时基线见尾部')
    h = {'X-Access-Token': TOKEN, 'X-Tenant-Id': str(TENANT), 'X-Low-App-ID': appid}

    rr = requests.get(API + '/act/process/extActProcess/list', params={'processName': MAIN, 'pageSize': 20},
                      headers=h, timeout=30).json()
    recs = (rr.get('result') or {}).get('records') or (rr.get('result') or [])
    if isinstance(recs, list) and recs:
        print(f'同名主流程已存在，中止(删旧用 DELETE extActProcess/delete?id=): {MAIN} {[x.get("id") for x in recs]}')
        sys.exit(3)

    ts = int(time.time() * 1000); sub_ts = ts + 1
    op_id, gm_id = f'task{ts}001', f'task{ts}002'

    # ---------- A. 子流程（先建后发；收件人 var 引用父 getMore 行 = search 形态） ----------
    var_entry = 'var.' + json.dumps({'formTableCode': CODE, 'formTableId': f'form_{gm_id}_{CODE}',
                                     'nodeId': gm_id, 'nodeType': 'search',
                                     'field': F_CUST, 'fieldType': 'select-user'}, ensure_ascii=False)
    sub_msg = {'id': f'task{sub_ts}001', 'name': '发送提醒消息', 'type': 'message_system', 'status': -1,
               'attr': {'type': 'system', 'description': '', 'title': a.title,
                        'expressionType': 'delegateExpression', 'expressionValue': '${messageDelegate}',
                        'templateContext': a.body, 'receiveType': 'user',
                        'toUserIds': [var_entry], 'toUsers': [], 'toUserExpression': '',
                        'toUserNames': [TO_COL], 'level': '1', 'jsonContext': {}},
               'privileges': [], 'configure': {}, 'childNode': None,
               'toUserIds': [var_entry], 'toUserNames': [TO_COL],
               'addable': True, 'deletable': False, 'error': False, 'errorContent': '',
               'content': f'通知人:{TO_COL}', 'pid': 'start'}
    search_obj = {'nodeName': '查询今日记录', 'nodeTypeMain': 'getMore', 'level': '2', 'formTableType': 1,
                  'getDataType': 1, 'formTableMainCode': CODE, 'nodeType': 'search', 'formTableCode': CODE,
                  'formTableName': NAME, 'isSubStart': True, 'selectType': 1,
                  'formTableId': f'form_{gm_id}_{CODE}', 'nodeId': gm_id}
    sub_pj = {'initiator': 'applyUserId', 'startNodeContent': None, 'timeType': 'timeDate', 'type': 'start',
              'error': False, 'entTime': None,
              'eventListeners': [{'allowDel': False, 'listenerType': 'javaClass', 'listenerName': '任务创建全局监听',
                                  'value': 'org.jeecg.modules.listener.tasktip.TaskCreateGlobalListener'}],
              'subFlowSourceInfo': [],
              'taskListenerData': [{'listenerType': 'class', 'listenerName': '发起人节点跳过监听', 'eventType': 'create',
                                    'value': 'org.jeecg.modules.extbpm.listener.task.TaskCreatedAutoSubmitListener'}],
              'createStartNode': False,
              'formTableList': [dict(search_obj),
                                {'formTableId': 'variable', 'nodeId': 'processVariable', 'formTableCode': '_variable_',
                                 'nodeName': '流程参数', 'formTableName': '流程参数', 'nodeType': 'variable'}],
              'id': 'start',
              'attr': {'endDate': None, 'formTableCode': CODE, 'startCondition': [], 'formTableName': NAME,
                       'hourValues': [], 'subFormTableObject': dict(search_obj),
                       'formTableId': f'form_{gm_id}_{CODE}', 'hourType': 1, 'endDateStr': None,
                       'beginDateStr': None, 'dayValue': 1, 'formType': 2, 'conditionFields': [],
                       'triggerField': None, 'titleField': None, 'plusDate': None, 'inputParams': [],
                       'startType': 'subEvent', 'executionTime': None, 'timeCycleName': None,
                       'startEventType': 'add|update', 'plusDateUnit': 3, 'dayValues': [],
                       'formTableSourceId': None, 'signalEventName': None},
              'executeListeners': [
                  {'allowDel': False, 'listenerType': 'javaClass', 'listenerName': '平台通用流程结束监听',
                   'id': '402880e54803a496014805e5d9190012', 'eventType': 'end',
                   'value': 'org.jeecg.modules.extbpm.listener.execution.ProcessEndListener'},
                  {'allowDel': False, 'listenerType': 'javaClass', 'listenerName': '流程结束删除redis数据',
                   'id': '506880e54803a496014805e5d9190012', 'eventType': 'end',
                   'value': 'org.jeecg.modules.minides.listener.ProcessEndRemoveRedisListener'}],
              'hasVariableList': False, 'startType': 'subEvent', 'startTaskId': f'task{sub_ts}000',
              'addable': True, 'deletable': False, 'content': '发起流程',
              'error': False, 'errorContent': '', 'status': -1, 'childNode': sub_msg}
    r1 = save_flow(API, TOKEN, {'processName': SUB, 'processKey': f'process{sub_ts}', 'processType': 'oa',
                                'lowAppId': appid, 'tenantId': str(TENANT), 'startType': 'subEvent'}, sub_pj)
    assert r1.get('success'), r1
    sub_id = r1['result']['id']; print('子流程 sub_id =', sub_id)
    uc = query_flow(API, TOKEN, flow_id=sub_id)['updateCount']
    p1 = requests.post(API + '/act/designer/miniDesFlow/api/saveFlow',
                       data={'updateCount': uc, 'processJson': json.dumps(sub_pj, ensure_ascii=False),
                             'processName': SUB, 'processKey': f'process{sub_id}', 'processType': 'oa',
                             'id': sub_id, 'customProcessId': sub_id, 'lowAppId': appid, 'startType': 'subEvent'},
                       headers={'X-Access-Token': TOKEN, 'X-Tenant-Id': str(TENANT),
                                'Content-Type': 'application/x-www-form-urlencoded'}, timeout=60).json()
    assert p1.get('success'), p1
    p2 = requests.put(API + '/act/process/extActProcess/deployProcess', json={'id': sub_id}, headers=h, timeout=60).json()
    assert p2.get('success'), p2
    print('子流程发布完成')

    # ---------- B. 主流程（timerEvent → function 当天 → getMore 日期eq当天 → callActivity） ----------
    var_cond = {'variableValue': 'result', 'formTableCode': 'function-date', 'variableName': '结果',
                'fieldType': FT, 'formNodeType': 'function', 'formNodeId': op_id,
                'formNodeName': '计算当天日期', 'operationMode': 'cache', 'decimals': 2}
    config = {'processName': MAIN, 'processKey': f'process{ts}', 'processType': 'oa',
              'lowAppId': appid, 'tenantId': str(TENANT), 'startType': 'timerEvent',
              'beginDateStr': BEGIN, 'timeCycleName': a.cycle,
              'startTaskId': f'task{ts}000',
              'nodes': [
                  {'type': 'get_more', 'id': gm_id, 'name': '查询今日记录', 'getType': 1,
                   'formTableCode': CODE, 'formTableName': NAME,
                   'conditions': [
                       {'rule': 'eq', 'ruleName': '等于', 'valueType': 3, 'val': var_cond, 'name': None,
                        'field': F_DATE, 'columnName': DATE_COL, 'type': FT, 'valType': 'variable'}],
                   'fetchMode': 'cache', 'limitCount': 0},
              ]}
    pj = build_process_json(config)

    def walk(n, acc=None):
        acc = [] if acc is None else acc
        if not n:
            return acc
        acc.append(n)
        for ch in [n.get('childNode')] + list(n.get('conditionNodes') or []):
            walk(ch, acc)
        return acc

    op = {'id': op_id, 'name': '计算当天日期', 'type': 'function', 'status': -1, 'configure': {},
          'attr': {'funType': 'date', 'funContext': {}, 'funText': '+0D',
                   'expressionType': 'delegateExpression', 'expressionValue': '${functionDelegate}',
                   'dateFieldVal': {'formNodeType': 'system', 'variableValue': 'nowDate', 'variableName': '当前日期'},
                   'dateFunctionFormat': {'argument': FT, 'result': FT, 'end': '2', 'out': 'd'},
                   'operationMode': 'cache', 'decimals': 2},
          'addable': True, 'deletable': False, 'error': False, 'errorContent': '', 'content': '当前日期'}
    op['childNode'] = pj.get('childNode'); op['pid'] = 'start'
    if pj.get('childNode'):
        pj['childNode']['pid'] = op_id
    pj['childNode'] = op
    pj.setdefault('formTableList', []).insert(0, {'formTableId': f'form_{op_id}_function-date', 'nodeId': op_id,
        'nodeName': '计算当天日期', 'nodeType': 'function', 'formTableCode': 'function-date',
        'formTableName': '计算当天日期', 'operationMode': 'cache', 'decimals': 2})

    nodes = {n['id']: n for n in walk(pj['childNode'])}
    gm = nodes[gm_id]
    gm['attr'].setdefault('searchFieldGroup', [{'id': f'{ts}9', 'matchType': '', 'queryItems': []}])
    gm['attr']['searchFieldGroup'][0]['queryItems'] = [
        {'rule': 'eq', 'ruleName': '等于', 'valueType': 3, 'val': var_cond, 'name': None,
         'field': F_DATE, 'columnName': DATE_COL, 'type': FT, 'valType': 'variable'}]
    gm['attr']['searchContent'] = f'[{DATE_COL} 等于 计算当天日期]'
    gm['attr'].setdefault('getDataType', 1); gm['attr'].setdefault('noDataType', 1)
    gm['attr']['formTableId'] = f'form_{gm_id}_{CODE}'
    gm['attr'].setdefault('selectType', 1); gm['attr'].setdefault('formType', 2)
    gm['attr'].setdefault('expressionType', 'delegateExpression')
    gm['attr'].setdefault('expressionValue', '${getMoreRecordDelegate}')
    gm.pop('conditions', None)
    ftl_gm = next((e for e in pj['formTableList'] if e.get('nodeId') == gm_id), None)
    if ftl_gm is None:
        ftl_gm = {'formTableId': f'form_{gm_id}_{CODE}', 'nodeId': gm_id, 'nodeName': '查询今日记录',
                  'nodeType': 'getMore', 'formTableCode': CODE, 'formTableName': NAME, 'formTableMainCode': CODE,
                  'selectType': 1, 'getDataType': 1}
        pj['formTableList'].insert(1, ftl_gm)
    ftl_gm['isSubStart'] = True

    act_id = f'Activity{ts}'
    act = {'id': act_id, 'name': '子流程', 'type': 'callActivity', 'status': -1,
           'attr': {'approvalEnabled': True, 'calledElement': f'process{sub_id}', 'formTableName': None,
                    'formTableSourceTaskId': gm_id, 'formTableCode': None, 'processName': SUB,
                    'processId': sub_id, 'customProcessId': sub_id, 'loopCardinality': None, 'ratio': 0.5,
                    'isSequential': False, 'isMulti': True, 'subFormTableObject': dict(ftl_gm, isSubStart=True),
                    'collection': '${flowUtil.stringToList(assigneeUserIdList)}', 'elementVariable': 'assigneeUserId',
                    'completionCondition': None, 'variableList': [], 'level': '3',
                    'formTableId': f'form_{gm_id}_{CODE}'},
           'approvalMode': 1,
           'listenerData': [{'id': '502880e54853a496014805e5d9190012', 'eventType': 'start',
                             'listenerType': 'javaClass', 'listenerName': '子流程流程变量',
                             'value': 'org.jeecg.modules.extbpm.process.adapter.delegate.MiniCallActivityListener',
                             'allowDel': False}],
           'inVariableModels': [{'source': 'applyUserId', 'target': 'applyUserId'},
                                {'source': 'dataId', 'target': 'dataId'},
                                {'source': 'JG_LOCAL_PROCESS_ID', 'target': 'JG_SUB_MAIN_PROCESS_ID'},
                                {'source': 'handleDataId', 'target': 'handleDataId'}],
           'childNode': None, 'configure': {},
           'addable': True, 'deletable': False, 'error': False, 'errorContent': '',
           'content': f'执行流程:{SUB}', 'pid': gm_id}
    gm['childNode'] = act

    chain = []; cur = pj.get('childNode')
    while cur:
        chain.append(cur); cur = cur.get('childNode')
    for i, n in enumerate(chain, 1):
        n['attr']['level'] = str(i)
    ra = pj['attr']
    ra['beginDateStr'] = BEGIN; ra['timeCycleName'] = a.cycle; ra['timeCycle'] = CYCLE_MAP[a.cycle]
    if a.end:
        ra['endDateStr'] = a.end
    ra.setdefault('conditionFields', []); ra.setdefault('startCondition', [])

    mcfg = {'processName': MAIN, 'processKey': f'process{ts}', 'processType': 'oa',
            'lowAppId': appid, 'tenantId': str(TENANT), 'startType': 'timerEvent'}
    r2 = save_flow(API, TOKEN, mcfg, pj)
    assert r2.get('success'), r2
    main_id = r2['result']['id']; print('主流程 main_id =', main_id)
    d2 = deploy_flow(API, TOKEN, main_id)
    assert isinstance(d2, dict) and d2.get('success'), d2
    print('主流程发布完成')

    # ---------- C. 双回读断言 ----------
    rp = query_flow(API, TOKEN, flow_id=main_id)['processJson']
    ch = [n['type'] for n in walk(rp['childNode'])]
    assert ch == ['function', 'data_get_more', 'callActivity'], '主链不符: ' + str(ch)
    fob = [n for n in walk(rp['childNode']) if n['type'] == 'function'][0]['attr']
    gmb = [n for n in walk(rp['childNode']) if n['type'] == 'data_get_more'][0]['attr']
    ab = [n for n in walk(rp['childNode']) if n['type'] == 'callActivity'][0]['attr']
    assert fob['funText'] == '+0D' and fob['level'] == '1', 'function 不符'
    qi = (gmb.get('searchFieldGroup') or [{}])[0].get('queryItems') or []
    assert qi and qi[0]['field'] == F_DATE and qi[0]['rule'] == 'eq' and qi[0]['valType'] == 'variable', \
        'getMore 条件不符: ' + json.dumps(qi, ensure_ascii=False)
    assert ab['customProcessId'] == sub_id and ab['isMulti'] is True, 'callActivity 不符'
    ra2 = rp['attr']
    assert ra2.get('timeCycle') == CYCLE_MAP[a.cycle] and ra2.get('beginDateStr') == BEGIN, '调度不符'
    rs = query_flow(API, TOKEN, flow_id=sub_id)['processJson']
    assert rs.get('startType') == 'subEvent' and rs['attr'].get('startType') == 'subEvent', '子流程 startType 缺失'
    ms = walk(rs['childNode'])[0]
    assert ms['type'] == 'message_system' and ms['attr']['toUserIds'] == [var_entry], '子流程消息不符'
    print(f"✅ 双回读通过: 主={MAIN}({main_id}) 子={SUB}({sub_id}) | {BEGIN} 起{a.cycle} | "
          f"查[{NAME}]{DATE_COL}=当天 → 逐行消息给{TO_COL} | 总耗时 {time.time() - t0:.1f}s")

if __name__ == '__main__':
    main()
