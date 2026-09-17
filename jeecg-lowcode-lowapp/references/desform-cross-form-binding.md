# 多表单互相关联（跨表关联记录）实战指南

> 本文档总结了创建多个互相关联表单的最佳实践、常见陷阱和正确写法。
> 场景：多个表单之间通过关联记录（link-record）、工作表子表（isSubTable）、他表字段（link-field）互相引用。

## 一、核心策略：先建表，后关联

跨表关联的核心困难是 **循环依赖**：A 关联 B，B 也关联 A，但创建 A 时 B 还不存在（或 B 的 titleField 未知）。

**正确做法：分两阶段，但写进同一条 `.py` 一次跑完**（不要每阶段一轮对话）。互不依赖的基础表 **并行** 创建。

```
阶段1：并行 desform_creator.py 创建所有基础表单（不含 link-record；不要默认 --force）
阶段2：用 add_widget() 添加关联记录
阶段3（一对一/双向）：用 update_widget() 设置 twoWayModel
```

**错误做法：**
- ❌ 在 JSON 配置中直接写 link-record 的 titleField（此时目标表单可能还未创建，或已被 --force 重建导致 model 变化）
- ❌ 在 update_form() 中混合基础字段和 link-record（update_form 会重建所有 model，破坏已有引用）

---

## 二、阶段1：创建基础表单

使用 JSON 配置 + `desform_creator.py`，每个表单只包含自身字段（无 link-record）。**并行创建**，不要依次等：

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
# 每个 cfg 走 subprocess：desform_creator.py --tenant-id --app-id --config -
# stdin 传 json.dumps(cfg).encode('utf-8')
with ThreadPoolExecutor(max_workers=len(cfgs)) as ex:
    futs = [ex.submit(create_one, cfg) for cfg in cfgs]
    for f in as_completed(futs):
        f.result()
```

只有用户明确要求覆盖已有表时才加 `--force`。

> **内部子表（sub-table-design）可以放在 JSON 配置中**，desform_creator.py 会自动处理 parent_key。

---

## 三、阶段2：查询字段 + 添加关联记录

### 3.1 查询所有表单的字段信息

```python
import sys
sys.path.insert(0, r'<skill>/scripts')
from desform_utils import *

init_api(API_BASE, TOKEN)

title_a, fields_a = get_form_fields('form_a_code')
title_b, fields_b = get_form_fields('form_b_code')
title_c, fields_c = get_form_fields('form_c_code')
```

### 3.2 用 add_widget 添加关联记录

**关键：LINK_RECORD() 返回元组 `(widgets_list, key, model)`，传给 add_widget 时只传 `widgets_list`（第一个元素）。**

```python
# ✅ 正确写法
ws, k, m = LINK_RECORD('关联表B', 'form_b_code', title_b,
                        show_fields=[fields_b['某字段']['model']],
                        show_mode='many', show_type='card')
add_widget('form_a_code', ws)   # 传 ws（list），不是整个元组

# ❌ 错误写法（会报 JSON parse error）
lr = LINK_RECORD('关联表B', 'form_b_code', title_b, ...)
add_widget('form_a_code', lr)   # 传了元组 (list, key, model)，API 无法序列化
```

### 3.3 各种关联模式的写法

#### 普通关联记录（单条/卡片）
```python
ws, k, m = LINK_RECORD('所属项目', 'project_code', proj_title,
                        show_fields=[proj_fields['状态']['model']],
                        show_mode='single', show_type='card')
add_widget('task_code', ws)
```

#### 普通关联记录（多条/下拉）
```python
ws, k, m = LINK_RECORD('参与成员', 'member_code', mem_title,
                        show_fields=[mem_fields['职位']['model']],
                        show_mode='many', show_type='select')
add_widget('task_code', ws)
```

#### 工作表子表（isSubTable=true，表格模式）
```python
ws, k, m = LINK_RECORD('子任务列表', 'task_code', task_title,
                        show_fields=[...],
                        show_mode='many', show_type='table')
# 必须手动设置 isSubTable
for w in ws:
    if isinstance(w, dict) and w.get('type') == 'link-record':
        w['isSubTable'] = True
add_widget('project_code', ws)
```

#### 他表字段（link-field）
```python
# 需要先拿到对应 link-record 的 key（创建时返回的 k）
ws, k_proj, m = LINK_RECORD('所属项目', 'project_code', proj_title, ...)
add_widget('task_code', ws)

# link-field 引用上面 link-record 的 key
ws_lf, _, _ = LINK_FIELD('项目名称(引用)', k_proj,
                          proj_fields['项目名称']['model'],
                          field_type='input')
add_widget('task_code', ws_lf)
```

---

## 四、阶段3：设置双向关联 twoWayModel

**关键：update_widget 必须用 `key=` 关键字参数定位控件，不能用 `model=`。**

```python
# 重新获取最新字段
_, pf = get_form_fields('project_code')
_, tf = get_form_fields('task_code')

