# 控件 Options 完整参考

每种控件的完整 options 配置，生成时按此结构填充。

> **配置某控件前必须先查本文档对应片段**：按 SKILL.md 注入的 `WIDGET_OPTIONS_INDEX` 索引表给出的 `offset` / `limit` 直接 `Read`，只读该片段、勿全量读（注入失败时再用 `grep -n "## <控件type>"` 兜底定位）。

> ⚠️ **2026-09-03 勘误提示**：文末「默认值溯源勘误」一节对照真实前端源码（`componentsConfig.js`）列出了与下方表格不一致的易错点（editor 无 advancedSetting 且宽度仅 100%、phone/email 的 UI 默认宽是 300px、map 的 defaultValue 为注入键、upload 的 multiple/autoWidth 会被 creator 白名单忽略等）。配置前先看文末，**两者冲突时以文末勘误为准**。

## 通用 options 字段

以下字段几乎所有控件都有（下方各控件参数表已逐一列出，此处统一说明含义）：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `required` | boolean | `false` | 是否必填（运行时注入；纯展示类控件如 divider/text 无此项） |
| `disabled` | boolean | `false` | 是否禁用 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏（运行时注入） |
| `fieldNote` | string | `""` | 字段备注（运行时注入） |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

---

## input — 单行文本

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `defaultValue` | string | `""` | 默认值 |
| `placeholder` | string | `""` | 占位提示 |
| `width` | string | `"100%"` | 控件宽度 |
| `required` | boolean | `false` | 是否必填 |
| `disabled` | boolean | `false` | 是否禁用 |
| `readonly` | boolean | `false` | 是否只读 |
| `clearable` | boolean | `false` | 是否显示清除按钮 |
| `unique` | boolean | `false` | 是否唯一校验 |
| `showPassword` | boolean | `false` | 是否密码模式（与 `allowScan` 互斥） |
| `allowScan` | boolean | `false` | 【LHZP-1945】允许扫码输入（APP 端） |
| `scanEditable` | boolean | `true` | 扫码后是否允许修改；`allowScan=true` 时才有意义 |
| `dataType` | string\|null | `null` | 数据类型校验（如 `"email"`、`"url"`） |
| `pattern` | string | `""` | 正则校验表达式 |
| `patternMessage` | string | `""` | 正则校验失败提示 |
| `fillRuleCode` | string | `""` | 填值规则 Code。⛔ 敲敲云属性面板不展示，不要配 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-input` | icon: `icon-input`

## textarea — 多行文本

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `width` | string | `"100%"` | 控件宽度 |
| `defaultValue` | string | `""` | 默认值 |
| `required` | boolean | `false` | 是否必填 |
| `disabled` | boolean | `false` | 是否禁用 |
| `pattern` | string | `""` | 正则校验表达式 |
| `patternMessage` | string | `""` | 正则校验失败提示 |
| `placeholder` | string | `""` | 占位提示 |
| `readonly` | boolean | `false` | 是否只读 |
| `unique` | boolean | `false` | 是否唯一校验 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-textarea` | icon: `icon-textarea`

## number — 数字

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `width` | string | `""` | 控件宽度 |
| `required` | boolean | `false` | 是否必填 |
| `defaultValue` | number | `0` | 默认值 |
| `placeholder` | string | `""` | 占位提示 |
| `precision` | number\|null | `null` | 小数精度：`null`=不限制，`0`=整数，`1`=保留1位小数，以此类推 |
| `controls` | boolean | `false` | 是否显示加减按钮 |
| `min` | number | `0` | 最小值 |
| `minUnlimited` | boolean | `true` | 是否不限制最小值（`true` 时忽略 `min`） |
| `max` | number | `100` | 最大值 |
| `maxUnlimited` | boolean | `true` | 是否不限制最大值（`true` 时忽略 `max`） |
| `step` | number | `1` | 步长 |
| `disabled` | boolean | `false` | 是否禁用 |
| `controlsPosition` | string | `"right"` | 加减按钮位置。仅支持 `null`（两侧）和 `"right"`（右侧），没有 `"left"` |
| `unitText` | string | `""` | 单位文本（如 `"元"`、`"kg"`） |
| `unitPosition` | string | `"suffix"` | 单位位置（`"suffix"`=后缀，`"prefix"`=前缀） |
| `showPercent` | boolean | `false` | 是否显示百分号 |
| `align` | string | `"left"` | 对齐方式（`"left"`/`"center"`/`"right"`） |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-number` | icon: `icon-number`

## integer — 整数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `width` | string | `""` | 控件宽度 |
| `defaultValue` | number\|undefined | `undefined` | 默认值（无默认值，初始为空） |
| `placeholder` | string | `"请输入整数"` | 占位提示 |
| `required` | boolean | `false` | 是否必填 |
| `min` | number | `0` | 最小值 |
| `minUnlimited` | boolean | `true` | 是否不限制最小值（`true` 时忽略 `min`） |
| `max` | number | `100` | 最大值 |
| `maxUnlimited` | boolean | `true` | 是否不限制最大值（`true` 时忽略 `max`） |
| `step` | number | `1` | 步长 |
| `precision` | number | `0` | 小数精度（固定为 `0`，即整数） |
| `controls` | boolean | `true` | 是否显示加减按钮 |
| `disabled` | boolean | `false` | 是否禁用 |
| `controlsPosition` | string | `"right"` | 加减按钮位置。仅支持 `null`（两侧）和 `"right"`（右侧），没有 `"left"` |
| `unitText` | string | `""` | 单位文本 |
| `unitPosition` | string | `"suffix"` | 单位位置（`"suffix"`=后缀，`"prefix"`=前缀） |
| `showPercent` | boolean | `false` | 是否显示百分号 |
| `align` | string | `"left"` | 对齐方式（`"left"`/`"center"`/`"right"`) |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-integer` | icon: `icon-integer`

## money — 金额

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `width` | string | `"180px"` | 控件宽度 |
| `defaultValue` | number\|undefined | `undefined` | 默认值（无默认值，初始为空） |
| `placeholder` | string | `"请输入金额"` | 占位提示 |
| `required` | boolean | `false` | 是否必填 |
| `unitText` | string | `"元"` | 单位文本 |
| `unitPosition` | string | `"suffix"` | 单位位置（`"suffix"`=后缀，`"prefix"`=前缀） |
| `precision` | number | `2` | 小数精度（默认保留2位小数） |
| `hidden` | boolean | `false` | 是否隐藏 |
| `disabled` | boolean | `false` | 是否禁用 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-money` | icon: `icon-money`

## ⚠️ 选项颜色（itemColor）合法值约束

**强制规则：** 所有控件（radio / select / checkbox）的 `itemColor` 字段只能使用以下 20 个值，这是前端硬编码的颜色表，传入**其他任何值都会导致脚本报错**。

| 色号 | 十六进制 | 文字色 | 预览 |
|------|---------|--------|------|
| 1 | `#2196F3` | 白色 | 蓝色 |
| 2 | `#08C9C9` | 白色 | 青色 |
| 3 | `#00C345` | 白色 | 绿色 |
| 4 | `#FAD714` | 深色 | 黄色 |
| 5 | `#FF9300` | 白色 | 橙色 |
| 6 | `#F52222` | 白色 | 红色 |
| 7 | `#EB2F96` | 白色 | 粉红 |
| 8 | `#7500EA` | 白色 | 深紫 |
| 9 | `#2D46C4` | 白色 | 深蓝 |
| 10 | `#484848` | 白色 | 深灰 |
| 11 | `#C9E6FC` | 深色 | 浅蓝 |
| 12 | `#C3F2F2` | 深色 | 浅青 |
| 13 | `#C2F1D2` | 深色 | 浅绿 |
| 14 | `#FEF6C6` | 深色 | 浅黄 |
| 15 | `#FFE5C2` | 深色 | 浅橙 |
| 16 | `#FDCACA` | 深色 | 浅红 |
| 17 | `#FACDE6` | 深色 | 浅粉 |
| 18 | `#DEC2FA` | 深色 | 浅紫 |
| 19 | `#CCD2F1` | 深色 | 浅靛 |
| 20 | `#D3D3D3` | 深色 | 浅灰 |

**同时必须设置 `useColor: true`**，否则颜色不生效。

---

