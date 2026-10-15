# syntax=docker/dockerfile:1.7

# BuildKit 自动在全局提供平台参数，FROM 可直接使用，无需在首个 FROM 前声明。
# 构建阶段内使用 TARGETOS、TARGETARCH 时，再在对应 FROM 后用 ARG 引入。
# 本项目按目标平台分别构建，使 amd64、arm64 直接体现在镜像仓库名称中。
# amd64 发布示例：
#   docker buildx build --platform linux/amd64 \
#     -t harbor.everoffice.cn/harbor-cucc/hexstrike-ai-amd64:1.0.0 --push .
# arm64 发布示例：
#   docker buildx build --platform linux/arm64 \
#     -t harbor.everoffice.cn/harbor-cucc/hexstrike-ai-arm64:1.0.0 --push .
# 多架构聚合镜像发布示例（拉取时由 Docker 自动选择目标架构）：
#   docker buildx build --platform linux/amd64,linux/arm64 \
#     -t harbor.everoffice.cn/harbor-cucc/hexstrike-ai-multiarch:1.0.0 --push .
# 完整构建、缓存、验证和运行命令见项目根目录 DOCKER_BUILD.md。
# 可使用多架构 manifest digest 覆盖此值，以进一步固定基础操作系统：
#   --build-arg KALI_BASE_IMAGE=kalilinux/kali-rolling@sha256:...
# 即使保持默认 rolling 标签，下文的安全工具仍全部使用精确版本，绝不自动升级。
ARG KALI_BASE_IMAGE=kalilinux/kali-rolling:latest

# HexStrike AI 完整工具镜像
#
# 构建顺序：
#   1. 在独立构建阶段编译 Kali 仓库中没有的工具；
#   2. 在 Kali 工具层逐项安装安全工具；
#   3. 创建与项目兼容的 Python 3.11 运行环境；
#   4. 最后复制 HexStrike 项目代码，避免代码变化导致工具层失去缓存。
#
# 重要边界：
#   - 支持 linux/amd64 与 linux/arm64；架构相关包版本在各工具段落分别锁定；
#   - Kali APT 工具全部使用精确包版本，仓库没有该版本时构建会失败，
#     不会静默安装更高版本；
#   - Nuclei 模板、Ophcrack 彩虹表、Volatility 符号表、Hashcat 字典等
#     大型或经常变化的数据不固化到镜像中，应通过卷挂载或运行时更新；
#   - 镜像只应在取得明确授权的安全测试环境中使用。


# =============================================================================
# 非 Kali 工具构建阶段：Go 工具
# =============================================================================
FROM --platform=${BUILDPLATFORM} golang:1.25-bookworm AS go-tools

ARG TARGETOS
ARG TARGETARCH

ENV CGO_ENABLED=0 \
    GOBIN=/out

# 在构建机架构上运行 Go 编译器，但输出目标镜像架构的静态二进制。
ENV GOOS=${TARGETOS} \
    GOARCH=${TARGETARCH}

# 工具: Gau
# 分类: Web Application Security / URL 发现
# 描述: 从 Wayback、Common Crawl、OTX、URLScan 等来源收集历史 URL。
# 安装: 使用官方 Go 模块固定到 v2.2.4。
ARG GAU_VERSION=v2.2.4
RUN go install github.com/lc/gau/v2/cmd/gau@${GAU_VERSION}

# 工具: Waybackurls
# 分类: Web Application Security / URL 发现
# 描述: 从 Internet Archive Wayback Machine 收集目标域名的历史 URL。
# 安装: 使用官方 Go 模块固定到 v0.1.0。
ARG WAYBACKURLS_VERSION=v0.1.0
RUN go install github.com/tomnomnom/waybackurls@${WAYBACKURLS_VERSION}

# 工具: Anew
# 分类: Web Application Security / 数据处理
# 描述: 只输出并追加尚未存在的文本行，便于扫描管道去重。
# 安装: 使用官方 Go 模块固定到 v0.1.1。
ARG ANEW_VERSION=v0.1.1
RUN go install github.com/tomnomnom/anew@${ANEW_VERSION}


# =============================================================================
# 非 Kali 工具构建阶段：Rust 工具
# =============================================================================
FROM --platform=${TARGETPLATFORM} rust:1.85-bookworm AS rust-tools

# 工具: X8
# 分类: Web Application Security / 参数发现
# 描述: 根据响应差异发现隐藏的 HTTP 参数。
# 安装: 使用 crates.io 的 x8 4.3.0，并使用锁定依赖。
ARG X8_VERSION=4.3.0
RUN cargo install x8 --version ${X8_VERSION} --locked --root /out


