from src.backtest.backtest_runner import BacktestRunner


runner = BacktestRunner(
    symbol="BTCUSDT",
    interval="1m",
    limit=5000,
    initial_balance=1000.0,
    buy_rsi=30.0,
    sell_rsi=70.0,
    min_difference=1.0,
    trading_fee=0.001,
    rsi_method="classic",
    data_source="file",
    data_file="data/backtest/BTCUSDT_1m_5000.json"
)

runner.load_data()
runner.run()

print()
print("=== TRANSACTION DIAGNOSTICS ===")

trades = runner.get_trades()

print(f"Number of trades: {len(trades)}")
print()

for i, trade in enumerate(trades, 1):
    print(f"--- TRADE {i} ---")

    for key, value in trade.items():
        print(f"{key}: {value}")

    print()

print("=== SUMMARY ===")
print(f"Initial balance: {runner.initial_balance}")
print(f"Final balance:   {runner.get_balance()}")
print(f"Total profit:    {runner.get_total_profit()}")
print(f"Trades:          {runner.get_trade_count()}")
print(f"Winners:         {runner.get_winning_trades()}")
print(f"Losers:          {runner.get_losing_trades()}")
print(f"Win rate:        {runner.get_win_rate()}")
print(f"Max drawdown:    {runner.get_max_drawdown()}")
print(f"Profit factor:   {runner.get_profit_factor()}")
print(f"Average win:     {runner.get_average_win()}")
print(f"Average loss:    {runner.get_average_loss()}")
print(f"Largest win:     {runner.get_largest_win()}")
print(f"Largest loss:    {runner.get_largest_loss()}")
print(f"Expectancy:      {runner.get_expectancy()}")
