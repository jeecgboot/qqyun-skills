"""
JeecgBoot 表单设计器视图通用创建脚本
====================================
通过 JSON 配置文件为已有主表单创建视图（PC 视图 / 移动端视图），
避免每次手动编写 Python 脚本。

用法:
  # 1. 复制主视图设计创建 PC 子视图
  python desform_view_creator.py --api-base <URL> --token <TOKEN> \
      --parent-code <主表单编码> --view-name "视图名称" --view-code <视图编码>

  # 2. 复制主视图并自动应用移动端优化
  python desform_view_creator.py --api-base <URL> --token <TOKEN> \
      --parent-code <主表单编码> --view-name "移动端视图" --view-code <视图编码> --mobile

  # 3. 使用自定义字段 JSON 配置创建视图（字段格式与 desform_creator.py 一致）
  python desform_view_creator.py --api-base <URL> --token <TOKEN> \
      --parent-code <主表单编码> --view-name "简洁视图" --view-code <视图编码> \
      --config <view_config.json>

  # 4. 自定义字段 + 移动端优化
  python desform_view_creator.py --api-base <URL> --token <TOKEN> \
      --parent-code <主表单编码> --view-name "移动端视图" --view-code <视图编码> \
      --config <view_config.json> --mobile

参数:
  --api-base      JeecgBoot 后端地址
  --token         X-Access-Token
  --parent-code   主表单编码（desformType=1 的表单）
  --view-name     视图名称
  --view-code     视图编码
  --mobile        设为移动端视图（izMobileView=1, designMobileView=true）
  --config        可选，自定义字段 JSON 配置文件（格式同 desform_creator.py 的 fields 部分）
  --force         强制覆盖已存在的视图

JSON 配置格式（--config 参数）:
  与 desform_creator.py 的配置格式相同，但只需 fields 相关字段:
  {
    "layout": "full",           // 可选，默认 "full"（移动端推荐 full）
    "titleIndex": 0,            // 可选，标题字段索引
    "fields": [
      {"name": "字段名", "type": "input", "required": true},
      ...
    ],
    "expand": {...}             // 可选，JS/CSS 增强
  }

  注意: formName/formCode 不在配置文件中，而是通过命令行参数 --view-name/--view-code 传入。

移动端优化（--mobile 自动应用）:
  1. config.designMobileView = true
  2. 所有控件 autoWidth → 100（单列全宽）
  3. radio/checkbox → mobileOptions: {inline: true, matrixWidth: 80}
  4. date/time → mobileOptions: {editable: false}
  5. sub-table-design → operationMode: 2（弹出编辑）
"""

import argparse
import json
import sys
import os

# 自动定位 desform_utils.py
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
for _path in [os.getcwd(), _SCRIPT_DIR]:
    if os.path.exists(os.path.join(_path, 'desform_utils.py')):
        sys.path.insert(0, _path)
        break

from desform_utils import *

# 复用 desform_creator.py 的 build_widget 和后处理逻辑
from desform_creator import build_widget, _post_process_widgets


def apply_mobile_optimizations(design):
    """对设计 JSON 应用移动端优化

    递归遍历所有控件，设置移动端友好属性：
    - autoWidth → 100（单列全宽）
    - radio/checkbox → mobileOptions: {inline: true, matrixWidth: 80}
    - date/time → mobileOptions: {editable: false}
    - sub-table-design → operationMode: 2（弹出编辑）
    """
    design['config']['designMobileView'] = True

    def _optimize_widgets(widget_list):
        for w in widget_list:
            opts = w.get('options', {})

            # 所有控件 autoWidth 设为 100（整行）
            if 'autoWidth' in opts:
                opts['autoWidth'] = 100

            # radio/checkbox 移动端横向排列
            if w.get('type') in ('radio', 'checkbox'):
                if 'mobileOptions' not in w:
                    w['mobileOptions'] = {"inline": True, "matrixWidth": 80}

            # date/time 移动端禁止手动输入
            if w.get('type') in ('date', 'time'):
                if 'mobileOptions' not in w:
                    w['mobileOptions'] = {"editable": False}

            # sub-table 移动端用弹出编辑
            if w.get('type') == 'sub-table-design':
                opts['operationMode'] = 2

            # 递归处理容器内控件
            if w.get('isContainer') or w.get('isAutoGrid'):
                if 'list' in w:
                    _optimize_widgets(w['list'])
                if 'columns' in w:
                    for col in w['columns']:
                        if 'list' in col:
                            _optimize_widgets(col['list'])
                if 'panes' in w:
                    for pane in w['panes']:
                        if 'list' in pane:
                            _optimize_widgets(pane['list'])

    _optimize_widgets(design.get('list', []))
    return design


