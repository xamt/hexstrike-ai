# HexStrike AI Docker 镜像构建说明

为了从镜像名称上直接区分 CPU 架构，同时提供统一入口，本项目发布以下三个镜像：

```text
amd64 专用:  harbor.everoffice.cn/harbor-cucc/hexstrike-ai-amd64:1.0.0
arm64 专用:  harbor.everoffice.cn/harbor-cucc/hexstrike-ai-arm64:1.0.0
多架构聚合: harbor.everoffice.cn/harbor-cucc/hexstrike-ai-multiarch:1.0.0
```

架构标识属于镜像仓库名称，版本号统一保持为 `1.0.0`。`multiarch` 镜像是一个同时指向 amd64 和 arm64 镜像的 OCI 镜像索引；用户拉取时，Docker 会自动选择与主机匹配的平台。构建命令应在项目根目录（即 `Dockerfile` 所在目录）执行。

## 1. 构建前准备

确认 Docker 服务和 Buildx 可用：

```bash
docker version
docker buildx version
```

## 2. 推荐：分别构建并推送 amd64、arm64 镜像

### 2.1 amd64 镜像

```bash
docker buildx build \
  --platform linux/amd64 \
  --tag harbor.everoffice.cn/harbor-cucc/hexstrike-ai-amd64:1.0.0 \
  --cache-from type=registry,ref=harbor.everoffice.cn/harbor-cucc/hexstrike-ai-amd64:buildcache \
  --cache-to type=registry,ref=harbor.everoffice.cn/harbor-cucc/hexstrike-ai-amd64:buildcache,mode=max \
  --push \
  .
```

### 2.2 arm64 镜像

```bash
docker buildx build \
  --platform linux/arm64 \
  --tag harbor.everoffice.cn/harbor-cucc/hexstrike-ai-arm64:1.0.0 \
  --cache-from type=registry,ref=harbor.everoffice.cn/harbor-cucc/hexstrike-ai-arm64:buildcache \
  --cache-to type=registry,ref=harbor.everoffice.cn/harbor-cucc/hexstrike-ai-arm64:buildcache,mode=max \
  --push \
  .
```

两个架构分别使用自己的构建缓存，避免不同架构的工具层相互覆盖。`buildcache` 仅为缓存标签，不是发布版本；发布镜像不自动追加可变的 `latest` 标签。

如果 Harbor 不允许推送 BuildKit 缓存清单，从对应命令中移除 `--cache-from` 和 `--cache-to` 即可，正式镜像标签保持不变。


## 4. 本机测试构建

使用 `--load` 可以将单架构构建结果直接加载到本机 Docker。即使只用于本地测试，仍保持与 Harbor 一致的镜像名称。

### 4.1 amd64

```bash
docker buildx build \
  --platform linux/amd64 \
  --tag harbor.everoffice.cn/harbor-cucc/hexstrike-ai-amd64:1.0.0 \
  --load \
  .
```

### 4.2 arm64

```bash
docker buildx build \
  --platform linux/arm64 \
  --tag harbor.everoffice.cn/harbor-cucc/hexstrike-ai-arm64:1.0.0 \
  --load \
  .
```

在非目标架构主机上交叉构建或运行时，Docker Desktop/Buildx 需要提供相应的 QEMU 模拟支持。


## 7. 发布结果校验


## 8. 启动验证

推荐直接运行多架构聚合镜像，Docker 会自动选择与主机匹配的镜像：

```bash
docker run --rm \
  --name hexstrike-ai \
  --publish 8888:8888 \
  --cap-add NET_RAW \
  --cap-add NET_ADMIN \
  harbor.everoffice.cn/harbor-cucc/hexstrike-ai-multiarch:1.0.0
```

如需强制使用专用架构镜像，可根据主机选择以下镜像：

```text
harbor.everoffice.cn/harbor-cucc/hexstrike-ai-amd64:1.0.0
harbor.everoffice.cn/harbor-cucc/hexstrike-ai-arm64:1.0.0
```

另开终端检查健康状态：

```bash
curl --fail --silent --show-error http://127.0.0.1:8888/health
```

`NET_RAW` 和 `NET_ADMIN` 仅用于确实需要原始套接字或网络管理能力的安全工具。若只验证 HTTP 服务，可以移除这两个参数；不建议直接使用范围更大的 `--privileged`。
