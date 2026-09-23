# 建后套件（postbuild_*）：规格语言写不下的东西，用声明式配置一次补齐

> **定位：提速，不改路线。** `build_app.py` + `app_spec.json` 照旧负责建壳；本套件只接管
> **建壳之后**那一段——以前这段靠现场手写 8~10 个补丁脚本（2026-09-21 CRM 24 表应用实测：
> 整轮 39.9 分钟里 **13.4 分钟在写脚本、12.9 分钟在想怎么写**，工具真正执行只有 4.1 分钟）。
> 现在改成：**写 4 份配置（只有中文名）→ 跑 6 条命令**。
>
> **不改任何现有脚本**，全部是新增文件；**覆盖不到的档位照旧回落手写**（见文末「回落」）。
> 每个脚本都支持 `--dry-run`（只报告不保存）且**幂等**，失败了改配置重跑即可。

## 一、建应用决策速查（先对着这张表分拣需求，再动手）

需求文档里的每一项，落到哪里：

| 需求里出现 | 写进哪 | 备注 |
|---|---|---|
| 分组 / 工作表 / 普通字段 / 字典字段 / 关联记录 / 汇总 / 公式 / 布局分节 | `app_spec.json` → `build_app.py` | 见 `app-spec.md`；先过 `precheck.py` |
| 应用级字典 | `app_spec.json`（或 `lowapp_dict.py`） | 选项**落库值是序号串** `"0" "1"…`，后面一律用 `dv('字典','文案')` 取，别写文案 |
| 字段名含 `/`（如 `金额/元`） | spec 里先写不含 `/` 的名字 → **`RENAME`** 改回 | 规格里斜杠=「与」，不是字段名（`app-spec.md`「斜杠是与」） |
| 「子表」「明细子表」「工作表子表」 | spec 里建双向关联 → **`SUBTABLES`** 转换 | ⛔ 转换不碰汇总 `linkTable`（它存控件 key） |
| 关联记录的**记录范围**（只能选本客户的联系人…） | **`FILTERS`** | |
| 子表「批量添加」（从另一张表勾选多行带入） | **`CREATE_MODE`** | |
| 关联记录显示哪个字段当标题 | **`LINK_TITLE`** | |
| 自动编号规则（前缀+日期+流水 / 引用本表字段） | **`NUMBER_RULES`** / **`FIELD_NUMBER_RULES`** | |
| 下拉选项来自另一张工作表 | **`LINKDATA`** | |
| 必填 / 隐藏 / 新增时隐藏 / 只读 / 禁用 | **`OPT_FLAGS`** | |
| 字段宽度（1/3、1/2、2/3 行） | **`WIDTH`** | |
| 建出来类型不对（该是他表字段却成了文本…） | **`TO_LINKFIELD`** / **`DELETE_THEN_MOVE`** | 先 probe 看实际类型再决定 |
| **任何默认值**（当前用户/部门、当天、静态值、取关联字段、查询工作表、函数计算） | **`DEFAULTS()`** | 默认值**一律建后配**，别往 spec 里塞 |
| 工作表事件触发的「审批 + 简单回写」流程 | `flows.py` → `build_flows.py`（`flow_dsl`） | 照旧 |
| **按钮触发**的流程 / 填写节点 / 节点字段权限 / 取关联明细逐行新增 / 查不到则新增 / **系统消息（含收件人·正文引用表单字段）** | **`postbuild_flows.py`** | `flow_dsl` 不出按钮流，其 `note()` 也做不了「收件人=表单字段」；**办理人=表单字段**（`assigneeByVariable`）同理 —— 这两样都只能走这里 |
| 自定义按钮（含显示条件、点击后填写/新建关联记录、绑简流） | **`BUTTONS`** | 先建流程再建按钮 |
| 列表视图（统计、显示列、快速筛选、数据过滤、排序、额外视图） | **`VIEWS`** | |
| 导航里隐藏某些工作表 | **`HIDE_MENUS`** | |
| 导航的分组顺序 / 组内工作表顺序 | spec 的 `菜单顺序`（新建）或 **`MENU_ORDER`**（已有应用） | 需求的分组清单就是顺序；「建议创建顺序」不是菜单顺序 |
| 功能开关全开 | **`SWITCH_ALL_ON = True`** | |
| 仪表盘 | dashboard skill | 不在本套件 |

