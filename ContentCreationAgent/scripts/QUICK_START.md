# Quick Start - Service Startup

## TL;DR - Just Start Everything

```powershell
# One command to start all services in order
.\scripts\start_services.ps1
```

## Service Startup Order

**MUST be in this order:**
1. PostgreSQL (5433) → Database ready
2. PiAPI MCP (7870) → MCP server listening
3. Backend (8006) → API + MCP client connected
4. Frontend (3006) → UI ready

## Common Commands

```powershell
# Standard startup (with health checks)
.\scripts\start_services.ps1

# Fast startup (skip health checks - dev only)
.\scripts\start_services.ps1 -SkipHealthChecks

# Verbose output (troubleshooting)
.\scripts\start_services.ps1 -Verbose

# Fix port conflicts first
.\scripts\check_ports.ps1
.\scripts\start_services.ps1
```

## Access Points

Once started:
- 🌐 **Frontend:** http://localhost:3006
- 🔧 **Backend API:** http://localhost:8006
- 📚 **API Docs:** http://localhost:8006/docs
- 🗄️ **PostgreSQL:** localhost:5433

## Troubleshooting

### Service failed to start?
```powershell
# Check logs
docker-compose logs [service-name]

# Restart specific service
docker-compose restart [service-name]

# Full rebuild
docker-compose down
docker-compose up -d --build
```

### Port conflicts?
```powershell
# Auto-fix ports
.\scripts\check_ports.ps1
```

### MCP connection error?
```powershell
# Restart in order
docker-compose restart piapi-mcp
Start-Sleep -Seconds 15
docker-compose restart backend
```

## Pre-Requisites Checklist

Before running the script:
- [ ] Docker Desktop is running
- [ ] In project root directory
- [ ] `.env` file exists (or will be created from `.env.example`)
- [ ] `PiAPI_MCP/piapi_mcp_server_python/.env.local` exists with `PIAPI_API_KEY`

## Typical Startup Time

- **With health checks:** ~55 seconds
- **Without health checks:** ~15 seconds
- **On slow systems:** up to 2 minutes

## Next Steps After Startup

```powershell
# 1. Verify all systems operational
docker-compose exec backend python -m backend.validation.system_health_check

# 2. Open frontend
Start-Process "http://localhost:3006"

# 3. Check API docs
Start-Process "http://localhost:8006/docs"

# 4. Monitor logs (optional)
docker-compose logs -f
```

## Stop All Services

```powershell
# Stop but keep data
docker-compose down

# Stop and remove data (clean slate)
docker-compose down -v
```

---

**Full Documentation:** [README_START_SERVICES.md](README_START_SERVICES.md)
