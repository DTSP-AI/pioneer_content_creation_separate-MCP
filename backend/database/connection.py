"""
Database Connection Management

Async PostgreSQL connection pool using asyncpg and SQLAlchemy.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager
import logging

from backend.config import get_settings
from backend.database.models import Base

logger = logging.getLogger(__name__)
settings = get_settings()

# Global engine instance
_engine = None
_session_factory = None


def get_async_engine():
    """
    Get or create async SQLAlchemy engine.

    Returns:
        AsyncEngine: SQLAlchemy async engine instance
    """
    global _engine

    if _engine is None:
        database_url = settings.DATABASE_URL

        # Convert postgresql:// to postgresql+asyncpg://
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        _engine = create_async_engine(
            database_url,
            echo=settings.DEBUG,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_pre_ping=True,  # Verify connections before using
            poolclass=NullPool if "sqlite" in database_url else None
        )

        logger.info(f"Database engine created: {database_url.split('@')[-1]}")  # Log without credentials

    return _engine


def get_session_factory():
    """
    Get or create async session factory.

    Returns:
        async_sessionmaker: Factory for creating async sessions
    """
    global _session_factory

    if _session_factory is None:
        engine = get_async_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    return _session_factory


@asynccontextmanager
async def get_db_session():
    """
    Async context manager for database sessions.

    Usage:
        async with get_db_session() as session:
            result = await session.execute(query)
            await session.commit()

    Yields:
        AsyncSession: SQLAlchemy async session
    """
    session_factory = get_session_factory()
    session = session_factory()

    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        await session.close()


async def init_database():
    """
    Initialize database schema.

    Creates all tables defined in models.py.
    Should be called on application startup.
    """
    engine = get_async_engine()

    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database schema initialized")


async def close_database():
    """
    Close database connections.

    Should be called on application shutdown.
    """
    global _engine, _session_factory

    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None

    logger.info("Database connections closed")
