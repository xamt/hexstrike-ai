# comprehensive_api_audit

## 用途（原始说明）

Comprehensive API security audit combining multiple testing techniques.

Args:
    base_url: Base URL of the API
    schema_url: Optional API schema URL
    jwt_token: Optional JWT token for analysis
    graphql_endpoint: Optional GraphQL endpoint

Returns:
    Comprehensive audit results with all API security tests

## MCP 调用

通过宿主发现的 `comprehensive_api_audit` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `base_url` | `str` | 是 | `—` |
| `schema_url` | `str` | 否 | `""` |
| `jwt_token` | `str` | 否 | `""` |
| `graphql_endpoint` | `str` | 否 | `""` |

## 维护来源

`tools/api_security.py:174`；由维护者离线导出，不要求技能使用者安装 Python。
