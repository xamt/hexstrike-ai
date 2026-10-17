import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, realpath, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Client } from '../plugins/pentest-tools/node_modules/@modelcontextprotocol/sdk/dist/esm/client/index.js';
import { StdioClientTransport } from '../plugins/pentest-tools/node_modules/@modelcontextprotocol/sdk/dist/esm/client/stdio.js';
import { createHandler } from '../plugins/pentest-tools/servers/records.mjs';
import { sampleView } from './fixtures/plugin-view.mjs';

const plugin = new URL('../plugins/pentest-tools/', import.meta.url);

/** 按发布配置解析记录目录，两个客户端有不同的项目工作目录。 */
async function connect(cwd, recordsRoot) {
  const config = JSON.parse(await readFile(new URL('.mcp.json', plugin), 'utf8'));
  const template = config.mcpServers.records.env.PENTEST_RECORDS_ROOT;
  const root = template.replaceAll('${user_config.records_root}', recordsRoot)
    .replaceAll('${DATAAGENT_PROJECT_DIR}', cwd);
  const client = new Client({ name: 'offline-context-test', version: '1.0.0' });
  const transport = new StdioClientTransport({ command: process.execPath, cwd,
    args: [fileURLToPath(new URL('dist/records.cjs', plugin))],
    env: { PENTEST_RECORDS_ROOT: root }, stderr: 'pipe' });
  try { await client.connect(transport); } catch (error) { await client.close(); throw error; }
  return { close: () => client.close(), call: async (name, args) => {
    const result = await client.callTool({ name, arguments: args });
    assert.equal(result.isError, false, JSON.stringify(result.structuredContent));
    return result.structuredContent;
  } };
}

/** 合成数据写入后，从另一真实stdio客户端读取进度及最终报告。 */
async function verifySharedRecords(writer, reader) {
  const fixture = sampleView();
  const created = await writer.call('create_engagement', {
    title: fixture.title, targets: fixture.targets, scope: fixture.scope,
  });
  const task = { task_id: created.task_id };
  const { assets, findings, activities, attackChains, report } = fixture;
  await writer.call('record_progress', { ...task, expected_revision: 1,
    status: 'running', assets, findings, activities, attackChains });
  assert.equal((await writer.call('open_engagement', task)).task_id, task.task_id);
  const progress = await reader.call('get_engagement_view', task);
  assert.equal(progress.view.revision, 2);
  assert.deepEqual(progress.view.assets, assets);
  assert.deepEqual(progress.view.findings, findings);
  await writer.call('record_progress', { ...task, expected_revision: 2, status: 'completed', report });
  const final = await reader.call('get_engagement_view', task);
  assert.equal(final.view.revision, 3);
  assert.equal(final.view.status, 'completed');
  assert.deepEqual(final.view.report, report);
  assert.deepEqual(final.view.attackChains, attackChains);
  return task;
}

test('智能体与面板跨工作目录和进程重启仍读取同一任务的进度与报告', async () => {
  const directory = await mkdtemp(join(await realpath(tmpdir()), 'records-context-'));
  const clients = [];
  try {
    const a = join(directory, '智能体工作区');
    const b = join(directory, '面板 host');
    const recordsRoot = join(directory, '共享记录 pentest-records');
    await mkdir(a); await mkdir(b);
    const writer = await connect(a, recordsRoot); clients.push(writer);
    const reader = await connect(b, recordsRoot); clients.push(reader);
    const task = await verifySharedRecords(writer, reader);
    const restarted = await connect(b, recordsRoot); clients.push(restarted);
    assert.equal((await restarted.call('get_engagement_view', task)).view.revision, 3);
  } finally {
    await Promise.all(clients.map(client => client.close()));
    await rm(directory, { recursive: true, force: true });
  }
});

test('错误目录返回任务和当前根目录诊断，不新建目录或伪造空成功', async () => {
  const directory = await mkdtemp(join(await realpath(tmpdir()), 'records-missing-'));
  try {
    const root = join(directory, '未配置到正确位置');
    const taskId = '00000000-0000-4000-8000-000000000001';
    const result = await createHandler({ root })('get_engagement_view', { task_id: taskId });
    assert.equal(result.success, false);
    assert.equal(result.error.code, 'NOT_FOUND');
    assert.ok(result.error.message.includes(root));
    assert.ok(result.error.message.includes(taskId));
    await assert.rejects(realpath(root), { code: 'ENOENT' });
  } finally { await rm(directory, { recursive: true, force: true }); }
});
