#!/usr/bin/env bash
# Python 安装组件：默认准备全局环境，也可为工具创建独立虚拟环境。
set -euo pipefail

PIP_VERSION=25.3
SETUPTOOLS_VERSION=80.9.0
WHEEL_VERSION=0.45.1
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
: "${PIP_INDEX_URL:?缺少 PyPI 下载源配置}"
interpreter=python3
environment=python
if [ "$#" -eq 2 ]; then
    python3 -m venv "$1"
    interpreter="$1/bin/python"
    environment="$2"
elif [ "$#" -ne 0 ]; then
    echo "用法：python.sh [虚拟环境路径 记录类型]" >&2
    exit 2
fi
"${interpreter}" -m pip install --index-url "${PIP_INDEX_URL}" \
    "pip==${PIP_VERSION}" "setuptools==${SETUPTOOLS_VERSION}" "wheel==${WHEEL_VERSION}"
export TOOL_RECORD_DIR=/opt/tool-versions.d
for item in "pip:${PIP_VERSION}" "setuptools:${SETUPTOOLS_VERSION}" "wheel:${WHEEL_VERSION}"; do
    bash "${script_dir}/../lib/record-tool-version.sh" "${environment}" "${item%%:*}" "${item#*:}" all
done
