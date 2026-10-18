const text = { type: 'string' };
const nonempty = { type: 'string', minLength: 1, pattern: '\\S' };
const id = { ...nonempty, maxLength: 128 };
const timestamp = { type: 'string', format: 'date-time' };
const evidence = {
  type: 'array', maxItems: 200,
  items: { type: 'string', pattern: '^(?!/)(?!.*[\\\\\\u0000-\\u001f:])(?!.*(?:^|/)\\.{1,2}(?:/|$))(?!.*//)(?!.*/$).+$' },
};
const strings = { type: 'array', items: nonempty, maxItems: 500 };
const taskId = { type: 'string', format: 'uuid' };
const taskTitle = { ...nonempty, maxLength: 160 };
const planText = { ...text, maxLength: 20000, description: '可执行测试计划全文，包含目标、阶段、方法、预算与停止条件；按纯文本保存。提交非空计划后自动打开HTML工作台，不执行扫描。' };

/** Build a strict JSON object schema with explicit required properties. */
function object(properties, required = Object.keys(properties)) {
  return { type: 'object', properties, required, additionalProperties: false };
}

/** Build an enumerated string schema. */
function choice(...values) {
  return { type: 'string', enum: values };
}

export const assetSchema = object({
  id, kind: choice('ip', 'domain', 'service', 'data'), value: nonempty,
  description: text, evidenceRefs: evidence, observedAt: timestamp,
  parentId: id, port: { type: 'integer', minimum: 1, maximum: 65535 },
  protocol: nonempty, service: nonempty, sensitivity: text,
  dataProfile: object({
    scale: { ...nonempty, maxLength: 500, description: '已知的集合/记录规模及来源；未知时明确写未查询，不推断记录量。' },
    categories: { type: 'array', items: { ...nonempty, maxLength: 100 }, maxItems: 30 },
    sampleStatus: choice('not_sampled', 'metadata_only', 'redacted'),
    redactedSample: { ...nonempty, maxLength: 500, description: '仅保存最小脱敏样例，不包含原始敏感内容。仅sampleStatus=redacted时填写。' },
    exposure: { ...nonempty, maxLength: 1000, description: '已验证的可见范围；区分元数据暴露与内容读取。' },
  }, ['scale', 'categories', 'sampleStatus', 'exposure']),
}, ['id', 'kind', 'value', 'description', 'evidenceRefs', 'observedAt']);
assetSchema.allOf = [{
  if: { properties: { kind: { const: 'service' } } },
  then: { required: ['parentId', 'port', 'protocol', 'service'] },
}, {
  if: { required: ['dataProfile'] },
  then: { properties: { kind: { const: 'data' } } },
}];
assetSchema.properties.dataProfile.allOf = [{
  if: { properties: { sampleStatus: { const: 'redacted' } }, required: ['sampleStatus'] },
  then: { required: ['redactedSample'] },
  else: { not: { required: ['redactedSample'] } },
}];

export const findingSchema = object({
  id, title: nonempty, status: choice('suspected', 'confirmed', 'rejected', 'remediated'),
  severity: choice('critical', 'high', 'medium', 'low', 'info'),
  assetIds: { type: 'array', items: id, maxItems: 500 }, description: text,
  validation: text, poc: text, impact: text, remediation: text, evidenceRefs: evidence,
});
findingSchema.allOf = [{
  if: { properties: { status: { const: 'confirmed' } } },
  then: { properties: { validation: nonempty, poc: nonempty, impact: nonempty, remediation: nonempty, evidenceRefs: { ...evidence, minItems: 1 } } },
}];

export const activitySchema = object({
  id, tool: nonempty, target: nonempty, status: choice('running', 'succeeded', 'failed', 'unknown'),
  planStepId: { ...id, description: '关联当前任务的计划步骤ID；步骤和活动可以在同次record_progress中保存。' },
  startedAt: { ...timestamp, description: '实际开始时间，ISO 8601 格式且含时区；字段名不是 startTime。' },
  summary: { ...text, description: '开始时填写执行意图，返回后填写结果摘要；不使用 intent 或 action 字段。' },
  evidenceRefs: { ...evidence, description: '任务目录内已保存的脱敏证据相对路径；开始执行时尚无证据可填空数组 []，不要编造路径。' },
  finishedAt: { ...timestamp, description: '仅在确认远端执行结束时填写；客户端超时且状态未知时省略。' },
}, ['id', 'tool', 'target', 'status', 'startedAt', 'summary', 'evidenceRefs']);

export const chainSchema = object({
  id, title: nonempty, status: choice('hypothesis', 'partial', 'verified'),
  steps: { type: 'array', minItems: 1, maxItems: 200, items: object({ findingId: id, description: nonempty, verified: { type: 'boolean' } }) },
  impact: text, evidenceRefs: { ...evidence, minItems: 1 },
});

