# 工具基础镜像与应用镜像构建说明

## 1. 镜像与构建顺序

只构建 AMD64、ARM64 两种独立镜像，不创建多架构入口。每个架构先构建基础镜像，再构建应用镜像。

| 用途 | AMD64 | ARM64 |
| --- | --- | --- |
| 基础镜像 | `harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.3.3-amd64` | `harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.3.3-arm64` |
| 应用镜像 | `harbor.everoffice.cn/harbor-cucc/pentest-tools:1.3.3-amd64` | `harbor.everoffice.cn/harbor-cucc/pentest-tools:1.3.3-arm64` |

- 基础镜像：Kali、安全工具、小型字典、Python 3.11，以及隔离的 Volatility 2/3、JWT-Tool、ParamSpider、Kube-Hunter 环境；默认进入 Bash，不启动服务。
- 应用镜像：继承同架构基础镜像，安装项目依赖、复制代码、配置 8888 端口和健康检查，不重复安装安全工具。
- 两类镜像版本独立管理，应用镜像引用同架构的基础镜像。
- 本项目发布标签不使用 `latest`；已发布的版本标签不可覆盖。调整版本时直接修改对应命令中的完整镜像名。

本版撤回新增数据库接口、技能声明与 MySQL/MariaDB、ClickHouse、Redis、PostgreSQL、MongoDB 客户端的专门安装步骤。
保留原有 SQLMap 等安全工具自身的数据库测试能力；其间接依赖不作为独立数据库客户端能力承诺。
恢复以 `1c865493^` 为基准的 MCP 参数契约，优先由固定工具版本、隔离运行时和命令入口适配原接口；
不以新版工具的参数替换原有接口。五个补充工具 testssl.sh、WhatWeb、JWT-Tool、TruffleHog、tcpdump 及其版本保持不变。
1.3.3 保留上一版的 Kube-Bench、Kube-Hunter、kubectl、Helm 和 Docker CLI，不默认安装 Trivy 或 Clair。
本版主要修复旧接口的命令兼容：Dalfox 固定为官方 `v2.12.0`，其他工具版本不变；AutoRecon、Hakrawler 的既有 MCP 默认参数由基础镜像兼容入口承接，不要求调用方更改默认值。版本差异与接口使用边界见第 6.8 节。

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
  --tag harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.3.3-amd64 \
  --load \
  --progress=plain \
  "."
```

### 2.2 ARM64 基础镜像

```bash
docker buildx build \
  --platform linux/arm64 \
  --file "Dockerfile.base" \
  --tag harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.3.3-arm64 \
  --load \
  --progress=plain \
  "."
```

下载源及覆盖参数见第 5 节。

## 3. 构建应用镜像

### 3.1 AMD64 应用镜像

先完成第 2.1 节。

```bash
docker buildx build \
  --platform linux/amd64 \
  --file "Dockerfile" \
  --build-arg BASE_IMAGE=harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.3.3-amd64 \
  --tag harbor.everoffice.cn/harbor-cucc/pentest-tools:1.3.3-amd64 \
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
  --build-arg BASE_IMAGE=harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.3.3-arm64 \
  --tag harbor.everoffice.cn/harbor-cucc/pentest-tools:1.3.3-arm64 \
  --load \
  --progress=plain \
  "."
```

命令显式指定基础镜像，避免选错架构。省略 `BASE_IMAGE` 时，Dockerfile 依据 BuildKit 的 `TARGETARCH`
选择对应架构标签，不引用公共多架构标签。[Docker 参数说明](https://docs.docker.com/reference/dockerfile/#automatic-platform-args-in-the-global-scope)

## 4. 启动应用镜像

下面两条启动命令包含 John/Hashcat 默认字典和 Nuclei 离线模板的只读挂载。执行前，将 `/path/to/rockyou.txt`
替换为宿主机上真实、可读且已解压的 `rockyou.txt` 文件的绝对路径；不能直接挂载 `rockyou.txt.gz`。
宿主机文件须提前准备好，离线运行环境应提前传入该文件。`--mount` 在源文件不存在时会直接报错，避免误建同名目录。
将 `/path/to/nuclei-templates` 替换为宿主机上已准备好的完整模板根目录绝对路径（准备要求见 4.4），不要指向归档文件或多包了一层的父目录。
两份数据的固定下载地址、联网准备、离线转移及解压步骤见 **4.5**；先完成数据准备，再运行 4.1 或 4.2 的启动命令。
以下命令假定对应架构的 `1.3.3` 应用镜像已导入离线 Docker 主机，或可从内网 Harbor 获取；仅准备数据不能代替镜像准备。

### 4.1 AMD64 应用

```bash
docker run --detach \
  --name pentest-tools-amd64 \
  --platform linux/amd64 \
  --publish 127.0.0.1:8888:8888 \
  --mount "type=bind,source=/path/to/rockyou.txt,target=/usr/share/wordlists/rockyou.txt,readonly" \
  --mount "type=bind,source=/path/to/nuclei-templates,target=/opt/nuclei-templates,readonly" \
  harbor.everoffice.cn/harbor-cucc/pentest-tools:1.3.3-amd64
```

### 4.2 ARM64 应用

```bash
docker run --detach \
  --name pentest-tools-arm64 \
  --platform linux/arm64 \
  --publish 127.0.0.1:8888:8888 \
  --mount "type=bind,source=/path/to/rockyou.txt,target=/usr/share/wordlists/rockyou.txt,readonly" \
  --mount "type=bind,source=/path/to/nuclei-templates,target=/opt/nuclei-templates,readonly" \
  harbor.everoffice.cn/harbor-cucc/pentest-tools:1.3.3-arm64
