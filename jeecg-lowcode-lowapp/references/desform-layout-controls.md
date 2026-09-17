# 布局控件详解（AutoGrid / Card / Grid / Tabs）

表单设计器的布局体系由四层构成，AI 在生成表单 JSON 时必须正确理解这些布局机制。

## Card 的两种形态

表单设计器中存在两种 `type=card` 的组件，功能完全不同：

| 属性 | AutoGrid Card | 普通 Card |
|------|:---:|:---:|
| `isAutoGrid` | `true` | `false` 或不存在 |
| 用户可见性 | 不可见（自动布局容器） | 可见（带标题、边框） |
| 最大子控件数 | 4 | 无限制 |
| 允许的子控件 | 仅非布局控件 | 非布局控件、AutoGrid Card、普通 Card、Grid、Tabs |

- **AutoGrid Card** 是系统自动创建的透明布局容器，用于将 1~4 个普通控件排列在同一行
- **普通 Card** 是用户手动创建的可见卡片容器，用于分组展示

## 一、AutoGrid（自动栅格）

### 机制说明

AutoGrid 是默认启用的自动布局机制。当 `config.disabledAutoGrid = false`（默认）时，每个普通控件都必须包裹在一个 `card` 容器中。

**全局开关**：`config.disabledAutoGrid`
- `false`（默认）：启用 AutoGrid，所有普通控件需要 card 包裹
- `true`：禁用 AutoGrid（Word 风格表单会设为 true）

### AutoGrid card 结构

```json
{
  "type": "card",
  "isAutoGrid": true,
  "isContainer": true,
  "list": [/* 1~4 个普通控件 */],
  "options": {},
  "key": "{timestamp}_{random6}",
  "model": "card_{timestamp}_{random6}"
}
```

### AutoGrid 绕过条件（源码精确逻辑）

前端 `componentsConfig.js` 中 `AutoGrid.check(widget)` 决定控件能否进入 AutoGrid Card：

```javascript
const NoEntryAutoGrid = ['map', 'markdown', 'editor', divider]

AutoGrid.check = (widget) => {
  if (widget.isContainer) return false           // ① 容器控件
  if (NoEntryAutoGrid.includes(widget.type)) return false  // ② 特定控件
  if (widget.type === 'link-record') {
    if (widget.isSubTable || widget.options?.showType === 'table') return false  // ③ link-record 特判
  }
  return true  // ④ 其余控件都应在 AutoGrid Card 中
}
```

**不进入 AutoGrid（独立占行）的控件：**
- **容器控件**（`isContainer: true`）：grid, card, tabs, sub-table-design
- **NoEntryAutoGrid 列表**：map, markdown, editor, divider
- **link-record 特判**：当 `showType='table'` 或 `isSubTable=true` 时

**应该进入 AutoGrid 的控件：**
- 所有其他控件，**包括 text 和 buttons**（它们虽然不存储数据，但仍需在 AutoGrid Card 中以获得正确的布局行为）
- link-record 当 `showType='card'` 或 `showType='select'` 时（无论 showMode 是 single 还是 many）

### autoWidth 宽度分配

card 内控件通过 `options.autoWidth` 控制宽度占比：

| card 内控件数 | 每个控件 autoWidth | 效果 |
|:---:|:---:|:---:|
| 1 | 100 | 整行 |
| 2 | 50 | 半行（两列） |
| 3 | 33.333 | 三等分 |
| 4 | 25 | 四等分 |

支持的 autoWidth 值：`25`, `33.333`, `50`, `66.667`, `75`, `100`

**半行布局示例**（一个 card 放两个控件）：
```json
{
  "type": "card",
  "isAutoGrid": true,
  "isContainer": true,
  "list": [
    {
      "type": "input",
      "name": "姓名",
      "options": { "autoWidth": 50, "required": true, ... },
      ...
    },
    {
      "type": "phone",
      "name": "电话",
      "options": { "autoWidth": 50, ... },
      ...
    }
  ],
  "options": {},
  "key": "1774581245281_700049",
  "model": "card_1774581245281_700049"
}
```

## 二、Card（卡片）

### 完整配置

```json
{
  "type": "card",
  "isContainer": true,
  "list": [/* 控件列表 */],
  "options": {
    "width": "100%",
    "rowNum": 1,
    "hidden": false
  }
}
```

- `list`：容纳的控件数组
- `rowNum`：每行显示的卡片数
- 普通 Card **允许嵌套**普通 Card（递归嵌套），详见上方"Card 的两种形态"和"容器嵌套规则"

## 三、Grid（栅格布局）

### 完整配置

```json
{
  "type": "grid",
  "isContainer": true,
  "columns": [
    {
      "span": 12,
      "list": [/* 左列控件 */],
      "options": {
        "flex": false,
        "flexAlignItems": "flex-start",
        "flexJustifyContent": "start"
      }
    },
    {
      "span": 12,
      "list": [/* 右列控件 */],
      "options": { ... }
    }
  ],
  "options": {
    "gutter": 8,
    "justify": "start",
    "align": "top",
    "isWordStyle": false,
    "hidden": false
  }
}
```

### 参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| `columns` | Array | 列配置数组 |
| `span` | Number | 栅格宽度（24 分制，所有列 span 之和应为 24） |
| `gutter` | Number | 列间距（px） |
| `justify` | String | 水平对齐：start / center / end / space-between / space-around |
| `align` | String | 垂直对齐：top / middle / bottom |
| `isWordStyle` | Boolean | Word 文档风格（带边框表格样式） |
| `flex` | Boolean | 列内是否启用 flex 布局 |

