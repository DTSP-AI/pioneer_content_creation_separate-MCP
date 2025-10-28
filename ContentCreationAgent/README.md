# Content Creation Agent - AI-Powered Social Media Automation

> **Enterprise-grade multi-agent system for end-to-end automated video content creation, generation, and cross-platform publishing**

**Transform ideas into viral content in minutes** - Powered by **LangGraph**, **Claude AI**, **GPT-5 Nano**, **PiAPI MCP**, **Mem0**, and **Qdrant**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.0-green.svg)](https://langchain.com/langgraph)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docker.com)

---

## 🎯 What This System Does

This is a **production-ready AI content pipeline** that automates the entire content creation lifecycle:

1. **Intelligent Request Analysis** - AI supervisor analyzes your content idea using GPT-5 Nano with memory-aware routing
2. **Script Generation** - Claude AI creates platform-optimized scripts (TikTok hooks, YouTube engagement patterns)
3. **AI Video Production** - PiAPI MCP generates professional videos via Hunyuan, Kling, Luma, Runway, or Minimax models
4. **Multi-Platform Publishing** - Automatic upload to TikTok and YouTube Shorts with OAuth authentication
5. **Memory & Learning** - Hybrid memory system (Mem0 + Qdrant) remembers past campaigns and user preferences
6. **Real-Time Monitoring** - Live progress tracking with Server-Sent Events (SSE) and cost breakdowns

---

## 🚀 Core Capabilities

### 🤖 Multi-Agent AI Orchestration
- **Supervisor Agent (GPT-5 Nano)** - Memory-aware routing with LLM-based intent analysis and structured decision making
- **Content Creation Agent (Claude AI)** - Generates viral scripts optimized for short-form video platforms
- **TikTok Publishing Agent** - Handles OAuth authentication, video validation, and direct uploads
- **YouTube Shorts Agent** - Manages OAuth2 flow, metadata optimization, and Shorts-specific requirements
- **Coordinator Agent** - Orchestrates multi-platform campaigns and aggregates results

### 🧠 Hybrid Memory Architecture
- **Mem0 Semantic Memory** - Stores agent learnings, user preferences, and campaign insights with automatic persistence
- **Qdrant Vector Store** - Self-hosted embeddings for conversation history and semantic search
- **PostgreSQL** - Multi-tenant database with thread persistence, workflow state, and checkpoint management
- **LangGraph Checkpoints** - Enables workflow pause/resume and time-travel debugging
- **Memory-Aware Routing** - Supervisor references past successful campaigns to improve recommendations

### 🎬 AI Video Generation (PiAPI MCP)
- **Multi-Model Support** - Hunyuan, Kling, Luma, Minimax, Runway Gen-3 via Model Context Protocol
- **Professional Quality** - Handles script-to-video, AI voiceover, auto-captions, and platform formatting
- **MCP Server Integration** - TypeScript MCP server exposes 10+ video generation tools
- **Fallback Systems** - ElevenLabs TTS + Creatomate rendering as backup pipeline
- **Video Validation** - FFmpeg checks for codec compliance, resolution, and duration

### 🌐 Cross-Platform Publishing
- **TikTok API** - Direct upload with OAuth, privacy controls, and engagement tracking
- **YouTube Data API v3** - OAuth2 authentication with Shorts optimization and metadata management
- **Retry Logic** - Circuit breakers, exponential backoff, and failure recovery
- **Status Tracking** - Real-time publishing status per platform with detailed error reporting

### 📊 Real-Time Monitoring & Analytics
- **Server-Sent Events (SSE)** - Live workflow progress streaming with phase updates
- **React Frontend** - Modern UI with Framer Motion animations and dark theme
- **Cost Tracking** - Per-service cost breakdown (Claude, PiAPI, embeddings, APIs)
- **Workflow Visualization** - Animated flow diagram showing agent coordination
- **Performance Metrics** - Token usage, API calls, video generation time, upload duration

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                  React Frontend (Port 3006)                       │
│              • Framer Motion animations                          │
│              • Real-time SSE workflow updates                    │
│              • Dark theme UI with cost tracking                  │
└────────────────────────┬─────────────────────────────────────────┘
                         │ HTTP + SSE
┌────────────────────────▼─────────────────────────────────────────┐
│                  FastAPI Backend (Port 8000)                      │
│              • REST API with OpenAPI docs                        │
│              • SSE streaming for real-time updates              │
│              • LangGraph workflow orchestration                  │
└────────────┬─────────────────────────────┬──────────────────────┘
             │                             │
    ┌────────▼────────┐          ┌────────▼────────┐
    │   PostgreSQL    │          │  Hybrid Memory  │
    │    (Port 5432)  │          │   Architecture  │
    │                 │          │                 │
    │ • Multi-tenant  │          │  ┌───────────┐  │
    │   database      │          │  │   Mem0    │  │ Semantic memory
    │ • Thread state  │          │  │ Platform  │  │ (agent learnings)
    │ • Checkpoints   │          │  └─────┬─────┘  │
    │ • Workflow logs │          │        │        │
    └─────────────────┘          │  ┌─────▼─────┐  │
                                 │  │  Qdrant   │  │ Vector search
                                 │  │ (Port 6333)│ │ (conversation)
                                 │  └───────────┘  │
                                 └─────────────────┘
┌──────────────────────────────────────────────────────────────────┐
│                  LangGraph Multi-Agent Workflow                   │
│                        (Single StateGraph)                        │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 1. SupervisorAgent (GPT-5 Nano)                           │  │
│  │    • Retrieves memory context (Mem0 + Qdrant)            │  │
│  │    • LLM-based routing with structured output             │  │
│  │    • Validates request & checks cost limits               │  │
│  │    • Routes to: content_creation | reject | clarify       │  │
│  └──────────────────────┬─────────────────────────────────────┘  │
│                         │                                         │
│  ┌──────────────────────▼─────────────────────────────────────┐  │
│  │ 2. ContentCreationAgent (Claude AI + PiAPI MCP)           │  │
│  │    ┌────────────────────────────────────────────┐         │  │
│  │    │ Tool 1: GoogleSheetsTrendsTool             │         │  │
│  │    │         → Fetch trending topics (optional) │         │  │
│  │    └────────────────────────────────────────────┘         │  │
│  │    ┌────────────────────────────────────────────┐         │  │
│  │    │ Tool 2: VideoScriptGeneratorTool           │         │  │
│  │    │         → Claude AI generates script        │         │  │
│  │    │         → Platform-optimized (TikTok/YT)   │         │  │
│  │    └────────────────────────────────────────────┘         │  │
│  │    ┌────────────────────────────────────────────┐         │  │
│  │    │ Tool 3: PiAPIVideoTool (via FastMCP)      │         │  │
│  │    │    ┌─────────────────────────────────┐     │         │  │
│  │    │    │ FastMCP Server (Port 8809)      │     │         │  │
│  │    │    │  • 4 unified AI generation tools│     │         │  │
│  │    │    │  • Video: Hailuo, Wan, Luma     │     │         │  │
│  │    │    │  • Image: Flux generation       │     │         │  │
│  │    │    │  • Audio: Udio, F5-TTS          │     │         │  │
│  │    │    └─────────────────────────────────┘     │         │  │
│  │    └────────────────────────────────────────────┘         │  │
│  │    Output: video_url, script, captions, cost              │  │
│  └──────────────────────┬─────────────────────────────────────┘  │
│                         │                                         │
│                         │ (Conditional fan-out to platforms)      │
│                         │                                         │
│         ┌───────────────┴───────────────┐                        │
│         │                               │                        │
│  ┌──────▼──────────┐           ┌───────▼──────────┐             │
│  │ 3. TikTokAgent  │           │ 4. YouTubeShorts │             │
│  │                 │ [Parallel]│     Agent        │             │
│  │ • OAuth flow    │           │ • OAuth2 flow    │             │
│  │ • Video upload  │           │ • Shorts upload  │             │
│  │ • Metadata      │           │ • Metadata opt.  │             │
│  │ • Retry logic   │           │ • Retry logic    │             │
│  └─────────┬───────┘           └────────┬─────────┘             │
│            │                            │                        │
│            └────────────┬───────────────┘                        │
│                         ▼                                         │
│                       [END]                                       │
│           publish_results: {tiktok: {...}, youtube: {...}}       │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘

Memory Flow:
─────────────
1. User Request → Supervisor retrieves context from Mem0 + Qdrant
2. Supervisor decision stored to Mem0 (learning from routing)
3. ContentCreation stores script/video metadata to Mem0 + Qdrant
4. Publishing results stored to Mem0 (campaign history)
5. Next workflow uses this history for better recommendations

Data Flow:
──────────
User Request → SupervisorAgent → ContentCreationAgent → PiAPI MCP Server
                      ↓                    ↓                    ↓
                  [Memory]            [Claude AI]          [Video Models]
                      ↓                    ↓                    ↓
                [Mem0+Qdrant]          [Script]          [MP4 with captions]
                      ↓                    ↓                    ↓
              [Past campaigns]    → Video metadata ←    [TikTok + YouTube]
```

---

## 🛠️ Tech Stack

### Backend (Python 3.11+)
- **LangGraph 1.0** - State machine orchestration for multi-agent workflows
- **LangChain 1.0** - Tool integration, chains, and agent frameworks
- **Claude AI (Anthropic)** - Script generation with `claude-3-5-sonnet-20241022`
- **GPT-5 Nano (OpenAI)** - Supervisor routing with structured output and low-latency decisions
- **FastAPI** - High-performance async REST API with automatic OpenAPI docs
- **PostgreSQL 15** - Multi-tenant database with async SQLAlchemy 2.0 ORM
- **Qdrant 1.12** - Vector database for embeddings and semantic search
- **Mem0** - Managed memory platform for agent persistence and learning
- **Pydantic v2** - Type-safe data validation and serialization
- **asyncpg** - High-performance PostgreSQL driver

### Frontend (React + TypeScript)
- **React 18.3** - Modern UI framework with hooks and concurrent rendering
- **TypeScript 5.7** - Type-safe development with strict mode
- **Vite 6.0** - Lightning-fast HMR and optimized production builds
- **Framer Motion 11.11** - Fluid animations and transitions
- **TailwindCSS 3.4** - Utility-first CSS with custom design system
- **Zustand 5.0** - Lightweight state management
- **Axios + EventSource** - REST client with SSE streaming support

### AI & Video Generation
- **PiAPI MCP Server** - Model Context Protocol server for video generation tools
- **Hunyuan, Kling, Luma, Minimax, Runway** - State-of-the-art text-to-video models
- **OpenAI Embeddings** - `text-embedding-3-small` for vector search
- **ElevenLabs** - Text-to-speech fallback system
- **FFmpeg** - Video processing, validation, and transcoding

### Infrastructure
- **Docker Compose** - Multi-service orchestration with health checks
- **Nginx** - Reverse proxy, static file serving, and load balancing
- **PostgreSQL** - Persistent storage with connection pooling
- **Qdrant** - Vector database (local Docker or cloud-hosted)

---

## Quick Start

### Prerequisites

- **Docker** and **Docker Compose**
- **API Keys**:
  - Anthropic (Claude)
  - OpenAI (optional)
  - Mem0
  - PiAPI
- **Platform OAuth** (optional):
  - TikTok Developer App
  - Google Cloud Project (YouTube)

### 1. Port Configuration

Run the port checker to ensure ports are available:

**Windows:**
```powershell
.\scripts\check_ports.ps1
```

**Linux/Mac:**
```bash
bash scripts/check_ports.sh
```

This will:
- Check ports 8006/8007 (backend) and 3006/3007 (frontend)
- Kill blocking processes if needed
- Update `docker-compose.yml` with available ports

### 2. Configure Environment

```bash
# Copy environment template
cp .env.docker .env

# Edit .env and add your API keys
nano .env
```

**Required environment variables:**
```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
MEM0_API_KEY=m0-...
PIAPI_API_KEY=...
POSTGRES_PASSWORD=changeme_in_production
```

### 3. Start Services

**Recommended:** Use the automated startup script (PowerShell):

```powershell
# Start all services in correct order with health checks
.\scripts\start_services.ps1

# Or skip health checks for faster startup (development)
.\scripts\start_services.ps1 -SkipHealthChecks
```

**Manual startup:**

```bash
# Build and start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

**Note:** The automated script ensures services start in the correct order (Postgres → MCP Server → Backend → Frontend) and verifies health before proceeding. See [scripts/README_START_SERVICES.md](scripts/README_START_SERVICES.md) for details.

### 4. Verify System Health

```bash
docker-compose exec backend python -m backend.validation.system_health_check
```

**Expected output:**
```
✅ PASS [Configuration] Required API keys present
✅ PASS [Database] PostgreSQL connection
✅ PASS [Qdrant] Service health check
✅ PASS [Mem0] API connectivity
✅ PASS [PiAPI MCP] Server connectivity
✅ PASS [Tool Registry] Hybrid tool loading
✅ PASS [LangGraph] Entry point is supervisor
✅ ALL SYSTEMS OPERATIONAL
```

---

## Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:3006 | React UI with real-time updates |
| **Backend API** | http://localhost:8006 | FastAPI REST API |
| **API Docs** | http://localhost:8006/docs | Interactive OpenAPI documentation |
| **Qdrant Dashboard** | http://localhost:6333/dashboard | Vector store management |
| **PostgreSQL** | localhost:5432 | Database access |

---

## Usage

### Create a Workflow (API)

```bash
curl -X POST http://localhost:8006/api/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "user_request": "Create a 30-second TikTok video about AI trends in 2025",
    "target_platforms": ["tiktok"],
    "cost_limit_usd": 5.0
  }'
```

**Response:**
```json
{
  "workflow_id": "wf_abc123",
  "workflow_status": "pending",
  "user_request": "Create a 30-second TikTok video about AI trends in 2025",
  "target_platforms": ["tiktok"],
  "current_phase": "supervisor",
  "created_at": "2025-10-17T10:30:00Z"
}
```

### Stream Real-Time Updates (SSE)

```bash
curl -N http://localhost:8006/api/workflows/wf_abc123/stream
```

**Event stream:**
```
data: {"event_type": "phase_update", "current_phase": "content_creation", "message": "Generating script..."}
data: {"event_type": "phase_update", "current_phase": "content_creation", "message": "Creating video..."}
data: {"event_type": "phase_update", "current_phase": "publishing", "message": "Uploading to TikTok..."}
data: {"event_type": "workflow_complete", "video_path": "/app/videos/wf_abc123.mp4"}
```

### List Workflows

```bash
curl http://localhost:8006/api/workflows
```

### Get Workflow Details

```bash
curl http://localhost:8006/api/workflows/wf_abc123
```

---

## Frontend Features

The React frontend provides:

- **Dashboard** - Overview with stats and workflow creation
- **Workflow Detail** - Real-time progress with visual graph
- **Workflow Visualization** - Animated flow diagram
- **Cost Breakdown** - Service-level cost analysis
- **Platform Status** - Publishing results per platform
- **Dark Theme** - Glass morphism effects

See [frontend/README.md](frontend/README.md) for more details.

---

## Development

### Backend Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (without Docker)
uvicorn backend.api.main:app --reload --port 8006
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start dev server with hot reload
npm run dev

# Build for production
npm run build
```

### Run Tests

```bash
# Backend tests
docker-compose exec backend pytest -v

# End-to-end test
docker-compose exec backend python -m tests.test_end_to_end

# Frontend tests (coming soon)
cd frontend
npm test
```

---

## Configuration

### Port Configuration (LAW)

**DO NOT CHANGE WITHOUT UPDATING DOCUMENTATION:**

- Backend: `8006` (fallback `8007`)
- Frontend: `3006` (fallback `3007`)
- PostgreSQL: `5432`
- Qdrant: `6333`
- FastMCP (TypeScript): `8809`

Use port check scripts to automatically detect and resolve conflicts.

### Environment Variables

See `.env` for full configuration. **Critical variables:**

```bash
# ============================================================================
# AI SERVICES (REQUIRED)
# ============================================================================
# Anthropic Claude for script generation and content creation
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# OpenAI for embeddings and supervisor routing
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5-nano  # GPT-5 Nano for fast supervisor decisions

# ============================================================================
# MEMORY SYSTEMS (REQUIRED)
# ============================================================================
# Mem0 Persistent Memory
MEM0_API_KEY=m0-...
MEM0_PROJECT=content-creation-agent
MEM0_STORE=local  # or 'remote' for cloud

# Qdrant Vector Store
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=content_creation_memory
QDRANT_API_KEY=  # Optional for Qdrant Cloud

# PostgreSQL Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/content_creation

# ============================================================================
# VIDEO GENERATION (REQUIRED) - PiAPI.ai
# ============================================================================
PIAPI_API_KEY=...  # Set in FastMCP server's .env.local
PIAPI_BASE_URL=https://api.piapi.ai/api/v1

# FastMCP Server (TypeScript - Model Context Protocol)
PIAPI_MCP_SERVER_URL=http://127.0.0.1:8809
PIAPI_MCP_ENABLED=true

# ============================================================================
# SOCIAL MEDIA PUBLISHING (OPTIONAL)
# ============================================================================
# TikTok API
TIKTOK_ACCESS_TOKEN=...
TIKTOK_CLIENT_KEY=...
TIKTOK_CLIENT_SECRET=...

# YouTube Data API v3
YOUTUBE_CLIENT_ID=...
YOUTUBE_CLIENT_SECRET=...
YOUTUBE_REFRESH_TOKEN=...

# ============================================================================
# COST TRACKING
# ============================================================================
MAX_DAILY_COST_USD=50.0
MAX_PER_WORKFLOW_COST_USD=5.0

# ============================================================================
# FALLBACK SERVICES (OPTIONAL)
# ============================================================================
# ElevenLabs TTS (if PiAPI unavailable)
ELEVENLABS_API_KEY=...

# Creatomate video rendering (if PiAPI unavailable)
CREATOMATE_API_KEY=...
CREATOMATE_TEMPLATE_ID=...
```

### LangGraph Configuration

The workflow is defined in `backend/workflow/graph.py`:

```python
graph = StateGraph(WorkflowState)
graph.add_node("supervisor", supervisor_node)
graph.add_node("content_creation", content_creation_node)
graph.add_node("publishing", publishing_node)
graph.set_entry_point("supervisor")
```

---

## Project Structure

```
ContentCreationAgent/
├── backend/                    # Python backend
│   ├── api/                   # FastAPI routes
│   │   ├── main.py           # API entry point
│   │   └── routes/           # Endpoint handlers
│   ├── workflow/              # LangGraph workflow
│   │   ├── graph.py          # Workflow definition
│   │   ├── nodes/            # Agent nodes
│   │   └── state.py          # State schema
│   ├── services/              # Business logic
│   │   ├── memory/           # Mem0 + Qdrant
│   │   ├── piapi/            # PiAPI MCP client
│   │   └── publishing/       # Platform uploaders
│   ├── database/              # PostgreSQL models
│   └── validation/            # Health checks
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── components/       # Reusable UI
│   │   ├── pages/            # Dashboard, WorkflowDetail
│   │   ├── hooks/            # useWorkflowStream
│   │   ├── services/         # API client
│   │   ├── store/            # Zustand state
│   │   └── types/            # TypeScript types
│   ├── Dockerfile            # Multi-stage build
│   └── nginx.conf            # Nginx config
├── ../PiAPI_MCP/              # FastMCP server (outside project)
│   └── piapi_fastmcp_server/  # TypeScript FastMCP server (active)
├── scripts/                   # Utilities
│   ├── check_ports.ps1       # Windows port checker
│   └── check_ports.sh        # Unix port checker
├── docker-compose.yml         # Service orchestration
├── .env.docker               # Environment template
├── START_LOCAL.md            # Quick start guide
└── README.md                 # This file
```

---

## Troubleshooting

### Port Conflicts

If you see "port is already allocated":

```bash
# Windows
.\scripts\check_ports.ps1

# Linux/Mac
bash scripts/check_ports.sh
```

### Backend Won't Start

```bash
# Check logs
docker-compose logs backend

# Common issues:
# 1. Missing API keys → Check .env
# 2. Database not ready → Wait 10s and restart
# 3. Port conflict → Run port checker
```

### Database Connection Failed

```bash
# Check PostgreSQL
docker-compose exec postgres pg_isready -U agentuser

# Restart services
docker-compose restart backend
```

### Frontend Build Fails

```bash
# Rebuild frontend
cd frontend
rm -rf node_modules dist
npm install
npm run build

# Rebuild Docker image
docker-compose build frontend
docker-compose up -d frontend
```

See [START_LOCAL.md](START_LOCAL.md) for detailed troubleshooting.

---

## Cost Tracking

The system tracks costs at multiple levels:

- **Per-service costs**: Claude, PiAPI, memory operations
- **Per-workflow limits**: Configurable maximum cost
- **Daily limits**: Global spending cap
- **Real-time monitoring**: SSE updates include cost data

Cost breakdown is available in:
- API responses (`cost_breakdown` field)
- Frontend UI (CostBreakdown component)
- Database (persisted per workflow)

---

## Security

- **API Keys**: Stored in `.env` (never committed)
- **OAuth Tokens**: Stored in `secrets/` directory (gitignored)
- **Database Credentials**: Configurable via environment
- **Network Isolation**: Docker bridge network
- **HTTPS**: Nginx reverse proxy (production)

---

## Performance

- **Async I/O**: All database and API calls use async/await
- **Connection Pooling**: SQLAlchemy + asyncpg
- **SSE Streaming**: Minimal latency for real-time updates
- **Vector Search**: Qdrant HNSW index
- **Caching**: Redis support (optional)

---

## 🎯 Full System Scope

### What This System Does (End-to-End)

#### 1️⃣ Intelligent Content Planning
- **Natural Language Input** - "Create a 30-second TikTok about AI trends"
- **Memory-Aware Analysis** - Supervisor references past campaigns and learnings
- **Structured Routing** - GPT-5 Nano makes intelligent decisions with confidence scores
- **Cost Estimation** - Pre-flight cost calculation with budget enforcement

#### 2️⃣ AI-Powered Script Generation
- **Platform Optimization** - TikTok hooks vs YouTube engagement patterns
- **Audience Targeting** - Gen Z slang, millennial references, or professional tone
- **Claude Integration** - Uses latest Claude 3.5 Sonnet for creative writing
- **Template Support** - Viral script structures (hook → problem → solution → CTA)

#### 3️⃣ Professional Video Production
- **PiAPI MCP Integration** - Text-to-video via Model Context Protocol
- **Multi-Model Selection** - Choose Hunyuan (fast), Kling (quality), Runway (cinematic)
- **Auto-Captions** - AI-generated subtitles synced to voiceover
- **Platform Formatting** - 9:16 aspect ratio, 30-60s duration, codec optimization

#### 4️⃣ Cross-Platform Publishing
- **OAuth Automation** - Handles TikTok and YouTube authentication flows
- **Metadata Optimization** - Hashtags, descriptions, privacy settings per platform
- **Retry Logic** - Circuit breakers for API failures with exponential backoff
- **Status Tracking** - Real-time upload progress and error reporting

#### 5️⃣ Memory & Learning
- **Campaign History** - Stores every workflow with results and performance
- **User Preferences** - Remembers content style, audience, and past successes
- **Semantic Search** - Qdrant vector similarity for related campaigns
- **Thread Persistence** - Multi-turn conversations with context retention

#### 6️⃣ Real-Time Monitoring
- **Live Progress** - SSE streams phase updates (supervisor → script → video → publish)
- **Cost Breakdown** - Per-service spending (Claude tokens, PiAPI credits, API calls)
- **Workflow Visualization** - Animated graph showing agent coordination
- **Error Recovery** - Graceful degradation with detailed error messages

---

## 🗺️ Roadmap

### ✅ Current Version (v1.0)
- [x] LangGraph multi-agent orchestration
- [x] GPT-5 Nano supervisor routing
- [x] Claude AI script generation
- [x] PiAPI MCP video generation
- [x] TikTok + YouTube publishing
- [x] Hybrid memory (Mem0 + Qdrant)
- [x] Real-time SSE streaming
- [x] React frontend with animations
- [x] Multi-tenant PostgreSQL database
- [x] Cost tracking and limits

### 🚧 Next Release (v1.1)
- [ ] Multi-user authentication (Clerk/Auth0)
- [ ] Workflow templates and presets
- [ ] Advanced video editing (transitions, effects)
- [ ] Instagram Reels support
- [ ] Scheduled publishing with cron jobs
- [ ] Analytics dashboard (views, engagement, virality score)

### 🔮 Future (v2.0)
- [ ] A/B testing for content variants
- [ ] Custom branding and watermarks
- [ ] Team collaboration features
- [ ] Voice cloning with ElevenLabs
- [ ] Multi-language support
- [ ] API rate limiting and quotas
- [ ] Content moderation and compliance checks

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow existing code style
- Add tests for new features
- Update documentation
- Use type hints (Python) and TypeScript
- Run linters before committing

---

## License

MIT License - see LICENSE file for details.

---

## Support

- **Documentation**: See [START_LOCAL.md](START_LOCAL.md)
- **API Docs**: http://localhost:8006/docs (when running)
- **Issues**: GitHub Issues
- **Discord**: [Coming soon]

---

## 🙏 Acknowledgments

This system leverages cutting-edge AI technologies:

- **LangGraph** - Multi-agent orchestration and workflow management
- **Anthropic Claude** - Industry-leading AI for creative script generation
- **OpenAI GPT-5 Nano** - Fast, cost-effective supervisor routing
- **PiAPI** - State-of-the-art text-to-video generation API
- **Mem0** - Managed memory platform for agent persistence
- **Qdrant** - High-performance vector database
- **LangChain** - Tool integration and agent frameworks

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🎯 Project Vision

**Democratize content creation through AI automation.**

This system represents the future of social media marketing:
- **Zero video editing skills required**
- **Professional quality at scale**
- **Memory-aware AI that learns from your brand**
- **Multi-platform distribution in minutes**
- **Cost-effective with transparent pricing**

Whether you're a solo creator, marketing agency, or enterprise brand, this system scales from 1 to 1000+ videos per day.

---

**Built with ❤️ for content creators, marketers, and AI enthusiasts**

Version 1.0.0 | January 2025 | Production-Ready
