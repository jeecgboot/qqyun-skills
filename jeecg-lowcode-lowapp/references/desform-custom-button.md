# 自定义动作参考文档

自定义动作包含两类功能：
- **自定义按钮**：列表视图中的操作按钮，通过独立的 `/desform/button/*` API 管理
- **自定义规则**：目前只有**删除规则**，控制用户是否可以删除记录，通过 `PUT /desform/view/updateViewConfig` 配置

> ⚠️ **执行入口是 CLI 一条命令** `scripts/list_view/desform_custom_button.py`（建/改/删/查/视图绑定/排序，支持字段中文名解析、rule 合法化、link-record 目标表自动推断；JSON 约定见 SKILL.md「自定义动作」章节）。本文档只作**数据结构与规则参考**，下方 Python 工具函数仅供脚本内部/特殊场景使用——业务操作不要手写调用它的临时 .py。

---

## 删除规则（customRules.delete）

删除规则配置在**视图级别**，通过更新视图配置接口写入。

### 数据结构

```json
{
    "id": "<视图ID>",
    "customRules": {
        "delete": {
            "enabled": true,
            "conditionType": "and",
            "conditionsGroup": [
                {
                    "matchType": "and",
                    "showPop": false,
                    "queryItems": [
                        {
                            "field": "select_1775716186796_352048",
                            "rule": "eq",
                            "type": "select",
                            "val": "已完成",
                            "valText": ""
                        }
                    ]
                }
            ],
            "allowDelete": "Y",
            "tipMessage": ""
        }
    }
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `enabled` | boolean | 是否启用删除规则，默认 `false`（不启用时所有人均可删除） |
| `conditionType` | `"and"` \| `"or"` | 条件分组之间的关系 |
| `conditionsGroup` | array | 条件分组，格式与自定义按钮的 `conditionsGroup` 完全一致 |
| `allowDelete` | `"Y"` \| `"N"` | 满足条件时的行为：`"Y"` = 允许删除（白名单模式），`"N"` = 禁止删除（黑名单模式） |
| `tipMessage` | string | 不允许删除时的提示信息，默认为空 |

> `conditionsGroup` 中的 `rule` 值规则与自定义按钮显示条件完全一致，参见 `references/desform-filter-rules.md`。

### API 调用

```
PUT /desform/view/updateViewConfig
Content-Type: application/json

{
    "id": "<视图ID>",
    "customRules": { ... }
}
```

### Python 示例

```python
import sys, requests
sys.path.insert(0, r'<skill目录>/scripts')
from desform_utils import init_api, query_list_views

init_api('<api_base>', '<token>')

# 获取视图 ID
views = query_list_views('my_form_code')
view_id = next(v['id'] for v in views if v['name'] == '全部')

