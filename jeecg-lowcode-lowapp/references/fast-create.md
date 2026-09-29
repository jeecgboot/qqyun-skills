# 租户 + 应用下建工作表 / 一对一关联（快路径）

> ⛔ **适用范围：已有应用下加少量工作表（一般 ≤3 张）/ 一对一。多表应用不属于本页。**
> 需求里出现「多张表 + 数据字典 + 关联记录 + 汇总 + 公式 + 视图」这类规模时
> （**有没有简流和看板都算**），走 `fast-full-chain.md` + `app_spec.json` + `build_app.py`。
>
> **2026-09-24 实测代价**：一个 53 表任务照本页走，结果——① 规格里写了 `unique` /
> `max`(附件上限) / `dec`(小数位) / `unit`(金额单位) / `scan`(扫码) / `owner`(拥有者)
> 六类字段级标志，本页的 job 格式**没列这些键**，全部静默丢弃，影响 **129 个字段项**；
> ② 关联/公式/汇总/子表/字典/业务规则/视图的建后补丁得**自己手搓六个脚本**，
> 而 `postbuild_*` 套件里本来就有；③ 唯一校验 `options.unique` 直到用户追问才发现是空的。
> `app-spec.md` 里这六类标志全是一等公民，连验收口径都写好了（「逐字段回读
> `options.unitText`，与需求原文对照」）。**低层通道不是不能建多表应用，是要你自己补完
> 上层工具已经做掉的事。**

只读这一页。读完立刻执行，不要再打开本技能 SKILL.md、`jeecg-desform`、`jeecg-system`、`desform-widget-options.md`、`desform-json-config.md`、`desform-cross-form-binding.md`。

**上次把「必须快」写在 SKILL 文末无效：** 开场已经读完 800 行 + 并行打开三个 skill，两表一对一墙钟仍约 6 分钟；真正跑接口约 50 秒。本页存在就是为了让第一条 tool call 变成跑脚本。

## 第一条 tool call

1. 用户消息里的 `api-base` / token 直接用。没有则对 `prompt_history.jsonl` **搜一次** `jeecg-boot` + `eyJ`；没有就问一句。禁止翻整个 `.grok/sessions`。
2. Write UTF-8 JSON 到 `skill_temp_path.py -f job.json` 打印的路径（`_jobs/` 下、文件名带时间戳）；属于一次建应用的一部分时，写进该次的工作目录。
3. 立刻：

```bash
python "<skill目录>/scripts/create_linked_worksheets.py" --api-base <URL> --token <TOKEN> --config <job.json>
```

Windows：中文只写在 JSON 文件里，禁止 `python -c`、禁止 PowerShell `--json '{"中文"}'`。不要等 y/n。字段没列全就让脚本用默认（编号/名称/金额/日期/状态）。

## job.json

```json
{
  "tenantName": "八匹狼租户",
  "appName": "关联记录应用",
  "forms": [
    {"name": "订单"},
    {"name": "订单支付记录"}
  ],
  "link": {
    "from": "订单",
    "to": "订单支付记录",
    "fromField": "订单支付记录",
    "toField": "所属订单",
    "showMode": "single",
    "showType": "card"
  }
}
```

