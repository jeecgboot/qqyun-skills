# 打印设置

控制表单的打印功能。所有字段均存储在 `designConfig.config` 中，通过 `update_design_config` 修改。

> **想一键自动生成积木报表并关联打印？** 不要手动准备 URL 再填 `jmReportURL` —— 直接用
> `scripts/desform_jimureport.py`，它会自动建报表、按字段排版、回写 `allowJmReport`/`jmReportURL`。
> 详见 `references/desform-jimureport.md`。本文档仅用于**已有现成报表 URL**、只需开关打印的场景。

---

## config 字段说明

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `allowPrint` | boolean | `false` | 启用系统默认打印（启用后表单右上角显示打印图标） |
| `disabledAutoGrid` | boolean | `false` | 禁用自适应布局（打印时布局混乱时开启此项） |
| `allowJmReport` | boolean | `false` | 启用积木报表打印（高度自定义的打印效果） |
| `jmReportURL` | string | `""` | 积木报表地址（`allowJmReport=true` 时**必填**） |

---

## 字段联动关系

```
allowPrint=true  → 表单右上角出现打印图标
  └─ disabledAutoGrid=true  → 打印时禁用自适应布局（解决布局混乱问题）

allowJmReport=true  → 使用积木报表打印（独立于 allowPrint，两者可同时开启）
  └─ jmReportURL   → 必须填写积木报表的 URL
```

- `disabledAutoGrid` 与 `allowPrint` 无强制联动（配置中独立），但业务上仅在 `allowPrint=true` 时有意义
- `allowPrint` 和 `allowJmReport` 可以同时为 `true`，两种打印方式并存

---

## Python 操作示例

```python
from desform_utils import init_api, update_design_config

init_api('<api_base>', '<token>')

# 开启系统默认打印
update_design_config('my_form', {"allowPrint": True})

# 开启打印 + 解决布局混乱
update_design_config('my_form', {
    "allowPrint": True,
    "disabledAutoGrid": True,
})

# 开启积木报表打印
update_design_config('my_form', {
    "allowJmReport": True,
    "jmReportURL": "https://report.example.com/jmreport/view/123456",
})

# 同时开启两种打印
update_design_config('my_form', {
    "allowPrint": True,
    "allowJmReport": True,
    "jmReportURL": "https://report.example.com/jmreport/view/123456",
})

# 关闭所有打印
update_design_config('my_form', {
    "allowPrint": False,
    "allowJmReport": False,
})
```

---

## 注意事项

- `jmReportURL` 的来源取决于场景：
  - **一键生成场景**（用 `scripts/desform_jimureport.py`）：URL 由脚本自动生成并回填，格式为 `{{sysBasePath}}/jmreport/view/{reportId}`，**无需用户提供**。
  - **手动开关已有报表场景**（本文档）：URL 必须由用户提供真实地址，AI **不能猜测或伪造**一个不存在的报表 URL。
- `disabledAutoGrid` 同时影响表单编辑视图（非仅打印），开启后整个表单禁用自适应栅格
