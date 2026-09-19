$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "Brak .venv. Uruchom najpierw setup_project.ps1" -ForegroundColor Red
    exit 1
}

Set-Location $ProjectRoot
Write-Host "AL TRADING AGENT API -> http://127.0.0.1:8000" -ForegroundColor Cyan
& $PythonExe -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000
