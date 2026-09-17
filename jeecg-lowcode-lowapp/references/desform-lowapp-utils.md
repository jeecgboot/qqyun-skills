# desform_lowapp_utils.py 使用指南

`scripts/desform_lowapp_utils.py` 封装了 JeecgBoot lowApp 模式下的所有专属 API。

## 导入方式

```python
import sys
sys.path.insert(0, r'<skill目录>/scripts')
from desform_lowapp_utils import (
    init_lowapp, set_app,
    get_tenants,
    get_apps, create_app, edit_app, copy_app, star_app, delete_app,
    get_app_groups, create_app_group, add_app_to_group, edit_app_group,
    star_app_group, delete_app_group,
    get_menus, get_worksheet_groups,
    edit_worksheet, sort_worksheets, delete_worksheet,
    create_worksheet_group, edit_worksheet_group,
    move_worksheet_to_group, delete_worksheet_group,
)
```

---

## 初始化

### `init_lowapp(api_base, token, tenant_id, app_id=None)`

初始化 lowApp 上下文，替代 `desform_utils.init_api`。

调用后，`desform_utils` 中所有函数（`create_form`、`add_widget` 等）自动携带 `x-tenant-id` 和 `x-low-app-id` header。

| 参数 | 类型 | 说明 |
|------|------|------|
| `api_base` | str | JeecgBoot 后端地址 |
| `token` | str | X-Access-Token |
| `tenant_id` | int | 组织（租户）ID |
| `app_id` | str \| None | 应用 ID（操作应用内工作表时必填） |

```python
init_lowapp('<api_base>', '<token>', tenant_id=<tenant_id>,
            app_id='<app_id>')
```

---

### `set_app(app_id)`

切换当前操作的应用，不重新初始化连接。

```python
set_app('<app_id>')  # 切换到另一个应用
set_app(None)                   # 清空应用上下文（退出 lowApp 模式）
```

---

## 组织（租户）

### `get_tenants()`

查询当前登录用户所属的所有组织。

**返回：** `list[dict]`，每项包含 `{id, name, status}`

```python
tenants = get_tenants()
# [{'id': 2, 'name': '北京国炬信息技术有限公司', 'status': 1}, ...]
```

---

## 应用管理

### `get_apps(tenant_id=None)`

查询组织下的所有应用。`tenant_id` 不传则使用 `init_lowapp` 设置的当前租户。

空组织实测 `appList`/`groupList` 可能为 `null`（不是 `[]`），函数已归一成空列表。

**返回：**
```python
{
    'apps': [
        {'id': '2011...', 'appName': '未命名应用', 'iconType': '...', 
         'iconBackColor': 'rgb(0, 188, 212)', 'appCoverImg': 'coverImage002',
         'orderNum': 1, 'createTime': '2026-01-15', 'starStatus': 0, ...}
    ],
    'groups': [
        {'id': '...', 'groupName': '测试分组', 'orderNum': None, 'useScope': 'self', ...}
    ],
    'relations': [
        {'id': '...', 'groupId': '...', 'appId': '...', 'orderNum': None}
    ]
}
```

---

### `create_app(tenant_id=None, app_name='未命名应用', icon_type=..., icon_back_color=..., app_cover_img=None)`

创建应用。`app_cover_img` 不传时随机选择 `coverImage001` ~ `coverImage012` 中的一张。

**返回：** `str`，新应用 ID

```python
app_id = create_app(tenant_id=<tenant_id>, app_name='销售管理')
# '[lowApp] 应用创建成功: 销售管理 (ID=2042...)'
```

---

### `edit_app(app_id, app_name=None, icon_type=None, icon_back_color=None, app_cover_img=None)`

修改应用信息，只传需要修改的字段。

**返回：** `bool`

```python
edit_app('2042...', app_name='销售管理v2', icon_back_color='rgb(76, 175, 80)')
```

---

### `copy_app(app_id, target_tenant_id=None)`

复制应用到目标租户。`target_tenant_id` 不传则复制到当前租户。

**返回：** `str`，新应用 ID

