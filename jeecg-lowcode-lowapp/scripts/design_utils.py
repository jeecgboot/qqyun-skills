# -*- coding: utf-8 -*-
"""表单设计 / 看板组件 / 应用菜单的**统一解析层**（全链路共用，不绑任何具体应用）。

## 为什么要单独一层

同一段「递归所有控件」原本在 `patch_fields.iter_widgets`、`regroup_layout.iter_widgets`
和临时脚本里**各写了一份**，三份对「card 的子控件放在哪」的假设并不一致：

**2026-09-20 实测**：一份只走 `columns` 的遍历器，在一个真实应用（47 张表，card 把子控件
放在 **`list`**）上**一个控件都找不到** —— 而它不报错，只是静默返回空，
表现是「补丁全部跳过 / 一张表都没改」，接口全绿。三份实现各自漂移就是这个形态。

所以：**任何遍历表单设计的代码都必须走本模块的 `iter_widgets`**，不要再自己写一份。

## 落库形态（实测）

```
design = {"list": [widget, ...], "config": {...}}
  card      → 子控件在 .list（**不是 columns**；columns 是另一种历史形态，两种都要走）
  tabs      → 子控件在 .panes[i].list；⚠️ **不要 yield pane 本身**
              （页签的 name 就是页签名，常与字段同名，吐出去会让 find_widget 抓错）
  其他控件  → 叶子，无子节点

看板 template = [comp, ...]，组件取「显示名」的位置**因组件而异**：
  JText          → config.chartData（**字符串**，不是对象）
  JCustomButton  → config.chartData[0].title
  JFilterQuery   → 固定 '查询条件'
  统计图/透视表  → config.option.title.text（⚠️ **顶层 card.title 是空的**）
"""
from __future__ import annotations

__all__ = [
    "iter_widgets", "find_widget", "widget_index", "field_names",
    "form_codes", "menu_index", "init_pages", "page_template", "page_key",
    "is_saved_field",
]

#: 他表字段（link-field）只有 `saveType == 'save'` 才**落库**；`view` 仅显示，
#: 流程 `cond` / `ref()` 取到的是空值（engine-contract「明细表要带哪些键」）。
SAVE_TYPES = ("save",)


# ---------------- 表单设计 ----------------

def iter_widgets(node):
    """递归吐出设计树里的**每一个控件**（含 card.list、columns、tabs.panes）。

    传 dict（design 或任一节点）或 list（`design['list']`）都行。

    ⚠️ 只走 `list` 或只走 `columns` 都是错的：两种形态在不同环境下都出现过，
       漏一种就是**静默少半张表的控件**。
    ⚠️ **不要 yield pane 本身**：页签名常与字段同名。
    """
    if isinstance(node, dict):
        items = node.get('list') or []
        cols = node.get('columns') or []
        panes = node.get('panes') or []
    else:
        items, cols, panes = (node or []), [], []
    for w in items:
        if not isinstance(w, dict):
            continue
        yield w
        for x in iter_widgets(w):
            yield x
        for p in (w.get('panes') or []):
            if isinstance(p, dict):
                for x in iter_widgets(p.get('list') or []):
                    yield x
    for c in cols:
        if isinstance(c, dict):
            for x in iter_widgets(c):
                yield x
    for p in panes:
        if isinstance(p, dict):
            for x in iter_widgets(p.get('list') or []):
                yield x


def find_widget(design, name, wtype=None):
    """按控件中文名找控件；`wtype` 给了就同时校验 type。找不到返回 None。"""
    hit = None
    for w in iter_widgets(design):
        if w.get('name') == name and (wtype is None or w.get('type') == wtype):
            if w.get('type') != 'divider':          # 同名分隔符只在没有别的同名控件时才算命中
                return w
            hit = hit or w
    return hit


def widget_index(design):
    """`{控件中文名: 控件}`。重名时**保留第一个**（与设计器显示顺序一致），
    但同名分隔符让位给真控件（分节标题常与首字段同名，2026-09-22 三个应用的审计都被它假报）。"""
    out = {}
    for w in iter_widgets(design):
        n = w.get('name')
        if not n:
            continue
        if n not in out or (out[n].get('type') == 'divider' and w.get('type') != 'divider'):
            out[n] = w
    return out


def field_names(design):
    return set(widget_index(design))


def is_saved_field(w):
    """该控件是否会**落库**。

    叶子控件恒落库；`link-field`（他表字段）要看 `options.saveType` ——
    规格里「带出」建出来的默认就是 `save`，只显示的是 `view`。
    流程 `cond`/`ref()` 命中一个 `view` 字段时取到空值（**不报错**）。
    """
    if not isinstance(w, dict):
        return False
    if w.get('type') != 'link-field':
        return True
    return (w.get('options') or {}).get('saveType') in SAVE_TYPES


# ---------------- 应用菜单 / 表单编码 ----------------

