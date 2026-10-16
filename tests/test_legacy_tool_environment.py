"""Offline checks for legacy CLI packaging; never execute installed security tools."""

import ast
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "legacy_collector", ROOT / "docker/collect-python2-runtime.py"
)
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class LegacyPackagingTests(unittest.TestCase):
    def test_shell_scripts_parse_without_execution(self):
        for filename in (
            "install-paramspider-legacy.sh",
            "install-volatility2-runtime.sh",
            "install-volatility3-compat.sh",
        ):
            with self.subTest(filename=filename):
                subprocess.run(["bash", "-n", str(ROOT / "docker" / filename)], check=True)

    def test_source_archives_are_exact_and_checked(self):
        for filename, commit, digest in (
            ("install-paramspider-legacy.sh", "3add9faf11fa269624a2a9e92ea12be90338cb02",
             "18196d50530c8694d6f61175489c531641ae27550db2c8a1eaec1f5f47f0b745"),
            ("install-volatility2-runtime.sh", "VOLATILITY2_VERSION=2.6.1",
             "a8dfdbdb2aaa0885387b709b821bb8250e698086fb32015bc2896ea55f359058"),
        ):
            script = (ROOT / "docker" / filename).read_text()
            self.assertIn(commit, script)
            self.assertIn(digest, script)
            self.assertLess(script.index("sha256sum -c -"), script.index("tar -xzf"))

    def test_paramspider_keeps_caller_output_directory(self):
        script = (ROOT / "docker/install-paramspider-legacy.sh").read_text()
        wrapper = script.split("<<'WRAPPER'\n", 1)[1].split("\nWRAPPER", 1)[0]
        self.assertNotIn("cd ", wrapper)
        self.assertIn('/opt/paramspider-venv/bin/python /opt/paramspider/paramspider.py "$@"', wrapper)
        self.assertNotIn("--level high", wrapper)

    def test_volatility_versions_are_not_aliased(self):
        script = (ROOT / "docker/install-volatility2-runtime.sh").read_text()
        self.assertIn("export PYTHONHOME=/opt/python2", script)
        self.assertIn("unset PYTHONPATH", script)
        self.assertIn("/opt/python2/lib:/opt/python2/lib/compat", script)
        self.assertIn('/usr/local/bin/volatility2-python /opt/volatility2/vol.py "$@"', script)
        self.assertIn("cat > /out/usr/local/bin/volatility ", script)
        self.assertNotIn("cat > /out/usr/local/bin/vol.py ", script)
        self.assertNotIn("volatility3-venv", script)

    def test_volatility3_compatibility_path_is_python(self):
        script = (ROOT / "docker/install-volatility3-compat.sh").read_text()
        source = script.split("<<'PY'\n", 1)[1].split("\nPY", 1)[0]
        ast.parse(source)
        self.assertIn("cat > /usr/local/bin/vol.py ", script)
        with patch("os.execv") as execute:
            with patch("sys.argv", ["/opt/volatility3/vol.py", "-f", "memory.raw", "windows.info"]):
                exec(compile(source, "vol.py", "exec"), {})
        execute.assert_called_once_with(
            "/opt/volatility3-venv/bin/vol", ["vol", "-f", "memory.raw", "windows.info"]
        )


class RuntimeCollectionTests(unittest.TestCase):
    def test_glibc_is_not_bundled(self):
        process = Mock(returncode=0)
        process.communicate.return_value = (
            b"libssl.so.1.1 => /usr/lib/libssl.so.1.1 (0x123)\n"
            b"libc.so.6 => /lib/libc.so.6 (0x456)\n"
            b"libpthread.so.0 => /lib/libpthread.so.0 (0x789)\n", b""
        )
        with patch.object(collector.subprocess, "Popen", return_value=process):
            self.assertEqual(collector.shared_dependencies("fake.so"), ["/usr/lib/libssl.so.1.1"])

    def test_unresolved_dependencies_fail_closed(self):
        process = Mock(returncode=0)
        process.communicate.return_value = (b"libmissing.so => not found\n", b"")
        with patch.object(collector.subprocess, "Popen", return_value=process):
            with self.assertRaisesRegex(RuntimeError, "Unresolved"):
                collector.shared_dependencies("fake.so")

    def test_collector_copies_external_dependency_recursively(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            (source / "python2").write_bytes(b"\x7fELFfake")
            (source / "lib").mkdir()
            library = root / "libssl.so.1.1"
            library.write_bytes(b"external-library")
            destination = root / "output"
            def dependencies(path):
                return [str(library)] if path.endswith("python2") else []
            with patch.object(collector, "shared_dependencies", side_effect=dependencies):
                collector.collect(str(source), str(destination))
            self.assertEqual((destination / "lib/compat/libssl.so.1.1").read_bytes(), b"external-library")


if __name__ == "__main__":
    unittest.main()
