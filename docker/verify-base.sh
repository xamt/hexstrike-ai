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
)
for command_name in "${expected_commands[@]}"; do
    command -v "${command_name}" >/dev/null || {
        echo "缺少工具命令: ${command_name}" >&2
        exit 1
    }
done

# 后续 APT 安装可能调整已装依赖，最终再次核对每个直接工具包版本。
locked_packages=(
    "nmap:NMAP_VERSION"
    "rustscan:RUSTSCAN_VERSION"
    "amass:AMASS_VERSION"
    "subfinder:SUBFINDER_VERSION"
    "nuclei:NUCLEI_VERSION"
    "fierce:FIERCE_VERSION"
    "dnsenum:DNSENUM_VERSION"
    "autorecon:AUTORECON_VERSION"
    "theharvester:THEHARVESTER_VERSION"
    "responder:RESPONDER_VERSION"
    "netexec:NETEXEC_VERSION"
    "enum4linux-ng:ENUM4LINUX_NG_VERSION"
    "gobuster:GOBUSTER_VERSION"
    "feroxbuster:FEROXBUSTER_VERSION"
    "dirsearch:DIRSEARCH_VERSION"
    "ffuf:FFUF_VERSION"
    "httpx-toolkit:HTTPX_TOOLKIT_VERSION"
    "katana:KATANA_VERSION"
    "hakrawler:HAKRAWLER_VERSION"
    "sqlmap:SQLMAP_VERSION"
    "arjun:ARJUN_VERSION"
    "paramspider:PARAMSPIDER_VERSION"
    "dalfox:DALFOX_VERSION"
    "wafw00f:WAFW00F_VERSION"
    "qsreplace:QSREPLACE_VERSION"
    "uro:URO_VERSION"
    "wfuzz:WFUZZ_VERSION"
    "hydra:HYDRA_VERSION"
    "john:JOHN_VERSION"
    "hashcat:HASHCAT_VERSION"
    "medusa:MEDUSA_VERSION"
    "patator:PATATOR_VERSION"
    "crackmapexec:CRACKMAPEXEC_VERSION"
    "evil-winrm:EVIL_WINRM_VERSION"
    "hash-identifier:HASH_IDENTIFIER_VERSION"
    "gdb:GDB_VERSION"
    "radare2:RADARE2_VERSION"
    "binwalk:BINWALK_VERSION"
    "ghidra:GHIDRA_VERSION"
    "checksec:CHECKSEC_VERSION"
    "binutils:BINUTILS_VERSION"
    "xxd:XXD_VERSION"
    "steghide:STEGHIDE_VERSION"
    "libimage-exiftool-perl:EXIFTOOL_VERSION"
    "masscan:MASSCAN_VERSION"
    "dirb:DIRB_VERSION"
    "ophcrack-cli:OPHCRACK_CLI_VERSION"
    "foremost:FOREMOST_VERSION"
)
for entry in "${locked_packages[@]}"; do
    package_name="${entry%%:*}"
    version_key="${entry#*:}"
    case "${package_name}" in
        masscan|dirb|ophcrack-cli|foremost)
            case "${TARGETARCH}" in
                amd64) version_key="${version_key}_AMD64" ;;
                arm64) version_key="${version_key}_ARM64" ;;
            esac
            ;;
    esac
    actual="$(dpkg-query -W -f='${Version}' "${package_name}")"
    if [ "${actual}" != "${!version_key}" ]; then
        echo "工具版本不匹配: ${package_name}，预期 ${!version_key}，实际 ${actual}" >&2
        exit 1
    fi
done
gem list --local --exact wpscan --version "${WPSCAN_VERSION}" --installed

/usr/local/bin/python3.11 -c 'import ssl, sqlite3, bz2, lzma, ctypes, readline, dbm.gnu, uuid; import sys; assert sys.version_info[:2] == (3, 11)'
/opt/volatility3-venv/bin/python -m pip check
installed_version="$(/opt/volatility3-venv/bin/python -c 'from importlib.metadata import version; print(version("volatility3"))')"
test "${installed_version}" = "${VOLATILITY3_VERSION}"
printf 'volatility3\t%s\tall\n' "${installed_version}" >> /opt/hexstrike/tool-versions.lock

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
