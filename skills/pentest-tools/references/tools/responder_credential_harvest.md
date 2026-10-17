# responder_credential_harvest

## 用途（原始说明）

Execute Responder for credential harvesting with enhanced logging.

Args:
    interface: Network interface to use
    analyze: Analyze mode only
    wpad: Enable WPAD rogue proxy
    force_wpad_auth: Force WPAD authentication
    fingerprint: Fingerprint mode
    duration: Duration to run in seconds
    additional_args: Additional Responder arguments

Returns:
    Credential harvesting results

## MCP 调用

通过宿主发现的 `responder_credential_harvest` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `interface` | `str` | 否 | `"eth0"` |
| `analyze` | `bool` | 否 | `false` |
| `wpad` | `bool` | 否 | `true` |
| `force_wpad_auth` | `bool` | 否 | `false` |
| `fingerprint` | `bool` | 否 | `false` |
| `duration` | `int` | 否 | `300` |
| `additional_args` | `str` | 否 | `""` |

## 维护来源

`tools/network_discovery.py:302`；由维护者离线导出，不要求技能使用者安装 Python。
