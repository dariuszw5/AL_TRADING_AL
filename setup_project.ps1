$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".venv")) {
    py -m venv .venv
}

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
& ".\.venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host "" 
Write-Host "Python environment ready." -ForegroundColor Green
Write-Host "Next:" -ForegroundColor Cyan
Write-Host "  .\start_paper_live.ps1"
Write-Host "  .\start_api.ps1"
Write-Host "  .\start_dashboard.ps1"
