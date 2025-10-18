"""
SupervisorAgent Node (Enhanced with LLM-based Routing)

Entry point for the content creation workflow with intelligent routing.

Architecture Compliance:
- LangGraph node (async function)
- LLM-based decision making with structured output
- Memory-aware routing (Mem0 + Qdrant context)
- Reads from VideoWorkflowState
- Returns state updates (Dict[str, Any])
- No side effects outside state updates

Pattern adopted from mcp-voice-agent:
- Supervisor uses LLM to analyze request + memory context
- Structured output for routing decisions
- Campaign history awareness for better recommendations
"""

from typing import Dict, Any, Literal, List
import logging
from datetime import datetime
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from backend.state.state_schema import VideoWorkflowState, update_workflow_phase
from backend.config import get_settings
from backend.memory.manager import MemoryManager
from backend.graph.error_recovery import safe_node_execution

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# Structured Output Models for LLM-based Routing
# =============================================================================

class SupervisorDecision(BaseModel):
    """
    Structured output for supervisor routing decisions.

    LLM returns this schema to make routing transparent and debuggable.
    """
    action: Literal["create_content", "clarify", "reject"] = Field(
        description="Action to take: create_content (proceed), clarify (need more info), reject (invalid request)"
    )
    reasoning: str = Field(
        description="Explanation of why this action was chosen"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score for this decision (0.0 to 1.0)"
    )
    extracted_topic: str = Field(
        description="Main topic/theme extracted from request"
    )
    target_audience: str = Field(
        description="Identified target audience (gen_z, millennials, general, etc.)"
    )
    content_style: str = Field(
        description="Recommended content style (educational, entertaining, inspirational, etc.)"
    )
    similar_campaigns: List[str] = Field(
        default_factory=list,
        description="IDs or descriptions of similar past campaigns (from memory)"
    )
    clarification_needed: str = Field(
        default="",
        description="What clarification is needed if action=clarify"
    )
    rejection_reason: str = Field(
        default="",
        description="Reason for rejection if action=reject"
    )


@safe_node_execution("supervisor")
async def supervisor_node(state: VideoWorkflowState) -> Dict[str, Any]:
    """
    SupervisorAgent (Enhanced) - Intelligent entry node with memory awareness.

    Responsibilities:
    1. Retrieve memory context (past campaigns, conversation history)
    2. Use LLM to analyze request + make routing decision
    3. Check cost limits (daily + per-workflow)
    4. Route to ContentCreationAgent or return clarification/rejection

    Enhanced Features:
    - LLM-based intent analysis (vs simple keywords)
    - Memory-aware recommendations (learns from past campaigns)
    - Structured output for transparency
    - Campaign history awareness

    Args:
        state: Current workflow state

    Returns:
        Dict with state updates to merge
    """
    try:
        logger.info(f"SupervisorAgent (enhanced) started for workflow: {state.get('workflow_id')}")

        # Extract input
        user_request = state.get("user_request", "")
        target_platforms = state.get("target_platforms", ["tiktok", "youtube_shorts"])
        cost_limit_usd = state.get("cost_limit_usd", settings.MAX_PER_WORKFLOW_COST_USD)
        tenant_id = state.get("tenant_id", "default-tenant")
        agent_id = state.get("agent_id", "supervisor-agent")
        thread_id = state.get("thread_id", "default-thread")

        # Validate input
        if not user_request:
            raise ValueError("user_request is required")

        if not target_platforms:
            raise ValueError("target_platforms must contain at least one platform")

        # STEP 1: Retrieve memory context (Mem0 + Qdrant + campaign history)
        logger.info("Retrieving memory context for supervisor decision...")
        memory_context = await _retrieve_supervisor_context(
            tenant_id=tenant_id,
            agent_id=agent_id,
            thread_id=thread_id,
            user_request=user_request
        )

        # STEP 2: LLM-based routing decision with structured output
        logger.info("Using LLM to analyze request and make routing decision...")
        decision = await _make_supervisor_decision(
            user_request=user_request,
            memory_context=memory_context,
            target_platforms=target_platforms
        )

        # Log decision
        logger.info(
            f"Supervisor decision: action={decision.action}, "
            f"confidence={decision.confidence:.2f}, "
            f"reasoning={decision.reasoning}"
        )

        # STEP 3: Handle different actions
        if decision.action == "reject":
            logger.warning(f"Request rejected: {decision.rejection_reason}")
            return {
                **update_workflow_phase(state, "supervisor", "rejected"),
                "error_message": decision.rejection_reason,
                "supervisor_decision": decision.model_dump(),
                "workflow_status": "rejected"
            }

        if decision.action == "clarify":
            logger.info(f"Clarification needed: {decision.clarification_needed}")
            return {
                **update_workflow_phase(state, "supervisor", "needs_clarification"),
                "clarification_prompt": decision.clarification_needed,
                "supervisor_decision": decision.model_dump(),
                "workflow_status": "awaiting_input"
            }

        # STEP 4: Check cost limits (for create_content action)
        cost_check_passed = await _check_cost_limits(tenant_id, cost_limit_usd)

        if not cost_check_passed:
            logger.warning(f"Cost limit exceeded for workflow: {state.get('workflow_id')}")
            return {
                **update_workflow_phase(state, "supervisor", "failed"),
                "error_message": "Daily or per-workflow cost limit exceeded",
                "cost_check_passed": False,
                "supervisor_decision": decision.model_dump()
            }

        # STEP 5: Route to ContentCreationAgent
        logger.info(
            f"SupervisorAgent completed: routing to content_creation, "
            f"topic={decision.extracted_topic}, "
            f"audience={decision.target_audience}, "
            f"platforms: {target_platforms}"
        )

        return {
            **update_workflow_phase(state, "content_creation", "running"),
            "supervisor_decision": decision.model_dump(),
            "extracted_topic": decision.extracted_topic,
            "target_audience": decision.target_audience,
            "content_style": decision.content_style,
            "similar_campaigns": decision.similar_campaigns,
            "memory_context": memory_context,
            "cost_check_passed": True,
            "routing_decision": "content_creation",
            "cost_breakdown": state.get("cost_breakdown", {}),
            "total_cost_usd": 0.0
        }

    except Exception as e:
        logger.error(f"SupervisorAgent failed: {e}", exc_info=True)
        return {
            **update_workflow_phase(state, "supervisor", "failed"),
            "error_message": str(e),
            "workflow_status": "failed"
        }


