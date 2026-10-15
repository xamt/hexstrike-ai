#!/usr/bin/env bash
# 仅在安装成功后记录脚本声明的预期版本，不从已安装包反推预期值。
# 可选的产物摘要用于校验跨阶段复制的源码或二进制；不维护任何版本常量。
set -euo pipefail

kind="${1:?缺少安装类型}"
name="${2:?缺少工具名}"
version="${3:?缺少预期版本}"
arch="${4:?缺少架构}"
source_path="${5:--}"
target_path="${6:--}"
record_dir="${TOOL_RECORD_DIR:-/opt/hexstrike/tool-versions.d}"

case "${kind}" in apt|gem|go|rust|source|python|vol-python) ;; *) exit 2 ;; esac
case "${arch}" in amd64|arm64|all) ;; *) exit 2 ;; esac
[[ "${name}" =~ ^[a-z0-9][a-z0-9.+_-]*$ ]] || exit 2
[[ "${version}" != *$'\t'* && "${version}" != *$'\n'* ]] || exit 2
digest="-"
if [ "${source_path}" != - ]; then
    [[ "${target_path}" = /* && "${target_path}" != *$'\t'* && "${target_path}" != *$'\n'* ]] || exit 2
    digest="$(sha256sum "${source_path}")"
    digest="${digest%% *}"
fi

mkdir -p "${record_dir}"
temporary="$(mktemp "${record_dir}/.record.XXXXXX")"
trap 'rm -f "${temporary}"' EXIT
printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
    "${kind}" "${name}" "${version}" "${arch}" "${digest}" "${target_path}" > "${temporary}"
target="${record_dir}/${kind}-${name}.tsv"
# Binutils 提供多个命令，重复安装同版本允许；记录冲突必须显式失败。
if [ -e "${target}" ]; then
    cmp -s "${temporary}" "${target}" || {
        echo "工具版本记录冲突: ${name}" >&2
        exit 1
    }
else
    mv "${temporary}" "${target}"
fi
