# lowApp 模式（敲敲云 / 零代码模式）

> 当用户提及「应用」「工作表」「敲敲云」「零代码」「lowApp」时，必须先阅读本文档，再执行任何操作。

---

## 概念说明

**lowApp 模式**（又称「敲敲云模式」「零代码模式」）是 JeecgBoot 中以「应用」为单位组织表单的零代码平台。

| lowApp 概念 | 对应普通模式 |
|------------|------------|
| 工作表 | 设计器表单（desform） |
| 应用 | 无对应概念 |
| 组织（租户） | 系统租户（tenantId） |

**层级体系：**

```
组织（租户）
  └── 应用分组（对应用归类，可选）
  └── 应用
        └── 工作表分组（对工作表归类，可选）
        └── 工作表（= 设计器表单）
```

**关键认知：**
- 「工作表」就是设计器表单，创建工作表 = 创建设计器表单，只是多了应用上下文
- 所有工作表相关操作（字段设计、视图、业务规则等）与普通模式完全相同，只需提前通过 `init_lowapp` 注入上下文
- 工作表有两个 ID：`menu_id`（菜单系统的 ID）和 `desform_id`（表单自身 ID）——操作菜单（改名、排序、删除）用 `menu_id`，操作表单内容（字段、数据）用 `desform_id` 或 `desformCode`

---

## 初始化

所有操作前，必须通过 `init_lowapp` 设置组织和应用上下文：

```python
import sys
sys.path.insert(0, r'<skill目录>/scripts')
from desform_lowapp_utils import init_lowapp

init_lowapp(
    api_base='<api_base>',
    token='<token>',
    tenant_id=<tenant_id>,
    app_id='<app_id>'  # 操作具体应用时必填
)
```

**初始化后**，`desform_utils` 中所有表单操作函数（`create_form`、`add_widget`、`update_widget` 等）会自动携带 `x-tenant-id` 和 `x-low-app-id` header，无需任何额外改动。

**切换应用（不重新初始化）：**

```python
from desform_lowapp_utils import set_app
set_app('<app_id>')  # 切换到另一个应用
```

---

## 操作前置流程

用户已给出**应用名**或**工作表名**时：不要停下来只问组织。遍历 `get_tenants()` → 各租户 `get_apps()` → 匹配应用的 `get_menus()`，按名称**精确匹配**：

- 唯一命中 → 直接 `init_lowapp(api_base, token, tenant_id, app_id)`
- 0 条 → 告知找不到
- 多条（如同名应用在多个组织）→ 列出组织 / 应用 / 工作表让用户选

「录入学生-复制的工作表学生」= 应用名 `录入学生-复制` + 工作表名 `学生`，不是工作表名叫「录入学生-复制」。

### 1. 确认组织

用户未指定组织、也没有可匹配的应用名/工作表名时，查询所有组织，询问用户选择：

```python
from desform_lowapp_utils import get_tenants
tenants = get_tenants()
# 返回：[{'id': 2, 'name': '北京国炬信息技术有限公司', 'status': 1}, ...]
# → 展示给用户，让用户选择
```

### 2. 确认应用

用户未指定应用、且上一步未能按名称定位时，查询组织内所有应用，询问用户选择：

```python
from desform_lowapp_utils import get_apps
data = get_apps(tenant_id=<tenant_id>)
apps = data['apps']  # [{id, appName, ...}]
# → 展示给用户，让用户选择
```

### 3. 初始化上下文

定位到组织和应用后，调用 `init_lowapp` 完成初始化。

---

## 函数速查表

详细说明见 `references/desform-lowapp-utils.md`。

### desform_lowapp_utils.py

**初始化**

| 函数 | 说明 |
|------|------|
| `init_lowapp(api_base, token, tenant_id, app_id=None)` | 初始化 lowApp 上下文（替代 `init_api`） |
| `set_app(app_id)` | 切换当前应用（不重新初始化） |

**组织管理**

| 函数 | 说明 |
|------|------|
| `get_tenants()` | 查询当前用户的所有组织 |

**应用管理**

| 函数 | 说明 |
|------|------|
| `get_apps(tenant_id=None)` | 查询组织下所有应用（含分组和关联） |
| `create_app(tenant_id=None, app_name, ...)` | 创建应用，返回应用ID |
| `edit_app(app_id, app_name=None, ...)` | 修改应用信息 |
| `copy_app(app_id, target_tenant_id=None)` | 复制应用到租户，返回新应用ID |
| `star_app(app_id, star=True)` | 标星/取消标星应用 |
| `delete_app(app_id)` | ⚠️ 删除应用（含所有工作表和数据） |

**应用分组（组织级别）**

