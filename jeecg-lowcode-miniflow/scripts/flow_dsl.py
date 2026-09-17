# -*- coding: utf-8 -*-
"""流程规格 DSL —— 写 flows.py 只需 import 本模块，**不要自己造助手**。

用法（flows.py）：

    from flow_dsl import *

    # 下面三个流程只是示意结构，表名/字段名按当轮需求替换
    FLOWS = [
      # 子流程：上下文表=维修明细，被主流程逐行调用
      subflow("维修工单-累计台账-子流程", context="维修明细", nodes=[
          # 没有就新建；新建出来是空记录，所以 update 要把定位键一起写进去
          get_one("设备维修台账", cond=["设备编码", "统计月份"], empty="新增"),
          update("设备维修台账", {"设备名称": ref("设备名称"),
                                  "统计月份": ref("统计月份"),
                                  "累计维修次数": inc(ref("本次维修次数"))}),
      ]),

      # 主流程：工作表事件触发
      flow("报销单-回写台账", table="报销单", on="新增", nodes=[
          get_one("费用台账", cond=["台账编号", "部门编码"]),
          update("费用台账", {"处理状态": "确认",
                             "报销金额": ref("报销金额"),
                             "提交时间": ref("提交时间")}),
      ]),

      # 审批人=发起人
      flow("设备请修-主管审批", table="设备请修单", on="新增", nodes=[
          appr("主管审批"),
      ]),
    ]

**写法铁律**：
  · 表名、字段名一律写**中文名**；引擎负责换 code / model（你永远不写 model）。
  · 变量引用一律用 `ref("字段名")`——**不要手写 `{"variableValue": ...}`**，那是引擎的事。
  · 固定值直接写字符串/数字；引用别处记录写 `ref(..., node="某节点名")`。
  · **流程里做不了算术**（`calc()` 未实现）→ 累加/扣减用 `inc()/dec()`，其他派生量交给
    工作表的**公式字段**算好再 `ref()`。

## ⚠️ 两个最容易静默写坏的地方

**① 子流程上下文只读「本行」字段**（`ref()`、`cond` 都只在本行解析，取不到父单据的值）。
所以被逐行处理的明细表必须**物理携带**它要用的键——`fast-full-chain` 与
`references/engine-contract.md` 第五节有统一清单。不给键 → 流程能发布、能跑、**一行都不写**。

**② `get_one(cond=[X])` 要求 X 在上下文表和目标表里同名同值都存在。**
跨表回写拿不到单号时，用**两侧都有的业务字段**当桥（实测最好用的是「产品名称」）。

序列化依据：2026-09-15 从 63 条**实际在跑**的流程 processJson 中实测提取
（`val` = `{variableValue:<源字段model>, variableName:<源字段中文名>, formTableCode:<源表code>,
formNodeType:"table", formNodeId:"start", formNodeName:"工作表事件触发"}`）。

## ⚠️ 覆盖范围（别假设它什么都能建）

**已覆盖**：
  · 流程容器：`flow`（tableEvent 主流程）/ `subflow`（subEvent 子流程）
  · 触发条件与监控字段：`flow(cond=[(字段, 规则, 值)], watch=[字段名])`
  · 节点：get_one / get_more / update / add / approve（审批） / **fill（填写）** /
    appr / gateway(排他分支) / **data_branch(数据判断分支)** / **compute(运算)** /
    call_sub / delay / note
  · 值：ref / lit / inc / dec（累加/扣减）/ **var（流程变量）** / **result（运算结果）**

**未覆盖——用到就停下，别硬套**（缺的类型照 `miniflow-node-types.md` 手写 node_config，
creator 侧多数已实现，只是没有 DSL 助手）：

| 缺口 | 说明 |
|---|---|
| 触发类型 | 只支持 **tableEvent（新增/修改/删除）** 与 **subEvent**。**timerEvent（定时）/ buttonEvent（按钮）/ dateFieldEvent 都没覆盖** |
| 分支 | 排他网关 + 数据判断分支。**包含（inclusive）/ 并行（parallel）/ 意见（opinion）/ 审批结果（approve_result）** 未覆盖 |
| 节点权限 | 节点**字段权限**不在 processJson 里，**只能**调 `/act/process/extActProcessNodePermission/saveOrUpdateBatch`，是独立的收尾步骤（见 `field-perm-rule.md`） |
| 节点类型 | 业务变量(upvariable) / 删除(data_delete) / 取人员部门(get_*_sysinfo) / 服务(service) / 脚本(script) / api / AI 节点 全未覆盖（creator 有 `build_*`，可直接手写 node_config 兜） |
| 办理人细节 | 只支持「指定用户 / 指定角色 / 发起人 / 兜底」；**部门、岗位、组织角色、按表单字段取人、会签比例** 未覆盖。节点的**高级设置**（转办/加签/抄送/驳回/自选下一步/超时）也没助手，走 `attr` 手写 |
| 值语义 | 上下文行字段 / 某节点结果字段 / 流程变量 / 运算结果 都已覆盖。**系统字段（当前用户、当前时间）** 未覆盖 |
| `calc()` | 仍**未实现，调用即报错**——算术一律走 `compute()` 或工作表公式字段 |

**判定**：需求的触发类型是 tableEvent/subEvent、且节点只落在上表「已覆盖」列 → 可直接用；
**只要出现「未覆盖」列任何一项 → 停下来按 node-types 手写**，不要指望本 DSL 兜住。

## 验证状态

`build_flows.py` 的 dry-run 与 **save → deploy 实盘路径均已验证**
（2026-09-16：52 表应用建 63 条流程，一次 80.3s，全部启用；`inc/dec` 与 `appr`
的落地形态已回读 `processJson` 确认——`optType` 与 `assigneeByExp` 都在）。
"""

