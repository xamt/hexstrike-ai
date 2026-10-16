#!/usr/bin/env bash
# 由数据库安装脚本 source；下载固定包，先核对 SHA256 与元数据，再允许安装。
set -euo pipefail

# 参数：下载地址、固定摘要、包名、固定版本、目标文件。
download_database_deb() {
    local url="$1" digest="$2" package="$3" version="$4" destination="$5"
    # 绕开大包传输时的 HTTP/2 流重置；下载失败最多重试5次，不放宽后续校验。
    # curl 直接写文件，重试时重置本次失败的数据；不使用追加或管道，避免混合残缺内容。
    curl --http1.1 --fail --show-error --location \
        --retry 5 --retry-all-errors --retry-delay 3 \
        --proto '=https' --proto-redir '=https' --tlsv1.2 \
        --output "${destination}" "${url}"
    printf '%s  %s\n' "${digest}" "${destination}" | sha256sum -c >/dev/null
    [ "$(dpkg-deb --field "${destination}" Package)" = "${package}" ]
    [ "$(dpkg-deb --field "${destination}" Version)" = "${version}" ]
    [ "$(dpkg-deb --field "${destination}" Architecture)" = "${TARGETARCH}" ]
}
