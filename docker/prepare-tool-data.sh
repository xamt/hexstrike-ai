#!/usr/bin/env bash
set -euo pipefail

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
