# 全链路新建（应用 + 工作表 + 关联 + 简流 + 盘；灌数按需，非默认）

> **需求只有一句话 / 没逐表列字段？** 先读 `requirement-design.md` 把它补成完整设计（`design.md`），**发给用户确认后**再回到本页建造。

**只读两页**：本页 + **`engine-contract.md`**（引擎硬约束一页纸——那十几条**不报错、
只静默写坏**，写规格前必须先读完）。读完第一条 tool call 必须是执行脚本。

> **② 文档分「契约类 / 操作类」，读法不同。判据只有一句：违反它会不会当场报错？**
>
> | 类型 | 判据 | 读法 | 本 skill 里是 |
> |---|---|---|---|
> | **契约类** | 违反**不报错**、只静默写坏 | **写规格之前**精读一遍（就一遍） | `engine-contract.md`、`app-spec.md` 的「四条硬规矩」、miniflow `node-contract.md` |
> | **操作类** | 违反**会报错** | **执行到那一步之前**才按节 grep 切片，**禁止通读** | `postbuild-kit.md`、`fast-create.md`、dashboard `create.md`/`mutate.md` |
>
> 2026-09-28 进销存 47 表实测：把操作类的 `postbuild-kit.md`（448 行）**通读**花了 8 分钟，
> 占整轮最大一段空档 —— 而实际只用到 `RENAME` / `DEFAULTS()` 两节。
> **「不读契约」和「通读操作手册」是两种错，别用后者去防前者。**

> **一句话建应用**（没有逐字段需求，要自己写规格/流程/冒烟）另外**按节查**，别通读：
> `requirement-design.md`（全文，设计层）· `app-spec.md` 开头骨架 +「写规格时的四条硬规矩」·
> `postbuild-kit.md` 第三节（配置写法）· `smoke-flows.md`「配置」「审批断言」两节 ·
> `miniflow/references/batch-flows.md`「两个批量构建器的签名对照」· `dashboard/references/create.md`「批量建盘」。
> 2026-09-24 担保-一句话11：这 8 份逐份读完花了 230 秒（全轮 1/3），按上面的节查就够。

> ⛔ **第三页（读一眼标题即可，别通读）**：`app-prompt-skeleton.md` 的**第 11~30 条**
> **+ 第五节「成组出现的需求要按原文逐条点名核对」**
> —— 那是「需求语言 → 规格语言」的硬规则清单（明细=双向关联而非设计子表、
> 审批「或」条件、看板宽度/筛选面板/图表标题…）。
> ⚠️ 该页第 25、26 条（`/` 单位后缀与 RENAME 顺序）**已于 2026-09-24 作废**，
> 见该页原文更正 —— **别再照做**。
> **2026-09-23 的教训**：这些规则**早就写在那页里了**，但全链路这条路由**从不指向它**，
> 于是当轮原地重踩了「看板非标宽度」「盘名与工作表同名」两条，多花一轮返工。
> **2026-09-24 同型第三次**：53 表应用里 **4 处默认值漏配**，同样是因为本页只指到
> 「11~30 条」、没指第五节 —— 而第五节课文里连「11 条只铺 8 条」的实例都写着。
> 建后套件已同步加 ⚠（见 `postbuild-kit.md` 3.2）。
>
> **2026-09-24 同型第四次 —— 变体：知识就在本页，照样漏。** 15 处【子表】全漏，
> 而「③ 建完必须再跑一次转换」就写在本页 §③-b、我也读了本页 —— 区别是那儿只有散文、
> 又没点名套件里现成的 `SUBTABLES`，于是五道闸门全绿。
> **写在同一页不算数：得让「漏做」有东西会失败 —— 归宿是 `struct_cfg.py` 的一条配置，
> 不是交付说明里的一条待办。**
> 那页的条目按编号/节标题查，**不要通读全文**。

**第一步：开工作目录**（`python "<lowapp>/scripts/skill_temp_path.py" --new <应用名的英文简称>`，如 `crm`）——
本次所有手写配置（`app_spec.json` / `flows.py` / `struct_cfg.py` / `dashboards.json` …）都写进它打印的目录；
`build_app --spec <工作目录>/app_spec.json` 建出应用后把 app_id 绑进目录里的 `app.json`，三个 skill 的脚本产物随后都按 app_id
自动落回这个目录（见 SKILL.md「临时目录标准」）。**并行建多个应用时每个代理各开各的**；别自己另起目录，也别写到 `jeecg-lowcode/` 根下。

**禁止：** 并行 Read `jeecg-lowcode-lowapp` / `miniflow` / `dashboard` 的 SKILL.md 全文；`memory_search`；`miniflow-node-types.md`；`example/入库审批*.md`；`widget-options`；`json-config`；`desform-lowapp.md` 全文；`--help` 再确认。

> **动真机前先过 `scripts/precheck.py`**（纯静态、不联网、可反复跑）：
> `python scripts/precheck.py --spec app_spec.json --flows flows.py --struct struct_cfg.py --expect "表单=52,字典=22,看板=25"`
> （`--struct` 可选：读建后套件的 DEFAULTS，已给初值的累加目标不再报「缺初值」）
> 拦的是**本来要真机才暴露**的错：公式占位符、带出字段名、看板透视空 `val`、
> 查询面板跨表、流程 `ref/cond` 引了本行没有的字段、**网关单出口带条件**、
> **标题只靠关联带出**。
> 2026-09-16 建 52 表应用实测：不过这一关，每一类错都要付一次 3~9 分钟的重跑。
>
> ⚠️ **`--flows` 必须带**（2026-09-17 实测事故）：漏传时**流程段整段不跑**，
> 却照样打印「✓ 可以动真机了」—— 那一轮 63 条流程带着 19 个静态就能查出的错上了真机，
> 代价是一轮 19 条失败 + 两轮 234s 全量重发。现在**漏传会被直接拦下**（目录里有
> 带 `FLOWS =` 的 `.py` 就报错），确实没有流程时用 `--no-flows` 显式跳过。
> 另外：有提示时收尾语变成「✓ 预检通过（有 N 条提示，逐条确认过再动真机）」——
> **提示里躺着的正是「接口全绿但内容错」那类**（19 张表的标题就是这么漏掉的），别不看。

**预算（2026-09-16 实测，走 `build_app.py`）：**

| 规模 | 墙钟 | 瓶颈 |
|---|---|---|
| 4 表全流程 | **20 秒** | — |
| 52 表 6 段 | **约 6 分钟** | 建壳数分钟；补丁已不再是瓶颈 |
| 单段 | 流程 52 条 **51 秒**；看板 25 张 **22 秒** | 都很快，别怕批量 |

> **补丁段的瓶颈已修**（2026-09-16）：原先 52 张表**串行**读设计 ≈ **4 分 31 秒**，
> 而每次跑补丁都要付一遍。真凶不是并发度，是 `query_form()` 里
> `get_form_id` 逐表走的慢路径（每表 2~3 次 HTTP）。
> 现在 `prewarm_form_ids()` 用 `/online/lowApp/miniflow/tenantAppFormList` **一次**拿全
> 「编码→ID」，再加 4 并发读 —— **4 分 31 秒 → 5.2 秒**。
> 注意：各轮之间**本来就不重读**（设计读进内存后各轮在内存里重算），优化点只在第一遍读。

**超标 = 在逐条手工拼、或又在读文档**，不是接口慢（读 5ms / 写 330ms）。
手工逐条时 63 条流程要 55 分钟、25 张盘要 42 分钟 —— 差的是**轮数**，不是速度。
另一类超标是**返工**：规格里一个静态错误 → 一次真机重跑。所以 `precheck.py` 是必需品。

（本页与 dashboard skill / multiform-template 同规则处**同步维护**：改 add-filter 约束等规则时两处同改，本页=全链路自包含优先。）

