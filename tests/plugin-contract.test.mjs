import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile, access } from 'node:fs/promises';

const root = new URL('../external/plugin/', import.meta.url);
const json = async path => JSON.parse(await readFile(new URL(path, root), 'utf8'));

test('DataAgent 插件同时声明技能、两个 MCP 和 HTML 面板', async () => {
  const manifest = await json('.dataagent-plugin/plugin.json');
  assert.equal(manifest.name, 'pentest-tools');
  assert.equal(manifest.skills, undefined, '默认技能目录不能重复声明');
  assert.equal(manifest.mcpServers, './.mcp.json');
  const config = await json('.mcp.json');
  assert.equal(config.mcpServers.scanner.type, 'http');
  assert.equal(config.mcpServers.scanner.url, 'http://127.0.0.1:8889/mcp');
  assert.deepEqual(Object.keys(config.mcpServers).sort(), ['records', 'scanner']);
  assert.equal(config.mcpServers.records.env.PENTEST_RECORDS_ROOT,
    '${DATAAGENT_PROJECT_DIR}/pentest-records');
  assert.equal(manifest.userConfig, undefined, '无需手工选项，不声明未接入的必填配置');
  const panel = await json(manifest.dataPanels);
  assert.equal(panel.schemaVersion, 2);
  assert.equal(panel.renderer, 'html');
  assert.equal(panel.activation.autoOpen, true);
  assert.deepEqual(panel.activation.mcpServers, ['plugin:pentest-tools:records']);
  assert.deepEqual(panel.layout, { type: 'dashboard', sections: [] });
  await access(new URL(`${panel.template.root}/${panel.template.entry}`, root));
});

test('页面只允许读取固定记录工具，原子视图字段不被宿主丢弃', async () => {
  const panel = await json('panels/workbench.panel.json');
  assert.equal(panel.queries.length, 1);
  const [query] = panel.queries;
  assert.equal(query.server, 'plugin:pentest-tools:records');
  assert.equal(query.tool, 'get_engagement_view');
  assert.equal(query.resultPath, 'view');
  assert.deepEqual(query.successConditions, [{ path: 'success', equals: true }]);
  assert.equal(query.autoLoad, false);
  assert.equal(query.refreshIntervalSeconds, 15);
  const fields = panel.dataSources.find(item => item.id === 'view').fields;
  assert.equal(fields.plan.type, 'string');
  assert.equal(fields.plan.required, false, '旧快照未保存计划也能读取');
  assert.deepEqual(fields.planSteps, { type: 'array', required: false });
  assert.deepEqual(fields.preflight, { type: 'object', required: false });
  for (const key of ['taskId', 'revision', 'assets', 'findings', 'activities',
    'attackChains', 'report', 'targets', 'scope', 'exclusions', 'updatedAt']) {
    assert.equal(fields[key].required, true, key);
  }
});
