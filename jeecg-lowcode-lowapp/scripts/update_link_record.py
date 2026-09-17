#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""改已有关联记录：显示方式 / 记录范围 / 查看权限 / 默认值 / 查询工作表。

给 AI：不要手写 update_widget + 猜 filters/sqParam/linkage 编码。
用户点名了工作表 + 关联记录字段后，Write utf-8 job.json，一条命令跑本脚本。
Windows 中文必须走 --config 文件，不要 PowerShell --json、不要 python -c。

  python update_link_record.py --api-base <URL> --token <TOKEN> --config job.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from urllib.parse import quote

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from desform_lowapp_utils import init_lowapp, get_apps, get_menus  # noqa: E402
from desform_utils import query_form, update_widget, save_design_from_file  # noqa: E402
from lowapp_creator import list_current_tenants  # noqa: E402

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SYS_FIELDS = {
    "创建人": ("create_by", "select-user"),
    "创建者": ("create_by", "select-user"),
    "create_by": ("create_by", "select-user"),
    "创建时间": ("create_time", "datetime"),
    "create_time": ("create_time", "datetime"),
    "修改人": ("update_by", "select-user"),
    "update_by": ("update_by", "select-user"),
    "修改时间": ("update_time", "datetime"),
    "update_time": ("update_time", "datetime"),
}

SHOW_TYPE = {"下拉": "select", "卡片": "card", "表格": "table", "select": "select", "card": "card", "table": "table"}
AUTH = {
    "read": "read",
    "all": "all",
    "有查看权限": "read",
    "仅可选择有查看权限的记录": "read",
    "查看权限": "read",
    "全部": "all",
}
VAL_TYPE = {
    "none": "none",
    "first": "first",
    "无": "none",
    "第一条": "first",
    "第一条数据": "first",
}
FILTER_RULE = {
    "开头是": "BEFORE", "before": "BEFORE", "right_like": "BEFORE",
    "结尾是": "AFTER", "after": "AFTER", "left_like": "AFTER",
    "等于": "EQ", "eq": "EQ",
    "不等于": "NE", "ne": "NE",
    "大于": "GT", "gt": "GT",
    "大于等于": "GE", ">=": "GE", "gte": "GE", "ge": "GE",
    "小于": "LT", "lt": "LT",
    "小于等于": "LE", "<=": "LE", "lte": "LE", "le": "LE",
    "包含": "IN", "in": "IN", "like": "IN",
    "不包含": "NOT_IN", "not_in": "NOT_IN", "not_like": "NOT_IN",
    "为空": "EMPTY", "empty": "EMPTY",
    "不为空": "NOT_EMPTY", "not_empty": "NOT_EMPTY",
    "是其中一个": "IS_ONE_OF",
    "不是其中一个": "NOT_IS_ONE_OF",
}
FILTER_SQ = {
    "EQ": "eq", "NE": "ne", "GT": "gt", "GE": "ge", "LT": "lt", "LE": "le",
    "IN": "like", "NOT_IN": "not_like",
    "BEFORE": "right_like", "AFTER": "left_like",
    "EMPTY": "empty", "NOT_EMPTY": "not_empty",
    "IS_ONE_OF": "in", "NOT_IS_ONE_OF": "not_in",
    "IN_ONE_OF": "in", "NOT_IN_ONE_OF": "not_in",
    "DATE_LT": "lt", "DATE_LE": "le", "DATE_GT": "gt", "DATE_GE": "ge",
}
LINKAGE_RULE = {
    "等于": "eq", "eq": "eq",
    "不等于": "ne", "ne": "ne",
    "大于": "gt", "gt": "gt",
    "大于等于": "gte", "gte": "gte", "ge": "gte", ">=": "gte",
    "小于": "lt", "lt": "lt",
    "小于等于": "lte", "lte": "lte", "le": "lte", "<=": "lte",
    "包含": "like", "like": "like",
    "开头是": "right_like", "right_like": "right_like",
    "结尾是": "left_like", "left_like": "left_like",
}
LINKAGE_OPER = {
    "CUSTOM_SORT": "CUSTOM_SORT", "自定义排序": "CUSTOM_SORT",
    "FIRST": "FIRST", "最新": "FIRST", "最新一条": "FIRST",
    "LAST": "LAST", "最老": "LAST", "最老一条": "LAST",
    "COUNT": "COUNT", "IGNORE": "IGNORE",
}
COMPRESS_KEYS = {
    "appId": "aid", "desformCode": "fCode", "matchType": "mType",
    "operation": "oper", "linkModel": "lModel", "valueType": "vType",
}


