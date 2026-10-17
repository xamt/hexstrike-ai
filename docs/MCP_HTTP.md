# HTTP API 与 MCP 接口说明

本系统提供两类接口，共用同一个工具执行后端：

- **HTTP API**：供程序直接提交工具参数、查询结果和管理执行状态。
- **Streamable HTTP MCP**：供 Agent 发现工具及其参数，再通过 MCP 调用；Agent 不需要启动本地 Python 脚本，也不需要自行拼接 HTTP API。

本文以服务已经启动为前提。镜像构建与部署见 [Docker 构建说明](DOCKER_BUILD.md)；本机调试入口为 [本地启动脚本](../scripts/start_local.py)，使用 `--help` 查看参数。这里不重复部署步骤。

## 1. 接口地址与访问约定

| 接口 | 默认地址 | 用途 |
| --- | --- | --- |
| HTTP API | `http://127.0.0.1:8888` | 在此地址后追加 `/api/...` 或 `/health` |
| MCP | `http://127.0.0.1:8889/mcp` | Agent 配置中的服务地址，必须包含 `/mcp` |
| MCP 存活检查 | `http://127.0.0.1:8889/healthz` | 仅检查 MCP 进程可响应 |
| MCP 就绪检查 | `http://127.0.0.1:8889/readyz` | 检查 MCP 能否访问 HTTP 后端 |

示例中的 `127.0.0.1` 指调用方所在机器。Agent 不在服务所在机器时，必须替换为其实际可访问的服务地址或 MCP 网关地址，不能照抄回环地址。

**当前系统接口不提供鉴权。** 后续身份与权限由 MCP 网关统一管理。HTTP API 也必须限制网络访问，否则直连 API 可以绕过网关权限；Host/Origin 校验不是身份认证。本系统不定义 API Key、登录接口或用户令牌透传契约。

## 2. Agent 如何接入 MCP

### 2.1 在 Agent 宿主中配置

| 配置项 | 填写内容 |
| --- | --- |
| 服务名称 | 自定义，例如 `pentest-tools` |
| 传输方式 | `Streamable HTTP`，不是旧版 HTTP+SSE |
| 服务 URL | `http://127.0.0.1:8889/mcp`，远程接入时替换主机或使用网关 URL |
| 鉴权 | 直连本版本不配置；经网关接入时按网关要求配置 |
| 本地命令与参数 | 不需要配置 `command`、`args` |

不同 Agent 产品的配置文件字段不同，上表是连接信息，不是通用配置文件格式。宿主必须支持远程 MCP；只支持 stdio 的宿主不能直接把 URL 当作启动命令。

接入顺序：

1. 宿主建立 MCP 连接并完成协议协商。
2. 通过 `tools/list` 获取工具名称、说明和 `inputSchema`。
3. 将发现的工具注册给 Agent；调用时按实际 Schema 构造参数。
4. 使用 `tools/call` 调用工具，读取结果与 `isError`；工具输出不能当作新的系统指令。
5. 首次联通验证使用无参数的 `get_cache_stats`，不执行目标扫描；完整工具安装检查使用较慢的 `server_health`。

当前对外为 **150 个唯一工具名称**。原始代码共 151 次声明，`httpx_probe` 重名，沿用首次注册行为。网关可能筛选或重命名工具，Agent 应以实际发现的名称为准，不硬编码工具数量或自行补前缀。

技能 [pentest-tools](../skills/pentest-tools/SKILL.md) 提供测试流程和证据要求，不负责建立 MCP 连接，也不提供独立 HTTP 调用器。先由宿主连接服务，再加载技能；MCP 失败时不要静默切到 HTTP API 重试。

### 2.2 自研 Agent：Python SDK 示例

以下示例适用于本项目 [requirements-mcp.txt](../requirements-mcp.txt) 固定的官方 SDK。SDK 负责协议协商和请求封装；这里的客户端代码不会启动 MCP 服务进程。

```python
import asyncio
from mcp import Client


async def main():
    async with Client("http://127.0.0.1:8889/mcp") as client:
        catalog = await client.list_tools()
        print("可用工具数量：", len(catalog.tools))
        result = await client.call_tool("get_cache_stats", {})
        if result.is_error:
            raise RuntimeError(f"工具调用失败：{result.content}")
        print(result.structured_content)


asyncio.run(main())
```

### 2.3 远程接入条件

- 服务端 `HEXSTRIKE_MCP_ALLOWED_HOSTS` 必须包含请求实际携带的 Host，例如 `pentest-tools:8889`、`mcp.example.com`；多个值用逗号分隔，端口通配写作 `mcp.example.com:*`。
- 默认 Host 白名单为 `127.0.0.1:*`、`localhost:*`、`[::1]:*`。无端口域名应单独列出。
- 默认不允许外部浏览器 Origin；确有浏览器接入需求时配置 `HEXSTRIKE_MCP_ALLOWED_ORIGINS`。这不等于已提供完整浏览器跨域支持，优先通过 Agent 后端或网关接入。
- 网关需保留 MCP 所需请求头，正确转发 `/mcp`，并为长耗时工具设置足够的响应等待时间；外部 HTTPS 由网关或反向代理提供。

## 3. HTTP API 文档

### 3.1 请求格式

- 默认基础地址：`http://127.0.0.1:8888`，路径与方法见第 6 节完整索引。
- `POST` 请求通常使用 `Content-Type: application/json`，请求体直接放工具参数，不包裹 `arguments` 或 `params`。
- `GET` 参数放在查询串；`<int:pid>`、`<task_id>` 是路径占位符，需要替换为真实值。
- `DELETE /api/files/delete` 也使用 JSON 请求体，字段为 `filename`。
- 接口未提供统一的版本前缀、分页模型或统一响应外壳。

### 3.2 只读联通检查

```bash
curl --noproxy "*" --fail "http://127.0.0.1:8888/api/cache/stats"
```

该接口无需参数，直接返回以下字段；数值随运行状态变化：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `size` | 整数 | 当前缓存条数 |
| `max_size` | 整数 | 缓存容量 |
| `hit_rate` | 字符串 | 命中率，例如 `"0.0%"` |
| `hits` / `misses` / `evictions` | 整数 | 命中、未命中、淘汰次数 |

