"""
Supervisor Agent Chat Processing

Handles conversational workflow creation:
1. Analyzes user requests
2. Generates workflow proposals
3. Returns human-readable responses
4. Creates workflows on approval

⚠️ IMPORTANT - LLM PRIORITY:
- PRIMARY: Claude (Anthropic) - claude-3-5-sonnet-20240620
- FALLBACK: OpenAI (gpt-5-nano) - only if ANTHROPIC_API_KEY not available
- Priority logic at lines 33-49 (get_llm function)
- Claude is preferred for all conversational interactions
- OpenAI used only as fallback when Claude unavailable
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import anthropic

from backend.config import get_settings
from backend.database.models import ThreadMessage
from backend.workflow.orchestration import (
    ContentOrchestrator,
    Priority,
    ContentType
)

logger = logging.getLogger(__name__)
settings = get_settings()


# Lazy LLM initialization function
def get_llm():
    """Get LLM instance with fallback logic and model validation"""
    if settings.ANTHROPIC_API_KEY:
        from langchain_anthropic import ChatAnthropic

        # Validate Claude model name
        valid_models = [
            # Current models (2025)
            "claude-sonnet-4-5-20250929",
            "claude-sonnet-4-5",
            "claude-haiku-4-5-20251001",
            "claude-haiku-4-5",
            "claude-opus-4-1-20250805",
            "claude-opus-4-1",
            # Legacy models (deprecated)
            "claude-3-5-sonnet-20241022",
            "claude-3-5-sonnet-20240620",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ]

        model = settings.ANTHROPIC_MODEL
        if model not in valid_models:
            logger.warning(
                f"Potentially invalid Claude model '{model}'. "
                f"Valid models: {', '.join(valid_models)}. "
                f"Falling back to claude-sonnet-4-5-20250929"
            )
            model = "claude-sonnet-4-5-20250929"

        return ChatAnthropic(
            model=model,
            temperature=0.7,
            anthropic_api_key=settings.ANTHROPIC_API_KEY
        )
    elif settings.OPENAI_API_KEY:
        return ChatOpenAI(
            model=settings.OPENAI_SCRIPT_MODEL,
            temperature=0.7,
            api_key=settings.OPENAI_API_KEY
        )
    else:
        raise ValueError(
            "No LLM API key configured. Set either ANTHROPIC_API_KEY or OPENAI_API_KEY"
        )


async def process_chat_message(
    thread_id: str,
    user_message: str,
    session: AsyncSession,
    tenant_id: str = "default-tenant",
    user_id: str = "default-user"
) -> Dict[str, Any]:
    """
    Process user message with supervisor agent.

    Analyzes message to detect workflow creation requests
    and generates appropriate response.

    Args:
        thread_id: Conversation thread ID
        user_message: User's message
        session: Database session
        tenant_id: Tenant identifier for memory isolation
        user_id: User identifier for memory context

    Returns:
        Dict with:
            - content: Agent response text
            - metadata: Optional workflow proposal
            - workflow_created: Optional created workflow
    """
    from backend.memory import MemoryManager

    try:
        # Initialize memory manager for thread context
        memory_manager = MemoryManager(tenant_id=tenant_id, agent_id="supervisor")

        # Store user message in thread memory
        memory_manager.append_thread(thread_id, "user", user_message)

        # Analyze user intent
        analysis = await analyze_user_intent(user_message)

        # Generate response based on intent
        if analysis["intent"] == "create_content":
            response = await generate_workflow_proposal(
                user_message=user_message,
                analysis=analysis
            )
        else:
            response = await generate_conversational_response(user_message)

        # Store assistant response in thread memory
        memory_manager.append_thread(thread_id, "assistant", response.get("content", ""))

        return response

    except Exception as e:
        logger.error(f"Error processing chat message: {e}", exc_info=True)
        error_response = {
            "content": "I'm sorry, I encountered an error processing your request. Please try again.",
            "metadata": {"error": str(e)}
        }

        # Try to store error response in memory
        try:
            from backend.memory import MemoryManager
            memory_manager = MemoryManager(tenant_id=tenant_id, agent_id="supervisor")
            memory_manager.append_thread(thread_id, "assistant", error_response["content"])
        except Exception:
            pass  # Don't fail if memory storage fails

        return error_response


async def analyze_user_intent(message: str) -> Dict[str, Any]:
    """
    Analyze user message to detect intent and extract parameters.

    Args:
        message: User's message

    Returns:
        Dict with intent and extracted parameters
    """
    system_prompt = """You are a supervisor agent that helps users create content for social media.

