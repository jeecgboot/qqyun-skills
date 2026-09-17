# 全新创建的设计子表（sub-table-design）

用户说「全新创建的子表」「设计子表」「内部子表」时读本文，不要和外部子表（`link-record` + `isSubTable`）混用。

对照设计器右侧面板（布局列数 / 默认值 / 操作控制 / 数据绑定 Key / 操作属性 / 校验 / 字段说明）。

子表内允许/禁止的 **列控件 type** 仍以 `desform-json-config.md`「子表内支持的 type」和「全新创建的设计子表不支持的 type」为准，本文不重复。

---

## 面板 → options

全部写在子表控件的 `options` 里（改的时候必须套 `{"options": {...}}`）。

| 面板 | options 字段 | 取值 | 工厂默认 |
|------|----------------|------|----------|
| 布局列数 单列/双列/三列/四列 | `columnNumber` | `1` / `2` / `3` / `4` | `2` |
| 默认值（右侧格子） | `defaultValType` + `defaultValue` | `none` 且 `[]` = 空；`custom` 时 `defaultValue` 为默认行数组 | `none` / `[]` |
| 操作控制 · 允许新增 | `allowAdd` | `true` / `false` | `true` |
| 操作控制 · 显示复选框 | `showCheckbox` | `true` / `false` | `true` |
| 操作控制 · 显示序号 | `showNumber` | `true` / `false` | `true` |
| 操作控制 · 自适应高度 | `autoHeight` | `true` / `false` | `true` |
| 数据绑定 Key | 控件顶层 `model` | `sub_table_design_<时间戳>` | 自动生成，**禁止手改** |
| 操作属性 · 允许新增 | 同 `allowAdd` | 面板出现两次，只改这一个字段 | `true` |
| 操作属性 · 隐藏 | `hidden` | `true` / `false` | `false` |
| 操作属性 · 新增时隐藏 | `hiddenOnAdd` | `true` / `false` | `false` |
| 校验 · 必填 | `required` | `true` / `false` | `false` |
| 字段说明 | `fieldNote` | 字符串 | `""` |

面板没有、但 options 里还有：`operationMode`（`1` 行内编辑 / `2` 弹出编辑）、`isWordStyle`、`isWordInnerGrid`、`defaultRows`、`showRowButton`。用户没说不要改。

`columnNumber` 必须和顶层 `columns` 数组长度一致（`span = 24 / columnNumber`）。只改数字不改 `columns`，设计器会空白列或挤压。

---

## 创建时 JSON（全部支持，直接写在子表字段上）

`desform_creator.py` 对 `type: "sub-table-design"` 会把面板项写进 `options`。用户指定了就写，没指定用工厂默认。

> ⚠️ **复制示例前必看：** 下面示例里只有 `columnNumber: 1`（单列布局演示）是特意改的值，其余键全部对齐工厂默认。**不要把示例当"可开关演示"抄成反默认值**——曾因照抄旧示例把 `showCheckbox`/`autoHeight` 写成 `false`，导致真实用户子表没有复选框、固定高度出现内部滚动条（各键默认见下方表格，默认 `true` 的开关没把握时直接不写）。

```json
{
  "name": "订单明细",
  "type": "sub-table-design",
  "columnNumber": 1,
  "operationMode": 1,
  "allowAdd": true,
  "showCheckbox": true,
  "showNumber": true,
  "autoHeight": true,
  "defaultValType": "none",
  "defaultValue": [],
  "hidden": false,
  "hiddenOnAdd": false,
  "required": false,
  "fieldNote": "",
  "fields": [
    {"name": "商品名称", "type": "input", "required": true},
    {"name": "数量", "type": "integer"}
  ]
}
```

| JSON 键 | 对应面板 | 不写时的默认 |
|---------|----------|----------------|
| `columnNumber` | 布局列数 | `2` 双列 |
| `allowAdd` | 允许新增 | `true` |
| `showCheckbox` | 显示复选框 | `true` |
| `showNumber` | 显示序号 | `true` |
| `autoHeight` | 自适应高度 | `true` |
| `defaultValType` | 默认值模式 | `"none"` |
| `defaultValue` | 默认值行 | `[]` |
| `hidden` / `hiddenOnAdd` | 隐藏 / 新增时隐藏 | `false` |
| `required` | 必填 | `false` |
| `fieldNote` | 字段说明 | `""` |

---

## 创建后改面板项

子表容器 **不在** `get_form_fields` 的 map 里。`query_form` 找到 `type == "sub-table-design"`，用它的 `key`：

```python
update_widget(code, {"options": {
    "columnNumber": 1,
    "showCheckbox": True,
    "showNumber": True,
    "allowAdd": True,
    "autoHeight": True,
    "hidden": False,
    "hiddenOnAdd": False,
    "required": False,
    "fieldNote": "",
}}, key=sub_key)
```

只改 `columnNumber` 时必须同时改设计 JSON 里的 `columns`（一条脚本：query → 改 columns + options → `save_design_from_file`），不要只 `update_widget` 数字。

