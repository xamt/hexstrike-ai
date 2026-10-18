const kindLabels = { ip: 'IP', domain: '域名', service: '端口与服务', data: '数据资产' };
const severityLabels = { critical: '严重', high: '高危', medium: '中危', low: '低危', info: '信息' };
const statusLabels = { suspected: '待验证', confirmed: '已确认', rejected: '已排除', remediated: '已修复' };

/** Escape every stored value before placing it in the standalone report. */
function h(value) {
  return String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function list(items, fallback = '暂无记录。') {
  return items.length ? `<ul>${items.map(item => `<li>${h(item)}</li>`).join('')}</ul>` : `<p class="muted">${fallback}</p>`;
}

function field(label, value, code = false) {
  return `<div class="field"><h4>${label}</h4><${code ? 'pre' : 'p'}>${h(value) || '未记录。'}</${code ? 'pre' : 'p'}></div>`;
}

function section(title, body) {
  return `<section><h2>${title}</h2>${body}</section>`;
}

function assetStatistics(view) {
  const counts = Object.entries(kindLabels).map(([kind, label]) => `<li><span>${label}</span><strong>${view.assets.filter(item => item.kind === kind).length}</strong></li>`);
  return `<ul class="stats"><li><span>资产总数</span><strong>${view.assets.length}</strong></li>${counts.join('')}</ul>`;
}

function dataProfile(asset) {
  if (asset.kind !== 'data') return '';
  const profile = asset.dataProfile;
  if (!profile) return '<p class="muted">规模未记录；数据类别未记录；样例状态未记录；暴露范围未记录。</p>';
  const sampleLabels = { not_sampled: '未取样', metadata_only: '仅观察元数据', redacted: '已保存最小脱敏样例' };
  return `${field('规模', profile.scale)}${field('数据类别', profile.categories.join('、') || '未确认')}
    ${field('样例状态', sampleLabels[profile.sampleStatus])}
    ${profile.redactedSample ? field('脱敏样例', profile.redactedSample, true) : ''}
    ${field('暴露范围', profile.exposure)}`;
}

function assets(view) {
  if (!view.assets.length) return '<p class="muted">尚未记录资产。</p>';
  return view.assets.map(asset => `<article><h3>${h(asset.value)} <small>${kindLabels[asset.kind]}</small></h3>
    ${field('标识', asset.id)}${field('说明', asset.description)}
    ${asset.kind === 'service' ? field('端口与服务', `${asset.protocol}/${asset.port} · ${asset.service} · 所属 ${asset.parentId}`) : ''}
    ${asset.sensitivity ? field('敏感性', asset.sensitivity) : ''}
    ${dataProfile(asset)}${field('发现时间', asset.observedAt)}${field('证据引用', asset.evidenceRefs.join('、'))}</article>`).join('');
}

function findings(view) {
  if (!view.findings.length) return '<p class="muted">尚未记录漏洞；不代表已证明不存在漏洞。</p>';
  return view.findings.map(item => `<article><h3>${h(item.id)} · ${h(item.title)}</h3>
    <p class="tags">${severityLabels[item.severity]} · ${statusLabels[item.status]}</p>
    ${field('关联资产', item.assetIds.join('、'))}${field('描述', item.description)}
    ${field('验证过程', item.validation)}${field('PoC / 最小复现', item.poc, true)}
    ${field('影响', item.impact)}${field('修复建议', item.remediation)}
    ${field('证据引用', item.evidenceRefs.join('、'))}</article>`).join('');
}

function chains(view) {
  if (!view.attackChains.length) return '<p class="muted">尚未记录攻击链，不推断已打通。</p>';
  return view.attackChains.map(chain => `<article><h3>${h(chain.id)} · ${h(chain.title)}</h3>
    ${field('验证状态', chain.status)}<ol>${chain.steps.map(step => `<li>${step.verified ? '已验证' : '未验证'} · ${h(step.findingId)}：${h(step.description)}</li>`).join('')}</ol>
    ${field('影响', chain.impact)}${field('证据引用', chain.evidenceRefs.join('、'))}</article>`).join('');
}

function unresolved(view) {
  const pending = view.findings.filter(item => item.status === 'suspected').map(item => `${item.id}：${item.title}`);
  const activities = view.activities.filter(item => ['running', 'unknown'].includes(item.status))
    .map(item => `${item.tool} → ${item.target}：Agent 记录状态 ${item.status}，非远端进程遥测`);
  const chainsPending = view.attackChains.filter(item => item.status !== 'verified').map(item => `${item.id}：${item.title}，${item.status}`);
  return `<h3>待验证线索与活动</h3>${list([...pending, ...activities, ...chainsPending], '当前记录中没有待验证项；仍须结合覆盖范围解读。')}
    ${field('测试覆盖', view.report.coverage)}<h3>覆盖限制</h3>${list(view.report.limitations, '未填写限制，不代表不存在限制。')}`;
}

/** Render a self-contained, inert HTML report from one saved engagement version. */
export function renderHtmlReport(view) {
  const confirmed = view.findings.filter(item => item.status === 'confirmed');
  const severity = Object.entries(severityLabels).map(([key, label]) => `<li><span>${label}</span><strong>${confirmed.filter(item => item.severity === key).length}</strong></li>`);
  const kind = view.status === 'completed' ? '渗透测试报告' : '渗透测试阶段报告';
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'none'">
<title>${h(kind)} · ${h(view.title)}</title><style>
:root{color-scheme:light;font-family:system-ui,-apple-system,"PingFang SC",sans-serif;color:#173046;background:#edf2f3}
*{box-sizing:border-box}body{margin:0}main{max-width:960px;margin:auto;padding:44px 28px 90px}header{border-bottom:4px solid #2b786e;padding-bottom:28px;margin-bottom:32px}
.eyebrow{font-size:12px;letter-spacing:.14em;color:#2b786e;font-weight:700}h1{font-size:34px;margin:10px 0}h2{font-size:21px;border-bottom:1px solid #c6d4d7;padding-bottom:10px}
h3{font-size:16px}h4{font-size:12px;color:#526d78;margin:0 0 4px}section{background:#fff;padding:22px 26px;margin:18px 0;border:1px solid #d9e3e5;border-radius:10px}
article{border-top:1px solid #e2e9e9;padding:12px 0}.field{margin:12px 0}p,li{line-height:1.65;white-space:pre-wrap;overflow-wrap:anywhere}.muted,small{color:#58717b}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f6f6;padding:12px;border-radius:6px;font-size:12px}.stats{list-style:none;display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;padding:0}
.stats li{background:#edf5f3;border-radius:6px;padding:12px;display:flex;justify-content:space-between;gap:8px}.stats strong{font-size:20px;color:#155a50}.tags{color:#2b786e;font-weight:700}
@media print{body{background:#fff}main{padding:0}section{break-inside:avoid;border:0;border-bottom:1px solid #ddd;padding:14px 0}article{break-inside:avoid}}
</style></head><body><main><header><p class="eyebrow">${h(kind)}</p><h1>${h(view.title)}</h1>
<p>任务 ${h(view.taskId)} · 版本 ${view.revision} · 更新于 ${h(view.updatedAt)}</p>
<p class="muted">本报告仅整理已保存、已脱敏的记录，不发起扫描；工具活动由 Agent 记录，不代表远端进程状态。</p></header>
${section('摘要', `<p>${h(view.report.summary) || '报告尚未整理。'}</p><h3>资产统计</h3>${assetStatistics(view)}<h3>漏洞统计</h3><ul class="stats"><li><span>已确认</span><strong>${confirmed.length}</strong></li><li><span>待验证</span><strong>${view.suspectedCount}</strong></li>${severity.join('')}</ul><h3>关键发现</h3>${list(view.report.keyFindings, '尚未整理关键发现。')}`)}
${section('测试目标与范围', `${list(view.targets)}${field('测试范围', view.scope)}${field('排除范围', view.exclusions.join('、'))}`)}
${section('资产清单', assets(view))}${section('漏洞详情', findings(view))}
${section('攻击链分析', chains(view))}${section('修复建议', list(view.report.recommendations, '尚未整理总体修复建议；逐项建议见漏洞清单。'))}
${section('未验证项与覆盖限制', unresolved(view))}</main></body></html>\n`;
}