| 字段 | 说明 |
|------|------|
| `tenantName` / `appName` | 用户原话即可。脚本先精确匹配，0 条再去掉末尾「租户」「组织」「应用」。⚠ 应用不存在时：job 加 `"createApp": true` 自动创建；不加则报错并提示两条出路（2026-09-15 起） |
| `tenantId` / `appId` | 会话已有 ID 就写这个，脚本不再 list |
| `forms[].code` | 可省略（脚本按表名稳定派生，**派生码跨应用全局唯一**）。⚠️ 同租户其它应用已有同名表时省略 code 会撞码 → `/desform/add` 502 空响应、creator 报「无法查找或创建表单」（`queryByCode` 可见异应用同码记录）——此时显式自拟唯一 code（日期短后缀）重跑即可，已有表不受影响。禁止自己 `get_form_id` 探编码 |
| `forms[].fields` | 可省略。要写：`{"name":"…","type":"input|radio|number|date|textarea|…","required":true,"options":["A","B"]}` + `titleIndex`。**不要**为此打开 json-config / widget-options。⚠️ 实测（2026-09-08 两次）：job 里字段级 `defaultValue` 键对**所有类型一律静默丢弃**（早期版本曾以为文本类生效，fields 接口回查 input/integer/phone/email 的 defaultValue 全空、integer 连键都没有）——默认值全部建后整单补 `options.defaultValue`（input/phone/email=字符串、integer/number=数字、radio/select=字符串、checkbox/多选=数组、开关=字面存储值、date/time=字符串），date/switch 若带空 `advancedSetting.defaultValue` 须删整个 `advancedSetting` 再 `save_design_from_file`；select-user/select-depart 默认当前登录人/部门整单补 `advancedSetting.defaultValue.value="#D:CURRENT#"`（与设计器保存产物一致；旧 `options.defaultLogin:true` 运行时兼容但面板不回显）、固定用户/部门默认值补 `#F:<username或部门id>#` 串联段（多选同写），org-role 固定角色直接 `options.defaultValue`=roleCode，详见 `desform-default-value.md`「select-user/select-depart — 当前登录与固定选择」；**date「默认当天」禁止 `options.defaultValueType:3`**（功能可用但设计器属性面板不回显）——写高级默认值 `advancedSetting.defaultValue`（① compose `$_CONTEXT_VAR_sysDate$` 系统变量 ② function `DATENOW()`），`defaultValueType` 保持 `1`，完整结构见 `desform-default-value.md`「date — 默认值类型」。建后回查必须覆盖**全部设了默认值的字段**，不要只查补丁字段 |
| `forms[].fields` date/time/switch | `dateType` 合法集（DATE 报错自述）：`year|month|quarter|week|date|datetime_s|datetime_sf|datetime`，**无 time**——纯时间（HH:mm:ss 含秒）用 `"type":"time"`。switch 的 `activeValue`/`inactiveValue` 配置项被丢弃但工厂默认恰为 Y/N（2026-09-08 实测） |
| ⚠️ **字典字段（radio/select/checkbox 绑定字典）禁止写进 job 的 `fields.options`**（2026-09-09 实测） | creator 会把 options **对象**的键名当成静态选项（快照变 "remote"/"dictCode"/…，dictCode/isDictItem 虽落上但选项全坏）。正确：job 里该字段只给 `name`+`type`，表建完后**整单补丁**：`query_form` → 该控件 `options` 写全 `remote:"dict"`+`dictCode`+`dictCodeAppId`+`isDictItem:true`+`options` 字典项快照（value/label/itemColor **抄 `lowapp_dict.py --action query` 当前项**）+`showLabel:true`/`useColor:true`+`props`，整单 `save_design_from_file`（回查 remote 归一化 false 属正常，判定看 UI 数据来源=数据字典）。汇总字段同理不在 job 里写（linkTable 是 link 控件 model，建表时不存在），建表+link 后按 SKILL「手工追加整行字段」整单追加 |
| `fields` 里 type=`formula`（2026-09-10 实测） | job 可写 `{"name":"公式","type":"formula","expression":"$数值$$整数$"}`（中文名占位自动解析）。⚠️ creator 落库 `mode=CUSTOM` 而表达式却是 SUM 拼接形态（两 model 无运算符相连，运行时算不对）——建后整单 `query_form` 把该控件 `options.mode` 改 `'SUM'` 再 `save_design_from_file` |
| `forms[].titleIndex` | 标题字段在 `fields` 里的下标，默认 0。⚠️ 分隔符/布局控件会占位：表首是 `divider` 时 `titleIndex: 0` 会把标题静默设成分隔符（建表成功不报错，列表标题列却是空的，2026-09-15 实测）。按**目标业务字段的真实下标**填，建完回读 `query_form(code)` 的 `config.titleField` 核对；错了用 `save_design_from_file` 整单改 |
| `link` | 一对一：`showMode=single` + `showType=card`。要「在 A 里以关联记录展示 B」→ `from=A`，`fromField=B的名称`。没有关联就删掉 `link`。**多对多双向**不要用这一条，表建完走 `fast-add-link-record.md` |

| 多张互不依赖的基础表 | 脚本内部并行调 `desform_creator.py`，不要自己再写一遍 |
| 工作表分组 | 表建完 `create_worksheet_group` + `move_worksheet_to_group`；或直接 `forms[].group=分组中文名`。**分组不存在时脚本自动创建**（2026-09-15 修复：原行为 SystemExit 整批失败），返回拿不到 id（首个分组迁移路径）会自动重试拉列表；不要打开 `desform-lowapp.md` 全文 |
| ⚠️ **分组顺序** | 自动创建的分组**按创建时序乱序**，不会跟规格里的声明顺序（2026-09-20 进销存实测：规格写「经营看板→基础数据→客户管理→销售管理→采购管理→库存管理→财务管理」，建出来是「库存管理→财务管理→采购管理→经营看板→…」）。**收尾必须重排**：`sort_worksheets([{'id': 分组id, 'orderNum': 1}, …])` —— 该函数签名写的是「工作表」，但**传分组 id 一样生效**（实测），一次调用即按 orderNum 升序。回读 `get_menus().menuList` 里 `type=='group'` 的顺序核对 |

