#!/usr/bin/env bash
set -euo pipefail

# 本类别工具的固定版本；修改工具时在本文件同步检查安装方式。
NMAP_VERSION=7.991+dfsg-1kali1
MASSCAN_VERSION_AMD64=2:1.3.2+ds1-2
MASSCAN_VERSION_ARM64=2:1.3.2+ds1-2+b1
RUSTSCAN_VERSION=2.4.1-0kali1
AMASS_VERSION=5.1.1-0kali3
SUBFINDER_VERSION=2.16.0-0kali1
NUCLEI_VERSION=3.11.1-0kali1
FIERCE_VERSION=1.6.0-2
DNSENUM_VERSION=1.3.2-1
AUTORECON_VERSION=0.0~git20251116.e7e98f6-0kali1
THEHARVESTER_VERSION=4.11.1-0kali2
RESPONDER_VERSION=3.2.2.0-0kali2
NETEXEC_VERSION=1.5.1-0kali2
ENUM4LINUX_NG_VERSION=1.3.10-0kali1
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# 同一类别共用一次成功的索引更新，随后仍逐项安装精确版本。
apt-get -o APT::Update::Error-Mode=any update

# 每个原始安装步骤在独立子进程中执行，任意 && 链失败均立即中止整个脚本。
# 工具: Nmap
# 分类: Network & Reconnaissance
# 描述: 主机发现、端口扫描、服务识别、操作系统识别和 NSE 检查。
# 安装: Kali 软件包 nmap。
(
apt-get install -y --no-install-recommends \
      "nmap=${NMAP_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt nmap "${NMAP_VERSION}" "${TARGETARCH}"
)

# 工具: Masscan
# 分类: Network & Reconnaissance
# 描述: 针对大量 IP 的高速异步端口扫描器；运行时可能需要额外网络能力。
# 安装: Kali 软件包 masscan。
(
case "${TARGETARCH}" in \
      amd64) package_version="${MASSCAN_VERSION_AMD64}" ;; \
      arm64) package_version="${MASSCAN_VERSION_ARM64}" ;; \
    esac && \
    apt-get install -y --no-install-recommends "masscan=${package_version}" && \
    bash "${script_dir}/record-tool-version.sh" apt masscan "${package_version}" "${TARGETARCH}"
)

# 工具: RustScan
# 分类: Network & Reconnaissance
# 描述: 快速发现开放端口，并可把结果交给 Nmap 深入扫描。
# 安装: Kali 软件包 rustscan。
(
apt-get install -y --no-install-recommends \
      "rustscan=${RUSTSCAN_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt rustscan "${RUSTSCAN_VERSION}" "${TARGETARCH}"
)

# 工具: Amass
# 分类: Network & Reconnaissance
# 描述: 收集子域名、DNS 关系和外部攻击面信息。
# 安装: Kali 软件包 amass。
(
apt-get install -y --no-install-recommends \
      "amass=${AMASS_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt amass "${AMASS_VERSION}" "${TARGETARCH}"
)

# 工具: Subfinder
# 分类: Network & Reconnaissance
# 描述: 使用公开数据源进行被动子域名发现；部分数据源需要 API Key。
# 安装: Kali 软件包 subfinder。
(
apt-get install -y --no-install-recommends \
      "subfinder=${SUBFINDER_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt subfinder "${SUBFINDER_VERSION}" "${TARGETARCH}"
)

# 工具: Nuclei
# 分类: Network & Reconnaissance / Web 漏洞扫描
# 描述: 使用模板检查服务和 Web 应用中的漏洞及配置问题。
# 安装: Kali 软件包 nuclei；不在构建中执行 update-templates，避免模板随构建漂移。
#       如需模板，请按版本通过只读卷挂载到运行容器。
(
apt-get install -y --no-install-recommends \
      "nuclei=${NUCLEI_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt nuclei "${NUCLEI_VERSION}" "${TARGETARCH}"
)

# 工具: Fierce
# 分类: Network & Reconnaissance
# 描述: 进行 DNS 枚举并发现与目标域名关联的主机。
# 安装: Kali 软件包 fierce。
(
apt-get install -y --no-install-recommends \
      "fierce=${FIERCE_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt fierce "${FIERCE_VERSION}" "${TARGETARCH}"
)

# 工具: DNSenum
# 分类: Network & Reconnaissance
# 描述: 枚举 DNS 记录、名称服务器、区域传送和子域名。
# 安装: Kali 软件包 dnsenum。
(
apt-get install -y --no-install-recommends \
      "dnsenum=${DNSENUM_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt dnsenum "${DNSENUM_VERSION}" "${TARGETARCH}"
)

# 工具: AutoRecon
# 分类: Network & Reconnaissance
# 描述: 自动编排端口扫描和服务枚举；实际覆盖率取决于镜像内被调用工具。
# 安装: Kali 软件包 autorecon。
(
apt-get install -y --no-install-recommends \
      "autorecon=${AUTORECON_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt autorecon "${AUTORECON_VERSION}" "${TARGETARCH}"
)

# 工具: theHarvester
# 分类: Network & Reconnaissance / OSINT
# 描述: 从公开搜索引擎和数据源收集邮箱、主机名、域名和 IP。
# 安装: Kali 软件包 theharvester；可执行文件名为 theHarvester。
(
apt-get install -y --no-install-recommends \
      "theharvester=${THEHARVESTER_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt theharvester "${THEHARVESTER_VERSION}" "${TARGETARCH}"
)

# 工具: Responder
# 分类: Network & Reconnaissance / 内网协议分析
# 描述: 监听并分析 LLMNR、NBT-NS、MDNS 等内网名称解析协议。
# 安装: Kali 软件包 responder；运行时通常需要 host 网络或附加网络能力。
(
apt-get install -y --no-install-recommends \
      "responder=${RESPONDER_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt responder "${RESPONDER_VERSION}" "${TARGETARCH}"
)

# 工具: NetExec
# 分类: Network & Reconnaissance / Active Directory
# 描述: 枚举和验证 SMB、WinRM、LDAP、MSSQL 等企业网络服务。
# 安装: Kali 软件包 netexec；主命令为 nxc。
(
apt-get install -y --no-install-recommends \
      "netexec=${NETEXEC_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt netexec "${NETEXEC_VERSION}" "${TARGETARCH}"
)

# 工具: enum4linux-ng
# 分类: Network & Reconnaissance / SMB 枚举
# 描述: 枚举 Windows/Samba 的用户、组、共享、策略和域信息。
# 安装: Kali 软件包 enum4linux-ng。
(
apt-get install -y --no-install-recommends \
      "enum4linux-ng=${ENUM4LINUX_NG_VERSION}" && \
    bash "${script_dir}/record-tool-version.sh" apt enum4linux-ng "${ENUM4LINUX_NG_VERSION}" "${TARGETARCH}"
)
