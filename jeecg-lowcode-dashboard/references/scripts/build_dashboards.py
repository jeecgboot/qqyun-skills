# -*- coding: utf-8 -*-
"""批量建仪表盘 —— 读一个声明式 dashboards.json，单进程建完全部盘。

    python build_dashboards.py --api-base URL --token TOKEN \
        --tenant-name 租户名 --app-name 应用名 --spec dashboards.json \
        [--only 盘1,盘2] [--recreate 盘3] [--dry-run]

dashboards.json：

    {"pages": [
      {"name": "客户分析", "group": "客户管理",
       "charts": { "客户": [
           {"comp":"JBar","title":"客户分析","dim":"客户名称","val":"record_count","w":24,"h":32}
       ]},
       "ui":      [{"comp":"JText","text":"正文","style":"大标题,加粗,居中,整行"}],
       "buttons": {"buttons":[...]},
       "filters": [{"title":"查询条件","charts":["客户分析"],
                    "conditions":[{"field":"客户来源","mode":"包含"}]}]
      }
    ]}

`charts` 的键是**表单 code 或表单名**——同一张盘要跨几张表就写几个键，引擎按表分别 add-charts。

> ⚠️ **优先写表单 code。** `--form-name` 走应用内表单解析，而 `forms` 在
> 「`desform.lowAppId` 与应用 ID 不一致」的环境会退化成菜单兜底、漏表（2026-09-15 实测：
> 一个 52 表的应用里 `--form-name 客户` 直接解析失败，`--form-code app_customer` 秒过）。
> 引擎按「是否含中文」自动选 `--form-code` / `--form-name`，报错时改用 code 重跑。

## 为什么要有这个脚本（2026-09-15 实测）

手搓一个 `build_dash.py` 编排 25 张盘，跑了 **42 分钟**且没建好，四个叠加原因：

1. **每个操作 `subprocess.run` 起新 Python 进程** —— ~125 次进程启动，纯开销。
   本脚本把 `qqy_ops.py` 的 CLI **在同一进程内**跑完（`sys.argv` + 重定向 stdout）。
2. **删除正则抓错列** —— `menus` 列序是 `id/type/menuName/parentId/menuUrl`，
   名称后那一列是 **parentId（分组 id）**，不是 pageId。对 drag 菜单 **`menuUrl` 才是 pageId**。
   抓错列 → `delete-page` 从未生效 → **每次重跑净增 25 个盘**（实测攒到 58 个）。
   本脚本一律用 `menuUrl` 列，且**不删盘**。
3. **破坏性重建** —— delete→create 让每次重跑都从零开始，调试循环 = 反复重建全部。
   本脚本**默认非破坏**：盘已存在就跳过（可断点续跑），`--recreate` 才显式重建。
4. 叠加**并发跑设计任务**：那次测量期间后端还崩过一次，所以「并发锁竞争」只是推测；
   但两个进程同时建盘会互相叠加负载是确定的（见 pitfalls-core.md）。

输出纪律：只打 `OK:` / `FAIL:` 摘要行。
"""
import argparse
import contextlib
import io
import json
import os
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.dirname(HERE)
for _d in (HERE, REFS):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import qqy_ops as Q  # noqa: E402


def log(*a):
    print(*a, flush=True)


# ---------------- 单进程跑 qqy_ops 子命令 ----------------

def run_cli(argv, quiet=True):
    """在原进程内执行 qqy_ops 子命令，返回 (rc, stdout)。
    比 subprocess 省掉每次 ~0.5–1.5s 的解释器启动与 import。"""
    buf = io.StringIO()
    old = sys.argv
    sys.argv = ["qqy_ops.py"] + [str(a) for a in argv]
    try:
        with contextlib.redirect_stdout(buf):
            Q.main()
        return 0, buf.getvalue()
    except SystemExit as e:
        return (e.code if isinstance(e.code, int) else 1), buf.getvalue()
    except Exception as e:                                    # noqa: BLE001
        return 1, buf.getvalue() + "\nEXC:%s: %s" % (type(e).__name__, e)
    finally:
        sys.argv = old


AUTH = None      # [api_base, token, tenant_id, app_id]


def cli(*args, **flags):
    """拼出带认证前缀的子命令 argv: <cmd> <api> <token> --tenant-id .. --app-id .."""
    argv = [args[0], AUTH[0], AUTH[1], "--tenant-id", AUTH[2]]
    if AUTH[3]:
        argv += ["--app-id", AUTH[3]]
    for k, v in flags.items():
        if v is None or v == "":
            continue
        argv += ["--" + k.replace("_", "-"), str(v)]
    argv += [a for a in args[1:]]
    return argv


# ---------------- 菜单索引（pageId 取 menuUrl 列） ----------------

def index_menus(app_id):
    """返回 (pages{名→pageId}, groups{组名→id}, drag_rows[])。

    ⚠️ drag 菜单的 pageId 在 **menuUrl** 列；名称后那一列是 parentId（分组 id），别抓错。
    """
    rc, out = run_cli(["menus", AUTH[0], AUTH[1], "--tenant-id", AUTH[2], "--app-id", app_id])
    pages, groups, rows = {}, {}, []
    for line in out.splitlines():
        p = line.split("\t")
        if len(p) < 5 or p[0] == "id":
            continue
        mid, typ, name, parent, url = p[0], p[1], p[2], p[3], p[4]
        rows.append({"id": mid, "type": typ, "name": name, "parent": parent, "url": url})
        if typ == "group":
            groups[name] = mid
        elif typ == "drag":
            pages.setdefault(name, []).append(url)     # url == pageId
    return pages, groups, rows


