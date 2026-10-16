"""对已构建基础镜像执行真实应用缓存回归；不修改工作区源码。"""
import argparse
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def command(arguments):
    """执行命令，失败时保留构建诊断并终止。"""
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=1800)
    log = result.stdout + result.stderr
    if result.returncode:
        raise RuntimeError(log)
    return log


def build(context, base, arch, tag):
    """从临时上下文构建应用镜像并返回逐步骤日志。"""
    return command([
        "docker", "buildx", "build", "--platform", f"linux/{arch}",
        "--build-arg", f"BASE_IMAGE={base}", "--tag", tag,
        "--load", "--progress=plain", str(context),
    ])


def check_dependency_cache(log, expected):
    """检查真正的依赖安装步骤是否命中缓存。"""
    match = re.search(r"#(\d+) .*RUN sed -E", log)
    if not match:
        raise AssertionError("构建日志中没有找到项目依赖安装步骤")
    cached = f"#{match[1]} CACHED" in log
    if cached != expected:
        raise AssertionError(f"依赖缓存状态不符，预期 {expected}\n{log}")


def check_isolation(tag):
    """验证重建应用未破坏 Volatility3 与 JWT-Tool 独立环境。"""
    command([
        "docker", "run", "--rm", "--entrypoint", "/bin/bash", tag, "-ec",
        "/usr/local/bin/python3.11 -m pip --python /opt/hexstrike-venv/bin/python check; "
        "/opt/volatility3-venv/bin/python -m pip check; vol -h >/dev/null; "
        "/opt/jwt-tool-venv/bin/python -m pip check; jwt_tool -h >/dev/null; "
        "test \"$(command -v python3)\" = /opt/hexstrike-venv/bin/python3; "
        "python3 -c 'import requests, httpx'",
    ])


def verify(context, base, arch, tags):
    """依次验证首次构建、代码变化和依赖输入变化。"""
    for name in ("Dockerfile", "requirements.txt", "hexstrike_server.py", "hexstrike_mcp.py"):
        shutil.copy2(ROOT / name, context / name)
    build(context, base, arch, tags[0])
    with (context / "hexstrike_server.py").open("a", encoding="utf-8") as source:
        source.write("\n# 缓存回归：仅代码发生变化。\n")
    code_log = build(context, base, arch, tags[1])
    check_dependency_cache(code_log, expected=True)
    check_isolation(tags[1])
    with (context / "requirements.txt").open("a", encoding="utf-8") as requirements:
        requirements.write("\n# 缓存回归：依赖输入发生变化。\n")
    dependency_log = build(context, base, arch, tags[2])
    check_dependency_cache(dependency_log, expected=False)
    check_isolation(tags[2])


def main():
    """运行缓存回归并清理本次创建的临时镜像标签。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_image")
    parser.add_argument("arch", choices=("amd64", "arm64"))
    args = parser.parse_args()
    inspect = ["docker", "image", "inspect", "--format", "{{.Id}}", args.base_image]
    before = command(inspect)
    prefix = f"pentest-tools-cache-check-{uuid.uuid4().hex[:12]}"
    tags = [f"{prefix}:{index}" for index in range(3)]
    try:
        with tempfile.TemporaryDirectory(prefix="pentest-cache-") as temporary:
            verify(Path(temporary), args.base_image, args.arch, tags)
        if command(inspect) != before:
            raise AssertionError("缓存回归期间基础镜像发生变化")
        print(f"应用代码/依赖缓存及环境隔离验证通过: {args.arch}")
    finally:
        for tag in tags:
            result = subprocess.run(["docker", "image", "rm", tag], capture_output=True, text=True)
            if result.returncode:
                print(f"临时镜像未生成或未能清理 {tag}: {result.stderr.strip()}")


if __name__ == "__main__":
    main()
