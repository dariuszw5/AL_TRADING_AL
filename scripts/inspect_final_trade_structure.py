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

    print()
    print("=" * 100)
    print(f"=== {dataset_name} TRADE STRUCTURE ===")
    print("=" * 100)

    if not trades:
        print("NO TRADES")
        continue

    print()
    print("TRADE DICT KEYS:")
    print(sorted(trades[0].keys()))

    print()
    print("FIRST TRADE:")
    print(trades[0])

    print()
    print("LAST TRADE:")
    print(trades[-1])

    print()
    print("ALL TRADE FIELD TYPES:")
    print("-" * 100)

    keys = sorted(trades[0].keys())

    for key in keys:
        value = trades[0].get(key)
        print(
            f"{key:<30} "
            f"type={type(value).__name__:<12} "
            f"value={value}"
        )

    print()
