"""单镜像双接口部署契约，不运行扫描。"""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DualServiceDockerTests(unittest.TestCase):
    def test_product_workdir_and_entrypoints(self):
        for name in ("Dockerfile", "Dockerfile.base"):
            content = (ROOT / name).read_text()
            self.assertIn("WORKDIR /opt/pentest-tools\n", content)
            self.assertNotIn("/opt/hexstrike/", content)
        dockerfile = (ROOT / "Dockerfile").read_text()
        for name in ("service_manager.py", "service_health.py"):
            self.assertIn(f'"/opt/pentest-tools/docker/{name}"', dockerfile)

    def test_independent_dependency_environments(self):
        dockerfile = (ROOT / "Dockerfile").read_text()
        self.assertIn("/opt/pentest-tools-mcp-venv", dockerfile)
        self.assertIn("install -r requirements-mcp.txt", dockerfile)
        self.assertIn("/opt/pentest-tools-mcp-venv/bin/python check", dockerfile)
        self.assertIn("mcp==2.3.0", (ROOT / "requirements-mcp.txt").read_text())
        self.assertNotIn("fastmcp", (ROOT / "requirements.txt").read_text())

    def test_both_ports_and_managed_entrypoint(self):
        dockerfile = (ROOT / "Dockerfile").read_text()
        self.assertIn("EXPOSE 8888 8889", dockerfile)
        self.assertIn('ENTRYPOINT ["/usr/bin/tini", "--"]', dockerfile)
        self.assertIn('CMD ["/opt/pentest-tools-venv/bin/python", "/opt/pentest-tools/docker/service_manager.py"]', dockerfile)
        self.assertIn("service_health.py", dockerfile)
        self.assertNotIn("PENTEST_TOOLS_MCP_PORT=", dockerfile)

    def test_shared_tool_modules_are_packaged(self):
        dockerfile = (ROOT / "Dockerfile").read_text()
        self.assertIn("COPY tools/ ./tools/", dockerfile)
        self.assertIn("COPY runtime/ ./runtime/", dockerfile)

    def test_api_probe_uses_readonly_stats_without_tool_execution(self):
        tree = ast.parse((ROOT / "server.py").read_text())
        endpoint = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == "cache_stats")
        calls = {ast.unparse(node.func) for node in ast.walk(endpoint)
                 if isinstance(node, ast.Call)}
        self.assertEqual({"app.route", "jsonify", "cache.get_stats"}, calls)
        self.assertIn("/api/cache/stats", ast.unparse(endpoint))
        for filename in ("service_health.py", "service_manager.py"):
            self.assertNotIn('/health"', (ROOT / "docker" / filename).read_text())


if __name__ == "__main__":
    unittest.main()
