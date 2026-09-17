# 改已有关联记录（快路径）

> ⚠️ 2026-09-02 实测坑（已修复）：查询工作表默认值（linkage）曾因脚本把 value 存成字符串、设计器面板读不到而「设置不上」，现已改为字符对象 + 整单保存，直接跑本页脚本即可。**只有遇到历史遗留的字符串形态 value / 面板仍不显示时**才需要读 `fast-link-record-linkage.md` 的手动配方兜底。显示方式 / 记录范围 / filters 不受影响。

只读这一页。读完立刻执行，不要再打开本技能 SKILL.md、`desform-link-record.md`、`desform-linkage-query.md`、`desform-widget-options.md`、`desform-filter-rules.md`、`jeecg-desform`。

**这不是建表。** 新建工作表 / 一对一走 `fast-create.md`。本页只改已经存在的 `link-record`：显示方式、记录范围、查看权限、默认值第一条、查询工作表。

整轮墙钟 **2 分钟内**。超过 2 分钟 = 又在开场读文档或手写 `update_widget`。

## 第一条 tool call

1. 用户消息里的 `api-base` / token 直接用。会话已有 `tenantId` / `appId` / 表 code / 字段 key 就写进 JSON，禁止再 list。
2. Write UTF-8 JSON 到 `{tmpdir}/jeecg-desform/link_job.json`（会话已有该目录则直接拼路径）。
3. 立刻：

```bash
python "<skill目录>/scripts/update_link_record.py" --api-base <URL> --token <TOKEN> --config <link_job.json>
```

Windows：中文只写在 JSON 文件里，禁止 `python -c`、禁止 PowerShell `--json '{"中文"}'`。不要等 y/n。不要先 `get_form_fields`。字段中文名交给脚本解析，禁止猜 model。

## job.json

只写用户点名要改的键。脚本会把中文规则 / 字段名解析成控件 JSON。

```json
{
  "tenantName": "八匹狼",
  "appName": "关联记录",
  "worksheet": "采购单",
  "field": "采购明细",
  "showType": "下拉",
  "dataSelectAuth": "有查看权限",
  "defaultValType": "第一条数据",
  "filterMatchType": "AND",
  "filters": [
    {"field": "物料编码", "rule": "开头是", "value": "wl_"},
    {"field": "数量", "rule": "不等于", "value": "0"},
    {"field": "单价", "rule": "大于等于", "value": "0"}
  ],
  "linkage": {
    "matchType": "OR",
    "operation": "自定义排序",
    "rules": [
      {"field": "单价", "rule": "大于", "valueType": "fixed", "value": "0"},
      {"field": "创建人", "rule": "等于", "valueType": "field", "value": "采购人"}
    ],
    "sorts": [
      {"field": "创建时间", "order": "asc"},
      {"field": "单价", "order": "asc"}
    ]
  }
}
```

| 字段 | 说明 |
|------|------|
| `tenantName` / `appName` / `worksheet` / `field` | 用户原话即可。精确匹配，0 条再去掉末尾「租户/组织/应用/工作表/关联记录」 |
| `tenantId` / `appId` / `code` / `key` | 会话已有就写这个，脚本不再 list |
| `showType` | `下拉`/`卡片`/`表格` 或 `select`/`card`/`table` |
| `dataSelectAuth` | `有查看权限`/`read` 或 `全部`/`all` |
| `defaultValType` | `第一条数据`/`first` 或 `无`/`none`。写了 `linkage` 时脚本强制 `none`。⚠️ 界面另有两档「其他字段值」「固定值」——parser 都会拒绝，分别见下方「默认值类型=其他字段值」「默认值类型=固定值」配方 |
| `filters` | 记录范围。`rule` 用中文（开头是/不等于/大于等于/等于/包含/为空）或大写 `BEFORE`/`NE`/`GE`。`valueType` 默认 `fixed`；引用本表字段用 `field`，`value` 填本表字段中文名 |
| `appendFilters` | `true` 时按源字段 model 追加，不覆盖其它已有条件 |
| `linkage` | 查询工作表默认值。`valueType: field` 的 `value` 是**本表**字段名（如采购人）；条件字段是**源表**字段名（如单价、创建人） |
| `linkage.operation` | `自定义排序`/`CUSTOM_SORT`（要 sorts）、`FIRST`、`LAST` |

一次请求里能改的都写进同一个 JSON，不要拆成多轮脚本。

## 默认值类型 =「其他字段值」（引用同表控件）

⚠️ 适用范围：本节与下节「固定值」均为 **link-record（关联记录/联动）控件专属**的默认值面板——普通控件没有这套 UI 与存储，不要推广到其它控件。

2026-09-02 实测（八匹狼租户「关联记录」应用「订单」工作表「订单支付记录」，手工界面配置后 `query_form` 读库确认）：

界面「默认值类型」第 3 档「其他字段值」= 引用**同表**控件（须同为关联记录、指向同一源表，单选）。落库**不走** `options.defaultValType`（保持 `"none"`），而是改控件**顶层** `advancedSetting.defaultValue`，type 仍是 `compose`，`value` 写 `$被引用控件model$`：

```json
{
  "options": { "defaultValType": "none" },
  "advancedSetting": {
    "defaultValue": {
      "type": "compose",
      "value": "$link_record_1788344960305_670090$",
      "format": "string",
      "allowFunc": true,
      "valueSplit": ",",
      "customConfig": true
    }
  }
}
```

