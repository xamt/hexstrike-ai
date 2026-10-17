"""离线模拟 Python 环境拆分，不运行真实 pip 或安装工具。"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = '''
import os, pathlib, shutil, sys
with open(os.environ["PYTHON_LOG"], "a") as stream:
    stream.write(" ".join(sys.argv[1:]) + "\\n")
if sys.argv[1:3] == ["-m", "venv"]:
    target = pathlib.Path(sys.argv[3]) / "bin/python"
    target.parent.mkdir(parents=True)
    shutil.copyfile(sys.argv[0], target)
    target.chmod(0o755)
elif "install" in sys.argv and os.environ.get("FAIL_INSTALL"):
    sys.exit(31)
'''


def prepare(root):
    """复制实际脚本依赖，只重定向绝对目的路径并替换 Python 进程。"""
    for name in ("runtime/python.sh", "tools/forensics/python3.sh", "lib/record-tool-version.sh"):
        target = root / "docker" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((ROOT / "docker" / name).read_text().replace("/opt/", str(root / "opt") + "/"))
    executable = root / "python3"
    executable.write_text(f"#!{sys.executable}\n" + SOURCE)
    executable.chmod(0o755)
    return dict(os.environ, PATH=f"{root}:{os.environ['PATH']}",
                PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple", PYTHON_LOG=str(root / "calls"))


class PythonBootstrapTests(unittest.TestCase):
    def test_global_and_volatility_environments_keep_separate_pinned_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = prepare(root)
            for name in ("runtime/python.sh", "tools/forensics/python3.sh"):
                result = subprocess.run(["bash", str(root / "docker" / name)], env=env,
                                        text=True, capture_output=True)
                self.assertEqual(0, result.returncode, result.stderr)
            records = root / "opt/tool-versions.d"
            self.assertEqual(7, len(list(records.glob("*.tsv"))))
            versions = {"pip": "25.3", "setuptools": "80.9.0", "wheel": "0.45.1"}
            for kind in ("python", "vol-python"):
                for package, version in versions.items():
                    fields = (records / f"{kind}-{package}.tsv").read_text().split("\t")
                    self.assertEqual([kind, package, version, "all"], fields[:4])
            self.assertIn("vol-python\tvolatility3\t2.28.2\tall",
                          (records / "vol-python-volatility3.tsv").read_text())
            calls = (root / "calls").read_text().splitlines()
            self.assertEqual(4, len(calls))
            for call in calls:
                if "install" in call:
                    self.assertIn("--index-url https://pypi.tuna.tsinghua.edu.cn/simple", call)

    def test_bootstrap_failure_stops_before_tool_install_or_version_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = prepare(root)
            env["FAIL_INSTALL"] = "1"
            result = subprocess.run(["bash", str(root / "docker/tools/forensics/python3.sh")],
                                    env=env, text=True, capture_output=True)
            self.assertEqual(31, result.returncode, result.stderr)
            self.assertFalse((root / "opt/tool-versions.d").exists())
            self.assertNotIn("volatility3==", (root / "calls").read_text())


if __name__ == "__main__":
    unittest.main()
