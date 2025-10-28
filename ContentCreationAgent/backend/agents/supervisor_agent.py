"""
SupervisorAgent V2 - Conversational-First with Memory Integration

Enhanced supervisor that acts as:
1. Conversational AI expert in content strategy (PRIMARY MODE)
2. Workflow orchestrator when user explicitly requests creation (SECONDARY MODE)

Key improvements:
- Dynamic LLM conversations using JSON contract identity
- Thread + persistent memory integration
- Structured decisions ONLY when needed for workflows
- Expert knowledge in social media content creation
"""

from typing import Dict, Any, Optional, List, Literal
import logging
from datetime import datetime
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableParallel
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain.callbacks.tracers import LangChainTracer

from backend.state.state_schema import VideoWorkflowState, update_workflow_phase
from backend.config import get_settings
from backend.memory import MemoryManager
from backend.graph.error_recovery import safe_node_execution

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# Pydantic Models
# =============================================================================

class ConversationalResponse(BaseModel):
    """Response for general conversation (no workflow creation)"""
    response_type: Literal["conversation"] = "conversation"
    message: str = Field(description="Natural language response to user")
    references_memory: bool = Field(default=False, description="Whether response used memory context")
    suggestions: Optional[List[str]] = Field(default=None, description="Optional suggestions or next steps")


class WorkflowDecision(BaseModel):
    """Structured decision for workflow creation"""
    response_type: Literal["workflow_creation"] = "workflow_creation"
    action: Literal["create_content", "clarify", "reject"]
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)

    # Content details (for create_content)
    extracted_topic: Optional[str] = None
    target_audience: Optional[str] = None
    content_style: Optional[str] = None
    recommended_platforms: Optional[List[str]] = None

    # Clarification (for clarify)
    clarification_needed: Optional[str] = None

    # Rejection (for reject)
    rejection_reason: Optional[str] = None

    # User-facing message
    message: str = Field(description="Natural language explanation of the decision")


# =============================================================================
# Main Supervisor Node (Conversational-First)
# =============================================================================

