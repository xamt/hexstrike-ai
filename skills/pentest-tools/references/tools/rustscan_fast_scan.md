# rustscan_fast_scan

## 用途（原始说明）

Execute Rustscan for ultra-fast port scanning with enhanced logging.

Args:
    target: The target IP address or hostname
    ports: Specific ports to scan (e.g., "22,80,443")
    ulimit: File descriptor limit
    batch_size: Batch size for scanning
    timeout: Timeout in milliseconds
    scripts: Run Nmap scripts on discovered ports
    additional_args: Additional Rustscan arguments

Returns:
    Ultra-fast port scanning results

## MCP 调用

通过宿主发现的 `rustscan_fast_scan` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `target` | `str` | 是 | `—` |
| `ports` | `str` | 否 | `""` |
| `ulimit` | `int` | 否 | `5000` |
| `batch_size` | `int` | 否 | `4500` |
| `timeout` | `int` | 否 | `1500` |
| `scripts` | `bool` | 否 | `false` |
| `additional_args` | `str` | 否 | `""` |

## 维护来源

`tools/network_discovery.py:11`；由维护者离线导出，不要求技能使用者安装 Python。
