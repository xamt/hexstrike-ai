import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, realpath, readdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Client } from '../external/plugin/node_modules/@modelcontextprotocol/sdk/dist/esm/client/index.js';
import { StdioClientTransport } from '../external/plugin/node_modules/@modelcontextprotocol/sdk/dist/esm/client/stdio.js';
import { verifyWorkflowProtocol } from './fixtures/plugin-workflow-protocol.mjs';

async function verifyActivityContract(call, task) {
  const wrong = { id: 'act-001', tool: 'nmap_scan', target: 'example.test', status: 'running',
    action: 'run', intent: '离线测试', startTime: '2026-10-17T09:00:00+08:00' };
  const bad = await call('record_progress', { ...task, expected_revision: 1, activities: [wrong] });
  assert.equal(bad.isError, true);
  for (const key of ['startedAt', 'summary', 'evidenceRefs', 'startTime', 'intent', 'action']) {
    assert.ok(bad.structuredContent.error.message.includes(key), key);
  }
  assert.equal((await call('get_engagement_view', task)).structuredContent.view.revision, 1);
  const { action, intent, startTime, ...base } = wrong;
  const fixed = { ...base, startedAt: startTime, summary: intent, evidenceRefs: [] };
  const saved = await call('record_progress', { ...task, expected_revision: 1, activities: [fixed] });
  assert.equal(saved.isError, false);
  assert.deepEqual((await call('get_engagement_view', task)).structuredContent.view.activities, [fixed]);
}

async function verifyEarlyWorkbench(call, root) {
  const first = await call('open_workbench', {});
  const second = await call('open_workbench', {});
  assert.equal(first.isError, false);
  assert.notEqual(first.structuredContent.runId, second.structuredContent.runId);
  assert.equal(first.structuredContent.task_id, undefined);
  assert.deepEqual(first._meta['dataagent/panelEvents'].map(event => event.type), ['panel.open']);
  assert.deepEqual(first.structuredContent.dataagentPanelEvents, first._meta['dataagent/panelEvents']);
  assert.deepEqual(JSON.parse(first.content[1].text), first._meta['dataagent/panelEvents'][0]);
  assert.deepEqual(await readdir(root), [], '仅打开空工作台不能创建任务记录');
  const bad = await call('open_workbench', { task_id: '不应接受' });
  assert.equal(bad.isError, true);
  assert.equal(bad._meta, undefined);
}

test('真实 stdio 协商、任务记录、面板事件与导出仅操作临时目录', async () => {
  const root = await realpath(await mkdtemp(join(tmpdir(), 'pentest-plugin-protocol-')));
  const client = new Client({ name: 'offline-test', version: '1.0.0' });
  const transport = new StdioClientTransport({ command: process.execPath,
    args: [process.env.PENTEST_PLUGIN_ENTRY || fileURLToPath(new URL('../external/plugin/dist/records.cjs', import.meta.url))],
    env: { PENTEST_RECORDS_ROOT: root }, stderr: 'pipe' });
  let errors = '';
  transport.stderr?.on('data', chunk => { errors += chunk; });
  try {
    await client.connect(transport);
    const { tools } = await client.listTools();
    assert.equal(tools.length, 6);
    assert.equal(tools.find(item => item.name === 'get_engagement_view').annotations.readOnlyHint, true);
    assert.equal(tools.find(item => item.name === 'open_workbench').annotations.readOnlyHint, true);
    for (const name of ['create_engagement', 'record_progress', 'export_report']) {
      assert.equal(tools.find(item => item.name === name).annotations.readOnlyHint, false);
    }
    const call = (name, args) => client.callTool({ name, arguments: args });
    await verifyEarlyWorkbench(call, root);
    const rejected = await call('create_engagement', { title: '长'.repeat(161),
      targets: ['example.test'], scope: '仅测试' });
    assert.equal(rejected.isError, true);
    assert.equal(rejected._meta, undefined);
    const initial = await call('create_engagement', { title: '离线契约验证',
      targets: ['example.test'], scope: '合成数据，无实际网络请求' });
    const created = initial.structuredContent;
    assert.equal(created.success, true);
    assert.deepEqual(initial._meta?.['dataagent/panelEvents'].map(event => event.type), ['panel.open', 'data.updated']);
    assert.equal(initial._meta['dataagent/panelEvents'][1].data.taskId, created.task_id);
    assert.equal(initial._meta['dataagent/panelEvents'][0].runId, created.runId);
    assert.deepEqual(initial.structuredContent.dataagentPanelEvents, initial._meta['dataagent/panelEvents']);
    assert.deepEqual(initial.content.slice(1).map(item => JSON.parse(item.text)), initial._meta['dataagent/panelEvents']);
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
    assert.equal(view.phase, '制定测试计划');
    assert.equal(view.plan, '');
    assert.equal(view.preflight, undefined);
    const exported = await call('export_report', { ...task, expected_revision: 1 });
    assert.equal(exported.isError, false);
    const bad = await call('record_progress', { ...task, expected_revision: 0, phase: '错误版本' });
    assert.equal(bad.isError, true);
    assert.equal(bad.structuredContent.success, false);
    await verifyActivityContract(call, task);
    await verifyPlanEvents(call);
    await verifyWorkflowProtocol(call);
    assert.equal(errors, '');
  } finally {
    await client.close();
    await rm(root, { recursive: true, force: true });
  }
});

async function verifyPlanEvents(call) {
  const created = await call('create_engagement', { title: '先计划后测试', targets: ['example.test'],
    scope: '离线合成数据', plan: '阶段一：核对范围\n阶段二：验证疑点' });
  assert.equal(created.isError, false);
  const saved = created.structuredContent;
  const events = created._meta['dataagent/panelEvents'];
  assert.deepEqual(events.map(item => item.type), ['panel.open', 'data.updated']);
  assert.equal(events[1].data.taskId, saved.task_id);
  assert.equal(events[0].runId, saved.runId);
  assert.equal(events[0].panelId, saved.panelId);
  assert.equal(saved.title, '先计划后测试');
  assert.ok(saved.task_path && saved.record_path);
  const task = { task_id: saved.task_id };
  const view = (await call('get_engagement_view', task)).structuredContent.view;
  assert.equal(view.plan, '阶段一：核对范围\n阶段二：验证疑点');
  assert.equal(view.status, 'planned');
  assert.deepEqual(view.activities, []);
  const update = await call('record_progress', { ...task, expected_revision: 1, plan: '调整计划，仅整理证据' });
  assert.equal(update.structuredContent.revision, 2);
  assert.equal(update.structuredContent.task_path, saved.task_path);
  assert.notEqual(update.structuredContent.record_path, saved.record_path);
  assert.notEqual(update.structuredContent.runId, saved.runId);
  assert.equal(update._meta['dataagent/panelEvents'][1].data.taskId, saved.task_id);
  const stale = await call('record_progress', { ...task, expected_revision: 1, plan: '旧版本' });
  assert.equal(stale.isError, true);
  assert.equal(stale._meta, undefined);
  const normal = await call('record_progress', { ...task, expected_revision: 2, phase: '计划讨论' });
  assert.equal(normal.isError, false);
  assert.equal(normal._meta, undefined);
  const blank = await call('create_engagement', { title: '空计划', targets: ['example.test'], scope: '离线', plan: ' ' });
  assert.equal(blank.isError, false);
  assert.equal(blank._meta['dataagent/panelEvents'][0].type, 'panel.open');
  const bad = await call('record_progress', { ...task, expected_revision: 3, plan: 123 });
  assert.equal(bad.isError, true);
  assert.equal(bad._meta, undefined);
}
