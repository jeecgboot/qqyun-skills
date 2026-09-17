# 自定义接收 URL

> ⛔ **强制输出规则（不可忽略）**：向用户回答时，**禁止**提及以下内容：
> - `config_overrides` 参数
> - JSON 配置字段名（如 `customRequestURL`、`transactional`）
> - 任何脚本内部实现细节
>
> **只允许介绍**：功能说明、接口规范（HTTP 方法、入参/返回格式）、事务控制行为、子表数据处理、Java 示例代码。
>
> 违反此规则 = 输出了用户不需要的 AI 实现细节，请在组织回复前先过滤。

## 用途

表单提交时，除了将数据写入系统数据库，还可以同步调用一个自定义后台接口。适用于需要在自己的接口里做二次数据处理、写入其他表、触发业务逻辑等场景。

## JSON 配置

存储在 `designFormDesignJson.config.customRequestURL`：

```json
{
  "config": {
    "customRequestURL": [{ "url": "/desform/customUrlTest" }],
    "transactional": true
  }
}
```

> **重要：`customRequestURL` 虽然是数组，但实际只支持填写 1 个 URL。** 不要配置多个对象，只写第一个元素即可。URL 为空字符串时表示未启用。
>
> **限制：只能填写 `/` 开头的相对路径**（即本项目内的接口地址，如 `/desform/customUrlTest`），不支持 `http://` 或 `https://` 等跨项目的绝对地址。

## 事务控制

通过 `config.transactional` 控制：

| 值 | 行为 |
|----|------|
| `true`（默认） | 自定义接口失败时，表单数据保存操作同步回滚 |
| `false` | 自定义接口失败时，表单数据已保存，不回滚 |

## 接口接收规则

| HTTP 方法 | 触发场景 |
|-----------|---------|
| `POST` | 新增记录 |
| `PUT` | 修改记录 |

**必须用 `@RequestMapping` 同时接收 POST 和 PUT**，不能只写 `@PostMapping` 或只写 `@PutMapping`，否则另一种操作会报错。

接口入参为一个 JSON 对象：

```java
@RequestBody JSONObject json
```

其中表单字段数据在 `json.getJSONObject("desformDataJson")` 里，key 为控件的 `model`（如 `input_1774581245280_703439`）。

## 接口返回规则

建议返回 `org.jeecg.common.api.vo.Result`。如果使用自定义返回类型，必须包含：

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | Boolean | `true` = 成功；`false` = 失败（触发事务回滚） |
| `message` | String | 失败时填写原因，成功时可不填 |

## 子表数据处理

**一对一子表**：字段名格式为 `表名#字段名`，判断是否以 `表名#` 开头即可识别。

**一对多子表**：字段名以 `sub-table-design_` 开头，值为 URLEncode 编码的 JSON 数组，需先解码再解析：

```java
String encoded = json.getString("sub-table-design_xxx");
String decoded = URLDecoder.decode(encoded, "UTF-8");
JSONArray rows = JSONArray.parseArray(decoded);
```

## 完整 Java 示例

```java
/**
 * 自定义接收URL示例：将数据抽取保存到其他表
 */
@RequestMapping("/customUrlTest")
public Result customUrlTest(@RequestBody JSONObject json, HttpServletRequest request) {
    boolean isPost = HttpMethod.POST.matches(request.getMethod());
    // POST = 新增，PUT = 修改
    if (isPost) {
        // 获取请求中携带的 token
        String token = TokenUtils.getTokenByRequest(request);

        // 从 desformDataJson 中读取表单字段（key 为控件的 model）
        JSONObject formData = json.getJSONObject("desformDataJson");
        JSONObject staff = new JSONObject();
        staff.put("name", formData.getString("name"));
        staff.put("sex", formData.getString("sex"));
        staff.put("age", formData.getString("age"));

        // 通过 RESTful 接口保存到另一个表单
        return RestDesformUtil.addOne("extract_test_staff", staff, token);
    } else {
        // 修改操作不处理
        return Result.ok();
    }
}
```

## 启用方式

### 通过 JSON 配置（desform_creator.py）

直接在 JSON 配置中传字符串，脚本自动转为 `[{"url": "..."}]`：

```json
{
  "formName": "员工信息",
  "formCode": "staff_form",
  "fields": [...],
  "customRequestURL": "/desform/customUrlTest",
  "transactional": true
}
```

### 通过 Python 脚本（create_form / update_form）

使用 `config_overrides` dict 传入任意 config 覆盖项：

```python
from desform_utils import init_api, create_form

init_api(api_base, token)
create_form('员工信息', 'staff_form', widgets, config_overrides={
    'customRequestURL': [{'url': '/desform/customUrlTest'}],
    'transactional': True,
})
```

## 注意事项

1. URL 只能配置 **1 个**，不支持多个接口同时接收
2. 接口必须同时处理 POST（新增）和 PUT（修改），推荐用 `@RequestMapping`
3. 接口内通过 `request.getMethod()` 判断是新增还是修改
4. 启用事务时，接口返回 `success: false` 会导致表单数据回滚——接口报错（5xx）也视为失败
5. 子表字段需要额外解码，一对多子表值为 URLEncode 后的 JSON 数组
