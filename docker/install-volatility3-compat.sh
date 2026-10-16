#!/usr/bin/env bash
# 原接口使用 python3 /opt/volatility3/vol.py；入口必须是Python源码，不是Shell链接。
set -euo pipefail

mkdir -p /opt/volatility3
cat > /opt/volatility3/vol.py <<'PY'
#!/usr/bin/env python3
"""Forward the historical script path to the isolated Volatility 3 runtime."""

import os
import sys

os.execv("/opt/volatility3-venv/bin/vol", ["vol"] + sys.argv[1:])
PY
chmod 0755 /opt/volatility3/vol.py
cat > /usr/local/bin/vol.py <<'WRAPPER'
#!/bin/sh
exec /opt/volatility3-venv/bin/vol "$@"
WRAPPER
chmod 0755 /usr/local/bin/vol.py
