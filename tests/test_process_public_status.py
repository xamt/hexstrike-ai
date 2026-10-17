"""隔离进程查询与控制函数；仅使用假进程，不启动服务、不发送真实信号。"""
import ast
import copy
import json
import logging
import signal
import threading
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "server.py"
FUNCTIONS = {
    "list_processes", "get_process_status", "pause_process",
    "resume_process", "process_dashboard",
}


def json_response(value):
    """强制经过真实JSON编码，而不是让不可序列化对象被测试桩放过。"""
    return json.loads(json.dumps(value, allow_nan=False))


def isolated_process_api():
    """仅编译进程管理类和路由，隔离所有模块导入与真实进程副作用。"""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    nodes = []
    for node in tree.body:
        selected = isinstance(node, ast.ClassDef) and node.name == "ProcessManager"
        selected |= isinstance(node, ast.FunctionDef) and node.name in FUNCTIONS
        if selected:
            item = copy.deepcopy(node)
            if isinstance(item, ast.FunctionDef):
                item.decorator_list = []
            nodes.append(item)
    namespace = {
        "active_processes": {}, "process_lock": threading.Lock(),
        "logger": logging.getLogger(__name__), "jsonify": json_response,
        "time": SimpleNamespace(time=Mock(return_value=120.0)),
        "os": SimpleNamespace(kill=Mock()), "signal": signal,
        "datetime": datetime,
        "psutil": SimpleNamespace(cpu_percent=Mock(return_value=1.0),
                                  virtual_memory=lambda: SimpleNamespace(percent=2.0),
                                  net_connections=lambda: []),
        "ModernVisualEngine": SimpleNamespace(create_live_dashboard=Mock(return_value="概览"),
                                             render_progress_bar=Mock(return_value="进度")),
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace


class ProcessPublicStatusTests(unittest.TestCase):
    def setUp(self):
        self.namespace = isolated_process_api()
        self.manager = self.namespace["ProcessManager"]
        self.process = SimpleNamespace(poll=Mock(return_value=None))
        self.manager.register_process(123, "工具 --target example.test", self.process)
        self.namespace["active_processes"][123]["start_time"] = 100.0

    def test_list_and_status_expose_only_public_json_fields(self):
        self.manager.update_process_progress(123, 0.5, "脱敏输出", 10)
        self.namespace["active_processes"][123]["future_private_handle"] = object()
        expected = {"pid", "command", "start_time", "status", "progress",
                    "last_output", "bytes_processed", "runtime", "eta"}
        for info in (self.manager.get_process_status(123),
                     self.manager.list_active_processes()[123]):
            self.assertEqual(set(info), expected)
            self.assertEqual(json_response(info)["pid"], 123)
        self.assertIs(self.namespace["active_processes"][123]["process"], self.process)
        self.process.poll.assert_not_called()

    def test_public_snapshots_do_not_alias_registry_or_each_other(self):
        first = self.manager.get_process_status(123)
        listed = self.manager.list_active_processes()
        first["status"] = "changed"
        listed[123]["runtime_formatted"] = "changed"
        listed.pop(123)
        self.assertEqual(self.namespace["active_processes"][123]["status"], "running")
        self.assertNotIn("runtime_formatted", self.namespace["active_processes"][123])
        self.assertEqual(self.manager.get_process_status(123)["status"], "running")

    def test_actual_list_and_status_routes_serialize_and_preserve_format(self):
        self.manager.update_process_progress(123, 0.5, "脱敏输出", 10)
        listed = self.namespace["list_processes"]()
        self.assertTrue(listed["success"])
        self.assertEqual(listed["total_count"], 1)
        info = listed["active_processes"]["123"]
        self.assertNotIn("process", info)
        self.assertEqual(info["runtime_formatted"], "20.0s")
        self.assertEqual(info["eta_formatted"], "20.0s")
        status = self.namespace["get_process_status"](123)
        self.assertEqual(status["process"], info)
        self.assertNotIn("runtime_formatted", self.namespace["active_processes"][123])
        self.assertNotIn("eta_formatted", self.namespace["active_processes"][123])

    def test_empty_list_unknown_process_and_unknown_eta_keep_contract(self):
        info = self.namespace["get_process_status"](123)["process"]
        self.assertEqual(info["eta_formatted"], "Unknown")
        self.assertIsNone(self.manager.get_process_status(999))
        payload, status = self.namespace["get_process_status"](999)
        self.assertEqual(status, 404)
        self.assertFalse(payload["success"])
        self.manager.cleanup_process(123)
        self.assertEqual(self.namespace["list_processes"](),
                         {"success": True, "active_processes": {}, "total_count": 0})

    def test_mock_pause_resume_retain_internal_handle_and_public_status(self):
        self.assertTrue(self.namespace["pause_process"](123)["success"])
        self.namespace["os"].kill.assert_called_once_with(123, signal.SIGSTOP)
        self.assertEqual(self.namespace["get_process_status"](123)["process"]["status"], "paused")
        self.assertTrue(self.namespace["resume_process"](123)["success"])
        self.namespace["os"].kill.assert_called_with(123, signal.SIGCONT)
        self.assertEqual(self.namespace["get_process_status"](123)["process"]["status"], "running")
        self.assertIs(self.namespace["active_processes"][123]["process"], self.process)

    def test_dashboard_uses_safe_snapshots_without_changing_metrics(self):
        response = self.namespace["process_dashboard"]()
        self.assertEqual(response["total_processes"], 1)
        self.assertEqual(response["processes"][0]["pid"], 123)
        self.assertEqual(response["system_load"]["active_connections"], 0)
        received = self.namespace["ModernVisualEngine"].create_live_dashboard.call_args.args[0]
        self.assertNotIn("process", received[123])
        json_response(received)


if __name__ == "__main__":
    unittest.main()
