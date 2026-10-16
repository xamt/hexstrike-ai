import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createTools } from '../skills/pentest-tools/scripts/generated-tools.mjs';
import { catalog, validateArguments } from '../skills/pentest-tools/scripts/catalog.mjs';

const samples = [
  ['testssl_scan', 'testssl', { target: 'https://app.example.test' }],
  ['whatweb_scan', 'whatweb', { target: 'https://app.example.test' }],
  ['jwt_tool_analyze', 'jwt-tool', { token: 'eyJhbGciOiJIUzI1NiJ9.e30.signature' }],
  ['trufflehog_scan', 'trufflehog', { target: '/evidence/source' }],
  ['tcpdump_capture', 'tcpdump', { read_file: '/evidence/traffic.pcap' }],
];

test('五工具向对应HTTP路由发送完整默认契约，不执行本地工具', async () => {
  const calls = [];
  const tools = createTools({
    async safe_post(path, data) {
      calls.push({ path, data });
      return { success: true, stdout: '模拟输出' };
    },
  });
  for (const [name, route, args] of samples) {
    const values = validateArguments(name, args);
    assert.deepEqual(await tools[name](...values), { success: true, stdout: '模拟输出' });
    const { path, data } = calls.at(-1);
    assert.equal(path, `api/tools/${route}`);
    for (const [key, param] of Object.entries(catalog[name].parameters)) {
      assert.deepEqual(data[key], Object.hasOwn(args, key) ? args[key] : param.default);
    }
  }
  assert.equal(calls[2].data.mode, 'decode');
  assert.equal(calls[3].data.verify, false);
  assert.equal(calls[4].data.mode, 'read');
});

test('五工具拒绝未知选项，保持服务端错误与不完整标记', async () => {
  const failure = { success: false, error_code: 'output_limit', truncated: true };
  const tools = createTools({ async safe_post() { return failure; } });
  for (const [name, , args] of samples) {
    assert.throws(() => validateArguments(name, { ...args, additional_args: '-x' }), /未知参数/);
    assert.throws(() => validateArguments(name, { ...args, timeout: true }), /必须为 int/);
    assert.deepEqual(await tools[name](...validateArguments(name, args)), failure);
  }
});
