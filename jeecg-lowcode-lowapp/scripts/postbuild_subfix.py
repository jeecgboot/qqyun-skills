# -*- coding: utf-8 -*-
"""子流程收尾修复 —— 建完父流程之后必须跑一次（幂等、可反复跑）。

    python postbuild_subfix.py --api-base URL --token TOKEN \
        --tenant-id N --app-id A [--check-only] [--dry-run] [--expect 25]

修两件事（**两件都是「闸门只报提示、但运行期真会不通」**，而且 save/deploy/条数全绿）：

① **`startType` 被打回 `tableEvent`。**
   `build_flows.py` 的「父流程回填趟」（建父流程之后跑、给子流程写数据源）**会重存子流程**，
   重存后 `startType` 从 `subEvent` 掉回 `tableEvent` —— 那几条子流程就变成**普通表事件流程**，
   会在自己的上下文表被写时**误触发**。
   症状：`check_node_contract` 报 `其中子流程 N 条` 的 N 会比规格少；
   `postbuild_subpub.py --check-only` 也只认已经是 `subEvent` 的，**修不了掉类型的**。
   2026-09-23 进销存 47 表实测：25 条子流程里有 6 条被打回（正好是被回填趟重存的那 6 条）。

② **`subFlowSourceInfo` 为空**（设计器面板上的「被以下工作流触发」）。
   按 gotchas ③：**必须在子流程最后一次保存时显式回填** —— 重存父流程不会补，
   子流程之后再被存一次又会清空。为空时子流程取不到父单据的上下文。
   本脚本从**各父流程 `processJson.subFlowList` 反推**（权威来源，不靠名字猜），
   写成 `[{mainProcessId, mainProcessName, nodeName}]`。

判据口径：`startType=='subEvent'` 且 `processJson.subFlowSourceInfo` == 反推出的那份，
且引擎定义 key（`processXml` base64 解出的 `<process id="...">`）== `process<DBid>`。

退出码：0 全部就绪 / 2 有失败项。`--check-only` 只核验不写，`--dry-run` 只列计划不写。
"""
import argparse, base64, json, os, re, sys, urllib.parse, urllib.request

sys.stdout.reconfigure(encoding='utf-8')


def req(base, hdr, method, path, data=None, form=False, timeout=240):
    h = dict(hdr)
    body = None
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode('utf-8')
            h['Content-Type'] = 'application/x-www-form-urlencoded'
        else:
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            h['Content-Type'] = 'application/json'
    rq = urllib.request.Request(base + path, data=body, headers=h, method=method)
    return json.loads(urllib.request.urlopen(rq, timeout=timeout).read().decode('utf-8'))


def def_key(xml):
    if not xml:
        return None
    try:
        m = re.search(r'<process\s+id="([^"]+)"', base64.b64decode(xml).decode('utf-8', 'ignore'))
        return m.group(1) if m else None
    except Exception:
        return None


def _nodes(pj):
    """processJson 里的全部节点（childNode 链 + 分支）。"""
    out, stack = [], [pj]
    while stack:
        n = stack.pop()
        if not isinstance(n, dict):
            continue
        if n.get('type'):
            out.append(n)
        stack.append(n.get('childNode'))
        stack.extend(n.get('conditionNodes') or [])
    return out


def _sub_obj(sfo):
    """父流程 callActivity 的 subFormTableObject → 子流程侧登记条目（与 build_flows 回填趟同口径：
    子流程侧 nodeType=search、nodeTypeMain=getMore、登记名固定「子流程」）。"""
    obj = dict(sfo)
    obj['nodeTypeMain'] = 'getMore'
    obj['nodeType'] = 'search'
    obj['nodeName'] = _SUB_ROW_NAME
    obj['isSubStart'] = True
    return obj


_MF = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                   'jeecg-lowcode-miniflow', 'scripts')
if _MF not in sys.path:
    sys.path.insert(0, _MF)