| 函数 | 说明 |
|------|------|
| `get_app_groups(tenant_id=None)` | 查询应用分组列表 |
| `create_app_group(tenant_id=None, group_name, ...)` | 创建应用分组 |
| `add_app_to_group(group_id, app_id)` | 将应用加入分组 |
| `edit_app_group(group_id, group_name=None, ...)` | 修改分组 |
| `star_app_group(group_id, star=True)` | 标星分组 |
| `delete_app_group(group_id)` | 删除应用分组（应用不受影响） |

**工作表菜单（应用内）**

| 函数 | 说明 |
|------|------|
| `get_menus(app_id=None)` | 查询应用内所有菜单（工作表+分组） |
| `get_worksheet_groups(app_id=None)` | ⚡ 只查分组（语法糖，返回 `{count, groups}`） |
| `edit_worksheet(menu_id, menu_name=None, icon_type=None)` | 修改工作表名称/图标 |
| `sort_worksheets(order_info)` | 重排工作表顺序 |
| `delete_worksheet(menu_id)` | ⚠️ 删除工作表（含所有数据） |

**工作表分组（应用内）**

| 函数 | 说明 |
|------|------|
| `create_worksheet_group(app_id=None, group_name)` | ⚡ 创建分组（自动判断首次/追加） |
| `edit_worksheet_group(group_id, group_name)` | 改分组名称 |
| `move_worksheet_to_group(menu_id, parent_group_id, app_id=None)` | 移动工作表到分组 |
| `delete_worksheet_group(group_id, move_to_group_id=None)` | 删除分组；有工作表且还有其他分组时必须先问用户迁入目标 |

---

## 在 lowApp 下创建工作表（核心流程）

lowApp 模式下创建工作表与普通创建表单的唯一区别：
1. 需要提前 `init_lowapp`（注入 tenant/app header）
2. 调用 `create_form` 时传入 `app_menu_group_id`（决定工作表放在哪个分组）

### 完整流程

```python
import sys
sys.path.insert(0, r'<skill目录>/scripts')
from desform_lowapp_utils import init_lowapp, get_worksheet_groups
from desform_utils import create_form, INPUT, SELECT, DATE

# 1. 初始化
init_lowapp('<api_base>', TOKEN, tenant_id=<tenant_id>,
            app_id='<app_id>')

# 2. 查询分组，确定工作表放在哪个分组
groups = get_worksheet_groups()  # {'count': 2, 'groups': [{id, menuName, orderNum}]}

# 分组选择逻辑：
# - 无分组（count=0）：app_menu_group_id=None 或先创建分组
# - 有分组且用户未指定：默认使用第一个分组
# - 有分组且用户指定：使用用户指定的分组
group_id = groups['groups'][0]['id'] if groups['count'] > 0 else None

# 3. 创建工作表（与普通 create_form 完全相同，多一个 app_menu_group_id 参数）
widgets = [
    INPUT('客户名称', required=True),
    SELECT('客户类型', options=['企业', '个人']),
    DATE('创建日期'),
]
form_id, title_model = create_form(
    '客户信息', 'customer_info', widgets,
    app_menu_group_id=group_id
)
```

### 分组处理规则

| 场景 | 处理方式 |
|------|---------|
| 应用无分组，用户未要求分组 | `app_menu_group_id=None`（不传分组，工作表直接创建） |
| 应用无分组，用户要求分组 | 先 `create_worksheet_group()` 创建分组，再创建工作表 |
| 有分组，用户未指定 | 默认使用 `get_worksheet_groups()` 返回的第一个分组 |
| 有分组，用户指定了分组名 | 从 `get_worksheet_groups()` 中匹配 `menuName`，取对应 `id` |

---

## ⚠️ 关键注意事项

### 1. menu_id 与 desform_id 的区分

工作表有两个 ID，**绝对不能混用**：

| ID 类型 | 来源 | 用于 |
|--------|------|------|
| `menu_id` | `get_menus().menuList[].id` | 改名(`edit_worksheet`)、排序(`sort_worksheets`)、删除(`delete_worksheet`)、移动(`move_worksheet_to_group`) |
| `desform_id` | `get_menus().menuList[].menuUrl` | 表单字段操作（`update_widget`、`add_widget` 等）、数据 CRUD |
| `desformCode` | `get_menus().menuList[].desformCode` | 表单设计操作（推荐用此而非 desform_id） |

### 2. delete_worksheet 的危险性

`delete_worksheet(menu_id)` 会级联删除该工作表的**所有字段设计、视图配置和业务数据**，执行前务必向用户二次确认。

### 2.1 删除工作表分组

`DELETE /online/lowAppMenu/deleteGroup?deleteId={要删的分组}&groupId={迁入目标}`。

删分组前先 `get_menus()`：看该分组下有无工作表（`type=form` 且 `parentId` 等于该分组 id），以及是否还有其他分组。

- **有工作表 + 还有其他分组**：不能直接删。列出工作表和可选目标分组，等用户选定迁入哪一组，再 `delete_worksheet_group(deleteId, move_to_group_id=目标id)`。
- **没有工作表，或已经是最后一个分组**：`delete_worksheet_group(deleteId)` 可直接删。

