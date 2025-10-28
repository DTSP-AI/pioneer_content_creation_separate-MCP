"""
Unified State Schema for Content Creation & Distribution System

This module defines TypedDict schemas for LangGraph state management.
All agents share these state definitions for seamless data flow.

Architecture Compliance:
- Follows AGENT_ORCHESTRATION_STANDARD.md
- TypedDict for explicit state schemas
- No hidden state or side effects
- Immutable state updates via node returns
"""

from typing import TypedDict, Dict, Any, List, Optional
from datetime import datetime, timezone


class BaseAgentState(TypedDict, total=False):
    """
    Base state schema inherited by all workflows.

    Fields:
        messages: Message history for LangChain
        current_agent: Currently executing agent name
        checkpoint_ref: User checkpoint reference (renamed from checkpoint_id to avoid LangGraph reserved name)
    """
    messages: List[Dict[str, Any]]
    current_agent: str
    checkpoint_ref: Optional[str]


class VideoWorkflowState(BaseAgentState, total=False):
    """
    Unified state for the complete video creation & distribution workflow.

    This is the PRIMARY state schema used by the graph orchestrator.
    All 4 agents (Supervisor, Content, TikTok, YouTube) read/write to this schema.

    Architecture Flow:
        SupervisorAgent (entry) → ContentCreationAgent → [TikTokAgent, YouTubeShortsAgent]

    Fields organized by workflow phase:
    """

    # === IDENTITY & CONTEXT ===
    workflow_id: str
    tenant_id: str
    user_id: str
    thread_id: str
    timestamp: str

    # === INPUT ===
    user_request: str  # Original user command
    target_platforms: List[str]  # ["tiktok", "youtube_shorts"]

    # === TREND DATA (from Google Sheets) ===
    trend_topic: Optional[str]
    trend_metadata: Optional[Dict[str, Any]]

    # === CONTENT CREATION (ContentCreationAgent) ===
    script: Optional[str]
    script_word_count: Optional[int]
    audio_path: Optional[str]
    audio_duration_seconds: Optional[float]
    video_path: Optional[str]
    video_duration_seconds: Optional[float]
    captions: Optional[str]

    # === PLATFORM-SPECIFIC ASSETS ===
    tiktok_video_path: Optional[str]
    youtube_video_path: Optional[str]

    # === PUBLISHING RESULTS ===
    publish_results: Optional[Dict[str, Any]]  # {platform: {url, status, metadata}}

    # === REVIEW WORKFLOW ===
    review_id: Optional[str]  # UUID of content_review record (FK only)

    # === COST TRACKING ===
    cost_breakdown: Optional[Dict[str, float]]  # {service: cost_usd}
    total_cost_usd: Optional[float]

    # === WORKFLOW CONTROL ===
    workflow_status: str  # pending, running, completed, failed
    current_phase: Optional[str]  # supervisor, content_creation, publishing
    current_stage: Optional[str]  # strategy, creation, refinement, delivery (from orchestration.WorkflowStage)
    error_message: Optional[str]
    retry_count: int

    # === CONFIGURATION ===
    agent_config: Optional[Dict[str, Any]]
    cost_limit_usd: float
    priority: Optional[str]  # quality, balanced, speed (from orchestration.Priority)

    # === ORCHESTRATION METADATA ===
    orchestration_metadata: Optional[Dict[str, Any]]  # Tool selection reasoning, model info, platform requirements

    # === METADATA ===
    created_at: Optional[str]
    updated_at: Optional[str]
    session_metadata: Optional[Dict[str, Any]]


# ============================================================================
# Helper Functions for State Initialization
# ============================================================================

def create_initial_workflow_state(
    workflow_id: str,
    tenant_id: str,
    user_id: str,
    thread_id: str,
    user_request: str,
    target_platforms: List[str],
    cost_limit_usd: float = 5.0
) -> VideoWorkflowState:
    """
    Initialize a new workflow state.

    Args:
        workflow_id: Unique workflow identifier
        tenant_id: Tenant/organization ID
        user_id: User who initiated workflow
        thread_id: Conversation thread ID
        user_request: User's original request
        target_platforms: Platforms to publish to ["tiktok", "youtube_shorts"]
        cost_limit_usd: Maximum cost for this workflow

    Returns:
        VideoWorkflowState: Initialized state ready for graph execution
    """
    now = datetime.now(timezone.utc).isoformat()

    return VideoWorkflowState(
        # Identity
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        user_id=user_id,
        thread_id=thread_id,
        timestamp=now,

        # Input
        user_request=user_request,
        target_platforms=target_platforms,

        # Workflow control
        workflow_status="pending",
        current_phase="supervisor",
        retry_count=0,
        cost_limit_usd=cost_limit_usd,
        total_cost_usd=0.0,

        # Timestamps
        created_at=now,
        updated_at=now,

        # Initialize messages
        messages=[],
        current_agent="supervisor"
    )


def update_workflow_phase(
    state: VideoWorkflowState,
    phase: str,
    status: str = "running"
) -> Dict[str, Any]:
    """
    Helper to update workflow phase.

    Args:
        state: Current workflow state
        phase: New phase name
        status: New status

    Returns:
        Dict with state updates to merge
    """
    return {
        "current_phase": phase,
        "workflow_status": status,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


def add_cost_to_workflow(
    state: VideoWorkflowState,
    service: str,
    cost_usd: float
) -> Dict[str, Any]:
    """
    Add cost to workflow tracking.

    Args:
        state: Current workflow state
        service: Service name (e.g., "claude", "elevenlabs", "creatomate")
        cost_usd: Cost in USD

    Returns:
        Dict with cost updates to merge
    """
    cost_breakdown = state.get("cost_breakdown", {})
    cost_breakdown[service] = cost_usd

    total_cost = sum(cost_breakdown.values())

    return {
        "cost_breakdown": cost_breakdown,
        "total_cost_usd": total_cost,
        "updated_at": datetime.utcnow().isoformat()
    }


def update_workflow_stage(
    state: VideoWorkflowState,
    stage: str
) -> Dict[str, Any]:
    """
    Update workflow orchestration stage.

    Workflow stages (from backend.workflow.orchestration.WorkflowStage):
    - strategy: Supervisor analyzes intent
    - creation: Content agent generates content
    - refinement: Platform-specific optimization
    - delivery: Upload and tracking

    Args:
        state: Current workflow state
        stage: New orchestration stage

    Returns:
        Dict with stage update to merge
    """
    return {
        "current_stage": stage,
        "updated_at": datetime.utcnow().isoformat()
    }
