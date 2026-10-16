"""只检查构建文件的组织和参数作用域，不调用 Docker。"""
import re
import shlex
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DockerLayoutTests(unittest.TestCase):
    """约束参数只有一个默认值来源，安装过程统一由脚本实现。"""

    def test_dockerfile_only_keeps_build_configuration(self):
        content = (ROOT / "Dockerfile.base").read_text()
        header, stages = content.split("\nFROM ", 1)
        defaults = re.findall(r"^ARG (\w+)=(.+)$", header, re.M)
        self.assertEqual(10, len(defaults))
        self.assertEqual(len(defaults), len(dict(defaults)))
        self.assertNotRegex(stages, r"(?m)^ARG \w+=")
        self.assertNotIn("ARG BUILDPLATFORM", header)
        self.assertNotIn("ARG TARGETARCH", header)
        self.assertNotRegex(content, r"\b\w+_VERSION\b")
        self.assertNotIn("RUST_TOOLCHAIN", content)
        rust = (ROOT / "docker/install-rust-toolchain.sh").read_text()
        self.assertIn("RUST_TOOLCHAIN=1.79.0", rust)
        self.assertIn('rustup default "${RUST_TOOLCHAIN}"', rust)

    def test_go_download_sources_are_scoped_and_keep_checksum_verification(self):
        content = (ROOT / "Dockerfile.base").read_text()
        header, stages = content.split("\nFROM ", 1)
        self.assertIn("ARG GOPROXY=https://goproxy.cn", header)
        self.assertIn('ARG GOSUMDB="sum.golang.org https://goproxy.cn/sumdb/sum.golang.org"', header)
        go_stage = stages.split("\nFROM ", 1)[0]
        for name in ("GOPROXY", "GOSUMDB"):
            self.assertIn(f"ARG {name}\n", go_stage)
            self.assertIn(f"{name}=${{{name}}}", go_stage)
        self.assertNotIn("GOSUMDB=off", content)
        self.assertNotIn("GOINSECURE", content)
        self.assertNotIn("GONOSUMDB", content)
        script = (ROOT / "docker/install-go-tool.sh").read_text()
        self.assertNotIn("GOPROXY=", script)
        self.assertIn('go install "${package}@${version}"', script)

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

    def test_expected_records_reach_final_stage(self):
        content = (ROOT / "Dockerfile.base").read_text()
        for stage in ("go-tools", "rust-tools", "nikto-source", "python-runtime"):
            self.assertRegex(content, rf"COPY --from={stage} \S+/ /opt/hexstrike/tool-versions.d/")
        self.assertIn("source=docker/verify-tool-versions.py", content)
        self.assertIn("verify-tool-versions.py", (ROOT / "docker/verify-base.sh").read_text())

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
            self.assertTrue(tag.endswith(f":1.2.0-{architecture}"))
            if recipe == "Dockerfile":
                base = command[command.index("--build-arg") + 1]
                self.assertTrue(base.endswith(f"pentest-tools-base:1.2.0-{architecture}"))
            pairs.add((recipe, architecture))
        self.assertEqual({(recipe, arch) for recipe in ("Dockerfile", "Dockerfile.base")
                          for arch in ("amd64", "arm64")}, pairs)


if __name__ == "__main__":
    unittest.main()
