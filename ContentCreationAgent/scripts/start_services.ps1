# Content Creation Agent - Service Startup Script
# Starts services in proper order: MCP Server > Backend > Frontend
# Version: 1.0.0
# Date: 2025-10-21

param(
    [switch]$SkipHealthChecks,
    [switch]$Verbose,
    [int]$TimeoutSeconds = 120
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Enable verbose output if requested
if ($Verbose) {
    $VerbosePreference = "Continue"
}

# Color output functions
function Write-SuccessMsg { param($Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-InfoMsg { param($Message) Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
function Write-WarningMsg { param($Message) Write-Host "⚠️  $Message" -ForegroundColor Yellow }
function Write-ErrorMsg { param($Message) Write-Host "❌ $Message" -ForegroundColor Red }
function Write-StepMsg { param($Message) Write-Host "`n🔹 $Message" -ForegroundColor Blue -BackgroundColor Black }

# Configuration
$PORTS = @{
    MCP_SERVER = 8809  # FastMCP server (TypeScript)
    BACKEND_PRIMARY = 8006
    BACKEND_FALLBACK = 8007
    FRONTEND_PRIMARY = 3006
    FRONTEND_FALLBACK = 3007
    POSTGRES = 5433
}

$SERVICES = @(
    @{ Name = "postgres"; WaitFor = 10; HealthCheck = "pg_isready" }
    @{ Name = "piapi-mcp"; WaitFor = 15; HealthCheck = "process" }
    @{ Name = "backend"; WaitFor = 20; HealthCheck = "http" }
    @{ Name = "frontend"; WaitFor = 10; HealthCheck = "http" }
)

# ==============================================================================
# Helper Functions
# ==============================================================================

function Test-DockerRunning {
    Write-Verbose "Checking if Docker is running..."
    try {
        $result = docker info 2>&1
        if ($LASTEXITCODE -ne 0) {
            return $false
        }
        return $true
    }
    catch {
        return $false
    }
}

function Test-PortAvailable {
    param([int]$Port)

    Write-Verbose "Checking if port $Port is available..."
    try {
        $connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if ($connection) {
            Write-Verbose "Port $Port is in use by process $($connection.OwningProcess)"
            return $false
        }
        Write-Verbose "Port $Port is available"
        return $true
    }
    catch {
        Write-Verbose "Port $Port is available (no connections found)"
        return $true
    }
}

function Stop-Service {
    param([string]$ServiceName)

    Write-InfoMsg "Stopping $ServiceName..."
    docker-compose stop $ServiceName 2>&1 | Out-Null

    if ($LASTEXITCODE -eq 0) {
        Write-SuccessMsg "$ServiceName stopped"
    }
    else {
        Write-WarningMsg "Failed to stop $ServiceName (may not be running)"
    }
}

function Start-Service {
    param(
        [string]$ServiceName,
        [int]$WaitSeconds
    )

    Write-StepMsg "Starting $ServiceName..."

    # Start the service
    docker-compose up -d $ServiceName

    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMsg "Failed to start $ServiceName"
        throw "Service startup failed: $ServiceName"
    }

    Write-SuccessMsg "$ServiceName container started"
    Write-InfoMsg "Waiting $WaitSeconds seconds for initialization..."

    # Progress bar for wait
    for ($i = 0; $i -lt $WaitSeconds; $i++) {
        $percent = [math]::Round(($i / $WaitSeconds) * 100)
        Write-Progress -Activity "Starting $ServiceName" -Status "$percent% Complete" -PercentComplete $percent
        Start-Sleep -Seconds 1
    }
    Write-Progress -Activity "Starting $ServiceName" -Completed
}

function Test-ServiceHealth {
    param(
        [string]$ServiceName,
        [string]$HealthCheckType
    )

    if ($SkipHealthChecks) {
        Write-WarningMsg "Skipping health check for $ServiceName (--SkipHealthChecks flag)"
        return $true
    }

    Write-InfoMsg "Checking $ServiceName health..."

    switch ($HealthCheckType) {
        "pg_isready" {
            # PostgreSQL health check
            $result = docker-compose exec -T postgres pg_isready -U agentuser -d content_agent 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-SuccessMsg "$ServiceName is healthy"
                return $true
            }
        }

        "process" {
            # Process-based health check (for MCP server)
            $result = docker-compose exec -T $ServiceName pgrep -f "python -m piapi_mcp_server_python" 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-SuccessMsg "$ServiceName is healthy (process running)"
                return $true
            }
        }

        "http" {
            # HTTP health check
            $port = switch ($ServiceName) {
                "backend" { $PORTS.BACKEND_PRIMARY }
                "frontend" { $PORTS.FRONTEND_PRIMARY }
                default { 8000 }
            }

            try {
                $url = "http://localhost:$port/health"
                if ($ServiceName -eq "frontend") {
                    $url = "http://localhost:$port/"
                }

                $response = Invoke-WebRequest -Uri $url -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
                if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
                    Write-SuccessMsg "$ServiceName is healthy (HTTP $($response.StatusCode))"
                    return $true
                }
            }
            catch {
                Write-Verbose "HTTP health check failed: $_"
            }
        }
    }

    Write-WarningMsg "$ServiceName health check failed"
    return $false
}

