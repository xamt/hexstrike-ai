#!/usr/bin/env bash
# 共用 Go 编译与产物记录；名称、模块路径、版本由类别脚本传入。
set -euo pipefail

name="${1:?缺少工具名}"
package="${2:?缺少 Go 模块路径}"
version="${3:?缺少工具版本}"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
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
