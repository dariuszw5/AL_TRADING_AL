from src.backtest.backtest_runner import BacktestRunner


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
    data_file="data/backtest/BTCUSDT_1m_validation_5000.json"
)

runner.agent.config.max_position_candles = 220

runner.load_data()
runner.run()

print()
print("=== TIME EXIT VALIDATION ===")
print()
print(f"TIME:        {runner.agent.config.max_position_candles} min")
print(f"TRADES:      {runner.get_trade_count()}")
print(f"WIN RATE:    {runner.get_win_rate():.2f}%")
print(f"PROFIT:      {runner.get_total_profit():.4f}")
print(f"PF:          {runner.get_profit_factor():.4f}")
print(f"DRAWDOWN:    {runner.get_max_drawdown():.4f}")
print(f"EXPECTANCY:  {runner.get_expectancy():.4f}")
print()