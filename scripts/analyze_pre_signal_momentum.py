from src.data.data_provider import DataProvider
from src.analysis.market_analyzer import MarketAnalyzer


DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALIDATION": "data/backtest/BTCUSDT_1m_validation_5000.json",
}

BUY_RSI = 30.0
SELL_RSI = 70.0
MIN_DIFFERENCE = 1.0

HORIZONS = [30, 60, 120, 240]
LOOKBACKS = [5, 15, 30, 60]


def load_candles(path):
    provider = DataProvider()
    return provider.load_candles(path)


def previous_return(candles, index, lookback):
    if index < lookback:
        return None

    start = candles[index - lookback].close
    current = candles[index].close

    if start == 0:
        return None

    return ((current - start) / start) * 100.0


def forward_return(candles, index, horizon, side):
    target = index + horizon

    if target >= len(candles):
        return None

    entry = candles[index].close
    future = candles[target].close

    if entry == 0:
        return None

    if side == "BUY":
        return ((future - entry) / entry) * 100.0

    return ((entry - future) / entry) * 100.0


def build_signal(candles, index, analyzer):
    if index < 20:
        return "HOLD"

    analysis = analyzer.analyze(candles[:index + 1])

    sma_values = analysis.get("sma", [])
    ema_values = analysis.get("ema", [])
    rsi_values = analysis.get("rsi", [])

    if not sma_values or not ema_values or not rsi_values:
        return "HOLD"

    sma = sma_values[-1]
    ema = ema_values[-1]
    rsi = rsi_values[-1]

    if abs(ema - sma) < MIN_DIFFERENCE:
        return "HOLD"

    if ema > sma and rsi < BUY_RSI:
        return "BUY"

    if ema < sma and rsi > SELL_RSI:
        return "SELL"

    return "HOLD"


def classify_momentum(value):
    if value < -0.50:
        return "STRONG_DOWN"

    if value < -0.20:
        return "MODERATE_DOWN"

    if value <= 0.20:
        return "FLAT"

    if value <= 0.50:
        return "MODERATE_UP"

    return "STRONG_UP"


def stats(rows, horizon):
    values = [
        row["returns"][horizon]
        for row in rows
        if row["returns"].get(horizon) is not None
    ]

    if not values:
        return None

    wins = [x for x in values if x > 0]
    losses = [x for x in values if x < 0]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    if gross_loss == 0:
        pf = float("inf") if gross_profit > 0 else 0.0
    else:
        pf = gross_profit / gross_loss

    return {
        "n": len(values),
        "wr": len(wins) / len(values) * 100.0,
        "avg": sum(values) / len(values),
        "sum": sum(values),
        "pf": pf,
    }


def print_stats(rows):
    for horizon in HORIZONS:
        result = stats(rows, horizon)

        if result is None:
            continue

        pf = (
            "INF"
            if result["pf"] == float("inf")
            else f"{result['pf']:.3f}"
        )

        print(
            f"  {horizon:>3}m | "
            f"N={result['n']:>2} | "
            f"WR={result['wr']:>6.2f}% | "
            f"AVG={result['avg']:>+8.4f}% | "
            f"SUM={result['sum']:>+9.4f}% | "
            f"PF={pf:>6}"
        )


def analyze_dataset(name, path):
    print("\n" + "=" * 90)
    print(name)
    print("=" * 90)

    candles = load_candles(path)
    analyzer = MarketAnalyzer(rsi_method="classic")

    rows = []

    for index in range(60, len(candles)):
        signal = build_signal(candles, index, analyzer)

        if signal not in ("BUY", "SELL"):
            continue

        momentum = {}

        valid = True

        for lookback in LOOKBACKS:
            value = previous_return(candles, index, lookback)

            if value is None:
                valid = False
                break

            momentum[lookback] = value

        if not valid:
            continue

        returns = {
            horizon: forward_return(
                candles,
                index,
                horizon,
                signal,
            )
            for horizon in HORIZONS
        }

        rows.append({
            "signal": signal,
            "momentum": momentum,
            "returns": returns,
        })

    print(f"Sygnały: {len(rows)}")

    for side in ("BUY", "SELL"):
        side_rows = [
            row for row in rows
            if row["signal"] == side
        ]

        print("\n" + "-" * 90)
        print(f"{side} | N={len(side_rows)}")
        print("-" * 90)

        for lookback in LOOKBACKS:
            print(f"\n### MOMENTUM {lookback}m")

            buckets = {
                "STRONG_DOWN": [],
                "MODERATE_DOWN": [],
                "FLAT": [],
                "MODERATE_UP": [],
                "STRONG_UP": [],
            }

            for row in side_rows:
                value = row["momentum"][lookback]
                bucket = classify_momentum(value)
                buckets[bucket].append(row)

            for bucket_name, bucket_rows in buckets.items():
                print(f"\n{bucket_name}")
                print_stats(bucket_rows)


def main():
    print("=" * 90)
    print("PRE-SIGNAL MOMENTUM / REGIME DIAGNOSTIC")
    print("=" * 90)

    for name, path in DATASETS.items():
        analyze_dataset(name, path)

    print("\n" + "=" * 90)
    print("KONIEC")
    print("=" * 90)


if __name__ == "__main__":
    main()
