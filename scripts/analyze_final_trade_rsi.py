from src.backtest.backtest_runner import BacktestRunner
from src.analysis.indicators import rsi


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

BUY_RSI = 34.50
SELL_RSI = 68.50
MIN_DIFF = 1.0
FEE = 0.0004

RISK_PERCENT = 5.0
RR = 2.0
MAX_POSITION_CANDLES = 240
RSI_PERIOD = 14


def get_rsi_at_index(rsi_values, candle_index):
    rsi_index = candle_index - RSI_PERIOD

    if rsi_index < 0 or rsi_index >= len(rsi_values):
        return None

    return float(rsi_values[rsi_index])


def find_candle_index(candles, timestamp):
    for i, candle in enumerate(candles):
        if candle.timestamp == timestamp:
            return i

    return None


def classify_rsi(side, value):
    if value is None:
        return "UNKNOWN"

    if side == "BUY":
        if value < 20:
            return "<20"
        if value < 25:
            return "20-25"
        if value < 30:
            return "25-30"
        if value < 32.5:
            return "30-32.5"
        return "32.5-34.5"

    if side == "SELL":
        if value < 70:
            return "68.5-70"
        if value < 75:
            return "70-75"
        if value < 80:
            return "75-80"
        if value < 90:
            return "80-90"
        return "90+"

    return "UNKNOWN"


def main():
    for name, path in DATASETS.items():

        print("\n" + "=" * 120)
        print(f"=== {name} REAL TRADE + ENTRY RSI ANALYSIS ===")
        print("=" * 120)

        runner = BacktestRunner(
            symbol="BTCUSDT",
            interval="1m",
            limit=5000,
            initial_balance=1000.0,
            buy_rsi=BUY_RSI,
            sell_rsi=SELL_RSI,
            min_difference=MIN_DIFF,
            trading_fee=FEE,
            rsi_method="classic",
            risk_percent=RISK_PERCENT,
            risk_reward_ratio=RR,
            data_source="file",
            data_file=path,
        )

        candles = runner.load_data()
        runner.run()

        closes = [float(c.close) for c in candles]
        rsi_values = rsi(closes, RSI_PERIOD)

        trades = runner.get_trades()

        print(
            f"\nCONFIG: BUY={BUY_RSI:.2f} | "
            f"SELL={SELL_RSI:.2f} | "
            f"MIN_DIFF={MIN_DIFF:.2f} | "
            f"FEE={FEE:.4f} | "
            f"RSI=classic | "
            f"MAX_TIME={MAX_POSITION_CANDLES}"
        )

        print(f"REAL TRADES: {len(trades)}")

        print("\nREAL TRADES")
        print("-" * 120)
        print(
            "TRADE | SIDE | ENTRY RSI | RSI GROUP | "
            "PROFIT | EXIT REASON | ENTRY INDEX"
        )
        print("-" * 120)

        enriched = []

        for number, trade in enumerate(trades, 1):

            entry_timestamp = trade["entry_timestamp"]
            entry_index = find_candle_index(
                candles,
                entry_timestamp
            )

            entry_rsi = None

            if entry_index is not None:
                entry_rsi = get_rsi_at_index(
                    rsi_values,
                    entry_index
                )

            group = classify_rsi(
                trade["side"],
                entry_rsi
            )

            profit = float(trade["profit"])

            enriched.append({
                "number": number,
                "side": trade["side"],
                "rsi": entry_rsi,
                "group": group,
                "profit": profit,
                "exit_reason": trade["exit_reason"],
                "entry_index": entry_index,
            })

            rsi_text = (
                f"{entry_rsi:9.2f}"
                if entry_rsi is not None
                else "      N/A"
            )

            print(
                f"{number:5d} | "
                f"{trade['side']:4s} | "
                f"{rsi_text} | "
                f"{group:9s} | "
                f"{profit:7.4f} | "
                f"{trade['exit_reason']:11s} | "
                f"{str(entry_index):>11s}"
            )

        print("\n" + "=" * 120)
        print("RSI GROUP PERFORMANCE")
        print("=" * 120)

        groups = [
            "<20",
            "20-25",
            "25-30",
            "30-32.5",
            "32.5-34.5",
            "68.5-70",
            "70-75",
            "75-80",
            "80-90",
            "90+",
        ]

        print(
            "GROUP       | TRADES | WINS | LOSSES | "
            "WR       | PROFIT    | AVG"
        )
        print("-" * 120)

        for group in groups:
            group_trades = [
                t for t in enriched
                if t["group"] == group
            ]

            if not group_trades:
                continue

            wins = [
                t for t in group_trades
                if t["profit"] > 0
            ]

            losses = [
                t for t in group_trades
                if t["profit"] <= 0
            ]

            total_profit = sum(
                t["profit"] for t in group_trades
            )

            avg_profit = (
                total_profit / len(group_trades)
            )

            win_rate = (
                len(wins) / len(group_trades) * 100
            )

            print(
                f"{group:12s} | "
                f"{len(group_trades):6d} | "
                f"{len(wins):4d} | "
                f"{len(losses):6d} | "
                f"{win_rate:7.2f}% | "
                f"{total_profit:9.4f} | "
                f"{avg_profit:7.4f}"
            )

        print("\n" + "=" * 120)
        print("BUY vs SELL")
        print("=" * 120)

        for side in ("BUY", "SELL"):
            side_trades = [
                t for t in enriched
                if t["side"] == side
            ]

            if not side_trades:
                continue

            wins = [
                t for t in side_trades
                if t["profit"] > 0
            ]

            total_profit = sum(
                t["profit"] for t in side_trades
            )

            print(
                f"{side:4s} | "
                f"TRADES={len(side_trades):2d} | "
                f"WINS={len(wins):2d} | "
                f"WR={len(wins)/len(side_trades)*100:6.2f}% | "
                f"PROFIT={total_profit:9.4f} | "
                f"AVG={total_profit/len(side_trades):8.4f}"
            )


if __name__ == "__main__":
    main()
