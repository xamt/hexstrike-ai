#!/usr/bin/env bash
# 构建依赖：固定兼容 X8 锁文件的 Rust 工具链，默认值只在 Dockerfile.base 中定义。
set -euo pipefail

rustup toolchain install "${RUST_TOOLCHAIN:?缺少 Rust 工具链版本}" --profile minimal
