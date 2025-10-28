# Content Creation Agent v3.0.0 - Production Dockerfile
# Enhanced with Mem0 + Qdrant + PiAPI MCP Integration
# LangGraph 1.0.0 + LangChain 1.0.0 stack

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# Added ffmpeg for video processing, postgresql-client for DB health checks
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    ffmpeg \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/

# Create necessary directories
RUN mkdir -p videos logs data

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose ports
# 8501: Streamlit UI (optional)
# 8000: FastAPI backend
EXPOSE 8501 8000

# Health check (FastAPI backend)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8000/health || exit 1

# Default command: Run FastAPI backend
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
