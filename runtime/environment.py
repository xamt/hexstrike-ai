"""产品环境配置；仅此处保留旧部署变量的兼容入口。"""
import os


def setting(name, default, environ=None):
    """优先读取 PENTEST_TOOLS_*，缺失时读取旧变量，不覆盖显式空值。"""
    values = os.environ if environ is None else environ
    key = "PENTEST_TOOLS_" + name
    if key in values:
        return values[key]
    return values.get("HEXSTRIKE_" + name, default)
