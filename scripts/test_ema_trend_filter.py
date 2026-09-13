from src.analysis.market_analyzer import MarketAnalyzer
from src.strategy.basic_strategy import BasicStrategy
import json


TIME_EXIT = 240


def load_candles(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_test(name, path, trend_filter):
    candles = load_candles(path)

    analyzer = MarketAnalyzer(rsi_method="classic")
    strategy = BasicStrategy()

    position = None
    trades = []

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

        # -------------------------------------------------
        # POZYCJA JUŻ OTWARTA
        # -------------------------------------------------
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

            continue

        # -------------------------------------------------
        # FILTR KIERUNKU EMA
        # -------------------------------------------------
        if trend_filter and len(ema_values) >= 2:
            previous_ema = ema_values[-2]

            if signal == "BUY" and ema <= previous_ema:
                signal = "HOLD"

            elif signal == "SELL" and ema >= previous_ema:
                signal = "HOLD"

        # -------------------------------------------------
        # OTWARCIE
        # -------------------------------------------------
        if signal in ("BUY", "SELL"):
            position = {
                "side": signal,
                "entry": float(candles[i]["close"]),
                "entry_index": i,
                "bars": 0,
            }

    # -----------------------------------------------------
    # ZAMKNIĘCIE OSTATNIEJ POZYCJI
    # -----------------------------------------------------
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

    # -----------------------------------------------------
    # STATYSTYKI
    # -----------------------------------------------------
    results = [t["result"] for t in trades]

    wins = [x for x in results if x > 0]
    losses = [x for x in results if x < 0]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    if gross_loss > 0:
        pf = gross_profit / gross_loss
    elif gross_profit > 0:
        pf = float("inf")
    else:
        pf = 0.0

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

        if gl > 0:
            side_pf = gp / gl
        elif gp > 0:
            side_pf = float("inf")
        else:
            side_pf = 0.0

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
    print("EMA TREND FILTER TEST")
    print("=" * 75)
    print()

    print("--- CURRENT LOGIC ---")

    run_test(
        "TRAIN",
        "data/backtest/BTCUSDT_1m_5000.json",
        trend_filter=False,
    )

    run_test(
        "VALIDATION",
        "data/backtest/BTCUSDT_1m_validation_5000.json",
        trend_filter=False,
    )

    print()
    print("--- EMA TREND FILTER ---")

    run_test(
        "TRAIN",
        "data/backtest/BTCUSDT_1m_5000.json",
        trend_filter=True,
    )

    run_test(
        "VALIDATION",
        "data/backtest/BTCUSDT_1m_validation_5000.json",
        trend_filter=True,
    )

    print()
