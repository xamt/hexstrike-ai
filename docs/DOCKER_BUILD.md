# 工具基础镜像与应用镜像构建说明

## 1. 镜像与构建顺序

只构建 AMD64、ARM64 两种独立镜像，不创建多架构入口。每个架构先构建基础镜像，再构建应用镜像。

| 用途 | AMD64 | ARM64 |
| --- | --- | --- |
| 基础镜像 | `harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.3.3-amd64` | `harbor.everoffice.cn/harbor-cucc/pentest-tools-base:1.3.3-arm64` |
| 应用镜像 | `harbor.everoffice.cn/harbor-cucc/pentest-tools:1.3.3-amd64` | `harbor.everoffice.cn/harbor-cucc/pentest-tools:1.3.3-arm64` |

- 基础镜像：Kali、安全工具、小型字典、Python 3.11，以及隔离的 Volatility 2/3、JWT-Tool、ParamSpider、Kube-Hunter 环境；默认进入 Bash，不启动服务。
- 应用镜像：继承同架构基础镜像，隔离安装 API/MCP 依赖；默认同时启动 HTTP API（8888）与 Streamable HTTP MCP（8889/mcp），不重复安装安全工具。
- 两类镜像版本独立管理，应用镜像引用同架构的基础镜像。
- 本项目发布标签不使用 `latest`；已发布的版本标签不可覆盖。调整版本时直接修改对应命令中的完整镜像名。

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

应用构建显式引用同架构基础镜像，不重复安装工具。

## 4. 启动应用镜像

本节双接口启动要求使用当前源码构建的应用镜像，已发布旧镜像不会自动获得 MCP 接口。新功能建议使用独立本地标签构建，完整命令、Agent 配置及网关网络限制见 [MCP 接入说明](MCP_HTTP.md)。本版本不增加鉴权，默认仅发布到主机回环。

应用可以直接启动，**不强制挂载字典或模板**。按任务补充数据，可扩展密码测试和漏洞检测能力，准备方法见 4.3、4.4。
离线运行前，请先将对应架构的应用镜像导入 Docker 主机，或确保可从内网 Harbor 获取。

### 4.1 AMD64 应用

```bash
docker run --detach \
  --name pentest-tools-amd64 \
  --platform linux/amd64 \
  --publish 127.0.0.1:8888:8888 \
  --publish 127.0.0.1:8889:8889 \
  --stop-timeout 15 \
  harbor.everoffice.cn/harbor-cucc/pentest-tools:1.3.3-amd64
```

### 4.2 ARM64 应用

```bash
docker run --detach \
  --name pentest-tools-arm64 \
  --platform linux/arm64 \
  --publish 127.0.0.1:8888:8888 \
  --publish 127.0.0.1:8889:8889 \
  --stop-timeout 15 \
  harbor.everoffice.cn/harbor-cucc/pentest-tools:1.3.3-arm64
```

API 地址为 `http://127.0.0.1:8888`，MCP 地址为 `http://127.0.0.1:8889/mcp`；两条命令占用相同宿主端口，不要同时运行。
通过 `docker logs pentest-tools-amd64` 或 `docker logs pentest-tools-arm64` 查看日志。

需要挂载时，将下文的 `--mount` 参数添加在对应启动命令的**镜像名之前**，替换为 Docker 主机上的真实绝对路径。
已有容器需要保留结果后重新创建，`docker restart` 不会增加挂载；补充数据不需要重建镜像。
Docker Desktop 须允许目录共享；远程 Docker context 使用的是守护进程所在主机的路径。

### 4.3 John/Hashcat 默认字典（可选）

John/Hashcat 默认字典路径为 `/usr/share/wordlists/rockyou.txt`。
镜像不内置这份约 133.4 MiB 的大型字典；挂载后可直接使用默认字典攻击，也可通过接口的 `wordlist` 指定其他已提供的字典。
**不挂载不影响服务启动，但默认字典攻击会因缺少文件而失败**。待处理的哈希文件仍需另行提供。

