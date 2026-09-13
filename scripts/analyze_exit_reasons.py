from collections import Counter

from src.backtest.backtest_runner import BacktestRunner


TIME_VALUES = [
    180,
    240,
    360,
]


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


def run_backtest(data_file, max_position_candles):

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
    runner.agent.config.max_position_candles = max_position_candles

    runner.load_data()
    runner.run()

    return runner


for dataset_name, data_file in DATASETS.items():

    print()
    print("=" * 75)
    print(f"=== {dataset_name} EXIT ANALYSIS ===")
    print("=" * 75)
    print()

    print(
        f"{'TIME':>6} | "
        f"{'TRADES':>6} | "
        f"{'SL':>5} | "
        f"{'TP':>5} | "
        f"{'TIME':>6} | "
        f"{'END':>5} | "
        f"{'PROFIT':>10} | "
        f"{'PF':>7}"
    )

    print("-" * 75)

    for max_time in TIME_VALUES:

        runner = run_backtest(
            data_file,
            max_time
        )

        trades = runner.get_trades()

        reasons = Counter(
            trade.get("exit_reason")
            for trade in trades
        )

        print(
            f"{max_time:>6} | "
            f"{len(trades):>6} | "
            f"{reasons.get('STOP_LOSS', 0):>5} | "
            f"{reasons.get('TAKE_PROFIT', 0):>5} | "
            f"{reasons.get('TIME_EXIT', 0):>6} | "
            f"{reasons.get('END_OF_DATA', 0):>5} | "
            f"{runner.get_total_profit():>10.4f} | "
            f"{runner.get_profit_factor():>7.4f}"
        )

    print()
