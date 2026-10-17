"""不依赖 MCP SDK、网络和工具进程的完整工具迁移契约。"""
import ast
import hashlib
import inspect
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import register_tools

try:
    from mcp.server import MCPServer
except ImportError:
    MCPServer = None


class RecordingMCP:
    """记录每次声明，并模拟历史 MCP 的同名工具首次注册行为。"""

    def __init__(self):
        self.definitions = []
        self.tools = {}

    def tool(self):
        def register(function):
            self.definitions.append(function)
            self.tools.setdefault(function.__name__, function)
            return function
        return register


def registered(client=None):
    """只绑定客户端，不执行客户端或网络操作。"""
    recorder = RecordingMCP()
    register_tools(recorder, client if client is not None else Mock())
    return recorder


class CatalogContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = json.loads((ROOT / "tests/fixtures/mcp-tool-contract.json").read_text())

    def test_signatures_and_reviewed_tool_bodies_match_contract(self):
        # Nmap 的输入校验与禁重放行为有独立回归测试；其余工具维持迁移基线。
        catalog = registered()
        self.assertEqual(len(catalog.definitions), self.baseline["definition_count"])
        self.assertEqual(len(catalog.tools), self.baseline["unique_tool_count"])
        for function, expected in zip(catalog.definitions, self.baseline["definitions"]):
            with self.subTest(tool=function.__name__, line=expected["original_line"]):
                source = ast.parse(Path(inspect.getsourcefile(function)).read_text())
                node = next(n for n in ast.walk(source) if isinstance(n, ast.FunctionDef)
                            and n.name == function.__name__)
                self.assertEqual(node.name, expected["name"])
                self.assertEqual(ast.dump(node.args), expected["arguments_ast"])
                self.assertEqual(ast.dump(node.returns), expected["returns_ast"])
                self.assertEqual(ast.get_docstring(node, clean=False), expected["docstring"])
                body = ast.dump(ast.Module(body=node.body, type_ignores=[]))
                self.assertEqual(hashlib.sha256(body.encode()).hexdigest(), expected["body_sha256"])

    def test_duplicate_httpx_retains_original_registration_order(self):
        catalog = registered()
        definitions = [f for f in catalog.definitions if f.__name__ == "httpx_probe"]
        self.assertEqual(len(definitions), 2)
        self.assertIs(catalog.tools["httpx_probe"], definitions[0])
        self.assertNotEqual(inspect.signature(definitions[0]), inspect.signature(definitions[1]))

    def test_registration_performs_no_client_calls(self):
        client = Mock()
        registered(client)
        self.assertEqual(client.mock_calls, [])

    def test_client_bindings_are_independent_per_server(self):
        first, second = Mock(), Mock()
        first.safe_post.return_value = {"success": True}
        second.safe_post.return_value = {"success": True}
        left, right = registered(first), registered(second)
        left.tools["nmap_scan"]("first.invalid")
        right.tools["nmap_scan"]("second.invalid")
        self.assertEqual(first.safe_post.call_args.args[1]["target"], "first.invalid")
        self.assertEqual(second.safe_post.call_args.args[1]["target"], "second.invalid")
        self.assertEqual(first.safe_post.call_count, 1)
        self.assertEqual(second.safe_post.call_count, 1)

    def test_threat_hunting_keeps_cross_tool_closure(self):
        client = Mock()
        client.safe_post.return_value = {"success": True, "threat_intelligence": {"test": True}}
        result = registered(client).tools["threat_hunting_assistant"](
            "Windows Domain", "indicator.invalid", "apt")
        self.assertTrue(result["success"])
        self.assertEqual(result["hunting_playbook"]["threat_correlation"], {"test": True})
        self.assertEqual(client.safe_post.call_count, 1)


@unittest.skipIf(MCPServer is None, "需使用已安装 MCP SDK 的测试环境")
class SDKCatalogContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_sdk_lists_all_unique_tools_with_original_parameter_defaults(self):
        server = MCPServer("catalog-contract")
        register_tools(server, Mock())
        actual = await server.list_tools()
        original = registered().tools
        self.assertEqual(len(actual), 150)
        self.assertEqual({tool.name for tool in actual}, set(original))
        for tool in actual:
            with self.subTest(tool=tool.name):
                parameters = inspect.signature(original[tool.name]).parameters
                schema = tool.input_schema
                self.assertEqual(set(schema["properties"]), set(parameters))
                required = {name for name, parameter in parameters.items()
                            if parameter.default is inspect.Parameter.empty}
                self.assertEqual(set(schema.get("required", [])), required)
                for name, parameter in parameters.items():
                    if name not in required:
                        self.assertEqual(schema["properties"][name]["default"], parameter.default)


if __name__ == "__main__":
    unittest.main()
