# 微服务 API 接口

本文件包含两类接口，基础路径不同：

- **内部接口**（`DesformBaseApiController`，下面标「内部接口」的分组）：2026-10-14 起基础路径由 `/desform/api` 改为 `/desform/inner/api`，只在微服务模式加载，供其他服务 Feign 调用；单体模式下不存在，微服务下网关也会拦截外部访问。**skill 脚本不要调用。**
- **前端接口**（表单结构、字段操作）：基础路径仍是 `/desform/api`，可正常调用。

## 数据查询（内部接口，`/desform/inner/api`，skill 不可调用）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/getDataById` | 按ID查询数据（desformCode, id） |
| GET | `/getFieldDataById` | 按ID查询指定字段（desformCode, dataId, fieldNames） |
| GET | `/getTranslateDataById` | 按ID查询（含翻译） |
| GET | `/getDataByIds` | 批量按ID查询 |
| GET | `/getViewListByCode` | 获取表单的所有表单视图（izView=1 的视图，非列表视图） |

## 数据操作（内部接口，`/desform/inner/api`，skill 不可调用）

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | `/updateDataById` | 更新数据（desformCode, id, body） |
| DELETE | `/deleteDataById` | 删除数据（desformCode, ids） |

## 表单管理（内部接口，`/desform/inner/api`，skill 不可调用）

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | `/copyDesignForm` | 复制表单（originFormCode, newFormCode）。skill 复制表单请用 `copy_form()`，走前端同款的 `/online/lowAppMenu/copy` |
| DELETE | `/deleteDesignForm` | 逻辑删除表单 |
| DELETE | `/realDeleteDesignForm` | 物理删除表单 |

## 数据翻译（内部接口，`/desform/inner/api`，skill 不可调用）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/translateData/{desformCode}` | 翻译数据字段值 |
| POST | `/translateData2` | 翻译（支持指定字段） |

## 表单结构（前端接口，`/desform/api`）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/struct/{desformCode}` | 获取表单结构定义 |
| GET | `/fields/{desformCode}` | 获取字段列表 |
| GET | `/config/{desformCode}` | 获取表单前端配置 |

## 字段操作（前端接口，`/desform/api`）

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | `/{desformCode}/addWidget` | 向表单追加控件 |
| PUT | `/{desformCode}/updateWidget` | 更新/删除控件 |
