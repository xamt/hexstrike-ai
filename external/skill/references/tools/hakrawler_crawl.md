# hakrawler_crawl

## 用途（原始说明）

Execute Hakrawler for web endpoint discovery with enhanced logging.

Note: Uses standard Kali Linux hakrawler (hakluke/hakrawler) with parameter mapping:
- url: Piped via echo to stdin (not -url flag)
- depth: Mapped to -d flag (not -depth)
- forms: Mapped to -s flag for showing sources
- robots/sitemap/wayback: Mapped to -subs for subdomain inclusion
- Always includes -u for unique URLs

Args:
    url: Target URL to crawl
    depth: Crawling depth (mapped to -d)
    forms: Include forms in crawling (mapped to -s)
    robots: Check robots.txt (mapped to -subs)
    sitemap: Check sitemap.xml (mapped to -subs)
    wayback: Use Wayback Machine (mapped to -subs)
    additional_args: Additional Hakrawler arguments

Returns:
    Web endpoint discovery results

## MCP 调用

通过宿主发现的 `hakrawler_crawl` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `url` | `str` | 是 | `—` |
| `depth` | `int` | 否 | `2` |
| `forms` | `bool` | 否 | `true` |
| `robots` | `bool` | 否 | `true` |
| `sitemap` | `bool` | 否 | `true` |
| `wayback` | `bool` | 否 | `false` |
| `additional_args` | `str` | 否 | `""` |

## 维护来源

`tools/web_scanners.py:11`；由维护者离线导出，不要求技能使用者安装 Python。
