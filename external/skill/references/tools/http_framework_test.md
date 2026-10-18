# http_framework_test

## 用途（原始说明）

Enhanced HTTP testing framework (Burp Suite alternative) for comprehensive web security testing.

Args:
    url: Target URL to test
    method: HTTP method (GET, POST, PUT, DELETE, etc.)
    data: Request data/parameters
    headers: Custom headers
    cookies: Custom cookies
    action: Action to perform (request, spider, proxy_history, set_rules, set_scope, repeater, intruder)

Returns:
    HTTP testing results with vulnerability analysis

## MCP 调用

通过宿主发现的 `http_framework_test` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `url` | `str` | 是 | `—` |
| `method` | `str` | 否 | `"GET"` |
| `data` | `dict` | 否 | `{}` |
| `headers` | `dict` | 否 | `{}` |
| `cookies` | `dict` | 否 | `{}` |
| `action` | `str` | 否 | `"request"` |

## 维护来源

`tools/http_testing.py:11`；由维护者离线导出，不要求技能使用者安装 Python。
