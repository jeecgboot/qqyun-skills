# 发布设置（外部链接）

发布设置的本质是**外部链接配置**，所有字段均存储在 `designConfig.config` 中。
通过 `update_design_config` 修改，无需改动控件列表。

---

## config 字段说明

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `allowExternalLink` | boolean | `false` | 是否允许外部链接访问 |
| `externalTitle` | string | `""` | 页面标题（显示在浏览器标签页）；空字符串在后台存为 `"#empty#"`，读取时需反向转换 |
| `dialogOptions.width` | number | `1000` | 页面宽度（px），最小 320，大屏显示器上表单区域宽度，移动端不受影响 |
| `headerImgUrl` | string | `""` | 页眉图片 URL（单个 URL 字符串，非数组；建议图片宽度 1600px） |
| `externalLinkShowData` | boolean | `false` | 保存后是否展示已保存的数据 |

---

## 外部链接 URL 格式

```
{BASE_URL}/desform/pub/{desformId}
```

- 使用的是表单 **ID**，不是 code
- `desformId` 从 `query_form(code)['id']` 获取
- `BASE_URL` 是后端地址（`init_api` 传入的第一个参数）

---

## externalTitle 的特殊值处理

前端对 `externalTitle` 有特殊处理：

| 场景 | 存储值 | 显示值 |
|------|--------|--------|
| 用户未填写（显示表单名） | `""` 或未设置 | 自动显示 `desformName` |
| 用户主动清空 | `"#empty#"` | 显示为空 |
| 用户填写内容 | `"我的表单"` | `"我的表单"` |

**AI 配置时**：直接传用户希望显示的标题字符串即可，不需要传 `"#empty#"`。若用户要求清空标题，传 `"#empty#"`。

---

## Python 操作示例

```python
from desform_utils import init_api, query_form, update_design_config

init_api('<api_base>', '<token>')

# 开启外部链接（最简）
update_design_config('my_form', {"allowExternalLink": True})

# 完整配置
update_design_config('my_form', {
    "allowExternalLink": True,
    "externalTitle": "员工信息填报",
    "dialogOptions": {"width": 800},   # 只更新 width，不影响 top/padding
    "externalLinkShowData": True,
    "headerImgUrl": "https://example.com/banner.png",
})

# 关闭外部链接
update_design_config('my_form', {"allowExternalLink": False})

# 获取外部链接 URL
form_data = query_form('my_form')
api_base = '<api_base>'
external_url = f"{api_base}/desform/pub/{form_data['id']}"
print(f"外部链接：{external_url}")
```

---

## 注意事项

- `dialogOptions` 是嵌套对象，`update_design_config` 会深度合并，只传需要改的子字段即可
- `headerImgUrl` 是单个字符串，不是数组；前端组件内部会转换为数组格式展示，但 config 中存的始终是字符串
- 外部链接中**无法使用**用户、部门组件（前端有提示）