# ---------------- 建一张盘 ----------------

def _validate_page(page):
    """建之前的规格预校验（失败就整张盘不建，别留半成品）。"""
    errs = []
    flts = page.get("filters") or []
    if len(flts) > 1:
        # `add-filter` 要求同一面板里的图来自同一张表，所以跨表就会生成多个面板 ——
        # 盘上出现两组一模一样的「查询/重置」，使用者分不清哪个管哪块
        #（2026-09-22 进销存 R5 用户报障：采购订单看板 / 财务收支看板各两个面板）。
        # 这是「一张盘塞了两个主题」的信号，正确做法是拆盘，而不是并排两个面板。
        errs.append("盘「%s」声明了 %d 个查询面板（%s）—— 一张盘只允许一个。"
                    "多个面板来自图跨了多张表；请**按主题拆成多张盘**（每盘一张主表 + 一个面板），"
                    "或只保留主表那一个筛选"
                    % (page["name"], len(flts),
                       "、".join(str(f.get("title") or "?") for f in flts)))
    return errs


def build_page(page, workdir, dry_run=False):
    name = page["name"]
    group = page.get("group", "")
    errs = _validate_page(page)
    if errs:
        return None, errs

    rc, out = run_cli(cli("create-page", "--name", name, "--group", group))
    m = None
    for line in out.splitlines():
        if line.startswith("PAGE_ID="):
            m = line.split("=", 1)[1].strip()
    if not m:
        return None, ["create-page: %s" % out.strip()[-200:]]
    page_id = m
    if dry_run:
        return page_id, errs

    # 按表分别加图
    for form, specs in (page.get("charts") or {}).items():
        p = os.path.join(workdir, "specs_%s_%s.json" % (abs(hash(name)) % 100000, abs(hash(form)) % 100000))
        with open(p, "w", encoding="utf-8") as f:                 # 无 BOM；add-charts 收裸数组
            json.dump(specs, f, ensure_ascii=False, indent=1)
        flag = "--form-code" if _looks_like_code(form) else "--form-name"
        rc, out = run_cli(cli("add-charts", "--page-id", page_id, flag, form, "--specs-file", p))
        if "ADDED=" not in out:
            errs.append("charts/%s: %s" % (form, out.strip()[-200:]))
        os.remove(p)

    # 文本 / 富文本 / 轮播等
    # 键名直通 add-ui 的同名参数（w/h/x/y/place/bg/fg-color/font-size/form-name/url/html…），
    # 只有 comp/text/style 需要改名/兜底。页头横幅 = {"comp":"JText","text":"销售订单",
    # "place":"top","bg":"#4A90E2","fg-color":"#FFFFFF","font-size":30,"bold":True,"h":10}
    if not (page.get("ui") or []):
        # ⚠️ 2026-09-22 降级：这里曾经 errs.append → 整页判 FAIL。
        # 「每张盘第 1 行放盘标题」是**某些应用的需求**（进销存就是），
        # **不是平台或本脚本的规则** —— 引擎没这条约束，`app_audit` 的
        # 「盘标题不在数组下标 0」只在盘上**已经有 JText** 时才判。
        # 拿它当 FAIL 的代价（实测）：进销存 11 张本来就不需要标题的盘全 FAIL，
        # 逼作者回头给 16 张盘补 ui 段再重建 11 张。现在只出声、不判失败。
        if page.get("charts"):
            log("NOTE:%s 没有 ui 段 → 本页不生成盘标题（要的话在规格里加 ui）" % name)
    for ui in (page.get("ui") or []):
        argv = ["--page-id", page_id,
                "--comp", ui.get("comp", "JText"),
                "--text", ui.get("text", ""),
                "--style", ui.get("style", "")]
        for k, v in ui.items():
            if k in ("comp", "text", "style"):
                continue
            if v is True:
                argv.append("--%s" % k)
            elif v not in (None, "", False):
                argv += ["--%s" % k, str(v)]
        rc, out = run_cli(cli("add-ui", *argv))
        if "ADDED=" not in out:
            errs.append("ui: %s" % out.strip()[-160:])

    # 查询面板（每表一次；add-filter 禁传 --form-code）
    for flt in (page.get("filters") or []):
        p = os.path.join(workdir, "flt_%s.json" % (abs(hash(name)) % 100000))
        with open(p, "w", encoding="utf-8") as f:
            json.dump(flt, f, ensure_ascii=False, indent=1)
        rc, out = run_cli(cli("add-filter", "--page-id", page_id, "--specs-file", p))
        if "CHART_MATCH=" not in out and "ADDED=" not in out:
            errs.append("filter: %s" % out.strip()[-160:])
        os.remove(p)

    # ⚠️ 按钮**不在这一趟加**：见 add_page_buttons 的说明（必须等所有盘都建完）。
    return page_id, errs


def page_has_buttons(page_id):
    """盘上是否已经有按钮组件。跳过时用它判定，避免重跑把按钮组加两遍。"""
    try:
        page = Q.bi_utils.query_page(page_id)
        tmpl = page.get("template") or []
        if isinstance(tmpl, str):
            tmpl = json.loads(tmpl)
        return any(isinstance(c, dict) and c.get("component") == "JCustomButton"
                   for c in (tmpl or []))
    except Exception:                                             # noqa: BLE001
        return True          # 查不到就当「有」，宁可少加也不要重复加


