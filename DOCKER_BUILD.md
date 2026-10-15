# HexStrike AI 双镜像构建说明

## 1. 职责与更新规则

| 镜像 | 内容 | 重建时机 |
| --- | --- | --- |
| 基础镜像 | Kali、现有安全工具、字典、Python 3.11、独立 Volatility3 环境 | 工具、系统库或 Python 运行时变化 |
| 应用镜像 | 基础镜像 + 项目 Python 依赖 + 服务代码 | 项目依赖或代码变化 |

基础镜像入口为 `Dockerfile.base`，应用入口为 `Dockerfile`。
基础镜像不读取项目依赖文件和服务代码，不自动启动 HTTP 服务。
应用只引用已构建的基础镜像，不执行 APT、Go、Cargo 或安全工具安装。

保留现有镜像仓库的 `penttest` 拼写：

| 架构 | 基础镜像 | 应用镜像 |
| --- | --- | --- |
| AMD64 | `penttest-tools-base-amd64` | `penttest-tools-amd64` |
| ARM64 | `penttest-tools-base-arm64` | `penttest-tools-arm64` |
| 多架构入口 | `penttest-tools-base-multiarch` | `penttest-tools-multiarch` |

仓库前缀统一为 `harbor.everoffice.cn/harbor-cucc/`。
基础镜像和应用版本独立管理，首版均为 `1.0.0`；发布标签不可覆盖，不发布可变的 `latest`。

## 2. 构建准备

在项目根目录执行：

```bash
docker version
docker buildx version
docker buildx ls
python3 -m unittest discover -s tests -v
```

本地两步构建使用 Docker Desktop 的 `docker` 驱动。
`docker-container` 等独立构建器不能假定能读取宿主机镜像存储，必须先将验证通过的基础镜像发布到仓库。
非本机架构执行安装或运行检查需要 QEMU；Docker Desktop 通常自带。
首次基础镜像构建会安装完整工具链，占用较多时间、磁盘和网络资源。

## 3. 本地两步构建

先验证 ARM64；验证 AMD64 时仅将 `ARCH` 改为 `amd64`，重复本节和第 4 节。

```bash
ARCH=arm64
REGISTRY=harbor.everoffice.cn/harbor-cucc
BASE_VERSION=1.0.0
APP_VERSION=1.0.0
BASE_IMAGE="${REGISTRY}/penttest-tools-base-${ARCH}:${BASE_VERSION}"
APP_IMAGE="${REGISTRY}/penttest-tools-${ARCH}:${APP_VERSION}"
```

### 3.1 基础镜像

```bash
docker buildx build \
  --platform "linux/${ARCH}" \
  --file Dockerfile.base \
  --tag "${BASE_IMAGE}" \
  --load --progress=plain .
```

保留精确工具版本；版本不可用时构建失败，不自动升级或跳过。
默认 Kali 源为阿里云；可显式换为官方镜像分发地址：

```bash
docker buildx build \
  --platform "linux/${ARCH}" \
  --file Dockerfile.base \
  --build-arg KALI_APT_MIRROR=http://http.kali.org/kali \
  --tag "${BASE_IMAGE}" \
  --load --progress=plain .
```

该覆盖仍要求 Kali 官方签名验证。HTTPS 引导使用官方 Python 镜像的 CA 信任链，然后由 Kali 的证书包接管；不关闭证书校验。
最小 Kali 尚未建立 OpenSSL 默认信任路径，因此显式设置 APT 的 CA 文件路径。下载缓存由 BuildKit 管理，移除镜像自带的下载后清理钩子，以便重试复用软件包。
APT 索引更新失败立即中止，不使用不完整索引继续安装。

### 3.2 应用镜像

```bash
docker buildx build \
  --platform "linux/${ARCH}" \
  --build-arg BASE_IMAGE="${BASE_IMAGE}" \
  --tag "${APP_IMAGE}" \
  --load --progress=plain .
```

