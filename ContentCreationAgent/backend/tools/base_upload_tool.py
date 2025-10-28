"""
Base Upload Tool

Provides shared functionality for platform-specific upload tools (TikTok, YouTube, etc).
Eliminates code duplication by providing common patterns like video downloading,
sync wrappers, and mock response generation.
"""

import json
import time
import logging
import asyncio
import httpx
from abc import abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any
from langchain.tools import BaseTool

logger = logging.getLogger(__name__)


class BaseUploadTool(BaseTool):
    """
    Abstract base class for upload tools.

    Provides common functionality:
    - Video download from URL
    - Sync/async wrapper pattern
    - Mock response generation
    """

    @abstractmethod
    def get_platform_name(self) -> str:
        """Return the platform name (e.g., 'tiktok', 'youtube_shorts')."""
        pass

    @abstractmethod
    def get_temp_filename_prefix(self) -> str:
        """Return the prefix for temporary video files (e.g., 'tiktok_video', 'youtube_video')."""
        pass

    @abstractmethod
    def get_download_timeout(self) -> float:
        """Return the download timeout in seconds."""
        pass

    async def download_video(self, video_url: str) -> str:
        """
        Download video from URL or verify local path.

        This method is shared across all upload tools to eliminate duplication.

        Args:
            video_url: Video URL or local path

        Returns:
            Local file path
        """
        # Check if it's a local path
        if Path(video_url).exists():
            return video_url

        # Download from URL
        timeout = self.get_download_timeout()
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(video_url)
            response.raise_for_status()

            # Save to temp file
            prefix = self.get_temp_filename_prefix()
            temp_path = f"/tmp/{prefix}_{int(time.time())}.mp4"
            with open(temp_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Video downloaded to: {temp_path}")
            return temp_path

    def create_mock_response(
        self,
        platform: str,
        video_id_prefix: str,
        metadata: Dict[str, Any],
        platform_specific_fields: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a mock upload response for testing/development.

        Args:
            platform: Platform name (e.g., 'tiktok', 'youtube_shorts')
            video_id_prefix: Prefix for mock video ID (e.g., 'mock_tiktok')
            metadata: Common metadata (caption, title, etc.)
            platform_specific_fields: Additional platform-specific fields

        Returns:
            JSON string with mock response
        """
        mock_video_id = f"{video_id_prefix}_{int(time.time())}"

        response_data = {
            "status": "success",
            "platform": platform,
            "video_id": mock_video_id,
            "published_at": time.time(),
            "metadata": {
                "is_mock": True,
                "message": f"{platform.upper()} API not configured - this is a mock response"
            }
        }

        # Add common metadata
        response_data.update(metadata)

        # Add platform-specific fields
        if platform_specific_fields:
            response_data.update(platform_specific_fields)

        logger.info(f"{platform.upper()} credentials not configured - returning mock response")

        return json.dumps(response_data, indent=2)

    def run_async_in_sync(self, coro):
        """
        Run async coroutine in sync context.

        This is the standard pattern used by LangChain tools
        when both _run() and _arun() methods are defined.

        Args:
            coro: Async coroutine to run

        Returns:
            Result from the coroutine
        """
        return asyncio.run(coro)
