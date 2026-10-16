"""五项安全工具的技能导出与服务契约一致性，不发出网络请求。"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTES = {
    "testssl_scan": "testssl", "whatweb_scan": "whatweb",
    "jwt_tool_analyze": "jwt-tool", "trufflehog_scan": "trufflehog",
    "tcpdump_capture": "tcpdump",
}


class SecuritySkillTests(unittest.TestCase):
    def test_catalog_matches_server_contract(self):
        contracts = json.loads((ROOT / "security_tools/contracts.json").read_text())
        catalog = json.loads((ROOT / "skills/pentest-tools/scripts/tools.json").read_text())
        self.assertEqual(set(contracts), set(ROUTES))
        self.assertEqual(len(catalog), 161)
        for name, route in ROUTES.items():
            with self.subTest(name=name):
                self.assertEqual(contracts[name]["endpoint"], "api/tools/" + route)
                self.assertEqual(catalog[name]["parameters"], contracts[name]["parameters"])
                self.assertEqual(catalog[name]["sourceFile"], "security_tools/contracts.json")
                self.assertIn("api/tools/" + route, catalog[name]["calls"][0])

    def test_documented_entrypoints_have_real_references(self):
        index = (ROOT / "skills/pentest-tools/references/tools-index.md").read_text()
        for name in ROUTES:
            self.assertIn(f"tools/{name}.md", index)
            doc = ROOT / f"skills/pentest-tools/references/tools/{name}.md"
            self.assertIn("security_tools/contracts.json", doc.read_text())


if __name__ == "__main__":
    unittest.main()
