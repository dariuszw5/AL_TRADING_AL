from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


BUY_RSI = 35.50
SELL_A = 68.50
SELL_B = 76.50
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


def candle_timestamp(candle):
    return candle.timestamp


def candle_close(candle):
    return float(candle.close)


def trade_entry_index(trade, candles):
    timestamp = trade.get("entry_timestamp")

    for index, candle in enumerate(candles):
        if candle_timestamp(candle) == timestamp:
            return index

    return None


def trade_exit_index(trade, candles):
    timestamp = trade.get("exit_timestamp")

    for index, candle in enumerate(candles):
        if candle_timestamp(candle) == timestamp:
            return index

    return None


def trade_map(trades, candles):
    result = {}

    for trade in trades:
        index = trade_entry_index(
            trade,
            candles
        )

        if index is not None:
            result[index] = trade

    return result


def print_trade(label, trade, candles):

    if trade is None:
        print(f"{label}: NONE")
        return

    entry = trade_entry_index(
        trade,
        candles
    )

    exit_ = trade_exit_index(
        trade,
        candles
    )

    side = trade.get(
        "side",
        trade.get("signal", "?")
    )

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
        f"{entry} -> {exit_} "
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

    map_a = trade_map(
        trades_a,
        candles
    )

    map_b = trade_map(
        trades_b,
        candles
    )

    entries_a = set(map_a)
    entries_b = set(map_b)

    divergences = sorted(
        entries_a ^ entries_b
    )

    print()
    print("=" * 125)
    print(
        f"{name} | "
        f"REAL BACKTEST | "
        f"SELL {SELL_A:.2f} vs SELL {SELL_B:.2f}"
    )
    print("=" * 125)

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
        f"REAL ENTRY DIVERGENCIES: "
        f"{len(divergences)}"
    )

    for index in divergences:

        trade_a = map_a.get(index)
        trade_b = map_b.get(index)

        print()
        print("-" * 125)

        print(
            f"INDEX={index} | "
            f"PRICE={candle_close(candles[index]):.2f}"
        )

        print_trade(
            f"SELL {SELL_A:.2f}",
            trade_a,
            candles
        )

        print_trade(
            f"SELL {SELL_B:.2f}",
            trade_b,
            candles
        )

        if trade_a is not None and trade_b is None:

            profit = float(
                trade_a.get(
                    "profit",
                    0.0
                )
            )

            print(
                f"UNIQUE TO {SELL_A:.2f}: "
                f"P/L={profit:+.4f}"
            )

        elif trade_b is not None and trade_a is None:

            profit = float(
                trade_b.get(
                    "profit",
                    0.0
                )
            )

            print(
                f"UNIQUE TO {SELL_B:.2f}: "
                f"P/L={profit:+.4f}"
            )

    print()
    print("=" * 125)
    print(
        f"{name} | END"
    )
    print("=" * 125)


def main():

    for name, path in DATASETS.items():

        compare_dataset(
            name,
            path
        )


if __name__ == "__main__":
    main()
