# 工具基础镜像与应用镜像构建说明

## 1. 镜像与构建顺序

只构建 AMD64、ARM64 两种独立镜像，不创建多架构入口。每个架构先构建基础镜像，再构建应用镜像。

| 用途 | AMD64 | ARM64 |
| --- | --- | --- |
| 基础镜像 | `harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.0.0-amd64` | `harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.0.0-arm64` |
| 应用镜像 | `harbor.everoffice.cn/harbor-cucc/pentest-tools:1.0.0-amd64` | `harbor.everoffice.cn/harbor-cucc/pentest-tools:1.0.0-arm64` |

- 基础镜像：Kali、安全工具、小型字典、Python 3.11、独立 Volatility3 环境；默认进入 Bash，不启动服务。
- 应用镜像：继承同架构基础镜像，安装项目依赖、复制代码、配置 8888 端口和健康检查，不重复安装安全工具。
- 两类镜像版本独立管理；工具或运行时变化才重建基础镜像，仅代码或项目依赖变化只重建应用镜像。
- 不使用 `latest`；已发布的版本标签不可覆盖。调整版本时直接修改对应命令中的完整镜像名。

以下命令全部在项目根目录执行，不需要预先设置任何 Shell 变量。
本地两步构建使用 Docker Desktop 的 `docker` 驱动，基础镜像通过 `--load` 保存到本机。
`docker-container` 等独立构建器需要先从仓库获取基础镜像，不能假定可读取宿主机镜像存储。
跨架构构建或运行需要模拟器支持；Docker Desktop 通常已提供。

## 2. 构建基础镜像

### 2.1 AMD64 基础镜像

```bash
docker buildx build \
  --platform linux/amd64 \
  --file "Dockerfile.base" \
  --tag harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.0.0-amd64 \
  --load \
  --progress=plain \
  "."
```

### 2.2 ARM64 基础镜像

```bash
docker buildx build \
  --platform linux/arm64 \
  --file "Dockerfile.base" \
  --tag harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.0.0-arm64 \
  --load \
  --progress=plain \
  "."
```

默认使用阿里云 Kali 源。需要切换到 Kali 官方分发地址时，在对应命令的 `--load` 前增加
`--build-arg KALI_APT_MIRROR=http://http.kali.org/kali`；仍验证 Kali 官方签名。
软件包版本不存在或下载失败时直接中止，不自动升级或跳过工具。

## 3. 构建应用镜像

### 3.1 AMD64 应用镜像

先完成第 2.1 节。

```bash
docker buildx build \
  --platform linux/amd64 \
  --file "Dockerfile" \
  --build-arg BASE_IMAGE=harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.0.0-amd64 \
  --tag harbor.everoffice.cn/harbor-cucc/pentest-tools:1.0.0-amd64 \
  --load \
  --progress=plain \
  "."
```

### 3.2 ARM64 应用镜像

先完成第 2.2 节。

```bash
docker buildx build \
  --platform linux/arm64 \
  --file "Dockerfile" \
  --build-arg BASE_IMAGE=harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.0.0-arm64 \
  --tag harbor.everoffice.cn/harbor-cucc/pentest-tools:1.0.0-arm64 \
  --load \
  --progress=plain \
  "."
```

