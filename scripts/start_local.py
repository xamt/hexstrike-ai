#!/usr/bin/env python3
"""本地同时启动HTTP API与Streamable HTTP MCP，Ctrl+C统一清理（macOS/Linux）。"""
import argparse
from contextlib import ExitStack
from dataclasses import replace
import os
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "docker"))
from service_health import load_configuration
from service_manager import main as run_services


def parse_args(argv=None):
    """独立环境默认位于项目根目录，允许显式指定已有解释器和端口。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-python", default=str(ROOT / ".venv-api/bin/python"),
                        help="API解释器路径（默认项目内.venv-api/bin/python）")
    parser.add_argument("--mcp-python", default=str(ROOT / ".venv-mcp/bin/python"),
                        help="MCP解释器路径（默认项目内.venv-mcp/bin/python）")
    parser.add_argument("--api-port", type=int, help="API端口（默认8888，可由HEXSTRIKE_PORT设置）")
    parser.add_argument("--mcp-port", type=int, help="MCP端口（默认8889，可由HEXSTRIKE_MCP_PORT设置）")
    parser.add_argument("--startup-timeout", type=float, help="双服务总启动期限，默认60秒")
    parser.add_argument("--shutdown-timeout", type=float, help="进程组优雅退出期限，默认10秒")
    return parser.parse_args(argv)


def local_configuration(args):
    """复用已有配置验证；不解析虚拟环境解释器符号链接。"""
    values = dict(os.environ)
    for argument, name in (("api_port", "HEXSTRIKE_PORT"),
                           ("mcp_port", "HEXSTRIKE_MCP_PORT"),
                           ("startup_timeout", "HEXSTRIKE_STARTUP_TIMEOUT"),
                           ("shutdown_timeout", "HEXSTRIKE_SHUTDOWN_TIMEOUT")):
        value = getattr(args, argument)
        if value is not None:
            values[name] = str(value)
    return replace(load_configuration(values), root=ROOT,
                   api_python=str(Path(args.api_python).expanduser().absolute()),
                   mcp_python=str(Path(args.mcp_python).expanduser().absolute()))


def local_commands(config):
    """使用原Flask应用，只绑定回环且禁用自动重载；不改变工具执行逻辑。"""
    api = [config.api_python, "-u", "-c",
           "import os; os.environ.update(HEXSTRIKE_HOST='127.0.0.1', "
           f"HEXSTRIKE_PORT='{config.api_port}'); from hexstrike_server import app; "
           f"app.run(host='127.0.0.1', port={config.api_port}, "
           "debug=False, use_reloader=False)"]
    mcp = [config.mcp_python, "-u", str(config.root / "hexstrike_mcp.py"),
           "--transport", "streamable-http", "--host", "127.0.0.1",
           "--port", str(config.mcp_port), "--server", config.api_url]
    return api, mcp


def check_interpreter(interpreter, requirements):
    """启动前检查解释器，缺失时给出依赖位置，不隐式安装或切换环境。"""
    if not Path(interpreter).is_file() or not os.access(interpreter, os.X_OK):
        raise ValueError(f"Python解释器不存在或不可执行：{interpreter}；"
                         f"请先创建对应虚拟环境并安装 {ROOT / requirements}")


def check_ports(ports):
    """同时检查两个本地监听端口；不连接、接管或终止已有服务。"""
    with ExitStack() as stack:
        for port in ports:
            listener = stack.enter_context(socket.socket())
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                listener.bind(("127.0.0.1", port))
                listener.listen(1)
            except OSError as error:
                raise ValueError(f"本地端口 {port} 已被占用或无法监听：{error}") from error


def main(argv=None):
    """前台启动双服务；复用容器管理器的信号转发、故障联动与限时清理。"""
    args = parse_args(argv)
    try:
        if os.name != "posix":
            raise ValueError("本地进程组管理仅支持macOS/Linux")
        config = local_configuration(args)
        check_interpreter(config.api_python, "requirements.txt")
        check_interpreter(config.mcp_python, "requirements-mcp.txt")
        check_ports((config.api_port, config.mcp_port))
    except ValueError as error:
        print(f"启动失败：{error}", file=sys.stderr)
        return 2
    previous_directory = Path.cwd()
    try:
        os.chdir(ROOT)
        print(f"准备启动 HTTP API：{config.api_url}；"
              f"MCP：http://127.0.0.1:{config.mcp_port}/mcp", flush=True)
        print("按Ctrl+C同时停止两个服务；服务异常退出时自动清理另一服务。", flush=True)
        return run_services(config, commands=local_commands(config))
    finally:
        os.chdir(previous_directory)


if __name__ == "__main__":
    sys.exit(main())
