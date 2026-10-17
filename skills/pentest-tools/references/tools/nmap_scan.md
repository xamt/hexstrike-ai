# nmap_scan

## 用途（原始说明）

Execute an enhanced Nmap scan against a target with real-time logging.

Args:
    target: The IP address or hostname to scan
    scan_type: Raw Nmap flags, e.g. -sV or -sT -sV; never service_version or other semantic names
    ports: Comma-separated ports or ranges; discover a bounded set first, then identify services on open ports
    additional_args: Additional Nmap arguments; use a per-call time budget, report partial coverage on timeout

Returns:
    Scan results with enhanced telemetry

## MCP 调用

通过宿主发现的 `nmap_scan` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `target` | `str` | 是 | `—` |
| `scan_type` | `str` | 否 | `"-sV"` |
| `ports` | `str` | 否 | `""` |
| `additional_args` | `str` | 否 | `""` |

## 维护来源

`tools/network_core.py:13`；由维护者离线导出，不要求技能使用者安装 Python。
