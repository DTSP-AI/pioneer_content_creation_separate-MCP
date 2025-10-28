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

from backend.state.state_schema import VideoWorkflowState, update_workflow_phase, add_cost_to_workflow, update_workflow_stage
from backend.tools import ToolRegistry
from backend.utils.response_parsers import parse_video_response
from backend.utils.state_helpers import create_error_update, validate_required_fields
from backend.graph.error_recovery import (
    with_retry,
    with_timeout,
    safe_node_execution,
    STANDARD_RETRY,
    API_ERRORS
)
from backend.workflow.orchestration import (
    ContentOrchestrator,
    Priority,
    ContentType
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

        # Validate required state fields
        validation_error = validate_required_fields(
            state=state,
            required_fields=["user_request", "parsed_intent", "target_platforms"],
            agent_name="content_creation"
        )
        if validation_error:
            return validation_error

        # Update workflow stage to CREATION (from orchestration.WorkflowStage)
        logger.info("Entering CREATION stage - generating content assets")

        # Get tools (dynamically loads MCP tools if available)
        tools = await ToolRegistry.get_content_creation_tools()

        # Find tools by name (robust to MCP tool addition)
        google_sheets_tool = next((t for t in tools if "sheets" in t.name.lower() or "trend" in t.name.lower()), None)
        script_tool = next((t for t in tools if "script" in t.name.lower()), None)

        # Extract state variables first (needed for tool selection)
        user_request = state.get("user_request", "")
        parsed_intent = state.get("parsed_intent", {})
        target_platforms = state.get("target_platforms", ["tiktok"])

        # Extract workflow metadata for intelligent tool selection
        workflow_priority = state.get("priority", "balanced")
        duration_seconds = parsed_intent.get("duration_seconds", 5)

        # Determine priority from user request keywords
        priority = Priority.BALANCED
        user_request_lower = user_request.lower()
        if any(word in user_request_lower for word in ["quickly", "fast", "asap", "urgent", "hurry"]):
            priority = Priority.SPEED
            logger.info("Detected urgency keywords - prioritizing SPEED")
        elif any(word in user_request_lower for word in ["high quality", "best", "professional", "cinematic"]):
            priority = Priority.QUALITY
            logger.info("Detected quality keywords - prioritizing QUALITY")
        elif workflow_priority in ["quality", "speed", "balanced"]:
            priority = Priority(workflow_priority)

        # Get primary platform for tool selection
        platform = target_platforms[0] if target_platforms else "tiktok"

        # Get platform requirements for aspect ratio
        platform_requirements = ContentOrchestrator.get_platform_requirements(platform)
        aspect_ratio = platform_requirements.get("video_aspect_ratio", "9:16")

        # Use orchestrator for intelligent tool selection
        selected_model, reasoning = ContentOrchestrator.select_video_tool(
            platform=platform,
            priority=priority,
            duration_seconds=duration_seconds,
            aspect_ratio=aspect_ratio.split(" ")[0]  # Get first option if multiple
        )

        logger.info(f"Orchestrator selected: {selected_model}")
        logger.info(f"Selection reasoning: {reasoning}")

        # Find the selected tool from available tools
        video_tool = next((t for t in tools if t.name == selected_model), None)

        # Fallback chain from orchestrator reasoning
        if not video_tool and "fallback_models" in reasoning:
            for fallback_model in reasoning["fallback_models"]:
                video_tool = next((t for t in tools if t.name == fallback_model), None)
                if video_tool:
                    logger.warning(f"Primary tool unavailable, using fallback: {fallback_model}")
                    break

        # Ultimate fallback to any video generation tool
        if not video_tool:
            video_tool = next((t for t in tools if "video" in t.name.lower() and "generate" in t.name.lower()), None)
            if video_tool:
                logger.warning(f"Using ultimate fallback video tool: {video_tool.name}")

        if not google_sheets_tool or not script_tool or not video_tool:
            raise RuntimeError(f"Missing required tools. Available: {[t.name for t in tools]}")

        # Step 1: Fetch trending topic (if not explicitly provided)
        trend_topic = await _fetch_trending_topic(
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
        script_service = script_result.get("service_name", "claude")  # Get actual service used (claude or openai)

        logger.info(f"Script generated: {len(script)} characters, service: {script_service}, cost: ${script_cost:.4f}")

        # Step 3: Generate video (via MCP server)
        video_result = await _generate_video(
            video_tool,
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
        logger.info("Content CREATION stage completed - moving to REFINEMENT/DELIVERY stage")

        # Extract provider from video tool name for cost tracking
        provider_name = "piapi"  # Default fallback
        if video_tool and video_tool.name.startswith("generate_video_"):
            # Extract provider from tool name (e.g., "generate_video_hailuo" -> "hailuo")
            provider_name = video_tool.name.replace("generate_video_", "")
            logger.info(f"Detected video provider: {provider_name}")

        return {
            **update_workflow_phase(state, "publishing", "running"),
            **update_workflow_stage(state, "refinement"),  # Moving to refinement/delivery stage
            "priority": priority.value,  # Store priority for downstream agents
            "trend_topic": trend_topic,
            "script": script,
            "script_word_count": len(script.split()),
            "video_path": video_url,
            "video_duration_seconds": video_duration,
            "captions": captions,
            "asset_pack": asset_pack,
            "video_provider": provider_name,  # Track which provider was used
            "orchestration_metadata": {
                "selected_model": reasoning.get("selected_model"),
                "priority": priority.value,
                "platform": platform,
                "platform_requirements": platform_requirements,
                "quality_score": reasoning.get("quality_score"),
                "estimated_time": reasoning.get("estimated_time"),
                "cost_tier": reasoning.get("cost_tier"),
                "strengths": reasoning.get("strengths"),
                "fallback_models": reasoning.get("fallback_models", []),
                "script_service": script_service,  # Track which LLM was used for script
                "video_provider": provider_name  # Track which video provider was used
            },
            **add_cost_to_workflow(state, script_service, script_cost),  # Use actual service name instead of hardcoded "claude"
            **add_cost_to_workflow(state, provider_name, video_cost)  # Use actual provider instead of hardcoded "piapi"
        }

    except Exception as e:
        logger.error(f"ContentCreationAgent failed: {e}", exc_info=True)
        return {
            **create_error_update(
                agent_name="content_creation",
                error=e,
                context={}
            ),
            **update_workflow_phase(state, "content_creation", "failed")
        }


@with_retry(
    retry_config=STANDARD_RETRY,
    retryable_exceptions=API_ERRORS
)
@with_timeout(30.0)
async def _fetch_trending_topic(
    user_request: str,
    parsed_intent: Dict[str, Any]
) -> str:
    """
    Extract topic from user request (no fake trend generation).

    Args:
        user_request: User's original request
        parsed_intent: Parsed intent dict

    Returns:
        Topic string extracted from user request

    Raises:
        ValueError: If no valid topic can be determined from user request
    """
    # Check if user provided explicit topic
    detected_topic = parsed_intent.get("topic")

    if detected_topic and detected_topic != "General":
        logger.info(f"Using user-provided topic: {detected_topic}")
        return detected_topic

    # Extract topic from user request
    if user_request and len(user_request.strip()) > 0:
        # Use first 50 chars of user request as topic
        extracted_topic = user_request[:50].strip()
        logger.info(f"Extracted topic from user request: {extracted_topic}")
        return extracted_topic

    # No valid topic found
    error_msg = (
        f"Cannot determine video topic from user request. "
        f"Please provide a specific topic or content idea."
    )
    logger.error(error_msg)
    raise ValueError(error_msg)


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
    Generate video script using Claude, optimized for visual generation.

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

        # Add visual instructions to topic for better video generation
        visual_instructions = (
            "Include vivid visual descriptions, camera movements, and scene details. "
            "Write for a 5-10 second video with dynamic, engaging visuals."
        )

        enhanced_topic = f"{topic}. {visual_instructions}"

        # Generate script with visual focus
        result = await script_tool._arun(
            topic=enhanced_topic,
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


def _build_video_prompt_from_script(script: str, topic: str, style: str) -> tuple:
    """
    Convert script to cinematic video prompt with motion cues for MCP tools.

    Uses proven prompt engineering techniques:
    - Hunyuan: Dramatic lighting, built-in prompt rewrite
    - Kling: Layered prompts with motion cues
    - Luma: Cinematic camera movements

    Args:
        script: Video script text
        topic: Content topic
        style: Visual style (cinematic, professional, etc.)

    Returns:
        Tuple of (prompt, negative_prompt)
    """
    # Cinematic style descriptors optimized for video generation
    style_descriptors = {
        "cinematic": "cinematic slow motion, dramatic lighting from above creates soft glow, wide angle shot",
        "professional": "professional broadcast quality, clean composition, corporate aesthetic, sharp focus",
        "energetic": "dynamic camera movement, vibrant colors, high energy, smooth tracking shot",
        "vibrant": "colorful, bright natural lighting, cheerful atmosphere, warm tones",
        "realistic": "photorealistic, natural lighting, documentary style, authentic feel"
    }

    # Build prompt with script summary + cinematic descriptors + motion cues
    # Limit to first 200 chars of script to stay within model limits
    script_summary = script[:200].strip()

    # Add visual style and motion cues
    style_desc = style_descriptors.get(style, style_descriptors['realistic'])

    prompt = (
        f"{script_summary}. "
        f"{style_desc}, "
        f"smooth camera movement, high production value, engaging visuals, professional cinematography"
    )

    # Negative prompt to filter out low-quality outputs
    negative_prompt = (
        "chaos, bad video, low quality, low resolution, blurry, distorted, "
        "choppy motion, amateur, pixelated, artifacts, glitches"
    )

    return prompt, negative_prompt


@with_retry(
    retry_config=STANDARD_RETRY,
    circuit_breaker_name="piapi_api",
    retryable_exceptions=API_ERRORS
)
@with_timeout(120.0)  # Video generation takes longer
async def _generate_video(
    video_tool,
    script: str,
    platform: str,
    parsed_intent: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate complete video via MCP server using optimal prompting.

    Args:
        video_tool: Video generation tool (MCP tool from PiAPI)
        script: Video script
        platform: Target platform (tiktok, youtube_shorts, etc.)
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

        # Build cinematic prompt from script using proven techniques
        prompt, negative_prompt = _build_video_prompt_from_script(script, topic, style)

        logger.info(f"Generated video prompt: {prompt[:100]}...")

        # Map platform to aspect ratio (MCP parameter)
        aspect_ratio_map = {
            "tiktok": "9:16",          # Vertical for TikTok
            "youtube_shorts": "9:16",   # Vertical for Shorts
            "youtube": "16:9",          # Horizontal for regular YouTube
            "instagram": "9:16"         # Vertical for Instagram Reels
        }
        aspect_ratio = aspect_ratio_map.get(platform.lower(), "9:16")

        # Build MCP-compliant parameters
        params = {
            "prompt": prompt,
            "negativePrompt": negative_prompt,
            "aspectRatio": aspect_ratio
        }

        # Unified video tool - map to new schema
        if video_tool.name == "generate_video_unified":
            # Determine provider based on legacy tool mapping
            params["provider"] = "hailuo"  # Default to best quality
            params["task_type"] = "txt2vid"
            params["duration"] = 6
            params["resolution"] = "1080p"
            params["aspect_ratio"] = aspect_ratio or "9:16"

            # Hailuo has 2000 char limit on prompt
            if len(params["prompt"]) > 2000:
                params["prompt"] = params["prompt"][:2000]

        # Legacy tool support (backwards compatibility)
        elif video_tool.name == "generate_video_hunyuan":
            params["model"] = "fastHunyuan"
        elif video_tool.name == "generate_video_kling":
            params["duration"] = "5s"
        elif video_tool.name == "generate_video_luma":
            params["duration"] = "5s"
        elif video_tool.name == "generate_video_hailuo":
            if len(params["prompt"]) > 2000:
                params["prompt"] = params["prompt"][:2000]
            params["model"] = "t2v-01"
            params["expandPrompt"] = False

        # Call MCP tool with correct parameters
        logger.info(f"Calling {video_tool.name} with aspect ratio {aspect_ratio}")
        result = await video_tool._arun(**params)

        # Parse response using unified parser (supports both JSON and text formats)
        return parse_video_response(
            result=result,
            tool_name=video_tool.name,
            prompt=prompt,
            aspect_ratio=aspect_ratio
        )

    except Exception as e:
        logger.error(f"Video generation error: {e}")
        raise
