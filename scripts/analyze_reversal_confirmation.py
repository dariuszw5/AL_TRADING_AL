from src.data.data_provider import DataProvider
from src.analysis.indicators import sma, ema, rsi


TRAIN = "data/backtest/BTCUSDT_1m_5000.json"
VALIDATION = "data/backtest/BTCUSDT_1m_validation_5000.json"

BUY_RSI = 30.0
SELL_RSI = 70.0
MIN_DIFFERENCE = 1.0

HORIZONS = [30, 60, 120, 240]


def load_candles(path):
    provider = DataProvider()
    return provider.load_candles(path)


def calculate_return(entry_price, exit_price, side):
    if side == "BUY":
        return ((exit_price - entry_price) / entry_price) * 100.0

    return ((entry_price - exit_price) / entry_price) * 100.0


def calculate_pf(results):
    profits = [x for x in results if x > 0]
    losses = [x for x in results if x < 0]

    gross_profit = sum(profits)
    gross_loss = abs(sum(losses))

    if gross_loss == 0:
        if gross_profit > 0:
            return float("inf")
        return 0.0

    return gross_profit / gross_loss


def print_result(results):
    if not results:
        print("   N= 0")
        return

    wins = sum(1 for x in results if x > 0)
    total = len(results)
    avg = sum(results) / total
    total_profit = sum(results)
    pf = calculate_pf(results)

    print(
        f"   N={total:2d} | "
        f"WR={wins / total * 100:6.2f}% | "
        f"AVG={avg:+8.4f}% | "
        f"SUM={total_profit:+9.4f}% | "
        f"PF={pf:6.3f}"
    )


def generate_signals(candles):
    closes = [c.close for c in candles]

    sma_values = sma(closes, 20)
    ema_values = ema(closes, 20)
    rsi_values = rsi(closes, 14)

    signals = []

    sma_start = 19
    ema_start = 19
    rsi_start = 14

    for i in range(len(candles)):
        if i < max(sma_start, ema_start, rsi_start):
            continue

        sma_index = i - sma_start
        ema_index = i - ema_start
        rsi_index = i - rsi_start

        if sma_index >= len(sma_values):
            continue

        if ema_index >= len(ema_values):
            continue

        if rsi_index >= len(rsi_values):
            continue

        sma_value = sma_values[sma_index]
        ema_value = ema_values[ema_index]
        rsi_value = rsi_values[rsi_index]

        if sma_value is None or ema_value is None or rsi_value is None:
            continue

        difference = abs(ema_value - sma_value)

        if difference < MIN_DIFFERENCE:
            continue

        signal = "HOLD"

        if ema_value > sma_value and rsi_value < BUY_RSI:
            signal = "BUY"

        elif ema_value < sma_value and rsi_value > SELL_RSI:
            signal = "SELL"

        if signal not in ("BUY", "SELL"):
            continue

        previous_rsi = rsi_values[rsi_index - 1]

        if i == 0:
            continue

        previous_close = closes[i - 1]

        rsi_turn = (
            (signal == "BUY" and rsi_value > previous_rsi)
            or
            (signal == "SELL" and rsi_value < previous_rsi)
        )

        price_turn = (
            (signal == "BUY" and closes[i] > previous_close)
            or
            (signal == "SELL" and closes[i] < previous_close)
        )

        signals.append(
            {
                "index": i,
                "side": signal,
                "rsi_turn": rsi_turn,
                "price_turn": price_turn,
            }
        )

    return signals


def analyze_variant(candles, signals, variant_name, condition):
    selected = [
        signal for signal in signals
        if condition(signal)
    ]

    print()
    print("-" * 90)
    print(f"{variant_name} | N={len(selected)}")
    print("-" * 90)

    closes = [c.close for c in candles]

    for side in ("BUY", "SELL"):
        side_signals = [
            signal for signal in selected
            if signal["side"] == side
        ]

        print()
        print(f"{side} | N={len(side_signals)}")

        for horizon in HORIZONS:
            results = []

            for signal in side_signals:
                index = signal["index"]
                exit_index = index + horizon

                if exit_index >= len(candles):
                    continue

                entry_price = closes[index]
                exit_price = closes[exit_index]

                result = calculate_return(
                    entry_price,
                    exit_price,
                    side,
                )

                results.append(result)

            print(f"{horizon:4d}m", end="")
            print_result(results)


def analyze_dataset(path, name):
    candles = load_candles(path)
    signals = generate_signals(candles)

    print("=" * 90)
    print(name)
    print("=" * 90)
    print(f"Base signals: {len(signals)}")

    buy_count = sum(
        1 for signal in signals
        if signal["side"] == "BUY"
    )

    sell_count = sum(
        1 for signal in signals
        if signal["side"] == "SELL"
    )

    print(f"BUY: {buy_count}")
    print(f"SELL: {sell_count}")

    variants = {
        "CURRENT": lambda x: True,

        "RSI_TURN": lambda x: (
            x["rsi_turn"]
        ),

        "PRICE_TURN": lambda x: (
            x["price_turn"]
        ),

        "RSI_PRICE_TURN": lambda x: (
            x["rsi_turn"]
            and x["price_turn"]
        ),
    }

    for variant_name, condition in variants.items():
        analyze_variant(
            candles,
            signals,
            variant_name,
            condition,
        )


def main():
    analyze_dataset(
        TRAIN,
        "TRAIN",
    )

    print()

    analyze_dataset(
        VALIDATION,
        "VALIDATION",
    )

    print()
    print("=" * 90)
    print("END")
    print("=" * 90)


if __name__ == "__main__":
    main()
