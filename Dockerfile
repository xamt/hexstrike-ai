# syntax=docker/dockerfile:1.7

# 默认按目标架构选择独立基础镜像，不依赖多架构入口。
# 正式发布可通过 BASE_IMAGE=仓库@sha256:摘要固定同架构基础镜像。
ARG BASE_IMAGE=harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.3.3-${TARGETARCH}
FROM ${BASE_IMAGE} AS runtime

# 保留项目生成脚本使用 python3 时的原有应用依赖环境。
# 同名 httpx 命令在依赖安装后单独指向安全工具，不改变 Python 库导入。
ENV PATH="/opt/hexstrike-compat/bin:/opt/hexstrike-venv/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HEXSTRIKE_HOST=0.0.0.0 \
    HEXSTRIKE_PORT=8888 \
    HEXSTRIKE_MCP_PORT=8889 \
    HEXSTRIKE_STARTUP_TIMEOUT=60 \
    HEXSTRIKE_SHUTDOWN_TIMEOUT=10

WORKDIR /opt/pentest-tools
# 使用基础镜像固定的 pip 管理新环境，不修改系统或工具虚拟环境。
RUN /usr/local/bin/python3.11 -m venv --without-pip /opt/hexstrike-venv && \
    /usr/local/bin/python3.11 -m venv --without-pip /opt/hexstrike-mcp-venv
COPY requirements.txt requirements-mcp.txt ./
# 与基础镜像统一国内 PyPI 源；只用于构建，不改容器运行时的 pip 配置。
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
RUN sed -E '/^(pwntools|angr|bcrypt)([<=>]|$)/d' requirements.txt \
      > requirements-runtime.txt && \
    /usr/local/bin/python3.11 -m pip --python /opt/hexstrike-venv/bin/python install -r requirements-runtime.txt --index-url "${PIP_INDEX_URL}" && \
    ln -sf /usr/local/bin/httpx /opt/hexstrike-venv/bin/httpx && \
    /usr/local/bin/python3.11 -m pip --python /opt/hexstrike-venv/bin/python check && \
    /usr/local/bin/python3.11 -m pip --python /opt/hexstrike-mcp-venv/bin/python install -r requirements-mcp.txt --index-url "${PIP_INDEX_URL}" && \
    /usr/local/bin/python3.11 -m pip --python /opt/hexstrike-mcp-venv/bin/python check && \
    /opt/volatility3-venv/bin/python -m pip check && \
    vol -h >/dev/null

# 代码变化不触发前面的依赖安装。
COPY server.py mcp_server.py ./
COPY runtime/ ./runtime/
COPY tools/ ./tools/
COPY docker/service_manager.py docker/service_health.py ./docker/
RUN /opt/hexstrike-venv/bin/python -c 'import aiohttp, bs4, flask, mitmproxy, psutil, requests, selenium' && \
    /opt/hexstrike-venv/bin/python -m py_compile server.py docker/service_manager.py docker/service_health.py && \
    /opt/hexstrike-mcp-venv/bin/python -c 'import mcp, requests, tools; from runtime.server import setup_mcp_server' && \
    /opt/hexstrike-mcp-venv/bin/python -m compileall -q mcp_server.py runtime tools

EXPOSE 8888 8889
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD ["/opt/hexstrike-venv/bin/python", "/opt/pentest-tools/docker/service_health.py"]

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/opt/hexstrike-venv/bin/python", "/opt/pentest-tools/docker/service_manager.py"]
