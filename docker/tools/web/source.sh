#!/usr/bin/env bash
# 工具：Nikto；只保留固定标签源码，Git 和下载依赖不进入最终镜像。
set -euo pipefail

NIKTO_VERSION=2.6.1
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
apt-get -o APT::Update::Error-Mode=any update
apt-get install -y --no-install-recommends ca-certificates git
git clone --depth 1 --branch "${NIKTO_VERSION}" \
    https://github.com/sullo/nikto.git /opt/nikto
test "$(git -C "/opt/nikto" describe --tags --exact-match)" = "${NIKTO_VERSION}"
TOOL_RECORD_DIR=/opt/tool-versions.d bash "${script_dir}/../../lib/record-tool-version.sh" \
    source nikto "${NIKTO_VERSION}" all "/opt/nikto/program/nikto.pl" "/opt/nikto/program/nikto.pl"
rm -rf "/opt/nikto/.git"
find "/var/lib/apt/lists" -mindepth 1 -delete
