"""离线对照原 Python 工具行为；不导入第三方库，不访问 Docker 或网络。"""
import ast
import copy
import json
import subprocess
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/skill-export"))
from source import definitions, parameters, StripLogging, database_definitions


class MockClient:
    def __init__(self, response):
        self.calls = []
        self.response = response

    def safe_post(self, path, data):
        self.calls.append(["POST", path, copy.deepcopy(data)])
        return copy.deepcopy(self.response)

    def safe_get(self, path, params=None):
        self.calls.append(["GET", path, params or {}])
        return copy.deepcopy(self.response)

    def check_health(self):
        return self.safe_get("health")

    def execute_command(self, command, use_cache=True):
        return self.safe_post("api/command", {"command": command, "use_cache": use_cache})


def reference_functions(client):
    """隔离执行原函数，self 错误按已披露的同名工具引用修正。"""
    namespace = {
        "hexstrike_client": client,
        "time": types.SimpleNamespace(time=lambda: 1700000000),
        "datetime": types.SimpleNamespace(now=lambda: types.SimpleNamespace(isoformat=lambda: "2023-11-14T22:13:20")),
        "HexStrikeColors": types.SimpleNamespace(CRITICAL="", FIRE_RED="", CYBER_ORANGE="", YELLOW="", INFO=""),
    }
    for node in definitions():
        node = StripLogging().visit(node)
        node.decorator_list = []
        node.returns = None
        for arg in node.args.args:
            arg.annotation = None
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), "original-tool", "exec"), namespace)
    namespace["self"] = types.SimpleNamespace(**{n.name: namespace[n.name] for n in definitions()})
    return namespace


def inputs(node, full=False):
    """构造非扫描用的参数；只进入模拟客户端。"""
    special = {"vulnerabilities": '[{"severity":"high"}]', "context": '{"mode":"test"}',
               "indicators": " indicator-one, ,indicator-two ", "threat_indicators": "one,two",
               "attack_types": "xss,sqli", "endpoints": " /one, ,/two ",
               "target_environment": "windows", "depth": "deep", "focus_areas": "network"}
    result = {}
    for name, spec in parameters(node).items():
        if not spec["required"] and not full:
            continue
        value = {"str": "offline.example", "int": 2, "float": 1.5, "bool": False,
                 "list": [], "dict": {}, "Dict[str, Any]": {}}[spec["type"]]
        result[name] = special.get(name, value) if spec["type"] == "str" else value
    return result


class SkillParityTests(unittest.TestCase):
    def test_every_declaration_against_original(self):
        responses = [{}, {"success": False, "error": "模拟失败"}, {"success": True,
            "ai_payload_generation": {"payload_count": 2, "test_cases": [1], "payloads": [{"risk_level": "HIGH"}]},
            "schema_analysis_results": {"security_issues": [{}]},
            "jwt_analysis_results": {"vulnerabilities": [{}]},
            "graphql_scan_results": {"vulnerabilities": [{}]},
            "target_profile": {"target_type": "network_host"}, "cms_type": "WordPress"}]
        cases = []
        functions = reference_functions(MockClient({}))
        for node in definitions():
            for full in (False, True):
                for response in responses:
                    client = MockClient(response)
                    functions["hexstrike_client"] = client
                    args = inputs(node, full)
                    expected = functions[node.name](**args)
                    cases.append({"name": node.name, "args": args, "response": response,
                                  "expected": expected, "calls": client.calls})
        completed = subprocess.run(["node", str(ROOT / "tests/skill-parity.mjs")],
                                   input=json.dumps(cases), capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["checked"], 6 * len(definitions()))

    def test_database_routes_and_parameters(self):
        routes = {"mysql_query": "mysql", "clickhouse_query": "clickhouse",
                  "redis_command": "redis", "postgresql_query": "postgresql",
                  "mongodb_command": "mongodb"}
        nodes = database_definitions()
        self.assertEqual({n.name for n in nodes}, set(routes))
        for node in nodes:
            client = MockClient({"success": True})
            funcs = reference_functions(client)
            funcs[node.name](**inputs(node))
            self.assertEqual(client.calls[0][:2], ["POST", "api/tools/" + routes[node.name]])
            self.assertEqual(set(client.calls[0][2]), set(parameters(node)))
            self.assertTrue(parameters(node)["host"]["required"])

    def test_database_catalog_and_image_use_shared_contract(self):
        contract = json.loads((ROOT / "database_tools/contracts.json").read_text())
        catalog = json.loads((ROOT / "skills/pentest-tools/scripts/tools.json").read_text())
        for name, spec in contract.items():
            self.assertEqual(catalog[name]["parameters"], spec["parameters"])
            self.assertEqual(catalog[name]["sourceFile"], "database_tools/contracts.json")
        dockerfile = (ROOT / "Dockerfile").read_text()
        self.assertIn("COPY database_tools/ ./database_tools/", dockerfile)
        self.assertIn("compileall -q database_tools", dockerfile)

    def test_export_is_current(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/skill-export/export.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