@safe_node_execution("supervisor_v2")
async def supervisor_node_conversational(state: VideoWorkflowState) -> Dict[str, Any]:
    """
    SupervisorAgent V2 - Conversational-first with dynamic LLM responses.

    Flow:
    1. Retrieve memory context (thread + persistent)
    2. Determine if user wants conversation OR workflow creation
    3. Generate appropriate response:
       - Conversation: Dynamic LLM chat response
       - Workflow: Structured decision + delegation
    4. Store interaction in memory

    Args:
        state: Current workflow state

    Returns:
        Dict with state updates
    """
    try:
        logger.info(f"SupervisorAgent V2 (conversational) started")

        # Extract inputs
        user_request = state.get("user_request", "")
        thread_id = state.get("thread_id", "default-thread")
        tenant_id = state.get("tenant_id", "default-tenant")
        agent_id = "supervisor_agent"

        if not user_request:
            raise ValueError("user_request is required")

        # STEP 1: Retrieve memory context
        logger.info("Retrieving memory context...")
        memory_manager = MemoryManager(tenant_id=tenant_id, agent_id=agent_id)

        memory_context = await memory_manager.get_agent_context(
            user_input=user_request,
            session_id=thread_id,
            k=5
        )

        # STEP 2: Determine response mode (conversation vs workflow)
        response_mode = await _determine_response_mode(user_request, memory_context)

        logger.info(f"Response mode: {response_mode}")

        # STEP 3: Generate appropriate response
        if response_mode == "conversation":
            # Store user message FIRST so LLM can see it in thread context
            memory_manager.append_thread(thread_id, "user", user_request)

            # Generate dynamic conversational response with updated thread context
            response = await _generate_conversational_response(
                user_request=user_request,
                memory_context=memory_context,
                thread_id=thread_id,
                tenant_id=tenant_id
            )

            # Store assistant response after generation
            memory_manager.append_thread(thread_id, "assistant", response.message)

            # Return conversational state (no workflow created)
            return {
                **update_workflow_phase(state, "supervisor", "conversation"),
                "supervisor_response": response.message,
                "response_type": "conversation",
                "workflow_status": "conversation",  # Not creating a workflow
                "messages": state.get("messages", []) + [{
                    "role": "assistant",
                    "content": response.message,
                    "timestamp": datetime.utcnow().isoformat()
                }]
            }

        else:  # workflow_creation mode
            # Generate structured workflow decision
            decision = await _make_workflow_decision(
                user_request=user_request,
                memory_context=memory_context,
                target_platforms=state.get("target_platforms", ["tiktok"])
            )

            # Store decision in memory (synchronous method - no await)
            memory_manager.append_thread(thread_id, "user", user_request)
            memory_manager.append_thread(thread_id, "assistant", decision.message)

            # Handle workflow actions
            if decision.action == "create_content":
                logger.info(f"Creating workflow for: {decision.extracted_topic}")
                return {
                    **update_workflow_phase(state, "supervisor", "approved"),
                    "supervisor_response": decision.message,
                    "supervisor_decision": decision.model_dump(),
                    "parsed_intent": {
                        "topic": decision.extracted_topic,
                        "audience": decision.target_audience,
                        "style": decision.content_style
                    },
                    "workflow_status": "active",
                    "messages": state.get("messages", []) + [{
                        "role": "assistant",
                        "content": decision.message,
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }

            elif decision.action == "clarify":
                logger.info("Requesting clarification from user")
                return {
                    **update_workflow_phase(state, "supervisor", "needs_clarification"),
                    "supervisor_response": decision.message,
                    "clarification_prompt": decision.clarification_needed,
                    "workflow_status": "awaiting_input",
                    "messages": state.get("messages", []) + [{
                        "role": "assistant",
                        "content": decision.message,
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }

            else:  # reject
                logger.warning(f"Request rejected: {decision.rejection_reason}")
                return {
                    **update_workflow_phase(state, "supervisor", "rejected"),
                    "supervisor_response": decision.message,
                    "error_message": decision.rejection_reason,
                    "workflow_status": "rejected",
                    "messages": state.get("messages", []) + [{
                        "role": "assistant",
                        "content": decision.message,
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                }

    except Exception as e:
        logger.error(f"Supervisor V2 error: {e}", exc_info=True)
        return {
            **update_workflow_phase(state, "supervisor", "error"),
            "error_message": f"Supervisor error: {str(e)}",
            "workflow_status": "error"
        }


# =============================================================================
# Response Mode Detection
# =============================================================================

async def _determine_response_mode(
    user_request: str,
    memory_context: Dict[str, Any]
) -> Literal["conversation", "workflow_creation"]:
    """
    Determine if user wants conversation or workflow creation.

    Workflow keywords: create, make, generate, build, produce, publish
    Everything else: Conversation

    Args:
        user_request: User's message
        memory_context: Memory context

    Returns:
        "conversation" or "workflow_creation"
    """
    user_lower = user_request.lower()

    # Explicit workflow creation keywords
    workflow_keywords = [
        "create a", "make a", "generate a", "build a", "produce a",
        "create video", "make video", "generate content",
        "publish to", "post to", "upload to"
    ]

    for keyword in workflow_keywords:
        if keyword in user_lower:
            logger.info(f"Detected workflow keyword: '{keyword}'")
            return "workflow_creation"

    # Default to conversation
    logger.info("No workflow keywords detected - using conversational mode")
    return "conversation"


# =============================================================================
# Conversational Response Generation
# =============================================================================

# =============================================================================
# LangChain Conversation History Store (INTEGRATED WITH MEMORY MANAGER)
# =============================================================================

class MemoryManagerChatHistory(BaseChatMessageHistory):
    """
    Custom chat history that bridges LangChain to MemoryManager thread context.

    This ensures conversation history is consistent across:
    - LangChain RunnableWithMessageHistory
    - MemoryManager thread context
    - Database persistence
    """

    def __init__(self, session_id: str, memory_manager: MemoryManager):
        self.session_id = session_id
        self.memory_manager = memory_manager

    @property
    def messages(self) -> List:
        """Get messages from MemoryManager thread context"""
        thread_context = self.memory_manager.get_thread_context(self.session_id)

        # Convert to LangChain message objects
        langchain_messages = []
        for msg in thread_context:
            if msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))

        return langchain_messages

    def add_message(self, message) -> None:
        """Add message to MemoryManager (handled separately - no-op here)"""
        # Messages are already being added via memory_manager.append_thread()
        # in the supervisor_node_conversational function
        pass

    def clear(self) -> None:
        """Clear history (not implemented - thread context is persistent)"""
        pass


# Global memory managers cache for session history
_memory_managers_cache = {}


def get_session_history(session_id: str, tenant_id: str = "default-tenant") -> BaseChatMessageHistory:
    """
    Get chat history from MemoryManager for session.

    This bridges LangChain's RunnableWithMessageHistory to our MemoryManager.
    """
    cache_key = f"{tenant_id}:{session_id}"

    if cache_key not in _memory_managers_cache:
        # Create memory manager for this session
        memory_manager = MemoryManager(tenant_id=tenant_id, agent_id="supervisor")
        _memory_managers_cache[cache_key] = memory_manager

    memory_manager = _memory_managers_cache[cache_key]
    return MemoryManagerChatHistory(session_id, memory_manager)


async def _generate_conversational_response(
    user_request: str,
    memory_context: Dict[str, Any],
    thread_id: str,
    tenant_id: str = "default-tenant"
) -> ConversationalResponse:
    """
    Generate dynamic conversational response using LLM.

    This is the PRIMARY mode - natural conversation with expert knowledge.

    Args:
        user_request: User's message
        memory_context: Retrieved memory context
        thread_id: Thread ID for conversation history
        tenant_id: Tenant ID for memory isolation

    Returns:
        ConversationalResponse with LLM-generated message
    """
    try:
        # Load supervisor JSON contract
        from backend.agents.registry import get_agent_registry
        registry = get_agent_registry()
        supervisor_config = registry.get_agent("supervisor_agent")

        # Validate registry config structure
        if not supervisor_config:
            logger.error("Supervisor config not found in registry")
            raise ValueError("Invalid supervisor configuration: config not found")

        if "prompt_template" not in supervisor_config:
            logger.error("Missing prompt_template in supervisor config")
            raise ValueError("Invalid supervisor configuration: missing prompt_template")

        if "system" not in supervisor_config.get("prompt_template", {}):
            logger.error("Missing system prompt in supervisor config")
            raise ValueError("Invalid supervisor configuration: missing system prompt template")

        # Get system prompt from contract
        system_prompt_template = supervisor_config["prompt_template"]["system"]

        # Format with memory context
        memory_str = _format_memory_for_prompt(memory_context)
        campaign_history_str = _format_campaign_history(memory_context.get("retrieved_memories", []))

        system_prompt = system_prompt_template.format(
            memory_context=memory_str,
            campaign_history=campaign_history_str,
            daily_cost_usd=0.0,  # TODO: Get from cost tracker
            max_daily_cost_usd=settings.MAX_DAILY_COST_USD,
            cost_limit_usd=settings.MAX_PER_WORKFLOW_COST_USD
        )

        # Add conversational instruction
        system_prompt += "\n\nIMPORTANT: You are in CONVERSATION mode. Provide a natural, helpful, expert response. Do NOT return structured JSON."

        # =================================================================
        # FULL LANGCHAIN IMPLEMENTATION - Using ALL powerful features
        # =================================================================

        # 1. Create ChatPromptTemplate with MessagesPlaceholder
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),  # Shorthand syntax
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")  # LangChain standard variable name
        ])

        # 2. Initialize LLM with trait-based configuration (RVR pattern)
        # Supervisor agent traits (from JSON contract - content strategist profile)
        creativity_trait = 75  # High - creative content strategy
        verbosity_trait = 70   # Detailed - explain strategies thoroughly

        # RVR Formula: temperature from creativity (0-100 → 0.0-1.0)
        temperature = creativity_trait / 100.0

        # RVR Formula: max_tokens from verbosity (80 + verbosity% * 560 = 80-640 range)
        max_tokens = int(80 + (verbosity_trait / 100.0) * 560)

        logger.info(f"Supervisor LLM config (RVR): temp={temperature:.2f}, max_tokens={max_tokens}")

        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=settings.OPENAI_API_KEY,
            streaming=True,  # Enable streaming for better UX
            verbose=True  # Enable debug logging
        )

        # 3. Create Output Parser for clean text extraction
        output_parser = StrOutputParser()

        # 4. Build FULL LangChain chain with composition
        # Chain: Prompt → LLM → Output Parser
        base_chain = prompt | llm | output_parser

        # 5. Add context enrichment with RunnableParallel
        # This runs memory retrieval and user input in parallel
        context_chain = RunnableParallel(
            {
                "input": RunnablePassthrough(),  # Pass input through
                "memory_context": RunnableLambda(
                    lambda x: _format_memory_for_prompt(memory_context)
                ),
                "campaign_data": RunnableLambda(
                    lambda x: _format_campaign_history(
                        memory_context.get("retrieved_memories", [])
                    )
                )
            }
        )

        # 6. Wrap with RunnableWithMessageHistory for automatic history management
        chain_with_history = RunnableWithMessageHistory(
            base_chain,
            get_session_history,
            input_messages_key="input",
            history_messages_key="history"
        )

        # 7. Configure session for history tracking with tenant isolation
        # Custom get_session_history function that uses tenant_id
        def get_history_for_this_session(session_id: str) -> BaseChatMessageHistory:
            return get_session_history(session_id, tenant_id)

        # Update chain to use custom history function
        chain_with_history = RunnableWithMessageHistory(
            base_chain,
            get_history_for_this_session,  # Use closure with tenant_id
            input_messages_key="input",
            history_messages_key="history"
        )

        config = {
            "configurable": {"session_id": thread_id},
            "callbacks": [],  # LangSmith tracer can be added here
            "tags": ["supervisor", "conversational", "v2"],
            "metadata": {
                "agent": "supervisor_agent",
                "mode": "conversation",
                "thread_id": thread_id,
                "tenant_id": tenant_id
            }
        }

        # 8. Invoke the FULL chain with all LangChain features
        response_text = await chain_with_history.ainvoke(
            {"input": user_request},
            config=config
        )

        logger.info(f"Generated conversational response: {response_text[:100]}...")

        return ConversationalResponse(
            message=response_text,
            references_memory=len(memory_context.get("retrieved_memories", [])) > 0
        )

    except Exception as e:
        logger.error(f"Conversational response generation failed: {e}", exc_info=True)
        return ConversationalResponse(
            message="I'm here to help with your content strategy! What would you like to know about creating viral TikToks or YouTube Shorts?"
        )


