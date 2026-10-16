"""共享契约和严格请求校验；不开放任意命令行选项。"""
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

CONTRACTS = json.loads(Path(__file__).with_name('contracts.json').read_text(encoding='utf-8'))
REQUEST_LIMIT = 131072


def validate_request(name, payload):
    """返回带默认值的请求，拒绝未知字段、隐式类型转换和不支持的模式。"""
    if name not in CONTRACTS or type(payload) is not dict:
        raise ValueError('工具或请求对象无效')
    schema = CONTRACTS[name]['parameters']
    if payload.keys() - schema.keys():
        raise ValueError('请求包含不支持的字段')
    args = {}
    for key, rule in schema.items():
        if key not in payload and rule['required']:
            raise ValueError(f'缺少字段：{key}')
        value = payload.get(key, rule.get('default'))
        if type(value) is not {'str': str, 'int': int, 'bool': bool}[rule['type']]:
            raise ValueError(f'字段类型错误：{key}')
        if isinstance(value, str) and (len(value) > 32768 or any(ord(c) < 32 for c in value)):
            raise ValueError(f'字段包含控制字符或超出长度：{key}')
        args[key] = value
    _range(args, 'timeout', 1, 120 if name == 'tcpdump_capture' else 600)
    _range(args, 'max_output_bytes', 1024, 1048576)
    _validate_tool(name, args, payload)
    return args


def _range(args, field, low, high):
    if not low <= args[field] <= high:
        raise ValueError(f'{field} 必须在 {low} 至 {high} 之间')


def _url(value, schemes=('https', 'http')):
    try:
        parsed = urlsplit(value)
        port = parsed.port
        valid = (parsed.scheme in schemes and parsed.hostname and not parsed.username
                 and not parsed.password and not any(c.isspace() for c in value)
                 and len(value) <= 8192 and (port is None or port > 0))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('需要不包含凭据的有效目标 URL')


def _path(value):
    if not value.startswith('/') or len(value) > 4096:
        raise ValueError('文件路径必须是容器内的绝对路径')


def _validate_tool(name, args, payload):
    if name in ('testssl_scan', 'whatweb_scan'):
        _url(args['target'], ('https',) if name == 'testssl_scan' else ('http', 'https'))
        if name == 'whatweb_scan':
            _range(args, 'aggression', 1, 3)
    elif name == 'jwt_tool_analyze':
        _jwt(args)
    elif name == 'trufflehog_scan':
        _trufflehog(args)
    else:
        _tcpdump(args, payload)


def _jwt(args):
    if not re.fullmatch(r'[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*', args['token']):
        raise ValueError('token 必须为三段紧凑 JWT')
    if args['mode'] == 'scan':
        _url(args['target_url'])
    elif args['mode'] != 'decode' or args['target_url']:
        raise ValueError('mode 仅支持 decode 或 scan，decode 不接受 target_url')


def _trufflehog(args):
    if args['source'] == 'filesystem':
        _path(args['target'])
    elif args['source'] == 'git':
        if args['target'].startswith('file:///'):
            _path(args['target'][7:])
        else:
            _url(args['target'], ('https',))
    else:
        raise ValueError('source 仅支持 filesystem 或 git')


def _tcpdump(args, payload):
    _range(args, 'count', 1, 10000)
    if len(args['filter']) > 4096:
        raise ValueError('过滤器过长')
    if args['mode'] == 'read':
        _path(args['read_file'])
        if args['interface']:
            raise ValueError('read 模式不能指定 interface')
    elif args['mode'] == 'capture':
        if ('count' not in payload or not re.fullmatch(r'[A-Za-z0-9_.:@-]{1,64}', args['interface'])
                or args['interface'].startswith('-') or args['read_file']):
            raise ValueError('capture 需要 interface 和显式 count，不接受 read_file')
    else:
        raise ValueError('mode 仅支持 read 或 capture')
