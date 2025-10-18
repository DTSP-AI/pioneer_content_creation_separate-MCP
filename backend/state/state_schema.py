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
from datetime import datetime


class BaseAgentState(TypedDict, total=False):
    """
    Base state schema inherited by all workflows.

    Fields:
        messages: Message history for LangChain
        current_agent: Currently executing agent name
        checkpoint_id: LangGraph checkpoint identifier
    """
    messages: List[Dict[str, Any]]
    current_agent: str
    checkpoint_id: Optional[str]


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

    # === COST TRACKING ===
    cost_breakdown: Optional[Dict[str, float]]  # {service: cost_usd}
    total_cost_usd: Optional[float]

    # === WORKFLOW CONTROL ===
    workflow_status: str  # pending, running, completed, failed
    current_phase: Optional[str]  # supervisor, content_creation, publishing
    error_message: Optional[str]
    retry_count: int

    # === CONFIGURATION ===
    agent_config: Optional[Dict[str, Any]]
    cost_limit_usd: float

    # === METADATA ===
    created_at: Optional[str]
    updated_at: Optional[str]
    session_metadata: Optional[Dict[str, Any]]


class SupervisorState(TypedDict, total=False):
    """
    Supervisor Agent-specific state.

    The supervisor is the entry node that:
    - Receives user requests
    - Validates inputs
    - Manages cost ledger
    - Routes to ContentCreationAgent
    - Aggregates results
    """
    user_request: str
    parsed_intent: Optional[Dict[str, Any]]
    target_platforms: List[str]
    cost_check_passed: bool
    routing_decision: Optional[str]
    aggregated_results: Optional[Dict[str, Any]]


class ContentCreationState(TypedDict, total=False):
    """
    Content Creation Agent-specific state.

    Centralized API usage node that:
    - Fetches trends from Google Sheets
    - Generates script via Claude
    - Generates audio via ElevenLabs
    - Renders video via Creatomate
    - Returns asset pack to platform agents
    """
    trend_query: Optional[str]
    trend_results: Optional[List[Dict[str, Any]]]
    selected_trend: Optional[str]

    script_prompt: Optional[str]
    script_generation_tokens: Optional[int]
    script_cost_usd: Optional[float]

    tts_request: Optional[Dict[str, Any]]
    tts_character_count: Optional[int]
    tts_cost_usd: Optional[float]

    video_render_request: Optional[Dict[str, Any]]
    video_render_cost_usd: Optional[float]

    asset_pack: Optional[Dict[str, Any]]  # {script, audio_path, video_path, captions}


class PlatformPublishState(TypedDict, total=False):
    """
    Platform Publishing Agent-specific state (TikTok & YouTube).

    Platform agents:
    - Receive asset_pack from ContentCreationAgent
    - Format content for platform requirements
    - Generate platform-specific metadata
    - Upload via platform API
    - Return URL + metrics
    """
    platform_name: str  # "tiktok" or "youtube_shorts"

    # Asset processing
    input_video_path: str
    formatted_video_path: Optional[str]
    aspect_ratio: str  # "9:16" for vertical
    max_duration_seconds: int

    # Platform-specific metadata
    title: Optional[str]
    description: Optional[str]
    tags: Optional[List[str]]
    caption: Optional[str]

    # Upload
    upload_request: Optional[Dict[str, Any]]
    upload_status: Optional[str]  # uploading, processing, published, failed

    # Results
    published_url: Optional[str]
    platform_video_id: Optional[str]
    publish_metrics: Optional[Dict[str, Any]]  # views, likes, shares (initial)


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
    now = datetime.utcnow().isoformat()

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
        "updated_at": datetime.utcnow().isoformat()
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
