---
name: jeecg-lowcode-lowapp
description: JeecgBoot 低代码应用（lowApp / 敲敲云）及应用内工作表。创建/复制/改名/删除/列出应用；在某租户或应用下创建/修改工作表、一对一、关联记录。不处理 Online 表单。禁止同时加载 jeecg-desform / jeecg-onlform / jeecg-system。同一句要应用+工作表+简流+仪表盘（或同时点名 miniflow/dashboard）：只读 references/fast-full-chain.md，禁止并行通读三个 SKILL.md。应用 CRUD：直接跑 scripts/lowapp_creator.py（零预读）。租户+应用下建表或一对一：不要读本 SKILL 全文，只读 references/fast-create.md，立刻跑 scripts/create_linked_worksheets.py。改已有关联记录：只读 references/fast-link-record.md。已有表新增关联记录字段：只读 references/fast-add-link-record.md。
---

# JeecgBoot 低代码应用（敲敲云）

> 本 skill 处理敲敲云应用和工作表，不涉及 Online 表单。

## 开场禁令（先执行，不要往下翻）

> **⚠️ 2026-09-17 重大事故更正 —— 正确性 > 速度。**
> 本 skill 曾为提速立过几条硬红线（「只准读两页」「整轮墙钟 5 分钟内」
> 「禁止打开 node-types / 入库审批示例」）。2026-09-16 照这些红线建 52 表应用时，
> **批量生成的 63 条简流全部不可用**：引擎契约（明细取关联记录 `selectType=3`、
> `callActivity` 的数据对象/并行/传 record id、`data_add` 全字段映射、
> 子流程数据源与「被以下工作流触发」登记）**一条都没发出去**，
> 而 `save/deploy/ADDED` 全部显示成功。根因就是「为了快，不读真实契约」。
> **以下规则以此为准，任何与「提速」冲突之处，一律以正确性优先。**

用户同一句要「应用 + 工作表 + 简流 + 仪表盘」（或同时点名 `/jeecg-lowcode-lowapp` + `/jeecg-lowcode-miniflow` + `/jeecg-lowcode-dashboard`）时：

1. 先读 `references/fast-full-chain.md` + `references/engine-contract.md`（编排顺序 + 引擎硬约束）。
2. **契约文档必须读，不得以「耗时」为由跳过**——按要做的东西选：
   - 生成**简流**：miniflow 的 `references/node-contract.md`（**每种节点的必填键**）+
     `create-flow.md`「常用节点组合」+ `miniflow-node-types.md` 对应节点节
   - 生成**明细子表**（工作表子表 / 关联记录）：`desform-link-record.md`「二-a」+ `fast-create.md`
   - 生成**看板**：dashboard `create.md`（布局 / 配色 / 按钮排布）
   - 生成**表单布局**：`app-spec.md`「`layouts`」节——**规格里必须给分节**，
     否则建出来是一长串单字段卡、零 divider（2026-09-17 布局事故）。
     已建好的表要补布局 → `scripts/regroup_layout.py --config layout.json`（可 `--dry-run`）
3. **「全绿」不是验收**：`save` / `deploy` / `ADDED` 成功、计数对得上，都**不能**证明配置落地
   （`engine-contract.md` 开头第一句就是这个）。验收 = **与已知正确产物逐节点/逐字段 diff**。
   建应用/建流程**必须**跑 diff 闸门（见 `fast-full-chain.md` 文末「交付闸门」）。
4. **批量引擎有覆盖边界**：`build_flows.py` + `flow_dsl` 只覆盖「审批 + 简单回写」。
   凡节点落在 `flow_dsl`「未覆盖」清单里（含**取关联多条明细、传 record id、
   子流程登记**），**必须先补齐引擎，或回落到手建**，禁止用最接近的助手硬套。
5. 动真机前先过 `scripts/precheck.py`（纯静态、不联网、可反复跑）：
   `python scripts/precheck.py --spec app_spec.json --flows flows.py`
6. 效率仍然要管，但**只在「功能完整、数据链与业务链都正确」的前提下优化**
   （并行读、脚本化、少轮次）；**任何提速手段都不得以跳过契约阅读或跳过 diff 为代价**。

用户说「租户 + 应用 + 建表/工作表/一对一」且是**新建**时：

1. **禁止 Read：** `jeecg-desform`、`jeecg-onlform`、`jeecg-system` 的 SKILL.md 全文。
2. **只读** `references/fast-create.md`。读完第一条 tool call 是：Write utf-8 `job.json` + 跑 `scripts/create_linked_worksheets.py`。
3. ⚠️ **例外（必须读）**：凡涉及**明细子表 / 工作表子表**（`isSubTable:true`、
   `model=sub_table_design_<key>`、`twoWayModel`、汇总 `linkTable`）或**关联带出的字段命名**，
   先读 `references/desform-link-record.md`「二-a」与 `fast-create.md`「建后补丁契约速查」——
   这一块的契约**不在** `create_linked_worksheets.py` 里，不读就会建成普通关联记录（布局与模板不符）。
4. 不要等 y/n。不要 `get_form_id` / `check_code_available` 探编码。消息没 token 时对 `prompt_history.jsonl` 搜一次 `jeecg-boot`+`eyJ`，没有就问一句。

用户说「改已有关联记录 / 显示方式改为下拉 / 记录范围 / 设置筛选条件 / 默认值第一条 / 查询工作表」时（工作表已存在）：

1. **立刻停止读本文件**。不要读 `desform-link-record.md`、`desform-linkage-query.md`、widget-options、filter-rules。
2. **只准 Read** `references/fast-link-record.md`。读完第一条 tool call 必须是：Write utf-8 job.json + 跑 `scripts/update_link_record.py`。不要手写 `filters`/`sqParam`/linkage 编码。
3. 中文字段名和「开头是 / 不等于 / 大于等于」原样写进 JSON，脚本解析 model。不要先 `get_form_fields`。

整轮墙钟 **2 分钟内**。超过 2 分钟 = 又在开场读文档或手写 `update_widget`。

用户说「给已有工作表**新增关联记录**字段（关联记录-多条/单条 + 卡片/下拉 + 设置筛选）」（目标工作表已存在，主表存在）：

1. **立刻停止读本文件**。不要读 `desform-link-record.md`、`desform-cross-form-binding.md` 全文。
2. **只准 Read** `references/fast-add-link-record.md`。读完第一条 tool call 必须是：Write utf-8 job.json + 跑 `scripts/add_link_record.py`。
3. 中文原话写进 JSON（`多条`/`卡片`/筛选 `等于 采购审批`），脚本解析 code/model/sqParam。不要先 `get_form_fields` 猜 model。

整轮墙钟 **1 分钟内**。超过 1 分钟 = 又在开场读文档或手写 `LINK_RECORD`。

---

## 读文档路由（先看这张表，再决定读不读后面）

本文件后半是表单设计器，前半夹了应用 CRUD。**按用户这句选一行，只读该行文件，读完立刻执行。** 不要把文末参考列表当必读清单，不要并行打开 `jeecg-desform` / `jeecg-onlform`。知识只从本 skill 的 `SKILL.md` / `references/` 获取；`scripts/` 只执行、禁止打开。禁止为补知识去读任何源码（见执行准则第 5 条）。

| 用户在说 | 只读 | 禁止读 |
|---------|------|--------|
| 同一句 **应用+工作表+简流+仪表盘**（全链路） | **只读** `references/fast-full-chain.md`，立刻跑脚本 | 本文件全文；miniflow/dashboard 的 SKILL.md；node-types；入库审批示例；widget-options；json-config；`memory_search` |
| 创建 / 复制 / 改名 / 删除 / 列出**应用** | **第一条 tool call 就是** `lowapp_creator.py`（参数见「创建 / 复制 / 编辑 / 删除应用」）。会话已有 api-base / token / 租户时 **零 Read** | 先读 `lowapp_creator.py` / `desform_lowapp_utils.py` / 本文件全文 / `desform-lowapp.md` |
| 在某租户 / 应用下**新建**工作表 / 一对一 | **只读** `references/fast-create.md`，立刻跑 `scripts/create_linked_worksheets.py`。只有「全新创建子表」才再读 `desform-new-sub-table.md` | 本文件全文；`lowapp-init.md`；`desform-lowapp.md`；`desform-cross-form-binding.md`；`desform-link-record.md`；应用 CRUD；`jeecg-desform` / `jeecg-onlform` / `jeecg-system` 的 SKILL.md；`widget-options`；`json-config` |
| 应用分组 / 工作表分组 / 改工作表名 / 删工作表 | `desform-lowapp.md` 用 grep 定位对应节，`Read` limit=50 | widget-options；json-config；应用 CRUD |
| 给已有**主表**加字段（点名了表+字段） | 文末「主表加字段只跑 add_widget」。会话已有 code 时 **零 Read**，第一条 tool call 就是 `add_widget` 脚本 | 本文件「更新已有表单」；加前/加后 `get_form_fields`；`save_auth_from_design`；工厂默认 type 的 widget-options |
| 改已有控件 / 删字段 / 子表加列 | 改/删：`grep -n "^## 更新已有表单"` Read limit=40。子表加列：文末「往已有子表加列」 | 本文件全文；`desform-lowapp.md`；应用 CRUD |
| 转为工作表 / 转换工作表 | `references/desform-new-sub-table.md`「转换工作表」+ `scripts/sub_to_worksheet.py`（两步接口，脚本一次跑完） | 只 POST 不改主表设计；猜 `id`/`key` 探测 |
| 改**列表视图**（数据统计 / 行高 / 刷新 / 数据过滤 / 看板 / 日历 / 甘特图） | 会话已有 api-base / token / 租户 / 应用时 **零 Read**，**第一条 tool call 就是** `desform_list_view.py`（参数见「列表视图一条命令」）。数据过滤 JSON 用字段中文名和界面值；**条件值形态按 `desform-filter-rules.md`「条件值形态实测」（禁数组）；系统字段/字符串日期直连 `updateViewConfig`（文末 2026-09-10）**。创建看板/日历/甘特缺字段规则才读 `desform-list-view.md` 对应节 | 现写临时 `.py`；先 `get_form_fields` / `query_form` 探路；`desform-list-view.md` 全文；`desform_view_creator.py`（那是表单视图） |
| 建表/改字段时给**关联记录**配记录范围或查询设置 | `references/desform-link-record.md`「二-b」调用场景，再读三或四；**写进创建 JSON / `LINK_RECORD`** | `desform-filter-rules.md`；`desform-super-query.md`；列表数据过滤；把 `filters` 和 `search` 互相写错 |
| 改字段**宽度 / 半行 / 整行**（敲敲云工作表） | 本 SKILL「追加：控件行宽度（半行/整行）实测」一节（整单 `query_form`→改→`save_design_from_file`） | 只 `update_widget` 写 `options.autoWidth`/`options.width` 就完事（UI 保存会重置）；把 widget-options 的 `autoWidth` 当行布局唯一事实 |
| 建表时给**新**关联记录配记录范围或查询设置 | 写入创建 JSON / `LINK_RECORD`（`fast-create.md` 的 job 或字段 options）。规则细节才读 `desform-link-record.md`「二-b」 | `desform-filter-rules.md`；列表数据过滤；把 `filters` 和 `search` 互相写错 |
| 改已有关联记录（显示方式 / 记录范围 / 筛选条件 / 默认值第一条 / 查询工作表 / 仅可选择有查看权限） | **只读** `references/fast-link-record.md`，立刻跑 `scripts/update_link_record.py`。查询工作表默认值（linkage）脚本已内置字符对象 + 整单保存（2026-09-02 修复）；历史遗留字符串形态兜底见 `fast-link-record-linkage.md`。文末「关联记录筛选条件」是同一条路径 | 手写 `update_widget`；`desform-link-record.md` 全文；`desform-linkage-query.md`；高级查询的 `field`/`val`；`valueType:"value"`；小写 `right_like` 当设计器 rule |
| 给已有主表**新增**关联记录字段（多条/单条 + 卡片/下拉 + 设置筛选；目标表已存在） | **只读** `references/fast-add-link-record.md`，立刻跑 `scripts/add_link_record.py`（中文筛选/模式直写，脚本解析 code/model/sqParam）。2026-09-03 实测后 `LINK_RECORD` 已支持 `filters=/search=/data_select_auth=` 显式参数，一次提交即带筛选，不要再先 add 再 update 补；**自己关联自己(target==主表)时脚本自动写顶层 `isSelf:true` → 自关联树,只有自关联才有 isSelf**(2026-09-04) | 手写 `LINK_RECORD` / `update_widget` 拼 filters；读 `desform-link-record.md` 全文；`desform-filter-rules.md`；复用 `update_link_record.py`（那只改已有控件） |

`references/desform-lowapp.md` 文首写「提及应用就必须先读全文」——**以本表为准，不要打开它除非上表第三行。** 不要改那个文件。

---

## 执行准则

> 租户+应用下建表/一对一：以文首「开场禁令」为准，本节不是开场必读。

本技能的所有强制规则，都在对抗同一个 AI 倾向：**用"我大概知道"替代"我确认知道"**。

**跳步**：校验、确认、读文档看似多余——AI 倾向于省略。但每个步骤都是防错设计，省略后出错时代价是数据损坏或 API 异常，且无法回头。

**猜测**：系统特定的编码、API 参数格式、控件配置细节，训练知识不够用，但 AI 会用"看起来合理"的值填补——配置看似正确，运行时才报错。

本系统有大量与通用认知冲突的特殊行为（API 接口不可靠、参数大小写有严格要求、控件结构非直觉、部分值只存在于用户自己的系统中）。**你对这个系统的了解程度，不如这份文档和用户本身。**

