$statePath = ".\data\live_state\paper_live_BTCUSDT_1m.json"
$snapshotPath = ".\data\live_state\paper_live_snapshots.csv"

$header = "Timestamp,LastProcessedTimestamp,Balance,NetProfit,PeakBalance,MaxDrawdown,Trades,Wins,Losses,WinRate,ProfitFactor,Position,PositionCandles,MarketPrice,DailyLoss"

if (-not (Test-Path $snapshotPath)) {
    $header | Set-Content $snapshotPath -Encoding UTF8
}

while ($true) {

    try {
        if (Test-Path $statePath) {

            $s = Get-Content $statePath -Raw | ConvertFrom-Json

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

            $grossProfit = 0.0
            $grossLoss = 0.0

            if ($winCount -gt 0) {
                $grossProfit = ($wins | Measure-Object -Property profit -Sum).Sum
            }

            if ($lossCount -gt 0) {
                $grossLoss = [math]::Abs(
                    ($losses | Measure-Object -Property profit -Sum).Sum
                )
            }

            if ($grossLoss -gt 0) {
                $profitFactor = $grossProfit / $grossLoss
            }
            else {
                $profitFactor = 0
            }

            $balance = [double]$s.balance
            $netProfit = $balance - 1000.0

            if ($null -eq $s.position) {
                $position = "FLAT"
            }
            else {
                $position = [string]$s.position
            }

            $line = [string]::Format(
                [System.Globalization.CultureInfo]::InvariantCulture,
                "{0},{1},{2:F8},{3:F8},{4:F8},{5:F8},{6},{7},{8},{9:F4},{10:F6},{11},{12},{13:F2},{14:F8}",
                (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"),
                [int64]$s.last_processed_timestamp,
                $balance,
                $netProfit,
                [double]$s.peak_balance,
                [double]$s.max_drawdown,
                $tradeCount,
                $winCount,
                $lossCount,
                $winRate,
                $profitFactor,
                $position,
                [int]$s.position_candles,
                [double]$s.market_price,
                [double]$s.risk_guard.daily_loss
            )

            Add-Content $snapshotPath $line -Encoding UTF8
        }
    }
    catch {
        # Snapshotter pozostaje aktywny.
    }

    Start-Sleep -Seconds 60
}
