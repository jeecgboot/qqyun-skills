# -*- coding: utf-8 -*-
"""`build_dashboards.py` 排版归一的离线单测（**不发任何请求**，可反复跑）。

回归样本是 2026-09-30「进销存管理」事故的真实坐标：16 张盘里 7 张有「同一排高度不齐」，
共 9 行（数字卡 h=12 与折线/柱状 h=28 并排）。当时 `_spec_layout_bad` 的四条判据**一条都
拦不住**，规格被判成合格原样落位 —— 因为「同一排必须等高」这条规则只写在 `create.md` 里，
代码里没有对应闸门。本文件锁住三件事：

  ① `_normalize_rows` 能把混排拆开、拉平等高、归到标准宽度档位、y 连续；
  ② `_spec_layout_bad` 第 5 条能拦住没归一过的混排，且**不误伤**「按钮与图并排」；
  ③ 归一**幂等** —— `--finalize` 重跑是常态，不幂等会越跑越乱。

跑法：`python test_build_dashboards.py`（退出码 0 = 全绿）

控制台是 GBK，所以**打印一律走 ASCII**，中文只出现在源码注释里。
"""
import copy
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_dashboards as B                                              # noqa: E402

KPI_H, CHART_H, WIDE_H, GRID = B.KPI_H, B.CHART_H, B.WIDE_H, B.GRID

FAILED = []


def C(comp, x, y, w, h, title=""):
    """一条图表规格。坐标缺省用 None 表示「规格没给」。"""
    c = {"comp": comp, "title": title or comp}
    for k, v in (("x", x), ("y", y), ("w", w), ("h", h)):
        if v is not None:
            c[k] = v
    return c


def page(charts, buttons=None):
    """charts: {formCode: [规格]}；buttons: [规格]。"""
    p = {"name": "T", "charts": charts}
    if buttons:
        p["buttons"] = buttons
    return p


def rows_of(p):
    """{y: [组件]}，跨表单合并 —— 首页实测两个表单共排同一行。"""
    r = {}
    for items in (p.get("charts") or {}).values():
        for c in items:
            r.setdefault(int(c.get("y") or 0), []).append(c)
    return r


def layout_of(p):
    """按 y 排序的 [(y, h, [w...], [x...], [comp...])]，方便整体比对。"""
    out = []
    for y, items in sorted(rows_of(p).items()):
        it = sorted(items, key=lambda c: int(c.get("x") or 0))
        out.append((y, int(it[0].get("h") or 0), [int(c.get("w") or 0) for c in it],
                    [int(c.get("x") or 0) for c in it], [c.get("comp") for c in it]))
    return out


def check_even(p, label):
    """每排等高、宽和=24、只用标准档位、x 连续无缝、y 首尾相接。"""
    rows = layout_of(p)
    y_prev_end = None
    for y, h, ws, xs, comps in rows:
        assert sum(ws) == GRID, "%s y=%d width sum=%d != 24 (%s)" % (label, y, sum(ws), ws)
        assert all(w in B.W_NOTCHES for w in ws), \
            "%s y=%d non-standard width %s" % (label, y, ws)
        assert xs == [sum(ws[:i]) for i in range(len(ws))], \
            "%s y=%d x not contiguous: %s (w=%s)" % (label, y, xs, ws)
        if y_prev_end is not None:
            assert y == y_prev_end, "%s gap/overlap before y=%d (prev ends %d)" % (label, y, y_prev_end)
        y_prev_end = y + h


def run(tid, desc, fn):
    try:
        fn()
    except AssertionError as e:
        FAILED.append("%s %s -> %s" % (tid, desc, e))
        print("FAIL %-4s %s" % (tid, desc))
    except Exception as e:                                                # noqa: BLE001
        FAILED.append("%s %s -> %r" % (tid, desc, e))
        print("FAIL %-4s %s (exception %r)" % (tid, desc, e))
    else:
        print("ok   %-4s %s" % (tid, desc))


# ── ① 真实事故坐标：7 张盘 9 行混排（取自 2026-09-30 进销存 spec）──

