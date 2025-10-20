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

Pattern adapted from supervisor_READONLY_AGENTEXMPL.py:
- Agent JSON contract as source of truth for prompts
- ChatPromptTemplate with history and placeholders
- Unified response processor for memory injection
- Structured output for transparent routing decisions
"""

from typing import Dict, Any, Literal, List
import logging
from datetime import datetime
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)

from backend.state.state_schema import VideoWorkflowState, update_workflow_phase
from backend.config import get_settings
from backend.memory import MemoryManager

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# Structured Output Models for LLM-based Routing
# =============================================================================

class SupervisorDecision(BaseModel):
    """
    Structured output for supervisor routing decisions.

    LLM returns this schema to make routing transparent and debuggable.

    This is the standardized JSON contract for agent responses.
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


# =============================================================================
# LangChain Prompt Template & Chain (Contract-Driven Pattern)
# =============================================================================

def create_supervisor_chain(
    agent_config: Dict[str, Any],
    memory_context: Dict[str, Any],
    cost_info: Dict[str, float]
) -> tuple[ChatPromptTemplate, Any]:
    """
    Create LangChain prompt template and chain from agent JSON contract.

    This function implements the pattern from supervisor_READONLY_AGENTEXMPL.py:
    1. Load system prompt from agent contract
    2. Format with current context (memory, cost, etc.)
    3. Build ChatPromptTemplate with history support
    4. Create chain: prompt_template | llm

    Args:
        agent_config: Agent configuration from registry (JSON contract)
        memory_context: Memory context dict (campaigns, messages, etc.)
        cost_info: Cost tracking info (daily_cost_usd, max_daily_cost_usd, etc.)

    Returns:
        Tuple of (prompt_template, chain)
    """
    # Get base system prompt from agent contract
    system_prompt_template = agent_config.get("prompt_template", {}).get("system", "")

    if not system_prompt_template:
        raise ValueError(f"Agent config missing prompt_template.system")

    # Format memory context
    memory_str = _format_memory_context(memory_context)
    campaign_history_str = _format_campaign_history(memory_context.get("campaign_history", []))

    # Format system prompt with current context
    system_prompt = system_prompt_template.format(
        memory_context=memory_str,
        campaign_history=campaign_history_str,
        daily_cost_usd=cost_info.get("daily_cost_usd", 0.0),
        max_daily_cost_usd=cost_info.get("max_daily_cost_usd", 50.0),
        cost_limit_usd=cost_info.get("cost_limit_usd", 5.0)
    )

    # Build ChatPromptTemplate with history support
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_prompt),
        MessagesPlaceholder(variable_name="history"),
        HumanMessagePromptTemplate.from_template("{user_input}")
    ])

    # Create LLM with structured output
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.3,
        api_key=settings.OPENAI_API_KEY
    )
    llm_with_structure = llm.with_structured_output(SupervisorDecision)

    # Create chain
    chain = prompt_template | llm_with_structure

    logger.info(f"Created supervisor chain with {len(system_prompt)} char system prompt")

    return prompt_template, chain


