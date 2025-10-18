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
from .piapi_video_tool import PiAPIVideoTool  # Fallback if MCP unavailable
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
            PiAPIVideoTool(),  # Fallback if MCP unavailable
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

        # Try to load MCP tools
        try:
            _, mcp_tools = await get_piapi_mcp_client()
            if mcp_tools:
                logger.info(f"Loaded {len(mcp_tools)} tools from PiAPI MCP")
                # Add MCP tools (they replace PiAPIVideoTool if available)
                tools.extend(mcp_tools)
            else:
                logger.info("No MCP tools loaded, using static tools only")
        except Exception as e:
            logger.warning(f"Failed to load MCP tools: {e}. Using static tools.")

        return tools

    @staticmethod
    async def get_content_creation_tools() -> List[BaseTool]:
        """
        Get tools for ContentCreationAgent (hybrid MCP + LangChain).

        These tools handle:
        - Trend fetching (Google Sheets) - LangChain
        - Script generation (Claude) - LangChain
        - Video generation - MCP preferred, LangChain fallback
          * AI voiceover (MCP)
          * AI video generation (MCP: Hunyuan, Kling, Luma, etc.)
          * Auto captions (MCP)
          * Platform formatting (MCP)

        Returns:
            List of content creation tools
        """
        # Base workflow tools (always present)
        base_tools = [
            GoogleSheetsTrendsTool(),
            VideoScriptGeneratorTool()
        ]

        # Try to load MCP video generation tools
        try:
            _, mcp_tools = await get_piapi_mcp_client()
            if mcp_tools:
                logger.info(f"Using {len(mcp_tools)} MCP tools for content creation")
                # Use MCP tools for video generation
                return base_tools + mcp_tools
            else:
                # Fallback to PiAPIVideoTool (direct API)
                logger.info("Using PiAPIVideoTool (direct API) fallback")
                return base_tools + [PiAPIVideoTool()]
        except Exception as e:
            logger.warning(f"MCP tools unavailable: {e}. Using PiAPIVideoTool fallback.")
            return base_tools + [PiAPIVideoTool()]

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
    "PiAPIVideoTool",
    "TikTokUploadTool",
    "YouTubeShortsUploadTool",
    "GoogleSheetsTrendsTool"
]