Analyze the user's message and determine:
1. Intent: Is this a content creation request? (create_content, question, greeting, other)
2. Platforms: Which platforms? (tiktok, youtube_shorts, youtube, instagram, twitter, linkedin)
3. Content type: What type of content? (video, image, text)
4. Topic: What is the content about?
5. Priority: Quality vs speed preference? (quality, balanced, speed)
6. Duration: Desired video duration in seconds

Respond in JSON format:
{
  "intent": "create_content|question|greeting|other",
  "platforms": ["tiktok", "youtube_shorts"],
  "content_type": "video",
  "topic": "brief description",
  "duration_seconds": 5,
  "priority": "quality|balanced|speed",
  "urgency_detected": false,
  "quality_keywords": [],
  "speed_keywords": [],
  "confidence": 0.0-1.0
}

Priority Detection Rules:
- SPEED: Keywords like "quickly", "fast", "ASAP", "urgent", "hurry", "rush"
- QUALITY: Keywords like "high quality", "best", "professional", "cinematic", "polished", "premium"
- BALANCED: Default if no specific keywords

Examples:
User: "Create a TikTok video about AI"
Response: {"intent": "create_content", "platforms": ["tiktok"], "content_type": "video", "topic": "AI", "duration_seconds": 5, "priority": "balanced", "urgency_detected": false, "quality_keywords": [], "speed_keywords": [], "confidence": 0.95}

User: "Make a high quality professional video for YouTube about cooking"
Response: {"intent": "create_content", "platforms": ["youtube"], "content_type": "video", "topic": "cooking", "duration_seconds": 10, "priority": "quality", "urgency_detected": false, "quality_keywords": ["high quality", "professional"], "speed_keywords": [], "confidence": 0.9}

User: "I need a quick TikTok video ASAP about trending tech"
Response: {"intent": "create_content", "platforms": ["tiktok"], "content_type": "video", "topic": "trending tech", "duration_seconds": 5, "priority": "speed", "urgency_detected": true, "quality_keywords": [], "speed_keywords": ["quick", "ASAP"], "confidence": 0.95}

