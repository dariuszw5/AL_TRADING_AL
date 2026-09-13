from datetime import datetime, timezone
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

print()
print("=" * 110)
print("=== OOS #1 | ENTRY HOURS ===")
print("=" * 110)
print("BUY=33.8 | SELL=68.5 | TIME=241 | RSI=classic | FEE=0.0004")
print()

for i, trade in enumerate(trades, 1):

    side = str(trade.get("side", "?")).upper()
    profit = float(trade.get("profit", 0.0))

    timestamp = (
        trade.get("entry_timestamp")
        or trade.get("timestamp")
        or trade.get("entry_time")
    )

    try:
        if isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(
                timestamp / 1000,
                tz=timezone.utc
            )
        else:
            dt = datetime.fromisoformat(
                str(timestamp).replace("Z", "+00:00")
            )

        hour = dt.hour
        date_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    except Exception:
        hour = -1
        date_str = str(timestamp)

    result = "WIN" if profit > 0 else "LOSS" if profit < 0 else "FLAT"

    print(
        f"{i:>2}. "
        f"{date_str:<22} | "
        f"HOUR={hour:02d} | "
        f"{side:<5} | "
        f"{result:<5} | "
        f"PROFIT={profit:>10.4f}"
    )


print()
print("=" * 110)
print("SUMMARY BY HOUR")
print("=" * 110)

hour_data = {}

for trade in trades:

    profit = float(trade.get("profit", 0.0))

    timestamp = (
        trade.get("entry_timestamp")
        or trade.get("timestamp")
        or trade.get("entry_time")
    )

    try:
        if isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(
                timestamp / 1000,
                tz=timezone.utc
            )
        else:
            dt = datetime.fromisoformat(
                str(timestamp).replace("Z", "+00:00")
            )

        hour = dt.hour

    except Exception:
        continue

    if hour not in hour_data:
        hour_data[hour] = []

    hour_data[hour].append(profit)


for hour in sorted(hour_data):

    profits = hour_data[hour]

    wins = sum(1 for p in profits if p > 0)
    losses = sum(1 for p in profits if p < 0)

    total = sum(profits)

    print(
        f"HOUR={hour:02d} | "
        f"TRADES={len(profits):>2} | "
        f"WINS={wins:>2} | "
        f"LOSSES={losses:>2} | "
        f"PROFIT={total:>10.4f}"
    )


print()
print("=" * 110)
print("END")
print("=" * 110)
