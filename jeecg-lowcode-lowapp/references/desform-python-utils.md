# desform_utils.py 函数参考

位于 `scripts/desform_utils.py`。提供控件工厂、API 封装、布局引擎、字段权限等功能。

> **阅读建议**：需要某个函数的详细说明时，直接 grep 函数名定位行号，再用 offset+limit 读取对应章节，无需全量阅读本文件。

## 函数速查表

| 函数 | 适用场景 |
|------|---------|
| **表单生命周期** | |
| `check_code_available(code)` | 新建前校验编码唯一性 |
| `create_form(name, code, widgets, ...)` | 一站式创建表单（查找/创建→保存设计→同步权限） |
| `update_form(code, widgets, ...)` | 整体重设计已有表单 |
| `update_design_config(code, config_updates)` | 只改配置不改控件（发布/通知/打印/业务规则等） |
| `copy_form(source_code, new_code)` | 复制已有表单 |
| `delete_form(code_or_id)` | 删除表单（逻辑+物理） |
| `query_form(code)` | 查询表单完整信息（含设计JSON） |
| `get_form_id(code)` | 获取表单 ID 和 updateCount |
| `get_form_fields(form_code)` | 获取所有字段的 model/key/type 映射 |
| **字段级操作** | |
| `add_widget(code, widget_or_widgets)` | 追加字段到已有表单末尾 |
| `update_widget(code, changes, *, key=None, model=None)` | 修改字段属性（优先传 key=） |
| `delete_widget(code, *, key=None, model=None)` | 删除字段（优先传 key=） |
| **设计JSON预处理** | |
| `export_design_json(code, output_path=None)` | 导出设计JSON到文件，返回 `(file_path, field_rows)` |
| `save_design_from_file(code, file_path)` | 将修改后的文件保存回后台 |
| `extract_field_table_from_design(design_json)` | 从设计JSON提取字段参照表（不调用API） |
| **权限** | |
| `sync_auth(code, design_list)` | 同步字段权限（update_form 后使用） |
| `add_auth_batch(code, design_list)` | 批量新建权限（create_form 后使用） |
| `save_auth_from_design(code)` | 从表单现有设计重建权限（权限创建失败时） |
| **列表视图** | |
| `add_list_view_table(code, name)` | 创建表格视图（系统已自动创建，按需调用） |
| `add_list_view_board(code, group_field, ...)` | 创建看板视图 |
| `add_list_view_calendar(code, date_columns, ...)` | 创建日历视图 |
| `config_calendar_columns(view_id, date_columns)` | 改已有日历视图的开始/结束日期组 |
| `add_list_view_gantt(code, start_field, end_field, ...)` | 创建甘特图视图 |
| `query_list_views(code)` | 查询表单下所有列表视图 |
| `query_list_view_by_id(view_id)` | 查询视图完整配置 |
| `delete_list_view(view_id)` | 删除列表视图 |
| `sort_list_view(view_id, after)` | 将视图移到指定位置 |
| `reset_list_view_order(view_ids)` | 完全重排视图顺序 |
| **表格视图配置** | |
| `config_table_base(view_id, ...)` | 配置行高/自动刷新/列显隐/冻结列等基础设置 |
| `config_table_system_columns(view_id, show_fields)` | 配置系统字段显隐（default模式） |
| `config_table_sort(view_id, orders)` | 配置默认排序规则 |
| `config_table_quick_filter(view_id, query_list, ...)` | 配置快速筛选栏 |
| `config_table_left_filter(view_id, ...)` | 配置左侧分组筛选栏 |
| `config_view_data_filter(view_id, conditions, ...)` | 配置视图数据过滤条件 |
| **版本管理** | |
| `create_version(code, remarks)` | 创建表单版本快照 |
| `list_versions(code)` | 查看表单版本历史 |
| **字典工具** | |
| `query_dict(dict_code)` | 查询字典项列表 |
| `search_dict(keyword)` | 按名称/编码模糊搜索字典 |
| **菜单** | |
| `gen_menu_sql(parent_name, children, ...)` | 生成菜单和角色授权SQL |

---

## init_api / get_api_base

