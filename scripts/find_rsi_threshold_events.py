from src.data.data_provider import DataProvider
from src.analysis.indicators import sma, ema, rsi


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}


SMA_PERIOD = 20
EMA_PERIOD = 20
RSI_PERIOD = 14

MIN_DIFFERENCE = 1.0

LOW_RSI = 34.90
HIGH_RSI = 35.80


def get_indexed_values(values, index, warmup):
    value_index = index - warmup

    if value_index < 0:
        return None

    if value_index >= len(values):
        return None

    return values[value_index]


def main():
    provider = DataProvider()

    for dataset_name, path in DATASETS.items():

        print()
        print("#" * 130)
        print(
            f"{dataset_name} | "
            f"RSI THRESHOLD TRANSITION CANDLES"
        )
        print("#" * 130)

        candles = provider.load_candles(path)

        closes = [
            candle.close
            for candle in candles
        ]

        sma_values = sma(
            closes,
            SMA_PERIOD
        )

        ema_values = ema(
            closes,
            EMA_PERIOD
        )

        rsi_values = rsi(
            closes,
            RSI_PERIOD
        )

        candidates = []

        for index in range(len(candles)):

            sma_value = get_indexed_values(
                sma_values,
                index,
                SMA_PERIOD - 1
            )

            ema_value = get_indexed_values(
                ema_values,
                index,
                EMA_PERIOD - 1
            )

            rsi_value = get_indexed_values(
                rsi_values,
                index,
                RSI_PERIOD
            )

            if (
                sma_value is None
                or ema_value is None
                or rsi_value is None
            ):
                continue

            difference = abs(
                ema_value - sma_value
            )

            if difference < MIN_DIFFERENCE:
                continue

            if ema_value <= sma_value:
                continue

            if not (
                LOW_RSI <= rsi_value <= HIGH_RSI
            ):
                continue

            candidates.append(
                (
                    index,
                    rsi_value,
                    difference,
                    candles[index].close,
                    candles[index].timestamp,
                )
            )

        print()
        print(
            "INDEX    RSI        EMA-SMA       CLOSE"
        )
        print("-" * 80)

        for index, rsi_value, difference, close, timestamp in candidates:

            print(
                f"{index:5d}    "
                f"{rsi_value:8.5f}    "
                f"{difference:10.5f}    "
                f"{close:10.2f}"
            )

        print()
        print(
            f"TOTAL CANDIDATES: {len(candidates)}"
        )

        print()
        print(
            "THRESHOLD CHECK"
        )
        print("-" * 80)

        thresholds = [
            35.00,
            35.05,
            35.10,
            35.15,
            35.20,
            35.25,
            35.30,
            35.35,
            35.40,
            35.45,
            35.50,
            35.55,
            35.60,
            35.65,
            35.70,
            35.75,
        ]

        for threshold in thresholds:

            triggered = [
                item
                for item in candidates
                if item[1] < threshold
            ]

            print(
                f"BUY RSI < {threshold:5.2f} | "
                f"SIGNALS={len(triggered):3d}"
            )


if __name__ == "__main__":
    main()
