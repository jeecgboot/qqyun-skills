#!/usr/bin/env python3
"""JeecgBoot 低代码应用（lowApp）通用脚本。

只从命令行读取连接信息，只从 JSON 读取业务参数。禁止在本文件写死
api-base / token / tenant-id。

用法:
  python lowapp_creator.py --api-base <URL> --token <TOKEN> --tenant-id <TID> --json '{"action":"create","appName":"xx"}'
  python lowapp_creator.py --api-base <URL> --token <TOKEN> --tenant-name <租户名> --config <cfg.json>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdin.reconfigure(encoding='utf-8')
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from desform_lowapp_utils import (
    init_lowapp,
    get_apps,
    create_app,
    edit_app,
    copy_app,
    star_app,
    delete_app,
)
from desform_utils import _urlopen

# 用户没传时由本脚本补上（不改原来的 desform_lowapp_utils.py）
_DEFAULT_APP_NAME = '未命名应用'
_DEFAULT_ICON_TYPE = 'ant-design:schedule-outlined'
_DEFAULT_ICON_BACK_COLOR = 'rgb(0, 188, 212)'
_DEFAULT_APP_COVER_IMG = 'coverImage002'


def load_config(path: str | None, raw: str | None) -> dict:
    if raw:
        return json.loads(raw)
    if not path:
        raise ValueError('必须提供 --json 或 --config')
    if path == '-':
        raw = sys.stdin.buffer.read()
        for enc in ('utf-8-sig', 'utf-8', 'gbk'):
            try:
                return json.loads(raw.decode(enc))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        raise ValueError('无法按 utf-8/gbk 解析 stdin JSON')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def dump(ok: bool, action: str, result=None, message: str | None = None) -> None:
    out = {'success': ok, 'action': action}
    if result is not None:
        out['result'] = result
    if message:
        out['message'] = message
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if not ok:
        sys.exit(1)


def require_id(cfg: dict) -> str:
    app_id = cfg.get('id') or cfg.get('appId')
    if not app_id:
        raise ValueError('JSON 必须提供 id')
    return str(app_id)


def list_current_tenants(api_base, token):
    """查当前用户租户。不要走 get_tenants()：init_api 默认 X-Tenant-Id=1，会 401「登录租户授权变更」。"""
    req = urllib.request.Request(
        api_base.rstrip('/') + '/sys/tenant/getCurrentUserTenant',
        headers={
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json',
            'X-Access-Token': token,
            'Connection': 'close',
        },
        method='GET',
    )
    with _urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode('utf-8'))
    return payload.get('result', {}).get('list') or []


def resolve_tenant_id(tenant_id, tenant_name, api_base=None, token=None):
    """有租户 ID 直接用；只有名称时先查租户精确匹配再操作。"""
    if tenant_id not in (None, ''):
        return tenant_id
    name = (tenant_name or '').strip()
    if not name:
        raise ValueError('必须提供 --tenant-id 或租户名称（--tenant-name / JSON tenantName）')
    if not api_base or not token:
        raise ValueError('按名称查租户时必须提供 api_base 和 token')
    tenants = list_current_tenants(api_base, token)
    exact = [t for t in tenants if str(t.get('name') or '').strip() == name]
    if len(exact) == 1:
        return exact[0]['id']
    if len(exact) > 1:
        raise ValueError(f'多个租户同名: {name}')
    listing = ', '.join(f"{t.get('id')}={t.get('name')}" for t in tenants) or '(空)'
    raise ValueError(f'未找到租户: {name}；当前用户租户: {listing}')


def resolve_app_id(cfg: dict, tenant_id) -> str:
    """有 id 直接用；只有 fromName 时在本进程内查列表再改，避免来回两次命令。"""
    app_id = cfg.get('id') or cfg.get('appId')
    if app_id:
        return str(app_id)
    from_name = provided(cfg, 'fromName') or provided(cfg, 'oldName')
    if not from_name:
        raise ValueError('JSON 必须提供 id 或 fromName')
    matched = [a for a in get_apps(tenant_id=tenant_id).get('apps', [])
               if a.get('appName') == from_name]
    if len(matched) == 1:
        return str(matched[0]['id'])
    if not matched:
        raise ValueError(f'未找到应用: {from_name}')
    raise ValueError(f'找到多个同名应用，请传 id: {from_name}')


def provided(cfg: dict, key: str):
    """用户 JSON 里写了且非空才返回值，否则 None（让函数走写死的默认值）。"""
    val = cfg.get(key)
    if val is None or val == '':
        return None
    return val


def run(action: str, cfg: dict, tenant_id) -> None:
    if action == 'create':
        app_name = provided(cfg, 'appName') or _DEFAULT_APP_NAME
        app_id = create_app(
            tenant_id=tenant_id,
            app_name=app_name,
            icon_type=provided(cfg, 'iconType') or _DEFAULT_ICON_TYPE,
            icon_back_color=provided(cfg, 'iconBackColor') or _DEFAULT_ICON_BACK_COLOR,
            app_cover_img=provided(cfg, 'appCoverImg') or _DEFAULT_APP_COVER_IMG,
        )
        dump(True, action, result={'id': app_id, 'appName': app_name})
        return

    if action == 'copy':
        source_id = require_id(cfg)
        new_id = copy_app(source_id)
        dump(True, action, result={'id': new_id, 'sourceId': source_id})
        return

    if action == 'delete':
        app_id = require_id(cfg)
        ok = delete_app(app_id)
        dump(bool(ok), action, result={'id': app_id}, message=None if ok else '删除失败')
        return

    if action == 'edit':
        app_id = resolve_app_id(cfg, tenant_id)
        ok = edit_app(
            app_id,
            app_name=cfg.get('appName'),
            icon_type=cfg.get('iconType'),
            icon_back_color=cfg.get('iconBackColor'),
            app_cover_img=cfg.get('appCoverImg'),
        )
        dump(bool(ok), action, result={'id': app_id, 'appName': cfg.get('appName')},
             message=None if ok else '修改失败')
        return

    if action == 'star':
        app_id = require_id(cfg)
        star = cfg.get('starStatus', 1)
        ok = star_app(app_id, star=bool(int(star)))
        dump(bool(ok), action, result={'id': app_id, 'starStatus': int(star)})
        return

    if action == 'list':
        data = get_apps(tenant_id=tenant_id)
        apps = [
            {
                'id': a.get('id'),
                'appName': a.get('appName'),
                'iconType': a.get('iconType'),
                'iconBackColor': a.get('iconBackColor'),
                'appCoverImg': a.get('appCoverImg'),
                'tenantId': a.get('tenantId'),
            }
            for a in data.get('apps', [])
        ]
        dump(True, action, result={'apps': apps, 'count': len(apps)})
        return

    raise ValueError(f'不支持的 action: {action}（create/copy/delete/edit/star/list）')


def main() -> None:
    parser = argparse.ArgumentParser(description='JeecgBoot lowApp 应用管理')
    parser.add_argument('--api-base', required=True, help='由用户提供的后端地址')
    parser.add_argument('--token', required=True, help='由用户提供的 X-Access-Token')
    parser.add_argument('--tenant-id', default=None, help='由用户提供的租户 ID')
    parser.add_argument('--tenant-name', default=None, help='由用户提供的租户名称（无 ID 时先查询再操作）')
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument('--json', help='业务 JSON 字符串（推荐，一条命令完成，不要写临时文件）')
    src.add_argument('--config', help='业务 JSON 路径，或 - 表示 stdin')
    args = parser.parse_args()

    cfg = load_config(args.config, args.json)
    action = (cfg.get('action') or '').strip()
    if not action:
        dump(False, '', message='JSON 必须包含 action')
        return

    tenant_name = args.tenant_name or cfg.get('tenantName')
    if not args.tenant_id and not tenant_name:
        dump(False, action, message='必须提供租户 ID 或租户名称')
        return

    try:
        if args.tenant_id:
            tenant_id = args.tenant_id
        else:
            tenant_id = resolve_tenant_id(None, tenant_name, args.api_base, args.token)
        init_lowapp(args.api_base, args.token, tenant_id=tenant_id)
        run(action, cfg, tenant_id)
    except Exception as e:
        dump(False, action, message=str(e))


if __name__ == '__main__':
    main()
