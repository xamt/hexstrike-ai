# 工具基础镜像与应用镜像构建说明

## 1. 镜像与构建顺序

只构建 AMD64、ARM64 两种独立镜像，不创建多架构入口。每个架构先构建基础镜像，再构建应用镜像。

| 用途 | AMD64 | ARM64 |
| --- | --- | --- |
| 基础镜像 | `harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.3.0-amd64` | `harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.3.0-arm64` |
| 应用镜像 | `harbor.everoffice.cn/harbor-cucc/pentest-tools:1.3.0-amd64` | `harbor.everoffice.cn/harbor-cucc/pentest-tools:1.3.0-arm64` |

- 基础镜像：Kali、安全工具、小型字典、Python 3.11，以及隔离的 Volatility 2/3、JWT-Tool、ParamSpider 环境；默认进入 Bash，不启动服务。
- 应用镜像：继承同架构基础镜像，安装项目依赖、复制代码、配置 8888 端口和健康检查，不重复安装安全工具。
- 两类镜像版本独立管理，应用镜像引用同架构的基础镜像。
- 本项目发布标签不使用 `latest`；已发布的版本标签不可覆盖。调整版本时直接修改对应命令中的完整镜像名。

本版撤回新增数据库接口、技能声明与 MySQL/MariaDB、ClickHouse、Redis、PostgreSQL、MongoDB 客户端的专门安装步骤。
保留原有 SQLMap 等安全工具自身的数据库测试能力；其间接依赖不作为独立数据库客户端能力承诺。
恢复以 `1c865493^` 为基准的 MCP 参数契约，优先由固定工具版本、隔离运行时和命令入口适配原接口；
不以新版工具的参数替换原有接口。五个补充工具 testssl.sh、WhatWeb、JWT-Tool、TruffleHog、tcpdump 及其版本保持不变。

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
  --tag harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.3.0-amd64 \
  --load \
  --progress=plain \
  "."
```

### 2.2 ARM64 基础镜像

```bash
docker buildx build \
  --platform linux/arm64 \
  --file "Dockerfile.base" \
  --tag harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.3.0-arm64 \
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
  --build-arg BASE_IMAGE=harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.3.0-amd64 \
  --tag harbor.everoffice.cn/harbor-cucc/pentest-tools:1.3.0-amd64 \
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
  --build-arg BASE_IMAGE=harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.3.0-arm64 \
  --tag harbor.everoffice.cn/harbor-cucc/pentest-tools:1.3.0-arm64 \
  --load \
  --progress=plain \
  "."
```

命令显式指定基础镜像，避免选错架构。省略 `BASE_IMAGE` 时，Dockerfile 依据 BuildKit 的 `TARGETARCH`
选择对应架构标签，不引用公共多架构标签。[Docker 参数说明](https://docs.docker.com/reference/dockerfile/#automatic-platform-args-in-the-global-scope)

## 4. 启动应用镜像

### 4.1 AMD64 应用

```bash
docker run --detach \
  --name pentest-tools-amd64 \
  --platform linux/amd64 \
  --publish 127.0.0.1:8888:8888 \
  harbor.everoffice.cn/harbor-cucc/pentest-tools:1.3.0-amd64
```

### 4.2 ARM64 应用

```bash
docker run --detach \
  --name pentest-tools-arm64 \
  --platform linux/arm64 \
  --publish 127.0.0.1:8888:8888 \
  harbor.everoffice.cn/harbor-cucc/pentest-tools:1.3.0-arm64
```

服务地址为 `http://127.0.0.1:8888`。两条命令使用相同的宿主机端口，不要同时运行。
使用 `docker logs pentest-tools-amd64` 或 `docker logs pentest-tools-arm64` 查看日志。
停止容器时使用对应名称执行 `docker stop`，删除已停止的容器使用 `docker rm`。

默认仅绑定本机地址。确需原始套接字或网络管理时再添加 `--cap-add NET_RAW --cap-add NET_ADMIN`，不要直接使用 `--privileged`。
实时抓包和内网协议工具只能操作容器可见的网络接口；Docker Desktop 不等同于 Linux 宿主机二层网络直通。

## 5. 构建下载源

原构建命令默认使用下列源，无需额外设置环境变量。

| 下载内容 | 默认来源 | 构建参数 |
| --- | --- | --- |
| Kali 软件包 | 阿里云 Kali 镜像 `https://mirrors.aliyun.com/kali` | `KALI_APT_MIRROR` |
| 基础镜像及应用镜像的 Python 包 | 清华 PyPI 镜像 `https://pypi.tuna.tsinghua.edu.cn/simple` | `PIP_INDEX_URL` |
| Gau、Waybackurls、Anew 的 Go 模块 | `https://goproxy.cn` | `GOPROXY` |
| Go 模块校验数据 | `sum.golang.org https://goproxy.cn/sumdb/sum.golang.org` | `GOSUMDB` |
| Rust、RubyGems、GitHub 固定源码归档 | 各自配置的上游来源 | 不由上述参数覆盖 |

需要切换来源时，在对应构建命令的 `--load` 前添加参数：

- Kali 官方分发源：`--build-arg KALI_APT_MIRROR=http://http.kali.org/kali`。
- 官方 PyPI：`--build-arg PIP_INDEX_URL=https://pypi.org/simple`。
- 官方 Go 源：同时添加 `--build-arg GOPROXY=https://proxy.golang.org` 和 `--build-arg GOSUMDB=sum.golang.org`。

Kali 和 Go 参数只用于基础镜像构建，PyPI 参数可用于两种镜像构建。
宿主机的 `go env -w` 不会自动传入 Docker 构建。
国内代理配置保留 HTTPS 与官方校验机制，不自动切换到其他下载源。