# =============================================================================
# 非 Kali 工具构建阶段：Nikto 源码
# =============================================================================
FROM --platform=${BUILDPLATFORM} debian:bookworm-slim AS nikto-source

# 工具: Nikto
# 分类: Web Application Security / Web 服务器检查
# 描述: 检查 Web 服务器危险文件、错误配置和已知风险。
# 安装: Kali 当前主仓库没有 nikto 包，固定克隆官方 2.6.1 标签。
ARG NIKTO_VERSION=2.6.1
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates git && \
    git clone --depth 1 --branch ${NIKTO_VERSION} \
      https://github.com/sullo/nikto.git /opt/nikto && \
    rm -rf /opt/nikto/.git /var/lib/apt/lists/*


# =============================================================================
# Kali 工具层：先安装全部外部工具，暂不复制 HexStrike 项目代码
# =============================================================================
FROM --platform=${TARGETPLATFORM} ${KALI_BASE_IMAGE} AS security-tools

ARG TARGETARCH
ARG WPSCAN_VERSION=4.0.0

# Kali APT 镜像源
# 默认使用阿里云中国区镜像；可在构建时覆盖为官方负载均衡地址：
#   --build-arg KALI_APT_MIRROR=http://http.kali.org/kali
# 仍使用 Kali 官方 keyring 校验 Release/InRelease 签名。
ARG KALI_APT_MIRROR=https://mirrors.aliyun.com/kali
ARG KALI_APT_SUITE=kali-rolling

# Kali 安全工具包版本锁（核对日期：2026-10-14）。
# 规则：APT 始终使用 package=${VERSION}；镜像站未同步或移除该版本时直接失败，
# 绝不退回到“安装当前最新版”。仅存在 Debian 架构重编译后缀差异的包分架构锁定。
ARG NMAP_VERSION=7.991+dfsg-1kali1
ARG MASSCAN_VERSION_AMD64=2:1.3.2+ds1-2
ARG MASSCAN_VERSION_ARM64=2:1.3.2+ds1-2+b1
ARG RUSTSCAN_VERSION=2.4.1-0kali1
ARG AMASS_VERSION=5.1.1-0kali3
ARG SUBFINDER_VERSION=2.16.0-0kali1
ARG NUCLEI_VERSION=3.11.1-0kali1
ARG FIERCE_VERSION=1.6.0-2
ARG DNSENUM_VERSION=1.3.2-1
ARG AUTORECON_VERSION=0.0~git20251116.e7e98f6-0kali1
ARG THEHARVESTER_VERSION=4.11.1-0kali2
ARG RESPONDER_VERSION=3.2.2.0-0kali2
ARG NETEXEC_VERSION=1.5.1-0kali2
ARG ENUM4LINUX_NG_VERSION=1.3.10-0kali1
ARG GOBUSTER_VERSION=3.8.2-1
ARG FEROXBUSTER_VERSION=2.13.1-0kali3
ARG DIRSEARCH_VERSION=0.4.3-1
ARG FFUF_VERSION=2.2.1-1
ARG DIRB_VERSION_AMD64=2.22+dfsg-7
ARG DIRB_VERSION_ARM64=2.22+dfsg-7+b1
ARG HTTPX_TOOLKIT_VERSION=1.9.0-0kali2
ARG KATANA_VERSION=1.7.0-0kali1
ARG HAKRAWLER_VERSION=2.1-0kali1
ARG SQLMAP_VERSION=1.10.9-1
ARG ARJUN_VERSION=2.2.7-1
ARG PARAMSPIDER_VERSION=1.0.1-3
ARG DALFOX_VERSION=3.2.2-0kali1
ARG WAFW00F_VERSION=2.4.2-1
ARG QSREPLACE_VERSION=0.0.3-0kali1
ARG URO_VERSION=1.0.2-0kali1
ARG WFUZZ_VERSION=3.1.1-1
ARG HYDRA_VERSION=9.7-2
ARG JOHN_VERSION=1.9.0-Jumbo-1+git20211102-0kali11
ARG HASHCAT_VERSION=7.1.2+ds1-4
ARG MEDUSA_VERSION=2.3-3
ARG PATATOR_VERSION=1.1.0-1
ARG CRACKMAPEXEC_VERSION=5.4.0-0kali7
ARG EVIL_WINRM_VERSION=4.1-0kali1
ARG HASH_IDENTIFIER_VERSION=1.2+git20180314-0kali3
ARG OPHCRACK_CLI_VERSION_AMD64=3.8.0-4
ARG OPHCRACK_CLI_VERSION_ARM64=3.8.0-4+b1
ARG GDB_VERSION=17.2-1+b1
ARG RADARE2_VERSION=6.0.4+dfsg-1
ARG BINWALK_VERSION=2.4.3+dfsg1-3
ARG GHIDRA_VERSION=12.1.4+ds-0kali1
ARG CHECKSEC_VERSION=2.6.0-2
ARG BINUTILS_VERSION=2.47-6
ARG XXD_VERSION=2:9.2.0858-1
ARG FOREMOST_VERSION_AMD64=1.5.7-12+b1
ARG FOREMOST_VERSION_ARM64=1.5.7-12
ARG STEGHIDE_VERSION=0.5.1+git20240220-2
ARG EXIFTOOL_VERSION=13.55+dfsg-1

ENV DEBIAN_FRONTEND=noninteractive \
    PATH="/opt/hexstrike-venv/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HEXSTRIKE_HOST=0.0.0.0 \
    HEXSTRIKE_PORT=8888

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# 平台边界：只允许已核对工具包可用性的 amd64 和 arm64。
RUN case "${TARGETARCH}" in \
      amd64|arm64) ;; \
      *) echo "不支持的目标架构: ${TARGETARCH}" >&2; exit 1 ;; \
    esac

# APT 源配置
# 分类: 镜像基础设施
# 描述: 使用可覆盖的 Kali 镜像站，加速中国区构建，同时保留官方签名校验。
# 安装: 写入唯一的 deb822 软件源，避免基础镜像原源与自定义源重复读取。
RUN printf '%s\n' \
      'Types: deb' \
      "URIs: ${KALI_APT_MIRROR}" \
      "Suites: ${KALI_APT_SUITE}" \
      'Components: main contrib non-free non-free-firmware' \
      'Signed-By: /usr/share/keyrings/kali-archive-keyring.gpg' \
      > /etc/apt/sources.list.d/kali.sources && \
    : > /etc/apt/sources.list

# 基础运行库
# 分类: 镜像基础设施
# 描述: 提供证书、进程管理、源码获取、Perl 工具运行库和 Python 3.11
#       从 Debian 镜像复制后所需的动态链接库。
# 安装: 仅安装运行期依赖；APT 索引和下载包使用 BuildKit 缓存挂载。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates curl git tini perl \
      libnet-ssleay-perl libio-socket-ssl-perl libwww-perl \
      libssl3t64 libffi8 libbz2-1.0 libsqlite3-0 liblzma5 \
      libreadline8t64 libncursesw6 libgdbm6t64 libgdbm-compat4t64 \
      libexpat1 libuuid1 libnsl2 libtirpc3t64 zlib1g


# -----------------------------------------------------------------------------
# Network & Reconnaissance
# -----------------------------------------------------------------------------

# 工具: Nmap
# 分类: Network & Reconnaissance
# 描述: 主机发现、端口扫描、服务识别、操作系统识别和 NSE 检查。
# 安装: Kali 软件包 nmap。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "nmap=${NMAP_VERSION}"

# 工具: Masscan
# 分类: Network & Reconnaissance
# 描述: 针对大量 IP 的高速异步端口扫描器；运行时可能需要额外网络能力。
# 安装: Kali 软件包 masscan。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && \
    case "${TARGETARCH}" in \
      amd64) package_version="${MASSCAN_VERSION_AMD64}" ;; \
      arm64) package_version="${MASSCAN_VERSION_ARM64}" ;; \
    esac && \
    apt-get install -y --no-install-recommends "masscan=${package_version}"

# 工具: RustScan
# 分类: Network & Reconnaissance
# 描述: 快速发现开放端口，并可把结果交给 Nmap 深入扫描。
# 安装: Kali 软件包 rustscan。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "rustscan=${RUSTSCAN_VERSION}"

# 工具: Amass
# 分类: Network & Reconnaissance
# 描述: 收集子域名、DNS 关系和外部攻击面信息。
# 安装: Kali 软件包 amass。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "amass=${AMASS_VERSION}"

# 工具: Subfinder
# 分类: Network & Reconnaissance
# 描述: 使用公开数据源进行被动子域名发现；部分数据源需要 API Key。
# 安装: Kali 软件包 subfinder。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "subfinder=${SUBFINDER_VERSION}"

# 工具: Nuclei
# 分类: Network & Reconnaissance / Web 漏洞扫描
# 描述: 使用模板检查服务和 Web 应用中的漏洞及配置问题。
# 安装: Kali 软件包 nuclei；不在构建中执行 update-templates，避免模板随构建漂移。
#       如需模板，请按版本通过只读卷挂载到运行容器。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "nuclei=${NUCLEI_VERSION}"

# 工具: Fierce
# 分类: Network & Reconnaissance
# 描述: 进行 DNS 枚举并发现与目标域名关联的主机。
# 安装: Kali 软件包 fierce。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "fierce=${FIERCE_VERSION}"

# 工具: DNSenum
# 分类: Network & Reconnaissance
# 描述: 枚举 DNS 记录、名称服务器、区域传送和子域名。
# 安装: Kali 软件包 dnsenum。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "dnsenum=${DNSENUM_VERSION}"

# 工具: AutoRecon
# 分类: Network & Reconnaissance
# 描述: 自动编排端口扫描和服务枚举；实际覆盖率取决于镜像内被调用工具。
# 安装: Kali 软件包 autorecon。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "autorecon=${AUTORECON_VERSION}"

# 工具: theHarvester
# 分类: Network & Reconnaissance / OSINT
# 描述: 从公开搜索引擎和数据源收集邮箱、主机名、域名和 IP。
# 安装: Kali 软件包 theharvester；可执行文件名为 theHarvester。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "theharvester=${THEHARVESTER_VERSION}"

# 工具: Responder
# 分类: Network & Reconnaissance / 内网协议分析
# 描述: 监听并分析 LLMNR、NBT-NS、MDNS 等内网名称解析协议。
# 安装: Kali 软件包 responder；运行时通常需要 host 网络或附加网络能力。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "responder=${RESPONDER_VERSION}"

# 工具: NetExec
# 分类: Network & Reconnaissance / Active Directory
# 描述: 枚举和验证 SMB、WinRM、LDAP、MSSQL 等企业网络服务。
# 安装: Kali 软件包 netexec；主命令为 nxc。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "netexec=${NETEXEC_VERSION}"

# 工具: enum4linux-ng
# 分类: Network & Reconnaissance / SMB 枚举
# 描述: 枚举 Windows/Samba 的用户、组、共享、策略和域信息。
# 安装: Kali 软件包 enum4linux-ng。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "enum4linux-ng=${ENUM4LINUX_NG_VERSION}"


# -----------------------------------------------------------------------------
# Web Application Security
# -----------------------------------------------------------------------------

# 工具: Gobuster
# 分类: Web Application Security / 内容发现
# 描述: 枚举目录、文件、DNS 名称和虚拟主机。
# 安装: Kali 软件包 gobuster。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "gobuster=${GOBUSTER_VERSION}"

# 工具: Feroxbuster
# 分类: Web Application Security / 内容发现
# 描述: 递归发现 Web 目录、文件和链接。
# 安装: Kali 软件包 feroxbuster。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "feroxbuster=${FEROXBUSTER_VERSION}"

# 工具: Dirsearch
# 分类: Web Application Security / 内容发现
# 描述: 使用字典发现 Web 目录和文件，支持扩展名与递归扫描。
# 安装: Kali 软件包 dirsearch。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "dirsearch=${DIRSEARCH_VERSION}"

# 工具: FFuf
# 分类: Web Application Security / 模糊测试
# 描述: 对 URL、参数、请求头和虚拟主机进行高速模糊测试。
# 安装: Kali 软件包 ffuf。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "ffuf=${FFUF_VERSION}"

# 工具: Dirb
# 分类: Web Application Security / 内容发现
# 描述: 使用目录字典发现 Web 服务器中的隐藏资源。
# 安装: Kali 软件包 dirb；其 common.txt 同时作为多个 MCP 的默认小字典。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && \
    case "${TARGETARCH}" in \
      amd64) package_version="${DIRB_VERSION_AMD64}" ;; \
      arm64) package_version="${DIRB_VERSION_ARM64}" ;; \
    esac && \
    apt-get install -y --no-install-recommends "dirb=${package_version}"

# 工具: HTTPx
# 分类: Web Application Security / HTTP 探测
# 描述: 批量探测 HTTP 服务、状态码、标题和技术栈。
# MCP 参数契约: 单目标使用 -u，目标文件使用 -l，并使用 -t/-probe/-td/-sc 等
#               httpx 1.9.0 支持的参数；服务端会区分目标字符串和目标文件。
# 安装: Kali 包名为 httpx-toolkit；创建 httpx 兼容命令供 HexStrike 调用。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "httpx-toolkit=${HTTPX_TOOLKIT_VERSION}" && \
    ln -sf /usr/bin/httpx-toolkit /usr/local/bin/httpx

# 工具: Katana
# 分类: Web Application Security / 爬虫
# 描述: 抓取网页、JavaScript 端点和表单；无头浏览器模式需要另装浏览器。
# 安装: Kali 软件包 katana。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "katana=${KATANA_VERSION}"

# 工具: Hakrawler
# 分类: Web Application Security / 爬虫
# 描述: 从标准输入接收 URL，发现链接、脚本端点和表单来源。
# 安装: Kali 软件包 hakrawler。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "hakrawler=${HAKRAWLER_VERSION}"

# 工具: Nikto
# 分类: Web Application Security / Web 服务器检查
# 描述: 检查 Web 服务器危险文件、错误配置和已知风险。
# 安装: 从 nikto-source 阶段复制官方 2.6.1 源码并创建命令包装器。
COPY --from=nikto-source /opt/nikto/ /opt/nikto/
RUN printf '%s\n' '#!/bin/sh' 'exec perl /opt/nikto/program/nikto.pl "$@"' \
      > /usr/local/bin/nikto && chmod 0755 /usr/local/bin/nikto

# 工具: SQLMap
# 分类: Web Application Security / SQL 注入
# 描述: 自动检测、验证并利用 SQL 注入问题。
# 安装: Kali 软件包 sqlmap。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "sqlmap=${SQLMAP_VERSION}"

# 工具: WPScan
# 分类: Web Application Security / WordPress
# 描述: 枚举 WordPress 核心、主题、插件和已知漏洞；漏洞数据库需运行时更新。
# 安装: Kali 当前主仓库没有 wpscan 包，使用 RubyGems 固定安装 4.0.0。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      ruby-full ruby-dev build-essential \
      libcurl4-openssl-dev libxml2-dev libxslt1-dev zlib1g-dev && \
    gem install wpscan --version "${WPSCAN_VERSION}" --no-document

# 工具: Arjun
# 分类: Web Application Security / 参数发现
# 描述: 发现 GET、POST、JSON 等请求中的隐藏 HTTP 参数。
# 安装: Kali 软件包 arjun。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "arjun=${ARJUN_VERSION}"

# 工具: ParamSpider
# 分类: Web Application Security / 参数发现
# 描述: 从历史 URL 数据中提取包含参数的端点。
# MCP 参数契约: 固定使用 1.0.1 的 -d/-s/--proxy/-p；该版本的 -l 表示
#               “域名列表文件”，因此代码不再把 -l 错当成扫描层级。
# 安装: Kali 软件包 paramspider。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "paramspider=${PARAMSPIDER_VERSION}"

# 工具: Dalfox
# 分类: Web Application Security / XSS
# 描述: 发现和验证反射型、存储型及 DOM 型 XSS。
# 安装: Kali 软件包 dalfox。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "dalfox=${DALFOX_VERSION}"

# 工具: Wafw00f
# 分类: Web Application Security / WAF 识别
# 描述: 识别目标使用的 Web 应用防火墙产品。
# 安装: Kali 软件包 wafw00f。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "wafw00f=${WAFW00F_VERSION}"

# 工具: Gau
# 分类: Web Application Security / URL 发现
# 描述: 从多个公开数据源收集历史 URL。
# 安装: 从 go-tools 阶段复制固定版本静态二进制。
COPY --from=go-tools /out/gau /usr/local/bin/gau

# 工具: Waybackurls
# 分类: Web Application Security / URL 发现
# 描述: 从 Wayback Machine 收集历史 URL。
# 安装: 从 go-tools 阶段复制固定版本静态二进制。
COPY --from=go-tools /out/waybackurls /usr/local/bin/waybackurls

# 工具: X8
# 分类: Web Application Security / 参数发现
# 描述: 根据页面响应差异发现隐藏参数。
# 安装: 从 rust-tools 阶段复制固定版本二进制。
COPY --from=rust-tools /out/bin/x8 /usr/local/bin/x8

# 工具: Anew
# 分类: Web Application Security / 数据处理
# 描述: 对扫描管道中的文本行进行去重和增量追加。
# 安装: 从 go-tools 阶段复制固定版本静态二进制。
COPY --from=go-tools /out/anew /usr/local/bin/anew

# 工具: QSReplace
# 分类: Web Application Security / 数据处理
# 描述: 批量替换 URL 查询参数值，便于生成模糊测试输入。
# 安装: Kali 软件包 qsreplace。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "qsreplace=${QSREPLACE_VERSION}"

# 工具: Uro
# 分类: Web Application Security / 数据处理
# 描述: 归并结构相似的 URL，减少重复扫描。
# 安装: Kali 软件包 uro。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "uro=${URO_VERSION}"

# 工具: Wfuzz
# 分类: Web Application Security / 模糊测试
# 描述: 对 HTTP 请求路径、参数、头部和认证位置进行模糊测试。
# 安装: Kali 软件包 wfuzz。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "wfuzz=${WFUZZ_VERSION}"


# -----------------------------------------------------------------------------
# Password & Authentication
# -----------------------------------------------------------------------------

# 工具: Hydra
# 分类: Password & Authentication
# 描述: 对多种网络协议执行在线口令验证和字典测试。
# 安装: Kali 软件包 hydra。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "hydra=${HYDRA_VERSION}"

# 工具: John the Ripper
# 分类: Password & Authentication
# 描述: 对多种密码哈希格式执行离线恢复和强度验证。
# 安装: Kali 软件包 john；大型字典不纳入镜像。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "john=${JOHN_VERSION}"

# 工具: Hashcat
# 分类: Password & Authentication
# 描述: 使用 CPU、GPU 或其他加速设备进行离线哈希恢复。
# 安装: Kali 软件包 hashcat；GPU 使用还需要宿主机驱动和设备透传。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "hashcat=${HASHCAT_VERSION}"

# 工具: Medusa
# 分类: Password & Authentication
# 描述: 并行验证多种远程服务的认证凭据。
# 安装: Kali 软件包 medusa。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "medusa=${MEDUSA_VERSION}"

# 工具: Patator
# 分类: Password & Authentication
# 描述: 模块化、多协议的认证测试和口令验证工具。
# 安装: Kali 软件包 patator。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "patator=${PATATOR_VERSION}"

# 工具: CrackMapExec
# 分类: Password & Authentication / Active Directory
# 描述: 枚举和验证 Windows/Active Directory 环境中的凭据与访问权限。
# 安装: Kali 软件包 crackmapexec；同时保留较新的 NetExec，二者命令不互相替代。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "crackmapexec=${CRACKMAPEXEC_VERSION}"

# 工具: Evil-WinRM
# 分类: Password & Authentication / Windows 远程管理
# 描述: 通过 WinRM 连接到已获授权的 Windows 主机并执行管理操作。
# 安装: Kali 软件包 evil-winrm。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "evil-winrm=${EVIL_WINRM_VERSION}"

# 工具: Hash-Identifier
# 分类: Password & Authentication / 哈希识别
# 描述: 根据哈希的长度和字符特征推测可能的算法类型。
# 安装: Kali 软件包 hash-identifier。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "hash-identifier=${HASH_IDENTIFIER_VERSION}"

# 工具: Ophcrack
# 分类: Password & Authentication / Windows 哈希恢复
# 描述: 使用彩虹表恢复 Windows LM/NTLM 哈希；彩虹表不纳入镜像。
# 安装: 使用 Kali 的无图形界面包 ophcrack-cli，避免 Qt/X11 依赖。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && \
    case "${TARGETARCH}" in \
      amd64) package_version="${OPHCRACK_CLI_VERSION_AMD64}" ;; \
      arm64) package_version="${OPHCRACK_CLI_VERSION_ARM64}" ;; \
    esac && \
    apt-get install -y --no-install-recommends "ophcrack-cli=${package_version}"


# -----------------------------------------------------------------------------
# Binary Analysis & Reverse Engineering
# -----------------------------------------------------------------------------

# 工具: GDB
# 分类: Binary Analysis & Reverse Engineering
# 描述: 调试本地程序、检查寄存器、内存、断点和调用栈。
# 安装: Kali 软件包 gdb。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "gdb=${GDB_VERSION}"

# 工具: Radare2
# 分类: Binary Analysis & Reverse Engineering
# 描述: 提供反汇编、调试、二进制修补和脚本化分析能力。
# 安装: Kali 软件包 radare2。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "radare2=${RADARE2_VERSION}"

# 工具: Binwalk
# 分类: Binary Analysis & Reverse Engineering
# 描述: 识别固件和二进制中的嵌入文件、签名及压缩数据。
# 安装: Kali 软件包 binwalk。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "binwalk=${BINWALK_VERSION}"

# 工具: Ghidra
# 分类: Binary Analysis & Reverse Engineering
# 描述: 提供反编译、反汇编和 headless 自动分析；该工具会显著增大镜像。
# 安装: Kali 软件包 ghidra，Java 运行时由软件包依赖安装；为 MCP 使用的
#       analyzeHeadless 创建稳定 PATH 入口。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "ghidra=${GHIDRA_VERSION}" && \
    ghidra_headless="$(find /usr/share/ghidra -type f -name analyzeHeadless -print -quit)" && \
    test -n "${ghidra_headless}" && \
    ln -sf "${ghidra_headless}" /usr/local/bin/analyzeHeadless

# 工具: Checksec
# 分类: Binary Analysis & Reverse Engineering
# 描述: 检查 ELF/进程的 PIE、RELRO、NX、Canary 等安全机制。
# 安装: Kali 软件包 checksec。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "checksec=${CHECKSEC_VERSION}"

# 工具: Strings
# 分类: Binary Analysis & Reverse Engineering / 共享基础工具
# 描述: 从二进制文件中提取可打印字符串。
# 安装: strings 由 Kali 软件包 binutils 提供。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "binutils=${BINUTILS_VERSION}"

# 工具: Objdump
# 分类: Binary Analysis & Reverse Engineering / 共享基础工具
# 描述: 查看对象文件的段、符号和反汇编结果。
# 安装: objdump 与 strings 共享 Kali 软件包 binutils；此命令确认依赖归属。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "binutils=${BINUTILS_VERSION}"

# 工具: XXD
# 分类: Binary Analysis & Reverse Engineering / 共享基础工具
# 描述: 创建十六进制转储并把十六进制数据还原为二进制。
# 安装: Kali 软件包 xxd。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "xxd=${XXD_VERSION}"

# 工具: Foremost
# 分类: Binary Analysis & Reverse Engineering / 数字取证
# 描述: 根据文件头、文件尾和数据结构从镜像中恢复文件。
# 安装: Kali 软件包 foremost。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && \
    case "${TARGETARCH}" in \
      amd64) package_version="${FOREMOST_VERSION_AMD64}" ;; \
      arm64) package_version="${FOREMOST_VERSION_ARM64}" ;; \
    esac && \
    apt-get install -y --no-install-recommends "foremost=${package_version}"

# 工具: Steghide
# 分类: Binary Analysis & Reverse Engineering / 隐写分析
# 描述: 在 JPEG、BMP、WAV、AU 等载体中嵌入或提取隐藏数据。
# 安装: Kali 软件包 steghide。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "steghide=${STEGHIDE_VERSION}"

# 工具: ExifTool
# 分类: Binary Analysis & Reverse Engineering / 元数据分析
# 描述: 读取、写入和比较多种文件格式的元数据。
# 安装: Kali 包名为 libimage-exiftool-perl，提供 exiftool 命令。
RUN --mount=type=cache,id=hexstrike-apt-lists-${TARGETARCH},target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,id=hexstrike-apt-cache-${TARGETARCH},target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      "libimage-exiftool-perl=${EXIFTOOL_VERSION}"


# 工具版本清单
# 分类: 镜像可审计性
# 描述: 将实际安装的包版本、架构以及源码安装工具版本写入最终镜像。
# 安装: 读取 dpkg 数据库生成 /opt/hexstrike/tool-versions.lock。
RUN install -d /opt/hexstrike && \
    locked_packages=( \
      nmap masscan rustscan amass subfinder nuclei fierce dnsenum autorecon \
      theharvester responder netexec enum4linux-ng gobuster feroxbuster \
      dirsearch ffuf dirb httpx-toolkit katana hakrawler sqlmap arjun \
      paramspider dalfox wafw00f qsreplace uro wfuzz hydra john hashcat \
      medusa patator crackmapexec evil-winrm hash-identifier ophcrack-cli \
      gdb radare2 binwalk ghidra checksec binutils xxd foremost steghide \
      libimage-exiftool-perl \
    ) && \
    { \
      printf '# tool\tversion\tarchitecture\n'; \
      dpkg-query -W -f='${Package}\t${Version}\t${Architecture}\n' \
        "${locked_packages[@]}" | sort; \
      printf 'nikto\t2.6.1\tall\n'; \
      printf 'wpscan\t%s\tall\n' "${WPSCAN_VERSION}"; \
      printf 'gau\tv2.2.4\t%s\n' "${TARGETARCH}"; \
      printf 'waybackurls\tv0.1.0\t%s\n' "${TARGETARCH}"; \
      printf 'anew\tv0.1.1\t%s\n' "${TARGETARCH}"; \
      printf 'x8\t4.3.0\t%s\n' "${TARGETARCH}"; \
    } > /opt/hexstrike/tool-versions.lock


# -----------------------------------------------------------------------------
# 共享字典与工具数据路径
# -----------------------------------------------------------------------------
# 只复制工具正常启动所需的小型字典。SecLists、Nuclei 模板、彩虹表、
# Volatility 符号表等大型数据应在运行时通过只读卷挂载。
RUN install -d \
      /usr/share/wordlists/dirb \
      /usr/share/wordlists/dirsearch \
      /usr/share/wordlists/x8 && \
    dirb_words="$(find /usr/share -type f -path '*dirb*' -name common.txt -print -quit)" && \
    test -n "${dirb_words}" && \
    if [ "${dirb_words}" != /usr/share/wordlists/dirb/common.txt ]; then \
      cp "${dirb_words}" /usr/share/wordlists/dirb/common.txt; \
    fi && \
    cp /usr/share/wordlists/dirb/common.txt \
      /usr/share/wordlists/dirsearch/common.txt && \
    arjun_words="$(find /usr -type f -path '*arjun*' \
      \( -name large.txt -o -name small.txt \) -print -quit)" && \
    test -n "${arjun_words}" && \
    cp "${arjun_words}" /usr/share/wordlists/x8/params.txt


# =============================================================================
# Python 3.11 环境阶段：安装 Volatility3 和 HexStrike Python 依赖
# =============================================================================
FROM --platform=${TARGETPLATFORM} python:3.11-slim-bookworm AS python-runtime

ARG PIP_VERSION=25.3
ARG SETUPTOOLS_VERSION=80.9.0
ARG WHEEL_VERSION=0.45.1

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN python3 -m venv /opt/hexstrike-venv && \
    /opt/hexstrike-venv/bin/python -m pip install \
      "pip==${PIP_VERSION}" \
      "setuptools==${SETUPTOOLS_VERSION}" \
      "wheel==${WHEEL_VERSION}"

# 工具: Volatility3
# 分类: Binary Analysis & Reverse Engineering / 内存取证
# 描述: 从 Windows、Linux 等内存镜像中提取进程、模块、网络和其他取证信息。
# MCP 参数契约: 使用 2.28.2 的 vol -f IMAGE [-o DIR] PLUGIN 语法；
#               不使用 Volatility2 的 profile 参数或 volatility 命令名。
# 安装: Kali 主仓库没有 volatility3 包，使用 PyPI 固定安装 2.28.2；符号表不内置。
ARG VOLATILITY3_VERSION=2.28.2
RUN /opt/hexstrike-venv/bin/python -m pip install \
      "volatility3==${VOLATILITY3_VERSION}"

# HexStrike Python 运行依赖
# 说明: requirements.txt 在工具层完成后才复制，以保持工具安装缓存。
# pwntools、angr 和 bcrypt 对应未纳入本镜像的可选二进制分析 Python 端点，
# 因此从本镜像的运行依赖中排除；外部 GDB/Radare2 等工具仍然完整安装。
WORKDIR /build
COPY requirements.txt ./
RUN sed -E '/^(pwntools|angr|bcrypt)([<=>]|$)/d' requirements.txt \
      > requirements-runtime.txt && \
    /opt/hexstrike-venv/bin/python -m pip install -r requirements-runtime.txt && \
    /opt/hexstrike-venv/bin/python -m pip check


# =============================================================================
# 最终镜像：继承全部工具，最后复制 Python 环境和本项目代码
# =============================================================================
FROM security-tools AS runtime

# Python 3.11 解释器和虚拟环境在全部外部工具安装完成后进入最终镜像。
COPY --from=python-runtime /usr/local/ /usr/local/
COPY --from=python-runtime /opt/hexstrike-venv/ /opt/hexstrike-venv/

# Volatility3 版本复核并写入统一工具版本清单。
ARG VOLATILITY3_VERSION=2.28.2
RUN installed_version="$(python3 -c \
      'from importlib.metadata import version; print(version("volatility3"))')" && \
    test "${installed_version}" = "${VOLATILITY3_VERSION}" && \
    printf 'volatility3\t%s\tall\n' "${installed_version}" \
      >> /opt/hexstrike/tool-versions.lock

# 构建期工具覆盖检查：验证上文每个工具段落最终都提供了预期命令。
# 此检查只确认安装和命令发现，不会对任何外部目标执行扫描。
RUN expected_commands=( \
      nmap masscan rustscan amass subfinder nuclei fierce dnsenum autorecon \
      theHarvester responder nxc enum4linux-ng gobuster feroxbuster dirsearch \
      ffuf dirb httpx katana hakrawler nikto sqlmap wpscan arjun paramspider \
      dalfox wafw00f gau waybackurls x8 anew qsreplace uro wfuzz hydra john \
      hashcat medusa patator crackmapexec evil-winrm hash-identifier \
      ophcrack-cli gdb r2 radare2 binwalk ghidra analyzeHeadless checksec \
      strings objdump xxd \
      vol foremost steghide exiftool \
    ) && \
    for command_name in "${expected_commands[@]}"; do \
      command -v "${command_name}" >/dev/null || { \
        echo "缺少工具命令: ${command_name}" >&2; exit 1; \
      }; \
    done

# 最后复制本系统代码。此后仅做本项目检查和运行时配置，不再安装外部工具。
WORKDIR /opt/hexstrike
COPY hexstrike_server.py hexstrike_mcp.py ./

# 验证服务启动所需 Python 模块和项目源文件语法。
RUN python3 -c 'import aiohttp, bs4, flask, mcp, mitmproxy, psutil, requests, selenium' && \
    python3 -m py_compile hexstrike_server.py hexstrike_mcp.py

EXPOSE 8888

# /health 返回服务和工具可用性状态；非 2xx 响应会让容器进入 unhealthy。
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD python3 -c "import requests; response=requests.get('http://127.0.0.1:8888/health', timeout=4); response.raise_for_status()"

# tini 负责转发信号和回收子进程；默认启动 HexStrike HTTP API 服务。
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python3", "/opt/hexstrike/hexstrike_server.py", "--port", "8888"]
