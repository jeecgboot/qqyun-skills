#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""敲敲云（lowApp）应用级数据字典脚本。

应用级字典不是全局 /sys/dict 的普通字典，必须携带 x-tenant-id 和 x-low-app-id。
接口：
  GET  /sys/dict/getDictListByLowAppId    查询当前应用字典
  POST /sys/dict/addDictByLowAppId        新增，后端自动生成 10 位 dictCode
  PUT  /sys/dict/editDictByLowAppId       编辑
  DELETE /sys/dict/delete?id=...          删除

用法：
  python lowapp_dict.py --api-base <URL> --token <TOKEN> \
      --tenant-id <TENANT_ID> --app-id <APP_ID> --action query

  python lowapp_dict.py ... --action add --config dict_job.json
  python lowapp_dict.py ... --action edit --config dict_job.json
  python lowapp_dict.py ... --action delete --id <DICT_ID>

dict_job.json（add）：
{
  "dictName": "性别",
  "dictItemsList": [
    {"itemText": "男", "itemValue": "0", "itemColor": "#2196F3", "sortOrder": 1},
    {"itemText": "女", "itemValue": "1", "itemColor": "#FF9300", "sortOrder": 2}
  ]
}

edit 时增加 "id": "<字典ID>"。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from desform_lowapp_utils import init_lowapp  # noqa: E402
from desform_utils import api_request  # noqa: E402

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


VALID_ITEM_COLORS = [
    "#2196F3",
    "#08C9C9",
    "#00C345",
    "#FAD714",
    "#FF9300",
    "#F52222",
    "#EB2F96",
    "#7500EA",
    "#2D46C4",
    "#484848",
    "#C9E6FC",
    "#C3F2F2",
    "#C2F1D2",
    "#FEF6C6",
    "#FFE5C2",
    "#FDCACA",
    "#FACDE6",
    "#DEC2FA",
    "#CCD2F1",
    "#D3D3D3",
]


def load_config(path):
    if path == "-":
        return json.load(sys.stdin)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_items(items):
    """补齐字典项字段，保证 itemValue 未填时从 0 递增，itemColor 未填时自动分配合法颜色。"""
    result = []
    for i, it in enumerate(items or []):
        if not isinstance(it, dict):
            it = {"itemText": str(it), "itemValue": str(i), "sortOrder": i + 1}
        else:
            it = dict(it)
        if not it.get("itemValue"):
            it["itemValue"] = str(i)
        it.setdefault("sortOrder", i + 1)
        if it.get("itemColor"):
            if it["itemColor"] not in VALID_ITEM_COLORS:
                raise SystemExit(
                    f"非法字典项颜色 {it['itemColor']}；仅支持以下 20 色: "
                    + ", ".join(VALID_ITEM_COLORS)
                )
        else:
            it["itemColor"] = VALID_ITEM_COLORS[i % len(VALID_ITEM_COLORS)]
        result.append(it)
    return result


def main():
    p = argparse.ArgumentParser(description="敲敲云应用级数据字典管理")
    p.add_argument("--api-base", required=True)
    p.add_argument("--token", required=True)
    p.add_argument("--tenant-id", required=True)
    p.add_argument("--app-id", required=True)
    p.add_argument("--action", required=True, choices=["query", "add", "edit", "delete"])
    p.add_argument("--config", help="UTF-8 JSON 配置路径，或 - 表示 stdin")
    p.add_argument("--id", help="编辑/删除时使用，也可写进 config")
    args = p.parse_args()

    api_base = args.api_base.rstrip("/")
    token = args.token
    init_lowapp(api_base, token, tenant_id=int(args.tenant_id), app_id=args.app_id)

    action = args.action
    if action == "query":
        r = api_request("/sys/dict/getDictListByLowAppId", method="GET")
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if r.get("success") else 1

    if action == "delete":
        dict_id = args.id
        if not dict_id:
            cfg = load_config(args.config)
            dict_id = cfg.get("id")
        if not dict_id:
            raise SystemExit("delete 需要 --id 或 config.id")
        r = api_request("/sys/dict/delete", params={"id": str(dict_id)}, method="DELETE")
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if r.get("success") else 1

    if not args.config:
        raise SystemExit(f"{action} 需要 --config")
    cfg = load_config(args.config)
    payload = {
        "dictName": cfg.get("dictName"),
        "dictItemsList": normalize_items(cfg.get("dictItemsList")),
    }
    if not payload["dictName"]:
        raise SystemExit("config.dictName 不能为空")
    if args.id:
        payload["id"] = str(args.id)
    elif action == "edit" and cfg.get("id"):
        payload["id"] = str(cfg["id"])
    if action == "edit" and not payload.get("id"):
        raise SystemExit("edit 需要 --id 或 config.id")

    path = "/sys/dict/addDictByLowAppId" if action == "add" else "/sys/dict/editDictByLowAppId"
    method = "POST" if action == "add" else "PUT"
    r = api_request(path, data=payload, method=method)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    if r.get("success"):
        print("[当前应用字典列表]")
        q = api_request("/sys/dict/getDictListByLowAppId", method="GET")
        print(json.dumps(q, ensure_ascii=False, indent=2))
    return 0 if r.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
