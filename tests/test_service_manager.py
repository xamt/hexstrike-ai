"""双服务生命周期与健康检查，不启动真实安全工具。"""
from pathlib import Path
import signal
import subprocess
import sys
import time
from urllib.error import URLError
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "docker"))
import service_health
import service_manager


class ServiceConfigurationTests(unittest.TestCase):
    def test_defaults_and_independent_interpreters(self):
        config = service_health.load_configuration({})
        self.assertEqual((8888, 8889), (config.api_port, config.mcp_port))
        commands = service_manager.service_commands(config)
        self.assertEqual(Path("/opt/pentest-tools"), config.root)
        self.assertEqual("/opt/pentest-tools/server.py", commands[0][1])
        self.assertEqual("/opt/pentest-tools/mcp_server.py", commands[1][1])
        self.assertEqual("/opt/hexstrike-venv/bin/python", commands[0][0])
        self.assertEqual("/opt/hexstrike-mcp-venv/bin/python", commands[1][0])
        self.assertNotIn("--transport", commands[1])
        self.assertEqual("http://127.0.0.1:8888", commands[1][-1])

    def test_custom_ports_and_deadlines(self):
        config = service_health.load_configuration({"HEXSTRIKE_PORT": "9088",
            "HEXSTRIKE_MCP_PORT": "9089", "HEXSTRIKE_STARTUP_TIMEOUT": "12.5",
            "HEXSTRIKE_SHUTDOWN_TIMEOUT": "2"})
        self.assertEqual(12.5, config.startup_timeout)
        self.assertEqual(2, config.shutdown_timeout)
        self.assertIn("9089", service_manager.service_commands(config)[1])

    def test_rejects_invalid_ports_and_deadlines(self):
        for value in ("0", "65536", "abc", "-1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                service_health.load_configuration({"HEXSTRIKE_PORT": value})
        with self.assertRaises(ValueError):
            service_health.load_configuration({"HEXSTRIKE_MCP_PORT": "8888"})
        for value in ("0", "-1", "nan", "inf", "bad"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                service_health.load_configuration({"HEXSTRIKE_STARTUP_TIMEOUT": value})

    def test_health_requires_both_services(self):
        config = service_health.load_configuration({})
        with patch.object(service_health, "probe_http", side_effect=[True, False]) as probe:
            self.assertFalse(service_health.services_healthy(config))
            self.assertEqual(["http://127.0.0.1:8888/api/cache/stats", "http://127.0.0.1:8889/readyz"],
                             [call.args[0] for call in probe.call_args_list])

    def test_health_probes_never_run_commands_or_use_inventory_health(self):
        with patch.object(service_health, "build_opener") as factory, \
             patch("subprocess.Popen", side_effect=AssertionError("探针不能启动命令")), \
             patch("os.system", side_effect=AssertionError("探针不能运行 shell")):
            response = factory.return_value.open.return_value.__enter__.return_value
            response.status = 200
            self.assertTrue(service_health.services_healthy(service_health.load_configuration({})))
            urls = [call.args[0] for call in factory.return_value.open.call_args_list]
        self.assertEqual(["http://127.0.0.1:8888/api/cache/stats",
                          "http://127.0.0.1:8889/readyz"], urls)
        self.assertTrue(all(not url.endswith("/health") for url in urls))

    def test_probe_bypasses_environment_proxies(self):
        with patch.object(service_health, "build_opener") as factory:
            response = factory.return_value.open.return_value.__enter__.return_value
            response.status = 200
            self.assertTrue(service_health.probe_http("http://127.0.0.1:8888/api/cache/stats"))
            self.assertEqual({}, factory.call_args.args[0].proxies)

    def test_health_probe_handles_network_and_http_failure(self):
        with patch.object(service_health, "build_opener") as factory:
            factory.return_value.open.side_effect = URLError("unavailable")
            self.assertFalse(service_health.probe_http("http://127.0.0.1:8888/api/cache/stats"))
            factory.return_value.open.side_effect = None
            response = factory.return_value.open.return_value.__enter__.return_value
            response.status = 503
            self.assertFalse(service_health.probe_http("http://127.0.0.1:8888/api/cache/stats"))


class ServiceManagerTests(unittest.TestCase):
    def setUp(self):
        self.config = service_health.load_configuration({"HEXSTRIKE_STARTUP_TIMEOUT": "0.03",
            "HEXSTRIKE_SHUTDOWN_TIMEOUT": "0.03"})

    def test_api_ready_before_mcp_is_started(self):
        events = []
        process = Mock(pid=123)
        process.poll.return_value = None
        manager = service_manager.ServiceManager(self.config)
        def start(command):
            events.append("api" if Path(command[1]).name == "server.py" else "mcp")
            manager.children.append(process)
        def ready(url):
            events.append(url.rsplit("/", 1)[-1])
            return True
        with patch.object(manager, "start", side_effect=start), \
             patch.object(manager, "wait_ready", side_effect=ready), \
             patch.object(manager, "monitor", return_value=1), \
             patch.object(manager, "shutdown") as shutdown:
            self.assertEqual(1, manager.run())
        self.assertEqual(["api", "stats", "mcp", "readyz"], events)
        shutdown.assert_called_once()

    def test_start_uses_argv_and_new_process_group(self):
        manager = service_manager.ServiceManager(self.config)
        with patch.object(service_manager.subprocess, "Popen") as popen:
            manager.start([sys.executable, "fake.py"])
        self.assertTrue(popen.call_args.kwargs["start_new_session"])
        self.assertNotIn("shell", popen.call_args.kwargs)

    def test_unexpected_clean_exit_is_failure(self):
        manager = service_manager.ServiceManager(self.config)
        manager.children = [Mock(pid=123, poll=Mock(return_value=0))]
        self.assertEqual(1, manager.monitor())

    def test_failed_startup_does_not_start_mcp(self):
        manager = service_manager.ServiceManager(self.config)
        with patch.object(manager, "start") as start, \
             patch.object(manager, "wait_ready", return_value=False), \
             patch.object(manager, "shutdown") as shutdown:
            self.assertEqual(1, manager.run())
        self.assertEqual(1, start.call_count)
        shutdown.assert_called_once()

    def test_readiness_timeout_and_child_death(self):
        manager = service_manager.ServiceManager(self.config)
        process = Mock(pid=123, poll=Mock(return_value=None))
        manager.children = [process]
        with patch.object(service_manager, "probe_http", return_value=False):
            self.assertFalse(manager.wait_ready("http://127.0.0.1:1/api/cache/stats"))
        process.poll.return_value = 0
        with patch.object(service_manager, "probe_http") as probe:
            self.assertFalse(manager.wait_ready("http://127.0.0.1:1/api/cache/stats"))
        probe.assert_not_called()

    def test_stop_signal_is_forwarded_and_returns_success(self):
        manager = service_manager.ServiceManager(self.config)
        manager.handle_signal(signal.SIGINT, None)
        self.assertEqual(signal.SIGINT, manager.stop_signal)
        self.assertEqual(0, manager.monitor())

    def test_group_cleanup_even_after_leader_exited(self):
        manager = service_manager.ServiceManager(self.config)
        manager.children = [Mock(pid=123, poll=Mock(return_value=0))]
        with patch.object(service_manager.os, "killpg") as killpg:
            manager.shutdown()
        self.assertIn(unittest.mock.call(123, signal.SIGTERM), killpg.call_args_list)
        self.assertIn(unittest.mock.call(123, signal.SIGKILL), killpg.call_args_list)

    def test_stop_signal_is_sent_to_all_groups(self):
        manager = service_manager.ServiceManager(self.config)
        manager.children = [Mock(pid=123), Mock(pid=456)]
        manager.handle_signal(signal.SIGINT, None)
        with patch.object(manager, "groups_alive", return_value=False), \
             patch.object(service_manager.os, "killpg") as killpg:
            manager.shutdown()
        for pid in (123, 456):
            self.assertIn(unittest.mock.call(pid, signal.SIGINT), killpg.call_args_list)

    def test_health_success_cannot_hide_an_exited_child(self):
        manager = service_manager.ServiceManager(self.config)
        process = Mock(pid=123, poll=Mock(side_effect=[None, 0]))
        manager.children = [process]
        with patch.object(service_manager, "probe_http", return_value=True):
            self.assertFalse(manager.wait_ready("http://127.0.0.1:1/api/cache/stats"))

    def test_mcp_failure_cleans_up_both_services(self):
        manager = service_manager.ServiceManager(self.config)
        with patch.object(manager, "start") as start, \
             patch.object(manager, "wait_ready", side_effect=[True, False]), \
             patch.object(manager, "shutdown") as shutdown:
            self.assertEqual(1, manager.run())
        self.assertEqual(2, start.call_count)
        shutdown.assert_called_once()

    def test_spawn_failure_is_reported_and_cleaned(self):
        manager = service_manager.ServiceManager(self.config)
        with patch.object(manager, "start", side_effect=OSError("missing executable")), \
             patch.object(manager, "shutdown") as shutdown:
            self.assertEqual(1, manager.run())
        shutdown.assert_called_once()

    def test_real_child_process_stops(self):
        manager = service_manager.ServiceManager(self.config)
        manager.start([sys.executable, "-c", "import time; time.sleep(30)"])
        try:
            manager.shutdown()
            self.assertIsNotNone(manager.children[0].poll())
        finally:
            if manager.children[0].poll() is None:
                manager.children[0].kill()
                manager.children[0].wait()

    def test_real_uncooperative_child_is_killed(self):
        manager = service_manager.ServiceManager(self.config)
        child = subprocess.Popen([sys.executable, "-c",
            "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            "print('ready', flush=True); time.sleep(30)"],
            start_new_session=True, stdout=subprocess.PIPE, text=True)
        manager.children.append(child)
        try:
            self.assertEqual("ready", child.stdout.readline().strip())
            started = time.monotonic()
            manager.shutdown()
            self.assertLess(time.monotonic() - started, 2)
            self.assertEqual(-signal.SIGKILL, child.returncode)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
            child.stdout.close()


if __name__ == "__main__":
    unittest.main()
