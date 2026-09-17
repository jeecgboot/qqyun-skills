# -*- coding: utf-8 -*-
"""批量建流程 —— 从一个声明式 flows.py 建完全部流程（规格驱动，从零生成，不需要任何既有应用作参考）。

    python build_flows.py --api-base URL --token TOKEN --tenant-id N --app-id A \
        --spec /path/flows.py [--only 流程名] [--dry-run]

`flows.py` 只写业务规格（`from flow_dsl import *` + `FLOWS = [...]`），**不写引擎代码**。
字段/表名一律中文，引擎自己换 code / model——见 `flow_dsl.py` 顶部。

## 为什么要有这个脚本（2026-09-15 实测）

63 条流程那一轮跑了 **55 分钟且 0 产出**，两个原因：
1. **逐条一轮的散打做法**：63 条 × ~44KB 节点配置写进模型输出 → 撞 32000 输出上限直接崩。
2. 全链路路径（`fast-full-chain.md`）当时**不指向 `batch-flows.md`**，agent 55 分钟后才偶然翻到。

本脚本把「机制」全部固化，agent 只剩「把规格翻译成 DSL」这一件不可避免的事：
  · 中文名 → code/model 解析（一次拉全，落盘复用）
  · **先子流程后主流程**：子流程 save → deploy → 注册 → 补 customProcessId → 再 deploy → 校验
  · 主流程的 `call_sub` 自动绑到**新建的**子流程 id
  · 幂等：同名已存在则跳过（可断点续跑）
  · 大 JSON 只在脚本内流转，**不进模型输出**；只打 `OK:` / `FAIL:`

2026-09-16 补齐 5 处「静默建错」（详见 `references/batch-flows.md`）：
  · 触发事件类型发的是数字键 `tableEventType` → 改成引擎真的读的字符串 `startEventType`
  · 触发条件 `startCondition` 从未下传 → 现在由 `flow(cond=[...])` 生成
  · `databranch` / `function` 两种节点没有分发 → 现在 `data_branch()` / `compute()`
  · `ref(node=...)` 一律把 formNodeId 写成 "start" → 现在指向真实节点 id
  · 子流程的流程变量三处都没传 → 现在 `subflow(params=)` / `call_sub(pass_=)` / `var()`

序列化依据：从 63 条实际在跑的流程 processJson 实测提取（见 flow_dsl.py 文末）。
"""
import argparse
import importlib.util
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import miniflow_creator as MC  # noqa: E402
from flow_dsl import OPT_SET, OPT_INC, OPT_DEC, APPLY_EXPR  # noqa: E402


def log(*a):
    print(*a, flush=True)


RULE = {"等于": "eq", "不等于": "ne", "大于": "gt", "大于等于": "ge",
        "小于": "lt", "小于等于": "le", "包含": "like", "属于": "in",
        "为空": "empty", "不为空": "not_empty"}
# 触发事件类型。引擎读的是 **attr.startEventType**，值是字符串——
# 2026-09-16 之前这里发的是数字键 `tableEventType`，creator 那边读的是
# `startEventType`（取不到就落回默认 "add|update"）→ **63 条流程的触发事件
# 全部静默变成「新增|修改」**，这是「生成的流程触发时机全都不对」的根因。
EVENT = {"新增": "add", "修改": "update", "新增|修改": "add|update", "删除": "delete"}

# 引擎里「变量对象」的 formNodeType 是节点类型的另一种叫法，不是节点 type 本身
NODE_FORM_TYPE = {"get_one": "search", "get_more": "getMore",
                  "data_add": "plus", "operation": "function"}


class Resolver(object):
    """中文名 → code / model 的解析层。一次拉全，之后只查内存。"""

    def __init__(self, api, token, tenant, app):
        self.api, self.token = api, token
        self.tenant, self.app = str(tenant), str(app)
        self.forms = {}          # 表名 → code
        self.fields = {}         # (表名, 字段名) → {"model","type"}

    def load(self, tables):
        all_apps = MC.fetch_app_forms(self.api, self.token, self.tenant)
        me = None
        for a in (all_apps or []):
            if str(a.get("id")) == self.app:
                me = a
                break
        if not me:
            raise SystemExit("FAIL: 在租户里找不到 app=%s" % self.app)
        for f in (me.get("forms") or []):
            self.forms[f.get("name")] = f.get("code")
        missing = [t for t in tables if t not in self.forms]
        if missing:
            raise SystemExit("FAIL: 应用里没有这些工作表: %s" % "、".join(missing))
        n = 0
        for t in tables:
            # fetch_form_fields 返回单个 dict {中文名: {model,type,options}}
            ip = MC.fetch_form_fields(self.api, self.token, self.forms[t], self.tenant)
            for name, v in (ip or {}).items():
                # options 必须留：link-record 的 options 里有 sourceCode/titleField，
                # 「取本单关联明细」要靠它反查主表上那个关联控件的 model
                self.fields[(t, name)] = {"model": v["model"], "type": v["type"],
                                          "options": v.get("options")}
                n += 1
        log("OK:resolve %d 张表 / %d 个字段" % (len(tables), n))

    def link_to(self, master, detail):
        """主表上指向 detail 表的 link-record 控件 → (model, 字段中文名)。

        「取本单关联明细」必须带 linkFormTableField = 这个 model，否则引擎按
        「从工作表获取多条」处理（selectType=1），逐行子流程一行都取不到。
        """
        dcode = self.forms.get(detail)
        if not dcode:
            return None, None
        for (t, name), fi in self.fields.items():
            if t != master or fi.get("type") != "link-record":
                continue
            op = fi.get("options") or {}
            if isinstance(op, dict) and op.get("sourceCode") == dcode:
                return fi["model"], name
        return None, None

    def code(self, table):
        if table not in self.forms:
            raise KeyError("工作表不存在: %s" % table)
        return self.forms[table]

    def has(self, table, field):
        return (table, field) in self.fields

    def f(self, table, field):
        k = (table, field)
        if k not in self.fields:
            raise KeyError("%s 里没有字段 %s" % (table, field))
        return self.fields[k]


