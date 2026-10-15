#!/usr/bin/env bash
# 工具：Nikto；只保留固定标签源码，Git 和下载依赖不进入最终镜像。
set -euo pipefail

apt-get -o APT::Update::Error-Mode=any update
apt-get install -y --no-install-recommends ca-certificates git
git clone --depth 1 --branch "${NIKTO_VERSION:?缺少 Nikto 版本}" \
    https://github.com/sullo/nikto.git /opt/nikto
rm -rf "/opt/nikto/.git"
find "/var/lib/apt/lists" -mindepth 1 -delete
