"""从真实 MCP 函数默认值开始验证请求；不启动服务、工具或网络。"""
import importlib.util
import io
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from test_server_command_contracts import ROOT, endpoint

sys.path.insert(0, str(ROOT))
from tools import register_tools


def mcp_request(name, **arguments):
    """载入原 MCP 函数，不重写其签名与数据构造，再捕获 HTTP 请求。"""
    client = Mock()
    client.safe_post.return_value = {"success": True}
    functions = {}
    def register(function):
        functions.setdefault(function.__name__, function)
        return function
    mcp = Mock()
    mcp.tool.return_value = register
    register_tools(mcp, client)
    functions[name](**arguments)
    return client.safe_post.call_args.args


def mcp_command(name, **arguments):
    """贯穿原 MCP 请求和真实路由函数，仅替换最终命令执行器。"""
    route, payload = mcp_request(name, **arguments)
    response, execute = endpoint(route.rsplit("/", 1)[1], payload)
    if not isinstance(response, dict) or not response.get("success"):
        raise AssertionError(f"默认 MCP 请求被拒绝: {response}")
    return shlex.split(execute.call_args.args[0])


class MCPDefaultContractTests(unittest.TestCase):
    def test_autorecon_comprehensive_default_is_compatible_profile(self):
        argv = mcp_command("autorecon_comprehensive", target="example.com")
        self.assertEqual(argv[argv.index("--port-scans") + 1], "top-100-ports")
        self.assertEqual(argv[argv.index("-o") + 1], "/tmp/autorecon")

    def test_autorecon_scan_empty_defaults_are_normalized(self):
        argv = mcp_command("autorecon_scan", target="example.com")
        self.assertNotIn("", argv)
        self.assertEqual(argv[argv.index("--port-scans") + 1], "top-100-ports")
        self.assertEqual(argv[argv.index("--heartbeat") + 1], "60")
        self.assertEqual(argv[argv.index("--timeout") + 1], "300")
        self.assertEqual(argv[argv.index("-o") + 1], "/tmp/autorecon")

    def test_hakrawler_default_keeps_distinct_features_without_subdomains(self):
        argv = mcp_command("hakrawler_crawl", url="https://example.com/?a=1&b=2")
        self.assertEqual(argv[:5], ["printf", "%s\\n", "https://example.com/?a=1&b=2", "|", "hakrawler"])
        self.assertEqual(argv[argv.index("-d") + 1], "2")
        for name, value in (("forms", "true"), ("robots", "true"), ("sitemap", "true"), ("wayback", "false")):
            self.assertIn(f"--hexstrike-{name}={value}", argv)
        self.assertNotIn("-subs", argv)

    def test_autorecon_defaults_reach_real_environment_adapter(self):
        spec = importlib.util.spec_from_file_location("autorecon_default_adapter", ROOT / "docker/compat/autorecon-compat.py")
        adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter)
        for name in ("autorecon_comprehensive", "autorecon_scan"):
            argv = mcp_command(name, target="example.com")
            with patch.object(adapter.sys, "argv", argv), patch.object(adapter.os, "execv") as execute:
                self.assertEqual(adapter.main(), 0)
            executable, command = execute.call_args.args
            self.assertEqual(executable, "/usr/bin/autorecon")
            self.assertEqual(command[command.index("--port-scans") + 1], "top-100-ports")
            self.assertEqual(command[command.index("--exclude-tags") + 1], "default-port-scan")
            self.assertEqual(command[command.index("--add-plugins-dir") + 1], adapter.PLUGINS_DIR)

    def test_hakrawler_default_reaches_environment_and_native_command(self):
        # Import through the same sibling directory used by the installed entry point.
        import sys
        with patch.object(sys, "path", [str(ROOT / "docker/compat")] + sys.path):
            import hakrawler_runtime as adapter
        argv = mcp_command("hakrawler_crawl", url="https://example.com/")
        output = io.StringIO()
        native_output = '{"Source":"form","URL":"https://example.com/login"}'
        with patch.object(adapter, "run_process", return_value=native_output) as execute:
            with patch.object(adapter, "discover", return_value=[]) as discover:
                with patch.object(adapter.Fetcher, "fetch", return_value=b"ok"):
                    result = adapter.main(argv[5:], io.StringIO(argv[2] + "\n"), output)
        self.assertEqual(result, 0)
        native = execute.call_args.args[0]
        self.assertEqual(native[0], "/usr/bin/hakrawler")
        self.assertEqual(native[native.index("-d") + 1], "2")
        self.assertNotIn("-subs", native)
        self.assertFalse(any(value.startswith("--hexstrike-") for value in native))
        self.assertFalse(discover.call_args.args[1]["wayback"])
        self.assertEqual(output.getvalue().strip(), "https://example.com/login")

    def test_compatibility_assets_are_in_base_build_and_installation(self):
        base = (ROOT / "Dockerfile.base").read_text()
        install = (ROOT / "docker/compat/install.sh").read_text()
        for name in ("autorecon-compat.py", "hakrawler-compat.py", "hakrawler_runtime.py",
                     "hakrawler_sources.py", "hakrawler_process.py"):
            self.assertTrue((ROOT / "docker/compat" / name).is_file())
            self.assertIn(f"source=docker/compat/{name},target=/tmp/docker/compat/{name}", base)
        self.assertIn("source=docker/compat/autorecon-plugins/hexstrike-tcp-profiles.py,target=/tmp/docker/compat/autorecon-plugins/hexstrike-tcp-profiles.py", base)
        self.assertIn("for name in autorecon hakrawler; do", install)
        self.assertIn('ln -s "../${name}-compat.py"', install)
        self.assertIn("/opt/hexstrike-compat/autorecon-plugins/hexstrike-tcp-profiles.py", install)

    def test_installed_hakrawler_symlink_resolves_sibling_modules(self):
        # 空输入在启动网络或安全工具前失败，仅验证安装布局及导入路径。
        with tempfile.TemporaryDirectory() as directory:
            from pathlib import Path
            root = Path(directory)
            (root / "bin").mkdir()
            for name in ("hakrawler-compat.py", "hakrawler_runtime.py",
                         "hakrawler_sources.py", "hakrawler_process.py"):
                shutil.copyfile(ROOT / "docker/compat" / name, root / name)
            (root / "bin/hakrawler").symlink_to("../hakrawler-compat.py")
            result = subprocess.run([sys.executable, str(root / "bin/hakrawler"),
                                     "--hexstrike-forms=true"], input="", text=True,
                                    capture_output=True, timeout=5, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("标准输入必须包含", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
