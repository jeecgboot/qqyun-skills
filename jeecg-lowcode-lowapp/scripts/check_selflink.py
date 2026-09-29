#!/usr/bin/env python3
"""自关联控件三处属性自检（SKILL.md「建表收尾自检 ④」引用的脚本；以前文档引用了但文件不存在）。

自关联（关联记录的来源表 == 本表，如 任务.上级任务）要写**三处**（engine-contract C6，desform_utils.LINK_RECORD is_self）：
  ① 控件顶层 `isSelf: true`
  ② `options.isSelf: true` + `options.valueSplit: ""`
  ③ `advancedSetting.defaultValue.valueSplit: ""`
缺②时隐藏的「上级任务占位」会在列表里露成一列、父级回写/树展开认不到它。

用法：
  python check_selflink.py --api-base URL --token TOKEN --tenant-id 2 --app-id <id>          # 只检查
  python check_selflink.py ... --fix                                                         # 补齐并回读
退出码：有缺失且未 --fix → 1；否则 0。
"""
import argparse
import json
import os
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:                                     # noqa: BLE001
    pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from desform_lowapp_utils import init_lowapp, get_menus   # noqa: E402
from desform_utils import query_form, save_design_from_file   # noqa: E402
from design_utils import iter_widgets   # noqa: E402
from patch_fields import preserve_dicts   # noqa: E402


def problems(w, code):
    """返回该控件缺的项（空列表 = 齐全）；非自关联控件返回 None。"""
    o = w.get('options') or {}
    if w.get('type') != 'link-record' or not (w.get('isSelf') or o.get('isSelf') or o.get('sourceCode') == code):
        return None
    dv = ((w.get('advancedSetting') or {}).get('defaultValue') or {})
    miss = []
    if w.get('isSelf') is not True:
        miss.append('顶层 isSelf')
    if o.get('isSelf') is not True:
        miss.append('options.isSelf')
    if o.get('valueSplit') != '':
        miss.append('options.valueSplit')
    if 'valueSplit' in dv and dv.get('valueSplit') != '':
        miss.append('advancedSetting.defaultValue.valueSplit')
    return miss


def fix(w):
    w['isSelf'] = True
    w.setdefault('options', {})['isSelf'] = True
    w['options']['valueSplit'] = ''
    dv = (w.get('advancedSetting') or {}).get('defaultValue')
    if isinstance(dv, dict):
        dv['valueSplit'] = ''


def main():
    ap = argparse.ArgumentParser(description='自关联控件三处属性自检')
    ap.add_argument('--api-base', required=True)
    ap.add_argument('--token', required=True)
    ap.add_argument('--tenant-id', required=True)
    ap.add_argument('--app-id', required=True)
    ap.add_argument('--fix', action='store_true', help='补齐缺失的属性并回读')
    a = ap.parse_args()
    init_lowapp(a.api_base, a.token, tenant_id=int(a.tenant_id), app_id=a.app_id)
    forms = {}

    def walk(ms):
        for m in ms or []:
            if m.get('type') == 'form':
                forms[m['menuName']] = m['desformCode']
            walk(m.get('children'))
    walk((get_menus(a.app_id) or {}).get('menuList'))

    bad = 0
    still = 0          # --fix 后回读仍缺的（review #10：以前这种情况也退出 0）
    for name, code in forms.items():
        d = json.loads(query_form(code)['desformDesignJson'])
        hits = [(w, problems(w, code)) for w in iter_widgets(d.get('list') or [])]
        hits = [(w, m) for w, m in hits if m is not None]
        for w, miss in hits:
            print('%s  %s.%s  %s' % ('✗' if miss else '✓', name, w.get('name'), ('缺：' + '、'.join(miss)) if miss else '三处齐全'))
        broken = [w for w, m in hits if m]
        bad += len(broken)
        if broken and a.fix:
            for w in broken:
                fix(w)
            preserve_dicts(d)                      # 整单回存前字典控件 remote 复位
            p = os.path.join(tempfile.gettempdir(), 'selflink_%s.json' % code)
            with open(p, 'w', encoding='utf-8') as fh:
                json.dump(d, fh, ensure_ascii=False)
            save_design_from_file(code, p)
            os.remove(p)
            d2 = json.loads(query_form(code)['desformDesignJson'])
            left = [w.get('name') for w in iter_widgets(d2.get('list') or []) if problems(w, code)]
            print('   回读：%s' % ('OK' if not left else '仍缺 %s' % left))
            still += len(left)
    print('自关联控件缺项 %d 个%s' % (bad, '（已 --fix）' if bad and a.fix else ''))
    return 1 if (bad and not a.fix) or still else 0


if __name__ == '__main__':
    sys.exit(main())
