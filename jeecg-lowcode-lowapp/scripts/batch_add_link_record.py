# -*- coding: utf-8 -*-
"""批量并行给已有工作表新增关联记录字段（通用，不含任何业务模板）。

与逐条跑 scripts/add_link_record.py 完全等价，但用线程池并行——逐条串行时
每个子进程都要重复 get_tenants/get_apps/get_form_fields 定位（每次 10s+），
N 条串行 ≈ N×20s+；并行（默认 4 并发）墙钟接近单条耗时。

用法:
    python batch_add_link_record.py --api-base <URL> --token <TOKEN> --config <job.json>

job.json:
{
  "tenantName": "八匹狼",
  "appName": "采购申请",
  "maxWorkers": 4,
  "links": [
    {"worksheet": "报销单", "field": "审批模板", "mode": "单条", "display": "卡片",
     "target": {"appName": "流程审批", "worksheet": "审批流程模板"},
     "showFields": ["流程类型"],
     "filters": [{"field": "流程类型", "rule": "等于", "value": "采购审批"}]},
    {"worksheet": "请假单", "target": {"worksheet": "请假类型表"}, "mode": "单条", "display": "下拉"}
  ]
}

每条 link 的字段格式与 add_link_record.py 的 job.json 完全相同（见
references/fast-add-link-record.md），本脚本自动补全顶层 tenantName/appName；
field 缺省 = 目标工作表名。links 内 (worksheet, field) 重复即 fail-fast 拒绝。
自关联（target==主表）由 add_link_record.py 内部自动判定，本脚本不特殊处理。
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ADDER = os.path.join(HERE, 'add_link_record.py')


def run_one(idx, cfg, link, tmpdir):
    job = dict(link)
    job.setdefault('tenantName', cfg.get('tenantName'))
    job.setdefault('appName', cfg.get('appName'))
    # 目标表未指定应用时默认同应用（2026-09-15 修复：target 缺 appName 报「缺少应用」）
    tgt = job.get('target') or {}
    if 'code' not in tgt and 'appName' not in tgt:
        tgt = dict(tgt)
        tgt['appName'] = cfg.get('appName')
        job['target'] = tgt
    path = os.path.join(tmpdir, f'batch_link_{idx:03d}.json')
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(job, fh, ensure_ascii=False, indent=2)
    try:
        p = subprocess.run(
            [sys.executable, ADDER, '--api-base', cfg['apiBase'],
             '--token', cfg['token'], '--config', path],
            capture_output=True, timeout=300)
    except subprocess.TimeoutExpired:
        return idx, False, -1, '超时(300s)'
    text = ((p.stdout or b'') + b'\n' + (p.stderr or b'')).decode('utf-8', errors='replace')
    ok = p.returncode == 0 and ('成功' in text or 'add_widget' in text
                                or 'update_widget' in text or 'isSelf' in text)
    tail = ' | '.join([ln.strip() for ln in text.strip().splitlines() if ln.strip()][-2:])
    return idx, ok, p.returncode, tail


def main():
    ap = argparse.ArgumentParser(description='批量并行新增关联记录字段')
    ap.add_argument('--api-base', required=True)
    ap.add_argument('--token', required=True)
    ap.add_argument('--config', required=True)
    a = ap.parse_args()

    with open(a.config, encoding='utf-8') as fh:
        cfg = json.load(fh)
    links = cfg.get('links') or []
    if not links:
        raise SystemExit('config.links 不能为空')
    seen = set()
    for l in links:
        key = (l.get('worksheet'),
               l.get('field') or (l.get('target') or {}).get('worksheet'))
        if key in seen:
            raise SystemExit(f'links 存在重复项: {key}')
        seen.add(key)

    cfg['apiBase'] = a.api_base
    cfg['token'] = a.token
    tmpdir = os.path.join(tempfile.gettempdir(), 'jeecg-desform')
    os.makedirs(tmpdir, exist_ok=True)
    workers = max(1, min(int(cfg.get('maxWorkers') or 4), len(links)))

    fails = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(run_one, i, cfg, l, tmpdir) for i, l in enumerate(links)]
        for f in as_completed(futs):
            idx, ok, rc, tail = f.result()
            if not ok:
                fails += 1
            l = links[idx]
            label = f"{l.get('worksheet')}.{l.get('field') or (l.get('target') or {}).get('worksheet')}"
            print(f"[{idx:02d}] {'OK' if ok else 'FAIL'} {label} rc={rc} :: {tail}",
                  flush=True)
    print(f'DONE 共{len(links)}条 失败{fails}条')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
