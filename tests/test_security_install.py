"""五类安全工具安装契约；只模拟包管理器，不安装或执行真实工具。"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "tests/fixtures/security-tool-contract.json").read_text())
CATEGORIES = ("network", "web", "osint")


def sandbox_category(root, category):
    """保留类别安装流程，仅重定向固定写入路径并替换系统命令。"""
    from test_autorecon_wordlists import WORDS
    script = (ROOT / f"docker/tools/{category}/apt.sh").read_text()
    script = script.replace("${script_dir}/../../lib/record-tool-version.sh",
                            str(ROOT / "docker/lib/record-tool-version.sh"))
    script = script.replace("/usr/share/seclists", str(root / "seclists"))
    script = script.replace("/opt/hexstrike-compat/autorecon-data", str(root / "data"))
    for relative in WORDS:
        source = root / "seclists" / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("测试字典\n")
    installer = root / f"{category}.sh"
    installer.write_text(script)
    link = root / "ln"
    link.write_text('#!/bin/sh\nexit 0\n')
    link.chmod(0o755)
    return installer


class SecurityInstallTests(unittest.TestCase):
    """验证精确版本、失败停止和独立 Python 环境。"""

    def test_apt_records_exact_versions_on_both_architectures(self):
        for arch in ("amd64", "arm64"):
            with self.subTest(arch=arch), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                apt = root / "apt-get"
                apt.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$TEST_LOG"\n')
                apt.chmod(0o755)
                env = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}", TARGETARCH=arch,
                           TEST_LOG=str(root / "calls"), TOOL_RECORD_DIR=str(root / "records"))
                for category in CATEGORIES:
                    result = subprocess.run(["bash", str(sandbox_category(root, category))],
                                            env=env, capture_output=True, text=True)
                    self.assertEqual(0, result.returncode, result.stderr)
                for package, variable in CONTRACT["aptPackages"].items():
                    self.assertIn(f"{package}={CONTRACT['versions'][variable]}",
                                  (root / "calls").read_text())
                    fields = (root / "records" / f"apt-{package}.tsv").read_text().split("\t")
                    self.assertEqual(fields[:4], ["apt", package, CONTRACT["versions"][variable], arch])

    def test_apt_failure_and_invalid_arch_never_record_success(self):
        for arch, code in (("arm64", 37), ("s390x", 1)):
            with self.subTest(arch=arch), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                apt = root / "apt-get"
                apt.write_text('#!/bin/sh\nexit 37\n')
                apt.chmod(0o755)
                env = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}", TARGETARCH=arch,
                           TOOL_RECORD_DIR=str(root / "records"))
                for category in CATEGORIES:
                    result = subprocess.run(["bash", str(ROOT / f"docker/tools/{category}/apt.sh")],
                                            env=env, capture_output=True, text=True)
                    self.assertEqual(code, result.returncode, result.stderr)
                self.assertFalse((root / "records").exists())

    def test_jwt_is_pinned_isolated_and_checked(self):
        script = (ROOT / "docker/tools/authentication/python.sh").read_text()
        base = (ROOT / "Dockerfile.base").read_text()
        self.assertIn("JWT_TOOL_VERSION=2.3.0", script)
        self.assertIn("0f8c32aa9f67cea4312e5df81d48f72dc5daf57f3cc0ce09d67db78e23fbe451", script)
        self.assertLess(script.index("sha256sum -c"), script.index("tar -xzf"))
        self.assertIn("/opt/jwt-tool-venv", script)
        self.assertNotIn("/opt/hexstrike-venv", script)
        self.assertIn("source jwt_tool", script)
        self.assertIn("cd /opt/jwt-tool", script)
        self.assertIn("COPY --from=python-runtime /opt/jwt-tool-venv/", base)
        self.assertIn("COPY --from=python-runtime /opt/jwt-tool/", base)
        self.assertNotIn("security_tools/", base)

    def test_smoke_checks_only_use_help_or_version(self):
        script = (ROOT / "docker/verify/base.sh").read_text()
        for command in ("testssl", "whatweb", "trufflehog", "tcpdump"):
            self.assertIn(f"timeout 30 {command} --version", script)
        self.assertIn("timeout 30 jwt_tool -h", script)
        self.assertIn("/opt/jwt-tool-venv/bin/python -m pip check", script)

    def test_jwt_download_and_digest_failure_stop_before_install(self):
        for failure, expected in (("download", 22), ("digest", 43)):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                python = root / "python3.11"
                python.write_text('#!/bin/sh\nif [ "$FAILURE" = download ]; then exit 22; fi\n'
                                  'printf fixture > "$3"\n')
                python.chmod(0o755)
                digest = root / "sha256sum"
                digest.write_text('#!/bin/sh\ncat >/dev/null\nexit 43\n')
                digest.chmod(0o755)
                mkdir = root / "mkdir"
                mkdir.write_text('#!/bin/sh\necho unexpected > "$TEST_LOG"\nexit 99\n')
                mkdir.chmod(0o755)
                env = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}", FAILURE=failure,
                           TEST_LOG=str(root / "calls"), PIP_INDEX_URL="https://example.invalid/simple")
                result = subprocess.run(["bash", str(ROOT / "docker/tools/authentication/python.sh")],
                                        env=env, capture_output=True, text=True)
                self.assertEqual(expected, result.returncode, result.stderr)
                self.assertFalse((root / "calls").exists())

    def test_application_has_no_new_database_or_security_api(self):
        app = (ROOT / "Dockerfile").read_text()
        server = (ROOT / "server.py").read_text()
        script = (ROOT / "tests/verify_docker_cache.py").read_text()
        self.assertFalse((ROOT / "database_tools").exists())
        self.assertIn('"jwt-tool": "python3 /opt/jwt_tool/jwt_tool.py"', server)
        self.assertIn("/opt/jwt_tool/jwt_tool.py", (ROOT / "docker/compat/install.sh").read_text())
        self.assertIn('@app.route("/api/tools/jwt_analyzer", methods=["POST"])', server)
        self.assertFalse((ROOT / "security_tools").exists())
        for content in (app, server, script):
            self.assertNotIn("database_tools", content)
            self.assertNotIn("register_database_routes", content)
            self.assertNotIn("security_tools/", content)
            self.assertNotIn("register_security_routes", content)
        self.assertIn("/opt/jwt-tool-venv/bin/python -m pip check", script)


if __name__ == "__main__":
    unittest.main()
