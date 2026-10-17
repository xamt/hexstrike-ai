"""用伪 Go 命令验证产物路径选择及失败传播，不访问网络。"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAKE_GO = '''
import os
import sys
from pathlib import Path

values = dict(GOPATH=os.environ["TEST_GOPATH"], GOOS="linux",
              GOARCH=os.environ["TEST_ARCH"], GOHOSTOS="linux", GOHOSTARCH="arm64")
if sys.argv[1] == "env":
    print(values[sys.argv[2]])
elif sys.argv[1] == "install":
    assert os.environ.get("GOBIN") == "", "GOBIN 未清除"
    name = os.environ["TEST_TOOL"]
    expected = {"gau": "github.com/lc/gau/v2/cmd/gau@v2.2.4",
                "dalfox": "github.com/hahwul/dalfox/v2@v2.12.0"}
    assert sys.argv[2] == expected[name]
    if os.environ.get("TEST_FAIL"):
        sys.exit(17)
    folder = Path(values["GOPATH"]) / "bin"
    if values["GOARCH"] != values["GOHOSTARCH"]:
        folder /= "linux_" + values["GOARCH"]
    folder.mkdir(parents=True)
    (folder / name).write_text(values["GOARCH"])
else:
    sys.exit(2)
'''


class GoToolInstallTests(unittest.TestCase):
    """本机与交叉构建均收集到相同输出路径。"""

    def run_install(self, arch, fail=False, tool="gau"):
        """创建隔离的 Go 测试环境并返回退出状态与产物。"""
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            go = directory / "go"
            go.write_text(f"#!{sys.executable}\n" + FAKE_GO)
            go.chmod(0o755)
            output = directory / "out"
            env = dict(os.environ, PATH=f"{directory}:{os.environ['PATH']}",
                       TEST_GOPATH=str(directory / "gopath"), TEST_ARCH=arch, TEST_TOOL=tool,
                       GOBIN="/unexpected", OUTPUT_DIR=str(output), TARGETARCH=arch,
                       TOOL_RECORD_DIR=str(directory / "records"))
            if fail:
                env["TEST_FAIL"] = "1"
            result = subprocess.run(
                ["bash", str(ROOT / "docker/install-go-tool.sh"), tool],
                env=env, capture_output=True, text=True,
            )
            artifact = output / tool
            return result, artifact.read_text() if artifact.exists() else None

    def test_native_output(self):
        result, artifact = self.run_install("arm64")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("arm64", artifact)

    def test_cross_compiled_output(self):
        result, artifact = self.run_install("amd64")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("amd64", artifact)

    def test_failed_install_does_not_copy_output(self):
        result, artifact = self.run_install("amd64", fail=True)
        self.assertEqual(17, result.returncode, result.stderr)
        self.assertIsNone(artifact)

    def test_dalfox_legacy_version_uses_same_native_and_cross_paths(self):
        for arch in ("amd64", "arm64"):
            result, artifact = self.run_install(arch, tool="dalfox")
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(arch, artifact)


if __name__ == "__main__":
    unittest.main()
