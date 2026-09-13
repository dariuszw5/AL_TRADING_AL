from src.backtest.backtest_runner import BacktestRunner


runner = BacktestRunner(
    symbol="BTCUSDT",
    interval="1m",
    limit=5000,
    initial_balance=1000.0,
    buy_rsi=33.8,
    sell_rsi=68.5,
    min_difference=1.0,
    trading_fee=0.0004,
    rsi_method="classic",
    data_source="file",
    data_file="data/backtest/BTCUSDT_1m_forward_5000.json"
)

runner.load_data()

# ZAMROŻONY PARAMETR STRATEGII
runner.agent.config.max_position_candles = 241

runner.run()

summary = runner.get_summary()

print()
print("=== FORWARD / OOS BENCHMARK #1 ===")
print("Frozen strategy:")
print("BUY RSI:          33.8")
print("SELL RSI:         68.5")
print("MAX TIME:         241")
print("RSI method:       classic")
print("MIN DIFFERENCE:   1.0")
print("FEE:              0.0004")
print()
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
print(f"Largest win:      {summary['largest_win']}")
print(f"Largest loss:     {summary['largest_loss']}")
print(f"Expectancy:       {summary['expectancy']}")
