"""Offline container client packaging checks; package managers are always mocked."""

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "docker/tools/container/apt.sh"
RELEASE = ROOT / "docker/tools/container/release.sh"
PYTHON = ROOT / "docker/tools/container/python.sh"


def container_scripts():
    """读取同一类别的三种安装方式，版本仍由各脚本独立定义。"""
    return "\n".join(path.read_text() for path in (SCRIPT, RELEASE, PYTHON))


CONTRACT = json.loads((ROOT / "tests/fixtures/container-tool-contract.json").read_text())


class ContainerInstallTests(unittest.TestCase):
    def test_prioritized_kubernetes_tools_without_optional_scanners(self):
        self.assertEqual(set(CONTRACT["commands"]),
                         {"docker", "kubectl", "helm", "kube-bench", "kube-hunter"})
        script = container_scripts()
        for package in ("trivy", "clair", "awscli", "azure-cli"):
            self.assertNotRegex(script, rf'"{package}=')

    def test_exact_cli_only_packages_for_each_architecture(self):
        for architecture in ("amd64", "arm64"):
            with self.subTest(architecture=architecture), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                executable = root / "apt-get"
                executable.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$TEST_LOG"\n')
                executable.chmod(0o755)
                environment = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}",
                                   TARGETARCH=architecture, TEST_LOG=str(root / "calls"),
                                   TOOL_RECORD_DIR=str(root / "records"))
                result = subprocess.run(["bash", str(SCRIPT)], env=environment,
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                calls = (root / "calls").read_text().splitlines()
                self.assertEqual(calls[0], "-o APT::Update::Error-Mode=any update")
                self.assertEqual(len(calls), 2)
                arguments = calls[1].split()
                self.assertEqual(arguments[:3], ["install", "-y", "--no-install-recommends"])
                expected = [f"{package}={CONTRACT['versions'][variable]}"
                            for package, variable in CONTRACT["aptPackages"].items()]
                self.assertEqual(arguments[3:], expected)
                self.assertEqual(len(list((root / "records").glob("*.tsv"))), 3)
                for package, variable in CONTRACT["aptPackages"].items():
                    fields = (root / "records" / f"apt-{package}.tsv").read_text().strip().split("\t")
                    self.assertEqual(fields[:4], ["apt", package, CONTRACT["versions"][variable], architecture])

    def test_update_or_install_failure_cannot_record_success(self):
        for phase in ("update", "install"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                executable = root / "apt-get"
                executable.write_text('#!/bin/sh\ncase "$*" in *"$FAIL_PHASE"*) exit 37;; esac\n')
                executable.chmod(0o755)
                environment = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}",
                                   TARGETARCH="arm64", FAIL_PHASE=phase,
                                   TOOL_RECORD_DIR=str(root / "records"))
                result = subprocess.run(["bash", str(SCRIPT)], env=environment,
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 37, result.stderr)
                self.assertFalse((root / "records").exists())

    def test_unsupported_architecture_fails_before_apt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "apt-get"
            executable.write_text('#!/bin/sh\nprintf called > "$TEST_LOG"\nexit 99\n')
            executable.chmod(0o755)
            environment = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}",
                               TARGETARCH="s390x", TEST_LOG=str(root / "calls"))
            result = subprocess.run(["bash", str(SCRIPT)], env=environment,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertFalse((root / "calls").exists())

    def test_versions_are_local_and_no_runtime_downloads(self):
        script = container_scripts()
        variables = dict(re.findall(r"^([A-Z][A-Z0-9_]*_VERSION)=(\S+)$", script, re.M))
        self.assertEqual(variables, CONTRACT["versions"])
        for forbidden in ("--download-db-only", "--download-java-db-only", "systemctl "):
            self.assertNotIn(forbidden, script)
        subprocess.run(["bash", "-n", str(SCRIPT)], check=True)

    def test_bench_download_or_digest_failure_stops_before_extracting(self):
        for phase, expected in (("download", 22), ("digest", 43)):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                curl = root / "curl"
                curl.write_text('#!/bin/sh\nif [ "$FAIL_PHASE" = download ]; then exit 22; fi\n'
                                'while [ "$1" != --output ]; do shift; done\nprintf fixture > "$2"\n')
                curl.chmod(0o755)
                digest = root / "sha256sum"
                digest.write_text('#!/bin/sh\ncat > "$DIGEST_INPUT"\nexit 43\n')
                digest.chmod(0o755)
                extract = root / "tar"
                extract.write_text('#!/bin/sh\nprintf unexpected > "$TEST_LOG"\nexit 99\n')
                extract.chmod(0o755)
                env = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}", TARGETARCH="arm64",
                           FAIL_PHASE=phase, DIGEST_INPUT=str(root / "digest"), TEST_LOG=str(root / "calls"))
                result = subprocess.run(["bash", str(RELEASE)], env=env,
                                        capture_output=True, text=True)
                self.assertEqual(expected, result.returncode, result.stderr)
                self.assertFalse((root / "calls").exists())
                if phase == "digest":
                    self.assertIn(CONTRACT["benchArchives"]["arm64"]["sha256"], (root / "digest").read_text())

    def test_bench_configuration_has_individual_file_digests(self):
        script = RELEASE.read_text()
        for architecture in ("amd64", "arm64"):
            self.assertIn(CONTRACT["benchArchives"][architecture]["sha256"], script)
        self.assertLess(script.index("sha256sum -c -"), script.index("tar -xzf"))
        self.assertIn("--proto '=https' --proto-redir '=https'", script)
        self.assertIn("/etc/kube-bench/cfg", script)
        self.assertIn("/opt/kube-bench/cfg.sha256", script)
        self.assertIn("source kube-bench-config", script)
        self.assertIn('find "/etc/kube-bench/cfg" -type f -print0', script)

    def test_invalid_mode_never_installs(self):
        result = subprocess.run(["bash", str(SCRIPT), "invalid"],
                                env=dict(os.environ, TARGETARCH="amd64"), capture_output=True, text=True)
        self.assertEqual(2, result.returncode)


