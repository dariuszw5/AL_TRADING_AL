from pathlib import Path

from src.data.data_provider import DataProvider
from src.backtest.backtest_runner import BacktestRunner


BUY_RSI = 33.8
SELL_RSI = 68.5
FEE = 0.0004

HORIZONS = [60, 120, 180, 240]

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


def pct(value):
    return value * 100.0


for name, path in DATASETS:
    print()
    print("=" * 125)
    print(f"{name} | SELL 240-MINUTE PRICE PATH")
    print("=" * 125)
    print(
        f"BUY={BUY_RSI} | SELL={SELL_RSI} | "
        f"TIME=241 | RSI=classic | FEE={FEE}"
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

    highs = [
        float(value(c, "high"))
        for c in candles
    ]

    lows = [
        float(value(c, "low"))
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
        f"{'#':>3} | {'ENTRY':>9} | "
        f"{'H60':>8} | {'H120':>8} | {'H180':>8} | {'H240':>8} | "
        f"{'MFE':>8} | {'MAE':>8} | {'FINAL':>9}"
    )
    print("-" * 125)

    sell_count = 0

    for number, trade in enumerate(trades, 1):
        if trade.get("side") != "SELL":
            continue

        sell_count += 1

        entry_ts = trade.get("entry_timestamp")
        entry_index = timestamp_to_index.get(entry_ts)

        if entry_index is None:
            print(
                f"{number:3d} | BRAK ENTRY INDEX"
            )
            continue

        entry_price = float(
            trade["entry_price"]
        )

        horizon_results = {}

        for horizon in HORIZONS:
            target_index = entry_index + horizon

            if target_index >= len(closes):
                horizon_results[horizon] = None
                continue

            close_price = closes[target_index]

            # SELL: profit percentage = entry - exit
            move = (
                entry_price - close_price
            ) / entry_price

            horizon_results[horizon] = move

        # Use all candles available after entry, up to 240 minutes.
        end_index = min(
            entry_index + 240,
            len(candles) - 1
        )

        path_highs = highs[
            entry_index + 1:end_index + 1
        ]

        path_lows = lows[
            entry_index + 1:end_index + 1
        ]

        if path_lows:
            lowest_price = min(path_lows)

            # Favorable excursion for SELL.
            mfe = (
                entry_price - lowest_price
            ) / entry_price
        else:
            mfe = 0.0

        if path_highs:
            highest_price = max(path_highs)

            # Adverse excursion for SELL.
            mae = (
                highest_price - entry_price
            ) / entry_price
        else:
            mae = 0.0

        final_move = horizon_results.get(240)

        if final_move is None:
            final_move = (
                entry_price - closes[end_index]
            ) / entry_price

        def fmt_move(move):
            if move is None:
                return "   N/A  "
            return f"{pct(move):+7.3f}%"

        print(
            f"{number:3d} | "
            f"{entry_price:9.2f} | "
            f"{fmt_move(horizon_results[60])} | "
            f"{fmt_move(horizon_results[120])} | "
            f"{fmt_move(horizon_results[180])} | "
            f"{fmt_move(horizon_results[240])} | "
            f"{pct(mfe):+7.3f}% | "
            f"{pct(mae):+7.3f}% | "
            f"{float(trade['profit']):+9.4f}"
        )

    print()
    print("-" * 125)
    print(f"SELL trades analysed: {sell_count}")
    print()

    # Druga, bardziej czytelna sekcja:
    # szczegółowa ścieżka każdego SELL-a.
    print("DETAILED SELL PATH")
    print("-" * 125)

    for number, trade in enumerate(trades, 1):
        if trade.get("side") != "SELL":
            continue

        entry_ts = trade.get("entry_timestamp")
        entry_index = timestamp_to_index.get(entry_ts)

        if entry_index is None:
            continue

        entry_price = float(
            trade["entry_price"]
        )

        print()
        print(
            f"SELL #{number} | "
            f"ENTRY={entry_price:.2f} | "
            f"FINAL PROFIT={float(trade['profit']):+.4f} | "
            f"EXIT={trade.get('exit_reason', 'N/A')}"
        )

        for horizon in HORIZONS:
            target_index = entry_index + horizon

            if target_index >= len(closes):
                continue

            close_price = closes[target_index]

            move = (
                entry_price - close_price
            ) / entry_price

            print(
                f"  +{horizon:3d} min: "
                f"close={close_price:9.2f} | "
                f"SELL move={pct(move):+7.3f}%"
            )

        end_index = min(
            entry_index + 240,
            len(candles) - 1
        )

        path_highs = highs[
            entry_index + 1:end_index + 1
        ]

        path_lows = lows[
            entry_index + 1:end_index + 1
        ]

        if path_lows:
            lowest_price = min(path_lows)
            mfe = (
                entry_price - lowest_price
            ) / entry_price
        else:
            lowest_price = entry_price
            mfe = 0.0

        if path_highs:
            highest_price = max(path_highs)
            mae = (
                highest_price - entry_price
            ) / entry_price
        else:
            highest_price = entry_price
            mae = 0.0

        print(
            f"  MFE: lowest={lowest_price:.2f} "
            f"({pct(mfe):+.3f}%)"
        )

        print(
            f"  MAE: highest={highest_price:.2f} "
            f"({pct(mae):+.3f}%)"
        )

print()
print("=" * 125)
print("KONIEC ANALIZY SELL PRICE PATH")
print("=" * 125)
