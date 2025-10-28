# Database Session Management Guardrails - Local Check Script
# Run this before committing to ensure session management patterns are correct

$ErrorCount = 0

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "🔒 Database Session Management Guardrails Check" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# Check 1: Invalid Depends(get_session)
Write-Host "🔍 Checking for invalid Depends(get_session)..." -NoNewline
$matches = Select-String -Path "backend\api\*.py" -Pattern "Depends\(get_session\)" -Exclude "*NEVER use*"
if ($matches) {
    Write-Host " ❌ FAILED" -ForegroundColor Red
    Write-Host "   Found invalid Depends(get_session) in:" -ForegroundColor Red
    $matches | ForEach-Object { Write-Host "   - $($_.Filename):$($_.LineNumber)" -ForegroundColor Red }
    $ErrorCount++
} else {
    Write-Host " ✅ PASSED" -ForegroundColor Green
}

# Check 2: Invalid Depends(get_db)
Write-Host "🔍 Checking for invalid Depends(get_db)..." -NoNewline
$matches = Select-String -Path "backend\api\*.py" -Pattern "Depends\(get_db\)" -Exclude "*NEVER use*"
if ($matches) {
    Write-Host " ❌ FAILED" -ForegroundColor Red
    Write-Host "   Found invalid Depends(get_db) in:" -ForegroundColor Red
    $matches | ForEach-Object { Write-Host "   - $($_.Filename):$($_.LineNumber)" -ForegroundColor Red }
    $ErrorCount++
} else {
    Write-Host " ✅ PASSED" -ForegroundColor Green
}

# Check 3: Invalid Depends(get_async_session)
Write-Host "🔍 Checking for invalid Depends(get_async_session)..." -NoNewline
$matches = Select-String -Path "backend\**\*.py" -Pattern "Depends\(get_async_session\)" -Exclude "*NEVER use*"
if ($matches) {
    Write-Host " ❌ FAILED" -ForegroundColor Red
    Write-Host "   Found invalid Depends(get_async_session) in:" -ForegroundColor Red
    $matches | ForEach-Object { Write-Host "   - $($_.Filename):$($_.LineNumber)" -ForegroundColor Red }
    $ErrorCount++
} else {
    Write-Host " ✅ PASSED" -ForegroundColor Green
}

# Check 4: Canonical helpers exist
Write-Host "🔍 Verifying canonical session helpers..." -NoNewline
$hasGetDbSession = Select-String -Path "backend\database\models.py" -Pattern "async def get_db_session\(\):"
$hasOpenSession = Select-String -Path "backend\database\models.py" -Pattern "async def open_session\(\):"

if (-not $hasGetDbSession) {
    Write-Host " ❌ FAILED" -ForegroundColor Red
    Write-Host "   get_db_session not found in models.py!" -ForegroundColor Red
    $ErrorCount++
} elseif (-not $hasOpenSession) {
    Write-Host " ❌ FAILED" -ForegroundColor Red
    Write-Host "   open_session not found in models.py!" -ForegroundColor Red
    $ErrorCount++
} else {
    Write-Host " ✅ PASSED" -ForegroundColor Green
}

# Check 5: LangGraph reserved fields
Write-Host "🔍 Checking for LangGraph reserved field 'checkpoint_id'..." -NoNewline
$matches = Select-String -Path "backend\state\*.py" -Pattern "checkpoint_id:" | Where-Object { $_.Line -notmatch "checkpoint_ref" }
if ($matches) {
    Write-Host " ❌ FAILED" -ForegroundColor Red
    Write-Host "   Found 'checkpoint_id' in state schema (use 'checkpoint_ref' instead):" -ForegroundColor Red
    $matches | ForEach-Object { Write-Host "   - $($_.Filename):$($_.LineNumber)" -ForegroundColor Red }
    $ErrorCount++
} else {
    Write-Host " ✅ PASSED" -ForegroundColor Green
}

# Check 6: Protective comments
Write-Host "🔍 Verifying protective comments..." -NoNewline
$routesComment = Select-String -Path "backend\api\routes.py" -Pattern "DATABASE SESSION MANAGEMENT GUARDRAILS"
$chatRoutesComment = Select-String -Path "backend\api\chat_routes.py" -Pattern "DATABASE SESSION MANAGEMENT GUARDRAILS"

if (-not $routesComment) {
    Write-Host " ⚠️  WARNING" -ForegroundColor Yellow
    Write-Host "   Protective comment missing in routes.py" -ForegroundColor Yellow
} elseif (-not $chatRoutesComment) {
    Write-Host " ⚠️  WARNING" -ForegroundColor Yellow
    Write-Host "   Protective comment missing in chat_routes.py" -ForegroundColor Yellow
} else {
    Write-Host " ✅ PASSED" -ForegroundColor Green
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

if ($ErrorCount -gt 0) {
    Write-Host "❌ GUARDRAILS FAILED: $ErrorCount error(s) detected" -ForegroundColor Red
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "RULES:" -ForegroundColor Yellow
    Write-Host "1. FastAPI routes MUST use: session: AsyncSession = Depends(get_db_session)" -ForegroundColor Yellow
    Write-Host "2. Background tasks MUST use: async with open_session as session:" -ForegroundColor Yellow
    Write-Host "3. NEVER use get_session, get_db, or get_async_session" -ForegroundColor Yellow
    Write-Host "4. State schemas MUST use checkpoint_ref not checkpoint_id" -ForegroundColor Yellow
    Write-Host ""
    exit 1
} else {
    Write-Host "✅ All guardrails passed! Safe to commit." -ForegroundColor Green
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    exit 0
}
