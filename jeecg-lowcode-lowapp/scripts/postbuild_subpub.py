#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""postbuild_subpub —— subEvent 子流程补发 customProcessId（建后套件的 ⑤.5 步）

为什么需要这一步
----------------
`build_flows.py` 建出的 subEvent 子流程，记录里 `customProcessId` 是空的。
引擎拼 BPMN 定义 key 时用的是 `'process' + customProcessId`，空值就拼成坏 key `process`，
于是父流程 `callActivity` 永远找不到定义。

**症状是静默的**：`saveFlow` 成功、`deployProcess` 成功、条数对得上、
`processStatus=1`，只有 `build_flows` 的 barrier 闸门报「N/N 条子流程未注册」，
主流程一条都不建。实测 25 条子流程只会浪费掉一整轮。

本脚本对每条 `startType=subEvent` 的记录：`customProcessId=<自身DBid>` → 重存 → 重新 deploy
→ **回读 `processXml`（base64）解码核验** `<process id="process<DBid>">`。
幂等，可反复跑；25 条约 42 秒。

用法
----
    python scripts/postbuild_subpub.py --api-base URL --token T --tenant-id N --app-id A
    python scripts/postbuild_subpub.py $C --dry-run          # 只列出定义 key 不对的子流程，不保存
    python scripts/postbuild_subpub.py $C --check-only       # 只核验现状，不保存

位置：建完子流程（`build_flows.py` 第一趟、barrier 报未注册）之后、
      建父流程（`build_flows.py --force`）之前。见 `postbuild-kit.md`「二、运行顺序」。

