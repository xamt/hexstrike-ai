#!/usr/bin/env bash
# 由数据库安装脚本 source；下载固定包，先核对 SHA256 与元数据，再允许安装。
set -euo pipefail

# 参数：下载地址、固定摘要、包名、固定版本、目标文件。
download_database_deb() {
    local url="$1" digest="$2" package="$3" version="$4" destination="$5"
    curl --fail --show-error --location --proto '=https' --tlsv1.2 \
        --output "${destination}" "${url}"
    printf '%s  %s\n' "${digest}" "${destination}" | sha256sum -c >/dev/null
    [ "$(dpkg-deb --field "${destination}" Package)" = "${package}" ]
    [ "$(dpkg-deb --field "${destination}" Version)" = "${version}" ]
    [ "$(dpkg-deb --field "${destination}" Architecture)" = "${TARGETARCH}" ]
}
