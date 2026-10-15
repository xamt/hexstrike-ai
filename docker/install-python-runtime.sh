#!/usr/bin/env bash
# 只准备 Python 安装工具和独立 Volatility3 环境，不读取项目 requirements.txt。
# Volatility3 保留 vol -f IMAGE [-o DIR] PLUGIN 契约。
set -euo pipefail

PIP_VERSION=25.3
SETUPTOOLS_VERSION=80.9.0
WHEEL_VERSION=0.45.1
VOLATILITY3_VERSION=2.28.2
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
: "${PIP_INDEX_URL:?缺少 PyPI 下载源配置}"

python3 -m venv /opt/volatility3-venv
/opt/volatility3-venv/bin/python -m pip install --index-url "${PIP_INDEX_URL}" \
    "pip==${PIP_VERSION}" \
    "setuptools==${SETUPTOOLS_VERSION}" \
    "wheel==${WHEEL_VERSION}"

/opt/volatility3-venv/bin/python -m pip install --index-url "${PIP_INDEX_URL}" "volatility3==${VOLATILITY3_VERSION}"

# 供应用镜像通过 pip --python 创建/管理另一套环境，不写入 Volatility3 环境。
python3 -m pip install --index-url "${PIP_INDEX_URL}" \
    "pip==${PIP_VERSION}" \
    "setuptools==${SETUPTOOLS_VERSION}" \
    "wheel==${WHEEL_VERSION}"

# 全部安装成功后分别记录两个环境，不把实际安装值当成期望值。
export TOOL_RECORD_DIR=/opt/tool-versions.d
for environment in python vol-python; do
    bash "${script_dir}/record-tool-version.sh" "${environment}" pip "${PIP_VERSION}" all
    bash "${script_dir}/record-tool-version.sh" "${environment}" setuptools "${SETUPTOOLS_VERSION}" all
    bash "${script_dir}/record-tool-version.sh" "${environment}" wheel "${WHEEL_VERSION}" all
done
bash "${script_dir}/record-tool-version.sh" vol-python volatility3 "${VOLATILITY3_VERSION}" all
