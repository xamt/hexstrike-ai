# ropgadget_search

## 用途（原始说明）

Search for ROP gadgets in a binary using ROPgadget with enhanced logging.

Args:
    binary: Path to the binary file
    gadget_type: Type of gadgets to search for
    additional_args: Additional ROPgadget arguments

Returns:
    ROP gadget search results

## MCP 调用

通过宿主发现的 `ropgadget_search` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `binary` | `str` | 是 | `—` |
| `gadget_type` | `str` | 否 | `""` |
| `additional_args` | `str` | 否 | `""` |

## 维护来源

`tools/binary_analysis.py:91`；由维护者离线导出，不要求技能使用者安装 Python。
