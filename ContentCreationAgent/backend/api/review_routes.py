"""
FastAPI routes for content review management.

Endpoints:
- GET  /api/reviews              - List pending reviews
- GET  /api/reviews/{id}         - Get review details
- PATCH /api/reviews/{id}        - Update review (approve/reject)
- POST /api/reviews/{id}/assign  - Assign reviewer
"""

from typing import List, Optional
from datetime import datetime
from uuid import UUID
import logging

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from backend.database.models import ContentReview, WorkflowExecution
from backend.database.connection import get_db_session
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


# ============================================================================
# Request/Response Models
# ============================================================================

class ReviewResponse(BaseModel):
    """Response model for review data."""
    id: UUID
    workflow_id: UUID
    workflow_execution_id: UUID
    reviewer_id: Optional[UUID]
    asset_type: str
    asset_url: Optional[str]
    asset_metadata: Optional[dict]
    status: str
    feedback: Optional[str]
    created_at: datetime
    assigned_at: Optional[datetime]
    reviewed_at: Optional[datetime]

    class Config:
        from_attributes = True


class UpdateReviewRequest(BaseModel):
    """Request model for updating review status."""
    status: str = Field(..., pattern="^(approved|rejected)$")
    feedback: Optional[str] = None
    feedback_metadata: Optional[dict] = None


