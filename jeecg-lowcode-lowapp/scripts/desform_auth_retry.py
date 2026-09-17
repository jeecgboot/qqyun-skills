"""
JeecgBoot 表单设计器字段权限重试脚本
=====================================
当创建表单时字段权限自动创建失败，可使用此脚本重新创建。

用法:
  python desform_auth_retry.py --api-base <URL> --token <TOKEN> --code <form_code>

示例:
  python desform_auth_retry.py --api-base <api_base> --token eyJ... --code oa_leave_apply
"""

import argparse
import sys
import os

# 修复 Windows 控制台中文乱码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 自动定位 desform_utils.py
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
for _path in [os.getcwd(), _SCRIPT_DIR]:
    if os.path.exists(os.path.join(_path, 'desform_utils.py')):
        sys.path.insert(0, _path)
        break

from desform_utils import init_api, save_auth_from_design


def main():
    parser = argparse.ArgumentParser(description='JeecgBoot 表单设计器字段权限重试工具')
    parser.add_argument('--api-base', required=True, help='JeecgBoot 后端地址')
    parser.add_argument('--token', required=True, help='X-Access-Token')
    parser.add_argument('--code', required=True, help='表单编码 (desformCode)')
    args = parser.parse_args()

    init_api(args.api_base, args.token)

    try:
        save_auth_from_design(args.code)
        print(f'\n字段权限创建成功: {args.code}')
    except Exception as e:
        print(f'\n字段权限创建失败: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
