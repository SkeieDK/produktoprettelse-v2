# Produktoprettelse-v2 Streamlit App Launcher
# This script activates the virtual environment and launches the Streamlit app

$ErrorActionPreference = "Stop"

# Setup paths
$PROJECT_ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$VENV_PATH = "C:\Users\anton\virtual_environments\produktoprettelse-v2\.venv"
$VENV_ACTIVATE = Join-Path $VENV_PATH "Scripts\Activate.ps1"

Write-Host "Produktoprettelse-v2 - Streamlit Application" -ForegroundColor Cyan
Write-Host ""

# --- AUTO-DETECT ONEDRIVE PATH (Added for Image Support) ---
$oneDrivePath = $env:OneDriveCommercial
if (-not $oneDrivePath) { $oneDrivePath = $env:OneDrive }

if ($oneDrivePath) {
    $imagePath = Join-Path $oneDrivePath "Documents - Bonvig\Produktbilleder_1500x1500"
    if (Test-Path $imagePath) {
        $env:EXTERNAL_IMAGES_DIR = $imagePath
        Write-Host "OK - Auto-detected images at: $imagePath" -ForegroundColor Green
    }
}
# -----------------------------------------------------------

# Check if venv exists
if (-not (Test-Path $VENV_ACTIVATE)) {
    Write-Host "ERROR: Virtual environment not found at:" -ForegroundColor Red
    Write-Host "   $VENV_PATH" -ForegroundColor Red
    exit 1
}

Write-Host "OK - Virtual environment found" -ForegroundColor Green
Write-Host "  Path: $VENV_PATH" -ForegroundColor Gray
Write-Host ""

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& $VENV_ACTIVATE

# Verify we're in the right environment
$pythonPath = (Get-Command python).Source
Write-Host "OK - Using Python from: $pythonPath" -ForegroundColor Green
Write-Host ""

# Change to project root
Set-Location $PROJECT_ROOT
Write-Host "OK - Working directory: $PROJECT_ROOT" -ForegroundColor Green
Write-Host ""

# Run Streamlit using the full path to Python
Write-Host "Launching Streamlit app..." -ForegroundColor Yellow
Write-Host ""

$pythonExe = Join-Path $VENV_PATH "Scripts\python.exe"
& $pythonExe -m streamlit run app/app.py
