"""只执行隔离的小字典复制和链接片段，不安装软件或访问网络。"""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORDS = ["Discovery/DNS/subdomains-top1million-110000.txt",
         "Usernames/top-usernames-shortlist.txt",
         "Discovery/SNMP/common-snmp-community-strings-onesixtyone.txt"]


def section(name, marker):
    """截取脚本末尾独立数据步骤，避免执行安装步骤。"""
    return (ROOT / "docker" / name).read_text().split(marker, 1)[1]


class AutoReconWordlistTests(unittest.TestCase):
    def test_exact_upstream_files_survive_cache_unmount_at_original_paths(self):
        copy_script = section("tools/network/apt.sh", "# AUTORECON_SMALL_DATA\n")
        link_script = section("assembly/prepare-tool-data.sh", "# AUTORECON_SMALL_DATA\n")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            cache, runtime, output = base / "cache", base / "runtime", base / "output"
            for index, relative in enumerate(WORDS):
                source = cache / relative
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text(f"真实字典替身 {index}\n")
            (cache / "large-unused.txt").write_text("不得带入镜像")
            copy_script = copy_script.replace("/usr/share/seclists", str(cache)).replace(
                "/opt/pentest-tools-compat/autorecon-data", str(output))
            subprocess.run(["bash", "-euo", "pipefail", "-c", copy_script], check=True)
            link_script = link_script.replace("/usr/share/seclists", str(runtime)).replace(
                "/opt/pentest-tools-compat/autorecon-data", str(output))
            subprocess.run(["bash", "-euo", "pipefail", "-c", link_script], check=True)
            self.assertEqual((output / "manifest.txt").read_text().splitlines(), WORDS)
            for index, relative in enumerate(WORDS):
                self.assertTrue((runtime / relative).is_symlink())
                self.assertEqual((runtime / relative).read_text(), f"真实字典替身 {index}\n")
            self.assertFalse((runtime / "large-unused.txt").exists())
            self.assertFalse((output / "large-unused.txt").exists())
            verification = (ROOT / "docker/verify/base.sh").read_text().split("<<'PY'\n", 1)[1].split("\nPY", 1)[0]
            verification = verification.replace("/usr/share/seclists", str(runtime)).replace(
                "/opt/pentest-tools-compat/autorecon-data", str(output))
            exec(verification, {})
            (runtime / "unexpected.txt").write_text("不应固化的其他数据")
            with self.assertRaises(AssertionError):
                exec(verification, {})

    def test_missing_dictionary_fails_instead_of_reducing_coverage(self):
        script = section("tools/network/apt.sh", "# AUTORECON_SMALL_DATA\n")
        with tempfile.TemporaryDirectory() as directory:
            script = script.replace("/usr/share/seclists", directory + "/missing").replace(
                "/opt/pentest-tools-compat/autorecon-data", directory + "/output")
            result = subprocess.run(["bash", "-euo", "pipefail", "-c", script], capture_output=True)
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
