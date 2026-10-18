# bugbounty_comprehensive_assessment

## 用途（原始说明）

Create comprehensive bug bounty assessment combining all specialized workflows.

Args:
    domain: Target domain for bug bounty
    scope: Comma-separated list of in-scope domains/IPs
    priority_vulns: Comma-separated list of priority vulnerability types
    include_osint: Include OSINT gathering workflow
    include_business_logic: Include business logic testing workflow

Returns:
    Comprehensive bug bounty assessment with all workflows and summary

## MCP 调用

通过宿主发现的 `bugbounty_comprehensive_assessment` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `domain` | `str` | 是 | `—` |
| `scope` | `str` | 否 | `""` |
| `priority_vulns` | `str` | 否 | `"rce,sqli,xss,idor,ssrf"` |
| `include_osint` | `bool` | 否 | `true` |
| `include_business_logic` | `bool` | 否 | `true` |

## 维护来源

`tools/bugbounty.py:155`；由维护者离线导出，不要求技能使用者安装 Python。
