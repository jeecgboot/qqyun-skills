# -*- coding: utf-8 -*-
"""按 references/node-contract.md 逐节点校验已建流程的 processJson。

用法：
    py scripts/check_node_contract.py --api-base URL --token TOK \
        --tenant-id N --app-id A [--only 流程名子串]
    py scripts/check_node_contract.py --self-test      # 不联网，自测校验器本身

退出码：0=全部通过；1=有违例（逐条打印）。

**为什么需要它**：save/deploy/ADDED 全绿、计数对得上，都不能证明节点键发对了——
本页第一版就是被这个坑掉的（批量建的 63 条流程，引擎认的键一条都没发出去）。

覆盖三块：节点键契约（check_flow / check_extra / check_link_src）、
**引用解析与画布可读性**（check_display：formTableId / funText 能否落到真实节点与表、
content 是不是原始 id）、**同名重复副本**。
"""
import argparse
import json
import re
import sys
import urllib.request

OK, BAD, WARN = [], [], []
SUB_DEFAULT_NOISE = []     # 「子流程内部节点未用设计器默认名」按流程收集，收尾合并成一条（只影响画布文案）

#: 本应用真实存在的表码集合，main() 联网时填；None＝没取到，跳过「表码属于本应用」这一项
#  （--self-test 就在自测里临时赋值，见 self_test）。
APP_CODES = None

