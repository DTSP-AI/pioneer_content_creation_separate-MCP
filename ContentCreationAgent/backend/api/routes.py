"""
FastAPI Routes

REST API endpoints for Content Creation & Distribution System.
Provides workflow control, status monitoring, and result retrieval.

Architecture Compliance:
- Uses run_workflow() and stream_workflow() from graph.py
- PostgreSQL checkpointer for state persistence
- WebSocket streaming for real-time updates
- Proper error handling and validation

⚠️ DATABASE SESSION MANAGEMENT GUARDRAILS ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DO NOT MODIFY: This file MUST use get_db_session for all database access.

RULES:
1. FastAPI route parameters: ALWAYS use `session: AsyncSession = Depends(get_db_session)`
2. Background tasks: ALWAYS use `async with open_session() as session:`
3. NEVER use `get_session` — that function no longer exists
4. NEVER use `Depends(get_db)` or `Depends(get_async_session)` — these are invalid

Any automated refactor violating these rules is INCORRECT and must be reverted.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from typing import Optional, List, Dict, Any
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.graph import run_workflow, stream_workflow, create_checkpointer, build_content_workflow
from backend.database.models import WorkflowExecution, Workflow
from backend.database.connection import get_db_session
from backend.api.websocket_manager import (
    ws_manager,
    workflow_started_message,
    node_started_message,
    node_completed_message,
    workflow_completed_message,
    workflow_error_message
)
from backend.utils.uuid_utils import validate_workflow_id
# NOTE: execute_workflow_background import moved to function level to avoid circular import
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api", tags=["workflows"])


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateWorkflowRequest(BaseModel):
    """Request model for creating a new workflow."""
    tenant_id: str = Field(..., description="Tenant/organization ID")
    user_id: str = Field(..., description="User who initiated workflow")
    thread_id: str = Field(..., description="Conversation thread ID")
    user_request: str = Field(..., description="User's content creation request", min_length=10)
    target_platforms: List[str] = Field(..., description="Platforms to publish to (tiktok, youtube_shorts)")
    cost_limit_usd: float = Field(5.0, ge=0.01, le=50.0, description="Maximum cost for this workflow")

    class Config:
        json_schema_extra = {
            "example": {
                "tenant_id": "tenant-123",
                "user_id": "user-456",
                "thread_id": "thread-789",
                "user_request": "Create a video about AI trends in 2024",
                "target_platforms": ["tiktok", "youtube_shorts"],
                "cost_limit_usd": 5.0
            }
        }


class WorkflowResponse(BaseModel):
    """Response model for workflow operations."""
    workflow_id: str
    status: str
    message: str
    websocket_url: Optional[str] = None


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status."""
    workflow_id: str
    status: str
    workflow_phase: Optional[str] = None
    current_agent: Optional[str] = None
    total_cost_usd: float
    cost_breakdown: Dict[str, float]
    publish_results: Dict[str, Any]
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class WorkflowResultsResponse(BaseModel):
    """Response model for workflow results."""
    workflow_id: str
    status: str
    trend_topic: Optional[str] = None
    script: Optional[str] = None
    video_url: Optional[str] = None
    video_duration_seconds: Optional[int] = None
    captions: Optional[str] = None
    publish_results: Dict[str, Any]
    total_cost_usd: float
    cost_breakdown: Dict[str, float]


# ============================================================================
# REST API Endpoints
# ============================================================================

