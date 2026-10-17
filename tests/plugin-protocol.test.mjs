import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, realpath } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Client } from '../plugins/pentest-tools/node_modules/@modelcontextprotocol/sdk/dist/esm/client/index.js';
import { StdioClientTransport } from '../plugins/pentest-tools/node_modules/@modelcontextprotocol/sdk/dist/esm/client/stdio.js';

test('真实 stdio 协商、任务记录、面板事件与导出仅操作临时目录', async () => {
  const root = await realpath(await mkdtemp(join(tmpdir(), 'pentest-plugin-protocol-')));
  const client = new Client({ name: 'offline-test', version: '1.0.0' });
  const transport = new StdioClientTransport({ command: process.execPath,
    args: [process.env.PENTEST_PLUGIN_ENTRY || fileURLToPath(new URL('../plugins/pentest-tools/dist/records.cjs', import.meta.url))],
    env: { PENTEST_RECORDS_ROOT: root }, stderr: 'pipe' });
  let errors = '';
  transport.stderr?.on('data', chunk => { errors += chunk; });
  try {
    await client.connect(transport);
    const { tools } = await client.listTools();
    assert.equal(tools.length, 5);
    assert.equal(tools.find(item => item.name === 'get_engagement_view').annotations.readOnlyHint, true);
    for (const name of ['create_engagement', 'record_progress', 'export_report']) {
      assert.equal(tools.find(item => item.name === name).annotations.readOnlyHint, false);
    }
    const call = (name, args) => client.callTool({ name, arguments: args });
    assert.equal((await call('create_engagement', { title: '长'.repeat(161),
      targets: ['example.test'], scope: '仅测试' })).isError, true);
    const created = (await call('create_engagement', { title: '离线契约验证',
      targets: ['example.test'], scope: '合成数据，无实际网络请求' })).structuredContent;
    assert.equal(created.success, true);
    const task = { task_id: created.task_id };
    const first = await call('open_engagement', task);
    const second = await call('open_engagement', task);
    assert.notEqual(first.structuredContent.runId, second.structuredContent.runId);
    const events = first._meta['dataagent/panelEvents'];
    assert.deepEqual(events.map(item => item.type), ['panel.open', 'data.updated']);
    assert.equal(events[1].data.taskId, created.task_id);
    assert.equal(events[0].pluginId, 'pentest-tools');
    const view = (await call('get_engagement_view', task)).structuredContent.view;
    assert.equal(view.revision, 1);
    assert.deepEqual(view.assets, []);
    const exported = await call('export_report', { ...task, expected_revision: 1 });
    assert.equal(exported.isError, false);
    const bad = await call('record_progress', { ...task, expected_revision: 0, phase: '错误版本' });
    assert.equal(bad.isError, true);
    assert.equal(bad.structuredContent.success, false);
    assert.equal(errors, '');
  } finally {
    await client.close();
    await rm(root, { recursive: true, force: true });
  }
});
