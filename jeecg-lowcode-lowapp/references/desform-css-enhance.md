# CSS 增强（CSS Enhancement）

表单设计器支持通过 CSS 增强自定义表单样式，覆盖默认样式或实现特殊视觉效果。

## JSON 存储位置

CSS 增强存储在 `designFormJson.config` 中：

```json
{
  "config": {
    "expand": {
      "js": "",
      "css": "/* 内联 CSS 代码 */",
      "url": {
        "js": "",
        "css": "/desform/expand/css/custom.css"
      }
    },
    "disableMobileCss": true
  }
}
```

- `expand.css` — 内联 CSS 代码
- `expand.url.css` — 外部 CSS 文件 URL
- `disableMobileCss` — 移动端是否禁用 CSS 增强（默认 `true`）

## 执行机制

1. CSS 通过动态创建 `<style>` 标签注入到 `document.head`
2. 样式 ID 为 `__view-css-expand`（同一表单只有一个样式标签，后加载的覆盖前面的）
3. 如果同时配置了内联 CSS 和外部 CSS URL，两者会合并（内联在前，外部在后）
4. 移动端默认禁用 CSS 增强（`disableMobileCss: true`），可设为 `false` 启用

## 常用 CSS 选择器

### 表单整体

```css
/* 表单容器（GenerateForm.vue 最外层） */
.j-generate-form { }

/* 表单项 */
.j-desform-form-item { }

/* 表单标签 */
.el-form-item__label { }

/* 表单内容区域 */
.el-form-item__content { }
```

### 控件类型选择器

通过 `data-widget-type` 属性选择特定类型的控件：

```css
/* 输入框 */
.j-desform-form-item[data-widget-type="input"] { }

/* 日期 */
.j-desform-form-item[data-widget-type="date"] { }

/* 子表 */
.j-desform-form-item[data-widget-type="sub-table-design"] { }

/* 公式 */
.j-desform-form-item[data-widget-type="formula"] { }
```

### 通过 model / key 精确定位字段

每个表单项同时输出 `data-widget-model` 和 `data-widget-key` 两个属性（由 `GenerateFormItem.vue` 渲染），可精确选中单个字段：

```css
/* 通过 data-widget-model 定位（model 是字段数据绑定键） */
.j-desform-form-item[data-widget-model="input_1234567_123456"] {
  /* 特定字段的样式 */
}

/* 通过 data-widget-key 定位（key 是字段唯一标识） */
.j-desform-form-item[data-widget-key="1234567_123456"] {
  background-color: #fffbe6;
}
```

> `data-widget-model` 和 `data-widget-key` 的值可在设计器右侧属性面板底部的「数据绑定Key」处查看。

### Word 风格相关

```css
/* Word 风格栅格 */
.form-grid-word-theme { }

/* Word 风格栅格的列 */
.form-grid-word-theme > .el-col { }

/* Word 风格子表 */
.form-sub-table-word-theme { }
.form-sub-table-word-theme .el-table { }

/* Word 风格子表内嵌栅格 */
.form-sub-table-word-theme.inner-grid { }
```

## 常用样式示例

### 隐藏特定字段标签

```css
.j-desform-form-item[data-widget-model="my_field"] .el-form-item__label {
  display: none;
}
```

### 修改字段宽度

```css
.j-desform-form-item[data-widget-model="my_field"] {
  width: 50% !important;
}
```

### 修改表单标签样式

```css
.el-form-item__label {
  font-weight: bold;
  color: #333;
}
```

### 子表样式定制

```css
/* 子表表头背景色 */
.form-sub-table .el-table th {
  background-color: #e6f7ff !important;
  color: #1890ff;
  font-weight: 600;
}

/* 子表斑马纹 */
.form-sub-table .el-table__row:nth-child(even) {
  background-color: #f6ffed;
}
.form-sub-table .el-table__row:nth-child(odd) {
  background-color: #ffffff;
}

/* 子表行悬停效果（注意：el-table 的 hover 通过 JS 添加 .hover-row 类实现，不能用 :hover 伪类） */
.form-sub-table .el-table__row.hover-row > td {
  background-color: #bae7ff !important;
}
```

