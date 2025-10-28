# Credential Backup Script
# Run this BEFORE making any changes to the codebase

param(
    [string]$BackupDir = "C:\AI_src\BACKUPS\ContentCreationAgent"
)

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$ErrorActionPreference = "Continue"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "CREDENTIAL BACKUP UTILITY" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Create backup directory
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
Write-Host "📁 Backup directory: $BackupDir" -ForegroundColor Gray

# Files to backup
$files = @(
    @{Path=".env"; Name="backend_env"},
    @{Path="../PiAPI_MCP/piapi_fastmcp_server/.env.local"; Name="fastmcp_env"},
    @{Path="frontend/.env"; Name="frontend_env"},
    @{Path="secrets/client_secret.json"; Name="oauth_secrets"}
)

$backedUp = 0
$failed = 0

foreach ($file in $files) {
    $sourcePath = $file.Path
    $backupName = "$($file.Name).$timestamp"
    $destPath = Join-Path $BackupDir $backupName

    if (Test-Path $sourcePath) {
        try {
            Copy-Item $sourcePath $destPath -ErrorAction Stop
            Write-Host "✅ Backed up: $sourcePath → $backupName" -ForegroundColor Green
            $backedUp++
        } catch {
            Write-Host "❌ Failed to backup: $sourcePath - $($_.Exception.Message)" -ForegroundColor Red
            $failed++
        }
    } else {
        Write-Host "⚠️  Skipped (not found): $sourcePath" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  Backed up: $backedUp files" -ForegroundColor Green
Write-Host "  Failed: $failed files" -ForegroundColor $(if($failed -gt 0){"Red"}else{"Green"})
Write-Host "  Location: $BackupDir" -ForegroundColor Gray
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# List recent backups
Write-Host "Recent backups (last 5):" -ForegroundColor Cyan
Get-ChildItem $BackupDir | Sort-Object LastWriteTime -Descending | Select-Object -First 5 | ForEach-Object {
    Write-Host "  $($_.Name) - $($_.LastWriteTime)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "💡 Tip: Run this script BEFORE making any code changes" -ForegroundColor Yellow
