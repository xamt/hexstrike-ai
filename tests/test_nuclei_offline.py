"""验证离线模板入口：只模拟原生进程，不联网、不执行 Nuclei。"""
import importlib.util
import io
import os
import shlex
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from test_mcp_default_contracts import mcp_request
from test_server_command_contracts import ROOT, load_function


class NucleiOfflineTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("nuclei_offline", ROOT / "docker/nuclei-compat.py")
        self.adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.adapter)

    def run_adapter(self, args, directory):
        environment = {"NUCLEI_TEMPLATES_DIR": directory}
        with patch.dict(os.environ, environment), patch.object(self.adapter.os, "execve") as execute:
            with patch.object(self.adapter.sys, "stderr", io.StringIO()) as errors:
                status = self.adapter.main(args)
            return status, execute, errors.getvalue()

    def test_default_mcp_uses_local_templates_and_disables_downloads(self):
        _, payload = mcp_request("nuclei_scan", target="https://example.test")
        function, namespace = load_function("nuclei", request=SimpleNamespace(json=payload))
        self.assertTrue(function()["success"])
        argv = shlex.split(namespace["execute_command_with_recovery"].call_args.args[1])
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "template.yaml").write_text("id: local-template\n")
            status, execute, _ = self.run_adapter(argv[1:], directory)
        self.assertEqual(status, 0)
        binary, native, environment = execute.call_args.args
        self.assertEqual(binary, "/usr/bin/nuclei")
        self.assertEqual(native[native.index("-t") + 1], directory)
        self.assertIn("-duc", native)
        self.assertIn("-ni", native)
        self.assertEqual(environment["NUCLEI_TEMPLATES_DIR"], directory)
        for provider in ("PUBLIC", "GITHUB", "GITLAB", "AWS", "AZURE"):
            self.assertEqual(environment[f"DISABLE_NUCLEI_TEMPLATES_{provider}_DOWNLOAD"], "true")

    def test_missing_and_empty_mount_fail_before_native_tool(self):
        with tempfile.TemporaryDirectory() as directory:
            for path in (directory, directory + "/missing"):
                status, execute, error = self.run_adapter(["-u", "https://example.test"], path)
                self.assertEqual(status, 2)
                execute.assert_not_called()
                self.assertIn("模板", error)

    def test_help_and_version_do_not_require_templates(self):
        for flag in ("-h", "--help", "-version"):
            status, execute, _ = self.run_adapter([flag], "/does-not-exist")
            self.assertEqual(status, 0)
            execute.assert_called_once()

    def test_explicit_local_templates_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "custom.yaml"
            template.write_text("id: custom\n")
            for option in (["-t", str(template)], [f"-templates={template}"]):
                status, execute, _ = self.run_adapter(["-u", "https://example.test", *option], directory)
                self.assertEqual(status, 0)
                self.assertTrue(all(arg in execute.call_args.args[1] for arg in option))
                self.assertNotIn(directory, execute.call_args.args[1])

    def test_relative_paths_and_local_globs_use_mounted_template_root(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "http").mkdir()
            (Path(directory) / "http/custom.yaml").write_text("id: custom\n")
            for value in ("http", "http/custom.yaml", "http/*.yaml"):
                status, execute, _ = self.run_adapter(["-u", "https://example.test", "-t", value], directory)
                self.assertEqual(status, 0)
                self.assertIn(value, execute.call_args.args[1])

    def test_native_exec_failure_is_not_reported_as_success(self):
        with patch.object(self.adapter.os, "execve", side_effect=OSError("missing binary")):
            with patch.object(self.adapter.sys, "stderr", io.StringIO()) as errors:
                self.assertEqual(self.adapter.main(["-version"]), 2)
            self.assertIn("missing binary", errors.getvalue())

    def test_documented_start_commands_leave_data_mounts_optional(self):
        import re
        docs = (ROOT / "docs/DOCKER_BUILD.md").read_text()
        blocks = re.findall(r"```bash\n(docker run[\s\S]*?)```", docs)
        self.assertEqual(len(blocks), 2)
        mount = "type=bind,source=/path/to/nuclei-templates,target=/opt/nuclei-templates,readonly"
        for block in blocks:
            self.assertNotIn("--mount", shlex.split(block.replace("\\\n", " ")))
        self.assertIn(mount, docs)
        self.assertIn("### 4.3 John/Hashcat 默认字典（可选）", docs)
        self.assertIn("### 4.4 Nuclei 离线模板（可选）", docs)
        self.assertNotIn("### 4.5", docs)

    def test_remote_templates_and_updates_are_not_silent_network_fallback(self):
        for args in (["-ut"], ["-update"], ["-t", "https://example.test/template.yaml"],
                     ["-t", "/missing.yaml"], ["-t"]):
            status, execute, error = self.run_adapter(args, "/missing")
            self.assertEqual(status, 2)
            execute.assert_not_called()
            self.assertTrue(error)

    def test_installer_and_build_include_adapter(self):
        self.assertIn("source=docker/nuclei-compat.py,target=/tmp/nuclei-compat.py",
                      (ROOT / "Dockerfile.base").read_text())
        self.assertIn("nuclei-compat.py", (ROOT / "docker/install-cli-compat.sh").read_text())
        self.assertIn("WPSCAN_VERSION=3.8.28", (ROOT / "docker/install-web.sh").read_text())


if __name__ == "__main__":
    unittest.main()
