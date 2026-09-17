# -*- coding: utf-8 -*-
"""定时触发简流【统一一键运行器】2026-09-09（整链均来自当日双回读/实证契约，模板固化）

5 个子命令，覆盖截图 12 条定时触发题集：

  shell    定时壳：#4-7 —— 只配调度无动作。
  announce 定时公告：#2 —— 向全员/指定用户发系统消息；--once=当天23:59截断仅一次（组合I 实证）。
  scan     定时扫描 → 批量更新/批量逐条新增 + 通知：#1 #3 #8 #10。
  check    定时检查有无记录 → 有/无分支动作：#9b #11（get_one emptyAction=3 + databranch，#63 实证）。
  datefield 按日期字段触发壳（dateFieldEvent）——监控工作表某日期字段，每条记录到期时刻各触发一次，
            executeType=1 到期当天 at 时刻执行；2/3 配 --plus/--plus-unit 提前/延后（2026-09-09 建流实证）。
            --conds 触发条件(记录级过滤, attr.startCondition)全字段族全规则 DSL，见用法示例与 cmd_datefield 注释。

条件 DSL（--conds，逗号分隔）：
  字段=eq:值 / 字段=ge:123 ...                    静态值（值按字段：radio/select 写选项文案）
  字段=le_fn:-24H / ge_fn:+1D / eq_fn:today|tomorrow   动态时刻函数（D=天,H=小时）
  字段A=le_field:字段B                             同表两行字段比较（#63 形态）
动作：
  --update 状态=已超时                 批量改（E2 契约）
  --add 补货清单:商品=商品,状态=固定:待补货,日期=now   批量逐条新增（addDataType=2，#63）
  --to-field 医生 --title .. --body ..   逐行站内消息→callActivity 子流程（#57 实证）
  --mail-to 采购员 ...                跑完一封邮件（message_email）

用法示例：
  shell:    py -3 scripts/timer_job_runner.py shell   --tenant 1008 --app <app> --begin "2026-09-10 08:00" --end "2026-09-30 18:00" --cycle 每天 [--name 定时触发流程-每天]
  announce: py -3 scripts/timer_job_runner.py announce --tenant 1008 --app <app> --begin "2026-09-10 15:00" --once --title 公告 --body 正文
  scan:     py -3 scripts/timer_job_runner.py scan     --tenant 1008 --app <app> --scan 订单表 --conds "支付状态=eq:未付款,下单时间=le_fn:-24H" --update 支付状态=已超时 --to-field 客户 --title 超时提醒 --body 订单超24小时未支付 --begin "2026-09-10 09:00" --end "2026-12-31 18:00"
  check:    py -3 scripts/timer_job_runner.py check    --tenant 1008 --app <app> --scan 预约表 --conds "就诊日期=ge_fn:+1D" --if-empty "msg:user:秦风" --title 明日无预约 --body 明天暂无预约 --begin "2026-09-11 22:00" --cycle 周一到周五
  datefield: py -3 scripts/timer_job_runner.py datefield --tenant 1008 --app 应用2 --table 预约表 --field 预约日期 --at 15:00
             # 预约日期当天15:00执行、每条记录一次（--execute 1 默认）
             # 到期前1天09:00并每年重复: --execute 2 --plus 1 --plus-unit 天 --at 09:00 --cycle-type 2
             # --at 即 executionTime(HH:MM)；"下午三点"=15:00；--execute 1当天/2前/3后；--cycle-type 1不重复/2每年/3每月/4每周
             # 带触发条件(12 行全且示例, 全字段族): --name 预约表按日期触发-多条件
             #   --conds "预约日期=eq:今天,患者=eq:张三,医生=eq:管理员,状态=eq:待确认,描述=like:复诊,附件=not_empty:,
             #            数字=ge:10,整数=eq:5,金额=gt:100,时间=eq:18:00,下拉选择框=eq:选项A,多选框组=in:选项A|选项B"
             #   （datefield --conds 全规则 DSL 2026-09-10: eq/ne/gt/ge/lt/le/like/left_like/right_like/range/in/not_in/
             #     empty/not_empty; 属于/范围 值内|分隔; 日期=宏(今天/昨天/明天/本周/上周/最近7天/本月/上月/下月)或
             #     字面量(2026-09-09→毫秒); 组织字段(人员/部门/岗位/组织角色/省市区)按名/编码解析; 系统字段创建人/创建时间/
             #     修改人/修改时间; 文件附件类仅 为空/不为空 —— 契约见 trigger-types.md dateFieldEvent 节, UI 手工修复样本实证)

凭证自动读 memory（唯一凭证源，--api/--token 可覆盖）。--begin 省=下一次 --at(默认07:00)。
防呆同名中止；双回读断言 + 耗时统计内嵌；输出即终态。
"""
import argparse, os, sys, time, json, datetime, requests, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timer_notify_runner import load_creds, get_fields, pick, CYCLE_MAP
from miniflow_creator import fetch_app_forms, build_process_json, save_flow, deploy_flow, query_flow

t0 = time.time()


_APPS_CACHE = os.path.join(tempfile.gettempdir(), 'miniflow_apps_cache.json')
_APPS_TTL = 300   # 秒；tenantAppFormList 服务端 ~0.9s，连续建流命中缓存跳过（2026-09-09 剖析实测）


def app_find(api, tok, tenant, want):
    """应用定位。⚠️ tenantAppFormList 单次 0.9s（服务端重）→ 短 TTL 文件缓存，
    建流连跑时第 2 条起直接命中；缓存期间新建了应用/工作表会漏 → TTL 5 分钟自愈"""
    key = f'{api}|{str(tenant)}'
    apps = None
    try:
        if os.path.exists(_APPS_CACHE) and time.time() - os.path.getmtime(_APPS_CACHE) < _APPS_TTL:
            with open(_APPS_CACHE, encoding='utf-8') as f:
                c = json.load(f)
            if c.get('key') == key:
                apps = c.get('apps') or []
    except Exception:
        apps = None
    if apps is None:
        apps = fetch_app_forms(api, tok, tenant)
        try:
            with open(_APPS_CACHE, 'w', encoding='utf-8') as f:
                json.dump({'key': key, 'apps': apps}, f, ensure_ascii=False)
        except Exception:
            pass
    for x in apps:
        if str(x.get('id')) == str(want) or (x.get('name') or '') == want:
            return x
    raise SystemExit(f'应用不存在(--app 传 id 或名称): {want}')


def user_all(api, tok, tenant):
    uj = requests.get(api + '/sys/user/list',
                      headers={'X-Access-Token': tok, 'X-Tenant-Id': str(tenant)},
                      params={'pageNo': 1, 'pageSize': 200}, timeout=30).json()
    return (uj.get('result') or {}).get('records') or []


def resolve_users(api, tok, tenant, kws):
    us = user_all(api, tok, tenant)
    out = []
    for kw in [k.strip() for k in kws if k.strip()]:
        cand = [u for u in us if kw in ((u.get('realname') or '') + (u.get('username') or ''))]
        if not cand:
            raise SystemExit(f'租户内查无用户「{kw}」,现有: ' + json.dumps(
                [(u.get('realname'), u.get('username')) for u in us], ensure_ascii=False))
        if len(cand) > 1:
            print(f'⚠️ 「{kw}」命中多个,取第一个: ' + json.dumps([(u.get('realname'), u.get('username')) for u in cand],
                                                           ensure_ascii=False))
        out.append(cand[0])
    return out


def role_code(api, tok, tenant, name):
    rj = requests.get(api + '/sys/role/list', headers={'X-Access-Token': tok, 'X-Tenant-Id': str(tenant)},
                      params={'pageNo': 1, 'pageSize': 200}, timeout=30).json()
    roles = [(r) for r in ((rj.get('result') or {}).get('records') or []) if str(r.get('tenantId')) == str(tenant)]
    cand = [r for r in roles if name in (r.get('roleName') or '')]
    if not cand:
        raise SystemExit(f'租户内查无角色「{name}」: ' + json.dumps([r.get('roleName') for r in roles], ensure_ascii=False))
    if len(cand) > 1:
        print(f'⚠️ 角色「{name}」命中多个取第一个')
    return cand[0]


def parse_begin(a):
    if a.begin:
        return a.begin
    hh, mm = map(int, (a.at or '07:00').split(':'))
    nxt = datetime.datetime.now().replace(hour=hh, minute=mm, second=0, microsecond=0)
    if nxt <= datetime.datetime.now():
        nxt += datetime.timedelta(days=1)
    return nxt.strftime('%Y-%m-%d %H:%M')