不要先逐张 `move_worksheet_to_group` 再删；迁入由 `deleteGroup` 的 `groupId` 一次完成。

### 2.2 隐藏工作表菜单（导航不显示）

`PUT /online/lowAppMenu/edit`，body `{"id": <菜单记录id>, "hideFlag": 1}`（`menuList[].id` 见 `2.1`；`hideFlag`：`1`=隐藏、`None`=显示）。

- **隐藏 = 设 `hideFlag`**，不是 `move_worksheet_to_group(menu_id, None)`（移出分组 ≠ 隐藏机制）。
- ⚠️ 该接口对任何输入都返回「编辑成功!」（空 body 也成功），**必须回读 `get_menus()` 确认 `hideFlag==1`**。

### 3. 封面图可选值

`create_app` 和 `edit_app` 的 `app_cover_img` 参数只允许 `coverImage001` ~ `coverImage012`，共 12 个值。不传时随机选取。

### 4. 应用分组 vs 工作表分组

这是两个独立的分组体系，不要混淆：

| | 应用分组 | 工作表分组 |
|-|---------|----------|
| 作用范围 | 组织级别，对多个应用归类 | 应用内，对工作表归类 |
| API 前缀 | `/online/lowAppGroup/` | `/online/lowAppMenu/` |
| 函数前缀 | `_app_group` | `_worksheet_group` |

### 5. 敲敲云设计器禁用的控件与功能（源码 Container.vue / WidgetConfig.vue）

同一套 `vue-form-making-jeecg` 嵌套到普通 Vue 表单设计器和敲敲云。`isLowApp=true` 时左侧面板和属性面板会隐藏一批能力，**本 skill 禁止生成它们**。

**禁用控件（禁止新建）：**

| 控件 | 原因 |
|------|------|
| `table-dict` 表字典 | QQYUN-3641，关联分组不展示 |
| `select-tree` 下拉树 | 同上 |
| `cascader` 级联选择器 | 源码已注释隐藏 |
| `category-linkage` 联动 | 本 skill 屏蔽，禁止新建 |
| 全部 OA 字段 | OA 分组 `v-if="!isLowApp"`：`oa-approval-comments`、`x_oa_timeout_date`、`x_oa_official_doc_no`、`oa-sign-holiday-select`、`oa-leave-date-select`、`oa-sign-patch-select` |

**敲敲云属性面板不展示（不要配）：**

- `fillRuleCode` 填值规则（input/textarea）
- `remoteAPI` 远程取值
- 选人/选部门的「自定义返回字段」「数据绑定映射 keyMaps」
- Online 表单绑定、自定义接收 URL、JS/CSS 外部增强
- 日期 `daterange` / `dates` / `datetimerange`（仅普通设计器兼容老数据）

**敲敲云可用的新能力：**

- 日期 `year` / `month` / `quarter` / `week`（LHZP-322）
- 单行文本 `allowScan` 扫码（LHZP-1945，APP 端）
- 子表支持 `capital-money` / `text-compose`（LHZP-1984）

---

## ⛔ 角色成员 / 用户租户关系：**不要**用 `PUT /sys/user/edit` 整条回写（2026-09-17 事故）

给角色加成员时，`GET /sys/user/queryById` 读出来的用户 VO 里有个 `relTenantIds` —— 那是**计算字段**
（`sys_user` 表里根本没有这一列）。把这个 VO 原样 `PUT /sys/user/edit` 回写，会**删掉 `sys_user_tenant` 里该用户的所有行**：

- 后果：账号能登录，但**看不到任何租户/应用/菜单**；`/sys/user/*`、`/sys/role/*`、`/sys/tenant/list` 全返 `510 没有权限`，
  token 随后判 `401`。**应用与表单数据都在**（`/desform/list`、`/online/lowApp/queryList` 都读得到），只是该账号的关联被清。
- 恢复：`sys_user_tenant` 补回一行（`id, user_id, tenant_id, status, create_by, create_time`）→ 重新登录即可看到租户；
  角色绑定若同时空了，再补 `sys_user_role`（`role_id` 存 `sys_role.id`，19 位雪花；`管理员` 是 32 位 UUID）。
- 排障陷阱：DBeaver/Navicat 开着「显示外键引用值」时会把 FK 列显示成**角色名**，连 `LENGTH(role_id)` 都被改写，
  容易误判成"存的是名字"——要判定真值请关掉该显示，或用 `JOIN sys_role r ON r.id = ur.role_id` 验证。

**加成员的正确顺序：** ① 界面（系统管理 → 用户管理 → 编辑用户 → 分配角色）；
② 直接写 `sys_user_role` 表；③ 实在要用接口，**先确认回写体里的计算字段不会带崩关系表**——本环境已证明会崩，默认禁用。

完整事故复盘与恢复 SQL：`jeecg-lowcode-miniflow/references/gotchas.md` #95 / #96。
