"""静态读取真实 MCP 注册顺序；不导入服务或执行工具。"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "hexstrike_tools/__init__.py"


def source_paths():
    """依据实际注册入口解析源文件，拒绝无法识别的注册语句。"""
    module = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imports = {alias.asname or alias.name: item.module
               for item in module.body if isinstance(item, ast.ImportFrom)
               for alias in item.names}
    register = next(item for item in module.body if isinstance(item, ast.FunctionDef)
                    and item.name == "register_tools")
    paths = []
    for item in register.body:
        if isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant):
            continue
        if not (isinstance(item, ast.Expr) and isinstance(item.value, ast.Call)
                and isinstance(item.value.func, ast.Name) and item.value.func.id in imports):
            raise ValueError("MCP 注册入口变化，需要更新静态导出规则")
        paths.append(SOURCE.parent / (imports[item.value.func.id] + ".py"))
    return paths


def definitions():
    """与 MCP 一致：同名工具只保留首次注册，不生成额外别名。"""
    seen = set()
    result = []
    for path in source_paths():
        module = ast.parse(path.read_text(encoding="utf-8"))
        setup = next(n for n in module.body if isinstance(n, ast.FunctionDef)
                     and n.name == "register")
        for node in setup.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            if not any(ast.unparse(decorator) == "mcp.tool()" for decorator in node.decorator_list):
                continue
            if node.name in seen:
                continue
            seen.add(node.name)
            node.source_file = str(path.relative_to(ROOT))
            result.append(node)
    return result


def parameters(node):
    """记录声明类型和默认值，必填与默认 null 明确区分。"""
    if node.args.posonlyargs or node.args.kwonlyargs or node.args.vararg or node.args.kwarg:
        raise ValueError(f"工具 {node.name} 的参数形式变化，需要更新导出规则")
    optional = len(node.args.args) - len(node.args.defaults)
    result = {}
    for index, arg in enumerate(node.args.args):
        value = {"type": ast.unparse(arg.annotation), "required": index < optional}
        if index >= optional:
            value["default"] = ast.literal_eval(node.args.defaults[index - optional])
        result[arg.arg] = value
    return result