from build_flows import _fix_sub_ownrow_refs, SUB_ROW_NAME as _SUB_ROW_NAME  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--api-base', required=True)
    ap.add_argument('--token', required=True)
    ap.add_argument('--tenant-id', required=True)
    ap.add_argument('--app-id', required=True)
    ap.add_argument('--expect', type=int, default=0, help='期望的子流程条数，0=不校验')
    ap.add_argument('--check-only', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    base = a.api_base.rstrip('/')
    hdr = {'X-Access-Token': a.token, 'X-Tenant-Id': str(a.tenant_id)}
    app = str(a.app_id)

    lst = req(base, hdr, 'GET',
              '/act/process/extActProcess/list?lowAppId=%s&pageSize=300&pageNo=1' % app)
    recs = (lst.get('result') or {}).get('records') or []
    byid = {r['id']: r for r in recs}
    print('应用 %s 共 %d 条流程' % (app, len(recs)))
    if not recs:
        sys.exit('!! 没读到流程 —— 检查 app-id / 租户头')

    # ---- 反推：谁调用了哪个子流程（subProcessId 是权威来源） ----
    rev, walk = {}, []
    sfo_of = {}        # 子流程 id → [(父流程名, 父 callActivity 的 subFormTableObject)]
    for r in recs:
        d = req(base, hdr, 'GET', '/act/process/extActProcess/queryById?id=%s' % r['id'])['result']
        try:
            p = json.loads(d.get('processJson') or '{}')
        except Exception:
            continue
        walk.append((r, d, p))
        listed = {str(it.get('subProcessId')) for it in (p.get('subFlowList') or [])}
        for n in _nodes(p):
            a_ = n.get('attr') or {}
            sid = str(a_.get('customProcessId') or '')
            if n.get('type') != 'callActivity' or not sid:
                continue
            if a_.get('subFormTableObject'):
                sfo_of.setdefault(sid, []).append((r.get('processName'), a_['subFormTableObject']))
            if sid not in listed:
                # 手拼的父流程（定时触发，gotchas #127）常没写 subFlowList：以前只按 subFlowList 反推调用方，
                # 这类子流程整条漏掉，「被以下工作流触发」不回填、--check-only 还报就绪（销售-速测19 #4）
                rev.setdefault(sid, []).append({
                    'mainProcessId': r['id'], 'mainProcessName': r.get('processName'),
                    'nodeName': n.get('name') or '子流程'})
        for it in (p.get('subFlowList') or []):
            sid = it.get('subProcessId')
            if sid:
                rev.setdefault(sid, []).append({
                    'mainProcessId': r['id'],
                    'mainProcessName': r.get('processName'),
                    'nodeName': it.get('subNodeName') or '子流程',
                })
    # 兜底：已经是 subEvent 但没被反推到（父流程尚未建）的，也纳入检查
    for r, d, p in walk:
        if r.get('startType') == 'subEvent':
            rev.setdefault(r['id'], rev.get(r['id'], []))

    print('反推出 %d 条子流程（被父流程 callActivity 引用）' % len(rev))
    if a.expect and len(rev) != a.expect:
        print('!! 期望 %d 条，实际反推出 %d 条 —— 先确认父流程都建全了' % (a.expect, len(rev)))

    plan, bad = [], 0
    obj_for = {}       # 子流程 id → 要补的数据源登记条目
    for r, d, p in walk:
        fid = r['id']
        if fid not in rev:
            continue
        want = rev[fid]
        st = d.get('startType')
        cur = p.get('subFlowSourceInfo') or []
        key = def_key(d.get('processXml'))
        keys_ok = (key == 'process%s' % fid)
        need = []
        if st != 'subEvent':
            need.append('startType(%s→subEvent)' % st)
        if want and cur != want:
            need.append('subFlowSourceInfo(%d→%d 条)' % (len(cur), len(want)))
        if not keys_ok:
            need.append('defKey(%s→process%s)' % (key, fid))
        # ③ 数据源登记：只有 build_flows 的回填趟会写；父流程若是手拼的（定时触发 gotchas #127），
        #    子流程就缺 isSubStart / subFormTableObject、本行取值还是 table/start —— 契约闸门报违例、
        #    运行时 ref() 取空（2026-09-24 销售-速测18 #1）。从父流程 callActivity 的 subFormTableObject 补。
        sfos = sfo_of.get(str(fid)) or []
        nodes_ = {str((o or {}).get('nodeId')) for _n, o in sfos}
        if len(nodes_) > 1:
            print('!! %s 被 %d 个取数节点调用（%s），本行取值只能绑一个 —— 每个调用方各建一条子流程，这里不补'
                  % (r.get('processName'), len(nodes_), '、'.join(x for x, _o in sfos)))
        elif sfos:
            obj = _sub_obj(sfos[0][1])
            ftl = p.get('formTableList') or []
            head = next((e for e in ftl if e.get('isSubStart')), None)
            sattr = (p.get('attr') or {}).get('subFormTableObject') or {}
            if not head or head.get('nodeId') != obj.get('nodeId') or sattr.get('nodeId') != obj.get('nodeId'):
                need.append('数据源登记(isSubStart/subFormTableObject ← %s)' % sfos[0][0])
                obj_for[fid] = obj
        if need:
            plan.append((r, d, p, want, need))

    print()
    if not plan:
        print('==> 全部就绪，无需修复')
        return 0

    for r, d, p, want, need in plan:
        print('%-6s %-26s %s' % ('DRY' if (a.dry_run or a.check_only) else 'FIX',
                                 r.get('processName'), ' / '.join(need)))
    if a.dry_run or a.check_only:
        print('==> 待修 %d 条（未写入）' % len(plan))
        return 2

    ok = 0
    for r, d, p, want, need in plan:
        fid, nm = r['id'], r.get('processName')
        p2 = dict(p)
        p2['subFlowSourceInfo'] = want
        obj = obj_for.get(fid)
        if obj:
            ftl = [e for e in (p2.get('formTableList') or []) if not e.get('isSubStart')]
            p2['formTableList'] = [obj] + ftl
            sattr = dict(p2.get('attr') or {})
            sattr['subFormTableObject'] = dict(obj)
            sattr['formTableId'] = obj.get('formTableId')
            sattr.setdefault('formTableCode', obj.get('formTableCode'))
            sattr.setdefault('formTableName', obj.get('formTableName'))
            p2['attr'] = sattr
            _fix_sub_ownrow_refs(p2, obj.get('nodeId'), print)
        try:
            s = req(base, hdr, 'POST', '/act/designer/miniDesFlow/api/saveFlow', {
                'id': fid, 'customProcessId': fid, 'processKey': 'process%s' % fid,
                'processName': d.get('processName') or nm,
                'processType': d.get('processType') or 'oa',
                'lowAppId': app, 'startType': 'subEvent',
                'processJson': json.dumps(p2, ensure_ascii=False),
                'updateCount': d.get('updateCount') or 1,
            }, form=True)
            if not s.get('success'):
                print('FAIL saveFlow', nm, s.get('message')); bad += 1; continue
            dep = req(base, hdr, 'PUT', '/act/process/extActProcess/deployProcess', {'id': fid})
            if not dep.get('success'):
                print('FAIL deploy', nm, dep.get('message')); bad += 1; continue
            d2 = req(base, hdr, 'GET', '/act/process/extActProcess/queryById?id=%s' % fid)['result']
            p3 = json.loads(d2.get('processJson') or '{}')
            good = (d2.get('startType') == 'subEvent'
                    and (p3.get('subFlowSourceInfo') or []) == want
                    and def_key(d2.get('processXml')) == 'process%s' % fid)
            print(('OK   ' if good else 'BAD  '), nm)
            ok += good; bad += (not good)
        except Exception as e:
            print('ERR ', nm, repr(e)[:160]); bad += 1

    print('==> 修好 %d / 异常 %d' % (ok, bad))
    return 0 if bad == 0 else 2


if __name__ == '__main__':
    sys.exit(main())
