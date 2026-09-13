from src.data.data_provider import DataProvider
from src.analysis.indicators import sma, ema, rsi


TRAIN = "data/backtest/BTCUSDT_1m_5000.json"
VALIDATION = "data/backtest/BTCUSDT_1m_validation_5000.json"

BUY_RSI = 30.0
SELL_RSI = 70.0
MIN_DIFFERENCE = 1.0

LOOKBACKS = [5, 15, 30, 60, 120]
HORIZONS = [30, 60, 120, 240]


def load_candles(path):
    provider = DataProvider()
    return provider.load_candles(path)


def forward_return(entry_price, exit_price, side):
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
        print("N= 0")
        return

    wins = sum(1 for x in results if x > 0)
    total = len(results)
    avg = sum(results) / total
    total_profit = sum(results)
    pf = calculate_pf(results)

    print(
        f"N={total:2d} | "
        f"WR={wins / total * 100:6.2f}% | "
        f"AVG={avg:+8.4f}% | "
        f"SUM={total_profit:+9.4f}% | "
        f"PF={pf:6.3f}"
    )


def regime_name(value):
    if value < -0.50:
        return "STRONG_DOWN"

    if value < -0.20:
        return "DOWN"

    if value <= 0.20:
        return "FLAT"

    if value <= 0.50:
        return "UP"

    return "STRONG_UP"


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

        regime_data = {}

        for lookback in LOOKBACKS:
            if i < lookback:
                continue

            old_price = closes[i - lookback]
            current_price = closes[i]

            movement = (
                (current_price - old_price)
                / old_price
            ) * 100.0

            regime_data[lookback] = {
                "movement": movement,
                "regime": regime_name(movement),
            }

        signals.append(
            {
                "index": i,
                "side": signal,
                "regime": regime_data,
            }
        )

    return signals


def analyze_dataset(path, name):
    candles = load_candles(path)
    closes = [c.close for c in candles]

    signals = generate_signals(candles)

    print()
    print("=" * 110)
    print(name)
    print("=" * 110)

    print(f"Total signals: {len(signals)}")

    buy_count = sum(
        1 for x in signals
        if x["side"] == "BUY"
    )

    sell_count = sum(
        1 for x in signals
        if x["side"] == "SELL"
    )

    print(f"BUY:  {buy_count}")
    print(f"SELL: {sell_count}")

    for lookback in LOOKBACKS:

        print()
        print("#" * 110)
        print(f"LOOKBACK {lookback}m")
        print("#" * 110)

        for side in ("BUY", "SELL"):

            print()
            print("=" * 110)
            print(f"{side}")
            print("=" * 110)

            side_signals = [
                x for x in signals
                if x["side"] == side
                and lookback in x["regime"]
            ]

            regimes = [
                "STRONG_DOWN",
                "DOWN",
                "FLAT",
                "UP",
                "STRONG_UP",
            ]

            for regime in regimes:

                selected = [
                    x for x in side_signals
                    if x["regime"][lookback]["regime"] == regime
                ]

                print()
                print(f"REGIME: {regime} | SIGNALS={len(selected)}")

                for horizon in HORIZONS:

                    results = []

                    for signal in selected:

                        index = signal["index"]
                        exit_index = index + horizon

                        if exit_index >= len(candles):
                            continue

                        entry_price = closes[index]
                        exit_price = closes[exit_index]

                        result = forward_return(
                            entry_price,
                            exit_price,
                            side,
                        )

                        results.append(result)

                    print(
                        f"  {horizon:3d}m | ",
                        end=""
                    )

                    print_result(results)


def main():
    analyze_dataset(
        TRAIN,
        "TRAIN",
    )

    analyze_dataset(
        VALIDATION,
        "VALIDATION",
    )

    print()
    print("=" * 110)
    print("END")
    print("=" * 110)


if __name__ == "__main__":
    main()
