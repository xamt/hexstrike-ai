import { fileURLToPath, pathToFileURL } from 'node:url';
import { readFile, mkdtemp, realpath, readdir, rm } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { tmpdir } from 'node:os';
import assert from 'node:assert/strict';
import { Client } from '../external/plugin/node_modules/@modelcontextprotocol/sdk/dist/esm/client/index.js';
import { StdioClientTransport } from '../external/plugin/node_modules/@modelcontextprotocol/sdk/dist/esm/client/stdio.js';

const plugin = fileURLToPath(new URL('../external/plugin/', import.meta.url));
const host = process.env.DATAAGENT_SOURCE_ROOT;
if (!host) throw new Error('请用 DATAAGENT_SOURCE_ROOT 指定 DataAgent 应用源码根目录（含 src）。');
if (!process.versions.bun) throw new Error('此源码验收使用 DataAgent 原生 Bun 运行时，请用 bun 执行，不替换宿主模块。');
const schemas = {};
const modules = [
  ['PluginPanelDefinitionSchema', 'src/services/pluginPanels/pluginPanelSchema.ts'],
  ['PluginManifestSchema', 'src/utils/plugins/schemas.ts'],
  ['McpJsonConfigSchema', 'src/services/mcp/types.ts'],
];
for (const [name, path] of modules) schemas[name] = (await import(pathToFileURL(resolve(host, path)).href))[name];
const cases = [['面板', 'panels/workbench.panel.json', schemas.PluginPanelDefinitionSchema],
  ['插件清单', '.dataagent-plugin/plugin.json', schemas.PluginManifestSchema()],
  ['MCP配置', '.mcp.json', schemas.McpJsonConfigSchema()]];
for (const [label, path, schema] of cases) {
  schema.parse(JSON.parse(await readFile(join(plugin, path), 'utf8')));
  console.log(`PASS：真实宿主 ${label} Schema`);
}

const { extractSdkToolResultLines, parsePanelEvent } = await import(pathToFileURL(
  resolve(host, 'src/services/pluginPanels/pluginPanelEvents.ts')).href);
const { PluginPanelRuntime } = await import(pathToFileURL(
  resolve(host, 'src/services/pluginPanels/pluginPanelRuntime.ts')).href);
const { loadPluginPanelDefinition } = await import(pathToFileURL(
  resolve(host, 'src/services/pluginPanels/pluginPanelSchema.ts')).href);
const root = await realpath(await mkdtemp(join(tmpdir(), 'pentest-plugin-host-events-')));
const previousConfigDir = process.env.AGENT_CONFIG_DIR;
process.env.AGENT_CONFIG_DIR = join(root, 'host-config');
const client = new Client({ name: 'host-event-check', version: '1.0.0' });
const transport = new StdioClientTransport({ command: process.execPath,
  args: [join(plugin, 'dist/records.cjs')], env: { PENTEST_RECORDS_ROOT: root }, stderr: 'pipe' });
try {
  await client.connect(transport);
  const opened = await client.callTool({ name: 'open_workbench', arguments: {} });
  assert.equal(opened.isError, false);
  const toolResult = { type: 'user', message: { content: [{ type: 'tool_result', content: opened.content }] } };
  const events = extractSdkToolResultLines({ ...toolResult, tool_use_result: opened })
    .map(line => { try { return parsePanelEvent(JSON.parse(line)); } catch { return null; } }).filter(Boolean);
  assert.deepEqual(events.map(event => event.type), ['panel.open']);
  assert.equal(events[0].runId, opened.structuredContent.runId);
  const textOnly = extractSdkToolResultLines(toolResult)
    .map(line => { try { return parsePanelEvent(JSON.parse(line)); } catch { return null; } }).filter(Boolean);
  assert.deepEqual(textOnly, events, 'SDK 丢失_meta与结构化内容后仍能从工具文本提取事件');
  assert.deepEqual(await readdir(root), [], '打开空工作台不创建记录');
  console.log('PASS：真实宿主解析器从MCP工具结果提取唯一打开事件，文本降级仍可提取');
  const definition = await loadPluginPanelDefinition(plugin, './panels/workbench.panel.json');
  const runtime = new PluginPanelRuntime({ storageDir: join(root, 'host-panels'),
    loadRegistry: async () => [{ pluginId: 'pentest-tools', pluginName: 'pentest-tools',
      pluginRoot: plugin, definition }] });
  assert.equal(await runtime.ingestSdkPayload('offline-session', { ...toolResult, tool_use_result: opened }), 1);
  const [panel] = await runtime.listPanels('offline-session');
  assert.equal(panel.autoOpen, true);
  assert.equal(panel.document.data.renderer, 'plugin-panel/html-v1');
  assert.equal(panel.document.data.runId, opened.structuredContent.runId);
  assert.deepEqual(panel.document.data.runtime.dataSources.context.value, {});
  assert.equal(panel.document.data.runtime.dataSources.context.status, 'loading');
  assert.equal(panel.previewAvailable, true);
  console.log('PASS：真实宿主为无任务打开事件创建可展示的HTML实时面板');
  const created = await client.callTool({ name: 'create_engagement', arguments: {
    title: '离线绑定验证', targets: ['example.test'], scope: '合成数据，不连接目标',
  } });
  const createdPayload = { type: 'user', message: { content: [{ type: 'tool_result', content: created.content }] },
    tool_use_result: created };
  assert.equal(await runtime.ingestSdkPayload('offline-session', createdPayload), 2);
  const [bound] = await runtime.listPanels('offline-session');
  assert.equal(bound.id, panel.id, '绑定真实任务时复用同一实时面板');
  assert.equal(bound.document.data.runId, created.structuredContent.runId);
  assert.equal(bound.document.data.runtime.dataSources.context.value.taskId, created.structuredContent.task_id);
  assert.equal(bound.autoOpen, true);
  console.log('PASS：真实宿主复用实时面板并将后续创建的任务上下文绑定至新运行');
} finally {
  await client.close();
  await rm(root, { recursive: true, force: true });
  if (previousConfigDir === undefined) delete process.env.AGENT_CONFIG_DIR;
  else process.env.AGENT_CONFIG_DIR = previousConfigDir;
}
