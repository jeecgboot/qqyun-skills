# CLI 与脚本速查（按需）

> 兼容速查（默认勿读）：CLI 命令对照，与 mutate/create 同源冗余。执行权威：改图 `mutate.md`；建盘/加组件 `create.md`；表单统计 `create.md`「工作表右侧统计」。

## 环境前缀（全文只此一处）

```bash
SKILL_REFS="$HOME/.claude/skills/jeecg-lowcode-dashboard/references"
QQY="$SKILL_REFS/scripts/qqy_ops.py"
COMP="$SKILL_REFS/scripts/comp_ops.py"
LINKAGE="$SKILL_REFS/scripts/linkage_ops.py"
LINK="$SKILL_REFS/scripts/link_ops.py"
# 之后所有命令隐含：
#   PYTHONIOENCODING=utf-8 PYTHONPATH="$SKILL_REFS:$SKILL_REFS/scripts" py <脚本> ...
# Windows：用 py；JSON 必须 --specs-file；禁止 Set-Content UTF8（BOM）
# 禁止 ConvertTo-Json 写 specs（1 元数组塌成对象）；用：
#   py -c "import json; json.dump([...], open(r'PATH','w',encoding='utf-8'), ensure_ascii=False)"
```

下文示例省略该前缀，写作 `py "$QQY" …`。

## 脚本一览

| 脚本 | 用途 |
|------|------|
| `qqy_ops.py` | 建盘/加图/表单统计/按钮/过滤/edit-filter/改名/rebind-chart/set-chart-filter/set-chart-calc/set-chart-color/set-chart-sort |
| `comp_ops.py` | list/edit/delete/move/switch-type（**add 不能用于 QQY 统计图**） |
| `page_ops.py` | 背景/主题；`rename` 只改 drag 名 → QQY 仪表盘改用 `rename-page` |
| `linkage_ops.py` | 联动/钻取 |
| `link_ops.py` | 外部链接 / 自定义 JS |
| `gen_qqy_all_comps.py` | 30 统计 + 7 UI 批量生成 |

---

## qqy_ops.py