## ⓪ 先看规模：≥10 张表就走编排器，别手工串

`build_app.py` 一条命令跑完六段，每段回读计数、有缺口非零退出：

```bash
python "<lowapp>/scripts/build_app.py" --api-base URL --token TOKEN \
  --tenant-name "租户名" --app-name "应用名" --create-app --spec app_spec.json
```
`--tenant-name` **必填**（给了 `--tenant-id` 也要带，后续子步骤按名字认租户）。

> ⚠️ **`--create-app` = 必须新建**：租户里已有同名应用会**直接报错退出**（附已有 id），不再静默复用。
> 续跑已建的应用（`--from` / `--only`）请**去掉 `--create-app`、改传 `--app-id <id>`**。
> 2026-09-23 实测事故：旧行为下同名测试应用被当成新应用打了一整轮补丁（41 张表被改）。
> 起名前先 `lowapp_creator.py --json '{"action":"list"}'` 看一眼现有应用名。

规格格式（表名+字段名+关系，**只写业务语言**）见 `app-spec.md`。字段类型由 `spec_infer`
推断、关联/汇总/字典由 `patch_fields` 建、流程由 `build_flows` 建——都不用手写。
`--from 阶段名` 续跑，`--only 阶段名` 单跑。


> ## ⛔ 灌数是**例外**，不是默认
>
> **默认不灌数**（`--rows` 默认 `0`）。**只有用户在提示词里明确要求**
> ——「灌测试数据」「造示例数据」「填几条演示数据」「每个表来几条」——
> **才传 `--rows N`**。
>
> - **看不出要求 = 没要求。** 需求写「建一个 XX 应用」而不含灌数字样 → 不灌。
> - **别为「让看板有东西看」擅自灌**：那是用户没要的数据污染，清起来比灌起来更麻烦。
> - **空盘是正常交付态**：看板/报表打开时实时查库，没数据就是没数据，不是缺陷。
> - 收尾说明里写明「未灌测试数据」，别让用户以为漏了。
>
> 灌数是最贵的一段（级联写 + 全表抽样回读），且**会改变阶段顺序**（见下）——
> 只在真要它时才付这个代价。

> ## ⓪-b 规格写不下的东西 → 建后套件，**别现场手写补丁脚本**
>
> 子表转换、记录范围、批量添加、关联标题、编号规则、必填/隐藏/宽度、改名、**一切默认值**、
> **按钮触发的简流**、填写节点与字段权限、自定义按钮、列表视图、导航隐藏、功能开关——
> `app_spec.json` 都表达不了。以前这段靠现场写 8~10 个补丁脚本（2026-09-21 CRM 24 表实测：
> 整轮 39.9 分钟里 26 分钟耗在写和想这些脚本上）。现在：**读 `postbuild-kit.md`
> （首节是「建应用决策速查」，先拿它分拣需求）→ 写配置（只有中文名）→ 跑 `postbuild_*.py`**。
> 全部支持 `--dry-run`、幂等；覆盖不到的单项照旧回落手写（该页「回落」节）。
> 本页 ③-b / ⑤ / ⑧ 的规则不变，套件只是把它们固化成了脚本。

**手写各段只在表数很少、或要做编排器覆盖不到的定制时。**下面 ①–⑦ 是各段的做法。

用户点名了顺序就跟点名。
**默认：①应用 ②分组+工作表 ③双向关联 ⑤简流 save+deploy ⑥按钮绑简流 ⑦仪表盘。**
**④灌数只在用户要求时插入**，插入时**必须排在 ⑤简流 之前**。

> ⚠️ **要灌数时，④灌数 必须排在 ⑤简流 之前。** `add_data` 会触发该表的
> tableEvent 主流程，而主流程普遍带「取多条 → 逐行调子流程」——灌 N 行 = **N 轮级联写**。
> 2026-09-15 实测照旧顺序跑：**1 小时 4 分，后端崩一次**；2026-09-16 复现：52 条流程建好后
> 再灌数，**6 分钟没跑完，后端直接失联**（同一天干净顺序只要 3.7 分钟）。
> 流程还没建时先灌：无级联。这条以前只写在注释里、靠人记得，现在 `build_app.py`
> 的灌数段会**主动拦住**（应用里已有流程就报错退出，见 `stage_data`）。
>
> **注意：不灌数时这条约束自动消失** —— 默认路径（① ② ③ ⑤ ⑥ ⑦）没有这个风险。

凭证：本轮消息或本会话已有的 api-base / token；租户按**名**匹配（`--tenant-name`），禁止用默认 `X-Tenant-Id:2` 冒充点名租户。Windows：中文只进 UTF-8 JSON / `.py`，禁止 `python -c` 内联中文。

---

## ① 应用（零预读）

```bash
python "<lowapp>/scripts/lowapp_creator.py" --api-base URL --token TOKEN \
  --tenant-name "租户名" --config create_app.json
# create_app.json: {"action":"create","appName":"应用名"}
```

⚠️ **规格给了应用的图标/主题色/封面就一定要传，不要省**——不传走脚本默认值 `iconType=ant-design:schedule-outlined`、`iconBackColor=rgb(0, 188, 212)`、`appCoverImg=coverImage002`，**撞对两项也是巧合**，封面基本必错（2026-09-16 用户实测：「图标/颜色/封面 这个是不是没有对上」→ 只有封面错，前两项恰好等于默认值）：

```json
{"action":"create","appName":"应用名",
 "iconType":"ant-design:schedule-outlined", "iconBackColor":"rgb(0, 188, 212)",
 "appCoverImg":"coverImage009"}
```
改已有应用（`action:edit` **必须带 `id` 或 `fromName`**，只给 appName 会报「JSON 必须提供 id 或 fromName」）：`{"action":"edit","id":"<app_id>","appName":"...","iconType":"...","iconBackColor":"...","appCoverImg":"..."}`；`action:list` 回读三项核对。

打印的 `tenant_id` / `app_id` 后面全用，禁止再 list。

## ② 分组 + 工作表（同一对话轮，可先分组后表）

分组：`init_lowapp` 后 `create_worksheet_group(group_name=…)`（函数在 `desform_lowapp_utils`，不要打开 `desform-lowapp.md`）。

工作表：Write `job.json` → `create_linked_worksheets.py`（字段写法见 `fast-create.md`，**不要**打开 json-config）。公式修正 / link-field 关联带出 / 流水号规则 / 隐藏键的补丁契约全在 `fast-create.md`「建后补丁契约速查」一张表，随取随用。

- `forms[].code` 必须全局唯一：自带短后缀（如日期），禁止探 `get_form_id`。
- `forms[].fields` + `titleIndex` 直接写；radio `options` 数组、`required`/`defaultValue` 可写。
- 多表互指关联：**先不写 `link`**，表建完走 ③。单条一对一才用 `link`。
- 表建完 `get_menus` + `move_worksheet_to_group(menu_id, group_id)`。
- ⛔ **建完必须排菜单顺序**（分组顺序 + 组内顺序）：并行建表的 `orderNum` 天然错乱且会重复，
  首个分组的 `parentId` 还是 NULL（永远排最前）。走 `build_app.py` 时它按规格的 `菜单顺序`
  （没写则按 `forms` 书写顺序）自动强排并回读；手写各段时调
  `apply_menu_order([(分组, [表...]), ...])`（`desform_lowapp_utils`，写完回读、幂等），
  已有应用用建后套件的 `MENU_ORDER`。**别照需求里的「建议创建顺序」排菜单** —— 菜单顺序看的是需求的分组清单。

## ③ 双向关联（`add_link_record.py`）

