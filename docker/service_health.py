"""双服务配置及仅访问容器回环地址的健康探针。"""
from dataclasses import dataclass
import math
import os
from pathlib import Path
import sys
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.environment import setting


@dataclass(frozen=True)
class ServiceConfiguration:
    """容器启动配置；程序路径可由测试显式注入，不从环境变量读取。"""

    api_port: int = 8888
    mcp_port: int = 8889
    startup_timeout: float = 60
    shutdown_timeout: float = 10
    root: Path = Path("/opt/pentest-tools")
    api_python: str = "/opt/pentest-tools-venv/bin/python"
    mcp_python: str = "/opt/pentest-tools-mcp-venv/bin/python"

    @property
    def api_url(self):
        """返回内部 API 地址。"""
        return f"http://127.0.0.1:{self.api_port}"

    @property
    def api_probe_url(self):
        """读取缓存统计验证 API，不触发工具清单探测或命令执行。"""
        return f"{self.api_url}/api/cache/stats"

    @property
    def readiness_url(self):
        """返回 MCP 就绪探针地址。"""
        return f"http://127.0.0.1:{self.mcp_port}/readyz"


def load_configuration(environ=None):
    """读取并校验端口和有限的正数超时，不接受相同监听端口。"""
    values = os.environ if environ is None else environ
    api_port = int(setting("PORT", "8888", values))
    mcp_port = int(setting("MCP_PORT", "8889", values))
    if not all(1 <= port <= 65535 for port in (api_port, mcp_port)):
        raise ValueError("服务端口必须介于 1 和 65535")
    if api_port == mcp_port:
        raise ValueError("API 与 MCP 不能使用相同端口")
    startup = float(setting("STARTUP_TIMEOUT", "60", values))
    shutdown = float(setting("SHUTDOWN_TIMEOUT", "10", values))
    if not all(math.isfinite(value) and value > 0 for value in (startup, shutdown)):
        raise ValueError("启动和停止超时必须为有限正数")
    return ServiceConfiguration(api_port, mcp_port, startup, shutdown)


def probe_http(url, timeout=2):
    """HTTP 2xx 表示探针可访问；回环探针绕过外部代理。"""
    try:
        opener = build_opener(ProxyHandler({}))
        with opener.open(url, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (OSError, URLError, ValueError):
        return False


def services_healthy(config):
    """API 和 MCP 同时就绪才判定容器健康。"""
    api_ready = probe_http(config.api_probe_url)
    mcp_ready = probe_http(config.readiness_url)
    return api_ready and mcp_ready


def main():
    """以退出状态供 Docker HEALTHCHECK 使用。"""
    try:
        return 0 if services_healthy(load_configuration()) else 1
    except ValueError as error:
        print(f"健康检查配置错误：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
