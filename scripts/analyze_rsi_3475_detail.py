from src.data.data_provider import DataProvider
from src.analysis.indicators import sma, ema, rsi
from src.strategy.basic_strategy import BasicStrategy


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

THRESHOLD = 34.75
HORIZONS = [1, 2, 3, 4, 5]


def candle_body_ratio(candle):
    candle_range = candle.high - candle.low

    if candle_range <= 0:
        return 0.0

    return abs(candle.close - candle.open) / candle_range


def inspect_dataset(name, path):
    provider = DataProvider()
    candles = provider.load_candles(path)

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

        signal = strategy.generate_signal(
            sma_value=sma_value,
            ema_value=ema_value,
            rsi_value=rsi_value,
            min_difference=1.0,
            buy_rsi=THRESHOLD,
            sell_rsi=70.0,
        )

        if signal == "BUY":
            signals.append({
                "index": i,
                "timestamp": candles[i].timestamp,
                "rsi": rsi_value,
                "difference": abs(ema_value - sma_value),
                "body_ratio": candle_body_ratio(candles[i]),
                "entry": candles[i].close,
            })

    print()
    print("=" * 140)
    print(f"{name} | RSI={THRESHOLD:.2f} | ALL BUY SIGNALS")
    print("=" * 140)

    for item in signals:
        i = item["index"]

        print()
        print(
            f"INDEX={i:4d} | "
            f"TS={item['timestamp']} | "
            f"RSI={item['rsi']:6.2f} | "
            f"EMA-SMA={item['difference']:8.2f} | "
            f"B/R={item['body_ratio']:.3f} | "
            f"ENTRY={item['entry']:.2f}"
        )

        for horizon in HORIZONS:
            future_index = i + horizon

            if future_index >= len(candles):
                continue

            future_price = candles[future_index].close

            result_pct = (
                (future_price - item["entry"])
                / item["entry"]
                * 100.0
            )

            print(
                f"    +{horizon}m: "
                f"{result_pct:+.5f}%"
            )


print("=" * 140)
print("RSI 34.75 SIGNAL DETAIL ANALYSIS")
print("=" * 140)

for name, path in DATASETS.items():
    inspect_dataset(name, path)

print()
print("=" * 140)
print("DETAIL ANALYSIS COMPLETE")
print("=" * 140)
