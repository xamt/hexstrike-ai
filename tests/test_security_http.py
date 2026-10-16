"""Flask 测试客户端验证路由，无网络监听或真实工具调用。"""
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask
from security_tools.contracts import CONTRACTS
from security_tools.http import register_security_routes


class SecurityHttpTests(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        register_security_routes(app)
        self.client = app.test_client()

    def test_five_routes_dispatch_to_bound_handler(self):
        examples = [{'target': 'https://example.com'}, {'target': 'https://example.com'},
                    {'token': 'a.b.c'}, {'target': '/mnt/source'}, {'read_file': '/mnt/in.pcap'}]
        for (name, contract), payload in zip(CONTRACTS.items(), examples):
            with patch('security_tools.http.execute_security', return_value={'success': True}) as execute:
                response = self.client.post('/' + contract['endpoint'], json=payload)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(execute.call_args.args[0], name)

    def test_invalid_unknown_duplicate_and_oversize_do_not_execute(self):
        path = '/api/tools/whatweb'
        with patch('security_tools.http.execute_security') as execute:
            for payload in ('[]', '{', '{"target":"https://a","target":"https://b"}',
                            json.dumps({'target': 'https://a', 'timeout': True}),
                            json.dumps({'target': 'https://a', 'additional_args': '--help'})):
                self.assertEqual(self.client.post(path, data=payload).status_code, 400)
            self.assertEqual(self.client.post(path, data='X' * 131073).status_code, 413)
        execute.assert_not_called()

    def test_status_codes_and_exception_redaction(self):
        for code, status in [('busy', 429), ('timeout', 504), ('tool_missing', 503),
                             ('output_limit', 422), ('command_failed', 422)]:
            with patch('security_tools.http.execute_security', return_value={
                    'success': False, 'error_code': code}):
                response = self.client.post('/api/tools/whatweb', json={'target': 'https://a'})
            self.assertEqual(response.status_code, status)
        with patch('security_tools.http.execute_security', side_effect=RuntimeError('secret-token')):
            response = self.client.post('/api/tools/jwt-tool', json={'token': 'a.b.c'})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('secret-token', response.get_data(as_text=True))

    def test_server_keeps_legacy_jwt_analyzer_and_registers_real_names(self):
        source = Path('hexstrike_server.py').read_text()
        self.assertIn('register_security_routes(app)', source)
        self.assertIn('"jwt-tool": "jwt_tool"', source)
        self.assertNotIn('python3 /opt/jwt_tool/jwt_tool.py', source)
        for command in ('testssl', 'whatweb', 'jwt_tool', 'trufflehog', 'tcpdump'):
            self.assertIn('"' + command + '"', source[source.index('def health_check():'):])
        self.assertIn('"jwt-analyzer"', source)
