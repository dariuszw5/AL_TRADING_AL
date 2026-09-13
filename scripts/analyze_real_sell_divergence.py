from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


BUY_RSI = 35.50
SELL_A = 69.0
SELL_B = 77.0
MIN_DIFFERENCE = 1.0
TRADING_FEE = 0.0
RSI_METHOD = "classic"


def run_backtest(data_file, sell_rsi):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=BUY_RSI,
        sell_rsi=sell_rsi,
        min_difference=MIN_DIFFERENCE,
        trading_fee=TRADING_FEE,
        rsi_method=RSI_METHOD,
        data_source="file",
        data_file=data_file,
    )

    runner.load_data()
    runner.run()

    return runner


def trade_entry(trade):
    return trade.get("entry_timestamp")


def trade_exit(trade):
    return trade.get("exit_timestamp")


def candle_timestamp(candle):
    return candle.timestamp


def candle_close(candle):
    return float(candle.close)


def trade_index_from_timestamp(trade, candles):
    timestamp = trade_entry(trade)

    for index, candle in enumerate(candles):
        if candle_timestamp(candle) == timestamp:
            return index

    return None


def trade_exit_index(trade, candles):
    timestamp = trade_exit(trade)

    for index, candle in enumerate(candles):
        if candle_timestamp(candle) == timestamp:
            return index

    return None


def trade_by_entry_index(trades, candles):
    result = {}

    for trade in trades:
        index = trade_index_from_timestamp(trade, candles)

        if index is not None:
            result[index] = trade

    return result


def print_trade(label, trade, candles):
    if trade is None:
        print(f"{label}: NONE")
        return

    entry_index = trade_index_from_timestamp(trade, candles)
    exit_index = trade_exit_index(trade, candles)

    side = trade.get("side", trade.get("signal", "?"))

    profit = float(
        trade.get("profit", 0.0)
    )

    entry_price = float(
        trade.get("entry_price", 0.0)
    )

    exit_price = float(
        trade.get("exit_price", 0.0)
    )

    reason = trade.get(
        "exit_reason",
        "?"
    )

    print(
        f"{label}: "
        f"{side} "
        f"{entry_index} -> {exit_index} "
        f"ENTRY={entry_price:.2f} "
        f"EXIT={exit_price:.2f} "
        f"P/L={profit:+.4f} "
        f"REASON={reason}"
    )


def compare_dataset(name, path):

    runner_a = run_backtest(
        path,
        SELL_A
    )

    runner_b = run_backtest(
        path,
        SELL_B
    )

    candles = runner_a.candles

    trades_a = runner_a.get_trades()
    trades_b = runner_b.get_trades()

    map_a = trade_by_entry_index(
        trades_a,
        candles
    )

    map_b = trade_by_entry_index(
        trades_b,
        candles
    )

    entries_a = set(map_a)
    entries_b = set(map_b)

    divergences = sorted(
        entries_a ^ entries_b
    )

    print()
    print("=" * 120)
    print(
        f"{name} | REAL BACKTEST | "
        f"SELL {SELL_A:.2f} vs SELL {SELL_B:.2f}"
    )
    print("=" * 120)
    print()

    print(
        f"SELL {SELL_A:.2f}: "
        f"{len(trades_a)} trades | "
        f"PROFIT={runner_a.get_total_profit():+.4f} | "
        f"FINAL={runner_a.get_balance():.4f} | "
        f"PF={runner_a.get_profit_factor():.4f}"
    )

    print(
        f"SELL {SELL_B:.2f}: "
        f"{len(trades_b)} trades | "
        f"PROFIT={runner_b.get_total_profit():+.4f} | "
        f"FINAL={runner_b.get_balance():.4f} | "
        f"PF={runner_b.get_profit_factor():.4f}"
    )

    print()
    print(
        f"REAL TRADE ENTRY DIVERGENCIES: "
        f"{len(divergences)}"
    )

    total_a_advantage = 0.0
    total_b_advantage = 0.0

    for index in divergences:

        trade_a = map_a.get(index)
        trade_b = map_b.get(index)

        price = candle_close(
            candles[index]
        )

        print()
        print("-" * 120)
        print(
            f"INDEX {index} | "
            f"PRICE={price:.2f}"
        )

        print_trade(
            f"SELL {SELL_A:.0f}",
            trade_a,
            candles
        )

        print_trade(
            f"SELL {SELL_B:.0f}",
            trade_b,
            candles
        )

        if trade_a is not None and trade_b is None:

            profit_a = float(
                trade_a.get(
                    "profit",
                    0.0
                )
            )

            total_a_advantage += profit_a

            print(
                f"CAUSAL DIFFERENCE: "
                f"SELL {SELL_A:.0f} took this trade "
                f"-> {profit_a:+.4f}"
            )

        elif trade_b is not None and trade_a is None:

            profit_b = float(
                trade_b.get(
                    "profit",
                    0.0
                )
            )

            total_b_advantage += profit_b

            print(
                f"CAUSAL DIFFERENCE: "
                f"SELL {SELL_B:.0f} took this trade "
                f"-> {profit_b:+.4f}"
            )

    print()
    print("=" * 120)
    print(
        f"{name} | DIVERGENCE CONTRIBUTION"
    )
    print("=" * 120)

    print(
        f"SELL {SELL_A:.0f} "
        f"unique-entry contribution: "
        f"{total_a_advantage:+.4f}"
    )

    print(
        f"SELL {SELL_B:.0f} "
        f"unique-entry contribution: "
        f"{total_b_advantage:+.4f}"
    )

    print(
        f"Difference B-A: "
        f"{total_b_advantage - total_a_advantage:+.4f}"
    )


def main():

    for name, path in DATASETS.items():

        compare_dataset(
            name,
            path
        )


if __name__ == "__main__":
    main()
