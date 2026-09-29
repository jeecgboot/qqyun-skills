# -*- coding: utf-8 -*-
"""交付门禁聚合器：三套一起跑，输出一份合并的违例清单。

为什么要聚合：三套门禁各自为政时，常见做法是「跑一套 → 改 → 再跑」，每套都要重读
47 表 / 54 流程，一轮下来十几分钟。改成一次跑完三套、把违例合并输出，改完只重跑一遍。

三套门禁：
  ① precheck            纯静态、不联网（规格 + 流程语法/引用校验）
  ② app_audit           真机回读（字典/表/字段/布局/看板/权限）
  ③ check_node_contract 真机回读（简流逐节点契约）

用法：
    python run_gates.py --api-base <url> --token <jwt> --tenant-id <id> --app-id <id> \
        --spec app_spec.json [--flows flows_final.py] [--expect "表单=47,字典=32,看板=16"] \
        [--only precheck,audit,contract] [--workspace <dir>]

退出码：0 = 三套全过；1 = 有违例；2 = 用法/环境错误。
"""
from __future__ import annotations

import argparse
import io
import os
import re
import subprocess
import sys

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
MINIFLOW_SCRIPTS = os.path.normpath(os.path.join(HERE, '..', '..', 'jeecg-lowcode-miniflow', 'scripts'))

# 违例行：check_node_contract 用 ✗，app_audit 用 x，precheck 用 ✗ / ERROR
RE_VIOLATION = re.compile(r'^\s*(?:✗|x|X|ERROR|错误)\s', re.UNICODE)
# 提示行：统一是 !
RE_HINT = re.compile(r'^\s*!\s', re.UNICODE)
# 汇总行：[check] …违例 N 条 / 提示 M 条    或    ==== 违例 N 条 / 提示 M 条 ====
RE_SUMMARY = re.compile(r'违例\s*(\d+)\s*条(?:.*?提示\s*(\d+)\s*条)?', re.UNICODE)


def run_stage(label, argv, cwd, timeout):
    """跑一个门禁脚本，返回 (输出全文, 退出码)。输出按行实时透传前缀。"""
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'      # 子脚本在 GBK 控制台会因 ✓ 之类字符崩掉
    env['PYTHONUTF8'] = '1'
    try:
        p = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=timeout)
        out = (p.stdout or b'').decode('utf-8', errors='replace')
        return out, p.returncode
    except subprocess.TimeoutExpired:
        return '[%s] 超时（%ss）' % (label, timeout), 124
    except FileNotFoundError:
        return '[%s] 找不到脚本：%s' % (label, argv[0]), 127


# precheck 是「小节 + 缩进短横线」格式：
#   ⚠ 提示 256 条：
#     - xxx
#     … 还有 236 条
#   ✗ 预检不通过 3 条：
#     - yyy
RE_SECTION = re.compile(r'^\s*([⚠✗])\s*(提示|预检不通过|违例)\s*(\d+)\s*条', re.UNICODE)
RE_ITEM = re.compile(r'^\s*-\s+(.*)$', re.UNICODE)


def collect(stage, out):
    viol, hint = [], []
    summary = None
    mode = None          # None / 'hint' / 'viol'
    for line in out.splitlines():
        s = line.rstrip()
        if not s.strip():
            continue
        m = RE_SUMMARY.search(s)
        if m and '违例' in s:
            summary = (int(m.group(1)), int(m.group(2) or 0))

        sec = RE_SECTION.match(s)
        if sec:
            mode = 'hint' if (sec.group(1) == '⚠' or sec.group(2) == '提示') else 'viol'
            continue
        if mode:
            if s.strip().startswith('…'):
                mode = None
                continue
            it = RE_ITEM.match(s)
            if it:
                (hint if mode == 'hint' else viol).append(it.group(1).strip())
                continue
            mode = None

        if RE_VIOLATION.match(s):
            viol.append(s.strip())
        elif RE_HINT.match(s):
            hint.append(s.strip())
    return {'stage': stage, 'violations': viol, 'hints': hint, 'summary': summary}