def process_supervisor_response(
    user_input: str,
    decision: SupervisorDecision,
    memory_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Unified response processor for supervisor decisions.

    This function implements the pattern from supervisor_READONLY_AGENTEXMPL.py:
    - process_ai_response(user_input, ai_response)
    - inject_relevant_url(user_input, ai_response)

    In our case, we inject memory context, campaign references, and
    generate user-friendly chat responses.

    Args:
        user_input: Original user request
        decision: SupervisorDecision from LLM
        memory_context: Retrieved memory context

    Returns:
        Dict with processed response data
    """
    try:
        # Generate conversational chat response
        chat_response = _generate_chat_response_from_decision(
            decision=decision,
            user_input=user_input,
            memory_context=memory_context
        )

        # Inject memory references if available
        chat_response = _inject_memory_references(chat_response, memory_context)

        return {
            "chat_response": chat_response,
            "decision": decision.model_dump(),
            "memory_injected": True,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error processing supervisor response: {e}", exc_info=True)
        # Fallback to basic response
        return {
            "chat_response": f"Processing your request: {user_input}",
            "decision": decision.model_dump(),
            "memory_injected": False,
            "error": str(e)
        }


def _inject_memory_references(response: str, memory_context: Dict[str, Any]) -> str:
    """
    Inject memory references into response (similar to inject_relevant_url).

    This adds contextual references to past campaigns, user preferences, etc.

    Args:
        response: Original response text
        memory_context: Memory context with campaigns and preferences

    Returns:
        Response with memory references injected
    """
    campaigns = memory_context.get("campaign_history", [])

    # If there are relevant campaigns, add reference
    if campaigns and "similar" in response.lower():
        latest_campaign = campaigns[0]
        timestamp = latest_campaign.get("timestamp", "recently")
        response += f"\n\n_Reference: Your campaign from {timestamp} is similar._"

    return response


async def supervisor_node(state: VideoWorkflowState) -> Dict[str, Any]:
    """
    SupervisorAgent (Enhanced with LangChain Pattern).

    Implements contract-driven prompt template pattern from supervisor_READONLY_AGENTEXMPL.py:
    1. Load agent config from JSON contract
    2. Create ChatPromptTemplate with history support
    3. Build chain: prompt_template | llm
    4. Invoke chain with user_input and conversation history
    5. Process response with unified response processor

    Responsibilities:
    - Retrieve memory context (past campaigns, conversation history)
    - Use LLM chain to analyze request + make routing decision
    - Check cost limits (daily + per-workflow)
    - Route to ContentCreationAgent or return clarification/rejection

    Args:
        state: Current workflow state

    Returns:
        Dict with state updates to merge
    """
    try:
        logger.info(f"SupervisorAgent (LangChain pattern) started for workflow: {state.get('workflow_id')}")

        # Extract input
        user_request = state.get("user_request", "")
        target_platforms = state.get("target_platforms", ["tiktok", "youtube_shorts"])
        cost_limit_usd = state.get("cost_limit_usd", settings.MAX_PER_WORKFLOW_COST_USD)
        tenant_id = state.get("tenant_id", "default-tenant")
        agent_id = "supervisor_agent"
        thread_id = state.get("thread_id", "default-thread")

        # Validate input
        if not user_request:
            raise ValueError("user_request is required")

        if not target_platforms:
            raise ValueError("target_platforms must contain at least one platform")

        # STEP 1: Load agent config from registry (JSON contract)
        from backend.agents.registry import get_agent_registry
        registry = get_agent_registry()
        agent_config = registry.get_agent(agent_id)

        if not agent_config:
            raise ValueError(f"Agent config not found for: {agent_id}")

        # STEP 2: Retrieve memory context (Mem0 + Qdrant + campaign history)
        logger.info("Retrieving memory context for supervisor decision...")
        memory_context = await _retrieve_supervisor_context(
            tenant_id=tenant_id,
            agent_id=agent_id,
            thread_id=thread_id,
            user_request=user_request
        )

        # STEP 3: Get cost tracking info
        cost_info = {
            "daily_cost_usd": 0.0,  # TODO: Get from DB
            "max_daily_cost_usd": settings.MAX_DAILY_COST_USD,
            "cost_limit_usd": cost_limit_usd
        }

        # STEP 4: Create LangChain prompt template and chain
        prompt_template, chain = create_supervisor_chain(
            agent_config=agent_config,
            memory_context=memory_context,
            cost_info=cost_info
        )

        # STEP 5: Prepare conversation history
        messages_history = state.get("messages", [])
        history = [
            HumanMessage(content=msg["content"]) if msg["role"] == "user"
            else SystemMessage(content=msg["content"])
            for msg in messages_history[-10:]  # Last 10 messages
        ]

        # STEP 6: Invoke chain with user_input and history
        logger.info(f"Invoking supervisor chain with user_input: {user_request[:100]}...")
        decision = await chain.ainvoke({
            "user_input": user_request,
            "history": history
        })

        # Log decision
        logger.info(
            f"Supervisor decision: action={decision.action}, "
            f"confidence={decision.confidence:.2f}, "
            f"reasoning={decision.reasoning}"
        )

        # STEP 7: Process response with unified response processor
        processed = process_supervisor_response(
            user_input=user_request,
            decision=decision,
            memory_context=memory_context
        )

        chat_response = processed["chat_response"]

        # Add supervisor message to thread
        messages_history.append({
            "role": "supervisor",
            "content": chat_response,
            "timestamp": datetime.utcnow().isoformat(),
            "decision": decision.action
        })

        # STEP 8: Handle different actions
        if decision.action == "reject":
            logger.warning(f"Request rejected: {decision.rejection_reason}")
            return {
                **update_workflow_phase(state, "supervisor", "rejected"),
                "error_message": decision.rejection_reason,
                "supervisor_decision": decision.model_dump(),
                "workflow_status": "rejected",
                "messages": messages_history,
                "processed_response": processed
            }

        if decision.action == "clarify":
            logger.info(f"Clarification needed: {decision.clarification_needed}")
            return {
                **update_workflow_phase(state, "supervisor", "needs_clarification"),
                "clarification_prompt": decision.clarification_needed,
                "supervisor_decision": decision.model_dump(),
                "workflow_status": "awaiting_input",
                "messages": messages_history,
                "processed_response": processed
            }

        # STEP 9: Check cost limits (for create_content action)
        cost_check_passed = await _check_cost_limits(tenant_id, cost_limit_usd)

        if not cost_check_passed:
            logger.warning(f"Cost limit exceeded for workflow: {state.get('workflow_id')}")
            return {
                **update_workflow_phase(state, "supervisor", "failed"),
                "error_message": "Daily or per-workflow cost limit exceeded",
                "cost_check_passed": False,
                "supervisor_decision": decision.model_dump(),
                "messages": messages_history,
                "processed_response": processed
            }

        # STEP 10: Route to ContentCreationAgent
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
            "total_cost_usd": 0.0,
            "messages": messages_history,
            "processed_response": processed
        }

    except Exception as e:
        logger.error(f"SupervisorAgent failed: {e}", exc_info=True)

        # Apply safe_node_execution pattern manually
        from backend.graph.error_recovery import create_error_state
        return create_error_state(
            phase="supervisor",
            error=e,
            state=state
        )


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
# Helper Functions for Response Generation
# =============================================================================

def _generate_chat_response_from_decision(
    decision: SupervisorDecision,
    user_input: str,
    memory_context: Dict[str, Any]
) -> str:
    """
    Generate a conversational chat response for the user.

    This creates a natural, human-friendly response from the structured
    decision output.

    Args:
        decision: Supervisor decision object
        user_input: Original user request
        memory_context: Memory context with campaign history

    Returns:
        Conversational response string
    """
    # Get similar campaigns for context
    campaigns = memory_context.get("campaign_history", [])
    has_similar = len(decision.similar_campaigns) > 0

    if decision.action == "reject":
        return f"I cannot proceed with this request. {decision.rejection_reason}"

    if decision.action == "clarify":
        return f"{decision.clarification_needed}"

    # create_content action - provide detailed explanation
    response_parts = []

    # Main confirmation
    response_parts.append(
        f"Perfect! I'll create a {decision.content_style} video about **{decision.extracted_topic}**, "
        f"targeting {decision.target_audience}."
    )

    # Reference similar campaigns if available
    if has_similar and campaigns:
        response_parts.append(
            f"\n\nThis is similar to your previous campaign from {campaigns[0].get('timestamp', 'recently')}. "
            f"I'll use those insights to optimize this content."
        )

    # Explain workflow
    response_parts.append(
        f"\n\n**Here's what I'll do:**\n"
        f"1. Generate a platform-optimized script using Claude AI\n"
        f"2. Create the video using PiAPI (AI voiceover + visuals + captions)\n"
        f"3. Publish to the target platform(s)\n"
    )

    # Cost estimate
    response_parts.append(f"\n**Estimated cost:** ~$0.30-0.50 for the complete workflow")

    # Confidence indicator
    if decision.confidence < 0.7:
        response_parts.append(
            f"\n\n_Note: I'm {int(decision.confidence * 100)}% confident about this interpretation. "
            f"Let me know if I misunderstood anything._"
        )

    response_parts.append(f"\n\nRouting to ContentCreationAgent now... 🚀")

    return "".join(response_parts)


def _format_memory_context(memory_context: Dict[str, Any]) -> str:
    """
    Format memory context for LLM consumption.

    Args:
        memory_context: Memory context dict

    Returns:
        Formatted string for prompt
    """
    lines = []

    # Recent conversation
    recent_msgs = memory_context.get("recent_messages", [])
    if recent_msgs:
        lines.append("Recent Conversation:")
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


def _format_campaign_history(campaigns: List[Dict[str, Any]]) -> str:
    """
    Format campaign history for LLM consumption.

    Args:
        campaigns: List of campaign dicts

    Returns:
        Formatted string for prompt
    """
    if not campaigns:
        return "(No campaign history available)"

    lines = ["Recent Campaigns:"]
    for i, campaign in enumerate(campaigns[:5], 1):
        timestamp = campaign.get("timestamp", "unknown")
        content = campaign.get("content", "")[:150]  # Truncate
        lines.append(f"  {i}. [{timestamp}] {content}")

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
    try:
        from sqlalchemy import select, func
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from backend.db.models import WorkflowRun
        from datetime import date, datetime

        # Create async engine
        engine = create_async_engine(settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
        async_session = async_sessionmaker(engine, expire_on_commit=False)

        async with async_session() as session:
            # Get today's date range
            today_start = datetime.combine(date.today(), datetime.min.time())
            today_end = datetime.combine(date.today(), datetime.max.time())

            # Query total cost for tenant today
            result = await session.execute(
                select(func.coalesce(func.sum(WorkflowRun.total_cost_usd), 0.0))
                .where(
                    WorkflowRun.tenant_id == tenant_id,
                    WorkflowRun.created_at >= today_start,
                    WorkflowRun.created_at <= today_end
                )
            )
            daily_cost = result.scalar() or 0.0

            # Check daily limit
            if daily_cost >= settings.MAX_DAILY_COST_USD:
                logger.warning(
                    f"Daily cost limit exceeded for tenant {tenant_id}: "
                    f"${daily_cost:.2f} / ${settings.MAX_DAILY_COST_USD:.2f}"
                )
                return False

            # Check per-workflow limit
            if per_workflow_limit > settings.MAX_PER_WORKFLOW_COST_USD:
                logger.warning(
                    f"Per-workflow limit too high: ${per_workflow_limit:.2f} > "
                    f"${settings.MAX_PER_WORKFLOW_COST_USD:.2f}"
                )
                return False

            # Check if this workflow would exceed daily limit
            if (daily_cost + per_workflow_limit) > settings.MAX_DAILY_COST_USD:
                logger.warning(
                    f"Workflow would exceed daily limit: "
                    f"${daily_cost:.2f} + ${per_workflow_limit:.2f} > "
                    f"${settings.MAX_DAILY_COST_USD:.2f}"
                )
                return False

            logger.info(
                f"Cost check passed for tenant {tenant_id}: "
                f"Daily: ${daily_cost:.2f}/{settings.MAX_DAILY_COST_USD:.2f}, "
                f"Workflow: ${per_workflow_limit:.2f}/{settings.MAX_PER_WORKFLOW_COST_USD:.2f}"
            )
            return True

    except Exception as e:
        logger.error(f"Error checking cost limits: {e}", exc_info=True)
        # On error, allow workflow (fail-open for availability)
        logger.warning("Cost check failed, allowing workflow to proceed")
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
