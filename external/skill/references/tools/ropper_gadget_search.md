# ropper_gadget_search

## 用途（原始说明）

Execute ropper for advanced ROP/JOP gadget searching.

Args:
    binary: Binary to search for gadgets
    gadget_type: Type of gadgets (rop, jop, sys, all)
    quality: Gadget quality level (1-5)
    arch: Target architecture (x86, x86_64, arm, etc.)
    search_string: Specific gadget pattern to search for
    additional_args: Additional ropper arguments

Returns:
    Advanced ROP/JOP gadget search results

## MCP 调用

通过宿主发现的 `ropper_gadget_search` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `binary` | `str` | 是 | `—` |
| `gadget_type` | `str` | 否 | `"rop"` |
| `quality` | `int` | 否 | `1` |
| `arch` | `str` | 否 | `""` |
| `search_string` | `str` | 否 | `""` |
| `additional_args` | `str` | 否 | `""` |

## 维护来源

`tools/exploit_development.py:199`；由维护者离线导出，不要求技能使用者安装 Python。
