# 仓储 5 表单库存仪表盘（金标实例，按需）

> **实例字面量，不是通则。** 仅当需求与此金标同类（多表单 + KPI×4 + 柱/饼/折/透视 + 按钮 + 跨表过滤）时复用。字段/图名勿当通用默认。租户/应用/表单码 = 本文件字面量（§1–§4）；凭证另见 memory `reference_jeecgboot_credentials.md`（铁律 #1）。通则 → `create.md`；**跨域通用占位符编排 → `multiform-template.md`**。
> 2026-09-07 全套实测通过，wall ≈8m（其中 ~4m 为可省轮数）；按本文件重放目标 ≤2–3m。

## 0. 一次性预置

- 凭证 → 首条 Bash 前 Read 一次 memory `reference_jeecgboot_credentials.md` 取 API/TOKEN（铁律 #1，会话内复用）；租户/应用/表单码 = 本文件字面量（新疆兵团 TID=1008，APP_ID=2095784150765826050，formCode 见 §2/§4）
- 建盘决策默认值（同组已有盘=新建「X看板」；对比口径=单据数；明细无日期按日=create_time）→ `multiform-template.md` §1（本金标与模板同步维护）
- 编排通则 → `multiform-template.md`；组件词表 → `component-words.md`

## 1. 发现捆绑（单条 Bash，~8s）

```bash
QQY="py $SKILL_REFS/scripts/qqy_ops.py"; API=...; TOKEN=...
$QQY tenants "$API" "$TOKEN" --name 新疆兵团 && \
$QQY menus "$API" "$TOKEN" --tenant-id 1008 --app-name 仓储系统管理 && \
$QQY forms  "$API" "$TOKEN" --tenant-id 1008 --app-name 仓储系统管理
# fields 仅在点名字段疑似不存在时追加
```

## 2. specs（并行 Write 至 $HOME/.claude/tmp-qqy/；字面量可照抄本单）

布局：y0 KPI×4(w6)；y17 柱×2；y49 饼+柱；y81 折+饼；y113 透视整行。

```json
# a_ck.json → ws_ab7352cfbb 仓库档案
[{"comp":"JNumber","title":"仓库总数","x":0,"y":0,"w":6,"h":17,"dim":[],"val":"record_count"}]
# b_wl.json → ws_18f7bd57d5 物料档案
[{"comp":"JNumber","title":"物料SKU数","x":6,"y":0,"w":6,"h":17,"dim":[],"val":"record_count"}]
# c_kc.json → ws_65609158de 实时库存
[{"comp":"JNumber","title":"实时库存总量","x":12,"y":0,"w":6,"h":17,"dim":[],"val":"库存数量"},
 {"comp":"JBar","title":"各仓库库存","x":0,"y":17,"w":12,"h":32,"dim":"关联仓库","val":"库存数量"},
 {"comp":"JBar","title":"物料库存排行","x":12,"y":17,"w":12,"h":32,"dim":"关联物料","val":"库存数量","sorts":{"name":"库存数量","type":"desc"}},
 {"comp":"JPie","title":"库存按仓库分布","x":0,"y":49,"w":12,"h":32,"dim":"关联仓库","val":"库存数量","percentLabel":true},
 {"comp":"JPivotTable","title":"仓库×物料库存","x":0,"y":113,"w":24,"h":34,"dim":"关联仓库","val":"库存数量"}]
# d_rk.json → ws_8c84e36570 入库单
[{"comp":"JNumber","title":"本月入库单数","x":18,"y":0,"w":6,"h":17,"dim":[],"val":"record_count","queryRange":"month"},
 {"comp":"JBar","title":"本月各仓库入库对比","x":12,"y":49,"w":12,"h":32,"dim":"关联仓库","val":"record_count","queryRange":"month"},
 {"comp":"JPie","title":"入库单状态","x":12,"y":81,"w":12,"h":32,"dim":"审批状态","val":"record_count"}]
# e_mx.json → ws_c615616613 入库明细（无日期字段→create_time 按日）
[{"comp":"JLine","title":"本月每日入库量","x":0,"y":81,"w":12,"h":32,"dim":"create_time","val":"入库数量","dateGroup":"3","queryRange":"month"}]
```

注：透视列维度（typeFields）CLI 侧未确认支持，`grp` 不展开——两维矩阵需前端把列维度拖入，勿中途探究。

## 3. 按钮 + 过滤 specs（并行 Write）

```json
# buttons.json
{"rowNum":3,"btnType":"graphical","btnStyle":"solid","btnWidth":"divide","place":"bottom",
 "buttons":[{"title":"新建入库单","op":"创建记录","form":"入库单"},
            {"title":"打开实时库存","op":"打开列表视图","form":"实时库存"},
            {"title":"打开入库单列表","op":"打开列表视图","form":"入库单"}]}
# filter1_kc.json（实时库存表）
{"title":"仓库名·库存","place":"above","charts":["实时库存总量","各仓库库存","物料库存排行","库存按仓库分布","表格"],
 "conditions":[{"field":"关联仓库","mode":"包含"}]}
# filter2_rk.json（入库单表）
{"title":"仓库名·入库单","place":"above","charts":["本月入库单数","本月各仓库入库对比","入库单状态"],
 "conditions":[{"field":"关联仓库","mode":"包含"}]}
```

## 4. 主链单条 Bash（合规同壳串行，~40s；失败按 step 标记只重跑失败段）

```bash
set -e
S=$HOME/.claude/tmp-qqy
$QQY create-page "$API" "$TOKEN" --tenant-id 1008 --app-id 2095784150765826050 --name 库存管理看板 --group 库存管理 && echo STEP1_OK && \
$QQY add-charts  "$API" "$TOKEN" --tenant-id 1008 --app-name 仓储系统管理 --page-name 库存管理看板 --form-code ws_ab7352cfbb  --specs-file $S/a_ck.json && echo STEP2_OK && \
$QQY add-charts  "$API" "$TOKEN" --tenant-id 1008 --app-name 仓储系统管理 --page-name 库存管理看板 --form-code ws_18f7bd57d5 --specs-file $S/b_wl.json && echo STEP3_OK && \
$QQY add-charts  "$API" "$TOKEN" --tenant-id 1008 --app-name 仓储系统管理 --page-name 库存管理看板 --form-code ws_65609158de --specs-file $S/c_kc.json && echo STEP4_OK && \
$QQY add-charts  "$API" "$TOKEN" --tenant-id 1008 --app-name 仓储系统管理 --page-name 库存管理看板 --form-code ws_8c84e36570 --specs-file $S/d_rk.json && echo STEP5_OK && \
$QQY add-charts  "$API" "$TOKEN" --tenant-id 1008 --app-name 仓储系统管理 --page-name 库存管理看板 --form-code ws_c615616613 --specs-file $S/e_mx.json && echo STEP6_OK && \
$QQY add-buttons "$API" "$TOKEN" --tenant-id 1008 --app-name 仓储系统管理 --page-name 库存管理看板 --specs-file $S/buttons.json && echo STEP7_OK && \
$QQY add-filter "$API" "$TOKEN" --tenant-id 1008 --app-name 仓储系统管理 --page-name 库存管理看板 --specs-file $S/filter1_kc.json && echo STEP8_OK && \
$QQY add-filter "$API" "$TOKEN" --tenant-id 1008 --app-name 仓储系统管理 --page-name 库存管理看板 --specs-file $S/filter2_rk.json
# 末尾 rm -f $S/*.json
```
