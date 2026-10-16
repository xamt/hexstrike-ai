"""离线验证原接口与必要修复；只执行提取函数，绝不启动服务或安全工具。"""
import ast
import logging
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
SERVER = ast.parse((ROOT / "hexstrike_server.py").read_text())


def endpoint(name, payload, result=None):
    """隔离加载单个处理函数并替换命令执行器。"""
    node = next(node for node in SERVER.body if isinstance(node, ast.FunctionDef) and node.name == name)
    node.decorator_list = []
    execute = Mock(return_value=result or {"success": True, "stdout": "report\n"})
    namespace = {
        "request": SimpleNamespace(json=payload), "jsonify": lambda value: value,
        "execute_command": execute, "logger": logging.getLogger(__name__),
        "Path": Path, "os": os,
    }
    exec(compile(ast.Module(body=[node], type_ignores=[]), "endpoint", "exec"), namespace)
    return namespace[name](), execute


class LegacyApiTests(unittest.TestCase):
    def test_ctf_templates_substitute_target_once(self):
        source = next(node for node in SERVER.body if isinstance(node, ast.ClassDef) and node.name == "CTFToolManager")
        methods = [node for node in source.body if isinstance(node, ast.FunctionDef)
                   and node.name in ("__init__", "get_tool_command")]
        wrapper = ast.ClassDef(name="Manager", bases=[], keywords=[], body=methods, decorator_list=[])
        namespace = {}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[wrapper], type_ignores=[])), "ctf", "exec"), namespace)
        manager = namespace["Manager"]()
        for name in ("httpx", "katana", "gobuster", "dirsearch", "arjun", "volatility"):
            with self.subTest(tool=name):
                command = manager.get_tool_command(name, "TARGET", "--extra")
                self.assertNotIn("{}", command)
                self.assertEqual(command.count("TARGET"), 1)
                self.assertTrue(command.endswith(" --extra"))
        self.assertEqual(manager.get_tool_command("volatility", "sample.raw"),
                         "volatility -f sample.raw imageinfo")

    def test_volatility2_preserves_profile_and_plugin(self):
        result, execute = endpoint("volatility", {
            "memory_file": "memory.raw", "plugin": "pslist", "profile": "Win7SP1x64",
        })
        self.assertTrue(result["success"])
        execute.assert_called_once_with("volatility -f memory.raw --profile=Win7SP1x64 pslist")

    def test_paramspider_original_parameters_and_high_mode(self):
        _, execute = endpoint("paramspider", {
            "domain": "example.com", "level": 2, "exclude": "png,jpg", "output": "urls.txt",
        })
        execute.assert_called_once_with("paramspider -d example.com -l high --exclude png,jpg -o urls.txt")

    def test_paramspider_second_mcp_output_alias(self):
        _, execute = endpoint("paramspider", {
            "domain": "example.com", "level": 1, "exclude": "", "output_file": "urls.txt",
        })
        execute.assert_called_once_with("paramspider -d example.com -o urls.txt")

    def test_paramspider_rejects_undefined_levels(self):
        for value in (0, 3, "high", True):
            with self.subTest(level=value):
                response, execute = endpoint("paramspider", {"domain": "example.com", "level": value})
                self.assertEqual(response[1], 400)
                execute.assert_not_called()

    def test_volatility3_output_file_is_report_not_dump_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.txt"
            result, execute = endpoint("volatility3", {
                "memory_file": "memory.raw", "plugin": "windows.pslist", "output_file": str(report),
            })
            execute.assert_called_once_with("vol.py -f memory.raw windows.pslist", use_cache=False)
            self.assertEqual(report.read_text(), "report\n")
            self.assertEqual(result["stdout"], "report\n")

    def test_volatility3_no_file_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.txt"
            endpoint("volatility3", {"memory_file": "m", "plugin": "p", "output_file": str(report)},
                     {"success": False, "stdout": "partial"})
            self.assertFalse(report.exists())

    def test_httpx_second_mcp_payload_remains_supported(self):
        _, execute = endpoint("httpx", {
            "targets": "https://example.com", "status_code": "200,302",
            "ports": "443", "methods": "GET", "output_file": "http.txt",
        })
        execute.assert_called_once_with(
            "httpx -u https://example.com -t 50 -probe -sc -mc 200,302 -p 443 -x GET -o http.txt")

    def test_httpx_file_input_uses_list_flag(self):
        _, execute = endpoint("httpx", {"target_file": "targets.txt", "probe": False})
        execute.assert_called_once_with("httpx -l targets.txt -t 50")

    def test_no_database_registration(self):
        self.assertFalse("database_tools" in (ROOT / "hexstrike_server.py").read_text())


if __name__ == "__main__":
    unittest.main()
