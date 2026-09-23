# -*- coding: utf-8 -*-
"""字段名 → 控件类型推断 + 名字对不上时的近似候选。

**为什么要有它**：一份 50+ 表应用的规格约 1000+ 个字段。若每个字段都要写类型，
规格 ≈32k token，**超过单次输出上限**，只能拆成多次 Write —— 这正是「耗时长」的主因。
把叶子类型交给命名推断后，规格只需写名字，≈19k token，一次写完。

**边界（别越界）**：只推断**叶子类型**（input/money/number/date/...）。
下面这些是**语义**、名字里看不出来，必须由 spec 显式声明，本模块一律不猜：
  · 关联记录 / 他表字段 / 汇总  → spec 的 `links` / `summaries`
  · 字典控件                    → spec 的 `字典`（字段名 → 字典名）
  · 自动编号                    → spec 的 `编号`
  · 公式                        → spec 的 `公式`
实测依据：把全部字段都交给命名推断只有四成多命中——因为其中三四成是
link-field/link-record，纯语义。剥掉语义类只推断叶子后，准确率约 93%，
剩余差异是 money↔number、input↔textarea 这类**外观差异，不影响应用可用性**。

用途：
    from spec_infer import infer, near_names
    infer("订单金额")            -> 'money'
    infer("负责人手机")          -> 'phone'
    near_names(["设备名称","设备编码"], "巡检设备名称")  -> ['设备名称']
"""

__all__ = ["infer", "near_names", "resolve", "hint", "normalize_containers", "LEAF_TYPES"]

# infer() 可能返回的全部叶子类型（都与 desform_creator._TYPE_MAP 对齐）
LEAF_TYPES = (
    "input", "textarea", "number", "integer", "money", "date", "time",
    "phone", "email", "select-user", "select-depart", "area-linkage",
    "imgupload", "file-upload", "capital-money", "rate",
)

#: 规格里 `类型` 映射可用的**中文类型名** → 叶子类型。
#  只覆盖叶子类型：需要选项/关联/汇总的（下拉、关联记录、汇总、公式…）请用
#  `静态下拉` / `静态单选` / `links` / `summaries` 那些既有声明，它们带得出额外配置。
TYPE_CN = {
    "单行文本": "input", "多行文本": "textarea", "金额": "money",
    "大写金额": "capital-money", "数字": "number", "整数": "integer",
    "日期": "date", "时间": "time", "手机号": "phone", "邮箱": "email",
    "选择用户": "select-user", "选择部门": "select-depart",
    "地区": "area-linkage", "附件上传": "file-upload", "图片上传": "imgupload",
    # 评分（星级）。需求里「客户重要程度（评分，默认 0）」这类字段名推不出来，
    # 而 `desform_creator._TYPE_MAP` 早就有 'rate': RATE —— 只是规格无处声明，
    # 于是落成单行文本、只能建后就地改类型（2026-09-21 销售管理实测 2 个字段）。
    "评分": "rate",
    # 开关（布尔）。`desform_creator._TYPE_MAP` 早就有 'switch': SWITCH，只是规格无处声明，
    # 名字推不出来，需求点名了就得能写死。
    "开关": "switch",
}


def explicit(type_name):
    """把规格 `类型` 里的中文类型名翻成叶子类型。**认不出就报错**，不静默兜底。

    存在的意义：`infer()` 是**猜**名字，业务上完全可能出现它猜不对的名字
    （2026-09-20 实测：`技术协议` 推成单行文本 —— 它其实是附件上传）。
    在此之前规格**没有任何显式指定类型的口子**，猜错了只能建完表再单独改控件，
    属于「只能事后补丁」的一类坑。现在在规格里写一行 `类型` 即可。
    """
    t = TYPE_CN.get((type_name or "").strip())
    if not t:
        raise ValueError(
            "规格「类型」里的 %r 不是可用的类型名；可用：%s"
            % (type_name, "、".join(TYPE_CN)))
    return t

