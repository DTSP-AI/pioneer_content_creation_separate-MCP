"""
FastAPI Main Application

Entry point for Content Creation & Distribution System backend.
Initializes FastAPI app, database, and routes.

Architecture Compliance:
- CORS middleware for frontend integration
- Database connection lifecycle
- Health check endpoints
- Graceful shutdown
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os

from backend.config import get_settings
from backend.database.connection import init_database, close_database
from backend.api.routes import router as workflow_router
from backend.api.chat_routes import router as chat_router
from backend.api.review_routes import router as review_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
settings = get_settings()


# ============================================================================
# Application Lifecycle
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown events:
    - Startup: Initialize database connection and MCP client
    - Shutdown: Close database connection and MCP client
    """
    # Startup
    logger.info("Starting Content Creation & Distribution System...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Host: {settings.HOST}:{settings.PORT}")

    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise

    # FastMCP client uses lazy initialization - will connect on first workflow execution
    logger.info("FastMCP client configured for lazy initialization")

    yield

    # Shutdown
    logger.info("Shutting down Content Creation & Distribution System...")

    # Close MCP client
    try:
        from backend.mcp_client import close_piapi_mcp_client
        await close_piapi_mcp_client()
        logger.info("MCP client connection closed")
    except Exception as e:
        logger.warning(f"Error closing MCP client: {e}")

    # Close database
    try:
        await close_database()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Content Creation & Distribution System",
    description=(
        "Multi-agent system for automated content creation and platform distribution. "
        "Built with LangGraph, Claude, and PiAPI.ai."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# ============================================================================
# Static File Serving
# ============================================================================

# Mount static files for video serving
videos_dir = os.path.join(os.path.dirname(__file__), "..", "videos")
if os.path.exists(videos_dir):
    app.mount("/videos", StaticFiles(directory=videos_dir), name="videos")
    logger.info(f"Mounted /videos directory: {videos_dir}")
else:
    logger.warning(f"Videos directory not found: {videos_dir}")


# ============================================================================
# Middleware
# ============================================================================

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:3001",
        "http://localhost:3005",  # Next.js primary port
        "http://localhost:3006",  # Next.js secondary port
        f"http://{settings.HOST}:{settings.PORT}",
        f"http://{settings.HOST}:3005",
        f"http://{settings.HOST}:3006"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)


# ============================================================================
# Routes
# ============================================================================

# Include workflow routes
app.include_router(workflow_router)

# Include chat routes
app.include_router(chat_router)

# Include review routes
app.include_router(review_router)


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint.

    Returns:
        Service status and version
    """
    return JSONResponse({
        "status": "healthy",
        "service": "content-creation-system",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    })


@app.get("/health/mcp", tags=["health"])
async def mcp_health_check():
    """
    Check FastMCP server (TypeScript) connectivity and tool availability.

    This endpoint tests the FastMCP client connection and reports:
    - Connection status
    - Number of available tools (expected: 4 unified tools)
    - Server URL configuration
    - Tool names

    Returns:
        FastMCP connection status and tool count
    """
    import asyncio
    from backend.mcp_client import get_piapi_mcp_client

    try:
        # Attempt to get or initialize FastMCP client with short timeout
        client, tools = await asyncio.wait_for(
            get_piapi_mcp_client(),
            timeout=5.0
        )

        if client and client._connected:
            return JSONResponse({
                "status": "connected",
                "tools_count": len(tools),
                "expected_tools": 4,
                "server_url": client.server_url,
                "tools": [tool.name for tool in tools],  # All 4 tools
                "message": f"FastMCP client connected successfully with {len(tools)} tools (expected: 4)"
            })
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "disconnected",
                    "tools_count": 0,
                    "message": "FastMCP client not initialized or disabled"
                }
            )

    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=503,
            content={
                "status": "timeout",
                "tools_count": 0,
                "message": "FastMCP server not responding within 5s timeout"
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "tools_count": 0,
                "message": f"FastMCP connection failed: {str(e)}"
            }
        )


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint with API information.

    Returns:
        Welcome message and documentation links
    """
    return JSONResponse({
        "message": "Content Creation & Distribution System API",
        "version": "1.0.0",
        "documentation": f"http://{settings.HOST}:{settings.PORT}/docs",
        "health_check": f"http://{settings.HOST}:{settings.PORT}/health",
        "websocket_example": f"ws://{settings.HOST}:{settings.PORT}/api/ws/workflows/{{workflow_id}}"
    })


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "path": str(request.url)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later."
        }
    )


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level="info"
    )
