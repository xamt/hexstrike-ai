"""现有 MCP 四个发现开关与 Hakrawler 2.1 CLI 的兼容入口。"""
import json
import os
import sys
import time

from hakrawler_process import run_process
from hakrawler_sources import Fetcher, MAX_URLS, discover

FEATURES = {"forms", "robots", "sitemap", "wayback"}
BOOLEAN_OPTIONS = {"insecure", "subs", "json", "s", "u"}
VALUE_OPTIONS = {"t", "d", "size", "h", "proxy", "timeout"}


def boolean(value):
    """只接受明确布尔值，避免把非空的 false 字符串当成真。"""
    if value.lower() not in ("true", "false"):
        raise ValueError("布尔参数只接受 true 或 false")
    return value.lower() == "true"


def parse_options(arguments):
    """提取兼容开关，同时保留原生请求/深度选项。"""
    features = dict.fromkeys(FEATURES, False)
    options = dict(t=8, d=2, size=-1, h="", proxy="", timeout=120,
                   insecure=False, subs=False, json=False, s=False, u=False)
    native, index = [], 0
    while index < len(arguments):
        token = arguments[index]
        key, separator, value = token.lstrip("-").partition("=")
        if not token.startswith("-"):
            raise ValueError("兼容模式只从标准输入接收目标 URL")
        if key.startswith("pentest-tools-"):
            name = key.removeprefix("pentest-tools-")
            if name not in FEATURES or not separator:
                raise ValueError("未知或缺少布尔值的 Hakrawler 兼容参数")
            features[name] = boolean(value)
        elif key in BOOLEAN_OPTIONS:
            options[key] = boolean(value) if separator else True
            if key not in ("json", "s"):
                native.append(token)
        elif key in VALUE_OPTIONS:
            if not separator:
                index += 1
                if index == len(arguments):
                    raise ValueError(f"参数 -{key} 缺少值")
                value = arguments[index]
            options[key] = value if key in ("h", "proxy") else int(value)
            if key != "timeout":
                native.extend([f"-{key}", value])
        else:
            raise ValueError(f"不支持的 Hakrawler 参数：{token}")
        index += 1
    if options["d"] < 1 or options["t"] < 1 or options["timeout"] == 0 or options["timeout"] < -1:
        raise ValueError("深度、线程和超时必须为正数；timeout=-1 使用兼容层 120 秒上限")
    if options["size"] == 0 or options["size"] < -1:
        raise ValueError("页面大小必须为正数或 -1")
    options["timeout"] = 120 if options["timeout"] == -1 else options["timeout"]
    options.update(features)
    native += ["-json=true", "-timeout", str(options["timeout"])]
    return features, options, native


def emit_records(records, fetcher, options, seen, output):
    """同范围过滤、精确控制表单输出，并统一去重和输出格式。"""
    for source, candidate in records:
        url = fetcher.scope.normalize(candidate)
        if not url or url in seen or (source == "form" and not options["forms"]):
            continue
        if len(seen) >= MAX_URLS:
            raise RuntimeError("发现结果超过 10000 个 URL 上限，结果不完整")
        seen.add(url)
        if options["json"]:
            print(json.dumps({"Source": source, "URL": url}, ensure_ascii=False), file=output)
        elif options["s"]:
            print(f"[{source}] {url}", file=output)
        else:
            print(url, file=output)


def native_records(text):
    """解析固定版本原生 JSON 行，拒绝未知输出而非静默遗漏。"""
    for line in text.splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record, dict) or not isinstance(record.get("URL"), str) or not isinstance(record.get("Source"), str):
            raise ValueError("Hakrawler 返回不符合约定的 JSON 记录")
        yield record["Source"], record["URL"]


def run_compatible(arguments, stdin, output):
    """执行默认请求；补充 URL 不再次爬取，原生深度保持不变。"""
    _, options, native = parse_options(arguments)
    content = stdin.read(65537)
    targets = list(dict.fromkeys(line.strip() for line in content.splitlines() if line.strip()))
    if len(content) > 65536 or len(targets) > 32 or not targets:
        raise ValueError("标准输入必须包含 1 至 32 个 URL，且不超过 64 KiB")
    deadline, seen = time.monotonic() + options["timeout"], set()
    for target in targets:
        fetcher = Fetcher(target, options, deadline)
        # 上游忽略部分首请求错误；预检避免 DNS/TLS/HTTP 失败被空输出伪装成成功。
        fetcher.fetch(target, probe=True)
        text = run_process(["/usr/bin/hakrawler", *native], target + "\n", deadline)
        emit_records(native_records(text), fetcher, options, seen, output)
        emit_records(discover(fetcher, options), fetcher, options, seen, output)


def main(arguments=None, stdin=None, output=None):
    """无兼容参数时透明转交原生 CLI；兼容错误明确返回非零。"""
    arguments = sys.argv[1:] if arguments is None else arguments
    if not any(arg.startswith("--pentest-tools-") for arg in arguments):
        os.execv("/usr/bin/hakrawler", ["hakrawler", *arguments])
        return 0
    try:
        run_compatible(arguments, sys.stdin if stdin is None else stdin,
                       sys.stdout if output is None else output)
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Hakrawler 兼容调用失败：{error}", file=sys.stderr)
        return 2