## 二、运行顺序（6 条命令）

> ⚠️ 结构配置文件叫 **`struct_cfg.py`**，不要叫 `struct.py`：与标准库 `struct` 同名，配置目录里任何
> `import requests` 的脚本都会崩在 `zipfile → struct.calcsize`（2026-09-22 四个应用里三个撞到）。
> `postbuild_run.py` 两个名字都认，优先新名。

公共参数：`--api-base URL --token T --tenant-id N --app-id A`（下文记作 `$C`）。
工作目录默认 `{系统临时目录}/jeecg-desform/<app-id>/`，配置文件也放这里。

```bash
python scripts/postbuild_probe.py     $C                                  # ① 快照：probe.json + dicts.json（只读）
python scripts/postbuild_struct.py    $C --config struct_cfg.py   --dry-run   # ② 先看计划，MISS=0 再去掉 --dry-run
python scripts/postbuild_probe.py     $C                                  # ③ 转过子表/改过名 → 必须重拍快照
python scripts/postbuild_defaults.py  $C --config struct_cfg.py               # ④ 默认值（可与 ② 同一个配置文件）
python scripts/postbuild_flows.py     $C --config pb_flows.py             # ⑤ 简流（别叫 flows.py：与 flow_dsl 的 flows.py 撞名）
python scripts/postbuild_appconfig.py $C --config appconfig.py            # ⑥ 按钮/视图/导航/开关
python scripts/postbuild_verify.py    $C                                  # ⑦ 只读验收（引用完整性+子表不变量+流程启用+按钮绑定）
python ../jeecg-lowcode-miniflow/scripts/check_node_contract.py ...       # ⑧ 简流契约闸门（照旧必跑）
```

**一条命令版（推荐）**：把 `struct_cfg.py` / `pb_flows.py` / `appconfig.py` 放进同一个目录（缺哪个跳过哪段；`--work DIR` 可把 probe/dicts 也放进自定义目录），

```bash
python scripts/postbuild_run.py $C --dir <配置目录> [--dry-run] [--from struct|defaults|flows|appconfig|verify]
```

它就是按上面 ①~⑧ 的顺序逐个起子进程，任一段非 0 立刻停并提示 `--from` 续跑点。
⚠️ 全新应用上 `--dry-run` 只对 `struct` 段有意义：没真保存，改名/转子表没发生，后面几段会按旧名字报 `MISS`。
正常做法：`struct` 单独 dry-run 看一眼计划 → 去掉 `--dry-run` 整条跑。

- **退出码 2 = 有未解析的名字 / 失败项**，看 `MISS:` / `FAIL:` 行改配置重跑；**0 才往下走**。
- 顺序不能换：②改名/转子表 → ③重拍 → ④⑤⑥ 都按**改名后**的名字解析；⑤ 在 ⑥ 之前（按钮按流程名绑定）。
- ⑦ 自带 `--self-test`（往内存副本里注入 6 类坏引用，确认检查器本身没瞎）。

## 三、配置写法（全部写中文名；同名时默认取非分隔符控件，点名分隔符写 `'名称#divider'`）

> 下面的片段够写大多数应用。**完整样例**（24 表 CRM：7 个子表、132 个默认值、22 条简流、18 个按钮）在
> `references/postbuild-examples/crm/{struct,flows,appconfig}.py`——写法拿不准时按关键字 grep 它，**别通读**。
> 它同时是套件的回归基线：改了 `postbuild_*.py` 之后，对那套 CRM 应用跑
> `postbuild_run.py --dir references/postbuild-examples/crm --dry-run`，struct/defaults/flows/appconfig 四段都应是 0 差异。

### 3.1 `struct_cfg.py` —— 结构补丁（每个变量都可省略；`RENAME` 最后执行，其余项用**改名前**的名字）

