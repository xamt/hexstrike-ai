"""原 MCP 工具的机械迁移；函数体和参数由冻结契约校验，不修改执行逻辑。"""

from typing import Any, Dict

from .support import logger


def register(mcp, tool_client):
    """将本领域工具绑定到当前服务实例，保留实例独立的后端客户端。"""
    @mcp.tool()
    def kube_hunter_scan(target: str = "", remote: str = "", cidr: str = "",
                        interface: str = "", active: bool = False, report: str = "json",
                        additional_args: str = "") -> Dict[str, Any]:
        """
        Execute kube-hunter for Kubernetes penetration testing.

        Args:
            target: Specific target to scan
            remote: Remote target to scan
            cidr: CIDR range to scan
            interface: Network interface to scan
            active: Enable active hunting (potentially harmful)
            report: Report format (json, yaml)
            additional_args: Additional kube-hunter arguments

        Returns:
            Kubernetes penetration testing results
        """
        data = {
            "target": target,
            "remote": remote,
            "cidr": cidr,
            "interface": interface,
            "active": active,
            "report": report,
            "additional_args": additional_args
        }
        logger.info(f"☁️  Starting kube-hunter Kubernetes scan")
        result = tool_client.safe_post("api/tools/kube-hunter", data)
        if result.get("success"):
            logger.info(f"✅ kube-hunter scan completed")
        else:
            logger.error(f"❌ kube-hunter scan failed")
        return result

    @mcp.tool()
    def kube_bench_cis(targets: str = "", version: str = "", config_dir: str = "",
                      output_format: str = "json", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute kube-bench for CIS Kubernetes benchmark checks.

        Args:
            targets: Targets to check (master, node, etcd, policies)
            version: Kubernetes version
            config_dir: Configuration directory
            output_format: Output format (json, yaml)
            additional_args: Additional kube-bench arguments

        Returns:
            CIS Kubernetes benchmark results
        """
        data = {
            "targets": targets,
            "version": version,
            "config_dir": config_dir,
            "output_format": output_format,
            "additional_args": additional_args
        }
        logger.info(f"☁️  Starting kube-bench CIS benchmark")
        result = tool_client.safe_post("api/tools/kube-bench", data)
        if result.get("success"):
            logger.info(f"✅ kube-bench benchmark completed")
        else:
            logger.error(f"❌ kube-bench benchmark failed")
        return result

    @mcp.tool()
    def docker_bench_security_scan(checks: str = "", exclude: str = "",
                                  output_file: str = "/tmp/docker-bench-results.json",
                                  additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Docker Bench for Security for Docker security assessment.

        Args:
            checks: Specific checks to run
            exclude: Checks to exclude
            output_file: Output file path
            additional_args: Additional Docker Bench arguments

        Returns:
            Docker security assessment results
        """
        data = {
            "checks": checks,
            "exclude": exclude,
            "output_file": output_file,
            "additional_args": additional_args
        }
        logger.info(f"🐳 Starting Docker Bench Security assessment")
        result = tool_client.safe_post("api/tools/docker-bench-security", data)
        if result.get("success"):
            logger.info(f"✅ Docker Bench Security completed")
        else:
            logger.error(f"❌ Docker Bench Security failed")
        return result

    @mcp.tool()
    def clair_vulnerability_scan(image: str, config: str = "/etc/clair/config.yaml",
                                output_format: str = "json", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Clair for container vulnerability analysis.

        Args:
            image: Container image to scan
            config: Clair configuration file
            output_format: Output format (json, yaml)
            additional_args: Additional Clair arguments

        Returns:
            Container vulnerability analysis results
        """
        data = {
            "image": image,
            "config": config,
            "output_format": output_format,
            "additional_args": additional_args
        }
        logger.info(f"🐳 Starting Clair vulnerability scan: {image}")
        result = tool_client.safe_post("api/tools/clair", data)
        if result.get("success"):
            logger.info(f"✅ Clair scan completed for {image}")
        else:
            logger.error(f"❌ Clair scan failed for {image}")
        return result

    @mcp.tool()
    def falco_runtime_monitoring(config_file: str = "/etc/falco/falco.yaml",
                                rules_file: str = "", output_format: str = "json",
                                duration: int = 60, additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Falco for runtime security monitoring.

        Args:
            config_file: Falco configuration file
            rules_file: Custom rules file
            output_format: Output format (json, text)
            duration: Monitoring duration in seconds
            additional_args: Additional Falco arguments

        Returns:
            Runtime security monitoring results
        """
        data = {
            "config_file": config_file,
            "rules_file": rules_file,
            "output_format": output_format,
            "duration": duration,
            "additional_args": additional_args
        }
        logger.info(f"🛡️  Starting Falco runtime monitoring for {duration}s")
        result = tool_client.safe_post("api/tools/falco", data)
        if result.get("success"):
            logger.info(f"✅ Falco monitoring completed")
        else:
            logger.error(f"❌ Falco monitoring failed")
        return result

    @mcp.tool()
    def checkov_iac_scan(directory: str = ".", framework: str = "", check: str = "",
                        skip_check: str = "", output_format: str = "json",
                        additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Checkov for infrastructure as code security scanning.

        Args:
            directory: Directory to scan
            framework: Framework to scan (terraform, cloudformation, kubernetes, etc.)
            check: Specific check to run
            skip_check: Check to skip
            output_format: Output format (json, yaml, cli)
            additional_args: Additional Checkov arguments

        Returns:
            Infrastructure as code security scanning results
        """
        data = {
            "directory": directory,
            "framework": framework,
            "check": check,
            "skip_check": skip_check,
            "output_format": output_format,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting Checkov IaC scan: {directory}")
        result = tool_client.safe_post("api/tools/checkov", data)
        if result.get("success"):
            logger.info(f"✅ Checkov scan completed")
        else:
            logger.error(f"❌ Checkov scan failed")
        return result

    @mcp.tool()
    def terrascan_iac_scan(scan_type: str = "all", iac_dir: str = ".",
                          policy_type: str = "", output_format: str = "json",
                          severity: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Terrascan for infrastructure as code security scanning.

        Args:
            scan_type: Type of scan (all, terraform, k8s, etc.)
            iac_dir: Infrastructure as code directory
            policy_type: Policy type to use
            output_format: Output format (json, yaml, xml)
            severity: Severity filter (high, medium, low)
            additional_args: Additional Terrascan arguments

        Returns:
            Infrastructure as code security scanning results
        """
        data = {
            "scan_type": scan_type,
            "iac_dir": iac_dir,
            "policy_type": policy_type,
            "output_format": output_format,
            "severity": severity,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting Terrascan IaC scan: {iac_dir}")
        result = tool_client.safe_post("api/tools/terrascan", data)
        if result.get("success"):
            logger.info(f"✅ Terrascan scan completed")
        else:
            logger.error(f"❌ Terrascan scan failed")
        return result
