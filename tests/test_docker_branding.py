"""镜像命名与旧部署配置兼容契约，不调用外部扫描器。"""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "docker"))


class DockerBrandingTests(unittest.TestCase):
    def test_image_checks_follow_split_python_environments(self):
        for relative in ("docker/verify/test-images.sh", "tests/verify_docker_cache.py"):
            source = (ROOT / relative).read_text()
            self.assertNotIn("python3 -c 'import requests, httpx'", source)
            self.assertNotIn('python3 -c "import requests, httpx"', source)
            self.assertIn("/opt/pentest-tools-mcp-venv/bin/python -c", source)

    def test_build_chain_has_no_legacy_brand(self):
        files = [ROOT / "Dockerfile", ROOT / "Dockerfile.base", ROOT / "requirements.txt"]
        files += [path for path in (ROOT / "docker").rglob("*")
                  if path.suffix in {".py", ".sh", ".java"}]
        for path in files:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertNotIn("hexstrike", path.name.lower())
                self.assertFalse("hexstrike" in path.read_text().lower(), str(path))

    def test_shipped_sources_only_keep_explicit_environment_compatibility(self):
        files = [ROOT / "server.py", ROOT / "mcp_server.py"]
        files += list((ROOT / "runtime").glob("*.py")) + list((ROOT / "tools").glob("*.py"))
        for path in files:
            if path.name == "environment.py":
                continue
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertFalse("hexstrike" in path.read_text().lower(), str(path))
                self.assertFalse("pentest-agent-tools" in path.read_text(), str(path))

    def test_environment_preserves_legacy_and_prefers_explicit_new_values(self):
        from runtime.environment import setting
        self.assertEqual(setting("PORT", "8888", {}), "8888")
        self.assertEqual(setting("PORT", "8888", {"HEXSTRIKE_PORT": "9000"}), "9000")
        self.assertEqual(setting("PORT", "8888", {
            "HEXSTRIKE_PORT": "9000", "PENTEST_TOOLS_PORT": "9001",
        }), "9001")

    def test_service_and_mcp_read_legacy_configuration(self):
        from service_health import load_configuration
        from runtime.cli import parse_args
        config = load_configuration({"HEXSTRIKE_PORT": "9100", "HEXSTRIKE_MCP_PORT": "9101"})
        self.assertEqual((config.api_port, config.mcp_port), (9100, 9101))
        self.assertEqual(config.api_python, "/opt/pentest-tools-venv/bin/python")
        self.assertEqual(config.mcp_python, "/opt/pentest-tools-mcp-venv/bin/python")
        with patch.dict(os.environ, {"HEXSTRIKE_MCP_TIMEOUT": "71",
                                     "PENTEST_TOOLS_MCP_MAX_CONCURRENT": "3"}, clear=True):
            args = parse_args([])
        self.assertEqual((args.timeout, args.max_concurrent), (71, 3))

    def test_image_defaults_do_not_mask_existing_environment_overrides(self):
        dockerfile = (ROOT / "Dockerfile").read_text()
        self.assertNotIn("PENTEST_TOOLS_PORT=", dockerfile)
        self.assertNotIn("PENTEST_TOOLS_HOST=", dockerfile)
        from service_health import load_configuration
        from service_manager import service_commands
        with patch.dict(os.environ, {}, clear=True):
            api, _ = service_commands(load_configuration({}))
        self.assertEqual(api[api.index("--host") + 1], "0.0.0.0")
        with patch.dict(os.environ, {"HEXSTRIKE_HOST": "127.0.0.1"}, clear=True):
            api, _ = service_commands(load_configuration({}))
        self.assertEqual(api[api.index("--host") + 1], "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
