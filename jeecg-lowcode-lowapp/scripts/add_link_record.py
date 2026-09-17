#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给已有工作表【新增】关联记录字段（多条/单条 + 卡片/下拉/表格 + 筛选条件 + 可选记录范围）。

给 AI：这是「已有主表新增关联记录字段」的唯一入口。
用户点名了 租户/应用/工作表/目标工作表/显示方式(/筛选) 后，
Write utf-8 job.json，一条命令跑本脚本。不要手写 LINK_RECORD/filters/sqParam 编码。
Windows 中文必须走 --config 文件，不要 PowerShell --json、不要 python -c。

  python add_link_record.py --api-base <URL> --token <TOKEN> --config job.json

job.json：
{
  "tenantName": "八匹狼",                // 或 tenantId
  "appName": "采购申请",                  // 主表所在应用（或 appId）
  "worksheet": "采购申请单",              // 已有主表工作表名（或 code=desformCode）
  "field": "审批流程模板",                // 新关联字段名；缺省=目标工作表名
  "mode": "多条",                        // 单条/多条 或 single/many（默认 single）
  "display": "卡片",                     // 卡片/下拉/表格 或 card/select/table（默认 card）
  "target": {                            // 目标表；给 targetCode 可只写这一个
    "appName": "流程审批",
    "worksheet": "审批流程模板"
  },
  "showFields": ["流程类型"],             // 可选：额外展示的源表字段（中文名）
  "dataSelectAuth": "全部",              // 可选：全部 / 仅可选择有查看权限的记录 (read/all)
  "filterMatchType": "AND",              // 可选：AND / OR
  "filters": [                           // 可选：设置筛选条件
    {"field": "流程类型", "rule": "等于", "value": "采购审批"},
    {"field": "状态", "rule": "不等于", "valueType": "字段", "value": "本表字段中文名"}
  ]
}

筛选 rule 中文：等于/不等于/大于/大于等于/小于/小于等于/开头是/结尾是/包含/不包含/为空/不为空/是其中一个
valueType 缺省 fixed(固定值)；写「字段」时 value=本表(主表)字段中文名。

自关联（自己关联自己 = 自关联树/表单数据树，2026-09-04 用户确认）：当 target 工作表 == 主表自身时，
脚本自动按自关联树处理 —— LINK_RECORD 传 is_self=True：控件顶层写 isSelf:true、valueSplit 置空。
没有 isSelf 时系统不认「自己关联自己」，无下级/子树能力（同表单普通下拉 ≠ 自关联树）。
自关联树建议 mode=单条(一条记录一个父节点) + display=卡片(可展开下级)；下拉亦可(数据量大配合搜索)。
结构细节见 references/desform-self-tree.md，禁止手写。

⚠ 双向关联（twoWay）不在本脚本 v1 范围：doc 需先建目标表反向字段再互相填 twoWayModel。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from desform_lowapp_utils import init_lowapp, get_apps, get_menus  # noqa: E402
from desform_utils import query_form, get_form_fields, add_widget, LINK_RECORD  # noqa: E402
from lowapp_creator import list_current_tenants  # noqa: E402
import update_link_record as ulr  # noqa: E402  复用: match_one/load_config/walk_nodes/build_filter_rule/resolve_field

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

MODE_MAP = {"单条": "single", "多条": "many", "single": "single", "many": "many"}
SHOW_MAP = {"卡片": "card", "下拉": "select", "表格": "table", "card": "card", "select": "select", "table": "table"}
AUTH_MAP = {
    "read": "read", "all": "all",
    "有查看权限": "read", "仅可选择有查看权限的记录": "read", "查看权限": "read",
    "全部": "all",
}


