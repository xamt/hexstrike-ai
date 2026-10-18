# scout_suite_assessment

## 用途（原始说明）

Execute Scout Suite for multi-cloud security assessment.

Args:
    provider: Cloud provider (aws, azure, gcp, aliyun, oci)
    profile: AWS profile to use
    report_dir: Directory to save reports
    services: Specific services to assess
    exceptions: Exceptions file path
    additional_args: Additional Scout Suite arguments

Returns:
    Multi-cloud security assessment results

## MCP 调用

通过宿主发现的 `scout_suite_assessment` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `provider` | `str` | 否 | `"aws"` |
| `profile` | `str` | 否 | `"default"` |
| `report_dir` | `str` | 否 | `"/tmp/scout-suite"` |
| `services` | `str` | 否 | `""` |
| `exceptions` | `str` | 否 | `""` |
| `additional_args` | `str` | 否 | `""` |

## 维护来源

`tools/cloud_security.py:77`；由维护者离线导出，不要求技能使用者安装 Python。
