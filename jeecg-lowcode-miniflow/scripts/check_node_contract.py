# -*- coding: utf-8 -*-
"""按 references/node-contract.md 逐节点校验已建流程的 processJson。

用法：
    py scripts/check_node_contract.py --api-base URL --token TOK \
        --tenant-id N --app-id A [--only 流程名子串]

退出码：0=全部通过；1=有违例（逐条打印）。

**为什么需要它**：save/deploy/ADDED 全绿、计数对得上，都不能证明节点键发对了——
本页第一版就是被这个坑掉的（批量建的 63 条流程，引擎认的键一条都没发出去）。
"""
import argparse
import json
import sys
import urllib.request

OK, BAD, WARN = [], [], []


def _get(api, tok, tid, app, path, timeout=90):
    req = urllib.request.Request(api.rstrip("/") + path)
    req.add_header("X-Access-Token", tok)
    req.add_header("X-Tenant-Id", str(tid))
    req.add_header("X-Low-App-ID", str(app))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def nodes_of(pj):
    """深度遍历所有节点（含分支子节点）。"""
    out = []

    def walk(n, depth=0):
        if not isinstance(n, dict) or depth > 12:
            return
        out.append(n)
        walk(n.get("childNode"), depth + 1)
        for c in (n.get("conditionNodes") or []):
            walk(c, depth + 1)
            for cc in (c.get("nodes") or []):
                walk(cc, depth + 1)

    walk(pj.get("childNode"))
    return out


def nonempty(v):
    return v not in (None, "", [], {})


