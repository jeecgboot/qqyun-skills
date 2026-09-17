# 导入导出接口

## 导出

```
GET /desform/data/exportXls/{desformCode}
参数：pageNo, pageSize, superQuery, column, order, selections, selectionIds, listViewId
返回：Excel 文件流
```

## 导入

```
POST /desform/data/importXls/{desformCode}
参数：file (multipart), isCreateMissFields
返回：导入结果（成功/失败数）
```

## 上传预览

```
POST /desform/data/uploadExcel/{desformCode}
参数：file (multipart)
返回：上传信息（预览数据）
```

## 字段转换器（17种）

| 转换器 | 控件类型 | 导出行为 | 导入行为 |
|--------|---------|---------|---------|
| NormalConvert | input/textarea 等 | 原值 | 原值 |
| DateConverter | date/time | 格式化日期 | 解析日期 |
| MoneyConverter | money | 格式化金额 | 解析数字 |
| SelectUserConverter | select-user | ID→姓名 | 姓名→ID |
| SelectDepartConverter | select-depart | ID→部门名 | 部门名→ID |
| LinkRecordConverter | link-record | ID→标题 | 标题→ID |
| MultipleConverter | checkbox/多选 | 逗号分隔 | 文本拆分 |
| FileConverter | file-upload | 文件名列表 | — |
| PictureConverter | imgupload | 图片链接 | — |
| SwitchConverter | switch | Y/N→是/否 | 是/否→Y/N |
| AreaLinkageConverter | area-linkage | 编码→名称 | 名称→编码 |
| LocationConverter | location | 经纬度 | — |
| TableDictConverter | table-dict | 编码→名称 | 名称→编码 |
| SelectTreeConverter | select-tree | 编码→名称 | 名称→编码 |
| SelectRoleConverter | org-role | 编码→名称 | 名称→编码 |
| LinkFieldConverter | link-field | 关联值 | — |
| OaApprovalCommentsConverter | oa-approval-comments | 审批意见 | — |