## radio — 单选框组

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `options` | array | `[]` | 选项列表，每项 `{value, label?, itemColor}`；**静态选项必填**。`label` 默认可省略（显示 `value`）；**`showLabel=true` 时 `label` 必须提供**，否则显示为空 |
| `defaultValue` | string | `""` | 默认值 |
| `width` | string | `""` | 控件宽度 |
| `required` | boolean | `false` | 是否必填 |
| `disabled` | boolean | `false` | 是否禁用 |
| `inline` | boolean\|string | `true` | 选项排列方式：`true`=横排，`false`=竖排，`"matrix"`=矩阵布局（配合 `matrixWidth` 设置每列宽度） |
| `showLabel` | boolean | `false` | 选项是否显示 label 文本；设为 `true` 时 `options` 每项必须提供 `label`，否则显示为空 |
| `showType` | string | `"default"` | 显示风格：`"default"`=普通样式，`"border"`=边框样式 |
| `matrixWidth` | number | `120` | 矩阵布局下每列宽度（px），仅 `inline="matrix"` 时生效 |
| `useColor` | boolean | `false` | 启用选项颜色（需同时在 `options[].itemColor` 设置合法颜色值） |
| `remote` | boolean\|string | `false` | 数据来源：`false`=静态，`"dict"`=系统字典 |
| `dictCode` | string | — | 字典编码（`remote="dict"` 时填写） |
| `dictOptions`（顶层） | array | — | 与 `options` 同级，字典项 `{value,label}` 数组快照（`remote="dict"` 时建议提供，完整用法见下方 [radio / checkbox / select 使用系统字典](#radio--checkbox--select-使用系统字典三者通用) 一节） |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-radio` | icon: `icon-radio-active`

**radio 的 advancedSetting.defaultValue 需要 `valueSplit: ",", customConfig: true`**

## checkbox — 多选框组

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `options` | array | `[]` | 选项列表，每项 `{value, label?, itemColor}`；**静态选项必填**。`label` 默认可省略（显示 `value`）；**`showLabel=true` 时 `label` 必须提供**，否则显示为空 |
| `defaultValue` | array | `[]` | 默认选中值（数组） |
| `width` | string | `""` | 控件宽度 |
| `required` | boolean | `false` | 是否必填 |
| `disabled` | boolean | `false` | 是否禁用 |
| `inline` | boolean\|string | `true` | 选项排列方式：`true`=横排，`false`=竖排，`"matrix"`=矩阵布局（配合 `matrixWidth` 设置每列宽度） |
| `showLabel` | boolean | `false` | 选项是否显示 label 文本；设为 `true` 时 `options` 每项必须提供 `label`，否则显示为空 |
| `showType` | string | `"default"` | 显示风格：`"default"`=普通样式，`"border"`=边框样式 |
| `matrixWidth` | number | `120` | 矩阵布局下每列宽度（px），仅 `inline="matrix"` 时生效 |
| `useColor` | boolean | `false` | 启用选项颜色（需同时在 `options[].itemColor` 设置合法颜色值） |
| `remote` | boolean\|string | `false` | 数据来源：`false`=静态，`"dict"`=系统字典 |
| `dictCode` | string | — | 字典编码（`remote="dict"` 时填写） |
| `dictOptions`（顶层） | array | — | 与 `options` 同级，字典项 `{value,label}` 数组快照（`remote="dict"` 时建议提供，完整用法见下方 [radio / checkbox / select 使用系统字典](#radio--checkbox--select-使用系统字典三者通用) 一节） |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-checkbox` | icon: `icon-checkbox`

**checkbox 的 advancedSetting.defaultValue 需要 `valueSplit: ",", customConfig: true`**

## select — 下拉选择框

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `options` | array | `[]` | 选项列表，每项 `{value, label?, itemColor}`；**静态选项必填**。`label` 默认可省略（显示 `value`）；**`showLabel=true` 时 `label` 必须提供**，否则显示为空 |
| `defaultValue` | string | `""` | 默认值 |
| `placeholder` | string | `""` | 占位提示 |
| `width` | string | `""` | 控件宽度 |
| `multiple` | boolean | `false` | 是否多选 |
| `required` | boolean | `false` | 是否必填 |
| `disabled` | boolean | `false` | 是否禁用 |
| `clearable` | boolean | `true` | 是否显示清除按钮 |
| `filterable` | boolean | `false` | 是否可搜索过滤 |
| `showLabel` | boolean | `false` | 选项是否显示 label 文本；设为 `true` 时 `options` 每项必须提供 `label`，否则显示为空 |
| `showType` | string | `"default"` | 显示风格（`default`/`tag`） |
| `useColor` | boolean | `false` | 启用选项颜色（需同时设置 `itemColor`，颜色值见颜色约束表） |
| `remote` | boolean\|string | `false` | 数据来源：`false`=静态，`"dict"`=系统字典 |
| `dictCode` | string | — | 字典编码（`remote="dict"` 时填写） |
| `dictOptions`（顶层） | array | — | 与 `options` 同级，字典项 `{value,label}` 数组快照（`remote="dict"` 时建议提供，完整用法见下方 [radio / checkbox / select 使用系统字典](#radio--checkbox--select-使用系统字典三者通用) 一节） |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-select` | icon: `icon-select`

**select 的 advancedSetting.defaultValue 需要 `valueSplit: ",", customConfig: true`**

## radio / checkbox / select 使用系统字典（三者通用）

以上 radio、checkbox、select 三个控件使用系统字典的方式完全一致：把 `options.remote` 设为 `"dict"`、填 `options.dictCode`、并在**控件顶层**（与 `options` 同级）写 `dictOptions` 作为字典项映射快照。同时建议 `options.showLabel: true` 以显示文本。

```json
{
  "options": {
    "remote": "dict",
    "dictCode": "sys_user_sex",
    "showLabel": true
  },
  "dictOptions": [
    { "value": "1", "label": "男" },
    { "value": "2", "label": "女" }
  ]
}
```

- `dictOptions`：顶层字段，字典 `{value, label}` 数组。运行时组件会按 `dictCode` 自动从后端拉取并回填，但持久化时应一并保存以保证列表页/详情页能正确翻译。
- `remoteOptions: []` / `props: {value,label}` 是组件 default options 自带的内部占位字段。手工精简构造时可省略（不影响功能）；用 `desform_utils.py` 脚本生成时会自动带上，无需关心。

## date — 日期选择器

先选 `designType`（日期 / 日期时间），再选 `type`（显示类型）。敲敲云源码 `dateTypeOptions`（LHZP-322）：

| designType | type | 显示名 | 默认 format | 备注 |
|------------|------|--------|-------------|------|
| `date` | `year` | 年份 | `yyyy` | |
| `date` | `month` | 年-月 | `yyyy-MM` | |
| `date` | `quarter` | 年-季度 | `yyyy-[Q]Q` | **格式锁定**；存该季度 1 日 0 点时间戳 |
| `date` | `week` | 年-周 | `yyyy-WW周` | **格式锁定**；取 ISO 周周一 |

**⚠️ 周期档位通用值规则（贯穿所有存值场景）**：年-月 / 年-季度 / 年-周等（`type` ∈ `month`/`quarter`/`week`，`designType=date`）值一律存**周期起始日的毫秒时间戳**（2026-09 → `1788192000000`、2026-Q3 → `1782835200000`），界面才按 `format` 格式化为 `2026-09` / `2026-Q3` / `2026-36周`。此规则贯穿：**数据落库（`_dictText` 为格式化文案）、固定默认值、linkData/查询默认值、关联记录 filters/sqParam 固定值**——以上场景都不要写格式化字符串（2026-09-09 实测：filters 固定值写 `"2026-Q3"` 面板不显示值）。**例外：筛选条件值（高级查询 `queryItems`、数据过滤 `conditions`）用格式化字符串、不用时间戳**（2026-09-10 用户确认；规则见 `desform-filter-rules.md`「日期字段」）。
| `date` | `date` | 年-月-日（默认） | `yyyy-MM-dd` | |
| `datetime` | `datetime_s` | 年-月-日 时 | `yyyy-MM-dd HH` | |
| `datetime` | `datetime_sf` | 年-月-日 时:分 | `yyyy-MM-dd HH:mm` | |
| `datetime` | `datetime` | 年-月-日 时:分:秒 | `yyyy-MM-dd HH:mm:ss` | |

⛔ 敲敲云**不要**用 `daterange` / `dates` / `datetimerange`（仅普通设计器兼容老数据）。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `defaultValue` | string | `""` | 默认值 |
| `defaultValueType` | number | `1` | `1`=选择值，`2`=输入值；⚠️ `3`（当前系统时间）**已禁用勿写**（2026-09-08：功能可用但设计器面板不回显）→ 默认当前时间用高级默认值 `compose $_CONTEXT_VAR_sysDate$` / `function DATENOW()`，`defaultValueType` 保持 `1`，见 desform-default-value.md「date — 默认值类型」 |
| `readonly` | boolean | `false` | 是否只读 |
| `disabled` | boolean | `false` | 是否禁用 |
| `editable` | boolean | `true` | 是否可手动输入 |
| `clearable` | boolean | `true` | 是否显示清除按钮 |
| `placeholder` | string | `""` | 占位提示 |
| `startPlaceholder` | string | `""` | 范围选择时开始占位提示（敲敲云不用） |
| `endPlaceholder` | string | `""` | 范围选择时结束占位提示（敲敲云不用） |
| `designType` | string | `"date"` | `date` 或 `datetime` |
| `type` | string | `"date"` | 见上表 |
| `format` | string | `"yyyy-MM-dd"` | 随 `type` 切换；quarter/week 不可改 |
| `timestamp` | boolean | `true` | 是否时间戳存储。敲敲云属性面板不展示此开关（year 除外） |
| `required` | boolean | `false` | 是否必填 |
| `width` | string | `""` | 控件宽度 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-date` | icon: `icon-date`

JSON：`{"name": "入职日期", "type": "date"}` 或 `{"name": "所属季度", "type": "date", "dateType": "quarter"}`。Python：`DATE('所属季度', date_type='quarter')`。

## time — 时间选择器

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `defaultValue` | string | `""` | 默认值 |
| `inputDefVal` | boolean | `false` | 是否使用输入默认值 |
| `readonly` | boolean | `false` | 是否只读 |
| `disabled` | boolean | `false` | 是否禁用 |
| `editable` | boolean | `true` | 是否可手动输入 |
| `clearable` | boolean | `true` | 是否显示清除按钮 |
| `placeholder` | string | `""` | 占位提示 |
| `startPlaceholder` | string | `""` | 范围选择时开始占位提示 |
| `endPlaceholder` | string | `""` | 范围选择时结束占位提示 |
| `isRange` | boolean | `false` | 是否为时间范围选择 |
| `arrowControl` | boolean | `false` | 是否使用箭头控制时间 |
| `format` | string | `"HH:mm:ss"` | 时间格式 |
| `required` | boolean | `false` | 是否必填 |
| `width` | string | `""` | 控件宽度 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-time` | icon: `icon-time`

## switch — 开关

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `defaultValue` | boolean | `false` | 默认值 |
| `required` | boolean | `false` | 是否必填 |
| `disabled` | boolean | `false` | 是否禁用 |
| `activeValue` | string | `"Y"` | 开启时的值 |
| `inactiveValue` | string | `"N"` | 关闭时的值 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-switch` | icon: `icon-switch`

## rate — 评分

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `defaultValue` | number\|null | `null` | 默认值（`null` 时渲染为 0 星，运行时等效于 0） |
| `max` | number | `5` | 最大星数 |
| `disabled` | boolean | `false` | 是否禁用 |
| `allowHalf` | boolean | `false` | 是否允许半星 |
| `required` | boolean | `false` | 是否必填 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-rate` | icon: `icon-rate`

**rate 有 defaultRules：**
```json
"defaultRules": [{ "type": "validator", "message": "", "trigger": "change" }]
```

## color — 颜色选择器

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `defaultValue` | string | `""` | 默认值 |
| `disabled` | boolean | `false` | 是否禁用 |
| `showAlpha` | boolean | `false` | 是否支持透明度选择 |
| `required` | boolean | `false` | 是否必填 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-color` | icon: `icon-color`

## slider — 滑块

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `defaultValue` | number | `0` | 默认值 |
| `disabled` | boolean | `false` | 是否禁用 |
| `required` | boolean | `false` | 是否必填 |
| `min` | number | `0` | 最小值 |
| `max` | number | `100` | 最大值 |
| `step` | number | `1` | 步长 |
| `showInput` | boolean | `false` | 是否显示输入框 |
| `showPercent` | boolean | `false` | 是否显示百分号 |
| `range` | boolean | `false` | 是否为范围选择 |
| `width` | string | `""` | 控件宽度 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-slider` | icon: `icon-slider`

## phone — 手机

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `width` | string | `"300px"` | 控件宽度 |
| `defaultValue` | string | `""` | 默认值 |
| `required` | boolean | `false` | 是否必填 |
| `placeholder` | string | `""` | 占位提示 |
| `readonly` | boolean | `false` | 是否只读 |
| `disabled` | boolean | `false` | 是否禁用 |
| `unique` | boolean | `false` | 是否唯一校验 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `showVerifyCode` | boolean | `false` | 是否显示验证码 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-input-phone` | icon: `icon-mobile-phone`

**phone 有 defaultRules：**
```json
"defaultRules": [
  { "type": "phone", "message": "请输入正确的手机号码" },
  { "type": "validator", "message": "", "trigger": "blur" }
]
```

## email — 邮箱

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `width` | string | `"300px"` | 控件宽度 |
| `defaultValue` | string | `""` | 默认值 |
| `required` | boolean | `false` | 是否必填 |
| `placeholder` | string | `""` | 占位提示 |
| `readonly` | boolean | `false` | 是否只读 |
| `disabled` | boolean | `false` | 是否禁用 |
| `unique` | boolean | `false` | 是否唯一校验 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `showVerifyCode` | boolean | `false` | 是否显示验证码 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-input-email` | icon: `icon-email`

**email 有 defaultRules：**
```json
"defaultRules": [
  { "type": "email", "message": "请输入正确的邮箱地址" },
  { "type": "validator", "message": "", "trigger": "blur" }
]
```

## imgupload — 图片上传

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `defaultValue` | array | `[]` | 默认值 |
| `size` | object | `{"width":100,"height":100}` | 图片尺寸限制 |
| `width` | string | `""` | 控件宽度 |
| `tokenFunc` | string | `"funcGetToken"` | 获取 token 的函数名 |
| `token` | string | `""` | 上传 token |
| `domain` | string | `"http://img.h5huodong.com"` | 图片域名 |
| `disabled` | boolean | `false` | 是否禁用 |
| `length` | number | `9` | 最大上传数量 |
| `multiple` | boolean | `true` | 是否多选上传 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `required` | boolean | `false` | 是否必填 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-tupian` | icon: `icon-tupian`

## file-upload — 文件上传

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `defaultValue` | array | `[]` | 默认值 |
| `token` | string | `""` | 上传 token |
| `length` | number | `0` | 最大上传数量（0=不限） |
| `drag` | boolean | `false` | 是否支持拖拽上传 |
| `listStyleType` | string | `"card"` | 列表展示样式 |
| `multiple` | boolean | `false` | 是否多选上传 |
| `multipleDown` | boolean | `true` | 是否支持批量下载 |
| `disabled` | boolean | `false` | 是否禁用 |
| `buttonText` | string | `"点击上传文件"` | 上传按钮文本 |
| `tokenFunc` | string | `"funcGetToken"` | 获取 token 的函数名 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `required` | boolean | `false` | 是否必填 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-file-upload` | icon: `icon-shangchuan`

## editor — 富文本编辑器

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `defaultValue` | string | `""` | 默认值 |
| `width` | string | `"100%"` | 控件宽度 |
| `disabled` | boolean | `false` | 是否禁用 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `required` | boolean | `false` | 是否必填 |
| `fieldNote` | string | `""` | 字段备注 |

className: `form-editor` | icon: `icon-fuwenbenkuang`

> **不需要 card 容器，无 autoWidth 字段**

## markdown — Markdown 编辑器

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `defaultValue` | string | `""` | 默认值 |
| `width` | string | `"100%"` | 控件宽度 |
| `height` | number | `300` | 编辑器高度（px） |
| `viewerAutoHeight` | boolean | `false` | 查看模式自动高度 |
| `disabled` | boolean | `false` | 是否禁用 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `required` | boolean | `false` | 是否必填 |
| `fieldNote` | string | `""` | 字段备注 |

className: `form-markdown` | icon: `icon-markdown`

> **不需要 card 容器，无 autoWidth 字段**

## buttons — 按钮

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `text` | string | `"按钮"` | 按钮文本 |
| `icon` | string | `""` | 按钮图标 |
| `type` | string | `"default"` | 按钮类型（`default`/`primary`/`success`/`warning`/`danger`/`info`） |
| `btnSize` | string | `"default"` | 按钮尺寸（`default`/`medium`/`small`/`mini`） |
| `plain` | boolean | `false` | 是否朴素按钮 |
| `round` | boolean | `false` | 是否圆角按钮 |
| `circle` | boolean | `false` | 是否圆形按钮 |
| `disabled` | boolean | `false` | 是否禁用 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `required` | boolean | `false` | 是否必填 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-buttons` | icon: `icon-btn2` | hideLabel: `true`

**buttons 有 event 字段：**
```json
"event": { "click": "console.log('hello,world!')" }
```

## text — 文本

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `text` | string | `"这里是一段文本"` | 显示文本内容 |
| `width` | string | `"100%"` | 控件宽度 |
| `align` | string | `"left"` | 水平对齐（`left`/`center`/`right`） |
| `verticalAlign` | string | `"top"` | 垂直对齐（`top`/`middle`/`bottom`） |
| `fontSize` | number | `16` | 字号（px） |
| `lineHeight` | string | `""` | 行高 |
| `fontColor` | string | `"#4c4c4c"` | 字体颜色 |
| `fontBold` | boolean | `false` | 是否加粗 |
| `fontItalic` | boolean | `false` | 是否斜体 |
| `fontUnderline` | boolean | `false` | 是否下划线 |
| `fontLineThrough` | boolean | `false` | 是否删除线 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `required` | boolean | `false` | 是否必填 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-text` | icon: `icon-text` | hideLabel: `true`

## divider — 分隔符

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `heightNumber` | number | `48` | 分隔符高度（px） |
| `type` | string | `"horizontal"` | 分隔线方向（`horizontal`/`vertical`） |
| `text` | string | `""` | 分隔线文本 |
| `position` | string | `"center"` | 文本位置（`left`/`center`/`right`） |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `required` | boolean | `false` | 是否必填 |
| `fieldNote` | string | `""` | 字段备注 |

className: `form-divider` | icon: `icon-divider` | hideLabel: `true` | formItemMargin: `true`

> **不需要 card 容器，无 autoWidth 字段**

> ⚠️ **2026-09-14 实测：整单 `save_design_from_file` 会把 divider 的 `options.text` 从 `name` 自动重填**（在整单 JSON 里写 `text:''` 落库后仍变回 name，如 name=分隔符1 则显示"分隔符1"）。要清空/改分隔线文案**必须走 `update_widget(code, {'options': {'text': ''}}, key=...)` 单点写入**再 `query_form` 回查；delete_widget 可整控件删除。job 建表时 divider 的 name 会被忽略、用 `text`，但整单补丁路径不受此保护。

## area-linkage — 省市级联动

源码默认配置（2026-09-01 对照前端）：

```javascript
{
  type: 'area-linkage',
  name: '省市级联动',
  className: 'form-area-linkage',
  icon: 'icon-jilianxuanze',
  hideTitle: false,
  options: {
    width: '',
    placeholder: '请选择',
    // 选择级别：1 = 省，2 = 省市，3 = 省市区
    areaLevel: 3,
    defaultValue: "",
    clearable: true,
    disabled: false,
    hidden: false,
  }
}
```

`hideTitle: false` 在控件顶层（与 `type`/`name` 同级），`make_widget` 已默认写入。`AREA()` 工厂还会注入运行时通用字段 `hiddenOnAdd`/`required`/`fieldNote`/`autoWidth`（源码 default options 不含这四项）。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `width` | string | `""` | 控件宽度 |
| `placeholder` | string | `"请选择"` | 占位提示 |
| `areaLevel` | number | `3` | 选择级别：`1`=省，`2`=省市，`3`=省市区（默认） |
| `defaultValue` | string | `""` | 默认值。**只填最后一级区划代码**（见下方），不要填 `"110000,110100,110101"` |
| `clearable` | boolean | `true` | 是否显示清除按钮 |
| `disabled` | boolean | `false` | 是否禁用 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏（运行时注入） |
| `required` | boolean | `false` | 是否必填（运行时注入） |
| `fieldNote` | string | `""` | 字段备注（运行时注入） |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行；运行时注入） |

className: `form-area-linkage` | icon: `icon-jilianxuanze`

JSON 配置用 `"areaLevel": 1|2|3`（映射到 `AREA(level=...)`）。Python 直接调 `AREA('所在地区', level=2)`。

**写入/存储值（实测 2026-09-01）：** 字段值只存**最后一级**区划代码，哪一级由 `areaLevel` 决定。前端据此翻译 `*_dictText`。

| areaLevel | 含义 | 写入值示例 | dictText 示例 |
|-----------|------|------------|---------------|
| `1` | 省 | `"110000"` | `北京市` |
| `2` | 省市 | `"110100"` | `北京市/北京市` |
| `3` | 省市区（默认） | `"110101"` | `北京市/北京市/东城区` |

完整写法见 `desform-data-utils.md`「area-linkage 字段值格式」。

## category-linkage — 联动

⛔ **本 skill 禁止新建**（敲敲云需屏蔽）。主表、子表都不允许使用，不要生成该控件。

【LHZP-229】源码有此控件，但敲敲云 skill 不使用。**不是**省市 `area-linkage`。

源码默认：

```javascript
{
  type: 'category-linkage',
  name: '联动',
  className: 'form-category-linkage',
  icon: 'icon-liandong',
  hideTitle: false,
  options: {
    defaultValue: [],
    width: '100%',
    placeholder: '请选择',
    required: false,
    disabled: false,
    clearable: true,
    hidden: false,
    category: {
      table: '',
      txt: '',
      key: '',
      level: 3,
      idField: '',
      pidField: '',
      condition: '',
    },
  },
}
```

运行时请求 `/online/cgform/api/querySelectOptions`，`emitPath: true`，值是**整条路径数组**。`*_dictText` 为各级 label 用 `/` 拼接。移动端最多 3 层。子表清单含此类型，但 **不允许使用**。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `defaultValue` | array | `[]` | 路径数组，如 `["p1","c1"]` |
| `width` | string | `"100%"` | 控件宽度 |
| `placeholder` | string | `"请选择"` | 占位提示 |
| `required` | boolean | `false` | 是否必填 |
| `disabled` | boolean | `false` | 是否禁用 |
| `clearable` | boolean | `true` | 是否可清除 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `category.table` | string | `""` | **必填** 数据表名，禁止猜测 |
| `category.txt` | string | `""` | 显示字段 |
| `category.key` | string | `""` | 存储字段 |
| `category.idField` | string | `""` | ID 字段 |
| `category.pidField` | string | `""` | 父 ID 字段 |
| `category.level` | number | `3` | 联动层级 1–10；移动端最多 3 |
| `category.condition` | string | `""` | 仅第一层的根级条件 |

⛔ 禁止通过 JSON / `CATEGORY_LINKAGE()` 新建。已有表单若含此字段，值是路径数组。

## map — 地图

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `width` | string | `"100%"` | 控件宽度 |
| `height` | string | `"300px"` | 地图高度 |
| `zoom` | number | `15` | 缩放级别 |
| `point` | object | `{"lng":116.397467,"lat":39.908806}` | 默认中心点经纬度 |
| `mapSettings` | object | `{"dragging":true,"scrollWheelZoom":true,"doubleClickZoom":true,"keyboard":false,"inertialDragging":true,"continuousZoom":true,"pinchToZoom":true}` | 地图交互设置 |
| `mapControls` | object | `{"navigation":true,"geolocation":true,"scale":true,"mapType":true,"panorama":false,"overviewMap":false}` | 地图控件开关 |
| `disabled` | boolean | `false` | 是否禁用 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `required` | boolean | `false` | 是否必填 |
| `fieldNote` | string | `""` | 字段备注 |
| `defaultValue` | string | `"116.397467,39.908806"` | 默认值（经度,纬度） |

className: `form-map` | icon: `icon-map`

> **不需要 card 容器，无 autoWidth 字段**

## location — 定位

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `width` | string | `"100%"` | 控件宽度 |
| `defaultValue` | string | `""` | 默认值 |
| `defaultCurrent` | boolean | `false` | 是否默认定位当前位置 |
| `showLngLat` | boolean | `false` | 是否显示经纬度 |
| `showMap` | boolean | `false` | 是否显示地图 |
| `disabled` | boolean | `false` | 是否禁用 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `required` | boolean | `false` | 是否必填 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-location` | icon: `icon-location`

## capital-money — 大写金额

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `moneyWidgetKey` | string | `""` | 关联的 money 控件的 key，自动将金额转大写 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-money` | icon: `icon-money`

## barcode — 条码

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `maxWidth` | number | `180` | 最大宽度（px） |
| `codeType` | string | `"barcode"` | 码类型：`"barcode"`（条码）或 `"qrcode"`（二维码） |
| `sourceModel` | string | `""` | 数据源字段 model |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-barcode` | icon: `icon-tiaoma`

## text-compose — 文本组合

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `expression` | string | `""` | 组合表达式 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-text-compose` | icon: `icon-zuhe`

## auto-number — 自动编号

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `numberRules` | array | `[{type:"number",mode:1,start:1,reset:0,length:4,continue:false}]` | 编号规则数组，每项结构见下方表格 |
| `generateOnAdd` | boolean | `true` | 新增时自动生成编号 |
| `placeholder` | string | `"${title}自动生成，不需要填写"` | 占位提示 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-auto-number` | icon: `icon-hashtag`

**numberRules[] 元素结构**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | string | 规则类型：`"number"` 序号 / `"create_date"` 日期 / `"text"` 固定文本 / `"field"` 字段引用 |
| `mode` | number | number 时：`1` = 自然数（1,2,3...），`2` = 指定位数（0001,0002...） |
| `start` | number | number 时：起始值（默认 1） |
| `reset` | number | number 时：重置规则 `0`=不重置 / `1`=每天 / `2`=每周 / `3`=每月 / `4`=每年 |
| `length` | number | number 时（mode=2）：指定位数（如 4 → 0001） |
| `continue` | boolean | number 时（mode=2）：超出指定位数时是否继续递增 |
| `dateFormat` | string | create_date 时：日期格式（如 `"yyyyMMdd"`） |
| `value` | string | text 时：固定文本内容；field 时：引用字段 model |

## select-user — 用户组件

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `keyMaps` | array | `[]` | 选择用户后自动回填其他字段，每项 `{from, to}`（from 可选值见下方表格） |
| `defaultValue` | string | `""` | 默认值 |
| `defaultLogin` | boolean | `false` | 默认填充当前登录用户（仅 add/preview 模式生效） |
| `placeholder` | string | `""` | 占位提示 |
| `width` | string | `"100%"` | 控件宽度 |
| `multiple` | boolean | `false` | 是否多选 |
| `disabled` | boolean | `false` | 是否禁用 |
| `customReturnField` | string | `"username"` | 存储字段（`username`=用户名，`realname`=真实姓名等） |
| `hidden` | boolean | `false` | 是否隐藏 |
| `dataAuthType` | string | `"member"` | 权限（radio）：`member`=成员（默认）/ `owner`=拥有者 / `storage`=仅用于存储数据 |
| `allowCurrLogin` | boolean | `false` | 弹窗中是否显示"当前登录用户"快捷选项 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `required` | boolean | `false` | 是否必填 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-select-user` | icon: `icon-user-circle`

**keyMaps `from` 可用值：**

| from 值         | 说明            | 示例值                           |
|-----------------|-----------------|----------------------------------|
| `id`            | 用户ID          | e9ca23d68d884d4ebb19d07889727dae |
| `username`      | 用户名          | zhangsan                         |
| `realname`      | 真实姓名        | 张三                             |
| `avatar`        | 头像地址        | xxx.png                          |
| `birthday`      | 生日            | 1990-7-11                        |
| `sex`           | 性别(1=男 2=女) | 1                                |
| `sex_dictText`  | 性别字典文本    | 男                               |
| `email`         | 邮箱地址        | zhangsan@xx.com                  |
| `phone`         | 电话号码        | 150xxxxxxxx                      |
| `orgCode`       | 机构编码        | A001                             |
| `status`        | 状态            | 1                                |
| `status_dictText` | 状态字典文本  | 正常                             |
| `createTime`    | 用户创建时间    | 2018-12-21 17:54:10              |
| `workNo`        | 工号            | A0001                            |
| `orgCode`       | 所属部门编码    | A01                              |
| `orgCodeTxt`    | 所属部门名称(翻译值) | 北京国炬软件信息            |
| `post`          | 职务编码        | manager                          |
| `postText`      | 职务名称(翻译值) | 项目经理                        |
| `telephone`     | 座机            | 010-xxxxxxx                      |
| `positionType_dictText` | 职级字典文本 | 高级                         |

> **`from` 实际支持的字段比上表更全**：凡是 `/sys/user/list` 返回的 `result.records[0]` 里出现的字段名都可用（包含 `xxx_dictText` 翻译后缀字段）。需要带出"部门名/职务名"等展示文本时，优先用 `orgCodeTxt`/`postText` 这类翻译值，而不是 `orgCode`/`post` 编码。不确定字段名时，先 `GET /sys/user/list?username=<某用户>` 查一次确认。

## select-depart — 部门组件

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `multiple` | boolean | `false` | 是否多选 |
| `required` | boolean | `false` | 是否必填 |
| `disabled` | boolean | `false` | 是否禁用 |
| `placeholder` | string | `""` | 占位提示 |
| `width` | string | `"100%"` | 控件宽度 |
| `defaultValue` | string | `""` | 默认值 |
| `defaultLogin` | boolean | `false` | 默认填当前登录用户所在部门 |
| `customReturnField` | string | `"id"` | 存储字段（`id`=部门ID，`orgCode`=机构编码，`departName`=部门名称） |
| `dataAuthType` | string | `"member"` | 权限（radio）：`member`=成员（默认）/ `owner`=拥有者 / `storage`=仅用于存储数据 |
| `allowCurrLogin` | boolean | `false` | 弹窗中是否显示"当前登录用户的部门"快捷选项 |
| `keyMaps` | array | `[]` | 选择部门后自动回填其他字段，每项 `{from, to}`（from 可选值：id/departName/orgCode/orgType 等，见下方表格） |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

**keyMaps `from` 可用值：**

| from 值 | 说明 |
|---------|------|
| `id` | 部门 ID |
| `departName` | 部门名称 |
| `departNameAbbr` | 缩写 |
| `orgCode` | 机构编码 |
| `orgType` | 机构类型（1=一级，2=子部门） |
| `parentId` | 父机构 ID |
| `address` | 地址 |
| `mobile` | 手机号 |

className: `form-select-depart` | icon: `icon-depart`

**keyMaps[] 元素结构**（数据绑定映射，选择部门后自动回填其他字段）：

```json
[
  { "from": "departName", "to": "input_field_model" },
  { "from": "orgCode",    "to": "any_field_name" }
]
```

- `from`：部门对象的属性名（见下表）
- `to`：回填目标，优先填本表其他字段的 model，也可填任意字段名（无需该字段存在）

**部门组件 from 可用值：**

| from 值          | 说明                       | 示例值                           |
|------------------|----------------------------|----------------------------------|
| `id`             | 机构/部门ID                | c6d7cb4deeac411cb3384b1b31278596 |
| `departName`     | 机构/部门名称              | 北京国炬信息技术有限公司         |
| `departNameAbbr` | 缩写                       |                                  |
| `departNameEn`   | 英文名                     |                                  |
| `departOrder`    | 排序序号                   | 0                                |
| `description`    | 描述                       |                                  |
| `fax`            | 传真                       |                                  |
| `memo`           | 备注                       |                                  |
| `mobile`         | 手机号                     |                                  |
| `address`        | 地址                       |                                  |
| `orgCode`        | 机构编码                   | A01                              |
| `orgType`        | 机构类型 1一级部门 2子部门 | 1                                |
| `parentId`       | 父机构ID                   |                                  |
| `createTime`     | 创建时间                   | 2019-02-11 14:21:51              |

## select-depart-post — 岗位组件

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `keyMaps` | array | `[]` | 选择后自动回填其他字段，每项 `{from, to}` |
| `defaultValue` | string | `""` | 默认值 |
| `defaultLogin` | boolean | `false` | 默认填充当前登录用户所在岗位 |
| `placeholder` | string | `""` | 占位提示 |
| `width` | string | `"100%"` | 控件宽度 |
| `multiple` | boolean | `false` | 是否多选 |
| `disabled` | boolean | `false` | 是否禁用 |
| `customReturnField` | string | `"id"` | 存储字段（`id`=岗位ID） |
| `hidden` | boolean | `false` | 是否隐藏 |
| `dataAuthType` | string | `"member"` | 权限（radio）：`member`=成员（默认）/ `owner`=拥有者 / `storage`=仅用于存储数据 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `required` | boolean | `false` | 是否必填 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-select-depart` | icon: `icon-gangwei`

## org-role — 组织角色

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `defaultValue` | array | `[]` | 默认值（roleCode 数组，**单选也存数组**，如 `["ROmI1Fh2jR"]`，对齐 UI 手选落库） |
| `defaultLogin` | boolean | `false` | 默认填充当前登录用户的组织角色 |
| `placeholder` | string | `"选择组织角色"` | 占位提示 |
| `width` | string | `"100%"` | 控件宽度 |
| `multiple` | boolean | `false` | 是否多选 |
| `disabled` | boolean | `false` | 是否禁用 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `dataAuthType` | string | `"member"` | 权限（radio）：`member`=成员（默认）/ `owner`=拥有者 / `storage`=仅用于存储数据 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `required` | boolean | `false` | 是否必填 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-org-role` | icon: `icon-zuzhijuese`

> ⚠️ `org-role` 存的是 `roleCode`（如 `oa_duty_admin`），不是 `roleId`（UUID）。通过 `GET /sys/role/list` 获取。

## select-tree — 下拉树

⛔ **敲敲云禁用**（QQYUN-3641）。禁止新建。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `dataFrom` | string | `"category"` | 数据来源：`"category"`=分类字典，`"table"`=自定义表树；**必须显式传入** |
| `multiple` | boolean | `false` | 是否多选 |
| `required` | boolean | `false` | 是否必填 |
| `disabled` | boolean | `false` | 是否禁用 |
| `placeholder` | string | `""` | 占位提示 |
| `width` | string | `""` | 控件宽度 |
| `defaultValue` | string | `""` | 默认值 |
| `conf.category.code` | string | `"B02"` | 分类字典编码（`dataFrom="category"` 时使用；**未指定时直接用 `"B02"`，不查 API 不问用户**） |
| `conf.table.name` | string | `""` | 表名（`dataFrom="table"` 时填写） |
| `conf.table.code` | string | `""` | 值字段名 |
| `conf.table.text` | string | `""` | 显示字段名 |
| `conf.table.pidField` | string | `""` | 父节点字段名 |
| `conf.table.rootPid` | string | `""` | 根节点的父字段值（⚠️ 填实际存储值；不确定时填 `""`，**不要填 `"0"`**） |
| `conf.table.leaf` | string | `""` | 叶子节点标识字段 |
| `conf.table.converIsLeafVal` | boolean | `true` | 是否转换叶子节点标识值 |
| `conf.condition` | string | `""` | 节点过滤条件 |
| `conf.conditionOnlyRoot` | boolean | `true` | 过滤条件是否仅作用于根节点 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-select-tree` | icon: `icon-tree`

**dataFrom=table 时 rootPid 踩坑（已验证）：**
- `rootPid` 必须填该表中根节点的 **父字段实际存储值**，不能随意填 `"0"`
- `sys_depart`：根节点 `parent_id` 为空字符串，因此 `rootPid` 必须填 `""`
- 通用规则：不确定时填 `""`（表示顶级节点），**不要**默认填 `"0"`——填了不存在的值会导致树加载为空

**查询分类树节点（用于设置 defaultValue）：**
- `GET /sys/category/rootList?code=B04` — 获取指定分类的根节点列表（返回 `result.records`）
- `GET /sys/category/childList?pid=<节点ID>` — 获取某节点的子节点列表
- `defaultValue` 格式为数组 `['<节点ID>']`（如 `['1456203592097148930']`），不是字符串

## ocr — 文本识别

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `type` | string | `"normal"` | 识别类型：`normal`=通用文字识别，`id_card`=身份证识别，`vat_invoice`=增值税发票识别，`train_ticket`=火车票识别 |
| `fieldMapping` | object | `{}` | 字段映射（默认为空对象）；`type=normal` 时结构为 `{"content":"目标控件model"}`；其他类型为 `{"识别字段key":"目标控件model"}` 的键值对（如身份证的 `{"姓名":"input_xxx","公民身份号码":"input_yyy"}`） |
| `hidden` | boolean | `false` | 是否隐藏 |
| `disabled` | boolean | `false` | 是否禁用 |
| `required` | boolean | `false` | 是否必填 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-ocr` | icon: `icon-ocr-a`

**各识别类型的 fieldMapping 可用 key：**

| type | 可用 key |
|------|---------|
| `normal` | `content`（识别到的全部文字） |
| `id_card` | `姓名`、`民族`、`住址`、`出生`（出生日期）、`性别`、`公民身份号码` |
| `vat_invoice` | `发票种类`、`发票名称`、`发票代码`、`发票号码`、`开票日期`、`密码区`、`购方名称`、`购方纳税人识别号`、`购方地址及电话`、`购方开户行及账号`、`销售方名称`、`销售方纳税人识别号`、`销售方地址及电话`、`销售方开户行及账号`、`合计金额`、`合计税额`、`价税合计_大写`、`价税合计_小写`、`备注`、`收款人`、`复核`、`开票人`、`货物名称`、`规格型号`、`数量`、`单位`、`金额`、`单价`、`税率`、`税额` |
| `train_ticket` | `车票号`、`始发站`、`车次号`、`到达站`、`出发日期`、`时间`、`车票金额`、`席别`、`座位号`、`乘客姓名`、`身份证号`、`序列号`、`售站` |

## summary — 汇总控件

用于汇总子表列数据（如求和、计数等），将子表某一列的聚合结果显示在主表中。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `linkTable` | string | `""` | **汇总源控件**——⚠️ 取值**按控件类型分两种**：<br>① 汇总源是**关联记录**（link-record）→ 填该控件的 **`key`**（如 `1693451000559_843595`），**不是** `link_record_xxx` model；填 model 时设计器解析不了，面板的筛选条件会显示成「**字段已删除**」（2026-09-16 实测：线上参照落库值 `linkTable=1693451000559_843595`，同控件 `model=link_record_1693451000559_843595`）。<br>② 汇总源是**设计子表**（sub-table-design）→ 填子表 **model**（`sub_table_design_xxx`） |
| `field` | string | `""` | 子表列/源表列 model（如 `money_xxx`）。**例外**：`inner-record-count` 时填 `"inner-record-count"`，见下方 |

> **⚠️ `inner-record-count` 的结构与其他汇总不同：**

| 汇总类型 | `field` | `summary` | 说明 |
|---------|---------|-----------|------|
| `inner-record-count` | **`"inner-record-count"`** | **`""`** | 统计子表行数，不引用任何数据列 |
| 其他所有类型 | 子表列 model | `"inner-sum"` / `"inner-average"` / ... | 引用子表具体列 |
| `summary` | string | `""` | **值类**：填汇总类型（如 `"inner-sum"`）；**统计类**：填 `""`（留空） |
| `filter` | object | `(见说明)` | 过滤条件对象，含 `enabled`/`rules`/`matchType`；`enabled: true` 时仅对满足条件的子表行汇总 |
| `filter.enabled` | boolean | `false` | 是否启用过滤 |
| `filter.rules` | array | `[]` | 过滤规则数组，每项含 `model`/`rule`/`valueType`/`value` |
| `filter.matchType` | string | `"AND"` | 多条规则的逻辑关系（`AND`/`OR`） |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `required` | boolean | `false` | 是否必填 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `50` | 宽度百分比（100=整行，50=半行） |

className: `form-summary` | icon: `icon-sigma`

> **⚠️ `inner-record-count` 的结构与其他汇总不同：**

| 汇总类型 | `field` | `summary` | 说明 |
|---------|---------|-----------|------|
| `inner-record-count` | **`"inner-record-count"`** | **`""`** | 统计子表行数，不引用任何数据列 |
| 其他所有类型 | 子表列 model | `"inner-sum"` / `"inner-average"` / ... | 引用子表具体列 |

示例：
```json
// 普通汇总：对子表"小计"列求和
{ "field": "formula_xxx", "summary": "inner-sum" }

// inner-record-count：field 填类型字符串，summary 留空
{ "field": "inner-record-count", "summary": "" }
```

> **⛔ 重要：`type: "summary"` 不支持日期聚合。** `inner-date-earliest` / `inner-date-latest` **不是** `summary` 控件的合法 summary 值。对日期字段做最早/最晚聚合，必须使用**汇总日期**（`type: "date"` + `isSummary: true`），详见下方「汇总日期」章节。两者是完全不同的控件类型，不可混用。
>
> 设计器行为（源码 ConfigItem.vue `onFieldChange`）：数值字段（number/integer/money/summary/formula 且 options.type=number）被选为汇总字段时，汇总类型自动默认为 `inner-sum`。

**汇总类型完整列表（仅 `type: "summary"` 支持）：**

| summary 值 | 说明 | 适用字段类型 |
|------------|------|-------------|
| `inner-sum` | 求和 | 数字/金额/公式 |
| `inner-average` | 平均值 | 数字/金额/公式 |
| `inner-max` | 最大值 | 数字/金额/公式 |
| `inner-min` | 最小值 | 数字/金额/公式 |
| `inner-record-count` | 记录数量 | 任意（`field` 特殊，见上方） |
| `inner-completed-count` | 已填计数 | 任意（统计已填写的行数） |
| `inner-incompletely-count` | 未填计数 | 任意（统计未填写的行数） |
| `oa-leave-duration-calc` | 请假时长（OA 专用） | 请假时间子表 |

**filter 子结构**：
```json
{
  "enabled": true,
  "matchType": "AND",
  "rules": [
    {"model": "子表字段model", "rule": "EQ", "valueType": "fixed", "value": ["固定值"]},
    {"model": "子表字段model", "rule": "EQ", "valueType": "field", "value": ["另一字段model"]},
    {"model": "子表字段model", "rule": "EMPTY", "valueType": "fixed", "value": []},
    {"model": "子表字段model", "rule": "NOT_EMPTY", "valueType": "fixed", "value": []}
  ]
}
```

| 字段 | 说明 |
|------|------|
| `model` | 要过滤的子表字段 model |
| `rule` | 比较规则码 = 前端 `QueryRuleMap` 的键（**无 LIKE**），按组件类别查下方「组件 → 可用规则总表」；无值规则 `EMPTY`/`NOT_EMPTY`/`VALUE_CHANGE` 的 `value` 传 `[]` |
| `valueType` | `fixed`=固定值，`field`=引用其他字段的 model |
| `value` | **始终为数组**，如 `["A类"]`、`[233]`；`EMPTY`/`NOT_EMPTY` 时传 `[]` |
| `matchType` | 多条规则的逻辑关系：`AND` 或 `OR` |

> `filter.rules[].model` 只能是该汇总控件 `options.linkTable` 绑定的那张子表/关联记录里的字段列（设计器「添加筛选条件」下拉 = 该表的列），**禁止引用主表字段或他表字段**；日期汇总的 `field` 同理限该子表内的日期列，filter 的字段则不限列类型（只要在该子表内）。
>
**组件 → 可用规则总表（QueryRuleMap 源码对照，2026-09-03）：**

| 字段类别 | 组件 | 可用规则（码=文案） |
|---------|------|---------------------|
| 文本类 | `input` `textarea` `phone` `email` `editor` `markdown` `barcode` `auto-number` `text-compose`（源码怪癖：`time`、`capital-money` 也算此类） | `EQ`等于 `NE`不等于 `IN`包含 `NOT_IN`不包含 `BEFORE`开头是 `NOT_BEFORE`开头不是 `AFTER`结尾是 `NOT_AFTER`结尾不是 + `EMPTY`/`NOT_EMPTY`/`VALUE_CHANGE` |
| 数值类 | `number` `integer` `money` `slider` `rate` `summary`、`formula`(options.type=number) | `EQ` `NE` `GT`大于 `GE`大于等于 `LT`小于 `LE`小于等于 + `EMPTY`/`NOT_EMPTY`/`VALUE_CHANGE` |
| 日期类 | `date`（options.type ∈ date/datetime/year/month/quarter/week）、`formula`(options.type=date) | `EQ` `NE` `DATE_LT`早于 `DATE_LE`早于等于 `DATE_GT`晚于 `DATE_GE`晚于等于 + `EMPTY`/`NOT_EMPTY`/`VALUE_CHANGE` |
| 单选类 | `radio`、`oa-sign-holiday-select`、`select-user`/`select-depart`/`select-depart-post`/`org-role`(multiple=false)、`select-tree`/`table-dict`(单选)、`link-record`(showMode=single) | `EQ` `NE` `IS_ONE_OF`是其中一个 `NOT_IS_ONE_OF`不是其中一个 + `EMPTY`/`NOT_EMPTY`/`VALUE_CHANGE` |
| 多选类 | `checkbox`、`select`（无论是否多选）、上述人员/部门/岗位/角色(multiple=true)、`select-tree`/`table-dict`(多选)、`link-record`(showMode=many) | `EQ` `NE` `IN_ONE_OF`包含其中一个 `NOT_IN_ONE_OF`不包含任何一个 `IN_ALL_OF`同时包含 + `EMPTY`/`NOT_EMPTY`/`VALUE_CHANGE` |
| 开关 | `switch` | `EQ` `NE` `VALUE_CHANGE`（无 EMPTY） |
| 上传/签名 | `imgupload` `file-upload` `hand-sign`、`sub-table-design` 容器、`link-record`(isSubTable=true) | 仅 `EMPTY` `NOT_EMPTY` `VALUE_CHANGE`（不做文本/数值比较） |

> **以本表为准直接写码**（AI 不必跑脚本）；`scripts/query_rule_map.py` 是同一口径的复刻实现，供脚本内 import 做批量/自动校验，AI 不强制调用。

> **脚本自动解析：** JSON 配置中 `model` 和 `value`（当 `valueType: "field"` 时）支持传入字段中文名，脚本会自动解析为实际 model。

> **典型用法：** 主表需要显示子表某列的合计金额时，使用 `SUMMARY(name, sub_table_model, field_model, summary_type='inner-sum')`，不要用 `FORMULA`。

> **⚠️ `linkTable` 取值由目标控件类型决定（2026-09-04 前端源码核实：WidgetConfigMixins.js `widgetOptions` 每项 `value=控件 key`、`model=控件 model`；JSummary/ConfigItem.vue「关联表」下拉：`sub-table-design` 用 `value=model`，`link-record` 用 `value=key`，`link-record` 且 `showMode=single` 直接过滤不可选）：**
> - 目标=**设计子表**（内部子表）→ `linkTable` 存子表控件 **model**（`sub_table_design_<key>`，与 Python `SUMMARY(name, sub_table_model, ...)` 一致）；
> - 目标=**关联记录 many**（含明细区 link-record+`isSubTable` 的"子表作为单独工作表"样式）→ `linkTable` 必须存**明细控件 key（无前缀）**；若存 `sub_table_design_` 前缀 model，面板 `getFieldOptions` 按 `value===linkTable` 匹配不到（link-record 候选 value=key），汇总字段下拉为空、显示不对——2026-09-04 天脉双应用实测复现（API 写前缀 → 用户反馈"关联表和汇总不对"，改 key 后正常）。复制他表汇总骨架只换 key 后缀，不要改成前缀 model。
> - `field` 一律存被汇总子表/关联表（link-record 时动态查 sourceCode 表）的列 model。
> **⚠️ 必填落库形态（UI 保存，2026-09-04 实测）：** `options.required:true` 且 widget 顶层 `rules:[{"required":true,"message":"${title}必须填写"}]`，两处双写。

## 汇总日期（date + isSummary: true）

**这不是独立的 widget type**，而是对 `date` 控件的特殊化——`type: "date"` + `isSummary: true`，内部通过 `__summary__date` 前缀注册以区分普通日期选择器。汇总日期仅能对子表/关联记录的日期字段做"最早"和"最晚"两种聚合，**不能用于设计子表内部**。

`name` 由 AI 根据字段用途自行设定。显示类型/格式档位对齐前端源码（`WidgetConfigMixins.js` 的 `dateTypeOptions` 与 `onDateTypeChange`，2026-09-03 实测）：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `isSummary` | boolean | `true` | **widget 顶层属性，必须为 `true`**，是区分普通日期选择器的唯一标记 |
| `linkTable` | string | `""` | 关联表 model（仅支持 `sub-table-design` / `link-record` 两种，link-record 需 `showMode=many`） |
| `field` | string | `""` | 汇总的目标字段 model，**必须指向日期类型字段**（`date` 或 `oa-leave-date-select`） |
| `summary` | string | `""` | 汇总方式：**仅 `inner-date-earliest`（最早）或 `inner-date-latest`（最晚）** |
| `designType` | string | `"date"` | 基础档：`date` / `datetime`（汇总日期无面板单选，选择汇总字段时自动同步该字段的 designType） |
| `type` | string | `"date"` | 显示类型（设计器下拉，**存值≠标签**）。`designType=date` 档：`date`（年-月-日）/ `year`（年份）/ `month`（年-月）/ `quarter`（年-季度）/ `week`（年-周）；`designType=datetime` 档：`datetime`（…秒）/ `datetime_s`（…时）/ `datetime_sf`（…分） |
| `format` | string | `"yyyy-MM-dd"` | 日期输出格式，随 `type` 联动：`date`→`yyyy-MM-dd`、`year`→`yyyy`、`month`→`yyyy-MM`、`quarter`→`yyyy-[Q]Q`、`week`→`yyyy-WW周`、`datetime`→`yyyy-MM-dd HH:mm:ss`、`datetime_s`→`yyyy-MM-dd HH`、`datetime_sf`→`yyyy-MM-dd HH:mm`（实现同源码 `onDateTypeChange` 的 switch） |
| `timestamp` | boolean | `true` | **必须为 `true`**，以时间戳存储汇总结果 |
| `defaultValue` | string | `""` | 默认值 |
| `filter` | object | `(见汇总控件)` | 筛选条件对象，结构与普通汇总相同 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |

className: `form-summary-date` | icon: `icon-sigma` | model 前缀: `date_`

```json
{
  "type": "date",
  "name": "汇总日期",
  "className": "form-summary-date",
  "icon": "icon-sigma",
  "isSummary": true,
  "options": {
    "linkTable": "sub_table_design_xxx",
    "field": "date_xxx",
    "summary": "inner-date-earliest",
    "type": "date",
    "designType": "date",
    "format": "yyyy-MM-dd",
    "timestamp": true,
    "defaultValue": "",
    "filter": { "enabled": false, "rules": [], "matchType": "AND" }
  },
  "key": "1783581543074_744661",
  "model": "date_1783581543074_744661"
}
```

汇总日期面板「显示类型」下拉直接写 `options.type` 并按上表联动 `format`（不改 `designType`）；`designType` 只在选择汇总字段（`onFieldChange`）时按目标字段同步。

> **关于 JSON config 中的 `"type": "summary-date"`**：这只是 `desform_creator.py` 的语法糖，内部映射到 `SUMMARY_DATE()` 工厂函数，最终生成的控件 type 仍然是 `"date"`（而非 `"summary-date"`）。系统中不存在 type 为 `"summary-date"` 的控件。
```

**与普通汇总控件的区别：**

| 维度 | 汇总 (`summary`) | 汇总日期 (`date` + `isSummary`) |
|------|-----------------|-------------------------------|
| widget type | `"summary"` | `"date"` |
| className | `"form-summary"` | `"form-summary-date"` |
| model 前缀 | `summary_` | `date_` |
| isSummary | 无 | **必须为 `true`** |
| 可选汇总方式 | sum/avg/max/min/count 等 10 种 | **仅 earliest / latest** |
| 可选字段类型 | 任意（数值字段才支持 sum/avg/max/min） | **仅日期字段** |
| 是否有 type/designType/format/timestamp | 无 | **有** |
| 是否有 defaultValue | 无 | **有** |
| 输出值 | 数值 | **时间戳** |
| 子表内可用 | 是 | **否** |

## sub-table-design — 设计子表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `isWordStyle` | boolean | `false` | 是否 Word 样式 |
| `isWordInnerGrid` | boolean | `false` | 是否 Word 内嵌网格 |
| `gutter` | number | `0` | 列间距 |
| `columnNumber` | number | `2` | 列数 |
| `operationMode` | number | `1` | 操作模式（`1`=表格模式，`2`=卡片模式） |
| `justify` | string | `"start"` | 水平排列方式（`start`/`end`/`center`/`space-around`/`space-between`） |
| `align` | string | `"top"` | 垂直对齐（`top`/`middle`/`bottom`） |
| `defaultValue` | array | `[]` | 默认数据行 |
| `subTableName` | string | `""` | 子表名称 |
| `defaultRows` | number | `0` | 默认行数 |
| `showCheckbox` | boolean | `true` | 是否显示复选框 |
| `showNumber` | boolean | `true` | 是否显示行号 |
| `showRowButton` | boolean | `false` | 是否显示行操作按钮 |
| `allowAdd` | boolean | `true` | 是否允许新增行 |
| `autoHeight` | boolean | `true` | 是否自动高度 |
| `defaultValType` | string | `"none"` | 默认值类型（`none`/`custom`） |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `required` | boolean | `false` | 是否必填 |
| `fieldNote` | string | `""` | 字段备注 |

className: `form-sub-table` | icon: `icon-table`

> **不需要 card 容器。子控件结构见 desform-examples.md**

## formula — 公式

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `type` | string | `"number"` | 公式类型（`number`=数字，`date`=日期） |
| `mode` | string | `"SUM"` | 计算模式，数字：`SUM`/`AVERAGE`/`MAX`/`MIN`/`PRODUCT`/`CUSTOM`；日期：`DATEIF`/`DATEADD`/`NOW_DATEIF`/`PAST_NOW_DATEIF` |
| `expression` | string | `""` | 公式表达式，用 `$model$` 引用字段 |
| `decimal` | number | `2` | 小数位数 |
| `thousand` | boolean | `true` | 是否千分位格式 |
| `percent` | boolean | `false` | 是否百分比显示 |
| `unitPosition` | string | `"suffix"` | 单位位置（`prefix`/`suffix`） |
| `unitText` | string | `""` | 单位文本 |
| `emptyAsZero` | boolean | `true` | 空值是否视为 0 |
| `dateBegin` | string | `""` | 日期模式：开始日期字段引用，**必须写 `$model$` 包裹形态**（如 `"$date_xxx$"`），与 expression 引用同规则 |
| `dateEnd` | string | `""` | 日期模式：结束日期字段引用，同 dateBegin，写 `$model$` 包裹形态 |
| `dateFormatMethod` | number | `1` | 日期模式：格式化方式 |
| `datePrintUnit` | string | `"m"` | 日期模式：输出单位（`y`年/`M`月/`d`天/`h`时/`m`分） |
| `dateAddExp` | string | `""` | 日期模式：DATEADD 表达式 |
| `datePrintFormat` | string | `"YYYY-MM-DD"` | 日期模式：输出日期格式 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-formula` | icon: `icon-formula`

**表达式格式：** 使用 `$model$` 引用字段（每个字段引用以 `$` 开头和结尾）。例如：
- SUM: `"expression": "$money_xxx$$number_xxx$"`（两个字段相加）
- PRODUCT: `"expression": "$money_xxx$$integer_xxx$"`（两个字段相乘）
- CUSTOM: `"expression": "$field1$ + $field2$ - $field3$"`（自定义运算）

> **注意：** 子表内的 formula 控件引用同行其他列，格式相同。

**数字模式 (`type: "number"`)：**
| mode | 说明 |
|------|------|
| `SUM` | 求和（选择多个字段相加） |
| `AVERAGE` | 平均值 |
| `MAX` | 最大值 |
| `MIN` | 最小值 |
| `PRODUCT` | 乘积 |
| `CUSTOM` | 自定义公式，使用 `expression` 字段 |

**日期模式 (`type: "date"`)：**
| mode | 说明 |
|------|------|
| `DATEIF` | 两个日期之差 |
| `DATEADD` | 日期加减运算 |
| `NOW_DATEIF` | 距此刻时长（当前时间到目标日期，未来为正、过去为负） |
| `PAST_NOW_DATEIF` | 至今已过时长（目标日期到当前时间，过去为正、未来为负） |

## link-record — 关联记录

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `sourceCode` | string | `""` | 来源表单编码（desformCode） |
| `showMode` | string | `"single"` | 显示模式（`single`=单条，`many`=多条） |
| `showType` | string | `"card"` | 展示方式（`card`=卡片，`select`=下拉，`table`=表格） |
| `titleField` | string | `""` | **必填** — 来源表单的标题字段 model（用于下拉/卡片显示） |
| `showFields` | array | `[]` | 要在关联视图中展示的来源表字段 model 列表 |
| `allowView` | boolean | `true` | 是否允许查看 |
| `allowEdit` | boolean | `true` | 是否允许编辑 |
| `allowAdd` | boolean | `true` | 是否允许新增 |
| `allowSelect` | boolean | `true` | 是否允许选择 |
| `hiddenOnAdd` | boolean | `false` | **「新增时隐藏」**（设计器右侧操作属性最后一个勾选框）：新建记录时整块不渲染，查看/编辑已有记录时照常显示。要「新建时看不到、看完能维护」就用它 |
| `buttonText` | string | `"添加记录"` | 添加按钮文本 |
| `twoWayModel` | string | `""` | 双向关联的反向字段 model |
| `dataSelectAuth` | string | `"all"` | 数据权限范围：`all`=可选择所有记录，`read`=仅可选择有查看权限的记录 |
| `filters` | array | `[{matchType:"AND",rules:[]}]` | 筛选条件，**始终只用 `[0]`**。`rule` 必须是大写 `EQ`/`IN`/`DATE_LT` 等，完整规则见 `desform-link-record.md`「filters」节，禁止套用 `desform-filter-rules.md` 的小写 `eq` |
| `search` | object | `{enabled:false, field:"", rule:"like", afterShow:false, fields:[]}` | 查询设置，完整规则见 `desform-link-record.md`「search」节。`isSubTable` 无此面板 |
| `search.enabled` | boolean | `false` | 是否启用查询设置 |
| `search.field` | string | `""` | 关键词搜索字段 model，仅 `input`/`textarea`/`phone`/`email`/`text-compose`/`auto-number` |
| `search.rule` | string | `"like"` | 关键词方式：`eq` 精确 / `like` 模糊（小写，不是 `EQ`） |
| `search.afterShow` | boolean | `false` | 打开选择弹窗先不拉数据，查询之后再显示（下拉模式无效） |
| `search.fields` | array | `[]` | 用户筛选可用的源表字段 model 列表（不是固定条件，不要和 `filters` 混用） |
| `createMode` | object | `(见说明)` | 创建模式配置：`{add, select, params}` |
| `createMode.add` | boolean | `true` | 是否支持新增创建 |
| `createMode.select` | boolean | `false` | 是否支持选择已有记录 |
| `createMode.params.selectLinkModel` | string | `""` | 选择模式关联字段 model |
| `width` | string | `"100%"` | 控件宽度 |
| `defaultValue` | string | `""` | 默认值 |
| `defaultValType` | string | `"none"` | 默认值类型 |
| `required` | boolean | `false` | 是否必填 |
| `disabled` | boolean | `false` | 是否禁用 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-link-record` | icon: **`icon-link`**（注意：不是 `icon-link-record`！）

**控件顶层属性**（与 `type`/`key`/`model` 同级，不在 options 内）：

| 属性 | 说明 |
|------|------|
| `isSubTable` | 是否为子表模式（一对多），设为 `true` 时不需要 card 容器 |
| `isSelf` | 是否为自关联（关联自身表单）；自关联树场景必须设为 `true`；使用 `LINK_RECORD(..., is_self=True)` 自动处理 |

> **showMode="many" 或 showType="table" 时不需要 card 容器**

### link-record 重要注意事项（实战踩坑）

1. **`advancedSetting.defaultValue.customConfig` 必须为 `true`**
2. **默认 4 个操作选项（`allowView`/`allowEdit`/`allowAdd`/`allowSelect`）全设 `true`**，否则关联记录功能不完整
   - 想「新建记录时看不到这块」→ 用 `hiddenOnAdd=true`（设计器里的「新增时隐藏」勾选框），**不要**去关 `allowAdd`/`allowSelect`：
     那只会在已有记录上把「+ 添加记录 / + 关联已有数据」按钮去掉，语义完全不同（2026-09-17 用户当场否掉）。
   - 确实要「已有记录里也只读、不给任何入口」时，才**四键一起关**：`allowAdd=false` ＋ `allowSelect=false` ＋ `createMode.add=false` ＋ `createMode.select=false`；
     少关一个界面上就还留着一个按钮——实测只关 `allowAdd`/`createMode.add` 后，「+ 添加记录」会变成「+ 关联已有数据」仍在
3. **`titleField` 必须填源表的真实标题字段 model**（如 `input_xxx`），否则关联记录无法正常显示
4. **`showFields` 建议填入源表中需要展示的字段 model 列表**，提升选择体验
5. **icon 是 `icon-link`** 而非 `icon-link-record`，写错会导致控件显示异常

## link-field — 他表字段

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `linkRecordKey` | string | `""` | 关联记录控件的 **key**（不是 model！） |
| `showField` | string | `""` | 要显示的来源表字段的 **model** |
| `saveType` | string | `"view"` | 存储方式（`view`=仅显示，`save`=保存到当前表） |
| `fieldType` | string | `""` | 来源字段的实际控件类型（如 `"input"`/`"select-user"`/`"money"` 等） |
| `fieldOptions` | object | `{}` | 来源字段的相关 options 子集（如 select-user 需 `{multiple: false, customReturnField: "username"}`） |
| `width` | string | `"100%"` | 控件宽度 |
| `defaultValue` | string | `""` | 默认值 |
| `readonly` | boolean | `false` | 是否只读 |
| `disabled` | boolean | `false` | 是否禁用 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-link-field` | icon: **`icon-field`**（注意：不是 `icon-link-field`！）

> **必须与一个 link-record 控件配对使用**

### link-field 与关联记录的绑定规则（2026-09-04 源码验证：componentsConfig.js / WidgetConfig.vue / WidgetConfigMixins.js / linkage/JLinkField.vue）

1. **只能绑「单条」关联记录**：可选范围 = 本表单**同层级**里 `showMode:'single'` 的 link-record（多条 many 不出现；子表内的 link-field 只能绑本子表内的关联记录）。面板无可用时提示「请先添加一个单条的关联记录组件」。数据来源表 = 所绑关联记录的 `sourceCode`
2. **`showField` 选项 = 来源表字段去 link-record 类型**（value 存字段 **model**），UI 还允许链式再选来源表里的 link-field。**手动换绑关联记录后 UI 自动把来源表 `titleField` 填进 showField**
3. **`fieldType`/`fieldOptions` 由 UI 选中显示字段时自动拷贝**：来源字段 type 拷进 `fieldType`；options 只拷白名单 `{multiple, remote, options, dictCode, customReturnField}`（来源是 formula 再拷 `type/decimal/thousand/percent/unitPosition/unitText/datePrintFormat`；来源是 link-field 则透传其 fieldType/fieldOptions）。公式/查询/过滤/显示格式化均按 `fieldType` 视作真实组件
4. **`saveType`：`view` 仅显示不落库；`save` 原值落库 + `<model>_dictText` 存翻译文本**。表单**标题字段**若用他表字段**必须 save**（UI 禁止 view 并报错）；子表内（isSubItem）面板无 saveType 选项
5. **运行态只取关联记录第一条选中记录**（dataIds[0]），显示值优先 `showField+'_dictText'`；`fieldType`=imgupload/file-upload 时按附件列表展示
6. 敲敲云工作表**可用**（isLowApp 仅隐藏 table-dict/select-tree/category-linkage），与关联记录一起拖入；无 `advancedSetting`

### link-field 重要注意事项（实战踩坑）

1. **link-field 不需要 `advancedSetting`** — 与其他控件不同，link-field 没有此字段
2. **icon 是 `icon-field`** 而非 `icon-link-field`
3. **`fieldType` 必须填来源字段的真实控件类型**，不能一律写 `"input"`
4. **`fieldOptions` 需包含来源字段类型相关的配置**，例如 select-user 需要 `{"multiple": false, "customReturnField": "username"}`
5. **`linkRecordKey` 填的是 link-record 控件的 key（如 `1773457559119_461003`）**，不是 model（如 `link_record_xxx`）

## hand-sign — 手写签名

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `disabled` | boolean | `false` | 是否禁用 |
| `required` | boolean | `false` | 是否必填 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-hand-sign` | icon: `icon-signature`

> `desform_utils.py` 生成时会额外传入 `"width": "100%"` 和 `"height": "200px"` 优化显示效果，但源码默认 options 不含这两个字段。

## oa-approval-comments — OA审批意见

⛔ **敲敲云无 OA 字段分组**（Container.vue `v-if="!isLowApp"`）。禁止新建。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `width` | string | `"100%"` | 控件宽度 |
| `required` | boolean | `false` | 是否必填 |
| `disabled` | boolean | `false` | 是否禁用 |
| `placeholder` | string | `""` | 占位提示 |
| `hidden` | boolean | `false` | 是否隐藏 |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-oa-approval-comments` | icon: `icon-input`

OA 流程审批意见控件，用于 BPM 审批场景。

## table-dict — 表字典

⛔ **敲敲云禁用**（QQYUN-3641）。禁止新建。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `width` | string | `"100%"` | 控件宽度 |
| `defaultValue` | string | `""` | 默认值 |
| `placeholder` | string | `"点击选择表字典"` | 占位提示 |
| `showIcon` | boolean | `true` | 是否显示图标 |
| `iconName` | string | `"icon-popup"` | 图标名 |
| `disabled` | boolean | `false` | 是否禁用 |
| `multiple` | boolean | `false` | 是否多选 |
| `clearable` | boolean | `true` | 是否可清除 |
| `style` | string | `"select"` | 展示方式（`select`=下拉模糊搜索，`popup`=弹窗选择） |
| `dictTable` | string | `""` | 表名（`queryScope=cgreport` 时为 Online 报表编码） |
| `dictCode` | string | `""` | 存储字段（value） |
| `dictText` | string | `""` | 显示字段（label）；**style=popup 时自动设为该控件自身或其他文本控件的 model** |
| `hidden` | boolean | `false` | 是否隐藏 |
| `required` | boolean | `false` | 是否必填 |
| `filterable` | boolean | `true` | 是否可搜索（仅 style=select 时有效） |
| `queryScope` | string | `"cgreport"` | 查询作用域（`cgreport`=Online报表，`database`=数据库表，**database 仅支持 style=select**） |
| `reportParams` | object | `{}` | Online 报表动态参数，用于替换报表 SQL 中的 `${xxx}` 占位符（仅 `queryScope=cgreport` 时生效） |
| `reportQueryConditions` | object | `{}` | Online 报表预设查询条件，结构为 `{ 字段名: { view, mode, value \| begin, end } }`（仅 `queryScope=cgreport` 时生效） |
| `hiddenOnAdd` | boolean | `false` | 新增时隐藏 |
| `fieldNote` | string | `""` | 字段备注 |
| `autoWidth` | number | `100` | 宽度百分比（100=整行，50=半行） |

className: `form-dict` | icon: `icon-dict`

> **使用 table-dict 组件前必须完整阅读以下内容！** 错误配置会导致表单无法正常使用。

**关键约束（已验证）：**
- `dictTable`/`dictCode`/`dictText`/`queryScope` 必须放在 `options` 内部，**不是**顶层字段
- `style=popup` 时，`dictText` 必须设为该控件自身或其他文本控件的 model（`desform_utils.py` 已自动处理，无需手动指定）
- `queryScope=database` 时**不支持 `style=popup`**，只支持 `style=select`
- `queryScope=cgreport` 时 `dictTable` 为 Online 报表编码，`dictCode`/`dictText` 为报表的字段名

⚠️ **强制前提（不可跳过，不可替代）**：配置 `queryScope=cgreport` 或 `style=popup` 之前，**必须先调用 `jeecg-onlreport` skill** 查询系统中现有的报表编码和字段名。**禁止**尝试直接调用 API、猜测编码或跳过此步骤——报表编码是系统生成的，无法预知，填错会导致控件无法加载数据。在获取到真实编码之前，不要继续生成表单 JSON。

> **踩坑记录**：cgform（Online 表单）和 cgreport（Online 报表）是**完全独立的两套系统**，不是同一体系下的子类型。AI 容易误以为 cgreport 只是 cgform 里 `tableType=2` 的一种，从而自行调用 cgform API 来"过滤出报表"——这是错误的，两套 API 路径和数据结构完全不同，自行调用 cgform API 查到的是 Online 表单数据，不是报表。查询 Online 报表**必须且只能**通过调用 `jeecg-onlreport` skill，优先使用其中的语法糖 `list_all_reports_table()` 和 `list_fields_by_code_table(code)` 完成查询，**禁止**绕过 skill 自行拼接 API 调用。

## tabs — 标签页

布局容器控件。子控件分组放入各标签页（pane）。结构与普通字段控件不同——`panes` 在控件**顶层**（不在 options 内），`options` 仅含样式参数。

**顶层属性：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `type` | string | `"tabs"` | 控件类型标识 |
| `isContainer` | boolean | `true` | 是否为容器控件 |
| `panes` | array | `[]` | 标签页数组，每项含 `name`/`label`/`list`/`hidden`/`hiddenOnAdd` |
| `panes[].name` | string | — | pane 唯一标识（不可重复，如 `tab_1`） |
| `panes[].label` | string | — | 标签显示文本 |
| `panes[].list` | array | `[]` | 该标签页内的控件数组 |
| `panes[].hidden` | boolean | `false` | 是否隐藏此 tab |
| `panes[].hiddenOnAdd` | boolean | `false` | 新增数据时隐藏此 tab |

**options 属性：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `activeName` | string | `"tab_1"` | 默认激活的 pane name |
| `type` | string | `"border-card"` | 样式（`card`/`border-card`） |
| `position` | string | `"top"` | 标签位置（`top`/`left`/`right`/`bottom`） |
| `width` | string | `"100%"` | 控件宽度 |
| `hidden` | boolean | `false` | 是否隐藏 |

> Tabs 可递归嵌套 Grid / Card / Tabs。完整容器嵌套规则见 `references/desform-layout-controls.md`。

---

## ⚠️ 默认值溯源勘误（2026-09-03，对照真实前端源码）

**原则：UI 拖拽组件的标准 JSON = 源码默认 options；creator 脚本/落库/保存注入会增删键。禁止拿落库 JSON 反推 UI 默认值，也不要按本页参数表拼出 UI 不认识的形态。** 拿不准时让用户在 UI 拖一个同控件对照（本会话用「编辑器-01」对照定位了 editor 问题）。

易错点（与上方表格不一致处，以此为准）：

1. **editor（富文本）**：源码 options 只有 `defaultValue / width / disabled / hidden` 四键，**无 `advancedSetting` 块、无 autoWidth**；UI 保存时才注入 `hiddenOnAdd/required/fieldNote`。**已修复（2026-09-03）**：`desform_utils.make_widget` 改为仅对源码白名单类型（input/textarea/number/integer/money/radio/checkbox/date/select/switch/slider/phone/email/select-user/select-depart/select-depart-post/link-record）注入 `advancedSetting`，其余类型（editor/markdown/imgupload/file-upload/map/location/ocr/formula/…）不再注入。**旧脚本建的表现在仍可能残留该块**，遇到时参照 UI 拖拽结构手工对齐：删 advancedSetting，options 只留 7 键，width 恒 '100%'（editor 无半宽档）。
2. **phone / email**：源码 `width:'300px'`；creator 落库却是 `''`。别按落库值判断 UI 默认。
3. **map**：源码**没有 defaultValue 键**（落库出现是 creator 注入）；设置中心点要同时写 `point:{lng,lat}` 与 `defaultValue:"lng,lat"` 两个键。
4. **imgupload / file-upload**：`multiple`/`autoWidth` 等不在 creator make_widget 白名单（建表时静默忽略并告警）——要改必须建表后走 `update_widget`/整单改（见 SKILL.md 行宽度与补丁经验）。
5. **radio/checkbox/select**：源码默认自带静态选项 `[选项1/2/3]`（带 itemColor）；`advancedSetting.defaultValue` 恒为 `customConfig:true + valueSplit:","`，手写 JSON 勿漏（与上文备注一致）。
6. **hand-sign（手写签名）**：源码仅 `disabled/required/hidden` 三键；`width:'100%'`/`height:'200px'` 是 desform_utils 工厂附加，UI 面板无。
7. 其余控件默认值已逐一核对与上表一致，要点：number `defaultValue:0`、integer/money `undefined`（money width '180px'/unitText '元'/precision 2/placeholder '请输入金额'）、input/textarea width '100%'、formula mode `'SUM'` decimal 2 thousand true、auto-number 规则 `[{type:'number',mode:1,start:1,reset:0,length:4,continue:false}]` + generateOnAdd true、ocr type 'normal'、area-linkage areaLevel 3、select-user `customReturnField:'username'`、select-depart / select-depart-post `customReturnField:'id'`、人员/部门/角色 `dataAuthType:'member'`、org-role placeholder '选择组织角色'。
8. **auto-number 的 `numberRules` 段对象必须带 UI 渲染依赖的辅助键（2026-09-03 实测，对照 UI 手工配置「自动编号-01」及 ConfigItem.vue 源码）**：text 段要 `{type:'text', value:'AIC', text:'AIC'}`——**面板 `v-model` 绑定的是 `rule.text`**，缺 text 是「设置没生效」的真正原因，value 为后端兼容键同写；create_date 段要 `{type:'create_date', dateFormat:'yyyyMMdd', formatCustom:'yyyyMMdd', format:'yyyyMMdd'}`——**面板绑定 `rule.format`**（下拉 yyyyMMdd/yyyyMM/MMdd/yyyy/custom），`formatCustom` 仅 format='custom' 时显示，dateFormat 为后端兼容键，三键同写；number 段 `{type:'number', mode:1|2, start, reset, length, continue}` 无附加键（面板位数限 2~6，超出后 continue=false 时从 0 重新编号）。**缺 text/format 键时接口 success 但面板读不到段内容**。`AUTONUMBER(prefix=..., date_format=...)` 工厂已按此补全（2026-09-03），creator JSON 支持 `dateFormat` 参数；引用字段段 `{type:'field', model:'<他字段model>'}` 只存在于 UI 面板，需手工 `update_widget` 整组 rules 写入（先拖 UI 参照抄键集合）。
