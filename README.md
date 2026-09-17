# 敲敲云 Skills — AI 驱动 · 一句话搭建应用

> 在 **Claude Code** 中，用一句话搭建 **敲敲云 APaaS** 业务应用：**应用 · 工作表 · 简流 · 仪表盘** 一次到位。
> 零代码、自然语言驱动 —— 依托敲敲云表单引擎、流程引擎、仪表盘引擎，AI 自动生成全套配置。

<p>
  <a href="https://www.qiaoqiaoyun.com/skills"><img src="https://img.shields.io/badge/Skills专题页-qiaoqiaoyun.com%2Fskills-1677ff?style=flat-square"></a>
  <a href="https://gitee.com/jeecg/qqyun-skills"><img src="https://img.shields.io/badge/Gitee-jeecg%2Fqqyun--skills-C71D23?style=flat-square&logo=gitee"></a>
  <a href="https://github.com/jeecgboot/qqyun-skills"><img src="https://img.shields.io/badge/GitHub-jeecgboot%2Fqqyun--skills-181717?style=flat-square&logo=github"></a>
  <img src="https://img.shields.io/badge/License-Apache%202.0-52c41a?style=flat-square">
</p>

|            |                                          |
| ---------- | ---------------------------------------- |
| **3**      | 敲敲云官方 Skills 全量上架               |
| **1 句话** | 应用 + 工作表 + 简流 + 仪表盘 全链路     |
| **100%**   | 开源 · Apache 2.0                        |

---

## 🚀 一键安装

### 第 1 步 · 一行命令装齐环境（推荐 · 无需翻墙）

国内镜像加速，一行命令装齐 **Node.js · Python · Git · Claude Code**，并写入 **DeepSeek** 作为模型后端，**装完即可使用**。

**Windows（PowerShell）**

```powershell
irm https://www.qiaoqiaoyun.com/claude/boot.ps1 | iex
```

