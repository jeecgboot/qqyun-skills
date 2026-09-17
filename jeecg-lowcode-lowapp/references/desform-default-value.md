# 默认值表达式（Default Value Expressions）

表单控件支持通过 `advancedSetting.defaultValue` 配置高级默认值，包括静态值、字段引用组合、函数计算、自定义 JS 函数、查询工作表等多种方式。

## advancedSetting.defaultValue 结构

```json
{
  "advancedSetting": {
    "defaultValue": {
      "type": "compose",
      "value": "",
      "format": "string",
      "allowFunc": true,
      "valueSplit": "",
      "customConfig": false
    }
  }
}
```

### 属性说明

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `type` | string | `"compose"` | 默认值类型，见下方类型说明 |
| `value` | string | `""` | 默认值表达式内容 |
| `format` | string | `"string"` | 值格式化方式：`string`/`number`/`boolean` |
| `allowFunc` | boolean | `true` | 是否允许使用函数计算 |
| `valueSplit` | string | `""` | 数据分割符（如 `,`），非空时将多值 join 为分割字符串 |
| `customConfig` | boolean | `false` | 为 `true` 时使用自定义配置面板（如 link-record、sub-table-design） |

### type 类型说明

设计器默认值面板下拉三项与 type 的对应关系：

| 用户面板文案 | type | 说明 | 示例 |
|------|------|------|------|
| 其他字段值 | `compose` | 静态文本 + 字段引用组合（`$model$` 存在与否自动切换静态/动态执行，无引用即纯静态值） | `"订单-$input_model$"` |
| 函数计算 | `function` | 内置函数库表达式（弹窗左下角有「自定义函数」开关，打开后 type 变 `javascript`） | `"SUM($field1$,$field2$)"` |
| （同上开关） | `javascript` | 自定义 JavaScript 代码体（`return` 返回） | `var a=$f1$; return a*2;` |
| 查询工作表 | `linkage` | 按条件从其他工作表查数据回填（配置见 `desform-linkage-query.md`） | 查询配置 JSON |

> **选型口径（2026-09-16 用户口径）：优先 `function` 内置函数表达式（如 `IF(...)`/`DATENOW(...)`），内置表达不了再用 `javascript`。**

## 支持「默认值-函数计算」的组件清单

> **并非所有组件都有高级默认值（面板下拉：其他字段值/函数计算/查询工作表）属性**，以下清单依据组件 schema 核对（2026-09-07）。**不在支持清单里的组件，即使用户要求，也不要为它写 `advancedSetting.defaultValue`（type=function/javascript/linkage）**——设计器没有该入口，写进去配置面板不显示、再编辑会丢。

### ① 支持通用高级默认值（含函数计算入口）的组件

| 组件 | 说明 |
|------|------|
| `input` 单行文本 / `textarea` 多行文本 | format 默认 string |
| `number` 数字 / `integer` 整数 / `money` 金额 | format 默认 number |
| `date` 日期 | 另有 options.defaultValueType 快捷开关（见下节），两者不冲突 |
| `switch` 开关 | 值按字面存储值写 |
| `slider` 滑块 | format 默认 number |
| `phone` 手机 / `email` 邮箱 | format 默认 string |

以上组件四种 type（compose/function/javascript/linkage）都可用。

### ② 有默认值能力、但**没有函数计算入口**的组件

| 组件 | 默认值形态（注意不要写成 function/javascript） |
|------|------|
| `radio` 单选框组 / `checkbox` 多选框组 / `select` 下拉选择框 | 默认值区只在**数据源=静态数据或数据字典**时显示：从选项/字典项挑默认（多选可连选多个）；「其他字段值」入口**仅数据字典模式下**提供（可引用同 dictCode 控件）；**无「函数计算」「查询工作表」入口**（面板代码中查询工作表项为注释态，2026-09-08 源码核对） |
| `select-user` 用户 / `select-depart` 部门 / `select-depart-post` 岗位 | 默认值编辑器=JBizDefValConfig：选固定用户/部门/岗位 + 「当前登录人」（写入 advancedSetting 值 `#D:CURRENT#`，运行期同时认 `options.defaultLogin:true`，新增/预览填充：用户=sysUserCode、部门/岗位=sysOrgCode）+ 「其他字段值」+ 「查询工作表」；无函数计算面板 |
| `org-role` 组织角色 | 仅**选择固定角色**（JSelectRoles 绑定 `options.defaultValue`），无当前登录人/字段/查询入口 |
| `link-record` 关联记录 | 专用面板：默认第一条数据 / 查询工作表（见 `desform-linkage-query.md`），不走通用函数弹窗 |
| `sub-table-design` 设计子表 | 专用面板：固定值 / 查询工作表 |
| `time`（inputDefVal）、`auto-number`（generateOnAdd）、`text-compose`、`rate`、`color`、`editor` 等 | 默认值配在各自 options 里，无高级默认值/函数计算 |

