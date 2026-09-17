# 关联记录「查询工作表」默认值 —— 真实落地格式（2026-09-02 实测修正）

> **触发场景**：改已有关联记录，默认值 = 查询工作表（linkage）。
>
> 本文是 `fast-link-record.md` 的修正篇 + 兜底配方。**`update_link_record.py` 已于 2026-09-02 修复**：linkage 默认值自动写字符对象 + 整单设计保存，正常跑脚本即可。本文用于：①了解根因，②遇到**历史遗留字符串形态** value（2026-09-02 修复前写入、接口 success 但设计器面板不显示）时手动兜底。
>
> ⚠️ **2026-09-16 补充核对**：当前部署的设计器提交路径是 `advancedSetting.defaultValue.value = encodeLINKAGETConfig(配置对象)`，encode/decode 均已为恒等函数（不压缩键名、不摊字符）——**新一轮 API 直写应按 `desform-linkage-query.md` 二节的「对象形态」**；本文「字符对象 / 双段」仅作 2026-09-02 前后历史数据的读取兜底。

## 一、为什么以前「设置不上」（根因，已修复）

- 修复前：`update_link_record.py` 把 `advancedSetting.defaultValue.value` 存成**普通字符串**（URL 编码串，如 `%7B%22aid%22…`），接口返回 success，解码后内容完全正确。
- 但**设计器面板 / 运行时只认「编码串逐字符展开的对象」**：`{"0":"%","1":"7",…,"1005":"D"}`（前端把字符串 spread 成字符索引对象再入库）。
- 结果：字符串版写入后接口成功但面板读不到 → 表现就是「没有设置上」；手工在界面重存一次（变成字符对象）就正常。
- 顺带根因二：`update_widget` 是**深合并**，旧 value（字符串版/长键段残留）删不掉，会与新版叠加成脏对象。修复后 linkage 一律走**整单设计保存**。

## 二、判定口诀（修复后）

| 写入方 | value 形态 | 设计器面板 |
|---|---|---|
| `update_link_record.py`（当前版本，2026-09-02 起） | 字符对象 `{"0":…}` + 整单保存 | 显示 ✓ |
| 历史版本脚本写入（2026-09-02 前） | 字符串 | 不显示 ✗（需兜底，见四） |
| 设计器手工保存 | 字符对象 `{"0":…}` | 显示 ✓ |

实测案例：同一份正确内容，测试应用先用旧版脚本写字符串 → 面板空；改成字符对象整单回写 → 面板正常显示条件。

## 三、value 内部结构（解码后 = 运行时配置，压缩键短格式）

```json
{
  "aid": "<应用ID>",
  "fCode": "<源表 code>",
  "mType": "OR",                // 或；AND 且
  "oper": "CUSTOM_SORT",        // FIRST / LAST / CUSTOM_SORT / COUNT / MAX / MIN / AVG / SUM / IGNORE
  "rules": [
    {"model": "<源表字段model>", "rule": "gt", "vType": "fixed", "value": ["0"],
     "sqParam": {"type": "money", "rule": {"value": "gt"}}},        // rule 小写；sqParam.rule 是对象 {value}
    {"model": "create_by", "rule": "eq", "vType": "field", "value": ["<本表字段model>"],
     "sqParam": {"type": "select-user", "rule": {"value": "eq"}}}
  ],
  "linkages": [{"model": "<本关联记录自身model>", "lModel": "id", "linkName": "id"}],
  "sorts": [{"column": "create_time", "order": "asc"}, {"column": "<源表字段model>", "order": "asc"}],
  "isMultiple": false,
  "maxRecordCount": 200
}
```

要点：

- 条件字段 model = **源表**字段（或系统字段 `create_by`/`create_time`）；`vType:"field"` 的 value = **本表**字段 model。
- `create_by` = 源表创建人（人员系统字段），`sqParam.type = "select-user"`。
- 缺规则或依赖字段为空时整条规则运行时被跳过（如本表无「采购人」字段时配不了第二条）。
- 用户需求里说「价格升序」但源表只有「单价」字段 → 按「单价」解析，没有就叫停不要猜。
- 关联「创建人=采购人」前确认本表单**已有**「采购人」人员字段，没有先 `add_widget` 加字段。