```python
new_id = copy_app('<app_id>', target_tenant_id=<tenant_id>)
```

---

### `star_app(app_id, star=True)`

标星或取消标星应用。

```python
star_app('2042...', star=True)   # 标星
star_app('2042...', star=False)  # 取消
```

---

### `delete_app(app_id)`

**⚠️ 危险操作**：删除应用及其所有工作表、配置和数据，不可恢复。执行前必须向用户二次确认。

**返回：** `bool`

---

## 应用分组（组织级别）

### `get_app_groups(tenant_id=None)`

查询组织下的应用分组列表（实际是从 `get_apps` 的 `groupList` 中提取）。

**返回：** `list[dict]`，每项包含 `{id, groupName, orderNum, iconType, useScope, ...}`

---

### `create_app_group(tenant_id=None, group_name='未命名分组', use_scope='self', icon_type=...)`

创建应用分组。

**返回：** 新分组信息 dict（含 id）

```python
group = create_app_group(tenant_id=<tenant_id>, group_name='生产系统')
```

---

### `add_app_to_group(group_id, app_id)`

将应用加入分组。

```python
add_app_to_group('2042511177...', '2042510891...')
```

---

### `edit_app_group(group_id, group_name=None, star_status=None, icon_type=None, use_scope=None)`

修改应用分组，只传需要修改的字段。

---

### `star_app_group(group_id, star=True)`

标星或取消标星应用分组。

---

### `delete_app_group(group_id)`

删除应用分组。**注意：仅删除分组本身，分组下的应用不受影响。**

---

## 工作表菜单管理（应用内）

### `get_menus(app_id=None)`

查询应用内所有菜单（工作表 + 工作表分组）。

**返回：**
```python
{
    'hasAdmin': True,  # 当前用户是否为该应用管理员
    'menuList': [
        {
            'id': '2042516351720214529',   # ⚠️ menu_id（菜单操作用此ID）
            'menuName': 'aaa',
            'type': 'form',                # 'form'=工作表, 'group'=分组
            'parentId': '2042516716...',   # 所属工作表分组ID
            'desformCode': 'aaa_ouz5',     # 表单编码（设计操作用此值）
            'menuUrl': '2042516351590...',  # 表单ID（= desform 的 id）
            'orderNum': 1,
            ...
        },
        {
            'id': '2042516716536582146',
            'menuName': '未命名分组',
            'type': 'group',
            'desformCode': None,
            ...
        }
    ]
}
```

---

### `get_worksheet_groups(app_id=None)`

**语法糖**：只返回分组（`type='group'`）的简化信息，按 `orderNum` 排序。

创建工作表前调用，判断是否有分组、有哪些分组可选。

**返回：**
```python
{
    'count': 2,  # 分组数量（0=无分组）
    'groups': [
        {'id': '2042516716536582146', 'menuName': '未命名分组', 'orderNum': 1},
        {'id': '2042516751638712321', 'menuName': '业务分组', 'orderNum': 2},
    ]
}
```

```python
groups = get_worksheet_groups()
if groups['count'] == 0:
    # 无分组，工作表直接创建
    group_id = None
else:
    # 默认用第一个分组
    group_id = groups['groups'][0]['id']
```

---

### `edit_worksheet(menu_id, menu_name=None, icon_type=None)`

修改工作表的名称或图标。

**⚠️ 参数是 menu_id（`get_menus().menuList[].id`），不是 desformCode 或 desform_id**

```python
edit_worksheet('2042516351720214529', menu_name='客户信息', icon_type='ant-design:user-outlined')
```

---

### `sort_worksheets(order_info)`

重排应用内工作表顺序。必须包含**所有**工作表（不含分组）。

```python
sort_worksheets([
    {'id': '2042516351720214529', 'orderNum': 1},
    {'id': '2042515145719402497', 'orderNum': 2},
    {'id': '2042516438139654145', 'orderNum': 3},
])
```

---

### `delete_worksheet(menu_id)`

**⚠️ 危险操作**：删除工作表及其所有配置和数据，不可恢复。执行前必须向用户二次确认。

