from src.data.data_provider import DataProvider
from src.analysis.indicators import sma, ema, rsi


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
}

TARGETS = {
    "TRAIN": [
        1787488620000,
    ],
    "VALIDATION": [
        1787609940000,
        1787610000000,
        1787648880000,
        1787649060000,
    ],
}


def find_index(candles, timestamp):
    for i, candle in enumerate(candles):
        if candle.timestamp == timestamp:
            return i
    return None


def get_indicator_values(
    sma_values,
    ema_values,
    rsi_values,
    candle_index
):
    sma_index = candle_index - 19
    ema_index = candle_index - 19
    rsi_index = candle_index - 14

    if sma_index < 0 or ema_index < 0 or rsi_index < 0:
        return None

    if (
        sma_index >= len(sma_values)
        or ema_index >= len(ema_values)
        or rsi_index >= len(rsi_values)
    ):
        return None

    return (
        sma_values[sma_index],
        ema_values[ema_index],
        rsi_values[rsi_index]
    )


def main():
    provider = DataProvider()

    for dataset_name, timestamps in TARGETS.items():

        print()
        print("#" * 140)
        print(dataset_name)
        print("#" * 140)

        candles = provider.load_candles(
            DATASETS[dataset_name]
        )

        closes = [c.close for c in candles]

        sma_values = sma(closes, 20)
        ema_values = ema(closes, 20)
        rsi_values = rsi(closes, 14)

        for target_ts in timestamps:

            entry_index = find_index(
                candles,
                target_ts
            )

            if entry_index is None:
                print(
                    f"TARGET TS={target_ts} NOT FOUND"
                )
                continue

            print()
            print("=" * 140)
            print(
                f"ENTRY TS={target_ts} | "
                f"ENTRY INDEX={entry_index} | "
                f"ENTRY PRICE={candles[entry_index].close}"
            )
            print("=" * 140)

            start = max(0, entry_index - 20)
            end = min(len(candles), entry_index + 2)

            for i in range(start, end):

                values = get_indicator_values(
                    sma_values=sma_values,
                    ema_values=ema_values,
                    rsi_values=rsi_values,
                    candle_index=i
                )

                if values is None:
                    continue

                sma_value, ema_value, rsi_value = values
                candle = candles[i]

                difference = abs(
                    ema_value - sma_value
                )

                buy_3450 = (
                    ema_value > sma_value
                    and rsi_value < 34.50
                    and difference >= 1.0
                )

                buy_3550 = (
                    ema_value > sma_value
                    and rsi_value < 35.50
                    and difference >= 1.0
                )

                if buy_3450 or buy_3550 or i >= entry_index - 3:

                    print(
                        f"INDEX={i:4d} | "
                        f"TS={candle.timestamp} | "
                        f"CLOSE={candle.close:10.2f} | "
                        f"RSI={rsi_value:8.3f} | "
                        f"EMA-SMA={difference:8.3f} | "
                        f"BUY34.50={str(buy_3450):5s} | "
                        f"BUY35.50={str(buy_3550):5s}"
                    )


if __name__ == "__main__":
    main()