### 建后补丁契约速查（公式 / 关联字段带出 / 流水号 / 隐藏，一张表拿全，禁止分轮 inspect）

以下签名与结构即全量（2026-09-16 30 表任务实测归总），补丁脚本一次拿全，**不要**为确认签名分多轮 `inspect.getsource`/`grep`：

- **关联字段带出（link-field）**：job 里**不写**（建表时目标字段 model 不存在），走 `fast-add-link-record.md` 关联建完后用工厂补：`from desform_utils import LINK_FIELD`；`LINK_FIELD(新字段名, link_record_key, show_field, field_type)` 返回 `(card, key, model)`，控件取 `[0]`（card 可直接 insert 进 `design['list']`）。⚠️ 两个参数都是**编码不是中文名**：`link_record_key`=主表 link-record 控件的 `key`；`show_field`=**目标表**字段的 model（`get_form_fields(目标表code)` 按中文名解析）。插到主表 design['list'] 中关联控件所在 card 之后，保持字段顺序。
- **「默认值函数计算」≠ 公式控件（2026-09-16 误建实证返工）**：规格写「XX（日期类型，默认值函数计算公式：FUNC(...)）」时是**普通字段的函数默认值**——建该类型的正常控件（如 DATE），整单补 `advancedSetting.defaultValue={"type":"function","value":"FUNC($model$...)","format":"<字段类型，date 字段写 date>"}`；字段**可编辑**、被引用字段变化自动重算。只有「实发工资」「行驶公里数」这类**计算结果只读字段**才用公式控件（下条）。判据：规格主语是「XX 类型」+默认值=函数 → 函数默认值；规格主语是「公式」→ 公式控件。
- **公式补丁**：job 建的 formula 表达式是坏的（见上表 formula 行），整单改 `options.mode='CUSTOM'` + `options.expression`=**解析后 model 拼接**的表达式（如 `f"ROUND({m金额}/{m数量},2)"`、`f"{m1}+{m2}-{m3}"`）。输出类型补 `options.type`：日期结果 `'date'`、数值 `'number'`；金额加 `decimal:2`/`unitText:'元'`。FORMULA 工厂签名 `FORMULA(name, mode='CUSTOM', expression='', decimal=2, ...)`，expression 内用 `$model$` 引用。
  ⚠️ **写规格时就要查：`$X$` 里引用的字段名必须在本表存在**（自身字段 **或** 关联带出的他表字段）。
  写错不会在补丁时报——只在**真机补丁阶段**以「公式占位符对不上本表字段」收尾失败，
  白等一整轮（52 表约 4~5 分钟，2026-09-16 实测）。动真机前用
  `scripts/precheck.py --spec app_spec.json` 静态查掉。
- **换控件类型（delete_widget + add_widget）会换掉字段的 `model`**：
  若要换的正好是**标题字段**，会同时打断两条链——① 表单自己的 `titleField`
  ② **所有上游关联记录的** `options.titleField` / `showFields[]`。
  表现：列表里该列显示空白、下拉选不到东西，**接口零报错**。
  → 换到标题字段时：要么改走 `update_widget` 原地改类型（保留 model），要么
  **用原 `key`/`model` 重新挂上去**复原（`add_widget` 收完整控件 dict，key/model 可覆盖）。
  2026-09-16 实测：给「收款项」「付款项」换单选控件，两张表的标题链一起悬空。
- **补档位 = 改控件 `type` 本身，不是只改 `options`；且禁止整块覆盖 `options`**（2026-09-20 实测事故）：规格（`app-spec.md`）表达得了的只有 `静态下拉/字典/单选/多选/编号`，这三类档位建后必补——①「下拉但选项来自某表某字段」→ `type='select'` + `options.remote='linkData'` + `linkDataConfig`（只挂 linkData 仍是文本框）；②「日期时间」→ 仍是 `date` 控件，补 `designType/type='datetime'` + `format='yyyy-MM-dd HH:mm:ss'`；③「他表字段存值」→ 工厂 `LINK_FIELD` 的 `save_type` 被白名单丢弃、恒 `view`，必须整单改 `options.saveType='save'`（见 `desform-link-record.md` §七）。
  **写法铁律**：逐键 `update`（如 `o['type']='datetime'`），**禁止 `w['options'] = 新控件['options']` 整块覆盖**——实测整块覆盖把 22 个日期字段的 `format/timestamp` 全清空，只剩 `{hidden,autoWidth}`，存档与回读全绿，只有人打开表单才看得出。