class AssignReviewerRequest(BaseModel):
    """Request model for assigning a reviewer."""
    reviewer_id: UUID


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/", response_model=List[ReviewResponse])
async def list_reviews(
    status: Optional[str] = Query(None, regex="^(pending|in_review|approved|rejected)$"),
    asset_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session)
):
    """
    List content reviews with optional filters.

    Args:
        status: Filter by review status
        asset_type: Filter by asset type (video, image, audio, script)
        limit: Max results to return
        offset: Pagination offset
        session: Database session

    Returns:
        List of reviews
    """
    try:
        query = select(ContentReview).options(
            joinedload(ContentReview.workflow),
            joinedload(ContentReview.reviewer)
        ).order_by(ContentReview.created_at.desc())

        # Apply filters
        if status:
            query = query.where(ContentReview.status == status)
        if asset_type:
            query = query.where(ContentReview.asset_type == asset_type)

        # Pagination
        query = query.limit(limit).offset(offset)

        result = await session.execute(query)
        reviews = result.scalars().all()

        return [ReviewResponse.from_orm(review) for review in reviews]

    except Exception as e:
        logger.error(f"Failed to list reviews: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve reviews")


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: UUID,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get detailed review information.

    Args:
        review_id: Review UUID
        session: Database session

    Returns:
        Review details with asset metadata
    """
    try:
        query = select(ContentReview).where(
            ContentReview.id == review_id
        ).options(
            joinedload(ContentReview.workflow),
            joinedload(ContentReview.reviewer)
        )

        result = await session.execute(query)
        review = result.scalar_one_or_none()

        if not review:
            raise HTTPException(status_code=404, detail="Review not found")

        return ReviewResponse.from_orm(review)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get review {review_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve review")


@router.patch("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: UUID,
    update_data: UpdateReviewRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Update review status (approve or reject).

    This is the critical endpoint for human-in-the-loop workflow control.
    When status changes to 'approved', the LangGraph workflow resumes.

    Args:
        review_id: Review UUID
        update_data: Update payload (status, feedback)
        session: Database session

    Returns:
        Updated review
    """
    try:
        # Fetch review
        query = select(ContentReview).where(ContentReview.id == review_id)
        result = await session.execute(query)
        review = result.scalar_one_or_none()

        if not review:
            raise HTTPException(status_code=404, detail="Review not found")

        # Validate state transition
        if review.status in ('approved', 'rejected'):
            raise HTTPException(
                status_code=400,
                detail=f"Review already {review.status}, cannot update"
            )

        # Update review
        review.status = update_data.status
        review.feedback = update_data.feedback
        review.feedback_metadata = update_data.feedback_metadata
        review.reviewed_at = datetime.utcnow()

        # Record reinforcement learning feedback in Mem0
        await _record_review_feedback(review, update_data.status, update_data.feedback)

        # Resume or end workflow using LangGraph
        if update_data.status == 'approved':
            logger.info(f"Resuming workflow {review.workflow_id}")

            # Resume workflow execution in background
            # When interrupt() was called, the graph paused and saved state
            # To resume, we need to invoke the graph again with the same config
            from backend.workflow.execution import resume_workflow_after_review
            import asyncio

            # Create background task to resume workflow
            asyncio.create_task(resume_workflow_after_review(
                workflow_id=str(review.workflow_id),
                review_id=str(review.id)
            ))

        elif update_data.status == 'rejected':
            # Mark workflow as rejected
            workflow_exec_query = select(WorkflowExecution).where(
                WorkflowExecution.id == review.workflow_execution_id
            )
            exec_result = await session.execute(workflow_exec_query)
            workflow_exec = exec_result.scalar_one_or_none()

            if workflow_exec:
                workflow_exec.status = 'rejected'
                workflow_exec.error_message = update_data.feedback or "Rejected by reviewer"

        await session.commit()
        await session.refresh(review)

        return ReviewResponse.from_orm(review)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to update review {review_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update review")


@router.post("/{review_id}/assign", response_model=ReviewResponse)
async def assign_reviewer(
    review_id: UUID,
    assign_data: AssignReviewerRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Assign a reviewer to a pending review.

    Args:
        review_id: Review UUID
        assign_data: Reviewer assignment data
        session: Database session

    Returns:
        Updated review
    """
    try:
        query = select(ContentReview).where(ContentReview.id == review_id)
        result = await session.execute(query)
        review = result.scalar_one_or_none()

        if not review:
            raise HTTPException(status_code=404, detail="Review not found")

        if review.status != 'pending':
            raise HTTPException(
                status_code=400,
                detail="Can only assign reviewers to pending reviews"
            )

        review.reviewer_id = assign_data.reviewer_id
        review.assigned_at = datetime.utcnow()
        review.status = 'in_review'

        await session.commit()
        await session.refresh(review)

        return ReviewResponse.from_orm(review)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to assign reviewer to {review_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to assign reviewer")


# =============================================================================
# Reinforcement Learning Helper Functions
# =============================================================================

async def _record_review_feedback(
    review: ContentReview,
    decision: str,
    feedback: Optional[str] = None
):
    """
    Record reinforcement learning feedback in Mem0 based on review decision.

    This connects human-in-the-loop approvals/rejections to the memory system,
    enabling the agent to learn from feedback over time.

    Args:
        review: Content review object
        decision: 'approved' or 'rejected'
        feedback: Optional feedback text from reviewer
    """
    try:
        from backend.memory.memory_manager import MemoryManager

        # Get metadata from review
        asset_type = review.asset_type
        metadata = review.asset_metadata or {}
        platforms = metadata.get("platforms", [])
        script = metadata.get("script", "")

        # Determine RL score based on decision
        # Approved content gets positive score, rejected gets negative
        if decision == "approved":
            rl_score = 1.0
            outcome = "success"
        else:
            rl_score = -0.5  # Negative but not as strong (learns what to avoid)
            outcome = "failure"

        # Create memory manager for system-wide learning
        # Using supervisor agent as the memory owner (system learns as a whole)
        memory_manager = MemoryManager(
            tenant_id=str(review.workflow_id),  # Workflow as tenant context
            agent_id="supervisor"  # System-wide learning
        )

        # Construct the learning fact
        learning_text = (
            f"Content review {outcome}: {asset_type} for {', '.join(platforms)}. "
            f"{f'Feedback: {feedback[:100]}' if feedback else ''}"
        )

        # Add category and tags for filtering
        category = "content_quality"
        tags = [asset_type, outcome] + platforms

        # Store as reinforced fact in Mem0
        # Positive score for approved, negative for rejected
        mem_id = memory_manager.add_fact(
            user_id=str(review.workflow_id),  # Workflow as user
            text=learning_text,
            score=rl_score,
            category=category,
            tags=tags
        )

        if mem_id:
            logger.info(
                f"✅ RL feedback recorded in Mem0: {decision} → score={rl_score:.2f} "
                f"(ID: {mem_id}, platforms: {platforms})"
            )

        # Also reinforce any previous related memories if this is approval
        if decision == "approved" and script:
            # Search for similar successful content patterns
            similar_memories = memory_manager.retrieve(
                user_id=str(review.workflow_id),
                query=f"successful {asset_type} content patterns"
            )

            # Boost confidence on similar successful patterns
            for mem in similar_memories[:3]:  # Top 3 most relevant
                memory_manager.reinforce(mem["id"], delta=0.1)
                logger.debug(f"Reinforced similar memory: {mem.get('memory', '')[:50]}")

    except Exception as e:
        # Don't fail review if RL recording fails
        logger.error(f"Failed to record RL feedback in Mem0: {e}", exc_info=True)
