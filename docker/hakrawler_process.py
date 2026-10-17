"""有时间和输出大小上限的外部进程执行，不使用 shell。"""
import subprocess
import tempfile
import time

MAX_OUTPUT = 8 * 1024 * 1024


def run_process(command, input_text, deadline, environment=None):
    """执行工具并保留失败；stdout/stderr 超过上限时终止进程。"""
    with tempfile.TemporaryFile() as stdin, tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        stdin.write(input_text.encode("utf-8"))
        stdin.seek(0)
        process = subprocess.Popen(command, stdin=stdin, stdout=stdout, stderr=stderr, env=environment)
        try:
            while process.poll() is None:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Hakrawler 兼容调用已达到总时间上限")
                if stdout.tell() > MAX_OUTPUT or stderr.tell() > MAX_OUTPUT:
                    raise RuntimeError("工具输出超过 8 MiB 上限")
                time.sleep(0.05)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
        stdout.seek(0)
        stderr.seek(0)
        result, errors = stdout.read(MAX_OUTPUT + 1), stderr.read(MAX_OUTPUT + 1)
        if len(result) > MAX_OUTPUT or len(errors) > MAX_OUTPUT:
            raise RuntimeError("工具输出超过 8 MiB 上限")
        errors = errors.decode("utf-8", errors="replace").strip()
        if process.returncode or errors:
            # 上游遇到超时/Wayback 提供商失败时可能仍返回 0，不能伪装成完整成功。
            raise RuntimeError(f"{command[0]} 执行异常（退出码 {process.returncode}）：{errors[:2000]}")
        return result.decode("utf-8")
