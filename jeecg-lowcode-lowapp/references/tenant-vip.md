# 租户升级会员（sys_vip_membership）

> 2026-09-28 实测：本地库 `jeecgbootsylow3_9` 把北京国炬及其余 5 个租户升为普通会员。

## 结论先看

- **没有接口可调**。敲敲云 API 里没有升级会员的接口，会员状态只存在 MySQL 表 `sys_vip_membership`。
  所以这件事**直连数据库**做，不走 `api-base` / token。
- 数据库连接从用户贴的 application yml 取：`spring.datasource.dynamic.datasource.master.url/username/password`。
  没给就问一句，不要猜库名。
- **一条命令**：`scripts/tenant_vip.py`（依赖 `pymysql`；本机没有 `mysql` 命令行，别找它）。

```bash
# 指定租户（名称或 ID，可重复传）
python "<skill目录>/scripts/tenant_vip.py" --jdbc-url "jdbc:mysql://127.0.0.1:3306/jeecgbootsylow3_9?..." --db-user root --db-password root --tenant-name 北京国炬信息有限公司
python "<skill目录>/scripts/tenant_vip.py" --jdbc-url "..." --tenant-id 1000 --tenant-id 1008
# 所有还不是会员的租户
python "<skill目录>/scripts/tenant_vip.py" --jdbc-url "..." --all
# 先看会改哪些
python "<skill目录>/scripts/tenant_vip.py" --jdbc-url "..." --all --dry-run
```

参数：`--years`（有效期年数，默认 3）、`--fallback-user`（创建人查不到时挂谁，默认 `admin`）。
脚本跑完会回读这些租户的全部会员行。

## 表结构要点

| 字段 | 说明 |
|---|---|
| `id` | varchar(32)，无自增，脚本用 毫秒时间戳+6 位随机数 |
| `tenant_id` | 租户 id |
| `user_id` | 会员挂在哪个用户名下（`sys_user.id`） |
| `member_type` | `default` = 免费用户，`normalVip` = 普通会员 |
| `start_time` / `end_time` | date |
| 短信 / 空间用量列 | 新会员留空（已有会员行也是空） |

一个租户一行 `normalVip` 就算会员；同租户另有 `default` 行（如 3 号租户的 jeecg）不影响，不要顺手改。

## 取值规则（照已有数据定的）

1. **租户名匹配**：精确 → 去掉末尾「租户/组织」再精确 → 包含匹配（唯一）→ 相似度 ≥0.8 且领先第二名 ≥0.15。
   都不满足就报错列出全部租户，改用 `--tenant-id`，不要猜。
   用户口述常不全：说「北京国炬信息有限公司」，库里是「北京国炬信息技术有限公司」。
2. **挂在谁名下**：租户创建人（`sys_tenant.create_by` 按 `sys_user.username` 或 `phone` 查）。
   查不到（实测 1007 华为的创建人是手机号 `13426432920`，用户表里没有）→ 挂 `admin`。
   user_id **不要求是该租户成员**：已有数据里 3 号租户的会员 qinfeng 就不在 `sys_user_tenant` 里。
3. **已有 `normalVip` 行的租户跳过**，不重复插、不改原有效期。
4. `create_by` / `update_by` 写 `admin`，日期写当天。

## 收尾告诉用户

- 改的是哪个库（直连 SQL，不是技能接口）；
- 每个租户挂在谁名下、有效期；有兜底到 admin 的单独点名；
- 后端可能缓存了会员状态，界面仍显示免费版 → 重新登录。
