# JS 增强（JavaScript Enhancement）

表单设计器支持通过 JS 增强在表单加载时执行自定义 JavaScript 代码，实现动态控制字段显隐、值联动、数据校验、HTTP 请求等高级功能。

## JSON 存储位置

JS 增强代码存储在 `designFormJson.config.expand` 中：

```json
{
  "config": {
    "expand": {
      "js": "// 内联 JS 代码",
      "css": "",
      "url": {
        "js": "/desform/expand/js/custom.js",
        "css": ""
      }
    }
  }
}
```

- `expand.js` — 内联 JS 代码（直接写在设计 JSON 中）
- `expand.url.js` — 外部 JS 文件 URL（运行时通过 HTTP 加载）
- 两者可同时使用，内联 JS 先执行，外部 JS 后执行

> **⛔ 易错点（禁止猜测字段名）：** 设计 JSON 中 JS 增强的字段名是 `config.expand.js`，**不是** `config.jsEnhance`、`config.jsCode` 或其他名称。在预处理模式中通过 Python 直接修改设计 JSON 时，必须写：
> ```python
> # 正确写法
> if 'expand' not in design['config']:
>     design['config']['expand'] = {'js': '', 'css': '', 'url': {'js': '', 'css': ''}}
> design['config']['expand']['js'] = js_code
>
> # 错误写法
> design['config']['jsEnhance'] = js_code  # ❌ 字段名错误
> ```

## 执行时机

JS 增强在表单数据模型（models）初始化完成后执行，即所有字段的默认值已设置完毕。
相当于 Vue 的 `mounted` 阶段之后。

## 执行上下文

JS 代码在一个 IIFE 中执行，接收以下参数：

```javascript
(function (event, data, api, on, moment, vm) {
  // 你的 JS 增强代码写在这里
})(event, data, api, on, moment, vm)
```

### `data` — 表单元数据

```javascript
data.desformCode     // 表单编码（string）
data.action          // 当前操作：'add' | 'edit' | 'detail' | 'preview'
data.isAddAction     // 是否为新增操作（boolean）
data.isEditAction    // 是否为编辑操作（boolean）
data.isDetailAction  // 是否为详情操作（boolean）
data.isPreviewAction // 是否为预览操作（boolean）
```

### `api` — 表单操作 API

#### 数据读写

```javascript
// 获取字段值（传 key 返回单个值，不传返回所有 models 对象）
api.getFormData('field_model')
api.getFormData()  // 返回整个 models 对象

// 设置字段值
api.setFormData('field_model', '新值')
```

#### 字段显隐控制

```javascript
// 隐藏字段（设置 options.hidden = true）
api.hide('field_model')

// 显示字段（设置 options.hidden = false）
api.show('field_model')

// 支持批量操作（逗号分隔的 model 字符串或数组）
api.hide('field1,field2,field3')
api.show(['field1', 'field2'])
```

#### 设置控件选项

```javascript
// 设置控件的 options 属性
api.setFormOptions('field_model', 'disabled', true)    // 禁用
api.setFormOptions('field_model', 'placeholder', '请输入')
api.setFormOptions('field_model', 'required', true)    // 设为必填

// 设置加载状态
api.setWidgetLoading('field_model', true)
api.setWidgetLoading('field_model', false)
```

#### 设置子表控件选项（设计子表 sub-table-design）

`api.setFormOptions` 只作用于主表控件，**修改设计子表（sub-table-design）内控件的 options 属性必须用 `api.setSubTableOptions`**。

```javascript
api.setSubTableOptions(
  'sub_table_design_xxx',  // 设计子表 model（第一参）
  'select_xxx',            // 子表字段 model（第二参）
  'options',               // 要修改的 options 属性名（第三参）
  [
    {label: '选项一', value: '1'},
    {label: '选项二', value: '2'}
  ]                        // 属性值（第四参）
)
```

典型场景：主表字段变化时联动修改子表下拉选项。

