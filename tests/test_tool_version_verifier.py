"""使用伪造查询结果验证最终版本检查，不访问真实容器或软件包管理器。"""
import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("tool_version_verifier", ROOT / "docker/verify-tool-versions.py")
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


def write_fixture(directory, arch="arm64"):
    """创建所有必需记录；测试版本不依赖真实安装环境。"""
    for kind, names in VERIFIER.REQUIRED.items():
        for name in names:
            digest, path = ("a" * 64, "/fixture/artifact") if kind in ("go", "rust", "source") else ("-", "-")
            record = VERIFIER.Record(kind, name, "fixed-version", arch, digest, path)
            (directory / f"{kind}-{name}.tsv").write_text("\t".join(record) + "\n")


class ToolVersionVerifierTests(unittest.TestCase):
    """缺项、版本漂移和架构错误都必须使校验失败。"""

    def test_required_apt_names_match_original_contract(self):
        fixture = json.loads((ROOT / "tests/fixtures/docker-tool-contract.json").read_text())
        database = json.loads((ROOT / "tests/fixtures/database-client-contract.json").read_text())
        security = json.loads((ROOT / "tests/fixtures/security-tool-contract.json").read_text())
        self.assertEqual(set(fixture["aptPackages"]) | set(database["aptPackages"]) | set(security["aptPackages"]),
                         set(VERIFIER.REQUIRED["apt"]))

    def test_complete_records_load_for_both_architectures(self):
        for arch in ("amd64", "arm64"):
            with self.subTest(arch=arch), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                write_fixture(root, arch)
                self.assertEqual(79, len(VERIFIER.load_records(root, arch)))

    def test_missing_record_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_fixture(root)
            (root / "apt-nmap.tsv").unlink()
            with self.assertRaisesRegex(ValueError, "缺少.*nmap"):
                VERIFIER.load_records(root, "arm64")

    def test_wrong_architecture_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_fixture(root, "amd64")
            with self.assertRaisesRegex(ValueError, "架构错误"):
                VERIFIER.load_records(root, "arm64")

    def test_malformed_record_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_fixture(root)
            (root / "apt-nmap.tsv").write_text("apt\tnmap\n")
            with self.assertRaisesRegex(ValueError, "格式错误"):
                VERIFIER.load_records(root, "arm64")

    def test_apt_requires_installed_state_exact_version_and_architecture(self):
        record = VERIFIER.Record("apt", "nmap", "locked", "arm64", "-", "-")
        for actual_arch in ("arm64", "all"):
            with patch.object(VERIFIER, "command_output", return_value=f"install ok installed\tlocked\t{actual_arch}"):
                self.assertEqual(("locked", actual_arch), VERIFIER.verify_record(record))
        for actual in ("deinstall ok config-files\tlocked\tarm64", "install ok installed\tchanged\tarm64",
                       "install ok installed\tlocked\tamd64"):
            with self.subTest(actual=actual), patch.object(VERIFIER, "command_output", return_value=actual):
                with self.assertRaises(ValueError):
                    VERIFIER.verify_record(record)

    def test_missing_apt_package_query_failure_propagates(self):
        record = VERIFIER.Record("apt", "nmap", "locked", "arm64", "-", "-")
        with patch.object(VERIFIER, "command_output", side_effect=subprocess.CalledProcessError(1, "dpkg-query")):
            with self.assertRaises(subprocess.CalledProcessError):
                VERIFIER.verify_record(record)

    def test_python_environments_are_queried_independently(self):
        for kind, executable in VERIFIER.PYTHON_EXECUTABLES.items():
            record = VERIFIER.Record(kind, "pip", "locked", "all", "-", "-")
            with patch.object(VERIFIER, "command_output", return_value="locked") as query:
                VERIFIER.verify_record(record)
                self.assertEqual(executable, query.call_args.args[0][0])
            with patch.object(VERIFIER, "command_output", return_value="changed"):
                with self.assertRaisesRegex(ValueError, "Python 包版本不符"):
                    VERIFIER.verify_record(record)

    def test_ruby_version_query_uses_recorded_version(self):
        record = VERIFIER.Record("gem", "wpscan", "locked", "all", "-", "-")
        with patch.object(VERIFIER, "command_output", return_value="true") as query:
            VERIFIER.verify_record(record)
            self.assertEqual(["gem", "list", "--local", "--exact", "wpscan", "--version", "locked", "--installed"],
                             query.call_args.args[0])

    def test_artifact_digest_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            artifact = Path(temporary) / "binary"
            artifact.write_bytes(b"original")
            record = VERIFIER.Record("go", "gau", "locked", "arm64",
                                     hashlib.sha256(b"original").hexdigest(), str(artifact))
            self.assertEqual(("locked", "arm64"), VERIFIER.verify_record(record))
            artifact.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "摘要不符"):
                VERIFIER.verify_record(record)

    def test_lock_is_written_only_after_all_checks_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "tool-versions.lock"
            record = VERIFIER.Record("apt", "nmap", "locked", "arm64", "-", "-")
            records = {("apt", "nmap"): record}
            with patch.object(VERIFIER, "verify_record", side_effect=ValueError("不符")):
                with self.assertRaises(ValueError):
                    VERIFIER.write_lock(records, output)
                self.assertFalse(output.exists())
            with patch.object(VERIFIER, "verify_record", return_value=("locked", "arm64")):
                VERIFIER.write_lock(records, output)
            self.assertEqual("# tool\tversion\tarchitecture\nnmap\tlocked\tarm64\n", output.read_text())


if __name__ == "__main__":
    unittest.main()
