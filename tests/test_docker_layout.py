"""只检查构建文件的组织和参数作用域，不调用 Docker。"""
import json
import re
import shlex
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DockerLayoutTests(unittest.TestCase):
    """约束参数只有一个默认值来源，安装过程统一由脚本实现。"""

    def test_defaults_are_centralized(self):
        content = (ROOT / "Dockerfile.base").read_text()
        header, stages = content.split("\nFROM ", 1)
        defaults = re.findall(r"^ARG (\w+)=(.+)$", header, re.M)
        self.assertGreater(len(defaults), 60)
        self.assertEqual(len(defaults), len(dict(defaults)))
        self.assertNotRegex(stages, r"(?m)^ARG \w+=")
        self.assertNotIn("ARG BUILDPLATFORM", header)
        self.assertNotIn("ARG TARGETARCH", header)
        for path in (ROOT / "docker").glob("*.sh"):
            self.assertNotRegex(path.read_text(), r"(?m)^(?:export )?\w+_VERSION=")

    def test_every_run_executes_a_mounted_script(self):
        content = (ROOT / "Dockerfile.base").read_text().replace("\\\n", " ")
        runs = re.findall(r"^RUN (.+)$", content, re.M)
        self.assertGreater(len(runs), 10)
        for run in runs:
            with self.subTest(run=run):
                source = re.search(r"source=(docker/[\w-]+\.sh)", run)
                self.assertIsNotNone(source)
                self.assertTrue((ROOT / source[1]).is_file())
                self.assertRegex(run, r"bash /tmp/[\w-]+\.sh(?: |$)")
                self.assertNotIn("&&", run)

    def test_build_versions_reach_their_stage(self):
        content = (ROOT / "Dockerfile.base").read_text()
        stage_args = {
            "rust-tools": ("RUST_TOOLCHAIN", "X8_VERSION"),
            "nikto-source": ("NIKTO_VERSION",),
            "python-runtime": ("PIP_VERSION", "SETUPTOOLS_VERSION", "WHEEL_VERSION", "VOLATILITY3_VERSION"),
            "base": ("VOLATILITY3_VERSION", "TARGETARCH"),
        }
        for stage, names in stage_args.items():
            section = re.search(rf"(?m)^FROM .+ AS {stage}\n([\s\S]*?)(?=^FROM |\Z)", content)[1]
            for name in names:
                self.assertIn(f"ARG {name}\n", section)

    def test_all_apt_versions_are_imported_into_install_stage(self):
        content = (ROOT / "Dockerfile.base").read_text()
        section = content.split("AS security-packages\n", 1)[1].split("\nFROM ", 1)[0]
        contract = json.loads((ROOT / "tests/fixtures/docker-tool-contract.json").read_text())
        for name in contract["aptPackages"].values():
            names = (f"{name}_AMD64", f"{name}_ARM64") if name in {
                "MASSCAN_VERSION", "DIRB_VERSION", "OPHCRACK_CLI_VERSION", "FOREMOST_VERSION"
            } else (name,)
            for argument in names:
                self.assertIn(f"ARG {argument}\n", section)

    def test_documented_commands_are_standalone_and_architecture_matched(self):
        docs = (ROOT / "DOCKER_BUILD.md").read_text()
        blocks = re.findall(r"```bash\n([\s\S]*?)```", docs)
        builds = []
        for block in blocks:
            subprocess.run(["bash", "-n"], input=block, text=True, check=True)
            if block.startswith("docker buildx build"):
                builds.append(shlex.split(block.replace("\\\n", " ")))
        self.assertEqual(4, len(builds))
        pairs = set()
        for command in builds:
            architecture = command[command.index("--platform") + 1].split("/")[1]
            recipe = command[command.index("--file") + 1]
            tag = command[command.index("--tag") + 1]
            self.assertTrue(tag.endswith(f":1.0.0-{architecture}"))
            if recipe == "Dockerfile":
                base = command[command.index("--build-arg") + 1]
                self.assertTrue(base.endswith(f"pentest-tools-base:1.0.0-{architecture}"))
            pairs.add((recipe, architecture))
        self.assertEqual({(recipe, arch) for recipe in ("Dockerfile", "Dockerfile.base")
                          for arch in ("amd64", "arm64")}, pairs)


if __name__ == "__main__":
    unittest.main()
