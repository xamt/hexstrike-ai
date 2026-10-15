# HTTP 工具技能 — 实施规划

## 目标与范围
建立可分发的 pentest-tools 技能及零第三方依赖 HTTP 调用器。

## 架构与实现策略
项目 skills/pentest-tools 为分发源；从原 Python 工具定义生成参数清单、分组参考与 JavaScript 调用函数。生成器仅用于维护，运行不读 Python。Node.js fetch 直接发 HTTP；无 shell 拼接、无自动重试、无启动探测。

## 领域语言
工具定义是 Agent 调用契约；工具执行在容器；本地复合工具可能返回计划而非执行扫描。

## 完成定义
全部 151 个注册声明被记录，重名定义明确处理；默认参数及特殊转换有离线对照证据。qaMode=standard，qaFocus=参数兼容、复合逻辑、HTTP 失败、零运行时依赖。

## 文件结构
skills/pentest-tools/{SKILL.md,scripts/,references/}；scripts/skill-export/ 为开发生成器；tests/ 为纯离线验证。

## UI / 设计约束
不适用。

## 风险与验证
原脚本存在重名 httpx_probe 与未定义 self 的复合调用。原始声明全部保留，重名追加明确别名；self 调用修正为同名工具函数并披露。模拟客户端对照全部调用，禁止真实扫描。

## 决策记录
- 2026-10-15 用户已授权实现技能，不再追加确认；仅运行离线模拟验证。
