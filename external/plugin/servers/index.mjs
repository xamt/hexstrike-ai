import { randomUUID } from 'node:crypto';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { tools, createHandler } from './records.mjs';

const handler = createHandler({ root: process.env.PENTEST_RECORDS_ROOT });
const server = new Server({ name: 'pentest-tools-records', title: '渗透测试记录', version: '1.0.7' },
  { capabilities: { tools: {} } });

function result(value) {
  return {
    isError: value.success === false,
    structuredContent: value,
    content: [{ type: 'text', text: JSON.stringify(value) }],
  };
}

/** Publish the same validated event through all host-supported MCP result channels. */
function opened(view, saved = {}) {
  const identity = { pluginId: 'pentest-tools', panelId: 'pentest-workbench', runId: randomUUID() };
  const base = { protocol: 'dataagent-plugin-panel-event/v2', ...identity };
  const events = [{ ...base, type: 'panel.open', ...(view?.title ? { title: view.title } : {}) }];
  if (view?.taskId) events.push({ ...base, type: 'data.updated', dataSourceId: 'context',
    operation: 'replace', status: 'ready', data: { taskId: view.taskId, title: view.title } });
  const value = { ...saved, success: true, ...identity,
    ...(view?.taskId ? { task_id: view.taskId, revision: view.revision } : {}) };
  return {
    ...result(value),
    structuredContent: { ...value, dataagentPanelEvents: events },
    content: [{ type: 'text', text: JSON.stringify(value) },
      ...events.map(event => ({ type: 'text', text: JSON.stringify(event) }))],
    _meta: { 'dataagent/panelEvents': events },
  };
}

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools }));
server.setRequestHandler(CallToolRequestSchema, async request => {
  const name = request.params.name;
  const args = request.params.arguments ?? {};
  const value = await handler(name, args);
  if (name === 'open_workbench' && value.success) return opened(undefined, value);
  if (name === 'open_engagement' && value.success) return opened(value.view);
  const opensPlan = name === 'record_progress' && typeof args.plan === 'string' && args.plan.trim();
  if (value.success && (name === 'create_engagement' || opensPlan)) {
    return opened({ taskId: value.task_id, title: value.title, revision: value.revision }, value);
  }
  return result(value);
});

server.connect(new StdioServerTransport()).catch(error => {
  console.error(`记录服务启动失败：${error.message}`);
  process.exitCode = 1;
});
