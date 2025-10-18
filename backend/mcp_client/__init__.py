"""
MCP Client Module

Model Context Protocol (MCP) client for connecting to external MCP servers.

Currently supports:
- PiAPI MCP Server (video generation tools via SSE)

Pattern adopted from mcp-voice-agent example.
"""

from backend.mcp_client.piapi_client import (
    get_piapi_mcp_client,
    PiAPIMCPClient
)

__all__ = [
    "get_piapi_mcp_client",
    "PiAPIMCPClient"
]
