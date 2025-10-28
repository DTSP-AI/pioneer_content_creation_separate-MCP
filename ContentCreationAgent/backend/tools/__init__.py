"""
Tool Registry for Content Creation System (Hybrid MCP + LangChain)

Centralized registry combining:
1. LangChain BaseTool implementations (native tools)
2. MCP-loaded tools (from PiAPI MCP server)

Architecture Compliance:
- All tools extend LangChain BaseTool
- Tools are bound to LLMs, not agents
- No mock implementations (all real API clients)
- Hybrid approach: MCP for advanced video features, LangChain for workflow tools

Pattern adopted from mcp-voice-agent:
- Load MCP tools dynamically at startup
- Combine with static LangChain tools
- Graceful degradation if MCP unavailable
"""

from typing import List
import logging
from langchain.tools import BaseTool

from .video_script_tool import VideoScriptGeneratorTool
from .google_sheets_tool import GoogleSheetsTrendsTool

# Upload tools (platform-specific)
from .tiktok_upload_tool import TikTokUploadTool
from .ytshorts_upload_tool import YouTubeShortsUploadTool

# MCP client (lazy import)
from backend.mcp_client import get_piapi_mcp_client

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Hybrid Tool Registry (MCP + LangChain).

    Combines:
    1. Static LangChain tools (native implementations)
    2. Dynamic MCP tools (loaded from PiAPI MCP server)

    Usage:
        # Get all tools (includes MCP)
        tools = await ToolRegistry.get_all_tools()

        # Get content creation tools (includes MCP video tools)
        content_tools = await ToolRegistry.get_content_creation_tools()

        # Get tools without MCP (fallback)
        static_tools = ToolRegistry.get_static_tools()

        # Bind to LLM
        llm_with_tools = llm.bind_tools(tools)
    """

    @staticmethod
    def get_static_tools() -> List[BaseTool]:
        """
        Get static LangChain tools only (no MCP).

        Returns:
            List of native LangChain BaseTool implementations
        """
        return [
            GoogleSheetsTrendsTool(),
            VideoScriptGeneratorTool(),
            TikTokUploadTool(),
            YouTubeShortsUploadTool()
        ]

    @staticmethod
    async def get_all_tools() -> List[BaseTool]:
        """
        Get all available tools (static + MCP).

        Loads MCP tools if enabled, falls back to static tools if MCP unavailable.

        Returns:
            Combined list of all tools
        """
        # Start with static tools
        tools = ToolRegistry.get_static_tools()

        # Try to load FastMCP tools (4 unified tools)
        try:
            _, mcp_tools = await get_piapi_mcp_client()
            if mcp_tools:
                logger.info(f"Loaded {len(mcp_tools)} tools from FastMCP (expected: 4)")
                # Add FastMCP tools (they replace PiAPIVideoTool if available)
                tools.extend(mcp_tools)
            else:
                logger.info("No FastMCP tools loaded, using static tools only")
        except Exception as e:
            logger.warning(f"Failed to load FastMCP tools: {e}. Using static tools.")

        return tools

    @staticmethod
    async def get_content_creation_tools() -> List[BaseTool]:
        """
        Get tools for ContentCreationAgent (hybrid FastMCP + LangChain).

        These tools handle:
        - Trend fetching (Google Sheets) - LangChain
        - Script generation (Claude) - LangChain
        - Video generation - FastMCP preferred, LangChain fallback
          * AI voiceover (FastMCP unified)
          * AI video generation (FastMCP: generate_video_unified)
          * Auto captions (FastMCP unified)
          * Platform formatting (FastMCP unified)

        Returns:
            List of content creation tools (base + 4 FastMCP tools or fallback)
        """
        # Base workflow tools (always present)
        base_tools = [
            GoogleSheetsTrendsTool(),
            VideoScriptGeneratorTool()
        ]

        # Try to load FastMCP video generation tools (4 unified tools)
        try:
            _, mcp_tools = await get_piapi_mcp_client()
            if mcp_tools:
                logger.info(f"Using {len(mcp_tools)} FastMCP tools for content creation (expected: 4)")
                # Use FastMCP tools for video generation
                return base_tools + mcp_tools
            else:
                # No MCP tools available - return base tools only
                logger.warning("FastMCP tools not available, returning base tools only")
                return base_tools
        except Exception as e:
            logger.error(f"FastMCP tools unavailable: {e}. Returning base tools only.")
            return base_tools

    @staticmethod
    def get_tiktok_tools() -> List[BaseTool]:
        """
        Get tools for TikTokAgent.

        TikTok agent just needs upload tool.
        (PiAPI already formatted video correctly)
        """
        return [
            TikTokUploadTool()
        ]

    @staticmethod
    def get_youtube_tools() -> List[BaseTool]:
        """
        Get tools for YouTubeShortsAgent.

        YouTube agent just needs upload tool.
        (PiAPI already formatted video correctly)
        """
        return [
            YouTubeShortsUploadTool()
        ]

    @staticmethod
    def get_supervisor_tools() -> List[BaseTool]:
        """
        Get tools for SupervisorAgent.

        Supervisor typically doesn't use tools directly,
        but may need access for routing decisions.
        """
        return []


__all__ = [
    "ToolRegistry",
    "VideoScriptGeneratorTool",
    "TikTokUploadTool",
    "YouTubeShortsUploadTool",
    "GoogleSheetsTrendsTool"
]
