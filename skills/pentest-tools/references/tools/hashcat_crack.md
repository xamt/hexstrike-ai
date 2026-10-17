# hashcat_crack

## 用途（原始说明）

Execute Hashcat for advanced password cracking with enhanced logging.

Args:
    hash_file: File containing password hashes
    hash_type: Hash type number for Hashcat
    attack_mode: Attack mode (0=dict, 1=combo, 3=mask, etc.)
    wordlist: Wordlist file for dictionary attacks
    mask: Mask for mask attacks
    additional_args: Additional Hashcat arguments

Returns:
    Password cracking results

## MCP 调用

通过宿主发现的 `hashcat_crack` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `hash_file` | `str` | 是 | `—` |
| `hash_type` | `str` | 是 | `—` |
| `attack_mode` | `str` | 否 | `"0"` |
| `wordlist` | `str` | 否 | `"/usr/share/wordlists/rockyou.txt"` |
| `mask` | `str` | 否 | `""` |
| `additional_args` | `str` | 否 | `""` |

## 维护来源

`tools/network_credentials.py:71`；由维护者离线导出，不要求技能使用者安装 Python。
