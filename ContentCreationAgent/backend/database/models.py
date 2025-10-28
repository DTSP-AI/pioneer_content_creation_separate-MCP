"""
PostgreSQL Database Models

Schema design follows AGENT_CREATION_STANDARD.md patterns:
- Tenant-based multi-tenancy
- Agent lifecycle management
- Thread-based conversations
- Workflow execution tracking
- Cost tracking per workflow

All tables include:
- UUID primary keys
- Timestamps (created_at, updated_at)
- Soft delete support (status fields)
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey, text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import relationship
from contextlib import asynccontextmanager
from datetime import datetime
import uuid
import logging
import asyncio
from asyncpg.exceptions import CannotConnectNowError

from backend.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

Base = declarative_base()

# Database engine and session factory
engine = None
async_session_factory = None


class Tenant(Base):
    """
    Organization/tenant entity for multi-tenancy.

    Tenants own all agents, users, and workflows.
    """
    __tablename__ = 'tenants'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(String(20), default='active', index=True)  # active, suspended, deleted

    # Relationships
    agents = relationship("Agent", back_populates="tenant", cascade="all, delete-orphan")
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    workflows = relationship("Workflow", back_populates="tenant", cascade="all, delete-orphan")

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base):
    """
    User entity for authentication and ownership.
    """
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    status = Column(String(20), default='active')  # active, inactive, deleted

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    threads = relationship("Thread", back_populates="user", cascade="all, delete-orphan")

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Agent(Base):
    """
    Agent entity with JSON contract storage.

    Follows AGENT_CREATION_STANDARD.md:
    - JSON contract defines agent behavior
    - Database + filesystem storage
    - Version tracking
    - Interaction metrics
    """
    __tablename__ = 'agents'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # Core identity
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False, index=True)  # supervisor, content_creation, tiktok, youtube_shorts
    version = Column(String(20), default='1.0.0')

    # JSON contract (complete agent configuration)
    contract = Column(JSON, nullable=False)

    # Status
    status = Column(String(20), default='active', index=True)  # active, inactive, archived, deleted

    # Metrics
    interaction_count = Column(Integer, default=0)
    last_interaction_at = Column(DateTime, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="agents")
    threads = relationship("Thread", back_populates="agent", cascade="all, delete-orphan")

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Thread(Base):
    """
    Conversation thread for agent-user interactions.

    Threads maintain conversation history and context.
    """
    __tablename__ = 'threads'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id'), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)

    # Thread metadata
    title = Column(String(500), nullable=True)
    status = Column(String(20), default='active', index=True)  # active, archived, deleted

    # Conversation state
    message_count = Column(Integer, default=0)
    last_message_at = Column(DateTime, nullable=True)

    # Memory context summary (optional cached summary)
    context_summary = Column(Text, nullable=True)

    # Relationships
    agent = relationship("Agent", back_populates="threads")
    user = relationship("User", back_populates="threads")
    messages = relationship("ThreadMessage", back_populates="thread", cascade="all, delete-orphan")

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ThreadMessage(Base):
    """
    Individual message in a conversation thread.
    """
    __tablename__ = 'thread_messages'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey('threads.id', ondelete='CASCADE'), nullable=False, index=True)

    # Message content
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)

    # Metadata (tool calls, costs, etc.)
    message_metadata = Column(JSON, nullable=True)

    # Optional feedback
    feedback_score = Column(Float, nullable=True)
    feedback_reason = Column(Text, nullable=True)

    # Relationships
    thread = relationship("Thread", back_populates="messages")

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Workflow(Base):
    """
    Workflow definition for content creation campaigns.

    Represents a reusable workflow configuration.
    """
    __tablename__ = 'workflows'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # Workflow identity
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(50), default='content_distribution')  # content_distribution, scheduled_campaign

    # Configuration
    schedule_config = Column(JSON, nullable=True)  # {platforms, templates, scheduling}

    # Status
    is_active = Column(Boolean, default=True)
    status = Column(String(20), default='active', index=True)  # active, paused, archived
    is_template = Column(Boolean, default=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="workflows")
    executions = relationship("WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan")
    reviews = relationship("ContentReview", back_populates="workflow", cascade="all, delete-orphan")

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkflowExecution(Base):
    """
    Workflow execution tracking.

    Each execution represents one run of a workflow (content creation + distribution).
    Stores LangGraph state checkpoints via workflow_id as thread_id.
    """
    __tablename__ = 'workflow_executions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('workflows.id'), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # Execution state
    status = Column(String(20), default='pending', index=True)  # pending, running, completed, failed
    current_phase = Column(String(50), nullable=True)  # supervisor, content_creation, publishing

    # Input
    user_request = Column(Text, nullable=False)
    target_platforms = Column(JSON, nullable=False)

    # Output assets
    trend_topic = Column(String(500), nullable=True)
    script = Column(Text, nullable=True)
    audio_path = Column(String(500), nullable=True)
    video_path = Column(String(500), nullable=True)
    captions = Column(Text, nullable=True)

    # Publishing results
    publish_results = Column(JSON, nullable=True)  # {platform: {url, status, metrics}}

    # Cost tracking
    cost_breakdown = Column(JSON, nullable=True)  # {service: cost_usd}
    total_cost_usd = Column(Float, default=0.0)

    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Metadata
    execution_metadata = Column(JSON, nullable=True)

    # Relationships
    workflow = relationship("Workflow", back_populates="executions")
    cost_records = relationship("CostTracking", back_populates="execution", cascade="all, delete-orphan")
    review = relationship("ContentReview", back_populates="workflow_execution", uselist=False)

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class CostTracking(Base):
    """
    Detailed cost tracking per workflow execution.

    Tracks API usage and costs for:
    - Claude (script generation)
    - ElevenLabs (TTS)
    - Creatomate (video rendering)
    - Platform APIs (TikTok, YouTube)
    """
    __tablename__ = 'cost_tracking'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey('workflow_executions.id', ondelete='CASCADE'), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)

    # Service identification
    service_name = Column(String(100), nullable=False, index=True)  # claude, elevenlabs, creatomate, tiktok, youtube
    service_type = Column(String(50), nullable=False)  # llm, tts, video_render, upload

    # Usage metrics
    usage_units = Column(Float, nullable=True)  # tokens, characters, renders, uploads
    usage_type = Column(String(50), nullable=True)  # tokens, characters, renders

    # Cost
    cost_usd = Column(Float, nullable=False)
    cost_calculation = Column(JSON, nullable=True)  # {rate, quantity, formula}

    # Metadata
    cost_metadata = Column(JSON, nullable=True)

    # Relationships
    execution = relationship("WorkflowExecution", back_populates="cost_records")

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ContentReview(Base):
    """
    Content review entity for human-in-the-loop approval.

    Workflow:
    1. Content generated → review created (status=pending)
    2. Reviewer approves → status=approved → workflow continues
    3. Reviewer rejects → status=rejected → workflow ends with feedback
    """
    __tablename__ = 'content_reviews'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey('workflows.id'),
        nullable=False,
        index=True
    )
    workflow_execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey('workflow_executions.id'),
        nullable=False,
        index=True
    )
    reviewer_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id'),
        nullable=True  # Null if pending assignment
    )

    # Content references
    asset_type = Column(
        String(50),
        nullable=False
    )  # 'video', 'image', 'audio', 'script'
    asset_url = Column(Text, nullable=True)  # S3/cloud URL or local path
    asset_metadata = Column(JSON, nullable=True)  # Duration, resolution, format, etc.

    # Review state
    status = Column(
        String(20),
        nullable=False,
        default='pending',
        index=True
    )  # pending, in_review, approved, rejected

    # Feedback
    feedback = Column(Text, nullable=True)  # Reviewer comments
    feedback_metadata = Column(JSON, nullable=True)  # Structured feedback

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    assigned_at = Column(DateTime, nullable=True)  # When reviewer assigned
    reviewed_at = Column(DateTime, nullable=True)  # When review completed

    # Relationships
    workflow = relationship("Workflow", back_populates="reviews")
    workflow_execution = relationship("WorkflowExecution", back_populates="review")
    reviewer = relationship("User", foreign_keys=[reviewer_id])


# ============================================================================
# Indexes for query optimization
# ============================================================================

# Additional indexes are created via SQLAlchemy index=True on columns above
# For complex queries, create composite indexes in Alembic migrations:
#
# CREATE INDEX idx_executions_tenant_status ON workflow_executions(tenant_id, status);
# CREATE INDEX idx_executions_created_at ON workflow_executions(created_at DESC);
# CREATE INDEX idx_cost_tracking_tenant_service ON cost_tracking(tenant_id, service_name);


# ============================================================================
# Database Connection Management
# ============================================================================

async def init_database():
    """
    Initialize database connection with retry logic.

    Retries up to 5 times with exponential backoff to handle
    PostgreSQL initialization delays.

    Called during FastAPI startup.
    """
    global engine, async_session_factory

    max_retries = 5
    retry_delay = 2  # seconds

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Database connection attempt {attempt}/{max_retries}")

            # Create async engine
            engine = create_async_engine(
                settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
                echo=settings.ENVIRONMENT == "development",
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True
            )

            # Create async session factory
            async_session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            # Test connection with simple query and create tables
            async with engine.begin() as conn:
                # Test connection
                await conn.execute(text("SELECT 1"))
                # Create all tables
                await conn.run_sync(Base.metadata.create_all)

            logger.info("Database initialized successfully")
            return

        except CannotConnectNowError as e:
            if attempt < max_retries:
                wait_time = retry_delay * attempt  # Exponential backoff
                logger.warning(
                    f"Database not ready (attempt {attempt}/{max_retries}): {e}"
                    f"\nRetrying in {wait_time} seconds..."
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"Database connection failed after {max_retries} attempts"
                )
                raise
        except (asyncio.TimeoutError, ConnectionError) as e:
            # Handle other connection-related errors
            if attempt < max_retries:
                wait_time = retry_delay * attempt
                logger.warning(
                    f"Database connection error (attempt {attempt}/{max_retries}): {e}"
                    f"\nRetrying in {wait_time} seconds..."
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"Database connection failed after {max_retries} attempts: {e}"
                )
                raise

        except Exception as e:
            logger.error(f"Database initialization error: {e}", exc_info=True)
            raise


async def close_database():
    """
    Close database connection.

    Called during FastAPI shutdown.
    """
    global engine

    if engine:
        await engine.dispose()
        logger.info("Database connection closed")


# Session management functions moved to backend/database/connection.py
# Import from there: from backend.database.connection import get_db_session, open_session
