# 表单数据 CRUD 接口

基础路径：`/desform/data`

## 查询

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/list` | desformCode, pageNo, pageSize, superQuery, column, order, listViewId | 分页列表查询 |
| GET | `/queryById` | id, desformCode | 查询单条数据 |
| GET | `/cardList` | code, pageNo, pageSize, superQuery | 卡片视图列表 |
| GET | `/calendarList` | code, dateField, superQuery | 日历视图列表 |
| GET | `/ganttList` | code, superQuery, startDateCol, endDateCol | 甘特图列表 |
| GET | `/statisticalValue` | code, operationType, operationField, superQuery | 聚合统计 |
| GET | `/queryLinkDataOptions` | desformCode, fieldModel | 关联字段选项 |

## 新增/编辑

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| POST | `/add` | RequestBody: DesignFormData | 新增数据 |
| PUT | `/edit` | RequestBody: DesignFormData | 编辑数据 |
| PUT | `/batchUpdate` | desformCode, fieldModel, fieldValue, superQuery | 批量更新 |

## 删除

| 方法 | 路径 | 说明 |
|------|------|------|
| DELETE | `/{desformCode}/delete?id=xxx` | 逻辑删除（进回收站） |
| DELETE | `/{desformCode}/deleteFromDb?id=xxx` | 物理删除 |
| DELETE | `/{desformCode}/deleteBatch?ids=x,y` | 批量逻辑删除 |
| DELETE | `/{desformCode}/deleteBatchFromDb?ids=x,y` | 批量物理删除 |
| DELETE | `/{desformCode}/clearRecycle` | 清空回收站 |

## 复制

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | `/{desformCode}/copyRecord?id=xxx` | 复制单条（旧接口） |
| PUT | `/{desformCode}/copyRecords?ids=id1,id2,id3` | 复制（界面用这个；多个 id **逗号分隔**，线上为 `ids=id1%2Cid2`，不是 JSON body） |

## 回收站

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/{desformCode}/restoreData?ids=x,y` | 还原数据 |

## 导入导出

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/exportXls/{desformCode}` | 导出 Excel |
| POST | `/importXls/{desformCode}` | 导入 Excel（file） |
| POST | `/uploadExcel/{desformCode}` | 上传预览 |

## 唯一性检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/checkUniqueForField/{desformCode}` | 检查字段值唯一性（fieldModel, fieldValue, dataId） |

## 文件下载

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/download/{desformCode}/{dataId}/{field}` | 下载单个字段文件 |
| GET | `/downloadByFiles?files=x,y` | 批量下载（ZIP） |
