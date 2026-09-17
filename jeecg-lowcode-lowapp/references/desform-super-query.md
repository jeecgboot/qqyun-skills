# 筛选条件（高级查询）

## 概念说明

**筛选条件**（又称高级查询条件）是用户在列表页面自定义的查询条件，与视图里的**数据过滤**是两个独立功能。关联记录控件上的「设置筛选条件」是第三套（`options.filters`，大写 `EQ`），见 `desform-link-record.md`。

| 对比项 | 数据过滤（sjgl） | 筛选条件（高级查询） |
|--------|----------------|------------------|
| 配置入口 | 视图设置 | 列表页筛选条件面板 |
| 操作权限 | 仅具有视图管理权限的管理员 | 所有用户（每人管自己的） |
| 隔离维度 | 按视图隔离 | 按表单编码（code）+ 用户隔离 |
| 生效范围 | 强制过滤，用户不可关闭 | 用户自行选择是否启用 |
| 同时生效数 | 每个视图一套 | 同一时刻最多选中 1 条 |

---

## API

基础路径：`/desform/superQuery`

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/list` | `code`（desformCode） | 查询当前用户在该表单下的所有筛选条件 |
| POST | `/save` | RequestBody: 筛选条件对象 | 新建筛选条件 |
| POST | `/update` | RequestBody: 筛选条件对象（含 `id`） | 更新筛选条件 |
| POST | `/updateSelected` | `{id, code, selected}` | 切换选中状态 |
| DELETE | `/remove?id=xxx` | `id`（URL 参数） | 删除筛选条件 |

---

## 数据结构

### 筛选条件对象

```json
{
  "id": "2042432444215709697",
  "title": "包含马",
  "code": "student_form",
  "conditionType": "and",
  "conditions": null,
  "conditionsGroup": [
    {
      "matchType": "and",
      "queryItems": [
        {
          "field": "input_1775737429491_692500",
          "rule": "like",
          "val": "马",
          "type": "input",
          "valText": null
        }
      ]
    }
  ],
  "selected": true,
  "myself": false,
  "createBy": "admin",
  "createTime": "2026-04-10 10:40:15"
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 条件 ID，新建时不传，更新/删除时必传 |
| `title` | string | 条件名称（用户自定义） |
| `code` | string | 表单编码（desformCode） |
| `conditionType` | string | 顶层分组关系：`"and"` / `"or"` |
| `conditions` | null | 旧版字段，固定传 `null` 或不传 |
| `conditionsGroup` | array | 条件分组列表，见下方说明 |
| `selected` | bool | 是否选中（即是否作为当前生效的筛选条件） |
| `myself` | bool | 是否仅自己可见（通常传 `false`） |

### conditionsGroup 结构

```json
[
  {
    "matchType": "and",
    "queryItems": [
      {
        "field": "input_1775737429491_692500",
        "rule": "like",
        "val": "马",
        "type": "input",
        "valText": null
      }
    ]
  }
]
```

| 字段 | 说明 |
|------|------|
| `matchType` | 该分组内条件关系：`"and"` / `"or"` |
| `queryItems` | 具体条件列表 |
| `queryItems[].field` | 字段 model |
| `queryItems[].rule` | 比较规则，**必须参照 `desform-filter-rules.md` 中的合法值** |
| `queryItems[].val` | 比较值。**多词"任意匹配"是独立操作符 `like_with_and`（包含任意）：val 传逗号分隔关键词，命中任一即匹配；文本类没有 `not_like`「不包含」操作符**（2026-09-10 源码核对；规则集以 `desform-filter-rules.md` 为准） |
| `queryItems[].type` | 字段控件类型（如 `input`、`select`、`number`、`date`） |
| `queryItems[].valText` | 展示用文本（select/字典等控件填标签，其余传 `null`） |

---

## 选中状态规则

- **同一表单下同一用户最多只能选中 1 条**。
- 调用 `/save` 时若 `selected=true`，系统会自动取消该用户此表单下其他条件的选中状态。
- 调用 `/update` 时，`selected` 必须传入当前实际状态（先查询再更新），否则可能意外切换。
- 专门切换选中状态时使用 `/updateSelected`，不需要传完整对象。

---

## 应用到数据查询

当用户选中了某个筛选条件后，列表查询接口（`/desform/data/list` 等）会携带 `superQuery` URL 参数。

**`superQuery` 的值**：将 `conditionsGroup` 转换为以下 JSON，再做 URL 编码：

```json
{
  "matchType": "and",
  "superQueryGroup": [
    {
      "queryItems": [
        {
          "field": "input_1775737429491_692500",
          "rule": "like",
          "val": "何",
          "type": "input",
          "valText": null
        }
      ],
      "matchType": "and"
    }
  ]
}
```

与筛选条件对象的对应关系：
- 外层 `matchType` ← `conditionType`
- `superQueryGroup` ← `conditionsGroup`（结构一致，仅 key 名不同）

未选中任何筛选条件时，`superQuery` 参数不传或为空。

> ⚠️ 2026-09-10 实测：`superQuery` 的值必须**双重 URL 编码**才生效——先把 JSON `urllib.parse.quote(json_str, safe='')` 编码一次作为参数值，再由请求层编码一次；只编码一次时服务端**静默忽略、返回全量**（success=true 不报错，`total` 不变）。Python 校验配方：`params={'desformCode':code,'pageNo':1,'pageSize':100,'superQuery':urllib.parse.quote(json.dumps({'matchType':'and','superQueryGroup':[...]}))}`。
>
> 落库归一化（实测 312 条 round-trip）：`/save` 会丢弃 `name`/`multiple`/`timestamp` 并置 `valText` 为 `null`，只保留 `field`/`rule`/`type`/`val`；展示文本由前端按字段配置解析，不依赖 valText，也不需要为块参纠结 `""` 与 `null`。

---

## Python 用法

```python
import sys
sys.path.insert(0, r'<skill目录>/scripts')
from desform_utils import init_api, api_request

init_api('<api_base>', '<token>')

# 查询所有筛选条件
def list_super_queries(code):
    result = api_request('/desform/superQuery/list', method='GET', params={'code': code})
    return result['result']

# 新建筛选条件
def save_super_query(code, title, conditions_group, condition_type='and', selected=False, myself=False):
    body = {
        'code': code,
        'title': title,
        'conditionType': condition_type,
        'conditions': None,
        'conditionsGroup': conditions_group,
        'selected': selected,
        'myself': myself,
    }
    return api_request('/desform/superQuery/save', data=body)

# 更新筛选条件（需先查询获取完整对象）
def update_super_query(record):
    """record 为 list_super_queries 返回的条目，修改字段后直接传入"""
    return api_request('/desform/superQuery/update', data=record)

# 切换选中状态
def update_super_query_selected(id, code, selected):
    body = {'id': id, 'code': code, 'selected': selected}
    return api_request('/desform/superQuery/updateSelected', data=body)

# 删除筛选条件
def delete_super_query(id):
    return api_request('/desform/superQuery/remove', method='DELETE', params={'id': id})
```

> ⚠️ 构建 `conditionsGroup` 中的 `rule` 值前，**必须阅读 `references/desform-filter-rules.md`**，使用非法 rule 值会导致前端查询报错。
