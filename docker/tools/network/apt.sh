#!/usr/bin/env bash
# network 类 APT 工具；版本与安装定义在同一文件，任意失败立即停止。
set -euo pipefail

TCPDUMP_VERSION=4.99.6-2
NMAP_VERSION=7.991+dfsg-1kali1
MASSCAN_VERSION_AMD64=2:1.3.2+ds1-2
MASSCAN_VERSION_ARM64=2:1.3.2+ds1-2+b1
RUSTSCAN_VERSION=2.4.1-0kali1
FIERCE_VERSION=1.6.0-2
DNSENUM_VERSION=1.3.2-1
AUTORECON_VERSION=0.0~git20251116.e7e98f6-0kali1
ENUM4LINUX_NG_VERSION=1.3.10-0kali1

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${TARGETARCH:?缺少目标架构}" in
    amd64|arm64) ;;
    *) echo "不支持的架构: ${TARGETARCH}" >&2; exit 1 ;;
esac

apt-get -o APT::Update::Error-Mode=any update

# 工具: Nmap
# 描述: 主机发现、端口扫描、服务识别、操作系统识别和 NSE 检查。
# 安装: Kali 软件包 nmap。
(
apt-get install -y --no-install-recommends \
      "nmap=${NMAP_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt nmap "${NMAP_VERSION}" "${TARGETARCH}"
)

# 工具: Masscan
# 描述: 针对大量 IP 的高速异步端口扫描器；运行时可能需要额外网络能力。
# 安装: Kali 软件包 masscan。
(
case "${TARGETARCH}" in \
      amd64) package_version="${MASSCAN_VERSION_AMD64}" ;; \
      arm64) package_version="${MASSCAN_VERSION_ARM64}" ;; \
    esac && \
    apt-get install -y --no-install-recommends "masscan=${package_version}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt masscan "${package_version}" "${TARGETARCH}"
)

# 工具: RustScan
# 描述: 快速发现开放端口，并可把结果交给 Nmap 深入扫描。
# 安装: Kali 软件包 rustscan。
(
apt-get install -y --no-install-recommends \
      "rustscan=${RUSTSCAN_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt rustscan "${RUSTSCAN_VERSION}" "${TARGETARCH}"
)

# 工具: Fierce
# 描述: 进行 DNS 枚举并发现与目标域名关联的主机。
# 安装: Kali 软件包 fierce。
(
apt-get install -y --no-install-recommends \
      "fierce=${FIERCE_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt fierce "${FIERCE_VERSION}" "${TARGETARCH}"
)

# 工具: DNSenum
# 描述: 枚举 DNS 记录、名称服务器、区域传送和子域名。
# 安装: Kali 软件包 dnsenum。
(
apt-get install -y --no-install-recommends \
      "dnsenum=${DNSENUM_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt dnsenum "${DNSENUM_VERSION}" "${TARGETARCH}"
)

# 工具: AutoRecon
# 描述: 自动编排端口扫描和服务枚举；实际覆盖率取决于镜像内被调用工具。
# 安装: Kali 软件包 autorecon。
(
apt-get install -y --no-install-recommends \
      "autorecon=${AUTORECON_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt autorecon "${AUTORECON_VERSION}" "${TARGETARCH}"
)

# 工具: enum4linux-ng
# 描述: 枚举 Windows/Samba 的用户、组、共享、策略和域信息。
# 安装: Kali 软件包 enum4linux-ng。
(
apt-get install -y --no-install-recommends \
      "enum4linux-ng=${ENUM4LINUX_NG_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt enum4linux-ng "${ENUM4LINUX_NG_VERSION}" "${TARGETARCH}"
)

# 工具: tcpdump
(
apt-get install -y --no-install-recommends "tcpdump=${TCPDUMP_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt tcpdump "${TCPDUMP_VERSION}" "${TARGETARCH}"
)

# AUTORECON_SMALL_DATA
# 在 APT 安装的同一层从 SecLists 缓存保留默认枚举必需的小字典。
# 不在后续层依赖缓存仍然存在，不复制整个 SecLists，也不缩减原字典覆盖。
autorecon_data=/opt/pentest-tools-compat/autorecon-data
autorecon_wordlists=(
    Discovery/DNS/subdomains-top1million-110000.txt
    Usernames/top-usernames-shortlist.txt
    Discovery/SNMP/common-snmp-community-strings-onesixtyone.txt
)
for relative in "${autorecon_wordlists[@]}"; do
    test -s "/usr/share/seclists/${relative}"
    install -d "${autorecon_data}/$(dirname -- "${relative}")"
    install -m 0644 "/usr/share/seclists/${relative}" "${autorecon_data}/${relative}"
done
printf '%s\n' "${autorecon_wordlists[@]}" > "${autorecon_data}/manifest.txt"
