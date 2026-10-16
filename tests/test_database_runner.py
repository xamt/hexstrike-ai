"""使用本地 Python 伪客户端测试执行边界；无网络和真实数据库调用。"""
import ast
import json
import os
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from database_tools.commands import Invocation
from database_tools.contracts import validate_request
from database_tools.runner import execute_database


def execute_fake(script, **changes):
    """执行受控的本地伪客户端，复用真实管道/超时/输出处理。"""
    args = validate_request("mysql_query", {
        "host": "db.example.test", "query": "SELECT 1", **changes})
    fake = Invocation([sys.executable, "-c", script])
    with patch("database_tools.runner.build_invocation", return_value=fake):
        return execute_database("mysql_query", args)


class DatabaseRunnerTests(unittest.TestCase):
    def test_success_and_nonzero_exit(self):
        success = execute_fake("print('row')")
        self.assertTrue(success["success"])
        self.assertEqual(success["stdout"], "row\n")
        failure = execute_fake("import sys; print('bad', file=sys.stderr); sys.exit(7)")
        self.assertFalse(failure["success"])
        self.assertEqual(failure["return_code"], 7)
        self.assertEqual(failure["error_code"], "command_failed")

    def test_timeout_does_not_retry(self):
        result = execute_fake("import time; time.sleep(20)", timeout=1)
        self.assertTrue(result["timed_out"])
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "timeout")
        self.assertLess(result["execution_time"], 4)

    def test_combined_output_cap_terminates_producer(self):
        result = execute_fake("import sys; sys.stdout.write('x'*20000); sys.stdout.flush()",
                              max_output_bytes=1024)
        self.assertFalse(result["success"])
        self.assertTrue(result["truncated"])
        self.assertLessEqual(len((result["stdout"] + result["stderr"]).encode()), 1024)
        self.assertEqual(result["error_code"], "output_limit")

    def test_credentials_redacted_in_all_output(self):
        result = execute_fake("import sys; print('test-secret'); print('test-secret', file=sys.stderr)",
                              password="test-secret")
        self.assertNotIn("test-secret", json.dumps(result))
        self.assertIn("REDACTED", result["stdout"])
        self.assertIn("REDACTED", result["stderr"])

    def test_complete_output_does_not_redact_partial_match(self):
        result = execute_fake("import sys; sys.stdout.write('result')", password="test-secret")
        self.assertEqual(result["stdout"], "result")

    def test_truncated_password_prefix_is_not_exposed(self):
        result = execute_fake("import sys; sys.stdout.write('x'*1020 + 'test-secret' + 'z'*100)",
                              password="test-secret", max_output_bytes=1024)
        self.assertTrue(result["truncated"])
        self.assertNotIn("test", result["stdout"])

    def test_missing_binary_and_spawn_error_do_not_disclose_secrets(self):
        args = validate_request("mysql_query", {"host": "x", "query": "SELECT 1"})
        with patch("database_tools.runner.shutil.which", return_value=None):
            self.assertEqual(execute_database("mysql_query", args)["error_code"], "tool_missing")
        with patch("database_tools.runner.shutil.which", return_value="/fake/mysql"):
            with patch("database_tools.runner.subprocess.Popen", side_effect=OSError("SECRET")):
                result = execute_database("mysql_query", args)
        self.assertEqual(result["error_code"], "execution_error")
        self.assertNotIn("SECRET", json.dumps(result))

    def test_busy_returns_without_starting_process(self):
        args = validate_request("mysql_query", {"host": "x", "query": "SELECT 1"})
        semaphore = threading.BoundedSemaphore(1)
        semaphore.acquire()
        with patch("database_tools.runner.SLOTS", semaphore):
            with patch("database_tools.runner.subprocess.Popen") as popen:
                result = execute_database("mysql_query", args)
                self.assertEqual(result["error_code"], "busy")
                popen.assert_not_called()
        semaphore.release()

    def test_slot_released_after_error(self):
        args = validate_request("mysql_query", {"host": "x", "query": "SELECT 1"})
        semaphore = threading.BoundedSemaphore(1)
        with patch("database_tools.runner.SLOTS", semaphore):
            with patch("database_tools.runner.shutil.which", return_value=None):
                execute_database("mysql_query", args)
            self.assertTrue(semaphore.acquire(blocking=False))
        semaphore.release()

    def test_stdin_stream_and_isolated_environment(self):
        script = "import sys,os; print(sys.stdin.read()); print(os.getenv('PARENT_SECRET', 'absent'))"
        fake = Invocation([sys.executable, "-c", script], b"a" * 65536)
        args = validate_request("mysql_query", {"host": "x", "query": "SELECT 1",
                                                "max_output_bytes": 100000})
        with patch.dict(os.environ, {"PARENT_SECRET": "SECRET"}):
            with patch("database_tools.runner.build_invocation", return_value=fake):
                result = execute_database("mysql_query", args)
        self.assertTrue(result["success"])
        self.assertIn("a" * 65536, result["stdout"])
        self.assertIn("absent", result["stdout"])
        self.assertNotIn("SECRET", result["stdout"])

    def test_server_registration_is_present(self):
        tree = ast.parse(Path("hexstrike_server.py").read_text("utf-8"))
        calls = [node for node in tree.body if isinstance(node, ast.Expr)
                 and isinstance(node.value, ast.Call)
                 and isinstance(node.value.func, ast.Name)
                 and node.value.func.id == "register_database_routes"]
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
