"""
TikTokAgent Node

Formats and publishes content to TikTok.
Receives asset pack from ContentCreationAgent and uploads via TikTokUploadTool.

Architecture Compliance:
- LangGraph node (async function)
- Reads from VideoWorkflowState
- Returns state updates (Dict[str, Any])
- Parallel execution with YouTubeShortsAgent
"""

from typing import Dict, Any
import logging
import json

from backend.state.state_schema import VideoWorkflowState, update_workflow_phase
from backend.tools import ToolRegistry

logger = logging.getLogger(__name__)


async def tiktok_node(state: VideoWorkflowState) -> Dict[str, Any]:
    """
    TikTokAgent - Format and upload to TikTok.

    Workflow:
    1. Get asset pack from ContentCreationAgent
    2. Format metadata (caption + hashtags)
    3. Upload via TikTokUploadTool
    4. Return URL + metrics

    Args:
        state: Current workflow state

    Returns:
        Dict with state updates including:
        - publish_results.tiktok
        - tiktok_video_path (same as video_path, already formatted)
    """
    try:
        logger.info(f"TikTokAgent started for workflow: {state.get('workflow_id')}")

        # Check if TikTok is in target platforms
        target_platforms = state.get("target_platforms", [])
        if "tiktok" not in target_platforms:
            logger.info("TikTok not in target platforms, skipping")
            return {
                "current_agent": "tiktok",
                "workflow_status": "running"
            }

        # Get tool
        tools = ToolRegistry.get_tiktok_tools()
        tiktok_upload_tool = tools[0]  # TikTokUploadTool

        # Get asset pack
        asset_pack = state.get("asset_pack", {})
        video_url = asset_pack.get("video_url") or state.get("video_path", "")
        script = asset_pack.get("script") or state.get("script", "")
        trend_topic = asset_pack.get("trend_topic") or state.get("trend_topic", "")

        if not video_url:
            raise ValueError("No video URL found in asset pack")

        # Format metadata for TikTok
        caption, hashtags = _format_tiktok_metadata(
            script,
            trend_topic,
            state.get("parsed_intent", {})
        )

        logger.info(f"TikTok upload starting: {len(caption)} char caption, {len(hashtags)} hashtags")

        # Upload to TikTok
        result = await tiktok_upload_tool._arun(
            video_url=video_url,
            caption=caption,
            hashtags=hashtags,
            privacy_level="PUBLIC_TO_EVERYONE",
            allow_comments=True,
            allow_duet=True,
            allow_stitch=True
        )

        result_data = json.loads(result)

        if result_data.get("status") == "success":
            tiktok_result = {
                "status": "success",
                "platform": "tiktok",
                "video_id": result_data.get("video_id"),
                "url": result_data.get("share_url"),
                "embed_link": result_data.get("embed_link"),
                "caption": caption,
                "hashtags": hashtags,
                "published_at": result_data.get("published_at"),
                "metadata": result_data.get("metadata", {})
            }

            logger.info(f"TikTok upload successful: {tiktok_result.get('url')}")

            # Update publish_results
            publish_results = state.get("publish_results", {})
            publish_results["tiktok"] = tiktok_result

            return {
                "current_agent": "tiktok",
                "tiktok_video_path": video_url,
                "publish_results": publish_results
            }

        else:
            error_msg = result_data.get("message", "Unknown error")
            logger.error(f"TikTok upload failed: {error_msg}")

            publish_results = state.get("publish_results", {})
            publish_results["tiktok"] = {
                "status": "failed",
                "platform": "tiktok",
                "error": error_msg
            }

            return {
                "current_agent": "tiktok",
                "publish_results": publish_results,
                "error_message": f"TikTok upload failed: {error_msg}"
            }

    except Exception as e:
        logger.error(f"TikTokAgent failed: {e}", exc_info=True)

        publish_results = state.get("publish_results", {})
        publish_results["tiktok"] = {
            "status": "failed",
            "platform": "tiktok",
            "error": str(e)
        }

        return {
            "current_agent": "tiktok",
            "publish_results": publish_results,
            "error_message": f"TikTok agent error: {str(e)}"
        }


def _format_tiktok_metadata(
    script: str,
    trend_topic: str,
    parsed_intent: Dict[str, Any]
) -> tuple[str, list[str]]:
    """
    Format caption and hashtags for TikTok.

    TikTok best practices:
    - Caption: 150-300 characters (max 2200)
    - Hashtags: 3-5 relevant tags
    - Include trending tags
    - Call-to-action

    Args:
        script: Video script
        trend_topic: Trending topic
        parsed_intent: Parsed user intent

    Returns:
        Tuple of (caption, hashtags)
    """
    # Extract first sentence or first 200 chars for caption
    caption_text = script.split('.')[0] if '.' in script else script[:200]

    # Add call-to-action
    caption_text += "\n\n👉 Follow for more!"

    # Generate hashtags
    hashtags = []

    # Add topic-based tags
    topic = parsed_intent.get("topic", "General")
    topic_tags = {
        "AI and Technology": ["ai", "tech", "technology", "innovation"],
        "Business and Entrepreneurship": ["business", "entrepreneur", "startup", "success"],
        "Health and Fitness": ["fitness", "health", "workout", "wellness"],
        "Food and Cooking": ["food", "cooking", "recipe", "foodie"],
        "Travel": ["travel", "adventure", "explore", "wanderlust"],
        "General": ["trending", "viral", "fyp"]
    }

    hashtags.extend(topic_tags.get(topic, ["trending"])[:2])

    # Add platform tags
    hashtags.extend(["tiktok", "viral", "fyp"])

    # Add trend-related tag (if applicable)
    if trend_topic and len(trend_topic.split()) <= 2:
        trend_tag = trend_topic.lower().replace(" ", "")
        if len(trend_tag) < 20:
            hashtags.append(trend_tag)

    # Limit to 5 hashtags
    hashtags = hashtags[:5]

    # Ensure caption isn't too long
    if len(caption_text) > 300:
        caption_text = caption_text[:297] + "..."

    return caption_text, hashtags
