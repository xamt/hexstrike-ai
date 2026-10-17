#!/usr/bin/env bash
# 兼容原代码中的历史参数/路径；不修改 APT 原命令或工具版本。
set -euo pipefail

# 独立 PATH 入口不覆盖原工具，Go 产物摘要与架构校验仍指向原二进制。
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
install -d /opt/hexstrike-compat/bin
install -d /opt/hexstrike-compat/ghidra
install -m 0755 "${script_dir}/cli-compat.py" /opt/hexstrike-compat/cli-compat.py
install -m 0644 "${script_dir}/ExportXml.java" /opt/hexstrike-compat/ghidra/ExportXml.java
for name in enum4linux-ng gobuster checksec binwalk waybackurls anew analyzeHeadless; do
    ln -s ../cli-compat.py "/opt/hexstrike-compat/bin/${name}"
done
# 原 MCP 默认值由环境承接；原始 AutoRecon/Hakrawler 仍保留在 /usr/bin。
install -d /opt/hexstrike-compat/autorecon-plugins
install -m 0644 "${script_dir}/autorecon-plugins/hexstrike-tcp-profiles.py" \
    /opt/hexstrike-compat/autorecon-plugins/hexstrike-tcp-profiles.py
for name in autorecon hakrawler; do
    install -m 0755 "${script_dir}/${name}-compat.py" "/opt/hexstrike-compat/${name}-compat.py"
    ln -s "../${name}-compat.py" "/opt/hexstrike-compat/bin/${name}"
done
for name in hakrawler_runtime.py hakrawler_sources.py hakrawler_process.py; do
    install -m 0644 "${script_dir}/${name}" "/opt/hexstrike-compat/${name}"
done
# 模板由运行时只读挂载，不在构建或第一次扫描时下载。
install -d /opt/nuclei-templates
install -m 0755 "${script_dir}/nuclei-compat.py" /opt/hexstrike-compat/nuclei-compat.py
ln -s ../nuclei-compat.py /opt/hexstrike-compat/bin/nuclei
# Binwalk 主进程仍能读取输入，但外部解包程序不默认以 root 执行。
# Binwalk 2.x 的 UID/GID 处理存在历史缺陷，专用用户使用相同且均未占用的编号。
if ! id hexstrike-extract >/dev/null 2>&1; then
    extract_id=100
    while getent passwd "${extract_id}" >/dev/null || getent group "${extract_id}" >/dev/null; do
        extract_id=$((extract_id + 1))
        if [ "${extract_id}" -gt 999 ]; then
            echo "无法分配提取用户的系统 UID/GID" >&2
            exit 1
        fi
    done
    groupadd --system --gid "${extract_id}" hexstrike-extract
    useradd --system --uid "${extract_id}" --gid "${extract_id}" \
        --no-create-home --shell /usr/sbin/nologin hexstrike-extract
fi
test "$(id -u hexstrike-extract)" = "$(id -g hexstrike-extract)"
test "$(id -u hexstrike-extract)" -ne 0

cat > /usr/local/bin/arjun <<'PY'
#!/usr/local/bin/python3.11
"""将历史 GET/POST 开关转为两个明确调用，现代参数原样传递。"""
import subprocess
import sys


def main():
    """兼容旧调用并保留输出、错误状态，不对失败命令重试。"""
    arguments = sys.argv[1:]
    methods = [method for flag, method in (("--get", "GET"), ("--post", "POST"))
               if flag in arguments]
    if methods and any(arg == "-m" or arg.startswith("-m") for arg in arguments):
        sys.stderr.write("旧方法开关不能与 -m 同时使用\n")
        return 2
    arguments = [arg for arg in arguments if arg not in ("--get", "--post")]
    for method in methods or [None]:
        command = ["/usr/bin/arjun"] + arguments
        if method:
            command += ["-m", method]
        status = subprocess.call(command)
        if status:
            return status if status > 0 else 128 - status
    return 0


if __name__ == "__main__":
    sys.exit(main())
PY

cat > /usr/local/bin/fierce <<'PY'
#!/usr/local/bin/python3.11
"""兼容旧 CTF 命令的 -dns，其他参数原样交给系统 Fierce。"""
import os
import sys