function Get-ServiceLogs {
    param([string]$ServiceName, [int]$Lines = 20)

    Write-InfoMsg "Last $Lines lines from $ServiceName logs:"
    docker-compose logs --tail=$Lines $ServiceName
}

# ==============================================================================
# Pre-Flight Checks
# ==============================================================================

Write-Host @"

╔═══════════════════════════════════════════════════════════════╗
║     Content Creation Agent - Service Startup Script          ║
║                      Version 1.0.0                            ║
╚═══════════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

Write-StepMsg "Running pre-flight checks..."

# Check Docker
if (-not (Test-DockerRunning)) {
    Write-ErrorMsg "Docker is not running. Please start Docker Desktop and try again."
    exit 1
}
Write-SuccessMsg "Docker is running"

# Check docker-compose.yml exists
if (-not (Test-Path "docker-compose.yml")) {
    Write-ErrorMsg "docker-compose.yml not found. Please run this script from the project root."
    exit 1
}
Write-SuccessMsg "docker-compose.yml found"

# Check .env file exists
if (-not (Test-Path ".env")) {
    Write-WarningMsg ".env file not found. Using .env.example defaults."
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-InfoMsg "Copied .env.example to .env"
    }
}
else {
    Write-SuccessMsg ".env file found"
}

# Check PiAPI MCP .env.local
$mcpEnvPath = "..\PiAPI_MCP\piapi_fastmcp_server\.env.local"
if (-not (Test-Path $mcpEnvPath)) {
    Write-ErrorMsg "PiAPI MCP .env.local not found at: $mcpEnvPath"
    Write-InfoMsg "Please create this file with PIAPI_API_KEY=your-key-here"
    exit 1
}
Write-SuccessMsg "PiAPI MCP .env.local found"

# Check port availability
Write-InfoMsg "Checking port availability..."
$portsInUse = @()

foreach ($portConfig in $PORTS.GetEnumerator()) {
    if (-not (Test-PortAvailable -Port $portConfig.Value)) {
        $portsInUse += "$($portConfig.Key) ($($portConfig.Value))"
    }
}

if ($portsInUse.Count -gt 0) {
    Write-WarningMsg "The following ports are in use:"
    $portsInUse | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
    Write-InfoMsg "Run './scripts/check_ports.ps1' to automatically resolve conflicts"

    $continue = Read-Host "`nDo you want to continue anyway? (y/N)"
    if ($continue -ne 'y' -and $continue -ne 'Y') {
        Write-InfoMsg "Startup cancelled by user"
        exit 0
    }
}
else {
    Write-SuccessMsg "All required ports are available"
}

# ==============================================================================
# Service Startup Sequence
# ==============================================================================

Write-StepMsg "Starting services in order: Postgres > MCP Server > Backend > Frontend"

# Stop all services first (clean start)
Write-InfoMsg "Stopping any running services..."
docker-compose down 2>&1 | Out-Null
Write-SuccessMsg "All services stopped"

# Startup counter
$successCount = 0
$failedServices = @()

foreach ($service in $SERVICES) {
    $serviceName = $service.Name
    $waitTime = $service.WaitFor
    $healthCheck = $service.HealthCheck

    try {
        # Start service
        Start-Service -ServiceName $serviceName -WaitSeconds $waitTime

        # Health check with retry
        $maxRetries = 3
        $healthy = $false

        for ($retry = 1; $retry -le $maxRetries; $retry++) {
            Write-Verbose "Health check attempt $retry of $maxRetries..."
            $healthy = Test-ServiceHealth -ServiceName $serviceName -HealthCheckType $healthCheck

            if ($healthy) {
                break
            }

            if ($retry -lt $maxRetries) {
                Write-InfoMsg "Retrying health check in 5 seconds..."
                Start-Sleep -Seconds 5
            }
        }

        if ($healthy) {
            $successCount++
        }
        else {
            Write-WarningMsg "$serviceName started but health check failed"
            $failedServices += $serviceName

            if (-not $SkipHealthChecks) {
                Write-InfoMsg "Showing recent logs:"
                Get-ServiceLogs -ServiceName $serviceName -Lines 10
            }
        }
    }
    catch {
        $errorMsg = $_.Exception.Message
        Write-ErrorMsg "Failed to start ${serviceName}: $errorMsg"
        $failedServices += $serviceName
        Get-ServiceLogs -ServiceName $serviceName -Lines 20
    }
}

