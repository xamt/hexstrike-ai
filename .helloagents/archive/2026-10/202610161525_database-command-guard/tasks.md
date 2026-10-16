# 数据库命令保护 — 任务分解

## 拆分原则
按可验证的保护行为拆分，全部离线实施。

## 任务列表
- [√] SQL保护（AFK）：三类SQL检查入口（依赖：无；涉及文件：database_tools/policy*.py、SQL词法模块、tests/test_database_policy_sql.py；预期变更：允许查询和INSERT/UPDATE，拒绝多语句/删除/DDL/动态执行及词法歧义；完成标准：正反例测试均通过，字符串内容不被误当删除指令；验证方式：unittest离线测试）。
- [√] NoSQL保护（AFK）：Redis与MongoDB嵌套保护（依赖：无；涉及文件：database_tools/policy_nosql.py、tests/test_database_policy_nosql.py；预期变更：命令允许列表及嵌套副作用校验；完成标准：读取与受限新增/更新通过、删除/过期/裁剪/删字段/脚本/输出集合/未知命令拒绝；验证方式：unittest离线测试）。
- [√] 执行边界与交付（AFK）：HTTP和执行器接入并同步文档（依赖：前两项；涉及文件：database_tools/contracts.py、http.py、runner.py、contracts.json、tests/test_database_*.py、skills/pentest-tools、DOCKER_BUILD.md；预期变更：403策略错误，防绕过、更新工具说明；完成标准：危险请求不调用执行器，直接入口不启动进程，原离线回归及导出校验通过；验证方式：Python全套、Node测试、技能校验、静态审查）。

## Codex /goal 执行入口
本轮不创建goal。方案已归档；历史执行入口为 `.helloagents/plans/202610161525_database-command-guard/tasks.md`，流程为 /goal -> ~auto -> ~qa；本轮已完成验证与归档，无剩余执行任务。

## 进度
已完成：100项Python、14项Node通过，技能校验及导出一致性通过。独立审查的INSERT目标后缀问题已按失败用例修复并复核。未做真实数据库连接、扫描或镜像构建；部署后方能生效。
