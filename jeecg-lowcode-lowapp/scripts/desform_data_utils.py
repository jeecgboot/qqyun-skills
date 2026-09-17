"""
JeecgBoot 表单设计器数据操作工具库
====================================
提供表单数据的 CRUD、导入导出、回收站等操作。
依赖 desform_utils.py 的 API 基础设施。

使用示例:
    from desform_utils import init_api
    from desform_data_utils import *

    init_api('<api_base>', '<token>')

    # 新增数据
    result = add_data('form_code', {'input_xxx': '张三', 'phone_xxx': '13800000000'})

    # 查询列表
    records = list_data('form_code', page=1, size=10)

    # 编辑
    edit_data('form_code', 'data_id', {'input_xxx': '李四'})

    # 删除
    delete_data('form_code', 'data_id')
"""

import json
import sys
import os

# 自动定位 desform_utils.py
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
for _path in [os.getcwd(), _SCRIPT_DIR]:
    if os.path.exists(os.path.join(_path, 'desform_utils.py')):
        sys.path.insert(0, _path)
        break

from desform_utils import api_request


# ============================================================
# 数据 CRUD
# ============================================================
def add_data(code, data_dict):
    """新增表单数据

    Args:
        code: 表单编码
        data_dict: 数据字典，key 为字段 model，value 为值

    Returns:
        新增的数据记录（含 id）
    """
    body = {
        "desformCode": code,
        "desformDataJson": json.dumps(data_dict, ensure_ascii=False)
    }
    r = api_request('/desform/data/add', data=body)
    if r.get('success'):
        result = r.get('result')
        if not isinstance(result, dict):
            result = {} if result is None else {'result': result}
        else:
            result = dict(result)
        # 实测 POST /desform/data/add 返回 {dataId, customURLFail}，没有 id
        data_id = result.get('id') or result.get('dataId')
        if data_id:
            result['id'] = data_id
            result.setdefault('dataId', data_id)
        print(f"[add_data] 新增成功: {code} id={data_id or '?'}")
        return result
    else:
        raise RuntimeError(f"新增失败: {r.get('message', '未知错误')}")


def edit_data(code, data_id, data_dict):
    """编辑表单数据

    ⚠️ 全量覆盖：data_dict 会替换整条记录，未传入的字段会被清空。
    只更新部分字段时，必须先获取完整字段数据，再合并修改后传入。

    ⚠️ list_data 返回的记录结构为 {"id": "...", "desformData": {字段数据}}，
    字段数据嵌套在 desformData 里，不能直接把整条记录传给 edit_data。
    正确写法：
        result = list_data(code, size=100)
        for r in result['records']:
            data = dict(r['desformData'])   # 取 desformData，不是整个 r
            data['field_model'] = new_value
            edit_data(code, r['id'], data)

    Args:
        code: 表单编码
        data_id: 数据ID
        data_dict: 完整数据字典（全量覆盖，非增量更新）
    """
    body = {
        "id": data_id,
        "desformCode": code,
        "desformDataJson": json.dumps(data_dict, ensure_ascii=False)
    }
    r = api_request('/desform/data/edit', data=body, method='PUT')
    if r.get('success'):
        print(f"[edit_data] 编辑成功: {data_id}")
        return r.get('result')
    else:
        raise RuntimeError(f"编辑失败: {r.get('message', '未知错误')}")


def get_data(code, data_id):
    """获取单条数据

    Args:
        code: 表单编码
        data_id: 数据ID

    Returns:
        数据记录
    """
    r = api_request(f'/desform/data/queryById?id={data_id}&desformCode={code}', method='GET')
    if r.get('success'):
        return r.get('result')
    return None


def list_data(code, page=1, size=10, super_query=None, sort_column=None, sort_order=None):
    """分页查询数据列表

    Args:
        code: 表单编码
        page: 页码
        size: 每页数量
        super_query: 高级查询JSON字符串（可选）
        sort_column: 排序列（可选）
        sort_order: 排序方向 asc/desc（可选）

    Returns:
        {'records': [...], 'total': int}
    """
    url = f'/desform/data/list?desformCode={code}&pageNo={page}&pageSize={size}'
    if super_query:
        import urllib.parse
        url += f'&superQuery={urllib.parse.quote(super_query)}'
    if sort_column:
        url += f'&column={sort_column}'
    if sort_order:
        url += f'&order={sort_order}'
    r = api_request(url, method='GET')
    if r.get('success') and r.get('result'):
        return r['result']
    return {'records': [], 'total': 0}


