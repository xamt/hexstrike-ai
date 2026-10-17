"""只运行兼容入口的参数转换，所有真实进程调用均使用模拟对象。"""
import ast
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "docker/compat/install.sh").read_text()
SOURCES = [section.split("\nPY", 1)[0] for section in SCRIPT.split("<<'PY'\n")[1:]]


class CliCompatibilityTests(unittest.TestCase):
    def run_arjun(self, arguments, statuses):
        """用假退出状态检查参数转换，不执行命令。"""
        namespace = {"__name__": "compat_test"}
        exec(compile(SOURCES[0], "arjun", "exec"), namespace)
        with patch("sys.argv", ["arjun"] + arguments), patch("subprocess.call", side_effect=statuses) as calls:
            status = namespace["main"]()
        return status, [call.args[0] for call in calls.call_args_list]

    def test_old_get_and_post_both_run(self):
        status, calls = self.run_arjun(["-u", "https://example.com", "--get", "--post"], [0, 0])
        self.assertEqual(status, 0)
        self.assertEqual(calls, [["/usr/bin/arjun", "-u", "https://example.com", "-m", mode]
                                 for mode in ("GET", "POST")])

    def test_modern_arguments_unchanged(self):
        arguments = ["-u", "https://example.com", "-m", "JSON"]
        self.assertEqual(self.run_arjun(arguments, [0]), (0, [["/usr/bin/arjun"] + arguments]))

    def test_failure_stops_without_retry(self):
        status, calls = self.run_arjun(["--get", "--post"], [7])
        self.assertEqual(status, 7)
        self.assertEqual(len(calls), 1)

    def test_mixed_method_flags_rejected(self):
        status, calls = self.run_arjun(["--get", "-m", "POST"], [])
        self.assertEqual((status, calls), (2, []))

    def test_fierce_and_jwt_compatibility(self):
        for source, arguments, executable, forwarded in (
            (SOURCES[1], ["fierce", "-dns", "example.com"], "/usr/bin/fierce",
             ["fierce", "--domain", "example.com"]),
            (SOURCES[2], ["/opt/jwt_tool/jwt_tool.py", "-h"], "/usr/local/bin/jwt_tool", ["jwt_tool", "-h"]),
        ):
            ast.parse(source)
            with patch("sys.argv", arguments), patch("os.execv") as execute:
                exec(compile(source, "compat", "exec"), {})
            execute.assert_called_once_with(executable, forwarded)


if __name__ == "__main__":
    unittest.main()
