"""本地启动入口与实际进程生命周期；只使用模拟API，不执行扫描。"""
import importlib.util
import asyncio
import json
import os
import re
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import start_local


class LocalConfigurationTests(unittest.TestCase):
    def test_default_paths_and_loopback_commands(self):
        with patch.dict(os.environ, {}, clear=True):
            args = start_local.parse_args([])
            config = start_local.local_configuration(args)
        self.assertEqual(str(ROOT / ".venv-api/bin/python"), config.api_python)
        self.assertEqual(str(ROOT / ".venv-mcp/bin/python"), config.mcp_python)
        api, mcp = start_local.local_commands(config)
        self.assertIn("host='127.0.0.1'", api[-1])
        self.assertIn("use_reloader=False", api[-1])
        self.assertEqual("127.0.0.1", mcp[mcp.index("--host") + 1])

    def test_cli_overrides_environment(self):
        with patch.dict(os.environ, {"PENTEST_TOOLS_PORT": "9001"}, clear=True):
            args = start_local.parse_args(["--api-port", "9002", "--mcp-port", "9003",
                "--api-python", sys.executable, "--mcp-python", sys.executable,
                "--startup-timeout", "4", "--shutdown-timeout", "0.5"])
            config = start_local.local_configuration(args)
        self.assertEqual((9002, 9003, 4, 0.5), (config.api_port, config.mcp_port,
                         config.startup_timeout, config.shutdown_timeout))
        self.assertIn("PENTEST_TOOLS_PORT='9002'", start_local.local_commands(config)[0][-1])

    def test_invalid_and_equal_ports_rejected(self):
        for ports in ((0, 8889), (65536, 8889), (8889, 8889)):
            with self.subTest(ports=ports), patch.dict(os.environ, {}, clear=True):
                args = start_local.parse_args(["--api-port", str(ports[0]),
                                               "--mcp-port", str(ports[1])])
                with self.assertRaises(ValueError):
                    start_local.local_configuration(args)

    def test_missing_interpreter_reports_install_instruction(self):
        with self.assertRaisesRegex(ValueError, "requirements.txt"):
            start_local.check_interpreter("/missing/pentest-tools-python", "requirements.txt")

    def test_venv_interpreter_symlink_is_not_resolved(self):
        with tempfile.TemporaryDirectory() as directory:
            interpreter = Path(directory) / "python"
            interpreter.symlink_to(sys.executable)
            args = start_local.parse_args(["--api-python", str(interpreter)])
            self.assertEqual(str(interpreter), start_local.local_configuration(args).api_python)

    def test_api_bootstrap_applies_binding_and_environment_without_reloader(self):
        with tempfile.TemporaryDirectory() as directory:
            module = Path(directory) / "server.py"
            module.write_text("import json, os\n"
                "class App:\n"
                "    def run(self, **kwargs):\n"
                "        print(json.dumps([kwargs, os.environ['PENTEST_TOOLS_PORT'], "
                "os.environ['PENTEST_TOOLS_HOST']]))\n"
                "app = App()\n", encoding="utf-8")
            args = start_local.parse_args(["--api-python", sys.executable,
                                           "--api-port", "19088", "--mcp-port", "19089"])
            with patch.dict(os.environ, {"PENTEST_TOOLS_PORT": "invalid"}):
                command = start_local.local_commands(start_local.local_configuration(args))[0]
                result = subprocess.run(command, cwd=directory, text=True,
                                        capture_output=True, check=True, timeout=5)
            settings, port, host = json.loads(result.stdout)
            self.assertEqual({"host": "127.0.0.1", "port": 19088,
                              "debug": False, "use_reloader": False}, settings)
            self.assertEqual(("19088", "127.0.0.1"), (port, host))

    def test_occupied_port_rejected_without_terminating_owner(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            with self.assertRaisesRegex(ValueError, "已被占用"):
                start_local.check_ports([listener.getsockname()[1]])
            self.assertGreater(listener.fileno(), 0)


def unused_ports():
    """同时占位两个端口再释放，降低测试自身重复分配的概率。"""
    with socket.socket() as first, socket.socket() as second:
        first.bind(("127.0.0.1", 0))
        second.bind(("127.0.0.1", 0))
        return first.getsockname()[1], second.getsockname()[1]


def wait_for_ready(process, port):
    """等待真实MCP就绪，不把进程存在当作成功。"""
    opener = build_opener(ProxyHandler({}))
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and process.poll() is None:
        try:
            with opener.open(f"http://127.0.0.1:{port}/readyz", timeout=0.3) as response:
                if json.load(response)["status"] == "ready":
                    return
        except (OSError, ValueError):
            time.sleep(0.05)
    raise AssertionError("本地双服务未就绪")


async def verify_mcp(port):
    """真实协议发现与只读工具调用，验证启动参数指向本次模拟API。"""
    from mcp import Client
    async with Client(f"http://127.0.0.1:{port}/mcp") as client:
        catalog = await client.list_tools()
        assert len(catalog.tools) == 150
        result = await client.call_tool("get_cache_stats", {})
        assert not result.is_error
        assert json.loads(result.content[0].text)["success"] is True


@unittest.skipUnless(importlib.util.find_spec("mcp"), "需安装requirements-mcp.txt")
class LocalLifecycleTests(unittest.TestCase):
    def make_api_wrapper(self, directory, port):
        """模拟API解释器，忽略真实API启动参数；MCP仍运行真实代码。"""
        wrapper = Path(directory) / "api interpreter"
        pid_file = Path(directory) / "api.pid"
        source = f'''#!{sys.executable}
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
Path({str(pid_file)!r}).write_text(str(os.getpid()))
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{{"success":true}}')
    def log_message(self, *args):
        pass
HTTPServer(("127.0.0.1", {port}), Handler).serve_forever()
'''
        wrapper.write_text(source, encoding="utf-8")
        wrapper.chmod(0o700)
        return wrapper, pid_file

    def launch(self, directory, api_port, mcp_port):
        """从项目外启动，验证脚本定位项目目录及含空格的解释器路径。"""
        wrapper, pid_file = self.make_api_wrapper(directory, api_port)
        log = tempfile.TemporaryFile(mode="w+")
        process = subprocess.Popen([sys.executable, str(ROOT / "scripts/start_local.py"),
            "--api-python", str(wrapper), "--mcp-python", sys.executable,
            "--api-port", str(api_port), "--mcp-port", str(mcp_port),
            "--startup-timeout", "10", "--shutdown-timeout", "1"],
            cwd=directory, stdout=log, stderr=log)
        return process, pid_file, log

    def verify_exit(self, action):
        """验证中断/终止/子服务故障后管理器退出、子进程和端口均回收。"""
        with tempfile.TemporaryDirectory() as directory:
            api_port, mcp_port = unused_ports()
            process, pid_file, log = self.launch(directory, api_port, mcp_port)
            try:
                wait_for_ready(process, mcp_port)
                asyncio.run(verify_mcp(mcp_port))
                api_pid = int(pid_file.read_text())
                log.seek(0)
                pids = [int(pid) for pid in re.findall(r"已启动服务：.*PID=(\d+)", log.read())]
                self.assertEqual(2, len(pids))
                failure = isinstance(action, str)
                if failure:
                    os.kill(api_pid if action == "api_failure" else pids[1], signal.SIGKILL)
                else:
                    process.send_signal(action)
                self.assertEqual(1 if failure else 0, process.wait(timeout=8))
                for pid in pids:
                    with self.assertRaises(ProcessLookupError):
                        os.kill(pid, 0)
                start_local.check_ports([api_port, mcp_port])
            except BaseException:
                log.seek(0)
                print(log.read(), file=sys.stderr)
                raise
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=8)
                log.close()

    def test_ctrl_c_cleans_up_both_services(self):
        self.verify_exit(signal.SIGINT)

    def test_sigterm_cleans_up_both_services(self):
        self.verify_exit(signal.SIGTERM)

    def test_api_failure_cleans_up_mcp(self):
        self.verify_exit("api_failure")

    def test_mcp_failure_cleans_up_api(self):
        self.verify_exit("mcp_failure")


if __name__ == "__main__":
    unittest.main()
