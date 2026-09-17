# 手动构造 desformDesignJson（降级方案）

> 仅当 `desform_creator.py` + JSON 配置方式执行失败，且用户确认降级后才使用此方案。
> 核心规则（card 包裹、key/model 格式、易错控件等）已在 SKILL.md 主文件中说明，此处不重复。

## 参考文件

手动构造时需要阅读以下文件获取完整的 JSON 结构和控件配置：

- `references/desform-design-json-schema.md` — JSON Schema 结构、控件类型清单、通用字段
- `references/desform-widget-options.md` — 每种控件的完整 options 配置

## 调用 API

使用 Python 调用（不要用 curl），详见：
- `references/desform-python-utils.md` — desform_utils.py 使用指南、快捷函数列表、layout 参数说明
- `references/desform-api-notes.md` — API 踩坑记录、错误处理、命名规则
