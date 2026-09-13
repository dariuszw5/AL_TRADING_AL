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

# ZAMROŻONA STRATEGIA
runner.agent.config.max_position_candles = 241

runner.run()

trades = runner.get_trades()

print()
print("=" * 110)
print("=== OOS #1 TRADE ANALYSIS ===")
print("=" * 110)
print("BUY=33.8 | SELL=68.5 | TIME=241 | RSI=classic | FEE=0.0004")
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
    print(f"  Profit:      {profit:+.6f}")
    print(f"  Exit reason: {exit_reason}")
    print(f"  Duration:    {duration_minutes:.1f} min")
    print()

print("=" * 110)
print("=== OOS #1 SUMMARY ===")
print("=" * 110)

wins = [t["profit"] for t in trades if t["profit"] > 0]
losses = [t["profit"] for t in trades if t["profit"] < 0]

print(f"Trades:        {len(trades)}")
print(f"Wins:          {len(wins)}")
print(f"Losses:        {len(losses)}")
print(f"Total profit:  {sum(t['profit'] for t in trades):+.6f}")
print(f"Best trade:    {max(wins):+.6f}")
print(f"Worst trade:   {min(losses):+.6f}")
print(f"Avg win:       {sum(wins)/len(wins):+.6f}")
print(f"Avg loss:      {sum(losses)/len(losses):+.6f}")
print("=" * 110)
