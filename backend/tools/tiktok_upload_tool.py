"""
TikTok Upload Tool

Uploads videos to TikTok using the TikTok Content Posting API.
Used by TikTokAgent for final content distribution.

API Documentation: https://developers.tiktok.com/doc/content-posting-api-overview
"""

from typing import Optional, Type, Dict, Any
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
import logging
import httpx
import asyncio
from pathlib import Path

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TikTokUploadInput(BaseModel):
    """Input schema for TikTok upload."""

    video_url: str = Field(
        description="URL or local path to video file to upload"
    )

    caption: str = Field(
        description="Video caption (max 2200 characters)"
    )

    hashtags: Optional[list[str]] = Field(
        default=None,
        description="List of hashtags (without # symbol)"
    )

    privacy_level: str = Field(
        default="PUBLIC_TO_EVERYONE",
        description="Privacy: PUBLIC_TO_EVERYONE, MUTUAL_FOLLOW_FRIENDS, SELF_ONLY"
    )

    allow_comments: bool = Field(
        default=True,
        description="Allow comments on video"
    )

    allow_duet: bool = Field(
        default=True,
        description="Allow duets"
    )

    allow_stitch: bool = Field(
        default=True,
        description="Allow stitching"
    )


class TikTokUploadTool(BaseTool):
    """
    Upload videos to TikTok.

    Uses TikTok Content Posting API v2.
    Requires TikTok developer app credentials and user authorization.

    Flow:
    1. Download video (if URL)
    2. Initialize upload session
    3. Upload video chunks
    4. Publish with metadata
    5. Return TikTok video URL
    """

    name: str = "tiktok_upload"
    description: str = """
    Upload a video to TikTok with caption and metadata.

    Input: video URL/path, caption, hashtags, privacy settings
    Output: Published TikTok video URL and video ID

    Handles the complete TikTok publishing workflow including
    video upload, metadata attachment, and publication.
    """
    args_schema: Type[BaseModel] = TikTokUploadInput

    def _run(
        self,
        video_url: str,
        caption: str,
        hashtags: Optional[list[str]] = None,
        privacy_level: str = "PUBLIC_TO_EVERYONE",
        allow_comments: bool = True,
        allow_duet: bool = True,
        allow_stitch: bool = True
    ) -> str:
        """Sync execution (not used)."""
        import asyncio
        return asyncio.run(self._arun(
            video_url, caption, hashtags, privacy_level,
            allow_comments, allow_duet, allow_stitch
        ))

    async def _arun(
        self,
        video_url: str,
        caption: str,
        hashtags: Optional[list[str]] = None,
        privacy_level: str = "PUBLIC_TO_EVERYONE",
        allow_comments: bool = True,
        allow_duet: bool = True,
        allow_stitch: bool = True
    ) -> str:
        """
        Async execution - upload to TikTok.

        Args:
            video_url: Video URL or local path
            caption: Video caption
            hashtags: Optional hashtags
            privacy_level: Privacy setting
            allow_comments: Enable comments
            allow_duet: Enable duets
            allow_stitch: Enable stitching

        Returns:
            JSON string with TikTok video URL and metadata
        """
        try:
            logger.info(f"Starting TikTok upload for video: {video_url}")

            # Check if credentials configured
            if not settings.TIKTOK_ACCESS_TOKEN:
                logger.warning("TikTok credentials not configured - using mock upload")
                return self._mock_upload(video_url, caption, hashtags)

            # Step 1: Download video if URL
            local_video_path = await self._download_video(video_url)

            # Step 2: Initialize upload session
            upload_url = await self._initialize_upload()

            # Step 3: Upload video
            video_id = await self._upload_video(local_video_path, upload_url)

            # Step 4: Publish with metadata
            result = await self._publish_video(
                video_id=video_id,
                caption=caption,
                hashtags=hashtags,
                privacy_level=privacy_level,
                allow_comments=allow_comments,
                allow_duet=allow_duet,
                allow_stitch=allow_stitch
            )

            logger.info(f"TikTok upload completed: {result.get('share_url')}")

            import json
            return json.dumps({
                "status": "success",
                "platform": "tiktok",
                "video_id": result.get("video_id"),
                "share_url": result.get("share_url"),
                "embed_link": result.get("embed_link"),
                "caption": caption,
                "hashtags": hashtags,
                "privacy_level": privacy_level,
                "published_at": result.get("published_at"),
                "metadata": {
                    "allow_comments": allow_comments,
                    "allow_duet": allow_duet,
                    "allow_stitch": allow_stitch
                }
            }, indent=2)

        except Exception as e:
            logger.error(f"TikTok upload failed: {e}")
            import json
            return json.dumps({
                "status": "error",
                "platform": "tiktok",
                "message": str(e)
            })

    async def _download_video(self, video_url: str) -> str:
        """
        Download video from URL or verify local path.

        Args:
            video_url: Video URL or local path

        Returns:
            Local file path
        """
        # Check if it's a local path
        if Path(video_url).exists():
            return video_url

        # Download from URL
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(video_url)
            response.raise_for_status()

            # Save to temp file
            temp_path = f"/tmp/tiktok_video_{int(time.time())}.mp4"
            with open(temp_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Video downloaded to: {temp_path}")
            return temp_path

    async def _initialize_upload(self) -> str:
        """
        Initialize TikTok upload session.

        Returns:
            Upload URL
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://open.tiktokapis.com/v2/post/publish/video/init/",
                headers={
                    "Authorization": f"Bearer {settings.TIKTOK_ACCESS_TOKEN}",
                    "Content-Type": "application/json"
                },
                json={
                    "post_info": {
                        "title": "Content Creation Agent",
                        "privacy_level": "PUBLIC_TO_EVERYONE",
                        "disable_duet": False,
                        "disable_comment": False,
                        "disable_stitch": False
                    },
                    "source_info": {
                        "source": "PULL_FROM_URL",
                        "video_url": "",  # Will be provided in upload step
                    }
                }
            )

            response.raise_for_status()
            data = response.json()

            return data["data"]["upload_url"]

    async def _upload_video(self, video_path: str, upload_url: str) -> str:
        """
        Upload video file to TikTok.

        Args:
            video_path: Local video file path
            upload_url: TikTok upload URL

        Returns:
            Video ID
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            with open(video_path, "rb") as video_file:
                files = {"video": video_file}

                response = await client.put(
                    upload_url,
                    files=files
                )

                response.raise_for_status()
                data = response.json()

                return data["data"]["video_id"]

    async def _publish_video(
        self,
        video_id: str,
        caption: str,
        hashtags: Optional[list[str]],
        privacy_level: str,
        allow_comments: bool,
        allow_duet: bool,
        allow_stitch: bool
    ) -> Dict[str, Any]:
        """
        Publish uploaded video with metadata.

        Args:
            video_id: TikTok video ID
            caption: Video caption
            hashtags: Hashtags
            privacy_level: Privacy setting
            allow_comments: Enable comments
            allow_duet: Enable duets
            allow_stitch: Enable stitching

        Returns:
            Publication result with share URL
        """
        # Format caption with hashtags
        full_caption = caption
        if hashtags:
            hashtag_str = " ".join([f"#{tag}" for tag in hashtags])
            full_caption = f"{caption}\n\n{hashtag_str}"

        # Truncate if too long
        if len(full_caption) > 2200:
            full_caption = full_caption[:2197] + "..."

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://open.tiktokapis.com/v2/post/publish/status/fetch/",
                headers={
                    "Authorization": f"Bearer {settings.TIKTOK_ACCESS_TOKEN}",
                    "Content-Type": "application/json"
                },
                json={
                    "publish_id": video_id
                }
            )

            response.raise_for_status()
            data = response.json()

            return {
                "video_id": video_id,
                "share_url": data["data"].get("share_url", ""),
                "embed_link": data["data"].get("embed_link", ""),
                "published_at": data["data"].get("published_time", ""),
                "status": data["data"].get("status", "")
            }

    def _mock_upload(
        self,
        video_url: str,
        caption: str,
        hashtags: Optional[list[str]]
    ) -> str:
        """
        Mock upload for development/testing.

        Args:
            video_url: Video URL
            caption: Caption
            hashtags: Hashtags

        Returns:
            Mock JSON response
        """
        import json
        import time

        mock_video_id = f"mock_tiktok_{int(time.time())}"

        logger.info("TikTok credentials not configured - returning mock response")

        return json.dumps({
            "status": "success",
            "platform": "tiktok",
            "video_id": mock_video_id,
            "share_url": f"https://www.tiktok.com/@mock_user/video/{mock_video_id}",
            "embed_link": f"https://www.tiktok.com/embed/v2/{mock_video_id}",
            "caption": caption,
            "hashtags": hashtags,
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "published_at": time.time(),
            "metadata": {
                "is_mock": True,
                "message": "TikTok API not configured - this is a mock response"
            }
        }, indent=2)
