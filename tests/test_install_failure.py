"""安装脚本必须在首个失败步骤停止，不能继续执行后续工具。"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InstallFailureTests(unittest.TestCase):
    """模拟包源失败，确认未静默跳过任何工具。"""

    def test_first_index_failure_stops_category(self):
        self.check_failure(1)

    def test_first_package_failure_stops_category(self):
        self.check_failure(2)

    def test_later_package_failure_does_not_record_failed_tool(self):
        self.check_failure(3)

    def check_failure(self, fail_on):
        """在指定调用失败，并断言没有尝试安装后续工具。"""
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            fake = directory / "apt-get"
            fake.write_text('#!/bin/sh\nprintf "调用\\n" >> "$TEST_LOG"\n'
                            'if [ "$(wc -l < "$TEST_LOG")" -eq "$TEST_FAIL_ON" ]; then exit 37; fi\n'
                            'exit 0\n')
            fake.chmod(0o755)
            log = directory / "calls"
            records = directory / "records"
            env = dict(os.environ, PATH=f"{directory}:{os.environ['PATH']}",
                       TEST_LOG=str(log), TEST_FAIL_ON=str(fail_on), TARGETARCH="arm64",
                       TOOL_RECORD_DIR=str(records))
            result = subprocess.run(["bash", str(ROOT / "docker/tools/network/apt.sh")],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(37, result.returncode, result.stderr)
            self.assertEqual(fail_on, len(log.read_text().splitlines()))
            expected = ["apt-nmap.tsv"] if fail_on == 3 else []
            self.assertEqual(expected, sorted(path.name for path in records.glob("*.tsv")))


if __name__ == "__main__":
    unittest.main()
