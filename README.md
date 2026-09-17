# 敲敲云 Skills — AI 驱动 · 一句话搭建应用

> 在 **Claude Code** 中，用一句话搭建 **敲敲云 APaaS** 业务应用：**应用 · 工作表 · 简流 · 仪表盘** 一次到位。
> 零代码、自然语言驱动 —— 依托敲敲云表单引擎、流程引擎、仪表盘引擎，AI 自动生成全套配置。

<p>
  <a href="https://www.qiaoqiaoyun.com"><img src="https://img.shields.io/badge/敲敲云官网-qiaoqiaoyun.com-1677ff?style=flat-square"></a>
  <a href="https://github.com/jeecgboot/qqyun-skills"><img src="https://img.shields.io/badge/GitHub-jeecgboot%2Fqqyun--skills-181717?style=flat-square&logo=github"></a>
  <img src="https://img.shields.io/badge/License-Apache%202.0-52c41a?style=flat-square">
</p>

|          |                                        |
| -------- | -------------------------------------- |
| **3**    | 敲敲云官方 Skills 全量上架             |
| **1 句话** | 应用 + 工作表 + 简流 + 仪表盘 全链路 |
| **100%** | 开源 · Apache 2.0                      |

---

## 🚀 安装

### 前置要求

- **Claude Code** 最新版本：[code.claude.com/docs/zh-CN/quickstart](https://code.claude.com/docs/zh-CN/quickstart)
- **Python 3.12+**（Skills 通过 Python 脚本调用敲敲云 API），终端可运行 `python --version`

### 方案 A · 全新安装（`~/.claude/skills` 尚未使用）

```bash
git clone https://github.com/jeecgboot/qqyun-skills.git ~/.claude/skills
```

已存在则增量更新：

```bash
cd ~/.claude/skills && git pull
```

### 方案 B · 与 JeecgBoot Skills 共存（局部复制）

若 `~/.claude/skills` 已被 [jeecgboot/skills](https://github.com/jeecgboot/skills) 等仓库占用，克隆本仓库后只复制三个 Skill 目录：

```bash
git clone https://github.com/jeecgboot/qqyun-skills.git
cd qqyun-skills

# macOS / Linux
cp -r jeecg-lowcode-lowapp jeecg-lowcode-miniflow jeecg-lowcode-dashboard ~/.claude/skills/

# Windows（PowerShell）
xcopy jeecg-lowcode-lowapp    %USERPROFILE%\.claude\skills\jeecg-lowcode-lowapp\    /E /I
xcopy jeecg-lowcode-miniflow  %USERPROFILE%\.claude\skills\jeecg-lowcode-miniflow\  /E /I
xcopy jeecg-lowcode-dashboard %USERPROFILE%\.claude\skills\jeecg-lowcode-dashboard\ /E /I
```

> 使用时在对话中提供敲敲云后端地址与 `X-Access-Token` 即可（获取方式见下文），无需修改 Skill 文件。

**安装完成**

```bash
claude
> 帮我搭一个请假管理应用：表单 + 审批流程 + 统计看板
```

---

## 📦 Skills 列表

| #   | 技能                       | 一句话能力                                                                                     | 触发关键词                                             | 产出物                    |
| --- | -------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------ | ------------------------- |
| 1   | **jeecg-lowcode-lowapp**   | 一句话创建 / 管理敲敲云低代码应用及应用内工作表，40+ 控件、主子表、一对一、关联记录、视图、按钮 | 创建应用、建工作表、一对一、关联记录、加字段           | 应用 + 工作表（表单）配置 |
| 2   | **jeecg-lowcode-miniflow** | 一句话生成简流：工作表事件 / 定时 / 按日期字段触发，审批、填写、回写、子流程、消息通知          | 创建简流、审批流程、定时提醒、工作表触发流程           | 简流配置（processJson）   |
| 3   | **jeecg-lowcode-dashboard**| 一句话创建应用内仪表盘 / 看板 / 门户：24 列栅格，图表、筛选、按钮、聚合表、环比同比             | 创建仪表盘、数据看板、统计图表、查询面板               | 仪表盘页面配置            |

> **全链路**：同一句话同时要「应用 + 工作表 + 简流 + 仪表盘」时，三个 Skill 自动协同，一次交付完整应用。

---

## 💬 使用示例

所有技能都在 Claude Code 对话中**通过自然语言触发**，无需手动调用。

<details open>
<summary><b>示例 · 一句话搭建完整应用（全链路）</b></summary>

```
🧑 用户提问
在「行政管理」应用里做一个请假管理：
请假表单（申请人、请假类型、起止日期、天数、事由、附件），
提交后走直属上级审批，审批通过状态改为"已通过"，
再来一个请假统计看板：按类型分布饼图 + 按月趋势折线图。

🤖 AI 回复
✅ 已完成「请假管理」全套搭建：

工作表  请假申请
  申请人（用户选择）/ 请假类型（单选：事假·病假·年假·调休）
  开始日期 / 结束日期 / 请假天数 / 请假原因 / 附件

简流  请假审批
  新增记录触发 → 直属上级审批 → 通过后回写状态为"已通过"

仪表盘  请假统计
  请假类型分布（饼图）+ 月度请假趋势（折线图）+ 查询面板
```

</details>

<details>
<summary><b>示例 · 单独建工作表（jeecg-lowcode-lowapp）</b></summary>

```
🧑 用户提问
创建一个采购申请单：
主表：采购标题(必填)、采购部门、采购日期、总金额
子表明细：物品名称、规格型号、数量、单价、小计

🤖 AI 回复
✅ 已创建「采购申请」工作表（主子表），明细子表含 5 个字段，
小计支持公式计算，总金额可配置汇总。
```

</details>

<details>
<summary><b>示例 · 定时流程（jeecg-lowcode-miniflow）</b></summary>

```
🧑 用户提问
每天下午三点扫描预约表，把超过 24 小时未确认的预约标记为"已超时"，
并给对应医生发站内提醒。

🤖 AI 回复
✅ 已创建定时简流「预约超时提醒」：
定时触发（每天 15:00）→ 扫描预约表（确认时间早于 24 小时前且状态=待确认）
→ 批量更新状态为"已超时" → 逐条发送站内通知。
```

</details>

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

## 🔍 技能详情

### 1. jeecg-lowcode-lowapp — 敲敲云应用与工作表

**一句话**：用自然语言创建和管理敲敲云低代码应用及应用内工作表（表单设计器）。

**核心能力**：

- 应用全生命周期：创建 / 复制 / 改名 / 删除 / 列出应用，应用分组管理
- 工作表三种模式：单表、主子表（明细子表）、一对一，支持树形结构
- 40+ 控件类型：文本、数字、金额、单选 / 多选、日期时间、开关、评分、滑块、上传、省市区、定位、自动编号、用户 / 部门 / 岗位选择等
- 关联体系：关联记录（单条 / 多条、卡片 / 下拉）、他表字段、汇总、跨表绑定、关联筛选
- 表单增强：公式计算、填充规则、校验规则、默认值、JS / CSS 增强、选项数据源
- 视图与按钮：列表视图（列配置、筛选、快速筛选）、自定义按钮、PC / 移动端视图
- 数据管理：记录 CRUD、Excel 导入导出、打印设置、外链分享
- 一键创建 OA 审批应用（表单 + 流程 + 授权）

### 2. jeecg-lowcode-miniflow — 简流设计器

**一句话**：用自然语言生成简流（工作表驱动的轻量流程），经 API 创建 / 修改 / 发布。

**核心能力**：

- 触发方式：工作表事件触发（新增 / 更新 / 删除）、定时触发（每分钟 ~ 每年、自定义周期）、按日期字段触发（每条记录到期各触发一次）
- 丰富节点：审批（会签 / 或签）、填写、更新记录、新增 / 删除数据、获取单条 / 多条数据、消息通知（站内 / 邮件）、公告、运算节点
- 分支与子流程：互斥 / 包含 / 并行三种分支，callActivity 子流程（含主子流程数据传递）
- 定时场景一条命令直跑：定时壳、一次性公告、扫描 + 批量更新 / 新增 + 逐行通知、有 / 无记录分支
- 增量修改：在已有流程加 / 改 / 删节点，改触发条件与筛选规则
- 完整业务模板：资产领用 / 归还 / 调拨等「主表 + 明细 + 台账」改造示例可直接复用

> 注意：简流是敲敲云应用内的轻量流程；系统级 BPMN 工作流请使用 [jeecgboot/skills](https://github.com/jeecgboot/skills) 中的 `jeecg-bpmn`。

### 3. jeecg-lowcode-dashboard — 应用内仪表盘

**一句话**：用自然语言创建敲敲云应用内仪表盘 / 看板 / 门户，图表 + 筛选 + 按钮一次配齐。

**核心能力**：

- 24 列栅格布局、卡片式设计，应用内盘（归属租户 + 应用）
- 丰富图表：柱状图、折线图、饼图、雷达图、组合图（双轴）、地图、透视表、数字卡片、排行榜、滚动表格等
- 图上精修：换维度 / 数值、计算值、配色、数据标签、TopN、排序、环比 / 同比对比
- 交互组件：查询面板（筛选条件）、按钮（打开页面 / 触发业务流程）、轮播、iframe、时钟、富文本
- 聚合表与聚合工厂，支撑跨表统计
- 口语直建：描述「各产品销售额饼图」这类原句即可建图，字段智能匹配
- 批量建盘：≥5 张盘走声明式 `build_dashboards.py`，一条命令建完、支持断点续跑

> 注意：本技能处理**有应用归属**的应用内仪表盘；无应用归属的积木仪表盘 / 大屏 / 门户请使用 [jeecgboot/skills](https://github.com/jeecgboot/skills)。

---

## 🧩 适用版本

- **敲敲云 APaaS**（[qiaoqiaoyun.com](https://www.qiaoqiaoyun.com) 在线版）或基于 JeecgBoot 低代码引擎的私有化环境
- **Claude Code** 最新版本
- **Python 3.12+**

---

## 🔗 相关链接

- **敲敲云官网**：<https://www.qiaoqiaoyun.com>
- **GitHub 仓库**：<https://github.com/jeecgboot/qqyun-skills>
- **姊妹项目 · JeecgBoot Skills**（开发侧：代码生成 / Online 表单 / BPMN / 积木报表 / 大屏）：<https://github.com/jeecgboot/skills>
- **Claude Code 下载**：<https://code.claude.com/docs/zh-CN/quickstart>

---

<p align="center">
  <sub>敲敲云 APaaS 零代码平台 · Skills 加持 —— 告别拖拉拽，一句话搭建业务应用</sub>
</p>
