#!/usr/bin/env bash
# ClickHouse 官方客户端与其必需公共二进制，不安装 clickhouse-server 服务包。
# 摘要来源：https://packages.clickhouse.com/deb/dists/stable/main/binary-{amd64,arm64}/Packages
set -euo pipefail

CLICKHOUSE_CLIENT_VERSION=25.8.20.4
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${script_dir}/install-database-deb.sh"
case "${TARGETARCH}" in
    amd64)
        client_sha256=5dfc76917649b88c4aee653bdbcf202df9d8c714a14e68c2e53435e85ac5325e
        common_sha256=80d06a2744b420ffcd7a802618c6f4abcc38ceca54d3cfb7f60f6636413869f8
        ;;
    arm64)
        client_sha256=faf4aa0149140b0866a94714a0664c5960a331e43d84e05681fc17411f521808
        common_sha256=65e87dff6776bd0b2ea8ed2eaf587ca21410481411cfa4afaa788703bce10df8
        ;;
    *) echo "不支持的 ClickHouse 架构: ${TARGETARCH}" >&2; exit 1 ;;
esac

temporary="$(mktemp -d)"
trap 'rm -rf "${temporary}"' EXIT
source_url=https://packages.clickhouse.com/deb/pool/main/c/clickhouse
download_database_deb \
    "${source_url}/clickhouse-common-static_${CLICKHOUSE_CLIENT_VERSION}_${TARGETARCH}.deb" \
    "${common_sha256}" clickhouse-common-static "${CLICKHOUSE_CLIENT_VERSION}" "${temporary}/common.deb"
download_database_deb \
    "${source_url}/clickhouse-client_${CLICKHOUSE_CLIENT_VERSION}_${TARGETARCH}.deb" \
    "${client_sha256}" clickhouse-client "${CLICKHOUSE_CLIENT_VERSION}" "${temporary}/client.deb"
apt-get install -y --no-install-recommends "${temporary}/common.deb" "${temporary}/client.deb"
for package in clickhouse-common-static clickhouse-client; do
    bash "${script_dir}/record-tool-version.sh" apt "${package}" "${CLICKHOUSE_CLIENT_VERSION}" "${TARGETARCH}"
done
