from src.analysis.market_analyzer import MarketAnalyzer
from src.strategy.basic_strategy import BasicStrategy
import json


HORIZONS = [30, 60, 120, 240]


def load_candles(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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

        history = [Candle(x) for x in candles[:i + 1]]

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

        previous_ema = None
        ema_slope = None

        if len(ema_values) >= 2:
            previous_ema = ema_values[-2]
            ema_slope = ema - previous_ema

        future_returns = {}

        for horizon in HORIZONS:
            future_index = i + horizon

            if future_index >= len(candles):
                continue

            entry = float(candles[i]["close"])
            future = float(candles[future_index]["close"])

            if signal == "BUY":
                result = (future - entry) / entry * 100
            else:
                result = (entry - future) / entry * 100

            future_returns[horizon] = result

        signals.append(
            {
                "index": i,
                "side": signal,
                "rsi": rsi,
                "ema_sma": ema - sma,
                "ema_slope": ema_slope,
                "returns": future_returns,
            }
        )

    print()
    print("=" * 85)
    print(f"{name} - REGIME DIAGNOSTIC")
    print("=" * 85)
    print(f"SYGNAŁÓW: {len(signals)}")
    print()

    for side in ("BUY", "SELL"):

        side_signals = [
            s for s in signals
            if s["side"] == side
        ]

        if not side_signals:
            print(f"{side}: BRAK")
            continue

        print(f"--- {side} ---")
        print(f"Liczba: {len(side_signals)}")

        avg_rsi = sum(
            s["rsi"] for s in side_signals
        ) / len(side_signals)

        avg_ema_sma = sum(
            s["ema_sma"] for s in side_signals
        ) / len(side_signals)

        slopes = [
            s["ema_slope"]
            for s in side_signals
            if s["ema_slope"] is not None
        ]

        avg_slope = (
            sum(slopes) / len(slopes)
            if slopes
            else 0.0
        )

        slope_up = sum(
            1 for x in slopes if x > 0
        )

        slope_down = sum(
            1 for x in slopes if x < 0
        )

        print(f"Średnie RSI:       {avg_rsi:>9.4f}")
        print(f"Średnie EMA-SMA:   {avg_ema_sma:>9.4f}")
        print(f"Średni EMA slope:  {avg_slope:>9.6f}")
        print(
            f"EMA rośnie:        {slope_up:>3} "
            f"({slope_up / len(slopes) * 100:>6.2f}%)"
        )
        print(
            f"EMA spada:         {slope_down:>3} "
            f"({slope_down / len(slopes) * 100:>6.2f}%)"
        )

        for horizon in HORIZONS:

            values = [
                s["returns"][horizon]
                for s in side_signals
                if horizon in s["returns"]
            ]

            if not values:
                continue

            wins = [
                x for x in values
                if x > 0
            ]

            losses = [
                x for x in values
                if x < 0
            ]

            profit = sum(values)

            gross_profit = sum(wins)
            gross_loss = abs(sum(losses))

            pf = (
                gross_profit / gross_loss
                if gross_loss > 0
                else 0.0
            )

            wr = (
                len(wins) / len(values) * 100
                if values
                else 0.0
            )

            avg = sum(values) / len(values)

            print(
                f"{horizon:>3}m | "
                f"N={len(values):>2} | "
                f"WR={wr:>6.2f}% | "
                f"AVG={avg:>+8.4f}% | "
                f"SUM={profit:>+9.4f}% | "
                f"PF={pf:>6.3f}"
            )

        print()

    # -----------------------------------------------------
    # SZCZEGÓŁOWA LISTA SYGNAŁÓW
    # -----------------------------------------------------

    print("--- SZCZEGÓŁY SYGNAŁÓW ---")
    print()

    print(
        f"{'#':>3} "
        f"{'SIDE':>5} "
        f"{'RSI':>7} "
        f"{'EMA-SMA':>10} "
        f"{'EMA SLOPE':>11} "
        f"{'30m':>9} "
        f"{'120m':>9} "
        f"{'240m':>9}"
    )

    print("-" * 85)

    for n, s in enumerate(signals, 1):

        r30 = s["returns"].get(30)
        r120 = s["returns"].get(120)
        r240 = s["returns"].get(240)

        def fmt(value):
            if value is None:
                return "---"
            return f"{value:+.4f}"

        print(
            f"{n:>3} "
            f"{s['side']:>5} "
            f"{s['rsi']:>7.2f} "
            f"{s['ema_sma']:>+10.4f} "
            f"{s['ema_slope']:>+11.6f} "
            f"{fmt(r30):>9} "
            f"{fmt(r120):>9} "
            f"{fmt(r240):>9}"
        )


if __name__ == "__main__":

    analyze_dataset(
        "TRAIN",
        "data/backtest/BTCUSDT_1m_5000.json",
    )

    analyze_dataset(
        "VALIDATION",
        "data/backtest/BTCUSDT_1m_validation_5000.json",
    )
