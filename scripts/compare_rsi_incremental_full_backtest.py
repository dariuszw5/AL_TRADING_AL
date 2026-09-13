from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

THRESHOLDS = [
    34.50,
    35.25,
    35.50,
    35.75,
    36.00,
]


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


def main():
    print()
    print("=" * 115)
    print("RSI THRESHOLD FULL BACKTEST")
    print("Frozen datasets | Classic RSI | min_difference=1.0 | fee=0.0")
    print("=" * 115)

    for dataset_name, data_file in DATASETS.items():
        print()
        print("-" * 115)
        print(dataset_name)
        print("-" * 115)

        for buy_rsi in THRESHOLDS:
            runner = run_backtest(
                data_file=data_file,
                buy_rsi=buy_rsi
            )

            print(
                f"BUY={buy_rsi:5.2f} | "
                f"TRADES={runner.get_trade_count():2d} | "
                f"WR={runner.get_win_rate():6.2f}% | "
                f"PROFIT={runner.get_total_profit():9.4f} | "
                f"PF={runner.get_profit_factor():7.4f} | "
                f"DD={runner.get_max_drawdown():9.4f} | "
                f"EXP={runner.get_expectancy():8.4f}"
            )

    print()
    print("=" * 115)
    print("TEST COMPLETE")
    print("=" * 115)


if __name__ == "__main__":
    main()
