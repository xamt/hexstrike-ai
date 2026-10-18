# ai_generate_payload

## 用途（原始说明）

Generate AI-powered contextual payloads for security testing.

Args:
    attack_type: Type of attack (xss, sqli, lfi, cmd_injection, ssti, xxe)
    complexity: Complexity level (basic, advanced, bypass)
    technology: Target technology (php, asp, jsp, python, nodejs)
    url: Target URL for context

Returns:
    Contextual payloads with risk assessment and test cases

## MCP 调用

通过宿主发现的 `ai_generate_payload` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `attack_type` | `str` | 是 | `—` |
| `complexity` | `str` | 否 | `"basic"` |
| `technology` | `str` | 否 | `""` |
| `url` | `str` | 否 | `""` |

## 维护来源

`tools/ai_payloads.py:12`；由维护者离线导出，不要求技能使用者安装 Python。
