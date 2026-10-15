#!/usr/bin/env bash
# 工具：X8；保留 Cargo 锁定依赖，产物供最终工具镜像复制。
set -euo pipefail

X8_VERSION=4.3.0
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cargo install x8 --version "${X8_VERSION}" --locked --root "/out"
TOOL_RECORD_DIR=/out/tool-versions.d bash "${script_dir}/record-tool-version.sh" \
    rust x8 "${X8_VERSION}" "${TARGETARCH}" "/out/bin/x8" "/usr/local/bin/x8"
