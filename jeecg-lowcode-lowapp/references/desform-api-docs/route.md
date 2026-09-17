# 路由配置接口

基础路径：`/desform/route`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/list` | 路由列表（分页） |
| POST | `/add` | 新增路由 |
| PUT | `/edit` | 编辑路由 |
| DELETE | `/delete?id=xxx` | 删除路由 |
| DELETE | `/deleteBatch?ids=x,y` | 批量删除 |
| GET | `/queryById?id=xxx` | 查询路由 |

路由类型：1=表单跳转、2=菜单跳转、3=外部跳转
