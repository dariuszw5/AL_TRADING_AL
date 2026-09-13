from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


CONFIGS = [
    (34.50, 68.25),
    (34.50, 68.50),
    (35.50, 68.25),
    (35.50, 68.50),
]

FEE = 0.0004
MIN_DIFFERENCE = 1.0


def run_backtest(path, buy_rsi, sell_rsi):

    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=sell_rsi,
        min_difference=MIN_DIFFERENCE,
        trading_fee=FEE,
        rsi_method="classic",
        data_source="file",
        data_file=path,
    )

    runner.load_data()
    runner.run()

    result = runner.get_backtest_result()

    return result


def trade_key(trade):

    return (
        trade["entry_timestamp"],
        trade["side"],
    )


def print_trades(label, result):

    print()
    print(f"--- {label} ---")

    for i, trade in enumerate(result.trades, start=1):

        print(
            f"{i:2d}. "
            f"{trade['side']:4s} "
            f"ENTRY={trade['entry_timestamp']} "
            f"EXIT={trade['exit_timestamp']} "
            f"P/L={trade['profit']:+.4f} "
            f"REASON={trade['exit_reason']}"
        )


def main():

    print()
    print("=" * 150)
    print("SELL THRESHOLD DIVERGENCE ANALYSIS")
    print(
        "FEE=0.0004 | MIN_DIFF=1.00 | RSI=classic"
    )
    print("=" * 150)

    for dataset, path in DATASETS.items():

        print()
        print()
        print("#" * 150)
        print(f"DATASET: {dataset}")
        print("#" * 150)

        results = {}

        for buy, sell in CONFIGS:

            result = run_backtest(
                path,
                buy,
                sell
            )

            results[(buy, sell)] = result

            profit = (
                result.balance
                - result.initial_balance
            )

            print()
            print(
                f"BUY={buy:.2f} "
                f"SELL={sell:.2f} "
                f"PROFIT={profit:+.4f} "
                f"TRADES={len(result.trades)}"
            )

            print_trades(
                f"BUY={buy:.2f} SELL={sell:.2f}",
                result
            )

        print()
        print("=" * 150)
        print("PAIRWISE DIFFERENCES")
        print("=" * 150)

        pairs = [
            ((34.50, 68.25), (34.50, 68.50)),
            ((35.50, 68.25), (35.50, 68.50)),
        ]

        for config_a, config_b in pairs:

            result_a = results[config_a]
            result_b = results[config_b]

            trades_a = {
                trade_key(t): t
                for t in result_a.trades
            }

            trades_b = {
                trade_key(t): t
                for t in result_b.trades
            }

            keys = sorted(
                set(trades_a) | set(trades_b)
            )

            print()
            print(
                f"COMPARE "
                f"{config_a[0]:.2f}/{config_a[1]:.2f}"
                f" -> "
                f"{config_b[0]:.2f}/{config_b[1]:.2f}"
            )

            profit_a = (
                result_a.balance
                - result_a.initial_balance
            )

            profit_b = (
                result_b.balance
                - result_b.initial_balance
            )

            print(
                f"TOTAL A={profit_a:+.4f} | "
                f"TOTAL B={profit_b:+.4f} | "
                f"DELTA={profit_b - profit_a:+.4f}"
            )

            print()

            for key in keys:

                a = trades_a.get(key)
                b = trades_b.get(key)

                if a and b:

                    delta = (
                        b["profit"]
                        - a["profit"]
                    )

                    if abs(delta) > 1e-9:

                        print(
                            f"SAME ENTRY "
                            f"{key} | "
                            f"A={a['profit']:+.4f} | "
                            f"B={b['profit']:+.4f} | "
                            f"DELTA={delta:+.4f}"
                        )

                elif a:

                    print(
                        f"ONLY A "
                        f"{key} | "
                        f"A P/L={a['profit']:+.4f}"
                    )

                elif b:

                    print(
                        f"ONLY B "
                        f"{key} | "
                        f"B P/L={b['profit']:+.4f}"
                    )

        print()
        print("=" * 150)
        print("END DATASET")
        print("=" * 150)


if __name__ == "__main__":
    main()