# =============================================================================
# Memory Context Retrieval
# =============================================================================

async def _retrieve_supervisor_context(
    tenant_id: str,
    agent_id: str,
    thread_id: str,
    user_request: str
) -> Dict[str, Any]:
    """
    Retrieve comprehensive memory context for supervisor decision.

    Retrieves:
    1. Semantic memories from Mem0 (agent learnings, preferences)
    2. Conversation history from Qdrant (recent thread messages)
    3. Campaign history from Qdrant (past successful campaigns)

    Args:
        tenant_id: Tenant identifier
        agent_id: Agent identifier
        thread_id: Thread identifier
        user_request: Current user request

    Returns:
        Dict with memory context data
    """
    try:
        # Initialize memory manager
        memory = MemoryManager(
            tenant_id=tenant_id,
            agent_id=agent_id
        )

        # Get agent context (Mem0 + Qdrant search)
        agent_context = await memory.get_agent_context(
            user_input=user_request,
            session_id=thread_id,
            k=5
        )

        # Get campaign history (past workflows)
        campaigns = await memory.get_campaigns_by_tenant(limit=10)

        # Extract campaign summaries
        campaign_summaries = []
        for campaign in campaigns[:5]:  # Top 5 most recent
            campaign_summaries.append({
                "timestamp": campaign.get("timestamp", ""),
                "content": campaign.get("content", "")[:200],  # Truncate
                "session_id": campaign.get("session_id", "")
            })

        logger.info(
            f"Retrieved memory context: "
            f"{len(agent_context.get('retrieved_memories', []))} memories, "
            f"{len(agent_context.get('recent_messages', []))} messages, "
            f"{len(campaigns)} campaigns"
        )

        return {
            "semantic_memories": agent_context.get("retrieved_memories", []),
            "recent_messages": agent_context.get("recent_messages", []),
            "campaign_history": campaign_summaries,
            "confidence_score": agent_context.get("confidence_score", 0.0)
        }

    except Exception as e:
        logger.error(f"Failed to retrieve supervisor context: {e}")
        # Return empty context on failure
        return {
            "semantic_memories": [],
            "recent_messages": [],
            "campaign_history": [],
            "confidence_score": 0.0
        }


# =============================================================================
# LLM-based Decision Making
# =============================================================================

