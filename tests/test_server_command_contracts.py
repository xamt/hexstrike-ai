"""离线验证命令参数契约；只提取函数并模拟执行器，不启动安全工具。"""
import ast
import copy
import logging
import shlex
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import Mock
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
TREE = ast.parse((ROOT / "server.py").read_text())


def load_function(name, **overrides):
    """隔离载入单个函数，替换所有外部执行与文件副作用。"""
    node = copy.deepcopy(next(item for item in TREE.body
                              if isinstance(item, ast.FunctionDef) and item.name == name))
    node.decorator_list = []
    namespace = {
        "request": SimpleNamespace(json={}), "jsonify": lambda value: value,
        "logger": logging.getLogger(__name__), "shlex": shlex,
        "urlparse": urlparse,
        "execute_command": Mock(return_value={"success": True}),
        "execute_command_with_recovery": Mock(return_value={"success": True}),
        "os": SimpleNamespace(makedirs=Mock(), path=SimpleNamespace(isfile=lambda _: False)),
        "Dict": Dict, "Any": Any, "COMMAND_TIMEOUT": 300,
    }
    namespace.update(overrides)
    exec(compile(ast.Module(body=[node], type_ignores=[]), "isolated", "exec"), namespace)
    return namespace[name], namespace


def endpoint(name, payload):
    """执行隔离接口并返回响应和模拟执行器。"""
    function, namespace = load_function(name, request=SimpleNamespace(json=payload))
    return function(), namespace["execute_command"]


def shell_tokens(command):
    """分辨未引用的 shell 运算符，不运行生成的命令。"""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()<>")
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)


class ExecutorContractTests(unittest.TestCase):
    def test_timeout_reaches_executor_and_cache_key(self):
        cache = Mock()
        cache.get.return_value = None
        factory = Mock()
        factory.return_value.execute.return_value = {"success": True}
        function, _ = load_function("execute_command", cache=cache, EnhancedCommandExecutor=factory)
        for timeout in (30, 900):
            function("example", timeout=timeout)
            factory.assert_called_with("example", timeout=timeout)
            cache.get.assert_called_with("example", {"timeout": timeout})
            cache.set.assert_called_with("example", {"timeout": timeout}, {"success": True})

    def test_timeout_validation_precedes_execution(self):
        factory = Mock()
        function, _ = load_function("execute_command", cache=Mock(), EnhancedCommandExecutor=factory)
        for timeout in (0, -1, True, "300"):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                function("example", timeout=timeout)
        factory.assert_not_called()

    def test_cached_result_and_cache_bypass_keep_timeout_contract(self):
        cache = Mock()
        cache.get.return_value = {"success": True, "stdout": "cached"}
        factory = Mock()
        factory.return_value.execute.return_value = {"success": True}
        function, _ = load_function("execute_command", cache=cache, EnhancedCommandExecutor=factory)
        self.assertEqual(function("example", timeout=900)["stdout"], "cached")
        factory.assert_not_called()
        cache.reset_mock()
        function("example", use_cache=False, timeout=900)
        factory.assert_called_once_with("example", timeout=900)
        cache.get.assert_not_called()
        cache.set.assert_not_called()

    def test_ghidra_quotes_paths_and_passes_timeout(self):
        response, execute = endpoint("ghidra", {
            "binary": "/tmp/a b.bin", "project_name": "project a", "analysis_timeout": 900,
        })
        self.assertTrue(response["success"])
        self.assertEqual(execute.call_args.kwargs, {"timeout": 900})
        argv = shlex.split(execute.call_args.args[0])
        self.assertIn("/tmp/a b.bin", argv)
        self.assertIn("/tmp/ghidra_projects/project a/analysis.xml", argv)


