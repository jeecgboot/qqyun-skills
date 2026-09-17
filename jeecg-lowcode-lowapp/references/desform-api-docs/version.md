# 版本管理接口

基础路径：`/desform/version`

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/list` | desformCode, pageNo, pageSize | 版本列表 |
| POST | `/create` | desformCode, remarks | 创建版本快照 |
| PUT | `/update` | id, remarks | 更新版本备注 |
| GET | `/queryById?id=xxx` | id | 查询版本详情（含设计JSON快照） |
| DELETE | `/deleteById?id=xxx` | id | 删除版本 |
| DELETE | `/deleteBatchById?ids=x,y` | ids | 批量删除 |

版本记录包含字段：desformCode、version、desformDesignJson（快照）、widgetCount、remarks、mainUpdateCount。
