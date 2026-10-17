"""Hakrawler 环境兼容契约；所有网络和子进程均使用替身。"""
import importlib
import io
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docker/compat"))
runtime = importlib.import_module("hakrawler_runtime")
sources = importlib.import_module("hakrawler_sources")
processes = importlib.import_module("hakrawler_process")

DEFAULTS = ["-d", "2", "-u", "--hexstrike-forms=true",
            "--hexstrike-robots=true", "--hexstrike-sitemap=true",
            "--hexstrike-wayback=false"]


class HakrawlerEnvironmentTests(unittest.TestCase):
    def test_native_call_is_forwarded_without_feature_work(self):
        with patch.object(runtime.os, "execv") as execute:
            self.assertEqual(runtime.main(["-d", "3", "-s"]), 0)
        execute.assert_called_once_with("/usr/bin/hakrawler", ["hakrawler", "-d", "3", "-s"])

    def test_defaults_preserve_depth_forms_and_no_archive(self):
        records = '\n'.join(json.dumps({"Source": source, "URL": url}) for source, url in [
            ("href", "https://example.test/a"), ("form", "https://example.test/login"),
            ("href", "https://elsewhere.test/no"), ("href", "https://example.test/a")])
        output = io.StringIO()
        with patch.object(runtime, "run_process", return_value=records) as run:
            with patch.object(runtime, "discover", return_value=[("robots", "https://example.test/a"),
                                                                    ("sitemap", "https://example.test/map")]) as discover:
                with patch.object(runtime.Fetcher, "fetch", return_value=b"ok"):
                    self.assertEqual(runtime.main(DEFAULTS, io.StringIO("https://example.test/\n"), output), 0)
        command = run.call_args.args[0]
        self.assertEqual(command[command.index("-d") + 1], "2")
        self.assertIn("-json=true", command)
        self.assertNotIn("-subs", command)
        self.assertEqual(run.call_count, 1)
        self.assertTrue(discover.call_args.args[1]["robots"])
        self.assertFalse(discover.call_args.args[1]["wayback"])
        self.assertEqual(output.getvalue().splitlines(), ["https://example.test/a",
                         "https://example.test/login", "https://example.test/map"])

    def test_false_form_flag_filters_only_form_records(self):
        records = '\n'.join(json.dumps({"Source": source, "URL": "https://example.test/" + source})
                            for source in ("href", "form", "script"))
        arguments = [item.replace("=true", "=false") if item.startswith("--hexstrike-") else item
                     for item in DEFAULTS]
        output = io.StringIO()
        with patch.object(runtime, "run_process", return_value=records):
            with patch.object(runtime, "discover", return_value=[]):
                with patch.object(runtime.Fetcher, "fetch", return_value=b"ok"):
                    runtime.main(arguments, io.StringIO("https://example.test/\n"), output)
        self.assertNotIn("/form", output.getvalue())
        self.assertIn("/script", output.getvalue())

    def test_form_does_not_hide_same_url_discovered_as_href(self):
        records = '\n'.join(json.dumps({"Source": source, "URL": "https://example.test/shared"})
                            for source in ("form", "href"))
        arguments = [item.replace("forms=true", "forms=false") for item in DEFAULTS]
        output = io.StringIO()
        with patch.object(runtime, "run_process", return_value=records):
            with patch.object(runtime, "discover", return_value=[]):
                with patch.object(runtime.Fetcher, "fetch", return_value=b"ok"):
                    runtime.main(arguments, io.StringIO("https://example.test/\n"), output)
        self.assertEqual(output.getvalue(), "https://example.test/shared\n")

    def test_json_and_source_formats_remain_available(self):
        for flags, expected in [(["-json"], '{"Source": "form", "URL": "https://example.test/form"}'),
                                (["-s"], '[form] https://example.test/form')]:
            output = io.StringIO()
            with patch.object(runtime, "run_process", return_value='{"Source":"form","URL":"https://example.test/form"}'):
                with patch.object(runtime, "discover", return_value=[]):
                    with patch.object(runtime.Fetcher, "fetch", return_value=b"ok"):
                        runtime.main(DEFAULTS + flags, io.StringIO("https://example.test/\n"), output)
            self.assertEqual(output.getvalue().strip(), expected)

    def test_http_configuration_matches_native_options(self):
        _, options, native = runtime.parse_options(DEFAULTS + ["-h", "Cookie: a=b;;X-Test: yes", "-proxy", "http://proxy:8888", "-insecure"])
        fetcher = sources.Fetcher("https://example.test/", options, 99999999999)
        self.assertEqual(fetcher.headers["Cookie"], "a=b")
        self.assertEqual(fetcher.headers["X-Test"], "yes")
        self.assertEqual(options["proxy"], "http://proxy:8888")
        self.assertTrue(options["insecure"])
        self.assertIn("-h", native)

    def test_real_failures_do_not_return_success(self):
        for failure in (RuntimeError("子进程退出 1"), TimeoutError("已超时")):
            with patch.object(runtime, "run_process", side_effect=failure):
                with patch.object(runtime.Fetcher, "fetch", return_value=b"ok"):
                    with patch.object(runtime.sys, "stderr", io.StringIO()) as errors:
                        self.assertEqual(runtime.main(DEFAULTS, io.StringIO("https://example.test/\n"), io.StringIO()), 2)
                        self.assertIn(str(failure), errors.getvalue())

    def test_invalid_native_output_is_not_silently_ignored(self):
        with patch.object(runtime, "run_process", return_value="not JSON"):
            with patch.object(runtime.Fetcher, "fetch", return_value=b"ok"):
                with patch.object(runtime.sys, "stderr", io.StringIO()):
                    self.assertEqual(runtime.main(DEFAULTS, io.StringIO("https://example.test/\n"), io.StringIO()), 2)

    def test_scope_and_fragments(self):
        scope = sources.Scope("https://example.test/path", False)
        self.assertEqual(scope.normalize("/a#part"), "https://example.test/a")
        for url in ("https://elsewhere.test/", "https://sub.example.test/", "javascript:x", "https://user:pass@example.test/"):
            self.assertIsNone(scope.normalize(url))
        self.assertEqual(sources.Scope("https://example.test", True).normalize("https://sub.example.test/a"),
                         "https://sub.example.test/a")

    def test_robots_sitemap_index_and_archive_are_bounded_and_deduplicated(self):
        _, options, _ = runtime.parse_options(DEFAULTS)
        fetcher = sources.Fetcher("https://example.test/path", options, 99999999999)
        docs = {
            "https://example.test/robots.txt": b"User-agent: *\nDisallow: /admin\nDisallow: /wild*\nSitemap: https://example.test/index.xml\nSitemap: https://other.test/map.xml",
            "https://example.test/sitemap.xml": b"<urlset><url><loc>https://example.test/page</loc></url></urlset>",
            "https://example.test/index.xml": b"<sitemapindex><sitemap><loc>https://example.test/child.xml</loc></sitemap></sitemapindex>",
            "https://example.test/child.xml": b"<urlset><url><loc>https://other.test/outside</loc></url><url><loc>https://example.test/child</loc></url></urlset>",
        }
        with patch.object(fetcher, "fetch", side_effect=lambda url, **kwargs: docs[url]) as fetch:
            with patch.object(sources, "run_process") as run:
                result = list(sources.discover(fetcher, options))
        self.assertIn(("robots", "https://example.test/admin"), result)
        self.assertIn(("sitemap", "https://example.test/child"), result)
        self.assertEqual(fetch.call_count, 4)
        run.assert_not_called()

    def test_all_features_false_never_downloads_supplemental_documents(self):
        _, options, _ = runtime.parse_options([arg.replace("=true", "=false") for arg in DEFAULTS])
        fetcher = sources.Fetcher("https://example.test", options, 99999999999)
        with patch.object(fetcher, "fetch") as fetch:
            with patch.object(sources, "run_process") as run:
                self.assertEqual(list(sources.discover(fetcher, options)), [])
        fetch.assert_not_called()
        run.assert_not_called()

    def test_archive_requires_explicit_opt_in_and_stays_in_scope(self):
        _, options, _ = runtime.parse_options(["--hexstrike-wayback=true"])
        fetcher = sources.Fetcher("https://example.test", options, 99999999999)
        with patch.object(sources, "run_process", return_value="https://example.test/old\nhttps://outside.test/no") as run:
            self.assertEqual(list(sources.discover(fetcher, options)), [("wayback", "https://example.test/old")])
        self.assertEqual(run.call_args.args[0], ["/usr/local/bin/waybackurls", "--no-subs", "example.test"])

    def test_optional_html_sitemap_warns_without_failing_primary_results(self):
        _, options, _ = runtime.parse_options(DEFAULTS)
        fetcher = sources.Fetcher("https://example.test", options, 99999999999)
        with patch.object(fetcher, "fetch", return_value=b"<html>fallback</html>"):
            with patch.object(sources.sys, "stderr", io.StringIO()) as errors:
                self.assertEqual(list(sources.discover(fetcher, options)), [])
        self.assertIn("补充来源不可用", errors.getvalue())

    def test_optional_network_failure_is_observable(self):
        _, options, _ = runtime.parse_options(DEFAULTS)
        fetcher = sources.Fetcher("https://example.test", options, 99999999999)
        with patch.object(fetcher, "fetch", side_effect=OSError("连接失败")):
            with patch.object(sources.sys, "stderr", io.StringIO()) as errors:
                self.assertEqual(list(sources.discover(fetcher, options)), [])
        self.assertIn("连接失败", errors.getvalue())

    def test_optional_404_is_absence_but_primary_404_is_error(self):
        _, options, _ = runtime.parse_options(DEFAULTS)
        fetcher = sources.Fetcher("https://example.test", options, 99999999999)
        error = urllib.error.HTTPError("https://example.test", 404, "missing", {}, None)
        with patch.object(fetcher.opener, "open", side_effect=error):
            self.assertIsNone(fetcher.fetch("https://example.test/sitemap.xml", optional=True))
            with self.assertRaises(RuntimeError):
                fetcher.fetch("https://example.test", probe=True)

    def test_redirect_is_rejected_before_outside_request(self):
        handler = sources.ScopedRedirect(sources.Scope("https://example.test"))
        with self.assertRaisesRegex(RuntimeError, "范围"):
            handler.redirect_request(urllib.request.Request("https://example.test"), None,
                                     302, "redirect", {}, "https://outside.test/")

    def test_document_size_and_sitemap_count_are_bounded(self):
        _, options, _ = runtime.parse_options(DEFAULTS)
        fetcher = sources.Fetcher("https://example.test", options, 99999999999)
        with patch.object(sources, "MAX_DOCUMENT", 10):
            with self.assertRaisesRegex(RuntimeError, "上限"):
                fetcher._read(io.BytesIO(b"x" * 11))
        with patch.object(sources, "MAX_SITEMAPS", 1):
            with patch.object(fetcher, "fetch", return_value=b"<urlset />"):
                with self.assertRaisesRegex(RuntimeError, "上限"):
                    list(sources.sitemap_entries(fetcher, ["https://example.test/a", "https://example.test/b"]))

    def test_timed_out_child_is_killed_and_waited(self):
        process = Mock()
        process.poll.return_value = None
        with patch.object(processes.subprocess, "Popen", return_value=process):
            with patch.object(processes.time, "monotonic", return_value=20):
                with self.assertRaises(TimeoutError):
                    processes.run_process(["fake"], "", 10)
        process.kill.assert_called_once()
        process.wait.assert_called_once()

    def test_zero_exit_with_native_timeout_message_is_failure(self):
        process = Mock(returncode=0)
        process.poll.return_value = 0

        def fake_start(*args, **kwargs):
            kwargs["stderr"].write(b"[timeout] https://example.test\n")
            return process

        with patch.object(processes.subprocess, "Popen", side_effect=fake_start):
            with self.assertRaisesRegex(RuntimeError, "timeout"):
                processes.run_process(["fake"], "", 100)


if __name__ == "__main__":
    unittest.main()
