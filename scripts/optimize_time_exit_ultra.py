from src.backtest.backtest_runner import BacktestRunner


TIME_VALUES = [
    210,
    215,
    220,
    225,
    230,
    235,
    240,
]


print()
print("=== TIME EXIT ULTRA OPTIMIZATION ===")
print()

print(
    f"{'TIME':>6} | "
    f"{'TRADES':>6} | "
    f"{'WR %':>7} | "
    f"{'PROFIT':>10} | "
    f"{'PF':>8} | "
    f"{'DD':>10} | "
    f"{'EXPECT':>10}"
)

print("-" * 75)


for max_candles in TIME_VALUES:

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
        data_source="file"
    )

    runner.agent.config.max_position_candles = max_candles

    runner.load_data()
    runner.run()

    print(
        f"{max_candles:>6} | "
        f"{runner.get_trade_count():>6} | "
        f"{runner.get_win_rate():>7.2f} | "
        f"{runner.get_total_profit():>10.4f} | "
        f"{runner.get_profit_factor():>8.4f} | "
        f"{runner.get_max_drawdown():>10.4f} | "
        f"{runner.get_expectancy():>10.4f}"
    )