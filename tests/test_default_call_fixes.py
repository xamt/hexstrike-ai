"""贯穿真实 MCP 默认请求，隔离工具执行，验证三个局部路由修复。"""
import shlex
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

from test_mcp_default_contracts import mcp_request
from test_server_command_contracts import load_function


def call(name, payload, **overrides):
    """调用真实路由函数，不启动 HTTP 服务或外部工具。"""
    function, namespace = load_function(name, request=SimpleNamespace(json=payload),
                                        urlparse=urlparse, **overrides)
    return function(), namespace["execute_command"]


class RpcclientDefaultsTests(unittest.TestCase):
    def test_mcp_anonymous_default_is_noninteractive(self):
        _, payload = mcp_request("rpcclient_enumeration", target="192.0.2.1")
        response, execute = call("rpcclient", payload)
        self.assertTrue(response["success"])
        argv = shlex.split(execute.call_args.args[0])
        self.assertEqual(argv[0], "rpcclient")
        self.assertIn("-N", argv)
        self.assertEqual(argv[argv.index("-U") + 1], "")
        self.assertEqual(argv[argv.index("-c") + 1], "enumdomusers;enumdomgroups;querydominfo")
        self.assertNotIn("|", argv)

    def test_credentials_and_commands_are_single_arguments(self):
        for password in ("", "p'a $ss"):
            _, execute = call("rpcclient", {
                "target": "server name", "username": "user name", "password": password,
                "domain": "test domain", "commands": "help;querydominfo", "additional_args": "--debuglevel=1",
            })
            argv = shlex.split(execute.call_args.args[0])
            self.assertNotIn("-N", argv)
            self.assertIn(f"user name%{password}", argv)
            self.assertIn("test domain", argv)
            self.assertIn("server name", argv)
            self.assertIn("help;querydominfo", argv)
            self.assertEqual(argv[-1], "--debuglevel=1")


class FfufDefaultsTests(unittest.TestCase):
    def test_default_directory_urls(self):
        cases = {
            "https://example.test": "https://example.test/FUZZ",
            "https://example.test/": "https://example.test/FUZZ",
            "https://example.test/app/?a=1&b=2": "https://example.test/app/FUZZ?a=1&b=2",
            "https://example.test/a//b/": "https://example.test/a//b/FUZZ",
            "https://example.test/FUZZ?x=1": "https://example.test/FUZZ?x=1",
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                _, payload = mcp_request("ffuf_scan", url=url)
                response, execute = call("ffuf", payload)
                self.assertTrue(response["success"])
                argv = shlex.split(execute.call_args.args[0])
                self.assertEqual(argv[argv.index("-u") + 1], expected)

    def test_parameter_mode_preserves_existing_query(self):
        _, execute = call("ffuf", {"url": "https://example.test/?a=1", "mode": "parameter"})
        self.assertIn("https://example.test/?a=1&FUZZ=value", shlex.split(execute.call_args.args[0]))


class ForemostDefaultsTests(unittest.TestCase):
    def test_mcp_default_allocates_distinct_empty_directories(self):
        _, payload = mcp_request("foremost_carving", input_file="/tmp/input image.dd")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = lambda value: root if value == "/tmp/foremost_output" else Path(value)
            results = []
            for _ in range(2):
                result, execute = call("foremost", payload, Path=path, tempfile=tempfile)
                output = Path(result["output_directory"])
                self.assertTrue(output.is_dir())
                self.assertEqual(output.parent, root)
                self.assertFalse(list(output.iterdir()))
                argv = shlex.split(execute.call_args.args[0])
                self.assertEqual(argv[argv.index("-o") + 1], str(output))
                self.assertIn("/tmp/input image.dd", argv)
                self.assertEqual(execute.call_args.kwargs, {"use_cache": False})
                (output / "audit.txt").write_text("preserved report")
                results.append(output)
            self.assertNotEqual(*results)
            self.assertTrue(all((output / "audit.txt").is_file() for output in results))

    def test_explicit_nonempty_directory_is_rejected_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "audit.txt"
            report.write_text("existing result")
            result, execute = call("foremost", {"input_file": "image.dd", "output_dir": directory},
                                   Path=Path, tempfile=tempfile)
            self.assertEqual(result[1], 400)
            execute.assert_not_called()
            self.assertEqual(report.read_text(), "existing result")

    def test_explicit_empty_directory_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            result, execute = call("foremost", {"input_file": "image.dd", "output_dir": directory},
                                   Path=Path, tempfile=tempfile)
            self.assertEqual(result["output_directory"], directory)
            self.assertTrue(result["success"])
            self.assertIn(directory, shlex.split(execute.call_args.args[0]))


if __name__ == "__main__":
    unittest.main()