def add_page_buttons(page, page_id, workdir):
    """加按钮组。**必须在所有页面建完之后单独跑一趟**。

    按钮组可以是**一组**（dict）或多组（list）——模版首页就是左右两组半宽并排
    （x=0 / x=12，各 5 个按钮），一组 dict 表达不了。

    ⚠️ 2026-09-17 改成两趟：`_resolve_button_pages` 要查菜单表把「看板名」换成 pageId，
      所以**被指向的看板必须已经存在**。原先按钮和建盘在同一趟里，规格里只要把「首页」
      排在它要跳转的看板**前面**（很自然 —— 首页本来就是第一条），
      那几个跳转按钮就永远解析不到 id：`[btn] 找不到看板 xxx` + 按钮空 customPage，
      而盘本身照报 `OK:`，属于静默半坏。
    """
    name = page["name"]
    errs = []
    btns = page.get("buttons")
    groups = [btns] if isinstance(btns, dict) else (btns or [])
    # ⚠️ 先把**所有**按钮组校验一遍，再动第一组。2026-09-21 进销存实测：两组按钮里第一组加成功、
    # 第二组因 op 写成别名表外的「跳转」而 FAIL —— 盘上留下一个半成品按钮组件，重跑时
    # page_has_buttons 判「已有按钮」直接跳过，永远修不好；手工补加又叠出重复组。
    # 校验失败一个组件都不加，规格改对后重跑就是干净的。
    pre = _validate_button_groups(groups)
    if pre:
        return ["buttons 规格未通过预校验（一个按钮都没加）: " + "；".join(pre)]
    for i, grp in enumerate(groups):
        if not grp:
            continue
        grp = _resolve_button_pages(grp)
        # 每组一个不重复的组件名（add-buttons 落成 componentName），finalize_page 按名配对规格坐标
        grp = dict(grp, groupTitle=_btn_group_key(grp, i))
        if ("x" in grp or "y" in grp) and not grp.get("place"):
            # 规格给了坐标：add-buttons 默认 place=top 会把同列图表整体下移按钮高度，finalize_page 只搬按钮不搬图
            # → 重叠（2026-09-22 销售管理 R2）。先追加到底部，第 ③ 趟 finalize_page 按坐标落位
            grp = dict(grp, place="bottom")
        p = os.path.join(workdir, "btn_%s_%d.json" % (abs(hash(name)) % 100000, i))
        with open(p, "w", encoding="utf-8") as f:
            json.dump(grp, f, ensure_ascii=False, indent=1)
        rc, out = run_cli(cli("add-buttons", "--page-id", page_id, "--specs-file", p))
        if "ADDED=" not in out:
            errs.append("buttons[%d]: %s" % (i, out.strip()[-160:]))
        os.remove(p)
    return errs


def _validate_button_groups(groups):
    """静态校验按钮组：op 必须在 qqy_ops 的别名表里；"page" 点名的看板必须已存在。
    返回错误列表（空 = 通过）。只读不写，失败不会留下半成品组件。"""
    try:
        from qqy_ops import _BTN_OP_ALIASES as aliases          # 同目录，PYTHONPATH 已含 scripts
    except Exception:                                            # noqa: BLE001
        aliases = None
    pages = None
    errs = []
    for gi, grp in enumerate(groups):
        if not grp:
            continue
        if not isinstance(grp, dict):
            errs.append("buttons[%d] 应是对象 {rowNum,btnType,btnWidth,place,buttons:[…]}" % gi)
            continue
        for bi, b in enumerate(grp.get("buttons") or []):
            where = "buttons[%d].buttons[%d]「%s」" % (gi, bi, b.get("title", "?"))
            op = str(b.get("op") or b.get("operationType") or "").strip()
            if b.get("page") and not b.get("customPage") and not op:
                op = "打开页面"
            if aliases is not None and op and op not in aliases and op.lower() not in aliases:
                errs.append("%s op=%r 不在别名表（可用：创建记录/打开列表视图/打开页面(跳转)/打开链接/调用业务流程）"
                            % (where, op))
            if b.get("page") and not b.get("customPage"):
                if pages is None:
                    pages, _g, _r = index_menus(AUTH[3])
                if not pages.get(b["page"]):
                    errs.append("%s 指向的看板「%s」不存在（现有：%s）"
                                % (where, b["page"], "、".join(sorted(pages)[:12])))
    return errs


def _resolve_button_pages(grp):
    """按钮里的 "page": "<看板名>" → customPage={label,value,key}（value = menuUrl = pageId）。"""
    btns = grp.get("buttons") or []
    want = [b for b in btns if b.get("page") and not b.get("customPage")]
    if not want:
        return grp
    pages, _groups, _rows = index_menus(AUTH[3])
    grp = json.loads(json.dumps(grp, ensure_ascii=False))     # 不就地改调用方的规格
    for b in grp.get("buttons") or []:
        nm = b.pop("page", None)
        if not nm or b.get("customPage"):
            continue
        ids = pages.get(nm) or []
        if not ids:
            print("[btn] 找不到看板 %s（现有：%s）" % (nm, "、".join(sorted(pages)[:12])))
            continue
        b["op"] = b.get("op") or "打开页面"
        b["customPage"] = {"label": nm, "value": ids[0], "key": ids[0]}
    return grp


