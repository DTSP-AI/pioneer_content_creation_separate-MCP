"""
YouTube Shorts Upload Tool

Uploads videos to YouTube Shorts using the YouTube Data API v3.
Used by YouTubeShortsAgent for final content distribution.

API Documentation: https://developers.google.com/youtube/v3/docs/videos/insert
"""

from typing import Optional, Type, Dict, Any
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
import logging
import httpx
from pathlib import Path
import time

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class YouTubeShortsUploadInput(BaseModel):
    """Input schema for YouTube Shorts upload."""

    video_url: str = Field(
        description="URL or local path to video file to upload"
    )

    title: str = Field(
        description="Video title (max 100 characters)"
    )

    description: str = Field(
        description="Video description (max 5000 characters)"
    )

    tags: Optional[list[str]] = Field(
        default=None,
        description="List of video tags (max 500 characters total)"
    )

    category_id: str = Field(
        default="22",
        description="YouTube category ID (22=People & Blogs, 24=Entertainment)"
    )

    privacy_status: str = Field(
        default="public",
        description="Privacy: public, private, or unlisted"
    )

    made_for_kids: bool = Field(
        default=False,
        description="Whether video is made for kids"
    )


class YouTubeShortsUploadTool(BaseTool):
    """
    Upload videos to YouTube Shorts.

    Uses YouTube Data API v3 with OAuth2 authentication.
    Automatically marks videos as #Shorts for YouTube Shorts feed.

    Flow:
    1. Authenticate with OAuth2
    2. Download video (if URL)
    3. Upload video file
    4. Set metadata (title, description, tags)
    5. Publish and return YouTube URL
    """

    name: str = "youtube_shorts_upload"
    description: str = """
    Upload a video to YouTube Shorts with metadata.

    Input: video URL/path, title, description, tags, privacy settings
    Output: Published YouTube Shorts URL and video ID

    Automatically adds #Shorts to description for YouTube Shorts discovery.
    Handles OAuth2 authentication and video upload workflow.
    """
    args_schema: Type[BaseModel] = YouTubeShortsUploadInput

    def _run(
        self,
        video_url: str,
        title: str,
        description: str,
        tags: Optional[list[str]] = None,
        category_id: str = "22",
        privacy_status: str = "public",
        made_for_kids: bool = False
    ) -> str:
        """Sync execution (not used)."""
        import asyncio
        return asyncio.run(self._arun(
            video_url, title, description, tags,
            category_id, privacy_status, made_for_kids
        ))

    async def _arun(
        self,
        video_url: str,
        title: str,
        description: str,
        tags: Optional[list[str]] = None,
        category_id: str = "22",
        privacy_status: str = "public",
        made_for_kids: bool = False
    ) -> str:
        """
        Async execution - upload to YouTube Shorts.

        Args:
            video_url: Video URL or local path
            title: Video title
            description: Video description
            tags: Optional tags
            category_id: YouTube category
            privacy_status: Privacy setting
            made_for_kids: Kids content flag

        Returns:
            JSON string with YouTube Shorts URL and metadata
        """
        try:
            logger.info(f"Starting YouTube Shorts upload: {title}")

            # Check if credentials configured
            if not settings.YOUTUBE_CLIENT_ID:
                logger.warning("YouTube credentials not configured - using mock upload")
                return self._mock_upload(video_url, title, description, tags)

            # Step 1: Authenticate
            youtube_service = await self._authenticate()

            # Step 2: Download video if URL
            local_video_path = await self._download_video(video_url)

            # Step 3: Prepare metadata
            metadata = self._prepare_metadata(
                title=title,
                description=description,
                tags=tags,
                category_id=category_id,
                privacy_status=privacy_status,
                made_for_kids=made_for_kids
            )

            # Step 4: Upload video
            result = await self._upload_video(
                youtube_service=youtube_service,
                video_path=local_video_path,
                metadata=metadata
            )

            logger.info(f"YouTube Shorts upload completed: {result.get('video_url')}")

            import json
            return json.dumps({
                "status": "success",
                "platform": "youtube_shorts",
                "video_id": result.get("video_id"),
                "video_url": result.get("video_url"),
                "watch_url": result.get("watch_url"),
                "title": title,
                "description": description,
                "tags": tags,
                "privacy_status": privacy_status,
                "published_at": result.get("published_at"),
                "metadata": {
                    "category_id": category_id,
                    "made_for_kids": made_for_kids,
                    "is_short": True
                }
            }, indent=2)

        except Exception as e:
            logger.error(f"YouTube Shorts upload failed: {e}")
            import json
            return json.dumps({
                "status": "error",
                "platform": "youtube_shorts",
                "message": str(e)
            })

    async def _authenticate(self):
        """
        Authenticate with YouTube API using OAuth2.

        Returns:
            YouTube service object
        """
        # Load credentials
        creds = None

        # Check if refresh token exists
        if settings.YOUTUBE_REFRESH_TOKEN:
            creds = Credentials(
                token=None,
                refresh_token=settings.YOUTUBE_REFRESH_TOKEN,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.YOUTUBE_CLIENT_ID,
                client_secret=settings.YOUTUBE_CLIENT_SECRET
            )

            # Refresh token if expired
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())

        if not creds:
            raise ValueError(
                "YouTube authentication failed. Please configure YOUTUBE_REFRESH_TOKEN. "
                "See: https://developers.google.com/youtube/v3/guides/authentication"
            )

        # Build YouTube service
        youtube = build("youtube", "v3", credentials=creds)

        return youtube

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
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(video_url)
            response.raise_for_status()

            # Save to temp file
            temp_path = f"/tmp/youtube_video_{int(time.time())}.mp4"
            with open(temp_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Video downloaded to: {temp_path}")
            return temp_path

    def _prepare_metadata(
        self,
        title: str,
        description: str,
        tags: Optional[list[str]],
        category_id: str,
        privacy_status: str,
        made_for_kids: bool
    ) -> Dict[str, Any]:
        """
        Prepare video metadata for YouTube.

        Args:
            title: Video title
            description: Video description
            tags: Tags
            category_id: Category ID
            privacy_status: Privacy setting
            made_for_kids: Kids content flag

        Returns:
            Metadata dict for YouTube API
        """
        # Ensure #Shorts is in description
        if "#Shorts" not in description and "#shorts" not in description:
            description = f"{description}\n\n#Shorts"

        # Truncate title if too long
        if len(title) > 100:
            title = title[:97] + "..."

        # Truncate description if too long
        if len(description) > 5000:
            description = description[:4997] + "..."

        # Prepare tags
        video_tags = tags or []
        if "Shorts" not in video_tags:
            video_tags.append("Shorts")

        # Build metadata
        return {
            "snippet": {
                "title": title,
                "description": description,
                "tags": video_tags,
                "categoryId": category_id
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": made_for_kids,
                "madeForKids": made_for_kids
            }
        }

    async def _upload_video(
        self,
        youtube_service,
        video_path: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Upload video to YouTube.

        Args:
            youtube_service: YouTube service object
            video_path: Local video path
            metadata: Video metadata

        Returns:
            Upload result with video URL
        """
        # Create media upload
        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024  # 1MB chunks
        )

        # Execute upload
        request = youtube_service.videos().insert(
            part="snippet,status",
            body=metadata,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info(f"Upload progress: {int(status.progress() * 100)}%")

        video_id = response["id"]
        published_at = response["snippet"].get("publishedAt", "")

        return {
            "video_id": video_id,
            "video_url": f"https://www.youtube.com/shorts/{video_id}",
            "watch_url": f"https://www.youtube.com/watch?v={video_id}",
            "published_at": published_at
        }

    def _mock_upload(
        self,
        video_url: str,
        title: str,
        description: str,
        tags: Optional[list[str]]
    ) -> str:
        """
        Mock upload for development/testing.

        Args:
            video_url: Video URL
            title: Title
            description: Description
            tags: Tags

        Returns:
            Mock JSON response
        """
        import json
        import time

        mock_video_id = f"mock_yt_{int(time.time())}"

        logger.info("YouTube credentials not configured - returning mock response")

        return json.dumps({
            "status": "success",
            "platform": "youtube_shorts",
            "video_id": mock_video_id,
            "video_url": f"https://www.youtube.com/shorts/{mock_video_id}",
            "watch_url": f"https://www.youtube.com/watch?v={mock_video_id}",
            "title": title,
            "description": description,
            "tags": tags,
            "privacy_status": "public",
            "published_at": time.time(),
            "metadata": {
                "is_mock": True,
                "message": "YouTube API not configured - this is a mock response"
            }
        }, indent=2)
