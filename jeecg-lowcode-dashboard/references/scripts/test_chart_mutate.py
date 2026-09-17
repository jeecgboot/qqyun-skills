# -*- coding: utf-8 -*-
"""set-chart-calc 升级普通数值 / rename-chart 三字段。无 API。"""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REFS = os.path.dirname(_HERE)
for d in (_HERE, _REFS):
    if d not in sys.path:
        sys.path.insert(0, d)

import qqy_ops as qo


def _plain_bar(name='各仓库库存柱'):
    return {
        'component': 'JBar',
        'componentName': name,
        'config': {
            'dataType': 4,
            'valueFields': [{
                'fieldName': 'number_1788522241158_621918',
                'fieldTxt': '库存数量',
                'fieldType': 'number',
                'widgetType': 'number',
            }],
            'calcFields': [],
            'option': {
                'title': {'show': True, 'text': name},
                'card': {'title': 'tab残留'},
                'series': [{'type': 'bar', 'name': '库存数量'}],
            },
        },
    }


def _calc_bar(name='计算值测试', formula='$money_1-4$*$number_2-1$'):
    calc = {
        'fieldName': formula,
        'fieldTxt': '销售额',
        'widgetType': 'calcVal',
        'fieldType': 'number',
        'calcId': 'id-1',
    }
    return {
        'component': 'JBar',
        'componentName': name,
        'config': {
            'dataType': 4,
            'valueFields': [dict(calc)],
            'calcFields': [dict(calc)],
            'option': {'title': {'show': True, 'text': name}, 'card': {'title': ''}},
        },
    }


class ApplyCalcTests(unittest.TestCase):
    def test_upgrade_plain_number_sum(self):
        cfg = _plain_bar()['config']
        changes = qo._apply_calc_on_cfg(cfg, '求和')
        self.assertTrue(changes)
        vf = cfg['valueFields'][0]
        self.assertEqual(vf['widgetType'], 'calcVal')
        self.assertEqual(vf['fieldName'], '$number_1788522241158_621918-1$')
        self.assertEqual(vf['fieldTxt'], '库存数量')
        self.assertEqual(cfg['calcFields'][0]['fieldName'], vf['fieldName'])
        self.assertEqual(cfg['calcFields'][0]['calcId'], vf['calcId'])

    def test_rewrite_existing_avg_times_sum(self):
        cfg = _calc_bar()['config']
        changes = qo._apply_calc_on_cfg(cfg, '求和×求和')
        self.assertTrue(changes)
        self.assertEqual(cfg['valueFields'][0]['fieldName'], '$money_1-1$*$number_2-1$')
        self.assertEqual(cfg['calcFields'][0]['fieldName'], '$money_1-1$*$number_2-1$')

    def test_sum_times_sum_on_single_plain_exits(self):
        cfg = _plain_bar()['config']
        with self.assertRaises(SystemExit):
            qo._apply_calc_on_cfg(cfg, '求和×求和')

    def test_record_count_only_exits(self):
        cfg = {
            'valueFields': [{'fieldName': 'record_count', 'fieldTxt': '记录数',
                             'widgetType': 'number'}],
            'calcFields': [],
        }
        with self.assertRaises(SystemExit):
            qo._apply_calc_on_cfg(cfg, '求和')


class ApplyTitleTests(unittest.TestCase):
    def test_rename_writes_three_fields(self):
        comp = _plain_bar()
        cfg = comp['config']
        qo._apply_chart_title(comp, cfg, '各仓库库存合计')
        self.assertEqual(comp['componentName'], '各仓库库存合计')
        self.assertEqual(cfg['option']['title']['text'], '各仓库库存合计')
        self.assertTrue(cfg['option']['title']['show'])
        self.assertEqual(cfg['option']['card']['title'], '')


class SelectChartForCalcTests(unittest.TestCase):
    def test_named_plain_chart_not_redirected_to_other_calc(self):
        tmpl = [_plain_bar(), _calc_bar()]
        hits = qo._select_chart_for_calc(tmpl, name='各仓库库存柱')
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['componentName'], '各仓库库存柱')


class SoleDragPageTests(unittest.TestCase):
    def test_pick_sole_drag(self):
        menus = [
            {'type': 'group', 'menuName': '基础数据'},
            {'type': 'form', 'menuName': '实时库存'},
            {'type': 'drag', 'menuName': '仓储运营分析看板', 'menuUrl': '1255'},
        ]
        pid, pname = qo._pick_sole_drag_page(menus)
        self.assertEqual(pid, '1255')
        self.assertEqual(pname, '仓储运营分析看板')

    def test_two_drags_no_auto(self):
        menus = [
            {'type': 'drag', 'menuName': 'A', 'menuUrl': '1'},
            {'type': 'drag', 'menuName': 'B', 'menuUrl': '2'},
        ]
        pid, pname = qo._pick_sole_drag_page(menus)
        self.assertIsNone(pid)
        self.assertIsNone(pname)


