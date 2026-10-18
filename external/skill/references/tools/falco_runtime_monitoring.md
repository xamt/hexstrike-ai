# falco_runtime_monitoring

## 用途（原始说明）

Execute Falco for runtime security monitoring.

Args:
    config_file: Falco configuration file
    rules_file: Custom rules file
    output_format: Output format (json, text)
    duration: Monitoring duration in seconds
    additional_args: Additional Falco arguments

Returns:
    Runtime security monitoring results

## MCP 调用

通过宿主发现的 `falco_runtime_monitoring` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `config_file` | `str` | 否 | `"/etc/falco/falco.yaml"` |
| `rules_file` | `str` | 否 | `""` |
| `output_format` | `str` | 否 | `"json"` |
| `duration` | `int` | 否 | `60` |
| `additional_args` | `str` | 否 | `""` |

## 维护来源

`tools/container_security.py:137`；由维护者离线导出，不要求技能使用者安装 Python。
