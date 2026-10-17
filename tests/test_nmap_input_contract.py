"""离线验证 Nmap 输入契约，不启动扫描或访问目标。"""
import unittest
from unittest.mock import Mock

from test_mcp_catalog import registered
from test_server_command_contracts import load_function


class NmapInputContractTests(unittest.TestCase):
    def test_invalid_semantic_name_is_rejected_before_http(self):
        client = Mock()
        result = registered(client).tools["nmap_scan"](
            "192.0.2.1", scan_type="service_version", ports="1-65535")
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "INVALID_ARGUMENT")
        self.assertIn("-sV", result["error"])
        client.safe_post.assert_not_called()

    def test_valid_flags_keep_signature_and_disable_recovery_replay(self):
        client = Mock()
        client.safe_post.return_value = {"success": True}
        tool = registered(client).tools["nmap_scan"]
        for flags in ("", "-sV", "-sCV", "-sT -sV", "-sS -Pn", "-sn"):
            with self.subTest(flags=flags):
                self.assertTrue(tool("192.0.2.1", scan_type=flags, ports="443")["success"])
                self.assertEqual(client.safe_post.call_args.args[1]["scan_type"], flags)
                self.assertFalse(client.safe_post.call_args.args[1]["use_recovery"])

    def test_timeout_result_does_not_trigger_mcp_retry(self):
        client = Mock()
        timeout = {"success": False, "error": "执行状态未确认"}
        client.safe_post.return_value = timeout
        self.assertIs(registered(client).tools["nmap_scan"]("192.0.2.1"), timeout)
        self.assertEqual(client.safe_post.call_count, 1)

    def test_direct_http_rejects_names_and_metacharacters_before_executor(self):
        for flags in ("service_version", "-sV other.example", "-sV; true", "-sV\n--help", None, ["-sV"]):
            with self.subTest(flags=flags):
                function, ns = load_function("nmap")
                ns["request"].json = {"target": "192.0.2.1", "scan_type": flags}
                result, status = function()
                self.assertEqual(status, 400)
                self.assertFalse(result["success"])
                ns["execute_command"].assert_not_called()
                ns["execute_command_with_recovery"].assert_not_called()

    def test_direct_http_defaults_to_one_execution_without_recovery(self):
        function, ns = load_function("nmap")
        ns["request"].json = {"target": "192.0.2.1", "scan_type": "-sT -sV", "ports": "443"}
        function()
        ns["execute_command"].assert_called_once()
        self.assertIn("nmap -sT -sV -p 443", ns["execute_command"].call_args.args[0])
        ns["execute_command_with_recovery"].assert_not_called()


if __name__ == "__main__":
    unittest.main()
