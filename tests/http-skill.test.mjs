import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createClient } from '../skills/pentest-tools/scripts/http-client.mjs';
import { validateArguments } from '../skills/pentest-tools/scripts/catalog.mjs';
import { createTools } from '../skills/pentest-tools/scripts/generated-tools.mjs';
import { localIso } from '../skills/pentest-tools/scripts/python-values.mjs';

const cli = new URL('../skills/pentest-tools/scripts/run.mjs', import.meta.url);

test('HTTP 参数和请求方法保留；特殊字符不进入 shell', async () => {
  const captured = [];
  const client = createClient({ server: 'http://offline.invalid/prefix/', fetchImpl: async (url, options) => {
    captured.push([url, options]);
    return new Response(JSON.stringify({ success: true }), { status: 200 });
  } });
  await client.safe_get('api/files/list', { directory: '/tmp/a &b?中' });
  await client.safe_post('api/command', { command: 'echo "$(not-executed)"', use_cache: false });
  assert.equal(captured[0][0].pathname, '/prefix/api/files/list');
  assert.equal(captured[0][0].searchParams.get('directory'), '/tmp/a &b?中');
  assert.equal(captured[0][1].method, 'GET');
  assert.equal(captured[1][1].method, 'POST');
  assert.deepEqual(JSON.parse(captured[1][1].body), { command: 'echo "$(not-executed)"', use_cache: false });
  assert.equal(captured[1][1].redirect, 'manual');
});

test('HTTP 错误、重定向、非 JSON、无效响应和断连不重试', async () => {
  for (const response of [() => new Response('{}', { status: 500 }),
    () => new Response('', { status: 302 }), () => new Response('not-json'),
    () => new Response('[]'), () => { throw new Error('连接断开'); }]) {
    let count = 0;
    const client = createClient({ fetchImpl: async () => { count++; return response(); } });
    const result = await client.safe_post('api/tools/example', {});
    assert.equal(result.success, false);
    assert.ok(result.error);
    assert.equal(count, 1);
    assert.equal(client.failures.length, 1);
  }
});

test('超时中止等待，但不声称取消了后台任务', async () => {
  let count = 0;
  const client = createClient({ timeout: 0.01, fetchImpl: async (_url, { signal }) => {
    count++;
    return new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new Error('中止'))));
  } });
  const result = await client.safe_get('api/processes/list');
  assert.match(result.error, /后台任务可能仍在运行/);
  assert.equal(count, 1);
});

test('业务失败不篡改响应；组合工具保留原聚合但记录子请求失败', async () => {
  const payload = { success: false, error: '工具缺失', detail: { code: 7 } };
  const client = createClient({ fetchImpl: async () => new Response(JSON.stringify(payload)) });
  assert.deepEqual(await client.check_health(), payload);
  const result = await createTools(client).ai_generate_attack_suite('offline.example', 'xss');
  assert.equal(result.success, true);
  assert.equal(client.failures.length, 2);
});

test('非 2xx 数据库错误保留结构化诊断并强制失败，不重试', async () => {
  let calls = 0;
  const body = { success: false, error: '客户端缺失', error_code: 'tool_missing', stderr: '' };
  const client = createClient({ fetchImpl: async () => {
    calls++;
    return new Response(JSON.stringify(body), { status: 503 });
  } });
  assert.deepEqual(await client.safe_post('api/tools/mysql', {}), { ...body, http_status: 503 });
  assert.equal(calls, 1);
  assert.equal(client.failures.length, 1);
});

test('五类数据库入口保留参数、默认值和服务端结果，不转为 shell 命令', async () => {
  const cases = [
    ['mysql_query', 'mysql', { host: 'db.example.test', query: 'SELECT 1' }, 3306],
    ['clickhouse_query', 'clickhouse', { host: 'db.example.test', query: 'SELECT 1' }, 9000],
    ['redis_command', 'redis', { host: 'db.example.test', command: ['PING'] }, 6379],
    ['postgresql_query', 'postgresql', { host: 'db.example.test', query: 'SELECT 1' }, 5432],
    ['mongodb_command', 'mongodb', { host: 'db.example.test', command: { ping: 1 } }, 27017],
  ];
  for (const [name, route, params, port] of cases) {
    const response = { success: false, timed_out: true, truncated: false };
    const client = createClient({ fetchImpl: async (url, options) => {
      assert.equal(url.pathname, `/api/tools/${route}`);
      assert.equal(options.method, 'POST');
      const data = JSON.parse(options.body);
      for (const [key, value] of Object.entries(params)) assert.deepEqual(data[key], value);
      assert.equal(data.port, port);
      assert.equal(data.timeout, 30);
      assert.equal(data.max_output_bytes, 65536);
      assert.equal(data.password, '"$(never-run);中文');
      return new Response(JSON.stringify(response));
    } });
    const args = validateArguments(name, { ...params, password: '"$(never-run);中文' });
    assert.deepEqual(await createTools(client)[name](...args), response);
    assert.equal(client.failures.length, 1);
  }
});

