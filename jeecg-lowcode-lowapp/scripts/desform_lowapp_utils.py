"""
JeecgBoot lowApp 模式（敲敲云 / 零代码）工具库
================================================
提供组织（租户）、应用、应用分组、工作表菜单、工作表分组的管理功能。

层级关系：组织（租户）→ 应用 → 工作表（设计器表单）
           组织 → 应用分组（对应用归类）
           应用 → 工作表分组（对工作表归类）

使用示例：
    import sys
    sys.path.insert(0, r'<skill目录>/scripts')
    from desform_lowapp_utils import *

    # 1. 初始化（设置组织和应用上下文）
    init_lowapp('<api_base>', '<token>', tenant_id=<tenant_id>, app_id='<app_id>')

    # 2. 之后可直接使用 desform_utils 中的 create_form 等函数，
    #    它们会自动携带 x-tenant-id 和 x-low-app-id header

    # 3. 在应用内创建工作表（传入分组ID）
    from desform_utils import create_form, INPUT, SELECT
    create_form('客户信息', 'customer_info', [...], app_menu_group_id='<group_id>')
"""

import os
import sys
import json
import random

# 确保可以导入同目录下的 desform_utils
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import desform_utils
from desform_utils import api_request

# Windows 控制台中文乱码修复
if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 封面图可选值（coverImage001 ~ coverImage012）
_COVER_IMAGES = [f'coverImage{str(i).zfill(3)}' for i in range(1, 13)]


# ============================================================
# 初始化
# ============================================================

def init_lowapp(api_base, token, tenant_id, app_id=None):
    """初始化 lowApp 模式上下文

    调用后，desform_utils 中所有表单操作函数（create_form、add_widget、
    update_widget 等）都会自动携带 x-tenant-id 和 x-low-app-id header，
    无需额外配置。

    Args:
        api_base: JeecgBoot 后端地址（如 'http://<host>:<port>/jeecgboot'）
        token: X-Access-Token
        tenant_id: 组织（租户）ID，整数
        app_id: 应用 ID（字符串）。操作具体应用内的工作表时必填；
                仅操作应用本身（create_app 等）时可不填
    """
    desform_utils.init_api(api_base, token)
    desform_utils._TENANT_ID = str(tenant_id)
    desform_utils._LOW_APP_ID = str(app_id) if app_id else None
    print(f'initialized: tenant_id={tenant_id}, app_id={app_id or "未设置"}', file=sys.stderr)


def set_app(app_id):
    """切换当前操作的应用（不重新初始化连接）

    在同一租户下切换不同应用时使用，避免重复调用 init_lowapp。

    Args:
        app_id: 新的应用 ID，传 None 则退出 lowApp 模式
    """
    desform_utils._LOW_APP_ID = str(app_id) if app_id else None
    print(f'[lowApp] 切换应用: app_id={app_id or "已清空"}', file=sys.stderr)


# ============================================================
# 组织（租户）
# ============================================================

def get_tenants():
    """查询当前登录用户所属的所有组织（租户）

    此接口不受 x-tenant-id header 影响，返回该用户有权限的所有组织。
    当用户未指定组织时，调用此函数列出所有组织，询问用户选择。

    Returns:
        list[dict]: [{'id': 2, 'name': '北京国炬信息技术有限公司', 'status': 1}, ...]
    """
    r = api_request('/sys/tenant/getCurrentUserTenant', method='GET')
    if r.get('success') and r.get('result'):
        tenants = r['result'].get('list', [])
        return [{'id': t['id'], 'name': t['name'], 'status': t.get('status')} for t in tenants]
    return []


# ============================================================
# 应用管理
# ============================================================

