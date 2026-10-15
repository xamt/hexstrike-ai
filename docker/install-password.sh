#!/usr/bin/env bash
set -euo pipefail

# 同一类别共用一次成功的索引更新，随后仍逐项安装精确版本。
apt-get -o APT::Update::Error-Mode=any update

# 每个原始安装步骤在独立子进程中执行，任意 && 链失败均立即中止整个脚本。
# 工具: Hydra
# 分类: Password & Authentication
# 描述: 对多种网络协议执行在线口令验证和字典测试。
# 安装: Kali 软件包 hydra。
(
apt-get install -y --no-install-recommends \
      "hydra=${HYDRA_VERSION}"
)

# 工具: John the Ripper
# 分类: Password & Authentication
# 描述: 对多种密码哈希格式执行离线恢复和强度验证。
# 安装: Kali 软件包 john；大型字典不纳入镜像。
(
apt-get install -y --no-install-recommends \
      "john=${JOHN_VERSION}"
)

# 工具: Hashcat
# 分类: Password & Authentication
# 描述: 使用 CPU、GPU 或其他加速设备进行离线哈希恢复。
# 安装: Kali 软件包 hashcat；GPU 使用还需要宿主机驱动和设备透传。
(
apt-get install -y --no-install-recommends \
      "hashcat=${HASHCAT_VERSION}"
)

# 工具: Medusa
# 分类: Password & Authentication
# 描述: 并行验证多种远程服务的认证凭据。
# 安装: Kali 软件包 medusa。
(
apt-get install -y --no-install-recommends \
      "medusa=${MEDUSA_VERSION}"
)

# 工具: Patator
# 分类: Password & Authentication
# 描述: 模块化、多协议的认证测试和口令验证工具。
# 安装: Kali 软件包 patator。
(
apt-get install -y --no-install-recommends \
      "patator=${PATATOR_VERSION}"
)

# 工具: CrackMapExec
# 分类: Password & Authentication / Active Directory
# 描述: 枚举和验证 Windows/Active Directory 环境中的凭据与访问权限。
# 安装: Kali 软件包 crackmapexec；同时保留较新的 NetExec，二者命令不互相替代。
(
apt-get install -y --no-install-recommends \
      "crackmapexec=${CRACKMAPEXEC_VERSION}"
)

# 工具: Evil-WinRM
# 分类: Password & Authentication / Windows 远程管理
# 描述: 通过 WinRM 连接到已获授权的 Windows 主机并执行管理操作。
# 安装: Kali 软件包 evil-winrm。
(
apt-get install -y --no-install-recommends \
      "evil-winrm=${EVIL_WINRM_VERSION}"
)

# 工具: Hash-Identifier
# 分类: Password & Authentication / 哈希识别
# 描述: 根据哈希的长度和字符特征推测可能的算法类型。
# 安装: Kali 软件包 hash-identifier。
(
apt-get install -y --no-install-recommends \
      "hash-identifier=${HASH_IDENTIFIER_VERSION}"
)

# 工具: Ophcrack
# 分类: Password & Authentication / Windows 哈希恢复
# 描述: 使用彩虹表恢复 Windows LM/NTLM 哈希；彩虹表不纳入镜像。
# 安装: 使用 Kali 的无图形界面包 ophcrack-cli，避免 Qt/X11 依赖。
(
case "${TARGETARCH}" in \
      amd64) package_version="${OPHCRACK_CLI_VERSION_AMD64}" ;; \
      arm64) package_version="${OPHCRACK_CLI_VERSION_ARM64}" ;; \
    esac && \
    apt-get install -y --no-install-recommends "ophcrack-cli=${package_version}"
)


# -----------------------------------------------------------------------------
# Binary Analysis & Reverse Engineering
# -----------------------------------------------------------------------------
