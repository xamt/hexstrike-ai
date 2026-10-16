"""有限并发的专项客户端执行器：不使用 shell、缓存、日志或自动重试。"""
import os
import selectors
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from .commands import build_command
from .contracts import validate_request

SLOTS = threading.BoundedSemaphore(4)
ERRORS = {
    'invalid_request': '工具请求参数无效', 'busy': '专项工具执行并发已达上限',
    'tool_missing': '镜像中缺少对应工具入口', 'timeout': '工具已超时终止，结果不完整',
    'output_limit': '工具输出超限并已终止，结果不完整',
    'command_failed': '工具返回非零退出码，请检查输出',
    'execution_error': '专项工具无法正常执行',
}


def execute_security(name, payload):
    """校验后单次执行，返回原始证据而非漏洞结论；每进程最多四项并发。"""
    try:
        args = validate_request(name, payload)
    except (ValueError, KeyError):
        return _result('invalid_request')
    if not SLOTS.acquire(blocking=False):
        return _result('busy')
    started = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix='hexstrike-security-') as directory:
            argv = build_command(name, args)
            executable = shutil.which(argv[0], path='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin')
            if executable is None:
                return _result('tool_missing')
            argv[0] = executable
            env = _environment(directory)
            deadline = started + args['timeout']
            if name == 'jwt_tool_analyze':
                error = _prepare_jwt(executable, args, directory, env, deadline)
                if error:
                    return error
            result = _execute(argv, args, directory, env, deadline)
            result['execution_time'] = round(time.monotonic() - started, 3)
            return result
    except (OSError, ValueError):
        return _result('execution_error')
    finally:
        SLOTS.release()


def _environment(directory):
    return {'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
            'HOME': directory, 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
            'TMPDIR': directory, 'XDG_CONFIG_HOME': directory,
            'GIT_TERMINAL_PROMPT': '0', 'GIT_CONFIG_NOSYSTEM': '1',
            'NO_COLOR': '1'}


def _prepare_jwt(executable, args, directory, env, deadline):
    # v2.3.0 首次运行生成独立配置/密钥后退出1；本地初始化不会发送目标请求。
    result = _execute([executable], args, directory, env, deadline)
    if result.get('error_code') in ('timeout', 'output_limit'):
        return _result(result['error_code'], result['return_code'])
    config = Path(directory, '.jwt_tool', 'jwtconf.ini')
    if result['return_code'] != 1 or not config.is_file():
        return _result('execution_error')
    # 上游会将令牌和 argv 写入日志，显式丢弃而不是等待临时目录清理。
    config.with_name('logs.txt').symlink_to(os.devnull)
    return None


def _execute(argv, args, directory, env, deadline):
    with subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, shell=False, env=env, cwd=directory,
                          start_new_session=True, bufsize=0) as process:
        try:
            output, error = _pump(process, deadline, args['max_output_bytes'])
        except Exception:
            _kill(process)
            process.wait()
            raise
        process.wait()
        if not error and process.returncode != 0:
            error = 'command_failed'
    result = _result(error, process.returncode)
    budget = args['max_output_bytes']
    for name, value in output.items():
        # 无效UTF-8替换可能扩张字节，解码后再次执行总输出上限。
        data = bytes(value).decode('utf-8', errors='replace').encode('utf-8')[:budget]
        result[name] = data.decode('utf-8', errors='ignore')
        budget -= len(result[name].encode('utf-8'))
    return result


def _pump(process, deadline, limit):
    output = {'stdout': bytearray(), 'stderr': bytearray()}
    with selectors.DefaultSelector() as selector:
        for name in output:
            stream = getattr(process, name)
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        while selector.get_map() or process.poll() is None:
            if time.monotonic() >= deadline:
                _kill(process)
                return output, 'timeout'
            for key, _ in selector.select(min(0.1, max(0, deadline - time.monotonic()))):
                chunk = os.read(key.fileobj.fileno(), 8192)
                if not chunk:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                capacity = limit - sum(len(value) for value in output.values())
                output[key.data].extend(chunk[:capacity])
                if len(chunk) > capacity:
                    _kill(process)
                    return output, 'output_limit'
    return output, None


def _kill(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass  # 已退出的进程组无需再次终止。


def _result(error=None, return_code=None):
    result = {'success': error is None, 'return_code': return_code,
              'stdout': '', 'stderr': '', 'timed_out': error == 'timeout',
              'truncated': error == 'output_limit',
              'evidence_only': True}
    if error:
        result.update(error_code=error, error=ERRORS[error])
    return result
