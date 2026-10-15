#!/usr/bin/env bash
# 只准备 Python 安装工具和独立 Volatility3 环境，不读取项目 requirements.txt。
# 版本来自 Dockerfile.base；Volatility3 保留 vol -f IMAGE [-o DIR] PLUGIN 契约。
set -euo pipefail

python3 -m venv /opt/volatility3-venv
/opt/volatility3-venv/bin/python -m pip install \
    "pip==${PIP_VERSION}" \
    "setuptools==${SETUPTOOLS_VERSION}" \
    "wheel==${WHEEL_VERSION}"
/opt/volatility3-venv/bin/python -m pip install "volatility3==${VOLATILITY3_VERSION}"

# 供应用镜像通过 pip --python 创建/管理另一套环境，不写入 Volatility3 环境。
python3 -m pip install \
    "pip==${PIP_VERSION}" \
    "setuptools==${SETUPTOOLS_VERSION}" \
    "wheel==${WHEEL_VERSION}"
