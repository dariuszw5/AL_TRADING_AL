$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "Brak .venv. Uruchom najpierw setup_project.ps1" -ForegroundColor Red
    exit 1
}

Set-Location $ProjectRoot
Write-Host "AUTONOMICZNY RESEARCH PAPER | REAL DATA | REAL ORDERS: 0" -ForegroundColor Cyan
& $PythonExe -m scripts.run_autonomous_research
