# 工作表右侧统计（按需）

> **默认不要读。** 加/删/改归属/复制到当前：以 `create.md`「工作表右侧统计」为准直接跑命令。  
> **仅当**：① 复制到**仪表盘/自定义页面**需扁平化；② 命令失败需自定义 dim/字段排障。  
> 历史教训索引 → `lessons.md`。

## 与仪表盘的区别

| 项 | 说明 |
|----|------|
| 加图 CLI | `add-form-chart`：**`--comp` 只收 J 码**（JPie/JBar/JLine…，中文口语必被拒）；默认 comp=JBar、dim=create_time、date-group=3、val=record_count、query-range=month（要「全部」显式 `--query-range all`）。金样例 → `create.md` 工作表右侧统计 |
| 入口 | URL `/myapp/{appId}/form/{desformId}` 右侧「统计」抽屉，**不是** drag 页 |
| Tab | `public` / `private` |
| 列表 | `GET /desform/chart/list?code={formCode}`；`item.chartId`=组件 ID，`item.id`=挂载 ID |
| 改归属 | `move-form-chart`（`updateType` 用挂载 id） |
| 删除 | `delete-form-chart`（挂载 remove + comp deleteById） |
| config | dataType=4；表单统计常为**嵌套** `{component,id,config:{…}}` |

## 复制到仪表盘（必须扁平化）

| | 表单统计（源） | 仪表盘（目标） |
|---|---|---|
| 结构 | **嵌套** | **扁平** dataType=4 顶层 |
| 常缺 | — | `appId` / `appType` / `type` / `filterField` 等 |

**禁止** `copyById` 原样 append + `/drag/page/edit` → 不渲染、不能编辑。

**推荐做法 B（官方）：**

1. `POST /drag/page/comp/add` `{pageId, component, config:<扁平 JSON 字符串>}` → `pageCompId`
2. template 只 push 元数据（**无 config 字段**）：`x/y/w/h/i/component/componentName/pageCompId`
3. `POST /drag/page/saveCompToPage` `{id, template: json.dumps(template), updateCount}`  
   — `template` **必须是字符串**，传 list 报 `Cannot deserialize … String from Array`

**做法 A：** 同页同表单正常组件扁平 config 做骨架 → 覆盖语义字段 → template 带 config → `save_page`（会重建 comp）。

已有页优先做法 B，避免换 pageCompId 弄坏 JFilterQuery 联动。1 次进程完成定位+写入。

**最短路径 = 2 条 Bash（2026-09-08 实测；无现成 CLI——`copy-form-chart` 只复制统计 Tab 内、`page_ops.py` 无此命令，禁再花轮次找命令）：**

Bash1（解析 ID）：`qqy_ops.py menus --tenant-name … --app-name …` 取 drag 行 pageId + `forms` 取 formCode（**禁跑 `apps`**——menus/forms 自带按名解析）。

Bash2 = **单个 python(requests) 进程完成全链**（拆多轮 = 路径违规）：
1. `GET /desform/chart/list?code={formCode}` → `result` 直接是 **list**（非 {records}）；找 `type=public` 的图；`item.chartId` 即 comp id。**同型多图**（公共区 2+ 张同 component）→ **默认取首张直接复制，禁询问、禁对比**（2026-09-08 复测：重复副本配置哈希一致取首即可；旧规则「逐个交用户确认、禁默认首张」按用户铁令作废）
2. `GET /drag/page/comp/queryById?id={chartId}` → `result.config` 是 JSON **串**（嵌套 envelope `{component,id,config}`）；扁平段 = 解析后 `['config']`（顶层含 `dataType/formType/formId/tableName/nameFields/valueFields/calcFields/chart/option/compStyleConfig/…/seriesType`），**剔除缓存 `chartData`**
3. `GET /drag/page/queryById?id={pageId}` → `result.template` 是 JSON **串**（组件元数据列表；现项目带内嵌 config，**保持原样**）；记 `result.updateCount`
4. `POST /drag/page/comp/add` `{pageId, component:'JPie', config: json.dumps(扁平段)}` → 成功码=**200**（message「操作成功」，**非 0**——禁 `code!=0` 当失败退出）；新组件行 ID 在 **`result.id`**（**不是** `pageCompId`——那是 template 项里引用它的字段名）
5. 新项目只 push 元数据：`visible/pcX/pcW/pcY/x/y/w/h/i/orderNum/component/componentName/pageCompId`；位置 `y = max(现项目 y+h)`
6. `POST /drag/page/saveCompToPage` `{id, template: json.dumps(tpl), updateCount: 原值}` → 200
7. 回读校验：**数 template 项数 = 原数+1**（打印/截断禁 tail `[:N]`——坏项会藏在截断外）→ 末项 `componentName/pageCompId` + `comp/queryById?id=pageCompId` 返回 `component=JPie`，即停。**中途失败重跑前先清坏项**：上次 save 已真实落库——`pageCompId=None` 的项（`i='0'`、componentName=裸码）渲染空白，重取 template 滤掉 `pageCompId` 为空再 save

**响应解码铁则：全程 `requests.get(...).content.decode('utf-8')` 再 `json.loads`**。QQY 响应常含未转义换行/中文，`curl | python json.loads` 在 Windows 管道连环失败（2026-09-08 实测挂 4 轮）；第一轮失败立即换 requests，禁止同法重试。

**成功码铁则（2026-09-08 实测）：本环境 drag/desform 接口成功返回 `code:200`（message「操作成功」）**——不是 Jeecg 常规 code:0。raw 链首轮必须原样打印完整响应再串联，禁按 `code!=0` 判失败。

## 接口速查

| 接口 | 方法 | 说明 |
|------|------|------|
| `/desform/chart/list?code=` | GET | 列表 |
| `/desform/chart/save` | POST | 挂载 `{chartId,type,designFormCode}` |
| `/desform/chart/updateType` | POST | 公共↔个人（挂载 id） |
| `/desform/chart/remove` | DELETE | 解挂载 |
| `/drag/page/comp/createDefChart` | GET | 默认两图（会真实创建） |
| `/drag/page/comp/add` / `edit` / `queryById` / `deleteById` / `copyById` | — | comp CRUD；copyById **嵌套**不能直接进仪表盘 |
| `/drag/page/queryById?id=` | GET | 页面行：`template`(串) + `updateCount`，复制前必取 |
| `/drag/page/saveCompToPage` | POST | template 必须 JSON **字符串** |

## 排障要点

- dim 直用字段显示名原词（用户说「按多选框组统计」→ 该 checkbox 字段显示名就叫「多选框组」，点名 0 探查）；报字段不存在才停问
- 非日期 dim 不要 `--date-group`（默认 3 会套成「字段(日)」+ 暂无数据）
- list 的 `title` 常为 `None`，匹配用 `option.title.text`；`CAND title=` 未命中立刻重跑
- 同名全删/全改归属
- 复制到盘全链单进程 requests；响应含未转义换行/中文乱码 → `.content.decode('utf-8')` 再 `loads`（curl 管道连挂即弃，勿重试）
- 无现成 CLI：`copy-form-chart` 仅统计 Tab 内复制、`page_ops.py` 无复制命令 → 直接走「最短路径」raw 流程，禁找命令
- 完成凭据 = 回读 page.template 含新 pageCompId + comp/queryById 返回目标 component，写入 code 200 即停
