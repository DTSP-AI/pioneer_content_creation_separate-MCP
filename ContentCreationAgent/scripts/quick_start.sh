#!/bin/bash
# Quick Start Script for Local Testing
# Automates the setup and validation process

set -e  # Exit on error

echo "================================================================================"
echo "CONTENT CREATION AGENT v3.0.0 - QUICK START"
echo "================================================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check prerequisites
echo "📋 Step 1: Checking prerequisites..."
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker installed${NC}"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose not found. Please install Docker Compose.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker Compose installed${NC}"

# Check .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Copying from .env.docker...${NC}"
    cp .env.docker .env
    echo -e "${YELLOW}⚠️  Please edit .env and add your API keys before continuing!${NC}"
    echo ""
    echo "Required keys:"
    echo "  - ANTHROPIC_API_KEY"
    echo "  - OPENAI_API_KEY"
    echo "  - MEM0_API_KEY"
    echo "  - PIAPI_API_KEY"
    echo ""
    read -p "Press Enter after you've added your API keys..."
fi
echo -e "${GREEN}✅ .env file exists${NC}"

# Step 2: Start Docker services
echo ""
echo "================================================================================"
echo "🚀 Step 2: Starting Docker services..."
echo "================================================================================"
echo ""

echo "Starting PostgreSQL, Qdrant, PiAPI MCP, and Backend..."
docker-compose up -d

echo ""
echo "Waiting for services to be ready..."
sleep 10

# Step 3: Check service health
echo ""
echo "================================================================================"
echo "🏥 Step 3: Checking service health..."
echo "================================================================================"
echo ""

# Check PostgreSQL
if docker-compose exec -T postgres pg_isready -U agentuser &> /dev/null; then
    echo -e "${GREEN}✅ PostgreSQL is healthy${NC}"
else
    echo -e "${RED}❌ PostgreSQL is not ready${NC}"
fi

# Check Qdrant
if curl -f http://localhost:6333/health &> /dev/null; then
    echo -e "${GREEN}✅ Qdrant is healthy${NC}"
else
    echo -e "${RED}❌ Qdrant is not ready${NC}"
fi

# Check Backend
if curl -f http://localhost:8000/health &> /dev/null; then
    echo -e "${GREEN}✅ Backend is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  Backend is starting... (this may take a minute)${NC}"
fi

# Step 4: Run system health check
echo ""
echo "================================================================================"
echo "🔍 Step 4: Running comprehensive system health check..."
echo "================================================================================"
echo ""

docker-compose exec backend python -m backend.validation.system_health_check

HEALTH_CHECK_EXIT_CODE=$?

if [ $HEALTH_CHECK_EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All systems operational!${NC}"
else
    echo ""
    echo -e "${YELLOW}⚠️  Some systems have issues (see above)${NC}"
    echo -e "${YELLOW}   This may be expected if external services are not configured${NC}"
fi

# Step 5: Summary
echo ""
echo "================================================================================"
echo "📊 QUICK START COMPLETE"
echo "================================================================================"
echo ""
echo "Service URLs:"
echo "  - Backend API:      http://localhost:8000"
echo "  - API Docs:         http://localhost:8000/docs"
echo "  - Qdrant Dashboard: http://localhost:6333/dashboard"
echo "  - PostgreSQL:       localhost:5432"
echo ""
echo "Useful commands:"
echo "  - View logs:        docker-compose logs -f backend"
echo "  - Restart backend:  docker-compose restart backend"
echo "  - Stop all:         docker-compose down"
echo "  - Run tests:        docker-compose exec backend pytest"
echo "  - Health check:     docker-compose exec backend python -m backend.validation.system_health_check"
echo ""
echo "Next steps:"
echo "  1. Test the API:    curl -X POST http://localhost:8000/api/workflows \\"
echo "                        -H 'Content-Type: application/json' \\"
echo "                        -d '{\"user_request\":\"Create AI video\",\"target_platforms\":[\"tiktok\"]}'"
echo ""
echo "  2. Run E2E test:    docker-compose exec backend python -m tests.test_end_to_end"
echo ""
echo "  3. Start UI:        docker-compose --profile ui up -d"
echo ""
echo "================================================================================"
