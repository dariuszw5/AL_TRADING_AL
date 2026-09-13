import json

from src.analysis.indicators import sma, ema, rsi


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

BUY_RSI = 35.50
SELL_LOW = 69.0
SELL_HIGH = 77.0
MIN_DIFFERENCE = 1.0
HORIZON = 240


def load_candles(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_indicators(candles):
    closes = [float(c["close"]) for c in candles]

    return (
        sma(closes, 20),
        ema(closes, 20),
        rsi(closes, 14),
    )


def at(values, index, offset):
    pos = index - offset

    if pos < 0 or pos >= len(values):
        return None

    return values[pos]


def signal_at(index, sma_values, ema_values, rsi_values, sell_rsi):
    sma_value = at(sma_values, index, 19)
    ema_value = at(ema_values, index, 19)
    rsi_value = at(rsi_values, index, 14)

    if (
        sma_value is None
        or ema_value is None
        or rsi_value is None
    ):
        return "HOLD", None, None

    difference = abs(ema_value - sma_value)
    ema_minus_sma = ema_value - sma_value

    if difference < MIN_DIFFERENCE:
        return "HOLD", rsi_value, ema_minus_sma

    if ema_value > sma_value and rsi_value < BUY_RSI:
        return "BUY", rsi_value, ema_minus_sma

    if ema_value < sma_value and rsi_value > sell_rsi:
        return "SELL", rsi_value, ema_minus_sma

    return "HOLD", rsi_value, ema_minus_sma


def main():

    for dataset_name, path in DATASETS.items():

        candles = load_candles(path)

        sma_values, ema_values, rsi_values = get_indicators(candles)

        print()
        print("=" * 125)
        print(
            f"{dataset_name} | REJECTED SHORT QUALITY | "
            f"SELL {SELL_LOW:.2f} vs SELL {SELL_HIGH:.2f}"
        )
        print("=" * 125)

        print()
        print(
            "INDEX | RSI      | EMA-SMA    | ENTRY    | "
            "PRICE      | +240 PRICE | SHORT P/L | LONG P/L"
        )
        print("-" * 105)

        count = 0

        for index in range(len(candles) - HORIZON):

            signal_low, rsi_value, diff = signal_at(
                index,
                sma_values,
                ema_values,
                rsi_values,
                SELL_LOW,
            )

            signal_high, _, _ = signal_at(
                index,
                sma_values,
                ema_values,
                rsi_values,
                SELL_HIGH,
            )

            if signal_low != "SELL" or signal_high == "SELL":
                continue

            entry_price = float(candles[index]["close"])
            future_price = float(
                candles[index + HORIZON]["close"]
            )

            short_profit = future_price - entry_price
            long_profit = entry_price - future_price

            print(
                f"{index:5d} | "
                f"{rsi_value:8.4f} | "
                f"{diff:10.4f} | "
                f"69=SELL 77=HOLD | "
                f"{entry_price:10.2f} | "
                f"{future_price:10.2f} | "
                f"{short_profit:+10.2f} | "
                f"{long_profit:+9.2f}"
            )

            count += 1

        print()
        print(
            f"REJECTED SELL SIGNALS: {count}"
        )


if __name__ == "__main__":
    main()