```bash
# 业务盘（1 次进程）
py "$QQY" create-dashboard API TOKEN \
  --tenant-name "北京国炬信息技术有限公司" --app-name "应用2" --form-name "产品表" \
  --name "产品统计仪表盘" --group "数据分析" --specs-file SPECS.json

# 定位（仅排查；建盘用 create-dashboard --tenant-name）
py "$QQY" tenants API TOKEN --name "测试"
py "$QQY" apps API TOKEN --tenant-id TID --name "902"
py "$QQY" forms API TOKEN --tenant-id TID --app-id APP
py "$QQY" forms API TOKEN --tenant-id TID --app-name "仓储系统管理"
py "$QQY" fields API TOKEN --tenant-id TID --app-id APP --form-code FORM_CODE
py "$QQY" fields API TOKEN --tenant-id TID --app-name APP --form-name "物料档案"
py "$QQY" menus API TOKEN --tenant-id TID --app-id APP|--app-name APP

# 空白页（业务盘请用 create-dashboard）
py "$QQY" create-page API TOKEN --app-id APP --tenant-id TID --name "订单每日数量"

# 加图（≥2 张一次；Windows --specs-file）
py "$QQY" add-charts API TOKEN --app-id APP --tenant-id TID --page-id PAGE \
  --form-code FORM --form-name "订单表" --specs-file SPECS.json
# 跨应用
py "$QQY" add-charts API TOKEN --tenant-id TID \
  --app-name "应用1" --page-name "测试" --form-app-name "应用2" --form-name "产品表" --specs-file SPECS.json

# 归组（仅历史未归组页；新建已自动归组）
py "$QQY" group-menu API TOKEN --app-id APP --tenant-id TID --page-id PAGE --group "数据分析"

# 工作表右侧统计
py "$QQY" add-form-chart API TOKEN --tenant-id TID --app-name APP --form-name FORM \
  --type private --title "本月每日订单数量"
# 饼图按选项统计：勿传 --date-group
py "$QQY" add-form-chart API TOKEN --tenant-id TID --app-name APP --form-name FORM \
  --type private --title "按多选框组统计" --comp JPie --dim 多选框组 --val record_count --query-range all
py "$QQY" delete-form-chart API TOKEN --tenant-id TID --app-name APP --form-name FORM \
  --type private --title "本月每日订单数量"
py "$QQY" move-form-chart API TOKEN --tenant-id TID --app-name APP --form-name FORM \
  --type public --to private --title "…"
py "$QQY" copy-form-chart API TOKEN --tenant-id TID --app-name APP --form-name FORM \
  --type public --title "…"

# 按钮 / 查询面板 / 改名 / mutate（权威示例与字段约束 → ../mutate.md / ../create.md）
py "$QQY" add-buttons API TOKEN --tenant-id TID --app-name APP --page-name PAGE --specs-file BUTTONS.json
py "$QQY" add-filter API TOKEN --tenant-id TID --app-name APP --page-name PAGE --specs-file FILTER.json
py "$QQY" edit-filter API TOKEN --tenant-id TID --app-name APP --page-name PAGE --field 产品名称 --mode 等于 --value 测试
py "$QQY" rename-page API TOKEN --tenant-id TID --app-name APP --page-name "旧名" --name "新名"
py "$COMP" switch-type API TOKEN PAGE_ID --name "<图标题>" --to JLine
py "$QQY" rebind-chart API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --name "<图>" --dim … --val … [--query-range …] [--form-app-name … --form-name …] \
  [--grp …] [--assist-y …] [--assist-type …] [--comp DoubleLineBar]
py "$QQY" set-chart-filter API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --name "<图>" --field 销量 --op 大于 --value 100
py "$QQY" set-chart-calc API TOKEN --tenant-id TID --app-name APP --page-name PAGE --comp JBar --formula 求和×求和
py "$QQY" set-chart-color API TOKEN --tenant-id TID --app-name APP --page-name PAGE --comp JBar --color "#FFD700"
# 柱体渐变（每色一条 customColor；禁 {color,color1} 一条）→ ../mutate.md
py "$QQY" set-chart-color API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --name CHART --comp JBar --colors "#64b5f6,#1890FF" --gradient
# 折线类型 曲线/折线/面积（可与 --color 同条；禁 switch-type JSmoothLine/JArea）→ ../mutate.md
py "$QQY" set-chart-color API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --name CHART --comp JLine --color 黄色 --line-type 面积
# 已有饼改色+数值标签（同条；禁手写 py）→ ../mutate.md
py "$QQY" set-chart-color API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --name CHART --colors 紫,绿,黄色 --label-show
# 前 N 项 + 排序（≠ set-chart-filter）→ ../mutate.md
py "$QQY" set-chart-sort API TOKEN --tenant-id TID --app-name APP --page-name PAGE \
  --name CHART --top-n 8 --field 库存数量 --order desc
# 聚合表/工厂
py "$QQY" save-agg API TOKEN --tenant-id TID --app-name APP --specs-file AGG.json
py "$QQY" delete-agg API TOKEN --tenant-id TID --app-name APP --name "库存聚合"
```

**add-charts specs 旗标：** `comp,title,x/y/w/h,dim,val,grp,assistY,assistType,dateGroup,colors,percentLabel,scatterLabelShow,queryRange,calc,unit,numberLevel,isCompare,compareType,compareValue,trendType,barWidth,borderRadius,lineType,dataFilterNum,sorts,labelShow,showLinearGradient,option`（语义 → ../create.md / ../mutate.md）。  
**save-agg specs：** `{name,kind,join,forms,links,headers,calcs,filters}` → `aggregation.md`（links 同 type 且值相等；按关联记录名称用单表）。  
**add-filter specs：** `{title,place,w,h,showQueryBtn,charts:[图标题],conditions:[{field,label,mode}]}`。  
**specs 文件：** Write / `py -c json.dump` 无 BOM → `--specs-file`；成功后立刻删。Windows 禁 `ConvertTo-Json`（见 SKILL.md「运行」节）。

---

## comp_ops.py

> 增删改用本脚本；禁止手写 `bi_utils.add_component`+`save_page`（会空列表覆盖丢组件）。  
> QQY **统计图添加**必须走 `qqy_ops add-charts` / JT 的 `comp/add`，本脚本 `add` 默认 dataType=1。

```bash
py "$COMP" list API TOKEN PAGE_ID
py "$COMP" delete API TOKEN PAGE_ID --name "组件名"
py "$COMP" edit API TOKEN PAGE_ID --name "组件名" --set "option.title.text=新标题"
py "$COMP" edit API TOKEN PAGE_ID --name "组件名" --set "option.showValue=true" --set "option.unit=个"
py "$COMP" add API TOKEN PAGE_ID --comp "JBar" --title "柱形图" --x 0 --y 0 --w 12 --h 30   # 仅静态/UI
py "$COMP" batch-add API TOKEN PAGE_ID --specs-file BATCH.json   # ≥2 个一次 save
py "$COMP" move API TOKEN PAGE_ID --name "组件名" --x 0 --y 17
# move 改了 --w/--h 后须修回像素 size：width=w*75 height=h*11
py "$COMP" edit API TOKEN PAGE_ID --name "组件名" --set "size.width=900" --set "size.height=352"
py "$COMP" switch-type API TOKEN PAGE_ID --name "基础柱形图" --to "JLine"
# QQY 已有统计图同命令：--name=componentName --to=JLine/JBar/…；打印 SWITCHED=
# （QQY 分支保留绑定；积木盘仍走 dataSet 迁移。勿对地图/JNumber/JTotalProgress 硬切）
```