## 四、兜底配方（历史字符串形态 / 面板仍不显示时用）

> 当前 `update_link_record.py` 已内置「字符对象 + 整单保存」，新配置直接跑脚本，本配方只在处理历史遗留或手工场景才需要。

**不要**用 `update_widget` 改这个 value（平台保存是深合并，旧键删不掉，会越叠越乱）。用整份设计 JSON 覆盖：

```python
# -*- coding: utf-8 -*-
import sys, json, os, tempfile, urllib.parse
sys.path.insert(0, r'<skill目录>/scripts')
from desform_lowapp_utils import init_lowapp
from desform_utils import query_form, save_design_from_file

init_lowapp(api_base, token, tenant_id=..., app_id=...)
design = json.loads(query_form(code)['desformDesignJson'])

# 1) 递归定位 link-record widget（按 key 或 name）
# 2) 取出 advancedSetting.defaultValue.value，若为字符串 s：
value = {str(i): ch for i, ch in enumerate(s)}        # 字符对象形态 ← 关键
#    若已是 dict：保留数字键部分（0..N 字符），长键冗余段（见下）建议重建为与字符段同义内容或删除
# 3) 修改后整单保存：
path = os.path.join(tempfile.gettempdir(), 'jeecg-desform', code + '_design.json')
json.dump(design, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
save_design_from_file(code, path)
```

Windows：中文只写文件，禁止 `python -c` 内联。

## 五、手工保存版的冗余长键段（认识即可）

设计器手工保存后，value 对象里除字符段外还会带一段长键同义配置（9 键）：

```json
{"appId": "", "desformCode": "<源表code>", "matchType": "OR", "operation": "CUSTOM_SORT",
 "rules": [{"model": "…", "rule": "GT", "valueType": "fixed", "value": [0],
            "sqParam": {"type": "money", "rule": "gt"}}],   // 大写 rule + valueType，另一套 schema
 "linkages": [{"model": "…", "linkModel": "_id", "linkName": ""}],
 "sorts": [{"column": "…", "order": "asc"}], "isMultiple": false, "maxRecordCount": 200}
```

- 面板显示读**字符段**（实测：纯字符对象无长键段也能正常显示）。
- ⚠️ 2026-09-09 实测：**部分环境纯字符段（无长键段）面板读不出条件**。UI 保存恒为「字符段+长键段」双段；API 直写建议**双段同义**（长键段特征：`appId:""`、大写 `rule`、`sqParam.rule` 字符串、`linkModel:"_id"`、`linkName:""`）。面板为准：不显示则补双段。
- 长键段可能与字符段不一致（历史深合并残留），面板不受影响。

## 六、验证

1. 回写后用户 **Ctrl+F5 刷新**设计器再打开（API 直改不会刷新已打开的页面，缓存假象最常见）。
2. 面板能看到条件/排序 = 形态正确；再新增记录验证运行时默认值。
3. 脚本 dry-run（`--dry-run`）可先看输出里 `advancedSetting.defaultValue.value` 是否已是 `<char-map N keys>` 形态。

## 七、已实测案例（八匹狼租户，2026-09-02）

- 老应用「关联记录」采购单「采购明细」（源表 `purchase_order_item`）：或(单价>0 / 创建人=本表采购人)，排序 创建时间正序 + 单价升序。手工保存「好用」= 字符对象形态。
- 测试应用 `cs_purchase_order` 采购明细：脚本字符串版面板空 → 按本文配方整单回写字符对象 → 面板显示；补「采购人」字段后加第二条 or 规则，确认可用。
- 全程接口均 success=true，差异只在 value 的存储容器（字符串 vs 字符对象）——容器不对 = 面板读不到。
