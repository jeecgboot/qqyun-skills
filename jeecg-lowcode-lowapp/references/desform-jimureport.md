# desform 一键生成积木报表（打印）

为表单设计器（desform）表单一键创建积木报表并关联到「积木报表打印」（`allowJmReport`），
实现单条记录的高度自定义打印效果。脚本：`scripts/desform_jimureport.py`。

> 触发场景：用户说「给这个表单加积木报表打印」「创建打印报表」「desform 集成积木」「一键生成打印模板」等。
> 仅需简单的"按字段排版打印"用本脚本即可，**无需**加载 jimureport 技能。
> 仅当用户要高度定制的报表（分组/交叉/图表/套打背景图等）时，才加载 **jimureport** 技能，
> 并用本文档的 desform 数据 API 规范作为数据集来源。

---

## 与 onlform 集成的关键差异（已实测确认 @2026-05-21）

| 维度 | desform（本脚本） | onlform |
|------|------------------|---------|
| 数据 API 路径 | `/desform/api/data/{desformCode}/queryById` | `/online/cgform/api/data/{tableName}/queryById` |
| `mock` 参数 | **不支持**（apiUrl 里不带 `&mock=true`） | 支持 `&mock=true` |
| `fieldList.fieldName` | 控件 **model**（如 `input_1779...`） | 数据库字段名 |
| `fieldList.fieldText` | 控件 **title**（中文名） | 字段中文名 |
| 单元格绑定符号 | `${dbCode.model}`（**单值**绑定） | `#{dbCode.field}`（列表绑定） |
| 数据返回结构 | `{"data":[ {model:value} ]}` | 同 |
| `isList` / `isPage` | `"1"` / `"0"` | `"1"` / `"0"` |
| 预览 URL 变量 | `{{sysBasePath}}/jmreport/view/{id}` | `{{ window._CONFIG['domianURL'] }}/jmreport/view/{id}` |
| 回写位置 | `designConfig.config.allowJmReport` + `jmReportURL` | `extConfigJson.reportPrintShow` + `reportPrintUrl` |
| 回写方式 | `update_design_config(code, {...})` | `PUT /online/cgform/head/edit` |

> **核心结论（最易踩坑）**：数据 API 返回 JSON 的 key **永远等于控件 `model`**。
> 所以 `fieldName` 必须填 model、绑定写 `${dbCode.model}`；填 `key` 或中文名会导致打印值全空。

---

## API base 可能是两个不同地址（重要）

desform 接口与积木报表接口的服务地址常常不同：

| 接口前缀 | 用哪个 base | 示例 |
|---------|-----------|------|
| `/desform/*` | `--api-base` | `http://host:3100/jeecgboot` |
| `/jmreport/*` | `--jmreport-base` | `http://host:8080/jeecg-boot` |

- `--jmreport-base` 缺省时与 `--api-base` 相同（同体部署时只传一个即可）。
- 部署分离时**必须**显式传 `--jmreport-base`，否则报表创建/预览会失败或访问到错误后端。
- 回写表单的 `jmReportURL` 用运行时变量 `{{sysBasePath}}`，由前端解析，不写死地址，因此跨环境迁移友好。

---

## 用法

```bash
python <skill目录>/scripts/desform_jimureport.py \
    --api-base http://host:3100/jeecgboot \
    --jmreport-base http://host:8080/jeecg-boot \
    --token <X-Access-Token> \
    --config <config.json>
```

> Windows 下用 PowerShell tool 执行（避免 Bash tool 把 python 后台化）。

### 创建报表 config