def _looks_like_code(s):
    return bool(s) and all(c.isalnum() or c in "_-" for c in s) and not any("一" <= c <= "鿿" for c in s)


def _chart_title(c):
    """图组件在盘上的标题：`config.option.title.text`（`config.title` 是空的）。"""
    o = ((c.get("config") or {}).get("option") or {}).get("title") or {}
    t = o.get("text")
    return t if isinstance(t, str) else ""


# ── 自动排版：规格没给坐标时，按组件类型套标准尺寸并铺满 24 栅格 ──
#    （2026-09-22 进销存 R5：规格 x/y 全为 None 且 w/h 离谱 —— KPI w=10 h=32、趋势图 w=6，
#     结果全堆在 x=0 一列、58% 的行宽度不足 24，盘看着很丑）
KPI_COMPS = {"JNumber", "JIndicator", "JCircle", "JProgress"}
WIDE_COMPS = {"JPivotTable", "JTable", "JList", "JTimeline", "JMap"}
GRID = 24
KPI_W, KPI_H = 6, 12          # 一行四个
# ⚠️ KPI 卡高度别往大了给。`number.vue` 的数字是在**标题下方那块 body 区**里居中，
# 不是在整张卡里居中；body 区 = 格子高 - 卡头 42 - 内边距 24。h=16(166px) 时 body 还剩 100px
# 去放一个 36px 的数字，上下各空一大截，整体重心偏下，看着就是「贴底 + 空荡」
#（2026-09-22 用户实测截图：标题 430、数字 572、卡底 648）。h=12(122px) 时 body 剩 56px，
# 刚好包住数字。**改像素公式救不了这个**——手工拖出来的同高卡片一样难看。
CHART_W, CHART_H = 12, 28     # 一行两个
WIDE_H = 32
BTN_MIN_H = 20
# ⚠️ 按钮组（JCustomButton）**不能低于 20 行**。`customButton/Button.vue` 的 `.btn-area`
# 写死 `min-height: 200px`（外加 `padding:24px 20px`、空 `.title` 还占 `margin-bottom:12px`），
# 图标区 72px + 10px + 文字 + 上下 10px ≈ 123px 是**居中在那 200px 里**的。
# 格子若矮于 200px，设计器不裁剪、撑到 200 看着还行，运行态 `ViewPane` 是
# `overflow:hidden; height:100%`，于是内容被按 200 居中后下压再裁底 ——
# 图标和文字整体贴到下半截（2026-09-22 用户对比截图：设计器对、预览错，h=15=155px）。
# 11h-10 ≥ 200 ⇒ h ≥ 19.1 ⇒ 取 20（210px）。
FILTER_H = 8
TITLE_H = 6


def _btn_group_key(g, i):
    """按钮组的组件名：规格写了 title 用 title，否则「按钮组N」（N 为规格里的序号，从 1 起）。
    add-buttons 把新组**插到模板最前面**，按出现顺序 zip 配坐标会整组对调
    （2026-09-24 人事OA-速测18：5 个按钮的组跑到 y=72、3 个按钮的组跑到 y=0）。"""
    return (g.get("title") or g.get("groupTitle") or "按钮组%d" % (i + 1)) if isinstance(g, dict) else ""


def _tile_class(comp):
    if comp in WIDE_COMPS:
        return "wide"
    return "kpi" if comp in KPI_COMPS else "chart"


def _spec_layout_bad(specs, extra=()):
    """规格自带的 x/y/w/h 是否**不合格**（不合格就别尊重它，改用自动铺版）。

    四条判据，都来自真机渲染出来的难看效果（2026-09-22 项目管理 R5）：
    · 行宽 > 24 → 组件重叠；
    · 中间有整行没人占 → 页面开天窗（项目看板 y=100~111 空了 12 行）；
    · 图类组件高度 < 20 → 图例压在图上（项目状态分布饼图 h=15）；
    · 数字卡高度 > KPI_H → 一个大空框中间一个小数字。

    ⚠️ 最后一条的门槛原先写 18，结果规格给的 h=16 从门槛下溜过去，自动铺版没接管，
    真机上四张 KPI 全是大空框（2026-09-22 用户连报三次「贴底」）。门槛一律跟 KPI_H 走，
    别再单独设一个更松的数。
    """
    if not specs:
        return None
    cov, top, bottom = {}, None, 0
    # extra：规格给了坐标的按钮组也占行。以前只算图表，按钮组占的那几行被当成「开天窗」，
    # 整页坐标被丢掉、透视表被排到盘底（人事OA-速测19：规格 y=20 落到 y=110）
    for g in list(specs) + [dict(e, comp="JCustomButton") for e in extra]:
        try:
            x, y = int(g.get("x") or 0), int(g.get("y") or 0)
            w, h = int(g.get("w") or 0), int(g.get("h") or 0)
        except (TypeError, ValueError):
            return "坐标不是整数（%s）" % (g.get("title") or g.get("comp"))
        cls = _tile_class(g.get("comp"))
        if g.get("comp") != "JCustomButton":
            if cls == "chart" and h < 20:
                return "图「%s」高 %d < 20（图例会压在图上）" % (g.get("title") or g.get("comp"), h)
            if cls == "kpi" and h > KPI_H:
                return "数字卡「%s」高 %d > %d（大空框）" % (g.get("title") or g.get("comp"), h, KPI_H)
        for yy in range(y, y + max(h, 1)):
            cov[yy] = cov.get(yy, 0) + w
        top = y if top is None else min(top, y)
        bottom = max(bottom, y + h)
    over = sorted(yy for yy, v in cov.items() if v > GRID)
    if over:
        return "第 %d 行起组件宽度合计超过 24（会重叠）" % over[0]
    hole = next((yy for yy in range(top or 0, bottom) if yy not in cov), None)
    if hole is not None:
        return "第 %d 行整行没有组件（页面开天窗）" % hole
    return None


