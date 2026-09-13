from src.data.data_provider import DataProvider
from src.analysis.indicators import sma, ema, rsi
from src.strategy.basic_strategy import BasicStrategy

DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALID": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

for name, path in DATASETS.items():
    candles = DataProvider().load_candles(path)
    closes = [c.close for c in candles]

    sv = sma(closes, 20)
    ev = ema(closes, 20)
    rv = rsi(closes, 14)
    strategy = BasicStrategy()

    rows = []

    for i in range(len(candles)):
        if i >= len(sv) or i >= len(ev) or i >= len(rv):
            continue
        if sv[i] is None or ev[i] is None or rv[i] is None:
            continue

        signal = strategy.generate_signal(
            sma_value=sv[i],
            ema_value=ev[i],
            rsi_value=rv[i],
            min_difference=1.0,
            buy_rsi=34.75,
            sell_rsi=70.0,
        )

        if signal != "BUY":
            continue

        br = abs(candles[i].close - candles[i].open) / max(
            candles[i].high - candles[i].low, 1e-12
        )

        r1 = (candles[i+1].close / candles[i].close - 1) * 100 if i+1 < len(candles) else None
        r2 = (candles[i+2].close / candles[i].close - 1) * 100 if i+2 < len(candles) else None

        rows.append((abs(ev[i]-sv[i]), br, r1, r2))

    print(f"\n{name} | RSI 34.75 | N={len(rows)}")

    for j, (diff, br, r1, r2) in enumerate(rows, 1):
        print(
            f"{j}: EMA-SMA={diff:6.2f} | "
            f"B/R={br:.3f} | "
            f"+1m={r1:+.4f}% | "
            f"+2m={r2:+.4f}%"
        )