- 样例：订单「订单支付记录」引用同表隐藏控件「隐藏订单支付记录」（model `link_record_1788344960305_670090`），两者源表均为 `ws_90fe10081f`。
- `$…$` 里必须是**被引用控件自己的 model**（中文名或别的字段 model 都不行）。被引用值为空时默认值为空；值变化时自动重算（compose 字段引用通用行为）。
- ⚠️ `update_link_record.py` parser **不接受** `defaultValType: 其他字段值`（报「只能是 none/first」）。走整单保存配方（同 linkage 兜底，Windows 中文写文件禁止 `python -c`）：

```python
# -*- coding: utf-8 -*-
import sys, json, os, tempfile
sys.path.insert(0, r'<skill目录>/scripts')
from desform_lowapp_utils import init_lowapp
from desform_utils import query_form, save_design_from_file

init_lowapp(api_base, token, tenant_id=..., app_id=...)
design = json.loads(query_form('<表code>')['desformDesignJson'])

def find(node, key):
    if isinstance(node, dict):
        if node.get('key') == key:
            return node
        for v in node.values():
            r = find(v, key)
            if r:
                return r
    elif isinstance(node, list):
        for i in node:
            r = find(i, key)
            if r:
                return r

w = find(design, '<被改控件key>')   # 如 1788334072485_814628
w.setdefault('advancedSetting', {}).setdefault('defaultValue', {})['value'] = '$<被引用控件model>$'
path = os.path.join(tempfile.gettempdir(), 'jeecg-desform', '<表code>_design.json')
os.makedirs(os.path.dirname(path), exist_ok=True)
json.dump(design, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
save_design_from_file('<表code>', path)
```

验证：Ctrl+F5 刷新设计器，字段面板「默认值」应显示其他字段值 + 控件名；或 `query_form` 读 `advancedSetting.defaultValue.value` 是否含 `$…$`。

## 默认值类型 =「固定值」(选中源表具体记录)

2026-09-02 实测（八匹狼租户「关联记录」应用「订单」工作表「订单支付记录」）：UI 默认值区块显示「已设置N条默认值」，点 [+] 弹「选择默认记录」，列表=源表数据，选中一条作为固定默认。⚠️ 仅 link-record 控件有这套「选择默认记录」存储（联动专属），普通控件无。

落库**分两处，缺一不可**：

1. **设计 JSON**：widget 只写档位标记 `options.defaultValType: "fixed"`（`options.defaultValue` 保持 `""`）；
2. **独立存储**：随 **`PUT /desform/edit`**（整单保存接口）请求体**顶层**额外字段 `refTableDefaultValDbSync` 同步，changes 里存选中记录：

```json
"refTableDefaultValDbSync": {
  "changes": {
    "<widgetKey>": {                       // 控件 key，如 1788334072485_814628
      "desformCode": "<本表code>",
      "widgetKey": "<widgetKey>",
      "type": "fixed",
      "queryConfig": null,                 // 其它 type 才非 null
      "fixedData": ["<源表记录id>"]         // 选中的源表数据行 id（19位）
    }
  },
  "removeKeys": []
}
```

- 实测样本：`fixedData: ["2095051678106976257"]` = 支付记录 NO202609021。设计器重开时把该存储读回显示「已设置1条默认值」——所以只翻 `desformDesignJson` 永远找不到记录 id。
- PUT /desform/edit 完整 body = desform 实体：`{id, desformCode, desformDesignJson, updateCount, refTableDefaultValDbSync, autoNumberDesignConfig:{update:{},current:{}}}`；`updateCount` 必须从 `query_form` 现取（乐观锁，不取会版本冲突）。
- 清除默认记录：推测 `removeKeys: ["<widgetKey>"]`（未实测）。
- ⚠️ 现有工具脚本与 `save_design_from_file` 都不携带 `refTableDefaultValDbSync`，自动配置该档必须手写 PUT（配方）：

```python
# -*- coding: utf-8 -*-
import sys, json, urllib.request
sys.path.insert(0, r'<skill目录>/scripts')
from desform_lowapp_utils import init_lowapp
from desform_utils import query_form

init_lowapp(api_base, token, tenant_id=..., app_id=...)
row = query_form('<表code>')
# 1) 递归定位 widget（按 name 或 key），改 options.defaultValType = 'fixed'
# 2) 整单 PUT /desform/edit：
body = {
    'id': row['id'], 'desformCode': row['desformCode'],
    'desformDesignJson': json.dumps(design, ensure_ascii=False),
    'updateCount': row['updateCount'],
    'refTableDefaultValDbSync': {
        'changes': {'<widgetKey>': {
            'desformCode': row['desformCode'], 'widgetKey': '<widgetKey>',
            'type': 'fixed', 'queryConfig': None,
            'fixedData': ['<源表记录id>']}},
        'removeKeys': []},
    'autoNumberDesignConfig': {'update': {}, 'current': {}},
}
req = urllib.request.Request(api_base + '/desform/edit',
    data=json.dumps(body).encode('utf-8'), method='PUT',
    headers={'Content-Type': 'application/json',
             'X-Access-Token': token, 'X-Tenant-Id': str(tenant_id)})
print(urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'replace'))
```

验证：Ctrl+F5 刷新设计器，字段「默认值」显示已设置记录；新增记录看默认带出。

## 禁止（再犯就是 6 分钟）

- Read 本技能 SKILL.md 全文、`desform-link-record.md`、`desform-linkage-query.md`、widget-options、filter-rules
- 手写 `filters` 用小写 `right_like` / `valueType:"value"` / `type:"text"`（那是列表筛选，运行时「开头是」不生效）
- 手写查询工作表编码、去翻源码 / GitHub 猜 `fCode`
- 先 `get_form_fields` 探路再改；为没有数字 ID 再问一轮
- 把记录范围配成列表数据过滤 / 高级查询
