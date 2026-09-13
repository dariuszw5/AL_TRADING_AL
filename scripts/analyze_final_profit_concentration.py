from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


def run_backtest(data_file):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=34.50,
        sell_rsi=68.50,
        min_difference=1.0,
        trading_fee=0.0004,
        rsi_method="classic",
        data_source="file",
        data_file=data_file,
    )

    runner.agent.config.stop_loss_percent = 5.0
    runner.agent.config.risk_reward_ratio = 2.0
    runner.agent.config.max_position_candles = 240

    runner.load_data()
    runner.run()

    return runner


for dataset_name, data_file in DATASETS.items():

    runner = run_backtest(data_file)
    trades = runner.get_trades()

    profits = [
        float(trade.get("profit", 0.0))
        for trade in trades
    ]

    profits.sort(reverse=True)

    total_profit = sum(profits)

    print()
    print("=" * 80)
    print(f"=== {dataset_name} PROFIT CONCENTRATION ===")
    print("=" * 80)

    print(f"Trades              : {len(profits)}")
    print(f"Total profit        : {total_profit:10.4f}")
    print(f"Profit factor       : {runner.get_profit_factor():10.4f}")
    print(f"Expectancy          : {runner.get_expectancy():10.4f}")

    if not profits:
        continue

    print()
    print("TOP WINNERS")
    print("-" * 80)

    for i, profit in enumerate(profits[:5], 1):
        share = (
            profit / total_profit * 100.0
            if total_profit != 0
            else 0.0
        )
        print(
            f"{i:>2}. Profit={profit:>10.4f} | "
            f"Share of total={share:>7.2f}%"
        )

    top1 = sum(profits[:1])
    top3 = sum(profits[:3])

    remaining_after_top1 = total_profit - top1
    remaining_after_top3 = total_profit - top3

    print()
    print("CONCENTRATION")
    print("-" * 80)
    print(f"Top 1 contribution        : {top1:>10.4f}")
    print(f"Profit without Top 1      : {remaining_after_top1:>10.4f}")
    print(f"Top 3 contribution        : {top3:>10.4f}")
    print(f"Profit without Top 3      : {remaining_after_top3:>10.4f}")

    if len(profits) >= 2:
        median_index = len(profits) // 2

        if len(profits) % 2:
            median_profit = profits[median_index]
        else:
            median_profit = (
                profits[median_index - 1] + profits[median_index]
            ) / 2.0

        print(f"Median trade profit       : {median_profit:>10.4f}")

    print()
