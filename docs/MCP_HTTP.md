# 单容器 HTTP API 与 Streamable HTTP MCP

一个应用容器默认启动两个服务：HTTP API `8888`、MCP `8889/mcp`。Agent 直接连接 MCP URL，不需要在本机启动 Python 脚本或通过技能运行 Node 调用器。

## 1. 构建与启动

基础镜像和安全工具不变，仅构建应用镜像。下例在项目根目录执行，使用已有 ARM64 基础镜像；AMD64 对应替换平台和基础镜像后缀。使用新的本地标签，不覆盖已发布版本。

```bash
docker build --platform linux/arm64 \
  --build-arg BASE_IMAGE=harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.3.3-arm64 \
  --tag pentest-tools:mcp-http \
  "."

docker run --detach --name pentest-tools-mcp \
  --publish 127.0.0.1:8888:8888 \
  --publish 127.0.0.1:8889:8889 \
  --stop-timeout 15 \
  pentest-tools:mcp-http
```

地址：

| 用途 | 地址 |
| --- | --- |
| 原 HTTP API | `http://127.0.0.1:8888/api/...` |
| 原 API 健康信息 | `http://127.0.0.1:8888/health` |
| MCP 接入 | `http://127.0.0.1:8889/mcp` |
| MCP 进程存活 | `http://127.0.0.1:8889/healthz` |
| MCP 后端可连接 | `http://127.0.0.1:8889/readyz` |

**本版本按项目要求不增加鉴权。两类接口都具备执行能力，不得裸露到公网或非可信网络。** 后续接入 MCP 网关时，只允许网关访问 MCP，HTTP API 也必须保持网络隔离，否则可绕过网关权限。上例仅发布到 Docker 主机回环，不代表远程 Agent 可以直接访问。

网关与本服务在同一个 Docker 网络时可以不发布宿主端口，通过容器服务名访问；此时将该服务名加入下文 Host 白名单。外部 HTTPS/TLS、身份和权限由网关管理，本项目不透传或自行解释用户令牌。

## 2. Agent 接入

在支持远程 MCP 的 Agent 宿主中选择 **Streamable HTTP**，填写 `/mcp` URL，无需配置 `command`、`args` 或本地执行器。不同产品字段不同，不能把某个客户端 JSON 格式视为通用协议配置。

自研 Agent 可使用官方 Python SDK（`requirements-mcp.txt`）的客户端：

```python
import asyncio
from mcp import Client


async def main():
    async with Client("http://127.0.0.1:8889/mcp") as client:
        tools = await client.list_tools()
        result = await client.call_tool("server_health", {})
        print(len(tools.tools), result.content)


asyncio.run(main())
```

SDK 负责协议发现/初始化、工具列表和调用。服务使用无状态 Streamable HTTP，JSON 响应也是该传输的合法形式；不要求 `Mcp-Session-Id`，不提供旧式 `/sse` 接口。支持 SDK 的新协议连接和旧版初始化握手。

## 3. 运行配置

| 环境变量 | 默认值 | 作用 |
| --- | --- | --- |
| `HEXSTRIKE_PORT` | `8888` | API 容器内监听端口 |
| `HEXSTRIKE_MCP_PORT` | `8889` | MCP 容器内监听端口，不能与 API 相同 |
| `HEXSTRIKE_STARTUP_TIMEOUT` | `60` | 两个服务总启动期限，秒 |
| `HEXSTRIKE_SHUTDOWN_TIMEOUT` | `10` | 进程组优雅退出期限，秒 |
| `HEXSTRIKE_MCP_TIMEOUT` | `300` | 单次后端 HTTP 读取超时，秒；连接超时 5 秒 |
| `HEXSTRIKE_MCP_MAX_CONCURRENT` | `4` | MCP 顶层工具在途调用上限 |
| `HEXSTRIKE_MCP_ALLOWED_HOSTS` | `127.0.0.1:*,localhost:*,[::1]:*` | MCP Host 白名单，逗号分隔 |
| `HEXSTRIKE_MCP_ALLOWED_ORIGINS` | 空 | 允许的浏览器 Origin，逗号分隔；默认拒绝带外部 Origin 的请求 |