def get_apps(tenant_id=None):
    """查询组织下的所有应用（含分组和关联关系）

    Args:
        tenant_id: 组织ID，不传则使用 init_lowapp 设置的当前租户

    Returns:
        dict: {
            'apps': [{id, appName, iconType, iconBackColor, appCoverImg,
                      orderNum, createTime, createBy, starStatus, ...}],
            'groups': [{id, groupName, orderNum, iconType, useScope, ...}],
            'relations': [{id, groupId, appId, orderNum}]
        }
    """
    tid = str(tenant_id) if tenant_id is not None else desform_utils._TENANT_ID
    # 临时切换 tenant_id 确保 header 与 query param 一致
    old_tid = desform_utils._TENANT_ID
    desform_utils._TENANT_ID = tid
    try:
        r = api_request(f'/online/lowApp/queryList?tenantId={tid}', method='GET')
    finally:
        desform_utils._TENANT_ID = old_tid

    if r.get('success') and r.get('result'):
        result = r['result']
        # 空组织实测 appList=null（不是 []），.get 默认值不会生效
        return {
            'apps': result.get('appList') or [],
            'groups': result.get('groupList') or [],
            'relations': result.get('relationList') or [],
        }
    return {'apps': [], 'groups': [], 'relations': []}


def create_app(tenant_id=None, app_name='未命名应用',
               icon_type='ant-design:schedule-outlined',
               icon_back_color='rgb(0, 188, 212)',
               app_cover_img=None):
    """创建应用

    Args:
        tenant_id: 组织ID，不传则使用当前租户
        app_name: 应用名称
        icon_type: Iconify 图标名（如 'ant-design:schedule-outlined'）
        icon_back_color: 图标背景色（CSS rgb 格式）
        app_cover_img: 封面图编码（coverImage001 ~ coverImage012），
                       不传则随机选择一张

    Returns:
        str: 新应用 ID
    """
    tid = int(tenant_id) if tenant_id is not None else int(desform_utils._TENANT_ID)
    if app_cover_img is None:
        app_cover_img = random.choice(_COVER_IMAGES)

    body = {
        'appName': app_name,
        'iconBackColor': icon_back_color,
        'iconType': icon_type,
        'appCoverImg': app_cover_img,
        'tenantId': tid,
    }
    r = api_request('/online/lowApp/add', data=body)
    if r.get('success'):
        app_id = r.get('result')
        print(f'[lowApp] 应用创建成功: {app_name} (ID={app_id})')
        return app_id
    raise RuntimeError(f'创建应用失败: {r.get("message", "未知错误")}')


def edit_app(app_id, app_name=None, icon_type=None, icon_back_color=None,
             app_cover_img=None):
    """修改应用信息（只传需要修改的字段）

    Args:
        app_id: 应用 ID
        app_name: 新名称
        icon_type: 新图标
        icon_back_color: 新背景色
        app_cover_img: 新封面图（coverImage001 ~ coverImage012）

    Returns:
        bool
    """
    body = {'id': app_id}
    if app_name is not None:
        body['appName'] = app_name
    if icon_type is not None:
        body['iconType'] = icon_type
    if icon_back_color is not None:
        body['iconBackColor'] = icon_back_color
    if app_cover_img is not None:
        body['appCoverImg'] = app_cover_img
    r = api_request('/online/lowApp/edit', data=body, method='PUT')
    return r.get('success', False)


def copy_app(app_id, target_tenant_id=None):
    """复制应用到目标租户

    Args:
        app_id: 被复制的应用 ID
        target_tenant_id: 目标租户 ID。不传则复制到当前租户（init_lowapp 设置的）

    Returns:
        str: 新应用 ID
    """
    tid = str(target_tenant_id) if target_tenant_id is not None else desform_utils._TENANT_ID
    r = api_request(f'/online/lowApp/copy?tenantId={tid}&id={app_id}', method='GET')
    if r.get('success'):
        new_id = r.get('result')
        print(f'[lowApp] 应用复制成功 → tenant={tid}, 新ID={new_id}')
        return new_id
    raise RuntimeError(f'复制应用失败: {r.get("message", "未知错误")}')


def star_app(app_id, star=True):
    """标星或取消标星应用

    Args:
        app_id: 应用 ID
        star: True=标星，False=取消

    Returns:
        bool
    """
    body = {'id': app_id, 'starStatus': 1 if star else 0}
    r = api_request('/online/lowApp/edit', data=body, method='PUT')
    return r.get('success', False)


