#!/usr/bin/env bash
# WPScan 固定兼容版本，通过 RubyGems 安装。
set -euo pipefail

WPSCAN_VERSION=3.8.28

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${TARGETARCH:?缺少目标架构}" in
    amd64|arm64) ;;
    *) echo "不支持的架构: ${TARGETARCH}" >&2; exit 1 ;;
esac

apt-get -o APT::Update::Error-Mode=any update

# 工具: WPScan
# 分类: Web Application Security / WordPress
# 描述: 枚举 WordPress 核心、主题、插件和已知漏洞；漏洞数据库需运行时更新。
# 安装: 保留 RubyGems 安装方式，固定版本在本脚本顶部定义。
(
apt-get install -y --no-install-recommends \
      ruby-full ruby-dev build-essential \
      libcurl4-openssl-dev libxml2-dev libxslt1-dev zlib1g-dev && \
    gem install wpscan --version "${WPSCAN_VERSION}" --no-document && \
    bash "${script_dir}/../../lib/record-tool-version.sh" gem wpscan "${WPSCAN_VERSION}" "all"
)
