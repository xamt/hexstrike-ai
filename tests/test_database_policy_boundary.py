"""策略在HTTP和直接执行边界生效；不启动数据库客户端。"""
import json
import unittest
from unittest.mock import patch

from flask import Flask

from database_tools.contracts import CONTRACTS, validate_request
from database_tools.http import register_database_routes
from database_tools.policy_errors import OperationNotAllowed
from database_tools.runner import execute_database

CASES = {
    "mysql_query": ("query", "DROP DATABASE private_db"),
    "clickhouse_query": ("query", "ALTER TABLE private_table DROP COLUMN secret"),
    "postgresql_query": ("query", "DROP TABLE private_table"),
    "redis_command": ("command", ["FLUSHALL"]),
    "mongodb_command": ("command", {"dropDatabase": 1}),
}


class DatabasePolicyBoundaryTests(unittest.TestCase):
    def test_http_denial_never_calls_executor_or_discloses_input(self):
        app = Flask(__name__)
        register_database_routes(app)
        with patch("database_tools.http.execute_database") as execute:
            for name, (field, value) in CASES.items():
                response = app.test_client().post("/" + CONTRACTS[name]["endpoint"], json={
                    "host": "db.example.test", field: value, "username": "reader",
                    "password": "private-password"})
                with self.subTest(name=name):
                    self.assertEqual(response.status_code, 403)
                    self.assertEqual(response.json["error_code"], "operation_not_allowed")
                    self.assertFalse(response.json["success"])
                    self.assertNotIn("private", json.dumps(response.json))
            execute.assert_not_called()

    def test_direct_execution_revalidates_mutated_arguments_before_resources(self):
        with patch("database_tools.runner.build_invocation") as build:
            with patch("database_tools.runner.subprocess.Popen") as popen:
                for name, (field, value) in CASES.items():
                    safe = "SELECT 1" if field == "query" else (
                        ["PING"] if name == "redis_command" else {"ping": 1})
                    args = validate_request(name, {"host": "db.example.test", field: safe})
                    args[field] = value
                    result = execute_database(name, args)
                    self.assertEqual(result["error_code"], "operation_not_allowed")
                    self.assertIsNone(result["return_code"])
                    self.assertEqual(result["stdout"], "")
                build.assert_not_called()
                popen.assert_not_called()

    def test_no_allow_dangerous_override(self):
        for key in ("unsafe", "read_only", "allow_destructive", "skip_validation"):
            with self.assertRaises(ValueError):
                validate_request("mysql_query", {
                    "host": "x", "query": "SELECT 1", key: True})

    def test_direct_non_json_value_rejected_without_spawning(self):
        with patch("database_tools.runner.subprocess.Popen") as popen:
            result = execute_database("mongodb_command", {
                "host": "x", "command": {"find": "items", "filter": {"x": object()}}})
            self.assertEqual(result["error_code"], "invalid_request")
            popen.assert_not_called()

    def test_supported_writes_reach_http_executor(self):
        app = Flask(__name__)
        register_database_routes(app)
        cases = {
            "mysql_query": {"query": "INSERT INTO t (id) VALUES (1)"},
            "postgresql_query": {"query": "UPDATE t SET name='new' WHERE id=1"},
            "clickhouse_query": {"query": "INSERT INTO t VALUES (1)"},
            "redis_command": {"command": ["SET", "sample", "value", "NX"]},
            "mongodb_command": {"database": "test_db", "command": {
                "insert": "items", "documents": [{"id": 1}]}},
        }
        with patch("database_tools.http.execute_database", return_value={"success": True}) as execute:
            for name, args in cases.items():
                # 保持MongoDB命令首键，不使用Flask测试助手的键排序。
                response = app.test_client().post("/" + CONTRACTS[name]["endpoint"],
                    data=json.dumps({"host": "db.example.test", **args}), content_type="application/json")
                self.assertEqual(response.status_code, 200, response.json)
            self.assertEqual(execute.call_count, 5)

    def test_mongodb_system_metadata_writes_denied(self):
        for database, target in (("admin", "users"), ("config", "settings"),
                                 ("local", "startup_log"), ("test", "system.js")):
            with self.assertRaises(OperationNotAllowed):
                validate_request("mongodb_command", {"host": "x", "database": database,
                    "command": {"insert": target, "documents": [{"value": 1}]}})

    def test_duplicate_json_keys_rejected(self):
        app = Flask(__name__)
        register_database_routes(app)
        body = '{"host":"x","command":{"ping":1,"ping":2}}'
        with patch("database_tools.http.execute_database") as execute:
            response = app.test_client().post("/api/tools/mongodb", data=body)
            self.assertEqual(response.status_code, 400)
            execute.assert_not_called()
