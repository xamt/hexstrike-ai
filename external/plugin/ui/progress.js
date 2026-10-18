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

  /** 最新进展仅取留存快照；陈旧运行记录不得称作正在执行的远端进程。 */
  function currentWork(view, asOf, context) {
    const box = el('section', 'now-card');
    box.setAttribute('aria-label', '当前渗透进展');
    const runningSteps = (view.planSteps || []).filter(step => step.status === 'running');
    const phase = view.status === 'paused' ? '已暂停' : view.status === 'completed' ? '测试已完成'
      : runningSteps.length ? runningSteps.map(step => step.title).join(' · ')
        : view.status === 'planned' ? '等待开始' : view.phase || '等待新的步骤状态';
    const age = asOf - Date.parse(view.updatedAt);
    const stale = context.stale || (Number.isFinite(age) && age > 300000);
    const label = context.snapshot ? '历史快照记录' : stale ? '上次记录的工作'
      : view.status === 'running' && runningSteps.length ? '当前正在进行' : '当前进展';
    const main = el('div', 'now-main');
    main.append(el('p', 'now-label', label), el('h2', '', phase));
    if (view.phase && view.phase !== phase) main.append(el('p', 'now-phase', `Agent 记录阶段：${view.phase}`));
    const latest = [...view.activities].sort((a, b) => Date.parse(b.startedAt) - Date.parse(a.startedAt))[0];
    const detail = el('div', 'now-detail');
    if (view.status === 'paused') detail.append(el('p', '', '停止新的目标测试；已有远端进程是否结束仍须核实。'));
    else if (view.status === 'completed') detail.append(el('p', '', '已完成测试记录；查看报告核对最终结论与未验证项。'));
    else if (latest) {
      const state = activityState(latest, asOf);
      detail.append(el('span', 'now-detail-label', '最近工具记录 · Agent 留存'),
        el('p', 'mono', `${latest.tool} · ${latest.target}`),
        el('p', '', latest.summary || '尚未保存执行摘要'), badge(state.label, state.tone));
    } else detail.append(el('p', '', '等待 Agent 保存工具执行记录；此处不会主动发起扫描。'));
    box.append(main, detail);
    const timestamp = el('p', 'now-timestamp');
    timestamp.append(el('span', '', `记录于 ${date(view.updatedAt)} · `), el('span', '', ''));
    timestamp.lastChild.id = 'record-age';
    timestamp.append(el('span', '', ' · 10 秒只读轮询，非远端进程心跳'));
    box.append(timestamp);
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

  function progress(view, state, update, asOf = Date.now(), context = {}) {
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
    box.append(currentWork(view, asOf, context), metrics, assets(view, state, update),
      findings(view, state, update), activities(view, state, update, asOf));
    return box;
  }

  P.progress = progress;
  P.assetRows = assetRows;
}());
