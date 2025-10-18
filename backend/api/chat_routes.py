"""
Chat API Routes

Provides conversational interface for supervisor agent to create workflows.
Supports:
- Thread management
- Message history
- Workflow proposals
- Human approval flow
"""

from typing import Optional, List, Dict, Any
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from backend.database.models import Thread, ThreadMessage, Agent, User, Tenant, WorkflowExecution, get_session
from backend.config import get_settings
from backend.workflow.supervisor_chat import process_chat_message, approve_workflow_proposal

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ============================================================================
# Request/Response Models
# ============================================================================

class SendMessageRequest(BaseModel):
    """Request to send a message."""
    thread_id: Optional[str] = None
    message: str = Field(..., min_length=1)
    user_id: str = Field(default="default-user")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Create a 30-second TikTok video about AI trends",
                "user_id": "default-user"
            }
        }


class WorkflowProposal(BaseModel):
    """Workflow proposal from supervisor agent."""
    user_request: str
    target_platforms: List[str]
    estimated_cost_usd: Optional[float] = None
    reasoning: Optional[str] = None


class ChatMessageResponse(BaseModel):
    """Chat message response."""
    id: str
    thread_id: str
    role: str  # user, assistant, system
    content: str
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class ChatThreadResponse(BaseModel):
    """Chat thread response."""
    thread_id: str
    title: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    last_message: Optional[str] = None
    active_workflow_id: Optional[str] = None


class SendMessageResponse(BaseModel):
    """Response after sending a message."""
    message: ChatMessageResponse
    thread: ChatThreadResponse
    workflow_created: Optional[Dict[str, Any]] = None


# ============================================================================
# Chat Endpoints
# ============================================================================

@router.get("/threads", response_model=List[ChatThreadResponse])
async def list_threads(
    user_id: str = "default-user",
    session: AsyncSession = Depends(get_session)
):
    """
    List all threads for a user.

    Returns threads sorted by last activity (most recent first).
    """
    try:
        # Get or create default user
        user = await get_or_create_user(session, user_id)

        # Query threads
        result = await session.execute(
            select(Thread)
            .where(Thread.user_id == user.id)
            .where(Thread.status == 'active')
            .order_by(desc(Thread.last_message_at))
        )

        threads = result.scalars().all()

        # Convert to response
        thread_responses = []
        for thread in threads:
            # Get last message
            last_msg_result = await session.execute(
                select(ThreadMessage)
                .where(ThreadMessage.thread_id == thread.id)
                .order_by(desc(ThreadMessage.created_at))
                .limit(1)
            )
            last_message = last_msg_result.scalars().first()

            thread_responses.append(ChatThreadResponse(
                thread_id=str(thread.id),
                title=thread.title or "New Conversation",
                user_id=user_id,
                created_at=thread.created_at,
                updated_at=thread.updated_at,
                message_count=thread.message_count,
                last_message=last_message.content[:100] if last_message else None,
                active_workflow_id=None  # TODO: link to active workflows
            ))

        return thread_responses

    except Exception as e:
        logger.error(f"Error listing threads: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/threads/{thread_id}", response_model=ChatThreadResponse)