arguments = ["--domain" if arg == "-dns" else arg for arg in sys.argv[1:]]
os.execv("/usr/bin/fierce", ["fierce"] + arguments)
PY

# 原代码显式使用 python3 运行旧路径，必须提供 Python 入口而非 Shell 符号链接。
mkdir -p /opt/jwt_tool
cat > /opt/jwt_tool/jwt_tool.py <<'PY'
#!/usr/bin/env python3
"""将旧源码路径转交给已隔离、固定工作目录的 JWT-Tool 包装命令。"""
import os
import sys

os.execv("/usr/local/bin/jwt_tool", ["jwt_tool"] + sys.argv[1:])
PY
chmod 0755 /usr/local/bin/arjun /usr/local/bin/fierce /opt/jwt_tool/jwt_tool.py

# 原接口漏写 run，并且只读取 stdout；每次调用独立报告，不能读取历史报告冒充成功。
cat > /usr/local/bin/kube-bench <<'PY'
#!/usr/local/bin/python3.11
"""兼容历史 Kube-Bench 接口，保留审计失败状态和独立报告。"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def extract_output(arguments):
    """取出报告路径，拒绝重复或缺值参数。"""
    remaining, output = [], None
    values = iter(arguments)
    for value in values:
        if value == "--outputfile" or value.startswith("--outputfile="):
            if output is not None:
                raise ValueError("不能重复指定 --outputfile")
            output = value.split("=", 1)[1] if "=" in value else next(values, "")
            if not output or output.startswith("-"):
                raise ValueError("--outputfile 缺少有效路径")
        else:
            remaining.append(value)
    return remaining, output


def run_report(command, output):
    """只返回本次报告，保留发现风险时显式配置的非零退出状态。"""
    target = Path(output).absolute()
    descriptor, name = tempfile.mkstemp(prefix=".kube-bench-", dir=target.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        status = subprocess.call(command + ["--outputfile", name])
        if not temporary.stat().st_size:
            if status:
                return status if status > 0 else 128 - status
            raise ValueError("Kube-Bench 未生成报告")
        report = temporary.read_text(encoding="utf-8")
        temporary.replace(target)
        sys.stdout.write(report)
        return status if status >= 0 else 128 - status
    finally:
        temporary.unlink(missing_ok=True)


def main():
    """补齐旧参数的子命令和配置目录，不改写目标或检查结果。"""
    try:
        arguments, output = extract_output(sys.argv[1:])
        if arguments and arguments[0].startswith("-") and any(
            arg in ("--targets", "-s") or arg.startswith("--targets=") for arg in arguments
        ):
            arguments.insert(0, "run")
        informational = any(arg in ("version", "help", "--help", "-h") for arg in arguments)
        if not informational and not any(
            arg in ("--config-dir", "-D") or arg.startswith(("--config-dir=", "-D")) for arg in arguments
        ):
            arguments += ["--config-dir", "/etc/kube-bench/cfg"]
        command = ["/opt/kube-bench/kube-bench"] + arguments
        if output:
            return run_report(command, output)
        status = subprocess.call(command)
        return status if status >= 0 else 128 - status
    except (OSError, ValueError) as error:
        print(f"Kube-Bench 兼容入口失败: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
PY

# 上游 --interface 是布尔开关，不是网卡名称；禁止把旧接口的 eth0 静默扩大成所有网卡。
cat > /usr/local/bin/kube-hunter <<'PY'
#!/usr/local/bin/python3.11
"""转交隔离环境，明确拒绝上游不支持的命名网卡参数。"""
import os
import sys


def main():
    """保持显式目标参数不变，不把命名网卡转换成更大的扫描范围。"""
    arguments = sys.argv[1:]
    for index, value in enumerate(arguments):
        named = value.startswith("--interface=") or (
            value == "--interface" and index + 1 < len(arguments)
            and not arguments[index + 1].startswith("-")
        )
        if named:
            print("Kube-Hunter 不支持 interface 网卡名；请使用明确的 target 或 cidr", file=sys.stderr)
            return 2
    os.execv("/opt/kube-hunter-venv/bin/kube-hunter", ["kube-hunter"] + arguments)


if __name__ == "__main__":
    sys.exit(main())
PY
chmod 0755 /usr/local/bin/kube-bench /usr/local/bin/kube-hunter
