"""
Backend Startup Script

Quick startup script for the FastAPI backend server.

Usage:
    python run_backend.py
"""

import uvicorn
from backend.config import get_settings

settings = get_settings()

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower()
    )
