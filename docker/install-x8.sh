#!/usr/bin/env bash
# 工具：X8；保留 Cargo 锁定依赖，产物供最终工具镜像复制。
set -euo pipefail

cargo "+${RUST_TOOLCHAIN:?缺少 Rust 工具链版本}" install x8 \
    --version "${X8_VERSION:?缺少 X8 版本}" --locked --root /out