> ⛔ **写 `links` 时最容易漏的是「父→子」方向那一条**（2026-09-24 生产管理 53 表实测）：
> 子表侧的「子→父」写了，父表侧的「父→子」漏了 → 那个字段被 `infer()` 兜底成**单行文本**，
> 界面上本该是**明细表格**的地方变成一个输入框。**四道闸门全绿** ——
> `app_audit` / `postbuild_verify` 都是拿**规格**当基准，规格里没这条 link 就没有比对对象。
> 现已由 `precheck.py` 的 `check_table_named_fields` 判 **err**（字段名与另一张工作表同名却无
> 对应 link，零误报），**动真机前跑一次 precheck 就能拦下**。
> ⚠️ 之前 `check_undeclared` 其实报过，但混在一条 188 项的 ⚠ 里等于没报——现已剔除。

job **必须** `tenantName` + `appName`（`target` 同样要 `appName`+`worksheet`）。**不要只写 `tenantId`/`appId`** → 脚本报 `缺少应用`。

不同表可并行；**同一张表**的多个关联必须串行。

脚本不写 twoWay。两边字段都成功后，**同一脚本** `get_form_fields` 一次 + 两边 `update_widget(..., {"options":{"twoWayModel": 对方 model}}, key=本方 key)`。不要停下来告知「v1 不支持」。

⚠️ **`showFields`（显示字段）要主动给**：不传即落 `[]`，关联卡片/明细表里只显示标题一列，用户会当成「字段没勾上」（2026-09-16 实测反馈「显示字段 提示词里面没有，导致没有勾选」）。需求没写就按业务取 2~6 个关键列，或直接问一句。写法与判据 → `fast-add-link-record.md` 的 `showFields` 行。

> ⚠️ **`showFields` 的形状 = `["<model>", "<model>", …]` 纯字符串数组**（2026-09-20 实测，用户报「要求展示多个字段，怎么只展示了一个」）：
> 写成 `[{"field": "<model>", "show": true}]` **不报错、也不生效** —— 引擎认不出该形状，
> 回落到只显示标题一列，接口 save/deploy/回读全绿。**正确形状就是纯字符串数组**
> （例：`["select_depart_…"]`，或三个裸 model 字符串并列）。
> 手写补丁前先 `query_form` 读一个**本次建出来的**关联控件回读核对（自读自校），别凭记忆写。
> **两个连带坑**：① 数组里混进 `divider`/`tabs` 这类**非数据控件**的 model 是静默的（表格里多一列空白）；
> ② 按**中文名**取 model 时若目标表有**重名控件**（如 拜访记录 的分隔符「拜访内容」与多行文本「拜访内容」——
> 后者落库被加了 `#textarea_…` 后缀），`fields['拜访内容']` 拿到的是**分隔符**，要按 `type` 复核。
> 验收：逐个关联控件把 `showFields` 的 model 拿去**目标表**的 model 集里命中，并断言无 `divider`。

### ③-b 子表（关联工作表）—— ③ 建完必须再跑一次转换

⛔ **需求原文出现「子表」二字（并点名了从哪张工作表取数）时，③ 建出来的不是终点。**
`create_linked_worksheets.py` 的 `link` 和 `add_link_record.py` 产的都是**普通 many 关联记录**：
`isSubTable`、`model: sub_table_design_<key>`、两侧 `twoWayModel` **三处一处都不会落**。

> ⛔ **别手搓 —— 填 `struct_cfg.py` 的 `SUBTABLES`，`postbuild_struct` 一次转完**
> （`[(主表, 子表控件, 明细表, 明细表里回指主表的字段), …]`，见 `postbuild-kit.md` 决策表第 1 行）。
> 漏做时 `precheck` / `build_app` / `postbuild_run` / `app_audit` / `postbuild_verify` **没有一处会失败**：
> 2026-09-24 53 表应用 **15 处【子表】全建成普通关联记录**、`SUBTABLES` 空着，五道闸门全绿，
> 是用户在设计器里逐个翻出来的。
> **清单按需求原文逐条点名抽，禁止按控件名去重**（同日实测 `【子表】需质检的产成品`
> 出现两次、挂两张父表：去重得 14，实际 15）。
>
> ⚠️ **明细表无回指字段 = 需求写漏，不是"要不要转"的问题。**
> **先照搬同应用同类子表的成对写法补上再转，别停下来问**（2026-09-24 实测 15 处里 1 处）。
> 要问的是「写漏的字段按什么补」（命名 / 是否成对 / 显示列 / 默认值挂谁）——**不是「要不要转成子表」**；
> 补完在交付说明里点名「需求清单外新增的字段」。
> 唯一需要用户定的取舍：**明细表已有的回指字段被多个父表争用**（互指只能选一个）。
> **同理：「控件是子表」与「业务规则点名锁定它」是两个独立维度** ——
> 15 处里只有 8 处需求在「动作：锁定（只读）→ …」里点了名，另外 7 处
> **只转、不要动规则目标**（补了就是超需求改动）。

转换 4 步见 `desform-link-record.md`「二-a」，在本表 links 全部成功之后、`layouts` 之前跑：
主表侧顶层 `isSubTable:true` + `model` 改 `sub_table_design_<控件key>` → 两侧 `twoWayModel` 互指
→ `save_auth_from_design(主表code)`（auth 按 model 存）。
⛔ **主表汇总的 `options.linkTable` 不要动**：它存的是明细控件 **key**，key 在转换中不变。
改成 `sub_table_design_…` 会让设计器「关联表」下拉解析不到、直接显示原始串，而 save/回读/precheck 全绿
（2026-09-21 实测报障）。详见 `desform-link-record.md` 二-a 第 3 步。

> ⚠️ **判据是需求有没有写「子表」，不是控件长得像不像。**
> `显示:"表格"` 落库就是 `showType:"table"`，明细区本来就是一张表格 ——
> **看着像子表，设计器面板里仍是「关联记录」**（顶层没有 `isSubTable`、`model` 还是 `link_record_*`）。
> 2026-09-20 实测事故：16 表应用 53 个关联控件，`isSubTable` **0 个**，而需求里明确写过「子表」；
> 当时本文件与 `engine-contract.md` 提「子表」**0 次**（知识只在 `desform-link-record.md` 二-a，
> 而全链路这条路不读它）—— `save` / `回读` / `precheck` 全绿，只有用户打开设计器才发现。
>
> **验收（缺一项就是没转成）**：主表控件 `isSubTable is True` 且 `model.startswith('sub_table_design_')`
> 且后缀 == 控件 `key`；子表回指字段 `twoWayModel` == 主表**新** model；主表 `options.twoWayModel`
> == 子表回指字段 model（**两侧都要写，只改主表侧是"半转"**）。
>
> ⚠️ **转换时禁止「整组套用 options」——`hiddenOnAdd` 必须按需求原文逐条核对**（2026-09-21 实测）。
> 一次转多个子表时最省事的写法是"同一组 options 套给每个控件"，`hiddenOnAdd` 恰好混在里面 →
> **需求没写「新增时隐藏」的子表也被勾上了**。后果是静默的：save 成功、回读设计 JSON 正常、
> `isSubTable` / `twoWayModel` / `showFields` 三项验收**全对**，**只有人打开新增表单才发现整块不渲染**
> （用户原话「XX 子表没有创建吗」—— 建了，只是新增页看不见；上一轮两道闸门一条都没拦住）。
>
> **判据：「新增时隐藏」属于哪个控件，只看需求把那句话写在谁后面。**
> 需求写「**Tabs(新增时隐藏** …)」时，隐藏的是**页签容器**（`tabs` 控件）——
> 页签里装的关联控件、以及 **Tabs 之外的独立子表字段，都不带这个属性**。
> 所以转换只该动三项：`isSubTable` / `model` / 两侧 `twoWayModel`（**汇总 `linkTable` 不在内**）；
> **其余 options 一律保持控件原样**，确实要改的按需求原文**逐条点名写**。
> **回读断言：逐个子表控件打印 `hiddenOnAdd`，与需求原文逐条对照**（不是数个数对不上才查）
> —— 与本节末尾「逐条属性核对，不是计数核对」是同一条纪律。
>
> ⛔ **`model` 换名是「引用面」级变更，不是主表内部改一个键。** 上面三条验收只覆盖主表自己——
> 换名后**所有指向旧 model 的地方都会静默悬空**，而 `save` / 回读 / `precheck` /
> `check_node_contract` **一个都不报**（它们只查结构，不解析引用）。
> **做法：转换 4 步跑完后，拿旧 model 串在整个应用的 design JSON + 所有流程的 `processJson`
> 里 grep，命中即改，验收口径是旧 model 全应用 0 命中。** 已知会命中的面（按易漏程度排）：
> ① 其他表的 `link-record.options.showFields[]` / `filters.rules[].field`（**跨表，最易漏**）；
> ② ~~主表 `summary.options.linkTable`~~ —— **不在此列**（2026-09-21 更正）：它存的是控件 **key**，不受 model 换名影响，动了反而坏；
> ③ 本表 `formula` 表达式里的 `$<model>$` 占位；
> ④ 简流分支条件的 `field` / `data_update.updateFields[].field`。
> ⑤ **`config.bizRuleConfig[].actions[].value[]`（业务规则「锁定（只读）」的目标列表）**——
>    按 model 存，就在 `desformDesignJson['config']` 里（与 ①②③ 同一次 grep 覆盖）。
>    转子表后要把**新 model 补进去**，规则才锁得住它；没补则规则在、条件对、`save` 全绿，
>    而「转成子表能不能被锁」的验证**是空的**（2026-09-24：目标 24 个里没它，用户测不出任何东西）。
>    ⚠️ 这档 `SUBTABLES` **不覆盖**，转换后逐表单独补。
> ⚠️ ④ 有反直觉处：条件里该字段的 `type` **仍是 `link-record`**，不是 `sub-table-design`。
> ⚠️ **转换前抓的字段表快照（`fetch_form_fields` / 中文名→model 映射）在转换后整份作废**——
> ④ 建简流时若复用 ③ 阶段缓存的那份，条件会写到已不存在的 model 上而**不报错、也不生效**。
> 转换后必须**重新抓一次**，别省这一次往返。
> 整单回存前把字典控件 `options.remote` 置回 `'dict'`。

