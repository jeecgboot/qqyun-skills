# desform_data_utils.py 数据操作工具参考

位于 `scripts/desform_data_utils.py`。提供表单数据的 CRUD、批量操作、复制、回收站等功能。

> **阅读建议**：需要某个函数的详细说明时，直接 grep 函数名定位行号，再用 offset+limit 读取对应章节，无需全量阅读本文件。

## 函数速查表

| 函数 | 适用场景 |
|------|---------|
| `add_data(code, data_dict)` | 新增一条数据 |
| `get_data(code, data_id)` | 查询单条数据 |
| `list_data(code, page, size, super_query, ...)` | 分页查询数据列表（支持高级查询） |
| `edit_data(code, data_id, data_dict)` | 编辑数据（⚠️ 全量覆盖，需先取原数据再合并） |
| `delete_data(code, data_id, hard=False)` | 删除单条（hard=True 物理删除） |
| `delete_data_batch(code, ids, hard=False)` | 批量删除 |
| `copy_record(code, data_id)` | 复制单条数据 |
| `copy_records(code, ids)` | 批量复制数据 |
| `batch_update(code, field, val, id_list)` | 将多条记录的同一字段批量设为相同值 |
| `restore_data(code, ids)` | 从回收站还原数据 |
| `clear_recycle(code)` | 清空回收站（不可恢复） |
| `check_unique(code, field_model, value, exclude_id)` | 检查字段值唯一性 |
| `get_statistical(code, operation_type, field, ...)` | 聚合统计（count/max/min/avg/sum） |

---

## 初始化

```python
from desform_utils import init_api
from desform_data_utils import *   # 或按需导入具体函数

init_api('<api_base>', '<token>')
```

`desform_data_utils` 内部自动导入 `desform_utils.api_request`，**不需要**也**不能**再次 `from desform_data_utils import init_api`（该模块没有 init_api）。

---

## add_data

```python
add_data(code, data_dict) -> dict
# 新增一条表单数据
#
# Args:
#   code:      表单编码
#   data_dict: {字段model: 值, ...}，key 必须是 model 而非字段名
#
# Returns:
#   dict，至少含 id（与 dataId 相同）。
#   实测 POST /desform/data/add 的 result 是 {dataId, customURLFail}，没有 id；
#   函数会把 dataId 规范化为 id，调用方统一用 result['id']。
#
# 示例：
from desform_utils import init_api, get_form_fields
from desform_data_utils import add_data

init_api(api_base, token)
title_field, fields = get_form_fields('my_form')
result = add_data('my_form', {
    fields['姓名']['model']:   '张三',
    fields['手机号']['model']: '13800138001',
    fields['所属部门']['model']: ['dept_001'],
    fields['所属部门']['model'] + '_dictText': '研发组',
})
data_id = result['id']
```

写入前必须按下方「控件落库格式」构造 `value` 和 `model_dictText` / `model_dictTextPrint`。**不要**把人员/部门写成字符串。

> ⚠️ **所有键必须是字段 model（`fields[中文名]['model']`），禁止拿中文字段名当键**（2026-09-11 仁和医院「科室信息」实踩：10 条记录 `科室名称`/`科室类型`/`楼层`/`床位数` 整表显示空）。`add_data` / `edit_data` 传 `{"科室名称": "检验科"}` 服务端**原样入库、不报错**，`list_data` / `desformDataJson` 里也**看得到值**，但界面按 model 读 → 该列**整列显示空**；同一表单里走了 model 的字段（如 `select_user_*`）却正常，**极易误判成「数据没灌进去」**。⇒ 灌数后抽样回读**必须按 model 键核对**，只数行数会漏（本次就是只数了行数）。已入库的中文键记录可 `edit_data` **原地**按 model 键改写修复（保 record id，不破坏他表关联）。

界面 `POST /desform/data/add` 还会带 `desformId`、`desformVersion`；Python `add_data` 只传 `desformCode` + `desformDataJson` 即可。