# 顺序即优先级：越具体越靠前，命中即返回。
# 每条 = (关键词元组, 类型)。命中规则：
#   · 普通关键词 = 「是 name 的**子串**」就命中
#   · `*X` = 「name **以 X 结尾**」才命中（后缀锚定，见下方「合同」）
_RULES = (
    # —— 大写金额 —— 必须排在「金额」之前：`合同金额大写` 同时含「金额」与「大写」，
    # 排后面会被 money 抢先命中（回归里就是这么错的）。
    (("大写",), "capital-money"),
    # —— 文件类 ——
    (("图片", "拍照", "照片"), "imgupload"),
    # ⚠️ 「合同」必须是**后缀**匹配，不能是子串 —— 2026-09-20 实测事故：
    # 子串匹配把「合同金额」「合同税率」「销售合同名称」「销售合同号」「合同相对方」
    # 全推成了附件上传（本规则优先级高于下面的 金额/税率/文本），于是
    # `机会目录.销售合同额(元)` 这个**求和汇总实际在对一个附件字段求和**，
    # 而接口、建表、契约检查全部正常。业务表单里「XX合同」才是附件，
    # 「合同…」开头的都是合同的属性字段。
    (("附件", "回执", "回单", "证书", "*合同"), "file-upload"),
    # —— 联系方式 ——
    (("手机", "电话"), "phone"),
    (("邮箱",), "email"),
    (("地址",), "area-linkage"),
    # —— 人员 / 组织 ——
    (("部门",), "select-depart"),
    (("负责人", "主管", "申请人", "经办人", "出库员", "入库员", "盘点员",
      "质检员", "采购员", "跟进人", "审批人", "成员", "人员", "操作人"), "select-user"),
    # —— 长文本 ——（放在「内容」类词，注意「内容记录」也是长文本）
    (("备注", "原因", "说明", "内容", "简介", "描述"), "textarea"),
    # —— 金额 —— 注意「价」要单独处理：中文里「XX价(含税)」「XX价(元)」
    # 这类括号后缀写法不带「金额/单价」字样，得靠下面的 _PRICE_CHARS 兜住
    (("金额", "单价", "售价", "成本", "税额", "合计", "总额", "总价", "毛利",
      "额度", "价格", "原价"), "money"),
    # —— 数值 ——
    (("数量", "税率", "折扣率", "比例", "序号", "百分比", "库存", "总数",
      "位数", "次数", "天数"), "number"),
    # —— 日期 ——
    (("日期", "时间"), "date"),
)

# 「价」在中文里既可做「价格」也可做「评价」，但业务表单里绝大多数是金额。
# 单独处理是为了让它只在**明确的金额搭配**下生效，不误伤「评价」。
_PRICE_CHARS = ("采购价", "售价", "单价", "原价", "价(", "价)")


def infer(name, first=False):
    """按字段名推断**叶子**控件类型。

    Args:
        name:  字段中文名
        first: 是否为表单第一个字段（目前不参与判定，保留给「自动编号」的启发式；
               自动编号现在一律由 spec 的 `编号` 显式声明，避免误判——
               「XX编码」「XX编号」这类名字同样是 input，光看名字分不出是否自动编号）

    Returns:
        LEAF_TYPES 中的一个；判不出时返回 'input'（最安全的兜底）。
    """
    n = (name or "").strip()
    if not n:
        return "input"
    for keys, typ in _RULES:
        if any((n.endswith(k[1:]) if k.startswith("*") else k in n) for k in keys):
            return typ
    if any(k in n for k in _PRICE_CHARS):
        return "money"
    return "input"


# ---------------- 名字对不上时的近似候选 ----------------

_PREFIXES = ("调出", "调入", "供应商", "客户", "采购", "销售", "退货", "换货", "其他", "本次")
_PAIRS = (
    ("应收", "应付"), ("应付", "应收"),
    ("已入库", "已出库"), ("已出库", "已入库"),
    ("入库", "出库"), ("出库", "入库"),
    ("调入", "调出"), ("调出", "调入"),
    ("采购", "销售"), ("销售", "采购"),
    # 同义不同名：写规格时最常撞的几种
    ("不含税", "含税"), ("含税", "不含税"),
    ("编码", "编号"), ("编号", "编码"),
    # 「姓名」vs「名称」：同一实体在不同表里两种叫法都常见
    ("姓名", "名称"), ("名称", "姓名"),
    # 日期/时间混用：同类字段在不同表里可能一种叫「时间」、一种叫「日期」
    ("时间", "日期"), ("日期", "时间"),
)


def _variants(name):
    """对 name 施加**一轮**变换，返回所有变体（不含原名的去重由调用方做）。"""
    out = []
    for a, b in sorted(_PAIRS, key=lambda p: -len(p[0])):
        if a in name:
            out.append(name.replace(a, b))
    for pre in _PREFIXES:
        if name.startswith(pre) and len(name) > len(pre):
            out.append(name[len(pre):])
    return out


def near_names(cands, name, rounds=3):
    """在已有名字列表里找 `name` 的近似候选，按「成对替换 → 去前缀 → 子串包含」逐级放宽。

    **为什么要有它**：写规格时最高频的失败不是接口错，是**把「显示名」当成了
    「字段名」**——两者在平台上可以不同，且不报错。典型三类：
      ① 带限定前缀  规格要 `设备档案.巡检设备名称`，该表只有 `设备名称`
      ② 成对互串    规格要 `巡检计划编码`，实际是 `巡检计划编号`
      ③ 子串包含    `检测报告附件` ↔ `检测报告附件上传`
    以前只报「没有字段 X」，作者拿到一句否定却不知道该改成什么；这里直接把候选算出来。

    Returns:
        最多 3 个候选（都在 cands 里真实存在）；无候选返回 []。
    """
    cands = list(cands or [])
    if not cands or not name:
        return []
    # 变换必须**迭代到不动点**：真实用例经常要复合两步才算得出来——
    # `责任部门名称` →(去前缀)→ `部门名称` →(名称↔姓名 类的成对替换)→ `部门姓名`。
    # 只做一轮会漏掉第二步，实测因此有几十处落不下来。
    seen, frontier = {name}, [name]
    for _ in range(rounds):
        nxt = []
        for v in frontier:
            for w in _variants(v):
                if w not in seen:
                    seen.add(w)
                    nxt.append(w)
        frontier = nxt
        if not frontier:
            break
    for c in cands:                      # 子串双向包含：只算一轮，不参与迭代
        if c != name and (c in name or name in c):
            seen.add(c)
    return [c for c in cands if c in seen][:3]


