# -*- coding: utf-8 -*-
"""手拼简流构建器库（第 3 个构建器）—— 两个批量构建器（miniflow `build_flows.py` /
lowapp `postbuild_flows.py`）都不覆盖的档位，用本库手拼：

    · data_get_one selectType=3（关联取值取单条）+ searchFieldGroup 空置
    · databranch 数据分支（有数据 ${flow_has_data==1} / 无数据 ${flow_has_data==0}）
    · callActivity 调子流程（数据对象 / isMulti / 传参 variableList）
    · timerEvent 自定义周期（hourValues + generateExecTime）与 dateFieldEvent（startCondition）
    · function record 统计条数 + message_system 占位符消息
    · data_add 引用本记录字段（@start）、data_delete 挂 getMore 源

契约依据（改本库前先读）：node-contract.md §3-b/§9.1/§9.4、gotchas #110/#111/#131、
references/extra-flow-lib.md（用法与七个配方）。全部形态取自 2026-10-08 实测
（24 表应用 25 条流，其中 7 条手拼），check_node_contract 违例 0。

用法（app 脚本里）：
    import sys; sys.path.insert(0, '<miniflow skill>/scripts')
    from extra_flow_lib import *
    init(API, TOKEN, TID, AID, code_map={'主表': 'tb_main', '子表': 'tb_sub'},
         fields_map={'主表': fetch_form_fields(API, TOKEN, 'tb_main', TID), ...})
    n = get_one('task{TS}051', '获取子表数据', '子表', [], 3, 'start', '0.500',
                select_type=3, src={'node': 'start', 'type': 'table', 'table': '主表'},
                link_field=FM('主表', '子表'), link_table='子表')

⚠️ 节点 id 自定（惯例 task{TS}xxx / Gateway{TS}xxx，TS=int(time.time()*1000)），全流程内唯一。
"""
import base64
import json
import re
import time

import requests

from miniflow_creator import build_process_json, save_flow, deploy_flow, query_flow, api_request  # noqa: F401

CFG = {}
TS = int(time.time() * 1000)
HDR = {}


def init(api, token, tenant_id, app_id, code_map, fields_map, ts=None):
    """注入应用上下文。code_map: {表中文名: 表code}；fields_map: {表中文名: fetch_form_fields 结果}"""
    global TS, HDR
    if ts:
        TS = int(ts)
    CFG.update(api=api.rstrip('/'), token=token, tenant_id=str(tenant_id),
               app_id=str(app_id), codes=dict(code_map), fields=dict(fields_map))
    HDR = {'X-Access-Token': token, 'X-Tenant-Id': str(tenant_id), 'X-Low-App-ID': str(app_id)}
    return TS


def FM(t, f):
    return CFG['fields'][t][f]['model']


def FT(t, f):
    return CFG['fields'][t][f]['type']


def CODE(t):
    return CFG['codes'][t]


def db_id(t):
    """表的真实 DB id（/desform/api/fields 的 result.id）——按日期字段触发的 cfg.formTableId 用它"""
    r = requests.get(f"{CFG['api']}/desform/api/fields/{CODE(t)}", headers=HDR,
                     params={'group': 'true'}, timeout=30).json()
    return str(r['result']['id'])


# ── 通用取值形态（node-contract §3-b / §9.4）──
def row_ref(node_id, node_name, table_code, field_model, field_name):
    """引用某取单条节点记录的字段（formNodeType 必须是来源节点类型 search）"""
    return {'formNodeId': node_id, 'formNodeName': node_name, 'variableName': field_name,
            'formNodeType': 'search', 'variableValue': field_model, 'formTableCode': table_code}


def rec7(node_id, node_name, table_code, field_type='link-record'):
    """7 键「记录id」引用（子流程本行 / 按 id 取值 / callActivity 传参都用它）"""
    return {'variableValue': '_id', 'variableName': '记录id', 'formNodeType': 'search',
            'formNodeId': node_id, 'formNodeName': node_name, 'formTableCode': table_code,
            'fieldType': field_type}


def start_ref(table_code, field_model, field_name):
    """@start（本流程触发记录）字段引用"""
    return {'formNodeId': 'start', 'formNodeName': '工作表事件触发', 'variableName': field_name,
            'formNodeType': 'table', 'variableValue': field_model, 'formTableCode': table_code}


