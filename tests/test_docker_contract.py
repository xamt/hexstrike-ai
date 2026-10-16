"""镜像职责与现有工具版本的离线回归测试。"""
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "tests/fixtures/docker-tool-contract.json").read_text())
SECURITY = json.loads((ROOT / "tests/fixtures/security-tool-contract.json").read_text())
CONTAINER = json.loads((ROOT / "tests/fixtures/container-tool-contract.json").read_text())


class DockerContractTests(unittest.TestCase):
    """冻结批准的工具版本与命令，原接口兼容调整必须显式更新契约。"""

    def test_base_does_not_consume_application(self):
        base = (ROOT / "Dockerfile.base").read_text()
        for name in ("requirements.txt", "hexstrike_server.py", "hexstrike_mcp.py"):
            self.assertNotIn(name, base)
        self.assertNotIn("HEALTHCHECK", base)
        self.assertNotIn("EXPOSE", base)
        self.assertIn('CMD ["/bin/bash"]', base)
        self.assertNotIn("ARG BUILDPLATFORM", base.split("FROM ", 1)[0])

    def test_approved_versions_are_preserved(self):
        scripts = "\n".join(path.read_text() for path in (ROOT / "docker").glob("install-*.sh"))
        entries = re.findall(r"^\s*(\w+_VERSION(?:_AMD64|_ARM64)?)=([^\s]+)$", scripts, re.M)
        versions = dict(entries)
        self.assertEqual(len(entries), len(versions), "每个版本只能有一个定义")
        self.assertEqual(CONTRACT["versions"] | SECURITY["versions"] | CONTAINER["versions"], versions)

    def test_command_coverage_is_preserved(self):
        script = (ROOT / "docker/verify-base.sh").read_text()
        array = re.search(r"expected_commands=\(([\s\S]*?)\)", script)[1]
        expected = set(CONTRACT["commands"] + SECURITY["commands"] + CONTAINER["commands"])
        self.assertEqual(expected, set(array.split()))

    def test_all_locked_packages_are_installed_and_verified(self):
        scripts = "\n".join(path.read_text() for path in (ROOT / "docker").glob("install-*.sh"))
        verification = (ROOT / "docker/verify-tool-versions.py").read_text()
        arch_packages = {"masscan", "dirb", "ophcrack-cli", "foremost"}
        for package, version in CONTRACT["aptPackages"].items():
            with self.subTest(package=package):
                self.assertIn(package, verification)
                self.assertIn(f'record-tool-version.sh" apt {package} ', scripts)
                if package in arch_packages:
                    self.assertIn(f'"{package}=${{package_version}}"', scripts)
                    for arch in ("AMD64", "ARM64"):
                        self.assertIn(f"${{{version}_{arch}}}", scripts)
                else:
                    self.assertIn(f'"{package}=${{{version}}}"', scripts)

    def test_application_layers_and_isolation(self):
        app = (ROOT / "Dockerfile").read_text()
        self.assertIn("ARG BASE_IMAGE=harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.3.0-${TARGETARCH}", app)
        self.assertIn("FROM ${BASE_IMAGE}", app)
        self.assertEqual(1, len(re.findall(r"^FROM ", app, re.M)))
        self.assertNotIn("apt-get", app)
        self.assertNotIn("go install", app)
        self.assertLess(app.index("COPY requirements.txt"), app.index("COPY hexstrike_server.py"))
        self.assertIn("pwntools|angr|bcrypt", app)
        self.assertIn("/opt/hexstrike-venv/bin/python", app)
        base = (ROOT / "Dockerfile.base").read_text()
        self.assertIn("/opt/volatility3-venv", base)
        self.assertNotIn("/opt/hexstrike-venv", base)
        self.assertIn("ldconfig", (ROOT / "docker/finalize-base.sh").read_text())

    def test_image_repository_names_are_consistent(self):
        docs = (ROOT / "docs/DOCKER_BUILD.md").read_text()
        for arch in ("amd64", "arm64"):
            self.assertIn(f'--platform linux/{arch}', docs)
            self.assertIn(f'--tag harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.3.0-{arch}', docs)
            self.assertIn(f'--tag harbor.everoffice.cn/harbor-cucc/pentest-tools:1.3.0-{arch}', docs)
            self.assertIn(f'--build-arg BASE_IMAGE=harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.3.0-{arch}', docs)
        self.assertNotIn("${", docs)
        self.assertNotIn("imagetools", docs)
        self.assertNotRegex(docs, r'pentest-tools(?:-base)?:1\.3\.0(?!-)')
        for path in (ROOT / "Dockerfile", ROOT / "docs/DOCKER_BUILD.md",
                     ROOT / "tests/verify_docker_cache.py"):
            self.assertNotIn("penttest", path.read_text())

    def test_application_python_and_security_httpx_are_preserved(self):
        app = (ROOT / "Dockerfile").read_text()
        self.assertIn('PATH="/opt/hexstrike-venv/bin:/usr/local/bin:', app)
        self.assertIn('ln -sf /usr/local/bin/httpx /opt/hexstrike-venv/bin/httpx', app)
        self.assertLess(app.index('install -r requirements-runtime.txt'),
                        app.index('ln -sf /usr/local/bin/httpx'))

    def test_certificate_bootstrap_precedes_https(self):
        base = (ROOT / "Dockerfile.base").read_text()
        self.assertLess(base.index("COPY --from=python-source /etc/ssl/certs"),
                        base.index("bash /tmp/install-system.sh"))
        system = (ROOT / "docker/install-system.sh").read_text()
        self.assertIn('Acquire::https::CaInfo "/etc/ssl/certs/ca-certificates.crt"', system)
        for script in (ROOT / "docker").glob("install-*.sh"):
            content = script.read_text()
            self.assertNotIn("apt-get update", content)
            self.assertNotIn("Verify-Peer=false", content)

    def test_shell_syntax(self):
        scripts = list((ROOT / "docker").glob("*.sh"))
        self.assertGreater(len(scripts), 4)
        for script in scripts:
            with self.subTest(script=script.name):
                subprocess.run(["bash", "-n", str(script)], check=True)

    def test_build_context_excludes_private_files(self):
        ignored = (ROOT / ".dockerignore").read_text().splitlines()
        for pattern in (".git", ".helloagents", ".env", "*.xlsx", "__pycache__", ".venv"):
            self.assertIn(pattern, ignored)

    def test_large_transitive_wordlists_stay_out_of_layers(self):
        base = (ROOT / "Dockerfile.base").read_text()
        self.assertEqual(5, base.count("target=/usr/share/seclists,sharing=locked"))
        verification = (ROOT / "docker/verify-base.sh").read_text()
        self.assertIn("find /usr/share/seclists -mindepth 1", verification)


if __name__ == "__main__":
    unittest.main()