def t01_stock():                                            # 库存统计看板 y=0
    p = page({"t27": [C("JBar", 0, 0, 12, 28, "chanpin"), C("JNumber", 12, 0, 12, 12, "kucun"),
                      C("JPivotTable", 0, 28, 24, 32, "mingxi")]})
    assert B._normalize_rows(p) is True
    check_even(p, "t01")
    # 拆排后数字卡在上：y=0 是 KPI 排、y=12 才是图排
    rows = layout_of(p)
    assert [r[4] for r in rows] == [["JNumber"], ["JBar"], ["JPivotTable"]], rows
    assert rows[0][1] == KPI_H and rows[1][1] == CHART_H, rows


def t02_sales_order():                                      # 销售订单看板：KPI-图-KPI 夹心
    p = page({"t07": [C("JNumber", 0, 0, 8, 12, "jine"), C("JLine", 8, 0, 8, 28, "qushi"),
                      C("JNumber", 16, 0, 8, 12, "qiandan")]})
    assert B._normalize_rows(p) is True
    check_even(p, "t02")
    rows = layout_of(p)
    assert len(rows) == 2, rows                       # 夹心必须拆成两排
    assert rows[0][4] == ["JNumber", "JNumber"] and rows[0][2] == [12, 12], rows
    assert rows[1][4] == ["JLine"] and rows[1][2] == [24] and rows[1][1] == CHART_H, rows


def t03_purchase_order():                                   # 采购订单看板：图在尾
    p = page({"t20": [C("JNumber", 0, 0, 8, 12, "a"), C("JNumber", 8, 0, 8, 12, "b"),
                      C("JLine", 16, 0, 8, 28, "c")]})
    assert B._normalize_rows(p) is True
    check_even(p, "t03")
    assert [r[4] for r in layout_of(p)] == [["JNumber", "JNumber"], ["JLine"]], layout_of(p)


def t04_finance_two_blocks():                               # 财务收支看板：双混排块
    p = page({"t37": [C("JNumber", 0, 0, 6, 12, "a"), C("JNumber", 6, 0, 6, 12, "b"),
                      C("JLine", 12, 0, 12, 28, "c"), C("JPivotTable", 0, 28, 24, 32, "d")],
              "t43": [C("JNumber", 0, 60, 6, 12, "e"), C("JNumber", 6, 60, 6, 12, "f"),
                      C("JLine", 12, 60, 12, 28, "g"), C("JPivotTable", 0, 88, 24, 32, "h")]})
    assert B._normalize_rows(p) is True
    check_even(p, "t04")
    rows = layout_of(p)
    assert [r[4] for r in rows] == [["JNumber", "JNumber"], ["JLine"], ["JPivotTable"],
                                    ["JNumber", "JNumber"], ["JLine"], ["JPivotTable"]], rows
    # 原来 y=56..60 有 4 行断层，归一后必须首尾相接
    assert [r[0] for r in rows] == [0, 12, 40, 72, 84, 112], rows


def t05_sales_stats():                                      # 销售订单统计：两行混排
    p = page({"t07": [C("JNumber", 0, 0, 6, 12, "a"), C("JNumber", 6, 0, 6, 12, "b"),
                      C("JLine", 12, 0, 12, 28, "c"),
                      C("JNumber", 0, 28, 6, 12, "d"), C("JNumber", 6, 28, 6, 12, "e"),
                      C("JLine", 12, 28, 12, 28, "f"),
                      C("JPivotTable", 0, 56, 24, 32, "g")]})
    assert B._normalize_rows(p) is True
    check_even(p, "t05")
    assert [r[4] for r in layout_of(p)] == [["JNumber", "JNumber"], ["JLine"],
                                            ["JNumber", "JNumber"], ["JLine"], ["JPivotTable"]]


def t06_purchase_stats():                                   # 采购订单统计：混排在 y=32
    p = page({"t20": [C("JPivotTable", 0, 0, 24, 32, "a"),
                      C("JNumber", 0, 32, 8, 12, "b"), C("JNumber", 8, 32, 8, 12, "c"),
                      C("JLine", 16, 32, 8, 28, "d")]})
    assert B._normalize_rows(p) is True
    check_even(p, "t06")
    rows = layout_of(p)
    assert rows[0][4] == ["JPivotTable"] and rows[0][1] == WIDE_H, rows
    assert [r[4] for r in rows[1:]] == [["JNumber", "JNumber"], ["JLine"]], rows