#: 引擎保留的伪表码，不属于任何 desform，必须豁免
# 伪表码：不是工作表，但引擎/设计器要求原样出现在 formTableCode 上。
# `function-fun` / `function-record` 是**运算节点**的表码（`build_flows` 与 `miniflow_creator`
# 都按 `function-{funType}` 写，node-types 4.4.1 明确要求；写成别的值设计器解析不到字段源）。
# 2026-09-21 实测：不白名单它们，凡是带运算节点/统计条数的流程都会被误判成
# 「不是本应用的表码」——一个 9 条流程的应用报出 7 条假违例，把真违例埋了。
_PSEUDO_CODES = {"_variable_", "function-fun", "function-record"}


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
    # 子流程「本行」的 nodeId 是**父流程**那个 get_more 节点 —— 它不在本流程的节点树里，
    # 所以按 id 反查必然落空。更新对象指向它时是**合法**的，必须豁免，否则全量误报。
    own_row = {str(e.get("nodeId")) for e in (pj.get("formTableList") or [])
               if isinstance(e, dict) and e.get("isSubStart") and e.get("nodeId")}

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
                # 带 linkFormTableField ＝ 本来就是「明细取关联记录」，只是 selectType 漏写成 1（node-contract §1）。
                # 不带则是「工作表扫描 → 逐行子流程」（create-flow.md 组合 H 实证形态，开始节点无父记录），
                # selectType=1 合法 —— 早先版本对后者误报，见 2026-09-20 定时流程返工。
                nxt = n.get("childNode")
                if isinstance(nxt, dict) and nxt.get("type") == "callActivity" \
                        and nonempty(a.get("linkFormTableField")):
                    BAD.append("%s: 该 getMore 带 linkFormTableField（明细查询）却 selectType=%r 应为 3"
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
                # 真不变量（TaskNodeCreator:249-253）：多实例 collection 变量名由 attr.formTableSourceTaskId 拼，
                # 而变量是取多条节点按**自己的 activityId** 发布的（GetMoreRecordDelegate:142）。
                # 三者不一致 → ${flowUtil.stringToList(<id>_assigneeDataIdList)} 取不到 → PropertyNotFoundException。
                if a.get("formTableSourceTaskId") != obj.get("nodeId"):
                    BAD.append("%s: callActivity.attr.formTableSourceTaskId=%r 必须等于数据对象 nodeId=%r"
                               "（引擎用它拼 collection 变量名，不一致必 PropertyNotFoundException）"
                               % (nm, a.get("formTableSourceTaskId"), obj.get("nodeId")))
                if src.get("type") == "data_get_more" and sa.get("selectType") != 3 \
                        and nonempty(sa.get("linkFormTableField")):
                    BAD.append("%s: 数据对象指向的 getMore 带 linkFormTableField 却 selectType=%r 应为 3"
                               % (nm, sa.get("selectType")))
                # 多实例的 collection 由平台在**部署时**按源节点 id 生成成
                # `${flowUtil.stringToList(<源节点id>_assigneeDataIdList)}`（见该流程 processXml；
                # **processJson 里的 collection 是设计器默认残留，改它没用、看它会被带偏**）。
                # 不发布这个变量的 getMore → PropertyNotFoundException → 整条异步作业回滚。
                # 表现极具欺骗性：上游行已建出，只有该节点下游的写入永不发生、
                # 且日志里可能什么都看不到（2026-09-21 项目管理四版实测，selectType=4）。
                #
                # ⚠️ 合法值是 **1 和 3**，不是只有 1（2026-09-21 进销存 47 表应用端到端取证后收窄）。
                # 原先写死 `!= 1` 有两个问题：
                #  ① 与上面那条规则**直接打架** —— 上一条要求「带 linkFormTableField 时必须 =3」，
                #     这一条又要求「必须 =1」，凡是按 node-contract §7「取本单关联明细」建出来的节点
                #     都无法同时满足，必然报一堆无法消除的违例（实测 30 条），把真违例埋掉；
                #  ② 与真机不符 —— `build_flows` 的 `get_more(..., from_="start")` 恒产出 selectType=3，
                #     专项取证（一单三行、三个产品，`smoke_flows.py`）三行**全部**逐行记账成功，
                #     说明 selectType=3 同样发布了 collection 变量。collection 缺失时整条作业回滚，
                #     一行都不会落账，所以「三行全中」足以反证。
                # 源码定论（2026-09-21 对照 jeecg-boot-module-mindesflow-flowable）：
                #   GetMoreRecordDelegate：selectType 分三路取数（1=table 走 superQuery、
                #   3=link_field 走 getRecords(dataId)、4=plus 读新增节点 redis），随后在
                #   `if (isNotEmpty(records))` 分支里**对所有 selectType 统一** setVariable(
                #   "<activityId>_assigneeDataIdList", join(dataIds))；TaskNodeCreator 部署时
                #   固定生成 `${flowUtil.stringToList(<源节点id>_assigneeDataIdList)}`。
                #   → 真正的不变量是「取到 ≥1 行」，不是 selectType 的取值。取到 0 行 → 变量根本
                #   不设 → PropertyNotFoundException 回滚（#111 那次正是 selectType=4 取到 0 行）。
                #   SelectTypeEnums：table=1, more_data=2, link_field=3, plus=4。
                st = sa.get("selectType")
                if src.get("type") == "data_get_more" and st not in (1, 2, 3, 4):
                    BAD.append("%s: 多实例子流程的数据源 getMore.selectType=%r 不是合法枚举（1 表/2 多条/"
                               "3 关联字段/4 新增节点）—— 引擎取不到行就不会发布 "
                               "`<源节点id>_assigneeDataIdList`，运行时 PropertyNotFoundException 回滚"
                               % (nm, st))
                elif src.get("type") == "data_get_more" and st == 4:
                    WARN.append("%s: 多实例数据源来自新增节点（selectType=4）—— 该路径取到 0 行时不发布 "
                                "collection 变量、整条作业回滚（gotchas #111 实测）。确认上游新增节点"
                                "一定产出记录，或在前面加「统计条数>0」网关" % nm)
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

        if t == "data_get_one":
            # formTableId 必须是 form_<本节点 id>_<表 code>：设计器按它解析
            # 「这个节点取的是哪张表/哪一行」。落成 form_start_<表code> 时面板指错。
            want = "form_%s_%s" % (n.get("id"), a.get("formTableCode"))
            if a.get("formTableId") != want:
                BAD.append("%s: get_one.formTableId=%r 应为 %r"
                           % (nm, a.get("formTableId"), want))
            continue

        if t == "data_update":
            uf = a.get("updateFields") or n.get("updateFields")
            if not nonempty(uf):
                BAD.append("%s: data_update 缺 updateFields" % nm)
            for u in (uf if isinstance(uf, list) else []):
                if not isinstance(u, dict):
                    continue
                v = u.get("val")
                fld = u.get("field") or u.get("columnName") or "?"
                # val 是对象（formNodeType 系）＝变量引用：条目顶层必须带 valueType=3 + valType
                if isinstance(v, dict) and v.get("formNodeType"):
                    if u.get("valueType") != 3:
                        BAD.append("%s: updateFields[%s] 引用变量但 valueType=%r 应为 3"
                                   "（缺则设计器按固定字面量解析，值可能不落库，gotchas #58）"
                                   % (nm, fld, u.get("valueType")))
                    if u.get("valType") != "variable":
                        BAD.append("%s: updateFields[%s] 引用变量但 valType=%r 应为 'variable'"
                                   % (nm, fld, u.get("valType")))
                    if v.get("formNodeType") == "function":
                        for k in ("fieldType", "operationMode", "decimals"):
                            if not nonempty(v.get(k)):
                                BAD.append("%s: updateFields[%s] 的 val 缺 %s（运算结果引用不完整）"
                                           % (nm, fld, k))
                        is_date = v.get("fieldType") == "date" or "date" in str(u.get("type") or "")
                        if is_date and not nonempty(u.get("options")):
                            BAD.append("%s: updateFields[%s] 写日期字段缺 options.format"
                                       "（如 {'format': 'yyyy-MM-dd'}）" % (nm, fld))
            # 「更新对象」的来源（node-contract §9.1 ③④）：
            # search ⇒ formTableSourceTaskId 必须解析到**本流程里真实存在的 get_one**，
            # 且 formTableId = form_<该节点id>_<表code>。指错时查到一行、却更新另一行，
            # 而 save/deploy 全绿 —— 只有真跑才看得出。
            src_id = a.get("formTableSourceTaskId")
            # 先做一条**独立**的硬校验：更新对象来源的「类型」必须与上游节点真实类型一致。
            # ⚠️ 下面那两支只在「声明是 search」或「来源是触发行」时才校验，声明成别的值
            # （尤其把 get_one 误写成 getMore）时**整段被跳过** → 一路溜到线上：
            # 引擎不认这个键时**静默更新不到任何行**，save/deploy/其余条目全绿，
            # 只有真跑才看得出（2026-09-22 项目管理：子流程回填「上级任务」
            # 永远为空，而同一子流程里来源是 get_more 的那个 update 正常 —— 一个对一个错，
            # 把症状伪装成「流程跑了一半」）。
            # 口径：node-contract §5；builder `miniflow_creator.py` data_update 段实测注释
            # （线上 44 条：search 35 来自「取单条数据」/ plus 9 来自「新增记录」）。
            src_node = nadd.get(src_id) if src_id not in own_row else None
            if isinstance(src_node, dict):
                want_src = {"data_get_one": "search", "data_get_more": "getMore",
                            "data_add": "plus", "plus": "plus"}.get(src_node.get("type"))
                if want_src and a.get("formTableSourceNodeType") != want_src:
                    BAD.append("%s: data_update 的更新对象来源 %s 是 %s，"
                               "formTableSourceNodeType 应为 %r（现值 %r）→ 更新目标行指错、"
                               "运行时一行都更新不到（save/deploy/契约闸门全绿）"
                               % (nm, src_id, src_node.get("type"), want_src,
                                  a.get("formTableSourceNodeType")))
            if a.get("formTableSourceNodeType") == "search":
                is_own_row = str(src_id) in own_row
                sn = nadd.get(src_id)
                if not is_own_row and (not isinstance(sn, dict)
                                       or sn.get("type") != "data_get_one"):
                    BAD.append("%s: data_update.formTableSourceTaskId=%r 不是本流程里的 "
                               "get_one 节点（也不是子流程「本行」）→ 更新对象指错"
                               "（查到一行、却更新另一行）" % (nm, src_id))
                else:
                    want = "form_%s_%s" % (src_id, a.get("formTableCode"))
                    if a.get("formTableId") != want:
                        BAD.append("%s: data_update.formTableId=%r 应为 %r"
                                   % (nm, a.get("formTableId"), want))
            elif a.get("formTableSourceTaskId") in ("start", None, ""):
                # 反向：来源是触发行，但本流程里**明明有取同一张表的 get_one**
                # ⇒ 极可能本该更新「刚查到的那一行」。判 WARN 不判 BAD：审批流里
                # 「先查一眼、再更新触发的那一行」也合法。
                for sn in ns:
                    if (sn.get("type") == "data_get_one"
                            and (sn.get("attr") or {}).get("formTableCode")
                            == a.get("formTableCode")):
                        WARN.append("%s: data_update 的来源是触发行(start)，但本流程里有取"
                                    "同一张表 %s 的 get_one(%s) —— 确认是否本该更新那一行"
                                    % (nm, a.get("formTableCode"), sn.get("name")))
                        break
            continue

        if t == "function":
            fun = a.get("funType")
            if not nonempty(fun):
                BAD.append("%s: function 运算节点缺 attr.funType" % nm)
            # 「当前日期 / 当前时间」应直接引用系统变量 nowDate/nowTime，不该插 +0D 运算节点
            if fun == "date" and str(a.get("funText") or "").strip() in ("", "+0D", "-0D"):
                WARN.append("%s: 日期运算节点 funText=%r 等价于「当前日期」，应删掉它、直接引用系统变量"
                            "（nowDate/nowTime），见 gotchas #603" % (nm, a.get("funText")))
            for k, want in (("expressionType", "delegateExpression"),
                            ("expressionValue", "${functionDelegate}")):
                if a.get(k) != want:
                    BAD.append("%s: function 的 %s=%r 应为 %r" % (nm, k, a.get(k), want))
            dfv = a.get("dateFieldVal")
            if fun in ("date", "date-diff") and not nonempty(dfv):
                BAD.append("%s: funType=%s 缺 dateFieldVal（无基准日期 → 结果恒空，gotchas #41）"
                           % (nm, fun))
            if isinstance(dfv, dict) and not (dfv.get("formNodeType") and dfv.get("variableValue")):
                BAD.append("%s: dateFieldVal 缺 formNodeType/variableValue（应为三键系统变量对象，"
                           "如 {'formNodeType':'system','variableValue':'nowDate',"
                           "'variableName':'当前日期'}）" % nm)
            if fun in ("date", "date-diff") and not nonempty(a.get("dateFunctionFormat")):
                BAD.append("%s: funType=%s 缺 dateFunctionFormat"
                           "（如 {'argument':'date','result':'date','end':'2','out':'d'}）" % (nm, fun))
            for k in ("operationMode", "decimals"):
                if not nonempty(a.get(k)):
                    BAD.append("%s: function 缺 attr.%s" % (nm, k))
            for k in ("addable", "deletable", "error", "errorContent"):
                if k not in n:
                    BAD.append("%s: function 缺渲染键 %s（设计器画布显示不全）" % (nm, k))
            if not nonempty(n.get("content")):
                BAD.append("%s: function 的 content 为空 → 画布卡片空白" % nm)
            continue

        if t in ("databranch", "exclusive"):
            if not nonempty(n.get("conditionNodes")):
                BAD.append("%s: %s 缺 conditionNodes" % (nm, t))
            # 引擎 BaseDataDelegate.noDataExecute()（1081-1099）：取不到数据时只认下一节点
            # name.equals(MiniDesConstant.DATA_BRANCH_NAME="数据分支")，否则终止实例并标「已完成」。
            # 曾被误判成「无数据支不执行」（2026-09-21 源码定论）。
            if t == "databranch" and n.get("name") != "数据分支":
                BAD.append("%s: databranch 名字=%r，引擎只认「数据分支」—— 取不到数据时会直接终止实例" % (nm, n.get("name")))
            continue

        # 包含分支（= 明道云的「相容分支」）/ 并行分支。这两档以前**完全不校验**，
        # 于是「条件整组丢失」可以一路绿灯上真机（2026-09-20 实测：相容分支被建成
        # parallel，5 个分支条件全没了、变成无条件全跑，save/deploy/回读全绿）。
        if t in ("inclusive", "parallel"):
            cns = n.get("conditionNodes") or []
            if not cns:
                BAD.append("%s: %s 缺 conditionNodes" % (nm, t))
            for c in cns:
                ca = c.get("attr") or {}
                cname = c.get("name") or "?"
                cgs = ca.get("conditionGroup") or []
                ncond = sum(len(g.get("queryItems") or []) for g in cgs)
                if t == "parallel":
                    # 并行分支恒无条件；builder 把 conditionGroup 硬编码成 []，
                    # 所以这里非空 = 配置畸形（多半是构建期就丢了条件）。
                    if ncond:
                        BAD.append("%s: parallel 分支「%s」带了 %d 个条件——并行分支不支持条件，"
                                   "「满足条件的分支都走」请用 inclusive（相容/包含分支）"
                                   % (nm, cname, ncond))
                    continue
                # inclusive：① 不得用 isDefault 兜底，每条分支都要有明确条件；
                # ② 条件节点同级要带 branchForm+formTableCode（create-flow.md / gotchas #12）
                if c.get("isDefault") or str(ca.get("branchType")) == "2":
                    BAD.append("%s: inclusive 分支「%s」是 isDefault 兜底分支——inclusive "
                               "**不得用 isDefault 兜底**，每条分支都要有明确条件；"
                               "要兜底就写「为空」这类显式条件（create-flow.md 硬约束②/ gotchas #12）"
                               % (nm, cname))
                elif str(ca.get("branchType")) == "1" and not ncond:
                    BAD.append("%s: inclusive 分支「%s」branchType=1 但 conditionGroup 为空"
                               "（条件没落库）" % (nm, cname))
                if not nonempty(ca.get("branchForm")):
                    BAD.append("%s: inclusive 分支「%s」缺 branchForm"
                               "（gotchas #12 要求条件节点同级带 branchForm+formTableCode）"
                               % (nm, cname))
                for g in cgs:
                    for q in (g.get("queryItems") or []):
                        if isinstance(q.get("val"), (int, float)) \
                                and not isinstance(q.get("val"), bool):
                            WARN.append("%s: 分支「%s」条件 val=%r 是数字，"
                                        "gotchas #12 要求写成字符串" % (nm, cname, q.get("val")))
                        if q.get("name") is None:
                            WARN.append("%s: 分支「%s」条件 name=null，"
                                        "gotchas #12 要求填字段标签" % (nm, cname))
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
            # 按变量指人：fieldType 必须是**源控件族**（选人＝select-user…），
            # 写成他表字段自己的类型 link-field/link-record → 任务无人（待办「待签收」，gotchas #109）
            for g in (grp or []):
                if not isinstance(g, dict) or g.get("assigneeType") != "assigneeByVariable":
                    continue
                for vc in (g.get("variableContent") or []):
                    if isinstance(vc, dict) and str(vc.get("fieldType")) in ("link-field",
                                                                             "link-record"):
                        BAD.append("%s: %s 按变量指人（%s）的 fieldType=%r —— 应写源控件族"
                                   "（选人＝select-user…）；写 link-field 会指不到人（无人待办／待签收，"
                                   "gotchas #109）"
                                   % (nm, t, vc.get("fieldLabel"), vc.get("fieldType")))
            continue

    # 运算节点 virtual 表的登记顺序＝设计器对下游可引用数据源的解析顺序，须紧跟 start 表条目
    # （append 到下游条目之后 → 下游引用解析异常，gotchas #58/#59）
    ftl = pj.get("formTableList") or []
    si = next((i for i, e in enumerate(ftl) if e.get("nodeId") == "start"), None)
    fis = [i for i, e in enumerate(ftl) if e.get("nodeType") == "function"]
    if fis and si is not None and fis[0] != si + 1:
        BAD.append("%s: formTableList 中运算节点(%s) 登记在 index %d，须紧跟 start 条目(index %d)"
                   % (name, ftl[fis[0]].get("formTableCode") or "function", fis[0], si + 1))


SUB_DEFAULT_NAMES = {"data_get_one": "获取单条数据", "data_update": "更新记录",
                     "data_add": "添加记录", "databranch": "数据分支"}
NAME_ALLOW = {"系统", "流程参数"}
FIELD_CACHE = {}


def fields_of(api, tok, tid, app, code):
    """表 code -> {model: {name, type, src}}；src=link-record 的关联目标表 code"""
    if not code:
        return {}
    if code in FIELD_CACHE:
        return FIELD_CACHE[code]
    out = {}
    try:
        r = _get(api, tok, tid, app, "/desform/api/fields/%s?group=true" % code)
        for _, lst in (r.get("result") or {}).items():
            for f in lst:
                if isinstance(f, dict) and f.get("model"):
                    out[f["model"]] = {"name": f.get("name"), "type": f.get("type"),
                                       "src": (f.get("options") or {}).get("sourceCode")}
    except Exception:                                    # noqa: BLE001
        pass
    FIELD_CACHE[code] = out
    return out


def check_link_src(nm, pj, ctx):
    """关联记录条件：两侧关联的**目标表必须一致**，否则关联值永远匹配不上。
    2026-09-17 实测：出库产品明细.销售产品明细(->销售产品明细表) 对 库存实时统计.产品信息(->产品信息表)，
    设计器不报错、save/deploy 全绿，运行时恒查不到数据（用户截图才发现）。"""
    api, tok, tid, app = ctx
    for n in nodes_of(pj):
        if n.get("type") not in ("data_get_one", "data_get_more"):
            continue
        a = n.get("attr") or {}
        tf = fields_of(api, tok, tid, app, a.get("formTableCode"))
        for g in (a.get("searchFieldGroup") or []):
            for it in (g.get("queryItems") or []):
                v = it.get("val")
                if not isinstance(v, dict) or v.get("formNodeType") != "search":
                    continue
                tgd = tf.get(it.get("field")) or {}
                if tgd.get("type") != "link-record":
                    continue
                sf = fields_of(api, tok, tid, app, v.get("formTableCode"))
                sv = sf.get(v.get("variableValue")) or {}
                if tgd.get("src") and sv.get("src") and tgd["src"] != sv["src"]:
                    BAD.append("%s: 条件「%s」两侧关联目标表不同（%s ↔ %s）→ 关联值永远匹配不上"
                               % (nm, it.get("columnName") or it.get("field"),
                                  tgd["src"], sv["src"]))


def _in_gateway_branch(pj, node_id):
    """`node_id` 在不在**网关分支内**（相对主链路）。processJson 里链路走 `childNode`、分支走 `conditionNodes`。"""
    if not node_id:
        return False

    def walk(n, inside):
        while isinstance(n, dict) and n:
            if inside and str(n.get("id")) == str(node_id):
                return True
            for br in (n.get("conditionNodes") or []):
                if walk(br.get("childNode") or {}, True):
                    return True
            n = n.get("childNode") or {}
        return False

    return walk(pj if isinstance(pj, dict) else {}, False)


def check_extra(nm, det, pj, call_meta, def_keys, is_called):
    """2026-09-17 新增的三类静默缺陷（save/deploy 全绿、只有设计器/运行时才暴露）"""
    is_sub = (pj.get("attr") or {}).get("startType") == "subEvent"
    ns = nodes_of(pj)
    ftl = pj.get("formTableList") or []
    names = {n.get("name") for n in ns if n.get("name")}
    names |= {e.get("nodeName") for e in ftl if e.get("nodeName")}
    names |= NAME_ALLOW
    # ⚠️ **开始节点不在 nodes_of() 里**——它是 pj 自己，不是 childNode，所以它的名字
    # 天然进不了 names。可它恰恰是最常被当作值来源 `formNodeName` 的那个节点
    # （引擎对「输入行/起始行」就是这么序列化的）。原来只硬编码豁免字面量
    # 「工作表事件触发」（设计器给的默认名），**开始节点一旦改名就假阳性**：
    # 2026-09-21 四版把开始节点名改成了流程名，就报了「引用了本流程不存在的节点」。
    if pj.get("name"):
        names.add(pj["name"])
    if is_sub:
        names.add("子流程")          # 输入行在子流程内的合法别名
    ent = [e for e in ftl if e.get("isSubStart")]

    # ① processKey 必须已在引擎注册出定义，否则主流程调用必失败
    pk = det.get("processKey")
    if def_keys and pk and str(pk) not in def_keys:
        BAD.append("%s: processKey=%r 在引擎里没有已部署定义 → 父流程 callActivity 会抛 "
                   "FlowableObjectNotFoundException（须带 processKey=process<DBid> + "
                   "customProcessId=<DBid> 重存再 deploy，见 gotchas #47/#94）" % (nm, pk))

    # ② 值引用不得指向本流程不存在的节点（幽灵引用 → 下拉选不到 / 显示 [object Object]）
    ghost = {}

    def scan(v, where):
        if isinstance(v, dict):
            fn = v.get("formNodeName")
            if fn and fn not in names and not (not is_sub and fn == "工作表事件触发"):
                ghost.setdefault(fn, where)
            for vv in v.values():
                scan(vv, where)
        elif isinstance(v, list):
            for vv in v:
                scan(vv, where)

    # ⚠️ 只扫「筛选条件」和「更新值」：data_add 的 formModel 里写
    # `formNodeName:"工作表事件触发"` 是平台自身对输入行的序列化，运行时可用
    # （用户手工样板即如此、19:03 实跑成功），扫它全是假阳性。
    for n in ns:
        a = n.get("attr") or {}
        scan(a.get("searchFieldGroup"), "筛选条件")
        scan(a.get("updateFields"), "更新值")
    for g, where in sorted(ghost.items()):
        BAD.append("%s: %s 的值来源引用了本流程不存在的节点 %r（设计器下拉里没有这一项）"
                   % (nm, where, g))

    if not is_sub:
        return

    # ⑥ 子流程内引用「本流程输入行」的取值来源，必须是 search + 输入行登记的 nodeId。
    #    写成 table/start 时：设计器气泡显示「获取多条节点数据」（明明节点是取单条）。
    #    ⚠️ **例外**：父流程的取数节点若在网关分支里，search 形态运行时**取不到值**
    #    （子实例读不到分支执行的 redis 结果，2026-09-22 销售 R3 后端日志实证）→ 那种拓扑下 table/start 才是对的。
    #    按处数汇总成一条，避免一次刷出几百行。
    if ent and not (call_meta.get(str(det.get("id"))) or {}).get("nested"):
        sid, sname = ent[0].get("nodeId"), ent[0].get("nodeName")
        bad = []

        def scan_start(v, where, _k=[0]):
            if isinstance(v, dict):
                if v.get("formNodeType") == "table" and v.get("formNodeId") == "start":
                    _k[0] += 1
                    if len(bad) < 3:
                        bad.append("%s「%s」" % (where, v.get("variableName") or "?"))
                for vv in v.values():
                    scan_start(vv, where, _k)
            elif isinstance(v, list):
                for vv in v:
                    scan_start(vv, where, _k)

        total = [0]
        for n in ns:
            a2 = n.get("attr") or {}
            k = [0]
            scan_start(a2.get("searchFieldGroup"), "筛选条件", k)
            scan_start(a2.get("updateFields"), "更新值", k)
            total[0] += k[0]
        if total[0]:
            BAD.append("%s: 子流程内有 %d 处取值来源仍是 table/start，应为 "
                       "formNodeType='search' + formNodeId=%r（name=%r）—— 否则气泡显示"
                       "「获取多条节点数据」、运行时取不到值。例：%s"
                       % (nm, total[0], sid, sname, "、".join(bad)))

    # ⑥-b subFormTableObject 三处一致：父 callActivity / 子流程 start.attr / formTableList[0]
    #     （金标 example/主子流程配置示例.md 第 2、6 条）。start.attr 留空壳时引擎不知道「本行是哪张表」，
    #     子流程里 ref() 一律取空而 var() 正常 —— save/deploy/audit/verify 全绿（2026-09-22 进销存 R3）。
    if is_called and ent:
        sa = (pj.get("attr") or {}).get("subFormTableObject") or {}
        # ⚠️ 只报**提示**：已有两个真机应用（进销存 R2 19/19、销售 R3 4/4）在 start.attr 为空壳时
        #    冒烟照样全过，所以它不是「必错」条件；但 2026-09-22 进销存 R3 的记账子流程正是补上它之后
        #    才从「ref() 全取空、每次走 missing 分支」变正常。金标样例三处都有，建流程时按金标补齐。
        if not sa.get("nodeId"):
            WARN.append("%s: 子流程 start.attr.subFormTableObject 是空壳 —— 金标要求它与 formTableList[0]"
                        "（nodeId=%r）、父流程 callActivity 三处一致；空壳时曾出现「ref() 全取空、"
                        "记账子流程每次走 missing 分支」（进销存 R3）。重跑 build_flows --update 可补齐"
                        % (nm, ent[0].get("nodeId")))
        elif str(sa.get("nodeId")) != str(ent[0].get("nodeId")):
            BAD.append("%s: start.attr.subFormTableObject.nodeId=%r ≠ formTableList[0].nodeId=%r（三处必须一致）"
                       % (nm, sa.get("nodeId"), ent[0].get("nodeId")))

    # ③ 输入行登记名 = 父流程「调用节点」的名字（写 getMore 节点名 → 下拉显示成像表名）
    if is_called and ent:
        want = (call_meta.get(str(det.get("id"))) or {}).get("nodeName")
        # build_flows 有意把子流程侧登记名写成别名「子流程」（SUB_ROW_NAME，node-contract 9.1），
        # 校验器再按「父流程调用节点名」告警就是生成器与校验器互相打架的长期噪音（2026-09-22 销售管理 R2 22 条提示）
        if want and ent[0].get("nodeName") not in (want, "子流程"):
            WARN.append("%s: 输入行登记名=%r 应为父流程调用节点名 %r（下拉会显示成像表名）"
                        % (nm, ent[0].get("nodeName"), want))

    # ④ 子流程内部节点用设计器默认名（以用户手工配置的样板为准）
    odd = ["%s→%s" % (n.get("name"), SUB_DEFAULT_NAMES[n.get("type")])
           for n in ns
           if n.get("type") in SUB_DEFAULT_NAMES and n.get("name") != SUB_DEFAULT_NAMES[n.get("type")]]
    if odd:
        # 只影响设计器画布上的卡片文案，不影响运行。逐条刷会把真提示淹掉（进销存 R3 一次 28 行），
        # 所以收集起来在收尾合并成一条（2026-09-22）
        SUB_DEFAULT_NOISE.append("%s（%s）" % (nm, "; ".join(odd[:2])))


# ---------------------------------------------------------------------------
# 显示与引用完整性（2026-09-20 新增）
#
# **为什么需要它**：上面几类校验都过不了这一关 —— 当天曝出的 4 处缺陷
# （formTableList.formTableId 尾部缺表 code、运算节点 content 落成原始串、
# 数据源下拉出现解析不到的表）在 save/deploy/回读/计数上**全部是绿的**，
# 只有打开设计器看画布和下拉才暴露。
# 它们的共同结构特征是「字符串引用了不存在的对象」，纯结构即可判掉：
#   ① 引用解析 —— 每个 form_<节点id>_<表code> / funText 都要能落到本流程真实存在的节点与表上
#   ② 可读性  —— 画布上给人看的串不能是原始 id / hex / 字段名本身（#103）
#   ③ 完整性  —— formTableList 与节点双向对得上（悬空登记、漏登记都报）
#   ④ 消息绑定 —— {{<hash>.<字段名>}} 必须在 jsonContext 里有绑定（否则消息内容空，见 #55）
# ---------------------------------------------------------------------------
FORM_REF = re.compile(r"^form_([A-Za-z0-9]+?)_(.+)$")
HEX32 = re.compile(r"^[0-9a-f]{32}$")
# 引擎给自己登记的「流程参数」伪表，固定形态：
# {"formTableCode":"_variable_","formTableId":"variable","nodeId":"processVariable","nodeType":"variable"}
# 它不对应任何节点，也不是 form_<id>_<code> 形态 —— 必须豁免，否则每条流程都误报（实测 8/9 条都有）。
RESERVED_FTL_IDS = ("processVariable",)
# 反向登记检查只覆盖 getMore：实测 9 条流程里 data_update 一条都没登记
# （新增目标客户有 7 个 data_update 节点、登记表里 0 条），所以「没登记」不是缺陷。
DATA_NODES = ("data_get_more", "data_get_one")


def bad_display_content(c, fun_text):
    """#103 的四条判据（空串已由 check_flow 报，这里不重复）。返回原因或 None。"""
    s = str(c or "").strip()
    if not s:
        return None
    if s.startswith("form_") or s.startswith("task"):
        return "以 form_/task 开头（原始 id 未翻译）"
    if HEX32.match(s):
        return "纯 32 位 hex"
    if nonempty(fun_text) and s == str(fun_text).strip():
        return "与 attr.funText 相等（未写语义名）"
    return None


def why_ftid(v, ids, codes, foreign_ok=False):
    """`form_<节点id>_<表code>` 能否解析到真实对象。返回原因或 None。

    foreign_ok：子流程的登记条目本就指向**父流程**的 getMore 节点
    （isSubStart=true / level='1'，父流程侧同一节点登记为 level='2'），
    所以子流程里「节点 id 不在本流程」是正常形态，不是悬空 —— 只跳过这一档，
    形态档（尾部缺表 code）仍要判，那才是 2026-09-20 的真缺陷。
    """
    s = str(v or "")
    if not s.startswith("form_"):
        return "不以 form_ 开头"
    if s.endswith("_"):
        return "尾部缺表 code（形态是 form_<节点id>_）"
    m = FORM_REF.match(s)
    if not m:
        return "不是 form_<节点id>_<表code> 形态"
    nid, code = m.group(1), m.group(2)
    if foreign_ok:
        return None
    if nid not in ids:
        return "节点 id %r 在本流程里不存在" % nid
    if codes and code not in codes:
        return "表 code %r 不是本流程引用过的表" % code
    return None


def _code_of_form_ref(s):
    """`form_<节点id>_<表码>` → `<表码>`；不是这个形态返回 None。"""
    s = str(s or "")
    if not s.startswith("form_"):
        return None
    rest = s[len("form_"):]
    i = rest.find("_")
    return rest[i + 1:] if i >= 0 else None


def ref_codes(pj):
    """产出流程里**每一处**表码引用 `(位置描述, 表码)`。

    为什么单列一个函数：`check_display` 原来只从 `attr.formTableCode` /
    `subFormTableObject.formTableCode` / `formTableList` 三处收表码，**收不到条件项里的**。
    而那正是 2026-09-21 四版栽的地方：`attr.searchFieldGroup[].queryItems[].val` 是**独立的小对象**，
    跨应用/跨版本整体克隆节点时，外层 `formTableCode` 被重映射了，`val.formTableCode` 还留着
    上一个应用的表码（实测残留 `mj3_proj`）。表码指向不存在的表 → 那个变量解析不出来 →
    条件匹配 **0 条** → 「获取多条」取到 0 行 → 多实例子流程**一个实例都不起**，
    **日志里却一条错都不报**（对比：变量名本身不存在会抛 PropertyNotFoundException，那反而好查）。
    """
    out = []
    ra = pj.get("attr") or {}
    for k in ("formTableCode", "formTableMainCode", "linkFormTableCode", "formTableSourceCode"):
        if nonempty(ra.get(k)):
            out.append(("流程 attr.%s" % k, str(ra[k])))
    if nonempty(ra.get("formTableSourceId")):
        c = _code_of_form_ref(ra["formTableSourceId"])
        if c:
            out.append(("流程 attr.formTableSourceId", c))
    for e in (pj.get("formTableList") or []):
        if not isinstance(e, dict):
            continue
        for k in ("formTableCode", "formTableMainCode"):
            if nonempty(e.get(k)):
                out.append(("formTableList[%s].%s" % (e.get("nodeId"), k), str(e[k])))
    for n in nodes_of(pj):
        a = n.get("attr") or {}
        nm = n.get("name") or n.get("type") or "?"
        for k in ("formTableCode", "formTableMainCode", "linkFormTableCode",
                  "formTableSourceCode"):
            if nonempty(a.get(k)):
                out.append(("%s.attr.%s" % (nm, k), str(a[k])))
        for k in ("formTableSourceId", "formTableId"):
            c = _code_of_form_ref(a.get(k))
            if c:
                out.append(("%s.attr.%s" % (nm, k), c))
        obj = a.get("subFormTableObject")
        if isinstance(obj, dict):
            if nonempty(obj.get("formTableCode")):
                out.append(("%s.attr.subFormTableObject.formTableCode" % nm,
                            str(obj["formTableCode"])))
            c = _code_of_form_ref(obj.get("formTableId"))
            if c:
                out.append(("%s.attr.subFormTableObject.formTableId" % nm, c))
        # ↓ 条件项：**这一层最容易漏**，见函数头注释
        for g in (a.get("searchFieldGroup") or []):
            if not isinstance(g, dict):
                continue
            for qi, it in enumerate(g.get("queryItems") or []):
                if not isinstance(it, dict):
                    continue
                v = it.get("val")
                if not isinstance(v, dict):
                    continue
                col = it.get("columnName") or it.get("name") or "?"
                if nonempty(v.get("formTableCode")):
                    out.append(("%s 条件「%s」的 val.formTableCode" % (nm, col),
                                str(v["formTableCode"])))
                c = _code_of_form_ref(v.get("formTableId"))
                if c:
                    out.append(("%s 条件「%s」的 val.formTableId" % (nm, col), c))
    return out


def check_codes(name, pj, app_codes):
    """表码必须属于本应用。`app_codes` 为 None（没联网取到）时跳过。"""
    if not app_codes:
        return
    for where, code in ref_codes(pj):
        if code in app_codes or code in _PSEUDO_CODES:
            continue
        BAD.append(
            "%s: %s = %r —— 不是本应用的表码。跨版本/跨应用整体搬运流程定义时，"
            "**条件项里 val 是独立小对象，不会跟外层一起被重映射**；表码指向不存在的表 → "
            "变量解析不出来 → 条件匹配 0 条 → 「获取多条」取到 0 行 → 多实例子流程一个实例都不起，"
            "**日志里不报错**（gotchas #111）" % (name, where, code))


def check_display(name, pj):
    ns = nodes_of(pj)
    ids = {str(n.get("id")) for n in ns if n.get("id")}
    ids.add("start")
    ftl = pj.get("formTableList") or []

    # 本流程引用过的表 code 全集，供「引用能否解析」比对
    codes = set()
    ra = pj.get("attr") or {}
    if nonempty(ra.get("formTableCode")):
        codes.add(str(ra["formTableCode"]))
    for n in ns:
        a = n.get("attr") or {}
        for k in ("formTableCode", "formTableMainCode", "linkFormTableCode"):
            if nonempty(a.get(k)):
                codes.add(str(a[k]))
        obj = a.get("subFormTableObject")
        if isinstance(obj, dict) and nonempty(obj.get("formTableCode")):
            codes.add(str(obj["formTableCode"]))
    for e in ftl:
        for k in ("formTableCode", "formTableMainCode"):
            if nonempty(e.get(k)):
                codes.add(str(e[k]))

    # ① 引用解析 + ② 可读性：节点自身带的引用与显示串
    for n in ns:
        t = n.get("type")
        a = n.get("attr") or {}
        nm = "%s / %s" % (name, n.get("name") or t)
        if nonempty(a.get("formTableId")):
            why = why_ftid(a["formTableId"], ids, codes)
            if why:
                BAD.append("%s: attr.formTableId=%r 无法解析 —— %s"
                           % (nm, a["formTableId"], why))
        if t == "function":
            # funText 只有在「统计条数」(funType=record) 时才是 `form_<节点id>_<表code>` 引用；
            # 四则/函数运算 (funType=fun/number) 的 funText 是**表达式**（`{{<hash>.<model>}}-{{…}}`），
            # 拿它当引用去解析必然「不以 form_ 开头」—— 2026-09-21 进销存实测稳定误报 7~11 条，
            # 直接废掉了「违例 0」这个验收口径。
            ft = str(a.get("funText") or "")
            if nonempty(ft) and (a.get("funType") == "record" or ft.startswith("form_")):
                why = why_ftid(a["funText"], ids, codes)
                if why:
                    BAD.append("%s: attr.funText=%r 无法解析 —— %s（#102）"
                               % (nm, a["funText"], why))
            why = bad_display_content(n.get("content"), a.get("funText"))
            if why:
                BAD.append("%s: content=%r → 设计器画布显示原始串（%s，#103）"
                           % (nm, n.get("content"), why))
        elif t in ("edit", "approver") and nonempty(a.get("funText")):
            why = why_ftid(a["funText"], ids, codes)
            if why:
                BAD.append("%s: attr.funText=%r 无法解析 —— %s" % (nm, a["funText"], why))

    # ④ 消息节点：{{<hash>.<字段名>}} 必须在 jsonContext 里有绑定。
    # 2026-09-20 实测：只写 templateContext、不写 jsonContext，save/deploy/回读全绿、
    # 消息也照发，但占位符处**全空** —— 只有消息发出去才暴露（#55 / gotchas 4 键）。
    for n in ns:
        if n.get("type") != "message_system":
            continue
        a = n.get("attr") or {}
        nm = "%s / %s" % (name, n.get("name") or "消息")
        body = a.get("templateContext")
        if not nonempty(body):
            BAD.append("%s: 消息节点缺 attr.templateContext（正文键；DSL 的 noticeContent "
                       "落库到它，写 noticeContent 服务端双存且不生效）" % nm)
        for k in ("type", "title", "receiveType"):
            if not nonempty(a.get(k)):
                BAD.append("%s: 消息节点缺 attr.%s" % (nm, k))
        if not nonempty(a.get("toUserIds")) and not nonempty(n.get("toUserIds")):
            BAD.append("%s: 消息节点缺 toUserIds（收件人为空）" % nm)
        jc = a.get("jsonContext")
        jc = jc if isinstance(jc, dict) else {}
        for h in sorted(set(re.findall(r"\{\{([^.}]+)\.", str(body or "")))):
            if h.startswith("_"):
                continue            # 内置命名空间：{{_FW_NODE_NAME.节点名称}} 之类，无需绑定
            if h not in jc:
                BAD.append("%s: 正文占位符 {{%s.*}} 在 jsonContext 里没有绑定 → "
                           "消息照发但该处为空（#55 的键契约）" % (nm, h))
        for h in sorted(jc):
            if h not in str(body or ""):
                WARN.append("%s: jsonContext 的 %s 在正文里没被引用（多余绑定）" % (nm, h))

    # 子流程：登记条目可以指向父流程的 getMore 节点，见 why_ftid 的 foreign_ok
    is_sub = str(pj.get("startType") or "") == "subEvent"

    # ③ 完整性：formTableList 每条都要能对上一个真实节点，且 id 段与 nodeId 一致
    reg = set()
    for i, e in enumerate(ftl):
        nid = str(e.get("nodeId") or "")
        if not nid:
            BAD.append("%s: formTableList[%d] 无 nodeId" % (name, i))
            continue
        if nid in RESERVED_FTL_IDS or str(e.get("nodeType")) == "variable":
            continue                       # 引擎自己的「流程参数」伪表条目
        reg.add(nid)
        # 子流程登记父流程节点时，level='1' 那条是「输入行」；父流程侧同 id 另有 level='2'
        foreign = is_sub or bool(e.get("isSubStart"))
        if nid not in ids and not foreign:
            BAD.append("%s: formTableList[%d].nodeId=%r 在本流程里不存在（悬空登记）"
                       % (name, i, nid))
        if not nonempty(e.get("formTableId")):
            continue
        why = why_ftid(e["formTableId"], ids, codes, foreign_ok=foreign)
        if why:
            BAD.append("%s: formTableList[%d] nodeId=%s formTableId=%r 无法解析 —— %s（#102）"
                       % (name, i, nid, e["formTableId"], why))
            continue
        m = FORM_REF.match(str(e["formTableId"]))
        if m and m.group(1) != nid:
            BAD.append("%s: formTableList[%d] nodeId=%s 与 formTableId 的节点段 %r 不一致"
                       "（设计器按 sourceTaskId 反查会命中不到，#102）"
                       % (name, i, nid, m.group(1)))

    # ③ 反向：带表上下文的数据节点必须有登记条目（否则下游下拉里找不到这个数据源）
    for n in ns:
        t = n.get("type")
        a = n.get("attr") or {}
        if t not in DATA_NODES:
            continue
        nid = str(n.get("id") or "")
        if not nid or nid in reg:
            continue
        if not nonempty(a.get("formTableCode")):
            continue                    # subEvent 根表 code 为空等情形，登记 code 另有来源
        WARN.append("%s: %s(id=%s) 带 formTableCode=%r 但 formTableList 无登记条目"
                    % (name, n.get("name") or t, nid, a.get("formTableCode")))


def duplicate_name_bad(recs, only=None):
    """同名重复副本：`query_flow` 按名只返回**最新**一条，副本会让「我修的那条」和
    「校验器看的那条」不是同一个 —— 违例怎么改都下不去（2026-09-20 实测）。"""
    out = []
    byname = {}
    for x in recs:
        nm = str(x.get("processName") or "")
        if not nm or (only and only not in nm):
            continue
        byname.setdefault(nm, []).append(str(x.get("id")))
    for nm, xs in sorted(byname.items()):
        if len(xs) > 1:
            out.append("%s: 有 %d 个同名副本 id=%s —— 按名查询只会拿到最新那条，"
                       "先把副本删掉再改，否则改的和验的不是同一个"
                       % (nm, len(xs), ",".join(xs)))
    return out


# ---------------------------------------------------------------------------
# 自测：拿「已知坏」的合成 processJson 打一遍 check_display。
# 为什么要有：这几类缺陷全是**全绿但坏**（save/deploy/回读都过），
# 校验器本身如果不自测，它退化成永远返回 0 违例也没人看得出来 ——
# 那正是 2026-09-20 那批缺陷能一路交付的原因。
# ---------------------------------------------------------------------------
def _fx_clean():
    return {
        "startType": "event",
        "attr": {"formTableCode": "tAAA"},
        "childNode": {
            "id": "task1", "name": "获取单条数据", "type": "data_get_more",
            "attr": {"formTableId": "form_start_tAAA", "formTableCode": "tAAA"},
        },
        "formTableList": [
            {"nodeId": "start", "nodeType": "table",
             "formTableId": "form_start_tAAA", "formTableCode": "tAAA"},
            # 引擎保留的「流程参数」伪表：既不是 form_ 形态、也没有对应节点，必须豁免
            {"nodeId": "processVariable", "nodeType": "variable",
             "formTableId": "variable", "formTableCode": "_variable_"},
            {"nodeId": "task1", "nodeType": "getMore",
             "formTableId": "form_task1_tAAA", "formTableCode": "tAAA"},
        ],
    }


def _fn(pj, **kw):
    """把 task1 变成运算节点。"""
    n = pj["childNode"]
    n["type"] = "function"
    n.update(kw)
    return pj


def _mut_update_srctype(pj, declared="getMore"):
    """把流程改成「取单条数据 → 更新该行」：来源节点 task1 是 data_get_one。

    `declared` 是给更新节点填的 formTableSourceNodeType —— 填 "getMore" 即缺陷形态
    （应为 "search"），填 "search" 是正确形态（用于「不得误报」回归）。
    """
    pj["childNode"]["type"] = "data_get_one"        # 来源 = 取单条数据
    pj["childNode"]["attr"]["formTableId"] = "form_task1_tAAA"
    pj["childNode"]["childNode"] = {
        "id": "task2", "name": "更新本条任务父级节点", "type": "data_update",
        "attr": {"formTableSourceTaskId": "task1", "formTableSourceNodeType": declared,
                 "formTableCode": "tAAA", "formTableId": "form_task1_tAAA",
                 "updateFields": [{"field": "link_record_1", "valueType": 3,
                                   "valType": "variable", "fieldType": "link-record",
                                   "val": {"formNodeId": "task1", "formNodeType": "getMore",
                                           "variableName": "记录id", "variableValue": "_id"}}]}}
    return pj


SELF_TESTS = [
    ("databranch 名字不是「数据分支」（引擎按名放行）",
     lambda pj: pj["childNode"].update({"type": "databranch", "name": "数据判断",
                                        "conditionNodes": [{"name": "有数据"}, {"name": "无数据"}]}),
     "引擎只认「数据分支」"),
    ("callActivity.formTableSourceTaskId ≠ 数据对象 nodeId",
     lambda pj: pj["childNode"].__setitem__("childNode", {
         "id": "task2", "name": "调子流程", "type": "callActivity",
         "attr": {"isMulti": True, "customProcessId": "1", "formTableSourceTaskId": "start",
                  "formTableId": "form_task1_tAAA",
                  "subFormTableObject": {"nodeId": "task1", "nodeType": "getMore", "formTableCode": "tAAA"}}}),
     "必须等于数据对象 nodeId"),
    ("formTableList.formTableId 尾部缺表 code（#102）",
     lambda pj: pj["formTableList"][2].__setitem__("formTableId", "form_task1_"),
     "尾部缺表 code"),
    ("节点 attr.formTableId 尾部缺表 code",
     lambda pj: pj["childNode"]["attr"].__setitem__("formTableId", "form_start_"),
     "尾部缺表 code"),
    ("formTableId 指向不存在的节点",
     lambda pj: pj["formTableList"][2].__setitem__("formTableId", "form_task99_tAAA"),
     "在本流程里不存在"),
    ("formTableList 悬空登记（nodeId 不存在）",
     lambda pj: pj["formTableList"].append(
         {"nodeId": "task99", "nodeType": "getMore", "formTableId": "form_task99_tAAA"}),
     "悬空登记"),
    ("运算节点 content 是 funText 原文（#103）",
     lambda pj: _fn(pj, content="form_task1_tAAA", attr={"funText": "form_task1_tAAA"}),
     "画布显示原始串"),
    ("运算节点 content 是 32 位 hex（#103）",
     lambda pj: _fn(pj, content="8f26329d394e6507ceca72d1be28b61c",
                    attr={"funText": "form_task1_tAAA"}),
     "画布显示原始串"),
    ("消息占位符未绑定 jsonContext（#55）",
     lambda pj: pj["childNode"].update({
         "type": "message_system",
         "attr": {"type": "system", "title": "通知", "receiveType": "user",
                  "toUserIds": ["u1"],
                  "templateContext": "{{8f26329d394e6507ceca72d1be28b61c.机会名称}}已签订",
                  "jsonContext": {}}}),
     "没有绑定"),
    ("消息节点收件人为空",
     lambda pj: pj["childNode"].update({
         "type": "message_system",
         "attr": {"type": "system", "title": "通知", "receiveType": "user",
                  "templateContext": "无占位符"}}),
     "缺 toUserIds"),
    # 2026-09-21 四版真正的病根：外层是 tAAA，条件项 val 里却留着别的应用的表码。
    # 全绿但坏：save/deploy/回读都过，跑起来子流程一个实例都不起，日志里一条错都没有。
    ("条件项 val.formTableCode 是别的应用的表码",
     lambda pj: pj["childNode"]["attr"].update({
         "searchFieldGroup": [{
             "id": "g1", "matchType": "AND",
             "queryItems": [{
                 "rule": "eq", "ruleName": "等于", "valType": "variable", "valueType": 2,
                 "name": "项目", "columnName": "项目", "type": "link-record",
                 "field": "link_record_1_1",
                 "val": {"formNodeId": "start", "formNodeType": "table",
                         "variableName": "记录id", "variableValue": "_id",
                         "formTableCode": "tZZZ"}}]}]}),
     "不是本应用的表码"),
    # 2026-09-22 项目管理真正的病根：更新对象来源是「取单条数据」(data_get_one)，
    # 却声明成 getMore。引擎不认这个键时**静默更新不到任何行** —— 子流程回填「上级任务」
    # 永远为空，而同一子流程里来源是 get_more 的那个 update 正常，把症状伪装成
    # 「流程跑了一半」；save/deploy/契约闸门全绿。
    ("data_update 来源是 get_one 却声明成 getMore（静默更新不到任何行）",
     _mut_update_srctype,
     "formTableSourceNodeType 应为 'search'"),
]


def self_test():
    import copy as _copy
    fails = []

    global APP_CODES
    save, save_codes = (list(BAD), list(WARN)), APP_CODES
    APP_CODES = {"tAAA"} | set(_PSEUDO_CODES)     # 合成样例里合法的表码
    try:
        del BAD[:], WARN[:], SUB_DEFAULT_NOISE[:]
        check_display("干净样例", _fx_clean())
        check_codes("干净样例", _fx_clean(), APP_CODES)
        if BAD:
            fails.append("干净样例被误报: %s" % BAD)
        if WARN:
            fails.append("干净样例有提示（应为空）: %s" % WARN)
    finally:
        pass

    for label, mutate, want in SELF_TESTS:
        del BAD[:], WARN[:]
        pj = _copy.deepcopy(_fx_clean())
        mutate(pj)          # 就地改；不要用返回值（__setitem__ 返回 None）
        check_display("合成样例", pj)
        check_codes("合成样例", pj, APP_CODES)
        try:                       # 节点键契约（callActivity / databranch 等）在 check_flow 里；夹具是最小样例，允许它多报
            check_flow("合成样例", pj)
        except Exception as ex:    # noqa: BLE001
            BAD.append("check_flow 抛异常: %r" % ex)
        if not any(want in b for b in BAD):
            fails.append("没抓出「%s」（期望含 %r，实际 BAD=%s）" % (label, want, BAD))

    # 四则运算节点：funText 是表达式，不得按「表引用」判（2026-09-21 误报回归）
    del BAD[:], WARN[:]
    pj = _fn(_copy.deepcopy(_fx_clean()), content="到货数量 - 不合格数量")
    pj["childNode"]["attr"] = {"funType": "fun", "funText": "{{aaa111.number_1}}-{{bbb222.number_2}}"}
    pj["formTableList"] = pj["formTableList"][:2]
    check_display("四则运算样例", pj)
    if any("funText" in b for b in BAD):
        fails.append("四则运算节点的表达式被当成表引用误报: %s" % BAD)

    # data_update 来源类型**写对**时不得误报（上面那条新检查的反向回归）
    del BAD[:], WARN[:]
    pj = _mut_update_srctype(_copy.deepcopy(_fx_clean()), declared="search")
    check_flow("来源类型正确样例", pj)
    if any("formTableSourceNodeType" in b for b in BAD):
        fails.append("来源类型正确（search）却被误报: %s" % BAD)

    # 同名副本
    del BAD[:], WARN[:]
    got = duplicate_name_bad([{"processName": "A", "id": "1"},
                              {"processName": "A", "id": "2"},
                              {"processName": "B", "id": "3"}])
    if len(got) != 1 or "同名副本" not in got[0]:
        fails.append("没抓出同名副本: %s" % got)

    del BAD[:], WARN[:]
    BAD.extend(save[0])
    WARN.extend(save[1])
    APP_CODES = save_codes

    for label, _, _ in SELF_TESTS:
        print("  %s %s" % ("✗" if any(label in f for f in fails) else "✓", label))
    print("  %s 干净样例不误报" % ("✗" if any("干净样例" in f for f in fails) else "✓"))
    print("  %s 四则运算节点不误报" % ("✗" if any("四则运算" in f for f in fails) else "✓"))
    print("  %s 同名重复副本" % ("✗" if any("同名副本" in f for f in fails) else "✓"))
    if fails:
        print("\n自测失败：")
        for f in fails:
            print("  ✗ " + f)
        return 1
    print("\n✓ 自测通过：%d 类已知缺陷全部能抓出，且干净样例不误报" % (len(SELF_TESTS) + 1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true",
                    help="不联网：拿合成样例自测校验器本身能抓出已知缺陷")
    ap.add_argument("--api-base")
    ap.add_argument("--token")
    ap.add_argument("--tenant-id")
    ap.add_argument("--app-id")
    ap.add_argument("--only", default=None)
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    miss = [k for k in ("api_base", "token", "tenant_id", "app_id") if not getattr(a, k)]
    if miss:
        ap.error("缺少参数 %s（或改用 --self-test）"
                 % ", ".join("--" + m.replace("_", "-") for m in miss))

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
    call_meta = {}      # 子流程 id -> 父流程调用节点名（拷自 2026-09-17 用户手工样板）
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
                    a0 = n0.get("attr") or {}
                    cp = a0.get("customProcessId")
                    if cp:
                        called.add(str(cp))
                        call_meta.setdefault(str(cp), {
                            "nodeName": n0.get("name"),
                            "mainName": x.get("processName"),
                            # 取数节点在网关分支里 → 子流程取值来源该保持 table/start（见规则 ⑥ 的例外）
                            "nested": _in_gateway_branch(
                                pj0, ((a0.get("subFormTableObject") or {}).get("nodeId")
                                      or a0.get("formTableSourceTaskId"))),
                        })

    # 引擎里已部署的定义 key 集合（2026-09-17 新增）。
    # API 建的流程若 processKey 与部署 key 对不上，引擎里就是「没有定义」，
    # 主流程一调到它必抛 FlowableObjectNotFoundException（实测：23 条子流程踩坑）。
    DEF_KEYS = set()
    try:
        dd = _get(a.api_base, a.token, a.tenant_id, a.app_id,
                  "/act/process/list?pageNo=1&pageSize=500")
        dr = dd.get("result")
        drecs = dr.get("records") if isinstance(dr, dict) else dr
        for x2 in (drecs or []):
            if x2.get("key"):
                DEF_KEYS.add(str(x2.get("key")))
    except Exception:                                    # noqa: BLE001
        pass
    if not DEF_KEYS:
        print("  ! 未取到引擎定义列表，跳过「定义 key 已注册」检查")

    # 本应用真实表码（用于「表码属于本应用」检查，见 check_codes）。
    global APP_CODES
    try:
        # ⚠️ 这个接口返回的是**整个租户**的应用（实测：一个租户 5 个应用、255 张表，
        # 本应用只占 24 张）。不按 app 过滤的话，上个版本的表码（mj3_proj 之类）
        # 也会被当成合法 —— 这项检查就白做了。必须按 apps[].id == 本应用 id 收窄。
        fd = _get(a.api_base, a.token, a.tenant_id, a.app_id,
                  "/online/lowApp/miniflow/tenantAppFormList?tenantId=%s" % a.tenant_id)
        codes = set()
        for ap0 in ((fd.get("result") or {}).get("apps") or []):
            if str(ap0.get("id")) != str(a.app_id):
                continue
            for f0 in (ap0.get("desforms") or []):
                if f0.get("code"):
                    codes.add(str(f0["code"]))
        APP_CODES = codes or None
    except Exception:                                    # noqa: BLE001
        APP_CODES = None
    if not APP_CODES:
        print("  ! 未取到应用表清单，跳过「表码属于本应用」检查")
    else:
        print("[check] 本应用表码 %d 个" % len(APP_CODES))

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
        check_extra(nm, det, pj, call_meta, DEF_KEYS, str(x.get("id")) in called)
        check_link_src(nm, pj, (a.api_base, a.token, a.tenant_id, a.app_id))
        check_display(nm, pj)
        check_codes(nm, pj, APP_CODES)

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
                # ⚠️ 旧提示语写「父流程重新保存/发布一次通常会回填」—— gotchas ③ 实测**不成立**
                #    （20 条父流程全部重发后提示从 23 涨到 26），2026-09-22 销售管理又踩一次：
                #    重存父流程后本行提示原样留着。正确修法是**显式回填**：
                #    pj['subFlowSourceInfo'] = [{mainProcessId, mainProcessName, nodeName}] 再 save+deploy，
                #    且必须是该子流程**最后一次**保存（子流程之后再被存一次就又清空）。
                WARN.append("%s: 子流程缺 subFlowSourceInfo（「被以下工作流触发」为空）"
                            "—— 需**显式回填**后 save+deploy（重存父流程不会补，见 gotchas ③）；"
                            "回填必须放在该子流程最后一次保存" % nm)
            varf = {v.get("field") for v in (pj.get("variableList") or [])}
            if len(varf) != len(pj.get("variableList") or []):
                BAD.append("%s: 子流程 variableList 有重名参数 %s" % (nm, sorted(varf)))

    BAD.extend(duplicate_name_bad(recs, a.only))

    if n_sub:
        print("[check] 其中子流程 %d 条（检查「数据源 / 被谁触发」回填）" % n_sub)

    if SUB_DEFAULT_NOISE:
        WARN.append("%d 条子流程的内部节点未用设计器默认名（只影响画布文案，不影响运行）：%s%s"
                    % (len(SUB_DEFAULT_NOISE), "、".join(x.split("（")[0] for x in SUB_DEFAULT_NOISE[:6]),
                       " 等" if len(SUB_DEFAULT_NOISE) > 6 else ""))
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
