"""
Configuration Management
Centralized configuration for all services and APIs
"""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings with environment variable loading"""

    model_config = ConfigDict(
        extra="ignore",
        env_file=".env",
        case_sensitive=True
    )

    # Application
    APP_NAME: str = "ContentCreationAgent"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # development, production
    HOST: str = "0.0.0.0"
    PORT: int = 8005
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://agentuser:changeme@localhost:5433/content_agent"
    POSTGRES_PASSWORD: Optional[str] = "changeme"  # For Docker Compose
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Mem0 Memory (semantic memory engine - REPLACES Qdrant)
    MEM0_API_KEY: Optional[str] = None  # Optional: Uses Mem0 Cloud if provided, local otherwise
    MEM0_PROJECT: str = "content-creation-agent"
    MEM0_ORG_ID: Optional[str] = None  # Required for Mem0 Cloud

    # LLM Providers
    ANTHROPIC_API_KEY: Optional[str] = None  # Optional - can use OpenAI instead
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    OPENAI_API_KEY: Optional[str] = None  # For simple routing/chat (low-cost)
    OPENAI_MODEL: str = "gpt-5-nano"  # For fast, low-cost routing
    OPENAI_SCRIPT_MODEL: str = "gpt-5-nano"  # Not used (Claude handles scripts, GPT is fallback)

    # Voice Services
    TTS_PROVIDER: str = "piapi"  # piapi (default) | elevenlabs (future: supervisor voice mode)
    ELEVENLABS_API_KEY: Optional[str] = ""  # Optional - reserved for future supervisor voice mode
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"  # Default Rachel voice (for future use)

    # Video Generation (PiAPI.ai - AI Video Generation)
    # ⚠️ PIAPI_API_KEY should NOT be set in backend .env
    # The API key lives in: PiAPI_MCP/piapi_fastmcp_server/.env.local
    # Backend communicates ONLY with FastMCP server, never directly with PiAPI API
    PIAPI_API_KEY: Optional[str] = None  # DEPRECATED - DO NOT USE - FastMCP server handles API calls
    PIAPI_BASE_URL: str = "https://api.piapi.ai/api/v1"  # Reference only - not used by backend

    # PiAPI FastMCP Server (TypeScript - Model Context Protocol) - REQUIRED
    # Docker service name 'piapi-mcp' resolves via Docker network DNS
    # Port 8809 is the configured FastMCP server port
    # IMPORTANT: Base URL only - MCP SDK will append /sse automatically
    PIAPI_MCP_SERVER_URL: str = "http://piapi-mcp:8809"
    PIAPI_MCP_ENABLED: bool = True  # Must be True - no fallback to direct API

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
    API_PORT: int = 8005
    API_PORT_SECONDARY: int = 8006
    CORS_ORIGINS: list[str] = ["http://localhost:3005", "http://localhost:3006"]

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MESSAGE_QUEUE_SIZE: int = 100

    # LangGraph
    LANGGRAPH_CHECKPOINT_TABLE: str = "langgraph_checkpoints"
    LANGGRAPH_THREAD_TIMEOUT_HOURS: int = 24

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"


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


# Video Model Platform Requirements
# Used for validating platform compatibility during orchestration
VIDEO_MODEL_SPECS = {
    "generate_video_unified": {
        "best_for": ["tiktok", "youtube_shorts", "instagram", "youtube", "linkedin"],
        "max_duration": 10,
        "aspect_ratios": ["9:16", "16:9", "1:1", "4:3", "21:9"]
    }
}

# Platform requirements (dimensions, formats, etc.)
PLATFORM_REQUIREMENTS = {
    "tiktok": {
        "aspect_ratio": "9:16",
        "max_duration_seconds": 60,
        "max_video_size_mb": 287
    },
    "youtube_shorts": {
        "aspect_ratio": "9:16",
        "max_duration_seconds": 60,
        "max_video_size_mb": 500
    }
}


def get_settings() -> Settings:
    """Get application settings instance"""
    return settings
