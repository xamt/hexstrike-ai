#!/usr/bin/env bash
set -euo pipefail

# 同一类别共用一次成功的索引更新，随后仍逐项安装精确版本。
apt-get -o APT::Update::Error-Mode=any update

# 每个原始安装步骤在独立子进程中执行，任意 && 链失败均立即中止整个脚本。
# 工具: GDB
# 分类: Binary Analysis & Reverse Engineering
# 描述: 调试本地程序、检查寄存器、内存、断点和调用栈。
# 安装: Kali 软件包 gdb。
(
apt-get install -y --no-install-recommends \
      "gdb=${GDB_VERSION}"
)

# 工具: Radare2
# 分类: Binary Analysis & Reverse Engineering
# 描述: 提供反汇编、调试、二进制修补和脚本化分析能力。
# 安装: Kali 软件包 radare2。
(
apt-get install -y --no-install-recommends \
      "radare2=${RADARE2_VERSION}"
)

# 工具: Binwalk
# 分类: Binary Analysis & Reverse Engineering
# 描述: 识别固件和二进制中的嵌入文件、签名及压缩数据。
# 安装: Kali 软件包 binwalk。
(
apt-get install -y --no-install-recommends \
      "binwalk=${BINWALK_VERSION}"
)

# 工具: Ghidra
# 分类: Binary Analysis & Reverse Engineering
# 描述: 提供反编译、反汇编和 headless 自动分析；该工具会显著增大镜像。
# 安装: Kali 软件包 ghidra，Java 运行时由软件包依赖安装；为 MCP 使用的
#       analyzeHeadless 创建稳定 PATH 入口。
(
apt-get install -y --no-install-recommends \
      "ghidra=${GHIDRA_VERSION}" && \
    ghidra_headless="$(find /usr/share/ghidra -type f -name analyzeHeadless -print -quit)" && \
    test -n "${ghidra_headless}" && \
    ln -sf "${ghidra_headless}" /usr/local/bin/analyzeHeadless
)

# 工具: Checksec
# 分类: Binary Analysis & Reverse Engineering
# 描述: 检查 ELF/进程的 PIE、RELRO、NX、Canary 等安全机制。
# 安装: Kali 软件包 checksec。
(
apt-get install -y --no-install-recommends \
      "checksec=${CHECKSEC_VERSION}"
)

# 工具: Strings
# 分类: Binary Analysis & Reverse Engineering / 共享基础工具
# 描述: 从二进制文件中提取可打印字符串。
# 安装: strings 由 Kali 软件包 binutils 提供。
(
apt-get install -y --no-install-recommends \
      "binutils=${BINUTILS_VERSION}"
)

# 工具: Objdump
# 分类: Binary Analysis & Reverse Engineering / 共享基础工具
# 描述: 查看对象文件的段、符号和反汇编结果。
# 安装: objdump 与 strings 共享 Kali 软件包 binutils；此命令确认依赖归属。
(
apt-get install -y --no-install-recommends \
      "binutils=${BINUTILS_VERSION}"
)

# 工具: XXD
# 分类: Binary Analysis & Reverse Engineering / 共享基础工具
# 描述: 创建十六进制转储并把十六进制数据还原为二进制。
# 安装: Kali 软件包 xxd。
(
apt-get install -y --no-install-recommends \
      "xxd=${XXD_VERSION}"
)

# 工具: Foremost
# 分类: Binary Analysis & Reverse Engineering / 数字取证
# 描述: 根据文件头、文件尾和数据结构从镜像中恢复文件。
# 安装: Kali 软件包 foremost。
(
case "${TARGETARCH}" in \
      amd64) package_version="${FOREMOST_VERSION_AMD64}" ;; \
      arm64) package_version="${FOREMOST_VERSION_ARM64}" ;; \
    esac && \
    apt-get install -y --no-install-recommends "foremost=${package_version}"
)

# 工具: Steghide
# 分类: Binary Analysis & Reverse Engineering / 隐写分析
# 描述: 在 JPEG、BMP、WAV、AU 等载体中嵌入或提取隐藏数据。
# 安装: Kali 软件包 steghide。
(
apt-get install -y --no-install-recommends \
      "steghide=${STEGHIDE_VERSION}"
)

# 工具: ExifTool
# 分类: Binary Analysis & Reverse Engineering / 元数据分析
# 描述: 读取、写入和比较多种文件格式的元数据。
# 安装: Kali 包名为 libimage-exiftool-perl，提供 exiftool 命令。
(
apt-get install -y --no-install-recommends \
      "libimage-exiftool-perl=${EXIFTOOL_VERSION}"
)
