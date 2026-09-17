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

def build_page(page, workdir, dry_run=False):
    name = page["name"]
    group = page.get("group", "")
    errs = []

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
    for i, grp in enumerate([btns] if isinstance(btns, dict) else (btns or [])):
        if not grp:
            continue
        grp = _resolve_button_pages(grp)
        p = os.path.join(workdir, "btn_%s_%d.json" % (abs(hash(name)) % 100000, i))
        with open(p, "w", encoding="utf-8") as f:
            json.dump(grp, f, ensure_ascii=False, indent=1)
        rc, out = run_cli(cli("add-buttons", "--page-id", page_id, "--specs-file", p))
        if "ADDED=" not in out:
            errs.append("buttons[%d]: %s" % (i, out.strip()[-160:]))
        os.remove(p)
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


# ---------------- 主流程 ----------------

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

    # 菜单索引：一次取全，pageId 用 menuUrl 列
    existing, groups, _ = index_menus(a.app_id)
    if recreate:
        for nm in list(recreate):
            for pid in existing.get(nm, []):
                run_cli(cli("delete-page", "--page-id", pid))
                log("OK:recreate 删除旧盘 %s %s" % (nm, pid))
        existing, groups, _ = index_menus(a.app_id)

    workdir = tempfile.mkdtemp(prefix="qqy-dash-")
    t0 = time.time()
    ok = skip = fail = 0
    want_buttons = []          # [(page, pid)]：第 ② 趟统一加按钮
    for page in pages:
        name = page["name"]
        # 非破坏：已存在就跳过（可断点续跑）。要重建请用 --recreate
        if existing.get(name):
            log("OK:skip %s（已存在 %s）" % (name, existing[name][0]))
            skip += 1
            # 已存在的盘也可能是「图建好了、按钮还没加」的半成品（老版本一趟建成时，
            # 跳转按钮会因为目标盘还没建而解析不到 pageId）。查一下真有没有按钮组件，
            # 没有就补第 ② 趟——**不无条件补**，否则每次重跑都会再叠一组按钮。
            if page.get("buttons") and not a.dry_run \
                    and not page_has_buttons(existing[name][0]):
                log("   ↳ 有 buttons 规格但盘上没有按钮组件，补加")
                want_buttons.append((page, existing[name][0]))
            continue
        if a.dry_run:
            log("OK:plan %s → 分组「%s」 图 %d 表 / 查询 %d"
                % (name, page.get("group", ""), len(page.get("charts") or {}),
                   len(page.get("filters") or [])))
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

    log("OK:done 建 %d / 跳过 %d / 失败 %d，%.1fs" % (ok, skip, fail, time.time() - t0))
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