命令显式指定基础镜像，避免选错架构。省略 `BASE_IMAGE` 时，Dockerfile 依据 BuildKit 的 `TARGETARCH`
选择对应架构标签，不引用公共多架构标签。[Docker 参数说明](https://docs.docker.com/reference/dockerfile/#automatic-platform-args-in-the-global-scope)

## 4. 验收与启动（由使用者执行）

### 4.1 离线检查

不调用 Docker、不访问网络：

```bash
python3 -m unittest discover -s "tests" -v
```

### 4.2 AMD64 镜像验收

```bash
bash "docker/test-images.sh" \
  harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.0.0-amd64 \
  harbor.everoffice.cn/harbor-cucc/pentest-tools:1.0.0-amd64 \
  amd64
```

### 4.3 ARM64 镜像验收

```bash
bash "docker/test-images.sh" \
  harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.0.0-arm64 \
  harbor.everoffice.cn/harbor-cucc/pentest-tools:1.0.0-arm64 \
  arm64
```

脚本检查架构、工具启动、Python 依赖隔离和 HTTP 健康状态，禁用容器网络并清理自己创建的测试容器。
健康接口列出的可选工具不要求全部安装；验收不执行外部扫描。

### 4.4 手动启动 AMD64 应用

```bash
docker run --detach \
  --name pentest-tools-amd64 \
  --platform linux/amd64 \
  --publish 127.0.0.1:8888:8888 \
  harbor.everoffice.cn/harbor-cucc/pentest-tools:1.0.0-amd64
curl --fail --silent --show-error http://127.0.0.1:8888/health
docker inspect --format '{{.State.Health.Status}}' pentest-tools-amd64
docker logs pentest-tools-amd64
```

### 4.5 手动启动 ARM64 应用

```bash
docker run --detach \
  --name pentest-tools-arm64 \
  --platform linux/arm64 \
  --publish 127.0.0.1:8888:8888 \
  harbor.everoffice.cn/harbor-cucc/pentest-tools:1.0.0-arm64
curl --fail --silent --show-error http://127.0.0.1:8888/health
docker inspect --format '{{.State.Health.Status}}' pentest-tools-arm64
docker logs pentest-tools-arm64
```

两条启动命令使用同一个宿主机端口，不要同时运行。等待健康状态变为 `healthy` 后再验收。
停止时使用对应容器名执行 `docker stop`，再执行 `docker rm`。
确需原始套接字或网络管理时才添加 `--cap-add NET_RAW --cap-add NET_ADMIN`，不要直接使用 `--privileged`。

### 4.6 缓存回归

AMD64：

```bash
python3 "tests/verify_docker_cache.py" \
  harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.0.0-amd64 amd64
```

ARM64：

```bash
python3 "tests/verify_docker_cache.py" \
  harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.0.0-arm64 arm64
```

该脚本会实际构建临时应用镜像：只改代码时复用依赖层，只改依赖时重新安装项目依赖，基础镜像保持不变。
同时验证 Volatility3 不受影响；源码不变，临时标签在结束时清理。

## 5. 发布独立镜像

对应架构完成构建与验收后再推送，不合并镜像。若版本已发布，应先换用新版本。

### 5.1 AMD64

```bash
docker push harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.0.0-amd64
docker push harbor.everoffice.cn/harbor-cucc/pentest-tools:1.0.0-amd64
```

### 5.2 ARM64

```bash
docker push harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.0.0-arm64
docker push harbor.everoffice.cn/harbor-cucc/pentest-tools:1.0.0-arm64
```

正式应用发布时，先推送并记录**同架构基础镜像**的真实摘要，将第 3 节 `BASE_IMAGE` 的值替换为
`harbor.everoffice.cn/harbor-cucc/pentest-tools-base@sha256:<该架构的真实摘要>`，再重建、验收并推送应用。
占位内容不能原样执行；不要把 ARM64 基础摘要用于 AMD64 构建。
部署时记录应用摘要和基础摘要；回滚直接部署上一版应用，不覆盖旧基础镜像。

## 6. Dockerfile 与脚本如何维护

### 6.1 唯一配置入口

`Dockerfile.base` 顶部配置区集中定义所有可覆盖的构建参数默认值：上游镜像、Kali 源、编译器和工具版本。
顶部以下只允许无默认值的 `ARG`，用于把配置导入当前阶段；子阶段继承父阶段已导入的参数。
这是 Docker 的作用域要求，不是重复维护版本。[ARG 与 FROM 的作用域](https://docs.docker.com/reference/dockerfile/#understand-how-arg-and-from-interact)

脚本不再另设版本默认值，只使用传入参数。软件包名、目录、包装命令和架构选择属于安装实现，保留在脚本中。
Go 安装器的 `OUTPUT_DIR` 只供离线测试隔离产物；镜像构建固定使用默认 `/out`。

### 6.2 统一执行方式

之前仅抽出了较长的 Kali 安装过程，较短的 Rust、Nikto、Python 安装仍内联在 Dockerfile，导致组织方式混杂。
现在基础镜像的每个 `RUN` 都只挂载并执行职责明确的脚本；Dockerfile 负责参数、阶段、缓存与文件复制。
脚本通过只读构建挂载使用，不复制到最终镜像中。不同工具类别仍保留独立安装层，不合并为一个大脚本。

| 阶段 | 安装与校验入口 | 产物 |
| --- | --- | --- |
| Go | `docker/install-go-tool.sh` | Gau、Waybackurls、Anew 目标架构二进制 |
| Rust | `docker/install-rust-toolchain.sh`、`docker/install-x8.sh` | X8 二进制 |
| Nikto | `docker/install-nikto-source.sh` | 固定标签源码 |
| Kali | `docker/install-system.sh`、四类工具安装脚本 | 系统运行库和 APT 工具 |
| 工具组装 | `docker/prepare-tool-data.sh` | 版本清单和小型字典 |
| Python | `docker/install-python-runtime.sh` | Python 安装工具和独立 Volatility3 环境 |
| 最终镜像 | `docker/finalize-base.sh`、`docker/verify-base.sh` | 动态库接入、vol 包装命令和最终校验 |

### 6.3 工具清单与环境边界

48 个 APT 工具包均按固定版本实际安装，最终再次核对包版本和命令；不存在只声明 `ARG` 却未安装的工具。

| 脚本 | 包数量 | 工具 |
| --- | --- | --- |
| `docker/install-network.sh` | 13 | Nmap、Masscan、Rustscan、Amass、Subfinder、Nuclei、Fierce、Dnsenum、AutoRecon、theHarvester、Responder、NetExec、Enum4linux-ng |
| `docker/install-web.sh` | 16 | Gobuster、Feroxbuster、Dirsearch、FFUF、Dirb、HTTPX Toolkit、Katana、Hakrawler、SQLMap、Arjun、ParamSpider、Dalfox、Wafw00f、Qsreplace、Uro、Wfuzz |
| `docker/install-password.sh` | 9 | Hydra、John、Hashcat、Medusa、Patator、CrackMapExec、Evil-WinRM、Hash-Identifier、Ophcrack CLI |
| `docker/install-binary.sh` | 10 | GDB、Radare2、Binwalk、Ghidra、Checksec、Binutils、XXD、Foremost、Steghide、ExifTool |

Masscan、Dirb、Ophcrack CLI、Foremost 按架构选择固定版本。
ExifTool 包名为 `libimage-exiftool-perl`，NetExec 命令为 `nxc`，HTTPX Toolkit 提供 `httpx`，Binutils 提供 `strings`、`objdump`。
另外安装 Gau、Waybackurls、Anew、X8、Nikto、WPScan、Volatility3；清单路径保持 `/opt/hexstrike/tool-versions.lock`。

Kali 系统 Python 保持不变；另提供 Python 3.11。Volatility3 使用 `/opt/volatility3-venv`，应用使用 `/opt/hexstrike-venv`。
项目依赖仍排除 `pwntools`、`angr`、`bcrypt`。应用 venv 优先的 PATH 保持不变，只有同名 `httpx` 命令链接到安全工具。
应用 Python 的 `httpx` 库导入不受影响；基础镜像固定版本 pip 通过 `--python` 管理应用环境。

## 7. 缓存与重建限制

APT 索引、下载和 SecLists 缓存按架构隔离。最小 Kali 的 HTTPS 由官方 Python 镜像 CA 引导，显式配置 APT 信任路径；
保留 TLS 和签名校验，索引失败立即中止，移除下载后清理钩子以复用包缓存。

可选远程缓存使用以下四个独立引用，不与发布标签混用：

| 用途 | 完整缓存引用 |
| --- | --- |
| AMD64 基础 | `harbor.everoffice.cn/harbor-cucc/pentest-tools-base:buildcache-amd64` |
| ARM64 基础 | `harbor.everoffice.cn/harbor-cucc/pentest-tools-base:buildcache-arm64` |
| AMD64 应用 | `harbor.everoffice.cn/harbor-cucc/pentest-tools:buildcache-amd64` |
| ARM64 应用 | `harbor.everoffice.cn/harbor-cucc/pentest-tools:buildcache-arm64` |

仅在构建器支持 registry 缓存时，才向对应构建命令添加 `--cache-from` / `--cache-to` 并使用表中完整引用。
缓存标签允许更新；普通本地两步构建不依赖远程缓存。

Kali 滚动仓库可能移除历史包，传递依赖和项目 Python 依赖也并非全部固定，锁定工具版本不代表任意时间都能重建。
X8 4.3.0 锁定的 time 0.3.21 需要 Rust 1.79.0；不升级 X8 或锁文件，编译器不进入最终镜像。
大型字典、Nuclei 模板、彩虹表和 Volatility 符号表不内置，通过挂载或运行时准备。
AutoRecon 依赖安装的 SecLists 数据只写入构建缓存；需要时挂载到 `/usr/share/seclists`，包元数据不代表数据已经可用。
