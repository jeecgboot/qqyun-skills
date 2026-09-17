# 选项数据源配置（radio / checkbox / select）

单选框、多选框、下拉选择支持四种选项数据源。

## 一、数据源决策流程

```
需要选项数据源
    ↓
选项是否固定不变？
  ├─ 是 → 选项是否通用（多表单共用）？
  │      ├─ 是 → 系统字典（search_dict → 有则用，无则创建）
  │      └─ 否 → 静态选项
  └─ 否 → 选项来自哪里？
         ├─ 来自其他表单字段 → 查询工作表（linkData）
         └─ 来自自定义接口 → 远程函数
```

**AI 使用系统字典的决策流程**：
1. `search_dict(关键词)` 搜索系统内是否已有合适的字典
2. 有匹配 → `query_dict(dictCode)` 获取字典项 → 直接使用
3. 无匹配 → 选项会被多个表单复用 → 创建新字典；仅此表单使用 → 使用静态选项

## 二、静态选项（remote: false）

```json
{
  "options": {
    "remote": false,
    "options": [
      { "value": "1", "label": "选项一", "itemColor": "#2196F3" },
      { "value": "2", "label": "选项二", "itemColor": "#08C9C9" }
    ]
  }
}
```

适用场景：选项固定不变、数量少。

Python 用法：
```python
RADIO('是否同意', [
    {'value': 'Y', 'label': '同意'},
    {'value': 'N', 'label': '不同意'}
])
SELECT('职位', ['教授', '副教授', '讲师'])  # 字符串列表自动转 value=label
```

## 三、系统字典（remote: "dict"）— 推荐

```json
{
  "options": {
    "remote": "dict",
    "dictCode": "sex",
    "options": []
  },
  "dictOptions": [
    { "value": "1", "label": "男" },
    { "value": "2", "label": "女" }
  ]
}
```

运行时调用 `GET /sys/dict/getDictItems/{dictCode}` 加载选项。

### 常用系统字典编码

| dictCode | 名称 | 值 |
|----------|------|-----|
| `sex` | 性别 | 1=男, 2=女 |
| `priority` | 优先级 | L=低, M=中, H=高 |
| `valid_status` | 有效状态 | 0=无效, 1=有效 |
| `yn` | 是否 | Y=是, N=否 |
| `msg_category` | 消息类型 | 1=通知, 2=系统 |
| `send_status` | 发送状态 | 0=未发送, 1=已发送 |

### Python 用法

```python
# 先搜索是否有合适的字典
results = search_dict('性别')  # → [{'dictCode': 'sex', ...}]

# 查询字典项
sex_items = query_dict('sex')  # → [{'value': '1', 'text': '男'}, ...]

# 使用字典创建控件
RADIO('性别', sex_items, dict_code='sex')
SELECT('优先级', query_dict('priority'), dict_code='priority')
```

**关键规则**：
- `dict_code` 参数对应系统字典编码
- `options` 位置参数必填，传 `[{value, label}]` 列表
- 底层自动设置 `remote="dict"` 和 `dictOptions`

### 创建新字典

当系统内没有合适的字典时：

**Step 1：创建字典主表**
```
POST /sys/dict/add
{"dictCode": "leave_type", "dictName": "请假类型", "description": "请假类型选项", "type": 0}
```

**Step 2：逐条添加字典项**
```
POST /sys/dictItem/add
{"dictId": "{字典ID}", "itemText": "事假", "itemValue": "1", "sortOrder": 1, "status": 1}
```

**Python 工具函数**（desform_utils.py 提供）：
```python
# 创建字典（自动创建主表+字典项）
dict_id = create_dict('leave_type', '请假类型', [
    {'value': '1', 'label': '事假'},
    {'value': '2', 'label': '病假'},
    {'value': '3', 'label': '年假'},
])

# 查询或创建（优先查询已有字典，避免重复）
dict_id, items = query_or_create_dict('leave_type', '请假类型', [...])
```

## 四、查询工作表（remote: "linkData"）

从目标工作表中查询指定字段的去重值作为下拉选项，支持多表联动和条件筛选。

> **与「默认值=查询工作表」区分：** 两者配置弹窗**同名「查询工作表设置」但产出不同配置**——本节的选项数据源配置写 `options.linkDataConfig`（含 `sortType`，无 operation 聚合，条件可为空）；默认值的查询工作表写 `advancedSetting.defaultValue.type="linkage"`（含 `operation` 聚合，条件至少一条），见 `desform-linkage-query.md`。

