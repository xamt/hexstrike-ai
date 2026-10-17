#!/usr/bin/env bash
# JWT-Tool 独立于 Kali 系统和应用环境；固定源码标签、归档摘要及直接依赖。
set -euo pipefail

JWT_TOOL_VERSION=2.3.0
JWT_TERMCOLOR_VERSION=3.3.0
JWT_CPRINT_VERSION=1.2.2
JWT_PYCRYPTODOMEX_VERSION=3.24.1
JWT_REQUESTS_VERSION=2.34.2
JWT_RATELIMIT_VERSION=2.2.1
# v2.3.0 对应 commit 3bc7407cf2222d6a821dcc19c776e5a1b1cb9a9b。
archive_sha256=0f8c32aa9f67cea4312e5df81d48f72dc5daf57f3cc0ce09d67db78e23fbe451
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
: "${PIP_INDEX_URL:?缺少 PyPI 下载源配置}"
temporary="$(mktemp -d)"
trap 'rm -rf "${temporary}"' EXIT

# Python 官方 slim 阶段无需额外安装 curl；HTTPS 使用系统证书，不关闭验证。
python3.11 - "${JWT_TOOL_VERSION}" "${temporary}/jwt-tool.tar.gz" <<'PY'
import shutil
import sys
import urllib.request

url = "https://codeload.github.com/ticarpi/jwt_tool/tar.gz/refs/tags/v" + sys.argv[1]
with urllib.request.urlopen(url, timeout=120) as response, open(sys.argv[2], "wb") as output:
    shutil.copyfileobj(response, output)
PY
printf '%s  %s\n' "${archive_sha256}" "${temporary}/jwt-tool.tar.gz" | sha256sum -c -
mkdir -p /opt/jwt-tool
tar -xzf "${temporary}/jwt-tool.tar.gz" --strip-components=1 -C /opt/jwt-tool
python3.11 -m venv /opt/jwt-tool-venv
/opt/jwt-tool-venv/bin/python -m pip install --index-url "${PIP_INDEX_URL}" \
    "termcolor==${JWT_TERMCOLOR_VERSION}" \
    "cprint==${JWT_CPRINT_VERSION}" \
    "pycryptodomex==${JWT_PYCRYPTODOMEX_VERSION}" \
    "requests==${JWT_REQUESTS_VERSION}" \
    "ratelimit==${JWT_RATELIMIT_VERSION}"
/opt/jwt-tool-venv/bin/python -m pip check

# 固定解释器，不依赖应用 PATH；首次配置/测试密钥由运行时在独立 HOME 生成。
cat > /usr/local/bin/jwt_tool <<'WRAPPER'
#!/bin/sh
cd /opt/jwt-tool || exit 1
exec /opt/jwt-tool-venv/bin/python /opt/jwt-tool/jwt_tool.py "$@"
WRAPPER
chmod 0755 /usr/local/bin/jwt_tool

export TOOL_RECORD_DIR=/opt/tool-versions.d
bash "${script_dir}/../../lib/record-tool-version.sh" source jwt_tool "${JWT_TOOL_VERSION}" all \
    /opt/jwt-tool/jwt_tool.py /opt/jwt-tool/jwt_tool.py
bash "${script_dir}/../../lib/record-tool-version.sh" jwt-python termcolor "${JWT_TERMCOLOR_VERSION}" all
bash "${script_dir}/../../lib/record-tool-version.sh" jwt-python cprint "${JWT_CPRINT_VERSION}" all
bash "${script_dir}/../../lib/record-tool-version.sh" jwt-python pycryptodomex "${JWT_PYCRYPTODOMEX_VERSION}" all
bash "${script_dir}/../../lib/record-tool-version.sh" jwt-python requests "${JWT_REQUESTS_VERSION}" all
bash "${script_dir}/../../lib/record-tool-version.sh" jwt-python ratelimit "${JWT_RATELIMIT_VERSION}" all