- **读字段清单的响应层级**：`/desform/api/fields/<code>?group=true` 的字段在
  **`result.fields`** 这层（`{desformCode, titleField, desformName, id, fields:{中文名:{model,key,type}}}`）。
  在 `result` 顶层找字段名 → 一场空，会误报一片「字段不存在」的假缺口。
- **流水号自定义规则**：`AUTONUMBER(name, prefix='', date_format='yyyyMMdd')` 带 prefix 时**恒插 create_date 段**；「GH-+4位流水」这类**无日期**规则、或日期段不在前缀后（如 `YZSQ-yyyyMMdd-####`）时，建后整单覆盖 `options.numberRules` 段数组：text 段 `{"type":"text","text":"GH-","value":"GH-"}`；日期段 `{"type":"create_date","format":"yyyyMMdd","dateFormat":"yyyyMMdd","formatCustom":"yyyyMMdd"}`；流水段 `{"type":"number","mode":2,"start":1,"reset":0,"length":4,"continue":false}`。段顺序=编号拼接顺序。
  - ⚠️ **补不补零只由 `mode` 决定，`length` 单独写没用（2026-09-20 实测事故）**：`mode:1` = 自然数（`1,2,3…`，**`length` 被完全忽略**）、`mode:2` = 指定位数（`0001,0002…`）。规格或 `app-spec.md` 的 `编号:[前缀,位数,是否含日期]` 里**只要给了位数**（「4 位流水号」「补零」「0001 起」）→ **必须 `mode:2`**；只有需求明说「不要补零、1,2,3 递增」才写 `mode:1`。⚠️ auto-number 控件的**工厂默认流水段就是 `mode:1` + `length:4`，照抄默认值即错**——落库后编号形如 `JH-26-2` 而不是 `JH-26-0002`，且 save/回读全绿、只有人翻开数据才看得出（前缀 / 日期 / 起始值 / 不重置全对，只有位数没生效）。
  - ⚠️ **日期段要「自定义格式」时 `format` 必须写 `custom`**：面板的格式下拉绑定 `rule.format`，合法值只有 `yyyyMMdd`/`yyyyMM`/`MMdd`/`yyyy`/`custom`。写 `format:"YY-"` 时后端仍按 `dateFormat` 渲染出 `26-`（**输出是对的**），但设计器面板该下拉**显示空白**，看着像没配。要 `YY-` 这类自定义格式 → `{"type":"create_date","format":"custom","formatCustom":"YY-","dateFormat":"YY-"}` 三键同写。
- **`radio` → `select`（存量表补丁；新建直接用 `静态下拉`，2026-09-20 实测）**：规格现已有 `静态下拉` 档（→ select），**新建表写它即可**，本节是给「已用 `静态单选` 建错、要改回来」的表用的。曾经的缺口：`静态单选` 固定落 `radio`、`静态多选` 固定落 `checkbox`，`字典` 那档又要求选项来自应用字典，于是「不绑字典的静态下拉」无档可写、建出来是一排横排单选钮，`precheck` 不报错（它只认字段名、不看控件偏好）。补救三步：
  ① **键集照抄本应用一个真实 `select` 控件的 `options`**（别凭记忆手写），再抽掉字典专属键 `dictCode`/`dictCodeAppId`/`isDictItem`/`remoteOptions`/`remoteFunc`、`remote` 置 `false`；
  ② **⚠️ 每个选项项必须补 `label`**——`radio` 的项是 `{value,itemColor}`、**没有 `label`**，`select` 的是 `{label,value,itemColor}`。只改 `type` 不补 `label`，下拉**空白**，而 save 返回 success、回读 `options` 也非空，只有人打开新增页才看得出。补法 `{'itemColor':o.get('itemColor'),'label':o.get('label') or o.get('value'),'value':o.get('value')}`；
  ③ 回填 `defaultValue`/`required`/`hidden`/`hiddenOnAdd`/`readonly`/`disabled`/`fieldNote`/`placeholder`，再设 `multiple`（需求同时写「可多选」才 `true`）/`filterable:false`/`clearable:true`/`showLabel:true`。
  **改完必须同步简流**：被流程分支条件 / `data_update.updateFields` / `data_add.formModel` 引用的，里面存的 `type`/`valType`/`fieldType` 还是 `radio`，要一并改 `select` 并重新 save+deploy。回读断言：`type=='select'` 且**选项 `label` 缺失数 0**。
  **根因（改 `SELECT()` 工厂前必读）**：工厂用 `show_label = any("label" in o for o in options_list)` 决定 `showLabel`，而 `_make_options_list` 对**纯字符串列表**只产出 `{value, itemColor}`（无 `label`）→ 静态 select 落库 `showLabel:false` 且选项无 `label`，前端下拉空白。已在 `SELECT()` 里对静态选项（`not dict_code`）统一 `setdefault("label", value)` 修掉；`RADIO`/`CHECKBOX` 不走这条、行为不变。
