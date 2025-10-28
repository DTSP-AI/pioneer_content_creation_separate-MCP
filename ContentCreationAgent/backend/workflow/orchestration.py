"""
Platform Requirements Module

Provides platform-specific requirements for content creation.
Tool selection is handled by MCP server automatically.
This module only validates platform compatibility.

Architecture Compliance:
- LangGraph handles orchestration (graph.py)
- MCP server handles tool selection automatically
- This module only provides platform requirement validation
"""

from typing import Dict, Tuple, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ContentType(str, Enum):
    """Supported content types"""
    VIDEO = "video"
    IMAGE = "image"
    AUDIO = "audio"
    TEXT = "text"


class WorkflowStage(str, Enum):
    """Workflow execution stages"""
    STRATEGY = "strategy"  # Supervisor analyzes intent
    CREATION = "creation"  # Content agent generates content
    REFINEMENT = "refinement"  # Platform-specific optimization
    DELIVERY = "delivery"  # Upload and tracking


class Priority(str, Enum):
    """Content generation priorities"""
    QUALITY = "quality"  # Best quality, longer generation time
    BALANCED = "balanced"  # Balance quality and speed
    SPEED = "speed"  # Fastest generation, acceptable quality


class Platform(str, Enum):
    """Supported platforms"""
    TIKTOK = "tiktok"
    YOUTUBE_SHORTS = "youtube_shorts"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"


# Import platform requirements from config
from backend.config import VIDEO_MODEL_SPECS, PLATFORM_REQUIREMENTS


class ContentOrchestrator:
    """
    Platform Requirements Validator

    Simplified orchestration layer that validates platform compatibility.
    Tool selection is delegated to MCP server which automatically
    routes to optimal providers based on requirements.

    This class only validates that platform requirements are met.
    """

    @staticmethod
    def select_video_tool(
        platform: str,
        priority: Priority = Priority.BALANCED,
        duration_seconds: int = 5,
        aspect_ratio: Optional[str] = None
    ) -> Tuple[str, Dict]:
        """
        Validate video tool selection for platform.

        Delegates tool selection to MCP server's unified tools.
        This function validates platform requirements only.

        Args:
            platform: Target platform (tiktok, youtube, etc.)
            priority: Quality vs speed preference (passed through)
            duration_seconds: Desired video duration
            aspect_ratio: Desired aspect ratio (9:16, 16:9, 1:1)

        Returns:
            Tuple of (tool_name, reasoning_dict)
            Always returns "generate_video_unified" - MCP routes to best provider
        """
        # Validate platform requirements
        requirements = ContentOrchestrator.get_platform_requirements(platform)

        # Check duration compatibility
        max_duration = requirements.get("max_duration", 60)
        if duration_seconds > max_duration:
            logger.warning(
                f"Requested duration {duration_seconds}s exceeds platform max {max_duration}s"
            )

        # Return unified tool - MCP auto-selects best provider
        return "generate_video_unified", {
            "selected_model": "generate_video_unified",
            "platform": platform,
            "priority": priority.value,
            "duration_seconds": duration_seconds,
            "aspect_ratio": aspect_ratio,
            "reason": "MCP server will auto-route to optimal provider (hailuo, wan, luma)"
        }

    @staticmethod
    def select_image_tool(
        purpose: str = "general",
        priority: Priority = Priority.BALANCED
    ) -> Tuple[str, Dict]:
        """
        Validate image tool selection.

        Args:
            purpose: Image purpose (thumbnail, post, logo, etc.)
            priority: Quality vs speed preference

        Returns:
            Tuple of (tool_name, reasoning_dict)
            Always returns "process_image_unified" - unified image tool
        """
        return "process_image_unified", {
            "selected_model": "process_image_unified",
            "purpose": purpose,
            "priority": priority.value,
            "reason": "Unified image tool handles all 9 task types"
        }

    @staticmethod
    def get_tool_chain(
        content_type: ContentType,
        platform: str,
        priority: Priority = Priority.BALANCED,
        **kwargs
    ) -> Dict:
        """
        Get simplified tool chain for content creation workflow.

        Returns basic tool chain - detailed execution handled by LangGraph.

        Args:
            content_type: Type of content to create
            platform: Target platform
            priority: Quality vs speed preference
            **kwargs: Additional parameters

        Returns:
            Dict with tool chain metadata
        """
        tool_chain = {
            "content_type": content_type.value,
            "platform": platform,
            "priority": priority.value,
            "stages": []
        }

        if content_type == ContentType.VIDEO:
            tool_chain["stages"] = [
                {"stage": "trend_research", "tool": "google_sheets_trends"},
                {"stage": "script_generation", "tool": "video_script_generator"},
                {"stage": "video_generation", "tool": "generate_video_unified"}
            ]
        elif content_type == ContentType.IMAGE:
            tool_chain["stages"] = [
                {"stage": "image_generation", "tool": "process_image_unified"}
            ]
        elif content_type == ContentType.AUDIO:
            tool_chain["stages"] = [
                {"stage": "audio_generation", "tool": "generate_audio_unified"}
            ]

        return tool_chain

    @staticmethod
    def get_platform_requirements(platform: str) -> Dict:
        """
        Get platform-specific content requirements

        Args:
            platform: Platform name

        Returns:
            Dict with platform requirements
        """
        requirements = {
            Platform.TIKTOK.value: {
                "video_aspect_ratio": "9:16",
                "max_duration": 60,
                "optimal_duration": "15-30",
                "caption_required": True,
                "hashtags_recommended": 5,
                "preferred_style": "trendy, fast-paced"
            },
            Platform.YOUTUBE_SHORTS.value: {
                "video_aspect_ratio": "9:16",
                "max_duration": 60,
                "optimal_duration": "30-60",
                "caption_optional": True,
                "hashtags_recommended": 3,
                "preferred_style": "engaging, informative"
            },
            Platform.YOUTUBE.value: {
                "video_aspect_ratio": "16:9",
                "max_duration": 3600,
                "optimal_duration": "8-15 minutes",
                "caption_optional": True,
                "hashtags_recommended": 5,
                "preferred_style": "cinematic, professional"
            },
            Platform.INSTAGRAM.value: {
                "video_aspect_ratio": "1:1 or 9:16",
                "max_duration": 90,
                "optimal_duration": "15-30",
                "caption_required": True,
                "hashtags_recommended": 10,
                "preferred_style": "aesthetic, visual"
            }
        }

        return requirements.get(platform.lower(), {
            "video_aspect_ratio": "16:9",
            "max_duration": 60,
            "optimal_duration": "30",
            "caption_optional": True,
            "hashtags_recommended": 3,
            "preferred_style": "engaging"
        })
