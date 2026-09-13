$statePath  = ".\data\live_state\paper_live_BTCUSDT_1m.json"
$csvPath    = ".\data\live_state\paper_live_history.csv"
$cursorPath = ".\data\live_state\paper_live_history.cursor"

$header = "TradeNumber,Side,EntryPrice,ExitPrice,Quantity,StopLoss,TakeProfit,EntryTimestamp,ExitTimestamp,ExitReason,GrossProfit,Fee,NetProfit"

# ------------------------------------------------------------------
# REBUILD CORRECT CSV FROM CURRENT STATE
# ------------------------------------------------------------------

if (Test-Path $statePath) {

    try {
        $s = Get-Content $statePath -Raw | ConvertFrom-Json
        $trades = @($s.trade_manager_history)

        $lines = New-Object System.Collections.Generic.List[string]
        $lines.Add($header)

        $i = 0

        foreach ($t in $trades) {
            $i++

            $line = [string]::Format(
                [System.Globalization.CultureInfo]::InvariantCulture,
                "{0},{1},{2:F8},{3:F8},{4:F8},{5:F8},{6:F8},{7},{8},{9},{10:F8},{11:F8},{12:F8}",
                $i,
                $t.side,
                [double]$t.entry_price,
                [double]$t.exit_price,
                [double]$t.quantity,
                [double]$t.stop_loss,
                [double]$t.take_profit,
                [int64]$t.entry_timestamp,
                [int64]$t.exit_timestamp,
                $t.exit_reason,
                [double]$t.gross_profit,
                [double]$t.fee,
                [double]$t.profit
            )

            $lines.Add($line)
        }

        $lines | Set-Content $csvPath -Encoding UTF8
        $trades.Count | Set-Content $cursorPath -Encoding ASCII
    }
    catch {
        # Nie przerywaj loggera przy błędzie pojedynczego odczytu.
    }
}

# ------------------------------------------------------------------
# LIVE LOGGER
# ------------------------------------------------------------------

while ($true) {

    try {
        if (Test-Path $statePath) {

            $s = Get-Content $statePath -Raw | ConvertFrom-Json
            $trades = @($s.trade_manager_history)

            [int]$loggedCount = 0

            if (Test-Path $cursorPath) {
                try {
                    $loggedCount = [int](Get-Content $cursorPath -Raw).Trim()
                }
                catch {
                    $loggedCount = 0
                }
            }

            if ($trades.Count -gt $loggedCount) {

                for ($i = $loggedCount; $i -lt $trades.Count; $i++) {

                    $t = $trades[$i]
                    $tradeNumber = $i + 1

                    $line = [string]::Format(
                        [System.Globalization.CultureInfo]::InvariantCulture,
                        "{0},{1},{2:F8},{3:F8},{4:F8},{5:F8},{6:F8},{7},{8},{9},{10:F8},{11:F8},{12:F8}",
                        $tradeNumber,
                        $t.side,
                        [double]$t.entry_price,
                        [double]$t.exit_price,
                        [double]$t.quantity,
                        [double]$t.stop_loss,
                        [double]$t.take_profit,
                        [int64]$t.entry_timestamp,
                        [int64]$t.exit_timestamp,
                        $t.exit_reason,
                        [double]$t.gross_profit,
                        [double]$t.fee,
                        [double]$t.profit
                    )

                    Add-Content $csvPath $line -Encoding UTF8
                }

                $trades.Count | Set-Content $cursorPath -Encoding ASCII
            }
        }
    }
    catch {
        # Logger pozostaje aktywny.
    }

    Start-Sleep -Seconds 5
}
