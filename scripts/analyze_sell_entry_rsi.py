from pathlib import Path

from src.data.data_provider import DataProvider
from src.analysis.indicators import rsi
from src.backtest.backtest_runner import BacktestRunner


BUY_RSI = 33.8
SELL_RSI = 68.5
FEE = 0.0004


DATASETS = [
    (
        "OOS #1",
        Path("data/backtest/BTCUSDT_1m_forward_5000.json"),
    ),
    (
        "OOS #2",
        Path("data/backtest/BTCUSDT_1m_forward_5000_oos2.json"),
    ),
]


def value(candle, key):
    if isinstance(candle, dict):
        return candle[key]
    return getattr(candle, key)


def calculate_entry_rsi(closes, entry_index):
    if entry_index < 14:
        return None

    values = rsi(
        closes[:entry_index + 1],
        14
    )

    if not values:
        return None

    # rsi() starts at candle index 14.
    rsi_index = entry_index - 14

    if rsi_index < 0 or rsi_index >= len(values):
        return None

    return float(values[rsi_index])


for name, path in DATASETS:
    print()
    print("=" * 115)
    print(f"{name} | SELL ENTRY RSI STRUCTURE")
    print("=" * 115)
    print(
        f"BUY={BUY_RSI} | SELL={SELL_RSI} | "
        f"RSI=classic | FEE={FEE}"
    )
    print()

    provider = DataProvider()
    candles = provider.load_candles(str(path))

    timestamps = [
        value(c, "timestamp")
        for c in candles
    ]

    closes = [
        float(value(c, "close"))
        for c in candles
    ]

    timestamp_to_index = {
        ts: i
        for i, ts in enumerate(timestamps)
    }

    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=100,
        initial_balance=1000.0,
        buy_rsi=BUY_RSI,
        sell_rsi=SELL_RSI,
        min_difference=1.0,
        trading_fee=FEE,
        rsi_method="classic",
        risk_percent=5.0,
        max_daily_loss_percent=10.0,
        risk_reward_ratio=2.0,
        data_source="file",
        data_file=str(path),
    )

    runner.run()
    trades = runner.get_trades()

    print(
        f"{'#':>3} | {'SIDE':<5} | {'INDEX':>5} | "
        f"{'ENTRY RSI':>9} | {'DIST':>8} | "
        f"{'PROFIT':>10} | {'RESULT':<5} | {'EXIT':<12}"
    )
    print("-" * 115)

    sell_rows = []

    for number, trade in enumerate(trades, 1):
        side = trade.get("side")
        entry_ts = trade.get("entry_timestamp")
        profit = float(trade.get("profit", 0.0))
        exit_reason = trade.get("exit_reason", "N/A")

        if side != "SELL":
            continue

        entry_index = timestamp_to_index.get(entry_ts)

        entry_rsi = None

        if entry_index is not None:
            entry_rsi = calculate_entry_rsi(
                closes,
                entry_index
            )

        if entry_rsi is None:
            print(
                f"{number:3d} | "
                f"{side:<5} | "
                f"{str(entry_index):>5} | "
                f"{'N/A':>9} | "
                f"{'N/A':>8} | "
                f"{profit:+10.4f} | "
                f"{'WIN' if profit > 0 else 'LOSS':<5} | "
                f"{exit_reason:<12}"
            )
            continue

        distance = entry_rsi - SELL_RSI
        result = "WIN" if profit > 0 else "LOSS"

        sell_rows.append(
            {
                "number": number,
                "rsi": entry_rsi,
                "distance": distance,
                "profit": profit,
                "exit": exit_reason,
            }
        )

        print(
            f"{number:3d} | "
            f"{side:<5} | "
            f"{entry_index:5d} | "
            f"{entry_rsi:9.3f} | "
            f"{distance:+8.3f} | "
            f"{profit:+10.4f} | "
            f"{result:<5} | "
            f"{exit_reason:<12}"
        )

    print()
    print("-" * 115)
    print("SELL SUMMARY")
    print("-" * 115)

    if not sell_rows:
        print("Brak SELL-i z możliwym do obliczenia RSI.")
        continue

    wins = [
        row for row in sell_rows
        if row["profit"] > 0
    ]

    losses = [
        row for row in sell_rows
        if row["profit"] <= 0
    ]

    rsis = [row["rsi"] for row in sell_rows]
    profits = [row["profit"] for row in sell_rows]

    print(f"SELL trades       : {len(sell_rows)}")
    print(f"SELL wins         : {len(wins)}")
    print(f"SELL losses       : {len(losses)}")
    print(f"SELL profit       : {sum(profits):+.4f}")
    print(f"RSI min           : {min(rsis):.3f}")
    print(f"RSI max           : {max(rsis):.3f}")
    print(f"RSI average       : {sum(rsis) / len(rsis):.3f}")
    print()

    if wins:
        win_rsis = [
            row["rsi"]
            for row in wins
        ]

        print(
            f"WIN  RSI average  : "
            f"{sum(win_rsis) / len(win_rsis):.3f}"
        )

        print(
            f"WIN  RSI range    : "
            f"{min(win_rsis):.3f} -> {max(win_rsis):.3f}"
        )

    if losses:
        loss_rsis = [
            row["rsi"]
            for row in losses
        ]

        print(
            f"LOSS RSI average  : "
            f"{sum(loss_rsis) / len(loss_rsis):.3f}"
        )

        print(
            f"LOSS RSI range    : "
            f"{min(loss_rsis):.3f} -> {max(loss_rsis):.3f}"
        )

    print()
    print("SELL RSI BUCKETS")
    print("-" * 115)

    buckets = [
        ("68.5 - 69.0", 68.5, 69.0),
        ("69.0 - 70.0", 69.0, 70.0),
        ("70.0 - 72.0", 70.0, 72.0),
        ("72.0 - 75.0", 72.0, 75.0),
        ("75.0+", 75.0, float("inf")),
    ]

    for label, low, high in buckets:
        rows = [
            row
            for row in sell_rows
            if low <= row["rsi"] < high
        ]

        if not rows:
            print(
                f"{label:<14} | trades=0"
            )
            continue

        bucket_profit = sum(
            row["profit"]
            for row in rows
        )

        bucket_wins = sum(
            1
            for row in rows
            if row["profit"] > 0
        )

        print(
            f"{label:<14} | "
            f"trades={len(rows):2d} | "
            f"W/L={bucket_wins}/{len(rows)-bucket_wins} | "
            f"profit={bucket_profit:+.4f}"
        )

print()
print("=" * 115)
print("KONIEC DIAGNOSTYKI")
print("=" * 115)