def delete_app(app_id):
    """删除应用

    ⚠️ 应用下的所有工作表、配置和数据将被永久删除，不可恢复！
    执行前请务必向用户二次确认。

    Args:
        app_id: 应用 ID

    Returns:
        bool
    """
    r = api_request(f'/online/lowApp/delete?id={app_id}',
                    data={'id': app_id}, method='DELETE')
    return r.get('success', False)


# ============================================================
# 应用分组（组织级别，用于对应用本身归类）
# ============================================================

def get_app_groups(tenant_id=None):
    """查询组织下的应用分组列表

    Args:
        tenant_id: 组织ID，不传则使用当前租户

    Returns:
        list[dict]: [{id, groupName, orderNum, iconType, useScope, starStatus, ...}]
    """
    data = get_apps(tenant_id)
    return data.get('groups', [])


def create_app_group(tenant_id=None, group_name='未命名分组',
                     use_scope='self',
                     icon_type='ant-design:folder-open-outlined'):
    """在组织级别创建应用分组

    Args:
        tenant_id: 组织ID，不传则使用当前租户
        group_name: 分组名称
        use_scope: 可见范围，'self' 表示仅自己可见
        icon_type: Iconify 图标名

    Returns:
        dict 或 str: 新分组信息（含 id）
    """
    tid = int(tenant_id) if tenant_id is not None else int(desform_utils._TENANT_ID)
    body = {
        'groupName': group_name,
        'useScope': use_scope,
        'iconType': icon_type,
        'tenantId': tid,
    }
    r = api_request('/online/lowAppGroup/add', data=body)
    if r.get('success'):
        return r.get('result')
    raise RuntimeError(f'创建应用分组失败: {r.get("message", "未知错误")}')


def add_app_to_group(group_id, app_id):
    """将应用加入应用分组

    Args:
        group_id: 分组 ID
        app_id: 应用 ID

    Returns:
        bool
    """
    body = {'groupId': group_id, 'appId': app_id}
    r = api_request('/online/lowAppGroup/addAppGroupRelation', data=body)
    return r.get('success', False)


def edit_app_group(group_id, group_name=None, star_status=None,
                   icon_type=None, use_scope=None):
    """修改应用分组（只传需要修改的字段）

    Returns:
        bool
    """
    body = {'id': group_id}
    if group_name is not None:
        body['groupName'] = group_name
    if star_status is not None:
        body['starStatus'] = star_status
    if icon_type is not None:
        body['iconType'] = icon_type
    if use_scope is not None:
        body['useScope'] = use_scope
    r = api_request('/online/lowAppGroup/edit', data=body, method='PUT')
    return r.get('success', False)


def star_app_group(group_id, star=True):
    """标星或取消标星应用分组"""
    return edit_app_group(group_id, star_status=1 if star else 0)


def delete_app_group(group_id):
    """删除应用分组

    注意：仅删除分组本身，分组下的应用不会被删除。

    Returns:
        bool
    """
    r = api_request(f'/online/lowAppGroup/delete?id={group_id}',
                    data={'id': group_id}, method='DELETE')
    return r.get('success', False)


# ============================================================
# 工作表菜单管理（应用内，需要 _LOW_APP_ID 已设置）
# ============================================================

def get_menus(app_id=None):
    """查询应用中的所有菜单（工作表和工作表分组）

    返回的 menuList 包含两种 type：
    - type='form'：工作表（desformCode 和 menuUrl=formId 均有值）
    - type='group'：工作表分组（desformCode 为 null）

    Args:
        app_id: 应用 ID，不传则使用 init_lowapp 设置的当前应用

    Returns:
        dict: {
            'hasAdmin': bool,  # 当前登录人是否有该应用管理员权限
            'menuList': [
                {
                    id,           # 菜单ID（⚠️ 非 desform_id，操作工作表时用此ID）
                    menuName,     # 工作表/分组名称
                    type,         # 'form' | 'group'
                    parentId,     # 所属分组ID（type=form 时有值）
                    desformCode,  # 表单编码（type=form 时有值）
                    menuUrl,      # 表单ID（type=form 时有值，= desform 的 id）
                    orderNum,
                    ...
                }
            ]
        }
    """
    aid = str(app_id) if app_id is not None else desform_utils._LOW_APP_ID
    if not aid:
        raise ValueError('app_id 未指定，请通过 init_lowapp 或参数传入')

    old_app = desform_utils._LOW_APP_ID
    desform_utils._LOW_APP_ID = aid
    try:
        r = api_request(f'/online/lowAppMenu/queryMenus?appId={aid}', method='GET')
    finally:
        desform_utils._LOW_APP_ID = old_app

    if r.get('success') and r.get('result'):
        return r['result']
    return {'hasAdmin': False, 'menuList': []}