```python
SUBTABLES = [('商机', '商机明细', '商机明细', '商机')]           # (主表, 主表上的子表控件, 明细表, 明细表里回指主表的字段)
#   ⚠️ 转换会换明细控件 model：流程必须在它之后建（build_app 不带 --flows）；已有流程引用旧 model 时本脚本打 TODO 并 exit 2
FILTERS = [('商机', '客户联系人', '联系人', '关联客户', '关联客户')]  # (本表, 本表关联控件, 目标表, 目标表字段, 本表比较字段) → 目标字段 等于 本表字段
CREATE_MODE = [('产品报价', '产品明细', '报价产品明细', '选择产品')]  # (主表, 子表控件, 明细表, 明细里用于批量勾选的关联字段)
LINK_TITLE = {'商机明细': {'商机': '商机名称'}}                  # {表: {关联控件: 目标表里当标题的字段}}
TO_LINKFIELD = {'合同订单': [('客户地址', '关联客户', '客户', '客户地址')]}  # (本表字段, 经由哪个关联控件, 源表, 源表字段) → 改成他表字段，保留 key/model
DELETE_THEN_MOVE = {'服务工单': [('客户联系人', 'input', '姓名', 'link-field')]}  # 删掉建错的那个，把对的搬到它的位置
_D = {'type': 'create_date', 'format': 'yyyyMMdd', 'dateFormat': 'yyyyMMdd', 'formatCustom': 'yyyyMMdd'}
NUMBER_RULES = {'客户': {'客户编号': [{'type': 'text', 'text': 'C-', 'value': 'C-'}, _D,
                {'type': 'number', 'mode': 2, 'start': 1, 'reset': 1, 'length': 6, 'continue': False}]}}
FIELD_NUMBER_RULES = [('商机', '商机编号', 'SJ-', '客户编号（中转）', '-', 3)]   # 前缀 + {本表字段} + 连接符 + 3 位流水
LINKDATA = [('线索', '线索来源', '市场活动记录', '活动名称')]         # 下拉选项来自工作表
OPT_FLAGS = {'商机': {'关联客户': {'required': True}}, '线索': {'客户': {'hiddenOnAdd': True, 'disabled': True}}}
WIDTH = {'线索': {'活动类型': 66.667, '协作人': 50}}                # autoWidth 百分比：33.333 / 50 / 66.667 / 100
RENAME = {'商机': {'预测商机金额': '预测商机金额/元'}}
```

### 3.2 `DEFAULTS()` —— 默认值（写在同一个 `struct_cfg.py` 里即可；用**改名后**的名字）

> ⚠️ **凡是会被流程 `inc`/`dec` 累加的数值列，都要有初值 0。**
> 空值上做「增加/减少」是**静默不生效**（那一次累加被吞掉，不是报错也不是 NPE），
> 而且 2026-09-22 进销存实测：`inc` 撞 null 还会连累**同一节点里其余字段一起不写**。
>
> 三条路径要分清（2026-09-22 进销存 R4/R5 两次实测更正）：
> · **流程 `add()` 建的行** → `flow_rules` 规则 2 自动补 0，不用管；
> · **页面新增的行** → 这里的 `static(表, 列, 0)` 生效；
> · **接口（`add_data`）建的行 → `static()` 不落**，默认值整套（`static` / `func` / 取关联字段）在 API 写入时都不触发。
>   所以**造数脚本必须自己把这些列显式写 0**，别指望 `DEFAULTS()` 兜住。
>
> `precheck.py` 会逐表提示缺初值的累加列。

```python
def DEFAULTS():
    current_user([('商机', '负责人'), ('线索', '负责人')]);  current_dept([('商机', '归属部门')])
    today([('产品报价', '报价日期')]);                        now([('跟进记录', '跟进时间')])
    static('线索', '线索状态', '未转换', '线索状态')     # 字典字段：第 4 个参数给字典名，脚本换成落库值
    static('商机明细', '折扣率', 100)
    take('商机', '赢率', '销售阶段', '销售阶段', '赢率')  # (表, 字段, 本表关联控件, 目标表, 目标字段) = 选了关联记录就带出
    same('商机', '客户编号（中转）', '客户编号')          # 取本表另一字段
    lookup('客户', '手机', '线索', '手机号', ('客户名称', '客户名称'))   # 查询工作表取第一条：(目标条件字段, 本表字段)
    lookup_count('客户', '该客户数量', '客户', ('客户名称', '客户名称'))  # 查询工作表计条数
    func('商机明细', '小计/元', '%s*%s*%s/100' % (F('商机明细', '标准价格/元'), F('商机明细', '数量'), F('商机明细', '折扣率')))
    func('合同订单', '合同订单编号', "CONCAT('HT-',%s,'-',%s+1)"
         % (F('合同订单', '客户编码'), COUNT('合同订单', '客户编码', '合同订单', '客户编码')))
    # F(表,字段) → $model$ ； COUNT(目标表, 目标条件字段, 本表, 本表字段) → 计条数的 LINKAGET 文本，可参与运算
```

