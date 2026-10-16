"""生成独立技能产物；仅维护者需要 Python，使用技能无需 Python。"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

from source import ROOT, SOURCE, DATABASE_SOURCE, SECURITY_SOURCE, definitions, executable, parameters
from translate import Translator

DEST = ROOT / "skills/pentest-tools"


def artifacts():
    """生成代码、参数清单和按需阅读的原始工具说明。"""
    nodes = definitions()
    translator = Translator(n.name for n in nodes)
    digest = hashlib.sha256(SOURCE.read_bytes() + DATABASE_SOURCE.read_bytes()
                            + SECURITY_SOURCE.read_bytes()).hexdigest()
    catalog = {}
    functions = []
    docs = {}
    for node in nodes:
        cleaned = executable(node)
        functions.append(translator.function(cleaned))
        calls = [ast.unparse(n) for n in ast.walk(cleaned) if isinstance(n, ast.Call)
                 and ast.unparse(n.func).startswith(("hexstrike_client.", "self."))]
        catalog[node.name] = {"parameters": parameters(node),
                              "sourceLine": node.lineno if node.source_file == "hexstrike_mcp.py" else None,
                              "description": ast.get_docstring(node), "calls": calls}
        if node.source_file != "hexstrike_mcp.py":
            catalog[node.name]["sourceFile"] = node.source_file
        docs[f"references/tools/{node.name}.md"] = tool_doc(node, catalog[node.name])
    text = "// 自动生成；维护源为 hexstrike_mcp.py、database_tools/contracts.json 与 security_tools/contracts.json。不要手工修改。\n"
    text += f"// 源文件 SHA256: {digest}\nimport {{ py, defaultClock }} from './python-values.mjs';\n\n"
    text += "/** 构造兼容原工具调用的函数，不在初始化时发出网络请求。 */\n"
    text += "export function createTools(client, clock = defaultClock) {\n  const tools = Object.create(null);\n"
    text += "\n\n".join(functions) + "\n  return tools;\n}\n"
    docs["scripts/generated-tools.mjs"] = text
    docs["scripts/tools.json"] = json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
    index = ["# 工具索引", "", "按工具名定位后只读取对应说明。参数、默认值和调用转换均来自原脚本；说明中的英文为保留的原始工具文档。", "",
             f"{len(nodes)} 个入口：原脚本声明（含显式别名 `httpx_probe_extended`）、数据库与安全工具 HTTP 契约；按各条目的来源维护。", ""]
    index.extend(f"- [{n.name}](tools/{n.name}.md) — {(ast.get_docstring(n) or '').splitlines()[0]}" for n in nodes)
    docs["references/tools-index.md"] = "\n".join(index) + "\n"
    return docs


def tool_doc(node, spec):
    """把接口参数与实际调用转换并列，便于 Agent 按需核对。"""
    shared_contract = node.source_file != "hexstrike_mcp.py"
    lines = [f"# {node.name}", "", "## 用途（原始说明）", "", spec["description"], "",
             "## 参数", "", "| 名称 | 类型 | 必填 | 默认值 |", "|---|---|---|---|"]
    for name, param in spec["parameters"].items():
        default = "—" if param["required"] else json.dumps(param["default"], ensure_ascii=False).replace("|", "\\|")
        lines.append(f"| `{name}` | `{param['type']}` | {'是' if param['required'] else '否'} | `{default}` |")
    note = (f"维护来源：`{node.source_file}`；按共享 HTTP 契约直接 POST。以下为生成逻辑参考，不要用 Python 执行。"
            if shared_contract else "下列内容是维护参考，不要用 Python 执行。技能调用器已实现相同逻辑；删除的仅为日志和日志专用计算。")
    lines += ["", "## 调用逻辑参考", "", note, "", "```python", ast.unparse(executable(node)), "```", ""]
    return "\n".join(lines)


def main():
    """导出或只检查已提交产物，任何未支持语法直接失败。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = []
    for name, content in artifacts().items():
        path = DEST / name
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if stale:
        raise SystemExit("技能产物需要重新导出: " + ", ".join(stale))


if __name__ == "__main__":
    main()
