"""真实 MCP 协议端到端测试；全部工具调用只访问本地模拟后端。"""

import importlib.util
import json
import unittest
import urllib.error
import urllib.request

from mcp_test_support import (
    HEALTH, FakeBackend, MCPProcess, call_client, client_result, start_client,
)


def business_payload(result):
    """提取 MCP 结构化结果或 JSON 文本中的原业务字典。"""
    structured = result.get("structuredContent")
    if isinstance(structured, dict) and isinstance(structured.get("result"), dict):
        structured = structured["result"]
    for item in result.get("content", []):
        if item.get("type") == "text":
            try:
                payload = json.loads(item["text"])
            except (ValueError, KeyError):
                continue
            if isinstance(payload, dict):
                if isinstance(structured, dict) and structured != payload:
                    raise AssertionError(f"MCP 结构化与文本业务结果不一致：{result}")
                return payload
    if isinstance(structured, dict):
        return structured
    raise AssertionError(f"MCP 结果缺少业务字典：{result}")


@unittest.skipUnless(importlib.util.find_spec("mcp"), "需要安装 requirements-mcp.txt 中的官方 MCP SDK")
class MCPTransportTests(unittest.TestCase):
    def setUp(self):
        self.backend = FakeBackend()
        self.addCleanup(self.backend.close)
        self.service = self.start_service()

    def start_service(self, timeout=15, concurrency=4):
        service = MCPProcess(self.backend.url, timeout, concurrency)
        self.addCleanup(service.close)
        service.ready()
        return service

    def call(self, name, arguments=None, service=None):
        endpoint = (service or self.service).url + "/mcp"
        return call_client("http", endpoint, name, arguments)

    def test_http_discovers_all_tools_without_authentication(self):
        result = self.call("list")
        tools = {tool["name"]: tool for tool in result["tools"]}
        # 原文件有 151 个声明，但 httpx_probe 重名，实际只有 150 个工具名。
        self.assertEqual(len(result["tools"]), 150)
        self.assertEqual(len(tools), 150)
        self.assertIn("server_health", tools)
        schema = tools["nmap_scan"]["inputSchema"]
        self.assertEqual(schema["required"], ["target"])
        for name, default in (("scan_type", "-sV"), ("ports", ""), ("additional_args", "")):
            self.assertEqual(schema["properties"][name]["default"], default)

    def test_health_tool_preserves_backend_response(self):
        result = self.call("server_health")
        self.assertFalse(result.get("isError", False))
        self.assertEqual(business_payload(result), HEALTH)

    def test_nmap_default_request_disables_recovery_and_preserves_result(self):
        result = self.call("nmap_scan", {"target": "example.test"})
        expected = {"target": "example.test", "scan_type": "-sV", "ports": "",
                    "additional_args": "", "use_recovery": False}
        self.assertFalse(result.get("isError", False))
        self.assertEqual(self.backend.requests, [("/api/tools/nmap", expected)])
        self.assertEqual(business_payload(result), {
            "success": True, "stdout": "mock-output", "echo": expected,
        })

    def test_nmap_semantic_scan_type_is_mcp_error_without_backend_request(self):
        result = self.call("nmap_scan", {"target": "example.test", "scan_type": "service_version"})
        self.assertTrue(result.get("isError"))
        self.assertEqual(business_payload(result)["error_code"], "INVALID_ARGUMENT")
        self.assertEqual(self.backend.requests, [])

    def test_business_failure_sets_is_error_and_keeps_fields(self):
        result = self.call("nmap_scan", {"target": "business-error"})
        self.assertTrue(result.get("isError"))
        self.assertEqual(business_payload(result), {
            "success": False, "error": "tool-failed", "marker": 42,
        })
        self.assertEqual(len(self.backend.requests), 1)

    def test_backend_500_sets_is_error_without_retry(self):
        result = self.call("nmap_scan", {"target": "error500"})
        self.assertTrue(result.get("isError"))
        payload = business_payload(result)
        self.assertEqual(payload["marker"], 500)
        self.assertIn("backend-500", payload["error"])
        self.assertEqual(len(self.backend.requests), 1)

    def test_invalid_json_sets_is_error_without_retry(self):
        result = self.call("nmap_scan", {"target": "invalid-json"})
        self.assertTrue(result.get("isError"))
        self.assertTrue(result.get("content"))
        self.assertEqual(len(self.backend.requests), 1)

    def test_timeout_sets_is_error_without_retry(self):
        service = self.start_service(timeout=1)
        result = self.call("nmap_scan", {"target": "timeout"}, service=service)
        self.assertTrue(result.get("isError"))
        self.assertEqual(len(self.backend.requests), 1)
        self.assertRegex(json.dumps(result, ensure_ascii=False).lower(), r"timeout|timed out|超时")

    def test_legacy_initialize_negotiates_2025_protocol(self):
        result = call_client("http-legacy", self.service.url + "/mcp", "list")
        self.assertEqual(result["protocolVersion"], "2025-11-25")
        self.assertEqual(len(result["tools"]), 150)
        result = call_client("http-legacy", self.service.url + "/mcp", "server_health")
        self.assertFalse(result.get("isError", False))
        self.assertEqual(business_payload(result), HEALTH)

    def test_untrusted_host_and_origin_are_rejected(self):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode()
        for header, value, expected in (("Host", "untrusted.invalid", 421),
                                        ("Origin", "https://untrusted.invalid", 403)):
            with self.subTest(header=header):
                request = urllib.request.Request(
                    self.service.url + "/mcp", data=body,
                    headers={"Content-Type": "application/json", header: value,
                             "Accept": "application/json, text/event-stream"},
                )
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    urllib.request.urlopen(request, timeout=3)
                self.assertEqual(raised.exception.code, expected)

    def test_health_and_readiness_differ_when_backend_fails(self):
        self.backend.healthy = False
        with urllib.request.urlopen(self.service.url + "/healthz", timeout=3) as response:
            self.assertEqual(response.status, 200)
        with self.assertRaises(urllib.error.HTTPError) as raised:
            urllib.request.urlopen(self.service.url + "/readyz", timeout=3)
        self.assertEqual(raised.exception.code, 503)
        self.backend.healthy = True
        with urllib.request.urlopen(self.service.url + "/readyz", timeout=3) as response:
            self.assertEqual(response.status, 200)

    def test_concurrency_limit_keeps_discovery_responsive_and_recovers(self):
        clients = []
        try:
            for index in range(4):
                target = f"slow-{index}"
                process = start_client("http", self.service.url + "/mcp",
                                       "nmap_scan", {"target": target})
                clients.append(process)
                self.assertTrue(self.backend.wait_for_target(target), target)
            self.assertEqual(len(self.call("list")["tools"]), 150)
            result = self.call("nmap_scan", {"target": "overflow"})
            self.assertTrue(result.get("isError"))
            self.assertRegex(json.dumps(result, ensure_ascii=False).lower(), r"busy|繁忙|并发")
            self.assertEqual(len(self.backend.requests), 4)
        finally:
            self.backend.release.set()
            for process in clients:
                result = client_result(process)
                self.assertFalse(result.get("isError", False))
        result = self.call("nmap_scan", {"target": "after-release"})
        self.assertFalse(result.get("isError", False))
        self.assertEqual(len(self.backend.requests), 5)

if __name__ == "__main__":
    unittest.main()
