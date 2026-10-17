"""原 MCP 工具的机械迁移；函数体和参数由冻结契约校验，不修改执行逻辑。"""

from typing import Any, Dict

from .support import HexStrikeColors, logger


def register(mcp, hexstrike_client):
    """将本领域工具绑定到当前服务实例，保留实例独立的后端客户端。"""
    @mcp.tool()
    def http_framework_test(url: str, method: str = "GET", data: dict = {},
                           headers: dict = {}, cookies: dict = {}, action: str = "request") -> Dict[str, Any]:
        """
        Enhanced HTTP testing framework (Burp Suite alternative) for comprehensive web security testing.

        Args:
            url: Target URL to test
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            data: Request data/parameters
            headers: Custom headers
            cookies: Custom cookies
            action: Action to perform (request, spider, proxy_history, set_rules, set_scope, repeater, intruder)

        Returns:
            HTTP testing results with vulnerability analysis
        """
        data_payload = {
            "url": url,
            "method": method,
            "data": data,
            "headers": headers,
            "cookies": cookies,
            "action": action
        }

        logger.info(f"{HexStrikeColors.FIRE_RED}🔥 Starting HTTP Framework {action}: {url}{HexStrikeColors.RESET}")
        result = hexstrike_client.safe_post("api/tools/http-framework", data_payload)

        if result.get("success"):
            logger.info(f"{HexStrikeColors.SUCCESS}✅ HTTP Framework {action} completed for {url}{HexStrikeColors.RESET}")

            # Enhanced logging for vulnerabilities found
            if result.get("result", {}).get("vulnerabilities"):
                vuln_count = len(result["result"]["vulnerabilities"])
                logger.info(f"{HexStrikeColors.HIGHLIGHT_RED} Found {vuln_count} potential vulnerabilities {HexStrikeColors.RESET}")
        else:
            logger.error(f"{HexStrikeColors.ERROR}❌ HTTP Framework {action} failed for {url}{HexStrikeColors.RESET}")

        return result

    @mcp.tool()
    def browser_agent_inspect(url: str, headless: bool = True, wait_time: int = 5,
                             action: str = "navigate", proxy_port: int = None, active_tests: bool = False) -> Dict[str, Any]:
        """
        AI-powered browser agent for comprehensive web application inspection and security analysis.

        Args:
            url: Target URL to inspect
            headless: Run browser in headless mode
            wait_time: Time to wait after page load
            action: Action to perform (navigate, screenshot, close, status)
            proxy_port: Optional proxy port for request interception
            active_tests: Run lightweight active reflected XSS tests (safe GET-only)

        Returns:
            Browser inspection results with security analysis
        """
        data_payload = {
            "url": url,
            "headless": headless,
            "wait_time": wait_time,
            "action": action,
            "proxy_port": proxy_port,
            "active_tests": active_tests
        }

        logger.info(f"{HexStrikeColors.CRIMSON}🌐 Starting Browser Agent {action}: {url}{HexStrikeColors.RESET}")
        result = hexstrike_client.safe_post("api/tools/browser-agent", data_payload)

        if result.get("success"):
            logger.info(f"{HexStrikeColors.SUCCESS}✅ Browser Agent {action} completed for {url}{HexStrikeColors.RESET}")

            # Enhanced logging for security analysis
            if action == "navigate" and result.get("result", {}).get("security_analysis"):
                security_analysis = result["result"]["security_analysis"]
                issues_count = security_analysis.get("total_issues", 0)
                security_score = security_analysis.get("security_score", 0)

                if issues_count > 0:
                    logger.warning(f"{HexStrikeColors.HIGHLIGHT_YELLOW} Security Issues: {issues_count} | Score: {security_score}/100 {HexStrikeColors.RESET}")
                else:
                    logger.info(f"{HexStrikeColors.HIGHLIGHT_GREEN} No security issues found | Score: {security_score}/100 {HexStrikeColors.RESET}")
        else:
            logger.error(f"{HexStrikeColors.ERROR}❌ Browser Agent {action} failed for {url}{HexStrikeColors.RESET}")

        return result

    @mcp.tool()
    def http_set_rules(rules: list) -> Dict[str, Any]:
        """Set match/replace rules used to rewrite parts of URL/query/headers/body before sending.
        Rule format: {'where':'url|query|headers|body','pattern':'regex','replacement':'string'}"""
        payload = {"action": "set_rules", "rules": rules}
        return hexstrike_client.safe_post("api/tools/http-framework", payload)

    @mcp.tool()
    def http_set_scope(host: str, include_subdomains: bool = True) -> Dict[str, Any]:
        """Define in-scope host (and optionally subdomains) so out-of-scope requests are skipped."""
        payload = {"action": "set_scope", "host": host, "include_subdomains": include_subdomains}
        return hexstrike_client.safe_post("api/tools/http-framework", payload)

    @mcp.tool()
    def http_repeater(request_spec: dict) -> Dict[str, Any]:
        """Send a crafted request (Burp Repeater equivalent). request_spec keys: url, method, headers, cookies, data."""
        payload = {"action": "repeater", "request": request_spec}
        return hexstrike_client.safe_post("api/tools/http-framework", payload)

    @mcp.tool()
    def http_intruder(url: str, method: str = "GET", location: str = "query", params: list = None,
                      payloads: list = None, base_data: dict = None, max_requests: int = 100) -> Dict[str, Any]:
        """Simple Intruder (sniper) fuzzing. Iterates payloads over each param individually.
        location: query|body|headers|cookie."""
        payload = {
            "action": "intruder",
            "url": url,
            "method": method,
            "location": location,
            "params": params or [],
            "payloads": payloads or [],
            "base_data": base_data or {},
            "max_requests": max_requests
        }
        return hexstrike_client.safe_post("api/tools/http-framework", payload)

    @mcp.tool()
    def burpsuite_alternative_scan(target: str, scan_type: str = "comprehensive",
                                  headless: bool = True, max_depth: int = 3,
                                  max_pages: int = 50) -> Dict[str, Any]:
        """
        Comprehensive Burp Suite alternative combining HTTP framework and browser agent for complete web security testing.

        Args:
            target: Target URL or domain to scan
            scan_type: Type of scan (comprehensive, spider, passive, active)
            headless: Run browser in headless mode
            max_depth: Maximum crawling depth
            max_pages: Maximum pages to analyze

        Returns:
            Comprehensive security assessment results
        """
        data_payload = {
            "target": target,
            "scan_type": scan_type,
            "headless": headless,
            "max_depth": max_depth,
            "max_pages": max_pages
        }

        logger.info(f"{HexStrikeColors.BLOOD_RED}🔥 Starting Burp Suite Alternative {scan_type} scan: {target}{HexStrikeColors.RESET}")
        result = hexstrike_client.safe_post("api/tools/burpsuite-alternative", data_payload)

        if result.get("success"):
            logger.info(f"{HexStrikeColors.SUCCESS}✅ Burp Suite Alternative scan completed for {target}{HexStrikeColors.RESET}")

            # Enhanced logging for comprehensive results
            if result.get("result", {}).get("summary"):
                summary = result["result"]["summary"]
                total_vulns = summary.get("total_vulnerabilities", 0)
                pages_analyzed = summary.get("pages_analyzed", 0)
                security_score = summary.get("security_score", 0)

                logger.info(f"{HexStrikeColors.HIGHLIGHT_BLUE} SCAN SUMMARY {HexStrikeColors.RESET}")
                logger.info(f"  📊 Pages Analyzed: {pages_analyzed}")
                logger.info(f"  🚨 Vulnerabilities: {total_vulns}")
                logger.info(f"  🛡️  Security Score: {security_score}/100")

                # Log vulnerability breakdown
                vuln_breakdown = summary.get("vulnerability_breakdown", {})
                for severity, count in vuln_breakdown.items():
                    if count > 0:
                        color = {
                                    'critical': HexStrikeColors.CRITICAL,
        'high': HexStrikeColors.FIRE_RED,
        'medium': HexStrikeColors.CYBER_ORANGE,
        'low': HexStrikeColors.YELLOW,
        'info': HexStrikeColors.INFO
    }.get(severity.lower(), HexStrikeColors.WHITE)

                        logger.info(f"  {color}{severity.upper()}: {count}{HexStrikeColors.RESET}")
        else:
            logger.error(f"{HexStrikeColors.ERROR}❌ Burp Suite Alternative scan failed for {target}{HexStrikeColors.RESET}")

        return result
