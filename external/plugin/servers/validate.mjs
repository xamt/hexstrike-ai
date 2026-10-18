import path from 'node:path';
import { collections, viewSchema } from './schema.mjs';
import { fail } from './errors.mjs';
import { validatePlan } from './workflow.mjs';

export const MAX_BYTES = 1024 * 1024;
export const UUID = /^[a-f\d]{8}-[a-f\d]{4}-[1-8][a-f\d]{3}-[89ab][a-f\d]{3}-[a-f\d]{12}$/i;

/** Accept only task-relative evidence paths, never URLs or traversal segments. */
export function validEvidence(value) {
  return Boolean(value && !/[\\\x00-\x1f:]/.test(value) && !path.posix.isAbsolute(value)
    && value.split('/').every(part => part && part !== '.' && part !== '..'));
}

/** Validate schema formats without loading external schemas or executing content. */
function validFormat(value, format) {
  if (format === 'uuid') return UUID.test(value);
  if (format === 'evidence-path') return validEvidence(value);
  if (format === 'date-time') return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value));
  return true;
}

/** Validate primitive constraints shared by published input schemas and handlers. */
function primitive(value, schema, label) {
  const expected = schema.type;
  const valid = expected === 'integer' ? Number.isSafeInteger(value) : typeof value === expected;
  if (!valid) fail('VALIDATION_ERROR', `${label} 类型必须为 ${expected}。`);
  if (schema.enum && !schema.enum.includes(value)) fail('VALIDATION_ERROR', `${label} 不属于允许值。`);
  if (typeof value === 'string') {
    if (schema.minLength && value.length < schema.minLength) fail('VALIDATION_ERROR', `${label} 不得为空。`);
    if (schema.maxLength && value.length > schema.maxLength) fail('LIMIT_EXCEEDED', `${label} 超出长度上限。`);
    if (schema.pattern && !new RegExp(schema.pattern).test(value)) fail('VALIDATION_ERROR', `${label} 格式不正确。`);
    if (schema.format && !validFormat(value, schema.format)) fail('VALIDATION_ERROR', `${label} 格式不正确。`);
  }
  if (schema.minimum !== undefined && value < schema.minimum) fail('VALIDATION_ERROR', `${label} 低于允许值。`);
  if (schema.maximum !== undefined && value > schema.maximum) fail('VALIDATION_ERROR', `${label} 超出允许值。`);
}

/** Validate JSON values using the same schema published to the MCP host. */
export function validate(value, schema, label = '参数') {
  if (schema.type === 'object') {
    if (!value || typeof value !== 'object' || Array.isArray(value)) fail('VALIDATION_ERROR', `${label} 必须为对象。`);
    const missing = (schema.required ?? []).filter(key => !Object.hasOwn(value, key));
    const unknown = Object.keys(value).filter(key => !Object.hasOwn(schema.properties, key));
    if (missing.length || unknown.length) {
      const issues = [];
      if (missing.length) issues.push(`缺少必填字段 ${missing.join('、')}`);
      if (unknown.length) issues.push(`含未知字段 ${unknown.slice(0, 10).map(key => key.slice(0, 80)).join('、')}`);
      fail('VALIDATION_ERROR', `${label}：${issues.join('；')}。请按工具 inputSchema 提交，不使用字段别名。`);
    }
    if (Object.keys(value).length < (schema.minProperties ?? 0)) fail('VALIDATION_ERROR', '必须提供至少一个修改字段。');
    for (const [key, entry] of Object.entries(value)) {
      validate(entry, schema.properties[key], `${label}.${key}`);
    }
  } else if (schema.type === 'array') {
    if (!Array.isArray(value)) fail('VALIDATION_ERROR', `${label} 必须为数组。`);
    if (value.length > (schema.maxItems ?? Infinity)) fail('LIMIT_EXCEEDED', `${label} 超出记录数量上限。`);
    if (value.length < (schema.minItems ?? 0)) fail('VALIDATION_ERROR', `${label} 缺少必要记录。`);
    value.forEach((entry, index) => validate(entry, schema.items, `${label}[${index}]`));
  } else primitive(value, schema, label);
}

