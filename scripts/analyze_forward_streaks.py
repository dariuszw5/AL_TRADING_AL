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
    data_file="data/backtest/BTCUSDT_1m_forward_5000.json",
)

runner.agent.config.max_position_candles = 241

runner.load_data()
runner.run()

trades = runner.get_trades()

results = [
    float(trade.get("profit", 0.0))
    for trade in trades
]

print()
print("=" * 100)
print("=== OOS #1 | WIN / LOSS STREAKS ===")
print("=" * 100)
print("BUY=33.8 | SELL=68.5 | TIME=241 | RSI=classic | FEE=0.0004")
print()

current_win = 0
current_loss = 0

max_win = 0
max_loss = 0

win_streaks = []
loss_streaks = []

for profit in results:

    if profit > 0:

        current_win += 1
        current_loss = 0

        max_win = max(max_win, current_win)

        if current_loss == 0:
            pass

    elif profit < 0:

        current_loss += 1
        current_win = 0

        max_loss = max(max_loss, current_loss)

    else:

        current_win = 0
        current_loss = 0


print("TRADE SEQUENCE")
print("-" * 100)

for i, trade in enumerate(trades, 1):

    profit = float(trade.get("profit", 0.0))
    side = str(trade.get("side", "?")).upper()

    if profit > 0:
        result = "WIN"
    elif profit < 0:
        result = "LOSS"
    else:
        result = "FLAT"

    print(
        f"{i:>2}. {side:<5} | "
        f"{result:<5} | "
        f"Profit={profit:>10.4f}"
    )


print()
print("STREAK SUMMARY")
print("-" * 100)
print(f"Longest winning streak : {max_win}")
print(f"Longest losing streak  : {max_loss}")

wins = sum(1 for p in results if p > 0)
losses = sum(1 for p in results if p < 0)

print()
print(f"Wins                   : {wins}")
print(f"Losses                 : {losses}")
print(f"Total                  : {len(results)}")

print()
print("=" * 100)
print("END")
print("=" * 100)