```python
init_api(api_base, token)
# 初始化 API 地址和 Token，所有操作前必须调用一次
# api_base: 后端地址，如 'https://boot3.jeecg.com/jeecgboot'
# token: X-Access-Token

get_api_base()  # 返回当前 API 基础地址
```

---

## check_code_available

```python
check_code_available(code) -> bool
# 校验表单编码是否可用（数据库级唯一性检查）
# True = 可用，False = 已存在
# 新建表单时必须在展示摘要前调用
```

---

## get_form_id

```python
get_form_id(code) -> (form_id, update_count) | (None, None)
# 通过表单编码获取 ID 和 updateCount（带缓存）
# 查找顺序：缓存 → queryByCode（带验证）→ list 全量搜索
```

---

## query_form

```python
query_form(code) -> dict | None
# 查询表单完整信息（带缓存）
# 返回字段：id, desformCode, desformName, updateCount, desformDesignJson 等
# 用于读取当前设计 JSON 或获取最新 updateCount
```

---

## get_form_fields

```python
get_form_fields(form_code) -> (title_field_model, fields_map)
# 查询已有表单所有字段信息
# 返回：
#   title_field_model: 标题字段的 model 字符串
#   fields_map: {字段名: {model, key, type, parent?}, ...}
#
# 字段中文名不唯一（设计子表列常与主表同名）。禁止按 name 覆盖：
#   主表：fields['数字']
#   子表列：fields['设计子表.数字']，并带 parent='设计子表'
#   仍冲突：key 追加 #{model}
#
# 示例：
title_field, fields = get_form_fields('my_form')
# fields['姓名'] == {'model': 'input_xxx', 'key': 'xxx', 'type': 'input'}
# fields['采购明细.数量'] == {'model': 'integer_xxx', 'key': '...', 'type': 'integer', 'parent': '采购明细'}
```

---

## create_form

```python
create_form(name, code, widgets, title_index=0, layout='auto',
            expand=None, config_overrides=None) -> (form_id, title_model)
# 一站式创建表单：查找/创建 → 保存设计 → 同步权限
#
# layout 参数：
#   'auto'  — 字段数 >= 6 时自动启用半行布局（默认）
#   'half'  — 强制半行布局
#   'full'  — 强制整行布局
#   'word'  — Word 风格带边框布局（需用户明确要求）
#
# config_overrides: dict，覆盖 config 任意字段
#   {"customRequestURL": [{"url": "https://..."}], "transactional": False}
#
# 示例：
create_form('员工信息', 'employee_info', [
    INPUT('姓名', required=True),
    PHONE('电话'),
    SELECT('部门', options=['研发', '销售', '运营']),
])
```

---

## update_form

```python
update_form(code, widgets, title_index=0, config_overrides=None) -> (form_id, title_model)
# 整体重设计已有表单：查询 → 保存设计 → 同步权限
# widgets: 全量新控件列表（替换，不是追加）
# config_overrides: 仅需覆盖 config 时使用；若只改 config 不改控件，优先用 update_design_config
```

### ⚠️ 批量修改组件属性：必须递归遍历（实测教训）

用 `update_form` 全量替换时，若需批量修改每个组件的属性（如 `hiddenOnAdd`/`hidden`/`disabled`），**必须递归遍历组件树**——组件可能嵌套在容器（card 的 `list[]`、tabs 的 panes 等）内部，只遍历顶层 `obj['list']` 会漏掉嵌套字段。

**实测案例（2026-08-13）**：表单"全组件校验"顶层 33 个组件中 31 个是 card 容器，真实字段（名称/数字/日期/自动编号等 29 个）全部嵌套在 card 的 `list[0]` 里。只遍历顶层设置 `hiddenOnAdd=true`，29 个嵌套字段全部遗漏，验证时也只看顶层同样发现不了；用户手工设置自动编号时才暴露。

**正确做法**：递归遍历所有含 `model` 的节点，修改后**验证也必须递归**（同样的 walk 检查所有嵌套组件），否则遗漏不可见：

