from src.backtest.backtest_runner import BacktestRunner


RSI_LEVELS = [
    (20.0, 80.0),
    (25.0, 75.0),
    (30.0, 70.0),
    (35.0, 65.0),
    (40.0, 60.0),
]


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
}


def run_backtest(data_file, buy_rsi, sell_rsi):

    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=buy_rsi,
        sell_rsi=sell_rsi,
        min_difference=1.0,
        trading_fee=0.0,
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


print()
print("=== RSI LEVELS TRAIN vs VALIDATION ===")
print()

print(
    f"{'BUY':>6} | "
    f"{'SELL':>6} | "
    f"{'TRAIN PROFIT':>12} | "
    f"{'TRAIN PF':>9} | "
    f"{'VALID PROFIT':>12} | "
    f"{'VALID PF':>9}"
)

print("-" * 75)


for buy_rsi, sell_rsi in RSI_LEVELS:

    train = run_backtest(
        DATASETS["TRAIN"],
        buy_rsi,
        sell_rsi
    )

    validation = run_backtest(
        DATASETS["VALIDATION"],
        buy_rsi,
        sell_rsi
    )

    print(
        f"{buy_rsi:>6.0f} | "
        f"{sell_rsi:>6.0f} | "
        f"{train.get_total_profit():>12.4f} | "
        f"{train.get_profit_factor():>9.4f} | "
        f"{validation.get_total_profit():>12.4f} | "
        f"{validation.get_profit_factor():>9.4f}"
    )
    