__all__ = [
    "flow", "subflow", "get_one", "get_more", "update", "add", "approve",
    "appr", "fill", "gateway", "data_branch", "compute", "call_sub", "delay",
    "calc", "note", "ref", "lit", "inc", "dec", "var", "result", "START",
    "record_id",
]

START = "start"

#：表达式取人的三个内置选项：显示名 → (expressionsIds, expressionsNames)
#  ⚠️ 名称与 id 必须成对，别自己拼——写「获取发起人」却绑 `${applyUserDeptLeaderId}`，
#  设计器卡片显示的和实际取的人会不一致。
APPLY_EXPR = {
    "发起人":      ("${applyUserId}", "获取发起人"),
    "部门":        ("${applyUserDeptId}", "获取发起人部门"),
    "部门负责人":  ("${applyUserDeptLeaderId}", "获取发起人部门负责人"),
}

#：引擎约定：updateFields 的 optType（"1" 设值 / "2" 增加 / "3" 减少）
OPT_SET, OPT_INC, OPT_DEC = "1", "2", "3"


# ---------------- 值 ----------------

def inc(value):
    """更新时**累加**（optType="2"）。用于计数这类「在旧值上加」的字段。

        update("设备维修台账", {"累计维修次数": inc(ref("本次维修次数"))})

    ⚠️ optType 是**逐字段**的：同一节点里可以「键字段设值 + 计数累加」混着写。
    """
    return {"$inc": value}


def dec(value):
    """更新时**扣减**（optType="3"）。见 `inc()`。"""
    return {"$dec": value}

def ref(field, node=START):
    """引用字段值。node=START 表示流程上下文表（主流程=触发表；子流程=上下文表）；
    取某 get_one 的结果则传 node="<该节点名>"。引擎负责解析成 model。"""
    return {"$ref": field, "$node": node}


def lit(value):
    """显式固定值（一般不用写，裸字符串/数字就是固定值）。"""
    return {"$lit": value}


def var(name):
    """引用**流程变量**（子流程收到的参数）。

        subflow("销售出库-更新库存-子流程", context="出库产品明细",
                params=["仓库编码"], nodes=[
            get_one("库存实时统计", cond=[("仓库编码", "等于", var("仓库编码"))]),
        ])

    流程变量的名字就是 `subflow(params=[...])` 里写的那一个，调用方用
    `call_sub(..., pass_={"仓库编码": ref("仓库编码")})` 传进来。

    落库形态：`{variableName: <名>, formNodeType: "variable", variableValue: <名>}`。
    """
    return {"$var": name}


