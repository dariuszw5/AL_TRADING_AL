from datetime import datetime, timezone
from collections import defaultdict

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

    by_side = defaultdict(list)

    print()
    print("=" * 100)
    print(f"=== {dataset_name} TRADE DURATION / SIDE ===")
    print("=" * 100)

    for i, trade in enumerate(trades, 1):

        entry_ts = int(trade["entry_timestamp"])
        exit_ts = int(trade["exit_timestamp"])

        duration_minutes = (exit_ts - entry_ts) / 60000.0
        profit = float(trade["profit"])
        side = trade["side"]

        by_side[side].append(profit)

        entry_dt = datetime.fromtimestamp(
            entry_ts / 1000,
            tz=timezone.utc
        )

        exit_dt = datetime.fromtimestamp(
            exit_ts / 1000,
            tz=timezone.utc
        )

        print(
            f"{i:>2} | "
            f"{side:>4} | "
            f"duration={duration_minutes:>6.1f}m | "
            f"profit={profit:>9.4f} | "
            f"{entry_dt.strftime('%Y-%m-%d %H:%M')} -> "
            f"{exit_dt.strftime('%H:%M')} | "
            f"{trade['exit_reason']}"
        )

    print()
    print("SIDE SUMMARY")
    print("-" * 100)

    for side in ("BUY", "SELL"):

        values = by_side.get(side, [])

        if not values:
            print(f"{side}: no trades")
            continue

        wins = [x for x in values if x > 0]
        losses = [x for x in values if x < 0]

        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        pf = (
            gross_profit / gross_loss
            if gross_loss > 0
            else float("inf")
        )

        print(
            f"{side:>4} | "
            f"trades={len(values):>2} | "
            f"wins={len(wins):>2} | "
            f"losses={len(losses):>2} | "
            f"profit={sum(values):>10.4f} | "
            f"PF={pf:>7.4f}"
        )

    print()
