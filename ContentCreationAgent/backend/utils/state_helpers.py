"""
State Update Helpers

Standardized functions for creating consistent state updates across all agents.
These helpers ensure uniform error handling and success responses in LangGraph nodes.

Architecture Compliance:
- Follows template pattern from READ_ONLY_SUB_AGENT_EXAMPLE.md
- Provides type-safe state update construction
- Reduces boilerplate in agent return statements
"""

from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


def create_success_update(
    agent_name: str,
    data: Dict[str, Any],
    status: str = "success"
) -> Dict[str, Any]:
    """
    Create a standardized success state update.

    Args:
        agent_name: Name of the agent (e.g., "tiktok", "youtube_shorts", "content_creation")
        data: Additional state data to merge (video_url, script, etc.)
        status: Status string (default: "success")

    Returns:
        Dict with current_agent, status, and merged data

    Example:
        >>> create_success_update("tiktok", {"video_url": "https://...", "caption": "..."})
        {
            "current_agent": "tiktok",
            "status": "success",
            "video_url": "https://...",
            "caption": "..."
        }
    """
    return {
        "current_agent": agent_name,
        "status": status,
        **data
    }


def create_error_update(
    agent_name: str,
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized error state update.

    Args:
        agent_name: Name of the agent that encountered the error
        error: Exception that was raised
        context: Optional additional context (video_url, step, etc.)

    Returns:
        Dict with current_agent, status, error details, and context

    Example:
        >>> create_error_update("tiktok", ValueError("Invalid URL"), {"step": "upload"})
        {
            "current_agent": "tiktok",
            "status": "failed",
            "error_message": "Invalid URL",
            "error_type": "ValueError",
            "step": "upload"
        }
    """
    base_update = {
        "current_agent": agent_name,
        "status": "failed",
        "error_message": str(error),
        "error_type": type(error).__name__
    }

    if context:
        base_update.update(context)

    logger.error(
        f"Agent {agent_name} failed: {type(error).__name__}: {str(error)}",
        extra={"agent": agent_name, "error_type": type(error).__name__}
    )

    return base_update


def create_platform_publish_result(
    platform: str,
    status: str,
    url: Optional[str] = None,
    video_id: Optional[str] = None,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized publish result for platform agents.

    Used in publish_results dictionary for TikTok, YouTube, etc.

    Args:
        platform: Platform name ("tiktok", "youtube_shorts", "instagram")
        status: Status ("success" or "failed")
        url: Published video URL (for success)
        video_id: Platform video ID (for success)
        error: Error message (for failure)
        metadata: Additional platform-specific metadata

    Returns:
        Dict with standardized publish result structure

    Example:
        >>> create_platform_publish_result(
        ...     platform="tiktok",
        ...     status="success",
        ...     url="https://tiktok.com/@user/video/123",
        ...     video_id="123",
        ...     metadata={"caption": "...", "hashtags": [...]}
        ... )
        {
            "status": "success",
            "platform": "tiktok",
            "url": "https://tiktok.com/@user/video/123",
            "video_id": "123",
            "caption": "...",
            "hashtags": [...]
        }
    """
    result = {
        "status": status,
        "platform": platform
    }

    if status == "success":
        if url:
            result["url"] = url
        if video_id:
            result["video_id"] = video_id
        if metadata:
            result.update(metadata)
    else:
        if error:
            result["error"] = error

    return result


def merge_publish_results(
    state: Dict[str, Any],
    platform: str,
    result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge a new publish result into state's publish_results dictionary.

    Args:
        state: Current workflow state
        platform: Platform name (key for publish_results)
        result: Platform publish result to add

    Returns:
        Dict with updated publish_results

    Example:
        >>> state = {"publish_results": {"tiktok": {...}}}
        >>> result = {"status": "success", "url": "..."}
        >>> merge_publish_results(state, "youtube_shorts", result)
        {
            "publish_results": {
                "tiktok": {...},
                "youtube_shorts": {"status": "success", "url": "..."}
            }
        }
    """
    publish_results = state.get("publish_results", {})
    publish_results[platform] = result

    return {"publish_results": publish_results}


def validate_required_fields(
    state: Dict[str, Any],
    required_fields: List[str],
    agent_name: str
) -> Optional[Dict[str, Any]]:
    """
    Validate that required fields exist in state.

    If validation fails, returns an error update. Otherwise returns None.

    Args:
        state: Current workflow state
        required_fields: List of required field names
        agent_name: Name of agent performing validation

    Returns:
        Error update dict if validation fails, None if validation passes

    Example:
        >>> error = validate_required_fields(
        ...     state={"video_url": "..."},
        ...     required_fields=["video_url", "script"],
        ...     agent_name="tiktok"
        ... )
        >>> if error:
        ...     return error  # Missing "script" field
    """
    # Check if field exists in state (not if it's truthy)
    missing_fields = [field for field in required_fields if field not in state]

    if missing_fields:
        error_msg = f"Missing required fields: {', '.join(missing_fields)}"
        logger.error(f"Validation failed for {agent_name}: {error_msg}")

        return create_error_update(
            agent_name=agent_name,
            error=ValueError(error_msg),
            context={"missing_fields": missing_fields}
        )

    return None
