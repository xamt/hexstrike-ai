"""五类数据库工具 HTTP 路由；不记录凭据、SQL 或命令正文。"""
import json
from functools import partial

from flask import jsonify, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from .contracts import CONTRACTS, REQUEST_LIMIT, validate_request
from .runner import execute_database

STATUS = {"busy": 429, "tool_missing": 503, "timeout": 504,
          "output_limit": 422, "command_failed": 422, "execution_error": 500}


def register_database_routes(app):
    """将五个契约路由注册到已有 Flask 应用，不发起数据库连接。"""
    for name, schema in CONTRACTS.items():
        app.add_url_rule("/" + schema["endpoint"], endpoint="database_" + name,
                         view_func=partial(_handle, name), methods=["POST"])


def _handle(name):
    try:
        if request.content_length and request.content_length > REQUEST_LIMIT:
            return jsonify(success=False, error_code="invalid_request",
                           error="请求超过 128 KiB 上限"), 413
        raw = request.stream.read(REQUEST_LIMIT + 1)
        if len(raw) > REQUEST_LIMIT:
            return jsonify(success=False, error_code="invalid_request",
                           error="请求超过 128 KiB 上限"), 413
        payload = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError, BadRequest, RequestEntityTooLarge):
        return jsonify(success=False, error_code="invalid_request",
                       error="请求必须为有效且嵌套深度合理的 UTF-8 JSON"), 400
    try:
        args = validate_request(name, payload)
    except ValueError as error:
        return jsonify(success=False, error_code="invalid_request", error=str(error)), 400
    try:
        result = execute_database(name, args)
    except Exception:
        # 不把含连接串、查询或凭据的第三方异常写入服务日志/HTTP 响应。
        return jsonify(success=False, error_code="execution_error",
                       error="数据库执行器内部错误"), 500
    return jsonify(result), STATUS.get(result.get("error_code"), 200)
