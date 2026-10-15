#!/usr/bin/env bash
# 安装指定 Go 工具，统一收集本机构建或交叉编译的产物。
set -euo pipefail

package="${1:?缺少 Go 包路径}"
version="${2:?缺少工具版本}"
name="${3:?缺少输出命令名}"
export GOBIN=
go install "${package}@${version}"

binary_dir="$(go env GOPATH)/bin"
if [ "$(go env GOOS)/$(go env GOARCH)" != "$(go env GOHOSTOS)/$(go env GOHOSTARCH)" ]; then
    binary_dir="${binary_dir}/$(go env GOOS)_$(go env GOARCH)"
fi
output_dir="${OUTPUT_DIR:-/out}"
mkdir -p "${output_dir}"
install -m 0755 "${binary_dir}/${name}" "${output_dir}/${name}"
