# 五项安全工具补充 — 任务分解

## 拆分原则
AFK 为离线实现和验证；镜像和真实工具执行由用户负责，不计作已通过。

## 任务列表
- [√] 安装与版本（AFK）：docker/ 与 Dockerfile；五工具固定版本、双架构路径、最终校验和 1.2.0 引用完整；安装合同与 shell 语法测试通过。
- [√] 服务调用（AFK）：security_tools/ 与 hexstrike_server.py；五 POST 路由和健康命令正确，有界无 shell 执行；Flask 模拟请求和进程测试通过。
- [√] 技能声明（AFK）：scripts/skill-export/ 与 skills/pentest-tools/；五声明与服务契约一致，原声明保持；导出检查与 966 组调用对照通过。
- [√] 文档与回归（AFK）：DOCKER_BUILD.md、tests/；独立架构命令和工具限制清晰；125 项 Python、16 项 Node 测试及独立复核通过。
- [-] 实际构建与扫描（HITL）：用户自行完成，本轮不执行也不宣称通过。

## Codex /goal 执行入口
后续需要长程执行时，按本目录 tasks.md 经 /goal -> ~auto -> ~qa 执行；不得跨越不构建镜像和不扫描的边界。

## 进度
已完成约定的源码与离线验证交付，镜像和真实工具验证由用户执行。