## ④ 简流（只 import `miniflow_creator`，禁止打开 node-types / 入库审批示例）

同一 `.py`：`fetch_app_forms` + `fetch_form_fields` 解析中文名 → `build_process_json` → save → deploy。全程 py ≤2 次。

> ⛔ **写第一个字之前先确认：改名（`RENAME`）做完了没有 —— 这是本段的第 0 条规则
> （2026-09-22 进销存 47 表实测，代价：17 条子流程字段解析失败 + 一整轮返工）。**
>
> `build_flows` 是**按「中文字段名」解析**的。`RENAME` 换的是控件显示名（key/model 不变），
> 设计器内部 `$model$` 引用安全，**但流程源码里的中文名会全部对不上**。
>
> **正确顺序**（不可交换）：`build_app`（**不带 `--flows`**）→ `postbuild_struct`（含 `RENAME`）
> → `postbuild_defaults` → **再写/跑 `build_flows`**。
> **流程源码里直接写改名后的名字**（`ref("成本单价/元")`、`add()/update()` 的 mapping 键、
> `cond` 的字段名），别等报错再补。
>
> 漏改的症状是 `FAIL:sub … 'XX 里没有字段 成本单价'` —— 不会静默，但一条失败拖住整批。
> 已写完才发现要改名时：回扫流程源码用**负向前瞻** `名字(?!/元)` + **最长优先**排序
> （`收款金额` 是 `已收款金额` 的子串，用「已含 `X/元` 就跳过」的守卫会整批漏掉，本轮实测漏 12 处）。
> 详见 `postbuild-kit.md`「3.1 `struct_cfg.py`」的 RENAME 块。

> ⛔ **建完 subEvent 子流程必须再补发一轮 —— 这是本段的第二硬规则（2026-09-22 进销存 47 表实测，
> 代价：25 条子流程白建 + 父流程被闸门整体拦下 + 一整轮返工）。**
>
> `build_flows.py` 对子流程报 `OK:sub …`、`deploy` 也全绿、`/act/process/extActProcess/list` 里也
> `processStatus=1`，**但记录的 `customProcessId` 是 `None`** → 引擎把定义 key 拼成坏 key `process`，
> 父流程的 `callActivity` 永远找不到定义（阶段①.5 闸门会报
> `FAIL:barrier … 在引擎里没有已部署定义`，**25/25 全中**）。
>
> **补发 = 一条命令**（建完子流程、建父流程之前跑；实测 25 条 **42 秒**）：
>
> ```bash
> python scripts/postbuild_subpub.py --api-base … --token … --tenant-id … --app-id …
> ```
>
> 幂等可反复跑；`--check-only` 只核验现状、`--dry-run` 只列待补发的、退出码 2 = 有失败项。
> **核验/判据口径统一为定义 key 本身**：`GET /act/process/extActProcess/queryById?id=<DBid>`
> → `result.processXml` 是 base64，解码后 `<process id="process<DBid>">` 才算注册成功。
>
> ⚠️ 判据**不能**用记录里的 `customProcessId` —— `saveFlow` 拿它拼 BPMN 但**不回写该列**，
> `queryById` 回读恒为 `None`，拿它当判据会把 25 条已就绪的流程全报成「待补发」（2026-09-22 实测）。
> ⛔ **也不要用 `/act/process/list` 核验 —— 该接口实测 read timeout，白等 5 分钟。**
>
> 脚本内部的配方（miniflow `gotchas #47`，2026-09-03 定论），手写补丁时照抄：
> ① `POST /act/designer/miniDesFlow/api/saveFlow`（**form-urlencoded，不是 JSON body**）带
> `id/customProcessId=<DBid>/processKey=process<DBid>/processName/processType=oa/lowAppId/startType=subEvent/processJson/updateCount`；
> ② `PUT /act/process/extActProcess/deployProcess` body `{"id":"<DBid>"}`。
>
> **建父流程之前必须跑这一步**；`--force` 只是"承认带病继续"，不是修法。
> `build_app.py` / `postbuild_run.py` 目前都**不含**这一段——建完子流程、建父流程之前，手工插一次。
>
> ✅ **2026-09-28 修：`build_flows` 的 ①.5 屏障已改用同一条权威判据（`queryById` + `processXml`）。**
> 在那之前它判的是 `/act/process/list` —— 正是上面写着「read timeout、别拿它核验」的那个接口，
> 于是出现最坏组合：`postbuild_subpub` 报「30/30 已就绪」，**同一次运行的屏障**报「30/30 未注册」，
> **补发之后重跑屏障仍然全红**（进销存 47 表实测，连报两趟、白烧一轮）。
> 现在屏障是两层：① 逐条 `queryById` 解 `processXml`（**权威**，就是 `postbuild_subpub` 用的口径）；
> ② 只有 ① 报缺口的，才再用 `/act/process/list` 兜一次**并集**（它会被超时吞成空集，
> 所以**只能救误报、不能一票否决**）；① 全过时**根本不发那个请求**（省掉它的超时等待）。
>
> **因此正确顺序是**（不要再插一轮空跑）
> `build_flows` 建子流程（被屏障拦下 = **预期路径**）→ `postbuild_subpub.py`
> → **`postbuild_subpub.py --check-only` 确认 `异常 0`** → **原命令重跑 `build_flows`**（屏障自动放行，父流程正常建）。
> ⛔ **不要绕过 `--check-only` 直接 `--force`**：`--force` 把「真没注册」和「判据读不到」一起放行，
> 而这两者在运行期的后果完全一样（`FlowableObjectNotFoundException`）。只有 `--check-only`
> 明确报出失败、且你判定可以带病继续时才用 `--force`。