未覆盖时，`BASE_IMAGE` 默认指向：
`harbor.everoffice.cn/harbor-cucc/penttest-tools-base-multiarch:1.0.0`。
首次本地构建必须按上例传入已经加载的单架构基础镜像，不依赖多架构入口已经发布。

## 4. 运行验收

可以直接执行自动验收脚本（检查镜像架构、环境隔离和 HTTP 健康状态，退出时清理自己的测试容器）：

```bash
bash docker/test-images.sh "${BASE_IMAGE}" "${APP_IMAGE}" "${ARCH}"
```

以下分项命令用于人工排查。

### 4.1 基础镜像

```bash
docker run --rm --platform "linux/${ARCH}" "${BASE_IMAGE}" \
  /bin/bash -ec 'python3.11 --version; nmap --version; x8 --version; vol -h; cat /opt/hexstrike/tool-versions.lock'
```

构建末尾已经检查全部承诺工具命令、Go/Rust 二进制架构、Python 动态库、Volatility3 版本和依赖。
默认运行基础镜像进入 Bash，不提供 HTTP 端口或健康检查。

### 4.2 应用依赖与工具隔离

```bash
docker run --rm --platform "linux/${ARCH}" "${APP_IMAGE}" \
  /bin/bash -ec '/usr/local/bin/python3.11 -m pip --python /opt/hexstrike-venv/bin/python check; /opt/volatility3-venv/bin/python -m pip check; vol -h; command -v httpx'
```

Volatility3 环境位于 `/opt/volatility3-venv`；项目环境位于 `/opt/hexstrike-venv`。
应用依赖仍排除 `pwntools`、`angr`、`bcrypt`，与拆分前一致。
基础镜像的固定版本 pip 通过 `--python` 管理应用环境；应用环境不要求独立安装 pip。
应用虚拟环境仍位于 `PATH` 首位，保留项目生成脚本通过 `python3` 使用项目依赖的行为。
安装依赖后，将应用环境的同名 `httpx` 命令链接到基础镜像安全工具；Python 的 `httpx` 库导入不受影响。
服务启动和健康检查显式使用 `/opt/hexstrike-venv/bin/python`，工具 Volatility3 则始终使用自己的解释器。

### 4.3 启动与健康检查

```bash
docker run --detach \
  --name penttest-tools \
  --platform "linux/${ARCH}" \
  --publish 127.0.0.1:8888:8888 \
  "${APP_IMAGE}"

curl --fail --silent --show-error http://127.0.0.1:8888/health
docker inspect --format '{{.State.Health.Status}}' penttest-tools
docker logs penttest-tools
```

等待容器健康状态为 `healthy`。健康接口包含未纳入镜像的可选工具，不要求全部标记可用。
验收仅验证本机启动，不执行外部扫描。确需原始套接字或网络管理时才添加
`--cap-add NET_RAW --cap-add NET_ADMIN`，不使用 `--privileged`。
测试结束后停止并移除本次创建的容器：

```bash
docker stop penttest-tools
docker rm penttest-tools
```

### 4.4 缓存验证

自动验证使用临时工作副本与唯一镜像标签，不修改源码；结束后清理临时标签：

```bash
python3 tests/verify_docker_cache.py "${BASE_IMAGE}" "${ARCH}"
```

在临时工作副本验证，不修改待发布源码：
1. 基于同一基础镜像构建应用，保存 `--progress=plain` 输出。
2. 仅在服务代码追加注释再构建：依赖安装步骤应为 `CACHED`，代码复制与检查重新执行。
3. 仅在依赖文件追加注释再构建：依赖安装步骤重新执行；基础镜像摘要不变，不执行工具安装。
4. 对两次产物执行依赖检查与 `vol -h`，证明应用依赖安装不影响工具环境。

## 5. 发布与摘要固定

只有两个架构完成实际构建和运行验收后才执行发布；以下命令不会由本次开发自动执行。
若 `1.0.0` 已发布，先改为新版本，禁止覆盖。

