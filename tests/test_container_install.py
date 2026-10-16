"""Offline container client packaging checks; package managers are always mocked."""

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "docker/install-container-tools.sh"
CONTRACT = json.loads((ROOT / "tests/fixtures/container-tool-contract.json").read_text())


class ContainerInstallTests(unittest.TestCase):
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
        script = SCRIPT.read_text()
        variables = dict(re.findall(r"^([A-Z][A-Z0-9_]*_VERSION)=(\S+)$", script, re.M))
        self.assertEqual(variables, CONTRACT["versions"])
        for forbidden in ("curl ", "wget ", "--download-db-only", "--download-java-db-only", "systemctl "):
            self.assertNotIn(forbidden, script)
        subprocess.run(["bash", "-n", str(SCRIPT)], check=True)


if __name__ == "__main__":
    unittest.main()