class HunterInstallTests(unittest.TestCase):
    @staticmethod
    def prepare_sandbox(root):
        """Redirect only filesystem destinations and substitute apt/Python processes."""
        script = root / "install-container-tools.sh"
        script.write_text(PYTHON.read_text().replace("/opt/", str(root / "opt") + "/").replace(
            "${script_dir}/../../lib/record-tool-version.sh", str(root / "record-tool-version.sh")))
        (root / "record-tool-version.sh").write_text(
            '#!/bin/sh\nmkdir -p "$TOOL_RECORD_DIR"\nprintf "%s\\n" "$*" >> "$TOOL_RECORD_DIR/records"\n'
        )
        apt = root / "apt-get"
        apt.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$APT_LOG"\n')
        apt.chmod(0o755)
        python = root / "python3.11"
        python.write_text(
            '#!/usr/bin/env python3\nimport os,pathlib,sys\n'
            'destination=pathlib.Path(sys.argv[3])/"bin"/"python"\n'
            'destination.parent.mkdir(parents=True)\n'
            'destination.write_text(os.environ["MOCK_PYTHON_SOURCE"])\n'
            'destination.chmod(0o755)\n'
        )
        python.chmod(0o755)
        mock_python = (
            '#!/usr/bin/env python3\nimport json,os,pathlib,sys\n'
            'with open(os.environ["PYTHON_LOG"],"a") as stream: stream.write(json.dumps(sys.argv[1:])+"\\n")\n'
            'if "-r" in sys.argv:\n'
            ' pathlib.Path(os.environ["REQUIREMENTS_COPY"]).write_text(pathlib.Path(sys.argv[sys.argv.index("-r")+1]).read_text())\n'
            'if "check" in sys.argv and os.environ.get("FAIL_CHECK"): sys.exit(33)\n'
        )
        env = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}", TARGETARCH="arm64",
                   PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple", APT_LOG=str(root / "apt.log"),
                   PYTHON_LOG=str(root / "python.log"), REQUIREMENTS_COPY=str(root / "requirements.txt"),
                   MOCK_PYTHON_SOURCE=mock_python)
        return script, env

    def test_python_install_has_complete_pinned_closure_and_isolated_bootstrap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script, env = self.prepare_sandbox(root)
            result = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            requirements = (root / "requirements.txt").read_text().splitlines()
            bootstrap = {"pip", "setuptools", "wheel"}
            expected = [f"{name}=={CONTRACT['versions'][variable]}"
                        for name, variable in CONTRACT["pythonPackages"].items() if name not in bootstrap]
            self.assertEqual(sorted(expected), sorted(requirements))
            calls = [json.loads(line) for line in (root / "python.log").read_text().splitlines()]
            self.assertEqual(3, len(calls))
            self.assertIn("--no-deps", calls[0])
            self.assertIn("--no-deps", calls[1])
            self.assertIn("--no-build-isolation", calls[1])
            self.assertEqual(["-m", "pip", "check"], calls[2])
            for name in bootstrap:
                self.assertIn(f"{name}=={CONTRACT['versions'][CONTRACT['pythonPackages'][name]]}", calls[0])
            records = (root / "opt/tool-versions.d/records").read_text().splitlines()
            self.assertEqual(31, len(records))
            for name, variable in CONTRACT["pythonPackages"].items():
                self.assertIn(f"hunter-python {name} {CONTRACT['versions'][variable]} all", records)

    def test_failed_pip_check_does_not_record_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script, env = self.prepare_sandbox(root)
            env["FAIL_CHECK"] = "1"
            result = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True)
            self.assertEqual(33, result.returncode, result.stderr)
            self.assertFalse((root / "opt/tool-versions.d/records").exists())


if __name__ == "__main__":
    unittest.main()
