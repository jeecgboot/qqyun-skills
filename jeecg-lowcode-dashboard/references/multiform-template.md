# 多表单仪表盘通用执行模板（占位符版 · 零字面量）

> **跨域通用编排模板**：任何租户/应用的 ≥2 表单复合盘（KPI×N + 图表 ± 按钮 ± 过滤）按本文件执行。
> 字面量实例（同仓储结构照抄改名即跑）→ `examples/gold-warehouse-5table-dashboard.md`。
> JSON 骨架与规则权威 → `create.md` / `gold-specs.md`；CLI 实参速查 → `create.md`「空白盘」（create-page 例外）。实例同构字面量 → `examples/gold-warehouse-5table-dashboard.md`——**本模板与金标实例必须同步维护**（规则/骨架变更时同改两处）。
> **目标墙钟 ≤2–3m**（主链一条 ≈40–60s）：全部内容以 `<占位>` 形式出现，禁止把任何占位固化成默认值（金标才允许字面量）。

## 0. 适用判定（先用后判，勿滥用）

| 场景 | 走哪条路 |
|------|----------|
| ≥2 表单 + 图/按钮/过滤混排（本模板） | create-page → 按 formCode 串行 add-charts → add-buttons → 每表一次 add-filter |
| 仅 1 表单 | `create-dashboard --layout-file` 一条（create.md 复合盘） |
| 同应用仿上一张盘 | 先查 examples/ 金标字面量替换，比本模板更快 |
| 只往已有盘加图/按钮/过滤 | create.md「按钮/查询面板」段（add-charts → add-filter） |

## 1. 输入采集与默认决策（不提问）

用户一句给全：`<租户名> <应用名> <分组> <盘名>` + 每表单出什么图/数 + 按钮动作 + 过滤需求。缺失时用默认（即「默认决策四件套」，勿为以下情形提问）：

1. 盘名 = `<分组>看板`；分组内已有盘 → 默认**新建**独立盘（用户点名旧盘/旧内容才并入）
2. 「对比/排行」类跨表口径 → 取同表单步可得口径（如**单据数**），不跨两级关联
3. 明细表无日期字段 → 按日统计回退 `create_time` + dateGroup=3；「本月/本周」锚表单自己的 date 字段
4. 提问仅限「猜错代价大」的真歧义，且最多 1 问

- 过滤跨表 → 每表单一次 add-filter，**面板标题带表名**防重名
- 视觉细节 CLI 不支持（如透视列维度 typeFields）→ 交付时点一句，禁止中途探究

## 2. 发现捆绑（单条 Bash，产出 TID/APP_ID/formCode/分组/已有盘）

```bash
QQY="py $SKILL_REFS/scripts/qqy_ops.py"
$QQY tenants "$API" "$TOKEN" --name <租户名> && \
$QQY menus  "$API" "$TOKEN" --tenant-id <TID> --app-name <应用名> && \
$QQY forms  "$API" "$TOKEN" --tenant-id <TID> --app-name <应用名>
# fields 仅当点名字段疑似不存在时追加（点名维值=跳过）
```

规格/命令一律用 **formCode**（`--form-code <码>` 防子串冲突）；dim/val 写**字段中文名**（引擎自动展开关联记录维度；禁写 `link_record_*`）。

## 3. 布局预设（坐标换算通用规则）

- KPI 行：3 个 → 各 `w:8, y:0, h:17`；4 个 → 各 `w:6`；有环比/同比 h≥30
- 图表行：半行 `w:12, h:28–34`（柱/折/饼 30–32）；透视/大表 整行 `w:24, h:30–34`；地图 `w:12, h:35`（禁 w:24）
- 同行 w 合计 = 24；`config.size` = w×75 / h×11（脚本算，勿手写像素）
- specs 每条必带 x/y/w/h；省略 y 仅用于已有盘底部追加

## 4. specs 写法（跨域通用，非占位部分）

- `comp` 口语或码均可（JNumber/JBar/JPie/JLine/JPivotTable…，脚本归一）
- KPI：计数 `"val":"record_count"`；求和/均值写数值字段中文名（默认求和；**禁写 calc 占位符**）
- 时间：`queryRange` 口语（本月…）或码（month）；`dateGroup` `"3"`=按日（仅日期维生效）
- 样式首轮写全：饼 `percentLabel:true`；排行 `sorts:{"name":"<数值中文名>","type":"desc"}`（+`dataFilterNum` N）；保持默认浅蓝勿写 colors
- 失败重试：**只重跑失败 step**，禁止整链重放（重复加图）

## 5. 执行（主链单条 Bash · 同壳串行 = 合规）

并行 Write 全部 JSON（`$HOME/.claude/tmp-qqy/`）后一条跑完，~40–60s：

```bash
set -e; D=$HOME/.claude/tmp-qqy
$QQY create-page "$API" "$TOKEN" --tenant-id <TID> --app-id <APP_ID> --name <盘名> --group <分组> && echo S1_OK && \
$QQY add-charts "$API" "$TOKEN" --tenant-id <TID> --app-name <应用名> --page-name <盘名> --form-code <码A> --specs-file $D/a.json && echo S2_OK && \
$QQY add-charts "$API" "$TOKEN" --tenant-id <TID> --app-name <应用名> --page-name <盘名> --form-code <码B> --specs-file $D/b.json && echo S3_OK && \
… &&
$QQY add-buttons "$API" "$TOKEN" --tenant-id <TID> --app-name <应用名> --page-name <盘名> --specs-file $D/buttons.json && echo Sn_OK && \
$QQY add-filter "$API" "$TOKEN" --tenant-id <TID> --app-name <应用名> --page-name <盘名> --specs-file $D/filter_A.json && echo Sn1_OK && \
$QQY add-filter "$API" "$TOKEN" --tenant-id <TID> --app-name <应用名> --page-name <盘名> --specs-file $D/filter_B.json
# 收尾 rm -f $D/*.json；打印 PAGE_ID/SHARE_URL 即停
```

## 6. 按钮 / 过滤骨架（字面量替换处）

```json
# buttons.json
{"rowNum":<每行个数>,"btnType":"graphical","btnStyle":"solid","btnWidth":"divide","place":"bottom",
 "buttons":[{"title":"<文案1>","op":"创建记录","form":"<表单名>"},
            {"title":"<文案2>","op":"打开列表视图","form":"<表单名>"},
            {"title":"<文案3>","op":"打开页面","customPage":{…}}]}
# op 别名：创建记录+form / 打开列表视图+form / 打开页面+pageId / 打开链接+url / 调用业务流程+flowId
# filter_<表>.json —— 每表单一份、charts 须同一表单
{"title":"<条件名·表名>","place":"above",
 "charts":["<同表单图标题…>","表格"],
 "conditions":[{"field":"<本表字段中文名>","mode":"包含"}]}
# add-filter 禁 --form-name/--oral/--form-code（表单从 charts 推断）；透视用「表格」匹配；过滤后须重跑原命令式即非最新
```
