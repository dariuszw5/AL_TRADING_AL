from src.backtest.backtest_runner import BacktestRunner


TIME_VALUES = [
    300,
    330,
    360,
    390,
    420,
    450,
    480,
]


def run_backtest(data_file, max_candles):
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
        data_file=data_file
    )

    runner.agent.config.max_position_candles = max_candles

    runner.load_data()
    runner.run()

    return {
        "trades": runner.get_trade_count(),
        "win_rate": runner.get_win_rate(),
        "profit": runner.get_total_profit(),
        "pf": runner.get_profit_factor(),
        "dd": runner.get_max_drawdown(),
        "expectancy": runner.get_expectancy(),
    }


train_file = "data/backtest/BTCUSDT_1m_5000.json"
validation_file = "data/backtest/BTCUSDT_1m_validation_5000.json"


print()
print("=== TIME EXIT TRAIN vs VALIDATION ===")
print()

print(
    f"{'TIME':>6} | "
    f"{'TRAIN PROFIT':>12} | "
    f"{'TRAIN PF':>9} | "
    f"{'VALID PROFIT':>12} | "
    f"{'VALID PF':>9}"
)

print("-" * 65)


for max_candles in TIME_VALUES:

    train = run_backtest(
        train_file,
        max_candles
    )

    validation = run_backtest(
        validation_file,
        max_candles
    )

    print(
        f"{max_candles:>6} | "
        f"{train['profit']:>12.4f} | "
        f"{train['pf']:>9.4f} | "
        f"{validation['profit']:>12.4f} | "
        f"{validation['pf']:>9.4f}"
    )