# 已有盘顶部加「5-op 按钮组」金标（按需）

> **实例字面量，不是通则。** 仅当需求与此金标同类：**已有盘顶部放一组按钮，op 混合 ≥2 类（创建记录/打开列表视图/打开页面/打开链接/调用业务流程），每行 N 均分、图形样式**。单类简单按钮 → create.md「按钮/查询面板」即可；字段/文案按点名替换，勿当默认。
> 2026-09-08 实测通过（新疆兵团 TID=1008 应用1 AI看板903）：`ADDED=JCustomButton buttons=5 rowNum=2 btnWidth=divide place=top`，接口耗时 1.4s。本文件目标重放 ≤60s（冷会话 2–3 轮）。

## 1. 直跑前的 ID（只查缺的，一次 Bash 拿全）

`menus` 输出 drag 行 `menuUrl` = 目标盘 pageId（含「打开页面」要跳的看板）；业务流程 flowId 不在 menus，用 extActProcess 查（lowAppId=应用ID 过滤）：

```bash
QQY="py $SKILL_REFS/scripts/qqy_ops.py"
# pageId：目标盘 + 跳转盘
$QQY menus "$API" "$TOKEN" --tenant-name 租户 --app-name 应用
# flowId（heredoc，中文 processName 须 urlencode；result 可能是 dict(records)/list，先判类型）
py -X utf8 - <<'EOF'
import urllib.request, urllib.parse, json
API,TOKEN,LOWAPP="<API>","<TOKEN>","<APP_ID>"
H={"X-Access-Token":TOKEN,"X-Tenant-Id":"<TID>","Content-Type":"application/json"}
kw=urllib.parse.quote("流程中文名")
r=json.loads(urllib.request.urlopen(urllib.request.Request(API+"/act/process/extActProcess/list?pageNo=1&pageSize=50&processName="+kw,headers=H),timeout=30).read().decode())
res=r.get("result") or {}; recs=res.get("records") if isinstance(res,dict) else (res if isinstance(res,list) else [])
print([(p.get("id"),p.get("processName"),p.get("lowAppId")) for p in recs])
EOF
```

## 2. 按钮 specs（Write 到系统临时目录；字面量可照抄本单换 ID）

```json
# buttons.json — 5-op 按钮组：顶部 每行2 均分 图形按钮
{"rowNum":2,"btnType":"graphical","btnWidth":"divide","place":"top",
 "buttons":[
   {"title":"新增","op":"创建记录","form":"产品表"},
   {"title":"列表","op":"打开列表视图","form":"产品表"},
   {"title":"看板","op":"打开页面","customPage":{"label":"本月订单看板","value":"1257139876441759744","key":"1257139876441759744"}},
   {"title":"外链","op":"打开链接","url":"https://www.baidu.com","openMode":"2"},
   {"title":"流程","op":"调用业务流程","bizFlow":{"label":"省份销售记录","value":"2095700506042855426","key":"2095700506042855426"}}]}
# 字段要点：customPage/bizFlow 必须 {label,value,key}；外部打开必须 openMode:"2"；
# 多行高度脚本自动（h≈20×ceil(n/rowNum)，本组 h=60 三行）；place=top|bottom
```

## 3. 直跑 + 停

```bash
# 参数顺序铁律：qqy_ops.py <command> API TOKEN（脚本在 references/scripts/ 下，勿 cd 相对引用）
$QQY add-buttons "$API" "$TOKEN" --tenant-name 租户 --app-name 应用 --page-name 看板名 --specs-file buttons.json
# 停：ADDED=JCustomButton … 打印即停，禁 query_page；删临时 JSON
```

## 4. 换盘/换应用时

- 表单名用用户点名中文名即可（`FORM_CODE=` 回显确认）；页面/流程 ID 按 §1 现查，**禁止沿用本单 ID**（memory 旧 ID 一律丢弃，铁律 #2）
- 凭证 → 首条 Bash 前 Read 一次 memory `reference_jeecgboot_credentials.md` 取 API/TOKEN（铁律 #1；上文 `$API`/`$TOKEN` 即此）