退出码：0 = 全部核验通过；2 = 有失败项（照 `FAIL:` 行排查）；1 = 参数/列表阶段出错。
"""
from __future__ import print_function

import argparse
import base64
import json
import re
import sys
import urllib.parse
import urllib.request

LIST_PATH = '/act/process/extActProcess/list'
QUERY_PATH = '/act/process/extActProcess/queryById'
SAVE_PATH = '/act/designer/miniDesFlow/api/saveFlow'
DEPLOY_PATH = '/act/process/extActProcess/deployProcess'

PROCESS_ID_RE = re.compile(r'<process\s+id="([^"]+)"')


def make_requester(api_base, token, tenant_id, timeout):
    """返回 req(method, path, data=None, form=False) —— 与套件其它脚本同样的调用形态。"""
    base = api_base.rstrip('/')

    def req(method, path, data=None, form=False):
        headers = {'X-Access-Token': token, 'X-Tenant-Id': str(tenant_id)}
        body = None
        if data is not None:
            if form:
                body = urllib.parse.urlencode(data).encode('utf-8')
                headers['Content-Type'] = 'application/x-www-form-urlencoded'
            else:
                body = json.dumps(data, ensure_ascii=False).encode('utf-8')
                headers['Content-Type'] = 'application/json'
        rq = urllib.request.Request(base + path, data=body, headers=headers, method=method)
        raw = urllib.request.urlopen(rq, timeout=timeout).read().decode('utf-8')
        return json.loads(raw)

    return req


def list_subflows(req, app_id):
    """列出该应用下所有 startType=subEvent 的流程记录。"""
    out, page = [], 1
    while True:
        q = urllib.parse.urlencode({'lowAppId': app_id, 'pageNo': page, 'pageSize': 100})
        res = req('GET', '%s?%s' % (LIST_PATH, q))
        if not res.get('success', True) and res.get('result') is None:
            raise RuntimeError('list 失败: %s' % res.get('message'))
        result = res.get('result') or {}
        recs = result.get('records') or []
        out.extend(recs)
        if len(recs) < 100 or len(out) >= (result.get('total') or len(out)):
            break
        page += 1
    return [r for r in out if r.get('startType') == 'subEvent']


def verify(req, fid):
    """回读 processXml（base64）并解码，返回 (是否通过, 实际 key)。"""
    res = req('GET', '%s?id=%s' % (QUERY_PATH, fid))
    xml_b64 = (res.get('result') or {}).get('processXml') or ''
    if not xml_b64:
        return False, '(no processXml)'
    try:
        xml = base64.b64decode(xml_b64).decode('utf-8', 'ignore')
    except Exception as e:                                    # noqa: BLE001 —— 报错信息给调用者看
        return False, '(processXml 解码失败: %r)' % (e,)
    m = PROCESS_ID_RE.search(xml)
    return (m is not None and m.group(1) == 'process%s' % fid), (m.group(1) if m else '(no process id)')


def republish(req, rec, dry_run=False):
    """补 customProcessId 重存 + 重新 deploy + 核验。返回 (通过?, 说明)。

    幂等判据用**定义 key 本身**（`processXml` 解码），不用记录里的 `customProcessId`：
    实测 `queryById` 回读时该列恒为 None（`saveFlow` 用它拼 BPMN，但不回写该列），
    拿它当判据会让每条流程都「待补发」。
    """
    fid = rec.get('id')
    name = rec.get('processName') or fid

    ok, key = verify(req, fid)
    if ok:
        return True, '已就绪，跳过'
    if dry_run:
        return True, '待补发（当前 def key = %s）' % key

    detail = req('GET', '%s?id=%s' % (QUERY_PATH, fid)).get('result') or {}
    form = {
        'id': fid,
        'customProcessId': fid,
        'processKey': 'process%s' % fid,
        'processName': detail.get('processName') or name,
        'processType': detail.get('processType') or 'oa',
        'lowAppId': rec.get('lowAppId') or detail.get('lowAppId'),
        'startType': 'subEvent',
        'processJson': detail.get('processJson') or '',
        'updateCount': detail.get('updateCount') or 1,
    }
    saved = req('POST', SAVE_PATH, form, form=True)
    if not saved.get('success'):
        return False, 'saveFlow 失败: %s' % saved.get('message')

    dep = req('PUT', DEPLOY_PATH, {'id': fid})
    if not dep.get('success'):
        return False, 'deployProcess 失败: %s' % dep.get('message')

    ok, key = verify(req, fid)
    return ok, 'def key = %s' % key


def main(argv=None):
    p = argparse.ArgumentParser(description='subEvent 子流程补发 customProcessId 并核验（建后套件 ⑤.5）')
    p.add_argument('--api-base', required=True, help='JeecgBoot 后端地址，如 http://host:8080/jeecg-boot')
    p.add_argument('--token', required=True, help='X-Access-Token')
    p.add_argument('--tenant-id', required=True, help='租户 ID（X-Tenant-Id）')
    p.add_argument('--app-id', required=True, help='lowAppId')
    p.add_argument('--dry-run', action='store_true', help='只列出待补发的子流程，不保存')
    p.add_argument('--check-only', action='store_true', help='只核验现状，不保存')
    p.add_argument('--timeout', type=int, default=180, help='单请求超时秒数（默认 180）')
    args = p.parse_args(argv)

    req = make_requester(args.api_base, args.token, args.tenant_id, args.timeout)

    try:
        subs = list_subflows(req, args.app_id)
    except Exception as e:                                     # noqa: BLE001
        print('ERROR 取子流程列表失败: %r' % (e,))
        return 1

    print('subEvent 子流程 %d 条（app-id=%s）' % (len(subs), args.app_id))
    if not subs:
        print('==> 正常 0 / 异常 0（没有子流程，无需补发）')
        return 0

    ok = bad = 0
    for rec in subs:
        name = rec.get('processName') or rec.get('id')
        try:
            if args.check_only:
                good, note = verify(req, rec['id'])
            else:
                good, note = republish(req, rec, dry_run=args.dry_run)
        except Exception as e:                                 # noqa: BLE001
            good, note = False, '异常 %r' % (e,)
        print(('OK   ' if good else 'FAIL ') + str(name) + '  ' + note)
        ok += bool(good)
        bad += (not good)

    print('==> 正常 %d / 异常 %d' % (ok, bad))
    if bad:
        print('提示：仍失败时不要用 /act/process/list 复查（该接口实测 read timeout），'
              '用本脚本的 queryById+processXml 口径。')
        return 2
    if not args.dry_run and not args.check_only:
        print('下一步：build_flows.py --spec flows.py --force   # 建父流程（子流程会 skip）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
