# 外链表单（公共填报）

外链表单允许未登录用户通过公共链接访问和填写表单，适用于问卷调查、信息采集等场景。

## 开启外链

在 `config` 中设置：

```json
{
  "config": {
    "allowExternalLink": true,
    "externalLinkShowData": false,
    "headerImgUrl": "",
    "externalTitle": "请填写信息"
  }
}
```

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `allowExternalLink` | 是否允许外链访问 | `false` |
| `externalLinkShowData` | 提交后是否显示已填数据 | `false` |
| `headerImgUrl` | 外链页面顶部图片 URL | `""` |
| `externalTitle` | 外链页面标题 | `""` |

## API 端点

### 外链授权管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/desform/url/list` | 查询外链授权列表 |
| POST | `/desform/url/add` | 创建外链授权 |
| PUT | `/desform/url/edit` | 更新外链授权 |
| DELETE | `/desform/url/delete?id=xxx` | 删除外链授权 |
| GET | `/desform/url/queryAllStatus?desformCode=xxx` | 查询所有授权状态（自动初始化） |
| PUT | `/desform/url/editAllStatus` | 批量修改授权状态 |

### 按 ID 访问（PubController）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/desform/pub/{desformId}` | 打开新增表单页面（免登录） |
| GET | `/desform/pub/{desformId}/{dataId}` | 打开编辑表单页面 |
| POST | `/desform/pub/{desformId}` | 提交新增数据 |
| PUT | `/desform/pub/{desformId}/{dataId}` | 提交编辑数据 |
| GET | `/desform/pub/success` | 提交成功页面 |

### 按编码访问（ExtController）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/desform/ext/{desformCode}` | 按编码打开新增表单 |
| GET | `/desform/ext/{desformCode}/{dataId}` | 按编码打开编辑表单 |
| POST | `/desform/ext/{desformCode}` | 按编码提交新增数据 |
| PUT | `/desform/ext/{desformCode}/{dataId}` | 按编码提交编辑数据 |
| GET | `/desform/ext/success` | 按编码提交成功页面 |

## 外链授权实体

`design_form_url_auth` 表字段：

| 字段 | 说明 |
|------|------|
| `desformId` | 关联表单 ID |
| `desformCode` | 关联表单编码 |
| `urlType` | 链接类型（新增、编辑、详情） |
| `urlStatus` | 状态：1=有效，2=无效 |

## 使用流程

1. 创建表单并在 config 中设置 `allowExternalLink: true`
2. 通过 `/desform/url/add` 创建外链授权记录（设置 `urlStatus: 1`）
3. 构造外链 URL：`{后端地址}/desform/ext/{desformCode}`
4. 分享 URL 给外部用户填写
5. 用户填写后数据自动保存到 `design_form_data` 表

## 注意事项

- 外链表单不需要登录，但需要外链授权记录有效（`urlStatus=1`）
- 可通过 `headerImgUrl` 和 `externalTitle` 自定义外链页面外观
- 设置 `externalLinkShowData: true` 可在提交后展示用户填写的数据
- 通过关闭 `urlStatus` 可随时停用外链
- 授权管理支持三种类型（新增、编辑、详情），首次查询时会自动初始化
