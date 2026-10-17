import assert from 'node:assert/strict';
import { readFile, mkdir } from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { join, extname } from 'node:path';
import { sampleView } from './fixtures/plugin-view.mjs';

if (!process.env.PLAYWRIGHT_MODULE) throw new Error('请提供 PLAYWRIGHT_MODULE 模块入口路径。');
const { chromium } = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE).href);
const ui = fileURLToPath(new URL('../plugins/pentest-tools/ui/', import.meta.url));
const output = fileURLToPath(new URL('../plugins/pentest-tools/dist/screenshots/', import.meta.url));
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL });
let assertions = 0;

async function pageFor(mode, view, options = {}) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 1000 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    assert.equal(url.origin, 'https://plugin.test', '页面不得请求其他服务');
    const name = url.pathname === '/' ? 'index.html' : url.pathname.slice(1);
    assert.match(name, /^[a-z-]+\.(html|css|js)$/);
    const contentType = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript' }[extname(name)];
    await route.fulfill({ body: await readFile(join(ui, name)), contentType });
  });
  await page.addInitScript(({ mode, view, options }) => {
    const listeners = [];
    window.calls = [];
    window.mockState = { mode, document: { data: { runtime: {
      dataSources: { context: { value: { taskId: view.taskId, title: view.title }, hasData: true },
        view: { value: options.loading ? null : view, hasData: !options.loading } }, queries: {},
    } } } };
    window.emit = () => listeners.forEach(fn => fn(window.mockState));
    window.DataAgentPanel = {
      ready: Promise.resolve(window.mockState), getState: () => window.mockState,
      subscribe: fn => { listeners.push(fn); return () => {}; },
      query: async (id, args) => {
        window.calls.push({ id, args });
        if (options.loading) return new Promise(() => {});
        window.emit();
        return { data: view, parameters: args, fetchedAt: new Date().toISOString() };
      },
    };
  }, { mode, view, options });
  await page.goto('https://plugin.test');
  await page.locator('#task-title').filter({ hasText: view.title }).waitFor();
  return { page, errors };
}

async function capture(page, name) {
  await page.screenshot({ path: join(output, `${name}.png`), fullPage: false });
}

async function liveChecks() {
  const { page, errors } = await pageFor('live', sampleView());
  assert.equal(await page.evaluate(() => window.calls.length), 1); assertions++;
  assert.equal(await page.locator('#panel-content tbody tr').count(), 4); assertions++;
  await capture(page, 'progress-wide');
  await page.selectOption('#asset-kind', 'data');
  assert.equal(await page.locator('#panel-content tbody tr').count(), 1); assertions++;
  await page.locator('#tab-progress').focus();
  await page.keyboard.press('ArrowRight');
  assert.equal(await page.locator('#tab-report').getAttribute('aria-selected'), 'true'); assertions++;
  for (const text of ['摘要', '漏洞统计', '关键发现', '测试目标与范围', '资产清单', '验证过程', '修复建议', '攻击链分析', '未验证项']) {
    assert.ok((await page.locator('#panel-content').innerText()).includes(text), text); assertions++;
  }
  assert.equal(await page.locator('img').count(), 0); assertions++;
  assert.equal(await page.evaluate(() => window.injected), undefined); assertions++;
  await capture(page, 'report-wide');
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true); assertions++;
  await capture(page, 'report-narrow');
  await page.locator('.report-finding').first().scrollIntoViewIfNeeded();
  await capture(page, 'report-narrow-finding');
  await page.click('#tab-progress');
  await capture(page, 'progress-narrow');
  assert.deepEqual(errors, []); assertions++;
  await page.close();
}

async function stateChecks() {
  const { page, errors } = await pageFor('snapshot', sampleView());
  assert.equal(await page.evaluate(() => window.calls.length), 0); assertions++;
  assert.equal(await page.locator('#refresh').isDisabled(), true); assertions++;
  await capture(page, 'snapshot');
  await page.evaluate(() => {
    window.mockState.mode = 'live';
    window.mockState.document.data.runtime.queries['engagement-view'] = { error: '合成断连' };
    window.emit();
  });
  assert.match(await page.locator('#notice').innerText(), /合成断连.*保留旧数据/); assertions++;
  assert.equal(await page.locator('#panel-content tbody tr').count(), 4); assertions++;
  await capture(page, 'error-stale');
  assert.deepEqual(errors, []); assertions++;
  await page.close();
  const empty = sampleView();
  empty.assets = []; empty.findings = []; empty.activities = []; empty.attackChains = [];
  const emptyPage = await pageFor('snapshot', empty);
  assert.ok((await emptyPage.page.locator('#panel-content').innerText()).includes('暂无匹配资产')); assertions++;
  await capture(emptyPage.page, 'empty');
  await emptyPage.page.close();
  const loading = await pageFor('live', sampleView(), { loading: true });
  assert.equal(await loading.page.locator('#refresh').isDisabled(), true); assertions++;
  assert.ok((await loading.page.locator('#panel-content').innerText()).includes('等待任务记录')); assertions++;
  await capture(loading.page, 'loading');
  await loading.page.close();
}

