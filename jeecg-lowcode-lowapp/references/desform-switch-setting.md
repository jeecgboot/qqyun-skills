# 功能开关（零代码应用专属）

**仅适用于零代码应用（isLowApp=true）的工作表。** 普通表单设计器中没有此选项。

操作前必须通过 `init_lowapp` 初始化（普通 `init_api` 不携带 `x-low-app-id` header，调用会失败）。详见 `references/desform-lowapp.md`。

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/desform/setting/getAllSetting?desformCode={code}` | 查询全部功能开关配置 |
| `POST` | `/desform/setting/saveBatch` | 批量保存配置（传对象数组） |

---

## 单条配置数据结构

```json
{
  "_id": null,
  "code": "SHOW_CREATE_BTN",
  "desformCode": "school_student",
  "enabled": true,
  "userAuth": 1,
  "viewAuth": 1,
  "viewIds": [],
  "createBy": null,
  "createTime": "2026-04-10 18:27:58",
  "updateBy": null,
  "updateTime": null
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `_id` | string \| null | 数据库主键（通常为 null，后端按 `desformCode+code` upsert） |
| `code` | string | 功能标识（全大写，见下方速查表） |
| `desformCode` | string | 工作表编码 |
| `enabled` | boolean | 是否启用（`hideSwitch=true` 的项此字段无实际效果） |
| `userAuth` | number | `1`=所有用户，`2`=仅管理员 |
| `viewAuth` | number | `1`=所有视图，`2`=指定视图（`hideViewRole=true` 的项无此字段） |
| `viewIds` | string[] | `viewAuth=2` 时生效，填视图 ID（非视图名称）；**不能为空数组** |

**关键：后端以 `desformCode + code` 为唯一键做 upsert**，`_id=null` 时也能正常保存。因此可以直接构造对象而无需先查询现有配置。

---

## 全量 code 速查表

### 工作表

| code | 显示名称 | 说明 | hideSwitch | hideRole | hideViewRole |
|------|---------|------|-----------|---------|-------------|
| `SHOW_CREATE_BTN` | 显示创建按钮 | 关闭后无法在工作表中直接创建记录，只能通过关联记录等方式创建 | — | ✓ | — |
| `IMPORT_DATA` | 导入 | 控制数据导入功能 | ✓ | — | ✓ |

> `hideSwitch=✓`：该项没有启用/禁用开关，只能配置使用范围（`enabled` 字段无意义）  
> `hideRole=✓`：该项没有使用范围配置  
> `hideViewRole=✓`：该项只有用户范围，没有视图范围（`viewAuth`/`viewIds` 无意义）

### 视图

| code | 显示名称 | 说明 | hideSwitch | hideRole | hideViewRole | 备注 |
|------|---------|------|-----------|---------|-------------|------|
| `VIEW_EXPORT` | 视图导出 | 批量操作中的导出功能需额外设置 | — | — | — | — |
| `BATCH_ACTION` | 批量操作 | **父级**，控制所有批量子功能 | — | ✓ | — | 见父子联动规则 |
| `BATCH_EDIT` | 编辑 | 批量编辑记录 | — | — | — | BATCH_ACTION 子级 |
| `BATCH_EXPORT` | 导出 | 批量导出记录 | — | — | — | BATCH_ACTION 子级 |
| `BATCH_REMOVE` | 删除 | 批量删除记录 | — | — | — | BATCH_ACTION 子级 |
| `BATCH_CUSTOM_BUTTON` | 执行自定义按钮 | 批量执行自定义按钮 | — | — | — | BATCH_ACTION 子级 |
| `BATCH_SYS_PRINT` | 系统默认打印 | ⚠️ **已被前端屏蔽**，API 仍可操作，建议不配置 | — | — | — | BATCH_ACTION 子级 |

### 记录

| code | 显示名称 | 说明 | hideSwitch | hideRole | hideViewRole |
|------|---------|------|-----------|---------|-------------|
| `RECORD_SHARE` | 记录分享 | — | — | — | — |
| `RECORD_COMMENT` | 记录讨论 | — | — | — | — |
| `RECORD_SYS_PRINT` | 系统默认打印 | 仅控制系统默认打印方式，不包含打印模板 | — | — | — |
| `FILES_DOWNLOAD` | 附件下载 | 控制附件的下载、分享、保存到知识（不含用户自行上传的附件） | — | — | — |
| `RECORD_LOGS` | 记录日志 | — | ✓ | — | — |

---

## 父子联动规则

`BATCH_ACTION` 是父级，其子级为：`BATCH_EDIT`、`BATCH_SYS_PRINT`、`BATCH_EXPORT`、`BATCH_REMOVE`、`BATCH_CUSTOM_BUTTON`

**规则（前端行为，AI 需手动实现）：**

1. **父级 enabled 变更时** → 所有子级继承相同的 `enabled` 值  
   → `saveBatch` 需同时包含父级和所有子级

2. **最后一个子级被禁用时** → 父级自动禁用  
   → 例：5 个子级中只有 1 个启用，现在将其禁用，则父级 `enabled` 也变为 `false`  
   → `saveBatch` 需同时包含该子级和父级

**AI 操作原则：** 修改 `BATCH_ACTION` 相关开关时，先用 `get_switch_settings` 查出所有当前配置，根据规则调整好完整列表后，一次性 `save_switch_settings` 提交。

---

## viewAuth 约束

- `viewAuth=2` 时，`viewIds` **不得为空**（前端会阻止保存并提示「请至少选中一个视图！」）
- `viewAuth` 从 2 切换为 1 时，`viewIds` 自动清空（传 `[]` 即可）
- 视图 ID 来源：`query_list_views(code)` 返回的每项的 `id` 字段

```python
from desform_utils import query_list_views
views = query_list_views('my_form')
# [{'id': '...', 'name': '默认视图', 'type': 'table'}, ...]
```

---

## Python 操作示例

```python
import sys
sys.path.insert(0, r'<skill目录>/scripts')
from desform_lowapp_utils import init_lowapp, get_switch_settings, save_switch_settings

init_lowapp('<api_base>', '<token>', tenant_id=<tenant_id>, app_id='<app_id>')

# ── 方式一：直接构造（已知目标状态时推荐）──────────────────────
# 后端按 desformCode+code upsert，无需先查，_id=null 也能保存

# 禁用「显示创建按钮」
save_switch_settings('my_form', [{
    '_id': None, 'code': 'SHOW_CREATE_BTN', 'desformCode': 'my_form',
    'enabled': False, 'userAuth': 1, 'viewAuth': 1, 'viewIds': [],
    'createBy': None, 'createTime': None, 'updateBy': None, 'updateTime': None,
}])

# 禁用批量操作（父级+所有子级，需一起发送）
batch_codes = ['BATCH_ACTION', 'BATCH_EDIT', 'BATCH_EXPORT', 'BATCH_REMOVE', 'BATCH_CUSTOM_BUTTON']
save_switch_settings('my_form', [
    {'_id': None, 'code': c, 'desformCode': 'my_form',
     'enabled': False, 'userAuth': 1, 'viewAuth': 1, 'viewIds': [],
     'createBy': None, 'createTime': None, 'updateBy': None, 'updateTime': None}
    for c in batch_codes
])

# ── 方式二：查询后修改（需保留当前其他配置时使用）─────────────
settings = get_switch_settings('my_form')

# 将「视图导出」限制为仅管理员、指定视图
from desform_utils import query_list_views
views = query_list_views('my_form')
view_id = views[0]['id']  # 取第一个视图 ID

export_item = next(s for s in settings if s['code'] == 'VIEW_EXPORT')
export_item['userAuth'] = 2   # 仅管理员
export_item['viewAuth'] = 2   # 指定视图
export_item['viewIds'] = [view_id]
save_switch_settings('my_form', [export_item])
```

---

## 注意事项

- `BATCH_SYS_PRINT` 已被前端屏蔽，前端不显示此项，建议不主动配置
- `IMPORT_DATA` 和 `RECORD_LOGS` 没有启用/禁用开关，`enabled` 字段写入无效果，只能配置 `userAuth`/`viewAuth`
- `saveBatch` 每项需包含 `_id`（可为 null）、`desformCode`、`code`、`enabled`、`userAuth`、`viewAuth`、`viewIds`，以及 `createBy/createTime/updateBy/updateTime`（可均为 null）；后端按 `desformCode+code` upsert，直接构造或查询后修改均可
- 功能开关配置不受 `update_design_config` 管理，两者是独立系统
