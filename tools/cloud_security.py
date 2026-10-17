"""原 MCP 工具的机械迁移；函数体和参数由冻结契约校验，不修改执行逻辑。"""

from typing import Any, Dict

from .support import logger


def register(mcp, tool_client):
    """将本领域工具绑定到当前服务实例，保留实例独立的后端客户端。"""
    @mcp.tool()
    def prowler_scan(provider: str = "aws", profile: str = "default", region: str = "", checks: str = "", output_dir: str = "/tmp/prowler_output", output_format: str = "json", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Prowler for comprehensive cloud security assessment.

        Args:
            provider: Cloud provider (aws, azure, gcp)
            profile: AWS profile to use
            region: Specific region to scan
            checks: Specific checks to run
            output_dir: Directory to save results
            output_format: Output format (json, csv, html)
            additional_args: Additional Prowler arguments

        Returns:
            Cloud security assessment results
        """
        data = {
            "provider": provider,
            "profile": profile,
            "region": region,
            "checks": checks,
            "output_dir": output_dir,
            "output_format": output_format,
            "additional_args": additional_args
        }
        logger.info(f"☁️  Starting Prowler {provider} security assessment")
        result = tool_client.safe_post("api/tools/prowler", data)
        if result.get("success"):
            logger.info(f"✅ Prowler assessment completed")
        else:
            logger.error(f"❌ Prowler assessment failed")
        return result

    @mcp.tool()
    def trivy_scan(scan_type: str = "image", target: str = "", output_format: str = "json", severity: str = "", output_file: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Trivy for container and filesystem vulnerability scanning.

        Args:
            scan_type: Type of scan (image, fs, repo, config)
            target: Target to scan (image name, directory, repository)
            output_format: Output format (json, table, sarif)
            severity: Severity filter (UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL)
            output_file: File to save results
            additional_args: Additional Trivy arguments

        Returns:
            Vulnerability scan results
        """
        data = {
            "scan_type": scan_type,
            "target": target,
            "output_format": output_format,
            "severity": severity,
            "output_file": output_file,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting Trivy {scan_type} scan: {target}")
        result = tool_client.safe_post("api/tools/trivy", data)
        if result.get("success"):
            logger.info(f"✅ Trivy scan completed for {target}")
        else:
            logger.error(f"❌ Trivy scan failed for {target}")
        return result

    @mcp.tool()
    def scout_suite_assessment(provider: str = "aws", profile: str = "default",
                              report_dir: str = "/tmp/scout-suite", services: str = "",
                              exceptions: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Scout Suite for multi-cloud security assessment.

        Args:
            provider: Cloud provider (aws, azure, gcp, aliyun, oci)
            profile: AWS profile to use
            report_dir: Directory to save reports
            services: Specific services to assess
            exceptions: Exceptions file path
            additional_args: Additional Scout Suite arguments

        Returns:
            Multi-cloud security assessment results
        """
        data = {
            "provider": provider,
            "profile": profile,
            "report_dir": report_dir,
            "services": services,
            "exceptions": exceptions,
            "additional_args": additional_args
        }
        logger.info(f"☁️  Starting Scout Suite {provider} assessment")
        result = tool_client.safe_post("api/tools/scout-suite", data)
        if result.get("success"):
            logger.info(f"✅ Scout Suite assessment completed")
        else:
            logger.error(f"❌ Scout Suite assessment failed")
        return result

    @mcp.tool()
    def cloudmapper_analysis(action: str = "collect", account: str = "",
                            config: str = "config.json", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute CloudMapper for AWS network visualization and security analysis.

        Args:
            action: Action to perform (collect, prepare, webserver, find_admins, etc.)
            account: AWS account to analyze
            config: Configuration file path
            additional_args: Additional CloudMapper arguments

        Returns:
            AWS network visualization and security analysis results
        """
        data = {
            "action": action,
            "account": account,
            "config": config,
            "additional_args": additional_args
        }
        logger.info(f"☁️  Starting CloudMapper {action}")
        result = tool_client.safe_post("api/tools/cloudmapper", data)
        if result.get("success"):
            logger.info(f"✅ CloudMapper {action} completed")
        else:
            logger.error(f"❌ CloudMapper {action} failed")
        return result

    @mcp.tool()
    def pacu_exploitation(session_name: str = "pentest-tools_session", modules: str = "",
                         data_services: str = "", regions: str = "",
                         additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Pacu for AWS exploitation framework.

        Args:
            session_name: Pacu session name
            modules: Comma-separated list of modules to run
            data_services: Data services to enumerate
            regions: AWS regions to target
            additional_args: Additional Pacu arguments

        Returns:
            AWS exploitation framework results
        """
        data = {
            "session_name": session_name,
            "modules": modules,
            "data_services": data_services,
            "regions": regions,
            "additional_args": additional_args
        }
        logger.info(f"☁️  Starting Pacu AWS exploitation")
        result = tool_client.safe_post("api/tools/pacu", data)
        if result.get("success"):
            logger.info(f"✅ Pacu exploitation completed")
        else:
            logger.error(f"❌ Pacu exploitation failed")
        return result
