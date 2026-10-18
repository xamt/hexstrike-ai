(function () {
  'use strict';
  const P = window.Pentest;
  const { el, section, empty, badge, evidence } = P.dom;
  const labels = { pending: '待执行', running: '执行中', completed: '已完成', blocked: '受阻' };
  const tones = { pending: 'info', running: 'running', completed: 'succeeded', blocked: 'failed' };

  /** 用真实步骤状态绘制阶段轨迹，只有 running 状态可标为当前阶段。 */
  function stageTrack(steps, context) {
    const wrap = el('div', 'stage-visual');
    const active = steps.filter(step => step.status === 'running');
    const now = el('div', 'stage-now');
    const label = context.snapshot ? '快照时的阶段' : context.stale ? '上次记录的阶段' : '当前阶段';
    now.append(el('span', 'eyebrow', active.length ? label : '阶段状态'),
      el('strong', '', active.length ? active.map(step => step.title).join(' · ')
        : steps.every(step => step.status === 'completed') ? '已记录阶段均已完成' : '暂无执行中的阶段'));
    wrap.append(now);
    const track = el('ol', 'stage-track');
    track.setAttribute('aria-label', '测试计划阶段轨迹');
    steps.forEach((step, index) => {
      const stage = el('li', 'stage');
      stage.dataset.status = step.status;
      if (step.id === active[0]?.id) stage.setAttribute('aria-current', 'step');
      stage.append(el('span', 'stage-index', String(index + 1).padStart(2, '0')),
        el('span', 'stage-title', step.title),
        el('span', 'stage-status', labels[step.status] || '状态未知'));
      track.append(stage);
    });
    wrap.append(track);
    return wrap;
  }

  /** 展示最近留存的MCP检查，不将其伪装成实时探测。 */
  function preflight(check) {
    const box = el('div', `preflight ${check?.status === 'failed' ? 'preflight-failed' : ''}`);
    if (!check) {
      box.append(el('strong', '', 'MCP 尚未检查'), el('p', 'muted', '实际测试前必须通过健康检查；只制定计划或离线写报告不调用远端服务。'));
      return box;
    }
    box.append(el('strong', '', check.status === 'passed' ? 'MCP 最近检查通过' : 'MCP 检查未通过 · 已暂停测试派发'),
      el('p', 'muted', `检查于 ${P.model.date(check.checkedAt)} · Agent 留存，非实时监控`),
      el('p', 'mono', `${check.server} · ${check.tool}`), el('p', 'multiline', check.summary));
    if (check.status === 'failed') box.append(el('p', 'muted', '不再发起测试；已有远端进程是否结束仍须核实，不自动重放。'));
    return box;
  }

  /** 以稳定ID和明确状态呈现步骤，完成依据和受阻原因保持可追溯。 */
  function stepsList(steps) {
    const list = el('ol', 'plan-steps');
    for (const step of steps) {
      const row = el('li', 'plan-step');
      row.dataset.stepId = step.id;
      const head = el('div', 'row-head');
      head.append(el('h3', '', step.title), badge(labels[step.status] || '状态未知', tones[step.status] || 'unknown'));
      row.append(head, el('p', 'mono muted', step.id));
      if (step.summary) row.append(el('p', 'multiline', step.summary));
      if (step.evidenceRefs.length) row.append(evidence(step.evidenceRefs));
      list.append(row);
    }
    return list;
  }

  /** 渲染同一原子快照中的计划、健康检查与步骤状态。 */
  function testPlan(view, context = {}) {
    const box = section('渗透测试计划', '沿已保存的步骤推进；状态由 Agent 按实际执行更新，一次工具成功不等于整个阶段完成。');
    box.classList.add('test-plan');
    const steps = view.planSteps ?? [];
    if (steps.length) box.append(stageTrack(steps, context));
    if (view.plan?.trim()) box.append(el('p', 'multiline plan-text', view.plan));
    else if (!steps.length) {
      const planning = view.phase === '制定测试计划';
      box.append(empty(planning ? '正在制定测试计划' : '尚未记录测试计划', planning
        ? '任务已建立，尚未开始目标测试；计划保存后将在这里显示。'
        : '旧任务不会自动猜测或补写历史计划。'));
    }
    box.append(preflight(view.preflight));
    if (steps.length) {
      const summary = Object.entries(labels).map(([status, label]) => `${label} ${steps.filter(step => step.status === status).length}`).join(' · ');
      box.append(el('p', 'plan-counts', summary), stepsList(steps));
    } else box.append(el('p', 'muted', '尚未记录步骤状态；保留原文本计划，不自动推断完成情况。'));
    return box;
  }

  P.testPlan = testPlan;
}());
