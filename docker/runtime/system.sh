#!/usr/bin/env bash
set -euo pipefail

# 每个原始安装步骤在独立子进程中执行，任意 && 链失败均立即中止整个脚本。
(
case "${TARGETARCH}" in \
      amd64|arm64) ;; \
      *) echo "不支持的目标架构: ${TARGETARCH}" >&2; exit 1 ;; \
    esac
)

# 最小 Kali 的 OpenSSL 默认信任路径尚未建立，显式指定已复制的 CA bundle。
printf 'Acquire::https::CaInfo "/etc/ssl/certs/ca-certificates.crt";\n' \
    > /etc/apt/apt.conf.d/99-ca-bundle
# 包缓存由 BuildKit 挂载管理，不让镜像自带清理钩子删除可复用的下载。
rm -f "/etc/apt/apt.conf.d/docker-clean"

# APT 源配置
# 分类: 镜像基础设施
# 描述: 使用可覆盖的 Kali 镜像站，加速中国区构建，同时保留官方签名校验。
# 安装: 写入唯一的 deb822 软件源，避免基础镜像原源与自定义源重复读取。
(
printf '%s\n' \
      'Types: deb' \
      "URIs: ${KALI_APT_MIRROR}" \
      "Suites: ${KALI_APT_SUITE}" \
      'Components: main contrib non-free non-free-firmware' \
      'Signed-By: /usr/share/keyrings/kali-archive-keyring.gpg' \
      > /etc/apt/sources.list.d/kali.sources && \
    : > /etc/apt/sources.list
)

# 基础运行库
# 分类: 镜像基础设施
# 描述: 提供证书、进程管理、源码获取、Perl 工具运行库和 Python 3.11
#       从 Debian 镜像复制后所需的动态链接库。
# 安装: 仅安装运行期依赖；APT 索引和下载包使用 BuildKit 缓存挂载。
(
apt-get -o APT::Update::Error-Mode=any update && \
    apt-get install -y --no-install-recommends \
      ca-certificates curl git tini perl \
      libnet-ssleay-perl libio-socket-ssl-perl libwww-perl \
      libssl3t64 libffi8 libbz2-1.0 libsqlite3-0 liblzma5 \
      libreadline8t64 libncursesw6 libgdbm6t64 libgdbm-compat4t64 \
      libexpat1 libuuid1 libnsl2 libtirpc3t64 zlib1g
)
