"""原 MCP 工具的机械迁移；函数体和参数由冻结契约校验，不修改执行逻辑。"""

from typing import Any, Dict
import time

from .support import logger


def register(mcp, tool_client):
    """将本领域工具绑定到当前服务实例，保留实例独立的后端客户端。"""
    @mcp.tool()
    def correlate_threat_intelligence(indicators: str, timeframe: str = "30d", sources: str = "all") -> Dict[str, Any]:
        """
        Correlate threat intelligence across multiple sources with advanced analysis.

        Args:
            indicators: Comma-separated IOCs (IPs, domains, hashes, CVEs, etc.)
            timeframe: Time window for correlation (7d, 30d, 90d, 1y)
            sources: Intelligence sources to query (cve, exploit-db, github, twitter, all)

        Returns:
            Correlated threat intelligence with attribution, timeline, and threat scoring

        Example:
            correlate_threat_intelligence("CVE-2024-1234,192.168.1.100,malware.exe", "90d", "all")
        """
        # Validate timeframe
        valid_timeframes = ["7d", "30d", "90d", "1y"]
        if timeframe not in valid_timeframes:
            timeframe = "30d"

        # Parse indicators
        indicator_list = [i.strip() for i in indicators.split(",") if i.strip()]

        if not indicator_list:
            logger.error("❌ No valid indicators provided")
            return {"success": False, "error": "No valid indicators provided"}

        data = {
            "indicators": indicator_list,
            "timeframe": timeframe,
            "sources": sources
        }
        logger.info(f"🧠 Correlating threat intelligence for {len(indicator_list)} indicators | Timeframe: {timeframe}")
        result = tool_client.safe_post("api/vuln-intel/threat-feeds", data)

        if result.get("success"):
            threat_intel = result.get("threat_intelligence", {})
            correlations = len(threat_intel.get("correlations", []))
            threat_score = threat_intel.get("threat_score", 0)

            logger.info(f"📊 Found {correlations} threat correlations")
            logger.info(f"🎯 Overall Threat Score: {threat_score:.1f}/100")

        return result

    @mcp.tool()
    def advanced_payload_generation(attack_type: str, target_context: str = "", evasion_level: str = "standard", custom_constraints: str = "") -> Dict[str, Any]:
        """
        Generate advanced payloads with AI-powered evasion techniques and contextual adaptation.

        Args:
            attack_type: Type of attack (rce, privilege_escalation, persistence, exfiltration, xss, sqli)
            target_context: Target environment details (OS, software versions, security controls)
            evasion_level: Evasion sophistication (basic, standard, advanced, nation-state)
            custom_constraints: Custom payload constraints (size limits, character restrictions, etc.)

        Returns:
            Advanced payloads with multiple evasion techniques and deployment instructions

        Example:
            advanced_payload_generation("rce", "Windows 11 + Defender + AppLocker", "nation-state", "max_size:256,no_quotes")
        """
        valid_attack_types = ["rce", "privilege_escalation", "persistence", "exfiltration", "xss", "sqli", "lfi", "ssrf"]
        valid_evasion_levels = ["basic", "standard", "advanced", "nation-state"]

        if attack_type not in valid_attack_types:
            attack_type = "rce"

        if evasion_level not in valid_evasion_levels:
            evasion_level = "standard"

        data = {
            "attack_type": attack_type,
            "target_context": target_context,
            "evasion_level": evasion_level,
            "custom_constraints": custom_constraints
        }
        logger.info(f"🎯 Generating advanced {attack_type} payload | Evasion: {evasion_level}")
        if target_context:
            logger.info(f"🎯 Target Context: {target_context}")

        result = tool_client.safe_post("api/ai/advanced-payload-generation", data)

        if result.get("success"):
            payload_gen = result.get("advanced_payload_generation", {})
            payload_count = payload_gen.get("payload_count", 0)
            evasion_applied = payload_gen.get("evasion_level", "none")

            logger.info(f"📊 Generated {payload_count} advanced payloads")
            logger.info(f"🛡️ Evasion Level Applied: {evasion_applied}")

        return result

    @mcp.tool()
    def vulnerability_intelligence_dashboard() -> Dict[str, Any]:
        """
        Get a comprehensive vulnerability intelligence dashboard with latest threats and trends.

        Returns:
            Dashboard with latest CVEs, trending vulnerabilities, exploit availability, and threat landscape

        Example:
            vulnerability_intelligence_dashboard()
        """
        logger.info("📊 Generating vulnerability intelligence dashboard")

        # Get latest critical CVEs
        latest_cves = tool_client.safe_post("api/vuln-intel/cve-monitor", {
            "hours": 24,
            "severity_filter": "CRITICAL",
            "keywords": ""
        })

        # Get trending attack types
        trending_research = tool_client.safe_post("api/vuln-intel/zero-day-research", {
            "target_software": "web applications",
            "analysis_depth": "quick"
        })

        # Compile dashboard
        dashboard = {
            "timestamp": time.time(),
            "latest_critical_cves": latest_cves.get("cve_monitoring", {}).get("cves", [])[:5],
            "threat_landscape": {
                "high_risk_software": ["Apache HTTP Server", "Microsoft Exchange", "VMware vCenter", "Fortinet FortiOS"],
                "trending_attack_vectors": ["Supply chain attacks", "Cloud misconfigurations", "Zero-day exploits", "AI-powered attacks"],
                "active_threat_groups": ["APT29", "Lazarus Group", "FIN7", "REvil"],
            },
            "exploit_intelligence": {
                "new_public_exploits": "Simulated data - check exploit-db for real data",
                "weaponized_exploits": "Monitor threat intelligence feeds",
                "exploit_kits": "Track underground markets"
            },
            "recommendations": [
                "Prioritize patching for critical CVEs discovered in last 24h",
                "Monitor for zero-day activity in trending attack vectors",
                "Implement advanced threat detection for active threat groups",
                "Review security controls against nation-state level attacks"
            ]
        }

        logger.info("✅ Vulnerability intelligence dashboard generated")
        return {
            "success": True,
            "dashboard": dashboard
        }

    @mcp.tool()
    def threat_hunting_assistant(target_environment: str, threat_indicators: str = "", hunt_focus: str = "general") -> Dict[str, Any]:
        """
        AI-powered threat hunting assistant with vulnerability correlation and attack simulation.

        Args:
            target_environment: Environment to hunt in (e.g., "Windows Domain", "Cloud Infrastructure")
            threat_indicators: Known IOCs or suspicious indicators to investigate
            hunt_focus: Focus area (general, apt, ransomware, insider_threat, supply_chain)

        Returns:
            Threat hunting playbook with detection queries, IOCs, and investigation steps

        Example:
            threat_hunting_assistant("Windows Domain", "suspicious_process.exe,192.168.1.100", "apt")
        """
        valid_hunt_focus = ["general", "apt", "ransomware", "insider_threat", "supply_chain"]
        if hunt_focus not in valid_hunt_focus:
            hunt_focus = "general"

        logger.info(f"🔍 Generating threat hunting playbook for {target_environment} | Focus: {hunt_focus}")

        # Parse indicators if provided
        indicators = [i.strip() for i in threat_indicators.split(",") if i.strip()] if threat_indicators else []

        # Generate hunting playbook
        hunting_playbook = {
            "target_environment": target_environment,
            "hunt_focus": hunt_focus,
            "indicators_analyzed": indicators,
            "detection_queries": [],
            "investigation_steps": [],
            "threat_scenarios": [],
            "mitigation_strategies": []
        }

        # Environment-specific detection queries
        if "windows" in target_environment.lower():
            hunting_playbook["detection_queries"] = [
                "Get-WinEvent | Where-Object {$_.Id -eq 4688 -and $_.Message -like '*suspicious*'}",
                "Get-Process | Where-Object {$_.ProcessName -notin @('explorer.exe', 'svchost.exe')}",
                "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
                "Get-NetTCPConnection | Where-Object {$_.State -eq 'Established' -and $_.RemoteAddress -notlike '10.*'}"
            ]
        elif "cloud" in target_environment.lower():
            hunting_playbook["detection_queries"] = [
                "CloudTrail logs for unusual API calls",
                "Failed authentication attempts from unknown IPs",
                "Privilege escalation events",
                "Data exfiltration indicators"
            ]

        # Focus-specific threat scenarios
        focus_scenarios = {
            "apt": [
                "Spear phishing with weaponized documents",
                "Living-off-the-land techniques",
                "Lateral movement via stolen credentials",
                "Data staging and exfiltration"
            ],
            "ransomware": [
                "Initial access via RDP/VPN",
                "Privilege escalation and persistence",
                "Shadow copy deletion",
                "Encryption and ransom note deployment"
            ],
            "insider_threat": [
                "Unusual data access patterns",
                "After-hours activity",
                "Large data downloads",
                "Access to sensitive systems"
            ]
        }

        hunting_playbook["threat_scenarios"] = focus_scenarios.get(hunt_focus, [
            "Unauthorized access attempts",
            "Suspicious process execution",
            "Network anomalies",
            "Data access violations"
        ])

        # Investigation steps
        hunting_playbook["investigation_steps"] = [
            "1. Validate initial indicators and expand IOC list",
            "2. Run detection queries and analyze results",
            "3. Correlate events across multiple data sources",
            "4. Identify affected systems and user accounts",
            "5. Assess scope and impact of potential compromise",
            "6. Implement containment measures if threat confirmed",
            "7. Document findings and update detection rules"
        ]

        # Correlate with vulnerability intelligence if indicators provided
        if indicators:
            logger.info(f"🧠 Correlating {len(indicators)} indicators with threat intelligence")
            correlation_result = correlate_threat_intelligence(",".join(indicators), "30d", "all")

            if correlation_result.get("success"):
                hunting_playbook["threat_correlation"] = correlation_result.get("threat_intelligence", {})

        logger.info("✅ Threat hunting playbook generated")
        return {
            "success": True,
            "hunting_playbook": hunting_playbook
        }