def sys_ms():
    """系统毫秒（**日期控件写它**；gotchas 2026-09-24：nowDate 会落成字符串混格式）"""
    return {'formNodeType': 'system', 'variableValue': 'millisecond', 'variableName': '毫秒'}


def sys_now():
    return {'formNodeType': 'system', 'variableValue': 'nowDate', 'variableName': '当前日期'}


def fn_ref(node_id, node_name, fun_type, field_type):
    """运算节点结果引用（组合 H var_val 形态）；field_type ∈ number/date"""
    return {'variableValue': 'result', 'formTableCode': f'function-{fun_type}', 'variableName': '结果',
            'fieldType': field_type, 'formNodeType': 'function', 'formNodeId': node_id,
            'formNodeName': node_name, 'operationMode': 'cache' if fun_type != 'record' else 'everyTime',
            'decimals': 2}


def var_ref(name):
    """流程变量引用（3 键形态）"""
    return {'variableName': name, 'formNodeType': 'variable', 'variableValue': name}


# ── 条件形态（searchFieldGroup / startCondition 共用 queryItem）──
def c_fixed(field_model, column, ctype, val):
    return {'rule': 'eq', 'ruleName': '等于', 'valueType': '1', 'val': val, 'name': None,
            'field': field_model, 'columnName': column, 'type': ctype, 'valType': ctype}


def c_ref(field_model, column, ctype, ref, rule='eq', rule_name='等于', value_type=2):
    """value_type：2=本流程节点引用，3=运算节点结果引用"""
    return {'rule': rule, 'ruleName': rule_name, 'valueType': value_type, 'val': ref, 'name': None,
            'field': field_model, 'columnName': column, 'type': ctype, 'valType': 'variable'}


def grp(items, gid=None, match=''):
    return {'id': str(gid or (TS + len(items))), 'matchType': match, 'queryItems': items}


def df_cond_group(items, gid=None):
    """dateFieldEvent 的 startCondition（attr.startCondition = [df_cond_group(items)]）"""
    return {'id': str(gid or (TS + 1)), 'matchType': 'AND', 'queryItems': [
        dict(it, id=str(TS + 2 + i)) for i, it in enumerate(items)]}


def df_item(field_model, column, ctype, val=None, rule='eq', rule_name='等于', val_type=None):
    """startCondition 条件行（val_type：radio 传 'radio'；not_empty 传 None 且 val=None）"""
    return {'rule': rule, 'ruleName': rule_name, 'val': val, 'name': None,
            'field': field_model, 'columnName': column, 'type': ctype, 'valType': val_type}


# ── 节点骨架 ──
def _r(node_id, name, ntype, content, pid, level):
    return {'id': node_id, 'name': name, 'type': ntype, 'status': -1, 'configure': {},
            'childNode': None, 'addable': True, 'deletable': False, 'error': False,
            'errorContent': '', 'content': content, 'pid': pid,
            'attr': {'expressionType': 'delegateExpression', 'level': level}}


def get_one(node_id, name, table, conds, empty, pid, level,
            select_type=1, src=None, link_field=None, link_table=None):
    """取单条。select_type=1 普通查询；=3 关联取值（attr.formTableCode/Id 都按**源表**，
    目标表只进 linkFormTable*；src={'node','type','table'} 指上游节点/来源表。
    empty(noDataType)：继续=1 / 新增记录=2 / 中止=3（node-contract noDataType 口径）。"""
    n = _r(node_id, name, 'data_get_one', f'工作表 "{table}"', pid, level)
    a = n['attr']
    a.update({'selectType': select_type, 'formType': 2, 'formModel': {},
              'formTableId': f'form_{node_id}_{CODE(table)}', 'formTableCode': CODE(table),
              'formTableName': table, 'formTableSourceTaskId': '', 'formTableSourceNodeType': '',
              'expressionValue': '${getOneRecordDelegate}', 'searchContent': [],
              'searchFieldGroup': [grp(conds, TS + int(str(node_id)[-3:]) * 7)] if conds else [],
              'noDataType': empty, 'ignoreSortRule': False})
    if select_type == 3:
        st = src['table']
        a.update({'formTableId': f"form_{src['node']}_{CODE(st)}",
                  'formTableCode': CODE(st), 'formTableName': st,
                  'formTableSourceTaskId': src['node'], 'formTableSourceNodeType': src['type'],
                  'linkFormTableField': link_field, 'linkFormTableCode': CODE(link_table),
                  'linkFormTableName': link_table, 'linkFormTableType': 1})
    return n