def main():
    ap = argparse.ArgumentParser(description='三套交付门禁聚合器')
    ap.add_argument('--api-base', required=True)
    ap.add_argument('--token', required=True)
    ap.add_argument('--tenant-id', required=True)
    ap.add_argument('--app-id', required=True)
    ap.add_argument('--spec', help='app_spec.json 路径')
    ap.add_argument('--flows', help='flows_final.py 路径（可选）')
    ap.add_argument('--expect', default=None, help='数量期望，如 "表单=47,字典=32,看板=16"')
    ap.add_argument('--only', default='precheck,audit,contract',
                    help='要跑哪几套，逗号分隔（默认全跑）')
    ap.add_argument('--workspace', default=os.getcwd(), help='precheck 的工作目录（默认当前目录）')
    ap.add_argument('--max-hints', type=int, default=8, help='每套最多显示几条提示（默认 8）')
    a = ap.parse_args()

    # 路径一律绝对化 + 三个子进程统一在「工作目录」里跑：
    # 否则 app_audit / precheck 会按自己的 cwd 去找 app_spec.json 而报 FileNotFoundError。
    ws = os.path.abspath(a.workspace)
    spec = os.path.abspath(a.spec) if a.spec else None
    flows = os.path.abspath(a.flows) if a.flows else None
    if (spec and not os.path.exists(spec)) or (flows and not os.path.exists(flows)):
        print('!! --spec/--flows 路径不存在（工作目录 %s）' % ws, file=sys.stderr)
        return 2

    only = {x.strip() for x in a.only.split(',') if x.strip()}
    stages = []

    if 'precheck' in only:
        if not spec:
            print('!! precheck 需要 --spec', file=sys.stderr)
            return 2
        argv = [sys.executable, os.path.join(HERE, 'precheck.py'), '--spec', spec]
        argv += ['--flows', flows] if flows else ['--no-flows']
        if a.expect:
            argv += ['--expect', a.expect]
        stages.append(('precheck（静态）', argv, ws, 600))

    if 'audit' in only:
        if not spec:
            print('!! app_audit 需要 --spec', file=sys.stderr)
            return 2
        argv = [sys.executable, os.path.join(HERE, 'app_audit.py'),
                '--api-base', a.api_base, '--token', a.token,
                '--tenant-id', str(a.tenant_id), '--app-id', str(a.app_id),
                '--spec', spec]
        argv += ['--flows', flows] if flows else []
        if a.expect:
            argv += ['--expect', a.expect]
        stages.append(('app_audit（真机）', argv, ws, 3600))

    if 'contract' in only:
        argv = [sys.executable, os.path.join(MINIFLOW_SCRIPTS, 'check_node_contract.py'),
                '--api-base', a.api_base, '--token', a.token,
                '--tenant-id', str(a.tenant_id), '--app-id', str(a.app_id)]
        stages.append(('check_node_contract（真机）', argv, ws, 3600))

    if not stages:
        print('!! --only 里没有可跑的阶段', file=sys.stderr)
        return 2

    results = []
    for label, argv, cwd, tmo in stages:
        print('\n' + '=' * 78)
        print('▶ %s' % label)
        print('=' * 78, flush=True)
        out, rc = run_stage(label, argv, cwd, tmo)
        # 原样透传，方便看细节
        print(out, flush=True)
        r = collect(label, out)
        r['rc'] = rc
        results.append(r)

    # ---------- 合并报告 ----------
    print('\n' + '=' * 78)
    print('■ 合并结论（改完这三块，再跑一遍本脚本即可）')
    print('=' * 78)
    total_v = total_h = 0
    for r in results:
        v, h = len(r['violations']), len(r['hints'])
        total_v += v
        total_h += h
        s = r['summary']
        tag = 'OK' if v == 0 else '有违例'
        print('  %-28s %-6s 违例 %-4d 提示 %-4d%s'
              % (r['stage'], tag, v, h, '' if r['rc'] == 0 or v else '  (退出码 %s)' % r['rc']))

    if total_v:
        print('\n--- 违例明细（按门禁分组，改这些） ---')
        for r in results:
            if not r['violations']:
                continue
            print('\n[%s] 共 %d 条' % (r['stage'], len(r['violations'])))
            for line in r['violations']:
                print('   ' + line)
    if total_h:
        print('\n--- 提示（不阻塞交付，可延后） ---')
        for r in results:
            if not r['hints']:
                continue
            shown = r['hints'][:a.max_hints]
            print('\n[%s] 共 %d 条%s' % (r['stage'], len(r['hints']),
                                      '' if len(shown) == len(r['hints']) else '（只列前 %d 条）' % a.max_hints))
            for line in shown:
                print('   ' + line)

    print('\n' + ('★ 三套门禁全部通过' if total_v == 0 else '✗ 合计违例 %d 条 —— 按上面的明细一次改完，再重跑本脚本' % total_v))
    return 0 if total_v == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