```

服务地址为 `http://127.0.0.1:8888`。两条命令使用相同的宿主机端口，不要同时运行。
使用 `docker logs pentest-tools-amd64` 或 `docker logs pentest-tools-arm64` 查看日志。
停止容器时使用对应名称执行 `docker stop`，删除已停止的容器使用 `docker rm`。

默认仅绑定本机地址。确需原始套接字或网络管理时再添加 `--cap-add NET_RAW --cap-add NET_ADMIN`，不要直接使用 `--privileged`。
实时抓包和内网协议工具只能操作容器可见的网络接口；Docker Desktop 不等同于 Linux 宿主机二层网络直通。

### 4.3 John/Hashcat 默认字典为什么需要挂载

John 和 Hashcat 的现有 MCP 接口默认读取 `/usr/share/wordlists/rockyou.txt`。
基础镜像安装了工具程序，但为控制镜像体积、避免重复构建携带大型数据，没有内置或自动下载这份字典。
因此，服务能够启动、工具命令能够被发现，并不代表默认字典攻击可以执行；未挂载且未指定其他字典时，会因缺少文件而失败。

只挂载上述单个文件，不要用不完整的宿主机目录覆盖整个 `/usr/share/wordlists`，以免遮蔽镜像内已有的小型字典。
只读挂载不增加镜像层，也能避免容器修改宿主机字典。
不使用 John/Hashcat 的默认字典功能时，可以省略这项挂载；使用其他字典时，应先将其挂载到容器，再通过接口的 `wordlist` 指定容器内路径。
待处理的哈希文件也需另行提供给容器，字典挂载不包含输入文件。

### 4.4 Nuclei 离线模板准备与挂载

镜像安装 Nuclei 引擎，不固化完整模板。当前默认入口只使用本地模板，不会在首次扫描时下载模板、检查更新或更新引擎。
使用默认 MCP 调用前，必须按上面的启动命令将模板根目录只读挂载到 `/opt/nuclei-templates`；缺少目录、空目录或没有非空 YAML 模板时明确失败，不自动改用在线源。
不使用 Nuclei 时可以省略该挂载，不影响 HTTP 服务和其他工具启动，但工具可被健康检查发现不代表模板已就绪。

