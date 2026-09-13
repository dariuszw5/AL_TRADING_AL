from src.data.data_provider import DataProvider
from src.analysis.indicators import sma, ema, rsi
from src.strategy.basic_strategy import BasicStrategy


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


def get_buy_signals(data, buy_rsi):
    strategy = BasicStrategy()
    signals = {}

    for i in range(len(data)):
        if i < 20:
            continue

        closes = [c.close for c in data[:i + 1]]

        sma_values = sma(closes, 20)
        ema_values = ema(closes, 20)
        rsi_values = rsi(closes, 14)

        if not sma_values or not ema_values or not rsi_values:
            continue

        sma_value = sma_values[-1]
        ema_value = ema_values[-1]
        rsi_value = rsi_values[-1]

        signal = strategy.generate_signal(
            rsi_value=rsi_value,
            ema_value=ema_value,
            sma_value=sma_value,
            buy_rsi=buy_rsi,
            sell_rsi=70.0,
            min_difference=1.0,
        )

        if signal == "BUY":
            candle = data[i]

            candle_range = candle.high - candle.low

            body_ratio = (
                abs(candle.close - candle.open) / candle_range
                if candle_range != 0
                else 0.0
            )

            signals[candle.timestamp] = {
                "index": i,
                "timestamp": candle.timestamp,
                "rsi": rsi_value,
                "ema_sma": abs(ema_value - sma_value),
                "body_ratio": body_ratio,
                "entry": candle.close,
            }

    return signals


def main():
    provider = DataProvider()

    for name, path in DATASETS.items():

        print()
        print("=" * 90)
        print(f"{name} | NEW BUY: RSI 34.50 -> 34.75")
        print("=" * 90)

        data = provider.load_candles(path)

        signals_3450 = get_buy_signals(data, 34.50)
        signals_3475 = get_buy_signals(data, 34.75)

        new_timestamps = sorted(
            set(signals_3475) - set(signals_3450)
        )

        print(f"NEW SIGNALS: {len(new_timestamps)}")
        print()

        for timestamp in new_timestamps:
            s = signals_3475[timestamp]
            i = s["index"]

            ret1 = None
            ret2 = None

            if i + 1 < len(data):
                ret1 = (
                    (data[i + 1].close - s["entry"])
                    / s["entry"]
                    * 100
                )

            if i + 2 < len(data):
                ret2 = (
                    (data[i + 2].close - s["entry"])
                    / s["entry"]
                    * 100
                )

            print(
                f"INDEX={i:4d} | "
                f"TS={timestamp} | "
                f"RSI={s['rsi']:6.2f} | "
                f"EMA-SMA={s['ema_sma']:7.2f} | "
                f"B/R={s['body_ratio']:.3f} | "
                f"ENTRY={s['entry']:.2f} | "
                f"+1m={ret1:+.4f}% | "
                f"+2m={ret2:+.4f}%"
            )


if __name__ == "__main__":
    main()