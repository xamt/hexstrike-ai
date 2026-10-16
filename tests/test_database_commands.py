"""验证数据库命令构造，不运行任何数据库客户端。"""
import json
import subprocess
import tempfile
import unittest

from database_tools.commands import MONGO_SCRIPT, build_invocation
from database_tools.contracts import CONTRACTS, validate_request


def arguments(name, **changes):
    """构造五类最小测试请求。"""
    field = "command" if "command" in name else "query"
    value = ["PING"] if name == "redis_command" else (
        {"ping": 1} if name == "mongodb_command" else "SELECT 1")
    return validate_request(name, {"host": "db.example.test", field: value, **changes})


class DatabaseCommandTests(unittest.TestCase):
    def test_five_clients_credentials_and_ports(self):
        expected = ["mysql", "clickhouse-client", "redis-cli", "psql", "mongosh"]
        with tempfile.TemporaryDirectory() as directory:
            for name, binary in zip(CONTRACTS, expected):
                invocation = build_invocation(name, arguments(name, username="reader", password="test-secret"), directory)
                self.assertEqual(invocation.argv[0], binary)
                self.assertNotIn("test-secret", " ".join(invocation.argv))
                self.assertIn("test-secret", json.dumps(invocation.environment))

    def test_mysql_client_escape_channels_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            invocation = build_invocation("mysql_query", arguments("mysql_query"), directory)
            for option in ("--no-defaults", "--sandbox", "--binary-mode",
                           "--local-infile=0", "--skip-reconnect", "--protocol=TCP"):
                self.assertIn(option, invocation.argv)

    def test_sql_writes_and_literal_backslashes_remain_supported(self):
        query = "UPDATE sample SET value = 'back\\slash' WHERE id = 1"
        with tempfile.TemporaryDirectory() as directory:
            for name in ("mysql_query", "postgresql_query", "clickhouse_query"):
                invocation = build_invocation(name, arguments(name, query=query), directory)
                serialized = " ".join(invocation.argv) + invocation.stdin.decode()
                self.assertIn(query, serialized)

    def test_postgresql_meta_commands_rejected_and_query_atomic(self):
        for query in ("\\! id", "  \\copy x from '/etc/passwd'", "\\i file"):
            with self.assertRaises(ValueError):
                arguments("postgresql_query", query=query)
        with tempfile.TemporaryDirectory() as directory:
            query = "SELECT 1;\n\\! no-local-command"
            invocation = build_invocation("postgresql_query", arguments("postgresql_query", query=query), directory)
            self.assertIn("--command=" + query, invocation.argv)
            self.assertEqual(invocation.stdin, b"")
            self.assertIn("--no-psqlrc", invocation.argv)

    def test_clickhouse_blocks_files_but_not_literals(self):
        for query in ("SELECT 1 INTO OUTFILE '/tmp/x'", "INSERT INTO t FROM INFILE '/etc/passwd'"):
            with self.assertRaises(ValueError):
                arguments("clickhouse_query", query=query)
        arguments("clickhouse_query", query="SELECT 'INFILE OUTFILE' AS words")

    def test_redis_noninteractive_command_preserves_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            command = ["SET", "键", "a\nPING\n$(id)\"\\"]
            invocation = build_invocation("redis_command", arguments("redis_command", command=command), directory)
            self.assertIn("-e", invocation.argv)
            self.assertIn("-x", invocation.argv)
            self.assertNotIn("$(id)", " ".join(invocation.argv))
            self.assertEqual(invocation.argv[-2:], command[:-1])
            self.assertEqual(invocation.stdin.decode(), command[-1])
        for command in ([], ["--eval", "file"], ["CONNECT", "elsewhere"], ["PING", 1]):
            with self.assertRaises(ValueError):
                arguments("redis_command", command=command)

    def test_mongodb_command_is_data_not_local_eval(self):
        command = {"find": "records", "filter": {"value": "'); process.exit(); //"}}
        with tempfile.TemporaryDirectory() as directory:
            invocation = build_invocation("mongodb_command", arguments("mongodb_command", command=command), directory)
            self.assertEqual(invocation.argv[-1], MONGO_SCRIPT)
            self.assertNotIn(command["filter"]["value"], MONGO_SCRIPT)
            data = json.loads(invocation.environment["HEXSTRIKE_MONGO_REQUEST"])
            self.assertEqual(data["command"], command)
            self.assertIn("retryReads=false&retryWrites=false", MONGO_SCRIPT)

    def test_invocation_repr_omits_private_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            invocation = build_invocation("postgresql_query", arguments(
                "postgresql_query", query="SELECT 'private-query'", password="secret"), directory)
            self.assertNotIn("private-query", repr(invocation))
            self.assertNotIn("secret", repr(invocation))

    def test_redis_last_auth_value_uses_stdin(self):
        with tempfile.TemporaryDirectory() as directory:
            invocation = build_invocation("redis_command", arguments(
                "redis_command", command=["AUTH", "test-user", "private-password"]), directory)
            self.assertNotIn("private-password", " ".join(invocation.argv))
            self.assertEqual(invocation.stdin, b"private-password")
            self.assertEqual(invocation.argv[-3:], ["-x", "AUTH", "test-user"])

    def test_mongodb_write_errors_and_concern_errors_are_failures(self):
        harness = """
const vm = require('node:vm');
let input = '';
process.stdin.on('data', part => input += part);
process.stdin.on('end', () => {
  const {script, request, response} = JSON.parse(input);
  const output = [];
  const exits = [];
  function Mongo() {
    this.getDB = () => ({runCommand: () => response});
  }
  vm.runInNewContext(script, {Mongo, EJSON: JSON, print: x => output.push(x),
    quit: code => exits.push(code), process: {env: {
      HEXSTRIKE_MONGO_REQUEST: JSON.stringify(request)}}});
  console.log(JSON.stringify({output, exits}));
});
"""
        for response, code in (({"ok": 1}, 0), ({"ok": 0}, 1),
                               ({"ok": 1, "writeErrors": [{"code": 11000}]}, 1),
                               ({"ok": 1, "writeConcernError": {"code": 64}}, 1),
                               ({"ok": 1, "nErrors": 1}, 1),
                               ({"ok": 1, "cursor": {"firstBatch": [{"ok": 0}]}}, 1),
                               ({"ok": 1, "writeErrors": []}, 0)):
            result = subprocess.run(["node", "-e", harness], input=json.dumps({
                "script": MONGO_SCRIPT, "request": arguments("mongodb_command", command={
                    "bulkWrite": 1, "ops": [], "nsInfo": []}),
                "response": response}), text=True, capture_output=True, check=True)
            observed = json.loads(result.stdout)
            self.assertEqual(observed["exits"], [code])
            self.assertEqual(json.loads(observed["output"][0]), response)