def t07_transfer():                                         # 调拨统计：KPI + 宽表混排
    p = page({"t32": [C("JNumber", 0, 0, 8, 12, "a"), C("JPivotTable", 8, 0, 16, 32, "b"),
                      C("JNumber", 0, 32, 24, 12, "c"), C("JNumber", 0, 44, 24, 12, "d"),
                      C("JPivotTable", 0, 56, 12, 32, "e"), C("JPivotTable", 12, 56, 12, 32, "f")]})
    assert B._normalize_rows(p) is True
    check_even(p, "t07")
    rows = layout_of(p)
    # 宽表类也要拆出来 —— 断言别只判 kpi/chart 两类
    assert [r[4] for r in rows[:2]] == [["JNumber"], ["JPivotTable"]], rows
    assert rows[0][1] == KPI_H and rows[1][1] == WIDE_H, rows
    # 结论：后两行的 12/12 宽表 + 两个整行 KPI 原样保留
    assert [r[4] for r in rows[2:]] == [["JNumber"], ["JNumber"], ["JPivotTable", "JPivotTable"]]


# ── ② 判据 5（安全网）──

def t08_gate_catches_mixed():
    assert B._spec_layout_bad([C("JNumber", 0, 0, 12, 12), C("JLine", 12, 0, 12, 28)]) is not None


def t09_gate_passes_normalized():
    p = page({"f": [C("JNumber", 0, 0, 12, 12), C("JLine", 12, 0, 12, 28)]})
    B._normalize_rows(p)
    assert B._spec_layout_bad([c for c in p["charts"]["f"]]) is None


def t10_gate_exempts_buttons():
    """按钮 h=20 与图 h=28 同排：按钮必须豁免，不能判成不等高。"""
    assert B._spec_layout_bad([C("JBar", 0, 0, 12, 28)],
                              extra=[{"x": 12, "y": 0, "w": 12, "h": 20}]) is None


def t11_gate_overlap_still_first():
    """判据顺序不变：重叠仍先于等高被报出来。"""
    msg = B._spec_layout_bad([C("JNumber", 0, 0, 12, 12), C("JLine", 0, 0, 12, 28),
                              C("JBar", 12, 0, 12, 28), C("JNumber", 12, 0, 12, 12)])
    assert msg and "24" in msg, msg


# ── ③ 结构规则 ──

def t12_cross_form_one_row():
    """跨表共排：两个表单的 KPI 必须当成**同一排**归一到 24。

    按表单分开归一会各得「w 和=12≠24 → 重均分」，两个表单都占满 0..24 → 直接重叠。
    """
    p = page({"fA": [C("JNumber", 0, 20, 6, 12, "a"), C("JNumber", 6, 20, 6, 12, "b")],
              "fB": [C("JLine", 12, 20, 12, 28, "c")]})
    assert B._normalize_rows(p) is True
    check_even(p, "t12")
    rows = layout_of(p)
    assert [r[4] for r in rows] == [["JNumber", "JNumber"], ["JLine"]], rows
    # y 起点必须保住规格里的 20（首页按钮组占 y=0..20），不能归零
    assert rows[0][0] == 20, rows


def t13_skip_when_button_band_intersects():
    """图与按钮带相交 → 整页让步，坐标一个字都不动。"""
    c = C("JNumber", 0, 10, 24, 12)
    p = page({"f": [c]}, buttons=[{"x": 0, "y": 0, "w": 24, "h": 20}])
    snap = copy.deepcopy(p)
    assert B._normalize_rows(p) is False
    assert p == snap, "skipped page must be untouched: %s" % p


def t14_idempotent():
    """归一两次 ≡ 归一一次（--finalize 重跑是常态）。"""
    p = page({"t07": [C("JNumber", 0, 0, 8, 12, "a"), C("JLine", 8, 0, 8, 28, "b"),
                      C("JNumber", 16, 0, 8, 12, "c"), C("JPivotTable", 0, 28, 24, 32, "d")]})
    assert B._normalize_rows(p) is True
    once = copy.deepcopy(p)
    assert B._normalize_rows(p) is False, "second pass must be a no-op"
    assert p == once, "not idempotent"


