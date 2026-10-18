(function () {
  'use strict';
  const P = window.Pentest;
  const { el, section, empty, badge, field, list, evidence, table } = P.dom;
  const { names, severityCounts, activityState, date } = P.model;

  function overview(view) {
    const box = section('01 / 摘要', view.status === 'completed' ? '已完成任务报告；结论以本版本留存证据为准。' : '阶段报告；任务尚未完成，不将当前覆盖视为完整测试。');
    box.append(el('p', 'report-summary multiline', view.report.summary || '报告尚未整理。以下展示当前已保存的事实，不生成示例结论。'));
    const assetStats = el('div', 'asset-stats');
    const kinds = [['资产总数', view.assets.length], ...Object.entries(names.kind).map(([kind, label]) =>
      [label, view.assets.filter(item => item.kind === kind).length])];
    kinds.forEach(([label, count]) => {
      const stat = el('div', 'asset-stat');
      stat.append(el('span', '', label), el('strong', '', count));
      assetStats.append(stat);
    });
    box.append(el('h3', 'subheading', '资产统计'), assetStats);
    const counts = severityCounts(view.findings);
    const stats = el('div', 'severity-stats');
    Object.entries(names.severity).forEach(([key, label]) => {
      const stat = el('div', `severity-stat severity-${key}`);
      stat.append(el('span', '', label), el('strong', '', counts[key]));
      stats.append(stat);
    });
    box.append(field('漏洞统计', '仅统计状态为“已确认”的漏洞；待验证、已排除和已修复项另列于漏洞清单。'), stats);
    box.append(el('h3', 'subheading', '关键发现'), list(view.report.keyFindings, '尚未整理关键发现。'));
    return box;
  }

  function targets(view) {
    const box = section('02 / 测试目标与范围');
    box.append(list(view.targets, '未记录测试目标'), field('测试范围', view.scope),
      field('排除范围', view.exclusions.length ? view.exclusions.join('\n') : '未记录排除项'),
      field('覆盖情况', view.report.coverage));
    return box;
  }

  function assets(view) {
    const box = section('03 / 资产清单', `共 ${view.assets.length} 项；完整列出当前版本记录，不受进度页筛选影响。`);
    Object.entries(names.kind).forEach(([key, label]) => {
      const items = view.assets.filter(item => item.kind === key);
      box.append(el('h3', 'subheading', `${label} · ${items.length}`));
      box.append(items.length ? table(['类型', '资产 / 标识', '说明与证据', '发现时间'], P.assetRows(items))
        : el('p', 'muted', '尚未记录此类资产。'));
    });
    return box;
  }

  function findings(view) {
    const box = section('04 / 漏洞清单', '每项独立保留验证过程、最小 PoC、影响和修复建议。PoC 仅展示，不执行。');
    view.findings.forEach(item => {
      const article = el('article', 'report-finding');
      const head = el('div', 'row-head');
      head.append(el('h3', '', `${item.id} / ${item.title}`), badge(names.severity[item.severity], item.severity),
        badge(names.finding[item.status], item.status));
      article.append(head, field('关联资产', item.assetIds.join('、')),
        field('描述', item.description), field('验证过程', item.validation),
        field('PoC / 最小复现', item.poc, true), field('影响', item.impact), field('修复建议', item.remediation),
        evidence(item.evidenceRefs));
      box.append(article);
    });
    if (!view.findings.length) box.append(empty('暂无漏洞记录', '未发现记录不等于已完成测试，也不构成无漏洞结论。'));
    return box;
  }

  function chains(view) {
    const box = section('05 / 攻击链分析', '已验证步骤与推测路径分开显示；工具容器可达不等于目标已成为跳板。');
    view.attackChains.forEach(chain => {
      const article = el('article', 'chain');
      const head = el('div', 'row-head');
      head.append(el('h3', '', `${chain.id} / ${chain.title}`), badge(names.chain[chain.status], chain.status));
      article.append(head);
      const steps = el('ol', 'chain-steps');
      chain.steps.forEach(step => {
        const line = el('li', step.verified ? 'verified-step' : 'hypothesis-step');
        line.append(el('strong', '', `${step.findingId} · ${step.verified ? '已验证步骤' : '未验证关联'}`),
          el('p', 'multiline', step.description));
        steps.append(line);
      });
      article.append(steps, field('链路影响', chain.impact), evidence(chain.evidenceRefs));
      box.append(article);
    });
    if (!view.attackChains.length) box.append(el('p', 'muted', '尚未保存攻击链，不推断已打通的路径。'));
    return box;
  }

  function limits(view, asOf) {
    const box = section('06 / 未验证项与覆盖限制');
    const unresolved = view.findings.filter(item => item.status === 'suspected')
      .map(item => `${item.id} / ${item.title}：待验证`);
    view.activities.filter(item => ['running', 'unknown'].includes(item.status)).forEach(item => {
      unresolved.push(`${item.tool} → ${item.target}：${activityState(item, asOf).label}`);
    });
    view.attackChains.filter(chain => chain.status !== 'verified').forEach(chain => {
      unresolved.push(`${chain.id} / ${chain.title}：${names.chain[chain.status]}`);
    });
    box.append(list(unresolved, '当前记录中没有待验证项；仍须结合测试范围与覆盖限制解读。'),
      el('h3', 'subheading', '覆盖限制'), list(view.report.limitations, '未记录覆盖限制；不代表没有限制。'),
      el('h3', 'subheading', '修复优先级与建议'), list(view.report.recommendations, '尚未整理总体修复建议。'));
    return box;
  }

  function report(view, asOf = Date.now()) {
    const box = el('div', 'report');
    const masthead = el('div', 'report-masthead');
    masthead.append(el('span', 'eyebrow', '渗透测试报告'), el('h2', '', view.title),
      el('p', 'muted', `版本 ${view.revision} · 更新于 ${date(view.updatedAt)} · ${names.status[view.status] || view.status}`));
    const exportHint = el('p', 'report-export-hint muted',
      'HTML 报告由 Agent 调用记录服务 export_report（format=html）导出到任务目录；此只读面板不直接下载。');
    box.append(masthead, exportHint, overview(view), targets(view), assets(view), findings(view), chains(view), limits(view, asOf));
    return box;
  }

  P.report = report;
}());
