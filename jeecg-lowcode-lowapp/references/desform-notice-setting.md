# 填报通知

当表单有新的填写记录时自动通知指定人员。所有字段均存储在 `designConfig.config` 中，通过 `update_design_config` 修改。

---

## config 字段说明

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enableNotice` | boolean | `false` | 是否启用通知 |
| `noticeMode` | string | `"external"` | 通知触发模式，见下方枚举 |
| `noticeType` | string | `"system"` | 通知方式，**逗号分隔的多选值**，见下方枚举 |
| `noticeReceiver` | string | `""` | 通知接收人，**逗号分隔的 username（sysUserCode）** |

---

## noticeMode 枚举值

| 值 | 含义 |
|----|------|
| `"external"` | 仅外部链接通知（通过外部链接填报时才发通知） |
| `"always"` | 总是通知（任何途径填报均发通知） |

---

## noticeType 枚举值（多选，逗号拼接）

| 值 | 含义 |
|----|------|
| `"system"` | 系统通知（站内通知） |
| `"email"` | 邮件 |
| `"wechat_enterprise"` | 企业微信 |
| `"dingtalk"` | 钉钉 |

多种通知方式同时使用时，逗号拼接：`"system,email"`

---

## 校验规则

`enableNotice=true` 时，以下两个字段**均必填**：
- `noticeType`：不能为空字符串
- `noticeReceiver`：不能为空字符串

前端启用通知时若 `noticeReceiver` 为空，会自动填入当前登录人的 `sysUserCode`。
**AI 配置时需主动传入接收人**，不依赖这个前端默认行为。

---

## noticeReceiver 格式

存储的是**逗号分隔的 username（即 sysUserCode）**，不是用户 ID 也不是用户名称。

```python
# 单人
"admin"

# 多人
"admin,zhangsan,lisi"
```

如何获取用户的 sysUserCode：通过 `jeecg-system` 技能查询用户列表，或让用户提供。

---

## Python 操作示例

```python
from desform_utils import init_api, update_design_config

init_api('<api_base>', '<token>')

# 开启通知（系统通知 + 邮件，仅外部链接时触发）
update_design_config('my_form', {
    "enableNotice": True,
    "noticeMode": "external",
    "noticeType": "system,email",
    "noticeReceiver": "admin",
})

# 总是通知，多人接收，多种方式
update_design_config('my_form', {
    "enableNotice": True,
    "noticeMode": "always",
    "noticeType": "system,dingtalk",
    "noticeReceiver": "zhangsan,lisi,wangwu",
})

# 关闭通知
update_design_config('my_form', {"enableNotice": False})
```
