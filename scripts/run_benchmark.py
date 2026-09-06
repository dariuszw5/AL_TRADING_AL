from src.backtest.backtest_runner import BacktestRunner


runner = BacktestRunner(
    symbol="BTCUSDT",
    interval="1m",
    limit=5000,
    initial_balance=1000.0,
    buy_rsi=34.5,
    sell_rsi=68.5,
    min_difference=1.0,
    trading_fee=0.0004,
    rsi_method="classic",
    data_source="file"
)

runner.load_data()
runner.run()

summary = runner.get_summary()

print()
print("=== BACKTEST BENCHMARK ===")
print(f"Symbol:           {summary['symbol']}")
print(f"Interval:         {summary['interval']}")
print(f"Świece:           {summary['candles']}")
print(f"Kapitał początk.: {summary['initial_balance']}")
print(f"Kapitał końcowy:  {summary['final_balance']}")
print(f"Transakcje:       {summary['trades']}")
print(f"Wygrane:          {summary['winning_trades']}")
print(f"Przegrane:        {summary['losing_trades']}")
print(f"Win rate:         {summary['win_rate']}")
print(f"Total profit:     {summary['total_profit']}")
print(f"Max drawdown:     {summary['max_drawdown']}")
print(f"Profit factor:    {summary['profit_factor']}")
print(f"Average win:      {summary['average_win']}")
print(f"Average loss:     {summary['average_loss']}")
print(f"Largest win:     {summary['largest_win']}")
print(f"Largest loss:     {summary['largest_loss']}")
print(f"Expectancy:       {summary['expectancy']}")
