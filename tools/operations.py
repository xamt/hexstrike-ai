"""原 MCP 工具的机械迁移；函数体和参数由冻结契约校验，不修改执行逻辑。"""

from typing import Any, Dict

from .support import logger


def register(mcp, hexstrike_client):
    """将本领域工具绑定到当前服务实例，保留实例独立的后端客户端。"""
    @mcp.tool()
    def server_health() -> Dict[str, Any]:
        """
        Check the health status of the HexStrike AI server.

        Returns:
            Server health information with tool availability and telemetry
        """
        logger.info(f"🏥 Checking HexStrike AI server health")
        result = hexstrike_client.check_health()
        if result.get("status") == "healthy":
            logger.info(f"✅ Server is healthy - {result.get('total_tools_available', 0)} tools available")
        else:
            logger.warning(f"⚠️  Server health check returned: {result.get('status', 'unknown')}")
        return result

    @mcp.tool()
    def get_cache_stats() -> Dict[str, Any]:
        """
        Get cache statistics from the HexStrike AI server.

        Returns:
            Cache performance statistics
        """
        logger.info(f"💾 Getting cache statistics")
        result = hexstrike_client.safe_get("api/cache/stats")
        if "hit_rate" in result:
            logger.info(f"📊 Cache hit rate: {result.get('hit_rate', 'unknown')}")
        return result

    @mcp.tool()
    def clear_cache() -> Dict[str, Any]:
        """
        Clear the cache on the HexStrike AI server.

        Returns:
            Cache clear operation results
        """
        logger.info(f"🧹 Clearing server cache")
        result = hexstrike_client.safe_post("api/cache/clear", {})
        if result.get("success"):
            logger.info(f"✅ Cache cleared successfully")
        else:
            logger.error(f"❌ Failed to clear cache")
        return result

    @mcp.tool()
    def get_telemetry() -> Dict[str, Any]:
        """
        Get system telemetry from the HexStrike AI server.

        Returns:
            System performance and usage telemetry
        """
        logger.info(f"📈 Getting system telemetry")
        result = hexstrike_client.safe_get("api/telemetry")
        if "commands_executed" in result:
            logger.info(f"📊 Commands executed: {result.get('commands_executed', 0)}")
        return result

    @mcp.tool()
    def list_active_processes() -> Dict[str, Any]:
        """
        List all active processes on the HexStrike AI server.

        Returns:
            List of active processes with their status and progress
        """
        logger.info("📊 Listing active processes")
        result = hexstrike_client.safe_get("api/processes/list")
        if result.get("success"):
            logger.info(f"✅ Found {result.get('total_count', 0)} active processes")
        else:
            logger.error("❌ Failed to list processes")
        return result

    @mcp.tool()
    def get_process_status(pid: int) -> Dict[str, Any]:
        """
        Get the status of a specific process.

        Args:
            pid: Process ID to check

        Returns:
            Process status information including progress and runtime
        """
        logger.info(f"🔍 Checking status of process {pid}")
        result = hexstrike_client.safe_get(f"api/processes/status/{pid}")
        if result.get("success"):
            logger.info(f"✅ Process {pid} status retrieved")
        else:
            logger.error(f"❌ Process {pid} not found or error occurred")
        return result

    @mcp.tool()
    def terminate_process(pid: int) -> Dict[str, Any]:
        """
        Terminate a specific running process.

        Args:
            pid: Process ID to terminate

        Returns:
            Success status of the termination operation
        """
        logger.info(f"🛑 Terminating process {pid}")
        result = hexstrike_client.safe_post(f"api/processes/terminate/{pid}", {})
        if result.get("success"):
            logger.info(f"✅ Process {pid} terminated successfully")
        else:
            logger.error(f"❌ Failed to terminate process {pid}")
        return result

    @mcp.tool()
    def pause_process(pid: int) -> Dict[str, Any]:
        """
        Pause a specific running process.

        Args:
            pid: Process ID to pause

        Returns:
            Success status of the pause operation
        """
        logger.info(f"⏸️ Pausing process {pid}")
        result = hexstrike_client.safe_post(f"api/processes/pause/{pid}", {})
        if result.get("success"):
            logger.info(f"✅ Process {pid} paused successfully")
        else:
            logger.error(f"❌ Failed to pause process {pid}")
        return result

    @mcp.tool()
    def resume_process(pid: int) -> Dict[str, Any]:
        """
        Resume a paused process.

        Args:
            pid: Process ID to resume

        Returns:
            Success status of the resume operation
        """
        logger.info(f"▶️ Resuming process {pid}")
        result = hexstrike_client.safe_post(f"api/processes/resume/{pid}", {})
        if result.get("success"):
            logger.info(f"✅ Process {pid} resumed successfully")
        else:
            logger.error(f"❌ Failed to resume process {pid}")
        return result

    @mcp.tool()
    def get_process_dashboard() -> Dict[str, Any]:
        """
        Get enhanced process dashboard with visual status indicators.

        Returns:
            Real-time dashboard with progress bars, system metrics, and process status
        """
        logger.info("📊 Getting process dashboard")
        result = hexstrike_client.safe_get("api/processes/dashboard")
        if result.get("success", True) and "total_processes" in result:
            total = result.get("total_processes", 0)
            logger.info(f"✅ Dashboard retrieved: {total} active processes")

            # Log visual summary for better UX
            if total > 0:
                logger.info("📈 Active Processes Summary:")
                for proc in result.get("processes", [])[:3]:  # Show first 3
                    logger.info(f"   ├─ PID {proc['pid']}: {proc['progress_bar']} {proc['progress_percent']}")
        else:
            logger.error("❌ Failed to get process dashboard")
        return result

    @mcp.tool()
    def execute_command(command: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Execute an arbitrary command on the HexStrike AI server with enhanced logging.

        Args:
            command: The command to execute
            use_cache: Whether to use caching for this command

        Returns:
            Command execution results with enhanced telemetry
        """
        try:
            logger.info(f"⚡ Executing command: {command}")
            result = hexstrike_client.execute_command(command, use_cache)
            if "error" in result:
                logger.error(f"❌ Command failed: {result['error']}")
                return {
                    "success": False,
                    "error": result["error"],
                    "stdout": "",
                    "stderr": f"Error executing command: {result['error']}"
                }

            if result.get("success"):
                execution_time = result.get("execution_time", 0)
                logger.info(f"✅ Command completed successfully in {execution_time:.2f}s")
            else:
                logger.warning(f"⚠️  Command completed with errors")

            return result
        except Exception as e:
            logger.error(f"💥 Error executing command '{command}': {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": f"Error executing command: {str(e)}"
            }