遇到任何操作，遵守以下六条：

1. **步骤不可跳** — 感觉没必要时仍要执行，这是防错机制而不是形式。**不包括**把会话里已经确认过的 ID / 字段映射再查一遍，见文末「会话缓存」
2. **有专属文档的功能先读文档** — 通用知识在本系统大概率是错的，文档记录的是实测验证的行为
3. **系统特定的值必须问** — 无法从当前上下文确认的参数（规则 Code、报表编码、业务 ID 等），直接告知用户"需要您提供 X"，不要猜测
4. **会话已有的值直接用** — 从对话记录取 `api-base` / `token` / `tenant_id` / `app_id` / 表 code / `view_id` / 字段 model。禁止再 list、禁止再 `get_tenants`。**禁止把「要不要再读 SKILL、要不要再查租户」当思考步骤**——会话齐了，第一条 tool call 必须是带这些参数的变更命令。
6. **整单补丁首轮必做审计，禁止单独开审计轮回查** — 适用范围是一切整单补丁（含手写补丁脚本）：每表首趟 `query_form` 时同步核对「建表声明的字段/子表列是否都在 + 本表所有补丁项目标态」，逐表输出 ✓/✗；保存接口返回 success / 打印 `[OK]` 不等于内容落上（坏公式、叠控件均静默成功，2026-09-15 实测）。**遍历须递归到 tabs 的 `panes[].list`**（2026-09-16：漏遍历误报字段缺失）。细则见 `references/fast-create.md`「大批量提速流程」强制条。
5. **禁止读源码，知识只从本 skill 文档来** — 控件档位、接口行为、函数签名、下拉选项只从 `SKILL.md` 和 `references/` 获取（按文首路由点名片段，`grep` 只打 `references/*.md`）。**禁止** `Read`/`Grep`：本 skill 的 `scripts/*.py`、用户工程、JeecgBoot/敲敲云前后端（`.vue` `.java` `.ts` 等）。`scripts/` 只按文档里的命令执行，不要打开核对 argparse / 函数实现。skill 没写就问用户，不要去翻源码补。

> 编号说明：第 6 条为 2026-09-15 补丁环节踩坑后新增，插在 5 之前以保持「禁止读源码」紧随「先读文档」，执行优先级与顺序无关。

**第 2 条的执行方式（强制）：** 先查文首「读文档路由」，只读该行指定文件。租户+应用下建表/一对一 = 只读 `fast-create.md`；改已有关联记录 = 只读 `fast-link-record.md`；已有表新增关联记录字段 = 只读 `fast-add-link-record.md`。不是本文件后半。不确定某功能在哪时，再在文末参考列表里点名那一份，`grep` 定位后按片段读。参考列表不是开场必读清单。

---

## 临时配置文件规则（强制）

所有传给脚本的 `--config <xxx.json>` 必须放在 **`{系统临时目录}/jeecg-desform/`** 下，由操作系统自动清理；skill 与脚本均不主动删除该目录或文件。

`tempfile.gettempdir()` 自动适配各平台：Windows `%TEMP%`、Linux `/tmp`、macOS `/var/folders/.../T`（注意 macOS 并非 `/tmp`）。文件名建议使用 **`<表名>_<步骤>.json`**（如 `sk_audit_create.json`），路径已含技能名称无需重复前缀。

### 场景一：Claude 用 `Write` 工具写文件后调脚本（最常见）

`Write` 工具需要绝对路径，所以**必须先**通过公共脚本拿到路径。脚本一次完成「定位系统临时目录 → 创建技能子目录 → 返回路径」：

```bash
# 取目录
python "<skill目录>/scripts/skill_temp_path.py"
# → C:\Users\xxx\AppData\Local\Temp\jeecg-desform

# 直接拿完整文件路径（推荐）
python "<skill目录>/scripts/skill_temp_path.py" -f sk_audit_create.json
# → C:\Users\xxx\AppData\Local\Temp\jeecg-desform\sk_audit_create.json
```

得到路径后：
1. 用 `Write` 工具将 JSON 写入该路径
2. 调脚本 `--config <该路径>`

**会话内目录可复用**——首次取到后缓存到上下文，后续临时文件直接拼接同一前缀，不必每次重新调用脚本。

### 场景二：技能内的 Python 脚本自行写中间文件

skill 自己的脚本（`desform_creator.py` 等）在脚本进程内写文件时，**不要**通过 `Write` 工具，直接用 `tempfile`：

```python
import tempfile, os, json

skill_dir = os.path.join(tempfile.gettempdir(), "jeecg-desform")
os.makedirs(skill_dir, exist_ok=True)          # 确保目录存在，不主动检查

config_path = os.path.join(skill_dir, 'sk_audit_create.json')
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
```

### ❌ 禁止

- 写到 `<skill>/tmp/` 或当前工作目录（污染 skill / 用户项目）
- 硬编码 `/tmp`、`C:\Temp` 或任何固定路径（不跨平台）
- 每步完成后主动 `rm` / `Remove-Item`（操作系统会清理，属多余 tool call）
- 主动 `os.path.exists()` 检查（其本身即为一次 tool call）
  （`os.makedirs(…, exist_ok=True)` 与 `skill_temp_path.py` 都已隐式建目录，无需另外检查）

### 文件丢失补救

**临时文件可能被操作系统异步清理**，但仍遵循 **乐观调用 + 报错补救**：仅当脚本返回 `FileNotFoundError` 或 `配置文件不存在` 时，使用相同内容、**在相同的 `{系统临时目录}/jeecg-desform/` 路径下重写**（重写前重新调一次 `skill_temp_path.py` 或 `os.makedirs(skill_dir, exist_ok=True)` 确保目录存在），切勿更换路径或回退至 skill 目录。

---

## lowApp 模式（敲敲云 / 零代码模式）

当用户提及以下任一场景时，**先按文首「读文档路由」选路径**，不要默认打开 `references/desform-lowapp.md`：

- 用户说「工作表」（而非「表单」）
- 用户说「在 xxx 应用下」「应用里」「某个应用中」
- 用户说「敲敲云」「零代码」「lowApp」
- 用户提到「组织」「租户」（作为操作对象，而非系统权限配置）

lowApp 模式下：
- 表单设计器表单 = **工作表**（概念同，名称不同）
- 需要「组织（租户）+ 应用」两级上下文
- 初始化用 `init_lowapp`，**不是** `init_api`（步骤见 `references/lowapp-init.md`）
- 初始化后，`create_form`、`add_widget` 等所有表单操作函数**无需修改**，自动生效
- 应用分组 / 工作表菜单 / `menu_id` 对照：才读 `references/desform-lowapp.md` 对应节；函数签名见 `references/desform-lowapp-utils.md`（按函数名 grep，不要全文）

### 创建 / 复制 / 编辑 / 删除应用

操作**应用本身**（不是工作表）时：一条命令调用 `scripts/lowapp_creator.py`，禁止先写临时文件。`--api-base` / `--token` / 租户 从当前用户消息取，禁止写死。

**零预读：** 会话已有地址 / token / 租户时，禁止再 `Read` 任何文件（包括本 SKILL、`lowapp_creator.py` 源码）。第一条 tool call 必须是执行脚本。参数以本表为准，不要打开源码核对 argparse。

**创建应用必须由用户传租户 ID 或租户名称**，两者都没有就停下问，禁止猜测。给的是名称时：脚本内先 `get_tenants()` 按名称精确匹配得到 ID，**再新增应用**；匹配不到或多条同名则报错，不要自己挑。图标/颜色/封面：用户传了用用户的，没传不要问、不要写进 JSON，脚本用默认值 `ant-design:schedule-outlined` / `rgb(0, 188, 212)` / `coverImage002`。

```bash
python "<skill目录>/scripts/lowapp_creator.py" --api-base <用户地址> --token <用户token> --tenant-id <用户租户ID> --json "{\"action\":\"create\",\"appName\":\"应用名\"}"
python "<skill目录>/scripts/lowapp_creator.py" --api-base <用户地址> --token <用户token> --tenant-name <用户租户名称> --config <utf8.json>
```

| 用户意图 | `--json` |
|---------|----------|
| 创建应用 | `{"action":"create","appName":"应用名"}` |
| 复制应用 | `{"action":"copy","id":"<被复制的应用ID>"}` → `GET /online/lowApp/copy?id=` |
| 编辑应用 | `{"action":"edit","fromName":"旧名称","appName":"新名称"}` → 脚本内先查再 `PUT /online/lowApp/edit`（有 id 就直接传 `id`，不要先单独 list；只写要改的字段） |
| 删除应用 | `{"action":"delete","id":"<应用ID>"}`（先确认，会级联删工作表和数据） |
| 应用列表 | `{"action":"list"}` |

JSON 只放用户明确给的业务字段，不要写 tenantId / token / 地址。

---

## 前置条件

用户必须提供以下信息（或由 AI 引导确认）：

1. **API 地址**：JeecgBoot 后端地址（如 `https://boot3.jeecg.com/jeecgboot`）
2. **X-Access-Token**：JWT 登录令牌（从浏览器 F12 获取）

如果用户未提供，提示：
> 请提供 JeecgBoot 后端地址和 X-Access-Token（从浏览器 F12 → Network → 任意请求的 Request Headers 中复制）。

### API 初始化（统一入口）

所有 Python 操作前都需要先初始化 API 连接。`init_api` 只存在于 `desform_utils.py` 中，其他模块（如 `desform_data_utils.py`）不包含此函数——错误导入会导致 ImportError。

```python
import sys
sys.path.insert(0, r'<skill目录>/scripts')
from desform_utils import init_api
init_api('<api_base>', '<token>')
```

后续按需从各模块导入函数，查阅函数详细说明时：
**先 grep 函数名定位行号，再用 offset+limit 读取对应章节，不要全量阅读文档。**

```bash
# 示例：查 update_design_config 的用法
grep -n "## update_design_config" references/desform-python-utils.md
# 得到行号后：Read 该文件，offset=<行号-1>, limit=40
```

### desform_utils 函数速查表

完整函数列表见 `references/desform-python-utils.md`；列表视图函数见 `references/desform-list-view.md`。

| 函数 | 适用场景 |
|------|---------|
| **表单生命周期** | |
| `check_code_available(code)` | 新建前校验编码唯一性 |
| `create_form(name, code, widgets, ...)` | 一站式创建表单（查找/创建→保存设计→同步权限） |
| `update_form(code, widgets, ...)` | 整体重设计已有表单 |
| `update_design_config(code, config_updates)` | 只改配置不改控件（发布/通知/打印/业务规则等） |
| `query_form(code)` | 查询表单完整信息（含设计JSON） |
| `get_form_fields(form_code)` | 获取所有字段的 model/key/type 映射 |
| **字段级操作** | |
| `add_widget(code, widget_or_widgets)` | 追加字段到已有表单末尾 |
| `update_widget(code, changes, *, key=None, model=None)` | 修改字段属性（优先传 key=） |
| `delete_widget(code, *, key=None, model=None)` | 删除字段（优先传 key=） |
| **设计JSON预处理** | |
| `export_design_json(code, output_path)` | 导出设计JSON到文件（用于手动修改场景） |
| `save_design_from_file(code, file_path)` | 将修改后的文件保存回后台 |
| `extract_field_table_from_design(design_json)` | 从设计JSON提取字段参照表（不调用API） |
| **工具** | |
| `query_dict(dict_code)` | 查询字典项列表 |
| `search_dict(keyword)` | 按名称/编码模糊搜索字典 |
| `gen_menu_sql(parent_name, children, ...)` | 生成菜单和角色授权SQL |

## 主数据复用规则

表单字段配置**系统字典 / 角色 / 部门**时，遵循"先查后建"。静态 radio/select 选项（直接写 `["待支付","已支付"]`）**不要**加载 `jeecg-system`。

> 需要查/建字典或角色时才用 `jeecg-system` 的 `system_utils.py`。
>
> ⚠️ 租户下取成员/部门：`init_lowapp` 后经 `api_request` 调 `/sys/user/selectUserList`（成员，存 username）、`/sys/sysDepart/queryTreeList`（部门，存 id）；裸用 `system_utils` 用户为空、部门树是全局的。

**敲敲云应用级字典（不是全局字典）**：用 `scripts/lowapp_dict.py` 管理，说明见 `references/lowapp-dict.md`。接口为 `/sys/dict/getDictListByLowAppId`、`/sys/dict/addDictByLowAppId`、`/sys/dict/editDictByLowAppId`、`/sys/dict/delete`，请求必须带 `x-tenant-id` 和 `x-low-app-id`（脚本已处理）。不要用全局 `/sys/dict/add` 去建敲敲云应用字典。

---

## 创建表单

**敲敲云（租户+应用下建表/一对一）：跳过本节 §1–4。** 走文首开场禁令 + `references/fast-create.md` + `scripts/create_linked_worksheets.py`。不要在本节做编码预探、widget-options 全文、y/n、`get_form_id`。

### 1. 解析用户需求

从用户描述中提取：表单名称、表单编码（英文命名，模块名前缀）、字段列表、字段属性。

**布局选择规则：** 默认使用普通布局（`auto`/`half`/`full`），不要主动使用 Word 风格。只有当用户明确要求时才使用 `layout: "word"`——例如用户说"Word风格"、"表格边框样式"、"像Word文档那样"等。即使表单是审批单、申请表等看起来适合 Word 风格的场景，也不要自行判断使用 Word 风格，而是让用户来决定。

**编码唯一性校验（新建表单时）：**

