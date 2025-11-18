# Produktoprettelse-v2 Docker Launcher
# This script automatically detects the OneDrive image folder and starts the Docker container

$ErrorActionPreference = "Stop"

Write-Host "Produktoprettelse-v2 - Docker Launcher" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# 1. Detect OneDrive Root
$oneDrivePath = $env:OneDriveCommercial
if (-not $oneDrivePath) {
    $oneDrivePath = $env:OneDrive
}

if (-not $oneDrivePath) {
    Write-Host "WARNING: Could not detect OneDrive environment variable." -ForegroundColor Yellow
    # Fallback: Try to guess based on current user
    $userProfile = $env:USERPROFILE
    $possiblePaths = @(
        "$userProfile\OneDrive - Bunzl Continental Europe",
        "$userProfile\OneDrive"
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $oneDrivePath = $path
            break
        }
    }
}

if (-not $oneDrivePath) {
    Write-Host "ERROR: Could not find OneDrive folder." -ForegroundColor Red
    Write-Host "Please ensure OneDrive is running and synced." -ForegroundColor Red
    exit 1
}

Write-Host "Found OneDrive at: $oneDrivePath" -ForegroundColor Gray

# 2. Construct Image Path
# The folder is: Documents - Bonvig/Produktbilleder_1500x1500
$imagePath = Join-Path $oneDrivePath "Documents - Bonvig\Produktbilleder_1500x1500"

if (-not (Test-Path $imagePath)) {
    Write-Host "ERROR: Could not find image folder at:" -ForegroundColor Red
    Write-Host "  $imagePath" -ForegroundColor Red
    Write-Host "Please ensure the 'Documents - Bonvig' folder is synced to your computer." -ForegroundColor Yellow
    exit 1
}

Write-Host "Found Image Folder at: $imagePath" -ForegroundColor Green

# 3. Set Environment Variable for Docker Compose
$env:EXTERNAL_IMAGES_DIR = $imagePath

# 4. Run Docker Compose
Write-Host ""
Write-Host "Starting Docker Container..." -ForegroundColor Cyan
Write-Host "Access the app at: http://localhost:8501" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop." -ForegroundColor Gray
Write-Host ""

# Use 'docker compose' (V2) instead of 'docker-compose' (V1)
docker compose up --build