> 若提示脚本被禁，先运行：`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**macOS / Linux（Bash / Zsh）**

```bash
curl -fsSL https://www.qiaoqiaoyun.com/claude/install-claude-code.sh | bash
```

- **幂等运行**，重复执行只补缺；重装 / 换 Key 使用 `--force`
- 写入 `ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN / ANTHROPIC_MODEL=deepseek-v4-pro`
- Windows 装完请**新开一个 PowerShell 窗口**让环境变量生效；Linux / macOS 执行 `source ~/.bashrc`

> ⚠️ DeepSeek 按 token 计费，需自备 API Key：[DeepSeek 开放平台 申请 API Key](https://platform.deepseek.com/api_keys)

### 第 2 步 · 安装敲敲云 Skills

**macOS / Linux**

```bash
git clone https://gitee.com/jeecg/qqyun-skills.git
cp -r qqyun-skills/jeecg-lowcode-* ~/.claude/skills/
```

**Windows（PowerShell）**

```powershell
git clone https://gitee.com/jeecg/qqyun-skills.git
Copy-Item qqyun-skills\jeecg-lowcode-* $env:USERPROFILE\.claude\skills\ -Recurse -Force
```

> - **国内推荐 Gitee**（访问快）；海外可用 GitHub：`git clone https://github.com/jeecgboot/qqyun-skills.git`
> - 第 1 步脚本会顺带安装姊妹项目 [JeecgBoot Skills](https://gitee.com/jeecg/skills)（开发侧：代码生成 / Online 表单 / BPMN / 报表大屏），与敲敲云 Skills 同目录**共存、互不影响**
> - 若 `~/.claude/skills` 尚未被占用，也可整库克隆：`git clone https://gitee.com/jeecg/qqyun-skills.git ~/.claude/skills`

### 已有 Claude Code？

跳过第 1 步，直接执行第 2 步；并确保 **Python 3.12+** 可用（`python --version`，Skills 通过 Python 脚本调用敲敲云 API）。

**安装完成**

```bash
claude
> 帮我搭一个请假管理应用：表单 + 审批流程 + 统计看板
```

---

## 📦 Skills 列表

| #   | 技能                        | 一句话能力                                                                                      | 触发关键词                                     | 产出物                    |
| --- | --------------------------- | ----------------------------------------------------------------------------------------------- | ---------------------------------------------- | ------------------------- |
| 1   | **jeecg-lowcode-lowapp**    | 一句话创建 / 管理敲敲云低代码应用及应用内工作表，40+ 控件、主子表、一对一、关联记录、视图、按钮  | 创建应用、建工作表、一对一、关联记录、加字段   | 应用 + 工作表（表单）配置 |
| 2   | **jeecg-lowcode-miniflow**  | 一句话生成简流：工作表事件 / 定时 / 按日期字段触发，审批、填写、回写、子流程、消息通知           | 创建简流、审批流程、定时提醒、工作表触发流程   | 简流配置（processJson）   |
| 3   | **jeecg-lowcode-dashboard** | 一句话创建应用内仪表盘 / 看板 / 门户：24 列栅格，图表、筛选、按钮、聚合表、环比同比              | 创建仪表盘、数据看板、统计图表、查询面板       | 仪表盘页面配置            |

> **全链路**：同一句话同时要「应用 + 工作表 + 简流 + 仪表盘」时，三个 Skill 自动协同，一次交付完整应用。

---

## 💬 使用示例

所有技能都在 Claude Code 对话中**通过自然语言触发**，无需手动调用。

```
🧑 用户提问
在「行政管理」应用里做一个请假管理：
请假表单（申请人、请假类型、起止日期、天数、事由、附件），
提交后走直属上级审批，审批通过状态改为"已通过"，
再来一个请假统计看板：按类型分布饼图 + 按月趋势折线图。

🤖 AI 回复
✅ 已完成「请假管理」全套搭建：

工作表  请假申请
  申请人（用户选择）/ 请假类型（单选）/ 起止日期 / 天数 / 事由 / 附件

简流  请假审批
  新增记录触发 → 直属上级审批 → 通过后回写状态为"已通过"

仪表盘  请假统计
  请假类型分布（饼图）+ 月度请假趋势（折线图）+ 查询面板
```

**通用交互流程**

```
1. 用自然语言描述需求（点名租户 / 应用 / 工作表效果最佳）
2. AI 询问敲敲云后端地址和 Token（如需调用 API）
3. AI 展示配置摘要，等待确认
4. 确认后自动执行，返回结果
5. 可在同一会话中继续修改（加字段、改流程、换图表）
```

**X-Access-Token 获取方式**

1. 打开敲敲云系统并登录
2. 按 F12 打开浏览器开发者工具，切换到 **Network** 标签
3. 点击任意请求，在 **Request Headers** 中找到 `X-Access-Token`
4. 复制完整的 Token 值粘贴给 AI

---

## ✍️ 提示词写法

两种写法**等价、二选一即可**，不必叠写；把【租户】【应用】换成实际名称。

| 写法 | 示例开头 |
| --- | --- |
| **A · 命令触发** | `使用 /jeecg-lowcode-lowapp 在租户【租户名】的应用【应用名】下，……` |
| **B · 点名敲敲云** | `在敲敲云租户【租户名】的应用【应用名】下，……` |

三个技能各有对应命令：`/jeecg-lowcode-lowapp` · `/jeecg-lowcode-miniflow` · `/jeecg-lowcode-dashboard`；
说「在敲敲云」「创建工作表」「建审批流程」等自然语言，也会自动路由到对应 Skill。

**写法要点**

- 必须写 **租户 + 应用** 两级上下文；应用不存在时直接说「创建一个应用【xxx】」，一句话连应用一起建
- 字段用「**中文名 + 控件类型 + 关键属性**」描述（如：请假天数（整数，必填）），不要写 JSON
- 能默认的就写上：当前登录人 / 当前部门 / 当天日期
- 审批人给**真实姓名 / 角色名 / 部门名**；「分支」点名类型（互斥 / 包含 / 并行）
- 同一句要「应用 + 工作表 + 简流 + 仪表盘」时，以 lowapp 开场即可，三个 Skill 自动协同

---

## 📚 实战提示词库（复制即用）

> 更多示例（含 **30 张工作表 + 12 条简流 + 2 个仪表盘的人事OA整套系统完整提示词**）见官网专题页：**[qiaoqiaoyun.com/skills](https://www.qiaoqiaoyun.com/skills)**

<details>
<summary><b>单表 · 请假申请（最短一句话）</b></summary>

```text
在敲敲云租户【北京敲敲云科技有限公司】的应用【OA办公】下建工作表「请假申请」：
姓名（选择用户，必填，标题）、部门（选择部门，默认当前用户所属部门）、请假类型（下拉单选：事假/病假/年假/调休）、开始日期、结束日期、请假天数（整数，必填）、请假原因（多行文本）、附件（附件上传）。
```

</details>

<details>
<summary><b>主子表 · 采购申请（应用 + 两张表 + 公式汇总）</b></summary>

```text
在敲敲云租户【北京敲敲云科技有限公司】下创建应用【采购协同】，两张工作表一对一：
「采购申请」：申请编号（自动编号，前缀 PR+日期+4 位流水，只读）、申请标题（必填）、申请日期（默认当天）、申请人（成员，默认当前用户）、申请金额（汇总明细.金额 求和）。
「申请明细」：物料名称、数量（整数，必填，默认 1）、单价（金额）、金额（公式：数量×单价）、所属申请（回指采购申请）。
采购申请里把申请明细作为子表（表格、双向）。
```

</details>

<details>
<summary><b>简流 · 报销多级审批（金额分支）</b></summary>

```text
在敲敲云租户【北京敲敲云科技有限公司】的应用【费用管理】下，给「报销单」建审批流程：新增记录触发，金额小于等于 5000 走部门主管一级审批；金额大于 5000 先部门主管、再总经理二级审批。全部通过后状态改为「已通过」，驳回则改为「已驳回」，结果通知报销人。
```

</details>

<details>
<summary><b>简流 · 定时扫描超时提醒</b></summary>

```text
在敲敲云租户【北京敲敲云科技有限公司】的应用【客服工单】下，建定时流程：每天 9 点扫描「工单」，处理状态等于 待处理 且 创建时间超过 24 小时的改为 已超时，逐条站内通知负责人；没有超时记录时不通知。
```

</details>

---

## 🔍 技能详情

### 1. jeecg-lowcode-lowapp — 敲敲云应用与工作表

**一句话**：自然语言创建和管理敲敲云低代码应用及应用内工作表（表单设计器）。

- 应用全生命周期：创建 / 复制 / 改名 / 删除 / 列出，应用分组管理
- 工作表三种模式：单表、主子表（明细子表）、一对一
- 40+ 控件：文本、数字金额、单选多选、日期时间、上传、省市区、定位、自动编号、用户 / 部门 / 岗位选择等
- 关联体系：关联记录（卡片 / 下拉）、他表字段、汇总、跨表绑定、关联筛选
- 表单增强：公式计算、填充规则、校验规则、默认值、JS / CSS 增强
- 视图与数据：列表视图（列配置、筛选、自定义按钮）、Excel 导入导出、打印、外链
- 一键创建 OA 审批应用（表单 + 流程 + 授权）

**使用文档**：[skill-usage-guide.md](jeecg-lowcode-lowapp/docs/skill-usage-guide.md)

### 2. jeecg-lowcode-miniflow — 简流设计器

**一句话**：自然语言生成简流（工作表驱动的轻量流程），经 API 创建 / 修改 / 发布。

- 触发方式：工作表事件（新增 / 更新 / 删除）、定时（每分钟 ~ 每年、自定义周期）、按日期字段逐条触发
- 丰富节点：审批（会签 / 或签）、填写、更新 / 新增记录、获取数据、消息通知（站内 / 邮件）、公告、运算
- 分支与子流程：互斥 / 包含 / 并行分支，callActivity 子流程（含主子流程数据传递）
- 定时场景一条命令直跑：定时壳、一次性公告、扫描 + 批量更新 / 新增 + 逐行通知、有 / 无记录分支
- 增量修改：在已有流程加 / 改 / 删节点，改触发条件与筛选规则

### 3. jeecg-lowcode-dashboard — 应用内仪表盘

**一句话**：自然语言创建敲敲云应用内仪表盘 / 看板 / 门户，图表 + 筛选 + 按钮一次配齐。

- 24 列栅格布局、卡片式设计，归属租户 + 应用
- 丰富图表：柱状 / 折线 / 饼图、雷达、双轴组合、地图、透视表、数字卡片、排行榜等
- 图上精修：换维度 / 数值、计算值、配色、数据标签、TopN、排序、环比 / 同比
- 交互组件：查询面板、按钮（打开页面 / 触发业务流程）、轮播、iframe、时钟、富文本
- 聚合表与聚合工厂，支撑跨表统计
- 口语直建：说「各产品销售额饼图」即可建图，字段智能匹配；≥5 张盘支持声明式批量构建

---

## 🧩 适用版本与相关链接

- **敲敲云 APaaS**（[qiaoqiaoyun.com](https://www.qiaoqiaoyun.com) 在线版）或基于 JeecgBoot 低代码引擎的私有化环境
- **Skills 官网专题页** · [qiaoqiaoyun.com/skills](https://www.qiaoqiaoyun.com/skills)（安装演示 · 提示词库 · 使用示例）
- **本仓库** · [Gitee（国内推荐）](https://gitee.com/jeecg/qqyun-skills) · [GitHub](https://github.com/jeecgboot/qqyun-skills)
- **Claude Code** 最新版本 · **Python 3.12+**
- **姊妹项目** · [JeecgBoot Skills](https://gitee.com/jeecg/skills)（开发侧：代码生成 / Online 表单 / BPMN / 积木报表 / 大屏）

---

<p align="center">
  <sub>敲敲云 APaaS 零代码平台 · Skills 加持 —— 告别拖拉拽，一句话搭建业务应用</sub>
</p>