def get_more(node_id, name, table, conds, pid, level):
    a = {'selectType': 1, 'formType': 2, 'formTableId': f'form_{node_id}_{CODE(table)}',
         'formTableCode': CODE(table), 'formTableName': table, 'formTableSourceTaskId': '',
         'formTableSourceNodeType': '', 'expressionType': 'delegateExpression',
         'expressionValue': '${getMoreRecordDelegate}', 'searchContent': '',
         'searchFieldGroup': [grp(conds)] if conds else [], 'ignoreSortRule': False,
         'noDataType': 1, 'getDataType': 1, 'level': level, 'limitNum': 0}
    return {'id': node_id, 'name': name, 'type': 'data_get_more', 'status': -1, 'attr': a,
            'configure': {}, 'childNode': None, 'addable': True, 'deletable': False,
            'content': f'工作表 "{table}"', 'pid': pid, 'error': False, 'errorContent': ''}


def fn_node(node_id, name, fun_type, fun_text, pid, level, extra_attr=None, content=None):
    """运算节点。fun_type ∈ fun/date/record…；content 画布文案**必须与 funText 不同义重复**
    （check_node_contract 提示项）；日期运算用 extra_attr={'dateFieldVal': sys_now(),
    'dateFunctionFormat': {...}}"""
    a = {'funType': fun_type, 'funContext': {}, 'funText': fun_text,
         'expressionType': 'delegateExpression', 'expressionValue': '${functionDelegate}',
         'operationMode': 'cache' if fun_type != 'record' else 'everyTime', 'decimals': 2}
    if extra_attr:
        a.update(extra_attr)
    return {'id': node_id, 'name': name, 'type': 'function', 'status': -1, 'configure': {},
            'attr': a, 'addable': True, 'deletable': False, 'error': False,
            'errorContent': '', 'content': content or fun_text, 'pid': pid, 'childNode': None}


def record_fn(node_id, name, gm_id, table, pid, level):
    """record 统计条数（funContext 指向 getMore 节点；formTableId 用 GM 节点）"""
    a = {'funType': 'record',
         'funContext': {'nodeId': gm_id, 'formTableCode': CODE(table), 'getDataType': 1,
                        'formTableId': f'form_{gm_id}_{CODE(table)}', 'formTableName': table},
         'funText': f'form_{gm_id}_{CODE(table)}', 'expressionType': 'delegateExpression',
         'expressionValue': '${functionDelegate}', 'operationMode': 'everyTime', 'decimals': 2}
    return {'id': node_id, 'name': name, 'type': 'function', 'status': -1, 'configure': {},
            'attr': a, 'addable': True, 'deletable': False, 'error': False, 'errorContent': '',
            'content': f'{name}：{table}', 'pid': pid, 'childNode': None}


def branch_row(rid, gw_id, content, bname, prio, child=None):
    return {'deletable': False, 'pid': gw_id, 'type': 3, 'error': False, 'content': content,
            'childNode': child, 'isDefault': False, 'addable': True, 'errorContent': None,
            'name': bname, 'id': rid, 'status': -1,
            'attr': {'showPriorityLevel': True, 'priorityLevel': prio, 'level': '0.750',
                     'conditionGroup': [], 'branchType': 2}}


def databranch(gw_id, prev_id, yes_child, no_child, level='0.750'):
    """数据分支（名必须恰为「数据分支」）。**分支内首节点 pid 要手改成分支行 id**：
    n_x['pid'] = gw['conditionNodes'][i]['id']"""
    b1 = branch_row(f'flow{TS}{str(gw_id)[-3:]}1', gw_id, '${flow_has_data==1}', '有数据', 1, yes_child)
    b2 = branch_row(f'flow{TS}{str(gw_id)[-3:]}2', gw_id, '${flow_has_data==0}', '无数据', 2, no_child)
    return {'conditionNodes': [b1, b2], 'addable': True, 'name': '数据分支', 'pid': prev_id,
            'id': gw_id, 'type': 'databranch', 'attr': {'level': level}, 'status': -1, 'childNode': None}


