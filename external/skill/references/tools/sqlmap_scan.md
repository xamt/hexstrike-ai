# sqlmap_scan

## 用途（原始说明）

Execute SQLMap for SQL injection testing with enhanced logging.

Args:
    url: The target URL
    data: POST data for testing
    additional_args: Additional SQLMap arguments

Returns:
    SQL injection test results

## MCP 调用

通过宿主发现的 `sqlmap_scan` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `url` | `str` | 是 | `—` |
| `data` | `str` | 否 | `""` |
| `additional_args` | `str` | 否 | `""` |

## 维护来源

`tools/assessment.py:61`；由维护者离线导出，不要求技能使用者安装 Python。
