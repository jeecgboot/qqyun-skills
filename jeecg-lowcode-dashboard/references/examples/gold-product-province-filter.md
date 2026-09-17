# 产品名称 + 省份名称跨表查询过滤金标（按需）

> **实例字面量，不是通则。** 仅当盘结构与本金标同类时打开。  
> **通则**（任意跨表）：`create.md` — 每表一次同表 `add-filter`；透视匹配词=`表格`。本文件只提供 charts 清单与改名步骤，**勿把字段/图名当通用默认**。

## 字段（口称 ≠ 表字段）

| 条件显示名 | 表字段 `field` | 表 |
|------------|----------------|-----|
| 产品名称 | `名称` | 产品表 |
| 省份名称 | `省份` | 省份销售记录 |

## 产品 `charts`（9，非地图）

`总销售额,销售额构成,销量当前百分比,销售额完成比例,产品指标对比雷达图,产品售价与销量分布,本月总销量,产品售价-销量气泡图,表格`

- 透视匹配必须用 **「表格」**（`option.title` 常空；长 `componentName` 会 `CHART_NOT_FOUND`）
- **勿进：** `客户跟进漏斗`、`销售阶段金额金字塔`（他表）

## 省份 `charts`（4，地图）

`各省销售额分布,中国省份销售额气泡地图,省份销售额柱状地图,各省销售额热力分布`

## 子串冲突

同页若有「总销售额」与「总销售额比例」→ 先把后者 `componentName` 改为 **「销售额完成比例」**，再跑产品过滤（否则 `CHART_AMBIGUOUS`）。

## 一次进程顺序

1. 缺 TID 才 `tenants`
2. 必要改名「销售额完成比例」
3. `add-filter` ×2（产品 / 省份）
4. 省份 select「包含」强制 `rule=LIKE` / `condition=2` / `chartData.queryMode=2`
5. 顶置：`comp_ops list` 一次现取全组件坐标 → 两面板 `comp_ops move --x 0 --y 0/10`（JFilterQuery 高 10），面板原占位之上的组件 +20、之下 +10 级联顺移（细则 → `mutate.md`「顶置 / 插入级联」）。**y=14/24 只属本例原盘布局，勿跨盘照抄**
6. `ADDED=` 停

## 增量场景：盘上已有一面板（2026-09-08 实测）

- `comp_ops list` 一次盘点：缺哪张面板、图名与上文金标清单对得上即照抄、坐标现取（add-filter 自带逐图 `CHART_MATCH=` 校验，错名/他表当场报错，图名无需预查）
- 缺产品面板 → Write FILTER.json（title `产品名称查询`、charts=上文产品 9 项 + `表格`）→ `add-filter --specs-file`（回执 `ADDED=…conditions=1 charts=9`）
- 已有省份面板补匹配 → `edit-filter --name 省份名称查询 --field 省份 --mode 包含`（回执 `CHANGES=mode=2/LIKE;mode=2/LIKE;queryMode=2` 即 LIKE 生效）
- 顶置 + 级联位移命令见上文步骤 5

## 已有面板改匹配 / 默认值

勿重建 → `create.md` `edit-filter`。面板名常见 `产品名称查询` / `省份名称查询`。  
pageId 轮换 → `--page-name`（见 `SKILL.md` §3）。历史案例 → `../lessons.md`。