def resolve_app_worksheet(api_base, token, tenant_id, cfg_app, cfg_ws):
    """在指定应用下按名找工作表 → (app_id, desformCode)"""
    app_id = cfg_app.get("appId") or cfg_app.get("app_id") or cfg_app.get("id")
    if not app_id:
        init_lowapp(api_base, token, tenant_id=tenant_id)
        apps = get_apps(tenant_id=tenant_id).get("apps") or []
        app = ulr.match_one(apps, cfg_app.get("appName") or cfg_app.get("app"), "appName", ("应用",), "应用")
        app_id = app["id"]
    init_lowapp(api_base, token, tenant_id=tenant_id, app_id=app_id)
    code = (cfg_app.get("code") or {}).get("desformCode") if isinstance(cfg_app.get("code"), dict) else cfg_app.get("code")
    if not code:
        menus = [m for m in (get_menus().get("menuList") or []) if m.get("type") == "form"]
        ws = ulr.match_one(menus, cfg_ws, "menuName", ("工作表", "表单"), "工作表")
        code = ws.get("desformCode")
        if not code:
            raise SystemExit(f"工作表「{cfg_ws}」没有 desformCode")
    return app_id, code


def first_title_field(design_widgets):
    """目标表标题字段 model：优先 design.config.titleField，否则取第一个有 model 的控件"""
    cfg = (design_widgets and design_widgets.get("config")) or {}
    tf = cfg.get("titleField") or cfg.get("title_field")
    nodes = []
    ulr.walk_nodes(design_widgets, nodes)
    if not nodes:
        raise SystemExit("目标工作表设计为空，无法确定标题字段")
    by_model = {w.get("model"): w for w in nodes}
    if tf and tf in by_model:
        return tf, by_model[tf].get("name")
    first = nodes[0]
    return first.get("model"), first.get("name")