- **引用「控件本身」用 `key`，引用「字段」用 `model` —— 混了不报错，只在设计器里显示「字段已删除」**（2026-09-16 一次性踩了三处，都是 save 全绿、只有人打开面板才看得出）：
  ⚠️ **key / model 的归属以本表为准；更细的分类与前端源码依据见 `desform-widget-options.md` 汇总节**（`WidgetConfigMixins.js` 核实过：控件下拉 `value=控件key`、`model=控件model`）。任何**操作步骤类**文档（如 `desform-link-record.md`「二-a」转换、`fast-full-chain.md`「③-b」）与这两处冲突时，**以这两处为准**，并顺手把那边改掉。
  2026-09-21 实测教训：照「二-a」把汇总 `linkTable` 同步成了新 model，面板「关联表」下拉解析不到、直接显示原始串 `sub_table_design_…`，而 save/回读/precheck/契约检查全绿、运行时求和也正常——**只有打开设计器面板才看得见**。

  | 配置项 | 填什么 |
  |--------|--------|
  | 汇总 `options.linkTable`（源=**关联记录**） | 该 link-record 的 **`key`**（`1693451000559_843595`），**不是** `link_record_xxx` model |
  | 汇总 `options.linkTable`（源=**工作表子表**，即 `link-record` + `isSubTable`） | **仍是 `key`** —— 控件类型还是 `link-record`，转换只改 `model` 不改 `key`，**转换时别去动这个键**（2026-09-21 实测） |
  | 汇总 `options.linkTable`（源=**设计子表** `sub-table-design`） | 子表 **model** `sub_table_design_xxx` |
  | 他表字段 `options.linkRecordKey` | 主表 link-record 的 **`key`** |
  | 他表字段 `options.showField` / 汇总 `options.field` / 汇总筛选 `filter.rules[].model` / 公式 `expression` 里的 `$x$` / 业务规则 `rules[].model`+`actions[].value` | **字段 model** |
  | 默认值点分引用 `$<X>.<字段model>$` | `X` = 关联记录控件的 **`key`** |
  ⚠️ 工厂建的 link-record 其 **`key` 与 `model` 的随机后缀可能不同**（key `1789539935877_875104` / model `link_record_1789539935877_511731`），**必须从控件 `key` 取值，不能靠截 model 字符串**。收尾自检跑一遍「引用解析」：所有引用项都要能在本表 key 集或全局 model 集里命中。
- **只读 vs 禁用 —— 语义不同，且别套用成互斥组合**：`options.readonly=True`（单行文本/多行文本/日期）只是输入框不可编辑；`options.disabled=True`（选人/选部门/关联记录/数字）是**整个控件不可操作——用户连选都选不了**。
  ⚠️ **「必填 + 只读/禁用」是互斥组合，见到就先问，不要自行推导**（2026-09-16 用户实测质问「为什么禁用了，我没和你说要禁用吧」）：需求里字段标「必填，只读」、另一处又有类似「选人/选部门/关联记录 用禁用」的统一规则时，把规则机械映射过去 → 必填字段被禁用 → **表单直接不可用**（用户既不能选、又必须填）。判据不是「我设的属性落库了吗」，而是「按这个配置，用户能不能走完这条流程」。
  正确切分：**系统带出、用户不该改** 的字段才禁用（如「取关联记录的所属部门」这类回填）；**用户必须选、只是填完不再改** 的字段不能用禁用，该放开可编辑或用其它约束方式。规则级条款与字段级标注冲突时**字段级优先**并把冲突报给用户。
  拿不准时以「按这个配置用户能不能走完流程」为准，而不是以属性有没有落库为准。
