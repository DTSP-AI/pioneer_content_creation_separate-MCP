"""
Database Connection Management

Async PostgreSQL connection pool using asyncpg and SQLAlchemy.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text
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

        # Validate URL format
        if not database_url.startswith(("postgresql://", "postgresql+asyncpg://")):
            error_msg = (
                f"Invalid database URL format. Expected 'postgresql://' or 'postgresql+asyncpg://', "
                f"got: {database_url[:30]}..."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Convert postgresql:// to postgresql+asyncpg:// for async engine
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


async def get_db_session():
    """
    FastAPI dependency-safe session generator.

    Used by FastAPI Depends() for route handlers.

    Usage:
        @router.post("/items")
        async def create_item(session: AsyncSession = Depends(get_db_session)):
            result = await session.execute(query)

    Yields:
        AsyncSession: SQLAlchemy async session with auto-commit
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


@asynccontextmanager
async def open_session():
    """
    Manual async context manager for background tasks or scripts.

    Use this for background tasks, CLI scripts, tests, and internal services.
    DO NOT use in FastAPI routes - use get_db_session instead.

    Usage:
        async with open_session() as session:
            result = await session.execute(query)
            await session.commit()

    Yields:
        AsyncSession: SQLAlchemy async session (manual commit required)
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
    Initialize database schema with retry logic.

    Creates all tables defined in models.py.
    Retries up to 5 times with exponential backoff to handle
    PostgreSQL initialization delays.

    Should be called on application startup.
    """
    import asyncio
    from asyncpg.exceptions import CannotConnectNowError

    max_retries = 5
    retry_delay = 2  # seconds

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Database initialization attempt {attempt}/{max_retries}")

            engine = get_async_engine()

            async with engine.begin() as conn:
                # Test connection
                await conn.execute(text("SELECT 1"))
                # Create all tables
                await conn.run_sync(Base.metadata.create_all)

            logger.info("Database schema initialized successfully")
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
