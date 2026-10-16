"""注册五个专项工具端点；不将请求、结果或异常正文写入服务日志。"""
import json
from functools import partial

from flask import jsonify, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from .contracts import CONTRACTS, REQUEST_LIMIT, validate_request
from .runner import execute_security

STATUS = {'busy': 429, 'tool_missing': 503, 'timeout': 504, 'output_limit': 422,
          'command_failed': 422, 'execution_error': 500, 'invalid_request': 400}


def register_security_routes(app):
    """绑定独立契约，不启动客户端，也不替换已有分析器。"""
    for name, contract in CONTRACTS.items():
        app.add_url_rule('/' + contract['endpoint'], endpoint='security_' + name,
                         view_func=partial(_handle, name), methods=['POST'])


def _handle(name):
    try:
        if request.content_length and request.content_length > REQUEST_LIMIT:
            return _error('请求超过 128 KiB 上限', 413)
        raw = request.stream.read(REQUEST_LIMIT + 1)
        if len(raw) > REQUEST_LIMIT:
            return _error('请求超过 128 KiB 上限', 413)
        payload = json.loads(raw, object_pairs_hook=_unique_object)
        args = validate_request(name, payload)
    except (ValueError, UnicodeError, RecursionError, BadRequest, RequestEntityTooLarge):
        return _error('请求必须为有效 JSON 且符合工具参数契约', 400)
    try:
        result = execute_security(name, args)
    except Exception:
        return jsonify(success=False, error_code='execution_error',
                       error='专项工具执行器内部错误'), 500
    return jsonify(result), STATUS.get(result.get('error_code'), 200)


def _error(message, status):
    return jsonify(success=False, error_code='invalid_request', error=message), status


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('JSON 不允许重复键')
        result[key] = value
    return result