```python
def walk(node):
    opts = node.get('options') or {}
    if isinstance(opts, dict):
        opts['hiddenOnAdd'] = True   # 目标修改
    for k, v in node.items():
        if isinstance(v, list):
            for child in v:
                if isinstance(child, dict) and 'model' in child:
                    walk(child)
        elif isinstance(v, dict):
            for v2 in v.values():
                if isinstance(v2, list):
                    for child in v2:
                        if isinstance(child, dict) and 'model' in child:
                            walk(child)

for w in widgets:
    walk(w)
```

### ⚠️ hiddenOnAdd 与 hidden 是独立开关

设置"新增时隐藏"只改 `options.hiddenOnAdd=true`。实测发现组件的 `options` 里可能同时存在 `hidden=true`（彻底隐藏）——用户只要求新增时隐藏时，必须**显式把 `hidden` 设为 `false`**，否则组件在所有场景都隐藏。验证标准：所有组件 `hiddenOnAdd=true` 且 `hidden=false`。

---

## update_design_config

```python
update_design_config(code, config_updates) -> dict
# 快捷更新表单 designConfig（不影响控件列表）
# 自动查询最新 config，深度合并后保存
#
# 合并规则：
#   dict 值 → 递归合并（只更新指定子字段）
#   list 值 → 整体替换
#   其他类型 → 直接覆盖
#
# 示例：
# 打印设置
update_design_config('my_form', {"allowPrint": True, "disabledAutoGrid": False})
#
# 填报通知
update_design_config('my_form', {
    "enableNotice": True,
    "noticeMode": "always",
    "noticeType": "system,email",
    "noticeReceiver": "admin,zhangsan"
})
#
# 只更新 dialogOptions.width，不影响其他子字段
update_design_config('my_form', {"dialogOptions": {"width": 800}})
#
# 外部链接
update_design_config('my_form', {
    "allowExternalLink": True,
    "externalTitle": "填报表单"
})
#
# 业务规则（数组整体替换，需传完整列表）
update_design_config('my_form', {"bizRuleConfig": [...]})
```

---

## copy_form

```python
copy_form(source_code, new_code=None) -> dict
# 复制已有表单设计为新表单
# new_code 不传时后台自动生成编码
# 适合基于现有表单快速创建相似表单
```

---

## delete_form

```python
delete_form(code_or_id, form_id=None)
# 删除表单（逻辑删除 → 物理删除）
# 支持 3 种调用方式：
delete_form('my_form')                    # 传 code，自动查找 ID
delete_form('my_form', '1234567890')      # 传 code + 已知 ID（最快）
delete_form('1234567890123456789')        # 纯数字且长度>15 判定为 ID
```

---

## add_widget / update_widget / delete_widget

```python
add_widget(code, widget_or_widgets)
# 向已有表单追加控件（单个或列表）
# widget: 大写工厂函数的返回值 (card_dict, key, model)

update_widget(code, changes_dict, *, key=None, model=None)
# 修改指定控件的属性，key 和 model 必须显式指定其一，优先传 key（用 model 定位有时会报"组件不存在"）
#
# ⚠️ 【强制】修改前先确认目标属性是否是组件选项（即 options 里的字段）。如果是，必须套
#   {"options": {...}}，否则会导致后端静默失败——字段被错误地设置到了顶层而不是 options 子层！
#
# changes_dict: {"name": "新名称", "options": {"required": True}}
# 示例：update_widget('my_form', {'options': {'required': True}}, key=fields['姓名']['key'])

delete_widget(code, *, key=None, model=None)
# 删除指定控件，key 和 model 必须显式指定其一，优先传 key
# 示例：delete_widget('my_form', key=fields['备注']['key'])
```

---

## export_design_json / save_design_from_file

```python
export_design_json(code, output_path=None) -> (file_path, field_rows)
# 导出当前表单设计 JSON 到文件，并打印字段参照表
# 用于：需要手动修改设计 JSON 的场景（预处理模式）
# field_rows: [{name, key, model, type}, ...]
#
# 示例：
file_path, field_rows = export_design_json('my_form')
# ... 用 Read/Edit 工具修改 file_path ...
save_design_from_file('my_form', file_path)

save_design_from_file(code, file_path) -> dict
# 从文件读取设计 JSON 并保存到后台
# 自动获取最新 updateCount，避免版本冲突
```

