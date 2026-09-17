# -*- coding: utf-8 -*-
"""
QQY 低代码应用仪表盘通用操作（禁止为单次需求 Write 一次性脚本）

  py qqy_ops.py tenants        API TOKEN --name 北京国炬信息技术有限公司
  py qqy_ops.py apps           API TOKEN --tenant-id 2 [--name 测试11]
  py qqy_ops.py forms          API TOKEN --tenant-id 2 --app-id APP|--app-name 仓储系统管理
  py qqy_ops.py fields         API TOKEN --tenant-id 2 --app-id APP|--app-name … --form-code CODE|--form-name 物料档案
  py qqy_ops.py menus          API TOKEN --tenant-id 2 --app-id APP|--app-name …
  py qqy_ops.py create-page    API TOKEN --app-id APP --tenant-id 2 --name 订单每日数量
  py qqy_ops.py add-charts     API TOKEN --app-id APP --tenant-id 2 --page-id PAGE --form-code CODE --form-name 订单表 --specs-file specs.json
  py qqy_ops.py add-charts     API TOKEN --tenant-id 2 --app-name 应用1 --page-name 测试 --form-app-name 应用2 --form-name 产品表 --specs-file specs.json
  py qqy_ops.py group-menu     API TOKEN --app-id APP --tenant-id 2 --page-id PAGE --group 数据分析
  py qqy_ops.py create-dashboard API TOKEN --tenant-name 北京国炬信息技术有限公司 --app-name 应用2 --form-name 产品表 --name 产品统计仪表盘 --group 数据分析 --specs-file specs.json
  py qqy_ops.py add-form-chart    API TOKEN --tenant-id 2 --app-name 应用2 --form-name 产品表 --type private --title 本月每日订单数量
  py qqy_ops.py add-buttons       API TOKEN --tenant-id 2 --app-name 应用1 --page-name 本月订单看板 --specs-file buttons.json
  py qqy_ops.py delete-form-chart API TOKEN --tenant-id 2 --app-name 应用1 --form-name 订单表 --type private --title 本月每日订单数量
  py qqy_ops.py move-form-chart   API TOKEN --tenant-id 2 --app-name 应用1 --form-name 订单表 --type public --to private --title 本月每日订单数量
  py qqy_ops.py copy-form-chart   API TOKEN --tenant-id 2 --app-name 应用1 --form-name 订单表 --type public --title 本月每日订单数量
  py qqy_ops.py add-filter        API TOKEN --tenant-id 2 --app-name 应用1 --page-name 测试 --specs-file filter.json
  py qqy_ops.py edit-filter       API TOKEN --tenant-id 2 --app-name APP --page-name PAGE --field 产品名称 --mode 等于 --value 测试
  py qqy_ops.py rename-page       API TOKEN --tenant-id 2 --app-name 应用1 --page-name 测试 --name 新名称
  py qqy_ops.py rebind-chart      API TOKEN --tenant-id 2 --app-name 应用1 --page-name 本月订单看板 --name 本月订单按日统计 --dim 名称 --val 记录数 --query-range all
  py qqy_ops.py rebind-chart      API TOKEN --tenant-id 1008 --app-name 应用1 --page-name 本月产品门户 --name 产品信息 --form-app-name 仓储系统管理 --form-name 物料档案 --dim 物料名称 --val 安全库存 --query-range all
  py qqy_ops.py rebind-chart      API TOKEN --tenant-id 1008 --app-name 应用1 --page-name 本月产品门户 --comp DoubleLineBar --assist-y 单价 --assist-type 名称
  py qqy_ops.py set-chart-calc    API TOKEN --tenant-id 2 --app-name 应用1 --page-name 本月订单看板 --comp JBar --formula 求和×求和
  py qqy_ops.py set-chart-calc    API TOKEN --tenant-id 2 --app-name 仓储系统管理 --page-name 仓储运营分析看板 --name 各仓库库存柱 --formula 求和 --title 各仓库库存合计
  py qqy_ops.py rename-chart      API TOKEN --tenant-id 2 --app-name 仓储系统管理 --page-name 仓储运营分析看板 --name 各仓库库存柱 --title 各仓库库存合计
  py qqy_ops.py set-chart-color   API TOKEN --tenant-id 2 --app-name 应用1 --page-name 本月订单看板 --comp JBar --color "#FFD700"
  py qqy_ops.py set-chart-color   API TOKEN --tenant-id 2 --app-name 应用1 --page-name 本月订单看板 --name 物料库存排行 --comp JBar --colors "#64b5f6,#1890FF" --gradient
  py qqy_ops.py set-chart-color   API TOKEN --tenant-id 2 --app-name 应用1 --page-name 本月订单看板 --name 本月每日入库量折线 --comp JLine --color 红色 --line-type 曲线
  py qqy_ops.py set-chart-color   API TOKEN --tenant-id 2 --app-name 应用1 --page-name 仓储运营分析看板 --name 入库单状态饼 --colors 紫,绿,黄色 --label-show
  py qqy_ops.py set-chart-sort    API TOKEN --tenant-id 2 --app-name 仓储系统管理 --page-name 仓储运营分析看板 --name 物料库存排行 --top-n 8 --field 库存数量 --order desc
  py qqy_ops.py set-chart-compare API TOKEN --tenant-id 2 --app-name APP --page-name PAGE --name CHART --compare 上月 --trend 升红降绿
  py qqy_ops.py add-charts        API TOKEN --tenant-id 2 --app-name 应用1 --page-name PAGE --form-name 订单表 --comp JBar --title 各产品销售额 --dim 产品名称 --val 销售额
  py qqy_ops.py create-dashboard  API TOKEN --tenant-id 2 --app-name 应用1 --form-name 订单表 --name 本月订单看板 --layout-file layout.json
  py qqy_ops.py add-ui            API TOKEN --tenant-id 2 --app-name 应用1 --page-name PAGE --comp JText --text "XX公司经营驾驶舱" --bold --w 24
  py qqy_ops.py set-chart-refresh API TOKEN --tenant-id 2 --app-name APP --page-name PAGE --name CHART --minutes 5
  py qqy_ops.py set-pivot         API TOKEN --tenant-id 2 --app-name APP --page-name PAGE --name CHART --row-n 10 --col-n 5 --line-total 关 --column-total 关
"""
import argparse, json, os, re, sys, time, copy, uuid

_HERE = os.path.dirname(os.path.abspath(__file__))
_REFS = os.path.dirname(_HERE)
for d in (_HERE, _REFS):
    if d not in sys.path:
        sys.path.insert(0, d)

import bi_utils
import qqy_chart as qc

if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


def _init(args):
    extra = {'X-Tenant-Id': str(args.tenant_id)}
    app_id = getattr(args, 'app_id', None)
    if app_id:
        extra['X-Low-App-ID'] = app_id
    bi_utils.init_api(args.api_base, args.token, extra_headers=extra)


def _parse_json_maybe(raw, default=None):
    if raw is None or raw == '':
        return {} if default is None else default
    if isinstance(raw, (dict, list)):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return {} if default is None else default
    return {} if default is None else default


def _agg_kind(rel):
    rel = _parse_json_maybe(rel, {})
    ft = (rel.get('formType') or 'multi') if isinstance(rel, dict) else 'multi'
    if ft == 'aggregation':
        return 'factory', '[聚合工厂]'
    if ft == 'single':
        return 'single', '[聚合]'
    return 'multi', '[聚合]'


def _list_agg_records(app_id, page_size=50):
    resp = bi_utils._request('GET', '/drag/onlDragTableRelation/list',
                             params={'pageSize': page_size, 'pageNo': 1})
    records = ((resp.get('result') or {}).get('records')) or []
    out = []
    for r in records:
        low = r.get('lowAppId') or r.get('appId') or ''
        if app_id and low and str(low) != str(app_id):
            continue
        kind, tag = _agg_kind(r.get('relationForms'))
        name = (r.get('aggregationName') or r.get('name') or r.get('id') or '').strip()
        out.append({
            'id': str(r.get('id') or ''),
            'name': name,
            'label': '%s %s' % (tag, name),
            'kind': kind,
            'raw': r,
        })
    return out


def _find_agg_record(app_id, form_code, form_name):
    recs = _list_agg_records(app_id)
    code = (form_code or '').strip()
    keyword = (form_name or '').strip()
    if code:
        for r in recs:
            if r['id'] == code:
                return r
    if not keyword:
        return None
    kw = keyword.replace('[聚合工厂]', '').replace('[聚合]', '').strip()
    exact = []
    matched = []
    for r in recs:
        names = {r['name'], r['label'], r['id']}
        if keyword in names or kw == r['name']:
            exact.append(r)
        elif kw and (kw in r['name'] or r['name'] in kw):
            matched.append(r)
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return None
    if len(matched) == 1:
        return matched[0]
    return None


# 口径=售价×销量（非「售价/单价」单字段）。无 calc 时自动补 $money-4$*$qty-1$
_SALES_REVENUE_TOKENS = frozenset({
    '销售额', '销售金额', '营收', '收入', '总销售额', 'sales',
})


def _rect_overlap(x, y, w, h, ox, oy, ow, oh):
    return x < ox + ow and x + w > ox and y < oy + oh and y + h > oy


def _pack_grid_y(tmpl, x, w, h):
    """未写 y 时按 24 列栅格装箱：优先与已有组件同行（x 不重叠），否则落到更低空位。
    旧逻辑对每个未写 y 的项做 max(y+h) 串行堆叠 → 同行 KPI/半行图全部错位。"""
    occupied = []
    for it in tmpl:
        occupied.append((
            int(it.get('x') or 0), int(it.get('y') or 0),
            int(it.get('w') or 0), int(it.get('h') or 0),
        ))
    candidates = {0}
    for ox, oy, ow, oh in occupied:
        candidates.add(oy)
        candidates.add(oy + oh)
    for cy in sorted(candidates):
        if any(_rect_overlap(x, cy, w, h, ox, oy, ow, oh)
               for ox, oy, ow, oh in occupied):
            continue
        return cy
    if not occupied:
        return 0
    return max(oy + oh for _, oy, _, oh in occupied)


def _auto_sales_calc(val_tok, title, fields):
    """val/title 口径为「销售额」且表单同时有 money+数量字段时，返回售价平均×销量求和公式。"""
    keys = []
    for t in (val_tok, title):
        if isinstance(t, str) and t.strip():
            keys.append(t.strip())
    want = False
    for k in keys:
        if k in _SALES_REVENUE_TOKENS or ('销售' in k and '额' in k):
            want = True
            break
    if not want:
        return None
    return _sales_money_qty_formula(fields)


def _sales_money_qty_formula(fields):
    """售价(money)平均 × 销量(number)求和。字段不足返回 None。"""
    money = [f for f in fields
             if f.get('widgetType') == 'money' and f.get('fieldName')]
    nums = [f for f in fields
            if f.get('fieldType') == 'number' and f.get('fieldName')
            and f.get('widgetType') != 'money']
    if not money or not nums:
        return None
    return '$%s-4$*$%s-1$' % (money[0]['fieldName'], nums[0]['fieldName'])


def _normalize_calc_formula(formula, fields, val_tok=None, title=None):
    """把文档占位符 / 不存在的 model 展开为真实字段公式。

    金标/文档常写 `$money_xxx-4$*$number_yyy-1$`，若原样入库则 UI 计算值配置错误。
    规则：含 `_xxx`/`_yyy` 等示意 token，或 `$model-N$` 引用的 model 不在表单字段中
    → 用售价×销量真实公式替换（能生成时）；否则原样返回并告警。
    """
    formula = str(formula).strip()
    if not formula.startswith('$'):
        return formula
    models = re.findall(r'\$([^-$\s]+)-\d+\$', formula)
    field_names = {f.get('fieldName') for f in fields if f.get('fieldName')}
    placeholder = bool(re.search(r'_(xxx|yyy|zzz)\b', formula, re.I))
    missing = [m for m in models if m not in field_names]
    if not placeholder and not missing:
        return formula
    auto = _sales_money_qty_formula(fields)
    if not auto:
        auto = _auto_sales_calc(val_tok, title, fields)
    if auto:
        print('NOTE=calc 占位/无效 model 已展开: %s -> %s' % (formula, auto))
        return auto
    print('WARN=calc 含占位或未知 model 且无法自动展开: %s missing=%s'
          % (formula, missing))
    return formula


def _app_name_match(keyword, name):
    """应用测试11 能匹配 测试11；禁止因前缀差异判定找不到。"""
    if not keyword:
        return True
    if keyword in name or name in keyword:
        return True
    for prefix in ('应用', '低代码应用', 'QQY应用', '敲敲云'):
        rest_k = keyword[len(prefix):] if keyword.startswith(prefix) else keyword
        rest_n = name[len(prefix):] if name.startswith(prefix) else name
        if rest_k and (rest_k in name or rest_k in rest_n or rest_n in rest_k):
            return True
    return False


def _form_keyword_match(keyword, label, val=''):
    """产品统计 能匹配 产品表；禁止因「统计/仪表盘」后缀判定找不到。

    ⚠️ 禁止 label in keyword：会让「入库单」误匹配「入库明细」（子串反向包含）。
    ⚠️ 禁止剥「明细」后缀：入库明细→入库 后同时命中入库单/入库明细 → FORM_AMBIGUOUS。
    """
    if not keyword:
        return False
    if keyword == label or keyword == val:
        return True
    if keyword in label:
        return True
    rest = keyword
    for suffix in ('统计仪表盘', '仪表盘', '统计看板', '看板', '统计分析', '分析', '统计'):
        if rest.endswith(suffix) and len(rest) > len(suffix):
            rest = rest[:-len(suffix)]
            break
    if rest == keyword:
        return False
    return bool(rest) and (rest == label or rest in label or rest == (val or '') or rest in (val or ''))


def _print_json_line(obj):
    print(json.dumps(obj, ensure_ascii=False))


# ── apps ──────────────────────────────────────────────────────────────────
def cmd_apps(args):
    _init(args)
    resp = bi_utils._request('GET', '/online/lowApp/queryList',
                             params={'tenantId': str(args.tenant_id)})
    apps = ((resp.get('result') or {}).get('appList')) or []
    keyword = (args.name or '').strip()
    matched = []
    print('id\tappName\ttenantId')
    for a in apps:
        name = a.get('appName') or ''
        line = '%s\t%s\t%s' % (a.get('id'), name, a.get('tenantId'))
        if keyword and not _app_name_match(keyword, name):
            continue
        print(line)
        matched.append(a)
    if keyword:
        print('MATCH_COUNT=%d' % len(matched))
        if len(matched) == 1:
            print('APP_ID=%s' % matched[0].get('id'))
        elif not matched:
            print('APP_NOT_FOUND keyword=%s 全部应用见上方未过滤列表：' % keyword)
            for a in apps:
                print('%s\t%s' % (a.get('id'), a.get('appName')))


# ── forms ─────────────────────────────────────────────────────────────────
def _list_design_forms(app_id):
    """合并 list/options + 侧栏菜单 type=form。

    仅用 `/desform/api/list/options?appId=` 会漏表：若 desform.lowAppId 被写成
    非当前应用雪花 ID（历史脏数据常见），options 不含该表，但 lowAppMenu 仍挂着。
    点名表单存在性以菜单为准；返回项形如 {value:code, label:name, source:options|menu}。
    """
    forms_resp = bi_utils._request('GET', '/desform/api/list/options',
                                   params={'appId': app_id})
    by_code = {}
    for f in (forms_resp.get('result') or []):
        code = (f.get('value') or '').strip()
        if not code:
            continue
        by_code[code] = {
            'value': code,
            'label': f.get('label') or f.get('title') or code,
            'source': 'options',
        }
    for m in _list_menus(app_id):
        if (m.get('type') or '') != 'form':
            continue
        code = (m.get('desformCode') or '').strip()
        if not code:
            continue
        name = m.get('menuName') or code
        if code not in by_code:
            by_code[code] = {'value': code, 'label': name, 'source': 'menu'}
            print('NOTE=forms 菜单兜底补入 code=%s name=%s（list/options 未返回，常见于 desform.lowAppId 与应用 ID 不一致）' % (code, name))
        elif not by_code[code].get('label'):
            by_code[code]['label'] = name
    return list(by_code.values())


def cmd_forms(args):
    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    forms = _list_design_forms(app_id)
    print('【表单（普通）】')
    print('formCode\t表单名称\ttype\tsource')
    for f in forms:
        print('%s\t%s\tdesign\t%s' % (
            f.get('value'), f.get('label') or f.get('title') or '', f.get('source') or 'options'))
    print('FORM_COUNT=%d' % len(forms))

    print('【聚合表】')
    print('id\t聚合表名称\tkind\ttype')
    agg_n = 0
    for r in _list_agg_records(app_id):
        print('%s\t%s\t%s\taggregation' % (r['id'], r['label'], r['kind']))
        agg_n += 1
    print('AGG_COUNT=%d' % agg_n)


# ── fields ────────────────────────────────────────────────────────────────
def _load_fields(args):
    form_type = getattr(args, 'form_type', None) or 'design'
    if form_type == 'aggregation':
        resp = bi_utils._request('GET', '/drag/onlDragTableRelation/getFields/%s' % args.form_code)
        raw = resp.get('result') or []
        if isinstance(raw, dict):
            raw = raw.get('fields') or []
        fields = qc.parse_aggregation_fields(raw)
        tagged = getattr(args, 'form_name', None)
        if not tagged:
            rec = _find_agg_record(getattr(args, 'app_id', None), args.form_code, '')
            tagged = rec['label'] if rec else ('[聚合] %s' % args.form_code)
        return fields, tagged, 'aggregation'
    resp = bi_utils._request('GET', '/desform/api/fields/%s' % args.form_code,
                             params={'subTable': True})
    result = resp.get('result') or {}
    raw = result.get('fields') or []
    fields = qc.parse_design_fields(raw)
    form_name = getattr(args, 'form_name', None) or result.get('desformName') or args.form_code
    return fields, form_name, 'design'


def cmd_fields(args):
    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    code = (getattr(args, 'form_code', None) or '').strip()
    fname = (getattr(args, 'form_name', None) or '').strip()
    if not code:
        code, resolved_name = _resolve_form(
            app_id, '', fname, prefer_type=getattr(args, 'form_type', None))
        args.form_code = code
        if not fname:
            args.form_name = resolved_name
        if getattr(_resolve_form, 'last_type', '') == 'aggregation':
            args.form_type = 'aggregation'
    fields, form_name, form_type = _load_fields(args)
    print('FORM_CODE=%s' % args.form_code)
    print('FORM_NAME=%s' % form_name)
    print('FORM_TYPE=%s' % form_type)
    print('序号\t字段名\t显示名\t控件类型\tfieldType')
    for i, f in enumerate(fields, 1):
        print('%d\t%s\t%s\t%s\t%s' % (
            i, f['fieldName'], f['fieldTxt'], f.get('widgetType'), f['fieldType']))
    dim, val, grp, date_fields = qc.recommend_fields(fields)
    print('推荐维度=%s(%s)' % (
        (dim or {}).get('fieldName', 'create_time'),
        (dim or {}).get('fieldTxt', '创建时间')))
    print('推荐数值=%s(%s)' % (val.get('fieldName'), val.get('fieldTxt')))
    if grp:
        print('推荐分组=%s(%s)' % (grp.get('fieldName'), grp.get('fieldTxt')))
    if date_fields:
        print('日期字段=%s' % ','.join('%s(%s)' % (d['fieldName'], d['fieldTxt']) for d in date_fields))
    else:
        print('日期字段=无（按日统计请用 dim=create_time dateGroup=3）')
    print('DATE_GROUP 1=年 6=年月 2=月 7=月简 3=日 4=时 5=分')


# ── menus ─────────────────────────────────────────────────────────────────
def _list_menus(app_id):
    resp = bi_utils._request('GET', '/online/lowAppMenu/list',
                             params={'appId': app_id, 'pageSize': 100})
    records = ((resp.get('result') or {}).get('records')) or []
    return [m for m in records if str(m.get('appId') or '') == str(app_id)]


def cmd_menus(args):
    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    menus = _list_menus(app_id)
    print('id\ttype\tmenuName\tparentId\tmenuUrl')
    for m in menus:
        print('%s\t%s\t%s\t%s\t%s' % (
            m.get('id'), m.get('type'), m.get('menuName'),
            m.get('parentId'), m.get('menuUrl')))


# ── create-page ───────────────────────────────────────────────────────────
def cmd_create_page(args):
    _init(args)
    t0 = time.time()
    page_id = bi_utils.create_page(
        args.name, style='default', theme='default',
        low_app_id=args.app_id,
    )
    print('PAGE_ID=%s' % page_id)
    print('PAGE_NAME=%s' % args.name)
    # 建页后自动归组：--group 空 → 应用第一个已有分组（2026-09-02 修复：此前未归组导致侧边栏看不到）
    _group_page_into(args.app_id, page_id, getattr(args, 'group', '') or '')
    print('耗时: %.1fs' % (time.time() - t0))
    return page_id


def _read_json_text(path):
    """读 specs 文件；utf-8-sig 容忍 PowerShell Set-Content -Encoding UTF8 的 BOM。"""
    with open(path, encoding='utf-8-sig') as f:
        return f.read()


_COLOR_ALIASES = {
    'yellow': '#FFD700', 'gold': '#FFD700', '黄': '#FFD700', '黄色': '#FFD700', '金色': '#FFD700',
    'red': '#FF4D4F', '红': '#FF4D4F', '红色': '#FF4D4F',
    'blue': '#1890FF', '蓝': '#1890FF', '蓝色': '#1890FF',
    'green': '#52C41A', '绿': '#52C41A', '绿色': '#52C41A',
    'orange': '#FA8C16', '橙': '#FA8C16', '橙色': '#FA8C16',
    'purple': '#722ED1', '紫': '#722ED1', '紫色': '#722ED1',
}

# 样式面板「折线类型」：曲线/折线/面积。口语「改成曲线」≠ switch-type JSmoothLine。
_LINE_TYPE_ALIASES = {
    '曲线': 'smooth', 'smooth': 'smooth', 'curve': 'smooth', '平滑': 'smooth',
    '折线': 'line', 'line': 'line', '直线': 'line',
    '面积': 'area', 'area': 'area',
}


def _normalize_line_type(raw):
    s = str(raw or '').strip()
    if not s:
        return None
    hit = _LINE_TYPE_ALIASES.get(s) or _LINE_TYPE_ALIASES.get(s.lower())
    if hit:
        return hit
    if '面积' in s:
        return 'area'
    if '曲线' in s or '平滑' in s:
        return 'smooth'
    if '折线' in s or '直线' in s:
        return 'line'
    return None


def _apply_line_type(s0, line_type):
    """写入 series[0].lineType；曲线同时 smooth=true（否则面板是曲线、渲染仍折）。"""
    mapped = _normalize_line_type(line_type)
    if mapped:
        s0['lineType'] = mapped
        s0['smooth'] = (mapped == 'smooth')
        return mapped
    if line_type not in (None, ''):
        s0['lineType'] = line_type
    return None


def _normalize_color(token):
    """hex / 中英文色名 → #RRGGBB；无法识别返回 None。"""
    if token is None:
        return None
    if isinstance(token, dict):
        c = token.get('color') or token.get('color1') or token.get('value')
        return _normalize_color(c)
    s = str(token).strip()
    if not s:
        return None
    low = s.lower()
    if low in _COLOR_ALIASES:
        return _COLOR_ALIASES[low]
    if s in _COLOR_ALIASES:
        return _COLOR_ALIASES[s]
    if re.match(r'^#[0-9A-Fa-f]{6}$', s):
        return '#' + s[1:]
    if re.match(r'^[0-9A-Fa-f]{6}$', s):
        return '#' + s
    return None


# 柱体实心色：CompStyleConfig「柱体颜色」= series[0].itemStyle.color
# customColor 仅当 showLinearGradient=true（bar.vue linearGradient）
_ITEMSTYLE_COLOR_TYPES = {
    'JBar', 'JHorizontalBar', 'JRankingList', 'JGauge', 'JScatter',
}
# 折线/面积：设计弹窗写 itemStyle.color；画布「自定义配色」写 customColor；
# line.vue / area.vue 运行时 customColor[0] 优先，否则 itemStyle
_LINE_COLOR_TYPES = {'JLine', 'JArea'}
# 多系列/扇区：getCustomColor(option.customColor)
_CUSTOM_COLOR_TYPES = {
    'JPie', 'JRing', 'JRose', 'JFunnel', 'JPyramidFunnel',
    'JMultipleLine', 'JMultipleBar', 'JStackBar', 'JNegativeBar',
    'DoubleLineBar', 'JBubble', 'JRadar', 'JCircleRadar', 'JWordCloud',
}


def _split_colors(raw):
    """配色口语：黄,绿,蓝 / 黄绿蓝 / 黄色绿色蓝色。"""
    if raw is None or raw == '':
        return []
    if isinstance(raw, (list, tuple)):
        out = []
        for x in raw:
            out.extend(_split_colors(x))
        return out
    s = str(raw).strip()
    if not s:
        return []
    if s.startswith('['):
        try:
            arr = json.loads(s)
            if isinstance(arr, list):
                return _split_colors(arr)
        except Exception:
            pass
    parts = [p.strip() for p in re.split(r'[,，、/|+\s]+', s) if p.strip()]
    if len(parts) > 1:
        return parts
    s0 = parts[0] if parts else s
    if _normalize_color(s0):
        return [s0]
    keys = sorted(_COLOR_ALIASES.keys(), key=len, reverse=True)
    out = []
    i = 0
    while i < len(s0):
        hit = None
        for k in keys:
            if s0.startswith(k, i):
                hit = k
                break
        if hit:
            out.append(hit)
            i += len(hit)
        else:
            i += 1
    return out or [s0]


def _parse_spec_hexes(raw, spec_index=0):
    if raw is None or raw == '':
        return []
    if isinstance(raw, str):
        raw = _split_colors(raw)
    if not isinstance(raw, (list, tuple)) or not raw:
        print('NOTE=specs[%d] colors 无法解析，已忽略' % spec_index)
        return []
    hexes = []
    for item in raw:
        c = _normalize_color(item)
        if c:
            hexes.append(c)
        else:
            print('NOTE=specs[%d] 未知颜色「%s」，已跳过' % (spec_index, item))
    if not hexes:
        print('NOTE=specs[%d] colors 无有效色值，已忽略' % spec_index)
    return hexes


def _ensure_series0(opt, default_type='bar'):
    series = opt.get('series')
    if not isinstance(series, list) or not series or not isinstance(series[0], dict):
        series = [{'type': default_type}]
        opt['series'] = series
    return series


def _apply_spec_colors(cfg, spec, spec_index=0):
    """按组件运行时读色路径写入（对照 CompStyleConfig / *.vue）。

    JBar/JHorizontalBar：只认 series[0].itemStyle.color；渐变才写 customColor。
    JLine/JArea：itemStyle.color + customColor[0] 同步（运行时 customColor 优先）。
    饼/环/多系列：只写 customColor（getCustomColor）。
    JColorGauge：axisLine.lineStyle.color 分段。
    地图：visualMap.inRange + commonOption.inRange，禁止扩 series。
    """
    raw = spec.get('colors') or spec.get('color') or spec.get('customColor')
    hexes = _parse_spec_hexes(raw, spec_index)
    if not hexes:
        return
    opt = cfg.setdefault('option', {})
    subclass = ((cfg.get('chart') or {}).get('subclass') or '').strip()
    want_gradient = _truthy_flag(
        spec.get('showLinearGradient') if 'showLinearGradient' in spec
        else spec.get('gradient') if 'gradient' in spec
        else spec.get('linearGradient'))
    custom = [{'color': c, 'color1': c} for c in hexes]

    if subclass in ('JColorGauge', 'JGauge'):
        series = _ensure_series0(opt, 'gauge')
        s0 = series[0]
        s0['type'] = s0.get('type') or 'gauge'
        if subclass == 'JColorGauge':
            n = len(hexes)
            axis_colors = [[round((i + 1) / n, 4), hexes[i]] for i in range(n)]
            axis_line = s0.setdefault('axisLine', {})
            if not isinstance(axis_line, dict):
                axis_line = {}
                s0['axisLine'] = axis_line
            line_style = axis_line.setdefault('lineStyle', {})
            if not isinstance(line_style, dict):
                line_style = {}
                axis_line['lineStyle'] = line_style
            line_style['color'] = axis_colors
            line_style.setdefault('width', 10)
            opt['series'] = [s0]
            print('COLORS=%s AXIS_LINE=%s' % (','.join(hexes), axis_colors))
            return
        # JGauge：样式面板「基础颜色」= series[0].itemStyle.color
        ist = s0.setdefault('itemStyle', {})
        if isinstance(ist, dict):
            ist['color'] = hexes[0]
        print('COLORS=%s GAUGE_ITEMSTYLE=%s' % (','.join(hexes), hexes[0]))
        return

    if subclass in ('JHeatMap', 'JAreaMap', 'JBubbleMap', 'JBarMap'):
        opt['customColor'] = custom
        vm = opt.setdefault('visualMap', {})
        if not isinstance(vm, dict):
            vm = {}
            opt['visualMap'] = vm
        vm['inRange'] = {'color': list(hexes)}
        co = cfg.setdefault('commonOption', {})
        if not isinstance(co, dict):
            co = {}
            cfg['commonOption'] = co
        co['inRange'] = {'color': list(hexes)}
        if subclass == 'JHeatMap':
            heat = co.setdefault('heat', {})
            if not isinstance(heat, dict):
                heat = {}
                co['heat'] = heat
            heat.setdefault('blurSize', 20)
            heat.setdefault('pointSize', 15)
            heat.setdefault('maxOpacity', 1)
            area = opt.setdefault('area', {})
            if isinstance(area, dict):
                area['markerColor'] = hexes[-1]
                area['shadowColor'] = hexes[0]
        print('COLORS=%s MAP_INRANGE=%s' % (','.join(hexes), hexes))
        return

    if subclass in _ITEMSTYLE_COLOR_TYPES or (subclass in ('JBar', 'JHorizontalBar') and want_gradient):
        series = _ensure_series0(opt, 'bar' if 'Bar' in subclass or subclass == 'JRankingList' else 'scatter')
        s0 = series[0]
        ist = s0.setdefault('itemStyle', {})
        if not isinstance(ist, dict):
            ist = {}
            s0['itemStyle'] = ist
        if want_gradient and subclass in ('JBar', 'JHorizontalBar'):
            ist['showLinearGradient'] = True
            # 柱体渐变色列表：每色一条 customColor（UI「+ 新增」），禁止把第二色塞进 color1
            opt['customColor'] = custom
            print('COLORS=%s BAR_GRADIENT=1' % ','.join(hexes))
        else:
            ist['color'] = hexes[0]
            ist['showLinearGradient'] = False
            # 实心柱不写 customColor，避免和「柱体颜色」两条路径打架
            print('COLORS=%s ITEMSTYLE=%s' % (','.join(hexes), hexes[0]))
        opt['series'] = series
        return

    if subclass in _LINE_COLOR_TYPES:
        series = _ensure_series0(opt, 'line')
        s0 = series[0]
        ist = s0.setdefault('itemStyle', {})
        if not isinstance(ist, dict):
            ist = {}
            s0['itemStyle'] = ist
        ist['color'] = hexes[0]
        opt['customColor'] = custom
        opt['series'] = series
        print('COLORS=%s LINE_ITEMSTYLE+CUSTOM=%s' % (','.join(hexes), hexes[0]))
        return

    # 饼/环/多系列/雷达/气泡：只写 customColor（运行时 getCustomColor）
    opt['customColor'] = custom
    print('COLORS=%s CUSTOM_COLOR=%d' % (','.join(hexes), len(hexes)))


def _deep_merge_option(dst, src):
    if not isinstance(src, dict) or not isinstance(dst, dict):
        return
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge_option(dst[k], v)
        else:
            dst[k] = copy.deepcopy(v)


def _iter_chart_bind_fields(cfg):
    for key in ('valueFields', 'calcFields', 'nameFields', 'assistYFields', 'typeFields'):
        vals = cfg.get(key) or []
        if isinstance(vals, list):
            for f in vals:
                if isinstance(f, dict) and (f.get('fieldName') or f.get('fieldTxt')):
                    yield f


def _match_chart_bind_field(cfg, keyword):
    """从图已绑维/值解析排序字段（中文名或 model）；不拉全表 fields。"""
    kw = (keyword or '').strip()
    if not kw:
        return None
    exact, fuzzy = [], []
    for f in _iter_chart_bind_fields(cfg):
        fn = f.get('fieldName') or ''
        ft = f.get('fieldTxt') or ''
        if kw in (fn, ft):
            exact.append(f)
        elif kw in fn or kw in ft:
            fuzzy.append(f)
    if exact:
        return exact[0]
    if fuzzy:
        return fuzzy[0]
    return None


def _norm_sort_order(raw):
    s = (raw or '').strip()
    if not s:
        return ''
    low = s.lower()
    if '降' in s or low in ('desc', 'reverse') or low.endswith('desc'):
        return 'desc'
    if '升' in s or low in ('asc',) or low.endswith('asc'):
        return 'asc'
    return ''


def _parse_top_n(raw):
    if raw is None or raw == '':
        return None
    m = re.search(r'(\d+)', str(raw).strip())
    if not m:
        return None
    n = int(m.group(1))
    return n if n > 0 else None


def _parse_sorts_spec(cfg, sorts):
    """sorts → {name: fieldName, type: desc|asc}。name 尽量落成图上已绑 model。"""
    name, order = '', ''
    if isinstance(sorts, dict):
        name = str(sorts.get('name') or '')
        order = _norm_sort_order(sorts.get('type') or sorts.get('order') or '')
    else:
        s = str(sorts).strip()
        order = _norm_sort_order(s)
        name = re.sub(r'(_desc|_asc|降序|升序|desc|asc)$', '', s, flags=re.I).strip('_')
    hit = _match_chart_bind_field(cfg, name) if name else None
    if hit:
        name = hit.get('fieldName') or name
    return {'name': name, 'type': order}


def _apply_spec_style(cfg, spec, spec_index=0):
    """手工样式面板常见项首轮写入（对照 getSimpleOptionConfig）。"""
    opt = cfg.setdefault('option', {})
    notes = []
    dfn = spec.get('dataFilterNum')
    if dfn in (None, '') and spec.get('topN') not in (None, ''):
        dfn = spec.get('topN')
    top_n = _parse_top_n(dfn) if dfn not in (None, '') else None
    if top_n is not None:
        cfg['dataFilterNum'] = top_n
        notes.append('dataFilterNum=%s' % top_n)
    elif dfn not in (None, ''):
        cfg['dataFilterNum'] = dfn
        notes.append('dataFilterNum=%s' % dfn)
    sorts = spec.get('sorts') or spec.get('sort')
    if sorts:
        cfg['sorts'] = _parse_sorts_spec(cfg, sorts)
        notes.append('sorts=%s' % cfg['sorts'])
    series = opt.get('series')
    s0 = series[0] if isinstance(series, list) and series and isinstance(series[0], dict) else None
    if s0 is not None:
        if spec.get('barWidth') not in (None, ''):
            s0['barWidth'] = spec.get('barWidth')
            notes.append('barWidth=%s' % spec.get('barWidth'))
        if spec.get('borderRadius') not in (None, ''):
            ist = s0.setdefault('itemStyle', {})
            if isinstance(ist, dict):
                ist['borderRadius'] = spec.get('borderRadius')
            notes.append('borderRadius=%s' % spec.get('borderRadius'))
        line_type = spec.get('lineType') or spec.get('line_type')
        if line_type:
            mapped = _apply_line_type(s0, line_type)
            notes.append('lineType=%s' % (mapped or line_type))
        if spec.get('lineWidth') not in (None, ''):
            s0['lineWidth'] = spec.get('lineWidth')
            notes.append('lineWidth=%s' % spec.get('lineWidth'))
        if spec.get('symbol'):
            s0['symbol'] = spec.get('symbol')
        if spec.get('symbolSize') not in (None, ''):
            raw_ss = spec.get('symbolSize')
            try:
                s0['symbolSize'] = int(raw_ss)
            except (TypeError, ValueError):
                s0['symbolSize'] = raw_ss
            notes.append('symbolSize=%s' % s0['symbolSize'])
            print('SIZE_SET=symbolSize=%s' % s0['symbolSize'])
        label_raw = spec.get('labelShow') if 'labelShow' in spec else spec.get('showValue')
        if label_raw is not None:
            lab = s0.setdefault('label', {})
            if not isinstance(lab, dict):
                lab = {}
                s0['label'] = lab
            lab['show'] = _truthy_flag(label_raw)
            notes.append('label.show=%s' % lab['show'])
    legend_raw = spec.get('legendShow') if 'legendShow' in spec else (
        spec.get('legend') if not isinstance(spec.get('legend'), dict) else None)
    if legend_raw is not None:
        lg = opt.setdefault('legend', {})
        if not isinstance(lg, dict):
            lg = {}
            opt['legend'] = lg
        lg['show'] = _truthy_flag(legend_raw)
        notes.append('legend.show=%s' % lg['show'])
    extra = spec.get('option')
    if isinstance(extra, dict):
        _deep_merge_option(opt, extra)
        notes.append('option_overlay=%d' % len(extra))
    if notes:
        print('STYLE=specs[%d] %s' % (spec_index, ';'.join(notes)))


def _truthy_flag(raw):
    if raw is True or raw == 1:
        return True
    if raw is False or raw is None or raw == '' or raw == 0:
        return False
    if isinstance(raw, str):
        s = raw.strip().lower()
        if s in ('0', 'false', 'no', 'off', '否', '关', '关闭'):
            return False
        if s in ('1', 'true', 'yes', 'on', '是', '开', '开启', '百分比', 'percent', '百分比标签'):
            return True
        return bool(s)
    return bool(raw)


def _apply_spec_percent_label(cfg, spec, spec_index=0):
    """specs.percentLabel → series[0].label 百分比（首轮写入，禁止事后再 patch）。"""
    raw = (spec.get('percentLabel') if 'percentLabel' in spec
           else spec.get('labelPercent') if 'labelPercent' in spec
           else spec.get('showPercent'))
    if not _truthy_flag(raw):
        return
    opt = cfg.setdefault('option', {})
    series = opt.get('series')
    if not isinstance(series, list) or not series:
        series = [{'type': 'pie', 'data': []}]
    s0 = series[0] if isinstance(series[0], dict) else {'type': 'pie', 'data': []}
    s0['type'] = s0.get('type') or 'pie'
    s0['label'] = {'show': True, 'formatter': '{b}\n{d}%'}
    s0['labelLine'] = {'show': True}
    series[0] = s0
    opt['series'] = series
    print('PERCENT_LABEL=1 specs[%d]' % spec_index)


_PIE_LIKE_SUBCLASS = {
    'JPie', 'JRing', 'JRose', 'JFunnel', 'JPyramidFunnel',
}


def _apply_chart_label(cfg, kind, spec_index=0):
    """已有图数值/百分比标签。kind=value|percent。禁手写 py / 二次 save。"""
    kind = (kind or '').strip().lower()
    if kind in ('percent', '百分比', 'percentlabel', '%'):
        _apply_spec_percent_label(cfg, {'percentLabel': True}, spec_index)
        return 'percent'
    if kind not in ('value', '数值', 'label', 'show', '1', 'true', '数值标签'):
        return None
    subclass = ((cfg.get('chart') or {}).get('subclass') or '').strip()
    if subclass in _PIE_LIKE_SUBCLASS:
        opt = cfg.setdefault('option', {})
        series = _ensure_series0(opt, 'pie')
        s0 = series[0]
        s0['type'] = s0.get('type') or 'pie'
        s0['label'] = {'show': True, 'formatter': '{b}\n{c}'}
        s0['labelLine'] = {'show': True}
        opt['series'] = series
        print('VALUE_LABEL=1 specs[%d]' % spec_index)
        return 'value'
    _apply_spec_style(cfg, {'labelShow': True}, spec_index)
    return 'value'


def _apply_spec_map_label(cfg, spec, spec_index=0):
    """地图柱顶/散点数字标签：specs.scatterLabelShow → option.area.scatterLabelShow（首轮写入）。

    别名：mapLabel / labelShow / barLabel / topLabel。用户点名「顶端数字标签/柱顶标签」时
    首轮写 true，禁止 add 后再 query_page patch。
    """
    raw = None
    for k in ('scatterLabelShow', 'mapLabel', 'labelShow', 'barLabel', 'topLabel'):
        if k in spec:
            raw = spec.get(k)
            break
    if raw is None:
        return
    # 显式 false 也要写入（关闭标签）
    show = _truthy_flag(raw)
    opt = cfg.setdefault('option', {})
    area = opt.setdefault('area', {})
    if not isinstance(area, dict):
        area = {}
        opt['area'] = area
    area['scatterLabelShow'] = bool(show)
    print('MAP_LABEL=%s specs[%d]' % (1 if show else 0, spec_index))


# numberLevel：''/0 无；1 百分比；2 千分比；3 千；4 万；5 百万（与 CompStyleConfig 一致）
_NUMBER_LEVEL_ALIAS = {
    '': '', '0': '0', '无': '', 'none': '',
    '1': '1', '%': '1', '百分比': '1', 'percent': '1',
    '2': '2', '千分比': '2', 'permille': '2',
    '3': '3', '千': '3', 'k': '3',
    '4': '4', '万': '4', 'w': '4', '万元': '4',
    '5': '5', '百万': '5', 'm': '5',
}


def _apply_spec_unit(cfg, spec, spec_index=0):
    """specs.unit / numberLevel / decimal → compStyleConfig.showUnit（首轮写入）。"""
    unit = spec.get('unit')
    level_raw = spec.get('numberLevel') if 'numberLevel' in spec else spec.get('number_level')
    decimal = spec.get('decimal')
    if unit is None and level_raw is None and decimal is None:
        return
    su = (cfg.setdefault('compStyleConfig', {})
          .setdefault('showUnit', {}))
    if unit is not None:
        su['unit'] = str(unit)
        su.setdefault('position', 'suffix')
    if level_raw is not None and str(level_raw).strip() != '':
        key = str(level_raw).strip().lower()
        # 保留中文别名大小写：万/千 等
        key_cn = str(level_raw).strip()
        mapped = (_NUMBER_LEVEL_ALIAS.get(key)
                  if key in _NUMBER_LEVEL_ALIAS
                  else _NUMBER_LEVEL_ALIAS.get(key_cn, key_cn))
        su['numberLevel'] = mapped
        # 单位「万元」且未单独传 unit → 默认后缀万元 + 数量级万
        if mapped == '4' and unit is None and su.get('unit') in (None, ''):
            if key_cn in ('万元', '万') or key in ('万元', '万', '4', 'w'):
                if key_cn == '万元' or key == '万元':
                    su['unit'] = '万元'
        su.setdefault('position', 'suffix')
    if decimal is not None:
        try:
            su['decimal'] = int(decimal)
        except (TypeError, ValueError):
            su['decimal'] = decimal
    print('SHOW_UNIT=specs[%d] numberLevel=%s unit=%s decimal=%s' % (
        spec_index, su.get('numberLevel'), su.get('unit'), su.get('decimal')))


_COMPARE_TYPE_ALIAS = {
    '环比': 'preMonth', 'mom': 'preMonth', 'premonth': 'preMonth',
    'preMonth': 'preMonth', '上月': 'preMonth', '与上月相比': 'preMonth',
    '同比': 'preYear', 'yoy': 'preYear', 'preyear': 'preYear',
    'preYear': 'preYear', '上年': 'preYear', '去年': 'preYear',
    '与上年相比': 'preYear', '与去年相比': 'preYear',
    '上周': 'preWeek', '与上周相比': 'preWeek',
    'preWeek': 'preWeek', 'preweek': 'preWeek',
    '昨天': 'yesterday', '昨日': 'yesterday', 'yesterday': 'yesterday',
}
_COMPARE_NEED_QR = {
    'preMonth': 'month', 'befPreMonth': 'preMonth',
    'preYear': 'year', 'befPreYear': 'preYear',
    'preWeek': 'week', 'befPreWeek': 'preWeek',
    'yesterday': 'today', 'befYesterday': 'yesterday',
}


def _norm_compare_type(raw):
    """口语「与上月相比/环比/同比」→ analysis.compareType。"""
    s = str(raw or '').strip()
    if not s:
        return ''
    if s in _COMPARE_TYPE_ALIAS:
        return _COMPARE_TYPE_ALIAS[s]
    sl = s.lower()
    if sl in _COMPARE_TYPE_ALIAS:
        return _COMPARE_TYPE_ALIAS[sl]
    if '上月' in s or '环比' in s:
        return 'preMonth'
    if '上年' in s or '去年' in s or '同比' in s:
        return 'preYear'
    if '上周' in s:
        return 'preWeek'
    return ''


def _ensure_compare_query_range(cfg, compare_type):
    """开对比时 queryRange 不能是 all；上月→month、上年→year。返回新旧值。"""
    need = _COMPARE_NEED_QR.get(compare_type) or 'month'
    fl = cfg.setdefault('filter', {})
    old = fl.get('queryRange')
    if old != need:
        fl['queryRange'] = need
        if not fl.get('queryField'):
            fl['queryField'] = 'create_time'
        if need != 'custom':
            fl['customTime'] = []
    return old, need


def _ensure_jnumber_compare_height(comp, cfg, min_h=30):
    """有环比行时栅格 h≥30（size.height=h×11）。"""
    try:
        old_h = int(comp.get('h') or 0)
    except (TypeError, ValueError):
        old_h = 0
    if old_h >= min_h:
        return old_h, old_h
    comp['h'] = min_h
    sz = cfg.setdefault('size', {})
    sz['height'] = min_h * 11
    return old_h, min_h


def _norm_trend(raw):
    """升红降绿=2 / 升绿降红=1。红涨绿跌、跌了变绿等口语都认。"""
    trend = str(raw or '').strip()
    if not trend:
        return ''
    _TREND1 = ('绿升红降', 'up_green', '1', 'green_up', '升绿降红')
    _TREND2 = ('红升绿降', 'up_red', '2', 'red_up', '升红降绿', '升红', '降绿')
    if trend in _TREND1:
        return '1'
    if trend in _TREND2:
        return '2'
    if any(k in trend for k in ('绿升', '升绿')):
        return '1'
    if any(k in trend for k in ('红升', '升红')):
        return '2'
    if '红' in trend and '绿' in trend and trend.find('红') < trend.find('绿'):
        return '2'
    if '绿' in trend and '红' in trend and trend.find('绿') < trend.find('红'):
        return '1'
    if trend in ('1', '2'):
        return trend
    return ''


def _apply_spec_compare(cfg, spec, spec_index=0):
    """JNumber 环比/同比：specs.isCompare/compareType/compareValue/trendType（首轮写入）。

    缺 compareValue 时前端不渲染「与上月相比」行（2026-09-03 对照手工卡验证）。
    开对比时 queryRange 不能是 all；未写 compareType 时按 queryRange 推主项。
    """
    raw_cmp = (spec.get('isCompare') if 'isCompare' in spec
               else spec.get('compare') if 'compare' in spec
               else spec.get('mom') if 'mom' in spec
               else None)
    compare_type = spec.get('compareType') or spec.get('compare_type') or ''
    # 用户说「环比/本月环比」等别名
    if not compare_type:
        alias = str(spec.get('compare') or spec.get('mom') or '').strip().lower()
        if alias in ('环比', 'mom', 'premonth', '上月', '与上月相比'):
            compare_type = 'preMonth'
            if raw_cmp is None:
                raw_cmp = True
        elif alias in ('同比', 'yoy', 'preyear', '上年', '与上年相比'):
            compare_type = 'preYear'
            if raw_cmp is None:
                raw_cmp = True
    if raw_cmp is None and not compare_type and 'compareValue' not in spec and 'trendType' not in spec:
        return
    want = _truthy_flag(raw_cmp) if raw_cmp is not None else bool(compare_type)
    if not want and 'compareValue' not in spec:
        return
    qr = ((cfg.get('filter') or {}).get('queryRange') or 'all')
    if qr in ('all', 'last7days', 'last30days', 'custom'):
        print('NOTE=specs[%d] queryRange=%s 不能开数据对比，已忽略 isCompare' % (spec_index, qr))
        return
    # queryRange → 默认 compareType
    _QR_COMPARE = {
        'today': 'yesterday', 'yesterday': 'befYesterday', 'tomorrow': 'today',
        'week': 'preWeek', 'preWeek': 'befPreWeek', 'nextWeek': 'week',
        'month': 'preMonth', 'preMonth': 'befPreMonth', 'nextMonth': 'month',
        'year': 'preYear', 'preYear': 'befPreYear', 'nextYear': 'year',
    }
    if not compare_type:
        compare_type = _QR_COMPARE.get(str(qr), 'preMonth')
    trend_raw = spec.get('trendType') if 'trendType' in spec else (
        spec.get('trend_type') if 'trend_type' in spec else None)
    # 未显式写 trendType 时，从常见中文口径推断（用户点名「升红降绿」不得默认成 1）
    if trend_raw is None or trend_raw == '':
        blob = ' '.join(str(spec.get(k) or '') for k in (
            'trend', 'arrow', 'arrows', 'title', 'note', 'desc', 'compare'))
        if any(x in blob for x in ('红升绿降', '升红', '升了红', '红色箭头', 'up_red')):
            trend_raw = '2'
        elif any(x in blob for x in ('绿升红降', '升绿', '升了绿', '绿色箭头', 'up_green')):
            trend_raw = '1'
        else:
            trend_raw = '1'
    trend = _norm_trend(str(trend_raw).strip()) or '1'
    cv = spec.get('compareValue') if 'compareValue' in spec else 0
    try:
        cv = 0 if cv is None else cv
    except Exception:
        cv = 0
    an = cfg.setdefault('analysis', {})
    an['isCompare'] = True
    an['compareType'] = compare_type
    an['compareValue'] = cv  # 手工卡为 0；缺此键环比行不渲染
    an['trendType'] = trend
    opt = cfg.setdefault('option', {})
    opt['isCompare'] = True
    opt['trendType'] = trend
    # 供 add-charts 保存后回读校验
    spec['_compare_expect'] = {
        'compareType': compare_type, 'compareValue': cv, 'trendType': trend,
    }
    print('COMPARE=1 specs[%d] compareType=%s compareValue=%s trendType=%s' % (
        spec_index, compare_type, cv, trend))


def _verify_jnumber_compare_after_save(page_id, specs, added_start=0):
    """保存后回读 JNumber 环比四键；与手工环比金标对齐。

    仅当 specs 含 _compare_expect（即本轮开了对比）时查询；失败打印 VERIFY_COMPARE_FAIL。
    """
    expects = []
    for i, spec in enumerate(specs):
        exp = spec.get('_compare_expect')
        if not exp:
            continue
        expects.append((i, spec.get('title') or spec.get('name') or '', exp))
    if not expects:
        return
    try:
        page = bi_utils.query_page(page_id)
    except Exception as e:
        print('VERIFY_COMPARE_FAIL query_page: %s' % e)
        return
    tmpl = page.get('template') or []
    if isinstance(tmpl, str):
        try:
            tmpl = json.loads(tmpl)
        except Exception:
            tmpl = []
    # 按本轮追加的尾部组件校验（title + JNumber）
    tail = tmpl[added_start:] if added_start < len(tmpl) else tmpl
    by_title = {}
    for it in tail:
        cfg = it.get('config') or {}
        if isinstance(cfg, str):
            try:
                cfg = json.loads(cfg)
            except Exception:
                cfg = {}
        if (it.get('component') or '') != 'JNumber' and (
                (cfg.get('chart') or {}).get('subclass') != 'JNumber'):
            continue
        title = (((cfg.get('option') or {}).get('title') or {}).get('text')
                 or it.get('componentName') or '')
        by_title[title] = cfg
    ok_all = True
    for i, title, exp in expects:
        cfg = by_title.get(title)
        if not cfg:
            # 回退：扫全页同名
            for it in tmpl:
                c = it.get('config') or {}
                if isinstance(c, str):
                    try:
                        c = json.loads(c)
                    except Exception:
                        c = {}
                t = (((c.get('option') or {}).get('title') or {}).get('text')
                     or it.get('componentName') or '')
                if t == title:
                    cfg = c
                    break
        if not cfg:
            print('VERIFY_COMPARE_FAIL specs[%d] title=%s 保存后未找到组件' % (i, title))
            ok_all = False
            continue
        an = cfg.get('analysis') or {}
        opt = cfg.get('option') or {}
        qr = (cfg.get('filter') or {}).get('queryRange')
        checks = [
            ('analysis.isCompare', an.get('isCompare') in (True, 'true', 1, '1'), True),
            ('analysis.compareType', an.get('compareType') == exp['compareType'], exp['compareType']),
            ('analysis.compareValue', an.get('compareValue') == exp['compareValue'], exp['compareValue']),
            ('analysis.trendType', str(an.get('trendType')) == str(exp['trendType']), exp['trendType']),
            ('option.isCompare', opt.get('isCompare') in (True, 'true', 1, '1'), True),
            ('option.trendType', str(opt.get('trendType')) == str(exp['trendType']), exp['trendType']),
        ]
        bad = []
        for name, good, want in checks:
            if not good:
                bad.append('%s want=%r' % (name, want))
        if qr in ('all', 'last7days', 'last30days', 'custom'):
            bad.append('filter.queryRange=%r(不能开对比)' % qr)
        if bad:
            ok_all = False
            print('VERIFY_COMPARE_FAIL specs[%d] title=%s %s' % (i, title, '; '.join(bad)))
        else:
            print('VERIFY_COMPARE=ok specs[%d] title=%s compareType=%s compareValue=%s trendType=%s queryRange=%s' % (
                i, title, exp['compareType'], exp['compareValue'], exp['trendType'], qr))
    if not ok_all:
        print('VERIFY_COMPARE_FAIL 环比未按手工金标落盘；检查 isCompare/compareType/compareValue/trendType')


# 组件口语别名：qqy_chart.COMP_ALIAS / norm_comp_type（skill 禁止再写对照表）
_WORDCLOUD_SHAPE = {
    '心形': 'cardioid', '心': 'cardioid', '爱心': 'cardioid', '桃心': 'cardioid',
    'heart': 'cardioid', 'cardioid': 'cardioid',
    '圆形': 'circle', '圆': 'circle', 'circle': 'circle',
    '菱形': 'diamond', 'diamond': 'diamond',
    '三角': 'triangle', '三角形': 'triangle', 'triangle': 'triangle',
    '星形': 'star', '星': 'star', 'star': 'star',
    '五边': 'pentagon', 'pentagon': 'pentagon',
}
_SHAPE_ECHARTS = ('cardioid', 'circle', 'diamond', 'triangle', 'star', 'pentagon')
_SHAPE_HINTS = (
    (('爱心', '桃心', '心', 'heart', 'cardioid'), 'cardioid'),
    (('圆', 'circle'), 'circle'),
    (('菱', 'diamond'), 'diamond'),
    (('三角', 'triangle'), 'triangle'),
    (('星', 'star'), 'star'),
    (('五边', 'pentagon'), 'pentagon'),
)


def _norm_wordcloud_shape(raw):
    """口语形状 → echarts。『心的形状』『爱心』『改成心形』都认，禁止业务侧查 cardioid。"""
    s = str(raw or '').strip()
    if not s:
        return ''
    sl = s.lower()
    if sl in _SHAPE_ECHARTS:
        return sl
    hit = _WORDCLOUD_SHAPE.get(s) or _WORDCLOUD_SHAPE.get(sl)
    if hit:
        return hit
    s2 = re.sub(r'(改成|改为|换成|变成)', '', s)
    s2 = re.sub(r'(的)?形状$', '', s2).strip()
    s2 = re.sub(r'形$', '', s2).strip() or s2
    hit = _WORDCLOUD_SHAPE.get(s2) or _WORDCLOUD_SHAPE.get(s2.lower())
    if hit:
        return hit
    for keys, val in _SHAPE_HINTS:
        for k in keys:
            if k in s or k in sl:
                return val
    return ''


_DATE_GROUP_ALIAS = {
    '年': '1', '按年': '1',
    '月': '2', '按月': '2',
    '日': '3', '按日': '3', '每天': '3', '按天': '3', '每日': '3',
    '时': '4', '按小时': '4',
    '分': '5',
}


def _norm_date_group(raw):
    s = str(raw or '').strip()
    if not s:
        return ''
    hit = _DATE_GROUP_ALIAS.get(s) or _DATE_GROUP_ALIAS.get(s.lower())
    if hit:
        return hit
    if s in ('1', '2', '3', '4', '5', '6', '7'):
        return s
    if any(k in s for k in ('按日', '每天', '按天', '每日')):
        return '3'
    if '年' in s and '月' not in s:
        return '1'
    if '月' in s:
        return '2'
    if '日' in s or '天' in s:
        return '3'
    return ''
_CLEAR_CALC = {
    '字段', 'none', 'clear', '还原', '改回', '取消计算值', '普通数值',
    '取消', '改回字段',
}


def _norm_comp_alias(raw):
    return qc.norm_comp_type(raw)


def _apply_oral_chart_style(spec, blob):
    """兼容旧调用；完整解析见 _parse_chart_oral。"""
    parsed, _applied = _parse_chart_oral(blob)
    for k, v in parsed.items():
        if spec.get(k) in (None, '', []):
            spec[k] = v
    return spec


def _parse_chart_oral(text):
    """用户加图原句 → spec 片段。缺旗标时把整句丢进来，禁止业务侧翻 option 文档。"""
    s = str(text or '').strip()
    spec = {}
    applied = []
    if not s:
        return spec, applied

    def _take(key, val):
        if val in (None, ''):
            return
        spec[key] = val
        if key not in applied:
            applied.append(key)

    m = re.search(r'(?:加|一张|一个)[^\s「」"“]{0,12}[「"“]([^」"”]+)[」"”]', s)
    if m:
        _take('title', m.group(1).strip())
    if 'title' not in spec:
        qs = re.findall(r'[「"“]([^」"”]+)[」"”]', s)
        if qs:
            _take('title', qs[-1].strip())

    m = re.search(r'(?:加|一张|一个)\s*([^\s「」"“]{1,12})', s)
    if m:
        c = qc.norm_comp_type(m.group(1).strip('：:，,。'))
        if c in qc.QQY_CHARTS:
            _take('comp', c)
    if 'comp' not in spec:
        for alias, comp in sorted(qc.COMP_ALIAS.items(), key=lambda x: -len(x[0])):
            if alias and alias in s:
                _take('comp', comp)
                break

    def _field(pat, key):
        m = re.search(pat, s)
        if m:
            _take(key, m.group(1).strip('。，、；; '))

    _stop = r'，|。|；|维度|数值|分组|配色|颜色|圆角|点大小|柱宽|形状|图例|$'
    _field(r'维度[=:：是为]?\s*(?!轴|选)([^，。；;\n]+?)(?=%s)' % _stop, 'dim')
    _field(r'数值[=:：是为]?\s*(?!标签|显示|开启|轴)([^，。；;\n]+?)(?=%s)' % _stop, 'val')
    _field(r'分组[=:：是为]?\s*([^，。；;\n]+?)(?=%s)' % _stop, 'grp')
    if 'grp' not in spec:
        _field(r'列[=:：是为]?\s*([^，。；;\n]+?)(?=，|。|；|行|值|$)', 'grp')

    # 透视结构句：行=… → dim（=后置分隔符才认，防「进行/行为」误伤）
    if 'dim' not in spec:
        _field(r'行[=:：]\s*([^，。；;\n]+?)(?=，|。|；|列|值|$)', 'dim')
    # 值=… → val；计数口语词归一 record_count（与后端伪字段同名）
    _COUNT_WORDS = {'数字', '记录条数', '条数', '个数'}
    if 'val' not in spec:
        m = re.search(r'值[=:：]\s*([^，。；;\n]+?)(?=，|。|；|行|列|$)', s)
        if m:
            tok = m.group(1).strip('。，、；; ')
            _take('val', 'record_count' if tok in _COUNT_WORDS else tok)
    # 双轴结构句：左轴X（，右轴Y按Z）→ dim=X val=Y grp=Z；按日/按月不抢 grp
    if re.search(r'左轴|右轴', s):
        if 'dim' not in spec:
            m = re.search(r'左轴[=:：]?\s*([^，。；;\n]+?)(?=右轴|，|。|；|$)', s)
            if m:
                _take('dim', m.group(1).strip('。，、；; '))
        if 'val' not in spec:
            m = re.search(r'右轴[=:：]?\s*([^，。；按\n]+)', s)
            if m:
                tok = m.group(1).strip('。，、；; ')
                _take('val', 'record_count' if tok in _COUNT_WORDS else tok)
        if 'grp' not in spec and '按' in s:
            cand = re.split(r'[，。；;\n]', s.split('按', 1)[1], 1)[0].strip()
            for suf in ('统计', '显示', '展示', '分布', '排行', '情况', '汇总', '分析', '的'):
                if cand.endswith(suf):
                    cand = cand[:-len(suf)].strip()
            if cand and cand[0] not in '日月周年季天':
                _take('grp', cand)

    m = re.search(r'(?:配色|配三色|配色为|颜色)\s*(.+?)(?=点大小|圆角|柱宽|形状|图例|。|；|$)', s)
    if m:
        cols = _split_colors(m.group(1).strip('。，, '))
        if cols:
            _take('colors', cols)

    m = re.search(r'圆角\s*(\d+)', s)
    if m:
        _take('borderRadius', int(m.group(1)))
    m = re.search(r'(?:柱宽|barWidth|bar-width)\s*(\d+)', s, re.I)
    if m:
        _take('barWidth', int(m.group(1)))
    m = re.search(r'(?:点大小|点径|symbolSize)\s*(\d+)', s, re.I)
    if m:
        _take('symbolSize', int(m.group(1)))

    m = re.search(r'形状\s*([^，。；;\n]+)', s)
    if m:
        sh = _norm_wordcloud_shape(m.group(1))
        _take('shape', sh or m.group(1).strip())

    dg = _norm_date_group(s)
    if dg:
        _take('dateGroup', dg)
    qr = _norm_query_range(s)
    if qr:
        _take('queryRange', qr)

    lt = _normalize_line_type(s)
    if lt:
        _take('lineType', lt)

    m = re.search(r'前\s*(\d+)\s*项', s)
    if m:
        _take('dataFilterNum', int(m.group(1)))

    if re.search(r'图例\s*(打开|显示|开|开启)', s):
        _take('legendShow', True)
    if re.search(r'百分比标签', s):
        _take('percentLabel', True)
    if re.search(r'(数值标签|显示数值)', s):
        _take('labelShow', True)
    if re.search(r'(柱顶标签|散点标签)', s):
        _take('scatterLabelShow', True)
    if re.search(r'渐变', s):
        _take('showLinearGradient', True)

    m = re.search(r'计算值[「"“]?([^」"”。；\n]+)', s)
    if m:
        _take('calc', m.group(1).strip())

    return spec, applied


def _split_csv(raw):
    s = str(raw or '').strip()
    if not s:
        return []
    if s.startswith('['):
        try:
            arr = json.loads(s)
            if isinstance(arr, list):
                return [str(x).strip() for x in arr if str(x).strip()]
        except Exception:
            pass
    return [p.strip() for p in re.split(r'[,，、]', s) if p.strip()]


def _spec_from_flags(args):
    """单图捷径：旗标或 --oral 整句。缺旗标把用户原句进 --oral，禁止翻文档。"""
    spec = {}
    oral = (getattr(args, 'oral', None) or getattr(args, 'style', None) or '').strip()
    if oral:
        parsed, applied = _parse_chart_oral(oral)
        spec.update(parsed)
        if applied:
            print('ORAL_APPLIED=%s' % ','.join(applied))
    raw_comp = (getattr(args, 'comp', None) or '').strip()
    if raw_comp:
        spec['comp'] = raw_comp
    comp = _norm_comp_alias(spec.get('comp') or '')
    if not comp:
        return None
    if comp not in qc.QQY_CHARTS:
        print('COMP_UNKNOWN=%s' % (raw_comp or spec.get('comp') or ''))
        sys.exit(1)
    spec['comp'] = comp
    title = (getattr(args, 'title', None) or '').strip()
    if title:
        spec['title'] = title
    dim = (getattr(args, 'dim', None) or '').strip()
    if dim:
        dims = _split_csv(dim)
        spec['dim'] = dims if len(dims) > 1 else (dims[0] if dims else dim)
    val = (getattr(args, 'val', None) or '').strip()
    if val:
        vals = _split_csv(val)
        spec['val'] = vals if len(vals) > 1 else (vals[0] if vals else val)
    grp = (getattr(args, 'grp', None) or '').strip()
    if grp:
        spec['grp'] = grp
    ay = (getattr(args, 'assist_y', None) or '').strip()
    if ay:
        spec['assistY'] = ay
    at = (getattr(args, 'assist_type', None) or '').strip()
    if at:
        spec['assistType'] = at
    dg = (getattr(args, 'date_group', None) or '').strip()
    if dg:
        spec['dateGroup'] = _norm_date_group(dg) or dg
    qr = (getattr(args, 'query_range', None) or '').strip()
    if qr:
        spec['queryRange'] = _norm_query_range(qr) or qr
    qf = (getattr(args, 'query_field', None) or '').strip()
    if qf:
        spec['queryField'] = qf
    ct = (getattr(args, 'custom_time', None) or '').strip()
    if ct:
        parsed = _parse_custom_time(ct)
        if parsed:
            spec['customTime'] = parsed
            spec.setdefault('queryRange', 'custom')
    calc = (getattr(args, 'calc', None) or '').strip()
    if calc:
        spec['calc'] = calc
    colors = (getattr(args, 'colors', None) or getattr(args, 'color', None) or '').strip()
    if colors:
        spec['colors'] = _split_colors(colors)
    br = getattr(args, 'border_radius', None)
    if br not in (None, ''):
        m = re.search(r'(\d+)', str(br))
        if m:
            spec['borderRadius'] = int(m.group(1))
    bw = getattr(args, 'bar_width', None)
    if bw not in (None, ''):
        m = re.search(r'(\d+)', str(bw))
        if m:
            spec['barWidth'] = int(m.group(1))
    ss = getattr(args, 'symbol_size', None)
    if ss not in (None, ''):
        m = re.search(r'(\d+)', str(ss))
        if m:
            spec['symbolSize'] = int(m.group(1))
    style_blob = (getattr(args, 'style', None) or '').strip()
    if style_blob:
        _apply_oral_chart_style(spec, style_blob)
    top_n = getattr(args, 'top_n', None)
    if top_n not in (None, ''):
        spec['dataFilterNum'] = top_n
    lt = (getattr(args, 'line_type', None) or '').strip()
    if lt:
        spec['lineType'] = lt
    if getattr(args, 'label_show', False):
        spec['labelShow'] = True
    if getattr(args, 'percent_label', False):
        spec['percentLabel'] = True
    if getattr(args, 'scatter_label', False):
        spec['scatterLabelShow'] = True
    if getattr(args, 'legend_show', False):
        spec['legendShow'] = True
    for k in ('w', 'h', 'x', 'y'):
        v = getattr(args, k, None)
        if v not in (None, ''):
            spec[k] = int(v)
    slt = getattr(args, 'show_line_total', None)
    if slt not in (None, ''):
        spec['showLineTotal'] = slt
    sct = getattr(args, 'show_column_total', None)
    if sct not in (None, ''):
        spec['showColumnTotal'] = sct
    rn = getattr(args, 'row_n', None)
    if rn not in (None, ''):
        spec['showLineCount'] = rn
    cn = getattr(args, 'col_n', None)
    if cn not in (None, ''):
        spec['showColumnCount'] = cn
    if not spec.get('title'):
        auto = (getattr(args, 'chart_title', None) or '').strip()
        spec['title'] = auto or comp
        if not auto:
            # 缺省标题在 cmd_add_charts 解析 dim/val 后用真实统计描述覆盖（2026-09-08 禁组件名当标题）
            spec['_autoTitle'] = True
    if spec['comp'] in qc.EMPTY_DIM_TYPES:
        spec.setdefault('dim', [])
    if spec['comp'] in qc.MAP_TYPES:
        spec.setdefault('w', 12)
        spec.setdefault('h', 30)
    shape = (getattr(args, 'shape', None) or '').strip()
    if shape:
        mapped = _norm_wordcloud_shape(shape)
        if not mapped:
            print('SHAPE_UNKNOWN=%s 允许口语=心的形状/爱心/心形/圆形/菱形/三角/星形' % shape)
            sys.exit(1)
        spec['shape'] = mapped
    return spec


def _apply_spec_shape(cfg, spec, spec_index=0):
    """词云形状：心形=cardioid。无 series 时补 [{shape}]，禁业务侧 grep option。"""
    raw = spec.get('shape') or spec.get('wordShape') or spec.get('word_shape')
    if raw in (None, ''):
        return
    mapped = _norm_wordcloud_shape(raw) or str(raw).strip()
    if mapped not in (
            'cardioid', 'circle', 'diamond', 'triangle', 'star', 'pentagon'):
        mapped = _norm_wordcloud_shape(raw)
    if not mapped:
        print('SHAPE_UNKNOWN=specs[%d] %s' % (spec_index, raw))
        sys.exit(1)
    opt = cfg.setdefault('option', {})
    series = opt.get('series')
    if not isinstance(series, list) or not series or not isinstance(series[0], dict):
        opt['series'] = [{'shape': mapped}]
    else:
        series[0]['shape'] = mapped
    opt['shape'] = mapped
    print('SHAPE=specs[%d] %s' % (spec_index, mapped))


def _apply_spec_pivot(cfg, spec, spec_index=0):
    pt = cfg.get('pivotTable')
    if not isinstance(pt, dict):
        return
    notes = []
    if 'showLineTotal' in spec:
        pt['showLineTotal'] = _truthy_flag(spec.get('showLineTotal'))
        notes.append('showLineTotal=%s' % pt['showLineTotal'])
    if 'showColumnTotal' in spec:
        pt['showColumnTotal'] = _truthy_flag(spec.get('showColumnTotal'))
        notes.append('showColumnTotal=%s' % pt['showColumnTotal'])
    slc = spec.get('showLineCount')
    if slc in (None, ''):
        slc = spec.get('rowN')
    if slc not in (None, ''):
        pt['showLineCount'] = int(slc)
        notes.append('showLineCount=%s' % pt['showLineCount'])
    scc = spec.get('showColumnCount')
    if scc in (None, ''):
        scc = spec.get('colN')
    if scc not in (None, ''):
        pt['showColumnCount'] = int(scc)
        notes.append('showColumnCount=%s' % pt['showColumnCount'])
    if notes:
        print('PIVOT=specs[%d] %s' % (spec_index, ';'.join(notes)))


def _auto_specs_from_fields(fields):
    """自行发挥门户：KPI×3 + 柱 + 折 + 饼 + 透视。"""
    dim, val, grp, _dates = qc.recommend_fields(fields)
    dim_txt = (dim or {}).get('fieldTxt') or 'create_time'
    val_txt = (val or {}).get('fieldTxt') or 'record_count'
    grp_txt = (grp or {}).get('fieldTxt') or dim_txt
    money = None
    for f in fields or []:
        if (f.get('widgetType') or '') == 'money':
            money = f
            break
    specs = [
        {"comp": "JNumber", "title": "记录总数", "x": 0, "y": 0, "w": 8, "h": 17,
         "dim": [], "val": "record_count"},
    ]
    if money:
        specs.append({
            "comp": "JNumber", "title": (money.get('fieldTxt') or '金额') + "合计",
            "x": 8, "y": 0, "w": 8, "h": 17, "dim": [], "val": money.get('fieldTxt'),
        })
    elif val_txt and val_txt != '记录数量':
        specs.append({
            "comp": "JNumber", "title": val_txt + "合计",
            "x": 8, "y": 0, "w": 8, "h": 17, "dim": [], "val": val_txt,
        })
    else:
        specs.append({
            "comp": "JNumber", "title": "本月记录", "x": 8, "y": 0, "w": 8, "h": 17,
            "dim": [], "val": "record_count", "queryRange": "month",
        })
    specs.append({
        "comp": "JNumber", "title": "本月新增", "x": 16, "y": 0, "w": 8, "h": 17,
        "dim": [], "val": "record_count", "queryRange": "month",
    })
    specs.append({
        "comp": "JBar", "title": "%s分布" % dim_txt, "x": 0, "y": 17, "w": 12, "h": 32,
        "dim": dim_txt, "val": val_txt,
    })
    specs.append({
        "comp": "JLine", "title": "本月按日趋势", "x": 12, "y": 17, "w": 12, "h": 32,
        "dim": "create_time", "val": val_txt, "dateGroup": "3", "queryRange": "month",
    })
    specs.append({
        "comp": "JPie", "title": "%s构成" % grp_txt, "x": 0, "y": 49, "w": 12, "h": 32,
        "dim": grp_txt, "val": val_txt, "percentLabel": True,
    })
    specs.append({
        "comp": "JPivotTable", "title": "明细", "x": 12, "y": 49, "w": 12, "h": 32,
        "dim": dim_txt, "val": val_txt, "showLineTotal": True, "showColumnTotal": True,
    })
    return specs


def _apply_spec_oral_enums(spec, idx=None):
    """layout/specs JSON 与 CLI 旗标走同一套口语归一。禁止只认码、逼业务对表重跑。"""
    if not isinstance(spec, dict):
        return spec
    prefix = 'specs[%d] ' % idx if idx is not None else ''
    notes = []
    raw_comp = spec.get('comp') or spec.get('component')
    if raw_comp:
        mapped = _norm_comp_alias(raw_comp) or raw_comp
        spec['comp'] = mapped
        if mapped != raw_comp:
            notes.append('comp:%s->%s' % (raw_comp, mapped))
        if mapped not in qc.QQY_CHARTS:
            print('%s组件不在 QQY 清单: %s' % (prefix, raw_comp))
            sys.exit(1)
    qr = spec.get('queryRange') or spec.get('query_range')
    if qr not in (None, ''):
        mapped = _norm_query_range(str(qr))
        if not mapped:
            print('%squeryRange 非法: %s 允许=%s 或中文别名(全部/本月/本周/上月/…)' % (
                prefix, qr, ','.join(qc.QUERY_RANGE)))
            sys.exit(1)
        if mapped != str(qr).strip():
            notes.append('queryRange:%s->%s' % (qr, mapped))
        spec['queryRange'] = mapped
    dg = spec.get('dateGroup') or spec.get('date_group')
    if dg not in (None, ''):
        mapped = _norm_date_group(str(dg))
        if not mapped:
            print('%sdateGroup 非法: %s 允许=1..7 或按日/按月/按年' % (prefix, dg))
            sys.exit(1)
        if mapped != str(dg).strip():
            notes.append('dateGroup:%s->%s' % (dg, mapped))
        spec['dateGroup'] = mapped
    ct = spec.get('compareType') or spec.get('compare_type')
    if ct not in (None, ''):
        mapped = _norm_compare_type(str(ct))
        if mapped:
            if mapped != str(ct).strip():
                notes.append('compareType:%s->%s' % (ct, mapped))
            spec['compareType'] = mapped
    if notes:
        print('ORAL_ENUMS %s%s' % (prefix, ' '.join(notes)))
    return spec


def _apply_specs_oral_enums(specs):
    if not isinstance(specs, list):
        return specs
    for i, spec in enumerate(specs):
        _apply_spec_oral_enums(spec, idx=i)
    return specs


def _load_specs(args):
    """Windows PowerShell 会吃掉 --specs JSON 双引号，业务路径必须 --specs-file。
    单图可改走 --comp/--dim/--val 旗标，免写 JSON。"""
    path = (getattr(args, 'specs_file', None) or '').strip()
    raw = getattr(args, 'specs', None)
    if path:
        try:
            raw = _read_json_text(path)
        except OSError as e:
            print('--specs-file 读取失败: %s' % e)
            sys.exit(1)
        print('SPECS_FILE=%s' % path)
    if raw is None or not str(raw).strip():
        spec = _spec_from_flags(args)
        if spec:
            print('SPEC_FROM_FLAGS=1 comp=%s' % spec.get('comp'))
            return [spec]
        print('必须提供 --specs-file 或 --comp 或 --oral（加图原句）')
        sys.exit(1)
    try:
        specs = json.loads(raw)
    except json.JSONDecodeError as e:
        print('--specs JSON 解析失败: %s' % e)
        print('NOTE=PowerShell 传 --specs 会吃掉双引号，报 Expecting property name enclosed in double quotes。必须 Write JSON 文件后用 --specs-file')
        sys.exit(1)
    if not isinstance(specs, list) or not specs:
        print('--specs 必须是非空 JSON 数组')
        sys.exit(1)
    _apply_specs_oral_enums(specs)
    return specs


# ── 缺省标题=真实统计描述 ────────────────────────────────────────────────
# 2026-09-08 铁律：未点名标题时禁止把组件名（JBar/JLine）当标题。
# 结构化描述式（用户确认）：dim=名称类→各{表单名词}{数值词}统计；dim=其他→各{dim}{数值词}统计；
# 无 dim→{数值词}统计；本月/本周/近N天等 queryRange 时间词前缀（如 本月各产品销售额统计）。
_QR_WORD_MAP = {
    'all': '', 'month': '本月', 'preMonth': '上月', 'nextMonth': '下月',
    'week': '本周', 'preWeek': '上周', 'nextWeek': '下周',
    'year': '本年', 'preYear': '去年', 'nextYear': '明年',
    'today': '今日', 'yesterday': '昨日', 'tomorrow': '明日',
    'last7days': '近7天', 'last30days': '近30天',
}
_VAL_SUFFIXES = ('计算值', '汇总值', '统计值', '求和', '合计')


def _metric_title_word(v):
    s = str(v or '').strip().strip('"\'“”「」 ')
    if not s or s.startswith('$'):
        return ''
    w = '记录数' if s == 'record_count' else s
    while any(w.endswith(sf) for sf in _VAL_SUFFIXES):
        for sf in _VAL_SUFFIXES:
            if w.endswith(sf):
                w = w[:-len(sf)]
                break
    return w.strip()


def _form_noun(form_name):
    """产品表/销售明细表 → 产品/销售明细（标题用词，去表名后缀）"""
    n = str(form_name or '').strip()
    for sf in ('明细表', '信息表', '数据表', '统计表', '记录表', '管理表', '表单', '表'):
        if n.endswith(sf):
            n = n[:-len(sf)]
            break
    return n


def _auto_stat_title(form_name, dims_raw, vals_raw, query_range=''):
    """缺省标题=真实统计描述；无词可用时退'数值'（仍不是组件名）。"""
    metrics = [w for w in (_metric_title_word(v) for v in (vals_raw or [])) if w]
    if not metrics:
        metrics = ['数值']
    metric = '、'.join(metrics[:3]) + ('等' if len(metrics) > 3 else '')
    dims = [str(d).strip().strip('"\'“”「」 ')
            for d in (dims_raw or []) if str(d).strip()]
    if not dims:
        core = metric
    else:
        name_class = any(d == '名称' or d.endswith('名称') for d in dims)
        noun = _form_noun(form_name) if name_class else dims[0]
        core = ('各%s%s' % (noun, metric)) if noun else metric
    return (_QR_WORD_MAP.get(str(query_range or ''), '') or '') + core + '统计'


# ── add-charts ────────────────────────────────────────────────────────────
def cmd_add_charts(args):
    t0 = time.time()
    specs = _load_specs(args)
    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    if not (getattr(args, 'page_id', None) or '').strip():
        page_id, _page_name = _resolve_page_id(args, app_id)
        args.page_id = page_id
    form_app_id = (getattr(args, 'form_app_id', None) or '').strip()
    form_app_name = (getattr(args, 'form_app_name', None) or '').strip()
    if form_app_name and not form_app_id:
        other = type('A', (), {})()
        other.tenant_id = args.tenant_id
        other.app_id = ''
        other.app_name = form_app_name
        form_app_id = _resolve_app_id(other)
        print('FORM_APP_ID=%s' % form_app_id)
    if not form_app_id:
        form_app_id = app_id
    cross = str(form_app_id) != str(app_id)
    if cross:
        bi_utils.init_api(args.api_base, args.token, extra_headers={
            'X-Low-App-ID': form_app_id,
            'X-Tenant-Id': str(args.tenant_id),
        })
    if not (getattr(args, 'form_code', None) or '').strip() or (getattr(args, 'form_name', None) or '').strip():
        code, name = _resolve_form(
            form_app_id,
            getattr(args, 'form_code', None) or '',
            getattr(args, 'form_name', None) or '',
            prefer_type=getattr(args, 'form_type', None),
        )
        args.form_code = code
        args.form_name = name
        if getattr(_resolve_form, 'last_type', '') == 'aggregation':
            args.form_type = 'aggregation'
        print('FORM_CODE=%s FORM_NAME=%s FORM_TYPE=%s' % (
            code, name, getattr(args, 'form_type', None) or 'design'))
    fields, form_name, form_type = _load_fields(args)
    if args.form_name:
        form_name = args.form_name
    if cross:
        _init(args)
    # 创建人/流程状态等系统字段不在表单 fields 里，解析 dim/grp/assist 必须并入
    fields_res = list(qc.SYSTEM_FILTER_FIELDS) + list(fields)
    filter_field = copy.deepcopy(qc.SYSTEM_FILTER_FIELDS) + [
        {k: f[k] for k in ('fieldName', 'fieldTxt', 'fieldType', 'widgetType',
                            'fieldShow', 'options', 'customDateType')}
        for f in fields
    ]

    page = bi_utils.query_page(args.page_id)
    tmpl = page.get('template') or []
    if isinstance(tmpl, str):
        try:
            tmpl = json.loads(tmpl)
        except Exception:
            tmpl = []
    bi_utils._page_components[args.page_id] = list(tmpl)
    info = bi_utils._page_info.get(args.page_id) or {}
    info['style'] = info.get('style') or 'default'
    info['lowAppId'] = args.app_id
    bi_utils._page_info[args.page_id] = info

    base_ts = int(time.time() * 1000)
    added = []
    for i, spec in enumerate(specs):
        comp_type = spec.get('comp') or spec.get('component')
        title = spec.get('title') or spec.get('name') or comp_type
        if not comp_type:
            print('specs[%d] 缺少 comp' % i)
            sys.exit(1)
        if comp_type not in qc.QQY_CHARTS:
            print('specs[%d] 组件不在 QQY 清单: %s' % (i, comp_type))
            sys.exit(1)
        x = int(spec.get('x', 0))
        dw, dh = qc.menu_size(comp_type)
        w = int(spec.get('w', dw))
        h = int(spec.get('h', dh))
        if 'y' in spec:
            y = int(spec.get('y', 0))
        else:
            y = _pack_grid_y(tmpl, x, w, h)
        date_group = str(spec.get('dateGroup') or spec.get('date_group') or '')
        if date_group:
            date_group = _norm_date_group(date_group) or date_group
        dim_tok = spec.get('dim')
        val_tok = spec.get('val')
        grp_tok = spec.get('grp')

        # 雷达：维度必填。用户说「维度轴放销量/销售额」指的是 val，不是空 nameFields
        if comp_type in ('JRadar', 'JCircleRadar'):
            if dim_tok is None or dim_tok == '' or dim_tok == []:
                print('specs[%d] %s 必须设置 dim（如名称/产品名称）；空维度不渲染' % (i, comp_type))
                sys.exit(1)

        # 缺项合并成一条报错（原来 dim/val 分开 exit，单图旗标路径要空跑好几轮才知道全缺什么）
        dim_needed = not (comp_type in qc.EMPTY_DIM_TYPES and not dim_tok)
        dims_raw = list(dim_tok) if isinstance(dim_tok, (list, tuple)) else (
            [] if dim_tok in (None, '') else [dim_tok])
        dims_raw = [d for d in dims_raw if d is not None and str(d).strip() != '']
        vals_raw = list(val_tok) if isinstance(val_tok, (list, tuple)) else (
            [] if val_tok in (None, '') else [val_tok])
        vals_raw = [v for v in vals_raw if v is not None and str(v).strip() != '']
        missing_parts = []
        if dim_needed and not dims_raw:
            missing_parts.append('dim')
        if not vals_raw:
            missing_parts.append('val')
        if missing_parts:
            print('specs[%d] 缺少/无法解析: %s（口语写 维度=… 数值=… / 行=… 列=… 值=… / '
                  '左轴…右轴…按… 会被解析；或旗标 --dim/--val/--grp）' % (i, '、'.join(missing_parts)))
            sys.exit(1)

        # 缺省标题=真实统计描述（2026-09-08：漏叠 --title 禁把组件名/comp_type 当标题）
        if spec.get('_autoTitle') or not (spec.get('title') or spec.get('name') or '').strip():
            spec['_autoTitle'] = False
            spec['title'] = _auto_stat_title(
                form_name, dims_raw, vals_raw,
                spec.get('queryRange') or spec.get('query_range') or '')
            print('NOTE=specs[%d] 缺省标题=统计描述 %s' % (i, spec['title']))
        title = spec.get('title') or spec.get('name') or comp_type

        # 关联记录 dim：柱/折/饼/透视一律展开为 localField+标题字段（2026-09-04 用户修透视表对照）
        # 旧误判「JPivotTable 不展开」会导致 fieldName=link_record_* 且无 localField → 透视不渲染
        _expand_link = True

        if comp_type in qc.EMPTY_DIM_TYPES and not dim_tok:
            name_fields = []
        else:
            # dim 支持数组：透视多行维（如 ["关联仓库","关联物料"]）全部进 nameFields 并逐项展开
            dim_toks = list(dim_tok) if isinstance(dim_tok, (list, tuple)) else [dim_tok]
            dim_toks = [d for d in dim_toks if d is not None and d != '']
            if not dim_toks:
                print('specs[%d] 无法解析 dim=%s' % (i, dim_tok))
                sys.exit(1)
            name_fields = []
            for di, dtok in enumerate(dim_toks):
                dim, dim_note = qc.resolve_field_with_fallback(dtok, fields_res, role='dim')
                if dim is None:
                    print('specs[%d] 无法解析 dim[%d]=%s' % (i, di, dtok))
                    sys.exit(1)
                if dim_note:
                    print('NOTE=specs[%d] %s' % (i, dim_note))
                # 仅首维吃 dateGroup，关联维不会套日期归组
                dg = date_group if di == 0 else ''
                nf = qc.as_dim_field(dim, dg, expand_link_record=_expand_link)
                name_fields.append(nf)
                if nf.get('localField'):
                    print('LINK_DIM=1 specs[%d] dim[%d] localField=%s fieldName=%s sourceCode=%s' % (
                        i, di, nf.get('localField'), nf.get('fieldName'), nf.get('sourceCode')))

        # val 支持字符串或数组（雷达多指标：["销量","销售额","单价"]）
        if isinstance(val_tok, (list, tuple)):
            val_toks = [v for v in val_tok if v is not None and v != '']
        elif val_tok is None or val_tok == '':
            val_toks = []
        else:
            val_toks = [val_tok]
        if not val_toks:
            print('specs[%d] 缺少 val' % i)
            sys.exit(1)

        calc_tok = spec.get('calc') or spec.get('calcExpr') or spec.get('calc_expr')
        value_fields = []
        calc_fields_list = []
        last_val = None
        for vt in val_toks:
            item_calc = calc_tok if (len(val_toks) == 1 and calc_tok) else None
            if not item_calc:
                # 单指标时也看 title；多指标时按每个 token 判断是否销售额
                auto_title = title if len(val_toks) == 1 else (vt if isinstance(vt, str) else '')
                item_calc = _auto_sales_calc(vt, auto_title, fields)
                if item_calc:
                    print('NOTE=specs[%d] 销售额自动 calc=%s' % (i, item_calc))
            val_is_formula = isinstance(vt, str) and str(vt).strip().startswith('$')
            if val_is_formula:
                item_calc = vt
                last_val = None
            else:
                last_val, val_note = qc.resolve_field_with_fallback(vt, fields_res, role='val')
                if last_val is None:
                    print('specs[%d] 无法解析 val=%s' % (i, vt))
                    sys.exit(1)
                if val_note:
                    print('NOTE=specs[%d] %s' % (i, val_note))
            if item_calc:
                formula = str(item_calc).strip()
                if not formula.startswith('$'):
                    if not last_val or last_val.get('fieldName') in (None, 'record_count'):
                        print('specs[%d] 计算值需要数值字段 val，当前=%s' % (i, vt))
                        sys.exit(1)
                    model = last_val['fieldName']
                    formula = '$%s-2$*$%s-4$+$%s-1$' % (model, model, model)
                else:
                    formula = _normalize_calc_formula(
                        formula, fields, val_tok=vt, title=title)
                calc_txt = (spec.get('calcTitle') or spec.get('calc_title')
                            or (vt if isinstance(vt, str) and not str(vt).startswith('$') else title))
                if len(val_toks) == 1 and (spec.get('calcTitle') or spec.get('calc_title')):
                    calc_txt = spec.get('calcTitle') or spec.get('calc_title')
                calc_obj = qc.make_calc_field(formula, calc_txt)
                value_fields.append(copy.deepcopy(calc_obj))
                calc_fields_list.append(copy.deepcopy(calc_obj))
            else:
                value_fields.append(qc.as_value_field(last_val))
        calc_obj = calc_fields_list[0] if len(calc_fields_list) == 1 else None
        # 多计算值时整表写入；单计算值仍走下方 calc_obj 分支兼容

        type_fields = []
        if grp_tok:
            grp, grp_note = qc.resolve_field_with_fallback(
                grp_tok, fields_res, role='grp', allow_record_count=False)
            if grp is None:
                print('NOTE=specs[%d] 跳过 grp=%s' % (i, grp_tok))
            else:
                if grp_note:
                    print('NOTE=specs[%d] %s' % (i, grp_note))
                type_fields = [qc.as_dim_field(grp, expand_link_record=_expand_link)]

        assist_y_tok = spec.get('assistY') or spec.get('assistVal') or spec.get('assist_y')
        assist_type_tok = spec.get('assistType') or spec.get('assistGrp') or spec.get('assist_type')
        assist_y_fields = []
        assist_type_fields = []
        if assist_y_tok:
            ay, ay_note = qc.resolve_field_with_fallback(assist_y_tok, fields_res, role='val')
            if ay is None:
                print('specs[%d] 无法解析 assistY=%s' % (i, assist_y_tok))
                sys.exit(1)
            if ay_note:
                print('NOTE=specs[%d] %s' % (i, ay_note))
            assist_y_fields = [qc.as_value_field(ay)]
        if assist_type_tok:
            at, at_note = qc.resolve_field_with_fallback(
                assist_type_tok, fields_res, role='grp', allow_record_count=False)
            if at is None:
                print('NOTE=specs[%d] 跳过 assistType=%s' % (i, assist_type_tok))
            else:
                if at_note:
                    print('NOTE=specs[%d] %s' % (i, at_note))
                assist_type_fields = [qc.as_dim_field(at)]

        query_range = str(spec.get('queryRange') or spec.get('query_range') or 'all')
        query_range = _norm_query_range(query_range) or query_range
        query_field = str(spec.get('queryField') or spec.get('query_field') or 'create_time')
        custom_time = spec.get('customTime') or spec.get('custom_time') or []
        if query_range not in qc.QUERY_RANGE:
            print('specs[%d] queryRange 非法: %s 允许=%s 或中文别名(全部/本月/本周/上月/…)' % (
                i, query_range, ','.join(qc.QUERY_RANGE)))
            sys.exit(1)
        if query_range == 'custom' and (not isinstance(custom_time, list) or len(custom_time) < 2):
            print('specs[%d] queryRange=custom 必须配 customTime:[begin,end]' % i)
            sys.exit(1)
        if form_type == 'aggregation' and query_range != 'all':
            print('NOTE=聚合表弹窗不显示查询范围，specs[%d] queryRange=%s 已改为 all' % (i, query_range))
            query_range = 'all'

        cfg = qc.mk_cfg(
            form_app_id, args.form_code, form_name, form_type,
            comp_type, title, name_fields, value_fields, type_fields, w, h,
            query_range=query_range, query_field=query_field, custom_time=custom_time,
        )
        if cross:
            cfg['appId'] = form_app_id
            cfg.pop('appType', None)
            cfg.pop('type', None)
            print('NOTE=specs[%d] 跨应用表单 appId=%s，已省略 appType/type' % (i, form_app_id))
        if calc_fields_list:
            cfg['calcFields'] = copy.deepcopy(calc_fields_list)
            cfg['valueFields'] = copy.deepcopy(value_fields)
        if assist_y_fields:
            cfg['assistYFields'] = copy.deepcopy(assist_y_fields)
        if assist_type_fields:
            cfg['assistTypeFields'] = copy.deepcopy(assist_type_fields)
        _apply_spec_colors(cfg, spec, spec_index=i)
        _apply_spec_style(cfg, spec, spec_index=i)
        _apply_spec_percent_label(cfg, spec, spec_index=i)
        _apply_spec_map_label(cfg, spec, spec_index=i)
        _apply_spec_unit(cfg, spec, spec_index=i)
        _apply_spec_compare(cfg, spec, spec_index=i)
        _apply_spec_pivot(cfg, spec, spec_index=i)
        _apply_spec_shape(cfg, spec, spec_index=i)
        cfg['filterField'] = copy.deepcopy(filter_field)
        key = '%s_%s' % (base_ts, i)
        comp = qc.make_component(comp_type, title, x, y, w, h, cfg,
                                 order_num=len(tmpl) + i, key=key)
        tmpl.append(comp)
        added.append('%s(%s)' % (title, comp_type))
        print('  [%d] %s (%s) x=%s y=%s w=%s h=%s dim=%s val=%s' % (
            i + 1, title, comp_type, x, y, w, h,
            [f.get('fieldName') for f in name_fields],
            [f.get('fieldName') for f in value_fields]))

    bi_utils._page_components[args.page_id] = tmpl
    bi_utils.save_page(args.page_id)
    # 环比数字卡：保存后回读 analysis/option，避免「COMPARE=1 但编辑器未勾选」误交付
    _verify_jnumber_compare_after_save(args.page_id, specs, added_start=len(tmpl) - len(specs))
    print('ADDED=%d' % len(added))
    print('PAGE_ID=%s' % args.page_id)
    print('耗时: %.1fs' % (time.time() - t0))


# ── group-menu ────────────────────────────────────────────────────────────
def _group_page_into(app_id, page_id, group_name=''):
    """把仪表盘菜单归入分组（create-page / create-dashboard / group-menu 共用）。
    group_name 空 → 归应用已有第一个分组（_list_menus 顺序，DEFAULT_GROUP 打印确认）；
    仅应用无任何分组时才新建（有组名建同名，无组名兜底「数据分析」）。"""
    menus = _list_menus(app_id)
    groups = [m for m in menus if m.get('type') == 'group']
    drag = None
    for m in menus:
        if m.get('type') == 'drag' and str(m.get('menuUrl')) == str(page_id):
            drag = m
            break
    if not drag:
        print('未找到 pageId=%s 对应的 drag 菜单' % page_id)
        sys.exit(1)

    group_name = (group_name or '').strip()
    group_id = None
    created = False
    if group_name:
        for g in groups:
            if g.get('menuName') == group_name:
                group_id = g['id']
                break
    elif groups:
        # 未指定分组 → 自动归应用第一个已有分组（禁止新建「数据分析」之类的默认分组）
        group_id = groups[0]['id']
        group_name = groups[0].get('menuName')
        print('DEFAULT_GROUP=应用第一个分组 %s(%s)' % (group_name, group_id))

    if not group_id:
        if not group_name:
            group_name = '数据分析'
        if groups:
            resp = bi_utils._request('POST', '/online/lowAppMenu/createGroup',
                                     data={'menuName': group_name, 'appId': app_id})
            group_id = resp.get('result')
            created = True
            print('createGroup success=%s result=%s' % (resp.get('success'), group_id))
        else:
            # createFirstGroup 会把所有未分组菜单收进新分组（含工作表）
            resp = bi_utils._request('POST', '/online/lowAppMenu/createFirstGroup',
                                     data={'menuName': group_name, 'appId': app_id})
            print('createFirstGroup success=%s message=%s' % (
                resp.get('success'), resp.get('message')))
            print('NOTE=createFirstGroup 会把应用内所有未分组菜单收进该分组')
            menus = _list_menus(app_id)
            groups = [m for m in menus if m.get('type') == 'group']
            for g in groups:
                if g.get('menuName') == group_name:
                    group_id = g['id']
                    break
            if not group_id and groups:
                group_id = groups[0]['id']
            for m in menus:
                if m.get('type') == 'drag' and str(m.get('menuUrl')) == str(page_id):
                    drag = m
                    break
            created = True

    if not group_id:
        print('无法确定分组 ID')
        sys.exit(1)

    if str(drag.get('parentId') or '') == str(group_id):
        print('ALREADY_GROUPED menuId=%s group=%s(%s)' % (drag['id'], group_name, group_id))
    else:
        body = {
            'id': drag['id'],
            'parentId': group_id,
            'menuName': drag.get('menuName') or group_name or '',
            'type': 'drag',
            'menuUrl': page_id,
            'appId': app_id,
            'orderNum': drag.get('orderNum') or 1,
        }
        edit_resp = bi_utils._request('PUT', '/online/lowAppMenu/edit', data=body)
        print('menu_edit success=%s message=%s' % (
            edit_resp.get('success'), edit_resp.get('message')))
        if not edit_resp.get('success'):
            sys.exit(1)
    print('MENU_ID=%s' % drag['id'])
    print('GROUP_ID=%s' % group_id)
    print('GROUP_NAME=%s' % group_name)
    print('CREATED_GROUP=%s' % created)
    return drag['id'], group_id


def cmd_group_menu(args):
    _init(args)
    t0 = time.time()
    _group_page_into(args.app_id, args.page_id, getattr(args, 'group', '') or '')
    print('耗时: %.1fs' % (time.time() - t0))


_TENANT_NAME_SUFFIXES = (
    '有限责任公司', '股份有限公司', '集团公司', '有限公司', '集团', '公司', '租户',
)


def _tenant_name_candidates(name):
    """用户常带「租户/公司」后缀；0 条时同呼去后缀，禁止第二轮 tenants。"""
    s = (name or '').strip()
    out = []
    seen = set()

    def _add(x):
        x = (x or '').strip()
        if x and x not in seen:
            seen.add(x)
            out.append(x)

    _add(s)
    cur = s
    changed = True
    while changed and cur:
        changed = False
        for suf in _TENANT_NAME_SUFFIXES:
            if cur.endswith(suf) and len(cur) > len(suf):
                cur = cur[:-len(suf)].strip()
                _add(cur)
                changed = True
                break
    return out


def _resolve_tenant_id(api_base, token, tenant_id, tenant_name):
    """只给名称：/sys/tenant/list name= 精确匹配 1 条。禁止用 system_creator.py（import * 不导出 _request）。"""
    tid = str(tenant_id or '').strip()
    if tid:
        print('TENANT_ID=%s' % tid)
        return tid
    name = (tenant_name or '').strip()
    if not name:
        print('必须提供 --tenant-id 或 --tenant-name')
        sys.exit(1)
    bi_utils.init_api(api_base, token)
    last_recs = []
    for cand in _tenant_name_candidates(name):
        resp = bi_utils._request('GET', '/sys/tenant/list',
                                 params={'pageNo': 1, 'pageSize': 100, 'name': cand})
        recs = ((resp.get('result') or {}).get('records')) or []
        exact = [t for t in recs if (t.get('name') or '') == cand]
        print('TENANT_QUERY keyword=%s hit=%d exact=%d' % (cand, len(recs), len(exact)))
        last_recs = exact if exact else recs
        if cand != name:
            print('TENANT_RETRY keyword=%s' % cand)
        if len(exact) == 1:
            for t in exact:
                print('%s\t%s\t%s' % (t.get('id'), t.get('name'), t.get('status')))
            print('TENANT_ID=%s' % exact[0].get('id'))
            return str(exact[0].get('id'))
        if recs:
            break
    for t in last_recs:
        print('%s\t%s\t%s' % (t.get('id'), t.get('name'), t.get('status')))
    print('TENANT_NOT_UNIQUE')
    sys.exit(1)


def cmd_tenants(args):
    t0 = time.time()
    keyword = (getattr(args, 'name', None) or '').strip()
    _resolve_tenant_id(args.api_base, args.token, '', keyword)
    print('耗时: %.1fs' % (time.time() - t0))


def _load_layout_file(args):
    path = (getattr(args, 'layout_file', None) or '').strip()
    if not path:
        return None
    try:
        raw = _read_json_text(path)
    except OSError as e:
        print('--layout-file 读取失败: %s' % e)
        sys.exit(1)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print('--layout-file JSON 解析失败: %s' % e)
        sys.exit(1)
    if not isinstance(data, dict):
        print('--layout-file 必须是对象 {charts,buttons,afterCharts,filter}')
        sys.exit(1)
    print('LAYOUT_FILE=%s' % path)
    if data.get('name') and not (getattr(args, 'name', None) or '').strip():
        args.name = data['name']
    if data.get('group') and not (getattr(args, 'group', None) or '').strip():
        args.group = data['group']
    form = data.get('form') or data.get('formName') or data.get('form_name')
    if form and not (getattr(args, 'form_name', None) or '').strip() and not (
            getattr(args, 'form_code', None) or '').strip():
        args.form_name = form
    return data


def cmd_create_dashboard(args):
    """租户+应用+表单+建页+加图+归组同一进程。禁止拆成 apps/forms/fields/create-page/add-charts/group-menu。
    --layout-file 可在同一进程再跑 buttons / afterCharts / filter（复合盘一条命令）。"""
    t0 = time.time()
    layout = _load_layout_file(args)
    if layout is not None:
        specs = layout.get('charts') or []
        if specs and not isinstance(specs, list):
            print('layout.charts 必须是数组')
            sys.exit(1)
    elif getattr(args, 'auto', False) and not (
            getattr(args, 'specs_file', None) or getattr(args, 'specs', None)
            or getattr(args, 'comp', None)):
        specs = None
    else:
        specs = _load_specs(args)

    tenant_id = _resolve_tenant_id(
        args.api_base, args.token,
        getattr(args, 'tenant_id', None),
        getattr(args, 'tenant_name', None),
    )
    args.tenant_id = tenant_id
    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)

    cmd_forms(args)
    form_code = (getattr(args, 'form_code', None) or '').strip()
    form_name = (getattr(args, 'form_name', None) or '').strip()
    forms = _list_design_forms(app_id)
    if not form_code and not form_name:
        if len(forms) == 1:
            form_code = forms[0].get('value')
            form_name = forms[0].get('label') or forms[0].get('title') or form_code
            print('FORM_UNIQUE=1')
        else:
            print('FORM_NEED_CHOICE count=%d' % len(forms))
            sys.exit(1)
    else:
        form_code, form_name = _resolve_form(
            app_id, form_code, form_name,
            prefer_type=getattr(args, 'form_type', None))
    args.form_code = form_code
    args.form_name = form_name
    if getattr(_resolve_form, 'last_type', '') == 'aggregation':
        args.form_type = 'aggregation'
    else:
        args.form_type = getattr(args, 'form_type', None) or 'design'
    cmd_fields(args)

    if specs is None and getattr(args, 'auto', False):
        fields, _fn, _ft = _load_fields(args)
        specs = _auto_specs_from_fields(fields)
        print('AUTO_SPECS=%d' % len(specs))
    if not specs:
        print('必须提供 --specs-file / --comp / --layout-file.charts / --auto')
        sys.exit(1)
    _apply_specs_oral_enums(specs)
    after = None
    if layout:
        after = layout.get('afterCharts') or layout.get('after_charts')
        if after:
            _apply_specs_oral_enums(after)

    page_name = (args.name or '').strip()
    if not page_name:
        print('必须提供 --name 仪表盘名称')
        sys.exit(1)
    page_id = bi_utils.create_page(
        page_name, style='default', theme='default',
        low_app_id=app_id,
    )
    print('PAGE_ID=%s' % page_id)
    print('PAGE_NAME=%s' % page_name)
    args.page_id = page_id
    try:
        args.specs = json.dumps(specs, ensure_ascii=False)
        args.specs_file = ''
        cmd_add_charts(args)
        # --group 空 → 应用第一个已有分组（禁止强制默认「数据分析」新建分组，2026-09-02 修复）
        cmd_group_menu(args)
        if layout:
            btns = layout.get('buttons')
            if btns:
                args.specs = json.dumps(btns, ensure_ascii=False)
                args.specs_file = ''
                cmd_add_buttons(args)
            if after:
                args.specs = json.dumps(after, ensure_ascii=False)
                args.specs_file = ''
                cmd_add_charts(args)
            flt = layout.get('filter')
            if flt:
                args.specs = json.dumps(flt, ensure_ascii=False)
                args.specs_file = ''
                cmd_add_filter(args)
    except SystemExit:
        try:
            bi_utils.delete_page(page_id, physical=False)
            print('ROLLBACK_PAGE=%s' % page_id)
        except Exception as e:
            print('NOTE=ROLLBACK_FAIL=%s' % e)
        raise
    share = '%s/drag/share/%s/%s' % (_frontend_base(args.api_base), app_id, page_id)
    print('SHARE_URL=%s' % share)
    print('APP_ID=%s' % app_id)
    print('耗时: %.1fs' % (time.time() - t0))


# ── add-form-chart（工作表右侧统计，禁止拆成多次 shell / Write 临时脚本）──
def _unwrap_comp_config(result):
    cfg_raw = result.get('config')
    if isinstance(cfg_raw, str):
        try:
            inner = json.loads(cfg_raw)
        except Exception:
            inner = {}
    elif isinstance(cfg_raw, dict):
        inner = cfg_raw
    else:
        inner = {}
    inner_cfg = inner.get('config') if isinstance(inner, dict) else {}
    if isinstance(inner_cfg, str):
        try:
            inner_cfg = json.loads(inner_cfg)
        except Exception:
            inner_cfg = {}
    if not isinstance(inner_cfg, dict):
        inner_cfg = {}
    return inner if isinstance(inner, dict) else {}, inner_cfg


def _frontend_base(api_base):
    from urllib.parse import urlparse
    u = urlparse(api_base)
    scheme = u.scheme or 'http'
    host = u.hostname or '127.0.0.1'
    return '%s://%s:3100' % (scheme, host)


def _resolve_app_id(args):
    app_id = (getattr(args, 'app_id', None) or '').strip()
    name = (getattr(args, 'app_name', None) or '').strip()
    if app_id:
        return app_id
    if not name:
        print('必须提供 --app-id 或 --app-name')
        sys.exit(1)
    resp = bi_utils._request('GET', '/online/lowApp/queryList',
                             params={'tenantId': str(args.tenant_id)})
    apps = ((resp.get('result') or {}).get('appList')) or []
    matched = [a for a in apps if _app_name_match(name, a.get('appName') or '')]
    if len(matched) == 1:
        print('APP_ID=%s' % matched[0].get('id'))
        print('APP_NAME=%s' % (matched[0].get('appName') or ''))
        return matched[0].get('id')
    if not matched:
        print('APP_NOT_FOUND keyword=%s' % name)
        for a in apps:
            print('%s\t%s' % (a.get('id'), a.get('appName')))
        sys.exit(1)
    print('APP_AMBIGUOUS count=%d keyword=%s' % (len(matched), name))
    for a in matched:
        print('%s\t%s' % (a.get('id'), a.get('appName')))
    sys.exit(1)


def _resolve_form(app_id, form_code, form_name, prefer_type=None):
    """解析工作表或聚合表。命中聚合表时 last_type='aggregation'，调用方应写入 args.form_type。"""
    _resolve_form.last_type = 'design'
    prefer = (prefer_type or '').strip() or 'design'
    forms = _list_design_forms(app_id)
    code = (form_code or '').strip()
    keyword = (form_name or '').strip()
    want_agg = prefer == 'aggregation' or keyword.startswith('[聚合')
    if code:
        if not want_agg:
            for f in forms:
                if f.get('value') == code:
                    _resolve_form.last_type = 'design'
                    return f.get('value'), f.get('label') or f.get('title') or code
        rec = _find_agg_record(app_id, code, '')
        if rec:
            _resolve_form.last_type = 'aggregation'
            return rec['id'], rec['label']
        if want_agg:
            print('AGG_NOT_FOUND form-code=%s' % code)
            sys.exit(1)
        return code, keyword or code
    if not keyword:
        print('必须提供 --form-code 或 --form-name')
        print('【表单（普通）】')
        for f in forms:
            print('%s\t%s' % (f.get('value'), f.get('label') or f.get('title') or ''))
        print('【聚合表】')
        for r in _list_agg_records(app_id):
            print('%s\t%s' % (r['id'], r['label']))
        sys.exit(1)
    if not want_agg:
        exact = []
        matched = []
        for f in forms:
            label = f.get('label') or f.get('title') or ''
            val = f.get('value') or ''
            if keyword == label or keyword == val:
                exact.append(f)
            elif _form_keyword_match(keyword, label, val):
                matched.append(f)
        if len(exact) == 1:
            f = exact[0]
            _resolve_form.last_type = 'design'
            return f.get('value'), f.get('label') or f.get('title') or f.get('value')
        if len(exact) > 1:
            matched = exact
        elif len(matched) == 1:
            f = matched[0]
            _resolve_form.last_type = 'design'
            return f.get('value'), f.get('label') or f.get('title') or f.get('value')
        if matched and not want_agg:
            rec = _find_agg_record(app_id, '', keyword)
            if rec:
                _resolve_form.last_type = 'aggregation'
                return rec['id'], rec['label']
            print('FORM_AMBIGUOUS_OR_NOT_FOUND keyword=%s count=%d' % (
                keyword, len(exact) if exact else len(matched)))
            for f in forms:
                print('%s\t%s' % (f.get('value'), f.get('label') or f.get('title') or ''))
            sys.exit(1)
    rec = _find_agg_record(app_id, '', keyword)
    if rec:
        _resolve_form.last_type = 'aggregation'
        return rec['id'], rec['label']
    print('FORM_AMBIGUOUS_OR_NOT_FOUND keyword=%s' % keyword)
    print('【表单（普通）】')
    for f in forms:
        print('%s\t%s' % (f.get('value'), f.get('label') or f.get('title') or ''))
    print('【聚合表】')
    for r in _list_agg_records(app_id):
        print('%s\t%s' % (r['id'], r['label']))
    sys.exit(1)


def _is_default_month_bar(comp, dim, val, date_group, query_range):
    dim_ok = (dim or 'create_time') in ('create_time', '创建时间')
    val_ok = (val or 'record_count') in ('record_count', '记录数量', '记录数', 'count')
    dg_ok = str(date_group or '3') == '3'
    qr_ok = (query_range or 'month') == 'month'
    return comp == 'JBar' and dim_ok and val_ok and dg_ok and qr_ok


def cmd_add_form_chart(args):
    """工作表右侧统计加图：查应用+表单+创建+挂载同一进程完成。"""
    t0 = time.time()
    tab = (getattr(args, 'chart_tab', None) or 'public').strip()
    if tab not in ('public', 'private'):
        print('--type 必须是 public 或 private')
        sys.exit(1)
    title = (args.title or '').strip()
    if not title:
        print('必须提供 --title')
        sys.exit(1)
    comp = (getattr(args, 'comp', None) or 'JBar').strip()
    dim = (getattr(args, 'dim', None) or 'create_time').strip()
    val = (getattr(args, 'val', None) or 'record_count').strip()
    date_group = _norm_date_group(getattr(args, 'date_group', None) or '3') or '3'
    query_range = _norm_query_range(getattr(args, 'query_range', None) or 'month') or 'month'
    query_field = str(getattr(args, 'query_field', None) or 'create_time')

    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)

    form_code, form_name = _resolve_form(
        app_id,
        getattr(args, 'form_code', None) or '',
        getattr(args, 'form_name', None) or '',
    )
    args.form_code = form_code
    args.form_name = form_name
    args.form_type = getattr(args, 'form_type', None) or 'design'
    print('FORM_CODE=%s' % form_code)
    print('FORM_NAME=%s' % form_name)

    fields_resp = bi_utils._request('GET', '/desform/api/fields/' + form_code)
    form_meta = fields_resp.get('result') or {}
    desform_id = form_meta.get('id') or ''
    print('DESFORM_ID=%s' % desform_id)

    bar_id = None
    number_id = None
    use_def = _is_default_month_bar(comp, dim, val, date_group, query_range)

    if use_def:
        def_resp = bi_utils._request('GET', '/drag/page/comp/createDefChart', params={
            'name': title,
            'code': form_code,
        })
        ids = def_resp.get('result') or []
        if not isinstance(ids, list) or len(ids) < 2:
            print('createDefChart 失败: %s' % json.dumps(def_resp, ensure_ascii=False)[:500])
            sys.exit(1)
        number_id, bar_id = ids[0], ids[1]
        q = bi_utils._request('GET', '/drag/page/comp/queryById', params={'id': bar_id})
        r = q.get('result') or {}
        inner, inner_cfg = _unwrap_comp_config(r)
        actual = r.get('component') or inner.get('component')
        if actual and actual != 'JBar':
            for cid in ids:
                qq = bi_utils._request('GET', '/drag/page/comp/queryById', params={'id': cid})
                rr = qq.get('result') or {}
                inn, _cfg = _unwrap_comp_config(rr)
                ctype = rr.get('component') or inn.get('component')
                if ctype == 'JBar':
                    bar_id, inner, inner_cfg, r = cid, inn, _cfg, rr
                elif ctype == 'JNumber':
                    number_id = cid
        opt = inner_cfg.get('option') or {}
        title_obj = opt.get('title') if isinstance(opt.get('title'), dict) else {}
        if title_obj.get('text') != title:
            title_obj['show'] = True
            title_obj['text'] = title
            opt['title'] = title_obj
            inner_cfg['option'] = opt
            nested = inner if isinstance(inner, dict) else {}
            nested['component'] = 'JBar'
            nested['id'] = nested.get('id') or bar_id
            nested['config'] = inner_cfg
            edit_resp = bi_utils._request('POST', '/drag/page/comp/edit', data={
                'id': bar_id,
                'component': 'JBar',
                'config': json.dumps(nested, ensure_ascii=False),
            })
            if not edit_resp.get('success'):
                print('EDIT_FAIL=%s' % json.dumps(edit_resp, ensure_ascii=False)[:400])
                sys.exit(1)
        print('MODE=createDefChart')
    else:
        if comp not in qc.QQY_CHARTS:
            print('组件不在 QQY 清单: %s' % comp)
            sys.exit(1)
        fields, fname, form_type = _load_fields(args)
        form_name = form_name or fname
        if query_range not in qc.QUERY_RANGE:
            print('queryRange 非法: %s' % query_range)
            sys.exit(1)
        if comp in qc.EMPTY_DIM_TYPES:
            name_fields = []
        else:
            dim_f = qc.resolve_field(dim, fields)
            if dim_f is None:
                print('无法解析 dim=%s' % dim)
                sys.exit(1)
            if date_group and not qc.is_date_dim_field(dim_f):
                print('NOTE=dim=%s 非日期，忽略 dateGroup=%s' % (
                    dim_f.get('fieldTxt') or dim_f.get('fieldName') or dim, date_group))
                date_group = ''
            name_fields = [qc.as_dim_field(
                dim_f, date_group, expand_link_record=True)]
        val_f = qc.resolve_field(val, fields)
        if val_f is None:
            print('无法解析 val=%s' % val)
            sys.exit(1)
        cfg = qc.mk_cfg(
            app_id, form_code, form_name, form_type,
            comp, title, name_fields, [qc.as_value_field(val_f)], None, 12, 28,
            query_range=query_range, query_field=query_field,
        )
        cfg.pop('appId', None)
        cfg.pop('appType', None)
        cfg.pop('type', None)
        nested = {'component': comp, 'id': '', 'config': cfg}
        add_resp = bi_utils._request('POST', '/drag/page/comp/add', data={
            'component': comp,
            'config': json.dumps(nested, ensure_ascii=False),
        })
        result = add_resp.get('result')
        if isinstance(result, dict):
            bar_id = result.get('id')
        else:
            bar_id = result
        if not bar_id or not add_resp.get('success'):
            print('ADD_FAIL=%s' % json.dumps(add_resp, ensure_ascii=False)[:500])
            sys.exit(1)
        print('MODE=customAdd')

    save_resp = bi_utils._request('POST', '/desform/chart/save', data={
        'chartId': bar_id,
        'type': tab,
        'designFormCode': form_code,
    })
    if not save_resp.get('success'):
        print('SAVE_FAIL=%s' % json.dumps(save_resp, ensure_ascii=False)[:500])
        sys.exit(1)

    if number_id and not getattr(args, 'keep_number', False):
        bi_utils._request('DELETE', '/drag/page/comp/deleteById', params={'id': number_id})
        print('DEL_NUMBER=%s' % number_id)
    elif number_id and getattr(args, 'keep_number', False):
        num_save = bi_utils._request('POST', '/desform/chart/save', data={
            'chartId': number_id,
            'type': tab,
            'designFormCode': form_code,
        })
        print('SAVE_NUMBER=%s' % num_save.get('success'))

    verify = bi_utils._request('GET', '/desform/chart/list', params={'code': form_code})
    items = verify.get('result') or []
    found = [x for x in items if str(x.get('chartId')) == str(bar_id)]
    if not found:
        print('VERIFY_FAIL chartId=%s 未出现在 list' % bar_id)
        sys.exit(1)
    mount_id = found[0].get('id')
    url = '%s/myapp/%s/form/%s' % (_frontend_base(args.api_base), app_id, desform_id)
    print('CHART_ID=%s' % bar_id)
    print('MOUNT_ID=%s' % mount_id)
    print('TYPE=%s' % tab)
    print('PREVIEW_URL=%s' % url)
    print('耗时: %.1fs' % (time.time() - t0))


def _norm_title(s):
    s = (s or '').strip()
    if len(s) >= 2 and s[0] == '[' and s[-1] == ']':
        s = s[1:-1].strip()
    return s


def _title_match(actual, want):
    a = _norm_title(actual)
    w = _norm_title(want)
    return bool(w) and (a == w or w in a)


def _chart_title_of(item):
    t = item.get('title')
    if t:
        return str(t)
    cid = item.get('chartId')
    if not cid:
        return ''
    q = bi_utils._request('GET', '/drag/page/comp/queryById', params={'id': cid})
    r = q.get('result') or {}
    inner, inner_cfg = _unwrap_comp_config(r)
    opt = inner_cfg.get('option') if isinstance(inner_cfg.get('option'), dict) else {}
    title_obj = opt.get('title') if isinstance(opt.get('title'), dict) else {}
    return str(title_obj.get('text') or inner.get('componentName')
               or r.get('componentName') or inner_cfg.get('componentName') or '')


def _find_form_chart_cands(form_code, tab, title):
    """list 的 title 常为 None，按 option.title.text 匹配。同名全部返回。"""
    lst = bi_utils._request('GET', '/desform/chart/list', params={'code': form_code})
    items = lst.get('result') or []
    cands = []
    for x in items:
        if str(x.get('type') or '') != tab:
            continue
        text = _chart_title_of(x)
        print('CAND type=%s chartId=%s mountId=%s title=%s' % (
            x.get('type'), x.get('chartId'), x.get('id'), text))
        if _title_match(text, title):
            cands.append(x)
    return cands, items


def cmd_delete_form_chart(args):
    """工作表右侧统计删图：查应用+表单+按 Tab/标题删除，同一进程完成。同名全删。"""
    t0 = time.time()
    tab = (getattr(args, 'chart_tab', None) or 'public').strip()
    if tab not in ('public', 'private'):
        print('--type 必须是 public 或 private')
        sys.exit(1)
    title = _norm_title(args.title or '')
    if not title:
        print('必须提供 --title')
        sys.exit(1)

    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    form_code, form_name = _resolve_form(
        app_id,
        getattr(args, 'form_code', None) or '',
        getattr(args, 'form_name', None) or '',
    )
    print('FORM_CODE=%s' % form_code)
    print('FORM_NAME=%s' % form_name)

    fields_resp = bi_utils._request('GET', '/desform/api/fields/' + form_code)
    form_meta = fields_resp.get('result') or {}
    desform_id = form_meta.get('id') or ''
    print('DESFORM_ID=%s' % desform_id)

    cands, _items = _find_form_chart_cands(form_code, tab, title)

    if not cands:
        print('NOT_FOUND title=%s type=%s' % (title, tab))
        print('耗时: %.1fs' % (time.time() - t0))
        sys.exit(1)

    deleted = []
    for x in cands:
        mount_id = x.get('id')
        chart_id = x.get('chartId')
        rm = bi_utils._request('DELETE', '/desform/chart/remove', params={'id': mount_id})
        if not rm.get('success'):
            print('REMOVE_FAIL mount=%s %s' % (
                mount_id, json.dumps(rm, ensure_ascii=False)[:400]))
            sys.exit(1)
        dc = bi_utils._request('DELETE', '/drag/page/comp/deleteById', params={'id': chart_id})
        print('DEL mount=%s chart=%s remove=%s delcomp=%s' % (
            mount_id, chart_id, rm.get('success'), dc.get('success')))
        deleted.append((mount_id, chart_id))

    verify = bi_utils._request('GET', '/desform/chart/list', params={'code': form_code})
    items2 = verify.get('result') or []
    gone_ids = set(str(m) for m, _c in deleted) | set(str(c) for _m, c in deleted)
    still = [i for i in items2
             if str(i.get('id')) in gone_ids or str(i.get('chartId')) in gone_ids]
    tab_left = [i for i in items2 if str(i.get('type') or '') == tab]
    print('DELETED=%d' % len(deleted))
    print('VERIFY_GONE=%s' % (len(still) == 0))
    print('TAB_LEFT=%d' % len(tab_left))
    print('TYPE=%s' % tab)
    url = '%s/myapp/%s/form/%s' % (_frontend_base(args.api_base), app_id, desform_id)
    print('PREVIEW_URL=%s' % url)
    print('耗时: %.1fs' % (time.time() - t0))


def cmd_move_form_chart(args):
    """工作表右侧统计改归属：从公共中移出 / 转为公共。同一进程 list+标题匹配+updateType。同名全改。"""
    t0 = time.time()
    src = (getattr(args, 'chart_tab', None) or 'public').strip()
    dst = (getattr(args, 'to_tab', None) or '').strip()
    if src not in ('public', 'private'):
        print('--type 必须是 public 或 private')
        sys.exit(1)
    if dst not in ('public', 'private'):
        print('--to 必须是 public 或 private')
        sys.exit(1)
    if src == dst:
        print('FROM_EQ_TO type=%s' % src)
        sys.exit(1)
    title = _norm_title(args.title or '')
    if not title:
        print('必须提供 --title')
        sys.exit(1)

    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    form_code, form_name = _resolve_form(
        app_id,
        getattr(args, 'form_code', None) or '',
        getattr(args, 'form_name', None) or '',
    )
    print('FORM_CODE=%s' % form_code)
    print('FORM_NAME=%s' % form_name)

    fields_resp = bi_utils._request('GET', '/desform/api/fields/' + form_code)
    form_meta = fields_resp.get('result') or {}
    desform_id = form_meta.get('id') or ''
    print('DESFORM_ID=%s' % desform_id)

    cands, _items = _find_form_chart_cands(form_code, src, title)
    if not cands:
        print('NOT_FOUND title=%s type=%s' % (title, src))
        print('耗时: %.1fs' % (time.time() - t0))
        sys.exit(1)

    moved = []
    for x in cands:
        mount_id = x.get('id')
        chart_id = x.get('chartId')
        upd = bi_utils._request('POST', '/desform/chart/updateType', data={
            'id': mount_id,
            'type': dst,
        })
        if not upd.get('success'):
            print('UPDATE_FAIL mount=%s %s' % (
                mount_id, json.dumps(upd, ensure_ascii=False)[:400]))
            sys.exit(1)
        print('MOVE mount=%s chart=%s %s->%s' % (mount_id, chart_id, src, dst))
        moved.append((mount_id, chart_id))

    verify = bi_utils._request('GET', '/desform/chart/list', params={'code': form_code})
    items2 = verify.get('result') or []
    by_mount = {str(i.get('id')): str(i.get('type') or '') for i in items2}
    ok = all(by_mount.get(str(m)) == dst for m, _c in moved)
    print('MOVED=%d' % len(moved))
    print('FROM=%s' % src)
    print('TO=%s' % dst)
    print('VERIFY_TYPE=%s' % ok)
    for m, c in moved:
        print('CHART_ID=%s' % c)
        print('MOUNT_ID=%s' % m)
    url = '%s/myapp/%s/form/%s' % (_frontend_base(args.api_base), app_id, desform_id)
    print('PREVIEW_URL=%s' % url)
    print('耗时: %.1fs' % (time.time() - t0))
    if not ok:
        sys.exit(1)


def _copy_comp_id(resp):
    result = resp.get('result')
    if isinstance(result, dict):
        return result.get('id') or result.get('chartId')
    return result


def cmd_copy_form_chart(args):
    """复制到当前统计：copyById + save 到当前 Tab。同名多张取最新。"""
    t0 = time.time()
    tab = (getattr(args, 'chart_tab', None) or 'public').strip()
    if tab not in ('public', 'private'):
        print('--type 必须是 public 或 private')
        sys.exit(1)
    title = _norm_title(args.title or '')
    if not title:
        print('必须提供 --title')
        sys.exit(1)

    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    form_code, form_name = _resolve_form(
        app_id,
        getattr(args, 'form_code', None) or '',
        getattr(args, 'form_name', None) or '',
    )
    print('FORM_CODE=%s' % form_code)
    print('FORM_NAME=%s' % form_name)

    fields_resp = bi_utils._request('GET', '/desform/api/fields/' + form_code)
    form_meta = fields_resp.get('result') or {}
    desform_id = form_meta.get('id') or ''
    print('DESFORM_ID=%s' % desform_id)

    cands, items_before = _find_form_chart_cands(form_code, tab, title)
    if not cands:
        print('NOT_FOUND title=%s type=%s' % (title, tab))
        print('耗时: %.1fs' % (time.time() - t0))
        sys.exit(1)

    def _cid_key(x):
        cid = str(x.get('chartId') or '0')
        try:
            return int(cid)
        except ValueError:
            return 0

    src = max(cands, key=_cid_key)
    src_id = src.get('chartId')
    print('SRC_CHART_ID=%s' % src_id)
    print('SRC_MOUNT_ID=%s' % src.get('id'))

    copy_resp = bi_utils._request('GET', '/drag/page/comp/copyById', params={'id': src_id})
    if not copy_resp.get('success'):
        print('COPY_FAIL=%s' % json.dumps(copy_resp, ensure_ascii=False)[:500])
        sys.exit(1)
    new_id = _copy_comp_id(copy_resp)
    if not new_id:
        print('COPY_NO_ID=%s' % json.dumps(copy_resp, ensure_ascii=False)[:500])
        sys.exit(1)
    print('NEW_CHART_ID=%s' % new_id)

    save_resp = bi_utils._request('POST', '/desform/chart/save', data={
        'chartId': new_id,
        'type': tab,
        'designFormCode': form_code,
    })
    if not save_resp.get('success'):
        print('SAVE_FAIL=%s' % json.dumps(save_resp, ensure_ascii=False)[:500])
        sys.exit(1)

    verify = bi_utils._request('GET', '/desform/chart/list', params={'code': form_code})
    items2 = verify.get('result') or []
    found = [x for x in items2 if str(x.get('chartId')) == str(new_id)]
    if not found:
        print('VERIFY_FAIL chartId=%s 未出现在 list' % new_id)
        sys.exit(1)
    mount_id = found[0].get('id')
    same_tab = [x for x in items2 if str(x.get('type') or '') == tab]
    print('COPIED=1')
    print('TYPE=%s' % tab)
    print('MOUNT_ID=%s' % mount_id)
    print('TAB_COUNT=%d' % len(same_tab))
    print('TAB_BEFORE=%d' % len([x for x in items_before if str(x.get('type') or '') == tab]))
    url = '%s/myapp/%s/form/%s' % (_frontend_base(args.api_base), app_id, desform_id)
    print('PREVIEW_URL=%s' % url)
    print('耗时: %.1fs' % (time.time() - t0))


# ── add-buttons（已有仪表盘加 JCustomButton，禁止拆 shell / 读 qqy-guide / Write 临时脚本）──
_BTN_OP_ALIASES = {
    '1': '1', 'create': '1', '创建': '1', '创建记录': '1', '新增': '1', '新增记录': '1',
    '2': '2', 'view': '2', '打开视图': '2', '列表': '2', '打开列表': '2', '列表视图': '2',
    '打开订单列表视图': '2', '打开列表视图': '2',
    '3': '3', 'page': '3', '自定义页面': '3', '打开页面': '3', '打开自定义页面': '3',
    '4': '4', 'link': '4', 'url': '4', '打开链接': '4', '链接': '4',
    '6': '6', 'flow': '6', '业务流程': '6', '调用业务流程': '6', '流程': '6',
}
_BTN_ICON = {
    '1': ('ant-design:plus-outlined', '#2196f3'),
    '2': ('ant-design:unordered-list-outlined', '#ED4B82'),
    '3': ('ant-design:layout-outlined', '#9c27b0'),
    '4': ('ant-design:link-outlined', '#ff9800'),
    '6': ('ant-design:apartment-outlined', '#4caf50'),
}
#: 规格没点名 color 时按按钮位置轮换的调色板（线上进销存模版首页按钮组的实测顺序）。
#  2026-09-17 事故：一组 5 个「打开列表视图」按钮全落成同一个 #ED4B82，用户报
#  「按钮的颜色和图表都一样」。op 默认色只在调色板用尽时兜底；显式 color 永远优先。
_BTN_PALETTE = ['#ED4B82', '#9c27b0', '#64b5f6', '#83c683', '#ff8a66', '#ff9800']
_BTN_CLICK = {
    'type': '1',
    'message': {'title': '你确认执行此操作吗？', 'okText': '确认', 'cancelText': '取消'},
}


def _norm_op(raw):
    key = str(raw or '').strip()
    op = _BTN_OP_ALIASES.get(key) or _BTN_OP_ALIASES.get(key.lower())
    if not op:
        print('无法识别操作类型: %s（可用 1创建记录/2打开视图/3自定义页面/4链接/6业务流程）' % raw)
        sys.exit(1)
    return op


def _unwrap_views(resp):
    raw = resp.get('result')
    if isinstance(raw, dict):
        return raw.get('records') or raw.get('list') or raw.get('viewList') or []
    if isinstance(raw, list):
        return raw
    return []


def _view_id_name(v):
    if not isinstance(v, dict):
        return '', ''
    vid = str(v.get('id') or v.get('value') or v.get('key') or '')
    name = v.get('name') or v.get('label') or v.get('title') or ''
    return vid, name


def _pick_view(views, keyword):
    """无自定义视图 → ''（全部记录）。有视图则按名称匹配，『列表』可匹配含列表的视图。"""
    items = [_view_id_name(v) for v in views]
    items = [x for x in items if x[0] or x[1]]
    if not items:
        return '', ''
    kw = (keyword or '').strip()
    if not kw or kw in ('全部', '默认', 'all', '列表', '列表视图'):
        named = [x for x in items if '列表' in x[1] or x[1] in ('全部', '默认')]
        if len(named) == 1:
            return named[0]
        if kw in ('列表', '列表视图') and not named:
            return '', ''
        if len(items) == 1:
            return items[0]
        if not kw:
            return '', ''
    matched = [x for x in items if kw == x[1] or kw in x[1] or x[1] in kw]
    if len(matched) == 1:
        return matched[0]
    if len(matched) > 1:
        print('VIEW_AMBIGUOUS keyword=%s count=%d' % (kw, len(matched)))
        for vid, name in matched:
            print('%s\t%s' % (vid, name))
        sys.exit(1)
    print('VIEW_NOT_FOUND keyword=%s' % kw)
    for vid, name in items:
        print('%s\t%s' % (vid, name))
    sys.exit(1)


def _pick_sole_drag_page(menus):
    """应用内恰好一张 drag 盘时返回 (pageId, pageName)，否则 (None, None)。"""
    drag = [m for m in (menus or [])
            if m.get('type') == 'drag' and str(m.get('menuUrl') or '').strip()]
    if len(drag) != 1:
        return None, None
    return str(drag[0].get('menuUrl') or ''), (drag[0].get('menuName') or '')


def _resolve_page_id(args, app_id):
    page_id = (getattr(args, 'page_id', None) or '').strip()
    name = (getattr(args, 'page_name', None) or '').strip()
    if page_id:
        return page_id, name
    if not name:
        menus = _list_menus(app_id)
        pid, pname = _pick_sole_drag_page(menus)
        if pid:
            print('PAGE_ID=%s' % pid)
            print('PAGE_NAME=%s' % pname)
            print('NOTE=未给 --page-name，应用内仅一张盘，已自动选用')
            return pid, pname
        print('必须提供 --page-id 或 --page-name（应用内多张盘）')
        for m in menus:
            if m.get('type') == 'drag':
                print('%s\t%s\t%s' % (m.get('type'), m.get('menuName'), m.get('menuUrl')))
        sys.exit(1)
    menus = _list_menus(app_id)
    drag = [m for m in menus if m.get('type') == 'drag'
            and name in (m.get('menuName') or '')]
    if len(drag) == 1:
        pid = str(drag[0].get('menuUrl') or '')
        print('PAGE_ID=%s' % pid)
        print('PAGE_NAME=%s' % (drag[0].get('menuName') or ''))
        return pid, drag[0].get('menuName') or name
    pages_resp = bi_utils._request('GET', '/drag/page/list',
                                   params={'lowAppId': app_id, 'pageNo': 1, 'pageSize': 100})
    pages = [p for p in ((pages_resp.get('result') or {}).get('records') or [])
             if p.get('lowAppId') == app_id and name in (p.get('name') or '')]
    if len(pages) == 1:
        pid = str(pages[0].get('id'))
        print('PAGE_ID=%s' % pid)
        print('PAGE_NAME=%s' % (pages[0].get('name') or ''))
        return pid, pages[0].get('name') or name
    print('PAGE_AMBIGUOUS_OR_NOT_FOUND keyword=%s menus=%d pages=%d' % (
        name, len(drag), len(pages)))
    for m in menus:
        if m.get('type') == 'drag':
            print('%s\t%s\t%s' % (m.get('type'), m.get('menuName'), m.get('menuUrl')))
    sys.exit(1)


def _form_meta(app_id, form_code, form_name, cache):
    key = (form_code or '') + '|' + (form_name or '')
    if key in cache:
        return cache[key]
    code, label = _resolve_form(app_id, form_code, form_name)
    fields_resp = bi_utils._request('GET', '/desform/api/fields/' + code,
                                    params={'subTable': True})
    desform_id = str((fields_resp.get('result') or {}).get('id') or '')
    if not desform_id:
        print('未取到 desformId form=%s' % code)
        sys.exit(1)
    views_resp = bi_utils._request('GET', '/desform/api/list/view',
                                   params={'desformCode': code})
    views = _unwrap_views(views_resp)
    meta = {'code': code, 'label': label, 'desformId': desform_id, 'views': views}
    cache[key] = meta
    cache[code + '|'] = meta
    print('FORM_CODE=%s FORM_NAME=%s DESFORM_ID=%s VIEWS=%d' % (
        code, label, desform_id, len(views)))
    return meta


# 按钮样式词映射（产品面板：样式=btnType / 形状=btnStyle / 方向=btnDirection，见 ButtonSetModal.vue）
# 形状注意：图形样式下 solid 渲染 12px 圆角方块卡；circle 渲染 50% 正圆图标。
# 「圆角」= solid 圆角方形卡，不要映射成 circle（那会是正圆）；要正圆图标应说「圆形」。
_BTN_TYPE_WORDS = {'button': 'button', '按钮': 'button', '标准': 'button',
                   'graphical': 'graphical', '图形': 'graphical', '图标': 'graphical', 'icon': 'graphical'}
_BTN_STYLE_WORDS = {'solid': 'solid', '矩形': 'solid', '方块': 'solid', '方形': 'solid', '圆角': 'solid', 'square': 'solid',
                    'circle': 'circle', '圆形': 'circle', '椭圆': 'circle', 'round': 'circle',
                    'dashed': 'dashed', '虚线': 'dashed'}
_BTN_DIRECTION_WORDS = {'column': 'column', '上下': 'column', '纵向': 'column',
                        'row': 'row', '左右': 'row', '横向': 'row'}


def _norm_btn_word(word, table, default):
    """中英词归一化；不认识时打印 NOTE 并用默认值。"""
    if word is None:
        return default
    w = str(word).strip().lower()
    if w in table:
        return table[w]
    if w:
        print('NOTE=按钮样式词「%s」无法识别（可用：%s），使用默认 %s' % (
            word, '/'.join(sorted(table)), default))
    return default


def _load_button_payload(args):
    """list=按钮数组；dict 可含 title/rowNum/btnType/btnStyle/btnDirection/btnWidth/place/buttons。"""
    path = (getattr(args, 'specs_file', None) or '').strip()
    raw = getattr(args, 'specs', None)
    if path:
        try:
            raw = _read_json_text(path)
        except OSError as e:
            print('--specs-file 读取失败: %s' % e)
            sys.exit(1)
        print('SPECS_FILE=%s' % path)
    if raw is None or not str(raw).strip():
        print('必须提供 --specs-file（推荐）或 --specs')
        sys.exit(1)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print('--specs JSON 解析失败: %s' % e)
        print('NOTE=PowerShell 传 --specs 会吃掉双引号。必须 Write JSON 文件后用 --specs-file')
        sys.exit(1)
    if isinstance(data, list):
        if not data:
            print('--specs 必须是非空 JSON 数组或含 buttons 的对象')
            sys.exit(1)
        return {'buttons': data}
    if isinstance(data, dict) and isinstance(data.get('buttons'), list) and data['buttons']:
        return data
    print('--specs 必须是非空按钮数组，或 {title,rowNum,btnWidth,place,buttons:[...]}')
    sys.exit(1)


def _mk_button(spec, idx, app_id, form_cache, ts):
    title = (spec.get('title') or spec.get('name') or '').strip()
    if not title:
        print('buttons[%d] 缺少 title' % idx)
        sys.exit(1)
    op = _norm_op(spec.get('op') or spec.get('operationType') or spec.get('operation'))
    icon, color = _BTN_ICON[op]
    icon = spec.get('icon') or icon
    # 配色：规格没点名就**按按钮位置轮换调色板**，而不是整组用 op 的同一个默认色
    # （见 _BTN_PALETTE 注释的 2026-09-17 事故）。显式 color 优先，op 默认色兜底。
    color = spec.get('color') or _BTN_PALETTE[idx % len(_BTN_PALETTE)] or color
    btn = {
        'btnId': 'btn%d' % (ts + idx),
        'title': title,
        'icon': icon,
        'color': color,
        'operationType': op,
        'worksheet': '',
        'view': '',
        'defVal': spec.get('defVal') if isinstance(spec.get('defVal'), list) else [],
        'customPage': '',
        'href': {'url': '', 'isParam': False, 'params': []},
        'openMode': str(spec.get('openMode') or '2'),
        'bizFlow': '',
        'click': copy.deepcopy(_BTN_CLICK),
    }
    if op in ('1', '2'):
        form_code = spec.get('formCode') or spec.get('form_code') or ''
        form_name = spec.get('form') or spec.get('formName') or spec.get('form_name') or ''
        meta = _form_meta(app_id, form_code, form_name, form_cache)
        worksheet = {
            'label': meta['label'],
            'value': meta['code'],
            'key': meta['code'],
            'type': 'form',
            'desformId': meta['desformId'],
        }
        btn['worksheet'] = worksheet
        btn['appInfo'] = {'type': 'current'}
        btn['desformId'] = meta['desformId']
        if op == '2':
            vid, vname = _pick_view(meta['views'], spec.get('view') or spec.get('viewName') or '')
            btn['view'] = vid
            print('BTN[%d] VIEW_ID=%s VIEW_NAME=%s' % (idx, vid or '', vname or '(全部)'))
    elif op == '3':
        page_label = spec.get('page') or spec.get('pageName') or spec.get('customPage') or ''
        page_value = spec.get('pageId') or spec.get('page_id') or ''
        if isinstance(page_label, dict):
            btn['customPage'] = {
                'label': page_label.get('label') or '',
                'value': page_label.get('value') or page_label.get('key') or '',
                'key': page_label.get('key') or page_label.get('value') or '',
            }
        else:
            if not page_value:
                print('buttons[%d] op=3 需要 pageId 或 customPage 对象' % idx)
                sys.exit(1)
            btn['customPage'] = {
                'label': str(page_label or page_value),
                'value': str(page_value),
                'key': str(page_value),
            }
        btn['appInfo'] = {'type': 'current'}
    elif op == '4':
        url = spec.get('url') or spec.get('href') or ''
        if isinstance(url, dict):
            btn['href'] = {
                'url': url.get('url') or '',
                'isParam': bool(url.get('isParam')),
                'params': url.get('params') or [],
            }
        else:
            if not url:
                print('buttons[%d] op=4 需要 url' % idx)
                sys.exit(1)
            btn['href'] = {'url': str(url), 'isParam': False, 'params': []}
        btn['appInfo'] = None
    elif op == '6':
        flow = spec.get('flow') or spec.get('bizFlow') or spec.get('process')
        if isinstance(flow, dict):
            fid = str(flow.get('value') or flow.get('id') or flow.get('key') or '')
            flabel = flow.get('label') or flow.get('processName') or fid
        else:
            fid = str(spec.get('flowId') or spec.get('processId') or '')
            flabel = str(flow or fid)
        if not fid:
            print('buttons[%d] op=6 需要 flowId/bizFlow 对象' % idx)
            sys.exit(1)
        btn['bizFlow'] = {'label': flabel, 'value': fid, 'key': fid}
        btn['bizParams'] = spec.get('bizParams') if isinstance(spec.get('bizParams'), list) else []
        btn['appInfo'] = {'type': 'current'}
    return btn


def _template_meta(item):
    row = {
        'w': item.get('w'), 'h': item.get('h'), 'i': item.get('i'),
        'x': item.get('x'), 'y': item.get('y'),
        'orderNum': item.get('orderNum', 0),
        'pageCompId': item.get('pageCompId'),
        'component': item.get('component'),
        'componentName': item.get('componentName'),
        'visible': item.get('visible', True),
    }
    for k in ('pcX', 'pcY', 'pcW', 'isLock'):
        if k in item:
            row[k] = item[k]
    return row


def cmd_add_buttons(args):
    """已有仪表盘加一组 JCustomButton：定位应用/页面/表单/视图 + comp/add + saveCompToPage 同一进程。"""
    t0 = time.time()
    payload = _load_button_payload(args)
    buttons_spec = payload['buttons']
    group_title = (getattr(args, 'group_title', None) or payload.get('title')
                   or payload.get('groupTitle') or '自定义按钮')
    row_num = getattr(args, 'row_num', None)
    if row_num in (None, '', 0):
        row_num = payload.get('rowNum')
    # 未指定每行几个时的默认。**不能默认成按钮总数**（那样全挤在一行）——
    # 线上模版首页是 5 个按钮 / rowNum=4（第 5 个换行），用户 2026-09-17 报的
    # 「默认应该一行四个」指的就是这里。按钮不足 4 个时按实际个数，不硬凑。
    row_num = (int(row_num) if row_num not in (None, '')
               else (min(4, len(buttons_spec)) or 1))
    btn_width = (getattr(args, 'btn_width', None) or payload.get('btnWidth') or 'divide')
    place = (getattr(args, 'place', None) or payload.get('place') or 'top').strip() or 'top'
    grid_w = int(payload.get('w') or 24)
    btn_type = _norm_btn_word(
        getattr(args, 'btn_type', None) or payload.get('btnType') or payload.get('type') or 'button',
        _BTN_TYPE_WORDS, 'button')
    btn_style = _norm_btn_word(
        getattr(args, 'btn_style', None) or payload.get('btnStyle') or payload.get('shape') or 'solid',
        _BTN_STYLE_WORDS, 'solid')
    btn_direction = _norm_btn_word(
        getattr(args, 'btn_direction', None) or payload.get('btnDirection') or payload.get('direction') or 'column',
        _BTN_DIRECTION_WORDS, 'column')
    raw_h = payload.get('h')
    # 可视行数：每行 row_num 个；图形每行约需 h=20（min-height≈200px），多行必须按行数累加
    # 2026-09-03：4 钮 rowNum=2 仍用默认 h=20 → 第二行「订单看板/百度」文字被裁（图形按钮多行高度）
    n_btn = len(buttons_spec)
    visual_rows = max(1, (n_btn + row_num - 1) // row_num) if row_num > 0 else 1
    if raw_h in (None, ''):
        grid_h = (20 * visual_rows) if btn_type == 'graphical' else 10
    else:
        grid_h = int(raw_h)
    # 🚨 图形样式渲染区 min-height≈200px/行（Button.vue .btn-area）；单行 h<19 裁字；多行须 ≥19*行数
    min_graphical_h = 19 * visual_rows
    if btn_type == 'graphical' and grid_h < min_graphical_h:
        print('NOTE=图形样式按钮可视行=%d，最低 h=%d，自动从 %d 提到 %d' % (
            visual_rows, min_graphical_h, grid_h, max(min_graphical_h, 20 * visual_rows)))
        grid_h = max(min_graphical_h, 20 * visual_rows)

    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    page_id, page_name = _resolve_page_id(args, app_id)
    args.page_id = page_id

    form_cache = {}
    ts = int(time.time() * 1000)
    btn_list = [_mk_button(spec, i, app_id, form_cache, ts)
                for i, spec in enumerate(buttons_spec)]

    page = bi_utils.query_page(page_id)
    tmpl = page.get('template') or []
    if isinstance(tmpl, str):
        try:
            tmpl = json.loads(tmpl)
        except Exception:
            tmpl = []
    update_count = page.get('updateCount')
    print('UPDATE_COUNT=%s EXISTING=%d' % (update_count, len(tmpl)))

    if place == 'top':
        # 只把**与本次同 x 区段**的组件下移：模版首页是左右两组半宽按钮并排（x=0 / x=12），
        # 无脑整体下移会把另一组也推下去，两组就叠不齐了。
        bx0 = int(payload.get('x') or getattr(args, 'x', None) or 0)
        for item in tmpl:
            if int(item.get('pcX') or 0) != bx0:
                continue
            item['y'] = int(item.get('y') or 0) + grid_h
            if 'pcY' in item:
                item['pcY'] = int(item['pcY'] or 0) + grid_h
        bx, by = bx0, 0
    else:
        max_bottom = 0
        for item in tmpl:
            max_bottom = max(max_bottom, int(item.get('y') or 0) + int(item.get('h') or 0))
        bx, by = 0, max_bottom

    btn_config = {
        'dataType': 1,
        'url': '',
        'timeOut': 0,
        'chartData': btn_list,
        'option': {
            'title': '',
            'btnType': btn_type,
            'btnStyle': btn_style,
            'btnWidth': btn_width,
            'btnDirection': btn_direction,
            'rowNum': row_num,
            'card': {'title': '', 'extra': '', 'rightHref': '', 'size': 'default'},
        },
        'background': '#FFFFFF',
        'borderColor': '#E8E8E8',
        'size': {'width': grid_w * 75, 'height': grid_h * 11},
    }

    add_resp = bi_utils._request('POST', '/drag/page/comp/add', data={
        'pageId': page_id,
        'component': 'JCustomButton',
        'config': json.dumps(btn_config, ensure_ascii=False),
    })
    if not add_resp.get('success'):
        print('comp/add 失败: %s' % add_resp.get('message'))
        sys.exit(1)
    page_comp_id = str((add_resp.get('result') or {}).get('id') or add_resp.get('result') or '')
    if not page_comp_id or page_comp_id == 'None':
        print('comp/add 未返回 id: %s' % json.dumps(add_resp, ensure_ascii=False)[:500])
        sys.exit(1)
    print('PAGE_COMP_ID=%s' % page_comp_id)

    new_item = {
        'w': grid_w, 'h': grid_h, 'i': str(uuid.uuid4()),
        'x': bx, 'y': by, 'orderNum': 0,
        'pageCompId': page_comp_id,
        'component': 'JCustomButton',
        'componentName': group_title,
        'visible': True,
        'pcX': bx, 'pcY': by, 'pcW': grid_w,
    }
    clean = [_template_meta(new_item)] + [_template_meta(it) for it in tmpl]
    # template 必须是 JSON 字符串。传数组会报 Cannot deserialize value of type java.lang.String from Array
    save_resp = bi_utils._request('POST', '/drag/page/saveCompToPage', data={
        'id': page_id,
        'template': json.dumps(clean, ensure_ascii=False),
        'updateCount': update_count,
    })
    if not save_resp.get('success'):
        print('saveCompToPage 失败: %s' % save_resp.get('message'))
        print('NOTE=template 必须 json.dumps 成字符串；禁止 save_page 重建整页')
        sys.exit(1)

    print('ADDED=JCustomButton buttons=%d rowNum=%s btnWidth=%s place=%s' % (
        len(btn_list), row_num, btn_width, place))
    print('BTN_STYLE=btnType=%s btnStyle=%s btnDirection=%s h=%d' % (
        btn_type, btn_style, btn_direction, grid_h))
    share = '%s/drag/share/%s/%s' % (_frontend_base(args.api_base), app_id, page_id)
    print('APP_ID=%s' % app_id)
    print('PAGE_ID=%s' % page_id)
    print('SHARE_URL=%s' % share)
    print('耗时: %.1fs' % (time.time() - t0))


# ── add-filter（已有仪表盘加 JFilterQuery 查询条件并联动统计图；禁止读 qqy-guide 六步 / Write 临时脚本）──
_FILTER_NO_VIEW = {
    'JFilterQuery', 'JText', 'JCustomButton', 'JCarousel', 'JDragEditor',
    'JIframe', 'JCurrentTime', 'JImg', 'JCalendar', 'JMultiViewCalendar',
    'JWaitMatter', 'JDynamicInfo', 'JQuickNav', 'JProjectCard', 'JRadioButton',
    'JTabs', 'JGrid', 'JCustomEchart', 'online', 'design',
}
_FILTER_MODE_RULE = {'1': 'EQ', '2': 'LIKE', '3': 'GT', '4': 'LT', '5': 'LLIKE', '6': 'RLIKE'}
_FILTER_MODE_ALIAS = {
    '等于': '1', '是': '1', 'eq': '1', '=': '1',
    '包含': '2', 'like': '2', '在范围内': '2',
    '大于': '3', '晚于': '3', 'gt': '3', '>': '3',
    '小于': '4', '早于': '4', 'lt': '4', '<': '4',
    '开头是': '5', '开头为': '5',
    '结尾是': '6', '结尾为': '6',
}
_FILTER_SYSTEM_OPTIONS = [
    {'name': '创建人', 'model': 'create_by', 'type': 'select-user', 'options': {}},
    {'name': '修改人', 'model': 'update_by', 'type': 'select-user', 'options': {}},
    {'name': '修改时间', 'model': 'update_time', 'type': 'date', 'options': {}},
    {'name': '创建时间', 'model': 'create_time', 'type': 'date', 'options': {}},
    {'name': '流程状态', 'model': 'bpm_status', 'type': 'select',
     'options': {'dictCode': 'bpm_status', 'remote': 'dict'}},
]


def _load_filter_payload(args):
    """add-filter specs：{title,place,w,h,showQueryBtn,charts:[图表标题],conditions:[{field,label,mode,value?}]}"""
    path = (getattr(args, 'specs_file', None) or '').strip()
    raw = getattr(args, 'specs', None)
    if path:
        try:
            raw = _read_json_text(path)
        except OSError as e:
            print('--specs-file 读取失败: %s' % e)
            sys.exit(1)
        print('SPECS_FILE=%s' % path)
    if raw is None or not str(raw).strip():
        print('必须提供 --specs-file（推荐）或 --specs')
        sys.exit(1)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print('--specs JSON 解析失败: %s' % e)
        print('NOTE=PowerShell 传 --specs 会吃掉双引号。必须 Write JSON 文件后用 --specs-file')
        sys.exit(1)
    if not isinstance(data, dict):
        print('--specs 必须是对象 {title,place,charts:[图表标题],conditions:[{field,label,mode}]}')
        sys.exit(1)
    charts = data.get('charts') or data.get('chartList')
    if not isinstance(charts, list) or not charts:
        print('--specs 缺少 charts（联动图表标题数组，如 ["本周"]）')
        sys.exit(1)
    conds = data.get('conditions') or data.get('conditionFields')
    if not isinstance(conds, list) or not conds:
        print('--specs 缺少 conditions（如 [{"field":"名称","label":"名称","mode":"2"}]）')
        sys.exit(1)
    data['charts'] = charts
    data['conditions'] = conds
    return data


def _norm_filter_mode(raw_mode, field_type, widget_type):
    m = str(raw_mode or '').strip()
    if m in _FILTER_MODE_ALIAS:
        m = _FILTER_MODE_ALIAS[m]
    else:
        ml = m.lower()
        if ml in _FILTER_MODE_ALIAS:
            m = _FILTER_MODE_ALIAS[ml]
    if m not in _FILTER_MODE_RULE:
        if field_type == 'string' and widget_type in ('input', 'textarea'):
            m = '2'          # 文本默认 包含(LIKE)
        else:
            m = '1'          # 其余默认 等于
    return m


def cmd_add_filter(args):
    """已有仪表盘加 JFilterQuery 查询条件并联动统计图：
    定位应用/页面 → 按标题匹配统计图（排除 UI 组件）→ 表单字段取自联动图表 config →
    构建扁平 config（conditionFields+filter+relationChartList+chartData+linkageConfig）→
    comp/add + saveCompToPage 同一进程。已有页禁止 save_page（会换 pageCompId 弄坏联动）。"""
    t0 = time.time()
    payload = _load_filter_payload(args)
    title = (getattr(args, 'title', None) or payload.get('title') or '查询条件').strip()
    place = (getattr(args, 'place', None) or payload.get('place') or 'above').strip() or 'above'
    if place not in ('above', 'bottom'):
        print('place 只能 above（联动图表上方，默认）/ bottom（页面底部）')
        sys.exit(1)
    grid_w = int(payload.get('w') or 24)
    grid_h = int(payload.get('h') or 10)
    show_btn = payload.get('showQueryBtn')
    show_btn = True if show_btn is None else bool(show_btn)
    query_after = payload.get('queryAfterShow', False) or payload.get('queryAfterShowData', False)

    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    page_id, _page_name = _resolve_page_id(args, app_id)
    args.page_id = page_id

    page = bi_utils.query_page(page_id)
    tmpl = page.get('template') or []
    if isinstance(tmpl, str):
        try:
            tmpl = json.loads(tmpl)
        except Exception:
            tmpl = []
    update_count = page.get('updateCount')
    print('UPDATE_COUNT=%s EXISTING=%d' % (update_count, len(tmpl)))

    # 1. 按标题匹配统计图表（排除 noView/UI 组件；联动目标无需任何修改）
    stat = []
    for it in tmpl:
        comp_type = it.get('component') or ''
        if comp_type in _FILTER_NO_VIEW or not it.get('pageCompId'):
            continue
        ent = {}
        try:
            ent = (bi_utils._request('GET', '/drag/page/comp/queryById',
                                     params={'id': it.get('pageCompId')}) or {}).get('result') or {}
        except Exception:
            ent = {}
        outer, inner_cfg = _unwrap_comp_config(ent)
        cfg = inner_cfg if inner_cfg else outer
        opt_title = (((cfg.get('option') or {}).get('title') or {}).get('text') or '')
        # 透视 option.title 固定「表格」，匹配优先 componentName（用户 specs title）
        comp_name = (it.get('componentName') or '') or ''
        label = comp_name or opt_title or '未命名'
        aliases = {x for x in (label, comp_name, opt_title) if x}
        stat.append({'item': it, 'cfg': cfg, 'label': label, 'aliases': aliases,
                     'i': str(it.get('i') or ''),
                     'table': str(cfg.get('tableName') or ''),
                     'formType': str(cfg.get('formType') or cfg.get('type') or 'design'),
                     'app': str(cfg.get('appId') or '') or app_id})

    def _chart_hit(s, kw):
        for a in s.get('aliases') or {s['label']}:
            if kw == a or kw in a or a in kw:
                return True
        return False

    for kw in [str(c or '').strip() for c in payload['charts']]:
        if not kw:
            continue
        cands = [s for s in stat if _chart_hit(s, kw)]
        if not cands:
            print('CHART_NOT_FOUND keyword=%s' % kw)
            for s in stat:
                print('CAND i=%s label=%s aliases=%s comp=%s table=%s' % (
                    s['i'], s['label'], ','.join(sorted(s.get('aliases') or [])),
                    s['item'].get('component'), s['table']))
            sys.exit(1)
        if len(set(c['i'] for c in cands)) > 1:
            print('CHART_AMBIGUOUS keyword=%s（同名多张，请用 componentName / option.title.text 精确定位）' % kw)
            for c in cands:
                print('CAND i=%s label=%s table=%s' % (c['i'], c['label'], c['table']))
            sys.exit(1)
    matched, seen = [], set()
    for kw in [str(c or '').strip() for c in payload['charts']]:
        if not kw:
            continue
        hit = next(s for s in stat if _chart_hit(s, kw))
        if hit['i'] not in seen:
            seen.add(hit['i'])
            matched.append(hit)
    tables = sorted({(s['app'], s['table']) for s in matched})
    if len(tables) > 1:
        print('CHART_MIXED_FORMS tables=%s' % tables)
        print('NOTE=查询条件只支持联动同一张工作表的图表；不同表请分两次 add-filter')
        sys.exit(1)
    fields_app, table_code = tables[0] if tables else (app_id, '')
    if not table_code:
        print('CHART_NO_FORM=联动图表未绑定表单（非 dataType=4）')
        sys.exit(1)
    for s in matched:
        print('CHART_MATCH i=%s label=%s table=%s formType=%s y=%s' % (
            s['i'], s['label'], s['table'], s['formType'], s['item'].get('y')))

    # 2. 表单字段：跨应用表单先切 X-Low-App-ID，取完切回看板应用
    if str(fields_app) != str(app_id):
        bi_utils.init_api(args.api_base, args.token, extra_headers={
            'X-Low-App-ID': fields_app, 'X-Tenant-Id': str(args.tenant_id)})
    fields_resp = bi_utils._request('GET', '/desform/api/fields/' + table_code)
    if str(fields_app) != str(app_id):
        bi_utils.init_api(args.api_base, args.token, extra_headers={
            'X-Low-App-ID': app_id, 'X-Tenant-Id': str(args.tenant_id)})
    raw_fields = ((fields_resp or {}).get('result') or {}).get('fields') or []
    norm_fields = qc.parse_design_fields(raw_fields)
    if not norm_fields:
        print('CHART_NO_FIELDS table=%s' % table_code)
        sys.exit(1)
    all_options = []
    for nf in norm_fields:
        opts = copy.deepcopy(nf.get('options') or {})
        opts.pop('dataType', None)
        all_options.append({'name': nf['fieldTxt'], 'model': nf['fieldName'],
                            'type': nf['widgetType'], 'options': opts})
    all_options = all_options + list(_FILTER_SYSTEM_OPTIONS)
    print('FORM_CODE=%s FORM_FIELDS=%d OPTIONS=%d' % (table_code, len(norm_fields), len(all_options)))

    # 3. 条件解析（显示名/model 均可；文本默认 包含 mode=2）
    cond_defs = []
    for i, spec in enumerate(payload['conditions']):
        kw = str(spec.get('field') or spec.get('fieldName') or spec.get('name') or '').strip()
        if not kw:
            print('conditions[%d] 缺少 field（字段显示名或 model）' % i)
            sys.exit(1)
        hits = [f for f in norm_fields if kw == f['fieldName'] or kw == f['fieldTxt']]
        if not hits:
            hits = [f for f in norm_fields if kw in f['fieldTxt'] or f['fieldTxt'] in kw]
        if not hits:
            print('COND_FIELD_NOT_FOUND idx=%d keyword=%s' % (i, kw))
            for f in norm_fields:
                print('CAND %s\t%s\t%s' % (f['fieldName'], f['fieldTxt'], f['widgetType']))
            sys.exit(1)
        f = hits[0]
        mode = _norm_filter_mode(spec.get('mode'), f['fieldType'], f['widgetType'])
        label = str(spec.get('label') or spec.get('title') or f['fieldTxt']).strip()
        raw_val = spec.get('value', spec.get('defVal', spec.get('fieldValue', None)))
        if raw_val is None or raw_val == '':
            val = ''
            def_val = None
        else:
            val = str(raw_val)
            def_val = raw_val if not isinstance(raw_val, (dict, list)) else val
        cond_defs.append({'f': f, 'mode': mode, 'label': label, 'val': val, 'defVal': def_val})
        print('COND[%d] field=%s label=%s widget=%s fieldType=%s mode=%s value=%s' % (
            i, f['fieldName'], label, f['widgetType'], f['fieldType'], mode, val))

    # 4. 构建 JFilterQuery 扁平 config（chartData 内部是 JSON 字符串；联动全在自身 linkageConfig）
    condition_fields = []
    for cd in cond_defs:
        f = cd['f']
        condition_fields.append({
            'fieldName': f['fieldName'], 'fieldTxt': f['fieldTxt'],
            'fieldType': f['fieldType'], 'widgetType': f['widgetType'],
            'rule': _FILTER_MODE_RULE[cd['mode']], 'condition': cd['mode'],
            'val': cd['val'], 'fieldValue': cd['val'],
            'options': copy.deepcopy(f.get('options') or {}),
            'fieldShow': True, 'customDateType': '',
        })
    chart_data_list = []
    for cd in cond_defs:
        chart_data_list.append({
            'id': 'query_' + str(uuid.uuid4()),
            'label': cd['label'],
            'type': cd['f']['widgetType'],
            'fieldList': [cd['f']['fieldName'] for _s in matched],   # 顺序对应 relationChartList
            'queryMode': cd['mode'],
            'defVal': cd['defVal'], 'beginValue': None, 'endValue': None,
        })
    relation_chart_list = [{
        'code': s['table'], 'options': copy.deepcopy(all_options), 'checked': 1,
        'label': s['label'], 'type': s['formType'], 'key': s['i'],
    } for s in matched]
    linkage_config = [{
        'linkageId': s['i'],
        'linkageConfig': [{'src': cd['f']['fieldName'], 'tgt': cd['f']['fieldName']} for cd in cond_defs],
    } for s in matched]
    filter_config = {
        'dataType': 1, 'timeOut': 0,
        'isEnableFilterBtn': show_btn,
        'isQueryAfterShowData': query_after,
        'conditionFields': condition_fields,
        'filter': {'conditionMode': 'and', 'conditionFields': condition_fields,
                   'queryField': cond_defs[0]['f']['fieldName'],
                   'customTime': [], 'queryRange': 'all'},
        'relationChartList': relation_chart_list,
        'chartData': json.dumps(chart_data_list, ensure_ascii=False),
        'linkageConfig': linkage_config,
        'size': {'width': grid_w * 75, 'height': grid_h * 11},
        'background': '#FFFFFF', 'borderColor': '#E8E8E8',
        'chart': {'subclass': 'JFilterQuery', 'category': 'Common'},
        'option': {
            'title': {'show': True, 'text': title, 'textStyle': {'color': '#464646', 'fontSize': 14}},
            'card': {'rightHref': '', 'size': 'default', 'extra': '', 'title': ''},
        },
    }

    # 5. 布局：above 取联动图表最小 y 行并下移被占用组件；bottom 追加到底部
    if place == 'above':
        filter_y = min(int(s['item'].get('y') or 0) for s in matched)
        for item in tmpl:
            if int(item.get('y') or 0) + int(item.get('h') or 0) > filter_y:
                item['y'] = int(item.get('y') or 0) + grid_h
                if 'pcY' in item:
                    item['pcY'] = int(item.get('pcY') or 0) + grid_h
    else:
        filter_y = 0
        for item in tmpl:
            filter_y = max(filter_y, int(item.get('y') or 0) + int(item.get('h') or 0))

    # 6. comp/add + saveCompToPage（template 必须 json.dumps 成字符串，传数组报 String from Array）
    add_resp = bi_utils._request('POST', '/drag/page/comp/add', data={
        'pageId': page_id,
        'component': 'JFilterQuery',
        'config': json.dumps(filter_config, ensure_ascii=False),
    })
    if not add_resp.get('success'):
        print('comp/add 失败: %s' % add_resp.get('message'))
        sys.exit(1)
    page_comp_id = str((add_resp.get('result') or {}).get('id') or add_resp.get('result') or '')
    if not page_comp_id or page_comp_id == 'None':
        print('comp/add 未返回 id: %s' % json.dumps(add_resp, ensure_ascii=False)[:500])
        sys.exit(1)
    print('PAGE_COMP_ID=%s' % page_comp_id)

    new_item = {'w': grid_w, 'h': grid_h, 'i': str(uuid.uuid4()), 'x': 0, 'y': filter_y,
                'orderNum': 0, 'pageCompId': page_comp_id, 'component': 'JFilterQuery',
                'componentName': title, 'visible': True,
                'pcX': 0, 'pcY': filter_y, 'pcW': grid_w}
    new_meta = _template_meta(new_item)
    clean = ([new_meta] + [_template_meta(it) for it in tmpl]) if place == 'above' \
        else ([_template_meta(it) for it in tmpl] + [new_meta])
    save_resp = bi_utils._request('POST', '/drag/page/saveCompToPage', data={
        'id': page_id,
        'template': json.dumps(clean, ensure_ascii=False),
        'updateCount': update_count,
    })
    if not save_resp.get('success'):
        print('saveCompToPage 失败: %s' % save_resp.get('message'))
        print('NOTE=template 必须 json.dumps 成字符串；禁止 save_page 重建整页')
        sys.exit(1)

    print('ADDED=JFilterQuery conditions=%d charts=%d place=%s showQueryBtn=%s' % (
        len(cond_defs), len(matched), place, show_btn))
    share = '%s/drag/share/%s/%s' % (_frontend_base(args.api_base), app_id, page_id)
    print('APP_ID=%s' % app_id)
    print('PAGE_ID=%s' % page_id)
    print('SHARE_URL=%s' % share)
    print('耗时: %.1fs' % (time.time() - t0))


# ── edit-filter（已有 JFilterQuery 改匹配方式 / 默认值；≠ add-filter 新建、≠ set-chart-filter 图内筛选）──
def _filter_field_hit(cd_or_item, keyword):
    """命中查询条件字段：显示 label / fieldTxt / fieldName。"""
    kw = str(keyword or '').strip()
    if not kw:
        return False
    cands = []
    if isinstance(cd_or_item, dict):
        cands = [
            cd_or_item.get('label'), cd_or_item.get('fieldTxt'),
            cd_or_item.get('fieldName'), cd_or_item.get('title'),
        ]
    for c in cands:
        s = str(c or '').strip()
        if s and (kw == s or kw in s or s in kw):
            return True
    return False


def _patch_filter_condition(cd, mode=None, value=None, clear_value=False):
    """同步写 conditionFields 条目：rule/condition + val/fieldValue。"""
    changed = []
    if mode:
        cd['condition'] = mode
        cd['rule'] = _FILTER_MODE_RULE.get(mode, cd.get('rule') or 'EQ')
        changed.append('mode=%s/%s' % (mode, cd['rule']))
    if clear_value:
        cd['val'] = ''
        cd['fieldValue'] = ''
        changed.append('value=')
    elif value is not None:
        v = str(value)
        cd['val'] = v
        cd['fieldValue'] = v
        changed.append('value=%s' % v)
    return changed


def _patch_filter_chart_data_item(item, mode=None, value=None, clear_value=False):
    """同步写 chartData 条目：queryMode + defVal（面板默认值权威在此）。"""
    changed = []
    if mode:
        item['queryMode'] = mode
        changed.append('queryMode=%s' % mode)
    if clear_value:
        item['defVal'] = None
        changed.append('defVal=None')
    elif value is not None:
        item['defVal'] = value if not isinstance(value, (dict, list)) else str(value)
        changed.append('defVal=%s' % item['defVal'])
    return changed


def cmd_edit_filter(args):
    """已有仪表盘改 JFilterQuery 条件：匹配方式（包含→等于）和/或默认值。
    必须同步 conditionFields + filter.conditionFields + chartData；有 pageCompId 时先 comp/edit。
    打印 FILTER_EDITED= 即停；禁止 add-filter 重建、禁止手写临时脚本。"""
    t0 = time.time()
    field_kw = (getattr(args, 'field', None) or '').strip()
    if not field_kw:
        print('必须提供 --field（条件显示名/字段名，如 产品名称 / 名称）')
        sys.exit(1)
    mode_raw = getattr(args, 'mode', None)
    has_mode = mode_raw is not None and str(mode_raw).strip() != ''
    clear_value = bool(getattr(args, 'clear_value', False))
    value_arg = getattr(args, 'value', None)  # None=未传；''=显式清空（也可用 --clear-value）
    value_set = clear_value or (value_arg is not None)
    if not has_mode and not value_set:
        print('必须提供 --mode 和/或 --value（或 --clear-value）')
        sys.exit(1)

    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    # 优先 --page-name：memory 里的 pageId/appId 易过期（新疆兵团应用1 曾轮换）
    page_id, page_name = _resolve_page_id(args, app_id)
    args.page_id = page_id

    try:
        page = bi_utils.query_page(page_id)
    except Exception as e:
        print('PAGE_QUERY_FAIL pageId=%s err=%s' % (page_id, e))
        print('NOTE=过期 memory pageId/错租户时：去掉 --page-id，改 --page-name；错 app 则 --app-name')
        sys.exit(1)
    tmpl = page.get('template') or []
    if isinstance(tmpl, str):
        try:
            tmpl = json.loads(tmpl)
        except Exception:
            tmpl = []

    name_kw = (getattr(args, 'name', None) or getattr(args, 'comp_name', None) or '').strip()
    filters = []
    for it in tmpl:
        if (it.get('component') or '') != 'JFilterQuery':
            continue
        cfg = it.get('config') or {}
        if isinstance(cfg, str):
            try:
                cfg = json.loads(cfg)
            except Exception:
                cfg = {}
            it['config'] = cfg
        filters.append(it)

    if name_kw:
        filters = [f for f in filters
                   if name_kw == (f.get('componentName') or '')
                   or name_kw in (f.get('componentName') or '')]
    if not filters:
        print('FILTER_PANEL_NOT_FOUND name=%s' % (name_kw or '(any)'))
        for it in tmpl:
            if it.get('component') == 'JFilterQuery':
                print('CAND name=%s i=%s' % (it.get('componentName'), it.get('i')))
        sys.exit(1)

    # 在候选面板中找含该字段的条件
    hits = []
    for it in filters:
        cfg = it.get('config') or {}
        cds = list(cfg.get('conditionFields') or [])
        ch = cfg.get('chartData')
        if isinstance(ch, str):
            try:
                ch_list = json.loads(ch)
            except Exception:
                ch_list = []
        else:
            ch_list = ch if isinstance(ch, list) else []
        cd_hits = [i for i, cd in enumerate(cds) if _filter_field_hit(cd, field_kw)]
        item_hits = [i for i, item in enumerate(ch_list) if _filter_field_hit(item, field_kw)]
        if cd_hits or item_hits:
            hits.append((it, cfg, cds, ch_list, isinstance(ch, str), cd_hits, item_hits))

    if not hits:
        print('FILTER_FIELD_NOT_FOUND field=%s panels=%d' % (field_kw, len(filters)))
        for it in filters:
            cfg = it.get('config') or {}
            for cd in (cfg.get('conditionFields') or []):
                print('CAND panel=%s fieldTxt=%s fieldName=%s' % (
                    it.get('componentName'), cd.get('fieldTxt'), cd.get('fieldName')))
            ch = cfg.get('chartData')
            if isinstance(ch, str):
                try:
                    ch = json.loads(ch)
                except Exception:
                    ch = []
            if isinstance(ch, list):
                for item in ch:
                    print('CAND panel=%s label=%s' % (it.get('componentName'), item.get('label')))
        sys.exit(1)
    if len(hits) > 1 and not name_kw:
        print('FILTER_AMBIGUOUS field=%s count=%d（加 --name 面板标题精确定位）' % (
            field_kw, len(hits)))
        for it, _cfg, _cds, _ch, _ws, _a, _b in hits:
            print('CAND name=%s i=%s' % (it.get('componentName'), it.get('i')))
        sys.exit(1)

    it, cfg, cds, ch_list, chart_was_str, cd_hits, item_hits = hits[0]
    mode = None
    if has_mode:
        # 取首条命中字段的类型做默认回落
        sample = cds[cd_hits[0]] if cd_hits else {}
        mode = _norm_filter_mode(
            mode_raw,
            sample.get('fieldType') or 'string',
            sample.get('widgetType') or 'input')

    changes = []
    # conditionFields（顶层）
    for idx in cd_hits:
        changes.extend(_patch_filter_condition(
            cds[idx], mode=mode,
            value=None if clear_value else (value_arg if value_set else None),
            clear_value=clear_value if value_set else False))
    # filter.conditionFields（可能是拷贝）
    filt = cfg.setdefault('filter', {})
    fcds = filt.get('conditionFields')
    if isinstance(fcds, list) and fcds is not cds:
        for cd in fcds:
            if _filter_field_hit(cd, field_kw):
                changes.extend(_patch_filter_condition(
                    cd, mode=mode,
                    value=None if clear_value else (value_arg if value_set else None),
                    clear_value=clear_value if value_set else False))
    elif not fcds:
        filt['conditionFields'] = cds

    # chartData：优先 label 命中；否则用 fieldName↔fieldList 对齐；单条件面板兜底 [0]
    if item_hits:
        idxs = item_hits
    elif cd_hits and ch_list:
        fnames = {(cds[i].get('fieldName') or '') for i in cd_hits}
        idxs = [i for i, item in enumerate(ch_list)
                if any(fn and fn in (item.get('fieldList') or []) for fn in fnames)]
        if not idxs:
            idxs = [0] if len(ch_list) == 1 else []
    else:
        idxs = []
    for idx in idxs:
        if 0 <= idx < len(ch_list):
            changes.extend(_patch_filter_chart_data_item(
                ch_list[idx], mode=mode,
                value=None if clear_value else (value_arg if value_set else None),
                clear_value=clear_value if value_set else False))
    if ch_list is not None:
        cfg['chartData'] = json.dumps(ch_list, ensure_ascii=False) if chart_was_str else ch_list

    pcid = it.get('pageCompId') or it.get('id')
    if pcid:
        edit_resp = bi_utils._request('POST', '/drag/page/comp/edit', data={
            'id': pcid,
            'component': 'JFilterQuery',
            'config': json.dumps(cfg, ensure_ascii=False),
        })
        if not edit_resp.get('success'):
            print('COMP_EDIT_FAIL=%s' % json.dumps(edit_resp, ensure_ascii=False)[:400])
            sys.exit(1)
        print('COMP_EDIT=ok pageCompId=%s' % pcid)

    bi_utils._page_components[page_id] = tmpl
    bi_utils.save_page(page_id)
    print('FILTER_EDITED=%s field=%s' % (it.get('componentName') or 'JFilterQuery', field_kw))
    print('CHANGES=%s' % ';'.join(changes) if changes else 'CHANGES=')
    print('PAGE_ID=%s' % page_id)
    print('PAGE_NAME=%s' % (page_name or page.get('name') or ''))
    print('APP_ID=%s' % app_id)
    print('耗时: %.1fs' % (time.time() - t0))


# ── rename-page ───────────────────────────────────────────────────────────
_QUERY_RANGE_ALIAS = {
    '全部': 'all', '所有': 'all', 'all': 'all',
    '本月': 'month', 'month': 'month',
    '上月': 'preMonth', 'preMonth': 'preMonth',
    '下月': 'nextMonth', 'nextMonth': 'nextMonth',
    '本周': 'week', 'week': 'week',
    '上周': 'preWeek', 'preWeek': 'preWeek',
    '下周': 'nextWeek', 'nextWeek': 'nextWeek',
    '本年': 'year', '今年': 'year', 'year': 'year',
    '去年': 'preYear', '上年': 'preYear', 'preYear': 'preYear',
    '明年': 'nextYear', 'nextYear': 'nextYear',
    '今日': 'today', '今天': 'today', 'today': 'today',
    '昨日': 'yesterday', '昨天': 'yesterday', 'yesterday': 'yesterday',
    '明天': 'tomorrow', '明日': 'tomorrow', 'tomorrow': 'tomorrow',
    '近7天': 'last7days', '最近7天': 'last7days', 'last7days': 'last7days',
    '近30天': 'last30days', '最近30天': 'last30days', 'last30days': 'last30days',
    '自定义': 'custom', 'custom': 'custom',
}


def _norm_query_range(raw):
    s = (raw or '').strip()
    if not s:
        return None
    hit = _QUERY_RANGE_ALIAS.get(s) or _QUERY_RANGE_ALIAS.get(s.lower())
    if hit:
        return hit
    if s in qc.QUERY_RANGE:
        return s
    if '全部' in s or '所有' in s:
        return 'all'
    if '上月' in s:
        return 'preMonth'
    if '下月' in s:
        return 'nextMonth'
    if '本月' in s:
        return 'month'
    if '上周' in s:
        return 'preWeek'
    if '下周' in s:
        return 'nextWeek'
    if '本周' in s:
        return 'week'
    if '去年' in s or '上年' in s:
        return 'preYear'
    if '明年' in s:
        return 'nextYear'
    if '本年' in s or '今年' in s:
        return 'year'
    if '明天' in s or '明日' in s:
        return 'tomorrow'
    if '自定义' in s:
        return 'custom'
    if '近7' in s or '最近7' in s:
        return 'last7days'
    if '近30' in s or '最近30' in s:
        return 'last30days'
    return None


def _chart_has_calc(cfg):
    """config 是否含计算值（calcFields 或 valueFields.widgetType=calcVal / $model-N$）。"""
    for v in (cfg.get('calcFields') or []):
        if isinstance(v, dict) and (
                v.get('widgetType') == 'calcVal'
                or str(v.get('fieldName') or '').startswith('$')):
            return True
    for v in (cfg.get('valueFields') or []):
        if isinstance(v, dict) and (
                v.get('widgetType') == 'calcVal'
                or str(v.get('fieldName') or '').startswith('$')):
            return True
    return False


def _find_chart_for_rebind(tmpl, name=None, match_dim=None, comp=None, match_calc=False):
    """按 componentName / 当前维度 / 可选计算值图 + component 命中 QQY 统计图。"""
    name = (name or '').strip()
    match_dim = (match_dim or '').strip()
    comp = (comp or '').strip()
    if comp:
        comp = _norm_comp_alias(comp) or comp
    match_calc = bool(match_calc)
    cands = []
    for c in tmpl or []:
        ctype = c.get('component') or ''
        cfg = c.get('config') or {}
        if isinstance(cfg, str):
            try:
                cfg = json.loads(cfg)
            except Exception:
                cfg = {}
        is_qqy = (
            cfg.get('dataType') == 4
            or 'nameFields' in cfg
            or 'valueFields' in cfg
        )
        if not is_qqy:
            continue
        if comp and ctype != comp:
            continue
        cname = c.get('componentName') or ''
        title_txt = (((cfg.get('option') or {}).get('title') or {}).get('text') or '')
        if name and cname == name:
            cands.append(c)
            continue
        if name and name in cname:
            cands.append(c)
            continue
        if name and title_txt and name in title_txt:
            cands.append(c)
            continue
        if match_dim and not name:
            nfs = cfg.get('nameFields') or []
            for nf in nfs:
                if not isinstance(nf, dict):
                    continue
                fn = nf.get('fieldName') or ''
                ft = nf.get('fieldTxt') or ''
                if match_dim in (fn, ft):
                    cands.append(c)
                    break
                if match_dim in ('create_time', '创建时间') and fn == 'create_time':
                    cands.append(c)
                    break
        if match_calc and not name and not match_dim and _chart_has_calc(cfg):
            cands.append(c)
    # de-dup by i
    seen = set()
    out = []
    for c in cands:
        key = c.get('i') or id(c)
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def _parse_custom_time(raw):
    """解析 --custom-time：支持 'YYYY-MM-DD,YYYY-MM-DD' 或 JSON 数组。"""
    s = (raw or '').strip()
    if not s:
        return None
    if s.startswith('['):
        try:
            arr = json.loads(s)
        except Exception:
            return None
        if isinstance(arr, list) and len(arr) >= 2:
            return [str(arr[0]).strip(), str(arr[1]).strip()]
        return None
    parts = [p.strip() for p in s.replace('到', ',').replace('~', ',').split(',') if p.strip()]
    if len(parts) >= 2:
        return [parts[0], parts[1]]
    return None


def cmd_rebind_chart(args):
    """已有 QQY 统计图改维度 / 数值 / 查询范围 / 数据源表 / 双轴左右轴（含跨应用）。保留类型与布局。
    禁止 grep 脚本 / 手写 py -c 一次性改盘。"""
    t0 = time.time()
    dim_tok = (getattr(args, 'dim', None) or '').strip()
    val_tok = (getattr(args, 'val', None) or '').strip()
    grp_tok = (getattr(args, 'grp', None) or '').strip()
    assist_y_tok = (getattr(args, 'assist_y', None) or '').strip()
    assist_type_tok = (getattr(args, 'assist_type', None) or '').strip()
    qr_raw = (getattr(args, 'query_range', None) or '').strip()
    dg_raw = (getattr(args, 'date_group', None) or '').strip()
    ct_raw = (getattr(args, 'custom_time', None) or '').strip()
    new_form_code = (getattr(args, 'form_code', None) or '').strip()
    new_form_name = (getattr(args, 'form_name', None) or '').strip()
    form_app_id = (getattr(args, 'form_app_id', None) or '').strip()
    form_app_name = (getattr(args, 'form_app_name', None) or '').strip()
    want_form = bool(new_form_code or new_form_name or form_app_id or form_app_name)
    custom_time = _parse_custom_time(ct_raw) if ct_raw else None
    if ct_raw and not custom_time:
        print('customTime 非法: %s 期望 begin,end 如 2026-08-01,2026-09-03' % ct_raw)
        sys.exit(1)
    # 只给了起止日 → 默认走 custom
    if custom_time and not qr_raw:
        qr_raw = 'custom'
    if (not dim_tok and not val_tok and not grp_tok and not assist_y_tok
            and not assist_type_tok and not qr_raw and not want_form):
        print('必须至少提供 --dim / --val / --grp / --assist-y / --assist-type / '
              '--query-range / --form-name(--form-code) 之一')
        sys.exit(1)
    if want_form and (not new_form_code and not new_form_name):
        print('换数据源必须提供 --form-name 或 --form-code')
        sys.exit(1)
    if want_form and (not dim_tok or not val_tok):
        print('换数据源必须同时提供 --dim 与 --val（新表字段）')
        sys.exit(1)
    query_range = None
    if qr_raw:
        query_range = _norm_query_range(qr_raw)
        if not query_range:
            print('queryRange 非法: %s 允许=%s 或中文别名(全部/本月/本周/自定义…)' % (
                qr_raw, ','.join(qc.QUERY_RANGE)))
            sys.exit(1)
    if query_range == 'custom' and not custom_time:
        print('queryRange=custom 必须配 --custom-time BEGIN,END')
        sys.exit(1)
    # 换表未点名范围 → 默认 all（旧 week/month 对主数据易空）
    if want_form and query_range is None:
        query_range = 'all'
        print('NOTE=换表未点名 --query-range，默认 all')
    date_group = ''
    if dg_raw:
        date_group = _norm_date_group(dg_raw)
        if not date_group:
            print('dateGroup 非法: %s 允许=1..7 或按日/按月/按年' % dg_raw)
            sys.exit(1)

    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    page_id, page_name = _resolve_page_id(args, app_id)

    page = bi_utils.query_page(page_id)
    tmpl = page.get('template') or []
    if isinstance(tmpl, str):
        tmpl = json.loads(tmpl)

    name_arg = getattr(args, 'name', None)
    match_dim_arg = getattr(args, 'match_dim', None)
    comp_arg = getattr(args, 'comp', None)
    hits = _find_chart_for_rebind(
        tmpl, name=name_arg, match_dim=match_dim_arg, comp=comp_arg)
    # 仅 --comp（口语「双轴图」无标题）：_find_chart_for_rebind 不会因类型单独入选
    if (not hits and (comp_arg or '').strip()
            and not (name_arg or '').strip() and not (match_dim_arg or '').strip()):
        want = (comp_arg or '').strip()
        for c in tmpl or []:
            if (c.get('component') or '') != want:
                continue
            cfg0 = c.get('config') or {}
            if isinstance(cfg0, str):
                try:
                    cfg0 = json.loads(cfg0)
                except Exception:
                    cfg0 = {}
            if (cfg0.get('dataType') == 4
                    or 'nameFields' in cfg0
                    or 'valueFields' in cfg0
                    or 'assistYFields' in cfg0
                    or want in ('DoubleLineBar', 'JBar', 'JLine', 'JPie',
                                'JHorizontalBar', 'JStackBar', 'JMultipleBar',
                                'JMultipleLine', 'JArea', 'JSmoothLine', 'JStepLine')):
                hits.append(c)
    if not hits:
        print('CHART_NOT_FOUND name=%s match_dim=%s comp=%s' % (
            name_arg or '', match_dim_arg or '', comp_arg or ''))
        for c in tmpl:
            cfg = c.get('config') or {}
            if isinstance(cfg, str):
                try:
                    cfg = json.loads(cfg)
                except Exception:
                    cfg = {}
            nf = (cfg.get('nameFields') or [{}])
            n0 = nf[0] if nf else {}
            print('CAND\t%s\t%s\tdim=%s' % (
                c.get('componentName'), c.get('component'),
                (n0.get('fieldTxt') or n0.get('fieldName') or '')))
        sys.exit(1)
    if len(hits) > 1:
        print('CHART_AMBIGUOUS count=%d' % len(hits))
        for c in hits:
            print('CAND\t%s\t%s' % (c.get('componentName'), c.get('component')))
        sys.exit(1)

    comp = hits[0]
    cfg = comp.get('config') or {}
    if isinstance(cfg, str):
        cfg = json.loads(cfg)
        comp['config'] = cfg
    old_form_code = (cfg.get('tableName') or cfg.get('designFormCode')
                     or cfg.get('formCode') or cfg.get('formId') or '').strip()
    form_code = old_form_code
    if not form_code and not want_form:
        print('CHART_NO_FORM componentName=%s' % (comp.get('componentName') or ''))
        sys.exit(1)

    # 解析目标表单应用（跨应用换表）
    if form_app_name and not form_app_id:
        other = type('A', (), {})()
        other.tenant_id = args.tenant_id
        other.app_id = ''
        other.app_name = form_app_name
        form_app_id = _resolve_app_id(other)
        print('FORM_APP_ID=%s' % form_app_id)
    if not form_app_id:
        form_app_id = (cfg.get('appId') or '').strip() if want_form else app_id
    if not form_app_id:
        form_app_id = app_id
    cross = str(form_app_id) != str(app_id)

    # 加载字段：换表则切到表单应用解析；禁止裸读 fields API 不 parse
    class _FArgs(object):
        pass
    fa = _FArgs()
    if want_form:
        bi_utils.init_api(args.api_base, args.token, extra_headers={
            'X-Low-App-ID': form_app_id, 'X-Tenant-Id': str(args.tenant_id)})
        form_code, resolved_name = _resolve_form(
            form_app_id, new_form_code, new_form_name,
            prefer_type=getattr(args, 'form_type', None))
        fa.form_code = form_code
        fa.form_name = resolved_name or new_form_name
        fa.form_type = getattr(_resolve_form, 'last_type', None) or getattr(args, 'form_type', None) or 'design'
    else:
        fa.form_code = form_code
        fa.form_name = cfg.get('formName') or ''
        cfg_type = cfg.get('type') or ''
        fa.form_type = cfg_type if cfg_type in ('aggregation', 'design', 'online') else (
            cfg.get('formType') or 'design')
        # 旧图可能已是跨应用：读字段时切到 cfg.appId
        src_app = (cfg.get('appId') or '').strip() or app_id
        if str(src_app) != str(app_id):
            bi_utils.init_api(args.api_base, args.token, extra_headers={
                'X-Low-App-ID': src_app, 'X-Tenant-Id': str(args.tenant_id)})
    fields, form_name, form_type = _load_fields(fa)
    print('FORM_CODE=%s FORM_NAME=%s FORM_TYPE=%s FIELDS=%d' % (
        form_code, form_name, form_type, len(fields)))
    # 写回看板应用头，供 save_page
    bi_utils.init_api(args.api_base, args.token, extra_headers={
        'X-Low-App-ID': app_id, 'X-Tenant-Id': str(args.tenant_id)})

    old_nf = copy.deepcopy(cfg.get('nameFields') or [])
    old_vf = copy.deepcopy(cfg.get('valueFields') or [])
    old_tf = copy.deepcopy(cfg.get('typeFields') or [])
    old_ay = copy.deepcopy(cfg.get('assistYFields') or [])
    old_at = copy.deepcopy(cfg.get('assistTypeFields') or [])
    old_qr = ((cfg.get('filter') or {}).get('queryRange') or '')

    changes = []
    if want_form:
        cfg['formId'] = form_code
        cfg['formName'] = form_name
        cfg['tableName'] = form_code
        cfg['formType'] = form_type or 'design'
        cfg['appId'] = form_app_id
        if cross:
            cfg.pop('appType', None)
            cfg.pop('type', None)
        else:
            cfg['appType'] = 'current'
            cfg['type'] = form_type or 'design'
        # 旧表筛选条件字段 model 失效
        fl0 = cfg.setdefault('filter', {})
        fl0['conditionFields'] = []
        cfg['calcFields'] = []
        changes.append('form:%s->%s(%s@%s)' % (
            old_form_code, form_code, form_name, form_app_id))

    if dim_tok:
        ctype = comp.get('component') or ''
        if ctype in qc.EMPTY_DIM_TYPES:
            print('NOTE=组件 %s 通常空维；仍写入 --dim=%s' % (ctype, dim_tok))
        dim_f, note = qc.resolve_field_with_fallback(
            dim_tok, fields, role='dim', allow_record_count=False)
        if dim_f is None or not dim_f.get('fieldName'):
            print('DIM_NOT_FOUND token=%s' % dim_tok)
            for f in fields:
                print('FIELD\t%s\t%s\t%s' % (
                    f.get('fieldName'), f.get('fieldTxt'), f.get('widgetType')))
            sys.exit(1)
        if note:
            print('NOTE=%s' % note)
        # 非日期维禁止残留 dateGroup；日期维按 --date-group 或清空
        use_dg = date_group if (date_group and qc.is_date_dim_field(dim_f)) else ''
        if date_group and not use_dg:
            print('NOTE=dim 非日期字段，已忽略 --date-group=%s' % date_group)
        cfg['nameFields'] = [qc.as_dim_field(dim_f, use_dg)]
        # 关联维展开后顶层 sourceCode
        nf0 = cfg['nameFields'][0]
        if nf0.get('sourceCode'):
            cfg['sourceCode'] = nf0.get('sourceCode')
        changes.append('dim:%s->%s(%s)' % (
            (old_nf[0].get('fieldName') if old_nf else ''),
            nf0.get('fieldName'), nf0.get('fieldTxt')))

    if val_tok:
        val_f, note = qc.resolve_field_with_fallback(
            val_tok, fields, role='val', allow_record_count=True)
        if val_f is None or not val_f.get('fieldName'):
            print('VAL_NOT_FOUND token=%s' % val_tok)
            sys.exit(1)
        if note:
            print('NOTE=%s' % note)
        cfg['valueFields'] = [qc.as_value_field(val_f)]
        if val_f.get('fieldName') == 'record_count':
            cfg['calcFields'] = []
        # series 名跟数值显示名（若原是销量等）
        opt = cfg.setdefault('option', {})
        series = opt.get('series')
        if isinstance(series, list):
            for s in series:
                if isinstance(s, dict) and s.get('type') in (
                        'bar', 'line', 'pie', 'scatter', 'funnel', None, ''):
                    s['name'] = val_f.get('fieldTxt') or s.get('name')
        changes.append('val:%s->%s(%s)' % (
            (old_vf[0].get('fieldName') if old_vf else ''),
            val_f.get('fieldName'), val_f.get('fieldTxt')))

    # 双轴：左轴分组=typeFields(--grp)；右轴数值=assistYFields；右轴分组=assistTypeFields
    if grp_tok:
        grp_f, note = qc.resolve_field_with_fallback(
            grp_tok, fields, role='grp', allow_record_count=False)
        if grp_f is None or not grp_f.get('fieldName'):
            print('GRP_NOT_FOUND token=%s' % grp_tok)
            sys.exit(1)
        if note:
            print('NOTE=%s' % note)
        cfg['typeFields'] = [qc.as_dim_field(grp_f)]
        changes.append('grp:%s->%s(%s)' % (
            (old_tf[0].get('fieldName') if old_tf else ''),
            grp_f.get('fieldName'), grp_f.get('fieldTxt')))

    if assist_y_tok:
        ay_f, note = qc.resolve_field_with_fallback(
            assist_y_tok, fields, role='val', allow_record_count=True)
        if ay_f is None or not ay_f.get('fieldName'):
            print('ASSIST_Y_NOT_FOUND token=%s' % assist_y_tok)
            sys.exit(1)
        if note:
            print('NOTE=%s' % note)
        cfg['assistYFields'] = [qc.as_value_field(ay_f)]
        changes.append('assistY:%s->%s(%s)' % (
            (old_ay[0].get('fieldName') if old_ay else ''),
            ay_f.get('fieldName'), ay_f.get('fieldTxt')))

    if assist_type_tok:
        at_f, note = qc.resolve_field_with_fallback(
            assist_type_tok, fields, role='grp', allow_record_count=False)
        if at_f is None or not at_f.get('fieldName'):
            print('ASSIST_TYPE_NOT_FOUND token=%s' % assist_type_tok)
            sys.exit(1)
        if note:
            print('NOTE=%s' % note)
        cfg['assistTypeFields'] = [qc.as_dim_field(at_f)]
        changes.append('assistType:%s->%s(%s)' % (
            (old_at[0].get('fieldName') if old_at else ''),
            at_f.get('fieldName'), at_f.get('fieldTxt')))

    if query_range:
        fl = cfg.setdefault('filter', {})
        old_ct = list(fl.get('customTime') or [])
        fl['queryRange'] = query_range
        if not fl.get('queryField'):
            fl['queryField'] = 'create_time'
        if query_range == 'custom':
            fl['customTime'] = list(custom_time)
            changes.append('queryRange:%s->custom customTime:%s->%s' % (
                old_qr, old_ct, fl['customTime']))
        else:
            fl['customTime'] = []
            changes.append('queryRange:%s->%s' % (old_qr, query_range))

    bi_utils._page_components[page_id] = tmpl
    bi_utils.save_page(page_id)
    cname = comp.get('componentName') or comp.get('component') or ''
    title_txt = (((cfg.get('option') or {}).get('title') or {}).get('text') or '')
    if title_txt and title_txt != cname:
        print('REBOUND=%s title=%s' % (cname, title_txt))
    else:
        print('REBOUND=%s' % cname)
    print('CHANGES=%s' % ';'.join(changes))
    print('PAGE_ID=%s' % page_id)
    print('APP_ID=%s' % app_id)
    print('耗时: %.1fs' % (time.time() - t0))


# 图表内「筛选条件」≠ JFilterQuery「查询条件」。金标：本月订单看板手工图
# filter.conditionFields=[{condition:'3', fieldName:销量model, fieldTxt:'销量', fieldType:'number',
#   fieldValue:'100', widgetType:'number', fieldShow:True, options:{...}}]；无 val/rule。
_CHART_COND_OP = {
    '1': '1', '=': '1', '等于': '1', '是': '1', 'eq': '1',
    '2': '2', '!=': '2', '≠': '2', '不等于': '2', '不是': '2', 'ne': '2',
    '3': '3', '>': '3', '大于': '3', 'gt': '3',
    '4': '4', '<': '4', '小于': '4', 'lt': '4',
    '5': '5', '>=': '5', '≥': '5', '大于等于': '5', 'gte': '5',
    '6': '6', '<=': '6', '≤': '6', '小于等于': '6', 'lte': '6',
    '7': '7', '为空': '7', 'empty': '7',
    '8': '8', '不为空': '8', 'notempty': '8',
    '9': '9', '范围内': '9', 'between': '9',
    '10': '10', '不在范围内': '10', 'notbetween': '10',
}


def _norm_chart_cond_op(raw):
    s = str(raw or '').strip()
    if not s:
        return ''
    if s in _CHART_COND_OP:
        return _CHART_COND_OP[s]
    sl = s.lower()
    return _CHART_COND_OP.get(sl, '')


def cmd_set_chart_filter(args):
    """已有 QQY 统计图写入 filter.conditionFields（图表设置里的筛选条件）。
    禁止走 add-filter（那是 JFilterQuery 查询面板）。"""
    t0 = time.time()
    clear = bool(getattr(args, 'clear', False))
    field_tok = (getattr(args, 'field', None) or '').strip()
    op_raw = (getattr(args, 'op', None) or '').strip()
    value = getattr(args, 'value', None)
    if value is None:
        value = ''
    else:
        value = str(value)
    begin_v = (getattr(args, 'begin_value', None) or '').strip()
    end_v = (getattr(args, 'end_value', None) or '').strip()
    if not clear and not field_tok:
        print('必须提供 --field 与 --op/--value，或 --clear')
        sys.exit(1)
    op = ''
    if not clear:
        op = _norm_chart_cond_op(op_raw or '大于')
        if not op:
            print('op 非法: %s 允许=等于/不等于/大于/小于/大于等于/小于等于/为空/不为空/范围内' % op_raw)
            sys.exit(1)
        if op in ('9', '10') and (not begin_v or not end_v):
            print('范围内/不在范围内 必须 --begin-value 与 --end-value')
            sys.exit(1)
        if op not in ('7', '8', '9', '10') and value == '':
            print('必须提供 --value（为空/不为空/范围除外）')
            sys.exit(1)

    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    page_id, _page_name = _resolve_page_id(args, app_id)

    page = bi_utils.query_page(page_id)
    tmpl = page.get('template') or []
    if isinstance(tmpl, str):
        tmpl = json.loads(tmpl)

    hits = _find_chart_for_rebind(
        tmpl,
        name=getattr(args, 'name', None),
        match_dim=getattr(args, 'match_dim', None),
        comp=getattr(args, 'comp', None),
    )
    if not hits:
        print('CHART_NOT_FOUND name=%s' % (getattr(args, 'name', '') or ''))
        for c in tmpl:
            print('CAND\t%s\t%s' % (c.get('componentName'), c.get('component')))
        sys.exit(1)
    if len(hits) > 1:
        print('CHART_AMBIGUOUS count=%d' % len(hits))
        for c in hits:
            print('CAND\t%s\t%s' % (c.get('componentName'), c.get('component')))
        sys.exit(1)

    comp = hits[0]
    cfg = comp.get('config') or {}
    if isinstance(cfg, str):
        cfg = json.loads(cfg)
        comp['config'] = cfg
    fl = cfg.setdefault('filter', {})
    old = copy.deepcopy(fl.get('conditionFields') or [])

    if clear:
        fl['conditionFields'] = []
        fl.setdefault('conditionMode', 'and')
        bi_utils._page_components[page_id] = tmpl
        bi_utils.save_page(page_id)
        print('FILTERED=%s cleared old=%d' % (comp.get('componentName') or '', len(old)))
        print('PAGE_ID=%s' % page_id)
        print('耗时: %.1fs' % (time.time() - t0))
        return

    form_code = (cfg.get('tableName') or cfg.get('designFormCode')
                 or cfg.get('formCode') or '').strip()
    if not form_code:
        print('CHART_NO_FORM componentName=%s' % (comp.get('componentName') or ''))
        sys.exit(1)

    class _FArgs(object):
        pass
    fa = _FArgs()
    fa.form_code = form_code
    fa.form_name = cfg.get('formName') or ''
    cfg_type = cfg.get('type') or ''
    fa.form_type = cfg_type if cfg_type in ('aggregation', 'design', 'online') else (
        cfg.get('formType') or 'design')
    fields, form_name, form_type = _load_fields(fa)
    hits_f = [f for f in fields if field_tok in (f.get('fieldName'), f.get('fieldTxt'))]
    if not hits_f:
        hits_f = [f for f in fields
                  if field_tok in (f.get('fieldTxt') or '') or (f.get('fieldTxt') or '') in field_tok]
    if not hits_f:
        # 「数字」口语常指图上数值字段
        if field_tok in ('数字', '数值', '指标'):
            vfs = cfg.get('valueFields') or []
            if vfs and isinstance(vfs[0], dict) and vfs[0].get('fieldName'):
                vn = vfs[0].get('fieldName')
                hits_f = [f for f in fields if f.get('fieldName') == vn]
        if not hits_f:
            print('COND_FIELD_NOT_FOUND keyword=%s' % field_tok)
            for f in fields:
                print('CAND %s\t%s\t%s' % (f.get('fieldName'), f.get('fieldTxt'), f.get('widgetType')))
            sys.exit(1)
    f = hits_f[0]
    cond = {
        'condition': op,
        'fieldName': f.get('fieldName'),
        'fieldTxt': f.get('fieldTxt'),
        'fieldType': f.get('fieldType') or 'string',
        'widgetType': f.get('widgetType') or 'input',
        'fieldShow': True,
        'options': copy.deepcopy(f.get('options') or {}),
    }
    if op in ('9', '10'):
        cond['beginValue'] = begin_v
        cond['endValue'] = end_v
        cond['fieldValue'] = ''
    elif op in ('7', '8'):
        cond['fieldValue'] = ''
    else:
        cond['fieldValue'] = value
    # 手工金标：数值筛选无 val/rule；勿抄 JFilterQuery 的 rule/val
    fl['conditionFields'] = [cond]
    fl.setdefault('conditionMode', 'and')
    if not fl.get('queryField'):
        fl['queryField'] = 'create_time'

    bi_utils._page_components[page_id] = tmpl
    bi_utils.save_page(page_id)
    print('FILTERED=%s field=%s(%s) op=%s value=%s' % (
        comp.get('componentName') or '', f.get('fieldName'), f.get('fieldTxt'), op, value))
    print('PAGE_ID=%s' % page_id)
    print('APP_ID=%s' % app_id)
    print('耗时: %.1fs' % (time.time() - t0))


# 计算值聚合码（与 qqy_chart.CALC_AGG 一致；中文口语 → 码）
_CALC_AGG_NAME = {
    '1': '1', '求和': '1', 'sum': '1',
    '2': '2', '最大值': '2', '最大': '2', 'max': '2',
    '3': '3', '最小值': '3', '最小': '3', 'min': '3',
    '4': '4', '平均值': '4', '平均': '4', 'avg': '4', 'average': '4',
    '5': '5', '计算': '5',
}
_CALC_TOKEN_RE = re.compile(r'\$([^-$\s]+)-(\d)\$')


def _norm_calc_agg_token(raw):
    s = str(raw or '').strip()
    if not s:
        return ''
    if s in _CALC_AGG_NAME:
        return _CALC_AGG_NAME[s]
    return _CALC_AGG_NAME.get(s.lower(), '')


def _parse_calc_agg_pattern(formula):
    """解析口语公式「平均×求和」→ ['4','1']；原样 $model-N$ 返回 None（走整串替换）。"""
    s = str(formula or '').strip()
    if not s:
        return None
    if s.startswith('$'):
        return None
    # 去掉「改成/改为」等前缀噪声
    s = re.sub(r'^(改成|改为|换成|变更为)\s*', '', s)
    parts = re.split(r'[×\*xX＋+／/－\-\s]+', s)
    codes = []
    for p in parts:
        p = (p or '').strip()
        if not p:
            continue
        code = _norm_calc_agg_token(p)
        if not code:
            print('CALC_AGG_UNKNOWN token=%s 允许=求和/平均/最大值/最小值/计算' % p)
            sys.exit(1)
        codes.append(code)
    if not codes:
        print('formula 无法解析: %s' % formula)
        sys.exit(1)
    return codes


def _rewrite_calc_formula(old_formula, new_formula_or_pattern):
    """按口语聚合模式改写已有 $model-N$ 公式，或整串替换为以 $ 开头的新公式。

    例：旧 `$money-4$*$qty-1$` + 「求和×求和」→ `$money-1$*$qty-1$`
    默认销售额自动 calc 是「平均×求和」（money-4 * qty-1）。
    """
    old = str(old_formula or '').strip()
    raw = str(new_formula_or_pattern or '').strip()
    if not old:
        print('CHART_NO_CALC_FORMULA')
        sys.exit(1)
    if raw.startswith('$'):
        return raw
    codes = _parse_calc_agg_pattern(raw)
    toks = list(_CALC_TOKEN_RE.finditer(old))
    if not toks:
        print('CHART_CALC_NO_TOKENS formula=%s' % old)
        sys.exit(1)
    if len(codes) != len(toks):
        print('CALC_TOKEN_MISMATCH want=%d got=%d old=%s pattern=%s' % (
            len(toks), len(codes), old, raw))
        sys.exit(1)
    out = []
    last = 0
    for i, m in enumerate(toks):
        out.append(old[last:m.start()])
        out.append('$%s-%s$' % (m.group(1), codes[i]))
        last = m.end()
    out.append(old[last:])
    return ''.join(out)


def _sync_calc_formula_on_cfg(cfg, new_formula):
    """同步改写 calcFields 与 valueFields 中的计算值 fieldName；返回 (old, new) 列表。"""
    changes = []
    for key in ('calcFields', 'valueFields'):
        arr = cfg.get(key) or []
        for v in arr:
            if not isinstance(v, dict):
                continue
            fn = v.get('fieldName') or ''
            if not (v.get('widgetType') == 'calcVal' or str(fn).startswith('$')):
                continue
            rewritten = _rewrite_calc_formula(fn, new_formula)
            if rewritten != fn:
                v['fieldName'] = rewritten
                changes.append('%s:%s->%s' % (key, fn, rewritten))
    return changes


def _comp_cfg(comp):
    cfg = comp.get('config') or {}
    if isinstance(cfg, str):
        try:
            cfg = json.loads(cfg)
        except Exception:
            cfg = {}
        comp['config'] = cfg
    if not isinstance(cfg, dict):
        cfg = {}
        comp['config'] = cfg
    return cfg


def _plain_numeric_value_fields(cfg):
    """非计算值、非记录数的数值槽，供升级为 $model-N$。"""
    out = []
    for v in (cfg.get('valueFields') or []):
        if not isinstance(v, dict):
            continue
        fn = str(v.get('fieldName') or '').strip()
        if not fn or fn == 'record_count':
            continue
        if v.get('widgetType') == 'calcVal' or fn.startswith('$'):
            continue
        out.append(v)
    return out


def _upgrade_plain_value_to_calc(cfg, formula):
    """把普通 valueFields 升级为 calcVal（口语「对库存数量求和（计算值）」）。"""
    raw = str(formula or '').strip()
    vals = _plain_numeric_value_fields(cfg)
    if not vals:
        print('CHART_NO_VALUE_FOR_CALC')
        sys.exit(1)
    if raw.startswith('$'):
        formula_out = raw
        field_txt = vals[0].get('fieldTxt') or '计算值'
    else:
        codes = _parse_calc_agg_pattern(raw)
        if len(codes) != len(vals):
            print('CALC_TOKEN_MISMATCH want=%d got=%d old=plain(%s) pattern=%s' % (
                len(vals), len(codes),
                ','.join(v.get('fieldName') or '' for v in vals), raw))
            sys.exit(1)
        parts = ['$%s-%s$' % (v['fieldName'], codes[i]) for i, v in enumerate(vals)]
        formula_out = '*'.join(parts) if len(parts) > 1 else parts[0]
        field_txt = vals[0].get('fieldTxt') or '计算值'
        if len(vals) > 1:
            field_txt = '×'.join(v.get('fieldTxt') or v.get('fieldName') or '' for v in vals)
    calc_obj = qc.make_calc_field(formula_out, field_txt)
    old_fn = vals[0].get('fieldName')
    cfg['valueFields'] = [copy.deepcopy(calc_obj)]
    cfg['calcFields'] = [copy.deepcopy(calc_obj)]
    opt = cfg.setdefault('option', {})
    series = opt.get('series')
    if isinstance(series, list):
        for s in series:
            if isinstance(s, dict) and s.get('type') in (
                    'bar', 'line', 'pie', 'scatter', 'funnel', None, ''):
                s['name'] = field_txt
    return ['valueFields:%s->%s' % (old_fn, formula_out),
            'calcFields:[]->%s' % formula_out]


def _is_clear_calc(formula):
    s = str(formula or '').strip()
    if not s:
        return False
    if s in _CLEAR_CALC:
        return True
    sl = s.lower()
    if sl in {x.lower() for x in _CLEAR_CALC}:
        return True
    return s.startswith('改回')


def _clear_calc_on_cfg(cfg, val_tok=None):
    """取消计算值，改回普通数值字段。"""
    if not _chart_has_calc(cfg):
        print('CHART_NO_CALC')
        sys.exit(1)
    calc = None
    for v in list(cfg.get('calcFields') or []) + list(cfg.get('valueFields') or []):
        if isinstance(v, dict) and (
                v.get('widgetType') == 'calcVal'
                or str(v.get('fieldName') or '').startswith('$')):
            calc = v
            break
    formula = str((calc or {}).get('fieldName') or '')
    models = [m.group(1) for m in _CALC_TOKEN_RE.finditer(formula)]
    filter_field = cfg.get('filterField') or []

    def find_f(tok):
        t = str(tok or '').strip()
        if not t:
            return None
        for f in filter_field:
            if not isinstance(f, dict):
                continue
            if f.get('fieldName') == t or f.get('fieldTxt') == t:
                return f
        for f in filter_field:
            if not isinstance(f, dict):
                continue
            if t in str(f.get('fieldTxt') or ''):
                return f
        return None

    target = find_f(val_tok) if val_tok else None
    if target is None and models:
        target = find_f(models[0])
    if target is None and models:
        target = {
            'fieldName': models[0],
            'fieldTxt': (calc.get('fieldTxt') if calc else models[0]) or models[0],
            'fieldType': 'number',
            'widgetType': 'number',
            'fieldShow': True,
        }
    if target is None:
        print('CHART_CLEAR_CALC_NO_FIELD')
        sys.exit(1)
    vf = qc.as_value_field(target)
    cfg['calcFields'] = []
    cfg['valueFields'] = [vf]
    opt = cfg.setdefault('option', {})
    series = opt.get('series')
    if isinstance(series, list):
        for s in series:
            if isinstance(s, dict):
                s['name'] = vf.get('fieldTxt') or vf.get('fieldName')
    return ['calcFields->[]', 'valueFields:%s->%s' % (formula, vf.get('fieldName'))]


def _apply_calc_on_cfg(cfg, formula):
    """已有计算值则改公式；否则把当前数值字段升级为计算值。"""
    if _is_clear_calc(formula):
        return _clear_calc_on_cfg(cfg)
    if _chart_has_calc(cfg):
        return _sync_calc_formula_on_cfg(cfg, formula)
    return _upgrade_plain_value_to_calc(cfg, formula)


# 渲染键按组件类型分三种（2026-09-16 二次返工实测，详见 create.md「标题 / 口径」行）
#   · JNumber / JPivotTable：没有 ECharts 标题区，标题只走卡片头 option.card.title
#     （透视表 opt.title.text 还会被平台占位成「表格」）→ 必须写 card.title
#   · 其余饼/柱/折等：标题走 ECharts opt.title.text，card.title 写非空会「双标题」
_CARD_TITLE_COMPS = {'JNumber', 'JPivotTable'}


def _apply_chart_title(comp, cfg, new_title):
    """图标题三字段一次写：componentName + option.title.text + card.title（按类型定）。"""
    new_title = str(new_title or '').strip()
    if not new_title:
        print('必须提供 --title（新图标题）')
        sys.exit(1)
    comp['componentName'] = new_title
    opt = cfg.setdefault('option', {})
    title_obj = opt.get('title') if isinstance(opt.get('title'), dict) else {}
    title_obj['show'] = True
    title_obj['text'] = new_title
    opt['title'] = title_obj
    card = opt.get('card') if isinstance(opt.get('card'), dict) else {}
    card['title'] = new_title if comp.get('component') in _CARD_TITLE_COMPS else ''
    opt['card'] = card
    return new_title


def _select_chart_for_calc(tmpl, name=None, match_dim=None, comp=None):
    """点名图即使无 calc 也留下（升级为计算值）；禁止改绑到同页另一张 calc 图。"""
    named = bool((name or '').strip() or (match_dim or '').strip())
    hits = _find_chart_for_rebind(
        tmpl, name=name, match_dim=match_dim, comp=comp, match_calc=not named)
    if named:
        return hits
    if hits and not any(_chart_has_calc(_comp_cfg(h)) for h in hits):
        hits = _find_chart_for_rebind(
            tmpl, name=None, match_dim=None, comp=comp, match_calc=True)
    return hits


def cmd_set_chart_calc(args):
    """已有 QQY 统计图改计算值公式（calcFields + valueFields 同步）。

    口语：「平均×求和改成求和×求和」→ --formula 求和×求和。
    口语：「对库存数量求和（计算值）」且图尚无 calc → 把当前数值字段升级为 $model-1$。
    同句改标题 → --title。禁止 dump 页 JSON / 手写一次性改盘脚本。
    """
    t0 = time.time()
    formula = (getattr(args, 'formula', None) or '').strip()
    clear = bool(getattr(args, 'clear', False)) or _is_clear_calc(formula)
    if not formula and not clear:
        print('必须提供 --formula（如 求和×求和）或 --clear 改回字段')
        sys.exit(1)

    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    page_id, _page_name = _resolve_page_id(args, app_id)

    page = bi_utils.query_page(page_id)
    tmpl = page.get('template') or []
    if isinstance(tmpl, str):
        tmpl = json.loads(tmpl)

    name = getattr(args, 'name', None)
    match_dim = getattr(args, 'match_dim', None)
    comp = getattr(args, 'comp', None)
    hits = _select_chart_for_calc(tmpl, name=name, match_dim=match_dim, comp=comp)
    if not hits:
        print('CHART_NOT_FOUND name=%s match_dim=%s comp=%s' % (
            name or '', match_dim or '', comp or ''))
        for c in tmpl:
            cfg = c.get('config') or {}
            if isinstance(cfg, str):
                try:
                    cfg = json.loads(cfg)
                except Exception:
                    cfg = {}
            flag = 'calc' if _chart_has_calc(cfg) else '-'
            print('CAND\t%s\t%s\t%s' % (
                c.get('componentName'), c.get('component'), flag))
        sys.exit(1)
    if len(hits) > 1:
        print('CHART_AMBIGUOUS count=%d（请 --name 或 --comp 收窄）' % len(hits))
        for c in hits:
            print('CAND\t%s\t%s' % (c.get('componentName'), c.get('component')))
        sys.exit(1)

    comp_obj = hits[0]
    cfg = _comp_cfg(comp_obj)

    if clear:
        changes = _clear_calc_on_cfg(cfg, getattr(args, 'val', None))
    else:
        changes = _apply_calc_on_cfg(cfg, formula)
    if not changes:
        print('NO_CHANGE formula 已是目标或未命中 calc 槽')
        sys.exit(1)

    new_title = (getattr(args, 'title', None) or '').strip()
    if new_title:
        _apply_chart_title(comp_obj, cfg, new_title)

    bi_utils._page_components[page_id] = tmpl
    bi_utils.save_page(page_id)
    title = (comp_obj.get('componentName')
             or ((cfg.get('option') or {}).get('title') or {}).get('text')
             or 'calc-chart')
    print('CALC_SET=%s' % title)
    print('CHANGES=%s' % ';'.join(changes))
    if new_title:
        print('RENAMED=%s' % new_title)
    print('PAGE_ID=%s' % page_id)
    print('APP_ID=%s' % app_id)
    print('耗时: %.1fs' % (time.time() - t0))


def cmd_rename_chart(args):
    """已有 QQY 统计图改标题：componentName + option.title.text + card.title（后者按组件类型定）。"""
    t0 = time.time()
    new_title = (getattr(args, 'title', None) or '').strip()
    if not new_title:
        print('必须提供 --title（新图标题）')
        sys.exit(1)
    name = (getattr(args, 'name', None) or '').strip()
    match_dim = (getattr(args, 'match_dim', None) or '').strip()
    if not name and not match_dim:
        print('必须提供 --name 或 --match-dim')
        sys.exit(1)

    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    page_id, _page_name = _resolve_page_id(args, app_id)

    page = bi_utils.query_page(page_id)
    tmpl = page.get('template') or []
    if isinstance(tmpl, str):
        tmpl = json.loads(tmpl)

    hits = _find_chart_for_rebind(
        tmpl, name=name, match_dim=match_dim,
        comp=getattr(args, 'comp', None), match_calc=False)
    if not hits:
        print('CHART_NOT_FOUND name=%s match_dim=%s' % (name or '', match_dim or ''))
        for c in tmpl:
            print('CAND\t%s\t%s' % (c.get('componentName'), c.get('component')))
        sys.exit(1)
    if len(hits) > 1:
        print('CHART_AMBIGUOUS count=%d（请 --name 收窄）' % len(hits))
        for c in hits:
            print('CAND\t%s\t%s' % (c.get('componentName'), c.get('component')))
        sys.exit(1)

    comp_obj = hits[0]
    cfg = _comp_cfg(comp_obj)
    _apply_chart_title(comp_obj, cfg, new_title)
    bi_utils._page_components[page_id] = tmpl
    bi_utils.save_page(page_id)
    print('RENAMED=%s' % new_title)
    print('PAGE_ID=%s' % page_id)
    print('APP_ID=%s' % app_id)
    print('耗时: %.1fs' % (time.time() - t0))


def cmd_set_chart_color(args):
    """已有 QQY 统计图改色 / 折线类型 / 数值·百分比标签（按组件运行时读色路径分流，见 _apply_spec_colors）。

    口语：「柱形图柱体颜色改成金色 #FFD700」→ --comp JBar --color #FFD700（或 金色）。
    口语「打开柱体渐变 / 渐变色 A 到 B」→ --gradient --colors "#64b5f6,#1890FF"
    （每色一条 customColor；禁止 {color:A, color1:B} 一条，UI 只认各项 .color）。
    口语「折线类型改成曲线」→ --line-type 曲线（落盘 lineType=smooth + smooth=true）。
    口语「显示数值标签」→ --label-show（饼 formatter={b}\\n{c}）；「百分比标签」→ --percent-label。
    口语样式无专用旗标 → --style/--oral 整段（点大小/圆角/柱宽/配色）；禁 query_page / 手写 py。
    同轮改色+曲线/标签 → 一条命令同时 --color 与 --line-type / --label-show；禁 switch-type JSmoothLine、禁手写 py。
    JBar 实心柱只写 series[0].itemStyle.color；JLine 同步 itemStyle+customColor。
    未给 --name 且 --comp 命中多张同类型图 → 全部改。
    """
    t0 = time.time()
    color_raw = (getattr(args, 'color', None) or getattr(args, 'colors', None) or '').strip()
    line_type_raw = (getattr(args, 'line_type', None) or '').strip()
    mapped_lt = _normalize_line_type(line_type_raw)
    if line_type_raw and not mapped_lt:
        print('LINE_TYPE_UNKNOWN=%s（曲线/smooth 折线/line 面积/area）' % line_type_raw)
        sys.exit(1)
    shape_raw = (getattr(args, 'shape', None) or '').strip()
    mapped_shape = _norm_wordcloud_shape(shape_raw) if shape_raw else ''
    if shape_raw and not mapped_shape:
        print('SHAPE_UNKNOWN=%s 允许口语=心的形状/爱心/心形/圆形/菱形/三角/星形' % shape_raw)
        sys.exit(1)
    ss_raw = getattr(args, 'symbol_size', None)
    symbol_size = None
    if ss_raw not in (None, ''):
        m = re.search(r'(\d+)', str(ss_raw))
        if m:
            symbol_size = int(m.group(1))
    oral_spec = {}
    style_raw = (getattr(args, 'style', None) or getattr(args, 'oral', None) or '').strip()
    if style_raw:
        oral_spec, applied = _parse_chart_oral(style_raw)
        if applied:
            print('ORAL_APPLIED=%s' % ','.join(applied))
        if not color_raw and oral_spec.get('colors'):
            cols = oral_spec['colors']
            color_raw = ','.join(cols) if isinstance(cols, (list, tuple)) else str(cols)
        if symbol_size is None and oral_spec.get('symbolSize') not in (None, ''):
            try:
                symbol_size = int(oral_spec['symbolSize'])
            except (TypeError, ValueError):
                symbol_size = oral_spec['symbolSize']
        if not mapped_lt and oral_spec.get('lineType'):
            mapped_lt = oral_spec['lineType']
        if not mapped_shape and oral_spec.get('shape'):
            mapped_shape = oral_spec['shape']
        if getattr(args, 'gradient', False) is False and oral_spec.get('showLinearGradient'):
            args.gradient = True
    if getattr(args, 'percent_label', False):
        label_kind = 'percent'
    elif getattr(args, 'label_show', False):
        label_kind = 'value'
    elif oral_spec.get('percentLabel'):
        label_kind = 'percent'
    elif oral_spec.get('labelShow'):
        label_kind = 'value'
    else:
        label_kind = None
    style_keys = ('borderRadius', 'barWidth', 'symbolSize', 'lineType', 'shape',
                  'colors', 'labelShow', 'percentLabel', 'showLinearGradient', 'legendShow')
    has_oral_style = any(oral_spec.get(k) not in (None, '', []) for k in style_keys)
    if not color_raw and not mapped_lt and not label_kind and not mapped_shape and symbol_size is None and not has_oral_style:
        print('必须提供 --color/--colors/--line-type/--shape/--label-show/--percent-label/--symbol-size/--style')
        sys.exit(1)

    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    page_id, _page_name = _resolve_page_id(args, app_id)

    page = bi_utils.query_page(page_id)
    tmpl = page.get('template') or []
    if isinstance(tmpl, str):
        tmpl = json.loads(tmpl)

    name = getattr(args, 'name', None)
    match_dim = getattr(args, 'match_dim', None)
    comp = getattr(args, 'comp', None)
    hits = _find_chart_for_rebind(
        tmpl, name=name, match_dim=match_dim, comp=comp, match_calc=False)
    # 仅 --comp（口语「柱形图」无标题）：_find_chart_for_rebind 不会因类型单独入选，按类型兜底
    if not hits and (comp or '').strip() and not (name or '').strip() and not (match_dim or '').strip():
        want = _norm_comp_alias((comp or '').strip()) or (comp or '').strip()
        for c in tmpl or []:
            if (c.get('component') or '') != want:
                continue
            cfg = c.get('config') or {}
            if isinstance(cfg, str):
                try:
                    cfg = json.loads(cfg)
                except Exception:
                    cfg = {}
            if (cfg.get('dataType') == 4
                    or 'nameFields' in cfg
                    or 'valueFields' in cfg
                    or want in ('JBar', 'JLine', 'JPie', 'JHorizontalBar',
                                'JStackBar', 'JMultipleBar', 'JMultipleLine',
                                'JArea', 'JSmoothLine', 'JStepLine', 'JWordCloud')):
                hits.append(c)
    if not hits:
        print('CHART_NOT_FOUND name=%s match_dim=%s comp=%s' % (
            name or '', match_dim or '', comp or ''))
        for c in tmpl:
            print('CAND\t%s\t%s' % (c.get('componentName'), c.get('component')))
        sys.exit(1)
    # 多命中：有 --name 仍歧义 → 报错；无 --name（口语「柱形图」）→ 全部改
    if len(hits) > 1 and (name or '').strip():
        print('CHART_AMBIGUOUS count=%d（请更精确 --name 或 --comp）' % len(hits))
        for c in hits:
            print('CAND\t%s\t%s' % (c.get('componentName'), c.get('component')))
        sys.exit(1)

    colored = []
    lined = []
    labeled = []
    shaped = []
    sized = []
    for comp_obj in hits:
        cfg = comp_obj.get('config') or {}
        if isinstance(cfg, str):
            cfg = json.loads(cfg)
            comp_obj['config'] = cfg
        if color_raw:
            spec = {'colors': color_raw}
            if getattr(args, 'gradient', False):
                spec['showLinearGradient'] = True
            _apply_spec_colors(cfg, spec, spec_index=0)
        if mapped_lt:
            opt = cfg.setdefault('option', {})
            series = _ensure_series0(opt, 'line')
            _apply_line_type(series[0], mapped_lt)
            opt['series'] = series
        if mapped_shape:
            _apply_spec_shape(cfg, {'shape': mapped_shape}, spec_index=0)
        if symbol_size is not None:
            oral_spec['symbolSize'] = symbol_size
        if oral_spec:
            _apply_spec_style(cfg, oral_spec, spec_index=0)
        elif symbol_size is not None:
            _apply_spec_style(cfg, {'symbolSize': symbol_size}, spec_index=0)
        applied_label = _apply_chart_label(cfg, label_kind) if label_kind else None
        title = (comp_obj.get('componentName')
                 or ((cfg.get('option') or {}).get('title') or {}).get('text')
                 or comp_obj.get('i')
                 or 'chart')
        if color_raw:
            colored.append(title)
            print('COLORED=%s' % title)
        if mapped_lt:
            lined.append(title)
            print('LINE_TYPE=%s name=%s' % (mapped_lt, title))
        if applied_label:
            labeled.append(title)
            print('LABEL_SET=%s kind=%s' % (title, applied_label))
        if mapped_shape:
            shaped.append(title)
            print('SHAPE_SET=%s shape=%s' % (title, mapped_shape))
        if symbol_size is not None:
            sized.append(title)
            print('SIZE_SET=%s symbolSize=%s' % (title, symbol_size))

    bi_utils._page_components[page_id] = tmpl
    bi_utils.save_page(page_id)
    print('UPDATED=%d' % max(len(colored), len(lined), len(labeled), len(shaped), len(sized)))
    print('PAGE_ID=%s' % page_id)
    print('APP_ID=%s' % app_id)
    print('耗时: %.1fs' % (time.time() - t0))


def cmd_set_chart_sort(args):
    """已有 QQY 统计图写前 N 项（dataFilterNum）+ 排序（sorts）。

    口语：「只显示前 8 项，按库存数量降序」→ --top-n 8 --field 库存数量 --order desc
    也可 --sort 库存数量降序。禁 grep dataFilterNum、禁手写 py、禁 comp_ops --set。
    sorts.name 落盘为图上已绑 fieldName（中文名在 valueFields/nameFields 解析）。
    聚合表(type=aggregation)按数值列（公式/输出列，fieldName=中文名+calcId前5位 型内部键）
    或表单图按自动金额公式值（fieldName 以 $ 开头，如 $money_…$*$number_…$）排序 →
    自动留空 name 只写 type/前 N：内部键/公式串前端不认作 sorts.name，落盘致整图白屏
    （2026-09-08 实测：聚合盘 + 1009/902 表单排行榜两次）。
    """
    t0 = time.time()
    top_raw = (getattr(args, 'top_n', None) or getattr(args, 'data_filter_num', None) or '')
    field_tok = (getattr(args, 'field', None) or '').strip()
    order_raw = (getattr(args, 'order', None) or '').strip()
    sort_raw = (getattr(args, 'sort', None) or '').strip()
    top_n = _parse_top_n(top_raw)
    if top_raw and top_n is None:
        print('TOP_N_INVALID=%s（期望正整数，如 8 / 前8项）' % top_raw)
        sys.exit(1)
    if not top_n and not field_tok and not sort_raw and not order_raw:
        print('必须提供 --top-n 或 --field/--order 或 --sort（如 --top-n 8 --field 库存数量 --order desc）')
        sys.exit(1)

    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    page_id, _page_name = _resolve_page_id(args, app_id)

    page = bi_utils.query_page(page_id)
    tmpl = page.get('template') or []
    if isinstance(tmpl, str):
        tmpl = json.loads(tmpl)

    hits = _find_chart_for_rebind(
        tmpl,
        name=getattr(args, 'name', None),
        match_dim=getattr(args, 'match_dim', None),
        comp=getattr(args, 'comp', None),
    )
    if not hits:
        print('CHART_NOT_FOUND name=%s match_dim=%s comp=%s' % (
            getattr(args, 'name', '') or '',
            getattr(args, 'match_dim', '') or '',
            getattr(args, 'comp', '') or ''))
        for c in tmpl:
            print('CAND\t%s\t%s' % (c.get('componentName'), c.get('component')))
        sys.exit(1)
    if len(hits) > 1:
        print('CHART_AMBIGUOUS count=%d（请更精确 --name 或 --comp）' % len(hits))
        for c in hits:
            print('CAND\t%s\t%s' % (c.get('componentName'), c.get('component')))
        sys.exit(1)

    comp_obj = hits[0]
    cfg = comp_obj.get('config') or {}
    if isinstance(cfg, str):
        cfg = json.loads(cfg)
        comp_obj['config'] = cfg

    want_sort = bool(field_tok or sort_raw or order_raw)
    sort_name = field_tok
    sort_order = _norm_sort_order(order_raw)
    if sort_raw:
        parsed = _parse_sorts_spec(cfg, sort_raw)
        if parsed.get('name') and not sort_name:
            sort_name = parsed['name']
        if parsed.get('type') and not sort_order:
            sort_order = parsed['type']
    if want_sort and not sort_order:
        sort_order = 'desc'
    if want_sort and not sort_name:
        vfs = cfg.get('valueFields') or []
        if vfs and isinstance(vfs[0], dict) and vfs[0].get('fieldName'):
            sort_name = vfs[0]['fieldName']
            print('NOTE=未点名排序字段，回落到 valueFields[0]=%s' % sort_name)
        else:
            print('SORT_FIELD_REQUIRED（图无 valueFields，请 --field 中文名）')
            sys.exit(1)

    # 排序名先解析成图已绑 fieldName（与 _parse_sorts_spec 同口径：中文→fieldName），
    # 供下方聚合表 value 列回退判定（不提前解析则此处拿到的还是中文，拦不住 calcId 后缀键）
    if want_sort and sort_name:
        _hit = _match_chart_bind_field(cfg, sort_name)
        if _hit:
            sort_name = _hit.get('fieldName') or sort_name
    # 内部键/公式值不能作 sorts.name：① 聚合表(type=aggregation)数值列=中文名+calcId前5位 型内部键
    # （如 库存合计69c48）；② 表单图 value=自动金额公式（fieldName 以 $ 开头，
    # 如 $money_…$*$number_…$，widgetType=calcVal）。前端数据面板/渲染不认这些键作 sorts.name
    # ——落盘后整图白屏，设计器手工保存把 name 清空才恢复（2026-09-08 实测两次同签名：
    # 聚合盘 + 1009/902 表单排行榜）。回退 name 留空，保留 type 与前 N；
    # 按维度列（nameFields/本地列）排序未验证，暂不拦。
    if want_sort and sort_name and (cfg.get('type') == 'aggregation' or sort_name.startswith('$')):
        value_hit = False
        for _key in ('valueFields', 'calcFields', 'assistYFields'):
            for _f in cfg.get(_key) or []:
                if isinstance(_f, dict) and _f.get('fieldName') == sort_name:
                    value_hit = True
                    break
            if value_hit:
                break
        if value_hit:
            kind = '聚合数值列(calcId 内部键)' if cfg.get('type') == 'aggregation' else '公式值(自动金额计算)'
            print('NOTE=%s %s 不能作 sorts.name（落盘整图白屏）；'
                  'sorts.name 留空，仅保留 type=%s 与前 N，精确排序列请在设计器数据面板选'
                  % (kind, sort_name, sort_order))
            sort_name = ''

    spec = {}
    if top_n is not None:
        spec['dataFilterNum'] = top_n
    if want_sort:
        spec['sorts'] = {'name': sort_name, 'type': sort_order}
    _apply_spec_style(cfg, spec, spec_index=0)

    title = (comp_obj.get('componentName')
             or (((cfg.get('option') or {}).get('title') or {}).get('text'))
             or 'chart')
    if top_n is not None:
        print('TOP_N=%s name=%s' % (cfg.get('dataFilterNum'), title))
    if want_sort:
        print('SORTED=%s sorts=%s' % (title, json.dumps(cfg.get('sorts') or {}, ensure_ascii=False)))

    bi_utils._page_components[page_id] = tmpl
    bi_utils.save_page(page_id)
    print('PAGE_ID=%s' % page_id)
    print('APP_ID=%s' % app_id)
    print('耗时: %.1fs' % (time.time() - t0))


def cmd_set_chart_compare(args):
    """已有 JNumber 打开环比/同比（与上月相比、升红降绿）。

    口语：「打开与上月相比、升红降绿」→ --compare 上月 --trend 升红降绿
    落盘：queryRange=month + analysis.isCompare/compareType=preMonth/compareValue=0/trendType=2
    + option.isCompare/trendType；h<30 抬到 30。禁 grep isCompare、禁手写 py、禁 comp_ops --set。
    """
    t0 = time.time()
    compare_raw = (getattr(args, 'compare', None) or '').strip()
    trend_raw = (getattr(args, 'trend', None) or '').strip()
    if not compare_raw and not trend_raw:
        print('必须提供 --compare（上月/环比/同比）或 --trend（升红降绿/升绿降红）')
        sys.exit(1)
    compare_type = _norm_compare_type(compare_raw) if compare_raw else ''
    if compare_raw and not compare_type:
        print('COMPARE_TYPE_UNKNOWN=%s（上月/环比/preMonth 同比/上年/preYear 上周/preWeek）' % compare_raw)
        sys.exit(1)

    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    page_id, _page_name = _resolve_page_id(args, app_id)

    page = bi_utils.query_page(page_id)
    tmpl = page.get('template') or []
    if isinstance(tmpl, str):
        tmpl = json.loads(tmpl)

    name = getattr(args, 'name', None)
    match_dim = getattr(args, 'match_dim', None)
    comp = getattr(args, 'comp', None) or 'JNumber'
    hits = _find_chart_for_rebind(
        tmpl, name=name, match_dim=match_dim, comp=comp)
    if not hits and (comp or '').strip() and not (name or '').strip() and not (match_dim or '').strip():
        want = (comp or '').strip()
        for c in tmpl or []:
            if (c.get('component') or '') != want:
                continue
            cfg0 = c.get('config') or {}
            if isinstance(cfg0, str):
                try:
                    cfg0 = json.loads(cfg0)
                except Exception:
                    cfg0 = {}
            if (cfg0.get('dataType') == 4
                    or 'valueFields' in cfg0
                    or want == 'JNumber'):
                hits.append(c)
    if not hits:
        print('CHART_NOT_FOUND name=%s match_dim=%s comp=%s' % (
            name or '', match_dim or '', comp or ''))
        for c in tmpl:
            print('CAND\t%s\t%s' % (c.get('componentName'), c.get('component')))
        sys.exit(1)
    if len(hits) > 1:
        print('CHART_AMBIGUOUS count=%d（请更精确 --name）' % len(hits))
        for c in hits:
            print('CAND\t%s\t%s' % (c.get('componentName'), c.get('component')))
        sys.exit(1)

    comp_obj = hits[0]
    cfg = comp_obj.get('config') or {}
    if isinstance(cfg, str):
        cfg = json.loads(cfg)
        comp_obj['config'] = cfg
    ctype = comp_obj.get('component') or ''
    subclass = ((cfg.get('chart') or {}).get('subclass') or '')
    if ctype != 'JNumber' and subclass != 'JNumber':
        print('NOT_JNUMBER component=%s subclass=%s（环比只写数字卡）' % (ctype, subclass))
        sys.exit(1)

    an = cfg.get('analysis') or {}
    if not compare_type:
        compare_type = (an.get('compareType') or '').strip() or 'preMonth'
    old_qr, need_qr = _ensure_compare_query_range(cfg, compare_type)
    if old_qr != need_qr:
        print('queryRange:%s->%s' % (old_qr, need_qr))
    old_h, new_h = _ensure_jnumber_compare_height(comp_obj, cfg)
    if old_h != new_h:
        print('H:%s->%s' % (old_h, new_h))

    title = (comp_obj.get('componentName')
             or (((cfg.get('option') or {}).get('title') or {}).get('text'))
             or 'chart')
    spec = {
        'isCompare': True,
        'compareType': compare_type,
        'compareValue': 0,
        'title': title,
    }
    if trend_raw:
        spec['trendType'] = trend_raw
    elif str(an.get('trendType') or '') in ('1', '2'):
        spec['trendType'] = str(an.get('trendType'))
    _apply_spec_compare(cfg, spec, spec_index=0)

    bi_utils._page_components[page_id] = tmpl
    bi_utils.save_page(page_id)
    _verify_jnumber_compare_after_save(page_id, [spec], added_start=0)
    print('COMPARE=%s' % title)
    print('PAGE_ID=%s' % page_id)
    print('APP_ID=%s' % app_id)
    print('耗时: %.1fs' % (time.time() - t0))


def cmd_rename_page(args):
    """已有仪表盘重命名：drag 页面 name + lowAppMenu menuName 两处同步，一条命令完成。

    QQY 仪表盘「名称」显示两处：drag 页面 name（page_ops.py rename 只改这里）
    与应用侧边栏 lowAppMenu.menuName（菜单名）。只改一处会两边不一致
    （2026-09-02 实测：页面 name 已改、侧边栏仍显旧名，须再 PUT /online/lowAppMenu/edit）。
    """
    t0 = time.time()
    new_name = (args.name or '').strip()
    if not new_name:
        print('必须提供 --name（新仪表盘名称）')
        sys.exit(1)
    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    page_id, _kw = _resolve_page_id(args, app_id)

    # 1) drag 页面改名：queryById 全量实体 → 只改 name → POST /drag/page/edit（与 page_ops.py rename 同流程）
    page = bi_utils._request('GET', '/drag/page/queryById', params={'id': page_id})
    if not page.get('success') or not page.get('result'):
        print('查询页面失败: %s' % (page.get('message') or 'result 为空'))
        sys.exit(1)
    entity = page.get('result')
    old_name = entity.get('name') or _kw
    entity['name'] = new_name
    edit_resp = bi_utils._request('POST', '/drag/page/edit', data=entity)
    if not edit_resp.get('success'):
        print('页面改名失败: %s' % edit_resp.get('message'))
        sys.exit(1)
    print('PAGE_RENAMED: "%s" → "%s"' % (old_name, new_name))

    # 2) 同步侧边栏菜单名：按 menuUrl==page_id 找 drag 菜单 → PUT /online/lowAppMenu/edit
    menus = _list_menus(app_id)
    drag = [m for m in menus if m.get('type') == 'drag'
            and str(m.get('menuUrl') or '') == str(page_id)]
    if not drag:
        print('MENU_NOT_FOUND=应用内无对应 drag 菜单（页面名已改；历史未归组页面请先 group-menu 或手工同步菜单名）')
    else:
        menu = drag[0]
        body = {
            'id': menu['id'],
            'parentId': menu.get('parentId'),
            'menuName': new_name,
            'type': 'drag',
            'menuUrl': page_id,
            'appId': app_id,
            'orderNum': menu.get('orderNum') or 1,
        }
        m_resp = bi_utils._request('PUT', '/online/lowAppMenu/edit', data=body)
        if not m_resp.get('success'):
            print('菜单改名失败: %s' % m_resp.get('message'))
            print('NOTE=页面名已改成功，仅菜单未同步')
            sys.exit(1)
        print('MENU_RENAMED=%s' % menu.get('id'))

    print('APP_ID=%s' % app_id)
    print('PAGE_ID=%s' % page_id)
    share = '%s/drag/share/%s/%s' % (_frontend_base(args.api_base), app_id, page_id)
    print('SHARE_URL=%s' % share)
    print('耗时: %.1fs' % (time.time() - t0))


def _widget_to_agg_option(f):
    """desform field → 聚合 fieldOptions 项 {title,value,type,options,name,model}。"""
    ftype = f.get('type') or f.get('widgetType') or 'input'
    model = f.get('model') or f.get('fieldName') or f.get('value') or ''
    title = f.get('name') or f.get('fieldTxt') or f.get('title') or model
    opts = f.get('options') if isinstance(f.get('options'), dict) else {}
    return {
        'title': title, 'name': title, 'value': model, 'model': model,
        'type': ftype, 'options': opts,
    }


def _load_form_field_options(form_code, as_aggregation=False):
    if as_aggregation:
        resp = bi_utils._request(
            'GET', '/drag/onlDragTableRelation/getAggregationFields/%s' % form_code)
        result = resp.get('result') or {}
        raw = result.get('fields') or []
        out = []
        for f in raw:
            if not isinstance(f, dict):
                continue
            model = f.get('model') or f.get('value') or ''
            title = f.get('name') or f.get('title') or model
            out.append({
                'title': title, 'name': title, 'value': model, 'model': model,
                'type': f.get('type') or 'string',
                'options': f.get('options') if isinstance(f.get('options'), dict) else {},
            })
        return out
    resp = bi_utils._request('GET', '/desform/api/fields/%s' % form_code,
                             params={'subTable': True})
    result = resp.get('result') or {}
    raw = result.get('fields') or []
    return [_widget_to_agg_option(f) for f in raw if isinstance(f, dict)]


def _resolve_agg_source_form(app_id, token, kind):
    """token 可以是表单名 / formCode / 聚合表 id / [聚合] 名。"""
    t = (token or '').strip()
    if not t:
        return None
    if kind == 'factory':
        rec = _find_agg_record(app_id, t, t)
        if not rec:
            return None
        opts = _load_form_field_options(rec['id'], as_aggregation=True)
        return {
            'label': rec['name'], 'value': rec['id'], 'formKey': rec['id'],
            'fieldOptions': opts, 'type': 'aggregation',
        }
    forms = _list_design_forms(app_id)
    for f in forms:
        label = f.get('label') or f.get('title') or ''
        val = f.get('value') or ''
        if t == label or t == val:
            opts = _load_form_field_options(val, as_aggregation=False)
            return {
                'label': label or val, 'value': val, 'formKey': val,
                'fieldOptions': opts, 'type': 'design',
            }
    rec = _find_agg_record(app_id, t, t)
    if rec and kind != 'factory':
        # 普通聚合表的源不能是工厂；但允许误把聚合 id 当 formCode
        return None
    return None


def _find_field_opt(field_options, token):
    t = (token or '').strip()
    if not t:
        return None
    exact = [f for f in field_options if t in (
        f.get('title'), f.get('name'), f.get('value'), f.get('model'))]
    if len(exact) == 1:
        return exact[0]
    if exact:
        return exact[0]
    contains = [f for f in field_options
                if t in (f.get('title') or '') or t in (f.get('name') or '')]
    return contains[0] if contains else None


def _agg_widget_type(field):
    return str((field or {}).get('type') or (field or {}).get('widgetType') or '').lower().replace('_', '-')


_AGG_NUM_TYPES = ('money', 'integer', 'number', 'rate', 'slider', 'formula', 'summary')


def _agg_types_compatible(left_type, right_type):
    """对齐 DBFormTable.vue：同 type，或同属数值族，或任一侧是他表字段 link-field。"""
    a, b = (left_type or ''), (right_type or '')
    if a == b:
        return True
    if a in _AGG_NUM_TYPES and b in _AGG_NUM_TYPES:
        return True
    if a == 'link-field' or b == 'link-field':
        return True
    return False


def _build_calc_formula(expr, form_list):
    """把「入库数量-出库数量」编译成 $name@model@formCode@common$。"""
    s = str(expr or '').strip()
    if s.startswith('$') and '@' in s:
        return s
    # 长标题优先替换，避免「入库数量」被「数量」抢先
    pairs = []
    for form in form_list:
        for f in form.get('fieldOptions') or []:
            title = (f.get('title') or f.get('name') or '').strip()
            if not title:
                continue
            token = '$%s@%s@%s@common$' % (
                title.replace('/', '').replace('(', '').replace(')', ''),
                f.get('value') or f.get('model'),
                form.get('value'))
            pairs.append((title, token))
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    out = s
    for title, token in pairs:
        if title and title in out:
            out = out.replace(title, token)
    return out


def _load_specs_obj(args):
    """save-agg 用对象；若是数组取第一项。"""
    raw = getattr(args, 'specs', None) or ''
    path = getattr(args, 'specs_file', None) or ''
    if path:
        raw = _read_json_text(path)
    if raw is None or not str(raw).strip():
        print('必须提供 --specs-file 或 --specs')
        sys.exit(1)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print('--specs JSON 解析失败: %s' % e)
        sys.exit(1)
    if isinstance(data, list):
        if not data:
            print('--specs 空数组')
            sys.exit(1)
        data = data[0]
    if not isinstance(data, dict):
        print('--specs 必须是 JSON 对象')
        sys.exit(1)
    return data


def cmd_save_agg(args):
    """创建或编辑聚合表 / 聚合工厂（数据来源+行表头+公式+过滤）。"""
    t0 = time.time()
    spec = _load_specs_obj(args)
    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)

    name = (spec.get('name') or spec.get('aggregationName') or getattr(args, 'name', None) or '').strip()
    if not name:
        print('必须提供 name / --name 聚合表名称')
        sys.exit(1)
    desc = spec.get('desc') or spec.get('aggregationDesc') or ''
    kind_raw = str(spec.get('kind') or spec.get('formType') or spec.get('type') or 'multi').strip().lower()
    kind_map = {
        'single': 'single', '单表': 'single', '1': 'single',
        'multi': 'multi', '关联': 'multi', '聚合表': 'multi', '2': 'multi',
        'factory': 'factory', 'aggregation': 'factory', '工厂': 'factory',
        '聚合工厂': 'factory', '3': 'factory',
    }
    kind = kind_map.get(kind_raw, 'multi')
    form_type = 'aggregation' if kind == 'factory' else kind
    join_raw = str(spec.get('join') or spec.get('relationMode') or 'left').strip().lower()
    join_map = {'left': 'left', '左': 'left', '左连接': 'left',
                'inner': 'inner', '内': 'inner', '内连接': 'inner',
                'all': 'all', '全': 'all', '全连接': 'all'}
    if kind == 'factory' and join_raw in ('inner', '内', '内连接'):
        print('NOTE=聚合工厂无内连接，已改为 left')
        join_raw = 'left'
    relation_mode = join_map.get(join_raw, 'left')

    form_toks = spec.get('forms') or spec.get('sources') or []
    if isinstance(form_toks, str):
        form_toks = [p.strip() for p in re.split(r'[,，]+', form_toks) if p.strip()]
    form_list = []
    for tok in form_toks:
        if isinstance(tok, dict):
            tok = tok.get('name') or tok.get('code') or tok.get('value') or tok.get('label')
        src = _resolve_agg_source_form(app_id, tok, kind)
        if not src:
            print('AGG_SOURCE_NOT_FOUND=%s kind=%s' % (tok, kind))
            sys.exit(1)
        form_list.append(src)
        print('SOURCE=%s\t%s\tfields=%d' % (src['value'], src['label'], len(src['fieldOptions'])))
    if kind == 'single' and len(form_list) != 1:
        print('单表聚合必须恰好 1 个 forms')
        sys.exit(1)
    if kind in ('multi', 'factory') and len(form_list) < 1:
        print('关联/工厂至少 1 个 forms')
        sys.exit(1)

    field_list = []
    if kind == 'single' and form_list:
        fc = form_list[0]['value']
        field_list = [{fc: f['value']} for f in form_list[0]['fieldOptions']]
    else:
        links = spec.get('links') or spec.get('joinFields') or spec.get('fieldList') or []
        if isinstance(links, dict):
            links = [links]
        if links:
            for link in links:
                if isinstance(link, str) and '=' in link:
                    left_t, right_t = [x.strip() for x in link.split('=', 1)]
                    link = {'left': left_t, 'right': right_t}
                if not isinstance(link, dict):
                    continue
                row = {}
                if len(form_list) >= 1:
                    lf = _find_field_opt(form_list[0]['fieldOptions'],
                                         link.get('left') or link.get(form_list[0]['value']))
                    if not lf:
                        print('LINK_FIELD_NOT_FOUND form=%s token=%s' % (
                            form_list[0]['label'], link.get('left')))
                        sys.exit(1)
                    row[form_list[0]['value']] = lf['value']
                if len(form_list) >= 2:
                    rf = _find_field_opt(form_list[1]['fieldOptions'],
                                         link.get('right') or link.get(form_list[1]['value']))
                    if not rf:
                        print('LINK_FIELD_NOT_FOUND form=%s token=%s' % (
                            form_list[1]['label'], link.get('right')))
                        sys.exit(1)
                    lt, rt = _agg_widget_type(lf), _agg_widget_type(rf)
                    if not _agg_types_compatible(lt, rt):
                        print('LINK_TYPE_MISMATCH left=%s(%s) right=%s(%s)' % (
                            lf.get('title'), lt, rf.get('title'), rt))
                        if 'link-record' in (lt, rt) and ('input' in (lt, rt) or 'textarea' in (lt, rt)):
                            print('NOTE=多表 $lookup 按字段值相等连接。关联记录存对表_id，不能对标题文本，也不要对表反向关联记录（存的是本表id）。要按关联记录名称分组请用单表，行表头直接选该关联记录。')
                        sys.exit(1)
                    row[form_list[1]['value']] = rf['value']
                # 多表：其余键按表名
                for frm in form_list[2:]:
                    tok = link.get(frm['label']) or link.get(frm['value'])
                    if tok:
                        fo = _find_field_opt(frm['fieldOptions'], tok)
                        if fo:
                            row[frm['value']] = fo['value']
                field_list.append(row)
        else:
            # 无 links：按同名标题自动配对
            if len(form_list) >= 2:
                titles0 = {f['title']: f for f in form_list[0]['fieldOptions']}
                for f1 in form_list[1]['fieldOptions']:
                    f0 = titles0.get(f1['title'])
                    if f0:
                        field_list.append({
                            form_list[0]['value']: f0['value'],
                            form_list[1]['value']: f1['value'],
                        })
                print('NOTE=未传 links，按同名标题自动配对 %d 行' % len(field_list))
    if kind in ('multi', 'factory'):
        # 多表/工厂连接行必须带行 id（前端按 id 渲染连接配置，2026-09-08 手修教训）
        for _i, _row in enumerate(field_list, 1):
            _row.setdefault('id', 'row_%d' % _i)

    header_fields = []
    header_toks = spec.get('headers') or spec.get('headerFields') or []
    if isinstance(header_toks, str):
        header_toks = [p.strip() for p in re.split(r'[,，]+', header_toks) if p.strip()]
    form_keys = [f['value'] for f in form_list]
    if header_toks:
        for tok in header_toks:
            dict_val = ''
            if isinstance(tok, dict):
                dict_val = str(tok.get('value') or '')
                t = str(tok.get('name') or tok.get('value') or '')
            else:
                t = str(tok)
            found = None
            for row in field_list:
                names, vals = [], []
                for key in form_keys:
                    fo = next((f for f in (next(
                        (frm['fieldOptions'] for frm in form_list if frm['value'] == key), [])
                    ) if f['value'] == row.get(key)), None)
                    if fo:
                        names.append(fo['title'])
                        vals.append(fo['value'])
                chain_name = '-'.join(names)
                chain_val = '-'.join(vals)
                if t in names or t in (chain_name, chain_val) or (
                        dict_val and (dict_val in vals or dict_val == chain_val)):
                    found = {'name': chain_name, 'value': chain_val}
                    break
            if not found and kind == 'single' and form_list:
                fo = _find_field_opt(form_list[0]['fieldOptions'], t or dict_val)
                if fo:
                    found = {'name': fo['title'], 'value': fo['value']}
                elif dict_val:
                    found = {'name': t or dict_val, 'value': dict_val}
            if not found:
                print(('HEADER_NOT_IN_LINKS=%s' if kind != 'single' else 'HEADER_NOT_FOUND=%s') % (t or dict_val))
                sys.exit(1)
            header_fields.append(found)
    elif field_list and form_list:
        # 默认：第一行映射当行表头
        row = field_list[0]
        names, vals = [], []
        for key in form_keys:
            fo = next((f for f in (next(
                (frm['fieldOptions'] for frm in form_list if frm['value'] == key), [])
            ) if f['value'] == row.get(key)), None)
            if fo:
                names.append(fo['title'])
                vals.append(fo['value'])
        if vals:
            header_fields.append({'name': '-'.join(names), 'value': '-'.join(vals)})

    calc_fields = []
    for c in (spec.get('calcs') or spec.get('calculateFields') or []):
        if isinstance(c, str):
            if '=' in c:
                cname, expr = [x.strip() for x in c.split('=', 1)]
            else:
                cname, expr = '公式', c
            c = {'name': cname, 'expr': expr}
        if not isinstance(c, dict):
            continue
        cname = (c.get('name') or '公式').strip()
        expr = c.get('expr') or c.get('formula') or c.get('formulas') or ''
        formulas = _build_calc_formula(expr, form_list)
        calc_fields.append({
            'id': c.get('id') or uuid.uuid4().hex,
            'name': cname,
            'formulas': formulas,
        })
        print('CALC=%s %s' % (cname, formulas))

    filter_condition = spec.get('filters') or spec.get('filterCondition') or []
    if isinstance(filter_condition, dict):
        filter_condition = [filter_condition]
    built_filters = []
    for flt in filter_condition:
        if not isinstance(flt, dict):
            continue
        form_tok = flt.get('form') or flt.get('formName') or (form_list[0]['label'] if form_list else '')
        frm = next((f for f in form_list if form_tok in (f['label'], f['value'])), None)
        if not frm:
            print('FILTER_FORM_NOT_FOUND=%s' % form_tok)
            sys.exit(1)
        fo = _find_field_opt(frm['fieldOptions'], flt.get('field') or flt.get('title'))
        if not fo:
            print('FILTER_FIELD_NOT_FOUND=%s' % (flt.get('field') or flt.get('title')))
            sys.exit(1)
        rule = flt.get('rule') or flt.get('op') or flt.get('mode') or 'eq'
        rule_map = {
            '等于': 'eq', 'eq': 'eq', '1': 'eq',
            '包含': 'like', 'like': 'like', '2': 'like',
            '不等于': 'ne', 'ne': 'ne',
        }
        built_filters.append({
            'form': {'label': frm['label'], 'value': frm['value'],
                     'fieldOptions': frm['fieldOptions']},
            'title': fo['title'],
            'name': fo['title'],
            'field': fo['value'],
            'type': fo.get('type') or 'input',
            'options': fo.get('options') or {},
            'rule': rule_map.get(str(rule), str(rule)),
            'val': flt.get('value') if 'value' in flt else flt.get('val'),
        })

    relation_forms = {
        'formList': [{'label': f['label'], 'value': f['value'],
                      'fieldOptions': [dict(fo, children=fo.get('children', []))
                                       for fo in f['fieldOptions']]
                      if form_type == 'aggregation' else f['fieldOptions']} for f in form_list],
        'fieldList': field_list,
        'formType': form_type,
        'relationMode': relation_mode,
    }
    body = {
        'aggregationName': name,
        'aggregationDesc': desc,
        'relationForms': json.dumps(relation_forms, ensure_ascii=False),
        'filterCondition': json.dumps(built_filters, ensure_ascii=False),
        'headerFields': json.dumps(header_fields, ensure_ascii=False),
        'calculateFields': json.dumps(calc_fields, ensure_ascii=False),
        'validateInfo': json.dumps([], ensure_ascii=False),
    }
    exist = _find_agg_record(app_id, spec.get('id') or getattr(args, 'agg_id', None) or '', name)
    if exist and (spec.get('id') or getattr(args, 'agg_id', None) or spec.get('update') or True):
        # 同名则更新；新建时若要强制新记录传 spec.new=true
        if spec.get('new') is True:
            exist = None
    if exist:
        body['id'] = exist['id']
        resp = bi_utils._request('PUT', '/drag/onlDragTableRelation/edit', data=body)
        action = 'edit'
        agg_id = exist['id']
    else:
        resp = bi_utils._request('POST', '/drag/onlDragTableRelation/add', data=body)
        action = 'add'
        agg_id = str(((resp.get('result') or {}) if isinstance(resp.get('result'), dict)
                      else {}) .get('id') or '')
        if not agg_id:
            # 再查一次
            rec = _find_agg_record(app_id, '', name)
            agg_id = rec['id'] if rec else ''
    if not resp.get('success'):
        print('SAVE_AGG_FAIL %s %s' % (action, resp.get('message')))
        sys.exit(1)
    print('AGG_SAVED=%s' % agg_id)
    print('AGG_ACTION=%s' % action)
    print('AGG_NAME=%s' % name)
    print('AGG_KIND=%s' % kind)
    print('HEADERS=%d CALCS=%d FILTERS=%d LINKS=%d' % (
        len(header_fields), len(calc_fields), len(built_filters), len(field_list)))
    print('耗时: %.1fs' % (time.time() - t0))


def cmd_delete_agg(args):
    t0 = time.time()
    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    rec = _find_agg_record(app_id, getattr(args, 'agg_id', None) or '',
                           getattr(args, 'name', None) or '')
    if not rec:
        print('AGG_NOT_FOUND')
        sys.exit(1)
    resp = bi_utils._request('DELETE', '/drag/onlDragTableRelation/delete',
                             params={'id': rec['id']})
    if not resp.get('success'):
        print('DELETE_AGG_FAIL %s' % resp.get('message'))
        sys.exit(1)
    print('AGG_DELETED=%s' % rec['id'])
    print('AGG_NAME=%s' % rec['name'])
    print('耗时: %.1fs' % (time.time() - t0))


def _open_one_chart(args, require_name=True):
    """定位应用/页/一张图。返回 (t0, app_id, page_id, tmpl, comp, cfg)。"""
    t0 = time.time()
    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    page_id, _page_name = _resolve_page_id(args, app_id)
    page = bi_utils.query_page(page_id)
    tmpl = page.get('template') or []
    if isinstance(tmpl, str):
        tmpl = json.loads(tmpl)
    name = getattr(args, 'name', None)
    match_dim = getattr(args, 'match_dim', None)
    comp = getattr(args, 'comp', None)
    if require_name and not (name or '').strip() and not (match_dim or '').strip() and not (comp or '').strip():
        print('必须提供 --name / --match-dim / --comp')
        sys.exit(1)
    if (comp or '').strip():
        comp = _norm_comp_alias(comp) or comp
    hits = _find_chart_for_rebind(
        tmpl, name=name, match_dim=match_dim, comp=comp, match_calc=False)
    if (not hits and (comp or '').strip()
            and not (name or '').strip() and not (match_dim or '').strip()):
        want = _norm_comp_alias(comp) or (comp or '').strip()
        for c in tmpl or []:
            if (c.get('component') or '') == want:
                hits.append(c)
    if not hits:
        print('CHART_NOT_FOUND name=%s match_dim=%s comp=%s' % (
            name or '', match_dim or '', comp or ''))
        for c in tmpl:
            print('CAND\t%s\t%s' % (c.get('componentName'), c.get('component')))
        sys.exit(1)
    if len(hits) > 1:
        print('CHART_AMBIGUOUS count=%d' % len(hits))
        for c in hits:
            print('CAND\t%s\t%s' % (c.get('componentName'), c.get('component')))
        sys.exit(1)
    comp_obj = hits[0]
    cfg = _comp_cfg(comp_obj)
    return t0, app_id, page_id, tmpl, comp_obj, cfg


def _save_chart_mutate(page_id, app_id, tmpl, comp_obj, t0, ok_key):
    bi_utils._page_components[page_id] = tmpl
    bi_utils.save_page(page_id)
    title = (comp_obj.get('componentName')
             or (((comp_obj.get('config') or {}).get('option') or {}).get('title') or {}).get('text')
             or ok_key)
    print('%s=%s' % (ok_key, title))
    print('PAGE_ID=%s' % page_id)
    print('APP_ID=%s' % app_id)
    print('耗时: %.1fs' % (time.time() - t0))


def _norm_minutes(raw):
    """每5分钟 / 5min / 300秒 / 五分钟 → int 分钟。"""
    s = str(raw or '').strip().lower().replace('每', '')
    if not s:
        return None
    cn = {'一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5,
          '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
    for k, v in cn.items():
        s = s.replace(k, str(v))
    num = re.search(r'([\d.]+)', s)
    if not num:
        return None
    val = float(num.group(1))
    if '秒' in s or re.search(r'\d\s*s$', s) or 'sec' in s:
        return max(1, int(round(val / 60.0)))
    if '小时' in s or 'hour' in s or re.search(r'\d\s*h$', s):
        return int(val * 60)
    return int(val)


def cmd_set_chart_refresh(args):
    """已有图打开定时刷新。--minutes 口语原样（每5分钟/5min/300秒）。"""
    minutes = getattr(args, 'minutes', None)
    if minutes in (None, ''):
        print('必须提供 --minutes（口语：5 / 每5分钟 / 300秒）')
        sys.exit(1)
    minutes = _norm_minutes(minutes)
    if not minutes:
        print('MINUTES_UNKNOWN=%s' % getattr(args, 'minutes', ''))
        sys.exit(1)
    t0, app_id, page_id, tmpl, comp_obj, cfg = _open_one_chart(args)
    analysis = cfg.setdefault('analysis', {})
    analysis['izTimeOut'] = True
    analysis['timeOut'] = minutes
    cfg['timeOut'] = minutes
    print('REFRESH_MINUTES=%d' % minutes)
    _save_chart_mutate(page_id, app_id, tmpl, comp_obj, t0, 'REFRESH_SET')


def cmd_set_chart_summary(args):
    """已有图打开总计：showTotal + showField=all + totalType=average/sum。"""
    t0, app_id, page_id, tmpl, comp_obj, cfg = _open_one_chart(args)
    ss = cfg.setdefault('compStyleConfig', {}).setdefault('summary', {})
    ss['showY'] = True
    ss['showTotal'] = not bool(getattr(args, 'off', False))
    field = (getattr(args, 'field', None) or 'all').strip() or 'all'
    if field in ('全部', 'all', '全部字段'):
        field = 'all'
    ss['showField'] = field
    raw_type = (getattr(args, 'total_type', None) or 'sum').strip()
    alias = {
        '平均': 'average', '平均值': 'average', 'avg': 'average', 'average': 'average',
        '求和': 'sum', 'sum': 'sum', '合计': 'sum',
        '最大': 'max', 'max': 'max', '最小': 'min', 'min': 'min',
    }
    ss['totalType'] = alias.get(raw_type) or alias.get(raw_type.lower()) or raw_type
    if ss['totalType'] == 'avg':
        ss['totalType'] = 'average'
    ss.setdefault('showName', '总计')
    print('SUMMARY=showTotal=%s showField=%s totalType=%s' % (
        ss['showTotal'], ss['showField'], ss['totalType']))
    _save_chart_mutate(page_id, app_id, tmpl, comp_obj, t0, 'SUMMARY_SET')


def cmd_set_pivot(args):
    """透视表前 N 行/列、开/关行合计列合计。"""
    t0, app_id, page_id, tmpl, comp_obj, cfg = _open_one_chart(args)
    pt = cfg.get('pivotTable')
    if not isinstance(pt, dict):
        print('NOT_PIVOT component=%s' % (comp_obj.get('component') or ''))
        sys.exit(1)
    notes = []
    row_n = getattr(args, 'row_n', None)
    col_n = getattr(args, 'col_n', None)
    if row_n not in (None, ''):
        pt['showLineCount'] = int(row_n)
        notes.append('showLineCount=%s' % pt['showLineCount'])
    if col_n not in (None, ''):
        pt['showColumnCount'] = int(col_n)
        notes.append('showColumnCount=%s' % pt['showColumnCount'])
    lt = getattr(args, 'line_total', None)
    if lt not in (None, ''):
        pt['showLineTotal'] = _truthy_flag(lt)
        notes.append('showLineTotal=%s' % pt['showLineTotal'])
    ct = getattr(args, 'column_total', None)
    if ct not in (None, ''):
        pt['showColumnTotal'] = _truthy_flag(ct)
        notes.append('showColumnTotal=%s' % pt['showColumnTotal'])
    if not notes:
        print('必须提供 --row-n / --col-n / --line-total / --column-total')
        sys.exit(1)
    print('PIVOT=%s' % ';'.join(notes))
    _save_chart_mutate(page_id, app_id, tmpl, comp_obj, t0, 'PIVOT_SET')


def cmd_delete_page(args):
    """删除仪表盘页（逻辑删除）。"""
    t0 = time.time()
    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    page_id, page_name = _resolve_page_id(args, app_id)
    menus = _list_menus(app_id)
    menu_id = None
    for m in menus:
        if m.get('type') == 'drag' and str(m.get('menuUrl')) == str(page_id):
            menu_id = m.get('id')
            break
    bi_utils.delete_page(page_id, physical=bool(getattr(args, 'physical', False)))
    if menu_id:
        try:
            resp = bi_utils._request('DELETE', '/online/lowAppMenu/delete', params={'id': menu_id})
            print('MENU_DELETED=%s success=%s' % (menu_id, resp.get('success')))
        except Exception as e:
            print('NOTE=菜单删除跳过: %s' % e)
    print('DELETED=%s' % page_id)
    print('PAGE_NAME=%s' % (page_name or ''))
    print('APP_ID=%s' % app_id)
    print('耗时: %.1fs' % (time.time() - t0))


def cmd_set_form_chart(args):
    """工作表右侧统计改查询范围。"""
    t0 = time.time()
    qr_raw = (getattr(args, 'query_range', None) or '').strip()
    query_range = _norm_query_range(qr_raw) if qr_raw else None
    if not query_range:
        print('必须提供 --query-range（全部/本月/本周…）')
        sys.exit(1)
    title = _norm_title(getattr(args, 'title', None) or '')
    if not title:
        print('必须提供 --title')
        sys.exit(1)
    tab = (getattr(args, 'chart_tab', None) or 'private').strip()
    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    form_code, form_name = _resolve_form(
        app_id,
        getattr(args, 'form_code', None) or '',
        getattr(args, 'form_name', None) or '',
    )
    print('FORM_CODE=%s FORM_NAME=%s' % (form_code, form_name))
    cands, _items = _find_form_chart_cands(form_code, tab, title)
    if not cands:
        print('NOT_FOUND title=%s type=%s' % (title, tab))
        sys.exit(1)
    for x in cands:
        chart_id = x.get('chartId')
        q = bi_utils._request('GET', '/drag/page/comp/queryById', params={'id': chart_id})
        r = q.get('result') or {}
        inner, inner_cfg = _unwrap_comp_config(r)
        fl = inner_cfg.setdefault('filter', {}) if isinstance(inner_cfg, dict) else {}
        old = fl.get('queryRange')
        fl['queryRange'] = query_range
        nested = inner if isinstance(inner, dict) else {}
        nested['config'] = inner_cfg
        nested['component'] = nested.get('component') or r.get('component')
        nested['id'] = nested.get('id') or chart_id
        edit = bi_utils._request('POST', '/drag/page/comp/edit', data={
            'id': chart_id,
            'component': nested.get('component'),
            'config': json.dumps(nested, ensure_ascii=False),
        })
        print('FORM_CHART_SET title=%s queryRange=%s->%s success=%s' % (
            title, old, query_range, edit.get('success')))
        if not edit.get('success'):
            print('EDIT_FAIL=%s' % json.dumps(edit, ensure_ascii=False)[:400])
            sys.exit(1)
    print('PAGE_ID=form-chart')
    print('耗时: %.1fs' % (time.time() - t0))


_UI_COMPS = {
    'JText': ('文本', 24, 10),
    'JDragEditor': ('富文本', 24, 20),
    'JCarousel': ('轮播图', 12, 25),
    'JIframe': ('嵌入URL', 24, 35),
    'JCurrentTime': ('实时日期', 8, 10),
}
_UI_ALIAS = {
    '文本': 'JText', '纯文本': 'JText', '标题': 'JText', '大标题': 'JText',
    '富文本': 'JDragEditor', '编辑器': 'JDragEditor',
    '轮播': 'JCarousel', '轮播图': 'JCarousel',
    'iframe': 'JIframe', '嵌入': 'JIframe', '嵌入url': 'JIframe',
    '时钟': 'JCurrentTime', '实时日期': 'JCurrentTime',
}


def cmd_add_ui(args):
    """已有盘加 UI：JText / JDragEditor / JCarousel / JIframe / JCurrentTime。comp/add+saveCompToPage。"""
    t0 = time.time()
    raw = (getattr(args, 'comp', None) or '').strip()
    comp = _UI_ALIAS.get(raw) or _UI_ALIAS.get(raw.lower()) or raw
    if comp not in _UI_COMPS:
        print('UI_COMP_UNKNOWN=%s 允许=JText/JDragEditor/JCarousel/JIframe/JCurrentTime' % raw)
        sys.exit(1)
    _init(args)
    app_id = _resolve_app_id(args)
    args.app_id = app_id
    _init(args)
    page_id, _page_name = _resolve_page_id(args, app_id)
    default_w, default_h = _UI_COMPS[comp][1], _UI_COMPS[comp][2]
    w_raw = getattr(args, 'w', None)
    h_raw = getattr(args, 'h', None)
    x_raw = getattr(args, 'x', None)
    y_raw = getattr(args, 'y', None)
    x = int(x_raw) if x_raw not in (None, '') else 0
    title = (getattr(args, 'title', None) or _UI_COMPS[comp][0]).strip()
    text_preview = (getattr(args, 'text', None) or title or '').strip()
    style_blob = ' '.join([
        raw, title, text_preview,
        str(getattr(args, 'style', None) or ''),
        str(getattr(args, 'align', None) or ''),
        str(getattr(args, 'font_size', None) or ''),
    ])
    headline = any(k in style_blob for k in ('大标题', '大字', '标题加大'))
    want_bold = bool(getattr(args, 'bold', False)) or any(
        k in style_blob for k in ('加粗', '粗体', 'bold'))
    align_raw = (getattr(args, 'align', None) or '').strip()
    if '居中' in style_blob or align_raw in ('center', '居中'):
        align = 'center'
    elif '右' in style_blob or align_raw in ('right', '右'):
        align = 'right'
    elif '左' in style_blob or align_raw in ('left', '左'):
        align = 'left'
    else:
        align = 'center'
    fs_raw = str(getattr(args, 'font_size', None) or '').strip()
    font_size = None
    if fs_raw.isdigit():
        font_size = int(fs_raw)
    elif fs_raw in ('大', '大号', 'headline'):
        font_size = 28
        headline = True
    if headline:
        font_size = font_size or 28
        want_bold = True
        align = 'center'
    if w_raw not in (None, ''):
        w = int(w_raw)
    elif headline or any(k in style_blob for k in ('整行', '通栏', '全宽')):
        w = 24
    else:
        w = default_w
    h = int(h_raw) if h_raw not in (None, '') else default_h
    CARD = {'title': '', 'extra': '', 'rightHref': '', 'size': 'default'}

    page = bi_utils.query_page(page_id)
    tmpl = page.get('template') or []
    if isinstance(tmpl, str):
        try:
            tmpl = json.loads(tmpl)
        except Exception:
            tmpl = []
    update_count = page.get('updateCount')
    # 落位：--y 显式指定 > --place top（顶部插入并把已有组件整体下移）> 默认追加到底部。
    # 模版的页头横幅就是「y=0 整行 JText + 其余组件整体下移」——没有 place=top 就只能叠在图上。
    ui_place = (getattr(args, 'place', None) or '').strip() or 'bottom'
    if y_raw in (None, '') and ui_place == 'top':
        shift = 0
        if comp == 'JText':
            shift = int(h_raw) if str(h_raw or '').strip().isdigit() else default_h
        for item in tmpl:
            item['y'] = int(item.get('y') or 0) + shift
            if 'pcY' in item:
                item['pcY'] = int(item.get('pcY') or 0) + shift
        y = 0
    elif y_raw in (None, ''):
        max_bottom = 0
        for item in tmpl:
            max_bottom = max(max_bottom, int(item.get('y') or 0) + int(item.get('h') or 0))
        y = max_bottom
    else:
        y = int(y_raw)

    if comp == 'JText':
        text = (getattr(args, 'text', None) or title or '').strip()
        font_size = font_size or 22
        bold = want_bold
        # 页头横幅：模版里那种「蓝底白字居中大标题」（销售订单看板/采购订单看板/财务收支看板…）
        # = background 上色 + body.color 白 + fontSize 30 + 顶格 marginTop 0。
        # 默认仍是白底深灰字（内嵌说明文字用），要横幅就传 --bg/--color/--font-size。
        bg = (getattr(args, 'bg', None) or '').strip() or '#FFFFFF'
        fg = (getattr(args, 'fg_color', None) or '').strip() or '#464646'
        config = {
            'dataType': 1, 'url': '', 'timeOut': 0, 'linkageConfig': [],
            'turnConfig': {'url': ''}, 'chartData': text,
            'background': bg, 'borderColor': '#E8E8E8',
            'size': {'width': w * 75, 'height': h * 11},
            'option': {
                'horseLamp': False, 'speed': 1000, 'card': dict(CARD),
                'textAlign': align,
                'body': {
                    'text': text, 'color': fg,
                    'fontWeight': 'bold' if bold else 'normal',
                    'marginLeft': 0,
                    'marginTop': 0 if bg != '#FFFFFF' else 8,
                    'letterSpacing': 0,
                    'fontSize': font_size, 'textAlign': align,
                },
            },
        }
    elif comp == 'JDragEditor':
        html = (getattr(args, 'html', None) or getattr(args, 'text', None) or '<p></p>').strip()
        config = {
            'dataType': 1, 'timeOut': 0, 'chartData': html,
            'background': '#FFFFFF', 'borderColor': '#E8E8E8',
            'size': {'width': w * 75, 'height': h * 11},
        }
    elif comp == 'JIframe':
        url = (getattr(args, 'url', None) or '').strip()
        if not url:
            print('JIframe 必须 --url')
            sys.exit(1)
        config = {
            'dataType': 1, 'url': '', 'timeOut': 0, 'chartData': url,
            'background': '#FFFFFF', 'borderColor': '#E8E8E8',
            'size': {'width': w * 75, 'height': h * 11},
            'option': {'card': dict(CARD), 'body': {'url': url}},
        }
    elif comp == 'JCurrentTime':
        week = (getattr(args, 'week', None) or 'show').strip() or 'show'
        if week in ('1', 'true', 'yes', '是'):
            week = 'show'
        if week in ('0', 'false', 'no', '否', 'hide'):
            week = 'hide'
        if week not in ('show', 'hide'):
            week = 'show'
        config = {
            'dataType': 1, 'url': '', 'timeOut': 0, 'turnConfig': {'url': ''},
            'chartData': '', 'background': '#3F7DD4', 'borderColor': '#E8E8E8',
            'size': {'width': w * 75, 'height': h * 11},
            'option': {
                'showWeek': week, 'hourlySystem': '24',
                'format': 'YYYY-MM-DD hh:mm:ss', 'card': dict(CARD),
                'body': {'text': '', 'color': '#FFFFFF', 'fontWeight': 'normal',
                         'marginLeft': 0, 'marginTop': 13, 'letterSpacing': 0},
            },
        }
    else:
        form_name = (getattr(args, 'form_name', None) or '').strip()
        form_code = (getattr(args, 'form_code', None) or '').strip()
        max_count = int(getattr(args, 'max_count', None) or 3)
        autoplay = not bool(getattr(args, 'no_autoplay', False))
        code, fname = '', ''
        img_field = ''
        if form_name or form_code:
            code, fname = _resolve_form(app_id, form_code, form_name)
            fa = type('A', (), {})()
            fa.form_code = code
            fa.form_name = fname
            fa.form_type = 'design'
            fields, fname, _ft = _load_fields(fa)
            for f in fields:
                wt = (f.get('widgetType') or f.get('type') or '').lower()
                if wt in ('imgupload', 'photo', 'image'):
                    img_field = f.get('fieldName') or ''
                    break
            print('CAROUSEL_FIELD=%s FORM=%s' % (img_field, fname))
        config = {
            'dataType': 1, 'url': '', 'timeOut': 0, 'linkageConfig': [],
            'dataMapping': [{'filed': '路径', 'mapping': ''}],
            'maxCount': max_count, 'showMode': 'all', 'view': '',
            'option': {'autoplay': autoplay, 'dots': True, 'dotPosition': 'bottom',
                       'easing': 'linear'},
            'chartData': [
                {'src': 'https://jeecgos.oss-cn-beijing.aliyuncs.com/files/site/drag/0.png'},
                {'src': 'https://jeecgos.oss-cn-beijing.aliyuncs.com/files/site/drag/1.png'},
                {'src': 'https://jeecgos.oss-cn-beijing.aliyuncs.com/files/site/drag/2.png'},
            ][:max(1, max_count)],
            'background': '#FFFFFF', 'borderColor': '#E8E8E8',
            'size': {'width': w * 75, 'height': h * 11},
        }
        if code:
            config['worksheet'] = {'label': fname, 'value': code, 'key': code}
            config['field'] = img_field
            config['appInfo'] = {'label': '', 'value': app_id}

    add_resp = bi_utils._request('POST', '/drag/page/comp/add', data={
        'pageId': page_id,
        'component': comp,
        'config': json.dumps(config, ensure_ascii=False),
    })
    if not add_resp.get('success'):
        print('comp/add 失败: %s' % add_resp.get('message'))
        sys.exit(1)
    page_comp_id = str((add_resp.get('result') or {}).get('id') or add_resp.get('result') or '')
    if not page_comp_id or page_comp_id == 'None':
        print('comp/add 未返回 id: %s' % json.dumps(add_resp, ensure_ascii=False)[:500])
        sys.exit(1)
    new_item = {
        'w': w, 'h': h, 'i': str(uuid.uuid4()),
        'x': x, 'y': y, 'orderNum': 0,
        'pageCompId': page_comp_id,
        'component': comp, 'componentName': title, 'visible': True,
        'pcX': x, 'pcY': y, 'pcW': w,
    }
    clean = [_template_meta(new_item)] + [_template_meta(it) for it in tmpl]
    save_resp = bi_utils._request('POST', '/drag/page/saveCompToPage', data={
        'id': page_id,
        'template': json.dumps(clean, ensure_ascii=False),
        'updateCount': update_count,
    })
    if not save_resp.get('success'):
        print('saveCompToPage 失败: %s' % save_resp.get('message'))
        sys.exit(1)
    print('ADDED=%s' % comp)
    print('PAGE_COMP_ID=%s' % page_comp_id)
    print('APP_ID=%s' % app_id)
    print('PAGE_ID=%s' % page_id)
    print('耗时: %.1fs' % (time.time() - t0))


def _drill_resolve_model(cfg, tok):
    tok = str(tok or '').strip()
    pools = list(cfg.get('nameFields') or []) + list(cfg.get('valueFields') or [])
    pools += list(cfg.get('filterField') or [])
    if not tok:
        nfs = cfg.get('nameFields') or []
        return (nfs[0].get('fieldName') if nfs else '') or ''
    for f in pools:
        if not isinstance(f, dict):
            continue
        if f.get('fieldName') == tok or f.get('fieldTxt') == tok:
            return f.get('fieldName') or tok
    for f in pools:
        if not isinstance(f, dict):
            continue
        if tok in str(f.get('fieldTxt') or '') or tok in str(f.get('fieldName') or ''):
            return f.get('fieldName') or tok
    return tok


def cmd_add_drill(args):
    """已有图加钻取。--mapping 可中文维名；省略则用图上第一个维度。"""
    t0, app_id, page_id, tmpl, comp_obj, cfg = _open_one_chart(args)
    mapping_raw = (getattr(args, 'mapping', None) or '').strip()
    dim_tok = (getattr(args, 'dim', None) or '').strip()
    src = 'name'
    tgt = ''
    if mapping_raw:
        if '=' in mapping_raw:
            src, tgt = mapping_raw.split('=', 1)
            src, tgt = src.strip() or 'name', tgt.strip()
        else:
            tgt = mapping_raw
    elif dim_tok:
        tgt = dim_tok
    tgt = _drill_resolve_model(cfg, tgt)
    if not tgt:
        print('DRILL_NO_DIM')
        sys.exit(1)
    cfg['drillData'] = [{'source': src, 'target': tgt}]
    print('DRILL_MAP=%s=%s' % (src, tgt))
    _save_chart_mutate(page_id, app_id, tmpl, comp_obj, t0, 'DRILLED')


def main():
    parser = argparse.ArgumentParser(description='QQY 低代码应用仪表盘通用操作')
    sub = parser.add_subparsers(dest='command')

    def add_auth(p, need_app=True, need_page=False):
        p.add_argument('api_base')
        p.add_argument('token')
        p.add_argument('--tenant-id', default='', help='租户 ID，与 --tenant-name 二选一（缺省由主入口按名解析，2026-09-08）')
        p.add_argument('--tenant-name', default='', help='租户名称，与 --tenant-id 二选一；精确匹配 1 条，0 条自动去「租户/公司」后缀')
        if need_app:
            p.add_argument('--app-id', required=True)
        if need_page:
            p.add_argument('--page-id', required=True)

    def add_chart_flags(p):
        """单图捷径旗标，与 --specs-file 二选一。"""
        p.add_argument('--comp', default='', help='单图类型或中文别名（柱状图/折线图/透视表/…），免 specs-file')
        p.add_argument('--title', default='', help='单图标题')
        p.add_argument('--dim', default='', help='维度；透视多行维逗号分隔')
        p.add_argument('--val', default='', help='数值；雷达多指标逗号分隔')
        p.add_argument('--grp', default='', help='分组 / 透视列 / 多折线系列')
        p.add_argument('--assist-y', dest='assist_y', default='', help='双轴右轴数值')
        p.add_argument('--assist-type', dest='assist_type', default='', help='双轴右轴分组')
        p.add_argument('--date-group', dest='date_group', default='', help='口语：按日/每天/按月')
        p.add_argument('--query-range', dest='query_range', default='', help='all/month/week/custom 或 全部/本月')
        p.add_argument('--query-field', dest='query_field', default='')
        p.add_argument('--custom-time', dest='custom_time', default='', help='YYYY-MM-DD,YYYY-MM-DD')
        p.add_argument('--calc', default='', help='计算值公式，如 最大×平均+求和')
        p.add_argument('--color', default='', help='单色，等同 --colors；含 # $ ` 的值一律引号')
        p.add_argument('--colors', default='', help='配色口语：黄绿蓝 或 黄,绿,蓝；含 # $ ` 一律引号')
        p.add_argument('--border-radius', dest='border_radius', default='', help='柱圆角，数字或「圆角4」')
        p.add_argument('--bar-width', dest='bar_width', default='', help='柱宽')
        p.add_argument('--symbol-size', dest='symbol_size', default='', help='点大小数字；也可写进 --style')
        p.add_argument('--style', default='', help='同 --oral：点大小/圆角/柱宽/配色等整段口语')
        p.add_argument('--oral', default='',
                       help='加图需求原句。缺专用旗标把整句放这里，禁止翻文档/手写 py')
        p.add_argument('--top-n', dest='top_n', default='', help='前 N 项')
        p.add_argument('--line-type', dest='line_type', default='')
        p.add_argument('--label-show', action='store_true', dest='label_show')
        p.add_argument('--percent-label', action='store_true', dest='percent_label')
        p.add_argument('--scatter-label', action='store_true', dest='scatter_label')
        p.add_argument('--legend-show', action='store_true', dest='legend_show')
        p.add_argument('--w', default='', help='网格宽')
        p.add_argument('--h', default='', help='网格高')
        p.add_argument('--x', default='')
        p.add_argument('--y', default='')
        p.add_argument('--show-line-total', dest='show_line_total', default='', help='透视行合计 true/false')
        p.add_argument('--show-column-total', dest='show_column_total', default='', help='透视列合计')
        p.add_argument('--row-n', dest='row_n', default='', help='透视前 N 行')
        p.add_argument('--col-n', dest='col_n', default='', help='透视前 N 列')
        p.add_argument('--shape', default='',
                       help='词云形状，口语原样传入（心的形状/爱心/心形/圆形…），脚本解析')

    p_tenants = sub.add_parser('tenants', help='按名称精确匹配租户（替代坏掉的 system_creator.py query-tenants）')
    p_tenants.add_argument('api_base')
    p_tenants.add_argument('token')
    p_tenants.add_argument('--name', required=True, help='租户名称，精确匹配')

    p_apps = sub.add_parser('apps', help='列出/按名称查找应用')
    add_auth(p_apps, need_app=False)
    p_apps.add_argument('--name', default='', help='应用名称关键字（模糊匹配）')

    p_forms = sub.add_parser('forms', help='列出普通表单+聚合表')
    add_auth(p_forms, need_app=False)
    p_forms.add_argument('--app-id', default='', help='应用 ID，与 --app-name 二选一')
    p_forms.add_argument('--app-name', default='', help='应用名称（模糊匹配）')

    p_fields = sub.add_parser('fields', help='列出表单字段并给出推荐 dim/val')
    add_auth(p_fields, need_app=False)
    p_fields.add_argument('--app-id', default='', help='应用 ID，与 --app-name 二选一')
    p_fields.add_argument('--app-name', default='', help='应用名称（模糊匹配）')
    p_fields.add_argument('--form-code', default='', help='表单编码，与 --form-name 二选一')
    p_fields.add_argument('--form-name', default='', help='表单名称')
    p_fields.add_argument('--form-type', default='design',
                          choices=['design', 'aggregation', 'online'])

    p_menus = sub.add_parser('menus', help='列出应用菜单')
    add_auth(p_menus, need_app=False)
    p_menus.add_argument('--app-id', default='', help='应用 ID，与 --app-name 二选一')
    p_menus.add_argument('--app-name', default='', help='应用名称（模糊匹配）')

    p_create = sub.add_parser('create-page', help='创建 QQY 仪表盘页面（自动归组）')
    add_auth(p_create)
    p_create.add_argument('--name', required=True)
    p_create.add_argument('--group', default='', help='菜单分组名，空=应用已有第一个分组')

    p_add = sub.add_parser('add-charts', help='一次保存添加 dataType=4 统计图表')
    add_auth(p_add, need_app=False)
    p_add.add_argument('--app-id', default='', help='看板所属应用 ID，与 --app-name 二选一')
    p_add.add_argument('--app-name', default='', help='看板所属应用名称')
    p_add.add_argument('--page-id', default='', help='仪表盘页面 ID，与 --page-name 二选一')
    p_add.add_argument('--page-name', default='', help='仪表盘名称')
    p_add.add_argument('--form-code', default='', help='表单编码，与 --form-name 二选一')
    p_add.add_argument('--form-name', default='', help='表单名称')
    p_add.add_argument('--form-app-id', default='', help='跨应用表单：表单所属应用 ID')
    p_add.add_argument('--form-app-name', default='', help='跨应用表单：表单所属应用名称（如应用2）')
    p_add.add_argument('--form-type', default='design',
                       choices=['design', 'aggregation', 'online'])
    p_add.add_argument('--specs', default='',
                       help='JSON 数组。Windows PowerShell 禁止用此参数（会吃掉双引号），改用 --specs-file')
    p_add.add_argument('--specs-file', default='',
                       help='UTF-8 JSON 文件路径（推荐）。每项: comp/title/x/y/w/h/dim/val/grp/dateGroup/queryRange/queryField/customTime/calc/calcTitle/assistY/assistType/colors/percentLabel/scatterLabelShow/legendShow/unit/numberLevel/decimal/isCompare/compareType/compareValue/trendType')
    add_chart_flags(p_add)

    p_dash = sub.add_parser('create-dashboard', help='业务仪表盘一条命令：租户+应用+表单+建页+加图+归组')
    p_dash.add_argument('api_base')
    p_dash.add_argument('token')
    p_dash.add_argument('--tenant-id', default='', help='租户 ID，与 --tenant-name 二选一')
    p_dash.add_argument('--tenant-name', default='', help='租户名称，精确匹配 1 条')
    p_dash.add_argument('--app-id', default='', help='应用 ID，与 --app-name 二选一')
    p_dash.add_argument('--app-name', default='', help='应用名称（模糊匹配）')
    p_dash.add_argument('--form-code', default='', help='表单编码；应用内仅 1 张表时可省略')
    p_dash.add_argument('--form-name', default='', help='表单名称；「产品统计」可匹配「产品表」')
    p_dash.add_argument('--form-type', default='design',
                        choices=['design', 'aggregation', 'online'])
    p_dash.add_argument('--name', required=True, help='仪表盘页面名称')
    p_dash.add_argument('--group', default='', help='菜单分组名，空=归应用已有第一个分组；仅应用无分组才新建（兜底名 数据分析）')
    p_dash.add_argument('--specs', default='', help='禁止在 PowerShell 使用，改 --specs-file')
    p_dash.add_argument('--specs-file', default='',
                       help='UTF-8 JSON 图表 specs。每项字段同 add-charts（含 calc/calcTitle）')
    p_dash.add_argument('--layout-file', default='',
                        help='复合盘 JSON：{charts,buttons,afterCharts,filter}，同一进程建完')
    p_dash.add_argument('--auto', action='store_true',
                        help='自行发挥：按表字段自动 KPI+柱+折+饼+透视')
    add_chart_flags(p_dash)

    p_grp = sub.add_parser('group-menu', help='把仪表盘菜单归入分组')
    add_auth(p_grp, need_page=True)
    p_grp.add_argument('--group', default='', help='目标分组名称，空则用已有第一个分组')

    p_fc = sub.add_parser('add-form-chart', help='工作表右侧统计加一张公共/个人图（一条命令完成）')
    add_auth(p_fc, need_app=False)
    p_fc.add_argument('--app-id', default='', help='应用 ID，与 --app-name 二选一')
    p_fc.add_argument('--app-name', default='', help='应用名称（模糊匹配）')
    p_fc.add_argument('--form-code', default='', help='工作表编码，与 --form-name 二选一')
    p_fc.add_argument('--form-name', default='', help='工作表名称')
    p_fc.add_argument('--type', dest='chart_tab', default='public',
                      choices=['public', 'private'], help='公共 public / 个人 private')
    p_fc.add_argument('--title', required=True, help='图表标题')
    p_fc.add_argument('--comp', default='JBar', help='图表类型，默认 JBar')
    p_fc.add_argument('--dim', default='create_time', help='维度字段，默认 create_time')
    p_fc.add_argument('--date-group', default='3',
                      help='日期归组，默认 3=按日；仅日期维度生效，多选/单选/文本等会忽略')
    p_fc.add_argument('--val', default='record_count', help='数值字段，默认 record_count')
    p_fc.add_argument('--query-range', default='month', help='查询范围，默认 month=本月')
    p_fc.add_argument('--query-field', default='create_time')
    p_fc.add_argument('--keep-number', action='store_true',
                      help='同时挂上 createDefChart 生成的 JNumber，默认删掉')

    p_fd = sub.add_parser('delete-form-chart', help='工作表右侧统计删除公共/个人图（一条命令完成，同名全删）')
    add_auth(p_fd, need_app=False)
    p_fd.add_argument('--app-id', default='', help='应用 ID，与 --app-name 二选一')
    p_fd.add_argument('--app-name', default='', help='应用名称（模糊匹配）')
    p_fd.add_argument('--form-code', default='', help='工作表编码，与 --form-name 二选一')
    p_fd.add_argument('--form-name', default='', help='工作表名称')
    p_fd.add_argument('--type', dest='chart_tab', default='public',
                      choices=['public', 'private'], help='公共 public / 个人 private')
    p_fd.add_argument('--title', required=True, help='图表标题（option.title.text）')

    p_mv = sub.add_parser('move-form-chart', help='工作表右侧统计改归属（从公共中移出/转为公共，一条命令完成，同名全改）')
    add_auth(p_mv, need_app=False)
    p_mv.add_argument('--app-id', default='', help='应用 ID，与 --app-name 二选一')
    p_mv.add_argument('--app-name', default='', help='应用名称（模糊匹配）')
    p_mv.add_argument('--form-code', default='', help='工作表编码，与 --form-name 二选一')
    p_mv.add_argument('--form-name', default='', help='工作表名称')
    p_mv.add_argument('--type', dest='chart_tab', default='public',
                      choices=['public', 'private'], help='当前 Tab：公共 public / 个人 private')
    p_mv.add_argument('--to', dest='to_tab', required=True,
                      choices=['public', 'private'], help='目标 Tab')
    p_mv.add_argument('--title', required=True, help='图表标题（option.title.text）')

    p_cp = sub.add_parser('copy-form-chart', help='工作表右侧统计复制到当前统计（一条命令完成，同名取最新）')
    add_auth(p_cp, need_app=False)
    p_cp.add_argument('--app-id', default='', help='应用 ID，与 --app-name 二选一')
    p_cp.add_argument('--app-name', default='', help='应用名称（模糊匹配）')
    p_cp.add_argument('--form-code', default='', help='工作表编码，与 --form-name 二选一')
    p_cp.add_argument('--form-name', default='', help='工作表名称')
    p_cp.add_argument('--type', dest='chart_tab', default='public',
                      choices=['public', 'private'], help='当前 Tab（源图所在 Tab，复制后仍挂到该 Tab）')
    p_cp.add_argument('--title', required=True, help='图表标题（option.title.text）')

    p_btn = sub.add_parser('add-buttons', help='已有仪表盘加一组 JCustomButton（一条命令完成）')
    add_auth(p_btn, need_app=False)
    p_btn.add_argument('--app-id', default='', help='应用 ID，与 --app-name 二选一')
    p_btn.add_argument('--app-name', default='', help='应用名称（模糊匹配）')
    p_btn.add_argument('--page-id', default='', help='仪表盘页面 ID，与 --page-name 二选一')
    p_btn.add_argument('--page-name', default='', help='仪表盘名称（菜单 type=drag）')
    p_btn.add_argument('--specs', default='', help='禁止在 PowerShell 使用，改 --specs-file')
    p_btn.add_argument('--specs-file', default='',
                       help='UTF-8 JSON：按钮数组，或 {title,rowNum,btnType,btnStyle,btnDirection,btnWidth,place,buttons:[...]}。每项 title/op/form/view/url/pageId/flowId')
    p_btn.add_argument('--group-title', default='', help='按钮组 componentName，默认 自定义按钮')
    p_btn.add_argument('--row-num', default='', help='每行几个，默认=按钮数')
    p_btn.add_argument('--btn-type', default='', help='按钮样式：按钮/图形（button/graphical），默认 button。用户说「样式图形」必须传 graphical')
    p_btn.add_argument('--btn-style', default='', help='形状：矩形/圆角/圆形/虚线（solid/circle/dashed），默认 solid。图形样式下 solid=12px圆角卡、circle=正圆(50%%)')
    p_btn.add_argument('--btn-direction', default='', help='方向（仅图形样式）：上下/左右（column/row），默认 column')
    p_btn.add_argument('--btn-width', default='', help='divide 等分 / custom 自适应，默认 divide')
    p_btn.add_argument('--place', default='', help='top 顶部并下移已有组件 / bottom 追加到底部，默认 top')
    p_btn.add_argument('--x', default='', help='按钮组左起列（24 栅格）。两组半宽并排：0 和 12')

    p_flt = sub.add_parser('add-filter', help='已有仪表盘加 JFilterQuery 查询条件并联动统计图（一条命令完成）')
    add_auth(p_flt, need_app=False)
    p_flt.add_argument('--app-id', default='', help='应用 ID，与 --app-name 二选一')
    p_flt.add_argument('--app-name', default='', help='应用名称（模糊匹配）')
    p_flt.add_argument('--page-id', default='', help='仪表盘页面 ID，与 --page-name 二选一')
    p_flt.add_argument('--page-name', default='', help='仪表盘名称（菜单 type=drag）')
    p_flt.add_argument('--specs', default='', help='禁止在 PowerShell 使用，改 --specs-file')
    p_flt.add_argument('--specs-file', default='',
                       help='UTF-8 JSON：{title,place,w,h,showQueryBtn,charts:[图表标题],conditions:[{field,label,mode}]}。表单自动取自联动图表 config，禁止另传表单')
    p_flt.add_argument('--title', default='', help='查询条件标题，默认 查询条件')
    p_flt.add_argument('--place', default='', help='above 放联动图表上方并下移（默认）/ bottom 追加到底部')

    p_eflt = sub.add_parser(
        'edit-filter',
        help='已有 JFilterQuery 改匹配方式/默认值（≠ add-filter 新建、≠ set-chart-filter 图内筛选）')
    add_auth(p_eflt, need_app=False)
    p_eflt.add_argument('--app-id', default='', help='应用 ID，与 --app-name 二选一')
    p_eflt.add_argument('--app-name', default='', help='应用名称（模糊匹配）')
    p_eflt.add_argument('--page-id', default='', help='仪表盘页面 ID；易过期，优先 --page-name')
    p_eflt.add_argument('--page-name', default='', help='仪表盘名称（菜单 type=drag）')
    p_eflt.add_argument('--name', default='', help='查询面板 componentName（多面板时精确定位，如 产品名称查询）')
    p_eflt.add_argument('--field', required=True, help='条件显示名/字段名：产品名称 / 名称')
    p_eflt.add_argument('--mode', default='', help='等于/包含/开头是/结尾是（queryMode 1/2/5/6）')
    p_eflt.add_argument('--value', default=None, help='默认值（写入 chartData.defVal + conditionFields.val/fieldValue）')
    p_eflt.add_argument('--clear-value', action='store_true', help='清空默认值')

    p_rn = sub.add_parser('rename-page', help='已有仪表盘重命名（页面名+侧边栏菜单名同步，一条命令完成）')
    add_auth(p_rn, need_app=False)
    p_rn.add_argument('--app-id', default='', help='应用 ID，与 --app-name 二选一')
    p_rn.add_argument('--app-name', default='', help='应用名称（模糊匹配）')
    p_rn.add_argument('--page-id', default='', help='仪表盘页面 ID，与 --page-name 二选一')
    p_rn.add_argument('--page-name', default='', help='仪表盘名称（菜单 type=drag 或页面 name）')
    p_rn.add_argument('--name', required=True, help='新仪表盘名称')

    p_rnc = sub.add_parser(
        'rename-chart',
        help='已有 QQY 统计图改标题（componentName+title.text+card.title 按类型；禁 comp_ops --set）')
    add_auth(p_rnc, need_app=False)
    p_rnc.add_argument('--app-id', default='', help='应用 ID，与 --app-name 二选一')
    p_rnc.add_argument('--app-name', default='', help='应用名称（模糊匹配）')
    p_rnc.add_argument('--page-id', default='', help='仪表盘页面 ID，与 --page-name 二选一')
    p_rnc.add_argument('--page-name', default='', help='仪表盘名称（菜单 type=drag）')
    p_rnc.add_argument('--name', default='', help='当前图表 componentName / option.title')
    p_rnc.add_argument('--match-dim', default='', help='标题未知时按当前维度命中')
    p_rnc.add_argument('--comp', default='', help='可选收窄类型，如 JBar')
    p_rnc.add_argument('--title', required=True, help='新图标题')

    p_rb = sub.add_parser(
        'rebind-chart',
        help='已有 QQY 统计图改维度/数值/分组/双轴右轴/查询范围/数据源表（含跨应用；保留类型与布局）')
    add_auth(p_rb, need_app=False)
    p_rb.add_argument('--app-id', default='', help='看板所属应用 ID，与 --app-name 二选一')
    p_rb.add_argument('--app-name', default='', help='看板所属应用名称（模糊匹配）')
    p_rb.add_argument('--page-id', default='', help='仪表盘页面 ID，与 --page-name 二选一')
    p_rb.add_argument('--page-name', default='', help='仪表盘名称（菜单 type=drag）')
    p_rb.add_argument('--name', default='', help='图表 componentName（优先精确命中）')
    p_rb.add_argument('--match-dim', default='',
                      help='标题未知时按当前维度命中，如 create_time / 创建时间 / 名称')
    p_rb.add_argument('--comp', default='',
                      help='可选收窄类型，如 JBar / JLine / DoubleLineBar（无标题双轴可仅用此项）')
    p_rb.add_argument('--dim', default='', help='新维度 nameFields（中文名/fieldName/create_time）')
    p_rb.add_argument('--val', default='', help='新数值 valueFields（中文名/fieldName/记录数）')
    p_rb.add_argument('--grp', default='',
                      help='左轴分组 typeFields（双轴；中文名/fieldName）')
    p_rb.add_argument('--assist-y', default='',
                      help='右轴数值 assistYFields（双轴；中文名/fieldName/记录数）')
    p_rb.add_argument('--assist-type', default='',
                      help='右轴分组 assistTypeFields（双轴；中文名/fieldName）')
    p_rb.add_argument('--form-code', default='', help='换数据源：新表 formCode')
    p_rb.add_argument('--form-name', default='', help='换数据源：新表中文名（如 物料档案）')
    p_rb.add_argument('--form-app-id', default='', help='跨应用换表：表单所属应用 ID')
    p_rb.add_argument('--form-app-name', default='',
                      help='跨应用换表：表单所属应用名（如 仓储系统管理）')
    p_rb.add_argument('--form-type', default='design',
                      choices=['design', 'aggregation', 'online'])
    p_rb.add_argument('--query-range', default='',
                      help='查询范围：all/month/week/custom… 或 全部/本月/本周/自定义；换表未传默认 all')
    p_rb.add_argument('--custom-time', default='',
                      help='自定义起止：YYYY-MM-DD,YYYY-MM-DD（queryRange=custom 必填；只传此项也可）')
    p_rb.add_argument('--date-group', default='',
                      help='日期维归组 1..7；非日期维忽略。按日=3')
    p_scf = sub.add_parser(
        'set-chart-filter',
        help='已有 QQY 统计图写筛选条件（filter.conditionFields；≠ add-filter 查询面板）')
    add_auth(p_scf, need_app=False)
    p_scf.add_argument('--app-id', default='', help='应用 ID，与 --app-name 二选一')
    p_scf.add_argument('--app-name', default='', help='应用名称（模糊匹配）')
    p_scf.add_argument('--page-id', default='', help='仪表盘页面 ID，与 --page-name 二选一')
    p_scf.add_argument('--page-name', default='', help='仪表盘名称（菜单 type=drag）')
    p_scf.add_argument('--name', default='', help='图表 componentName')
    p_scf.add_argument('--match-dim', default='', help='标题未知时按当前维度命中')
    p_scf.add_argument('--comp', default='', help='可选收窄类型，如 JLine')
    p_scf.add_argument('--field', default='', help='筛选字段（中文名/model；「数字」可回落到图数值字段）')
    p_scf.add_argument('--op', default='', help='等于/不等于/大于/小于/大于等于/小于等于/为空/不为空/范围内')
    p_scf.add_argument('--value', default='', help='比较值（如 100）')
    p_scf.add_argument('--begin-value', default='', help='范围内起点')
    p_scf.add_argument('--end-value', default='', help='范围内终点')
    p_scf.add_argument('--clear', action='store_true', help='清空该图 conditionFields')

    p_scc = sub.add_parser(
        'set-chart-calc',
        help='已有 QQY 统计图改/升级计算值（无 calc 也把当前数值字段升级为 $model-N$；可同条 --title）')
    add_auth(p_scc, need_app=False)
    p_scc.add_argument('--app-id', default='', help='应用 ID，与 --app-name 二选一')
    p_scc.add_argument('--app-name', default='', help='应用名称（模糊匹配）')
    p_scc.add_argument('--page-id', default='', help='仪表盘页面 ID，与 --page-name 二选一')
    p_scc.add_argument('--page-name', default='', help='仪表盘名称（菜单 type=drag）')
    p_scc.add_argument('--name', default='', help='图表 componentName / option.title')
    p_scc.add_argument('--match-dim', default='', help='标题未知时按当前维度命中')
    p_scc.add_argument('--comp', default='', help='可选收窄类型，如 JBar（标题未知时常用）')
    p_scc.add_argument(
        '--formula', default='',
        help='目标公式：口语「求和」/「求和×求和」/「平均×求和」或完整 $model-N$…；无 calc 时升级当前数值字段')
    p_scc.add_argument(
        '--clear', action='store_true',
        help='取消计算值，改回普通字段（口语「改回销量字段」）')
    p_scc.add_argument(
        '--val', default='',
        help='--clear 时改回的字段中文名（如 销量）')
    p_scc.add_argument(
        '--title', default='',
        help='可选：同条改图标题（componentName+title.text+card.title 按类型；不必再 rename-chart）')

    p_scol = sub.add_parser(
        'set-chart-color',
        help='已有 QQY 统计图改柱/线色、折线类型或数值/百分比标签（口语 柱体改金色 / 显示数值标签）')
    add_auth(p_scol, need_app=False)
    p_scol.add_argument('--app-id', default='', help='应用 ID，与 --app-name 二选一')
    p_scol.add_argument('--app-name', default='', help='应用名称（模糊匹配）')
    p_scol.add_argument('--page-id', default='', help='仪表盘页面 ID，与 --page-name 二选一')
    p_scol.add_argument('--page-name', default='', help='仪表盘名称（菜单 type=drag）')
    p_scol.add_argument('--name', default='', help='图表 componentName（可省略：同类型全部改）')
    p_scol.add_argument('--match-dim', default='', help='标题未知时按当前维度命中')
    p_scol.add_argument('--comp', default='', help='收窄类型，如 JBar / JLine（口语「柱形图」传 JBar）')
    p_scol.add_argument('--color', default='', help='单色：#FFD700 / 金色 / gold / yellow')
    p_scol.add_argument('--colors', default='', help='多色逗号分隔：yellow,red 或 #FFD700,#FF4D4F')
    p_scol.add_argument(
        '--gradient', action='store_true',
        help='打开柱体渐变（JBar/JHorizontalBar：showLinearGradient + customColor color→color1）')
    p_scol.add_argument(
        '--line-type', dest='line_type', default='',
        help='折线类型：曲线/smooth、折线/line、面积/area（可与 --color 同条；禁 switch-type JSmoothLine）')
    p_scol.add_argument(
        '--label-show', action='store_true', dest='label_show',
        help='显示数值标签（饼/环 {b}\\n{c}；柱/折 label.show；可与 --colors 同条）')
    p_scol.add_argument(
        '--percent-label', action='store_true', dest='percent_label',
        help='显示百分比标签（饼 formatter={b}\\n{d}%%；可与 --colors 同条）')
    p_scol.add_argument(
        '--shape', default='',
        help='词云形状，口语原样：心的形状/爱心/心形/圆形/菱形/三角/星形')
    p_scol.add_argument(
        '--symbol-size', dest='symbol_size', default='',
        help='点大小数字；也可写进 --style')
    p_scol.add_argument(
        '--style', default='',
        help='其余样式口语整段：点大小12、圆角4、柱宽24、配色红（禁 query_page）')
    p_scol.add_argument(
        '--oral', default='',
        help='同 --style')

    p_ssort = sub.add_parser(
        'set-chart-sort',
        help='已有 QQY 统计图写前 N 项（dataFilterNum）与排序（sorts）；≠ set-chart-filter')
    add_auth(p_ssort, need_app=False)
    p_ssort.add_argument('--app-id', default='', help='应用 ID，与 --app-name 二选一')
    p_ssort.add_argument('--app-name', default='', help='应用名称（模糊匹配）')
    p_ssort.add_argument('--page-id', default='', help='仪表盘页面 ID，与 --page-name 二选一')
    p_ssort.add_argument('--page-name', default='', help='仪表盘名称（菜单 type=drag）')
    p_ssort.add_argument('--name', default='', help='图表 componentName / option.title')
    p_ssort.add_argument('--match-dim', default='', help='标题未知时按当前维度命中')
    p_ssort.add_argument('--comp', default='', help='可选收窄类型，如 JBar')
    p_ssort.add_argument('--top-n', dest='top_n', default='',
                        help='只显示前 N 项：8 / 前8项（落盘 dataFilterNum；截 X 轴不是系列数）')
    p_ssort.add_argument('--data-filter-num', dest='data_filter_num', default='',
                        help='--top-n 别名')
    p_ssort.add_argument('--field', default='', help='排序字段（中文名/model；从图已绑维值解析）')
    p_ssort.add_argument('--order', default='', help='desc/asc / 降序/升序；未传且要排序时默认 desc')
    p_ssort.add_argument('--sort', default='', help='合并写法：库存数量降序')

    p_scmp = sub.add_parser(
        'set-chart-compare',
        help='已有 JNumber 打开环比/同比（与上月相比、升红降绿）；禁手写 py')
    add_auth(p_scmp, need_app=False)
    p_scmp.add_argument('--app-id', default='', help='应用 ID，与 --app-name 二选一')
    p_scmp.add_argument('--app-name', default='', help='应用名称（模糊匹配）')
    p_scmp.add_argument('--page-id', default='', help='仪表盘页面 ID，与 --page-name 二选一')
    p_scmp.add_argument('--page-name', default='', help='仪表盘名称（菜单 type=drag）')
    p_scmp.add_argument('--name', default='', help='图表 componentName / option.title')
    p_scmp.add_argument('--match-dim', default='', help='标题未知时按当前维度命中')
    p_scmp.add_argument('--comp', default='', help='收窄类型，默认 JNumber')
    p_scmp.add_argument(
        '--compare', default='',
        help='对比项：上月/与上月相比/环比/preMonth；上年/同比/preYear；上周/preWeek')
    p_scmp.add_argument(
        '--trend', default='',
        help='箭头色，口语原样：升红降绿/红涨绿跌/升绿降红')

    p_agg = sub.add_parser(
        'save-agg',
        help='创建/编辑聚合表或聚合工厂（数据来源+行表头+公式+过滤；同名则更新）')
    add_auth(p_agg, need_app=False)
    p_agg.add_argument('--app-id', default='', help='应用 ID，与 --app-name 二选一')
    p_agg.add_argument('--app-name', default='', help='应用名称（模糊匹配）')
    p_agg.add_argument('--name', default='', help='聚合表名称（也可写在 specs.name）')
    p_agg.add_argument('--agg-id', default='', help='已有聚合表 id（编辑）')
    p_agg.add_argument('--specs', default='', help='禁止 PowerShell 内联，改 --specs-file')
    p_agg.add_argument('--specs-file', default='',
                       help='UTF-8 JSON 对象：name/kind/join/forms/links/headers/calcs/filters')

    p_dagg = sub.add_parser('delete-agg', help='删除聚合表/工厂')
    add_auth(p_dagg, need_app=False)
    p_dagg.add_argument('--app-id', default='', help='应用 ID，与 --app-name 二选一')
    p_dagg.add_argument('--app-name', default='', help='应用名称')
    p_dagg.add_argument('--name', default='', help='聚合表名称')
    p_dagg.add_argument('--agg-id', default='', help='聚合表 id')

    p_ref = sub.add_parser('set-chart-refresh', help='已有图打开每 N 分钟刷新')
    add_auth(p_ref, need_app=False)
    p_ref.add_argument('--app-id', default='')
    p_ref.add_argument('--app-name', default='')
    p_ref.add_argument('--page-id', default='')
    p_ref.add_argument('--page-name', default='')
    p_ref.add_argument('--name', default='')
    p_ref.add_argument('--match-dim', default='')
    p_ref.add_argument('--comp', default='')
    p_ref.add_argument('--minutes', required=True, help='口语：5 / 每5分钟 / 300秒 / 5min')

    p_sum = sub.add_parser('set-chart-summary', help='已有图打开总计/全部字段/汇总方式')
    add_auth(p_sum, need_app=False)
    p_sum.add_argument('--app-id', default='')
    p_sum.add_argument('--app-name', default='')
    p_sum.add_argument('--page-id', default='')
    p_sum.add_argument('--page-name', default='')
    p_sum.add_argument('--name', default='')
    p_sum.add_argument('--match-dim', default='')
    p_sum.add_argument('--comp', default='')
    p_sum.add_argument('--field', default='all', help='全部字段=all')
    p_sum.add_argument('--total-type', dest='total_type', default='sum',
                       help='average/sum/max/min 或 平均/求和')
    p_sum.add_argument('--off', action='store_true', help='关闭总计')

    p_pv = sub.add_parser('set-pivot', help='透视表前 N 行/列、开/关行合计列合计')
    add_auth(p_pv, need_app=False)
    p_pv.add_argument('--app-id', default='')
    p_pv.add_argument('--app-name', default='')
    p_pv.add_argument('--page-id', default='')
    p_pv.add_argument('--page-name', default='')
    p_pv.add_argument('--name', default='')
    p_pv.add_argument('--match-dim', default='')
    p_pv.add_argument('--comp', default='JPivotTable')
    p_pv.add_argument('--row-n', dest='row_n', default='', help='只显示前 N 行')
    p_pv.add_argument('--col-n', dest='col_n', default='', help='只显示前 N 列')
    p_pv.add_argument('--line-total', dest='line_total', default='',
                       help='行合计：1/0/开/关（关=关闭行合计）')
    p_pv.add_argument('--column-total', dest='column_total', default='',
                       help='列合计：1/0/开/关')

    p_delp = sub.add_parser('delete-page', help='删除仪表盘（逻辑删除）')
    add_auth(p_delp, need_app=False)
    p_delp.add_argument('--app-id', default='')
    p_delp.add_argument('--app-name', default='')
    p_delp.add_argument('--page-id', default='')
    p_delp.add_argument('--page-name', default='')
    p_delp.add_argument('--physical', action='store_true', help='物理删除')

    p_sfc = sub.add_parser('set-form-chart', help='工作表右侧统计改查询范围')
    add_auth(p_sfc, need_app=False)
    p_sfc.add_argument('--app-id', default='')
    p_sfc.add_argument('--app-name', default='')
    p_sfc.add_argument('--form-code', default='')
    p_sfc.add_argument('--form-name', default='')
    p_sfc.add_argument('--type', dest='chart_tab', default='private',
                       choices=['public', 'private'])
    p_sfc.add_argument('--title', required=True)
    p_sfc.add_argument('--query-range', dest='query_range', required=True)

    p_ui = sub.add_parser('add-ui', help='已有盘加文本/富文本/轮播/iframe/时钟')
    add_auth(p_ui, need_app=False)
    p_ui.add_argument('--app-id', default='')
    p_ui.add_argument('--app-name', default='')
    p_ui.add_argument('--page-id', default='')
    p_ui.add_argument('--page-name', default='')
    p_ui.add_argument('--comp', required=True, help='JText/JDragEditor/JCarousel/JIframe/JCurrentTime 或中文')
    p_ui.add_argument('--title', default='')
    p_ui.add_argument('--text', default='', help='JText 正文 / JDragEditor 可当 html')
    p_ui.add_argument('--html', default='', help='JDragEditor HTML')
    p_ui.add_argument('--url', default='', help='JIframe URL')
    p_ui.add_argument('--form-name', default='', help='JCarousel 绑定表')
    p_ui.add_argument('--form-code', default='')
    p_ui.add_argument('--max-count', dest='max_count', default='3')
    p_ui.add_argument('--no-autoplay', action='store_true')
    p_ui.add_argument('--font-size', dest='font_size', default='')
    p_ui.add_argument('--bold', action='store_true')
    p_ui.add_argument('--align', default='center')
    p_ui.add_argument('--week', default='show')
    p_ui.add_argument('--style', default='', help='口语：大标题/加粗/居中/整行')
    p_ui.add_argument('--bg', default='', help='JText 底色，如 "#4A90E2"（页头横幅）')
    p_ui.add_argument('--fg-color', dest='fg_color', default='', help='JText 字色，如 "#FFFFFF"')
    p_ui.add_argument('--w', default='')
    p_ui.add_argument('--h', default='')
    p_ui.add_argument('--x', default='')
    p_ui.add_argument('--y', default='')
    p_ui.add_argument('--place', default='', help='top 顶部插入并下移已有组件（页头横幅）/ '
                                                  'bottom 追加到底部（默认）')

    p_dr = sub.add_parser('add-drill', help='已有图加钻取；维名中文即可')
    add_auth(p_dr, need_app=False)
    p_dr.add_argument('--app-id', default='')
    p_dr.add_argument('--app-name', default='')
    p_dr.add_argument('--page-id', default='')
    p_dr.add_argument('--page-name', default='')
    p_dr.add_argument('--name', default='')
    p_dr.add_argument('--match-dim', default='')
    p_dr.add_argument('--comp', default='')
    p_dr.add_argument('--mapping', default='', help='name=维名 或直接中文维名；省略=图上第一维')
    p_dr.add_argument('--dim', default='')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    # 租户名集中解析：add_auth 全命令支持 --tenant-name（create-dashboard 内部自行解析、tenants 走 --name）
    if (args.command != 'create-dashboard'
            and hasattr(args, 'tenant_id') and hasattr(args, 'tenant_name')):
        if not str(args.tenant_id or '').strip():
            tname = (args.tenant_name or '').strip()
            if not tname:
                parser.error('the following arguments are required: --tenant-id 或 --tenant-name'
                             '（例：--tenant-name 北京国炬信息技术有限公司）')
            args.tenant_id = _resolve_tenant_id(args.api_base, args.token, '', tname)
    cmds = {
        'tenants': cmd_tenants,
        'apps': cmd_apps,
        'forms': cmd_forms,
        'fields': cmd_fields,
        'menus': cmd_menus,
        'create-page': cmd_create_page,
        'add-charts': cmd_add_charts,
        'create-dashboard': cmd_create_dashboard,
        'group-menu': cmd_group_menu,
        'add-form-chart': cmd_add_form_chart,
        'delete-form-chart': cmd_delete_form_chart,
        'move-form-chart': cmd_move_form_chart,
        'copy-form-chart': cmd_copy_form_chart,
        'add-buttons': cmd_add_buttons,
        'add-filter': cmd_add_filter,
        'edit-filter': cmd_edit_filter,
        'rename-page': cmd_rename_page,
        'rename-chart': cmd_rename_chart,
        'rebind-chart': cmd_rebind_chart,
        'set-chart-filter': cmd_set_chart_filter,
        'set-chart-calc': cmd_set_chart_calc,
        'set-chart-color': cmd_set_chart_color,
        'set-chart-sort': cmd_set_chart_sort,
        'set-chart-compare': cmd_set_chart_compare,
        'set-chart-refresh': cmd_set_chart_refresh,
        'set-chart-summary': cmd_set_chart_summary,
        'set-pivot': cmd_set_pivot,
        'delete-page': cmd_delete_page,
        'set-form-chart': cmd_set_form_chart,
        'add-ui': cmd_add_ui,
        'add-drill': cmd_add_drill,
        'save-agg': cmd_save_agg,
        'delete-agg': cmd_delete_agg,
    }
    cmds[args.command](args)


if __name__ == '__main__':
    main()
