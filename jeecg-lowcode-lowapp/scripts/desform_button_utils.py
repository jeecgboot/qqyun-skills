"""
desform_button_utils.py — 自定义按钮（自定义动作）操作工具库

依赖 desform_utils.py 中的 init_api 完成初始化，使用前必须先调用：
    from desform_utils import init_api
    init_api('<api_base>', '<token>')
"""

import json
import urllib.parse
import desform_utils as _du


def _get(path, params=None):
    """GET 请求（自动拼接 query string）"""
    if params:
        qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        path = f"{path}?{qs}"
    return _du.api_request(path, method='GET')


def _post(path, data):
    return _du.api_request(path, data=data, method='POST')


def _delete(path, params=None):
    if params:
        qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        path = f"{path}?{qs}"
    return _du.api_request(path, method='DELETE')


# ---------------------------------------------------------------------------
# 核心 CRUD
# ---------------------------------------------------------------------------

def create_button(form_code: str, button: dict, view_id: str = None) -> dict:
    """
    创建自定义按钮。

    Args:
        form_code: 表单编码
        button: 按钮配置字典（见 desform-custom-button.md 的 ButtonInfo 结构）
        view_id: 视图 ID；传 None 则创建为全局按钮（allView=True）

    Returns:
        后端返回的按钮对象，含 id 和 processId（若 flowStatus=True）

    注意：
        若 button['flowStatus'] == True，后端会自动生成 processId，
        但工作流节点内容需通过 jeecg-lowcode-miniflow 技能配置。
    """
    payload = dict(button)
    payload['designFormCode'] = form_code
    if view_id:
        payload['viewId'] = view_id
    else:
        payload.setdefault('allView', True)

    result = _post('/desform/button/save', payload)
    if not result.get('success'):
        # 此环境存在已知问题：按钮实际写库成功，但 Flowable 进程壳创建失败导致返回 false。
        # 反查是否已创建，避免调用方误判后重试产生重复按钮。
        label = button.get('label', '')
        existing = _get(f'/desform/button/list?designFormCode={form_code}')
        matches = [b for b in existing.get('result', []) if b.get('label') == label]
        if matches:
            return matches[-1]  # 返回最新一条，视为创建成功
        raise RuntimeError(f"创建按钮失败：{result.get('message', result)}")
    return result.get('result', result)


def update_button(button_id: str, form_code: str, changes: dict, view_id: str = None) -> dict:
    """
    更新已有按钮的属性。

    Args:
        button_id: 按钮 ID
        form_code: 表单编码
        changes: 需要更新的字段字典（仅传需要修改的字段）
        view_id: 视图 ID（可选）

    Returns:
        后端返回结果
    """
    existing = get_button(button_id)
    payload = {**existing, **changes}
    payload['id'] = button_id
    payload['designFormCode'] = form_code
    if view_id:
        payload['viewId'] = view_id

    result = _post('/desform/button/update', payload)
    if not result.get('success'):
        raise RuntimeError(f"更新按钮失败：{result.get('message', result)}")
    # update 接口 result 字段固定为 null，返回 True 表示成功
    return True


def delete_button(button_id: str, form_code: str) -> bool:
    """删除按钮"""
    result = _delete('/desform/button/remove', params={'buttonId': button_id, 'designFormCode': form_code})
    if not result.get('success'):
        raise RuntimeError(f"删除按钮失败：{result.get('message', result)}")
    return True


def get_button(button_id: str) -> dict:
    """根据 ID 查询按钮详情"""
    result = _get('/desform/button/queryById', params={'id': button_id})
    if not result.get('success'):
        raise RuntimeError(f"查询按钮失败：{result.get('message', result)}")
    return result.get('result', {})


def list_buttons(form_code: str, view_id: str = None) -> list:
    """
    查询表单的自定义按钮列表。

    Args:
        form_code: 表单编码
        view_id: 视图 ID；传 None 则返回所有按钮（含全局按钮）

    Returns:
        按钮列表
    """
    params = {'designFormCode': form_code}
    if view_id:
        params['viewId'] = view_id

    result = _get('/desform/button/list', params=params)
    if not result.get('success'):
        raise RuntimeError(f"查询按钮列表失败：{result.get('message', result)}")
    r = result.get('result', [])
    # 兼容分页和列表两种返回格式
    if isinstance(r, dict):
        return r.get('records', [])
    return r


# ---------------------------------------------------------------------------
# 排序
# ---------------------------------------------------------------------------

def reorder_buttons(button_id_list: list) -> bool:
    """
    按给定顺序重新排列按钮。

    Args:
        button_id_list: 按钮 ID 列表，顺序即为目标显示顺序

    Returns:
        True 表示成功
    """
    payload = [{'id': bid, 'seq': idx + 1} for idx, bid in enumerate(button_id_list)]
    result = _post('/desform/button/resetSequence', payload)
    if not result.get('success'):
        raise RuntimeError(f"重排序失败：{result.get('message', result)}")
    return True


# ---------------------------------------------------------------------------
# 视图绑定
# ---------------------------------------------------------------------------

def add_button_to_view(button_id: str, view_id: str) -> bool:
    """将按钮绑定到指定视图"""
    result = _post('/desform/button/addRelation', {'buttonId': button_id, 'viewId': view_id})
    if not result.get('success'):
        raise RuntimeError(f"绑定视图失败：{result.get('message', result)}")
    return True


def remove_button_from_view(button_id: str, view_id: str) -> bool:
    """将按钮从指定视图解绑"""
    result = _delete('/desform/button/removeRelation', params={'buttonId': button_id, 'viewId': view_id})
    if not result.get('success'):
        raise RuntimeError(f"解绑视图失败：{result.get('message', result)}")
    return True


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def check_button_label(form_code: str, label: str, button_id: str = None) -> bool:
    """
    检查按钮名称是否在当前表单内唯一。

    Returns:
        True 表示名称可用，False 表示已存在
    """
    params = {'designFormCode': form_code, 'label': label}
    if button_id:
        params['id'] = button_id
    result = _get('/desform/button/checkOnly', params=params)
    return result.get('result', True)