创建新表单时，生成 `desformCode` 后立即执行编码校验，在校验通过前不要展示摘要让用户确认。原因：用户确认摘要后会期望直接执行成功，如果执行时才发现编码冲突，体验很差，且可能意外覆盖已有表单数据。

```python
from desform_utils import init_api, check_code_available
init_api('<api_base>', '<token>')
result = check_code_available('<code>')  # 只接受 1 个参数
# True → 编码可用  |  False → 已占用，自动换一个编码重试
```

### 2. 识别字段并选择控件类型

根据用户描述的关键词（也可能是图片），匹配对应的控件 type——**下方自动注入的索引表已含「关键词 → 控件」映射**（`WIDGET_OPTIONS_INDEX` 区块的「关键词」列），直接据此选型。

**【强制】确定控件类型后、配置其属性前，必须先阅读 `references/desform-widget-options.md` 中该控件对应的片段**——按**下方自动注入的行号索引表**查到该控件的 `offset` / `limit`，直接 `Read` **只读那一段**（该文档很长，禁止全量读，无需 grep）。原因：许多控件有非直觉的内置能力，只看 `desform_utils.py` 工厂函数的默认 options 会把它们当成"无用的空字段"漏掉——典型如日期的 `dateType`（年/季/周）。敲敲云不展示选人/选部门的 `keyMaps` 和 `customReturnField`，不要配。不要凭训练知识假设某字段不存在或猜它的名字。

<!-- WIDGET_OPTIONS_INDEX:START -->
!`python ${CLAUDE_SKILL_DIR}/scripts/gen_widget_options_index.py 2>/dev/null || echo '> （控件选项索引自动生成失败，请用 grep -n "## <控件type>" references/desform-widget-options.md 定位行号后再 Read 该片段）'`
<!-- WIDGET_OPTIONS_INDEX:END -->

对于 radio/select/checkbox 控件，支持静态选项（默认）和系统字典两种数据源。

> 详见 `references/desform-dict-config.md` — 字典配置方式、常用字典编码、Python 快捷函数用法。

**⛔ 敲敲云禁用控件（禁止生成）：** `table-dict`、`select-tree`、`cascader`、`category-linkage`（联动）、全部 OA 字段。以本行为准，不要为此打开 `desform-lowapp.md`。

**⚠️ 选项颜色强制约束（radio / select / checkbox 的 `itemColor`）：**
系统前端硬编码了 20 个合法颜色值，设置 `itemColor` 时必须严格从这 20 个值中选取，禁止使用任何范围外的颜色（包括视觉上接近的近似色，如 `#FF9800` ≠ `#FF9300`，`#9C27B0` ≠ `#7500EA`，`#F44336` ≠ `#F52222`）。同时必须将 `useColor` 设为 `true`，否则颜色在甘特图/看板视图中不生效。
> 完整颜色表见 `references/desform-widget-options.md` 顶部「选项颜色合法值约束」章节（强制查阅，不可凭记忆填写颜色值）。

### 3. 展示表单摘要并确认

**敲敲云工作表例外：** 用户已给地址 + token + 租户（ID 或名称）+ 应用（ID 或名称）+ 表名（及关系），视为已授权执行——**跳过本节，不要等 y/n**。走 `references/fast-create.md`。

其余场景展示以下内容，等待用户确认后再执行：

```
## 表单摘要
- 表单名称：{name}
- 表单编码：{code}（已通过校验）
- 目标环境：{API_BASE}

### 字段列表
| 序号 | 字段名称 | 控件类型 | 必填 | 说明 |
|------|---------|---------|------|------|
| 1 | ... | ... | ... | ... |

确认以上信息正确？(y/n)
```

### 4. 防覆盖检查

用户确认后、执行创建前，通过 `get_form_id(code)` 检查编码是否已存在。这是防止误覆盖的最后一道安全网——编码校验只检查当前时刻，而从校验到执行之间可能有其他人创建了同编码表单。

如果表单已存在：
1. 告知用户：`表单 {code} 已存在 (ID={id})，是否要覆盖更新？`
2. 用户确认后才执行覆盖（调用 `update_form`）
3. 用户拒绝覆盖时，基于原编码生成 3~5 个新编码供选择

### 5. 生成 JSON 并调用 API

使用 `scripts/desform_creator.py` + JSON 配置文件创建表单。这个脚本封装了完整的 JSON 构造逻辑（控件包裹、key/model 生成、跨控件引用等），比手动拼 JSON 更可靠，也更不容易出错。

**⚡ 预处理优先原则（存在创建后需要修改的属性时）：**

执行创建前，先判断是否存在 JSON config **无法直接配置**、但需要创建后额外操作的属性，常见场景包括：

- 字段默认隐藏（`hidden: true`）—— JSON config 不支持此参数
- 业务规则（`bizRuleConfig`）
- JS / CSS 增强代码
- 控件深层嵌套属性的精确修改

如果存在以上任一需求，**优先使用 `--preprocess` 模式**，在一次创建流程内完成所有修改，避免创建后再调用 `update_widget` / `update_design_config` 等额外步骤。

> 详见本文档「设计 JSON 预处理 → 场景一：创建表单时预处理」章节。

⛔ **执行前必须判断字段数量，选择正确方式——禁止在字段数 ≤50 时使用临时文件：**

**默认方式：常规表单（≤50 个字段）** → stdin 管道，一条命令完成，无需临时文件：
```bash
echo '<json_config>' | python "<skill目录>/scripts/desform_creator.py" --api-base <URL> --token <TOKEN> --config -
```

**仅当字段 >50 时** → 临时文件方式，避免管道传输大量数据时的稳定性问题：
1. 根据「临时配置文件规则（强制）」章节，将 JSON 配置写到 `{系统临时目录}/jeecg-desform/<表名>_create.json`
2. 执行脚本：`python "<skill目录>/scripts/desform_creator.py" --api-base <URL> --token <TOKEN> --config <config.json>`
3. **不要**主动删除该文件，操作系统会自动清理

> 详见 `references/desform-json-config.md` — JSON 配置格式、字段定义、子表说明、完整示例。

**脚本自动处理的跨控件引用：**
- **capital-money（大写金额）**：优先通过 JSON 中的 `moneyField`（字段中文名）解析关联目标，未指定时兜底查找前面最近的 `money`/`formula`/`summary` 控件。当大写金额与目标字段不相邻时，必须显式传入 `moneyField`
- **summary（汇总）**：`linkTable`（子表中文名）和 `field`（子表列中文名）自动解析为实际 model；`filter.rules` 中的 `field` 也支持中文名自动解析
- **formula（公式）表达式**：支持使用字段中文名作为占位符（如 `$预算总额$`），自动解析为实际 model
- **Word 布局下的 divider（分隔符）**：自动包裹在 `span=24`、`isWordStyle=true` 的 grid 容器中

> 脚本已自动处理 JSON 结构规则（card 容器、key/model 生成、className/icon、控件跨引用等）。如需排查或手动构造，详见 `references/desform-design-json-schema.md`。

> **多表互相关联场景**（2+ 个表单通过 link-record 互相引用）：敲敲云用 `scripts/create_linked_worksheets.py`（见 `references/fast-create.md`），不要手写、不要先读 `desform-cross-form-binding.md`。
>
> **关联记录的「筛选条件」和「查询设置」是建表时写在该控件 `options` 上的**（`filters` vs `search` 先看 `desform-link-record.md`「调用场景」）。用户说了就随创建 JSON / `LINK_RECORD` 一起提交；没说保持默认。禁止拿去配列表数据过滤或高级查询。

**降级方案：** 如果脚本执行失败，先向用户说明失败原因，经用户确认后可降级为手动构造 JSON。
> 详见 `references/desform-fallback-manual-json.md` — 手动构造 desformDesignJson 的完整指南。

### 6. 检查结果与权限

- `success: true` → 表单创建成功，脚本会自动创建字段权限
- `success: false` → 输出错误信息，参见 `references/desform-api-notes.md` 错误处理表
- 权限创建失败不会阻断主流程（仅输出警告），可用 `scripts/desform_auth_retry.py --api-base <URL> --token <TOKEN> --code <form_code>` 重试

### 7. 输出结果

```
## 表单创建成功
- 表单ID：{id}
- 表单名称：{desformName}
- 表单编码：{desformCode}
- 目标环境：{API_BASE}

请在表单设计器中查看：打开 JeecgBoot 后台 → 表单设计器 → 找到该表单
```

同时输出菜单 + 角色授权 SQL（用于将表单设计器加入系统菜单）。

> 详见 `references/desform-menu-sql.md` — gen_menu_sql 调用方式、输出格式、SQL 字段说明、本地自动执行规则。

当 `api_base` 以 `http://127.0.0.1` 或 `http://localhost` 开头时，通过 MySQL CLI 自动执行菜单 SQL。

---

## 更新已有表单

所有更新相关的函数详见 `references/desform-python-utils.md`。

### 更新流程

1. 获取现有表单信息：`get_form_fields(code)`
2. 分析用户需求，确定操作类型（添加/修改/删除/整体重设计）
3. 展示变更摘要（新增/修改/删除的字段列表），等待用户确认
4. 执行操作
5. 自动同步权限

### 整体重设计

如果用户要全面修改已有表单：
1. 查询现有表单设计 JSON：`query_form(code)` 或 `get_form_fields(code)`
2. 根据用户需求重新组装控件列表
3. 调用 `update_form(code, new_widgets)` 保存（自动获取 `updateCount`）

### 字段级操作

如果用户只是添加/修改/删除个别字段：
- **添加字段**：`add_widget(code, widget)` — 向已有表单追加控件
- **修改字段属性**：`update_widget(code, changes_dict, *, key=None, model=None)` — 修改指定控件属性，优先传 `key=`。⚠️ 调用前先确认目标属性是否属于组件选项（options 子层），如果是必须套 `{"options": {...}}`，否则后端静默失败
- **删除字段**：`delete_widget(code, *, key=None, model=None)` — 删除指定控件，优先传 `key=`
- 操作后自动同步权限：`sync_auth(code, design_list, form_id)`

---

## 设计 JSON 预处理

当脚本能力不足以满足需求时（例如创建后还需要精确修改某个控件的嵌套属性），可以使用预处理模式——让脚本把生成的设计 JSON 输出到临时文件，AI 用文本工具手动修改后再统一保存。

### 场景一：创建表单时预处理

正常创建命令加 `--preprocess` 参数（管道符和临时文件方式均支持）：

```bash
echo '<json_config>' | python "<skill目录>/scripts/desform_creator.py" \
    --api-base <URL> --token <TOKEN> --config - --preprocess
```

脚本会：
1. 在后台创建表单实体（获得 form_id），但**跳过**保存设计 JSON
2. 将生成的设计 JSON 写入临时文件（格式化缩进）
3. 打印所有字段的标题 / key / model 参照表

AI 使用 Read/Edit/Write 工具修改临时文件，完成后调用保存：

```python
from desform_utils import init_api, save_design_from_file
init_api('<api_base>', '<token>')
save_design_from_file('<form_code>', r'<临时文件路径>')
```

### 场景二：修改已有表单时预处理

```python
from desform_utils import init_api, export_design_json, save_design_from_file
init_api('<api_base>', '<token>')

# 1. 导出当前设计 JSON，同时打印字段参照表
file_path, field_rows = export_design_json('<form_code>')

# 2. 使用 Read/Edit/Write 工具修改 file_path 中的内容

# 3. 保存修改后的设计 JSON
save_design_from_file('<form_code>', file_path)
```

---

## 复制表单

`copy_form(source_code, new_code)` 可快速复制已有表单的设计 JSON 创建新表单。适用于基于现有表单创建类似表单（如复制"请假申请"改造为"出差申请"）。

流程：
1. 用户提供源表单编码和新表单编码
2. 校验新编码可用性（`check_code_available(new_code)`）
3. 调用 `copy_form(source_code, new_code)` 完成复制
4. 如需修改，使用 `update_form` 或字段级操作调整

## 删除表单

`delete_form` 已封装完整的删除流程（查找 → 逻辑删除 → 物理删除），支持传 code 或 ID。

> 详见 `references/desform-api-notes.md` — 删除流程、注意事项。

## 视图类型说明（消歧）

desform 有两种完全独立的视图概念：

| 类型 | 控制内容 | 触发关键词 |
|------|---------|-----------|
| **列表视图** | 数据记录在列表页如何展示（表格/看板/日历/甘特图） | 用户直接说"视图"、"新建视图"、"看板"、"日历"、"甘特图"等 |
| **表单视图** | 填报表单时字段的布局和显示方式（PC/移动端） | 用户明确说"表单视图"、"移动端视图"、"移动视图" |

**默认规则：用户说"视图"时，默认理解为列表视图。只有明确提到"表单视图"或"移动视图/移动端视图"时，才处理表单视图。**

---

## 列表视图

列表视图控制数据记录在列表页的展示方式，支持四种类型：

| 类型 | 说明 | 必要配置 |
|------|------|---------|
| **表格** | Table 组件逐行显示，最常规 | 无 |
| **看板** | 按字段值分列展示卡片（也称卡片视图） | 分组字段（限单选/下拉/开关/人员/表字典/关联记录单条，且非多选） |
| **日历** | 数据挂载到日历显示 | 至少 1 个日期字段；可选开始+结束；可多组 |
| **甘特图** | 时间线任务展示 | 1 个开始日期 + 1 个结束日期（均必填） |

> **注意：创建表单时系统会自动生成一个默认的表格列表视图，无需主动调用视图创建方法。只有用户明确要求"创建看板"、"添加日历视图"、"新增甘特图"等时，才需要操作列表视图。**

