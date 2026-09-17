# 敲敲云应用级数据字典

敲敲云（lowApp）里的数据字典是**应用级**的，不是 JeecgBoot 全局 `/sys/dict` 普通字典。操作时必须在请求头里带 `x-tenant-id` 和 `x-low-app-id`。

## 接口

| 操作 | 方法 | 路径 |
|------|------|------|
| 查询 | GET | `/sys/dict/getDictListByLowAppId` |
| 新增 | POST | `/sys/dict/addDictByLowAppId` |
| 编辑 | PUT | `/sys/dict/editDictByLowAppId` |
| 删除 | DELETE | `/sys/dict/delete?id=<字典ID>` |

- 新增时后端自动生成 10 位随机 `dictCode`，但接口 `result` 固定返回 `"添加成功"`；要拿 `dictCode` 请调用 `--action query`，从返回列表里按 `dictName`/`id` 找到刚创建的字典。
- `lowAppId`、`tenantId` 由后端从 header 读取，不需要写进 body。
- `editDictByLowAppId` 会先按 id 删除旧字典项再重新写入。

## 脚本

```bash
python "<skill>/scripts/lowapp_dict.py" \
  --api-base <URL> --token <TOKEN> \
  --tenant-id <TENANT_ID> --app-id <APP_ID> \
  --action query|add|edit|delete \
  [--config dict_job.json] [--id <DICT_ID>]
```

## 配置格式

新增：

```json
{
  "dictName": "性别",
  "dictItemsList": [
    {"itemText": "男", "itemValue": "0", "itemColor": "#2196F3", "sortOrder": 1},
    {"itemText": "女", "itemValue": "1", "itemColor": "#FF9300", "sortOrder": 2}
  ]
}
```

编辑时增加 `"id": "<字典ID>"`。

`dictItemsList` 项字段：

| 字段 | 必填 | 说明 |
|------|------|------|
| `itemText` | 是 | 显示文本 |
| `itemValue` | 否 | 选项值；不填时脚本按数组下标从 `0` 递增 |
| `itemColor` | 否 | 字典项颜色；不填时脚本自动按顺序从合法 20 色分配 |
| `sortOrder` | 否 | 排序，不填时按数组下标从 `1` 递增 |

合法颜色仅支持以下 20 个：

`#2196F3`、`#08C9C9`、`#00C345`、`#FAD714`、`#FF9300`、`#F52222`、`#EB2F96`、`#7500EA`、`#2D46C4`、`#484848`、`#C9E6FC`、`#C3F2F2`、`#C2F1D2`、`#FEF6C6`、`#FFE5C2`、`#FDCACA`、`#FACDE6`、`#DEC2FA`、`#CCD2F1`、`#D3D3D3`

## 在表单控件里使用

拿到新增接口返回的 `dictCode` 后，配置 radio/checkbox/select：

```json
{
  "options": {
    "remote": "dict",
    "dictCode": "<返回的 dictCode>",
    "dictCodeAppId": "<当前低代码应用ID>",
    "showLabel": true
  },
  "dictOptions": [
    {"value": "0", "label": "男"},
    {"value": "1", "label": "女"}
  ]
}
```

实测保存后，敲敲云后端会把 `options.remote` 归一化为 `false`，同时写入 `options.dictCode`、`options.dictCodeAppId`、`options.isDictItem: true`、以及字典项快照；这是正常的落库形态，不需要手动改回 `remote: "dict"`。

**但「提交时」options.remote 必须写 `"dict"` 并经整单保存**（2026-09-08 定论，修正早期「面板态只能 UI 点选」结论）：设计器面板/画布/运行态全部以 `options.remote==='dict'` 判定数据字典；提交 remote=false 只写 dictCode/isDictItem/快照 → 面板显示静态数据。字段级 `update_widget` 提交 dict 无效，必须整单保存；且含字典字段的表每次整单保存都要让字典控件保持 remote:"dict" 提交，否则绑定态被冲掉回静态。详见 SKILL.md「绑定应用级字典 — 保存时提交 remote:'dict'」节。

## 关键踩坑

`options.dictCodeAppId` 是敲敲云应用级字典的**必需字段**，值就是当前低代码应用 ID。只写 `dictCode` 不写 `dictCodeAppId` 时，字段面板可能显示“已设置”，但运行/点击时找不到字典、不回显。创建字典后，把 `dictCodeAppId` 一并写入控件 `options`。
