/** 仅供离线 UI 验证的合成记录，不来自实际目标或扫描。 */
export function sampleView() {
  const now = new Date().toISOString();
  const evidenceRefs = ['evidence/synthetic.txt'];
  const asset = (id, kind, value, extra = {}) => ({ id, kind, value,
    description: '离线合成数据 · 仅验证视图', observedAt: now, evidenceRefs, ...extra });
  const finding = (id, status, severity, title) => ({ id, status, severity, title,
    assetIds: ['A-03'], description: '合成访问控制测试记录，不是真实漏洞。',
    validation: '使用两组虚构角色进行结果对照；仅用于展示验证过程。',
    poc: 'GET /synthetic-object\nX-Test: [REDACTED]\n<img src=x onerror="window.injected=true">',
    impact: '仅展示潜在的跨角色数据可见性风险。', remediation: '在服务端逐对象检查授权，并增加回归用例。', evidenceRefs });
  return {
    schemaVersion: 1, taskId: '00000000-0000-4000-8000-000000000001', revision: 4,
    title: '离线演示 · 应用安全验证', status: 'running', phase: '疑点复核与证据整理',
    targets: ['app.example.test'], scope: '合成记录，无实际网络测试', exclusions: ['任何真实目标'],
    createdAt: now, updatedAt: now, assetCount: 4, confirmedCount: 1, suspectedCount: 1, runningCount: 1,
    assets: [asset('A-01', 'ip', '192.0.2.10'), asset('A-02', 'domain', 'app.example.test'),
      asset('A-03', 'service', 'HTTPS · 443', { parentId: 'A-01', port: 443, protocol: 'tcp', service: 'https' }),
      asset('A-04', 'data', '演示订单元数据', { sensitivity: '已脱敏 · 无真实记录', parentId: 'A-03' })],
    findings: [finding('F-01', 'confirmed', 'high', '合成发现：对象级授权缺口'),
      finding('F-02', 'suspected', 'medium', '待验证：关联接口权限一致性')],
    activities: [{ id: 'T-01', tool: 'plugin:pentest-tools:scanner / httpx_probe',
      target: 'app.example.test', status: 'running', startedAt: now,
      summary: '仅验证执行记录展示，未调用真实工具。', evidenceRefs }],
    attackChains: [{ id: 'C-01', title: '合成路径：对象访问 → 数据范围', status: 'partial',
      steps: [{ findingId: 'F-01', description: '第一步验证记录', verified: true },
        { findingId: 'F-02', description: '第二步仍为假设', verified: false }],
      impact: '仅用于展示已验证与未验证边界。', evidenceRefs }],
    report: { summary: '本记录仅用于插件离线验收，展示资产、漏洞与证据的关联，不代表任何真实测试结论。',
      keyFindings: ['一项合成已确认发现、一项待验证线索；不合并为两个已确认漏洞。'],
      coverage: '合成应用与接口记录；无真实扫描。', limitations: ['未连接真实目标'],
      recommendations: ['优先修复已确认根因，再复核关联路径。'] },
  };
}