- **隐藏**：**按规格里的字面措辞一一对应，不要按「字段 / 分隔符」分类套用**（2026-09-16 误判返工）——
  - 写「**隐藏**」→ `options.hidden=True`（整单隐藏）。分隔符和字段都可能标「隐藏」。
  - 写「**新增时隐藏**」→ `options.hiddenOnAdd=True`（新增表单隐藏、编辑/审批环节可见）。
  - ⚠️ 「**默认隐藏（审批环节内填写）**」也归**前者**（`hidden=True`）——括号里的「审批环节内填写」**不等于** hiddenOnAdd：这类字段在审批节点由**简流的节点字段权限**（`extActProcessNodePermission` 的 ruleType=1 status="1" 显示）放出来，不要靠 hiddenOnAdd 兜——✅ **2026-09-16 实测确认**：字段设 `hidden=True` 后，在配了「显示+可编辑」权限的审批节点里**照常可见可填**（节点权限盖过表单级 hidden）。
  - 两类混在同一张字段清单里时逐条看措辞，禁止一律按一种处理。

### 六条「接口全绿但业务跑不通」的坑（2026-09-20 进销存实测）

- **他表字段（link-field）必须 `saveType='save'`**：工厂建出来默认 `'view'`（仅显示）→ **值不落库**，
  流程拿它当定位键（仓库编码/产品编码/单据号）时恒取空值。改法走**整单设计保存**（`query_form` →
  改控件 `options.saveType='save'` → `save_design_from_file`）；`update_widget` 改不动
  （`desform-link-record.md` §七「关键注意」第 2 条）。需求写「仅显示」才留 `view`。回读 `options.saveType == 'save'`。

  > ⚠️ **2026-09-20 进销存实测：这条不是「个别字段」问题，是「全表」问题。**
  > 47 张表建完，**所有**带出字段（仓库名称/编码、产品名称/编码、单号、客户名称…）全是 `view`，
  > 用户打开设计器一眼看到「这些应该自动带出，不要让用户手填」。
  > **批量化修法**（比逐字段点 UI 快，也比逐个 `update_widget` 可靠）：
  > 遍历「应用菜单 → 每张表 `query_form` → 递归取全部控件（**必须走 `panes[].list` 与子表 `columns[].list`**）
  > → 凡 `type=='link-field'` 的控件，`options.saveType='save'` → `save_design_from_file` + `save_auth_from_design`
  > → 回读断言每表 `link-field` 数 == `saveType=='save'` 数」。
  >
  > **改完必须同步流程**：控件类型变了，流程里存的 `type`/`valType`/`fieldType` 是旧值
  > （见 miniflow `node-contract.md` §9.3）——**这是「字段侧 + 流程侧」两处，只改一处 = 静默故障**。

  > ⚠️ **把手工输入框换成他表字段**（「仓库名称/编码」这类要求自动带出的字段，建表时是普通 `input`）：
  > 用 `LINK_FIELD(字段名, 主表 link-record 控件的 key, 目标表被带出字段的 model, 原控件类型)`
  > 造出正确形状的控件，**再把它的 `key`/`model` 覆盖成原控件的 `key`/`model`**，就地替换回设计树。
  > **绝不能换 key/model** —— 换了两侧 `twoWayModel`、上游关联引用、已建流程的字段引用一起断。
- **关联记录 + 它带出的他表字段放同一块**（同一 card / 同一 divider 区段），顺序「关联控件 → 带出字段」。
- **双向关联成对写 `twoWayModel`**：两边互指对方 link-record 的 model；只写一侧 = 明细挂不上单据。
- **选项控件开彩色**：`radio`/`checkbox`/`select` 设 `options.useColor=true`，`itemColor` 取系统 20 色之一。
- **只有 2 个选项的用 `radio`/`checkbox`，不用 `select`**（`单据确认` 是/否这类）；3 个以上才用下拉。
- **`divider` 标题居左**：`options.position='left'`（取值 left/center/right；设计器源码里没有 `titleAlign`，
  写它不生效——考勤-速测18 实测，此前本条写错）。
- **关联记录「表格」模式 `showFields` ≥ 4 个业务列**。

### fields.type 合法码速查（2026-09-15 实测）

`fields[].type` 只认设计器控件码；creator 遇未知类型抛 `未知的控件类型`，并行批建时**一张错、整批失败重跑**（create_linked_worksheets.py 已内置 fail-fast 预检，报「含未知控件类型」即此类错，会直接列出错字段并给出常见纠错）：

