const severityLabels = { critical: '严重', high: '高危', medium: '中危', low: '低危', info: '信息' };
const findingLabels = { suspected: '待验证', confirmed: '已确认', rejected: '已排除', remediated: '已修复' };
const assetLabels = { ip: 'IP', domain: '域名', service: '端口与服务', data: '数据资产' };
const chainLabels = { hypothesis: '假设', partial: '部分验证', verified: '已验证' };

/** Escape untrusted Markdown content without interpreting HTML or links. */
export function escapeMarkdown(value) {
  return String(value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/([\\`*_{}\[\]()#+.!|~-])/g, '\\$1');
}

/** Render a heading without allowing injected headings through line breaks. */
function heading(value) {
  return escapeMarkdown(String(value).replace(/[\r\n]+/g, ' '));
}

/** Render plain text bullets and an explicit empty-state message. */
function bullets(values, empty = '暂无记录。') {
  return values.length ? values.map(value => `- ${escapeMarkdown(value).replace(/\n/g, '\n  ')}`).join('\n') : empty;
}

/** Fence untrusted PoC with more backticks than any run in its content. */
function pocBlock(value) {
  if (!value.trim()) return '未保存PoC，不视为已经验证。';
  let longest = 0;
  for (const match of value.matchAll(/`+/g)) longest = Math.max(longest, match[0].length);
  const fence = '`'.repeat(Math.max(3, longest + 1));
  return `${fence}text\n${value}\n${fence}`;
}

/** Render each saved asset with its classification and evidence references. */
function assets(view) {
  if (!view.assets.length) return '尚未记录资产。';
  return view.assets.map(asset => [
    `### ${heading(asset.id)} · ${assetLabels[asset.kind]} · ${heading(asset.value)}`,
    escapeMarkdown(asset.description) || '未填写描述。',
    `观察时间：${escapeMarkdown(asset.observedAt)}`,
    asset.parentId ? `父级资产：${escapeMarkdown(asset.parentId)}` : '',
    asset.port ? `端口/协议/服务：${asset.port} / ${escapeMarkdown(asset.protocol ?? '')} / ${escapeMarkdown(asset.service ?? '')}` : '',
    asset.sensitivity ? `敏感性：${escapeMarkdown(asset.sensitivity)}` : '',
    '证据引用：', bullets(asset.evidenceRefs, '未记录证据引用。'),
  ].filter(Boolean).join('\n\n')).join('\n\n');
}

/** Render all findings without upgrading suspected or rejected items to confirmed. */
function findings(view) {
  if (!view.findings.length) return '尚未记录漏洞；不代表已证明不存在漏洞。';
  return view.findings.map(finding => [
    `### ${heading(finding.id)} · ${heading(finding.title)}`,
    `等级：${severityLabels[finding.severity]}；状态：${findingLabels[finding.status]}`,
    `关联资产：${finding.assetIds.map(heading).join('、') || '未关联资产'}`,
    '#### 描述', escapeMarkdown(finding.description) || '未填写。',
    '#### 验证过程', escapeMarkdown(finding.validation) || '未验证。',
    '#### PoC', pocBlock(finding.poc),
    '#### 影响', escapeMarkdown(finding.impact) || '未确认。',
    '#### 修复建议', escapeMarkdown(finding.remediation) || '未整理。',
    '#### 证据引用', bullets(finding.evidenceRefs, '未记录证据引用。'),
  ].join('\n\n')).join('\n\n');
}

/** Render attack-chain steps with their actual verification state. */
function chains(view) {
  if (!view.attackChains.length) return '尚未记录攻击链，不推断已打通。';
  return view.attackChains.map(chain => [
    `### ${heading(chain.id)} · ${heading(chain.title)}（${chainLabels[chain.status]}）`,
    ...chain.steps.map((step, index) => `${index + 1}. ${step.verified ? '已验证' : '未验证'} · ${heading(step.findingId)}：${escapeMarkdown(step.description)}`),
    `影响：${escapeMarkdown(chain.impact) || '尚未明确。'}`, '证据引用：', bullets(chain.evidenceRefs),
  ].join('\n\n')).join('\n\n');
}

/** Summarize only confirmed findings in severity counts, with other states separate. */
function statistics(view) {
  const confirmed = view.findings.filter(finding => finding.status === 'confirmed');
  return [
    `已确认漏洞：${confirmed.length}；待验证：${view.suspectedCount}；已修复：${view.findings.filter(item => item.status === 'remediated').length}；已排除：${view.findings.filter(item => item.status === 'rejected').length}。`,
    ...Object.entries(severityLabels).map(([severity, label]) => `- ${label}：${confirmed.filter(item => item.severity === severity).length}`),
  ].join('\n');
}

/** Include uncertainty and tool-reported states rather than inventing execution success. */
function uncertainties(view) {
  const pending = view.findings.filter(item => item.status === 'suspected').map(item => `${item.id}：${item.title}`);
  const activities = view.activities.filter(item => ['running', 'unknown'].includes(item.status))
    .map(item => `${item.id}：${item.tool}；目标${item.target}；记录状态${item.status}（Agent报告，非远端进程遥测）`);
  return [
    '### 未验证漏洞', bullets(pending, '无已记录的待验证漏洞；不代表全部目标已覆盖。'),
    '### 未确认工具活动', bullets(activities, '无已记录的未确认工具活动。'),
    '### 测试覆盖', escapeMarkdown(view.report.coverage) || '尚未整理覆盖范围。',
    '### 限制', bullets(view.report.limitations, '未填写限制，不代表不存在限制。'),
  ].join('\n\n');
}

/** Build a complete deterministic report from one immutable engagement version. */
export function renderReport(view) {
  const kind = view.status === 'completed' ? '渗透测试报告' : '渗透测试阶段报告';
  return [
    `# ${kind}：${heading(view.title)}`,
    `任务：${view.taskId}；版本：${view.revision}；记录更新时间：${escapeMarkdown(view.updatedAt)}`,
    '本报告仅整理已保存、已脱敏的记录，不发起扫描；工具执行状态由Agent报告，不是远端进程遥测。',
    '## 摘要', escapeMarkdown(view.report.summary) || '报告尚未整理。',
    '## 漏洞统计', statistics(view),
    '## 关键发现', bullets(view.report.keyFindings, '尚未整理关键发现。'),
    '## 测试目标', bullets(view.targets),
    '### 范围', escapeMarkdown(view.scope),
    '### 排除项', bullets(view.exclusions, '未填写排除项。'),
    '## 资产清单', assets(view),
    '## 漏洞详情', findings(view),
    '## 攻击链分析', chains(view),
    '## 修复建议', bullets(view.report.recommendations, '尚未整理整体修复建议；逐项建议见漏洞详情。'),
    '## 未验证项与覆盖限制', uncertainties(view),
  ].join('\n\n') + '\n';
}
