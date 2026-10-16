"""核对安装脚本记录的预期版本；本文件只维护必需工具名称，不维护版本常量。"""
import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple


REQUIRED = {
    "apt": """nmap masscan rustscan amass subfinder nuclei fierce dnsenum autorecon
        theharvester responder netexec enum4linux-ng gobuster feroxbuster dirsearch
        ffuf dirb httpx-toolkit katana hakrawler sqlmap arjun paramspider dalfox wafw00f
        qsreplace uro wfuzz hydra john hashcat medusa patator crackmapexec evil-winrm
        hash-identifier ophcrack-cli gdb radare2 binwalk ghidra checksec binutils xxd
        foremost steghide libimage-exiftool-perl mariadb-client mariadb-client-core
        mariadb-client-compat redis-tools postgresql-client-18 clickhouse-client
        clickhouse-common-static mongodb-mongosh testssl.sh whatweb trufflehog tcpdump""".split(),
    "gem": ["wpscan"],
    "go": ["gau", "waybackurls", "anew"],
    "rust": ["x8"],
    "source": ["nikto", "jwt_tool"],
    "python": ["pip", "setuptools", "wheel"],
    "vol-python": ["pip", "setuptools", "wheel", "volatility3"],
    "jwt-python": ["termcolor", "cprint", "pycryptodomex", "requests", "ratelimit"],
}
PYTHON_EXECUTABLES = {
    "python": "/usr/local/bin/python3.11",
    "vol-python": "/opt/volatility3-venv/bin/python",
    "jwt-python": "/opt/jwt-tool-venv/bin/python",
}


class Record(NamedTuple):
    """一条成功安装产生的预期记录。"""

    kind: str
    name: str
    version: str
    arch: str
    digest: str
    path: str


def load_records(directory, arch):
    """严格检查记录格式、完整性和架构，缺失记录不能当作跳过安装。"""
    records = {}
    required = {(kind, name) for kind, names in REQUIRED.items() for name in names}
    for path in sorted(directory.glob("*.tsv")):
        fields = path.read_text(encoding="utf-8").rstrip("\n").split("\t")
        if len(fields) != 6 or any(not field or "\n" in field for field in fields):
            raise ValueError(f"版本记录格式错误: {path.name}")
        record = Record(*fields)
        key = (record.kind, record.name)
        if key in records or path.name != f"{record.kind}-{record.name}.tsv":
            raise ValueError(f"重复或错误命名的版本记录: {path.name}")
        if record.arch not in (arch, "all"):
            raise ValueError(f"版本记录架构错误: {path.name}: {record.arch}")
        if record.kind in ("apt", "go", "rust") and record.arch != arch:
            raise ValueError(f"必须记录目标架构: {path.name}")
        if record.kind in ("go", "rust", "source"):
            if not re.fullmatch(r"[a-f0-9]{64}", record.digest) or not Path(record.path).is_absolute():
                raise ValueError(f"产物摘要记录错误: {path.name}")
        elif (record.digest, record.path) != ("-", "-"):
            raise ValueError(f"包版本记录不应包含产物路径: {path.name}")
        records[key] = record
    if set(records) != required:
        missing, extra = sorted(required - records.keys()), sorted(records.keys() - required)
        raise ValueError(f"工具版本记录不完整: 缺少 {missing}，多余 {extra}")
    return records


def command_output(command):
    """执行本地查询命令，失败直接向调用方抛出，不尝试其他版本。"""
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout.strip()


def verify_apt(record):
    """核对 dpkg 完整安装状态、实际版本和软件包架构。"""
    actual = command_output([
        "dpkg-query", "-W", "-f=${Status}\t${Version}\t${Architecture}", record.name,
    ]).split("\t")
    if len(actual) != 3 or actual[0] != "install ok installed":
        raise ValueError(f"工具包未完整安装: {record.name}: {actual}")
    if actual[1] != record.version or actual[2] not in (record.arch, "all"):
        raise ValueError(f"工具包版本或架构不符: {record.name}: 预期 {record.version}/{record.arch}，实际 {actual[1:]}")
    return actual[1], actual[2]


def verify_record(record):
    """将一条预期记录与最终镜像中的实际安装结果比较。"""
    if record.kind == "apt":
        return verify_apt(record)
    if record.kind == "gem":
        command_output(["gem", "list", "--local", "--exact", record.name,
                        "--version", record.version, "--installed"])
    elif record.kind in PYTHON_EXECUTABLES:
        actual = command_output([
            PYTHON_EXECUTABLES[record.kind], "-c",
            "import sys; from importlib.metadata import version; print(version(sys.argv[1]))",
            record.name,
        ])
        if actual != record.version:
            raise ValueError(f"Python 包版本不符: {record.kind}/{record.name}: {actual} != {record.version}")
    elif record.kind in ("go", "rust", "source"):
        digest = hashlib.sha256()
        with Path(record.path).open("rb") as artifact:
            for block in iter(lambda: artifact.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != record.digest:
            raise ValueError(f"安装产物摘要不符: {record.name}")
    else:
        raise ValueError(f"未知安装类型: {record.kind}")
    return record.version, record.arch


def write_lock(records, output):
    """全部校验成功后原子写出兼容原路径和三列格式的工具清单。"""
    rows = []
    for record in records.values():
        version, arch = verify_record(record)
        if record.kind in PYTHON_EXECUTABLES and record.name != "volatility3":
            continue
        rows.append(f"{record.name}\t{version}\t{arch}\n")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text("# tool\tversion\tarchitecture\n" + "".join(sorted(rows)), encoding="utf-8")
    temporary.replace(output)


def main():
    """最终镜像校验入口；不访问包源或外部目标。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arch", required=True, choices=("amd64", "arm64"))
    parser.add_argument("--records", type=Path, default=Path("/opt/hexstrike/tool-versions.d"))
    parser.add_argument("--output", type=Path, default=Path("/opt/hexstrike/tool-versions.lock"))
    args = parser.parse_args()
    try:
        write_lock(load_records(args.records, args.arch), args.output)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"工具版本校验失败: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