### 5.1 发布基础镜像

```bash
docker push "${REGISTRY}/penttest-tools-base-amd64:${BASE_VERSION}"
docker push "${REGISTRY}/penttest-tools-base-arm64:${BASE_VERSION}"
docker buildx imagetools create \
  --tag "${REGISTRY}/penttest-tools-base-multiarch:${BASE_VERSION}" \
  "${REGISTRY}/penttest-tools-base-amd64:${BASE_VERSION}" \
  "${REGISTRY}/penttest-tools-base-arm64:${BASE_VERSION}"
docker buildx imagetools inspect "${REGISTRY}/penttest-tools-base-multiarch:${BASE_VERSION}"
```

检查输出包含 `linux/amd64`、`linux/arm64`，记录多架构索引的 `Digest`。

### 5.2 固定摘要重建并验收应用

将上一步的真实索引摘要设置到 `BASE_DIGEST`，不可使用占位值：

```bash
: "${BASE_DIGEST:?请设置已验收基础镜像的 sha256 摘要}"
docker buildx build \
  --platform "linux/${ARCH}" \
  --build-arg BASE_IMAGE="${REGISTRY}/penttest-tools-base-multiarch@${BASE_DIGEST}" \
  --tag "${APP_IMAGE}" \
  --load --progress=plain .
```

两个架构分别重建并重复第 4 节，再发布应用：

```bash
docker push "${REGISTRY}/penttest-tools-amd64:${APP_VERSION}"
docker push "${REGISTRY}/penttest-tools-arm64:${APP_VERSION}"
docker buildx imagetools create \
  --tag "${REGISTRY}/penttest-tools-multiarch:${APP_VERSION}" \
  "${REGISTRY}/penttest-tools-amd64:${APP_VERSION}" \
  "${REGISTRY}/penttest-tools-arm64:${APP_VERSION}"
docker buildx imagetools inspect "${REGISTRY}/penttest-tools-multiarch:${APP_VERSION}"
```

最终可以通过 `harbor.everoffice.cn/harbor-cucc/penttest-tools-multiarch:1.0.0` 启动应用。
正式部署保留应用摘要和基础镜像摘要，回滚直接部署上一版应用镜像。

## 6. 构建缓存与限制

APT 缓存挂载按架构区分。基础镜像和应用镜像的远程缓存也必须分开：
- 基础镜像：`penttest-tools-base-${ARCH}:buildcache`。
- 应用镜像：`penttest-tools-${ARCH}:buildcache`。

支持 registry 缓存的构建器可添加：

```bash
--cache-from "type=registry,ref=${CACHE_IMAGE}" \
--cache-to "type=registry,ref=${CACHE_IMAGE},mode=max"
```

`CACHE_IMAGE` 必须根据当前构建类型选择对应仓库。缓存标签可以更新，发布标签不能覆盖。
不支持远程缓存时去掉这两个参数即可；应用继承基础镜像不依赖远程构建缓存。

工具版本锁定不等于所有传递依赖均可重复解析。Kali 滚动仓库可能移除旧版本，项目 Python 依赖也仍采用既有版本范围。
X8 4.3.0 锁定的 time 0.3.21 与 Rust 1.80 及以上不兼容，其独立构建阶段固定使用 Rust 1.79；不更新 X8 或 Cargo 锁文件，编译器不进入基础镜像。
基础镜像已发布后，日常应用构建不再依赖 Kali、Go 或 Rust 安装源，但项目依赖安装仍需要 Python 包源。
不把 Nuclei 模板、彩虹表、大型字典、Volatility 符号表固化到镜像，继续通过卷或运行时更新提供。
AutoRecon 的包依赖可能在构建时下载 SecLists；其安装目录挂载为独立构建缓存，不写入镜像层。需要这套字典时，将已有数据只读挂载到容器的 `/usr/share/seclists`。包版本元数据保留，但不能将它视为字典数据已经可用。
