import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, realpath, rm, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHandler } from '../plugins/pentest-tools/servers/records.mjs';

async function fixture(t) {
  const root = await mkdtemp(join(await realpath(tmpdir()), 'plugin-plan-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  return createHandler({ root });
}

test('计划在零扫描零资产阶段持久化，并按版本完整更新', async t => {
  const call = await fixture(t);
  const plan = '目标：核对暴露面\n1. 范围确认\n2. 低影响验证\n停止：服务异常';
  const created = await call('create_engagement', { title: '计划', targets: ['example.test'], scope: '离线', plan });
  assert.equal(created.success, true);
  const task = { task_id: created.task_id };
  const first = (await call('get_engagement_view', task)).view;
  assert.equal(first.plan, plan);
  assert.equal(first.status, 'planned');
  assert.deepEqual(first.activities, []);
  const nextPlan = '调整后的范围与停止条件';
  assert.equal((await call('record_progress', { ...task, expected_revision: 1, plan: nextPlan })).success, true);
  assert.equal((await call('get_engagement_view', task)).view.plan, nextPlan);
  assert.equal(JSON.parse(await readFile(created.record_path, 'utf8')).plan, plan);
  const conflict = await call('record_progress', { ...task, expected_revision: 1, plan });
  assert.equal(conflict.error.code, 'REVISION_CONFLICT');
  const bad = await call('record_progress', { ...task, expected_revision: 2, plan: 'x'.repeat(20001) });
  assert.equal(bad.success, false);
  assert.equal((await call('get_engagement_view', task)).view.revision, 2);
});

test('旧版无plan快照仍可读取和追加计划，不修改原版本', async t => {
  const call = await fixture(t);
  const created = await call('create_engagement', { title: '旧任务', targets: ['example.test'], scope: '离线' });
  const old = JSON.parse(await readFile(created.record_path, 'utf8'));
  delete old.plan;
  await writeFile(created.record_path, JSON.stringify(old));
  const task = { task_id: created.task_id };
  assert.equal((await call('get_engagement_view', task)).success, true);
  assert.equal((await call('record_progress', { ...task, expected_revision: 1, plan: '补充已确认的计划' })).success, true);
  assert.equal(JSON.parse(await readFile(created.record_path, 'utf8')).plan, undefined);
});

test('先创建后补计划只改变规划阶段，显式阶段优先且不自动开始测试', async t => {
  const call = await fixture(t);
  for (const patch of [{ plan: '离线计划' }, { planSteps: [
    { id: 's1', title: '离线核对', status: 'pending', summary: '', evidenceRefs: [] },
  ] }, { plan: '离线计划', phase: '范围确认中' }]) {
    const created = await call('create_engagement', { title: '规划', targets: ['example.test'], scope: '离线' });
    const task = { task_id: created.task_id };
    assert.equal((await call('get_engagement_view', task)).view.phase, '制定测试计划');
    assert.equal((await call('record_progress', { ...task, expected_revision: 1, ...patch })).success, true);
    const view = (await call('get_engagement_view', task)).view;
    assert.equal(view.phase, patch.phase || '计划已记录');
    assert.equal(view.status, 'planned');
    assert.deepEqual(view.activities, []);
    assert.equal(view.preflight, undefined);
  }
});