# =============================================================================
# Workflow Decision Generation
# =============================================================================

async def _make_workflow_decision(
    user_request: str,
    memory_context: Dict[str, Any],
    target_platforms: List[str]
) -> WorkflowDecision:
    """
    Generate structured workflow decision when user wants to create content.

    This is SECONDARY mode - only for explicit creation requests.

    Args:
        user_request: User's creation request
        memory_context: Memory context
        target_platforms: Target platforms

    Returns:
        WorkflowDecision with structured output
    """
    try:
        # Load system prompt (same as conversational)
        from backend.agents.registry import get_agent_registry
        registry = get_agent_registry()
        supervisor_config = registry.get_agent("supervisor_agent")

        # Validate registry config structure
        if not supervisor_config:
            logger.error("Supervisor config not found in registry")
            raise ValueError("Invalid supervisor configuration: config not found")

        if "prompt_template" not in supervisor_config:
            logger.error("Missing prompt_template in supervisor config")
            raise ValueError("Invalid supervisor configuration: missing prompt_template")

        if "system" not in supervisor_config.get("prompt_template", {}):
            logger.error("Missing system prompt in supervisor config")
            raise ValueError("Invalid supervisor configuration: missing system prompt template")

        system_prompt_template = supervisor_config["prompt_template"]["system"]

        memory_str = _format_memory_for_prompt(memory_context)
        campaign_history_str = _format_campaign_history(memory_context.get("retrieved_memories", []))

        system_prompt = system_prompt_template.format(
            memory_context=memory_str,
            campaign_history=campaign_history_str,
            daily_cost_usd=0.0,
            max_daily_cost_usd=settings.MAX_DAILY_COST_USD,
            cost_limit_usd=settings.MAX_PER_WORKFLOW_COST_USD
        )

        # Add workflow decision instruction
        system_prompt += f"\n\nIMPORTANT: You are in WORKFLOW CREATION mode. Analyze this content creation request and return a WorkflowDecision.\nTarget platforms: {', '.join(target_platforms)}"

        # =================================================================
        # FULL LANGCHAIN IMPLEMENTATION - Structured Output Chain
        # =================================================================

        # 1. Create ChatPromptTemplate with context enrichment
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "User wants to create content: {user_request}\n\nTarget platforms: {platforms}\n\nMemory context: {memory_summary}")
        ])

        # 2. Initialize LLM with trait-based configuration + structured output
        # Use slightly lower creativity for structured decisions (more consistent)
        decision_creativity = 60  # Moderate - balanced analysis
        decision_verbosity = 70   # Detailed reasoning

        # RVR formulas
        temperature = decision_creativity / 100.0
        max_tokens = int(80 + (decision_verbosity / 100.0) * 560)

        logger.info(f"Workflow decision LLM config: temp={temperature:.2f}, max_tokens={max_tokens}")

        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=settings.OPENAI_API_KEY,
            verbose=True
        ).with_structured_output(WorkflowDecision)

        # 3. Build enrichment chain with RunnableParallel
        # Runs data preparation in parallel for efficiency
        enrich_chain = RunnableParallel(
            {
                "user_request": RunnablePassthrough(),
                "platforms": RunnableLambda(lambda x: ', '.join(target_platforms)),
                "memory_summary": RunnableLambda(
                    lambda x: _format_memory_for_prompt(memory_context)[:200]  # Brief summary
                )
            }
        )

        # 4. Compose FULL chain: Enrich → Prompt → LLM → Structured Output
        full_chain = enrich_chain | prompt | llm

        # 5. Configure with metadata for tracking
        config = {
            "callbacks": [],
            "tags": ["supervisor", "workflow_decision", "v2"],
            "metadata": {
                "agent": "supervisor_agent",
                "mode": "workflow_creation",
                "platforms": target_platforms
            }
        }

        # 6. Invoke the FULL chain
        decision = await full_chain.ainvoke(
            user_request,  # Input gets enriched by RunnableParallel
            config=config
        )

        logger.info(f"Workflow decision: action={decision.action}, topic={decision.extracted_topic}")

        return decision

    except Exception as e:
        logger.error(f"Workflow decision failed: {e}", exc_info=True)
        # Fallback decision
        return WorkflowDecision(
            action="clarify",
            reasoning="Unable to parse request due to system error",
            confidence=0.3,
            clarification_needed="I'm having trouble understanding your request. Could you please rephrase what kind of video you'd like to create?",
            message="I'm having trouble understanding your request. Could you please rephrase what kind of video you'd like to create?"
        )


