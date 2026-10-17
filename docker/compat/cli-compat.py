#!/usr/local/bin/python3.11
"""只适配已确认的历史参数；真实工具仍保留原路径、版本和退出状态。"""
import os
import sys


def option_pairs(arguments, value_options):
    """将已知带值选项作为整体，避免把密码或文件名误认成其他开关。"""
    values = iter(arguments)
    for argument in values:
        if argument == "--":
            yield [argument, *values]
        elif argument in value_options:
            value = next(values, None)
            if value is None:
                raise ValueError(f"{argument} 缺少参数值")
            yield [argument, value]
        else:
            yield [argument]


def enum4linux(arguments):
    """转换旧类别列表；只在目标已经出现时识别旧 -d DOMAIN。"""
    result, target_seen = [], False
    values = list(option_pairs(arguments, {"-u", "-p", "-w", "-K", "-H", "-t", "-oA", "-oJ", "-oY"}))
    index = 0
    while index < len(values):
        group = values[index]
        following = values[index + 1] if index + 1 < len(values) else []
        if group == ["-A"] and target_seen and len(following) == 1 and set(following[0].split(",")) <= {"S", "U", "G", "P"}:
            result.extend("-" + category for category in dict.fromkeys(following[0].split(",")))
            index += 2
            continue
        if group == ["-d"] and target_seen and len(following) == 1 and not following[0].startswith("-"):
            result.extend(["-w", following[0]])
            index += 2
            continue
        result.extend(group)
        if len(group) == 1 and not group[0].startswith("-"):
            target_seen = True
        index += 1
    return result


def gobuster(arguments):
    """仅转换 DNS 模式的旧 -u；不将 URL 猜测成域名。"""
    if not arguments or arguments[0] != "dns":
        return list(arguments)
    result = ["dns"]
    for group in option_pairs(arguments[1:], {"-u", "--url", "-w", "--wordlist", "-r", "--resolver", "-o", "--output"}):
        if group[0] in ("-u", "--url"):
            if any(character in group[1] for character in "/:?#"):
                raise ValueError("Gobuster DNS 的 url 字段必须是域名，不能是带协议或路径的 URL")
            group[0] = "--domain"
        result.extend(group)
    return result


def checksec(arguments):
    """将旧的两个参数形式转为 Checksec 2.6 的 --file=PATH。"""
    result = []
    for group in option_pairs(arguments, {"--file"}):
        result.extend(["--file=" + group[1]] if group[0] == "--file" else group)
    return result


def go_flags(arguments, boolean_options):
    """把 Go 布尔开关移到唯一操作数前；拒绝会被上游静默忽略的输入。"""
    flags, operands, terminated = [], [], False
    for argument in arguments:
        if argument == "--" and not terminated:
            terminated = True
        elif not terminated and argument.startswith("-"):
            name = argument.lstrip("-").split("=", 1)[0]
            if name not in boolean_options | {"h", "help"}:
                raise ValueError(f"不支持的选项: {argument}")
            flags.append(argument)
        else:
            operands.append(argument)
    if len(operands) > 1:
        raise ValueError("此工具只接受一个域名或输出文件参数")
    return flags + (["--"] if terminated else []) + operands


def binwalk(arguments):
    """root 提取时默认降权运行第三方解包程序，保留显式 --run-as。"""
    result = list(arguments)
    options = []
    value_options = {"-D", "--dd", "-C", "--directory", "-d", "--depth", "-0", "--run-as",
                     "-f", "--log", "-m", "--magic", "-R", "--raw", "-l", "--length", "-o", "--offset"}
    for group in option_pairs(arguments, value_options):
        if group[0] == "--":
            break
        options.append(group[0])
    extraction = any(value in ("-e", "--extract", "-D", "--dd") or value.startswith("--dd=")
                     or (value.startswith("-") and not value.startswith("--") and "e" in value[1:])
                     for value in options)
    explicit_user = any(value in ("-0", "--run-as") or value.startswith(("--run-as=", "-0"))
                        for value in options)
    if extraction and os.geteuid() == 0 and not explicit_user:
        result.insert(0, "--run-as=pentest-tools-extract")
    return result


def ghidra(arguments):
    """补齐旧接口的 XML 导出脚本目录，保留调用方自定义脚本目录。"""
    if not arguments or any(value in ("-h", "--help", "-help") for value in arguments):
        return list(arguments)
    directory = "/opt/pentest-tools-compat/ghidra"
    result, found = [], False
    for group in option_pairs(arguments, {"-scriptPath"}):
        if group[0] == "-scriptPath":
            if found:
                raise ValueError("不能重复指定 -scriptPath")
            group[1] += ";" + directory
            found = True
        result.extend(group)
    return result if found else result + ["-scriptPath", directory]


def main():
    """按命令入口选择适配器，exec 保留信号、标准输入和退出状态。"""
    name = os.path.basename(sys.argv[0])
    transforms = {"enum4linux-ng": enum4linux, "gobuster": gobuster, "checksec": checksec,
                  "binwalk": binwalk, "analyzeHeadless": ghidra,
                  "waybackurls": lambda args: go_flags(args, {"dates", "get-versions", "no-subs"}),
                  "anew": lambda args: go_flags(args, {"q", "d", "t"})}
    try:
        if name not in transforms:
            raise ValueError(f"未知兼容入口: {name}")
        arguments = transforms[name](sys.argv[1:])
        directory = "/usr/local/bin" if name in ("waybackurls", "anew", "analyzeHeadless") else "/usr/bin"
        os.execv(f"{directory}/{name}", [name] + arguments)
        return 0
    except (OSError, ValueError) as error:
        print(f"{name} 参数适配失败: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
