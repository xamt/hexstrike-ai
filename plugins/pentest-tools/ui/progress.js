(function () {
  'use strict';
  const P = window.Pentest;
  const { el, section, empty, badge, select, pager, table, evidence } = P.dom;
  const { names, paginate, activityState, date, searchAsset } = P.model;

  function assetRows(assets) {
    return assets.map(asset => {
      const identity = el('div', 'identity');
      identity.append(el('strong', 'mono', asset.value), el('small', 'muted', asset.id));
      const detail = el('div');
      detail.append(el('p', '', asset.description || '未记录描述'));
      if (asset.kind === 'service') {
        detail.append(el('p', 'mono muted', `${asset.protocol}/${asset.port} · ${asset.service} · 所属 ${asset.parentId}`));
      }
      if (asset.sensitivity) detail.append(el('p', 'muted', `敏感性：${asset.sensitivity}`));
      detail.append(evidence(asset.evidenceRefs));
      return [names.kind[asset.kind] || asset.kind, identity, detail, date(asset.observedAt)];
    });
  }

  function assets(view, state, update) {
    const box = section('资产清单', '四类资产统一归档；数据资产仅展示类别、位置和脱敏证据。');
    const controls = el('div', 'filters');
    controls.append(select('资产类型', 'asset-kind', { '': '全部类型', ...names.kind }, state.kind, value => {
      update({ kind: value, assetPage: 1 });
    }));
    const label = el('label', 'control grow');
    label.append(el('span', '', '检索资产'));
    const input = el('input');
    input.id = 'asset-search';
    input.type = 'search';
    input.placeholder = 'IP、域名、服务或描述';
    input.value = state.search;
    input.addEventListener('input', () => update({ search: input.value, assetPage: 1 }));
    label.append(input);
    controls.append(label);
    box.append(controls);
    const filtered = view.assets.filter(item => (!state.kind || item.kind === state.kind) && searchAsset(item, state.search));
    const page = paginate(filtered, state.assetPage, 12);
    box.append(page.total ? table(['类型', '资产 / 标识', '说明与证据', '发现时间'], assetRows(page.items))
      : empty('暂无匹配资产', view.assets.length ? '调整筛选条件查看其他记录。' : 'Agent 保存资产记录后会在这里显示，不代表目标没有资产。'));
    box.append(pager(page, 'assets', value => update({ assetPage: value })));
    return box;
  }

  function findings(view, state, update) {
    const box = section('漏洞与线索', '待验证线索不计入已确认漏洞；等级由证据支持，不以工具告警代替结论。');
    const controls = el('div', 'filters');
    controls.append(select('验证状态', 'finding-status', { '': '全部状态', ...names.finding }, state.findingStatus,
      value => update({ findingStatus: value, findingPage: 1 })));
    controls.append(select('风险等级', 'finding-severity', { '': '全部等级', ...names.severity }, state.severity,
      value => update({ severity: value, findingPage: 1 })));
    box.append(controls);
    const filtered = view.findings.filter(item => (!state.findingStatus || item.status === state.findingStatus)
      && (!state.severity || item.severity === state.severity));
    const page = paginate(filtered, state.findingPage, 6);
    page.items.forEach(item => {
      const row = el('article', 'finding-row');
      const head = el('div', 'row-head');
      head.append(badge(names.severity[item.severity], item.severity), el('h3', '', item.title),
        badge(names.finding[item.status], item.status));
      row.append(head, el('p', 'muted mono', `${item.id} · 关联资产 ${item.assetIds.join('、') || '未记录'}`),
        el('p', 'multiline', item.description), evidence(item.evidenceRefs));
      box.append(row);
    });
    if (!page.total) box.append(empty('暂无匹配漏洞记录', view.findings.length ? '调整筛选条件查看其他记录。' : '尚未保存发现；这不是“目标安全”的结论。'));
    box.append(pager(page, 'findings', value => update({ findingPage: value })));
    return box;
  }

  function currentTools(view, asOf) {
    const box = section('当前工具（Agent 记录）', '仅展示最新 3 条执行中或状态未知记录；不是远端进程监控，完整历史见页面下方。');
    box.classList.add('current-tools');
    const current = P.model.currentActivities(view.activities);
    current.forEach(item => {
      const status = activityState(item, asOf);
      const row = el('article', 'current-tool');
      const identity = el('div', 'current-tool-identity');
      identity.append(el('h3', 'mono', item.tool), el('p', 'muted', `目标：${item.target}`));
      row.append(identity, badge(status.label, status.tone));
      box.append(row);
    });
    if (!current.length) box.append(el('p', 'muted', '暂无执行中或状态未知的记录；缺少记录不代表工具未执行。'));
    return box;
  }

  function activities(view, state, update, asOf) {
    const box = section('Agent 执行记录 · 非进程监控', '显示 Agent 调用工具前后保存的记录。执行中超过 5 分钟标记待确认，不代表任务被停止。');
    const ordered = [...view.activities].sort((a, b) => Date.parse(b.startedAt) - Date.parse(a.startedAt));
    const page = paginate(ordered, state.activityPage, 8);
    page.items.forEach(item => {
      const status = activityState(item, asOf);
      const row = el('article', 'activity');
      const head = el('div', 'row-head');
      head.append(badge(status.label, status.tone), el('h3', 'mono', item.tool));
      row.append(head, el('p', 'muted', `目标：${item.target} · 开始：${date(item.startedAt)}`),
        el('p', 'multiline', item.summary || '尚未保存执行摘要'));
      if (item.finishedAt) row.append(el('p', 'muted', `结束：${date(item.finishedAt)}`));
      row.append(evidence(item.evidenceRefs));
      box.append(row);
    });
    if (!page.total) box.append(empty('暂无工具执行记录', '本面板不会发起扫描。由 Agent 通过已连接的远端 MCP 执行并留存记录。'));
    box.append(pager(page, 'activities', value => update({ activityPage: value })));
    return box;
  }

  function progress(view, state, update, asOf = Date.now()) {
    const box = el('div');
    const metrics = el('div', 'metrics');
    const confirmed = view.findings.filter(item => item.status === 'confirmed').length;
    const suspected = view.findings.filter(item => item.status === 'suspected').length;
    const active = view.activities.filter(item => item.status === 'running').length;
    [['已发现资产', view.assets.length], ['已确认漏洞', confirmed], ['待验证线索', suspected], ['执行中记录', active]].forEach(([label, count]) => {
      const metric = el('div', 'metric');
      metric.append(el('span', 'muted', label), el('strong', '', count));
      metrics.append(metric);
    });
    box.append(P.testPlan(view), metrics, currentTools(view, asOf), assets(view, state, update),
      findings(view, state, update), activities(view, state, update, asOf));
    return box;
  }

  P.progress = progress;
  P.assetRows = assetRows;
}());