def result(node, decimals=2):
    """引用**运算节点**的结果（`compute()` 的产物）。

        compute("算当前库存", "$总入库$ - $总出库$",
                {"总入库": ref("总入库数量"), "总出库": ref("总出库数量")})
        update("库存实时统计", {"当前库存数量": result("算当前库存")})

    落库形态：`{formNodeId: <运算节点id>, formNodeType: "function",
                variableName: "结果", variableValue: "result",
                formTableCode: "function-fun", operationMode: "cache"}`。
    """
    return {"$result": node, "$decimals": decimals}


def calc(kind, args=None, node=None):
    """⚠️ **尚未实现——调用即报错，故意为之。**

    本意是「引用运算节点的结果」，但引擎侧（build_flows.Builder）只把请求收进
    `calc_specs` 就没了下文，**从未回填成真正的运算节点**（2026-09-15 自审发现）。
    原先直接返回 `{"$calc": ...}` 会被原样写进 `updateFields[].val`——save/deploy 全绿、
    运行时静默不对，属于最难查的一类错。所以这里改成**响亮失败**，好过静默写坏。

    要用运算，两条路：
      ① **`compute()`**（2026-09-16 已实现）——流程内运算节点，写完用 `result(节点名)` 引用；
      ② 需要「本行两字段相减」这类派生量，也可以用**工作表公式字段**算好再 `ref()`。
    """
    raise NotImplementedError(
        "flow_dsl.calc() 已废弃：算术请用 compute()（流程内运算）或工作表公式字段。")


# ---------------- 流程容器 ----------------

def flow(name, table, on="新增", cond=None, watch=None, nodes=None, **kw):
    """主流程（工作表事件触发）。on: 新增 / 修改 / 新增|修改 / 删除。

    cond 是**触发条件**（不满足就不跑），格式与 `gateway` 的分支条件一致：
    `[(字段名, 规则, 值), ...]`，规则用中文（等于/不等于/大于/为空/不为空…），
    值可以是裸值，也可以是 `ref(...)` / `var(...)`。

    watch 是**监控字段**（只对 on 含「修改」的流程有意义）：后端先比对新旧值，
    只有这几个字段真的变了才继续校验 cond。不写 = **任何一次修改只要满足 cond 就触发**。

        flow("销售出库-更新库存", table="销售出库", on="修改",
             watch=["产品出库确认"],                      # 只有它变了才算
             cond=[("产品出库确认", "等于", "确认")],       # 且它等于「确认」才跑
             nodes=[...])
    """
    return {"name": name, "kind": "main", "table": table, "on": on,
            "cond": cond or [], "watch": watch or [], "nodes": nodes or [], **kw}


def subflow(name, context, params=None, nodes=None, **kw):
    """子流程（startType=subEvent），被主流程逐行调用。

    context = 子流程的上下文工作表（即主流程调它时逐行遍历的那张明细表）。
    params  = 这条子流程要**收的流程变量名**列表；里面用 `var("名字")` 引用。
              调用方通过 `call_sub(..., pass_={...})` 对应传进来。
    """
    return {"name": name, "kind": "sub", "context": context,
            "params": params or [], "nodes": nodes or [], **kw}


# ---------------- 节点 ----------------

def get_one(table, cond=None, empty="继续", name=None, fields=None):
    """取[表](条件) —— 取单条数据。

    cond 两种写法：
      · 字符串列表 → **同名匹配**，值取流程上下文行的同名字段（最常用）
        `get_one("库存实时统计", cond=["仓库编码", "产品编码"])`
      · 元组列表 → 显式指定规则与值
        `get_one("库存实时统计", cond=[("仓库编码", "等于", var("仓库编码")),
                                       ("产品编码", "等于", ref("产品编码"))])`

    empty: 继续 / 新增 / 中止 / **分支**（配 `data_branch()` 用，见该函数）。
    """
    return {"type": "get_one", "table": table, "cond": cond or [],
            "empty": empty, "name": name or ("获取%s" % table), "fields": fields}


