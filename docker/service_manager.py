"""在 tini 下管理 API 与 MCP 两个独立进程组，不自动重启服务。"""
import logging
import os
import signal
import subprocess
import sys
import time

from service_health import load_configuration, probe_http

LOGGER = logging.getLogger("hexstrike.services")


def service_commands(config):
    """构造独立解释器的参数列表，禁止通过 shell 拼接执行。"""
    api = [config.api_python, str(config.root / "server.py"),
           "--port", str(config.api_port)]
    mcp = [config.mcp_python, str(config.root / "mcp_server.py"),
           "--host", "0.0.0.0",
           "--port", str(config.mcp_port), "--server", config.api_url]
    return api, mcp


class ServiceManager:
    """按就绪顺序启动服务，任何异常退出均结束整个容器。"""

    def __init__(self, config, *, commands=None):
        self.config = config
        self.commands = commands
        self.children = []
        self.stop_signal = None
        self.startup_deadline = time.monotonic() + config.startup_timeout

    def handle_signal(self, signum, _frame):
        """记录停止信号，由主循环统一转发和回收。"""
        if self.stop_signal is None:
            self.stop_signal = signum

    def start(self, command):
        """创建独立进程组，使后续清理包含服务的子进程。"""
        child = subprocess.Popen(command, start_new_session=True)
        self.children.append(child)
        LOGGER.info("已启动服务：%s，PID=%s", command[1], child.pid)

    def child_failed(self):
        """核心进程未经请求退出时，即使退出码为零也视为失败。"""
        for child in self.children:
            code = child.poll()
            if code is not None:
                LOGGER.error("服务意外退出：PID=%s，退出码=%s", child.pid, code)
                return True
        return False

    def wait_ready(self, url):
        """在整个启动期限内等待就绪，同时检查已启动的全部进程。"""
        while not self.stop_signal:
            if self.child_failed():
                return False
            remaining = self.startup_deadline - time.monotonic()
            if remaining <= 0:
                LOGGER.error("服务启动超时：%s", url)
                return False
            if probe_http(url, timeout=min(1, remaining)):
                return not self.stop_signal and not self.child_failed()
            time.sleep(min(0.1, remaining))
        return False

    def monitor(self):
        """持续监控进程；显式停止成功，任何意外退出返回失败。"""
        while not self.stop_signal:
            if self.child_failed():
                return 1
            time.sleep(0.1)
        return 0

    def signal_groups(self, signum):
        """即使组长已经退出，也向仍存活的进程组转发信号。"""
        for child in self.children:
            try:
                os.killpg(child.pid, signum)
            except ProcessLookupError:
                LOGGER.debug("进程组已退出：%s", child.pid)
            except OSError:
                LOGGER.exception("无法向进程组 %s 发送信号 %s", child.pid, signum)

    def groups_alive(self):
        """回收直接子进程并检查组内是否还有后代进程。"""
        alive = False
        for child in self.children:
            child.poll()
            try:
                os.killpg(child.pid, 0)
                alive = True
            except ProcessLookupError:
                continue
            except PermissionError:
                LOGGER.error("无法检查进程组：%s", child.pid)
                alive = True
        return alive

    def shutdown(self):
        """限时优雅退出，超时后强制清理完整进程组并回收子进程。"""
        self.signal_groups(self.stop_signal or signal.SIGTERM)
        deadline = time.monotonic() + self.config.shutdown_timeout
        while self.groups_alive() and time.monotonic() < deadline:
            time.sleep(0.05)
        self.signal_groups(signal.SIGKILL)
        for child in self.children:
            try:
                child.wait(timeout=1)
            except subprocess.TimeoutExpired:
                LOGGER.error("强制停止后仍未回收进程：%s", child.pid)

    def run(self):
        """启动双服务并监控到结束；所有退出路径都执行清理。"""
        try:
            api, mcp = self.commands or service_commands(self.config)
            self.start(api)
            if not self.wait_ready(self.config.api_probe_url):
                return 0 if self.stop_signal else 1
            self.start(mcp)
            if not self.wait_ready(self.config.readiness_url):
                return 0 if self.stop_signal else 1
            LOGGER.info("HTTP API 和 Streamable HTTP MCP 均已就绪")
            return self.monitor()
        except OSError:
            LOGGER.exception("服务启动失败")
            return 1
        finally:
            self.shutdown()


def main(config=None, *, commands=None):
    """安装信号处理器并启动管理器，供容器和隔离测试调用。"""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        manager = ServiceManager(config or load_configuration(), commands=commands)
    except ValueError as error:
        LOGGER.error("服务配置错误：%s", error)
        return 1
    previous = {}
    try:
        for signum in (signal.SIGTERM, signal.SIGINT):
            previous[signum] = signal.signal(signum, manager.handle_signal)
        return manager.run()
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


if __name__ == "__main__":
    sys.exit(main())
