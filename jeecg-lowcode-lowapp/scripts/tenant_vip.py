# -*- coding: utf-8 -*-
"""租户升级会员：直连 MySQL 往 sys_vip_membership 插 normalVip 行。

平台没有升级会员的接口可调，会员状态只存在 sys_vip_membership 表里。
用法见 references/tenant-vip.md。
"""
import argparse
import datetime
import difflib
import random
import sys
import time
from urllib.parse import urlparse

import pymysql

VIP = 'normalVip'


def parse_jdbc(url):
    # jdbc:mysql://127.0.0.1:3306/dbname?xxx → (host, port, db)
    u = urlparse(url[len('jdbc:'):] if url.startswith('jdbc:') else url)
    return u.hostname, u.port or 3306, u.path.lstrip('/')


def match_tenant(cur, name):
    # 精确 → 去掉末尾「租户」「组织」再精确 → 包含匹配；只接受唯一命中
    cur.execute("SELECT id,name FROM sys_tenant WHERE del_flag=0")
    tenants = cur.fetchall()
    for cand in (name, name.removesuffix('租户').removesuffix('组织')):
        hit = [t for t in tenants if t[1] == cand]
        if len(hit) == 1:
            return hit[0]
    hit = [t for t in tenants if cand in t[1] or t[1] in cand]
    if len(hit) == 1:
        return hit[0]
    if not hit:
        # 口述漏字（「北京国炬信息有限公司」→「北京国炬信息技术有限公司」）：相似度最高且明显领先才算
        scored = sorted(((difflib.SequenceMatcher(None, cand, t[1]).ratio(), t) for t in tenants), reverse=True)
        if scored and scored[0][0] >= 0.8 and (len(scored) == 1 or scored[0][0] - scored[1][0] >= 0.15):
            return scored[0][1]
    raise SystemExit(f'租户「{name}」匹配到 {len(hit)} 条，请改用 --tenant-id。现有租户：{tenants}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--jdbc-url', required=True, help='application yml 里 datasource.master.url')
    ap.add_argument('--db-user', default='root')
    ap.add_argument('--db-password', default='root')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--tenant-id', type=int, action='append')
    g.add_argument('--tenant-name', action='append')
    g.add_argument('--all', action='store_true', help='所有还没有 normalVip 行的租户')
    ap.add_argument('--years', type=int, default=3, help='有效期年数，默认 3')
    ap.add_argument('--fallback-user', default='admin', help='创建人查不到时挂到这个用户名下')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')

    host, port, db = parse_jdbc(a.jdbc_url)
    conn = pymysql.connect(host=host, port=port, user=a.db_user, password=a.db_password, db=db, charset='utf8mb4')
    cur = conn.cursor()

    if a.all:
        cur.execute("SELECT id FROM sys_tenant WHERE del_flag=0 ORDER BY id")
        tids = [r[0] for r in cur.fetchall()]
    elif a.tenant_name:
        tids = [match_tenant(cur, n)[0] for n in a.tenant_name]
    else:
        tids = a.tenant_id

    cur.execute("SELECT id FROM sys_user WHERE username=%s", (a.fallback_user,))
    row = cur.fetchone()
    if not row:
        raise SystemExit(f'兜底用户 {a.fallback_user} 不存在')
    fallback_uid = row[0]

    today = datetime.date.today()
    end = today.replace(year=today.year + a.years)
    for tid in tids:
        cur.execute("SELECT name,create_by FROM sys_tenant WHERE id=%s", (tid,))
        t = cur.fetchone()
        if not t:
            raise SystemExit(f'租户 {tid} 不存在')
        cur.execute("SELECT COUNT(*) FROM sys_vip_membership WHERE tenant_id=%s AND member_type=%s", (tid, VIP))
        if cur.fetchone()[0]:
            print(f'[跳过] {tid} {t[0]} 已有 {VIP} 行')
            continue
        # 会员挂在租户创建人名下；创建人在 sys_user 查不到（如只存了手机号）就挂兜底用户
        cur.execute("SELECT id FROM sys_user WHERE username=%s OR phone=%s", (t[1], t[1]))
        u = cur.fetchone()
        uid = u[0] if u else fallback_uid
        who = t[1] if u else f'{a.fallback_user}（创建人 {t[1]} 查不到）'
        print(f'[新增] {tid} {t[0]} → {who} {today}~{end}')
        if a.dry_run:
            continue
        new_id = str(int(time.time() * 1000)) + str(random.randint(100000, 999999))
        cur.execute(
            """INSERT INTO sys_vip_membership
               (id,tenant_id,user_id,member_type,start_time,end_time,create_by,create_time,update_by,update_time)
               VALUES (%s,%s,%s,%s,%s,%s,'admin',%s,'admin',%s)""",
            (new_id, tid, uid, VIP, today, end, today, today))
        time.sleep(0.002)
    conn.commit()

    # 回读
    cur.execute(
        """SELECT v.tenant_id,t.name,u.username,v.member_type,v.start_time,v.end_time
           FROM sys_vip_membership v JOIN sys_tenant t ON t.id=v.tenant_id
           LEFT JOIN sys_user u ON u.id=v.user_id WHERE v.tenant_id IN %s ORDER BY v.tenant_id""", (tuple(tids),))
    for r in cur.fetchall():
        print('  ', r)


if __name__ == '__main__':
    main()