async def _make_supervisor_decision(
    user_request: str,
    memory_context: Dict[str, Any],
    target_platforms: List[str]
) -> SupervisorDecision:
    """
    Use LLM to analyze request and make routing decision.

    This replaces simple keyword matching with intelligent LLM analysis.

    Args:
        user_request: User's content request
        memory_context: Retrieved memory context
        target_platforms: Target platforms (tiktok, youtube_shorts)

    Returns:
        SupervisorDecision with structured output
    """
    try:
        # Initialize LLM with structured output
        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.3,  # Low temperature for consistent routing
            api_key=settings.OPENAI_API_KEY
        )
        llm_with_structure = llm.with_structured_output(SupervisorDecision)

        # Build memory context string
        memory_str = _format_memory_context(memory_context)

        # Build system prompt
        system_prompt = f"""You are a Supervisor Agent for an AI content creation system.

Your job is to analyze user requests for video content creation and make intelligent routing decisions.

**Available Actions:**
1. create_content - Proceed with content creation
2. clarify - Request more information from user
3. reject - Reject invalid/inappropriate requests

**Memory Context (Past Campaigns & Conversations):**
{memory_str}

**Target Platforms:** {', '.join(target_platforms)}

**Your Task:**
Analyze the user's request and memory context to:
1. Determine if the request is valid and clear
2. Extract topic, audience, and content style
3. Reference similar past campaigns if relevant
4. Decide which action to take

Be intelligent but concise. Reject only truly problematic requests. Ask for clarification only when necessary."""

        # Build user message
        user_message = f"""User Request: "{user_request}"

Analyze this request and provide your routing decision."""

        # Invoke LLM
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]

        decision = await llm_with_structure.ainvoke(messages)

        logger.info(f"LLM supervisor decision: {decision.action} (confidence: {decision.confidence:.2f})")

        return decision

    except Exception as e:
        logger.error(f"LLM decision making failed: {e}", exc_info=True)
        # Fallback: Default to create_content with low confidence
        return SupervisorDecision(
            action="create_content",
            reasoning="Fallback decision due to LLM error",
            confidence=0.3,
            extracted_topic="General",
            target_audience="general",
            content_style="informative",
            similar_campaigns=[]
        )


def _format_memory_context(memory_context: Dict[str, Any]) -> str:
    """
    Format memory context for LLM consumption.

    Args:
        memory_context: Memory context dict

    Returns:
        Formatted string for prompt
    """
    lines = []

    # Recent campaigns
    campaigns = memory_context.get("campaign_history", [])
    if campaigns:
        lines.append("Recent Campaigns:")
        for i, campaign in enumerate(campaigns[:3], 1):
            timestamp = campaign.get("timestamp", "unknown")
            content = campaign.get("content", "")
            lines.append(f"  {i}. [{timestamp}] {content}")

    # Recent conversation
    recent_msgs = memory_context.get("recent_messages", [])
    if recent_msgs:
        lines.append("\nRecent Conversation:")
        for msg in recent_msgs[-5:]:  # Last 5 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:100]  # Truncate
            lines.append(f"  {role}: {content}")

    # Semantic memories
    memories = memory_context.get("semantic_memories", [])
    if memories:
        lines.append("\nLearned Facts:")
        for mem in memories[:3]:
            content = mem.get("content", "")
            score = mem.get("score", 0.0)
            lines.append(f"  - {content} (relevance: {score:.2f})")

    if not lines:
        return "(No prior context available)"

    return "\n".join(lines)


async def _check_cost_limits(
    tenant_id: str,
    per_workflow_limit: float
) -> bool:
    """
    Check if cost limits are within bounds.

    Checks:
    1. Daily cost limit for tenant
    2. Per-workflow cost limit

    Args:
        tenant_id: Tenant identifier
        per_workflow_limit: Max cost for this workflow

    Returns:
        True if within limits, False otherwise
    """
    # TODO: Query database for actual costs
    # For now, always return True (assume within limits)

    # Pseudo-code for future implementation:
    # daily_cost = await get_daily_cost(tenant_id, date.today())
    # if daily_cost >= settings.MAX_DAILY_COST_USD:
    #     return False
    #
    # if per_workflow_limit > settings.MAX_PER_WORKFLOW_COST_USD:
    #     return False

    return True


async def aggregate_results_node(state: VideoWorkflowState) -> Dict[str, Any]:
    """
    Aggregate results from platform agents (optional final node).

    This node can be added after TikTok and YouTube agents complete
    to aggregate their results and finalize the workflow.

    Args:
        state: Current workflow state

    Returns:
        Dict with aggregated results
    """
    logger.info(f"Aggregating results for workflow: {state.get('workflow_id')}")

    # Get publishing results
    publish_results = state.get("publish_results", {})

    # Count successes
    success_count = sum(
        1 for platform_result in publish_results.values()
        if platform_result.get("status") == "success"
    )

    # Calculate total cost
    total_cost = state.get("total_cost_usd", 0.0)

    # Determine final status
    if success_count == 0:
        final_status = "failed"
    elif success_count == len(state.get("target_platforms", [])):
        final_status = "completed"
    else:
        final_status = "partial_success"

    logger.info(
        f"Workflow aggregation complete: {success_count}/{len(state.get('target_platforms', []))} "
        f"platforms successful, total cost: ${total_cost:.2f}"
    )

    return {
        **update_workflow_phase(state, "completed", final_status),
        "workflow_status": final_status,
        "completed_at": datetime.utcnow().isoformat()
    }