来源说明：[清华 PyPI](https://mirrors.tuna.tsinghua.edu.cn/help/pypi/)、[Goproxy.cn](https://goproxy.cn/)、[Go 模块校验](https://go.dev/ref/mod#authenticating)。

## 6. 基础镜像包含的工具

以下按基础镜像 1.3.0 的显式安装配置列出主要工具及用途，不把间接依赖当作单独承诺的工具。
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
| WPScan | `wpscan` | 枚举 WordPress 核心、主题、插件并检查相关风险。 |
| Dalfox | `dalfox` | 发现和验证 XSS 问题。 |
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
| Trivy | 0.66.0-0kali1 | `trivy` | 检查镜像、文件系统及配置中的漏洞、敏感信息和错误配置，复用原有 Trivy 接口。 |

三个工具均从现有国内 Kali 镜像安装，不引入 AWS/Azure CLI。
Docker CLI 和 kubectl 不新增专用 HTTP 接口；安装客户端不等于已获得宿主机或集群访问权限。
不自动挂载 Docker socket、kubeconfig 或服务账号，也不默认提高容器权限。

按 2026-10-16 包索引的安装体积合计，三个组件约增加 AMD64 **341 MiB**、ARM64 **326 MiB**，其中大部分来自 Trivy；
安装包下载量约为 **69 MiB / 59 MiB**。这是包元数据估算，不是镜像层实测，也不包含 Trivy 后续下载的漏洞数据库。
[AMD64 包索引](https://http.kali.org/kali/dists/kali-rolling/main/binary-amd64/Packages.gz)、
[ARM64 包索引](https://mirrors.aliyun.com/kali/dists/kali-rolling/main/binary-arm64/Packages.gz)。

### 6.7 基础环境与辅助工具

| 环境或工具 | 主要用途 |
| --- | --- |
| Kali Linux、Bash | 提供系统环境和交互式命令行。 |
| curl | 发起 HTTP 等协议请求和下载文件。 |
| Git | 获取源码、读取和管理版本库。 |
| Perl、Ruby 及相关依赖 | 支持 Nikto、WPScan 等工具运行。 |
| Python 3.11、pip、venv | 提供 Python 运行与虚拟环境能力，不替换 Kali 系统 Python。 |
| 独立 Volatility3/JWT-Tool/ParamSpider 环境 | 各自隔离 Python 3 依赖，不使用应用虚拟环境。 |
| Python 2.7.18 专用运行时 | 只服务 Volatility 2；安装在 `/opt/python2`，不替换系统或应用解释器，不带入构建阶段编译器。 |
| tini | 作为容器轻量入口管理子进程与信号。 |
| CA 证书和系统动态库 | 支持 HTTPS 访问及各工具运行。 |
| 小型目录与参数字典 | 提供 Dirb、Dirsearch、X8 使用的基本输入数据。 |

### 6.8 工具使用边界

- 工具清单描述基础镜像的命令能力，不表示每个工具都有独立 HTTP 接口，也不把应用层接口的参数限制等同于客户端本身的全部能力。
- Subfinder、theHarvester 等工具的部分数据源需要 API Key；WPScan 的漏洞信息查询可能需要令牌。
- 大型字典、完整 SecLists、Nuclei 模板、彩虹表和 Volatility 符号表不作为内置数据保证，需要按任务准备或挂载。
- Katana 的无头浏览器模式需要可用浏览器；Hashcat 的 GPU 模式需要宿主机驱动与设备透传。
- tcpdump 实时采集需要可见网卡和相应权限，读取离线 PCAP 不需要抓包权限。
- TruffleHog 的凭据验证及 JWT-Tool 的主动测试会产生外部请求，使用时应明确选择相应模式。
- Volatility 2 与 Python 2 已停止维护，此处保留是为兼容旧接口和旧内存样本；不能视为仍受维护的通用 Python 环境。Volatility 3 不支持 Volatility 2 的 profile，两个命令不互相冒充；自定义 Linux/macOS profile、符号表与可选 XLSX 输出依赖仍需按需准备。
- ParamSpider 原接口的整数 `level` 明确为两档：`1` 普通提取，`2` 对应上游 `high` 提取；不是任意爬取深度，其他值返回参数错误。`output` 与另一旧入口的 `output_file` 均映射到旧工具 `-o`；无目录文件名遵循旧工具的 `output/` 目录规则。
- Volatility 3 的 `output_file` 保存成功命令的标准输出文本，而不是映射到含义不同的 `-o` 产物目录；HTTP 响应仍保留原命令输出。
- 服务端仅保留原接口无法靠工具版本纠正的必要修复：CTF 目标占位符和缺失参数、HTTPX 两个原入口的字段传递、ParamSpider 输出字段与两档参数、Volatility 3 报告文件语义。Arjun、Fierce 的旧参数及 JWT-Tool 的旧路径由基础镜像兼容入口处理，不修改原调用代码；Arjun 原 GET+POST 意图分别转为两次明确调用，任一步失败即返回失败。未增加上述五个工具的新专用接口。
- 工具选择以实际渗透复用为准：调试、逆向与内存取证工具保留其漏洞分析用途，不为了补齐 CTF 清单增加仅限赛题的工具；云与容器限定 Docker、Kubernetes 等通用环境，不增加 AWS/Azure 专用组件。
- Trivy 不内置漏洞数据库或 Java 数据库；扫描前需具备下载条件或预先准备的数据缓存，数据库缺失不能视为无漏洞。
- kubectl 1.33.x 应配合受支持的 Kubernetes API 版本使用，不能保证兼容所有旧集群；连接前核对服务端版本与官方版本偏差范围。[Kubernetes 版本偏差策略](https://kubernetes.io/releases/version-skew-policy/#kubectl)
