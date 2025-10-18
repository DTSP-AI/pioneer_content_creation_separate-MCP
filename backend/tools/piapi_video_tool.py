"""
PiAPI.ai Video Generation Tool

Comprehensive AI video generation using PiAPI.ai.
This tool replaces multiple separate tools (TTS, video rendering, caption generation)
with a single unified AI video generation pipeline.

PiAPI.ai Capabilities:
- Text-to-Video generation
- Script-to-Video with AI voiceover
- Automatic caption generation
- Multi-model support (Runway, Pika, Kling, Minimax, etc.)
- Platform-specific formatting (TikTok, YouTube Shorts)

Architecture:
This single tool replaces:
- TextToSpeechTool (handled by PiAPI)
- VideoRenderTool (handled by PiAPI)
- CaptionFormatterTool (handled by PiAPI)
"""

from typing import Optional, Type, Dict, Any
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
import logging
import httpx
import asyncio
import time

from backend.config import get_settings, COST_PER_PIAPI_VIDEO

logger = logging.getLogger(__name__)
settings = get_settings()


class PiAPIVideoInput(BaseModel):
    """Input schema for PiAPI.ai video generation."""

    script: str = Field(
        description="Video script text (will be converted to speech and video)"
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
    Generate complete AI videos using PiAPI.ai.

    This tool handles the entire video creation pipeline:
    1. Script input
    2. AI voiceover generation
    3. AI video generation from script/prompt
    4. Automatic caption generation
    5. Platform-specific formatting (9:16 for vertical)

    Supports multiple AI video models via PiAPI.ai:
    - Runway Gen-3
    - Pika 1.5
    - Kling AI
    - Minimax Video-01
    - And more
    """

    name = "piapi_video_generator"
    description = """
    Generate a complete AI video from a script using PiAPI.ai.

    Input: script text, platform, duration, style
    Output: Video URL with voiceover, visuals, and captions

    This tool handles ALL video creation steps:
    - Text-to-speech voiceover
    - AI video generation
    - Caption generation
    - Platform-specific formatting

    Use this instead of separate TTS/video/caption tools.
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
        """Sync execution (not used)."""
        import asyncio
        return asyncio.run(self._arun(
            script, topic, platform, duration_seconds,
            style, include_captions, voice_gender
        ))

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
        """
        Async execution - generate video with PiAPI.ai.

        Args:
            script: Video script text
            topic: Optional video topic
            platform: Target platform
            duration_seconds: Video length
            style: Visual style
            include_captions: Generate captions
            voice_gender: Voice gender

        Returns:
            JSON string with video URL and metadata
        """
        try:
            logger.info(f"Starting PiAPI.ai video generation for: {topic or 'video'}")

            # Step 1: Submit video generation request
            task_id = await self._submit_video_request(
                script=script,
                topic=topic,
                platform=platform,
                duration_seconds=duration_seconds,
                style=style,
                voice_gender=voice_gender
            )

            logger.info(f"PiAPI.ai task submitted: {task_id}")

            # Step 2: Poll for completion
            video_result = await self._poll_video_status(task_id)

            # Step 3: Generate captions if requested
            captions = None
            if include_captions and video_result.get("video_url"):
                captions = await self._generate_captions(script)

            # Step 4: Calculate cost
            cost_usd = COST_PER_PIAPI_VIDEO

            logger.info(f"PiAPI.ai video generation completed: {video_result.get('video_url')}")

            import json
            return json.dumps({
                "status": "success",
                "video_url": video_result.get("video_url"),
                "video_path": None,  # Download URL, not local path yet
                "duration_seconds": video_result.get("duration", duration_seconds),
                "script": script,
                "captions": captions,
                "platform": platform,
                "style": style,
                "task_id": task_id,
                "cost_usd": cost_usd,
                "metadata": {
                    "model": video_result.get("model", "unknown"),
                    "resolution": "1080x1920" if platform in ["tiktok", "youtube_shorts"] else "1920x1080",
                    "aspect_ratio": "9:16",
                    "has_voiceover": True,
                    "has_captions": include_captions
                }
            }, indent=2)

        except Exception as e:
            logger.error(f"PiAPI.ai video generation failed: {e}")
            import json
            return json.dumps({
                "status": "error",
                "message": str(e),
                "video_url": None
            })

    async def _submit_video_request(
        self,
        script: str,
        topic: Optional[str],
        platform: str,
        duration_seconds: int,
        style: str,
        voice_gender: str
    ) -> str:
        """
        Submit video generation request to PiAPI.ai.

        Returns:
            task_id: Task identifier for polling
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Build video generation prompt
            video_prompt = self._build_video_prompt(script, topic, style)

            # Determine aspect ratio
            aspect_ratio = "9:16" if platform in ["tiktok", "youtube_shorts"] else "16:9"

            # PiAPI.ai API endpoint (example - adjust based on actual API)
            # See: https://piapi.ai/docs
            response = await client.post(
                f"{settings.PIAPI_BASE_URL}/video/generate",
                headers={
                    "Authorization": f"Bearer {settings.PIAPI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": video_prompt,
                    "script": script,
                    "duration": duration_seconds,
                    "aspect_ratio": aspect_ratio,
                    "style": style,
                    "voice": {
                        "enabled": True,
                        "gender": voice_gender,
                        "language": "en-US"
                    },
                    "model": "auto",  # Let PiAPI choose best model
                    "quality": "high"
                }
            )

            response.raise_for_status()
            data = response.json()

            return data.get("task_id") or data.get("id")

    async def _poll_video_status(
        self,
        task_id: str,
        max_wait_seconds: int = 300,
        poll_interval: int = 10
    ) -> Dict[str, Any]:
        """
        Poll PiAPI.ai for video generation completion.

        Args:
            task_id: Task identifier
            max_wait_seconds: Maximum time to wait
            poll_interval: Seconds between polls

        Returns:
            Dict with video URL and metadata
        """
        start_time = time.time()

        async with httpx.AsyncClient(timeout=30.0) as client:
            while (time.time() - start_time) < max_wait_seconds:
                # Check task status
                response = await client.get(
                    f"{settings.PIAPI_BASE_URL}/video/task/{task_id}",
                    headers={
                        "Authorization": f"Bearer {settings.PIAPI_API_KEY}"
                    }
                )

                response.raise_for_status()
                data = response.json()

                status = data.get("status")

                if status == "completed":
                    logger.info(f"PiAPI.ai video generation completed: {task_id}")
                    return {
                        "video_url": data.get("video_url") or data.get("result_url"),
                        "duration": data.get("duration"),
                        "model": data.get("model"),
                        "metadata": data.get("metadata", {})
                    }

                elif status in ["failed", "error"]:
                    error_msg = data.get("error", "Unknown error")
                    raise Exception(f"PiAPI.ai generation failed: {error_msg}")

                # Still processing
                logger.debug(f"PiAPI.ai task {task_id} status: {status}")
                await asyncio.sleep(poll_interval)

            raise TimeoutError(f"PiAPI.ai video generation timed out after {max_wait_seconds}s")

    async def _generate_captions(self, script: str) -> str:
        """
        Generate formatted captions from script.

        PiAPI.ai can do this automatically, but we can also format manually.

        Args:
            script: Video script

        Returns:
            Formatted caption text
        """
        # Simple caption formatting
        # PiAPI.ai may already include this in the video

        # Split into sentences
        sentences = script.replace(".", ".\n").replace("!", "!\n").replace("?", "?\n")
        sentences = [s.strip() for s in sentences.split("\n") if s.strip()]

        # Format as captions (max 40 chars per line)
        captions = []
        for sentence in sentences:
            words = sentence.split()
            line = ""
            for word in words:
                if len(line + " " + word) <= 40:
                    line += " " + word if line else word
                else:
                    if line:
                        captions.append(line)
                    line = word
            if line:
                captions.append(line)

        return "\n".join(captions)

    def _build_video_prompt(
        self,
        script: str,
        topic: Optional[str],
        style: str
    ) -> str:
        """
        Build visual prompt for AI video generation.

        Args:
            script: Video script
            topic: Video topic
            style: Visual style

        Returns:
            Optimized prompt for PiAPI.ai
        """
        base_prompt = f"Create a {style} video"

        if topic:
            base_prompt += f" about {topic}"

        base_prompt += f". {script[:200]}"  # First 200 chars of script

        # Add style modifiers
        style_modifiers = {
            "realistic": "photorealistic, high quality, professional",
            "anime": "anime style, vibrant colors, expressive",
            "cartoon": "cartoon style, bright, playful",
            "cinematic": "cinematic, dramatic lighting, film quality"
        }

        modifier = style_modifiers.get(style, "")
        if modifier:
            base_prompt += f". Style: {modifier}"

        return base_prompt


# Optional: Fallback tools if PiAPI is not available
# These can be used as backup in ContentCreationAgent

class SimpleTTSTool(BaseTool):
    """Simplified TTS tool using ElevenLabs (fallback)."""
    name = "simple_tts"
    description = "Generate audio from text using ElevenLabs (fallback)"

    def _run(self, text: str) -> str:
        return "Fallback TTS not implemented - use PiAPI.ai"

    async def _arun(self, text: str) -> str:
        return "Fallback TTS not implemented - use PiAPI.ai"