def main():
    p = argparse.ArgumentParser(description="已有工作表新增关联记录字段（一次提交）")
    p.add_argument("--api-base", required=True)
    p.add_argument("--token", required=True)
    p.add_argument("--config", required=True, help="utf-8 job.json，或 - 表示 stdin")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    cfg = ulr.load_config(args.config)

    api_base = args.api_base.rstrip("/")
    token = args.token
    tenant_id = cfg.get("tenantId") or cfg.get("tenant_id")
    tenant_name = cfg.get("tenantName") or cfg.get("tenant")
    if tenant_id in (None, ""):
        tenants = list_current_tenants(api_base, token)
        t = ulr.match_one(tenants, tenant_name, "name", ("租户", "组织"), "租户")
        tenant_id = t["id"]

    # 目标表（先解析，需要它在设计器里真实存在）
    tg = cfg.get("target") or {}
    tg_code = tg.get("code") or tg.get("desformCode") or cfg.get("targetCode")
    target_form = None
    if tg_code:
        target_form = query_form(tg_code)
        if not target_form:
            raise SystemExit(f"未找到目标工作表 {tg_code}")
        target_app_id = cfg.get("targetAppId") or tg.get("appId")
        if not target_app_id:
            init_lowapp(api_base, token, tenant_id=tenant_id)
            apps = get_apps(tenant_id=tenant_id).get("apps") or []
            app = ulr.match_one(apps, tg.get("appName") or cfg.get("targetAppName"), "appName", ("应用",), "目标应用")
            target_app_id = app["id"]
    else:
        target_app_id, tg_code = resolve_app_worksheet(
            api_base, token, tenant_id,
            {"appId": cfg.get("targetAppId") or tg.get("appId"), "appName": tg.get("appName") or cfg.get("targetAppName")},
            tg.get("worksheet") or cfg.get("targetWorksheet") or cfg.get("targetForm"),
        )
        target_form = query_form(tg_code)
        if not target_form:
            raise SystemExit(f"未找到目标工作表 {tg_code}")

    # 主表
    m_app = {"appId": cfg.get("appId") or cfg.get("app_id"), "appName": cfg.get("appName") or cfg.get("app")}
    master_app_id, master_code = resolve_app_worksheet(
        api_base, token, tenant_id, m_app, cfg.get("worksheet") or cfg.get("form"))
    master_form = query_form(master_code)
    if not master_form:
        raise SystemExit(f"未找到主表工作表 {master_code}")

    # 自己关联自己 = 自关联树：目标表与主表同一张表 → LINK_RECORD is_self=True
    # (顶层 isSelf:true + valueSplit 置空)。缺 isSelf 时系统不认自关联，无下级/子树能力。
    is_self = (tg_code == master_code)

    # ---- 源表(目标)字段 + 主表字段索引 ----
    source_nodes = []
    ulr.walk_nodes(json.loads(target_form["desformDesignJson"]), source_nodes)
    master_nodes = []
    ulr.walk_nodes(json.loads(master_form["desformDesignJson"]), master_nodes)
    title_model, title_name = first_title_field(json.loads(target_form["desformDesignJson"]))

    field_name = cfg.get("field") or cfg.get("name") or cfg.get("worksheet") or tg.get("worksheet") or tg_code
    mode = MODE_MAP.get(str(cfg.get("mode") or "single").strip()) or MODE_MAP.get(str(cfg.get("mode") or "").lower())
    if not mode:
        raise SystemExit(f"mode 只能是 单条/多条 或 single/many，收到 {cfg.get('mode')}")
    show_type = SHOW_MAP.get(str(cfg.get("display") or cfg.get("showType") or "card").strip()) \
        or SHOW_MAP.get(str(cfg.get("display") or cfg.get("showType") or "").lower())
    if not show_type:
        raise SystemExit(f"display 只能是 卡片/下拉/表格 或 card/select/table，收到 {cfg.get('display')}")
    auth_raw = cfg.get("dataSelectAuth")
    auth = "all"
    if auth_raw not in (None, ""):
        auth = AUTH_MAP.get(str(auth_raw).strip()) or AUTH_MAP.get(str(auth_raw).lower())
        if not auth:
            raise SystemExit(f"dataSelectAuth 只能是 read/all 或 有查看权限/全部，收到 {auth_raw}")

    if cfg.get("twoWay") or cfg.get("twoWayModel"):
        raise SystemExit("v1 不支持 twoWay 双向关联：需先建目标表反向关联再互填 twoWayModel，请拆两次处理")

    filters = None
    if cfg.get("filters") is not None:
        match_type = str(cfg.get("filterMatchType") or cfg.get("matchType") or "AND").upper()
        if match_type not in ("AND", "OR"):
            raise SystemExit("filterMatchType 只能是 AND / OR")
        rules = [ulr.build_filter_rule(it, source_nodes, master_nodes) for it in cfg["filters"]]
        filters = [{"matchType": match_type, "rules": rules}]

    show_fields = []
    for s in cfg.get("showFields") or []:
        w = ulr.resolve_field(s, source_nodes)
        if w.get("model") != title_model:
            show_fields.append(w["model"])

    summary = {
        "tenantId": tenant_id,
        "masterAppId": master_app_id,
        "masterCode": master_code,
        "field": field_name,
        "targetAppId": target_app_id,
        "targetCode": tg_code,
        "isSelf": is_self,
        "titleField": title_model,
        "showMode": mode,
        "showType": show_type,
        "dataSelectAuth": auth,
        "filters": filters,
    }
    if args.dry_run:
        print(json.dumps({"success": True, "dryRun": True, **summary}, ensure_ascii=False, indent=2))
        return 0

    ws, k, m = LINK_RECORD(field_name, tg_code, title_model,
                           show_fields=show_fields or None,
                           show_mode=mode, show_type=show_type,
                           data_select_auth=auth, filters=filters,
                           is_self=is_self)
    r = add_widget(master_code, ws)
    ok = bool(r) and (not isinstance(r, dict) or r.get("success", True))
    out = {"success": ok, **summary, "key": k, "model": m, "result": r}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if not ok:
        return 1
    if is_self:
        print("[hint] 目标表=主表自身 → 已按「自关联树」处理: 顶层 isSelf=true, valueSplit=''；"
              "记录页/设计器以卡片展示父记录、可展开/添加下级，非普通下拉。")

    # 回查
    _, fields = get_form_fields(master_code)
    nf = fields.get(field_name)
    print(f"[verify] 主表现有字段数 {len(fields)}；新增字段:",
          json.dumps({field_name: nf}, ensure_ascii=False))
    if not nf:
        print("[verify] 警告：get_form_fields 未看到新字段，请在设计器里人工确认")
    return 0


if __name__ == "__main__":
    sys.exit(main())
