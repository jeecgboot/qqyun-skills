# -*- coding: utf-8 -*-
"""零真机预检 —— 动真机之前，把能静态查出来的错全查掉。

    python precheck.py --spec app_spec.json [--flows flows.py]

**为什么要它**：2026-09-16 建 52 表应用实测 42 分钟，其中约 15 分钟是**真机才暴露的错**
触发的重跑——公式占位符引用了本表没有的字段、看板透视 `val` 传了空数组、
查询面板的 charts 跨了两张表。这些都是**纯静态信息**，本可以在这里挡下来。

预检通过 ≠ 一定对（真机还有接口与权限问题），但**预检不过 = 一定错**，
且不用付一次几分钟的建表/建盘/建流程。

## 2026-09-17 补的四类（各对应一次真机返工，都是纯静态信息）

1. **元组 cond 不再崩**：`flow_dsl` 的 `(字段, 规则, 值)` 里值可能是 `ref()/var()` 的
   dict，老代码 `if c not in ctxf` 直接 `TypeError: unhashable type: 'dict'`
   —— **整段流程校验跑不完**（不是报错几条，是根本没输出）。
2. **`ref(node=...)` 按那个节点的表校验**：老代码一律按上下文表查，
   跨表 `ref("采购入库单编号", node="获取采购入库")` 全被误报（52 表应用刷 30+ 条假错）。
3. **`get_more(..., from_="start")` 必须有同名关联控件**：引擎靠「本表 → 目标表」的
   关联控件建数据对象，缺了它紧跟的 `call_sub` 会报「请先 get_more」级联失败。
   注意 `from_` 要写 **目标表名**，不是关联控件的显示名。
4. **看板的图名不能互为子串**：`add-filter` 的匹配是双向子串，
   一个查询面板的图名命中多张图 → 整盘 FAIL（图已建好、只差筛选栏）。

## 2026-09-17 再补一类：`多选` 写在没绑字典的字段上

5. **`多选` 是开关不是声明**。它只在「字段绑了 `字典`」的分支里生效（决定那个字典字段
   走 checkbox 还是 select）；字段**不在 `字典` 里**时它一个字都不起作用，直接落到
   `infer()` → `input`。表现是**静默**的：不报错、不警告、应用照建，前端多一个空文本框。
   要「不绑字典的静态选项」只能写 `静态多选` / `静态单选`。
   52 表应用实测踩到（`产品权限`：销售/采购/赠送），只能建完再打补丁改控件类型。

设计原则：**读文件，不联网**。所以它能在动真机之前跑，也就能跑很多次。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from spec_infer import normalize_containers                     # noqa: E402

#: patch_fields 的重入轮数（带出字段可能由另一条关联建出来）
ROUNDS = 3
#: DATE 工厂的 date_type 合法集（工厂自述；`dateType` 经创建器映射成工厂的 `date_type`）
DATE_TYPES = {'year', 'month', 'quarter', 'week', 'date',
              'datetime_s', 'datetime_sf', 'datetime'}
#: 字段名 → 档位线索，**按长的先匹配**。只收歧义极小的复合词：
#: 「时间」二字故意不收（外出时间=datetime / 跟进时间=date，名字判不出来）。
DATE_HINTS = (('日期时间', 'datetime'), ('年份', 'year'), ('年月', 'month'),
              ('季度', 'quarter'), ('年周', 'week'))

errs, warns = [], []
BY_NAME = {}          # 表名 → 表单定义
EFF = {}              # 表名 → 自身字段 ∪ 关联带出的字段（收敛后）
RECORD_COUNT_WAYS = {'计数', '记录数', '记录数量', '条数', '总数', '数量'}   # 记录数量不引用列，「汇总列」可省
SUMMARY_WAYS = {'求和', '合计', '平均', '平均值', '均值', '最大', '最大值', '最小', '最小值',
                '计数', '记录数', '记录数量', '条数', '总数', '数量', '已填计数', '未填计数'}
SUBS = set()          # 已定义的子流程名（call_sub 解析用）
SPEC = {}             # 整份规格（get_more(from_="start") 要查 links）
NODES = {}            # 流程名 → {节点名: 节点该表}（ref(node=...) 解析用）


def err(m):
    errs.append(m)


def warn(m):
    warns.append(m)


# ---------------- 规格 ----------------

def load_spec(path):
    with io.open(path, encoding='utf-8') as fh:
        return json.load(fh)


def build_eff(spec):
    """算出每张表「最终会有哪些字段」——自身字段 + 关联带出的他表字段。

    带出字段可能**本身是另一条关联建出来的**（明细表的标题来自它关联的上游表），
    patch_fields 靠最多 ROUNDS 轮重入收敛。这里照它的语义模拟：
    收敛不了的就是真缺口。
    """
    links = spec.get('links') or []
    eff = {n: set(f.get('字段') or []) for n, f in BY_NAME.items()}
    # 收敛结果要写回全局，后面的看板 / 流程检查都依赖它
    EFF.clear()
    EFF.update(eff)
    link_by = {}
    for lk in links:
        t, fld, tgt = lk.get('表'), lk.get('字段'), lk.get('目标')
        if t not in BY_NAME:
            err('links：表「%s」不存在' % t)
            continue
        if tgt not in BY_NAME:
            err('links：%s.%s 的目标表「%s」不存在' % (t, fld, tgt))
            continue
        if fld not in (BY_NAME[t].get('字段') or []):
            err('links：%s 的字段「%s」不在该表自己的字段列表里' % (t, fld))
        if (t, fld) in link_by:
            err('links：%s.%s 重复声明' % (t, fld))
        link_by[(t, fld)] = tgt

    pending = [lk for lk in links
               if lk.get('表') in BY_NAME and lk.get('目标') in BY_NAME]
    for _ in range(ROUNDS):
        still = []
        for lk in pending:
            t, tgt = lk['表'], lk['目标']
            if all(c in eff[tgt] for c in (lk.get('带出') or [])):
                eff[t].update(lk.get('带出') or [])
            else:
                still.append(lk)
        if len(still) == len(pending):
            break
        pending = still
    for lk in pending:
        bad = [c for c in (lk.get('带出') or []) if c not in eff[lk['目标']]]
        err('links：%s.%s → %s 带出 %s，%d 轮内落不下（目标表没有）'
            % (lk['表'], lk['字段'], lk['目标'], '、'.join(bad), ROUNDS))

    # 「显示字段」是**只展示、不建控件**的列：名字必须本来就在目标表上。
    # 不需要参与上面的收敛（它不产出字段），所以直接查最终态 eff 即可。
    # 2026-09-20 加：此前规格表达不了「只展示不带出」，只能手写补丁，而补丁形状
    # 写错是静默的（落 [{"field":…,"show":true}] 会被引擎忽略 → 只显示标题一列）。
    for lk in links:
        if lk.get('表') not in BY_NAME or lk.get('目标') not in BY_NAME:
            continue
        bad = [c for c in (lk.get('显示字段') or []) if c not in eff[lk['目标']]]
        if bad:
            err('links：%s.%s → %s 的显示字段 %s 在目标表里没有'
                % (lk['表'], lk['字段'], lk['目标'], '、'.join(bad)))

    # 单条关联只有「卡片 / 下拉」两档，**没有「表格」**。
    # 2026-09-20 加：写 `显示:"表格"` 会落 `showType:'table'`，前端把单条渲染成一张表
    # （用户实测 8 个）。patch_fields 现在会夹成卡片并打 WARN，但那是**建完才说**；
    # 这里提前拦，省一轮真机。
    for lk in links:
        if lk.get('条数') == '单条' and lk.get('显示') not in (None, '', '卡片', '下拉'):
            err('links：%s.%s 的「条数=单条」配「显示=%s」是非法组合'
                '（单条只有卡片/下拉；设计器里没有「表格」这一项）'
                '→ 改成「显示=卡片」或「显示=下拉」'
                % (lk['表'], lk['字段'], lk.get('显示')))
    # ⚠️ 2026-09-21：这条曾被**撤销过**，理由是「回读线上某进销存模版，里面就是
    # single+table」—— **因果搞反了**：那 8 个正是同类错误污染出来的坏数据。
    # 线上应用**不是标准**，它自己就可能不对；与设计器能力冲突时以**设计器**为准。
    # 规则：需求量写「单条 + 表格」时**拦下来**，不要放宽校验。

    # 「双向」= 两侧互填 twoWayModel（desform-link-record.md §六）。
    # true = 目标表里**恰好一个** link-record 指回本表；写控件名 = 指名那一个。
    # 2026-09-20 加：此前规格表达不了双向、patch_fields 里 twoWayModel 一处都没有，
    # 需求被静默降级——接口全绿，应用里 twoWayModel 全空，只能靠人眼发现。
    for lk in links:
        if not lk.get('双向'):
            continue
        t, fld, tgt = lk.get('表'), lk.get('字段'), lk.get('目标')
        if t not in BY_NAME or tgt not in BY_NAME:
            continue
        want = lk['双向']
        if want is not True and not (isinstance(want, str) and want.strip()):
            err('links：%s.%s 的「双向」只能是 true 或目标表里的回指控件名，收到 %r'
                % (t, fld, want))
            continue
        # 回指控件必须由**另一条 links** 声明建出来：表=目标表、目标=本表
        back = [x for x in links if x.get('表') == tgt and x.get('目标') == t]
        if not back:
            err('links：%s.%s 声明了「双向」，但「%s」没有任何关联记录指回「%s」——'
                '另一侧需要一条 links（表=%s、目标=%s），否则双向无处可指'
                % (t, fld, tgt, t, tgt, t))
            continue
        names = sorted({x.get('字段') or '?' for x in back})
        if isinstance(want, str) and want.strip():
            if want.strip() not in names:
                err('links：%s.%s 的「双向」指名了「%s」，但「%s」指回「%s」的控件是 %s'
                    % (t, fld, want, tgt, t, '、'.join(names)))
        elif len(back) > 1:
            err('links：%s.%s 的「双向」写 true，但「%s」有 %d 个控件指回「%s」（%s）——'
                '歧义，请写成要指定的那个控件名'
                % (t, fld, tgt, len(back), t, '、'.join(names)))

    for lk in links:
        stray = [x for x in (lk.get('仅显示') or [])
                 if x not in (lk.get('带出') or []) and x not in (lk.get('带出映射') or {})]
        if stray:
            err('links：%s.%s 的「仅显示」%s 不在这条关联的 带出/带出映射 里（仅显示只是给带出字段打标记）'
                % (lk.get('表'), lk.get('字段'), stray))

    for sm in (spec.get('summaries') or []):
        t, fld = sm.get('表'), sm.get('字段')
        lkf, col = sm.get('关联字段'), sm.get('汇总列')
        if t not in BY_NAME:
            err('summaries：表「%s」不存在' % t)
            continue
        if fld not in eff[t]:
            err('summaries：%s 的字段「%s」不在其字段列表里' % (t, fld))
        tgt = link_by.get((t, lkf))
        if not tgt:
            err('summaries：%s 没有关联记录「%s」' % (t, lkf))
        elif (sm.get('方式') or '') not in RECORD_COUNT_WAYS and col not in eff[tgt]:
            err('summaries：%s.%s ← %s 没有列「%s」' % (t, fld, tgt, col))
        # 父表汇总要能算，父表那侧的关联控件里得**有**子记录。子表也声明了指回父表的关联、
        # 而这一对没写「双向」时：从子表侧建的行只填了子表那一侧，父表控件恒空 → **汇总恒为空**，
        # 而 precheck/build_app/app_audit/postbuild_verify 四道检查都不报（2026-09-22 项目管理 R3：17 对全中）
        if tgt:
            lk = next((l for l in (spec.get('links') or [])
                       if l.get('表') == t and l.get('字段') == lkf), None)
            back_rows = [l for l in (spec.get('links') or []) if l.get('表') == tgt and l.get('目标') == t]
            back = bool(back_rows)
            # 「双向」标在对面（单条）那一行也是这一对：patch_fields 两侧互填，写哪侧都一样。
            # 以前只看父表这一行，照 requirement-design「标在其中一行」写在子表侧就报 3 条假错（担保-一句话10）
            paired = lk is not None and (lk.get('双向') or any(
                b.get('双向') is True or b.get('双向') == lkf for b in back_rows))
            if lk is not None and back and not paired:
                err('summaries：%s.%s 汇总的是关联「%s」，而「%s」也有指回「%s」的关联 —— '
                    '这一对必须写「双向」: true，否则从子表侧建的行不会进父表控件，汇总恒为空'
                    % (t, fld, lkf, tgt, t))
        if sm.get('方式') and sm['方式'] not in SUMMARY_WAYS:
            err('summaries：%s.%s 的方式「%s」不认识（会被静默当成求和），可用：%s'
                % (t, fld, sm['方式'], '、'.join(sorted(SUMMARY_WAYS))))
    EFF.clear()
    EFF.update(eff)
    return link_by


def check_forms(spec):
    dicts = spec.get('字典') or {}
    for f in (spec.get('forms') or []):
        name = f.get('名称')
        if not name:
            err('有表单没写「名称」')
            continue
        flds = f.get('字段') or []
        if not flds:
            err('表「%s」字段列表为空' % name)
        for k in list((f.get('字典') or {}).values()):
            if k not in dicts:
                err('表「%s」绑了不存在的字典「%s」' % (name, k))
        for fld in (f.get('字典') or {}):
            if fld not in flds:
                err('表「%s」字典字段「%s」不在字段列表里' % (name, fld))
        # 中转字段（2026-09-21 加）：隐藏取值信封，默认值 = 「本表指向某表 X 的关联控件」
        # 上的字段 Y。规格形态 `{"<本表字段名>": ("<X表名>", "<Y字段名>")}`。
        # 四样都得在：本表字段名要声明、被指的 X 表要存在、X 表上要有 Y 字段、
        # 且**本表必须有一条指向 X 的关联记录**（默认值就是顺着它取的，没有就取不到）。
        # 静态查不出的只剩「默认值表达式拼得对不对」——那条交给 app_audit 回读真机。
        for fld, pair in (f.get('中转字段') or {}).items():
            if fld not in flds:
                err('表「%s」中转字段「%s」不在字段列表里' % (name, fld))
            if not (isinstance(pair, (list, tuple)) and len(pair) == 2):
                err('表「%s」中转字段「%s」要写成 ("父表名", "父表字段名")' % (name, fld))
                continue
            parent, pfield = pair
            pf = next((x for x in (spec.get('forms') or [])
                       if x.get('名称') == parent), None)
            if not pf:
                err('表「%s」中转字段「%s」指向的表「%s」不在 spec 里' % (name, fld, parent))
            elif pfield not in (pf.get('字段') or []) \
                    and pfield not in (pf.get('字典') or {}) \
                    and pfield not in (pf.get('编号') or {}):
                err('表「%s」中转字段「%s」取的「%s.%s」不在那张表的字段列表里'
                    % (name, fld, parent, pfield))
            if not any(l.get('表') == name and l.get('目标') == parent
                       for l in (spec.get('links') or [])):
                err('表「%s」中转字段「%s」要顺着一条指向「%s」的关联记录取值，'
                    '但 links 里没有这条关联' % (name, fld, parent))

        for fld in list((f.get('编号') or {})) + list((f.get('公式') or {})):
            if fld not in flds:
                err('表「%s」编号/公式字段「%s」不在字段列表里' % (name, fld))
        # 日期粒度（2026-09-20 加）：需求写「年份 / 日期时间」时靠它声明。
        # 档位取自 DATE 工厂的自述合法集；写错落成默认 date（年月日），接口全绿、
        # 只有人打开新增页才看得出粒度不对。
        for fld, dt in (f.get('日期粒度') or {}).items():
            if fld not in flds:
                err('表「%s」日期粒度 的「%s」不在字段列表里' % (name, fld))
            if dt not in DATE_TYPES:
                err('表「%s」的「%s」日期粒度「%s」不合法，可用：%s'
                    % (name, fld, dt, ' / '.join(sorted(DATE_TYPES))))
        # 字段名自带档位线索、却没声明 `日期粒度` -> **提示**（不是报错：名字只是线索，
        # 需求才是准的；但漏声明的后果是静默落成年月日，只有人在新增页才看得出）。
        # 只在**歧义很小**的复合词上提示（年份/年月/季度/年周/日期时间）；
        # 「时间」单独一个词**不提示** —— 「外出时间」要 datetime、「跟进时间」要 date，
        # 名字判不出来，硬猜反而误导（这正是档位必须显式声明的原因）。
        for fld in flds:
            hit = next(((k, t) for k, t in DATE_HINTS if fld.endswith(k)), None)
            if not hit:
                continue
            kw, want = hit                      # 命中的关键词 / 建议档位
            cur = (f.get('日期粒度') or {}).get(fld)
            if cur is None and (f.get('类型') or {}).get(fld) == '日期':
                continue                        # 类型里已写明「日期」= 就要年月日（人事OA-速测18 3 条误报）
            if cur is None and (f.get('类型') or {}).get(fld) not in (None, '日期'):
                continue                        # 类型里写明了别的（「归属年份」= 单行文本），名字线索作废（考勤-速测19）
            if cur is None:
                warn('表「%s」的「%s」名字像「%s」，但没写 `日期粒度` —— 默认会落成年月日。'
                     '若需求是「%s」请写 {"%s": "%s"}' % (name, fld, kw, kw, fld, want))
            elif cur != want:
                warn('表「%s」的「%s」声明了日期粒度「%s」，但名字像「%s」（%s）—— 确认哪个对'
                     % (name, fld, cur, kw, want))
        # 静态选项（不绑应用字典的多选/单选，如 产品权限：销售/采购/赠送）。
        # 规格里不声明时 `spec_infer.infer` 只会给出 input，前端就是个空文本框。
        for key in ('静态多选', '静态单选', '静态下拉'):
            for fld, opts in (f.get(key) or {}).items():
                if fld not in flds:
                    err('表「%s」%s 的「%s」不在字段列表里' % (name, key, fld))
                if not opts:
                    err('表「%s」%s 的「%s」选项为空' % (name, key, fld))
                if fld in (f.get('字典') or {}):
                    err('表「%s」的「%s」同时出现在 %s 和 字典 里——绑字典的用 `多选`，'
                        '不绑字典的才用 `%s`' % (name, fld, key, key))
        # ⚠️ `多选` 是**开关**不是**声明**：它只在 `elif f in dicts` 那条分支里生效
        # （决定绑字典的字段走 checkbox 还是 select）。字段**不在 `字典` 里**时它一个
        # 字都不起作用，直接落到 `infer()` → `input`——前端是个空文本框，不报错、
        # 不警告、预检也照样通过。2026-09-17 建 52 表应用实测踩到（产品权限静默变文本框）。
        # 想表达「不绑字典的静态选项」只能写 `静态多选` / `静态单选` / `静态下拉`。
        for fld in (f.get('多选') or []):
            if fld not in flds:
                err('表「%s」多选 的「%s」不在字段列表里' % (name, fld))
            if fld not in (f.get('字典') or {}):
                err('表「%s」的「%s」写在 `多选` 里但没绑字典——`多选` 只是「字典字段走 '
                    'checkbox 还是 select」的开关，不绑字典时它完全不生效，会静默落成'
                    '文本框。要静态选项请写成 `静态多选`：{"%s": ["选项1", "选项2"]}'
                    % (name, fld, fld))
        # ⚠️ 需求写「下拉单选」时**别写 `静态单选`** —— 它固定落 radio（横排单选钮），
        # 规格里没有别的档能建出「静态选项 + 下拉」。这一档 2026-09-20 才补上。
        # precheck 只能提示、无法自动纠正（它只认字段名，读不到需求原文），所以这里
        # 只在两者同时出现时拦重复声明。
        for key in ('静态多选', '静态单选', '静态下拉'):
            for fld in (f.get(key) or {}):
                others = [k for k in ('静态多选', '静态单选', '静态下拉') if k != key]
                if any(fld in (f.get(k) or {}) for k in others):
                    err('表「%s」的「%s」被重复声明在多个静态选项键里（%s）——'
                        '一个字段只能占一档，否则建壳取哪一档由分支顺序决定'
                        % (name, fld, '/'.join([key] + others)))


#: `类型` 会被这些**更高优先级**的声明静默盖掉（= build_app.split_fields 的 if/elif 顺序）。
#: 盖住的后果是全链路静默：规格里写了类型、建出来是另一档，接口 / 回读 / 预检都全绿。
TYPE_SHADOW_KEYS = ('字典', '静态多选', '静态单选', '静态下拉', '日期粒度', '编号', '公式')


def check_types(spec):
    """`类型`（显式叶子类型）必须真的落到控件上。

    它是 `infer()` 猜名字猜错时的**唯一补救口子**（2026-09-20 实测：`技术协议`
    推成单行文本，其实是附件上传）。但它在 build_app 的分支里排在 字典 / 静态选项 /
    日期粒度 / 编号 / 公式 **之后**，被任何一个盖住都不报错；字段名写错则整条配置
    永远不会被遍历到。两种情况都只能靠这份预检拦下来。
    """
    from spec_infer import explicit
    for f in (spec.get('forms') or []):
        name = f.get('名称')
        types = f.get('类型') or {}
        if not types or not name:
            continue
        flds = set(f.get('字段') or [])
        # 关联记录 / 带出 / 汇总字段走补丁段，压根不进建壳分支 —— 写 `类型` 是死配置
        patchy = set()
        for lk in (spec.get('links') or []):
            if lk.get('表') == name:
                patchy.add(lk.get('字段'))
                patchy |= set(lk.get('带出') or [])
        patchy |= {s.get('字段') for s in (spec.get('summaries') or [])
                   if s.get('表') == name}
        for fld, tn in types.items():
            if fld not in flds:
                err('表「%s」类型 的「%s」不在字段列表里 —— 建壳按字段列表遍历，'
                    '这个名字永远不会生效' % (name, fld))
                continue
            if fld in patchy:
                # ⚠️ **提示，不是错误**（2026-09-21 校准）：`类型` 对补丁段字段确实是空操作，
                # 但这是「规格里有冗余声明」，**应用照建、行为正确**（补丁段那个分支先命中，
                # 带出的控件类型由**源字段**决定，通常与这里写的正好一致）。
                # 之前判 err 会把「建得完全对的规格」堵在门外 —— 闸门只该拦**会盖错的**，
                # 不拦**写了没用**的。真想据此发 `err`，得先拿到源字段类型（要联网），
                # 静态判不出来。
                warn('表「%s」的「%s」是关联记录/带出/汇总字段（补丁段建），'
                     '`类型` 对它不起作用 —— 冗余声明，删掉更干净' % (name, fld))
                continue
            try:
                explicit(tn)
            except ValueError as e:
                err('表「%s」的「%s」类型不合法：%s' % (name, fld, e))
                continue
            shadow = [k for k in TYPE_SHADOW_KEYS if fld in (f.get(k) or {})]
            if shadow == ['日期粒度'] and tn == '日期':
                continue                        # 同是日期控件，粒度只是细化，不存在「盖错」
            if shadow:
                warn('表「%s」的「%s」同时写了 `类型` 和 %s —— 建壳的 if/elif 里后者优先，'
                     '`类型` 会被盖掉；两个档一致就没事，不一致请二选一'
                     % (name, fld, ' / '.join('`%s`' % k for k in shadow)))


def check_undeclared(spec):
    """**没落进任何类型声明的字段 = 靠 `infer()` 猜名字** —— 猜错是静默的。

    建壳的 if/elif 链（字典 / 静态多选 / 静态单选 / 静态下拉 / 日期粒度 / 编号 / 公式 /
    `类型` / `infer()`）里，前七档都没命中就掉到 `infer()` 按**字段名**猜。
    猜错**不影响 save/deploy/字段权限/引用解析**，七道闸门一条都看不见，
    界面上却是「想选选不了、想填填不进」：

      2026-09-22 三处同源事故（都是这条）——
        · `人员成本.职级`：需求写「关联记录 →职级 单条·下拉」，规格里这条 links **整条漏了**
          → infer 猜成单行文本 → 界面上是只能手填的输入框（用户截图报障，显示裸值 `1`）；
        · `客户.注册电话`：需求「单行文本」，规格写成 `手机号` → 落成 phone 控件，
          带「请输入正确的手机号码」校验，**座机填不进去**；
        · `项目外采预算.小计`：需求「数字，必填，默认值：自动计算」，规格写成 `公式`。

    ⚠️ **只报「兜底」那一批**：`infer()` 先按名字关键词匹配（`日期`→date、`金额`→money…），
    匹配不上才兜底成 input。名字有线索的（`计划开始日期`）闭着眼也是对的，报了纯噪音；
    真正的风险全在兜底那批 —— 名字什么线索引不出，控件种类完全没依据（`职级` 就是）。
    按需求文档逐字比对是 `postbuild_types.py` 的活（那要建完、且要需求原文），
    这里判 warn 不判 err。汇总成**一条**，不逐表刷屏。
    """
    from spec_infer import infer
    loose = []
    for f in (spec.get('forms') or []):
        name = f.get('名称')
        if not name:
            continue
        declared = set((f.get('类型') or {}).keys())
        for k in TYPE_SHADOW_KEYS:
            declared |= set((f.get(k) or {}).keys())
        # 关联记录 / 带出 / 汇总 / 中转字段走补丁段，不进建壳分支 —— 天然不需要「类型」
        patchy = set()
        for lk in (spec.get('links') or []):
            if lk.get('表') == name:
                patchy.add(lk.get('字段'))
                patchy |= set(lk.get('带出') or [])
                patchy |= set((lk.get('带出映射') or {}).keys())
        patchy |= {s.get('字段') for s in (spec.get('summaries') or [])
                   if s.get('表') == name}
        # 建后套件会改类型的（TO_LINKFIELD / LINKDATA，--struct 时读）：不是「兜底成单行文本」（CRM/销售/进销存-速测19）
        patchy |= {fld for (t, fld) in STRUCT_TYPED if t == name}
        patchy |= set((f.get('中转字段') or {}).keys())
        title = f.get('标题')
        # 标题字段本来就该是单行文本：列进「兜底」提示纯属噪音（2026-09-24 三个应用都被它多逼一轮 precheck）。
        # 反过来，标题被名字推成多行文本/附件这类（`检查项内容` → textarea）才是要提示的。
        if title and title not in declared and title not in patchy and infer(title) != 'input':
            warn('表「%s」的标题「%s」会被名字推断成 %s —— 关联下拉/卡片显示的就是它，'
                 '标题应是单行文本：改名（别以 内容/描述/说明 结尾）或在 `类型` 里写「单行文本」'
                 % (name, title, infer(title)))
        for x in (f.get('字段') or []):
            if x in declared or x in patchy or x.startswith('__') or x == title:
                continue
            if infer(x) == 'input':          # 兜底 = 名字没有任何线索引出别的类型
                loose.append('%s.%s' % (name, x))
    if loose:
        warn('有 %d 个字段既没写类型声明、名字也无线索，控件种类**兜底成单行文本**：%s '
             '—— 逐个核对需求：如果需求写的是「关联记录 / 下拉 / 金额 / 附件」这类，'
             '必须显式写进 `类型` 或 `links`（猜错不影响 save/deploy，界面上一眼才看得出）；'
             '建完用 postbuild_types.py --work <postbuild_probe 产物目录> 逐字段对一遍'
             '（它**没有 --prompt 参数**；需求原文要按 `1. 表名 （标题字段：X）` + `   1) 字段 （类型）`'
             '的格式从 **stdin** 管进去）'
             % (len(loose), '、'.join(loose)))


def check_menu_order(spec):
    """`菜单顺序`（可选）里的名字必须是真表/真看板，且分组与该表的 `分组` 一致。

    没写 `菜单顺序` 时菜单按 `forms` 的书写顺序排 —— 打一行提示把结果亮出来，
    因为「按依赖顺序写 forms」是很自然的写法，而那样菜单顺序就不是需求要的顺序
    （2026-09-21 实测：24 表应用分组与组内顺序全乱，当时没有任何一环核对顺序）。
    """
    mo = spec.get('菜单顺序')
    if not mo:
        order = {}
        for f in spec.get('forms') or []:
            order.setdefault(f.get('分组') or '（未分组）', []).append(f.get('名称'))
        if len(order) > 1:
            warn('没写 `菜单顺序` → 导航按 forms 书写顺序排：%s。与需求的分组/菜单顺序不一致就补 `菜单顺序`'
                 % ' ｜ '.join('%s[%s]' % (g, '、'.join(map(str, ns))) for g, ns in order.items()))
        return
    pairs = list(mo.items()) if isinstance(mo, dict) else [(x.get('分组'), x.get('工作表') or []) for x in mo]
    pages = {p.get('name') or p.get('名称') for p in (spec.get('pages') or [])}
    seen = set()
    for g, names in pairs:
        for n in names:
            if n in seen:
                err('菜单顺序 里「%s」出现了多次' % n)
            seen.add(n)
            f = BY_NAME.get(n)
            if not f and n not in pages:
                err('菜单顺序 的「%s」不是规格里的工作表或看板' % n)
            elif f and (f.get('分组') or None) != (g or None):
                err('菜单顺序 把「%s」放在分组「%s」，但该表的 `分组` 是「%s」' % (n, g, f.get('分组')))
    lost = [n for n in BY_NAME if n not in seen]
    if lost:
        warn('菜单顺序 没点名 %d 张表（会排在各组点名项之后）：%s' % (len(lost), '、'.join(lost)))


def check_layouts(spec):
    """分节布局里的字段名必须真的在这张表上——名字写错要等第④段才炸，太晚。"""
    layouts = spec.get('layouts') or {}
    for name, secs in layouts.items():
        f = BY_NAME.get(name)
        if not f:
            err('layouts 里的表「%s」不存在' % name)
            continue
        # 表上的控件 = 建壳字段 + 补丁阶段建的（关联记录的「带出」、汇总）
        have = set(f.get('字段') or [])
        for l in (spec.get('links') or []):
            if l.get('表') == name:
                have |= set(l.get('带出') or [])
        have |= {s.get('字段') for s in (spec.get('summaries') or []) if s.get('表') == name}
        # 容器名可以写进分节名单：build_app 装完容器后按名单把选项卡排到这个位置
        have |= {c.get('名称') for c in (f.get('容器') or []) if isinstance(c, dict) and c.get('名称')}
        placed = []
        for s in secs:
            if not (s.get('字段') or s.get('标题')):
                err('layouts「%s」里有一个空分节（既没标题也没字段）' % name)
            for fld in (s.get('字段') or []):
                if fld not in have:
                    err('layouts「%s」的字段「%s」不在该表字段里' % (name, fld))
                placed.append(fld)
        dup = sorted({x for x in placed if placed.count(x) > 1})
        if dup:
            err('layouts「%s」里这些字段被放了多次：%s' % (name, '、'.join(dup)))
        # 段标题（落成 divider）与本表字段/关联字段同名：按名字解析控件的脚本可能取到 divider
        # （2026-09-24 任务-一句话5「工时记录」、担保-一句话5「调查结论/评审结论」各返工一次）
        ctl = have | {l.get('字段') for l in (spec.get('links') or []) if l.get('表') == name}
        same = [s.get('标题') for s in secs if s.get('标题') and s.get('标题') in ctl]
        if same:
            warn('layouts「%s」的段标题与本表字段同名：%s —— 按名字引用字段（按钮新建关联、流程取值）'
                 '可能取到段标题，建议段标题换个说法（如「工时记录」→「工时登记」）' % (name, '、'.join(same)))
        # 容器字段**故意不写进分节**（写了会被容器段摘走、只剩一条孤儿分隔线，
        # check_containers 会报错）。它们不归分节管，所以不该算「没点名」。
        in_cons = {x for c in normalize_containers(f)[0]
                   for _, pf in c['panes'] for x in pf}
        miss = [x for x in (f.get('字段') or []) if x not in placed and x not in in_cons]
        if miss:
            warn('layouts「%s」没点名 %d 个字段（会按原顺序排在最后）：%s'
                 % (name, len(miss), '、'.join(miss[:8])))


def check_field_opts(spec):
    """`必填` / `选项` 的字段名和选项键**必须真的生效**。

    ⚠️ 这两条以前在规格里**根本表达不了**：需求写「XX 必填」「附件最多 10 个」时无处可写，
    `required` 在 spec→建壳 的整条链路上没有任何消费者（`f('客户名称','input',
    required=True)` 是纯装饰），控件级选项连书写位置都没有。表现是**静默**的：
    应用照建、接口全绿，只是字段不是必填、附件没有上限。
    2026-09-18 实测：全应用 10 个 `required=True` 字段全是空操作。

    ⚠️ **白名单校验才是这条的主要价值**：`make_widget` 对不在白名单的键是
    「打印一行警告然后丢弃」，写错一个键名就是静默失效 —— 正是要提前拦的那类。
    """
    from desform_utils import _VALID_OPTIONS_KWARGS
    # ⚠️ `选项` **只收真正的 options 级键**（`_VALID_OPTIONS_KWARGS`）——
    # 不能把 `_PARAM_MAP` 也算进来：那里的键是**建壳器级的抽象**，工厂内部会做翻译
    # （`dateType` → `options.type='datetime'`、`dictCode` → `options.dictCode`…）。
    # 当成 options 级直接写进去，只会往控件里塞一个**设计器不认的键**：
    # 2026-09-18 实测，线上日期控件是 `options.type='datetime'`、`dateType` 根本不存在。
    # 收紧之后语义才干净 —— 「`选项` 里的键会被原样写进控件的 options」，
    # 建壳与事后补丁两条路径行为完全一致。
    ok_keys = set(_VALID_OPTIONS_KWARGS)
    # 这些键是建壳器自己拼字段定义用的，覆盖了会把控件拆散
    reserved = {'name', 'type', 'fields', 'columnNumber', 'category'}
    for f in (spec.get('forms') or []):
        name = f.get('名称')
        have = set(f.get('字段') or [])
        # 补丁阶段才建的字段（关联记录本身 / 带出 / 汇总）建壳时还不存在，设不了 required
        late = {l.get('字段') for l in (spec.get('links') or []) if l.get('表') == name}
        late |= {c for l in (spec.get('links') or []) if l.get('表') == name
                 for c in (l.get('带出') or [])}
        late |= {s.get('字段') for s in (spec.get('summaries') or [])
                 if s.get('表') == name}
        for fld in (f.get('必填') or []):
            if fld not in have:
                err('表「%s」必填 的「%s」不在字段列表里' % (name, fld))
            elif fld in late:
                # 关联记录：补丁阶段建控件时直接落 required（patch_fields 已支持）；他表字段/汇总不支持必填
                if not any(l.get('表') == name and l.get('字段') == fld for l in (spec.get('links') or [])):
                    is_sum = any(s.get('表') == name and s.get('字段') == fld for s in (spec.get('summaries') or []))
                    if is_sum:
                        warn('表「%s」的汇总「%s」写在必填里：建壳阶段不存在，规格落不了；要它必填请在建后套件 '
                             "struct_cfg.py 写 OPT_FLAGS = {'%s': {'%s': {'required': True}}}" % (name, fld, name, fld))
                    else:
                        err('表「%s」的「%s」是他表字段，不该必填（值来自源表）' % (name, fld))
        for fld, opts in (f.get('选项') or {}).items():
            if fld not in have:
                err('表「%s」选项 的「%s」不在字段列表里' % (name, fld))
            if not isinstance(opts, dict) or not opts:
                err('表「%s」选项「%s」要是非空对象 {键: 值}' % (name, fld))
                continue
            for k in opts:
                if k in reserved:
                    err('表「%s」选项「%s」的「%s」是保留键，不能覆盖' % (name, fld, k))
                elif k not in ok_keys:
                    err('表「%s」选项「%s」的「%s」不是 options 级键 —— 要么写错了名字'
                        '（make_widget 只会打一行警告然后**丢弃**），要么是建壳器级的参数'
                        '（如 dateType/mode/expression，工厂会翻译成别的 options 键，'
                        '不能直接写）。可用：%s'
                        % (name, fld, k, '、'.join(sorted(ok_keys))))


def check_containers(spec):
    """`容器` 点名的字段必须真在这张表上、不被重复点名、也不写进 layouts 分节。

    **这条检查以前完全不存在**——因为规格语言里根本没有「容器」这个概念。
    需求写「跟进记录、拜访记录、机会目录用多 tab」时，作者只能把三个控件平铺建出来、
    事后再手工搬，而 `precheck` / 建表 / 补丁**没有任何一环会告诉你 tab 没建**。
    2026-09-18 实测：一份需求点名 3 个字段用多 tab，应用建完是三个平铺的关联记录，
    接口全绿、预检通过，直到用户回头问「Tabs 布局空间可以加吗」。
    需求被静默降级 —— 就是本条要堵的口子。
    """
    for f in (spec.get('forms') or []):
        name = f.get('名称')
        cons, errs = normalize_containers(f)
        for e in errs:
            err(e)
        if not cons:
            continue
        # 表上的控件 = 建壳字段 + 补丁阶段建的（关联带出、汇总）—— 与 check_layouts 同口径
        have = set(f.get('字段') or [])
        for l in (spec.get('links') or []):
            if l.get('表') == name:
                have |= set(l.get('带出') or [])
        have |= {s.get('字段') for s in (spec.get('summaries') or []) if s.get('表') == name}
        in_sec = {x for sec in ((spec.get('layouts') or {}).get(name) or [])
                  for x in (sec.get('字段') or [])}
        for c in cons:
            for label, pf in c['panes']:
                for fld in pf:
                    if fld not in have:
                        err('表「%s」容器「%s」的页签「%s」点名了「%s」，该表没有这个字段'
                            % (name, c['name'], label, fld))
                    if fld in in_sec:
                        # 容器段会把控件从卡里摘走；那一节的段标题就成了孤儿分隔线。
                        # `group_into_tabs` 会清掉紧挨着的/收尾的孤儿，但中间那根会留下。
                        err('表「%s」的「%s」既在容器「%s」里、又写进了 layouts 分节——'
                            '容器会把它从卡里摘走，那一节只剩一条光秃秃的分隔线。'
                            '容器字段不要写进 layouts' % (name, fld, c['name']))
        # 容器**固定落在表单末尾**（这样重跑位置才稳定，见 desform_utils.group_into_tabs），
        # 且不依赖 `字段` 列表里的先后 —— 所以这里**不**按 `字段` 顺序提示「后面还有几个字段」：
        # 最终排布由 `layouts` 的分节顺序 + rest 决定，拿 `字段` 顺序去推断是个假模型
        # （2026-09-18 实测：它对本项目自己的规格刷出一条毫无意义的提示）。


def check_formulas(spec):
    for f in (spec.get('forms') or []):
        name = f.get('名称')
        for k, expr in (f.get('公式') or {}).items():
            for ph in re.findall(r'\$([^$]+)\$', expr or ''):
                if ph not in EFF.get(name, set()):
                    err('表「%s」公式「%s」引用了本表没有的字段「%s」' % (name, k, ph))


def check_titles(spec):
    # 靠「关联带出」建出来的字段（补丁阶段才存在）——建壳阶段解析不到。
    link_out = {}
    for l in (spec.get('links') or []):
        link_out.setdefault(l.get('表'), set()).update(l.get('带出') or [])
    for f in (spec.get('forms') or []):
        name, title = f.get('名称'), f.get('标题')
        if not title:
            warn('表「%s」没写标题字段' % name)
        elif title not in EFF.get(name, set()):
            err('表「%s」标题「%s」既不是自身字段，也不是关联带出的字段' % (name, title))
        elif title in link_out.get(name, set()):
            # 2026-09-17 实测：52 表里 19 张明细表的标题就是这么错的——规格写「产品名称」，
            # 该字段由 links 带出（补丁阶段才建），建壳时不存在，带出/汇总/公式分支都跳过它，
            # 构建器**静默回退**成字段列表里下一个能用的控件（例：标题变成「已出库-退货数量」）。
            # 接口全绿、列表标题列却是空的，只有逐表回读 config.titleField 才看得出。
            pass    # 标题是带出字段：build_app 布局段（regroup_layout --spec）会把 titleField 指回它，不再提示


# ---------------- 看板 ----------------

#: 看板的系统字段 —— **不在表单 `fields` 里**，但引擎解析 dim/grp/val 时会并进来。
#: `qqy_ops.py` 原话：「创建人/流程状态等系统字段不在表单 fields 里，解析 dim/grp/assist
#: 必须并入」；`gen_qqy_all_comps.py` 也要求 filterField 必须含这 5 个系统字段。
#: 图表里写的是**中文名**（黄金样例就是这么写的：`"assistType":"创建人"`），model 名一并收下。
#: ⚠️ 2026-09-18 实测：这里以前只有 `record_count`/`create_time`，于是任何按「创建人」分组的
#: 图都被判成「字段不在表里」——**假阳性**，而且是逼人无视预检的那一类。
SYS_FIELDS = {'record_count',
              'create_time', 'update_time', 'create_by', 'update_by', 'bpm_status',
              '创建时间', '修改时间', '创建人', '修改人', '流程状态'}


def check_pages(spec):
    code_of = {}
    for f in (spec.get('forms') or []):
        code_of[f.get('名称')] = (f.get('code') or '').strip() or f.get('名称')
    for p in (spec.get('pages') or []):
        pname = p.get('name')
        if not pname:
            err('有看板没写 name')
            continue
        charts = p.get('charts') or {}
        all_titles = set()
        for form, specs in charts.items():
            table = form if form in BY_NAME else None
            if not table:
                for nm, cd in code_of.items():
                    if form == cd:
                        table = nm
                        break
            if not table:
                err('看板「%s」引用了不存在的表「%s」' % (pname, form))
                continue
            flds = set(EFF.get(table, set())) | SYS_FIELDS
            for s in specs:
                title = s.get('title') or s.get('componentName') or '?'
                all_titles.add(title)
                dims = s.get('dim')
                dims = [dims] if isinstance(dims, str) else (dims or [])
                vals = s.get('val')
                vals = [vals] if isinstance(vals, str) else (vals or [])
                # ⚠️ 透视表空 val 会让 add-charts 直接失败（实测 25 张盘里 13 张栽在这）
                if s.get('comp') == 'JPivotTable' and not any(vals):
                    err('看板「%s」图「%s」是透视表但 val 为空 —— 清单式透视请给 record_count'
                        % (pname, title))
                for d in ([s.get('grp')] if s.get('grp') else []) + dims + vals:
                    # 透视表的 `val` 允许写成 `{"field":…, "calc":…}` 对象
                    # （多度量透视，见 charts-special.md）。直接拿整个 dict 去查集合会
                    # `TypeError: unhashable type: 'dict'` —— 而它**只在规格里带 pages 时**
                    # 才触发（不带 pages 则 check_pages 整段跳过），于是这个崩溃一直没被
                    # 预检自己发现：一旦把看板规格并进 app_spec.json，预检就整段挂掉。
                    if isinstance(d, dict):
                        d = d.get('field')
                    if d and d not in flds:
                        err('看板「%s」图「%s」的字段「%s」不在 %s 里'
                            % (pname, title, d, table))
        # ⚠️ add-filter 的 charts 必须同一张表；跨表要每表一次
        # ⚠️ 且**图名之间不能互为子串**：`qqy_ops.cmd_add_filter` 的 `_chart_hit` 是
        #    `kw == a or kw in a or a in kw`，命中多条就报「同名多张，请用 componentName
        #    精确定位」并让**整张盘 FAIL**（图已建好、只差筛选栏，重跑还得先 --recreate）。
        #    2026-09-17 实测栽了 4 张：对账数量/对账数量2、客户/客户标签分析、堆叠柱形图/堆叠柱形图2。
        all_titles = []
        for form, specs in charts.items():
            for s in specs:
                t = s.get('title') or s.get('componentName')
                if t:
                    all_titles.append(t)

        def _hits(kw):
            return [t for t in all_titles if kw == t or kw in t or t in kw]

        for flt in (p.get('filters') or []):
            names = flt.get('charts') or []
            if not names:
                err('看板「%s」的查询面板没写 charts' % pname)
                continue
            tables = set()
            for n in names:
                for form, specs in charts.items():
                    if any((s.get('title') or s.get('componentName')) == n for s in specs):
                        tables.add(form)
                        break
                else:
                    warn('看板「%s」查询面板引用的图「%s」不在本页 charts 里' % (pname, n))
                hit = _hits(n)
                if len(hit) > 1:
                    err('看板「%s」查询面板的图名「%s」会命中多张图 %s —— add-filter 会直接失败；'
                        '把同页标题改成互不为子串（如「应收对账数量」/「应付对账数量」）'
                        % (pname, n, hit))
            if len(tables) > 1:
                err('看板「%s」的查询面板跨了多张表 %s —— add-filter 必须同表，请每表一条'
                    % (pname, sorted(tables)))


# ---------------- 流程 ----------------

def load_flows(path):
    """执行 flows.py 拿 FLOWS。flow_dsl 是纯数据构造、不联网，所以可以安全 exec。"""
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    mf = os.path.normpath(os.path.join(here, '..', '..',
                                       'jeecg-lowcode-miniflow', 'scripts'))
    if mf not in sys.path:
        sys.path.insert(0, mf)
    m = importlib.util.spec_from_file_location('user_flows', path)
    mod = importlib.util.module_from_spec(m)
    try:
        m.loader.exec_module(mod)
    except NameError as ex:
        # 同 app_audit：建后套件的 pb_flows.py 传进来只会报裸 NameError（2026-09-22 项目管理 R2）
        raise SystemExit('FAIL: --flows 要的是 flow_dsl 写的 flows.py（定义 FLOWS = [...]），'
                         '%s 看起来是建后套件的 pb_flows.py：%s' % (path, ex))
    return getattr(mod, 'FLOWS', None) or []


def _node_tables(nodes):
    out = []
    for n in nodes or []:
        if n.get('table'):
            out.append(n['table'])
        for b in (n.get('branches') or []):
            out += _node_tables(b.get('nodes') or [])
    return out


def _spec_ftype(spec):
    """规格 → 「(表, 字段) 的控件类型」。只回答规格里**明说了**的（公式/汇总/带出/类型），推断出来的返回 None。"""
    ty = {}
    zh = {'金额': 'money', '数字': 'number', '整数': 'integer'}
    for f in spec.get('forms') or []:
        t = f.get('名称')
        for k, v in (f.get('类型') or {}).items():
            if v in zh:
                ty[(t, k)] = zh[v]
        for k in (f.get('公式') or {}):
            ty[(t, k)] = 'formula'
    for sm in spec.get('summaries') or []:
        ty[(sm.get('表'), sm.get('字段'))] = 'summary'
    for lk in spec.get('links') or []:
        for k in list(lk.get('带出') or []) + list((lk.get('带出映射') or {}).keys()):
            ty.setdefault((lk.get('表'), k), 'link-field')
    return lambda t, f: ty.get((t, f))


def apply_flow_rules(flows, spec):
    """引擎行为规则（miniflow/scripts/flow_rules.py）：与 build_flows 走同一份实现，
    所以「真机构建时会被改写 / 会被拦下」的东西，这里不联网就能看到。
    返回**改写后**的流程（后面的静态检查按最终形态查）。"""
    try:
        import flow_rules as FR
    except ImportError:
        warn('找不到 miniflow/scripts/flow_rules.py —— 引擎行为规则（无数据支不执行 / 公式累加冲 0 / '
             '同事件多流程 …）本次未检查')
        return flows
    flows, r1 = FR.apply_static(flows)
    fx = {(f.get('名称'), k): v for f in spec.get('forms') or [] for k, v in (f.get('公式') or {}).items()}
    flows, r2 = FR.apply_typed(flows, _spec_ftype(spec), lambda t, f: fx.get((t, f)))
    # 公式套公式 + 被流程 update()：引擎 handlerLinkFieldValue 把公式延后求值，外层公式的 env 取的是内层公式
    # **更新前**的旧值（DesignFormDataServiceBaseImpl:1398-1404 / 1664-1671）→ 流程写完一次后外层不对。
    import re as _re
    updated = {n.get('table') for f in flows for n in FR.walk_nodes(f.get('nodes') or []) if n.get('type') == 'data_update'}
    for (t, k), expr in fx.items():
        inner = [r for r in _re.findall(r'\$([^$]+)\$', expr or '') if (t, r) in fx]
        if not inner:
            continue
        # 2026-09-22 进销存 R2 实测更正：不止「被流程更新的表」—— **任何 API / 流程建的行**，
        # 外层公式都拿内层公式的旧值（盘点明细、采购入库明细、价格表都中招，落 0 让下游条件恒不成立）。
        # 被流程更新的表更严重（每写一次就错一次），仍然单独点名。
        warn('表「%s」的公式「%s」引用了同表公式 %s —— 引擎对公式延后求值，外层会拿到内层的旧值'
             '（API/流程建的行一律落 0，不限于被流程更新的表）；请展开成只引用基础字段的单层公式%s'
             % (t, k, '、'.join(inner), '。⚠️ 本表还被流程 update，错值会被反复写入' if t in updated else ''))
    # 被 inc/dec 累加的列若既没在 add() 里补 0、也没有默认值 → API/UI 建的行上第一次累加被静默吞掉
    inc_cols = FR.inc_columns(flows)
    added = {}
    for f in flows:
        for n in FR.walk_nodes(f.get('nodes') or []):
            if n.get('type') == 'data_add':
                added.setdefault(n.get('table'), set()).update((n.get('mapping') or {}).keys())
    for t, cols in sorted(inc_cols.items()):
        # `--struct` 给了建后套件配置时，DEFAULTS() 里已有默认值的列也算有初值
        # （2026-09-24 一句话建应用三应用：`static('任务','实际工时',0)` 写了，这条提示照报，属误报）
        bare = sorted(c for c in cols if c not in added.get(t, set()) and (t, c) not in DEFAULTED)
        if bare:
            warn('表「%s」的 %s 会被流程累加，但没有任何 add() 给它们初值 —— API/页面建的行上'
                 '第一次「增加/减少」会被静默吞掉；请在建后套件 DEFAULTS() 里给 0'
                 % (t, '、'.join(bare)))
    for rep in (r1, r2):
        for m in rep['errors']:
            err(m)
        for m in rep['warnings']:
            warn(m)
        for m in rep['notes']:
            warn('（构建时自动改写，无需处理）' + m)
    return flows


def check_flows(flows, spec):
    if not flows:
        return
    flows = apply_flow_rules(flows, spec)
    subs = [f for f in flows if f.get('kind') == 'sub']
    SUBS.clear()
    SUBS.update(f['name'] for f in subs)
    names = [f.get('name') for f in flows]
    dup = {n for n in names if names.count(n) > 1}
    if dup:
        err('流程名重复：%s' % '、'.join(sorted(dup)))

    NODES.clear()
    for f in flows:
        name = f.get('name')
        ctx = f.get('table') or f.get('context')
        if ctx not in BY_NAME:
            err('流程「%s」的表「%s」不存在' % (name, ctx))
            continue
        ctxf = EFF.get(ctx, set())
        NODES[name] = _node_map(f.get('nodes'), ctx)
        for t in _node_tables(f.get('nodes')):
            if t not in BY_NAME:
                err('流程「%s」引用了不存在的表「%s」' % (name, t))
        for node in (f.get('nodes') or []):
            _check_node(name, ctx, ctxf, node)
    _check_shared_subflows(flows, subs)


def _check_shared_subflows(flows, subs):
    """同一条子流程被 ≥2 条流程逐行调用，而子流程里取了「本行」字段 → 只能绑一个调用方。

    build_flows 回填时把子流程里「本行」引用改成**调用方那个取多条节点的 id**；第二个调用方的节点 id
    不同，引用仍指向第一个 → 从第二个父流程调用时本行取值**全空**，四道闸门都不报
    （2026-09-24 进销存-速测18：销售换货复用应收明细子流程，数量为空）。每个调用方各建一条子流程。"""
    callers = {}

    def walk(nodes, fname):
        for n in nodes or []:
            if not isinstance(n, dict):
                continue
            if n.get('type') == 'subprocess' and n.get('multi', True):
                callers.setdefault(n.get('sub'), set()).add(fname)
            for b in (n.get('branches') or []):
                walk((b or {}).get('nodes'), fname)
            for k in ('found', 'missing', 'default', 'nodes'):
                if isinstance(n.get(k), list):
                    walk(n[k], fname)

    for f in flows:
        walk(f.get('nodes'), f.get('name'))

    def uses_row(o):
        if isinstance(o, dict):
            if '$ref' in o and o.get('$node') in (None, 'start'):
                return True
            return any(uses_row(v) for v in o.values())
        if isinstance(o, list):
            return any(uses_row(v) for v in o)
        return False

    for f in subs:
        who = sorted(callers.get(f.get('name')) or ())
        if len(who) > 1 and uses_row(f.get('nodes')):
            err('子流程「%s」被 %d 条流程逐行调用（%s），且子流程里取了本行字段 ref() —— '
                '本行取值只能绑定一个调用方，其余调用方调用时取值全空。每个调用方各建一条子流程'
                % (f.get('name'), len(who), '、'.join(who)))


def _node_map(nodes, ctx, out=None):
    """流程内「节点名 → 该节点产出的表」——`ref(字段, node=X)` 要按 X 的表校验。"""
    out = {} if out is None else out
    for n in nodes or []:
        if not isinstance(n, dict):
            continue
        if n.get('name') and n.get('type') != 'subprocess':
            out[n['name']] = n.get('table') or ctx
        for b in (n.get('branches') or []):
            _node_map(b.get('nodes'), ctx, out)
        _node_map(n.get('found'), ctx, out)
        _node_map(n.get('missing'), ctx, out)
    return out


def _check_node(fname, ctx, ctxf, node, depth=0):
    if depth > 4:
        return
    t = node.get('type')
    if t == 'get_one' or t == 'get_more':
        tb = node.get('table')
        for c in (node.get('cond') or []):
            # ⚠️ 两种写法都要收（2026-09-17 修）：
            #   · 字符串       → 同名匹配：字段要在**上下文表**和**目标表**都有
            #   · (字段,规则,值) → 显式：字段名是**目标表**的，值可能是 ref()/var() 的 dict
            # 老版本直接 `if c not in ctxf`，元组里带 dict 会
            # `TypeError: unhashable type: 'dict'`，**整段流程校验跑不完**。
            fld = c if isinstance(c, str) else (c[0] if isinstance(c, (list, tuple)) and c else None)
            if fld is None:
                err('流程「%s」cond 形态无法识别：%r' % (fname, c))
                continue
            if isinstance(c, str) and fld not in ctxf:
                err('流程「%s」cond「%s」：上下文表 %s 没有该字段（两侧同名才取得到值）'
                    % (fname, fld, ctx))
            if tb in BY_NAME and fld not in EFF.get(tb, set()):
                err('流程「%s」cond「%s」：目标表 %s 没有该字段' % (fname, fld, tb))
        # 「取本单的关联明细」= `get_more(..., from_="start")`，引擎要拿**本表指向目标表的
        # 那条关联控件**（selectType=3 + linkFormTableField）。本表没有这条关联时，
        # 设计器里「选择数据对象」空白、紧跟的 call_sub 直接报「子流程尚未构建」级联失败。
        # 2026-09-17 实测：4 条主流程栽在这里（写的是**关联控件的显示名**而非**目标表名**，
        # 例如「采购退货.退货产品明细」的目标表其实叫「采购退货产品明细」）。
        if t == 'get_more' and str(node.get('from') or '') in ('start', '工作表事件触发'):
            if tb in BY_NAME and not any(
                    l.get('表') == ctx and l.get('目标') == tb for l in (SPEC.get('links') or [])):
                err('流程「%s」get_more("%s", from_="start")：本表 %s 没有指向「%s」的关联记录'
                    '（from_="start" 要写**目标表名**，不是关联控件的显示名）'
                    % (fname, tb, ctx, tb))
    elif t in ('data_update', 'data_add'):
        tb = node.get('table')
        if tb not in BY_NAME:
            return
        for k in (node.get('mapping') or {}):
            if k not in EFF.get(tb, set()):
                err('流程「%s」写 %s.%s：目标表没有该字段' % (fname, tb, k))
    elif t == 'approve_result':
        for b in (node.get('branches') or []):
            for n in (b.get('nodes') or []):
                _check_node(fname, ctx, ctxf, n, depth + 1)
    elif t == 'subprocess':
        if node.get('sub') not in SUBS:
            err('流程「%s」call_sub 调了未定义的子流程「%s」' % (fname, node.get('sub')))
    elif t == 'exclusive':
        brs = node.get('branches') or []
        # 排他网关至少要 2 个出口，且必须留一支不带条件做默认支。
        # 2026-09-17 实测：只写「如果 X 就走这一支」而漏掉「其他情况」那支时，
        # save_flow 全绿、deploy 才报「检测到排他网关, 仅有一个出口却配置了条件！」——
        # 4 条审批链整条发布不出来，得再跑一轮 build_flows（全量重发 234s）。
        if len(brs) < 2:
            err('流程「%s」网关「%s」只有 %d 个出口：排他网关至少 2 支，'
                '且其中一支不带条件（默认支 / 「其他情况进入此流程」）'
                % (fname, node.get('name'), len(brs)))
        elif not any(not (b.get('cond') or []) for b in brs):
            err('流程「%s」网关「%s」的 %d 个出口全带条件：必须留一支不带条件的默认支'
                % (fname, node.get('name'), len(brs)))
        for b in brs:
            for (fld, _rule, _val) in (b.get('cond') or []):
                # 判据主语可以是 `result("运算节点名")`（一个 dict）—— 2026-09-21 前这里直接拿它
                # 做 `in ctxf`，抛 `TypeError: unhashable type: 'dict'` 把整个预检带崩。
                if isinstance(fld, dict):
                    rn = fld.get('$result')
                    if rn is None:
                        # ref(字段, node=取单条节点) 当主语：build_flows 会拒（落库形态未实测），这里先拦
                        err('流程「%s」网关判据写成了 %s —— 主语只能是触发行字段名或 result(运算节点)；'
                            '按查到的记录判：compute("取值", "$x$", {"x": ref(字段, node=节点名)}) 再 result("取值")，'
                            '或并进 get_one 的 cond 用 empty="分支" + data_branch()' % (fname, fld))
                    elif rn not in (NODES.get(fname) or {}):
                        err('流程「%s」网关判据 result("%s")：前面没有叫这个名字的运算节点' % (fname, rn))
                    continue
                if fld not in ctxf:
                    err('流程「%s」网关条件字段「%s」不在上下文表 %s 里' % (fname, fld, ctx))
            for n in (b.get('nodes') or []):
                _check_node(fname, ctx, ctxf, n, depth + 1)


def _walk_ref_nodes(node, out):
    """收集 `($ref, $node)` 对——**带 node 的 ref 取的是那个节点产出的记录**。"""
    if isinstance(node, dict):
        if '$ref' in node:
            out.append((node['$ref'], node.get('$node') or 'start'))
        for v in node.values():
            _walk_ref_nodes(v, out)
    elif isinstance(node, list):
        for v in node:
            _walk_ref_nodes(v, out)


def check_flow_refs(flows):
    """`ref()` 分两种来源校验（2026-09-17 修）：

    · `node=start`（缺省）→ 取**上下文行**的字段，必须在本表（含带出）里；
    · `node=<取单/新增节点名>` → 取**那个节点产出的记录**的字段，要按**那个节点的表**查。

    老版本一律按上下文表查，跨表 `ref(字段, node="获取采购入库")` 全部误报——
    实测一个 52 表应用会刷 30+ 条假错误，等于把流程段的校验废掉。
    """
    for f in flows:
        name = f.get('name')
        ctx = f.get('table') or f.get('context')
        if ctx not in BY_NAME:
            continue
        ctxf = EFF.get(ctx, set())
        by_node = NODES.get(name) or {}
        refs = []
        _walk_ref_nodes(f.get('nodes') or [], refs)
        for r, nd in refs:
            if nd in ('start', '子流程', '工作表事件触发'):
                if r not in ctxf:
                    err('流程「%s」ref("%s")：上下文表 %s 没有该字段（子流程只能读本行）'
                        % (name, r, ctx))
                continue
            tb = by_node.get(nd)
            if tb is None:
                err('流程「%s」ref("%s", node=%r)：流程里没有这个节点名'
                    % (name, r, nd))
            elif r not in EFF.get(tb, set()):
                err('流程「%s」ref("%s", node=%r → %s)：该表没有这个字段'
                    % (name, r, nd, tb))


# ---------------- 数值用途 ----------------

NUMERIC_OK = {'money', 'number', 'integer', 'formula', 'summary', 'capital-money', 'rate'}
# ⚠️ 别叫 DATE_TYPES：同名模块级常量会覆盖上面日期粒度的合法集（year/datetime…），
# 2026-09-24 实测把所有 datetime/year 日期粒度判成不合法（第 14 轮四个应用全中）。
NUM_DATE_OK = {'date', 'time'}
CMP_RULES = {'大于', '大于等于', '小于', '小于等于', 'gt', 'ge', 'lt', 'le'}
SUM_NUMERIC = {'求和', '合计', '平均', '平均值', '均值'}
SUM_EXTREME = {'最大', '最大值', '最小', '最小值'}
TEXT_FUNCS = re.compile(r'\b(CONCAT|TEXT|LEFT|RIGHT|MID|SUBSTR\w*|REPLACE|UPPER|LOWER|TRIM)\s*\(', re.I)
TYPE_HINT = {'input': '单行文本', 'textarea': '多行文本', 'select': '下拉', 'radio': '单选',
             'checkbox': '多选', 'link-record': '关联记录', 'auto-number': '自动编号',
             'select-user': '选择用户', 'select-depart': '选择部门', 'phone': '手机号',
             'file-upload': '附件', 'imgupload': '图片', 'area-linkage': '省市区', 'date': '日期'}


def field_type(spec, table, fld, depth=0):
    """规格 → (表, 字段) 建出来会是什么控件。按 build_app `_split_fields` 的优先级复刻；
    判不出（系统字段、带出追不到源、中转字段）返回 None —— 调用方跳过，不猜。"""
    f = BY_NAME.get(table)
    if f is None or depth > 6:
        return None
    for lk in (spec.get('links') or []):
        if lk.get('表') != table:
            continue
        if lk.get('字段') == fld:
            return 'link-record'
        if fld in (lk.get('带出') or []):
            return field_type(spec, lk.get('目标'), fld, depth + 1)
        src = (lk.get('带出映射') or {}).get(fld)
        if src:
            return field_type(spec, lk.get('目标'), src, depth + 1)
    if any(s.get('表') == table and s.get('字段') == fld for s in (spec.get('summaries') or [])):
        return 'summary'
    if fld not in (f.get('字段') or []) or fld in (f.get('中转字段') or {}):
        return None
    if fld in (f.get('字典') or {}) or fld in (f.get('静态下拉') or {}):
        return 'select'
    if fld in (f.get('静态多选') or {}):
        return 'checkbox'
    if fld in (f.get('静态单选') or {}):
        return 'radio'
    if fld in (f.get('日期粒度') or {}):
        return 'date'
    if fld in (f.get('编号') or {}):
        return 'auto-number'
    if fld in (f.get('公式') or {}):
        return 'formula'
    from spec_infer import explicit, infer
    tn = (f.get('类型') or {}).get(fld)
    if tn:
        try:
            return explicit(tn)
        except ValueError:
            return None             # check_types 已报
    return infer(fld)


def _numeric_err(table, fld, typ, used_by, ok):
    if typ is None or typ in ok:
        return
    err('表「%s」的「%s」被%s当数值用，但它会建成「%s」(%s) —— 文本上的比较/求和接口全绿、结果全错。'
        '修：在 forms[名称=%s].类型 里写 "%s": "金额"（或 "数字"/"整数"）'
        % (table, fld, used_by, TYPE_HINT.get(typ, typ), typ, table, fld))


def _walk_conds(fname, nodes, ctx, out):
    """收集流程里所有 (表, 字段, 规则, 出处) 条件：网关/分支按上下文表，取数节点按目标表。"""
    for n in nodes or []:
        if not isinstance(n, dict):
            continue
        t = n.get('type')
        tb = n.get('table') if t in ('get_one', 'get_more', 'upsert') else ctx
        for c in (n.get('cond') or []):
            if isinstance(c, (list, tuple)) and len(c) >= 2:
                out.append((tb, c[0], c[1], '流程「%s」节点「%s」的条件' % (fname, n.get('name') or t)))
        for b in (n.get('branches') or []):
            for c in (b.get('cond') or []):
                if isinstance(c, (list, tuple)) and len(c) >= 2:
                    out.append((ctx, c[0], c[1], '流程「%s」分支「%s」的条件'
                                % (fname, b.get('name') or n.get('name') or '分支')))
            _walk_conds(fname, b.get('nodes'), ctx, out)
        for k in ('found', 'missing', 'nodes'):
            _walk_conds(fname, n.get(k), ctx, out)


def check_numeric_usage(spec, flows, flow_spec=None):
    """**被当数值用的字段必须建成数值控件**（2026-09-24 加）。

    一句话建应用时，规格作者（模型）自己起字段名，`计划资金` `拜访费用` 这类名字
    没有「金额」二字 → `infer()` 兜底成单行文本；而审批网关「计划资金 大于等于 200」、
    汇总「拜访费用 求和」、公式「$拜访费用$+$差旅费用$」都把它当数值用。
    接口、save/deploy、契约闸门全绿，只有结果错（文本比较 "90" > "200"、文本求和 0）。
    `check_undeclared` 只给一条汇总 warn，淹在提示里 —— 这里按**用途**判 err。

    日期可以参与比较（到期日 小于 今天）、极值汇总（最近跟进时间 = 最大值）和公式运算（日期差），
    只有求和/平均必须是纯数值。

    汇总/公式建表时按**规格原名**编译，用 spec；流程条件写的是 RENAME 后的现名，用 flow_spec
    （项目管理-兵团：RENAME 把关联「人力成本预算明细」改成与汇总同名，按现名判公式会误报 3 条）。
    """
    flow_spec = flow_spec or spec
    for sm in spec.get('summaries') or []:
        way = sm.get('方式') or '求和'
        if way not in SUM_NUMERIC | SUM_EXTREME:
            continue
        tgt = next((lk.get('目标') for lk in (spec.get('links') or [])
                    if lk.get('表') == sm.get('表') and lk.get('字段') == sm.get('关联字段')), None)
        col = sm.get('汇总列')
        if not tgt or not col:
            continue
        ok = NUMERIC_OK if way in SUM_NUMERIC else NUMERIC_OK | NUM_DATE_OK
        _numeric_err(tgt, col, field_type(spec, tgt, col),
                     '汇总 %s.%s（%s）' % (sm.get('表'), sm.get('字段'), way), ok)

    for f in spec.get('forms') or []:
        t = f.get('名称')
        for k, expr in (f.get('公式') or {}).items():
            expr = expr or ''
            if TEXT_FUNCS.search(expr):
                continue
            # 只判**直接参与四则运算**的占位符：左右紧挨 + - * /。
            # 函数参数（`DATEIF($开始日期$,$完成日期$,1,'d')`）不在此列。
            for m in re.finditer(r'\$([^$]+)\$', expr):
                before = expr[:m.start()].rstrip()[-1:]
                after = expr[m.end():].lstrip()[:1]
                if (before and before in '+-*/') or (after and after in '+-*/'):
                    _numeric_err(t, m.group(1), field_type(spec, t, m.group(1)),
                                 '公式 %s.%s' % (t, k), NUMERIC_OK | NUM_DATE_OK)

    conds = []
    for fl in flows or []:
        ctx = fl.get('table') or fl.get('context')
        for c in (fl.get('cond') or []):
            if isinstance(c, (list, tuple)) and len(c) >= 2:
                conds.append((ctx, c[0], c[1], '流程「%s」的触发条件' % fl.get('name')))
        _walk_conds(fl.get('name'), fl.get('nodes'), ctx, conds)
    seen = set()
    for tb, fld, rule, used_by in conds:
        if rule not in CMP_RULES or not isinstance(fld, str) or (tb, fld, used_by) in seen:
            continue
        seen.add((tb, fld, used_by))
        _numeric_err(tb, fld, field_type(flow_spec, tb, fld),
                     '%s（%s）' % (used_by, rule), NUMERIC_OK | NUM_DATE_OK)


# ---------------- 数量 ----------------

def check_counts(spec, expect):
    # 分组同时来自表单和看板（「经营看板」这类组只有看板、没有表单）
    got = {
        '分组': len({x.get('分组') for x in (spec.get('forms') or []) if x.get('分组')}
                  | {x.get('group') for x in (spec.get('pages') or []) if x.get('group')}),
        '表单': len(spec.get('forms') or []),
        '字典': len(spec.get('字典') or {}),
        '看板': len(spec.get('pages') or []),
    }
    for k, v in got.items():
        print('  %s：%d%s' % (k, v, ('（期望 %d）' % expect[k]) if expect.get(k) else ''))
    for k, want in (expect or {}).items():
        if want and got.get(k) != want:
            err('%s 数 %d ≠ 期望 %d' % (k, got.get(k), want))


#: 建后套件 DEFAULTS() 里配了默认值的 (表, 字段)；只在传 --struct 时填充
DEFAULTED = set()
#: 建后套件会改控件类型的 (表, 字段)：TO_LINKFIELD（→ 他表字段）、LINKDATA（→ 下拉来自工作表）
STRUCT_TYPED = set()


def load_struct_typed(path):
    ns = {}
    try:
        exec(compile(open(path, encoding='utf-8').read(), path, 'exec'), ns)
    except Exception:                  # noqa: BLE001  读不全只影响「兜底」提示，不拦
        return set()
    out = set()
    for t, rows in (ns.get('TO_LINKFIELD') or {}).items():
        for row in rows or []:
            if row:
                out.add((t, row[0]))
    for row in ns.get('LINKDATA') or []:
        if row and len(row) >= 2:
            out.add((row[0], row[1]))
    return out


def load_struct_defaults(path):
    """离线执行 struct_cfg.py 的 DEFAULTS()：助手全换成**只记名**的桩，不联网、不读 probe。

    只关心「哪些 (表, 字段) 有默认值」—— 给「流程累加目标缺初值」这条提示消误报用。
    配置里用到桩以外的名字时只提示、不中断预检。
    """
    got = set()

    def _pairs(pairs):
        for t, n in pairs or []:
            got.add((t, n))

    def _one(t, name, *a, **k):
        got.add((t, name))

    ns = {'__name__': 'struct_cfg', '__file__': path}
    ns.update({'current_user': _pairs, 'current_dept': _pairs, 'today': _pairs, 'now': _pairs,
               'static': _one, 'compose': _one, 'func': _one, 'take': _one, 'same': _one,
               'lookup': _one, 'lookup_count': _one,
               'F': lambda t, n: '$%s.%s$' % (t, n), 'COUNT': lambda *a: 'COUNT()'})
    try:
        exec(compile(open(path, encoding='utf-8').read(), path, 'exec'), ns)
        if callable(ns.get('DEFAULTS')):
            ns['DEFAULTS']()
    except Exception as ex:          # 桩覆盖不到的写法：不拦预检，只提示
        warn('--struct %s 的 DEFAULTS() 没能离线读全（%s: %s）—— 「累加缺初值」提示可能有误报'
             % (path, type(ex).__name__, ex))
    return got


def _renamed_for_flows(spec, struct_path):
    """流程里写的是建后 RENAME 之后的真机现名（带 `/元` 等），规格里是改名前的名字 ——
    以前 `--struct` 只读 DEFAULTS()，流程段照旧名比对，进销存一轮 95 条假违例（速测16/18 S3）。
    这里把 RENAME 套到规格上（与 app_audit.apply_rename 同一实现），并同步 EFF/BY_NAME/SPEC，
    **只影响后面的流程段**：规格自身的校验已经按原名跑完。"""
    ns = {}
    try:
        exec(compile(open(struct_path, encoding='utf-8').read(), struct_path, 'exec'), ns)
    except Exception as ex:                      # noqa: BLE001
        warn('--struct %s 读 RENAME 失败（%s）—— 流程段按规格原名校验' % (struct_path, ex))
        return spec
    ren = ns.get('RENAME') or {}
    if not ren:
        return spec
    from app_audit import apply_rename
    rspec = apply_rename(spec, struct_path)
    for t, m in ren.items():
        if t in EFF:                             # 新旧名都认：看板可能建在改名前，也可能在改名后
            EFF[t] = set(EFF[t]) | {m.get(x, x) for x in EFF[t]}
    BY_NAME.update({f.get('名称'): f for f in (rspec.get('forms') or [])})
    SPEC.clear()
    SPEC.update(rspec)
    print('  （--struct：看板/流程段按 RENAME 后的真机现名校验，%d 张表有改名）' % len(ren))
    return rspec


def main():
    ap = argparse.ArgumentParser(description='零真机预检：规格 + 流程静态校验，不联网')
    ap.add_argument('--spec', required=True)
    ap.add_argument('--flows', default='', help='flows.py（可选）')
    ap.add_argument('--no-flows', action='store_true',
                    help='显式声明本应用没有流程（跳过「漏传 --flows」的拦截）')
    ap.add_argument('--expect', default='',
                    help='数量期望，如 "汇总=7,表单=52,字典=22,看板=25"')
    ap.add_argument('--struct', default='',
                    help='建后套件配置 struct_cfg.py（可选）：读其 DEFAULTS()，已给默认值的累加列不再提示缺初值；'
                         '读其 RENAME，流程段按改名后的真机现名校验')
    a = ap.parse_args()
    if a.struct:
        DEFAULTED.update(load_struct_defaults(a.struct))
        STRUCT_TYPED.update(load_struct_typed(a.struct))

    spec = load_spec(a.spec)
    global BY_NAME
    SPEC.clear()
    SPEC.update(spec)
    for f in (spec.get('forms') or []):
        if f.get('名称') in BY_NAME:
            err('表名重复：%s' % f['名称'])
        BY_NAME[f.get('名称')] = f
    EFF.update({n: set(f.get('字段') or []) for n, f in BY_NAME.items()})

    expect = {}
    for kv in (a.expect or '').split(','):
        if '=' in kv:
            k, v = kv.split('=', 1)
            expect[k.strip()] = int(v)

    print('—— 数量 ——')
    check_counts(spec, expect)

    print('—— 工作表 / 关联 / 汇总 ——')
    build_eff(spec)
    check_forms(spec)
    check_formulas(spec)
    check_titles(spec)
    check_layouts(spec)
    check_menu_order(spec)
    check_containers(spec)
    check_field_opts(spec)
    check_types(spec)
    check_undeclared(spec)

    # 看板/流程写的是建后 RENAME 之后的真机现名：规格自身的校验按原名跑完，这里再套 RENAME
    fspec = _renamed_for_flows(spec, a.struct) if a.struct else spec

    print('—— 看板 ——')
    check_pages(fspec)

    flows = []
    if a.flows:
        print('—— 流程 ——')
        flows = load_flows(a.flows)
        print('  流程：%d（子 %d / 主 %d）'
              % (len(flows), len([x for x in flows if x.get('kind') == 'sub']),
                 len([x for x in flows if x.get('kind') == 'main'])))
        check_flows(flows, fspec)
        check_flow_refs(flows)
    elif not a.no_flows:
        # ⚠️ 2026-09-17 实测事故：漏传 --flows 时流程段**整段不跑**，
        # 却照样打印「✓ 预检通过 —— 可以动真机了」。那一轮 63 条流程带着 19 个静态
        # 就能查出来的错上了真机，代价是一轮 19 条失败 + 两轮 234s 全量重发。
        # 「绿灯」必须覆盖用户手上真实存在的流程，否则就是假绿灯。
        cand = []
        if spec.get('flows'):
            cand.append('spec 里的 flows 数组')
        d = os.path.dirname(os.path.abspath(a.spec))
        try:
            for fn in sorted(os.listdir(d)):
                if not fn.endswith('.py'):
                    continue
                try:
                    txt = io.open(os.path.join(d, fn), encoding='utf-8').read()
                except Exception:
                    continue
                if re.search(r'^\s*FLOWS\s*=', txt, re.M):
                    cand.append(fn)
        except OSError:
            pass
        if cand:
            err('漏传 --flows，流程段整段没校验（发现 %s）。'
                '流程的错只会在真机上暴露 —— 用 --flows <flows.py> 重跑；'
                '确实没有流程就加 --no-flows 显式跳过' % '、'.join(cand))

    print('—— 数值用途（汇总 / 公式 / 流程比较）——')
    check_numeric_usage(spec, list(flows) + list(spec.get('flows') or []), fspec)

    print()
    if warns:
        print('⚠ 提示 %d 条：' % len(warns))
        for w in warns[:20]:
            print('  -', w)
        if len(warns) > 20:
            print('  … 还有 %d 条' % (len(warns) - 20))
    if errs:
        print('✗ 预检不通过 %d 条：' % len(errs))
        for e in errs[:60]:
            print('  -', e)
        if len(errs) > 60:
            print('  … 还有 %d 条' % (len(errs) - 60))
        raise SystemExit(1)
    # 「通过了」这句话只在没有任何提示时才敢说满 —— 提示里躺着的是「接口全绿但内容错」那类，
    # 用户看到 ✓ 就不会再往下看提示（2026-09-17 实测：19 张表的标题就是这么漏掉的）。
    print('✓ 预检通过 —— 可以动真机了' if not warns
          else '✓ 预检通过（有 %d 条提示，逐条确认过再动真机）' % len(warns))


if __name__ == '__main__':
    if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')       # Windows 中文输出
    main()
