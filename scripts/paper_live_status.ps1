$statePath = ".\data\live_state\paper_live_BTCUSDT_1m.json"

Clear-Host

Write-Host ""
Write-Host ("=" * 90) -ForegroundColor Cyan
Write-Host "AL TRADING AGENT | PAPER-LIVE STATUS" -ForegroundColor Cyan
Write-Host ("=" * 90) -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------------
# PROCESS
# ------------------------------------------------------------------

$processes = @(Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like '*scripts.run_paper_live*'
})

$logicalInstances = 0

if ($processes.Count -gt 0) {
    $rootProcesses = @($processes | Where-Object {
        $_.ParentProcessId -notin @($processes.ProcessId)
    })

    if ($rootProcesses.Count -gt 0) {
        $logicalInstances = $rootProcesses.Count
    }
    else {
        $logicalInstances = 1
    }
}

Write-Host "PROCESS" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------"

if ($logicalInstances -gt 0) {
    Write-Host "Status           : RUNNING" -ForegroundColor Green
    Write-Host ("Logical instances: {0}" -f $logicalInstances)
    Write-Host ("Process chain    : {0}" -f $processes.Count)

    $processes |
        Select-Object ProcessId, ParentProcessId, Name |
        Format-Table -AutoSize
}
else {
    Write-Host "Status           : STOPPED" -ForegroundColor Red
    Write-Host "Logical instances: 0"
    Write-Host "Process chain    : 0"
}

Write-Host ""

# ------------------------------------------------------------------
# STATE FILE
# ------------------------------------------------------------------

if (-not (Test-Path $statePath)) {
    Write-Host "STATE FILE       : NOT FOUND" -ForegroundColor Red
    exit 1
}

try {
    $s = Get-Content $statePath -Raw | ConvertFrom-Json
}
catch {
    Write-Host "STATE FILE       : INVALID JSON" -ForegroundColor Red
    Write-Host ("Error            : {0}" -f $_.Exception.Message)
    exit 1
}

Write-Host "STATE" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------"
Write-Host ("Version          : {0}" -f $s.version)
Write-Host ("Last processed   : {0}" -f $s.last_processed_timestamp)

if ($s.last_processed_timestamp) {
    $lastMs = [double]$s.last_processed_timestamp
    $lastUtc = [DateTimeOffset]::FromUnixTimeMilliseconds([int64]$lastMs)
    $nowUtc = [DateTimeOffset]::UtcNow
    $ageSec = ($nowUtc - $lastUtc).TotalSeconds

    Write-Host ("Last candle UTC  : {0}" -f $lastUtc.ToString("yyyy-MM-dd HH:mm:ss"))
    Write-Host ("Candle age       : {0:N1} sec" -f $ageSec)

    if ($ageSec -le 120) {
        Write-Host "Candle status    : HEALTHY" -ForegroundColor Green
    }
    else {
        Write-Host "Candle status    : STALE" -ForegroundColor Red
    }
}

Write-Host ""

# ------------------------------------------------------------------
# ACCOUNT
# ------------------------------------------------------------------

Write-Host "ACCOUNT" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------"

if ($null -eq $s.position) {
    $positionText = "FLAT"
}
else {
    $positionText = [string]$s.position
}

Write-Host ("Position         : {0}" -f $positionText)
Write-Host ("Position candles : {0}" -f $s.position_candles)
Write-Host ("Balance          : {0:F8}" -f [double]$s.balance)
Write-Host ("Peak balance     : {0:F8}" -f [double]$s.peak_balance)
Write-Host ("Max drawdown     : {0:F8}" -f [double]$s.max_drawdown)
Write-Host ("Market price     : {0:F2}" -f [double]$s.market_price)
Write-Host ("Daily loss       : {0:F8}" -f [double]$s.risk_guard.daily_loss)
Write-Host ("Closed trades    : {0}" -f $s.trade_manager_history.Count)

$profit = [double]$s.balance - 1000.0
Write-Host ("Net P/L          : {0:F8}" -f $profit)

Write-Host ""

# ------------------------------------------------------------------
# LAST TRADE
# ------------------------------------------------------------------

if ($s.trade_manager_history.Count -gt 0) {
    $t = $s.trade_manager_history[-1]

    Write-Host "LAST TRADE" -ForegroundColor Yellow
    Write-Host "----------------------------------------------------------"
    Write-Host ("Side             : {0}" -f $t.side)
    Write-Host ("Entry            : {0:F2}" -f [double]$t.entry_price)
    Write-Host ("Exit             : {0:F2}" -f [double]$t.exit_price)
    Write-Host ("Reason           : {0}" -f $t.exit_reason)
    Write-Host ("Gross profit     : {0:F8}" -f [double]$t.gross_profit)
    Write-Host ("Fee              : {0:F8}" -f [double]$t.fee)
    Write-Host ("Net profit       : {0:F8}" -f [double]$t.profit)
    Write-Host ("Entry timestamp  : {0}" -f $t.entry_timestamp)
    Write-Host ("Exit timestamp   : {0}" -f $t.exit_timestamp)
}
else {
    Write-Host "LAST TRADE       : NONE"
}

Write-Host ""
Write-Host ("=" * 90) -ForegroundColor Cyan
Write-Host ("Checked          : {0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
Write-Host ("=" * 90) -ForegroundColor Cyan
Write-Host ""
