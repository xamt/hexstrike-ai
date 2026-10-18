# http_set_rules

## 用途（原始说明）

Set match/replace rules used to rewrite parts of URL/query/headers/body before sending.
Rule format: {'where':'url|query|headers|body','pattern':'regex','replacement':'string'}

## MCP 调用

通过宿主发现的 `http_set_rules` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `rules` | `list` | 是 | `—` |

## 维护来源

`tools/http_testing.py:99`；由维护者离线导出，不要求技能使用者安装 Python。