class SpecFromFlagsTests(unittest.TestCase):
    def _args(self, **kw):
        a = type('A', (), {})()
        defaults = dict(
            comp='', title='', dim='', val='', grp='', assist_y='', assist_type='',
            date_group='', query_range='', query_field='', custom_time='', calc='',
            colors='', color='', top_n='', line_type='', label_show=False, percent_label=False,
            scatter_label=False, legend_show=False, w='', h='', x='', y='',
            show_line_total='', show_column_total='', row_n='', col_n='',
            chart_title='', shape='', border_radius='', bar_width='', symbol_size='',
            style='', oral='',
        )
        defaults.update(kw)
        for k, v in defaults.items():
            setattr(a, k, v)
        return a

    def test_bar_alias_and_fields(self):
        spec = qo._spec_from_flags(self._args(
            comp='基础柱形图', title='各产品销售额', dim='产品名称', val='销售额',
            query_range='全部'))
        self.assertEqual(spec['comp'], 'JBar')
        self.assertEqual(spec['dim'], '产品名称')
        self.assertEqual(spec['val'], '销售额')
        self.assertEqual(spec['queryRange'], 'all')

    def test_pivot_multi_dim_and_totals(self):
        spec = qo._spec_from_flags(self._args(
            comp='透视表', dim='产品名称,支付方式', val='销售额',
            show_line_total='true', show_column_total='true', row_n='10', col_n='5'))
        self.assertEqual(spec['comp'], 'JPivotTable')
        self.assertEqual(spec['dim'], ['产品名称', '支付方式'])
        self.assertEqual(spec['showLineCount'], '10')
        self.assertEqual(spec['showColumnCount'], '5')

    def test_dual_axis_flags(self):
        spec = qo._spec_from_flags(self._args(
            comp='双轴图', dim='名称', val='record_count', grp='流程状态',
            assist_y='record_count', assist_type='创建人'))
        self.assertEqual(spec['comp'], 'DoubleLineBar')
        self.assertEqual(spec['assistY'], 'record_count')
        self.assertEqual(spec['assistType'], '创建人')

    def test_map_default_size(self):
        spec = qo._spec_from_flags(self._args(comp='柱状地图', dim='省份', val='销售额'))
        self.assertEqual(spec['comp'], 'JBarMap')
        self.assertEqual(spec['w'], 12)
        self.assertEqual(spec['h'], 30)

    def test_wordcloud_heart_shape(self):
        spec = qo._spec_from_flags(self._args(
            comp='词云', title='物料名称词云', dim='物料名称', val='记录数', shape='心形'))
        self.assertEqual(spec['comp'], 'JWordCloud')
        self.assertEqual(spec['shape'], 'cardioid')
        cfg = {'option': {'title': {'text': 't'}, 'card': {}}}
        qo._apply_spec_shape(cfg, spec)
        self.assertEqual(cfg['option']['series'][0]['shape'], 'cardioid')
        self.assertEqual(cfg['option']['shape'], 'cardioid')

    def test_unknown_comp_exits(self):
        with self.assertRaises(SystemExit):
            qo._spec_from_flags(self._args(comp='不是图'))

    def test_stack_bar_oral_spec(self):
        spec = qo._spec_from_flags(self._args(
            comp='堆叠柱', title='各仓库按审批堆叠', dim='关联仓库', val='记录数',
            grp='审批状态', colors='黄绿蓝', border_radius='4'))
        self.assertEqual(spec['comp'], 'JStackBar')
        self.assertEqual(spec['grp'], '审批状态')
        self.assertEqual(spec['colors'], ['黄', '绿', '蓝'])
        self.assertEqual(spec['borderRadius'], 4)

    def test_scatter_oral_and_symbol_size(self):
        spec = qo._spec_from_flags(self._args(
            comp='散点图', title='物料安全库存散点', dim='物料名称', val='安全库存',
            color='#eb2f96', symbol_size='点大小12'))
        self.assertEqual(spec['comp'], 'JScatter')
        self.assertEqual(spec['colors'], ['#eb2f96'])
        self.assertEqual(spec['symbolSize'], 12)

    def test_scatter_style_blob_size(self):
        spec = qo._spec_from_flags(self._args(
            comp='散点图', dim='物料名称', val='安全库存', style='点大小12'))
        self.assertEqual(spec['comp'], 'JScatter')
        self.assertEqual(spec['symbolSize'], 12)


