"""
Review Gate Node - Human-in-the-Loop Checkpoint

Uses LangGraph's built-in interrupt() for pause/resume.
"""

import logging
from typing import Dict, Any
from datetime import datetime
from uuid import uuid4

from langgraph.types import interrupt
from backend.state.state_schema import VideoWorkflowState
from backend.database.models import ContentReview
from backend.database.connection import open_session
from backend.graph.error_recovery import safe_node_execution

logger = logging.getLogger(__name__)


@safe_node_execution("review_gate")
async def review_gate_node(state: VideoWorkflowState) -> Dict[str, Any]:
    """
    Review gate - pauses workflow for human approval.

    Uses LangGraph's interrupt() - no polling needed.
    API endpoint calls graph.update_state() to resume.
    """
    logger.info("Review gate: creating review record")

    # Create review record for audit trail
    from uuid import UUID
    from sqlalchemy import select
    from backend.database.models import WorkflowExecution

    workflow_id_str = state.get("workflow_id", "")
    workflow_uuid = UUID(workflow_id_str.replace("wf-", "")) if workflow_id_str.startswith("wf-") else UUID(workflow_id_str)

    async with open_session() as session:
        # Find the workflow execution record
        result = await session.execute(
            select(WorkflowExecution)
            .where(WorkflowExecution.workflow_id == workflow_uuid)
            .order_by(WorkflowExecution.created_at.desc())
            .limit(1)
        )
        execution = result.scalars().first()
        execution_id = execution.id if execution else workflow_uuid

        review = ContentReview(
            id=uuid4(),
            workflow_id=workflow_uuid,
            workflow_execution_id=execution_id,
            asset_type="video",
            asset_url=state.get("video_path"),
            asset_metadata={
                "script": state.get("script"),
                "duration": state.get("video_duration_seconds"),
                "platforms": state.get("target_platforms")
            },
            status="pending"
        )
        session.add(review)
        await session.commit()
        review_id = str(review.id)

    logger.info(f"Review {review_id} created - pausing workflow")

    # Pause workflow (LangGraph saves state to PostgreSQL)
    interrupt({"review_id": review_id})

    # This runs after graph.update_state() is called
    logger.info("Review approved - resuming workflow")
    return {"current_phase": "publishing", "review_id": review_id}


__all__ = ['review_gate_node']
