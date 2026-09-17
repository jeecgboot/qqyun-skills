# 表单设计 CRUD API

基础路径：`/desform`

## 表单列表与查询

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/list` | 分页查询表单列表（支持 QueryGenerator 动态条件） |
| GET | `/queryByCode?desformCode={code}` | 按编码查询单个表单（部分表单可能查不到，推荐用 queryByIdOrCode） |
| GET | `/queryById?id={id}` | 按 ID 查询单个表单 |
| GET | `/queryByIdOrCode?desformCode={code}` | **推荐**：按编码或 ID 查询，更可靠 |
| GET | `/queryFormAndView?desformCode={code}` | 查询表单及其所有表单视图 |
| GET | `/getColumns?desformCode={code}` | 获取表单的字段列表 |
| GET | `/getAdaptCfg` | 获取数据适配器配置（SQL/MongoDB） |

### `/list` 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `pageNo` | int | 页码，默认 1 |
| `pageSize` | int | 每页条数，默认 10 |
| `desformName` | string | 按名称模糊查询 |
| `desformCode` | string | 按编码精确查询 |
| `hasWordTemplate` | boolean | 筛选有 Word 模板的表单 |
| `column` | string | 排序字段 |
| `order` | string | 排序方向 asc/desc |

## 表单新建与编辑

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/add` | 新建表单（注意：result 返回 null，需要再次查询获取 ID） |
| PUT | `/edit` | 更新表单设计（**必须传 updateCount 当前值**） |

### `/add` 请求体

创建**表单**：

```json
{
  "desformName": "表单名称",
  "desformCode": "form_code"
}
```

创建**表单视图**（`izView=1`，`izMobileView=0/1` 区分 PC/移动端）：

```json
{
  "desformName": "视图名称",
  "desformCode": "form_code",
  "desformDesignJson": "{...}",
  "izView": 1,
  "izMobileView": 0
}
```

> 表单视图与列表视图是两个独立概念：表单视图控制填报界面的字段布局；列表视图控制数据记录在列表页的展示方式（见 `list-view.md`）。

### `/edit` 请求体

```json
{
  "id": "表单ID",
  "desformDesignJson": "{\"list\":[...],\"config\":{...}}",
  "updateCount": 1,
  "autoNumberDesignConfig": {"update": {}, "current": {}},
  "refTableDefaultValDbSync": {"changes": {}, "removeKeys": []}
}
```

> **重要：** `updateCount` 必须传**当前数据库中的值**，后端会自动递增。传错值会导致乐观锁冲突（报错 "操作冲突"）。

### 响应格式

```json
{
  "success": true,
  "message": "操作成功！",
  "code": 200,
  "result": {
    "id": "...",
    "updateCount": 2
  }
}
```

## 删除与回收站

| 方法 | 路径 | 说明 |
|------|------|------|
| DELETE | `/delete?id={id}` | 逻辑删除表单（移入回收站） |
| DELETE | `/deleteBatch?ids={id1,id2}` | 批量逻辑删除 |
| GET | `/recycleBin/list` | 查询回收站列表 |
| PUT | `/recycleBin/recoverByIds?ids={id1,id2}` | 从回收站恢复表单 |
| DELETE | `/recycleBin/deleteByIds?ids={id1,id2}` | 从回收站物理删除（不可恢复） |
| DELETE | `/recycleBin/empty` | 清空回收站 |

## RESTful API（/api 前缀）

用于外部系统集成的 RESTful 风格接口。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/struct/{desformCode}` | 获取表单结构（字段定义） |
| GET | `/api/fields/{desformCode}` | 获取表单字段列表 |
| GET | `/api/config/{desformCode}` | 获取表单配置 |
| GET | `/api/{desformCode}/list` | 查询表单数据列表 |
| GET | `/api/{desformCode}/{dataId}` | 获取单条数据 |
| POST | `/api/{desformCode}` | 新增一条数据 |
| PUT | `/api/{desformCode}/{dataId}` | 更新一条数据 |
| DELETE | `/api/{desformCode}/{dataId}` | 删除一条数据 |
| PUT | `/api/{desformCode}/addWidget` | 向已有表单追加控件 |
| PUT | `/api/{desformCode}/updateWidget` | 修改指定控件属性 |
| GET | `/api/queryIdByCode?desformCode={code}` | 编码转 ID |
| GET | `/api/queryCodeById?id={id}` | ID 转编码 |
| GET | `/api/{desformCode}/getName` | 获取表单名称 |
| GET | `/api/list/options` | 获取表单下拉选项列表 |

## 工具接口

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | `/redoAllIndex` | 重建所有表单的 MongoDB 索引 |
| PUT | `/redoAllIndexForce` | 强制重建索引 |
| GET | `/getCurrentAutoNumberNo` | 获取自动编号当前值 |
| POST | `/subToWorksheet` | 子表转为独立工作表。只建新表+迁数据，**不改**主表设计；随后必须 `PUT /edit` 把主表字段换成工作表子表。两步见 `desform-new-sub-table.md`「转换工作表」 |
| PUT | `/translateColumns` | 翻译字段值（字典值转显示文本） |
| POST | `/api/aigc` | AIGC 智能生成表单 |