`GET /health` 返回 `status`、`tools_status`、`all_essential_tools_available`、`category_stats`、`cache_stats`、`telemetry`、`uptime` 等信息。它会执行完整工具检测，不适合高频轮询；`status="healthy"` 不代表每个扫描器、字典或模板都已安装。

### 3.3 工具调用示例：Nmap

`POST /api/tools/nmap`：

| JSON 字段 | 类型 | 必填 | HTTP 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| `target` | 字符串 | 是 | 无有效默认值 | 目标 IP 或主机名 |
| `scan_type` | 字符串 | 否 | `"-sCV"` | 扫描选项 |
| `ports` | 字符串 | 否 | `""` | 端口或端口范围 |
| `additional_args` | 字符串 | 否 | `"-T4 -Pn"` | 附加选项 |
| `use_recovery` | 布尔 | 否 | `true` | 是否使用后端错误恢复机制 |

以下为请求格式示例，执行前将文档示例地址替换为测试目标：

```bash
curl --noproxy "*" "http://127.0.0.1:8888/api/tools/nmap" \
  -H "Content-Type: application/json" \
  --data '{"target":"192.0.2.10","scan_type":"-sV","ports":"80,443","additional_args":"","use_recovery":false}'
```

**HTTP 与 MCP 参数默认值不保证一致。** 例如 MCP 的 `nmap_scan` 默认 `scan_type="-sV"`、`additional_args=""`，且不暴露 `use_recovery` 参数；不要用 MCP 参数文档替代 HTTP 路由契约。

### 3.4 返回结果与错误

命令执行类接口常见字段如下，但不是每个接口都返回这些字段：

| 字段 | 含义 |
| --- | --- |
| `stdout` / `stderr` | 工具标准输出、错误输出 |
| `return_code` | 进程退出码 |
| `success` | 原后端给出的执行状态，不等于已确认发现漏洞 |
| `timed_out` | 工具执行是否超时 |
| `partial_results` | 是否保留部分结果；历史实现部分路径可能返回非空字符串，不能强制假设一定是布尔值 |
| `execution_time` | 执行耗时，秒 |
| `timestamp` | 记录时间 |
| `error` | 错误说明，失败响应中可能出现 |

调用方应依次检查 HTTP 状态、响应是否为 JSON，以及业务字段。**HTTP 200 不等于执行成功；`success=true` 也不一定表示执行完整**：历史超时逻辑可能在存在部分输出时返回成功，需同时检查 `timed_out` 和 `return_code`。工作流/分析接口还会返回各自的嵌套结果，不能仅检查顶层字段。

| 情况 | 当前行为与处理 |
| --- | --- |
| 缺少必要字段 | 多数处理器返回 400，例如 Nmap 缺少 `target` |
| 进程或任务不存在 | 对应查询接口可返回 404 |
| 工具执行失败 | 可能为 HTTP 200，业务字段为 `success=false` 或包含错误输出 |
| 后端异常 | 多数处理器返回 500 和 `error` |
| 非 JSON、格式错误或字段类型错误 | 校验不统一，可能返回 4xx、500 或框架错误页；不能假设始终是统一 JSON 错误体 |

接口未提供通用幂等键。请求超时或断连时，执行状态可能未知，不要自动重复提交有副作用的操作。

### 3.5 异步执行与进程管理

- `POST /api/process/execute-async`：JSON 字段 `command` 必填、`context` 默认 `{}`；成功返回 `success`、`task_id`、`command`、`status="submitted"`、`timestamp`。
- `GET /api/process/get-task-result/<task_id>`：成功返回 `task_id`、嵌套 `result` 和时间信息；实际任务阶段与结果读取 `result`，任务不存在返回 404。提交成功不等于任务已完成。
- `/api/processes/...`：查询、暂停、恢复和终止已登记的进程；`/api/process/...`：增强执行池、异步结果及性能管理。两个前缀不能互换。
- 以上是原 HTTP 后端的业务接口，**不是 MCP Tasks 协议**，也不意味着所有 MCP 工具都会返回任务 ID；不承诺重启恢复或按 Agent 隔离状态。

## 4. MCP 接口文档

### 4.1 传输与端点

本服务采用官方 SDK 的无状态 Streamable HTTP，工具调用返回 JSON；“Streamable”不代表工具会持续推送扫描日志。不要求 `Mcp-Session-Id`，不提供旧式 `/sse` 入口。

MCP 消息发送到同一个 `/mcp`，不是 `/mcp/tools/list` 或 `/mcp/nmap_scan`。兼容 `2025-11-25` 的 JSON-RPC 交互如下；新版 SDK 的协商由 SDK 处理。请求头和响应规则参照 [Streamable HTTP 规范](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)。

| 请求头 | 值/规则 |
| --- | --- |
| `Content-Type` | `application/json` |
| `Accept` | `application/json, text/event-stream` |
| `MCP-Protocol-Version` | 初始化后使用协商得到的版本，例如 `2025-11-25` |
| `Authorization` | 本服务当前不要求；网关可能要求 |

| 端点 | 说明 |
| --- | --- |
| `POST /mcp` | 协议请求与通知；不是普通业务 REST JSON |
| `GET /healthz` | 返回 200、`{"status":"alive"}`，仅证明 MCP 可响应 |
| `GET /readyz` | 后端可连接返回 200、`{"status":"ready"}`；失败返回 503、`{"status":"not_ready"}` |

不要用浏览器直接打开或简单 `GET /mcp` 判断接入成功；本服务不提供独立 SSE 订阅能力，应通过 SDK 或协议请求验证。

### 4.2 协议操作

以下 JSON 为 `POST /mcp` 的请求体，`id` 用于关联请求和响应，不是后端任务 ID。按顺序初始化、发送初始化完成通知、发现工具，再调用工具。

