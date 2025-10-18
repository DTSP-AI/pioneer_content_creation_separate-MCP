"""
Configuration Management
Centralized configuration for all services and APIs
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings with environment variable loading"""

    # Application
    APP_NAME: str = "ContentCreationAgent"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # development, production
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/content_creation"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Mem0 Memory
    MEM0_API_KEY: str
    MEM0_ORG_ID: Optional[str] = None

    # Qdrant Vector Store (for conversation history)
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "content_creation_memory"
    QDRANT_API_KEY: Optional[str] = None  # For Qdrant Cloud

    # LLM Providers
    ANTHROPIC_API_KEY: str
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    OPENAI_API_KEY: str  # Required for embeddings and optionally for GPT models
    OPENAI_MODEL: str = "gpt-5-nano"  # For supervisor routing

    # Voice Services
    ELEVENLABS_API_KEY: str
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"  # Default Rachel voice

    # Video Generation (PiAPI.ai - AI Video Generation)
    PIAPI_API_KEY: str
    PIAPI_BASE_URL: str = "https://api.piapi.ai/api/v1"

    # PiAPI MCP Server (Model Context Protocol)
    PIAPI_MCP_SERVER_URL: str = "http://127.0.0.1:7870/sse"
    PIAPI_MCP_ENABLED: bool = True  # Use MCP for advanced features

    # Legacy Video Rendering (optional fallback)
    CREATOMATE_API_KEY: Optional[str] = None
    CREATOMATE_TEMPLATE_ID: Optional[str] = None

    # Social Media APIs
    TIKTOK_ACCESS_TOKEN: Optional[str] = None
    TIKTOK_CLIENT_KEY: Optional[str] = None
    TIKTOK_CLIENT_SECRET: Optional[str] = None

    YOUTUBE_CLIENT_ID: Optional[str] = None
    YOUTUBE_CLIENT_SECRET: Optional[str] = None
    YOUTUBE_REFRESH_TOKEN: Optional[str] = None

    # Google Sheets (for trend data)
    GOOGLE_SHEETS_CREDENTIALS_PATH: Optional[str] = None
    GOOGLE_SHEETS_SPREADSHEET_ID: Optional[str] = None
    GOOGLE_SHEETS_RANGE: str = "Trends!A2:C100"

    # Cost Tracking
    MAX_DAILY_COST_USD: float = 50.0
    MAX_PER_WORKFLOW_COST_USD: float = 5.0

    # Campaign Scheduling
    ENABLE_SCHEDULING: bool = True
    DEFAULT_TIMEZONE: str = "UTC"

    # FastAPI
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MESSAGE_QUEUE_SIZE: int = 100

    # LangGraph
    LANGGRAPH_CHECKPOINT_TABLE: str = "langgraph_checkpoints"
    LANGGRAPH_THREAD_TIMEOUT_HOURS: int = 24

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


# Cost tracking configuration
COST_PER_1K_TOKENS = {
    "claude-3-5-sonnet-20241022": {
        "input": 0.003,
        "output": 0.015
    },
    "claude-3-haiku-20240307": {
        "input": 0.00025,
        "output": 0.00125
    }
}

COST_PER_CHARACTER_TTS = 0.00003  # ElevenLabs pricing
COST_PER_VIDEO_RENDER = 0.05  # Creatomate estimate
COST_PER_PIAPI_VIDEO = 0.10  # PiAPI.ai estimate (varies by model)


def get_settings() -> Settings:
    """Get application settings instance"""
    return settings