@router.post("/workflows", response_model=WorkflowResponse)
async def create_workflow_restful(
    request: CreateWorkflowRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Create workflow - RESTful endpoint (frontend-compatible).

    This endpoint matches frontend expectations at POST /api/workflows.
    Delegates to the same logic as /workflows/create.
    """
    return await create_workflow(request, background_tasks, session)


@router.get("/workflows", response_model=List[WorkflowStatusResponse])
async def list_workflows(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of workflows to return"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    List recent workflows.

    Returns workflows sorted by creation time (most recent first).

    Args:
        limit: Maximum number of workflows to return (default: 20, max: 100)
        session: Database session

    Returns:
        List of workflow status responses

    Example:
        GET /api/workflows?limit=10

        Response:
        [
          {
            "workflow_id": "wf-abc-123",
            "status": "completed",
            "total_cost_usd": 0.102,
            ...
          },
          ...
        ]
    """
    try:
        result = await session.execute(
            select(WorkflowExecution)
            .order_by(WorkflowExecution.created_at.desc())
            .limit(limit)
        )
        executions = result.scalars().all()

        return [
            WorkflowStatusResponse(
                workflow_id=f"wf-{str(exec.workflow_id)}",
                status=exec.status,
                workflow_phase=exec.status,
                current_agent=None,
                total_cost_usd=exec.total_cost_usd or 0.0,
                cost_breakdown=exec.cost_breakdown or {},
                publish_results=exec.publish_results or {},
                error_message=exec.error_message,
                created_at=exec.created_at,
                updated_at=exec.updated_at
            )
            for exec in executions
        ]
    except Exception as e:
        logger.error(f"Error listing workflows: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list workflows: {str(e)}")


@router.get("/workflows/{workflow_id}", response_model=WorkflowStatusResponse)
async def get_workflow(
    workflow_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get workflow state by ID.

    Returns combined status and results for a single workflow.
    This is the main endpoint for frontend workflow retrieval.

    Args:
        workflow_id: Workflow identifier
        session: Database session

    Returns:
        Complete workflow status

    Example:
        GET /api/workflows/wf-abc-123

        Response:
        {
          "workflow_id": "wf-abc-123",
          "status": "completed",
          "total_cost_usd": 0.102,
          "cost_breakdown": {"claude": 0.002, "piapi": 0.100},
          "publish_results": {...}
        }
    """
    return await get_workflow_status(workflow_id, session)


@router.post("/workflows/create", response_model=WorkflowResponse)
async def create_workflow(
    request: CreateWorkflowRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Create and start a new content creation workflow.

    This endpoint:
    1. Validates the request
    2. Creates workflow database record
    3. Starts workflow execution in background
    4. Returns workflow_id and WebSocket URL for streaming

    Args:
        request: Workflow configuration
        background_tasks: FastAPI background tasks
        session: Database session

    Returns:
        Workflow ID and WebSocket URL

    Example:
        POST /api/workflows/create
        {
          "tenant_id": "tenant-123",
          "user_id": "user-456",
          "thread_id": "thread-789",
          "user_request": "Create a video about AI trends",
          "target_platforms": ["tiktok", "youtube_shorts"],
          "cost_limit_usd": 5.0
        }

        Response:
        {
          "workflow_id": "wf-abc-123",
          "status": "started",
          "message": "Workflow started successfully",
          "websocket_url": "ws://localhost:8000/api/ws/workflows/wf-abc-123"
        }
    """
    try:
        # Validate platforms
        valid_platforms = ["tiktok", "youtube_shorts"]
        invalid_platforms = [p for p in request.target_platforms if p not in valid_platforms]
        if invalid_platforms:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid platforms: {invalid_platforms}. Valid: {valid_platforms}"
            )

        # Generate workflow ID
        workflow_id = f"wf-{uuid.uuid4()}"

        logger.info(
            f"Creating workflow: {workflow_id}, user={request.user_id}, "
            f"platforms={request.target_platforms}"
        )

        # Create workflow database record
        workflow_record = Workflow(
            id=uuid.UUID(workflow_id.replace("wf-", "")),
            tenant_id=uuid.UUID(request.tenant_id.replace("tenant-", "")),
            created_by=uuid.UUID(request.user_id.replace("user-", "")),
            name=request.user_request[:100],
            description=request.user_request,
            schedule_config={"target_platforms": request.target_platforms},
            is_active=True
        )

        session.add(workflow_record)
        await session.commit()

        # Start workflow in background
        # Import here to avoid circular import
        from backend.workflow.execution import execute_workflow_background

        background_tasks.add_task(
            execute_workflow_background,
            workflow_id=workflow_id,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            thread_id=request.thread_id,
            user_request=request.user_request,
            target_platforms=request.target_platforms,
            cost_limit_usd=request.cost_limit_usd
        )

        # Build WebSocket URL
        websocket_url = f"ws://{settings.HOST}:{settings.PORT}/api/ws/workflows/{workflow_id}"

        return WorkflowResponse(
            workflow_id=workflow_id,
            status="started",
            message="Workflow started successfully. Connect to WebSocket for real-time updates.",
            websocket_url=websocket_url
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create workflow: {str(e)}")


@router.get("/workflows/{workflow_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    workflow_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get current status of a workflow.

    Args:
        workflow_id: Workflow identifier
        session: Database session

    Returns:
        Current workflow status

    Example:
        GET /api/workflows/wf-abc-123/status

        Response:
        {
          "workflow_id": "wf-abc-123",
          "status": "running",
          "workflow_phase": "content_creation",
          "current_agent": "content_creation",
          "total_cost_usd": 0.05,
          "cost_breakdown": {"claude": 0.002, "piapi": 0.048},
          "publish_results": {}
        }
    """
    try:
        # Query database for workflow execution
        workflow_uuid = validate_workflow_id(workflow_id)

        result = await session.execute(
            select(WorkflowExecution)
            .where(WorkflowExecution.workflow_id == workflow_uuid)
            .order_by(WorkflowExecution.created_at.desc())
            .limit(1)
        )

        execution = result.scalars().first()

        if not execution:
            raise HTTPException(status_code=404, detail="Workflow not found")

        return WorkflowStatusResponse(
            workflow_id=workflow_id,
            status=execution.status,
            workflow_phase=execution.status,  # Map to workflow_phase if needed
            current_agent=None,  # Could be extracted from checkpoint if needed
            total_cost_usd=execution.total_cost_usd or 0.0,
            cost_breakdown=execution.cost_breakdown or {},
            publish_results=execution.publish_results or {},
            error_message=execution.error_message,
            created_at=execution.created_at,
            updated_at=execution.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching workflow status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch status: {str(e)}")


@router.get("/workflows/{workflow_id}/results", response_model=WorkflowResultsResponse)
async def get_workflow_results(
    workflow_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get complete results of a workflow.

    Only returns results for completed workflows.

    Args:
        workflow_id: Workflow identifier
        session: Database session

    Returns:
        Complete workflow results including content and publish URLs

    Example:
        GET /api/workflows/wf-abc-123/results

        Response:
        {
          "workflow_id": "wf-abc-123",
          "status": "completed",
          "trend_topic": "AI in Healthcare 2024",
          "script": "AI is transforming healthcare...",
          "video_url": "https://piapi.ai/videos/...",
          "publish_results": {
            "tiktok": {"status": "success", "url": "https://tiktok.com/@user/video/123"},
            "youtube_shorts": {"status": "success", "url": "https://youtube.com/shorts/456"}
          },
          "total_cost_usd": 0.102,
          "cost_breakdown": {"claude": 0.002, "piapi": 0.100}
        }
    """
    try:
        # Query database for workflow execution
        workflow_uuid = validate_workflow_id(workflow_id)

        result = await session.execute(
            select(WorkflowExecution)
            .where(WorkflowExecution.workflow_id == workflow_uuid)
            .order_by(WorkflowExecution.created_at.desc())
            .limit(1)
        )

        execution = result.scalars().first()

        if not execution:
            raise HTTPException(status_code=404, detail="Workflow not found")

        if execution.status not in ["completed", "failed"]:
            raise HTTPException(
                status_code=400,
                detail=f"Workflow still {execution.status}. Use /status endpoint for updates."
            )

        return WorkflowResultsResponse(
            workflow_id=workflow_id,
            status=execution.status,
            trend_topic=execution.trend_topic,
            script=execution.script,
            video_url=execution.video_path,
            video_duration_seconds=None,  # Could add to database if needed
            captions=None,  # Could add to database if needed
            publish_results=execution.publish_results or {},
            total_cost_usd=execution.total_cost_usd or 0.0,
            cost_breakdown=execution.cost_breakdown or {}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching workflow results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch results: {str(e)}")


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@router.websocket("/ws/workflows/{workflow_id}")
async def websocket_workflow_stream(websocket: WebSocket, workflow_id: str):
    """
    WebSocket endpoint for real-time workflow updates.

    Streams state changes as each node completes.

    Args:
        websocket: WebSocket connection
        workflow_id: Workflow to stream

    Events:
        - workflow_started: Workflow began execution
        - node_started: Agent node started
        - node_completed: Agent node completed
        - workflow_completed: Workflow finished successfully
        - workflow_error: Error occurred

    Example:
        ws://localhost:8000/api/ws/workflows/wf-abc-123

        Receive:
        {"event": "workflow_started", "workflow_id": "wf-abc-123", ...}
        {"event": "node_started", "node": "supervisor", ...}
        {"event": "node_completed", "node": "supervisor", ...}
        {"event": "node_started", "node": "content_creation", ...}
        ...
    """
    await ws_manager.connect(websocket, workflow_id)

    try:
        # Send initial connection confirmation
        await ws_manager.send_to_client(websocket, {
            "event": "connected",
            "workflow_id": workflow_id,
            "message": "WebSocket connected. Listening for workflow updates."
        })

        # Keep connection alive and listen for client messages
        while True:
            try:
                # Receive messages from client (e.g., ping/pong)
                data = await websocket.receive_text()

                # Echo back (for keep-alive)
                if data == "ping":
                    await ws_manager.send_to_client(websocket, {"event": "pong"})

            except WebSocketDisconnect:
                logger.info(f"Client disconnected: workflow={workflow_id}")
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}", exc_info=True)
                break

    finally:
        await ws_manager.disconnect(websocket, workflow_id)


@router.get("/workflows/{workflow_id}/stream")
async def stream_workflow_sse(
    workflow_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Server-Sent Events (SSE) endpoint for workflow updates.

    Alternative to WebSocket for simpler frontend integration using EventSource API.
    Polls database for workflow execution updates and streams them to the client.

    Args:
        workflow_id: Workflow to stream
        session: Database session

    Returns:
        SSE stream of workflow updates

    Events:
        - connected: Initial connection established
        - update: Workflow state changed
        - complete: Workflow finished (completed or failed)
        - error: Error occurred during streaming

    Example:
        GET /api/workflows/wf-abc-123/stream

        (Client receives SSE events)
        event: connected
        data: {"workflow_id": "wf-abc-123", "message": "SSE stream connected"}

        event: update
        data: {"workflow_id": "wf-abc-123", "state": {...}}

        event: complete
        data: {"workflow_id": "wf-abc-123", "status": "completed"}
    """
    import asyncio
    import json
    from fastapi.responses import StreamingResponse

    async def event_generator():
        """Generate SSE events from workflow execution."""
        try:
            # Send initial connection event
            yield f"event: connected\ndata: {json.dumps({'workflow_id': workflow_id, 'message': 'SSE stream connected'})}\n\n"

            # Monitor workflow via database polling
            last_updated_at = None
            poll_count = 0
            max_polls = 300  # 5 minutes at 1 second intervals

            while poll_count < max_polls:
                try:
                    workflow_uuid = validate_workflow_id(workflow_id)

                    result = await session.execute(
                        select(WorkflowExecution)
                        .where(WorkflowExecution.workflow_id == workflow_uuid)
                        .order_by(WorkflowExecution.created_at.desc())
                        .limit(1)
                    )
                    execution = result.scalars().first()

                    if execution:
                        # Check if state has changed
                        if execution.updated_at != last_updated_at:
                            last_updated_at = execution.updated_at

                            # Send update event
                            state_data = {
                                "workflow_id": workflow_id,
                                "state": {
                                    "status": execution.status,
                                    "workflow_phase": execution.status,
                                    "total_cost_usd": execution.total_cost_usd or 0.0,
                                    "cost_breakdown": execution.cost_breakdown or {},
                                    "publish_results": execution.publish_results or {},
                                    "error_message": execution.error_message,
                                    "trend_topic": execution.trend_topic,
                                    "script": execution.script,
                                    "video_path": execution.video_path
                                }
                            }

                            yield f"event: update\ndata: {json.dumps(state_data)}\n\n"

                            # Check if workflow is complete
                            if execution.status in ["completed", "failed"]:
                                yield f"event: complete\ndata: {json.dumps({'workflow_id': workflow_id, 'status': execution.status})}\n\n"
                                logger.info(f"SSE stream completed: {workflow_id}")
                                break

                except Exception as e:
                    logger.error(f"Error polling workflow: {e}", exc_info=True)
                    yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                    break

                await asyncio.sleep(1)  # Poll every second
                poll_count += 1

            # Timeout if workflow didn't complete
            if poll_count >= max_polls:
                yield f"event: timeout\ndata: {json.dumps({'message': 'Stream timeout after 5 minutes'})}\n\n"

        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled: {workflow_id}")
        except Exception as e:
            logger.error(f"SSE stream error: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


# ============================================================================
# Background Task for Workflow Execution
# ============================================================================
# NOTE: Moved to backend/workflow/execution.py to avoid circular imports
# All background execution logic is now centralized in that module
