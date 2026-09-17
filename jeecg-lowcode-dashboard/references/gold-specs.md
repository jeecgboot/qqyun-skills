# 加图 / 建盘 specs 示例（按需）

> 规则权威在 `create.md`。本文件只放可复制 JSON；**字面量须按当轮用户点名替换**（表名/字段/标题均非默认值）。

## 单表新建盘示例（字面量须替换）

金额类图**省略 `calc`**。`--form-name` 跟用户点名（下例为「产品」仅作示意）。

```json
[
  {"comp":"JNumber","title":"总销量","x":0,"y":0,"w":8,"h":17,"dim":[],"val":"销量"},
  {"comp":"JNumber","title":"总销售额","x":8,"y":0,"w":8,"h":17,"dim":[],"val":"售价"},
  {"comp":"JNumber","title":"产品数","x":16,"y":0,"w":8,"h":17,"dim":[],"val":"record_count"},
  {"comp":"JLine","title":"每日销量","x":0,"y":17,"w":12,"h":32,"dim":"create_time","val":"销量","dateGroup":"3"},
  {"comp":"JLine","title":"每日销售额","x":12,"y":17,"w":12,"h":32,"dim":"create_time","val":"售价","dateGroup":"3"},
  {"comp":"JBar","title":"各产品销量","x":0,"y":49,"w":12,"h":32,"dim":"产品名称","val":"销量"},
  {"comp":"JBar","title":"各产品销售额","x":12,"y":49,"w":12,"h":32,"dim":"产品名称","val":"售价"},
  {"comp":"JPivotTable","title":"产品明细","x":0,"y":81,"w":24,"h":36,"dim":"产品名称","val":"销量"}
]
```

## 已有盘加图示例

空盘整页新建可 `y:0` 起排；**已有盘追加从 `max_bottom` 续排**（逐图省略 y = 自动装箱到底部）。下表 y 仅是整组贴入时的相对排布——贴已有盘把整组下移 `max_bottom` 或改相对 y，勿把示例的 y:0 原样写死。

```json
[
  {"comp":"JNumber","title":"总销售额","x":0,"y":0,"w":8,"h":30,"dim":[],"val":"销售额","queryRange":"month","isCompare":true,"compareType":"preMonth","compareValue":0,"trendType":"2","unit":"万元","numberLevel":"4","decimal":2},
  {"comp":"JPie","title":"销售额构成","x":0,"y":49,"w":12,"h":32,"dim":"产品名称","val":"销售额","percentLabel":true},
  {"comp":"JMultipleLine","title":"产品每日销售额对比","x":12,"y":49,"w":12,"h":32,"dim":"create_time","val":"销售额","grp":"产品名称","dateGroup":"3","colors":["yellow","red"]},
  {"comp":"JColorGauge","title":"销量当前百分比","x":0,"y":96,"w":12,"h":25,"dim":[],"val":"销量","colors":["#52C41A","#FAAD14","#FF4D4F"]},
  {"comp":"DoubleLineBar","title":"双轴","x":0,"y":121,"w":24,"h":32,"dim":"名称","val":"record_count","grp":"流程状态","assistY":"record_count","assistType":"创建人"},
  {"comp":"JRadar","title":"产品多维对比雷达图","x":0,"y":153,"w":12,"h":32,"dim":"名称","val":["销量","销售额","单价"],"legendShow":true},
  {"comp":"JBarMap","title":"省份销售额柱状地图","w":12,"h":35,"dim":"省份","val":"销售额","scatterLabelShow":true},
  {"comp":"JRankingList","title":"销量排行榜","w":24,"h":32,"dim":"关联产品","val":"销量","colors":["#FA8C16"],"dataFilterNum":10,"sorts":{"name":"销量","type":"desc"}}
]
```