默认值格子：空 = `defaultValType: "none"`、`defaultValue: []`。要预填行时 `defaultValType: "custom"`，`defaultValue` 为对象数组，key 用**列的 model**（不是中文名）。查询工作表那种默认值禁止猜结构，用户要时先 `query_form` 看已有样例。

---

## 转换工作表（subToWorksheet）

全新创建的设计子表（`sub-table-design`）可以 **转成独立工作表**。设计器里是子表右键 / 「将子表转为工作表」。

| 转换前 | 转换后 |
|--------|--------|
| 数据嵌在主表 JSON 里 | 独立 `design_form` + 独立数据 |
| 主表字段 type=`sub-table-design` | 主表字段变成 `link-record` 且 `isSubTable=true` |
| 不出现在应用导航 | 应用里多一张工作表，可单独打开、授权、统计 |
| 列控件受全新子表 type 限制 | 新工作表按普通表单，控件不再受子表白名单限制 |

**不可逆**：转完不能变回内部子表。用户没明确说「转为工作表 / 转换工作表 / 把子表转成工作表」时 **禁止调用**。本会话刚改过的那张表、用户接着点名要转，视为已确认，**不要**再出摘要等 y/n。

### 对应接口（两步，缺一不可）

官方转换接口是 **`POST /desform/subToWorksheet`**。点设计器「转为工作表」实际打 **两个** 请求，没有第三个「一键改掉主表控件」的接口。

| 顺序 | 接口 | 作用 |
|------|------|------|
| 1 | `POST /desform/subToWorksheet` | 建独立工作表、迁子表数据、建双向关联。body 见下。**不改**主表 `desformDesignJson` |
| 2 | `PUT /desform/edit` | 把主表该字段从 `sub-table-design` 换成 `link-record` + `isSubTable=true` 并保存 |

只调第 1 步：应用导航会多一张工作表，设计器里仍是「设计子表 / 转为工作表」（实测：订单信息 → 订单明细）。判定成功必须 `query_form` 主表该字段已是 `link-record` 且 `isSubTable=true`。

`scripts/sub_to_worksheet.py` 一条命令做完两步。禁止只 POST 完就报成功。

后端 `DesignFormController.subToWorksheet` **不会**按主表 `id` / `desformCode` / 控件 `key` 自己去查设计再拼 body。必须把前端同款完整 JSON 一次 POST 上去。

### 一条命令（强制）

会话里已有 api-base / token / 租户 / 应用时直接跑，禁止先 list 租户/应用、禁止猜键多次探测。

```bash
python "<skill目录>/scripts/sub_to_worksheet.py" --api-base <URL> --token <TOKEN> --tenant-id <TID> --app-id <APP> --parent-code <主表code> --sub-name <子表显示名>
```

Windows 中文名用 UTF-8 `--config`（同应用 CRUD；禁止 PowerShell `--json '{"subName":"中文"}'`，禁止 `python -c` 内联中文）：

```json
{"parentCode":"order_info","subName":"订单明细表"}
```

脚本内部：`query_form` → 已是工作表子表则成功退出 → 否则按下面规则拼 body → 若 `originSubCode` 已被占用则 `delete_form` → `POST /desform/subToWorksheet` → **把主表里的 `sub-table-design` 换成 `link-record` + `isSubTable=true` 并保存设计**（后端只建新表+迁数据，不改主表设计 JSON；不做这一步界面仍是内嵌设计子表）。

### body 怎么拼（前端 Network 实测，键名不可改）

`POST /desform/subToWorksheet`，**必须 JSON body**（只带 query / GET 会报 `Required request body is missing`）。lowApp 先 `init_lowapp`。

```json
{
  "subModel": "新工作表里反向 link-record 的 model",
  "parentCode": "主表 desformCode",
  "parentModel": "主表里替换子表后的 link-record model",
  "originSubCode": "原 sub-table-design 的 model",
  "designForm": {
    "desformName": "新工作表名称（子表显示名）",
    "desformCode": "原 sub-table-design 的 model（当作新表编码）",
    "desformDesignJson": "<字符串，不是对象>"
  }
}
```

从主表设计里找到 `type=="sub-table-design"` 且 `name==子表显示名` 的控件，再填：

| 键 | 取值 |
|----|------|
| `parentCode` | 主表 `desformCode` |
| `originSubCode` | 原子表顶层 **`model`**（`sub_table_design_<时间戳>`） |
| `parentModel` | `"link_record_"` + 原子表顶层 **`key`**（不是 model） |
| `subModel` | 新生成的反向 `link-record` 的 `model` |
| `designForm.desformName` | 原子表 `name` |
| `designForm.desformCode` | **等于** `originSubCode`（新工作表编码复用原子表 model） |
| `designForm.desformDesignJson` | `json.dumps(新设计, ensure_ascii=False)`，必须是**字符串** |

