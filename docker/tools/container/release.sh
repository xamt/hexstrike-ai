#!/usr/bin/env bash
# 通用容器工具的 release 安装阶段；只执行本文件对应的安装方式。
set -euo pipefail

KUBE_BENCH_VERSION=0.16.0

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${TARGETARCH:?缺少目标架构}" in
    amd64|arm64) ;;
    *) echo "不支持的架构: ${TARGETARCH}" >&2; exit 1 ;;
esac

if [ "$#" -ne 0 ]; then echo "此安装脚本不接受模式参数" >&2; exit 2; fi

install_kube_bench() {
    case "${TARGETARCH}" in
        amd64) archive_sha256=82dbc7e598740dc9344d41f8ad0b8210d57c4c00bdb2c5f1d8a69a2b98baddcf ;;
        arm64) archive_sha256=64500561f5fcaa3f86fe951ed26bbfc28f7bbf3d2eac13843abfd2924955d10b ;;
    esac
    temporary="$(mktemp -d)"
    trap 'rm -rf "${temporary}"' EXIT
    curl --fail --location --http1.1 --retry 5 --retry-all-errors --retry-delay 3 \
        --proto '=https' --proto-redir '=https' \
        "https://github.com/aquasecurity/kube-bench/releases/download/v${KUBE_BENCH_VERSION}/kube-bench_${KUBE_BENCH_VERSION}_linux_${TARGETARCH}.tar.gz" \
        --output "${temporary}/kube-bench.tar.gz"
    printf '%s  %s\n' "${archive_sha256}" "${temporary}/kube-bench.tar.gz" | sha256sum -c -
    mkdir -p "${temporary}/unpack" "/opt/kube-bench" "/etc/kube-bench/cfg"
    tar -xzf "${temporary}/kube-bench.tar.gz" -C "${temporary}/unpack"
    test -s "${temporary}/unpack/cfg/config.yaml"
    install -m 0755 "${temporary}/unpack/kube-bench" "/opt/kube-bench/kube-bench"
    cp -a "${temporary}/unpack/cfg/." "/etc/kube-bench/cfg/"
    # 记录清单摘要；最终校验还须sha256sum -c逐个核对配置内容。
    find "/etc/kube-bench/cfg" -type f -print0 | sort -z | xargs -0 sha256sum > "/opt/kube-bench/cfg.sha256"
    sha256sum -c "/opt/kube-bench/cfg.sha256"
    bash "${script_dir}/../../lib/record-tool-version.sh" source kube-bench "${KUBE_BENCH_VERSION}" "${TARGETARCH}" \
        "/opt/kube-bench/kube-bench" "/opt/kube-bench/kube-bench"
    bash "${script_dir}/../../lib/record-tool-version.sh" source kube-bench-config "${KUBE_BENCH_VERSION}" all \
        "/opt/kube-bench/cfg.sha256" "/opt/kube-bench/cfg.sha256"
}

install_kube_bench