def get_worksheet_groups(app_id=None):
    """查询应用内的工作表分组（语法糖，只返回 type='group' 的菜单项）

    创建工作表时，用此函数判断：
    1. 应用内是否已有分组（count > 0 则有）
    2. 有哪些分组可供选择（供用户确认或默认选第一个）

    Args:
        app_id: 应用 ID，不传则使用当前应用

    Returns:
        dict: {
            'count': int,   # 分组数量（0 表示无分组）
            'groups': [     # 分组列表（按 orderNum 排序）
                {'id': '...', 'menuName': '...', 'orderNum': N}
            ]
        }
    """
    menus_data = get_menus(app_id)
    menu_list = menus_data.get('menuList', [])
    groups = sorted(
        [
            {'id': m['id'], 'menuName': m['menuName'], 'orderNum': m.get('orderNum', 0)}
            for m in menu_list if m.get('type') == 'group'
        ],
        key=lambda g: g['orderNum']
    )
    return {'count': len(groups), 'groups': groups}


def edit_worksheet(menu_id, menu_name=None, icon_type=None):
    """修改工作表名称或图标

    ⚠️ 参数是 menu_id（来自 get_menus().menuList[].id），不是 desform_id

    Args:
        menu_id: 工作表菜单 ID（queryMenus 返回的 menuList[].id）
        menu_name: 新名称
        icon_type: 新图标（Iconify 格式，如 'ant-design:aim-outlined'）

    Returns:
        bool
    """
    body = {'id': menu_id}
    if menu_name is not None:
        body['menuName'] = menu_name
    if icon_type is not None:
        body['iconType'] = icon_type
    r = api_request('/online/lowAppMenu/edit', data=body, method='PUT')
    return r.get('success', False)


def sort_worksheets(order_info):
    """重新排序应用内的工作表

    Args:
        order_info: list[dict]，必须包含所有工作表（不含分组）
                    格式：[{'id': menu_id, 'orderNum': 1}, {'id': ..., 'orderNum': 2}, ...]

    Returns:
        bool
    """
    body = {'info': order_info}
    r = api_request('/online/lowAppMenu/changeOrder', data=body, method='PUT')
    return r.get('success', False)


def delete_worksheet(menu_id):
    """删除工作表

    ⚠️ 工作表下所有配置和数据将被永久删除，不可恢复！
    ⚠️ 参数是 menu_id（来自 get_menus().menuList[].id），不是 desform_id

    执行前请向用户二次确认。

    Args:
        menu_id: 工作表菜单 ID（queryMenus 返回的 menuList[].id）

    Returns:
        bool
    """
    r = api_request(f'/online/lowAppMenu/delete?id={menu_id}',
                    data={'id': menu_id}, method='DELETE')
    return r.get('success', False)


# ============================================================
# 应用内工作表分组管理
# ============================================================

