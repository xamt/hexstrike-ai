"""仅用内存注册器验证技能参考；不调用 MCP、HTTP 或扫描器。"""
import ast
import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/skill-export"))
sys.path.insert(0, str(ROOT))

from source import definitions, parameters
import export as skill_export
from tools import register_tools


class RecordingMCP:
    """与服务约定一致，同名工具仅保留首次注册。"""

    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(function):
            self.tools.setdefault(function.__name__, function)
            return function
        return register


class SkillCatalogTests(unittest.TestCase):
    def test_exported_contract_matches_registered_names_types_and_defaults(self):
        recorder, client = RecordingMCP(), Mock()
        register_tools(recorder, client)
        nodes = definitions()
        self.assertEqual([node.name for node in nodes], list(recorder.tools))
        self.assertEqual(len(nodes), 150)
        for node in nodes:
            with self.subTest(tool=node.name):
                function = recorder.tools[node.name]
                signature = inspect.signature(function)
                spec = parameters(node)
                self.assertEqual(list(spec), list(signature.parameters))
                for name, actual in signature.parameters.items():
                    self.assertEqual(spec[name]["required"], actual.default is inspect.Parameter.empty)
                    if actual.default is not inspect.Parameter.empty:
                        self.assertEqual(spec[name]["default"], actual.default)
                source = ast.parse(Path(inspect.getsourcefile(function)).read_text())
                expected = next(n for n in ast.walk(source)
                                if isinstance(n, ast.FunctionDef) and n.name == node.name)
                self.assertEqual(ast.dump(node.args), ast.dump(expected.args))
        self.assertEqual(client.mock_calls, [])

    def test_reference_manifest_and_documents_are_exactly_the_registered_tools(self):
        root = ROOT / "skills/pentest-tools"
        catalog = json.loads((root / "references/tool-catalog.json").read_text())
        expected = {node.name for node in definitions()}
        self.assertEqual(set(catalog), expected)
        self.assertEqual({path.stem for path in (root / "references/tools").glob("*.md")}, expected)
        self.assertIn("target", catalog["httpx_probe"]["parameters"])
        self.assertNotIn("targets", catalog["httpx_probe"]["parameters"])
        self.assertFalse((root / "scripts/run.mjs").exists())
        self.assertFalse((root / "scripts/http-client.mjs").exists())
        for name in ("mysql", "clickhouse", "redis", "postgresql", "mongodb"):
            self.assertNotIn(name, catalog)

    def test_generated_references_are_current(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/skill-export/export.py"), "--check"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_check_rejects_obsolete_tool_documents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "references/tools").mkdir(parents=True)
            (root / "references/tools/removed_tool.md").write_text("obsolete", encoding="utf-8")
            with patch.object(skill_export, "DEST", root), patch.object(sys, "argv", ["export", "--check"]):
                with self.assertRaisesRegex(SystemExit, "未注册工具说明"):
                    skill_export.main()

    def test_check_rejects_missing_or_changed_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(skill_export, "DEST", root), patch.object(sys, "argv", ["export", "--check"]):
                with self.assertRaisesRegex(SystemExit, "需要重新导出"):
                    skill_export.main()
                for name, content in skill_export.artifacts().items():
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding="utf-8")
                (root / "references/tools/httpx_probe.md").write_text("changed", encoding="utf-8")
                with self.assertRaisesRegex(SystemExit, "httpx_probe.md"):
                    skill_export.main()


if __name__ == "__main__":
    unittest.main()
