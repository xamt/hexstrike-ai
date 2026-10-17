"""验证构建目录职责及显式挂载；不运行 Docker 或真实安装器。"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = {"network", "web", "authentication", "binary", "container", "forensics", "osint"}


class DockerStructureTests(unittest.TestCase):
    def test_only_documentation_at_docker_root(self):
        self.assertEqual(["README.md"], sorted(p.name for p in (ROOT / "docker").iterdir()
                                             if p.is_file()))

    def test_seven_categories_have_installation_method_scripts(self):
        tools = ROOT / "docker/tools"
        self.assertTrue(tools.is_dir())
        self.assertEqual(CATEGORIES, {p.name for p in tools.iterdir() if p.is_dir()})
        allowed = {"apt.sh", "go.sh", "rust.sh", "ruby.sh", "source.sh", "release.sh",
                   "python.sh", "python2.sh", "python3.sh"}
        for directory in tools.iterdir():
            scripts = list(directory.glob("*.sh"))
            self.assertTrue(scripts, directory)
            self.assertTrue({p.name for p in scripts} <= allowed, directory)

    def test_every_bound_source_exists_and_preserves_directory_layout(self):
        base = (ROOT / "Dockerfile.base").read_text().replace("\\\n", " ")
        for source, target in re.findall(r"type=bind,source=([^, ]+),target=([^, ]+)", base):
            self.assertTrue((ROOT / source).exists(), source)
            self.assertEqual("/tmp/" + source, target)
        for run in re.findall(r"^RUN (.+)$", base, re.M):
            command = re.search(r"bash (/tmp/docker/[\w./-]+\.sh)", run)
            self.assertIsNotNone(command, run)
            self.assertIn("target=" + command[1], run)
            self.assertNotIn("source=docker,target=", run)

    def test_dependencies_are_bound_per_installation_layer(self):
        base = (ROOT / "Dockerfile.base").read_text().replace("\\\n", " ")
        for run in re.findall(r"^RUN (.+)$", base, re.M):
            bound = dict(re.findall(r"source=(docker/[^, ]+),target=([^, ]+)", run))
            for source in bound:
                path = ROOT / source
                if not path.is_file() or path.suffix != ".sh":
                    continue
                for relative in re.findall(r'\$\{script_dir\}/([\w./-]+\.(?:sh|py))', path.read_text()):
                    dependency = (path.parent / relative).resolve().relative_to(ROOT)
                    self.assertTrue(any(dependency == Path(item) or
                                        (ROOT / item).is_dir() and Path(item) in dependency.parents
                                        for item in bound), (source, dependency))

    def test_apt_tools_have_one_category_and_no_duplicate_package_install(self):
        expected = {
            "network": "nmap masscan rustscan fierce dnsenum autorecon enum4linux-ng tcpdump",
            "web": "gobuster feroxbuster dirsearch ffuf dirb httpx-toolkit katana hakrawler "
                   "sqlmap arjun wafw00f qsreplace uro wfuzz nuclei whatweb testssl.sh",
            "authentication": "responder netexec hydra john hashcat medusa patator crackmapexec "
                              "evil-winrm hash-identifier ophcrack-cli",
            "binary": "gdb radare2 binwalk ghidra checksec binutils xxd",
            "forensics": "foremost steghide libimage-exiftool-perl",
            "osint": "amass subfinder theharvester trufflehog",
            "container": "docker-cli kubectl kubernetes-helm",
        }
        installed = set()
        for category, packages in expected.items():
            script = (ROOT / f"docker/tools/{category}/apt.sh").read_text()
            records = re.findall(r'record-tool-version.sh" apt ([\w.-]+) ', script)
            self.assertCountEqual(packages.split(), records, category)
            self.assertFalse(installed.intersection(records), category)
            installed.update(records)

    def test_shared_build_helper_has_no_tool_versions(self):
        helper = (ROOT / "docker/lib/build-go-tool.sh").read_text()
        self.assertNotRegex(helper, r"[A-Z_]+_VERSION=")
        self.assertNotIn("github.com/", helper)


if __name__ == "__main__":
    unittest.main()
