#!/usr/bin/env python3
"""租户组织探针（只读）：设计审批人之前先看清「能落到谁」。

requirement-design.md 第 5 步要求「设计前查角色和成员」，以前每个代理都自己写探针
（2026-09-24 第 4、5 轮各写一遍）。本脚本一次列出：

  · 角色：roleCode / 名称 / 成员账号（审批节点 roles=[...] 选这里的）
  · 部门树：名称 / id
  · 用户：账号 / 姓名 / 所属部门 / 负责部门（「部门负责人」审批取的就是这个；没人负责的部门任务无人可办）

用法：
  python tenant_probe.py --api-base URL --token TOKEN --tenant-id 2 [--json]
"""
import argparse
import json
import sys
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:                                    # noqa: BLE001
    pass


def main():
    ap = argparse.ArgumentParser(description='租户组织探针（只读）')
    ap.add_argument('--api-base', required=True)
    ap.add_argument('--token', required=True)
    ap.add_argument('--tenant-id', required=True)
    ap.add_argument('--json', action='store_true', help='输出 JSON（给脚本用）')
    a = ap.parse_args()
    base = a.api_base.rstrip('/')

    def get(path, **params):
        url = base + path + ('?' + urllib.parse.urlencode(params) if params else '')
        req = urllib.request.Request(url, headers={'X-Access-Token': a.token, 'X-Tenant-Id': str(a.tenant_id)})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode('utf-8')).get('result')

    def recs(res):
        return (res.get('records') if isinstance(res, dict) else res) or []

    roles = []
    for r in recs(get('/sys/role/list', pageNo=1, pageSize=500)):
        if str(r.get('tenantId') or a.tenant_id) != str(a.tenant_id):
            continue
        mem = recs(get('/sys/user/userRoleList', roleId=r['id'], pageNo=1, pageSize=200))
        roles.append({'roleCode': r.get('roleCode'), 'roleName': r.get('roleName'),
                      'members': [u.get('username') for u in mem]})

    departs, dname = [], {}

    def walk(nodes, lv=0):
        for x in nodes or []:
            departs.append({'id': x.get('id'), 'name': x.get('departName'), 'level': lv})
            dname[x.get('id')] = x.get('departName')
            walk(x.get('children'), lv + 1)
    walk(get('/sys/sysDepart/queryTreeList'))

    users = []
    for u in recs(get('/sys/user/list', pageNo=1, pageSize=500)):
        lead = [d for d in str(u.get('departIds') or '').split(',') if d] if str(u.get('userIdentity')) == '2' else []
        users.append({'username': u.get('username'), 'realname': u.get('realname'),
                      'depart': u.get('orgCodeTxt'), 'leads': [dname.get(d, d) for d in lead]})

    if a.json:
        print(json.dumps({'roles': roles, 'departs': departs, 'users': users}, ensure_ascii=False, indent=1))
        return
    print('== 角色（审批 roles=[...] 从这里选；成员为空 = 任务无人可办）')
    for r in roles:
        print('  %-18s %-10s 成员：%s' % (r['roleCode'], r['roleName'], '、'.join(r['members']) or '（无）'))
    print('== 部门')
    for d in departs:
        print('  ' + '  ' * d['level'] + '%s  (%s)' % (d['name'], d['id']))
    print('== 用户（负责部门 = 「部门负责人」审批落到谁）')
    for u in users:
        print('  %-12s %-8s 所属：%-12s 负责：%s' % (u['username'], u['realname'], u['depart'] or '-',
                                                 '、'.join(u['leads']) or '-'))
    led = {x for u in users for x in u['leads']}
    orphan = [d['name'] for d in departs if d['name'] not in led]
    if orphan:
        print('⚠️ 没有负责人的部门：%s —— 发起人在这些部门时「部门负责人」审批无人可办' % '、'.join(orphan))


if __name__ == '__main__':
    main()
