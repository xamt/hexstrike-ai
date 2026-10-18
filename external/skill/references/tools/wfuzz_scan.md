# wfuzz_scan

## 用途（原始说明）

Execute Wfuzz for web application fuzzing with enhanced logging.

Args:
    url: The target URL (use FUZZ where you want to inject payloads)
    wordlist: Wordlist file to use
    additional_args: Additional Wfuzz arguments

Returns:
    Web application fuzzing results

## MCP 调用

通过宿主发现的 `wfuzz_scan` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `url` | `str` | 是 | `—` |
| `wordlist` | `str` | 否 | `"/usr/share/wordlists/dirb/common.txt"` |
| `additional_args` | `str` | 否 | `""` |

## 维护来源

`tools/web_discovery.py:91`；由维护者离线导出，不要求技能使用者安装 Python。
