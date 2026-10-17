#!/usr/bin/env bash
set -euo pipefail

# 本类别工具的固定版本；修改工具时在本文件同步检查安装方式。
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
WPSCAN_VERSION=4.0.0
ARJUN_VERSION=2.2.7-1
WAFW00F_VERSION=2.4.2-1
QSREPLACE_VERSION=0.0.3-0kali1
URO_VERSION=1.0.2-0kali1
WFUZZ_VERSION=3.1.1-1
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# 同一类别共用一次成功的索引更新，随后仍逐项安装精确版本。
apt-get -o APT::Update::Error-Mode=any update

# 每个原始安装步骤在独立子进程中执行，任意 && 链失败均立即中止整个脚本。
# 工具: Gobuster
# 分类: Web Application Security / 内容发现
# 描述: 枚举目录、文件、DNS 名称和虚拟主机。
# 安装: Kali 软件包 gobuster。
(
apt-get install -y --no-install-recommends \
      "gobuster=${GOBUSTER_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt gobuster "${GOBUSTER_VERSION}" "${TARGETARCH}"
)

# 工具: Feroxbuster
# 分类: Web Application Security / 内容发现
# 描述: 递归发现 Web 目录、文件和链接。
# 安装: Kali 软件包 feroxbuster。
(
apt-get install -y --no-install-recommends \
      "feroxbuster=${FEROXBUSTER_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt feroxbuster "${FEROXBUSTER_VERSION}" "${TARGETARCH}"
)

# 工具: Dirsearch
# 分类: Web Application Security / 内容发现
# 描述: 使用字典发现 Web 目录和文件，支持扩展名与递归扫描。
# 安装: Kali 软件包 dirsearch。
(
apt-get install -y --no-install-recommends \
      "dirsearch=${DIRSEARCH_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt dirsearch "${DIRSEARCH_VERSION}" "${TARGETARCH}"
)

# 工具: FFuf
# 分类: Web Application Security / 模糊测试
# 描述: 对 URL、参数、请求头和虚拟主机进行高速模糊测试。
# 安装: Kali 软件包 ffuf。
(
apt-get install -y --no-install-recommends \
      "ffuf=${FFUF_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt ffuf "${FFUF_VERSION}" "${TARGETARCH}"
)

# 工具: Dirb
# 分类: Web Application Security / 内容发现
# 描述: 使用目录字典发现 Web 服务器中的隐藏资源。
# 安装: Kali 软件包 dirb；其 common.txt 同时作为多个 MCP 的默认小字典。
(
case "${TARGETARCH}" in \
      amd64) package_version="${DIRB_VERSION_AMD64}" ;; \
      arm64) package_version="${DIRB_VERSION_ARM64}" ;; \
    esac && \
    apt-get install -y --no-install-recommends "dirb=${package_version}" && \
    bash "${script_dir}/record-tool-version.sh" apt dirb "${package_version}" "${TARGETARCH}"
)

# 工具: HTTPx
# 分类: Web Application Security / HTTP 探测
# 描述: 批量探测 HTTP 服务、状态码、标题和技术栈。
# MCP 参数契约: 单目标使用 -u，目标文件使用 -l，并使用 -t/-probe/-td/-sc 等
#               httpx 1.9.0 支持的参数；服务端会区分目标字符串和目标文件。
# 安装: Kali 包名为 httpx-toolkit；创建 httpx 兼容命令供 HexStrike 调用。
(
apt-get install -y --no-install-recommends \
      "httpx-toolkit=${HTTPX_TOOLKIT_VERSION}" && \
    ln -sf /usr/bin/httpx-toolkit /usr/local/bin/httpx && \
    bash "${script_dir}/record-tool-version.sh" apt httpx-toolkit "${HTTPX_TOOLKIT_VERSION}" "${TARGETARCH}"
)

# 工具: Katana
# 分类: Web Application Security / 爬虫
# 描述: 抓取网页、JavaScript 端点和表单；无头浏览器模式需要另装浏览器。
# 安装: Kali 软件包 katana。
(
apt-get install -y --no-install-recommends \
      "katana=${KATANA_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt katana "${KATANA_VERSION}" "${TARGETARCH}"
)

# 工具: Hakrawler
# 分类: Web Application Security / 爬虫
# 描述: 从标准输入接收 URL，发现链接、脚本端点和表单来源。
# 安装: Kali 软件包 hakrawler。
(
apt-get install -y --no-install-recommends \
      "hakrawler=${HAKRAWLER_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt hakrawler "${HAKRAWLER_VERSION}" "${TARGETARCH}"
)

