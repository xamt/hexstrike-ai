# steghide_analysis

## 用途（原始说明）

Execute Steghide for steganography analysis with enhanced logging.

Args:
    action: Action to perform (extract, embed, info)
    cover_file: Cover file for steganography
    embed_file: File to embed (for embed action)
    passphrase: Passphrase for steganography
    output_file: Output file path
    additional_args: Additional Steghide arguments

Returns:
    Steganography analysis results

## MCP 调用

通过宿主发现的 `steghide_analysis` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `action` | `str` | 是 | `—` |
| `cover_file` | `str` | 是 | `—` |
| `embed_file` | `str` | 否 | `""` |
| `passphrase` | `str` | 否 | `""` |
| `output_file` | `str` | 否 | `""` |
| `additional_args` | `str` | 否 | `""` |

## 维护来源

`tools/forensics.py:67`；由维护者离线导出，不要求技能使用者安装 Python。
