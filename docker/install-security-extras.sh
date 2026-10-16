#!/usr/bin/env bash
# TLS 检查、Web 指纹、凭据泄漏检测及抓包；沿用 Kali 签名源，缺包立即失败。
set -euo pipefail

TESTSSL_VERSION=3.2.4+dfsg-2
WHATWEB_VERSION=0.6.4-1
TRUFFLEHOG_VERSION=3.97.9-0kali1
TCPDUMP_VERSION=4.99.6-2
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${TARGETARCH:?缺少目标架构}" in
    amd64|arm64) ;;
    *) echo "不支持的架构: ${TARGETARCH}" >&2; exit 1 ;;
esac

apt-get -o APT::Update::Error-Mode=any update
apt-get install -y --no-install-recommends \
    "testssl.sh=${TESTSSL_VERSION}" \
    "whatweb=${WHATWEB_VERSION}" \
    "trufflehog=${TRUFFLEHOG_VERSION}" \
    "tcpdump=${TCPDUMP_VERSION}"

# 包名 testssl.sh 对应可执行命令 testssl，不额外创建易混淆的别名。
bash "${script_dir}/record-tool-version.sh" apt testssl.sh "${TESTSSL_VERSION}" "${TARGETARCH}"
bash "${script_dir}/record-tool-version.sh" apt whatweb "${WHATWEB_VERSION}" "${TARGETARCH}"
bash "${script_dir}/record-tool-version.sh" apt trufflehog "${TRUFFLEHOG_VERSION}" "${TARGETARCH}"
bash "${script_dir}/record-tool-version.sh" apt tcpdump "${TCPDUMP_VERSION}" "${TARGETARCH}"
