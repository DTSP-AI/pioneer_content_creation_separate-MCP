"""
Response parsing utilities for video generation tools.

Provides unified parsing for both JSON (MCP tools) and text (legacy tools) responses.
"""

import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Provider pricing per second (approximate costs for video generation)
PROVIDER_PRICING = {
    "hailuo": 0.002,  # High quality, best for general use
    "wan": 0.003,     # Camera control features
    "luma": 0.004,    # Physics simulation
    "piapi": 0.002,   # Fallback/default
    "hunyuan": 0.002,
    "kling": 0.003,
}


def estimate_video_cost(provider: str, seconds: float) -> float:
    """
    Estimate video generation cost based on provider and duration.

    Args:
        provider: Provider name (hailuo, wan, luma, etc.)
        seconds: Video duration in seconds

    Returns:
        Estimated cost in USD
    """
    rate = PROVIDER_PRICING.get(provider.lower(), PROVIDER_PRICING["hailuo"])
    cost = round(rate * seconds, 4)
    logger.debug(f"Estimated cost for {provider} ({seconds}s): ${cost}")
    return cost


def parse_video_response(
    result: str,
    tool_name: str,
    prompt: str,
    aspect_ratio: str = "9:16"
) -> Dict[str, Any]:
    """
    Parse video generation tool response in either JSON or text format.

    Handles two response formats:
    1. JSON format (MCP tools): TaskOutput schema with status, task_id, output
    2. Text format (legacy tools): Plain text with "Video url:" marker

    Args:
        result: Raw response string from tool
        tool_name: Name of the tool that generated the response
        prompt: Original video generation prompt
        aspect_ratio: Video aspect ratio

    Returns:
        Parsed video data dict with video_url, duration, cost, etc.

    Raises:
        ValueError: If response format is unrecognized or video_url not found
    """
    # ATTEMPT 1: Parse as JSON (Unified MCP Tools)
    try:
        response_data = json.loads(result)

        # Validate JSON structure matches TaskOutput schema
        if isinstance(response_data, dict):
            status = response_data.get("status")
            task_id = response_data.get("task_id")
            output = response_data.get("output", {})

            logger.info(f"Parsed JSON response: status={status}, task_id={task_id}")

            # Handle successful completion
            if status == "Completed" and output:
                video_url = output.get("video_url")

                if not video_url:
                    raise ValueError("No video_url in JSON output")

                logger.info(f"Video generated successfully (JSON): {video_url}")

                # Calculate accurate cost
                duration_seconds = output.get("duration", 6)
                # Try to get cost from output metadata, fallback to estimation
                cost_usd = (
                    output.get("cost_usd") or
                    output.get("metadata", {}).get("cost_usd") or
                    output.get("cost") or
                    estimate_video_cost(tool_name.replace("generate_video_", ""), duration_seconds)
                )

                return {
                    "video_url": video_url,
                    "duration_seconds": duration_seconds,
                    "captions": output.get("captions", ""),
                    "cost_usd": cost_usd,
                    "task_id": task_id,
                    "metadata": {
                        "tool": tool_name,
                        "prompt": prompt[:100],
                        "aspect_ratio": aspect_ratio,
                        "response_format": "json"
                    }
                }

            # Handle failure status
            elif status == "Failed":
                error_msg = response_data.get("error", "Unknown error")
                raise ValueError(f"Video generation failed (MCP): {error_msg}")

    except (json.JSONDecodeError, TypeError, AttributeError) as parse_error:
        # JSON parsing failed, fall back to legacy text parsing
        logger.debug(f"JSON parse failed, trying text format: {parse_error}")

    # ATTEMPT 2: Parse as text (Legacy PiAPIVideoTool format)
    if "Video generated successfully!" in result or "Video url:" in result:
        # Extract video URL from text response
        lines = result.split('\n')
        video_url = None

        for i, line in enumerate(lines):
            if line.startswith("Video url:") or line.startswith("Video urls:"):
                # URL is on the next line
                if i + 1 < len(lines):
                    video_url = lines[i + 1].strip()
                break

        if not video_url:
            raise ValueError(f"Video URL not found in text response: {result[:200]}")

        logger.info(f"Video generated successfully (text): {video_url}")

        # Estimate cost for text format (legacy)
        estimated_cost = estimate_video_cost(tool_name.replace("generate_video_", ""), 6)

        return {
            "video_url": video_url,
            "duration_seconds": 6,
            "captions": "",
            "cost_usd": estimated_cost,
            "metadata": {
                "tool": tool_name,
                "prompt": prompt[:100],
                "aspect_ratio": aspect_ratio,
                "response_format": "text"
            }
        }

    # Both parsing methods failed
    raise ValueError(
        f"Unrecognized response format from {tool_name}. "
        f"Expected JSON or text format. Received: {result[:200]}"
    )
