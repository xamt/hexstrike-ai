# nmap_advanced_scan

## 用途（原始说明）

Execute advanced Nmap scans with custom NSE scripts and optimized timing.

Args:
    target: The target IP address or hostname
    scan_type: Nmap scan type (e.g., -sS, -sT, -sU)
    ports: Specific ports to scan
    timing: Timing template (T0-T5)
    nse_scripts: Custom NSE scripts to run
    os_detection: Enable OS detection
    version_detection: Enable version detection
    aggressive: Enable aggressive scanning
    stealth: Enable stealth mode
    additional_args: Additional Nmap arguments

Returns:
    Advanced Nmap scanning results with custom NSE scripts

## MCP 调用

通过宿主发现的 `nmap_advanced_scan` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `target` | `str` | 是 | `—` |
| `scan_type` | `str` | 否 | `"-sS"` |
| `ports` | `str` | 否 | `""` |
| `timing` | `str` | 否 | `"T4"` |
| `nse_scripts` | `str` | 否 | `""` |
| `os_detection` | `bool` | 否 | `false` |
| `version_detection` | `bool` | 否 | `false` |
| `aggressive` | `bool` | 否 | `false` |
| `stealth` | `bool` | 否 | `false` |
| `additional_args` | `str` | 否 | `""` |

## 维护来源

`tools/network_discovery.py:85`；由维护者离线导出，不要求技能使用者安装 Python。
