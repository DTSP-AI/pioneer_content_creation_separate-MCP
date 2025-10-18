"""
PiAPI MCP Client

Connects to PiAPI MCP Server via Server-Sent Events (SSE) to access advanced
video generation tools through the Model Context Protocol.

Pattern adopted from mcp-voice-agent example's MCPClientWrapper.

Architecture:
- Connects to local PiAPI MCP server (Node.js/TypeScript)
- Retrieves available tools via MCP protocol
- Converts MCP tools to LangChain-compatible tools
- Caches client connection for reuse
"""

from typing import List, Optional, Tuple, Any, Dict
import logging
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_core.tools import Tool

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# Global client cache (singleton pattern)
_piapi_mcp_client: Optional['PiAPIMCPClient'] = None


class PiAPIMCPClient:
    """
    PiAPI MCP Client - Connects to PiAPI MCP server.

    Manages connection lifecycle and tool retrieval from the MCP server.

    Usage:
        client = PiAPIMCPClient()
        await client.connect()
        tools = await client.get_tools()
        await client.close()
    """

    def __init__(
        self,
        server_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize PiAPI MCP client.

        Args:
            server_url: MCP server URL (defaults to config)
            api_key: PiAPI API key (defaults to config)
        """
        self.server_url = server_url or settings.PIAPI_MCP_SERVER_URL
        self.api_key = api_key or settings.PIAPI_API_KEY
        self.session: Optional[ClientSession] = None
        self.tools: List[Tool] = []
        self._connected = False

    async def connect(self) -> None:
        """
        Connect to PiAPI MCP server.

        Establishes SSE connection and initializes client session.
        """
        try:
            logger.info(f"Connecting to PiAPI MCP server: {self.server_url}")

            # For SSE-based MCP servers, we use httpx client
            # Note: The actual MCP connection depends on server implementation
            # This is a simplified version - adjust based on actual PiAPI MCP server

            # Test connection
            async with httpx.AsyncClient() as client:
                response = await client.get(self.server_url, timeout=5.0)
                if response.status_code != 200:
                    raise ConnectionError(f"MCP server returned status {response.status_code}")

            logger.info("PiAPI MCP server connection established")
            self._connected = True

        except Exception as e:
            logger.error(f"Failed to connect to PiAPI MCP server: {e}")
            raise ConnectionError(f"PiAPI MCP connection failed: {e}")

    async def get_tools(self) -> List[Tool]:
        """
        Retrieve tools from PiAPI MCP server.

        Returns:
            List of LangChain-compatible tools

        Raises:
            RuntimeError: If not connected
        """
        if not self._connected:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            logger.info("Retrieving tools from PiAPI MCP server...")

            # Mock tools for now - replace with actual MCP tool discovery
            # In production, this would query the MCP server's tool list
            self.tools = await self._discover_mcp_tools()

            logger.info(f"Retrieved {len(self.tools)} tools from PiAPI MCP")

            return self.tools

        except Exception as e:
            logger.error(f"Failed to retrieve MCP tools: {e}")
            return []

    async def _discover_mcp_tools(self) -> List[Tool]:
        """
        Discover available tools from PiAPI MCP server.

        This is a placeholder implementation. In production, this would:
        1. Query MCP server's tool list endpoint
        2. Parse tool schemas
        3. Convert to LangChain Tool objects

        Returns:
            List of discovered tools
        """
        # Placeholder: Define expected PiAPI tools based on MCP server capabilities
        # These should match the tools exposed by PiAPI_MCP/piapi-mcp-server

        tools = []

        # Tool 1: Generate Video (Hunyuan, Kling, Luma, etc.)
        async def generate_video(
            prompt: str,
            model: str = "hunyuan",
            duration: int = 5,
            aspect_ratio: str = "9:16"
        ) -> Dict[str, Any]:
            """
            Generate video from text prompt using PiAPI models.

            Args:
                prompt: Text description of video
                model: Video model (hunyuan, kling, luma, minimax, runway)
                duration: Video duration in seconds
                aspect_ratio: Aspect ratio (9:16 for TikTok/Shorts, 16:9 for landscape)

            Returns:
                Video generation result with URL
            """
            # Placeholder - actual implementation would call PiAPI MCP server
            logger.info(f"Generating video via MCP: model={model}, prompt={prompt[:50]}")
            return {
                "status": "pending",
                "message": "MCP video generation not yet implemented",
                "model": model,
                "prompt": prompt
            }

        video_tool = Tool(
            name="piapi_generate_video",
            description="Generate AI video from text prompt using state-of-the-art models (Hunyuan, Kling, Luma, Minimax, Runway). Supports various aspect ratios and durations.",
            func=lambda **kwargs: generate_video(**kwargs),
            coroutine=generate_video
        )
        tools.append(video_tool)

        # Tool 2: Generate Image
        async def generate_image(
            prompt: str,
            model: str = "flux",
            size: str = "1024x1024"
        ) -> Dict[str, Any]:
            """
            Generate image from text prompt.

            Args:
                prompt: Image description
                model: Image model (flux, midjourney, stable-diffusion)
                size: Image size

            Returns:
                Image generation result
            """
            logger.info(f"Generating image via MCP: model={model}, prompt={prompt[:50]}")
            return {
                "status": "pending",
                "message": "MCP image generation not yet implemented"
            }

        image_tool = Tool(
            name="piapi_generate_image",
            description="Generate AI image from text prompt using Flux, Midjourney, or Stable Diffusion",
            func=lambda **kwargs: generate_image(**kwargs),
            coroutine=generate_image
        )
        tools.append(image_tool)

        # Tool 3: Text-to-Speech (if supported)
        async def text_to_speech(
            text: str,
            voice: str = "default",
            language: str = "en"
        ) -> Dict[str, Any]:
            """
            Convert text to speech audio.

            Args:
                text: Text to convert
                voice: Voice preset
                language: Language code

            Returns:
                Audio generation result
            """
            logger.info(f"Generating TTS via MCP: text={text[:50]}")
            return {
                "status": "pending",
                "message": "MCP TTS not yet implemented"
            }

        tts_tool = Tool(
            name="piapi_text_to_speech",
            description="Convert text to speech audio for video voiceovers",
            func=lambda **kwargs: text_to_speech(**kwargs),
            coroutine=text_to_speech
        )
        tools.append(tts_tool)

        logger.info(f"Discovered {len(tools)} placeholder tools (replace with actual MCP discovery)")

        return tools

    async def close(self) -> None:
        """Close MCP client connection."""
        if self.session:
            # Close session if needed
            pass
        self._connected = False
        logger.info("PiAPI MCP client connection closed")


# =============================================================================
# Convenience Functions
# =============================================================================

async def get_piapi_mcp_client() -> Tuple[PiAPIMCPClient, List[Tool]]:
    """
    Get or create PiAPI MCP client singleton.

    Returns:
        Tuple of (client, tools)

    Usage:
        client, tools = await get_piapi_mcp_client()
    """
    global _piapi_mcp_client

    # Check if MCP is enabled
    if not settings.PIAPI_MCP_ENABLED:
        logger.warning("PiAPI MCP is disabled in config. Returning empty tools.")
        return None, []

    # Return cached client if available
    if _piapi_mcp_client is not None and _piapi_mcp_client._connected:
        logger.info("Reusing existing PiAPI MCP client")
        return _piapi_mcp_client, _piapi_mcp_client.tools

    # Create new client
    try:
        client = PiAPIMCPClient()
        await client.connect()
        tools = await client.get_tools()

        # Cache for reuse
        _piapi_mcp_client = client

        logger.info(f"PiAPI MCP client initialized with {len(tools)} tools")

        return client, tools

    except Exception as e:
        logger.error(f"Failed to initialize PiAPI MCP client: {e}")
        logger.warning("Continuing without MCP tools")
        return None, []


async def close_piapi_mcp_client() -> None:
    """
    Close global PiAPI MCP client connection.

    Call this during application shutdown.
    """
    global _piapi_mcp_client

    if _piapi_mcp_client:
        await _piapi_mcp_client.close()
        _piapi_mcp_client = None
        logger.info("Global PiAPI MCP client closed")
