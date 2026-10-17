# generate_payload

## 用途（原始说明）

Generate large payloads for testing and exploitation.

Args:
    payload_type: Type of payload (buffer, cyclic, random)
    size: Size of the payload in bytes
    pattern: Pattern to use for buffer payloads
    filename: Custom filename (auto-generated if empty)

Returns:
    Payload generation results

## MCP 调用

通过宿主发现的 `generate_payload` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `payload_type` | `str` | 否 | `"buffer"` |
| `size` | `int` | 否 | `1024` |
| `pattern` | `str` | 否 | `"A"` |
| `filename` | `str` | 否 | `""` |

## 维护来源

`tools/workspace.py:105`；由维护者离线导出，不要求技能使用者安装 Python。
