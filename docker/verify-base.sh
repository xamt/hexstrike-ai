#!/usr/bin/env bash
# 验证工具镜像，无外部扫描；任意缺失或版本不符立即失败。
set -euo pipefail

# AutoRecon 的 APT 依赖会安装 SecLists；安装时只写构建缓存，运行时必须挂卷。
if [ -d /usr/share/seclists ] && [ -n "$(find /usr/share/seclists -mindepth 1 -print -quit)" ]; then
    echo "基础镜像不应包含 SecLists 大型数据，请检查构建缓存挂载" >&2
    exit 1
fi

expected_commands=(
    nmap masscan rustscan amass subfinder nuclei fierce dnsenum
    autorecon theHarvester responder nxc enum4linux-ng gobuster feroxbuster dirsearch
    ffuf dirb httpx katana hakrawler nikto sqlmap wpscan
    arjun paramspider dalfox wafw00f gau waybackurls x8 anew
    qsreplace uro wfuzz hydra john hashcat medusa patator
    crackmapexec evil-winrm hash-identifier ophcrack-cli gdb r2 radare2 binwalk
    ghidra analyzeHeadless checksec strings objdump xxd vol foremost
    steghide exiftool
    mysql clickhouse-client redis-cli psql mongosh
    testssl whatweb jwt_tool trufflehog tcpdump
)
for command_name in "${expected_commands[@]}"; do
    command -v "${command_name}" >/dev/null || {
        echo "缺少工具命令: ${command_name}" >&2
        exit 1
    }
done

# 读取各安装阶段成功后保存的预期记录，核对实际版本；全部通过才生成版本清单。
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
/usr/local/bin/python3.11 "${script_dir}/verify-tool-versions.py" --arch "${TARGETARCH}"
/usr/local/bin/python3.11 -c 'import ssl, sqlite3, bz2, lzma, ctypes, readline, dbm.gnu, uuid; import sys; assert sys.version_info[:2] == (3, 11)'
/opt/volatility3-venv/bin/python -m pip check
/opt/jwt-tool-venv/bin/python -m pip check
/opt/jwt-tool-venv/bin/python -c 'import Cryptodome, termcolor, cprint, requests, ratelimit'

# ELF 头验证架构，不依赖编译器进入最终镜像。
/usr/local/bin/python3.11 - <<'PY'
import os
import struct
from pathlib import Path

machine = {"amd64": 62, "arm64": 183}[os.environ["TARGETARCH"]]
for name in ("gau", "waybackurls", "anew", "x8"):
    with Path("/usr/local/bin", name).open("rb") as binary:
        header = binary.read(20)
    assert header[:4] == b"\x7fELF", f"{name}: 非 ELF 文件"
    assert header[5] == 1, f"{name}: 非小端 ELF"
    assert struct.unpack("<H", header[18:20])[0] == machine, f"{name}: 架构不匹配"
PY

timeout 30 nmap --version
timeout 30 x8 --version
timeout 30 vol -h >/dev/null

# 仅检查客户端版本与动态链接，不连接数据库、不执行 SQL 或脚本。
timeout 30 mysql --version
timeout 30 clickhouse-client --version
timeout 30 redis-cli --version
timeout 30 psql --version
timeout 30 mongosh --version

# 只查询版本/帮助，不抓包、不连接目标、不扫描本地内容。
timeout 30 testssl --version
timeout 30 whatweb --version
timeout 30 trufflehog --version
timeout 30 tcpdump --version
timeout 30 jwt_tool -h >/dev/null