### 3.3 `pb_flows.py` —— 简流（`button_flow` / `table_flow` 往里追加；节点 id、取值形态、save 前自愈都由脚本管）

```python
# 按钮：更新当前行 + 新增一条下游记录
button_flow('线索领取', '线索池', [
    upd('更新领取时间', '线索池', [('领取时间', sysdate())]),
    add('新增线索', '线索', {'客户名称': start('线索池', '客户名称'), '线索池id': start_id('线索池')})])

# 按钮：查不到则新增、查到则回写，最后删当前记录
_g = get_one('查询线索池记录', '线索池', [cond('线索池', '_id', start('线索', '线索池id'))])
button_flow('线索退回', '线索', [_g,
    branch('数据分支',          # ← 名字被强制成「数据分支」，引擎按名字判定（gotchas #113），别起业务名
           found=[upd('回写线索池', '线索池', [('领取时间', systime())], src=_g)],
           missing=[add('新增线索池', '线索池', {'客户名称': start('线索', '客户名称')})]),
    delete_cur('删除当前线索', '线索')])

# 按钮：新增主单 → 取关联明细 → 逐行新增明细并挂到新主单
_a = add('新增产品报价', '产品报价', {'关联商机': start_id('商机'), '审批状态': '草稿', '报价日期': sysdate()})
_m = get_more_link('取商机明细', '商机', '商机明细', '商机明细')     # (触发表, 触发表上的关联/子表字段, 明细表)
button_flow('创建报价单', '商机', [_a, _m, add('逐行新增报价产品明细', '报价产品明细', {
    '选择产品': more_id(_m, '商机明细'), '折扣率': more(_m, '商机明细', '折扣率'),
    '产品报价': added(_a, '产品报价')}, batch_from=_m)])

# 审批后写回状态（approver → data_update 直连）
button_flow('合同订单-发起审批流程', '合同订单',
            [appr('商务审批'), upd('审批通过', '合同订单', [('合同状态', '审批通过')])])

# 工作表事件：新增时触发 / 某字段改成某值时触发；填写节点；延时；排他分支
table_flow('开票申请-自查与财务处理', '开票申请', [fill('发起人（自查）'), fill('财务处理')],
           cond=trig('开票申请', '开票状态', '待进行'))
_g = get_one('查询应收计划', '付款计划', [cond('付款计划', '_id', start('回款单', '关联应收计划'))], empty=1)
table_flow('回款单', '回款单', [fill('财务审批'), delay('延时1分钟', 1), _g,
    exclusive('按回款状态分流', [
        when('回款单', '回款状态', '已回款', '已回款', [upd('应收计划已回款', '付款计划', [('应收计划状态', '已回款')], src=_g)]),
        otherwise('待进行')])])
table_flow('退款-红冲', '退货申请', [...], event='update', watch=['退款状态'], cond=trig('退货申请', '退款状态', '已退款'))

# 系统消息：收件人/正文都可以是**表单字段**（不是固定人/固定文本）
table_flow('签订销售合同后', '销售合同', [
    appr('部门经理审批', '销售合同', '销售部门'),
    _g := get_one('查询机会目录', '机会目录', [cond('机会目录', '目标客户', start('销售合同', '目标客户'))], empty=3),
    branch('数据分支',
           found=[msg('系统消息', '{机会名称}已签订销售合同，请安排下一步工作.',
                      to=[search(_g, '机会目录', '其他部门协同人员')],     # 收件人 = 查到的记录上的成员字段
                      body=[search(_g, '机会目录', '机会名称')])],        # 正文 {字段中文名} 占位符
           missing=[msg('系统消息', '机会目录中无此机会项目.',
                        to=[start('销售合同', '合同签订人')])])])          # 收件人 = 本单上的成员字段

# 节点字段权限：(流程名, 节点名, 表, 可编辑字段, 必填字段[, 隐藏字段])；没点名的字段只读可见
perm('回款单', '财务审批', '回款单', ['回款状态', '开票状态'], ['回款状态', '开票状态'])
```