### ③ 无默认值属性 / 仅静态默认值的组件

- **完全无默认值**：`imgupload`/`file-upload` 上传、`hand-sign` 手写签名、`ocr` 文本识别、`barcode` 条码、`map` 地图、`markdown`、`summary` 汇总、`formula` 公式（自身是计算控件、结果只读）、`select-tree` 下拉树、`link-field` 他表字段、布局容器（栅格/Tabs/卡片/分隔符/标题）——没有默认值概念，一律不要写默认值配置。⚠️ `markdown`/`map` 的 options 里残留有 defaultValue 键（map 被注释），面板无入口，勿按 schema 误配
- **仅面板自带默认控件**（绑定 `options.defaultValue`，无字段引用/函数/查询能力）：`rate` 评分（星级选择）、`color` 颜色（取色器）、`editor` 富文本（文本框）、`time` 时间（HH:mm:ss，另 range 模式在时间专用默认值区）、`area-linkage` 省市级联动（省市区选择器，按 areaLevel）、`table-dict` 表字典（「选择值/输入值」二选一）、`location` 定位（**默认值=「当前位置」开关 `options.defaultCurrent`**，非文本）——不要给这些写 `$model$` 引用或函数

> 用户要求在不支持组件上做函数计算/联动默认值时：说明该组件无此能力，并给出替代（数值计算改用 `formula` 公式控件承载；需要回填用 `link-record` 关联记录或 pick 一个①中的组件）。

## compose 类型 — 静态值 + 字段引用

最常用的默认值类型，支持纯静态文本和 `$fieldModel$` 字段引用的混合组合。

### 纯静态值

```json
{
  "type": "compose",
  "value": "默认文本",
  "format": "string"
}
```

### 字段引用

使用 `$fieldModel$` 语法引用其他字段的值（注意是 model 名，不是字段显示名）：

```json
{
  "type": "compose",
  "value": "部门：$select_depart_model$ - 姓名：$input_name_model$",
  "format": "string"
}
```

**引用规则：**
- 字段引用格式：`$model名$`（前后各一个 `$` 符号），中间不能有空格
- 支持引用主表字段和关联记录字段
- 关联记录字段用点分格式：`$<关联记录控件的 key>.字段model$`。⚠️ **前缀是控件的 `key`（形如 `1693392595066_406429`），不是 `model`** —— 写成 `$link_record_1693392595066_406429.xxx$`（带 `link_record_` 前缀）设计器解析不到，属性面板会显示成「**字段已删除**」（2026-09-16 实测：设计器手工配置的落库值 = `$1693392595066_406429.select_user_1692874017319_686764$`，同控件 `model=link_record_1693392595066_406429`）。注意工厂建的 link-record 其 `key` 与 `model` 的随机后缀可能不同，必须从控件 `key` 取值、不能靠字符串截 `model`。
- 支持系统上下文变量：`$_CONTEXT_VAR_sysUserCode$`（当前登录人账号）、`$_CONTEXT_VAR_sysUserName$`（当前登录人名称）、`$_CONTEXT_VAR_sysOrgCode$`（当前登录人的部门编号）、`$_CONTEXT_VAR_sysDate$`（当前系统日期）、`$_CONTEXT_VAR_sysTime$`（当前系统时间）
- 被引用字段值变化时，默认值自动重新计算（watch 防抖 50ms）
- compose 类型下引用的字段为空时替换为空字符串
- 引用 **date 控件**字段时，其值先按该控件自身的显示类型归一化再代入：`year→YYYY`、`month→YYYY-MM`、`quarter→YYYY-[Q]Q`、`week→GGGG-WW周`、`datetime→YYYY-MM-DD HH:mm:ss`、普通 date→`YYYY-MM-DD`
- **设计子表列（sub-table-design）默认值引用主表字段 = `$main_<model>$` 前缀**（如 `$main_number_xxx$`），引用本行列直接 `$<model>$`（2026-09-07 UI 实测：面板选主表字段生成 `main_` 前缀，裸 model 取不到主表值）。特例：DATEADD 等日期函数的主表日期参数保持裸 `$<model>$` 也正确