### 4.1 配置结构

启用方式：在控件设计 JSON 中同时设置 `options.remote = "linkData"` 和 `options.linkDataConfig`。

```json
{
  "options": {
    "remote": "linkData",
    "linkDataConfig": {
      "desformCode": "",       // 【必填】目标工作表编码
      "appId": "",             // 【lowApp必填】应用ID；普通表单留空
      "matchType": "AND",      // 【必填】多条规则匹配方式："AND" | "OR"
      "rules": [],             // 【可选】筛选条件数组，为空 = 不筛选
      "linkages": [            // 【必填，至少1项】联动字段映射
        {
          "model": "",         // 【必填】本表控件自身的 model（即当前 widget.model）
          "linkModel": "",     // 【必填】目标表字段 model — 该字段的去重值作为下拉选项
          "linkName": ""       // 【可选】显示名称
        }
      ],
      "sortType": "OPT_ASC"    // 【必填】排序规则，取值见下方 5.3
    }
  }
}
```

### 4.2 linkDataConfig 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `desformCode` | string | ✅ | 目标工作表编码，选项值从该表单数据中查询 |
| `appId` | string | 半 | lowApp（零代码）模式下必填，填目标应用 ID；普通表单留空 `""` |
| `matchType` | string | ✅ | 多条 rules 的匹配逻辑：`"AND"` 全部满足 / `"OR"` 任一满足 |
| `rules` | array | 否 | 筛选条件数组，为空数组 `[]` 表示无筛选条件 |
| `rules[].model` | string | ✅ | 目标表中参与筛选的字段 model |
| `rules[].rule` | string | ✅ | 匹配规则。合法值：`EQ` `NE` `IN` `NOT_IN` `IS_ONE_OF` `NOT_IS_ONE_OF` `EMPTY` `NOT_EMPTY`。**必须大写** |
| `rules[].valueType` | string | ✅ | `"field"` = 值为本表字段 model / `"fixed"` = 值为固定内容 |
| `rules[].value` | array | ✅ | 值数组。field 模式填本表字段 model 的数组如 `["radio_xxx"]`；fixed 模式填固定值如 `["进行中"]` |
| `rules[].sqParam` | object | — | **不要手工填写**，保存设计 JSON 时脚本自动填充 |
| `linkages` | array | ✅ | 联动字段映射，决定哪个目标表字段作为选项来源，**至少 1 项** |
| `linkages[].model` | string | ✅ | 本表控件自身的 model，即当前 widget.model |
| `linkages[].linkModel` | string | ✅ | 目标表字段 model——该字段的**所有去重值**将被查询回来作为下拉选项 |
| `linkages[].linkName` | string | 否 | 显示名称，用于 UI 展示；含半角括号 `()` 时会以百分号编码（`%28`/`%29`）存储 |
| `sortType` | string | ✅ | 选项排序规则，取值见 5.3 |

### 4.3 sortType 可选值

| 值 | 含义 | 说明 |
|----|------|------|
| `OPT_ASC` | 按选项值升序 | 默认值 |
| `OPT_DESC` | 按选项值降序 | |
| `CT_ASC` | 按创建时间升序 | 非 SQL 适配模式可用 |
| `CT_DESC` | 按创建时间降序 | 非 SQL 适配模式可用 |
| `UT_ASC` | 按更新时间升序 | 非 SQL 适配模式可用 |
| `UT_DESC` | 按更新时间降序 | 非 SQL 适配模式可用 |

### 4.4 运行时行为

1. 表单加载时，检查 `options.linkDataConfig` 是否存在
2. 若 rules 中有 `valueType: "field"` 的引用，watch 这些本表字段值的变化（150ms 防抖）
3. 字段值变化时自动调用后端 API：
   ```
   GET /desform/data/linkData/{desformCode}/getOptions
     ?field={linkages[0].linkModel}
     &sortType={sortType}
     &superQueryString={编码后的超调查询条件}
   ```
4. 接口返回 `{success: true, result: [{value, label}, ...]}`，作为控件选项
5. 非首次加载时（超过 1 秒后触发的查询），会先清空当前已选值再更新选项

### 4.5 与 linkForm 的核心区别