> ⛔ **建完父流程之后，必须再跑一次子流程收尾修复 —— 这是本段第三硬规则（2026-09-23 进销存 47 表实测，
> 代价：6 条子流程被打回 `tableEvent` 误触发 + 13 条 `subFlowSourceInfo` 为空 + 一整轮排查）。**
>
> 上面 ⑤.5 的 `postbuild_subpub.py` 只认**已经是 `subEvent`** 的子流程，
> 而 `build_flows` 的「父流程回填趟」在 ⑤ 之后**又重存了一遍子流程**，把其中一部分的
> `startType` 打回 `tableEvent` —— 它们会变成普通表事件流程，在上下文表被写时**误触发**；
> 同时 `subFlowSourceInfo`（「被以下工作流触发」）也被清空。
> 两者都**不报错**，`save`/`deploy`/条数/`app_audit` 全绿；只有 `check_node_contract`
> 的「其中子流程 N 条」会少（19 而不是 25）。
>
> **一条命令收尾（幂等，建完父流程后必跑）**：
>
> ```bash
> python scripts/postbuild_subfix.py --api-base … --token … --tenant-id N --app-id A --expect 25
> ```
>
> 它从**各父流程 `processJson.subFlowList` 反推**该修哪些子流程（权威来源，不靠名字猜），
> 逐条重存 `startType=subEvent` + `customProcessId` + `processKey` 并回填 `subFlowSourceInfo`，再 deploy。
> 判据 = `startType` + `subFlowSourceInfo` + `processXml` 解出的定义 key **三项全对**；
> `--check-only` 只核验、`--dry-run` 只列计划、退出码 2 = 有失败项。
> **排位**：⑤ 建父流程 → **⑤.6 本步** → ⑥ `check_node_contract`。详见 `engine-contract.md` #7-d。

> ⚠️ **建 `edit`（填写）节点必须写 `content`**（= 填写人**显示名**，如 `'直接上级'`），否则设计器卡片显示灰色的「**设置这个节点**」未配置占位，用户会以为流程没建好。界面自己拼「填写人：」前缀，落库只放显示名；手建的节点设计器会自动写这个字段，脚本建的不会（2026-09-15 实测，用户指出「手动的就没有」）。
> **显示名 ≠ 表达式原文**：填写人是表单字段就写字段中文名；填写人是表达式/内置解析（`assigneeByExp`+`${applyUserId}` 等）要写**语义名**（`'获取发起人'`，即同节点 `approverGroups[0].expressionsNames[0]`）；角色/岗位/部门写对应名称。把 `assigneeByExp(${applyUserId})` 原样塞进 content，画布卡片会把这段代码直接显示出来（2026-09-16 用户指着卡片纠正「这里应该是 获取发起人」，已自愈重发）。收尾回读断言 content 非空且**不含 `$`、不含 `assigneeBy`**。

同轮要建 **≥3 条流程：直接跑 `../../jeecg-lowcode-miniflow/scripts/build_flows.py`**，
不要在对话里逐条拼 `processJson`。它吃一个声明式 `flows.py`（用 `flow_dsl` 写，
字段/表名一律中文，引擎自己换 code/model）：

```python
from flow_dsl import *
FLOWS = [
    flow("巡检计划-审批", "巡检计划", on="新增", nodes=[
        approve(name="主管审批", users=["admin"], mode=1),
    ]),
]
```
```bash
python "<miniflow>/scripts/build_flows.py" --api-base URL --token TOKEN \
  --tenant-id N --app-id A --spec flows.py
```

> ⚠️ **重跑失败项必须带 `--only`**（2026-09-17 实测）：`--update` 是**无条件全量重存+重发布**，
> 63 条流程实测 **234s**，而且**什么都不改也一样跑满**。只改了几条却整批重发 =
> 每次返工白烧 4 分钟。重跑时把 `FAIL:` 行里的流程名抄进 `--only`，被点名主流程
> 引用到的子流程会**自动带上**：
> ```bash
> python ".../build_flows.py" ... --spec flows.py --update --only "调拨-其他出库单,销售换货"
> # → OK:only 只处理 2 条（点名 1 + 依赖子流程 1）…… 8.6s   （对比全量 234s）
> ```
> 流程名写错会当场 `SystemExit` 列出，不会静默少建。

> ⚠️ 这里**曾经是一条死链**：老版本写「先读 `create-flow.md`『批量建流程』节」——
> 那份文档讲的是单条流程怎么拼 `processJson`，**从来没有指向批量引擎**。
> 结果是几十条流程那轮跑了 **55 分钟 0 产出**（逐条拼、撞 32000 输出上限）。
> `build_flows.py` 现在一次 50+ 条实测 **51 秒**。别再逐条拼。

骨架抄 `create-flow.md`：

| 需求 | 组合 |
|------|------|
| 有则更新 / 无则新增 | **D** |
| 按钮改当前行 | **E**（buttonEvent 的 `attr.formTableId=None`；save 前自愈 `updateFields`） |
| 审批通过后按关联多条逐行改库存 | **F**（主流程 opinion + 子流程 D；getType=3 外科重写内嵌在 F，勿开 node-types） |

子流程：三层 `startType=subEvent`；save 后 `register_subprocess_id`；再按 create-flow **#47** 补 `customProcessId=<DBid>` 保存并 deploy；**按 `queryById.processXml`（不是 `/act/process/list`）确认 key=`process<DBid>` 已注册**才建父流程。

审批人：username/realname **精确**匹配点名 → 角色写 `approve(roles=["角色名或 roleCode"])`，**落库 roleIds 必须是 roleCode**（`build_flows` 按 `/sys/role/list` 自动解析，查不到直接报错；2026-09-24 前它把角色**名**原样写进 roleIds，三个应用任务全部无人可收） → 否则 `candidateUser` + `admin` + 该用户 `realname`。禁止把 `roleCode=admin`（超管角色）当成「管理员」。按部门负责人取人用 `appr(who="部门负责人")`（`${flowNodeExpression.getDepartLeaders(applyUserId)}`）；旧表达式 `${applyUserDeptLeaderId}` / `${applyUserDeptId}` 在本机 Flowable 报 Unknown property，实例起不来。

> ⚠️ **审批组四种形态写错都是静默故障**（save/deploy 全绿、实例照起，**只是任务没人收到**，2026-09-16 用户实测报障）：① 指定成员 = `candidateUser`（单数）+ `approverIds:[**裸账号**]`（**不带 `user.` 前缀**，那是消息节点 `toUserIds` 的写法）；② 发起人 = `candidateUser` + `assigneeByExp`；③ 办理人=表单**用户**字段 = `candidateUsers`（**复数**）+ `assigneeByVariable`；④ 办理人=表单**部门**字段 = 同上 **再加 `variableContent[].isNeedTranslateToUserIds: true`**（缺它部门不展开成用户 → 部门成员全收不到）。
> 验收判据只有一条：`/act/task/myTodo` 里任务是否出现在**该办理人**的待办（`/act/task/list` 的 `taskAssigneeId` 对表单字段类不回填，不能当判据）。最稳 = **正反例对照**：同一部门字段选「该用户所属部门」应出现、选「其不在的部门」应不出现，一次排除"兜底给发起人/管理员"的假阳性。详见 miniflow `gotchas #90`。

## ⑤ 自定义按钮

`desform_custom_button.py --config`：`clickThen=confirm` + `flowStatus=true` + `conditionsGroup`（字段中文名）。先有真实简流 `flow_id`，再 `action=update` 把 `processId` 换成它。不要等 y/n。

## ⑥ 仪表盘（敲敲云盘，禁止积木/大屏/门户）

`PYTHONIOENCODING=utf-8` + `PYTHONPATH=<dashboard/references>:<.../scripts>`。

