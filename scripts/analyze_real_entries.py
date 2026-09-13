from src.analysis.market_analyzer import MarketAnalyzer
from src.strategy.basic_strategy import BasicStrategy


TIME_EXIT = 240
FORWARD_WINDOWS = [30, 60, 120, 240]


def analyze_dataset(name, data_file):
    import json

    with open(data_file, "r", encoding="utf-8") as f:
        raw = json.load(f)

    candles = []

    for item in raw:
        if isinstance(item, dict):
            candles.append(
                {
                    "timestamp": item["timestamp"],
                    "open": float(item["open"]),
                    "high": float(item["high"]),
                    "low": float(item["low"]),
                    "close": float(item["close"]),
                }
            )

    analyzer = MarketAnalyzer(rsi_method="classic")
    strategy = BasicStrategy()

    position = None
    trades = []

    for i in range(len(candles)):
        history = candles[:i + 1]

        class Candle:
            def __init__(self, data):
                self.timestamp = data["timestamp"]
                self.open = data["open"]
                self.high = data["high"]
                self.low = data["low"]
                self.close = data["close"]

        candle_objects = [Candle(x) for x in history]

        analysis = analyzer.analyze(candle_objects)

        sma_values = analysis.get("sma", [])
        ema_values = analysis.get("ema", [])
        rsi_values = analysis.get("rsi", [])

        if not sma_values or not ema_values or not rsi_values:
            continue

        sma_value = sma_values[-1]
        ema_value = ema_values[-1]
        rsi_value = rsi_values[-1]

        signal = strategy.generate_signal(
            sma_value=sma_value,
            ema_value=ema_value,
            rsi_value=rsi_value,
            min_difference=1.0,
            buy_rsi=30.0,
            sell_rsi=70.0,
        )

        # Jeżeli pozycja jest otwarta, nie szukamy kolejnego wejścia.
        if position is not None:
            position["bars"] += 1

            if position["bars"] >= TIME_EXIT:
                exit_price = candles[i]["close"]

                if position["side"] == "BUY":
                    result = (
                        (exit_price - position["entry"])
                        / position["entry"]
                        * 100
                    )
                else:
                    result = (
                        (position["entry"] - exit_price)
                        / position["entry"]
                        * 100
                    )

                position["exit_index"] = i
                position["exit"] = exit_price
                position["result"] = result
                position["exit_reason"] = "TIME_EXIT"

                trades.append(position)
                position = None

            continue

        # Otwieramy tylko rzeczywiste wejście.
        if signal not in ("BUY", "SELL"):
            continue

        position = {
            "entry_index": i,
            "entry_timestamp": candles[i]["timestamp"],
            "side": signal,
            "entry": candles[i]["close"],
            "rsi": rsi_value,
            "sma": sma_value,
            "ema": ema_value,
            "difference": abs(ema_value - sma_value),
            "bars": 0,
        }

    # Pozycja pozostała na końcu danych.
    if position is not None:
        exit_price = candles[-1]["close"]

        if position["side"] == "BUY":
            result = (
                (exit_price - position["entry"])
                / position["entry"]
                * 100
            )
        else:
            result = (
                (position["entry"] - exit_price)
                / position["entry"]
                * 100
            )

        position["exit_index"] = len(candles) - 1
        position["exit"] = exit_price
        position["result"] = result
        position["exit_reason"] = "END_OF_DATA"

        trades.append(position)

    # ---------------------------------------------------------
    # Forward returns + MFE / MAE
    # ---------------------------------------------------------

    for trade in trades:
        entry_index = trade["entry_index"]
        entry = trade["entry"]
        side = trade["side"]

        for minutes in FORWARD_WINDOWS:
            future_index = entry_index + minutes

            if future_index >= len(candles):
                trade[f"ret_{minutes}"] = None
                continue

            future_close = candles[future_index]["close"]

            if side == "BUY":
                ret = (future_close - entry) / entry * 100
            else:
                ret = (entry - future_close) / entry * 100

            trade[f"ret_{minutes}"] = ret

        # MFE / MAE liczone w czasie maksymalnie do TIME_EXIT.
        end_index = min(
            entry_index + TIME_EXIT,
            len(candles) - 1
        )

        max_favorable = 0.0
        max_adverse = 0.0

        for j in range(entry_index + 1, end_index + 1):
            high = candles[j]["high"]
            low = candles[j]["low"]

            if side == "BUY":
                favorable = (high - entry) / entry * 100
                adverse = (low - entry) / entry * 100
            else:
                favorable = (entry - low) / entry * 100
                adverse = (entry - high) / entry * 100

            max_favorable = max(max_favorable, favorable)
            max_adverse = min(max_adverse, adverse)

        trade["mfe"] = max_favorable
        trade["mae"] = max_adverse

    # ---------------------------------------------------------
    # RAPORT
    # ---------------------------------------------------------

    print()
    print("=" * 110)
    print(name)
    print("=" * 110)

    print(f"RZECZYWISTE WEJŚCIA: {len(trades)}")

    if not trades:
        print("Brak transakcji.")
        return

    print()
    print(
        f"{'#':>2} "
        f"{'SIDE':>4} "
        f"{'RSI':>6} "
        f"{'EMA-SMA':>10} "
        f"{'RESULT':>9} "
        f"{'MFE':>8} "
        f"{'MAE':>8} "
        f"{'30m':>8} "
        f"{'60m':>8} "
        f"{'120m':>8} "
        f"{'240m':>8}"
    )

    print("-" * 110)

    for n, trade in enumerate(trades, start=1):
        def fmt(value):
            if value is None:
                return "---"
            return f"{value:+.3f}"

        print(
            f"{n:>2} "
            f"{trade['side']:>4} "
            f"{trade['rsi']:>6.2f} "
            f"{trade['ema'] - trade['sma']:>+10.2f} "
            f"{trade['result']:>+9.3f} "
            f"{trade['mfe']:>+8.3f} "
            f"{trade['mae']:>+8.3f} "
            f"{fmt(trade['ret_30']):>8} "
            f"{fmt(trade['ret_60']):>8} "
            f"{fmt(trade['ret_120']):>8} "
            f"{fmt(trade['ret_240']):>8}"
        )

    print()
    print("--- PODSUMOWANIE ---")

    for side in ("BUY", "SELL"):
        subset = [t for t in trades if t["side"] == side]

        if not subset:
            continue

        results = [t["result"] for t in subset]

        wins = [x for x in results if x > 0]
        losses = [x for x in results if x < 0]

        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))

        if gross_loss == 0:
            pf = float("inf") if gross_profit > 0 else 0.0
        else:
            pf = gross_profit / gross_loss

        win_rate = len(wins) / len(results) * 100
        avg = sum(results) / len(results)

        print(
            f"{side:>4} | "
            f"N={len(results):>2} | "
            f"WR={win_rate:>6.2f}% | "
            f"AVG={avg:+.4f}% | "
            f"PF={pf:.3f} | "
            f"SUM={sum(results):+.4f}%"
        )

    print()
    print("--- MFE / MAE ---")

    mfe_values = [t["mfe"] for t in trades]
    mae_values = [t["mae"] for t in trades]

    print(f"Średnie MFE: {sum(mfe_values) / len(mfe_values):+.4f}%")
    print(f"Średnie MAE: {sum(mae_values) / len(mae_values):+.4f}%")
    print(f"Najlepsze MFE: {max(mfe_values):+.4f}%")
    print(f"Najgorsze MAE: {min(mae_values):+.4f}%")

    print()
    print("--- EXIT ---")

    for reason in ("TIME_EXIT", "END_OF_DATA"):
        count = sum(
            1 for t in trades
            if t["exit_reason"] == reason
        )
        if count:
            print(f"{reason}: {count}")


if __name__ == "__main__":
    analyze_dataset(
        "TRAIN",
        "data/backtest/BTCUSDT_1m_5000.json"
    )

    analyze_dataset(
        "VALIDATION",
        "data/backtest/BTCUSDT_1m_validation_5000.json"
    )