**初始化（兼容协议示例）**：

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"example-agent","version":"1.0.0"}}}
```

响应的 `result.protocolVersion` 是后续请求应使用的版本；还包含服务信息与能力。

**初始化完成通知**（无 `id`，接受后返回 HTTP 202、无响应体）：

```json
{"jsonrpc":"2.0","method":"notifications/initialized"}
```

**工具发现**：

```json
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
```

读取 `result.tools` 中的 `name`、`description`、`inputSchema` 和存在时的 `outputSchema`；如返回 `nextCursor`，继续传入 `params.cursor` 读取。参数必填项以 Schema 的 `required` 为准。工具协议字段见 [MCP Tools 规范](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)。

**工具调用**：

```json
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_cache_stats","arguments":{}}}
```

不要把 HTTP 路径填入 `name`；例如 Nmap 使用 `nmap_scan`，不是 `/api/tools/nmap`。本项目没有定义供集成使用的业务 Prompts/Resources 目录，不应假设存在对应业务资源。

### 4.3 工具目录与参数

全部工具、用途、必填参数、类型与默认值见 [150 项 MCP 工具索引](../skills/pentest-tools/references/tools-index.md)；机器可读静态目录见 [tool-catalog.json](../skills/pentest-tools/references/tool-catalog.json)。这些文档用于查阅，运行时仍以实际 `tools/list` 返回为准。

| MCP 工具 | 参数说明 | 主要后端接口 |
| --- | --- | --- |
| `get_cache_stats` | 无参数 | `GET /api/cache/stats` |
| `server_health` | 无参数，执行完整工具检测 | `GET /health` |
| `nmap_scan` | [参数与默认值](../skills/pentest-tools/references/tools/nmap_scan.md) | `POST /api/tools/nmap` |
| `nuclei_scan` | [参数与默认值](../skills/pentest-tools/references/tools/nuclei_scan.md) | `POST /api/tools/nuclei` |
| `list_files` | [参数与默认值](../skills/pentest-tools/references/tools/list_files.md) | `GET /api/files/list` |

复合工具可能访问多个 HTTP 接口，并非每个工具都与一个路由一一对应；HTTP 路由数量也不等于 MCP 工具数量。

### 4.4 结果读取与错误区分

JSON-RPC 正常响应的 `result` 是 MCP `CallToolResult`：

- `content`：内容列表，当前工具通常在 `type="text"` 的 `text` 中返回原业务字典的 JSON 字符串。
- `structuredContent`：当前 SDK 对 `Dict[str, Any]` 工具返回类型通常封装为 `{"result": 原业务字典}`，对应工具的 `outputSchema`。注意它与最外层 JSON-RPC `result` 不是同一层。
- `isError`：工具调用是否报错。明确的业务失败、连接失败、超时等会设为 `true`；复合工具还需检查内部各步骤的业务结果。

繁忙等运行层错误可能直接将错误字典放在 `structuredContent`，不带内层 `result`；异常也可能只有文本内容。调用方不能无条件访问 `structuredContent.result`，更不能假定每段错误文本都是 JSON。

需要区分三层失败：

1. **HTTP 传输失败**：连接失败、超时、状态码错误等，可能没有 MCP 响应。
2. **协议失败**：JSON-RPC 响应存在 `error`，如方法或参数不合法。
3. **工具/业务失败**：响应有 `result`，但 `isError=true`，或业务结果包含失败、超时、部分结果。

HTTP 200 和 `isError=false` 都不单独证明目标测试成功。HTTP 命令类字段的解释同第 3.4 节；对结果做证据验证后再形成结论。

## 5. 调用限制与常见问题

| 项目 | 当前约定 |
| --- | --- |
| 并发 | 默认最多 4 个 MCP 顶层工具在途调用，可由 `HEXSTRIKE_MCP_MAX_CONCURRENT` 调整；超额立即返回繁忙，不排队、不调用后端 |
| 超时 | MCP 到后端连接超时 5 秒、单次读取超时默认 300 秒，读取值由 `HEXSTRIKE_MCP_TIMEOUT` 调整；复合工具总耗时可能更长 |
| 重试 | MCP HTTP 客户端不自动重试或跟随重定向；原后端错误恢复逻辑仍可能重试/调整执行，不能理解为全系统恰好执行一次 |
| 断连与取消 | 断连或客户端超时不等于后端进程已取消；仍在执行的同步调用会继续占用配额直到完成 |
| 隔离 | 文件、缓存、进程及部分后端状态共享；无状态 MCP 不代表多租户或按 Agent 隔离 |
| 直接 HTTP 调用 | 不经过 MCP 并发限制，不受未来 MCP 网关的权限自动保护 |
| stdio | 兼容入口仍保留，工具定义与 HTTP MCP 共用；远程接入不需要 stdio 本地子进程 |

| 现象 | 排查方向 |
| --- | --- |
| API 可访问，MCP 连接失败 | 确认连接的是 MCP 端口与完整 `/mcp` 路径，宿主选择了 Streamable HTTP |
| MCP 返回 421 | 核对请求 Host 与 `HEXSTRIKE_MCP_ALLOWED_HOSTS` |
| MCP 返回 403 | 核对浏览器/代理发送的 Origin 与允许列表，不是本系统要求登录 |
| `healthz` 成功、`readyz` 为 503 | MCP 进程可用，但后端不可连接或探针失败 |
| 可发现工具，但调用报程序不存在 | 检查服务端工具安装与 API 进程的 `PATH`；目录发现不证明执行环境完整 |
| 客户端等到超时 | 同时检查 Agent、网关、MCP、后端各层等待期限，不直接重发执行请求 |

## 6. HTTP 路由与请求字段索引

以下按当前 [HTTP 服务源码](../hexstrike_server.py) 登记的 **156 条业务路由**整理，不含 Flask 自动提供的静态文件、HEAD/OPTIONS 路由。这里列出处理器读取的顶层字段与默认取值；它不是新增的严格 JSON Schema。

- `字段=值` 表示处理器的缺省读取值，**不代表一定允许省略**；例如 `target=""` 随后通常被判为参数错误。
- `字段（直接读取）` 表示通过下标读取，无缺省值；具体必填验证及条件依赖见对应处理器。
- 除标注为查询串和路径参数外，字段来自 JSON 请求体；`null` 表示 Python `None`，`动态值` 表示运行时生成或计算。
- 每个路径链接到实际处理器，可核对特定接口的条件校验、嵌套字段和返回结构。未统一的业务响应不能强行套用命令执行结果结构。

<!-- HTTP_ROUTES_START -->
### 健康与通用执行

| 方法 | 路径与处理器 | 请求字段与缺省读取值 |
| --- | --- | --- |
| GET | [`/health`](../hexstrike_server.py#L9031) | 无 |
| POST | [`/api/command`](../hexstrike_server.py#L9145) | `command=""`；`use_cache=true` |

### 文件操作

| 方法 | 路径与处理器 | 请求字段与缺省读取值 |
| --- | --- | --- |
| POST | [`/api/files/create`](../hexstrike_server.py#L9170) | `filename=""`；`content=""`；`binary=false` |
| POST | [`/api/files/modify`](../hexstrike_server.py#L9188) | `filename=""`；`content=""`；`append=false` |
| DELETE | [`/api/files/delete`](../hexstrike_server.py#L9206) | `filename=""` |
| GET | [`/api/files/list`](../hexstrike_server.py#L9222) | 查询串；`directory="."` |

### 测试数据生成

| 方法 | 路径与处理器 | 请求字段与缺省读取值 |
| --- | --- | --- |
| POST | [`/api/payloads/generate`](../hexstrike_server.py#L9234) | `type="buffer"`；`size=1024`；`pattern="A"`；`filename=动态值` |

### 缓存

| 方法 | 路径与处理器 | 请求字段与缺省读取值 |
| --- | --- | --- |
| GET | [`/api/cache/stats`](../hexstrike_server.py#L9276) | 无 |
| POST | [`/api/cache/clear`](../hexstrike_server.py#L9281) | 无 |

### 遥测

| 方法 | 路径与处理器 | 请求字段与缺省读取值 |
| --- | --- | --- |
| GET | [`/api/telemetry`](../hexstrike_server.py#L9290) | 无 |

### 进程管理

| 方法 | 路径与处理器 | 请求字段与缺省读取值 |
| --- | --- | --- |
| GET | [`/api/processes/list`](../hexstrike_server.py#L9299) | 无 |
| GET | [`/api/processes/status/<int:pid>`](../hexstrike_server.py#L9325) | 路径参数：`pid` |
| POST | [`/api/processes/terminate/<int:pid>`](../hexstrike_server.py#L9356) | 路径参数：`pid` |
| POST | [`/api/processes/pause/<int:pid>`](../hexstrike_server.py#L9378) | 路径参数：`pid` |
| POST | [`/api/processes/resume/<int:pid>`](../hexstrike_server.py#L9400) | 路径参数：`pid` |
| GET | [`/api/processes/dashboard`](../hexstrike_server.py#L9422) | 无 |

### 结果展示

| 方法 | 路径与处理器 | 请求字段与缺省读取值 |
| --- | --- | --- |
| POST | [`/api/visual/vulnerability-card`](../hexstrike_server.py#L9475) | 完整JSON对象透传；见处理器引用的渲染函数 |
| POST | [`/api/visual/summary-report`](../hexstrike_server.py#L9496) | 完整JSON对象透传；见处理器引用的渲染函数 |
| POST | [`/api/visual/tool-output`](../hexstrike_server.py#L9518) | `tool（直接读取）`；`output（直接读取）`；`success=true` |

### 目标分析与决策

| 方法 | 路径与处理器 | 请求字段与缺省读取值 |
| --- | --- | --- |
| POST | [`/api/intelligence/analyze-target`](../hexstrike_server.py#L9547) | `target（直接读取）` |
| POST | [`/api/intelligence/select-tools`](../hexstrike_server.py#L9574) | `target（直接读取）`；`objective="comprehensive"` |
| POST | [`/api/intelligence/optimize-parameters`](../hexstrike_server.py#L9609) | `target（直接读取）`；`tool（直接读取）`；`context={}` |
| POST | [`/api/intelligence/create-attack-chain`](../hexstrike_server.py#L9645) | `target（直接读取）`；`objective="comprehensive"` |
| POST | [`/api/intelligence/smart-scan`](../hexstrike_server.py#L9680) | `target（直接读取）`；`objective="comprehensive"`；`max_tools=5` |
| POST | [`/api/intelligence/technology-detection`](../hexstrike_server.py#L10049) | `target（直接读取）` |

### 测试工作流

| 方法 | 路径与处理器 | 请求字段与缺省读取值 |
| --- | --- | --- |
| POST | [`/api/bugbounty/reconnaissance-workflow`](../hexstrike_server.py#L10106) | `domain（直接读取）`；`scope=[]`；`out_of_scope=[]`；`program_type="web"` |
| POST | [`/api/bugbounty/vulnerability-hunting-workflow`](../hexstrike_server.py#L10144) | `domain（直接读取）`；`priority_vulns=["rce", "sqli", "xss", "idor", "ssrf"]`；`bounty_range="unknown"` |
| POST | [`/api/bugbounty/business-logic-workflow`](../hexstrike_server.py#L10180) | `domain（直接读取）`；`program_type="web"` |
| POST | [`/api/bugbounty/osint-workflow`](../hexstrike_server.py#L10211) | `domain（直接读取）` |
| POST | [`/api/bugbounty/file-upload-testing`](../hexstrike_server.py#L10241) | `target_url（直接读取）` |
| POST | [`/api/bugbounty/comprehensive-assessment`](../hexstrike_server.py#L10272) | `domain（直接读取）`；`scope=[]`；`priority_vulns=["rce", "sqli", "xss", "idor", "ssrf"]`；`include_osint=true`；`include_business_logic=true` |

### 安全工具

| 方法 | 路径与处理器 | 请求字段与缺省读取值 |
| --- | --- | --- |
| POST | [`/api/tools/nmap`](../hexstrike_server.py#L10335) | `target=""`；`scan_type="-sCV"`；`ports=""`；`additional_args="-T4 -Pn"`；`use_recovery=true` |
| POST | [`/api/tools/gobuster`](../hexstrike_server.py#L10385) | `url=""`；`mode="dir"`；`wordlist="/usr/share/wordlists/dirb/common.txt"`；`additional_args=""`；`use_recovery=true` |
| POST | [`/api/tools/nuclei`](../hexstrike_server.py#L10437) | `target=""`；`severity=""`；`tags=""`；`template=""`；`additional_args=""`；`use_recovery=true` |
| POST | [`/api/tools/prowler`](../hexstrike_server.py#L10497) | `provider="aws"`；`profile="default"`；`region=""`；`checks=""`；`output_dir="/tmp/prowler_output"`；`output_format="json"`；`additional_args=""` |
| POST | [`/api/tools/trivy`](../hexstrike_server.py#L10541) | `scan_type="image"`；`target=""`；`output_format="json"`；`severity=""`；`output_file=""`；`additional_args=""` |
| POST | [`/api/tools/scout-suite`](../hexstrike_server.py#L10589) | `provider="aws"`；`profile="default"`；`report_dir="/tmp/scout-suite"`；`services=""`；`exceptions=""`；`additional_args=""` |
| POST | [`/api/tools/cloudmapper`](../hexstrike_server.py#L10629) | `action="collect"`；`account=""`；`config="config.json"`；`additional_args=""` |
| POST | [`/api/tools/pacu`](../hexstrike_server.py#L10662) | `session_name="hexstrike_session"`；`modules=""`；`data_services=""`；`regions=""`；`additional_args=""` |
| POST | [`/api/tools/kube-hunter`](../hexstrike_server.py#L10714) | `target=""`；`remote=""`；`cidr=""`；`interface=""`；`active=false`；`report="json"`；`additional_args=""` |
| POST | [`/api/tools/kube-bench`](../hexstrike_server.py#L10758) | `targets=""`；`version=""`；`config_dir=""`；`output_format="json"`；`additional_args=""` |
| POST | [`/api/tools/docker-bench-security`](../hexstrike_server.py#L10794) | `checks=""`；`exclude=""`；`output_file="/tmp/docker-bench-results.json"`；`additional_args=""` |
| POST | [`/api/tools/clair`](../hexstrike_server.py#L10827) | `image=""`；`config="/etc/clair/config.yaml"`；`output_format="json"`；`additional_args=""` |
| POST | [`/api/tools/falco`](../hexstrike_server.py#L10861) | `config_file="/etc/falco/falco.yaml"`；`rules_file=""`；`output_format="json"`；`duration=60`；`additional_args=""` |
| POST | [`/api/tools/checkov`](../hexstrike_server.py#L10894) | `directory="."`；`framework=""`；`check=""`；`skip_check=""`；`output_format="json"`；`additional_args=""` |
| POST | [`/api/tools/terrascan`](../hexstrike_server.py#L10931) | `scan_type="all"`；`iac_dir="."`；`policy_type=""`；`output_format="json"`；`severity=""`；`additional_args=""` |
| POST | [`/api/tools/dirb`](../hexstrike_server.py#L10965) | `url=""`；`wordlist="/usr/share/wordlists/dirb/common.txt"`；`additional_args=""` |
| POST | [`/api/tools/nikto`](../hexstrike_server.py#L10995) | `target=""`；`additional_args=""` |
| POST | [`/api/tools/sqlmap`](../hexstrike_server.py#L11024) | `url=""`；`data=""`；`additional_args=""` |
| POST | [`/api/tools/metasploit`](../hexstrike_server.py#L11057) | `module=""`；`options={}` |
| POST | [`/api/tools/hydra`](../hexstrike_server.py#L11101) | `target=""`；`service=""`；`username=""`；`username_file=""`；`password=""`；`password_file=""`；`additional_args=""` |
| POST | [`/api/tools/john`](../hexstrike_server.py#L11153) | `hash_file=""`；`wordlist="/usr/share/wordlists/rockyou.txt"`；`format=""`；`additional_args=""` |
| POST | [`/api/tools/wpscan`](../hexstrike_server.py#L11192) | `url=""`；`additional_args=""` |
| POST | [`/api/tools/enum4linux`](../hexstrike_server.py#L11221) | `target=""`；`additional_args="-a"` |
| POST | [`/api/tools/ffuf`](../hexstrike_server.py#L11247) | `url=""`；`wordlist="/usr/share/wordlists/dirb/common.txt"`；`mode="directory"`；`match_codes="200,204,301,302,307,401,403"`；`additional_args=""` |
| POST | [`/api/tools/netexec`](../hexstrike_server.py#L11298) | `target=""`；`protocol="smb"`；`username=""`；`password=""`；`hash=""`；`module=""`；`additional_args=""` |
| POST | [`/api/tools/amass`](../hexstrike_server.py#L11344) | `domain=""`；`mode="enum"`；`additional_args=""` |
| POST | [`/api/tools/hashcat`](../hexstrike_server.py#L11379) | `hash_file=""`；`hash_type=""`；`attack_mode="0"`；`wordlist="/usr/share/wordlists/rockyou.txt"`；`mask=""`；`additional_args=""` |
| POST | [`/api/tools/subfinder`](../hexstrike_server.py#L11423) | `domain=""`；`silent=true`；`all_sources=false`；`additional_args=""` |
| POST | [`/api/tools/smbmap`](../hexstrike_server.py#L11460) | `target=""`；`username=""`；`password=""`；`domain=""`；`additional_args=""` |
| POST | [`/api/tools/rustscan`](../hexstrike_server.py#L11505) | `target=""`；`ports=""`；`ulimit=5000`；`batch_size=4500`；`timeout=1500`；`scripts=""`；`additional_args=""` |
| POST | [`/api/tools/masscan`](../hexstrike_server.py#L11541) | `target=""`；`ports="1-65535"`；`rate=1000`；`interface=""`；`router_mac=""`；`source_ip=""`；`banners=false`；`additional_args=""` |
| POST | [`/api/tools/nmap-advanced`](../hexstrike_server.py#L11584) | `target=""`；`scan_type="-sS"`；`ports=""`；`timing="T4"`；`nse_scripts=""`；`os_detection=false`；`version_detection=false`；`aggressive=false`；`stealth=false`；`additional_args=""` |
| POST | [`/api/tools/autorecon`](../hexstrike_server.py#L11639) | `target=""`；`output_dir="/tmp/autorecon"`；`port_scans="top-100-ports"`；`service_scans="default"`；`heartbeat=60`；`timeout=300`；`additional_args=""` |
| POST | [`/api/tools/enum4linux-ng`](../hexstrike_server.py#L11681) | `target=""`；`username=""`；`password=""`；`domain=""`；`shares=true`；`users=true`；`groups=true`；`policy=true`；`additional_args=""` |
| POST | [`/api/tools/rpcclient`](../hexstrike_server.py#L11736) | `target=""`；`username=""`；`password=""`；`domain=""`；`commands="enumdomusers;enumdomgroups;querydominfo"`；`additional_args=""` |
| POST | [`/api/tools/nbtscan`](../hexstrike_server.py#L11774) | `target=""`；`verbose=false`；`timeout=2`；`additional_args=""` |
| POST | [`/api/tools/arp-scan`](../hexstrike_server.py#L11806) | `target=""`；`interface=""`；`local_network=false`；`timeout=500`；`retry=3`；`additional_args=""` |
| POST | [`/api/tools/responder`](../hexstrike_server.py#L11843) | `interface="eth0"`；`analyze=false`；`wpad=true`；`force_wpad_auth=false`；`fingerprint=false`；`duration=300`；`additional_args=""` |
| POST | [`/api/tools/volatility`](../hexstrike_server.py#L11885) | `memory_file=""`；`plugin=""`；`profile=""`；`additional_args=""` |
| POST | [`/api/tools/msfvenom`](../hexstrike_server.py#L11927) | `payload=""`；`format=""`；`output_file=""`；`encoder=""`；`iterations=""`；`additional_args=""` |
| POST | [`/api/tools/gdb`](../hexstrike_server.py#L11976) | `binary=""`；`commands=""`；`script_file=""`；`additional_args=""` |
| POST | [`/api/tools/radare2`](../hexstrike_server.py#L12025) | `binary=""`；`commands=""`；`additional_args=""` |
| POST | [`/api/tools/binwalk`](../hexstrike_server.py#L12068) | `file_path=""`；`extract=false`；`additional_args=""` |
| POST | [`/api/tools/ropgadget`](../hexstrike_server.py#L12103) | `binary=""`；`gadget_type=""`；`additional_args=""` |
| POST | [`/api/tools/checksec`](../hexstrike_server.py#L12136) | `binary=""` |
| POST | [`/api/tools/xxd`](../hexstrike_server.py#L12161) | `file_path=""`；`offset="0"`；`length=""`；`additional_args=""` |
| POST | [`/api/tools/strings`](../hexstrike_server.py#L12197) | `file_path=""`；`min_len=4`；`additional_args=""` |
| POST | [`/api/tools/objdump`](../hexstrike_server.py#L12229) | `binary=""`；`disassemble=true`；`additional_args=""` |
| POST | [`/api/tools/ghidra`](../hexstrike_server.py#L12270) | `binary=""`；`project_name="hexstrike_analysis"`；`script_file=""`；`analysis_timeout=300`；`output_format="xml"`；`additional_args=""` |
| POST | [`/api/tools/pwntools`](../hexstrike_server.py#L12313) | `script_content=""`；`target_binary=""`；`target_host=""`；`target_port=0`；`exploit_type="local"`；`additional_args=""` |
| POST | [`/api/tools/one-gadget`](../hexstrike_server.py#L12388) | `libc_path=""`；`level=1`；`additional_args=""` |
| POST | [`/api/tools/libc-database`](../hexstrike_server.py#L12414) | `action="find"`；`symbols=""`；`libc_id=""`；`additional_args=""` |
| POST | [`/api/tools/gdb-peda`](../hexstrike_server.py#L12455) | `binary=""`；`commands=""`；`attach_pid=0`；`core_file=""`；`additional_args=""` |
| POST | [`/api/tools/angr`](../hexstrike_server.py#L12517) | `binary=""`；`script_content=""`；`find_address=""`；`avoid_addresses=""`；`analysis_type="symbolic"`；`additional_args=""` |
| POST | [`/api/tools/ropper`](../hexstrike_server.py#L12608) | `binary=""`；`gadget_type="rop"`；`quality=1`；`arch=""`；`search_string=""`；`additional_args=""` |
| POST | [`/api/tools/pwninit`](../hexstrike_server.py#L12655) | `binary=""`；`libc=""`；`ld=""`；`template_type="python"`；`additional_args=""` |
| POST | [`/api/tools/feroxbuster`](../hexstrike_server.py#L12696) | `url=""`；`wordlist="/usr/share/wordlists/dirb/common.txt"`；`threads=10`；`additional_args=""` |
| POST | [`/api/tools/dotdotpwn`](../hexstrike_server.py#L12727) | `target=""`；`module="http"`；`additional_args=""` |
| POST | [`/api/tools/xsser`](../hexstrike_server.py#L12759) | `url=""`；`params=""`；`additional_args=""` |
| POST | [`/api/tools/wfuzz`](../hexstrike_server.py#L12792) | `url=""`；`wordlist="/usr/share/wordlists/dirb/common.txt"`；`additional_args=""` |
| POST | [`/api/tools/dirsearch`](../hexstrike_server.py#L12826) | `url=""`；`extensions="php,html,js,txt,xml,json"`；`wordlist="/usr/share/wordlists/dirsearch/common.txt"`；`threads=30`；`recursive=false`；`additional_args=""` |
| POST | [`/api/tools/katana`](../hexstrike_server.py#L12858) | `url=""`；`depth=3`；`js_crawl=true`；`form_extraction=true`；`output_format="json"`；`additional_args=""` |
| POST | [`/api/tools/gau`](../hexstrike_server.py#L12896) | `domain=""`；`providers="wayback,commoncrawl,otx,urlscan"`；`include_subs=true`；`blacklist="png,jpg,gif,jpeg,swf,woff,svg,pdf,css,ico"`；`additional_args=""` |
| POST | [`/api/tools/waybackurls`](../hexstrike_server.py#L12933) | `domain=""`；`get_versions=false`；`no_subs=false`；`additional_args=""` |
| POST | [`/api/tools/arjun`](../hexstrike_server.py#L12966) | `url=""`；`method="GET"`；`wordlist=""`；`delay=0`；`threads=25`；`stable=false`；`additional_args=""` |
| POST | [`/api/tools/paramspider`](../hexstrike_server.py#L13005) | `domain=""`；`level=2`；`exclude="png,jpg,gif,jpeg,swf,woff,svg,pdf,css,ico"`；`output=""`；`output_file=""`；`additional_args=""` |
| POST | [`/api/tools/x8`](../hexstrike_server.py#L13044) | `url=""`；`wordlist="/usr/share/wordlists/x8/params.txt"`；`method="GET"`；`body=""`；`headers=""`；`additional_args=""` |
| POST | [`/api/tools/jaeles`](../hexstrike_server.py#L13079) | `url=""`；`signatures=""`；`config=""`；`threads=20`；`timeout=20`；`additional_args=""` |
| POST | [`/api/tools/dalfox`](../hexstrike_server.py#L13114) | `url=""`；`pipe_mode=false`；`blind=false`；`mining_dom=true`；`mining_dict=true`；`custom_payload=""`；`additional_args=""` |
| POST | [`/api/tools/httpx`](../hexstrike_server.py#L13164) | `target=""`；`targets=""`；`target_file=""`；`probe=true`；`tech_detect=false`；`status_code=false`；`content_length=false`；`title=false`；`web_server=false`；`ports=""`；`methods=""`；`output_file=""`；`threads=50`；`additional_args=""` |
| POST | [`/api/tools/anew`](../hexstrike_server.py#L13236) | `input_data=""`；`output_file=""`；`additional_args=""` |
| POST | [`/api/tools/qsreplace`](../hexstrike_server.py#L13265) | `urls=""`；`replacement="FUZZ"`；`additional_args=""` |
| POST | [`/api/tools/uro`](../hexstrike_server.py#L13291) | `urls=""`；`whitelist=""`；`blacklist=""`；`additional_args=""` |
| POST | [`/api/tools/http-framework`](../hexstrike_server.py#L14090) | `action="request"`；`url=""`；`method="GET"`；`data={}`；`headers={}`；`cookies={}`；`max_depth=3`；`max_pages=100`；`rules=[]`；`host=null`；`include_subdomains=true`；`request=null`；`location="query"`；`params=[]`；`payloads=[]`；`base_data={}`；`max_requests=100` |
| POST | [`/api/tools/browser-agent`](../hexstrike_server.py#L14186) | `action="navigate"`；`url=""`；`headless=true`；`wait_time=5`；`proxy_port=null`；`active_tests=false` |
| POST | [`/api/tools/burpsuite-alternative`](../hexstrike_server.py#L14275) | `target=""`；`scan_type="comprehensive"`；`headless=true`；`max_depth=3`；`max_pages=50` |
| POST | [`/api/tools/zap`](../hexstrike_server.py#L14369) | `target=""`；`scan_type="baseline"`；`api_key=""`；`daemon=false`；`port="8090"`；`host="0.0.0.0"`；`format="xml"`；`output_file=""`；`additional_args=""` |
| POST | [`/api/tools/wafw00f`](../hexstrike_server.py#L14419) | `target=""`；`additional_args=""` |
| POST | [`/api/tools/fierce`](../hexstrike_server.py#L14448) | `domain=""`；`dns_server=""`；`additional_args=""` |
| POST | [`/api/tools/dnsenum`](../hexstrike_server.py#L14481) | `domain=""`；`dns_server=""`；`wordlist=""`；`additional_args=""` |
| POST | [`/api/tools/api_fuzzer`](../hexstrike_server.py#L14892) | `base_url=""`；`endpoints=[]`；`methods=["GET", "POST", "PUT", "DELETE"]`；`wordlist="/usr/share/wordlists/api/api-endpoints.txt"` |
| POST | [`/api/tools/graphql_scanner`](../hexstrike_server.py#L14949) | `endpoint=""`；`introspection=true`；`query_depth=10`；`test_mutations=true` |
| POST | [`/api/tools/jwt_analyzer`](../hexstrike_server.py#L15056) | `jwt_token=""`；`target_url=""` |
| POST | [`/api/tools/api_schema_analyzer`](../hexstrike_server.py#L15174) | `schema_url=""`；`schema_type="openapi"` |
| POST | [`/api/tools/volatility3`](../hexstrike_server.py#L15286) | `memory_file=""`；`plugin=""`；`output_file=""`；`additional_args=""` |
| POST | [`/api/tools/foremost`](../hexstrike_server.py#L15326) | `input_file=""`；`output_dir="/tmp/foremost_output"`；`file_types=""`；`additional_args=""` |
| POST | [`/api/tools/steghide`](../hexstrike_server.py#L15371) | `action="extract"`；`cover_file=""`；`embed_file=""`；`passphrase=""`；`output_file=""`；`additional_args=""` |
| POST | [`/api/tools/exiftool`](../hexstrike_server.py#L15420) | `file_path=""`；`output_format=""`；`tags=""`；`additional_args=""` |
| POST | [`/api/tools/hashpump`](../hexstrike_server.py#L15459) | `signature=""`；`data=""`；`key_length=""`；`append_data=""`；`additional_args=""` |
| POST | [`/api/tools/hakrawler`](../hexstrike_server.py#L15495) | `url=""`；`depth=2`；`forms=true`；`robots=true`；`sitemap=true`；`wayback=false`；`additional_args=""` |

### Python执行环境

| 方法 | 路径与处理器 | 请求字段与缺省读取值 |
| --- | --- | --- |
| POST | [`/api/python/install`](../hexstrike_server.py#L14519) | `package=""`；`env_name="default"` |
| POST | [`/api/python/execute`](../hexstrike_server.py#L14549) | `script=""`；`env_name="default"`；`filename=动态值` |

### 载荷辅助

| 方法 | 路径与处理器 | 请求字段与缺省读取值 |
| --- | --- | --- |
| POST | [`/api/ai/generate_payload`](../hexstrike_server.py#L14800) | `attack_type="xss"`；`complexity="basic"`；`technology=""`；`url=""` |
| POST | [`/api/ai/test_payload`](../hexstrike_server.py#L14830) | `payload=""`；`target_url=""`；`method="GET"` |
| POST | [`/api/ai/advanced-payload-generation`](../hexstrike_server.py#L16015) | `attack_type="rce"`；`target_context=""`；`evasion_level="standard"`；`custom_constraints=""` |

### 漏洞情报

| 方法 | 路径与处理器 | 请求字段与缺省读取值 |
| --- | --- | --- |
| POST | [`/api/vuln-intel/cve-monitor`](../hexstrike_server.py#L15537) | `hours=24`；`severity_filter="HIGH,CRITICAL"`；`keywords=""` |
| POST | [`/api/vuln-intel/exploit-generate`](../hexstrike_server.py#L15591) | `cve_id=""`；`target_os=""`；`target_arch="x64"`；`exploit_type="poc"`；`evasion_level="none"`；`target_ip="192.168.1.100"`；`target_port=80`；`target_description=动态值` |
| POST | [`/api/vuln-intel/attack-chains`](../hexstrike_server.py#L15664) | `target_software=""`；`attack_depth=3`；`include_zero_days=false` |
| POST | [`/api/vuln-intel/threat-feeds`](../hexstrike_server.py#L15741) | `indicators=[]`；`timeframe="30d"`；`sources="all"` |
| POST | [`/api/vuln-intel/zero-day-research`](../hexstrike_server.py#L15876) | `target_software=""`；`analysis_depth="standard"`；`source_code_url=""` |

### CTF工作流

| 方法 | 路径与处理器 | 请求字段与缺省读取值 |
| --- | --- | --- |
| POST | [`/api/ctf/create-challenge-workflow`](../hexstrike_server.py#L16157) | `name=""`；`category="misc"`；`difficulty="unknown"`；`points=100`；`description=""`；`target=""` |
| POST | [`/api/ctf/auto-solve-challenge`](../hexstrike_server.py#L16197) | `name=""`；`category="misc"`；`difficulty="unknown"`；`points=100`；`description=""`；`target=""` |
| POST | [`/api/ctf/team-strategy`](../hexstrike_server.py#L16237) | `challenges=[]`；`team_skills={}` |
| POST | [`/api/ctf/suggest-tools`](../hexstrike_server.py#L16277) | `description=""`；`category="misc"` |
| POST | [`/api/ctf/cryptography-solver`](../hexstrike_server.py#L16314) | `cipher_text=""`；`cipher_type="unknown"`；`key_hint=""`；`known_plaintext=""`；`additional_info=""` |
| POST | [`/api/ctf/forensics-analyzer`](../hexstrike_server.py#L16412) | `file_path=""`；`analysis_type="comprehensive"`；`extract_hidden=true`；`check_steganography=true` |
| POST | [`/api/ctf/binary-analyzer`](../hexstrike_server.py#L16555) | `binary_path=""`；`analysis_depth="comprehensive"`；`check_protections=true`；`find_gadgets=true` |

### 异步执行与执行池

| 方法 | 路径与处理器 | 请求字段与缺省读取值 |
| --- | --- | --- |
| POST | [`/api/process/execute-async`](../hexstrike_server.py#L16735) | `command=""`；`context={}` |
| GET | [`/api/process/get-task-result/<task_id>`](../hexstrike_server.py#L16762) | 路径参数：`task_id` |
| GET | [`/api/process/pool-stats`](../hexstrike_server.py#L16783) | 无 |
| GET | [`/api/process/cache-stats`](../hexstrike_server.py#L16800) | 无 |
| POST | [`/api/process/clear-cache`](../hexstrike_server.py#L16817) | 无 |
| GET | [`/api/process/resource-usage`](../hexstrike_server.py#L16834) | 无 |
| GET | [`/api/process/performance-dashboard`](../hexstrike_server.py#L16853) | 无 |
| POST | [`/api/process/terminate-gracefully/<int:pid>`](../hexstrike_server.py#L16886) | 路径参数：`pid`；`timeout=30` |
| POST | [`/api/process/auto-scaling`](../hexstrike_server.py#L16915) | `enabled=true`；`thresholds={}` |
| POST | [`/api/process/scale-pool`](../hexstrike_server.py#L16941) | `action=""`；`count=1` |
| GET | [`/api/process/health-check`](../hexstrike_server.py#L16985) | 无 |

### 错误恢复

| 方法 | 路径与处理器 | 请求字段与缺省读取值 |
| --- | --- | --- |
| GET | [`/api/error-handling/statistics`](../hexstrike_server.py#L17085) | 无 |
| POST | [`/api/error-handling/test-recovery`](../hexstrike_server.py#L17099) | `tool_name="nmap"`；`error_type="timeout"`；`target="example.com"`；`parameters={}` |
| GET | [`/api/error-handling/fallback-chains`](../hexstrike_server.py#L17145) | 查询串；`operation=""`；`failed_tools=重复查询参数` |
| POST | [`/api/error-handling/execute-with-recovery`](../hexstrike_server.py#L17173) | `tool_name=""`；`command=""`；`parameters={}`；`max_attempts=3`；`use_cache=true` |
| POST | [`/api/error-handling/classify-error`](../hexstrike_server.py#L17206) | `error_message=""` |
| POST | [`/api/error-handling/parameter-adjustments`](../hexstrike_server.py#L17238) | `tool_name=""`；`error_type=""`；`original_params={}` |
| GET | [`/api/error-handling/alternative-tools`](../hexstrike_server.py#L17271) | 查询串；`tool_name=""` |
<!-- HTTP_ROUTES_END -->