| 需求 | 正确写法 | 常见错码 |
|------|---------|---------|
| 日期时间 | `date` + `"dateType":"datetime"`（`datetime_s`/`datetime_sf` 同理） | ~~datetime~~ |
| 附件上传 | `file-upload` | ~~fileupload~~ |
| 流水号/自动编号 | `auto-number`（规则段建后整单补 `options.numberRules`） | ~~autonumber~~ |
| 省市区联动 | `area-linkage` | ~~cascader~~（敲敲云禁用） |
| 定位 | `location` | ~~map~~ |
| 图片上传 | `imgupload`（多选自带） | |
| 选择用户/部门多选 | `select-user`/`select-depart` + `"multiple":true`（实测生效） | |
| 下拉/单选 | `select`/`radio` + `options:["A","B"]`（**纯文本数组**；绑字典的字段禁止写 options，只给 name+type） | |
| 条码/二维码 | `barcode` + `"codeType":"barcode"\|"qrcode"` + `"sourceModel":"$字段名$"` | 曾整批被拦，见下 |
| 汇总 / 汇总日期 | `summary` / `summary-date`（`linkTable` 写子表或关联控件**中文名**，creator 自动解析） | |
| 子表 | `sub-table-design` | ⚠ 见下 |

其余可用：`input` `textarea` `number` `integer` `money` `phone` `email` `date` `time` `switch` `rate` `slider` `editor` `divider` `text` `capital-money` `text-compose` `select-depart-post` `org-role` `formula` `link-record` `link-field` `color` `hand-sign` `markdown` `ocr` `map`。纯时间（HH:mm:ss）用 `time`（dateType 无 time 档）。

> ⚠️ **2026-09-24 修正：预检白名单曾是 `desform_creator._TYPE_MAP` 的真子集**，`barcode`/`summary`/`summary-date`/`color`/`hand-sign`/`markdown`/`ocr`/`map` 这些 creator 侧**本来就能建**的码被 fail-fast 整批拦下（53 表任务里一个 `barcode` 就让 0 张表建成）。已补齐白名单。
> **`barcode` 的 `sourceModel` 写 `$字段名$`**（由 `_post_process_widgets` 解析成 model）；⚠️ 落库必须是**裸 model**——曾因复用了公式的解析器而落成 `$input_…$`，条码取不到数据源、渲染为空，而 save/回读全绿（同日已修）。也兼容直接写裸中文名。
> **仍未收录：`tabs` / `grid` / `card` / `buttons`** —— 它们是容器、需要嵌套子控件，而 `fields[]` 是扁平结构没有嵌套通道，放开只会建出空容器。要容器请走 `--preprocess` 或建后再补。

⚠ **子表 `columns` 键被静默忽略**：job 里给 `sub-table-design` 写 `columns:[...]` 不报错，但建出来是**空壳子表**（2026-09-15 实测）。建表后必须按 SKILL「往已有子表加列」用 `SUB_*` 工厂补列（工厂返回值取 `[0]`，补完 `save_design_from_file` + `save_auth_from_design` 并回读验证列存在）。

> ⛔ **子表列必须包单元格（2026-09-16 实测，save 全绿但整表瘫痪）**：`columns` 数组的元素是**单元格** `{"span":12,"list":[...]}`（空壳自带 1~2 个空单元格），`SUB_*` 工厂返回的是**裸控件**。必须把控件 append 进某个单元格的 `list`（列不够就整列重建为 `[{"span":12,"list":[w]} for w in 控件列表]`）。**禁止把裸控件直接 append 到 `sub['columns']`**：保存接口照常 success，但后端会把列清成空单元格，随后 `queryById` 直接 500 `columnList is null`，**整张表查询/保存全瘫**（表现为 list 列表能查到、queryById/query_form/get_form_fields 全挂）。保存后必须回查 `queryById success` + 列存在，不能只信 save 返回值。

### 大批量（>10 表）提速流程（2026-09-15 30 表实测，串行约 21min；2026-09-16 复测：脚本内 30 表全并行墙钟约 6~8min）

