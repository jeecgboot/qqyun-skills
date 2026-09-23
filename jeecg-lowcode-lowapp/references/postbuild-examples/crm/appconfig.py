# -*- coding: utf-8 -*-
# CRM 应用配置回归：--dry-run 对现网应为 0 待办。

WZ = dv('线索状态', '未转换')
ST = {k: record_id('销售阶段', k) for k in ('进行中', '赢单', '输单', '无效')}

BUTTONS = [
    ('线索池', '领取', 'execute', None, None, '线索领取'),
    ('线索池', '分配', 'form', None, fill_fields('负责人'), '分配线索'),
    ('线索池', '转移', 'form', None, fill_fields('线索池'), None),
    ('线索', '跟进', 'form', None, new_link('跟进记录'), None),
    ('线索', '退回', 'form', [C('线索状态', 'eq', WZ)], fill_fields('线索退回原因'), '线索退回'),
    ('线索', '转换', 'form', [C('线索状态', 'eq', WZ)], new_link('客户'), '线索转换'),
    ('公海池', '领取', 'execute', None, None, '客户领取'),
    ('公海池', '退回', 'form', None, fill_fields('客户退回原因', ('所属公海', 'required')), None),
    ('客户', '跟进', 'form', None, new_link('跟进记录'), None),
    ('客户', '退回', 'form', None, fill_fields(('所属公海', 'required'), '客户退回原因'), '客户退回'),
    ('商机', '推进', 'form', None, fill_fields(('销售阶段', 'required'), '输单原因'), '推进'),
    ('商机', '创建报价单', 'execute', [C('销售阶段', 'in', '%s,%s' % (ST['赢单'], ST['进行中']))], None, '创建报价单'),
    ('产品报价', '发起审批流程', 'execute',
     [C('审批状态', 'eq', '草稿'), C('产品明细', 'not_empty'), C('整单折扣率', 'not_empty')], None, '产品报价-发起审批流程'),
    ('产品报价', '创建合同', 'execute', [C('审批状态', 'eq', '审批通过')], None, '创建合同'),
    ('合同订单', '发起审批流程', 'execute',
     [C('合同状态', 'eq', '草稿'), C('合同标题', 'not_empty'), C('合同签订日期', 'not_empty'),
      C('合同到期日期', 'not_empty')], None, '合同订单-发起审批流程'),
    ('合同订单', '开票申请', 'execute', [C('合同状态', 'eq', '审批通过')], None, '开票申请'),
    ('合同订单', '登记回款', 'form', [C('合同状态', 'eq', '审批通过')], new_link('回款单'), None),
    ('开票申请', '发起审批流程', 'execute',
     [C('开票状态', 'eq', '草稿'), C('开票金额/元', 'not_empty'), C('开票类型', 'not_empty'),
      C('财务信息（客户）', 'not_empty')], None, '开票申请-发起审批流程'),
]

QF = ['客户名称', '部门', '职务', '归属部门', '修改人']
LEAD = ['客户名称', '手机号', '联系人', '部门', '职务', '线索池', '线索来源', '负责人', '归属部门', '协作人',
        '活动类型', '线索状态', '领取时间', '最后跟进时间', '线索转换时间', '线索退回原因', '转换为客户',
        '预计回收时间', '跟进记录']
VIEWS = {t: {'summary': True} for t in PROBE}
VIEWS['线索池']['extra'] = [{'name': '退回', 'filter': [C('线索退回原因', 'not_empty')]},
                          {'name': '已领取', 'filter': [C('领取时间', 'not_empty')]}]
VIEWS['线索'].update(cols=LEAD, extra=[
    {'name': '已转换', 'filter': [C('线索状态', 'eq', '已转换')], 'cols': LEAD, 'qf': QF},
    {'name': '未转化', 'filter': [C('线索状态', 'eq', '未转换')], 'cols': LEAD, 'qf': QF},
    {'name': '跟进中', 'filter': [C('最后跟进时间', 'not_empty'), C('线索状态', 'eq', '未转换')], 'cols': LEAD, 'qf': QF}])
VIEWS['公海池'] = {'summary': False, 'qf': ['所属公海'], 'filter': [C('领取时间', 'empty')]}
VIEWS['客户']['extra'] = [{'name': '全部（负责人不为空）', 'filter': [C('负责人', 'not_empty')], 'lineHeight': 'middle'}]
VIEWS['商机']['extra'] = [{'name': n, 'filter': [C('销售阶段', 'eq', ST[k])]}
                        for n, k in [('推进中', '进行中'), ('赢单', '赢单'), ('输单', '输单'), ('无效', '无效')]]
VIEWS['销售阶段']['sort'] = [{'field': '创建时间', 'type': 'asc'}]
VIEWS['产品报价']['extra'] = [{'name': '审批状态=草稿', 'filter': [C('审批状态', 'eq', '草稿')]}]

HIDE_MENUS = ['销售阶段', '商机明细', '报价产品明细', '合同产品明细', '换货产品明细', '退货产品明细']
SWITCH_ALL_ON = True