# ==============================================================================
# Final Status Report
# ==============================================================================

Write-Host @"

╔═══════════════════════════════════════════════════════════════╗
║                      Startup Summary                          ║
╚═══════════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

Write-Host "Services Started: $successCount / $($SERVICES.Count)`n"

# Service status table
$runningServices = docker-compose ps --format json | ConvertFrom-Json

foreach ($service in $SERVICES) {
    $serviceName = $service.Name
    $status = $runningServices | Where-Object { $_.Service -eq $serviceName }

    if ($status -and $status.State -eq "running") {
        $healthStatus = if ($failedServices -contains $serviceName) { "⚠️  Unhealthy" } else { "✅ Healthy" }

        # Determine port
        $port = switch ($serviceName) {
            "postgres" { $PORTS.POSTGRES }
            "piapi-mcp" { $PORTS.MCP_SERVER }
            "backend" { $PORTS.BACKEND_PRIMARY }
            "frontend" { $PORTS.FRONTEND_PRIMARY }
        }

        Write-Host "  $healthStatus  $serviceName".PadRight(35) -NoNewline
        Write-Host "Port: $port" -ForegroundColor Cyan
    }
    else {
        Write-Host "  ❌ FAILED  $serviceName" -ForegroundColor Red
    }
}

# ==============================================================================
# Access URLs
# ==============================================================================

Write-Host @"

╔═══════════════════════════════════════════════════════════════╗
║                       Access Points                           ║
╚═══════════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

Write-Host "  🌐 Frontend UI:      " -NoNewline -ForegroundColor White
Write-Host "http://localhost:$($PORTS.FRONTEND_PRIMARY)" -ForegroundColor Green

Write-Host "  🔧 Backend API:      " -NoNewline -ForegroundColor White
Write-Host "http://localhost:$($PORTS.BACKEND_PRIMARY)" -ForegroundColor Green

Write-Host "  📚 API Docs:         " -NoNewline -ForegroundColor White
Write-Host "http://localhost:$($PORTS.BACKEND_PRIMARY)/docs" -ForegroundColor Green

Write-Host "  🤖 MCP Server:       " -NoNewline -ForegroundColor White
Write-Host "http://localhost:$($PORTS.MCP_SERVER) (internal)" -ForegroundColor Cyan

Write-Host "  🗄️  PostgreSQL:       " -NoNewline -ForegroundColor White
Write-Host "localhost:$($PORTS.POSTGRES)" -ForegroundColor Cyan

# ==============================================================================
# Next Steps
# ==============================================================================

Write-Host @"

╔═══════════════════════════════════════════════════════════════╗
║                        Next Steps                             ║
╚═══════════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

if ($failedServices.Count -eq 0) {
    Write-SuccessMsg "All services started successfully!"
    Write-Host @"

  1. Visit the frontend: http://localhost:$($PORTS.FRONTEND_PRIMARY)
  2. Check API docs: http://localhost:$($PORTS.BACKEND_PRIMARY)/docs
  3. Run health check: docker-compose exec backend python -m backend.validation.system_health_check
  4. View logs: docker-compose logs -f

"@
}
else {
    Write-WarningMsg "Some services failed to start or are unhealthy:"
    $failedServices | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }

    Write-Host @"

Troubleshooting:
  1. Check logs: docker-compose logs [service-name]
  2. Restart service: docker-compose restart [service-name]
  3. Rebuild service: docker-compose up -d --build [service-name]
  4. Full restart: docker-compose down && .\scripts\start_services.ps1

"@
}

# ==============================================================================
# Useful Commands
# ==============================================================================

Write-Host @"
╔═══════════════════════════════════════════════════════════════╗
║                     Useful Commands                           ║
╚═══════════════════════════════════════════════════════════════╝

  View all logs:           docker-compose logs -f
  View specific service:   docker-compose logs -f [service-name]
  Restart service:         docker-compose restart [service-name]
  Stop all services:       docker-compose down
  Check service status:    docker-compose ps

  Services: postgres | piapi-mcp | backend | frontend

"@ -ForegroundColor Gray

# Exit with appropriate code
if ($failedServices.Count -eq 0) {
    exit 0
}
else {
    exit 1
}
