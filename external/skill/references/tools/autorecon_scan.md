# autorecon_scan

## 用途（原始说明）

Execute AutoRecon for comprehensive target enumeration with full parameter support.

Args:
    target: Single target to scan
    target_file: File containing multiple targets
    ports: Specific ports to scan
    output_dir: Output directory
    max_scans: Maximum number of concurrent scans
    max_port_scans: Maximum number of concurrent port scans
    heartbeat: Heartbeat interval
    timeout: Global timeout
    target_timeout: Per-target timeout
    config_file: Configuration file path
    global_file: Global configuration file
    plugins_dir: Plugins directory
    add_plugins_dir: Additional plugins directory
    tags: Plugin tags to include
    exclude_tags: Plugin tags to exclude
    port_scans: Port scan plugins to run
    service_scans: Service scan plugins to run
    reports: Report plugins to run
    single_target: Use single target directory structure
    only_scans_dir: Only create scans directory
    no_port_dirs: Don't create port directories
    nmap: Custom nmap command
    nmap_append: Arguments to append to nmap
    proxychains: Use proxychains
    disable_sanity_checks: Disable sanity checks
    disable_keyboard_control: Disable keyboard control
    force_services: Force service detection
    accessible: Enable accessible output
    verbose: Verbosity level (0-3)
    curl_path: Custom curl path
    dirbuster_tool: Directory busting tool
    dirbuster_wordlist: Directory busting wordlist
    dirbuster_threads: Directory busting threads
    dirbuster_ext: Directory busting extensions
    onesixtyone_community_strings: SNMP community strings
    global_username_wordlist: Global username wordlist
    global_password_wordlist: Global password wordlist
    global_domain: Global domain
    additional_args: Additional AutoRecon arguments

Returns:
    Comprehensive enumeration results with full configurability

## MCP 调用

通过宿主发现的 `autorecon_scan` 工具调用；如宿主加了服务前缀，使用实际完整名称。先核对远端 inputSchema，以下是仓库声明参考，不替代运行时契约。

连接与结果判定见 [MCP 调用说明](../mcp-runtime.md)，既有实现限制见 [兼容说明](../compatibility.md)。

## 参数

| 名称 | 类型 | 必填 | 默认值 |
|---|---|---|---|
| `target` | `str` | 否 | `""` |
| `target_file` | `str` | 否 | `""` |
| `ports` | `str` | 否 | `""` |
| `output_dir` | `str` | 否 | `""` |
| `max_scans` | `str` | 否 | `""` |
| `max_port_scans` | `str` | 否 | `""` |
| `heartbeat` | `str` | 否 | `""` |
| `timeout` | `str` | 否 | `""` |
| `target_timeout` | `str` | 否 | `""` |
| `config_file` | `str` | 否 | `""` |
| `global_file` | `str` | 否 | `""` |
| `plugins_dir` | `str` | 否 | `""` |
| `add_plugins_dir` | `str` | 否 | `""` |
| `tags` | `str` | 否 | `""` |
| `exclude_tags` | `str` | 否 | `""` |
| `port_scans` | `str` | 否 | `""` |
| `service_scans` | `str` | 否 | `""` |
| `reports` | `str` | 否 | `""` |
| `single_target` | `bool` | 否 | `false` |
| `only_scans_dir` | `bool` | 否 | `false` |
| `no_port_dirs` | `bool` | 否 | `false` |
| `nmap` | `str` | 否 | `""` |
| `nmap_append` | `str` | 否 | `""` |
| `proxychains` | `bool` | 否 | `false` |
| `disable_sanity_checks` | `bool` | 否 | `false` |
| `disable_keyboard_control` | `bool` | 否 | `false` |
| `force_services` | `str` | 否 | `""` |
| `accessible` | `bool` | 否 | `false` |
| `verbose` | `int` | 否 | `0` |
| `curl_path` | `str` | 否 | `""` |
| `dirbuster_tool` | `str` | 否 | `""` |
| `dirbuster_wordlist` | `str` | 否 | `""` |
| `dirbuster_threads` | `str` | 否 | `""` |
| `dirbuster_ext` | `str` | 否 | `""` |
| `onesixtyone_community_strings` | `str` | 否 | `""` |
| `global_username_wordlist` | `str` | 否 | `""` |
| `global_password_wordlist` | `str` | 否 | `""` |
| `global_domain` | `str` | 否 | `""` |
| `additional_args` | `str` | 否 | `""` |

## 维护来源

`tools/autorecon.py:11`；由维护者离线导出，不要求技能使用者安装 Python。
