"""显式镜像验收：只读能力检查与本脚本容器生命周期，不执行目标扫描。"""

import argparse
import asyncio
import json
import subprocess
import time
import uuid
from urllib.request import ProxyHandler, build_opener

from mcp import Client


def docker(*args, timeout=40):
    """执行 Docker 命令并保留失败诊断。"""
    result = subprocess.run(["docker", *args], check=True, capture_output=True,
                            text=True, timeout=timeout)
    return result.stdout.strip()


def inspect_container(name):
    """读取本脚本专用容器状态。"""
    return json.loads(docker("inspect", name))[0]


def get_json(url, timeout=5):
    """回环验证绕过宿主代理。"""
    with build_opener(ProxyHandler({})).open(url, timeout=timeout) as response:
        return json.load(response)


def wait_ready(name):
    """同时验证 API 可访问和 MCP ready，而非仅检查进程存在。"""
    deadline = time.monotonic() + 65
    last_error = ""
    while time.monotonic() < deadline:
        info = inspect_container(name)
        if not info["State"]["Running"]:
            raise AssertionError("容器提前退出：" + docker("logs", "--tail", "30", name))
        ports = info["NetworkSettings"]["Ports"]
        api = "http://127.0.0.1:" + ports["8888/tcp"][0]["HostPort"]
        mcp = "http://127.0.0.1:" + ports["8889/tcp"][0]["HostPort"]
        try:
            get_json(api + "/api/cache/stats")
            if get_json(mcp + "/readyz")["status"] == "ready":
                return api, mcp
        except (OSError, ValueError) as error:
            last_error = str(error)
        time.sleep(0.2)
    raise AssertionError("双接口启动超时：" + last_error)


async def verify_protocol(address):
    """真实 SDK 连接镜像中的 HTTP MCP；仅执行健康工具。"""
    async with Client(address + "/mcp", read_timeout_seconds=180) as client:
        tools = await client.list_tools()
        assert len(tools.tools) == 150
        health = await client.call_tool("server_health", {})
        assert not health.is_error, health
        payload = json.loads(health.content[0].text)
        assert payload["status"] == "healthy", payload
        assert len({tool.name for tool in tools.tools}) == 150
    print("通过：镜像 HTTP MCP 发现 150 个唯一工具，server_health 返回成功", flush=True)


def kill_service(name, filename):
    """只终止本脚本专用容器内的指定核心服务，验证故障联动。"""
    script = (
        "import os,signal,psutil,sys; "
        "target='/opt/pentest-tools/'+sys.argv[1]; "
        "matches=[p.pid for p in psutil.process_iter(['cmdline']) "
        "if target in (p.info['cmdline'] or [])]; "
        "assert len(matches)==1,matches; os.kill(matches[0],signal.SIGKILL)"
    )
    docker("exec", name, "/opt/pentest-tools-venv/bin/python", "-c", script, filename)
    code = docker("wait", name, timeout=25)
    assert code == "1", code
    state = inspect_container(name)["State"]
    assert not state["Running"] and state["Pid"] == 0, state
    print(f"通过：{filename} 异常退出触发容器非零退出与清理", flush=True)


def verify_image(image):
    """依次验收双接口、两个核心服务故障及正常停止，始终清理临时容器。"""
    for scenario in ("mcp", "api", "stop"):
        name = "pentest-tools-mcp-check-" + uuid.uuid4().hex[:10]
        started = False
        try:
            docker("run", "--detach", "--name", name,
                   "--publish", "127.0.0.1::8888", "--publish", "127.0.0.1::8889",
                   "--stop-timeout", "15", image)
            started = True
            _, address = wait_ready(name)
            docker("exec", name, "/opt/pentest-tools-venv/bin/python",
                   "/opt/pentest-tools/docker/service_health.py")
            if scenario == "mcp":
                asyncio.run(verify_protocol(address))
                kill_service(name, "mcp_server.py")
            elif scenario == "api":
                kill_service(name, "server.py")
            else:
                docker("stop", "--time", "15", name)
                state = inspect_container(name)["State"]
                assert state["ExitCode"] == 0 and state["Pid"] == 0, state
                print("通过：docker stop 优雅退出，双服务无残留", flush=True)
        finally:
            if started:
                docker("rm", "--force", name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", help="已在本机构建的应用镜像标签")
    verify_image(parser.parse_args().image)
