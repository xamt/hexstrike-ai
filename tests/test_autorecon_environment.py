"""AutoRecon 环境适配的离线契约；不运行 Nmap 或 AutoRecon。"""
import importlib.util
import inspect
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    """从指定文件加载独立兼容模块。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


compat = load_module("autorecon_compat", ROOT / "docker/compat/autorecon-compat.py")


class AutoReconAdapterTests(unittest.TestCase):
    def test_legacy_profiles_add_plugins_and_disable_only_default_port_scans(self):
        for profile in ("top-100-ports", "top-1000-ports"):
            args = ["example.com", "--port-scans", profile]
            self.assertEqual(compat.adapt(args), args + [
                "--add-plugins-dir", compat.PLUGINS_DIR,
                "--exclude-tags", "default-port-scan",
            ])

    def test_explicit_other_plugins_and_excluded_service_tags_survive(self):
        args = ["host", "--port-scans=top-100-ports,all-tcp-ports",
                "--exclude-tags=long,http", "--service-scans", "http-curl"]
        adapted = compat.adapt(args)
        self.assertIn("--port-scans=top-100-ports,all-tcp-ports", adapted)
        self.assertEqual(adapted[-2:], ["--exclude-tags", "long,http,default-port-scan"])
        self.assertIn("http-curl", adapted)

    def test_repeated_options_use_native_last_value_semantics(self):
        args = ["host", "--port-scans", "top-100-ports", "--port-scans", "top-tcp-ports"]
        self.assertEqual(compat.adapt(args), args)
        args = ["host", "--port-scans", "top-100-ports", "--exclude-tags=old",
                "--exclude-tags", "long,default-port-scan"]
        result = compat.adapt(args)
        self.assertEqual(result[-2:], ["--exclude-tags", "long,default-port-scan"])
        self.assertNotIn("--exclude-tags=old", result)

    def test_existing_compat_directory_is_not_duplicated(self):
        args = ["host", "--port-scans=top-100-ports",
                "--add-plugins-dir", compat.PLUGINS_DIR]
        result = compat.adapt(args)
        self.assertEqual(result.count("--add-plugins-dir"), 1)

    def test_combined_profiles_share_only_one_port_scan_exclusion(self):
        args = ["host", "--port-scans=top-100-ports,top-1000-ports"]
        result = compat.adapt(args)
        self.assertEqual(result[-2:], ["--exclude-tags", "default-port-scan"])
        self.assertEqual(result.count("--add-plugins-dir"), 1)

    def test_inserted_options_precede_target_terminator(self):
        result = compat.adapt(["--port-scans=top-100-ports", "--", "host"])
        self.assertEqual(result[-2:], ["--", "host"])
        self.assertLess(result.index("--exclude-tags"), result.index("--"))

    def test_explicit_conflicting_directories_or_port_lists_are_not_overwritten(self):
        for extra in (["--add-plugins-dir", "/custom/plugins"], ["--ports=80,443"]):
            with self.assertRaises(ValueError):
                compat.adapt(["host", "--port-scans=top-100-ports"] + extra)

    def test_native_calls_and_option_terminator_remain_native(self):
        for args in (["--help"], ["host"], ["host", "--port-scans=all-tcp-ports"],
                     ["--", "--port-scans=top-100-ports"]):
            self.assertEqual(compat.adapt(args), args)

    def test_exec_replaces_wrapper_without_shell(self):
        args = ["host", "--port-scans=top-100-ports"]
        with patch.object(compat.sys, "argv", ["autorecon"] + args):
            with patch.object(compat.os, "execv") as execute:
                self.assertEqual(compat.main(), 0)
        execute.assert_called_once_with("/usr/bin/autorecon", ["autorecon"] + compat.adapt(args))


class AutoReconPluginTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.plugins_stub = types.ModuleType("autorecon.plugins")
        self.plugins_stub.PortScan = type("PortScan", (), {"__module__": "autorecon.plugins"})
        with patch.dict(sys.modules, {"autorecon.plugins": self.plugins_stub}):
            self.plugins = load_module("autorecon.hexstrike_tcp_profiles", ROOT /
                "docker/compat/autorecon-plugins/hexstrike-tcp-profiles.py")

    def test_upstream_class_discovery_finds_exactly_both_port_plugins(self):
        # e7e98f6 main.py:987-999 使用 inspect.isclass；不会注册辅助协程。
        discovered = []
        for _, cls in inspect.getmembers(self.plugins, predicate=inspect.isclass):
            if cls.__module__ in ["autorecon.plugins", "autorecon.targets"]:
                continue
            self.assertTrue(issubclass(cls, self.plugins_stub.PortScan))
            discovered.append(cls().slug)
        self.assertEqual(set(discovered), {"top-100-ports", "top-1000-ports"})

    async def test_upstream_caller_frame_and_default_nmap_contract(self):
        # e7e98f6 targets.py:59-75 通过直接调用帧的 self 获取插件；
        # config.py 的默认 nmap 参数不区分 root，也不包含 -sS。
        process = types.SimpleNamespace(wait=AsyncMock(return_value=0))
        captured = []

        async def execute(command, blocking=True):
            plugin = inspect.currentframe().f_back.f_locals["self"]
            nmap_extra = "-vv --reason -Pn -T4"
            captured.append((plugin.slug, command.format(
                nmap_extra=nmap_extra, scandir="/tmp/scans", address="example.com")))
            return process, "stream", "errors"

        target = types.SimpleNamespace(ports=None, execute=execute,
            extract_services=AsyncMock(return_value=[]))
        for cls in (self.plugins.Top100Ports, self.plugins.Top1000Ports):
            await cls().run(target)
        self.assertEqual([slug for slug, _ in captured], ["top-100-ports", "top-1000-ports"])
        self.assertTrue(all("-sS" not in command for _, command in captured))

    async def test_top_profiles_are_tcp_only_and_return_discovered_services(self):
        for cls, count in ((self.plugins.Top100Ports, 100), (self.plugins.Top1000Ports, 1000)):
            plugin = cls()
            services = [object()]
            process = types.SimpleNamespace(wait=AsyncMock(return_value=0))
            target = types.SimpleNamespace(
                ports=None, execute=AsyncMock(return_value=(process, "stream", "errors")),
                extract_services=AsyncMock(return_value=services))
            self.assertEqual(await plugin.run(target), services)
            command = target.execute.call_args.args[0]
            self.assertIn(f"--top-ports {count}", command)
            self.assertIn("-sV", command)
            self.assertIn("{nmap_extra}", command)
            self.assertNotIn("-sU", command)
            self.assertNotIn("-p-", command)
            self.assertEqual(plugin.type, "tcp")
            self.assertEqual(plugin.slug, f"top-{count}-ports")
            self.assertNotIn("default", plugin.tags)
            self.assertNotIn("default-port-scan", plugin.tags)
            target.extract_services.assert_awaited_once_with("stream")
            process.wait.assert_awaited_once()

    async def test_failed_nmap_is_not_treated_as_success(self):
        process = types.SimpleNamespace(wait=AsyncMock(return_value=2))
        target = types.SimpleNamespace(ports=None,
            execute=AsyncMock(return_value=(process, "stream", "errors")),
            extract_services=AsyncMock(return_value=[]))
        with self.assertRaises(RuntimeError):
            await self.plugins.Top100Ports().run(target)

    async def test_explicit_port_list_cannot_silently_change_profile_scope(self):
        target = types.SimpleNamespace(ports={"tcp": [80]}, execute=AsyncMock())
        with self.assertRaises(ValueError):
            await self.plugins.Top100Ports().run(target)
        target.execute.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
