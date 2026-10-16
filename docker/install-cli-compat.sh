#!/usr/bin/env bash
# 兼容原代码中的历史参数/路径；不修改 APT 原命令或工具版本。
set -euo pipefail

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
