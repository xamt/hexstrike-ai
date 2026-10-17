#!/usr/bin/env bash
# Python 复制到 Kali 后更新共享库缓存，并固定 vol 使用工具专用解释器。
set -euo pipefail

ldconfig
printf '%s\n' '#!/bin/sh' 'exec /opt/volatility3-venv/bin/vol "$@"' \
    > /usr/local/bin/vol
chmod 0755 /usr/local/bin/vol