## function 类型 — 函数计算

使用内置函数库计算默认值，函数内可引用字段值。

```json
{
  "type": "function",
  "value": "SUM($price_model$,$tax_model$)",
  "format": "number"
}
```

> **注意：** function 类型与 formula 控件不同。formula 是独立的公式控件，function 类型是任意控件的默认值计算。

> ⚠️ **字段引用漏写 `$…$` = 静默失效（2026-09-16 实测返工）**：`value` 里引用字段必须写 `$<model>$`，**裸 model 被当字面量字符串**——设计器「编辑函数」原样显示 model key（如 `xxx_<时间戳>_<序号>`）、新增页不代入值、算不出结果，但接口 save success、回读 value 也非空，只有人打开设计器才看出来。**批量脚本用正则把中文字段名替换成 model 时最易漏**：替换结果要拼成 `$<model>$`；不要和自带标记的形态混淆（`#D:CURRENT#`、`#F:<值>#`、`$_CONTEXT_VAR_sysDate$`、`$<关联记录key>.<model>$` 本身已含定界符）。回查：正则 `(?<![$\w])[a-z][a-z0-9_]*_\d{10,}_\d+(?![\w$])`，扫**两个键**——① 每个控件的 `advancedSetting.defaultValue.value`；② `type=='formula'` 控件的 `options.expression`（公式表达式同款坑，2026-09-16 实测一次批量建表里 4 个公式全中）。命中即漏写。遍历须递归到 `card.list`/`tabs.panes[].list`/`sub-table-design.columns[].list`。**切勿**拿该正则扫整份 designJson：`model`/`titleField`/`showField` 本应为裸 model，会淹出数百条误报。

**可用函数详见 `desform-formula-function.md`。**

## javascript 类型 — 自定义 JS 函数

通过自定义 JavaScript 代码计算默认值。函数体必须返回一个值。

```json
{
  "type": "javascript",
  "value": "var price = $price_model$; var qty = $qty_model$; return price * qty * 1.13;",
  "format": "number"
}
```

**执行特点：**
- 代码中的 `$model$` 会被替换为字段实际值
- 字符串类型的值会被包装为引号字符串
- 函数异步执行，不阻塞 UI
- 必须通过 `return` 返回计算结果

## 表达式求值细节（源码核对 2026-09-07）

**执行引擎：**
- `function` 类型 = **JavaScript 表达式**：按 JS 语义**异步**求值，内置函数调用自动异步化（参数可含异步结果），支持嵌套调用、比较运算（`>=`/`<` 等）、字符串拼接。`javascript` 类型 = 整段 JS 代码执行（须 `return`）。
- 表达式内无任何 `$model$` 引用时只静态执行一次；有引用则监听引用字段，变化 50ms 防抖后重算（与 formula 控件同机制）。
- **保留原值语义：** 编辑（edit）模式下，关联记录字段首次取值、字典文本首次获取（页面加载 1.5s 内）失败，或值源尚未就绪时，不覆盖当前值；用户手动点击/输入后才允许清空。
- **字段值代入规则：** 字符串自动加双引号 `"..."`；数字/布尔原样；`null`→`null`；数组/对象等 `JSON.stringify`；compose 类型下空值替换为空串。
- **字典兜底：** 引用字段控件类型与目标控件不一致（如目标 input 引用 select 字段）且存在 `model_dictText` 时，自动用字典显示文本代入表达式。
- **多值拼接：** 配置了 `valueSplit` 时每个被引用字段替换后都追加该分隔符；结果中 `#F:xxx#` 固定值片段被拆出后与动态值一起**去重拼接**。

**结果写入前按目标控件转换（parseValue）：**
- `format: "number"` → `Number(value)`，NaN 则返回 `''`
- `format: "boolean"` → `Boolean(value)`
- 目标控件是 **date**：数值字符串先 `Number()`（视为时间戳）；`options.timestamp: true` 时存毫秒时间戳；否则按控件 `options.format`（yyyy→YYYY 等转换）格式化输出
- 其余按字符串处理后走 `valueSplit`/`#F:` 规则；目标为 `sub-table-design` 时原样返回