> 改已有列表视图（数据统计 / 行高 / 自动刷新 / 关未排期等）**禁止现写临时 `.py`**，用 `scripts/list_view/desform_list_view.py`（见「列表视图一条命令」）。字段规则见 `references/desform-list-view.md`。

### 列表视图一条命令

操作**列表视图**时：一条命令 `scripts/list_view/desform_list_view.py`，禁止先写临时 Python。`--api-base` / `--token` / 租户 / 应用从会话取。会话已有 `view_id` 就传 `viewId`，禁止再单独 list。

```bash
python "<skill目录>/scripts/list_view/desform_list_view.py" --api-base <用户地址> --token <用户token> --tenant-id <租户ID> --app-id <应用ID> --json "{\"action\":\"config_table\",\"code\":\"<code>\",\"viewId\":\"<id>\",\"hasSummary\":false}"
python "<skill目录>/scripts/list_view/desform_list_view.py" --api-base <用户地址> --token <用户token> --tenant-name <租户名> --config <utf8.json>
```

| 用户意图 | `--json` |
|---------|----------|
| 关/开数据统计 | `{"action":"config_table","hasSummary":false}` |
| 行高 / 自动刷新 | `{"action":"config_table","lineHeight":"small","autoRefresh":60}` |
| 自定义显示列 | `{"action":"config_table","showColumn":"diy"}` |
| 与表单字段保持一致 | `{"action":"config_table","showColumn":"default"}` |
| 字段全部显示 | `{"action":"config_table","showAll":true}`（业务字段 + 写死 6 个系统字段：`create_time`/`create_by`/`update_time`/`update_by`/`sys_org_code`/`bpm_status`） |
| 显示列全部隐藏 | `{"action":"config_table","showAll":false}`（整表回写 `show:false`，禁止清空 `columnList`） |
| 只显示指定字段 | `{"action":"config_table","fieldNames":["单选框组","金额"]}`。**没说「组件/控件」就按字段中文名** |
| 隐藏指定字段 | `{"action":"config_table","hideFieldNames":["金额","整数"]}`。同样默认按字段名，其它列不动 |
| 只显示 / 隐藏某类组件 | 仅当明确说组件/控件类型：`showTypes` / `hideTypes` |
| 查视图列表 | `{"action":"list","code":"..."}` |
| 改视图类型 | `curl -X PUT "<api>/desform/view/updateViewConfig" -H "X-Access-Token: <token>" -H "X-Tenant-Id: <租户>" -d '{"id":"<viewId>","type":"base"}'`（实测 2026-09：type 可直接改，base=表格/card=看板/calendar=日历/gantt=甘特；改表格后原甘特字段 ganttFields 残留无害，前端按 type 忽略；⚠️ 视图列表 lite 接口的 type 有映射错位不可信，验证以 `queryById` 为准） |
| 甘特图关未排期 | `{"action":"update_gantt","viewId":"...","showUnscheduled":false}` |
| 甘特图设置（仅甘特视图） | `{"action":"update_gantt","viewId":"...","startField":"第一段开始日期","endField":"第一段结束日期","defaultView":"week","autoRefresh":60,"showUnscheduled":false}`。startField/endField 可写中文名，仅限 date/datetime 字段（year/month 不支持，对齐 UI GanttViewFieldSelect）且两端类型须一致，脚本自动维护 `dateType`；defaultView=day/week/month/quarter/year；autoRefresh 档位 0/30/60/120/180/240/300；显示字段：`ganttShowAll`/`ganttHideAll`/`ganttFieldNames`/`ganttHideFieldNames`（列表格式 `{key, field:model, show, seq}`，新字段默认隐藏）；省略项保持现状 |
| 配置默认排序 | `{"action":"config_sort","viewId":"...","orders":[{"field":"名称","type":"desc"},{"field":"金额1","type":"desc"}]}`。orders 的 `field` 写字段中文名（脚本自动转 model），`type` 只认 `asc`/`desc`，数组顺序即优先级，清空排序传 `orders:[]`。未点名视图时作用于全部表格视图（通常即默认表格视图），点名 viewId/viewName 时对任意视图类型生效 |
| 数据过滤 / 筛选组 | `{"action":"config_data_filter","matchType":"and","conditions":[...]}`。条件里写**字段中文名**和界面值（`name`/`rule`/`val`），组用 `match_type`+`items`。脚本内补 model、选项落库值。**取值形态见 `desform-filter-rules.md`「条件值形态实测」（禁数组）；系统字段/字符串日期直连 `updateViewConfig`（文末 2026-09-10）**。禁止先查字段 |
| 左侧筛选列表（仅表格视图） | `{"action":"config_left_filter","leftFilterField":"单选框组1","leftFilterData":"part","leftFilterCondition":["高中","本科"],"leftFilterOrder":"asc","addFormDefaultStatus":true}`。leftFilterField 写字段中文名，类型限 `link-record/table-dict/radio/checkbox/select/select-tree/select-user/select-depart/select-depart-post/org-role`（对齐 UI Shaixuanliebiao，其它类型报错）；**可用系统字段：创建人/修改人/所属部门/流程状态**（创建/修改时间 datetime 不可用，对齐前端 useFieldSelect）；data=all\|exist\|part；part 指定项 condition 可传数组自动转逗号串；未传项保持视图现状；清除：`{"action":"config_left_filter","clear":true}` |
| 配置快速筛选（字段名版，仅表格视图） | `{"action":"config_quick_filter","fieldNames":["创建时间","金额1","单选框组1"]}`。写字段中文名，脚本自动转 model，type/queryType 按 **UI 实测映射表**匹配（文本类 like、数值/单选/日期类 eq、展示类 empty；系统列：创建时间=datetime、创建人=select-user、所属部门=select-depart、流程状态=select），数组顺序即筛选栏顺序。完整映射见 `desform-list-view.md`「config_table_quick_filter」；未收录控件或需自定义用 `queryList` 显式传 `[{field,type,queryType,seq}]`（field 为 model）。两者只给一个 |
| 创建看板 / 日历 / 甘特 | `{"action":"add_board","groupField":"状态"}` 等；分组/日期字段规则才读 `desform-list-view.md` 对应节 |
| 看板设置修改（仅看板视图） | `{"action":"config_board","viewId":"...","groupField":"单选框组1","filterGroupType":"part","filterGroupCondition":["值1","值2"],"titleField":"邮箱1","showLabel":false,"coverField":"none","coverView":true}`。groupField 限 `radio/select/select-user/table-dict/link-record/switch`（对齐 UI Kanbanshezhi.vue）；filterGroupType 只有 `all`/`part`（看板无 exist）；改 groupField 自动清空条件；titleField 限 `input/textarea/money/integer/number/phone/email/link-record/select-user`；coverField 限 imgupload 字段或 `none`；省略项保持现状；卡片显示字段用 `cardShowAll`/`cardHideAll`/`cardFieldNames`/`cardHideFieldNames`（新增字段默认隐藏，对齐 LHZP-718）；可只传 viewId |
| 日历设置修改（仅日历视图） | `{"action":"config_calendar","viewId":"...","calendarDefault":"timeGridWeek","firstDay":1,"weekStatus":true,"weekDayList":["0","6"],"lunarStatus":true,"hourStatus":true,"titleField":"邮箱1"}`；日期分组：`dateColumns`/`calendarColumnList` 每项 `begin_field`/`end_field` 可写中文名 + `tag` + `type`（字段限 date/year/month/quarter/week/datetime 系）。calendarDefault=dayGridMonth（月）\|timeGridWeek（周）\|timeGridDay（日）；firstDay 0-6（0=周日）；weekStatus=true 且未传 weekDayList 默认隐藏周六日 `["0","6"]`、false 则清空（对齐 UI）；**titleField 存 model**（与看板存 key 不同），限 input/textarea/money/integer/number/phone/email/link-record/select-user；省略项保持现状；可只传 viewId |

显示列点名（显示和隐藏同一规则）：**没说「组件」「控件类型」就当字段中文名**（显示用 `fieldNames`，隐藏用 `hideFieldNames`）。只有明确说组件/控件才用 `showTypes` / `hideTypes`。禁止把「金额」「整数」当成 money/integer 类型。

数据过滤同样用字段中文名：`{"name":"名称","rule":"like","val":"刘"}`；选项写「高中」不要写 `2`，开关写 `"Y"`/`"N"`，月份写 `"2026-09"`；**条件值形态按 `desform-filter-rules.md`「条件值形态实测」（禁数组）**；系统字段或字符串日期直连 `updateViewConfig`（文末 2026-09-10）。**禁止**先 `get_form_fields` / `query_form` 探路；可用 `rule` 在脚本里校验（不合法会报错列出）。仍优先跑 `desform_list_view.py`。

有名称没 ID：先 `query_list_views(code)` 拿 id。未点名视图时：只有一张表格视图就改它，多张表格全部改。Windows 中文写进临时 `.py`，禁止 PowerShell `python -c '{"中文"}'`。

---

## 表单视图

创建表单视图（PC 表单视图、移动端表单视图）时，优先使用 `scripts/desform_view_creator.py` 通用脚本，支持复制主表单视图或自定义字段两种模式。

> 详见 `references/desform-view-config.md` — 创建流程、JSON 配置格式、移动端优化规则、踩坑汇总。

## 自定义动作（自定义按钮 + 自定义规则）

> **CLI 一条命令**（对齐 UI：BaseConfigDrawer 等四个视图抽屉里的 Zidingyianniu + ZdyanDrawer）：
> `scripts/list_view/desform_custom_button.py`。**四个视图类型（表格/看板/日历/甘特）的按钮规则完全相同，脚本不按视图类型分支**；唯一隐藏条件是 SQL 自适应（isSQLAdapt）数据源下 UI 不显示自定义动作。用法：
> - 查：`{"action":"list","worksheet":"xx"}`（可加 `viewId` 只看该视图已绑定的）
> - 建：`{"action":"create","label":"标记完成","clickThen":"form"|"execute"|"confirm","color":"rgb(...)"预设7色,"icon":"ant-design:xxx","showStatus":"always"|"condition","conditions":[...] 或 "conditionsGroup":[{"matchType":"and","queryItems":[{"field":"单选框组1","rule":"eq","val":"1"}]}],"flowStatus":bool}`。**名称自动查重**；**启用按钮=满足筛选条件**时支持「单条条件 conditions」和「筛选组 conditionsGroup」并存，组间关系 conditionType=and/or、组内 matchType=and/or，field 可写字段中文名自动转 model（**系统字段例外，须写 model+type**：创建时间/修改时间→`create_time`/`update_time`(datetime)、创建人/修改人→`create_by`/`update_by`(select-user)、流程状态→`bpm_status`(select)、所属部门→`sys_org_code`(select-depart)；写中文名会原样落库且 type 空）、rule 用代码（不能写 =）**且按字段类型校验可用集**（对齐 useFilterField.getConditionOptions：文本 like/eq/ne/right_like/left_like/like_with_and、数值/日期 eq/ne/gt/ge/lt/le/range、选项 radio/select/checkbox/用户/部门等 eq/ne/in/not_in、开关 eq/ne、富文本/附件/子表仅 empty/not_empty）；confirm 模式自动存默认确认文案（tip/ok/cancel 可覆盖）；execute/confirm 强制 flowStatus=true（返回 processId 用 jeecg-lowcode-miniflow 配流程）；form 默认不建流程。⚠️ `conditions`（旧单组格式）运行时优先判断，UI 打开旧按钮会自动升级为 `conditionsGroup` 单组；**新建推荐只写 conditionsGroup 包一层组**
> - 改：`{"action":"update","id":"...","label":"新名"}`（changes 任意 button 字段，含条件整组替换、confirmText、processId 换绑流程；改 label 同样查重）
> - **二次确认文案**（clickThen=confirm）：`"confirmText":{"tip":"提示文字","ok":"确认按钮文字","cancel":"取消按钮文字"}`（可只传要改的，其余保持默认文案）
> - **填写指定内容**（clickThen=form）：`"buttonFormConfig":{"formTable":"current"|"link-record","formType":"update"|"create","linkRecordField":"关联字段(中文名可)","createFormField":"...","createFormCode":"目标表编码(可自动推断)","updateFieldList":[{"key":"单选框组1","attr":"required"|"readonly"|"","defaultVal":"值"}]}`。formTable=current 改当前记录、link-record 改关联记录（须 linkRecordField，目标表编码可自动推断）；formType=update 填指定字段（updateFieldList 必填非空、key 支持中文名、attr 三档 必填/只读/填写）、create 新建关联记录（createFormField 必填）
> - 删（彻底，连带工作流）：`{"action":"delete","id":"..."}`；仅从当前视图移除：`{"action":"remove","id":"...","viewId":"..."}`；把已有按钮加入当前视图：`{"action":"bind","id":"...","viewId":"..."}`；排序：`{"action":"reorder","ids":[...]}`；单个详情：`{"action":"get","id":"..."}`。颜色预设/图标/showStatus/buttonFormConfig 结构规则见 `desform-custom-button.md`

> 当用户说"自定义按钮"、"添加按钮"、"视图按钮"、"自定义动作"、"zdyan"、"删除规则"、"控制删除"时触发本章节。

自定义动作包含两类：
- **自定义按钮**：通过独立的 `/desform/button/*` API 管理
- **自定义规则**：目前只有**删除规则**，通过 `PUT /desform/view/updateViewConfig` 的 `customRules` 字段配置，控制用户能否删除记录

> 详见 `references/desform-custom-button.md` — 删除规则完整结构与示例、自定义按钮数据结构、三种动作模式、显示条件、颜色预设、API 列表、Python 用法、工作流关联说明。

