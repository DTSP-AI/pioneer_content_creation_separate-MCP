"""
ContentCreationAgent Node

Centralized content creation using:
1. GoogleSheetsTrendsTool - Fetch trending topics
2. VideoScriptGeneratorTool - Generate script (Claude)
3. PiAPIVideoTool - Create complete video with voiceover + captions

Architecture Compliance:
- LangGraph node (async function)
- Reads from VideoWorkflowState
- Returns state updates (Dict[str, Any])
- All API usage centralized here
"""

from typing import Dict, Any
import logging
import json

from backend.state.state_schema import VideoWorkflowState, update_workflow_phase, add_cost_to_workflow
from backend.tools import ToolRegistry
from backend.graph.error_recovery import (
    with_retry,
    with_timeout,
    safe_node_execution,
    STANDARD_RETRY,
    API_ERRORS
)

logger = logging.getLogger(__name__)


@safe_node_execution("content_creation")
async def content_creation_node(state: VideoWorkflowState) -> Dict[str, Any]:
    """
    ContentCreationAgent - Generate all content assets.

    Workflow:
    1. Fetch trending topic (optional, based on user request)
    2. Generate video script (Claude)
    3. Generate complete video (PiAPI.ai)
       - Voiceover
       - Visual generation
       - Captions

    Args:
        state: Current workflow state

    Returns:
        Dict with state updates including:
        - trend_topic
        - script
        - video_path (URL from PiAPI)
        - captions
        - cost_breakdown
    """
    try:
        logger.info(f"ContentCreationAgent started for workflow: {state.get('workflow_id')}")

        # Get tools
        tools = ToolRegistry.get_content_creation_tools()
        google_sheets_tool = tools[0]  # GoogleSheetsTrendsTool
        script_tool = tools[1]          # VideoScriptGeneratorTool
        piapi_tool = tools[2]           # PiAPIVideoTool

        # Extract state
        user_request = state.get("user_request", "")
        parsed_intent = state.get("parsed_intent", {})
        target_platforms = state.get("target_platforms", ["tiktok"])

        # Step 1: Fetch trending topic (if not explicitly provided)
        trend_topic = await _fetch_trending_topic(
            google_sheets_tool,
            user_request,
            parsed_intent
        )

        logger.info(f"Selected trend topic: {trend_topic}")

        # Step 2: Generate script
        script_result = await _generate_script(
            script_tool,
            trend_topic,
            target_platforms[0],  # Use first platform for script optimization
            parsed_intent
        )

        script = script_result.get("script", "")
        script_cost = script_result.get("cost_usd", 0.0)

        logger.info(f"Script generated: {len(script)} characters, cost: ${script_cost:.4f}")

        # Step 3: Generate video with PiAPI.ai
        video_result = await _generate_video(
            piapi_tool,
            script,
            target_platforms[0],
            parsed_intent
        )

        video_url = video_result.get("video_url", "")
        video_duration = video_result.get("duration_seconds", 0)
        captions = video_result.get("captions", "")
        video_cost = video_result.get("cost_usd", 0.0)

        logger.info(
            f"Video generated: {video_url}, duration: {video_duration}s, "
            f"cost: ${video_cost:.2f}"
        )

        # Calculate total cost
        total_cost = script_cost + video_cost

        # Build asset pack for platform agents
        asset_pack = {
            "video_url": video_url,
            "script": script,
            "captions": captions,
            "duration_seconds": video_duration,
            "trend_topic": trend_topic
        }

        logger.info(f"ContentCreationAgent completed, total cost: ${total_cost:.2f}")

        return {
            **update_workflow_phase(state, "publishing", "running"),
            "trend_topic": trend_topic,
            "script": script,
            "script_word_count": len(script.split()),
            "video_path": video_url,
            "video_duration_seconds": video_duration,
            "captions": captions,
            "asset_pack": asset_pack,
            **add_cost_to_workflow(state, "claude", script_cost),
            **add_cost_to_workflow(state, "piapi", video_cost)
        }

    except Exception as e:
        logger.error(f"ContentCreationAgent failed: {e}", exc_info=True)
        return {
            **update_workflow_phase(state, "content_creation", "failed"),
            "error_message": f"Content creation failed: {str(e)}"
        }