本文为当前 `1.3.3` 镜像固定使用 **Nuclei 3.11.1 + nuclei-templates v10.4.2** 作为离线数据基线，不下载浮动的 latest。
模板 v10.4.2 发布于 2026-04-15，早于引擎 v3.11.1；选择固定的较早模板集，避免随最新版引入当前引擎不支持的新语法。
这是一组固定部署基线，不是上游提供的一对一兼容矩阵，也不表示所有模板都具备运行条件。本次已核对下载归档、官方校验值和目录结构，未进行容器内完整模板编译或扫描验证。
依据：[模板发布说明](https://github.com/projectdiscovery/nuclei-templates/releases/tag/v10.4.2)、[引擎发布说明](https://github.com/projectdiscovery/nuclei/releases/tag/v3.11.1)。
该模板快照不会包含其发布之后新增的检测规则；后续更新需同时评估引擎兼容性，不能直接替换成 latest。

第 4.5 节给出直接下载与解压命令，保留完整目录结构、隐藏文件和辅助数据（例如 helpers、workflows）。
归档及校验文件在联网机器准备，再经部署介质传入运行环境；运行时不要求容器访问 GitHub，也不需要重新构建基础镜像。

兼容入口通过 `NUCLEI_TEMPLATES_DIR` 指定模板根目录（默认 `/opt/nuclei-templates`），追加 `-duc` 禁止更新检查，
并禁用公共及自定义仓库的自动模板下载。现有 `template` 参数仍可选择容器内的本地 YAML 文件或目录；逗号分隔的多个本地路径、相对于模板根目录的路径及本地通配符也支持。
不接受远程模板 URL 或更新命令，模板更新应在准备环境完成后更换挂载内容。模板选择只检查本地文件存在和基本可读性，具体语法和执行错误由 Nuclei 原生引擎返回。

默认追加 `-ni` 禁用 Interactsh 外部回连，依赖 OAST 的模板不会执行；这属于离线模式的检测范围限制，不代表这些风险不存在。
其他模板仍会访问目标，部分模板可能另有外部 API、浏览器或辅助程序依赖，因此本入口不是网络隔离沙箱，也不保证所有模板都能在无外网环境工作。
模板挂载可只读，但容器内 Nuclei 的用户配置目录、缓存和临时目录仍需可写；不要仅凭模板只读就将整个容器根文件系统改成只读。

### 4.5 离线数据的下载、转移与解压

#### 4.5.1 下载来源与准备条件

| 数据 | 固定来源 | 当前镜像如何使用 |
| --- | --- | --- |
| Nuclei 模板 | [ProjectDiscovery 官方 v10.4.2 归档](https://github.com/projectdiscovery/nuclei-templates/archive/refs/tags/v10.4.2.tar.gz) | 配合镜像内 Nuclei 3.11.1，挂载完整模板目录，不需要在宿主机安装 Nuclei。 |
| RockYou 字典 | [SecLists 官方 2025.3 中的 rockyou.txt.tar.gz](https://raw.githubusercontent.com/danielmiessler/SecLists/2025.3/Passwords/Leaked-Databases/rockyou.txt.tar.gz) | 只下载这一个字典归档，不下载整个 SecLists；解压得到普通文本文件，可供当前 John/Hashcat 使用，不区分 CPU 架构。 |

模板归档约 8.8 MiB；RockYou 归档约 50.8 MiB，解压后的 `rockyou.txt` 为 139921497 字节（约 133.4 MiB）。
RockYou 是历史字典，不需要与工具版本号一一对应；不要用小型示例字典、rockyou2021/2024 等不同数据集替换后仍宣称是同一份文件。
下载命令适用于联网的 macOS/Linux 主机，需要 Bash、curl、tar、gzip，以及 `sha256sum` 或 macOS 自带的 `shasum`。
离线主机仅需解压和校验工具；两种架构共用同一份数据。建议为归档、解压数据和后续更新保留至少 1 GiB 空间。
所有步骤都在项目目录外的 `$HOME/pentest-offline-1.3.3` 中执行，不将大文件加入 Git 或 Docker 构建上下文。

#### 4.5.2 在联网机器下载并生成交付校验清单

以下整段在 **Bash** 中执行。HTTP/1.1 用于避开部分链路的 HTTP/2 中断；下载失败会停止，临时文件不会被当作完成文件。
若网络无法连接 GitHub，应在可访问官方源的准备机器完成下载，再通过内网文件仓库或介质转移；不要在离线容器里执行这些下载命令。

```bash
(
  set -eu
  mkdir -p "$HOME/pentest-offline-1.3.3"
  cd "$HOME/pentest-offline-1.3.3"

  curl --http1.1 --fail --location --retry 5 \
    --output "nuclei-templates-10.4.2.tar.gz.part" \
    "https://github.com/projectdiscovery/nuclei-templates/archive/refs/tags/v10.4.2.tar.gz"
  mv "nuclei-templates-10.4.2.tar.gz.part" "nuclei-templates-10.4.2.tar.gz"

  curl --http1.1 --fail --location --retry 5 \
    --output "rockyou-seclists-2025.3.tar.gz.part" \
    "https://raw.githubusercontent.com/danielmiessler/SecLists/2025.3/Passwords/Leaked-Databases/rockyou.txt.tar.gz"
  mv "rockyou-seclists-2025.3.tar.gz.part" "rockyou-seclists-2025.3.tar.gz"

  gzip -t "nuclei-templates-10.4.2.tar.gz"
  gzip -t "rockyou-seclists-2025.3.tar.gz"
  printf '%s\n' '5f416b77da1397adb0e19aedf1b2744dc715673465c64b3031b53ad31a1bf6c9  nuclei-templates-10.4.2.tar.gz' > "SHA256SUMS"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -c "SHA256SUMS"
    sha256sum "rockyou-seclists-2025.3.tar.gz" >> "SHA256SUMS"
  else
    shasum -a 256 -c "SHA256SUMS"
    shasum -a 256 "rockyou-seclists-2025.3.tar.gz" >> "SHA256SUMS"
  fi
)
```

Nuclei 的 SHA-256 来自 [官方 v10.4.2 校验清单](https://github.com/projectdiscovery/nuclei-templates/releases/download/v10.4.2/nuclei-templates-10.4.2_checksums.txt)，本次也已对实际下载归档核对一致。
RockYou 的 SHA-256 在可信联网准备机器上根据实际下载生成，用于验证离线转移未损坏或被替换，**不是 SecLists 发布者的独立签名**。
应通过可信渠道保留、传递校验清单；若归档和清单同时被替换，单独校验两者不能证明来源可信。

#### 4.5.3 将文件转入离线运行主机

将联网机器上 `$HOME/pentest-offline-1.3.3` 中以下三个文件整体复制到离线运行用户的 `$HOME/pentest-offline-1.3.3`：

```text
pentest-offline-1.3.3/
├── nuclei-templates-10.4.2.tar.gz
├── rockyou-seclists-2025.3.tar.gz
└── SHA256SUMS
```

可使用离线介质或内部文件传输，不需要运行主机有外网。保留本节文档或下载来源记录，便于追溯固定版本。
复制完成后，在 **离线主机** 执行下一步；联网准备机器与 Docker 主机不是同一台时，不要挂载准备机器上的路径。

#### 4.5.4 离线核对并解压

以下整段在离线主机的 **Bash** 中执行，无任何下载命令。校验失败立即停止，不能跳过校验继续解压。
解压目标 `runtime` 必须尚不存在，以免把不同版本模板混在一起；已有目录时，应保留旧数据，另选新的版本化准备目录，不要直接覆盖或清空。

```bash
(
  set -eu
  cd "$HOME/pentest-offline-1.3.3"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -c "SHA256SUMS"
  else
    shasum -a 256 -c "SHA256SUMS"
  fi

  mkdir "runtime"
  mkdir "runtime/nuclei-templates"
  mkdir "runtime/wordlists"
  tar -xzf "nuclei-templates-10.4.2.tar.gz" \
    -C "runtime/nuclei-templates" --strip-components=1
  tar -xzf "rockyou-seclists-2025.3.tar.gz" \
    -C "runtime/wordlists" "rockyou.txt"

  test -s "runtime/wordlists/rockyou.txt"
  test -d "runtime/nuclei-templates/http"
  test -d "runtime/nuclei-templates/helpers"
  test -d "runtime/nuclei-templates/workflows"
  test -f "runtime/nuclei-templates/.nuclei-ignore"
  chmod -R u+rX "runtime"
  printf 'RockYou 宿主机绝对路径：%s/runtime/wordlists/rockyou.txt\n' "$(pwd -P)"
  printf 'Nuclei 模板宿主机绝对路径：%s/runtime/nuclei-templates\n' "$(pwd -P)"
)
```

`--strip-components=1` 仅去掉模板归档的外层 `nuclei-templates-10.4.2/`，保留内部相对路径和隐藏文件。
RockYou 下载的是 **tar.gz 归档**，不能仅用 `gzip -dc` 将其输出重定向成 `rockyou.txt`，否则得到的是 tar 数据而非字典正文；也不要用文本编辑器转码或重新保存字典。

#### 4.5.5 按架构挂载并启动

把上一步输出的两个绝对路径代入 4.1（AMD64）或 4.2（ARM64）启动命令：

| 启动命令中的占位符 | 替换为离线 Docker 主机上的实际路径 | 容器内固定位置 |
| --- | --- | --- |
| `/path/to/rockyou.txt` | `$HOME/pentest-offline-1.3.3/runtime/wordlists/rockyou.txt` 展开后的绝对路径 | `/usr/share/wordlists/rockyou.txt` |
| `/path/to/nuclei-templates` | `$HOME/pentest-offline-1.3.3/runtime/nuclei-templates` 展开后的绝对路径 | `/opt/nuclei-templates` |

两项都保持 `readonly`。不要将 `.tar.gz` 本身挂载进去，也不要把 `runtime` 的父目录当成模板根目录。
Docker Desktop 使用当前宿主机目录时，需允许该目录被文件共享；远程 Docker context 则必须在 Docker daemon 所在主机准备这些文件。
已有容器不能通过 `docker restart` 添加挂载：先保留需要的结果，再停止并删除旧容器，按相应架构的启动命令重新创建。
模板和字典均为运行数据，补充或更换挂载不需要重建镜像。解压中断或升级数据时采用新目录，避免把未完成的数据交给运行中的容器。

## 5. 构建下载源

原构建命令默认使用下列源，无需额外设置环境变量。

| 下载内容 | 默认来源 | 构建参数 |
| --- | --- | --- |
| Kali 软件包 | 阿里云 Kali 镜像 `https://mirrors.aliyun.com/kali` | `KALI_APT_MIRROR` |
| 基础镜像及应用镜像的 Python 包 | 清华 PyPI 镜像 `https://pypi.tuna.tsinghua.edu.cn/simple` | `PIP_INDEX_URL` |
| Gau、Waybackurls、Anew、Dalfox 的 Go 模块 | `https://goproxy.cn` | `GOPROXY` |
| Go 模块校验数据 | `sum.golang.org https://goproxy.cn/sumdb/sum.golang.org` | `GOSUMDB` |
| Rust、RubyGems、GitHub 固定源码归档及 Kube-Bench 发布包 | 各自配置的上游来源 | 不由上述参数覆盖 |

需要切换来源时，在对应构建命令的 `--load` 前添加参数：

- Kali 官方分发源：`--build-arg KALI_APT_MIRROR=http://http.kali.org/kali`。
- 官方 PyPI：`--build-arg PIP_INDEX_URL=https://pypi.org/simple`。
- 官方 Go 源：同时添加 `--build-arg GOPROXY=https://proxy.golang.org` 和 `--build-arg GOSUMDB=sum.golang.org`。

Kali 和 Go 参数只用于基础镜像构建，PyPI 参数可用于两种镜像构建。
宿主机的 `go env -w` 不会自动传入 Docker 构建。
国内代理配置保留 HTTPS 与官方校验机制，不自动切换到其他下载源。

来源说明：[清华 PyPI](https://mirrors.tuna.tsinghua.edu.cn/help/pypi/)、[Goproxy.cn](https://goproxy.cn/)、[Go 模块校验](https://go.dev/ref/mod#authenticating)。

## 6. 基础镜像包含的工具

以下按基础镜像 1.3.3 的显式安装配置列出主要工具及用途，不把间接依赖当作单独承诺的工具。
AMD64 与 ARM64 提供相同的工具类别。命令名与软件包名可能不同，表中以实际命令入口为准。

### 6.1 网络发现与资产收集

| 工具 | 命令 | 主要用途 |
| --- | --- | --- |
| Nmap | `nmap` | 主机发现、端口扫描、服务与操作系统识别，以及 NSE 脚本检查。 |
| Masscan | `masscan` | 大批量 IP 的高速端口发现。 |
| RustScan | `rustscan` | 快速发现开放端口，可交由 Nmap 进一步识别服务。 |
| Amass | `amass` | 收集子域名、DNS 关系及外部资产信息。 |
| Subfinder | `subfinder` | 通过公开数据源被动发现子域名。 |
| Fierce | `fierce` | DNS 枚举及关联主机发现。 |
| DNSenum | `dnsenum` | 枚举 DNS 记录、名称服务器、子域名及区域传送配置。 |
| AutoRecon | `autorecon` | 编排端口扫描和服务枚举，实际能力取决于可用子工具与数据。 |
| theHarvester | `theHarvester` | 从公开数据源收集邮箱、域名、主机名和 IP。 |
| tcpdump | `tcpdump` | 采集网络报文，或读取 PCAP 文件分析协议与流量。 |

### 6.2 Web 内容、接口与参数发现

| 工具 | 命令 | 主要用途 |
| --- | --- | --- |
| Gobuster | `gobuster` | 枚举 Web 目录、文件、DNS 名称和虚拟主机。 |
| Feroxbuster | `feroxbuster` | 递归发现 Web 目录、文件和链接。 |
| Dirsearch | `dirsearch` | 使用字典、扩展名和递归规则发现隐藏路径。 |
| FFUF | `ffuf` | 对 URL、参数、请求头和虚拟主机进行模糊测试。 |
| Dirb | `dirb` | 基于字典发现 Web 服务器隐藏资源。 |
| HTTPX Toolkit | `httpx` | 批量探测 HTTP 服务、状态码、标题及技术栈；不是 Python 同名库的命令。 |
| Katana | `katana` | 抓取页面、JavaScript 端点和表单。 |
| Hakrawler | `hakrawler` | 从输入 URL 中发现链接、脚本及其他端点。 |
| Gau | `gau` | 从多个公开数据源收集历史 URL。 |
| Waybackurls | `waybackurls` | 从 Wayback Machine 收集历史 URL。 |
| Arjun | `arjun` | 发现 GET、POST、JSON 请求中的隐藏参数。 |
| ParamSpider | `paramspider` | 从历史 URL 中提取带参数的端点；固定官方旧提交 `3add9faf11fa269624a2a9e92ea12be90338cb02`，保留 `--exclude/-o/-l` 参数。 |
| X8 | `x8` | 根据响应差异发现隐藏 HTTP 参数。 |
| Anew | `anew` | 对文本行去重，仅追加尚未出现的结果。 |
| QSReplace | `qsreplace` | 批量替换 URL 查询参数值，准备测试输入。 |
| Uro | `uro` | 归并相似 URL，减少重复测试。 |
| Wfuzz | `wfuzz` | 对请求路径、参数、头部及认证字段进行模糊测试。 |

### 6.3 Web 漏洞、TLS 与凭据检查

| 工具 | 命令 | 主要用途 |
| --- | --- | --- |
| Nuclei | `nuclei` | 依据模板检查服务和 Web 应用的漏洞及配置问题。 |
| Nikto | `nikto` | 检查 Web 服务器危险文件、错误配置和已知风险。 |
| SQLMap | `sqlmap` | 检测和验证 SQL 注入及其影响。 |
| WPScan | `wpscan` | 固定 3.8.28，保留旧接口的默认插件枚举行为；检查 WordPress 核心、主题、插件风险，漏洞信息仍受数据库和 API 令牌条件限制。 |
| Dalfox v2.12.0 | `dalfox` | 发现和验证 XSS 问题；固定官方 v2 版本以原生支持现有 mining、deep-domxss 参数，通过 Go 阶段编译，不安装 Kali 的 v3 包。 |
| Wafw00f | `wafw00f` | 识别 Web 应用防火墙。 |
| WhatWeb | `whatweb` | 识别 Web 技术、服务器和 CMS 指纹。 |
| testssl.sh | `testssl` | 检查 TLS 协议、密码套件、证书及相关配置风险。 |
| JWT-Tool | `jwt_tool` | 解析 JWT，并测试签名、令牌篡改和相关认证问题。 |
| TruffleHog | `trufflehog` | 在文件、源码和 Git 历史中检测凭据泄漏，可按需验证凭据。 |

### 6.4 内网枚举与身份认证

| 工具 | 命令 | 主要用途 |
| --- | --- | --- |
| Responder | `responder` | 分析和响应 LLMNR、NBT-NS、mDNS 等名称解析请求，验证名称解析投毒及认证信息泄露风险。 |
| NetExec | `nxc` | 枚举 SMB、WinRM、LDAP、MSSQL 等服务，验证凭据与访问权限。 |
| enum4linux-ng | `enum4linux-ng` | 枚举 Windows/Samba 用户、组、共享、策略及域信息。 |
| CrackMapExec | `crackmapexec` | Windows/Active Directory 环境中的凭据与权限验证；与 NetExec 分别保留。 |
| Evil-WinRM | `evil-winrm` | 使用已有凭据通过 WinRM 连接 Windows 主机并执行远程操作。 |
| Hydra | `hydra` | 多种网络协议的在线口令验证。 |
| Medusa | `medusa` | 并行验证多种远程服务的认证凭据。 |
| Patator | `patator` | 模块化、多协议认证测试。 |
| John the Ripper | `john` | 多种密码哈希的离线恢复和强度评估。 |
| Hashcat | `hashcat` | 使用 CPU/GPU 等设备进行离线哈希恢复。 |
| Hash-Identifier | `hash-identifier` | 根据哈希特征推测可能的算法类型。 |
| Ophcrack CLI | `ophcrack-cli` | 使用彩虹表恢复 Windows LM/NTLM 哈希，无图形界面。 |

### 6.5 二进制分析与数字取证

| 工具 | 命令 | 主要用途 |
| --- | --- | --- |
| GDB | `gdb` | 调试程序，查看寄存器、内存、断点和调用栈。 |
| Radare2 | `r2`、`radare2` | 反汇编、调试、二进制修补及脚本化分析。 |
| Binwalk | `binwalk` | 识别固件中的嵌入文件、签名与压缩数据。 |
| Ghidra | `ghidra`、`analyzeHeadless` | 反汇编、反编译及无界面的批量分析。 |
| Checksec | `checksec` | 查看 ELF 文件及进程的 PIE、RELRO、NX、Canary 等保护机制。 |
| Binutils：Strings | `strings` | 提取二进制文件中的可打印字符串。 |
| Binutils：Objdump | `objdump` | 查看目标文件段、符号和反汇编结果。 |
| XXD | `xxd` | 生成十六进制转储或还原二进制数据。 |
| Foremost | `foremost` | 根据文件特征从磁盘镜像或原始数据中恢复文件。 |
| Steghide | `steghide` | 在图片、音频等载体中嵌入或提取隐藏数据。 |
| ExifTool | `exiftool` | 读取、修改和比较文件元数据。 |
| Volatility 2.6.1 | `volatility` | 分析旧版系统内存镜像，保留 `--profile`、`imageinfo` 等旧接口能力。 |
| Volatility 3（2.28.2） | `vol`、`vol.py` | 使用新版插件与符号机制分析内存；另保留 `/opt/volatility3/vol.py` Python 入口。 |

### 6.6 通用容器与 Kubernetes

| 工具 | 固定版本 | 命令 | 主要用途 |
| --- | --- | --- | --- |
| Docker CLI | 28.5.2+dfsg4-5 | `docker` | 连接授权的 Docker 服务，读取镜像、容器、网络与运行配置；不包含守护进程。 |
| kubectl | 1.33.4+ds-1 | `kubectl` | 使用授权的 kubeconfig 访问 Kubernetes API，检查资源配置、RBAC 与暴露面；不安装集群。 |
| Helm | 4.3.0+ds1-0kali1 | `helm` | 渲染、检查 Kubernetes Chart，查看或管理授权集群的应用发布。 |
| Kube-Bench | 0.16.0 | `kube-bench` | 按 CIS 基线检查 Kubernetes 节点配置；内置该发布包的检查配置。 |
| Kube-Hunter | 0.6.8 | `kube-hunter` | 发现 Kubernetes 暴露服务和已知配置风险；主动检查需要明确选择。 |

Docker CLI、kubectl、Helm 从国内 Kali 镜像安装，Helm 的包名为 `kubernetes-helm`。
Kube-Bench 使用官方双架构发布包并校验固定 SHA-256；Kube-Hunter 从国内 PyPI 安装到独立虚拟环境，工具及依赖均固定版本。
安装配置集中在 `docker/install-container-tools.sh`，按 APT、发布包和 Python 构建阶段调用，不额外拆成单工具脚本。
Docker CLI、kubectl、Helm 不新增专用 HTTP 接口；Kube-Bench、Kube-Hunter 沿用已有接口。
安装客户端不等于已获得宿主机或集群访问权限。
不自动挂载 Docker socket、kubeconfig 或服务账号，也不默认提高容器权限。

#### 体积与可选工具

按本次核对的包索引及官方发布元数据估算（2026-10-16 至 2026-10-17）：

| 组件 | AMD64 | ARM64 | 口径 |
| --- | --- | --- | --- |
| Docker CLI | 32.1 MiB | 30.1 MiB | APT 安装体积 |
| kubectl | 79.8 MiB | 77.6 MiB | APT 安装体积 |
| Helm | 63.3 MiB | 59.0 MiB | APT 安装体积 |
| Kube-Bench | 16.1 MiB | 14.3 MiB | 压缩发布包下载量，解压后更大 |
| Kube-Hunter | 约 68 KiB | 约 68 KiB | 仅工具 wheel；不含独立环境及 30 项依赖/安装组件 |

前三个 APT 组件合计约 **175.1 / 166.7 MiB**，不是四个优先工具的总增量；Docker CLI 和 kubectl 在上一版中已存在。
Kube-Hunter 的完整环境含 Kubernetes Python 客户端和 netifaces 扩展，不能用小型工具 wheel 的大小代表整体占用。
以上不是最终镜像层实测，也不能将压缩下载量与安装体积直接相加。

- **Trivy 暂不默认安装**：此前固定包的程序安装体积约 **229.4 / 218.7 MiB**，另需漏洞数据库；不符合此次“体积影响不大”的条件。本版移除原默认安装，不调整已有接口。
- **Clair 暂不安装**：完整能力需要服务端和 PostgreSQL，不是单个轻量客户端；原代码的 `clairctl analyze` 调用也不能直接视为兼容当前官方 Clair。

[AMD64 包索引](https://http.kali.org/kali/dists/kali-rolling/main/binary-amd64/Packages.gz)、
[ARM64 包索引](https://mirrors.aliyun.com/kali/dists/kali-rolling/main/binary-arm64/Packages.gz)、
[Kube-Bench 固定发布](https://github.com/aquasecurity/kube-bench/releases/tag/v0.16.0)、
[Kube-Hunter 包元数据](https://pypi.org/pypi/kube-hunter/0.6.8/json)、
[Clair 部署要求](https://quay.github.io/clair/howto/getting_started.html)。

#### 原接口与运行前提

- Kube-Bench 需要目标节点的进程、配置文件及相应可见权限。在普通应用容器内启动命令不等于检查宿主节点；Docker Desktop 内的结果也不等于 macOS 宿主机审计结果。
- 独立临时报告针对实际命令执行；原服务的命令结果缓存保持不变，重复 HTTP 请求不保证重新检查目标。
- 原 Kube-Bench 接口的 `targets` 由命令入口补齐 `run` 子命令；`version` 仍表示被测 Kubernetes 版本。`--outputfile` 使用每次调用独立的临时文件，把本次生成的报告返回标准输出并更新请求的报告路径；显式设置 `--exit-code` 后发现风险的非零状态仍保留，无报告的执行错误不读取旧报告。原接口始终传递 `--json`，因此只承诺 JSON 报告，不以文件扩展名冒充其他格式。
- Kube-Hunter 原接口的 `interface="eth0"` 不受上游支持；命令入口明确报错，不能静默改成扫描全部网卡。使用明确的 `target` 或 `cidr`。未指定目标时，原接口走 `--pod`，并非空操作；上游该模式可能探测云元数据地址，不因未安装 AWS/Azure CLI 而消失。
- Kube-Hunter 0.6.8 固定较旧的 Kubernetes Python 客户端，不保证覆盖新集群的全部风险；Helm 4 与现有 Chart、插件和集群版本也需匹配。安装完成不等于所有现有接口参数均已获得运行验证。

参数依据：[Kube-Bench run](https://github.com/aquasecurity/kube-bench/blob/v0.16.0/cmd/run.go)、
[Kube-Hunter 参数定义](https://github.com/aquasecurity/kube-hunter/blob/v0.6.8/kube_hunter/conf/parser.py)。

### 6.7 基础环境与辅助工具

| 环境或工具 | 主要用途 |
| --- | --- |
| Kali Linux、Bash | 提供系统环境和交互式命令行。 |
| curl | 发起 HTTP 等协议请求和下载文件。 |
| Git | 获取源码、读取和管理版本库。 |
| Perl、Ruby 及相关依赖 | 支持 Nikto、WPScan 等工具运行。 |
| Python 3.11、pip、venv | 提供 Python 运行与虚拟环境能力，不替换 Kali 系统 Python。 |
| 独立 Volatility3/JWT-Tool/ParamSpider/Kube-Hunter 环境 | 各自隔离 Python 3 依赖，不使用应用虚拟环境。 |
| Python 2.7.18 专用运行时 | 只服务 Volatility 2；安装在 `/opt/python2`，不替换系统或应用解释器，不带入构建阶段编译器。 |
| tini | 作为容器轻量入口管理子进程与信号。 |
| CA 证书和系统动态库 | 支持 HTTPS 访问及各工具运行。 |
| 小型目录与参数字典 | 提供 Dirb、Dirsearch、X8 使用的基本输入数据。 |

### 6.8 工具使用边界

- 工具清单描述基础镜像的命令能力，不表示每个工具都有独立 HTTP 接口，也不把应用层接口的参数限制等同于客户端本身的全部能力。
- Subfinder、theHarvester 等工具的部分数据源需要 API Key；WPScan 的漏洞信息查询可能需要令牌。
- 大型字典、完整 SecLists、Nuclei 模板、彩虹表和 Volatility 符号表不作为内置数据保证，需要按任务准备或挂载。
- Nuclei 默认调用使用第 4.4 节的离线模板挂载，不再依赖首次调用时下载；不代表所有模板的外部依赖也已离线化。
- Katana 的无头浏览器模式需要可用浏览器；Hashcat 的 GPU 模式需要宿主机驱动与设备透传。
- tcpdump 实时采集需要可见网卡和相应权限，读取离线 PCAP 不需要抓包权限。
- TruffleHog 的凭据验证及 JWT-Tool 的主动测试会产生外部请求，使用时应明确选择相应模式。
- Volatility 2 与 Python 2 已停止维护，此处保留是为兼容旧接口和旧内存样本；不能视为仍受维护的通用 Python 环境。Volatility 3 不支持 Volatility 2 的 profile，两个命令不互相冒充；自定义 Linux/macOS profile、符号表与可选 XLSX 输出依赖仍需按需准备。
- ParamSpider 原接口的整数 `level` 明确为两档：`1` 普通提取，`2` 对应上游 `high` 提取；不是任意爬取深度，其他值返回参数错误。`output` 与另一旧入口的 `output_file` 均映射到旧工具 `-o`；无目录文件名遵循旧工具的 `output/` 目录规则。
- Volatility 3 的 `output_file` 保存成功命令的标准输出文本，而不是映射到含义不同的 `-o` 产物目录；HTTP 响应仍保留原命令输出。
- 原有 CTF 目标占位符、HTTPX 字段传递、ParamSpider 两档参数和 Volatility 3 报告修复保持不变；未增加五个补充工具的新专用接口。Arjun 的 GET+POST 仍分别执行，任一步失败即返回失败；Fierce 参数与 JWT-Tool 旧路径仍由基础镜像适配。
- 工具选择以实际渗透复用为准：调试、逆向与内存取证工具保留其漏洞分析用途，不为了补齐 CTF 清单增加仅限赛题的工具；云与容器限定 Docker、Kubernetes 等通用环境，不增加 AWS/Azure 专用组件。
- Trivy、Clair 的原接口仍保留在代码中，但本版不提供其运行环境；接口存在不能作为工具可用的依据。
- kubectl 1.33.x 应配合受支持的 Kubernetes API 版本使用，不能保证兼容所有旧集群；连接前核对服务端版本与官方版本偏差范围。[Kubernetes 版本偏差策略](https://kubernetes.io/releases/version-skew-policy/#kubectl)

#### 1.3.3 的兼容入口与接口参数

本版将 WPScan 固定为 3.8.28，恢复其原生默认插件枚举（被动检测）和配置备份检查，不新增 WPScan 包装入口。
Nuclei 增加基础环境离线模板入口；服务端仅调整 RPCclient、FFUF、Foremost 三个路由，不修改 `hexstrike_mcp.py`。
RPCclient 默认匿名认证使用 `-N -U ''`，用户名配空密码时明确传递空密码，命令序列通过 `-c` 执行，不再使用交互管道。
FFUF 默认目录模式在 URL 路径部分追加 `/FUZZ`，保留查询参数，已有 `FUZZ` 时不重复添加；参数模式正确追加查询项。
Foremost 默认在 `/tmp/foremost_output` 下为每次调用创建唯一 `run-*` 子目录，响应中的 `output_directory` 返回实际结果目录。
显式指定非默认目录时保留该路径，非空则拒绝执行，不删除旧证据；该接口不复用结果缓存，避免返回历史结果。
默认结果保存在容器文件系统中，需要持久化时将 `/tmp/foremost_output` 挂载到单独的可写数据目录；保留目录权限与容量，按保留策略管理旧结果，不自动清空。

基础镜像和应用镜像均优先使用 `/opt/hexstrike-compat/bin`，原始 APT 与 Go 命令保留在原路径。
兼容入口不改写目标、不吞掉退出状态，也不以“找到命令”替代工具能力判断。
本次兼容能力需要使用包含下述入口的基础镜像；不能只更新应用代码而继续继承旧基础镜像。

| 工具 | 当前兼容行为 |
| --- | --- |
| enum4linux-ng | 原接口的 `-A S,U,G,P` 转为独立 `-S -U -G -P`；目标后面的旧 `-d DOMAIN` 转为 `-w DOMAIN`。直接调用现代语法时使用 `-w` 指定域；详细输出的 `-d` 放在目标前或命令末尾，避免与旧语法歧义。 |
| Gobuster | DNS 模式的旧 `-u DOMAIN` 转为 `--domain DOMAIN`，其他模式不改；DNS 的 `url` 字段应填纯域名，不填带协议或路径的 URL。 |
| Checksec | `--file PATH` 转为 `--file=PATH`；两条既有分析路径使用同一真实工具。 |
| Ghidra | 保留原始 `analyzeHeadless`，兼容入口补充脚本搜索目录；提供使用官方 XML 导出器的 `ExportXml.java`，满足原接口默认 XML 报告调用，不假设上游内置该脚本。 |
| Waybackurls、Anew | 将已知布尔开关移到域名或输出文件前，避免被 Go 参数解析器忽略；未知开关和多余操作数明确报错。 |
| Binwalk | 默认 root 环境中的提取操作使用专用低权限用户 `hexstrike-extract` 运行外部解包程序；该用户使用相同的非零 UID/GID，避开 2.x 历史权限处理差异。显式 `--run-as` 保留。普通识别不变，提取输出目录须允许该用户访问，私有挂载和只读目录需要单独安排。 |
| Dalfox | 官方 v2.12.0 原生接受现有旧参数，不使用 v3 删除参数的假兼容；两个 mining 字段的 false 会实际关闭对应功能。`custom_payload` 是镜像内文件路径，不是载荷正文。 |
| AutoRecon | 为 `top-100-ports`、`top-1000-ports` 提供实际的 TCP 前 100／1000 端口扫描插件，将 Nmap 识别出的服务交回 AutoRecon 枚举。使用这些配置时排除其余默认端口扫描插件，不暗中附加全 TCP 或 UDP 扫描；默认服务枚举仍保留。 |
| Hakrawler | 保留 2.1 原生爬取，兼容入口分别实现表单 action 收集、robots 路径发现、sitemap 解析和可选 Waybackurls 历史 URL 获取。默认同主机、合并去重，不把功能开关误转为 `-subs`。不带兼容参数的直接命令仍转交原生工具。 |

Dalfox v2 的 DOM 动态验证仍需要可用的 Chromium/Chrome；本版不额外安装浏览器，不将静态分析结果冒充动态验证。[固定版本参数](https://github.com/hahwul/dalfox/blob/v2.12.0/cmd/root.go)。
Dalfox 的 Go 产物继续纳入摘要、架构与版本清单；无需在最终镜像安装 Go 编译器。

环境无法恢复调用方未提供的信息或修复 Python 调用错误，因此保留以下最小服务端修正，`hexstrike_mcp.py` 不变：

- **Ghidra**：`analysis_timeout` 必须为正整数秒，真实传给执行器；不同超时不复用同一缓存条目。
- **Dalfox**：`blind=true` 时，须在 `additional_args` 中提供 `--blind URL` 或 `-b URL`，不能只传无值开关。`pipe_mode=true` 时仍须提供 `url`，服务会把它送入标准输入；缺少输入返回 400。
- **AutoRecon**：`autorecon_comprehensive(target=...)` 的默认 `top-100-ports` 可直接交给环境执行；`autorecon_scan(target=...)` 发送的空输出目录、扫描配置、心跳和超时会在服务端补齐，同样默认 TCP 前 100 端口。显式 `port_scans="default"` 才使用上游原生默认策略，该策略不限制为前 100 端口。`timeout` 沿用工具的分钟单位，公共命令执行器仍有独立秒级上限。
- **Hakrawler**：`hakrawler_crawl(url=...)` 默认深度为 2，启用 `forms`、`robots`、`sitemap`，关闭 `wayback`；不需要调用方改参数。`forms` 收集表单 action、不提交表单；设为 false 则过滤表单来源。robots、sitemap、Wayback 的补充 URL 仅作为发现结果输出，不重新投喂爬虫，避免绕过 `depth`。`wayback=false` 不查询历史归档；为 true 时使用已安装的 Waybackurls。需要子域名时仍通过 `additional_args` 显式传 `-subs`。
- **职责边界**：服务端只补齐 AutoRecon 的空默认值、将 Hakrawler 的四个布尔值分别传递给兼容入口；不在服务端重新实现扫描。`hexstrike_mcp.py` 的函数、默认值及请求字段保持不变，其中 Hakrawler 的旧参数映射注释不再代表实际运行行为。目标不可达、真实工具失败和超时仍应报告失败，不能把“默认参数兼容”理解为所有目标都会扫描成功。
- **参数保真**：已安装常用工具的专用路由与扫描辅助函数对 URL、路径和凭据作 Shell 引用，保留 `&`、空格、引号和 `$` 等内容。没有整体重写所有可选工具接口、CTF 模板或通用命令接口；`additional_args` 等高级原始命令字段仍按原约定解释，不能当作不可信普通文本传入。

AutoRecon 的 top-N 配置与显式端口列表不能同时使用，也不能同时覆盖其附加插件目录；冲突会明确报错，不忽略用户设置。显式追加的其他端口插件仍按用户配置运行。
AutoRecon 默认枚举用到的 DNS 110000 条字典、用户名短字典和 SNMP community 字典从已有安装数据中保留，当前合计约 1.25 MiB（具体以安装包为准，上限 4 MiB），不是完整 SecLists。
这三份文件保存在 `/opt/hexstrike-compat/autorecon-data`，在 `/usr/share/seclists` 下保留对应原生路径；无需调用方改字典参数，也不覆盖用户自定义配置。目录枚举继续使用 AutoRecon 自带的 `dirbuster.txt`。
Hakrawler 兼容调用默认有 120 秒总预算，可通过 `additional_args` 的 `-timeout` 指定正整数秒（仍受服务端执行上限约束）；`-timeout=-1` 不取消兼容层上限。
补充文档单个最多 2 MiB、站点图最多 16 个、结果最多 10000 条；达到数量或总时间上限会明确失败，不把截断结果当作完整成功。
robots/sitemap 的 404 或 410 视为文件不存在；其他下载错误、错误 XML 或 HTML 回退页会在标准错误中提示“补充来源不可用”，保留主体爬取结果，不声称这些补充来源已成功检查。

默认数据路径也属于运行条件：John/Hashcat 使用的 `/usr/share/wordlists/rockyou.txt`，以及部分工作流使用的
`/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt` 不由本版自动下载或保证存在。
RockYou 的挂载命令与原因见第 4 章；其他字典同样应只读挂载到对应路径，或通过接口的 `wordlist` 指定容器内已有文件。不使用小字典冒充 RockYou，也不靠解压大型字典增加基础镜像层。
Amass 5.1.1 会尝试自动启动本地引擎，仍需要可写数据目录及启动时间；本版没有另加守护服务。
