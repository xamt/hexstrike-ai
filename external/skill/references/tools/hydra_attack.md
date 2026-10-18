# hydra_attack

## 用途（原始说明）

Execute Hydra for password brute forcing with enhanced logging.

Args:
    target: The target IP or hostname
    service: The service to attack (ssh, ftp, http, etc.)
    username: Single username to test
    username_file: File containing usernames
    password: Single password to test
    password_file: File containing passwords
    additional_args: Additional Hydra arguments

Returns:
    Brute force attack results

## MCP 调用

通过宿主发现的 `hydra_attack` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `target` | `str` | 是 | `—` |
| `service` | `str` | 是 | `—` |
| `username` | `str` | 否 | `""` |
| `username_file` | `str` | 否 | `""` |
| `password` | `str` | 否 | `""` |
| `password_file` | `str` | 否 | `""` |
| `additional_args` | `str` | 否 | `""` |

## 维护来源

`tools/assessment.py:111`；由维护者离线导出，不要求技能使用者安装 Python。