**联网下载：**在项目目录外准备 [SecLists 2025.3 的 RockYou 归档](https://raw.githubusercontent.com/danielmiessler/SecLists/2025.3/Passwords/Leaked-Databases/rockyou.txt.tar.gz)（约 50.8 MiB），无需下载整个 SecLists。
以下命令适用于 Bash；校验使用 `shasum`（macOS 自带），Linux 可将 `shasum -a 256` 替换为 `sha256sum`。

```bash
(
  set -eu
  mkdir -p "$HOME/pentest-data/rockyou-2025.3"
  cd "$HOME/pentest-data/rockyou-2025.3"
  curl --http1.1 --fail --location --retry 5 \
    --output "rockyou.txt.tar.gz.part" \
    "https://raw.githubusercontent.com/danielmiessler/SecLists/2025.3/Passwords/Leaked-Databases/rockyou.txt.tar.gz"
  mv "rockyou.txt.tar.gz.part" "rockyou.txt.tar.gz"
  gzip -t "rockyou.txt.tar.gz"
  shasum -a 256 "rockyou.txt.tar.gz" > "SHA256SUMS"
)
```

**离线转移与解压：**将归档和 `SHA256SUMS` 通过可信内网或介质复制到离线主机的同名目录，再执行：

```bash
(
  set -eu
  cd "$HOME/pentest-data/rockyou-2025.3"
  shasum -a 256 -c "SHA256SUMS"
  mkdir "wordlists"
  tar -xzf "rockyou.txt.tar.gz" -C "wordlists" "rockyou.txt"
  test -s "wordlists/rockyou.txt"
  printf '字典绝对路径：%s/wordlists/rockyou.txt\n' "$(pwd -P)"
)
```

校验清单用于检查转移完整性，不是发布者签名，应与归档一起通过可信渠道传递。
`wordlists` 须为新目录；下载的是 tar.gz，不能仅解 gzip，也不要对字典转码。

**可选挂载参数：**将 `/path/to/rockyou.txt` 替换为上一步输出的文件路径，仅挂载该文件，不覆盖整个字典目录：

```text
--mount "type=bind,source=/path/to/rockyou.txt,target=/usr/share/wordlists/rockyou.txt,readonly"
```

### 4.4 Nuclei 离线模板（可选）

镜像包含 **Nuclei 3.11.1** 引擎，不包含完整模板，也不会在首次调用时下载。
挂载模板可启用模板扫描；**不挂载不影响服务启动，但未提供其他本地模板时，Nuclei 扫描会明确失败**。

沿用固定的 [nuclei-templates v10.4.2](https://github.com/projectdiscovery/nuclei-templates/releases/tag/v10.4.2) 离线快照（归档约 8.8 MiB），避免使用浮动的 latest。
这是当前部署基线，不是上游的逐模板兼容保证；尚未进行容器内全量模板验证，快照也不包含后续新增规则。

**联网下载与校验：**在项目目录外执行，需 Bash、curl、tar、gzip 和 `shasum`（Linux 可用 `sha256sum` 替换 `shasum -a 256`）。
摘要来自 [官方 v10.4.2 校验清单](https://github.com/projectdiscovery/nuclei-templates/releases/download/v10.4.2/nuclei-templates-10.4.2_checksums.txt)。

```bash
(
  set -eu
  mkdir -p "$HOME/pentest-data/nuclei-10.4.2"
  cd "$HOME/pentest-data/nuclei-10.4.2"
  curl --http1.1 --fail --location --retry 5 \
    --output "nuclei-templates-10.4.2.tar.gz.part" \
    "https://github.com/projectdiscovery/nuclei-templates/archive/refs/tags/v10.4.2.tar.gz"
  mv "nuclei-templates-10.4.2.tar.gz.part" "nuclei-templates-10.4.2.tar.gz"
  printf '%s\n' '5f416b77da1397adb0e19aedf1b2744dc715673465c64b3031b53ad31a1bf6c9  nuclei-templates-10.4.2.tar.gz' > "SHA256SUMS"
  shasum -a 256 -c "SHA256SUMS"
)
```

**离线转移与解压：**将归档和 `SHA256SUMS` 通过可信内网或介质复制到离线主机的同名目录，再执行：

```bash
(
  set -eu
  cd "$HOME/pentest-data/nuclei-10.4.2"
  shasum -a 256 -c "SHA256SUMS"
  mkdir "templates"
  tar -xzf "nuclei-templates-10.4.2.tar.gz" -C "templates" --strip-components=1
  test -d "templates/http"
  test -d "templates/helpers"
  test -d "templates/workflows"
  test -f "templates/.nuclei-ignore"
  printf '模板绝对路径：%s/templates\n' "$(pwd -P)"
)
```

`templates` 须为新目录；保留隐藏文件、helpers 和 workflows，不混合不同版本的数据。
升级时在联网环境准备新快照，转入离线环境后更换挂载。

**可选挂载参数：**将 `/path/to/nuclei-templates` 替换为上一步输出的目录路径，不挂载压缩包或额外套一层的父目录：

```text
--mount "type=bind,source=/path/to/nuclei-templates,target=/opt/nuclei-templates,readonly"
```

默认扫描读取 `/opt/nuclei-templates`，也可通过接口的 `template` 选择本地模板。
入口禁止自动更新和远程模板下载，并禁用 Interactsh 外部回连；依赖外部 API、浏览器或其他辅助程序的模板仍可能无法离线执行。
字典与模板均不区分 AMD64/ARM64；校验失败应停止，解压中断应换新目录，不把未完成的数据挂给容器。

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
## 6. 基础镜像包含的工具

以下按 1.3.3 的安装配置分类，每个工具只列一次，别名不重复计数；AMD64、ARM64 提供相同类别。
清单描述已配置安装的主要工具，不代表每个工具都有独立 HTTP 接口，也不把依赖包计为额外安全工具。

### 6.1 🔍 网络侦察与扫描（8 项）

| 工具 | 命令 | 主要用途 |
| --- | --- | --- |
| Nmap | `nmap` | 主机发现、端口扫描、服务与操作系统识别，以及 NSE 脚本检查。 |
| Masscan | `masscan` | 大批量 IP 的高速端口发现。 |
| RustScan | `rustscan` | 快速发现开放端口，可交由 Nmap 进一步识别服务。 |
| Fierce | `fierce` | DNS 枚举及关联主机发现。 |
| DNSenum | `dnsenum` | 枚举 DNS 记录、名称服务器、子域名及区域传送配置。 |
| AutoRecon | `autorecon` | 编排端口扫描和服务枚举，实际能力取决于可用子工具与数据。 |
| enum4linux-ng | `enum4linux-ng` | 枚举 Windows/Samba 用户、组、共享、策略及域信息。 |
| tcpdump | `tcpdump` | 采集网络报文，或读取 PCAP 文件分析协议与流量。 |

### 6.2 🌐 Web 应用程序安全测试（22 项）

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
| Arjun | `arjun` | 发现 GET、POST、JSON 请求中的隐藏参数。 |
| ParamSpider | `paramspider` | 从历史 URL 中提取带参数的端点。 |
| X8 | `x8` | 根据响应差异发现隐藏 HTTP 参数。 |
| QSReplace | `qsreplace` | 批量替换 URL 查询参数值，准备测试输入。 |
| Uro | `uro` | 归并相似 URL，减少重复测试。 |
| Wfuzz | `wfuzz` | 对请求路径、参数、头部及认证字段进行模糊测试。 |
| Nuclei | `nuclei` | 依据模板检查服务和 Web 应用的漏洞及配置问题。 |
| Nikto | `nikto` | 检查 Web 服务器危险文件、错误配置和已知风险。 |
| SQLMap | `sqlmap` | 检测和验证 SQL 注入及其影响。 |
| WPScan | `wpscan` | 固定 3.8.28，检查 WordPress 核心、主题和插件；保留默认被动插件枚举。 |
| Dalfox v2.12.0 | `dalfox` | 发现和验证 XSS，兼容现有接口参数；动态 DOM 验证需要另备浏览器。 |
| Wafw00f | `wafw00f` | 识别 Web 应用防火墙。 |
| WhatWeb | `whatweb` | 识别 Web 技术、服务器和 CMS 指纹。 |
| testssl.sh | `testssl` | 检查 TLS 协议、密码套件、证书及相关配置风险。 |

### 6.3 🔐 身份验证和密码安全（12 项）

| 工具 | 命令 | 主要用途 |
| --- | --- | --- |
| Responder | `responder` | 分析和响应 LLMNR、NBT-NS、mDNS 等名称解析请求，验证名称解析投毒及认证信息泄露风险。 |
| NetExec | `nxc` | 枚举 SMB、WinRM、LDAP、MSSQL 等服务，验证凭据与访问权限。 |
| CrackMapExec | `crackmapexec` | Windows/Active Directory 环境中的凭据与权限验证；与 NetExec 分别保留。 |
| Evil-WinRM | `evil-winrm` | 使用已有凭据通过 WinRM 连接 Windows 主机并执行远程操作。 |
| Hydra | `hydra` | 多种网络协议的在线口令验证。 |
| Medusa | `medusa` | 并行验证多种远程服务的认证凭据。 |
| Patator | `patator` | 模块化、多协议认证测试。 |
| John the Ripper | `john` | 多种密码哈希的离线恢复和强度评估。 |
| Hashcat | `hashcat` | 使用 CPU/GPU 等设备进行离线哈希恢复。 |
| Hash-Identifier | `hash-identifier` | 根据哈希特征推测可能的算法类型。 |
| Ophcrack CLI | `ophcrack-cli` | 使用彩虹表恢复 Windows LM/NTLM 哈希，无图形界面。 |
| JWT-Tool | `jwt_tool` | 解析 JWT，并测试签名、令牌篡改和相关认证问题。 |

### 6.4 🔬 二进制分析与逆向工程（8 项）

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

### 6.5 ☁️ 云和容器安全（5 项）

| 工具 | 命令 | 主要用途 |
| --- | --- | --- |
| Docker CLI | `docker` | 连接授权的 Docker 服务，读取镜像、容器、网络与运行配置；不包含守护进程。 |
| kubectl | `kubectl` | 使用授权的 kubeconfig 访问 Kubernetes API，检查资源配置、RBAC 与暴露面；不安装集群。 |
| Helm | `helm` | 渲染、检查 Kubernetes Chart，查看或管理授权集群的应用发布。 |
| Kube-Bench | `kube-bench` | 按 CIS 基线检查 Kubernetes 节点配置；内置该发布包的检查配置。 |
| Kube-Hunter | `kube-hunter` | 发现 Kubernetes 暴露服务和已知配置风险；主动检查需要明确选择。 |

仅覆盖 Docker、Kubernetes 通用环境；不内置 Docker 守护进程或集群，不安装 AWS/Azure 专用工具、Trivy、Clair。
访问目标需自行提供 kubeconfig、节点配置或 Docker 服务连接，默认不挂载 socket、不提升权限。

### 6.6 🏆 CTF 和取证工具（5 项）

| 工具 | 命令 | 主要用途 |
| --- | --- | --- |
| Foremost | `foremost` | 根据文件特征从磁盘镜像或原始数据中恢复文件。 |
| Steghide | `steghide` | 在图片、音频等载体中嵌入或提取隐藏数据。 |
| ExifTool | `exiftool` | 读取、修改和比较文件元数据。 |
| Volatility 2.6.1 | `volatility` | 分析旧版系统内存镜像，保留 `--profile`、`imageinfo` 等旧接口能力。 |
| Volatility 3（2.28.2） | `vol`、`vol.py` | 使用新版插件与符号机制分析内存；另保留 `/opt/volatility3/vol.py` Python 入口。 |

保留可复用于漏洞分析和数字取证的工具，不为补齐 CTF 清单额外安装仅限赛题的组件。
Volatility 2 使用隔离的 Python 2，已停止维护；Volatility 3 使用独立 Python 3 环境，符号表与旧版 profile 按需提供。

### 6.7 🔥 漏洞赏金和开源情报工具库（7 项）

| 工具 | 命令 | 主要用途 |
| --- | --- | --- |
| Amass | `amass` | 收集子域名、DNS 关系及外部资产信息。 |
| Subfinder | `subfinder` | 通过公开数据源被动发现子域名。 |
| theHarvester | `theHarvester` | 从公开数据源收集邮箱、域名、主机名和 IP。 |
| Gau | `gau` | 从多个公开数据源收集历史 URL。 |
| Waybackurls | `waybackurls` | 从 Wayback Machine 收集历史 URL。 |
| Anew | `anew` | 对文本行去重，仅追加尚未出现的结果。 |
| TruffleHog | `trufflehog` | 在文件、源码和 Git 历史中检测凭据泄漏，可按需验证凭据。 |

基础镜像与应用镜像的默认工作目录均为 `/opt/pentest-tools`。应用代码中的 API 入口为 `server.py`，运行模块为 `runtime/`，工具注册为 `tools/`；MCP 入口为 `mcp_server.py`，仅提供 Streamable HTTP。镜像启动和健康检查配置已同步，内部虚拟环境和兼容目录名称保持不变。

**基础运行环境：**Kali、Bash、curl、Git、Perl、Ruby、Python 3.11、pip、venv、tini、CA 证书及运行库；安全工具的专用 Python 环境与应用依赖隔离。内置小型目录、参数字典及 AutoRecon 必需的小字典，不携带完整 SecLists、大型字典、彩虹表或完整符号表。实际工具版本记录位于 `/opt/pentest-tools/tool-versions.lock`。

**使用条件：**
- 工具已安装不等于扫描条件已齐备；字典和模板按第 4 章选用，部分情报源和 WPScan 漏洞查询需要 API Key。
- Katana/Dalfox 的浏览器模式、Hashcat 的 GPU 模式需额外运行环境。tcpdump 等实时网络工具需可见网卡和相应权限；按需添加 `--cap-add NET_RAW --cap-add NET_ADMIN`，不默认使用特权容器。Docker Desktop 不等于宿主机二层网络直通。
- Kube-Bench 需目标节点的进程与配置可见；普通容器中运行不等于审计宿主机。Kube-Hunter 未指定目标时会走原接口的 Pod 检查模式，应明确被测范围。
- 默认结果保存在容器内；需保留取证产物时，另行挂载可写结果目录（例如 Foremost 的 `/tmp/foremost_output`），删除容器前保存结果。
