# -*- coding: utf-8 -*-
"""建后默认值补丁：当前用户/部门、当天/当前时间、静态值、其他字段值、查询工作表、函数计算。
落库形态（advancedSetting.defaultValue 的 compose/function/linkage、sqParam、LINKAGET 文本）
全部由脚本生成，配置里只写字段中文名。逻辑来自 2026-09-21 CRM 应用真机跑通的脚本。

  python postbuild_defaults.py --api-base URL --token T --tenant-id N --app-id A \
         --config postbuild_config.py [--work DIR] [--dry-run]

前置：postbuild_probe.py 已跑过；若 postbuild_struct.py 改过名，先重跑 probe，且这里用**改名后**的名字。
配置文件里定义一个函数 DEFAULTS()，在里面调用下面这些助手（写法见 references/postbuild-kit.md）：

  current_user([(表,字段)…]) / current_dept([…])         默认当前登录人 / 当前部门
  today([(表,字段)…]) / now([(表,字段)…])                 日期默认当天 / 日期时间默认当前时间
  static(表, 字段, 值, 字典名=None)                        静态默认值；字典字段传字典名，自动换成落库值
  take(表, 字段, 关联控件, 目标表, 目标字段)                默认 【关联控件】【目标字段】
  same(表, 字段, 源字段)                                   默认 取本表另一字段
  lookup(表, 字段, 目标表, 取哪个字段, (目标条件字段, 本表字段))   默认值(查询工作表)，取第一条
  lookup_count(表, 字段, 目标表, (目标条件字段, 本表字段))        默认值(查询工作表)，计条数
  func(表, 字段, 表达式)                                   默认值(函数计算)，表达式里用 F()/COUNT() 拼
      F(表, 字段)                       → $model$
      COUNT(目标表, 目标条件字段, 本表, 本表字段)  → 计条数的 LINKAGET(...) 文本，可参与运算/IF/CONCAT
"""
import sys, os, json, argparse, tempfile, copy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from desform_lowapp_utils import init_lowapp
from desform_utils import query_form, save_design_from_file, save_auth_from_design

ap = argparse.ArgumentParser()
ap.add_argument('--api-base', required=True)
ap.add_argument('--token', required=True)
ap.add_argument('--tenant-id', required=True)
ap.add_argument('--app-id', required=True)
ap.add_argument('--config', required=True)
ap.add_argument('--work', default=None)
ap.add_argument('--dry-run', action='store_true')
A = ap.parse_args()
AID = A.app_id
WORK = A.work or os.path.join(tempfile.gettempdir(), 'jeecg-desform', AID)
for _f in ('probe.json', 'dicts.json'):
    if not os.path.exists(os.path.join(WORK, _f)):
        sys.exit('缺少 %s —— 先跑 postbuild_probe.py' % os.path.join(WORK, _f))
CODE = {t: v['code'] for t, v in json.load(open(os.path.join(WORK, 'probe.json'), encoding='utf-8')).items()}
DICTS = json.load(open(os.path.join(WORK, 'dicts.json'), encoding='utf-8'))

TID = int(A.tenant_id) if str(A.tenant_id).isdigit() else A.tenant_id
init_lowapp(A.api_base, A.token, tenant_id=TID, app_id=AID)

DESIGNS, ORIG, MISS, TOUCHED = {}, {}, [], []


def design(t):
    if t not in CODE:
        raise KeyError('应用里没有工作表「%s」（probe.json 过期就重跑 postbuild_probe.py）' % t)
    if t not in DESIGNS:
        DESIGNS[t] = json.loads(query_form(CODE[t])['desformDesignJson'])
        ORIG[t] = copy.deepcopy(DESIGNS[t])
    return DESIGNS[t]


def walk(node, out=None):
    out = [] if out is None else out
    if isinstance(node, dict):
        if node.get('type') and node.get('key') and node.get('type') not in ('card', 'grid'):
            out.append(node)
        for k in ('list', 'columns', 'panes'):
            v = node.get(k)
            if isinstance(v, list):
                for it in v:
                    walk(it, out)
    elif isinstance(node, list):
        for it in node:
            walk(it, out)
    return out


def W(t, name):
    for w in walk(design(t).get('list') or []):
        if w.get('name') == name and w.get('type') != 'divider':
            return w
    return None


def M(t, name):
    w = W(t, name)
    if w is None:
        MISS.append('%s.%s 不存在' % (t, name))
        return None
    return w.get('model')


def K(t, name):
    w = W(t, name)
    return w and w.get('key')


def TY(t, name):
    """控件族：他表字段取 fieldType，日期取档位——sqParam.type 按源表字段算"""
    w = W(t, name)
    if not w:
        return 'input'
    o = w.get('options') or {}
    if w['type'] == 'link-field':
        return o.get('fieldType') or 'input'
    if w['type'] == 'date':
        return o.get('type') or 'date'
    return w['type']


def _fmt(t, name):
    w = W(t, name)
    if not w:
        return 'string'
    if w['type'] in ('money', 'number', 'integer'):
        return 'number'
    if w['type'] == 'date':
        return 'date'
    return 'string'


def _adv(t, name, dv):
    w = W(t, name)
    if w is None:
        MISS.append('%s.%s 不存在' % (t, name)); return
    w['advancedSetting'] = {'defaultValue': dv}
    TOUCHED.append((t, name))


def _dv(kind, value, fmt, custom=False):
    return {'type': kind, 'value': value, 'format': fmt, 'allowFunc': True,
            'valueSplit': '', 'customConfig': custom}


# ── 助手（配置文件的 DEFAULTS() 里调用）──
def current_user(pairs):
    for t, n in pairs:
        _adv(t, n, _dv('compose', '#D:CURRENT#', 'string', True))