同壳串行：`create-page --group 点名分组 --name 看板名` → 按表 `add-charts --form-code --specs-file` → `add-buttons` → 跨表则**每表一次** `add-filter --specs-file`（**禁止**给 add-filter 传 `--form-code` / `--form-name`）。

- 关联维写中文名；按日 `dateGroup:"3"`；本月 `queryRange:"month"`；饼 `percentLabel:true`。
- 透视 `charts` 匹配「表格」或 componentName。
- 4 个 KPI 同行各 `w:6`；半行图 `w:12 h:32`。
- specs 用 Write / `json.dump` 无 BOM；成功立刻删临时 JSON。

## ④ 灌数（**仅用户明确要求时**；并发 + 后台，勿逐条串行干等）

> ⛔ **本段是例外，不是默认。** 用户没在提示词里点名要灌数 → **整段不做**，
> `--rows` 留默认 `0`。用户点名了 → 才往下读，且注意它**必须排在简流之前**。


**用 `scripts/mock_data_fill.py`**，它是**规格驱动**的，不是「改顶部 FIELDS 即跑」的模板：

```bash
python "<lowapp>/scripts/mock_data_fill.py" --api-base URL --token TOKEN \
  --tenant-id N --app-id A --spec app_spec.json --rows 3
```

两遍灌，顺序不能反：① 先灌所有表的**标量**（文本/金额/数字/日期/选项），
② 再灌**关联记录**（单条→随机挑一条目标表记录；多条→挑 K 条回填 id 数组）。
汇总字段的值来自子记录，所以必须先有 ② 才有数。

**执行默认：写数据串行跑**（`WORKERS = 1`）。2026-09-16 实测推翻了原先「并发 8~16」的写法：

| 方式 | 每次写入 | 依据 |
|---|---|---|
| **串行** | **0.044s** | 25 次：0.09 + 23×0.04 + 0.05 |
| 4 并发 | 0.065s | 48 次 / 3.1s |

服务端把并发写全序列化了 —— **加并发换不来吞吐，只换来争用开销**，而连接池只有 20。
8 并发实测把池子占干 → `CannotCreateTransactionException: Could not open JDBC Connection
for transaction` → 请求积压 → **后端进程直接倒下**。串行在这台环境下是又快又稳那一侧。

`get_form_fields` 取字段（纯读，单次 4~5.6s）**另给 4 并发**：52 张表串行要 4.3 分钟，
那才是灌数「看起来卡住」的真正原因。读不占事务，风险与写不同，所以两者不用同一个数。

灌数 Bash 用 `run_in_background: true`，**与绑图/看板并行**——盘只依赖表单结构、不依赖行数据
（页面打开实时查数），灌数不是绑图前置。完成后 TaskOutput 收结果。

**数据量分级**：≤50 条 → 并发 `add_data`；50~1000+ 条 → 1 次整批 `POST /desform/data/importXls/{desformCode}`；直连 SQL 仅纯演示且用户授权才用。

`get_form_fields` → `add_data`。关联记录：id **数组** + `model_dictTextPrint`。radio/select 固定值=选项文案。date 按 timestamp 写毫秒 + `_dictText`。

**键一律用 model（`fields[中文名]['model']`）**：写中文字段名会**静默入库**——`list_data` 看得见值、界面**整列显示空**（2026-09-11 仁和医院「科室信息」10 条全空实踩，详见 `desform-data-utils.md` 开头 ⚠️）。灌完**按 model 键抽样回读**，只数行数查不出来。

**`add_data` 会触发 tableEvent 主流程 —— 这不是「属预期」就完事了，它是级联写的入口。**
流程建好后每写一行都可能拖动几十次下游写。所以灌数**必须在流程之前**（见文首 ⚠️）。
若应用里已经有流程，`build_app.py` 会拦住；手工单独跑时自己确认清楚。

改状态：**不要** `batch_update`（常报「参数缺失」）→ `list_data` 取 `desformData` 再
`edit_data` 整单合并。**`edit_data` 是全量覆盖**，只传要改的字段会把该行其余字段清空。

---

## ⑧ 交付闸门（**一条命令**，外加下面那张手工表）

```bash
python "<lowapp>/scripts/app_audit.py" --api-base URL --token TOKEN \
  --tenant-id N --app-id A --spec app_spec.json --flows flows.py \
  --struct <配置目录>/struct_cfg.py \
  --expect "表单=47,字典=32,看板=16"
```

`app_audit.py` = `precheck.py` 的**联网姊妹件**（那个不联网、动真机前跑；这个每段跑完跑）。
**跑过建后套件就必须带 `--struct`**：审计只吃规格，而 `RENAME` / `TO_LINKFIELD` / `DELETE_THEN_MOVE`
让规格名与真机分家——不带它，CRM 60 条、销售管理 13 条「声明 input → 实际 link-field」「控件缺失」
全是假阳性（2026-09-22 四应用实测）；带上后三个应用违例 0。流程条数只在**少于** flows.py 时违例
（套件的按钮流/审批流不在 flows.py 里）；看板标题只在规格写了 `ui` 时查下标 0；排宽按覆盖行算。
**输入只有 spec + flows，零应用知识**，所以任何应用/任何提示词通用。一次覆盖：
规模计数、字典条数、流程条数与启用、**控件类型/档位**、**标题字段**、**关联记录**
（条数·显示 / 双向互指 / 带出是否 `saveType=save`）、**汇总**、**中转字段**、
**流程要用到的键**（从 `ref()`/同名 `cond` 推导）、**流程里的取值**（真机 `processJson`
每处字面量拿表单 options 对照）、**看板**（盘标题位置、每排宽和、图表字段真实存在）。

先跑 `--form <表名>` **单表小样**，别整批跑完才发现解析写错。

> ⚠️ **`app_audit` 不查布局——交付前另跑两项**：① 按需求的半行/整行/1-3 逐字段设 `options.autoWidth`
> （顺序在 `regroup_layout` **之后**，否则被重算冲掉）；② 逐页签回读 `panes[].list` 核对容器没漏搬。
> 规则见 `app-spec.md` 的 layouts 节与「容器」节。

> ⏱ **实测墙钟（2026-09-22 进销存 47 表 / 53 流程 / 16 盘）：`app_audit` 单跑 = 278 秒（4.6 分钟）。**
> 它是**全轮最慢的单条命令**（要回读 47 张表设计 + 53 条 `processJson`），
> 但**不是**"最后一项要 40 分钟"的来源——那种体感来自**它之前的返工轮**（见 ④ 的子流程补发硬规则）。
> 预算：把 5 分钟留给它，不要在它前面再省那 42 秒的补发。
>
> **它还查「调子流程传参的字典文案」**（`attr.variableList` 里的字面量 vs 目标字段 options）——
> 实测 `build_flows` **不会**把 `call_sub(pass_={"账向": "增加应收"})` 翻成存储值，落库就是文案，
> 这里会报 `传参 … 像是「X.账向」的显示文案（存储值 '0'）`。**写 `pass_` 时直接写存储值**（`"0"`）。

### ⑧-b 端到端冒烟（**默认不跑**，用户要求时才跑）

