# 简流 API 接口参考

## 目录

- [前置查询接口](#前置查询接口)
- [创建/修改/发布简流](#创建修改发布简流)
- [Desform 自定义按钮 API](#desform-自定义按钮-api)
- [节点字段权限 API](#节点字段权限-api)

---

## 前置查询接口

> ⚠️ 以下路径已验证可用，直接使用，不要猜测其他路径。

**查询当前用户所在租户列表（获取 tenantId）：**
```
GET /sys/tenant/getCurrentUserTenant
X-Access-Token: <token>
```
> 返回 `result.list[]`，包含当前用户所属的所有租户。
> ⚠️ 返回多个租户时，必须展示列表让用户选择使用哪个，不可自动选第一个。
> ❌ `/sys/tenant/list` 是管理员查所有租户，不要用于获取当前用户租户ID。

**✅ 推荐：一次获取租户下全部应用 + 工作表 + titleField（合并接口）：**
```
GET /online/lowApp/miniflow/tenantAppFormList?tenantId=<tenantId>
X-Access-Token: <token>
X-Tenant-Id: <tenantId>
```
> 返回结构：
> ```json
> {
>   "result": {
>     "apps": [
>       {
>         "id": "<appId>",
>         "name": "<appName>",
>         "desforms": [
>           {
>             "id": "<formId>",
>             "code": "<formCode>",
>             "name": "<formName>",
>             "titleField": "<fieldModel>"
>           }
>         ]
>       }
>     ]
>   }
> }
> ```
> 此接口合并了原来的 `/online/lowApp/queryList` + `/desform/list` + titleField 查询，**优先使用此接口**。
> 注意字段名：app 层用 `id`/`name`，form 层用 `id`/`code`/`name`/`titleField`（均为简短名，无前缀）。

**查询 Desform 表单字段详情（需要完整字段 model 列表时）：**
```
GET /desform/api/fields/<desformCode>?group=true
X-Access-Token: <token>
```
> 仅当需要**全量字段 model**（配置节点字段权限、条件过滤等）时才调用；titleField 已包含在合并接口中，无需重复查询。
> 加 `?group=true` 同时返回字段 `key`（即 `desformComKey`），无需再查 `queryById`。
> 返回结构：`result.titleField`=标题字段 model，`result.fields[].model`=字段 ID，`result.fields[].key`=desformComKey。

**查询简流详情（修改时获取 processJson、updateCount）：**
```
GET /act/process/extActProcess/queryById?id={flowId}
X-Access-Token: <token>
```
> 返回 `result.processJson`（已序列化的 JSON 字符串，需再 parse）、`result.updateCount`、`result.processKey`、`result.lowAppId`。
> ❌ `/act/designer/miniDesFlow/api/queryById` 和 `/act/designer/miniDesFlow/api/getFlowById` 均 404，禁止使用。

**查询应用下流程列表（简流列表页同款，快）：**
```
GET /act/process/extActProcess/list?pageNo=1&pageSize=50
X-Access-Token: <token>
X-Tenant-Id: <tenantId>
X-Low-App-ID: <lowAppId>
```
> 返回 `result.records[]`（`processName`/`lowAppId`/`id`=流程记录 DBid）。实测 0.1s，**只含该应用下的流程**——按应用列流程、或诊断「流程列表慢」用这个。
> ❌ `/act/process/list` 是**引擎定义列表**，**不带应用过滤**（带了 `X-Low-App-ID` 头也返回租户内全部定义），定义多时很慢（457 条实测 3–5s、响应 154KB）——不要拿它当应用流程列表、也不要拿它的耗时当「列表页慢」的证据；它只用于查引擎 key/version（如 subEvent 发布校验，见 SKILL.md subEvent 段）。

**查询部门树（获取 deptId）：**
```
GET /sys/sysDepart/queryTreeList
X-Access-Token: <token>
```
> ⚠️ **不带 X-Tenant-Id 头返回跨组织全量树**：首层根节点是各组织公司节点（含他组织），取「第一条」会命中他组织根部门（2026-09-09 实测）。要取「某租户下部门」，先 `GET /sys/tenant/list` 按组织名定位租户 id，再带 `X-Tenant-Id: <租户id>` 调用——实测带头后返回的才是该租户直属部门列表。

**查询角色列表（获取 roleId/roleCode）：**
```
GET /sys/role/list?pageSize=100&pageNo=1
X-Access-Token: <token>
```
> ⚠️ **接口不做租户过滤**（实测带不带 X-Tenant-Id 头返回结果相同，记录里 tenantId 混有本租户 id / 0 / 1 / null / 他租户 id，2026-09-09 实测）。必须在结果内按 **`tenantId == 当前租户id` 严格相等**过滤再取 roleCode/roleName，禁止 `''/0/None` 宽匹配（会命中根租户/他租户角色，如取组织查询节点条件值时踩中他组织角色）。

**查询用户列表（获取 userId/username）：**
```
GET /sys/user/list?pageSize=100&pageNo=1
X-Access-Token: <token>
```

---

## 创建/修改/发布简流

### 保存简流（创建或修改同一接口）

```
POST /act/designer/miniDesFlow/api/saveFlow
Content-Type: application/x-www-form-urlencoded

updateCount=<当前版本号>      ← 新建传 1；修改必须传当前流程的 updateCount
processJson=<URL 编码的 processJson JSON>
processName=<流程名称>
processKey=<流程 Key>
processType=oa
id=                          ← 创建时留空；修改时填已有流程 ID
customProcessId=
lowAppId=<低代码应用 ID>
startType=tableEvent|manual|...
```

> ⚠️ saveFlow API **只接受 `application/x-www-form-urlencoded`**，禁止用 `application/json`，否则报 "Cannot invoke ProcessData.getCreateStartNode() because process is null"。
> ⚠️ Windows bash 下用 curl 内联中文 JSON 会导致 UTF-8 编码错误。解决方案：JSON 写入文件后用 `--data-binary @file` 发送，或用 Python requests 库。

**创建成功响应：**
```json
{"success": true, "code": 0, "result": {"updateCount": 1, "id": "2041778024880873473"}}
```

**修改成功响应：**
```json
{"success": true, "code": 0, "result": {"updateCount": 2, "id": "2041778024880873473"}}
```

**updateCount 规则：**
- 新建：传 `1`
- 修改：必须传当前流程的实际 updateCount（从 `queryById` 取得），否则报"不是最新版本"

### 删除简流流程记录

```text
DELETE /act/process/extActProcess/delete?id=<流程记录DBid>
头：X-Access-Token + X-Tenant-Id + X-Low-App-ID
```
- id = 流程记录 DB id（query_flow 返回的 id），不是 processKey；方法必须 DELETE（GET 报不支持）
- 实测 2026-09-03：删除成功返回 success:true，记录消失；按钮 create 返回的 processId 若无独立流程记录会报「未找到对应实体」（正常）
- 详见 `gotchas.md` #42

### 发布简流

```
PUT /act/process/extActProcess/deployProcess
Content-Type: application/json

{"id": "2041778024880873473"}
```

> ⚠️ 方法是 **PUT**（前端 `packages/api/index.js` 与 gotchas #47 实测一致；旧文档写 POST 有误）。

**发布成功响应：**
```json
{"success": true, "message": "发布成功!", "code": 200, "result": null}
```

> **重要：** 发布是必须步骤，保存后未发布流程不生效；修改后也需重新发布。
> **⚠️ 请求头带 `X-Tenant-Id` + `X-Low-App-ID`（会话标配）**；subEvent 子流程发布"回成功但查无 process<DBid>"的**真根因是记录缺 `customProcessId` 字段**（deploy 注册出的 key 拼错），配方见 gotchas **#47**——补一次 designer saveFlow 带 `customProcessId=<DBid>` 再 PUT 即全 API 自动注册，与请求头/签名无关。

---

## Desform 自定义按钮 API

`startType=buttonEvent` 的简流需要在 Desform 工作表上创建并绑定自定义按钮。

### 完整操作顺序

```
1. 创建完整的 buttonEvent 简流  →  获得 flow_id
2. POST /desform/button/save（带 flowStatus=true）  →  获得 button_id + auto_process_id
3. POST /desform/button/update（带 processId=flow_id）  →  将按钮绑定到真实简流
```

> `button/save` 只能创建按钮并自动生成空流程 shell，无法在 save 时直接指定已有流程 ID，必须通过 update 接口更换。

### 第一步：创建按钮（POST /desform/button/save）

> ⚠️ **`flowStatus: true` 是必须字段！** 不传或传 `false` 会报 **"操作失败，Id must not be null"**。

```python
button_data = {
    'label': '申请审批',
    'clickThen': 'confirm',                # confirm=弹确认框；direct=直接触发
    'confirmText': {                       # 必须是 JSON 对象，不能是字符串
        'tip': '确认提交审批？',
        'ok': '确定',
        'cancel': '取消'
    },
    'icon': 'CheckCircleOutlined',         # AntDesign 图标名
    'color': '#1890ff',
    'seq': 1,
    'showStatus': 'all',
    'allView': True,
    'flowStatus': True,                    # ← 必须！
    'note': '',
    'designFormCode': 'outbound_manage',   # formTableCode
    'viewId': ''
}

resp = requests.post(f'{api_base}/desform/button/save', json=button_data,
                     headers={'X-Access-Token': token})
button_id = resp.json()['result']['id']
auto_process_id = resp.json()['result']['processId']  # 临时空流程 shell
```

### 第二步：绑定按钮到真实简流（POST /desform/button/update）

```python
button_update = {
    **button_data,
    'id': button_id,
    'processId': flow_id,    # ← 替换为真实简流 flow_id
    'flowStatus': True,
}
requests.post(f'{api_base}/desform/button/update', json=button_update,
              headers={'X-Access-Token': token})
```

### 删除按钮

```python
requests.delete(f'{api_base}/desform/button/remove', params={'id': button_id},
                headers={'X-Access-Token': token})
```

---

## 节点字段权限 API

配置某节点对某字段的显示/编辑权限。

### 查询节点字段权限

```
GET /act/process/extActProcessNodePermission/list?processNodeCode={nodeId}&processId={flowId}&pageSize=100
X-Access-Token: <token>
```

### 批量保存（saveOrUpdateBatch）

```
POST /act/process/extActProcessNodePermission/saveOrUpdateBatch
Content-Type: application/json

[
  {
    "ruleCode": "auto_number_xxx",       // 字段 model 值（不是 desformComKey！）
    "ruleName": "入库单号",
    "desformComKey": "1776337156811_723650",
    "formBizCode": "wh_inbound",
    "formType": "2",
    "processId": "xxx",
    "processNodeCode": "taskXxx",
    "ruleType": "1",                     // "1"=显示权限
    "status": 0                          // 0=隐藏，1=显示
  },
  {
    "ruleCode": "auto_number_xxx",
    "ruleName": "入库单号",
    "desformComKey": "1776337156811_723650",
    "formBizCode": "wh_inbound",
    "formType": "2",
    "processId": "xxx",
    "processNodeCode": "taskXxx",
    "ruleType": "2",                     // "2"=编辑权限
    "status": 1                          // 0=可编辑，1=只读/禁用
  }
]
```

**关键规则：**

1. `ruleCode` 必须是字段 **model 值**（如 `auto_number_xxx`），不是 `desformComKey`
2. 每个字段必须同时提交两条记录（`ruleType=1` 显示权限 + `ruleType=2` 编辑权限），缺一不生效
3. `processJson` 的 `privileges` 数组对简流字段权限无效，必须用此独立 API
4. 只需为有特殊权限的字段保存记录，未配置字段默认"显示+可编辑"
5. **`status` 是字符串**：`"0"` / `"1"`，不是数字
6. **必填**：在 ruleType=1 和 ruleType=2 两条记录上都加 `"required": true`；**禁止** 用 ruleType=3（不存在）
7. **`desformComKey` 必须非空**（= 控件 `key`）：留空则整条权限静默不生效，表现为**审批表单里全部字段仍可编辑**（save 返回 `批量保存成功`）。取值用 `desform_utils.get_form_fields(code)` 的 `key`；⚠️ **别用 `miniflow_creator.fetch_form_fields`**——同名函数，它只返回 `{model,type,options}` 没有 `key`，`info.get('key') or ''` 会静默写空串（2026-09-16 实测：370 行全空返工）

### 批量删除

```
DELETE /act/process/extActProcessNodePermission/deleteBatch?ids=id1,id2,...
X-Access-Token: <token>
```

---

## 补充端点

### 读 processJson 的正门（设计器同款）

```
GET /act/designer/miniDesFlow/api/getProcess?processId=<流程DBid>
```

返回 `Result<MyExtActProcess>`，result 即流程实体（含 processJson/processXml/updateCount）。设计器前端就用它加载流程；`query_flow` 封装的 `/act/process/extActProcess/queryById` 仍可用，两者取一即可。

### 挂起 / 激活流程（比"改名挪移法"正规的停用方式）

```
GET /act/process/close/{processKey}    # 挂起（停用）
GET /act/process/open/{processKey}     # 激活（恢复）
```

> gotchas #42 的「改名挪移法」是删除不便时的兜底；仅想停用/启用流程时优先用这两个端点（路径参数是 processKey，不是 DB id）。
>
> ⚠️ **`close` 会永久拆掉「工作表新增触发」注册，`open` 恢复不了**（2026-09-16 实测，见 gotchas #88）：`close` 过的流程此后**再也不触发**，且 `openStatus=1`、重新 `save_flow`、重新 `deploy_flow` 全部显示正常。**别用 close 做临时停用**；已经 close 过又不触发的，只能 `DELETE extActProcess/delete?id=` 删掉流程记录后重建。

### 立即执行 / 定时预览 / 手动启动

| 端点 | 方法 | 参数 | 用途 |
|---|---|---|---|
| `/act/designer/miniDesFlow/api/executeProcess` | ANY | `dataId`、`processId`、`desformCode` | 按触发动作立即执行一次流程 |
| `/act/designer/miniDesFlow/api/generateExecTime` | ANY | attr 表单参数（beginDateStr/timeCycle 等） | 预览定时流程未来 7 次执行时间 |
| `/act/designer/miniDesFlow/api/buttonStartProcess` | POST | `processId`、`dataId`、`formKey`、`inputParams`(JSON数组`[{field,value}]`)、`applyUserId` | 按钮启动流程（自定义按钮的运行时入口） |

### API 节点 / AI 编排节点辅助端点

| 端点 | 方法 | 参数 | 用途 |
|---|---|---|---|
| `/act/api/hello` | GET/POST/PUT/DELETE | name/type/count 等 | API 节点官方 demo 接口（`@IgnoreAuth` 免登录），调通前可用它联调 |
| `/airag/flow/list` | GET | `pageNo=1&pageSize=999&column=createTime&order=desc&status=enable,release` | 查 AI 编排流程列表（aiOrchestration 节点选 aiProcessId 用） |
| `/airag/flow/queryFlowConfig?id=` | GET | AI 流程 id | 查 AI 流程配置详情（入参/出参定义） |

### 应用级流程管理（SignalProcessController，按需使用）

| 端点 | 方法 | 用途 |
|---|---|---|
| `/act/designer/miniDesFlow/api/copyAppProcess` | POST | 复制应用下全部流程（跨应用/跨租户模板复用） |
| `/act/designer/miniDesFlow/api/backupAppProcess` | PUT | 备份应用流程 |
| `/act/designer/miniDesFlow/api/coverAppProcess` | PUT | 从备份还原 |
| `/act/designer/miniDesFlow/api/deleteAppProcess?appId=` | DELETE | 删除应用下全部流程（危险，慎用） |
