import json

from src.analysis.indicators import sma, ema, rsi


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

TARGET_TIMESTAMPS = {
    1787295360000,
    1787302080000,
}


def load_candles(path):

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    candles = []

    for item in raw:

        if isinstance(item, dict):

            timestamp = item.get("timestamp")
            close = item.get("close")

        else:

            timestamp = item.timestamp
            close = item.close

        candles.append(
            {
                "timestamp": int(timestamp),
                "close": float(close),
            }
        )

    return candles


def main():

    print()
    print("=" * 150)
    print("EXACT SELL THRESHOLD EVENTS")
    print("Searching RSI events responsible for SELL=68.25 vs SELL=68.50")
    print("=" * 150)

    for dataset, path in DATASETS.items():

        candles = load_candles(path)

        closes = [c["close"] for c in candles]

        sma_values = sma(closes, 20)
        ema_values = ema(closes, 20)
        rsi_values = rsi(closes, 14)

        print()
        print()
        print("#" * 150)
        print(f"DATASET: {dataset}")
        print("#" * 150)

        for index, candle in enumerate(candles):

            timestamp = candle["timestamp"]

            sma_index = index - 19
            ema_index = index - 19
            rsi_index = index - 14

            if (
                sma_index < 0
                or ema_index < 0
                or rsi_index < 0
            ):
                continue

            sma_value = sma_values[sma_index]
            ema_value = ema_values[ema_index]
            rsi_value = rsi_values[rsi_index]

            difference = abs(
                ema_value - sma_value
            )

            sell_condition_6825 = (
                ema_value < sma_value
                and rsi_value > 68.25
                and difference >= 1.0
            )

            sell_condition_6850 = (
                ema_value < sma_value
                and rsi_value > 68.50
                and difference >= 1.0
            )

            if sell_condition_6825 and not sell_condition_6850:

                print(
                    f"INDEX={index:4d} "
                    f"TS={timestamp} "
                    f"RSI={rsi_value:8.4f} "
                    f"EMA-SMA={ema_value - sma_value:+9.4f} "
                    f"PRICE={candle['close']:.2f}"
                )

        print()
        print("--- TARGET EVENT DETAILS ---")

        for target_ts in sorted(TARGET_TIMESTAMPS):

            matches = [
                i
                for i, c in enumerate(candles)
                if c["timestamp"] == target_ts
            ]

            if not matches:
                continue

            index = matches[0]

            sma_index = index - 19
            ema_index = index - 19
            rsi_index = index - 14

            if min(sma_index, ema_index, rsi_index) < 0:
                continue

            sma_value = sma_values[sma_index]
            ema_value = ema_values[ema_index]
            rsi_value = rsi_values[rsi_index]

            print()
            print(
                f"TARGET INDEX={index} "
                f"TS={target_ts}"
            )

            print(
                f"RSI       = {rsi_value:.8f}"
            )

            print(
                f"SMA       = {sma_value:.8f}"
            )

            print(
                f"EMA       = {ema_value:.8f}"
            )

            print(
                f"EMA-SMA   = {ema_value - sma_value:+.8f}"
            )

            print(
                f"CLOSE     = {candles[index]['close']:.8f}"
            )

            print(
                f"SELL 68.25 = "
                f"{ema_value < sma_value and rsi_value > 68.25 and abs(ema_value-sma_value) >= 1.0}"
            )

            print(
                f"SELL 68.50 = "
                f"{ema_value < sma_value and rsi_value > 68.50 and abs(ema_value-sma_value) >= 1.0}"
            )

            print()
            print("WINDOW +/- 5 CANDLES")

            start = max(0, index - 5)
            end = min(len(candles), index + 6)

            for j in range(start, end):

                s_idx = j - 19
                e_idx = j - 19
                r_idx = j - 14

                if min(s_idx, e_idx, r_idx) < 0:
                    continue

                s = sma_values[s_idx]
                e = ema_values[e_idx]
                r = rsi_values[r_idx]

                print(
                    f"{j:4d} "
                    f"TS={candles[j]['timestamp']} "
                    f"RSI={r:8.4f} "
                    f"EMA-SMA={e-s:+9.4f} "
                    f"CLOSE={candles[j]['close']:.2f}"
                )

    print()
    print("=" * 150)
    print("END")
    print("=" * 150)


if __name__ == "__main__":
    main()