# =============================================================================
# Helper Functions
# =============================================================================

def _format_memory_for_prompt(memory_context: Dict[str, Any]) -> str:
    """Format memory context for LLM prompt"""
    lines = []

    # Recent messages
    recent = memory_context.get("recent_messages", [])
    if recent:
        lines.append("**Recent Conversation:**")
        for msg in recent[-3:]:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:200]
            lines.append(f"- {role}: {content}")

    # Retrieved memories
    memories = memory_context.get("retrieved_memories", [])
    if memories:
        lines.append("\n**Relevant Past Context:**")
        for mem in memories[:3]:
            text = mem.get("memory", mem.get("text", ""))[:200]
            lines.append(f"- {text}")

    return "\n".join(lines) if lines else "No previous context available."


def _format_campaign_history(memories: List[Dict[str, Any]]) -> str:
    """Format campaign history for prompt"""
    if not memories:
        return "No campaign history available."

    campaigns = [m for m in memories if "campaign" in m.get("memory", "").lower() or "video" in m.get("memory", "").lower()]

    if not campaigns:
        return "No campaign history available."

    lines = ["**Past Campaigns:**"]
    for campaign in campaigns[:3]:
        text = campaign.get("memory", campaign.get("text", ""))[:150]
        lines.append(f"- {text}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# CLI TESTING UTILITY
# ═══════════════════════════════════════════════════════════════════════════

async def run_cli_sanity_test():
    """
    CLI sanity test for SupervisorAgent.

    Tests supervisor logic outside of FastAPI for development/debugging.
    Run directly: python -m backend.agents.supervisor_agent

    Test scenarios:
    1. Video request routing
    2. Conversational response
    3. Memory persistence
    4. Error handling
    """
    import asyncio

    print("=" * 80)
    print("SUPERVISOR AGENT CLI SANITY TEST")
    print("=" * 80)
    print()

    # Test 1: Video creation request
    print("Test 1: Video creation request")
    print("-" * 40)
    request_1 = SupervisorRequest(
        session_id="test_session_123",
        user_message="Create a TikTok video about AI trends",
        metadata={}
    )

    try:
        response_1 = await route_supervisor_request(request_1)
        print(f"Response Type: {response_1.response_type}")
        print(f"Message: {response_1.message[:100]}...")

        if response_1.response_type == "workflow_initiated":
            print(f"Workflow ID: {response_1.workflow_id}")
            print(f"Platforms: {response_1.parsed_intent.get('platforms', [])}")
            print("PASS: Video request routed to workflow")
        else:
            print("FAIL: Expected workflow_initiated")
    except Exception as e:
        print(f"FAIL: {e}")
    print()

    # Test 2: Conversational request
    print("Test 2: Conversational request")
    print("-" * 40)
    request_2 = SupervisorRequest(
        session_id="test_session_123",
        user_message="What platforms do you support?",
        metadata={}
    )

    try:
        response_2 = await route_supervisor_request(request_2)
        print(f"Response Type: {response_2.response_type}")
        print(f"Message: {response_2.message[:100]}...")

        if response_2.response_type == "conversational":
            print("PASS: Conversational request handled")
        else:
            print("FAIL: Expected conversational response")
    except Exception as e:
        print(f"FAIL: {e}")
    print()

    # Test 3: Memory recall (same session)
    print("Test 3: Memory recall (same session)")
    print("-" * 40)
    request_3 = SupervisorRequest(
        session_id="test_session_123",
        user_message="What did I just ask you about?",
        metadata={}
    )

    try:
        response_3 = await route_supervisor_request(request_3)
        print(f"Response Type: {response_3.response_type}")
        print(f"Message: {response_3.message[:100]}...")

        # Check if response mentions "platforms" or previous context
        if "platform" in response_3.message.lower():
            print("PASS: Memory recall working")
        else:
            print("WARN: Memory may not be recalling previous context")
    except Exception as e:
        print(f"FAIL: {e}")
    print()

    # Test 4: Invalid request handling
    print("Test 4: Invalid request handling")
    print("-" * 40)
    request_4 = SupervisorRequest(
        session_id="",  # Empty session ID
        user_message="Test",
        metadata={}
    )

    try:
        response_4 = await route_supervisor_request(request_4)
        print(f"Response: {response_4.message}")
        print("WARN: Should validate session_id")
    except Exception as e:
        print(f"Expected error handling: {type(e).__name__}")
    print()

    print("=" * 80)
    print("CLI SANITY TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    """
    Run CLI sanity test when module is executed directly.

    Usage:
        python -m backend.agents.supervisor_agent
    """
    import asyncio
    asyncio.run(run_cli_sanity_test())
