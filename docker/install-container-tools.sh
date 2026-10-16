#!/usr/bin/env bash
# 通用Docker/Kubernetes检查：仅CLI和扫描器，不安装daemon、厂商云CLI或漏洞数据库。
# 使用现有Kali签名源和国内镜像；固定双架构包版本，不自动降级或跳过。
set -euo pipefail

DOCKER_CLI_VERSION=28.5.2+dfsg4-5
KUBECTL_VERSION=1.33.4+ds-1
TRIVY_VERSION=0.66.0-0kali1
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${TARGETARCH:?缺少目标架构}" in
    amd64|arm64) ;;
    *) echo "不支持的架构: ${TARGETARCH}" >&2; exit 1 ;;
esac

apt-get -o APT::Update::Error-Mode=any update
# docker-cli是独立客户端包，不是包含daemon的docker.io；kubectl不是过渡元包。
apt-get install -y --no-install-recommends \
    "docker-cli=${DOCKER_CLI_VERSION}" \
    "kubectl=${KUBECTL_VERSION}" \
    "trivy=${TRIVY_VERSION}"

bash "${script_dir}/record-tool-version.sh" apt docker-cli "${DOCKER_CLI_VERSION}" "${TARGETARCH}"
bash "${script_dir}/record-tool-version.sh" apt kubectl "${KUBECTL_VERSION}" "${TARGETARCH}"
bash "${script_dir}/record-tool-version.sh" apt trivy "${TRIVY_VERSION}" "${TARGETARCH}"