def msg_node(node_id, name, title, body, pid, level, json_ctx=None, content=None, to='管理员'):
    """系统消息。占位符消息：body='还有{{<md5>.结果}}条…'，json_ctx={md5: base64(json字符串)}；
    明文消息 json_ctx=None。toUserIds/toUserNames 双写。
    ⚠️ 收件人固定 user.admin（仅显示名 to 可参数化）——应用内无 admin 账号时需改 toUserIds。"""
    a = {'type': 'system', 'title': title, 'description': '',
         'expressionType': 'delegateExpression', 'expressionValue': '${messageDelegate}',
         'receiveType': 'user', 'toUserIds': ['user.admin'], 'toUserNames': [to],
         'toUsers': [], 'toUserExpression': '', 'templateContext': body, 'level': level}
    if json_ctx:
        a['jsonContext'] = json_ctx
    return {'id': node_id, 'name': name, 'type': 'message_system', 'status': -1, 'attr': a,
            'configure': {}, 'childNode': None, 'addable': True, 'deletable': False,
            'error': False, 'errorContent': '', 'content': content or name, 'pid': pid,
            'toUserIds': ['user.admin'], 'toUserNames': [to]}


def placeholder_ctx(fn_id, decimals=2):
    """record 统计的占位符 jsonContext：返回 (md5, body片段, jsonContext)。
    场景见 gotchas #131 邻近——消息体引用 function-record 结果。"""
    import hashlib
    key = {'field': 'result', 'formTableCode': 'function-record', 'nodeId': fn_id,
           'nodeType': 'function', 'operationMode': 'everyTime', 'decimals': decimals}
    cs = json.dumps(key, ensure_ascii=False, separators=(',', ':'))
    h = hashlib.md5(cs.encode('utf-8')).hexdigest()
    ctx = {h: base64.b64encode(cs.encode('utf-8')).decode()}
    return h, '{{%s.结果}}' % h, ctx


def add_node(node_id, name, table, form_model, pid, level):
    """新增记录（data_add；form_model 值形态：rec7/row_ref/start_ref/常量/sys_ms()；
    关联记录字段值要补 ['fieldType']='link-record'）"""
    a = {'addDataType': 1, 'noDataType': 1, 'formType': 2,
         'formTableId': f'form_{node_id}_{CODE(table)}', 'formTableCode': CODE(table),
         'formTableName': table, 'formTableSourceTaskId': '', 'formTableSourceNodeType': '',
         'expressionType': 'delegateExpression', 'expressionValue': '${addRecordDelegate}',
         'level': level, 'formModel': form_model}
    return {'id': node_id, 'name': name, 'type': 'data_add', 'status': -1, 'attr': a,
            'configure': {}, 'childNode': None, 'addable': True, 'deletable': False,
            'error': False, 'errorContent': '', 'content': f'工作表 "{table}"', 'pid': pid}


def del_node(node_id, name, table, src_id, pid, level):
    """删除记录（data_delete 挂 getMore 源查找）"""
    a = {'formType': 2, 'formModel': {}, 'formTableId': f'form_{src_id}_{CODE(table)}',
         'formTableCode': CODE(table), 'formTableName': table, 'formTableSourceTaskId': src_id,
         'formTableSourceNodeType': 'getMore', 'formTableSourceGetDataType': 1,
         'expressionType': 'delegateExpression', 'expressionValue': '${deleteRecordDelegate}',
         'level': level}
    return {'id': node_id, 'name': name, 'type': 'data_delete', 'status': -1, 'attr': a,
            'configure': {}, 'childNode': None, 'addable': True, 'deletable': False,
            'error': False, 'errorContent': '', 'content': f'工作表 "{table}"', 'pid': pid}


def ca_node(node_id, name, sub_db_id, sub_name, pid, level, src_gm_id,
            pass_list=None, sub_obj=None, table_main=None):
    """调子流程（callActivity）。必带：customProcessId=DB id、isMulti、
    subFormTableObject（**与子流程 start 那份同一对象**，formTableId 非空）、
    formTableSourceTaskId=上游 getMore 节点 id、listenerData=MiniCallActivityListener、
    inVariableModels 四对。pass_list: [{'field','columnName','type','value'}]。"""
    a = {'approvalEnabled': True, 'calledElement': f'process{sub_db_id}',
         'formTableName': None, 'formTableSourceTaskId': src_gm_id,
         'formTableCode': None, 'processName': sub_name, 'processId': sub_db_id,
         'customProcessId': sub_db_id, 'loopCardinality': None, 'ratio': 0.5,
         'isSequential': False, 'isMulti': True, 'subFormTableObject': sub_obj,
         'collection': '${flowUtil.stringToList(assigneeUserIdList)}',
         'elementVariable': 'assigneeUserId', 'completionCondition': None,
         'variableList': pass_list or [],
         'level': level,
         'formTableId': f'form_{src_gm_id}_{CODE(table_main)}' if table_main else None}
    return {'id': node_id, 'name': name, 'type': 'callActivity', 'status': -1,
            'attr': a, 'approvalMode': 1,
            'listenerData': [{'id': '502880e54853a496014805e5d9190012', 'eventType': 'start',
                              'listenerType': 'javaClass', 'listenerName': '子流程流程变量',
                              'value': 'org.jeecg.modules.extbpm.process.adapter.delegate.MiniCallActivityListener',
                              'allowDel': False}],
            'inVariableModels': [{'source': s, 'target': t} for s, t in [
                ('applyUserId', 'applyUserId'), ('dataId', 'dataId'),
                ('JG_LOCAL_PROCESS_ID', 'JG_SUB_MAIN_PROCESS_ID'), ('handleDataId', 'handleDataId')]],
            'outVariableModels': [], 'childNode': None, 'addable': True, 'deletable': False,
            'error': False, 'content': f'执行流程:{sub_name}', 'pid': pid, 'errorContent': ''}


