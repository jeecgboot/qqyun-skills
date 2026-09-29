# -*- coding: utf-8 -*-
"""建后套件一条命令跑完：probe → struct → probe → defaults → flows → appconfig → verify → 简流契约闸门。
每段是独立子进程（就是手工逐条跑的那几条命令），任一段非 0 立刻停，修好配置后用 --from 续跑。

  python postbuild_run.py --api-base URL --token T --tenant-id N --app-id A --dir CONFIG_DIR \
         [--dry-run] [--from struct|defaults|flows|appconfig|verify] [--replace 流程名,流程名]

CONFIG_DIR 里放（缺哪个就跳过哪段）：
  struct_cfg.py 结构补丁 + DEFAULTS()      pb_flows.py   简流      appconfig.py  按钮/视图/导航/开关
  （旧名 struct.py / flows.py 仍认，但前者遮蔽标准库、后者与 flow_dsl 的 flows.py 撞名，别再用）
--dry-run：struct/defaults/flows/appconfig 只报告不保存（verify 与契约闸门本来就只读，照跑）。
"""
import sys, os, re, time, argparse, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.normpath(os.path.join(HERE, '..', '..', 'jeecg-lowcode-miniflow', 'scripts', 'check_node_contract.py'))
ORDER = ['struct', 'defaults', 'flows', 'appconfig', 'verify']

ap = argparse.ArgumentParser()
ap.add_argument('--api-base', required=True)
ap.add_argument('--token', required=True)
ap.add_argument('--tenant-id', required=True)
ap.add_argument('--app-id', required=True)
ap.add_argument('--dir', required=True)
ap.add_argument('--dry-run', action='store_true')
ap.add_argument('--from', dest='from_', default='struct', choices=ORDER)
ap.add_argument('--replace', default='')
ap.add_argument('--work', default='', help='probe.json / dicts.json 的目录（透传给各 postbuild_*.py；默认该应用的工作目录 %TEMP%/jeecg-lowcode/<英文简称>_<时间戳>/）')
A = ap.parse_args()
COMMON = ['--api-base', A.api_base, '--token', A.token, '--tenant-id', str(A.tenant_id), '--app-id', A.app_id]
if A.work:
    COMMON += ['--work', A.work]
DRY = ['--dry-run'] if A.dry_run else []


def cfg(name):
    p = os.path.join(A.dir, name)
    return p if os.path.exists(p) else None


def step(label, script, extra=()):
    t0 = time.time()
    print('── %s ──' % label, flush=True)
    rc = subprocess.run([sys.executable, script] + COMMON + list(extra)).returncode
    print('[%s] %.1fs exit=%d' % (label, time.time() - t0, rc), flush=True)
    if rc:
        key = label.split()[0]
        print('FAIL: 停在「%s」。按上面的 MISS:/FAIL: 行改配置，然后加 --from %s 续跑。'
              % (label, key if key in ORDER else 'struct'), flush=True)
        sys.exit(rc)


def kit(name):
    return os.path.join(HERE, 'postbuild_%s.py' % name)


todo = ORDER[ORDER.index(A.from_):]
T0 = time.time()
step('probe', kit('probe'))
# 结构配置推荐叫 struct_cfg.py —— 叫 struct.py 会遮蔽标准库，同目录任何 import requests 的脚本都崩（2026-09-22）
s = cfg('struct_cfg.py') if os.path.exists(cfg('struct_cfg.py')) else cfg('struct.py')
# 简流配置推荐叫 pb_flows.py：叫 flows.py 会与 flow_dsl 的 flows.py 撞名（同目录放两份必混，2026-09-22 CRM R2）。
# 回退用 flows.py 之前先看它是不是 flow_dsl 那份（定义 FLOWS）—— 误吃会让套件把 47 表应用的主流程当按钮流建（进销存 R3）
f = cfg('pb_flows.py')
if not f:
    _legacy = cfg('flows.py')
    if _legacy:
        try:
            _txt = open(_legacy, encoding='utf-8').read()
        except OSError:
            _txt = ''
        if re.search(r'^\s*FLOWS\s*=', _txt, re.M):
            print('NOTE: %s 是 flow_dsl 的 flows.py（定义 FLOWS），套件 flows 段跳过 —— '
                  '建后套件的简流配置请命名为 pb_flows.py' % _legacy, flush=True)
        else:
            f = _legacy
c = cfg('appconfig.py')
if 'struct' in todo and s:
    step('struct', kit('struct'), ['--config', s] + DRY)
    if not A.dry_run:
        step('probe (结构变更后重拍)', kit('probe'))
if 'defaults' in todo and s:
    step('defaults', kit('defaults'), ['--config', s] + DRY)
if 'flows' in todo and f:
    step('flows', kit('flows'), ['--config', f] + DRY + (['--replace', A.replace] if A.replace else []))
if 'appconfig' in todo and c:
    step('appconfig', kit('appconfig'), ['--config', c] + DRY)
step('verify', kit('verify'))
if os.path.exists(GATE):
    # 契约闸门不认 --work（它自己按 app-id 定位），透传会让整条链最后一段 exit=2（2026-09-22 销售 R3）
    _g = list(COMMON)
    if '--work' in _g:
        _i = _g.index('--work'); del _g[_i:_i + 2]
    t0 = time.time()
    print('── %s ──' % 'verify 简流契约闸门', flush=True)
    rc = subprocess.run([sys.executable, GATE] + _g).returncode
    print('[%s] %.1fs exit=%d' % ('verify 简流契约闸门', time.time() - t0, rc), flush=True)
    if rc:
        print('FAIL: 停在「verify 简流契约闸门」。', flush=True)
        sys.exit(rc)
print('OK:postbuild 全部通过 %.1fs%s' % (time.time() - T0, '（dry-run，未保存）' if A.dry_run else ''))
