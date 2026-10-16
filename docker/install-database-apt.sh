#!/usr/bin/env bash
# 数据库客户端：复用 Kali 签名仓库；不安装数据库服务端。
set -euo pipefail

MARIADB_CLIENT_VERSION=1:11.8.9+ds-2
REDIS_TOOLS_VERSION=5:8.0.6-3
POSTGRESQL_CLIENT_VERSION=18.6-3
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${TARGETARCH}" in
    amd64|arm64) ;;
    *) echo "不支持的数据库客户端架构: ${TARGETARCH}" >&2; exit 1 ;;
esac

apt-get -o APT::Update::Error-Mode=any update
# core 承载客户端二进制，compat 提供 mysql 等兼容命令；三者一起锁定。
apt-get install -y --no-install-recommends \
    "mariadb-client=${MARIADB_CLIENT_VERSION}" \
    "mariadb-client-core=${MARIADB_CLIENT_VERSION}" \
    "mariadb-client-compat=${MARIADB_CLIENT_VERSION}"
for package in mariadb-client mariadb-client-core mariadb-client-compat; do
    bash "${script_dir}/record-tool-version.sh" apt "${package}" "${MARIADB_CLIENT_VERSION}" "${TARGETARCH}"
done

apt-get install -y --no-install-recommends "redis-tools=${REDIS_TOOLS_VERSION}"
bash "${script_dir}/record-tool-version.sh" apt redis-tools "${REDIS_TOOLS_VERSION}" "${TARGETARCH}"

# 指定客户端主版本，不安装 postgresql / postgresql-18 服务端包。
apt-get install -y --no-install-recommends "postgresql-client-18=${POSTGRESQL_CLIENT_VERSION}"
bash "${script_dir}/record-tool-version.sh" apt postgresql-client-18 "${POSTGRESQL_CLIENT_VERSION}" "${TARGETARCH}"
