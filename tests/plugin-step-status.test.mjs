import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, realpath, rm, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHandler } from '../plugins/pentest-tools/servers/records.mjs';

const step = (id, status = 'pending', summary = '') => ({ id, title: `测试步骤 ${id}`, status, summary, evidenceRefs: [] });
const health = status => ({ status, checkedAt: new Date().toISOString(), server: 'plugin:pentest-tools:hexstrike',
  tool: 'mcp__plugin_pentest-tools_hexstrike__server_health', summary: status === 'passed' ? '合成正常响应' : '合成连接超时' });

async function fixture(t) {
  const root = await mkdtemp(join(await realpath(tmpdir()), 'plugin-steps-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const call = createHandler({ root });
  const created = await call('create_engagement', { title: '离线计划状态', targets: ['example.test'], scope: '仅合成数据',
    plan: '按范围低影响测试', planSteps: [step('s1'), step('s2')] });
  assert.equal(created.success, true, JSON.stringify(created));
  return { call, created, task: { task_id: created.task_id } };
}

test('步骤按ID合并，检查前不开始，通过后四状态更新且保留历史', async t => {
  const { call, task, created } = await fixture(t);
  const run = { ...task, expected_revision: 1, planSteps: [step('s1', 'running', '开始验证')] };
  assert.equal((await call('record_progress', run)).error.code, 'PREFLIGHT_REQUIRED');
  assert.equal((await call('record_progress', { ...run, preflight: health('passed') })).success, true);
  let view = (await call('get_engagement_view', task)).view;
  assert.equal(view.status, 'running', '步骤开始后任务不能仍显示待开始');
  assert.deepEqual(view.planSteps.map(s => s.status), ['running', 'pending']);
  assert.equal(JSON.parse(await readFile(created.record_path, 'utf8')).planSteps[0].status, 'pending');
  assert.equal((await call('record_progress', { ...task, expected_revision: 2,
    planSteps: [step('s1', 'completed', '完成对照验证'), step('s2', 'blocked', '缺少账号')] })).success, true);
  view = (await call('get_engagement_view', task)).view;
  assert.deepEqual(view.planSteps.map(s => s.status), ['completed', 'blocked']);
  assert.equal((await call('record_progress', { ...task, expected_revision: 3, status: 'completed' })).success, false);
  assert.equal((await call('record_progress', { ...task, expected_revision: 2, planSteps: [step('s2')] })).error.code, 'REVISION_CONFLICT');
  assert.equal((await call('record_progress', { ...task, expected_revision: 3, status: 'completed',
    planSteps: [step('s2', 'completed', '已补齐范围内验证与报告')] })).success, true);
  assert.equal((await call('get_engagement_view', task)).view.status, 'completed');
});

test('健康检查失败暂停任务和执行中步骤，不宣称停止远端进程，恢复需重新通过', async t => {
  const { call, task } = await fixture(t);
  await call('record_progress', { ...task, expected_revision: 1, preflight: health('passed'), status: 'running',
    planSteps: [step('s1', 'running', '验证中')], activities: [{ id: 'a1', planStepId: 's1', tool: 'synthetic_tool',
      target: 'example.test', status: 'running', startedAt: new Date().toISOString(), summary: '合成活动', evidenceRefs: [] }] });
  assert.equal((await call('record_progress', { ...task, expected_revision: 2, preflight: health('failed') })).success, true);
  let view = (await call('get_engagement_view', task)).view;
  assert.equal(view.status, 'paused');
  assert.equal(view.planSteps[0].status, 'blocked');
  assert.match(view.planSteps[0].summary, /连接超时/);
  assert.equal(view.planSteps[1].status, 'pending');
  assert.equal(view.activities[0].status, 'unknown');
  assert.equal(view.activities[0].finishedAt, undefined);
  const resume = { ...task, expected_revision: 3, status: 'running', planSteps: [step('s1', 'running', '恢复验证')] };
  assert.equal((await call('record_progress', resume)).error.code, 'PREFLIGHT_REQUIRED');
  assert.equal((await call('record_progress', { ...resume, preflight: health('passed') })).success, true);
  view = (await call('get_engagement_view', task)).view;
  assert.equal(view.status, 'running');
});

test('文档的新建计划与失败检查示例可执行，最大长度失败原因仍可保存', async t => {
  const { call, task } = await fixture(t);
  const readme = await readFile(new URL('../plugins/pentest-tools/README.md', import.meta.url), 'utf8');
  const createArgs = JSON.parse(readme.match(/```json\n([\s\S]*?)\n```/)[1]);
  assert.equal((await call('create_engagement', createArgs)).success, true);
  const workflow = await readFile(new URL('../skills/pentest-tools/references/plugin-workbench.md', import.meta.url), 'utf8');
  const example = JSON.parse(workflow.match(/<!-- preflight-example -->\s*```json\n([\s\S]*?)\n```/)[1]);
  assert.equal((await call('record_progress', { ...example, ...task })).success, true);
  const started = await call('record_progress', { ...task, expected_revision: 2, preflight: health('passed'),
    planSteps: [step('s1', 'running', '合成执行')] });
  assert.equal(started.success, true);
  assert.equal((await call('record_progress', { ...task, expected_revision: 3,
    preflight: { ...health('failed'), summary: '错'.repeat(4000) } })).success, true);
});

test('拒绝重复步骤、未知状态、空完成或受阻原因及不存在的步骤引用', async t => {
  const { call, task } = await fixture(t);
  const activity = { id: 'a1', tool: 'synthetic_tool', target: 'example.test', status: 'running',
    startedAt: new Date().toISOString(), summary: '合成执行', evidenceRefs: [], planStepId: 'missing' };
  for (const patch of [
    { planSteps: [step('s1'), step('s1')] }, { planSteps: [step('s1', 'done')] },
    { planSteps: [step('s1', 'completed')] }, { planSteps: [step('s1', 'blocked', ' ')] },
    { activities: [activity] }, { preflight: { ...health('passed'), summary: '' } },
  ]) {
    assert.equal((await call('record_progress', { ...task, expected_revision: 1, ...patch })).success, false);
  }
  assert.equal((await call('get_engagement_view', task)).view.revision, 1);
  assert.equal((await call('record_progress', { ...task, expected_revision: 1, preflight: health('passed'),
    planSteps: [step('s1', 'running', '合成执行')], activities: [{ ...activity, planStepId: 's1' }] })).success, true);
});

test('旧文本计划可升级步骤，不要求重建或更改旧快照', async t => {
  const { call, task, created } = await fixture(t);
  const legacy = JSON.parse(await readFile(created.record_path, 'utf8'));
  delete legacy.planSteps;
  delete legacy.preflight;
  await writeFile(created.record_path, JSON.stringify(legacy));
  assert.equal((await call('get_engagement_view', task)).success, true);
  assert.equal((await call('record_progress', { ...task, expected_revision: 1, planSteps: [step('s1')] })).success, true);
  assert.equal(JSON.parse(await readFile(created.record_path, 'utf8')).planSteps, undefined);
});

test('新建步骤只能待执行且拒绝重复ID和超容量；关联活动不能绕过检查', async t => {
  const { call, task } = await fixture(t);
  const base = { title: '边界验证', targets: ['example.test'], scope: '离线' };
  for (const planSteps of [[step('s1', 'running')], [step('s1'), step('s1')],
    Array.from({ length: 101 }, (_, i) => step(`s${i}`))]) {
    assert.equal((await call('create_engagement', { ...base, planSteps })).success, false);
  }
  const activity = { id: 'a1', planStepId: 's1', tool: 'synthetic_tool', target: 'example.test', status: 'running',
    startedAt: new Date().toISOString(), summary: '合成活动', evidenceRefs: [] };
  assert.equal((await call('record_progress', { ...task, expected_revision: 1,
    activities: [activity] })).error.code, 'PREFLIGHT_REQUIRED');
  assert.equal((await call('get_engagement_view', task)).view.revision, 1);
});