def data_branch(name=None, found=None, missing=None):
    """**看上一次「取单条数据」找到了没有**，分两支往下走。

    必须**紧跟在** `get_one(..., empty="分支")` 后面——引擎是按查找结果分流的。
    支路名用 `missing`（不叫 `empty`），免得和 `get_one` 的 `empty=`（未查到时的动作）
    在同一个节点列表里撞名。

        get_one("库存实时统计", cond=["仓库编码", "产品编码"], empty="分支"),
        data_branch(found=[
            update("库存实时统计", {"当前库存数量": inc(ref("本次出库数量"))}),
        ], missing=[
            add("库存实时统计", {...}),
        ]),
    """
    return {"type": "data_branch", "name": name or "数据判断",
            "found": found or [], "missing": missing or []}


def compute(name, expr, fields, decimals=2):
    """运算节点（落库 type=function）。做流程内的加减乘除。

    expr   用 `$名字$` 占位；fields = {名字: ref(...)}，每个占位符给出取值来源。
    decimals 小数位。

        compute("算当前库存", "$总入库$ - $总出库$", {
            "总入库": ref("总入库数量", node="获取单条数据"),
            "总出库": ref("总出库数量", node="获取单条数据"),
        })

    引用结果用 `result("算当前库存")`。流程里做不了算术的老限制到此解除；
    但仍建议：能用工作表**公式字段**算的派生量，优先用公式字段。
    """
    return {"type": "operation", "name": name, "expr": expr,
            "fields": fields or {}, "decimals": decimals}


def get_more(table, cond=None, sort=None, limit=0, from_=None, name=None):
    """取多条 =。from_ 取某节点结果，不传则直接查表。"""
    return {"type": "get_more", "table": table, "cond": cond or [],
            "sort": sort, "limit": limit, "from": from_,
            "name": name or ("获取多条%s" % table)}


def update(table, mapping, name=None, source=START):
    """更新[表]:字段。mapping = {字段名: 值}；值是字符串/数字=固定值，`ref(...)`=引用。"""
    return {"type": "data_update", "table": table, "mapping": mapping,
            "source": source, "name": name or ("更新%s" % table)}


def add(table, mapping=None, from_=None, name=None, source=START):
    """新增[表]。mapping 不给则用流程上下文行整行。"""
    return {"type": "data_add", "table": table, "mapping": mapping or {},
            "from": from_, "source": source, "name": name or ("新增%s" % table)}


def approve(name, users=None, roles=None, mode=1):
    """审批[名称]。users=账号列表（**裸账号，如 `["admin"]`**），roles=角色名列表，mode: 1 或签 / 3 会签。

    审批人=发起人请用 `appr()`（本函数不点名审批人时会兜底成 admin）。

    ⚠️ **`approverIds` 不能带 `user.` 前缀**（那是消息节点 `toUserIds` 的写法）：带上时
    save/deploy 全绿、记录新增也起实例，**但任务谁都收不到**（2026-09-16 实测）。
    三种办理人落库形态不同，见 gotchas #90；表单字段/部门类办理人本 DSL 不支持（`assigneeByVariable`），
    需手写 `approverGroups`（部门字段还要 `isNeedTranslateToUserIds: true`）。
    """
    return {"type": "approver", "name": name, "users": users or [],
            "roles": roles or [], "mode": mode}


def fill(name, users=None, roles=None, who=None):
    """**填写节点**（落库 type=`edit`）——办理人**打开表单边看边改**，与审批节点不同。

    ⚠️ `approve()` 落的是**审批节点** `approver`（只显示审批按钮，不展示表单）；
    「边看单子边处理」「要改表里的字段」「要设节点字段权限」这些场景用的是**填写节点**。

        fill("主管审批")                                  # 发起人填写（生产默认）
        fill("仓库收货检验", users=["张三"])               # 指定人填写
        fill("财务处理", who="部门负责人")                 # 按表达式取人

    who 只能取 `APPLY_EXPR` 的三个名字之一（发起人 / 部门 / 部门负责人）。
    不给 users/roles/who → 默认「发起人」。要设字段权限，建完流程后调
    `/act/process/extActProcessNodePermission/saveOrUpdateBatch`（见 `field-perm-rule.md`）。
    """
    return {"type": "edit", "name": name, "users": users or [], "roles": roles or [],
            "who": who}


