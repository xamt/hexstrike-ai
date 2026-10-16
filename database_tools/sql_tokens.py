"""保守SQL词法读取；不尝试修复或猜测方言歧义。"""
import re

from .policy_errors import OperationNotAllowed

WORD = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")


def tokenize_sql(query):
    """返回有界词元；拒绝执行注释、转义歧义和不支持的词法形式。"""
    if not isinstance(query, str) or not query or len(query) > 65536:
        raise OperationNotAllowed("SQL为空或超过策略长度上限")
    tokens, position = [], 0
    while position < len(query):
        if query[position] in " \t\r\n":
            position += 1
            continue
        end = _comment_end(query, position)
        if end is not None:
            position = end
            continue
        token, position = _token(query, position)
        tokens.append(token)
        if len(tokens) > 16384:
            raise OperationNotAllowed("SQL词元数量超过策略上限")
    return tokens


def _comment_end(query, start):
    if query.startswith("--", start):
        after = start + 2
        if after < len(query) and query[after] not in " \t\r\n":
            raise OperationNotAllowed("不支持有方言歧义的行注释")
        endings = [index for ending in ("\r", "\n")
                   if (index := query.find(ending, after)) >= 0]
        return min(endings) + 1 if endings else len(query)
    if not query.startswith("/*", start):
        return None
    end = query.find("*/", start + 2)
    body = query[start + 2:end] if end >= 0 else ""
    if end < 0 or "/*" in body or body.lstrip().upper().startswith(("!", "M!", "+")):
        raise OperationNotAllowed("不接受执行注释、提示注释、嵌套或未闭合注释")
    return end + 2


def _token(query, position):
    char = query[position]
    if char in "'\"`":
        return _quoted(query, position)
    for kind, pattern in (("word", WORD), ("number", NUMBER)):
        match = pattern.match(query, position)
        if match:
            return (kind, match[0].upper()), match.end()
    if char in "(),.;=<>!+-*/%|&~^":
        return ("symbol", char), position + 1
    raise OperationNotAllowed("SQL包含不支持的转义、控制字符或方言语法")


def _quoted(query, start):
    quote, position = query[start], start + 1
    while position < len(query):
        char = query[position]
        if char == "\\" or ord(char) < 32 or ord(char) == 127:
            raise OperationNotAllowed("SQL引号内容包含不支持的转义或控制字符")
        if char == quote:
            if position + 1 < len(query) and query[position + 1] == quote:
                position += 2
                continue
            kind = "string" if quote == "'" else "identifier"
            return (kind, query[start + 1:position]), position + 1
        position += 1
    raise OperationNotAllowed("SQL引号未闭合")
