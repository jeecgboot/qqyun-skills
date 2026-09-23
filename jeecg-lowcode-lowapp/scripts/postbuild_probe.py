# -*- coding: utf-8 -*-
"""建后探查：把应用真机结构 dump 成 probe.json / dicts.json，供 postbuild_* 系列脚本读取。
只读、不改任何配置。build_app 之后、每次结构补丁（改名/子表转换）之后都要重跑一次。

  python postbuild_probe.py --api-base URL --token T --tenant-id N --app-id A [--work DIR]

产物（默认 {tmp}/jeecg-desform/<app-id>/）：
  probe.json  {表名: {code, menuId, hideFlag, titleField, widgets:[{name,key,model,type,...}]}}
  dicts.json  {字典名: {选项文案: 落库值}}
"""
import sys, os, json, argparse, tempfile, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from desform_lowapp_utils import init_lowapp, get_menus
from desform_utils import query_form

ap = argparse.ArgumentParser()
ap.add_argument('--api-base', required=True)
ap.add_argument('--token', required=True)
ap.add_argument('--tenant-id', required=True)
ap.add_argument('--app-id', required=True)
ap.add_argument('--work', default=None)
A = ap.parse_args()
WORK = A.work or os.path.join(tempfile.gettempdir(), 'jeecg-desform', A.app_id)
os.makedirs(WORK, exist_ok=True)
TID = int(A.tenant_id) if str(A.tenant_id).isdigit() else A.tenant_id

init_lowapp(A.api_base, A.token, tenant_id=TID, app_id=A.app_id)

menus = get_menus(A.app_id) or {}
forms = []


def walk_menu(nodes):
    for n in nodes or []:
        if n.get('type') == 'form' and n.get('desformCode'):
            forms.append({'name': n.get('menuName'), 'code': n.get('desformCode'),
                          'menuId': n.get('id'), 'hideFlag': n.get('hideFlag')})
        walk_menu(n.get('children'))


walk_menu(menus.get('menuList') or menus.get('result') or [])


def iter_w(node, out):
    """递归所有控件：list / columns[].list / panes[].list"""
    if isinstance(node, dict):
        if node.get('type') and node.get('type') not in ('card', 'grid') and node.get('key'):
            out.append(node)
        for k in ('list', 'columns', 'panes'):
            v = node.get(k)
            if isinstance(v, list):
                for it in v:
                    iter_w(it, out)
    elif isinstance(node, list):
        for it in node:
            iter_w(it, out)
    return out


data, fails = {}, []
for f in forms:
    try:
        design = json.loads(query_form(f['code'])['desformDesignJson'])
    except Exception as e:
        fails.append('%s %s' % (f['name'], e))
        continue
    ws = []
    for w in iter_w(design.get('list') or [], []):
        o = w.get('options') or {}
        ws.append({'name': w.get('name'), 'key': w.get('key'), 'model': w.get('model'),
                   'type': w.get('type'), 'isSubTable': w.get('isSubTable'),
                   'sourceCode': o.get('sourceCode'), 'showMode': o.get('showMode'),
                   'showType': o.get('showType'), 'twoWayModel': o.get('twoWayModel'),
                   'titleField': o.get('titleField'), 'showFields': o.get('showFields'),
                   'saveType': o.get('saveType'), 'linkRecordKey': o.get('linkRecordKey'),
                   'showField': o.get('showField'), 'fieldType': o.get('fieldType'),
                   'linkTable': o.get('linkTable'), 'field': o.get('field'),
                   'dictCode': o.get('dictCode'), 'remote': o.get('remote'),
                   'hidden': o.get('hidden'), 'hiddenOnAdd': o.get('hiddenOnAdd'),
                   'autoWidth': o.get('autoWidth'), 'dtype': o.get('type')})
    data[f['name']] = {'code': f['code'], 'menuId': f['menuId'], 'hideFlag': f['hideFlag'],
                       'titleField': (design.get('config') or {}).get('titleField'),
                       'widgets': ws}

json.dump(data, open(os.path.join(WORK, 'probe.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

# 应用字典：选项文案 → 落库值（落库值是序号串 "0"/"1"…，不是文案）
dicts = {}
try:
    out = subprocess.run([sys.executable, os.path.join(HERE, 'lowapp_dict.py'),
                          '--api-base', A.api_base, '--token', A.token,
                          '--tenant-id', str(A.tenant_id), '--app-id', A.app_id,
                          '--action', 'query'],
                         capture_output=True, text=True, encoding='utf-8').stdout
    dec = json.JSONDecoder()
    for i, ch in enumerate(out):
        if ch == '{':
            try:
                obj, _e = dec.raw_decode(out[i:])
            except Exception:
                continue
            if isinstance(obj, dict) and 'result' in obj:
                for d in (obj.get('result') or []):
                    dicts[d.get('dictName')] = {it.get('itemText'): it.get('itemValue')
                                                for it in (d.get('dictItemsList') or [])}
                break
except Exception as e:
    fails.append('字典查询 %s' % e)
json.dump(dicts, open(os.path.join(WORK, 'dicts.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print('OK:probe 表 %d 张 / 字典 %d 个 -> %s' % (len(data), len(dicts), WORK))
for x in fails:
    print('FAIL:' + x)
if fails:
    sys.exit(2)
