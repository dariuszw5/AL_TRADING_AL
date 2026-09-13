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


def signal_at(
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


def find_unique_rejected_sell_events(
    candles,
    sma_values,
    ema_values,
    rsi_values,
):
    events = []

    previous_low_signal = False

    for index in range(len(candles)):

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

        current_low_sell = signal_low == "SELL"

        # Tylko pierwsza świeca nowego epizodu SELL=69.
        new_sell_episode = (
            current_low_sell
            and not previous_low_signal
        )

        if new_sell_episode and signal_high != "SELL":

            if index + HORIZON < len(candles):

                entry_price = float(
                    candles[index]["close"]
                )

                future_price = float(
                    candles[index + HORIZON]["close"]
                )

                # PRAWIDŁOWE kierunki:
                short_profit = entry_price - future_price
                long_profit = future_price - entry_price

                if short_profit > 0:
                    classification = "BAD_FILTER"
                elif short_profit < 0:
                    classification = "GOOD_FILTER"
                else:
                    classification = "NEUTRAL"

                events.append({
                    "index": index,
                    "rsi": rsi_value,
                    "diff": diff,
                    "entry": entry_price,
                    "future": future_price,
                    "short_profit": short_profit,
                    "long_profit": long_profit,
                    "classification": classification,
                })

        previous_low_signal = current_low_sell

    return events


def print_events(dataset_name, events):

    print()
    print("=" * 125)
    print(
        f"{dataset_name} | UNIQUE REJECTED SELL EPISODES | "
        f"69 -> 77"
    )
    print("=" * 125)

    print()
    print(
        "INDEX | RSI      | EMA-SMA    | ENTRY      | "
        "+240 PRICE | SHORT P/L | LONG P/L | CLASS"
    )
    print("-" * 105)

    for event in events:

        print(
            f"{event['index']:5d} | "
            f"{event['rsi']:8.4f} | "
            f"{event['diff']:10.4f} | "
            f"{event['entry']:10.2f} | "
            f"{event['future']:10.2f} | "
            f"{event['short_profit']:+10.2f} | "
            f"{event['long_profit']:+9.2f} | "
            f"{event['classification']}"
        )

    good = sum(
        1 for e in events
        if e["classification"] == "GOOD_FILTER"
    )

    bad = sum(
        1 for e in events
        if e["classification"] == "BAD_FILTER"
    )

    neutral = sum(
        1 for e in events
        if e["classification"] == "NEUTRAL"
    )

    total_short = sum(
        e["short_profit"] for e in events
    )

    total_long = sum(
        e["long_profit"] for e in events
    )

    print()
    print(f"UNIQUE REJECTED SELL EPISODES: {len(events)}")
    print(f"GOOD FILTER  (SHORT stratny):  {good}")
    print(f"BAD FILTER   (SHORT zyskowny): {bad}")
    print(f"NEUTRAL:                       {neutral}")

    print()
    print(
        f"SUM HYPOTHETICAL SHORT P/L: {total_short:+.2f}"
    )
    print(
        f"SUM HYPOTHETICAL LONG P/L:  {total_long:+.2f}"
    )


def main():

    for dataset_name, path in DATASETS.items():

        candles = load_candles(path)

        sma_values, ema_values, rsi_values = (
            get_indicators(candles)
        )

        events = find_unique_rejected_sell_events(
            candles,
            sma_values,
            ema_values,
            rsi_values,
        )

        print_events(
            dataset_name,
            events,
        )


if __name__ == "__main__":
    main()