### 函数计算弹窗可引用的字段范围（2026-09-07 源码核对）

函数计算弹窗左侧「字段」页签的候选，是配置面板按**目标控件类型**过滤后的列表，不是表单里所有字段：

**候选分组（来源 = 本表单设计列表）：**
- 本表字段（自动排除目标自身、逻辑删除字段；子表中另分组展示同子表字段/主表字段）
- 关联记录：仅**单条（single）**显示模式的 link-record 可展开其源表字段（附加系统字段 `create_by`/`create_time`/`update_by`/`update_time`），插入为 `$<关联记录控件key>.字段model$` 点分格式（前缀=控件 **key**，见上方 ⚠️）
- 系统上下文变量：`$_CONTEXT_VAR_sysUserCode$` 等 5 个（目标为关联记录时不展示）

**目标类型 → 可引用的字段类型白名单：**
- 目标为**数字类**（`number`/`integer`/`money`/`slider` 等数值存储）：只允许引用 `input`、`textarea`、`number`、`integer`、`money`、`phone`、`email`、`capital-money`、`date`、`time`、`slider`、`rate`、`summary`、`formula`（须数字型公式）、`link-field`（须 saveType=save 存值型）、`auto-number`；选择控件/用户类不可引用
- 目标为**字典类**（绑定字典或字典项的 `radio`/`checkbox`/`select`）：只能引用**同 dictCode** 的同类控件；目标单选（radio 或 multiple=false 的 select）时候选也须单选
- 目标为**其他**（`input`/`textarea`/`switch`/`phone`/`email`/`date`/`time`/非字典 select 等）：允许 `input`、`textarea`、`number`、`integer`、`money`、`phone`、`email`、`capital-money`、`date`、`time`、`switch`、`slider`、`radio`、`checkbox`、`select`、`select-user`、`select-depart`、`select-depart-post`、`org-role`、`area-linkage`、`formula`、`link-field`（saveType=save）、`link-record`（仅单条）、`auto-number`

> 同理：给字段配函数计算默认值时，**引用的字段类型必须在上面白名单内**；数字目标引用下拉/开关/用户类字段、字典目标引用其他字典等写法，设计器字段页签里根本选不出来，不要凭空构造 `$model$` 引用。

## 特殊控件的内置默认值行为

部分控件有内置的特殊默认值逻辑（不通过 advancedSetting 配置）：

### select-user / select-depart / select-depart-post — 当前登录与固定选择（2026-09-08 源码/UI 核对）

**设计器标准落库形态（与 UI 保存产物一致，API 新建照此写）：**

```json
{
  "type": "select-user",
  "options": {"customReturnField": "username", "defaultLogin": false, "defaultValue": ""},
  "advancedSetting": {
    "defaultValue": {"type": "compose", "value": "#D:CURRENT#",
                     "format": "string", "allowFunc": true, "valueSplit": "", "customConfig": false}
  }
}
```

> ⚠️ **壳键值以 UI 产物为准（2026-09-16 用户在设计器实测配置后回读对照）**：**带值**默认值（compose / function / javascript 同型）UI 恒落 `valueSplit: ""` + `customConfig: false`——写成 `valueSplit: ","` 是早期误判形态（运行时函数计算表现为新增页不算、保存后才出值）；**空值壳**（value 为 ""）UI 落 `valueSplit: ""` + `customConfig: true`。设计器打开 API 写的壳不会报错也不会归一化，必须主动按上述形态写。
> **例外：`link-record`（有专用默认值面板的控件）带值也写 `customConfig: true`**——写 false 时面板会同时渲染专用默认值区和通用编辑器，**显示成两个默认值**（2026-09-16 实测：界面手建同款控件落库即 true）。

默认值编辑器（JBizDefValConfig）四种面板项**全部落在 `advancedSetting.defaultValue`**：

| 面板项 | 落库写法 |
|--------|---------|
| 当前用户 / 当前登录的部门 / 当前登录人的岗位 | `value="#D:CURRENT#"`（单选多选同款；add/preview 生效，edit 不填充） |
| 固定用户 / 部门 / 岗位 | `value="#F:<值>#"` 段，**多个直接串联无分隔符**：`#F:a##F:b#`（`valueSplit:","` 供运行时拆分去重回显） |
| 其他字段值（引用本表单字段） | compose `value="$<本表字段model>$"`，可混拼静态文本 |
| 查询工作表 | `type="linkage"`，`value`=完整键配置对象（规则见 `desform-linkage-query.md`） |

