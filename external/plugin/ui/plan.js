(function () {
  'use strict';
  const P = window.Pentest;
  const { el, section, empty, badge, evidence } = P.dom;
  const labels = { pending: '待执行', running: '执行中', completed: '已完成', blocked: '受阻' };
  const tones = { pending: 'info', running: 'running', completed: 'succeeded', blocked: 'failed' };

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
  function testPlan(view) {
    const box = section('渗透测试计划', '状态由 Agent 按实际执行更新；一次工具成功不等于整个步骤完成。');
    box.classList.add('test-plan');
    const steps = view.planSteps ?? [];
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