async def _fetch_trending_topic(
    google_sheets_tool,
    user_request: str,
    parsed_intent: Dict[str, Any]
) -> str:
    """
    Fetch trending topic from Google Sheets or use user request.

    Args:
        google_sheets_tool: GoogleSheetsTrendsTool instance
        user_request: User's original request
        parsed_intent: Parsed intent dict

    Returns:
        Trending topic string
    """
    try:
        # Check if user provided explicit topic
        detected_topic = parsed_intent.get("topic")

        if detected_topic and detected_topic != "General":
            logger.info(f"Using user-provided topic: {detected_topic}")
            return detected_topic

        # Fetch from Google Sheets
        category = parsed_intent.get("topic", "").lower()
        result = await google_sheets_tool._arun(category=category, limit=1)

        result_data = json.loads(result)

        if result_data.get("status") == "success" and result_data.get("trends"):
            trend = result_data["trends"][0]
            return trend.get("topic", "AI and Technology")

        # Fallback
        return "Trending Technology Topics"

    except Exception as e:
        logger.warning(f"Trend fetch failed, using fallback: {e}")
        return "Current Technology Trends"


@with_retry(
    retry_config=STANDARD_RETRY,
    circuit_breaker_name="claude_api",
    retryable_exceptions=API_ERRORS
)
@with_timeout(60.0)
async def _generate_script(
    script_tool,
    topic: str,
    platform: str,
    parsed_intent: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate video script using Claude.

    Args:
        script_tool: VideoScriptGeneratorTool instance
        topic: Video topic
        platform: Target platform
        parsed_intent: Parsed intent

    Returns:
        Dict with script and cost
    """
    try:
        # Determine tone based on audience
        audience = parsed_intent.get("audience", "general")
        tone_map = {
            "gen_z": "energetic",
            "millennials": "engaging",
            "boomers": "professional",
            "general": "engaging"
        }
        tone = tone_map.get(audience, "engaging")

        # Generate script
        result = await script_tool._arun(
            topic=topic,
            platform=platform,
            duration_seconds=30,
            tone=tone
        )

        result_data = json.loads(result)

        if result_data.get("status") == "success":
            return {
                "script": result_data.get("script", ""),
                "word_count": result_data.get("word_count", 0),
                "cost_usd": result_data.get("cost_usd", 0.0),
                "tokens": result_data.get("tokens", {})
            }

        raise ValueError(f"Script generation failed: {result_data.get('message')}")

    except Exception as e:
        logger.error(f"Script generation error: {e}")
        raise


@with_retry(
    retry_config=STANDARD_RETRY,
    circuit_breaker_name="piapi_api",
    retryable_exceptions=API_ERRORS
)
@with_timeout(120.0)  # Video generation takes longer
async def _generate_video(
    piapi_tool,
    script: str,
    platform: str,
    parsed_intent: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate complete video with PiAPI.ai.

    Args:
        piapi_tool: PiAPIVideoTool instance
        script: Video script
        platform: Target platform
        parsed_intent: Parsed intent

    Returns:
        Dict with video URL, captions, and cost
    """
    try:
        # Determine style based on topic
        topic = parsed_intent.get("topic", "General")
        style_map = {
            "AI and Technology": "cinematic",
            "Business and Entrepreneurship": "professional",
            "Health and Fitness": "energetic",
            "Food and Cooking": "vibrant",
            "Travel": "cinematic",
            "General": "realistic"
        }
        style = style_map.get(topic, "realistic")

        # Generate video
        result = await piapi_tool._arun(
            script=script,
            topic=parsed_intent.get("topic"),
            platform=platform,
            duration_seconds=30,
            style=style,
            include_captions=True,
            voice_gender="female"
        )

        result_data = json.loads(result)

        if result_data.get("status") == "success":
            return {
                "video_url": result_data.get("video_url", ""),
                "duration_seconds": result_data.get("duration_seconds", 0),
                "captions": result_data.get("captions", ""),
                "cost_usd": result_data.get("cost_usd", 0.0),
                "metadata": result_data.get("metadata", {})
            }

        raise ValueError(f"Video generation failed: {result_data.get('message')}")

    except Exception as e:
        logger.error(f"Video generation error: {e}")
        raise