class EndpointContractTests(unittest.TestCase):
    def test_autorecon_default_and_legacy_profiles_reach_environment(self):
        response, execute = endpoint("autorecon", {"target": "example.com"})
        self.assertTrue(response["success"])
        self.assertIn("--port-scans top-100-ports", execute.call_args.args[0])
        for plugin in ("top-100-ports", "top-1000-ports"):
            response, execute = endpoint("autorecon", {"target": "example.com", "port_scans": plugin})
            self.assertTrue(response["success"])
            self.assertIn(f"--port-scans {plugin}", execute.call_args.args[0])

    def test_autorecon_explicit_native_default_remains_available(self):
        _, execute = endpoint("autorecon", {"target": "example.com", "port_scans": "default"})
        self.assertNotIn("--port-scans", execute.call_args.args[0])

    def test_dalfox_explicit_false_disables_default_mining(self):
        _, execute = endpoint("dalfox", {
            "url": "https://example.com", "mining_dom": False, "mining_dict": False,
        })
        argv = shlex.split(execute.call_args.args[0])
        self.assertIn("--mining-dom=false", argv)
        self.assertIn("--mining-dict=false", argv)

    def test_hakrawler_default_does_not_expand_scope(self):
        response, execute = endpoint("hakrawler", {"url": "https://example.com/?x=1&y=2"})
        self.assertTrue(response["success"])
        argv = shlex.split(execute.call_args.args[0])
        self.assertIn("https://example.com/?x=1&y=2", argv)
        self.assertNotIn("-subs", argv)
        self.assertNotIn("-s", argv)

    def test_hakrawler_preserves_each_feature_switch(self):
        for feature in ("forms", "robots", "sitemap", "wayback"):
            for enabled in (True, False):
                with self.subTest(feature=feature, enabled=enabled):
                    response, execute = endpoint("hakrawler", {"url": "https://example.com", feature: enabled})
                    self.assertTrue(response["success"])
                    self.assertIn(f"--hexstrike-{feature}={str(enabled).lower()}", execute.call_args.args[0])

    def test_dalfox_blind_requires_callback(self):
        for args in ("", "--blind", "--blind --debug", "--blind=", "-b ''"):
            response, execute = endpoint("dalfox", {
                "url": "https://example.com", "blind": True, "additional_args": args,
            })
            self.assertEqual(response[1], 400)
            execute.assert_not_called()

    def test_dalfox_blind_value_is_not_duplicated(self):
        for args in ("--blind https://callback.example", "--blind=https://callback.example", "-b https://callback.example"):
            response, execute = endpoint("dalfox", {
                "url": "https://example.com", "blind": True, "additional_args": args,
            })
            self.assertTrue(response["success"])
            self.assertTrue(execute.call_args.args[0].endswith(args))
            self.assertEqual(execute.call_args.args[0].count(args), 1)

    def test_dalfox_pipe_uses_explicit_url(self):
        response, execute = endpoint("dalfox", {"pipe_mode": True})
        self.assertEqual(response[1], 400)
        execute.assert_not_called()
        response, execute = endpoint("dalfox", {"pipe_mode": True, "url": "https://example.com/?a=1&b=2"})
        self.assertTrue(response["success"])
        argv = shlex.split(execute.call_args.args[0])
        self.assertEqual(argv[:5], ["printf", "%s\\n", "https://example.com/?a=1&b=2", "|", "dalfox"])

    def test_endpoint_values_survive_shell_tokenization(self):
        cases = [
            ("sqlmap", {"url": "https://example.com/?a=1&b=2", "data": "a=$x&b='text'"}, ["https://example.com/?a=1&b=2", "--data=a=$x&b='text'"]),
            ("hydra", {"target": "example.com", "service": "ssh", "username": "a b", "password": "p'$x"}, ["a b", "p'$x"]),
            ("gobuster", {"url": "https://example.com/?x=1&y=2", "wordlist": "/tmp/a b.txt", "use_recovery": False}, ["https://example.com/?x=1&y=2", "/tmp/a b.txt"]),
            ("ffuf", {"url": "https://example.com/?a=1&b=2", "mode": "parameter"}, ["https://example.com/?a=1&b=2&FUZZ=value"]),
            ("anew", {"input_data": "a'b\n$x", "output_file": "/tmp/a b.txt"}, ["a'b\n$x", "/tmp/a b.txt"]),
            ("x8", {"url": "https://example.com/?a=1&b=2", "body": "a='x'&b=$y", "headers": "X-Key: a'b"}, ["https://example.com/?a=1&b=2", "a='x'&b=$y", "X-Key: a'b"]),
            ("volatility3", {"memory_file": "/tmp/a b.raw", "plugin": "windows.pslist"}, ["/tmp/a b.raw"]),
            ("nmap_advanced", {"target": "example.com; echo unexpected"}, ["example.com; echo unexpected"]),
            ("checksec", {"binary": "/tmp/a b"}, ["--file=/tmp/a b"]),
        ]
        for name, payload, expected in cases:
            with self.subTest(endpoint=name):
                response, execute = endpoint(name, payload)
                self.assertTrue(response["success"])
                argv = shell_tokens(execute.call_args.args[0])
                for value in expected:
                    self.assertIn(value, argv)

    def test_all_smart_scan_targets_are_single_shell_argument(self):
        target = "https://example.com/?x=1&y='a b'"
        for node in TREE.body:
            if not isinstance(node, ast.FunctionDef) or not (node.name.startswith("execute_") and node.name.endswith("_scan")):
                continue
            with self.subTest(function=node.name):
                function, namespace = load_function(node.name)
                result = function(target, {"severity": "high", "tags": "cve", "wordlist": "/tmp/a b"})
                self.assertTrue(result["success"])
                argv = shell_tokens(namespace["execute_command"].call_args.args[0])
                self.assertIn(target + "/FUZZ" if node.name == "execute_ffuf_scan" else target, argv)
                self.assertNotIn("&", argv)
                if node.name == "execute_nuclei_scan":
                    self.assertEqual(argv[argv.index("-severity") + 1], "high")
                    self.assertEqual(argv[argv.index("-tags") + 1], "cve")

    def test_smart_scan_quotes_target_without_rewriting_advanced_args(self):
        function, namespace = load_function("execute_gobuster_scan")
        function("https://example.com/?a=1&b=2", {"wordlist": "/tmp/a b", "additional_args": "-H 'X-Key: hello world'"})
        command = namespace["execute_command"].call_args.args[0]
        self.assertIn("https://example.com/?a=1&b=2", shlex.split(command))
        self.assertIn("/tmp/a b", shlex.split(command))
        self.assertTrue(command.endswith("-H 'X-Key: hello world'"))


if __name__ == "__main__":
    unittest.main()