> ⚠️ **API 写入同样触发简流**：`add_data` 对绑定了「新增触发」流程（startEventType=add）的工作表插入记录，会正常起流程实例生成待办（2026-09-03 实测）——造测试数据属预期行为，不是 bug。
> ⚠️ **date 落库格式判定**：date 控件是存毫秒时间戳还是 `"yyyy-MM-dd"` 字符串，用 `GET /desform/api/fields/{code}` 里该控件 `options.timestamp` 判定：`true` → 毫秒 + `_dictText`；否则直接存日期字符串。年-月/年-季度/年-周等周期档位（`options.type`=month/quarter/week）存周期起始时间戳、界面格式化的通用规则见 `desform-widget-options.md`「date」。

### 控件落库格式（对齐 vue-form-making-jeecg + 学生表实测）

> ⚠️ 本表是**数据落库**格式；**条件值**形态不同（单值串/多值逗号串），见 `desform-filter-rules.md`「条件值形态实测」。

源码：`JSelectUsers.emitValue` / `JSelectDepart.handleOK` / `JSelectRoles.emitValue` 里 `.join(',')` 已注释，**单选也存数组**。展示文案写入 `models[model+'_dictText']`。关联记录另写 `model_dictTextPrint`（`JLinkRecord.emitDictTextPrint`，标题用 `", "` 拼接）。子表行内字段规则与主表相同。

#### 1. 必须写成数组（即使 `multiple: false`）+ `_dictText`

| 控件 | 存值 | `_dictText`（多人用英文逗号、无空格） |
|------|------|-------------|
| `select-user` | `["username"]` | `"前端3号"` / `"前端3号,前端2号"`。空选 `[]` + `""` |
| `select-depart` | `["部门id"]` | `"互动云"`。空选 `[]` + `""` |
| `select-depart-post` | `["岗位id"]` | 岗位名。空选 `[]` + `""` |
| `org-role` | `["roleCode"]` | `"斗尊"` / `"斗皇,斗宗,斗尊"` |

#### 2. 必须写展示文案的标量 / 特殊 key

| 控件 | 存值 | 展示字段 |
|------|------|----------|
| `date`（`timestamp: true`） | 毫秒时间戳，如 `1788192000000` | `_dictText`=`"2026-09-01"`；空日期存 `""` |
| `area-linkage` | **最后一级**区划码 `"120101"` | `_dictText`=`"天津市/天津市/和平区"`（level 1/2/3 见下） |
| `category-linkage` | 路径数组 | `_dictText` 各级 label 用 `/` 拼接 |
| `money` | 数字 `12` | `_dictText`=`"12元"`（默认 unitText=元，实测必带） |
| `link-record` | id 的 list（单条也是数组） | **`_dictTextPrint`**=`"韩老师, 沈老师"`（逗号+空格）。仅当该字段是表单 titleField 且单条时才额外写 `_dictText` |
| `link-field` | 来源字段原值（`saveType=save`） | 来源有展示文案时写 `_dictText` |

```python
data[fields['老师']['model']] = ['2094703165858418689']
data[fields['老师']['model'] + '_dictTextPrint'] = '韩老师'
```

#### 3. radio / select / checkbox

- `radio`、`select` 非多选：**字符串**，不是数组
- `checkbox`、`select` 多选：**字符串数组**（只选一项也是 `["2"]`）
- `showLabel` 或字典（value≠文案）时必须写 `_dictText`：`"2"` → `"高中"`
- 静态选项 value 即文案（`"男"`、`"下拉框2"`）可以不写 `_dictText`

#### 4. 其余类型（无 `_dictText`，除非上表已列）

