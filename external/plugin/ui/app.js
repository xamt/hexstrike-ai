(function () {
  'use strict';
  const P = window.Pentest;
  const panel = window.DataAgentPanel;
  const byId = id => document.getElementById(id);
  const initial = () => ({ activityPage: 1 });
  let filters = initial();
  let latest;
  let view;
  let taskId = '';
  let busy = false;
  let ready = false;
  const tabs = ['plan', 'report'];
  let tab = 'plan';
  let localError = '';
  let requestedTask = '';

  function runtime() {
    return latest?.document?.data?.runtime || {};
  }

  function queryError() {
    return localError || runtime().queries?.['engagement-view']?.error || runtime().dataSources?.view?.error;
  }

  function updateFilters(patch) {
    filters = { ...filters, ...patch };
    renderContent();
  }

  function renderContent() {
    const active = document.activeElement;
    const focusId = active?.id;
    const selection = typeof active?.selectionStart === 'number' ? active.selectionStart : undefined;
    const content = byId('panel-content');
    const asOf = view && P.model.displayTime(latest?.mode, view);
    if (view) {
      const pages = { plan: () => P.planProgress(view, filters, updateFilters, asOf,
        { stale: Boolean(queryError()), snapshot: latest?.mode === 'snapshot' }),
        report: () => P.report(view, asOf) };
      content.replaceChildren(pages[tab]());
    }
    else content.replaceChildren(P.dom.empty(
      latest?.mode === 'snapshot' ? '快照未保存任务数据' : queryError() ? '未能读取任务记录' : taskId ? '等待任务记录' : '尚未选择测试任务',
      latest?.mode === 'snapshot' ? '历史快照不会发起查询；本地筛选和页签仍可使用。'
        : queryError() ? '请按上方错误提示核对目录与任务；读取失败不代表没有发现资产或漏洞。'
        : taskId ? '正在等待本地记录服务返回当前任务；不会展示其他任务的数据。'
          : '工作台已打开，等待 Agent 确认目标与范围后建立任务。打开页面不会自动连接远端 MCP 或执行测试。',
    ));
    const replacement = focusId && byId(focusId);
    if (replacement && replacement !== active && content.contains(replacement)) {
      replacement.focus({ preventScroll: true });
      if (selection !== undefined && replacement.setSelectionRange) replacement.setSelectionRange(selection, selection);
    }
    updateRecordAge();
  }

  function updateRecordAge() {
    const node = byId('record-age');
    if (node && view) node.textContent = latest?.mode === 'snapshot' ? '历史快照' : P.model.recordAge(view.updatedAt);
  }

  function renderHeading() {
    const context = runtime().dataSources?.context?.value;
    byId('task-title').textContent = view?.title || context?.title || '等待任务上下文';
    byId('task-meta').textContent = view
      ? `${P.model.names.status[view.status] || view.status} · ${view.phase || '阶段未记录'} · 版本 ${view.revision} · 更新于 ${P.model.date(view.updatedAt)}`
      : taskId ? `任务 ${taskId} · 尚无当前任务的可用数据` : '连接宿主面板后读取真实记录。';
    const refresh = byId('refresh');
    refresh.disabled = !ready || !taskId || latest?.mode !== 'live' || busy;
    refresh.textContent = busy ? '读取中…' : '刷新记录';
    refresh.setAttribute('aria-busy', String(busy));
    const error = queryError();
    const notice = byId('notice');
    notice.className = error ? 'notice error' : 'notice';
    if (error) notice.textContent = `记录读取失败：${String(error)}。${view ? `保留旧数据，记录时间 ${P.model.date(view.updatedAt)}。` : '尚无可用数据。'}${P.model.recordErrorHint(error)}`;
    else if (latest?.mode === 'snapshot') notice.textContent = '历史快照 · 内容已冻结，不发起远端请求；仍可切换页签、筛选和分页。';
    else notice.textContent = '只读工作台 · 宿主每 10 秒轮询记录。远端 pentest-tools MCP 的连接状态不由此页检测；未连接时不能执行测试。';
  }

  function receive(state) {
    if (!state) return;
    latest = state;
    const sources = runtime().dataSources || {};
    const incoming = sources.view?.value;
    const nextTask = sources.context?.value?.taskId || (state.mode === 'snapshot' ? incoming?.taskId : '') || '';
    if (nextTask !== taskId) {
      taskId = nextTask;
      view = undefined;
      localError = '';
      filters = initial();
      activate('plan');
    }
    if (taskId && incoming?.taskId === taskId && incoming.schemaVersion === 1) view = incoming;
    renderHeading();
    renderContent();
    if (ready && state.mode === 'live' && taskId && taskId !== requestedTask && !busy) void load();
  }

  async function load() {
    if (!ready || latest?.mode !== 'live' || !taskId || busy) return;
    const requested = taskId;
    requestedTask = requested;
    busy = true;
    localError = '';
    renderHeading();
    try {
      await panel.query('engagement-view', { task_id: requested });
    } catch (error) {
      if (requested === taskId) localError = error instanceof Error ? error.message : String(error);
    } finally {
      busy = false;
      receive(panel.getState());
    }
  }

  function activate(name, focus = false) {
    tab = name;
    tabs.forEach(value => {
      const button = byId(`tab-${value}`);
      button.setAttribute('aria-selected', String(name === value));
      button.tabIndex = name === value ? 0 : -1;
    });
    byId('panel-content').setAttribute('aria-labelledby', `tab-${name}`);
    renderContent();
    if (focus) byId(`tab-${name}`).focus();
  }

  function bindTabs() {
    tabs.forEach(name => {
      const button = byId(`tab-${name}`);
      button.addEventListener('click', () => activate(name));
      button.addEventListener('keydown', event => {
        const index = tabs.indexOf(name);
        const next = { ArrowLeft: tabs[(index + tabs.length - 1) % tabs.length],
          ArrowRight: tabs[(index + 1) % tabs.length], Home: tabs[0], End: tabs.at(-1) }[event.key];
        if (next) { event.preventDefault(); activate(next, true); }
      });
    });
  }

  bindTabs();
  byId('refresh').addEventListener('click', load);
  renderContent();
  if (!panel) {
    byId('notice').className = 'notice error';
    byId('notice').textContent = '未连接 DataAgent 面板宿主。请从已安装插件打开工作台，并启用 records MCP 与远端 pentest-tools MCP；此页面不会直接调用 HTTP 接口。';
    return;
  }
  const ageTimer = window.setInterval(updateRecordAge, 15000);
  window.addEventListener('pagehide', () => window.clearInterval(ageTimer), { once: true });
  const unsubscribe = panel.subscribe(receive);
  window.addEventListener('pagehide', unsubscribe, { once: true });
  panel.ready.then(state => { ready = true; receive(state || panel.getState()); }).catch(error => {
    byId('notice').className = 'notice error';
    byId('notice').textContent = `宿主初始化失败：${error instanceof Error ? error.message : String(error)}`;
  });
}());
