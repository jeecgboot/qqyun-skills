# 金标：单表单「按钮门户」复合盘（整盘一次成型）

> 场景：租户+应用内，**同一张表单**建复合盘——数字卡行（总数+合计）+ 柱/折并排行 + 图形按钮组 + afterChart 统计折线 + 查询条件联动该折线。
> 实例：新疆兵团(1008)/应用1/产品表 → 「测试按钮门户」入组「首页门户」。**同款提示词历史 1 分钟完成 = 照抄本文件字面量**（2026-09-08 实测整链一次 `create-dashboard` 4.3s）。
> 与 `gold-5ops-button-group.md` 区别：那是**已有盘**加按钮组；这是 `create-dashboard --layout-file` 整盘新建。

## 一次成型命令（单条 Bash）

```bash
# 凭证：首条 Bash 前 Read memory reference_jeecgboot_credentials.md 取 QQY_API / QQY_TOKEN（会话内复用）
QQY_API="http://192.168.1.66:8080/jeecg-boot"; QQY_TOKEN="<token>";
SKILL_REFS="$HOME/.claude/skills/jeecg-lowcode-dashboard/references"
PYTHONIOENCODING=utf-8 PYTHONPATH="$SKILL_REFS:$SKILL_REFS/scripts" \
  py "$SKILL_REFS/scripts/qqy_ops.py" create-dashboard "$QQY_API" "$QQY_TOKEN" \
  --tenant-name 新疆兵团 --app-name 应用1 --form-name 产品表 \
  --name 测试按钮门户 --group 首页门户 --layout-file layout.json
# 停：PAGE_ID= / SHARE_URL= / ADDED= 打印完即停（成功后 rm layout.json）
```

## layout.json（实测字面量；换表单只改字段「显示名」/标题，引擎字段回显 + CAND 自愈）

```json
{
  "charts": [
    {"comp": "JNumber", "title": "产品总数", "x": 0, "y": 0, "w": 12, "h": 17, "dim": [], "val": "record_count"},
    {"comp": "JNumber", "title": "数字合计", "x": 12, "y": 0, "w": 12, "h": 17, "dim": [], "val": "销量"},
    {"comp": "JBar", "title": "本月按日销量", "x": 0, "y": 17, "w": 12, "h": 32, "dim": "create_time", "val": "销量", "dateGroup": "按日", "queryRange": "本月"},
    {"comp": "JLine", "title": "本月销量折线图", "x": 12, "y": 17, "w": 12, "h": 32, "dim": "create_time", "val": "销量", "dateGroup": "按日", "queryRange": "本月"}
  ],
  "buttons": {
    "rowNum": 2,
    "btnType": "graphical",
    "btnWidth": "divide",
    "round": true,
    "buttons": [
      {"title": "新增订单", "op": "创建记录", "form": "产品表"},
      {"title": "打开产品列表视图", "op": "打开列表视图", "form": "产品表"}
    ]
  },
  "afterCharts": [
    {"comp": "JLine", "title": "本周记录数统计", "w": 24, "h": 32, "dim": "create_time", "val": "record_count", "dateGroup": "按月", "queryRange": "本周"}
  ],
  "filter": {
    "title": "查询条件",
    "place": "above",
    "charts": ["本周记录数统计"],
    "conditions": [{"field": "名称", "mode": "包含"}]
  }
}
```

## 版面结果（24 列网格，坐标即成功态）

| 行 | 内容 | 坐标 |
|----|------|------|
| 1 | 数字卡 产品总数 / 数字合计（并排） | (0,0)/(12,0) w12 h17 |
| 2 | 柱状图 + 折线图 本月按日销量（并排） | (0,17)/(12,17) w12 h32 |
| 3 | 图形按钮组 ×2（每行2、均分、圆角、h20） | 引擎自动排在图表块后（无 place 键=实测） |
| 4 | afterChart 折线 本周记录数统计（整行） | (0,69) w24 h32（=图表块底 49 + 按钮行 20） |
| — | 查询条件面板 place=above，仅联动 afterChart 折线 | charts:["本周记录数统计"] 必须与 afterChart title 一致 |

## 实测要点（2026-09-08）

- **并排必须显式 x/y**：省略坐标 → 引擎只从上到下顺序排（全 x=0 单列堆叠），要并排就照上表给全 x/y（create.md「布局」行 ⚠️、lessons §61）。
- 口语归一实测：queryRange 本月/本周 → month/week；dateGroup 按日 → 3、按月 → 2（= create.md `--date-group/--query-range` 行）。
- 按钮 op 口语直接通：创建记录（form=产品表）/ 打开列表视图；btnType=graphical btnWidth=divide round=true → 图形/均分/圆角，引擎回显 `btnType=graphical … h=20`。
- 数字卡：总数卡 `val=record_count`；合计卡 `val=数值字段`（如 销量）。**禁叠 `calc`**：表含 money 字段（单价）时引擎自动拼 $f-x$*$f-y$ 垃圾公式（SKILL.md layout 注释 2026-09-08 行）。
- 字段写「显示名」即可：run 内 `数量→销量` 近义猜测被引擎 CAND 到 `number_1788403992897_937151(销量)`，无需预查 fields。
- 建错布局（如漏 x/y）→ 同条 `delete-page --page-name … && create-dashboard …` 删盘重建，勿手工逐组件 patch。