---

## extract_field_table_from_design

```python
extract_field_table_from_design(design_json) -> list[dict]
# 从设计 JSON 中提取字段参照表（不调用 API）
# 返回：[{name, key, model, type}, ...]
# 递归遍历 card/grid/tabs/sub-table-design 容器
```

---

## sync_auth / add_auth_batch / save_auth_from_design

```python
sync_auth(form_code, design_list, form_id=None)
# 同步字段权限（增删同步）：用于 update_form 后
# design_list: 顶层控件列表

add_auth_batch(form_code, design_list, form_id=None)
# 批量新建字段权限：用于 create_form 后
# design_list: 顶层控件列表

save_auth_from_design(form_code)
# 从表单现有设计重建权限，仅在权限自动创建失败时使用
```

---

## 列表视图

```python
add_list_view_table(code, name=None) -> view_id
# 创建表格列表视图
# 注意：创建表单时系统已自动生成默认表格视图，只有用户明确要求时才调用

add_list_view_board(code, group_field=None, title_field=None, name=None) -> view_id
# 创建看板视图（按字段值分列展示卡片）
# group_field: 分组字段 model，默认 'create_by'
# 分组字段限：单选/下拉/开关/人员/表字典/关联记录单条（必须非多选；不含部门、他表仅显示）

add_list_view_calendar(code, date_columns, title_field=None, name=None) -> view_id
# 创建日历视图
# date_columns: [{"begin_field": model, "end_field": model(可选),
#                 "tag": "标签≤5字", "field_type": "date"/"datetime"}, ...]

config_calendar_columns(view_id, date_columns) -> dict
# 改已有日历的开始/结束日期组（整表替换 calendarColumnList）
# date_columns 格式与 add_list_view_calendar 相同；填字段 model

add_list_view_gantt(code, start_field, end_field, field_type='date',
                    default_view='day', title_field=None, name=None) -> view_id
# 创建甘特图视图（start_field 和 end_field 必须不同）

query_list_views(code) -> list[dict]
# 查询表单下所有列表视图（id, name, type, seq）

query_list_view_by_id(view_id) -> dict
# 查询视图完整配置

delete_list_view(view_id) -> dict
# 删除列表视图

sort_list_view(view_id, after)
# 将视图移到 after 视图之后；after='first' 移到最前

reset_list_view_order(view_ids)
# 按传入顺序完全重排序，view_ids 即最终排列顺序
```

---

## 表格视图配置

```python
config_table_base(view_id, line_height=None, auto_refresh=None, has_summary=None,
                  auto_submit_bpm=None, show_column=None, fixed_column_num=None,
                  column_list=None, show_column_list=None)
# 配置表格视图基础设置
# line_height: 'small'(紧凑) | 'middle'(中等) | 'large'(高)
# auto_refresh: 自动刷新秒数，0=关闭，最小 3
# has_summary: bool，开启数据统计
# show_column: 'default'(与表单字段一致) | 'diy'(自定义列)
# fixed_column_num: 冻结前 N 列
# column_list: [{"field": "字段key", "show": True/False, "seq": 0}, ...]
# show_column_list: 可见性覆盖，优先级高于 column_list

config_table_system_columns(view_id, show_fields)
# 配置系统字段显隐（仅 show_column='default' 模式有效）
# show_fields: 从 ['create_time','create_by','update_time','update_by','sys_org_code','bpm_status'] 中选
# 未列出的字段将被隐藏

config_table_sort(view_id, orders)
# 配置默认排序（表格/看板/日历/甘特图通用）
# orders: [{"field": "字段model", "type": "asc"/"desc"}, ...]
# 升降序键是 type，不是 order。清空：orders=[]

config_table_quick_filter(view_id, query_list, query_button=True, wait_query=False)
# 配置快速筛选栏
# query_list: [{"field": model, "name": 显示名, "type": 控件类型,
#               "query_type": 查询方式, "seq": 0}, ...]

config_table_left_filter(view_id, left_filter_field=None, left_filter_data='all',
                         left_filter_order='desc', left_filter_condition=None,
                         add_form_default_status=True)
# 配置左侧分组筛选栏
# left_filter_data: 'all' | 'part' | 'exist'

config_view_data_filter(view_id, conditions, match_type='and')
# 配置视图数据过滤（限制此视图只显示满足条件的记录）
# 支持所有视图类型（表格/看板/日历/甘特图）
# conditions 格式见函数 docstring
# 清除过滤：config_view_data_filter(view_id, [])
```

