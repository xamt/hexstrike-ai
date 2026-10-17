# Docker 构建目录说明

镜像构建和启动命令见 [构建说明](../docs/DOCKER_BUILD.md)。本文件只说明安装脚本的组织与维护规则。

## 1. 分类原则

**按用途找目录，按安装方式找脚本，按依赖顺序安排 Dockerfile 阶段。**

- `tools/<类别>/<安装方式>.sh` 是工具版本与安装命令的维护入口，不另建统一版本文件。
- 同类、同安装方式的工具放在同一脚本。只有一个工具的脚本也采用安装方式命名，不再混用单工具文件名。
- 跨场景工具只归属一个主要类别，分类与 `docs/DOCKER_BUILD.md` 一致。不设置 extras、misc 等兜底分类。
- 所有工具安装成功后记录预期版本；失败立即停止，不跳过、不自动升级或切换下载源。
- `Dockerfile.base` 只保留上游镜像、平台、软件源、阶段、挂载和产物复制，不放工具版本或安装细节。

## 2. 目录职责

| 目录 | 职责 |
| --- | --- |
| `runtime/` | Kali 源与系统运行库、Python 安装组件、Rust 工具链，不决定安全工具清单。 |
| `tools/` | 七类安全工具，版本、摘要、依赖及安装行为就地维护。 |
| `lib/` | Go 本机/交叉编译产物收集、版本记录、Python 2 动态库收集；不定义工具版本。 |
| `compat/` | 既有接口的参数和命令路径兼容程序，以及安装入口；不升级原生工具。 |
| `assembly/` | Nikto 命令入口、小字典路径、运行库缓存和最终命令组装。 |
| `verify/` | 镜像内命令、架构、版本校验，以及手动镜像运行检查脚本。 |

## 3. 工具安装位置

| 类别 | 安装脚本 | 工具 |
| --- | --- | --- |
| 网络侦察 `network` | `apt.sh` | Nmap、Masscan、RustScan、Fierce、DNSenum、AutoRecon、enum4linux-ng、tcpdump。 |
| Web 安全 `web` | `apt.sh` | Gobuster、Feroxbuster、Dirsearch、FFUF、Dirb、HTTPX、Katana、Hakrawler、SQLMap、Arjun、Wafw00f、QSReplace、Uro、Wfuzz、Nuclei、WhatWeb、testssl.sh。 |
| Web 安全 `web` | `ruby.sh` / `go.sh` / `rust.sh` | WPScan / Dalfox / X8。 |
| Web 安全 `web` | `source.sh` / `python.sh` | Nikto 固定标签源码 / ParamSpider 隔离环境。 |
| 身份认证 `authentication` | `apt.sh` | Responder、NetExec、Hydra、John、Hashcat、Medusa、Patator、CrackMapExec、Evil-WinRM、Hash-Identifier、Ophcrack CLI。 |
| 身份认证 `authentication` | `python.sh` | JWT-Tool 隔离环境。 |
| 二进制分析 `binary` | `apt.sh` | GDB、Radare2、Binwalk、Ghidra、Checksec、Binutils（Strings/Objdump）、XXD；Binutils 仅安装和记录一次。 |
| 容器安全 `container` | `apt.sh` / `release.sh` / `python.sh` | Docker CLI、kubectl、Helm / Kube-Bench 固定发布包 / Kube-Hunter 隔离环境。 |
| 取证 `forensics` | `apt.sh` / `python2.sh` / `python3.sh` | Foremost、Steghide、ExifTool / Volatility 2 / Volatility 3。 |
| 开源情报 `osint` | `apt.sh` / `go.sh` | Amass、Subfinder、theHarvester、TruffleHog / Gau、Waybackurls、Anew。 |

Python 安全工具各自使用独立虚拟环境。`runtime/python.sh` 统一维护 Python 3 的 pip、setuptools、wheel 版本，可准备全局环境或指定虚拟环境；Volatility 2 与 Kube-Hunter 保留各自原有的安装组件版本。

## 4. 构建顺序与脚本依赖

1. Go 阶段分别编译情报工具和 Dalfox；每个工具单独调用、单独形成构建层。Rust 阶段编译 X8，Nikto 阶段仅获取源码。
2. Kali 阶段先引入证书、配置国内软件源与系统运行库，再按类别安装 APT 工具和 Ruby 工具。
3. 组装阶段复制编译产物、版本记录和小型字典，并安装容器客户端及 Kube-Bench 发布包。
4. Python 3 阶段准备隔离工具环境；Python 2 阶段独立准备旧取证环境，编译器不进入最终镜像。
5. 最终阶段复制运行产物，安装兼容入口，完成命令、架构和版本校验，默认进入 Bash。

脚本通过相对于自身目录的路径引用共用代码。Dockerfile 将所需文件显式只读绑定到 `/tmp/docker/` 下的同构目录，不把整棵 docker 目录作为每层的输入，不依赖当前工作目录。
新增共用依赖时必须同步该 RUN 的绑定挂载；禁止扫描目录后自动执行全部安装脚本。

APT 层继续挂载独立架构的索引、下载包和 SecLists 缓存，防止大型间接字典进入镜像层。
AutoRecon 的三份小字典仍在安装它的同一层保留，组装阶段只建立原生路径链接；不得把数据提取推迟到缓存可能缺失的后续层。
国内 Kali、PyPI、Go 代理配置及证书/摘要校验保持不变。目录迁移会使涉及路径的构建层缓存失效，但不改变工具版本或预期运行能力。

## 5. 维护与验证

- 修改工具：在对应类别与安装方式脚本中修改版本、摘要、依赖和记录，再更新对应测试契约。
- 修改接口兼容：只在 `compat/` 处理，保持原生命令路径和退出状态，不把扫描失败转换成成功。
- 新增工具：按主要用途选目录；仅在安装方式确实不同时新增脚本，并同步工具清单、阶段挂载和版本校验。
- 所有安装脚本由 Bash 显式执行，不要求源码文件具有执行权限。

本地离线检查（不调用 Docker，不安装真实工具）：

```bash
python3 -m unittest discover -s "tests" -p "test_*.py"
git diff --check
```

测试包括脚本语法、目录与挂载依赖、固定版本、模拟包管理器失败、Go 产物路径及既有兼容行为。静态和模拟检查不等于真实镜像构建验收。
`verify/base.sh` 只在镜像构建的最终校验阶段运行；`verify/test-images.sh` 会启动真实容器，仅用于明确要求的手动镜像检查，不由上述测试自动触发。
