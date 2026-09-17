# 权限管理接口

基础路径：`/desform/auth`

## 查询

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/list` | 分页列表 |
| GET | `/query/{code}` | 按表单编码查询所有权限 |
| GET | `/query/{code}/{authComKey}` | 查询单个权限 |
| GET | `/queryById?id=xxx` | 按ID查询 |
| GET | `/list/{permissionType}/{desformCode}` | 按权限类型筛选 |
| GET | `/roleList/{roleCode}/{permissionType}/{desformCode}` | 按角色筛选 |
| GET | `/departList/{departId}/{permissionType}/{desformCode}` | 按部门筛选 |
| GET | `/userList/{username}/{permissionType}/{desformCode}` | 按用户筛选 |

## 新增

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/addAuth` | 添加单个权限 |
| POST | `/addAuthBatch` | 批量添加权限 |
| POST | `/addAuth/{permissionType}` | 按类型添加 |

## 编辑

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | `/edit` | 编辑权限 |
| PUT | `/edit/{permissionType}` | 按类型编辑 |
| PUT | `/updateFieldStatus` | 更新字段状态 |
| PUT | `/updateBatch` | 批量更新 |
| PUT | `/saveOrUpdateBatch` | 批量保存或更新 |

## 删除

| 方法 | 路径 | 说明 |
|------|------|------|
| DELETE | `/delete?id=xxx` | 删除单个 |
| DELETE | `/deleteBatch?ids=x,y` | 批量删除 |
| DELETE | `/deleteByComKey` | 按 comKey 删除 |
| DELETE | `/deleteBatchByAuthComKey` | 按 authComKey 批量删除 |
| POST | `/cleanAuthData/{desformCode}` | 清理无效权限 |

## 权限类型（permissionType）

- `field` — 字段权限（可见/可编辑/列表可见）
- `data` — 数据权限（行级过滤）
- `button` — 按钮权限（操作控制）
