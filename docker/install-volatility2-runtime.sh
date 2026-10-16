#!/usr/bin/env bash
# 仅在固定的官方 Python 2.7.18 构建阶段运行；编译器和系统包不进入最终镜像。
# Python 2/Volatility 2 已停止维护，仅用于原 --profile 接口的离线旧内存镜像分析。
set -euo pipefail

PYTHON2_VERSION=2.7.18
VOLATILITY2_VERSION=2.6.1
LEGACY_PIP_VERSION=20.3.4
LEGACY_SETUPTOOLS_VERSION=44.1.1
LEGACY_WHEEL_VERSION=0.37.1
LEGACY_PYCRYPTODOME_VERSION=3.23.0
LEGACY_DISTORM3_VERSION=3.5.2
LEGACY_YARA_PYTHON_VERSION=3.11.0
LEGACY_PEFILE_VERSION=2019.4.18
LEGACY_FUTURE_VERSION=0.18.3
LEGACY_CAPSTONE_VERSION=4.0.2
LEGACY_PILLOW_VERSION=6.2.2
archive_sha256=a8dfdbdb2aaa0885387b709b821bb8250e698086fb32015bc2896ea55f359058
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
: "${PIP_INDEX_URL:?缺少 PyPI 下载源配置}"
: "${TARGETARCH:?缺少目标架构}"
case "${TARGETARCH}" in amd64|arm64) ;; *) exit 2 ;; esac
# 老版pip自带的证书包不继续使用，由Docker阶段复制的现行系统CA验证国内源。
export PIP_CERT=/etc/ssl/certs/ca-certificates.crt
test "$(python2.7 -c 'import platform; print(platform.python_version())')" = "${PYTHON2_VERSION}"
temporary="$(mktemp -d)"
trap 'rm -rf "${temporary}"' EXIT

python2.7 - "${VOLATILITY2_VERSION}" "${temporary}/volatility.tar.gz" <<'PY'
import shutil
import sys
import urllib2

url = "https://codeload.github.com/volatilityfoundation/volatility/tar.gz/refs/tags/" + sys.argv[1]
with open(sys.argv[2], "wb") as target:
    source = urllib2.urlopen(url, timeout=120)
    try:
        shutil.copyfileobj(source, target)
    finally:
        source.close()
PY
printf '%s  %s\n' "${archive_sha256}" "${temporary}/volatility.tar.gz" | sha256sum -c -
mkdir -p /out/opt/volatility2 /out/usr/local/bin
tar -xzf "${temporary}/volatility.tar.gz" --strip-components=1 -C /out/opt/volatility2
python2.7 -m pip install --index-url "${PIP_INDEX_URL}" \
    "pip==${LEGACY_PIP_VERSION}" "setuptools==${LEGACY_SETUPTOOLS_VERSION}" "wheel==${LEGACY_WHEEL_VERSION}"
# Python2兼容版：加密、反汇编、YARA、PE及屏幕图像插件。两种架构使用同一源码版本。
python2.7 -m pip install --index-url "${PIP_INDEX_URL}" \
    "pycryptodome==${LEGACY_PYCRYPTODOME_VERSION}" "distorm3==${LEGACY_DISTORM3_VERSION}" \
    "yara-python==${LEGACY_YARA_PYTHON_VERSION}" "pefile==${LEGACY_PEFILE_VERSION}" \
    "future==${LEGACY_FUTURE_VERSION}" "capstone==${LEGACY_CAPSTONE_VERSION}" \
    "Pillow==${LEGACY_PILLOW_VERSION}"
python2.7 -m pip check
python2.7 "${script_dir}/collect-python2-runtime.py" /usr/local /out/opt/python2

cat > /out/usr/local/bin/volatility2-python <<'WRAPPER'
#!/bin/sh
export PYTHONHOME=/opt/python2
export LD_LIBRARY_PATH=/opt/python2/lib:/opt/python2/lib/compat
unset PYTHONPATH
exec /opt/python2/bin/python2.7 "$@"
WRAPPER
cat > /out/usr/local/bin/volatility <<'WRAPPER'
#!/bin/sh
exec /usr/local/bin/volatility2-python /opt/volatility2/vol.py "$@"
WRAPPER
chmod 0755 /out/usr/local/bin/volatility /out/usr/local/bin/volatility2-python

export TOOL_RECORD_DIR=/out/opt/hexstrike/tool-versions.d
bash "${script_dir}/record-tool-version.sh" source python2 "${PYTHON2_VERSION}" "${TARGETARCH}" \
    /out/opt/python2/bin/python2.7 /opt/python2/bin/python2.7
bash "${script_dir}/record-tool-version.sh" source volatility2 "${VOLATILITY2_VERSION}" all \
    /out/opt/volatility2/vol.py /opt/volatility2/vol.py
for item in "pip:${LEGACY_PIP_VERSION}" "setuptools:${LEGACY_SETUPTOOLS_VERSION}" \
    "wheel:${LEGACY_WHEEL_VERSION}" "pycryptodome:${LEGACY_PYCRYPTODOME_VERSION}" \
    "distorm3:${LEGACY_DISTORM3_VERSION}" "yara-python:${LEGACY_YARA_PYTHON_VERSION}" \
    "pefile:${LEGACY_PEFILE_VERSION}" "future:${LEGACY_FUTURE_VERSION}" \
    "capstone:${LEGACY_CAPSTONE_VERSION}" "pillow:${LEGACY_PILLOW_VERSION}"; do
    bash "${script_dir}/record-tool-version.sh" legacy-python "${item%%:*}" "${item#*:}" all
done
