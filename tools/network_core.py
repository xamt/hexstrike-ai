"""网络工具 MCP 适配；Nmap 在提交前校验扫描选项，不自动重放执行。"""

from typing import Any, Dict

from runtime.nmap_options import validate_scan_type

from .support import HexStrikeColors, logger


def register(mcp, hexstrike_client):
    """将本领域工具绑定到当前服务实例，保留实例独立的后端客户端。"""
    @mcp.tool()
    def nmap_scan(target: str, scan_type: str = "-sV", ports: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute an enhanced Nmap scan against a target with real-time logging.

        Args:
            target: The IP address or hostname to scan
            scan_type: Raw Nmap flags, e.g. -sV or -sT -sV; never service_version or other semantic names
            ports: Comma-separated ports or ranges; discover a bounded set first, then identify services on open ports
            additional_args: Additional Nmap arguments; use a per-call time budget, report partial coverage on timeout

        Returns:
            Scan results with enhanced telemetry
        """
        try:
            validate_scan_type(scan_type)
        except ValueError as exc:
            return {"success": False, "error_code": "INVALID_ARGUMENT", "error": str(exc)}
        data = {
            "target": target,
            "scan_type": scan_type,
            "ports": ports,
            "additional_args": additional_args
        }
        logger.info(f"{HexStrikeColors.FIRE_RED}🔍 Initiating Nmap scan: {target}{HexStrikeColors.RESET}")

        # 超时并不代表远端已停止；禁止自动重放或修改扫描范围。
        data["use_recovery"] = False
        result = hexstrike_client.safe_post("api/tools/nmap", data)

        if result.get("success"):
            logger.info(f"{HexStrikeColors.SUCCESS}✅ Nmap scan completed successfully for {target}{HexStrikeColors.RESET}")

            # Check for recovery information
            if result.get("recovery_info", {}).get("recovery_applied"):
                recovery_info = result["recovery_info"]
                attempts = recovery_info.get("attempts_made", 1)
                logger.info(f"{HexStrikeColors.HIGHLIGHT_YELLOW} Recovery applied: {attempts} attempts made {HexStrikeColors.RESET}")
        else:
            logger.error(f"{HexStrikeColors.ERROR}❌ Nmap scan failed for {target}{HexStrikeColors.RESET}")

            # Check for human escalation
            if result.get("human_escalation"):
                logger.error(f"{HexStrikeColors.CRITICAL} HUMAN ESCALATION REQUIRED {HexStrikeColors.RESET}")

        return result

    @mcp.tool()
    def gobuster_scan(url: str, mode: str = "dir", wordlist: str = "/usr/share/wordlists/dirb/common.txt", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Gobuster to find directories, DNS subdomains, or virtual hosts with enhanced logging.

        Args:
            url: The target URL
            mode: Scan mode (dir, dns, fuzz, vhost)
            wordlist: Path to wordlist file
            additional_args: Additional Gobuster arguments

        Returns:
            Scan results with enhanced telemetry
        """
        data = {
            "url": url,
            "mode": mode,
            "wordlist": wordlist,
            "additional_args": additional_args
        }
        logger.info(f"{HexStrikeColors.CRIMSON}📁 Starting Gobuster {mode} scan: {url}{HexStrikeColors.RESET}")

        # Use enhanced error handling by default
        data["use_recovery"] = True
        result = hexstrike_client.safe_post("api/tools/gobuster", data)

        if result.get("success"):
            logger.info(f"{HexStrikeColors.SUCCESS}✅ Gobuster scan completed for {url}{HexStrikeColors.RESET}")

            # Check for recovery information
            if result.get("recovery_info", {}).get("recovery_applied"):
                recovery_info = result["recovery_info"]
                attempts = recovery_info.get("attempts_made", 1)
                logger.info(f"{HexStrikeColors.HIGHLIGHT_YELLOW} Recovery applied: {attempts} attempts made {HexStrikeColors.RESET}")
        else:
            logger.error(f"{HexStrikeColors.ERROR}❌ Gobuster scan failed for {url}{HexStrikeColors.RESET}")

            # Check for alternative tool suggestion
            if result.get("alternative_tool_suggested"):
                alt_tool = result["alternative_tool_suggested"]
                logger.info(f"{HexStrikeColors.HIGHLIGHT_BLUE} Alternative tool suggested: {alt_tool} {HexStrikeColors.RESET}")

        return result

    @mcp.tool()
    def nuclei_scan(target: str, severity: str = "", tags: str = "", template: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Nuclei vulnerability scanner with enhanced logging and real-time progress.

        Args:
            target: The target URL or IP
            severity: Filter by severity (critical,high,medium,low,info)
            tags: Filter by tags (e.g. cve,rce,lfi)
            template: Custom template path
            additional_args: Additional Nuclei arguments

        Returns:
            Scan results with discovered vulnerabilities and telemetry
        """
        data = {
            "target": target,
            "severity": severity,
            "tags": tags,
            "template": template,
            "additional_args": additional_args
        }
        logger.info(f"{HexStrikeColors.BLOOD_RED}🔬 Starting Nuclei vulnerability scan: {target}{HexStrikeColors.RESET}")

        # Use enhanced error handling by default
        data["use_recovery"] = True
        result = hexstrike_client.safe_post("api/tools/nuclei", data)

        if result.get("success"):
            logger.info(f"{HexStrikeColors.SUCCESS}✅ Nuclei scan completed for {target}{HexStrikeColors.RESET}")

            # Enhanced vulnerability reporting
            if result.get("stdout") and "CRITICAL" in result["stdout"]:
                logger.warning(f"{HexStrikeColors.CRITICAL} CRITICAL vulnerabilities detected! {HexStrikeColors.RESET}")
            elif result.get("stdout") and "HIGH" in result["stdout"]:
                logger.warning(f"{HexStrikeColors.FIRE_RED} HIGH severity vulnerabilities found! {HexStrikeColors.RESET}")

            # Check for recovery information
            if result.get("recovery_info", {}).get("recovery_applied"):
                recovery_info = result["recovery_info"]
                attempts = recovery_info.get("attempts_made", 1)
                logger.info(f"{HexStrikeColors.HIGHLIGHT_YELLOW} Recovery applied: {attempts} attempts made {HexStrikeColors.RESET}")
        else:
            logger.error(f"{HexStrikeColors.ERROR}❌ Nuclei scan failed for {target}{HexStrikeColors.RESET}")

        return result