User: "What can you do?"
Response: {"intent": "question", "platforms": [], "content_type": null, "topic": "capabilities", "duration_seconds": 0, "priority": "balanced", "urgency_detected": false, "quality_keywords": [], "speed_keywords": [], "confidence": 0.95}
"""

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=message)
        ]

        response = await get_llm().ainvoke(messages)

        # Parse JSON response (extract JSON from response if it contains extra text)
        import json
        import re

        content = response.content.strip()

        # Try to extract JSON if response contains extra text
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            content = json_match.group(0)

        analysis = json.loads(content)

        return analysis

    except anthropic.NotFoundError as e:
        logger.error(f"Claude model not found: {e}. Attempting fallback to OpenAI.")

        # Try OpenAI fallback
        try:
            if settings.OPENAI_API_KEY:
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=message)
                ]

                client = ChatOpenAI(
                    model=settings.OPENAI_MODEL,
                    api_key=settings.OPENAI_API_KEY
                )
                response = await client.ainvoke(messages)

                import json
                import re
                content = response.content.strip()
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    content = json_match.group(0)

                analysis = json.loads(content)
                return analysis
            else:
                raise ValueError("No valid LLM available for fallback")
        except Exception as fallback_error:
            logger.error(f"OpenAI fallback also failed: {fallback_error}")
            # Return default intent
            return {
                "intent": "other",
                "platforms": [],
                "content_type": None,
                "topic": message[:100],
                "confidence": 0.0
            }

    except Exception as e:
        logger.error(f"Error analyzing intent: {e}", exc_info=True)
        # Default to unknown intent
        return {
            "intent": "other",
            "platforms": [],
            "content_type": None,
            "topic": message[:100],
            "confidence": 0.0
        }


async def generate_workflow_proposal(
    user_message: str,
    analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate a workflow proposal for content creation using orchestration system.

    Args:
        user_message: Original user request
        analysis: Analyzed intent with platforms, content_type, priority, etc.

    Returns:
        Response with workflow proposal
    """
    # Extract analysis details
    platforms = analysis.get("platforms", ["tiktok"])
    content_type = analysis.get("content_type", "video")
    priority_str = analysis.get("priority", "balanced")
    duration_seconds = analysis.get("duration_seconds", 5)
    urgency_detected = analysis.get("urgency_detected", False)

    # Convert priority string to enum
    priority = Priority(priority_str)

    # Get primary platform for orchestration
    primary_platform = platforms[0] if platforms else "tiktok"

    # Get orchestration recommendations if video content
    orchestration_metadata = {}
    selected_model = "generate_video_hunyuan"  # Default fallback
    estimated_time = 60

    if content_type == "video":
        # Get platform requirements
        platform_requirements = ContentOrchestrator.get_platform_requirements(primary_platform)

        # Get recommended video tool
        selected_model, reasoning = ContentOrchestrator.select_video_tool(
            platform=primary_platform,
            priority=priority,
            duration_seconds=duration_seconds,
            aspect_ratio=platform_requirements.get("video_aspect_ratio", "9:16").split(" ")[0]
        )

        orchestration_metadata = reasoning
        estimated_time = reasoning.get("estimated_time", 60)

    # Estimate cost (rough approximation)
    base_cost = 0.50  # Claude for script
    video_cost = 2.00 if content_type == "video" else 0.0  # PiAPI
    platform_cost = len(platforms) * 0.10  # Platform APIs
    total_cost = base_cost + video_cost + platform_cost

    # Build response
    platform_names = {
        "tiktok": "TikTok",
        "youtube_shorts": "YouTube Shorts",
        "youtube": "YouTube",
        "instagram": "Instagram",
        "twitter": "Twitter",
        "linkedin": "LinkedIn"
    }
    platform_str = " and ".join([platform_names.get(p, p) for p in platforms])

    # Priority-specific messaging
    priority_msg = ""
    if priority == Priority.SPEED:
        priority_msg = "⚡ **Fast Mode**: Optimized for speed (estimated ~{} seconds)".format(estimated_time)
    elif priority == Priority.QUALITY:
        priority_msg = "✨ **Quality Mode**: Optimized for best quality (estimated ~{} seconds)".format(estimated_time)
    else:
        priority_msg = "⚖️ **Balanced Mode**: Optimizing for quality and speed"

    # Urgency indicator
    urgency_msg = "🚨 **Urgent Request Detected**\n" if urgency_detected else ""

    # Model selection info
    model_info = ""
    if "selected_model" in orchestration_metadata:
        model_name = orchestration_metadata["selected_model"].replace("generate_video_", "").title()
        strengths = ", ".join(orchestration_metadata.get("strengths", []))
        model_info = f"\n🎬 **Video Generator**: {model_name}\n💪 **Strengths**: {strengths}"

    content = f"""I understand you want to create content for {platform_str}.

{urgency_msg}Here's what I propose:

📝 **Request:** {user_message}
🎯 **Platforms:** {platform_str}
{priority_msg}
💰 **Estimated Cost:** ${total_cost:.2f}
⏱️ **Estimated Time:** ~{estimated_time + 30} seconds (including script generation){model_info}

**What I'll do:**
1. 📊 Fetch trending topic for {primary_platform} (if needed)
2. ✍️ Generate an engaging script optimized for {primary_platform}
3. 🎥 Create a high-quality video using AI ({content_type})
4. 📤 Prepare for publishing to {platform_str}

**Cost Breakdown:**
- Script Generation (Claude): $0.50
- Video Creation (PiAPI): ${video_cost:.2f}
- Platform Publishing: ${platform_cost:.2f}

Should I proceed with creating this content?"""

    # Return with proposal metadata (now includes orchestration info)
    result = {
        "content": content,
        "metadata": {
            "awaiting_approval": True,
            "workflow_proposal": {
                "user_request": user_message,
                "target_platforms": platforms,
                "estimated_cost_usd": total_cost,
                "priority": priority_str,
                "urgency_detected": urgency_detected,
                "duration_seconds": duration_seconds,
                "orchestration": orchestration_metadata,
                "reasoning": f"Optimized {content_type} for {platform_str} with {priority_str} priority"
            }
        }
    }

    logger.info(f"Generated workflow proposal with orchestration: {selected_model}, priority: {priority_str}")
    logger.info(f"DEBUG: generate_workflow_proposal returning keys: {list(result.keys())}")
    logger.info(f"DEBUG: Metadata keys: {list(result['metadata'].keys())}")
    logger.info(f"DEBUG: Has workflow_proposal: {'workflow_proposal' in result['metadata']}")

    return result


async def generate_conversational_response(message: str) -> Dict[str, Any]:
    """
    Generate conversational response for non-workflow messages.

    Args:
        message: User's message

    Returns:
        Response dict
    """
    system_prompt = """You are a helpful supervisor agent for a content creation system.

Your capabilities:
- Create TikTok videos (30-60 seconds)
- Create YouTube Shorts (up to 60 seconds)
- Generate scripts optimized for each platform
- Use AI to create engaging videos
- Publish directly to platforms

When users ask about your capabilities, explain what you can do.
When they greet you, be friendly.
When they ask questions, provide helpful answers.

Keep responses concise and friendly."""

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=message)
        ]

        response = await get_llm().ainvoke(messages)

        return {
            "content": response.content,
            "metadata": {}
        }

    except Exception as e:
        logger.error(f"Error generating response: {e}", exc_info=True)
        return {
            "content": "I'm here to help you create content for TikTok and YouTube Shorts. Just tell me what you'd like to create!",
            "metadata": {}
        }