async function missingRecordChecks() {
  const { page, errors } = await pageFor('snapshot', sampleView());
  await page.evaluate(() => {
    window.mockState.mode = 'live';
    window.mockState.document.data.runtime.dataSources.view.value = null;
    window.mockState.document.data.runtime.dataSources.context.value.taskId = '00000000-0000-4000-8000-000000000002';
    window.mockState.document.data.runtime.queries['engagement-view'] = {
      error: JSON.stringify({ success: false, error: { code: 'NOT_FOUND', message: '未找到指定任务记录。' } }),
    };
    window.emit();
  });
  assert.match(await page.locator('#notice').innerText(), /记录服务已响应.*记录根目录.*不要重新创建任务或重跑扫描/); assertions++;
  assert.match(await page.locator('#panel-content').innerText(), /未能读取任务记录/); assertions++;
  await capture(page, 'missing-record');
  await page.click('#tab-report');
  assert.match(await page.locator('#panel-content').innerText(), /未能读取任务记录/); assertions++;
  assert.deepEqual(errors, []); assertions++;
  await page.close();
}

async function planChecks() {
  const planned = sampleView();
  Object.assign(planned, { status: 'planned', phase: '', assets: [], findings: [], activities: [], attackChains: [],
    assetCount: 0, confirmedCount: 0, suspectedCount: 0, runningCount: 0,
    plan: '阶段1：核对目标与范围\n阶段2：复用工具验证疑点\n停止条件：服务退化立即停止\n<img src=x onerror="window.injected=true">' });
  const { page, errors } = await pageFor('live', planned);
  assert.equal(await page.locator('#tab-progress').getAttribute('aria-selected'), 'true'); assertions++;
  assert.equal(await page.locator('.test-plan .multiline').textContent(), planned.plan); assertions++;
  assert.equal(await page.locator('#panel-content section').first().getAttribute('class'), 'section test-plan'); assertions++;
  assert.match(await page.locator('#task-meta').innerText(), /待开始/); assertions++;
  assert.equal(await page.locator('img').count(), 0); assertions++;
  assert.equal(await page.evaluate(() => window.injected), undefined); assertions++;
  assert.equal(await page.locator('.test-plan .multiline').evaluate(el => getComputedStyle(el).whiteSpace), 'pre-wrap'); assertions++;
  await capture(page, 'plan-wide');
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true); assertions++;
  await capture(page, 'plan-narrow');
  assert.deepEqual(errors, []); assertions++;
  await page.close();
  const legacy = await pageFor('snapshot', sampleView());
  assert.match(await legacy.page.locator('.test-plan').innerText(), /尚未记录测试计划/); assertions++;
  assert.equal(await legacy.page.evaluate(() => window.calls.length), 0); assertions++;
  await legacy.page.close();
}

async function stepStatusChecks() {
  const view = sampleView();
  view.plan = '验证过程按实际结果更新，不以扫描调用成功代替完成。';
  view.planSteps = ['pending', 'running', 'completed', 'blocked'].map((status, index) => ({
    id: `s${index}`, title: ['资产识别', '访问控制验证', '基线证据核对', '需账号的验证'][index], status,
    summary: ['尚未执行', '已保存正常请求，等待对照结果', '已核对现有证据', '缺少测试角色账号'][index], evidenceRefs: [],
  }));
  view.preflight = { status: 'passed', checkedAt: view.updatedAt, server: 'plugin:pentest-tools:hexstrike',
    tool: 'mcp__plugin_pentest-tools_hexstrike__server_health', summary: '合成健康响应，核心工具及本轮所用工具可用' };
  const { page, errors } = await pageFor('live', view);
  assert.deepEqual(await page.locator('.plan-step .badge').allTextContents(), ['待执行', '执行中', '已完成', '受阻']); assertions++;
  assert.match(await page.locator('.plan-counts').innerText(), /待执行 1 · 执行中 1 · 已完成 1 · 受阻 1/); assertions++;
  assert.match(await page.locator('.preflight').innerText(), /最近检查通过.*检查于/s); assertions++;
  await capture(page, 'steps-wide');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator('.test-plan').scrollIntoViewIfNeeded();
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true); assertions++;
  await capture(page, 'steps-narrow');
  await page.evaluate(() => {
    const current = window.mockState.document.data.runtime.dataSources.view.value;
    current.revision++;
    current.status = 'paused';
    current.preflight.status = 'failed';
    current.preflight.summary = '合成MCP断连，停止新的目标测试';
    current.planSteps[1].status = 'blocked';
    current.planSteps[1].summary = '远端执行状态未知，不重放';
    window.emit();
  });
  assert.deepEqual(await page.locator('.plan-step .badge').allTextContents(), ['待执行', '受阻', '已完成', '受阻']); assertions++;
  assert.match(await page.locator('.preflight').innerText(), /检查未通过.*已暂停测试派发/s); assertions++;
  assert.match(await page.locator('[data-step-id="s1"]').innerText(), /远端执行状态未知/); assertions++;
  assert.equal(await page.evaluate(() => window.calls.length), 1, '状态更新不追加查询或打开'); assertions++;
  await capture(page, 'steps-blocked');
  assert.deepEqual(errors, []); assertions++;
  await page.close();
}

try {
  await liveChecks();
  await stateChecks();
  await missingRecordChecks();
  await planChecks();
  await stepStatusChecks();
  console.log(`PASS：浏览器离线交互 ${assertions} 项断言；截图目录 ${output}`);
} finally { await browser.close(); }
