# netexec_scan

## 用途（原始说明）

Execute NetExec (formerly CrackMapExec) for network enumeration with enhanced logging.

Args:
    target: The target IP or network
    protocol: Protocol to use (smb, ssh, winrm, etc.)
    username: Username for authentication
    password: Password for authentication
    hash_value: Hash for pass-the-hash attacks
    module: NetExec module to execute
    additional_args: Additional NetExec arguments

Returns:
    Network enumeration results

## MCP 调用

通过宿主发现的 `netexec_scan` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `target` | `str` | 是 | `—` |
| `protocol` | `str` | 否 | `"smb"` |
| `username` | `str` | 否 | `""` |
| `password` | `str` | 否 | `""` |
| `hash_value` | `str` | 否 | `""` |
| `module` | `str` | 否 | `""` |
| `additional_args` | `str` | 否 | `""` |

## 维护来源

`tools/network_credentials.py:11`；由维护者离线导出，不要求技能使用者安装 Python。
