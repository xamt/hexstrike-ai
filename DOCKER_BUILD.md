# 工具基础镜像与应用镜像构建说明

## 1. 镜像与构建顺序

只构建 AMD64、ARM64 两种独立镜像，不创建多架构入口。每个架构先构建基础镜像，再构建应用镜像。

| 用途 | AMD64 | ARM64 |
| --- | --- | --- |
| 基础镜像 | `harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.1.0-amd64` | `harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.1.0-arm64` |
| 应用镜像 | `harbor.everoffice.cn/harbor-cucc/pentest-tools:1.1.0-amd64` | `harbor.everoffice.cn/harbor-cucc/pentest-tools:1.1.0-arm64` |

- 基础镜像：Kali、安全工具、五类数据库客户端、小型字典、Python 3.11、独立 Volatility3 环境；默认进入 Bash，不启动服务。
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
  --tag harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.1.0-amd64 \
  --load \
  --progress=plain \
  "."
```

### 2.2 ARM64 基础镜像

```bash
docker buildx build \
  --platform linux/arm64 \
  --file "Dockerfile.base" \
  --tag harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.1.0-arm64 \
  --load \
  --progress=plain \
  "."
```

默认使用阿里云 Kali 源。需要切换到 Kali 官方分发地址时，在对应命令的 `--load` 前增加
`--build-arg KALI_APT_MIRROR=http://http.kali.org/kali`；仍验证 Kali 官方签名。
软件包版本不存在或下载失败时直接中止，不自动升级或跳过工具。

