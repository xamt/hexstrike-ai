#!/usr/bin/env bash
# osint 类 APT 工具；版本与安装定义在同一文件，任意失败立即停止。
set -euo pipefail

TRUFFLEHOG_VERSION=3.97.9-0kali1
AMASS_VERSION=5.1.1-0kali3
SUBFINDER_VERSION=2.16.0-0kali1
THEHARVESTER_VERSION=4.11.1-0kali2

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${TARGETARCH:?缺少目标架构}" in
    amd64|arm64) ;;
    *) echo "不支持的架构: ${TARGETARCH}" >&2; exit 1 ;;
esac

apt-get -o APT::Update::Error-Mode=any update

# 工具: Amass
# 描述: 收集子域名、DNS 关系和外部攻击面信息。
# 安装: Kali 软件包 amass。
(
apt-get install -y --no-install-recommends \
      "amass=${AMASS_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt amass "${AMASS_VERSION}" "${TARGETARCH}"
)

# 工具: Subfinder
# 描述: 使用公开数据源进行被动子域名发现；部分数据源需要 API Key。
# 安装: Kali 软件包 subfinder。
(
apt-get install -y --no-install-recommends \
      "subfinder=${SUBFINDER_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt subfinder "${SUBFINDER_VERSION}" "${TARGETARCH}"
)

# 工具: theHarvester
# 描述: 从公开搜索引擎和数据源收集邮箱、主机名、域名和 IP。
# 安装: Kali 软件包 theharvester；可执行文件名为 theHarvester。
(
apt-get install -y --no-install-recommends \
      "theharvester=${THEHARVESTER_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt theharvester "${THEHARVESTER_VERSION}" "${TARGETARCH}"
)

# 工具: TruffleHog
(
apt-get install -y --no-install-recommends "trufflehog=${TRUFFLEHOG_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt trufflehog "${TRUFFLEHOG_VERSION}" "${TARGETARCH}"
)