# ── formTableList 登记条目（变量选择器的输入行；节点建了就要登记）──
def ftl_get_more(node_id, name, table):
    return {'formTableId': f'form_{node_id}_{CODE(table)}', 'nodeId': node_id, 'nodeName': name,
            'nodeType': 'getMore', 'formTableCode': CODE(table), 'formTableName': table,
            'formTableMainCode': CODE(table), 'formTableType': 1, 'selectType': 1,
            'getDataType': 1, 'level': '2'}


def ftl_get_one(node_id, name, table, select_type=1, main_table=None):
    return {'formTableId': f'form_{node_id}_{CODE(table)}', 'nodeId': node_id, 'nodeName': name,
            'nodeType': 'search', 'formTableCode': CODE(table), 'formTableName': table,
            'formTableMainCode': CODE(main_table or table), 'selectType': select_type, 'level': '1'}


def ftl_fn(node_id, name, fun_type):
    return {'formTableId': f'form_{node_id}_function-{fun_type}', 'nodeId': node_id, 'nodeName': name,
            'nodeType': 'function', 'formTableCode': f'function-{fun_type}', 'formTableName': name,
            'operationMode': 'cache' if fun_type != 'record' else 'everyTime', 'decimals': 2}


def ftl_add(node_id, name, table):
    return {'formTableId': f'form_{node_id}_{CODE(table)}', 'nodeId': node_id, 'nodeName': name,
            'nodeType': 'plus', 'formTableCode': CODE(table), 'formTableName': table,
            'addDataType': 1}


def walk(n, acc=None):
    if acc is None:
        acc = []
    while n:
        acc.append(n)
        walk(n.get('childNode'), acc)
        for b in (n.get('conditionNodes') or []):
            acc.append(b)
            walk(b.get('childNode'), acc)
        n = None
    return acc


# ── 流程级助手 ──
def existing_names():
    r = requests.get(f"{CFG['api']}/act/process/extActProcess/list", headers=HDR,
                     params={'pageNo': 1, 'pageSize': 200}, timeout=30).json()
    return {x.get('processName') for x in ((r.get('result') or {}).get('records') or [])}


def save_deploy(cfg, pj, name):
    r = save_flow(CFG['api'], CFG['token'], cfg, pj)
    assert r.get('success'), f'{name} save 失败 {json.dumps(r, ensure_ascii=False)[:400]}'
    fid = r['result']['id']
    d = deploy_flow(CFG['api'], CFG['token'], fid)
    print(f'  OK {name} id={fid} deploy={str(d)[:60]}')
    return fid


