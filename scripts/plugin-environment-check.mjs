import assert from 'node:assert/strict';
import { mkdtemp, readFile, realpath, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const host = process.env.DATAAGENT_SOURCE_ROOT;
if (!host || !process.versions.bun) throw new Error('请指定 DATAAGENT_SOURCE_ROOT 并用 Bun 运行。');
const pluginRoot = resolve(fileURLToPath(new URL('../external/plugin/', import.meta.url)));
const temporary = await realpath(await mkdtemp(join(tmpdir(), 'pentest-plugin-environment-')));
const previousConfig = process.env.AGENT_CONFIG_DIR;
process.env.AGENT_CONFIG_DIR = join(temporary, 'config');
const { resolvePluginMcpEnvironment } = await import(pathToFileURL(
  resolve(host, 'src/utils/plugins/mcpPluginIntegration.ts')).href);
const { setOriginalCwd, getOriginalCwd } = await import(pathToFileURL(
  resolve(host, 'src/bootstrap/state.ts')).href);
const { runWithCwdOverride } = await import(pathToFileURL(
  resolve(host, 'src/utils/cwd.ts')).href);
const previousCwd = getOriginalCwd();
const plugin = { path: pluginRoot, source: 'pentest-tools@offline-environment-check' };
const config = JSON.parse(await readFile(join(pluginRoot, '.mcp.json'), 'utf8')).mcpServers;
try {
  const legacy = { ...config.records, env: { PENTEST_RECORDS_ROOT: '${user_config.records_root}' } };
  assert.throws(() => resolvePluginMcpEnvironment(legacy, plugin, {}), /records_root/);
  console.log('PASS：真实宿主复现未保存 records_root 时的变量替换失败');
  setOriginalCwd(join(temporary, 'workspace'));
  const errors = [];
  const resolved = resolvePluginMcpEnvironment(config.records, plugin, undefined, errors, 'pentest-tools', 'records');
  assert.equal(resolved.env.PENTEST_RECORDS_ROOT, join(temporary, 'workspace/pentest-records'));
  assert.equal(resolved.args[0], join(pluginRoot, 'dist/records.cjs'));
  assert.deepEqual(errors, []);
  console.log('PASS：工作区目录变量无需用户配置即可解析，记录服务入口为实际插件目录');
  const sessionProject = join(temporary, 'workspace');
  setOriginalCwd(join(temporary, 'server-workspace'));
  const panel = runWithCwdOverride(sessionProject,
    () => resolvePluginMcpEnvironment(config.records, plugin));
  assert.equal(panel.env.PENTEST_RECORDS_ROOT, resolved.env.PENTEST_RECORDS_ROOT);
  const projects = ['project-a', 'project-b'].map(name => join(temporary, name));
  const roots = await Promise.all(projects.map(project => runWithCwdOverride(project, async () => {
    await new Promise(resolve => setTimeout(resolve, 1));
    return resolvePluginMcpEnvironment(config.records, plugin).env.PENTEST_RECORDS_ROOT;
  })));
  assert.deepEqual(roots, projects.map(project => join(project, 'pentest-records')));
  console.log('PASS：智能体与HTML查询使用相同会话目录，并发工作区相互隔离');

  const persistent = resolvePluginMcpEnvironment({ ...config.records,
    env: { PENTEST_RECORDS_ROOT: '${DATAAGENT_PLUGIN_DATA}/pentest-records' } }, plugin);
  assert.ok(persistent.env.PENTEST_RECORDS_ROOT.endsWith('/pentest-records'));
  assert.ok(!persistent.env.PENTEST_RECORDS_ROOT.includes('${'));
  console.log('PASS：插件持久目录变量可解析，但未设为本插件默认值');
} finally {
  setOriginalCwd(previousCwd);
  if (previousConfig === undefined) delete process.env.AGENT_CONFIG_DIR;
  else process.env.AGENT_CONFIG_DIR = previousConfig;
  await rm(temporary, { recursive: true, force: true });
}
