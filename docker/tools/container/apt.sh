#!/usr/bin/env bash
# 通用容器工具的 apt 安装阶段；只执行本文件对应的安装方式。
set -euo pipefail

DOCKER_CLI_VERSION=28.5.2+dfsg4-5
KUBECTL_VERSION=1.33.4+ds-1
HELM_VERSION=4.3.0+ds1-0kali1

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${TARGETARCH:?缺少目标架构}" in
    amd64|arm64) ;;
    *) echo "不支持的架构: ${TARGETARCH}" >&2; exit 1 ;;
esac

if [ "$#" -ne 0 ]; then echo "此安装脚本不接受模式参数" >&2; exit 2; fi

install_apt_tools() {
    apt-get -o APT::Update::Error-Mode=any update
    apt-get install -y --no-install-recommends \
        "docker-cli=${DOCKER_CLI_VERSION}" "kubectl=${KUBECTL_VERSION}" \
        "kubernetes-helm=${HELM_VERSION}"
    bash "${script_dir}/../../lib/record-tool-version.sh" apt docker-cli "${DOCKER_CLI_VERSION}" "${TARGETARCH}"
    bash "${script_dir}/../../lib/record-tool-version.sh" apt kubectl "${KUBECTL_VERSION}" "${TARGETARCH}"
    bash "${script_dir}/../../lib/record-tool-version.sh" apt kubernetes-helm "${HELM_VERSION}" "${TARGETARCH}"
}

install_apt_tools
