#!/usr/bin/env bash
set -euo pipefail

# 工具: Nikto
# 分类: Web Application Security / Web 服务器检查
# 描述: 检查 Web 服务器危险文件、错误配置和已知风险。
# 安装: 从 nikto-source 阶段复制固定标签源码并创建命令包装器；版本由其安装脚本维护。
(
printf '%s\n' '#!/bin/sh' 'exec perl /opt/nikto/program/nikto.pl "$@"' \
      > /usr/local/bin/nikto && chmod 0755 /usr/local/bin/nikto
)

# -----------------------------------------------------------------------------
# 共享字典与工具数据路径
# -----------------------------------------------------------------------------
# 只复制工具正常启动所需的小型字典。完整 SecLists、Nuclei 模板、彩虹表、
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

# AUTORECON_SMALL_DATA
# 使用原生默认路径，不用 CLI 覆盖用户配置中的字典选项。
autorecon_data=/opt/hexstrike-compat/autorecon-data
while IFS= read -r relative; do
    test -s "${autorecon_data}/${relative}"
    install -d "/usr/share/seclists/$(dirname -- "${relative}")"
    ln -s "${autorecon_data}/${relative}" "/usr/share/seclists/${relative}"
done < "${autorecon_data}/manifest.txt"
