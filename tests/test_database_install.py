"""数据库客户端构建契约与失败停止测试；不下载软件，不调用 Docker。"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "tests/fixtures/database-client-contract.json").read_text())


def fake_command(directory, name, body):
    """在临时 PATH 中创建显式模拟命令。"""
    path = directory / name
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(0o755)


class DatabaseInstallTests(unittest.TestCase):
    """新客户端必须固定版本，双架构等价，下载失败不能生成成功记录。"""

    def test_apt_clients_record_exact_versions_for_both_architectures(self):
        for arch in ("amd64", "arm64"):
            with self.subTest(arch=arch), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                fake_command(root, "apt-get", 'printf "%s\\n" "$*" >> "$TEST_LOG"\n')
                env = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}", TARGETARCH=arch,
                           TEST_LOG=str(root / "calls"), TOOL_RECORD_DIR=str(root / "records"))
                result = subprocess.run(["bash", str(ROOT / "docker/install-database-apt.sh")],
                                        env=env, capture_output=True, text=True)
                self.assertEqual(0, result.returncode, result.stderr)
                records = list((root / "records").glob("*.tsv"))
                self.assertEqual(5, len(records))
                calls = (root / "calls").read_text()
                for package in ("mariadb-client", "mariadb-client-core", "mariadb-client-compat"):
                    self.assertIn(f"{package}={CONTRACT['versions']['MARIADB_CLIENT_VERSION']}", calls)
                self.assertIn("redis-tools=5:8.0.6-3", calls)
                self.assertIn("postgresql-client-18=18.6-3", calls)
                self.assertNotIn("--allow-unauthenticated", calls)
                self.assertNotIn("server=", calls)
                self.assertTrue(all(f"\t{arch}\t" in record.read_text() for record in records))

    def test_failed_apt_install_creates_no_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake_command(root, "apt-get", 'case "$*" in *install*) exit 37;; esac\n')
            env = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}", TARGETARCH="arm64",
                       TOOL_RECORD_DIR=str(root / "records"))
            result = subprocess.run(["bash", str(ROOT / "docker/install-database-apt.sh")], env=env)
            self.assertEqual(37, result.returncode)
            self.assertFalse((root / "records").exists())

    def test_unsupported_architecture_fails_before_install_or_download(self):
        for name in ("apt", "clickhouse", "mongodb"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                for command in ("apt-get", "curl"):
                    fake_command(root, command, 'echo unexpected > "$TEST_LOG"; exit 99\n')
                env = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}", TARGETARCH="s390x",
                           TEST_LOG=str(root / "calls"))
                result = subprocess.run(["bash", str(ROOT / f"docker/install-database-{name}.sh")],
                                        env=env, capture_output=True, text=True)
                self.assertEqual(1, result.returncode)
                self.assertFalse((root / "calls").exists())

    def test_download_failure_never_installs_or_records(self):
        for name in ("clickhouse", "mongodb"):
            for arch in ("amd64", "arm64"):
                with self.subTest(name=name, arch=arch), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    fake_command(root, "curl", 'exit 22\n')
                    fake_command(root, "apt-get", 'echo unexpected > "$TEST_LOG"; exit 99\n')
                    env = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}", TARGETARCH=arch,
                               TEST_LOG=str(root / "calls"), TOOL_RECORD_DIR=str(root / "records"))
                    result = subprocess.run(["bash", str(ROOT / f"docker/install-database-{name}.sh")],
                                            env=env, capture_output=True, text=True)
                    self.assertEqual(22, result.returncode, result.stderr)
                    self.assertFalse((root / "calls").exists())
                    self.assertFalse((root / "records").exists())

    def test_download_uses_http1_and_bounded_retry_and_propagates_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake_command(root, "curl", 'printf "%s\\n" "$@" > "$TEST_LOG"; exit 92\n')
            fake_command(root, "sha256sum", 'echo unexpected > "$VERIFY_LOG"; exit 99\n')
            env = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}", TARGETARCH="arm64",
                       TEST_LOG=str(root / "calls"), VERIFY_LOG=str(root / "verified"))
            result = subprocess.run([
                "bash", "-c", 'source "$1"; download_database_deb https://example.invalid/client.deb digest client 1.0 "$2"',
                "test", str(ROOT / "docker/install-database-deb.sh"), str(root / "client.deb"),
            ], env=env, capture_output=True, text=True)
            self.assertEqual(92, result.returncode, result.stderr)
            self.assertFalse((root / "verified").exists())
            args = (root / "calls").read_text().splitlines()
            for flag in ("--http1.1", "--retry-all-errors", "--fail", "--show-error"):
                self.assertIn(flag, args)
            for flag, value in (("--retry", "5"), ("--retry-delay", "3"),
                                ("--proto", "=https"), ("--proto-redir", "=https")):
                self.assertIn(flag, args)
                self.assertEqual(value, args[args.index(flag) + 1])
            self.assertNotIn("--insecure", args)
            self.assertEqual(str(root / "client.deb"), args[args.index("--output") + 1])

    def test_download_verifies_digest_and_package_metadata(self):
        for failure in (None, "digest", "Package", "Version", "Architecture", "download"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                checksum = root / "sha256sum"
                checksum.write_text(f"#!{sys.executable}\n"
                                    "import hashlib, pathlib, sys\n"
                                    "digest, path = sys.stdin.read().strip().split('  ', 1)\n"
                                    "sys.exit(hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest() != digest)\n")
                checksum.chmod(0o755)
                fake_command(root, "curl", 'if [ "$FAILURE" = download ]; then exit 22; fi\n'
                             'while [ "$1" != --output ]; do shift; done\n'
                             'printf fixture > "$2"\n')
                fake_command(root, "dpkg-deb", 'if [ "$FAILURE" = "$3" ]; then echo wrong; exit; fi\n'
                             'case "$3" in Package) echo client;; Version) echo 1.0;; '
                             'Architecture) echo arm64;; esac\n')
                digest = hashlib.sha256(b"fixture").hexdigest() if failure != "digest" else "0" * 64
                env = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}", TARGETARCH="arm64",
                           FAILURE=failure or "")
                result = subprocess.run([
                    "bash", "-c", 'source "$1"; download_database_deb https://example.invalid/client.deb "$2" client 1.0 "$3"',
                    "test", str(ROOT / "docker/install-database-deb.sh"), digest, str(root / "client.deb"),
                ], env=env, capture_output=True, text=True)
                self.assertEqual(failure is None, result.returncode == 0, result.stderr)

    def test_database_layers_and_smoke_checks_are_present(self):
        base = (ROOT / "Dockerfile.base").read_text()
        verifier = (ROOT / "docker/verify-base.sh").read_text()
        for name in ("apt", "clickhouse", "mongodb"):
            self.assertIn(f"bash /tmp/install-database-{name}.sh", base)
        for command in CONTRACT["commands"]:
            self.assertIn(f"timeout 30 {command} --version", verifier)
        for name in ("clickhouse", "mongodb"):
            script = (ROOT / f"docker/install-database-{name}.sh").read_text()
            self.assertIn("download_database_deb", script)
            self.assertNotIn("trusted=yes", script)
            self.assertNotIn("--allow-unauthenticated", script)


if __name__ == "__main__":
    unittest.main()
