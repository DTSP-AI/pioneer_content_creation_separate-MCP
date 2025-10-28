"""
LangGraph Workflow Orchestrator

This is the SINGLE graph orchestrator for the entire system.
All agents are registered as nodes and wired via edges.

Architecture Compliance:
- AGENT_ORCHESTRATION_STANDARD.md: Single LangGraph orchestration
- StateGraph with VideoWorkflowState
- PostgreSQL checkpointer for state persistence
- MemoryManager for semantic memory
- No custom state machines or loops

Graph Flow:
    supervisor → content_creation → review_gate → [tiktok, youtube_shorts] → END
"""

from typing import Dict, Any, Literal
import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

from backend.state.state_schema import VideoWorkflowState, create_initial_workflow_state
from backend.agents import (
    supervisor_node,
    content_creation_node,
    tiktok_node,
    youtube_shorts_node
)
from backend.graph.review_gate import review_gate_node
from backend.memory.memory_manager import MemoryManager
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def build_content_workflow(
    checkpointer: PostgresSaver = None,
    memory_manager: MemoryManager = None
) -> StateGraph:
    """
    Build the complete content creation & distribution workflow.

    This is the SINGLE graph orchestrator that coordinates all agents:
    1. SupervisorAgent - Entry node, validates, routes
    2. ContentCreationAgent - Generates all content assets
    3. ReviewGateNode - Human-in-the-loop approval checkpoint
    4. TikTokAgent - Publishes to TikTok (parallel)
    5. YouTubeShortsAgent - Publishes to YouTube Shorts (parallel)

    Args:
        checkpointer: PostgreSQL checkpointer for state persistence
        memory_manager: Mem0 memory manager (optional, for testing)

    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("Building content creation workflow graph")

    # Create StateGraph with VideoWorkflowState schema
    workflow = StateGraph(VideoWorkflowState)

    # ========================================================================
    # NODE REGISTRATION
    # ========================================================================

    # Node 1: SupervisorAgent (entry point)
    workflow.add_node("supervisor", supervisor_node)

    # Node 2: ContentCreationAgent (content generation)
    workflow.add_node("content_creation", content_creation_node)

    # Node 3: Review Gate (human approval checkpoint)
    workflow.add_node("review_gate", review_gate_node)

    # Node 4: TikTokAgent (publishing)
    workflow.add_node("tiktok", tiktok_node)

    # Node 5: YouTubeShortsAgent (publishing)
    workflow.add_node("youtube_shorts", youtube_shorts_node)

    # ========================================================================
    # EDGE DEFINITION (Workflow Flow)
    # ========================================================================

    # Set entry point
    workflow.set_entry_point("supervisor")

    # Sequential flow: Supervisor → ContentCreation → Review Gate
    workflow.add_edge("supervisor", "content_creation")
    workflow.add_edge("content_creation", "review_gate")

    # Conditional routing after review approval
    def route_to_platforms(state: VideoWorkflowState) -> list[str]:
        """
        Route to platform agents based on target_platforms.

        Returns list of nodes to execute in parallel.
        """
        target_platforms = state.get("target_platforms", [])
        next_nodes = []

        if "tiktok" in target_platforms:
            next_nodes.append("tiktok")

        if "youtube_shorts" in target_platforms:
            next_nodes.append("youtube_shorts")

        # If no platforms, go to END
        if not next_nodes:
            next_nodes = [END]

        logger.info(f"Routing to platforms: {next_nodes}")
        return next_nodes

    # Conditional fan-out to platform agents (parallel execution)
    workflow.add_conditional_edges(
        "review_gate",
        route_to_platforms
    )

    # Both platform agents go to END
    workflow.add_edge("tiktok", END)
    workflow.add_edge("youtube_shorts", END)

    # ========================================================================
    # COMPILATION
    # ========================================================================

    # Compile graph with checkpointer (if provided)
    if checkpointer:
        logger.info("Compiling graph with PostgreSQL checkpointer")
        compiled_graph = workflow.compile(checkpointer=checkpointer)
    else:
        logger.info("Compiling graph without checkpointer (in-memory only)")
        compiled_graph = workflow.compile()

    logger.info("Content creation workflow graph built successfully")

    return compiled_graph


async def run_workflow(
    workflow_id: str,
    tenant_id: str,
    user_id: str,
    thread_id: str,
    user_request: str,
    target_platforms: list[str],
    cost_limit_usd: float = 5.0,
    checkpointer: PostgresSaver = None,
    memory_manager: MemoryManager = None
) -> Dict[str, Any]:
    """
    Run the complete content creation workflow.

    This is the main entry point for executing workflows.

    Args:
        workflow_id: Unique workflow identifier
        tenant_id: Tenant/organization ID
        user_id: User who initiated workflow
        thread_id: Conversation thread ID
        user_request: User's content creation request
        target_platforms: Platforms to publish to
        cost_limit_usd: Maximum cost for this workflow
        checkpointer: PostgreSQL checkpointer (optional)
        memory_manager: Mem0 memory manager (optional)

    Returns:
        Final workflow state with results

    Example:
        result = await run_workflow(
            workflow_id="wf-123",
            tenant_id="tenant-456",
            user_id="user-789",
            thread_id="thread-abc",
            user_request="Create a video about AI trends",
            target_platforms=["tiktok", "youtube_shorts"],
            cost_limit_usd=5.0
        )

        # Access results
        tiktok_url = result["publish_results"]["tiktok"]["url"]
        youtube_url = result["publish_results"]["youtube_shorts"]["url"]
        total_cost = result["total_cost_usd"]
    """
    logger.info(f"Starting workflow execution: {workflow_id}")

    # Build graph
    graph = build_content_workflow(
        checkpointer=checkpointer,
        memory_manager=memory_manager
    )

    # Create initial state
    initial_state = create_initial_workflow_state(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        user_id=user_id,
        thread_id=thread_id,
        user_request=user_request,
        target_platforms=target_platforms,
        cost_limit_usd=cost_limit_usd
    )

    logger.info(
        f"Initial state created: platforms={target_platforms}, "
        f"cost_limit=${cost_limit_usd}"
    )

    # Execute workflow
    config = {}
    if checkpointer:
        # Use workflow_id as checkpoint thread_id for state persistence
        config = {"configurable": {"thread_id": workflow_id}}

    try:
        # Invoke graph
        final_state = await graph.ainvoke(initial_state, config=config)

        logger.info(
            f"Workflow completed: {workflow_id}, "
            f"status={final_state.get('workflow_status')}, "
            f"cost=${final_state.get('total_cost_usd', 0):.2f}"
        )

        return final_state

    except Exception as e:
        logger.error(f"Workflow execution failed: {workflow_id}, error: {e}", exc_info=True)
        raise


async def stream_workflow(
    workflow_id: str,
    tenant_id: str,
    user_id: str,
    thread_id: str,
    user_request: str,
    target_platforms: list[str],
    cost_limit_usd: float = 5.0,
    checkpointer: PostgresSaver = None
):
    """
    Stream workflow execution for real-time updates.

    Yields state updates as each node completes.
    Used by WebSocket connections for frontend updates.

    Args:
        (same as run_workflow)

    Yields:
        Dict with node name and updated state

    Example:
        async for update in stream_workflow(...):
            node_name = update["node"]
            status = update["state"]["workflow_status"]
            print(f"{node_name}: {status}")
    """
    logger.info(f"Starting workflow stream: {workflow_id}")

    # Build graph
    graph = build_content_workflow(checkpointer=checkpointer)

    # Create initial state
    initial_state = create_initial_workflow_state(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        user_id=user_id,
        thread_id=thread_id,
        user_request=user_request,
        target_platforms=target_platforms,
        cost_limit_usd=cost_limit_usd
    )

    # Execute with streaming
    config = {}
    if checkpointer:
        config = {"configurable": {"thread_id": workflow_id}}

    try:
        async for event in graph.astream(initial_state, config=config):
            # Extract node name and state
            node_name = list(event.keys())[0] if event else "unknown"
            node_state = event.get(node_name, {})

            logger.debug(f"Workflow stream event: {node_name}")

            yield {
                "node": node_name,
                "state": node_state,
                "timestamp": node_state.get("updated_at")
            }

    except Exception as e:
        logger.error(f"Workflow stream failed: {workflow_id}, error: {e}", exc_info=True)
        yield {
            "node": "error",
            "state": {"error_message": str(e)},
            "timestamp": None
        }


def create_checkpointer():
    """
    Create persistent SQLite checkpointer for state persistence.

    SQLite provides persistence across restarts without PostgreSQL's async context complexity.
    This ensures interrupted workflows (review gates) can resume after backend restarts.

    Returns:
        SqliteSaver instance (or MemorySaver as fallback)
    """
    import os
    from pathlib import Path

    try:
        from langgraph.checkpoint.sqlite import SqliteSaver

        # Ensure checkpoint directory exists
        checkpoint_dir = Path("/app/checkpoints")
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        checkpoint_db = checkpoint_dir / "langgraph_state.db"
        checkpointer = SqliteSaver.from_conn_string(str(checkpoint_db))

        logger.info(f"Persistent SQLite checkpointer created: {checkpoint_db}")

    except (ImportError, Exception) as e:
        # Fallback to in-memory if SQLite unavailable
        logger.warning(f"SQLite checkpointer unavailable: {e}, falling back to MemorySaver")
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()
        logger.info("In-memory checkpointer created (fallback)")

    return checkpointer


# ============================================================================
# Graph Visualization (for debugging/documentation)
# ============================================================================

def visualize_graph() -> str:
    """
    Generate Mermaid diagram of workflow graph.

    Returns:
        Mermaid markdown string

    Example output:
        ```mermaid
        graph TD
            START --> supervisor
            supervisor --> content_creation
            content_creation --> tiktok
            content_creation --> youtube_shorts
            tiktok --> END
            youtube_shorts --> END
        ```
    """
    graph = build_content_workflow()

    try:
        # LangGraph provides get_graph() method
        mermaid = graph.get_graph().draw_mermaid()
        return mermaid
    except Exception as e:
        logger.warning(f"Graph visualization failed: {e}")
        return """
```mermaid
graph TD
    START --> supervisor[SupervisorAgent]
    supervisor --> content_creation[ContentCreationAgent]
    content_creation --> tiktok[TikTokAgent]
    content_creation --> youtube_shorts[YouTubeShortsAgent]
    tiktok --> END
    youtube_shorts --> END
```
        """