> ⛔ **默认不跑，连 `smoke.py` 都不用写。** 交付一个应用**不包含**端到端冒烟。
> 这一段的真正开销不是脚本（实测 8 秒 ~ 2 分钟），而是**写冒烟配置**（要为每条链路设计最小单据、
> 期望值、别名依赖）**加上排查它查出来的问题**——两项加起来常常比建应用本身还久。
> **只有用户明确说了**「跑一下冒烟 / 做端到端验证 / 验证流程跑通」才做这一段：
> 那时才写 `smoke.py`、才执行脚本。看不出要求 = 没要求，**不写配置、不跑、不提交**。
>
> **但交付说明里必须写明**：「三道结构闸门全绿，**未做端到端验证**——流程是否真的写对未经运行验证」。
> 别把「闸门全绿」说成「流程没问题」，这两件事不是一回事（下一段就是原因）。
>
> **例外：一句话建应用（走 `requirement-design.md` 路由）必跑**，按该页第三节的最小集：每条分级审批（设计里有才测）高低阈值各一单（断言落点 + 进待办）+ 一条主链路回写。理由：设计是你补的、用户没逐条审过，而审批人配错是**四道闸门都看不见**的静默故障（2026-09-24 第 1 轮三个应用全踩）。配置写法见 `smoke-flows.md`。
>
> **什么时候值得主动提醒用户跑一次**：应用里有台账/记账/累加（`inc`/`dec`）、跨表回写、
> 子流程逐行处理这类流程时——这些正是结构检查看不见、一跑就错的重灾区。提醒一句即可，别擅自跑。
>
> ### ⛳ 2026-09-23 实证：一次冒烟抓出 **4 个真缺陷**（进销存-标准版，47 表 / 52 流程）
>
> 交付时 `check_node_contract` 违例 0/提示 1、`app_audit` 违例 0/提示 0 —— **全绿**。
> 8 个用例的冒烟一跑，**账全是错的**：
>
> | 抓到的问题 | 结构闸门 | 冒烟 |
> |---|---|---|
> | 79 条公式里 **30 条恒空**（表达式含全角 `×` `÷` / `IIF`） | 看不见 | ✅ |
> | 19 条**链式公式不重算**（改了 `销售出库数量`，`当前库存数量` 停在旧值） | 看不见 | ✅ |
> | 盘亏建出的凭证单**库存永远不动**（建单/明细/触发的**顺序竞态**） | 看不见 | ✅ |
> | `get_one empty=` 错位 → 每轮往明细表扔**空行** | 看不见 | ✅ |
>
> **成本对照**：写 `smoke.py`（8 个用例）≈ 20 分钟；**不跑的话这 4 个缺陷会原样交付**，
> 而它们每一个都让「账本」这个应用的核心功能失效。**带台账/记账的应用，这一段的性价比是正的。**
>
> ⚠️ **两个踩坑记录**：
> 1. **残留判据不能只看「带标记的行」**——错位新建的**空行**没有任何文本列，标记兜底扫不到；
>    收尾要**数一遍全表行数**（`sum(total)`），不能只看「带标记残留 0 条」。
> 2. **断言要打在「账」上**，不是「流程跑了」上：只断言「凭证单建出来了」会漏掉
>    「建出来了但没记账」——同一张单要同时断言记账位（`库存已记账=是`）**和台账数量**。

```bash
python "<lowapp>/scripts/smoke_flows.py" --api-base URL --token TOKEN \
  --tenant-id N --app-id A --config smoke.py --flows flows.py
```

`app_audit` / `check_node_contract` / `precheck` **全是结构检查**，「流程跑起来账对不对」一条都看不见。
2026-09-21 进销存（47 表 / 56 流程）实测：三道结构闸门全绿的应用里藏着「第一笔入库丢账」
「公式值累加把库存冲成 0」「同事件两条流程只跑一条」「判据取金额字段恒判错」—— 全靠造单回读才暴露。
`smoke_flows.py` = 造最小单据 → 触发流程 → 轮询回读断言 → 按记录 id 清理（断言零残留）。
配置只写中文名与显示文案，**写法见 `smoke-flows.md`**（别去翻脚本）；审批流用用例的 `approval` 断言测落点与待办、`approve_all` 办结后验回写，收尾自动清本次实例。
**验收口径：`RESULT fail=0` 且「带标记的残留 0 条」。** 实测 12 个用例 / 28 条断言约 40 秒。

> **两条纪律（2026-09-21 从零重建进销存实测，合计白烧约 15 分钟）：**
>
> 1. **复跑只跑失败用例：`--only "<用例名>"`。** 每个用例的 `wait` 是串行硬等（5 个用例 ≈ 2 分钟纯等待），
>    改完一处又全量跑，等于把已经通过的用例再等一遍。脚本失败时已在末尾打出 `HINT: --only "…"`，照抄。
> 2. **结构校验与冒烟结论冲突时，以冒烟为准，先跑冒烟再改结构。** 三道结构闸门查的是「形状」，
>    冒烟查的是「账对不对」；形状规则本身也可能错。实例：`check_node_contract` 曾对每个喂多实例
>    子流程的取多条报「selectType=3 应为 1」（与它上一条「带 linkFormTableField 必须 =3」直接打架，
>    按契约建出来的节点无解），作者按它连改四种结构、每改一次重发流程 —— 而一次「一单三行」冒烟
>    三行全部记账成功，直接证明 3 是对的（规则已收窄成「不在 (1,3) 才报」）。
>    **看到一条改不掉的结构违例，先花 40 秒跑冒烟，别花 10 分钟改结构。**

下面那张表是**脚本覆盖不到的补充项**，照旧逐项回读，**不要只看脚本自己报的「成功」**：

