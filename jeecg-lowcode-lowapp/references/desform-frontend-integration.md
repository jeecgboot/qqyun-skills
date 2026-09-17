# 前端集成指南

## DesformView.vue — 表单渲染组件

通过 iframe 展示表单（add/edit/detail 模式）。

### 核心 Props

| Prop | 类型 | 默认 | 说明 |
|------|------|------|------|
| `mode` | string | 必填 | add / edit / detail |
| `desformCode` | string | '' | 表单编码 |
| `dataId` | string | — | 数据ID（edit/detail必填） |
| `viewId` | string | — | 视图ID |
| `lowAppId` | string | — | 应用ID |
| `taskId` | string | '' | 流程任务ID |
| `triggerProcess` | string | '' | 触发流程 |
| `showFooter` | boolean | true | 显示底部按钮 |
| `forceOpenPrint` | boolean | false | 强制开启打印 |
| `innerDialog` | boolean | false | 内部弹窗模式 |
| `eventDialog` | boolean | true | 事件弹关联记录 |
| `skipPage` | boolean | true | 保存后跳转 |
| `isLinkDialog` | boolean | false | 关联表单弹窗 |
| `defaultFormData` | object | — | 默认数据 |
| `minHeight` | number | — | 最小高度 |
| `customButtonId` | string | '' | 自定义按钮ID |

### 事件

| 事件 | 说明 |
|------|------|
| `success` | 保存成功 |
| `close` | 关闭 |
| `reload` | 刷新 |
| `dialogChange` | 弹窗状态变化 |
| `formLoadingChange` | 加载状态变化 |

## DesformViewModal.vue — 表单弹窗组件

### 核心 Props

| Prop | 类型 | 默认 | 说明 |
|------|------|------|------|
| `zIndex` | number | 999 | z-index |
| `showComment` | boolean | true | 显示评论 |
| `showFiles` | boolean | true | 显示文件 |
| `showDataLog` | boolean | true | 显示日志 |
| `showRecordCopy` | boolean | true | 复制按钮 |
| `showRecordShare` | boolean | true | 分享按钮 |
| `showRecordSysPrint` | boolean | true | 打印按钮 |
| `showDesignFormBtn` | boolean | true | 设计按钮 |
| `inlineMode` | boolean | false | 内嵌模式 |
| `index` | number | — | 当前记录下标 |
| `total` | number | — | 总记录数 |

### 集成示例

```vue
<!-- 基础查看 -->
<DesformView mode="detail" desformCode="order" :dataId="id" @success="onSuccess" />

<!-- 弹窗新增 -->
<DesformViewModal ref="modal" @success="reload">
  <template #trigger>
    <a-button @click="modal.openModal({mode: 'add', desformCode: 'order'})">新增</a-button>
  </template>
</DesformViewModal>
```