### Word 风格边框颜色修改

```css
/* 将 Word 风格默认黑色边框改为灰色 */
.form-grid-word-theme {
  border-color: #d9d9d9;
}
.form-grid-word-theme > .el-col {
  border-right-color: #d9d9d9;
}
.form-sub-table-word-theme .el-table {
  border-color: #d9d9d9;
}
.form-sub-table-word-theme thead th,
.form-sub-table-word-theme tbody td {
  border-bottom-color: #d9d9d9 !important;
  border-right-color: #d9d9d9 !important;
}
```

### 打印样式优化

```css
@media print {
  /* 打印时隐藏操作按钮 */
  .editable-action-btn {
    display: none !important;
  }
  /* 打印时子表不显示滚动条 */
  .form-sub-table-word-theme .el-table__body-wrapper {
    overflow: hidden !important;
  }
}
```

## 外部 CSS 文件

外部 CSS 文件通常放在 JeecgBoot 后端的静态资源目录下：

- 路径格式：`/desform/expand/css/your-theme.css`
- 实际部署位置取决于后端的静态资源配置

## desform_utils.py 中设置 CSS 增强

```python
# 在 save_design 的 config 中设置 CSS
config = {
    "expand": {
        "js": "",
        "css": ".el-form-item__label { font-weight: bold; }",
        "url": {
            "js": "",
            "css": ""
        }
    },
    "disableMobileCss": True
}
```

## 注意事项

1. CSS 增强是全局生效的，注意选择器的精确性，避免影响页面其他元素
2. 使用 `!important` 时要谨慎，可能导致后续样式难以覆盖
3. 移动端默认禁用 CSS 增强，如需移动端也生效需设置 `disableMobileCss: false`
4. 表单关闭时样式标签会自动清理，不会残留
5. Word 风格（`formStyle: 'word'`）由 `_apply_word_layout` 自动处理，CSS 增强中无需重复设置 Word 主题的基础边框样式
6. 仅预览/使用时 CSS 增强生效，设计器中不生效

## 移动端表单视图样式

移动端表单视图通过 `config.designMobileView = true` 和 `config.disableMobileCss` 控制。

**设备尺寸变量**（mobileView.scss）：
- iPhone 5：320×568px
- iPhone 6/7/8：375×667px
- iPhone 6+：414×736px
- iPad：768×1024px

**移动端布局规则**：
- `designMobileView=true` 时，所有栅格列强制 `span=24`（全宽）
- `disableMobileCss=true`（默认）时移动端禁用自定义 CSS
- 设为 `false` 可让 CSS 增强在移动端也生效

**有 mobileOptions 的控件**：

| 控件 | mobileOptions | 说明 |
|------|--------------|------|
| radio / checkbox | `{inline: true, matrixWidth: 120}` | 横向排列 |
| date / time | `{editable: false}` | 禁用手动输入 |

## 打印样式定制

打印时浏览器进入 `@media print` 模式，以下选择器可定制打印效果：

```css
@media print {
  /* 强制显示背景颜色（checkbox/radio 选中状态） */
  * {
    print-color-adjust: exact !important;
    -webkit-print-color-adjust: exact !important;
  }

  /* 隐藏必填星号 */
  .el-form-item__label::before { display: none; }

  /* 隐藏下拉箭头 */
  .el-select__caret { display: none !important; }

  /* 隐藏占位符 */
  input::placeholder { color: transparent !important; }

  /* 修复 radio/checkbox 边框颜色 */
  .el-radio__input:not(.is-checked) > span.el-radio__inner,
  .el-checkbox__input:not(.is-checked) > span.el-checkbox__inner {
    border-color: #696969 !important;
  }
}
```

**打印模式专用类名**：
- `.j-desform-form-item-printer` — 打印模式表单项
- `.j-desform-form-item-printer-text` — 打印文本
- `.j-editable-printer-text` — 可编辑区域打印文本
- `.j-detail-action` — 详情模式动作