def delete_data(code, data_id, hard=False):
    """删除数据

    Args:
        code: 表单编码
        data_id: 数据ID
        hard: True=物理删除 False=逻辑删除（进回收站）
    """
    endpoint = 'deleteFromDb' if hard else 'delete'
    r = api_request(f'/desform/data/{code}/{endpoint}?id={data_id}', method='DELETE')
    if r.get('success'):
        print(f"[delete_data] 删除成功: {data_id} (hard={hard})")
    else:
        print(f"[delete_data] 删除失败: {r.get('message', '')}")
    return r


def delete_data_batch(code, ids, hard=False):
    """批量删除数据

    Args:
        code: 表单编码
        ids: ID列表或逗号分隔的ID字符串
        hard: True=物理删除 False=逻辑删除
    """
    if isinstance(ids, list):
        ids = ','.join(ids)
    endpoint = 'deleteBatchFromDb' if hard else 'deleteBatch'
    r = api_request(f'/desform/data/{code}/{endpoint}?ids={ids}', method='DELETE')
    if r.get('success'):
        print(f"[delete_data_batch] 批量删除成功: {ids}")
    else:
        print(f"[delete_data_batch] 删除失败: {r.get('message', '')}")
    return r


# ============================================================
# 数据复制
# ============================================================
def copy_record(code, data_id):
    """复制单条数据"""
    r = api_request(f'/desform/data/{code}/copyRecord?id={data_id}', method='PUT')
    if r.get('success'):
        print(f"[copy_record] 复制成功")
        return r.get('result')
    else:
        raise RuntimeError(f"复制失败: {r.get('message', '')}")


def copy_records(code, ids):
    """批量复制数据。对齐前端：PUT /desform/data/{code}/copyRecords?ids=id1,id2,id3

    ids 为逗号分隔字符串（传 list 时自动 join）。单条复制界面也走本接口。
    标题字段会追加「-复制」，auto-number 重新生成。
    """
    if isinstance(ids, list):
        ids = ','.join(str(i) for i in ids)
    r = api_request(f'/desform/data/{code}/copyRecords', params={'ids': ids}, method='PUT')
    if r.get('success'):
        print(f"[copy_records] 批量复制成功")
        return r.get('result')
    else:
        raise RuntimeError(f"批量复制失败: {r.get('message', '')}")


# ============================================================
# 批量操作
# ============================================================
def batch_update(code, field, val, id_list):
    """批量更新字段值

    Args:
        code: 表单编码
        field: 要更新的字段 model
        val: 新值
        id_list: 要更新的数据ID列表，如 ['id1', 'id2']
    """
    if isinstance(id_list, str):
        id_list = id_list.split(',')
    body = {
        "designFormCode": code,
        "field": field,
        "val": val,
        "idList": id_list,
    }
    r = api_request('/desform/data/batchUpdate', data=body, method='PUT')
    if r.get('success'):
        print(f"[batch_update] 批量更新成功")
    else:
        print(f"[batch_update] 更新失败: {r.get('message', '')}")
    return r


# ============================================================
# 回收站
# ============================================================
def restore_data(code, ids):
    """从回收站还原数据"""
    if isinstance(ids, list):
        ids = ','.join(ids)
    r = api_request(f'/desform/data/{code}/restoreData?ids={ids}', method='GET')
    if r.get('success'):
        print(f"[restore_data] 还原成功")
    return r


def clear_recycle(code):
    """清空回收站"""
    r = api_request(f'/desform/data/{code}/clearRecycle', method='DELETE')
    if r.get('success'):
        print(f"[clear_recycle] 回收站已清空")
    return r


# ============================================================
# 唯一性检查
# ============================================================
def check_unique(code, field_model, field_value, exclude_id=None):
    """检查字段值唯一性

    Returns:
        True=唯一（无重复），False=有重复
    """
    url = f'/desform/data/checkUniqueForField/{code}?fieldModel={field_model}&fieldValue={field_value}'
    if exclude_id:
        url += f'&dataId={exclude_id}'
    r = api_request(url, method='GET')
    return r.get('success', False)


# ============================================================
# 统计查询
# ============================================================
def get_statistical(code, operation_type, field, super_query=None):
    """聚合统计

    Args:
        code: 表单编码
        operation_type: 操作类型（count/max/min/avg/sum）
        field: 统计字段 model
        super_query: 筛选条件
    """
    url = f'/desform/data/statisticalValue?code={code}&operationType={operation_type}&operationField={field}'
    if super_query:
        import urllib.parse
        url += f'&superQuery={urllib.parse.quote(super_query)}'
    r = api_request(url, method='GET')
    if r.get('success'):
        return r.get('result')
    return None
