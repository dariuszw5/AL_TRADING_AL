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
    data_source="file"
)

runner.load_data()
runner.run()

trades = runner.get_trades()

print()
print("=== TRADE ANALYSIS ===")
print()

for i, trade in enumerate(trades, start=1):

    entry = trade.get("entry_price", 0)
    exit_price = trade.get("exit_price", 0)
    quantity = trade.get("quantity", 0)
    profit = trade.get("profit", 0)

    side = trade.get("side")
    entry_timestamp = trade.get("entry_timestamp")
    exit_timestamp = trade.get("exit_timestamp")

    stop_loss = trade.get("stop_loss")
    take_profit = trade.get("take_profit")

    exit_reason = trade.get("exit_reason")

    duration_minutes = None

    if entry_timestamp is not None and exit_timestamp is not None:
        duration_minutes = (
            exit_timestamp - entry_timestamp
        ) / 60000

    print(f"TRADE #{i}")
    print(f"  Side:        {side}")
    print(f"  Entry:       {entry}")
    print(f"  Exit:        {exit_price}")
    print(f"  Quantity:    {quantity}")
    print(f"  Stop Loss:   {stop_loss}")
    print(f"  Take Profit: {take_profit}")
    print(f"  Profit:      {profit}")
    print(f"  Exit reason: {exit_reason}")
    print(f"  Duration:    {duration_minutes}")
    print()