def _auto_tile(items, y0):
    """按「看板该长什么样」重排：**数字卡在上、图居中、明细表垫底**，每行凑满 24。

    两条来自实测的规矩（2026-09-22 进销存 R5，用户连报三次「太丑」）：
    · **按类型重排，不跟规格顺序**。规格常写成 KPI→图→KPI→表，若只合并「连续同类」，
      两个数字卡会被图隔开、各自独占一整行 → 900×154 的大白条，中间一个小数字。
    · **数字卡只有 1~2 个时，竖排在左侧 1/4 宽，右侧留给第一张图**（经典看板排法）；
      ≥3 个才平铺成一行。数字卡绝不和图**并排等高**，否则又被拉成大空框。
    """
    kpis = [c for c in items if _tile_class(c.get("component")) == "kpi"]
    charts = [c for c in items if _tile_class(c.get("component")) == "chart"]
    wides = [c for c in items if _tile_class(c.get("component")) == "wide"]
    out, y = [], y0

    def row(chunk, h):
        nonlocal y
        x = 0
        for k, c in enumerate(chunk):
            w = (GRID // len(chunk)) if k < len(chunk) - 1 else GRID - x   # 最后一个吃余数，凑满 24
            out.append((c, x, y, w, h))
            x += w
        y += h

    if kpis and len(kpis) <= 2 and charts:
        # 左：数字卡竖排（各 1/4 宽）；右：第一张图占满剩下的 3/4，高度与整列对齐
        col_h = CHART_H // len(kpis)
        for i, c in enumerate(kpis):
            out.append((c, 0, y + i * col_h, KPI_W, col_h))
        out.append((charts[0], KPI_W, y, GRID - KPI_W, CHART_H))
        y += CHART_H
        charts = charts[1:]
    else:
        for i in range(0, len(kpis), 4):
            row(kpis[i:i + 4], KPI_H)
    for i in range(0, len(charts), 2):
        row(charts[i:i + 2], CHART_H)
    for c in wides:
        h = max(WIDE_H, int(c.get("h") or 0))
        out.append((c, 0, y, GRID, h))
        y += h
    return out, y


def finalize_page(page, page_id):
    """**整页按规格落位**：文本标题置顶 → 图表/按钮按规格的 x/y/w/h 各就各位。

    三个 CLI 各有各的落位脾气，谁也管不了全页：`add-ui` 追加到数组末尾（渲染到盘底）、
    `add-buttons` 默认 `place=top` 把**同列**已有组件整体下移、`add-charts` 按自己的顺序排。
    2026-09-22 四个应用每个都要手写一遍搬运脚本，最严重一例（进销存首页）4 张 KPI 被两组
    半宽按钮各顶一次，散成 x=6/18/0/12、y=20/40 两排，每排右侧留白 12。

    所以这里不做增量微调，而是**拿规格当权威重排一遍**：图按标题匹配（匹配不上就按同类型出现
    顺序兜底），按钮组按出现顺序，规格没给坐标的组件保持原样。失败不算建盘失败。"""
    api, token, tenant, app = AUTH
    hdr = {"X-Access-Token": token, "X-Tenant-Id": str(tenant), "X-Low-App-ID": str(app)}
    req = urllib.request.Request(api.rstrip("/") + "/drag/page/queryById?id=" + str(page_id), headers=hdr)
    res = json.load(urllib.request.urlopen(req, timeout=60)).get("result") or {}
    tmpl = res.get("template")
    comps = json.loads(tmpl) if isinstance(tmpl, str) and tmpl else (tmpl or [])
    if not comps:
        return "空模板"

    def place(c, x, y, w, h):
        before = (c.get("x"), c.get("y"), c.get("w"), c.get("h"))
        c.update(x=x, y=y, w=w, h=h, pcX=x, pcY=y, pcW=w)
        # ⚠️ 高度必须写**格子的真实像素高**：vue-grid-layout 里 `row-height=1`、`margin=[10,10]`，
        # 所以一格 = h*1 + (h-1)*10 = 11h-10（`viewEngine/ViewPane.vue`）。
        # 写成 11h 会多 10px，而敲敲云运行态还比设计器多吃一份 a-card 内边距
        # （`number.vue` 的 bodyStyle：!isLowApp 才 padding:0），内容就溢出到格子外 ——
        # 数字贴底、按钮文字被裁（2026-09-22 用户实测：设计器好、运行态坏）。
        c.setdefault("config", {})["size"] = {"width": w * 75, "height": h * 11 - 10}
        return before != (x, y, w, h)

    texts = [c for c in comps if c.get("component") == "JText"]
    others = [c for c in comps if c.get("component") != "JText"]
    charts = [c for c in others if c.get("component") not in ("JFilterQuery", "JCustomButton")]
    changed = False

    # ① 文本标题：置顶并占位，后面所有组件的 y 以 top_h 为原点
    top_h = 0
    for t in texts:
        h = int(t.get("h") or 10)
        changed |= place(t, 0, top_h, 24, h)
        top_h += h
    if texts and comps[0].get("component") != "JText":
        changed = True                              # 数组顺序也要改（见文末 out）

    # ①-b 查询面板：`add-filter` 把它插在「它联动的第一张图的 y」上，既不认标题占位、也和首行图压在一起
    #      （2026-09-22 进销存 R3 九张盘中招）。让它在标题下方各占一整行，其余组件整体顺延。
    flts = [c for c in others if c.get("component") == "JFilterQuery"]
    filt_h = 0
    for fq in flts:
        h = max(int(fq.get("h") or 8), 1)
        changed |= place(fq, 0, top_h + filt_h, 24, h)
        filt_h += h
    top_h += filt_h                                 # 后面的图与按钮都从这里往下排

    # ①-c 规格给了坐标的按钮组**先落位**：它们通常钉在盘顶，自动铺版的图必须从它们下方开始，
    #      否则两者都从 y=0 起算、直接压在一起（2026-09-22 进销存 R5 首页实测 10 行重叠）
    _grps = page.get("buttons")
    _grps = [_grps] if isinstance(_grps, dict) else (_grps or [])
    btn_comps = [c for c in others if c.get("component") == "JCustomButton"]
    btn_fixed, btn_bottom = set(), top_h
    spec_bottom = top_h                 # 规格**原本**以为按钮排到哪一行
    by_name = {}
    for c in btn_comps:
        by_name.setdefault(c.get("componentName"), []).append(c)
    pairs, left = [], list(btn_comps)
    for i, g in enumerate(_grps):
        cand = by_name.get(_btn_group_key(g, i)) or []
        c = next((x for x in cand if x in left), None)
        if c is not None:
            left.remove(c)
        pairs.append((g, c))
    # 名字对不上的（老页面组件名都叫「自定义按钮」）按剩余组件兜底：模板是倒序插入的，所以倒着配
    left.reverse()
    pairs = [(g, c if c is not None else (left.pop(0) if left else None)) for g, c in pairs]
    for g, c in pairs:
        if c is None:
            continue
        if isinstance(g, dict) and ("x" in g or "y" in g):
            h_raw = int(g.get("h", c.get("h") or BTN_MIN_H))
            h = max(h_raw, BTN_MIN_H)
            y = int(g.get("y", 0)) + top_h
            changed |= place(c, int(g.get("x", c.get("x") or 0)), y, int(g.get("w", c.get("w") or 24)), h)
            btn_fixed.add(id(c))
            btn_bottom = max(btn_bottom, y + h)
            spec_bottom = max(spec_bottom, y + h_raw)
    # 按钮被 BTN_MIN_H 抬高后，规格里按原高度往下排的图会被顶穿 → 整体下移同样的量
    btn_shift = max(0, btn_bottom - spec_bottom)

    # ② 图表：规格给了 x/y 就按规格落位；**一个都没给就自动铺版**
    #    （2026-09-22 进销存 R5：规格 x/y 全 None、w/h 又离谱，原来这一段整个跳过，
    #     图就保持 add-charts 的原始堆叠 —— 全挤在 x=0 一列、58% 的行宽度不足 24）
    spec_charts = [g for grp in (page.get("charts") or {}).values() for g in (grp or [])]
    want = [(g.get("comp"), (g.get("title") or ""), g) for g in spec_charts if "x" in g or "y" in g]
    chart_comps = [c for c in others if c.get("component") not in ("JFilterQuery", "JCustomButton")]
    btn_specs = [g for g in _grps if isinstance(g, dict) and ("x" in g or "y" in g)]
    why = _spec_layout_bad([g for _c, _t, g in want], extra=btn_specs) if want else None
    if why:
        # 以前静默丢，日志照打 OK（考勤/销售-速测19）
        print("WARN:%s 规格坐标不合格，整页改自动铺版：%s" % (page.get("name"), why), flush=True)
        want = []                                   # 规格排版不合格 → 丢掉坐标，走自动铺版

    if want:                                        # —— 规格排过版：尊重它
        pool = list(others)
        for comp, title, g in want:
            hit = None
            if title:
                hit = next((c for c in pool if c.get("component") == comp and _chart_title(c) == title), None)
            if hit is None:
                hit = next((c for c in pool if c.get("component") == comp), None)
            if hit is None:
                continue
            pool.remove(hit)
            gy = int(g.get("y", 0)) + top_h
            changed |= place(hit, int(g.get("x", hit.get("x") or 0)),
                             gy + (btn_shift if gy >= spec_bottom else 0),
                             int(g.get("w", hit.get("w") or 24)), int(g.get("h", hit.get("h") or 20)))
        next_y = max([int(c.get("y") or 0) + int(c.get("h") or 0) for c in chart_comps] or [top_h])
    elif chart_comps:                               # —— 规格没排版：按类型套标准尺寸铺满 24 栅格
        ordered = []                                # 按规格里的出现顺序排，标题匹配不上就按类型顺序兜底
        pool = list(chart_comps)
        for g in spec_charts:
            t, comp = (g.get("title") or ""), g.get("comp")
            hit = next((c for c in pool if c.get("component") == comp and _chart_title(c) == t), None) \
                if t else None
            hit = hit or next((c for c in pool if c.get("component") == comp), None)
            if hit is not None:
                pool.remove(hit)
                ordered.append(hit)
        ordered += pool                             # 规格里没点名的挂在后面
        tiled, next_y = _auto_tile(ordered, btn_bottom)
        for c, x, y, w, h in tiled:
            changed |= place(c, x, y, w, h)
    else:
        next_y = top_h

    # ③ 没给坐标的按钮组：整行接在图表下面（给了坐标的已在 ①-c 落位）
    for c in btn_comps:
        if id(c) in btn_fixed:
            continue
        h = max(int(c.get("h") or 0), BTN_MIN_H)
        changed |= place(c, 0, next_y, 24, h)
        next_y += h

    # ③-b 规格给了半宽坐标、但那一行最后没人跟它并排的按钮组 → 拉满整行，别留半边空白
    #     （规格本意是「按钮左半 + 图右半」，而图的坐标若因不合格被丢弃就会排到下一行去）
    for c in btn_comps:
        if id(c) not in btn_fixed or int(c.get("w") or 0) >= GRID:
            continue
        y0, y1 = int(c.get("y") or 0), int(c.get("y") or 0) + max(int(c.get("h") or 1), 1)
        share = any(o is not c and int(o.get("y") or 0) < y1
                    and int(o.get("y") or 0) + max(int(o.get("h") or 1), 1) > y0
                    for o in comps)
        if not share:
            changed |= place(c, 0, y0, GRID, max(int(c.get("h") or 0), BTN_MIN_H))
    if not changed:
        return None
    out = texts + sorted(others, key=lambda c: (int(c.get("y") or 0), int(c.get("x") or 0)))
    for i, c in enumerate(out):
        c["orderNum"] = i
    body = json.dumps({"id": str(page_id), "template": json.dumps(out, ensure_ascii=False)}).encode("utf-8")
    req = urllib.request.Request(api.rstrip("/") + "/drag/page/edit", data=body, method="POST",
                                 headers=dict(hdr, **{"Content-Type": "application/json"}))
    r = json.load(urllib.request.urlopen(req, timeout=60))
    if not r.get("success"):
        return "保存失败 %s" % str(r)[:120]
    # 没有文本标题时别说「标题@0」（人事OA-速测18：日志说有标题，盘上其实没有）
    return ("标题@0 + %d 组件已规整" % len(out)) if texts else ("%d 组件已规整（无标题）" % len(out))


# ---------------- 主流程 ----------------

def _lowcode_workdir(app_id, sub):
    """与 lowapp/scripts/skill_temp_path.app_workdir 同一规则：按 app.json 找该应用的工作目录。"""
    import json
    root = os.path.join(tempfile.gettempdir(), 'jeecg-lowcode')
    base = (os.environ.get('JEECG_LOWCODE_WORKDIR') or '').strip()
    if not (base and os.path.isdir(base)):
        hits = []
        for name in (os.listdir(root) if os.path.isdir(root) else []):
            try:
                j = json.load(open(os.path.join(root, name, 'app.json'), encoding='utf-8'))
            except (OSError, ValueError):
                continue
            if str(j.get('app_id')) == str(app_id):
                hits.append((j.get('created') or '', name))
        base = os.path.join(root, max(hits)[1] if hits else str(app_id))
    return os.path.join(base, sub)


def main():
    ap = argparse.ArgumentParser(description="批量建仪表盘：单进程、非破坏、可断点续跑")
    ap.add_argument("--api-base", required=True)
    ap.add_argument("--token", required=True)
    ap.add_argument("--tenant-id", default="")
    ap.add_argument("--tenant-name", default="")
    ap.add_argument("--app-id", default="")
    ap.add_argument("--app-name", default="")
    ap.add_argument("--spec", required=True, help="dashboards.json")
    ap.add_argument("--only", default="", help="只建这些盘（逗号分隔）")
    ap.add_argument("--recreate", default="", help="这些盘先删后建（逗号分隔）；默认已存在则跳过")
    ap.add_argument("--finalize", action="store_true",
                    help="对**已存在的盘**也补跑一遍第 ③ 趟整页规整（标题置顶/按钮落位）。"
                         "默认只规整本次新建的盘 —— 跳过的不动。老盘排版乱、又不想删盘重建时用它。")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    global AUTH
    AUTH = [a.api_base, a.token, "", a.app_id]

    # 租户/应用解析（各一次）
    if not a.tenant_id:
        rc, out = run_cli(["tenants", a.api_base, a.token, "--name", a.tenant_name])
        for line in out.splitlines():
            if line.startswith("TENANT_ID="):
                a.tenant_id = line.split("=", 1)[1].strip()
    if not a.tenant_id:
        raise SystemExit("FAIL:tenant 无法解析（给 --tenant-id 或 --tenant-name）")
    AUTH[2] = a.tenant_id
    log("OK:tenant %s" % a.tenant_id)

    if not a.app_id:
        if not a.app_name:
            raise SystemExit("FAIL:app 需要 --app-id 或 --app-name")
        rc, out = run_cli(cli("apps", "--name", a.app_name))
        for line in out.splitlines():
            if line.startswith("APP_ID="):
                a.app_id = line.split("=", 1)[1].strip()
        if not a.app_id:
            raise SystemExit("FAIL:app 无法解析 %s" % a.app_name)
    AUTH[3] = a.app_id
    log("OK:app %s" % a.app_id)

    with open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)
    pages = spec.get("pages") or []
    only = {s.strip() for s in a.only.split(",") if s.strip()}
    recreate = {s.strip() for s in a.recreate.split(",") if s.strip()}
    if only:
        pages = [p for p in pages if p["name"] in only]
    if not pages:
        raise SystemExit("FAIL:spec 里没有待建页面")

    # ⚠️ 规格预校验要在**删盘之前**：否则 --recreate 先把旧盘删了、再因规格不合格拒建，
    #    应用里那张盘就凭空消失了（2026-09-22 实测踩到）。
    bad = [(p["name"], e) for p in pages for e in _validate_page(p)]
    if bad:
        for nm, e in bad:
            log("FAIL:规格预校验 %s" % nm)
            log("   " + e)
        raise SystemExit("FAIL:规格预校验未通过 %d 项 —— 未删除、未新建任何盘" % len(bad))

    # 菜单索引：一次取全，pageId 用 menuUrl 列
    existing, groups, _ = index_menus(a.app_id)
    if recreate:
        for nm in list(recreate):
            for pid in existing.get(nm, []):
                run_cli(cli("delete-page", "--page-id", pid))
                log("OK:recreate 删除旧盘 %s %s" % (nm, pid))
        existing, groups, _ = index_menus(a.app_id)

    workdir = _lowcode_workdir(a.app_id, "dash")   # 该应用的工作目录 /dash/
    os.makedirs(workdir, exist_ok=True)
    t0 = time.time()
    ok = skip = fail = 0
    want_buttons = []          # [(page, pid)]：第 ② 趟统一加按钮
    done_pages = []            # 第 ③ 趟整页规整（标题置顶 / 按钮落位）
    for page in pages:
        name = page["name"]
        # 非破坏：已存在就跳过（可断点续跑）。要重建请用 --recreate
        if existing.get(name):
            log("OK:skip %s（已存在 %s）" % (name, existing[name][0]))
            skip += 1
            if a.finalize:
                done_pages.append((page, existing[name][0]))
            # 已存在的盘也可能是「图建好了、按钮还没加」的半成品（老版本一趟建成时，
            # 跳转按钮会因为目标盘还没建而解析不到 pageId）。查一下真有没有按钮组件，
            # 没有就补第 ② 趟——**不无条件补**，否则每次重跑都会再叠一组按钮。
            if page.get("buttons") and not a.dry_run \
                    and not page_has_buttons(existing[name][0]):
                log("   ↳ 有 buttons 规格但盘上没有按钮组件，补加")
                want_buttons.append((page, existing[name][0]))
            continue
        if a.dry_run:
            log("OK:plan %s → 分组「%s」 图 %d 表 / 查询 %d%s"
                % (name, page.get("group", ""), len(page.get("charts") or {}),
                   len(page.get("filters") or []),
                   "" if (page.get("ui") or []) else "  · 无 ui 段（本页不加盘标题）"))
            continue
        try:
            pid, errs = build_page(page, workdir, dry_run=False)
        except Exception as e:                                # noqa: BLE001
            log("FAIL:%s 异常 %s" % (name, str(e)[:160]))
            fail += 1
            continue
        if errs:
            log("FAIL:%s" % name)
            for e in errs[:4]:
                log("   " + e.replace("\n", " ")[:180])
            fail += 1
        else:
            log("OK:%s pid=%s" % (name, pid))
            ok += 1
            done_pages.append((page, pid))
            if page.get("buttons"):
                want_buttons.append((page, pid))

    # ② 趟：所有盘都建完之后再加按钮 —— 「打开页面」按钮要指向的看板此时才都存在。
    for page, pid in want_buttons:
        try:
            errs = add_page_buttons(page, pid, workdir)
        except Exception as e:                                # noqa: BLE001
            log("FAIL:按钮 %s 异常 %s" % (page["name"], str(e)[:160]))
            fail += 1
            continue
        if errs:
            log("FAIL:按钮 %s" % page["name"])
            for e in errs[:4]:
                log("   " + e.replace("\n", " ")[:180])
            fail += 1
        else:
            log("OK:按钮 %s" % page["name"])

    try:
        os.rmdir(workdir)
    except OSError:
        pass

    # 收尾校验：每个盘是不是真的落在点名分组里（复用的菜单索引，不再多发请求）
    if not a.dry_run:
        _, g2, rows2 = index_menus(a.app_id)
        page_parent = {}
        for r in rows2:
            if r["type"] == "drag":
                page_parent.setdefault(r["name"], r["parent"])
        wrong = []
        for page in pages:
            nm, want = page["name"], page.get("group")
            if not want or nm not in page_parent:
                continue
            if g2.get(want) and page_parent[nm] != g2[want]:
                wrong.append(nm)
        if wrong:
            log("FAIL:分组不对 %d 个: %s" % (len(wrong), "、".join(wrong[:8])))
        else:
            log("OK:分组 全部就位")

    # ③ 趟：整页规整（标题置顶、按钮组按规格坐标）。失败不算建盘失败，只提示
    for page, pid in done_pages:
        try:
            msg = finalize_page(page, pid)
            if msg:
                log("OK:finalize %s %s" % (page["name"], msg))
        except Exception as e:                                # noqa: BLE001
            log("WARN:finalize %s %s" % (page["name"], str(e)[:120]))
    log("OK:done 建 %d / 跳过 %d / 失败 %d，%.1fs" % (ok, skip, fail, time.time() - t0))
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