def no_dup(api, h, name):
    rr = requests.get(api + '/act/process/extActProcess/list', params={'processName': name, 'pageSize': 20},
                      headers=h, timeout=30).json()
    recs = (rr.get('result') or {}).get('records') or (rr.get('result') or [])
    if isinstance(recs, list) and recs:
        raise SystemExit(f'同名流程已存在,中止: {name} {[x.get("id") for x in recs]}')


def walk(n, acc=None):
    acc = [] if acc is None else acc
    if not n:
        return acc
    acc.append(n)
    for ch in [n.get('childNode')] + list(n.get('conditionNodes') or []):
        walk(ch, acc)
    return acc


def back(api, tok, flow_id, tenant_id=''):
    # ⚠️ tenant_id 必须显式传：省掉 query_flow 内部的 getUserInfo 一次往返（耗时优化 2026-09-09）
    pj = query_flow(api, tok, flow_id=flow_id, tenant_id=tenant_id)['processJson']
    return pj if isinstance(pj, dict) else json.loads(pj)


def relabel_levels(head):
    i = 1
    cur = head
    while cur:
        cur['attr']['level'] = str(i); i += 1
        cur = cur.get('childNode')


RN = {'eq': '等于', 'ne': '不等于', 'gt': '大于', 'ge': '大于等于', 'lt': '小于', 'le': '小于等于'}


def parse_conds(flds, code, name, node_id, node_name, spec_list, ts):
    """→ (queryItems, fns[(id,name,funText,arg)])  fns 为需插在查询节点前的 function 节点"""
    items, fns = [], []
    n = 0
    for spec in [s.strip() for s in spec_list if s.strip()]:
        col, _, rest = spec.partition('=')
        op, _, val = rest.partition(':')
        fn_mode = field_mode = False
        if op.endswith('_fn'):
            fn_mode, op = True, op[:-3]
        elif op.endswith('_field'):
            field_mode, op = True, op[:-6]
        if op not in RN:
            raise SystemExit(f'条件语法错 字段={op}:{val},规则须 eq/ne/gt/ge/lt/le (+_fn/_field): {spec}')
        f = pick(flds, col, ('input', 'select', 'radio', 'number', 'money', 'date', 'datetime', 'textarea',
                             'checkbox', 'select-user', 'time'), '条件')
        coln, ft = f['name'], f['type']
        if fn_mode:
            n += 1
            arg = 'datetime' if ft == 'datetime' else 'date'
            off = {'today': '+0D', 'tomorrow': '+1D'}.get(val, val)
            fn_id = f'task{ts}9{n}'
            fns.append((fn_id, f'计算{coln}', off, arg))
            items.append({'rule': op, 'ruleName': RN[op], 'valueType': 3, 'val': {
                'variableValue': 'result', 'formTableCode': f'function-{arg}', 'variableName': '结果',
                'fieldType': arg, 'formNodeType': 'function', 'formNodeId': fn_id,
                'formNodeName': f'计算{coln}', 'operationMode': 'cache', 'decimals': 2},
                'name': None, 'field': f['model'], 'columnName': coln, 'type': ft, 'valType': 'variable'})
        elif field_mode:
            bf = pick(flds, val, ('input', 'number', 'money', 'date', 'datetime'), '同表比较')
            items.append({'rule': op, 'ruleName': RN[op], 'valueType': 2, 'val': {
                'variableValue': bf['model'], 'formTableCode': code, 'variableName': bf['name'],
                'fieldType': bf['type'], 'formNodeType': 'search', 'formNodeId': node_id,
                'formNodeName': node_name}, 'name': None, 'field': f['model'], 'columnName': coln,
                'type': ft, 'valType': 'variable'})
        else:
            items.append({'rule': op, 'ruleName': RN[op], 'valueType': 1, 'val': val, 'name': None,
                          'field': f['model'], 'columnName': coln, 'type': ft, 'valType': ft})
    if not items:
        raise SystemExit('--conds 为空')
    return items, fns


def insert_fns(pj, fns):
    for fn_id, fn_name, fun_text, arg in fns:
        op = {'id': fn_id, 'name': fn_name, 'type': 'function', 'status': -1, 'configure': {},
              'attr': {'funType': 'date', 'funContext': {}, 'funText': fun_text,
                       'expressionType': 'delegateExpression', 'expressionValue': '${functionDelegate}',
                       'dateFieldVal': {'formNodeType': 'system', 'variableValue': 'nowDate', 'variableName': '当前日期'},
                       'dateFunctionFormat': {'argument': arg, 'result': arg, 'end': '2', 'out': 'd'},
                       'operationMode': 'cache', 'decimals': 2},
              'addable': True, 'deletable': False, 'error': False, 'errorContent': '',
              'content': f'当前日期{fun_text}', 'pid': 'start'}
        head = pj.get('childNode')
        op['childNode'] = head
        if head:
            head['pid'] = fn_id
        pj['childNode'] = op
        pj.setdefault('formTableList', []).insert(0, {'formTableId': f'form_{fn_id}_function-{arg}',
            'nodeId': fn_id, 'nodeName': fn_name, 'nodeType': 'function', 'formTableCode': f'function-{arg}',
            'formTableName': fn_name, 'operationMode': 'cache', 'decimals': 2})


