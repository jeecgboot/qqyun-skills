# 菜单 SQL 生成说明

## 生成方式

使用 `gen_menu_sql` 函数生成 `sys_permission`（菜单）和 `sys_role_permission`（角色授权）的 SQL。
**所有 ID（菜单 ID、授权记录 ID）均自动生成 32 位无横线 UUID，无需手动指定。**

```python
# 调用方式：只需传父菜单名称 + 子菜单列表
sql = gen_menu_sql('物业管理', [
    ('小区信息', 'pm_community', 1),
    ('楼栋信息', 'pm_building', 2),
    ('房屋信息', 'pm_house', 3),
])
print(sql)
```

## 生成的 SQL 格式

每条 INSERT 都带完整列名，避免列错位：

```sql
-- 父菜单（ID 自动生成 UUID）
INSERT INTO sys_permission(id, parent_id, name, url, component, component_name, redirect, menu_type, perms, perms_type, sort_no, always_show, icon, is_route, is_leaf, keep_alive, hidden, hide_tab, description, status, del_flag, rule_flag, create_by, create_time, update_by, update_time, internal_or_external)
VALUES ('{uuid}', NULL, '{parentName}', '/{uuid}', 'layouts/RouteView', NULL, NULL, 0, NULL, '1', 1.00, 0, NULL, 1, 0, 0, 0, 0, NULL, '1', 0, 0, 'admin', now(), NULL, NULL, 0);
INSERT INTO sys_role_permission (id, role_id, permission_id, data_rule_ids, operate_date, operate_ip)
VALUES ('{uuid}', '{roleId}', '{parentUuid}', NULL, now(), '127.0.0.1');

-- 子菜单（ID 自动生成 UUID）
INSERT INTO sys_permission(id, parent_id, name, url, component, component_name, redirect, menu_type, perms, perms_type, sort_no, always_show, icon, is_route, is_leaf, keep_alive, hidden, hide_tab, description, status, del_flag, rule_flag, create_by, create_time, update_by, update_time, internal_or_external)
VALUES ('{uuid}', '{parentUuid}', '{desformName}', '/online/desform/list/{desformCode}', 'super/online/desform/auto/AutoDesformDataList', 'AutoDesformDataList', NULL, 0, NULL, '1', 1.00, 0, NULL, 0, 1, 0, 0, 0, NULL, '1', 0, 0, 'admin', now(), NULL, NULL, 0);
INSERT INTO sys_role_permission (id, role_id, permission_id, data_rule_ids, operate_date, operate_ip)
VALUES ('{uuid}', '{roleId}', '{menuUuid}', NULL, now(), '127.0.0.1');
```

## 菜单 SQL 关键字段说明

| 字段 | 值 | 说明 |
|------|-----|------|
| id | 自动生成 32 位 UUID | 如 `d0ca42ae976a4dfbbff491e304858fe1` |
| url | `/online/desform/list/{desformCode}` | 表单设计器数据列表路由，desformCode 是表单编码 |
| component | `super/online/desform/auto/AutoDesformDataList` | 固定值，表单设计器自动数据列表组件 |
| component_name | `AutoDesformDataList` | 固定值 |
| is_route | `0` | 不走普通路由 |
| is_leaf | `1` | 叶子节点 |
| parent_id | `NULL` 或父菜单UUID | NULL=一级菜单，指定父UUID=子菜单 |

## 角色授权 SQL 说明

| 字段 | 值 | 说明 |
|------|-----|------|
| id | 自动生成 32 位 UUID | 每条授权记录独立 UUID |
| role_id | `f6817f48af4fb3af11b9e8bf182f618b` | 默认角色 ID（desform_utils.py 中 ROLE_ID 常量），可通过参数覆盖 |
| permission_id | 对应的菜单 UUID | 关联 sys_permission.id |

> **重要：输出菜单 SQL 时，必须直接使用 `gen_menu_sql` 函数的完整输出，不要手动缩写或省略列名，否则会因列错位导致执行报错。**

## 本地环境自动执行菜单 SQL 规则

**判断条件：** `init_api` 传入的 api_base 以 `http://127.0.0.1` 或 `http://localhost` 开头（不区分大小写）。

**自动执行方式：** 在 `gen_menu_sql` 生成 SQL 后，通过 Bash 工具逐条执行 MySQL 命令：

```bash
# 先检查菜单是否已存在，避免重复插入
mysql -h127.0.0.1 -P3306 -uroot -proot jeecgboot3 -e "SELECT id FROM sys_permission WHERE id='{menuId}'"
# 不存在则执行插入（包括 sys_permission 和 sys_role_permission）
mysql -h127.0.0.1 -P3306 -uroot -proot jeecgboot3 -e "INSERT INTO sys_permission(...) VALUES (...);"
mysql -h127.0.0.1 -P3306 -uroot -proot jeecgboot3 -e "INSERT INTO sys_role_permission(...) VALUES (...);"
```

**注意事项：**
- 将 `gen_menu_sql` 的每条 INSERT 语句拆分后逐条通过 MySQL CLI 执行
- 执行前先检查父菜单 ID 是否已存在，避免重复插入
- 如果 MySQL 执行失败，回退为输出 SQL 让用户手动执行，不中断整体流程
- 数据库连接参数默认 `mysql -h127.0.0.1 -P3306 -uroot -proot jeecgboot3`，与 jeecg-codegen 保持一致
- 输出结果中标注 `菜单 SQL：已自动执行`