class CompTypeAliasTests(unittest.TestCase):
    def test_oral_to_comp(self):
        import qqy_chart as qc
        cases = {
            '横向条': 'JHorizontalBar',
            '立体柱地图': 'JBarMap',
            '字符云': 'JWordCloud',
            '基础柱形图': 'JBar',
            '折线图': 'JLine',
            'JPie': 'JPie',
            '散点图': 'JScatter',
            '散点': 'JScatter',
            '气泡图': 'JBubble',
            '散点地图': 'JBubbleMap',
            '气泡地图': 'JBubbleMap',
            '漏斗图': 'JFunnel',
            '金字塔漏斗图': 'JPyramidFunnel',
            '圆形雷达图': 'JCircleRadar',
            '仪表盘': 'JGauge',
            '多色仪表盘': 'JColorGauge',
            '渐变仪表盘': 'JAntvGauge',
            '对比柱形图': 'JMultipleBar',
            '正负条形图': 'JNegativeBar',
            '南丁格尔玫瑰图': 'JRose',
            '数字卡片': 'JNumber',
        }
        for raw, want in cases.items():
            self.assertEqual(qc.norm_comp_type(raw), want, raw)


class OralFlagTests(unittest.TestCase):
    def test_date_group(self):
        self.assertEqual(qo._norm_date_group('按日'), '3')
        self.assertEqual(qo._norm_date_group('每天统计'), '3')
        self.assertEqual(qo._norm_date_group('按月'), '2')

    def test_query_range(self):
        self.assertEqual(qo._norm_query_range('全部数据'), 'all')
        self.assertEqual(qo._norm_query_range('本月'), 'month')
        self.assertEqual(qo._norm_query_range('上月'), 'preMonth')
        self.assertEqual(qo._norm_query_range('上周'), 'preWeek')
        self.assertEqual(qo._norm_query_range('去年'), 'preYear')

    def test_specs_json_oral_enums(self):
        spec = {'comp': '柱状图', 'queryRange': '本月', 'dateGroup': '按日'}
        qo._apply_spec_oral_enums(spec)
        self.assertEqual(spec['comp'], 'JBar')
        self.assertEqual(spec['queryRange'], 'month')
        self.assertEqual(spec['dateGroup'], '3')

    def test_tenant_name_candidates(self):
        cands = qo._tenant_name_candidates('测试租户')
        self.assertEqual(cands[0], '测试租户')
        self.assertIn('测试', cands)
        company = qo._tenant_name_candidates('北京国炬信息技术有限公司')
        self.assertIn('北京国炬信息技术', company)

    def test_minutes(self):
        self.assertEqual(qo._norm_minutes('每5分钟'), 5)
        self.assertEqual(qo._norm_minutes('300秒'), 5)
        self.assertEqual(qo._norm_minutes('五分钟'), 5)
        self.assertEqual(qo._norm_minutes('5min'), 5)

    def test_trend(self):
        self.assertEqual(qo._norm_trend('升红降绿'), '2')
        self.assertEqual(qo._norm_trend('红涨绿跌'), '2')
        self.assertEqual(qo._norm_trend('升绿降红'), '1')

    def test_line_type_phrase(self):
        self.assertEqual(qo._normalize_line_type('改成面积'), 'area')
        self.assertEqual(qo._normalize_line_type('曲线'), 'smooth')

    def test_split_colors_runon(self):
        self.assertEqual(qo._split_colors('黄绿蓝'), ['黄', '绿', '蓝'])
        self.assertEqual(qo._split_colors('黄,绿,蓝'), ['黄', '绿', '蓝'])
        hexes = qo._parse_spec_hexes('黄绿蓝')
        self.assertEqual(len(hexes), 3)

    def test_parse_full_user_prompt(self):
        text = ('租户 ID=2，在应用「仓储系统管理」下用「入库单」加堆叠柱「各仓库按审批堆叠」。'
                '维度关联仓库，数值记录数，分组审批状态。配色黄绿蓝。柱圆角 4。')
        spec, applied = qo._parse_chart_oral(text)
        self.assertEqual(spec.get('comp'), 'JStackBar')
        self.assertEqual(spec.get('title'), '各仓库按审批堆叠')
        self.assertEqual(spec.get('dim'), '关联仓库')
        self.assertEqual(spec.get('val'), '记录数')
        self.assertEqual(spec.get('grp'), '审批状态')
        self.assertEqual(spec.get('colors'), ['黄', '绿', '蓝'])
        self.assertEqual(spec.get('borderRadius'), 4)
        self.assertIn('comp', applied)

    def test_oral_flag_builds_spec(self):
        helper = SpecFromFlagsTests()
        spec = qo._spec_from_flags(helper._args(
            oral='加堆叠柱「T」。维度仓库，数值记录数，分组状态。配色黄绿蓝。圆角4'))
        self.assertEqual(spec['comp'], 'JStackBar')
        self.assertEqual(spec['title'], 'T')
        self.assertEqual(spec['borderRadius'], 4)
        self.assertEqual(spec['colors'], ['黄', '绿', '蓝'])

    def test_style_radius_oral(self):
        spec = {}
        qo._apply_oral_chart_style(spec, '柱圆角 4 配色黄绿蓝')
        self.assertEqual(spec['borderRadius'], 4)
        self.assertEqual(spec['colors'], ['黄', '绿', '蓝'])

    def test_style_symbol_size_oral(self):
        spec = {}
        qo._apply_oral_chart_style(spec, '点大小12')
        self.assertEqual(spec['symbolSize'], 12)

    def test_oral_sentence_style_not_eaten_by_val(self):
        spec, applied = qo._parse_chart_oral(
            '加散点图，维度物料名称，数值安全库存，颜色 #eb2f96,点大小12')
        self.assertEqual(spec.get('comp'), 'JScatter')
        self.assertEqual(spec.get('dim'), '物料名称')
        self.assertEqual(spec.get('val'), '安全库存')
        self.assertEqual(spec.get('symbolSize'), 12)
        self.assertIn('symbolSize', applied)

    def test_drill_resolve_cn(self):
        cfg = {'nameFields': [
            {'fieldName': 'input_1', 'fieldTxt': '物料名称'},
        ]}
        self.assertEqual(qo._drill_resolve_model(cfg, '物料名称'), 'input_1')
        self.assertEqual(qo._drill_resolve_model(cfg, ''), 'input_1')