def subflow_notify(api, tok, appid, tenant, code, name, gm_id, to_model, to_col, sub_name, msg_title, msg_body):
    """subEvent 子流程逐行 message_system（#57/#47 实证）→ 返回 (sub_id, var_entry)"""
    sub_ts = int(time.time() * 1000) + 1
    var_entry = 'var.' + json.dumps({'formTableCode': code, 'formTableId': f'form_{gm_id}_{code}',
                                     'nodeId': gm_id, 'nodeType': 'search',
                                     'field': to_model, 'fieldType': 'select-user'}, ensure_ascii=False)
    sub_msg = {'id': f'task{sub_ts}001', 'name': '发送提醒消息', 'type': 'message_system', 'status': -1,
               'attr': {'type': 'system', 'description': '', 'title': msg_title,
                        'expressionType': 'delegateExpression', 'expressionValue': '${messageDelegate}',
                        'templateContext': msg_body, 'receiveType': 'user',
                        'toUserIds': [var_entry], 'toUsers': [], 'toUserExpression': '',
                        'toUserNames': [to_col], 'level': '1', 'jsonContext': {}},
               'privileges': [], 'configure': {}, 'childNode': None,
               'toUserIds': [var_entry], 'toUserNames': [to_col],
               'addable': True, 'deletable': False, 'error': False, 'errorContent': '',
               'content': f'通知人:{to_col}', 'pid': 'start'}
    search_obj = {'nodeName': '查询记录', 'nodeTypeMain': 'getMore', 'level': '2', 'formTableType': 1,
                  'getDataType': 1, 'formTableMainCode': code, 'nodeType': 'search', 'formTableCode': code,
                  'formTableName': name, 'isSubStart': True, 'selectType': 1,
                  'formTableId': f'form_{gm_id}_{code}', 'nodeId': gm_id}
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
              'attr': {'endDate': None, 'formTableCode': code, 'startCondition': [], 'formTableName': name,
                       'hourValues': [], 'subFormTableObject': dict(search_obj),
                       'formTableId': f'form_{gm_id}_{code}', 'hourType': 1, 'endDateStr': None,
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
    r1 = save_flow(api, tok, {'processName': sub_name, 'processKey': f'process{sub_ts}', 'processType': 'oa',
                              'lowAppId': appid, 'tenantId': str(tenant), 'startType': 'subEvent'}, sub_pj)
    assert r1.get('success'), r1
    sub_id = r1['result']['id']
    uc = query_flow(api, tok, flow_id=sub_id)['updateCount']
    p1 = requests.post(api + '/act/designer/miniDesFlow/api/saveFlow',
                       data={'updateCount': uc, 'processJson': json.dumps(sub_pj, ensure_ascii=False),
                             'processName': sub_name, 'processKey': f'process{sub_id}', 'processType': 'oa',
                             'id': sub_id, 'customProcessId': sub_id, 'lowAppId': appid, 'startType': 'subEvent'},
                       headers={'X-Access-Token': tok, 'X-Tenant-Id': str(tenant),
                                'Content-Type': 'application/x-www-form-urlencoded'}, timeout=60).json()
    assert p1.get('success'), p1
    p2 = requests.put(api + '/act/process/extActProcess/deployProcess', json={'id': sub_id},
                      headers={'X-Access-Token': tok, 'X-Tenant-Id': str(tenant), 'X-Low-App-ID': appid}, timeout=60).json()
    assert p2.get('success'), p2
    return sub_id, var_entry


def attach_call_activity(pj, gm_id, code, ftl_gm, sub_id, sub_name, ts, prev_tail):
    act_id = f'Activity{ts}'
    act = {'id': act_id, 'name': '子流程', 'type': 'callActivity', 'status': -1,
           'attr': {'approvalEnabled': True, 'calledElement': f'process{sub_id}', 'formTableName': None,
                    'formTableSourceTaskId': gm_id, 'formTableCode': None, 'processName': sub_name,
                    'processId': sub_id, 'customProcessId': sub_id, 'loopCardinality': None, 'ratio': 0.5,
                    'isSequential': False, 'isMulti': True, 'subFormTableObject': dict(ftl_gm, isSubStart=True),
                    'collection': '${flowUtil.stringToList(assigneeUserIdList)}', 'elementVariable': 'assigneeUserId',
                    'completionCondition': None, 'variableList': [], 'level': '9',
                    'formTableId': f'form_{gm_id}_{code}'},
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
           'content': f'执行流程:{sub_name}', 'pid': prev_tail['id']}
    prev_tail['childNode'] = act
    return act


def msg_static(api, tok, tenant, chan, title, body, uids, unames, pid):
    ts = int(time.time() * 1000)
    pre = 'task' + str(ts) + ('e' if chan == 'email' else 's')
    attr = {'title': title, 'description': '', 'expressionType': 'delegateExpression',
            'expressionValue': '${messageDelegate}', 'templateContext': body,
            'toUserIds': uids, 'toUserNames': unames, 'toUsers': [], 'toUserExpression': '',
            'level': '9', 'jsonContext': {}}
    if chan == 'email':
        nd = {'id': pre, 'name': '发送邮件', 'type': 'message_email', 'status': -1,
              'attr': dict(attr, type='email', sendType=1, copyToUserIds=[], copyToUserName=[], copyUserExpression='')}
    else:
        nd = {'id': pre, 'name': '发送系统消息', 'type': 'message_system', 'status': -1,
              'attr': dict(attr, type='system', receiveType='user')}
    nd['toUserIds'] = uids
    nd['toUserNames'] = unames
    nd.update({'privileges': [], 'configure': {}, 'childNode': None,
               'addable': True, 'deletable': False, 'error': False, 'errorContent': '',
               'content': '通知人:' + ','.join(unames), 'pid': pid})
    return nd


# ---------------- shell ----------------
def cmd_shell(a, api, tok, app, appid, tenant):
    h = {'X-Access-Token': tok, 'X-Tenant-Id': str(tenant), 'X-Low-App-ID': appid}
    no_dup(api, h, a.name)
    ts = int(time.time() * 1000)
    cfg = {'processName': a.name, 'processKey': f'process{ts}', 'processType': 'oa',
           'lowAppId': appid, 'tenantId': str(tenant), 'startType': 'timerEvent',
           'beginDateStr': a.begin, 'timeCycleName': a.cycle, 'startTaskId': f'task{ts}000', 'nodes': []}
    if a.end:
        cfg['endDateStr'] = a.end
    pj = build_process_json(cfg)
    res = save_flow(api, tok, cfg, pj)
    assert res.get('success'), res
    fid = res['result']['id']
    d = deploy_flow(api, tok, fid, tenant, appid)   # ⚠️ 显式租户+应用：跳过 getUserInfo+listProcess 兜底扫描（耗时优化）
    assert isinstance(d, dict) and d.get('success'), d
    ra = back(api, tok, fid, tenant)['attr']
    assert ra.get('timeCycle') == CYCLE_MAP[a.cycle] and ra.get('beginDateStr') == a.begin \
        and (not a.end or ra.get('endDateStr') == a.end), ra
    print(f"✅ shell: {a.name}({fid}) | {a.begin}~{a.end or '∞'} {a.cycle} | 总耗时 {time.time()-t0:.1f}s")


# ---------------- announce ----------------
def cmd_announce(a, api, tok, app, appid, tenant):
    h = {'X-Access-Token': tok, 'X-Tenant-Id': str(tenant), 'X-Low-App-ID': appid}
    ts = int(time.time() * 1000)
    no_dup(api, h, a.name)
    users = resolve_users(api, tok, tenant, a.users.split(',')) if a.users else user_all(api, tok, tenant)
    uids = ['user.' + (u.get('username') or '') for u in users]
    unames = [u.get('realname') or u.get('username') for u in users]
    cfg = {'processName': a.name, 'processKey': f'process{ts}', 'processType': 'oa',
           'lowAppId': appid, 'tenantId': str(tenant), 'startType': 'timerEvent',
           'beginDateStr': a.begin, 'timeCycleName': a.cycle, 'startTaskId': f'task{ts}000',
           'nodes': [{'type': 'notice', 'id': f'task{ts}001', 'name': '发送系统公告',
                      'attr': {'noticeType': 'system', 'noticeTitle': a.title, 'noticeContent': a.body},
                      'toUserIds': uids, 'toUserNames': unames}]}
    if a.once:
        cfg['endDateStr'] = a.begin[:10] + ' 23:59'
    elif a.end:
        cfg['endDateStr'] = a.end
    pj = build_process_json(cfg)
    for n in walk(pj.get('childNode')):
        if n.get('type') == 'message_system':
            n['attr'].setdefault('receiveType', 'user')
    res = save_flow(api, tok, cfg, pj)
    assert res.get('success'), res
    fid = res['result']['id']
    d = deploy_flow(api, tok, fid, tenant, appid)   # ⚠️ 显式租户+应用：跳过 getUserInfo+listProcess 兜底扫描（耗时优化）
    assert isinstance(d, dict) and d.get('success'), d
    rp = back(api, tok, fid, tenant)
    assert rp['attr'].get('beginDateStr') == a.begin and rp['attr'].get('timeCycle') == '3', rp['attr']
    ms = walk(rp.get('childNode'))[0]
    assert ms['type'] == 'message_system' and ms['attr'].get('receiveType') == 'user' \
        and len(ms.get('toUserIds') or []) == len(uids), '消息契约不符'
    mode = '仅一次' if (a.once or a.end) else a.cycle
    print(f"✅ announce: {a.name}({fid}) | {a.begin} 起 {mode} | 收件 {len(uids)} 人 | 总耗时 {time.time()-t0:.1f}s")


# ---------------- scan ----------------
def cmd_scan(a, api, tok, app, appid, tenant):
    h = {'X-Access-Token': tok, 'X-Tenant-Id': str(tenant), 'X-Low-App-ID': appid}
    t1 = time.time()
    forms = app.get('forms') or []
    hit = next((f for f in forms if a.scan in (f.get('name') or '')), None)
    if not hit:
        raise SystemExit(f'扫描表不存在(--scan): ' + json.dumps([f.get('name') for f in forms], ensure_ascii=False))
    code, name = hit['code'], hit['name']
    flds = get_fields(api, tok, code, tenant)
    if a.update and a.add:
        raise SystemExit('--update 与 --add 互斥,一次只做一个动作')
    upd = None
    if a.update:
        ucol, _, uval = a.update.partition('=')
        if not uval:
            raise SystemExit(f'--update 语法 字段=值: {a.update}')
        upd = (pick(flds, ucol, ('select', 'radio', 'number', 'money', 'input', 'textarea', 'checkbox', 'date'), '更新'), uval)
    add = None
    if a.add:
        tname, _, maps = a.add.partition(':')
        tf = next((f for f in forms if tname in (f.get('name') or '')), None)
        if not tf:
            raise SystemExit(f'--add 目标表不存在: {tname} 现有 ' + json.dumps([f.get('name') for f in forms], ensure_ascii=False))
        add = (tf, maps)
    no_dup(api, h, a.name)
    ts = int(time.time() * 1000)
    gm_id, gm_name = f'task{ts}002', '查询记录'
    items, fns = parse_conds(flds, code, name, gm_id, gm_name, a.conds.split(','), ts)
    cfg = {'processName': a.name, 'processKey': f'process{ts}', 'processType': 'oa',
           'lowAppId': appid, 'tenantId': str(tenant), 'startType': 'timerEvent',
           'beginDateStr': a.begin, 'timeCycleName': a.cycle, 'startTaskId': f'task{ts}000', 'nodes': []}
    if a.end:
        cfg['endDateStr'] = a.end
    cfg['nodes'].append({'type': 'get_more', 'id': gm_id, 'name': gm_name, 'getType': 1,
                         'formTableCode': code, 'formTableName': name, 'conditions': items,
                         'fetchMode': 'cache', 'limitCount': 0})
    if upd:
        cfg['nodes'].append({'type': 'data_update', 'id': f'task{ts}003', 'name': '批量更新',
                             'formTableCode': code, 'formTableName': name,
                             'formTableSourceTaskId': gm_id, 'attr': {'formTableSourceNodeType': 'getMore'}})
    pj = build_process_json(cfg)
    nodes = {n['id']: n for n in walk(pj['childNode'])}
    gm = nodes[gm_id]
    gm['attr'].setdefault('searchFieldGroup', [{'id': f'{ts}9', 'matchType': '', 'queryItems': []}])
    gm['attr']['searchFieldGroup'][0]['queryItems'] = items
    gm['attr']['searchContent'] = ' 且 '.join(
        f"[{i['columnName']} {i['ruleName']} {'变量' if i.get('valType') == 'variable' else i.get('val')}]" for i in items)
    gm['attr'].setdefault('getDataType', 1); gm['attr'].setdefault('noDataType', 1)
    gm['attr']['formTableId'] = f'form_{gm_id}_{code}'
    gm['attr'].setdefault('selectType', 1); gm['attr'].setdefault('formType', 2)
    gm['attr'].setdefault('expressionType', 'delegateExpression')
    gm['attr'].setdefault('expressionValue', '${getMoreRecordDelegate}')
    gm.pop('conditions', None)
    ftl = pj.setdefault('formTableList', [])
    ftl_gm = next((e for e in ftl if e.get('nodeId') == gm_id), None)
    if ftl_gm is None:
        ftl_gm = {'formTableId': f'form_{gm_id}_{code}', 'nodeId': gm_id, 'nodeName': gm_name,
                  'nodeType': 'getMore', 'formTableCode': code, 'formTableName': name,
                  'formTableMainCode': code, 'selectType': 1, 'getDataType': 1}
        ftl.insert(1, ftl_gm)
    ftl_gm['isSubStart'] = True
    if upd:
        du = nodes[f'task{ts}003']
        du['attr']['updateFields'] = [{'id': f'{ts}9', 'optType': '1', 'fieldValue': '', 'field': upd[0]['model'],
                                       'val': upd[1], 'fieldType': upd[0]['type'], 'type': upd[0]['type']}]
        du['attr']['formTableSourceTaskId'] = gm_id
        du['attr']['formTableSourceNodeType'] = 'getMore'
        du['attr']['formTableSourceGetDataType'] = 1
        du['attr']['formTableId'] = f'form_{gm_id}_{code}'
    insert_fns(pj, fns)
    tail = pj['childNode']
    while tail and tail.get('childNode'):
        tail = tail['childNode']
    if add:
        da_id = f'task{ts}004'
        tcode, tname2 = add[0]['code'], add[0]['name']
        tflds = get_fields(api, tok, tcode, tenant)
        fmodel = {}
        for tok_ in add[1].split(','):
            tk = tok_.strip()
            if not tk:
                continue
            tcol, _, src = tk.partition('=')
            tf2 = pick(tflds, tcol, ('input', 'select', 'radio', 'number', 'money', 'date', 'datetime', 'textarea'), '新增目标')
            if src.startswith('固定:'):
                fmodel[tf2['model']] = src[3:]
            elif src == 'now':
                fmodel[tf2['model']] = {'formNodeType': 'system', 'variableValue': 'nowDate', 'variableName': '当前日期'}
            else:
                sf = pick(flds, src, ('input', 'select', 'radio', 'number', 'money', 'date', 'datetime', 'textarea'), '新增来源')
                fmodel[tf2['model']] = {'variableValue': sf['model'], 'formTableCode': code,
                                        'variableName': sf['name'], 'fieldType': sf['type'],
                                        'formNodeType': 'getMore', 'formNodeId': gm_id, 'formNodeName': gm_name}
        da = {'id': da_id, 'name': f'新增{tname2}', 'type': 'data_add', 'status': -1, 'configure': {},
              'attr': {'addDataType': 2, 'noDataType': 1, 'formType': 2,
                       'formTableId': f'form_{da_id}_{tcode}', 'formTableCode': tcode, 'formTableName': tname2,
                       'formTableSourceTaskId': gm_id, 'formTableSourceNodeType': 'getMore',
                       'formTableSourceCode': code, 'formTableSourceGetDataType': 1,
                       'formTableSourceId': f'form_{gm_id}_{code}',
                       'expressionType': 'delegateExpression', 'expressionValue': '${addRecordDelegate}',
                       'level': '9', 'formModel': fmodel},
              'addable': True, 'deletable': False, 'error': False, 'errorContent': '',
              'content': f'新增记录:{tname2}', 'pid': tail['id']}
        tail['childNode'] = da
        tail = da
        ftl.append({'formTableId': f'form_{da_id}_{tcode}', 'nodeId': da_id, 'nodeName': f'新增{tname2}',
                    'nodeType': 'plus', 'formTableCode': tcode, 'formTableName': tname2,
                    'formTableMainCode': tcode, 'addDataType': 2})
    sub_id = None
    if a.mail_to:
        us = resolve_users(api, tok, tenant, a.mail_to.split(','))
        mn = msg_static(api, tok, tenant, 'email', a.mail_title or a.title, a.mail_body or a.body,
                        ['user.' + u['username'] for u in us],
                        [u['realname'] or u['username'] for u in us], tail['id'])
        tail['childNode'] = mn
        tail = mn
    if a.to_field:
        tf = pick(flds, a.to_field, ('select-user',), '逐行收件人')
        sub_name = a.name + '通知子流程'
        sub_id, _ve = subflow_notify(api, tok, appid, tenant, code, name, gm_id, tf['model'], tf['name'],
                                     sub_name, a.title, a.body)
        attach_call_activity(pj, gm_id, code, ftl_gm, sub_id, sub_name, ts, tail)
    relabel_levels(pj['childNode'])
    ra = pj['attr']
    ra['beginDateStr'] = a.begin; ra['timeCycleName'] = a.cycle; ra['timeCycle'] = CYCLE_MAP[a.cycle]
    if a.end:
        ra['endDateStr'] = a.end
    ra.setdefault('conditionFields', []); ra.setdefault('startCondition', [])
    mcfg = {'processName': a.name, 'processKey': f'process{ts}', 'processType': 'oa',
            'lowAppId': appid, 'tenantId': str(tenant), 'startType': 'timerEvent'}
    res = save_flow(api, tok, mcfg, pj)
    assert res.get('success'), res
    fid = res['result']['id']
    d = deploy_flow(api, tok, fid, tenant, appid)   # ⚠️ 显式租户+应用：跳过 getUserInfo+listProcess 兜底扫描（耗时优化）
    assert isinstance(d, dict) and d.get('success'), d
    rp = back(api, tok, fid, tenant)
    ch = [n['type'] for n in walk(rp['childNode'])]
    gmb = next((n for n in walk(rp['childNode']) if n['type'] == 'data_get_more'), None)
    assert gmb, f'无 data_get_more: {ch}'
    qi = (gmb['attr'].get('searchFieldGroup') or [{}])[0].get('queryItems') or []
    assert len(qi) == len(items), '回读条件数不符: ' + json.dumps(qi, ensure_ascii=False)
    assert rp['attr'].get('timeCycle') == CYCLE_MAP[a.cycle] and rp['attr'].get('beginDateStr') == a.begin, '调度不符'
    acts = ('更新' if upd else '') + ('新增' if add else '') + ('逐行消息' if a.to_field else '') + ('邮件' if a.mail_to else '')
    print(f"✅ scan: {a.name}({fid}) 子流程={sub_id} | 动作[{acts}] | 主链 {ch} | "
          f"{a.begin} 起{a.cycle} | 总耗时 {time.time()-t1:.1f}s")


# ---------------- check ----------------
def cmd_check(a, api, tok, app, appid, tenant):
    h = {'X-Access-Token': tok, 'X-Tenant-Id': str(tenant), 'X-Low-App-ID': appid}
    t1 = time.time()
    forms = app.get('forms') or []
    hit = next((f for f in forms if a.scan in (f.get('name') or '')), None)
    if not hit:
        raise SystemExit(f'检查表不存在(--scan): ' + json.dumps([f.get('name') for f in forms], ensure_ascii=False))
    code, name = hit['code'], hit['name']
    flds = get_fields(api, tok, code, tenant)
    if not (a.if_data or a.if_empty):
        raise SystemExit('至少给 --if-data / --if-empty 一个动作')
    no_dup(api, h, a.name)
    ts = int(time.time() * 1000)
    go_id, go_name = f'task{ts}001', '查询记录'
    items, fns = parse_conds(flds, code, name, go_id, go_name, a.conds.split(','), ts)

    def acts(spec):
        if not spec or spec == 'nothing':
            return []
        kind, _, val = spec.partition(':')
        if kind != 'msg':
            raise SystemExit(f'分支动作语法 msg:user:姓名|msg:role:角色|nothing, 收到: {spec}')
        rk, _, nm = val.partition(':')
        if rk == 'user':
            us = resolve_users(api, tok, tenant, [nm])
            return [{'type': 'notice', 'name': '发送消息',
                     'attr': {'noticeType': 'system', 'noticeTitle': a.title, 'noticeContent': a.body},
                     'toUserIds': ['user.' + u['username'] for u in us],
                     'toUserNames': [u['realname'] or u['username'] for u in us]}]
        if rk == 'role':
            r = role_code(api, tok, tenant, nm)
            return [{'type': 'notice', 'name': '发送消息',
                     'attr': {'noticeType': 'system', 'noticeTitle': a.title, 'noticeContent': a.body},
                     'toUserIds': ['role.' + r['roleCode']], 'toUserNames': [r['roleName']]}]
        raise SystemExit(f'msg 后须 user:或 role: → {spec}')

    yes_acts, no_acts = acts(a.if_data), acts(a.if_empty)
    cfg = {'processName': a.name, 'processKey': f'process{ts}', 'processType': 'oa',
           'lowAppId': appid, 'tenantId': str(tenant), 'startType': 'timerEvent',
           'beginDateStr': a.begin, 'timeCycleName': a.cycle, 'startTaskId': f'task{ts}000',
           'nodes': [{'type': 'get_one', 'id': go_id, 'name': go_name, 'getType': 1,
                      'formTableCode': code, 'formTableName': name, 'conditions': items, 'emptyAction': 3},
                     {'type': 'data_branch', 'name': '数据判断',
                      'conditionNodes': [{'name': '有数据', 'nodes': yes_acts},
                                         {'name': '无数据', 'nodes': no_acts}]}]}
    if a.end:
        cfg['endDateStr'] = a.end
    pj = build_process_json(cfg)
    insert_fns(pj, fns)
    nodes = {n['id']: n for n in walk(pj['childNode'])}
    go = nodes.get(go_id) or next((n for n in walk(pj['childNode']) if (n.get('type') or '').endswith('get_one')), None)
    assert go, f'找不到 get_one 节点: {[n["type"] for n in walk(pj["childNode"])]}'
    go['attr'].setdefault('searchFieldGroup', [{'id': f'{ts}9', 'matchType': '', 'queryItems': []}])
    go['attr']['searchFieldGroup'][0]['queryItems'] = items
    go['attr']['searchContent'] = ' 且 '.join(
        f"[{i['columnName']} {i['ruleName']} {'变量' if i.get('valType') == 'variable' else i.get('val')}]" for i in items)
    go['attr']['formTableId'] = f'form_{go_id}_{code}'
    go['attr']['noDataType'] = 3   # 落库键是 noDataType（emptyAction 只是配置层入参）
    go.pop('conditions', None)
    ftl = pj.setdefault('formTableList', [])
    if not any(e.get('nodeId') == go_id for e in ftl):
        ftl.insert(1, {'formTableId': f'form_{go_id}_{code}', 'nodeId': go_id, 'nodeName': go_name,
                       'nodeType': 'getOne', 'formTableCode': code, 'formTableName': name,
                       'formTableMainCode': code, 'selectType': 1, 'getDataType': 1})
    for n in walk(pj.get('childNode')):
        if n.get('type') == 'message_system':
            n['attr'].setdefault('receiveType', 'user')
    relabel_levels(pj['childNode'])
    ra = pj['attr']
    ra['beginDateStr'] = a.begin; ra['timeCycleName'] = a.cycle; ra['timeCycle'] = CYCLE_MAP[a.cycle]
    if a.end:
        ra['endDateStr'] = a.end
    ra.setdefault('conditionFields', []); ra.setdefault('startCondition', [])
    mcfg = {'processName': a.name, 'processKey': f'process{ts}', 'processType': 'oa',
            'lowAppId': appid, 'tenantId': str(tenant), 'startType': 'timerEvent'}
    res = save_flow(api, tok, mcfg, pj)
    assert res.get('success'), res
    fid = res['result']['id']
    d = deploy_flow(api, tok, fid, tenant, appid)   # ⚠️ 显式租户+应用：跳过 getUserInfo+listProcess 兜底扫描（耗时优化）
    assert isinstance(d, dict) and d.get('success'), d
    rp = back(api, tok, fid, tenant)
    ch = [n['type'] for n in walk(rp['childNode'])]
    br = [n for n in walk(rp['childNode']) if (n.get('type') or '') in ('databranch', 'exclusive') and n.get('name') == '数据判断']
    assert br, f'无数据判断分支: {ch}'
    bnames = [b.get('name') for b in (br[0].get('conditionNodes') or [])]
    assert '有数据' in bnames and '无数据' in bnames, bnames
    print(f"✅ check: {a.name}({fid}) | 主链 {ch} | 分支 {bnames} | {a.begin} 起{a.cycle} | 总耗时 {time.time()-t1:.1f}s")


# ---------------- datefield ----------------
UNIT_MAP = {'分钟': 1, '小时': 2, '天': 3}   # plusDateUnit: 1分钟/2小时/3天
CT_MAP = {'1': '不重复', '2': '每年', '3': '每月', '4': '每周'}   # cycleType 枚举（源码口径）

# —— datefield 触发条件全规则 DSL（2026-09-10 由 eq/ne 扩展全字段族；序列化契约=trigger-types.md dateFieldEvent 节 + gotchas #51/#52）——
DF_RN2 = {'eq': '等于', 'ne': '不等于', 'gt': '大于', 'ge': '大于等于', 'lt': '小于', 'le': '小于等于',
          'like': '全模糊', 'left_like': '左模糊', 'right_like': '右模糊', 'range': '在范围内',
          'in': '属于', 'not_in': '不属于', 'empty': '为空', 'not_empty': '不为空'}
DF_NUM_T = ('number', 'integer', 'int', 'money', 'percent')          # 数值族：值转 int/float
DF_TXT_T = ('input', 'textarea')                                     # 文本族：eq/ne/模糊系
DF_DATE_T = ('date', 'datetime')                                     # 日期族：宏行 或 字面量→本地毫秒 int
DF_MACRO = {'今天': 'Today', '@today': 'Today', '昨天': 'Yesterday', '@yesterday': 'Yesterday',
            '明天': 'Tomorrow', '@tomorrow': 'Tomorrow', '本周': 'ThisWeek', '@thisweek': 'ThisWeek',
            '上周': 'LastWeek', '下周': 'NextWeek', '最近7天': 'Last7Days', '近7天': 'Last7Days',
            '本月': 'ThisMonth', '上月': 'LastMonth', '下月': 'NextMonth'}
DF_MACRO_CN = {'Today': '今天', 'Yesterday': '昨天', 'Tomorrow': '明天', 'ThisWeek': '本周', 'LastWeek': '上周',
               'NextWeek': '下周', 'Last7Days': '最近7天', 'ThisMonth': '本月', 'LastMonth': '上月', 'NextMonth': '下月'}
SYS_COL_ALIAS = {   # 系统字段：中文名 → 候选 model（命中即按该字段控件类型走；在 fields 列表没有中文名条目时兜底）
    '创建人': ('create_by', 'createBy'), '创建时间': ('create_time', 'createTime'), '创建日期': ('create_time', 'createTime'),
    '更新人': ('update_by', 'updateBy'), '修改人': ('update_by', 'updateBy'),
    '更新时间': ('update_time', 'updateTime'), '修改时间': ('update_time', 'updateTime')}


def df_num(v, what):
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            raise SystemExit(f'{what}须为数字: {v}')


def df_date_ms(s):
    """日期字面量 → 本地毫秒时间戳。⛔ date 控件固定值必须毫秒 int（写日期串能 save 但恒不成立/UI 歪，2026-09-08 实测）"""
    s = s.strip().replace('/', '-')
    if s.lower().endswith('z'):
        s = s[:-1]
    for fm in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d', '%Y-%m', '%Y'):
        try:
            return int(datetime.datetime.strptime(s, fm).timestamp() * 1000)
        except ValueError:
            continue
    raise SystemExit(f'日期值解析失败(支持 2026-09-09 / 2026-09-09 18:00 / 2026-09 / 2026): {s}')


def df_field(flist, col, name):
    f = next((x for x in flist if (x.get('name') or '') == col), None)
    if f:
        return f
    for key in SYS_COL_ALIAS.get(col, ()):
        f = next((x for x in flist if str(x.get('model') or '').lower() == key), None)
        if f:
            return f
    raise SystemExit(f'工作表「{name}」无字段「{col}」(系统字段名: 创建人/创建时间/修改人/修改时间), 现有: '
                     + json.dumps([x.get('name') for x in flist], ensure_ascii=False))


def df_dept_flat(api, tok, tenant):
    """该租户直属部门树拍平（带头才是本租户，2026-09-09 实测）；返回 [{title,name,id}]"""
    dj = requests.get(api + '/sys/sysDepart/queryTreeList',
                      headers={'X-Access-Token': tok, 'X-Tenant-Id': str(tenant)}, timeout=30).json()
    tree = (dj.get('result') or {})
    tree = tree.get('records') if isinstance(tree, dict) else (tree if isinstance(tree, list) else [])

    def walk(ns, out):
        for x in ns or []:
            out.append(x)
            walk(x.get('children'), out)
        return out
    return walk(tree, [])


def cmd_datefield(a, api, tok, app, appid, tenant):
    h = {'X-Access-Token': tok, 'X-Tenant-Id': tenant, 'X-Low-App-ID': appid}
    t1 = time.time()
    forms = app.get('forms') or []
    hit = next((f for f in forms if a.table in (f.get('name') or '')), None)
    if not hit:
        raise SystemExit(f'工作表不存在(--table): ' + json.dumps([f.get('name') for f in forms], ensure_ascii=False))
    code, name = hit['code'], hit['name']
    try:
        datetime.datetime.strptime(a.at, '%H:%M')
    except ValueError:
        raise SystemExit(f'--at 须为 HH:MM 时刻(如 15:00): {a.at}')
    et, ct = str(a.execute), str(a.cycle_type)
    if et not in ('1', '2', '3'):
        raise SystemExit(f'--execute 枚举: 1=到期当天 2=到期前 3=到期后, 收到: {et}')
    if ct not in CT_MAP:
        raise SystemExit(f'--cycle-type 枚举: 1=不重复 2=每年 3=每月 4=每周, 收到: {ct}')
    if et != '1':
        if not a.plus:
            raise SystemExit(f'--execute {et} 须配 --plus 偏移量(如 --plus 1 --plus-unit 天)')
        if a.plus_unit not in UNIT_MAP:
            raise SystemExit(f'--plus-unit 枚举: 分钟/小时/天, 收到: {a.plus_unit}')
    # ⚠️ formTableId 必须用 fields 接口 result.id（真实 DB id），禁止 form_start_ 前缀（trigger-types.md）
    raw = requests.get(api + f'/desform/api/fields/{code}?group=true',
                       headers={'X-Access-Token': tok, 'X-Tenant-Id': tenant}, timeout=30).json()
    res = raw.get('result') or {}
    dbid = res.get('id')
    assert dbid, f'fields 接口未返回 result.id: {raw}'
    fl = next((f for f in (res.get('fields') or []) if (f.get('name') or '') == a.field), None)
    if not fl:
        raise SystemExit(f'工作表「{name}」无日期字段「{a.field}」, 现有: '
                         + json.dumps([f.get('name') for f in (res.get('fields') or [])], ensure_ascii=False))
    ft = (fl.get('type') or '').lower()
    fmt = (fl.get('options') or {}).get('format', '')
    # triggerFieldType 只收 year/month/date/datetime：按控件类型 + 时间格式映射
    tt = 'datetime' if (ft == 'datetime' or (ft == 'date' and 'HH' in str(fmt))) \
        else ('year' if ft == 'year' else ('month' if ft == 'month' else 'date'))
    no_dup(api, h, a.name)
    ts = int(time.time() * 1000)
    cfg = {'processName': a.name, 'processKey': f'process{ts}', 'processType': 'oa',
           'lowAppId': appid, 'tenantId': tenant, 'startType': 'dateFieldEvent',
           'formTableCode': code, 'formTableName': name, 'formTableId': dbid, 'titleField': None,
           'triggerField': fl['model'], 'triggerFieldType': tt, 'executeType': int(et),
           'executionTime': a.at, 'cycleType': int(ct), 'linkFormTableName': a.field,
           'startTaskId': f'task{ts}000', 'nodes': []}
    if et != '1':
        cfg['plusDate'] = str(a.plus)          # ⚠️ 字符串
        cfg['plusDateUnit'] = UNIT_MAP[a.plus_unit]
    pj = build_process_json(cfg)
    # —— 触发条件（--conds）—— 全规则全字段族 DSL（2026-09-10 由 eq/ne 扩展；序列化契约=trigger-types.md dateFieldEvent 节
    #    + gotchas #51/#52 + SKILL.md 组织/人员类控件值形态，2026-09-09 用户 UI 手工修复实证）
    #    ⛔ 铁律：① 行独立雪花式 id（与组 id 不同——缺 id/重 id 行 UI 无法 加/删/且或）
    #             ② 组 matchType 大写 AND/OR（多行） ③ 日期字段条件行=系统变量形态（valueType:3 + 三键对象，与 triggerField 调度并存）
    #             ④ select-user：val=username + name=realname（无 valueType 键）⑤ select/radio 值直通选项文案
    #    DSL：<字段中文名>=<规则>:<值>，逗号分隔=且；属于/不属于/在范围内 值内用 | 分隔；
    #    日期字段值：宏(今天/昨天/明天/本周/上周/下周/最近7天/本月/上月/下月/@today 等) 或 字面量(2026-09-09 → 毫秒)；
    #    empty/not_empty 值留空；select-user 值支持 username/realname；部门/岗位按名称解析；组织角色按角色名解析；
    #    省市区按编码链 省码|市码|区码（末级=val，全链=allVal）；系统字段（创建人/创建时间/修改人/修改时间）按别名匹配
    conds = getattr(a, 'conds', '') or ''
    rows = []
    if conds:
        flist = res.get('fields') or []
        us = dep = pos = None
        n = 0
        for spec in [x.strip() for x in conds.split(',') if x.strip()]:
            col, _, rest = spec.partition('=')
            op, _, val = rest.partition(':')
            if op not in DF_RN2:
                raise SystemExit(f'datefield --conds 规则须为: {"/".join(DF_RN2)} '
                                 f'(例: 状态=eq:待确认,描述=like:复诊,附件=not_empty:,预约日期=eq:今天,'
                                 f'数字=ge:10,金额=range:100|200,多选框组=in:选项A|选项B), 收到: {spec}')
            f = df_field(flist, col, name)
            ft = (f.get('type') or '').lower()
            coln, fy, mdl = f.get('name'), f.get('type'), f['model']
            rid, n = f'{ts}{n:03d}', n + 1              # ⛔ 行 id 独立且 ≠ 组 id({ts}000)
            if op in ('empty', 'not_empty'):            # 任意控件类型；val/valType 写 null（⛔ 禁空串→设计器 Invalid date）
                rows.append({'id': rid, 'rule': op, 'ruleName': DF_RN2[op], 'valueType': '1',
                             'val': None, 'name': None, 'field': mdl, 'columnName': coln, 'type': fy, 'valType': None})
                continue
            if op == 'range':                           # 在范围内 begin|end：数字=数值、日期=字面量（宏不行）
                bv, _, ev = val.partition('|')
                if ft in DF_NUM_T:
                    rowv = {'beginVal': df_num(bv, 'range 起'), 'endVal': df_num(ev, 'range 止')}
                elif ft in DF_DATE_T:
                    rowv = {'beginVal': df_date_ms(bv), 'endVal': df_date_ms(ev)}
                else:
                    raise SystemExit(f'range 仅支持数字/金额/日期字段, 字段「{col}」类型 {fy}: {spec}')
                rows.append({'id': rid, 'rule': 'range', 'ruleName': '在范围内', 'valueType': '1',
                             'name': None, 'field': mdl, 'columnName': coln, 'type': fy, 'valType': fy, **rowv})
                continue
            if val == '':
                raise SystemExit(f'条件值缺失(为空/不为空才可留空): {spec}')
            if ft == 'select-user':                     # 人员：val=username + name=realname（无 valueType 键）
                if op not in ('eq', 'ne'):
                    raise SystemExit(f'人员字段「{col}」仅支持 等于/不等于: {spec}')
                if us is None:
                    us = user_all(api, tok, tenant)
                byu = [u for u in us if u.get('username') == val]
                byr = [u for u in us if u.get('realname') == val]
                if byu:
                    cand = byu
                elif len(byr) == 1:
                    cand = byr
                elif len(byr) > 1:
                    raise SystemExit(f'「{val}」命中多个用户(重名), 请写 username: ' + json.dumps(
                        [(u.get('username'), u.get('realname')) for u in byr], ensure_ascii=False))
                else:
                    raise SystemExit(f'租户内查无用户「{val}」(支持 username/realname), 现有: ' + json.dumps(
                        [(u.get('username'), u.get('realname')) for u in us], ensure_ascii=False))
                u = cand[0]
                rows.append({'id': rid, 'rule': op, 'ruleName': DF_RN2[op],
                             'val': u['username'], 'name': u.get('realname'), 'field': mdl,
                             'columnName': coln, 'type': 'select-user', 'valType': 'select-user'})
                continue
            if ft in ('select-depart', 'position', 'select-position', 'post'):
                # 部门/岗位：val=[id] + name=[名称] 数组（org 选择器族形态；岗位无 UI 原生样本按部门族推断）
                if op not in ('eq', 'ne', 'in', 'not_in'):
                    raise SystemExit(f'组织字段「{col}」支持 等于/属于 系规则: {spec}')
                ns = [x.strip() for x in val.split('|') if x.strip()] if op in ('in', 'not_in') else [val]
                if ft == 'select-depart':
                    if dep is None:
                        dep = df_dept_flat(api, tok, tenant)
                    pool = dep
                    hit = lambda kw: [x for x in pool if (x.get('title') or '') == kw]
                    idk = 'id'
                else:                                   # 岗位列表（sys_position）：名称/编码匹配
                    if pos is None:
                        pj0 = requests.get(api + '/sys/position/list',
                                           headers={'X-Access-Token': tok, 'X-Tenant-Id': str(tenant)},
                                           params={'pageNo': 1, 'pageSize': 200}, timeout=30).json()
                        pos = (pj0.get('result') or {}).get('records') or []
                    pool = pos
                    hit = lambda kw: [x for x in pool
                                      if kw in ((x.get('name') or '') + (x.get('code') or ''))]
                    idk = 'id'
                ids, nms = [], []
                for kw in ns:
                    cand = hit(kw)
                    if not cand:
                        raise SystemExit(f'租户内查无{("部门" if ft == "select-depart" else "岗位")}「{kw}」: '
                                         + json.dumps([(x.get('title') or x.get('name')) for x in pool][:20],
                                                      ensure_ascii=False))
                    if len(cand) > 1:
                        print(f'⚠️ {("部门" if ft == "select-depart" else "岗位")}「{kw}」命中多个取第一个')
                    ids.append(cand[0].get(idk) or cand[0].get('code'))
                    nms.append(cand[0].get('title') or cand[0].get('name') or kw)
                rows.append({'id': rid, 'rule': op, 'ruleName': DF_RN2[op], 'val': ids, 'name': nms,
                             'field': mdl, 'columnName': coln, 'type': 'select-depart'
                             if ft == 'select-depart' else 'select-position', 'valType': 'select-depart'
                             if ft == 'select-depart' else 'select-position'})
                continue
            if ft == 'org-role':                        # 组织角色：val=roleCode 标量 + name=null（SKILL UI 原生样本带 valueType）
                if op not in ('eq', 'ne'):
                    raise SystemExit(f'组织角色字段「{col}」仅支持 等于/不等于: {spec}')
                r = role_code(api, tok, tenant, val)    # ⚠️ role/list 跨租户，内部已按 tenantId 过滤
                rows.append({'id': rid, 'rule': op, 'ruleName': DF_RN2[op], 'valueType': '1',
                             'val': r.get('roleCode'), 'name': None, 'field': mdl,
                             'columnName': coln, 'type': 'org-role', 'valType': 'org-role'})
                continue
            if ft == 'area-linkage':                    # 省市区：值=编码链 省|市|区（末级=val、全链=allVal；写名称路径无效）
                if op not in ('eq', 'ne'):
                    raise SystemExit(f'省市区字段「{col}」仅支持 等于/不等于(值=末级行政区编码): {spec}')
                codes = [x.strip() for x in val.split('|') if x.strip()]
                if len(codes) == 1:
                    print(f'⚠️ 省市区「{col}」建议传编码链 省码|市码|区码(如 110000|110100|110108), 只传末级 allVal 不完整')
                rows.append({'id': rid, 'rule': op, 'ruleName': DF_RN2[op], 'valueType': '1',
                             'val': codes[-1], 'allVal': codes, 'name': None, 'field': mdl,
                             'columnName': coln, 'type': fy, 'valType': fy})
                continue
            if ft == 'link-field':                      # 他表字段控件：type/valType 写 input，值=设计器选择器显示的选项文本
                if op not in ('eq', 'ne', 'like', 'left_like', 'right_like'):
                    raise SystemExit(f'他表字段「{col}」支持 等于/模糊 系规则: {spec}')
                rows.append({'id': rid, 'rule': op, 'ruleName': DF_RN2[op], 'valueType': '1',
                             'val': val, 'name': None, 'field': mdl, 'columnName': coln,
                             'type': 'input', 'valType': 'input'})
                continue
            if ft == 'link-record':                     # 关联记录：值=来源表记录 _id（本地无法按标题解析, 用表数据 API 查到 _id 再填）
                if op not in ('eq', 'ne', 'in', 'not_in'):
                    raise SystemExit(f'关联记录「{col}」支持 等于/属于 系规则: {spec}')
                if op in ('in', 'not_in'):
                    vs = [x.strip() for x in val.split('|') if x.strip()]
                    rows.append({'id': rid, 'rule': op, 'ruleName': DF_RN2[op], 'valueType': '1',
                                 'val': vs, 'value': vs, 'name': None, 'field': mdl,
                                 'columnName': coln, 'type': fy, 'valType': fy})
                else:
                    rows.append({'id': rid, 'rule': op, 'ruleName': DF_RN2[op], 'valueType': '1',
                                 'val': val, 'name': None, 'field': mdl,
                                 'columnName': coln, 'type': fy, 'valType': fy})
                continue
            if ft == 'switch':                          # 开关：值=activeValue 字符串（如 是/1，由字段 options 定义）
                if op not in ('eq', 'ne'):
                    raise SystemExit(f'开关字段「{col}」仅支持 等于/不等于(值须为 activeValue): {spec}')
                rows.append({'id': rid, 'rule': op, 'ruleName': DF_RN2[op], 'valueType': '1',
                             'val': val, 'name': None, 'field': mdl, 'columnName': coln, 'type': fy, 'valType': fy})
                continue
            if ft == 'checkbox':                        # 多选：in/not_in（val=逗号串 + value=数组 双形态）
                if op not in ('in', 'not_in'):
                    raise SystemExit(f'多选字段「{col}」仅支持 属于/不属于/为空/不为空: {spec}')
                vs = [x.strip() for x in val.split('|') if x.strip()]
                if not vs:
                    raise SystemExit(f'多选字段「{col}」属于值用 | 分隔至少一项: {spec}')
                rows.append({'id': rid, 'rule': op, 'ruleName': DF_RN2[op], 'valueType': '1',
                             'val': ','.join(vs), 'value': vs, 'name': None, 'field': mdl,
                             'columnName': coln, 'type': fy, 'valType': fy})
                continue
            if ft in ('select', 'radio'):               # 下拉/单选：eq/ne 直通文案；属于=数组（radio 无 value 键, select 带 value 键）
                if op not in ('eq', 'ne', 'in', 'not_in'):
                    raise SystemExit(f'下拉/单选字段「{col}」支持 等于/不等于/属于/不属于: {spec}')
                if op in ('in', 'not_in'):
                    vs = [x.strip() for x in val.split('|') if x.strip()]
                    r = {'id': rid, 'rule': op, 'ruleName': DF_RN2[op], 'valueType': '1',
                         'val': vs, 'name': None, 'field': mdl, 'columnName': coln, 'type': fy, 'valType': fy}
                    if ft == 'select':
                        r['value'] = vs
                    rows.append(r)
                else:
                    rows.append({'id': rid, 'rule': op, 'ruleName': DF_RN2[op], 'valueType': '1',
                                 'val': val, 'name': None, 'field': mdl, 'columnName': coln, 'type': fy, 'valType': fy})
                continue
            if ft in DF_DATE_T:                         # 日期族：宏 → 系统变量行（valueType:3 + 三键对象）；字面量 → 毫秒 int
                if val in DF_MACRO:
                    if op != 'eq':
                        raise SystemExit(f'日期字段「{col}」宏值(今天/昨天/…/最近7天/本月/上月)仅支持 等于: {spec}')
                    vv = DF_MACRO[val]
                    rows.append({'id': rid, 'columnName': coln, 'field': mdl, 'rule': 'eq', 'ruleName': '等于',
                                 'valueType': 3, 'val': {'formNodeType': 'system', 'variableValue': vv,
                                                         'variableName': DF_MACRO_CN[vv]},
                                 'type': fy, 'valType': 'variable'})
                else:
                    if op not in ('eq', 'ne', 'gt', 'ge', 'lt', 'le'):
                        raise SystemExit(f'日期字段「{col}」支持 等于/大于 系规则: {spec}')
                    rows.append({'id': rid, 'rule': op, 'ruleName': DF_RN2[op], 'valueType': '1',
                                 'val': df_date_ms(val), 'name': None, 'field': mdl,
                                 'columnName': coln, 'type': fy, 'valType': fy})
                continue
            if ft == 'time':                            # 时间控件：无 timestamp，值写 "HH:mm:ss" 字符串
                if op not in ('eq', 'ne'):
                    raise SystemExit(f'时间字段「{col}」支持 等于/不等于(值写 HH:mm:ss): {spec}')
                if val.count(':') == 1:
                    val = val + ':00'
                rows.append({'id': rid, 'rule': op, 'ruleName': DF_RN2[op], 'valueType': '1',
                             'val': val, 'name': None, 'field': mdl, 'columnName': coln, 'type': fy, 'valType': fy})
                continue
            if ft in DF_NUM_T:                          # 数值族：值转 int/float
                if op not in ('eq', 'ne', 'gt', 'ge', 'lt', 'le'):
                    raise SystemExit(f'数值字段「{col}」支持 等于/大于 系规则: {spec}')
                rows.append({'id': rid, 'rule': op, 'ruleName': DF_RN2[op], 'valueType': '1',
                             'val': df_num(val, f'数值字段「{col}」'), 'name': None, 'field': mdl,
                             'columnName': coln, 'type': fy, 'valType': fy})
                continue
            if ft in DF_TXT_T:                          # 文本族：等于/不等于/全模糊/左模糊/右模糊
                if op not in ('eq', 'ne', 'like', 'left_like', 'right_like'):
                    raise SystemExit(f'文本字段「{col}」支持 等于/全模糊/左模糊/右模糊: {spec}')
                rows.append({'id': rid, 'rule': op, 'ruleName': DF_RN2[op], 'valueType': '1',
                             'val': val, 'name': None, 'field': mdl, 'columnName': coln, 'type': fy, 'valType': fy})
                continue
            raise SystemExit(f'触发条件暂不支持字段类型 {fy}(字段「{col}」): {spec}\n'
                             f'已支持: 文本/数值/金额/日期/时间/下拉/单选/多选/人员/部门/岗位/组织角色/省市区/开关/'
                             f'他表字段/关联记录 + 系统字段(创建人/创建时间等); 该类型可试 为空/不为空')
        if not rows:
            raise SystemExit('--conds 为空')
        pj.setdefault('attr', {})['startCondition'] = [{
            'id': f'{ts}000', 'matchType': 'AND' if len(rows) > 1 else '', 'queryItems': rows}]
        print('触发条件:', json.dumps([f"{r['columnName']} {r['ruleName']} "
              + ('[系统变量]' if isinstance(r.get('val'), dict) else str(r.get('name') if r.get('name') is not None
                else (f"{r.get('beginVal')}~{r.get('endVal')}" if r.get('rule') == 'range' else r.get('val'))))
              for r in rows], ensure_ascii=False))
    res2 = save_flow(api, tok, cfg, pj)
    assert res2.get('success'), res2
    fid = res2['result']['id']
    d = deploy_flow(api, tok, fid, tenant, appid)   # ⚠️ 显式租户+应用：跳过 getUserInfo+listProcess 兜底扫描（耗时优化）
    assert isinstance(d, dict) and d.get('success'), d
    ra = back(api, tok, fid, tenant)['attr']
    assert ra.get('startType') == 'dateFieldEvent' and ra.get('triggerField') == fl['model'] \
        and ra.get('triggerFieldType') == tt and ra.get('executionTime') == a.at \
        and int(ra.get('executeType')) == int(et) and int(ra.get('cycleType')) == int(ct) \
        and ra.get('formTableCode') == code, ra
    if rows:
        rsc = ra.get('startCondition') or []
        assert rsc and (rsc[0].get('queryItems') or []) and len(rsc[0]['queryItems']) == len(rows), \
            f'回读触发条件不符: {rsc}'
        got = [(i.get('columnName'), i.get('val'), i.get('value')) for i in rsc[0]['queryItems']]
        want = [(i.get('columnName'), i.get('val'), i.get('value')) for i in rows]
        assert got == want, f'回读触发条件不符: {got} != {want}'
        assert all(i.get('id') for i in rsc[0]['queryItems']), f'回读条件行缺 id: {rsc}'
    when = ('当天' if et == '1' else ('前' if et == '2' else '后')) + ('' if et == '1' else a.plus + a.plus_unit)
    print(f"✅ datefield: {a.name}({fid}) | 表「{name}」字段「{a.field}」到期{when} {a.at} 执行 {CT_MAP[ct]} | "
          f"总耗时 {time.time()-t1:.1f}s")


def main():
    p = argparse.ArgumentParser(description='定时触发简流统一运行器')
    sub = p.add_subparsers(dest='cmd', required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--tenant', required=True)
    common.add_argument('--app', required=True)
    common.add_argument('--name', default='')
    common.add_argument('--begin', default='')
    common.add_argument('--end', default='')
    common.add_argument('--cycle', default='每天')
    common.add_argument('--api', default='')
    common.add_argument('--token', default='')
    for nm in ('shell', 'announce', 'scan', 'check', 'datefield'):
        s = sub.add_parser(nm, parents=[common])
        # --at：shell/announce/scan/check 为 --begin 缺省时的取时（07:00）；datefield 为 executionTime 时刻（默认15:00）
        s.add_argument('--at', default='15:00' if nm == 'datefield' else '07:00')
        if nm == 'announce':
            s.add_argument('--once', action='store_true')
            s.add_argument('--users', default='')
            s.add_argument('--title', required=True)
            s.add_argument('--body', required=True)
        elif nm == 'scan':
            s.add_argument('--scan', required=True)
            s.add_argument('--conds', required=True)
            s.add_argument('--update', default='')
            s.add_argument('--add', default='')
            s.add_argument('--to-field', default='')
            s.add_argument('--title', default='提醒')
            s.add_argument('--body', default='请及时处理。')
            s.add_argument('--mail-to', default='')
            s.add_argument('--mail-title', default='')
            s.add_argument('--mail-body', default='')
        elif nm == 'check':
            s.add_argument('--scan', required=True)
            s.add_argument('--conds', required=True)
            s.add_argument('--if-data', default='')
            s.add_argument('--if-empty', default='')
            s.add_argument('--title', default='提醒')
            s.add_argument('--body', default='请及时处理。')
        elif nm == 'datefield':
            s.add_argument('--table', required=True)          # 工作表名（中文，按名称定位）
            s.add_argument('--field', required=True)          # 日期字段中文名
            s.add_argument('--execute', default='1')          # 1=到期当天 2=到期前 3=到期后
            s.add_argument('--cycle-type', default='1')       # 1=不重复 2=每年 3=每月 4=每周
            s.add_argument('--plus', default='')              # execute=2/3 偏移量（字符串）
            s.add_argument('--plus-unit', default='天')        # 分钟/小时/天
            s.add_argument('--conds', default='')             # 触发条件 字段=<规则>:<值>,逗号=且; 规则: eq/ne/gt/ge/lt/le/
                                                              #   like(全模糊)/left_like/right_like/range/in/not_in/
                                                              #   empty/not_empty; 多值用|; 日期字段写 宏(今天/昨天/…/本月)
                                                              #   或字面量2026-09-09(自动转毫秒); 系统字段(创建人/时间等)可用
                                                              #   组织字段按名解析; 附件等文件类只支持 为空/不为空
    a = p.parse_args()
    a.cycle = a.cycle if a.cycle in CYCLE_MAP else {'每天': '3'}.get(a.cycle, a.cycle)
    API, TOKEN = (a.api or load_creds()[0]), (a.token or load_creds()[1])
    app = app_find(API, TOKEN, int(a.tenant), a.app)
    appid = str(app['id'])
    a.begin = parse_begin(a)
    if not a.name:
        if a.cmd == 'datefield':
            a.name = a.table + '按日期触发'
        else:
            a.name = {'shell': '定时触发流程-' + a.cycle, 'announce': '定时公告-' + a.begin[:10],
                      'scan': '定时扫描-' + a.begin[:10], 'check': '定时检查-' + a.begin[:10]}[a.cmd]
    if a.cycle not in CYCLE_MAP:
        raise SystemExit(f'周期须为: {list(CYCLE_MAP)}')
    {'shell': cmd_shell, 'announce': cmd_announce, 'scan': cmd_scan, 'check': cmd_check,
     'datefield': cmd_datefield}[a.cmd](a, API, TOKEN, app, appid, str(a.tenant))


if __name__ == '__main__':
    main()
