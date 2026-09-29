# -*- coding: utf-8 -*-
"""敲敲云简流 —— 部署后置补丁（通用，不含任何应用知识）

背景：`build_flows.py` 是从 `flows.py` 重新生成、整份覆盖。有两类东西它不落地：

  ① **规格里声明、builder 丢弃的节点键** —— 最典型是 `data_get_one` 的
     `sortField` / `sortType`（排序），以及 `noDataType`。丢了不会报错，
     只是「取最早的一条」变成「取任意一条」，只有业务跑起来才看得出来。
  ② **`function` 节点 funContext 里指向 get_one 的条目 `formNodeType`** ——
     必须是 `search`，builder 写成 `table`。写成 table → 运算结果恒空，
     而 save/deploy/回读计数全绿，只有造单才发现。

本脚本把这两件事一趟做完，且**自愈**：
  · ① 按节点 id 对齐规格与真机，把规格里声明了、真机上没有的键回灌到 `attr`；
     `sortField` 允许写「字段显示名」，脚本按该节点的 `formTableCode` 解析成 model。
  · ② 从真机节点树自己推导哪些 id 是 data_get_one，凡指向它的 funContext 条目一律改
    `search`；改 formNodeType 会换 md5 key，所以同步按「字段 model」把 funText 占位符
    重指到现存 key —— 按 model 反查而非按旧 key 替换，天然自愈、不依赖改没改 key。
  · 最后回读校验：funText 里每个 `{{key.model}}` 都能命中 funContext；声明的排序已落地。

用法（任何应用通用）：
  python postdeploy.py --api-base URL --token T --tenant-id N --app-id A --spec flows.py
  可选：--only "流程名1,流程名2"（默认处理规格里的全部流程）
        --dry-run            只打印计划，不写库
        --flow-dsl-dir DIR   规格 import 不到 flow_dsl 时指定
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

# builder 丢弃、需要从规格回灌的节点键（写在这里 = 这份脚本的「已知丢失清单」）
REPLAY_KEYS = ('sortField', 'sortType', 'noDataType', 'ignoreSortRule')

# get_one 的 empty 文案 -> 落库 noDataType（以设计器为准，不是 builder 的历史错位表）
EMPTY_CODE = {'继续': 1, '新增': 2, '中止': 3, '分支': 3}

PLACEHOLDER = re.compile(r'\{\{([0-9a-f]{32})\.([^}]+)\}\}')

DEFAULT_DSL_DIRS = [
    os.path.expanduser(r'~\.claude\skills\jeecg-lowcode-miniflow\scripts'),
    '/root/.claude/skills/jeecg-lowcode-miniflow/scripts',
]


def req(ab, hdr, method, path, data=None, form=False):
    h = dict(hdr)
    body = None
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode('utf-8')
            h['Content-Type'] = 'application/x-www-form-urlencoded'
        else:
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            h['Content-Type'] = 'application/json'
    r = urllib.request.Request(ab + path, data=body, headers=h, method=method)
    return json.loads(urllib.request.urlopen(r, timeout=120).read().decode('utf-8'))


def walk(n):
    if not isinstance(n, dict):
        return
    yield n
    v = n.get('childNode')
    if isinstance(v, dict):
        yield from walk(v)
    elif isinstance(v, list):
        for c in v:
            yield from walk(c)
    # 网关 / 数据分支 / 审批结果分支里的节点：以前不进 conditionNodes，分支里的节点一律
    # 「在真机上找不到对应」、回灌和校验都漏（进销存-速测19 #18：查客户在审批结果分支里）
    for b in n.get('conditionNodes') or []:
        yield from walk(b)


# flow_dsl 的节点 type → 真机 processJson 的节点 type。
# ⚠️ 2026-09-24 实测误报：规格里是 `get_one`、真机是 `data_get_one`，按 (type, name) 永远对不上，
# 而 get_one 规格恒带 `empty` 键 → **每个 get_one 都打「!! 规格节点 X 在真机上找不到对应」**
# （三个应用、所有 --update 重建都出现），排序/noDataType 回灌也因此从未生效过；
# 非 dry-run 时 acts 非空还会白做一次 save+deploy。
SPEC_TYPE = {'get_one': 'data_get_one'}


def spec_nodes(nodes):
    """规格 nodes 是「按顺序的列表」，get_one 的下游是它的分支 —— 这里只要扁平清单
    （网关分支 branches[].nodes、data_branch 的 found/missing 里的节点也要收，否则分支里的 get_one 漏检）"""
    out = []
    for n in nodes or []:
        if isinstance(n, dict):
            out.append(n)
            out.extend(spec_nodes(n.get('nodes')))
            for b in n.get('branches') or []:
                out.extend(spec_nodes((b or {}).get('nodes')))
            out.extend(spec_nodes(n.get('found')))
            out.extend(spec_nodes(n.get('missing')))
    return out


def _live_key(sn):
    return (SPEC_TYPE.get(sn.get('type'), sn.get('type')), sn.get('name'))


def load_spec(path, dsl_dir):
    for d in [dsl_dir] + DEFAULT_DSL_DIRS:
        if d and d not in sys.path:
            sys.path.insert(0, d)
        if d and os.path.isdir(d):
            break
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    sp = importlib.util.spec_from_file_location('_flow_spec', path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m.FLOWS


class Tables:
    """表 code -> {字段显示名: model}"""

    def __init__(self, ab, hdr):
        self.ab, self.hdr, self.c = ab, hdr, {}

    def fields(self, code):
        if code not in self.c:
            r = urllib.request.Request(
                '%s/desform/api/queryForm?code=%s' % (self.ab, code), headers=self.hdr)
            raw = json.loads(urllib.request.urlopen(r, timeout=60).read().decode('utf-8'))
            res = raw.get('result') or {}
            d = res.get('desformDesignJson') or '{}'
            d = json.loads(d) if isinstance(d, str) else d
            m = {}

            def each(x):
                if isinstance(x, dict):
                    if x.get('name'):
                        m[x['name']] = x.get('model')
                    for v in x.values():
                        each(v)
                elif isinstance(x, list):
                    for v in x:
                        each(v)
            each(d.get('list'))
            self.c[code] = m
        return self.c[code]


def do_flow(ab, hdr, tb, name, fid, snodes, dry):
    rec = req(ab, hdr, 'GET', '/act/process/extActProcess/queryById?id=' + fid)['result']
    pj = json.loads(rec['processJson'])
    dn = list(walk(pj))
    by_id = {n['id']: n for n in dn if n.get('id')}
    by_name = {}
    for n in dn:
        by_name.setdefault((n.get('type'), n.get('name')), n)
    getone = {n['id'] for n in dn if n.get('type') == 'data_get_one' and n.get('id')}
    acts = []
    warns = []     # 只提示、不改：放进 acts 会被当成「有改动」触发一次多余的 save+deploy

    # ① 回灌规格里声明、builder 丢弃的键
    for sn in snodes:
        keys = [k for k in REPLAY_KEYS if k in sn]
        if not keys and 'empty' not in sn:
            continue
        tgt = by_id.get(sn.get('id')) if sn.get('id') else None
        if tgt is None:
            tgt = by_name.get(_live_key(sn))
        if tgt is None:
            # 只报告，不计入 acts（acts 非空会触发一次 save+deploy，找不到节点时什么也没改）
            print('%-10s !! 规格节点 %s 在真机上找不到对应' % (name, sn.get('name')))
            continue
        a = tgt.setdefault('attr', {})
        code = a.get('formTableCode') or tgt.get('formTableCode')
        fm = tb.fields(code) if code else {}
        for k in keys:
            val = sn[k]
            if k == 'sortField' and val in fm:       # 允许写字段显示名
                val = fm[val]
            if a.get(k) != val:
                a[k] = val
                acts.append('%s: %s.%s=%s' % (name, sn.get('name'), k, val))
        # empty 文案 -> noDataType（builder 曾整体错位一格，见 EMPTY_CODE 注释）
        if sn.get('empty') in EMPTY_CODE:
            want = EMPTY_CODE[sn['empty']]
            if a.get('noDataType') != want:
                a['noDataType'] = want
                acts.append('%s: %s.empty=%s -> noDataType=%d'
                            % (name, sn.get('name'), sn['empty'], want))

    # ② funContext.formNodeType 自愈 + funText 按 model 重指
    for n in dn:
        a = n.get('attr') or {}
        if n.get('type') != 'function' or not a.get('funContext'):
            continue
        new_fc = {}
        for k, v in a['funContext'].items():
            if not isinstance(v, str):                 # 整数/数字字面量不是编码 JSON：原样保留（以前 unquote(int) 直接崩，
                new_fc[k] = v                          # 2026-09-24 销售-速测17 H：重要程度 1~5 只能改写成字符串绕过）
                continue
            canon = urllib.parse.unquote(v)
            if hashlib.md5(canon.encode('utf-8')).hexdigest() != k:
                if a.get('funType') != 'record':     # 统计条数的 funContext 本就是另一套口径（销售-速测19 #11）
                    warns.append('!! %s 的 funContext 条目口径不符（原样保留）' % n.get('name'))
                new_fc[k] = v
                continue
            d = json.loads(canon)
            if d.get('formNodeId') in getone and d.get('formNodeType') != 'search':
                d['formNodeType'] = 'search'
                c2 = json.dumps(d, ensure_ascii=False, separators=(',', ':'))
                new_fc[hashlib.md5(c2.encode('utf-8')).hexdigest()] = \
                    urllib.parse.quote(c2, safe=':,.-_/?')
                acts.append('%s: %s 取值源 %s->search' % (name, n.get('name'),
                                                          d.get('formNodeName')))
            else:
                new_fc[k] = v
        model2key = {}
        for k, v in new_fc.items():
            # 统计条数（funType=record）等节点的 funContext 值是**普通 dict**，不是编码 JSON：
            # 以前这里一律 json.loads(unquote(v)) → JSONDecodeError，整批部署后置中断
            # （2026-09-24 销售/进销存-速测18）。只认能解开的编码 JSON。
            if not isinstance(v, str):
                continue
            try:
                d = json.loads(urllib.parse.unquote(v))
            except ValueError:
                continue
            if isinstance(d, dict):
                model2key.setdefault(d.get('field'), k)
        ft = a.get('funText') or n.get('funText') or ''

        def sub(m):
            good = model2key.get(m.group(2))
            if good and good != m.group(1):
                acts.append('%s: %s funText %s->%s'
                            % (name, n.get('name'), m.group(1)[:8], good[:8]))
                return '{{%s.%s}}' % (good, m.group(2))
            return m.group(0)
        nft = PLACEHOLDER.sub(sub, ft)
        a['funContext'] = new_fc
        if nft:
            a['funText'] = nft
            if 'funText' in n:
                n['funText'] = nft

    if acts and not dry:
        req(ab, hdr, 'POST', '/act/designer/miniDesFlow/api/saveFlow', {
            'id': fid, 'processKey': rec['processKey'], 'processName': rec['processName'],
            'processType': rec.get('processType') or 'oa', 'lowAppId': rec.get('lowAppId'),
            # 按原流程的触发类型存：写死 tableEvent 会把子流程/按钮流打回表事件
            'startType': rec.get('startType') or pj.get('startType') or 'tableEvent', 'updateCount': rec.get('updateCount') or 0,
            'processJson': json.dumps(pj, ensure_ascii=False)}, form=True)
        req(ab, hdr, 'PUT', '/act/process/extActProcess/deployProcess', {'id': fid})

    if dry:
        print('%-10s [dry-run] %d 处' % (name, len(acts)))
        for x in acts + sorted(set(warns)):
            print('           %s' % x)
        return True

    # ③ 回读校验
    pj2 = json.loads(req(ab, hdr, 'GET', '/act/process/extActProcess/queryById?id=' + fid)
                     ['result']['processJson'])
    dn2 = list(walk(pj2))
    by_id2 = {n['id']: n for n in dn2 if n.get('id')}
    bad = []
    for n in dn2:
        a = n.get('attr') or {}
        if n.get('type') == 'function' and a.get('funContext'):
            keys = set(a['funContext'])
            for k, _m in PLACEHOLDER.findall(a.get('funText') or n.get('funText') or ''):
                if k not in keys:
                    bad.append('%s funText 占位符 %s 不在 funContext' % (n.get('name'), k[:8]))
    for sn in snodes:
        if 'sortField' not in sn:
            continue
        tgt = by_id2.get(sn.get('id')) if sn.get('id') else by_name.get(_live_key(sn))
        a = (tgt or {}).get('attr') or {}
        code = a.get('formTableCode')
        want = sn['sortField']
        if code and want in tb.fields(code):
            want = tb.fields(code)[want]
        if a.get('sortField') != want:
            bad.append('%s 排序未落地（%s）' % (sn.get('name'), a.get('sortField')))
    print('%-10s 改动 %d 处 | 校验 %s' % (name, len(acts), 'OK' if not bad else bad))
    for x in acts + sorted(set(warns)):
        print('           %s' % x)
    return not bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--api-base', required=True)
    ap.add_argument('--token', required=True)
    ap.add_argument('--tenant-id', required=True)
    ap.add_argument('--app-id', required=True)
    ap.add_argument('--spec', required=True, help='flows.py（flow_dsl 声明式规格）')
    ap.add_argument('--only', default='', help='逗号分隔的流程名；默认规格里的全部')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--flow-dsl-dir', default='')
    a = ap.parse_args()

    hdr = {'X-Access-Token': a.token, 'X-Tenant-Id': a.tenant_id, 'X-Low-App-ID': a.app_id}
    specs = load_spec(a.spec, a.flow_dsl_dir)
    want = [x for x in a.only.split(',') if x] or [f['name'] for f in specs]

    # 按应用过滤：同租户多个应用用同一份提示词时流程同名，按名取第一个会改到别的应用（进销存-速测18 S9）
    lst = req(a.api_base, hdr, 'GET',
              '/act/process/extActProcess/list?pageNo=1&pageSize=1000&lowAppId=' + a.app_id)
    recs = (lst.get('result') or {}).get('records') or []
    idmap = {}
    for r in recs:
        if r.get('lowAppId') and str(r.get('lowAppId')) != str(a.app_id):
            continue
        idmap.setdefault(r.get('processName'), r.get('id'))
    missing = [n for n in want if n not in idmap]
    if missing:                                  # 缺的跳过、其余照做（以前整体中止，一条都不查）
        print('!! 应用下找不到这些流程（跳过）：%s' % missing)
        print('   应用内现有流程：%s' % sorted(idmap))

    tb = Tables(a.api_base, hdr)
    ok = True
    for f in specs:
        if f['name'] not in want or f['name'] not in idmap:
            continue
        ok = do_flow(a.api_base, hdr, tb, f['name'], idmap[f['name']],
                     spec_nodes(f.get('nodes')), a.dry_run) and ok
    print('\n==== 部署后置 %s ====' % ('全部通过' if ok and not missing else '存在失败项'))
    return 0 if (ok and not missing) else 2


if __name__ == '__main__':
    sys.exit(main())