test('参数名、类型、必填、默认 null 与服务地址校验', () => {
  assert.throws(() => validateArguments('unknown', {}), /未知工具/);
  assert.throws(() => validateArguments('nmap_scan', {}), /缺少参数/);
  assert.throws(() => validateArguments('nmap_scan', { target: 'x', typo: 1 }), /未知参数/);
  assert.throws(() => validateArguments('httpx_probe', { target: 'x', probe: 'false' }), /必须为 bool/);
  assert.doesNotThrow(() => validateArguments('http_intruder', { url: 'x', params: null }));
  assert.throws(() => createClient({ server: 'file:///tmp/test' }));
  assert.throws(() => createClient({ server: 'https://user:pass@offline.invalid' }));
  assert.throws(() => createClient({ timeout: 0 }));
});

test('CLI 发现和说明完全离线；错误输入不连接真实服务', () => {
  const run = args => spawnSync(process.execPath, [cli.pathname, ...args], { encoding: 'utf8', env: { ...process.env, PENTEST_SERVER_URL: 'invalid' } });
  const list = run(['list']);
  assert.equal(list.status, 0, list.stderr);
  assert.equal(JSON.parse(list.stdout).length, 156);
  const describe = run(['describe', 'nmap_scan']);
  assert.equal(describe.status, 0);
  assert.equal(JSON.parse(describe.stdout).parameters.scan_type.default, '-sV');
  const invalid = run(['call', 'nmap_scan']);
  assert.equal(invalid.status, 1);
  assert.match(invalid.stderr, /缺少参数/);
});

test('CLI 无效 JSON 不在错误信息中回显数据库凭据', () => {
  const result = spawnSync(process.execPath, [cli.pathname, 'call', 'mysql_query', '--input', '-'], {
    encoding: 'utf8', input: '{"password":"offline-sensitive-value", broken}',
  });
  assert.equal(result.status, 1);
  assert.doesNotMatch(result.stderr, /offline-sensitive-value/);
  assert.match(result.stderr, /参数输入不是有效 JSON/);
});

test('复合工具前两步成功、最后一步失败时 CLI 退出 1', () => {
  const preload = new URL('./skill-mock-fetch.mjs', import.meta.url);
  const result = spawnSync(process.execPath, ['--import', preload.href, cli.pathname,
    'call', 'ai_reconnaissance_workflow', '--input', '-', '--server', 'http://offline.invalid'], {
    encoding: 'utf8', input: JSON.stringify({ target: 'offline.example', depth: 'deep' }),
    env: { ...process.env, SKILL_MOCK_REPLIES: JSON.stringify([
      { success: true, target_profile: { target: 'offline.example' } },
      { success: true, attack_chain: { steps: [] } }, { success: false, error: '模拟失败' },
    ]) },
  });
  assert.equal(result.status, 1);
  assert.equal(JSON.parse(result.stdout).success, true);
  assert.match(result.stderr, /部分请求失败/);
});

test('复合工具早期失败不会继续发出请求', async () => {
  let count = 0;
  const client = createClient({ fetchImpl: async () => {
    count++;
    return new Response(JSON.stringify({ success: false, error: '模拟失败' }));
  } });
  const result = await createTools(client).ai_reconnaissance_workflow('offline.example');
  assert.equal(result.success, false);
  assert.equal(count, 1);
});

test('本地时间戳保持原 ISO 格式，不变成 UTC Z', () => {
  assert.equal(localIso(new Date(2025, 0, 2, 3, 4, 5, 123)), '2025-01-02T03:04:05.123000');
  assert.equal(localIso(new Date(2025, 0, 2, 3, 4, 5, 0)), '2025-01-02T03:04:05');
});