def form_codes(api_base, token, tenant_id, app_id):
    """一次调用拿全 `({表名: code}, {code: 表名})`。

    用 `/online/lowApp/miniflow/tenantAppFormList?tenantId=` —— 它**按租户**返回全部应用，
    所以要按 `app_id` 过滤。逐个 `get_form_id` 会多花 2×N 次 HTTP。
    """
    from desform_utils import api_request
    r = api_request('/online/lowApp/miniflow/tenantAppFormList?tenantId=%s' % tenant_id,
                    method='GET')
    by_name, by_code = {}, {}
    for ap in (r.get('result') or {}).get('apps') or []:
        if str(ap.get('id')) != str(app_id):
            continue
        for f in ap.get('desforms') or []:
            if f.get('name') and f.get('code'):
                by_name[f['name']] = f['code']
                by_code[f['code']] = f['name']
    return by_name, by_code


def menu_index(app_id):
    """`{分组名: id}` / `{表单名: id}` / `{看板名: pageId}` / `{表单名: menuUrl}`。

    ⚠️ 看板的 **pageId 在 `menuUrl` 列**，不是 `menuId`（抓错列会让「按名找盘」全落空，
       而删除/定位类脚本会**静默不生效**）。
    """
    from desform_lowapp_utils import get_menus
    ml = (get_menus(app_id) or {}).get('menuList') or []
    groups, forms, pages = {}, {}, {}
    for m in ml:
        t, nm = m.get('type'), m.get('menuName')
        if t == 'group':
            groups[nm] = m.get('id')
        elif t == 'form':
            forms[nm] = m.get('id')
        elif t == 'drag':
            pages.setdefault(nm, m.get('menuUrl'))
    return {'groups': groups, 'forms': forms, 'pages': pages, 'raw': ml}


def init_pages(api_base, token):
    """看板侧**另一套连接**：`bi_utils` 有自己的 api base / token，不 init 会拼出
    `/drag/page/queryById?...` 这种**没有 host 的 URL**，报 `unknown url type`。

    调用链上两套连接各管一摊：`desform_utils`（表单）与 `bi_utils`（看板）。
    只 init 了表单那侧、再调 `page_template()` 就是踩这一条（2026-09-21 实测）。
    任何**同时**要读表单和看板的脚本（`app_audit.py` 就是）都必须两边都 init。

    `bi_utils` 在**另一个 skill** 的目录下（`jeecg-lowcode-dashboard/references/scripts`），
    调用方通常没把它放进 sys.path —— 这里自己兜住，省得每个脚本各写一遍。
    """
    import os
    import sys
    if not _bi_utils_importable():
        for p in (os.path.expanduser(
                      '~/.claude/skills/jeecg-lowcode-dashboard/references'),
                  os.path.expanduser(
                      '~/.claude/skills/jeecg-lowcode-dashboard/references/scripts'),
                  os.path.expanduser('~/.claude/skills/jeecg-lowcode-dashboard/scripts')):
            if os.path.isdir(p) and p not in sys.path:
                sys.path.insert(0, p)
                if _bi_utils_importable():
                    break
    import bi_utils
    init = getattr(bi_utils, 'init_api', None)
    if init:
        init(api_base, token)
        return True
    return False


def _bi_utils_importable():
    import importlib.util
    try:
        return importlib.util.find_spec('bi_utils') is not None
    except (ImportError, ValueError):
        return False


def page_template(page_id):
    """`(components, updateCount)`；`template` 是 JSON **字符串**时自动解析。

    回写必须把 components 放回 `bi_utils._page_components[page_id]` 再 `save_page(page_id)`。
    """
    import bi_utils
    page = bi_utils.query_page(page_id)
    tmpl = page.get('template') or []
    if isinstance(tmpl, str):
        import json
        tmpl = json.loads(tmpl)
    return tmpl, page.get('updateCount')


def page_key(comp):
    """组件的「显示名」——看板规格里按它认领组件。

    ⚠️ 统计图的标题**不在顶层 `card.title`**（那里恒为空），
       在 `config.option.title.text`；文本组件在 `config.chartData`（字符串）。
       按 `card.title` 匹配图表 = 一个都匹配不上（2026-09-20 实测）。
    """
    if not isinstance(comp, dict):
        return None
    c = comp.get('component')
    cfg = comp.get('config') or {}
    if c == 'JText':
        v = cfg.get('chartData')
        return v.get('value') if isinstance(v, dict) else v
    if c == 'JCustomButton':
        cd = cfg.get('chartData') or []
        return (cd[0] or {}).get('title') if cd else None
    if c == 'JFilterQuery':
        return (cfg.get('option') or {}).get('title') or '查询条件'
    opt = (cfg.get('option') or {})
    t = ((opt.get('title') or {}).get('text') if isinstance(opt.get('title'), dict)
         else None)
    return t or ((cfg.get('card') or {}).get('title') or
                 (comp.get('card') or {}).get('title'))
