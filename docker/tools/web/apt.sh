#!/usr/bin/env bash
# web 类 APT 工具；版本与安装定义在同一文件，任意失败立即停止。
set -euo pipefail

GOBUSTER_VERSION=3.8.2-1
FEROXBUSTER_VERSION=2.13.1-0kali3
DIRSEARCH_VERSION=0.4.3-1
FFUF_VERSION=2.2.1-1
DIRB_VERSION_AMD64=2.22+dfsg-7
DIRB_VERSION_ARM64=2.22+dfsg-7+b1
HTTPX_TOOLKIT_VERSION=1.9.0-0kali2
KATANA_VERSION=1.7.0-0kali1
HAKRAWLER_VERSION=2.1-0kali1
SQLMAP_VERSION=1.10.9-1
ARJUN_VERSION=2.2.7-1
WAFW00F_VERSION=2.4.2-1
QSREPLACE_VERSION=0.0.3-0kali1
URO_VERSION=1.0.2-0kali1
WFUZZ_VERSION=3.1.1-1
TESTSSL_VERSION=3.2.4+dfsg-2
WHATWEB_VERSION=0.6.4-1
NUCLEI_VERSION=3.11.1-0kali1

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${TARGETARCH:?缺少目标架构}" in
    amd64|arm64) ;;
    *) echo "不支持的架构: ${TARGETARCH}" >&2; exit 1 ;;
esac

apt-get -o APT::Update::Error-Mode=any update

# 工具: Gobuster
# 描述: 枚举目录、文件、DNS 名称和虚拟主机。
# 安装: Kali 软件包 gobuster。
(
apt-get install -y --no-install-recommends \
      "gobuster=${GOBUSTER_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt gobuster "${GOBUSTER_VERSION}" "${TARGETARCH}"
)

# 工具: Feroxbuster
# 描述: 递归发现 Web 目录、文件和链接。
# 安装: Kali 软件包 feroxbuster。
(
apt-get install -y --no-install-recommends \
      "feroxbuster=${FEROXBUSTER_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt feroxbuster "${FEROXBUSTER_VERSION}" "${TARGETARCH}"
)

# 工具: Dirsearch
# 描述: 使用字典发现 Web 目录和文件，支持扩展名与递归扫描。
# 安装: Kali 软件包 dirsearch。
(
apt-get install -y --no-install-recommends \
      "dirsearch=${DIRSEARCH_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt dirsearch "${DIRSEARCH_VERSION}" "${TARGETARCH}"
)

# 工具: FFuf
# 描述: 对 URL、参数、请求头和虚拟主机进行高速模糊测试。
# 安装: Kali 软件包 ffuf。
(
apt-get install -y --no-install-recommends \
      "ffuf=${FFUF_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt ffuf "${FFUF_VERSION}" "${TARGETARCH}"
)

# 工具: Dirb
# 描述: 使用目录字典发现 Web 服务器中的隐藏资源。
# 安装: Kali 软件包 dirb；其 common.txt 同时作为多个 MCP 的默认小字典。
(
case "${TARGETARCH}" in \
      amd64) package_version="${DIRB_VERSION_AMD64}" ;; \
      arm64) package_version="${DIRB_VERSION_ARM64}" ;; \
    esac && \
    apt-get install -y --no-install-recommends "dirb=${package_version}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt dirb "${package_version}" "${TARGETARCH}"
)

# 工具: HTTPx
# 描述: 批量探测 HTTP 服务、状态码、标题和技术栈。
# MCP 参数契约: 单目标使用 -u，目标文件使用 -l，并使用 -t/-probe/-td/-sc 等
#               httpx 1.9.0 支持的参数；服务端会区分目标字符串和目标文件。
# 安装: Kali 包名为 httpx-toolkit；创建 httpx 兼容命令供 HexStrike 调用。
(
apt-get install -y --no-install-recommends \
      "httpx-toolkit=${HTTPX_TOOLKIT_VERSION}" && \
    ln -sf /usr/bin/httpx-toolkit /usr/local/bin/httpx && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt httpx-toolkit "${HTTPX_TOOLKIT_VERSION}" "${TARGETARCH}"
)

# 工具: Katana
# 描述: 抓取网页、JavaScript 端点和表单；无头浏览器模式需要另装浏览器。
# 安装: Kali 软件包 katana。
(
apt-get install -y --no-install-recommends \
      "katana=${KATANA_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt katana "${KATANA_VERSION}" "${TARGETARCH}"
)

# 工具: Hakrawler
# 描述: 从标准输入接收 URL，发现链接、脚本端点和表单来源。
# 安装: Kali 软件包 hakrawler。
(
apt-get install -y --no-install-recommends \
      "hakrawler=${HAKRAWLER_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt hakrawler "${HAKRAWLER_VERSION}" "${TARGETARCH}"
)

# 工具: SQLMap
# 描述: 自动检测、验证并利用 SQL 注入问题。
# 安装: Kali 软件包 sqlmap。
(
apt-get install -y --no-install-recommends \
      "sqlmap=${SQLMAP_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt sqlmap "${SQLMAP_VERSION}" "${TARGETARCH}"
)

# 工具: Arjun
# 描述: 发现 GET、POST、JSON 等请求中的隐藏 HTTP 参数。
# 安装: Kali 软件包 arjun。
(
apt-get install -y --no-install-recommends \
      "arjun=${ARJUN_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt arjun "${ARJUN_VERSION}" "${TARGETARCH}"
)

# 工具: Wafw00f
# 描述: 识别目标使用的 Web 应用防火墙产品。
# 安装: Kali 软件包 wafw00f。
(
apt-get install -y --no-install-recommends \
      "wafw00f=${WAFW00F_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt wafw00f "${WAFW00F_VERSION}" "${TARGETARCH}"
)

# 工具: QSReplace
# 描述: 批量替换 URL 查询参数值，便于生成模糊测试输入。
# 安装: Kali 软件包 qsreplace。
(
apt-get install -y --no-install-recommends \
      "qsreplace=${QSREPLACE_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt qsreplace "${QSREPLACE_VERSION}" "${TARGETARCH}"
)

# 工具: Uro
# 描述: 归并结构相似的 URL，减少重复扫描。
# 安装: Kali 软件包 uro。
(
apt-get install -y --no-install-recommends \
      "uro=${URO_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt uro "${URO_VERSION}" "${TARGETARCH}"
)

# 工具: Wfuzz
# 描述: 对 HTTP 请求路径、参数、头部和认证位置进行模糊测试。
# 安装: Kali 软件包 wfuzz。
(
apt-get install -y --no-install-recommends \
      "wfuzz=${WFUZZ_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt wfuzz "${WFUZZ_VERSION}" "${TARGETARCH}"
)

# 工具: Nuclei
# 描述: 使用模板检查服务和 Web 应用中的漏洞及配置问题。
# 安装: Kali 软件包 nuclei；不在构建中执行 update-templates，避免模板随构建漂移。
#       如需模板，请按版本通过只读卷挂载到运行容器。
(
apt-get install -y --no-install-recommends \
      "nuclei=${NUCLEI_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt nuclei "${NUCLEI_VERSION}" "${TARGETARCH}"
)

# 工具: WhatWeb
(
apt-get install -y --no-install-recommends "whatweb=${WHATWEB_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt whatweb "${WHATWEB_VERSION}" "${TARGETARCH}"
)

# 工具: testssl.sh
(
apt-get install -y --no-install-recommends "testssl.sh=${TESTSSL_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt testssl.sh "${TESTSSL_VERSION}" "${TARGETARCH}"
)
