# 数据库客户端镜像环境 — 实施规划

## 目标与范围
按用户最新要求仅交付五类固定版本客户端安装、最终镜像校验与构建文档；不构建或运行镜像、不连接数据库。

## 架构与实现策略
按 Kali 客户端、ClickHouse、MongoDB 三层安装，复用原版本记录校验。MariaDB/Redis/PostgreSQL 使用已有 Kali 签名仓库；ClickHouse/MongoDB 固定官方包和双架构 SHA256，核对包名/版本/架构后安装。基础和应用示例版本升至 1.1.0，不覆盖已构建的 1.0.0。

## 领域语言
客户端可发现仅代表命令存在，不等价数据库可连接；MySQL 客户端为 MariaDB 实现；MongoDB shell 为 mongosh。

## 完成定义
五类安装路径、双架构元数据、版本记录和构建命令校验一致，原工具版本不变；仅离线测试通过，不声称实际镜像验收通过。qaMode=deep，聚焦供应链、版本契约、失败处理和范围回退。

## 文件结构
Dockerfile.base；Dockerfile 的基础镜像引用；docker/install-database*.sh；最终验证和用户验收脚本；tests/test_database_install.py 与 fixtures；DOCKER_BUILD.md。

## UI / 设计约束
不涉及 UI。

## 风险与验证
安装与下载调用均用临时伪命令验证；官方包索引已查证但未下载/运行完整客户端包。Kali 滚动包可被移除，必须报错，不放宽版本。ClickHouse 公共二进制和 MongoDB 包在 Kali 上的实际运行需用户构建验证。

## 决策记录
- [2026-10-16] 用户选择 MariaDB 兼容客户端；按已给方案实施，保留不构建、不连接数据库的边界。
- [2026-10-16] 用户随后明确“做好dockerfile就行，我自己制作镜像”，范围收敛；撤回本轮未提交的 HTTP/MCP/健康检查实现及相应测试和文档。