def create_worksheet_group(app_id=None, group_name='未命名分组'):
    """创建工作表分组（语法糖，自动判断首次/追加场景）

    内部逻辑：
    - 先调用 get_worksheet_groups 检查分组数量
    - count == 0（首次创建）→ 调用 createFirstGroup：
      此时系统会将已有的所有工作表迁移进新分组
    - count > 0（已有分组）→ 调用 createGroup：
      只新增分组，已有工作表不受影响

    Args:
        app_id: 应用 ID，不传则使用当前应用
        group_name: 分组名称（默认'未命名分组'）

    Returns:
        str: 新分组的 ID（可用于 create_form 的 appMenuGroupId 参数）
    """
    aid = str(app_id) if app_id is not None else desform_utils._LOW_APP_ID
    if not aid:
        raise ValueError('app_id 未指定，请通过 init_lowapp 或参数传入')

    groups_info = get_worksheet_groups(aid)

    if groups_info['count'] == 0:
        # 首次创建分组
        body = {'menuName': group_name, 'appId': aid}
        r = api_request('/online/lowAppMenu/createFirstGroup', data=body)
        if r.get('success'):
            print(f'[lowApp] 首个工作表分组创建成功: {group_name}')
            # createFirstGroup 不返回分组ID，通过查询获取
            new_groups = get_worksheet_groups(aid)
            for g in new_groups['groups']:
                if g['menuName'] == group_name:
                    return g['id']
            # 查不到时返回第一个分组的ID
            if new_groups['groups']:
                return new_groups['groups'][0]['id']
            return None
        raise RuntimeError(f'创建首个工作表分组失败: {r.get("message", "未知错误")}')
    else:
        # 追加新分组
        body = {'menuName': group_name, 'appId': aid}
        r = api_request('/online/lowAppMenu/createGroup', data=body)
        if r.get('success'):
            group_id = r.get('result')
            print(f'[lowApp] 工作表分组创建成功: {group_name} (ID={group_id})')
            return group_id
        raise RuntimeError(f'创建工作表分组失败: {r.get("message", "未知错误")}')


def edit_worksheet_group(group_id, group_name):
    """修改工作表分组名称

    Args:
        group_id: 分组 ID（来自 get_worksheet_groups().groups[].id）
        group_name: 新名称

    Returns:
        bool
    """
    body = {'id': group_id, 'menuName': group_name}
    r = api_request('/online/lowAppMenu/updateName', data=body, method='PUT')
    return r.get('success', False)


def move_worksheet_to_group(menu_id, parent_group_id, app_id=None):
    """将工作表移动到指定分组

    Args:
        menu_id: 工作表菜单 ID（来自 get_menus().menuList[].id）
        parent_group_id: 目标分组 ID
        app_id: 应用 ID，不传则使用当前应用

    Returns:
        bool
    """
    aid = str(app_id) if app_id is not None else desform_utils._LOW_APP_ID
    body = {'id': menu_id, 'appId': aid, 'parentId': parent_group_id}
    r = api_request('/online/lowAppMenu/moveToGroup', data=body)
    return r.get('success', False)


def delete_worksheet_group(group_id, move_to_group_id=None, app_id=None):
    """删除工作表分组

    DELETE /online/lowAppMenu/deleteGroup?deleteId={group_id}&groupId={move_to_group_id}

    对齐前端 AppGroupMenu.vue：
    - 该分组下有工作表，且应用内还有其他分组：必须先让用户选择迁入目标，再传 move_to_group_id
    - 没有其他分组，或该分组下没有工作表：只传 group_id，可直接删除
    工作表不会被删，只是迁到目标分组（或随最后一个分组一起解开）。

    Args:
        group_id: 要删除的分组 ID（URL 参数 deleteId）
        move_to_group_id: 工作表迁入的目标分组 ID（URL 参数 groupId）。有工作表且还有其他分组时必填
        app_id: 应用 ID，不传则使用当前应用

    Returns:
        bool
    """
    gid = str(group_id)
    menus = get_menus(app_id)
    menu_list = menus.get('menuList') or []
    children = [
        m for m in menu_list
        if m.get('type') == 'form' and str(m.get('parentId') or '') == gid
    ]
    other_groups = [
        m for m in menu_list
        if m.get('type') == 'group' and str(m.get('id')) != gid
    ]

    if children and other_groups and not move_to_group_id:
        child_names = [c.get('menuName') or c.get('desformCode') for c in children]
        options = [f"{g.get('menuName')} (id={g.get('id')})" for g in other_groups]
        raise ValueError(
            f'分组 {gid} 下还有工作表 {child_names}，且应用内还有其他分组。'
            f'不能直接删除，必须先让用户选择迁入目标后再调用 '
            f'delete_worksheet_group(group_id, move_to_group_id=目标id)。'
            f'可选分组: {options}'
        )

    params = {'deleteId': gid}
    if move_to_group_id:
        target = str(move_to_group_id)
        if target == gid:
            raise ValueError('move_to_group_id 不能与要删除的分组相同')
        if other_groups and target not in {str(g.get('id')) for g in other_groups}:
            raise ValueError(f'move_to_group_id={target} 不是当前应用内的其他分组')
        params['groupId'] = target

    r = api_request('/online/lowAppMenu/deleteGroup', params=params, method='DELETE')
    return r.get('success', False)


