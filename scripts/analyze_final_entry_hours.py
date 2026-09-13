from collections import defaultdict
from datetime import datetime, timezone

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

    hours = defaultdict(list)

    for trade in trades:
        timestamp = int(trade["entry_timestamp"])

        hour = datetime.fromtimestamp(
            timestamp / 1000,
            tz=timezone.utc
        ).hour

        hours[hour].append(trade)

    print()
    print("=" * 100)
    print(f"=== {dataset_name} ENTRY HOUR ANALYSIS (UTC) ===")
    print("=" * 100)

    print()
    print(
        f"{'HOUR':>4} | "
        f"{'TRADES':>6} | "
        f"{'WINS':>4} | "
        f"{'LOSSES':>6} | "
        f"{'WR':>7} | "
        f"{'PROFIT':>10} | "
        f"{'AVG':>9}"
    )

    print("-" * 100)

    for hour in range(24):

        bucket = hours.get(hour, [])

        if not bucket:
            continue

        profits = [
            float(t["profit"])
            for t in bucket
        ]

        wins = [p for p in profits if p > 0]
        losses = [p for p in profits if p < 0]

        win_rate = (
            len(wins) / len(profits) * 100
            if profits
            else 0.0
        )

        total_profit = sum(profits)
        avg_profit = total_profit / len(profits)

        print(
            f"{hour:>4} | "
            f"{len(profits):>6} | "
            f"{len(wins):>4} | "
            f"{len(losses):>6} | "
            f"{win_rate:>6.2f}% | "
            f"{total_profit:>10.4f} | "
            f"{avg_profit:>9.4f}"
        )

    print()
