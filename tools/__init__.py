"""Streamable HTTP MCP 服务的工具目录。"""

from .network_core import register as register_network_core
from .cloud_security import register as register_cloud_security
from .container_security import register as register_container_security
from .workspace import register as register_workspace
from .assessment import register as register_assessment
from .network_credentials import register as register_network_credentials
from .network_discovery import register as register_network_discovery
from .binary_analysis import register as register_binary_analysis
from .exploit_development import register as register_exploit_development
from .web_discovery import register as register_web_discovery
from .web_analysis import register as register_web_analysis
from .ai_payloads import register as register_ai_payloads
from .api_security import register as register_api_security
from .forensics import register as register_forensics
from .web_scanners import register as register_web_scanners
from .autorecon import register as register_autorecon
from .operations import register as register_operations
from .threat_research import register as register_threat_research
from .threat_intelligence import register as register_threat_intelligence
from .reporting import register as register_reporting
from .ai_workflows import register as register_ai_workflows
from .bugbounty import register as register_bugbounty
from .http_testing import register as register_http_testing
from .error_recovery import register as register_error_recovery


def register_tools(mcp, hexstrike_client):
    """按原顺序注册全部工具；重复名称沿用服务端的首次注册语义。"""
    register_network_core(mcp, hexstrike_client)
    register_cloud_security(mcp, hexstrike_client)
    register_container_security(mcp, hexstrike_client)
    register_workspace(mcp, hexstrike_client)
    register_assessment(mcp, hexstrike_client)
    register_network_credentials(mcp, hexstrike_client)
    register_network_discovery(mcp, hexstrike_client)
    register_binary_analysis(mcp, hexstrike_client)
    register_exploit_development(mcp, hexstrike_client)
    register_web_discovery(mcp, hexstrike_client)
    register_web_analysis(mcp, hexstrike_client)
    register_ai_payloads(mcp, hexstrike_client)
    register_api_security(mcp, hexstrike_client)
    register_forensics(mcp, hexstrike_client)
    register_web_scanners(mcp, hexstrike_client)
    register_autorecon(mcp, hexstrike_client)
    register_operations(mcp, hexstrike_client)
    register_threat_research(mcp, hexstrike_client)
    register_threat_intelligence(mcp, hexstrike_client)
    register_reporting(mcp, hexstrike_client)
    register_ai_workflows(mcp, hexstrike_client)
    register_bugbounty(mcp, hexstrike_client)
    register_http_testing(mcp, hexstrike_client)
    register_error_recovery(mcp, hexstrike_client)