- 办理人：`appr(name)` / `fill(name)` 默认=发起人；`fill('售后处理', '服务工单', '售后技术人员')` = 取表单成员字段。
- 字典字段的固定值用 `dv('字典名','文案')`；静态字典（radio/select 手写选项）直接写文案。
- 已存在的同名流程**跳过**；要重建用 `--replace 流程名,流程名`（之后重跑 ⑥ 重绑按钮）。
- `--dry-run` 会把配置生成的结构与**现网已部署流程**逐条比对，输出 `SAME` / `DIFF` / `NEW`。
- **系统消息 `msg()`**：收件人/正文引用表单字段时，引擎要的是两种**不同**的落库形态（6 键 `var.` 条目 / 4 键 ref
  → md5 → base64 存 `jsonContext`），肉眼看不出来、save/deploy 全绿但消息发不出去 —— 一律用 `msg()` 生成，
  别手写。`to=` 传 `start(t,成员字段)` 或 `search(get_one节点, t, 成员字段)`，正文里用**字段中文名**写 `{…}`
  占位符（字段名写错会直接报错）。消息节点必须挂在被引用节点**之后**、且在同一条链上。
- **子流程两处别漏**（都是闸门只报提示、但真会不通的档）：
  ① 流程级 `pj['attr']['subFormTableObject']` 要与 `start` 节点那份、`formTableList[0]` **三处一致**
  （空壳时子流程内 `ref()` 全取空、分支永远走 missing）；
  ② `subFlowSourceInfo` 必须在**该子流程最后一次保存时**显式回填 `[{mainProcessId, mainProcessName, nodeName}]`
  —— 重存父流程**不会**补（gotchas ③ 已证伪旧提示语），且子流程之后再被存一次就又清空。

### 3.4 `appconfig.py` —— 按钮 / 视图 / 导航 / 开关

```python
WZ = dv('线索状态', '未转换')
ST = {k: record_id('销售阶段', k) for k in ('进行中', '赢单')}   # 关联记录字段的条件值必须是记录 id

BUTTONS = [   # (工作表, 按钮名, 'execute'|'form'|'confirm', 显示条件或None, 表单配置或None, 绑定的简流名或None)
    ('线索池', '领取', 'execute', None, None, '线索领取'),
    ('线索', '退回', 'form', [C('线索状态', 'eq', WZ)], fill_fields('线索退回原因'), '线索退回'),
    ('客户', '退回', 'form', None, fill_fields(('所属公海', 'required'), '客户退回原因'), '客户退回'),
    ('线索', '转换', 'form', [C('线索状态', 'eq', WZ)], new_link('客户'), '线索转换'),   # 新建关联记录
    ('商机', '创建报价单', 'execute', [C('销售阶段', 'in', '%s,%s' % (ST['赢单'], ST['进行中']))], None, '创建报价单'),
    ('产品报价', '发起审批流程', 'execute', [C('审批状态', 'eq', '草稿'), C('产品明细', 'not_empty')], None, '产品报价-发起审批流程'),
]
VIEWS = {t: {'summary': True} for t in PROBE}                    # 每张表默认视图开数据统计
VIEWS['线索'].update(cols=['客户名称', '手机号'], extra=[
    {'name': '未转化', 'filter': [C('线索状态', 'eq', '未转换')], 'cols': ['客户名称'], 'qf': ['客户名称', '归属部门']}])
VIEWS['公海池'] = {'summary': False, 'qf': ['所属公海'], 'filter': [C('领取时间', 'empty')]}
VIEWS['销售阶段']['sort'] = [{'field': '创建时间', 'type': 'asc'}]
HIDE_MENUS = ['销售阶段', '商机明细']
MENU_ORDER = [('驾驶舱', ['经营驾驶舱']),                              # 看板分组可以先写：建盘前不存在只提示、跳过，建盘后 `--only menus` 再跑一次补齐
              ('市场及线索管理', ['市场活动记录', '线索池', '线索']),      # 分组顺序 + 组内顺序；隐藏的表也点名
              ('客户及商机管理', ['公海池', '客户', '联系人', '销售阶段', '商机明细'])]
SWITCH_ALL_ON = True
SEED = {'销售阶段': [{'销售阶段': '进行中', '阶段类型': '进行中'}, {'销售阶段': '赢单', '阶段类型': '赢单'}]}
# ↑ 基础数据预置：按钮条件 / 视图过滤里用 `record_id('销售阶段', '赢单')` 引用关联记录时，目标表**首跑必须先有这条记录**，
#   否则 KeyError（2026-09-22 CRM 实测）。键是字段中文名，按标题字段去重、幂等；段 0 在建按钮前执行。
```

