# gau_discovery

## 用途（原始说明）

Execute Gau (Get All URLs) for URL discovery from multiple sources with enhanced logging.

Args:
    domain: The target domain
    providers: Data providers to use
    include_subs: Include subdomains
    blacklist: File extensions to blacklist
    additional_args: Additional Gau arguments

Returns:
    Comprehensive URL discovery results from multiple sources

## MCP 调用

通过宿主发现的 `gau_discovery` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `domain` | `str` | 是 | `—` |
| `providers` | `str` | 否 | `"wayback,commoncrawl,otx,urlscan"` |
| `include_subs` | `bool` | 否 | `true` |
| `blacklist` | `str` | 否 | `"png,jpg,gif,jpeg,swf,woff,svg,pdf,css,ico"` |
| `additional_args` | `str` | 否 | `""` |

## 维护来源

`tools/web_discovery.py:185`；由维护者离线导出，不要求技能使用者安装 Python。