def load_config(path):
    if path == "-":
        raw = sys.stdin.buffer.read()
        for enc in ("utf-8-sig", "utf-8", "gbk"):
            try:
                return json.loads(raw.decode(enc))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        raise SystemExit("无法解析 stdin JSON")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def match_one(items, raw, name_key, suffixes, label):
    raw = (raw or "").strip()
    if not raw:
        raise SystemExit(f"缺少{label}")
    exact = [x for x in items if str(x.get(name_key) or "").strip() == raw]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise SystemExit(f'{label}「{raw}」匹配到多条: {", ".join(str(x.get(name_key)) for x in exact)}')
    stripped = raw
    for s in suffixes:
        if stripped.endswith(s) and len(stripped) > len(s):
            stripped = stripped[: -len(s)]
            break
    if stripped != raw:
        exact2 = [x for x in items if str(x.get(name_key) or "").strip() == stripped]
        if len(exact2) == 1:
            return exact2[0]
        if len(exact2) > 1:
            raise SystemExit(f'{label}「{stripped}」匹配到多条')
    listing = ", ".join(f"{x.get('id')}={x.get(name_key)}" for x in items) or "(空)"
    raise SystemExit(f"未找到{label}: {raw}；现有: {listing}")


def walk_nodes(node, acc):
    if isinstance(node, dict):
        if node.get("type") and node.get("model"):
            acc.append(node)
        for v in node.values():
            walk_nodes(v, acc)
    elif isinstance(node, list):
        for i in node:
            walk_nodes(i, acc)


def field_index(widgets):
    idx = {}
    for w in widgets:
        name = (w.get("name") or "").strip()
        if name and name not in idx:
            idx[name] = w
    return idx


def resolve_field(name, widgets, *, current=False):
    raw = (name or "").strip()
    if not raw:
        raise SystemExit("条件缺少 field")
    sys_hit = SYS_FIELDS.get(raw)
    if sys_hit:
        model, typ = sys_hit
        return {"name": raw, "model": model, "type": typ, "options": {}}
    idx = field_index(widgets)
    if raw in idx:
        return idx[raw]
    stripped = raw
    for s in ("关联记录", "字段"):
        if stripped.endswith(s) and len(stripped) > len(s):
            stripped = stripped[: -len(s)]
            break
    if stripped in idx:
        return idx[stripped]
    contains = [w for n, w in idx.items() if raw in n or n in raw]
    if len(contains) == 1:
        return contains[0]
    if len(contains) > 1:
        raise SystemExit(f'字段「{raw}」匹配到多条: {", ".join(w.get("name") for w in contains)}')
    listing = ", ".join(idx.keys()) or "(空)"
    where = "本表" if current else "源表"
    raise SystemExit(f"未找到{where}字段: {raw}；现有: {listing}")


def sq_type(widget):
    t = widget.get("type") or "text"
    if t == "date":
        return (widget.get("options") or {}).get("type") or "date"
    if t == "formula":
        opts = widget.get("options") or {}
        if opts.get("type") == "date" and opts.get("mode") == "DATEADD":
            return "date"
        if opts.get("type") == "date":
            return "input"
        return "number"
    if t == "link-field":
        return (widget.get("options") or {}).get("fieldType") or "text"
    if widget.get("model") in ("create_by", "update_by"):
        return "select-user"
    if widget.get("model") in ("create_time", "update_time"):
        return "datetime"
    return t


def as_list(val):
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x) for x in val]
    return [str(val)]


def norm_filter_rule(raw):
    key = str(raw or "EQ").strip()
    if key in FILTER_SQ:
        return key
    mapped = FILTER_RULE.get(key) or FILTER_RULE.get(key.lower())
    if not mapped:
        raise SystemExit(f"未知筛选规则: {raw}；用 开头是/等于/不等于/大于/大于等于/包含/为空 或大写 EQ/NE/BEFORE/GE")
    return mapped


