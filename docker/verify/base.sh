#!/usr/bin/env bash
# 验证工具镜像，无外部扫描；任意缺失或版本不符立即失败。
set -euo pipefail

# 只允许 AutoRecon 默认枚举的三份小字典；其他 SecLists 数据仍须挂卷。
/usr/local/bin/python3.11 - <<'PY'
from pathlib import Path

data = Path("/opt/hexstrike-compat/autorecon-data")
root = Path("/usr/share/seclists")
expected = set((data / "manifest.txt").read_text().splitlines())
assert len(expected) == 3, "AutoRecon 小字典清单不完整"
actual = {str(path.relative_to(root)) for path in root.rglob("*") if path.is_file() or path.is_symlink()}
assert actual == expected, "SecLists 包含额外数据或缺少默认小字典"
for relative in expected:
    source = data / relative
    assert source.is_file() and source.stat().st_size > 0, f"缺少字典: {relative}"
    assert (root / relative).is_symlink() and (root / relative).resolve() == source.resolve(), f"字典路径错误: {relative}"
assert sum((data / relative).stat().st_size for relative in expected) <= 4 * 1024 * 1024, "小字典超过 4 MiB 预算"
PY

expected_commands=(
    nmap masscan rustscan amass subfinder nuclei fierce dnsenum
    autorecon theHarvester responder nxc enum4linux-ng gobuster feroxbuster dirsearch
    ffuf dirb httpx katana hakrawler nikto sqlmap wpscan
    arjun paramspider dalfox wafw00f gau waybackurls x8 anew
    qsreplace uro wfuzz hydra john hashcat medusa patator
    crackmapexec evil-winrm hash-identifier ophcrack-cli gdb r2 radare2 binwalk
    ghidra analyzeHeadless checksec strings objdump xxd vol foremost
    steghide exiftool
    volatility volatility2-python vol.py
    testssl whatweb jwt_tool trufflehog tcpdump
    docker kubectl helm kube-bench kube-hunter
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
/opt/kube-hunter-venv/bin/python -m pip check
/opt/kube-hunter-venv/bin/python -c 'import kube_hunter, kubernetes, netifaces, netaddr, requests, ruamel.yaml'
# 同时验证固定发布包中的 CIS 配置内容，不只校验清单文件自身。
sha256sum -c /opt/kube-bench/cfg.sha256 >/dev/null

# ELF 头验证架构，不依赖编译器进入最终镜像。
/usr/local/bin/python3.11 - <<'PY'
import os
import struct
from pathlib import Path

machine = {"amd64": 62, "arm64": 183}[os.environ["TARGETARCH"]]
executables = [Path("/usr/local/bin", name) for name in ("gau", "waybackurls", "anew", "dalfox", "x8")]
executables.append(Path("/opt/python2/bin/python2.7"))
executables.append(Path("/opt/kube-bench/kube-bench"))
for executable in executables:
    with executable.open("rb") as binary:
        header = binary.read(20)
    assert header[:4] == b"\x7fELF", f"{executable}: 非 ELF 文件"
    assert header[5] == 1, f"{executable}: 非小端 ELF"
    assert struct.unpack("<H", header[18:20])[0] == machine, f"{executable}: 架构不匹配"
PY

timeout 30 nmap --version
timeout 30 x8 --version
timeout 30 dalfox version
timeout 30 vol -h >/dev/null

# 原接口的隔离环境与兼容入口；不读取内存样本，不访问目标。
/opt/paramspider-venv/bin/python -m pip check
volatility2-python -m pip check
volatility2-python -c 'import ssl, sqlite3, bz2, ctypes, Crypto, distorm3, yara, pefile, capstone, PIL; import sys; assert sys.version_info[:3] == (2, 7, 18)'
timeout 30 volatility -h >/dev/null
timeout 30 vol.py -h >/dev/null
timeout 30 /usr/local/bin/python3.11 /opt/volatility3/vol.py -h >/dev/null
timeout 30 paramspider -h >/dev/null

# 只查询版本/帮助，不抓包、不连接目标、不扫描本地内容。
timeout 30 testssl --version
timeout 30 whatweb --version
timeout 30 trufflehog --version
timeout 30 tcpdump --version
timeout 30 jwt_tool -h >/dev/null

# 只读取客户端版本；不访问 Docker socket、Kubernetes 集群或漏洞数据库。
timeout 30 docker --version
timeout 30 kubectl version --client=true --output=json
timeout 30 helm version --short
timeout 30 kube-bench version
timeout 30 kube-hunter --help >/dev/null

# 兼容入口使用显式 PATH，不覆盖上面验证摘要和 ELF 架构的原始二进制。
for name in enum4linux-ng gobuster checksec binwalk waybackurls anew analyzeHeadless autorecon hakrawler nuclei; do
    test "$(command -v "${name}")" = "/opt/hexstrike-compat/bin/${name}"
done
test "$(id -u hexstrike-extract)" -ne 0
test "$(id -u hexstrike-extract)" = "$(id -g hexstrike-extract)"
test -r /opt/hexstrike-compat/ghidra/ExportXml.java
/usr/local/bin/python3.11 -m py_compile /opt/hexstrike-compat/cli-compat.py
/usr/local/bin/python3.11 -m py_compile /opt/hexstrike-compat/nuclei-compat.py
timeout 30 nuclei -version
/usr/local/bin/python3.11 -m py_compile /opt/hexstrike-compat/autorecon-compat.py \
    /opt/hexstrike-compat/autorecon-plugins/hexstrike-tcp-profiles.py \
    /opt/hexstrike-compat/hakrawler-compat.py /opt/hexstrike-compat/hakrawler_runtime.py \
    /opt/hexstrike-compat/hakrawler_sources.py /opt/hexstrike-compat/hakrawler_process.py
