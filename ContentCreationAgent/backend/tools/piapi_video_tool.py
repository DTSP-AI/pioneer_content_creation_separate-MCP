"""
PiAPI Video Generation Tool - MCP STUB ONLY

⚠️ THIS IS A FALLBACK STUB - SHOULD NEVER BE USED IN PRODUCTION ⚠️

All PiAPI video generation MUST go through the MCP server at:
  PIAPI_MCP_SERVER_URL=http://127.0.0.1:8809/sse

The MCP server (TypeScript FastMCP) handles:
- Unified AI generation tools (image, video, audio)
- 4 MCP tools: process_image_unified, generate_video_unified, generate_audio_unified, health_check
- SSE-based real-time communication
- PiAPI API integration with proper credentials

Architecture Flow:
  Backend → MCP Client → FastMCP Server (http://127.0.0.1:8809/sse) → PiAPI API

The FastMCP Server internally handles PiAPI API calls using credentials from:
  PiAPI_MCP/piapi_fastmcp_server/.env.local

This stub exists ONLY for graceful degradation if MCP server is down.
It should NEVER make direct API calls to PiAPI.
"""

from typing import Optional, Type
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
import logging

logger = logging.getLogger(__name__)


class PiAPIVideoInput(BaseModel):
    """Input schema for PiAPI video generation (stub)."""

    script: str = Field(
        description="Video script text"
    )

    topic: Optional[str] = Field(
        default=None,
        description="Video topic/title for context"
    )

    platform: str = Field(
        default="tiktok",
        description="Target platform: 'tiktok' or 'youtube_shorts'"
    )

    duration_seconds: int = Field(
        default=30,
        description="Desired video duration (15-60 seconds)"
    )

    style: str = Field(
        default="realistic",
        description="Video style: 'realistic', 'anime', 'cartoon', 'cinematic'"
    )

    include_captions: bool = Field(
        default=True,
        description="Auto-generate captions"
    )

    voice_gender: str = Field(
        default="female",
        description="Voice gender: 'male' or 'female'"
    )


class PiAPIVideoTool(BaseTool):
    """
    ⚠️ FALLBACK STUB - MCP SERVER REQUIRED ⚠️

    This tool is a STUB that should NEVER execute in production.

    All video generation MUST go through the MCP server.
    If this tool executes, it means:
    1. PIAPI_MCP_ENABLED=false (wrong!)
    2. MCP server is down (critical error!)
    3. get_piapi_mcp_client() failed (needs investigation!)

    DO NOT add direct API implementation here.
    DO NOT use PIAPI_API_KEY from backend config.
    DO NOT make httpx/requests calls to api.piapi.ai.

    The ONLY correct path is: Backend → MCP Server → PiAPI API
    """

    name: str = "piapi_video_generator"
    description: str = """
    ⚠️ STUB TOOL - MCP SERVER REQUIRED ⚠️

    This is a fallback stub. If you see this tool, the MCP server is not available.

    Video generation requires the PiAPI FastMCP server (TypeScript) running at:
    http://127.0.0.1:8809/sse

    Start the FastMCP server via Docker:
    docker-compose up -d piapi-mcp

    The server provides 4 unified MCP tools:
    - process_image_unified
    - generate_video_unified
    - generate_audio_unified
    - health_check
    """
    args_schema: Type[BaseModel] = PiAPIVideoInput

    def _run(
        self,
        script: str,
        topic: Optional[str] = None,
        platform: str = "tiktok",
        duration_seconds: int = 30,
        style: str = "realistic",
        include_captions: bool = True,
        voice_gender: str = "female"
    ) -> str:
        """Sync execution stub."""
        import json

        error_msg = (
            "❌ PiAPI FASTMCP SERVER NOT AVAILABLE\n\n"
            "Video generation requires the PiAPI FastMCP server (TypeScript).\n\n"
            "This stub tool should NEVER execute in production.\n\n"
            "Resolution:\n"
            "1. Ensure FastMCP server is running: docker-compose ps piapi-mcp\n"
            "2. Check MCP server URL: PIAPI_MCP_SERVER_URL=http://127.0.0.1:8809/sse\n"
            "3. Verify MCP enabled: PIAPI_MCP_ENABLED=true\n"
            "4. Check MCP logs: docker-compose logs piapi-mcp\n"
            "5. Test MCP health: curl http://localhost:8006/health/mcp\n\n"
            "DO NOT add direct PiAPI API calls here. All requests must go through FastMCP."
        )

        logger.error(error_msg)

        return json.dumps({
            "status": "error",
            "error": "MCP_SERVER_REQUIRED",
            "message": error_msg,
            "video_url": None,
            "resolution": {
                "check_mcp_status": "docker-compose ps piapi-mcp",
                "check_mcp_logs": "docker-compose logs piapi-mcp",
                "verify_env": "PIAPI_MCP_ENABLED=true and PIAPI_MCP_SERVER_URL=http://127.0.0.1:8809/sse",
                "test_health": "curl http://localhost:8006/health/mcp"
            }
        }, indent=2)

    async def _arun(
        self,
        script: str,
        topic: Optional[str] = None,
        platform: str = "tiktok",
        duration_seconds: int = 30,
        style: str = "realistic",
        include_captions: bool = True,
        voice_gender: str = "female"
    ) -> str:
        """Async execution stub."""
        return self._run(
            script, topic, platform, duration_seconds,
            style, include_captions, voice_gender
        )
