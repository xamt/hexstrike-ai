import { readFileSync } from 'node:fs';

export const catalog = JSON.parse(readFileSync(new URL('../external/skill/references/tool-catalog.json', import.meta.url), 'utf8'));

/** 仅离线检查文档示例；实际 MCP 参数验证由宿主和服务负责。 */
export function validateArguments(name, args) {
  if (!Object.hasOwn(catalog, name)) throw new Error(`未知工具: ${name}`);
  if (!args || typeof args !== 'object' || Array.isArray(args)) throw new Error('参数必须为 JSON 对象');
  const specs = catalog[name].parameters;
  for (const key of Object.keys(args)) {
    if (!Object.hasOwn(specs, key)) throw new Error(`未知参数: ${key}`);
  }
  for (const [key, spec] of Object.entries(specs)) {
    if (!Object.hasOwn(args, key)) {
      if (spec.required) throw new Error(`缺少参数: ${key}`);
      continue;
    }
    const value = args[key];
    if (value === null && spec.default === null) continue;
    const type = spec.type === 'Dict[str, Any]' ? 'dict' : spec.type;
    const valid = {
      str: typeof value === 'string', bool: typeof value === 'boolean',
      int: Number.isSafeInteger(value), float: typeof value === 'number' && Number.isFinite(value),
      list: Array.isArray(value), dict: value !== null && typeof value === 'object' && !Array.isArray(value),
    }[type];
    if (!valid) throw new Error(`参数 ${key} 必须为 ${spec.type}`);
  }
  return Object.keys(specs).map(key => args[key]);
}
