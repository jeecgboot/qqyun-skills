# 真实表单设计案例参考

> 从 JeecgBoot 演示系统 `design_form` 表中提取的真实表单配置，涵盖 OA、HR、行政等常见业务场景。

---

## 1. 字典翻译示例 (demo_test_dict_transl)

**场景：** 展示 radio/checkbox/select 的三种数据源（静态、字典、远程）

**控件清单（18个）：**
- 单行文本 (input)
- 单选框组_远程数据 (radio) — `remote: true, remoteFunc: "http://..."`
- 单选框组_静态数据 (radio) — `showLabel: true, options: [{value:"1",label:"数学"}, ...]`
- 单选框组 (radio) — **`remote: "dict", dictCode: "sex"`**
- 多选框组 (checkbox) — **`remote: "dict", dictCode: "sex"`**
- 多选框组_静态数据 (checkbox) — 静态选项
- 下拉选择框 (select) — `showLabel: true, options: [{value:"1",label:"选项1"}, ...]`
- 下拉选择框_多选 (select) — `multiple: true`
- 下拉选择框_字典 (select) — **`remote: "dict", dictCode: "urgent_level"`**
- 开关 (switch)
- 省市级联动 (area-linkage)
- 用户组件 (select-user) — `multiple: true`
- 部门组件 (select-depart) — `multiple: true`
- 下拉树_分类字典 (select-tree) — `multiple: true`
- 下拉树_表 (select-tree) — `multiple: true`
- 表字典_popup (table-dict) — `multiple: true`
- 表字典_模糊online (table-dict) — `multiple: true`
- 表字典_模糊表 (table-dict) — `multiple: true`

**关键配置模式 — 字典 radio：**
```json
{
  "type": "radio",
  "name": "单选框组",
  "options": {
    "inline": true,
    "showLabel": true,
    "remote": "dict",
    "dictCode": "sex",
    "options": [
      {"value": "选项1", "itemColor": "#e9e9e9"},
      {"value": "选项2", "itemColor": "#e9e9e9"}
    ],
    "remoteOptions": [],
    "props": {"value": "value", "label": "label"},
    "remoteFunc": "",
    "useColor": false,
    "showType": "default",
    "colorIteratorIndex": 0,
    "matrixWidth": 120
  },
  "advancedSetting": {
    "defaultValue": {
      "type": "compose", "value": "", "format": "string",
      "allowFunc": true, "valueSplit": "", "customConfig": true
    }
  }
}
```

**关键配置模式 — 静态 radio (showLabel+value/label)：**
```json
{
  "type": "radio",
  "options": {
    "showLabel": true,
    "remote": false,
    "options": [
      {"value": "1", "label": "数学", "itemColor": "#e9e9e9"},
      {"value": "2", "label": "语文", "itemColor": "#e9e9e9"},
      {"value": "3", "label": "自然", "itemColor": "#e9e9e9"}
    ]
  }
}
```

> **注意：** 当 `showLabel: true` 时，选项需要同时有 `value`（存储值）和 `label`（显示文本）。
> 当 `showLabel: false` 时，`value` 既是存储值也是显示文本。

---

## 2. 请假申请 (qing_jia_shen_qing_5qfk)

**场景：** 典型 OA 审批表单

**控件清单（12个）：**
- 姓名 (select-user) — 必填，`defaultLogin: true`
- 所在部门 (select-depart)
- 申请日期 (date)
- 请假类型 (select) — 选项：事假/病假/年假/调休
- 开始日期 (date)
- 结束日期 (date)
- 天数 (number)
- 请假说明 (textarea)
- 审批意见 (radio) — 选项：同意/不同意
- 直属领导 (select-user)
- 审批时间 (date)
- 附件 (file-upload)

**config：**
```json
{
  "titleField": "select_user_1692952011928_137220",
  "hasWidgets": ["select-user", "select-depart", "date", "card", "select", "number", "textarea", "radio", "file-upload"]
}
```

> **要点：** `titleField` 指向 select-user 控件（而非 input），说明 titleField 可以指向任何控件类型。

---

## 3. 员工基本信息 (yuan_gong_ji_ben_xin_xi_dnjq)

**场景：** HR 员工档案，展示半行布局

**控件清单（8个，全部半行两两配对）：**
- [半行] 姓名 (select-user) | 所在部门 (select-depart)
- [半行] 岗位 (input) | 性别 (select) — 选项：男/女
- [半行] 入职时间 (date) | 参加工作时间 (date)
- [半行] 直属上级 (select-user) | 负责 HR (select-user)

**config：**
```json
{
  "titleField": "select_user_1692874017319_686764",
  "hasWidgets": ["select-user", "select-depart", "card", "input", "select", "date"]
}
```

> **要点：** 整个表单全部使用半行布局（每个 card 内 2 个控件，autoWidth: 50）。

---

## 4. 用车申请 (yong_che_shen_qing_gh3j)

**场景：** 行政用车，展示 area-linkage + formula + link-record + divider

