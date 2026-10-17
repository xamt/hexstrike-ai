#!/usr/bin/env bash
# forensics 类 APT 工具；版本与安装定义在同一文件，任意失败立即停止。
set -euo pipefail

FOREMOST_VERSION_AMD64=1.5.7-12+b1
FOREMOST_VERSION_ARM64=1.5.7-12
STEGHIDE_VERSION=0.5.1+git20240220-2
EXIFTOOL_VERSION=13.55+dfsg-1

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${TARGETARCH:?缺少目标架构}" in
    amd64|arm64) ;;
    *) echo "不支持的架构: ${TARGETARCH}" >&2; exit 1 ;;
esac

apt-get -o APT::Update::Error-Mode=any update

# 工具: Foremost
# 描述: 根据文件头、文件尾和数据结构从镜像中恢复文件。
# 安装: Kali 软件包 foremost。
(
case "${TARGETARCH}" in \
      amd64) package_version="${FOREMOST_VERSION_AMD64}" ;; \
      arm64) package_version="${FOREMOST_VERSION_ARM64}" ;; \
    esac && \
    apt-get install -y --no-install-recommends "foremost=${package_version}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt foremost "${package_version}" "${TARGETARCH}"
)

# 工具: Steghide
# 描述: 在 JPEG、BMP、WAV、AU 等载体中嵌入或提取隐藏数据。
# 安装: Kali 软件包 steghide。
(
apt-get install -y --no-install-recommends \
      "steghide=${STEGHIDE_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt steghide "${STEGHIDE_VERSION}" "${TARGETARCH}"
)

# 工具: ExifTool
# 描述: 读取、写入和比较多种文件格式的元数据。
# 安装: Kali 包名为 libimage-exiftool-perl，提供 exiftool 命令。
(
apt-get install -y --no-install-recommends \
      "libimage-exiftool-perl=${EXIFTOOL_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt libimage-exiftool-perl "${EXIFTOOL_VERSION}" "${TARGETARCH}"
)
