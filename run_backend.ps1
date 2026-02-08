#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Start the Emergent Backend Server with MongoDB
.DESCRIPTION
  Simplified script to start the backend with proper configuration
.EXAMPLE
  .\run_backend.ps1
  .\run_backend.ps1 -Port 8001
#>

param(
    [int]$Port = 8000,
    [switch]$NoReload = $false,
    [string]$ServerHost = "0.0.0.0"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  Emergent Backend Server Launcher" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path ".\.venv")) {
    Write-Host "[ERROR] Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

Write-Host "[INFO] Activating virtual environment..." -ForegroundColor Yellow
& ".\.venv\Scripts\Activate.ps1"
Write-Host "[OK] Virtual environment activated" -ForegroundColor Green
Write-Host ""

if (-not (Test-Path ".\.env")) {
    Write-Host "[WARNING] .env file not found! Creating default..." -ForegroundColor Yellow
    @"
MONGO_URL=mongodb://localhost:27017
DB_NAME=emergent_test
"@ | Out-File -Encoding UTF8 .\.env
    Write-Host "[OK] Created .env file" -ForegroundColor Green
}

Write-Host "[INFO] Checking MongoDB configuration..." -ForegroundColor Yellow
$mongoUrl = (Select-String -Path .\.env "MONGO_URL" | ForEach-Object { $_.Line -split "=" })[1].Trim()

if ($mongoUrl -like "*localhost*") {
    Write-Host "     Using local MongoDB: $mongoUrl" -ForegroundColor Cyan
    Write-Host "     Make sure mongod is running locally!" -ForegroundColor Yellow
} else {
    Write-Host "     Using MongoDB Atlas/Cloud: $mongoUrl" -ForegroundColor Cyan
}
Write-Host ""

$reloadArg = if ($NoReload) { "" } else { "--reload" }
$uvicornCmd = "python -m uvicorn server:app --host $ServerHost --port $Port $reloadArg"

Write-Host "[INFO] Starting FastAPI server..." -ForegroundColor Cyan
Write-Host "     Host: $ServerHost" -ForegroundColor Gray
Write-Host "     Port: $Port" -ForegroundColor Gray
Write-Host "     Reload: $(if($NoReload) { 'Disabled' } else { 'Enabled' })" -ForegroundColor Gray
Write-Host ""
Write-Host "[SUCCESS] Server will be available at: http://localhost:$Port" -ForegroundColor Green
Write-Host "[SUCCESS] API Docs: http://localhost:$Port/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host "=======================================" -ForegroundColor Gray
Write-Host ""

Invoke-Expression $uvicornCmd
