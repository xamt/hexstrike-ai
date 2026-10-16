"""从单一 JSON 契约装载默认值并校验 HTTP 请求。"""
import ipaddress
import json
import re
from pathlib import Path

from .policy import enforce_policy

CONTRACTS = json.loads(Path(__file__).with_name("contracts.json").read_text("utf-8"))
REQUEST_LIMIT = 131072
TYPES = {"str": str, "int": int, "bool": bool, "list": list, "dict": dict}


def validate_request(name, payload):
    """返回带默认值的合法参数；错误信息不包含用户提供的值。"""
    if not isinstance(payload, dict):
        raise ValueError("请求必须为 JSON 对象")
    parameters = CONTRACTS[name]["parameters"]
    if set(payload) - set(parameters):
        raise ValueError("请求包含未支持的参数")
    result = {}
    for key, spec in parameters.items():
        if key not in payload and spec["required"]:
            raise ValueError(f"缺少必填参数：{key}")
        value = payload.get(key, spec.get("default"))
        if type(value) is not TYPES[spec["type"]]:
            raise ValueError(f"参数类型错误：{key}")
        result[key] = value
    _validate_values(result)
    _validate_operation(name, result)
    enforce_policy(name, result)
    return result


def _validate_values(args):
    try:
        encoded = json.dumps(args, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise ValueError("请求存在非有限数值、无效字符或过深嵌套") from None
    if len(encoded) > REQUEST_LIMIT:
        raise ValueError("请求超过 128 KiB 上限")
    host = args["host"]
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?", host):
            raise ValueError("host 必须为单个域名或 IP，不接受 URI、套接字或选项") from None
    for key, low, high in (("port", 1, 65535), ("timeout", 1, 600),
                           ("max_output_bytes", 1024, 1048576)):
        if not low <= args[key] <= high:
            raise ValueError(f"{key} 必须在 {low} 到 {high} 之间")
    for key in ("username", "password", "database", "auth_database"):
        value = args.get(key)
        if isinstance(value, str) and (len(value) > 4096 or "\0" in value):
            raise ValueError(f"参数长度或字符无效：{key}")
    for key in ("username", "database", "auth_database"):
        value = args.get(key)
        if isinstance(value, str) and not re.fullmatch(r"[\w.@-]*", value):
            raise ValueError(f"{key} 仅接受普通名称，不接受连接串或控制字符")
    if isinstance(args["database"], int) and not 0 <= args["database"] <= 2147483647:
        raise ValueError("Redis database 必须为非负整数")


def _validate_operation(name, args):
    if name == "mongodb_command" and args["password"] and not args["username"]:
        raise ValueError("MongoDB 使用密码时必须同时提供 username")
    if "query" in args:
        query = args["query"]
        if not query.strip() or len(query.encode("utf-8")) > 65536 or "\0" in query:
            raise ValueError("query 必须非空、无 NUL 且不超过 64 KiB")
    elif name == "redis_command":
        command = args["command"]
        if not command or len(command) > 256 or any(type(v) is not str or "\0" in v for v in command):
            raise ValueError("command 必须为 1 到 256 个无 NUL 的字符串")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", command[0]):
            raise ValueError("Redis 命令名称无效")
    elif not args["command"]:
        raise ValueError("MongoDB command 必须为非空 JSON 对象")