# ============================================================
# 功能开关（零代码应用专属）
# ============================================================

def get_switch_settings(desform_code):
    """查询工作表的所有功能开关配置

    仅适用于零代码应用（isLowApp=true）的工作表，需提前调用 init_lowapp。

    Args:
        desform_code: 工作表的表单编码（desformCode）

    Returns:
        list[dict]: 所有功能开关配置项，每项结构如下：
            {
                '_id': str | None,   # 数据库主键（通常为 null）
                'code': str,         # 功能标识（全大写，如 'SHOW_CREATE_BTN'）
                'desformCode': str,  # 工作表编码
                'enabled': bool,
                'userAuth': int,     # 1=所有用户, 2=仅管理员
                'viewAuth': int,     # 1=所有视图, 2=指定视图
                'viewIds': list,     # viewAuth=2 时生效，视图 ID 列表
                'createBy': ..., 'createTime': ..., 'updateBy': ..., 'updateTime': ...
            }

    Example:
        settings = get_switch_settings('my_form')
        target = next(s for s in settings if s['code'] == 'SHOW_CREATE_BTN')
        target['enabled'] = False
        save_switch_settings('my_form', [target])
    """
    r = api_request('/desform/setting/getAllSetting', params={'desformCode': desform_code}, method='GET')
    if not r.get('success'):
        raise RuntimeError(f'查询功能开关失败：{r.get("message", "未知错误")}')
    return r.get('result', [])


def save_switch_settings(desform_code, settings_list):
    """批量保存功能开关配置

    仅适用于零代码应用（isLowApp=true）的工作表，需提前调用 init_lowapp。

    父子联动规则（AI 需手动处理，不在本函数内自动处理）：
    - BATCH_ACTION 是父级，子级为 BATCH_EDIT/BATCH_EXPORT/BATCH_REMOVE/BATCH_CUSTOM_BUTTON/BATCH_SYS_PRINT
    - 父级 enabled 变更时，需同时传入所有子级（继承相同 enabled）
    - 最后一个子级禁用时，需同时传入父级（enabled=False）

    viewAuth 约束：
    - viewAuth=2 时，viewIds 不得为空（至少传一个视图 ID）
    - 切换回 viewAuth=1 时，viewIds 传空列表即可

    Args:
        desform_code: 工作表的表单编码（仅用于日志提示，实际保存依赖 settings_list 中的 desformCode）
        settings_list: list[dict]，每项需包含：
                       _id（可为 None）、code、desformCode、enabled、userAuth、viewAuth、viewIds、
                       createBy/createTime/updateBy/updateTime（可均为 None）
                       后端按 desformCode+code upsert，可直接构造无需先查询

    Returns:
        bool: 是否保存成功

    Example:
        settings = get_switch_settings('my_form')
        # 启用批量操作（父级+所有子级）
        batch_codes = ['BATCH_ACTION', 'BATCH_EDIT', 'BATCH_EXPORT', 'BATCH_REMOVE', 'BATCH_CUSTOM_BUTTON']
        batch_items = [s for s in settings if s['code'] in batch_codes]
        for item in batch_items:
            item['enabled'] = True
        save_switch_settings('my_form', batch_items)
    """
    r = api_request('/desform/setting/saveBatch', data=settings_list)
    if not r.get('success'):
        raise RuntimeError(f'保存功能开关失败（{desform_code}）：{r.get("message", "未知错误")}')
    print(f'[switch] 功能开关已保存，更新了 {len(settings_list)} 项')
    return True
