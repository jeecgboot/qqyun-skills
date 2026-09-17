# -*- coding: utf-8 -*-
"""
miniflow_helpers —— 简流批量创建提速助手（配合 miniflow_creator 使用）

解决三个反复耗时的点：
1. function（运算·fun）节点的 funContext 手工拼装（8 键 compact JSON + md5 + URL 编码）——FunBuilder 一行一个引用；
2. subEvent 子流程 5 步发布配方——publish_subflow 一次调用；
3. 批建收尾按应用核对流程条数（防 lowAppId 静默丢失）——check_app_flows。

契约来源：线上已发布流程 processJson 实测提取（funText 占位符 / funContext 编码 / data_update 引用形态），非推测。

仅依赖 miniflow_creator 的公开函数（register_subprocess_id / query_flow）与 requests。
"""
import hashlib
import json
import urllib.parse

import requests

QUOTE_SAFE = ":,.-_/?"


# ---------------------------------------------------------------- function 节点

class FunBuilder:
    """拼 function(fun) 运算节点。

    用法：
        fb = FunBuilder()
        p1 = fb.add_ref(field='input_xxx', form_table_code='tbl', node_id='task...001',
                        node_type='search', node_name='获取客户记录',
                        table_text='客户', field_text='客户名称')
        p2 = fb.add_ref(field='number_yyy', form_table_code='tbl2', node_id='task...002',
                        node_type='search', node_name='获取订单记录',
                        table_text='订单', field_text='金额')
        expr = f"CONCAT({p1},'-',IF({p2}>100,'大','小'))"
        node = fb.build(node_id=f'task{ts}010', name='拼接品名', expr=expr,
                        content="CONCAT(客户名称,'-',IF(金额>100,'大','小'))", level='2')
        # node 直接挂到 processJson 链上（pid/childNode 由调用方维护）

    add_ref 返回 funText 里的占位符串 '{{md5.field_model}}'，原样拼进表达式。
    """

    def __init__(self):
        self.fun_context = {}

    def add_ref(self, field, form_table_code, node_id, node_type,
                node_name, table_text, field_text):
        obj = {
            "field": field,
            "formTableCode": form_table_code,
            "formNodeId": node_id,
            "formNodeType": node_type,          # 'search'（get_one/get_more 结果）或 'table'（起始行）
            "variableValue": field,
            "formNodeName": node_name,
            "tableText": table_text,
            "fieldText": field_text,
        }
        compact = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
        md5 = hashlib.md5(compact.encode("utf-8")).hexdigest()
        self.fun_context[md5] = urllib.parse.quote(compact, safe=QUOTE_SAFE)
        return "{{%s.%s}}" % (md5, field)

    def build(self, node_id, name, expr, content=None, level="1", decimals=2):
        return {
            "id": node_id,
            "name": name,
            "type": "function",
            "status": -1,
            "configure": {},
            "attr": {
                "funType": "fun",
                "funText": expr,
                "funContext": self.fun_context,
                "expressionType": "delegateExpression",
                "expressionValue": "${functionDelegate}",
                "level": str(level),
                "operationMode": "cache",
                "decimals": decimals,
            },
            "addable": True,
            "deletable": False,
            "error": False,
            "errorContent": "",
            "content": content or expr,
        }


def du_var_function(function_node_id, function_node_name, field_type="input", decimals=2):
    """data_update 的 updateFields[].val —— 引用某 function 节点计算结果（variableValue='result'）。

    updateFields 条目整体写法：
        {'id': <行id>, 'optType': '1', 'fieldValue': '',
         'field': <目标字段model>, 'val': du_var_function(...),
         'fieldType': <目标字段type>, 'type': <目标字段type>}
    """
    return {
        "formNodeType": "function",
        "variableValue": "result",
        "formTableCode": "function-fun",
        "variableName": "结果",
        "fieldType": field_type,
        "formNodeId": function_node_id,
        "formNodeName": function_node_name,
        "operationMode": "cache",
        "decimals": decimals,
    }


