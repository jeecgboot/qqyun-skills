# 微服务 API 接口

基础路径：`/desform/api`

## 数据查询

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/getDataById` | 按ID查询数据（desformCode, id） |
| GET | `/getFieldDataById` | 按ID查询指定字段（desformCode, dataId, fieldNames） |
| GET | `/getTranslateDataById` | 按ID查询（含翻译） |
| GET | `/getDataByIds` | 批量按ID查询 |
| GET | `/getViewListByCode` | 获取表单的所有表单视图（izView=1 的视图，非列表视图） |

## 数据操作

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | `/updateDataById` | 更新数据（desformCode, id, body） |
| DELETE | `/deleteDataById` | 删除数据（desformCode, ids） |

## 表单管理

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | `/copyDesignForm` | 复制表单（originFormCode, newFormCode） |
| DELETE | `/deleteDesignForm` | 逻辑删除表单 |
| DELETE | `/realDeleteDesignForm` | 物理删除表单 |

## 数据翻译

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/translateData/{desformCode}` | 翻译数据字段值 |
| POST | `/translateData2` | 翻译（支持指定字段） |

## 表单结构

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/struct/{desformCode}` | 获取表单结构定义 |
| GET | `/fields/{desformCode}` | 获取字段列表 |
| GET | `/config/{desformCode}` | 获取表单前端配置 |

## 字段操作

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | `/{desformCode}/addWidget` | 向表单追加控件 |
| PUT | `/{desformCode}/updateWidget` | 更新/删除控件 |
