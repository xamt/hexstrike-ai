"""核对Python包源配置，不访问镜像站、不调用Docker或pip。"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = "https://pypi.tuna.tsinghua.edu.cn/simple"


class PythonDownloadSourceTests(unittest.TestCase):
    """基础镜像和应用默认走国内HTTPS源，允许显式覆盖。"""

    def test_base_exposes_and_passes_index_to_python_stage(self):
        base = (ROOT / "Dockerfile.base").read_text()
        header = base.split("\nFROM ", 1)[0]
        self.assertIn(f"ARG PIP_INDEX_URL={INDEX}", header)
        stage = base.split("FROM python-source AS python-runtime\n", 1)[1].split("\nFROM ", 1)[0]
        self.assertIn("ARG PIP_INDEX_URL\n", stage)
        script = (ROOT / "docker/runtime/python.sh").read_text()
        self.assertEqual(1, script.count('--index-url "${PIP_INDEX_URL}"'))
        volatility = (ROOT / "docker/tools/forensics/python3.sh").read_text()
        self.assertIn('--index-url "${PIP_INDEX_URL}"', volatility)
        self.assertIn('runtime/python.sh" /opt/volatility3-venv vol-python', volatility)

    def test_application_installer_uses_same_configurable_index(self):
        app = (ROOT / "Dockerfile").read_text()
        self.assertIn(f"ARG PIP_INDEX_URL={INDEX}", app)
        self.assertIn('install -r requirements-runtime.txt --index-url "${PIP_INDEX_URL}"', app)
        self.assertLess(app.index("ARG PIP_INDEX_URL"), app.index("install -r requirements-runtime.txt"))

    def test_no_insecure_or_implicit_fallback_source(self):
        for name in ("Dockerfile", "Dockerfile.base", "docker/runtime/python.sh"):
            content = (ROOT / name).read_text()
            self.assertNotIn("--trusted-host", content)
            self.assertNotIn("--extra-index-url", content)
            self.assertNotIn("PIP_TRUSTED_HOST", content)


if __name__ == "__main__":
    unittest.main()