# ✅ 正确：用 key= 关键字参数定位控件
update_widget('project_code', {'options': {'twoWayModel': tf['所属项目']['model']}},
              key=pf['项目任务']['key'])
update_widget('task_code', {'options': {'twoWayModel': pf['项目任务']['model']}},
              key=tf['所属项目']['key'])

# ❌ 错误：用 model= 定位（报"组件不存在"）
update_widget('project_code', {'options': {'twoWayModel': tf['所属项目']['model']}},
              model=pf['项目任务']['model'])
```

> 注意：twoWayModel 的 **值** 填的是对方 link-record 的 **model**（不是 key），
> 但 update_widget **定位控件** 用的是 `key=`。

---

## 五、踩坑汇总

| 陷阱 | 现象 | 正确做法 |
|------|------|----------|
| add_widget 传入整个 LINK_RECORD 返回值 | `JSON parse error: Cannot deserialize` | 只传 `ws`（元组第一个元素） |
| LINK_FIELD 传 `save_type` 参数 | `TypeError: unexpected keyword argument` | 创建后手动修改 `w['options']['saveType']` |
| SUB_* 函数传 `parent_key=None` | `KeyError: 'subOptions'` | 不要在 Python 中手动调 SUB_*，用 JSON 配置的 sub-table-design |
| update_widget 用 model= 定位控件 | `组件不存在，无法操作` | 用 `key=` 定位（`key=fields['字段名']['key']`） |
| update_form 重建含关联的表单 | 所有 model 重新生成，破坏其他表的引用 | 用 add_widget 增量添加关联，不要用 update_form |
| JSON 配置中写 link-record 的 titleField | 目标表重建后 model 变化，引用失效 | 用阶段 2 的 Python 方式动态获取 |

---

## 六、完整实战模板（3 表互联）

以下模板可直接复用，创建 N 个互相关联的表单：

```python
import sys
sys.path.insert(0, r'<skill>/scripts')
from desform_utils import *

init_api(API_BASE, TOKEN)

# ========== 阶段 2：查询字段 ==========
title_a, fa = get_form_fields('form_a')
title_b, fb = get_form_fields('form_b')
title_c, fc = get_form_fields('form_c')

# ========== 阶段 2：添加关联记录 ==========

# A → B（关联记录/多条/卡片）
ws, _, _ = LINK_RECORD('关联B', 'form_b', title_b,
                        show_fields=[fb['字段X']['model']],
                        show_mode='many', show_type='card')
add_widget('form_a', ws)

# A → C（工作表子表）
ws, _, _ = LINK_RECORD('子表C', 'form_c', title_c,
                        show_fields=[fc['字段Y']['model']],
                        show_mode='many', show_type='table')
for w in ws:
    if isinstance(w, dict) and w.get('type') == 'link-record':
        w['isSubTable'] = True
add_widget('form_a', ws)

# B → A（关联记录/单条/卡片）+ 他表字段
ws, k_a, _ = LINK_RECORD('所属A', 'form_a', title_a,
                           show_mode='single', show_type='card')
add_widget('form_b', ws)
ws_lf, _, _ = LINK_FIELD('A的名称', k_a, fa['名称']['model'], field_type='input')
add_widget('form_b', ws_lf)

# B → C（关联记录/多条/下拉）
ws, _, _ = LINK_RECORD('关联C', 'form_c', title_c,
                        show_mode='many', show_type='select')
add_widget('form_b', ws)

# C → A, C → B ...（同理）

# ========== 阶段 3：双向关联 ==========
_, fa2 = get_form_fields('form_a')
_, fb2 = get_form_fields('form_b')

update_widget('form_a', {'options': {'twoWayModel': fc2['所属A']['model']}},
              key=fa2['子表C']['key'])
update_widget('form_c', {'options': {'twoWayModel': fa2['子表C']['model']}},
              key=fc2['所属A']['key'])
# ... 其他双向对同理
```

---

## 七、LINK_FIELD saveType 修改方法

LINK_FIELD 默认 saveType='view'（动态展示，不保存），如需改为 'save'（保存快照）：

```python
ws_lf, _, _ = LINK_FIELD('项目名称', k_proj, proj_fields['项目名称']['model'],
                          field_type='input')

# 方法 1：创建后手动遍历修改（适用于 add_widget 前）
for w in ws_lf:
    if isinstance(w, dict) and w.get('type') == 'link-field':
        w['options']['saveType'] = 'save'
add_widget('task_code', ws_lf)

# 方法 2：add_widget 后用 update_widget 修改
add_widget('task_code', ws_lf)
_, tf = get_form_fields('task_code')
update_widget('task_code', {'options': {'saveType': 'save'}},
              key=tf['项目名称']['key'])
```

> **注意：** `ws_lf` 中的元素可能是 dict（控件本身）或被 card 包裹后的嵌套结构，
> 遍历时务必用 `isinstance(w, dict) and w.get('type') == 'link-field'` 精确匹配。
