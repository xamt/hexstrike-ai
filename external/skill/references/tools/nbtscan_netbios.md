# nbtscan_netbios

## 用途（原始说明）

Execute nbtscan for NetBIOS name scanning with enhanced logging.

Args:
    target: The target IP address or range
    verbose: Enable verbose output
    timeout: Timeout in seconds
    additional_args: Additional nbtscan arguments

Returns:
    NetBIOS name scanning results

## MCP 调用

通过宿主发现的 `nbtscan_netbios` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `target` | `str` | 是 | `—` |
| `verbose` | `bool` | 否 | `false` |
| `timeout` | `int` | 否 | `2` |
| `additional_args` | `str` | 否 | `""` |

## 维护来源

`tools/network_discovery.py:240`；由维护者离线导出，不要求技能使用者安装 Python。
