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


def get_value(trade, *keys):
    for key in keys:
        if key in trade and trade[key] is not None:
            return trade[key]
    return None


def format_timestamp(value):
    if value is None:
        return "N/A"

    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(
                value / 1000,
                tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S UTC")

        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        ).strftime("%Y-%m-%d %H:%M:%S UTC")

    except Exception:
        return str(value)


def duration_minutes(entry, exit_):
    if entry is None or exit_ is None:
        return None

    try:
        if isinstance(entry, (int, float)):
            entry_dt = datetime.fromtimestamp(
                entry / 1000,
                tz=timezone.utc
            )
        else:
            entry_dt = datetime.fromisoformat(
                str(entry).replace("Z", "+00:00")
            )

        if isinstance(exit_, (int, float)):
            exit_dt = datetime.fromtimestamp(
                exit_ / 1000,
                tz=timezone.utc
            )
        else:
            exit_dt = datetime.fromisoformat(
                str(exit_).replace("Z", "+00:00")
            )

        return (exit_dt - entry_dt).total_seconds() / 60.0

    except Exception:
        return None


print()
print("=" * 125)
print("=== OOS #1 | TRADE STRUCTURE: RSI + TIME + EXIT ===")
print("=" * 125)
print("BUY=33.8 | SELL=68.5 | TIME=241 | RSI=classic | FEE=0.0004")
print()


rows = []

for i, trade in enumerate(trades, 1):

    side = str(get_value(trade, "side") or "?").upper()

    profit = float(
        get_value(trade, "profit", "pnl", "pnl_quote")
        or 0.0
    )

    entry_timestamp = get_value(
        trade,
        "entry_timestamp",
        "entry_time",
        "timestamp"
    )

    exit_timestamp = get_value(
        trade,
        "exit_timestamp",
        "exit_time"
    )

    rsi = get_value(
        trade,
        "entry_rsi",
        "rsi",
        "entry_RSI"
    )

    entry_price = get_value(
        trade,
        "entry_price",
        "entry"
    )

    exit_price = get_value(
        trade,
        "exit_price",
        "exit"
    )

    exit_reason = get_value(
        trade,
        "exit_reason",
        "reason"
    )

    duration = duration_minutes(
        entry_timestamp,
        exit_timestamp
    )

    if profit > 0:
        result = "WIN"
    elif profit < 0:
        result = "LOSS"
    else:
        result = "FLAT"

    if isinstance(entry_timestamp, (int, float)):
        hour = datetime.fromtimestamp(
            entry_timestamp / 1000,
            tz=timezone.utc
        ).hour
    else:
        try:
            hour = datetime.fromisoformat(
                str(entry_timestamp).replace("Z", "+00:00")
            ).hour
        except Exception:
            hour = -1

    rows.append({
        "number": i,
        "side": side,
        "result": result,
        "profit": profit,
        "rsi": rsi,
        "hour": hour,
        "entry": entry_price,
        "exit": exit_price,
        "duration": duration,
        "exit_reason": exit_reason,
    })

    rsi_text = (
        f"{float(rsi):>7.2f}"
        if rsi is not None
        else "    N/A"
    )

    entry_text = (
        f"{float(entry_price):>10.2f}"
        if entry_price is not None
        else "       N/A"
    )

    exit_text = (
        f"{float(exit_price):>10.2f}"
        if exit_price is not None
        else "       N/A"
    )

    duration_text = (
        f"{duration:>7.1f}"
        if duration is not None
        else "    N/A"
    )

    print(
        f"{i:>2}. "
        f"{side:<5} | "
        f"{result:<5} | "
        f"RSI={rsi_text} | "
        f"HOUR={hour:02d} | "
        f"PROFIT={profit:>10.4f} | "
        f"DURATION={duration_text}m | "
        f"ENTRY={entry_text} | "
        f"EXIT={exit_text} | "
        f"EXIT_REASON={exit_reason}"
    )


print()
print("=" * 125)
print("=== SORTED BY PROFIT ===")
print("=" * 125)

for row in sorted(rows, key=lambda x: x["profit"], reverse=True):

    rsi = (
        f"{float(row['rsi']):.2f}"
        if row["rsi"] is not None
        else "N/A"
    )

    duration = (
        f"{row['duration']:.1f}m"
        if row["duration"] is not None
        else "N/A"
    )

    print(
        f"{row['number']:>2}. "
        f"{row['side']:<5} | "
        f"{row['result']:<5} | "
        f"RSI={rsi:<6} | "
        f"HOUR={row['hour']:02d} | "
        f"PROFIT={row['profit']:>10.4f} | "
        f"DURATION={duration:<8} | "
        f"EXIT={row['exit_reason']}"
    )


print()
print("=" * 125)
print("=== BUY vs SELL SUMMARY ===")
print("=" * 125)

for side in ("BUY", "SELL"):

    side_rows = [
        row for row in rows
        if row["side"] == side
    ]

    profits = [
        row["profit"]
        for row in side_rows
    ]

    wins = [
        p for p in profits
        if p > 0
    ]

    losses = [
        p for p in profits
        if p < 0
    ]

    total_profit = sum(profits)

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    pf = (
        gross_profit / gross_loss
        if gross_loss > 0
        else float("inf")
    )

    expectancy = (
        total_profit / len(profits)
        if profits
        else 0.0
    )

    print(
        f"{side:<5} | "
        f"TRADES={len(profits):>2} | "
        f"WINS={len(wins):>2} | "
        f"LOSSES={len(losses):>2} | "
        f"PROFIT={total_profit:>10.4f} | "
        f"PF={pf:>7.4f} | "
        f"EXPECTANCY={expectancy:>8.4f}"
    )


print()
print("=" * 125)
print("=== END ===")
print("=" * 125)