| 项 | 怎么读 | 判定 |
|---|---|---|
| 分组 / 表单 / 看板 | `get_menus(app_id).menuList` 按 `type` 分组计数 | 与规格一致 |
| 字典 | `/sys/dict/getDictListByLowAppId` | 22 条 |
| 流程 | `/act/process/extActProcess/listProcess`，按 `openStatus`+`processStatus` 均为 1 过滤 | 全部启用 |
| **流程节点契约** | **跑 `jeecg-lowcode-miniflow/scripts/check_node_contract.py`** | **违例 0 条** |
| **中转字段** | 回读 design：字段在、`options.hidden=true`、`advancedSetting.defaultValue.value` = `$<父关联控件key>.<父表字段model>$` | 三项都对（默认值空 = 台账行永远没有那个关联记录） |
| **流程里的取值** | 真机 `processJson` 的每处字面量（`queryItems[].val` / `updateFields[].val` / `formModel`）拿该字段的 `options[].value` 对照 | 写的是**存储值**、不是页面显示名（写「是」而库里存 `"0"` → 条件恒不成立，流程静默不触发） |
| **流程字段映射** | 需求里每条「新增记录中的【X】」逐条对齐该 `data_add` 的 `formModel`**条数**（契约校验只管结构键，**不看映射全不全**） | 条数一致 |
| **表单布局** | 每张表回读 design，数 `divider` 与 `card` 子字段数 | 有分节、每卡 ≤3 字段 |
| **控件类型 / 档位** | 逐字段比对「需求声明的控件 vs 实际 `type`」；连带比档位键（日期 `options.type`、他表字段 `options.saveType`）。做法与判据见 `app-spec.md`「`类型`」节末尾 —— **必须做全量比对，报告口径是「不符 0 处」**。⚠️ 抽查会漏：本轮先只发现 6 个金额字段，全量比对才又抓出 16 个「选择用户」+ 2 个「数字」（2026-09-21） | 不符 0 |
| **流程节点形态（需求原文 → 真机 `processJson`）** | 拿**需求原文点名的节点**当基准（获取多条 / 获取单条 / 运算统计条数 / 互斥分支 / 相容分支 / 子流程 / 审批 / 定时…），逐个对照真机节点 `type`。⚠️ **这一条没有机械闸门**：`check_node_contract` 只判「结构合法」、`app_audit` 只比 spec/flows 与真机 —— 两者都看不见「按需求该建的那个节点被换成了别的」。**闸门的 ⚠ 提示不是改结构的许可证**：`✗ 预检不通过` 才必须改结构；`⚠ 提示` 一律照原文建、在交付里标为已知风险。⛔ 2026-09-20 与 2026-09-22 **同一应用的同一个子流程连撞两次**（「获取多条 → 统计条数 → 互斥分支」被换成「取单条 + 数据分支」，理由是「闸门告警 + 同语义」），两次 save/deploy/契约/审计全绿。详见 `miniflow/references/batch-flows.md` 的「禁止语义等价替换」条 | 不符 0 |
| **金额字段的「类型」与「单位」** | 分开查，别只看一个：① `type == 'money'`（名字没「金额」二字的极易落成 `input`）② `options.unitText` 与需求原文一致（**`unitText` 会被静默丢弃而 `precision` 会落地**，别用 precision 当判据） | 不符 0 |
| **子表形态** | **从需求原文逐条点名**抽出每处【子表】（**同名控件挂不同父表算两处**：2026-09-24 实测 15 处，按控件名去重会得 14），逐条验：主表控件 `isSubTable is True` + `model.startswith('sub_table_design_')` + 后缀==控件 `key` + `options.showType=='table'`；明细表回指字段 `showMode=='single'`+`showType=='card'`+`twoWayModel`==主表新 model；两侧互指；最后拿**旧 model** 全应用 grep。⚠️ 转不成的（明细表**无回指字段**）要单独列出问用户，别默默跳过 | 该转的都转了、旧 model **0 命中**。⛔ **这一档没有机械闸门**：`precheck`/`build_app`/`postbuild_run`/`app_audit`/`postbuild_verify` **一个都不查**（2026-09-24 生产管理 15 处全漏，五道闸门全绿，用户在设计器里翻出来）。防复发靠 **`struct_cfg.py` 的 `SUBTABLES` 填满**，不是靠交付说明里写待办 |
| **关联记录子配置** | 需求写了就逐条比：`options.filters`（记录范围）、`advancedSetting.defaultValue`（默认带出）、`options.createMode.params.selectLinkModel`（批量添加绑定字段）、`options.twoWayModel` | 该有都有 |
| **引用完整性（key vs model）** | 逐控件把**每一处引用**拿真机设计解析一遍：汇总 `linkTable`（→本表关联控件 **key**）与 `field`（→明细表 model）、他表字段 `linkRecordKey`（**key**）与 `showField`（model）、关联记录 `titleField`/`showFields[]`/`twoWayModel`/`filters.rules[].model`/`createMode.params.selectLinkModel`、默认值 `$key.model$`（key 是本表关联控件、model 在目标表）、`linkage`/`linkDataConfig` 的 `desformCode`+`appId`+`rules`+`linkages`、`auto-number` 的 `field` 段、`formula` 的 `$…$`、**`config.bizRuleConfig[].actions[].value[]`（业务规则锁定目标，按 model 存）** | 解析不到 **0 处**。⚠️ 这类「**存了值但面板解析不到**」的缺陷 `save`/回读/`precheck`/契约检查**全绿**、运行时往往也正常，**只有打开设计器面板才看得见**（2026-09-21 汇总 `linkTable` 实测报障）。**凡是脚本之外手改过的引用键，必须单独验**——脚本按契约生成的反而稳。校验器要能自证：注入一处已知缺陷看它报不报，别让校验器本身悄悄退化 |
| **自定义按钮** | `desform_custom_button.py` `action=list` 逐表数个数；每个非空 `processId` 必须在**本应用**流程清单里（`lowAppId` 过滤）——纯表单按钮应为 `null`/`false` | 悬空 0 |
| **按钮条件值** | `conditionsGroup[].queryItems[].val`：link-record 用记录 id（纯数字）、字典控件用 `itemValue` | 无文案/无空值 |
| **列表视图** | 逐表 `action=list` 取视图，再 `action=get` 回读 `conditions` / `queryList` / `columnList`(show) / `hasSummary` | 与规格一致 |
| **功能开关** | 逐表 `get_switch_settings(code)`，数 `enabled=True` 的 code 个数 | 该开的全开 |
| **导航隐藏** | `get_menus(app_id).menuList[].hideFlag` | 该隐藏的 `=1`，其余 ≠1 |
| **导航顺序** | `check_menu_order(get_menus(app_id)['menuList'], [(分组,[表…]),…])` —— 比的是接口**返回顺序**（前端按它渲染），不是 `orderNum` 排序后的顺序 | 返回 `[]`。`postbuild_verify.py` 只查「排序号重复/为空、分组 parentId 混用 NULL 与空串」（不需要期望）；**「顺序对不对」要带期望比**，由 `build_app` / `MENU_ORDER` 写完回读 |
| **字典值形态** | 凡 `options.isDictItem` 控件，看按钮条件 / 简流写入（`data_update.updateFields[].val`、`data_add` 常量）/ 视图过滤 / **看板图内筛选（`config.filter.conditionFields[].fieldValue`）** 里是否出现该 model，值必须是 `itemValue`（如 `"0"`） | 无显示文案值 |
| 数据 | `list_data(code,1,2)`，值在 **`record['desformData']`** 里 | 非空 |

⚠️ **「流程全部启用」这一行不能单独用**。2026-09-17 实测：63 条流程全绿、全部启用，
但节点键一条都没发对（`data_add` 发的 `addFields` 引擎不认、`get_more` 没发 `selectType=3`、
`callActivity` 缺数据对象），应用整体不可用。
**计数对得上 ≠ 配置发对了**，必须再跑一次节点契约校验。

⚠️ **「字段一个不少」同样不是验收**。2026-09-20 实测：24 表 424 个字段名齐全、`precheck` 全绿，
但控件类型大面积错配——「下拉（选项来自别的表）」建成单行文本、22 个「日期时间」丢了档位、
89 个他表字段 `saveType` 恒 `view`（只显示不落库、被公式引用的在设计器里显示「字段已删除」）。
**按字段名比对看不见控件类型**，必须逐字段比 `type` + 档位键。

⚠️ **按钮条件值与字典值同样是「全绿但运行不生效」的重灾区**。2026-09-21 实测：18 个按钮全部建成功、
`processId` 全部非空，但其中 2 个条件写的是字典**显示文案**（`"未转换"`）而非 `itemValue`（`"0"`）、
1 条简流 `data_update` 写入值同样是文案；另有 5 个纯表单按钮残留了已删占位流程的 `processId`。
**这类值只在运行期匹配，回读设计 JSON 看着完全正常** —— 必须按上表两行显式比对。
按钮 `processId` 悬空与孤儿流程的成因见 `jeecg-lowcode-miniflow/references/batch-flows.md`
「改 / 重建单条流程的收尾」。

`build_app.py` 每段都会打 `[N/7 阶段] 期望 X / 实际 Y`，有缺口立即非零退出。
**静默通过是最坏的结果** —— 曾经有一次 app-id 写错、一张表都没读到，却报「补丁全部落地，
无缺口」并以 0 退出（`patch_fields.py` 的 `load_gaps` / `SystemExit(5)` 就是为堵这个）。

---

## 失败立刻改参短跑（不要再读文档）

| 现象 | 立刻做 |
|------|--------|
| `缺少应用` | job 补 `tenantName`+`appName`，去掉仅 ID 写法 |
| `unrecognized arguments: --form-code` | add-filter 删 `--form-code`/`--form-name` |
| `batch_update` 参数缺失 | 改 `edit_data` |
| save 500 Duplicate key | `startTaskId` 不要等于任何节点 id |
| deploy 成功但 callActivity 找不到定义 | 子流程补 `customProcessId` 再 deploy（组合 F / #47） |
| `FAIL:barrier N/N 条子流程未注册` | **别改流程、别 --force**：先 `postbuild_subpub.py --check-only` 核一遍——报 `异常 0` 就是屏障自己的判据过时（2026-09-28 前的 `/act/process/list` 会整批误报），装最新 `build_flows` 后原命令重跑即自动放行；真报缺口才补发。⛔ 别拿「闸门告警」当改结构的许可证（见 ⑧ 末条） |
| 编码已存在 / `[阻止]` | 换带日期后缀的 code，不要探 8 次 `get_form_id` |
