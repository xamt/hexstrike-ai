#!/usr/bin/env bash
# 安装指定 Go 工具，统一收集本机构建或交叉编译的产物。
set -euo pipefail

GAU_VERSION=v2.2.4
WAYBACKURLS_VERSION=v0.1.0
ANEW_VERSION=v0.1.1
# 现有接口使用 v2 的 mining/deep-domxss 参数；不以 v3 的不同能力冒充兼容。
DALFOX_VERSION=v2.12.0
name="${1:?缺少 Go 工具名}"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${name}" in
    gau) package=github.com/lc/gau/v2/cmd/gau; version="${GAU_VERSION}" ;;
    waybackurls) package=github.com/tomnomnom/waybackurls; version="${WAYBACKURLS_VERSION}" ;;
    anew) package=github.com/tomnomnom/anew; version="${ANEW_VERSION}" ;;
    dalfox) package=github.com/hahwul/dalfox/v2; version="${DALFOX_VERSION}" ;;
    *) echo "不支持的 Go 工具: ${name}" >&2; exit 2 ;;
esac
export GOBIN=
go install "${package}@${version}"

binary_dir="$(go env GOPATH)/bin"
if [ "$(go env GOOS)/$(go env GOARCH)" != "$(go env GOHOSTOS)/$(go env GOHOSTARCH)" ]; then
    binary_dir="${binary_dir}/$(go env GOOS)_$(go env GOARCH)"
fi
output_dir="${OUTPUT_DIR:-/out/bin}"
mkdir -p "${output_dir}"
install -m 0755 "${binary_dir}/${name}" "${output_dir}/${name}"
TOOL_RECORD_DIR="${TOOL_RECORD_DIR:-/out/tool-versions.d}" \
    bash "${script_dir}/record-tool-version.sh" go "${name}" "${version}" "${TARGETARCH}" \
    "${output_dir}/${name}" "/usr/local/bin/${name}"