> **⚠️ 编辑回显必须 `immediate: true`（编辑回显关键）**：`api.watch` 默认只在值**变化**时触发。新增时用户操作会触发，但**编辑已有记录时表单加载即带出已选值，不会触发 watch**，导致子表下拉 options 停留在默认值。加 `immediate: true` 让表单加载时立即按当前选中值初始化一次 options。

```javascript
api.watch({
  'activity_type': {
    handler: function(val) {
      var subTableModel = 'signup_detail'   // 设计子表 model
      var subFieldModel = 'member_item'     // 子表字段 model
      if (val === 'sports') {
        api.setSubTableOptions(subTableModel, subFieldModel, 'options', [
          {label: '篮球', value: 'basketball'},
          {label: '足球', value: 'football'},
          {label: '羽毛球', value: 'badminton'}
        ])
      } else if (val === 'art') {
        api.setSubTableOptions(subTableModel, subFieldModel, 'options', [
          {label: '钢琴', value: 'piano'},
          {label: '舞蹈', value: 'dance'},
          {label: '合唱', value: 'chorus'}
        ])
      }
    },
    immediate: true
  }
})
```

> 若切换时需清空目标字段值（如清空已选课程），用 `handler(val, oldVal)` 并在 `val !== oldVal` 时才 `setFormData` 清空——immediate 首轮执行时 `val === oldVal`，不会误清编辑回显值。

#### 监听字段变化

```javascript
// 监听指定字段值变化
api.watch({
  'field_model_1': function(newVal, oldVal) {
    console.log('字段1变化:', oldVal, '->', newVal)
  },
  'field_model_2': {
    handler: function(newVal, oldVal) {
      // 处理变化
    },
    immediate: true  // 立即执行一次（表单加载即触发，编辑回显初始化用）
  }
})
```

#### HTTP 请求

```javascript
// GET 请求
api.get('/api/data', { param1: 'value1' }).then(res => {
  api.setFormData('result', res.result)
})

// POST 请求
api.post('/api/submit', { key: 'value' }).then(res => {
  console.log(res)
})

// PUT 请求
api.put('/api/update', { id: 1, key: 'value' })

// 通用请求
api.request('/api/custom', { data: 'value' }, 'DELETE')
```

#### 提交前校验

```javascript
// 注册提交前回调（返回 false 阻止提交）
api.onSubmitBefore(async function(models, oldModels) {
  // models: 当前表单数据，oldModels: 修改前的数据（编辑时有值）
  if (!models.name) {
    alert('名称不能为空')
    return false  // 阻止提交
  }
  // 可以在这里修改数据
  models.submit_time = new Date().toISOString()
  return true  // 允许提交
})
```

#### 控件状态控制

```javascript
// 设置控件加载状态（显示 loading 动画）
api.setWidgetLoading('field_model', true)
api.setWidgetLoading('field_model', false)

// 设置控件 options 属性
// model 支持字符串或数组（批量设置）
api.setFormOptions('field_model', 'disabled', true)
api.setFormOptions(['field1', 'field2'], 'hidden', true)
```

#### 大数据模式事件（bigDataMode=true 时可用）

```javascript
// 监听控件 change 事件
api.onChange('field_model', function(value) {
  console.log('值变化:', value)
})

// 取消监听
api.offChange('field_model', handler)
```

#### 获取当前数据 ID

通过解析 URL 路径获取当前编辑/详情的数据 ID：

```javascript
// URL 格式：/desform/edit/{formCode}/{dataId} 或 /desform/detail/{formCode}/{dataId}
function getId() {
  var match = /\/desform\/(edit|detail)\/.+\/(.+)$/.exec(
    window.location.pathname
  );
  if (match && match.length === 3) {
    return match[2];
  }
  return "";
}

// 使用示例
var dataId = getId()
if (dataId) {
  console.log('当前数据ID:', dataId)
  // 可用于调用后端接口
  api.get('/api/some-endpoint', { id: dataId }).then(res => {
    // 处理返回数据
  })
}
```

> **注意：** 仅在编辑（edit）和详情（detail）模式下 URL 中包含数据 ID，新增模式下无法获取。

