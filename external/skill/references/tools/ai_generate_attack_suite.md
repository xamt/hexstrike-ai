# ai_generate_attack_suite

## 用途（原始说明）

Generate comprehensive attack suite with multiple payload types.

Args:
    target_url: Target URL for testing
    attack_types: Comma-separated list of attack types

Returns:
    Comprehensive attack suite with multiple payload types

## MCP 调用

通过宿主发现的 `ai_generate_attack_suite` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `target_url` | `str` | 是 | `—` |
| `attack_types` | `str` | 否 | `"xss,sqli,lfi"` |

## 维护来源

`tools/ai_payloads.py:88`；由维护者离线导出，不要求技能使用者安装 Python。