| | linkForm（已过时） | linkData |
|---|---|---|
| 配置字段 | `linkFormCode` + `linkFormField` | `linkDataConfig`（结构化对象） |
| 条件筛选 | ❌ 不支持 | ✅ 支持 rules 条件筛选 |
| 数据获取 | 前端 store 缓存 | 后端 `/desform/data/linkData` API |
| 空查询 | 取全表数据 | 前端不会发无 linkModel 的请求 |

### 4.6 创建表单时的配置方式

**方式一：预处理后手动写入（推荐）**

`desform_creator.py` 的 JSON config 暂不直接支持 `linkDataConfig`。创建表单时：

1. 创建表单时不配置该字段的 options，仅创建带占位选项的控件
2. 使用 `--preprocess` 模式或在创建后手动修改设计 JSON
3. 对目标控件写入完整的 `linkDataConfig` 对象
4. 同时设置 `options.remote = "linkData"`

```json
// 预处理后写入设计 JSON 的控件片段
{
  "key": "select_xxx",
  "type": "select",
  "model": "select_xxx",
  "name": "下拉_查询工作表",
  "options": {
    "remote": "linkData",
    "linkDataConfig": {
      "desformCode": "target_form_code",
      "appId": "",
      "matchType": "AND",
      "rules": [
        {
          "model": "target_field_model",
          "rule": "EQ",
          "valueType": "field",
          "value": ["current_form_field_model"]
        }
      ],
      "linkages": [
        {
          "model": "select_xxx",
          "linkModel": "target_option_field_model",
          "linkName": "选项字段"
        }
      ],
      "sortType": "OPT_ASC"
    },
    "options": []
  }
}
```

> **注意**：`linkDataConfig` 中的 `model`（本表）和 `linkModel`（目标表）都必须填写控件的 **model**（如 `select_1783049626117_649648`），不能填 key 或中文名。创建时 model 未知（含时间戳），因此必须通过预处理方式在拿到 model 后写入。

## 五、远程函数（remote: true）

```json
{
  "options": {
    "remote": true,
    "remoteFunc": "getStatusList"
  }
}
```

需要在前端全局注册对应的函数。适用于自定义接口加载选项。

#### 远程函数注册机制

远程函数通过 `GenerateForm.vue` 的 `remote` prop 传入：

```javascript
// 父组件中
<generate-form :remote="remoteFunctions" />

// remoteFunctions 对象
{
  functionName(resolve) {
    // 异步获取选项数据
    api.get('/your/endpoint').then(res => {
      resolve(res.data.map(item => ({ value: item.id, label: item.name })))
    })
  }
}
```

在控件配置中设置 `remote: true` 和 `remoteFunc: 'functionName'`，表单渲染时自动调用对应函数填充选项。

> **注意：** 远程函数仅在 iframe 内的 Vue2 表单渲染器中生效。通过 Python 工具创建表单时，如需使用远程函数，需在表单的 JS 增强中实现数据加载逻辑。

## 六、对比总结

| 数据源 | remote 值 | 必填参数 | API 调用 | 适用场景 |
|--------|----------|---------|---------|---------|
| 静态选项 | `false` | options[] | 无 | 固定少量选项 |
| 系统字典 | `"dict"` | dictCode, dictOptions | GET /sys/dict/getDictItems | 通用复用选项 |
| 查询工作表 | `"linkData"` | linkDataConfig（含 desformCode, linkages, sortType） | GET /desform/data/linkData/{code}/getOptions | 跨表联动选项+条件筛选 |
| 远程函数 | `true` | remoteFunc | 自定义 | 自定义接口 |

---

## 附：已过时的数据源

### 关联表单（remote: "linkForm"）⚠️ 已过时

> **已过时（Deprecated）**：`remote: "linkForm"` 已被 **查询工作表（linkData）** 取代，新表单**禁止使用**此方式。
> 保留此文档仅用于识别旧表单中的遗留配置——如果你在旧表单中看到 `remote: "linkForm"`，应**提醒用户该配置已过时**，建议迁移为 linkData，**必须经用户确认同意后才能执行迁移**，不可擅自修改。

```json
// ⚠️ 已过时，新表单请使用 linkData
{
  "options": {
    "remote": "linkForm",
    "linkFormCode": "product_form",
    "linkFormField": "product_name"
  }
}
```

选项来自其他工作表指定字段的所有去重值（旧行为）。