```json
{
  "action": "create_report",
  "desformCode": "oa_car_use",
  "reportName": "用车申请打印",
  "formStyle": "auto"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `action` | 是 | `create_report` |
| `desformCode` | 是 | desform 表单编码 |
| `reportName` | 否 | 缺省 = `{表单名}打印` |
| `formStyle` | 否 | `auto`(默认,读表单 formStyle) / `normal` / `word` |
| `dataCode` | 否 | 主表数据集编码，缺省 = `formmain` |
| `includeSubTables` | 否 | 是否打印子表/关联记录，缺省 `true`（表单含子表/关联时自动生成） |
| `fields` | 否 | 手动指定主表字段 `[{"fieldName":"<model>","fieldText":"中文"}]`；缺省自动从表单设计读取 |

脚本 5 步：创建空报表 → 保存 API 数据源（主表 + 子表 + 关联）→ 构造主子表模板 → 保存设计 → 回写表单 `allowJmReport`/`jmReportURL`。

### 删除报表 config

```json
{
  "action": "delete_report",
  "reportId": "1217365226891173888",
  "desformCode": "oa_car_use"
}
```

- `reportId` 必填。
- `desformCode` 可选：提供则同时清除表单的 `allowJmReport=false`、`jmReportURL=""`。
- ⚠️ 若该表单的关联已指向**另一个**报表，删旧报表时**不要**传 `desformCode`，否则会误清当前关联。

---

## formStyle 样式适配

脚本按表单的 `formStyle` 自动套用两套打印样式（`formStyle:"auto"` 时）：

| 表单风格 | 标题 | 标签列 | 值列 |
|---------|------|--------|------|
| `normal` | 蓝底深蓝字加粗（style 5） | 灰底右对齐加粗（style 3） | 左对齐（style 6） |
| `word` | 无底色加粗（style 7） | 浅灰底居中加粗（style 8） | 左对齐（style 6） |

布局：标签-值成对排列，每行 2 组共 4 列；长文本控件（textarea/富文本）值独占整行（合并 3 列）。
样式数组与 onlform 的 `build_styles()` 同源，确保观感一致。

---

## 子表 / 关联表单打印（API v2 多数据集方案，默认开启）

> 实测方案（2026-08-05）：用户手动报表 + AI 复刻验证（reportId=1244929904612962304 / 1244932213170466816）。

脚本自动识别表单中的 **sub-table-design（子表）** 和 **link-record（关联记录）**，
为每个生成独立数据集 + 主子表三段式打印区块。config 中 `includeSubTables: false` 可关闭。

### 关联记录：单条 → 主表字段，多条 → 子表（实测 @2026-08-05）

link-record 按 `options.showMode` 区分处理（实测自平台 generateTemplateByDesign 生成模板，报表 1244952366432088064 / 表单 `ldd_guan_lian_ji_lu`）：

| `showMode` | 处理方式 | 绑定 |
|-----------|---------|------|
| `"single"`（单条记录） | **仅作为主表字段**，与普通字段同卡片布局，渲染关联记录存储文本 | `${lumain.{model}}` 单值绑定 |
| `"many"`（多条记录） | **生成子表**：独立数据集 + 三段式区块（标题+表头+数据行，自动循环展开）；同时主表区仍保留一个 `${lumain.{model}}` 字段行显示存储文本 | `#{customersub.{字段model}}` 列表绑定 |

- 子表数据集编码：`{sourceCode去demo_前缀}sub`（`demo_customer` → `customersub`），API `/desform/api/v2/data/{formId}/{sourceCode}/queryById?id=${id}`，`isList="1"`
- **主表数据集编码平台生成固定为 `lumain`**（平台 generateTemplateByDesign 生成，区别于脚本缺省 `formmain`），API `/desform/api/v2/data/{formId}/queryById?id=${id}&token=${token}`，`isList="0"`
- 实测字段映射（`ldd_guan_lian_ji_lu`，5 控件 + 2 关联）：单条关联「日期函数测试表单」(`link_record_...903277`) → `${lumain.link_record_...903277}` 主表绑定；多条关联「客户档案」(`link_record_...293100`, sourceCode=`demo_customer`) → 子表 `customersub` 三列（客户名称/联系电话/联系邮箱）`#{customersub.input_...}` 列表绑定，子表区块标题「客户档案」merge 全列