#### 其他

```javascript
// 获取上下文变量（如 sysDate、sysUserCode 等）
api.getContextVar('varName')

// 批量执行所有填值规则
api.executeAllFillRule()
```

### `on` — 事件监听

```javascript
// 关联记录编辑模式点击提交按钮时触发
on.linkRecordEditSubmit = function(params) {
  // params.desformCode — 关联表单编码
  // params.data — 提交的数据
  // params.getResult() — 获取提交结果
  console.log('关联记录提交:', params.data)
}
```

### `moment` — 日期处理库

```javascript
// 获取当前时间
moment().format('YYYY-MM-DD HH:mm:ss')

// 日期加减
moment().add(7, 'days').format('YYYY-MM-DD')
moment().subtract(1, 'months').format('YYYY-MM-DD')

// 日期差值
moment('2024-12-31').diff(moment('2024-01-01'), 'days')  // 365
```

### `vm` — Vue 组件实例

直接访问 Vue 组件实例，可用于高级操作（一般不推荐直接使用）。

## 完整示例

### 示例1：根据操作类型控制字段显隐

```javascript
// 新增时隐藏审批字段，编辑时显示
if (data.isAddAction) {
  api.hide('approve_status,approve_user,approve_time')
} else {
  api.show('approve_status,approve_user,approve_time')
}
```

### 示例2：字段联动

```javascript
// 选择类型后自动填充相关字段
api.watch({
  'select_type_model': function(val) {
    if (val === 'urgent') {
      api.setFormData('priority_model', 'H')
      api.setFormOptions('reason_model', 'required', true)
    } else {
      api.setFormData('priority_model', 'M')
      api.setFormOptions('reason_model', 'required', false)
    }
  }
})
```

### 示例3：从后端加载数据填充表单

```javascript
if (data.isAddAction) {
  api.get('/api/defaults', { type: 'leave' }).then(res => {
    if (res.success) {
      api.setFormData('dept_model', res.result.deptName)
      api.setFormData('user_model', res.result.userName)
    }
  })
}
```

### 示例4：提交前数据校验

```javascript
api.onSubmitBefore(async function(models, oldModels) {
  // 验证日期范围
  if (models.end_date && models.start_date) {
    if (moment(models.end_date).isBefore(models.start_date)) {
      alert('结束日期不能早于开始日期')
      return false
    }
  }
  return true
})
```

## 通过 JSON 配置设置 JS/CSS 增强

`desform_creator.py` 的 JSON 配置直接支持 `expand` 字段：

```json
{
  "formName": "请假申请",
  "formCode": "oa_leave",
  "fields": [...],
  "expand": {
    "js": "api.watch({ 'select_model': function(val) { if (val === 'A') { api.hide('field_b') } else { api.show('field_b') } } })",
    "css": ".el-form-item__label { font-weight: bold; }",
    "url": {
      "js": "",
      "css": "/desform/expand/css/custom.css"
    }
  }
}
```

`expand` 中的四个字段均为可选，只需填写需要的部分即可。

## 通过 Python 脚本设置 JS/CSS 增强

`create_form` 和 `save_design` 均支持 `expand` 参数：

```python
create_form('请假申请', 'oa_leave', widgets, layout='auto', expand={
    "js": """
api.watch({
  'select_model': function(val) {
    if (val === 'A') {
      api.hide('field_b')
    } else {
      api.show('field_b')
    }
  }
})
""",
    "css": ".el-form-item__label { font-weight: bold; }",
    "url": {"js": "", "css": ""}
})
```

## 注意事项

1. JS 代码在 `<script>` 标签中执行，享有完整的浏览器 API 访问权限
2. 代码执行出错不会阻断表单加载，但会在控制台输出错误信息
3. `api.watch` 的回调只在值真正变化时触发（`val !== oldVal`），避免不必要的触发
4. 外部 JS URL 支持绝对路径和相对路径（相对于后端服务地址）
5. 移动端和 PC 端共用同一套 JS 增强代码，需自行判断 `data.action` 或设备类型
