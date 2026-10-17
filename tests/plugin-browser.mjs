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

try {
  await liveChecks();
  await stateChecks();
  await missingRecordChecks();
  console.log(`PASS：浏览器离线交互 ${assertions} 项断言；截图目录 ${output}`);
} finally { await browser.close(); }