def resolve(cands, name):
    """在 cands 里定位 name，逐级放宽：① 精确 → ② 去空白后精确 → ③ 唯一近似候选。

    「去空白」不是洁癖：录入/导入来的字段名可能带前导空格或尾部 TAB，
    精确匹配会全部落空——实测几十处缺口里有一批就是这么来的。
    """
    cands = list(cands or [])
    if name in cands:
        return name
    stripped = (name or '').strip()
    for c in cands:
        if c.strip() == stripped:
            return c
    hits = near_names(cands, stripped)
    return hits[0] if len(hits) == 1 else None


def hint(cands, name):
    """把 near_names 的结果拼成一句可直接读的提示；无候选返回空串。"""
    hits = near_names(cands, name)
    return ("（是否想写：%s）" % "、".join(hits)) if hits else ""


# ---------------- 容器（Tabs） ----------------

def normalize_containers(form):
    """规格表单的 `容器` → 规范形态 + 错误清单。**纯解析，不联网。**

    为什么要有它：规格语言以前**根本没有「容器」这个概念**——每个字段只有
    「一个名字 → 一个平铺控件」这一条出路。需求写「跟进记录、拜访记录、机会目录
    用多 tab」时，作者只能把三个控件平铺建出来、事后再手工搬，而且**没有任何东西
    会告诉你 tab 没建**（2026-09-18 实测：应用建完是三个平铺的关联记录，接口全绿、
    预检通过，直到用户回头问「Tabs 布局空间可以加吗」）。

    规格写法::

        "容器": [
          {"名称": "关联明细",
           "页签": ["跟进", "拜访/出差", "机会"],   // 字符串 = 页签名就是字段名
           "新增时隐藏": true}
        ]

    `页签` 的元素两种写法：
      · `"跟进"`                      → 页签名 = 字段名，该页签装这一个控件
      · `{"相关记录": ["跟进", "机会"]}` → 一个页签装多个控件

    Returns:
        `(containers, errors)`；errors 非空时 containers 里**只保留解析成功的部分**
        （调用方应把 errors 当致命错误处理）。
    """
    name = (form or {}).get('名称') or '?'
    raw = (form or {}).get('容器')
    out, errs = [], []
    if raw is None:
        return out, errs
    if not isinstance(raw, list):
        errs.append('表「%s」的 `容器` 要写成数组 [{名称, 页签, ...}]，现在是 %s'
                    % (name, type(raw).__name__))
        return out, errs
    owner = {}                      # 字段名 → 已经认领它的容器（查重复点名）
    seen_c = set()
    for i, c in enumerate(raw):
        if not isinstance(c, dict):
            errs.append('表「%s」容器[%d] 不是对象' % (name, i))
            continue
        cname = (c.get('名称') or '').strip()
        if not cname:
            errs.append('表「%s」容器[%d] 没写「名称」' % (name, i))
            continue
        if cname in seen_c:
            # 重名容器在真机上表现为**第二个被静默跳过**（幂等判定按名字匹配）
            errs.append('表「%s」有两个同名容器「%s」——同名的只会建出第一个'
                        % (name, cname))
            continue
        seen_c.add(cname)
        panes, labels = [], set()
        for j, p in enumerate(c.get('页签') or []):
            if isinstance(p, str):
                label, flds = p, [p]
            elif isinstance(p, dict) and len(p) == 1:
                label, flds = list(p.items())[0]
                flds = [flds] if isinstance(flds, str) else list(flds or [])
            else:
                errs.append('表「%s」容器「%s」的页签[%d] 形态无法识别：%r'
                            '（要么写字段名，要么写 {"页签名": ["字段", ...]}）'
                            % (name, cname, j, p))
                continue
            label = (label or '').strip()
            if not label:
                errs.append('表「%s」容器「%s」的页签[%d] 没有名字' % (name, cname, j))
                continue
            if label in labels:
                # 页签的 name 就是 label，重名 → Tabs 里两个页签同名
                errs.append('表「%s」容器「%s」有两个同名页签「%s」' % (name, cname, label))
                continue
            labels.add(label)
            flds = [f for f in flds if f]
            if not flds:
                errs.append('表「%s」容器「%s」的页签「%s」没点名任何字段'
                            % (name, cname, label))
                continue
            for f in flds:
                if f in owner:
                    errs.append('表「%s」的「%s」同时被容器「%s」和「%s」点名'
                                % (name, f, owner[f], cname))
                else:
                    owner[f] = cname
            panes.append((label, flds))
        if not panes:
            errs.append('表「%s」容器「%s」没有任何可用的页签' % (name, cname))
            continue
        out.append({'name': cname, 'panes': panes,
                    'hiddenOnAdd': bool(c.get('新增时隐藏'))})
    return out, errs
