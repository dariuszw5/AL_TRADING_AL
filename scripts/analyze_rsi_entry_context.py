from src.data.data_provider import DataProvider
from src.analysis.indicators import sma, ema, rsi


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
}

CASES = {
    "TRAIN": [
        1787488620000,  # BUY 77065.32
    ],
    "VALIDATION": [
        1787609940000,  # BUY 78860.01
        1787648880000,  # BUY 79758.07
        1787610000000,  # BUY 78832.00
        1787649060000,  # BUY 79759.17
    ],
}


def find_index_by_timestamp(candles, timestamp):
    for i, candle in enumerate(candles):
        if candle.timestamp == timestamp:
            return i
    return None


def print_case(candles, sma_values, ema_values, rsi_values, timestamp):
    index = find_index_by_timestamp(candles, timestamp)

    if index is None:
        print(f"TS={timestamp} -> NOT FOUND")
        return

    print()
    print("=" * 125)
    print(f"TIMESTAMP={timestamp} | INDEX={index}")
    print("=" * 125)

    start = max(0, index - 5)
    end = min(len(candles), index + 6)

    for i in range(start, end):
        candle = candles[i]

        sma_value = sma_values[i] if i < len(sma_values) else None
        ema_value = ema_values[i] if i < len(ema_values) else None
        rsi_value = rsi_values[i] if i < len(rsi_values) else None

        difference = None
        if sma_value is not None and ema_value is not None:
            difference = abs(ema_value - sma_value)

        buy_ok = (
            ema_value is not None
            and sma_value is not None
            and rsi_value is not None
            and ema_value > sma_value
            and rsi_value < 35.50
            and difference >= 1.0
        )

        marker = "<-- TARGET" if i == index else ""

        print(
            f"INDEX={i:4d} | "
            f"TS={candle.timestamp} | "
            f"CLOSE={candle.close:10.2f} | "
            f"SMA={sma_value if sma_value is not None else None!s:>12} | "
            f"EMA={ema_value if ema_value is not None else None!s:>12} | "
            f"EMA-SMA={difference if difference is not None else None!s:>10} | "
            f"RSI={rsi_value if rsi_value is not None else None!s:>10} | "
            f"BUY@35.50={str(buy_ok):5s} "
            f"{marker}"
        )


def main():
    provider = DataProvider()

    for dataset_name, timestamps in CASES.items():
        print()
        print("#" * 125)
        print(dataset_name)
        print("#" * 125)

        candles = provider.load_candles(DATASETS[dataset_name])
        closes = [candle.close for candle in candles]

        sma_values = sma(closes, 20)
        ema_values = ema(closes, 20)
        rsi_values = rsi(closes, 14)

        for timestamp in timestamps:
            print_case(
                candles,
                sma_values,
                ema_values,
                rsi_values,
                timestamp
            )


if __name__ == "__main__":
    main()
