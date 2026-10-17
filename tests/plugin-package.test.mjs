import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir, mkdtemp, rm, realpath } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { unzipSync } from '../plugins/pentest-tools/node_modules/fflate/esm/index.mjs';
import { fileURLToPath } from 'node:url';

const root = new URL('../plugins/pentest-tools/', import.meta.url);
const manifest = JSON.parse(await readFile(new URL('.dataagent-plugin/plugin.json', root), 'utf8'));
const archive = `dist/pentest-tools-${manifest.version}.zip`;

test('ZIP 仅包含可分发内容，技能同步且摘要正确', async () => {
  const zip = await readFile(new URL(archive, root));
  const files = unzipSync(zip);
  for (const name of ['.dataagent-plugin/plugin.json', '.mcp.json', 'panels/workbench.panel.json',
    'ui/index.html', 'dist/records.cjs', 'dist/THIRD_PARTY_LICENSES.txt',
    'skills/pentest-tools/SKILL.md', 'skills/pentest-tools/references/plugin-workbench.md']) {
    assert.ok(files[name], name);
  }
  assert.equal(Object.hasOwn(files, 'LICENSE'), false, '不重新打包已删除的项目许可证，包括旧暂存目录遗留文件');
  assert.equal(Object.hasOwn(files, 'DEVELOPMENT.md'), false, '开发设计与构建文档不得打包');
  const guide = Buffer.from(files['README.md']).toString();
  assert.match(guide, /智能体使用指南/);
  assert.match(guide, /plan/);
  assert.doesNotMatch(guide, /npm (ci|run build|test)|DEVELOPMENT\.md/);
  for (const [, path] of guide.matchAll(/\]\(([^)]+)\)/g)) assert.ok(files[path], `指南链接必须随包：${path}`);
  assert.deepEqual(Object.keys(files).filter(name => name.startsWith('docs/')).sort(),
    ['docs/data-contract.md', 'docs/troubleshooting.md']);
  assert.match(Buffer.from(files['dist/THIRD_PARTY_LICENSES.txt']).toString(), /@modelcontextprotocol\/sdk@/,
    '第三方依赖声明独立保留');
  assert.ok(Object.keys(files).every(name => !/(node_modules|pentest-records|\.git\/|\.helloagents|screenshots|\.env)/.test(name)));
  const config = JSON.parse(Buffer.from(files['.mcp.json']).toString());
  assert.deepEqual(config, JSON.parse(await readFile(new URL('.mcp.json', root), 'utf8')),
    '发布包忠实使用当前MCP配置，不替换用户已确定的本机地址');
  assert.equal(JSON.parse(Buffer.from(files['.dataagent-plugin/plugin.json']).toString()).version, manifest.version);
  const source = await readFile(new URL('../skills/pentest-tools/SKILL.md', import.meta.url), 'utf8');
  const packaged = Buffer.from(files['skills/pentest-tools/SKILL.md']).toString();
  assert.equal(packaged.replace('displayName: 渗透测试工作台\nuser-invocable: true\n', ''), source);
  const hash = createHash('sha256').update(zip).digest('hex');
  assert.ok((await readFile(new URL(`${archive}.sha256`, root), 'utf8')).startsWith(hash));
});

test('解压 ZIP 在无 node_modules 的独立目录运行真实 MCP 协议', async () => {
  const directory = await realpath(await mkdtemp(join(tmpdir(), 'pentest-package-')));
  try {
    const files = unzipSync(await readFile(new URL(archive, root)));
    for (const [name, bytes] of Object.entries(files)) {
      assert.ok(!name.startsWith('/') && !name.split('/').includes('..'));
      const path = join(directory, name);
      await mkdir(dirname(path), { recursive: true });
      await writeFile(path, bytes);
    }
    const env = { ...process.env, PENTEST_PLUGIN_ENTRY: join(directory, 'dist/records.cjs') };
    delete env.NODE_TEST_CONTEXT; // 子进程必须独立启动测试运行器，不能继承父测试的内部执行模式。
    const result = spawnSync(process.execPath,
      ['--test', fileURLToPath(new URL('./plugin-protocol.test.mjs', import.meta.url))],
      { cwd: directory, env,
        encoding: 'utf8', timeout: 20000 });
    assert.equal(result.status, 0, result.stdout + result.stderr);
    assert.match(result.stdout, /(?:# pass 1|pass 1)/, '确认独立协议测试实际执行并通过');
  } finally { await rm(directory, { recursive: true, force: true }); }
});
