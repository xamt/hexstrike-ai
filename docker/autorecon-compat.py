#!/usr/local/bin/python3.11
"""为原有 MCP 端口配置提供 AutoRecon 插件，不改变其他原生命令。"""
import os
import sys


PLUGINS_DIR = "/opt/hexstrike-compat/autorecon-plugins"
PROFILES = {"top-100-ports", "top-1000-ports"}


def option_value(arguments, option):
    """读取命令行最后一次指定的选项值，与上游 argparse 行为一致。"""
    value = None
    for index, argument in enumerate(arguments):
        if argument == "--":
            break
        if argument.startswith(option + "="):
            value = argument.split("=", 1)[1]
        elif argument == option:
            if index + 1 >= len(arguments):
                raise ValueError(f"{option} 缺少参数值")
            value = arguments[index + 1]
    return value


def without_option(arguments, option):
    """移除需要合并的选项，保留终止符之后的目标文本。"""
    result = []
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument == "--":
            result.extend(arguments[index:])
            break
        if argument == option:
            index += 2
            continue
        if not argument.startswith(option + "="):
            result.append(argument)
        index += 1
    return result


def adapt(arguments):
    """只为旧 top-N 配置追加插件及默认端口扫描排除条件。"""
    selected = option_value(arguments, "--port-scans") or ""
    if not PROFILES.intersection(item.strip() for item in selected.split(",")):
        return list(arguments)
    directory = option_value(arguments, "--add-plugins-dir")
    if directory is not None and directory != PLUGINS_DIR:
        raise ValueError("top-N 兼容配置需要内置插件目录，不能覆盖自定义 --add-plugins-dir")
    if option_value(arguments, "--ports") is not None or option_value(arguments, "-p") is not None:
        raise ValueError("top-N 兼容配置与显式端口列表不能同时使用；请明确选择扫描范围")
    excluded = option_value(arguments, "--exclude-tags") or ""
    tags = [tag.strip() for tag in excluded.split(",") if tag.strip()]
    if "default-port-scan" not in tags:
        tags.append("default-port-scan")
    additions = []
    if directory is None:
        additions.extend(["--add-plugins-dir", PLUGINS_DIR])
    additions.extend(["--exclude-tags", ",".join(tags)])
    result = without_option(arguments, "--exclude-tags")
    boundary = result.index("--") if "--" in result else len(result)
    return result[:boundary] + additions + result[boundary:]


def main():
    """替换为真实 AutoRecon 进程，保留信号、输出和退出状态。"""
    try:
        os.execv("/usr/bin/autorecon", ["autorecon"] + adapt(sys.argv[1:]))
    except (OSError, ValueError) as error:
        print(f"AutoRecon 兼容参数错误：{error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