- `--only buttons,views,menus,switches` 可只跑某几段。
- `--dry-run` 核对：按钮是否存在 + `processId` 是否指向目标流程；额外视图是否存在；导航隐藏；开关。
  （按钮条件/视图内部配置不做逐项比对——按钮条件由 `postbuild_verify.py` 查引用。）

## 四、已经固化进脚本的坑（**不用再记、不用再试**）

| 坑 | 现象 | 脚本怎么处理 |
|---|---|---|
| 汇总 `linkTable` 存的是明细**控件 key** | 转子表时顺手改成 `sub_table_design_…` → 面板显示裸字符串、汇总失效 | `SUBTABLES` 只动 `isSubTable` / `model` / 两侧 `twoWayModel` |
| 字典选项落库值是序号串 | 条件/默认值写文案 → 永远不匹配 | `dv()` / `static(..., 字典名)` |
| 字典列表接口的键名是 `dictItemsList` | 取不到选项 | probe 已处理 |
| 整单保存时字典控件的 `remote` 要保持 `'dict'` | 回写设计时容易带丢 | 保存前统一复位 `remote='dict'` |
| 建按钮会**自动生成占位流程**并写进 `processId`（纯表单按钮也会） | 按钮点了跑空流程；应用里多出一堆孤儿流程 | 建完立刻换绑/清空 → 回读 → 删占位 |
| 按钮 CLI：`list` 返回 `result.buttons`；stdout/stderr 混排；`update` 的 `changes:{}` 写法以前静默无效 | JSON 解析失败；绑流程没绑上却回 success | 已封装；CLI 本身也已修（`changes:{}` 与顶层字段两种写法都生效，2026-09-21 真机回归） |
| 导航隐藏接口对任何输入都回「编辑成功」 | 以为隐藏了其实没有 | 回读 `hideFlag` 断言 |
| 并行建表的菜单 `orderNum` 错乱且重复；首个分组 `parentId` 是 NULL、其余是空串（后端 `ORDER BY parent_id, order_num`） | 分组/组内顺序全乱；NULL 的分组永远排最前，只改 `orderNum` 修不好 | `MENU_ORDER`：先把 NULL 归一成空串 → 分组与菜单各发一次 `changeOrder` → 按**接口返回顺序**回读；`postbuild_verify.py` 另查排序号重复与 parentId 混用 |
| 功能开关有父子联动（见 `desform-lowapp-utils.md`「父子联动规则」） | 只发一部分容易父子不一致 | 13 项一次全发，已全开的表跳过 |
| 「= 当前日期」插 `+0D` 运算节点 | 契约闸门判违例 | `sysdate()` / `systime()` 系统变量 |
| 节点 id 有前缀约定（审批/填写、网关、延时各不同） | 手写容易写错 | 自动取号 |
| 审批后接「意见分支」保存报 mxGraph `getAbsolutePoints()` NPE（2026-09-21 本机三种 id 写法均失败） | 流程存不上 | 用 `appr → upd` 直连；驳回走审批节点自带按钮。**「不同意则写回作废」这一支目前不建，交付说明里要写明** |
| 数据过滤条件裸放根层 | 界面不显示、落库被吞 | 自动包进筛选组 |

## 五、回落（保证稳定的那条底线）

- 套件是**加速器，不是唯一入口**。某个档位配置里写不出来（或脚本报错一时修不了）→
  **只把那一项**回落成现场手写补丁，其余照常用套件；不要因为一项卡住整段弃用。
- 回落时照旧遵守：整单 `query_form` → 改 → `save_design_from_file` → `save_auth_from_design`；
  改完跑 `postbuild_verify.py` + `check_node_contract.py`。
- 「接口全绿」不是验收。套件的 `OK:` 行同样不是——**⑦ ⑧ 两条只读闸门过了才算**。
- 不灌数是默认（见 `fast-full-chain.md` 文首 ⛔ 段）；套件里没有灌数脚本。