def appr(name, who="发起人"):
    """审批[名称]，**审批人按表达式取**（默认流程发起人：`assigneeByExp` + `${applyUserId}`）。

    who 取 `APPLY_EXPR` 的三个名字：发起人 / 部门 / 部门负责人。

    落库形态（回读 processJson 确认过）：
        approverGroups[0] = {approverType: "candidateUser",
                             assigneeType: "assigneeByExp",
                             expressionsIds: ["${applyUserId}"],
                             expressionsNames: ["获取发起人"]}
    `expressionsNames` 就是设计器卡片上显示的填写人，别塞表达式原文。
    """
    return {"type": "approver", "name": name, "users": [], "roles": [],
            "mode": 1, "who": who}


def gateway(name=None, branches=None, default=None):
    """网关→分支。branches = [{name, cond:[(字段,规则,值)], nodes:[...]}, ...]
    规则用中文别名：等于/不等于/大于/大于等于/小于/小于等于/包含/属于/为空/不为空。
    最后一个不给 cond 的分支视为默认分支。

    ⚠️ **被判字段是「流程中途才填」的（新增页隐藏、审批/填写节点内填）时，本助手建出来的
    分支恒判失败、永远走默认支** —— 网关的 `attr.branchForm.formNodeId` 由 builder 固定写
    `"start"`（取触发那一刻的行快照），中途填的值不在快照里。这类分支必须**建后外科改成
    「产出该值的 edit/approver 节点 id」+ `formNodeType:"table"`**（save 前改，部署后改要走
    重建），规则与实测见 gotchas #89。触发时就有值的字段（新增页可填）不受影响。
    """
    return {"type": "exclusive", "name": name or "条件分支",
            "branches": branches or [], "default": default}


def record_id(node=None):
    """「传 record id」——上游 `add()` 建出来的那条记录的 id。

    用在 call_sub 传参里（线上模版每个逐行子流程的第一条参数都是它）：

        add("其他出库单", {...}, name="添加记录")
        call_sub("采购退货-其他出库-子流程", pass_={"id": record_id()})

    node 不传 = 最近一个 `add()`；传了就写那个 `add()` 的节点名。
    ⚠️ 它**不是** `ref()`：落库形态是 `{variableName:"记录id", variableValue:"_id",
       formNodeType:"plus", formNodeId:<新增节点 id>}`，套 ref() 会取到空值。
    """
    return {"$record_id": node}


def call_sub(sub_name, multi=True, pass_=None, name=None, via=None):
    """调子流程（callActivity）。multi=True 逐行调用（逐行调子流程[名]）。

    pass_ = {子流程参数名: 值}，对应 `subflow(params=[...])` 里声明的变量：
        call_sub("销售出库-更新库存-子流程",
                 pass_={"仓库编码": ref("仓库编码"), "仓库名称": ref("仓库名称")})
    ⚠️ 子流程里 `var("X")` 用到的每个参数，这里都必须传——漏传不会报错，
       子流程里那个字段**永远是空的**，跑起来像「什么都没发生」。

    **multi=True 时前面必须有 `get_more(..., from_="start")`**（取本单关联明细）——
    它就是子流程的「选择数据对象」；不传 via 时取最近那一个，传了 via 就写那个节点名。
    没有数据对象 → 设计器里数据对象空白、子流程绑不上、运行时一行都不进子流程。
    """
    return {"type": "subprocess", "sub": sub_name, "multi": multi,
            "pass": pass_ or {}, "via": via,
            "name": name or ("调用%s" % sub_name)}


def delay(minutes=1, name=None):
    """延时 N 分钟。"""
    return {"type": "time", "minutes": minutes, "name": name or ("延时%d分钟" % minutes)}


def note(title, users=None, content="", kind="system", name=None):
    """发消息通知。kind: 系统消息 `system` / 邮件 `email` / 钉钉 `dingding` /
    企业微信 `weixinqy`（落库分别变成 `message_system` / `message_email` /
    `message_ding` / `message`）。

    users 是**收件人姓名**列表（也可写 `role.xxx` / `dept.xxx`）。
    ⚠️ 收件人**只认显式名单**：`toUserExpression`（如 `${applyUserId}`）实测无效，
    要发给发起人得走「变量收件人」写法，见 `miniflow-node-types.md` 8.1b。
    """
    return {"type": "notice", "title": title, "users": users or [],
            "kind": kind, "content": content, "name": name or "发送通知"}
