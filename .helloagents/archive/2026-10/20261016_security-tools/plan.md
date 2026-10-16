# 五项安全工具补充 — 实施规划

## 目标与范围
沿用用户已确认的五工具建议直接实施，镜像实际制作由用户完成。

## 架构与实现策略
安装脚本管理版本，最终校验入口纳入工具；security_tools 独立封装契约、命令、执行及 Flask 注册；技能导出器消费共享契约，避免手写生成产物。

## 领域语言
testssl.sh 是包名，testssl 是命令；jwt_tool 是新外部工具，不等于旧 jwt_analyzer。

## 完成定义
五工具安装配方与验证一致，五路由和技能声明匹配；保留原工具版本，基础镜像引用统一 1.2.0；qaMode=deep，离线回归通过，不声称镜像验收通过。

## 文件结构
docker/install-*、Dockerfile.base、Dockerfile、DOCKER_BUILD.md；security_tools/；hexstrike_server.py；scripts/skill-export/；skills/pentest-tools/；tests/。

## UI / 设计约束
不适用。

## 风险与验证
验证双架构包来源、JWT 源码和依赖锁定、命令参数隔离、超时/输出/并发限制；使用模拟子进程和 Flask 内存客户端，不执行五个实际工具。

## 决策记录
- 2026-10-16：用户已明确同意实施；检查并补齐缺失声明，不改原业务接口。
- 2026-10-16：TruffleHog 默认不联网验证凭据；tcpdump 默认离线读包，实时抓包显式选择且有界。
