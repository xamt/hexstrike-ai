import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { catalog, validateArguments } from '../skills/pentest-tools/scripts/catalog.mjs';

const root = fileURLToPath(new URL('../skills/pentest-tools/', import.meta.url));

function markdownFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? markdownFiles(path) : path.endsWith('.md') ? [path] : [];
  });
}

test('技能所有本地引用可解析，工具说明指向真实调用契约', () => {
  for (const path of markdownFiles(root)) {
    const content = readFileSync(path, 'utf8');
    for (const match of content.matchAll(/\]\(([^)]+)\)/g)) {
      const link = match[1];
      if (/^https?:/.test(link)) continue;
      const destination = resolve(dirname(path), link.split('#')[0]);
      assert.ok(existsSync(destination), `${path}: ${link}`);
      if (destination.includes('/references/tools/') && destination.endsWith('.md')) {
        const name = destination.split('/').at(-1).slice(0, -3);
        assert.ok(Object.hasOwn(catalog, name), `不存在的工具: ${name}`);
      }
    }
  }
});

test('场景中的参数示例符合真实工具参数类型和必填项，不执行调用', () => {
  const files = markdownFiles(join(root, 'references/workflows'));
  let count = 0;
  for (const path of files) {
    const text = readFileSync(path, 'utf8');
    for (const match of text.matchAll(/<!-- tool: ([a-z_]+) -->\s*```json\s*([\s\S]*?)```/g)) {
      const params = JSON.parse(match[2]);
      assert.doesNotThrow(() => validateArguments(match[1], params), `${path}: 参数示例`);
      count++;
    }
  }
  assert.equal(count, 8);
});
