"""原 MCP 工具的机械迁移；函数体和参数由冻结契约校验，不修改执行逻辑。"""

from typing import Any, Dict

from .support import ToolsColors, logger


def register(mcp, tool_client):
    """将本领域工具绑定到当前服务实例，保留实例独立的后端客户端。"""
    @mcp.tool()
    def error_handling_statistics() -> Dict[str, Any]:
        """
        Get intelligent error handling system statistics and recent error patterns.

        Returns:
            Error handling statistics and patterns
        """
        logger.info(f"{ToolsColors.ELECTRIC_PURPLE}📊 Retrieving error handling statistics{ToolsColors.RESET}")
        result = tool_client.safe_get("api/error-handling/statistics")

        if result.get("success"):
            stats = result.get("statistics", {})
            total_errors = stats.get("total_errors", 0)
            recent_errors = stats.get("recent_errors_count", 0)

            logger.info(f"{ToolsColors.SUCCESS}✅ Error statistics retrieved{ToolsColors.RESET}")
            logger.info(f"  📈 Total Errors: {total_errors}")
            logger.info(f"  🕒 Recent Errors: {recent_errors}")

            # Log error breakdown by type
            error_counts = stats.get("error_counts_by_type", {})
            if error_counts:
                logger.info(f"{ToolsColors.HIGHLIGHT_BLUE} ERROR BREAKDOWN {ToolsColors.RESET}")
                for error_type, count in error_counts.items():
                                          logger.info(f"  {ToolsColors.FIRE_RED}{error_type}: {count}{ToolsColors.RESET}")
        else:
            logger.error(f"{ToolsColors.ERROR}❌ Failed to retrieve error statistics{ToolsColors.RESET}")

        return result

    @mcp.tool()
    def test_error_recovery(tool_name: str, error_type: str = "timeout",
                           target: str = "example.com") -> Dict[str, Any]:
        """
        Test the intelligent error recovery system with simulated failures.

        Args:
            tool_name: Name of tool to simulate error for
            error_type: Type of error to simulate (timeout, permission_denied, network_unreachable, etc.)
            target: Target for the simulated test

        Returns:
            Recovery strategy and system response
        """
        data_payload = {
            "tool_name": tool_name,
            "error_type": error_type,
            "target": target
        }

        logger.info(f"{ToolsColors.RUBY}🧪 Testing error recovery for {tool_name} with {error_type}{ToolsColors.RESET}")
        result = tool_client.safe_post("api/error-handling/test-recovery", data_payload)

        if result.get("success"):
            recovery_strategy = result.get("recovery_strategy", {})
            action = recovery_strategy.get("action", "unknown")
            success_prob = recovery_strategy.get("success_probability", 0)

            logger.info(f"{ToolsColors.SUCCESS}✅ Error recovery test completed{ToolsColors.RESET}")
            logger.info(f"  🔧 Recovery Action: {action}")
            logger.info(f"  📊 Success Probability: {success_prob:.2%}")

            # Log alternative tools if available
            alternatives = result.get("alternative_tools", [])
            if alternatives:
                logger.info(f"  🔄 Alternative Tools: {', '.join(alternatives)}")
        else:
            logger.error(f"{ToolsColors.ERROR}❌ Error recovery test failed{ToolsColors.RESET}")

        return result
