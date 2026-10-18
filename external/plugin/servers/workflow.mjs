import { fail } from './errors.mjs';

/** 校验步骤身份、完成依据和活动关联，不猜测历史任务的步骤。 */
export function validatePlan(view) {
  const steps = view.planSteps ?? [];
  const ids = new Set(steps.map(step => step.id));
  if (ids.size !== steps.length) fail('VALIDATION_ERROR', 'planSteps包含重复ID。');
  for (const step of steps) {
    if (['completed', 'blocked'].includes(step.status) && !step.summary.trim()) {
      fail('VALIDATION_ERROR', '已完成步骤必须记录结果，受阻步骤必须记录原因。');
    }
  }
  for (const activity of view.activities) {
    if (activity.planStepId && !ids.has(activity.planStepId)) fail('VALIDATION_ERROR', '活动引用了不存在的计划步骤。');
  }
  if (view.status === 'completed' && steps.some(step => step.status !== 'completed')) {
    fail('VALIDATION_ERROR', '仍有未完成计划步骤，不能将整个任务标为已完成。');
  }
}

/** 应用记录层执行门槛；只处理记录，不连接或停止远端工具进程。 */
export function applyPreflight(view, args) {
  if (args.preflight?.status === 'failed') {
    view.status = 'paused';
    view.planSteps = (view.planSteps ?? []).map(step => step.status === 'running'
      ? { ...step, status: 'blocked', summary: args.preflight.summary } : step);
    view.activities = view.activities.map(activity => {
      if (activity.status !== 'running') return activity;
      const { finishedAt, ...rest } = activity;
      return { ...rest, status: 'unknown', summary: `MCP异常，远端执行状态待确认：${args.preflight.summary}` };
    });
    return;
  }
  const startsStep = args.planSteps?.some(step => step.status === 'running');
  const startsTask = view.planSteps?.length && args.status === 'running';
  const startsActivity = args.activities?.some(activity => activity.planStepId && activity.status === 'running');
  if ((startsStep || startsTask || startsActivity) && view.preflight?.status !== 'passed') {
    fail('PREFLIGHT_REQUIRED', '先通过宿主实际调用server_health并记录preflight passed；检查未通过时停止渗透，不绕过MCP。');
  }
  if (startsStep || startsActivity) {
    if (args.status && args.status !== 'running') fail('VALIDATION_ERROR', '开始步骤或关联活动时任务状态必须为running。');
    view.status = 'running';
  }
}
