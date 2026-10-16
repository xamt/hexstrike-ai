"""执行边界离线检查：仅启动本地 Python 替身，不执行扫描客户端。"""
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from security_tools.runner import execute_security, SLOTS


class SecurityRunnerTests(unittest.TestCase):
    def run_fake(self, code, **args):
        with patch('security_tools.runner.shutil.which', return_value=sys.executable), \
             patch('security_tools.runner.build_command', return_value=[sys.executable, '-c', code]):
            return execute_security('whatweb_scan', {'target': 'https://example.com', **args})

    def test_success_uses_no_shell_and_isolated_environment(self):
        real_popen = subprocess.Popen
        calls = []

        def popen(*args, **kwargs):
            calls.append(kwargs)
            return real_popen(*args, **kwargs)

        with patch('security_tools.runner.subprocess.Popen', side_effect=popen), \
             patch.dict(os.environ, {'SECRET_ACCESS_KEY': 'do-not-inherit'}):
            result = self.run_fake('import os; print(os.getenv("SECRET_ACCESS_KEY", "clean"))')
        self.assertTrue(result['success'])
        self.assertEqual(result['stdout'].strip(), 'clean')
        self.assertFalse(calls[0]['shell'])
        self.assertTrue(calls[0]['start_new_session'])
        self.assertNotIn('command', result)
        self.assertFalse(os.path.exists(calls[0]['cwd']))

    def test_limits_failures_and_missing_command(self):
        result = self.run_fake('print("X" * 5000)', max_output_bytes=1024)
        self.assertEqual(result['error_code'], 'output_limit')
        self.assertLessEqual(len(result['stdout'].encode()), 1024)
        self.assertEqual(self.run_fake('import time; time.sleep(10)', timeout=1)['error_code'], 'timeout')
        self.assertEqual(self.run_fake('raise SystemExit(3)')['error_code'], 'command_failed')
        with patch('security_tools.runner.shutil.which', return_value=None):
            self.assertEqual(execute_security('whatweb_scan', {'target': 'https://example.com'})['error_code'], 'tool_missing')

    def test_busy_and_revalidation(self):
        for _ in range(4):
            self.assertTrue(SLOTS.acquire(blocking=False))
        try:
            result = execute_security('whatweb_scan', {'target': 'https://example.com'})
            self.assertEqual(result['error_code'], 'busy')
        finally:
            for _ in range(4):
                SLOTS.release()
        self.assertEqual(execute_security('whatweb_scan', {'target': '--help'})['error_code'], 'invalid_request')

    def test_errors_do_not_leak_exception_details(self):
        with patch('security_tools.runner.shutil.which', side_effect=OSError('secret')):
            result = execute_security('whatweb_scan', {'target': 'https://example.com'})
        self.assertNotIn('secret', str(result))

    def test_timeout_kills_process_group(self):
        with patch('security_tools.runner.os.killpg', wraps=os.killpg) as kill:
            self.run_fake('import time; time.sleep(10)', timeout=1)
        kill.assert_called_once()

    def test_jwt_initializes_without_token_and_discards_tool_log(self):
        calls = []

        def fake_execute(argv, args, directory, env, deadline):
            calls.append((list(argv), deadline))
            config_dir = Path(directory, '.jwt_tool')
            if len(argv) == 1:
                config_dir.mkdir()
                (config_dir / 'jwtconf.ini').write_text('[services]\njwt_tool_version=2.3.0')
                return {'return_code': 1, 'error_code': 'command_failed'}
            self.assertTrue((config_dir / 'logs.txt').is_symlink())
            self.assertEqual(os.readlink(config_dir / 'logs.txt'), os.devnull)
            return {'success': True, 'stdout': 'decoded'}

        with patch('security_tools.runner.shutil.which', return_value='/usr/local/bin/jwt_tool'), \
             patch('security_tools.runner._execute', side_effect=fake_execute):
            result = execute_security('jwt_tool_analyze', {'token': 'a.b.c'})
        self.assertTrue(result['success'])
        self.assertEqual(calls[0][0], ['/usr/local/bin/jwt_tool'])
        self.assertEqual(calls[0][1], calls[1][1])

    def test_jwt_failed_initialization_does_not_run_request(self):
        with patch('security_tools.runner.shutil.which', return_value='/usr/local/bin/jwt_tool'), \
             patch('security_tools.runner._execute', return_value={'return_code': 1}) as execute:
            result = execute_security('jwt_tool_analyze', {'token': 'a.b.c'})
        self.assertEqual(result['error_code'], 'execution_error')
        execute.assert_called_once()

    def test_combined_output_remains_bounded_after_utf8_replacement(self):
        result = self.run_fake('import os; os.write(1, b"\\xff" * 700); os.write(2, b"Y" * 700)',
                               max_output_bytes=1024)
        self.assertEqual(result['error_code'], 'output_limit')
        self.assertLessEqual(sum(len(result[key].encode()) for key in ('stdout', 'stderr')), 1024)

    def test_jwt_initialization_timeout_is_not_retried(self):
        with patch('security_tools.runner.shutil.which', return_value='/usr/local/bin/jwt_tool'), \
             patch('security_tools.runner._execute', return_value={
                 'return_code': -9, 'error_code': 'timeout', 'stdout': 'sensitive'}) as execute:
            result = execute_security('jwt_tool_analyze', {'token': 'a.b.c'})
        self.assertEqual(result['error_code'], 'timeout')
        self.assertEqual(result['stdout'], '')
        execute.assert_called_once()
