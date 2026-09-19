$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$PythonExe   = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LiveDir     = Join-Path $ProjectRoot "data\live_state"
$LogFile     = Join-Path $LiveDir "paper_live.log"
$ErrorLog    = Join-Path $LiveDir "paper_live_error.log"

Write-Host ""
Write-Host ("=" * 90) -ForegroundColor Cyan
Write-Host "AL TRADING AGENT | START MULTI-ASSET PAPER-LIVE" -ForegroundColor Cyan
Write-Host ("=" * 90) -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $PythonExe)) {
    Write-Host "PYTHON VENV : NOT FOUND" -ForegroundColor Red
    Write-Host "Run first:" -ForegroundColor Yellow
    Write-Host "  py -m venv .venv"
    Write-Host "  .\.venv\Scripts\Activate.ps1"
    Write-Host "  python -m pip install -r requirements.txt"
    exit 1
}

if (-not (Test-Path (Join-Path $ProjectRoot "scripts\run_paper_live.py"))) {
    Write-Host "PAPER-LIVE SCRIPT: NOT FOUND" -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path $LiveDir | Out-Null

$existing = @(Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like '*scripts.run_paper_live*'
})

if ($existing.Count -gt 0) {
    Write-Host "STATUS : ALREADY RUNNING" -ForegroundColor Green
    $existing |
        Select-Object ProcessId, ParentProcessId, Name |
        Format-Table -AutoSize
    exit 0
}

Write-Host "MODE           : PAPER ONLY" -ForegroundColor Green
Write-Host "MARKET DATA    : REAL PROVIDER DATA"
Write-Host "REAL ORDERS    : NEVER"
Write-Host "PLN            : REPORTING CONVERSION IN API/DASHBOARD"
Write-Host "AI EXPERIMENT  : OFF BY DEFAULT"
Write-Host ""
Write-Host "STARTING..." -ForegroundColor Yellow

$process = Start-Process `
    -FilePath $PythonExe `
    -ArgumentList "-m","scripts.run_paper_live" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $LogFile `
    -RedirectStandardError $ErrorLog `
    -PassThru

Start-Sleep -Seconds 2

$running = @(Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like '*scripts.run_paper_live*'
})

Write-Host ""
if ($running.Count -gt 0) {
    Write-Host "STATUS         : RUNNING" -ForegroundColor Green
    Write-Host ("START PID      : {0}" -f $process.Id)
    Write-Host ("LOG FILE       : {0}" -f $LogFile)
    Write-Host ("ERROR LOG      : {0}" -f $ErrorLog)
}
else {
    Write-Host "STATUS         : FAILED TO START" -ForegroundColor Red
    Write-Host "Check: $ErrorLog"
    exit 1
}

Write-Host ""
Write-Host ("=" * 90) -ForegroundColor Cyan
Write-Host "MULTI-ASSET PAPER-LIVE IS RUNNING" -ForegroundColor Green
Write-Host ("=" * 90) -ForegroundColor Cyan
