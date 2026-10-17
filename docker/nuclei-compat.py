#!/usr/local/bin/python3.11
"""使用本地模板完成原 Nuclei 调用，不在扫描时下载或更新模板。"""
import glob
import os
from pathlib import Path
import sys

TEMPLATE_OPTIONS = {"t", "templates", "w", "workflows"}
UPDATE_OPTIONS = {"up", "update", "ut", "update-templates", "ud", "update-template-dir"}
REMOTE_OPTIONS = {"tu", "template-url", "wu", "workflow-url"}


def local_templates(value, directory=None):
    """确认本地模板存在且可读；模板内容是否合法由原生引擎验证。"""
    path = Path(value)
    if "://" in value:
        raise ValueError(f"离线模板路径不存在或不是本地路径: {value}")
    if not path.is_absolute() and not path.exists() and directory:
        path = Path(directory) / path
    matches = [path] if path.exists() else (Path(item) for item in glob.iglob(str(path), recursive=True))
    for match in matches:
        candidates = [match] if match.is_file() else match.rglob("*")
        for candidate in candidates:
            if candidate.suffix.lower() in (".yaml", ".yml") and candidate.is_file():
                with candidate.open("rb") as handle:
                    if handle.read(1):
                        return
    raise ValueError(f"未找到非空 YAML 模板，请挂载完整模板目录: {value}")


def template_arguments(arguments, directory):
    """保留显式本地模板选择，默认指向挂载目录，拒绝在线更新入口。"""
    explicit = False
    values = iter(arguments)
    for argument in values:
        name, separator, value = argument.lstrip("-").partition("=")
        if not argument.startswith("-"):
            continue
        if name in UPDATE_OPTIONS | REMOTE_OPTIONS:
            raise ValueError("离线入口不下载或更新模板；请在联网环境准备模板后重新挂载")
        if name in TEMPLATE_OPTIONS:
            value = value if separator else next(values, "")
            if not value or value.startswith("-"):
                raise ValueError(f"{argument} 缺少本地模板路径")
            for path in value.split(","):
                local_templates(path, directory)
            explicit = True
    if explicit:
        return list(arguments)
    local_templates(directory)
    return [*arguments, "-t", directory]


def main(arguments=None):
    """替换为原生进程，保留输出、信号和退出状态，不把缺失模板当成功。"""
    arguments = list(sys.argv[1:] if arguments is None else arguments)
    environment = os.environ.copy()
    directory = environment.get("NUCLEI_TEMPLATES_DIR", "/opt/nuclei-templates")
    environment["NUCLEI_TEMPLATES_DIR"] = directory
    for provider in ("PUBLIC", "GITHUB", "GITLAB", "AWS", "AZURE"):
        environment[f"DISABLE_NUCLEI_TEMPLATES_{provider}_DOWNLOAD"] = "true"
    try:
        informational = len(arguments) == 1 and arguments[0] in (
            "-h", "--help", "-help", "-version", "--version")
        if not informational:
            arguments = template_arguments(arguments, directory)
            # 无外部回连服务时不运行 OAST 模板；其他模板仍会访问其指定目标。
            arguments += ["-ni"]
        arguments += ["-duc"]
        os.execve("/usr/bin/nuclei", ["nuclei", *arguments], environment)
        return 0
    except (OSError, ValueError) as error:
        print(f"Nuclei 离线模板入口失败: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