**⚠️ 参数是 menu_id，不是 desformCode 或 desform_id**

```python
delete_worksheet('2042516351720214529')
```

---

## 工作表分组管理（应用内）

### `create_worksheet_group(app_id=None, group_name='未命名分组')`

**语法糖**：创建工作表分组，自动判断首次/追加场景。

| 情况 | 内部行为 |
|------|---------|
| 应用内当前无分组（首次） | 调用 `createFirstGroup`：已有工作表全部迁移进新分组 |
| 应用内已有分组 | 调用 `createGroup`：只新增分组，已有工作表不受影响 |

**返回：** `str`，新分组 ID

```python
group_id = create_worksheet_group(group_name='客户管理')
# 之后创建工作表时使用：
create_form('客户信息', 'customer_info', widgets, app_menu_group_id=group_id)
```

---

### `edit_worksheet_group(group_id, group_name)`

修改工作表分组名称。

```python
edit_worksheet_group('2042516716536582146', '新分组名称')
```

---

### `move_worksheet_to_group(menu_id, parent_group_id, app_id=None)`

将工作表移动到指定分组。

```python
move_worksheet_to_group(
    menu_id='2042516351720214529',
    parent_group_id='2042516716536582146'
)
```

---

### `delete_worksheet_group(group_id, move_to_group_id=None)`

删除工作表分组。工作表不会被删。

`DELETE /online/lowAppMenu/deleteGroup?deleteId={group_id}&groupId={move_to_group_id}`

| 场景 | 做法 |
|------|------|
| 该分组下**有工作表**，且应用内**还有其他分组** | **禁止直接删**。列出工作表和其他分组，等用户选定迁入目标后，再传 `move_to_group_id` |
| 该分组下没有工作表，或已经是最后一个分组 | 只传 `group_id`，可直接删除 |

```python
# 空分组 / 最后一个分组
delete_worksheet_group('2094733397353074690')

# 有工作表且还有其他分组：用户选定迁入「工资条」后
delete_worksheet_group('2094733397353074690', move_to_group_id='2094733397759922177')
```

未传 `move_to_group_id` 却仍有工作表和其他分组时，函数会 `ValueError` 并带上可选分组列表。

---

## 功能开关（零代码应用专属）

### `get_switch_settings(desform_code)`

查询工作表的所有功能开关配置。需提前调用 `init_lowapp`。

**返回：** `list[dict]`，每项含 `{id, desformId, code, enabled, userAuth, viewAuth, viewIds}`

```python
settings = get_switch_settings('my_form')
# [{'id': '...', 'code': 'SHOW_CREATE_BTN', 'enabled': True, 'userAuth': 1, 'viewAuth': 1, 'viewIds': []}, ...]
```

---

### `save_switch_settings(desform_code, settings_list)`

批量保存功能开关配置。`settings_list` 直接传 `get_switch_settings` 返回的原始对象（修改后传入），不要手动构造缺少 `id`/`desformId` 的对象。

**父子联动规则（需手动处理）：**
- `BATCH_ACTION` 是父级，子级为 `BATCH_EDIT`/`BATCH_EXPORT`/`BATCH_REMOVE`/`BATCH_CUSTOM_BUTTON`
- 父级 `enabled` 变更时，需同时传入所有子级
- 最后一个子级禁用时，需同时传入父级（`enabled=False`）

详见 `references/desform-switch-setting.md`。

```python
# 直接构造（后端按 desformCode+code upsert，_id=null 也能保存）
save_switch_settings('my_form', [{
    '_id': None, 'code': 'SHOW_CREATE_BTN', 'desformCode': 'my_form',
    'enabled': False, 'userAuth': 1, 'viewAuth': 1, 'viewIds': [],
    'createBy': None, 'createTime': None, 'updateBy': None, 'updateTime': None,
}])

# 查询后修改（需保留当前其他配置时使用）
settings = get_switch_settings('my_form')
target = next(s for s in settings if s['code'] == 'SHOW_CREATE_BTN')
target['enabled'] = False
save_switch_settings('my_form', [target])
```