**`#F:` 内值 = 控件 value 语义**：select-user 固定用户 = **username**（默认 customReturnField=username）、select-depart/岗位固定 = **部门/岗位 id**（默认 customReturnField=id）；org-role 见下节 roleCode。label 由组件运行时按 value 远端回显，落库不需带 label。

**取目标主数据（2026-09-08 实测接口，均带 `X-Tenant-Id` 头）**：用户 `GET /sys/user/list`（取 username）、部门 `GET /sys/sysDepart/queryTreeList`（按 departName 递归取 id）、角色 `GET /sys/role/list`（取 roleCode）。或走 jeecg-system 技能的主数据查询。

**旧写法与保存迁移（utils.js）：** 旧属性 `options.defaultLogin:true`（属性面板旧勾选框）运行时仍兼容填充，但设计器打开/保存会把 `defaultLogin:true` 或非空 `options.defaultValue` 归一化为上面 token 形态——`defaultLogin:true` → `value="#D:CURRENT#"` 且 defaultLogin 复位 `false`；`options.defaultValue` 有值 → 按逗号拆开包 `#F:v#` 串写入 value 并清空 options.defaultValue。**新建直接写 token 形态，不要只写 defaultLogin**（面板按 value 标签展示，只写 defaultLogin 面板回显空白）。Python `USER(..., default_login=True)` / `DEPART(..., default_login=True)` 为旧写法（运行时兼容）。

### org-role — 固定组织角色（默认值唯一入口）

- 绑 **`options.defaultValue`**，不走 advancedSetting：单选=roleCode **字符串**（如 `"ROmI1Fh2jR"`）、多选=roleCode **数组**（如 `["AS877NoI87","ROmI1Fh2jR"]`）——是 roleCode 不是角色 id。
- 无当前登录人 / 字段引用 / 查询工作表入口（2026-09-08 源码核对）。

### date — 默认值类型

date 控件通过 `defaultValueType` 控制默认值行为：

```json
{
  "type": "date",
  "options": {
    "defaultValueType": 1
  }
}
```

- `defaultValueType: 1` — 选择值（通过日期选择器手动选择，可预设固定默认值）
- `defaultValueType: 2` — 输入值（手动输入日期文本）
- `defaultValueType: 3` — （⚠️ **已禁用，勿写**，见下方警示）默认为当前系统时间（日期选择器禁用，新增时自动填充当前日期）

> ⚠️ **「默认当天」不要用 `defaultValueType: 3`**（2026-09-08 用户纠正）：功能可用但**设计器属性面板不回显**，再打开配置看不到设置。要默认当前日期用高级默认值（面板有回显，`defaultValueType` 保持 `1`）：
> ① 系统变量 compose：`{"type":"compose","value":"$_CONTEXT_VAR_sysDate$",...}`；
> ② 函数计算：`{"type":"function","value":"DATENOW()",...}`。
> 实测参照形态：工作表「基础数据-默认值」字段 日期选择器-1（①）、日期选择器-2（②）。
> `defaultValueType: 3` 仅 add/preview 生效，edit 不自动填充。

### time — 允许手动输入

```json
{
  "type": "time",
  "options": {
    "inputDefVal": false
  }
}
```

- `inputDefVal: true` — 允许用户手动输入时间值

### auto-number — 新增时自动生成

```json
{
  "type": "auto-number",
  "options": {
    "generateOnAdd": true
  }
}
```

- `generateOnAdd: true` — 新增记录时自动生成编号

## valueSplit 分割符

当控件支持多值（如 checkbox、多选 select）时，`valueSplit` 将多个值拼接为单个字符串：

```json
{
  "type": "compose",
  "value": "$checkbox_model$",
  "valueSplit": ","
}
```

例如 checkbox 选中了 `["A", "B", "C"]`，结果为 `"A,B,C"`。

## customConfig 自定义配置

当 `customConfig: true` 时，控件使用独立的默认值配置面板而非通用面板：

- `link-record` — 使用关联记录专用配置
- `sub-table-design` — 使用子表默认值配置（支持固定值和查询工作表两种模式）

## 默认值执行流程

