#!/usr/bin/env python3
"""HexStrike MCP 兼容入口：保留 stdio，并支持 Streamable HTTP。"""

from runtime.cli import main, parse_args
from runtime.client import (
    DEFAULT_HEXSTRIKE_SERVER,
    DEFAULT_REQUEST_TIMEOUT,
    HexStrikeClient,
)
from runtime.server import setup_mcp_server


if __name__ == "__main__":
    main()
