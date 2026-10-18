import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, realpath, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHandler, tools } from '../external/plugin/servers/records.mjs';
import { validate } from '../external/plugin/servers/validate.mjs';

test('错误活动一次返回缺失与未知字段，修正后持久化且不影响版本', async () => {
  const root = await mkdtemp(join(await realpath(tmpdir()), 'activity-contract-'));
  try {
    const call = createHandler({ root });
    const created = await call('create_engagement', { title: '离线回归', targets: ['example.test'], scope: '仅合成数据' });
    const base = { task_id: created.task_id, expected_revision: 1 };
    const activity = { action: 'run', id: 'act-001', intent: '识别端口与服务',
      startTime: '2026-10-17T00:00:00+08:00', status: 'running',
      target: 'example.test', tool: 'mcp__plugin_pentest-tools_scanner__nmap_scan' };
    const bad = await call('record_progress', { ...base, activities: [activity] });
    assert.equal(bad.success, false);
    for (const key of ['startedAt', 'summary', 'evidenceRefs', 'action', 'intent', 'startTime']) {
      assert.ok(bad.error.message.includes(key), key);
    }
    assert.equal((await call('get_engagement_view', { task_id: base.task_id })).view.revision, 1);
    const { action, intent, startTime, ...rest } = activity;
    const fixed = { ...rest, startedAt: startTime, summary: intent, evidenceRefs: [] };
    assert.equal((await call('record_progress', { ...base, activities: [fixed] })).success, true);
    const view = (await call('get_engagement_view', { task_id: base.task_id })).view;
    assert.deepEqual(view.activities, [fixed]);
    const finished = { ...fixed, status: 'unknown', summary: '客户端超时，远端状态未知' };
    assert.equal((await call('record_progress', { ...base, expected_revision: 2, activities: [finished] })).success, true);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('运行时Schema直接解释活动字段，不依赖模型猜测字段别名', () => {
  const schema = tools.find(item => item.name === 'record_progress').inputSchema.properties.activities.items;
  assert.match(schema.properties.startedAt.description, /ISO|时间/);
  assert.match(schema.properties.summary.description, /意图|摘要/);
  assert.match(schema.properties.evidenceRefs.description, /空数组/);
});

test('技能中的活动示例与运行时输入Schema一致', async () => {
  const doc = await readFile(new URL('../external/skill/references/plugin-workbench.md', import.meta.url), 'utf8');
  const match = doc.match(/<!-- record-progress-example -->\s*```json\n([\s\S]*?)\n```/);
  assert.ok(match);
  const schema = tools.find(item => item.name === 'record_progress').inputSchema;
  assert.doesNotThrow(() => validate(JSON.parse(match[1]), schema));
});