def find_link_record(design, field_name):
    widgets = []
    walk_nodes(design, widgets)
    links = [w for w in widgets if w.get("type") == "link-record"]
    if not links:
        raise SystemExit("该工作表没有关联记录字段")
    raw = (field_name or "").strip()
    if not raw:
        if len(links) == 1:
            return links[0]
        names = ", ".join(w.get("name") or w.get("model") for w in links)
        raise SystemExit(f"有多条关联记录，请指定 field。现有: {names}")
    exact = [w for w in links if (w.get("name") or "").strip() == raw]
    if len(exact) == 1:
        return exact[0]
    stripped = raw
    for s in ("关联记录", "字段"):
        if stripped.endswith(s) and len(stripped) > len(s):
            stripped = stripped[: -len(s)]
            break
    if stripped != raw:
        exact2 = [w for w in links if (w.get("name") or "").strip() == stripped]
        if len(exact2) == 1:
            return exact2[0]
    fuzzy = [w for w in links if raw in (w.get("name") or "") or (w.get("name") or "") in raw]
    if len(fuzzy) == 1:
        return fuzzy[0]
    if len(fuzzy) > 1:
        raise SystemExit(f'关联记录「{raw}」匹配到多条: {", ".join(w.get("name") for w in fuzzy)}')
    names = ", ".join(w.get("name") or w.get("model") for w in links)
    raise SystemExit(f"未找到关联记录: {raw}；现有: {names}")


def build_filter_rule(item, source_widgets, current_widgets):
    src = resolve_field(item.get("field") or item.get("name"), source_widgets)
    rule = norm_filter_rule(item.get("rule") or item.get("op") or "EQ")
    value_type = item.get("valueType") or "fixed"
    if value_type in ("本表", "字段"):
        value_type = "field"
    if value_type not in ("fixed", "field"):
        raise SystemExit(f"filters.valueType 只能是 fixed / field，收到 {value_type}")
    if value_type == "field":
        cur = resolve_field(item.get("value") or item.get("currentField"), current_widgets, current=True)
        value = [cur.get("model")]
        value_text = cur.get("name") or ""
    else:
        value = as_list(item.get("value"))
        if rule not in ("EMPTY", "NOT_EMPTY") and not value:
            raise SystemExit(f'筛选「{src.get("name")}」缺少 value')
        value_text = item.get("valueText")
        if value_text is None:
            value_text = ",".join(value)
    sq = FILTER_SQ.get(rule)
    if not sq:
        raise SystemExit(f"筛选规则 {rule} 没有 sqParam 映射")
    out = {
        "model": src.get("model"),
        "rule": rule,
        "valueType": value_type,
        "value": value,
        "sqParam": {"type": sq_type(src), "rule": sq},
    }
    if value_text not in (None, ""):
        out["valueText"] = value_text
    return out


def compress(obj):
    if isinstance(obj, list):
        return [compress(i) for i in obj]
    if isinstance(obj, dict):
        return {COMPRESS_KEYS.get(k, k): compress(v) for k, v in obj.items()}
    return obj


def encode_linkage(cfg):
    raw = json.dumps(compress(cfg), ensure_ascii=False, separators=(",", ":"))
    return quote(raw, safe="")


def build_linkage(link_cfg, link_widget, source_widgets, current_widgets, app_id):
    source_code = (link_widget.get("options") or {}).get("sourceCode")
    if not source_code:
        raise SystemExit("关联记录没有 sourceCode，无法查询工作表")
    match_type = str(link_cfg.get("matchType") or "AND").upper()
    if match_type not in ("AND", "OR"):
        raise SystemExit("linkage.matchType 只能是 AND / OR")
    oper_raw = link_cfg.get("operation") or "CUSTOM_SORT"
    oper = LINKAGE_OPER.get(str(oper_raw)) or LINKAGE_OPER.get(str(oper_raw).upper())
    if not oper:
        raise SystemExit(f"未知 linkage.operation: {oper_raw}")
    rules = []
    for item in link_cfg.get("rules") or []:
        src = resolve_field(item.get("field") or item.get("name"), source_widgets)
        rule = str(item.get("rule") or "eq").strip()
        rule = LINKAGE_RULE.get(rule) or LINKAGE_RULE.get(rule.lower()) or rule.lower()
        value_type = item.get("valueType") or "fixed"
        if value_type in ("本表", "字段"):
            value_type = "field"
        if value_type == "system":
            pass
        elif value_type not in ("fixed", "field"):
            raise SystemExit(f"linkage.valueType 只能是 fixed / field / system，收到 {value_type}")
        if value_type == "field":
            cur = resolve_field(item.get("value") or item.get("currentField"), current_widgets, current=True)
            value = [cur.get("model")]
        else:
            value = as_list(item.get("value"))
        rules.append({
            "model": src.get("model"),
            "rule": rule,
            "valueType": value_type,
            "value": value,
            "sqParam": {"type": sq_type(src), "rule": {"value": rule}},
        })
    if not rules:
        raise SystemExit("查询工作表至少一条 rules")
    sorts = []
    for s in link_cfg.get("sorts") or []:
        col = s.get("field") or s.get("column")
        src = resolve_field(col, source_widgets)
        order = str(s.get("order") or "asc").lower()
        if order in ("正序", "升序"):
            order = "asc"
        if order in ("倒序", "降序"):
            order = "desc"
        if order not in ("asc", "desc"):
            raise SystemExit(f"sorts.order 只能是 asc/desc，收到 {s.get('order')}")
        sorts.append({"column": src.get("model"), "order": order})
    if oper == "CUSTOM_SORT" and not sorts:
        raise SystemExit("CUSTOM_SORT 需要 sorts")
    linkages = link_cfg.get("linkages")
    if not linkages:
        linkages = [{
            "model": link_widget.get("model"),
            "linkModel": "id",
            "linkName": "id",
        }]
    return {
        "appId": str(app_id),
        "desformCode": source_code,
        "matchType": match_type,
        "operation": oper,
        "rules": rules,
        "linkages": linkages,
        "sorts": sorts,
        "isMultiple": bool(link_cfg.get("isMultiple", False)),
        "maxRecordCount": int(link_cfg.get("maxRecordCount") or 200),
    }


