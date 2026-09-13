from src.analysis.market_analyzer import MarketAnalyzer
from src.strategy.basic_strategy import BasicStrategy
import json


HORIZONS = [30, 60, 120, 240]

BINS = [
    ("<3", 0.0, 3.0),
    ("3-5", 3.0, 5.0),
    ("5-10", 5.0, 10.0),
    ("10-20", 10.0, 20.0),
    (">20", 20.0, float("inf")),
]


def load_candles(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_result(side, entry, future):
    if side == "BUY":
        return (future - entry) / entry * 100

    return (entry - future) / entry * 100


def calculate_stats(values):
    if not values:
        return None

    wins = [x for x in values if x > 0]
    losses = [x for x in values if x < 0]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    pf = (
        gross_profit / gross_loss
        if gross_loss > 0
        else (float("inf") if gross_profit > 0 else 0.0)
    )

    wr = len(wins) / len(values) * 100
    avg = sum(values) / len(values)

    return {
        "n": len(values),
        "wr": wr,
        "avg": avg,
        "sum": sum(values),
        "pf": pf,
    }


def analyze_dataset(name, path):
    candles = load_candles(path)

    analyzer = MarketAnalyzer(rsi_method="classic")
    strategy = BasicStrategy()

    signals = []

    for i in range(len(candles)):

        class Candle:
            def __init__(self, data):
                self.timestamp = data["timestamp"]
                self.open = float(data["open"])
                self.high = float(data["high"])
                self.low = float(data["low"])
                self.close = float(data["close"])

        history = [
            Candle(x)
            for x in candles[:i + 1]
        ]

        analysis = analyzer.analyze(history)

        sma_values = analysis.get("sma", [])
        ema_values = analysis.get("ema", [])
        rsi_values = analysis.get("rsi", [])

        if not sma_values or not ema_values or not rsi_values:
            continue

        sma = sma_values[-1]
        ema = ema_values[-1]
        rsi = rsi_values[-1]

        signal = strategy.generate_signal(
            sma_value=sma,
            ema_value=ema,
            rsi_value=rsi,
            min_difference=1.0,
            buy_rsi=30.0,
            sell_rsi=70.0,
        )

        if signal not in ("BUY", "SELL"):
            continue

        distance = abs(ema - sma)

        future_returns = {}

        for horizon in HORIZONS:

            future_index = i + horizon

            if future_index >= len(candles):
                continue

            entry = float(candles[i]["close"])
            future = float(candles[future_index]["close"])

            future_returns[horizon] = calculate_result(
                signal,
                entry,
                future,
            )

        signals.append(
            {
                "side": signal,
                "distance": distance,
                "rsi": rsi,
                "returns": future_returns,
            }
        )

    print()
    print("=" * 90)
    print(f"{name} - EMA-SMA DISTANCE DIAGNOSTIC")
    print("=" * 90)
    print(f"SYGNAŁÓW: {len(signals)}")
    print()

    for side in ("BUY", "SELL"):

        print()
        print(f"################ {side} ################")
        print()

        side_signals = [
            s for s in signals
            if s["side"] == side
        ]

        for bin_name, low, high in BINS:

            bucket = [
                s for s in side_signals
                if low <= s["distance"] < high
            ]

            print(
                f"--- EMA-SMA {bin_name} "
                f"(N={len(bucket)}) ---"
            )

            if not bucket:
                print("BRAK")
                print()
                continue

            avg_rsi = sum(
                s["rsi"]
                for s in bucket
            ) / len(bucket)

            print(
                f"Średnie RSI: {avg_rsi:.2f}"
            )

            for horizon in HORIZONS:

                values = [
                    s["returns"][horizon]
                    for s in bucket
                    if horizon in s["returns"]
                ]

                stats = calculate_stats(values)

                if stats is None:
                    continue

                print(
                    f"{horizon:>3}m | "
                    f"N={stats['n']:>2} | "
                    f"WR={stats['wr']:>6.2f}% | "
                    f"AVG={stats['avg']:>+8.4f}% | "
                    f"SUM={stats['sum']:>+9.4f}% | "
                    f"PF={stats['pf']:>6.3f}"
                )

            print()


if __name__ == "__main__":

    analyze_dataset(
        "TRAIN",
        "data/backtest/BTCUSDT_1m_5000.json",
    )

    analyze_dataset(
        "VALIDATION",
        "data/backtest/BTCUSDT_1m_validation_5000.json",
    )
