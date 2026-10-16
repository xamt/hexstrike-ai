#!/usr/bin/env bash
# MongoDB 独立 Shell；不安装 MongoDB 服务端或旧 mongo 命令。
# 摘要来自 mongodb-js/mongosh v2.13.0 官方发行 API，并与 repo.mongodb.org 包索引交叉核对。
set -euo pipefail

MONGOSH_VERSION=2.13.0
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${script_dir}/install-database-deb.sh"
case "${TARGETARCH}" in
    amd64) package_sha256=63b71930a7065acd199fe68babba6dda2c045aa1786f6091089c595773638119 ;;
    arm64) package_sha256=03b1e71300fae67ffee09cf0aff127bdcd3aeb7ec4a355800281d7c0bf97607a ;;
    *) echo "不支持的 MongoDB Shell 架构: ${TARGETARCH}" >&2; exit 1 ;;
esac

temporary="$(mktemp -d)"
trap 'rm -rf "${temporary}"' EXIT
source_url=https://repo.mongodb.org/apt/ubuntu/dists/noble/mongodb-org/8.0/multiverse
download_database_deb \
    "${source_url}/binary-${TARGETARCH}/mongodb-mongosh_${MONGOSH_VERSION}_${TARGETARCH}.deb" \
    "${package_sha256}" mongodb-mongosh "${MONGOSH_VERSION}" "${temporary}/mongosh.deb"
apt-get install -y --no-install-recommends "${temporary}/mongosh.deb"
bash "${script_dir}/record-tool-version.sh" apt mongodb-mongosh "${MONGOSH_VERSION}" "${TARGETARCH}"
