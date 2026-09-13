from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

RSI_LEVELS = [34.50, 34.75]


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


def print_trade(trade, number):
    print(f"  TRADE #{number}")

    if isinstance(trade, dict):
        for key, value in trade.items():
            print(f"    {key}: {value}")
    else:
        print(f"    {trade}")

    print()


def main():
    print()
    print("=" * 110)
    print("RSI 34.50 vs 34.75 | TRADE-BY-TRADE")
    print("=" * 110)

    for dataset, data_file in DATASETS.items():

        print()
        print("=" * 110)
        print(dataset)
        print("=" * 110)

        runners = {}

        for buy_rsi in RSI_LEVELS:
            runners[buy_rsi] = run_backtest(
                data_file,
                buy_rsi
            )

        for buy_rsi in RSI_LEVELS:
            runner = runners[buy_rsi]
            trades = runner.get_trades()

            print()
            print(f"BUY RSI={buy_rsi:.2f}")
            print("-" * 80)
            print(f"TRADES: {len(trades)}")

            for number, trade in enumerate(trades, start=1):
                print_trade(trade, number)

        print()
        print("SUMMARY")
        print("-" * 80)

        for buy_rsi in RSI_LEVELS:
            runner = runners[buy_rsi]

            print(
                f"RSI={buy_rsi:.2f} | "
                f"TRADES={runner.get_trade_count():3d} | "
                f"PROFIT={runner.get_total_profit():9.4f} | "
                f"PF={runner.get_profit_factor():7.4f} | "
                f"WR={runner.get_win_rate():6.2f}% | "
                f"EXP={runner.get_expectancy():8.4f}"
            )


if __name__ == "__main__":
    main()