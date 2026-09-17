#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
扫描 references/desform-widget-options.md 的二级标题（## 章节 = 各控件），算出每个
章节的起始行号(offset)与行数(limit)；并从 references/desform-widget-types.md 合并
每个控件的「用户关键词」映射，输出一张「关键词 → 控件 → 配置位置」索引表到 stdout。

供 SKILL.md 动态注入使用（skill 加载时执行，输出替换占位符注入上下文）：

    <!-- WIDGET_OPTIONS_INDEX:START -->
    !`python ${CLAUDE_SKILL_DIR}/scripts/gen_widget_options_index.py`
    <!-- WIDGET_OPTIONS_INDEX:END -->

注入后这张表同时承担两件事，因此 widget-types.md 的关键词映射已完全进入 SKILL.md：
  ① 按用户描述匹配「关键词」选定控件（原 widget-types.md 的职责）
  ② 用其 offset/limit 直接 Read 读取该控件完整配置（widget-options.md 定位）

文档结构或关键词变化后**无需手动重跑**，每次加载都是最新。
本脚本只输出纯表格（无副作用、不写任何文件），保证注入内容干净。
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(SKILL_ROOT, 'references', 'desform-widget-options.md')
TYPES = os.path.join(SKILL_ROOT, 'references', 'desform-widget-types.md')
DOC_REL = 'references/desform-widget-options.md'

# 从章节标题（如 "select-user — 用户组件"）提取控件 type
_TYPE_RE = re.compile(r'^([a-z][a-z0-9\-]*)\s*[—\-]')
# 从 types.md 第二列（如 "`link-record` (isSubTable=true)"）提取 type
_TYPECELL_RE = re.compile(r'`([a-z][a-z0-9\-]*)`')


def parse_type_keywords():
    """解析 widget-types.md，返回 {type: 合并后的关键词字符串}。同一 type 多行用「；」连接。"""
    kw_map = {}
    for line in open(TYPES, encoding='utf-8').read().split('\n'):
        if line.startswith('|') and '`' in line:
            cells = [c.strip() for c in line.strip('|').split('|')]
            if len(cells) >= 2:
                m = _TYPECELL_RE.search(cells[1])
                if m:
                    kw_map.setdefault(m.group(1), []).append(cells[0])
    return {t: '；'.join(kws) for t, kws in kw_map.items()}


def build_index():
    """返回 [(title, type_or_None, offset, limit)]，type 仅控件章节有。"""
    lines = open(DOC, encoding='utf-8').read().split('\n')
    total = len(lines)
    heads = [(i, l[3:].strip()) for i, l in enumerate(lines, start=1) if l.startswith('## ')]
    rows = []
    for idx, (ln, title) in enumerate(heads):
        end_ln = heads[idx + 1][0] - 1 if idx + 1 < len(heads) else total
        m = _TYPE_RE.match(title)
        rows.append((title, m.group(1) if m else None, ln, end_ln - ln + 1))
    return rows


def render_table(rows, kw_map):
    out = [
        f'> 以下为 `{DOC_REL}` 各控件的「关键词 → 控件 → 配置位置」索引（skill 加载时自动生成，始终对应当前文档）。',
        '> 用法：① 按用户描述匹配「关键词」选定控件；'
        f'② 用其 offset/limit 直接 `Read("{DOC_REL}", offset, limit)` 读取该控件完整配置，无需 grep。',
        '',
        '| 控件 | 关键词 | offset | limit |',
        '|---|---|---|---|',
    ]
    for title, typ, ln, span in rows:
        kw = kw_map.get(typ, '') if typ else ''
        out.append(f'| {title} | {kw} | {ln} | {span} |')
    return '\n'.join(out)


def main():
    sys.stdout.write(render_table(build_index(), parse_type_keywords()) + '\n')


if __name__ == '__main__':
    main()
