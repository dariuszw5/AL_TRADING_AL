from src.backtest.backtest_runner import BacktestRunner


STOP_VALUES = [
    0.5,
    1.0,
    1.5,
    2.0,
    2.5,
    3.0,
    4.0,
    5.0,
]


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
}


def run_backtest(data_file, stop_loss_percent):
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=30.0,
        sell_rsi=70.0,
        min_difference=1.0,
        trading_fee=0.0,
        rsi_method="classic",
        data_source="file",
        data_file=data_file,
    )

    runner.agent.config.stop_loss_percent = stop_loss_percent
    runner.agent.config.risk_reward_ratio = 2.0
    runner.agent.config.max_position_candles = 240

    runner.load_data()
    runner.run()

    return runner


print()
print("=== STOP LOSS TRAIN vs VALIDATION ===")
print()

print(
    f"{'SL %':>6} | "
    f"{'TRAIN PROFIT':>12} | "
    f"{'TRAIN PF':>9} | "
    f"{'VALID PROFIT':>12} | "
    f"{'VALID PF':>9}"
)

print("-" * 65)


for stop_loss in STOP_VALUES:

    train = run_backtest(
        DATASETS["TRAIN"],
        stop_loss
    )

    validation = run_backtest(
        DATASETS["VALIDATION"],
        stop_loss
    )

    print(
        f"{stop_loss:>6.1f} | "
        f"{train.get_total_profit():>12.4f} | "
        f"{train.get_profit_factor():>9.4f} | "
        f"{validation.get_total_profit():>12.4f} | "
        f"{validation.get_profit_factor():>9.4f}"
    )