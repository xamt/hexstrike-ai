"""仅读取原始工具声明；不导入 MCP、requests，也不运行服务。"""
import ast
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "hexstrike_mcp.py"
DATABASE_SOURCE = ROOT / "database_tools/contracts.json"
SECURITY_SOURCE = ROOT / "security_tools/contracts.json"


def database_definitions():
    """从服务端共享契约生成直接 POST 声明，不发出网络请求。"""
    return contract_definitions(DATABASE_SOURCE)


def security_definitions():
    """从五项安全工具契约生成声明，不导入或执行扫描工具。"""
    return contract_definitions(SECURITY_SOURCE)


def contract_definitions(path):
    """将共享 HTTP 契约转换成原工具导出器可处理的语法树。"""
    result = []
    contracts = json.loads(path.read_text(encoding="utf-8"))
    for name, spec in contracts.items():
        params = spec["parameters"]
        ordered = sorted(params, key=lambda key: not params[key]["required"])
        arguments = []
        for key in ordered:
            item = params[key]
            argument = f"{key}: {item['type']}"
            if not item["required"]:
                argument += f" = {item['default']!r}"
            arguments.append(argument)
        payload = ", ".join(f"{key!r}: {key}" for key in ordered)
        source = (f"def {name}({', '.join(arguments)}):\n"
                  f"    {spec['description']!r}\n"
                  f"    return hexstrike_client.safe_post({spec['endpoint']!r}, {{{payload}}})\n")
        node = ast.parse(source).body[0]
        node.source_file = str(path.relative_to(ROOT))
        result.append(node)
    return result


def definitions():
    """返回全部声明，重复 httpx 名称采用显式别名，不丢弃任何参数。"""
    module = ast.parse(SOURCE.read_text(encoding="utf-8"))
    setup = next(n for n in module.body if isinstance(n, ast.FunctionDef)
                 and n.name == "setup_mcp_server")
    seen = set()
    result = []
    for node in setup.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        node = copy.deepcopy(node)
        original = node.name
        if original in seen:
            if original != "httpx_probe":
                raise ValueError(f"未处理的重复工具: {original}")
            node.name = "httpx_probe_extended"
        seen.add(original)
        node.source_file = str(SOURCE.relative_to(ROOT))
        result.append(node)
    extra = database_definitions() + security_definitions()
    for node in extra:
        if node.name in seen:
            raise ValueError("共享契约工具名冲突: " + node.name)
        seen.add(node.name)
    return result + extra


class StripLogging(ast.NodeTransformer):
    """删除日志及仅供日志使用的计算，保留请求与返回副作用。"""

    def visit_Expr(self, node):
        if isinstance(node.value, ast.Constant):
            return None
        if isinstance(node.value, ast.Call) and ast.unparse(node.value.func).startswith("logger."):
            return None
        return self.generic_visit(node)

    def visit_If(self, node):
        self.generic_visit(node)
        if not node.body and not node.orelse:
            return None
        if not node.body:
            node.body = [ast.Pass()]
        return node

    def visit_For(self, node):
        self.generic_visit(node)
        return node if node.body else None


def executable(node):
    """提取可迁移行为；仅删除无副作用且无人引用的局部变量。"""
    node = StripLogging().visit(copy.deepcopy(node))
    node.decorator_list = []
    node.returns = None
    for arg in node.args.args:
        arg.annotation = None
    while True:
        before = ast.dump(node)
        reads = {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}

        class RemoveUnused(StripLogging):
            def visit_AugAssign(self, assignment):
                if isinstance(assignment.target, ast.Name) and assignment.target.id not in reads:
                    return None
                return assignment

            def visit_Assign(self, assignment):
                targets = assignment.targets
                calls = [ast.unparse(n.func) for n in ast.walk(assignment.value) if isinstance(n, ast.Call)]
                effect = any(c.startswith(("hexstrike_client.", "self."))
                             or c == "correlate_threat_intelligence" for c in calls)
                if all(isinstance(t, ast.Name) and t.id not in reads for t in targets) and not effect:
                    return None
                return assignment

        node = RemoveUnused().visit(node)
        if ast.dump(node) == before:
            return ast.fix_missing_locations(node)


def parameters(node):
    """记录原始类型与默认值，required 与默认 null 明确区分。"""
    optional = len(node.args.args) - len(node.args.defaults)
    result = {}
    for index, arg in enumerate(node.args.args):
        value = {"type": ast.unparse(arg.annotation), "required": index < optional}
        if index >= optional:
            value["default"] = ast.literal_eval(node.args.defaults[index - optional])
        result[arg.arg] = value
    return result
