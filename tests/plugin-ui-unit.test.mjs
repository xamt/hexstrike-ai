import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import test from 'node:test';

const context = { window: {} };
runInNewContext(readFileSync(new URL('../external/plugin/ui/model.js', import.meta.url), 'utf8'), context);
const model = context.window.Pentest.model;

test('本地分页保留完整集合并收敛越界页', () => {
  const rows = Array.from({ length: 30 }, (_, id) => ({ id }));
  const result = model.paginate(rows, 9, 12);
  assert.equal(result.page, 3);
  assert.equal(result.items.length, 6);
  assert.equal(rows.length, 30);
});

test('长时间运行记录标记为待确认而不是远端进程', () => {
  const now = Date.parse('2026-10-17T10:10:00Z');
  assert.equal(model.activityState({ status: 'running', startedAt: '2026-10-17T10:00:00Z' }, now).label, '状态待确认');
  assert.equal(model.activityState({ status: 'running', startedAt: '2026-10-17T10:09:00Z' }, now).label, '执行中（Agent 记录）');
  assert.equal(model.activityState({ status: 'succeeded' }, now).label, '已完成');
});

test('漏洞统计只计入已确认漏洞，排除待验证及误报', () => {
  const totals = model.severityCounts([
    { status: 'confirmed', severity: 'high' },
    { status: 'suspected', severity: 'critical' },
    { status: 'rejected', severity: 'high' },
  ]);
  assert.equal(totals.high, 1);
  assert.equal(totals.critical, 0);
});

test('快照执行状态按留存时点派生，不随着查看日期变化', () => {
  const view = { updatedAt: '2026-10-17T10:03:00Z' };
  const activity = { status: 'running', startedAt: '2026-10-17T10:00:00Z' };
  const asOf = model.displayTime('snapshot', view, Date.parse('2027-01-01T00:00:00Z'));
  assert.equal(asOf, Date.parse(view.updatedAt));
  assert.equal(model.activityState(activity, asOf).label, '执行中（Agent 记录）');
  assert.equal(model.activityState(activity, model.displayTime('live', view, Date.parse('2027-01-01T00:00:00Z'))).label, '状态待确认');
});

test('记录相对时间只说明新鲜度，长时间未更新明确标记可能滞后', () => {
  const now = Date.parse('2026-10-17T10:10:00Z');
  assert.equal(model.recordAge('2026-10-17T10:09:50Z', now), '刚刚更新');
  assert.equal(model.recordAge('2026-10-17T09:00:00Z', now), '1 小时前更新 · 可能滞后');
});

