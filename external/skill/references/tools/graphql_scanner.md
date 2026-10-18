# graphql_scanner

## 用途（原始说明）

Advanced GraphQL security scanning and introspection.

Args:
    endpoint: GraphQL endpoint URL
    introspection: Test introspection queries
    query_depth: Maximum query depth to test
    test_mutations: Test mutation operations

Returns:
    GraphQL security scan results with vulnerability assessment

## MCP 调用

通过宿主发现的 `graphql_scanner` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `endpoint` | `str` | 是 | `—` |
| `introspection` | `bool` | 否 | `true` |
| `query_depth` | `int` | 否 | `10` |
| `test_mutations` | `bool` | 否 | `true` |

## 维护来源

`tools/api_security.py:48`；由维护者离线导出，不要求技能使用者安装 Python。
