# 技能工具与测试闭环 — 任务分解

## 拆分原则
接口核对与流程增强分离，按共享参数契约和独立验证证据验收。

## 任务列表
- [√] 流程增强（AFK）
  - 涉及文件：skills/pentest-tools/SKILL.md、references/planning-validation.md、references/engagement.md、references/workflows/*.md、agents/openai.yaml。
  - 完成标准：技能明确要求首次目标请求前输出计划；计划含假设、排序、证伪标准与预算；疑点验证、根因深化和停止条件均有独立步骤。
  - 验证方式：离线引用和参数测试、技能格式验证、独立情境推演。
- [√] 数据库工具封装（AFK）
  - 涉及文件：database_tools/、hexstrike_server.py、Dockerfile、scripts/skill-export/、skills/pentest-tools/scripts/、references/tools/、tests/。
  - 完成标准：五个 POST 路由注册且调用独立执行器；生成工具参数与共享契约相等；SQL/命令允许读写；失败、超时、输出限制、并发与密码保护均有通过测试。
  - 验证方式：离线参数/请求/返回对照与错误路径模拟。
- [√] 回归与交付（AFK）
  - 涉及文件：tests/、DOCKER_BUILD.md、当前方案包。
  - 完成标准：旧契约保留、所有本轮检查通过、无镜像构建和扫描。
  - 验证方式：Python 与 Node 离线回归、diff 检查及交付证据。

## 进度
已完成。76 项 Python、14 项 Node 测试、936 组契约对照、技能格式、源码语法及差异检查通过。独立情境和代码审查完成；修复 Mongo 部分写失败与 Redis 退出状态问题。未构建镜像、连接真实数据库或扫描；生产链路与双架构实际客户端运行不在离线证据范围内。