| 控件 | 存值 |
|------|------|
| `input` / `textarea` / `phone` / `email` / `markdown` | 字符串 |
| `editor` | HTML，如 `"<p>我是编辑器</p>"` |
| `time` | `"19:38:30"` |
| `number` / `integer` / `rate` / `slider` / `formula` / `summary` | 数字 |
| `switch` | `"Y"` / `"N"` |
| `color` | 色值字符串，空为 `""` |
| `capital-money` | `"壹拾贰元整"` |
| `text-compose` | 组合后的字符串 |
| `hand-sign` | `"signature_xxx.png"` |
| `imgupload` | `[{"key":…,"url":"文件名","percent":100,"status":"success"}]` |
| `file-upload` | `[{"uid":…,"size":…,"name":"原名.png","url":"存盘名.png","percent":100,"percentage":100,"status":"success","updateTime":"…","updateBy":"廖志阳"}]` |
| `sub-table-design` | 行对象数组，**行内字段同样按本表规则** |
| `auto-number` | `add` 时系统重新生成会覆盖手写值；需固定编号 → add 后用 `edit_data` 覆盖（编辑不重算） |

系统字段 `create_by` / `create_time` / `bpm_status` 等由后端写入，**add_data 不要传**。

area-linkage 只存最后一级：`1`=`"110000"` / `2`=`"110100"` / `3`=`"120101"`。

formula：`add` 时后端按表达式自动计算；`edit_data` 全量覆盖**不重算**，需把计算值一并传入。capital-money：API `add` 未自动生成，需手写大写串。

---

## get_data

```python
get_data(code, data_id) -> dict | None
# 查询单条数据
#
# Returns:
#   数据记录 dict，含 id 和各字段值；不存在时返回 None
#
# 示例：
record = get_data('my_form', '1234567890')
```

---

## list_data

```python
list_data(code, page=1, size=10, super_query=None,
          sort_column=None, sort_order=None) -> dict
# 分页查询数据列表
#
# Args:
#   code:        表单编码
#   page:        页码（从 1 开始）
#   size:        每页数量
#   super_query: 高级查询 JSON 字符串（见下方格式）
#   sort_column: 排序字段 model（如 'create_time'）
#   sort_order:  排序方向，'asc' 或 'desc'
#
# Returns:
#   {'records': [{'id': '...', 'desformData': {字段数据}}, ...], 'total': int}
#   ⚠️ 字段数据在 desformData 内，不在记录顶层

# 示例：查询全部（分批）
page = 1
all_records = []
while True:
    result = list_data('my_form', page=page, size=100)
    all_records.extend(result['records'])
    if len(all_records) >= result['total']:
        break
    page += 1
```

### super_query 格式

```python
import json, urllib.parse

# 单条件
sq = json.dumps({
    "matchType": "and",
    "conditionsGroup": [
        {
            "matchType": "and",
            "showPop": False,
            "queryItems": [
                {"field": "select_xxx", "rule": "eq", "val": "待审核",
                 "type": "select", "name": "状态", "valText": ""}
            ]
        }
    ]
})
result = list_data('my_form', super_query=sq)
```

> `rule` 值使用 **小写**（`eq`/`ne`/`like` 等），详见 `desform-filter-rules.md`。
>
> ⚠️ 2026-09-10 实测：`list_data(..., super_query=sq)` 的过滤**不生效**——传 `conditionsGroup` 或 `superQueryGroup` 形态均返回全量（函数只把 JSON 单次编码进 `superQuery` 参数，服务端对单次编码静默忽略）。要按条件实过滤：直接 GET `/desform/data/list`（params：`desformCode`/`pageNo`/`pageSize`/`superQuery`），`superQuery` 值先 `urllib.parse.quote(json.dumps({...}))` 再传，见 `desform-super-query.md`「应用到数据查询」。

---

## edit_data

```python
edit_data(code, data_id, data_dict) -> dict
# 编辑一条数据
#
# ⚠️ 全量覆盖：data_dict 替换整条记录，未传入的字段值将被清空
# ⚠️ 只更新部分字段时，必须先取出原数据再合并修改：
#
# 正确写法：
result = list_data('my_form', size=100)
for r in result['records']:
    data = dict(r['desformData'])      # ✅ 取 desformData，不是整个 r
    data[fields['状态']['model']] = '已完成'
    edit_data('my_form', r['id'], data)
```

---

## delete_data

