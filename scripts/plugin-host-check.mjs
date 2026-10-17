import { fileURLToPath, pathToFileURL } from 'node:url';
import { readFile } from 'node:fs/promises';
import { resolve, join } from 'node:path';

const plugin = fileURLToPath(new URL('../plugins/pentest-tools/', import.meta.url));
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
