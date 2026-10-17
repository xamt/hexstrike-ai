#!/usr/bin/env bash
# 情报类 Go 工具：显式选择一个工具，每个调用保留独立构建层。
set -euo pipefail

GAU_VERSION=v2.2.4
WAYBACKURLS_VERSION=v0.1.0
ANEW_VERSION=v0.1.1

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
name="${1:?缺少 Go 工具名}"
case "${name}" in
    gau) package=github.com/lc/gau/v2/cmd/gau; version="${GAU_VERSION}" ;;
    waybackurls) package=github.com/tomnomnom/waybackurls; version="${WAYBACKURLS_VERSION}" ;;
    anew) package=github.com/tomnomnom/anew; version="${ANEW_VERSION}" ;;
    *) echo "不支持的 Go 工具: ${name}" >&2; exit 2 ;;
esac
bash "${script_dir}/../../lib/build-go-tool.sh" "${name}" "${package}" "${version}"
