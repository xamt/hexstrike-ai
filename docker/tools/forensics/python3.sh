#!/usr/bin/env bash
# Volatility3 独立环境；不使用项目虚拟环境，旧路径入口在 compat 中维护。
set -euo pipefail

VOLATILITY3_VERSION=2.28.2
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
: "${PIP_INDEX_URL:?缺少 PyPI 下载源配置}"
bash "${script_dir}/../../runtime/python.sh" /opt/volatility3-venv vol-python
/opt/volatility3-venv/bin/python -m pip install --index-url "${PIP_INDEX_URL}" "volatility3==${VOLATILITY3_VERSION}"
export TOOL_RECORD_DIR=/opt/tool-versions.d
bash "${script_dir}/../../lib/record-tool-version.sh" vol-python volatility3 "${VOLATILITY3_VERSION}" all