class Element {
  constructor(id) { this.id = id; this.children = []; this.listeners = {}; this.attributes = {}; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  addEventListener(name, listener) { this.listeners[name] = listener; }
  setAttribute(name, value) { this.attributes[name] = value; }
  contains(node) { return this.children.includes(node); }
  focus() {}
}

function state(mode, taskId, viewTask = taskId) {
  return { mode, document: { data: { runtime: { dataSources: {
    context: { value: { taskId, title: taskId } },
    view: { value: viewTask ? { schemaVersion: 1, taskId: viewTask, title: viewTask,
      status: 'running', revision: 1, updatedAt: '2026-10-17T10:00:00Z' } : undefined },
  }, queries: {} } } } };
}

function harness(initial, query) {
  const elements = new Map();
  const calls = [];
  let current = initial;
  let listener;
  const panel = {
    ready: Promise.resolve(initial), getState: () => current,
    subscribe: callback => { listener = callback; return () => {}; },
    query: async (id, parameters) => { calls.push({ id, parameters }); return query?.(id, parameters); },
  };
  const P = { model, dom: { empty: (title, detail) => ({ title, detail }) },
    planProgress: (view, filters, update, asOf) => ({ planTaskId: view.taskId, asOf }),
    report: (view, asOf) => ({ reportTaskId: view.taskId, asOf }) };
  const document = { getElementById: id => {
    if (!elements.has(id)) elements.set(id, new Element(id));
    return elements.get(id);
  } };
  const window = { Pentest: P, DataAgentPanel: panel, addEventListener() {}, setInterval: () => 1, clearInterval() {} };
  runInNewContext(readFileSync(new URL('../external/plugin/ui/app.js', import.meta.url), 'utf8'), { window, document });
  return { calls, elements, emit: next => { current = next; listener(next); } };
}

const settle = () => new Promise(resolve => setImmediate(resolve));

test('快照不查询，页签可以在本地切换', async () => {
  const h = harness(state('snapshot', 'task-a'));
  await settle();
  assert.equal(h.calls.length, 0);
  assert.equal(h.elements.get('refresh').disabled, true);
  assert.equal(h.elements.get('panel-content').children[0].planTaskId, 'task-a');
  h.elements.get('tab-report').listeners.click();
  assert.equal(h.elements.get('panel-content').children[0].reportTaskId, 'task-a');
  assert.equal(h.elements.get('panel-content').children[0].asOf, Date.parse('2026-10-17T10:00:00Z'));
});

test('初次ready只查询一次，收到同任务状态不重复查询', async () => {
  const h = harness(state('live', 'task-a'));
  await settle();
  h.emit(state('live', 'task-a'));
  await settle();
  assert.equal(h.calls.length, 1);
  assert.equal(h.calls[0].id, 'engagement-view');
  assert.equal(h.calls[0].parameters.task_id, 'task-a');
});

test('切换任务时立即清空旧数据，新任务仅查询一次', async () => {
  const h = harness(state('live', 'task-a'));
  await settle();
  h.emit(state('live', 'task-b', 'task-a'));
  assert.equal(h.elements.get('panel-content').children[0].taskId, undefined);
  await settle();
  assert.equal(h.calls.length, 2);
  assert.equal(h.calls[1].parameters.task_id, 'task-b');
  h.emit(state('live', 'task-b'));
  assert.equal(h.elements.get('panel-content').children[0].planTaskId, 'task-b');
});

test('读取失败保留旧数据并明确提示，不自动重试', async () => {
  const h = harness(state('live', 'task-a'), () => { throw new Error('连接不可用'); });
  await settle();
  assert.equal(h.calls.length, 1);
  assert.match(h.elements.get('notice').textContent, /连接不可用.*保留旧数据/);
  assert.equal(h.elements.get('panel-content').children[0].planTaskId, 'task-a');
});

test('NOT_FOUND明确提示目录和任务核对，不误报MCP未连接或诱导重跑', async () => {
  const initial = state('live', 'task-a', '');
  const h = harness(initial, () => { throw new Error(JSON.stringify({ success: false,
    error: { code: 'NOT_FOUND', message: '未找到指定任务记录。' } })); });
  await settle();
  const notice = h.elements.get('notice').textContent;
  assert.match(notice, /记录服务已响应/);
  assert.match(notice, /记录根目录/);
  assert.match(notice, /task_id/);
  assert.doesNotMatch(notice, /检查记录 MCP 连接/);
  assert.match(notice, /不要重新创建任务或重跑扫描/);
  assert.equal(h.calls.length, 1);
});

test('查询忙态阻止重复刷新，切换任务后顺序获取新任务', async () => {
  let release;
  const pending = new Promise(resolve => { release = resolve; });
  const h = harness(state('live', 'task-a'), () => pending);
  await settle();
  assert.equal(h.elements.get('refresh').disabled, true);
  h.elements.get('refresh').listeners.click();
  h.emit(state('live', 'task-b', 'task-a'));
  assert.equal(h.calls.length, 1);
  assert.equal(h.elements.get('panel-content').children[0].taskId, undefined);
  release();
  await settle();
  assert.equal(h.calls.length, 2);
  assert.equal(h.calls[1].parameters.task_id, 'task-b');
});

test('键盘方向键切换页签并维护ARIA状态', async () => {
  const h = harness(state('snapshot', 'task-a'));
  await settle();
  let prevented = false;
  h.elements.get('tab-plan').listeners.keydown({ key: 'ArrowRight', preventDefault: () => { prevented = true; } });
  assert.equal(prevented, true);
  assert.equal(h.elements.get('tab-report').attributes['aria-selected'], 'true');
  assert.equal(h.elements.get('tab-plan').tabIndex, -1);
  assert.equal(h.elements.get('panel-content').attributes['aria-labelledby'], 'tab-report');
});

test('视图没有直接网络调用或动态HTML，仅本地年龄文案定时刷新', () => {
  for (const name of ['model', 'dom', 'plan', 'progress', 'report', 'app']) {
    const source = readFileSync(new URL(`../external/plugin/ui/${name}.js`, import.meta.url), 'utf8');
    assert.doesNotMatch(source, /innerHTML|outerHTML|insertAdjacentHTML|\bfetch\s*\(|XMLHttpRequest|setTimeout\s*\(/);
    if (name !== 'app') assert.doesNotMatch(source, /setInterval\s*\(/);
    else assert.match(source, /setInterval\(updateRecordAge, 15000\)/);
  }
});
