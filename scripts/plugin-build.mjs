import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { join, dirname, relative } from 'node:path';
import { readFile, writeFile, mkdir, cp, rm, readdir, lstat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { bundledLicenses } from './plugin-build-licenses.mjs';

const repository = fileURLToPath(new URL('../', import.meta.url));
const root = join(repository, 'plugins/pentest-tools');
const require = createRequire(join(root, 'package.json'));
const { build } = require('esbuild');
const { zipSync } = require('fflate');

async function collect(directory, base, files = {}) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if ((await lstat(path)).isSymbolicLink()) throw new Error(`不允许符号链接：${path}`);
    if (entry.isDirectory()) await collect(path, base, files);
    else files[relative(base, path).split('\\').join('/')] = await readFile(path);
  }
  return files;
}

async function copySkills() {
  const target = join(root, 'skills/pentest-tools');
  await rm(target, { recursive: true, force: true }); // 仅清理声明为生成产物的目录。
  await cp(join(repository, 'skills/pentest-tools'), target, { recursive: true });
  const entry = join(target, 'SKILL.md');
  const source = await readFile(entry, 'utf8');
  await writeFile(entry, source.replace('name: pentest-tools\n',
    'name: pentest-tools\ndisplayName: 渗透测试工作台\nuser-invocable: true\n'));
}

async function packagePlugin(version) {
  const stage = join(root, 'dist/package');
  await rm(stage, { recursive: true, force: true });
  await mkdir(stage, { recursive: true });
  const paths = ['.dataagent-plugin', '.mcp.json', 'panels', 'ui', 'skills', 'docs',
    'README.md', 'dist/records.cjs', 'dist/THIRD_PARTY_LICENSES.txt'];
  for (const path of paths) {
    await mkdir(dirname(join(stage, path)), { recursive: true });
    await cp(join(root, path), join(stage, path), { recursive: true });
  }
  await cp(join(repository, 'LICENSE'), join(stage, 'LICENSE'));
  const files = await collect(stage, stage);
  const bytes = zipSync(files, { level: 6, mtime: new Date('2026-01-01T00:00:00Z') });
  const path = join(root, `dist/pentest-tools-${version}.zip`);
  await writeFile(path, bytes);
  const sha = createHash('sha256').update(bytes).digest('hex');
  await writeFile(`${path}.sha256`, `${sha}  pentest-tools-${version}.zip\n`);
  await rm(stage, { recursive: true, force: true });
  console.log(`插件包：${path}\nSHA-256：${sha}\n文件数：${Object.keys(files).length}`);
}

await mkdir(join(root, 'dist'), { recursive: true });
await copySkills();
const bundle = await build({
  absWorkingDir: root, entryPoints: ['servers/index.mjs'], outfile: 'dist/records.cjs',
  bundle: true, platform: 'node', format: 'cjs', target: 'node22',
  metafile: true, legalComments: 'inline', sourcemap: false,
});
await writeFile(join(root, 'dist/THIRD_PARTY_LICENSES.txt'), await bundledLicenses(root, bundle.metafile));
const manifest = JSON.parse(await readFile(join(root, '.dataagent-plugin/plugin.json'), 'utf8'));
await packagePlugin(manifest.version);