**操作流程（默认 CLI 一条命令，禁止为按钮操作手写临时 .py）：**

1. 查现状：`desform_custom_button.py --json '{"action":"list",...}'`（可加 `viewId`）
2. 展示变更摘要，等待用户确认
3. 建/改/删执行（JSON 写法见上方 CLI 块；ButtonInfo 字段结构、条件 rule 合法值、颜色/图标约定见 `references/desform-custom-button.md`，该文档是数据结构参考，不是执行入口）

**关于工作流（重要）：**

- `clickThen='form'` + `flowStatus=False`：**完全可以纯 API 完成**，无需工作流
- `clickThen='execute'` 或 `'confirm'`（必须触发工作流）：创建按钮后会得到 `processId`，工作流节点内容需同时使用 **`jeecg-lowcode-miniflow` 技能**配置

---

## 功能开关（零代码应用专属）

> **触发场景**：当用户在零代码应用（工作表）语境下，说到以下任意情况时，立即阅读 `references/desform-switch-setting.md`：
>
> - **控制某功能是否显示/可用**：「不让用户创建记录」「隐藏创建按钮」「禁用导入」「关掉批量操作」「关闭批量删除」「关闭分享」「禁止下载附件」「隐藏评论」「禁用打印」
> - **限制使用范围**：「只有管理员才能 XX」「XX 功能只在某个视图显示」「限制某功能的可见范围」
> - **直接说功能开关**：「功能开关」「开关设置」「switchSetting」
>
> **注意**：功能开关仅在**零代码应用的工作表**中存在，普通表单设计器没有此功能。函数位于 `desform_lowapp_utils`，需 `init_lowapp` 初始化（非 `init_api`）。

**操作流程：**

1. 阅读 `references/desform-switch-setting.md`，确认目标 code 和配置值
2. 调用 `get_switch_settings(code)` 查看当前状态（可选，直接构造也可）
3. 构造配置对象，注意父子联动规则（`BATCH_ACTION` 变更时需同时传所有子级）
4. 调用 `save_switch_settings(code, items)` 保存（函数导入方式见 `references/desform-lowapp-utils.md`，需 `init_lowapp` 初始化）

---

## 表单数据操作（CRUD）

对已有表单进行数据新增、查询、编辑、删除。

> 详见 `references/desform-data-utils.md` — 函数导入方式、完整函数列表和用法。

**数据新增流程：**
1. 先获取字段 model 映射：`get_form_fields(code)` 返回 `(titleField, {字段名: {model, key, type}, ...})`。主表用中文名；子表列用 `{子表名}.{列名}`，禁止按同名覆盖
2. 构造数据字典：key 为字段的 `model`（如 `input_1774607211242_327900`），value **必须按 `references/desform-data-utils.md`「控件落库格式」**。人员/部门/岗位/组织角色即使单选也存数组并写 `_dictText`；日期、省市、金额写 `_dictText`；关联记录写 `_dictTextPrint`
3. 调用 `add_data(code, data_dict)` 提交，用返回值的 `id`（由接口 `dataId` 规范化）

## 错误处理

> 详见 `references/desform-api-notes.md` — 完整错误处理表。

---

## OA 审批应用一键生成（表单 + 流程 + 授权）

> ⛔ 敲敲云工作表**没有 OA 字段分组**，不要生成 `oa-approval-comments` 等 OA 专用控件。普通请假/报销用常规字段 + 简流即可。

> 当用户说"创建审批单"、"创建报销单"、"做一个OA表单带流程"、"面试申请"、"请假申请"等，**立即阅读 `references/desform-oa-guide.md`**，其中包含完整的交互流程（Step 0–2）、JSON 配置格式、OA 专用字段类型、审批人类型、流程分支规则和常见模板。

---

## 一键生成积木报表（打印）

> 当用户说"给这个表单加积木报表打印"、"创建打印报表"、"desform 集成积木"、"一键生成打印模板"、"按字段生成打印报表"等，**立即阅读 `references/desform-jimureport.md`**，然后用 `scripts/desform_jimureport.py` 一键创建报表并关联到表单的 `allowJmReport` 打印。

脚本自动完成 5 步：创建空报表 → 保存 desform API 数据源 → 构造卡片打印模板（按 formStyle 适配 normal/word）→ 保存设计 → 回写表单 `allowJmReport`/`jmReportURL`。

**两个关键点（详见 reference）：**
- **积木报表 API base 常与 desform 不同**：desform 用 `--api-base`（如 `:3100/jeecgboot`），积木报表用 `--jmreport-base`（如 `:8080/jeecg-boot`）；同体部署时只传 `--api-base`。
- **字段绑定用 `${dbCode.model}`**：desform 数据 API 返回的 JSON key = 控件 model，绑定/`fieldName` 都必须用 model（不是 key），否则打印值全空。

> 简单的"按字段排版打印"用本脚本即可，**无需**加载 jimureport 技能。仅当用户要高度定制报表（分组/交叉/图表/套打背景图等）时，才提示用户加载 **jimureport** 技能，并以 `references/desform-jimureport.md` 的 desform 数据 API 规范作为数据集来源。

---

## 参考文档

### OA 审批应用

- `references/desform-oa-guide.md` — OA 一键生成完整指南：交互步骤、JSON 配置格式、OA 专用字段类型、审批人类型、流程分支规则、常见模板（费用报销/请假/采购/出差）

### 脚本工具

| 脚本 | 用途 |
|------|------|
| `scripts/desform_creator.py` | 通用表单创建脚本，优先使用 |
| `scripts/desform_view_creator.py` | 通用表单视图创建脚本（PC/移动端） |
| `scripts/desform_utils.py` | 共通工具库（控件工厂、API 封装、布局引擎、字段权限） |
| `scripts/desform_data_utils.py` | 数据操作工具库（CRUD、批量、回收站） |
| `scripts/desform_auth_retry.py` | 字段权限重试（仅权限自动创建失败时使用） |
| `scripts/desform_button_utils.py` | 自定义按钮操作工具库（增删改查、视图绑定、排序） |
| `scripts/desform_jimureport.py` | 一键创建积木报表并关联表单打印（含删除/清除关联） |
| `scripts/skill_temp_path.py` | 跨平台获取本技能临时目录/文件路径（写临时配置前必先调用，自动建目录） |
| `scripts/lowapp_creator.py` | 创建/复制/编辑/删除/查询低代码应用（`--json` 一条命令，不要改 desform_lowapp_utils.py） |
| `scripts/list_view/desform_list_view.py` | 列表视图查/改/建入口（表格类 action + 通用 action：list/get/delete/sort/config_table/config_sort/config_quick_filter/config_left_filter/config_data_filter/update 等；`--json` 一条命令。内部还有 columns/filter/quickfilter 模块，禁止当 CLI 跑） |
| `scripts/list_view/desform_custom_button.py` | 自定义按钮 CLI（list/get/create/update/delete/remove/bind/reorder；**四类视图同一套按钮体系，无需按视图分支**，见「自定义动作」章节） |
| `scripts/list_view/desform_list_view_special.py` | 视图专有 action 集中模块：看板 `add_board`/`config_board`（Kanbanshezhi）、日历 `add_calendar`/`config_calendar`（Rilishezhi）、甘特 `add_gantt`/`update_gantt`（GanttViewConfig）。由主脚本内部调用，禁止当 CLI 跑 |
| `scripts/create_linked_worksheets.py` | 租户+应用下并行建工作表 + 一对一关联记录。见 `references/fast-create.md`，禁止手写临时脚本 |
| `scripts/update_link_record.py` | 改已有关联记录（显示方式/记录范围/默认值/查询工作表）。见 `references/fast-link-record.md`，禁止手写 `filters`/`sqParam`/linkage 编码 |
| 列表视图函数（`desform_utils`，见 python-utils.md「列表视图/表格视图配置」） | 列表视图查/改/建（`add_list_view_*` / `config_table_*` / `query_list_views`）。⚠️ 无 `scripts/desform_list_view.py` CLI（2026-09-03 实测），禁止按该名调用 |
| `scripts/add_link_record.py` | 已有工作表**新增**关联记录字段（多条/单条 + 卡片/下拉/表格 + 中文筛选一次提交，内部解析 code/model/sqParam）。见 `references/fast-add-link-record.md`，禁止手写 `LINK_RECORD`/filters/sqParam 编码 |
| `scripts/batch_add_link_record.py` | **批量并行**新增关联记录字段（≥2 条用这条，job 为 `{tenantName, appName, links:[...]}`；逐条串行跑 add_link_record 每个子进程重复定位租户/应用，N 条 ≈ N×20s，并行墙钟接近单条）。条目格式同 `fast-add-link-record.md` |
| `scripts/desform_list_view.py` | 列表视图查/改/建（数据统计、行高、看板/日历/甘特；`--json` 一条命令，禁止现写临时 `.py`） |
| `scripts/sub_to_worksheet.py` | 设计子表转为独立工作表：`POST /desform/subToWorksheet` + `PUT /desform/edit`（主表换成工作表子表），一条命令 |
| `scripts/query_rule_map.py` | 组件→可用筛选规则码映射（复刻前端 QueryRuleMap.js）：写 summary 筛选/业务规则/条件组的 `rule` 前先查字段允许集合。CLI：`python scripts/query_rule_map.py <type> '<options-json>'` 或 `--demo` |

### 应用 / 工作表初始化（按文首路由，不要两份都读）

- `references/fast-full-chain.md` — **同一句要应用+表+简流+盘**：只读这一页
- `references/fast-create.md` — **租户+应用下建表 / 一对一**：只读这一页，跑 `create_linked_worksheets.py`
- `references/fast-link-record.md` — **改已有关联记录**：只读这一页，跑 `update_link_record.py`
- `references/fast-add-link-record.md` — **已有表新增关联记录字段**：只读这一页，跑 `add_link_record.py`
- `references/fast-link-record-linkage.md` — **关联记录默认值=查询工作表的真实落地格式**（2026-09-02 实测：脚本已内置字符对象 + 整单保存；本页记录根因与历史遗留字符串形态的兜底配方）
- `references/lowapp-init.md` — 手写临时脚本才读（加字段、改已有表）。建表+一对一不要读这份
- 应用增删改查不读上一份，只用上文「创建 / 复制 / 编辑 / 删除应用」+ `scripts/lowapp_creator.py`

### 创建/更新表单时阅读

- `references/desform-json-config.md` — JSON 配置格式、字段定义、子表说明、完整示例
- `references/desform-dict-config.md` — 字典数据源配置（静态选项、系统字典、Python 用法）
- `references/desform-python-utils.md` — desform_utils.py 使用指南、快捷函数、layout 参数
- `references/desform-api-notes.md` — API 踩坑记录、错误处理、命名规则
- `references/desform-menu-sql.md` — 菜单 SQL 生成、字段说明、本地自动执行

### 高级功能（按需阅读）

