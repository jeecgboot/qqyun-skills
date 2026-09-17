# 给已有工作表【新增】关联记录字段（快路径）

只读这一页，读完立刻执行。不要读 `desform-link-record.md` / `desform-cross-form-binding.md` / widget-options / json-config 全文。

## 第一条 tool call

用户消息里的 `api-base` / token 直接用（会话已有租户/应用也写进 JSON）。Write UTF-8 JSON 到 `{tmpdir}/jeecg-desform/job.json`（先 `skill_temp_path.py -f job.json`；会话已有该目录直接拼路径）。立刻：

```bash
python "<skill目录>/scripts/add_link_record.py" --api-base <URL> --token <TOKEN> --config <job.json>
```

Windows：中文只写在 JSON 文件里，禁止 `python -c`、禁止 PowerShell `--json '{"中文"}'`。不要等 y/n。不需要知道主表/目标表的 code 或字段 model——脚本内部按名称解析，**filter 的 sqParam/valueType/字段 model 全部由脚本算**，禁止手写。

**批量（≥2 条）用 `scripts/batch_add_link_record.py`**：job 为 `{"tenantName","appName","maxWorkers":4,"links":[<每条同本页格式>]}`，线程池并行跑全部（逐条串行时每个子进程重复 get_tenants/get_apps 定位，N 条 ≈ N×20s+；并行墙钟接近单条）。links 内 `(worksheet, field)` 重复会 fail-fast 拒绝。

## job.json

```json
{
  "tenantName": "八匹狼",
  "appName": "采购申请",
  "worksheet": "采购申请单",
  "field": "审批流程模板",
  "mode": "多条",
  "display": "卡片",
  "target": {"appName": "流程审批", "worksheet": "审批流程模板"},
  "showFields": ["流程类型"],
  "filters": [
    {"field": "流程类型", "rule": "等于", "value": "采购审批"}
  ]
}
```

| 字段 | 说明 |
|------|------|
| `tenantName` / `appName` / `worksheet` | **必须写中文名**（脚本按名解析应用）。⚠️ 只写 `tenantId`/`appId`、不写名称 → `initialized app_id=未设置` 后 **`缺少应用`**（2026-09-04 实测，脚本不认 JSON 里的 appId） |
| `field` | 新关联字段名；缺省=目标工作表名 |
| `mode` | `单条`/`多条`（或 single/many）；**「关联记录-多条」→ 多条** |
| `display` | `卡片`/`下拉`/`表格`（或 card/select/table） |
| `target` | 目标表：`appName`+`worksheet`；或直接 `target.code`。**同应用关联时 `target` 只写 `worksheet` 即可**——未指定 `code`/`appName` 时自动继承顶层 `appName`（2026-09-15 修复：原行为报「缺少应用」） |
| `showFields` | 可选，额外展示的源表字段中文名。⚠ 2026-09-15 实测：**showFields 只配置「关联视图里展示哪些源表字段」，不会生成独立的「关联字段带出（只读）」控件**——不要把 `showFields` 当带出字段用。<br>⚠ **规格没写也要主动确认**：不传 `showFields` 落库为 `[]`，关联记录卡片/表格里**只显示标题字段一列**，列表页看着像「字段没勾」。需要看哪些列就问一句或按业务取（常见 2~6 个关键列）。2026-09-16 用户实测反馈「显示字段 提示词里面没有，导致没有勾选」 |
| `filters` | 可选筛选：`field`=源表中文字段名（或系统字段 创建人/创建时间…），`rule`=等于/不等于/开头是/结尾是/大于等于/包含/为空/是其中一个…，`value`=固定值；`"valueType": "字段"` 时 `value`=**主表**字段中文名 |
| `filterMatchType` | 可选 AND/OR，默认 AND |
| `dataSelectAuth` | 可选 `全部` / `仅可选择有查看权限的记录` |

**自关联 = 自关联树（自己关联自己，2026-09-04 用户确认）：** `target` 与主表指向**同一工作表**时脚本自动按自关联树处理（`LINK_RECORD` 传 `is_self=True`）：控件**顶层**写 `isSelf:true`、valueSplit 置空，输出带 `"isSelf": true` 与 [hint] 提示。
- 没有 `isSelf` = 系统不认「自己关联自己」，只是同表单普通下拉/卡片，**没有下级/子树能力**（首次实测就这么错的，必须整单或 UI 补 isSelf）
- 推荐 `mode: 单条`（一条记录一个父节点）+ `display: 卡片`（卡片展示父记录、可展开/添加下级；下拉亦可，数据量大配搜索）
- `isSelf` 是控件**顶层属性**（与 key/model 同级），放 `options` 内无效；差异结构见 `desform-self-tree.md`

**双向关联（twoWay）脚本 v1 不支持**：用户说「双向/反向关联」时如实告知需分两步（先建目标表反向字段再互相填 twoWayModel），不要硬塞字段。

已存在同名字段：add_widget 会报错/重复？看输出——字段名冲突时先 `get_form_fields` 确认，改名或删旧再跑。

## 实测记录（2026-09-03）

- 曾手写 `LINK_RECORD(..., filters=[...])` + `add_widget`：工厂当时把 `filters` 当非白名单参数**静默丢弃**（仅打印警告），筛选没写进 options，必须二次 `update_widget`。**已修**：`LINK_RECORD` 现支持 `filters=/search=/data_select_auth=` 显式参数（desform_utils.py 2026-09-03）。
- 本脚本单次提交即含 filters，回查 options.filters 落地无二次修正（报销单→审批流程模板 测试用例通过）。
- 标题字段 model 由脚本自动取（design.config.titleField 或第一个控件），不要在 JSON 里猜 model。
- ⚠️ 标题字段「两层」：控件级 `options.titleField` 在建字段时固化；后续把目标表标题改名字段（/desform/edit 改 config.titleField）**不会**自动同步已建关联控件，需逐个 update_widget 覆盖（见 desform-link-record.md「十二」）。
- 2026-09-04 自关联实测：target==worksheet(主表) 时输出 `"isSelf": true`，回查设计 JSON 顶层 isSelf=True 且 valueSplit=''；临时字段增删验证通过。⚠ **只有自己关联自己有 isSelf，其它（跨表）关联没有**——is_self 仅当 tg_code==master_code 才为 True，跨表一律 False，禁止给跨表关联手动加 isSelf。

## 禁止（都实测踩过坑）

- 手写 `LINK_RECORD`/`update_widget` 拼 filters/sqParam
- 先 `query_form` 源表猜 title/model 再等下一轮
- 复用 `update_link_record.py` 去加**新**字段（它只改已有控件）
- job 只写 `tenantId`/`appId` 不写 `tenantName`/`appName`（`缺少应用`）
- 改完 type 残留 options 旧键问题与「改控件类型」场景相关，见 SKILL.md「追加：改控件类型 / 互换字段语义」
