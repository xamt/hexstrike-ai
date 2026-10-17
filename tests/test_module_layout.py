"""产品模块命名与镜像上下文导入契约，不启动服务或扫描器。"""
from pathlib import Path
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ModuleLayoutTests(unittest.TestCase):
    def test_product_modules_replace_legacy_sources(self):
        for name in ("tools", "runtime"):
            self.assertTrue((ROOT / name / "__init__.py").is_file())
            self.assertFalse((ROOT / ("hexstrike_" + name) / "__init__.py").exists())
        self.assertTrue((ROOT / "server.py").is_file())
        self.assertFalse((ROOT / ("hexstrike_" + "server.py")).exists())

    def test_docker_packages_all_product_modules(self):
        dockerfile = (ROOT / "Dockerfile").read_text()
        self.assertIn("COPY server.py mcp_server.py ./", dockerfile)
        for name in ("tools", "runtime"):
            self.assertIn(f"COPY {name}/ ./{name}/", dockerfile)
        self.assertIn("-m py_compile server.py", dockerfile)

    def test_mcp_entrypoint_does_not_shadow_sdk_or_keep_old_launcher(self):
        self.assertTrue((ROOT / "mcp_server.py").is_file())
        self.assertFalse((ROOT / "mcp.py").exists())
        self.assertFalse((ROOT / ("hexstrike_" + "mcp.py")).exists())
        self.assertFalse((ROOT / ("hexstrike-" + "ai-mcp.json")).exists())

    def test_packaged_modules_import_without_original_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            for name in ("tools", "runtime"):
                shutil.copytree(ROOT / name, destination / name,
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            code = (
                "from pathlib import Path; import tools, runtime; "
                "from runtime.cli import parse_args; "
                "from runtime.nmap_options import validate_scan_type; "
                "assert Path(tools.__file__).parent == Path.cwd() / 'tools'; "
                "assert Path(runtime.__file__).parent == Path.cwd() / 'runtime'; "
                "assert callable(tools.register_tools); "
                "assert parse_args([]).port == 8889; "
                "assert not hasattr(parse_args([]), 'transport')"
            )
            result = subprocess.run([sys.executable, "-B", "-c", code],
                                    cwd=destination, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_cache_verifier_copies_complete_application_context(self):
        spec = importlib.util.spec_from_file_location("cache_verifier", ROOT / "tests/verify_docker_cache.py")
        verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier)
        with tempfile.TemporaryDirectory() as directory:
            context = Path(directory)
            verifier.prepare_context(context)
            for name in ("server.py", "mcp_server.py", "requirements.txt", "requirements-mcp.txt",
                         "tools/__init__.py", "runtime/server.py", "docker/service_manager.py",
                         "docker/service_health.py"):
                self.assertTrue((context / name).is_file(), name)
            self.assertFalse(list(context.rglob("__pycache__")))


if __name__ == "__main__":
    unittest.main()
