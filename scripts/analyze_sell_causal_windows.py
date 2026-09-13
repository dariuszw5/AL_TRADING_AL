import json

from src.analysis.indicators import sma, ema, rsi


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

BUY_RSI = 35.50
SELL_A = 69.0
SELL_B = 77.0
MIN_DIFFERENCE = 1.0
WINDOW = 240


def load_candles(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_values(candles):
    closes = [float(c["close"]) for c in candles]

    sma_values = sma(closes, 20)
    ema_values = ema(closes, 20)
    rsi_values = rsi(closes, 14)

    return sma_values, ema_values, rsi_values


def at(values, index, offset):
    pos = index - offset

    if pos < 0 or pos >= len(values):
        return None

    return values[pos]


def get_signal(
    index,
    sma_values,
    ema_values,
    rsi_values,
    sell_rsi,
):
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


def find_first_divergence(
    candles,
    sma_values,
    ema_values,
    rsi_values,
):
    for index in range(len(candles)):

        signal_a, rsi_value, diff = get_signal(
            index,
            sma_values,
            ema_values,
            rsi_values,
            SELL_A,
        )

        signal_b, _, _ = get_signal(
            index,
            sma_values,
            ema_values,
            rsi_values,
            SELL_B,
        )

        if signal_a != signal_b:
            return index, signal_a, signal_b, rsi_value, diff

    return None


def print_window(
    candles,
    sma_values,
    ema_values,
    rsi_values,
    start,
    end,
):
    print()
    print(
        f"WINDOW {start} -> {end}"
    )
    print(
        "INDEX | RSI      | EMA-SMA    | SIGNAL69 | SIGNAL77 | CLOSE"
    )
    print("-" * 75)

    for index in range(start, min(end + 1, len(candles))):

        signal_a, rsi_value, diff = get_signal(
            index,
            sma_values,
            ema_values,
            rsi_values,
            SELL_A,
        )

        signal_b, _, _ = get_signal(
            index,
            sma_values,
            ema_values,
            rsi_values,
            SELL_B,
        )

        if signal_a == "HOLD" and signal_b == "HOLD":
            continue

        close = float(candles[index]["close"])

        print(
            f"{index:5d} | "
            f"{rsi_value:8.4f} | "
            f"{diff:10.4f} | "
            f"{signal_a:^8} | "
            f"{signal_b:^8} | "
            f"{close:.2f}"
        )


def main():

    for dataset_name, path in DATASETS.items():

        candles = load_candles(path)

        sma_values, ema_values, rsi_values = get_values(candles)

        result = find_first_divergence(
            candles,
            sma_values,
            ema_values,
            rsi_values,
        )

        print()
        print("=" * 100)
        print(
            f"{dataset_name} | CAUSAL SELL 69 vs 77 ANALYSIS"
        )
        print("=" * 100)

        if result is None:
            print("NO DIVERGENCE FOUND")
            continue

        index, signal_a, signal_b, rsi_value, diff = result

        print()
        print(
            f"FIRST DIVERGENCE:"
        )
        print(
            f"INDEX={index} | "
            f"RSI={rsi_value:.4f} | "
            f"EMA-SMA={diff:.4f}"
        )
        print(
            f"SELL 69 = {signal_a}"
        )
        print(
            f"SELL 77 = {signal_b}"
        )
        print(
            f"CLOSE={float(candles[index]['close']):.2f}"
        )

        print()

        window_start = max(0, index)
        window_end = min(
            len(candles) - 1,
            index + WINDOW
        )

        print_window(
            candles,
            sma_values,
            ema_values,
            rsi_values,
            window_start,
            window_end,
        )


if __name__ == "__main__":
    main()
