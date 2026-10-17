#!/usr/bin/env bash
# 验证已经构建的同架构基础/应用镜像；只探测本机，不扫描外部目标。
set -euo pipefail

base_image="${1:?缺少基础镜像引用}"
app_image="${2:?缺少应用镜像引用}"
arch="${3:?缺少 amd64 或 arm64 架构}"
case "${arch}" in
    amd64|arm64) ;;
    *) echo "不支持的架构: ${arch}" >&2; exit 2 ;;
esac

for image in "${base_image}" "${app_image}"; do
    test "$(docker image inspect --format '{{.Architecture}}' "${image}")" = "${arch}"
done

docker run --rm --platform "linux/${arch}" --network none "${base_image}" /bin/bash -ec '
    test ! -e /opt/pentest-tools/hexstrike_server.py
    test ! -e /opt/pentest-tools/requirements.txt
    test ! -e /opt/hexstrike-venv
    python3.11 --version
    nmap --version
    x8 --version
    timeout 30 autorecon --help >/dev/null
    timeout 30 nxc --help >/dev/null
    timeout 30 sqlmap --version
    timeout 30 httpx -version
    timeout 30 wpscan --version
    vol -h >/dev/null
    timeout 30 volatility -h >/dev/null
    timeout 30 vol.py -h >/dev/null
    timeout 30 paramspider -h >/dev/null
    /opt/paramspider-venv/bin/python -m pip check
    volatility2-python -m pip check
    timeout 30 testssl --version
    timeout 30 whatweb --version
    timeout 30 trufflehog --version
    timeout 30 tcpdump --version
    timeout 30 jwt_tool -h >/dev/null
    timeout 30 docker --version
    timeout 30 kubectl version --client=true --output=json
    timeout 30 helm version --short
    timeout 30 kube-bench version
    timeout 30 kube-hunter --help >/dev/null
    /opt/kube-hunter-venv/bin/python -m pip check
    /opt/jwt-tool-venv/bin/python -m pip check
    test -s /opt/pentest-tools/tool-versions.lock
'
docker run --rm --platform "linux/${arch}" --network none "${app_image}" /bin/bash -ec '
    /usr/local/bin/python3.11 -m pip --python /opt/hexstrike-venv/bin/python check
    /opt/volatility3-venv/bin/python -m pip check
    /opt/jwt-tool-venv/bin/python -m pip check
    timeout 30 jwt_tool -h >/dev/null
    test "$(command -v python3)" = /opt/hexstrike-venv/bin/python3
    python3 -c "import requests, httpx"
    test "$(readlink -f "$(command -v httpx)")" = /usr/bin/httpx-toolkit
    vol -h >/dev/null
    timeout 30 volatility -h >/dev/null
    timeout 30 vol.py -h >/dev/null
    timeout 30 paramspider -h >/dev/null
    /opt/paramspider-venv/bin/python -m pip check
    volatility2-python -m pip check
'

container_id="$(docker run --detach --platform "linux/${arch}" --network none "${app_image}")"
# 只清理由本脚本刚创建的容器；任何失败同时输出日志。
cleanup() {
    local status=$?
    if [ "${status}" -ne 0 ]; then
        docker logs "${container_id}" >&2 || echo "无法读取测试容器日志" >&2
    fi
    docker rm --force "${container_id}" >/dev/null || echo "测试容器清理失败: ${container_id}" >&2
    exit "${status}"
}
trap cleanup EXIT

for attempt in $(seq 1 90); do
    state="$(docker inspect --format '{{.State.Status}}' "${container_id}")"
    test "${state}" = running
    health="$(docker inspect --format '{{.State.Health.Status}}' "${container_id}")"
    if [ "${health}" = healthy ]; then
        docker exec "${container_id}" /opt/hexstrike-venv/bin/python -c '
import requests
response = requests.get("http://127.0.0.1:8888/health", timeout=10)
response.raise_for_status()
tools = response.json()["tools_status"]
required = ("nmap", "gobuster", "dirb", "nikto", "sqlmap", "hydra", "john", "hashcat",
            "testssl", "whatweb", "jwt_tool", "trufflehog", "tcpdump")
assert all(tools.get(name) for name in required), tools
'
        echo "镜像运行验证通过: ${arch}"
        exit 0
    fi
    test "${health}" != unhealthy
    sleep 2
done
echo "等待应用健康检查超时" >&2
exit 1