---

## 版本管理

```python
create_version(code, remarks='')
# 为表单创建版本快照

list_versions(code, page=1, size=10) -> list
# 列出表单版本历史
```

---

## 字典工具

```python
query_dict(dict_code) -> list[dict]
# 查询字典项列表，返回 [{value, text}, ...]

search_dict(keyword) -> list[dict]
# 按名称或编码模糊搜索字典
```

---

## gen_menu_sql

```python
gen_menu_sql(parent_name, children, role_id=None, icon='ant-design:appstore-outlined') -> str
# 生成菜单和角色授权 SQL
# children: [(菜单名, form_code, seq), ...]
#
# 示例：
sql = gen_menu_sql('CRM系统', [
    ('客户信息', 'customer_info', 1),
    ('联系人', 'contact_info', 2),
])
print(sql)
# 当 api_base 以 http://127.0.0.1 或 http://localhost 开头时，自动通过 MySQL CLI 执行
```

---

## 控件工厂函数（大写命名）

所有大写工厂函数返回 `(card_dict, key, model)` 三元组，直接传入 `create_form` / `update_form` 的 widgets 列表。

| 分类 | 函数 |
|------|------|
| 基础输入 | `INPUT` `TEXTAREA` `NUMBER` `INTEGER` `MONEY` `DATE` `TIME` `SWITCH` `SLIDER` `RATE` `COLOR` |
| 选择 | `RADIO` `SELECT` `CHECKBOX`（支持 `dict_code`） |
| 系统 | `USER` `DEPART` `DEPART_POST` `ORG_ROLE` `PHONE` `EMAIL` `AREA` |
| 高级选择 | `TABLE_DICT` `SELECT_TREE` |
| 文件 | `FILE` `IMGUPLOAD` `HANDSIGN` |
| 计算 | `AUTONUMBER` `FORMULA` `SUMMARY` `CAPITAL_MONEY` `TEXT_COMPOSE` |
| 关联 | `LINK_RECORD` `LINK_FIELD` |
| 展示 | `BARCODE` `LOCATION` `MAP` `OCR` `TEXT` `BUTTONS` |
| 不需 card | `DIVIDER` `EDITOR` `MARKDOWN` `TABS` |
| 布局容器 | `GRID` `CARD` |
| 子表内 | `SUB_INPUT` `SUB_TEXTAREA` `SUB_INTEGER` `SUB_NUMBER` `SUB_MONEY` `SUB_DATE` `SUB_TIME` `SUB_SWITCH` `SUB_SLIDER` `SUB_RATE` `SUB_COLOR` `SUB_SELECT` `SUB_RADIO` `SUB_CHECKBOX` `SUB_USER` `SUB_DEPART` `SUB_DEPART_POST` `SUB_PHONE` `SUB_EMAIL` `SUB_AREA` `SUB_IMGUPLOAD` `SUB_FILE` `SUB_ORG_ROLE` `SUB_LINK_RECORD` `SUB_LINK_FIELD` `SUB_FORMULA` `SUB_PRODUCT` `SUB_CAPITAL_MONEY` `SUB_TEXT_COMPOSE` |

**重要**：子控件用于 `create_form`/`update_form` 的 `wrap=False` 场景（放入 `CARD`/`GRID` 容器时），以及 `make_sub_table` 的列定义。

> ⚠️ **2026-09-15 实测：`FORMULA` 第二位置参数是 `mode` 不是表达式——表达式必须 `expression=` 关键字传参。** `FORMULA('实发工资', '$m1$+$m2$')` 会把表达式塞进 `options.mode`，加 `mode='CUSTOM'` 一起传则抛 `got multiple values for argument 'mode'`；更坑的是只传两个位置参数时**静默保存成功**（`options.expression` 为空、接口不报错），且事后补正确公式若按 card 一层子节点查重会漏掉它（坏控件实际嵌在 `card/list[0]/list[0]` 三层），造成同名公式双胞胎。正确：`FORMULA('实发工资', expression='$m1$+$m2$', mode='CUSTOM')[0]`。查重/去重必须**递归遍历整个设计 JSON** 按 `type=='formula' and options.expression 非空` 判定，禁止只查 card 直接子节点。