- **fail-fast 已内置**：错类型码在创建前整批拒绝，不再浪费一轮。
- **建表墙钟预期**：30 表 job 已 `max_workers=len(forms)` 全并行，剩余 6~8min 是**服务端**串行处理（建表+设计+权限逐表落库），本地拆批/重试/加线程都不会更快——跑到一半「 seemingly 卡住」是正常服务端耗时，禁止中断重跑（重跑虽幂等但白等）。job 编写（写字段 JSON）时间在大模型侧，与接口无关。
- **关联记录批量并行**：N 个关联字段用 `scripts/batch_add_link_record.py` 一条命令并行跑（job 为 `{tenantName, appName, links:[...]}`，每条格式同 `fast-add-link-record.md`）。逐条串行跑 CLI 时每个子进程重复 get_tenants/get_apps 定位（10s+），N 条 ≈ N×20s；并行后墙钟接近单条。
- **整单补丁线程池化**：补丁各表互相独立，`ThreadPoolExecutor(max_workers=5)` 并发「query→改→save→auth→回读验证」；`get_form_fields(源表)` 进程内缓存（同一张源表常被多张主表引用）；**无变更的表直接跳过不保存**；脚本按幂等设计（每表检查标记，已补的不重复补），失败重跑不从头来。
- **分组**：建组串行（首个分组有全量迁移副作用），之后的 `move_worksheet_to_group` 可并行。

> ⛔ **【强制·2026-09-15 补丁环节踩坑后升级】审计必须并入补丁首轮，禁止单独跑审计轮回查。** 适用范围 = **建表 job 之后的一切整单补丁**（含手写补丁脚本、通用补丁脚本），不只建表流程本身。做法：补丁脚本每表的首趟 `query_form` 同时产出两类检查——① 建表 job 里声明的字段/`subColumns` 是否都在（防静默丢字段）② 本表所有补丁项的目标态核对（hidden/numberRules/expression 非空/advancedSetting 非空/子表列存在），逐表打印 ✓/✗ 清单；`[OK]` 只代表保存接口返回成功，不代表内容落上（坏公式、叠控件都报 `[OK]`）。**禁止**写完整补丁→发现可疑→再写一个独立 audit 脚本（实际发生过：独立审计抓出 3 张表公式缺失 + 子表漏列，代价是一整轮返工）。禁令语气原因：上轮执行时本规则被误归类为"建表脚本内部行为"，手写补丁脚本时脱约束——规则不依赖"记得"，靠首轮必做。

已存在的表：creator 打印 `[阻止]`，脚本继续加关联，不覆盖。

> ⚠️ **2026-09-14 实测（人事OA 30 表）：job 建表全绿但可能静默丢个别字段**（入职审批丢「试用期(月）」整数、转正申请丢「部门负责人」选人，无报错）。**建表后必须立刻回查**：逐表 `query_form` 用 `get_form_fields` 比对 job 里 `fields[].name`，缺的字段当场用工厂函数（`INTEGER`/`USER`/`INPUT`…）+ `add_widget` 补，不要等后续补丁/简流按名取 model 才 KeyError（彼时要多花一轮定位+回补）。字段多的 job（>10 表）必查。

> ⛔ **`link` 产出的是普通 many 关联（明细区为外链表格）—— 需求写「子表」时这不是终点。**
> 「子表作为单独工作表 / 已有工作表作为子表」= 明细控件顶层 `isSubTable:true` + `model` 改 `sub_table_design_<控件key>`
> + **两侧 `twoWayModel` 互指**，**建完必须再跑一遍转换**（4 步 + 自查见 `references/desform-link-record.md`「二-a」，
> 样例：工作表 主.子）。`add_link_record.py` 同此。
>
> ⚠️ **判据是需求原文有没有「子表」二字，不是控件长得像不像。** `显示:"表格"` 落库是 `showType:"table"`，
> 明细区本身就是一张表格 —— **看着就是子表，设计器面板里仍叫「关联记录」**（顶层无 `isSubTable`、
> `model` 还是 `link_record_*`）。2026-09-20 实测：16 表应用 53 个关联控件 `isSubTable` **0 个**，
> 需求里明确写过「子表」，`save`/回读/`precheck` 全绿，只有用户打开设计器才发现。

## 禁止（再犯就是 6 分钟）

- Read `jeecg-desform` / `jeecg-onlform` / `jeecg-system` 的 SKILL.md
- Read 本技能 SKILL.md 全文、「创建表单」§1–4、widget-options、json-config
- 同一句还要简流/盘时并行 Read miniflow/dashboard SKILL.md（应改走 `fast-full-chain.md`）
- 先 `action=list` 再创建；为没有数字 ID 再问一轮
- 手写 `LINK_RECORD` + 两段 `desform_creator` 临时脚本（本脚本就是干这个的）
