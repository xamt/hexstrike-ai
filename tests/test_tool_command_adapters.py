"""仅检查参数与转交行为；不执行安全工具或构建镜像。"""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cli_compat", ROOT / "docker/compat/cli-compat.py")
compat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compat)


class ToolCommandAdaptersTests(unittest.TestCase):
    def test_enum_legacy_categories_and_domain(self):
        self.assertEqual(compat.enum4linux(["host", "-u", "user", "-d", "DOMAIN", "-A", "S,U,G,P"]),
                         ["host", "-u", "user", "-w", "DOMAIN", "-S", "-U", "-G", "-P"])

    def test_enum_modern_and_option_like_password(self):
        for args in (["-A", "host"], ["-A", "S"], ["-d", "host"], ["host", "-p", "-A", "-w", "D"]):
            self.assertEqual(compat.enum4linux(args), list(args))

    def test_enum_partial_selection_does_not_become_all(self):
        self.assertEqual(compat.enum4linux(["host", "-A", "S,P"]), ["host", "-S", "-P"])

    def test_gobuster_only_changes_dns_url_option(self):
        self.assertEqual(compat.gobuster(["dns", "-u", "example.com", "-w", "words"]),
                         ["dns", "--domain", "example.com", "-w", "words"])
        for args in (["dir", "-u", "https://host"], ["dns", "-do", "host"]):
            self.assertEqual(compat.gobuster(args), list(args))
        with self.assertRaises(ValueError):
            compat.gobuster(["dns", "-u", "https://host/path"])

    def test_checksec_accepts_both_file_forms(self):
        self.assertEqual(compat.checksec(["--file", "a b"]), ["--file=a b"])
        self.assertEqual(compat.checksec(["--file=a b"]), ["--file=a b"])
        with self.assertRaises(ValueError):
            compat.checksec(["--file"])
        self.assertEqual(compat.checksec(["--", "literal"]), ["--", "literal"])

    def test_go_boolean_flags_moved_before_operand(self):
        self.assertEqual(compat.go_flags(["example.com", "--get-versions", "--no-subs"],
                                         {"dates", "get-versions", "no-subs"}),
                         ["--get-versions", "--no-subs", "example.com"])
        self.assertEqual(compat.go_flags(["out file", "-q", "-d=false"], {"q", "d", "t"}),
                         ["-q", "-d=false", "out file"])

    def test_go_explicit_terminator_and_unknown_options_not_silently_ignored(self):
        self.assertEqual(compat.go_flags(["--", "-q"], {"q"}), ["--", "-q"])
        with self.assertRaises(ValueError):
            compat.go_flags(["out", "--unknown"], {"q"})
        with self.assertRaises(ValueError):
            compat.go_flags(["first", "second"], {"q"})

    def test_binwalk_extract_defaults_to_dedicated_user_only_as_root(self):
        with patch.object(compat.os, "geteuid", return_value=0):
            self.assertEqual(compat.binwalk(["-e", "sample"]),
                             ["--run-as=hexstrike-extract", "-e", "sample"])
            self.assertEqual(compat.binwalk(["--help"]), ["--help"])
            self.assertEqual(compat.binwalk(["-e", "--run-as=user", "sample"]),
                             ["-e", "--run-as=user", "sample"])
        with patch.object(compat.os, "geteuid", return_value=1000):
            self.assertEqual(compat.binwalk(["-e", "sample"]), ["-e", "sample"])

    def test_exec_replaces_wrapper_without_shell_or_status_masking(self):
        with patch.object(compat.sys, "argv", ["/opt/hexstrike-compat/bin/checksec", "--file", "x"]):
            with patch.object(compat.os, "execv") as execute:
                self.assertEqual(compat.main(), 0)
            execute.assert_called_once_with("/usr/bin/checksec", ["checksec", "--file=x"])

    def test_ghidra_default_and_custom_script_paths(self):
        args = ["/tmp/project", "name", "-postScript", "ExportXml.java", "/tmp/report.xml"]
        self.assertEqual(compat.ghidra(args), args + ["-scriptPath", "/opt/hexstrike-compat/ghidra"])
        self.assertEqual(compat.ghidra(["project", "name", "-scriptPath", "/tmp/my scripts"]),
                         ["project", "name", "-scriptPath", "/tmp/my scripts;/opt/hexstrike-compat/ghidra"])
        self.assertEqual(compat.ghidra([]), [])
        with self.assertRaises(ValueError):
            compat.ghidra(["project", "name", "-scriptPath"])

    def test_installation_does_not_replace_verified_go_binaries(self):
        base = (ROOT / "Dockerfile.base").read_text()
        app = (ROOT / "Dockerfile").read_text()
        for content in (base, app):
            self.assertIn('PATH="/opt/hexstrike-compat/bin:', content)
        install = (ROOT / "docker/compat/install.sh").read_text()
        self.assertIn("cli-compat.py", install)
        self.assertIn("hexstrike-extract", install)
        self.assertIn('test "$(id -u hexstrike-extract)" = "$(id -g hexstrike-extract)"', install)
        self.assertIn('--uid "${extract_id}" --gid "${extract_id}"', install)
        self.assertNotIn("mv /usr/local/bin/waybackurls", install)


if __name__ == "__main__":
    unittest.main()
