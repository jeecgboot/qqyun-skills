# QQY UI 组件最小 config（轮播 / iframe / 时钟）

> **按需。** 已点名路径：读 `create.md`「轮播 / iframe / 时钟」要点即可；仅组装 config 卡住时打开本节。  
> 一律 `dataType:1` + `comp/add` + `saveCompToPage`（template **字符串**）；禁止 `add-charts`。  
> `card.title` 必须 `''`。

## JCarousel 轮播

- raw `/desform/api/fields` 取 `imgupload`/`photo`/`image`（勿 `file-upload`；`qqy_ops fields` 可能漏图）
- 已有盘 y=底部，勿 `y:0`；默认半行 `w=12 h=25`

```python
config = {
  'dataType': 1,
  'worksheet': {'label': '产品表', 'value': FORM_CODE, 'key': FORM_CODE},
  'field': 'imgupload_…', 'view': '', 'showMode': 'all', 'maxCount': 3,
  'appInfo': {'label': '应用1', 'value': APP_ID},
  'dataMapping': [{'filed': '路径', 'mapping': ''}],
  'option': {'autoplay': True, 'dots': True, 'dotPosition': 'bottom', 'easing': 'linear'},
  'chartData': [{'src': 'https://jeecgos.oss-cn-beijing.aliyuncs.com/files/site/drag/0.png'}],
  'size': {'width': w * 75, 'height': h * 11},
}
```

## JIframe 嵌入 URL

- 展示地址只写 **`option.body.url`**（禁止 `option.url`）
- 默认 `w:24 h:35`；「中间」→ `insert_y=max_bottom//2`，`y>=insert_y` 的组件下移 `h`

```python
config = {
  'dataType': 1, 'url': '', 'timeOut': 0,
  'chartData': 'https://www.jeecg.com',  # 占位，非展示地址
  'background': '#FFFFFF', 'borderColor': '#E8E8E8',
  'size': {'width': 24 * 75, 'height': 35 * 11},
  'option': {
    'card': {'title': '', 'extra': '', 'rightHref': '', 'size': 'default'},
    'body': {'url': 'https://www.jeecg.com'},  # 用户网址
  },
}
```

站点若设 `X-Frame-Options`/CSP 可能拒嵌——交付一句说明即可。

## JCurrentTime 实时时钟

- `showWeek` 必须字符串 `'show'`/`'hide'`（禁止布尔）
- 右上角默认 `x:16 y:0 w:8 h:10`（角标允许 y:0）；未点名位置 → 底部
- 秒级走时组件内置，勿另加定时器

```python
w, h, x, y = 8, 10, 16, 0
config = {
  'dataType': 1, 'url': '', 'timeOut': 0,
  'turnConfig': {'url': ''}, 'chartData': '',
  'background': '#3F7DD4', 'borderColor': '#E8E8E8',
  'size': {'width': w * 75, 'height': h * 11},
  'option': {
    'showWeek': 'show', 'hourlySystem': '24',
    'format': 'YYYY-MM-DD hh:mm:ss',
    'card': {'title': '', 'extra': '', 'rightHref': '', 'size': 'default'},
    'body': {
      'text': '', 'color': '#FFFFFF', 'fontWeight': 'normal',
      'marginLeft': 0, 'marginTop': 13, 'letterSpacing': 0,
    },
  },
}
```

## 图 / 按钮 / 过滤 / 复合盘（非本组件域的编排）

编排与骨架 → **`create.md`「复合盘」（一条 `--layout-file`，禁拆四轮）**；按钮/过滤 specs → `create.md`「按钮 / 查询面板」；可复制 JSON → `gold-specs.md`。本节只服务本文件三组件（轮播/iframe/时钟）；UI 组件全清单 → `component-words.md`。
