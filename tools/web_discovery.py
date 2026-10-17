"""原 MCP 工具的机械迁移；函数体和参数由冻结契约校验，不修改执行逻辑。"""

from typing import Any, Dict

from .support import logger


def register(mcp, hexstrike_client):
    """将本领域工具绑定到当前服务实例，保留实例独立的后端客户端。"""
    @mcp.tool()
    def feroxbuster_scan(url: str, wordlist: str = "/usr/share/wordlists/dirb/common.txt", threads: int = 10, additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Feroxbuster for recursive content discovery with enhanced logging.

        Args:
            url: The target URL
            wordlist: Wordlist file to use
            threads: Number of threads
            additional_args: Additional Feroxbuster arguments

        Returns:
            Content discovery results
        """
        data = {
            "url": url,
            "wordlist": wordlist,
            "threads": threads,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting Feroxbuster scan: {url}")
        result = hexstrike_client.safe_post("api/tools/feroxbuster", data)
        if result.get("success"):
            logger.info(f"✅ Feroxbuster scan completed for {url}")
        else:
            logger.error(f"❌ Feroxbuster scan failed for {url}")
        return result

    @mcp.tool()
    def dotdotpwn_scan(target: str, module: str = "http", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute DotDotPwn for directory traversal testing with enhanced logging.

        Args:
            target: The target hostname or IP
            module: Module to use (http, ftp, tftp, etc.)
            additional_args: Additional DotDotPwn arguments

        Returns:
            Directory traversal test results
        """
        data = {
            "target": target,
            "module": module,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting DotDotPwn scan: {target}")
        result = hexstrike_client.safe_post("api/tools/dotdotpwn", data)
        if result.get("success"):
            logger.info(f"✅ DotDotPwn scan completed for {target}")
        else:
            logger.error(f"❌ DotDotPwn scan failed for {target}")
        return result

    @mcp.tool()
    def xsser_scan(url: str, params: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute XSSer for XSS vulnerability testing with enhanced logging.

        Args:
            url: The target URL
            params: Parameters to test
            additional_args: Additional XSSer arguments

        Returns:
            XSS vulnerability test results
        """
        data = {
            "url": url,
            "params": params,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting XSSer scan: {url}")
        result = hexstrike_client.safe_post("api/tools/xsser", data)
        if result.get("success"):
            logger.info(f"✅ XSSer scan completed for {url}")
        else:
            logger.error(f"❌ XSSer scan failed for {url}")
        return result

    @mcp.tool()
    def wfuzz_scan(url: str, wordlist: str = "/usr/share/wordlists/dirb/common.txt", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Wfuzz for web application fuzzing with enhanced logging.

        Args:
            url: The target URL (use FUZZ where you want to inject payloads)
            wordlist: Wordlist file to use
            additional_args: Additional Wfuzz arguments

        Returns:
            Web application fuzzing results
        """
        data = {
            "url": url,
            "wordlist": wordlist,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting Wfuzz scan: {url}")
        result = hexstrike_client.safe_post("api/tools/wfuzz", data)
        if result.get("success"):
            logger.info(f"✅ Wfuzz scan completed for {url}")
        else:
            logger.error(f"❌ Wfuzz scan failed for {url}")
        return result

    @mcp.tool()
    def dirsearch_scan(url: str, extensions: str = "php,html,js,txt,xml,json",
                      wordlist: str = "/usr/share/wordlists/dirsearch/common.txt",
                      threads: int = 30, recursive: bool = False, additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Dirsearch for advanced directory and file discovery with enhanced logging.

        Args:
            url: The target URL
            extensions: File extensions to search for
            wordlist: Wordlist file to use
            threads: Number of threads to use
            recursive: Enable recursive scanning
            additional_args: Additional Dirsearch arguments

        Returns:
            Advanced directory discovery results
        """
        data = {
            "url": url,
            "extensions": extensions,
            "wordlist": wordlist,
            "threads": threads,
            "recursive": recursive,
            "additional_args": additional_args
        }
        logger.info(f"📁 Starting Dirsearch scan: {url}")
        result = hexstrike_client.safe_post("api/tools/dirsearch", data)
        if result.get("success"):
            logger.info(f"✅ Dirsearch scan completed for {url}")
        else:
            logger.error(f"❌ Dirsearch scan failed for {url}")
        return result

    @mcp.tool()
    def katana_crawl(url: str, depth: int = 3, js_crawl: bool = True,
                    form_extraction: bool = True, output_format: str = "json",
                    additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Katana for next-generation crawling and spidering with enhanced logging.

        Args:
            url: The target URL to crawl
            depth: Crawling depth
            js_crawl: Enable JavaScript crawling
            form_extraction: Enable form extraction
            output_format: Output format (json, txt)
            additional_args: Additional Katana arguments

        Returns:
            Advanced web crawling results with endpoints and forms
        """
        data = {
            "url": url,
            "depth": depth,
            "js_crawl": js_crawl,
            "form_extraction": form_extraction,
            "output_format": output_format,
            "additional_args": additional_args
        }
        logger.info(f"⚔️  Starting Katana crawl: {url}")
        result = hexstrike_client.safe_post("api/tools/katana", data)
        if result.get("success"):
            logger.info(f"✅ Katana crawl completed for {url}")
        else:
            logger.error(f"❌ Katana crawl failed for {url}")
        return result

    @mcp.tool()
    def gau_discovery(domain: str, providers: str = "wayback,commoncrawl,otx,urlscan",
                     include_subs: bool = True, blacklist: str = "png,jpg,gif,jpeg,swf,woff,svg,pdf,css,ico",
                     additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Gau (Get All URLs) for URL discovery from multiple sources with enhanced logging.

        Args:
            domain: The target domain
            providers: Data providers to use
            include_subs: Include subdomains
            blacklist: File extensions to blacklist
            additional_args: Additional Gau arguments

        Returns:
            Comprehensive URL discovery results from multiple sources
        """
        data = {
            "domain": domain,
            "providers": providers,
            "include_subs": include_subs,
            "blacklist": blacklist,
            "additional_args": additional_args
        }
        logger.info(f"📡 Starting Gau URL discovery: {domain}")
        result = hexstrike_client.safe_post("api/tools/gau", data)
        if result.get("success"):
            logger.info(f"✅ Gau URL discovery completed for {domain}")
        else:
            logger.error(f"❌ Gau URL discovery failed for {domain}")
        return result

    @mcp.tool()
    def waybackurls_discovery(domain: str, get_versions: bool = False,
                             no_subs: bool = False, additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Waybackurls for historical URL discovery with enhanced logging.

        Args:
            domain: The target domain
            get_versions: Get all versions of URLs
            no_subs: Don't include subdomains
            additional_args: Additional Waybackurls arguments

        Returns:
            Historical URL discovery results from Wayback Machine
        """
        data = {
            "domain": domain,
            "get_versions": get_versions,
            "no_subs": no_subs,
            "additional_args": additional_args
        }
        logger.info(f"🕰️  Starting Waybackurls discovery: {domain}")
        result = hexstrike_client.safe_post("api/tools/waybackurls", data)
        if result.get("success"):
            logger.info(f"✅ Waybackurls discovery completed for {domain}")
        else:
            logger.error(f"❌ Waybackurls discovery failed for {domain}")
        return result

    @mcp.tool()
    def arjun_parameter_discovery(url: str, method: str = "GET", wordlist: str = "",
                                 delay: int = 0, threads: int = 25, stable: bool = False,
                                 additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Arjun for HTTP parameter discovery with enhanced logging.

        Args:
            url: The target URL
            method: HTTP method to use
            wordlist: Custom wordlist file
            delay: Delay between requests
            threads: Number of threads
            stable: Use stable mode
            additional_args: Additional Arjun arguments

        Returns:
            HTTP parameter discovery results
        """
        data = {
            "url": url,
            "method": method,
            "wordlist": wordlist,
            "delay": delay,
            "threads": threads,
            "stable": stable,
            "additional_args": additional_args
        }
        logger.info(f"🎯 Starting Arjun parameter discovery: {url}")
        result = hexstrike_client.safe_post("api/tools/arjun", data)
        if result.get("success"):
            logger.info(f"✅ Arjun parameter discovery completed for {url}")
        else:
            logger.error(f"❌ Arjun parameter discovery failed for {url}")
        return result

    @mcp.tool()
    def paramspider_mining(domain: str, level: int = 2,
                          exclude: str = "png,jpg,gif,jpeg,swf,woff,svg,pdf,css,ico",
                          output: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute ParamSpider for parameter mining from web archives with enhanced logging.

        Args:
            domain: The target domain
            level: Mining level depth
            exclude: File extensions to exclude
            output: Output file path
            additional_args: Additional ParamSpider arguments

        Returns:
            Parameter mining results from web archives
        """
        data = {
            "domain": domain,
            "level": level,
            "exclude": exclude,
            "output": output,
            "additional_args": additional_args
        }
        logger.info(f"🕷️  Starting ParamSpider mining: {domain}")
        result = hexstrike_client.safe_post("api/tools/paramspider", data)
        if result.get("success"):
            logger.info(f"✅ ParamSpider mining completed for {domain}")
        else:
            logger.error(f"❌ ParamSpider mining failed for {domain}")
        return result

    @mcp.tool()
    def x8_parameter_discovery(url: str, wordlist: str = "/usr/share/wordlists/x8/params.txt",
                              method: str = "GET", body: str = "", headers: str = "",
                              additional_args: str = "") -> Dict[str, Any]:
        """
        Execute x8 for hidden parameter discovery with enhanced logging.

        Args:
            url: The target URL
            wordlist: Parameter wordlist
            method: HTTP method
            body: Request body
            headers: Custom headers
            additional_args: Additional x8 arguments

        Returns:
            Hidden parameter discovery results
        """
        data = {
            "url": url,
            "wordlist": wordlist,
            "method": method,
            "body": body,
            "headers": headers,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting x8 parameter discovery: {url}")
        result = hexstrike_client.safe_post("api/tools/x8", data)
        if result.get("success"):
            logger.info(f"✅ x8 parameter discovery completed for {url}")
        else:
            logger.error(f"❌ x8 parameter discovery failed for {url}")
        return result