def main():
    p = argparse.ArgumentParser(description="改已有关联记录（显示方式/记录范围/默认值/查询工作表）")
    p.add_argument("--api-base", required=True)
    p.add_argument("--token", required=True)
    p.add_argument("--config", required=True, help="utf-8 job.json，或 - 表示 stdin")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    cfg = load_config(args.config)

    api_base = args.api_base.rstrip("/")
    token = args.token
    tenant_id = cfg.get("tenantId") or cfg.get("tenant_id")
    tenant_name = cfg.get("tenantName") or cfg.get("tenant")
    if tenant_id in (None, ""):
        tenants = list_current_tenants(api_base, token)
        t = match_one(tenants, tenant_name, "name", ("租户", "组织"), "租户")
        tenant_id = t["id"]

    app_id = cfg.get("appId") or cfg.get("app_id")
    if not app_id:
        init_lowapp(api_base, token, tenant_id=tenant_id)
        apps = get_apps(tenant_id=tenant_id).get("apps") or []
        app = match_one(apps, cfg.get("appName") or cfg.get("app"), "appName", ("应用",), "应用")
        app_id = app["id"]
    init_lowapp(api_base, token, tenant_id=tenant_id, app_id=app_id)

    code = cfg.get("code") or cfg.get("desformCode")
    if not code:
        menus = [m for m in (get_menus().get("menuList") or []) if m.get("type") == "form"]
        ws = match_one(menus, cfg.get("worksheet") or cfg.get("form"), "menuName", ("工作表", "表单"), "工作表")
        code = ws.get("desformCode")
        if not code:
            raise SystemExit("工作表没有 desformCode")

    form = query_form(code)
    if not form:
        raise SystemExit(f"未找到工作表 {code}")
    design = json.loads(form["desformDesignJson"])
    current_widgets = []
    walk_nodes(design, current_widgets)
    link = find_link_record(design, cfg.get("field") or cfg.get("linkField") or cfg.get("name"))
    key = cfg.get("key") or link.get("key")
    opts = dict(link.get("options") or {})
    source_code = opts.get("sourceCode")
    source_widgets = []
    if source_code:
        src_form = query_form(source_code)
        if src_form:
            walk_nodes(json.loads(src_form["desformDesignJson"]), source_widgets)

    changes_options = {}
    if cfg.get("showType") not in (None, ""):
        st = SHOW_TYPE.get(str(cfg["showType"])) or SHOW_TYPE.get(str(cfg["showType"]).lower())
        if not st:
            raise SystemExit(f"showType 只能是 下拉/卡片/表格 或 select/card/table，收到 {cfg['showType']}")
        changes_options["showType"] = st
    if cfg.get("dataSelectAuth") not in (None, ""):
        auth = AUTH.get(str(cfg["dataSelectAuth"])) or AUTH.get(str(cfg["dataSelectAuth"]).strip())
        if not auth:
            raise SystemExit(f"dataSelectAuth 只能是 read/all 或 有查看权限/全部，收到 {cfg['dataSelectAuth']}")
        changes_options["dataSelectAuth"] = auth
    if cfg.get("defaultValType") not in (None, ""):
        dvt = VAL_TYPE.get(str(cfg["defaultValType"])) or VAL_TYPE.get(str(cfg["defaultValType"]).strip())
        if not dvt:
            raise SystemExit(f"defaultValType 只能是 none/first 或 无/第一条数据，收到 {cfg['defaultValType']}")
        changes_options["defaultValType"] = dvt

    filters_in = cfg.get("filters")
    if filters_in is not None:
        match_type = str(cfg.get("filterMatchType") or cfg.get("matchType") or "AND").upper()
        if match_type not in ("AND", "OR"):
            raise SystemExit("filterMatchType 只能是 AND / OR")
        new_rules = [build_filter_rule(it, source_widgets, current_widgets) for it in filters_in]
        if cfg.get("appendFilters") or cfg.get("append"):
            old = ((opts.get("filters") or [{}])[0].get("rules")) or []
            keep = []
            new_models = {r["model"] for r in new_rules}
            for r in old:
                if r.get("model") not in new_models:
                    keep.append(r)
            new_rules = keep + new_rules
        changes_options["filters"] = [{"matchType": match_type, "rules": new_rules}]

    linkage_cfg = cfg.get("linkage") or cfg.get("defaultValue")
    if isinstance(linkage_cfg, dict) and (linkage_cfg.get("type") in (None, "linkage") or linkage_cfg.get("rules") is not None):
        if linkage_cfg.get("type") and linkage_cfg.get("type") != "linkage" and "rules" not in linkage_cfg:
            linkage_cfg = None
    else:
        linkage_cfg = None

    adv = None
    if linkage_cfg:
        encoded_cfg = build_linkage(linkage_cfg, link, source_widgets, current_widgets, app_id)
        encoded = encode_linkage(encoded_cfg)
        # 2026-09-02 实测修复：设计器面板/运行时只认「编码串逐字符展开的对象」，
        # 普通字符串接口 success 但面板读不到 → 必须 {str(i): ch} 形态入库
        value_obj = {str(i): ch for i, ch in enumerate(encoded)}
        adv = {
            "defaultValue": {
                "type": "linkage",
                "value": value_obj,
                "format": "string",
                "allowFunc": True,
                "valueSplit": ",",
                "customConfig": True,
            }
        }
        # 查询工作表与「第一条数据」互斥，否则 first 会抢先填值
        changes_options["defaultValType"] = "none"

    if not changes_options and not adv:
        raise SystemExit("JSON 没有可改项（showType / dataSelectAuth / defaultValType / filters / linkage）")

    payload = {}
    if changes_options:
        payload["options"] = changes_options
    if adv:
        payload["advancedSetting"] = adv

    def summarize_adv(v):
        dv = (v or {}).get("defaultValue")
        if dv is None:
            return None
        chars = dv.get("value") or {}
        head = "".join(chars.get(str(i), "") for i in range(len(chars)))[:80]
        return {"type": dv.get("type"), "value": f"<char-map {len(chars)} keys> decode-head: {head}..."}

    summary = {
        "tenantId": tenant_id,
        "appId": app_id,
        "code": code,
        "field": link.get("name"),
        "key": key,
        "sourceCode": source_code,
        "changes": {k: (summarize_adv(v) if k == "advancedSetting" else v) for k, v in payload.items()},
    }
    if args.dry_run:
        shown = json.loads(json.dumps(payload))
        ad = (shown.get("advancedSetting") or {}).get("defaultValue")
        if ad is not None:
            chars = ad.get("value") or {}
            head = "".join(chars.get(str(i), "") for i in range(len(chars)))
            ad["value"] = f"<char-map {len(chars)} keys> decode-head: {head[:80]}..."
        print(json.dumps({"success": True, "dryRun": True, **summary, "payload": shown}, ensure_ascii=False, indent=2))
        return 0

    if adv:
        # 2026-09-02 实测修复：查询工作表默认值走整单设计保存 —— update_widget 是深合并，
        # 旧 value（字符串版 / 长键残留段）删不掉会与新版叠加成脏数据
        link["options"] = {**(link.get("options") or {}), **changes_options}
        old_adv = dict(link.get("advancedSetting") or {})
        old_adv["defaultValue"] = adv["defaultValue"]
        link["advancedSetting"] = old_adv
        path = os.path.join(tempfile.gettempdir(), "jeecg-desform", f"{code}_linkage_fix.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(design, f, ensure_ascii=False)
        r = save_design_from_file(code, path)
        method = "save_design_from_file (linkage 整单保存)"
    else:
        r = update_widget(code, payload, key=key)
        method = "update_widget"
    ok = bool(r) and (not isinstance(r, dict) or r.get("success", True))
    out = {"success": ok, **summary, "method": method, "result": r}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if not ok:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
