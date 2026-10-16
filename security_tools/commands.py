"""从验证后的字段构造固定客户端 argv，不经 shell。"""


def build_command(name, args):
    """将有限结构化参数映射为实际安装的命令入口。"""
    if name == 'testssl_scan':
        return ['testssl', '--quiet', '--warnings', 'batch', '--color', '0', args['target']]
    if name == 'whatweb_scan':
        return ['whatweb', '--color=never', '--aggression=' + str(args['aggression']), args['target']]
    if name == 'jwt_tool_analyze':
        argv = ['jwt_tool', args['token']]
        if args['mode'] == 'scan':
            argv += ['-M', 'at', '-t', args['target_url'], '-rh',
                     'Authorization: Bearer ' + args['token'], '-np', '-nr']
        return argv
    if name == 'trufflehog_scan':
        argv = ['trufflehog', args['source'], '--json', '--no-update', '--concurrency=2',
                '--fail-on-scan-errors', '--no-verification-cache']
        if not args['verify']:
            argv.append('--no-verification')
        return argv + ['--', args['target']]
    argv = ['tcpdump', '-nn', '-l', '-c', str(args['count'])]
    argv += ['-r', args['read_file']] if args['mode'] == 'read' else ['-i', args['interface']]
    return argv + (['--', args['filter']] if args['filter'] else [])