# 设置删除规则：任务状态为"已完成"时才允许删除
import requests
resp = requests.put(
    '<api_base>/desform/view/updateViewConfig',
    headers={'X-Access-Token': '<token>', 'Content-Type': 'application/json'},
    json={
        "id": view_id,
        "customRules": {
            "delete": {
                "enabled": True,
                "conditionType": "and",
                "conditionsGroup": [
                    {
                        "matchType": "and",
                        "showPop": False,
                        "queryItems": [
                            {
                                "field": "select_xxx",
                                "rule": "eq",
                                "type": "select",
                                "val": "已完成",
                                "valText": ""
                            }
                        ]
                    }
                ],
                "allowDelete": "Y",
                "tipMessage": "只有状态为已完成的记录才能删除"
            }
        }
    }
)
print(resp.json())
```

### 禁用删除规则

```python
resp = requests.put(
    '<api_base>/desform/view/updateViewConfig',
    headers={'X-Access-Token': '<token>', 'Content-Type': 'application/json'},
    json={"id": view_id, "customRules": {"delete": {"enabled": False}}}
)
```

---

## 自定义按钮

自定义按钮是列表视图中的操作扩展功能，通过独立的 `/desform/button/*` API 管理，与视图配置完全分离。

---

## 数据结构（ButtonInfo）

```typescript
interface ButtonInfo {
  id?: string;              // 按钮唯一ID（新建时不传，由后端生成）
  label: string;            // 按钮名称（显示文本）
  icon: string;             // Iconify 图标名，格式：{集合}:{图标名}，如 "ant-design:check-circle-outlined"
  color: string;            // 按钮颜色（RGB格式，见下方预设色）
  note: string;             // 按钮说明/tooltip 文字
  showStatus: string;       // 显示方式：'always' | 'condition'
  clickThen: string;        // 点击动作：'execute' | 'confirm' | 'form'
  flowStatus: boolean;      // 是否关联工作流（form 模式下可选，其他模式见说明）
  processId?: string;       // 工作流流程ID（后端保存时自动生成，不需手动传入）
  seq?: number;             // 排序序号
  allView?: boolean;        // true=全局按钮（出现在所有视图），false/不传=仅当前视图

  // showStatus='condition' 时配置（推荐使用新格式 conditionsGroup）
  conditionsGroup?: FilterItemGroup[];
  conditionType?: 'and' | 'or';   // 条件分组之间的关系
  conditionList?: FilterItem[];    // 旧格式（兼容），单分组条件

  // clickThen='confirm' 时配置
  confirmText?: {
    tip: string;    // 提示文字
    ok: string;     // 确认按钮文字
    cancel: string; // 取消按钮文字
  };

  // clickThen='form' 时配置
  buttonFormConfig?: {
    formTable: string;         // 'current'=当前表，'link-record'=关联记录表
    formType: string;          // 'update'=编辑字段，'create'=新建记录
    updateFieldList?: FormField[];  // formType='update' 时，指定可编辑字段
    createFormCode?: string;   // formType='create' 时，目标表单编码
    createFormField?: string;  // formType='create' 时，与当前记录关联的字段
    linkRecordField?: string;  // formTable='link-record' 时，关联记录字段 model
    linkRecordTable?: string;  // formTable='link-record' 时，关联表单编码
  };
}

interface FormField {
  // ⚠️ key 必须是列的原始 key（无类型前缀），不是 model！
  // 例如：key="1775716186796_271142"，而不是 model="select_1775716186796_352048"
  // 通过 get_form_fields(code) 返回的 fields_map[字段名]['key'] 获取
  key: string;         // 列 key（无类型前缀，如 "1775716186796_271142"）
  attr: string;        // '' | 'readonly' | 'required'
  defaultVal: string;  // 默认值
}

interface FilterItemGroup {
  matchType: 'and' | 'or';  // 组内条件的关系
  queryItems: FilterItem[];
}

interface FilterItem {
  field: string;                        // 字段 model
  rule: string;                         // 运算符
  val: string | number | any[];         // 条件值
  type?: string;                        // 字段类型
  name?: string;                        // 字段名（展示用）
  valText?: string;                     // 条件值文本（展示用）
}
```

---

## clickThen 三种动作模式

### `execute` — 直接执行工作流

点击后立即触发工作流，无任何弹窗。

- `flowStatus` 必须为 `true`，且必须已关联工作流（processId 有效）
- 适合：一键提交、一键标记等不需要额外输入的操作
- 关联工作流：见下方"工作流关联说明"

### `confirm` — 二次确认后执行工作流

点击后弹出确认对话框，用户确认后触发工作流。

- `flowStatus` 必须为 `true`，且必须已关联工作流
- 必须配置 `confirmText`
- 适合：删除、归档、发送通知等需要防止误操作的场景

```python
button = {
  "clickThen": "confirm",
  "flowStatus": True,
  "confirmText": {
    "tip": "确定要发送通知吗？",
    "ok": "确定",
    "cancel": "取消"
  }
}
```

### `form` — 打开表单操作

点击后弹出表单弹窗，用户填写后保存，可选是否同时触发工作流。

- `flowStatus` 可为 `true` 或 `false`（若为 `false` 则无需关联工作流，**完全可以纯 API 完成**）
- 必须配置 `buttonFormConfig`

**表单操作子类型（formTable × formType 组合）：**

| formTable | formType | 效果 |
|-----------|----------|------|
| `current` | `update` | 编辑当前记录的指定字段（弹窗只展示 updateFieldList 中的字段） |
| `current` | `create` | 在当前表单中新建一条记录 |
| `link-record` | `update` | 编辑当前记录关联的关联记录表字段 |
| `link-record` | `create` | 在关联记录表中新建一条关联记录 |

**新建关联记录（源码核对 2026-09-15 `ButtonFormConfig.vue`/`useCustomButton.ts`）：** `formTable`=「填写对象」`current`当前记录/`link-record`关联记录(单条)；`formType`=「填写内容」`update`填写指定字段/`create`新建关联记录。槽位一律存**控件 key**：
- `current`+`create`（＝「点击后当前记录，新建关联记录，关联字段「X」」）：`createFormField`=**当前表**内 link-record 字段 key，`createFormCode`=该字段 `options.sourceCode`；运行时打开该表单新建并挂回当前记录；单条且已有值时报「已有关联记录，无法重复添加」。
- `link-record`+`create`：`linkRecordField`=当前表 link-record 字段 key，`linkRecordTable`=其 sourceCode；`createFormField`=**关联记录表内**的 link-record 字段 key，`createFormCode`=其 sourceCode；运行时要求当前记录该关联字段**已有值**（否则报「“X”为空」），与 current 形态不是一回事，勿互套。
- 「点击后当前记录的【X】可填写/必填」= `current`+`update`+`updateFieldList[{key,attr,defaultVal}]`，且 `clickThen` 用 `form`（`execute`=点击直接跑流程无弹窗，仅用于「点击后直接执行」类）。

---

## 显示条件（showStatus）

### `always` — 始终显示

按钮在所有记录上都显示。

### `condition` — 条件显示

仅在满足条件的记录上显示按钮。推荐使用新格式（conditionsGroup）：

```python
button = {
  "showStatus": "condition",
  "conditionType": "and",        # 组间关系：and / or
  "conditionsGroup": [
    {
      "matchType": "and",        # 组内关系：and / or
      "showPop": False,          # 固定传 False（UI 状态字段）
      "queryItems": [
        {
          "field": "status_xxx", # 字段 model
          "rule": "eq",          # 使用 code，不能用 "=" 等符号
          "val": "pending",
          "type": "select",
          "valText": ""          # 空字符串，不要传 null
        }
      ]
    }
  ]
}
```

> ⚠️ **构建条件前必须阅读 `references/desform-filter-rules.md`**，其中包含完整的 rule 合法值列表、各字段类型对应可用规则、及常见错误写法对照表。直接使用 `=`、`!=` 等符号会导致前端报错。

---

## 图标

`icon` 字段必须使用 **Iconify** 格式：`{图标集}:{图标名}`。传裸字符串（如 `"check"`）无法渲染。

**常用图标速查（ant-design 集合）：**

| 含义 | icon 值 |
|------|---------|
| 确认/完成 | `ant-design:check-circle-outlined` |
| 加号/新建 | `ant-design:plus-outlined` |
| 编辑 | `ant-design:edit-outlined` |
| 删除 | `ant-design:delete-outlined` |
| 发送/邮件 | `ant-design:mail-outlined` |
| 上传 | `ant-design:upload-outlined` |
| 下载 | `ant-design:download-outlined` |
| 刷新 | `ant-design:reload-outlined` |
| 搜索 | `ant-design:search-outlined` |
| 设置 | `ant-design:setting-outlined` |
| 关闭 | `ant-design:close-circle-outlined` |
| 警告 | `ant-design:warning-outlined` |
| 信息 | `ant-design:info-circle-outlined` |
| 星标 | `ant-design:star-outlined` |
| 用户 | `ant-design:user-outlined` |
| 打印 | `ant-design:printer-outlined` |
| 导出 | `ant-design:export-outlined` |
| 链接 | `ant-design:link-outlined` |
| 眼睛/查看 | `ant-design:eye-outlined` |
| 锁 | `ant-design:lock-outlined` |

> 更多图标可在 [Iconify](https://icon-sets.iconify.design/) 搜索，选择 `ant-design` 集合。

---

## 预设颜色

```python
COLOR_BLUE   = 'rgb(33, 150, 243)'
COLOR_PURPLE = 'rgb(156, 39, 176)'
COLOR_INDIGO = 'rgb(63, 81, 181)'
COLOR_RED    = 'rgb(233, 30, 99)'
COLOR_ORANGE = 'rgb(255, 152, 0)'
COLOR_GREEN  = 'rgb(76, 175, 80)'
COLOR_CYAN   = 'rgb(0, 188, 212)'
```

---

## API 接口列表

| 操作 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 创建按钮 | POST | `/desform/button/save` | 新建按钮 |
| 更新按钮 | POST | `/desform/button/update` | 更新按钮配置 |
| 删除按钮 | DELETE | `/desform/button/remove?buttonId={id}&designFormCode={code}` | 删除按钮。⚠️ 实测（2026-09-03）必须同时传 `buttonId` 和 `designFormCode` 两个参数：只传 `id` 报 500「Required request parameter 'buttonId'」，补 `buttonId` 后又报缺 `designFormCode`。curl 示例：`curl -X DELETE ".../desform/button/remove?buttonId=xxx&designFormCode=my_form"` |
| 查询列表 | GET | `/desform/button/list` | 查询表单/视图的按钮列表 |
| 查询单个 | GET | `/desform/button/queryById` | 根据 id 查询详情 |
| 验证名称 | GET | `/desform/button/checkOnly` | 验证按钮名称是否重复 |
| 重排序 | POST | `/desform/button/resetSequence` | 批量更新按钮排列顺序 |
| 绑定视图 | POST | `/desform/button/addRelation` | 将按钮关联到指定视图 |
| 解绑视图 | DELETE | `/desform/button/removeRelation` | 移除按钮与视图的绑定 |
| 翻译条件 | POST | `/desform/button/translateCondition` | 将条件表达式翻译为可读文本 |

**通用请求参数（POST body / GET query）：**
- `designFormCode`：表单编码（必填）
- `viewId`：视图 ID（可选，不传则为全局按钮）

---

## Python 工具函数（desform_button_utils.py）

```python
import sys
sys.path.insert(0, r'<skill目录>/scripts')
from desform_utils import init_api
from desform_button_utils import (
    create_button,
    update_button,
    delete_button,
    list_buttons,
    get_button,
    reorder_buttons,
    add_button_to_view,
    remove_button_from_view,
)

# ⚠️ 敲敲云（租户 + 应用）工作表的按钮必须用 init_lowapp 带租户/应用头，
#    用 init_api（默认 X-Tenant-Id=1）会 401（2026-09-03 实测）：
# from desform_lowapp_utils import init_lowapp
# init_lowapp('<api_base>', '<token>', tenant_id=<租户ID>, app_id=<应用ID>)
init_api('<api_base>', '<token>')   # 仅普通表单设计器（无租户/应用两级）场景
```

### create_button

> **⚠️ `flowStatus` 必须传 `True`，否则报 "Id must not be null"**
>
> 后端在 `flowStatus=True` 时会自动创建一个空 buttonEvent 流程 shell，保存时需要该流程 ID。不传或传 `False` 则 ID 为 null，MongoDB 报错。返回值中 `result.processId` 即为自动创建的空流程 ID；若需绑定已有流程，再调 `update_button` 将 `processId` 替换为目标流程 ID。

```python
result = create_button(
    form_code='my_form',
    view_id='view_id_001',     # 传 None 则为全局按钮
    button={
        'label': '发送通知',
        'icon': 'ant-design:mail-outlined',   # Iconify 格式：{集合}:{图标名}
        'color': 'rgb(233, 30, 99)',
        'note': '向相关人员发送通知',
        'showStatus': 'condition',
        'clickThen': 'form',
        'flowStatus': True,    # ⚠️ 必须为 True，否则报 "Id must not be null"
        'conditionType': 'and',
        'conditionsGroup': [...],
        'buttonFormConfig': {
            'formTable': 'current',
            'formType': 'update',
            'updateFieldList': [
                # key 必须是列的原始 key（无类型前缀），通过 get_form_fields 的 fields_map[name]['key'] 获取
                {'key': '1775716186788_712670', 'attr': 'required', 'defaultVal': ''}
            ]
        }
    }
)
# 返回 {'id': '...', 'processId': '...', ...}
```

### update_button

```python
update_button(
    button_id='btn_id_001',
    form_code='my_form',
    view_id='view_id_001',
    changes={'label': '新名称', 'color': 'rgb(76, 175, 80)'}
)
```

### list_buttons

```python
buttons = list_buttons(form_code='my_form', view_id='view_id_001')
# view_id=None 返回所有按钮（含全局按钮）
```

### reorder_buttons

```python
# 按 id 列表顺序重排序
reorder_buttons(['btn_id_003', 'btn_id_001', 'btn_id_002'])
```

### 视图绑定

```python
add_button_to_view(button_id='btn_id_001', view_id='view_id_002')
remove_button_from_view(button_id='btn_id_001', view_id='view_id_002')
```

---

## 工作流关联说明

`execute` 和 `confirm` 模式必须关联工作流才能正常触发。工作流关联机制如下：

1. 调用 `create_button`（`flowStatus=True`）时，后端自动生成一个 `processId` 并随结果返回
2. 该 `processId` 是工作流的占位符，**工作流节点内容尚未配置**
3. 工作流节点（审批人、连线、条件等）需通过 **`jeecg-lowcode-miniflow` 技能** 完成配置

**完整流程：**

```
① 用本技能创建按钮（flowStatus=True）
        ↓
② 从返回结果中获取 processId
        ↓
③ 使用 jeecg-lowcode-miniflow 技能
   以该 processId 为 customProcessId 创建/配置工作流节点
```

**`form` 模式 + `flowStatus=False` 不需要工作流，可完全通过本技能的 API 自动完成。**

---

## 完整示例：创建一个"编辑指定字段"按钮

```python
import sys
sys.path.insert(0, r'<skill目录>/scripts')
from desform_utils import init_api
from desform_button_utils import create_button

init_api('https://your-api.com/jeecgboot', 'your-token')

# 创建一个"更新状态"按钮，仅在状态为"待处理"时显示
result = create_button(
    form_code='task_form',
    view_id='view_001',
    button={
        'label': '标记完成',
        'icon': 'ant-design:check-circle-outlined',
        'color': 'rgb(76, 175, 80)',
        'note': '将该任务状态更新为已完成',
        'showStatus': 'condition',
        'conditionType': 'and',
        'conditionsGroup': [
            {
                'matchType': 'and',
                'showPop': False,
                'queryItems': [
                    {
                        'field': 'select_1774xxx_status',
                        'rule': 'eq',
                        'val': 'pending',
                        'type': 'select',
                        'valText': ''
                    }
                ]
            }
        ],
        'clickThen': 'form',
        'flowStatus': False,
        'buttonFormConfig': {
            'formTable': 'current',
            'formType': 'update',
            'updateFieldList': [
                {
                    # key 是列原始 key（无前缀），通过 get_form_fields 的 fields_map[name]['key'] 取得
                    'key': '1774xxx_status',   # 不是 model "select_1774xxx_status"
                    'attr': 'required',
                    'defaultVal': 'done'
                }
            ]
        }
    }
)
print('按钮ID:', result.get('id'))
```

---

## 按钮的「权限说明」与「可用条件」（还原原应用的置灰＋提示）

原应用（明道云等）里按钮通常配了**可用条件**：条件不满足时按钮**置灰**，鼠标悬浮显示一句说明
（例：「状态为【草稿】，按钮可用」「合同审批通过后，可申请开发票」）。

**敲敲云没有置灰态** —— 自定义按钮只有「显示 / 不显示」两态（`showStatus: always | condition`）。
落地口径（2026-09-17 MEGA-项目管理 实测）：
- `note` 字段 = **那句说明原文**（前端渲染成按钮的悬浮提示）；
- 同时把「可用条件」配成 `showStatus: 'condition'` + `conditionsGroup`，条件不满足时按钮**不出现**，
  从源头挡住非法状态流转；
- `note` 默认会被填成按钮名（`{"label":"发起合同审批","note":"发起合同审批"}`），
  必须显式改写成说明文案，否则悬浮提示等于没写。

```python
update_button(button_id=b['id'], form_code='mj_contract', changes={
    'note': '状态为【草稿】，按钮可用',
    'showStatus': 'condition', 'conditionType': 'and',
    'conditionsGroup': [{'matchType': 'and', 'showPop': False, 'queryItems': [
        {'field': 'select_xxx', 'rule': 'eq', 'val': '草稿', 'type': 'select', 'valText': ''}]}],
})
```
多值用 `rule: 'in'` + **逗号串**（`val: '待启动,进行中,暂停'`）；数值字段（含公式/汇总）
用 `rule: 'gt'` + 数字（例：`待收款 > 0`）。

### 「在当前记录上新建关联记录」的按钮

原应用的「申请发票 / 登记收款」这类（点一下在当前合同下建一条开票记录/收款登记），
**不挂流程**，用：

```python
button = {
    'label': '申请发票', 'clickThen': 'form', 'flowStatus': False, 'allView': True,
    'showStatus': 'condition',
    'conditionsGroup': [{'matchType': 'and', 'showPop': False, 'queryItems': [
        {'field': 'select_审批状态', 'rule': 'eq', 'val': '审批通过', 'type': 'select', 'valText': ''}]}],
    'buttonFormConfig': {'formTable': 'current', 'formType': 'create',
                         'createFormField': '<当前表 link-record 字段的 key>',
                         'createFormCode': '<该字段 options.sourceCode>',
                         'updateFieldList': []},
}
```
`createFormField` 取**当前表**那个 link-record 字段的 `key`（不是 model），`createFormCode` 是它指向的表；
运行时在当前记录下新建并从关联控件挂回去（单条关联已有值时会被拒绝，多条关联则随便加）。

