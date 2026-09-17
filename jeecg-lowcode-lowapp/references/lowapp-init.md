# 应用内工作表：初始化

**建表 / 一对一不要读本文。** 只读 `references/fast-create.md`，跑 `scripts/create_linked_worksheets.py`。

只在手写临时脚本（加字段、改已有表）时读本文。创建、复制、改名、删除、列出**应用**走 SKILL「创建 / 复制 / 编辑 / 删除应用」。

不要打开 `desform-lowapp.md`、`desform-lowapp-utils.md`、`jeecg-desform`、`jeecg-onlform`。

## 参数

| 已有 | 做法 |
|------|------|
| 会话里已有 `api-base` / `token` / 租户 ID / 应用 ID / 表单 code / 视图 ID / 字段 model | 直接用，禁止再 list、禁止再 `get_form_fields` / `query_list_views` |
| 用户消息里给了地址和 token | 用消息里的；会话没有才问 |
| **用户给了租户 ID** | **直接用**，`--tenant-id` / `init_lowapp(tenant_id=tid)`，禁止再查租户列表 |
| 租户只有名称（没有 ID） | **脚本内先查再 init，禁止单独 list 一轮再创建。** `lowapp_creator.list_current_tenants(api_base, token)`（`/sys/tenant/getCurrentUserTenant`，**不要带**默认 `X-Tenant-Id: 1`）。匹配：① `name` 精确等于用户词；② 0 条则去掉末尾「租户」「组织」再精确匹配。仍 0 条或多条则停并打印现有名称，禁止用历史数字猜。禁止 `init_lowapp(tenant_id=0)` / `init_api` 后再 `get_tenants()`——默认头 `1` 会 401「登录租户授权变更」 |
| 应用只有名称 | 已有租户 ID 后 `get_apps(tenant_id)` 按 `appName` 匹配：① 精确等于用户词；② 0 条则去掉末尾「应用」再精确匹配。仍 0 条或多条则停 |
| 用户没提分组 | **不查分组**，不传 `app_menu_group_id` |
| 用户说放到某分组 | 才 `get_worksheet_groups()`，按 `menuName` 取 `id` |

## 和创建写在同一条命令里

Windows 中文不要 `python -c`，不要 PowerShell `--json '{"中文"}'`。解析租户/应用和建表放进**一个** `.py` 再跑。

```python
import sys
sys.path.insert(0, r'<skill目录>/scripts')
from desform_lowapp_utils import init_lowapp, set_app, get_apps
from lowapp_creator import list_current_tenants
# 建表用 subprocess desform_creator.py --tenant-id --app-id --config -

# 有租户 ID：直接用，不要 list_current_tenants
# tid = 1012
# 只有名称：先查再匹配
tenants = list_current_tenants(api_base, token)
matched = [t for t in tenants if t.get('name') == '八匹狼']
tid = matched[0]['id']

init_lowapp(api_base, token, tenant_id=tid)  # 必须先 init 连上服务，get_apps 否则报 unknown url type
apps = (get_apps(tenant_id=tid).get('apps') or [])
app_id = [a for a in apps if a.get('appName') == '销售记录'][0]['id']
set_app(app_id)  # 或重新 init_lowapp(api_base, token, tenant_id=tid, app_id=app_id)
# 随后 desform_creator.py --tenant-id tid --app-id app_id --config -
# 不要自己再写 get_form_id 防覆盖：脚本已是 existing_id, _ = get_form_id(code)
# 若手写必须 unpack：fid, uc = get_form_id(code); if fid:  # (None, None) 是真值
# 禁止创建前/后 get_form_id、check_code_available 探候选编码（一次全量 list 校验 10s+）
# 编码一次定死；LINK_RECORD 的 (ws, key, model) 直接给 twoWayModel；add_widget / update_widget 两边并行
```

`desform_creator.py` 在传了 `--tenant-id` 和 `--app-id` 时会自己 `init_lowapp`。字段 ≤50 用 stdin `--config -`（Python `subprocess` 传 UTF-8，不要 `echo`）。

两张以上互不依赖的基础表：同一脚本里 **并行** 调 `desform_creator.py`（`concurrent.futures`），不要 for 循环串行。一对一/双向关联必须等两张表都建完再 `add_widget` + `twoWayModel`，流程见 `desform-cross-form-binding.md`，不要拆成多次对话。

用户给了地址 + token + 名称 + 要建什么：不要等 y/n，不要先问数字 ID。

## 禁止

- 先 `lowapp_creator.py --json {"action":"list"}` 再创建工作表（冷启动没有 ID 也禁止拆成两轮）
- 为「在应用下」去读封面图、应用分组、`menu_id` 对照、禁用控件长表（禁用名单以 SKILL「创建表单」里那一行 ⛔ 为准）
- 打开 `jeecg-desform` / `jeecg-onlform` 的 SKILL.md
- 全量读 `desform-widget-options.md`（`offset=1`）
