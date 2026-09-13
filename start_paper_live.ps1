$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\Users\ddare\Desktop\Al_Trading_Al"
$PythonExe   = "$ProjectRoot\.venv\Scripts\python.exe"
$StateFile   = "$ProjectRoot\data\live_state\paper_live_BTCUSDT_1m.json"
$LogFile     = "$ProjectRoot\data\live_state\paper_live.log"
$ErrorLog    = "$ProjectRoot\data\live_state\paper_live_error.log"

Write-Host ""
Write-Host ("=" * 90) -ForegroundColor Cyan
Write-Host "AL TRADING AGENT | START PAPER-LIVE" -ForegroundColor Cyan
Write-Host ("=" * 90) -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------------
# CHECK PROJECT
# ------------------------------------------------------------------

if (-not (Test-Path $ProjectRoot)) {
    Write-Host "PROJECT        : NOT FOUND" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $PythonExe)) {
    Write-Host "PYTHON         : NOT FOUND" -ForegroundColor Red
    Write-Host $PythonExe
    exit 1
}

if (-not (Test-Path "$ProjectRoot\scripts\run_paper_live.py")) {
    Write-Host "PAPER-LIVE     : SCRIPT NOT FOUND" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $StateFile)) {
    Write-Host "STATE FILE      : NOT FOUND" -ForegroundColor Red
    Write-Host $StateFile
    exit 1
}

# ------------------------------------------------------------------
# CHECK EXISTING PROCESS
# ------------------------------------------------------------------

$existing = @(Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like '*scripts.run_paper_live*'
})

if ($existing.Count -gt 0) {

    $root = @($existing | Where-Object {
        $_.ParentProcessId -notin @($existing.ProcessId)
    })

    if ($root.Count -gt 0) {
        Write-Host "STATUS         : ALREADY RUNNING" -ForegroundColor Green
        Write-Host ("LOGICAL RUNS   : {0}" -f $root.Count)
    }
    else {
        Write-Host "STATUS         : ALREADY RUNNING" -ForegroundColor Green
        Write-Host "LOGICAL RUNS   : 1"
    }

    Write-Host ("PROCESS CHAIN  : {0}" -f $existing.Count)
    Write-Host ""

    $existing |
        Select-Object ProcessId, ParentProcessId, Name |
        Format-Table -AutoSize

    exit 0
}

# ------------------------------------------------------------------
# READ CURRENT STATE
# ------------------------------------------------------------------

try {
    $state = Get-Content $StateFile -Raw | ConvertFrom-Json
}
catch {
    Write-Host "STATE FILE      : INVALID JSON" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}

Write-Host "STATE           : OK" -ForegroundColor Green
Write-Host ("Version         : {0}" -f $state.version)
Write-Host ("Balance         : {0:F8}" -f [double]$state.balance)
Write-Host ("Position        : {0}" -f $(if ($null -eq $state.position) { "FLAT" } else { $state.position }))
Write-Host ("Closed trades   : {0}" -f @($state.trade_manager_history).Count)
Write-Host ("Last processed  : {0}" -f $state.last_processed_timestamp)

Write-Host ""

# ------------------------------------------------------------------
# START
# ------------------------------------------------------------------

Write-Host "STARTING PAPER-LIVE..." -ForegroundColor Yellow

$process = Start-Process `
    -FilePath $PythonExe `
    -ArgumentList "-m","scripts.run_paper_live" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $LogFile `
    -RedirectStandardError $ErrorLog `
    -PassThru

Start-Sleep -Seconds 2

# ------------------------------------------------------------------
# VERIFY
# ------------------------------------------------------------------

$running = @(Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like '*scripts.run_paper_live*'
})

Write-Host ""

if ($running.Count -gt 0) {
    Write-Host "STATUS         : RUNNING" -ForegroundColor Green
    Write-Host ("START PID      : {0}" -f $process.Id)
    Write-Host ("PROCESS CHAIN  : {0}" -f $running.Count)
    Write-Host ("STATE FILE     : {0}" -f $StateFile)
    Write-Host ("LOG FILE       : {0}" -f $LogFile)
    Write-Host ("ERROR LOG      : {0}" -f $ErrorLog)
}
else {
    Write-Host "STATUS         : FAILED TO START" -ForegroundColor Red
    Write-Host "Sprawdz:"
    Write-Host $ErrorLog
    exit 1
}

Write-Host ""
Write-Host ("=" * 90) -ForegroundColor Cyan
Write-Host "PAPER-LIVE IS RUNNING IN BACKGROUND" -ForegroundColor Green
Write-Host ("=" * 90) -ForegroundColor Cyan
Write-Host ""
