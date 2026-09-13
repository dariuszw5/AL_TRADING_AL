from src.analysis.market_analyzer import MarketAnalyzer
from src.strategy.basic_strategy import BasicStrategy
import json


TIME_EXIT = 240


def load_candles(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_test(name, path, fresh_only):
    candles = load_candles(path)

    analyzer = MarketAnalyzer(rsi_method="classic")
    strategy = BasicStrategy()

    position = None
    previous_signal = "HOLD"
    trades = []

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

        sma = analysis.get("sma", [])
        ema = analysis.get("ema", [])
        rsi = analysis.get("rsi", [])

        if not sma or not ema or not rsi:
            continue

        signal = strategy.generate_signal(
            sma_value=sma[-1],
            ema_value=ema[-1],
            rsi_value=rsi[-1],
            min_difference=1.0,
            buy_rsi=30.0,
            sell_rsi=70.0,
        )

        if position is not None:
            position["bars"] += 1

            if position["bars"] >= TIME_EXIT:
                exit_price = float(candles[i]["close"])

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

                position["exit"] = exit_price
                position["result"] = result
                trades.append(position)
                position = None

            previous_signal = signal
            continue

        allowed = signal in ("BUY", "SELL")

        if fresh_only:
            allowed = allowed and signal != previous_signal

        if allowed:
            position = {
                "side": signal,
                "entry": float(candles[i]["close"]),
                "entry_index": i,
                "bars": 0,
            }

        previous_signal = signal

    if position is not None:
        exit_price = float(candles[-1]["close"])

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

        position["exit"] = exit_price
        position["result"] = result
        trades.append(position)

    results = [t["result"] for t in trades]

    wins = [x for x in results if x > 0]
    losses = [x for x in results if x < 0]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    pf = (
        gross_profit / gross_loss
        if gross_loss > 0
        else (float("inf") if gross_profit > 0 else 0.0)
    )

    wr = (
        len(wins) / len(results) * 100
        if results
        else 0.0
    )

    print(
        f"{name:12} | "
        f"TRADES={len(trades):>3} | "
        f"WR={wr:>6.2f}% | "
        f"PROFIT={sum(results):>+9.4f}% | "
        f"PF={pf:>7.3f}"
    )

    for side in ("BUY", "SELL"):
        side_results = [
            t["result"]
            for t in trades
            if t["side"] == side
        ]

        if not side_results:
            continue

        side_wins = [x for x in side_results if x > 0]
        side_losses = [x for x in side_results if x < 0]

        gp = sum(side_wins)
        gl = abs(sum(side_losses))

        side_pf = (
            gp / gl
            if gl > 0
            else (float("inf") if gp > 0 else 0.0)
        )

        side_wr = len(side_wins) / len(side_results) * 100

        print(
            f"  {side:4} | "
            f"N={len(side_results):>2} | "
            f"WR={side_wr:>6.2f}% | "
            f"PROFIT={sum(side_results):>+9.4f}% | "
            f"PF={side_pf:>7.3f}"
        )


if __name__ == "__main__":
    print()
    print("=" * 75)
    print("SIGNAL FRESHNESS TEST")
    print("=" * 75)

    print()
    print("--- CURRENT LOGIC ---")

    run_test(
        "TRAIN",
        "data/backtest/BTCUSDT_1m_5000.json",
        fresh_only=False,
    )

    run_test(
        "VALIDATION",
        "data/backtest/BTCUSDT_1m_validation_5000.json",
        fresh_only=False,
    )

    print()
    print("--- FRESH SIGNAL ONLY ---")

    run_test(
        "TRAIN",
        "data/backtest/BTCUSDT_1m_5000.json",
        fresh_only=True,
    )

    run_test(
        "VALIDATION",
        "data/backtest/BTCUSDT_1m_validation_5000.json",
        fresh_only=True,
    )
