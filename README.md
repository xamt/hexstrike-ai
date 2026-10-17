# pentest-agent-tools

面向 AI Agent 的安全测试工具服务，提供 HTTP API、Streamable HTTP MCP 和 stdio 接入。

## Installation

### Docker 部署

完整的基础镜像、应用镜像构建及部署步骤见 [Docker 构建说明](docs/DOCKER_BUILD.md)。应用镜像同时启动以下接口：

| 接口 | 默认地址 |
| --- | --- |
| HTTP API | `http://127.0.0.1:8888` |
| MCP | `http://127.0.0.1:8889/mcp` |

### 本地安装与启动

在项目根目录执行以下命令。使用 Python 3.11+，API 与 MCP 必须安装到独立环境；本地双服务启动脚本支持 macOS/Linux。

```bash
python3 -m venv ".venv-api"
".venv-api/bin/python" -m pip install -r "requirements.txt"
python3 -m venv ".venv-mcp"
".venv-mcp/bin/python" -m pip install -r "requirements-mcp.txt"
python3 "scripts/start_local.py"
```

脚本默认只绑定回环地址，按 `Ctrl+C` 同时停止两个服务。自定义端口或解释器参数可通过 `python3 "scripts/start_local.py" --help` 查看。

Python 依赖不包含全部扫描器、字典和模板；本地运行须另行安装所需安全工具，完整工具环境优先使用 Docker。工具清单见 [构建说明](docs/DOCKER_BUILD.md)。

```bash
# 轻量联通检查，不执行目标扫描
curl --fail "http://127.0.0.1:8888/api/cache/stats"
curl --fail "http://127.0.0.1:8889/readyz"
```

当前接口不提供鉴权，HTTP API 与 MCP 都必须限制网络访问，远程访问通过受控网关接入。`/health` 会检测工具可用性，不适合高频轮询。

API 入口为 `server.py`，共用运行模块位于 `runtime/`，MCP 工具注册位于 `tools/`。项目启动脚本和 Docker 配置已同步；自定义 API 启动命令需改为 `python server.py`，自定义模块导入也需使用新包名。MCP 入口 `hexstrike_mcp.py`、`HEXSTRIKE_*` 环境变量及既有插件标识保持不变。

## AI Client Integration Setup

### Streamable HTTP

支持远程 MCP 的客户端填写以下连接信息；具体字段以客户端配置格式为准。

| 配置项 | 值 |
| --- | --- |
| 服务名称 | `pentest-agent-tools` |
| 传输方式 | `Streamable HTTP` |
| 服务 URL | `http://127.0.0.1:8889/mcp` |

远程客户端须将回环地址替换为可达的服务或网关地址，并在服务端设置 `HEXSTRIKE_MCP_ALLOWED_HOSTS`。这不是旧版 HTTP+SSE，也不需要配置本地启动命令。详细连接、网关与协议说明见 [接口文档](docs/MCP_HTTP.md)。

### stdio

只支持 stdio 的客户端可使用下列配置。先启动 HTTP API，再将示例路径替换为实际项目绝对路径；MCP 使用独立环境的 Python。

```json
{
  "mcpServers": {
    "pentest-agent-tools": {
      "command": "/path/to/pentest-agent-tools/.venv-mcp/bin/python",
      "args": [
        "/path/to/pentest-agent-tools/hexstrike_mcp.py",
        "--server",
        "http://127.0.0.1:8888"
      ]
    }
  }
}
```

默认传输仍为 stdio。兼容入口的配置示例见 [MCP 配置](hexstrike-ai-mcp.json)。DataAgent 可安装 [渗透测试工作台插件](plugins/pentest-tools/README.md)，复用远端 MCP、技能及进度/报告面板，避免重复建立同一服务连接。

## Features

- **网络与资产发现**：Nmap、Masscan、RustScan、Amass、Subfinder、AutoRecon。
- **Web 与 API 测试**：目录发现、模板检测、SQL 注入、XSS、JWT、GraphQL 与接口结构分析。
- **云与容器检查**：Prowler、Scout Suite、Trivy、Kube-Hunter、Kube-Bench。
- **二进制与取证分析**：GDB、Ghidra、Radare2、Pwntools、Angr、Volatility。
- **测试辅助工作流**：目标分析、工具选择、参数优化、漏洞情报及报告辅助。
- **运行管理**：执行状态、进程管理、缓存、遥测及错误恢复。

当前 MCP 注册 150 个唯一工具名称；实际能力取决于已安装的工具、运行权限及目标环境。完整名称和参数见 [工具索引](skills/pentest-tools/references/tools-index.md)，调用时以 `tools/list` 返回的 Schema 为准。

## API Reference

HTTP API 默认地址为 `http://127.0.0.1:8888`；POST 请求使用 JSON 请求体。

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/health` | 服务状态及工具可用性检查 |
| GET | `/api/telemetry` | 运行遥测 |
| GET | `/api/cache/stats` | 缓存统计及轻量联通检查 |
| POST | `/api/command` | 执行命令 |
| POST | `/api/tools/nmap` | Nmap 扫描 |
| POST | `/api/intelligence/analyze-target` | 目标分析 |
| POST | `/api/intelligence/select-tools` | 工具选择 |
| POST | `/api/intelligence/optimize-parameters` | 参数优化 |
| GET | `/api/processes/list` | 已登记进程列表 |
| GET | `/api/processes/status/<pid>` | 进程状态 |
| POST | `/api/processes/terminate/<pid>` | 终止指定进程 |
| GET | `/api/processes/dashboard` | 进程概览 |

MCP 端口默认是 `8889`，消息统一发送到 `/mcp`；`/healthz` 检查 MCP 存活，`/readyz` 检查后端连通。

| 类别 | 常用 MCP 工具 |
| --- | --- |
| 网络 | `nmap_scan`、`rustscan_fast_scan`、`masscan_high_speed`、`amass_scan` |
| Web | `gobuster_scan`、`feroxbuster_scan`、`ffuf_scan`、`nuclei_scan`、`sqlmap_scan` |
| 二进制 | `ghidra_analysis`、`radare2_analyze`、`gdb_analyze`、`angr_symbolic_execution` |
| 云与容器 | `prowler_scan`、`scout_suite_assessment`、`trivy_scan`、`kube_bench_cis` |
| 运维 | `get_cache_stats`、`server_health`、`list_active_processes`、`get_process_status` |

完整路由、参数及响应约定见 [HTTP API 与 MCP 接口文档](docs/MCP_HTTP.md)。HTTP 与 MCP 默认参数不保证一致。HTTP 200 不等于工具执行成功；调用方还需检查 `success`、`error`、`timed_out`、`return_code` 或 MCP 的 `isError`。超时或断连后不要自动重复提交有副作用的操作。

## Usage Examples

### Agent 调用

```text
使用 pentest-agent-tools 对已授权测试目标 192.0.2.10 的 80、443 端口进行服务识别。
先确认 MCP 连接和工具参数，只执行本次端口识别，整理结果及未验证项。
```

首次连接可先调用无参数的 `get_cache_stats`，不执行目标扫描。下面是 `nmap_scan` 的参数示例：

```json
{
  "target": "192.0.2.10",
  "scan_type": "-sV",
  "ports": "80,443",
  "additional_args": ""
}
```

### HTTP API 调用

将文档示例地址替换为实际测试目标后执行：

```bash
curl --fail "http://127.0.0.1:8888/api/tools/nmap" \
  -H "Content-Type: application/json" \
  --data '{"target":"192.0.2.10","scan_type":"-sV","ports":"80,443","additional_args":"","use_recovery":false}'
```
