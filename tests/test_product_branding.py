"""产品名称与兼容边界验收，不启动扫描器。"""

import ast
import contextlib
import io
import json
from pathlib import Path
import re
import sys
import unittest
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PRODUCT = "pentest-tools"


class ProductBrandingTests(unittest.TestCase):
    def test_readme_has_only_requested_sections(self):
        readme = (ROOT / "README.md").read_text()
        self.assertTrue(readme.startswith(f"# {PRODUCT}\n"))
        self.assertEqual(re.findall(r"^## (.+)$", readme, re.M), [
            "Installation", "AI Client Integration Setup", "Features",
            "API Reference", "Usage Examples",
        ])
        self.assertNotIn("github.com/0x4m4", readme)
        self.assertNotIn("assets/hexstrike", readme)
        self.assertLess(len(readme.splitlines()), 220)
        for block in re.findall(r"```json\n(.*?)\n```", readme, re.S):
            json.loads(block)

    def test_banner_and_dashboard_use_product_name(self):
        tree = ast.parse((ROOT / "server.py").read_text())
        visual = next(node for node in tree.body
                      if isinstance(node, ast.ClassDef) and node.name == "ModernVisualEngine")
        namespace = {"API_HOST": "127.0.0.1", "API_PORT": 8888, "Dict": Dict, "Any": Any}
        exec(compile(ast.Module(body=[visual], type_ignores=[]), "visual", "exec"), namespace)
        engine = namespace["ModernVisualEngine"]
        for output in (engine.create_banner(), engine.create_live_dashboard({}),
                       engine.create_live_dashboard({1: {"command": "example"}})):
            self.assertIn(PRODUCT, output)
            self.assertNotIn("hexstrike", output.lower())

    def test_health_message_uses_product_name(self):
        tree = ast.parse((ROOT / "server.py").read_text())
        messages = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant)
                    and isinstance(node.value, str) and "API Server is operational" in node.value]
        self.assertEqual(messages, [f"{PRODUCT} API Server is operational"])

    def test_http_cli_help_uses_product_name(self):
        from runtime.cli import parse_args
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            parse_args(["--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn(PRODUCT, output.getvalue())
        self.assertNotIn("stdio", output.getvalue())
        self.assertFalse(hasattr(parse_args([]), "transport"))

    def test_mcp_service_name(self):
        tree = ast.parse((ROOT / "runtime/server.py").read_text())
        names = [node.args[0].value for node in ast.walk(tree)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                 and node.func.attr == "__init__" and node.args
                 and isinstance(node.args[0], ast.Constant)]
        self.assertEqual(names, [PRODUCT])

    def test_sample_connects_to_http_without_spawning_process(self):
        config = json.loads((ROOT / "mcp-config.json").read_text())
        self.assertEqual(list(config["mcpServers"]), [PRODUCT])
        server = config["mcpServers"][PRODUCT]
        self.assertEqual(server, {"type": "http", "url": "http://127.0.0.1:8889/mcp"})
        self.assertNotIn("command", server)
        self.assertNotIn("args", server)
        readme = (ROOT / "README.md").read_text()
        examples = [json.loads(block) for block in re.findall(r"```json\n(.*?)\n```", readme, re.S)]
        self.assertIn(config, examples)

    def test_plugin_display_changes_without_identity_migration(self):
        plugin = json.loads((ROOT / "external/plugin/.dataagent-plugin/plugin.json").read_text())
        self.assertEqual(plugin["name"], "pentest-tools")
        self.assertIn(PRODUCT, plugin["description"])
        self.assertNotIn("userConfig", plugin)
        for path in ("external/plugin/ui/app.js", "external/skill/SKILL.md",
                     "external/skill/agents/openai.yaml"):
            with self.subTest(path=path):
                source = (ROOT / path).read_text()
                self.assertNotIn("HexStrike", source)
                self.assertIn(PRODUCT, source)


if __name__ == "__main__":
    unittest.main()