- `references/desform-link-record.md` — 涉及关联记录 + 他表字段时阅读。建表时「只能选… / 记录范围 / 设置筛选条件」和「查询设置 / 按名称搜 / 查询后再显示」都是控件 options，**先读「调用场景」再写入创建 JSON**，不要当列表筛选
- `references/desform-self-tree.md` — 涉及**表单数据树**（自关联树）时阅读：当用户说"自关联"、"数据树"、"自引用树"、"父子记录"、"关联自身"、"关联自己"、"上级记录"、"父节点字段"、"无限级分类"等，必须先阅读此文档再配置
- `references/desform-cross-form-binding.md` — 多表单互相关联时阅读（跨表 link-record/isSubTable/link-field/twoWayModel）
- `references/desform-sub-table-types.md` — 涉及子表时阅读（内部子表 vs 外部子表）
- `references/desform-new-sub-table.md` — 全新创建设计子表面板项、创建 JSON 透传、**转换工作表**（`subToWorksheet` 请求体 / 编码已存在 / 一键脚本）
- `references/desform-formula-function.md` — 涉及公式计算时阅读（内置函数库、自定义 JS 函数、日期计算）
- `references/desform-default-value.md` — 涉及默认值时阅读（compose/function/javascript/linkage 四种类型）
- `references/desform-context-vars.md` — 涉及上下文变量（{{sysUserCode}} 等）时阅读（完整变量列表、支持位置、JSON/Python 用法）
- `references/desform-fill-rule.md` — 涉及填值规则（fillRuleCode）时阅读（触发时机、完全只读、动态触发 JS 写法；**规则 Code 必须用户提供，禁止猜测**）
- `references/desform-validation-rules.md` — 涉及校验规则时阅读（rules/defaultRules/pattern/unique）
- `references/desform-option-datasource.md` — 涉及选项数据源时阅读（静态/系统字典/关联表单/远程函数）
- `references/desform-remote-api.md` — 涉及远程API取值（remoteAPI）时阅读（动态参数语法、${字段model}传参、返回值规则、触发时机）
- `references/desform-js-enhance.md` — 涉及 JS 增强时阅读（自定义 JavaScript、API 方法、事件监听、子表控件选项设置 `setSubTableOptions`）
- `references/desform-layout.md` — 涉及布局模式时阅读（auto/half/full/word 四种模式的说明和适用场景）
- `references/desform-css-enhance.md` — 涉及 CSS 增强时阅读（自定义样式、Word 风格定制）
- `references/desform-layout-controls.md` — 涉及复杂布局时阅读（AutoGrid/Card/Grid/Tabs）
- `references/desform-linkage-query.md` — 涉及查询工作表时阅读（linkage 类型默认值）
- `references/desform-online-binding.md` — 涉及关联 Online 表单时阅读（字段映射/子表/数据同步）
- `references/desform-external-link.md` — 涉及外链表单时阅读（公共填报、免登录访问、外链授权管理）
- `references/desform-filter-rules.md` — **【强制】构建列表数据过滤 / 高级查询 / 自定义按钮 `conditionsGroup` 等含小写 `rule` 的条件对象前必须阅读**。**不包括**关联记录 `options.filters`。**例外：关联记录「记录范围 / 筛选条件」不要读这份**，走 `references/fast-link-record.md` + `update_link_record.py`
- `references/desform-list-view.md` — 涉及列表视图时阅读（表格/看板/日历/甘特图类型说明、字段规则）
- `references/desform-api-docs/list-view.md` — 列表视图完整 API 文档（addView/updateViewConfig/排序/删除等所有接口）
- `references/desform-super-query.md` — 涉及列表页用户自定义筛选条件（高级查询）时阅读；触发关键词：「筛选条件」「高级查询」「superQuery」。用户在**关联记录控件**上说「筛选条件」→ `desform-link-record.md`；在**创建/配置视图**语境下说「筛选条件」「添加条件」→ 数据过滤（`config_view_data_filter`）
- `references/desform-custom-button.md` — 涉及自定义按钮/自定义动作时阅读（数据结构、三种动作模式、显示条件、API、Python 用法、工作流关联）
- `references/desform-view-config.md` — 涉及表单视图时阅读（JSON 配置、移动端优化、踩坑汇总）
- `references/desform-custom-receive-url.md` — 涉及自定义接收URL时阅读（接口规则、事务控制、子表数据处理、Java示例）
- `references/desform-biz-rules.md` — 涉及业务规则时阅读（`bizRuleConfig` 完整结构、条件操作符枚举、动作类型枚举、原始属性联动陷阱、与 filter-rules 的差异）；触发关键词：「业务规则」「联动」「满足条件时」「显示隐藏条件」「必填条件」「锁定记录」`bizRuleConfig`
- `references/desform-release-setting.md` — 涉及发布设置/外部链接时阅读（字段说明、URL格式、`externalTitle` 特殊值处理）；触发关键词：「发布设置」「外部链接」「公开链接」「二维码」「allowExternalLink」「页眉图片」「headerImgUrl」
- `references/desform-notice-setting.md` — 涉及填报通知时阅读（`noticeType` 枚举值、`noticeReceiver` 格式、校验规则）；触发关键词：「填报通知」「新增通知」「提交通知」「enableNotice」「noticeType」「通知接收人」
- `references/desform-print-setting.md` — 涉及打印设置时阅读（字段联动关系、积木报表集成）；触发关键词：「打印」「打印设置」「allowPrint」「积木报表」「jmReport」「disabledAutoGrid」
- `references/desform-jimureport.md` — **一键生成积木报表打印**时阅读（脚本用法、与 onlform 差异、双 API base、formStyle 适配、`${dbCode.model}` 绑定规则）；触发关键词：「给表单加积木报表」「创建打印报表」「一键生成打印模板」「desform 集成积木」
- `references/desform-switch-setting.md` — **零代码应用专属**，涉及功能开关时阅读（14个开关的完整配置、父子联动规则、viewAuth 约束、Python 示例）；触发关键词：「功能开关」「显示创建按钮」「禁用批量操作」「导入功能」「记录分享」「记录讨论」「附件下载」「记录日志」；函数导入方式见 `references/desform-lowapp-utils.md`

### 降级/排障

- `references/desform-fallback-manual-json.md` — 脚本失败时手动构造 JSON 的完整指南
- `references/desform-design-json-schema.md` — JSON Schema 结构、控件类型清单、通用字段
- `references/desform-widget-options.md` — 每种控件的完整 options 配置

### 示例参考

- `references/desform-examples.md` — 常见表单模式示例 + Python 脚本模板
- `references/desform-real-samples.md` — 真实业务表单案例（字典、半行、分区、公式、关联）

---

## 追加：会话内必须快（加字段 / 改已有表）

建表+一对一的开场禁令在**文首**，读到这里再「开始快」已经晚了。本节只约束加字段、改已有表、应用 CRUD。

接口本身一般 **5–30 秒**。超过 1 分钟几乎都是 AI 多余步骤。

**耗时预算（墙钟）：**
- 建 1~2 张工作表（含一对一）：只跑 `create_linked_worksheets.py`；整轮 **1 分钟内**
- 改已有关联记录（显示方式/筛选/默认值/查询工作表）：只跑 `update_link_record.py`；整轮 **2 分钟内**
- 已有表加字段：约 **5 秒**（一条 `add_widget`）
- 超过 2 分钟 = 开场读了 SKILL 全文 / `desform-link-record.md` / linkage-query / 手写 filters 编码

### 冷启动没有 ID

第一次只有「租户名 + 应用名 + 地址 + token」，**也能一次做完**。缺的是 ID，不是缺一轮问答。
- 禁止：先 `list` 租户/应用 → 等下一轮再创建
- 禁止：因没有数字 ID 就问用户要 ID
- 禁止：因「字段没列全」再问一轮。未指定字段用最少可工作字段直接建（标题编号 + 名称/金额/日期/状态），之后加字段走 `add_widget`
- 正确：Write `job.json` + `scripts/create_linked_worksheets.py`（见 `references/fast-create.md`）
- 用户给了 token 和要建什么 = 已授权。不要走上文「创建表单 §3 摘要确认」
- 当前消息没带地址/token：最多在 `prompt_history.jsonl` **搜一次**最近的 `jeecg-boot` + `eyJ`；没有就问一句。禁止翻整个 `.grok/sessions`，禁止为此打开 `jeecg-desform` / `jeecg-onlform`

名称匹配（用户常说「八匹狼租户」「关联记录应用」，系统里是「八匹狼」「关联记录」）：
1. `name` / `appName` **精确匹配**
2. 0 条时：去掉末尾「租户」「组织」「应用」再精确匹配一次
3. 仍 0 条或多条：停，打印现有名称，禁止猜

两张互不依赖的基础表由 `create_linked_worksheets.py` 内部并行创建。禁止再手写 for 循环串行 `desform_creator`，禁止先读 `desform-cross-form-binding.md`。

### 会话缓存（禁止重复取）

同一会话里已经确认过的值**从对话记录读取**，禁止再问、禁止再 list、禁止为取参再跑一遍定位脚本。

必须复用（本会话出现过就用，不要重新查）：

- `api-base` / `token`
- `tenant_id`、租户名称、`app_id`、应用名
- 工作表 `desformCode`、`form_id`、`menu_id`
- 视图 `view_id`（如甘特图1 → `2094970842048897026`）
- 字段中文名 → `model` / `key` / `type`（如「名称」→ `input_1788233827189_850656`）

每条 bash 是新进程，`init_lowapp(api_base, token, tenant_id, app_id)` **仍要写进该条命令**，但四个参数全部从会话填，不要先 `get_tenants()` / `get_apps()` / `get_menus()` / `query_list_views()`。

允许再查的仅这几种：用户换了应用或工作表；用户新加了字段且会话没有该字段的 model；上次报「未找到」/ KeyError；写 `ganttFields` / `showColumnList` 需要当前配置做 merge 时，**只** `query_list_view_by_id(已有 view_id)` 一次，不要先按名字搜视图。

不要每轮重读本 SKILL。会话已有 `view_id` + 租户 + 应用时（如「甘特图1 关闭未排期」、数据过滤），**零 Read、零 get_tenants、零 get_form_fields**，直接 `desform_list_view.py --json`。禁止为列表视图现写临时 `.py`。

### 读文档（禁止全量）

- `desform-widget-options.md`：**先** `grep -n "^## <type>"` 拿到行号，再 `Read offset=<行号> limit=50`。**禁止** `offset=1` 从头读（文件一千多行，读一次就耗掉一轮）。
- 用户只给「名称 + 控件类型」、不改多选/keyMaps/默认登录时：读完该片段立刻执行，不要再翻 `desform-python-utils.md` 全文。
- 工厂默认已覆盖的参数（`select-user`：`customReturnField=username`、`multiple=false`、`keyMaps=[]`、`defaultLogin=false`）不要再问用户。

### 往已有子表加列（强制，不要绕）

`get_form_fields(code)` **不返回** `sub-table-design` 容器，只把子表**列**展平进 map。结果是能看到「商品名称」「数量」，**看不到「订单明细」**。用 `fields['订单明细']` 会失败并浪费一次请求。

`add_widget()` 追加到**主表末尾**，不会进子表。子表加列禁止走 `add_widget`。

⛔ **`columns` 元素是单元格 `{"span":12,"list":[...]}`，`SUB_*` 返回裸控件**——只能 append 进单元格的 `list`（上例 `target['list'].append(widget)`）。禁止裸控件直接 append 到 `sub['columns']`：save 照常 success，后端把列清空、`queryById` 500 `columnList is null` 整表瘫痪（2026-09-16 实测）。保存后回查 `queryById success` + 列存在。

正确路径（**一条 Python 脚本一次跑完**，不要先失败再改）：

```python
from desform_lowapp_utils import init_lowapp
from desform_utils import query_form, SUB_USER, save_design_from_file, save_auth_from_design
import json, os, tempfile

init_lowapp(api_base, token, tenant_id=tenant_id, app_id=app_id)
design = json.loads(query_form(code)['desformDesignJson'])

def find_sub(node, name=None):
    if isinstance(node, dict):
        if node.get('type') == 'sub-table-design' and (name is None or node.get('name') == name):
            return node
        for v in node.values():
            r = find_sub(v, name)
            if r: return r
    elif isinstance(node, list):
        for i in node:
            r = find_sub(i, name)
            if r: return r
    return None

sub = find_sub(design, '订单明细')  # 用户指定了子表名就传名；只有一张子表可传 None
widget, key, model = SUB_USER('填写人员', sub['key'])  # 或其他 SUB_*
target = min(sub['columns'], key=lambda c: len(c.get('list') or []))
target.setdefault('list', []).append(widget)
hw = design.setdefault('config', {}).get('hasWidgets') or []
if widget['type'] not in hw:
    hw.append(widget['type']); design['config']['hasWidgets'] = hw
path = os.path.join(tempfile.gettempdir(), 'jeecg-desform', f'{code}_design.json')
os.makedirs(os.path.dirname(path), exist_ok=True)
json.dump(design, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
save_design_from_file(code, path)
save_auth_from_design(code)
```

Windows：**禁止** `python -c` 内联中文（编码必坏）。把上面写成 `{tmpdir}/jeecg-desform/*.py` 再执行。

### 用户已经点名时不要再确认

「在刚才创建的订单信息子表加上用户组件，名称填写人员」= 目标、位置、控件、名称都齐了。**不要**再出字段摘要等 y/n。本会话刚操作过的唯一应用，用户说删就按已知 id 删，不要再 list 一轮。

### 应用 CRUD 也要一条命令

创建 / 改名 / 删除：直接 `lowapp_creator.py`。有 `fromName` 或 `id` 时脚本内解析，禁止先单独 `action=list`。**禁止先读脚本源码再跑。** Windows 中文名称用 UTF-8 `--config` 文件（python 写 `json.dumps(..., ensure_ascii=False)`），不要 PowerShell `--json '{"appName":"中文"}'`（引号和编码都会坏）。列表视图同理：直接 `desform_list_view.py`，禁止现写脚本。

### 转换工作表（两步接口）

对应接口：`POST /desform/subToWorksheet`（建表+迁数据，**不改**主表设计）然后 `PUT /desform/edit`（主表字段换成 `link-record` + `isSubTable`）。没有只调一个就能改掉设计器的接口。一条命令 `scripts/sub_to_worksheet.py`。body / 判定见 `references/desform-new-sub-table.md`「转换工作表」。禁止猜键探测；禁止只 POST 完就报成功。

---

## 追加：全新创建的子表

用户说「全新创建的子表」「设计子表」「内部子表」，或贴子表右侧面板（布局列数 / 默认值 / 操作控制 / 数据绑定 Key / 隐藏 / 必填 / 字段说明）时，**先读** `references/desform-new-sub-table.md`，再创建或改配置。

`allowAdd`、`showCheckbox`、`showNumber`、`autoHeight`、`defaultValType`、`defaultValue` **支持**，写在 `sub-table-design` 的 JSON 上，创建脚本会写入 `options`。用户指定了就写进创建 JSON，不要再走一遍 `update_widget`。

**转换工作表**：用户说「转为工作表」「转换工作表」「把子表转成工作表」「subToWorksheet」时读同一文档的「转换工作表」节（**两步接口**：`POST /desform/subToWorksheet` + `PUT /desform/edit`），然后 **一条命令** `scripts/sub_to_worksheet.py`。不可逆；未点名禁止调用；点名了主表+子表就直接转，不要等 y/n。只调 POST、主表仍是设计子表 = 没转完。

禁止猜 `id`/`widgetKey`/`model` 去探测：后端不会按这些键反查，空 body 报 `designForm is null`，没 JSON body 报 `Required request body is missing`。报「编码已存在」先 `query_form` 主表——已是 `link-record`+`isSubTable` 就是转完了，不要再 POST。

---

## 追加：查租户 / get_form_id

**有租户 ID 直接用**（`--tenant-id` / `init_lowapp(tenant_id=tid)`），禁止再查租户列表。

**只有名称、没有 ID 时才先查再操作**，且必须和建表写在同一条脚本里（见上文「冷启动没有 ID」）。匹配规则与 `references/lowapp-init.md` 相同：先精确，0 条再去掉末尾「租户」「组织」「应用」。不要 `init_api` / `init_lowapp(tenant_id=0)` 之后再 `get_tenants()`：`desform_utils` 默认 `X-Tenant-Id=1`，会 401「登录租户授权变更」。应用 CRUD：`--tenant-id` 直接用，`--tenant-name` 才由脚本先查；工作表同理。

