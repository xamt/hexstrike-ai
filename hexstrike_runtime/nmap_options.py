"""Nmap 扫描类型的 HTTP/MCP 共用参数契约。"""

import re


def validate_scan_type(value):
    """拒绝语义名称、额外目标和 Shell 语法，保留无值的 Nmap 选项组合。"""
    if not isinstance(value, str) or re.search(r"[\r\n]", value) or any(
        not re.fullmatch(r"-{1,2}[A-Za-z][A-Za-z0-9_.=-]*", token)
        for token in value.split()
    ):
        raise ValueError(
            "scan_type 必须填写 Nmap 选项，例如 -sV、-sT -sV 或空字符串；"
            "不能填写 service_version 等名称或额外目标。需要独立参数值的选项放入 additional_args。"
        )
