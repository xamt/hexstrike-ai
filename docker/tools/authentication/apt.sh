#!/usr/bin/env bash
# authentication 类 APT 工具；版本与安装定义在同一文件，任意失败立即停止。
set -euo pipefail

HYDRA_VERSION=9.7-2
JOHN_VERSION=1.9.0-Jumbo-1+git20211102-0kali11
HASHCAT_VERSION=7.1.2+ds1-4
MEDUSA_VERSION=2.3-3
PATATOR_VERSION=1.1.0-1
CRACKMAPEXEC_VERSION=5.4.0-0kali7
EVIL_WINRM_VERSION=4.1-0kali1
HASH_IDENTIFIER_VERSION=1.2+git20180314-0kali3
OPHCRACK_CLI_VERSION_AMD64=3.8.0-4
OPHCRACK_CLI_VERSION_ARM64=3.8.0-4+b1
RESPONDER_VERSION=3.2.2.0-0kali2
NETEXEC_VERSION=1.5.1-0kali2

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${TARGETARCH:?缺少目标架构}" in
    amd64|arm64) ;;
    *) echo "不支持的架构: ${TARGETARCH}" >&2; exit 1 ;;
esac

apt-get -o APT::Update::Error-Mode=any update

# 工具: Responder
# 描述: 监听并分析 LLMNR、NBT-NS、MDNS 等内网名称解析协议。
# 安装: Kali 软件包 responder；运行时通常需要 host 网络或附加网络能力。
(
apt-get install -y --no-install-recommends \
      "responder=${RESPONDER_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt responder "${RESPONDER_VERSION}" "${TARGETARCH}"
)

# 工具: NetExec
# 描述: 枚举和验证 SMB、WinRM、LDAP、MSSQL 等企业网络服务。
# 安装: Kali 软件包 netexec；主命令为 nxc。
(
apt-get install -y --no-install-recommends \
      "netexec=${NETEXEC_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt netexec "${NETEXEC_VERSION}" "${TARGETARCH}"
)

# 工具: Hydra
# 描述: 对多种网络协议执行在线口令验证和字典测试。
# 安装: Kali 软件包 hydra。
(
apt-get install -y --no-install-recommends \
      "hydra=${HYDRA_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt hydra "${HYDRA_VERSION}" "${TARGETARCH}"
)

# 工具: John the Ripper
# 描述: 对多种密码哈希格式执行离线恢复和强度验证。
# 安装: Kali 软件包 john；大型字典不纳入镜像。
(
apt-get install -y --no-install-recommends \
      "john=${JOHN_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt john "${JOHN_VERSION}" "${TARGETARCH}"
)

# 工具: Hashcat
# 描述: 使用 CPU、GPU 或其他加速设备进行离线哈希恢复。
# 安装: Kali 软件包 hashcat；GPU 使用还需要宿主机驱动和设备透传。
(
apt-get install -y --no-install-recommends \
      "hashcat=${HASHCAT_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt hashcat "${HASHCAT_VERSION}" "${TARGETARCH}"
)

# 工具: Medusa
# 描述: 并行验证多种远程服务的认证凭据。
# 安装: Kali 软件包 medusa。
(
apt-get install -y --no-install-recommends \
      "medusa=${MEDUSA_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt medusa "${MEDUSA_VERSION}" "${TARGETARCH}"
)

# 工具: Patator
# 描述: 模块化、多协议的认证测试和口令验证工具。
# 安装: Kali 软件包 patator。
(
apt-get install -y --no-install-recommends \
      "patator=${PATATOR_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt patator "${PATATOR_VERSION}" "${TARGETARCH}"
)

# 工具: CrackMapExec
# 描述: 枚举和验证 Windows/Active Directory 环境中的凭据与访问权限。
# 安装: Kali 软件包 crackmapexec；同时保留较新的 NetExec，二者命令不互相替代。
(
apt-get install -y --no-install-recommends \
      "crackmapexec=${CRACKMAPEXEC_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt crackmapexec "${CRACKMAPEXEC_VERSION}" "${TARGETARCH}"
)

# 工具: Evil-WinRM
# 描述: 通过 WinRM 连接到已获授权的 Windows 主机并执行管理操作。
# 安装: Kali 软件包 evil-winrm。
(
apt-get install -y --no-install-recommends \
      "evil-winrm=${EVIL_WINRM_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt evil-winrm "${EVIL_WINRM_VERSION}" "${TARGETARCH}"
)

# 工具: Hash-Identifier
# 描述: 根据哈希的长度和字符特征推测可能的算法类型。
# 安装: Kali 软件包 hash-identifier。
(
apt-get install -y --no-install-recommends \
      "hash-identifier=${HASH_IDENTIFIER_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt hash-identifier "${HASH_IDENTIFIER_VERSION}" "${TARGETARCH}"
)

# 工具: Ophcrack
# 描述: 使用彩虹表恢复 Windows LM/NTLM 哈希；彩虹表不纳入镜像。
# 安装: 使用 Kali 的无图形界面包 ophcrack-cli，避免 Qt/X11 依赖。
(
case "${TARGETARCH}" in \
      amd64) package_version="${OPHCRACK_CLI_VERSION_AMD64}" ;; \
      arm64) package_version="${OPHCRACK_CLI_VERSION_ARM64}" ;; \
    esac && \
    apt-get install -y --no-install-recommends "ophcrack-cli=${package_version}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt ophcrack-cli "${package_version}" "${TARGETARCH}"
)
