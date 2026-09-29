# -*- coding: utf-8 -*-
"""建后核验：**需求提示词里写的控件类型** vs **真机建出来的控件类型**，逐表逐字段比对。

    python postbuild_types.py --work <WORK 目录> [--all]

需求提示词的**文本从标准输入读**（本脚本只处理文本，不读文件；调用方负责把文本管进 stdin）。
`--work` 指 `postbuild_probe.py` 的产物目录（读 `probe.json`；不联网）。

提示词里的表写成 `1. 人员成本 （标题字段：姓名）`、字段写成 `   1) 人员 （选人）`
—— 各应用的表单提示词都是这个写法（实测 项目管理 24 表、ERP表单 54 表、考勤 11 表 均可解析；
**流程 / 仪表盘那两份解析不出字段**，护栏会拒）。解析不到时本脚本**拒绝出「通过」结论**。

**为什么需要它**（2026-09-22 三处同源事故）：控件**种类**只决定「能不能选、显示什么」，
**不影响 save / deploy / 字段权限 / 引用解析**，所以现有的七道闸门
（save·deploy·`check_node_contract`·`postbuild_verify`·`app_audit`·`precheck`·`app_spec` 自检）
**一条都看不见**。界面上却是一眼就看得出来，三处都是**使用者先发现、回头才查出来**的：

| 提示词原文 | 实建 | 后果 |
|---|---|---|
| `职级（关联记录，→职级，单条·下拉）` | 单行文本 | 只能手填裸值，选不了职级 |
| `注册电话（单行文本）` | `phone` 控件 | 带「请输入正确的手机号码」校验，**座机填不进去** |
| `小计（数字，必填，默认值：自动计算…）` | 公式控件 | 控件类型不符 |

三处的共同根因都是「**提示词 → 建表规格**」这层抄漏/抄歪（规格里那条字段没进
`类型` / `links`，就静默落成 `infer()` 猜的单行文本）。本脚本是**唯一**能从需求侧
发现这类偏差的闸门 —— 它比对的是提示词原文，不是规格文件（规格文件本身已经错了）。

解析口径（踩过两次）：
  · 字段名自带括号的（`4) 问题（风险）描述 （多行文本）`）—— 类型括号用 `[^（）]+`，
    否则会把 `问题` 当名字、`风险` 当类型；
  · 列表视图的组件条目（`1) 查询面板 （全局筛选条·下）（位置 第1列/第5行）`）**不是表单字段**，
    按 `位置 第` 跳过，否则每张表都误报几条。

退出码：0=全部一致；1=有类型不符。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

#: 提示词里的中文控件名 → 平台控件 type
#  （提示词写法有近义词，都收在这里；遇到没收录的会在结尾列出，别当通过）
#: 「子表」在需求里有**两个词**、平台上有**两个形态**，单键映射天然只能对上一半：
#:   内部子表 → `type == 'sub-table-design'`（列当场定义，数据嵌在主表 JSON 里）
#:   外部子表 → `type == 'link-record'` **且** 顶层 `isSubTable:true`
#:              （「转换工作表」的产物；转换**刻意不改 `type`**，标记只在 isSubTable + model 前缀，
#:                见 `references/fast-full-chain.md`「③-b 子表（关联工作表）」）
#: 所以「子表」这一档收成一个**候选集合**：内部 / 外部任一都算过。
#: 而「内部子表」「外部子表」这两个需求里真在用的词，各自只认自己那一种 ——
#: 补上它们之前，这两个词根本不在词表里 → 落到「类型名未收录」提示、**完全不参与比对**。
_SUB_INNER = 'sub-table-design'
_SUB_OUTER = 'link-record+isSubTable'      # 仅 type==link-record 且 isSubTable 为真时用这个 token

TYPE_MAP = {
    '关联记录': 'link-record', '他表字段': 'link-field', '汇总': 'summary',
    '单行文本': 'input', '多行文本': 'textarea', '金额': 'money',
    '数字': 'number', '整数': 'integer', '公式': 'formula',
    '选人': 'select-user', '选部门': 'select-depart',
    '日期': 'date', '日期时间': 'date', '开关': 'switch',
    '文件上传': 'file-upload', '附件上传': 'file-upload', '图片上传': 'imgupload',
    '单选框': 'radio', '多选框': 'checkbox', '下拉': 'select', '单选下拉': 'select',
    '下拉选择': 'select', '下拉单选': 'select', '分割线': 'divider',
    '子表': (_SUB_INNER, _SUB_OUTER),
    '内部子表': (_SUB_INNER,), '外部子表': (_SUB_OUTER,),
    '文本组合': 'text-compose', '编号': 'auto-number',
    '自动编号': 'auto-number', '地址': 'area-linkage', '富文本': 'richtext',
    '评分': 'rate', '滑块': 'slider', '颜色': 'color', '手机': 'phone',
    '金额大写': 'capital-money', '大写金额': 'capital-money', '手写签名': 'hand-sign',
}


def wants_of(tcn):
    """需求侧的中文类型 → 可接受的 token 集合（None = 词表未收录）。"""
    v = TYPE_MAP.get(tcn)
    if v is None:
        return None
    return v if isinstance(v, tuple) else (v,)


def actual_type(w):
    """真机控件的比对 token。外部子表要能区别于普通关联记录，所以单独给一个 token。"""
    if w.get('type') == _SUB_INNER:
        return _SUB_INNER
    if w.get('type') == 'link-record' and w.get('isSubTable'):
        return _SUB_OUTER
    return w.get('type')

_TBL_RE = re.compile(r'^\s*\d+\.\s*(\S+?)\s*（标题字段：(.+?)）\s*$', re.M)
_FLD_RE = re.compile(r'^\s*\d+\)\s*(.+?)（([^（）]+)）\s*$', re.M)
_BRACKETS = re.compile(r'（[^）]*）')

err = []          # 类型不符 / 没建出来（判失败）
info = []         # 未收录的类型名（提示：补 TYPE_MAP）
extra = []        # 提示词里没直接写、但建了的字段（默认只计数）


def parse_prompt():
    """从标准输入读需求提示词 → {表名: {字段名: 需求写的类型}}。"""
    txt = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8').read()
    marks = [(m.start(), m.group(1)) for m in _TBL_RE.finditer(txt)]
    out = {}
    for i, (pos, tname) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(txt)
        flds = {}
        for m in _FLD_RE.finditer(txt[pos:end]):
            line, fname, tcn = m.group(0), m.group(1), m.group(2)
            if '位置 第' in line:                       # 列表视图组件，不是表单字段
                continue
            fname = _BRACKETS.sub('', fname).strip()     # `问题（风险）描述` → `问题描述`
            # 类型名取第一个词：`金额，单位元` / `数字，必填` / `文件上传；**初始 hidden=true**`
            tcn = re.split(r'[，,、；;]', tcn)[0].strip().strip('*').strip()
            flds[fname] = tcn
        if flds:
            out[tname] = flds
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', required=True, help='postbuild_probe.py 的产物目录（读 probe.json）')
    ap.add_argument('--all', action='store_true', help='逐字段打印比对过程')
    a = ap.parse_args()

    probe_p = os.path.join(a.work, 'probe.json')
    if not os.path.exists(probe_p):
        print('找不到 %s —— 先跑 postbuild_probe.py --work %s' % (probe_p, a.work))
        return 2
    P = json.load(io.open(probe_p, encoding='utf-8'))
    spec = parse_prompt()

    # ── 覆盖率护栏 ────────────────────────────────────────────────────────
    # 这个脚本最危险的失败模式是**静默通过**：提示词格式一变（表头/字段行的写法换了），
    # 解析出来的是空集或残缺集，于是它照样打印「✓ 一致」—— 比不跑还糟。
    # 所以先自证「我到底读到了多少」，读不到就不许说通过。
    if not spec:
        print('✗ 提示词里一个字段都没解析出来 —— 格式对不上，本次校验无效。\n'
              '  期望的表头：`1. 人员成本 （标题字段：姓名）`\n'
              '  期望的字段行：`   1) 人员 （选人）`')
        return 2
    unparsed = [t for t in P if t not in spec]
    if unparsed:
        info.append('应用里这 %d 张表在提示词里没解析到，**未参与核对**：%s'
                    % (len(unparsed), '、'.join(unparsed)))
    thin = []
    for t, flds in spec.items():
        n_app = len([w for w in (P.get(t) or {}).get('widgets', [])
                     if w.get('type') not in ('divider', 'card', 'tabs', 'grid')])
        if len(flds) <= 1 and n_app >= 5:      # 解析到 0~1 个字段却真有 5+ 个控件 = 多半是格式变了
            thin.append('%s（解析到 %d，真机 %d）' % (t, len(flds), n_app))
    if thin:
        info.append('⚠ 这些表解析到的字段数异常少，检查提示词格式是否变了：' + '、'.join(thin))

    ok = skipped = 0
    for tname, flds in spec.items():
        if tname not in P:
            err.append('提示词里的表「%s」没建出来' % tname)
            continue
        built = {_BRACKETS.sub('', w['name']).strip(): w for w in P[tname]['widgets']}
        for f, tcn in flds.items():
            w = built.get(f)
            if not w:
                err.append('%s.%s 没建出来（提示词：%s）' % (tname, f, tcn))
                continue
            want = wants_of(tcn)
            if want is None:
                skipped += 1
                info.append('提示词里的类型「%s」未收录（%s.%s）—— 请补进 TYPE_MAP' % (tcn, tname, f))
                continue
            got = actual_type(w)
            if got not in want:
                err.append('%s.%s 提示词「%s」应为 %s，实建 %s%s（model %s）'
                           % (tname, f, tcn, ' 或 '.join(want), w['type'],
                              '（外部子表）' if got == _SUB_OUTER else '', w['model']))
            else:
                ok += 1
                if a.all:
                    print('  ✓ %-12s %-12s %s' % (tname, f, got))
        # 提示词里没写、但建了的字段。**默认只计数不列明细**：分割线（提示词用 `▸ 布局` 表达）、
        # 子表列（提示词写在子表那一行里）、自动编号这些天然不在字段列表里，逐条列会淹掉真信号。
        for f in built:
            if f not in flds and not f.startswith('__'):
                extra.append('%s.%s（%s）' % (tname, f, actual_type(built[f])))

    print('提示词可核对的字段 %d 个（一致 %d、类型名未收录 %d）'
          % (ok + len([e for e in err if '应为' in e]), ok, skipped))
    for i in info:
        print('  · ' + i)
    if extra:
        print('  · 另有 %d 个字段提示词里没直接写（分割线/子表列/自动编号等，请自行扫一眼）'
              % len(extra))
        if a.all:
            for e in extra:
                print('      - ' + e)
    if err:
        print('\n✗ 类型不符 %d 处：' % len(err))
        for e in err:
            print('  x ' + e)
        return 1
    print('✓ 控件类型与提示词一致')
    return 0


if __name__ == '__main__':
    sys.exit(main())
