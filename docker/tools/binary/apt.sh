#!/usr/bin/env bash
# binary 类 APT 工具；版本与安装定义在同一文件，任意失败立即停止。
set -euo pipefail

GDB_VERSION=17.2-1+b1
RADARE2_VERSION=6.0.4+dfsg-1
BINWALK_VERSION=2.4.3+dfsg1-3
GHIDRA_VERSION=12.1.4+ds-0kali1
CHECKSEC_VERSION=2.6.0-2
BINUTILS_VERSION=2.47-6
XXD_VERSION=2:9.2.0858-1

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${TARGETARCH:?缺少目标架构}" in
    amd64|arm64) ;;
    *) echo "不支持的架构: ${TARGETARCH}" >&2; exit 1 ;;
esac

apt-get -o APT::Update::Error-Mode=any update

# 工具: GDB
# 描述: 调试本地程序、检查寄存器、内存、断点和调用栈。
# 安装: Kali 软件包 gdb。
(
apt-get install -y --no-install-recommends \
      "gdb=${GDB_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt gdb "${GDB_VERSION}" "${TARGETARCH}"
)

# 工具: Radare2
# 描述: 提供反汇编、调试、二进制修补和脚本化分析能力。
# 安装: Kali 软件包 radare2。
(
apt-get install -y --no-install-recommends \
      "radare2=${RADARE2_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt radare2 "${RADARE2_VERSION}" "${TARGETARCH}"
)

# 工具: Binwalk
# 描述: 识别固件和二进制中的嵌入文件、签名及压缩数据。
# 安装: Kali 软件包 binwalk。
(
apt-get install -y --no-install-recommends \
      "binwalk=${BINWALK_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt binwalk "${BINWALK_VERSION}" "${TARGETARCH}"
)

# 工具: Ghidra
# 描述: 提供反编译、反汇编和 headless 自动分析；该工具会显著增大镜像。
# 安装: Kali 软件包 ghidra，Java 运行时由软件包依赖安装；为 MCP 使用的
#       analyzeHeadless 创建稳定 PATH 入口。
(
apt-get install -y --no-install-recommends \
      "ghidra=${GHIDRA_VERSION}" && \
    ghidra_headless="$(find /usr/share/ghidra -type f -name analyzeHeadless -print -quit)" && \
    test -n "${ghidra_headless}" && \
    ln -sf "${ghidra_headless}" /usr/local/bin/analyzeHeadless && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt ghidra "${GHIDRA_VERSION}" "${TARGETARCH}"
)

# 工具: Checksec
# 描述: 检查 ELF/进程的 PIE、RELRO、NX、Canary 等安全机制。
# 安装: Kali 软件包 checksec。
(
apt-get install -y --no-install-recommends \
      "checksec=${CHECKSEC_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt checksec "${CHECKSEC_VERSION}" "${TARGETARCH}"
)

# 工具: Strings / Objdump
# 描述: 从二进制文件中提取可打印字符串。
# 安装: strings 由 Kali 软件包 binutils 提供。
(
apt-get install -y --no-install-recommends \
      "binutils=${BINUTILS_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt binutils "${BINUTILS_VERSION}" "${TARGETARCH}"
)

# 工具: XXD
# 描述: 创建十六进制转储并把十六进制数据还原为二进制。
# 安装: Kali 软件包 xxd。
(
apt-get install -y --no-install-recommends \
      "xxd=${XXD_VERSION}" && \
    bash "${script_dir}/../../lib/record-tool-version.sh" apt xxd "${XXD_VERSION}" "${TARGETARCH}"
)
