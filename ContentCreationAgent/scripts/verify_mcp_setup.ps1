# FastMCP Server Setup Verification Script
# Validates that the TypeScript FastMCP server is properly configured

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "FastMCP Server Setup Verification" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

$errors = 0
$warnings = 0

# Check 1: .env.local exists (outside ContentCreationAgent)
Write-Host "1. Checking .env.local file..." -NoNewline
if (Test-Path "..\PiAPI_MCP\piapi_fastmcp_server\.env.local") {
    Write-Host " ✅" -ForegroundColor Green

    # Check if API key is set
    $content = Get-Content "..\PiAPI_MCP\piapi_fastmcp_server\.env.local" -Raw
    if ($content -match "PIAPI_API_KEY=(?!your_piapi_api_key_here)[\w]+") {
        Write-Host "   API key is configured" -ForegroundColor Gray
    } else {
        Write-Host "   ⚠️  API key not set or using placeholder" -ForegroundColor Yellow
        $warnings++
    }
} else {
    Write-Host " ❌" -ForegroundColor Red
    Write-Host "   Missing: ..\PiAPI_MCP\piapi_fastmcp_server\.env.local" -ForegroundColor Red
    Write-Host "   Create .env.local with your PIAPI_API_KEY in FastMCP server directory" -ForegroundColor Yellow
    $errors++
}

# Check 2: Dockerfile exists
Write-Host "2. Checking Dockerfile..." -NoNewline
if (Test-Path "..\PiAPI_MCP\piapi_fastmcp_server\Dockerfile") {
    Write-Host " ✅" -ForegroundColor Green
} else {
    Write-Host " ❌" -ForegroundColor Red
    $errors++
}

# Check 3: package.json exists
Write-Host "3. Checking package.json..." -NoNewline
if (Test-Path "..\PiAPI_MCP\piapi_fastmcp_server\package.json") {
    Write-Host " ✅" -ForegroundColor Green
} else {
    Write-Host " ❌" -ForegroundColor Red
    $errors++
}

# Check 4: docker-compose.yml has correct context
Write-Host "4. Checking docker-compose.yml..." -NoNewline
$dockerCompose = Get-Content "docker-compose.yml" -Raw
if ($dockerCompose -match "context:\s+\.\./PiAPI_MCP/piapi_fastmcp_server") {
    Write-Host " ✅" -ForegroundColor Green
} else {
    Write-Host " ❌" -ForegroundColor Red
    Write-Host "   docker-compose.yml has incorrect FastMCP server context" -ForegroundColor Red
    $errors++
}

# Check 5: Backend config uses port 8809
Write-Host "5. Checking backend config..." -NoNewline
$backendConfig = Get-Content "backend\config.py" -Raw
if ($backendConfig -match "8809") {
    Write-Host " ✅" -ForegroundColor Green
} else {
    Write-Host " ⚠️" -ForegroundColor Yellow
    Write-Host "   backend\config.py may use old port 7870" -ForegroundColor Yellow
    $warnings++
}

# Check 6: Verify Node.js version
Write-Host "6. Checking Node.js version..." -NoNewline
try {
    $nodeVersion = node --version 2>&1
    if ($nodeVersion -match "v([2-9][0-9]|1[2-9])\.") {
        Write-Host " ✅" -ForegroundColor Green
        Write-Host "   $nodeVersion" -ForegroundColor Gray
    } else {
        Write-Host " ⚠️" -ForegroundColor Yellow
        Write-Host "   $nodeVersion (Node.js 20+ recommended)" -ForegroundColor Yellow
        $warnings++
    }
} catch {
    Write-Host " ⚠️" -ForegroundColor Yellow
    Write-Host "   Node.js not found in PATH" -ForegroundColor Yellow
    $warnings++
}

# Check 7: Docker is running
Write-Host "7. Checking Docker..." -NoNewline
try {
    docker info *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Host " ✅" -ForegroundColor Green
    } else {
        Write-Host " ⚠️" -ForegroundColor Yellow
        Write-Host "   Docker is not running" -ForegroundColor Yellow
        $warnings++
    }
} catch {
    Write-Host " ⚠️" -ForegroundColor Yellow
    Write-Host "   Docker not found" -ForegroundColor Yellow
    $warnings++
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

if ($errors -eq 0 -and $warnings -eq 0) {
    Write-Host "✅ All checks passed! Ready to build." -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. docker-compose build piapi-mcp" -ForegroundColor White
    Write-Host "  2. docker-compose up -d piapi-mcp" -ForegroundColor White
    Write-Host "  3. docker-compose logs -f piapi-mcp" -ForegroundColor White
} elseif ($errors -eq 0) {
    Write-Host "⚠️  $warnings warning(s) found" -ForegroundColor Yellow
    Write-Host "Setup is functional but could be improved" -ForegroundColor Yellow
} else {
    Write-Host "❌ $errors error(s) and $warnings warning(s) found" -ForegroundColor Red
    Write-Host "Please fix the errors above before continuing" -ForegroundColor Red
}

Write-Host ""