```python
delete_data(code, data_id, hard=False)
# 删除单条数据
#
# hard=False: 逻辑删除（进回收站，可还原）
# hard=True:  物理删除（不可恢复）
```

---

## delete_data_batch

```python
delete_data_batch(code, ids, hard=False)
# 批量删除数据
#
# ids: ID 列表 ['id1', 'id2'] 或逗号分隔字符串 'id1,id2'
# hard: False=逻辑删除 True=物理删除
```

---

## copy_record / copy_records

界面复制（含只复制一条、复制多条）都走 query，**不要 JSON body**：

```
PUT /desform/data/{desformCode}/copyRecords?ids=id1
PUT /desform/data/{desformCode}/copyRecords?ids=id1,id2,id3
```

多条时 `ids` 是 **逗号分隔**。浏览器里逗号会显示成 `%2C`，例如：

`copyRecords?ids=2094752369913925634%2C2094699668387696642`

DevTools「请求载荷」可能把这一串解析成 `{ids: ["…","…"]}`，那只是面板展示，真正发出的是 query 上的逗号分隔字符串。

```python
copy_records('ke_hu_jp04_alvucopy', '2094752369913925634')
copy_records('ke_hu_jp04_alvucopy', 'id1,id2,id3')
copy_records('ke_hu_jp04_alvucopy', ['id1', 'id2', 'id3'])  # 函数 join 成 id1,id2,id3，urlencode 后逗号变为 %2C
```

`copy_record(code, data_id)` 仍调用 `copyRecord?id=`，单条请优先用 `copy_records`（与前端一致）。

实测（学生表复制 `2094752369913925634` → `2094755559891832833`）：
- 标题字段追加 `-复制`（`我是新添加的` → `我是新添加的-复制`）
- `auto-number` 重新生成（`11` → `12`）
- 引用标题的 `text-compose` 随标题重算
- 人员/部门/关联记录数组、`_dictText`、`_dictTextPrint`、附件原样复制（含 unique 手机号）

---

## batch_update

```python
batch_update(code, field, val, id_list) -> dict
# 批量更新指定字段的值（将多条记录的同一字段设为相同值）
#
# Args:
#   code:    表单编码
#   field:   字段 model
#   val:     新值
#   id_list: 要更新的 ID 列表
#
# 示例：将多条记录的状态改为"已完成"
batch_update('my_form', fields['状态']['model'], '已完成',
             ['id1', 'id2', 'id3'])
```

---

## restore_data

```python
restore_data(code, ids)
# 从回收站还原数据
#
# ids: ID 列表或逗号分隔字符串
```

---

## clear_recycle

```python
clear_recycle(code)
# 清空表单回收站（物理删除所有已逻辑删除的记录，不可恢复）
```

---

## check_unique

```python
check_unique(code, field_model, field_value, exclude_id=None) -> bool
# 检查字段值唯一性
#
# Returns:
#   True = 唯一（无重复），False = 存在重复
#
# exclude_id: 编辑时排除自身 ID，避免与自身比较
#
# 示例：
is_unique = check_unique('my_form', fields['工号']['model'], 'EMP001',
                          exclude_id='current_record_id')
```

---

## get_statistical

```python
get_statistical(code, operation_type, field, super_query=None) -> any
# 聚合统计查询
#
# Args:
#   operation_type: 'count' | 'max' | 'min' | 'avg' | 'sum'
#   field:          统计字段 model
#   super_query:    筛选条件（JSON 字符串，格式同 list_data 的 super_query）
#
# 示例：统计全部记录数
total = get_statistical('my_form', 'count', fields['姓名']['model'])

# 示例：统计"已完成"状态下的金额总计
sq = json.dumps({
    "matchType": "and",
    "conditionsGroup": [{
        "matchType": "and", "showPop": False,
        "queryItems": [{"field": fields['状态']['model'], "rule": "eq",
                        "val": "已完成", "type": "select", "valText": ""}]
    }]
})
total_amount = get_statistical('my_form', 'sum', fields['金额']['model'], super_query=sq)
```
