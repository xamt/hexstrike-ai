import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, realpath, readFile, readdir, mkdir, symlink, stat, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { createHandler, tools } from '../external/plugin/servers/records.mjs';

/** Create an isolated store that is removed after each test. */
async function store(t) {
  const parent = await realpath(tmpdir());
  const root = await mkdtemp(path.join(parent, 'pentest-records-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  return { root, call: createHandler({ root }) };
}

/** Create a minimal engagement without invoking any remote service. */
async function create(call) {
  const result = await call('create_engagement', { title: '授权测试', targets: ['example.test'], scope: '仅测试环境' });
  assert.equal(result.success, true, JSON.stringify(result));
  return result.task_id;
}

/** Return an asset fixture with evidence paths, not sensitive contents. */
function asset(id = 'A-1') {
  return { id, kind: 'domain', value: 'example.test', description: '授权域名', evidenceRefs: ['evidence/asset.txt'], observedAt: '2026-10-17T01:00:00.000Z' };
}

/** Return a confirmed finding backed by an asset and a local evidence reference. */
function finding() {
  return { id: 'F-1', title: '访问控制缺陷', status: 'confirmed', severity: 'high', assetIds: ['A-1'], description: '测试描述', validation: '双账号复核', poc: 'GET /item/1\n```\n<script>alert(1)</script>', impact: '测试账号越权读取', remediation: '实施对象级鉴权', evidenceRefs: ['evidence/F-1.txt'] };
}

test('工具声明、初始记录、原子版本读取与open保持一致', async t => {
  const { root, call } = await store(t);
  assert.deepEqual(tools.map(tool => tool.name), ['open_workbench', 'create_engagement', 'record_progress', 'get_engagement_view', 'open_engagement', 'export_report']);
  assert.ok(tools.every(tool => tool.inputSchema.additionalProperties === false));
  assert.equal((await call('open_workbench', {})).success, true);
  assert.deepEqual(await readdir(root), [], '先打开工作台不能提前创建任务目录');
  const taskId = await create(call);
  const { view } = await call('get_engagement_view', { task_id: taskId });
  assert.equal(view.revision, 1);
  assert.equal(view.status, 'planned');
  assert.equal(view.assetCount, 0);
  assert.equal(view.report.summary, '');
  assert.deepEqual((await call('open_engagement', { task_id: taskId })).view, view);
  assert.equal((await stat(path.join(root, taskId))).mode & 0o777, 0o700);
  const revisions = await readdir(path.join(root, taskId, 'revisions'));
  assert.equal(revisions.length, 1);
  assert.equal((await stat(path.join(root, taskId, 'revisions', revisions[0]))).mode & 0o777, 0o600);
});

test('按ID更新、引用校验、计数和revision历史', async t => {
  const { root, call } = await store(t);
  const taskId = await create(call);
  const result = await call('record_progress', {
    task_id: taskId, expected_revision: 1, status: 'running', phase: '验证',
    assets: [asset(), { ...asset('A-2'), kind: 'service', value: 'HTTPS', parentId: 'A-1', port: 443, protocol: 'tcp', service: 'https' }],
    findings: [finding()],
    activities: [{ id: 'T-1', tool: 'plugin:pentest-tools:scanner:nmap_scan', target: 'example.test', status: 'running', startedAt: '2026-10-17T01:00:00Z', summary: '仅为离线夹具', evidenceRefs: [] }],
    attackChains: [{ id: 'C-1', title: '对象访问链', status: 'verified', steps: [{ findingId: 'F-1', description: '已复核', verified: true }], impact: '受限影响', evidenceRefs: ['evidence/F-1.txt'] }],
  });
  assert.equal(result.success, true, JSON.stringify(result));
  assert.equal(result.revision, 2);
  const { view } = await call('get_engagement_view', { task_id: taskId });
  assert.equal(view.assetCount, 2);
  assert.equal(view.confirmedCount, 1);
  assert.equal(view.runningCount, 1);
  assert.equal(view.findings.length, 1);
  assert.equal((await readdir(path.join(root, taskId, 'revisions'))).length, 2);
  const updated = await call('record_progress', { task_id: taskId, expected_revision: 2, findings: [{ ...finding(), description: '修订说明' }] });
  assert.equal(updated.success, true);
  assert.equal((await call('get_engagement_view', { task_id: taskId })).view.findings.length, 1);
});

test('CAS冲突不写入、不自动重放，空修改被拒绝', async t => {
  const { call } = await store(t);
  const taskId = await create(call);
  const attempts = await Promise.all(['侦察', '验证'].map(phase => call('record_progress', { task_id: taskId, expected_revision: 1, phase })));
  assert.equal(attempts.filter(result => result.success).length, 1);
  assert.equal(attempts.find(result => !result.success).error.code, 'REVISION_CONFLICT');
  assert.equal((await call('get_engagement_view', { task_id: taskId })).view.revision, 2);
  assert.equal((await call('record_progress', { task_id: taskId, expected_revision: 2 })).error.code, 'VALIDATION_ERROR');
});

test('拒绝缺失证据、无效引用、环、未知字段和错误类型', async t => {
  const { call } = await store(t);
  const taskId = await create(call);
  const invalid = [
    { assets: [asset()], findings: [{ ...finding(), evidenceRefs: [] }] },
    { assets: [asset()], findings: [{ ...finding(), assetIds: ['missing'] }] },
    { assets: [{ ...asset(), parentId: 'A-2' }, { ...asset('A-2'), parentId: 'A-1' }] },
    { assets: [{ ...asset(), kind: 'service' }] },
    { assets: [{ ...asset(), port: '443' }] },
    { assets: [{ ...asset(), evidenceRefs: ['../outside'] }] },
    { assets: [asset()], findings: [finding()], attackChains: [{ id: 'C-1', title: '未验证链', status: 'verified', steps: [{ findingId: 'F-1', description: '假设', verified: false }], impact: '', evidenceRefs: ['evidence.txt'] }] },
    { status: 'not-a-status' }, { phase: 'x', allow_delete: true },
    { assets: [asset(), asset()] },
  ];
  for (const patch of invalid) {
    const result = await call('record_progress', { task_id: taskId, expected_revision: 1, ...patch });
    assert.equal(result.success, false, JSON.stringify(patch));
    assert.equal(result.error.code, 'VALIDATION_ERROR');
  }
  assert.equal((await call('get_engagement_view', { task_id: taskId })).view.revision, 1);
});

test('拒绝路径逃逸、符号链接、未知任务和超限内容', async t => {
  const { root, call } = await store(t);
  const taskId = await create(call);
  assert.equal((await call('get_engagement_view', { task_id: '../outside' })).success, false);
  assert.equal((await call('get_engagement_view', { task_id: '11111111-1111-4111-8111-111111111111' })).error.code, 'NOT_FOUND');
  const tooLarge = await call('record_progress', { task_id: taskId, expected_revision: 1, phase: 'x'.repeat(1024 * 1024) });
  assert.equal(tooLarge.error.code, 'LIMIT_EXCEEDED');
  const many = await call('record_progress', { task_id: taskId, expected_revision: 1, assets: Array.from({ length: 501 }, (_, i) => asset(`A-${i}`)) });
  assert.equal(many.error.code, 'LIMIT_EXCEEDED');
  const linkId = '22222222-2222-4222-8222-222222222222';
  await symlink(path.join(root, taskId), path.join(root, linkId));
  assert.equal((await call('get_engagement_view', { task_id: linkId })).error.code, 'UNSAFE_PATH');
  await symlink(root, path.join(root, taskId, 'evidence'));
  assert.equal((await call('record_progress', { task_id: taskId, expected_revision: 1, assets: [asset()] })).error.code, 'UNSAFE_PATH');
  assert.throws(() => createHandler({ root: 'relative/path' }), /绝对路径/);
});

test('完整报告导出、PoC fence安全、阶段标识与版本固定', async t => {
  const { call } = await store(t);
  const taskId = await create(call);
  await call('record_progress', { task_id: taskId, expected_revision: 1, assets: [asset()], findings: [finding()], report: { summary: '<script>恶意标题</script>', keyFindings: ['关键发现'], coverage: '仅离线夹具', limitations: ['尚未验证其他目标'], recommendations: ['修复鉴权'] } });
  const result = await call('export_report', { task_id: taskId, expected_revision: 2 });
  assert.equal(result.success, true, JSON.stringify(result));
  const report = await readFile(result.report_path, 'utf8');
  for (const section of ['摘要', '漏洞统计', '关键发现', '测试目标', '资产清单', '漏洞详情', '攻击链分析', '未验证项与覆盖限制', '修复建议']) assert.ok(report.includes(section), section);
  assert.match(report, /阶段报告/);
  assert.match(report, /&lt;script&gt;/);
  assert.match(report, /````text\nGET \/item\/1\n```\n<script>/);
  assert.equal((await call('export_report', { task_id: taskId, expected_revision: 1 })).error.code, 'REVISION_CONFLICT');
  assert.equal((await call('get_engagement_view', { task_id: taskId })).view.revision, 2);
  assert.equal((await call('export_report', { task_id: taskId, expected_revision: 2 })).success, true);
});

test('跨进程CAS只允许一个版本写入', async t => {
  const { root, call } = await store(t);
  const taskId = await create(call);
  const moduleUrl = new URL('../external/plugin/servers/records.mjs', import.meta.url).href;
  const code = `import {createHandler} from ${JSON.stringify(moduleUrl)}; console.log(JSON.stringify(await createHandler({root:process.argv[1]})('record_progress',{task_id:process.argv[2],expected_revision:1,phase:'跨进程'})));`;
  const run = () => new Promise((resolve, reject) => {
    const child = spawn(process.execPath, ['--input-type=module', '-e', code, root, taskId], { stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '', error = '';
    child.stdout.on('data', chunk => { output += chunk; });
    child.stderr.on('data', chunk => { error += chunk; });
    child.on('error', reject);
    child.on('exit', status => status === 0 ? resolve(JSON.parse(output)) : reject(new Error(error)));
  });
  const results = await Promise.all([run(), run()]);
  assert.equal(results.filter(result => result.success).length, 1);
  assert.equal(results.find(result => !result.success).error.code, 'REVISION_CONFLICT');
});

test('遗留锁明确超时报错，数据不被清理', async t => {
  const { root, call } = await store(t);
  const taskId = await create(call);
  await mkdir(path.join(root, taskId, '.write-lock'));
  const result = await call('record_progress', { task_id: taskId, expected_revision: 1, phase: '不得写入' });
  assert.equal(result.error.code, 'LOCK_TIMEOUT');
  assert.ok((await stat(path.join(root, taskId, '.write-lock'))).isDirectory());
  assert.equal((await call('get_engagement_view', { task_id: taskId })).view.revision, 1);
});

test('未发布临时文件不影响读取，损坏统计不伪装成功', async t => {
  const { root, call } = await store(t);
  const taskId = await create(call);
  const revisions = path.join(root, taskId, 'revisions');
  await writeFile(path.join(revisions, '.tmp-crashed'), '{partial', { mode: 0o600 });
  assert.equal((await call('get_engagement_view', { task_id: taskId })).view.revision, 1);
  const current = path.join(revisions, 'r0000000001.json');
  const value = JSON.parse(await readFile(current, 'utf8'));
  value.assetCount = 99;
  await writeFile(current, JSON.stringify(value));
  assert.equal((await call('get_engagement_view', { task_id: taskId })).error.code, 'CORRUPT_RECORD');
});

test('快照、报告目的地和配置根目录的符号链接均被拒绝', async t => {
  const { root, call } = await store(t);
  const taskId = await create(call);
  const task = path.join(root, taskId);
  await mkdir(path.join(task, 'reports'));
  await symlink(path.join(task, 'revisions', 'r0000000001.json'), path.join(task, 'reports', 'report-r1.md'));
  assert.equal((await call('export_report', { task_id: taskId, expected_revision: 1 })).error.code, 'UNSAFE_PATH');
  await symlink(path.join(task, 'revisions', 'r0000000001.json'), path.join(task, 'revisions', 'r0000000002.json'));
  assert.equal((await call('get_engagement_view', { task_id: taskId })).error.code, 'UNSAFE_PATH');
  const linkedRoot = path.join(root, 'linked-root');
  await symlink(root, linkedRoot);
  const unsafe = createHandler({ root: linkedRoot });
  assert.equal((await unsafe('create_engagement', { title: 'test', targets: ['example.test'], scope: '离线测试' })).error.code, 'UNSAFE_PATH');
});
