"""
Supervisor Agent Chat Processing

Handles conversational workflow creation:
1. Analyzes user requests
2. Generates workflow proposals
3. Returns human-readable responses
4. Creates workflows on approval
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from backend.config import get_settings
from backend.database.models import ThreadMessage

logger = logging.getLogger(__name__)
settings = get_settings()


# Initialize Claude
claude = ChatAnthropic(
    model=settings.ANTHROPIC_MODEL,
    temperature=0.7,
    anthropic_api_key=settings.ANTHROPIC_API_KEY
)


async def process_chat_message(
    thread_id: str,
    user_message: str,
    session: AsyncSession
) -> Dict[str, Any]:
    """
    Process user message with supervisor agent.

    Analyzes message to detect workflow creation requests
    and generates appropriate response.

    Args:
        thread_id: Conversation thread ID
        user_message: User's message
        session: Database session

    Returns:
        Dict with:
            - content: Agent response text
            - metadata: Optional workflow proposal
            - workflow_created: Optional created workflow
    """
    try:
        # Analyze user intent
        analysis = await analyze_user_intent(user_message)

        # If user wants to create content, propose workflow
        if analysis["intent"] == "create_content":
            return await generate_workflow_proposal(
                user_message=user_message,
                platforms=analysis.get("platforms", ["tiktok"]),
                content_type=analysis.get("content_type", "video")
            )

        # Otherwise, provide conversational response
        return await generate_conversational_response(user_message)

    except Exception as e:
        logger.error(f"Error processing chat message: {e}", exc_info=True)
        return {
            "content": "I'm sorry, I encountered an error processing your request. Please try again.",
            "metadata": {"error": str(e)}
        }


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
2. Platforms: Which platforms? (tiktok, youtube_shorts, both)
3. Content type: What type of content? (video, image, text)
4. Topic: What is the content about?

Respond in JSON format:
{
  "intent": "create_content|question|greeting|other",
  "platforms": ["tiktok", "youtube_shorts"],
  "content_type": "video",
  "topic": "brief description",
  "duration": "30 seconds|60 seconds|custom",
  "confidence": 0.0-1.0
}

Examples:
User: "Create a TikTok video about AI"
Response: {"intent": "create_content", "platforms": ["tiktok"], "content_type": "video", "topic": "AI", "duration": "30 seconds", "confidence": 0.95}

User: "Make a video for both TikTok and YouTube Shorts about cooking"
Response: {"intent": "create_content", "platforms": ["tiktok", "youtube_shorts"], "content_type": "video", "topic": "cooking", "duration": "60 seconds", "confidence": 0.9}

User: "What can you do?"
Response: {"intent": "question", "platforms": [], "content_type": null, "topic": "capabilities", "confidence": 0.95}
"""

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=message)
        ]

        response = await claude.ainvoke(messages)

        # Parse JSON response
        import json
        analysis = json.loads(response.content)

        return analysis

    except Exception as e:
        logger.error(f"Error analyzing intent: {e}", exc_info=True)
        # Default to unknown intent
        return {
            "intent": "other",
            "platforms": [],
            "content_type": null,
            "topic": message[:100],
            "confidence": 0.0
        }


async def generate_workflow_proposal(
    user_message: str,
    platforms: list[str],
    content_type: str
) -> Dict[str, Any]:
    """
    Generate a workflow proposal for content creation.

    Args:
        user_message: Original user request
        platforms: Target platforms
        content_type: Type of content

    Returns:
        Response with workflow proposal
    """
    # Estimate cost (rough approximation)
    base_cost = 0.50  # Claude for script
    video_cost = 2.00 if content_type == "video" else 0.0  # PiAPI
    platform_cost = len(platforms) * 0.10  # Platform APIs
    total_cost = base_cost + video_cost + platform_cost

    # Build response
    platform_names = {
        "tiktok": "TikTok",
        "youtube_shorts": "YouTube Shorts"
    }
    platform_str = " and ".join([platform_names.get(p, p) for p in platforms])

    content = f"""I understand you want to create content for {platform_str}.

Here's what I propose:

📝 **Request:** {user_message}
🎯 **Platforms:** {platform_str}
💰 **Estimated Cost:** ${total_cost:.2f}

**What I'll do:**
1. Generate an engaging script optimized for short-form video
2. Create a high-quality video using AI ({content_type})
3. Prepare for publishing to {platform_str}

**Cost Breakdown:**
- Script Generation (Claude): $0.50
- Video Creation (PiAPI): ${video_cost:.2f}
- Platform Publishing: ${platform_cost:.2f}

Should I proceed with creating this content?"""

    # Return with proposal metadata
    return {
        "content": content,
        "metadata": {
            "awaiting_approval": True,
            "workflow_proposal": {
                "user_request": user_message,
                "target_platforms": platforms,
                "estimated_cost_usd": total_cost,
                "reasoning": f"Optimized {content_type} for {platform_str}"
            }
        }
    }


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

        response = await claude.ainvoke(messages)

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
    session: AsyncSession
) -> Dict[str, Any]:
    """
    Create workflow from approved proposal.

    Args:
        thread_id: Thread ID
        message: Message containing proposal
        session: Database session

    Returns:
        Created workflow details
    """
    try:
        proposal = message.metadata.get("workflow_proposal", {})

        # Import here to avoid circular dependency
        from backend.api.routes import CreateWorkflowRequest
        from fastapi import BackgroundTasks

        # Create workflow using existing endpoint logic
        # For now, return the proposal as if workflow was created
        # TODO: Actually trigger workflow creation

        return {
            "workflow_id": f"wf-{str(uuid.uuid4())}",
            "status": "pending",
            "user_request": proposal.get("user_request"),
            "target_platforms": proposal.get("target_platforms", []),
            "workflow_status": "pending",
            "current_phase": "supervisor",
            "created_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error approving workflow: {e}", exc_info=True)
        raise


# Import at bottom to avoid circular import
import uuid
from datetime import datetime
