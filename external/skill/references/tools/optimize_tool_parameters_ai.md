# optimize_tool_parameters_ai

## 用途（原始说明）

Use AI to optimize tool parameters based on target profile and context.

Args:
    target: Target to test
    tool: Security tool to optimize
    context: JSON string with additional context (stealth, aggressive, etc.)

Returns:
    AI-optimized parameters for maximum effectiveness

## MCP 调用

通过宿主发现的 `optimize_tool_parameters_ai` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `target` | `str` | 是 | `—` |
| `tool` | `str` | 是 | `—` |
| `context` | `str` | 否 | `"{}"` |

## 维护来源

`tools/ai_workflows.py:64`；由维护者离线导出，不要求技能使用者安装 Python。
