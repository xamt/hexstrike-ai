import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createTools } from '../skills/pentest-tools/scripts/generated-tools.mjs';
import { catalog, validateArguments } from '../skills/pentest-tools/scripts/catalog.mjs';

const cases = JSON.parse(readFileSync(0, 'utf8'));
for (const sample of cases) {
  const calls = [];
  const client = {
    async safe_post(path, data) { calls.push(['POST', path, structuredClone(data)]); return structuredClone(sample.response); },
    async safe_get(path, params = {}) { calls.push(['GET', path, params]); return structuredClone(sample.response); },
    async check_health() { return this.safe_get('health'); },
    async execute_command(command, use_cache) { return this.safe_post('api/command', { command, use_cache }); },
  };
  const tools = createTools(client, { seconds: () => 1700000000, iso: () => '2023-11-14T22:13:20' });
  validateArguments(sample.name, sample.args);
  const args = Object.keys(catalog[sample.name].parameters).map(key => sample.args[key]);
  const actual = await tools[sample.name](...args);
  assert.deepEqual(calls, sample.calls, `${sample.name}: 请求不一致`);
  assert.deepEqual(actual, sample.expected, `${sample.name}: 返回不一致`);
}
process.stdout.write(JSON.stringify({ checked: cases.length }));
