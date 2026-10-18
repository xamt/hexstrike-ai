# arjun_parameter_discovery

## 用途（原始说明）

Execute Arjun for HTTP parameter discovery with enhanced logging.

Args:
    url: The target URL
    method: HTTP method to use
    wordlist: Custom wordlist file
    delay: Delay between requests
    threads: Number of threads
    stable: Use stable mode
    additional_args: Additional Arjun arguments

Returns:
    HTTP parameter discovery results

## MCP 调用

通过宿主发现的 `arjun_parameter_discovery` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `url` | `str` | 是 | `—` |
| `method` | `str` | 否 | `"GET"` |
| `wordlist` | `str` | 否 | `""` |
| `delay` | `int` | 否 | `0` |
| `threads` | `int` | 否 | `25` |
| `stable` | `bool` | 否 | `false` |
| `additional_args` | `str` | 否 | `""` |

## 维护来源

`tools/web_discovery.py:246`；由维护者离线导出，不要求技能使用者安装 Python。
