"""
YouTubeShortsAgent Node

Formats and publishes content to YouTube Shorts.
Receives asset pack from ContentCreationAgent and uploads via YouTubeShortsUploadTool.

Architecture Compliance:
- LangGraph node (async function)
- Reads from VideoWorkflowState
- Returns state updates (Dict[str, Any])
- Parallel execution with TikTokAgent
"""

from typing import Dict, Any
import logging
import json

from backend.state.state_schema import VideoWorkflowState, update_workflow_phase
from backend.tools import ToolRegistry

logger = logging.getLogger(__name__)


async def youtube_shorts_node(state: VideoWorkflowState) -> Dict[str, Any]:
    """
    YouTubeShortsAgent - Format and upload to YouTube Shorts.

    Workflow:
    1. Get asset pack from ContentCreationAgent
    2. Generate metadata (title, description, tags)
    3. Upload via YouTubeShortsUploadTool
    4. Return URL + metrics

    Args:
        state: Current workflow state

    Returns:
        Dict with state updates including:
        - publish_results.youtube_shorts
        - youtube_video_path (same as video_path, already formatted)
    """
    try:
        logger.info(f"YouTubeShortsAgent started for workflow: {state.get('workflow_id')}")

        # Check if YouTube Shorts is in target platforms
        target_platforms = state.get("target_platforms", [])
        if "youtube_shorts" not in target_platforms:
            logger.info("YouTube Shorts not in target platforms, skipping")
            return {
                "current_agent": "youtube_shorts",
                "workflow_status": "running"
            }

        # Get tool
        tools = ToolRegistry.get_youtube_tools()
        youtube_upload_tool = tools[0]  # YouTubeShortsUploadTool

        # Get asset pack
        asset_pack = state.get("asset_pack", {})
        video_url = asset_pack.get("video_url") or state.get("video_path", "")
        script = asset_pack.get("script") or state.get("script", "")
        trend_topic = asset_pack.get("trend_topic") or state.get("trend_topic", "")

        if not video_url:
            raise ValueError("No video URL found in asset pack")

        # Generate metadata for YouTube
        title, description, tags = _generate_youtube_metadata(
            script,
            trend_topic,
            state.get("parsed_intent", {})
        )

        logger.info(
            f"YouTube Shorts upload starting: title='{title[:50]}...', "
            f"{len(tags)} tags"
        )

        # Upload to YouTube Shorts
        result = await youtube_upload_tool._arun(
            video_url=video_url,
            title=title,
            description=description,
            tags=tags,
            category_id="22",  # People & Blogs
            privacy_status="public",
            made_for_kids=False
        )

        result_data = json.loads(result)

        if result_data.get("status") == "success":
            youtube_result = {
                "status": "success",
                "platform": "youtube_shorts",
                "video_id": result_data.get("video_id"),
                "url": result_data.get("video_url"),
                "watch_url": result_data.get("watch_url"),
                "title": title,
                "description": description,
                "tags": tags,
                "published_at": result_data.get("published_at"),
                "metadata": result_data.get("metadata", {})
            }

            logger.info(f"YouTube Shorts upload successful: {youtube_result.get('url')}")

            # Update publish_results
            publish_results = state.get("publish_results", {})
            publish_results["youtube_shorts"] = youtube_result

            return {
                "current_agent": "youtube_shorts",
                "youtube_video_path": video_url,
                "publish_results": publish_results
            }

        else:
            error_msg = result_data.get("message", "Unknown error")
            logger.error(f"YouTube Shorts upload failed: {error_msg}")

            publish_results = state.get("publish_results", {})
            publish_results["youtube_shorts"] = {
                "status": "failed",
                "platform": "youtube_shorts",
                "error": error_msg
            }

            return {
                "current_agent": "youtube_shorts",
                "publish_results": publish_results,
                "error_message": f"YouTube Shorts upload failed: {error_msg}"
            }

    except Exception as e:
        logger.error(f"YouTubeShortsAgent failed: {e}", exc_info=True)

        publish_results = state.get("publish_results", {})
        publish_results["youtube_shorts"] = {
            "status": "failed",
            "platform": "youtube_shorts",
            "error": str(e)
        }

        return {
            "current_agent": "youtube_shorts",
            "publish_results": publish_results,
            "error_message": f"YouTube Shorts agent error: {str(e)}"
        }


def _generate_youtube_metadata(
    script: str,
    trend_topic: str,
    parsed_intent: Dict[str, Any]
) -> tuple[str, str, list[str]]:
    """
    Generate title, description, and tags for YouTube Shorts.

    YouTube best practices:
    - Title: 60-70 characters (max 100)
    - Description: 200-300 characters (max 5000)
    - Tags: 5-8 relevant tags
    - Include #Shorts

    Args:
        script: Video script
        trend_topic: Trending topic
        parsed_intent: Parsed user intent

    Returns:
        Tuple of (title, description, tags)
    """
    # Generate title
    if trend_topic:
        title = trend_topic
    else:
        # Use first sentence of script
        title = script.split('.')[0] if '.' in script else script[:60]

    # Add emoji based on topic
    topic = parsed_intent.get("topic", "General")
    emoji_map = {
        "AI and Technology": "🤖",
        "Business and Entrepreneurship": "💼",
        "Health and Fitness": "💪",
        "Food and Cooking": "🍳",
        "Travel": "✈️",
        "General": "✨"
    }
    emoji = emoji_map.get(topic, "✨")

    title = f"{emoji} {title}"

    # Truncate title if too long
    if len(title) > 70:
        title = title[:67] + "..."

    # Generate description
    # First paragraph of script
    description_text = script.split('\n\n')[0] if '\n\n' in script else script[:300]

    # Add call-to-action and #Shorts
    description_text += "\n\n👍 Like and Subscribe for more!\n\n#Shorts"

    # Add topic tags
    topic_tags = {
        "AI and Technology": ["AI", "Technology", "Tech", "Innovation"],
        "Business and Entrepreneurship": ["Business", "Entrepreneur", "Startup", "Success"],
        "Health and Fitness": ["Fitness", "Health", "Workout", "Wellness"],
        "Food and Cooking": ["Food", "Cooking", "Recipe", "Foodie"],
        "Travel": ["Travel", "Adventure", "Explore", "Wanderlust"],
        "General": ["Trending", "Viral", "Shorts"]
    }

    description_tags = topic_tags.get(topic, ["Trending"])[:3]
    description_text += " " + " ".join([f"#{tag}" for tag in description_tags])

    # Truncate description if too long
    if len(description_text) > 400:
        description_text = description_text[:397] + "..."

    # Generate tags (YouTube tags, not hashtags)
    tags = []

    # Add topic-based tags
    tags.extend(topic_tags.get(topic, ["Trending"])[:3])

    # Add platform tags
    tags.extend(["Shorts", "Short Video", "YouTube Shorts"])

    # Add trend tag
    if trend_topic:
        tags.append(trend_topic)

    # Limit to 8 tags
    tags = tags[:8]

    return title, description_text, tags
