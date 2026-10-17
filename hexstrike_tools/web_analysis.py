"""原 MCP 工具的机械迁移；函数体和参数由冻结契约校验，不修改执行逻辑。"""

from typing import Any, Dict

from .support import logger


def register(mcp, hexstrike_client):
    """将本领域工具绑定到当前服务实例，保留实例独立的后端客户端。"""
    @mcp.tool()
    def jaeles_vulnerability_scan(url: str, signatures: str = "", config: str = "",
                                 threads: int = 20, timeout: int = 20,
                                 additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Jaeles for advanced vulnerability scanning with custom signatures.

        Args:
            url: The target URL
            signatures: Custom signature path
            config: Configuration file
            threads: Number of threads
            timeout: Request timeout
            additional_args: Additional Jaeles arguments

        Returns:
            Advanced vulnerability scanning results with custom signatures
        """
        data = {
            "url": url,
            "signatures": signatures,
            "config": config,
            "threads": threads,
            "timeout": timeout,
            "additional_args": additional_args
        }
        logger.info(f"🔬 Starting Jaeles vulnerability scan: {url}")
        result = hexstrike_client.safe_post("api/tools/jaeles", data)
        if result.get("success"):
            logger.info(f"✅ Jaeles vulnerability scan completed for {url}")
        else:
            logger.error(f"❌ Jaeles vulnerability scan failed for {url}")
        return result

    @mcp.tool()
    def dalfox_xss_scan(url: str, pipe_mode: bool = False, blind: bool = False,
                       mining_dom: bool = True, mining_dict: bool = True,
                       custom_payload: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Dalfox for advanced XSS vulnerability scanning with enhanced logging.

        Args:
            url: The target URL
            pipe_mode: Use pipe mode for input
            blind: Enable blind XSS testing
            mining_dom: Enable DOM mining
            mining_dict: Enable dictionary mining
            custom_payload: Custom XSS payload
            additional_args: Additional Dalfox arguments

        Returns:
            Advanced XSS vulnerability scanning results
        """
        data = {
            "url": url,
            "pipe_mode": pipe_mode,
            "blind": blind,
            "mining_dom": mining_dom,
            "mining_dict": mining_dict,
            "custom_payload": custom_payload,
            "additional_args": additional_args
        }
        logger.info(f"🎯 Starting Dalfox XSS scan: {url if url else 'pipe mode'}")
        result = hexstrike_client.safe_post("api/tools/dalfox", data)
        if result.get("success"):
            logger.info(f"✅ Dalfox XSS scan completed")
        else:
            logger.error(f"❌ Dalfox XSS scan failed")
        return result

    @mcp.tool()
    def httpx_probe(target: str, probe: bool = True, tech_detect: bool = False,
                   status_code: bool = False, content_length: bool = False,
                   title: bool = False, web_server: bool = False, threads: int = 50,
                   additional_args: str = "") -> Dict[str, Any]:
        """
        Execute httpx for fast HTTP probing and technology detection.

        Args:
            target: Target file or single URL
            probe: Enable probing
            tech_detect: Enable technology detection
            status_code: Show status codes
            content_length: Show content length
            title: Show page titles
            web_server: Show web server
            threads: Number of threads
            additional_args: Additional httpx arguments

        Returns:
            Fast HTTP probing results with technology detection
        """
        data = {
            "target": target,
            "probe": probe,
            "tech_detect": tech_detect,
            "status_code": status_code,
            "content_length": content_length,
            "title": title,
            "web_server": web_server,
            "threads": threads,
            "additional_args": additional_args
        }
        logger.info(f"🌍 Starting httpx probe: {target}")
        result = hexstrike_client.safe_post("api/tools/httpx", data)
        if result.get("success"):
            logger.info(f"✅ httpx probe completed for {target}")
        else:
            logger.error(f"❌ httpx probe failed for {target}")
        return result

    @mcp.tool()
    def anew_data_processing(input_data: str, output_file: str = "",
                            additional_args: str = "") -> Dict[str, Any]:
        """
        Execute anew for appending new lines to files (useful for data processing).

        Args:
            input_data: Input data to process
            output_file: Output file path
            additional_args: Additional anew arguments

        Returns:
            Data processing results with unique line filtering
        """
        data = {
            "input_data": input_data,
            "output_file": output_file,
            "additional_args": additional_args
        }
        logger.info("📝 Starting anew data processing")
        result = hexstrike_client.safe_post("api/tools/anew", data)
        if result.get("success"):
            logger.info("✅ anew data processing completed")
        else:
            logger.error("❌ anew data processing failed")
        return result

    @mcp.tool()
    def qsreplace_parameter_replacement(urls: str, replacement: str = "FUZZ",
                                       additional_args: str = "") -> Dict[str, Any]:
        """
        Execute qsreplace for query string parameter replacement.

        Args:
            urls: URLs to process
            replacement: Replacement string for parameters
            additional_args: Additional qsreplace arguments

        Returns:
            Parameter replacement results for fuzzing
        """
        data = {
            "urls": urls,
            "replacement": replacement,
            "additional_args": additional_args
        }
        logger.info("🔄 Starting qsreplace parameter replacement")
        result = hexstrike_client.safe_post("api/tools/qsreplace", data)
        if result.get("success"):
            logger.info("✅ qsreplace parameter replacement completed")
        else:
            logger.error("❌ qsreplace parameter replacement failed")
        return result

    @mcp.tool()
    def uro_url_filtering(urls: str, whitelist: str = "", blacklist: str = "",
                         additional_args: str = "") -> Dict[str, Any]:
        """
        Execute uro for filtering out similar URLs.

        Args:
            urls: URLs to filter
            whitelist: Whitelist patterns
            blacklist: Blacklist patterns
            additional_args: Additional uro arguments

        Returns:
            Filtered URL results with duplicates removed
        """
        data = {
            "urls": urls,
            "whitelist": whitelist,
            "blacklist": blacklist,
            "additional_args": additional_args
        }
        logger.info("🔍 Starting uro URL filtering")
        result = hexstrike_client.safe_post("api/tools/uro", data)
        if result.get("success"):
            logger.info("✅ uro URL filtering completed")
        else:
            logger.error("❌ uro URL filtering failed")
        return result
