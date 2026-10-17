"""MCP 集成测试夹具：仅模拟 HTTP 后端，绝不执行安全工具。"""

import asyncio
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
HEALTH = {"status": "healthy", "version": "test", "total_tools_available": 151}


class FakeBackend:
    """提供可控错误、阻塞和请求记录的本地模拟 API。"""

    def __init__(self):
        self.requests = []
        self.condition = threading.Condition()
        self.release = threading.Event()
        self.healthy = True
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def respond(self, status, payload, content_type="application/json"):
                body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    # 客户端超时断开是测试场景，后端仍然完成该请求。
                    return

            def do_GET(self):
                status = 200 if owner.healthy else 503
                self.respond(status, HEALTH if owner.healthy else {"error": "offline"})

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                with owner.condition:
                    owner.requests.append((self.path, payload))
                    owner.condition.notify_all()
                target = payload.get("target", "")
                if target.startswith("slow-"):
                    owner.release.wait(20)
                if target == "timeout":
                    time.sleep(2)
                if target == "error500":
                    self.respond(500, {"success": False, "error": "backend-500", "marker": 500})
                elif target == "invalid-json":
                    self.respond(200, b"not-json", "text/plain")
                elif target == "business-error":
                    self.respond(200, {"success": False, "error": "tool-failed", "marker": 42})
                else:
                    self.respond(200, {"success": True, "stdout": "mock-output", "echo": payload})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def wait_for_target(self, target, timeout=10):
        """等待请求抵达后端，避免用固定休眠推断并发状态。"""
        with self.condition:
            return self.condition.wait_for(
                lambda: any(body.get("target") == target for _, body in self.requests),
                timeout=timeout,
            )

    def close(self):
        """释放阻塞请求并关闭监听端口。"""
        self.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def unused_port():
    """选择一个临时本地端口。"""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


class MCPProcess:
    """以当前解释器启动真实 MCP 服务并保留失败日志。"""

    def __init__(self, backend_url, timeout=15, concurrency=4):
        self.port = unused_port()
        self.url = f"http://127.0.0.1:{self.port}"
        self.log = tempfile.TemporaryFile(mode="w+")
        command = [sys.executable, str(ROOT / "hexstrike_mcp.py"),
                   "--transport", "streamable-http", "--host", "127.0.0.1",
                   "--port", str(self.port), "--server", backend_url,
                   "--timeout", str(timeout), "--max-concurrent", str(concurrency)]
        self.process = subprocess.Popen(command, cwd=ROOT, stdout=self.log, stderr=self.log)

    def ready(self):
        """等待真实服务监听；失败时附带服务日志。"""
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and self.process.poll() is None:
            try:
                with urllib.request.urlopen(self.url + "/healthz", timeout=0.5) as response:
                    if response.status == 200:
                        return
            except (OSError, urllib.error.URLError):
                time.sleep(0.05)
        self.log.seek(0)
        raise AssertionError("MCP 服务未就绪：\n" + self.log.read())

    def close(self):
        """保证失败测试也不遗留 MCP 服务进程。"""
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.log.close()


def start_client(transport, address, action, arguments=None):
    """独立进程运行官方 SDK 客户端，防止测试间连接状态污染。"""
    return subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), transport, address, action,
         json.dumps(arguments or {})], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )


def client_result(process, timeout=25):
    """读取客户端结果并在异常时保留诊断。"""
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        raise AssertionError(f"MCP 客户端超时：{stderr}")
    if process.returncode:
        raise AssertionError(f"MCP 客户端失败：{stderr}\n{stdout}")
    return json.loads(stdout)


def call_client(transport, address, action, arguments=None):
    """完成一次独立的真实协议客户端调用。"""
    return client_result(start_client(transport, address, action, arguments))


async def run_client(transport, address, action, arguments):
    """使用官方 SDK 协商协议并调用工具，不用手写 JSON-RPC 替代验收。"""
    from mcp import Client, StdioServerParameters

    destination = address
    if transport == "stdio":
        # 故意省略 --transport，验证原有默认启动方式。
        destination = StdioServerParameters(
            command=sys.executable,
            args=[str(ROOT / "hexstrike_mcp.py"), "--server", address],
            cwd=str(ROOT),
        )
    mode = "legacy" if transport == "http-legacy" else "auto"
    async with Client(destination, read_timeout_seconds=20, mode=mode) as client:
        if action == "list":
            result = await client.list_tools()
        else:
            result = await client.call_tool(action, arguments)
        payload = result.model_dump(by_alias=True, mode="json")
        payload["protocolVersion"] = client.protocol_version
        print(json.dumps(payload))


if __name__ == "__main__":
    asyncio.run(run_client(*sys.argv[1:4], json.loads(sys.argv[4])))
