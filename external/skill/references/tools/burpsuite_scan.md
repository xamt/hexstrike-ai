# burpsuite_scan

## 用途（原始说明）

Execute Burp Suite with enhanced logging.

Args:
    project_file: Burp project file path
    config_file: Burp configuration file path
    target: Target URL
    headless: Run in headless mode
    scan_type: Type of scan to perform
    scan_config: Scan configuration
    output_file: Output file path
    additional_args: Additional Burp Suite arguments

Returns:
    Burp Suite scan results

## MCP 调用

通过宿主发现的 `burpsuite_scan` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `project_file` | `str` | 否 | `""` |
| `config_file` | `str` | 否 | `""` |
| `target` | `str` | 否 | `""` |
| `headless` | `bool` | 否 | `false` |
| `scan_type` | `str` | 否 | `""` |
| `scan_config` | `str` | 否 | `""` |
| `output_file` | `str` | 否 | `""` |
| `additional_args` | `str` | 否 | `""` |

## 维护来源

`tools/web_scanners.py:118`；由维护者离线导出，不要求技能使用者安装 Python。