# 工具: Nikto
# 分类: Web Application Security / Web 服务器检查
# 描述: 检查 Web 服务器危险文件、错误配置和已知风险。
# 安装: 从 nikto-source 阶段复制固定标签源码并创建命令包装器；版本由其安装脚本维护。
(
printf '%s\n' '#!/bin/sh' 'exec perl /opt/nikto/program/nikto.pl "$@"' \
      > /usr/local/bin/nikto && chmod 0755 /usr/local/bin/nikto
)

# 工具: SQLMap
# 分类: Web Application Security / SQL 注入
# 描述: 自动检测、验证并利用 SQL 注入问题。
# 安装: Kali 软件包 sqlmap。
(
apt-get install -y --no-install-recommends \
      "sqlmap=${SQLMAP_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt sqlmap "${SQLMAP_VERSION}" "${TARGETARCH}"
)

# 工具: WPScan
# 分类: Web Application Security / WordPress
# 描述: 枚举 WordPress 核心、主题、插件和已知漏洞；漏洞数据库需运行时更新。
# 安装: 保留 RubyGems 安装方式，固定版本在本脚本顶部定义。
(
apt-get install -y --no-install-recommends \
      ruby-full ruby-dev build-essential \
      libcurl4-openssl-dev libxml2-dev libxslt1-dev zlib1g-dev && \
    gem install wpscan --version "${WPSCAN_VERSION}" --no-document && \
    bash "${script_dir}/record-tool-version.sh" gem wpscan "${WPSCAN_VERSION}" "all"
)

# 工具: Arjun
# 分类: Web Application Security / 参数发现
# 描述: 发现 GET、POST、JSON 等请求中的隐藏 HTTP 参数。
# 安装: Kali 软件包 arjun。
(
apt-get install -y --no-install-recommends \
      "arjun=${ARJUN_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt arjun "${ARJUN_VERSION}" "${TARGETARCH}"
)

# ParamSpider 在独立 Python 运行时阶段安装兼容原接口的固定源码。

# Dalfox 在 Go 阶段编译固定 v2 版本，原生保留旧接口的参数能力。

# 工具: Wafw00f
# 分类: Web Application Security / WAF 识别
# 描述: 识别目标使用的 Web 应用防火墙产品。
# 安装: Kali 软件包 wafw00f。
(
apt-get install -y --no-install-recommends \
      "wafw00f=${WAFW00F_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt wafw00f "${WAFW00F_VERSION}" "${TARGETARCH}"
)

# 工具: Gau
# 分类: Web Application Security / URL 发现
# 描述: 从多个公开数据源收集历史 URL。
# 安装: 从 go-tools 阶段复制固定版本静态二进制。

# 工具: Waybackurls
# 分类: Web Application Security / URL 发现
# 描述: 从 Wayback Machine 收集历史 URL。
# 安装: 从 go-tools 阶段复制固定版本静态二进制。

# 工具: X8
# 分类: Web Application Security / 参数发现
# 描述: 根据页面响应差异发现隐藏参数。
# 安装: 从 rust-tools 阶段复制固定版本二进制。

# 工具: Anew
# 分类: Web Application Security / 数据处理
# 描述: 对扫描管道中的文本行进行去重和增量追加。
# 安装: 从 go-tools 阶段复制固定版本静态二进制。

# 工具: QSReplace
# 分类: Web Application Security / 数据处理
# 描述: 批量替换 URL 查询参数值，便于生成模糊测试输入。
# 安装: Kali 软件包 qsreplace。
(
apt-get install -y --no-install-recommends \
      "qsreplace=${QSREPLACE_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt qsreplace "${QSREPLACE_VERSION}" "${TARGETARCH}"
)

# 工具: Uro
# 分类: Web Application Security / 数据处理
# 描述: 归并结构相似的 URL，减少重复扫描。
# 安装: Kali 软件包 uro。
(
apt-get install -y --no-install-recommends \
      "uro=${URO_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt uro "${URO_VERSION}" "${TARGETARCH}"
)

# 工具: Wfuzz
# 分类: Web Application Security / 模糊测试
# 描述: 对 HTTP 请求路径、参数、头部和认证位置进行模糊测试。
# 安装: Kali 软件包 wfuzz。
(
apt-get install -y --no-install-recommends \
      "wfuzz=${WFUZZ_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt wfuzz "${WFUZZ_VERSION}" "${TARGETARCH}"
)