> **脚本已实现该规则（@2026-08-05）**：`desform_jimureport.py` 的 `_extract_link_records` 同时提取 `showMode`，子表生成循环跳过 `showMode=="single"` 的关联记录（仅保留主表 `${formmain.model}` 字段绑定），只有 `many` 才建独立数据集+区块。实测：`ldd_guan_lian_ji_lu` 重新生成（报表 1244961084305534976）仅创建 `customersub` 一个关联子表数据集，单条关联「日期函数测试表单」无子表数据集。

### 数据源 API（desform API v2，注意与主表单数据集方案不同）

| 数据集 | 编码规则 | API URL |
|--------|---------|---------|
| 主表 | `formmain`（config.dataCode 可改） | `/desform/api/v2/data/{formId}/queryById?id=${id}&token=${token}` |
| 子表 | `gen_{子表model尾段}sub`（如 `gen_272163sub`） | `/desform/api/v2/data/{formId}/{子表model}/queryById?id=${id}` |
| 关联记录 | `{sourceCode去掉demo_前缀}sub`（如 `customersub`） | `/desform/api/v2/data/{formId}/{sourceCode}/queryById?id=${id}` |

> **formId 是主表单 ID**（非 desformCode），所有子表/关联数据集都挂在主表单 ID 下。
> 子表/关联数据集 paramList 只传 `id`（无 token），与主表不同。

### 模板布局（主子表三段式）

```
行 0     主表大标题（merge A1:D1）
行 1..N  主表字段：每行 2 组（标签 style2 + 值 style3），共 4 列
(空行)
行 N+2   子表区块标题（style5，merge 全列，如 A23:G23）
行 N+3   子表表头（style4 蓝底白字）
行 N+4   子表数据行（style0 边框，**#{dsCode.model} 列表绑定**，自动循环展开）
```

- **绑定语法**：主表 `${formmain.model}`（单值）；子表 `#{gen_xxxsub.model}`（**列表绑定，自动循环展开，无需 loopBlockList**）
- **merges 行号规则**：区块标题行 N → merge `A{N+1}:{末列字母}{N+1}`（如标题行 22 → `A23:G23`）
- 区块间空一行；每块 3 行（标题 + 表头 + 数据）

---

## 不打印的内容（与"复杂控件不特殊处理"约定一致）

脚本提取字段时自动跳过：
- 布局容器：`card` / `grid` / `tabs` / `divider` / `text` / `html` / `button` / `alert`

其余数据控件（选人/选部门/关联记录/图片/文件等）按 `${dbCode.model}` 原样绑定，渲染其存储值文本，不做转换。

---

## 实测验证记录

- 2026-05-21：`oa_car_use`（用车申请，10 字段，normal 风格），分离 base（desform=3100/jeecgboot，jmreport=8080/jeecg-boot）一次创建成功；浏览器预览 `${oa_car_use.model}` 全部正确替换为真实值，卡片布局、蓝底标题、标签灰底均正常渲染。
- 关键确认：数据 API 返回 `{"data":[{...}]}`，key=控件 model；`isList="1"` + `${}` 单值绑定组合渲染正确。
- 2026-08-05：`demo_all_widgets_form`（全控件演示，42 主表字段 + 1 子表 + 2 关联），API v2 多数据集主子表方案一次创建成功；子表数据行 `#{gen_272163sub.xxx}` 列表绑定自动循环展开，3 个主子区块均正常渲染。
- 2026-08-05：`ldd_guan_lian_ji_lu`（ldd关联记录，5 控件 + 2 关联），平台 generateTemplateByDesign 生成模板（报表 1244952366432088064）：单条关联「日期函数测试表单」作为主表字段 `${lumain.xxx}`；多条关联「客户档案」生成子表数据集 `customersub` + 三段式区块 `#{customersub.xxx}`；主表数据集编码为 `lumain`（非脚本默认 `formmain`）。
- 2026-08-05：`ldd_guan_lian_ji_lu` 用脚本重新生成（报表 1244961084305534976，名称「ldd关联记录打印」）：单条关联被跳过子表生成、仅作主表字段 `${formmain.link_record_...903277}`；多条关联生成 `customersub` 数据集 + 三段式区块；表单回写成功。
