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

from backend.config import get_settings
from backend.database.models import init_database, close_database
from backend.api.routes import router as workflow_router
from backend.api.chat_routes import router as chat_router

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
    - Startup: Initialize database connection
    - Shutdown: Close database connection
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

    yield

    # Shutdown
    logger.info("Shutting down Content Creation & Distribution System...")
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
# Middleware
# ============================================================================

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:3001",
        "http://localhost:3006",  # React CRA dev server
        "http://localhost:3007",  # React CRA fallback
        f"http://{settings.HOST}:{settings.PORT}",
        f"http://{settings.HOST}:3000",
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


# Comprehensive system health check
@app.get("/health/detailed", tags=["health"])
async def detailed_health_check():
    """
    Detailed system health check.

    Validates all critical subsystems:
    - Database (PostgreSQL)
    - Vector store (Qdrant)
    - Memory layer (Mem0)
    - PiAPI MCP server
    - Tool registry

    Returns:
        Detailed health status of all components
    """
    from backend.database.connection import DatabaseConnection
    from backend.memory.manager import MemoryManager
    from backend.integrations.piapi_client import PiAPIMCPClient
    from qdrant_client import QdrantClient
    import asyncio

    health_status = {
        "overall": "healthy",
        "timestamp": None,
        "components": {}
    }

    # 1. PostgreSQL Health
    try:
        db = DatabaseConnection()
        async with db.get_connection() as conn:
            result = await conn.fetchval("SELECT 1")
            health_status["components"]["postgresql"] = {
                "status": "healthy" if result == 1 else "degraded",
                "message": "Database connection successful"
            }
    except Exception as e:
        health_status["components"]["postgresql"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        health_status["overall"] = "degraded"

    # 2. Qdrant Health
    try:
        qdrant_client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port
        )
        collections = qdrant_client.get_collections()
        health_status["components"]["qdrant"] = {
            "status": "healthy",
            "message": f"Connected - {len(collections.collections)} collections",
            "collections_count": len(collections.collections)
        }
    except Exception as e:
        health_status["components"]["qdrant"] = {
            "status": "unhealthy",
            "message": f"Qdrant connection failed: {str(e)}"
        }
        health_status["overall"] = "degraded"

    # 3. Mem0 Health
    try:
        memory_mgr = MemoryManager(
            tenant_id="health_check",
            agent_id="system",
            thread_id="health"
        )
        health_status["components"]["mem0"] = {
            "status": "healthy",
            "message": "Memory manager initialized",
            "namespace": memory_mgr.namespace
        }
    except Exception as e:
        health_status["components"]["mem0"] = {
            "status": "degraded",
            "message": f"Mem0 initialization warning: {str(e)}"
        }

    # 4. PiAPI MCP Health
    piapi_status = "unknown"
    piapi_message = "Not tested"
    try:
        piapi_client = PiAPIMCPClient()
        await piapi_client.connect()

        if piapi_client.is_connected:
            tools = await piapi_client.list_tools()
            piapi_status = "healthy"
            piapi_message = f"MCP connected - {len(tools)} tools available"
        else:
            piapi_status = "degraded"
            piapi_message = "MCP connection failed - using fallback"

        await piapi_client.disconnect()
    except Exception as e:
        piapi_status = "degraded"
        piapi_message = f"MCP unavailable - fallback active: {str(e)}"

    health_status["components"]["piapi_mcp"] = {
        "status": piapi_status,
        "message": piapi_message
    }

    # 5. Tool Registry Health
    try:
        from backend.tools.registry import ToolRegistry
        registry = ToolRegistry()
        health_status["components"]["tool_registry"] = {
            "status": "healthy",
            "message": "Tool registry initialized"
        }
    except Exception as e:
        health_status["components"]["tool_registry"] = {
            "status": "unhealthy",
            "message": f"Tool registry failed: {str(e)}"
        }
        health_status["overall"] = "degraded"

    # Set timestamp
    from datetime import datetime
    health_status["timestamp"] = datetime.utcnow().isoformat()

    # Determine overall status
    component_statuses = [c["status"] for c in health_status["components"].values()]
    if "unhealthy" in component_statuses:
        health_status["overall"] = "unhealthy"
    elif "degraded" in component_statuses:
        health_status["overall"] = "degraded"

    return JSONResponse(health_status)


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
