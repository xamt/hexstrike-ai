#!/usr/bin/env bash
# 通用容器工具的 python 安装阶段；只执行本文件对应的安装方式。
set -euo pipefail

KUBE_HUNTER_VERSION=0.6.8
HUNTER_PIP_VERSION=25.3
HUNTER_SETUPTOOLS_VERSION=80.9.0
HUNTER_WHEEL_VERSION=0.45.1
HUNTER_NETADDR_VERSION=1.3.0
HUNTER_NETIFACES_VERSION=0.11.0
HUNTER_REQUESTS_VERSION=2.34.2
HUNTER_PRETTYTABLE_VERSION=3.18.0
HUNTER_URLLIB3_VERSION=2.8.0
HUNTER_RUAMEL_YAML_VERSION=0.18.16
HUNTER_RUAMEL_YAML_CLIB_VERSION=0.2.15
HUNTER_FUTURE_VERSION=1.0.0
HUNTER_PACKAGING_VERSION=26.3
HUNTER_DATACLASSES_VERSION=0.6
HUNTER_PLUGGY_VERSION=1.7.0
HUNTER_KUBERNETES_VERSION=12.0.1
HUNTER_CERTIFI_VERSION=2026.7.22
HUNTER_CHARSET_NORMALIZER_VERSION=3.5.2
HUNTER_IDNA_VERSION=3.20
HUNTER_WCWIDTH_VERSION=0.9.2
HUNTER_SIX_VERSION=1.17.0
HUNTER_DATEUTIL_VERSION=2.9.0.post0
HUNTER_PYYAML_VERSION=6.0.3
HUNTER_GOOGLE_AUTH_VERSION=2.40.3
HUNTER_WEBSOCKET_CLIENT_VERSION=1.9.2
HUNTER_REQUESTS_OAUTHLIB_VERSION=2.0.0
HUNTER_OAUTHLIB_VERSION=4.0.0
HUNTER_CACHETOOLS_VERSION=5.5.2
HUNTER_PYASN1_VERSION=0.6.4
HUNTER_PYASN1_MODULES_VERSION=0.4.2
HUNTER_RSA_VERSION=4.9.1

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${TARGETARCH:?缺少目标架构}" in
    amd64|arm64) ;;
    *) echo "不支持的架构: ${TARGETARCH}" >&2; exit 1 ;;
esac

if [ "$#" -ne 0 ]; then echo "此安装脚本不接受模式参数" >&2; exit 2; fi

hunter_requirements() {
    printf '%s\n' \
        "kube-hunter==${KUBE_HUNTER_VERSION}" "netaddr==${HUNTER_NETADDR_VERSION}" \
        "netifaces==${HUNTER_NETIFACES_VERSION}" "requests==${HUNTER_REQUESTS_VERSION}" \
        "prettytable==${HUNTER_PRETTYTABLE_VERSION}" "urllib3==${HUNTER_URLLIB3_VERSION}" \
        "ruamel.yaml==${HUNTER_RUAMEL_YAML_VERSION}" "ruamel.yaml.clib==${HUNTER_RUAMEL_YAML_CLIB_VERSION}" \
        "future==${HUNTER_FUTURE_VERSION}" "packaging==${HUNTER_PACKAGING_VERSION}" \
        "dataclasses==${HUNTER_DATACLASSES_VERSION}" "pluggy==${HUNTER_PLUGGY_VERSION}" \
        "kubernetes==${HUNTER_KUBERNETES_VERSION}" "certifi==${HUNTER_CERTIFI_VERSION}" \
        "charset-normalizer==${HUNTER_CHARSET_NORMALIZER_VERSION}" "idna==${HUNTER_IDNA_VERSION}" \
        "wcwidth==${HUNTER_WCWIDTH_VERSION}" "six==${HUNTER_SIX_VERSION}" \
        "python-dateutil==${HUNTER_DATEUTIL_VERSION}" "pyyaml==${HUNTER_PYYAML_VERSION}" \
        "google-auth==${HUNTER_GOOGLE_AUTH_VERSION}" "websocket-client==${HUNTER_WEBSOCKET_CLIENT_VERSION}" \
        "requests-oauthlib==${HUNTER_REQUESTS_OAUTHLIB_VERSION}" "oauthlib==${HUNTER_OAUTHLIB_VERSION}" \
        "cachetools==${HUNTER_CACHETOOLS_VERSION}" "pyasn1==${HUNTER_PYASN1_VERSION}" \
        "pyasn1-modules==${HUNTER_PYASN1_MODULES_VERSION}" "rsa==${HUNTER_RSA_VERSION}"
}

install_kube_hunter() {
    : "${PIP_INDEX_URL:?缺少 PyPI 下载源配置}"
    apt-get -o APT::Update::Error-Mode=any update
    apt-get install -y --no-install-recommends gcc libc6-dev
    python3.11 -m venv "/opt/kube-hunter-venv"
    interpreter="/opt/kube-hunter-venv/bin/python"
    "${interpreter}" -m pip install --index-url "${PIP_INDEX_URL}" --no-deps \
        "pip==${HUNTER_PIP_VERSION}" "setuptools==${HUNTER_SETUPTOOLS_VERSION}" "wheel==${HUNTER_WHEEL_VERSION}"
    temporary="$(mktemp -d)"
    trap 'rm -rf "${temporary}"' EXIT
    hunter_requirements > "${temporary}/requirements.txt"
    "${interpreter}" -m pip install --index-url "${PIP_INDEX_URL}" --no-deps --no-build-isolation \
        -r "${temporary}/requirements.txt"
    "${interpreter}" -m pip check
    export TOOL_RECORD_DIR="/opt/tool-versions.d"
    for item in "pip==${HUNTER_PIP_VERSION}" "setuptools==${HUNTER_SETUPTOOLS_VERSION}" \
        "wheel==${HUNTER_WHEEL_VERSION}"; do
        bash "${script_dir}/../../lib/record-tool-version.sh" hunter-python "${item%%==*}" "${item#*==}" all
    done
    while IFS= read -r item; do
        bash "${script_dir}/../../lib/record-tool-version.sh" hunter-python "${item%%==*}" "${item#*==}" all
    done < "${temporary}/requirements.txt"
}

install_kube_hunter
