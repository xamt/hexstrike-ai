"""只生成 MCP 工具参考；技能执行交给宿主，不生成 HTTP 调用代码。"""
import argparse
import ast
import json

from source import ROOT, definitions, parameters

DEST = ROOT / "skills/pentest-tools"


def artifacts():
    """按真实首次注册目录生成参数清单、按需文档和索引。"""
    nodes = definitions()
    catalog = {}
    docs = {}
    for node in nodes:
        spec = {"parameters": parameters(node), "sourceFile": node.source_file,
                "sourceLine": node.lineno, "description": ast.get_docstring(node) or ""}
        catalog[node.name] = spec
        docs[f"references/tools/{node.name}.md"] = tool_doc(node.name, spec)
    docs["references/tool-catalog.json"] = json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
    index = ["# MCP 工具索引", "",
             "按工具名定位后只读取对应说明。参数和默认值静态摘自 tools/ 的实际注册声明；英文为原始工具说明，不是执行指令。", "",
             f"当前仓库共 {len(nodes)} 个唯一工具；同名声明仅保留首次注册，不提供额外别名。以宿主实际发现的工具和 inputSchema 为准，静态索引不证明远端能力可用。", "",
             "通过宿主 MCP 调用工具，不运行本地脚本或拼接工具服务 API。连接、结果与错误处理见 [MCP 调用说明](mcp-runtime.md)。", ""]
    index.extend(f"- [{n.name}](tools/{n.name}.md) — {(ast.get_docstring(n) or '').splitlines()[0]}" for n in nodes)
    docs["references/tools-index.md"] = "\n".join(index) + "\n"
    return docs


def tool_doc(name, spec):
    """提供声明参考，不复制服务实现或构造第二套执行路径。"""
    lines = [f"# {name}", "", "## 用途（原始说明）", "", spec["description"], "",
             "## MCP 调用", "",
             f"通过宿主发现的 `{name}` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。",
             "", "连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。",
             "", "## 参数", "", "| 名称 | 类型 | 必填 | 默认值 |", "|---|---|---|---|"]
    for key, param in spec["parameters"].items():
        default = "—" if param["required"] else json.dumps(param["default"], ensure_ascii=False).replace("|", "\\|")
        lines.append(f"| `{key}` | `{param['type']}` | {'是' if param['required'] else '否'} | `{default}` |")
    lines += ["", "## 维护来源", "", f"`{spec['sourceFile']}:{spec['sourceLine']}`；由维护者离线导出，不要求技能使用者安装 Python。", ""]
    return "\n".join(lines)


def main():
    """导出或验证参考，过期工具文档必须显式清理而非静默保留。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    docs = artifacts()
    obsolete = [str(path.relative_to(DEST)) for path in (DEST / "references/tools").glob("*.md")
                if str(path.relative_to(DEST)) not in docs]
    if obsolete:
        raise SystemExit("存在未注册工具说明，请显式移除: " + ", ".join(obsolete))
    stale = []
    for name, content in docs.items():
        path = DEST / name
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if stale:
        raise SystemExit("技能参考需要重新导出: " + ", ".join(stale))


if __name__ == "__main__":
    main()