def t15_defaults():
    """h 缺省的图 → CHART_H；KPI 排恒为 KPI_H（哪怕规格写了 JNumber 文档里的 h=17）。"""
    p = page({"f": [C("JBar", 0, 0, 24, None, "a")]})
    assert B._normalize_rows(p) is True
    assert p["charts"]["f"][0]["h"] == CHART_H, p["charts"]["f"][0]
    p2 = page({"f": [C("JNumber", 0, 0, 24, 17, "b")]})
    assert B._normalize_rows(p2) is True
    assert p2["charts"]["f"][0]["h"] == KPI_H, p2["charts"]["f"][0]
    # 顺带：h=17 单独一行会触发判据 ④（大空框）→ 归一后必须能过闸门
    assert B._spec_layout_bad([dict(p2["charts"]["f"][0])]) is None


def t16_five_kpi_chunks():
    """5 张 KPI 同行：`GRID//5`=4 不是标准档位 → 拆 4+1。"""
    p = page({"f": [C("JNumber", i * 4, 0, 4, 12, "k%d" % i) for i in range(5)]})
    assert B._normalize_rows(p) is True
    check_even(p, "t16")
    rows = layout_of(p)
    assert len(rows) == 2, rows
    assert rows[0][2] == [6, 6, 6, 6] and rows[1][2] == [24], rows


def t17_nonstandard_width():
    """非标准档位（7/9/8）→ 归到 8/8/8；宽和不足 24 同样重均分。"""
    p = page({"f": [C("JBar", 0, 0, 7, 28, "a"), C("JBar", 7, 0, 9, 28, "b"),
                    C("JBar", 16, 0, 8, 28, "c")]})
    assert B._normalize_rows(p) is True
    check_even(p, "t17")
    assert layout_of(p)[0][2] == [8, 8, 8], layout_of(p)


def t18_no_change_is_noop():
    """本来就合规的页 → 返回 False，且一个字节都不改（别误伤已建好的盘）。"""
    p = page({"f": [C("JNumber", 0, 0, 12, 12, "a"), C("JNumber", 12, 0, 12, 12, "b"),
                    C("JBar", 0, 12, 24, 28, "c")]})
    snap = copy.deepcopy(p)
    assert B._normalize_rows(p) is False
    assert p == snap


def t19_no_coords_untouched():
    """没给坐标的规格不归它管（走 _auto_tile），且不因它而报改动。"""
    p = page({"f": [C("JBar", None, None, None, None, "a")]})
    assert B._normalize_rows(p) is False


# ── ④ 回读闸门 `_verify_layout` 自证：伪造 template，证明它**真的会拦** ──
#    「全绿不是验收」对自己的闸门同样成立 —— 一个永远打 OK:排版 的核对等于没有。

class _Resp(object):
    def __init__(self, payload):
        self._p = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def read(self):
        return self._p


def _with_template(comps, fn):
    """把 `_verify_layout` 的回读换成伪造的一页 template。"""
    saved_auth, saved_open = B.AUTH, B.urllib.request.urlopen
    B.AUTH = ["http://x", "tok", "1", "2"]
    B.urllib.request.urlopen = lambda req, timeout=60: _Resp(
        {"result": {"template": json.dumps(comps, ensure_ascii=False)}})
    try:
        return fn()
    finally:
        B.AUTH, B.urllib.request.urlopen = saved_auth, saved_open


def T(comp, x, y, w, h, title=""):
    """真机 template 里的组件（键是 `component`，不是规格里的 `comp`）。"""
    return {"component": comp, "x": x, "y": y, "w": w, "h": h,
            "config": {"option": {"title": {"text": title or comp}}}}


def _verify(comps):
    return _with_template(comps, lambda: B._verify_layout([({"name": "P"}, 1)]))


