#!/usr/bin/env bash
# Dalfox v2 原生支持既有 mining/deep-domxss 参数，不升级至 v3。
set -euo pipefail

DALFOX_VERSION=v2.12.0
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [ "$#" -ne 0 ]; then echo "此安装脚本不接受工具名" >&2; exit 2; fi
bash "${script_dir}/../../lib/build-go-tool.sh" dalfox github.com/hahwul/dalfox/v2 "${DALFOX_VERSION}"
