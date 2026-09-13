$statePath = "C:\Users\ddare\Desktop\Al_Trading_Al\data\live_state\paper_live_BTCUSDT_1m.json"
$dailyPath = "C:\Users\ddare\Desktop\Al_Trading_Al\data\live_state\paper_live_daily.csv"

$header = "Date,Balance,NetProfit,Trades,Wins,Losses,WinRate,ProfitFactor,AvgWin,AvgLoss,Expectancy,MaxDrawdown,Position,MarketPrice"

if (-not (Test-Path $dailyPath)) {
    $header | Set-Content $dailyPath -Encoding UTF8
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
                $expectancy = (([double]$s.balance - 1000.0) / $tradeCount)
            }
            else {
                $winRate = 0
                $expectancy = 0
            }

            $grossProfit = 0.0
            $grossLoss = 0.0

            if ($winCount -gt 0) {
                $grossProfit = [double](($wins | Measure-Object -Property profit -Sum).Sum)
            }

            if ($lossCount -gt 0) {
                $grossLoss = [math]::Abs(
                    [double](($losses | Measure-Object -Property profit -Sum).Sum)
                )
            }

            if ($grossLoss -gt 0) {
                $profitFactor = $grossProfit / $grossLoss
            }
            else {
                $profitFactor = 0
            }

            if ($winCount -gt 0) {
                $avgWin = $grossProfit / $winCount
            }
            else {
                $avgWin = 0
            }

            if ($lossCount -gt 0) {
                $avgLoss = $grossLoss / $lossCount
            }
            else {
                $avgLoss = 0
            }

            if ($null -eq $s.position) {
                $position = "FLAT"
            }
            else {
                $position = [string]$s.position
            }

            $date = (Get-Date).ToString("yyyy-MM-dd")

            $line = [string]::Format(
                [System.Globalization.CultureInfo]::InvariantCulture,
                "{0},{1:F8},{2:F8},{3},{4},{5},{6:F4},{7:F6},{8:F8},{9:F8},{10:F8},{11:F8},{12},{13:F2}",
                $date,
                [double]$s.balance,
                ([double]$s.balance - 1000.0),
                $tradeCount,
                $winCount,
                $lossCount,
                $winRate,
                $profitFactor,
                $avgWin,
                $avgLoss,
                $expectancy,
                [double]$s.max_drawdown,
                $position,
                [double]$s.market_price
            )

            # Aktualizuj istniejący dzisiejszy snapshot albo dopisz nowy.
            $existing = @()
            if (Test-Path $dailyPath) {
                $existing = @(Get-Content $dailyPath)
            }

            if ($existing.Count -gt 1) {
                $newLines = New-Object System.Collections.Generic.List[string]
                $newLines.Add($existing[0])

                $replaced = $false

                foreach ($oldLine in $existing[1..($existing.Count - 1)]) {
                    if ($oldLine -match "^$date,") {
                        $newLines.Add($line)
                        $replaced = $true
                    }
                    else {
                        $newLines.Add($oldLine)
                    }
                }

                if (-not $replaced) {
                    $newLines.Add($line)
                }

                $newLines | Set-Content $dailyPath -Encoding UTF8
            }
            else {
                Add-Content $dailyPath $line -Encoding UTF8
            }
        }
    }
    catch {
        # Nie zatrzymuj procesu przy pojedynczym błędzie odczytu/zapisu.
    }

    Start-Sleep -Seconds 60
}