/** Enforce the one-MiB serialized payload limit before writing a snapshot. */
export function bounded(value) {
  let serialized;
  try { serialized = JSON.stringify(value); } catch { fail('VALIDATION_ERROR', '参数必须是可序列化JSON。'); }
  if (typeof serialized !== 'string') fail('VALIDATION_ERROR', '参数必须是JSON对象。');
  if (Buffer.byteLength(serialized, 'utf8') > MAX_BYTES) fail('LIMIT_EXCEEDED', '完整记录不得超过1MiB，请保留脱敏摘要并引用工作区证据文件。');
  return serialized;
}

/** Reject ambiguous duplicate identifiers within a single update or snapshot. */
export function uniqueRows(rows, name) {
  if (new Set(rows.map(row => row.id)).size !== rows.length) fail('VALIDATION_ERROR', `${name} 包含重复ID。`);
}

/** Validate parent references and detect self-references and cycles. */
function assetReferences(assets) {
  const index = new Map(assets.map(asset => [asset.id, asset]));
  for (const asset of assets) {
    if (asset.kind === 'service' && ['parentId', 'port', 'protocol', 'service'].some(key => !Object.hasOwn(asset, key))) fail('VALIDATION_ERROR', '服务资产必须包含parentId、port、protocol和service。');
    if (asset.dataProfile && asset.kind !== 'data') fail('VALIDATION_ERROR', '数据画像只能用于数据资产。');
    if (asset.dataProfile) {
      const { sampleStatus, redactedSample } = asset.dataProfile;
      if ((sampleStatus === 'redacted') !== Boolean(redactedSample)) {
        fail('VALIDATION_ERROR', '仅在已保存最小脱敏样例时将sampleStatus设为redacted；未取样时不得填写样例。');
      }
    }
    let node = asset;
    const seen = new Set([asset.id]);
    while (node.parentId) {
      if (!index.has(node.parentId) || seen.has(node.parentId)) fail('VALIDATION_ERROR', '资产父级不存在、自引用或成环。');
      seen.add(node.parentId);
      node = index.get(node.parentId);
    }
  }
  return index;
}

/** Require minimal proof before a finding can count as confirmed. */
function findingReferences(findings, assets) {
  for (const finding of findings) {
    if (finding.assetIds.some(id => !assets.has(id))) fail('VALIDATION_ERROR', '漏洞引用了不存在的资产。');
    if (finding.status === 'confirmed' && (['validation', 'poc', 'impact', 'remediation'].some(key => !finding[key].trim()) || !finding.evidenceRefs.length)) fail('VALIDATION_ERROR', '已确认漏洞必须包含验证、PoC、影响、修复和证据引用。');
  }
  return new Map(findings.map(finding => [finding.id, finding]));
}

/** Check the complete merged view, not only individual update rows. */
export function validateView(view) {
  validate(view, viewSchema, 'view');
  validatePlan(view);
  for (const key of Object.keys(collections)) {
    uniqueRows(view[key], key);
  }
  const assets = assetReferences(view.assets);
  const findings = findingReferences(view.findings, assets);
  for (const chain of view.attackChains) {
    for (const step of chain.steps) {
      const finding = findings.get(step.findingId);
      if (!finding) fail('VALIDATION_ERROR', '攻击链引用了不存在的漏洞。');
      if (step.verified && !['confirmed', 'remediated'].includes(finding.status)) fail('VALIDATION_ERROR', '已验证步骤必须关联已确认或已修复漏洞。');
      if (chain.status === 'verified' && !step.verified) fail('VALIDATION_ERROR', '已验证攻击链不得包含未验证步骤。');
    }
  }
  for (const activity of view.activities) if (activity.finishedAt && Date.parse(activity.finishedAt) < Date.parse(activity.startedAt)) fail('VALIDATION_ERROR', '工具结束时间不得早于开始时间。');
  if (view.assetCount !== view.assets.length
    || view.confirmedCount !== view.findings.filter(item => item.status === 'confirmed').length
    || view.suspectedCount !== view.findings.filter(item => item.status === 'suspected').length
    || view.runningCount !== view.activities.filter(item => item.status === 'running').length) fail('CORRUPT_RECORD', '记录统计与明细不一致。');
  bounded(view);
}
