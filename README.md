# Pioneer Content Creation - Separate MCP Architecture

> **AI-Powered Content Creation System with Dedicated MCP Server Architecture**

This repository contains a multi-agent content creation system restructured to separate Model Context Protocol (MCP) concerns from the core application logic.

## 📁 Project Structure

```
pioneer_content_creation_separate-MCP/
├── ContentCreationAgent/          # Main application (multi-agent system)
│   ├── backend/                  # FastAPI + LangGraph workflow
│   ├── frontend/                 # React UI with real-time updates
│   ├── docs/                     # Documentation and implementation guides
│   ├── tests/                    # End-to-end and unit tests
│   └── README.md                 # Complete application documentation
│
├── PiAPI_MCP/                     # MCP Server implementations
│   └── piapi_fastmcp_server/     # FastMCP server for PiAPI.ai integration
│       ├── src/                  # TypeScript MCP server
│       ├── Dockerfile            # Containerized MCP server
│       └── README.md             # MCP server documentation
│
└── README.md                      # This file (project overview)
```

## 🎯 What This System Does

**ContentCreationAgent** is an enterprise-grade multi-agent system that automates end-to-end video content creation and publishing:

1. **Intelligent Request Analysis** - AI supervisor analyzes content ideas with memory-aware routing
2. **Script Generation** - Claude AI creates platform-optimized scripts for TikTok and YouTube
3. **AI Video Production** - PiAPI MCP generates professional videos via state-of-the-art models
4. **Multi-Platform Publishing** - Automatic upload to TikTok and YouTube Shorts with OAuth
5. **Memory & Learning** - Hybrid memory system (Mem0 + Qdrant) remembers past campaigns
6. **Real-Time Monitoring** - Live progress tracking with Server-Sent Events (SSE)

## 🚀 Quick Start

### 1. Navigate to the Main Application

```bash
cd ContentCreationAgent
```

### 2. Follow Setup Instructions

See **[ContentCreationAgent/README.md](ContentCreationAgent/README.md)** for:
- Prerequisites and API keys
- Docker Compose setup
- Port configuration
- Environment variables
- System health checks
- Usage examples

### 3. Optional: Deploy Separate MCP Server

If running the PiAPI MCP server separately:

```bash
cd PiAPI_MCP/piapi_fastmcp_server
```

See **[PiAPI_MCP/piapi_fastmcp_server/README.md](PiAPI_MCP/piapi_fastmcp_server/README.md)** for standalone deployment.

## 🛠️ Tech Stack

### ContentCreationAgent
- **LangGraph** - Multi-agent orchestration
- **Claude AI** - Script generation
- **GPT-5 Nano** - Supervisor routing
- **FastAPI** - Backend API
- **React + TypeScript** - Frontend UI
- **PostgreSQL** - Persistent storage
- **Mem0 + Qdrant** - Hybrid memory

### PiAPI MCP Server
- **FastMCP (TypeScript)** - Model Context Protocol server
- **PiAPI.ai** - Text-to-video generation (Hunyuan, Kling, Luma, Runway, Minimax)
- **Express** - HTTP server for MCP communication
- **Docker** - Containerized deployment

## 📖 Documentation

- **[ContentCreationAgent/README.md](ContentCreationAgent/README.md)** - Complete system documentation
- **[ContentCreationAgent/docs/](ContentCreationAgent/docs/)** - Implementation guides and architecture
- **[PiAPI_MCP/piapi_fastmcp_server/README.md](PiAPI_MCP/piapi_fastmcp_server/README.md)** - MCP server documentation

## 🏗️ Architecture Highlights

### Workflow: Supervisor → Content Creation → Review Gate → [TikTok, YouTube Shorts]

```
User Request
     ↓
SupervisorAgent (GPT-5 Nano)
     ↓
ContentCreationAgent (Claude AI + PiAPI MCP)
     ↓
Review Gate (Human-in-the-loop approval)
     ↓
[TikTokAgent | YouTubeShortsAgent] (Parallel publishing)
     ↓
Results + Metrics
```

### Separation of Concerns

- **ContentCreationAgent**: Core business logic, workflow orchestration, UI
- **PiAPI_MCP**: Video generation services via Model Context Protocol
- **Clean Integration**: MCP client in ContentCreationAgent communicates with MCP server

## 🔑 Key Features

- **Multi-Agent Orchestration** - LangGraph-based workflow with intelligent routing
- **Memory-Aware AI** - Remembers user preferences and past campaign results
- **Real-Time Streaming** - SSE updates for live progress tracking
- **Cost Tracking** - Per-service and per-workflow cost monitoring
- **Human-in-the-Loop** - Optional review gate before publishing
- **Platform Optimization** - TikTok and YouTube Shorts-specific formatting
- **Error Recovery** - Circuit breakers, retry logic, and graceful degradation

## 📊 Access Points (Default Ports)

When running via Docker Compose:

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3006 | React UI |
| Backend API | http://localhost:8006 | FastAPI REST API |
| API Docs | http://localhost:8006/docs | OpenAPI documentation |
| Qdrant | http://localhost:6333 | Vector database |
| PiAPI MCP | http://localhost:8809 | MCP server (if separate) |

## 🎓 Getting Started

**For most users:**
1. Read the main **[ContentCreationAgent/README.md](ContentCreationAgent/README.md)**
2. Configure API keys in `.env`
3. Run `docker-compose up -d` from ContentCreationAgent directory
4. Access the UI at http://localhost:3006

**For advanced deployments:**
- Deploy MCP server separately for scalability
- Use external Qdrant Cloud for vector storage
- Configure Nginx reverse proxy for production

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes in appropriate directory (ContentCreationAgent or PiAPI_MCP)
4. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details.

---

**Built for creators, marketers, and AI enthusiasts**

Version 1.0.0 | January 2025 | Production-Ready