基础镜像和应用镜像的 Python 包默认使用国内清华 PyPI 源：`https://pypi.tuna.tsinghua.edu.cn/simple`，
原构建命令无需额外参数。该地址是清华镜像站支持的服务域名，使用 HTTPS 并保留证书校验。[镜像站说明](https://mirrors.tuna.tsinghua.edu.cn/help/pypi/)
基础镜像中的 pip、setuptools、wheel、Volatility3，以及应用镜像的项目 Python 依赖，均显式使用这个源。
这次调整下载来源，不增加超时时间，不改变固定工具版本，也不自动回退到其他源。
需要显式切回官方 PyPI 时，在对应构建命令中加入 `--build-arg PIP_INDEX_URL=https://pypi.org/simple`。
国内镜像仍可能短暂不同步或连接异常；缺少固定版本时应排查包源，而不是放宽版本限制。
此配置只作用于 Python 包；Kali 仍使用既有阿里云源，Go、Rust、GitHub 的下载配置不变。

## 3. 构建应用镜像

### 3.1 AMD64 应用镜像

先完成第 2.1 节。

```bash
docker buildx build \
  --platform linux/amd64 \
  --file "Dockerfile" \
  --build-arg BASE_IMAGE=harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.1.0-amd64 \
  --tag harbor.everoffice.cn/harbor-cucc/pentest-tools:1.1.0-amd64 \
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
  --build-arg BASE_IMAGE=harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.1.0-arm64 \
  --tag harbor.everoffice.cn/harbor-cucc/pentest-tools:1.1.0-arm64 \
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
  harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.1.0-amd64 \
  harbor.everoffice.cn/harbor-cucc/pentest-tools:1.1.0-amd64 \
  amd64
```

### 4.3 ARM64 镜像验收

```bash
bash "docker/test-images.sh" \
  harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.1.0-arm64 \
  harbor.everoffice.cn/harbor-cucc/pentest-tools:1.1.0-arm64 \
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
  harbor.everoffice.cn/harbor-cucc/pentest-tools:1.1.0-amd64
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
  harbor.everoffice.cn/harbor-cucc/pentest-tools:1.1.0-arm64
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
  harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.1.0-amd64 amd64
```

ARM64：

```bash
python3 "tests/verify_docker_cache.py" \
  harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.1.0-arm64 arm64
```

该脚本会实际构建临时应用镜像：只改代码时复用依赖层，只改依赖时重新安装项目依赖，基础镜像保持不变。
同时验证 Volatility3 不受影响；源码不变，临时标签在结束时清理。

## 5. 发布独立镜像

对应架构完成构建与验收后再推送，不合并镜像。若版本已发布，应先换用新版本。

### 5.1 AMD64

```bash
docker push harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.1.0-amd64
docker push harbor.everoffice.cn/harbor-cucc/pentest-tools:1.1.0-amd64
```

### 5.2 ARM64

```bash
docker push harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.1.0-arm64
docker push harbor.everoffice.cn/harbor-cucc/pentest-tools:1.1.0-arm64
```

正式应用发布时，先推送并记录**同架构基础镜像**的真实摘要，将第 3 节 `BASE_IMAGE` 的值替换为
`harbor.everoffice.cn/harbor-cucc/pentest-tools-base@sha256:<该架构的真实摘要>`，再重建、验收并推送应用。
占位内容不能原样执行；不要把 ARM64 基础摘要用于 AMD64 构建。
部署时记录应用摘要和基础摘要；回滚直接部署上一版应用，不覆盖旧基础镜像。

## 6. Dockerfile 与脚本如何维护

### 6.1 版本与安装逻辑就近维护

`Dockerfile.base` 只保留上游镜像、Kali/PyPI 软件源和平台配置；不再声明或传递工具版本。
工具版本直接定义在对应安装脚本中，查看安装方式时即可找到版本，不需要跨文件追踪。

| 修改内容 | 唯一维护位置 |
| --- | --- |
| APT 工具版本、架构差异 | 对应的 `docker/install-network.sh`、`install-web.sh`、`install-password.sh`、`install-binary.sh` |
| Gau、Waybackurls、Anew | `docker/install-go-tool.sh` |
| Rust 编译工具链 | `docker/install-rust-toolchain.sh`；后续 Cargo 使用该阶段选定的默认工具链 |
| X8 | `docker/install-x8.sh` |
| Nikto | `docker/install-nikto-source.sh` |
| WPScan | `docker/install-web.sh` |
| pip、setuptools、wheel、Volatility3 | `docker/install-python-runtime.sh` |
| MySQL（MariaDB 兼容）、Redis、PostgreSQL 客户端 | `docker/install-database-apt.sh` |
| ClickHouse 客户端及双架构摘要 | `docker/install-database-clickhouse.sh` |
| MongoDB Shell 及双架构摘要 | `docker/install-database-mongodb.sh` |

修改工具版本时直接编辑上述脚本；不再通过 `--build-arg NMAP_VERSION=...` 等参数覆盖。
源地址和上游镜像仍可通过 Dockerfile 中的构建参数覆盖。现有工具版本及架构差异均未改变。
`OUTPUT_DIR`、`TOOL_RECORD_DIR` 仅供离线检查隔离临时输出；镜像构建不覆盖这些路径。

安装成功后，脚本调用 `docker/record-tool-version.sh` 保存其声明的**预期版本**，而不是把查询到的实际版本当成预期值。
Go、Rust、Nikto、Python 阶段的记录随产物一起复制，最终汇总到 `/opt/hexstrike/tool-versions.d/`。
最终校验不再维护第二份版本号：`docker/verify-tool-versions.py` 读取记录，与实际安装的包状态、版本和架构比对；
Go/X8 二进制及 Nikto 主程序还会比对构建阶段记录的 SHA256，防止复制后产物发生变化。
记录缺失、冲突、架构不符或版本漂移均使构建失败；全部校验通过后，才生成原路径 `/opt/hexstrike/tool-versions.lock`。
记录目录属于构建产物，不是另一套需要手工编辑的配置。校验器只保存必需工具名称，不保存版本常量。

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
| 数据库客户端 | `docker/install-database-apt.sh`、`install-database-clickhouse.sh`、`install-database-mongodb.sh` | 五类客户端；公共下载校验由 `install-database-deb.sh` 负责 |
| 工具组装 | `docker/prepare-tool-data.sh` | 小型字典；安装记录由各工具脚本产生 |
| Python | `docker/install-python-runtime.sh` | Python 安装工具和独立 Volatility3 环境 |
| 最终镜像 | `docker/finalize-base.sh`、`docker/verify-base.sh`、`docker/verify-tool-versions.py` | 动态库接入、vol 包装命令、版本核对与清单生成 |

### 6.3 工具清单与环境边界

48 个 APT 工具包均有固定版本安装步骤，最终再次核对完整安装状态、包版本和命令，不能仅凭版本变量或安装记录判定成功。

| 脚本 | 包数量 | 工具 |
| --- | --- | --- |
| `docker/install-network.sh` | 13 | Nmap、Masscan、Rustscan、Amass、Subfinder、Nuclei、Fierce、Dnsenum、AutoRecon、theHarvester、Responder、NetExec、Enum4linux-ng |
| `docker/install-web.sh` | 16 | Gobuster、Feroxbuster、Dirsearch、FFUF、Dirb、HTTPX Toolkit、Katana、Hakrawler、SQLMap、Arjun、ParamSpider、Dalfox、Wafw00f、Qsreplace、Uro、Wfuzz |
| `docker/install-password.sh` | 9 | Hydra、John、Hashcat、Medusa、Patator、CrackMapExec、Evil-WinRM、Hash-Identifier、Ophcrack CLI |
| `docker/install-binary.sh` | 10 | GDB、Radare2、Binwalk、Ghidra、Checksec、Binutils、XXD、Foremost、Steghide、ExifTool |

Masscan、Dirb、Ophcrack CLI、Foremost 按架构选择固定版本。
ExifTool 包名为 `libimage-exiftool-perl`，NetExec 命令为 `nxc`，HTTPX Toolkit 提供 `httpx`，Binutils 提供 `strings`、`objdump`。
另外安装 Gau、Waybackurls、Anew、X8、Nikto、WPScan、Volatility3；清单路径保持 `/opt/hexstrike/tool-versions.lock`。

### 6.4 数据库客户端（1.1.0 新增）

本次仅增加镜像内客户端环境，不新增 HTTP/MCP 接口，也不修改现有 `/health` 检查清单。

原安全工具版本不变；基础镜像和应用镜像使用新的 `1.1.0-amd64` / `1.1.0-arm64` 标签，应用通过继承新版基础镜像获得客户端，旧基础镜像不包含本次新增环境。

| 客户端命令 | 固定版本 | 安装来源 |
| --- | --- | --- |
| `mysql` | MariaDB `1:11.8.9+ds-2` | Kali 签名仓库，client/core/compat 三个包同步锁定 |
| `redis-cli` | `5:8.0.6-3` | Kali `redis-tools` |
| `psql` | `18.6-3` | Kali `postgresql-client-18` |
| `clickhouse-client` | `25.8.20.4` | ClickHouse 官方固定版本客户端及 `clickhouse-common-static` |
| `mongosh` | `2.13.0` | MongoDB 官方独立 Shell 包 |

`mysql` 是用户选定的 MariaDB 兼容客户端，不是 Oracle MySQL 官方客户端，也不是 Python 的 mysqlclient 驱动。
不新增 MySQL、Redis、PostgreSQL、MongoDB 或 ClickHouse 的服务端包，不配置或启动数据库服务。
ClickHouse 官方客户端必须依赖公共多功能二进制，因此其底层二进制仍包含服务端子命令能力；这里不安装 `clickhouse-server` 服务包。
MongoDB 仅提供 `mongosh`，不包含旧 `mongo` 命令或数据库备份工具套件。

五类客户端均提供 AMD64、ARM64 安装路径；Kali 包沿用阿里云镜像和官方签名验证。
ClickHouse、MongoDB 通过 HTTPS 下载官方固定版本 `.deb`，先核对安装脚本锁定的 SHA256、包名、版本、架构再安装；不添加第三方全局 APT 源、不使用未经验证的下载代理。
摘要来自 [ClickHouse 官方 AMD64 索引](https://packages.clickhouse.com/deb/dists/stable/main/binary-amd64/Packages)、[ARM64 索引](https://packages.clickhouse.com/deb/dists/stable/main/binary-arm64/Packages)，以及 [MongoDB 官方发行](https://github.com/mongodb-js/mongosh/releases/tag/v2.13.0)（并与官方 APT 索引交叉核对）。
官方来源不可达、固定包消失、摘要不符均直接失败，不静默换版本或跳过客户端。

最终构建校验新增五个命令及 `--version` 检查，版本清单记录八个新增客户端/支撑包；不连接数据库、不执行查询。
该修改只完成离线检查，实际双架构构建、客户端连接与数据库操作验收由使用者执行。

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

## 8. Agent 使用渗透测试技能（无需本机 Python / MCP）

应用容器启动后，可将本仓库的 `skills/pentest-tools/` **整个目录**导入支持技能和命令执行的 Agent。入口为 `SKILL.md`，`scripts/` 和 `references/` 需要一起保留；不再使用原来的 stdio MCP 配置。原 `hexstrike_mcp.py` 留作兼容与维护参考。

技能按测试目标选择流程，不要求用户先知道工具名：

| 方向 | 流程与交付 |
| --- | --- |
| 资产清单 | 输入定界 → 候选发现 → 归属/解析复核 → 存活与服务识别 → 可追溯资产清单 |
| Web / API 渗透 | 基线与身份 → 应用建模 → 具体假设 → 最小复核 → 发现、覆盖矩阵与复测条件 |
| 容器安全 | 区分镜像/部署/运行时/集群 → 检查真实能力 → 分层验证 → 风险及未覆盖项 |

用户可直接说“梳理指定域名的资产清单，不做漏洞扫描”或“评估这份 Kubernetes 配置，暂不连接集群”。技能按边界执行，不自动把清单任务升级成漏洞验证，也不因容器工具缺失而安装工具或扩大权限。详细阶段见 `skills/pentest-tools/references/workflows/`。

运行环境需要 Node.js 22 或更高版本，不需要 Python、requests、MCP SDK 或 npm install。调用器使用 Node.js 内置 fetch 直接访问 HTTP API；工具仍在容器中执行。

以下在仓库根目录执行，仅列出本地定义，不访问服务：

```bash
node "skills/pentest-tools/scripts/run.mjs" list
node "skills/pentest-tools/scripts/run.mjs" describe nmap_scan
```

服务地址默认 `http://127.0.0.1:8888`，可用 `PENTEST_SERVER_URL` 或单次 `--server` 覆盖。注意地址相对于 Agent 后端，不是浏览器所在机器。下面仅请求健康接口，不执行扫描：

```bash
node "skills/pentest-tools/scripts/run.mjs" call server_health --server http://127.0.0.1:8888
```

技能保留原 150 个唯一工具名，并将第二个重复 HTTPx 定义命名为 `httpx_probe_extended`，共 151 个可调用入口。详细参数用 `describe` 按需读取。调用通过 `--input` 读取 JSON 文件或 `--input -` 读取 stdin；无需激活虚拟环境。

本次仅完成离线参数/请求/返回对照及模拟 HTTP 验证，未运行镜像构建、真实服务联调或扫描。技能不是新的安全工具安装包，可选工具缺失仍会导致相应接口失败。