def t20_verify_passes_clean():
    comps = [T("JText", 0, 0, 24, 10, "biaoti"),
             T("JNumber", 0, 10, 12, 12, "a"), T("JNumber", 12, 10, 12, 12, "b"),
             T("JBar", 0, 22, 24, 28, "c")]
    checked, issues, rf = _verify(comps)
    assert checked == 1 and not issues and not rf, (checked, issues, rf)


def t21_verify_catches_uneven():
    checked, issues, rf = _verify([T("JNumber", 0, 0, 12, 12, "a"), T("JBar", 12, 0, 12, 28, "c")])
    assert len(issues) == 1 and "高度不一致" in issues[0], issues


def t22_verify_catches_overlap():
    checked, issues, rf = _verify([T("JBar", 0, 0, 12, 28, "a"), T("JBar", 12, 0, 12, 28, "b"),
                                   T("JNumber", 0, 0, 12, 12, "c")])
    assert len(issues) == 1 and "重叠" in issues[0], issues


def t23_verify_catches_hole():
    checked, issues, rf = _verify([T("JBar", 0, 0, 24, 28, "a"), T("JBar", 0, 40, 24, 28, "b")])
    assert len(issues) == 1 and "开天窗" in issues[0], issues


def t24_verify_exempts_button():
    """按钮与图并排不该被报成不等高（与判据 5 同一豁免）。"""
    checked, issues, rf = _verify([T("JBar", 0, 0, 12, 28, "a"),
                                   T("JCustomButton", 12, 0, 12, 20, "btn")])
    assert checked == 1 and not issues, issues


TESTS = [
    ("t01", "accident/stock: JBar28+JNumber12 same row -> split", t01_stock),
    ("t02", "accident/sales-order: KPI-line-KPI sandwich -> split", t02_sales_order),
    ("t03", "accident/purchase-order: line at tail -> split", t03_purchase_order),
    ("t04", "accident/finance: two mixed blocks, y re-flowed", t04_finance_two_blocks),
    ("t05", "accident/sales-stats: two mixed rows", t05_sales_stats),
    ("t06", "accident/purchase-stats: mixed row at y=32", t06_purchase_stats),
    ("t07", "accident/transfer: KPI + wide-pivot mixed", t07_transfer),
    ("t08", "gate#5: catches un-normalized mixed row", t08_gate_catches_mixed),
    ("t09", "gate#5: passes normalized row", t09_gate_passes_normalized),
    ("t10", "gate#5: button beside chart NOT flagged", t10_gate_exempts_buttons),
    ("t11", "gate: overlap still reported before evenness", t11_gate_overlap_still_first),
    ("t12", "cross-form row normalized as ONE row, y origin kept", t12_cross_form_one_row),
    ("t13", "chart x button band -> whole page skipped, untouched", t13_skip_when_button_band_intersects),
    ("t14", "idempotent", t14_idempotent),
    ("t15", "defaults: chart->CHART_H, KPI row->KPI_H", t15_defaults),
    ("t16", "5 KPIs in a row -> 4+1", t16_five_kpi_chunks),
    ("t17", "non-standard widths -> 8/8/8", t17_nonstandard_width),
    ("t18", "already-valid page -> no change, byte-identical", t18_no_change_is_noop),
    ("t19", "specs without coords untouched", t19_no_coords_untouched),
    ("t20", "verify: clean page -> no issue", t20_verify_passes_clean),
    ("t21", "verify: catches uneven row", t21_verify_catches_uneven),
    ("t22", "verify: catches overlap", t22_verify_catches_overlap),
    ("t23", "verify: catches hole", t23_verify_catches_hole),
    ("t24", "verify: button beside chart NOT flagged", t24_verify_exempts_button),
]


def main():
    out = []
    for tid, desc, fn in TESTS:
        run(tid, desc, fn)
        sys.stdout.flush()
    if FAILED:
        io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "_test_build_dashboards.fail.txt"), "w",
                encoding="utf-8").write("\n".join(FAILED))
        print("\nFAILED %d / %d (details -> _test_build_dashboards.fail.txt)"
              % (len(FAILED), len(TESTS)))
        return 1
    print("\nALL OK (%d tests, no network)" % len(TESTS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
