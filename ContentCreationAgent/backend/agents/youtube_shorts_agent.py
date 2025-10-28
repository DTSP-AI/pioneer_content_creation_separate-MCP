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
from backend.utils.metadata import format_youtube_metadata
from backend.utils.state_helpers import (
    create_success_update,
    create_error_update,
    create_platform_publish_result,
    merge_publish_results,
    validate_required_fields
)
from backend.graph.error_recovery import (
    safe_node_execution,
    with_retry,
    with_timeout,
    STANDARD_RETRY,
    API_ERRORS
)

logger = logging.getLogger(__name__)


@safe_node_execution("youtube_shorts")
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

        # Validate required state fields
        validation_error = validate_required_fields(
            state=state,
            required_fields=["asset_pack"],
            agent_name="youtube_shorts"
        )
        if validation_error:
            return validation_error

        # Get tool
        tools = ToolRegistry.get_youtube_tools()
        youtube_upload_tool = tools[0]  # YouTubeShortsUploadTool

        # Get asset pack
        asset_pack = state.get("asset_pack", {})
        video_url = asset_pack.get("video_url") or state.get("video_path", "")
        script = asset_pack.get("script") or state.get("script", "")
        trend_topic = asset_pack.get("trend_topic") or state.get("trend_topic", "")

        # Validate asset pack contains video URL
        if not video_url:
            return create_error_update(
                agent_name="youtube_shorts",
                error=ValueError("No video URL found in asset pack"),
                context={"asset_pack_keys": list(asset_pack.keys())}
            )

        # Generate metadata for YouTube
        title, description, tags = format_youtube_metadata(
            script,
            trend_topic,
            state.get("parsed_intent", {})
        )

        logger.info(
            f"YouTube Shorts upload starting: title='{title[:50]}...', "
            f"{len(tags)} tags"
        )

        # Upload to YouTube Shorts (with retry logic)
        result = await _execute_youtube_upload(
            tool=youtube_upload_tool,
            video_url=video_url,
            title=title,
            description=description,
            tags=tags
        )

        result_data = json.loads(result)

        if result_data.get("status") == "success":
            # Create standardized platform result
            youtube_result = create_platform_publish_result(
                platform="youtube_shorts",
                status="success",
                url=result_data.get("video_url"),
                video_id=result_data.get("video_id"),
                metadata={
                    "watch_url": result_data.get("watch_url"),
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "published_at": result_data.get("published_at"),
                    **result_data.get("metadata", {})
                }
            )

            logger.info(f"YouTube Shorts upload successful: {youtube_result.get('url')}")

            # Use helper to merge publish results
            return create_success_update(
                agent_name="youtube_shorts",
                data={
                    "youtube_video_path": video_url,
                    **merge_publish_results(state, "youtube_shorts", youtube_result)
                }
            )

        else:
            error_msg = result_data.get("message", "Unknown error")
            logger.error(f"YouTube Shorts upload failed: {error_msg}")

            # Create standardized failure result
            youtube_result = create_platform_publish_result(
                platform="youtube_shorts",
                status="failed",
                error=error_msg
            )

            return create_error_update(
                agent_name="youtube_shorts",
                error=RuntimeError(f"YouTube Shorts upload failed: {error_msg}"),
                context=merge_publish_results(state, "youtube_shorts", youtube_result)
            )

    except Exception as e:
        logger.error(f"YouTubeShortsAgent failed: {e}", exc_info=True)

        # Create standardized failure result
        youtube_result = create_platform_publish_result(
            platform="youtube_shorts",
            status="failed",
            error=str(e)
        )

        return create_error_update(
            agent_name="youtube_shorts",
            error=e,
            context=merge_publish_results(state, "youtube_shorts", youtube_result)
        )


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

@with_retry(retry_config=STANDARD_RETRY, circuit_breaker_name="youtube_api")
@with_timeout(180.0)  # 3 minute timeout for upload
async def _execute_youtube_upload(
    tool: Any,
    video_url: str,
    title: str,
    description: str,
    tags: list
) -> str:
    """
    Execute YouTube Shorts upload with retry logic for network resilience.

    This function automatically retries on API failures with exponential backoff,
    following the template pattern for robust external API calls.

    Args:
        tool: YouTubeShortsUploadTool instance
        video_url: Video URL to upload
        title: Video title
        description: Video description
        tags: List of tags

    Returns:
        JSON string with upload result

    Raises:
        RuntimeError: If upload fails after all retries
    """
    try:
        logger.info("Executing YouTube Shorts upload with retry protection")

        result = await tool._arun(
            video_url=video_url,
            title=title,
            description=description,
            tags=tags,
            category_id="22",  # People & Blogs
            privacy_status="public",
            made_for_kids=False
        )

        return result

    except Exception as e:
        logger.error(f"YouTube Shorts upload failed after retries: {e}")
        raise RuntimeError(f"YouTube Shorts upload execution failed: {str(e)}")