async def approve_workflow_proposal(
    thread_id: str,
    message: ThreadMessage,
    session: AsyncSession,
    background_tasks = None  # FastAPI BackgroundTasks (optional for testing)
) -> Dict[str, Any]:
    """
    Create workflow from approved proposal and trigger execution.

    Creates actual Workflow and WorkflowExecution records in database,
    then triggers background execution via LangGraph.

    Args:
        thread_id: Thread ID
        message: Message containing proposal
        session: Database session
        background_tasks: FastAPI BackgroundTasks for async execution

    Returns:
        Created workflow details with execution status
    """
    from backend.database.models import Workflow, WorkflowExecution, Thread
    from sqlalchemy import select

    try:
        proposal = message.message_metadata.get("workflow_proposal", {})

        if not proposal:
            raise ValueError("No workflow proposal found in message metadata")

        # Get thread to find user and tenant
        thread_result = await session.execute(
            select(Thread).where(Thread.id == uuid.UUID(thread_id))
        )
        thread = thread_result.scalars().first()

        if not thread:
            raise ValueError(f"Thread {thread_id} not found")

        # Create Workflow record
        workflow = Workflow(
            id=uuid.uuid4(),
            tenant_id=thread.tenant_id,
            created_by=thread.user_id,
            name=f"Content: {proposal.get('user_request', 'Untitled')[:50]}",
            description=proposal.get("reasoning", ""),
            type="content_distribution",
            status="active"
        )
        session.add(workflow)
        await session.flush()

        # Create WorkflowExecution record
        execution = WorkflowExecution(
            id=uuid.uuid4(),
            workflow_id=workflow.id,
            tenant_id=thread.tenant_id,
            user_id=thread.user_id,
            status="pending",
            current_phase="content_creation",
            user_request=proposal.get("user_request", ""),
            target_platforms=proposal.get("target_platforms", []),
            execution_metadata={
                "thread_id": thread_id,
                "message_id": str(message.id),
                "estimated_cost_usd": proposal.get("estimated_cost_usd", 0.0),
                "approved_at": datetime.now(timezone.utc).isoformat()
            }
        )
        session.add(execution)
        await session.commit()

        logger.info(f"Created workflow {workflow.id} and execution {execution.id} from approved proposal")

        # 🚀 CRITICAL FIX: Trigger workflow execution in background
        if background_tasks:
            from backend.workflow.execution import execute_workflow_background

            workflow_id = f"wf-{str(workflow.id)}"

            background_tasks.add_task(
                execute_workflow_background,
                workflow_id=workflow_id,
                tenant_id=str(thread.tenant_id),
                user_id=str(thread.user_id),
                thread_id=thread_id,
                user_request=proposal.get("user_request", ""),
                target_platforms=proposal.get("target_platforms", []),
                cost_limit_usd=proposal.get("estimated_cost_usd", 5.0)
            )

            logger.info(f"✅ Triggered background execution for workflow {workflow_id}")
        else:
            logger.warning("⚠️ BackgroundTasks not provided - workflow will NOT execute automatically")

        return {
            "workflow_id": str(workflow.id),
            "execution_id": str(execution.id),
            "status": "approved",
            "execution_started": background_tasks is not None,
            "user_request": execution.user_request,
            "target_platforms": execution.target_platforms,
            "workflow_status": execution.status,
            "current_phase": execution.current_phase,
            "created_at": execution.created_at.isoformat()
        }

    except Exception as e:
        logger.error(f"Error approving workflow: {e}", exc_info=True)
        await session.rollback()
        raise


async def save_progress_message(
    session: AsyncSession,
    thread_id: str,
    message_content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Save a system progress message to the conversation thread.

    This enables real-time conversational updates as the workflow executes.

    Args:
        session: Database session
        thread_id: Thread to add message to
        message_content: Progress message (e.g., "✅ Script generated!")
        metadata: Optional metadata to attach to message
    """
    try:
        thread_uuid = uuid.UUID(thread_id)

        # Create system message with metadata
        progress_metadata = {"type": "workflow_progress"}
        if metadata:
            progress_metadata.update(metadata)

        progress_msg = ThreadMessage(
            id=uuid.uuid4(),
            thread_id=thread_uuid,
            role="system",
            content=message_content,
            message_metadata=progress_metadata
        )

        session.add(progress_msg)
        await session.commit()

        logger.info(f"Progress message saved to thread {thread_id}: {message_content[:50]}...")

    except Exception as e:
        logger.error(f"Failed to save progress message: {e}", exc_info=True)
        # Don't fail the workflow if progress message fails
        await session.rollback()


# Import at bottom to avoid circular import
import uuid
from datetime import datetime, timezone

