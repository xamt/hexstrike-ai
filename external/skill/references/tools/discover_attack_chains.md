# discover_attack_chains

## 用途（原始说明）

Discover multi-stage attack chains for target software with vulnerability correlation.

Args:
    target_software: Target software/system (e.g., "Apache HTTP Server", "Windows Server 2019")
    attack_depth: Maximum number of stages in attack chain (1-5)
    include_zero_days: Include potential zero-day vulnerabilities in analysis

Returns:
    Attack chains with vulnerability combinations, success probabilities, and exploit availability

Example:
    discover_attack_chains("Apache HTTP Server 2.4", 4, True)

## MCP 调用

通过宿主发现的 `discover_attack_chains` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `target_software` | `str` | 是 | `—` |
| `attack_depth` | `int` | 否 | `3` |
| `include_zero_days` | `bool` | 否 | `false` |

## 维护来源

`tools/threat_research.py:81`；由维护者离线导出，不要求技能使用者安装 Python。
