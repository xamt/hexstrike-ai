"""数据库 HTTP 契约测试；不连接数据库。"""
import json
import unittest
from unittest.mock import patch

from flask import Flask

from database_tools.contracts import CONTRACTS, validate_request
from database_tools.http import register_database_routes


class DatabaseContractTests(unittest.TestCase):
    def test_defaults_and_required_fields(self):
        for name in CONTRACTS:
            payload = {"host": "db.example.test"}
            payload["command" if "command" in name else "query"] = (
                ["PING"] if name == "redis_command" else
                {"ping": 1} if name == "mongodb_command" else "SELECT 1"
            )
            args = validate_request(name, payload)
            self.assertEqual(args["timeout"], 30)
            self.assertEqual(args["max_output_bytes"], 65536)
            with self.assertRaises(ValueError):
                validate_request(name, {})

    def test_reject_invalid_types_and_connection_injection(self):
        for change in ({"host": "-x"}, {"host": "host:5432/db"},
                       {"host": "/tmp/socket"}, {"port": True},
                       {"port": 65536}, {"timeout": 601},
                       {"max_output_bytes": 1048577}, {"extra": "x"},
                       {"database": "host=other"}, {"password": "x\0y"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_request("postgresql_query", {
                    "host": "db.example.test", "query": "SELECT 1", **change})

    def test_five_routes_forward_only_valid_requests(self):
        app = Flask(__name__)
        register_database_routes(app)
        client = app.test_client()
        with patch("database_tools.http.execute_database") as execute:
            execute.return_value = {"success": True, "return_code": 0}
            for name, schema in CONTRACTS.items():
                field = "command" if "command" in name else "query"
                value = ["PING"] if name == "redis_command" else (
                    {"ping": 1} if name == "mongodb_command" else "SELECT 1")
                response = client.post("/" + schema["endpoint"], json={
                    "host": "db.example.test", field: value})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json["success"])
                self.assertEqual(execute.call_args.args[0], name)
            self.assertEqual(execute.call_count, 5)
            for payload in ([], None, {}, {"host": "x", "query": 1}):
                response = client.post("/api/tools/mysql", json=payload)
                self.assertEqual(response.status_code, 400)
            self.assertEqual(execute.call_count, 5)

    def test_error_statuses_and_no_exception_detail(self):
        app = Flask(__name__)
        register_database_routes(app)
        client = app.test_client()
        with patch("database_tools.http.execute_database") as execute:
            for error, status in (("tool_missing", 503), ("busy", 429),
                                  ("timeout", 504), ("output_limit", 422),
                                  ("command_failed", 422)):
                execute.return_value = {"success": False, "error_code": error}
                response = client.post("/api/tools/mysql", json={
                    "host": "db.example.test", "query": "SELECT 1"})
                self.assertEqual(response.status_code, status)
            execute.side_effect = RuntimeError("SECRET detail")
            response = client.post("/api/tools/mysql", json={
                "host": "db.example.test", "query": "SELECT 1"})
            self.assertEqual(response.status_code, 500)
            self.assertNotIn("SECRET", json.dumps(response.json))

    def test_unsafe_json_and_large_request_rejected_without_execution(self):
        app = Flask(__name__)
        register_database_routes(app)
        client = app.test_client()
        with patch("database_tools.http.execute_database") as execute:
            bodies = ["[" * 2000 + "0" + "]" * 2000,
                      '{"host":"x","query":"SELECT 1","password":"\\ud800"}']
            for body in bodies:
                response = client.post("/api/tools/mysql", data=body,
                                       content_type="application/json")
                self.assertEqual(response.status_code, 400)
            response = client.post("/api/tools/mysql", data="x" * 131073)
            self.assertEqual(response.status_code, 413)
            execute.assert_not_called()

    def test_validation_errors_identify_field_without_value(self):
        app = Flask(__name__)
        register_database_routes(app)
        response = app.test_client().post("/api/tools/mysql", json={
            "host": "db.example.test", "query": "SELECT 1", "timeout": 999})
        self.assertEqual(response.status_code, 400)
        self.assertIn("timeout", response.json["error"])
        self.assertNotIn("999", response.json["error"])
