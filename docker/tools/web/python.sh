#!/usr/bin/env bash
# 原接口依赖 -l/--exclude/-o；固定保留这些参数的官方源码，不替换为新版命令。
set -euo pipefail

PARAMSPIDER_VERSION=3add9faf11fa269624a2a9e92ea12be90338cb02
PARAM_REQUESTS_VERSION=2.34.2
PARAM_URLLIB3_VERSION=2.8.0
PARAM_CHARSET_NORMALIZER_VERSION=3.5.2
PARAM_IDNA_VERSION=3.20
PARAM_CERTIFI_VERSION=2026.7.22
archive_sha256=18196d50530c8694d6f61175489c531641ae27550db2c8a1eaec1f5f47f0b745
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
: "${PIP_INDEX_URL:?缺少 PyPI 下载源配置}"
temporary="$(mktemp -d)"
trap 'rm -rf "${temporary}"' EXIT

python3.11 - "${PARAMSPIDER_VERSION}" "${temporary}/paramspider.tar.gz" <<'PY'
import shutil
import sys
import urllib.request

url = "https://codeload.github.com/devanshbatham/ParamSpider/tar.gz/" + sys.argv[1]
with urllib.request.urlopen(url, timeout=120) as source, open(sys.argv[2], "wb") as target:
    shutil.copyfileobj(source, target)
PY
printf '%s  %s\n' "${archive_sha256}" "${temporary}/paramspider.tar.gz" | sha256sum -c -
mkdir -p /opt/paramspider
tar -xzf "${temporary}/paramspider.tar.gz" --strip-components=1 -C /opt/paramspider
python3.11 -m venv /opt/paramspider-venv
# 源码仅使用 requests 公共 API；不沿用上游2020年已过时的HTTP依赖锁定。
/opt/paramspider-venv/bin/python -m pip install --index-url "${PIP_INDEX_URL}" \
    "requests==${PARAM_REQUESTS_VERSION}" "urllib3==${PARAM_URLLIB3_VERSION}" \
    "charset-normalizer==${PARAM_CHARSET_NORMALIZER_VERSION}" \
    "idna==${PARAM_IDNA_VERSION}" "certifi==${PARAM_CERTIFI_VERSION}"
/opt/paramspider-venv/bin/python -m pip check
cat > /usr/local/bin/paramspider <<'WRAPPER'
#!/bin/sh
exec /opt/paramspider-venv/bin/python /opt/paramspider/paramspider.py "$@"
WRAPPER
chmod 0755 /usr/local/bin/paramspider

export TOOL_RECORD_DIR=/opt/tool-versions.d
bash "${script_dir}/../../lib/record-tool-version.sh" source paramspider "${PARAMSPIDER_VERSION}" all \
    /opt/paramspider/paramspider.py /opt/paramspider/paramspider.py
for item in "requests:${PARAM_REQUESTS_VERSION}" "urllib3:${PARAM_URLLIB3_VERSION}" \
    "charset-normalizer:${PARAM_CHARSET_NORMALIZER_VERSION}" "idna:${PARAM_IDNA_VERSION}" \
    "certifi:${PARAM_CERTIFI_VERSION}"; do
    bash "${script_dir}/../../lib/record-tool-version.sh" param-python "${item%%:*}" "${item#*:}" all
done
