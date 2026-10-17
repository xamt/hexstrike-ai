"""MCP 运行配置与 HTTP 客户端单测，不执行安全工具。"""

import importlib.util
import os
import threading
import unittest
from unittest.mock import Mock, patch

HAS_REQUESTS = importlib.util.find_spec("requests") is not None


class ConfigurationTests(unittest.TestCase):
    def test_defaults_select_http_without_transport_switch(self):
        from runtime.cli import parse_args
        with patch.dict(os.environ, {}, clear=True):
            args = parse_args([])
        self.assertFalse(hasattr(args, "transport"))
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 8889)
        self.assertEqual(args.timeout, 300)
        self.assertEqual(args.max_concurrent, 4)

    def test_http_configuration_and_validation(self):
        from runtime.cli import parse_args
        args = parse_args(["--port", "9000",
                           "--allowed-host", "gateway.example:*"])
        self.assertEqual(args.port, 9000)
        self.assertIn("gateway.example:*", args.allowed_hosts)
        for values in (["--port", "0"], ["--max-concurrent", "0"],
                       ["--timeout", "-1"], ["--server", "file:///tmp/api"],
                       ["--server", "http://user:secret@example.com"]):
            with self.subTest(values=values), self.assertRaises(SystemExit):
                parse_args(values)

    def test_transport_switch_is_no_longer_supported(self):
        from runtime.cli import parse_args
        for mode in ("stdio", "streamable-http"):
            with self.subTest(mode=mode):
                with self.assertRaises(SystemExit) as error:
                    parse_args(["--transport", mode])
                self.assertEqual(error.exception.code, 2)


@unittest.skipUnless(importlib.util.find_spec("mcp"), "需要 MCP SDK")
class EntryPointTests(unittest.TestCase):
    def test_default_start_uses_http_and_closes_backend_client(self):
        from runtime.cli import main
        for failure in (None, RuntimeError("模拟监听失败")):
            with self.subTest(failure=failure), \
                 patch("runtime.client.ToolsClient") as factory, \
                 patch("runtime.server.setup_mcp_server") as setup, \
                 patch("runtime.http.serve_http", side_effect=failure) as serve:
                if failure:
                    with self.assertRaisesRegex(RuntimeError, "模拟监听失败"):
                        main([])
                else:
                    main([])
                serve.assert_called_once()
                setup.return_value.run.assert_not_called()
                factory.return_value.close.assert_called_once()


@unittest.skipUnless(HAS_REQUESTS, "需要 requirements-mcp.txt 中的 requests")
class ClientTests(unittest.TestCase):
    def make_client(self):
        from runtime.client import ToolsClient
        return ToolsClient("http://127.0.0.1:8888", timeout=7)

    def test_sessions_are_thread_local_and_closed(self):
        client = self.make_client()
        sessions = [client.session]
        self.assertFalse(client.session.trust_env, "容器内部回环请求不能被外部代理截获")
        worker = threading.Thread(target=lambda: sessions.append(client.session))
        worker.start()
        worker.join()
        self.assertIsNot(sessions[0], sessions[1])
        for session in sessions:
            session.close = Mock()
        client.close()
        for session in sessions:
            session.close.assert_called_once()

    def test_post_preserves_payload_and_business_error(self):
        client = self.make_client()
        response = Mock(status_code=500)
        response.json.return_value = {"error": "工具不可用", "marker": "kept"}
        with patch.object(client.session, "request", return_value=response) as request:
            result = client.safe_post("api/tools/nmap", {"target": "example.test"})
        self.assertEqual(result["marker"], "kept")
        self.assertFalse(result["success"])
        request.assert_called_once()
        self.assertEqual(request.call_args.kwargs["timeout"], (5, 7))
        self.assertEqual(request.call_args.kwargs["json"], {"target": "example.test"})
        client.close()

    def test_timeout_is_not_retried_or_reported_cancelled(self):
        import requests
        client = self.make_client()
        with patch.object(client.session, "request", side_effect=requests.Timeout) as request:
            result = client.safe_post("api/command", {"command": "ignored"})
        self.assertFalse(result["success"])
        self.assertIn("未确认", result["error"])
        request.assert_called_once()
        client.close()

    def test_non_json_is_explicit_failure(self):
        client = self.make_client()
        response = Mock(status_code=200)
        response.json.side_effect = ValueError("not JSON")
        with patch.object(client.session, "request", return_value=response):
            result = client.safe_get("health")
        self.assertFalse(result["success"])
        self.assertIn("JSON", result["error"])
        client.close()

    def test_readiness_does_not_invoke_expensive_tool_health(self):
        client = self.make_client()
        with patch.object(client, "_request", return_value={}) as request:
            client.probe_backend()
        request.assert_called_once_with("GET", "api/cache/stats", timeout=1)
        with patch.object(client, "safe_get", return_value={}) as get:
            client.check_health()
        get.assert_called_once_with("health")
        client.close()


if __name__ == "__main__":
    unittest.main()