def check_flow(name, pj):
    ns = nodes_of(pj)
    nadd = {}           # 节点 id -> 节点（供 callActivity 反查上游）
    for n in ns:
        nadd[n.get("id")] = n

    for n in ns:
        t = n.get("type")
        a = n.get("attr") or {}
        nm = "%s / %s" % (name, n.get("name") or t)

        if t == "data_get_more":
            is_link = a.get("selectType") == 3
            if is_link:
                for k, want in (("getDataType", 1), ("noDataType", 1), ("formType", 2),
                                ("linkFormTableType", 1),
                                ("formTableSourceTaskId", "start"),
                                ("formTableSourceNodeType", "table"),
                                ("expressionType", "delegateExpression"),
                                ("expressionValue", "${getMoreRecordDelegate}")):
                    if a.get(k) != want:
                        BAD.append("%s: getMore.%s=%r 应为 %r" % (nm, k, a.get(k), want))
                for k in ("linkFormTableField", "linkFormTableCode", "linkFormTableName"):
                    if not nonempty(a.get(k)):
                        BAD.append("%s: getMore 取关联记录缺少 %s" % (nm, k))
                if not str(a.get("formTableId") or "").startswith("form_start_"):
                    BAD.append("%s: getMore.formTableId=%r 应为 form_start_<主表code>"
                               % (nm, a.get("formTableId")))
                if nonempty(a.get("limitNum")) and a.get("limitNum") not in (0, "0"):
                    BAD.append("%s: getMore 取关联记录不应设 limitNum（现值 %r），逐行会漏行"
                               % (nm, a.get("limitNum")))
            else:
                # 被 callActivity 当作数据源、却不是「从单条记录获取关联记录」
                nxt = n.get("childNode")
                if isinstance(nxt, dict) and nxt.get("type") == "callActivity":
                    BAD.append("%s: 该 getMore 是子流程的数据源，selectType=%r 应为 3"
                               % (nm, a.get("selectType")))
            continue

        if t == "callActivity":
            if a.get("isMulti") is not True:
                BAD.append("%s: callActivity 逐行执行应为 isMulti=true（现值 %r）"
                           % (nm, a.get("isMulti")))
            obj = a.get("subFormTableObject")
            if not isinstance(obj, dict) or not nonempty(obj.get("nodeId")):
                BAD.append("%s: callActivity 缺 subFormTableObject（「选择数据对象」为空）" % nm)
            else:
                if obj.get("nodeType") != "getMore":
                    BAD.append("%s: subFormTableObject.nodeType=%r 应为 getMore"
                               % (nm, obj.get("nodeType")))
                src = nadd.get(obj.get("nodeId")) or {}
                sa = src.get("attr") or {}
                if src.get("type") == "data_get_more" and sa.get("selectType") != 3:
                    BAD.append("%s: 数据对象指向的 getMore selectType=%r 应为 3"
                               % (nm, sa.get("selectType")))
                want_ftid = "form_%s_%s" % (obj.get("nodeId"), obj.get("formTableCode"))
                if a.get("formTableId") != want_ftid:
                    BAD.append("%s: callActivity.formTableId=%r 应为 %r"
                               % (nm, a.get("formTableId"), want_ftid))
            if not nonempty(a.get("customProcessId")):
                BAD.append("%s: callActivity 缺 customProcessId（子流程未绑定）" % nm)
            ivm = n.get("inVariableModels") or a.get("inVariableModels")
            if not nonempty(ivm):
                BAD.append("%s: callActivity 缺 inVariableModels（未向子流程传参）" % nm)
            continue

        if t == "data_add":
            fm = a.get("formModel") or n.get("formModel")
            if not nonempty(fm):
                BAD.append("%s: data_add 的 formModel 为空 → 面板全空、运行时建空记录" % nm)
            for k in ("formTableCode", "formTableName"):
                if not nonempty(a.get(k)):
                    BAD.append("%s: data_add 缺 %s" % (nm, k))
            continue

        if t == "data_update":
            uf = a.get("updateFields") or n.get("updateFields")
            if not nonempty(uf):
                BAD.append("%s: data_update 缺 updateFields" % nm)
            continue

        if t in ("databranch", "exclusive"):
            if not nonempty(n.get("conditionNodes")):
                BAD.append("%s: %s 缺 conditionNodes" % (nm, t))
            continue

        if t in ("edit", "approver"):
            res = n.get("assigneeType") or (a.get("assigneeType"))
            grp = n.get("approverGroups") or a.get("approverGroups")
            if not nonempty(grp) and not res:
                BAD.append("%s: %s 无办理人配置" % (nm, t))
            c = n.get("content")
            if not nonempty(c):
                BAD.append("%s: %s 的 content（办理人显示名）为空 → 画布显示灰色占位"
                           % (nm, t))
            elif "$" in str(c) or "assigneeBy" in str(c):
                BAD.append("%s: %s 的 content 是表达式原文（%r），应写语义名"
                           % (nm, t, c))
            continue


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-base", required=True)
    ap.add_argument("--token", required=True)
    ap.add_argument("--tenant-id", required=True)
    ap.add_argument("--app-id", required=True)
    ap.add_argument("--only", default=None)
    a = ap.parse_args()

    res = _get(a.api_base, a.token, a.tenant_id, a.app_id,
               "/act/process/extActProcess/listProcess?lowAppId=%s&pageSize=300" % a.app_id)
    res = res.get("result") or {}
    recs = res.get("records") if isinstance(res, dict) else res
    recs = recs or []
    print("[check] 应用 %s 共 %d 条流程" % (a.app_id, len(recs)))

    n = 0
    n_sub = 0
    # 先扫一遍：哪些子流程**真的被主流程调用**了。
    # 没被调用的（孤儿子流程）本就不该有「数据源 / 被谁触发」——
    # 拿它当违例会假阳性（线上模版自己也有这种：金标 30 条子里有 2 条没绑上）。
    called = set()
    cache = {}
    for x in recs:
        try:
            d0 = _get(a.api_base, a.token, a.tenant_id, a.app_id,
                      "/act/process/extActProcess/queryById?id=%s" % x.get("id"))
        except Exception:                                # noqa: BLE001
            continue
        det0 = d0.get("result") or {}
        pj0 = det0.get("processJson")
        if isinstance(pj0, str):
            try:
                pj0 = json.loads(pj0)
            except Exception:                            # noqa: BLE001
                continue
        cache[str(x.get("id"))] = (det0, pj0)
        if isinstance(pj0, dict):
            for n0 in nodes_of(pj0):
                if n0.get("type") == "callActivity":
                    cp = (n0.get("attr") or {}).get("customProcessId")
                    if cp:
                        called.add(str(cp))

    for x in recs:
        nm = x.get("processName") or ""
        if a.only and a.only not in nm:
            continue
        n += 1
        det, pj = cache.get(str(x.get("id")), (None, None))
        if det is None:
            try:
                d = _get(a.api_base, a.token, a.tenant_id, a.app_id,
                         "/act/process/extActProcess/queryById?id=%s" % x.get("id"))
            except Exception as e:                       # noqa: BLE001
                BAD.append("%s: 读取失败 %s" % (nm, e))
                continue
            det = d.get("result") or {}
            pj = det.get("processJson")
            if isinstance(pj, str):
                try:
                    pj = json.loads(pj)
                except Exception:                        # noqa: BLE001
                    BAD.append("%s: processJson 解析失败" % nm)
                    continue
        if not isinstance(pj, dict):
            continue
        check_flow(nm, pj)

        # —— 子流程侧的两个键是**父流程 deploy 后回填的**，回读才知道有没有 ——
        # 实测：63 条流程全绿、全部启用，但子流程只有 1 条回填上了「数据源/被谁触发」，
        # 于是设计器里子流程页白屏。计数对得上 ≠ 链路通。
        if det.get("startType") == "subEvent":
            n_sub += 1
            ftl = pj.get("formTableList") or []
            if not (ftl and ftl[0].get("isSubStart")):
                msg = ("%s: 子流程 formTableList[0] 无 isSubStart → "
                       "子流程页「数据源」为空" % nm)
                if str(det.get("id")) in called:
                    BAD.append(msg + "（父流程 callActivity 契约没发对）")
                else:
                    WARN.append(msg + "（没有被任何主流程调用，孤儿子流程）")
            if not pj.get("subFlowSourceInfo"):
                # 提示而非失败：连线上模版自己也有 2/30 条是空的（父流程未再部署过），
                # 拿它当失败会假阳性。但**有值才算真的挂上了**，别忽略这一行。
                WARN.append("%s: 子流程缺 subFlowSourceInfo（「被以下工作流触发」为空）"
                            "—— 父流程重新保存/发布一次通常会回填" % nm)
            varf = {v.get("field") for v in (pj.get("variableList") or [])}
            if len(varf) != len(pj.get("variableList") or []):
                BAD.append("%s: 子流程 variableList 有重名参数 %s" % (nm, sorted(varf)))
    if n_sub:
        print("[check] 其中子流程 %d 条（检查「数据源 / 被谁触发」回填）" % n_sub)

    for w in WARN[:20]:
        print("  ! " + w)
    if len(WARN) > 20:
        print("  … 还有 %d 条提示" % (len(WARN) - 20))
    print("[check] 校验 %d 条流程，违例 %d 条 / 提示 %d 条" % (n, len(BAD), len(WARN)))
    for b in BAD[:60]:
        print("  ✗ " + b)
    if len(BAD) > 60:
        print("  … 还有 %d 条" % (len(BAD) - 60))
    if BAD:
        print("\n不合格 —— 按 references/node-contract.md 修好再交付。")
        return 1
    print("\n✓ 全部节点符合 node-contract.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
