#!/usr/bin/env pwsh
# Cleanup Script - Remove Obsolete Files

Write-Host "=== Produktoprettelse-v2 Cleanup ===" -ForegroundColor Cyan
Write-Host ""

$filesToDelete = @(
    "csv_dashboard.py",
    "csv_manager.py",
    "CODE_FLOW.md",
    "DETAILED_WALKTHROUGH.md",
    "VISUAL_SUMMARY.md",
    "QUICK_REFERENCE.md",
    "INTEGRATION_EXAMPLE.py",
    "TASK_1_COMPLETE.md",
    "TASK_1_SUMMARY.md",
    "REFACTORING_PLAN.md"
)

Write-Host "Files found to delete:" -ForegroundColor Yellow
$foundCount = 0
foreach ($file in $filesToDelete) {
    if (Test-Path $file) {
        Write-Host "  [x] $file" -ForegroundColor Red
        $foundCount++
    }
}

if ($foundCount -eq 0) {
    Write-Host "All files already deleted!" -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "Checking for old logs..." -ForegroundColor Yellow
$logsFound = Get-ChildItem -Path "logs" -Filter "*.log" -ErrorAction SilentlyContinue
if ($logsFound) {
    Write-Host "  Found $($logsFound.Count) old log files" -ForegroundColor Yellow
}

Write-Host ""
$confirm = Read-Host "Delete these files? Type 'yes' to confirm"

if ($confirm -eq 'yes') {
    Write-Host ""
    Write-Host "Deleting files..." -ForegroundColor Green
    
    foreach ($file in $filesToDelete) {
        if (Test-Path $file) {
            Remove-Item $file -Force -ErrorAction SilentlyContinue
            Write-Host "  Deleted: $file" -ForegroundColor Green
        }
    }
    
    Write-Host ""
    Write-Host "Cleanup complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. pip install -r requirements.txt"
    Write-Host "  2. git add -A"
    Write-Host "  3. git commit -m 'Cleanup: Remove obsolete files'"
} else {
    Write-Host ""
    Write-Host "Cleanup cancelled." -ForegroundColor Yellow
}
