import { dirname, join, resolve } from 'node:path';
import { readFile, readdir } from 'node:fs/promises';

async function packageRoot(path) {
  let current = dirname(path);
  while (current !== dirname(current)) {
    try {
      const pkg = JSON.parse(await readFile(join(current, 'package.json'), 'utf8'));
      if (pkg.name && pkg.version) return { path: current, pkg };
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }
    current = dirname(current);
  }
  throw new Error(`未找到依赖许可证来源：${path}`);
}

/** 收集实际进入运行时产物的第三方包许可证，缺失时中止打包。 */
export async function bundledLicenses(root, metafile) {
  const packages = new Map();
  for (const path of Object.keys(metafile.inputs).filter(path => path.includes('node_modules/'))) {
    const item = await packageRoot(resolve(root, path));
    packages.set(item.path, item);
  }
  const sections = [];
  for (const { path, pkg } of [...packages.values()].sort((a, b) => a.pkg.name.localeCompare(b.pkg.name))) {
    const names = (await readdir(path)).filter(name => /^(licen[cs]e|copying|notice)(\.|$)/i.test(name));
    if (!names.length) throw new Error(`依赖缺少许可证文件：${pkg.name}`);
    const texts = await Promise.all(names.map(name => readFile(join(path, name), 'utf8')));
    sections.push(`${pkg.name}@${pkg.version} (${pkg.license || '见下文'})\n${texts.join('\n')}`);
  }
  return sections.join('\n\n' + '='.repeat(72) + '\n\n') + '\n';
}