> ⚠️ **2026-09-15 实测：`SUB_*` 子表列工厂必须传 `parent_key`（= 目标 `sub-table-design` 控件的 `key`），缺了抛 `missing 1 required positional argument: 'parent_key'`。** 正确：`pk = sub['key']` 后 `SUB_INPUT('工作内容', pk)`、`SUB_SELECT('是否交接', pk, ['已交接', '未交接'])`、`SUB_USER('工作交接人', pk)`。报错即修、不产生脏数据，但会让整表补丁失败重跑。另：job 建的空壳 `sub-table-design` 本身带 `[{"list":[]}]` 列结构——判「要不要加列」必须看列内 `list` 是否有控件（`any(c['list'] for c in sub['columns'])`），用 `columns` 是否为空判定会误判为「已有列」静默跳过。

> ⚠️ **2026-09-14 实测：手工整单补丁（query_form → 改 design['list'] → `save_design_from_file`）时，所有工厂返回值都要取 `[0]`**（`FORMULA`/`AUTONUMBER`/`LINK_FIELD`/`make_sub_table` 均是 `(x, key, model)` 三元组）。尤其 `make_sub_table` 的 `columns[].list` 内是**未解包的子三元组**，插已有表必须二次解包，否则落库后子表列变 JSON 数组、保存照报成功、之后 query NPE 整表查不出（修复配方见 `desform-sub-table-types.md`「Python 用法」末尾警告）。**补丁脚本必须按"必然重跑"设计**：每表一个幂等标记（如 `'工号' not in wmap`）跳过已完成表——**没有标记的重跑会把 link-field/子表等新增控件重复叠加**（实测带出字段叠出 4 套同名字段，且全部保存成功无报错，只能在设计器里看出来）；`save_design_from_file` 之后立即 `query_form` 回读验证再进下一张表。

---

## 在指定位置插入字段

`add_widget()` 只能追加到末尾。需要在特定位置插入时：

```python
import json
from desform_utils import init_api, query_form, update_form, EMAIL

init_api(BASE_URL, TOKEN)

# 1. 获取现有设计
form = query_form('my_form')
design = json.loads(form['desformDesignJson'])
widgets = design['list']   # 顶层 widget（card）列表

# 2. 定位目标索引（字段名在 card 子控件的 name 上，不在 card 自身）
insert_idx = None
for i, card in enumerate(widgets):
    for child in card.get('list', []):
        if child.get('name') == '手机号':
            insert_idx = i
            break
    if insert_idx is not None:
        break

# 3. 构造新控件并插入（解包三元组，取第一个元素）
email_card, _, _ = EMAIL('邮箱')
widgets.insert(insert_idx, email_card)

# 4. 保存（自动重建 hasWidgets 并同步权限）
update_form('my_form', widgets)
```

---

## 通用 kw 参数

所有大写工厂函数支持 `**kw`：

```python
# mobile_options — 移动端覆盖配置（合并到 mobileOptions 顶层属性）
RADIO('性别', ['男', '女'], mobile_options={"inline": True, "matrixWidth": 120})
DATE('日期', mobile_options={"editable": False})

# wrap=False — 不包裹 card，用于放入 CARD/GRID 容器
input_w, _, _ = INPUT('姓名', wrap=False)
phone_w, _, _ = PHONE('手机', wrap=False)
card_w, card_k, card_m = CARD(input_w, phone_w, row_num=2)
```

---

## 重要限制

1. **Windows 环境禁止 `python -c "..."` 内联执行**（中文/引号会被 bash 解析破坏），必须先 Write 临时 `.py` 文件再执行
2. 中文输出乱码：`from desform_utils import *` 后自动修复，`python -c` 内联需手动加 `sys.stdout.reconfigure(encoding='utf-8')`
