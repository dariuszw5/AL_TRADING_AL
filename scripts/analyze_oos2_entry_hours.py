from src.backtest.backtest_runner import BacktestRunner
from datetime import datetime, timezone
from collections import defaultdict


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
    data_file="data/backtest/BTCUSDT_1m_forward_5000_oos2.json",
)

runner.agent.config.max_position_candles = 241

runner.load_data()
runner.run()

trades = runner.get_trades()

hours = defaultdict(lambda: {
    "trades": 0,
    "wins": 0,
    "losses": 0,
    "profit": 0.0,
})

for trade in trades:

    timestamp = trade.get("entry_timestamp")

    if timestamp is None:
        continue

    if isinstance(timestamp, (int, float)):
        dt = datetime.fromtimestamp(
            timestamp / 1000,
            tz=timezone.utc,
        )
    else:
        dt = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))

    hour = dt.hour
    profit = float(trade.get("profit", 0.0))

    hours[hour]["trades"] += 1
    hours[hour]["profit"] += profit

    if profit > 0:
        hours[hour]["wins"] += 1
    elif profit < 0:
        hours[hour]["losses"] += 1


print()
print("=" * 100)
print("=== OOS #2 | ENTRY HOURS ===")
print("=" * 100)
print("BUY=33.8 | SELL=68.5 | TIME=241 | RSI=classic | FEE=0.0004")
print()

print(
    f"{'HOUR':>6} | "
    f"{'TRADES':>6} | "
    f"{'WINS':>5} | "
    f"{'LOSSES':>7} | "
    f"{'WINRATE':>8} | "
    f"{'PROFIT':>12}"
)

print("-" * 100)

for hour in sorted(hours):

    data = hours[hour]

    trades_count = data["trades"]
    wins = data["wins"]
    losses = data["losses"]
    profit = data["profit"]

    winrate = (
        wins / trades_count * 100
        if trades_count
        else 0.0
    )

    print(
        f"{hour:02d}:00 | "
        f"{trades_count:>6} | "
        f"{wins:>5} | "
        f"{losses:>7} | "
        f"{winrate:>7.2f}% | "
        f"{profit:>12.4f}"
    )

print()
print("=" * 100)
print("END")
print("=" * 100)