---

## linkage_ops.py

| | 联动 `add-linkage` | 钻取 `add-drill` |
|--|-------------------|------------------|
| 刷新 | **其他**组件 | **自身** |
| 参数 | `--source` + `--target` | 仅 `--comp` |
| mapping | `src=tgt`，多组逗号分隔 | QQY：`name=<nameFields[0].fieldName>` |

```bash
py "$LINKAGE" show API TOKEN PAGE_ID
py "$LINKAGE" add-linkage API TOKEN PAGE_ID --source "源" --target "目标" --mapping "value=age"
py "$LINKAGE" remove-linkage API TOKEN PAGE_ID --source "源" --target "目标"
py "$LINKAGE" add-drill API TOKEN PAGE_ID --comp "图表名" --mapping "name=input_xxxx"
py "$LINKAGE" remove-drill API TOKEN PAGE_ID --comp "图表名"
# 打印 DRILLED=；口语「点柱按名称过滤自己」= 钻取（自过滤）
```

禁止：`add-drill --source/--target`；mapping 用 `=` 不用 `:`。  
CLI：`menus` 无 `--name`；`comp_ops list` 无 `--tenant-id`/`--app-id`。

---

## link_ops.py

```bash
py "$LINK" show API TOKEN PAGE_ID
py "$LINK" set API TOKEN PAGE_ID --name "基础柱形图" --url "https://www.jeecg.com"
py "$LINK" set API TOKEN PAGE_ID --name "饼图" --url "https://example.com?c=\${name}"
py "$LINK" remove API TOKEN PAGE_ID --name "饼图"
py "$LINK" set-js API TOKEN PAGE_ID --name "基础柱形图" --js 'window.open("http://example.com");return false;'
py "$LINK" remove-js API TOKEN PAGE_ID --name "基础柱形图"
```

URL 占位：`${name}` / `${value}` / `${type}`。打开方式 `--target`：`_blank`（默认）/ `_self`。  
`config.jsConfig` 执行顺序：jsConfig →（return true?）→ 外链 → 联动 → 钻取。

```javascript
window.open("https://example.com/detail?name=" + params.name + "&value=" + params.value);
return false;
```

也可用：`py "$COMP" edit … --set "jsConfig=…"`。

---

## bi_utils 要点

```python
import bi_utils
bi_utils.init_api(API_BASE, TOKEN, extra_headers={
    'X-Low-App-ID': APP_ID, 'X-Tenant-Id': str(TENANT_ID),
})
# 无 bi_utils.init() 方法

page = bi_utils.query_page(PAGE_ID)
tmpl = page.get('template') or []          # 已是 list
# comp['i'] / componentName / component / pageCompId
bi_utils._page_components[PAGE_ID] = tmpl
bi_utils.save_page(PAGE_ID)                # 已有页业务加组件优先 saveCompToPage
```

---

## QQY UI 七组件（dataType=1）

已点名按钮/过滤 → `add-buttons` / `add-filter`（../create.md「按钮 / 查询面板」）。`op`：创建记录/打开列表视图/打开页面+pageId/打开链接+url/调用业务流程+flowId。

| 组件 | 要点 |
|------|------|
| JCustomButton | `chartData` 为数组；已有页 `comp/add`+`saveCompToPage` |
| JText | `chartData` 纯字符串；`turnConfig.url`；`card.title=''` |
| JFilterQuery | 新建 `add-filter`；改匹配/默认值 `edit-filter`；`queryMode` 与图表 condition 编号不同 |
| JCarousel | 交互选工作表+图片字段+视图；`field`=imgupload model |
| JIframe | 展示 URL=`option.body.url` |
| JCurrentTime | 业务路径 ../create.md「文本 / 轮播 / iframe / 时钟」：`comp/add`+`saveCompToPage`；`showWeek` 须 `'show'/'hide'` 字符串；`format`+`hourlySystem:'24'`；右上角 `x:16 y:0 w:8 h:10`；禁止 `add-charts` |
| JDragEditor | `chartData`=HTML 字符串 |
