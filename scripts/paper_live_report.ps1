$statePath = ".\data\live_state\paper_live_BTCUSDT_1m.json"

Clear-Host

Write-Host ""
Write-Host ("=" * 100) -ForegroundColor Cyan
Write-Host "AL TRADING AGENT | PAPER-LIVE REPORT" -ForegroundColor Cyan
Write-Host ("=" * 100) -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $statePath)) {
    Write-Host "STATE FILE NOT FOUND" -ForegroundColor Red
    exit 1
}

try {
    $s = Get-Content $statePath -Raw | ConvertFrom-Json
}
catch {
    Write-Host "STATE FILE INVALID" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}

# ------------------------------------------------------------------
# BASIC STATE
# ------------------------------------------------------------------

$initialBalance = 1000.0
$balance = [double]$s.balance
$netProfit = $balance - $initialBalance
$peak = [double]$s.peak_balance
$maxDrawdown = [double]$s.max_drawdown

$trades = @($s.trade_manager_history)

$wins = @($trades | Where-Object { [double]$_.profit -gt 0 })
$losses = @($trades | Where-Object { [double]$_.profit -lt 0 })

$tradeCount = $trades.Count
$winCount = $wins.Count
$lossCount = $losses.Count

if ($tradeCount -gt 0) {
    $winRate = ($winCount / $tradeCount) * 100
}
else {
    $winRate = 0
}

$totalWin = 0.0
$totalLossAbs = 0.0

if ($winCount -gt 0) {
    $totalWin = ($wins | Measure-Object -Property profit -Sum).Sum
}

if ($lossCount -gt 0) {
    $totalLossAbs = [math]::Abs(($losses | Measure-Object -Property profit -Sum).Sum)
}

if ($totalLossAbs -gt 0) {
    $profitFactor = $totalWin / $totalLossAbs
}
else {
    $profitFactor = 0
}

if ($winCount -gt 0) {
    $avgWin = $totalWin / $winCount
}
else {
    $avgWin = 0
}

if ($lossCount -gt 0) {
    $avgLoss = $totalLossAbs / $lossCount
}
else {
    $avgLoss = 0
}

if ($tradeCount -gt 0) {
    $expectancy = $netProfit / $tradeCount
}
else {
    $expectancy = 0
}

# ------------------------------------------------------------------
# PROCESS STATUS
# ------------------------------------------------------------------

$processes = @(Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like '*scripts.run_paper_live*'
})

if ($processes.Count -gt 0) {
    $processStatus = "RUNNING"
}
else {
    $processStatus = "STOPPED"
}

# ------------------------------------------------------------------
# CANDLE AGE
# ------------------------------------------------------------------

$lastUtc = $null
$ageSec = $null

if ($s.last_processed_timestamp) {
    $lastUtc = [DateTimeOffset]::FromUnixTimeMilliseconds(
        [int64]$s.last_processed_timestamp
    )

    $ageSec = ([DateTimeOffset]::UtcNow - $lastUtc).TotalSeconds
}

# ------------------------------------------------------------------
# HEADER
# ------------------------------------------------------------------

Write-Host "SYSTEM" -ForegroundColor Yellow
Write-Host ("-" * 100)
Write-Host ("Paper-live      : {0}" -f $processStatus) -ForegroundColor $(if ($processStatus -eq "RUNNING") { "Green" } else { "Red" })
Write-Host ("State version   : {0}" -f $s.version)
Write-Host ("Last candle     : {0}" -f $s.last_processed_timestamp)

if ($lastUtc) {
    Write-Host ("Candle UTC      : {0}" -f $lastUtc.ToString("yyyy-MM-dd HH:mm:ss"))
    Write-Host ("Candle age      : {0:N1} sec" -f $ageSec)

    if ($ageSec -le 120) {
        Write-Host "Candle health   : HEALTHY" -ForegroundColor Green
    }
    else {
        Write-Host "Candle health   : STALE" -ForegroundColor Red
    }
}

Write-Host ""

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------

Write-Host "FROZEN STRATEGY" -ForegroundColor Yellow
Write-Host ("-" * 100)
Write-Host "BUY RSI         : 33.8"
Write-Host "SELL RSI        : 68.5"
Write-Host "MAX TIME        : 241"
Write-Host "MIN DIFFERENCE  : 1.0"
Write-Host "RSI METHOD      : classic"
Write-Host "FEE             : 0.0004"

Write-Host ""

# ------------------------------------------------------------------
# ACCOUNT
# ------------------------------------------------------------------

Write-Host "ACCOUNT" -ForegroundColor Yellow
Write-Host ("-" * 100)
Write-Host ("Position        : {0}" -f $(if ($null -eq $s.position) { "FLAT" } else { $s.position }))
Write-Host ("Position candles: {0}" -f $s.position_candles)
Write-Host ("Balance         : {0:F8}" -f $balance)
Write-Host ("Peak balance    : {0:F8}" -f $peak)
Write-Host ("Net P/L         : {0:F8}" -f $netProfit)
Write-Host ("Max drawdown    : {0:F8}" -f $maxDrawdown)
Write-Host ("Market price    : {0:F2}" -f [double]$s.market_price)
Write-Host ("Daily loss      : {0:F8}" -f [double]$s.risk_guard.daily_loss)

Write-Host ""

# ------------------------------------------------------------------
# PERFORMANCE
# ------------------------------------------------------------------

Write-Host "PERFORMANCE" -ForegroundColor Yellow
Write-Host ("-" * 100)
Write-Host ("Trades          : {0}" -f $tradeCount)
Write-Host ("Wins            : {0}" -f $winCount)
Write-Host ("Losses          : {0}" -f $lossCount)
Write-Host ("Win rate        : {0:F2}%" -f $winRate)
if ($totalLossAbs -gt 0) { Write-Host ("Profit factor   : {0:F4}" -f $profitFactor) } else { Write-Host "Profit factor   : N/A (no losses yet)" }
Write-Host ("Avg win         : {0:F8}" -f $avgWin)
Write-Host ("Avg loss        : {0:F8}" -f $avgLoss)
Write-Host ("Expectancy      : {0:F8}" -f $expectancy)
Write-Host ("Gross profit    : {0:F8}" -f $totalWin)
Write-Host ("Gross loss      : {0:F8}" -f $totalLossAbs)

Write-Host ""

# ------------------------------------------------------------------
# TRADE TABLE
# ------------------------------------------------------------------

if ($tradeCount -gt 0) {

    Write-Host "TRADE HISTORY" -ForegroundColor Yellow
    Write-Host ("-" * 100)

    $i = 0

    foreach ($t in $trades) {
        $i++

        $profitValue = [double]$t.profit

        if ($profitValue -gt 0) {
            $resultText = "WIN"
        }
        elseif ($profitValue -lt 0) {
            $resultText = "LOSS"
        }
        else {
            $resultText = "BE"
        }

        Write-Host ("#{0,-3} {1,-5} {2,-5} Entry={3,10:F2} Exit={4,10:F2} Net={5,10:F6} Fee={6,10:F6} Reason={7}" -f `
            $i,
            $t.side,
            $resultText,
            [double]$t.entry_price,
            [double]$t.exit_price,
            $profitValue,
            [double]$t.fee,
            $t.exit_reason)
    }
}
else {
    Write-Host "TRADE HISTORY" -ForegroundColor Yellow
    Write-Host ("-" * 100)
    Write-Host "No closed trades."
}

Write-Host ""
Write-Host ("=" * 100) -ForegroundColor Cyan
Write-Host ("Report generated: {0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
Write-Host ("=" * 100) -ForegroundColor Cyan
Write-Host ""

