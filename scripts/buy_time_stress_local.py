from src.backtest.backtest_runner import BacktestRunner


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALID": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

BUY_VALUES = [33.7, 33.8, 33.9, 34.0, 34.1, 34.2]
TIME_VALUES = [239, 240, 241, 242, 243]

SELL_RSI = 68.5
FEE = 0.0004


def run_backtest(data_path, buy_rsi, max_time):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=SELL_RSI,
        min_difference=1.0,
        trading_fee=FEE,
        rsi_method="classic",
        data_source="file",
        data_file=data_path,
    )

    runner.agent.config.max_position_candles = max_time

    runner.run()

    return (
        runner.get_total_profit(),
        runner.get_profit_factor(),
        runner.get_max_drawdown(),
        runner.get_win_rate(),
        runner.get_trade_count(),
    )


print()
print("=" * 110)
print(
    f"BUY x TIME STRESS | SELL={SELL_RSI} | FEE={FEE:.4f}"
)
print("=" * 110)

results = []

for buy_rsi in BUY_VALUES:
    for max_time in TIME_VALUES:

        metrics = {}

        for dataset_name, data_path in DATASETS.items():
            metrics[dataset_name] = run_backtest(
                data_path,
                buy_rsi,
                max_time,
            )

        total_profit = sum(
            metrics[name][0]
            for name in DATASETS
        )

        test_profit = metrics["TEST"][0]
        test_pf = metrics["TEST"][1]

        results.append(
            (
                total_profit,
                test_profit,
                test_pf,
                buy_rsi,
                max_time,
                metrics,
            )
        )

        print(
            f"BUY={buy_rsi:>4.1f} | "
            f"TIME={max_time:>3} | "
            f"TRAIN={metrics['TRAIN'][0]:>8.4f} | "
            f"VALID={metrics['VALID'][0]:>8.4f} | "
            f"TEST={test_profit:>8.4f} | "
            f"TEST PF={test_pf:>6.4f} | "
            f"TOTAL={total_profit:>8.4f}"
        )


print()
print("=" * 110)
print("RANKING BY TEST PROFIT")
print("=" * 110)

for rank, item in enumerate(
    sorted(results, key=lambda x: (x[1], x[2], x[0]), reverse=True),
    start=1,
):
    total_profit, test_profit, test_pf, buy_rsi, max_time, metrics = item

    print(
        f"{rank:>2}. "
        f"BUY={buy_rsi:>4.1f} | "
        f"TIME={max_time:>3} | "
        f"TEST={test_profit:>8.4f} | "
        f"PF={test_pf:>6.4f} | "
        f"TOTAL={total_profit:>8.4f} | "
        f"TRAIN={metrics['TRAIN'][0]:>8.4f} | "
        f"VALID={metrics['VALID'][0]:>8.4f}"
    )
