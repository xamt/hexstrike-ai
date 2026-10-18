import assert from 'node:assert/strict';

/** 以真实stdio验证结构化计划及失败暂停，不接触远端服务。 */
export async function verifyWorkflowProtocol(call) {
  const step = { id: 's1', title: '合成步骤', status: 'pending', summary: '', evidenceRefs: [] };
  const created = await call('create_engagement', { title: '步骤与MCP门槛', targets: ['example.test'], scope: '离线', planSteps: [step] });
  assert.equal(created.isError, false);
  assert.equal(created._meta['dataagent/panelEvents'][0].type, 'panel.open');
  const task = { task_id: created.structuredContent.task_id };
  const running = { ...task, expected_revision: 1, planSteps: [{ ...step, status: 'running', summary: '开始合成验证' }] };
  const refused = await call('record_progress', running);
  assert.equal(refused.structuredContent.error.code, 'PREFLIGHT_REQUIRED');
  assert.equal(refused._meta, undefined);
  const preflight = { status: 'passed', checkedAt: new Date().toISOString(), server: 'plugin:pentest-tools:scanner',
    tool: 'mcp__plugin_pentest-tools_scanner__server_health', summary: '合成正常响应，仅协议测试' };
  const started = await call('record_progress', { ...running, preflight });
  assert.equal(started.isError, false);
  assert.equal(started._meta, undefined, '步骤状态更新不反复打开');
  const failed = await call('record_progress', { ...task, expected_revision: 2,
    preflight: { ...preflight, status: 'failed', summary: '合成断连' } });
  assert.equal(failed.isError, false);
  const view = (await call('get_engagement_view', task)).structuredContent.view;
  assert.equal(view.status, 'paused');
  assert.equal(view.planSteps[0].status, 'blocked');
  assert.equal(view.planSteps[0].summary, '合成断连');
  assert.equal(view.preflight.status, 'failed');
  const invalid = await call('create_engagement', { title: '错误类型', targets: ['example.test'], scope: '离线', plan: 123 });
  assert.equal(invalid.isError, true);
  assert.equal(invalid._meta, undefined);
}
