# Excel 导入导出

## 导出流程

```
GET /desform/data/exportXls/{desformCode}
→ 获取表单设计信息
→ 查询表单数据
→ 通过 ConvertFactory 创建字段转换器
→ 输出 Excel 文件
```

支持参数：pageNo, pageSize, superQuery, selections（选中行导出）

## 导入流程

```
POST /desform/data/importXls/{desformCode}
→ 上传 Excel 文件
→ 逐行解析数据
→ 通过 ConvertFactory 反向转换
→ ExcelImportMainDataHandler 处理主表
→ ExcelImportInnerSubDataHandler 处理子表
→ 批量保存数据
```

## 17 种字段转换器

| 转换器 | 控件 | 导出 | 导入 |
|--------|------|------|------|
| NormalConvert | input/textarea | 原值 | 原值 |
| DateConverter | date/time | 格式化 | 解析 |
| MoneyConverter | money | 格式化 | 解析数字 |
| SelectUserConverter | select-user | ID→姓名 | 姓名→ID |
| SelectDepartConverter | select-depart | ID→部门名 | 部门名→ID |
| SelectRoleConverter | org-role | 编码→名称 | 名称→编码 |
| LinkRecordConverter | link-record | ID→标题 | 标题→ID |
| LinkFieldConverter | link-field | 关联值 | — |
| MultipleConverter | checkbox/多选 | 逗号分隔 | 拆分 |
| FileConverter | file-upload | 文件名 | — |
| PictureConverter | imgupload | 图片链接 | — |
| SwitchConverter | switch | 是/否 | 是/否 |
| AreaLinkageConverter | area-linkage | 编码→名称 | 名称→编码 |
| LocationConverter | location | 经纬度 | — |
| TableDictConverter | table-dict | 编码→名称 | 名称→编码 |
| SelectTreeConverter | select-tree | 编码→名称 | 名称→编码 |
| OaApprovalCommentsConverter | oa-approval-comments | 审批意见 | — |