### 常用 span 组合

| 布局 | columns span |
|------|-------------|
| 两列等分 | `[12, 12]` |
| 三列等分 | `[8, 8, 8]` |
| 四列等分 | `[6, 6, 6, 6]` |
| 左窄右宽 | `[6, 18]` |
| 左宽右窄 | `[18, 6]` |
| Word 标签+控件 | `[6, 18]`（单列行）或 `[6, 6, 4, 8]`（双列行） |

## 四、Tabs（选项卡）

### 完整配置

```json
{
  "type": "tabs",
  "isContainer": true,
  "panes": [
    {
      "name": "tab_1",
      "label": "基本信息",
      "list": [/* 控件列表 */],
      "rowNum": 1,
      "hidden": false,
      "hiddenOnAdd": false
    },
    {
      "name": "tab_2",
      "label": "详细信息",
      "list": [/* 控件列表 */],
      "hidden": false,
      "hiddenOnAdd": true
    }
  ],
  "options": {
    "activeName": "tab_1",
    "type": "border-card",
    "position": "top",
    "width": "100%",
    "hidden": false
  }
}
```

### 参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| `panes` | Array | 标签页数组 |
| `name` | String | pane 唯一标识（不可重复） |
| `label` | String | 标签显示文本 |
| `list` | Array | pane 内的控件数组 |
| `hiddenOnAdd` | Boolean | 新增数据时隐藏此 tab |
| `activeName` | String | 默认激活的 pane name |
| `type` | String | 样式：`card` / `border-card` |
| `position` | String | 标签位置：`top` / `left` / `right` / `bottom` |

## 容器嵌套规则

### 嵌套矩阵

| 父容器 ↓ \ 可放置 → | AutoGrid Card | 普通 Card | Grid | Tabs | 非布局控件 |
|---------------------|:---:|:---:|:---:|:---:|:---:|
| **主布局（根层级）** | ✅ | ✅ | ✅ | ✅ | ❌（应在容器中） |
| **AutoGrid Card** | ❌ | ❌ | ❌ | ❌ | ✅（1~4 个） |
| **普通 Card** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Grid 列** | ❌ | ✅ | ✅ | ✅ | ✅（裸控件） |
| **Tabs 面板** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **sub-table-design 列** | ❌ | ❌ | ❌ | ❌ | ✅（28 种） |

### 关键规则

1. **AutoGrid Card 内只能放非布局控件**，不能嵌套任何容器
2. **Grid 列内不允许直接放置 AutoGrid Card**，但允许放置普通 Card 和 Tabs
3. **普通 Card 允许嵌套普通 Card**（递归嵌套）
4. **Tabs 允许嵌套 Tabs**（递归嵌套）
5. **sub-table-design 内不允许任何布局组件**，仅支持 28 种非布局控件

### 间接嵌套

虽然 Grid 列不允许直接放置 AutoGrid Card，但可通过中间容器间接使用自动布局：

```
Grid 列 → 普通 Card → AutoGrid Card → 普通控件（1~4 个）
Grid 列 → Tabs 面板 → AutoGrid Card → 普通控件（1~4 个）
```

即在 Grid 列内先放一个普通 Card 或 Tabs，其内部仍可享受 AutoGrid 自动布局效果。

## 六、布局渲染优先级

```
1. isAutoGrid: true  → JAutoGridGenerate 组件
2. type === "grid"   → JGridGenerate 组件
3. type === "card"   → JCard 组件
4. type === "tabs"   → JTabs 组件
5. 其他              → el-form-item（普通控件）
```

## 七、Python 工厂函数与布局

### wrap 参数

所有非 NoEntryAutoGrid 的工厂函数都支持 `wrap` 参数控制是否包裹 AutoGrid Card：

| 放置位置 | 调用方式 | wrap | 返回值 |
|---------|---------|:---:|-------|
| 主布局 / 普通 Card / Tabs | `INPUT("姓名")` | True（默认） | `(autoGridCard, key, model)` |
| Grid 列内 | `INPUT("姓名", wrap=False)` | False | `(widget, key, model)` |
| 子表列内 | `INPUT("姓名", is_sub=True, parent_key=sub_key)` | 自动跳过 | `(widget, key, model)` |
| 子表列内（兼容写法） | `SUB_INPUT("姓名", sub_key)` | 自动跳过 | `(widget, key, model)` |

### 无需 wrap 的控件（始终返回裸控件）

以下控件不受 AutoGrid 影响，始终返回 `(widget, key, model)`，无 `wrap` 参数：

- **NoEntryAutoGrid**：`DIVIDER()`, `EDITOR()`, `MARKDOWN()`, `MAP()`
- **容器**：`TABS()`

### 基本用法示例

```python
# 自动布局（默认）—— 工厂函数自动为每个控件包裹 AutoGrid Card
create_form('示例', 'demo', [
    INPUT('姓名'),     # 自动包裹 card，autoWidth=100
    PHONE('电话'),     # 自动包裹 card，autoWidth=100
])

# 半行布局 —— layout='half' 自动两两配对
create_form('示例', 'demo', [
    INPUT('姓名', width=50),
    PHONE('电话', width=50),
], layout='half')

# 不需要 card 的控件直接放在 list 中
create_form('示例', 'demo', [
    INPUT('标题'),
    DIVIDER('分隔线'),    # 不包裹 card
    EDITOR('正文'),       # 不包裹 card
])
```

## 八、非储值控件

以下控件不绑定数据字段，不参与表单数据提交：
`grid`, `card`, `tabs`, `text`, `divider`, `button`, `buttons`, `sub-table-design`