实测对照（订单信息 → 订单明细表）：子表 `key=1788260205955_630240`、`model=sub_table_design_1788260205955_177913` → `parentModel=link_record_1788260205955_630240`，`originSubCode`/`desformCode=sub_table_design_1788260205955_177913`，`subModel=link_record_<新key>`。

### `desformDesignJson` 怎么拼

1. 把子表 `columns[].list` 里每个控件 `deepcopy` 升为主字段：`isSubItem=false`，去掉 `subOptions`，**保留原 key/model**。
2. 末尾追加反向关联主表的 `link-record`（**不要** card 包裹）：
   - `name` = 主表名称；`options.sourceCode` = 主表 code
   - `showMode=single`，`showType=card`
   - `titleField` = 主表 `config.titleField`
   - `twoWayModel` = body 的 `parentModel`
   - 顶层 `isSelf=true`
   - `advancedSetting.defaultValue.customConfig=true`，`valueSplit=""`
3. `config`：deepcopy 主表 config；`titleField` 改成升上来的第一列 model（不要用反向 link-record）；`hasWidgets` 含列 type + `link-record`。

工厂：`LINK_RECORD(主表名, 主表code, 主表titleField, show_mode='single', show_type='card', is_self=True, wrap=False)`，再写 `twoWayModel`。

### 「编码已存在」

新表编码 = 原子表 `model`，所以半成品或并发点 UI 都会撞码。**先看主表字段，不要直接再 POST。**

| 主表该字段 | `originSubCode` 是否已有表 | 处理 |
|-----------|---------------------------|------|
| 已是 `link-record` 且 `isSubTable=true` | 通常已有 | **已经转完**，当成功，禁止再 POST、禁止删新表 |
| 仍是 `sub-table-design` | 已有 | 半成品：`delete_form(originSubCode)`（逻辑+物理）后再 POST |
| 仍是 `sub-table-design` | 没有 | 直接 POST |
| POST 后仍报「xxx已存在」 | — | 再 `query_form(主表)`：已是工作表子表 → 当成功（并发 UI 已转）；仍是内部子表 → 报错停，**不要换键重试** |

### 禁止探测（实测失败，不要再走）

接口**不会**按下面这些键反查主表再转换：

| 错 body | 报错 |
|---------|------|
| `{}` 或缺 `designForm` | `designForm is null` |
| 只 query / GET，无 JSON body | `Required request body is missing` |
| `designForm` 不完整（缺 `desformCode` 等） | `getByCode` cache Null key |
| 只传 `id` / `desformCode` / `key` / `widgetKey` / `model` / `parentId` / `sourceCode` | 仍 `designForm is null` |

body 只允许上面 5 个顶层键 + `designForm` 三字段。

---

## 给**已有**表补建子表（2026-09-16 实测，5 张表一次过）

场景：表单已经建好了，某个字段当初落成了普通控件（如 `input`），现在要改成「可加多条」的设计子表。

### 配方

```python
from desform_utils import (make_sub_table, SUB_INPUT, SUB_PHONE, SUB_TEXTAREA, SUB_DATE, SUB_FILE,
                           query_form, export_design_json, save_design_from_file, save_auth_from_design)

cont, skey = make_sub_table('其他联系人信息', [], column_number=3)   # ⚠️ 返回 **2 元组** (容器, key)
cont = cont if isinstance(cont, dict) else cont[0]
for i, (cname, fac) in enumerate([('名称', SUB_INPUT), ('手机', SUB_PHONE), ('职位', SUB_INPUT)]):
    w = fac(cname, skey)                    # ⚠️ SUB_* **必须传 parent_key**，返回 **3 元组**
    cont['columns'][i]['list'] = [w[0]]     # ⚠️ 列里要放**解包后的 dict**，不是元组
```

### 五个要点（漏一个就出静默故障）

1. **先建空壳拿 key，再填列**：`make_sub_table(名, [], column_number=N)` → `(容器, key)`；
   列数必须等于 `column_number`（`span` 自动 = 24/N），填第 i 列用 `columns[i]['list'] = [...]`
2. **两层解包**：容器取 `[0]`；`SUB_*` 返回的 `(widget, key, model)` 也要取 `[0]`。
   漏了会把 tuple 序列化成 JSON 数组 —— **保存接口照样返回成功**，
   之后 `queryByCode` 遍历时 NPE，**整张表查不出来**
3. **摘掉原来的同名普通控件**，再把容器追加进 `design['list']`；
   `design['config']['hasWidgets']` 里补 `sub-table-design`
4. **保存前本地自检**：递归扫 design，任何 `tuple`、或 `columns[].list` 里的非 dict 项 → 直接放弃保存
5. `export_design_json` → 改 → `save_design_from_file` → `save_auth_from_design`

### 验证

- 结构：回读 `query_form`，看 `columns[].list` 每项都是 dict（含 `isSubItem: true`、
  `subOptions.parentKey` = 子表 key）
- 健康：`list_data(code, 1, 2)` 能查通 = 设计 JSON 没被污染
- ⚠️ **不要用 `get_form_fields` 验证子表列** —— 它不返回子表列，会得到空结果误判为「没建成」