**`get_form_id(code)` 返回 `(form_id, update_count)` 或 `(None, None)`。** `(None, None)` 在 Python 里是真值。禁止 `if get_form_id(code):`。正确：

```python
fid, uc = get_form_id(code)
if fid:
    ...  # 已存在
```

建表不要自己再写一遍防覆盖：`desform_creator.py` 已经是 `existing_id, _ = get_form_id(form_code)`。

**`get_form_id` 很慢，禁止拿来探编码。** 实现是 `queryByCode` 后再 `/desform/list` 全量翻页校验幽灵记录，表一多一次 10s+。一对一建表实测：父进程对 4 个候选编码各探一次 + creator 里再各一次 + 结束再取 ID 两次 = **8 次全量 list**，脚本 138s（用户：还是太慢了）。

禁止：
- 创建前 `check_code_available` / `get_form_id` 试 `bpl_order`、`bpl_gljl_order` 等候选
- 创建后再 `get_form_id` 打印 ID（creator 已输出 `表单ID`）
- 为「是否已存在」先探再决定——编码一次定死交给 `desform_creator`；已存在它会 `[阻止]`，再换编码

关联不要第二次 `get_form_fields`：`LINK_RECORD` 返回的 `(ws, key, model)` 就是 `twoWayModel` 要用的值。两边 `add_widget` 并行，再两边 `update_widget` 并行。

---

## 追加：主表加字段只跑 add_widget

实测：给「采购单明细表」加「物料编码」，做成了预读本 SKILL + `get_form_fields` + `add_widget` + `save_auth_from_design` + 再 `get_form_fields`，脚本约 30s，用户感觉「加一个字段都这么慢」。30s 不是单次 `add_widget`，是多余文档和多余请求叠上去的。

**主表加字段**（用户点了工作表 + 字段名，如「采购单明细表 增加字段 物料编码」）：

1. 会话已有 `api-base` / `token` / 租户 / 应用 / 表 code → 直接用，禁止再 list、禁止再读本 SKILL。
2. **第一条 tool call** 就是一条 `.py`：`init_lowapp` + 工厂函数（`INPUT`/`DATE`/`INTEGER`/`MONEY`…）+ `add_widget(code, ws)`。`add_widget` 只传元组第一个元素（card 或控件 dict），不要传整个 `(ws, key, model)`。
3. 工厂默认已覆盖、用户没改 options 的 type（`input` / `textarea` / `integer` / `number` / `money` / `date` / `switch`）**零 Read** `widget-options`。用户指定了 radio/select/link-record 等才按索引只读该片段。
4. 禁止加之前 `get_form_fields` 探路；禁止加完再 `get_form_fields` 复查；禁止默认再调 `save_auth_from_design` / `sync_auth`（权限失败再补）。
5. 禁止出字段摘要等 y/n。
6. **子表加列**仍走上文「往已有子表加列」，不要用 `add_widget`，也不走本条。
7. 新字段是**关联记录**类型（用户带「关联记录 / 多条 / 单条 / 卡片 / 筛选」说）→ 不走本条，走 `fast-add-link-record.md` + `add_link_record.py`。

```python
from desform_lowapp_utils import init_lowapp
from desform_utils import INPUT, add_widget

init_lowapp(api_base, token, tenant_id=tenant_id, app_id=app_id)
ws, _k, _m = INPUT('物料编码')
r = add_widget(code, ws)
if not r or not r.get('success'):
    raise RuntimeError(r)
```

Windows：中文写进 `{tmpdir}/jeecg-desform/*.py` 再执行，禁止 `python -c` 内联中文。

---

## 追加：关联记录筛选条件

改**已有**关联记录的显示方式、记录范围、筛选条件、默认值（第一条数据 / 查询工作表）、仅可选择有查看权限：

1. **不要读** `desform-link-record.md` / `desform-linkage-query.md` / widget-options / filter-rules。
2. **只读** `references/fast-link-record.md`，Write job.json，跑 `scripts/update_link_record.py`。
3. 「开头是」写中文 `开头是` 或 `BEFORE`，不要写成小写 `right_like`（那是运行时 sqParam，当设计器 rule 会错）。`valueType` 用 `fixed`/`field`，禁止 `"value"`。
4. 会话已有租户/应用/表/字段时 JSON 写 ID，禁止再 list。追加条件用 `"appendFilters": true`。
5. **默认值=查询工作表（linkage）：脚本已修复（2026-09-02），自动写字符对象 + 整单设计保存，正常跑即可。** 若遇到历史遗留的字符串形态 value（接口 success 但设计器面板不显示）→ 必读 `references/fast-link-record-linkage.md` 按配方兜底。

新建表时把 `filters` 写进创建 JSON，仍走 `fast-create.md`。

---

## 追加：改控件类型 / 互换字段语义（防残留，2026-09-03 实测）

**现象：** 用 `update_widget` 把控件从一种 type 改成另一种（如 input→select 互换字段语义），`update_widget` 是**浅层键合并**——新 options 合并进去，但旧 type 的专属键**删不掉**。实测把「流程类型」从 input 改成 select 后，options 里残留 `showPassword`/`pattern`/`allowScan`/`readonly`/`required:true` 等 input 键，设计器面板里下拉框出现「显示为密码」「正则校验」等不该有的属性（用户必投诉）；反方向 select→input 同理残留 options 选项列表等。update_link_record.py 源码里 linkage 修复也印证了同一条：`update_widget` 深合并删不掉旧键，该场景走整单设计保存。

**正确姿势（两条）：**

1. **保留 key/model**：`update_widget` 改 type 时 key/model 不变（数据库列与对外引用稳定）。反之整体重建（新工厂生成）会换 key/model——若该 model 已被他表关联记录 filters / 数据 API 引用，**静默断链**，禁止。
2. **必须换控件语义且要清旧键 → 整单替换 options**：`query_form` → 解析 design → 找到目标控件 dict，**整体覆盖 `widget['options']`**（按 `desform-widget-options.md` 目标 type 的默认键集写全）→ `save_design_from_file(code, path)`（不要用 `update_widget`）。
3. 互换**两字段语义**（如「流程名称/流程类型搞反了」）：直接交换两个 widget dict 里除 name 外的 options，或各自整体替换 options + 交换 `name`；type/options 按目标形态重建，key/model 不动。

示例（清洗 2026-09-03 审批流程模板 ws_a2cf2f8180）已在会话验证：整体覆盖 input/select 两控件 options 后保存，残留归零、`required` 复位、关联筛选引用（目标表 model）不受影响。

**另一条相关实测（同日期）：** `LINK_RECORD(..., filters=...)` 曾经被 make_widget 白名单当未知参数**静默丢弃**（只打警告），加关联记录带筛选必须二次 `update_widget` 补。已修：`LINK_RECORD` 现显式支持 `filters=` / `search=` / `data_select_auth=`。若再遇到「警告: 收到非白名单参数」→ 立即停，改走显式参数或 `add_link_record.py`，不要无视警告继续。

## 追加：目标判定 + 控件常规属性 + 冷启动定位（2026-09-03 实测，防再犯）

**① 目标判定：文字 ≠ URL。** 用户话术「[xx租户] [yy应用] 下 [zz表单]」+ 面板属性词（隐藏标题/新增时隐藏/只读/禁用/校验必填）→ 目标是**敲敲云工作表**（本技能）；Online 表单没有租户/应用归属、也没有「新增时隐藏」。若同一请求里还贴了 jmreport `generateTemplateByOnline?onlineId=…` URL：该 onlineId 是 **Online cgform 表**的打印模板链接（只佐证那张 Online 表配过打印），URL 内 `token=` 是 jmreport 会话令牌，**不能**当 API 令牌（会 401）。按文字锁目标，禁止被 URL 带进 jeecg-onlform。

**② 控件常规属性修改（隐藏标题/只读/禁用/新增时隐藏/必填五件套）：**
- 键位：`hideTitle` 在控件**顶层**；`required`/`readonly`/`disabled`/`hidden`/`hiddenOnAdd`/`fieldNote`/`autoWidth` 全在 **options** 内。
- 改法：`update_widget(code, {"hideTitle": True, "options": {"required": True, "readonly": True, "disabled": True, "hiddenOnAdd": True}}, key=<控件key>)`。
- options 子层属性不套 `{"options":{}}` 包装 → 后端**静默成功但无效**；改完必须 `query_form` 回查目标键=true 再报成功（已在 ws_3a1720f142 的日期/时间控件验证）。

**③ 冷启动定位（租户/应用/表 code 都没有时）——禁止猜返回结构：**
- `get_apps()` 返回 **`{"apps":[…]}`**（不是 list），应用字段 `id`/`appName`；
- `get_menus(app_id)` 返回 **`{"menuList":[…]}`**，工作表菜单 `type=="form"`，取 `desformCode`/`menuName`；
- 递归按名匹配（精确 → 去掉「租户/应用/表单」后缀），匹配不到打印现有名单，禁止用「看起来对」的 id：

```python
def find(node, key, val, out, d=0):   # 按 键==key 且 值含val 收集所在 dict
    if d > 8:
        return
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key and isinstance(v, str) and val in v:
                out.append(node)
            find(v, key, val, out, d + 1)
    elif isinstance(node, list):
        for i in node:
            find(i, key, val, out, d + 1)
```


---

## 追加：视图数据过滤 / 类型切换 / 自定义按钮实测（2026-09-03）

**config_data_filter 根层禁止裸条件**：conditions 数组里与筛选组平级的单条条件，界面上不显示，且落库时会被吞掉（实测「数字1」条件落库后变成空组、条件丢失）。所有条件一律包进筛选组，单条条件也包 `{"match_type":"and"/"or","items":[...]}`。

**字段中文名带编号**：如 数字1 / 单选框组1 / 下拉选择框1 / 开关1，用户口述常省略编号。CLI 报「数据过滤未找到字段: xxx」时先 `get_form_fields(code)` 取实际名称重写，不要连续盲试。

**视图「图标类型」由配置推导，不是存 type 字段**：列表接口报的 type 与存储 type 可不同（实测：全部=card、看板01=base、甘特图01=base、日历01=calendar）。甘特图01 显示为甘特是因为 `ganttFields.beginDateField/endDateField` 非空；**甘特图 → 看板** = `update_list_view(view_id, ganttFields={...全部置null}, calendarColumnList=[], groupField=<分组字段model>, filterGroupType='all', titleField=<标题字段key>)`，保留 groupField 即按该字段分列，其余字段不动；转完 get 复核结构是否与既有看板视图一致（如 groupField/filterGroupType/titleField/ganttFields 形态）。

**desform_custom_button.py create/update 必须带 `code` 或 `worksheet`**：缺了报「JSON 必须提供 code 或 worksheet」。同名按钮创建直接报「按钮名称已存在」→ 应改走 `list` 查该按钮现有配置，需要修正时用 `update`，不要重复 create。`updateFieldList` 的 `key` 支持字段中文名，脚本自动转 key/model/type。

---

## 追加：数据过滤条件值实测（2026-09-10）

**条件值形态**：选项/人员/部门/角色/地区/关联/多选类 **单值=纯字符串、多值=逗号串，禁数组（编辑器不回显）**；日期=格式化字符串、`range`=逗号串。逐类表见 `desform-filter-rules.md`「条件值形态实测」；**条件值 ≠ 数据落库格式**（数据侧存数组+`_dictText`）。

**CLI 缺口 → 直连提交**：`desform_list_view.py` 的 `config_data_filter` 不解析系统列（`创建人/修改人/创建时间/修改时间` 四种写法均报「未找到字段」）、日期会转毫秒（冲突）、选项类不转换。含系统字段或要字符串日期时：`PUT /desform/view/updateViewConfig`，体 `{"id":viewId,"conditionType":"and","conditions":[{"matchType":"and","queryItems":[…],"showPop":false}]}`，item=`{"name","field","type","rule","val"}`（系统时间项 `type:"datetime"`+`"timestamp":true`）；提交后 `query_list_view_by_id` 回读复核。

---

## 追加：控件行宽度（半行/整行）实测（2026-09-03）

**失败基线：** 改「手机_1」整行连续失败两次——只调 `update_widget` 写 `options.autoWidth=100` / `options.width='100%'`，接口 success、读 JSON 也确实写进去了，但用户在设计器里再保存一次就全被重置回 `autoWidth=50, width=''`。前端保存会按自己的模型重建 options，API 塞进去的宽度键不认。

**真相（对照设计 JSON 实测）：** 敲敲云工作表「整行/半行」不在控件 options 里，而在 `desformDesignJson.list[]` 顶层的 **card 行容器**：`type:'card'` + `isAutoGrid:true` 的节点 = 一行，装 1~N 个控件。控件自己的 `options.autoWidth` 是行内宽度百分比档位。

**两套规则（2026-09-09 用户明确）：**
- **整体（表单级）列数设置：仅 1~4 列**（autoWidth=20 等勿配）；
- **单个控件行宽档位**：1/4=25、1/3=33.333、1/2=50、**2/3=66.667、3/4=75**、整行=100。

与 `options.width`（`'100%'`）是配套属性：**整行控件 = 独占一个 card 且 autoWidth 100 + width '100%'**（对照同表 定位_1/手写签名_1/文本识别_1 都是单卡 + 100）；工厂默认 text 类（input/phone/email/number 等）= autoWidth 50 + width ''，input 例外 width '100%'+autoWidth 50；imgupload 默认单卡但 autoWidth 50。