def publish_subflow(sub_name, sub_start, cfg_extra=None):
    """#47 子流程发布配方：saveFlow → 回查 updateCount → saveFlow 补 customProcessId
    → deploy → 校验定义 key 注册。返回 DB id。sub_start 的 variableList 声明输入变量。"""
    cfg = {'processName': sub_name, 'processKey': f'process{TS}901', 'processType': 'oa',
           'lowAppId': CFG['app_id'], 'startType': 'subEvent', 'tenantId': CFG['tenant_id']}
    if cfg_extra:
        cfg.update(cfg_extra)
    r1 = save_flow(CFG['api'], CFG['token'], cfg, sub_start)
    assert r1.get('success'), f'子流程 save 失败 {json.dumps(r1, ensure_ascii=False)[:400]}'
    sub_db = str(r1['result']['id'])
    sub_new = query_flow(CFG['api'], CFG['token'], flow_id=sub_db)
    r2 = api_request(CFG['api'], CFG['token'], '/act/designer/miniDesFlow/api/saveFlow', form_data={
        'processName': sub_name, 'processKey': f'process{sub_db}', 'processType': 'oa',
        'lowAppId': CFG['app_id'], 'startType': 'subEvent', 'id': sub_db,
        'customProcessId': sub_db, 'processJson': json.dumps(sub_start, ensure_ascii=False),
        'updateCount': str(sub_new['updateCount'])}, extra_headers=HDR)
    assert (r2 or {}).get('success'), f'补 customProcessId 失败 {json.dumps(r2, ensure_ascii=False)[:300]}'
    deploy_flow(CFG['api'], CFG['token'], sub_db)
    q = requests.get(f"{CFG['api']}/act/process/extActProcess/queryById", params={'id': sub_db},
                     headers=HDR, timeout=30).json()
    xml = (q.get('result') or {}).get('processXml') or ''
    m = re.search(r'<process id="([^"]+)"', base64.b64decode(xml).decode('utf-8', 'ignore')) if xml else None
    assert m and m.group(1) == f'process{sub_db}', f'子流程定义未注册: {m and m.group(1)}'
    print(f'  OK 子流程 {sub_name} DB={sub_db} key=process{sub_db}')
    return sub_db


def timer_custom(pj, begin_str, hour=7, end_str=None):
    """timerEvent 自定义周期（每天 hour 点）：attr 合并 + generateExecTime 回填 times。
    pj 由 build_process_json({'startType': 'timerEvent', ...}) 生成后调用。"""
    ra = pj['attr']
    ra.update({'beginDateStr': begin_str, 'timeCycleName': '自定义', 'timeCycle': 'custom',
               'hourType': 3, 'hourValues': [hour], 'hourValueMin': 0, 'hourValueMax': 23,
               'dayOrWeekType': 1, 'dayValue': 1, 'dayValues': [], 'weekValue': [],
               'monthType': 1, 'monthValues': []})
    if end_str:
        ra['endDateStr'] = end_str
    ra.setdefault('conditionFields', []); ra.setdefault('startCondition', [])
    ra.setdefault('endDateStr', None); ra['times'] = []
    form = {'beginDateStr': begin_str, 'timeCycleName': '自定义', 'timeCycle': 'custom',
            'hourType': '3', 'hourValues': str(hour), 'hourValueMin': '0', 'hourValueMax': '23',
            'dayOrWeekType': '1', 'dayValue': '1', 'monthType': '1'}
    g = requests.post(f"{CFG['api']}/act/designer/miniDesFlow/api/generateExecTime",
                      headers=HDR, data=form, timeout=30).json()
    assert isinstance(g.get('obj'), list) and len(g['obj']) >= 7, f'generateExecTime 失败 {str(g)[:200]}'
    ra['times'] = g['obj']
    assert all(t.endswith(' %02d:00:00' % hour) for t in g['obj'][:3]), g['obj'][:3]
    return pj


def readback(name, expect_types=None, sub_gm=None, sub_db=None):
    """回读断言：链上节点类型序列 +（可选）callActivity/数据分支/子流程数据对象检查。
    ⚠️ query_flow 按名查必须带 low_app_id，否则跨应用扫不到/命中错（2026-09-17 实测）。"""
    rec = query_flow(CFG['api'], CFG['token'], process_name=name,
                     tenant_id=CFG['tenant_id'], low_app_id=CFG['app_id'])
    pj = rec['processJson']
    if isinstance(pj, str):
        pj = json.loads(pj)
    nodes = [n for n in walk(pj.get('childNode')) if n.get('type') != 3]
    types = [n.get('type') for n in nodes]
    ks = ''
    for n in nodes:
        a = n.get('attr') or {}
        if n.get('type') == 'callActivity':
            ks += f" | ca:{a.get('customProcessId') == sub_db},{a.get('isMulti')}," \
                  f"{(a.get('subFormTableObject') or {}).get('nodeId') == sub_gm}"
        if n.get('type') == 'databranch':
            ks += f" | gw名:{n.get('name') == '数据分支'}"
    print(f'  {name}: startType={pj.get("startType")} 链={types}{ks}')
    if expect_types is not None:
        assert types == expect_types, f'{name} 链不符: {types} != {expect_types}'
    return pj
