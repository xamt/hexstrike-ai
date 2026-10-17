# create_scan_summary

## 用途（原始说明）

Create a comprehensive scan summary report with beautiful visual formatting.

Args:
    target: Target that was scanned
    tools_used: Comma-separated list of tools used
    vulnerabilities_found: Number of vulnerabilities discovered
    execution_time: Total execution time in seconds
    findings: Additional findings or notes

Returns:
    Beautiful scan summary report with visual enhancements

## MCP 调用

通过宿主发现的 `create_scan_summary` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `target` | `str` | 是 | `—` |
| `tools_used` | `str` | 是 | `—` |
| `vulnerabilities_found` | `int` | 否 | `0` |
| `execution_time` | `float` | 否 | `0.0` |
| `findings` | `str` | 否 | `""` |

## 维护来源

`tools/reporting.py:110`；由维护者离线导出，不要求技能使用者安装 Python。
