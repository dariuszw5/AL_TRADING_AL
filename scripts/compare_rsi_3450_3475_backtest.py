from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

RSI_LEVELS = [34.50, 34.75]


def run_backtest(data_path, buy_rsi):
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
    )

    # Używamy zamrożonego datasetu.
    runner.data_source = data_path

    runner.load_data()
    runner.run()

    return runner.get_summary()


def print_result(dataset, buy_rsi, summary):
    print(
        f"{dataset:10s} | "
        f"BUY={buy_rsi:5.2f} | "
        f"TRADES={summary['trades']:3d} | "
        f"WR={summary['win_rate']:6.2f}% | "
        f"PROFIT={summary['total_profit']:9.4f} | "
        f"PF={summary['profit_factor']:7.4f} | "
        f"DD={summary['max_drawdown']:9.4f} | "
        f"EXP={summary['expectancy']:8.4f}"
    )


def main():
    print()
    print("=" * 110)
    print("RSI 34.50 vs 34.75 | REAL BACKTEST")
    print("=" * 110)

    for dataset, path in DATASETS.items():
        print()
        print(f"--- {dataset} ---")

        for buy_rsi in RSI_LEVELS:
            summary = run_backtest(path, buy_rsi)
            print_result(dataset, buy_rsi, summary)


if __name__ == "__main__":
    main()