class WordcloudShapeAliasTests(unittest.TestCase):
    def test_oral_phrases_all_cardioid(self):
        for raw in ('心形', '心的形状', '爱心', '桃心', '改成心形', 'heart', 'Heart'):
            self.assertEqual(qo._norm_wordcloud_shape(raw), 'cardioid', raw)

    def test_circle_and_star(self):
        self.assertEqual(qo._norm_wordcloud_shape('圆形'), 'circle')
        self.assertEqual(qo._norm_wordcloud_shape('星的形状'), 'star')

    def test_unknown_empty(self):
        self.assertEqual(qo._norm_wordcloud_shape('六边形气泡'), '')


class ApplyPivotTests(unittest.TestCase):
    def test_row_col_and_totals(self):
        cfg = {'pivotTable': {
            'showLineCount': 0, 'showColumnCount': 0,
            'showLineTotal': True, 'showColumnTotal': True,
        }}
        qo._apply_spec_pivot(cfg, {
            'showLineCount': 10, 'showColumnCount': 5,
            'showLineTotal': False, 'showColumnTotal': '关',
        })
        pt = cfg['pivotTable']
        self.assertEqual(pt['showLineCount'], 10)
        self.assertEqual(pt['showColumnCount'], 5)
        self.assertFalse(pt['showLineTotal'])
        self.assertFalse(pt['showColumnTotal'])


class ClearCalcTests(unittest.TestCase):
    def test_clear_back_to_model(self):
        cfg = _calc_bar()['config']
        cfg['filterField'] = [{
            'fieldName': 'money_1', 'fieldTxt': '销量',
            'fieldType': 'number', 'widgetType': 'number',
        }]
        changes = qo._clear_calc_on_cfg(cfg, '销量')
        self.assertTrue(changes)
        self.assertEqual(cfg['calcFields'], [])
        self.assertEqual(cfg['valueFields'][0]['fieldName'], 'money_1')
        self.assertNotEqual(cfg['valueFields'][0].get('widgetType'), 'calcVal')

    def test_formula_gaihui_routes_to_clear(self):
        self.assertTrue(qo._is_clear_calc('改回销量字段'))
        self.assertTrue(qo._is_clear_calc('字段'))
        self.assertFalse(qo._is_clear_calc('求和'))


class AutoSpecsTests(unittest.TestCase):
    def test_kpi_bar_line_pie_pivot(self):
        fields = [
            {'fieldName': 'input_1', 'fieldTxt': '产品名称', 'widgetType': 'input',
             'fieldType': 'string'},
            {'fieldName': 'money_1', 'fieldTxt': '销售额', 'widgetType': 'money',
             'fieldType': 'number'},
            {'fieldName': 'select_1', 'fieldTxt': '支付方式', 'widgetType': 'select',
             'fieldType': 'string'},
        ]
        specs = qo._auto_specs_from_fields(fields)
        comps = [s['comp'] for s in specs]
        self.assertEqual(comps.count('JNumber'), 3)
        self.assertIn('JBar', comps)
        self.assertIn('JLine', comps)
        self.assertIn('JPie', comps)
        self.assertIn('JPivotTable', comps)


if __name__ == '__main__':
    unittest.main()
