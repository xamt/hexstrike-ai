"""由官方 SDK 提供 Streamable HTTP；不自行实现 JSON-RPC。"""

import anyio
import uvicorn
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse


def create_http_app(server, client, args):
    """构建自带生命周期的 SDK 应用及最小健康探针。"""
    @server.custom_route("/healthz", methods=["GET"])
    async def healthz(request):
        return JSONResponse({"status": "alive"})

    @server.custom_route("/readyz", methods=["GET"])
    async def readyz(request):
        result = await anyio.to_thread.run_sync(client.probe_backend)
        ready = not result.get("error") and result.get("success") is not False
        return JSONResponse({"status": "ready" if ready else "not_ready"},
                            status_code=200 if ready else 503)

    return server.streamable_http_app(
        streamable_http_path="/mcp", stateless_http=True, json_response=True,
        host=args.host,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=args.allowed_hosts,
            allowed_origins=args.allowed_origins,
        ),
    )


def serve_http(server, client, args):
    """运行单进程 ASGI 服务；外层容器管理器负责服务间故障联动。"""
    app = create_http_app(server, client, args)
    uvicorn.run(app, host=args.host, port=args.port, workers=1,
                log_level="debug" if args.debug else "info", access_log=False,
                timeout_graceful_shutdown=8)
