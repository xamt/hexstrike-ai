"""数据库客户端的单次、有界执行；无 shell、缓存和自动重试。"""
import json
import os
import selectors
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from urllib.parse import quote

from .commands import build_invocation

SLOTS = threading.BoundedSemaphore(4)
ERRORS = {
    "busy": "数据库执行并发已达上限，请先检查正在执行的任务",
    "tool_missing": "服务镜像中缺少对应数据库客户端",
    "timeout": "客户端已超时终止；远端操作状态未知，不得自动重试写入",
    "output_limit": "输出超过上限，客户端已终止；结果不完整，远端状态需核实",
    "command_failed": "数据库客户端返回失败，请检查脱敏后的输出",
    "execution_error": "数据库客户端无法正常执行",
}


def execute_database(name, args):
    """执行一次已校验请求；每个服务进程最多同时启动四个客户端。"""
    if not SLOTS.acquire(blocking=False):
        return _result("busy")
    started = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix="hexstrike-db-") as directory:
            invocation = build_invocation(name, args, directory)
            executable = shutil.which(invocation.argv[0])
            if executable is None:
                return _result("tool_missing")
            invocation.argv[0] = executable
            env = _environment(directory, invocation.environment)
            return _execute(invocation, args, directory, env, started)
    except (OSError, ValueError):
        return _result("execution_error")
    finally:
        SLOTS.release()


def _environment(directory, additions):
    # 不继承数据库连接默认值、代理、预加载、API 密钥或父服务的秘密。
    env = {"PATH": os.defpath, "HOME": directory, "LANG": "C.UTF-8",
           "LC_ALL": "C.UTF-8", "TMPDIR": directory,
           "XDG_CONFIG_HOME": directory, "MONGOSH_DISABLE_TELEMETRY": "1"}
    env.update(additions)
    return env


def _execute(invocation, args, directory, env, started):
    with subprocess.Popen(invocation.argv, stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          shell=False, env=env, cwd=directory,
                          start_new_session=True, bufsize=0) as process:
        try:
            output, error_code = _pump(process, invocation.stdin, args)
        except Exception:
            _kill(process)
            process.wait()
            raise
        process.wait()
        if not error_code and process.returncode != 0:
            error_code = "command_failed"
    result = _result(error_code, process.returncode)
    result.update(_safe_output(output, args["password"], args["max_output_bytes"],
                               error_code in {"timeout", "output_limit"}))
    result["execution_time"] = round(time.monotonic() - started, 3)
    return result


def _pump(process, input_bytes, args):
    output = {"stdout": bytearray(), "stderr": bytearray()}
    deadline = time.monotonic() + args["timeout"]
    with selectors.DefaultSelector() as selector:
        for label in ("stdout", "stderr"):
            stream = getattr(process, label)
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, label)
        if input_bytes:
            os.set_blocking(process.stdin.fileno(), False)
            selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
        else:
            process.stdin.close()
        remaining = memoryview(input_bytes)
        while selector.get_map() or process.poll() is None:
            if time.monotonic() >= deadline:
                _kill(process)
                return output, "timeout"
            events = selector.select(min(0.1, max(0, deadline - time.monotonic())))
            for key, _ in events:
                if key.data == "stdin":
                    remaining = _write_input(selector, key.fileobj, remaining)
                elif _read_output(selector, key, output, args["max_output_bytes"]):
                    _kill(process)
                    return output, "output_limit"
    return output, None


def _write_input(selector, stream, remaining):
    try:
        written = os.write(stream.fileno(), remaining[:8192])
        remaining = remaining[written:]
    except BrokenPipeError:
        remaining = remaining[:0]
    if not remaining:
        selector.unregister(stream)
        stream.close()
    return remaining


def _read_output(selector, key, output, limit):
    chunk = os.read(key.fileobj.fileno(), 8192)
    if not chunk:
        selector.unregister(key.fileobj)
        key.fileobj.close()
        return False
    capacity = limit - sum(len(value) for value in output.values())
    output[key.data].extend(chunk[:capacity])
    return len(chunk) > capacity


def _kill(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass  # 进程已退出，与终止目标一致。


def _safe_output(output, password, limit, incomplete=False):
    variants = {password, quote(password, safe=""),
                json.dumps(password, ensure_ascii=True)[1:-1],
                password.replace("'", "''"),
                password.replace("\\", "\\\\").replace('"', '\\"')}
    variants.discard("")
    result = {}
    for name, value in output.items():
        text = bytes(value).decode("utf-8", errors="replace")
        for secret in sorted(variants, key=len, reverse=True):
            text = text.replace(secret, "[REDACTED]")
            # 截断恰好发生在密码中间时，不泄露保留前缀。
            for length in range(min(len(secret) - 1, len(text)), 0, -1) if incomplete else ():
                if text.endswith(secret[:length]):
                    text = text[:-length] + "[REDACTED]"
                    break
        result[name] = text.encode("utf-8")[:limit].decode("utf-8", errors="ignore")
        limit -= len(result[name].encode("utf-8"))
    return result


def _result(error_code=None, return_code=None):
    result = {"success": error_code is None, "return_code": return_code,
              "stdout": "", "stderr": "", "timed_out": error_code == "timeout",
              "truncated": error_code == "output_limit"}
    if error_code:
        result.update(error_code=error_code, error=ERRORS[error_code])
    return result
