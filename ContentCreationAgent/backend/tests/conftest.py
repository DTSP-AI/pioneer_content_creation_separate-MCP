"""
Test Configuration and Shared Fixtures

Provides fixtures for:
- Database session management
- Mock services (Mem0, MCP)
- Test data generators
- Async test support
"""

import pytest
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

# Test database configuration
TEST_DATABASE_URL = "postgresql+asyncpg://testuser:testpass@localhost:5433/test_content_agent"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock application settings for testing."""
    from unittest.mock import Mock

    settings = Mock()
    settings.ANTHROPIC_API_KEY = "test_anthropic_key"
    settings.OPENAI_API_KEY = "test_openai_key"
    settings.OPENAI_MODEL = "gpt-4-turbo-test"
    settings.ANTHROPIC_MODEL = "claude-3-5-sonnet-test"
    settings.MEM0_API_KEY = "test_mem0_key"
    settings.MEM0_ORG_ID = "test-org"
    settings.PROJECT_ID = "test-project"
    settings.DATABASE_URL = TEST_DATABASE_URL
    settings.ENVIRONMENT = "test"
    settings.DEBUG = True
    settings.DB_POOL_SIZE = 5
    settings.DB_MAX_OVERFLOW = 10
    settings.MAX_DAILY_COST_USD = 100.0
    settings.MAX_PER_WORKFLOW_COST_USD = 10.0

    return settings


@pytest.fixture
def mock_mem0_client():
    """Mock Mem0 client for testing."""
    mock_client = AsyncMock()
    mock_client.add.return_value = {"id": "test-memory-id", "message": "Added successfully"}
    mock_client.search.return_value = [
        {"content": "test memory content", "metadata": {"relevance": 0.95}}
    ]
    mock_client.update.return_value = {"id": "test-memory-id", "message": "Updated successfully"}
    mock_client.delete.return_value = {"id": "test-memory-id", "message": "Deleted successfully"}
    mock_client.get_all.return_value = []

    return mock_client


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing."""
    mock_client = AsyncMock()
    mock_client.list_tools.return_value = [
        {"name": "generate_video_unified", "description": "Generate video"},
        {"name": "process_image_unified", "description": "Process image"},
        {"name": "generate_audio_unified", "description": "Generate audio"},
    ]
    mock_client.call_tool.return_value = {
        "status": "success",
        "video_url": "https://example.com/video.mp4",
        "duration_seconds": 30
    }

    return mock_client


@pytest.fixture
def mock_workflow_state():
    """Sample workflow state for testing."""
    return {
        "workflow_id": "test-workflow-123",
        "tenant_id": "test-tenant-123",
        "user_id": "test-user-123",
        "thread_id": "test-thread-123",
        "timestamp": "2025-01-23T00:00:00Z",
        "user_request": "Create a video about AI",
        "target_platforms": ["tiktok"],
        "workflow_status": "running",
        "current_phase": "content_creation",
        "retry_count": 0
    }


@pytest.fixture
def mock_database_session():
    """Mock database session for testing."""
    mock_session = AsyncMock()
    mock_session.execute.return_value.scalar_one_or_none.return_value = None
    mock_session.commit.return_value = None
    mock_session.rollback.return_value = None
    mock_session.add.return_value = None
    mock_session.delete.return_value = None

    return mock_session

