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
from backend.utils.metadata import format_tiktok_metadata
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


@safe_node_execution("tiktok")
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

        # Validate required state fields
        validation_error = validate_required_fields(
            state=state,
            required_fields=["asset_pack"],
            agent_name="tiktok"
        )
        if validation_error:
            return validation_error

        # Get tool
        tools = ToolRegistry.get_tiktok_tools()
        tiktok_upload_tool = tools[0]  # TikTokUploadTool

        # Get asset pack
        asset_pack = state.get("asset_pack", {})
        video_url = asset_pack.get("video_url") or state.get("video_path", "")
        script = asset_pack.get("script") or state.get("script", "")
        trend_topic = asset_pack.get("trend_topic") or state.get("trend_topic", "")

        # Validate asset pack contains video URL
        if not video_url:
            return create_error_update(
                agent_name="tiktok",
                error=ValueError("No video URL found in asset pack"),
                context={"asset_pack_keys": list(asset_pack.keys())}
            )

        # Format metadata for TikTok
        caption, hashtags = format_tiktok_metadata(
            script,
            trend_topic,
            state.get("parsed_intent", {})
        )

        logger.info(f"TikTok upload starting: {len(caption)} char caption, {len(hashtags)} hashtags")

        # Upload to TikTok (with retry logic)
        result = await _execute_tiktok_upload(
            tool=tiktok_upload_tool,
            video_url=video_url,
            caption=caption,
            hashtags=hashtags
        )

        result_data = json.loads(result)

        if result_data.get("status") == "success":
            # Create standardized platform result
            tiktok_result = create_platform_publish_result(
                platform="tiktok",
                status="success",
                url=result_data.get("share_url"),
                video_id=result_data.get("video_id"),
                metadata={
                    "embed_link": result_data.get("embed_link"),
                    "caption": caption,
                    "hashtags": hashtags,
                    "published_at": result_data.get("published_at"),
                    **result_data.get("metadata", {})
                }
            )

            logger.info(f"TikTok upload successful: {tiktok_result.get('url')}")

            # Use helper to merge publish results
            return create_success_update(
                agent_name="tiktok",
                data={
                    "tiktok_video_path": video_url,
                    **merge_publish_results(state, "tiktok", tiktok_result)
                }
            )

        else:
            error_msg = result_data.get("message", "Unknown error")
            logger.error(f"TikTok upload failed: {error_msg}")

            # Create standardized failure result
            tiktok_result = create_platform_publish_result(
                platform="tiktok",
                status="failed",
                error=error_msg
            )

            return create_error_update(
                agent_name="tiktok",
                error=RuntimeError(f"TikTok upload failed: {error_msg}"),
                context=merge_publish_results(state, "tiktok", tiktok_result)
            )

    except Exception as e:
        logger.error(f"TikTokAgent failed: {e}", exc_info=True)

        # Create standardized failure result
        tiktok_result = create_platform_publish_result(
            platform="tiktok",
            status="failed",
            error=str(e)
        )

        return create_error_update(
            agent_name="tiktok",
            error=e,
            context=merge_publish_results(state, "tiktok", tiktok_result)
        )


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

@with_retry(retry_config=STANDARD_RETRY, circuit_breaker_name="tiktok_api")
@with_timeout(120.0)  # 2 minute timeout for upload
async def _execute_tiktok_upload(
    tool: Any,
    video_url: str,
    caption: str,
    hashtags: list
) -> str:
    """
    Execute TikTok upload with retry logic for network resilience.

    This function automatically retries on API failures with exponential backoff,
    following the template pattern for robust external API calls.

    Args:
        tool: TikTokUploadTool instance
        video_url: Video URL to upload
        caption: Video caption
        hashtags: List of hashtags

    Returns:
        JSON string with upload result

    Raises:
        RuntimeError: If upload fails after all retries
    """
    try:
        logger.info("Executing TikTok upload with retry protection")

        result = await tool._arun(
            video_url=video_url,
            caption=caption,
            hashtags=hashtags,
            privacy_level="PUBLIC_TO_EVERYONE",
            allow_comments=True,
            allow_duet=True,
            allow_stitch=True
        )

        return result

    except Exception as e:
        logger.error(f"TikTok upload failed after retries: {e}")
        raise RuntimeError(f"TikTok upload execution failed: {str(e)}")
