from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

THRESHOLDS = (34.50, 35.50)


def run_backtest(data_file, buy_rsi):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=70.0,
        min_difference=1.0,
        trading_fee=0.0,
        rsi_method="classic",
        data_source="file",
        data_file=data_file,
    )

    runner.load_data()
    runner.run()

    return runner


def trade_dict(trade):
    if isinstance(trade, dict):
        return trade

    if hasattr(trade, "__dict__"):
        return vars(trade)

    return {}


def get_value(data, names, default=None):
    for name in names:
        if name in data:
            return data[name]

    return default


def trade_summary(trade, number):
    data = trade_dict(trade)

    entry_index = get_value(
        data,
        ["entry_index", "entry_candle_index", "open_index"]
    )

    exit_index = get_value(
        data,
        ["exit_index", "exit_candle_index", "close_index"]
    )

    entry_price = get_value(
        data,
        ["entry_price", "open_price"]
    )

    exit_price = get_value(
        data,
        ["exit_price", "close_price"]
    )

    profit = get_value(
        data,
        ["profit", "pnl", "profit_loss", "realized_pnl"]
    )

    side = get_value(
        data,
        ["side", "direction"]
    )

    return {
        "number": number,
        "entry_index": entry_index,
        "exit_index": exit_index,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "profit": profit,
        "side": side,
        "raw": data,
    }


def print_trade(summary):
    print(
        f"#{summary['number']:02d} | "
        f"ENTRY_IDX={str(summary['entry_index']):>5} | "
        f"EXIT_IDX={str(summary['exit_index']):>5} | "
        f"ENTRY={str(summary['entry_price']):>12} | "
        f"EXIT={str(summary['exit_price']):>12} | "
        f"PROFIT={str(summary['profit']):>12} | "
        f"SIDE={summary['side']}"
    )


def main():
    print()
    print("=" * 120)
    print("TRADE-BY-TRADE COMPARISON: RSI 34.50 vs 35.50")
    print("=" * 120)

    for dataset_name, data_file in DATASETS.items():
        print()
        print("#" * 120)
        print(dataset_name)
        print("#" * 120)

        runners = {}

        for threshold in THRESHOLDS:
            runners[threshold] = run_backtest(
                data_file=data_file,
                buy_rsi=threshold
            )

        trades = {}

        for threshold, runner in runners.items():
            raw_trades = runner.backtest_engine.get_trades()

            trades[threshold] = [
                trade_summary(trade, i + 1)
                for i, trade in enumerate(raw_trades)
            ]

            print()
            print(
                f"RSI {threshold:.2f} | "
                f"TRADES={len(raw_trades)} | "
                f"PROFIT={runner.get_total_profit():.4f} | "
                f"PF={runner.get_profit_factor():.4f} | "
                f"WR={runner.get_win_rate():.2f}%"
            )

        print()
        print("-" * 120)
        print("RSI 34.50")
        print("-" * 120)

        for trade in trades[34.50]:
            print_trade(trade)

        print()
        print("-" * 120)
        print("RSI 35.50")
        print("-" * 120)

        for trade in trades[35.50]:
            print_trade(trade)

        print()
        print("-" * 120)
        print("RAW DIFFERENCES")
        print("-" * 120)

        t34 = trades[34.50]
        t35 = trades[35.50]

        max_len = max(len(t34), len(t35))

        for i in range(max_len):
            a = t34[i] if i < len(t34) else None
            b = t35[i] if i < len(t35) else None

            if a is None:
                print(f"35.50 ONLY | TRADE #{i + 1}")
                print_trade(b)
                continue

            if b is None:
                print(f"34.50 ONLY | TRADE #{i + 1}")
                print_trade(a)
                continue

            key_a = (
                a["entry_index"],
                a["exit_index"],
                a["entry_price"],
                a["exit_price"],
                a["profit"],
            )

            key_b = (
                b["entry_index"],
                b["exit_index"],
                b["entry_price"],
                b["exit_price"],
                b["profit"],
            )

            if key_a != key_b:
                print(f"DIFFERENCE AROUND TRADE #{i + 1}")

                print("34.50:")
                print_trade(a)

                print("35.50:")
                print_trade(b)

    print()
    print("=" * 120)
    print("COMPARISON COMPLETE")
    print("=" * 120)


if __name__ == "__main__":
    main()
