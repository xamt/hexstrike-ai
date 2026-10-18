import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { catalog, validateArguments } from './skill-catalog.mjs';

const root = fileURLToPath(new URL('../external/skill/', import.meta.url));

test('离线示例校验拒绝旧别名、错误参数名和错误类型', () => {
  assert.throws(() => validateArguments('httpx_probe_extended', {}), /未知工具/);
  assert.throws(() => validateArguments('httpx_probe', { targets: 'example.test' }), /未知参数/);
  assert.throws(() => validateArguments('httpx_probe', {}), /缺少参数/);
  assert.throws(() => validateArguments('httpx_probe', { target: 'example.test', probe: 'true' }), /必须为/);
  assert.doesNotThrow(() => validateArguments('httpx_probe', { target: 'example.test', probe: true }));
});

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
  assert.equal(count, 3);
});

test('新漏洞与间接资产必须增量规划，数据画像不把元数据当泄漏', () => {
  const workflow = readFileSync(join(root, 'references/planning-validation.md'), 'utf8');
  const plugin = readFileSync(join(root, 'references/plugin-workbench.md'), 'utf8');
  const report = readFileSync(join(root, 'references/reporting.md'), 'utf8');
  for (const value of ['增量计划', 'Qdrant', 'collections', '规模未知', '最小脱敏样例', 'actuator', '逐个拆成IP与服务']) {
    assert.ok(workflow.includes(value), value);
  }
  assert.match(plugin, /dataProfile.*scale\/categories\/sampleStatus\/exposure/);
  assert.match(plugin, /planSteps.*假设.*最小验证.*停止条件/);
  assert.match(report, /记录数未知、未读取内容/);
  assert.match(report, /每个间接IP\/端口\/端点/);
});
