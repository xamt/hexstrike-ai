"""共用工具注册与传输无关的并发边界。"""

import json
import logging
import time
import uuid

import anyio
from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent

from tools import register_tools

logger = logging.getLogger(__name__)


class ToolsMCPServer(MCPServer):
    """限制在途工具数量，协议发现与健康路由不占用工具配额。"""

    def __init__(self, max_concurrent: int = 4):
        if max_concurrent < 1:
            raise ValueError("并发工具数量必须为正整数")
        self._max_concurrent = max_concurrent
        self._inflight = 0
        super().__init__("pentest-tools", subscriptions=False)

    async def call_tool(self, name, arguments, context=None):
        """在事件循环内快速分配配额，SDK 在线程中运行原同步工具。"""
        if self._inflight >= self._max_concurrent:
            payload = {"success": False, "error": "工具服务繁忙，达到并发上限；本次未执行"}
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))],
                structured_content=payload, is_error=True,
            )
        self._inflight += 1
        request_id = uuid.uuid4().hex
        started = time.monotonic()
        try:
            # 断连不能释放仍在执行的同步工具配额，避免后台工作无限增长。
            with anyio.CancelScope(shield=True):
                result = await super().call_tool(name, arguments, context)
            if isinstance(result, CallToolResult):
                payload = result.structured_content
                # SDK 为 Dict[str, Any] 返回类型生成 {result: ...} 输出 Schema。
                if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
                    payload = payload["result"]
                if isinstance(payload, dict) and (
                    payload.get("success") is False or bool(payload.get("error"))
                ):
                    result.is_error = True
            logger.info("调用完成 id=%s tool=%s elapsed=%.3f error=%s", request_id, name,
                        time.monotonic() - started, getattr(result, "is_error", False))
            return result
        except BaseException:
            logger.warning("调用异常 id=%s tool=%s elapsed=%.3f", request_id, name,
                           time.monotonic() - started)
            raise
        finally:
            self._inflight -= 1


def setup_mcp_server(tool_client, *, max_concurrent: int = 4) -> ToolsMCPServer:
    """为 HTTP MCP 服务注册工具目录。"""
    server = ToolsMCPServer(max_concurrent=max_concurrent)
    register_tools(server, tool_client)
    return server