current_dept = current_user


def today(pairs):
    for t, n in pairs:
        func(t, n, "DATENOW('YYYY-MM-DD')")


def now(pairs):
    for t, n in pairs:
        func(t, n, "DATENOW('YYYY-MM-DD HH:mm:ss')")


def static(t, name, val, dict_name=None):
    w = W(t, name)
    if w is None:
        MISS.append('%s.%s 不存在' % (t, name)); return
    v = val
    if dict_name:
        items = DICTS.get(dict_name)
        if not items or val not in items:
            MISS.append('%s.%s 静态值「%s」不在字典「%s」里' % (t, name, val, dict_name)); return
        v = items[val]                       # 字典字段存落库值（序号串），不是文案
    w.setdefault('options', {})['defaultValue'] = v
    w.pop('advancedSetting', None)           # 空的高级默认值会盖掉普通默认值
    TOUCHED.append((t, name))


def compose(t, name, expr):
    _adv(t, name, _dv('compose', expr, _fmt(t, name)))


def func(t, name, expr):
    _adv(t, name, _dv('function', expr, _fmt(t, name)))


def take(t, name, link_field, src_table, src_field):
    """默认 【关联控件】【目标字段】 → $关联控件key.目标字段model$（前半是 key，不是 model）"""
    k, m = K(t, link_field), M(src_table, src_field)
    if not k:
        MISS.append('%s.%s 关联控件不存在' % (t, link_field))
    if k and m:
        compose(t, name, '$%s.%s$' % (k, m))


def same(t, name, src_field):
    m = M(t, src_field)
    if m:
        compose(t, name, '$%s$' % m)


def F(t, name):
    return '$%s$' % M(t, name)


def _cfg(tgt, op, rules, linkages):
    return {'appId': AID, 'desformCode': CODE[tgt], 'matchType': 'AND', 'operation': op,
            'rules': rules, 'linkages': linkages, 'sorts': [],
            'isMultiple': False, 'maxRecordCount': 200}


def _rule(tgt, tgt_field, self_t, self_field):
    return {'model': M(tgt, tgt_field), 'rule': 'EQ', 'valueType': 'field',
            'value': [M(self_t, self_field)],
            'sqParam': {'type': TY(tgt, tgt_field), 'rule': 'eq'}}


def lookup(t, name, tgt, tgt_field, cond):
    c = _cfg(tgt, 'FIRST', [_rule(tgt, cond[0], t, cond[1])],
             [{'model': M(t, name), 'linkModel': M(tgt, tgt_field), 'linkName': tgt_field}])
    _adv(t, name, _dv('linkage', c, _fmt(t, name)))


def lookup_count(t, name, tgt, cond):
    c = _cfg(tgt, 'COUNT', [_rule(tgt, cond[0], t, cond[1])], [])
    _adv(t, name, _dv('linkage', c, 'number'))


def COUNT(tgt, tgt_field, self_t, self_field):
    """函数计算里的计条数：内嵌 config 的 value 存裸 model；第二参数 val 写 $model$ 且不带引号"""
    c = _cfg(tgt, 'COUNT', [_rule(tgt, tgt_field, self_t, self_field)], [])
    return ('LINKAGET(%s ,  [{"field":"%s","type":"%s","rule":"eq","val":$%s$}])'
            % (json.dumps(c, ensure_ascii=False, separators=(',', ':')),
               M(tgt, tgt_field), TY(tgt, tgt_field), M(self_t, self_field)))


# ── 执行配置 ──
def DEFAULTS():
    pass


exec(compile(open(A.config, encoding='utf-8').read(), A.config, 'exec'), globals())
DEFAULTS()


# ── 保存：只存真正变了的表 ──
def _dump(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False)


def _changed_names(t):
    a = {w['key']: _dump(w) for w in walk(ORIG[t].get('list') or [])}
    return [w.get('name') for w in walk(DESIGNS[t].get('list') or []) if a.get(w['key']) != _dump(w)]


CHANGED = [t for t in DESIGNS if _dump(ORIG[t]) != _dump(DESIGNS[t])]
for t in sorted(CHANGED):
    print('%s %s：%s' % ('PLAN' if A.dry_run else 'SAVE', t, '、'.join(_changed_names(t))))
    if A.dry_run:
        continue
    d = DESIGNS[t]
    for w in walk(d.get('list') or []):
        o = w.setdefault('options', {})
        if o.get('dictCode') and o.get('isDictItem'):
            o['remote'] = 'dict'
    p = os.path.join(WORK, 'defaults_%s.json' % CODE[t])
    json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
    save_design_from_file(CODE[t], p)
    save_auth_from_design(CODE[t])

# 回读断言：设过默认值的字段，落库后必须非空且不含 None
bad = []
if not A.dry_run and CHANGED:
    DESIGNS.clear()
for t, n in sorted(set(TOUCHED)):
    w = W(t, n)
    if w is None:
        bad.append('%s.%s 丢失' % (t, n)); continue
    dv = ((w.get('advancedSetting') or {}).get('defaultValue') or {})
    v, sv = dv.get('value'), (w.get('options') or {}).get('defaultValue')
    if (v in ('', None) and sv in ('', None)) or 'None' in json.dumps(v, ensure_ascii=False):
        bad.append('%s.%s' % (t, n))

for m in MISS:
    print('MISS:' + m)
for b in bad:
    print('BAD:' + b)
print('%s:defaults 设置 %d 个字段 / 变更 %d 张表 / 未解析 %d / 空值 %d'
      % ('DRY' if A.dry_run else 'OK', len(set(TOUCHED)), len(CHANGED), len(MISS), len(bad)))
if MISS or bad:
    sys.exit(2)