export const reportSchema = object({ summary: text, keyFindings: strings, coverage: text, limitations: strings, recommendations: strings });
export const planStepsSchema = { type: 'array', maxItems: 100, items: object({
  id, title: taskTitle, status: choice('pending', 'running', 'completed', 'blocked'),
  summary: { ...text, maxLength: 4000, description: '执行说明；已完成时写验证结果，受阻时写原因，不以一次工具成功代替整个步骤完成。' },
  evidenceRefs: evidence,
}) };
export const preflightSchema = object({
  status: choice('passed', 'failed'), checkedAt: timestamp, server: nonempty, tool: nonempty,
  summary: { ...nonempty, maxLength: 4000, description: '通过宿主实际调用server_health得到的脱敏结论或连接错误，不凭工具可发现判断健康。' },
});
export const collections = {
  assets: { type: 'array', items: assetSchema, maxItems: 500 },
  findings: { type: 'array', items: findingSchema, maxItems: 200 },
  activities: { type: 'array', items: activitySchema, maxItems: 500 },
  attackChains: { type: 'array', items: chainSchema, maxItems: 100 },
};

const createSchema = object({ title: taskTitle, targets: { ...strings, minItems: 1 }, scope: nonempty, exclusions: strings,
  plan: planText, planSteps: planStepsSchema }, ['title', 'targets', 'scope']);
const updateSchema = object({
  task_id: taskId, expected_revision: { type: 'integer', minimum: 1 },
  phase: text, plan: planText, planSteps: planStepsSchema, preflight: preflightSchema,
  status: choice('planned', 'running', 'paused', 'completed'), ...collections, report: reportSchema,
}, ['task_id', 'expected_revision']);
updateSchema.minProperties = 3;
updateSchema.anyOf = [
  ...['phase', 'status', 'report', 'plan', 'preflight'].map(key => ({ required: [key] })),
  { required: ['planSteps'], properties: { planSteps: { minItems: 1 } } },
  ...Object.keys(collections).map(key => ({ required: [key], properties: { [key]: { minItems: 1 } } })),
];
const readSchema = object({ task_id: taskId });
const openWorkbenchSchema = object({}, []);
const exportSchema = object({ task_id: taskId, expected_revision: { type: 'integer', minimum: 1 }, format: choice('markdown', 'html') }, ['task_id', 'expected_revision']);

export const tools = [
  { name: 'open_workbench', description: '开始执行本插件技能时首先调用，参数必须为{}。立即请求宿主打开HTML工作台，尚无目标和计划也可打开；只返回本次面板标识，不创建任务、不扫描。目标范围明确后再创建真实任务并绑定页面。', inputSchema: openWorkbenchSchema },
  { name: 'create_engagement', description: '目标和范围明确后立即创建任务并请求打开HTML，不等待完整计划或远端检查。title/targets/scope必填；plan/planSteps可稍后补充，初始步骤为pending。保存成功返回任务UUID、版本、路径及pluginId/panelId/runId；随后用宿主read_panel确认加载。此工具不扫描，实际测试前仍须调用远端server_health并保存preflight。', inputSchema: createSchema },
  { name: 'record_progress', description: '以expected_revision执行CAS更新。plan/报告/preflight全文替换；planSteps按ID整行更新，状态pending/running/completed/blocked。开始步骤须preflight passed；failed暂停任务和执行中步骤，停止派发测试，不代表远端进程停止。plan非空自动打开，步骤状态更新不反复打开。activities必填id/tool/target/status/startedAt/summary/evidenceRefs，可选planStepId；没有action/intent/startTime字段。仅存脱敏信息；冲突先读取合并，不重放扫描。', inputSchema: updateSchema },
  { name: 'get_engagement_view', description: '只读获取一个完整原子版本，包含资产、漏洞、工具活动和报告；未知任务报错。', inputSchema: readSchema, annotations: { readOnlyHint: true } },
  { name: 'open_engagement', description: '读取既有任务并打开渗透工作台；不修改任务或执行扫描。', inputSchema: readSchema, annotations: { readOnlyHint: true } },
  { name: 'export_report', description: '将指定当前版本导出为完整报告；format可选markdown（默认）或html。任务未完成时为阶段报告。仅写任务目录，不执行扫描、不改变任务状态。', inputSchema: exportSchema },
];
for (const tool of tools) {
  const readOnly = ['open_workbench', 'get_engagement_view', 'open_engagement'].includes(tool.name);
  tool.annotations = { readOnlyHint: readOnly, destructiveHint: false, openWorldHint: false };
}

export const schemas = Object.fromEntries(tools.map(tool => [tool.name, tool.inputSchema]));

export const viewSchema = object({
  schemaVersion: { type: 'integer', enum: [1] }, taskId, revision: { type: 'integer', minimum: 1 },
  title: taskTitle, status: choice('planned', 'running', 'paused', 'completed'), phase: text,
  targets: { ...strings, minItems: 1 }, scope: nonempty, exclusions: strings,
  createdAt: timestamp, updatedAt: timestamp,
  assetCount: { type: 'integer', minimum: 0 }, confirmedCount: { type: 'integer', minimum: 0 },
  suspectedCount: { type: 'integer', minimum: 0 }, runningCount: { type: 'integer', minimum: 0 },
  ...collections, report: reportSchema,
});
// 旧快照没有plan仍可读取；新建任务始终保存该字段。
viewSchema.properties.plan = planText;
viewSchema.properties.planSteps = planStepsSchema;
viewSchema.properties.preflight = preflightSchema;
