"""原 MCP 工具的机械迁移；函数体和参数由冻结契约校验，不修改执行逻辑。"""

from typing import Any, Dict

from .support import logger


def register(mcp, hexstrike_client):
    """将本领域工具绑定到当前服务实例，保留实例独立的后端客户端。"""
    @mcp.tool()
    def monitor_cve_feeds(hours: int = 24, severity_filter: str = "HIGH,CRITICAL", keywords: str = "") -> Dict[str, Any]:
        """
        Monitor CVE databases for new vulnerabilities with AI analysis.

        Args:
            hours: Hours to look back for new CVEs (default: 24)
            severity_filter: Filter by CVSS severity - comma-separated values (LOW,MEDIUM,HIGH,CRITICAL,ALL)
            keywords: Filter CVEs by keywords in description (comma-separated)

        Returns:
            Latest CVEs with exploitability analysis and threat intelligence

        Example:
            monitor_cve_feeds(48, "CRITICAL", "remote code execution")
        """
        data = {
            "hours": hours,
            "severity_filter": severity_filter,
            "keywords": keywords
        }
        logger.info(f"🔍 Monitoring CVE feeds for last {hours} hours | Severity: {severity_filter}")
        result = hexstrike_client.safe_post("api/vuln-intel/cve-monitor", data)

        if result.get("success"):
            cve_count = len(result.get("cve_monitoring", {}).get("cves", []))
            exploit_analysis_count = len(result.get("exploitability_analysis", []))
            logger.info(f"✅ Found {cve_count} CVEs with {exploit_analysis_count} exploitability analyses")

        return result

    @mcp.tool()
    def generate_exploit_from_cve(cve_id: str, target_os: str = "", target_arch: str = "x64", exploit_type: str = "poc", evasion_level: str = "none") -> Dict[str, Any]:
        """
        Generate working exploits from CVE information using AI-powered analysis.

        Args:
            cve_id: CVE identifier (e.g., CVE-2024-1234)
            target_os: Target operating system (windows, linux, macos, any)
            target_arch: Target architecture (x86, x64, arm, any)
            exploit_type: Type of exploit to generate (poc, weaponized, stealth)
            evasion_level: Evasion sophistication (none, basic, advanced)

        Returns:
            Generated exploit code with testing instructions and evasion techniques

        Example:
            generate_exploit_from_cve("CVE-2024-1234", "linux", "x64", "weaponized", "advanced")
        """
        data = {
            "cve_id": cve_id,
            "target_os": target_os,
            "target_arch": target_arch,
            "exploit_type": exploit_type,
            "evasion_level": evasion_level
        }
        logger.info(f"🤖 Generating {exploit_type} exploit for {cve_id} | Target: {target_os} {target_arch}")
        result = hexstrike_client.safe_post("api/vuln-intel/exploit-generate", data)

        if result.get("success"):
            cve_analysis = result.get("cve_analysis", {})
            exploit_gen = result.get("exploit_generation", {})
            exploitability = cve_analysis.get("exploitability_level", "UNKNOWN")
            exploit_success = exploit_gen.get("success", False)

            logger.info(f"📊 CVE Analysis: {exploitability} exploitability")
            logger.info(f"🎯 Exploit Generation: {'SUCCESS' if exploit_success else 'FAILED'}")

        return result

    @mcp.tool()
    def discover_attack_chains(target_software: str, attack_depth: int = 3, include_zero_days: bool = False) -> Dict[str, Any]:
        """
        Discover multi-stage attack chains for target software with vulnerability correlation.

        Args:
            target_software: Target software/system (e.g., "Apache HTTP Server", "Windows Server 2019")
            attack_depth: Maximum number of stages in attack chain (1-5)
            include_zero_days: Include potential zero-day vulnerabilities in analysis

        Returns:
            Attack chains with vulnerability combinations, success probabilities, and exploit availability

        Example:
            discover_attack_chains("Apache HTTP Server 2.4", 4, True)
        """
        data = {
            "target_software": target_software,
            "attack_depth": min(max(attack_depth, 1), 5),  # Clamp between 1-5
            "include_zero_days": include_zero_days
        }
        logger.info(f"🔗 Discovering attack chains for {target_software} | Depth: {attack_depth} | Zero-days: {include_zero_days}")
        result = hexstrike_client.safe_post("api/vuln-intel/attack-chains", data)

        if result.get("success"):
            chains = result.get("attack_chain_discovery", {}).get("attack_chains", [])
            enhanced_chains = result.get("attack_chain_discovery", {}).get("enhanced_chains", [])

            logger.info(f"📊 Found {len(chains)} attack chains")
            if enhanced_chains:
                logger.info(f"🎯 Enhanced {len(enhanced_chains)} chains with exploit analysis")

        return result

    @mcp.tool()
    def research_zero_day_opportunities(target_software: str, analysis_depth: str = "standard", source_code_url: str = "") -> Dict[str, Any]:
        """
        Automated zero-day vulnerability research using AI analysis and pattern recognition.

        Args:
            target_software: Software to research for vulnerabilities (e.g., "nginx", "OpenSSL")
            analysis_depth: Depth of analysis (quick, standard, comprehensive)
            source_code_url: URL to source code repository for enhanced analysis

        Returns:
            Potential vulnerability areas with exploitation feasibility and research recommendations

        Example:
            research_zero_day_opportunities("nginx 1.20", "comprehensive", "https://github.com/nginx/nginx")
        """
        if analysis_depth not in ["quick", "standard", "comprehensive"]:
            analysis_depth = "standard"

        data = {
            "target_software": target_software,
            "analysis_depth": analysis_depth,
            "source_code_url": source_code_url
        }
        logger.info(f"🔬 Researching zero-day opportunities in {target_software} | Depth: {analysis_depth}")
        result = hexstrike_client.safe_post("api/vuln-intel/zero-day-research", data)

        if result.get("success"):
            research = result.get("zero_day_research", {})
            potential_vulns = len(research.get("potential_vulnerabilities", []))
            risk_score = research.get("risk_assessment", {}).get("risk_score", 0)

            logger.info(f"📊 Found {potential_vulns} potential vulnerability areas")
            logger.info(f"🎯 Risk Score: {risk_score}/100")

        return result
