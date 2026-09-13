from src.backtest.backtest_runner import BacktestRunner


RR_VALUES = [
    0.25,
    0.5,
    0.75,
    1.0,
    1.5,
    2.0,
    3.0,
    4.0,
]


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
}


def run_backtest(data_file, risk_reward_ratio):

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

    runner.agent.config.stop_loss_percent = 5.0
    runner.agent.config.risk_reward_ratio = risk_reward_ratio
    runner.agent.config.max_position_candles = 240

    runner.load_data()
    runner.run()

    return runner


print()
print("=== RISK/REWARD TRAIN vs VALIDATION ===")
print()

print(
    f"{'RR':>6} | "
    f"{'TRAIN PROFIT':>12} | "
    f"{'TRAIN PF':>9} | "
    f"{'VALID PROFIT':>12} | "
    f"{'VALID PF':>9}"
)

print("-" * 65)


for rr in RR_VALUES:

    train = run_backtest(
        DATASETS["TRAIN"],
        rr
    )

    validation = run_backtest(
        DATASETS["VALIDATION"],
        rr
    )

    print(
        f"{rr:>6.2f} | "
        f"{train.get_total_profit():>12.4f} | "
        f"{train.get_profit_factor():>9.4f} | "
        f"{validation.get_total_profit():>12.4f} | "
        f"{validation.get_profit_factor():>9.4f}"
    )