1. 表单加载时，遍历所有控件的 `advancedSetting.defaultValue`
2. **纯静态值**（compose 类型且不含 `$field$` 引用）：直接返回，按 `format` 格式化
3. **动态值**（含 `$field$` 引用）：
   - 解析表达式中的字段引用
   - 建立 Vue watcher 监听被引用字段的变化
   - 字段变化时自动重新计算默认值
4. **function/javascript 类型**：通过表达式求值引擎计算
5. **linkage 类型**：向后端发起查询请求获取数据

## 注意事项

1. 默认值仅在新增（add）操作时生效，编辑（edit）时使用已保存的数据
2. 字段引用使用 `model` 名（如 `input_1234567_123456`），不是字段显示名
3. `format: "number"` 会将结果转为数字类型，适用于数字/金额字段
4. compose 类型的字段引用值为 `null/undefined` 时替换为空字符串
5. function/javascript 类型的字段引用值为字符串时会自动加引号包裹
6. **⚠️ radio/checkbox/select 默认值必须使用控件已有选项列表中的实际 `value`，不能凭猜测赋值（如猜 `"1"` 但实际是 `"选项1"`）。批量设置前先用 `query_form` 读取出这些控件的 `options.options[].value` 再填**
7. **⚠️ `time` 控件默认值格式为 `HH:mm:ss`（含秒），如 `'09:00:00'`，不是 `'09:00'`**

## 追加：UI 规范落库形态核对（componentsConfig.js / utils.js / advancedDefValUtils.js 源码，2026-09-08）

**① 单选/多选/下拉与人员类控件的普通默认值，当前规则（源码 2026-09-08）：**
- `radio`/`checkbox`/`select` 及 `select-user`/`select-depart`/`select-depart-post`/`org-role` 的 schema 恒带 advancedSetting：`{type:compose, value:"", format:string, allowFunc:true, valueSplit:"", customConfig:true}`（radio/checkbox/select 另 customConfig:true = 专用默认值面板；valueSplit 以 UI 产物为准是空串，见上节 ⚠️）。**默认值写在 `advancedSetting.defaultValue.value` 上**；选项控件也可以把值放在 `options.defaultValue`（radio 字符串 / checkbox·多选 select 数组），两者与引擎读取不冲突。
- **值形态**：引擎 `handleFixedData` 仅在 `valueSplit` 非空时解析 `#F:值#` 段（拆段去重后按 valueSplit 拼接）；无 `#F:` 时整串按 valueSplit 拆分。所以多值直接写 `"阅读,运动"`、单选直接写 `"在职"` 即可；`#F:` 段只在与 `$字段$` 引用混拼时用于标记静态片段。API 直写**不需要**手工包 `#F:`。
- **默认当前登录用户/部门/岗位**：设计器与保存迁移统一落成 advancedSetting token `value="#D:CURRENT#"`（见上「select-user / select-depart」节，运行期组件直接解析该 token 填充）；旧属性 `options.defaultLogin: true`（旧勾选框，add/preview 生效、edit 不填充）运行时仍兼容，但只写 defaultLogin 设计器面板回显空白——新建按 token 形态写。

**② 无 advancedSetting 的组件（默认值只在 options 普通默认值栏，无高级默认值）**：`time`、`rate`（null）、`color`、`editor`、`markdown`、`area-linkage`、`location`、`table-dict`、`select-tree`、`link-field`、`org-role`、`auto-number`、`imgupload`/`file-upload`（[]，无面板入口）、`hand-sign`、`ocr`、`barcode`、`map`、`formula`、`summary`/`date+isSummary`、容器与展示类。

**③ schema 遗留键警示**：`markdown`、`location` 的 options 里**存在** `defaultValue` 键（location 另有 `defaultCurrent`「默认当前位置」开关键，false）；`map` 的 defaultValue 被注释。schema 有键 ≠ 设计器面板有默认值入口——doc ③「完全无默认值」按 UI 面板实测为准；若 UI 复核发现 location/markdown 面板其实暴露默认值或「默认当前位置」，以 UI 为准并回改本节。
8. **⚠️ `org-role` / `select-tree` 默认值可能为数组格式 `['value']` 而非字符串；`select-user` / `select-depart` 可能使用 `advancedSetting.defaultValue` 的 `#F:value#` 格式配合 `valueSplit`。设置前先查询控件当前配置确认格式**