**控件清单（21个）：**
- 申请日期 (date) — 必填
- 申请人 (select-user) — 必填
- 申请部门 (select-depart)
- 用车人数 (integer) — 必填
- 要求用车时间 (date)
- 出发地 (area-linkage)
- 出发地详细地址 (input)
- 目的地 (area-linkage)
- 目的地详细地址 (input)
- 随行司机 (select-user)
- 用车理由 (textarea)
- **分隔符 (divider)**
- 出发时间 (date)
- 返程时间 (date)
- 车牌号码 (link-record) — 关联记录
- 起始公里数 (number)
- 到达公里数 (number)
- **行驶公里数 (formula)** — 公式计算
- 停车费 (money)
- 备注 (textarea)
- 附件 (file-upload)

**config：**
```json
{
  "hasWidgets": ["date", "select-user", "select-depart", "integer", "card", "area-linkage", "input", "textarea", "divider", "link-record", "number", "formula", "money", "file-upload"]
}
```

> **要点：**
> - 使用 `divider` 分隔"申请信息"和"用车记录"两个区域
> - `formula` 控件自动计算行驶公里数
> - `link-record` 关联车辆信息表

---

## 5. 工资表 (gong_zi_biao_zitx)

**场景：** HR 薪资管理，展示 divider 分区 + formula 计算 + money 字段

**控件清单（17个）：**
- 工资发放时间 (date)
- **分隔符 (divider)** — 基本信息区
- 姓名 (select-user) — 必填
- 部门 (select-depart)
- 手机号码 (phone)
- **分隔符 (divider)** — 收入区
- 基本工资 (money)
- 加班工资 (money)
- 奖金 (money)
- 补贴 (money)
- **分隔符 (divider)** — 扣款区
- 本期扣款 (money)
- 五险一金扣款 (money)
- 个税扣除 (money)
- **实发金额 (formula)** — 公式自动计算
- 备注 (textarea)
- 附件 (file-upload)

**config：**
```json
{
  "hasWidgets": ["date", "card", "divider", "select-user", "select-depart", "phone", "money", "formula", "textarea", "file-upload"]
}
```

> **要点：**
> - 用多个 `divider` 将表单分为"基本信息"、"收入"、"扣款"三个区域
> - `formula` 控件计算实发金额 = 基本工资+加班+奖金+补贴-扣款-五险一金-个税
> - 大量使用 `money` 控件（带"元"后缀）

---

## 6. 会议预约 (hui_yi_yu_yue_0s2h)

**场景：** 行政会议管理，展示 link-record + link-field 关联

**控件清单（14个）：**
- 预约人 (select-user) — 必填
- 所属部门 (select-depart) — 必填
- 当前时间 (date) — 必填
- 会议名称 (input) — 必填
- 会议室基础表 (link-record) — 关联记录
- 会议室名称 (link-field) — 他表字段（自动填充）
- 会议室编号 (link-field)
- 会议室容纳人数 (link-field)
- 参会人员 (select-user) — `multiple: true`（多选）
- 会议开始时间 (date)
- 会议结束时间 (date)
- 预约时间 (input)
- 备注 (textarea)
- 附件 (file-upload)

**config：**
```json
{
  "hasWidgets": ["select-user", "select-depart", "date", "card", "input", "link-record", "link-field", "textarea", "file-upload"]
}
```

> **要点：**
> - `link-record` 选择会议室后，`link-field` 自动填充关联数据（名称、编号、容纳人数）
> - `select-user` 支持 `multiple: true` 多选参会人员

---

## 7. 地图/定位/省市联动综合 (ceshi_ditu)

**场景：** 展示地图、表字典、下拉树、多选用户/部门

**控件清单（9个）：**
- 用户组件 (select-user) — `multiple: true`
- 部门组件 (select-depart) — `multiple: true`
- 表字典_popupOL报表 (table-dict)
- 表字典_模糊OL报表 (table-dict)
- 表字典_模糊表 (table-dict)
- 下拉树_分类字典 (select-tree)
- 下拉树_表 (select-tree)
- 性别 (radio) — `remote: "dict", dictCode: "sex"`
- **地图 (map)** — 不需要 card 容器

> **要点：** `map` 控件直接放在顶层 list，不需要 card 容器。

---

## 常用字典编码速查

从真实表单中收集到的字典编码：

| dictCode | 说明 | 使用场景 |
|----------|------|---------|
| `sex` | 性别 | radio/checkbox/select |
| `position_rank` | 职级 | select 多选 |
| `urgent_level` | 紧急程度 | select 多选 |

---

## 设计模式总结

| 模式 | 说明 | 示例表单 |
|------|------|---------|
| **字典数据源** | `remote:"dict"` + `dictCode` | 字典翻译示例 |
| **半行布局** | card 内两控件 `autoWidth:50` | 员工基本信息 |
| **分区分隔** | divider 控件分割表单区域 | 工资表、用车申请 |
| **公式计算** | formula 控件自动计算 | 工资表、用车申请 |
| **关联填充** | link-record + link-field | 会议预约 |
| **默认当前用户** | select-user `defaultLogin:true` | 请假申请 |
| **多选人员** | select-user `multiple:true` | 会议预约、字典示例 |
| **titleField 灵活** | 可指向 select-user 等非 input 控件 | 请假申请、员工信息 |
