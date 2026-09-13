from src.data.data_provider import DataProvider
from src.analysis.indicators import sma, ema, rsi
from src.strategy.basic_strategy import BasicStrategy


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

THRESHOLDS = [
    33.50,
    33.75,
    34.00,
    34.25,
    34.50,
    34.75,
    35.00,
    35.25,
    35.50,
    35.75,
    36.00,
    36.25,
    36.50,
]


def candle_body_ratio(candle):
    candle_range = candle.high - candle.low

    if candle_range <= 0:
        return 0.0

    return abs(candle.close - candle.open) / candle_range


def inspect_dataset(name, path):
    print(f"\nLoading {name}: {path}", flush=True)

    provider = DataProvider()
    candles = provider.load_candles(path)

    print(f"{name}: {len(candles)} candles loaded", flush=True)

    closes = [c.close for c in candles]

    sma_values = sma(closes, 20)
    ema_values = ema(closes, 20)
    rsi_values = rsi(closes, 14)

    strategy = BasicStrategy()

    signals = []

    for i in range(len(candles)):
        if i >= len(sma_values):
            continue

        if i >= len(ema_values):
            continue

        if i >= len(rsi_values):
            continue

        sma_value = sma_values[i]
        ema_value = ema_values[i]
        rsi_value = rsi_values[i]

        if sma_value is None or ema_value is None:
            continue

        if rsi_value is None:
            continue

        for threshold in THRESHOLDS:
            signal = strategy.generate_signal(
                sma_value=sma_value,
                ema_value=ema_value,
                rsi_value=rsi_value,
                min_difference=1.0,
                buy_rsi=threshold,
                sell_rsi=70.0,
            )

            if signal != "HOLD":
                signals.append(
                    {
                        "threshold": threshold,
                        "index": i,
                        "timestamp": candles[i].timestamp,
                        "signal": signal,
                        "rsi": rsi_value,
                        "ema": ema_value,
                        "sma": sma_value,
                        "difference": abs(ema_value - sma_value),
                        "body_ratio": candle_body_ratio(candles[i]),
                        "entry": candles[i].close,
                    }
                )

    print()
    print("=" * 120)
    print(f"{name} | INCREMENTAL SIGNAL ANALYSIS")
    print("=" * 120)

    previous_signals = set()

    for threshold in THRESHOLDS:
        current = [
            x for x in signals
            if x["threshold"] == threshold
        ]

        current_set = {
            (x["index"], x["signal"])
            for x in current
        }

        added = current_set - previous_signals

        print(
            f"\nBUY RSI={threshold:.2f} | "
            f"TOTAL SIGNALS={len(current)} | "
            f"NEW SIGNALS={len(added)}"
        )

        if added:
            for index, signal in sorted(added):
                item = next(
                    x for x in current
                    if x["index"] == index
                    and x["signal"] == signal
                )

                print(
                    f"  {signal:4s} | "
                    f"INDEX={index:4d} | "
                    f"TS={item['timestamp']} | "
                    f"RSI={item['rsi']:6.2f} | "
                    f"EMA-SMA={item['difference']:7.2f} | "
                    f"B/R={item['body_ratio']:.3f} | "
                    f"ENTRY={item['entry']:.2f}"
                )

        previous_signals = current_set


print("=" * 120)
print("INCREMENTAL BUY RSI ANALYSIS")
print("=" * 120)

for name, path in DATASETS.items():
    inspect_dataset(name, path)

print()
print("=" * 120)
print("INCREMENTAL ANALYSIS COMPLETE")
print("=" * 120)