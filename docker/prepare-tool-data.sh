#!/usr/bin/env bash
set -euo pipefail

# 每个原始安装步骤在独立子进程中执行，任意 && 链失败均立即中止整个脚本。
(
install -d /opt/hexstrike && \
    locked_packages=( \
      nmap masscan rustscan amass subfinder nuclei fierce dnsenum autorecon \
      theharvester responder netexec enum4linux-ng gobuster feroxbuster \
      dirsearch ffuf dirb httpx-toolkit katana hakrawler sqlmap arjun \
      paramspider dalfox wafw00f qsreplace uro wfuzz hydra john hashcat \
      medusa patator crackmapexec evil-winrm hash-identifier ophcrack-cli \
      gdb radare2 binwalk ghidra checksec binutils xxd foremost steghide \
      libimage-exiftool-perl \
    ) && \
    { \
      printf '# tool\tversion\tarchitecture\n'; \
      dpkg-query -W -f='${Package}\t${Version}\t${Architecture}\n' \
        "${locked_packages[@]}" | sort; \
      printf 'nikto\t%s\tall\n' "${NIKTO_VERSION}"; \
      printf 'wpscan\t%s\tall\n' "${WPSCAN_VERSION}"; \
      printf 'gau\t%s\t%s\n' "${GAU_VERSION}" "${TARGETARCH}"; \
      printf 'waybackurls\t%s\t%s\n' "${WAYBACKURLS_VERSION}" "${TARGETARCH}"; \
      printf 'anew\t%s\t%s\n' "${ANEW_VERSION}" "${TARGETARCH}"; \
      printf 'x8\t%s\t%s\n' "${X8_VERSION}" "${TARGETARCH}"; \
    } > /opt/hexstrike/tool-versions.lock
)


# -----------------------------------------------------------------------------
# 共享字典与工具数据路径
# -----------------------------------------------------------------------------
# 只复制工具正常启动所需的小型字典。SecLists、Nuclei 模板、彩虹表、
# Volatility 符号表等大型数据应在运行时通过只读卷挂载。
(
install -d \
      /usr/share/wordlists/dirb \
      /usr/share/wordlists/dirsearch \
      /usr/share/wordlists/x8 && \
    dirb_words="$(find /usr/share -type f -path '*dirb*' -name common.txt -print -quit)" && \
    test -n "${dirb_words}" && \
    if [ "${dirb_words}" != /usr/share/wordlists/dirb/common.txt ]; then \
      cp "${dirb_words}" /usr/share/wordlists/dirb/common.txt; \
    fi && \
    cp /usr/share/wordlists/dirb/common.txt \
      /usr/share/wordlists/dirsearch/common.txt && \
    arjun_words="$(find /usr -type f -path '*arjun*' \
      \( -name large.txt -o -name small.txt \) -print -quit)" && \
    test -n "${arjun_words}" && \
    cp "${arjun_words}" /usr/share/wordlists/x8/params.txt
)
