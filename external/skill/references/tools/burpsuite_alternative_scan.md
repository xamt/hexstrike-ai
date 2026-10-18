# burpsuite_alternative_scan

## 用途（原始说明）

Comprehensive Burp Suite alternative combining HTTP framework and browser agent for complete web security testing.

Args:
    target: Target URL or domain to scan
    scan_type: Type of scan (comprehensive, spider, passive, active)
    headless: Run browser in headless mode
    max_depth: Maximum crawling depth
    max_pages: Maximum pages to analyze

Returns:
    Comprehensive security assessment results

## MCP 调用

通过宿主发现的 `burpsuite_alternative_scan` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `target` | `str` | 是 | `—` |
| `scan_type` | `str` | 否 | `"comprehensive"` |
| `headless` | `bool` | 否 | `true` |
| `max_depth` | `int` | 否 | `3` |
| `max_pages` | `int` | 否 | `50` |

## 维护来源

`tools/http_testing.py:135`；由维护者离线导出，不要求技能使用者安装 Python。
