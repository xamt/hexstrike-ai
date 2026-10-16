"""仅用模拟进程验证 Kubernetes 历史接口兼容，不执行扫描。"""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_wrapper(name):
    """读取安装脚本中指定入口的 Python 源码。"""
    script = (ROOT / "docker/install-cli-compat.sh").read_text()
    source = script.split(f"cat > /usr/local/bin/{name} <<'PY'\n", 1)[1].split("\nPY", 1)[0]
    namespace = {"__name__": "compat_test"}
    exec(compile(source, name, "exec"), namespace)
    return namespace["main"]


class KubernetesCompatibilityTests(unittest.TestCase):
    def bench(self, arguments, callback):
        output = io.StringIO()
        with patch("sys.argv", ["kube-bench"] + arguments), contextlib.redirect_stdout(output):
            with patch("subprocess.call", side_effect=callback) as call:
                status = load_wrapper("kube-bench")()
        return status, output.getvalue(), call.call_args_list

    def test_old_targets_get_run_and_default_config(self):
        status, _, calls = self.bench(["--targets", "node", "--json"], lambda cmd: 0)
        self.assertEqual(status, 0)
        self.assertEqual(calls[0].args[0], ["/opt/kube-bench/kube-bench", "run", "--targets", "node",
                                          "--json", "--config-dir", "/etc/kube-bench/cfg"])

    def test_version_passthrough(self):
        _, _, calls = self.bench(["version"], lambda cmd: 0)
        self.assertEqual(calls[0].args[0], ["/opt/kube-bench/kube-bench", "version"])

    def test_existing_run_and_config_preserved(self):
        args = ["run", "--targets=node", "--config-dir=/custom"]
        _, _, calls = self.bench(args, lambda cmd: 0)
        self.assertEqual(calls[0].args[0], ["/opt/kube-bench/kube-bench"] + args)

    def test_output_is_unique_forwarded_and_replaces_requested_file(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.json"
            report.write_text("stale")
            paths = []

            def execute(command):
                path = Path(command[command.index("--outputfile") + 1])
                self.assertNotEqual(path, report)
                paths.append(path)
                path.write_text('{"fresh":true}')
                return 0

            for option in (["--outputfile", str(report)], [f"--outputfile={report}"]):
                status, output, _ = self.bench(["--targets", "node", "--json"] + option, execute)
                self.assertEqual((status, output), (0, '{"fresh":true}'))
                self.assertEqual(report.read_text(), output)
            self.assertNotEqual(paths[0], paths[1])
            self.assertTrue(all(not path.exists() for path in paths))

    def test_failure_does_not_return_stale_report(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.json"
            report.write_text("stale")
            status, output, _ = self.bench(["--outputfile", str(report)], lambda cmd: 7)
            self.assertEqual((status, output, report.read_text()), (7, "", "stale"))
            self.assertEqual(list(Path(directory).iterdir()), [report])

    def test_success_without_report_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            status, output, _ = self.bench(["--outputfile", str(Path(directory) / "r")], lambda cmd: 0)
            self.assertEqual((status, output), (1, ""))

    def test_audit_findings_preserve_nonzero_status_and_current_report(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.json"

            def execute(command):
                Path(command[command.index("--outputfile") + 1]).write_text('{"fail":1}')
                return 9

            status, output, _ = self.bench(["--outputfile", str(report), "--exit-code", "9"], execute)
            self.assertEqual((status, output, report.read_text()), (9, '{"fail":1}', '{"fail":1}'))

    def test_hunter_rejects_named_interface_instead_of_widening_scope(self):
        for args in (["--interface", "eth0"], ["--interface=eth0"]):
            with patch("sys.argv", ["kube-hunter"] + args), patch("os.execv") as execute:
                self.assertEqual(load_wrapper("kube-hunter")(), 2)
                execute.assert_not_called()

    def test_hunter_explicit_target_and_help_unchanged(self):
        for args in (["--remote", "example.com", "--report", "json"], ["--help"]):
            with patch("sys.argv", ["kube-hunter"] + args), patch("os.execv") as execute:
                load_wrapper("kube-hunter")()
                execute.assert_called_once_with("/opt/kube-hunter-venv/bin/kube-hunter", ["kube-hunter"] + args)


if __name__ == "__main__":
    unittest.main()