def _iso_duration(minutes):
    """分钟数 → ISO 8601 时长。整小时/整天走预置（设计器认得），其余走自定义。"""
    if minutes and minutes % 1440 == 0:
        return "P%dD" % (minutes // 1440)
    if minutes and minutes % 60 == 0:
        return "PT%dH" % (minutes // 60)
    return "PT%dM" % minutes


class Builder(object):
    def __init__(self, rv):
        self.rv = rv
        self.task_seq = 0
        self.sub_ids = {}         # 子流程名 → {"db_id","process_key","process_name"}
        self.built = {}           # 节点名 → {"id","type"}（引用别的节点结果时要用它的 id）
        self._ctx = ""            # 当前流程的上下文表（同名匹配的条件取值就用它）
        # 最近一个「取本单关联明细」节点 / 「新增记录」节点——call_sub 的
        # 数据对象与「传 record id」要指回它们（见 _node 的 subprocess 分支）
        self._last_get_more = None
        self._last_add = None

    def nid(self):
        self.task_seq += 1
        return "task%d%03d" % (int(time.time() * 1000), self.task_seq)

    # ---- 条件 ----
    def _cond_items(self, cond, table):
        """DSL 条件 → 引擎 queryItems。

        两种写法都收：
          · "字段名"           → 同名匹配：拿**上下文行**同名字段的值去比
          · (字段, 规则, 值)   → 显式：规则用中文，值可以是裸值 / ref() / var()
        """
        items = []
        for c in (cond or []):
            if isinstance(c, str):
                fname, rule_cn, val = c, "等于", None
                if not self.rv.has(table, fname):
                    # 目标表没这个字段 → 说明写错了，早点报，别等到运行时静默不匹配
                    raise KeyError("%s 里没有字段 %s（条件写的是目标表的字段名）"
                                   % (table, fname))
                val = {"$ref": fname, "$node": "start"}
            else:
                fname, rule_cn, val = c
            tf = self.rv.f(table, fname)
            v = self.value(val, self._ctx, table)
            items.append({
                "rule": RULE.get(rule_cn, "eq"), "ruleName": rule_cn,
                "valueType": 2 if isinstance(v, dict) else "1",
                "val": v, "name": None,
                "field": tf["model"], "columnName": fname,
                "type": tf["type"],
                "valType": "variable" if isinstance(v, dict) else tf["type"],
            })
        return items

    def trigger(self, spec):
        """主流程的**触发条件**。空列表 = 无条件（任何一次增删改都跑）。"""
        if not spec.get("cond"):
            return []
        self._ctx = spec["table"]
        return [{"id": MC.gen_id(), "matchType": "AND",
                 "queryItems": self._cond_items(spec["cond"], spec["table"])}]

    def watch_fields(self, spec):
        """主流程的**监控字段** → model 数组。空 = 任何一次修改都算。"""
        names = spec.get("watch") or []
        if not names:
            return []
        if "修改" not in str(spec.get("on", "")):
            raise KeyError("flow(%r)：写了 watch 但 on=%r —— 监控字段只在「修改」触发时起作用"
                           % (spec["name"], spec.get("on")))
        return [self.rv.f(spec["table"], n)["model"] for n in names]

    # ---- 值 ----
    def value(self, v, ctx_table, table=None):
        """把 DSL 值解析成落库形态：固定值 或 变量对象。"""
        if isinstance(v, dict) and "$var" in v:
            # 流程变量（子流程收到的参数）：名字就是 subflow(params=[...]) 里那一个
            n = v["$var"]
            return {"variableValue": n, "variableName": n, "formNodeType": "variable"}
        if isinstance(v, dict) and "$record_id" in v:
            # 「传 record id」= 上游「新增记录」节点建出来的那条记录的 id。
            # 落库形态与普通字段引用不同（variableName="记录id" / variableValue="_id" /
            # formNodeType="plus"），是线上模版实测的原样，别套用 ref() 的形状。
            nm = v["$record_id"] or (self._last_add or {}).get("name")
            b = self.built.get(nm) if nm else None
            add = self._last_add
            if not add or (nm and add["name"] != nm):
                raise KeyError("record_id(%r)：只能指向前面 add() 建的「新增记录」节点"
                               % nm)
            return {"variableValue": "_id", "formTableCode": add["code"],
                    "variableName": "记录id", "formNodeType": "plus",
                    "formNodeId": (b or {}).get("id") or add["id"],
                    "formNodeName": add["name"]}
        if isinstance(v, dict) and "$result" in v:
            # 运算节点的结果
            b = self.built.get(v["$result"])
            if not b or b["type"] != "operation":
                raise KeyError("result(%r)：找不到这个运算节点（只能引用前面 compute() 建的）"
                               % v["$result"])
            return {"formNodeId": b["id"], "formNodeName": v["$result"],
                    "operationMode": "cache", "variableName": "结果",
                    "formNodeType": "function", "variableValue": "result",
                    "decimals": v.get("$decimals", 2),
                    "formTableCode": "function-fun"}
        if isinstance(v, dict) and "$ref" in v:
            node = v["$node"]
            if node in ("start", "子流程", "工作表事件触发"):
                src_table, ftype, fid, fname = (ctx_table, "table", "start",
                                                "工作表事件触发")
            else:
                b = self.built.get(node)
                if not b:
                    raise KeyError("ref(%r, node=%r)：这个节点还没建（只能引用前面的节点）"
                                   % (v["$ref"], node))
                # formNodeId 必须指向**真正产出这个字段的节点**；早先这里一律写 "start"，
                # 字段名对了、来源指错了——运行时读的是上下文行，值永远不对。
                src_table = b.get("table") or ctx_table
                ftype = NODE_FORM_TYPE.get(b["type"], "search")
                fid, fname = b["id"], node
            fi = self.rv.f(src_table, v["$ref"])
            # fieldType 不能少：线上模版里引用型取值固定 7 键
            # （fieldType/formNodeId/formNodeName/formNodeType/formTableCode/variableName/variableValue）
            return {"variableValue": fi["model"], "formTableCode": self.rv.code(src_table),
                    "variableName": v["$ref"], "formNodeType": ftype,
                    "formNodeId": fid, "formNodeName": fname,
                    "fieldType": fi["type"]}
        if isinstance(v, dict) and ("$inc" in v or "$dec" in v):
            # flow_dsl.inc()/dec() 的标记：脱壳解析，optType 在 node() 里按字段补
            return self.value(v["$inc"] if "$inc" in v else v["$dec"], ctx_table, table)
        if isinstance(v, dict) and "$lit" in v:
            return v["$lit"]
        if isinstance(v, dict) and "$calc" in v:
            raise NotImplementedError(
                "flow_dsl.calc() 已废弃：算术请用 compute()（流程内运算）或工作表公式字段。")
        return v

    # ---- 办理人分组（审批节点与填写节点共用）----
    def groups(self, spec, dflt="admin"):
        """DSL 的 users/roles/exp → 引擎 approverGroups。

        `exp` 是**表达式取人**：`${applyUserId}` → 「获取发起人」这类语义名。
        `dflt` 决定「谁都没点名」时的兜底：审批节点兜底 admin，填写节点兜底发起人。
        """
        groups = []
        who = spec.get("who")
        if who:
            # 名称与表达式 id 必须**成对**（见 flow_dsl.APPLY_EXPR）：
            # 只改 expressionsNames 不改 id，卡片上写的和实际取的人会对不上。
            if who not in APPLY_EXPR:
                raise KeyError("办理人只支持 %s，收到 %r"
                               % ("/".join(APPLY_EXPR), who))
            eid, ename = APPLY_EXPR[who]
            groups.append({"approverType": "candidateUser", "assigneeType": "assigneeByExp",
                           "approverIds": [], "approverNames": [], "deptIds": [],
                           "roleIds": [], "postIds": [],
                           "expressionsIds": [eid],
                           "expressionsNames": [ename], "levelMode": 1,
                           "approverId": "", "approverName": "", "variableTitle": [],
                           "variableContent": "", "formTableType": ""})
        if spec.get("users"):
            groups.append({"approverType": "candidateUser", "assigneeType": "assigneeByName",
                           "approverIds": ["user.%s" % u for u in spec["users"]],
                           "approverNames": list(spec["users"]), "levelMode": 1,
                           "approverId": "", "approverName": "", "deptIds": [], "roleIds": [],
                           "postIds": [], "expressionsIds": []})
        if spec.get("roles"):
            groups.append({"approverType": "candidateGroups", "assigneeType": "assigneeByName",
                           "roleIds": list(spec["roles"]), "roleNames": list(spec["roles"]),
                           "levelMode": 1, "approverId": "", "approverName": "",
                           "approverIds": [], "deptIds": [], "postIds": [], "expressionsIds": []})
        if not groups:
            if dflt == "apply":
                eid, ename = APPLY_EXPR["发起人"]
                return [{"approverType": "candidateUser", "assigneeType": "assigneeByExp",
                         "approverIds": [], "approverNames": [], "deptIds": [], "roleIds": [],
                         "postIds": [], "expressionsIds": [eid],
                         "expressionsNames": [ename], "levelMode": 1,
                         "approverId": "", "approverName": "", "variableTitle": [],
                         "variableContent": "", "formTableType": ""}]
            groups.append({"approverType": "candidateUser", "assigneeType": "assigneeByName",
                           "approverIds": ["user.admin"], "approverNames": ["admin"],
                           "levelMode": 1, "approverId": "", "approverName": "",
                           "deptIds": [], "roleIds": [], "postIds": [], "expressionsIds": []})
        return groups

    # ---- 单个节点 ----
    def node(self, spec, ctx_table):
        """建一个节点，并登记「节点名 → id」，好让后面的节点能用 `ref(node=...)` 指它。"""
        self._ctx = ctx_table
        if "id" not in spec:
            spec = dict(spec, id=self.nid())     # 自己发 id，creator 侧会沿用
        n = self._node(spec, ctx_table)
        if isinstance(n, dict):
            # 自己发出去的 id 回填进节点，creator 侧会原样沿用——
            # 这样 `ref(node=...)` / `result(...)` 拿到的 id 与最终落库的一致
            n.setdefault("id", spec["id"])
            if n.get("name"):
                reg = {"id": n["id"], "type": n["type"],
                       "table": spec.get("table") or ctx_table}
                # 「取本单关联明细」要额外记住主表/明细表 code：后面 call_sub 的
                # 数据对象是按这四个值拼的（via=节点名时用得上）
                if (n["type"] == "get_more" and self._last_get_more
                        and self._last_get_more["name"] == n["name"]):
                    reg["main_code"] = self._last_get_more["main"]
                    reg["detail_code"] = self._last_get_more["code"]
                    reg["detail_table"] = self._last_get_more["table"]
                self.built[n["name"]] = reg
        return n

    def _node(self, spec, ctx_table):
        t = spec["type"]

        if t == "get_one":
            tb = spec["table"]
            conds = self._cond_items(spec.get("cond"), tb)
            return {"type": "get_one", "name": spec["name"], "getType": 1,
                    "formTableCode": self.rv.code(tb), "formTableName": tb,
                    "conditions": conds,
                    # 3 = 中止流程，或继续执行查找结果分支（配 data_branch）
                    "emptyAction": {"继续": 0, "新增": 1, "中止": 2,
                                    "分支": 3}.get(spec.get("empty"), 0)}

        if t == "get_more":
            tb = spec["table"]
            # —— 取「本单的关联明细」：selectType=3「从单条记录获取关联记录」——
            # 引擎认的是 selectType=3 + linkFormTableField(=主表 link 控件的 model)
            # + formTableId=form_start_<主表code> + limitNum 留空。
            # 只发 getType=1「从工作表获取多条」时：面板显示错、逐行子流程一行都取不到
            # （2026-09-17 实测：批量建的 63 条流程全栽在这里）。
            if str(spec.get("from") or "") in ("start", "工作表事件触发"):
                lmodel, lname = self.rv.link_to(ctx_table, tb)
                if lmodel:
                    self._last_get_more = {"id": spec["id"], "code": self.rv.code(tb),
                                           "name": spec["name"],
                                           "main": self.rv.code(ctx_table),
                                           "table": tb}
                    return {"type": "get_more", "name": spec["name"],
                            "selectType": 3, "sourceTaskId": "start",
                            "formTableCode": self.rv.code(ctx_table),
                            "formTableName": ctx_table,
                            "relationField": lmodel,
                            "limitCount": None,          # 关联明细不设条数上限
                            "conditions": [],
                            "attr": {"linkFormTableCode": self.rv.code(tb),
                                     "linkFormTableName": tb, "linkFormTableType": 1,
                                     "getDataType": 1, "noDataType": 1,
                                     "formTableSourceNodeType": "table"}}
            conds = self._cond_items(spec.get("cond"), tb)
            d = {"type": "get_more", "name": spec["name"], "getType": 1,
                 "formTableCode": self.rv.code(tb), "formTableName": tb,
                 "conditions": conds, "fetchMode": "realtime",
                 "limitCount": spec.get("limit") or 0}
            if spec.get("sort"):
                sf = self.rv.f(tb, spec["sort"])
                d["sortField"], d["sortType"] = sf["model"], "desc"
            return d

        if t == "data_update":
            tb = spec["table"]
            # 更新目标行由谁产出：formTableSourceTaskId 指向那个节点的 id，
            # formTableId 跟着写成 form_<来源节点id>_<表code>，formTableSourceNodeType
            # 取 search/plus（线上 44 条实测：search 35 / plus 9，没有一例是 "table"）。
            src = spec.get("source") or "start"
            if src in ("start", "工作表事件触发"):
                src_id, src_type = "start", "table"
            else:
                b = self.built.get(src)
                if not b:
                    raise KeyError("update(%r, source=%r)：这个节点还没建"
                                   % (spec["name"], src))
                src_id = b["id"]
                src_type = NODE_FORM_TYPE.get(b["type"], "search")
            ufs = []
            for fname, v in (spec["mapping"] or {}).items():
                tf = self.rv.f(tb, fname)
                # optType 逐字段：inc()→"2" 增加 / dec()→"3" 减少 / 其余→"1" 设值。
                # 没有它，「库存自动累加维护」只能写成覆盖，语义是错的。
                opt = OPT_SET
                if isinstance(v, dict) and "$inc" in v:
                    opt = OPT_INC
                elif isinstance(v, dict) and "$dec" in v:
                    opt = OPT_DEC
                val = self.value(v, ctx_table)
                ufs.append({"field": tf["model"], "val": val, "fieldType": tf["type"],
                            "type": tf["type"], "optType": opt,
                            "valueType": 3 if isinstance(val, dict) else None,
                            "valType": "variable" if isinstance(val, dict) else None})
            return {"type": "data_update", "name": spec["name"],
                    "formTableCode": self.rv.code(tb), "formTableName": tb,
                    "formTableSourceTaskId": src_id,
                    "formTableSourceNodeType": src_type,
                    "formTableId": "form_%s_%s" % (src_id, self.rv.code(tb)),
                    "updateFields": ufs}

        if t == "data_add":
            tb = spec["table"]
            # 必须是 formModel（{目标字段 model: 取值}），不是 addFields——
            # 发 addFields 时 creator 侧取不到，落库 formModel 为空：
            # 设计器「新增记录」面板全空、运行时建出空记录（2026-09-17 实测）。
            form_model = {}
            for fname, v in (spec.get("mapping") or {}).items():
                tf = self.rv.f(tb, fname)
                form_model[tf["model"]] = self.value(v, ctx_table)
            # 登记：后面 call_sub 的「传 record id」要指向它
            self._last_add = {"id": spec["id"], "name": spec["name"],
                              "code": self.rv.code(tb)}
            return {"type": "data_add", "name": spec["name"],
                    "formTableCode": self.rv.code(tb), "formTableName": tb,
                    # 线上 28 条 data_add 的这两个键**都是空串**（来源是「本节点自己」，
                    # 不是触发行）；写成 "start"/"table" 会让面板的来源标注错
                    "formTableSourceTaskId": "", "formTableSourceNodeType": "",
                    "formModel": form_model, "addDataType": 1, "formType": 2, "noDataType": 1,
                    "expressionType": "delegateExpression",
                    "expressionValue": "${addRecordDelegate}"}

        if t == "approver":
            groups = []
            if spec.get("_exp"):        # flow_dsl.appr()：审批人 = 发起人
                # expressionsNames 是设计器卡片上的「填写人」显示名，别塞表达式原文
                groups.append({"approverType": "candidateUser", "assigneeType": "assigneeByExp",
                               "approverIds": [], "approverNames": [], "deptIds": [],
                               "roleIds": [], "postIds": [],
                               "expressionsIds": ["${applyUserId}"],
                               "expressionsNames": [spec["_exp"]], "levelMode": 1,
                               "approverId": "", "approverName": "", "variableTitle": [],
                               "variableContent": "", "formTableType": ""})
            if spec.get("users"):
                # ⚠️ approverIds 写**裸账号**，不能带 `user.` 前缀——`user.xxx` 是**消息节点
                # toUserIds** 的写法；写成前缀时 save/deploy 全绿、新增记录也起实例，
                # 但**任务谁都收不到**（2026-09-16 用户实测报障「指定成员的任务没人收到」，
                # 线上参照应用的 2 条指定成员组落库均为裸账号）。
                groups.append({"approverType": "candidateUser", "assigneeType": "assigneeByName",
                               "approverIds": [u for u in spec["users"]],
                               "approverNames": list(spec["users"]), "levelMode": 1,
                               "approverId": "", "approverName": "", "deptIds": [], "roleIds": [],
                               "postIds": [], "expressionsIds": []})
            if spec.get("roles"):
                # ⚠️ candidateGroups 的 roleIds 按文档必须填**角色 Code**（如 "admin"），
                # 而 DSL 这里收的是角色名——名字≠Code 时同样静默解析不到人。未实测，用到请先核。
                groups.append({"approverType": "candidateGroups", "assigneeType": "assigneeByName",
                               "roleIds": list(spec["roles"]), "roleNames": list(spec["roles"]),
                               "levelMode": 1, "approverId": "", "approverName": "",
                               "approverIds": [], "deptIds": [], "postIds": [], "expressionsIds": []})
            if not groups:      # 没点名审批人 → 兜底 admin
                groups.append({"approverType": "candidateUser", "assigneeType": "assigneeByName",
                               "approverIds": ["admin"], "approverNames": ["admin"],
                               "levelMode": 1, "approverId": "", "approverName": "",
                               "deptIds": [], "roleIds": [], "postIds": [], "expressionsIds": []})
            return {"type": "approver", "name": spec["name"],
                    "approvalMode": 3 if spec.get("mode") == 3 else 1,
                    "approverGroups": self.groups(spec, dflt="admin")}

        if t == "edit":
            # 填写节点：办理人打开表单边看边改。与 approver 的区别见 flow_dsl.fill()。
            return {"type": "edit", "name": spec["name"],
                    "approverGroups": self.groups(spec, dflt="apply")}

        if t == "exclusive":
            brs = []
            for i, b in enumerate(spec.get("branches") or []):
                items = []
                for (fname, rule_cn, val) in (b.get("cond") or []):
                    tf = self.rv.f(ctx_table, fname)
                    items.append({"rule": RULE.get(rule_cn, "eq"),
                                  "ruleName": rule_cn, "valueType": "1",
                                  "val": val, "name": None,
                                  "field": tf["model"], "columnName": fname,
                                  "type": tf["type"], "valType": tf["type"]})
                e = {"name": b.get("name") or ("分支%d" % (i + 1)),
                     "nodes": [self.node(x, ctx_table) for x in (b.get("nodes") or [])]}
                if items:
                    e["conditions"] = items
                else:
                    e["isDefault"] = True
                brs.append(e)
            return {"type": "exclusive", "name": spec["name"], "conditionNodes": brs}

        if t == "data_branch":
            # 数据判断分支：必须紧跟在 get_one(empty="分支") 之后（creator 会校验）
            def branch(nm, nodes):
                return {"name": nm, "nodes": [self.node(x, ctx_table) for x in nodes]}
            return {"type": "data_branch", "name": spec["name"],
                    "conditionNodes": [branch("有数据", spec.get("found") or []),
                                       branch("无数据", spec.get("missing") or [])]}

        if t == "operation":
            # 运算节点：expr 里的 $名字$ 换成 funText 的 {{i}}，并备好每个字段的出处。
            # 用 creator 的「方式二」（显式 funFields），因为方式一假定所有字段都来自
            # 上下文表——而实际算式里的字段多半来自上面某个「取单条数据」节点。
            expr, fun_fields = spec.get("expr") or "", []
            for label, ref_v in (spec.get("fields") or {}).items():
                if ("$%s$" % label) not in expr:
                    raise KeyError("compute(%r)：算式里找不到占位符 $%s$"
                                   % (spec["name"], label))
                if not (isinstance(ref_v, dict) and "$ref" in ref_v):
                    raise KeyError("compute(%r)：$%s$ 必须是 ref(...)，不能是固定值"
                                   % (spec["name"], label))
                val = self.value(ref_v, ctx_table)
                src_node = ref_v["$node"]
                src_table = (ctx_table if src_node in ("start", "子流程", "工作表事件触发")
                             else (self.built.get(src_node) or {}).get("table"))
                fi = self.rv.f(src_table, ref_v["$ref"])
                fun_fields.append({
                    "field": fi["model"], "formTableCode": val["formTableCode"],
                    "fieldText": ref_v["$ref"], "formNodeId": val["formNodeId"],
                    "formNodeName": val["formNodeName"], "tableText": src_table or "",
                })
                expr = expr.replace("$%s$" % label, "{{%d}}" % (len(fun_fields) - 1))
            if "{{" not in expr:
                raise KeyError("compute(%r)：算式里一个 $占位符$ 都没有" % spec["name"])
            return {"type": "operation", "name": spec["name"],
                    "funText": expr, "funFields": fun_fields,
                    "funType": "fun", "decimals": spec.get("decimals", 2)}

        if t == "subprocess":
            sub = self.sub_ids.get(spec["sub"])
            if not sub:
                raise KeyError("子流程尚未构建: %s（顺序必须是先子后主）" % spec["sub"])
            multi = bool(spec.get("multi", True))

            # —— 逐行调子流程（callActivity）的**全套契约**，形状照线上模版实测 ——
            # 少任何一项都不是「建歪一点」，而是：设计器里「选择数据对象」空白、
            # 子流程页白屏、「被以下工作流触发」为空、运行时一行都不进子流程。
            gm = self._last_get_more
            via = spec.get("via")
            if via:
                b = self.built.get(via)
                if not b or b["type"] != "get_more":
                    raise KeyError("call_sub(%r, via=%r)：via 必须是前面 get_more() 建的节点"
                                   % (spec["name"], via))
                gm = {"id": b["id"], "name": via,
                      "code": b.get("detail_code"), "main": b.get("main_code"),
                      "table": b.get("detail_table")}
            if multi and not gm:
                raise KeyError(
                    "call_sub(%r)：逐行调子流程前面必须有 get_more(..., from_=\"start\")"
                    "（取本单关联明细）——没有数据对象时子流程会绑不上、整条链断掉"
                    % spec["name"])
            if multi and not (gm.get("code") and gm.get("main")):
                raise KeyError("call_sub(%r)：数据对象缺明细表/主表 code（%r）"
                               % (spec["name"], gm))

            attr = {"approvalEnabled": True,
                    "calledElement": "process%s" % sub["db_id"],
                    "formTableName": None, "formTableCode": None,
                    "processName": sub["process_name"], "processId": "",
                    "customProcessId": str(sub["db_id"]),
                    "loopCardinality": None, "ratio": 0.5,
                    "isSequential": False, "isMulti": multi,
                    "collection": "${flowUtil.stringToList(assigneeUserIdList)}",
                    "elementVariable": "assigneeUserId",
                    "completionCondition": None}

            var_list = []
            for pname, pv in (spec.get("pass") or {}).items():
                val = self.value(pv, ctx_table)
                var_list.append({
                    "id": MC.gen_id(), "optType": "1",
                    "valueType": 2 if isinstance(val, dict) else "1",
                    "fieldValue": "",
                    "field": pname, "val": val,
                    "fieldType": "input", "type": "input",
                    "valType": "variable" if isinstance(val, dict) else None,
                })
            if var_list:
                attr["variableList"] = var_list

            if multi:
                attr["formTableSourceTaskId"] = gm["id"]
                attr["formTableId"] = "form_%s_%s" % (gm["id"], gm["code"])
                attr["subFormTableObject"] = {
                    "formTableId": attr["formTableId"],
                    "nodeId": gm["id"], "nodeName": gm["name"], "nodeType": "getMore",
                    "formTableCode": gm["code"], "formTableName": gm.get("table") or "",
                    "formTableMainCode": gm["main"], "formTableType": 1,
                    "isSubStart": True, "selectType": 3, "getDataType": 1,
                }

            return {"type": "subprocess", "name": spec["name"],
                    "approvalMode": 1,
                    # 子流程流程变量靠这个监听器注入；漏了 → 子流程里 var() 全是空
                    "listenerData": [{
                        "id": "502880e54853a496014805e5d9190012",
                        "eventType": "start", "listenerType": "javaClass",
                        "listenerName": "子流程流程变量",
                        "value": ("org.jeecg.modules.extbpm.process.adapter.delegate."
                                  "MiniCallActivityListener"),
                        "allowDel": False}],
                    # 这 4 条是引擎固定回传的上下文，缺了子流程取不到父单据
                    "inVariableModels": [
                        {"source": "applyUserId", "target": "applyUserId"},
                        {"source": "dataId", "target": "dataId"},
                        {"source": "JG_LOCAL_PROCESS_ID",
                         "target": "JG_SUB_MAIN_PROCESS_ID"},
                        {"source": "handleDataId", "target": "handleDataId"},
                    ],
                    "outVariableModels": [],
                    "attr": attr}

        if t == "time":
            # duration 必须是 ISO 8601 时长串。早先写的是裸分钟数（`attr.duration: 5`），
            # build_time_node 又只在**顶层**找 duration → 一律落回 "PT1M"：
            # `delay(30)` 建出来是「1 分钟后」，save/deploy 全绿。
            return {"type": "time", "name": spec["name"],
                    "duration": _iso_duration(int(spec.get("minutes") or 1))}

        if t == "notice":
            users = list(spec.get("users") or [])
            # 收件人允许写 "role.xxx" / "dept.xxx"；裸姓名补 "user." 前缀
            ids = [u if "." in u else "user.%s" % u for u in users]
            return {"type": "notice", "name": spec["name"],
                    "noticeType": spec.get("kind") or "system",
                    "attr": {"noticeTitle": spec.get("title") or "通知",
                             "noticeContent": spec.get("content") or ""},
                    "toUserIds": ids, "toUserNames": users}

        raise KeyError("未知节点类型: %s" % t)

    def build(self, spec):
        """spec → (config, nodes) 供 build_process_json 用。"""
        ctx = spec.get("table") or spec.get("context")
        # 每条流程重新开始登记：节点名只在**本流程内**唯一，跨流程复用会指错节点
        self.built = {}
        self._last_get_more = None
        self._last_add = None
        nodes = [self.node(x, ctx) for x in (spec.get("nodes") or [])]
        if spec["kind"] == "main":
            config = {
                "processName": spec["name"],
                "lowAppId": self.rv.app,
                "processType": "oa",
                "startType": "tableEvent",
                "formTableCode": self.rv.code(spec["table"]),
                "formTableName": spec["table"],
                # 引擎读 attr.startEventType（字符串）；写数字键会被静默忽略
                "startEventType": EVENT.get(spec.get("on", "新增"), "add"),
                "startCondition": self.trigger(spec),
                # 监控字段：update 时后端先比对新旧值，只有这些字段变了才继续校验条件
                "conditionFields": self.watch_fields(spec),
                "nodes": nodes,
            }
        else:
            config = {
                "processName": spec["name"],
                "lowAppId": self.rv.app,
                "processType": "oa",
                "startType": "subEvent",
                "formTableCode": self.rv.code(spec["context"]),
                "formTableName": spec["context"],
                # 声明本子流程要收哪些流程变量；不声明 = 调用方传了也收不到
                "variableList": [{"field": p, "id": MC.gen_id(), "type": "input",
                                  "options": {"format": "yyyy-MM-dd"}}
                                 for p in (spec.get("params") or [])],
                "hasVariableList": False,     # 子流程恒 False（实测 29/29 条如此）
                "nodes": nodes,
            }
        # ⚠️ 必须返回**二元组**：两处调用点都写的是 `config, nodes = b.build(f)`
        # （本函数 docstring 也一直写着 "→ (config, nodes)"）。2026-09-16 实测：
        # 只 `return config` 时，把 8 个键的 dict 解包成 2 个变量 →
        # `ValueError: too many values to unpack (expected 2)`，
        # 主流程与子流程**一条都建不出来**——这就是 `flow_dsl.py` 里
        # 「save → deploy 实盘路径尚未验证过」那条备注背后的真实原因。
        return config, nodes


# ---------------- 主流程 ----------------

def load_spec(path):
    m = importlib.util.spec_from_file_location("user_flows", path)
    mod = importlib.util.module_from_spec(m)
    m.loader.exec_module(mod)
    flows = getattr(mod, "FLOWS", None)
    if not flows:
        raise SystemExit("FAIL: spec 里没有 FLOWS")
    return flows


def tables_of(flows):
    out = []
    for f in flows:
        for t in ([f.get("table"), f.get("context")] + _node_tables(f.get("nodes") or [])):
            if t and t not in out:
                out.append(t)
    return out


def _walk_nodes(nodes):
    """把节点树（含分支里的）拍平成一个列表。"""
    out = []
    if not isinstance(nodes, list):
        nodes = [nodes]
    for n in nodes:
        if not isinstance(n, dict):
            continue
        out.append(n)
        for b in (n.get("branches") or []):
            out += _walk_nodes(b.get("nodes"))
        for k in ("found", "missing"):
            out += _walk_nodes(n.get(k) or [])
        out += _walk_nodes(n.get("nodes") or [])
    return out


def _node_tables(nodes):
    out = []
    if not isinstance(nodes, list):
        return out
    for n in nodes:
        if not isinstance(n, dict):
            continue
        if n.get("table"):
            out.append(n["table"])
        for b in (n.get("branches") or []):
            out += _node_tables(b.get("nodes") or [])
        # data_branch 的两条支路（键名是 found/missing，别和 get_one 的 empty= 撞）
        out += _node_tables(n.get("found") or [])
        out += _node_tables(n.get("missing") or [])
    return out


def existing_names(api, token, tenant, app):
    """该应用下已有的流程名集合（带 X-Low-App-ID 头，0.1s 只含本应用）。"""
    import requests
    try:
        r = requests.get(api + "/act/process/extActProcess/list",
                         params={"lowAppId": app, "pageSize": 500, "pageNo": 1},
                         headers={"X-Access-Token": token, "X-Tenant-Id": str(tenant),
                                  "X-Low-App-ID": str(app)}, timeout=60)
        res = (r.json() or {}).get("result") or {}
        rows = (res.get("records") if isinstance(res, dict) else res) or []
        return {x.get("processName") for x in rows}
    except Exception:                                             # noqa: BLE001
        return set()


def _own_flow(rec, app_id, tenant_id=None):
    """按名字查回来的记录是否**真的属于本应用**。

    `listProcess` 不过滤租户，同名流程可能来自别的租户/应用 → 不能当成「本应用已存在」。
    记录里 `lowAppId` 为空时（后端偶发漏写）退回看 `tenantId`：还是本租户就认，
    保住「lowAppId 被写空、记录还在」那条兜底路径的原意。
    """
    if not rec:
        return None
    if str(rec.get("lowAppId") or "") == str(app_id):
        return rec
    if not rec.get("lowAppId") and tenant_id is not None \
            and str(rec.get("tenantId") or "") == str(tenant_id):
        return rec
    return None


def main():
    ap = argparse.ArgumentParser(description="批量建流程：规格驱动、单进程、幂等")
    ap.add_argument("--api-base", required=True)
    ap.add_argument("--token", required=True)
    ap.add_argument("--tenant-id", required=True)
    ap.add_argument("--app-id", required=True)
    ap.add_argument("--spec", required=True, help="flows.py")
    ap.add_argument("--only", default="",
                    help="只处理这些流程名（逗号分隔）。**重跑失败项时一定要加**："
                         "不加时 --update 会把全部流程重存重发（63 条实测 234s），"
                         "加了只碰这几条。被选中主流程引用到的子流程会自动带上"
                         "（子流程必须先建，否则只会撞「子流程尚未构建」白跑一轮）。")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--update", action="store_true",
                    help="同名流程**重存+重发布**（保留原 processKey），而不是跳过。"
                         "改了 flows.py 想生效必须加这个——默认同名会静默跳过。")
    a = ap.parse_args()

    flows = load_spec(a.spec)
    only = {s.strip() for s in a.only.split(",") if s.strip()}
    if only:
        known = {f["name"] for f in flows}
        miss = sorted(only - known)
        if miss:
            raise SystemExit("--only 里有 flows.py 中不存在的流程名：%s" % "、".join(miss))
        # 被选中主流程引用到的子流程自动带上：callActivity 是按 key 引用子流程的，
        # 子流程没先建/没先发布 → 「子流程尚未构建」整条主流程建不出来。
        sub_names = {f["name"] for f in flows if f["kind"] == "sub"}
        picked = set(only)
        changed = True
        while changed:
            changed = False
            for f in flows:
                if f["name"] not in picked:
                    continue
                for n in _walk_nodes(f.get("nodes") or []):
                    s = n.get("sub")
                    if s in sub_names and s not in picked:
                        picked.add(s)
                        changed = True
        flows = [f for f in flows if f["name"] in picked]
        log("OK:only 只处理 %d 条（点名 %d + 依赖子流程 %d）"
            % (len(flows), len(only), len(picked) - len(only)))
    rv = Resolver(a.api_base, a.token, a.tenant_id, a.app_id)
    rv.load(tables_of(flows))

    have = existing_names(a.api_base, a.token, a.tenant_id, a.app_id)
    # listProcess 是按 lowAppId 过滤的 —— 记录还在、但 lowAppId 被写空时它就不出现在列表里。
    # 那种情况下**不能当新建**（会建出重名副本、且原条目的 callActivity 绑定全断）。
    # 所以：列表里没有的，再按名字查一次；查得到就走更新。
    #
    # ⚠️ **必须带 low_app_id**（2026-09-17 修）：`listProcess` **不按 X-Tenant-Id 过滤**，
    # 不带 lowAppId 时会逐页扫到**别的租户的同名流程**并当命中返回。
    # 实测（租户 1013 新建「进销存」，1009~1012 早先建过同名应用）：63 条里 61 条被判
    # 「已存在」→ 全 `OK:skip` → 本应用 0 条流程；这轮按名字轮询还白烧了 20 分钟。
    # 带上 lowAppId 后服务端直接过滤（1 页返回），既准又快。
    orphan = [f["name"] for f in flows if f["name"] not in have
              and _own_flow(MC.query_flow(a.api_base, a.token, process_name=f["name"],
                                          tenant_id=a.tenant_id, low_app_id=a.app_id),
                            a.app_id, a.tenant_id)]
    if orphan:
        log("OK:plan 这几条不在列表里、但按名字查得到（lowAppId 可能被写空），按更新处理：%s"
            % "、".join(orphan))
        have |= set(orphan)
    subs = [f for f in flows if f["kind"] == "sub"]
    mains = [f for f in flows if f["kind"] == "main"]
    log("OK:plan 子流程 %d / 主流程 %d（已存在 %d 条同名）" % (len(subs), len(mains), len(have)))

    if a.dry_run:
        for f in subs + mains:
            log("OK:plan [%s] %s ← %s" % (f["kind"], f["name"], f.get("table") or f.get("context")))
        return

    b = Builder(rv)
    t0 = time.time()
    ok = skip = fail = 0
    sub_links = []      # 主流程 callActivity → 子流程的引用，供第 ③ 趟回填

    # ① 子流程：save → deploy → 注册 → 补 customProcessId → 再 deploy → 校验
    for f in subs:
        name = f["name"]
        rec = None
        if name in have:
            # 带 low_app_id：不带时 listProcess 会跨租户命中同名流程（见 query_flow 注释）
            rec = _own_flow(MC.query_flow(a.api_base, a.token, process_name=name,
                                          tenant_id=a.tenant_id, low_app_id=a.app_id),
                            a.app_id, a.tenant_id)
            if rec and not a.update:
                b.sub_ids[name] = {"db_id": str(rec["id"]), "process_key": rec.get("processKey"),
                                   "process_name": name}
                log("OK:skip 子 %s" % name)
                skip += 1
                continue
        try:
            config, nodes = b.build(f)
            # --update 必须**保留原 processKey**：主流程的 call_sub 是按 key 引用子流程的
            config["processKey"] = (rec.get("processKey") if rec
                                    else "process%d" % (int(time.time() * 1000) % 10 ** 12))
            config["startTaskId"] = "start%s" % (int(time.time() * 1000) % 10 ** 9)
            pj = MC.build_process_json(dict(config, nodes=nodes))
            if rec:                                   # 重存：按 id + updateCount 覆盖
                fid = str(rec["id"])
                MC.save_flow(a.api_base, a.token, config, pj, flow_id=fid,
                             update_count=rec.get("updateCount"))
            else:
                r = MC.save_flow(a.api_base, a.token, config, pj)
                fid = (r.get("result") or {}).get("id") or r.get("id")
            MC.register_subprocess_id(config["processKey"], str(fid))
            pj.setdefault("attr", {})["customProcessId"] = str(fid)
            pj["attr"]["processKey"] = config["processKey"]
            rec = MC.query_flow(a.api_base, a.token, flow_id=fid,
                                tenant_id=a.tenant_id)
            if rec:
                MC.save_flow(a.api_base, a.token, config, pj, flow_id=fid,
                             update_count=rec.get("updateCount"))
            MC.deploy_flow(a.api_base, a.token, fid, tenant_id=a.tenant_id, low_app_id=a.app_id)
            b.sub_ids[name] = {"db_id": str(fid), "process_key": config["processKey"],
                               "process_name": name}
            log("OK:sub %s id=%s" % (name, fid))
            ok += 1
        except Exception as e:                                    # noqa: BLE001
            log("FAIL:sub %s %s" % (name, str(e)[:170]))
            fail += 1

    # ② 主流程：call_sub 已能解析到新子流程 id
    for f in mains:
        name = f["name"]
        rec = None
        if name in have:
            # 带 low_app_id：不带时 listProcess 会跨租户命中同名流程（见 query_flow 注释）
            rec = _own_flow(MC.query_flow(a.api_base, a.token, process_name=name,
                                          tenant_id=a.tenant_id, low_app_id=a.app_id),
                            a.app_id, a.tenant_id)
            if rec and not a.update:
                log("OK:skip 主 %s" % name)
                skip += 1
                continue
        try:
            config, nodes = b.build(f)
            config["processKey"] = (rec.get("processKey") if rec
                                    else "process%d" % (int(time.time() * 1000) % 10 ** 12))
            config["startTaskId"] = "start%s" % (int(time.time() * 1000) % 10 ** 9)
            pj = MC.build_process_json(dict(config, nodes=nodes))
            if rec:                                   # --update：重存，保留原 processKey
                fid = str(rec["id"])
                MC.save_flow(a.api_base, a.token, config, pj, flow_id=fid,
                             update_count=rec.get("updateCount"))
            else:
                r = MC.save_flow(a.api_base, a.token, config, pj)
                fid = (r.get("result") or {}).get("id") or r.get("id")
            # 主流程侧：subFlowList = 每个 callActivity 一条（前端算的值，后端不推导）。
            # 缺它 → 子流程页「被以下工作流触发」为空。字段名与线上模版一致：
            # {subProcessId, subNodeName, status:1}
            sfl, seen = [], set()
            for n in _walk_nodes(nodes):
                if n.get("type") != "subprocess":
                    continue
                a2 = n.get("attr") or {}
                pid = a2.get("customProcessId")
                key = (pid, n.get("name"))
                if key in seen:
                    continue
                seen.add(key)
                sfl.append({"subProcessId": pid, "subNodeName": n.get("name"), "status": 1})
                obj = a2.get("subFormTableObject")
                if isinstance(obj, dict) and pid:
                    sub_links.append({"sub_id": pid, "sub_name": a2.get("processName"),
                                      "node_name": n.get("name"), "obj": dict(obj),
                                      "main_id": str(fid), "main_name": name})
            if sfl:
                pj["subFlowList"] = sfl
                # 二次保存必带 updateCount：新建的那条要先查一次当前值（乐观锁）
                again = MC.query_flow(a.api_base, a.token, flow_id=fid,
                                      tenant_id=a.tenant_id) or {}
                MC.save_flow(a.api_base, a.token, config, pj, flow_id=fid,
                             update_count=again.get("updateCount"))
            MC.deploy_flow(a.api_base, a.token, fid, tenant_id=a.tenant_id, low_app_id=a.app_id)
            log("OK:%s %s id=%s" % ("upd" if rec else "main", name, fid))
            ok += 1
        except Exception as e:                                    # noqa: BLE001
            log("FAIL:main %s %s" % (name, str(e)[:170]))
            fail += 1

    # ③ 子流程登记回填 —— **后端不会替你做**，设计器是自己算好一起提交的
    #    （2026-09-17 实测：两个应用、29 条子流程，靠 API 存完之后
    #     `formTableList[0].isSubStart` 与 `subFlowSourceInfo` 一条都没回填上，
    #     于是子流程页「数据源」空白、「被以下工作流触发」为空、点进去白屏）。
    #    主流程侧：`subFlowList` = 每个 callActivity 一条，前端算的。
    #    子流程侧：`formTableList[0]`（数据源）+ `subFlowSourceInfo`（谁调我）。
    if a.update or True:
        log("OK:backfill 子流程登记回填 %d 条引用" % len(sub_links))
        for lk in sub_links:
            try:
                srec = MC.query_flow(a.api_base, a.token, flow_id=lk["sub_id"],
                                     tenant_id=a.tenant_id)
                if not srec:
                    log("FAIL:backfill 子流程 %s 查不到" % lk["sub_name"])
                    continue
                spj = srec.get("processJson")
                spj = json.loads(spj) if isinstance(spj, str) else (spj or {})
                obj = dict(lk["obj"])
                obj["nodeTypeMain"] = "getMore"
                obj["nodeType"] = "search"          # 子流程侧是 search（主流程侧是 getMore）
                ftl = spj.get("formTableList") or []
                if ftl and ftl[0].get("isSubStart"):
                    ftl[0] = obj
                else:
                    spj["formTableList"] = [obj] + [e for e in ftl if not e.get("isSubStart")]
                src = [x for x in (spj.get("subFlowSourceInfo") or [])
                       if x.get("mainProcessId") != lk["main_id"]]
                src.append({"mainProcessName": lk["main_name"],
                            "nodeName": lk["node_name"],
                            "mainProcessId": lk["main_id"]})
                spj["subFlowSourceInfo"] = src
                # ⚠️ 第一个参数必须是**建流程时的 config**（processName/processKey/startType…），
                # 不能拿 processJson 顶替 —— 那里面没有这些键，save 会把 processName/
                # processKey 写成空串，流程记录当场被写坏。
                # 2026-09-17 实测：26 条回填把 25 条子流程写成空名，列表里直接查不到了。
                cfg = dict(srec)
                MC.save_flow(a.api_base, a.token, cfg, spj, flow_id=str(lk["sub_id"]),
                             update_count=srec.get("updateCount"))
                MC.deploy_flow(a.api_base, a.token, lk["sub_id"],
                               tenant_id=a.tenant_id, low_app_id=a.app_id)
                log("OK:backfill %s ← %s / %s" % (lk["sub_name"], lk["main_name"], lk["node_name"]))
                ok += 1
            except Exception as e:                                # noqa: BLE001
                log("FAIL:backfill %s %s" % (lk["sub_name"], str(e)[:150]))
                fail += 1

    log("OK:done %s %d / 跳过 %d / 失败 %d，%.1fs"
        % ("更新" if a.update else "建", ok, skip, fail, time.time() - t0))
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