async def get_thread(
    thread_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get details of a specific thread."""
    try:
        thread_uuid = uuid.UUID(thread_id)

        result = await session.execute(
            select(Thread).where(Thread.id == thread_uuid)
        )
        thread = result.scalars().first()

        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        # Get user
        user_result = await session.execute(
            select(User).where(User.id == thread.user_id)
        )
        user = user_result.scalars().first()

        # Get last message
        last_msg_result = await session.execute(
            select(ThreadMessage)
            .where(ThreadMessage.thread_id == thread.id)
            .order_by(desc(ThreadMessage.created_at))
            .limit(1)
        )
        last_message = last_msg_result.scalars().first()

        return ChatThreadResponse(
            thread_id=str(thread.id),
            title=thread.title or "New Conversation",
            user_id=user.email if user else "unknown",
            created_at=thread.created_at,
            updated_at=thread.updated_at,
            message_count=thread.message_count,
            last_message=last_message.content[:100] if last_message else None,
            active_workflow_id=None
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid thread ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting thread: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/threads/{thread_id}/messages", response_model=List[ChatMessageResponse])
async def get_messages(
    thread_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get all messages in a thread."""
    try:
        thread_uuid = uuid.UUID(thread_id)

        # Verify thread exists
        thread_result = await session.execute(
            select(Thread).where(Thread.id == thread_uuid)
        )
        thread = thread_result.scalars().first()

        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        # Get messages
        result = await session.execute(
            select(ThreadMessage)
            .where(ThreadMessage.thread_id == thread_uuid)
            .order_by(ThreadMessage.created_at)
        )

        messages = result.scalars().all()

        return [
            ChatMessageResponse(
                id=str(msg.id),
                thread_id=str(msg.thread_id),
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
                metadata=msg.metadata
            )
            for msg in messages
        ]

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid thread ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send", response_model=SendMessageResponse)
async def send_message(
    request: SendMessageRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Send a message to supervisor agent.

    Creates or updates thread, processes message with supervisor agent,
    and returns agent response (potentially with workflow proposal).
    """
    try:
        # Get or create user
        user = await get_or_create_user(session, request.user_id)

        # Get or create thread
        if request.thread_id:
            thread_uuid = uuid.UUID(request.thread_id)
            thread_result = await session.execute(
                select(Thread).where(Thread.id == thread_uuid)
            )
            thread = thread_result.scalars().first()

            if not thread:
                raise HTTPException(status_code=404, detail="Thread not found")
        else:
            # Create new thread
            thread = await create_new_thread(session, user)

        # Save user message
        user_message = ThreadMessage(
            id=uuid.uuid4(),
            thread_id=thread.id,
            role="user",
            content=request.message,
            metadata={}
        )
        session.add(user_message)

        # Update thread
        thread.message_count += 1
        thread.last_message_at = datetime.utcnow()

        # Generate title from first message
        if thread.message_count == 1:
            thread.title = request.message[:50] + ("..." if len(request.message) > 50 else "")

        await session.commit()

        # Process with supervisor agent
        agent_response = await process_chat_message(
            thread_id=str(thread.id),
            user_message=request.message,
            session=session
        )

        # Save agent response
        agent_message = ThreadMessage(
            id=uuid.uuid4(),
            thread_id=thread.id,
            role="assistant",
            content=agent_response["content"],
            metadata=agent_response.get("metadata", {})
        )
        session.add(agent_message)

        thread.message_count += 1
        thread.last_message_at = datetime.utcnow()

        await session.commit()
        await session.refresh(thread)

        # Build response
        return SendMessageResponse(
            message=ChatMessageResponse(
                id=str(agent_message.id),
                thread_id=str(thread.id),
                role=agent_message.role,
                content=agent_message.content,
                created_at=agent_message.created_at,
                metadata=agent_message.metadata
            ),
            thread=ChatThreadResponse(
                thread_id=str(thread.id),
                title=thread.title or "New Conversation",
                user_id=request.user_id,
                created_at=thread.created_at,
                updated_at=thread.updated_at,
                message_count=thread.message_count,
                last_message=agent_message.content[:100],
                active_workflow_id=None
            ),
            workflow_created=agent_response.get("workflow_created")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/threads/{thread_id}/messages/{message_id}/approve")
async def approve_workflow(
    thread_id: str,
    message_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    Approve a workflow proposal and create the workflow.
    """
    try:
        message_uuid = uuid.UUID(message_id)

        # Get message with proposal
        result = await session.execute(
            select(ThreadMessage).where(ThreadMessage.id == message_uuid)
        )
        message = result.scalars().first()

        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        # Check if message has proposal
        if not message.metadata or not message.metadata.get("workflow_proposal"):
            raise HTTPException(status_code=400, detail="Message does not contain a workflow proposal")

        # Create workflow from proposal
        workflow = await approve_workflow_proposal(
            thread_id=thread_id,
            message=message,
            session=session
        )

        return workflow

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/threads/{thread_id}/messages/{message_id}/reject")
async def reject_workflow(
    thread_id: str,
    message_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    Reject a workflow proposal.
    """
    try:
        message_uuid = uuid.UUID(message_id)

        # Get message
        result = await session.execute(
            select(ThreadMessage).where(ThreadMessage.id == message_uuid)
        )
        message = result.scalars().first()

        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        # Update metadata to mark as rejected
        if message.metadata:
            message.metadata["awaiting_approval"] = False
            message.metadata["rejected"] = True
            message.metadata["rejected_at"] = datetime.utcnow().isoformat()

        await session.commit()

        return {"status": "rejected", "message_id": message_id}

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Helper Functions
# ============================================================================

async def get_or_create_user(session: AsyncSession, user_email: str) -> User:
    """Get or create a user."""
    # Try to get existing user
    result = await session.execute(
        select(User).where(User.email == user_email)
    )
    user = result.scalars().first()

    if user:
        return user

    # Create new user
    # First, get or create default tenant
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == "default")
    )
    tenant = tenant_result.scalars().first()

    if not tenant:
        tenant = Tenant(
            id=uuid.uuid4(),
            name="Default Tenant",
            slug="default",
            status="active"
        )
        session.add(tenant)
        await session.flush()

    # Create user
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=user_email,
        name=user_email.split("@")[0] if "@" in user_email else user_email,
        status="active"
    )
    session.add(user)
    await session.flush()

    return user


async def create_new_thread(session: AsyncSession, user: User) -> Thread:
    """Create a new conversation thread."""
    # Get or create supervisor agent
    agent_result = await session.execute(
        select(Agent)
        .where(Agent.type == "supervisor")
        .where(Agent.status == "active")
    )
    agent = agent_result.scalars().first()

    if not agent:
        # Create supervisor agent
        agent = Agent(
            id=uuid.uuid4(),
            tenant_id=user.tenant_id,
            owner_id=user.id,
            name="Supervisor Agent",
            type="supervisor",
            version="1.0.0",
            contract={
                "name": "Supervisor Agent",
                "description": "Orchestrates content creation workflows",
                "capabilities": ["chat", "workflow_creation", "content_planning"]
            },
            status="active"
        )
        session.add(agent)
        await session.flush()

    # Create thread
    thread = Thread(
        id=uuid.uuid4(),
        agent_id=agent.id,
        user_id=user.id,
        tenant_id=user.tenant_id,
        title=None,  # Will be set from first message
        status="active",
        message_count=0
    )
    session.add(thread)
    await session.flush()

    return thread