def build_design_from_config(config):
    """从 JSON 配置构建设计 JSON（与 desform_creator.py 相同的字段解析逻辑）

    Returns:
        design_json dict（包含 list + config）
    """
    layout = config.get('layout', 'full')
    title_index = config.get('titleIndex', 0)
    expand = config.get('expand')
    fields = config.get('fields', [])

    # 构建控件列表
    widgets = []
    for fd in fields:
        widget = build_widget(fd)
        widgets.append(widget)

    # 后处理：自动解析跨控件引用
    _post_process_widgets(fields, widgets)

    # 按布局模式解包
    form_style = 'word' if layout == 'word' else 'normal'

    if layout == 'word':
        top_items, all_models = _apply_word_layout(widgets)
    elif layout == 'half' or (layout == 'auto' and len(widgets) >= 6):
        top_items, all_models = _apply_half_layout(widgets)
    else:
        top_items = []
        all_models = []
        for item in widgets:
            if isinstance(item, tuple):
                top_items.append(item[0])
                all_models.append((item[1], item[2]))
            else:
                top_items.append(item)
                all_models.append((item.get('key', ''), item.get('model', '')))

    # 确定标题字段
    title_model = all_models[title_index][1] if title_index < len(all_models) else all_models[0][1]

    # 构建设计 JSON
    design = build_design_json(top_items, title_model, form_style, expand=expand)
    return design


def main():
    parser = argparse.ArgumentParser(description='JeecgBoot 表单设计器视图创建工具')
    parser.add_argument('--api-base', required=True, help='JeecgBoot 后端地址')
    parser.add_argument('--token', required=True, help='X-Access-Token')
    parser.add_argument('--parent-code', required=True, help='主表单编码')
    parser.add_argument('--view-name', required=True, help='视图名称')
    parser.add_argument('--view-code', required=True, help='视图编码')
    parser.add_argument('--mobile', action='store_true', help='设为移动端视图')
    parser.add_argument('--config', help='可选，自定义字段 JSON 配置文件')
    parser.add_argument('--force', action='store_true', help='强制覆盖已存在的视图')
    args = parser.parse_args()

    init_api(args.api_base, args.token)

    parent_code = args.parent_code
    view_name = args.view_name
    view_code = args.view_code

    # 检查主表单是否存在
    parent_id, _ = get_form_id(parent_code)
    if not parent_id:
        print(f'[错误] 主表单不存在: {parent_code}')
        sys.exit(1)
    print(f'主表单: {parent_code} (ID={parent_id})')

    # 检查视图编码是否已被占用
    existing_id, _ = get_form_id(view_code)
    if existing_id and not args.force:
        print(f'[阻止] 视图编码 {view_code} 已存在 (ID={existing_id})')
        print(f'如需覆盖，请加 --force 参数')
        sys.exit(1)

    # 构建设计 JSON
    design_json_str = None

    if args.config:
        # 使用自定义字段配置
        print(f'从配置文件构建视图设计: {args.config}')
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
        design = build_design_from_config(config)

        if args.mobile:
            design = apply_mobile_optimizations(design)
            print('  已应用移动端优化')

        design_json_str = json.dumps(design, ensure_ascii=False)
    else:
        # 复制主视图设计
        print(f'复制主视图设计...')
        if args.mobile:
            # 复制 + 移动端优化
            parent_form = query_form(parent_code)
            if not parent_form or not parent_form.get('desformDesignJson'):
                print(f'[错误] 无法获取主视图设计 JSON')
                sys.exit(1)
            design = json.loads(parent_form['desformDesignJson'])
            design = apply_mobile_optimizations(design)
            design_json_str = json.dumps(design, ensure_ascii=False)
            print('  已应用移动端优化')
        # else: design_json_str = None → create_view 会自动复制主视图

    # 如果已存在且 --force，先删除旧视图
    if existing_id and args.force:
        print(f'删除已有视图: {view_code} (ID={existing_id})')
        try:
            delete_form(view_code, existing_id)
        except Exception as e:
            print(f'  [警告] 删除旧视图失败: {e}，尝试继续创建...')

    # 创建视图
    result = create_view(
        parent_code,
        view_name=view_name,
        view_code=view_code,
        design_json=design_json_str,
        is_mobile=args.mobile
    )

    view_id = result.get('id', 'N/A') if isinstance(result, dict) else result

    print(f'\n{"=" * 50}')
    print(f'视图创建成功')
    print(f'{"=" * 50}')
    print(f'  视图ID:     {view_id}')
    print(f'  视图名称:   {view_name}')
    print(f'  视图编码:   {view_code}')
    print(f'  主表单:     {parent_code}')
    print(f'  移动端视图: {"是" if args.mobile else "否"}')
    if args.config:
        print(f'  设计来源:   自定义配置 ({args.config})')
    else:
        print(f'  设计来源:   复制主视图')


if __name__ == '__main__':
    main()