**可靠改法（一条 python 整单改，禁止用 `update_widget` 单改宽度）：**
1. `query_form(code)` 拿 `desformDesignJson`（`get_form_fields` 只有字段映射，**拿不到 card 行结构**，要行布局必须整单 query）；
2. 改目标控件 `options`：`autoWidth=100` 且 `width='100%'`；
3. 把控件挪进**自己独占的 card**：原 card 只留另一半控件（或删）。新 card 照抄现有单控件 card 结构：`{"options":{}, "isContainer":true, "model":"card_"+ms, "type":"card", "isAutoGrid":true, "list":[控件], "key":ms+'_1'}`，`ms=int(time.time()*1000)`，model 与 key 都必须是新值；
4. 写临时文件 + `save_design_from_file(code, path)` 整单保存；
5. 再 `query_form` 复核：该控件所在 card 只剩它自己、options 里两个宽度键都在。

若用户已手工在界面改过：先 query 读当前真实结构再动，不要拿旧认知覆盖。改完提示用户硬刷新设计器。

---

## 追加：汇总字段「汇总列」必须指向**当前**子表列（2026-09-16 实测）

整单保存会让**设计子表的列重新生成内部 id**（`date_…` / `select_…` / `number_…`）。汇总控件的 `options.field` 存的是列的 model：
整单替换/重建子表列之后若没同步重映射，`field` 会指向**已废弃的旧列 id** —— 接口 `success`、回读该字段也有值，
但**设计器右侧面板的「汇总」下拉会显示成一串 `number_1789545054262_70` 而不是「调休天数」**，用户一眼就能看到。

- 判定：`options.field`（≠ `inner-record-count` 时）必须能在**本表当前子表列的 model 集**里命中。
- 修法：`query_form` 取整单 → 把该汇总控件的 `options.field` 改成当前列 model → `save_design_from_file` → 回读命中。
- **引用自查要覆盖"不带 `$` 包裹的裸 model 取值"**：`options.field`、`showField`、`linkTable`、`linkRecordKey`、
  业务规则 `rules[].model`/`actions[].value`。常规的「`$…$` 引用扫描」扫不到它们，本条就是这么漏检过去的
  （当年只扫了 `$…$`，STRICT 全绿，只有人打开设计器才暴露）。

## 追加：auto-number 规则段补全（2026-09-03）

`update_widget` 写 `numberRules` 返回 success ≠ 设计器规则面板生效：**段对象缺 UI 辅助键时面板读不到段内容**（text 段缺 `value`、create_date 段缺 `format`/`formatCustom` 时表现为「设置没生效」，但 JSON 已落库）。改自动编号规则时：先 query 找 UI 手工配置的参照控件（如「自动编号-01」）抄完整键集合；`AUTONUMBER(prefix=...)` 工厂已补全（text 段 value+text、create_date 段 format+dateFormat+formatCustom）。完整结构见 widget-options.md 勘误第 8 条。

## 追加：控件默认值 — 空的「高级默认值」会覆盖普通默认值（2026-09-03 实测）

**现象：** `update_widget` 给 date/time 控件写 `options.defaultValue='18:52:52'`，接口 success、回查 options.defaultValue 也在，但新增页默认值不显示；同表单用户手动拖出的新控件默认值正常。

**根因：** 脚本工厂/早前 API 改过的控件顶层残留 `advancedSetting.defaultValue={type:'compose', value:'', …}`（**空值**高级默认值）。运行时只要存在 `advancedSetting.defaultValue` 就以它为准——空值 = 无默认，把 `options.defaultValue` 覆盖掉。设计器手动添加的控件没有这个残留，所以正常。

**修法（与设计器形态对齐）：** 整单流程 `query_form` → 目标控件若 `advancedSetting.defaultValue.value` 为空 → `del widget['advancedSetting']` → `save_design_from_file`（**不要用 `update_widget`，浅合并删不掉顶层键**）。默认值保留在 `options.defaultValue`（date/time 字符串；checkbox/select-user 等数组或 `#F:` 特殊格式先 query_form 确认形态）。

**注意区分：** 若 `advancedSetting.defaultValue.value` **非空**（如 '202609031853'），说明默认值被存进了高级默认值，它会正常生效，**不要删**。

**验证仪式：** 回查控件「无 advancedSetting 且 options.defaultValue 非空」→ 让用户刷新**新增页**看默认值带出（不是设计器画布）。

**switch 补充（2026-09-03 用户纠正）：开关默认值按字面存储值写，禁止转布尔。** 例：开启的值=0、关闭的值=1、默认值=0 → `options.defaultValue = "0"`（不是 `true`）。widget-options 表里 defaultValue 标 boolean 是引擎口径，不代表用户面板口径——**用户给什么字面值就写什么**（与 activeValue/inactiveValue 同型字符串）。开启值=0 且默认值=0 → 初始为「开」、存储 0，语义正确。

## 追加：select/radio/checkbox 绑定应用级字典 —「保存时提交 remote:'dict'」决定面板态（2026-09-08 源码+实测定论，修正 09-03「UI 独写」误判）

**判据（源码 2026-09-08 核对）：** 属性面板（WidgetConfig → DictDefValConfig：数据来源下拉 `v-model=options.remote`，`isDictMode = remote==='dict'`）、设计画布（WidgetFormItem：`remote==='dict'` 才按 dictCode 拉字典）、运行态（GenerateFormItemMixins.loadRemoteDict）**全部只认 `options.remote === 'dict'` 为「数据字典」**，静态数据 = remote false。

**实测闭环（2026-09-08，同表 6 个字典字段 A~F 逐键对照 + 界面确认）：**
1. 只写 `dictCode/dictCodeAppId/isDictItem:true` + 快照而 options.remote 为 false 提交 → 落库后设计器面板数据来源 = **静态数据**（09-03 的「UI 独写」误判根因：面板绑定态根本没生成，不是 UI 专属）；
2. **整单保存时把字典控件 options.remote 显式置 `'dict'` 提交** → 落库 remote 仍被后端归一化为 false（isDictItem:true、快照保留，「保存即快照化」），但**面板绑定态已记录**，刷新设计器后数据来源显示「数据字典」✓；
3. 字段级 `update_widget` 提交 remote:'dict' **不生成**绑定态（实测仍静态）；**必须整单保存**（save_design_from_file / 建表整单通道）；
4. 绑定态**以最近一次整单保存提交为准、逐字段独立**：整单里漏带 dict（remote false）的字典字段，其既有绑定态会被冲掉回「静态数据」——含字典字段的表，**每次整单保存都要把所有字典控件 options.remote 保持 `'dict'`**（2026-09-08：中途一次只带部分字段 dict 的整单保存，导致其余字典字段面板回退静态）。

**API 正确姿势（一次到位，勿再让用户 UI 点选）：**
- 建表 job / 整单补丁中字典字段 options 写全：`remote:"dict"` + `dictCode` + `dictCodeAppId`（=目标字典所属应用ID）+ `isDictItem:true` + `options` 字典项快照（`{"value","label","itemColor"}` 抄字典当前项）+ `showLabel:true`/`useColor:true` + `props:{"label":"label","value":"value"}`；
- advancedSetting 保留空 compose 壳（radio/checkbox/select 常态：`type:compose,value:"",format:string,allowFunc:true,valueSplit:",",customConfig:true`）；
- 然后**整单保存**。回查 remote 被归一化为 false ≠ 失败；判定 = 用户在 UI 刷新设计器后数据来源显示「数据字典」。
- ⚠️ UI 整单重写会把 radio/checkbox/select 固定默认值迁移到 `advancedSetting.defaultValue.value` 的 `#F:值#` 静态段形态（多值按 valueSplit 拼接，如 `#F:0##F:1#`），options.defaultValue 被清空——这是 UI 原生形态；默认值丢 = 属性面板重设数据源/默认值编辑器重置所致，不是整单重写。**但 API 回写固定默认值时不要照抄该形态**（2026-09-16 用户 UI 实证）：下拉/单选的默认值是在属性面板**选项下直接选**的，正确落法 = 只写 `options.defaultValue`=选项文案字符串 + **删掉整个 `advancedSetting`**；写 `advancedSetting.defaultValue.value="#F:值#"`（或纯文本）都会让画布/新增页把 `#F:值#` 当字面量显示。动态字段引用默认值（`$model$` compose）不受影响。

**禁止：** ①只写 dictCode 不写 remote dict 提交后抱怨面板静态；②用 `update_widget` 单独补 remote:'dict'；③让用户逐个 UI 点选（已证实 API 整单可一次到位）；④写顶层 `dictOptions`（保存会清，面板识别不需要）。

**前置检查（沿用）：** 绑定/引用字典前先 `lowapp_dict.py --action query` 现查目标应用字典存在性与 dictCode、字典项（曾被删除后指向死 code，静默失效）；快照 value/label 必须抄字典当前项，不要凭猜测（2026-09-08 实测：UI 手工把快照 label 改成「男1/女1」后新增页按静态快照显示「男1/女1」，与字典「男/女」不一致）。

**补（2026-09-16）：** ①需求写「字典「X」」=数据字典；写"静态"才静态。②导出 JSON 改完回存前，先扫全表 `dictCode`+`isDictItem` 控件把 `options.remote` 置 `'dict'`——导出态 remote 恒为 false，回存即冲掉绑定态（含 tabs `panes[].list`）。

## 追加：creator 白名单忽略 + 外部子表 + 汇总绑定落库（2026-09-04 实测）

**创建 JSON 白名单外参数 = ⚠ 警告即忽略（未生效）**，三类已实测，需创建后 export→改 `options`→save 补：
- `select-user`/`select-depart` 的 `defaultLogin`（默认当前登录人/其部门）→ 补 `advancedSetting.defaultValue.value="#D:CURRENT#"`（设计器保存形态；旧补法 `options.defaultLogin:true` 运行时兼容但面板不回显，2026-09-08 源码/UI 核对）
- date 默认当天：**禁止补 `options.defaultValueType:3`**（2026-09-08 纠正：面板不回显）→ 整单补高级默认值 `advancedSetting.defaultValue`：① compose `$_CONTEXT_VAR_sysDate$` ② function `DATENOW()`，`defaultValueType` 保持 `1`（详见 `desform-default-value.md`「date — 默认值类型」）
- `link-record` 的 `showType` → 单卡场景默认已正确可忽略；要其他形态事后改 options

**「子表作为单独工作表 / 已有工作表作为子表」= 明细控件 link-record + `isSubTable:true` + `model:"sub_table_design_<key>"`（model 后缀=key）+ showType=table**。创建脚本 link 产普通 many 关联，要此外观需转换；结构与同步点见 `references/desform-link-record.md`「二-a」。转换后 3 处同步：① 子表回指字段 `options.twoWayModel` ② 主表汇总 `options.linkTable` ③ 改 model 后 `save_auth_from_design(主表code)` 重刷字段权限。

**汇总字段落库（UI 绑定 vs 脚本不一致）：** 用户在界面重绑汇总后 `linkTable` 存明细控件 **key**（无 `sub_table_design_` 前缀，脚本/整单写入的是 model 全名）；勾「必填」落库 = `options.required:true` + 顶层 `rules:[{"required":true,"message":"${title}必须填写"}]` 双写。用户 UI 绑过的控件以界面保存形态为准，禁止回改。

**手工向主表 design 追加整行字段：** 包 isAutoGrid card（`{"options":{},"isContainer":true,"type":"card","isAutoGrid":true,"model":"card_<ts>_<rnd>","key":"<ts>_<rnd>","list":[widget]}`）追加到 `design["list"]`（汇总类放明细区控件之后）。汇总控件绑工作表子表时 `linkTable` 写明细控件 **key（无前缀）**，勿写 `sub_table_design_` model（面板按 key 匹配，写 model 不回显，见 `references/desform-widget-options.md` 汇总节）。

**⛔ 强制前置检查（2026-09-03 用户要求，防再犯）：凡绑定/引用应用级字典（select/radio/checkbox 数据源、字段默认值引用等），无论会话/记忆里有没有记过 dictCode，第一步必须先 `lowapp_dict.py --action query` 查**目标应用当前**字典列表，确认 dictName/dictCode/字典项真实存在且未变**再动手**。字典可能已被用户删除或重建（实测：指向已删字典的绑定静默失效，不报错），禁止直接复用历史 dictCode。

## 追加：自己关联自己 = 自关联树，isSelf 只此一处（2026-09-04 实测）

用户说「在 X 表加关联记录，自己关联自己」= **自关联树（表单数据树）**，不是普通跨表关联。结构见 `desform-self-tree.md`。

- **判定**：关联目标表 == 所在表自身。正确形态 = link-record，sourceCode=本表 code + **控件顶层 `isSelf:true`**（valueSplit 置空）；UI 对应「查询工作表选当前工作表自己」。卡片展示父记录、可点击展开/添加**下级**；下拉/卡片只是选择形态，不影响自关联身份。
- **错误做法（踩过）**：按普通关联记录建同表引用——sourceCode 虽指向自身但**缺 isSelf**，系统不认自关联，没有下级/子树；用户纠正后才补上。
- **新建路径**：建表 job 不带 link，表建成后跑 `add_link_record.py`，target 写同表即自动 isSelf（脚本 `tg_code==master_code` 才为 True；**只有自己关联自己有 isSelf，跨表关联一律不加**，禁止手补）。
- **已有字段缺 isSelf**：整单 `query_form` → 该控件顶层补 `isSelf:true` + `advancedSetting.defaultValue.valueSplit=''` → `save_design_from_file`（顶层键 update_widget 删不掉，必须整单），或让用户在 UI 重设一次（系统自动打标）。