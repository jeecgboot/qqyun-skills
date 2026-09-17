# iframe 通信协议

Vue3 框架层与 Vue2 设计器/渲染器通过 postMessage 通信。

## 消息格式

```json
{ "messageId": "唯一ID", "type": "消息类型", "data": {} }
```

`messageId` 用于区分多个 iframe 实例。

## iframe → 父窗口

| type | data | 说明 |
|------|------|------|
| `close` | — | 关闭表单 |
| `success` | {dataId} | 保存成功 |
| `reload` | — | 刷新 |
| `save` | {version, json} | 保存数据 |
| `height-change` | number | 高度自适应 |
| `dialog-change` | {value, time, uni} | 弹窗状态变化（uni: 是否独占模式） |
| `dialog-change-reset` | {uni} | 重置弹窗状态（关闭弹窗后触发） |
| `form-loading-change` | boolean | 加载状态 |
| `show-message` | {type, message} | 消息提示 |
| `force-close` | data | 强制关闭 |
| `route-jump` | {nextRouteConfig, dataId} | 路由跳转 |
| `file-preview` | {name, url} | 文件预览 |
| `open-link-form` | {desformCode, dataId} | 打开关联表单 |
| `base-frame-interaction` | {type, data, cbKey} | 通用交互 |
| `action:validate:callback` | result | 验证回调（返回验证结果） |
| `save:submit-flow` | params | BPM 流程提交（提交数据并触发流程） |
| `event:beforePrint` | params | 打印前 |
| `event:afterPrint` | params | 打印后 |

## 父窗口 → iframe

| type | data | 说明 |
|------|------|------|
| `action:submit` | data | 触发提交 |
| `action:validate` | data | 触发验证（iframe 验证完成后回复 `action:validate:callback`） |
| `action:print` | params | 触发打印 |
| `action:printWithBpmTask` | params | 带流程打印 |
| `body:useRect` | {iframeRect, ...} | 全屏定位 |
| `body:cancelRect` | {agreedTime} | 取消全屏 |
| `link-form:success` | {dataId, eventKey} | 关联表单回调 |
| `base-frame-interaction-callback` | {cbKey, data} | 交互回调 |

## 设计器通信（FormDesignerIframeModal）

### iframe → 父窗口

| type | 说明 |
|------|------|
| `created` | 设计器 UI 初始化完成，父窗口显示设计器界面 |
| `mounted` | 设计器挂载完成，父窗口响应发送 `load-data` 消息传递 token |
| `closing` | 用户尝试关闭设计器，父窗口检查是否有未保存更改 |
| `modal` | 请求父窗口显示弹窗（alert/warning/confirm） |
| `request` | 旧版保存路径（兼容），与 request-save 类似 |
| `request-save` | 保存表单设计 JSON，携带完整设计数据 |
| `custom-button:add` | 打开自定义按钮新增抽屉 |
| `custom-button:edit` | 打开自定义按钮编辑抽屉 |
| `reload:menu` | 请求父窗口刷新菜单（设计器内操作影响了菜单） |
| `show-message` | 请求父窗口显示消息提示（success/error/warning） |
| `preview-fullscreen-change` | 全屏预览状态切换，父窗口隐藏/显示关闭按钮 |
| `base-frame-interaction` | 通用框架交互请求（如打开字典弹窗、AIGC 等），携带 cbKey 用于回调 |

### 父窗口 → iframe

| type | data | 说明 |
|------|------|------|
| `load-data` | `{token}` | 传递认证 token，设计器加载表单数据 |
| `try-close` | — | 通知设计器尝试关闭，设计器检查未保存更改后回复 `closing` |
| `change-page` | `{page}` | 切换设计器标签页（如"设计表单"/"表单设置"） |
| `custom-button:command` | `{command, data}` | 执行自定义按钮命令 |
| `base-frame-interaction-callback` | `{cbKey, data}` | 框架交互回调（如字典弹窗选择完成后返回数据） |
