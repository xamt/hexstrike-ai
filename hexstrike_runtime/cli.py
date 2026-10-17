"""兼容 stdio 的双传输启动入口。"""

import argparse
import logging
import os
from urllib.parse import urlsplit

DEFAULT_SERVER = "http://127.0.0.1:8888"


def positive_int(value: str) -> int:
    """解析严格正整数。"""
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("必须为正整数")
    return number


def port_number(value: str) -> int:
    """校验监听端口。"""
    port = positive_int(value)
    if port > 65535:
        raise argparse.ArgumentTypeError("端口必须在 1 到 65535 之间")
    return port


def backend_url(value: str) -> str:
    """后端地址仅允许不携带凭据、查询和片段的 HTTP(S) URL。"""
    parsed = urlsplit(value)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise argparse.ArgumentTypeError("后端地址必须是无凭据和查询参数的 HTTP(S) URL")
    try:
        parsed.port
    except ValueError as exc:
        raise argparse.ArgumentTypeError("后端 URL 端口无效") from exc
    return value.rstrip("/")


def _allowed_values(values, environment, defaults):
    configured = os.environ.get(environment, "")
    return values if values is not None else (
        [item.strip() for item in configured.split(",") if item.strip()] or defaults
    )


def parse_args(argv=None):
    """读取命令行；未指定传输时保持原 stdio 行为。"""
    parser = argparse.ArgumentParser(description="HexStrike MCP 服务：stdio / Streamable HTTP")
    parser.add_argument("--server", type=backend_url, default=DEFAULT_SERVER)
    parser.add_argument("--timeout", type=positive_int,
                        default=os.environ.get("HEXSTRIKE_MCP_TIMEOUT", "300"))
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=port_number, default="8889")
    parser.add_argument("--max-concurrent", type=positive_int,
                        default=os.environ.get("HEXSTRIKE_MCP_MAX_CONCURRENT", "4"))
    parser.add_argument("--allowed-host", action="append", dest="allowed_hosts")
    parser.add_argument("--allowed-origin", action="append", dest="allowed_origins")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)
    args.allowed_hosts = _allowed_values(args.allowed_hosts, "HEXSTRIKE_MCP_ALLOWED_HOSTS",
                                        ["127.0.0.1:*", "localhost:*", "[::1]:*"])
    args.allowed_origins = _allowed_values(args.allowed_origins, "HEXSTRIKE_MCP_ALLOWED_ORIGINS", [])
    return args


def main(argv=None):
    """启动同一工具目录的指定传输，日志只写 stderr。"""
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format="[HexStrike MCP] %(asctime)s %(levelname)s %(message)s")
    from .client import HexStrikeClient
    from .server import setup_mcp_server
    client = HexStrikeClient(args.server, args.timeout)
    try:
        server = setup_mcp_server(client, max_concurrent=args.max_concurrent)
        if args.transport == "stdio":
            server.run(transport="stdio")
        else:
            from .http import serve_http
            serve_http(server, client, args)
    finally:
        client.close()
