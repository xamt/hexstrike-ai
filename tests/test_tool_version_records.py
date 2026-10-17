"""在临时目录验证安装记录，不安装软件、不调用 Docker。"""
import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDER = ROOT / "docker/lib/record-tool-version.sh"


class ToolVersionRecordTests(unittest.TestCase):
    """预期值来自安装脚本，失败和冲突不能伪造成功记录。"""

    def record(self, directory, *arguments):
        """将测试记录写到临时目录，返回命令结果。"""
        return subprocess.run(["bash", str(RECORDER), *arguments], capture_output=True,
                              text=True, env=dict(os.environ, TOOL_RECORD_DIR=str(directory)))

    def test_expected_version_is_preserved_and_conflict_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            arguments = ("apt", "nmap", "7.991+dfsg-1kali1", "arm64")
            self.assertEqual(0, self.record(root, *arguments).returncode)
            first = (root / "apt-nmap.tsv").read_text()
            self.assertEqual("apt\tnmap\t7.991+dfsg-1kali1\tarm64\t-\t-\n", first)
            self.assertEqual(0, self.record(root, *arguments).returncode)
            self.assertNotEqual(0, self.record(root, "apt", "nmap", "other", "arm64").returncode)
            self.assertEqual(first, (root / "apt-nmap.tsv").read_text())
            self.assertEqual([], list(root.glob(".record.*")))

    def test_compiled_artifact_digest_is_recorded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / "gau"
            binary.write_bytes(b"binary fixture")
            result = self.record(root, "go", "gau", "v2.2.4", "arm64", str(binary), "/usr/local/bin/gau")
            self.assertEqual(0, result.returncode, result.stderr)
            fields = (root / "go-gau.tsv").read_text().strip().split("\t")
            self.assertEqual(hashlib.sha256(binary.read_bytes()).hexdigest(), fields[4])
            self.assertEqual("/usr/local/bin/gau", fields[5])

    def test_missing_artifact_does_not_create_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.record(root, "go", "gau", "v2.2.4", "arm64", str(root / "missing"), "/usr/local/bin/gau")
            self.assertNotEqual(0, result.returncode)
            self.assertFalse((root / "go-gau.tsv").exists())

    def test_network_install_records_both_architectures(self):
        for arch, version in (("amd64", "2:1.3.2+ds1-2"), ("arm64", "2:1.3.2+ds1-2+b1")):
            with self.subTest(arch=arch), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                apt = root / "apt-get"
                apt.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$TEST_LOG"\n')
                apt.chmod(0o755)
                log, records = root / "calls", root / "records"
                env = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}", TARGETARCH=arch,
                           TOOL_RECORD_DIR=str(records), TEST_LOG=str(log), NMAP_VERSION="unexpected")
                from test_autorecon_wordlists import WORDS
                for relative in WORDS:
                    source = root / "seclists" / relative
                    source.parent.mkdir(parents=True, exist_ok=True)
                    source.write_text("字典替身\n")
                script = (ROOT / "docker/tools/network/apt.sh").read_text().replace(
                    "/usr/share/seclists", str(root / "seclists")).replace(
                    "/opt/pentest-tools-compat/autorecon-data", str(root / "data"))
                installer = root / "install-network.sh"
                installer.write_text(script.replace('${script_dir}/../../lib/record-tool-version.sh', str(RECORDER)))
                shutil.copyfile(RECORDER, root / RECORDER.name)
                result = subprocess.run(["bash", str(installer)],
                                        env=env, text=True, capture_output=True)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(8, len(list(records.glob("*.tsv"))))
                self.assertIn(f"masscan={version}", log.read_text())
                self.assertIn(f"\tmasscan\t{version}\t{arch}\t", (records / "apt-masscan.tsv").read_text())
                self.assertIn("nmap=7.991+dfsg-1kali1", log.read_text())


if __name__ == "__main__":
    unittest.main()
