# Port Conflict Resolution Script (PowerShell)
# Checks if required ports are available and clears them if needed

$ErrorActionPreference = "Stop"

# Required ports
$BACKEND_PORTS = @(8006, 8007)
$FRONTEND_PORTS = @(3006, 3007)
$DATABASE_PORTS = @(5432, 6333, 6379, 8809)  # 8809 = FastMCP server (TypeScript)

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "PORT AVAILABILITY CHECK & RESOLUTION" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Function to check if port is in use
function Test-PortInUse {
    param([int]$Port)

    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        return $connections.Count -gt 0
    } catch {
        # Port is not in use
        return $false
    }
}

# Function to get process using port
function Get-PortProcess {
    param([int]$Port)

    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if ($connections) {
            $pid = $connections[0].OwningProcess
            $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
            return @{
                PID = $pid
                Name = $process.ProcessName
            }
        }
    } catch {
        return $null
    }
    return $null
}

# Function to kill process on port
function Stop-PortProcess {
    param([int]$Port)

    $processInfo = Get-PortProcess -Port $Port

    if ($processInfo) {
        Write-Host "  Killing process $($processInfo.Name) (PID: $($processInfo.PID)) on port $Port..." -ForegroundColor Yellow

        try {
            Stop-Process -Id $processInfo.PID -Force
            Start-Sleep -Seconds 1

            if (Test-PortInUse -Port $Port) {
                Write-Host "  Failed to free port $Port" -ForegroundColor Red
                return $false
            } else {
                Write-Host "  Port $Port freed" -ForegroundColor Green
                return $true
            }
        } catch {
            Write-Host "  Error killing process: $_" -ForegroundColor Red
            return $false
        }
    }
    return $false
}

# Check backend ports (8006-8007)
Write-Host "Checking backend ports (8006-8007)..." -ForegroundColor Yellow
$BACKEND_PORT = $null
foreach ($port in $BACKEND_PORTS) {
    if (Test-PortInUse -Port $port) {
        $processInfo = Get-PortProcess -Port $port
        Write-Host "  Port $port is in use by $($processInfo.Name) (PID: $($processInfo.PID))" -ForegroundColor Yellow

        $response = Read-Host "  Kill process on port $port? (y/n)"
        if ($response -eq 'y') {
            if (Stop-PortProcess -Port $port) {
                $BACKEND_PORT = $port
                break
            }
        }
    } else {
        Write-Host "  Port $port is available" -ForegroundColor Green
        $BACKEND_PORT = $port
        break
    }
}

if (-not $BACKEND_PORT) {
    Write-Host "No available backend ports (8006-8007)" -ForegroundColor Red
    exit 1
}

# Check frontend ports (3006-3007)
Write-Host ""
Write-Host "Checking frontend ports (3006-3007)..." -ForegroundColor Yellow
$FRONTEND_PORT = $null
foreach ($port in $FRONTEND_PORTS) {
    if (Test-PortInUse -Port $port) {
        $processInfo = Get-PortProcess -Port $port
        Write-Host "  Port $port is in use by $($processInfo.Name) (PID: $($processInfo.PID))" -ForegroundColor Yellow

        $response = Read-Host "  Kill process on port $port? (y/n)"
        if ($response -eq 'y') {
            if (Stop-PortProcess -Port $port) {
                $FRONTEND_PORT = $port
                break
            }
        }
    } else {
        Write-Host "  Port $port is available" -ForegroundColor Green
        $FRONTEND_PORT = $port
        break
    }
}

if (-not $FRONTEND_PORT) {
    Write-Host "No available frontend ports (3006-3007)" -ForegroundColor Red
    exit 1
}

# Check database ports
Write-Host ""
Write-Host "Checking database/service ports..." -ForegroundColor Yellow
foreach ($port in $DATABASE_PORTS) {
    if (Test-PortInUse -Port $port) {
        $processInfo = Get-PortProcess -Port $port
        Write-Host "  Port $port is in use by $($processInfo.Name) (likely existing service)" -ForegroundColor Yellow

        $response = Read-Host "  Kill process on port $port? (y/n)"
        if ($response -eq 'y') {
            Stop-PortProcess -Port $port | Out-Null
        }
    } else {
        Write-Host "  Port $port is available" -ForegroundColor Green
    }
}

# Update docker-compose.yml with selected ports
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "Updating docker-compose.yml with selected ports..." -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

# Backup docker-compose.yml
Copy-Item -Path "docker-compose.yml" -Destination "docker-compose.yml.backup" -Force

# Read and update docker-compose.yml
$content = Get-Content "docker-compose.yml" -Raw

# Update backend port
$content = $content -replace '- "\d+:8000"', "- `"$($BACKEND_PORT):8000`""

# Update frontend port
$content = $content -replace '- "\d+:8501"', "- `"$($FRONTEND_PORT):8501`""

# Write updated content
Set-Content -Path "docker-compose.yml" -Value $content

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Green
Write-Host "PORT CONFIGURATION COMPLETE" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Selected Ports:"
Write-Host "  - Backend:  http://localhost:$BACKEND_PORT"
Write-Host "  - Frontend: http://localhost:$FRONTEND_PORT"
Write-Host ""
Write-Host "Next Steps:"
Write-Host "  1. Start services: docker-compose up -d"
Write-Host "  2. Check status:   docker-compose ps"
Write-Host "  3. View logs:      docker-compose logs -f backend"
Write-Host ""
Write-Host "To restore original ports, restore backup:"
Write-Host "  Move-Item docker-compose.yml.backup docker-compose.yml -Force"
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