# ---------------------------------------------------------------- 子流程发布配方

def publish_subflow(api_base, token, low_app_id, flow_id, tenant_id):
    """subEvent 子流程一次发布到位（5 步配方封装）。

    register_subprocess_id → designer saveFlow(urlencoded, 补 customProcessId/processKey) →
    PUT deployProcess → /act/process/list 校验 key=process<DBid>。
    返回 {'ok': bool, 'engine_key_found': bool, 'messages': [...]}。
    普通（非 subEvent）流程不要用这个，直接 save_flow + deploy_flow。
    """
    from miniflow_creator import register_subprocess_id

    msgs = []
    headers = {"X-Access-Token": token, "X-Tenant-Id": str(tenant_id),
               "X-Low-App-ID": str(low_app_id)}
    rec = requests.get(api_base + "/act/process/extActProcess/queryById",
                       headers=headers, params={"id": flow_id}, timeout=60).json().get("result")
    if not rec:
        return {"ok": False, "engine_key_found": False, "messages": ["queryById 无记录 id=%s" % flow_id]}
    process_key = "process%s" % flow_id
    register_subprocess_id(process_key, flow_id)
    msgs.append("register_subprocess_id ok")
    data = {
        "updateCount": rec.get("updateCount"),
        "processJson": rec.get("processJson"),
        "processName": rec.get("processName"),
        "processKey": process_key,
        "processType": rec.get("processType") or "oa",
        "id": flow_id,
        "customProcessId": flow_id,
        "lowAppId": str(low_app_id),
        "startType": "subEvent",
    }
    j = requests.post(api_base + "/act/designer/miniDesFlow/api/saveFlow",
                      headers=headers, data=data, timeout=120).json()
    msgs.append("saveFlow: %s %s" % (j.get("success"), j.get("message")))
    if not j.get("success"):
        return {"ok": False, "engine_key_found": False, "messages": msgs}
    d = requests.put(api_base + "/act/process/extActProcess/deployProcess",
                     headers=headers, json={"id": flow_id}, timeout=120).json()
    msgs.append("deploy: %s %s" % (d.get("success"), d.get("message")))
    found = False
    for page in range(1, 15):
        lj = requests.get(api_base + "/act/process/list", headers=headers,
                          params={"pageNo": page, "pageSize": 100}, timeout=60).json()
        recs = (lj.get("result") or {}).get("records") or []
        if not recs:
            break
        if any(process_key == str(x.get("key")) for x in recs):   # 引擎列表键名是 key，不是 processKey
            found = True
            break
    msgs.append("engine key %s: %s" % (process_key, "found" if found else "NOT FOUND"))
    return {"ok": bool(d.get("success")) and found, "engine_key_found": found, "messages": msgs}


# ---------------------------------------------------------------- 批建收尾核对

def check_app_flows(api_base, token, low_app_id, tenant_id, expected_names=None):
    """按应用列简流（extActProcess/list?lowAppId=，0.1s），核对条数与名单。

    expected_names：期望在应用内看到的流程中文名列表；返回 {'records': [...], 'missing': [...]}。
    lowAppId 为空的流程不会出现在结果里 —— missing 非空时逐条 queryById 查 lowAppId 是否为空。
    """
    headers = {"X-Access-Token": token, "X-Tenant-Id": str(tenant_id),
               "X-Low-App-ID": str(low_app_id)}
    j = requests.get(api_base + "/act/process/extActProcess/list", headers=headers,
                     params={"pageNo": 1, "pageSize": 100, "lowAppId": str(low_app_id)},
                     timeout=60).json()
    records = (j.get("result") or {}).get("records") or []
    out = {"records": records, "missing": []}
    if expected_names is not None:
        have = {str(x.get("processName")) for x in records}
        out["missing"] = [n for n in expected_names if n not in have]
    return out
