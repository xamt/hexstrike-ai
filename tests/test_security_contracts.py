"""五个专用工具契约及命令构造的离线检查。"""
import unittest

from security_tools.contracts import validate_request
from security_tools.commands import build_command


class SecurityContractsTests(unittest.TestCase):
    def test_defaults_and_exact_types(self):
        args = validate_request('whatweb_scan', {'target': 'https://example.com'})
        self.assertEqual(args['aggression'], 1)
        for body in ({'target': 'https://example.com', 'timeout': True},
                     {'target': 'https://example.com', 'extra_args': '-v'},
                     {'target': 'https://example.com', 'timeout': 601}):
            with self.assertRaises(ValueError):
                validate_request('whatweb_scan', body)

    def test_untrusted_targets_and_modes(self):
        for target in ('--help', 'file:///etc/passwd', 'https://user:pass@example.com',
                       'https://example.com\n--help'):
            with self.assertRaises(ValueError):
                validate_request('testssl_scan', {'target': target})
        with self.assertRaises(ValueError):
            validate_request('jwt_tool_analyze', {'token': 'a.b.c', 'mode': 'scan'})
        with self.assertRaises(ValueError):
            validate_request('tcpdump_capture', {'mode': 'capture', 'interface': 'eth0'})

    def test_jwt_scan_uses_header_substitution(self):
        args = validate_request('jwt_tool_analyze', {
            'token': 'a.b.c', 'mode': 'scan', 'target_url': 'https://example.com/me'})
        command = build_command('jwt_tool_analyze', args)
        self.assertIn('Authorization: Bearer a.b.c', command)
        self.assertEqual(command[command.index('-M') + 1], 'at')
        self.assertEqual(build_command('jwt_tool_analyze', validate_request(
            'jwt_tool_analyze', {'token': 'a.b.c'})), ['jwt_tool', 'a.b.c'])

    def test_trufflehog_is_no_update_no_verification_by_default(self):
        args = validate_request('trufflehog_scan', {'target': '/mnt/source'})
        command = build_command('trufflehog_scan', args)
        self.assertIn('--no-verification', command)
        self.assertIn('--no-update', command)
        self.assertIn('--fail-on-scan-errors', command)
        self.assertIn('--no-verification-cache', command)
        self.assertNotIn('--fail', command)
        args['verify'] = True
        self.assertNotIn('--no-verification', build_command('trufflehog_scan', args))

    def test_tcpdump_filter_is_after_option_delimiter(self):
        args = validate_request('tcpdump_capture', {
            'read_file': '/mnt/input.pcap', 'filter': 'tcp port 443'})
        command = build_command('tcpdump_capture', args)
        self.assertEqual(command[-2:], ['--', 'tcp port 443'])
        for field in ('read_file', 'interface'):
            args = {'mode': 'capture', 'interface': 'eth0', 'count': 5}
            args[field] = '-z malicious'
            with self.assertRaises(ValueError):
                validate_request('tcpdump_capture', args)

    def test_each_command_is_argv_and_bounded(self):
        examples = {'testssl_scan': {'target': 'https://example.com'},
                    'whatweb_scan': {'target': 'https://example.com'},
                    'jwt_tool_analyze': {'token': 'a.b.c'},
                    'trufflehog_scan': {'target': '/mnt/source'},
                    'tcpdump_capture': {'read_file': '/mnt/in.pcap'}}
        for name, body in examples.items():
            args = validate_request(name, body)
            self.assertIsInstance(build_command(name, args), list)
            self.assertLessEqual(args['timeout'], 600)
            self.assertLessEqual(args['max_output_bytes'], 1048576)

    def test_capture_limits_and_trufflehog_git_sources(self):
        args = validate_request('tcpdump_capture', {
            'mode': 'capture', 'interface': 'eth0', 'count': 5})
        self.assertIn('eth0', build_command('tcpdump_capture', args))
        for extra in ({'count': 10001}, {'timeout': 121}, {'max_output_bytes': 1048577}):
            with self.assertRaises(ValueError):
                validate_request('tcpdump_capture', {
                    'mode': 'capture', 'interface': 'eth0', 'count': 5, **extra})
        for target in ('https://example.com/repo.git', 'file:///mnt/repo'):
            validate_request('trufflehog_scan', {'source': 'git', 'target': target})
        for target in ('ssh://user@example.com/repo', '-h', 'file://remote/repo'):
            with self.assertRaises(ValueError):
                validate_request('trufflehog_scan', {'source': 'git', 'target': target})
