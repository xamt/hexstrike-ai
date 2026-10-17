#!/usr/bin/env bash
# 构建依赖：固定兼容 X8 锁文件的工具链；后续 Cargo 使用此阶段的默认工具链。
set -euo pipefail

RUST_TOOLCHAIN=1.79.0
rustup toolchain install "${RUST_TOOLCHAIN}" --profile minimal
rustup default "${RUST_TOOLCHAIN}"
