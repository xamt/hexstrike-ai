"""线程内复用 HTTP 连接，保持现有工具所使用的客户端接口。"""

import logging
import threading
from typing import Any
from urllib.parse import urlsplit

import requests

logger = logging.getLogger(__name__)
DEFAULT_HEXSTRIKE_SERVER = "http://127.0.0.1:8888"
DEFAULT_REQUEST_TIMEOUT = 300


class HexStrikeClient:
    """连接固定后端；不自动重试执行请求，不在构造阶段访问网络。"""

    def __init__(self, server_url: str, timeout: int = DEFAULT_REQUEST_TIMEOUT):
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        self._local = threading.local()
        self._sessions = []
        self._lock = threading.Lock()
        self._closed = False

    @property
    def session(self) -> requests.Session:
        """每个工作线程拥有独立 Session，避免 Cookie 和连接状态竞争。"""
        with self._lock:
            if self._closed:
                raise RuntimeError("HTTP 客户端已关闭")
            session = getattr(self._local, "session", None)
            if session is None:
                session = requests.Session()
                if urlsplit(self.server_url).hostname in {"127.0.0.1", "localhost", "::1"}:
                    session.trust_env = False
                self._local.session = session
                self._sessions.append(session)
            return session

    def close(self) -> None:
        """所有调用结束后关闭线程持有的连接池；可重复调用。"""
        with self._lock:
            sessions, self._sessions = self._sessions, []
            self._closed = True
        for session in sessions:
            session.close()

    def _request(self, method: str, endpoint: str, *, timeout=None, **kwargs) -> dict[str, Any]:
        url = f"{self.server_url}/{endpoint.lstrip('/')}"
        try:
            response = self.session.request(
                method, url, timeout=(5, timeout or self.timeout),
                allow_redirects=False, **kwargs,
            )
            try:
                result = response.json()
            except ValueError:
                return {"success": False, "error": "后端返回的内容不是有效 JSON"}
            if not isinstance(result, dict):
                return {"success": False, "error": "后端返回的 JSON 不是对象"}
            if not 200 <= response.status_code < 300:
                result = dict(result)
                result["success"] = False
                result.setdefault("error", f"后端 HTTP 状态码 {response.status_code}")
            return result
        except requests.Timeout:
            logger.warning("后端请求超时：%s %s", method, endpoint)
            return {"success": False, "error": "后端请求超时，执行状态未确认；不会自动重试或取消"}
        except requests.RequestException as exc:
            logger.warning("后端请求失败：%s %s (%s)", method, endpoint, type(exc).__name__)
            return {"success": False, "error": "后端连接失败，执行状态未确认；不会自动重试"}

    def safe_get(self, endpoint: str, params=None) -> dict[str, Any]:
        """提交一次 GET，返回原业务字典或明确的连接错误。"""
        return self._request("GET", endpoint, params=params or {})

    def safe_post(self, endpoint: str, json_data: dict[str, Any]) -> dict[str, Any]:
        """提交一次 POST，不因超时或错误再次执行工具。"""
        return self._request("POST", endpoint, json=json_data)

    def execute_command(self, command: str, use_cache: bool = True) -> dict[str, Any]:
        """保持原命令工具调用的 API 和参数契约。"""
        return self.safe_post("api/command", {"command": command, "use_cache": use_cache})

    def check_health(self) -> dict[str, Any]:
        """保持原 server_health 工具的完整检测行为与读取超时。"""
        return self.safe_get("health")

    def probe_backend(self) -> dict[str, Any]:
        """用既有只读内存接口探测就绪，避免 /health 反复执行工具检测。"""
        return self._request("GET", "api/cache/stats", timeout=1)