远程网关访问时，Host 必须与实际传入值匹配，例如 `pentest-tools:8889`、`mcp.example.com`。端口通配使用 `mcp.example.com:*`；无端口域名单独列出。不要用任意 Host/Origin 通配来代替网络配置。

修改容器内端口时也要对应调整 `--publish` 的容器端口。`docker stop` 等待时间应大于 `HEXSTRIKE_SHUTDOWN_TIMEOUT`，上例为 15 秒。Agent 和网关的等待期限要覆盖后端调用；复合工具可能连续执行多次请求，单次读取超时并不限制整个复合任务时长。

命令行也可单独启动 MCP（先在专用虚拟环境安装 `requirements-mcp.txt`）：

```bash
python hexstrike_mcp.py --transport streamable-http \
  --host 127.0.0.1 --port 8889 --server http://127.0.0.1:8888

# 不指定 --transport 时，保持原 stdio 启动方式。
python hexstrike_mcp.py --server http://127.0.0.1:8888
```

CLI 的 `--timeout`、`--max-concurrent`、`--allowed-host`、`--allowed-origin` 可覆盖对应环境配置；白名单参数可重复传入。容器默认由管理器显式选择 HTTP，手动 CLI 默认仍为 stdio。

## 4. 工具与兼容边界

- 原文件实际为 **151 个工具声明、150 个唯一工具名称**：`httpx_probe` 重复声明。保留原注册顺序和首次注册语义，不新增别名、不暗中丢弃不同声明。
- 工具函数机械拆分到 `hexstrike_tools/`，两个传输共用同一份注册入口。契约测试冻结原参数、默认值、文档字符串及函数体 AST，后端 `hexstrike_server.py` 不修改。
- JSON 文本结果保留原业务字典；SDK 对 `Dict[str, Any]` 的结构化返回使用 `structuredContent.result`，与工具公布的 `outputSchema` 一致。明确业务错误和连接错误设置 MCP `isError`。
- HTTP 客户端不自动重试或跟随重定向；超时表示后端状态未确认，不等于扫描取消。原后端自身的恢复机制和历史工具缺陷保持不变。
- 上限约束的是 MCP 顶层调用，不是扫描器内部线程或所有 API 请求。直接 API 调用不经过该限流。超额请求明确返回繁忙，不进行后端调用。
- 断连不能释放仍在执行的同步调用配额，调用完成后才回收；不承诺任务持久化、取消、流式扫描日志或重启恢复。
- 后端文件、Cookie、作用域和进程仍共享；MCP 无状态不构成任务隔离。
- Skills 保留测试方法、证据与报告规范；支持 MCP 的 Agent 优先调用原生工具。HTTP 调用器仅用于明确选择的兼容方式，不静默切换执行通道。

## 5. 生命周期与验证

启动管理器先运行 API，通过现有只读 `/api/cache/stats` 确认可连接后再运行 MCP。原 `/health` 会执行完整工具检测，保留给显式能力检查，不用作高频启动或就绪探针。两个服务各自处于独立进程组；任一核心进程异常退出都会停止另一服务并让容器非零退出，不在容器内无限重启。可由部署平台设置重启策略。

Docker 健康探针同时检查 API 和 MCP 的后端就绪状态；健康不表示所有字典、模板或扫描器已验收。停止时先向进程组转发信号，再在期限后强制清理。

开发验证：

```bash
# 使用安装了 requirements-mcp.txt 的解释器执行，确保协议测试没有被跳过。
python -m unittest discover -s "tests" -p "test_*.py"
node --test "tests/http-skill.test.mjs" "tests/skill-workflows.test.mjs"
git diff --check

# 已构建镜像的真实双接口和退出清理验收；需要本机 Docker。
python "tests/verify_mcp_image.py" pentest-tools:mcp-http
```

协议测试仅使用本机模拟 API，覆盖新旧协议、stdio、工具目录一致性、参数、错误、超时、并发和健康状态，不执行目标扫描。镜像验收脚本创建并清理专用临时容器，核对 API、`/readyz`、健康探针、真实 MCP 工具发现和 `server_health`，比较 HTTP/stdio 完整目录，并验证任一服务异常退出及 `docker stop` 清理。
