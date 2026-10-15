# HTTP 工具技能 — 任务分解

## 拆分原则
按可验证调用行为交付，所有验证均离线。

## 任务列表
- [√] 工具迁移（AFK）：生成全部参数、默认值与请求逻辑（scripts/skill-export、skills/pentest-tools）；151 声明共 906 个原逻辑离线对照通过，产物一致性检查通过。
- [√] HTTP 调用（AFK）：提供 list、describe、call（skills/pentest-tools/scripts）；9 个 Node 测试覆盖 GET 查询、POST JSON、HTTP 错误、业务失败、超时、不重试、混合失败 CLI 退出码与本地时间格式。
- [√] 技能交付（AFK）：技能校验、JavaScript 语法和参考链接检查通过；说明 Node.js 运行需求、既有缺陷和测试边界，DOCKER_BUILD.md 已补入口说明。

## Codex /goal 执行入口
需要续跑时按本 tasks.md 继续 ~auto → ~qa；不允许镜像构建与真实扫描。

## 进度
已完成。Python 全部离线测试 41 项通过；906 个工具对照包含其中。独立审查发现的时间戳与无效日志中间值问题已修复。未构建镜像、未请求真实服务、未执行扫描。
